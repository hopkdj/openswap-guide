---
title: "Moneta vs Joda-Money in 2026: Which Java Money Library Should You Actually Use?"
date: "2026-09-17"
tags: ["java", "money", "fintech", "libraries", "jsr-354"]
draft: false
cover: "/img/screenshots/javamoney-logo.jpg"
description: "JSR-354 Moneta vs Joda-Money compared for Java in 2026: real Maven coordinates, real API code from the official user guide, official benchmark numbers and the rounding traps nobody warns you about."
---

Every Java team eventually ships an invoice that is off by one cent. The cause is almost never a logic error — it is a `double`. Money stored in a binary floating-point primitive accumulates error the moment you divide, and by the time a rounding step runs, the value has already drifted. The fix is not discipline; it is putting money behind a type that refuses to lose precision. In Java there are exactly two libraries worth considering for that job: **JSR-354 / Moneta** and **Joda-Money**. They make opposite architectural bets, and the wrong choice costs you either a heavyweight API you never use or a missing feature you have to build yourself.

## TL;DR — Quick Verdict

Take **Moneta**, the JSR-354 reference implementation (375 stars, last pushed July 2026), if you want the standardised API: two amount implementations, pluggable exchange-rate providers, cash rounding queries, and streaming-friendly monetary functions. Take **Joda-Money** (678 stars, last pushed December 2025) if you want a small, dependency-free base layer that stores amounts correctly and deliberately does nothing else. Joda-Money's README is unusually candid about the trade-off: it "does not provide, nor is it intended to provide, monetary algorithms beyond the most basic and obvious" because requirements "vary widely between domains".

If you have one currency, one format and a handful of additions, `BigDecimal` with a documented scale is a legitimate answer. These libraries earn their place when you have conversion, rounding policy or multi-currency reporting.

| Dimension | Moneta (JSR-354 RI) | Joda-Money |
| --- | --- | --- |
| GitHub stars | 375 | 678 |
| Last commit | Jul 2026 | Dec 2025 |
| Maven coordinates | `org.javamoney:moneta` (type `pom`, version `1.4.5`) | `org.joda:joda-money` |
| Java baseline | 1.4.x → Java 8+; 1.5.x → Java 11+ | 1.x → Java 8+; 2.x → Java SE 21+ |
| Dependencies | JSR-354 API plus implementation modules | no mandatory runtime dependencies |
| Core types | `MonetaryAmount` with `Money` (BigDecimal) and `FastMoney` (long, fixed scale) | `Money` and `BigMoney`, `CurrencyUnit` |
| Currency conversion | built in — ECB, ECB-HIST, ECB-HIST90, IMF, IDENT providers | none; you supply the rate |
| Rounding policy | `MonetaryRoundings`, `RoundingQueryBuilder` including currency cash rounding | `RoundingMode` passed per operation |
| Extensibility | SPI providers via `ServiceLoader` (currencies, roundings, rates) | add your own operators on top |
| Best fit | apps with conversion, rounding policy or multi-currency reporting | apps that need a correct amount type and nothing more |

## Decision Matrix: Pick in Ten Seconds

| Your situation | Use this | Why |
| --- | --- | --- |
| Multi-currency invoices where rates change daily | Moneta | pluggable rate providers and a default provider chain |
| You must apply Swiss cash rounding to CHF totals | Moneta | `RoundingQueryBuilder` supports named roundings such as `cashRounding` |
| You want money to be a value type in one currency, with no framework | Joda-Money | no mandatory dependencies, explicit rounding per call |
| You need percentages, permils or reciprocal calculations on amounts | Moneta + `javamoney-lib` | `MonetaryUtil` and the calculation library provide them |
| You need financial formulas (amortisation, interest) out of the box | `javamoney-lib` | the `javamoney-calc` module exists for that purpose |
| You need Jakarta CDI injection of money services | Moneta + `javamoney-cdi` | the CDI integration ships as a separate module |

![JavaMoney project logo from the official GitHub organisation](/img/screenshots/javamoney-logo.jpg "The JavaMoney organisation logo, covering the JSR-354 API, Moneta and the extension libraries")

## Moneta — The Standardised Stack

Moneta is the reference implementation of JSR 354, and the API is split from the implementation so other vendors can supply their own. The public surface lives in `javax.money`: `CurrencyUnit`, `MonetaryAmount`, `MonetaryOperator`, `MonetaryQuery`, `MonetaryRounding`, with singleton accessors `MonetaryCurrencies`, `MonetaryAmounts` and `MonetaryRoundings`. Adding it is a single Maven dependency — note the `pom` type, because `moneta` is an aggregator:

```xml
<dependency>
  <groupId>org.javamoney</groupId>
  <artifactId>moneta</artifactId>
  <version>1.4.5</version>
  <type>pom</type>
</dependency>
```

The same dependency in Gradle and SBT, straight from the project README:

```groovy
compile group: 'org.javamoney', name: 'moneta', version: '1.4.5', ext: 'pom'
```

```scala
libraryDependencies += "org.javamoney" % "moneta" % "1.4.5" pomOnly()
```

Currency units come from the `Monetary` singleton, and every JDK currency code is mapped by default:

```java
CurrencyUnit currencyCHF = Monetary.getCurrency("CHF");
CurrencyUnit currencyUSD = Monetary.getCurrency("USD");
CurrencyUnit currencyEUR = Monetary.getCurrency("EUR");

// all currently known currencies
Collection<CurrencyUnit> allCurrencies = Monetary.getCurrencies();
```

The part Joda-Money cannot match is conversion. Rates are fetched through `ExchangeRateProvider` instances obtained from `MonetaryConversions`, and providers can be chained so currency coverage falls through in priority order:

```java
// single provider
ExchangeRateProvider rateProvider = MonetaryConversions.getExchangeRateProvider("IMF");
ExchangeRate chfToUsdRate = rateProvider.getExchangeRate("CHF", "USD");

// compound provider: try ECB first, fall back to IMF
ExchangeRateProvider compound = MonetaryConversions.getExchangeRateProvider("ECB", "IMF");
ExchangeRate eurToChfRate = compound.getExchangeRate("EUR", "CHF");

// default provider chain
ExchangeRateProvider defaults = MonetaryConversions.getExchangeRateProvider();
```

Converting an amount is then a `MonetaryOperator` application. A `CurrencyConversion` is bound to a target currency and an underlying provider:

```java
CurrencyConversion conversion = rateProvider.getCurrencyConversion("CHF");

MonetaryAmount amountInUSD = ...;
MonetaryAmount amountInCHF = amountInUSD.with(conversion);
```

Moneta ships five rate providers: **ECB** (daily reference rates), **ECB-HIST90** (last 90 days of history), **ECB-HIST** (back to 1999), **IMF** (daily rates for almost all major currencies, internally derived through the SDR unit), and **IDENT** (factor 1.0 for same-currency pairs). The default chain is **IDENT, ECB, IMF, ECB-HIST, ECB-HIST90** — first provider to return a rate wins, which is exactly why chain order is a correctness decision and not a plumbing detail.

Rounding is query-based rather than hardcoded. You ask for a rounding by currency and named policy, then apply it:

```java
MonetaryRounding rounding = Monetary.getRounding(
  RoundingQueryBuilder.of()
      .setCurrency(Monetary.getCurrency("CHF"))
      .set("cashRounding", true)
      .build()
);

MonetaryAmount amt = ...;
MonetaryAmount roundedAmount = amt.with(rounding); // CHF cash rounding applied
```

Custom currencies go through the SPI. A Bitcoin provider means implementing `CurrencyProviderSpi` and registering it as a service:

```java
public final class BitCoinProvider implements CurrencyProviderSpi {

    private Set<CurrencyUnit> bitcoinSet = new HashSet<>();

    public BitCoinProvider() {
       bitcoinSet.add(CurrencyUnitBuilder.of("BTC", "MyCurrencyBuilder").build());
       bitcoinSet = Collections.unmodifiableSet(bitcoinSet);
    }

    @Override
    public Set<CurrencyUnit> getCurrencies(CurrencyQuery query) {
       if (query.isEmpty()
           || query.getCurrencyCodes().contains("BTC")
           || query.getCurrencyCodes().isEmpty()) {
           return bitcoinSet;
       }
       return Collections.emptySet();
    }
}
```

That class must be declared on the classpath in `META-INF/services/javax.money.spi.CurrencyProviderSpi` for `ServiceLoader` to find it, or registered as a CDI bean if the bootstrap uses CDI. Alternatively, `CurrencyUnitBuilder` can register on creation:

```java
CurrencyUnitBuilder.of("FLS22", "MyCurrencyProvider")
    .setDefaultFractionDigits(3)
    .build(true /* register */);
```

### The Two Amount Implementations, With Real Numbers

Moneta gives you `Money` (backed by `BigDecimal`, arbitrary precision) and `FastMoney` (backed by a `long` with a fixed scale of 5). The official user guide includes a benchmark that runs the same operation chain — add, subtract, multiply, divide, round — 100,000 times:

```text
Duration for 100000 operations (Money,BD): 2107 ms (21 ns per loop) -> EUR 1657407.95
Duration for 100000 operations (FastMoney,long): 1011 ms (10 ns per loop) -> EUR 1657407.95000
```

`FastMoney` is roughly twice as fast and, as the guide itself notes, can only represent scales up to 5. The guide is equally clear about the danger of mixing them: "mixing of different amount implementation types may require internal rounding to be performed. Whereas the compatibility of precision is ensured, scale may be reduced silently as needed." The recommended mitigation is explicit conversion before any operation, using the static `from()` methods each implementation provides:

```java
Money money = Money.from(myMoney);
FastMoney fastMoney = FastMoney.from(myMoney);

money = Money.from(fastMoney);
fastMoney = FastMoney.from(money);
```

For collections and streams, `MonetaryFunctions` provides collectors and comparators — `groupByCurrencyUnit()`, `summarizingMonetary()`, `sortCurrencyUnit()` — so a multi-currency report is a stream pipeline rather than a hand-written accumulator. `MonetaryUtil` adds `percent()`, `permil()`, `reciprocal()`, `minorPart()` and `majorPart()`.

## Joda-Money — The Base Layer, On Purpose

Joda-Money takes the opposite bet: it stores amounts precisely and refuses to guess at your business rules. It has no mandatory runtime dependencies (a compile-time dependency on Joda-Convert is not needed at runtime), which keeps it usable in environments where an SPI framework is unwelcome. The README example is the whole API in miniature:

```java
// create a monetary value
Money money = Money.parse("USD 23.87");

// add another amount with safe double conversion
CurrencyUnit usd = CurrencyUnit.of("USD");
money = money.plus(Money.of(usd, 12.43d));

// subtracts an amount in dollars
money = money.minusMajor(2);

// multiplies by 3.5 with rounding
money = money.multipliedBy(3.5d, RoundingMode.DOWN);

// compare two amounts
boolean bigAmount = money.isGreaterThan(dailyWage);

// convert to GBP using a supplied rate
BigDecimal conversionRate = ...;  // obtained from code outside Joda-Money
Money moneyGBP = money.convertedTo(CurrencyUnit.GBP, conversionRate, RoundingMode.HALF_EVEN);

// use a BigMoney for more complex calculations where scale matters
BigMoney moneyCalc = money.toBigMoney();
```

Two design details matter. First, `RoundingMode` is a required argument wherever rounding can occur — you cannot accidentally inherit a default. Second, `convertedTo` takes the rate as a parameter and there is no rate provider infrastructure at all: fetching and refreshing rates is your problem, which is a feature if you already have a treasury data pipeline and a liability if you hoped the library would solve it.

The version split is worth checking before you upgrade. The 2.x branch requires **Java SE 21 or later**; the 1.x branch supports Java SE 8 and up. The 2.x line is API-compatible with 1.x apart from the Java baseline and the `module-info.class`, so the migration is mostly a toolchain decision — but if you are still on Java 11 or 17, stay on 1.x deliberately rather than discovering it during a build.

## javamoney-lib — The Extensions You Will Probably Need

Moneta covers the API; the separate `javamoney-lib` project covers the financial glue, adding APIs and SPIs implemented as proof of concept during JSR development. Its modules are worth knowing by artifact name:

- **`javamoney-calc`** — a set of monetary calculations and financial formulas.
- **`javamoney-exchange`** — extra conversion resources, including `javamoney-exchange-frb` for the US Federal Reserve feed and `javamoney-exchange-yahoo`.
- **`javamoney-cdi`** — JavaMoney integration with Jakarta CDI in Java SE mode.

If your requirements include amortisation schedules, interest formulas or a Fed-sourced rate feed, budget for this library from the start rather than discovering mid-sprint that Moneta's core has no formula library.

## The Pitfalls That Actually Bite

**Never mix `Money` and `FastMoney` in a calculation chain.** The official guide states that mixing implementations "may require internal rounding" and that "scale may be reduced silently as needed". Convert once, explicitly, with `Money.from()` or `FastMoney.from()`, before the arithmetic. Silent scale loss is the exact failure mode these libraries exist to prevent.

**Rate providers reach the network.** ECB and IMF providers hit external feeds. A unit test that calls `MonetaryConversions.getExchangeRateProvider()` and expects a live rate will fail in CI the day the feed is slow, or in a restricted network. Register `IDENT` in tests, inject a stub `ExchangeRateProvider`, or use a locally seeded cash rounding; treat live rates as an integration concern. If you would rather own the rate feed entirely, our [self-hosted currency exchange rate API guide](../2026-06-09-self-hosted-currency-exchange-rate-apis-frankfurter-exchange-api-guide/) covers the self-hosted options, and you can then hand the rate to Joda-Money as a `BigDecimal` and skip provider infrastructure completely.

**`BigDecimal.divide` without a `MathContext` throws.** A non-terminating decimal expansion raises `ArithmeticException`. Every division on a monetary amount needs a declared scale or rounding mode — which is why JSR-354 routes division through rounding queries and Joda-Money requires a `RoundingMode` in `multipliedBy` and `convertedTo`.

**Currency fraction digits are not always two.** JPY has zero fraction digits and some currencies use three, which is why `CurrencyUnitBuilder.setDefaultFractionDigits(3)` exists. Hardcoding `setScale(2)` in a multi-currency system produces off-by-one-cent reports for currencies you did not test.

**`javax.money` is not a Jakarta namespace.** The API packages are `javax.money`, `javax.money.format`, `javax.money.spi` — a blanket `javax` → `jakarta` rename during a Jakarta EE migration will break your imports. Rename what the container requires and leave money alone.

**SPI registration is easy to forget.** A custom `CurrencyProviderSpi` or `RoundingProviderSpi` that is not listed in `META-INF/services/...` is simply invisible, and the failure looks like "my currency does not exist" rather than a configuration error.

**Serialization and persistence need a plan.** A `MonetaryAmount` is not a JDBC type, and mapping it through an ORM or a JSON layer requires a converter. On the JSON side, our [Java JSON library comparison](../2026-06-22-java-json-libraries-jackson-gson-moshi-guide/) maps onto the serialization choices; on the validation side, amounts that arrive from users still need [bean validation](../2026-07-04-java-validation-libraries-hibernate-validator-jakarta-yavi-valiktor/) before they reach a monetary type.

**Fixed-point is a separate axis.** Choosing JSR-354 or Joda-Money settles dimensional and rounding policy, not binary representation in downstream systems. Our [fixed-point arithmetic library comparison](../2026-06-19-fixed-point-arithmetic-libraries-libfixmath-fpm-cnl-shopspring-guide/) and the cross-language [money and decimal library round-up](../2026-09-16-money-decimal-libraries-dinerojs-go-money-py-moneyed-rust-decimal/) cover that layer, including how Go, Python and JavaScript ecosystems handle the same problem.

## FAQ

**Should I use Moneta or Joda-Money for a Java application in 2026?**
Use Moneta when you need the standardised JSR-354 API, currency conversion, query-based rounding policy or SPI extensibility — it is the only one of the two with rate providers and named roundings. Use Joda-Money when you want a small amount type with explicit rounding and no framework around it. Both are actively maintained and both are Apache 2.0.

**What is the difference between `Money` and `FastMoney` in Moneta?**
`Money` is backed by `BigDecimal` and supports arbitrary precision; `FastMoney` is backed by a `long` with a fixed scale of 5. In the project's own benchmark, 100,000 arithmetic operations took 2107 ms with `Money` and 1011 ms with `FastMoney`. Use `Money` when precision dominates and `FastMoney` when throughput dominates, and never mix the two in one chain.

**Does Joda-Money provide exchange rates?**
No. `convertedTo` accepts a `BigDecimal` rate and a `RoundingMode` that you supply. Joda-Money has no rate provider infrastructure by design — its README states the library is "intended to act as the base layer" and does not attempt domain-specific algorithms.

**How do I add a currency that the JDK does not know about, such as Bitcoin?**
With JSR-354, implement `CurrencyProviderSpi` and register it in `META-INF/services/javax.money.spi.CurrencyProviderSpi`, or register it as a CDI bean. For one-off currencies, `CurrencyUnitBuilder.of("FLS22", "MyCurrencyProvider").setDefaultFractionDigits(3).build(true)` registers on creation.

**How do I avoid flaky tests when rate providers call the network?**
Do not rely on live ECB or IMF feeds in unit tests. Register a deterministic provider, use `IDENT` for same-currency checks, or inject a stub `ExchangeRateProvider` through the SPI. Keep one integration test against the real feed, tagged so it can be skipped in restricted environments.

**Do I still need `BigDecimal` if I use these libraries?**
For amounts held inside a `MonetaryAmount`, no. But at the boundaries — database columns, JSON payloads, rate values handed to Joda-Money — you will still convert to and from `BigDecimal`, and division there needs an explicit `MathContext` or rounding mode.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Moneta vs Joda-Money in 2026: Which Java Money Library Should You Actually Use?",
  "description": "JSR-354 Moneta vs Joda-Money compared for Java in 2026, with real Maven coordinates, official API examples, published benchmark numbers and rounding pitfalls.",
  "datePublished": "2026-09-17",
  "dateModified": "2026-09-17",
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
