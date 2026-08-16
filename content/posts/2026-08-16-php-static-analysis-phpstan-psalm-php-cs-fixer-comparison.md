---
title: "PHPStan vs Psalm vs PHP-CS-Fixer in 2026: Which PHP Code Quality Tool Should You Use?"
date: "2026-08-16"
tags: ["php", "static-analysis", "code-quality", "phpstan", "psalm", "php-cs-fixer", "developer-tools"]
draft: false
cover: "/img/screenshots/phpstan-cover.jpg"
---

Your PHP app passes every test, ships to production, and then dies at 3 a.m. because a null slipped through an array offset that nobody thought to check. Static analysis exists precisely to catch that bug before your CI pipeline ever runs a single test. PHPStan, Psalm, and PHP-CS-Fixer are the three tools that dominate PHP code quality in 2026 — but they solve three different problems, and teams that pick the wrong one (or skip two of them) pay for it in production incidents and review burn-out. Here's the honest, data-backed comparison: what each tool actually does, how they differ, and which combination you should standardize on. It pairs naturally with our [PHP testing frameworks comparison](../2026-07-23-php-testing-frameworks-phpunit-pest-codeception-behat-phpspec/) — analyzers tell you what's wrong, tests prove behavior — and with our [PHP ORM libraries guide](../2026-07-06-php-orm-libraries-laravel-eloquent-doctrine-propel/), since typed model layers are exactly what lets you push PHPStan to higher levels.

## TL;DR — Quick Verdict

**Adopt PHPStan as your default analyzer** — it has the largest ecosystem (14,072 stars), the fastest release cadence, and the clearest upgrade path with its level system. **Add Psalm only if you need taint analysis for security-sensitive code** or you're already deep in a Symfony-adjacent stack; its taint mode is genuinely unique. **Treat PHP-CS-Fixer as a formatting gate, not an analyzer** — it fixes style, and it should run in your pipeline before your analyzers so style noise never drowns real findings. Small or legacy codebases: start PHPStan at level 0 and raise one level per sprint. If you can only run one tool, run PHPStan.

## Quick Comparison: The 2026 Landscape

| Dimension | PHPStan | Psalm | PHP-CS-Fixer |
|---|---|---|---|
| **What it does** | Type-aware static analysis (bugs without running code) | Static analysis + taint/security tracing | Automatic PSR-12/coding-standards fixing |
| **GitHub stars** | **14,072** | 5,882 | 13,548 |
| **Last push** | 2026-08-15 (very active) | 2026-07-13 (active) | 2026-08-16 (very active) |
| **Install** | `composer require --dev phpstan/phpstan` | `composer require --dev vimeo/psalm` | `composer require --dev friendsofphp/php-cs-fixer` |
| **Config file** | `phpstan.neon` / `.neon.dist` | `psalm.xml` / `psalm.xml.dist` | `.php-cs-fixer.php` / `.php-cs-fixer.dist.php` |
| **Difficulty ramp** | Levels 0–9, opt-in per level | Error levels 1–8, auto-detected at init | Flat: ruleset in, fixes out |
| **Unique killer feature** | Baseline + bleeding-edge rule set | Taint analysis (SQLi/XSS/SSRF tracing) | `--diff` mode for reviewable style changes |
| **False positives** | Moderate, tamed by baseline | Moderate, tamed by suppressions | None (formatting only) |
| **Runs on** | CLI, PHPStan Pro web UI | CLI, Docker image | CLI, PHPStorm integration |
| **License** | MIT | MIT | MIT |

## Use-Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| "We can afford exactly one quality tool" | PHPStan | Biggest ecosystem, best docs, level system scales with your codebase maturity |
| "Our app handles credit cards / auth / file uploads" | Psalm (add to PHPStan) | Taint analysis traces user input into sinks — PHPStan won't flag an unsanitized query string the same way |
| "PRs fail because of formatting bikeshedding" | PHP-CS-Fixer | `--dry-run --diff` turns style debates into a machine decision |
| "Legacy codebase with zero types" | PHPStan at level 0 | Start with `level: 0`, add `declare(strict_types=1)` file by file, raise the level as you go |
| "We use PHPUnit and want CI gates" | All three in one workflow | Analyze → fix → test; each catches what the others miss |
| "Frameworks: Laravel / Symfony / Drupal" | PHPStan + official extension | Larastan, PHPStan-Symfony, and phpstan-drupal cover framework magic methods PHPStan can't infer alone |

## PHPStan — The Default Choice for a Reason

PHPStan (phpstan/phpstan, 14,072 stars, last push 2026-08-15) positions itself as "discover bugs in your code without running it." It builds a type model of your entire codebase — classes, generics, array shapes, docblock types — and then walks every code path looking for operations that violate that model. It catches whole bug classes before you write tests: calling methods on possibly-null objects, passing the wrong types to functions, unreachable code, and mismatched array keys.

The genius of PHPStan is the **level system**. Levels run from 0 (basic checks: undefined variables, unknown classes) to 9 (strictest: mixed types, generics, precise array shapes). You opt into strictness gradually, so a 15-year-old codebase isn't a rewrite project — it's a level-0 ticket that climbs one level per sprint.

Install and first run:

```bash
composer require --dev phpstan/phpstan
./vendor/bin/phpstan analyse src --level=6
```

A minimal `phpstan.neon` — the config is loaded automatically when you run the command from the project root:

```neon
parameters:
    level: 6
    paths:
        - src
    tmpDir: /tmp/phpstan
    parallel:
        maximumNumberOfProcesses: 4
```

Two features make PHPStan painless at scale. **The baseline**: `vendor/bin/phpstan analyse --generate-baseline` snapshots every current error into `phpstan-baseline.neon`, so CI starts green and every new violation is visible in the diff — you pay down the baseline debt at your own pace. **Bleeding edge**: the `bleedingEdge` rule set (added in 2.x) turns on experimental checks early, giving you a preview of the next level's strictness. For Laravel, Symfony, and Drupal projects, the official extensions (Larastan, phpstan/extension-installer) teach the analyzer about framework magic — without them you'll drown in false positives about `Model::where()` return types.

The catch: PHPStan is strict about docblocks, and on untyped legacy code it will nag constantly until you add types. That nagging is the point — it's a directed, mechanical path to a fully typed codebase.

## Psalm — Security-First Analysis with Taint Tracing

Psalm (vimeo/psalm, 5,882 stars, last push 2026-07-13) was built at Vimeo and does the same class of type inference as PHPStan — with one feature nobody else matches: **taint analysis**. Psalm traces user-controlled input from its entry point (request bodies, query strings, file uploads) through your entire application to dangerous sinks (SQL queries, `eval()`, `header()`, file writes, `unlink()`), flagging every path where unsanitized input can reach one. That is precisely the class of bug — SQL injection, stored XSS, SSRF — that type analysis alone will never catch, because the types are all technically correct.

Install and initialize — Psalm scans your project and picks an appropriate error level for you:

```bash
composer require --dev vimeo/psalm
./vendor/bin/psalm --init
./vendor/bin/psalm --no-cache
```

Psalm's own docs recommend running it in the official Docker image — a custom PHP build that runs Psalm **+30% faster** on average (up to +50% vs. PHP without opcache):

```bash
docker run -v $PWD:/app --rm -it ghcr.io/danog/psalm:latest /composer/vendor/bin/psalm --no-cache
```

For teams that can't use Composer, Psalm ships a self-contained Phar:

```bash
wget https://github.com/vimeo/psalm/releases/latest/download/psalm.phar
chmod +x psalm.phar
./psalm.phar --version
```

Psalm's error levels run 1–8 (1 = strictest), and it's the friendlier of the two analyzers for gradual adoption: `--init` scans your code and suggests a starting level rather than forcing one on you. Its security mode (`--taint-analysis`) is a separate pass you can run in CI nightly. The trade-off is momentum — Psalm's release cadence has slowed compared to PHPStan, and its plugin ecosystem is smaller. Use it where its unique value pays for itself: anything that touches user input and talks to a database.

## PHP-CS-Fixer — the Formatting Gate That Ends Style Wars

PHP-CS-Fixer (PHP-CS-Fixer/PHP-CS-Fixer, 13,548 stars, last push 2026-08-16) is not an analyzer — it's the referee. It enforces a coding standard (PSR-12 by default) across your whole codebase and rewrites files to comply. In 2026 every serious PHP project runs it in CI as a gate: `--dry-run` fails the build if any file deviates, `--diff` shows exactly what would change.

Install and configure — the config file `.php-cs-fixer.dist.php` is plain PHP, so it can be version-controlled and shared across the team:

```bash
composer require --dev friendsofphp/php-cs-fixer
```

```php
<?php

$finder = PhpCsFixer\Finder::create()
    ->in(__DIR__ . '/src')
    ->in(__DIR__ . '/tests')
    ->exclude('vendor');

return (new PhpCsFixer\Config())
    ->setRiskyAllowed(true)
    ->setRules([
        '@PSR12' => true,
        'strict_param' => true,
        'array_syntax' => ['syntax' => 'short'],
        'no_unused_imports' => true,
        'ordered_imports' => ['sort_algorithm' => 'alpha'],
    ])
    ->setFinder($finder);
```

Run it in review mode (never mutates, just reports):

```bash
vendor/bin/php-cs-fixer fix --dry-run --diff
```

The `--diff` output is the killer feature: a PR that fails the style gate comes back with a machine-readable, copy-pasteable patch instead of a 40-comment review thread. Run PHP-CS-Fixer *first* in your pipeline — before PHPStan and Psalm — so style noise never buries a real type error. It has no false positives because it doesn't reason about semantics; it only reshapes syntax. The main risk is configuration sprawl: dozens of rules can tempt teams into bespoke standards that fight the ecosystem. Default to PSR-12, add a handful of ergonomic rules, and stop there.

## Building the Complete Quality Pipeline

The three tools compose into a single CI workflow — and the order matters. Fix style first, then analyze, then test:

```yaml
# .github/workflows/php-quality.yml (GitHub Actions)
name: PHP Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          coverage: xdebug
      - run: composer install --no-interaction

      - name: Fix code style
        run: vendor/bin/php-cs-fixer fix --dry-run --diff

      - name: Static analysis
        run: vendor/bin/phpstan analyse src --no-progress

      - name: Taint analysis
        run: vendor/bin/psalm --taint-analysis --no-cache
```

A realistic 2026 stack on a mid-size Laravel or Symfony app: PHP-CS-Fixer enforces style, PHPStan at level 6–8 (with the framework extension and a baseline) catches type bugs, Psalm's taint mode runs nightly to catch injection paths, and PHPUnit confirms behavior — the same tools that power the [PHP CLI frameworks](../2026-08-15-php-cli-frameworks-symfony-console-wp-cli-laravel-zero-comparison/) you likely use for cron jobs and console commands. Each tool's false-positive profile is different, which is exactly why the trio beats any single tool: PHPStan's baseline quarantines legacy debt, Psalm's suppressions are file- and line-scoped, and PHP-CS-Fixer never needs a suppression because it never reasons.

## Common Pitfalls (and How to Avoid Them)

1. **Running analyzers without a baseline on legacy code.** The first run on an untyped codebase produces hundreds of errors, the team gets overwhelmed, and the tool gets deleted from the pipeline. Always start with `--generate-baseline` (PHPStan) or `--set-baseline` (Psalm) so day one is green.
2. **Mistaking PHP-CS-Fixer for an analyzer.** It will happily format a file whose types are wrong. Style gates and type analysis solve different problems — running only a fixer gives you a beautiful codebase with the same bugs.
3. **Ignoring framework extensions.** Bare PHPStan on a Laravel codebase flags every `Model::query()` and `Collection` chain as an error. Larastan / PHPStan-Symfony / phpstan-drupal eliminate the vast majority of false positives. Skipping them is the #1 reason teams abandon PHPStan.
4. **Raising PHPStan levels faster than types land.** Level 9 demands `mixed`-free signatures. If your codebase still has `array` params everywhere, level 9 will block the build forever. Raise one level per sprint, not per day.
5. **Psalm without `--taint-analysis`.** The analyzer alone is a PHPStan alternative; the taint pass is the reason to run it at all. Teams that install Psalm and never enable taint mode get ~70% of the value with 100% of the maintenance cost.
6. **Letting style rules explode.** Every bespoke rule is a future migration cost. PSR-12 plus a few ergonomic rules is enough; treat anything beyond that as a proposal, not a default.
7. **Not pinning versions in CI.** PHPStan and PHP-CS-Fixer release aggressively (weekly-ish). Unpinned `composer install` in CI means a Monday-morning update can fail your build with a brand-new rule. Pin with `composer.lock` and upgrade deliberately.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHPStan vs Psalm vs PHP-CS-Fixer in 2026: Which PHP Code Quality Tool Should You Use?",
  "description": "In-depth 2026 comparison of PHPStan, Psalm, and PHP-CS-Fixer: how static analysis and code style fixing differ, real GitHub data, level systems, taint analysis, CI pipeline design, and migration pitfalls.",
  "datePublished": "2026-08-16",
  "dateModified": "2026-08-16",
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

**Can PHPStan and Psalm run in the same project?**
Yes, and it's common. They read the same composer autoloader and both respect `@phpstan-*` / `@psalm-*` docblock annotations independently. Teams typically run PHPStan on every push and Psalm's taint mode nightly or on security-sensitive paths. Duplicate warnings are rare because the tools disagree about far fewer things than people expect.

**What's the difference between static analysis and a code style fixer?**
Static analysis (PHPStan, Psalm) builds a type model and reasons about runtime behavior — null dereferences, type mismatches, unreachable code, injection paths. A style fixer (PHP-CS-Fixer) only rewrites syntax to match a standard like PSR-12. One finds bugs; the other ends formatting debates. They're complementary, not alternatives.

**Which PHPStan level should a new project use?**
Level 6 is the community default — it enables most type checks including return type inference, while leaving `mixed`-related strictness for later. Teams that write strict types from day one can start at level 8. The official PHPStan docs describe each level's exact rule set; raise the level in CI before every release.

**Is Psalm still maintained in 2026?**
Yes. Psalm's last push was 2026-07-13, it's under a new active maintainer (Daniil Gentili), and its taint analysis remains the most powerful security pass available for PHP — no other tool traces user input to dangerous sinks across method calls and include boundaries. Its slower cadence vs. PHPStan is the trade-off, not a sign of abandonment.

**Do I need a baseline if my code is already clean?**
No — a baseline only snapshots existing errors. If PHPStan returns zero errors at your target level, you don't need one. But add it the moment you adopt the tool on a codebase with history, even if you think it's clean; the first `--level=6` run always surprises you.

**How do these tools fit into CI without slowing it down?**
PHPStan runs in parallel processes (`parallel.maximumNumberOfProcesses`), Psalm's Docker image is measurably faster than stock PHP, and PHP-CS-Fixer only touches changed files when you scope the finder. On a mid-size app the full quality gate adds 1–3 minutes — cheap compared to the production incident it prevents.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
