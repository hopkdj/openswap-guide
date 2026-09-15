---
title: "Money Math in 2026: dinero.js vs go-money vs py-moneyed vs rust-decimal Compared"
date: "2026-09-16"
tags: ["developer-tools", "fintech", "rust", "python", "javascript", "go"]
draft: false
cover: "/img/screenshots/dinero-banner.jpg"
---

Ask any engineer who has shipped a billing system what caused their worst production incident and the answer is rarely a database outage. It is a rounding bug. Floating-point money is the classic: `0.1 + 0.2` evaluates to `0.30000000000000004`, and once that value is written to an invoice it never comes back. Every serious language ecosystem eventually grows a library whose entire job is to stop you from doing currency math with floats — but those libraries make very different trade-offs, and picking the wrong one means you fix rounding bugs by convention instead of by compiler.

This guide compares the money- and decimal-handling libraries that matter in 2026 across five ecosystems, with live repository data and code you can paste into a project today.

## TL;DR — Quick Verdict

**In JavaScript and TypeScript, use dinero.js** — it is the most actively maintained of the group (pushed September 15, 2026) and models arithmetic as immutable calculator functions rather than mutable objects. **In Go, use go-money** — Fowler's Money pattern with correct minor-unit arithmetic and a real `Allocate` for splitting a total without losing pennies. **In Rust, use rust-decimal** for the fixed-precision decimal type, and add a money wrapper only when you need currency validation. **In Python, py-moneyed is still the default choice**, but check its maintenance status first: the repository has not been pushed since April 2024. **In Java, Joda-Money** is mature and quiet (last push December 2025) — prefer it over hand-rolled `BigDecimal` helpers, but expect to bring your own formatting and exchange-rate layers in every ecosystem.

## Comparison Table: Money and Decimal Libraries (September 2026)

| Library | Language | Stars (live) | Last push (live) | Scope | Correctness model |
|---|---|---|---|---|---|
| **dinero.js** (`dinerojs/dinero.js`) | JavaScript / TypeScript | **6,794** | **2026-09-15** | Money type + calculator | Immutable objects, integer minor units, explicit scale |
| **go-money** (`Rhymond/go-money`) | Go | **1,911** | **2026-04-29** | Money type | `int64` minor units, Fowler Money pattern |
| **py-moneyed** (`py-moneyed/py-moneyed`) | Python | **474** | **2024-04-23** | Money + currency types | `Decimal` internally, currency-aware |
| **joda-money** (`JodaOrg/joda-money`) | Java | **678** | **2025-12-14** | Money + FastMoney | `BigDecimal` precision or `long` fast path |
| **rust-decimal** (`paupino/rust-decimal`) | Rust | **1,335** | **2026-09-14** | Decimal type (not currency-aware) | 96-bit fixed-point decimal, explicit rounding strategies |

| Capability | dinero.js | go-money | py-moneyed | joda-money | rust-decimal |
|---|---|---|---|---|---|
| Stores minor units as integers | Yes | Yes | Internal `Decimal` | Yes (`Money.of`) | Yes (scaled integer) |
| Currency mismatch detection | Yes (throws) | Yes (errors) | Yes (raises) | Yes (exceptions) | **No** (caller's job) |
| Split a total without losing cents | `allocate` | `Allocate` | Manual | Manual | Manual |
| Rounding strategy selection | Via calculator options | Limited | `Decimal` context | `RoundingMode` | `RoundingStrategy` |
| Locale/currency formatting | `toFormat` | `Display` | `format_money` helpers | None built in | None |
| Actively developed | Yes | Moderate | **Stale since 2024** | Low activity | Yes |

## Decision Matrix: Match the Library to the Money Problem

| Your situation | Pick | Why |
|---|---|---|
| Stripe-style payment amounts in Node/TS | **dinero.js** | Integer minor units plus a functional calculator API |
| Go service splitting an invoice across parties | **go-money** | `Allocate` distributes remainders deterministically |
| Rust pricing engine needing exact decimals | **rust-decimal** | Fixed-point decimal with explicit rounding strategies |
| Python data pipeline touching currencies | **py-moneyed** | Currency-aware type that refuses cross-currency math |
| Java batch job with millions of amounts | **joda-money** | `Money` for precision, `FastMoney` for throughput |
| You only need "never use float" in one service | **Language-native decimal** | `decimal.Decimal`, `BigDecimal`, or `Decimal` crate directly |

## dinero.js — Money Arithmetic for TypeScript

![dinero.js project banner from the official repository](/img/screenshots/dinero-banner.jpg)

dinero.js v2 abandoned the mutable-object style of v1 in favour of a functional calculator: an amount object plus pure functions that return new objects. The library's own description is precise — "Create, calculate, and format money in JavaScript and TypeScript" — and currencies are imported as typed objects rather than string codes, which is what makes cross-currency mistakes throw at runtime instead of silently producing nonsense.

```bash
npm install dinero.js
```

```ts
import { dinero, add, multiply, allocate, toSnapshot } from 'dinero.js';
import { USD } from 'dinero.js/currencies';

const price = dinero({ amount: 4999, currency: USD });      // $49.99 in minor units
const tax = multiply(price, { amount: 8, scale: 100 });      // 8%
const total = add(price, tax);

console.log(toSnapshot(total)); // { amount: 5399, currency: { code: 'USD', ... }, scale: 2 }

// Split $10.00 three ways without losing a cent
const parts = allocate(dinero({ amount: 1000, currency: USD }), [1, 1, 1]);
```

The `allocate` helper is the detail that separates a toy library from a production one. Splitting $10.00 three ways gives 333/333/334, not three values of 333.33 that sum to $9.99 — a penny vanishing between allocations is exactly the kind of bug auditors find years later.

**Where it hurts:** v1 and v2 APIs are incompatible, so migration guides matter more than usual; and because arithmetic is functional, existing code that mutated an amount in place must be rewritten rather than recompiled.

## go-money — Fowler's Money Pattern, Idiomatically

go-money implements Martin Fowler's Money pattern directly: an amount in minor units (`int64`) plus a currency, with arithmetic that returns errors on currency mismatch instead of panicking. The repository describes itself as exactly that, and the ergonomics are what Go developers expect.

```bash
go get github.com/Rhymond/go-money
```

```go
package billing

import "github.com/Rhymond/go-money"

func Total(lines []int64) (*money.Money, error) {
	total := money.New(0, "USD")
	for _, cents := range lines {
		line := money.New(cents, "USD")
		var err error
		total, err = total.Add(line)
		if err != nil {
			return nil, err // currency mismatch
		}
	}
	return total, nil
}

// Split an invoice across three cost centres, remainder included
parts, _ := money.New(1000, "USD").Allocate(1, 1, 1) // 333, 333, 334
```

`NewFromFloat` exists for legacy input, but treat it as an import boundary, not as a working type — convert floats to minor units once, at the edge, and never let them back into your domain logic. Note the activity gap: the last push to the repository was April 29, 2026, which for a library whose API surface is essentially finished is acceptable, but it does mean you should not expect new features.

## py-moneyed — Currency-Aware Amounts in Python

py-moneyed provides `Money` and `Currency` classes that refuse to add dollars to euros. Internally it uses `Decimal`, so the arithmetic itself is exact; the library's value is the currency layer, not the decimal type (Python's standard library already gives you `decimal.Decimal`).

```bash
pip install py-moneyed
```

```python
from decimal import Decimal, ROUND_HALF_EVEN
from moneyed import Money, USD, EUR

price = Money(Decimal("49.99"), USD)
shipping = Money(Decimal("4.50"), USD)
total = price + shipping                     # Money(54.49, USD)

try:
    total + Money(Decimal("10.00"), EUR)     # raises CurrencyMismatch
except Exception as exc:
    print("refused:", type(exc).__name__)
```

The maintenance caveat is real and worth stating plainly: the repository has not been pushed since April 2024, so py-moneyed is a stable-but-quiet dependency rather than an actively evolving one. It still works, and its scope is small enough that this is survivable — but if your compliance requirements demand a maintained dependency, plan a migration path to `Decimal` plus an explicit currency enum, or to `prices` where you need price lists.

## rust-decimal — Exact Decimals With Explicit Rounding

Rust splits the problem in two: `rust-decimal` owns the numeric type, and separate crates handle currency semantics. The official description is "a Decimal number implementation written in pure Rust suitable for financial and fixed-precision calculations," and the design decision that matters is that rounding is never implicit — you choose a `RoundingStrategy`, which is exactly what a financial code review wants to see.

```toml
[dependencies]
rust_decimal = { version = "1", features = ["macros", "serde-with-str"] }
```

```rust
use rust_decimal::{Decimal, RoundingStrategy};
use rust_decimal::prelude::FromStr;

fn invoice_total(lines: &[Decimal], vat_rate: Decimal) -> Decimal {
    let subtotal: Decimal = lines.iter().copied().sum();
    let vat = (subtotal * vat_rate).round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero);
    (subtotal + vat).round_dp(2)
}

fn main() {
    let price = Decimal::from_str("49.99").unwrap();
    let printed = Decimal::from(49_99) / Decimal::from(100);
    assert_eq!(price, printed);
    println!("{:?}", invoice_total(&[price], Decimal::from_str("0.20").unwrap()));
}
```

Because `rust-decimal` is not currency-aware, it will happily add a value in euros to one in dollars — an explicit limitation its documentation states. Pair it with a money wrapper (or your own newtype around `Decimal` plus a currency field) when the domain needs that guarantee, and serialize decimals as strings (`serde-with-str`) so a consumer in another language cannot reinterpret the scale.

## joda-money — The Java Default

Joda-Money is what most Java teams should reach for instead of scattered `BigDecimal` helpers. It offers two representations: `Money` for `BigDecimal`-backed precision and `FastMoney` for `long`-backed performance when you process millions of amounts and can tolerate its scale constraints.

```java
import org.joda.money.Money;
import org.joda.money.CurrencyUnit;
import java.math.RoundingMode;

Money price = Money.parse("USD 49.99");
Money shipping = Money.of(CurrencyUnit.USD, 4.50);
Money total = price.plus(shipping);                     // USD 54.49
Money rounded = total.rounded(2, RoundingMode.HALF_EVEN); // banker's rounding
```

Joda-Money deliberately does not do formatting or currency conversion — the project's stance is that those belong to the platform (locale-aware formatting) or to a rate provider. That keeps the library small, but it means a Java billing service still needs a formatting layer, and it means exchange rates are your responsibility in every one of the five libraries above.

## The Money Bugs That Libraries Do Not Fix For You

- **Mixing scale with minor units.** `49.99` as a float and `4999` as minor units are the same amount only until someone divides. Pick minor units as your storage and wire format, and convert at the boundaries.
- **Assuming two decimal places.** JPY has zero, KWD and BHD have three. Hard-coding `* 100` is a bug waiting for your first international customer.
- **Rounding per line instead of per total.** Summing pre-rounded line items and rounding the total produce different numbers. Decide once, document it, and test both directions.
- **Ignoring allocation remainders.** Any split of a total across N parties must distribute the remainder deterministically. Use `allocate`/`Allocate` rather than dividing and hoping.
- **Storing money in a float column.** Even with a correct library, a `REAL`/`DOUBLE` database column reintroduces binary floating point. Store integers or a `NUMERIC`/`DECIMAL` column.
- **Silent currency coercion in serialization.** Send the currency code, the minor-unit amount, and the scale — a bare number in a JSON payload is an interpretation waiting to happen.

## Why Own Your Money-Critical Code?

Money handling is the clearest case for keeping critical logic inside code you control. A decimal library is small, auditable, and boring on purpose — and the failure mode of an opaque dependency is a silent rounding change that surfaces as a reconciliation gap months later. Running the accounting, invoicing, or pricing service on infrastructure you operate also means you can pin the exact library version and prove, in an audit, which rounding strategy produced a given statement.

Related developer-library comparisons on this site take the same approach. Our [unique ID generation libraries guide](../2026-06-21-unique-id-generation-libraries-snowflake-ulid-ksuid-xid/) covers the identifier layer that sits next to money in every transaction table, the [Python data comparison libraries breakdown](../2026-07-30-python-data-comparison-libraries-deepdiff-datacompy-jsondiff-dictdiffer/) helps when you need to diff financial payloads in tests, and the [object mapping libraries comparison](../2026-06-20-object-mapping-libraries-automapper-mapstruct-marshmallow-ent/) covers the layer that turns database rows into the money types above.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Money Math in 2026: dinero.js vs go-money vs py-moneyed vs rust-decimal Compared",
  "description": "Money and decimal libraries compared across JavaScript, Go, Python, Java, and Rust with live repository data, real code examples, and the rounding traps that break billing systems.",
  "datePublished": "2026-09-16",
  "dateModified": "2026-09-16",
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

### Why is floating point bad for money?

Binary floating point cannot represent most decimal fractions exactly, so values like `0.1` are stored as approximations. Repeated addition and multiplication turn those approximations into visible errors — a total computed as `0.30000000000000004` becomes an off-by-one-cent invoice after rounding. Integer minor units or a decimal type avoid the problem entirely.

### Should I store money as decimal or integer?

Store it as an integer in minor units (cents, pence, satoshi) whenever the currency has a fixed smallest unit, because integer arithmetic is exact and unambiguous across languages. If you need arbitrary precision or variable scale, use a decimal type with an explicit scale, and make sure the database column is `NUMERIC`/`DECIMAL` rather than a floating-point type.

### What is the best money library for JavaScript?

dinero.js is the most complete option for JavaScript and TypeScript in 2026: it stores amounts in minor units, throws on currency mismatches, and provides calculator functions including `allocate` for splitting totals without losing a cent. It was most recently pushed on September 15, 2026, making it the most active library in this comparison.

### How do I split an amount without losing a penny?

Use an allocation function rather than division. dinero.js provides `allocate`, go-money provides `Allocate`, and both distribute the remainder deterministically so the parts sum back to the original amount exactly. In Java, Python, and Rust you either implement the same remainder-distribution loop or accept an explicit, tested discrepancy.

### Is py-moneyed still maintained?

It is stable but quiet — the repository's last push was April 23, 2024. The library works and its scope is narrow, so it remains a reasonable choice, but teams with dependency-maintenance requirements should plan to migrate to `decimal.Decimal` with an explicit currency type, or evaluate an actively maintained alternative.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
