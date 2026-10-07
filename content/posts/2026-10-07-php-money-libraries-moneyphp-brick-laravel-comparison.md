---
title: "MoneyPHP vs Brick Money vs Laravel Money in 2026: Which PHP Money Library Should You Use?"
date: "2026-10-07"
tags: ["php", "money-libraries", "ecommerce", "back-end", "developer-tools"]
draft: false
cover: "/img/screenshots/php-money-libraries.jpg"
description: "A live-data comparison of the three PHP money libraries that matter in 2026: MoneyPHP, Brick Money and Akaunting Laravel Money. Real install commands, real API examples, real rounding pitfalls."
---

Every PHP developer eventually ships a rounding bug. It usually looks harmless: a cart total of `19.99` multiplied by `3`, stored as a float, saved into a `FLOAT` column, and paid out a month later with a two-cent discrepancy that your accountant notices before you do. Money is not a number — it is an amount plus a currency plus a rounding policy — and PHP's ecosystem has three serious libraries built around that fact.

This guide compares **MoneyPHP**, **Brick Money** and **Akaunting Laravel Money** with live repository data from October 2026, real `composer` install commands, code taken from each project's official documentation, and the storage decisions that determine whether you will be debugging cent-level drift in six months.

## TL;DR: Quick Verdict

- **Choose MoneyPHP** if you need a framework-agnostic domain library with excellent allocation logic (`allocate([1,1,1])`), aggregate helpers, and a mature 4.x release line. It is the safest default for Symfony and custom applications.
- **Choose Brick Money** if correctness is the priority: it sits on top of `brick/math` for arbitrary-precision arithmetic, forces you to pick a `RoundingMode`, refuses cross-currency arithmetic at the type level, and ships `CashContext` for currencies with non-standard cash increments.
- **Choose Akaunting Laravel Money** if you are on Laravel and want formatting, currency conversion, Blade directives and a helper function in a single package with almost no integration work.
- **Mix them if you must**, but never let two libraries own the same domain object. Pick one representation of money and convert at the edges.

## Side-by-Side Comparison (Live Data, October 2026)

| Dimension | MoneyPHP | Brick Money | Laravel Money |
|---|---|---|---|
| Package | `moneyphp/money` | `brick/money` | `akaunting/laravel-money` |
| Repository stars | **4,869★** | **1,930★** | **790★** |
| Latest release | **v4.9.0** (May 4, 2026) | **0.15.2** (Sep 29, 2026) | **6.0.3** (Mar 24, 2026) |
| Last repository activity | Jul 7, 2026 | **Oct 6, 2026** | Mar 24, 2026 |
| Requires | PHP 8.x, ext-bcmath/gmp optional | **PHP 8.2+**, GMP/BCMath recommended | Laravel (package is Laravel-first) |
| Arithmetic backend | bcmath, GMP or plain PHP (auto-selected) | `brick/math` (BigNumber, BigRational) | Plain integers + float conversion helpers |
| Strict rounding modes | Yes, via formatter/rounding helpers | **Yes — `RoundingMode` is a first-class argument** | Delegates to rounding config |
| Cross-currency safety | `CurrencyMismatchException` | `CurrencyMismatchException` | `isSameCurrency()` check, manual |
| Allocation / split amounts | **Yes — `allocate()`** | Yes — `allocate()` on `Money` and `MoneyBag` | Yes — `allocate()` |
| Money bags / mixed currency | No | **Yes — `MoneyBag` with `Money::total()`** | No |
| Formatting | `IntlMoneyFormatter`, `DecimalMoneyFormatter` | `formatTo($locale)`, `formatWith()` | **Intl + Blade directives + helpers** |
| Currency conversion | Swap/Exchanger interfaces | Manual (bring your own rates) | **Built-in `convert()` + rates config** |
| Best fit | Symfony, framework-agnostic services | Domains with strict accounting rules | Laravel apps that need it working today |

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Reason |
|---|---|---|
| Symfony app, invoices and line items | **MoneyPHP** | Mature, stable API, split-amount helpers |
| Accounting, payroll, tax calculations | **Brick Money** | Explicit rounding modes, arbitrary precision, `CashContext` |
| Multi-currency totals in a report | **Brick Money** | `MoneyBag` and `Money::total()` handle mixed currencies |
| Laravel app with Blade views | **Laravel Money** | `@money()` directive and helpers with zero ceremony |
| Legacy code full of floats | **Brick Money** | `ofMinor()` forces you to think in cents |
| You need one library for both backend and views | **Laravel Money** on Laravel, **MoneyPHP** everywhere else | Different integration surfaces |
| You must support a currency with 0 decimals (JPY) or 3 (KWD, BHD) | **Brick Money** | Currency metadata and contexts are the most complete |

## MoneyPHP: The Battle-Tested Default

MoneyPHP implements Martin Fowler's Money pattern with an integer amount and a `Currency` object. Amounts are always stored in the currency's smallest unit, so `Money::EUR(500)` is five euros, not five hundred euros — a convention that eliminates float error at the source.

Installation is a single Composer command, and the library transparently uses bcmath or GMP when available and falls back to plain PHP arithmetic otherwise:

```bash
composer require moneyphp/money

# Recommended in production: install a fast arithmetic backend
apt-get install php-bcmath php-gmp
```

The most valuable feature in real applications is allocation — splitting an amount without creating or losing a cent. Note how the remainder is distributed deterministically:

```php
<?php

use Money\Money;

$fiveEur = Money::EUR(500);
$tenEur = $fiveEur->add($fiveEur);

list($part1, $part2, $part3) = $tenEur->allocate([1, 1, 1]);

assert($part1->equals(Money::EUR(334)));
assert($part2->equals(Money::EUR(333)));
assert($part3->equals(Money::EUR(333)));
```

Formatting goes through explicit formatter objects rather than magic output methods, which keeps locale decisions visible in your code:

```php
<?php

use Money\Currencies\ISOCurrencies;
use Money\Currency;
use Money\Formatter\DecimalMoneyFormatter;
use Money\Formatter\IntlMoneyFormatter;
use Money\Money;

$money = new Money(123456, new Currency('USD'));
$currencies = new ISOCurrencies();

// Machine-readable output: 1234.56
$decimalFormatter = new DecimalMoneyFormatter($currencies);
echo $decimalFormatter->format($money), PHP_EOL;

// Human-readable, locale aware: $1,234.56
$numberFormatter = new \NumberFormatter('en_US', \NumberFormatter::CURRENCY);
$intlFormatter = new IntlMoneyFormatter($numberFormatter, $currencies);
echo $intlFormatter->format($money), PHP_EOL;
```

Currency repositories are pluggable, so you can load only the ISO currencies you actually support instead of the whole list. The library also exposes aggregate helpers for reporting queries, and the 4.x line has been stable long enough that most tutorials you find online will still apply.

**What you get:** a stable 4.9.0 release, allocation logic that pays for itself the first time you split an invoice, and framework neutrality that lets the same object move between Symfony, a queue worker, and a CLI report.

**What it costs you:** no built-in currency conversion (you wire up an exchange-rate provider yourself), no money-bag type for mixed-currency aggregates, and a formatting API that requires a few more lines than Laravel Money's directive.

## Brick Money: Strictness as a Feature

Brick Money's design philosophy is that the compiler — or, in PHP terms, the runtime type system — should stop you before you make an accounting mistake. It requires **PHP 8.2 or newer**, recommends the GMP or BCMath extension for speed, and builds every operation on `brick/math` (currently **1.0.0**, released September 12, 2026, **2,176 stars**), which provides arbitrary-precision decimals and rationals.

The library is the most actively developed of the three: **1,930 stars with a push on October 6, 2026** and release 0.15.2 on September 29, 2026.

Creating money from a decimal value refuses to guess a rounding policy:

```php
<?php

use Brick\Money\Money;
use Brick\Math\RoundingMode;

$money = Money::of(50, 'USD');          // USD 50.00
$money = Money::of('19.9', 'USD');      // USD 19.90

// Throws RoundingNecessaryException — you must decide
Money::of('123.456', 'USD');

// Explicit policy
$money = Money::of('123.456', 'USD', roundingMode: RoundingMode::Up); // USD 123.46
```

An upcoming version's documentation is explicit that the rounding mode applies only to that single call — it is not stored on the object. Every subsequent operation that needs rounding asks you again. That is annoying for prototypes and exactly right for financial code.

Arithmetic accepts scalars, and mixed currencies are rejected with a typed exception instead of silently producing nonsense:

```php
<?php

use Brick\Money\Money;

$cost = Money::of(25, 'USD');
$shipping = Money::of('4.99', 'USD');
$discount = Money::of('2.50', 'USD');

echo $cost->plus($shipping)->minus($discount); // USD 27.49

$a = Money::of(1, 'USD');
$b = Money::of(1, 'EUR');
$a->plus($b); // CurrencyMismatchException
```

For systems that must add up line items in several currencies, `MoneyBag` plus `Money::total()` gives you a mixed-currency aggregate that keeps each currency separate instead of pretending an exchange rate is a fact. Brick Money also ships `CashContext` for currencies where the cash rounding increment differs from the accounting precision — the difference between an invoice total and the coins a till can actually produce.

**What you get:** the strictest correctness guarantees in the PHP ecosystem, the most complete currency metadata, explicit rounding everywhere, and a maintainer who keeps a published policy on what counts as a breaking change after 1.0.

**What it costs you:** PHP 8.2+, more verbose call sites because rounding is never implicit, no bundled exchange-rate integration, and a 0.x version number that some reviewers will (wrongly) read as immaturity.

## Akaunting Laravel Money: The Laravel Shortcut

Akaunting's `laravel-money` package is a formatting-first library for Laravel applications. It is the least active of the three (**6.0.3**, March 24, 2026) but it removes the most boilerplate if your entire application lives inside a Laravel release.

```bash
composer require akaunting/laravel-money

# Optional: publish the currency/format configuration
php artisan vendor:publish --tag=money
```

The API is deliberately terse. `convert` is a boolean argument on construction — with `true`, the amount is treated as major units; with `false` or omitted, as the currency's minor units:

```php
<?php

use Akaunting\Money\Currency;
use Akaunting\Money\Money;

echo Money::USD(500);                                     // '$5.00' unconverted
echo new Money(500, new Currency('USD'));                 // '$5.00' unconverted
echo Money::USD(500, true);                               // '$500.00' converted
echo new Money(500, new Currency('USD'), true);           // '$500.00' converted
```

It exposes the full comparison and arithmetic surface you would expect, plus conversion against a rate you supply:

```php
<?php

$m1 = Money::USD(500);
$m2 = Money::EUR(500);

$m1->isSameCurrency($m2);
$m1->greaterThan($m2);
$m1->convert(Currency::GBP(), 3.5);
$m1->add($m2);
$m1->allocate([1, 1, 1]);
$m1->format();
```

In Blade, the package provides directives, helpers and a component, which is where it earns its place:

```blade
@money(500)
@money(500, 'USD')
@currency('USD')

{{-- Component form --}}
<x-money amount="500" currency="USD" />
```

**What you get:** the fastest path from "I have an integer in cents" to a formatted, converted, localized string in a Laravel view.

**What it costs you:** Laravel coupling, a slower release cadence, and a smaller feature surface — `MoneyBag`, cash contexts and explicit rounding modes are simply not part of its model. If your application outgrows formatting, you will end up migrating to one of the other two.

## Storage and Architecture Pitfalls That Bite Everyone

1. **Never store money in a `FLOAT` or `DOUBLE` column.** Use `DECIMAL(19,4)` (MySQL/PostgreSQL) or an integer count of minor units with the currency code alongside it. Most money bugs are schema bugs wearing a library-shaped disguise.
2. **Fixed-point columns and library amounts must agree on scale.** If your column stores four decimals and your library rounds to two, reconciliation reports will disagree with your application by tiny amounts that are impossible to explain to a customer.
3. **Not every currency has two decimal places.** JPY has none; KWD and BHD have three. Hardcoding `100` as the minor-unit multiplier is the single most common source of silent errors in PHP codebases.
4. **Rounding mode is a business decision, not a default.** `RoundingMode::HALF_UP`, `HALF_EVEN` (banker's rounding) and `DOWN` produce different totals on the same data set. Choose once, document it, and apply it in every code path — including refunds.
5. **Exchange rates are not money.** Keep the rate, the rate's timestamp, and the source currency stored separately so that a historical invoice can be re-derived exactly, even when the rate has moved.
6. **Watch the mutability contract.** MoneyPHP and Brick Money objects are immutable — every operation returns a new instance. Akaunting's `Money` follows the same contract, but its `convert` flag changes how the constructor interprets the integer, which is an easy thing to flip accidentally during a refactor.
7. **Serialization is a boundary.** If money objects cross a queue or an HTTP response, serialize the amount and currency explicitly (both libraries offer JSON helpers) rather than relying on PHP's default object serialization, which couples your API to a library version.

Rounding behaviour across ecosystems is a surprisingly deep topic; our [comparison of money and decimal libraries in JavaScript, Go, Python and Rust](../2026-09-16-money-decimal-libraries-dinerojs-go-money-py-moneyed-rust-decimal/) shows how the same decisions are made in other languages, and the [Java money library comparison covering Moneta, Joda-Money and JSR-354](../2026-09-17-java-money-libraries-moneta-joda-money-jsr354-comparison/) is the reference point if your PHP service has to talk to a JVM backend. If you need live rates to feed a conversion layer, our [self-hosted currency exchange rate API guide covering Frankfurter](../2026-06-09-self-hosted-currency-exchange-rate-apis-frankfurter-exchange-api-guide/) shows how to run the rate source yourself instead of depending on a third-party quota.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MoneyPHP vs Brick Money vs Laravel Money in 2026: Which PHP Money Library Should You Use?",
  "description": "Live-data comparison of MoneyPHP, Brick Money and Akaunting Laravel Money: install commands, official API examples, storage patterns and the rounding pitfalls that cause cent-level drift.",
  "datePublished": "2026-10-07",
  "dateModified": "2026-10-07",
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

**Which PHP money library should I use with Symfony?**
MoneyPHP. It has no framework dependency, integrates cleanly with Symfony services, and its formatter objects map well onto Symfony's service container. Brick Money is a good upgrade if your accounting rules require explicit rounding modes.

**Does Brick Money really require PHP 8.2?**
Yes. The current 0.15.x line requires PHP 8.2 or later and recommends the GMP or BCMath extension for faster arithmetic. Older PHP versions need older releases: 0.10 for PHP 8.1, 0.8 for PHP 8.0, 0.7 for PHP 7.4.

**Can I use Akaunting Laravel Money outside Laravel?**
It is designed as a Laravel package with service-provider registration, config publishing and Blade directives, so using it standalone means fighting the framework integration. If you are not on Laravel, pick MoneyPHP or Brick Money.

**How do I store money in the database?**
Use a fixed-precision decimal column (`DECIMAL(19,4)`) or an integer minor-unit column plus a separate currency code. Never use floating point. Whichever you choose, keep the scale consistent with the library's rounding policy.

**What is the difference between `Money::of()` and `Money::ofMinor()` in Brick Money?**
`Money::of('12.34', 'USD')` takes a decimal amount in major units, while `Money::ofMinor(1234, 'USD')` takes an integer in the currency's smallest unit. Using `ofMinor()` on values that already come from your database as integers avoids an entire class of conversion bugs.

**Do any of these libraries convert currencies automatically?**
Only Laravel Money has a built-in `convert()` method, and even there you supply the rate. MoneyPHP exposes an exchange interface you implement, and Brick Money leaves conversion entirely to your application, which is the correct separation for accounting systems.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
