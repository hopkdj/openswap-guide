---
title: "TOML Parsing Libraries in 2026: tomllib vs tomlkit vs toml-rs vs go-toml"
date: "2026-09-27"
tags: ["developer-tools", "libraries", "configuration", "python", "rust", "golang"]
cover: "/img/screenshots/taplo-toml-editor-highlight.jpg"
draft: false
---

You built a small tool that bumps a version in `pyproject.toml`. It works — and it returns a file with every comment stripped, keys reordered alphabetically, and one-line inline arrays exploded across six lines. The user's diff is 400 lines for a one-character change, and they will never run your tool again.

That is the difference between **parsing** TOML and **round-tripping** TOML. Parsing is a solved problem in every language; preserving a human's formatting while editing a machine's configuration is the hard part, and it splits the ecosystem cleanly in two.

This guide covers the TOML parsers and editors that matter in 2026 — what each one does with your comments, which ones are strict about unknown keys, and which ones actually pass the official conformance suite.

## Quick Verdict (TL;DR)

- **Python:** read with the stdlib **`tomllib`** (3.11+); edit with **`tomlkit`**. Use `tomli-w` only when you are writing a fresh file you do not have to preserve.
- **Rust:** deserialize with the **`toml`** crate (Serde-compatible); edit programmatically with **`toml_edit`**, which is what `cargo add` and `cargo upgrade` use to patch manifests without reformatting them.
- **Go:** **`BurntSushi/toml`** when you want reflection-based decoding plus metadata about which keys were set; **`pelletier/go-toml` v2** when you want strict decoding and much better error messages.
- **JavaScript/TypeScript:** **`smol-toml`** is the actively maintained parser and advertises TOML 1.1.0 support; **`iarna-toml`** has the JSON-like interface but has not been pushed since 2024.
- **Validation, formatting and editor support:** **Taplo**, which is a full TOML toolkit (language server, formatter, schema validation) rather than a library.
- **Before you pick:** check the library against **`toml-test`**, the language-agnostic conformance suite. "Parses my config file" is not the same as "implements the specification".

## Comparison Table (Live Repository Data, September 2026)

| Library | Language | Stars | Last push | Style-preserving | Strict unknown keys | Formats dates natively | License |
|---|---|---|---|---|---|---|---|
| [`python-poetry/tomlkit`](https://github.com/python-poetry/tomlkit) | Python | 854 | 2026-09-21 | **Yes** | n/a (document model) | Yes | MIT |
| `tomllib` (Python stdlib) | Python | — | ships with 3.11+ | No (read-only) | n/a | Yes | PSF |
| [`toml-rs/toml`](https://github.com/toml-rs/toml) | Rust | 1080 | 2026-09-18 | Via companion `toml_edit` | Via `deny_unknown_fields` | Yes | MIT / Apache-2.0 |
| [`BurntSushi/toml`](https://github.com/BurntSushi/toml) | Go | 5011 | 2026-08-18 | No | `MetaData.Undecoded()` | Yes | MIT |
| [`pelletier/go-toml`](https://github.com/pelletier/go-toml) | Go | 1985 | 2026-08-03 | Order-preserving model | `Decoder.DisallowUnknownFields()` | Yes | MIT |
| [`squirrelchat/smol-toml`](https://github.com/squirrelchat/smol-toml) | JS/TS | 311 | 2026-09-22 | No | No | Yes | MIT |
| [`iarna/iarna-toml`](https://github.com/iarna/iarna-toml) | JS | 340 | 2024-05-30 | No | No | Yes | ISC |
| [`tamasfe/taplo`](https://github.com/tamasfe/taplo) | Rust (toolkit) | 2402 | 2026-07-28 | **Yes** (formatter/LSP) | Schema-based | Yes | MIT |
| [`toml-lang/toml-test`](https://github.com/toml-lang/toml-test) | suite | 265 | 2026-09-15 | n/a | n/a | n/a | MIT |

The TOML specification repository itself sits at **20,623 stars** and was last updated in September 2026, which tells you how much of the ecosystem's energy now goes into tooling around the format rather than the format.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Use | Why |
|---|---|---|
| Read config in a Python 3.11+ app | `tomllib` | Zero dependencies, spec-compliant, dates decoded to `datetime`/`date` for free |
| Python tool that rewrites user config | `tomlkit` | Keeps comments, whitespace, key order and inline-table style intact |
| Python 3.10 or older | `tomli` + `tomli-w` | Same API as `tomllib`; the stdlib module is a copy of it |
| Rust service config | `toml` + Serde | `#[derive(Deserialize)]` structs, `deny_unknown_fields` when you want strictness |
| Rust tool patching `Cargo.toml` | `toml_edit` | Format-preserving edits; the crate behind `cargo add` |
| Go service, want typed structs | `BurntSushi/toml` | `toml.Decode` into structs; `MetaData` reports every key you ignored |
| Go service, want loud failures | `pelletier/go-toml` v2 | Strict mode plus error messages with source context |
| Node/Deno/Bun config loader | `smol-toml` | Small, correct, actively maintained, claims 1.1.0 support |
| Editing TOML in an editor or CI | `taplo` | Language server, formatter and JSON-schema validation; both CLI and extension |
| Proving your parser is correct | `toml-test` | Thousands of valid/invalid cases; run it in CI |

## Python — tomllib for Reading, tomlkit for Editing

Since Python 3.11 the standard library has a real TOML parser, and it is the one you should reach for:

```python
import tomllib

with open("pyproject.toml", "rb") as f:      # binary mode is required
    cfg = tomllib.loads(f.read().decode())

cfg["project"]["version"]
```

Two details bite people immediately. First, `tomllib` requires **binary** mode — `tomllib.load(open("x.toml"))` raises `TypeError`. Second, it is **read-only**: there is no `tomllib.dumps`. That is deliberate; the stdlib team did not want to bless a serialisation style, because style is exactly what the ecosystem disagrees about.

For writing, that leaves `tomlkit`, whose entire reason to exist is preserving what the human wrote:

```bash
uv add tomlkit
```

```python
import tomlkit

doc = tomlkit.parse(open("pyproject.toml").read())
doc["tool"]["poetry"]["version"] = "1.2.3"   # comments, spacing and key order survive

with open("pyproject.toml", "w") as f:
    f.write(tomlkit.dumps(doc))
```

That is the whole difference: a `dict`-based writer produces a *valid* file, while `tomlkit` produces a *minimal diff*. If your tool touches someone's repository, that distinction decides whether you get adopted or reverted.

**Verdict for Python:** `tomllib` to read, `tomlkit` to edit, `tomli-w` if you genuinely do not need style preservation.

## Rust — The Serde Crate and the Editing Crate

Rust splits the same way, but the split is explicit in the documentation: the `toml` crate is a "Serde-compatible TOML decoder and encoder", and its README points at **`toml_edit`** for "format-preserving editing or finer control over output" — which is exactly what Cargo itself does when it inserts a dependency into your manifest without reordering your file.

```bash
cargo add toml
```

```rust
#[derive(serde::Deserialize)]
struct Config {
    server: Server,
}

#[derive(serde::Deserialize)]
struct Server {
    port: u16,
    host: String,
}

let cfg: Config = toml::from_str(&std::fs::read_to_string("app.toml")?)?;
```

Because it is Serde-based, the usual controls apply: `#[serde(deny_unknown_fields)]` turns a typo in a config key into an error instead of a silently ignored field, and `#[serde(default)]` lets you add options without breaking existing deployments. Dates arrive as `toml::value::Datetime` unless you map them to `chrono` or `time` types.

**Verdict for Rust:** `toml` for reading, `toml_edit` for writing back into files you do not own.

## Go — BurntSushi/toml vs pelletier/go-toml v2

Both are mature, both are MIT-licensed, and the choice comes down to error behaviour and model.

**`BurntSushi/toml`** (5,011 stars, the most-starred TOML parser on GitHub) decodes into structs via reflection and, crucially, tells you what it *ignored*:

```go
var conf Config
_, err := toml.Decode(tomlData, &conf)
if err != nil {
    log.Fatal(err)
}
```

The first return value is a `MetaData`, which reports `Undecoded()` keys — the built-in answer to "why did my config change have no effect?" It also exposes `IsDefined("server.port")` style queries for layering defaults with user overrides. The README's own example config, decoded into the documented struct, is the canonical usage:

```toml
Age = 25
Cats = [ "Cauchy", "Plato" ]
Pi = 3.14
Perfection = [ 6, 28, 496, 8128 ]
DOB = 1987-07-05T05:45:00Z
```

```go
type Config struct {
	Age        int
	Cats       []string
	Pi         float64
	Perfection []int
	DOB        time.Time
}
```

**`pelletier/go-toml` v2** focuses on strictness and diagnostics. Its README documents decoder errors that point at the offending line and type mismatch instead of returning a vague failure:

```go
import "github.com/pelletier/go-toml/v2"
```

```text
1| [server]
2| path = 100
 |        ~~~ cannot decode TOML integer into struct field toml_test.Server.Path of type string
3| port = 50
```

It also keeps a document model with preserved key order (`toml.Unmarshal` for structs, `Marshal`/`LoadBytes` for round-tripping), and `Decoder.DisallowUnknownFields()` gives you the strict mode that `BurntSushi/toml` offers through a different mechanism.

**Verdict for Go:** `BurntSushi/toml` if you want the 5k-star safety net and undecoded-key reporting; `go-toml` v2 if your team's pain point is unreadable decode errors. Ship one, not both.

## JavaScript and TypeScript — smol-toml vs iarna-toml

The JS story is a maintenance story. **`iarna-toml`** offered a JSON-like interface (`TOML.parse`, `TOML.stringify`) and was widely used, but its last push was **May 2024**. **`smol-toml`** (311 stars, last push September 2026) is small, actively maintained, and advertises **TOML 1.1.0** support, while most parsers in this comparison target 1.0.0.

```bash
npm install smol-toml
```

```javascript
import { parse, stringify } from 'smol-toml';

const config = parse(await readFile('config.toml', 'utf8'));
config.server.port = 8080;
await writeFile('config.toml', stringify(config));
```

Note what `stringify` cannot do: it serialises a plain object, so comments, key order and quoting style from the original file are gone. If you need to *edit* a user's TOML in Node, treat that as a product requirement and pick a formatting-preserving library — or drive `taplo` as a subprocess, which is what several config tooling projects do.

**Verdict for JS:** `smol-toml` for parsing, and be honest with yourself that you are not round-tripping.

## The Toolkit Layer — Taplo

Taplo is worth a section of its own because it is what you reach for when the requirement is not "parse this file" but "validate, format and edit TOML across a repository".

![TOML syntax highlighting in the Taplo editor extension](/img/screenshots/taplo-toml-editor-highlight.jpg "Taplo provides syntax highlighting for TOML configuration files")

It ships a **language server** (diagnostics, completion, hover, go-to-definition in key paths), a **formatter**, and **JSON-Schema-based validation** — so a `Cargo.toml` or `pyproject.toml` can be checked against a schema in CI the same way you would validate YAML.

![Semantic color customization in the Taplo extension](/img/screenshots/taplo-toml-semantic-colors.jpg "Taplo's editor integration exposes semantic color categories for TOML keys and values")

For a repository with dozens of TOML files, the practical win is the CLI in a pre-commit hook: one formatter, one validator, no per-language quirks. It does not replace a parsing library in your application — it replaces the *inconsistency* between the five parsers you would otherwise use.

## Pitfalls That Break Config Tooling

**Parsing is not round-tripping.** The single most common defect in config-writing tools is destroying comments and key order. If your tool modifies a file a human maintains, use `tomlkit`, `toml_edit`, or Taplo's formatter path.

**Dates and times are real types.** TOML has offset date-time, local date-time, local date and local time — four distinct types that map to `datetime`, `date` and `time` in Python and to `toml::value::Datetime` in Rust unless you opt into `chrono`/`time`. A parser that returns them as strings will silently break comparisons.

**Unknown keys are silently ignored by default.** In a struct-mapping language, a typo in a config key is usually not an error — it is a field that stays at its zero value. Turn on strict mode, or use `BurntSushi/toml`'s `Undecoded()` check, and fail loudly in development builds.

**Inline tables and standard tables are different things.** `key = { a = 1 }` is an inline table and must stay on one line in TOML 1.0; multi-line inline tables only arrive with the 1.1 draft. A parser that accepts them is lenient in a way that will fail on a different tool later.

**Duplicate keys are invalid.** A file that "works" with a lenient parser may be rejected outright elsewhere. Run your documents through `toml-test` or a strict validator in CI, not just through your own code.

**Bare keys have a restricted alphabet.** Keys with dots, spaces, or non-ASCII characters must be quoted: `"my.key" = 1` is one key, while `my.key = 1` is a dotted path defining `my` and then `key`. Config generators trip over this constantly.

**Encoding is UTF-8, always.** TOML has no encoding declaration. Files written by an editor in a legacy code page will either fail or produce mojibake, and the parser has no way to detect it.

**Hot reload needs file watching, not polling the parse.** Re-parsing a config every request is wasteful; watch the file and re-parse on change — then validate the new document before swapping it in, so a syntax error does not take down a running service.

If you are choosing a config format rather than a parser, our [YAML parsing libraries comparison](../2026-06-20-yaml-parsing-libraries-pyyaml-serdayaml-jsyaml-snakeyaml-libyaml/) and [JSON parser libraries comparison](../2026-06-19-self-hosted-json-parser-libraries-simdjson-rapidjson-orjson-ultrajson/) cover the other two sides of the same decision. For C++ codebases there is a dedicated [C++ configuration management libraries guide](../2026-06-22-cpp-configuration-management-libraries-toml11-yamlcpp-tomlplusplus-libconfig/), and Node-specific environment handling is covered in the [Node.js config libraries comparison](../2026-08-23-nodejs-config-libraries-dotenv-envalid-node-config-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TOML Parsing Libraries in 2026: tomllib vs tomlkit vs toml-rs vs go-toml",
  "description": "Compare TOML parsers and format-preserving editors across Python, Rust, Go and JavaScript, including spec conformance via toml-test and the Taplo toolkit.",
  "datePublished": "2026-09-27",
  "dateModified": "2026-09-27",
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

## FAQ

**What is the difference between parsing TOML and round-tripping TOML?**
Parsing produces a data structure and discards the original syntax. Round-tripping also preserves comments, whitespace, key order and quoting style so that re-serialising the document produces a minimal diff. Libraries such as `tomlkit`, `toml_edit` and Taplo are built for round-tripping; `tomllib`, `toml`, `smol-toml` and `BurntSushi/toml` are parsers.

**Does Python have a built-in TOML parser?**
Yes — `tomllib` ships with Python 3.11 and later and is spec-compliant. It is read-only, so writing requires `tomli-w` for new files or `tomlkit` when formatting must be preserved. On 3.10 and earlier, install `tomli` and `tomli-w`.

**Why does `tomllib.load()` require binary mode?**
Because the TOML specification does not define an encoding declaration; the parser expects bytes it can decode as UTF-8 itself. Passing a text-mode file object raises a `TypeError`.

**How do I know if a TOML parser is actually correct?**
Run it against `toml-test`, the official language-agnostic conformance suite. It contains valid and invalid documents covering dates, escapes, dotted keys and error cases, and it is designed to be wired into a parser's CI.

**Which Go TOML library is better, BurntSushi/toml or go-toml v2?**
`BurntSushi/toml` has the larger community, reports undecoded keys through `MetaData`, and is the safe default. `pelletier/go-toml` v2 produces much more informative decode errors and supports strict unknown-field rejection plus order-preserving documents. Pick by which failure mode hurts you more.

**Should I use TOML or YAML for configuration?**
TOML is stricter, has real date and time types, and avoids YAML's indentation and type-coercion surprises — which is why Cargo, Poetry and many modern tools chose it. YAML remains more expressive for deeply nested, document-style data. If your config is mostly flat key/value with sections, TOML is usually the better fit.

**Can I edit TOML safely from a shell script or CI job?**
Yes, if you use a format-preserving tool (Taplo's CLI, `toml_edit`-based tooling, or `tomlkit` in Python) rather than `sed`. Text substitution breaks on quoting styles, multi-line arrays and duplicate-looking keys that are semantically different.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
