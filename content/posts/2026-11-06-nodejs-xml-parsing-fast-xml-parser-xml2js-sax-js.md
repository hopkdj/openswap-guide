---
title: "fast-xml-parser vs xml2js vs sax-js in 2026: Which Node.js XML Parser Survives a 100 MB File?"
date: "2026-11-06"
tags: ["nodejs", "xml", "parsing", "javascript", "performance"]
draft: false
cover: "/img/screenshots/fxp_logo.jpg"
---

Your integration partner sends a 40 MB invoice batch as XML, your Node process climbs to 1.8 GB RSS, and the container gets OOM-killed at 3 a.m. That is the moment most teams discover they picked their XML parser by copying the first Stack Overflow answer.

XML never died. It is still the wire format for SOAP endpoints, ISO 20022 payments, UBL invoices, sitemaps, OOXML documents, SAML assertions, RSS feeds and roughly every government API on the planet. In Node.js you have three serious pure-JavaScript options: **fast-xml-parser**, **xml2js** and **sax-js** — plus **xmlbuilder2** on the writing side. They are not interchangeable. One materializes a full object tree, one emulates a 1998 SAX event API, and one was rebuilt specifically to avoid C++ addons while staying fast.

## TL;DR — the 30-second verdict

- **Building a new service that maps XML to objects?** Use **fast-xml-parser**. It is the only one of the three that validates, parses and builds, ships TypeScript types, has zero native dependencies and stays fast on large files.
- **Stuck maintaining a 2016 codebase?** Keep **xml2js** — it still gets security patches, but do not start new work on it.
- **Streaming 2 GB of XML that never fits in memory?** Use **sax-js** directly. It is an event parser, not a DOM builder, and that is exactly the point.
- **Need to *generate* XML (SOAP envelopes, sitemaps, UBL)?** Use **xmlbuilder2**, not string concatenation.

## Side-by-side comparison (data pulled from GitHub on 2026-11-06)

| | **fast-xml-parser** | **xml2js** | **sax-js** |
|---|---|---|---|
| GitHub stars | **3,140** | **4,959** | **1,157** |
| Last push | 2026-11-03 | 2026-04-30 | 2026-07-24 |
| License | MIT | MIT | Blue Oak Model License 1.0.0 |
| Parsing model | Direct string → JS object | SAX wrapper → JS object | Event callbacks (true SAX) |
| Native dependencies | None (pure JS) | None (pure JS) | None (pure JS) |
| Built-in validator | Yes (separate `fast-xml-validator` recommended) | No | Minimal (strict mode only) |
| XML building | Yes (`XMLBuilder`) | Yes (via `xmlbuilder`) | No |
| TypeScript types | Bundled | `@types/xml2js` | `@types/sax` |
| Streaming input | Yes (chunked `parse`) | Yes (SAX under the hood) | Yes, by design |
| Documented large-file ceiling | Tested to **100 MB** | Community reports of trouble past ~50 MB | Bounded by your chunk buffer |
| Async API | Sync (CPU-bound) | Callback **and** Promise | Event-driven |
| Browser support | Yes (ESM + UMD build) | Via bundler | Yes |

## Decision matrix: pick in ten seconds

| Your situation | Pick | Why |
|---|---|---|
| REST/SOAP client that needs plain objects | **fast-xml-parser** | `parser.parse(str)` returns what you expect, with attribute handling you control |
| Legacy code already calling `parseString` | **xml2js** | Avoid a rewrite; migrate file-by-file |
| 500 MB+ feed you must not load into RAM | **sax-js** | Constant memory: you consume tokens, nothing is retained |
| Generating SOAP envelopes or sitemaps | **xmlbuilder2** | Correct escaping, namespaces and declaration handling |
| RSS/Atom ingestion in a queue worker | **fast-xml-parser** + `isArray` | Terse mapping, predictable arrays for single-item feeds |
| Untrusted XML from the public internet | **fast-xml-parser** with entity processing disabled | Explicit control over DTD/entity expansion |

## fast-xml-parser: the default choice in 2026

The pitch is unusually blunt in the project README: *"Validate XML, Parse XML to JS Object, or Build XML from JS Object without C/C++ based libraries and no callback."* No callback matters more than it sounds — it means the hot path is a synchronous scan with no event dispatch overhead, and it means you can use it inside a `for` loop without wrapping everything in promises.

Basic parse and build, straight from the official README:

```javascript
import { XMLParser, XMLBuilder } from "fast-xml-parser";

const XMLdata = `<note><to>Ada</to><from>Grace</from><body>Ship it</body></note>`;

const parser = new XMLParser();
let jObj = parser.parse(XMLdata);
// { note: { to: 'Ada', from: 'Grace', body: 'Ship it' } }

const builder = new XMLBuilder();
const xmlContent = builder.build(jObj);
```

The configuration surface is where this library wins or bites you. These are the options that actually matter in production:

```javascript
import { XMLParser, XMLValidator } from "fast-xml-parser";

const options = {
  ignoreAttributes: false,          // keep attributes, default is TRUE (they vanish!)
  attributeNamePrefix: "@_",        // attributes become @_id, @_currency
  parseTagValue: true,              // "42" becomes the number 42 — see pitfalls
  parseAttributeValue: false,       // keep attribute values as strings
  trimValues: true,
  isArray: (name, jpath) => jpath === "feed.entry",  // force arrays for single-item feeds
  cdataPropName: "__cdata",
  stopNodes: ["*.script", "*.raw"], // do not descend into these
  processEntities: true,
  allowBooleanAttributes: true,
  ignoreDeclaration: true,
  ignorePiTags: true,
};

const validation = XMLValidator.validate(xmlString);
if (validation !== true) {
  throw new Error(`Malformed XML: ${validation.err.msg} at line ${validation.err.line}`);
}

const parser = new XMLParser(options);
const doc = parser.parse(xmlString);
```

Three things are worth calling out because they cause real incidents:

**`ignoreAttributes` defaults to `true`.** A UBL invoice where the currency lives on `<cbc:Amount currencyID="EUR">` will silently lose every attribute. Set it to `false` on day one.

**`isArray` is the fix for the single-item bug.** Most XML-to-object mappers return an object when a list has one element and an array when it has two. Your `for` loop works in staging and throws `entries.map is not a function` in production the first time a customer has exactly one line item. Forcing arrays by jPath removes that entire class of bug:

```javascript
const parser = new XMLParser({
  ignoreAttributes: false,
  isArray: (name, jpath) => ["orders.order", "orders.order.lines.line"].includes(jpath),
});
```

**Order preservation costs memory.** The `preserveOrder: true` option returns an array-of-tag-objects structure instead of a tree. It is the right call when signature verification depends on element order (XML-DSig, SAML), and the wrong call for a 100 MB import job.

![fast-xml-parser benchmark chart from the official repository](/img/screenshots/fxp_bench.jpg "Official fast-xml-parser comparison chart published in the project repository")

## xml2js: still alive, still callback-shaped

xml2js is the library your Stack Overflow answer was written against. It is a thin object-mapping layer over sax-js, which the README states plainly: *"Uses sax-js and xmlbuilder-js."* That inheritance explains both its strengths (battle-tested tokenizer) and its weaknesses (two mapping layers, two option sets, one very configurable result).

```javascript
const { parseString, parseStringPromise, Builder } = require("xml2js");

// Callback style — what most legacy code looks like
parseString("<root>Hello xml2js!</root>", (err, result) => {
  console.dir(result); // { root: 'Hello xml2js!' }
});

// Promise style — the only version worth writing today
const options = {
  explicitArray: false,   // single children are NOT wrapped in arrays
  explicitRoot: false,    // drop the root key
  attrkey: "$",           // attributes live under $
  charkey: "_",           // text lives under _
  trim: true,
  normalizeTags: true,    // <FooBar> and <foobar> both become 'foobar'
  mergeAttrs: false,
};

const doc = await parseStringPromise(xmlString, options);
// <book id="7"><title>Dune</title></book> with explicitRoot:false, explicitArray:false
// => { book: { title: 'Dune', $: { id: '7' } } }
```

The `explicitArray: false` default flip is the classic trap in reverse: xml2js defaults to **always** wrapping children in arrays (`explicitArray: true`), which is verbose but type-stable. Turning it off produces prettier objects and the same one-item/several-item inconsistency described above. Pick one convention and enforce it with a schema check at the boundary.

Where xml2js still earns its keep: bidirectional conversion with a matching `Builder`, an enormous install base, and security patches that keep landing (last push 2026-04-30). Where it does not: async-only API, no bundled types, no validator, and a mapping layer you cannot easily debug when the shape surprises you.

## sax-js: the parser you reach for when the file is bigger than the container

sax-js does exactly one thing: it turns a byte stream into events. The README is refreshingly honest about scope — *"An HTML Parser — That's a fine goal, but this isn't it. It's just XML."* No DOM, no object tree, no XPath, minimal validation.

That restriction is the feature. A SAX consumer holds one element's worth of state, so memory stays flat whether the feed is 4 MB or 4 GB:

```javascript
const sax = require("sax");
const fs = require("fs");

const strict = true;                 // set false for messy HTML-ish feeds
const parser = sax.parser(strict, { trim: true, lowercase: true });

let current = null;
let rows = 0;

parser.onopentag = (node) => {
  if (node.name === "record") {
    current = { id: node.attributes.id, title: "", amount: 0 };
  }
};

parser.ontext = (t) => {
  if (!current) return;
  current.title += t;               // text can arrive in multiple chunks
};

parser.onclosetag = (name) => {
  if (name === "record" && current) {
    rows++;
    // hand the row to a batch writer — do NOT accumulate in an array
    batch.push(current);
    if (batch.length >= 1000) flush(batch.splice(0));
    current = null;
  }
};

parser.onerror = (e) => {
  parser.resume();                  // or abort the whole job
};

fs.createReadStream("huge-feed.xml")
  .pipe(parser);
```

Two operational notes from running this pattern: **text arrives in fragments**, so `ontext` must append rather than assign, and **`parser.onerror` does not stop the parser** unless you throw — call `parser.resume()` if you want to skip a bad record, or destroy the stream if corruption means the rest of the file is untrustworthy.

If your pipeline is "consume a nightly dump into Postgres," sax-js plus a 1,000-row batch writer will run in a 256 MB container. The same job with a tree-building parser needs the file plus the tree, which is why teams keep rediscovering it.

## Building XML: xmlbuilder2 instead of string templates

Half of the XML bugs I see are on the write side. Template literals do not escape `&`, `<` or `"`, and they cannot emit namespace declarations correctly:

```javascript
const { create } = require("xmlbuilder2");

const doc = create({ version: "1.0", encoding: "UTF-8" })
  .ele("soap:Envelope", {
    "xmlns:soap": "http://schemas.xmlsoap.org/soap/envelope/",
  })
    .ele("soap:Body")
      .ele("GetInvoice", { id: "INV-2026-0042" })
        .ele("Amount", { currencyID: "EUR" }, "1499.00")
      .up()
    .up()
  .up();

console.log(doc.end({ prettyPrint: true }));
```

xmlbuilder2 is at **409 stars** with a push on 2026-05-08 and an MIT license. It is small, spec-correct and pairs well with fast-xml-parser, which uses it conceptually as the builder half of the ecosystem.

## Performance and memory: what the numbers actually say

Independent benchmarks move around, so treat any absolute milliseconds figure with suspicion and watch the shape instead:

| Workload | fast-xml-parser | xml2js | sax-js |
|---|---|---|---|
| 5 MB document → object | Fastest of the three; single pass, no event dispatch | 2–4× slower; two mapping layers | N/A unless you build the object yourself |
| 100 MB document → object | Works, but RSS ≈ 4–6× file size | Risky; teams report GC thrash | Stream it instead |
| 2 GB document | Do not | Do not | Correct tool — flat memory |
| CPU profile | String scanning | SAX events + mapping | SAX events only |

The practical rule: **object mapping is a memory multiplier.** Every parsed element becomes a JS object with hidden-class overhead, and V8 will happily spend your container's limit on it. If the file is larger than roughly a quarter of your memory budget, switch from "parse then process" to "stream and process."

Run the comparison yourself before committing — it is a 20-line benchmark, and your document shape (deep nesting, huge text nodes, many attributes) matters more than the averages:

```javascript
import { XMLParser } from "fast-xml-parser";
import { parseStringPromise } from "xml2js";
import { readFileSync } from "node:fs";

const xml = readFileSync("sample.xml", "utf8");
const N = 20;

console.time("fast-xml-parser");
for (let i = 0; i < N; i++) new XMLParser({ ignoreAttributes: false }).parse(xml);
console.timeEnd("fast-xml-parser");

console.time("xml2js");
for (let i = 0; i < N; i++) await parseStringPromise(xml, { explicitArray: false });
console.timeEnd("xml2js");

console.log("peak RSS MB:", Math.round(process.memoryUsage().rss / 1048576));
```

## Pitfalls that cost real money

**1. Entity expansion (billion laughs).** Any XML parser that resolves internal entities can be turned into a memory bomb by a malicious DTD. On the public internet, disable entity processing (`processEntities: false`) and reject documents with a DOCTYPE unless you specifically need them. This is the XML equivalent of letting a stranger run `eval` on your server.

**2. External entity injection (XXE).** If a parser resolves external entities, `<xi:include href="file:///etc/passwd"/>` becomes a file read. Pure-JS parsers are less exposed than libxml2-based tooling, but the mitigation is the same: no DTD, no external entities, ever.

**3. `parseTagValue` destroys leading zeros and big integers.** `<account>0001234</account>` becomes the number `1234`, and a 20-digit payment reference silently loses precision because it exceeds `Number.MAX_SAFE_INTEGER`. For financial and identifier fields, use `parseTagValue: false` and convert explicitly.

**4. Attribute-case and namespace prefixes.** `cbc:Amount` and `Amount` are different keys. If you are mapping UBL, ISO 20022 or SOAP documents, either strip prefixes deliberately with a `transformTagName`/post-processing step or match on full qualified names.

**5. Whitespace is content in mixed-content documents.** `trimValues: true` is a sane default for data feeds and wrong for documents where a space between `<b>` runs is meaningful (XHTML, OOXML runs). Test with a real document, not a pretty-printed sample.

**6. Encoding lies.** An XML declaration claiming `encoding="ISO-8859-1"` while the bytes are UTF-8 produces mojibake that survives every downstream check. Read the first bytes, decode explicitly with `TextDecoder`, and pass a string — not a buffer — to the parser.

**7. Silent recovery in loose mode.** sax-js with `strict = false` will happily parse broken markup and hand you partial events. Perfect for scraping, dangerous for invoices. Choose deliberately per data source.

## Migration path if you are leaving xml2js

You do not need a big-bang rewrite. Write one adapter module that exposes the same function signature your code already calls, implement it with fast-xml-parser, and let both run in shadow mode for a week:

```javascript
// xml-adapter.js — swap the implementation, keep the contract
import { XMLParser } from "fast-xml-parser";

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "@_",
  parseTagValue: false,
  isArray: (name, jpath) => jpath === "orders.order",
});

export async function parseInvoice(xml) {
  const doc = parser.parse(xml);
  return normalize(doc);   // your existing shape mapper, unchanged
}
```

Log a diff count per request, alert above zero, then delete the old path. If you have written per-language parsers before, the same trade-offs appear in other ecosystems — our [C++ and Python XML parser comparison](../2026-06-20-self-hosted-xml-parsing-libraries-lxml-pugixml-xerces-rapidxml/) and the [Rust XML crate benchmark](../2026-10-14-rust-xml-parsing-quick-xml-roxmltree-serde-xml-rs/) show the identical "tree versus stream" fork. For adjacent parsing work in Node, the [MIME email parser comparison](../2026-10-10-mime-email-parsing-libraries-mailparser-enmime-mime4j-comparison/) follows the same evaluation method.

## FAQ

### Which Node.js XML parser is fastest in 2026?

For document-to-object conversion, **fast-xml-parser** is consistently the fastest pure-JavaScript option and avoids native compilation entirely. sax-js can beat it on wall-clock time for very large files because it never builds an object tree, but you pay for that with hand-written event handlers and state management.

### Can fast-xml-parser handle a 100 MB XML file?

Yes — the maintainers document testing up to 100 MB. The limit is memory, not the parser: expect peak RSS around four to six times the file size once the object tree exists. Above roughly a quarter of your container's memory limit, stream the file with sax-js instead of parsing it whole.

### Is xml2js deprecated?

No. xml2js received a push in April 2026 and still gets dependency and security maintenance, but its API is callback-first, it ships no bundled types and it has no validator. It is safe to keep in existing code and hard to justify for new services.

### How do I stop attributes from disappearing when parsing XML in Node?

Set `ignoreAttributes: false` in fast-xml-parser. The default is `true`, which silently drops every attribute — the single most common cause of "where did the currency code go" bug reports. Also set `attributeNamePrefix` so attribute keys cannot collide with child element names.

### What is the safest way to parse untrusted XML?

Reject documents containing a DOCTYPE unless the business case requires it, disable entity processing (`processEntities: false`), never enable external entity resolution, and cap input size at the HTTP layer. Entity expansion attacks cost the attacker a few kilobytes and cost you the container.

### Should I use sax-js or fast-xml-parser for RSS feeds?

Use fast-xml-parser with `isArray` forcing the item path to an array. RSS feeds routinely contain a single `<item>`, and without forced arrays your `.map()` call fails intermittently. Reserve sax-js for feeds measured in gigabytes or for continuous streams where you must emit records as they arrive.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "fast-xml-parser vs xml2js vs sax-js in 2026: Which Node.js XML Parser Survives a 100 MB File?",
  "description": "A production-focused comparison of Node.js XML parsers: fast-xml-parser, xml2js, sax-js and xmlbuilder2, with real GitHub data, streaming patterns, memory limits and security pitfalls.",
  "datePublished": "2026-11-06",
  "dateModified": "2026-11-06",
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
