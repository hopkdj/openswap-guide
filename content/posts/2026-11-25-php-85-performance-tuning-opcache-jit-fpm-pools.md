---
title: "PHP 8.5 Performance Tuning in 2026: OPcache, JIT and php-fpm Pools That Actually Scale"
date: "2026-11-25"
tags: ["php", "performance", "opcache", "php-fpm", "tuning", "web"]
draft: false
cover: "/img/screenshots/php-opcache-tuning-cover.jpg"
---

A sixteen-core PHP server saturates at 380 requests per second while the CPU graph shows one core pinned and fifteen idle. The team adds four more cores. Throughput moves to 402 requests per second. That is the signature of a PHP deployment whose bottleneck is not hardware but four INI values nobody ever changed from the commented-out defaults shipped in `php.ini-production`.

This guide covers the tuning levers that produce measurable, repeatable gains in 2026: **OPcache sizing, the real cost/benefit of JIT, php-fpm pool math, realpath caching, and opcache preloading**. Every default value quoted below is taken from the shipped `php.ini-production` and `sapi/fpm/www.conf.in` in the official [php/php-src](https://github.com/php/php-src) repository (**41,867 stars**, last push 2026-11-25). Current stable releases at the time of writing: **PHP 8.5.13**, 8.4.28, 8.3.37 (all tagged 2026-11-21).

## Quick Verdict (TL;DR)

- **If you run a request/response app (Laravel, Symfony, WordPress, Magento):** fix OPcache sizing, realpath cache, and fpm pool sizing first. Those three deliver **2x-6x**. JIT usually delivers **0-8%** and occasionally makes things slower.
- **If you run CPU-bound PHP** (encoding, parsing, cryptography, math, report generation): enable JIT with `opcache.jit=tracing` and a 64M-128M buffer. Real gains land between **15% and 40%** on hot loops.
- **If you run a long-lived worker** (queue consumers, websockets), JIT plus `opcache.enable_cli=1` matters, but memory leaks surface faster — cap `pm.max_requests`.
- **Never** tune with `pm = dynamic` and `pm.max_children` left at the template's `5`. That single line is the most common cause of "PHP is slow" tickets.

## The Levers, Ranked by Return on Effort

| Lever | What it removes | Typical gain | Risk | Config knob |
|---|---|---|---|---|
| OPcache memory + file count | Recompiling every request | **2-4x** | Low | `opcache.memory_consumption`, `opcache.max_accelerated_files` |
| php-fpm pool sizing | Queueing behind too few workers | **2-5x** under load | Medium (RAM) | `pm`, `pm.max_children` |
| realpath cache | `stat()` syscalls per include | **5-20%** | Low | `realpath_cache_size`, `realpath_cache_ttl` |
| OPcache preloading | Per-request class linking | **10-30%** on frameworks | Medium (restart cost) | `opcache.preload` |
| JIT | Interpreter dispatch in hot loops | **0-40%** (workload-dependent) | Medium | `opcache.jit`, `opcache.jit_buffer_size` |
| File cache for OPcache | Cold start after deploy | **1-3x on first requests** | Low | `opcache.file_cache` |
| App server (RoadRunner/FrankenPHP) | Bootstrap per request | **2-10x** | High (rewrite) | N/A |

The ordering matters. Teams routinely jump to JIT and app servers because those are the exciting options, then discover the deployment was still recompiling 1,900 PHP files per request.

## The Decision Matrix

| Your situation | Do this | Why |
|---|---|---|
| Standard LAMP/LNMP app, < 100 req/s | OPcache + realpath + `pm=dynamic` sized properly | Fastest path to a stable baseline |
| High-traffic API, 500+ req/s | `pm=static` with measured `max_children`, status page exported | Removes pool resizing churn entirely |
| CPU-bound batch or report generation | JIT `tracing`, 128M buffer, `opcache.enable_cli=1` | Hot loops benefit from compiled traces |
| Large framework, deploy several times a day | Preload + `opcache.file_cache`, restart fpm atomically | Cuts cold-start after every release |
| Container with 512 MB limit | `pm=ondemand`, small OPcache, no preload | Memory predictability beats throughput |
| Legacy app with `include_path` sprawl | Raise `realpath_cache_size` to 4096k-16384k | Filesystem stats dominate profiles |

## OPcache: Five Values That Decide Everything

The shipped template is deliberately conservative. In `php.ini-production` the values are commented out, which means PHP runs with compiled defaults: `opcache.memory_consumption=128`, `opcache.interned_strings_buffer=8`, `opcache.max_accelerated_files=16229` (the real internal default is 10000; the template documents 16229), and `opcache.validate_timestamps=1` with `revalidate_freq=2`.

Here is a production block that fits most applications between 500 and 5,000 files:

```ini
[opcache]
opcache.enable=1
opcache.enable_cli=1
opcache.memory_consumption=256
opcache.interned_strings_buffer=32
opcache.max_accelerated_files=20000
opcache.validate_timestamps=0
opcache.revalidate_freq=0
opcache.save_comments=1
opcache.fast_shutdown=1
opcache.jit_buffer_size=0
realpath_cache_size=4096k
realpath_cache_ttl=600
```

Why each one matters:

- **`max_accelerated_files`** is a hash table size, not a limit on cached scripts. When it is too small, OPcache silently stops caching new files and `opcache_get_status()` reports `"cache_full": true`. Measure with `find . -name '*.php' | wc -l` and round up.
- **`validate_timestamps=0`** removes two `stat()` calls per included file per request. It is the single largest win on network filesystems, and it requires an explicit `systemctl reload php*-fpm` (or container restart) on every deploy. If your CD pipeline cannot guarantee that, keep `validate_timestamps=1` and set `revalidate_freq=60`.
- **`interned_strings_buffer`** at the default 8 MB is exhausted by large frameworks. Once full, string interning silently degrades.
- **`save_comments=1`** is required by Doctrine, Symfony annotations, and PHPUnit. Turning it off is a classic "works in staging, explodes in production" mistake.

Verify the result instead of trusting it:

```bash
php -r 'print_r(opcache_get_status(false)["opcache_statistics"]);'
# watch: num_cached_scripts, hits, misses, oom_restarts, hash_restarts, cache_full
```

If `oom_restarts` or `hash_restarts` is non-zero, sizing is wrong. A healthy production instance shows `hash_restarts: 0`, `oom_restarts: 0`, and a hit rate above 99.5%.

## JIT in 2026: Honest Numbers

JIT compiles hot opcode traces into machine code. It does not accelerate I/O, database round-trips, template rendering, or framework bootstrap — which is what most PHP requests actually spend time on. On a typical Laravel page doing 40 ms of database work and 6 ms of PHP execution, a 25% JIT gain on the 6 ms is invisible.

Configuration looks like this:

```ini
opcache.jit_buffer_size=64M
opcache.jit=tracing
opcache.jit_hot_loop=64
opcache.jit_hot_func=127
opcache.jit_hot_return=16
opcache.jit_hot_side_exit=32
```

Two hard rules from production experience:

1. **Never set `opcache.jit_buffer_size` without setting `opcache.jit`.** A non-zero buffer with JIT disabled still reserves memory.
2. **Do not enable JIT on shared hosting or on apps with heavy `eval()` usage.** Trace compilation of dynamically generated code wastes buffer space and can increase memory per worker by 10-20%.

Where JIT genuinely wins: PDF generation, image manipulation, CSV/XLSX exports, cryptographic signing loops, and anything with a tight numeric loop. Benchmark before and after with the same dataset — and measure p99, not just mean, because trace compilation causes a short warm-up spike.

## php-fpm Pool Math You Can Actually Defend

The template ships `pm = dynamic` with `pm.max_children = 5`, `start_servers = 2`, `min_spare = 1`, `max_spare = 3`. On a 16 GB machine that leaves 95% of the RAM unused and forces requests to queue in the listen backlog.

The sizing formula has not changed:

```text
max_children = (total RAM - OS and DB reserve) / average PHP worker RSS
```

Measure the real RSS, do not guess:

```bash
ps -o rss= -C php-fpm8.5 | awk '{sum+=$1; n++} END {printf "workers=%d avg_rss=%.1fMB total=%.1fMB\n", n, sum/n/1024, sum/1024}'
```

For a 16 GB host with 4 GB reserved for MySQL and the OS, and workers averaging 55 MB (Laravel with OPcache and preload sits around 45-70 MB), the ceiling is roughly `12288 / 55 ≈ 223`. Set `max_children` at **70-80% of that ceiling** — 170 — so a traffic spike cannot trigger the OOM killer.

```ini
; /etc/php/8.5/fpm/pool.d/www.conf
user = www-data
group = www-data
listen = /run/php/php8.5-fpm.sock
listen.backlog = 511

pm = static
pm.max_children = 170
pm.max_requests = 1000
pm.status_path = /fpm-status
ping.path = /fpm-ping

request_terminate_timeout = 60s
slowlog = /var/log/php-fpm/slow.log
request_slowlog_timeout = 5s
```

`pm = static` is the right choice for steady high traffic: no fork storms, no resize jitter, predictable memory. Use `dynamic` when traffic is bursty and RAM is shared with other tenants. Use `ondemand` only in memory-constrained containers, where the fork latency on the first request is acceptable.

`pm.max_requests = 1000` is not optional. It caps the blast radius of extension memory leaks. `request_slowlog_timeout` is how you find the endpoint that holds a worker for 40 seconds — without it you are guessing.

Export the status page to your monitoring, not to the public internet:

```nginx
location = /fpm-status {
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    fastcgi_pass unix:/run/php/php8.5-fpm.sock;
    allow 10.0.0.0/8;
    deny all;
}
```

`listen queue: 0`, `max listen queue: 0`, and `active processes < max_children` are the three numbers that tell you the pool is correctly sized. A growing `listen queue` means add workers or fix the slow endpoint.

## Preloading and the Container Deployment

Preloading links classes, interfaces, and functions at fpm start, eliminating per-request autoload and linking work. It costs memory once per worker and a full reload on deploy.

```ini
opcache.preload=/var/www/app/config/preload.php
opcache.preload_user=www-data
opcache.file_cache=/var/cache/php-opcache
opcache.file_cache_only=0
```

A minimal preload script for a framework application:

```php
<?php
// config/preload.php
$dir = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator(__DIR__ . '/../src')
);
foreach ($dir as $file) {
    if ($file->isFile() && $file->getExtension() === 'php') {
        opcache_compile_file($file->getPathname());
    }
}
```

Preloading only pays off when the preloaded set is stable. If your deploy copies files in place while fpm workers are live, preload will hold stale class definitions. Use a blue/green or atomic symlink release plus `systemctl reload php8.5-fpm`.

A working container layout looks like this:

```yaml
services:
  php:
    image: php:8.5-fpm-alpine
    volumes:
      - ./app:/var/www/app
      - ./php-prod.ini:/usr/local/etc/php/conf.d/99-prod.ini:ro
      - ./www.conf:/usr/local/etc/php-fpm.d/zz-www.conf:ro
    deploy:
      resources:
        limits:
          memory: 4G
    healthcheck:
      test: ["CMD-SHELL", "cgi-fcgi -bind -connect 127.0.0.1:9000 || exit 1"]
      interval: 15s
      retries: 3

  nginx:
    image: nginx:1.29-alpine
    volumes:
      - ./app:/var/www/app:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "8080:80"
    depends_on:
      - php
```

Note the ordering: the `www.conf` override must sort after the image's default file, hence the `zz-` prefix. And `memory: 4G` with `pm.max_children` sized for 55 MB workers caps you near 60 workers — the container limit, not the host, becomes the real ceiling.

If you later outgrow classical fpm, read our comparison of [PHP application servers: Swoole, RoadRunner and FrankenPHP](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/) before rewriting anything. For the web tier in front of fpm, the [OpenResty vs nginx vs Caddy guide](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) covers the buffering and FastCGI settings that pair with these pool options. And if sessions are your per-request latency source, our [Redis high availability guide](../2026-05-15-self-hosted-redis-high-availability-sentinel-cluster-keydb-guide/) explains the sentinel and cluster layouts that keep session reads under a millisecond.

## A Benchmark Loop That Produces Trustworthy Numbers

Tuning without measurement produces folklore. A minimal, honest loop:

```bash
# 1. Baseline before any change
wrk -t4 -c200 -d60s --latency http://127.0.0.1:8080/health

# 2. Change exactly one lever, reload
systemctl reload php8.5-fpm

# 3. Re-measure, compare p50/p99 and req/s
wrk -t4 -c200 -d60s --latency http://127.0.0.1:8080/health
```

Then confirm the app, not just the endpoint: `opcache_get_status()` for cache health, the fpm status page for queue depth, and `perf top` for where CPU time actually goes. If `perf` shows userland time inside `zend_execute`, JIT is worth testing. If it shows `sys` time in `stat` or `read`, fix realpath cache and OPcache first — JIT will do nothing.

## Pitfalls That Cost Real Incidents

- **`validate_timestamps=0` without a deploy hook.** Code changes silently do not apply. Always pair it with a reload step in CI.
- **Setting `max_accelerated_files` below your file count.** OPcache reports `cache_full: true` and behaves worse than no cache. Check after every major dependency upgrade.
- **Oversizing `pm.max_children` on a host that also runs the database.** The OOM killer picks the largest RSS consumer — usually MySQL, not PHP.
- **Enabling JIT on WordPress with opcode-heavy plugins.** Measured regressions of 5-10% occur; always A/B it.
- **`opcache.preload` pointing at a file that changes per release without a reload.** Preload is per-worker and only read at fpm start.
- **Using `memory_limit = -1`.** One runaway loop takes the whole worker pool down instead of one request.

## FAQ

**Does OPcache work with `pm = ondemand`?**
Yes. OPcache is shared memory owned by the master process, independent of the pool mode. Only `opcache.preload` behavior is affected: preloading happens once at master start, and ondemand workers inherit the preloaded shared memory.

**Is JIT worth enabling on PHP 8.5 for a typical CRUD application?**
Usually not. If profiling shows more than 30% of request time inside PHP userland execution rather than I/O or database calls, test it. Otherwise spend the effort on OPcache sizing, realpath cache, and pool sizing, which reliably deliver multiples rather than percentages.

**What `pm.max_children` value should a 4 GB container use?**
Measure worker RSS first. With 55 MB workers and 1 GB reserved for the OS and sidecars, `3072 / 55 ≈ 55`. Set 40-45 to leave headroom. Never copy a value from another host — worker RSS varies by 3x between frameworks.

**Do I still need `realpath_cache_size` tuning with OPcache enabled?**
Yes. OPcache caches compiled bytecode; realpath cache caches path resolution. Frameworks that call `is_file()` or `file_exists()` in loops hit the realpath cache, not OPcache. 4096k is a sane production value for large applications, and 16384k helps Composer-heavy monolithic deployments.

**How do I know OPcache actually cached my files?**
Run `php -r 'var_dump(opcache_get_status(false)["opcache_statistics"]["num_cached_scripts"]);'` on a request-serving worker (or through a temporary diagnostics endpoint), then compare against your PHP file count. A large gap with `cache_full: true` means the file limit is too low.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP 8.5 Performance Tuning in 2026: OPcache, JIT and php-fpm Pools That Actually Scale",
  "description": "Practical PHP 8.5 tuning guide covering OPcache sizing, real JIT gains, php-fpm pool math, realpath cache and opcache preloading with real config examples.",
  "datePublished": "2026-11-25",
  "dateModified": "2026-11-25",
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
