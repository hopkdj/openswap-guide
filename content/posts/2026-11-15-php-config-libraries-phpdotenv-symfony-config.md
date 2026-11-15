---
title: "phpdotenv vs Symfony Config vs Hassankhan Config in 2026: Which PHP Config Layer Holds Up?"
date: "2026-11-15"
draft: false
tags: ["php", "configuration", "symfony", "phpdotenv", "developer-tools"]
description: "A practical comparison of three PHP configuration approaches — vlucas/phpdotenv, symfony/config and hassankhan/config — with real code, validation behavior and deployment pitfalls."
cover: "/img/screenshots/php-config-cover.jpg"
---

The shortest path to a production incident in PHP is an unset environment variable. A missing `DATABASE_HOST` turns into a connection timeout at 3 a.m.; a typo'd `REDIS_PORT` silently falls back to 6379 and points your cache at the wrong cluster. PHP's configuration story is fragmented precisely because three different libraries solve three different parts of the problem, and most teams install two of them by accident.

**vlucas/phpdotenv** loads `.env` files into the process environment. **symfony/config** defines a validated configuration tree with merging, normalization and compiled caching. **hassankhan/config** loads JSON, INI, XML, YAML or PHP files with dot-notation access and almost no ceremony. They are not interchangeable, and picking the wrong one shows up as either "our config is an untested array" or "we wrote 300 lines of tree definitions for four settings".

## TL;DR: Quick Verdict

**Use phpdotenv for environment secrets and nothing else** — it is the standard way to get `DATABASE_URL` into `$_ENV` locally without committing credentials, and its `required()->notEmpty()->isInteger()` validation chain catches typos at boot. **Use symfony/config if you have layered configuration** — multiple YAML files, environment overrides, defaults, and a tree that must be identical in every environment. **Use hassankhan/config only for small tools** where a JSON file plus `get('app.debug', false)` is the entire requirement; its last commit was February 2025, so treat it as a convenience, not a foundation. Real applications usually want **phpdotenv for secrets plus symfony/config for structure** — the two compose cleanly, and pretending one replaces the other is how you end up with unvalidated arrays.

## Head-to-Head Comparison (November 2026)

| Dimension | vlucas/phpdotenv | symfony/config | hassankhan/config |
|---|---|---|---|
| GitHub stars | **13,554** | **4,277** | **974** |
| Last commit | 2026-10-25 | 2026-11-13 | **2025-02-14** |
| License | BSD-3-Clause | MIT | MIT |
| Input formats | `.env` only | YAML, XML, PHP, INI (via loaders) | JSON, INI, XML, YAML, PHP |
| Validation | Chainable assertions on env vars | **Full tree: types, ranges, enums, defaults** | None |
| Merging / precedence | File order + immutable vs mutable | **Yes, ordered config arrays** | Multiple files, `?` optional files |
| Compiled cache | No | **Yes** (`ConfigCache`, resource freshness) | No |
| Dot-notation access | No | No (arrays) | **Yes** |
| Write back to environment | Yes (`putenv`, `$_ENV`, `$_SERVER`) | No | No |
| Typical role | Secrets bootstrap | Application config schema | Lightweight file reader |
| Failure mode | Silent precedence surprises | Verbose tree boilerplate | No validation at all |

All star counts, commit dates and licenses were read from the GitHub API on 2026-11-15.

## Decision Matrix: Ten-Second Choice

| Your situation | Choose | Why |
|---|---|---|
| Need `DATABASE_URL` out of the repo | **phpdotenv** | Purpose-built; `required()` fails fast at boot |
| Several YAML files merged per environment | **symfony/config** | `Processor` merges arrays and validates the tree |
| Config file is JSON and read once at boot | **hassankhan/config** | Two lines to a working reader |
| Need compile-time-ish caching of parsed config | **symfony/config** | `ConfigCache` regenerates on resource change |
| Small CLI script, no framework | **hassankhan/config** or bare `json_decode` | Avoid pulling in a component tree |
| Kubernetes with env-injected secrets | **phpdotenv (dev only)** | In prod, read real env vars; no `.env` file at all |
| Multi-tenant app with per-tenant overrides | **symfony/config** | Ordered merging is the whole feature |

## phpdotenv: Secrets Bootstrap, Not a Config System

phpdotenv has one job: read a `.env` file and populate the process environment. Its important design decision is **immutability**. `createImmutable()` will not overwrite a variable that already exists in `$_SERVER` or `$_ENV`, which means real environment variables injected by Docker or Kubernetes always win over the file — exactly the precedence you want, and exactly the behavior people accidentally break by reaching for `createMutable()`.

```php
// Loads .env from the current directory, without overwriting real env vars
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();

// Same, but silently skip if the file does not exist (useful in CI)
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->safeLoad();
```

Multiple files are supported, and the third argument controls mutability while the fourth sets the encoding:

```php
$dotenv = Dotenv\Dotenv::createImmutable(
    __DIR__,
    ['.env', '.env.local'],
    false,      // do not allow overwriting
    'UTF-8'
);
$dotenv->load();
```

The half of the library most projects ignore is its validation API, which is the cheapest possible guard against typo-driven outages:

```php
$dotenv->required('DATABASE_DSN');
$dotenv->required(['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASS']);

$dotenv->required('DATABASE_DSN')->notEmpty();
$dotenv->required('FOO')->isInteger();
$dotenv->required('FOO')->isBoolean();
$dotenv->required('SESSION_STORE')->allowedValues(['Filesystem', 'Memcached']);
$dotenv->required('FOO')->allowedRegexValues('([[:lower:]]{3})');
```

That is the entire value proposition: fail at boot with a clear message instead of failing later with a null. What phpdotenv will **not** do is give you structure. Nested settings, defaults, environment merging, and type coercion all have to be written by hand — which is where the second library comes in.

Two traps worth memorizing. First, `getenv()` and `$_ENV` can diverge depending on `variables_order` in `php.ini`; the library writes to `$_ENV` and `$_SERVER`, so read from those, not from `getenv()`, unless you deliberately use the unsafe variants. Second, `.env` must never be committed and must never be baked into an image — the moment a secret lands in a layer, it is public.

## symfony/config: A Schema for Your Settings

symfony/config is a different species: you describe the shape of your configuration as a tree, then hand raw arrays to a `Processor` that merges them and rejects anything that does not match. It is the component that makes "config is validated" true rather than aspirational.

```php
use Symfony\Component\Config\Definition\Builder\TreeBuilder;
use Symfony\Component\Config\Definition\ConfigurationInterface;

class DatabaseConfiguration implements ConfigurationInterface
{
    public function getConfigTreeBuilder(): TreeBuilder
    {
        $treeBuilder = new TreeBuilder('database');

        // ... add node definitions to the root of the tree
        // $treeBuilder->getRootNode()->...

        return $treeBuilder;
    }
}
```

Node definitions give you types, defaults and ranges without writing a single `if`:

```php
$rootNode
    ->children()
        ->integerNode('positive_value')
            ->min(0)
        ->end()
        ->floatNode('big_value')
            ->max(5E45)
        ->end()
        ->integerNode('value_inside_a_range')
            ->min(-50)->max(50)
        ->end()
    ->end();
```

Node types cover scalar, boolean, string, integer, float, enum, array and variable (no validation), and building with `node($name, $type)` or the shortcut `booleanNode()`, `stringNode()` and friends keeps definitions readable. The documentation is explicit about one rule that matters in containerized deployments: **build the tree from static information only.** Never read environment variables or machine state while constructing the tree — it must be identical in every environment, or your compiled cache becomes environment-specific and wrong.

Processing merges an ordered list of arrays, so later files override earlier ones and defaults fill the gaps:

```php
use Acme\DatabaseConfiguration;
use Symfony\Component\Config\Definition\Processor;
use Symfony\Component\Yaml\Yaml;

$config = Yaml::parse(file_get_contents(__DIR__.'/config/config.yaml'));
$extraConfig = Yaml::parse(file_get_contents(__DIR__.'/config/config_extra.yaml'));

$configs = [$config, $extraConfig];

$processor = new Processor();
$databaseConfiguration = new DatabaseConfiguration();
$processedConfiguration = $processor->processConfiguration(
    $databaseConfiguration,
    $configs
);
```

If any value is the wrong type, mandatory and missing, or fails a constraint, `processConfiguration` throws — at deploy time, not at request time. That is the single biggest reliability difference between this library and a `json_decode()` call.

Caching closes the loop. `ConfigCache` records which files produced the cached output and regenerates when any of them changes:

```php
use Symfony\Component\Config\ConfigCache;
use Symfony\Component\Config\Resource\FileResource;

$cachePath = __DIR__.'/cache/appUserMatcher.php';

// second argument = debug mode
$userMatcherCache = new ConfigCache($cachePath, true);

if (!$userMatcherCache->isFresh()) {
    $yamlUserFiles = /* array of YAML paths */;
    $resources = [];

    foreach ($yamlUserFiles as $yamlUserFile) {
        $delegatingLoader->load($yamlUserFile);
        $resources[] = new FileResource($yamlUserFile);
    }

    // ... write compiled output through $userMatcherCache->write($code, $resources)
}
```

The cost is real: a config tree for a mid-sized application is a few hundred lines, and every new setting means editing the definition class, the defaults, and often the documentation. Teams under ten settings usually find that price too high and stop at phpdotenv plus a typed settings object.

## hassankhan/config: The Two-Line Reader

hassankhan/config exists for the case where you have a config file and want its values without ceremony. It auto-detects the format from the extension, supports multiple files with later ones overriding, and gives you dot-notation access:

```php
use Noodlehaus\Config;

$conf = new Config('config.json');
$conf = new Config(['config.json', 'config.xml']);
$conf = new Config(__DIR__ . '/config');

// optional file: the "?" prefix means "load if present"
$conf = new Config(['config.dist.json', '?config.json']);

// explicit parser instead of extension detection
$conf = new Config('configuration.config', new Noodlehaus\Parser\Json());
```

Reading values is where the dot notation pays off:

```php
$debug  = $conf->get('debug');
$secret = $conf->get('security.secret');
$ttl    = $conf->get('app.timeout', 3000);   // default when missing
```

Custom defaults are supported by extending `AbstractConfig` and populating `getDefaults()`, which is a neat trick for shipping a `config.dist.json` alongside an optional local override.

What it does not give you is validation. `get('app.timeout', 3000)` returns whatever the file contains; if someone writes `"30s"`, you get a string where an integer belongs, and PHP will coerce it silently in arithmetic. Combine that with a last commit in February 2025 and the honest conclusion is: fine for a small internal tool, wrong foundation for a service with SLAs.

## Pitfalls That Cause Real Outages

**1. `.env` files leak through image layers.** Copy `.env` in a `Dockerfile` once and it stays in the layer history forever, even after you delete it in a later step. Use `.dockerignore`, inject secrets at runtime, and add a `required('APP_KEY')` assertion so a missing secret fails the container immediately.

**2. Immutable vs mutable is a precedence decision, not a style choice.** `createMutable()` overwrites existing environment variables — which breaks the "real env wins" contract that makes the same code work locally and in Kubernetes. Default to immutable.

**3. Config caches go stale in ways `git status` cannot see.** Symfony's `ConfigCache` is only as correct as the resource list you give it. If you add a file to the loader but forget `new FileResource($path)`, production keeps serving yesterday's config until the cache directory is cleared.

**4. YAML parsing is not a security boundary.** `Yaml::parse()` with object support enabled lets a config file instantiate classes. Parse untrusted config with object support disabled, and never load configuration from a path an end user controls.

**5. Dot-notation collides with literal dots.** A key named `app.timeout` in a JSON file is indistinguishable from a nested `app: { timeout: ... }` when read through hassankhan/config. Pick one convention and enforce it.

**6. Environment-specific trees break compiled config.** Reading `$_ENV` inside a `TreeBuilder` produces a tree that differs per environment; anything compiled from it becomes unusable elsewhere. Keep trees static and inject environment values as the processed arrays instead.

**7. Twelve-factor purists still need defaults.** In production, read the real environment and skip `.env` entirely — but keep sensible defaults for timeouts so a missing optional variable does not crash the boot.

```yaml
services:
  app:
    image: ghcr.io/your-org/api:latest
    env_file:
      - .env.local          # local development only
    environment:
      APP_ENV: production
      DATABASE_URL: ${DATABASE_URL}   # injected by the platform, wins over env_file
```

## FAQ

**Do I need both phpdotenv and symfony/config?**
Usually yes, and for different reasons. phpdotenv moves secrets from a file into the environment; symfony/config validates and merges structured settings. A typical bootstrap loads `.env` first, then feeds the resulting arrays into a `Processor`. Neither library is designed to do the other's job.

**Is phpdotenv safe for production?**
It is safe in the sense that it does not weaken anything, but it is unnecessary in production if your platform injects environment variables directly. Loading a `.env` file in production risks stale values overriding nothing at all — real env vars still win with `createImmutable`, but a missing variable in the platform is better caught by a required assertion than by a leftover file.

**Can symfony/config validate an enum?**
Yes. The enum node type accepts a finite set of values, and violations throw during `processConfiguration`. For older versions, an `enumNode()` with `->values([...])` gives the same effect; either way the failure happens at boot, before any request is served.

**How do I handle secrets that must not live in YAML?**
Keep them in environment variables and reference them by name in your tree, resolving the actual value in a service factory or through Symfony's secret management. Never interpolate a secret into a compiled config cache file, because that file lands on disk in plaintext.

**Is hassankhan/config abandoned?**
Not formally — the repository is public and the MIT license stands — but its last commit was February 2025, so it is effectively in maintenance mode. For a small tool that is fine; for long-lived services, prefer symfony/config or a hand-written typed settings class you control.

## Further Reading

If you are wiring this into a runtime, our [PHP application server comparison](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/) covers Swoole, RoadRunner and FrankenPHP — all of which change how environment variables reach workers. Session and cookie configuration is the other half of the same problem, covered in the [PHP session management guide](../2026-07-05-php-session-management-native-symfony-laravel/). For a cross-language view of the same trade-offs, the [application configuration libraries comparison](../2026-06-21-application-configuration-libraries-viper-koanf-configrs-typesafe/) looks at Viper, Koanf, config-rs and Typesafe Config.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "phpdotenv vs Symfony Config vs Hassankhan Config in 2026: Which PHP Config Layer Holds Up?",
  "description": "Comparison of PHP configuration libraries: vlucas/phpdotenv for environment secrets, symfony/config for validated configuration trees, and hassankhan/config for lightweight file loading.",
  "datePublished": "2026-11-15",
  "dateModified": "2026-11-15",
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
