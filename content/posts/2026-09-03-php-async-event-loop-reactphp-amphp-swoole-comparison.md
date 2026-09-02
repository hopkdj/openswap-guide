---
title: "ReactPHP vs Amp vs Swoole in 2026: Which Async PHP Framework Should You Use?"
date: "2026-09-03"
tags: ["php", "async", "event-loop", "concurrency", "web-frameworks"]
draft: false
cover: "/img/screenshots/reactphp-async.jpg"
---

Plain PHP is synchronous: every database query and HTTP call blocks the process, which is why a classic PHP-FPM worker sits idle thousands of times per second waiting on I/O. In 2026 that model is optional. **Swoole (18,916 stars)** gives PHP real coroutines through a C extension, **Amp (4,433 stars)** brings fibers and a modern async ecosystem in pure PHP, and **ReactPHP (9,091 stars)** remains the battle-tested event-loop pioneer. They solve the same problem — keeping PHP busy during I/O waits — in three fundamentally different ways, and picking the wrong one for your team's constraints (shared hosting vs dedicated servers, extensions allowed or not, PHP version) can stall your project for months.

## TL;DR: Quick Verdict

If you control the server and want **maximum throughput with coroutine-style code** — an HTTP/WebSocket server or a Laravel app under Laravel Octane — choose **Swoole** (or the maintained Open Swoole fork). If you need **async HTTP clients, WebSocket and concurrency inside an ordinary Composer project** without installing any extension, choose **Amp v3** — its fiber-based model reads like synchronous code. Choose **ReactPHP** when you need the largest set of battle-tested event-loop components (HTTP, sockets, DNS, child processes) and accept callback-style async code. Do not start new work with ReactPHP-style promise chains if Amp v3 is an option — fibers are strictly easier to read and debug.

## Quick Comparison Table

GitHub data fetched 2026-09-03. ReactPHP and Amp are MIT; Swoole is Apache-2.0.

| Dimension | ReactPHP | Amp v3 | Swoole |
|---|---|---|---|
| GitHub stars | 9,091 | 4,433 | 18,916 |
| Last commit | 2024-11-25 | 2026-07-26 | 2026-09-02 |
| Async model | Event loop + callbacks/promises | Fibers + Revolt event loop | Coroutines (C extension) |
| PHP requirement | PHP 7.1+ (pure PHP) | PHP 8.1+ (pure PHP, Fibers) | PHP 7.2-8.x, requires `pecl install swoole` |
| Install | Composer | Composer | PECL extension + Composer |
| HTTP server | `react/http` | `amphp/http-server` | Built-in HTTP/WebSocket server |
| Async DB clients | Community adapters (mysql via clue) | amphp/mysql, amphp/postgres, amphp/redis | Built-in coroutine clients + PDO/Redis auto-hooks |
| WebSocket | `ratchet` (component) | amphp/websocket | Built-in WebSocket server |
| Ecosystem size | Large (30+ components, mature) | Growing (http, socket, websocket, process, cache) | Hyperf, Swoft, Laravel Octane support |
| Maintenance | Stable, slow-moving | Active | Very active |
| Learning curve | Steep (callbacks/promises) | Gentle (code reads sync) | Moderate (extension + coroutine rules) |
| Best for | Legacy async stacks, component reuse | New pure-PHP async projects | High-throughput servers, coroutine apps |

## Scenario Decision Matrix

| Your situation | Recommended stack | Why |
|---|---|---|
| Expose PHP as a high-throughput HTTP/WebSocket server | Swoole | Built-in server + coroutine clients deliver order-of-magnitude gains over FPM with one extension |
| Laravel app needs Octane or coroutine runtime | Swoole | Laravel Octane officially supports Swoole (and RoadRunner/FrankenPHP); see our [PHP application servers guide](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/) |
| Composer project needs an async HTTP client or WebSocket | Amp v3 | `Amp\async()` + fibers give you async without restructuring your app around a loop |
| Shared hosting / no extension allowed | Amp v3 (or ReactPHP) | Both are pure PHP; Amp's fiber model is far easier than ReactPHP callbacks |
| Maintain a legacy ReactPHP daemon | ReactPHP (stay) | Stable components with years of production history; migrate only if the codebase is small |
| You need an event loop embedded in a library | ReactPHP | `react/event-loop` is the de-facto standard loop other libraries plug into |

## Swoole — Coroutines in C

Swoole is not a library you Composer-install and forget: it is a PHP extension that rewrites how the interpreter handles concurrency. It provides coroutines, an asynchronous HTTP/WebSocket/TCP server, task workers, timers and coroutine-aware clients for MySQL, Redis and PostgreSQL — plus a "hooks" system that can transparently turn many blocking functions (PDO, `curl`, `file_get_contents`, `sleep`) into coroutine-safe calls.

```bash
pecl install swoole
# enable extension=swoole.so in php.ini, then restart php
```

```php
<?php
use Swoole\Http\Server;
use Swoole\Http\Request;
use Swoole\Http\Response;

$server = new Server('127.0.0.1', 9501);

$server->on('Request', function (Request $req, Response $res) {
    $res->end("<h1>Hello Swoole</h1>");
});

$server->start();
```

The coroutine model is the key difference from ReactPHP: your code stays *synchronous-looking* — `$result = $db->query(...)` — while the runtime suspends and resumes the coroutine during the I/O wait. That is why Swoole is the foundation of Hyperf and Swoft, and why Laravel Octane lists it as a first-class runtime. The costs are operational: you must compile the extension against your exact PHP version, long-running workers mean memory leaks from static state become your problem, and the project's 2021 governance split produced Open Swoole, a community fork with identical APIs — teams should evaluate both before standardizing.

## Amp v3 — Fibers Without Extensions

Amp v3, released for PHP 8.1+, builds on **Fibers** — a language-level primitive that arrived in PHP 8.1 — plus the Revolt event loop. The result is real async concurrency in pure PHP with no PECL extension, and code that reads like the synchronous PHP you already know.

```bash
composer require amphp/amp
```

```php
<?php
require __DIR__ . '/vendor/autoload.php';

use function Amp\async;
use function Amp\delay;

$future = async(function (): string {
    delay(1); // non-blocking sleep
    return 'finished after 1s';
});

echo 'main continues immediately', PHP_EOL;
echo $future->await(), PHP_EOL;
```

`Amp\async()` starts a fiber that runs concurrently with the caller; `await()` suspends until its result is ready. The official ecosystem — `amphp/http-server`, `amphp/http-client`, `amphp/websocket`, `amphp/socket`, `amphp/process`, plus async clients for MySQL, PostgreSQL and Redis — covers most production needs. Because everything is Composer-only, Amp works on shared hosting and in CI without special server setup. The main gap versus Swoole is raw performance: fibers multiplex on one process, so CPU-bound work still serializes, and very high-connection-count servers will eventually want Swoole's C-level event handling.

## ReactPHP — The Event-Loop Pioneer

ReactPHP has powered non-blocking PHP since 2012. Its core, `react/event-loop`, is the substrate that dozens of libraries (including Amp v2, historically) plugged into, and the component family — `react/http`, `react/socket`, `react/dns`, `react/child-process`, `react/stream` — is the most battle-tested async toolkit in the language.

```bash
composer require react/http
```

```php
<?php
require __DIR__ . '/vendor/autoload.php';

use Psr\Http\Message\ServerRequestInterface;
use React\Http\Message\Response;

$server = React\Http\HttpServer::create(
    function (ServerRequestInterface $request) {
        return Response::plaintext("Hello World!\n");
    }
);

$socket = new React\Socket\SocketServer('127.0.0.1:8080');
$server->listen($socket);
```

ReactPHP's model is explicit: you register callbacks and promises on a running event loop, and the loop dispatches events as I/O completes. That model is powerful — it is why ReactPHP components remain stable and dependable years later — but callback nesting and promise chains are harder to read, test and debug than fiber-based code. ReactPHP's last commit activity is sparse because the project is in maintenance mode: it still works excellently for existing daemons and long-running socket services, yet for new projects Amp v3 offers the same guarantees with a modern programming model. If you inherit a ReactPHP codebase, keep it running — just measure carefully before promising feature work on top of promise spaghetti.

## Common Pitfalls and Migration Traps

**Never block the loop.** In ReactPHP and Amp, any synchronous sleep, `file_get_contents` or blocking PDO query stalls *every* concurrent task in that process. Use the async components (`react/http`, `amphp/http-client`) or coroutine hooks (Swoole) for I/O, and keep CPU-heavy work in worker processes.

**Global state leaks in long-running processes.** Traditional PHP resets everything per request; async servers reuse the process, so static properties, singletons and unclosed resources accumulate across requests. Audit your application for static state before moving it under Octane, Swoole or any long-running model — this is the #1 cause of "works on FPM, crashes after an hour" reports.

**Swoole hooks are a sharp knife.** `SWOOLE_HOOK_ALL` converts blocking functions into coroutines — convenient, but calling hookable functions *outside* a coroutine context throws, and mixing hooked PDO with transaction state across coroutine boundaries corrupts sessions. Enable hooks per-case and test under concurrency.

**The Swoole/Open Swoole fork matters.** After the 2021 maintainership dispute, both extensions evolve separately. Package names, extensions and API compat differ slightly; pick one fork and pin the extension version in your deployment image. Laravel Octane supports both.

**ReactPHP to Amp migration is not automatic.** Promises, loops and streams differ; porting is a rewrite of the async glue, not a find-and-replace. Do it only when the codebase is small or the feature backlog justifies it — otherwise, leave stable ReactPHP daemons alone.

For the deployment layer around these runtimes — RoadRunner, FrankenPHP and Swoole compared as full application servers — read our [PHP application servers guide](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/). If you are building async HTTP clients or testing these stacks, our [PHP HTTP client libraries: Guzzle vs Saloon vs HTTPful](../2026-07-13-php-http-clients-guzzle-saloon-httpful/) and [PHP testing frameworks comparison](../2026-07-23-php-testing-frameworks-phpunit-pest-codeception-behat-phpspec/) cover the neighboring layers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ReactPHP vs Amp vs Swoole in 2026: Which Async PHP Framework Should You Use?",
  "description": "Compare ReactPHP, Amp v3 and Swoole in 2026: event loops vs fibers vs coroutines, PHP version requirements, HTTP server components, ecosystem maturity and migration pitfalls. Includes code examples and a decision matrix.",
  "datePublished": "2026-09-03",
  "dateModified": "2026-09-03",
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

**What is the difference between ReactPHP, Amp and Swoole?**
Their concurrency models. ReactPHP is an event loop with callbacks and promises (pure PHP). Amp v3 uses PHP 8.1 fibers on the Revolt loop, so async code reads like synchronous code (pure PHP). Swoole is a C extension providing true coroutines plus a built-in HTTP/WebSocket server and coroutine-aware database clients.

**Is Swoole production-ready?**
Yes. Swoole and Open Swoole power high-traffic services at scale, and Laravel Octane officially supports Swoole as a runtime. The requirements are a dedicated server, the extension compiled for your PHP version, and discipline about long-running-process memory management.

**Does Amp require a PHP extension?**
No. Amp v3 needs PHP 8.1+ (for Fibers) and installs entirely through Composer, making it suitable for shared hosting, containers and CI where PECL extensions are unavailable.

**Can I use normal PDO and Redis calls in async PHP?**
With Swoole, yes — its hooks transparently convert many blocking calls (including PDO and Redis) into coroutine operations. With ReactPHP and Amp, use their async clients instead (amphp/mysql, amphp/redis, react's socket-based components); a blocking PDO call inside either loop stalls all concurrent tasks.

**What is Open Swoole and how is it different from Swoole?**
Open Swoole is the community fork created after Swoole's 2021 governance dispute. Both provide the same coroutine APIs but release independently with slight differences; pick one and pin the extension version in your deployment.

**Which should I use for an existing Laravel or Symfony application?**
Keep the framework on its classic runtime unless you commit to a long-running model. For Laravel, Octane with Swoole (or RoadRunner/FrankenPHP) is the documented high-throughput path; Symfony has no equivalent first-party runtime, so weigh the operational cost before going async. For new pure-PHP async components, choose Amp v3.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
