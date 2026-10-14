---
title: "Rust XML Parsing in 2026: quick-xml vs roxmltree vs serde-xml-rs"
date: "2026-10-14"
tags: ["rust", "xml", "parsing", "libraries", "developer-tools"]
draft: false
---

Your service just got handed a 400 MB SAML assertion, an ISO 20022 payment file, or a decade-old RSS feed, and someone on the team said "let's just use `serde_json` with a conversion step." That is how Monday mornings turn into week-long incidents. XML never left: it is still the wire format for payments, aviation, publishing, desktop documents, and every enterprise integration older than your career.

Rust has four credible XML crates, and they are **not** interchangeable. Two are streaming parsers with completely different APIs, one only builds a read-only tree, and one bolts Serde onto a decade-old event parser. Picking wrong costs you either throughput or a rewrite.

## TL;DR: which Rust XML crate should you actually use?

- **Parsing big files, streaming, low memory?** → `quick-xml`. It is the fastest and most maintained option, and it works with `serde` when you want it.
- **Need to query a document ad hoc (XPath-ish navigation, config files, small payloads)?** → `roxmltree`. It builds a read-only tree you can walk by node reference, with zero unsafe code.
- **Already have `#[derive(Deserialize)]` structs and want XML to behave like JSON?** → `serde-xml-rs`, but accept its quirks and slower release cadence.
- **Legacy code that already uses the `xml-rs` event API?** → stay on it. Version 1.0.0 finally shipped, so migration is optional, not urgent.

If you only read one line: **start with `quick-xml`, and add `roxmltree` the moment you find yourself writing a state machine you did not want to write.**

## Quick comparison (all figures pulled from GitHub and crates.io at publish time)

| Library | Stars | Latest release | Last commit | Model | Namespaces | Serde | License | Verdict |
|---|---|---|---|---|---|---|---|---|
| **quick-xml** | 1,573 | 0.42.0 | 2026-09-02 | Pull / streaming events | Yes | Optional feature | MIT | Best all-rounder |
| **roxmltree** | 537 | 0.21.1 | 2026-09-22 | Read-only DOM tree | Yes | No | MIT / Apache-2.0 | Best for querying |
| **xml-rs** | 471 | 1.0.0 | 2026-08-06 | Push / pull events | Yes | No | MIT | Veteran, stable |
| **serde-xml-rs** | 333 | 0.8.2 | 2026-02-05 | Serde deserializer on `xml-rs` | Partial | Core purpose | MIT | Fastest to write, sharpest edges |

All four are pure Rust, MIT-family licensed, and have no C dependencies — they compile on musl and cross-compile to `wasm32-unknown-unknown` without ceremony.

## Use-case decision matrix

| Your situation | Pick | Why |
|---|---|---|
| 100 MB–10 GB documents, must not buffer | quick-xml | Constant memory pull reader; you decide when to allocate |
| One-shot config or manifest parsing (< 5 MB) | roxmltree | Tree navigation beats hand-written state machines |
| Team already writes Serde structs everywhere | serde-xml-rs | `#[derive(Deserialize)]` in ~10 lines |
| Need to write XML, not just read it | quick-xml | Only mainstream crate with a first-class writer (`quick_xml::Writer`) |
| Mixed namespaces (SOAP, XBRL, OOXML) | quick-xml or roxmltree | Both expose namespace-aware APIs instead of string prefixes |
| Zero-dependency vendor lockdown | xml-rs | Smallest API surface, no feature flags to audit |
| You need XSD validation | none of these | Add a separate validation layer; these crates only parse |

## quick-xml — the pull parser that scales

`quick-xml` is what most production Rust services end up on. You drive the loop, ask for the next event, and the crate hands you borrowed slices. Memory stays flat no matter how large the input is, and you can stop reading at any point — a property that matters enormously when you are scanning an 8 GB log archive for one attribute.

```toml
# Cargo.toml
[dependencies]
quick-xml = { version = "0.42", features = ["serialize", "encoding"] }
```

Basic streaming read, with namespaces resolved and entities decoded:

```rust
use quick_xml::events::Event;
use quick_xml::reader::Reader;

fn scan_titles(xml: &str) -> Vec<String> {
    let mut reader = Reader::from_str(xml);
    reader.config_mut().trim_text(true);
    let mut buf = Vec::new();
    let mut titles = Vec::new();
    let mut in_title = false;

    loop {
        match reader.read_event_into(&mut buf) {
            Ok(Event::Start(e)) if e.name().as_ref() == b"title" => in_title = true,
            Ok(Event::Text(t)) if in_title => {
                titles.push(t.unescape().unwrap().into_owned());
            }
            Ok(Event::End(e)) if e.name().as_ref() == b"title" => in_title = false,
            Ok(Event::Eof) => break,
            Err(e) => panic!("malformed XML at {}: {e}", reader.buffer_position()),
            _ => {}
        }
        buf.clear();
    }
    titles
}
```

Two details that trip people up. First, `read_event_into` borrows into your buffer, so you must copy anything you want to keep — the borrow ends at the next call. Second, `trim_text` is now configured through `reader.config_mut()`, not by setting a public field; older tutorials still show the field assignment and will not compile against 0.42.

Writing XML is equally direct, and it handles escaping for you:

```rust
use quick_xml::events::{BytesEnd, BytesStart, BytesText, Event};
use quick_xml::Writer;

let mut w = Writer::new(Vec::new());
w.write_event(Event::Start(BytesStart::new("invoice")))?;
w.write_event(Event::Text(BytesText::new("Air Filter")))?; // & -> &amp;
w.write_event(Event::End(BytesEnd::new("invoice")))?;
let bytes = w.into_inner();
```

Because the crate is still pre-1.0, minor versions do occasionally carry small breaking changes — pin the version, read the changelog before bumping, and write one round-trip test before you upgrade in a large codebase.

## roxmltree — the read-only DOM you can actually navigate

`roxmltree` parses a whole document into an immutable tree and hands you cheap `Node` handles. There is no unsafe code, no `Rc<RefCell<..>>` gymnastics, and no borrow-checker fight: you copy a `Node` (it is a small `Copy` type) and walk it wherever you like.

```toml
[dependencies]
roxmltree = "0.21"
```

```rust
let doc = roxmltree::Document::parse(xml)?;
let root = doc.root_element();

for svc in root.children().filter(|n| n.has_tag_name("service")) {
    let name = svc.attribute("name").unwrap_or("unnamed");
    let port = svc.children()
        .find(|n| n.has_tag_name("port"))
        .and_then(|n| n.text())
        .unwrap_or("0");
    println!("{name} -> {port}");
}
```

Namespace handling is explicit and correct, which is why this crate is popular for SOAP and OOXML payloads where prefixes lie:

```rust
if node.has_tag_name(("http://schemas.xmlsoap.org/soap/envelope/", "Body")) {
    // matches on the URI, not the prefix
}
```

The trade-offs are real: the whole document must fit in memory, parsing allocates a lot of small nodes, and it is read-only — you cannot mutate and re-serialize. For documents under a few megabytes it is the most pleasant API of the four, and its error messages are unusually good, with positions and hints.

## serde-xml-rs — deserialize straight into your structs

If your codebase is already Serde-shaped, this crate gets you to first working version fastest:

```toml
[dependencies]
serde = { version = "1", features = ["derive"] }
serde-xml-rs = "0.8"
```

```rust
use serde::Deserialize;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "PascalCase")]
struct Server {
    host: String,
    port: u16,
    #[serde(default)]
    tags: Vec<String>,
}

let s: Server = serde_xml_rs::from_str(xml)?;
```

It is built on the `xml-rs` event parser and inherits its behavior. The edges are what you need to plan for: attribute versus element ambiguity is resolved by heuristics that sometimes guess differently than you expect, `$value`/`$text` conventions are borrowed from the XML-to-JSON world and feel unnatural in Rust, sequences of repeated elements are inferred from context rather than schema, and mixed content (text interleaved with tags) essentially cannot be modeled. Its last commit was 2026-02-05 — noticeably quieter than `quick-xml` or `roxmltree`.

Use it when the schema is simple, flat, and stable. Reach for `quick-xml`'s `serialize` feature instead when a document needs both streaming and struct mapping.

## xml-rs — the veteran that finally reached 1.0

`xml-rs` is the oldest crate of the four and for years the only option. Version **1.0.0** shipped in 2026, roughly a decade after the project started, and the API is small and stable: an `EventReader` you pull `XmlEvent` values from, plus a matching writer.

```toml
[dependencies]
xml-rs = "1.0"
```

```rust
use xml::reader::{EventReader, XmlEvent};

let parser = EventReader::new(std::io::BufReader::new(file));
for e in parser {
    match e? {
        XmlEvent::StartElement { name, attributes, .. } => {
            println!("{} ({})", name.local_name, attributes.len());
        }
        XmlEvent::EndDocument => break,
        _ => {}
    }
}
```

Performance is the reason it lost ground: it allocates owned `String`s per event and is measurably slower than `quick-xml` on large inputs. Its value today is stability — if your cargo tree already contains it, or you want the smallest possible dependency surface with no feature-flag matrix to audit, 1.0.0 is a safe place to sit.

## Performance and memory: what actually differs

The honest summary, without fabricated benchmark tables:

- **Streaming beats tree building, always, above ~10 MB.** `quick-xml` in pull mode keeps memory proportional to your buffer; `roxmltree` keeps memory proportional to the document (typically 5–10× the file size once node metadata is accounted for).
- **`xml-rs` allocates per event**, so it sits behind `quick-xml` on throughput and ahead of it on allocation churn. If XML is on a hot path, this is the difference you will feel.
- **Serde layers cost more than raw parsing.** `serde-xml-rs` and `quick-xml`'s `serialize` feature both do struct-mapping work on top of events; measure before assuming.
- **Encoding conversion is a hidden cost.** Feature-gated `encoding` support decodes legacy charsets such as ISO-8859-1 and Shift_JIS. If your inputs are UTF-8 (they usually are), leaving that feature off removes a per-event branch.

The only benchmark that matters is yours: generate a realistic 50 MB sample of your own dialect and measure wall time and peak RSS for both a streaming and a tree approach. Both are a dozen lines of code.

## Pitfalls, security, and migration notes

**Never parse untrusted XML with entity expansion enabled.** Billion-laughs and XXE attacks are parser-level, not application-level. Deny `<!DOCTYPE>` outright: scan for a doctype before parsing or run input through a sanitizer, and never let a parser resolve external entities over the network. This applies identically to all four crates.

**Namespace prefixes are not identities.** `ns0:Body`, `soap:Body`, and `S:Body` can mean the same element. Match on the namespace URI plus local name — both `quick-xml` and `roxmltree` give you the URI, and string-comparing raw tags is how namespace bugs get shipped.

**`quick-xml` minor upgrades can break compilation.** At 0.42 the crate is still pre-1.0. Pin exactly (`=0.42.0`) in services that cannot tolerate churn, and keep one integration test that parses a captured sample document.

**Do not switch parsers mid-pipeline.** Teams commonly start with `serde-xml-rs`, hit a mixed-content document, and migrate to `quick-xml` — the migration is a rewrite of the parsing layer, not a configuration change. If your dialect is likely to grow complexity (SOAP attachments, XBRL contexts, OOXML tables), start on `quick-xml` and skip the detour.

**Whitespace and text nodes.** `roxmltree` preserves whitespace text nodes, so `children()` in a pretty-printed document yields indentation text. Filter with `n.is_element()` or use `children().filter_map(|n| n.is_element().then_some(n))`.

If you are comparing Rust libraries more broadly, our [Rust TUI framework comparison](../2026-08-26-rust-tui-frameworks-ratatui-cursive-crossterm-comparison/) and the [Rust JSON library shootout](../2026-10-03-rust-json-libraries-serde-json-simd-json-sonic-rs/) use the same evaluation approach, and the [Rust CLI parser comparison](../2026-08-10-rust-cli-parsers-clap-argh-bpaf/) covers the argument-handling side of the same ecosystem.

## FAQ

**Which Rust XML crate is fastest?**
`quick-xml` in pull-parsing mode is the fastest of the four for large documents because it borrows slices from a caller-owned buffer instead of allocating per event. `xml-rs` allocates owned values for each event, and tree-building with `roxmltree` adds a full allocation pass on top of parsing.

**Can I use Serde with quick-xml instead of serde-xml-rs?**
Yes. Enable the `serialize` feature (`quick-xml = { version = "0.42", features = ["serialize"] }`) and use `quick_xml::de::from_str`. You get Serde ergonomics on the fastest parser, which is why many teams migrate from `serde-xml-rs` once documents get large.

**Does roxmltree support editing or serializing XML?**
No. `roxmltree` is deliberately read-only: it parses into an immutable tree with no mutation API. To modify and write XML, use `quick-xml`'s `Writer`, which escapes text and attributes correctly and lets you stream output.

**Is xml-rs 1.0 a breaking change from 0.8?**
The 1.0.0 release stabilizes an API that had been effectively frozen for years, so most 0.8 code compiles with a dependency bump alone. The main work is verifying version pins across your workspace, since a 1.0 bump changes resolution for every crate depending on it.

**How do I protect against XXE and billion-laughs attacks in Rust?**
Do not expose entity expansion to untrusted input. Reject documents containing a `DOCTYPE` declaration before parsing, avoid external entity resolution entirely, and enforce a maximum document size at the transport layer. These crates do not fetch remote entities by default, but entity expansion denial is still your responsibility.

**Should I convert XML to JSON and parse that instead?**
Converting first doubles memory and CPU and silently loses information — mixed content, CDATA boundaries, namespace prefixes, and attribute ordering all disappear in the translation. Parse the XML dialect directly; it is less code than maintaining a conversion layer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust XML Parsing in 2026: quick-xml vs roxmltree vs serde-xml-rs",
  "description": "Hands-on comparison of the four viable Rust XML crates in 2026: quick-xml, roxmltree, serde-xml-rs and xml-rs, with real code, decision matrix, security pitfalls and version data.",
  "datePublished": "2026-10-14",
  "dateModified": "2026-10-14",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
