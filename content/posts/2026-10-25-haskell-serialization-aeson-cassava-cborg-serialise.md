---
title: "Haskell Serialization in 2026: aeson vs cassava vs cborg/serialise — Which Belongs in Your Stack?"
date: "2026-10-25"
tags: ["haskell", "serialization", "json", "developer-tools"]
draft: false
cover: "/img/screenshots/haskell-serialization-libs.jpg"
description: "aeson vs cassava vs cborg/serialise compared on real API surface, streaming behaviour, schema-migration story and build cost — with configs pulled from the upstream repos."
---

Every Haskell service eventually makes the same decision three times: how to talk JSON to the outside world, how to ingest the CSV someone emails you every Monday, and how to persist values in something cheaper and stricter than JSON. Most teams answer all three with one library and regret it by the second release.

The three libraries below are not competitors in the same lane — that is exactly why picking between them badly hurts. **aeson (1,306★) is a JSON codec, cassava (226★) is a row-oriented CSV engine, and cborg/serialise (209★) is a binary format with an actual migration story.** Data below was pulled from the upstream repositories on **2026-10-25**.

## Quick Verdict

- **aeson for anything that crosses a network boundary as JSON.** It is the ecosystem default: `FromJSON`/`ToJSON` instances, `Generic` deriving, and every library you depend on already speaks it.
- **cassava for CSV that is large enough to matter.** It decodes record-by-record from a lazy `ByteString` and does not build an intermediate AST — which is the difference between a 200 MB file succeeding and your heap exploding.
- **cborg/serialise for storage you control on both ends.** CBOR plus a version tag gives you compact binary that stays readable by generic tooling *and* supports backwards-compatible deserialisation with migrations.
- **Do not use one for all three.** JSON as an internal storage format is the most common Haskell performance mistake nobody profiles, because it works fine until the file is 300 MB.

## Side-by-Side Comparison

| Dimension | aeson | cassava | cborg + serialise |
|---|---|---|---|
| Latest version (2026-10-25) | **2.3.2.0** | 0.6.0.0 | cborg 0.2.10.0 / serialise 0.2.6.1 |
| GitHub stars | **1,306** | 226 | 209 (shared repo) |
| License | BSD-3-Clause | BSD3 | BSD3 |
| Last upstream push | 2026-10-23 | 2026-03-02 | 2026-05-13 |
| Format | JSON text | CSV / TSV (configurable delimiter) | CBOR (RFC 7049) |
| Intermediate representation | `Value` AST (optional) | none — records decoded directly | none — `Encoding`/`Decoding` |
| Streaming | Incremental via `attoparsec`/`conduit` variants | Row-by-row from lazy `ByteString`, plus incremental API | Incremental `Encoding`/`Decoding` runs |
| Schema evolution | optional fields + custom parsers | positional/header mapping by hand | first-class version tag + migration |
| Cross-platform binary stability | n/a (text) | n/a (text) | yes — 32/64-bit, endianness independent |
| Human-inspectable | yes | yes | yes, via generic CBOR→JSON conversion |
| Typical failure mode | lazy bytestring retaining the whole payload | header/record mismatch silently shifting columns | forgetting the version tag, then breaking old data |

## Decision Matrix

| Your task | Use | Why |
|---|---|---|
| REST/GraphQL API payloads | aeson | Instances already exist in your dependency tree |
| Config file parsing at startup | aeson | Config is small, human-edited, and needs good error messages |
| Importing a 2 GB vendor CSV nightly | cassava | Record-level decoding without an AST |
| Exporting a report for a spreadsheet | cassava | Encoder is trivial and matches what Excel expects |
| On-disk cache / event log / queue payloads | serialise | Compact, stable, migration-aware |
| Wire format between two of your own services | cborg (via serialise) | Cheaper than JSON text on both CPU and bytes |
| Audit data a human must read | aeson (JSON) | Never make auditors install a CBOR decoder |

## aeson: The Default You Should Understand Before You Rely On It

**aeson 2.3.2.0, BSD-3-Clause, written and maintained in the open at `haskell/aeson`.** The library is a fast JSON codec built around two type classes, and the `Generic` path gets you 90% of the way with no code:

```haskell
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE OverloadedStrings #-}

import Data.Aeson
import GHC.Generics (Generic)

data Invoice = Invoice
  { invoiceId :: Int
  , customer  :: String
  , total     :: Double
  } deriving (Generic, Show)

instance ToJSON Invoice
instance FromJSON Invoice
```

Install it the same way as any Haskell dependency — pick one toolchain and stay on it:

```bash
cabal install --lib aeson            # cabal
# or, in a Stack project, add to package.yaml dependencies:
#   - aeson
```

What the feature list does not tell you:

- **aeson 2.x replaced `HashMap Text Value` with `KeyMap`.** If you have older code doing `Object` manipulation with `HashMap` combinators, the migration is mechanical but unavoidable — and it is the single most common reason people stay pinned to aeson 1.x long past its support window.
- **`decode` on a lazy `ByteString` keeps the whole payload alive** for as long as any decoded value is reachable. For request bodies, read strictly and convert; for large files, stream with the incremental parser instead of `eitherDecode` on a `LBS.readFile`.
- **Derived instances are total, not validating.** A missing field is an error, but a `String` where you expected a bounded integer is not — put validation in a smart constructor and decode into *that*, otherwise every downstream module repeats the same checks.

![Haskell serialization libraries compared: aeson for JSON, cassava for CSV, cborg and serialise for CBOR](/img/screenshots/haskell-serialization-libs.jpg "Haskell — the three serialization paths a typical service ends up needing")

## cassava: CSV Without an AST

**cassava 0.6.0.0, BSD3.** The library's pitch is that CSV is not a document format — it is a stream of rows, and treating it as a tree is how you run out of memory. The upstream README's two-minute example is the whole mental model:

```haskell
{-# LANGUAGE ScopedTypeVariables #-}

import qualified Data.ByteString.Lazy as BL
import Data.Csv
import qualified Data.Vector as V

main :: IO ()
main = do
    csvData <- BL.readFile "salaries.csv"
    case decode NoHeader csvData of
        Left err -> putStrLn err
        Right v -> V.forM_ v $ \ (name, salary :: Int) ->
            putStrLn $ name ++ " earns " ++ show salary ++ " dollars"
```

Two details that decide whether this survives production:

1. **`decode` returns `Either String (Vector a)`** — the error is a `String`, which means a malformed row at line 400,000 gives you a message, not a line number. Wrap it with your own row counter or use the incremental `Data.Csv.Incremental` API, which reports how much input was consumed.
2. **Column mapping is positional unless you opt into headers.** With `HasHeader`, cassava matches on the header row — but a renamed column in next month's export turns into a silent `Left` at runtime, not a compile error. Pin the expected header list and fail loudly at startup rather than at 3 a.m.

For encoding, `encode` and `encodeByName` produce a lazy `ByteString`; that is fine for reports and wrong for anything that must fit in a fixed buffer.

## cborg/serialise: The Only One With a Migration Story

**cborg 0.2.10.0 and serialise 0.2.6.1, BSD3, one repository (`well-typed/cborg`).** This is the pair people skip until they have data on disk from three releases ago. Per the upstream README:

> The `serialise` library uses the CBOR format, via the `cborg` library, which gives it the following benefits: fast serialisation and deserialisation, compact binary format, stable format across platforms (32/64bit, big/little endian), support for backwards compatible deserialisation with migrations, the ability to inspect binary values with generic tools, e.g. for debugging or recovery, including generic conversion into JSON text.

That last clause is the underrated one: **CBOR is not an opaque blob.** You can dump a stored value as JSON with generic tooling when a customer reports a corrupt record, which is more than you can say for a hand-rolled `Binary` instance.

```haskell
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DeriveAnyClass #-}

import Codec.Serialise (Serialise, serialise, deserialise)
import GHC.Generics (Generic)

data Snapshot = Snapshot
  { version :: Word8
  , payload :: [Int]
  } deriving (Generic, Serialise)
```

```haskell
import qualified Data.ByteString.Lazy as BL
import Codec.Serialise (serialise, deserialise)

writeSnapshot :: FilePath -> Snapshot -> IO ()
writeSnapshot path s = BL.writeFile path (serialise s)

readSnapshot :: FilePath -> IO (Either DeserialiseFailure Snapshot)
readSnapshot path = do
  bs <- BL.readFile path
  pure (deserialiseOrFail bs)
```

The discipline that makes it work:

- **Store a version tag as the first field, always.** "Support for backwards compatible deserialisation with migrations" is a capability of the format, not a feature that turns itself on. Your `FromCBOR`/`Serialise` instance has to branch on the tag.
- **Never reorder record fields in a type you have already persisted** without bumping the tag. CBOR is compact *because* it is positional; that is the trade you made when you chose it over JSON.
- **Do not use CBOR for anything a human has to read** — support tickets, audit exports, config files. The generic inspection tooling is for debugging, not for operations.

## Pitfalls and Migration Notes

- **Choosing the format by the language, not by the boundary.** JSON at the edge, CBOR at rest, CSV at import. Mixing them — CBOR between a service and a browser, JSON for a 4 GB cache — is where teams lose weeks.
- **Build cost is not equal.** aeson pulls in `attoparsec`-based machinery and (optionally) `text`/`scientific` heavy paths; adding it to a lean CLI noticeably increases compile time. If a tool only needs to read one small config file, consider a narrower dependency and keep aeson for the services that actually speak JSON.
- **`Generic` deriving hides strictness.** Derived `FromJSON` builds the record lazily; a partially-forced value throws deep inside a handler instead of at the parse site. Add `{-# LANGUAGE StrictData #-}` or bang patterns on the fields that must be evaluated at decode time.
- **Stable-on-disk is a promise you keep with tests.** Golden-file tests — serialize a fixture, compare bytes — are the only thing that catches an accidental field reorder before your users' stored data does.
- **Library swap is cheap only at the edges.** Converting internal storage between JSON and CBOR means touching every persisted file. Do it behind a version tag with a dual-read path, not as a big-bang migration.

## Why Self-Host the Whole Serialization Layer?

Nothing here is a service, and that is the point: serialization sits on the boundary between your data and every third party who wants it. Keeping it in libraries you pin, audit and upgrade on your own schedule — rather than a hosted "data platform" that re-encodes your records — is the same argument as self-hosting a database. You own the format, the version tag, and the migration.

If you are building the surrounding service, our [Haskell web frameworks comparison](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) covers the servers these codecs plug into, the [Haskell build toolchain guide](../2026-09-19-haskell-build-toolchain-cabal-stack-ghcup-hpack/) explains how to pin these dependency versions reproducibly, and the [Haskell testing frameworks comparison](../2026-08-01-haskell-testing-frameworks-hspec-quickcheck-tasty-hunit/) shows where golden-file serialization tests fit. Readers working in another ecosystem will find the same trade-offs in our [Ruby JSON serialization comparison](../2026-07-31-ruby-json-serialization-alba-blueprinter-ams/).

## FAQ

### Is aeson fast enough for a high-throughput service?

For typical service payloads, yes — aeson is competitive with most mainstream JSON implementations, and the bottleneck is nearly always the database or the network. The cases where it is not fast enough are large documents decoded repeatedly or payloads retained lazily; fix those with streaming and strictness before looking for another library.

### Should I use cassava or aeson for a large CSV import?

cassava. aeson would force you to build a JSON-shaped AST for data that is naturally tabular, which multiplies memory and adds a conversion step. Keep cassava for the import, convert into your domain types immediately, and never persist the raw row vector.

### Why would I pick CBOR over JSON for internal storage?

Because it is compact, cheaper to encode and decode, stable across platforms, and — with `serialise` — designed for backwards-compatible reads with migrations. Choose it when both ends of the data are yours and you have a version-tag discipline. Do not choose it when a human or a third-party system must read the bytes.

### How do I evolve a persisted Haskell record without breaking old data?

Add an explicit version field, branch on it in the decoding instance, and keep a decoder for every version you still have on disk. Then cover it with a golden-file test that serializes a known fixture and compares bytes, so a field reorder fails CI instead of production.

### Do all three work with GHC 9.x and current Stackage snapshots?

Yes — all three are actively published on Hackage and tracked in Stackage, with aeson 2.3.2.0, cassava 0.6.0.0 and cborg 0.2.10.0 being the current releases as of October 2026. Pin exact versions in your build plan; the aeson 1.x→2.x transition is the one upgrade that genuinely requires code changes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Haskell Serialization in 2026: aeson vs cassava vs cborg/serialise — Which Belongs in Your Stack?",
  "description": "aeson vs cassava vs cborg/serialise compared on API surface, streaming behaviour, schema migration and build cost, with configs from the upstream repositories.",
  "datePublished": "2026-10-25",
  "dateModified": "2026-10-25",
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
