---
title: "Perl JSON in 2026: Cpanel::JSON::XS vs JSON::PP vs Mojo::JSON Compared"
date: "2026-11-14"
tags: ["perl", "json", "developer-tools", "performance"]
draft: false
cover: "/img/screenshots/perl-json-modules.jpg"
description: "Which Perl JSON module should you ship in 2026? A practical comparison of Cpanel::JSON::XS, JSON::PP and Mojo::JSON — speed, safety, incremental parsing and real benchmarks."
---

# Perl JSON in 2026: Cpanel::JSON::XS vs JSON::PP vs Mojo::JSON Compared

Perl ships with a JSON decoder in its core, yet most production code pulls a module from CPAN anyway — and the choice you make quietly determines whether your API handles 3,000 requests per second or 300. The three modules that matter in 2026 look interchangeable in a tutorial and behave very differently under load, under attack, and inside a Mojolicious app.

**TL;DR:** For anything serving traffic, use **Cpanel::JSON::XS** — it is an actively maintained C/XS implementation (version 4.81, November 2026) with the same API as the classic JSON::XS plus real security options and incremental parsing. Use **JSON::PP** only when you cannot compile C extensions or need `allow_bignum`; it is in Perl's core but pure Perl and an order of magnitude slower. Use **Mojo::JSON** when you are already inside Mojolicious and want zero extra dependencies — not as a general-purpose encoder.

## Side-by-side

| | Cpanel::JSON::XS | JSON::PP | Mojo::JSON |
|---|---|---|---|
| Implementation | C via XS | Pure Perl | Pure Perl |
| Latest version | 4.81 (2026-11-09) | 4.18 (2026-03-20) | Ships with Mojolicious 9.54 (2026-11-07) |
| Where it lives | CPAN, repo `rurban/cpanel-json-xs` (42 stars) | Perl core since 5.14 | Bundled with Mojolicious (`mojolicious/mojo`, 2,762 stars) |
| Install | `cpanm Cpanel::JSON::XS` | Already present | `cpanm Mojolicious` |
| Canonical key ordering | Yes | Yes | No |
| Pretty printing | Yes | Yes | No |
| Incremental / streaming parse | Yes (`incr_parse`) | Yes (`incr_parse`) | No |
| Big number support | No | Yes (`allow_bignum`) | No |
| Typed encoding (`json_type_*`) | Yes (`Cpanel::JSON::XS::Type`) | No | No |
| Max nesting guard | Yes (`max_depth`, default 512) | Yes (`max_depth`) | Limited |
| Typical encode speed | Fastest | Slowest | Middle |
| Maintenance | Active | Perl core | Active |

The pattern is clear: **one module is engineered for throughput, one for portability, and one for convenience inside a framework.**

### Use case → recommended module

| Use case | Pick | Why |
|---|---|---|
| Public API handling thousands of requests per second | Cpanel::JSON::XS | C-level encode/decode loop, reusable encoder object |
| Mojolicious controller returning a small document | Mojo::JSON | Already installed, `encode_json` is one call |
| Shared host or container without a C compiler | JSON::PP | In Perl core since 5.14, no build step |
| Signed or cached responses that must be byte-stable | Cpanel::JSON::XS | `canonical` gives deterministic key order; Mojo has none |
| Newline-delimited stream from a socket or log file | Cpanel::JSON::XS | `incr_parse` returns every complete document per chunk |
| Identifiers larger than 2^53 | JSON::PP | `allow_bignum` keeps them exact via `Math::BigInt` |
| Enforcing an output schema at encode time | Cpanel::JSON::XS | `Cpanel::JSON::XS::Type` type declarations |
| Decoding untrusted client payloads | Cpanel::JSON::XS | `max_depth` guard, no blessed-object conversion |

## Why the fork exists: a short history

Marc Lehmann's `JSON::XS` was the default Perl JSON encoder for over a decade and its API became a de-facto standard — `->new->utf8->canonical->encode($ref)` is recognized by nearly every Perl developer. But the original has not shipped a new release since 2020, and a decade of accumulated edge cases in its blessed-object handling went unfixed.

`Cpanel::JSON::XS` is a fork maintained by Reini Urban that keeps the API byte-for-byte compatible while fixing those edge cases, adding `max_depth` protection and the `Cpanel::JSON::XS::Type` type-checking layer. The 42 stars understate its adoption: it is a dependency of cPanel's own stack and is what most new Perl code means when it says "JSON::XS". In practice, when a tutorial tells you to `use JSON::XS`, you should install `Cpanel::JSON::XS` and change the `use` line.

```bash
# The practical install for any modern Perl service
cpanm Cpanel::JSON::XS

# Verify what you actually got
perl -MCpanel::JSON::XS -e 'print $Cpanel::JSON::XS::VERSION, "\n"'
```

## Cpanel::JSON::XS in practice

### Encoding with a reused object

The single biggest performance mistake in Perl JSON code is constructing a new encoder per call. Build it once at startup — the object holds its options and internal buffers:

```perl
use strict;
use warnings;
use Cpanel::JSON::XS;

my $json = Cpanel::JSON::XS->new->utf8->canonical->allow_nonref;

my $payload = $json->encode({
    id     => 42,
    name   => "widget",
    tags   => [qw(alpha beta gamma)],
    active => \1,          # JSON true, not the string "1"
});

print $payload;
# {"active":true,"id":42,"name":"widget","tags":["alpha","beta","gamma"]}
```

Three options carry most of the weight. `utf8` makes the encoder emit and accept UTF-8 byte strings instead of wide characters — mandatory for HTTP bodies. `canonical` sorts object keys, which makes output deterministic and therefore cacheable and testable. `allow_nonref` permits encoding bare scalars, which you want for JSON endpoints that return `"ok"` or `42`.

### Decoding untrusted input

This is where the fork earns its place. The defaults are safe-ish, but two options are dangerous in a request path:

```perl
use Cpanel::JSON::XS;

my $decoder = Cpanel::JSON::XS->new->utf8->max_depth(64);

my $data = eval { $decoder->decode($request_body) };
if (my $err = $@) {
    die "malformed JSON: $err";
}
die "expected object" unless ref $data eq 'HASH';
```

`max_depth(64)` stops deeply nested payloads from exhausting the stack — a classic denial-of-service vector against naïve decoders. Do **not** enable `allow_blessed` or `convert_blessed` on input from the network: they let a client name a class and have the decoder instantiate it, which turns a data channel into an object-injection surface.

### Streaming newline-delimited records

If you consume a log stream or a chunked API, buffering the whole body is wasteful. `incr_parse` handles partial documents across reads and returns every complete one:

```perl
my $parser = Cpanel::JSON::XS->new->utf8->incr_parse;

while (my $read = read($socket, my $buf, 65_536)) {
    my @records = $parser->incr_parse($buf);
    for my $rec (@records) {
        handle_event($rec);
    }
}
```

This is the feature that makes Cpanel::JSON::XS more than "a faster JSON::PP" — it is the only one of the three you can build a streaming pipeline on without writing your own framing logic.

### Typed encoding

`Cpanel::JSON::XS::Type` adds compile-time-ish type checking so that an accidental string does not silently serialize where a number is required:

```perl
use Cpanel::JSON::XS;
use Cpanel::JSON::XS::Type;

my $json = Cpanel::JSON::XS->new->utf8;
print $json->encode(
    { id => 42, price => 9.99, tags => ["a"] },
    { id => JSON_TYPE_INT, price => JSON_TYPE_FLOAT, tags => JSON_TYPE_ARRAY_STR },
);
```

If the value does not match the declared type, it dies at encode time instead of producing a contract violation your client discovers later. JSON::PP and Mojo::JSON have no equivalent.

## JSON::PP — the safe fallback

JSON::PP has been part of Perl's core since 5.14, which means a fresh Perl install can decode JSON without touching CPAN. That is its whole value proposition, and it is a real one: fat-packed containers, locked-down build hosts, and CGI-era deployments where installing XS modules is an argument you lose.

```perl
use JSON::PP;

my $json = JSON::PP->new->utf8->canonical->pretty;
my $text = $json->encode({ service => "billing", replicas => 3 });
my $data = $json->decode('{"ok":true}');

# Big integers survive as Math::BigInt when requested
my $exact = JSON::PP->new->allow_bignum->decode('{"id":12345678901234567890}');
```

The API deliberately mirrors JSON::XS, so migrating is usually a two-line change: swap the `use` line and the constructor. Everything else — `canonical`, `pretty`, `indent`, `space_before`, `allow_nonref`, `relaxed`, `convert_blessed` — behaves the same.

Two caveats. First, speed: because it is pure Perl, it walks every character in user space. On realistic 1–2 KB payloads it is typically several times slower than the XS encoder, sometimes far more on large documents; the exact ratio depends heavily on payload shape, so measure your own. Second, `allow_bignum` pulls in `Math::BigInt`, which is itself pure Perl and slow — fine for a nightly job, wrong for a request path.

Use JSON::PP when portability beats throughput: installers, build tooling, one-off migration scripts, and test suites that must run on any Perl.

## Mojo::JSON — convenience, not a JSON engine

Mojo::JSON ships with Mojolicious, so if you already run a Mojo app you have a JSON implementation with no additional dependency. Its API is deliberately tiny:

```perl
use Mojo::JSON qw(encode_json decode_json true false);

my $doc = {
    name    => "widget",
    inStock => true,
    tags    => ["alpha", "beta"],
};

my $bytes = encode_json($doc);        # UTF-8 encoded bytes
my $back  = decode_json($bytes);      # plain Perl structures
```

It is fast enough for typical controller work — serializing a response body of a few kilobytes — and it integrates with the framework's error handling and `$c->json` helper. The trade-offs are real, though: there is no `canonical` key ordering (so output is not deterministic across runs), no pretty printer, no incremental parser, and no typed encoding. `true` and `false` return `Mojo::JSON::_Bool` objects that work with Mojo's own encoder but are not interchangeable with `JSON::PP::Boolean` consumed by other libraries.

![Mojolicious logo](/img/screenshots/perl-json-modules.jpg "Mojo::JSON ships with Mojolicious — convenient inside the framework, limited outside it")

A subtle compatibility trap: `encode_json` returns UTF-8 **bytes**, not characters. If you concatenate that into a wider string (for example after `Encode::decode`), you get double-encoded output that looks like `Ã¼` in the browser. Keep the boundary explicit: build the document as characters, let the encoder produce bytes, and hand bytes to the socket.

The rule of thumb: inside Mojolicious, use Mojo::JSON; outside it, use Cpanel::JSON::XS even if Mojo is installed.

## Benchmarking your own payload

Published comparisons use synthetic documents that rarely resemble production traffic. Run this against a real sample from your logs and you get an answer in under a minute:

```perl
use strict;
use warnings;
use Benchmark qw(cmpthese);
use Cpanel::JSON::XS;
use JSON::PP;
use Mojo::JSON qw(encode_json);

my $sample = {
    id     => 918_273,
    name   => "order-service",
    region => "eu-west-1",
    items  => [ map { { sku => "SKU$_", qty => $_ % 7, price => $_ * 1.25 } } 1 .. 25 ],
    meta   => { retries => 2, ok => \1 },
};

my $xs = Cpanel::JSON::XS->new->utf8->canonical;
my $pp = JSON::PP->new->utf8->canonical;

cmpthese(-3, {
    cpanel_xs => sub { $xs->encode($sample) },
    json_pp   => sub { $pp->encode($sample) },
    mojo_json => sub { encode_json($sample) },
});
```

Three habits make the numbers meaningful. Benchmark the **encoder and decoder separately** — they are not equally fast, and most services are read-heavy. Benchmark the **object reuse pattern** you actually ship, not `->new` per call. And test with your **largest realistic document**, because the XS advantage grows with document size; a 200-byte response may show almost no difference, while a 200 KB report will show a large one.

## Pitfalls that bite in production

**UTF-8 double encoding.** The most common Perl JSON bug by far. Decide once whether your strings are characters or bytes; `->utf8` means "input and output are UTF-8 bytes". Mixing `Encode` with `->utf8` produces mojibake that survives all your unit tests and appears only in production data.

**Boolean confusion.** `\1` and `\0` are how the XS family encodes JSON booleans. Passing the number `1` gives you `1`, and the client's `if (doc.active === true)` fails. Always use the reference forms or the module's exported `true`/`false`.

**Numeric precision loss.** JSON has no integer type; large 64-bit IDs can lose precision if any layer treats them as floating point. If your identifiers exceed 2^53, encode them as strings — this is a client-contract decision, not something the module can fix for you.

**Unbounded nesting.** Without `max_depth`, a malicious 10,000-level nested array can crash a worker. Set it to something your domain actually needs (32–64 is generous for most APIs).

**Per-request encoder construction.** `Cpanel::JSON::XS->new->utf8->canonical` inside a request handler allocates options and buffers every time. Hoist it into a package-level lexical or a singleton in your app.

**Assuming Mojo output is stable.** Without `canonical`, key order can change between Perl versions and runs. Anything that hashes or signs a JSON document must use a canonical encoder, or signature verification will fail intermittently.

## FAQ

### Is Cpanel::JSON::XS a drop-in replacement for JSON::XS?

Yes, at the API level. It is a fork that preserves the `->new->utf8->canonical->encode($ref)` interface, so replacing `use JSON::XS` with `use Cpanel::JSON::XS` and updating the constructor name is usually all that is required. The fork adds fixes for blessed-object edge cases, a `max_depth` guard, and the `Cpanel::JSON::XS::Type` typed-encoding layer.

### How much faster is Cpanel::JSON::XS than JSON::PP?

It depends on payload size and shape, but the XS implementation is consistently and substantially faster because the encoding loop runs in C instead of Perl. Rather than trusting a published ratio, run a `Benchmark::cmpthese` comparison against a real sample from your own logs — small responses may show a modest gap while large documents show a dramatic one.

### Can I use JSON::PP without installing anything?

Yes. JSON::PP has been in Perl's core since version 5.14, so `use JSON::PP;` works on a stock Perl installation with no CPAN access. That makes it the right choice for installers, build scripts, and restricted environments — at the cost of throughput.

### Which module supports streaming or incremental JSON parsing?

Both Cpanel::JSON::XS and JSON::PP provide `incr_parse`, which accepts partial input and returns each complete document it can decode. Mojo::JSON has no incremental parser. For newline-delimited JSON pipelines, create the parser once with `incr_parse` and feed it each chunk as it arrives.

### Is it safe to decode JSON from an untrusted client?

It can be, if you configure it defensively: set `max_depth` to a small value, leave `allow_blessed` and `convert_blessed` disabled, and validate the resulting structure before use. `convert_blessed` on network input is an object-injection risk. Also cap request body size at the web-server layer, before the decoder ever sees it.

For related reading, our [Perl web frameworks comparison](../2026-08-01-perl-web-frameworks-mojolicious-dancer2-catalyst-comparison/) covers how Mojolicious, Dancer2 and Catalyst handle serialization, and the [Perl logging libraries guide](../2026-10-25-perl-logging-libraries-log4perl-log-dispatch-log-any/) shows the same trade-off pattern for structured output. If you are building a client instead of a server, see the [Perl HTTP clients review](../2026-10-20-perl-http-clients-lwp-mojo-http-tiny-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Perl JSON in 2026: Cpanel::JSON::XS vs JSON::PP vs Mojo::JSON Compared",
  "description": "Practical comparison of Perl JSON modules in 2026: Cpanel::JSON::XS performance and security options, JSON::PP as a core fallback, and Mojo::JSON inside Mojolicious.",
  "datePublished": "2026-11-14",
  "dateModified": "2026-11-14",
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
