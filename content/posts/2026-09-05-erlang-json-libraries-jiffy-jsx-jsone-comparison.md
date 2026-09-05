---
title: "Erlang JSON Libraries in 2026: jiffy vs jsx vs jsone — Picking the Right JSON Engine"
date: "2026-09-05"
tags: ["erlang", "json", "developer-tools", "performance"]
draft: false
---

Every Erlang service eventually hits the same wall: JSON parsing becomes your hottest code path, and the difference between a NIF-based parser and a pure-Erlang one shows up as milliseconds of scheduler latency under load. The BEAM community has settled on three serious options — **jiffy** (880 stars, the C NIF workhorse), **jsx** (696 stars, the veteran pure-Erlang parser), and **jsone** (294 stars, the actively maintained pure-Erlang contender) — and they are not interchangeable. One runs C code inside your VM. Two don't. One has been dormant since 2024. Choosing wrong means rediscovering these differences under production traffic.

The decision is more subtle than "NIF is faster." Jiffy's own README is candid: it's *not* the fastest JSON library in standard benchmarks — it optimizes for correctness and for not disrupting the rest of your system. Meanwhile jsone's decoder is written in continuation-passing style specifically to exploit Erlang's sub-binary optimization, and it ships `try_decode/1` — a streaming API that neither rival matches.

**TL;DR:** For high-throughput internal services parsing large payloads, choose **jiffy** — it's the fastest in scheduler-contention benchmarks, battle-tested, and still maintained (last push July 2026, 2.x line). For new pure-Erlang projects, or when you need `try_decode`, atom-key control, or must deploy without a C toolchain, choose **jsone** — smaller but genuinely active (last push May 2026). Do **not** start new work on **jsx**: it's a fine parser, but the repository has been quiet since June 2024 and the other two cover its ground with better maintenance. If you're on Elixir, this choice mostly happens for you — Jason can delegate its heavy lifting to jiffy as a native backend.

## The Three JSON Engines at a Glance

| Dimension | jiffy | jsx | jsone |
|---|---|---|---|
| Implementation | C NIF | Pure Erlang | Pure Erlang |
| GitHub repo | davisp/jiffy | talentdeficit/jsx | sile/jsone |
| Stars | 880 | 696 | 294 |
| Latest tag | 2.0.2 | v3.1.0 | v0.3.3 (hex.pm 1.x line) |
| Last repo push | 2026-07-01 | 2024-06-26 | 2026-05-21 |
| License | MIT | MIT | MIT |
| Maintenance status | Active | Dormant | Active (slow cadence) |
| Default object format | Proplist (`{[{K,V}]}`) | Map (`#{}`) | Map (`#{}`) |
| `try_decode` / non-fatal errors | No | No | Yes (`try_decode/1`, `try_encode/1`) |
| Pretty printing | `pretty` option | Yes | `{indent, N}, {space, N}` |
| Inline pre-encoded JSON | `{json, IoData}` | — | `{json, IOList}` / `{json_utf8, Chars}` |
| Atom key conversion | Manual | Manual | `{keys, attempt_atom}` / `{keys, atom}` |
| Scheduler behavior | Yields via `bytes_per_red` | Pure (no NIF risk) | Pure (no NIF risk) |
| RFC compliance | JSON (UTF-8 binaries only) | JSON | RFC 7159, UTF-8 |

## Use Case → Decision Matrix

| Use Case | Recommended Library | Reason |
|---|---|---|
| Parse 10 MB+ payloads in a busy service | jiffy | Scheduler benchmark: 24x concurrent encode/decode at ~140 ms vs ~817 ms (jsone) and ~1,655 ms (jsx) |
| Zero-dependency pure-Erlang deployment | jsone | No NIF compilation; works anywhere the BEAM runs |
| Stream/parse multiple JSON values from one buffer | jsone | `try_decode/1` returns the unconsumed remainder — jsx and jiffy can't |
| Existing codebase already on jsx | jsx (keep), migrate gradually | v3.1.0 works fine; just don't add new subsystems on it |
| Elixir project (Phoenix/LiveView API) | jiffy as Jason backend | Jason automatically uses jiffy when available for NIF-speed decoding |
| CLI tools, scripts, small config parsing | jsone | Fast startup, no C extension, forgiving options |
| Maximum single-core decode throughput | jiffy | ~12.5K IPS on UTF-8 unescaped data in jsone's own benchmark table |

## jiffy: The NIF Workhorse

Jiffy has one job — decode and encode JSON as fast as possible without wrecking your VM — and its design choices all serve that goal. It's a NIF that *yields*: instead of grabbing a dirty scheduler and blocking, it processes in chunks controlled by `{bytes_per_red, N}`, returning to the Erlang scheduler to stay responsive. The README's benchmark (via nickva/bench) shows why this matters — concurrent encode/decode across 12-24 schedulers barely degrades:

```
[jiffy]
  1x encdec       n=309 p50=38.3ms p95=51.9ms p99=57.4ms max=66.5ms
  24x encdec      n=306 p50=80.2ms p95=111.8ms p99=118.8ms max=140.1ms

[jsone]
  24x encdec      n=52 p50=440.1ms p95=700.3ms p99=773.3ms max=817.3ms

[jsx]
  24x encdec      n=24 p50=1181.3ms p95=1479.0ms p99=1558.1ms max=1654.7ms
```

Under 24x contention, jiffy finishes ~6x faster than jsone and ~12x faster than jsx. The API is deliberately small:

```erlang
1> jiffy:decode(<<"{\"foo\": \"bar\"}">>).
{[{<<"foo">>,<<"bar">>}]}
2> Doc = {[{foo, [<<"bing">>, 2.3, true]}]}.
{[{foo,[<<"bing">>,2.3,true]}]}
3> jiffy:encode(Doc).
<<"{\"foo\":[\"bing\",2.3,true]}">>
```

Note the gotcha baked into the very first example: `jiffy:encode/1` returns an **iolist**, not necessarily a binary. And decode returns *proplists* by default — objects come back as `{[{<<"foo">>,<<"bar">>}]}`, not maps, unless you pass `return_maps`. That's the single most common source of confusion when teams migrate to jiffy.

Decode options cover real-world pain: `return_maps` for map output, `{null_term, Term}` or `use_nil` to control `null`, `dedupe_keys` for repeated object keys (mirroring other parsers), `return_trailer` to decode multiple terms from one binary, and `copy_strings` — which prevents decoded strings from keeping the whole input document alive in memory (a subtle but brutal memory-leak source on large payloads).

Encode is equally pragmatic: `pretty` for indented output, `uescape` for 7-bit clean ASCII, `force_utf8` to repair broken surrogate pairs, and `escape_forward_slashes` for embedding JSON in HTML contexts.

Jiffy's EJSON data format is its own dialect of "Erlang terms stand for JSON":

```
Erlang                          JSON            Erlang
null                       -> null         -> null
<<"hi">>                   -> "hi"         -> <<"hi">>
hi                         -> "hi"         -> <<"hi">>
{[{foo, bar}]}             -> {"foo":"bar"} -> {[{<<"foo">>,<<"bar">>}]}
#{<<"foo">> => <<"bar">>}  -> {"foo":"bar"} -> #{<<"foo">> => <<"bar">>}
```

Atoms encode as strings; maps and proplists both work. One uniquely useful feature: `{json, IoData}` splices pre-encoded JSON straight into output without re-parsing — ideal for caching encoded fragments (e.g., a serialized object fetched from a database):

```erlang
1> jiffy:encode([1, {json, <<"{\"cached\":true}">>}, 3]).
<<"[1,{\"cached\":true},3]">>
```

The caller is responsible for that fragment being well-formed — jiffy does not validate it. Unicode policy is blunt: "Jiffy only understands UTF-8 in binaries. End of story."

## jsx: The Veteran You Shouldn't Start On

Jsx (inspired by YAJL) was the pure-Erlang parser of choice for years — RabbitMQ's management UI and countless OTP applications have shipped it. It's added to a rebar3 project the standard way:

```erlang
{erl_opts, [debug_info]}.
{deps, [
       {jsx, "~> 3.0"}
]}.
```

Its API is clean and map-first (note: jsx 3.x defaults to maps, unlike jiffy):

```erlang
1> jsx:decode(<<"{\"library\": \"jsx\", \"awesome\": true}">>, []).
#{<<"awesome">> => true, <<"library">> => <<"jsx">>}
2> jsx:decode(<<"{\"library\": \"jsx\", \"awesome\": true}">>, [{return_maps, false}]).
[{<<"library">>,<<"jsx">>},{<<"awesome">>,true}]

1> jsx:encode(#{<<"library">> => <<"jsx">>, <<"awesome">> => true}).
<<"{\"awesome\":true,\"library\":\"jsx\"}">>
```

It also ships handy utilities: `jsx:is_json/1` and `jsx:is_term/1` to check validity without a full parse, plus `jsx:minify/1` for compacting JSON. As a *library*, jsx is perfectly competent — v3.1.0 is the stable line, and its error messages are decent.

The problem is trajectory, not quality. The talentdeficit/jsx repository's last push was June 2024 — over two years of silence at the time of writing. Erlang itself has moved on (OTP 27 and 28 brought big performance and typing changes), and jsx has no maintainer visibly reacting to any of it. In the benchmark table above, it trails both alternatives by wide margins. If you're touching a legacy jsx codebase, leave it running — but new projects should pick jiffy or jsone, and teams planning multi-year investments should budget a migration.

## jsone: The Quiet Contender That Keeps Shipping

Jsone (by the same author as the `sile` family of BEAM libraries) is pure Erlang with an RFC 7159-compliant decoder written in continuation-passing style — a technique that lets it delay sub-binary creation and avoid copying decoded strings out of the input. That makes it surprisingly fast for a non-NIF parser, and the README's own benchmark table (run against the Poison benchmark suite) shows jiffy leading encode throughput while jsone consistently beats jsx on both encode and decode.

Where jsone genuinely differentiates is its API surface. `try_decode/1` returns the unconsumed tail of the input — a streaming primitive neither jiffy nor jsx offers:

```erlang
1> jsone:decode(<<"[1,2,3]">>).
[1,2,3]

2> jsone:decode(<<"{\"1\":2}">>).
#{<<"1">> => 2}

3> jsone:try_decode(<<"[1,2,3] \"next value\"">>).
{ok,[1,2,3],<<" \"next value\"">>}

% non-fatal errors return {error, Reason} instead of raising
4> jsone:try_decode(<<"1.x">>).
{error,{badarg,[{jsone_decode,number_fraction_part_rest,[<<"x">>,1,1,0,[],<<>>],[{line,228}]}]}}
```

Error handling is uniformly dual-mode: `decode/1` and `encode/1` raise exceptions; `try_decode/1` and `try_encode/1` return `{error, Reason}` tuples — no try/catch needed for expected failure paths.

Object format is configurable per call — map (default), tuple, or proplist — which eases interop with code written against jiffy or jsx conventions:

```erlang
> jsone:decode(<<"{\"1\":2}">>, [{object_format, tuple}]).
{[{<<"1">>, 2}]}

> jsone:decode(<<"{\"1\":2}">>, [{object_format, proplist}]).
[{<<"1">>, 2}]
```

Atom handling is where jsone shows real design maturity. Decoding JSON keys to atoms is an atom-table leak waiting to happen if you parse untrusted input — jsone's `{keys, attempt_atom}` only converts keys that already exist as atoms, and falls back to binaries otherwise. That single option prevents a whole class of production outages.

Encoding extras include pretty printing with configurable indent and spacing, datetime encoding, inline `{json, IOList}` fragments, `undefined_as_null`, and fine-grained float formatting:

```erlang
> jsone:encode(1.23).
<<"1.22999999999999998224e+00">>   % default: scientific notation

> jsone:encode(1.23, [{float_format, [{decimals, 4}, compact]}]).
<<"1.23">>

> jsone:encode(undefined, [undefined_as_null]).
<<"null">>
```

That float behavior is a trap worth calling out: jsone emits floats in scientific notation by default, so `1.23` round-trips as `1.22999999999999998224e+00`. If you're producing JSON for systems that expect plain decimals, you must set `float_format` explicitly — or your API consumers will file bugs about "weird exponent numbers."

## Performance and Memory Pitfalls Nobody Warns You About

1. **NIFs are not free.** Jiffy yields politely, but a NIF still executes C on BEAM scheduler threads. Under heavy load, an uncooperative NIF (or one doing large allocations) can introduce latency spikes across *all* processes on that scheduler. If your service is latency-sensitive with mixed workloads, benchmark jiffy under contention — the `bench_scheduling.sh` methodology from nickva/bench is the right tool.
2. **Sub-binary retention is a silent memory leak.** When jiffy or jsone decode strings as sub-binaries of the input, every decoded string keeps the entire original document alive in memory. Parse a 50 MB file, keep one small field, and you retain ~50 MB. jiffy's `copy_strings` option exists precisely for this; enable it when documents are large and results outlive the parse.
3. **`return_maps` changes everything.** jiffy's default proplist output and jsx/jsone's default map output mean code written against one library's shapes breaks subtly against another's. Pick your object format explicitly at the call site and encode it in a wrapper module.
4. **Floats need explicit formatting (jsone).** Default scientific notation for floats will corrupt naive round-trips. Set `{float_format, [{decimals, N}]}` for any float you emit to outside systems.
5. **Atom keys can crash your node.** Decoding untrusted keys straight to atoms grows the atom table without bound — OTP eventually kills the node. jsone's `attempt_atom` handles this safely; with jiffy or jsx you must do the conversion yourself, deliberately.
6. **jsx's silence is a risk factor, not a bug.** v3.1.0 works. But with no pushes since mid-2024, security-relevant fixes and OTP 28 compatibility land nowhere. Track it; plan around it.
7. **Inline JSON fragments skip validation.** Both jiffy's `{json, IoData}` and jsone's `{json, IOList}` splice raw bytes into output without checking them. Only use them with data you produced or validated earlier — user input straight into a fragment is how broken JSON ships to your API consumers.
8. **UTF-8 is the only encoding.** jiffy accepts only UTF-8 binaries, full stop. Non-UTF-8 legacy payloads need transcoding before they reach any of these three libraries.

Erlang's JSON layer sits underneath the Elixir ecosystem too — our [Elixir JSON libraries comparison](../2026-07-25-elixir-json-libraries-jason-poison-jsex-jsonrs/) covers the higher-level APIs built on these engines. For the HTTP servers that typically sit in front of JSON parsing, see the [Cowboy vs MochiWeb vs Yaws guide](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/). And if you're choosing a JSON parser in other languages, our [simdjson vs RapidJSON vs orjson benchmark roundup](../2026-06-19-self-hosted-json-parser-libraries-simdjson-rapidjson-orjson-ultrajson/) shows how C, Python, and Rust parsers approach the same tradeoffs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Erlang JSON Libraries in 2026: jiffy vs jsx vs jsone — Picking the Right JSON Engine",
  "description": "Comparison of Erlang's three JSON libraries in 2026: jiffy (C NIF, scheduler-friendly, fastest under contention), jsone (pure Erlang, try_decode streaming API, active), and jsx (veteran, dormant since 2024). Includes real benchmark data, code examples, and memory/performance pitfalls.",
  "datePublished": "2026-09-05",
  "dateModified": "2026-09-05",
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

**Is jiffy faster than pure-Erlang parsers in real workloads?**
In scheduler-contention benchmarks published in jiffy's README, jiffy completes 24x-concurrent encode/decode in ~140 ms versus ~817 ms for jsone and ~1,655 ms for jsx. On single-core decode throughput, jsone's own benchmark table shows jiffy leading on most large inputs (e.g., ~12.5K inputs/sec on UTF-8 unescaped data). The gap narrows on small documents, where pure-Erlang overhead is less significant.

**Can I use jsone and jiffy in the same project?**
Yes — they're just Erlang applications. A common pattern is jiffy for internal large-payload parsing and jsone where you want `try_decode` or non-fatal error handling. Both are MIT-licensed with no conflicting dependencies.

**Which library does Elixir's Jason use?**
Jason can use jiffy as its native (NIF) decoder backend when jiffy is present in the build, falling back to a pure-Erlang decoder otherwise. So Elixir projects indirectly benefit from jiffy's performance without calling it directly.

**Is jsx abandoned?**
The talentdeficit/jsx repository has not had a push since June 2024. The v3.1.0 release works and remains widely deployed, but with no visible maintenance activity, starting new subsystems on jsx is a long-term risk. jiffy and jsone are both actively maintained alternatives.

**How do these libraries handle JSON objects with duplicate keys?**
jiffy offers `dedupe_keys` (last value wins, mirroring most parsers); jsone keeps the last occurrence in map output; jsx follows standard behavior. If you must detect duplicates (e.g., for security validation), you need a custom decode pass — none of the three report duplicates by default.

**Do I need a C compiler to use jiffy?**
Yes — jiffy is a NIF and requires compilation against your OTP installation. If you deploy to restricted environments, run on Windows without a toolchain, or use Nerves-style minimal builds, prefer the pure-Erlang jsone or jsx.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
