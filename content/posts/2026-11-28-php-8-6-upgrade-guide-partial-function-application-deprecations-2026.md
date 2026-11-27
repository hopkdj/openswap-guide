---
title: "PHP 8.6 Upgrade Guide 2026: Partial Function Application, Readonly Defaults, and the Deprecations That Break CI"
date: "2026-11-28"
tags: ["php", "upgrade", "migration", "self-hosted", "web-development"]
draft: false
cover: "/img/screenshots/php-8-6-upgrade-logo.jpg"
---

PHP 8.6.0 shipped on **19 November 2026** — nine days ago. PHP 8.4 stops receiving active bugfixes on **31 December 2026**, and PHP 8.2 reaches full end of life the same day. That gives you five weeks to get off two branches at once, during a period when most teams are freezing deploys for the holidays.

The good news is that 8.6 is a feature release, not a compatibility minefield: nothing in the extension set was removed, and the language changes are additive. The bad news is concentrated in one place — the deprecation list, which is long enough that a suite running under `E_ALL` will produce failures that look like bugs in your own code.

## TL;DR: The Quick Verdict

**If you are on 8.2 or 8.3: go straight to 8.6.** You inherit 8.5's pipe operator and `#[\NoDiscard]` for free, and you skip a branch that is already dead. **If you are on 8.4: 8.6 is a two-day job** — one day fixing deprecations under `E_ALL`, one day validating extensions. **If you are on 8.5: this is a patch-level upgrade with better errors.** Either way, run your test suite with `error_reporting=E_ALL` *before* you change the version, because 8.6's deprecations fire on code that 8.4 accepts silently.

## PHP support status, November 2026

| Branch | Latest | GA | Active support ends | Security EOL | Headline change |
|---|---|---|---|---|---|
| **8.6** | 8.6.0 | 2026-11-19 | 2028-12-31 | 2030-12-31 | Partial function application, readonly defaults |
| 8.5 | 8.5.13 | 2025-11-20 | 2027-12-31 | 2029-12-31 | Pipe operator, `#[\NoDiscard]` |
| 8.4 | 8.4.28 | 2024-11-21 | **2026-12-31** | 2028-12-31 | Property hooks, asymmetric visibility |
| 8.3 | 8.3.37 | 2023-11-23 | Ended 2025-12-31 | 2027-12-31 | Typed class constants, `json_validate()` |
| 8.2 | 8.2.36 | 2022-12-08 | Ended | **2026-12-31** | Readonly classes, DNF types |

The interpreter repository is as active as ever — **41,876 stars** on `php/php-src`, last commit **27 November 2026**. Note the shape of that table: 8.4 and 8.2 both leave support coverage in the same five-week window, which is why this upgrade is worth scheduling now rather than in January.

## What actually landed in PHP 8.6

Four changes are worth planning around; the rest are quality-of-life.

**Readonly properties can declare defaults.** This removes one of the strangest ergonomic holes in the readonly implementation — you no longer need a constructor argument for every readonly property that has an obvious initial value.

```php
final class Money
{
    public function __construct(
        public readonly int $amount = 0,
        public readonly string $currency = 'USD',
    ) {}
}

$price = new Money(amount: 4999);
```

**Partial function application.** You can now leave `?` placeholders in a call and get back a `Closure` with the remaining arguments. For code that currently wraps `array_map` in a one-line closure just to pre-bind an argument, this is a real readability win.

```php
$slugify = str_replace(' ', '-', ?);
echo $slugify('Redis 8.12 Upgrade Guide');   // Redis-8.12-Upgrade-Guide

// Composes the way you would expect with array functions
$titles = ['PHP 8.6 Upgrade', 'Redis 8.12 Upgrade'];
$slugs  = array_map($slugify, $titles);
```

**`#[\Override]` now applies to class constants**, including enum cases. If you override a constant from a parent class or interface, the attribute turns a silent typo into a compile-time error.

```php
class BaseResponse
{
    public const FORMAT = 'json';
}

final class StreamResponse extends BaseResponse
{
    #[\Override]
    public const FORMAT = 'ndjson';
}
```

**A new `Time\Duration` class** joins the date extension for representing elapsed time as a first-class value rather than an integer whose unit lives in a variable name. Enums also gained `__debugInfo()`, objects stored in constants can now be mutated in place, and `curl_getinfo()` reports a new `size_delivered` key (requires libcurl 8.20 or newer).

If you are jumping from 8.4, you also collect 8.5's features without extra work: the **pipe operator** (`|>`), the **`#[\NoDiscard]`** attribute with its `(void)` cast escape hatch, closures and first-class callables in constant expressions, attributes on constants, `#[\Override]` on properties, and fatal errors that now include a backtrace — that last one alone justifies the jump for anyone who has debugged a max-execution-time failure with no stack.

## Breaking changes that pass `php -l` but fail at runtime

None of these are syntax errors, which is exactly why they belong in a staging soak test rather than a lint check.

1. **By-reference `foreach` may visit elements it previously skipped.** After array compaction, internal pointers on deleted elements now move to the next surviving element during copy-on-write. Code that mutates an array while iterating it by reference can see extra iterations.
2. **`??` and `empty()` on magic properties no longer call `__get()`** when `__isset()` has materialized the property by writing into the property table — the freshly written value is returned directly. If your `__get()` performed lazy loading or logging, that side effect disappears.
3. **Curl read callbacks now throw `ValueError`** when `CURLOPT_READFUNCTION` returns an integer other than `0`, `CURL_READFUNC_ABORT` or `CURL_READFUNC_PAUSE`. A callback that returned `strlen($chunk)` now throws instead of misbehaving quietly.
4. **DOM readonly properties use asymmetric visibility.** Writing to `DOMNode::$nodeType` and friends now raises "Cannot modify private(set) property", and `ReflectionProperty::isWritable()` finally reports the truth. Tests that asserted on the old error message will break.
5. **FTP non-blocking functions throw `Error`** when a transfer is already in progress, instead of warning and returning `false`.
6. **GMP and GD got strict about argument types and ranges** — shifts and exponentiation outside the unsigned long range throw `ValueError` instead of truncating, and string parsing rejects NUL bytes. `gmp_powm()` with a zero modulus raises `DivisionByZeroError` naming the argument.

The pattern is consistent: silent truncation and warning-plus-`false` are being replaced with exceptions. That is good for correctness and bad for anyone whose error handling assumed `false`.

## Deprecations that will fail CI under `E_ALL`

PHPUnit converts deprecations to failures in most modern configurations, so this list is effectively your work queue:

- `return` inside a `finally` block — deprecated. It has always been confusing; 8.6 stops pretending otherwise.
- `return` from `__construct()` or `__destruct()`, and making either a generator.
- `__debugInfo()` declared as returning `array|null` or `?array` — declare `array` instead.
- Passing a third argument to `define()` (the case-insensitive flag).
- `is_a()` / `is_subclass_of()` with a string first argument when `$allow_string` is false.
- Naming a function `readonly`, and using `let` or `is` as a class, interface, trait, enum, function or constant name.
- Using `_` as a constant name or as an alias in a `use` declaration.
- Using `namespace` as a class constant name.

Find the risky ones before the test run does:

```bash
# The two patterns most likely to be hiding in a legacy codebase
grep -rn --include='*.php' -E 'finally[[:space:]]*\{' app/ src/ | head -20
grep -rn --include='*.php' -E 'function[[:space:]]+readonly|define\([^,]+,[^,]+,[^)]+\)' app/ src/ | head -20

# Everything else surfaces here, with the deprecation text and file:line
php -d error_reporting=E_ALL -d display_errors=1 vendor/bin/phpunit 2>&1 | grep -i deprecated | head -40
```

## A practical upgrade pipeline

Do not upgrade the machine you develop on and hope. Run the three versions side by side, because the interesting failures are version-specific.

```yaml
services:
  app-84:
    image: php:8.4-cli
    working_dir: /app
    volumes: [".:/app"]
    command: ["sh", "-lc", "php -v && php -d error_reporting=E_ALL vendor/bin/phpunit"]

  app-86:
    image: php:8.6-cli
    working_dir: /app
    volumes: [".:/app"]
    command: ["sh", "-lc", "php -v && php -d error_reporting=E_ALL vendor/bin/phpunit"]
```

Pin the platform in `composer.json` so dependency resolution matches production, and let Composer tell you which extensions your lock file assumes:

```json
{
  "config": {
    "platform": {
      "php": "8.6.0"
    }
  }
}
```

```bash
composer check-platform-reqs      # extension and version requirements from the lock file
composer validate --strict        # catches platform drift before CI does
php -r 'echo PHP_VERSION, PHP_EOL;'
```

For production images, use the same base tag you tested with and keep the build reproducible:

```dockerfile
FROM php:8.6-cli AS base
RUN docker-php-ext-install pdo_mysql intl opcache \
 && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --prefer-dist --no-interaction --no-scripts
COPY . .
```

One caveat worth writing down: if your application server is FrankenPHP, RoadRunner or Swoole rather than PHP-FPM, the runtime's own compatibility with 8.6 lags the interpreter. Our [PHP application servers comparison](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/) covers which of them pin the interpreter version, and it is the first thing to check before you schedule the upgrade.

## Decision matrix: which branch to target

| Your situation | Target | Why |
|---|---|---|
| On 8.2, no blockers | **8.6 directly** | 8.2 is fully EOL on 31 Dec 2026 |
| On 8.3, dependencies lag | **8.5 first, 8.6 next quarter** | 8.5 buys a year of support with fewer deprecations |
| On 8.4, clean test suite | **8.6** | Five weeks before active support ends |
| On 8.4, heavy legacy code | **8.4 until the deprecation list is clean** | Security fixes continue into 2028; rush causes incidents |
| Using `#[\NoDiscard]`-style strictness | **8.6** | `(void)` cast and attribute-based return checks |
| Long-lived SOAP/FTP/GMP code | **Stage carefully** | Exception-based error handling replaces warnings |

## Pitfalls

1. **`E_ALL` locally is not the same as `E_ALL` in CI.** A phpunit.xml that overrides `error_reporting` hides exactly the deprecations you need to see. Check the effective value with `php -i | grep error_reporting`.
2. **Deprecations are not errors — until your test framework says so.** Confirm your PHPUnit/Pest configuration converts them to failures, otherwise they accumulate quietly until the next branch removal.
3. **Extension builds lag.** `docker-php-ext-install` for a brand-new minor version sometimes needs a newer base image; pin the digest you validated instead of `php:8.6-cli` floating.
4. **Composer's platform check can lie** if `config.platform.php` is set to an older version while your runtime is 8.6 — dependency resolution then installs packages that are not actually tested on 8.6.
5. **The DOM error message change breaks string-matching tests.** Assert on the exception class, not the message text.
6. **`finally { return }` removal is a real behavior change** when it does arrive: swallowed exceptions stop being swallowed, so error paths may surface loudly for the first time. Fix it now and observe the fallout while both branches are still supported.

## FAQ

**Is PHP 8.6 a breaking release?**
No extension or SAPI was removed, and the syntax changes are additive. The risk sits in two places: by-reference `foreach` semantics after array compaction, and the shift from warnings to exceptions in Curl, FTP, GMP and GD.

**Can I skip PHP 8.5 and go from 8.4 to 8.6?**
Yes, and it is the recommended path if your test suite can tolerate one bigger deprecation batch. You pick up 8.5's pipe operator, `#[\NoDiscard]`, closures in constant expressions and fatal-error backtraces along the way.

**What is partial function application good for in real code?**
Pre-binding an argument to produce a `Closure` you can pass to `array_map`, `array_filter` or a framework callback, without writing a one-line arrow function. It is syntax for composition, not a performance feature.

**Do readonly properties with defaults change serialization?**
They change initialization ergonomics, not serialization. A readonly property with a default still cannot be written after construction; you simply no longer have to thread every default through the constructor signature.

**How long is PHP 8.6 supported?**
Active bugfix support runs to 31 December 2028, with security-only fixes through 31 December 2030 — the longest window in the table above, which is the practical argument for landing on 8.6 rather than 8.5.

**What should I fix first?**
`return` inside `finally`, then the `__construct()`/`__destruct()` return rules, then the `define()` third argument. Those three cover most legacy codebases, and all of them are mechanical edits.

For dependency management across the upgrade, our [Composer repository guide](../2026-06-16-self-hosted-php-composer-repositories-satis-packeton-satisfy/) covers private package hosting with Satis, Packeton and Satisfy, which matters when a platform bump invalidates a cached mirror. If the upgrade forces you to revisit spreadsheet or export code, the [spreadsheet generation libraries comparison](../2026-06-20-spreadsheet-generation-libraries-openpyxl-xlsxwriter-excelize-phpspreadsheet/) includes PhpSpreadsheet's version constraints.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP 8.6 Upgrade Guide 2026: Partial Function Application, Readonly Defaults, and the Deprecations That Break CI",
  "description": "A practical PHP 8.6 upgrade guide covering the 2026 support cutoffs for 8.2 and 8.4, partial function application, readonly property defaults, runtime breaking changes and every deprecation that fails CI under E_ALL.",
  "datePublished": "2026-11-28",
  "dateModified": "2026-11-28",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
