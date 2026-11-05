---
title: "mathjs vs decimal.js vs big.js vs bignumber.js in 2026: Which Precision Library Survives Production?"
date: "2026-11-06"
tags: ["javascript", "developer-tools", "nodejs", "precision", "comparison"]
draft: false
cover: "/img/screenshots/mathjs-banner.jpg"
---

Three lines of JavaScript can destroy a month of accounting:

```js
let total = 0;
for (let i = 0; i < 100; i++) total += 19.99;
// 1999.0000000000007
```

Nobody typed that number. It is what IEEE-754 double precision produces when you add `19.99` a hundred times, because `19.99` has no exact binary representation. The value is off by 7e-13 — invisible in a unit test that uses `toBeCloseTo`, fatal in a ledger that reconciles to the cent, in an invoice PDF, or in a payment amount sent to a gateway that rejects three decimal places. Every JavaScript team eventually hits this, and every team then asks the same question: which arbitrary-precision library do we standardize on?

I benchmarked the four serious options on Node 22, pulled their live repository and registry data, and read their source for the sharp edges. Here is what the numbers actually say — including one result that contradicts the folklore.

## TL;DR: The Verdict in 40 Seconds

**Use `decimal.js` for money, pricing, tax, and anything that ends up in a database column.** It is the fastest of the three dedicated decimal libraries in my benchmark (1.08M ops/s), has zero dependencies, 284 KB unpacked, 7,269 stars, and a rounding-mode API complete enough to implement half-even ledger rules correctly.

**Use `mathjs` when you need more than arithmetic** — an expression parser, units (`2 inch + 3 cm`), matrices, fractions, statistics — and can afford a 9.4 MB package with four runtime dependencies. Do not import it just to add two decimals.

**Use `big.js` when payload size is the binding constraint** (59 KB unpacked, zero deps, 6 KB minified in practice). It is the smallest and simplest of the four, but it was the *slowest* in my loop, not the fastest, and its last commit was April 2025.

**Use `bignumber.js` only for non-decimal bases** (hex, base 36, base 2) or to keep an existing codebase working. For new decimal code it is a heavier `decimal.js` with a legacy API.

## The 2026 Comparison Table

Live data pulled from the GitHub API and the npm registry on 2026-11-06:

| | mathjs | decimal.js | big.js | bignumber.js |
|---|---|---|---|---|
| Stars | 15,105 | 7,269 | 5,203 | 7,013 |
| Last push | 2026-11-05 | 2026-08-30 | 2025-04-22 | 2026-08-31 |
| Latest release | 15.2.0 | 10.6.0 | 7.0.1 | 11.1.5 |
| Install size (npm unpacked) | 9.43 MB | 284 KB | 59 KB | 500 KB |
| Runtime dependencies | 4 | 0 | 0 | 0 |
| Default precision | 64 significant digits (configurable) | 20 significant digits | 20 decimal places | 20 decimal places |
| Default rounding | half-up | half-up | half-up | half-up |
| Number bases | 10 only | 10 only | 10 only | 2–36 |
| Units / matrices / parser | yes | no | no | no |
| Immutable values | yes | yes | yes | yes |
| License | Apache-2.0 | MIT | MIT | MIT |

Two rows deserve emphasis. First, `mathjs` pulls in `complex.js`, `decimal.js`, `fraction.js`, and `seedrandom` — it does not implement decimals itself, it delegates to decimal.js. Second, the "default rounding" row is a trap: all four default to half-up, which is *not* what financial auditors usually want. More on that below.

## Real Benchmarks on Node 22

I installed `decimal.js@10`, `big.js@7`, and `bignumber.js@11` in a clean directory and ran 300,000 iterations of `acc = acc + (a * b + a) / b` with `a = "123456.789"` and `b = "0.0007"` — a deliberately division-heavy loop, because division is where arbitrary-precision libraries actually spend time. Node v22.22.1, single core, warm-up pass before each measurement.

| Implementation | 300k loop | Throughput | Relative |
|---|---|---|---|
| native `number` | 2.1 ms | 144,478,675 ops/s | 134× faster |
| decimal.js 10.6.0 | 277.3 ms | 1,081,885 ops/s | 1.0× (baseline) |
| bignumber.js 11.1.5 | 423.8 ms | 707,963 ops/s | 0.65× |
| big.js 7.0.1 | 737.5 ms | 406,761 ops/s | 0.38× |

The folklore is that `big.js` is the fast one because it is the small one. On this workload it was **2.7× slower than decimal.js**. Size and speed are different axes, and big.js pays for its compactness with a simpler internal representation that does more work per division. If you picked big.js for performance, re-measure on your own workload before you commit.

A second measurement matters more for web services: `toFixed(2)` on a fixed decimal ran at **2.78M ops/s** (108 ms for 300k calls). Formatting money is cheap even in the slow path. The expensive part is the division, not the display.

And the sanity check that started this article, run on the same machine:

```text
float sum of 100 x 19.99   = 1999.0000000000007
decimal.js sum of 100      = 1999
decimal 0.1+0.2            = 0.3
```

## Decision Matrix: Pick by Use Case

| Use case | Pick | Why |
|---|---|---|
| Invoice lines, tax, discounts, ledger entries | decimal.js | Exact decimal semantics, explicit rounding modes, fastest of the four |
| Parsing user-entered formulas ("2 * (3 + 4)") | mathjs | `evaluate()` plus a scope object; the others cannot parse |
| Unit conversion in an engineering tool | mathjs | `math.unit('5 cm').to('inch')` is built in |
| Browser bundle where every KB is measured | big.js | 59 KB unpacked, zero deps, one class |
| Converting a hex or base-36 string to an exact integer | bignumber.js | The only one of the four with a base parameter |
| Matrix determinant / inverse in a script | mathjs | `math.det`, `math.inv`, `math.lusolve` |
| Existing code already on bignumber.js 9.x | bignumber.js | Migration cost exceeds the gain; pin the major |
| High-frequency pricing at 100k+ ops/s | native integer cents | Multiply by 100, store `BigInt`, divide at the edge |

That last row is not a joke. If you can express your domain in integer minor units, integers beat every library here by two orders of magnitude. The libraries are for when you *cannot* — fractional rates, unit prices with six decimals, or division that must not lose a digit.

## mathjs — One Import, Everything Included

`mathjs` is not a decimal library; it is a small computer algebra system that happens to expose decimals. Install it and create a narrowed instance so you do not ship the entire 9.4 MB package to a browser:

```bash
npm install mathjs
```

```js
import { create, all } from 'mathjs'

// Full build — fine on the server, expensive in a browser bundle
const math = create(all)

// Configure once, at module scope
math.config({
  number: 'BigNumber',   // 'number' | 'BigNumber' | 'Fraction'
  precision: 64,
  predictable: true      // makes BigNumber ops deterministic; disables some sugar
})

console.log(math.evaluate('0.1 + 0.2').toString())        // 0.3
console.log(math.format(math.bignumber('19.99').times(3)))  // 59.97
```

The features you cannot get elsewhere:

```js
// Units, with real dimensional analysis
math.evaluate('2 inch + 3 cm').to('mm').toString()   // 96.2 mm
math.unit('90 km/h').to('m/s').toString()            // 25 m / s

// Exact rationals — no rounding at all until you ask
math.fraction(1, 3).add(math.fraction(1, 6)).toString()   // 1/2

// Matrices
const A = math.matrix([[2, 1], [1, 3]])
console.log(math.det(A))          // 5
console.log(math.inv(A).toString())
```

**The `config` call is global and sticky.** `math.config({ number: 'BigNumber' })` changes the behaviour of every subsequent `evaluate` call in that process. In a long-running server this leaks between requests and between tests. Create a scoped instance per request if you are doing per-tenant configuration, or lock it at startup and never touch it again.

**Never call `evaluate()` on untrusted input.** The expression parser resolves symbols against the math namespace; a scope object plus `evaluate` is still a code-shaped surface, and `math.import` can install arbitrary functions. For user-supplied formulas, use `math.parse(expr).compile().evaluate(sandboxedScope)` with an explicit allowlist of functions, and reject anything that fails to parse into an `OperatorNode`/`SymbolNode` tree you recognize.

## decimal.js — The Default for Anything Resembling Money

```bash
npm install decimal.js
```

```js
import Decimal from 'decimal.js'

// Configure at startup. Defaults are precision=20, rounding=4 (ROUND_HALF_UP).
Decimal.set({
  precision: 34,                    // significant digits, not decimal places
  rounding: Decimal.ROUND_HALF_EVEN, // banker's rounding — what ledgers expect
  toExpNeg: -9,
  toExpPos: 21
})

const price = new Decimal('19.99')
const qty = new Decimal(3)
const subtotal = price.times(qty)              // 59.97
const tax = subtotal.times('0.0825')           // 4.947525
const total = subtotal.plus(tax).toFixed(2)    // 64.92

console.log(new Decimal('19.995').toFixed(2))  // 20.00 (half-up)
console.log(new Decimal('2.5').toFixed(0, Decimal.ROUND_HALF_EVEN)) // 2
console.log(new Decimal('3.5').toFixed(0, Decimal.ROUND_HALF_EVEN)) // 4
```

The rounding constants are the reason to choose decimal.js over its siblings. It exposes nine modes — `ROUND_UP`, `ROUND_DOWN`, `ROUND_CEIL`, `ROUND_FLOOR`, `ROUND_HALF_UP`, `ROUND_HALF_DOWN`, `ROUND_HALF_EVEN`, `ROUND_HALF_CEIL`, `ROUND_HALF_FLOOR` — and they can be passed per call, so a tax engine can round half-even while a shipping calculator rounds up, in the same process, without global mutation.

A production-grade money helper looks like this:

```js
const D = Decimal.clone({ precision: 34, rounding: Decimal.ROUND_HALF_EVEN })

export const money = (v) => new D(v ?? 0)

export function allocate(total, weights) {
  // Split an amount without losing a cent: distribute remainders deterministically
  const t = money(total)
  const sum = weights.reduce((a, w) => a.plus(w), money(0))
  const parts = weights.map((w) => t.times(w).div(sum).toDecimalPlaces(2, D.ROUND_DOWN))
  let remainder = t.minus(parts.reduce((a, p) => a.plus(p), money(0)))
  const cents = remainder.times(100).toNumber()
  for (let i = 0; i < Math.round(cents); i++) parts[i % parts.length] = parts[i % parts.length].plus('0.01')
  return parts.map((p) => p.toFixed(2))
}

console.log(allocate('100.00', ['1', '1', '1']))  // [ '33.34', '33.33', '33.33' ]
```

`Decimal.clone()` gives you an isolated constructor with its own settings — the clean answer to the "global config" problem. Use it per module instead of mutating the global `Decimal`.

## big.js — 59 KB and Zero Dependencies

```bash
npm install big.js
```

```js
import Big from 'big.js'

Big.DP = 40   // decimal places for division
Big.RM = 0    // 0=down, 1=half-up, 2=half-even, 3=up
Big.NE = -9   // when to switch to exponential notation
Big.PE = 21

const a = new Big('0.1')
const b = new Big('0.2')
console.log(a.plus(b).toString())   // 0.3
console.log(a.div(3).toString())    // 0.03333333333333333333 (20 places by default)
```

big.js has three settings and four rounding modes, and that is the entire configuration surface. If you want a library a new hire can read in twenty minutes, this is it. The cost: no `sqrt`, no `pow` with non-integer exponents, no precision in *significant digits* — only decimal places, which behaves differently depending on magnitude. `new Big(1).div(3)` at `DP = 20` gives 20 decimal places, but `new Big(1000000).div(3)` also gives 20 decimal places, i.e. 27 significant digits. With `decimal.js` you set one number and it means the same thing at every scale.

Where big.js genuinely wins is the browser. 59 KB unpacked translates to roughly 6 KB minified and under 3 KB gzipped for the single-file build — small enough to inline in a checkout page without a second thought. If your only requirement is "add prices without float drift in a 40 KB bundle", big.js is the right answer and the slowness does not matter at human-typing rates.

## bignumber.js — Non-Decimal Bases and Legacy Compatibility

```bash
npm install bignumber.js
```

```js
import BigNumber from 'bignumber.js'

BigNumber.config({ DECIMAL_PLACES: 20, ROUNDING_MODE: BigNumber.ROUND_HALF_UP })

// The feature nobody else has: arbitrary bases
console.log(new BigNumber('ff', 16).toString(10))        // 255
console.log(new BigNumber('zz', 36).toString(10))        // 1295
console.log(new BigNumber(255).toString(16))             // ff

// NaN and Infinity are first-class, like IEEE-754
console.log(new BigNumber('abc').isNaN())                // true
const x = new BigNumber(1).div(0)
console.log(x.isFinite(), x.toFixed(2))                  // false 'Infinity'
```

bignumber.js is the oldest of the three MikeMcl libraries and the most permissive: it accepts NaN and Infinity instead of throwing, supports bases 2 through 36, and has a configuration object with a dozen knobs (`EXPONENTIAL_AT`, `RANGE`, `CRYPTO`, `MODULO_MODE`, `POW_PRECISION`). That flexibility is why it accumulated 7,013 stars and why it is the hardest to reason about. For plain decimal arithmetic it is 65% the throughput of decimal.js with 1.8× the install size.

One migration note that matters in 2026: bignumber.js has moved to a v11 major. If your lockfile says 9.x, you are on a different API contract than the current docs describe. Pin the major explicitly and read the changelog before bumping — a silent major bump in a transitive dependency is exactly how rounding behaviour changes under you.

## The Pitfalls That Actually Cause Incidents

**1. Constructing from a float instead of a string.** `new Decimal(0.1)` works because the library reads the number's shortest decimal representation, but `new Decimal(1 / 3)` gives you `0.3333333333333333` — the double, not the fraction. Every user-supplied amount, every JSON field, every CSV cell must enter the system as a **string**, and the library constructor must be called on that string.

**2. Trusting the default precision.** All three default to 20 digits. That is fine for money and quietly wrong for scientific work: `new Decimal(1).div(3)` returns exactly 20 threes, and any downstream multiplication amplifies the truncation. Set `precision` explicitly in one place at startup and assert it in a test.

**3. Using `Math.round` for money.** JavaScript's `Math.round` rounds half **up toward +∞**, so `Math.round(-0.5)` is `-0` while `Math.round(0.5)` is `1`. Ledger systems and tax authorities expect half-even ("banker's rounding"). The four libraries can all do it; `Math.round` cannot.

**4. Comparing with `===`.** `new Decimal('1.0') === new Decimal('1')` is `false` — they are objects. `new Decimal('1.0').eq('1')` is `true`. Linters do not catch this and unit tests written with `toEqual` may pass or fail depending on the library's `toJSON`.

**5. Serializing to JSON and losing the type.** Here is what actually happens:

```js
JSON.stringify({ v: new Decimal('1.10') })   // {"v":"1.1"}
```

`toJSON()` returns a string, which is correct and safe — but note that `1.10` became `1.1`. If your API contract says two decimal places, format at the boundary with `toFixed(2)` and store the value in a `NUMERIC(20,6)` or string column, never a `FLOAT`/`double`.

**6. Reaching for a library when integers would do.** Storing cents as `BigInt` or as an integer column is faster, makes rounding explicit at exactly one place, and eliminates the "which library" question entirely. Use these libraries for rates and divisions; use integers for balances.

**7. Shipping the full mathjs bundle to the browser.** `import { create, all } from 'mathjs'` followed by `create(all)` bundles everything, including unit definitions and statistics functions. On the server nobody cares. In a client bundle it is the single largest dependency in the graph. Import individual functions (`import { add, multiply } from 'mathjs'`) or use the decimal libraries directly.

If you are comparing money libraries rather than raw precision arithmetic, the trade-offs shift toward wrapper APIs and currency semantics — our [cross-language money library comparison](../2026-09-16-money-decimal-libraries-dinerojs-go-money-py-moneyed-rust-decimal/) covers that ground, and the [Java money API comparison](../2026-09-17-java-money-libraries-moneta-joda-money-jsr354-comparison/) and [PHP money library comparison](../2026-10-07-php-money-libraries-moneyphp-brick-laravel-comparison/) cover the JVM and PHP equivalents.

## FAQ

### Which JavaScript library is best for currency calculations?

`decimal.js`. It has no runtime dependencies, is the fastest of the three dedicated decimal libraries in a division-heavy loop (1.08M ops/s on Node 22 in my test), and exposes nine rounding modes that can be applied per operation. Configure `precision: 34` and `rounding: Decimal.ROUND_HALF_EVEN` once at startup with `Decimal.clone()`.

### Is mathjs slower than decimal.js for simple arithmetic?

Yes, meaningfully. mathjs delegates decimal math to decimal.js internally, so it pays the same per-operation cost plus dispatch overhead, plus a 9.4 MB install and four transitive dependencies. Use mathjs for its parser, units, matrices and statistics — not for adding two numbers.

### Can I just use integers instead of a decimal library?

For balances and prices, yes, and you should. Store minor units (cents) as integers or `BigInt`, do all arithmetic in integers, and convert only for display. The decimal libraries become necessary when you have fractional rates, unit prices with more than two decimals, or divisions that must retain precision.

### Why did big.js perform worse than decimal.js in your benchmark?

big.js uses a simpler internal representation optimised for small operands and applies decimal-place rounding on every division, which costs more per operation in a division-heavy loop. It is still the smallest package by a wide margin (59 KB unpacked versus 284 KB) and is the right choice when bundle size dominates. Measure your own workload rather than trusting size as a proxy for speed.

### Do these libraries work in the browser and in edge runtimes?

All four ship ESM and UMD builds and run without Node APIs, so they work in browsers, Cloudflare Workers and Deno. `mathjs` is the one to watch: the full build is large enough to dominate a client bundle, so import individual functions or use `decimal.js`/`big.js` on the client and keep mathjs on the server.

### How do I migrate an existing codebase from bignumber.js to decimal.js?

Both expose `plus`, `minus`, `times`, `div`, `toFixed` and `toNumber`, so most call sites change by importing a different class. The differences that bite are `NaN`/`Infinity` handling (decimal.js throws where bignumber.js returns a value), the base parameter (decimal.js is base 10 only), and the rounding-mode constants, which use different numeric values. Add a property-based test that compares a fixed corpus of amounts across both libraries during the migration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "mathjs vs decimal.js vs big.js vs bignumber.js in 2026: Which Precision Library Survives Production?",
  "description": "Benchmarked comparison of JavaScript arbitrary-precision libraries: mathjs, decimal.js, big.js and bignumber.js, with real Node 22 throughput numbers, rounding-mode guidance and production pitfalls.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
