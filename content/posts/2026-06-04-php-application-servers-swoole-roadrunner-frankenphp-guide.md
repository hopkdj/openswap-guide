---
title: "Self-Hosted PHP Application Servers: Swoole vs RoadRunner vs FrankenPHP"
date: "2026-06-04"
tags: ["php", "web-server", "application-server", "self-hosted", "performance", "deployment"]
draft: false
---

PHP has powered the web for decades, but the traditional PHP-FPM + Apache/Nginx model has a fundamental limitation: every request starts a fresh PHP process. Modern PHP application servers solve this by keeping PHP running persistently in memory, dramatically improving throughput, reducing latency, and enabling long-lived connections like WebSockets. This article compares three leading self-hosted PHP application servers: Swoole, RoadRunner, and FrankenPHP.

## Why Move Beyond PHP-FPM?

Traditional PHP-FPM works by spawning worker processes that handle one request at a time and then terminate. While this model is battle-tested, it has several drawbacks for modern applications:

**Cold start overhead**: Every request pays the cost of bootstrapping the framework, loading configuration, and warming up caches. For complex frameworks like Laravel or Symfony, this can add 20-50ms per request before any business logic runs.

**No persistent state**: You cannot maintain in-memory caches, connection pools, or WebSocket connections across requests without an external service like Redis.

**Resource inefficiency**: PHP-FPM workers sit idle between requests, consuming memory without doing work. A typical production setup might have 20-50 workers each using 50-100MB of RAM.

PHP application servers address all three by keeping the PHP runtime alive between requests. The performance difference is substantial: benchmarks show Swoole handling 5-10x more requests per second than PHP-FPM with the same hardware, while reducing P99 latency by 60-80%.

For more on traditional PHP deployment, see our [self-hosted web server comparison](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/). If you are exploring containerized PHP deployment, check our [container build tools guide](../2026-06-02-container-image-builders-kaniko-buildah-buildkit/).

## Tool Comparison

| Feature | Swoole | RoadRunner | FrankenPHP |
|---------|--------|------------|------------|
| **Language** | C++ (PHP extension) | Go | Go (Caddy-based) |
| **GitHub Stars** | 18,878 | 8,467 | 11,123 |
| **Architecture** | Event-driven coroutine engine | Process manager + workers | Embedded PHP in Go worker |
| **PHP Support** | 7.4 - 8.3 | 7.4 - 8.4 | 8.1 - 8.4 |
| **Concurrency Model** | Coroutines (cooperative) | Worker pool (prefork) | Worker threads |
| **WebSocket Support** | Native | Via Centrifugo plugin | Native (Mercure) |
| **HTTP Server** | Built-in Swoole\Http\Server | Goridge protocol | Caddy web server |
| **Memory Resident** | Yes (long-lived) | Yes (worker pool) | Yes (worker mode) |
| **Framework Integration** | Laravel Octane, Hyperf | Laravel Octane, Symfony, Spiral | Laravel Octane, Symfony Runtime |
| **Hot Reload** | Manual restart | Automatic file watch | Automatic via Caddy |
| **Docker Support** | Official image | Official image | Official image |
| **TLS Termination** | Requires reverse proxy | Requires reverse proxy | Built-in (Caddy auto-TLS) |

### Swoole

Swoole is a PHP extension written in C++ that provides an event-driven, asynchronous, coroutine-based concurrency model. It replaces the traditional PHP execution model entirely, turning PHP into a long-running server process.

The core of Swoole is its event loop, which handles I/O operations asynchronously using epoll (Linux) or kqueue (macOS). Coroutines allow you to write sequential-looking code that suspends and resumes automatically when waiting for I/O, similar to async/await in JavaScript or Python.

```yaml
# docker-compose.yml for Swoole with Laravel Octane
version: '3.8'
services:
  app:
    image: phpswoole/swoole:5.1-php8.3
    working_dir: /var/www
    volumes:
      - ./:/var/www
    ports:
      - "8000:8000"
    command: php artisan octane:start --server=swoole --host=0.0.0.0 --port=8000
    environment:
      - APP_ENV=production
      - APP_DEBUG=false

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

Swoole excels at:
- **High-throughput APIs**: Swoole's coroutine model handles thousands of concurrent connections with minimal memory overhead. Each coroutine uses ~8KB of memory, compared to ~120KB for a PHP-FPM worker.
- **Real-time applications**: Native WebSocket server support makes Swoole ideal for chat applications, live dashboards, and collaborative tools.
- **Microservices**: Swoole's built-in TCP/UDP server enables fast inter-service communication without HTTP overhead.

The main tradeoff is that Swoole requires careful coding — blocking I/O calls (like `file_get_contents()` on a network URL) will block the entire event loop. You must use Swoole's coroutine-aware replacements (`Co\Http\Client`, `Co\MySQL`, etc.).

### RoadRunner

RoadRunner takes a different approach: it is a Go application server that manages a pool of PHP worker processes. Workers communicate with the Go server via the Goridge binary protocol, which is much faster than FastCGI.

RoadRunner does not modify PHP's execution model. Workers are standard PHP processes that handle one request at a time, but they persist across requests, eliminating cold-start overhead. The Go server handles HTTP, gRPC, WebSockets, job queues, and other long-lived connections, delegating PHP logic only when needed.

```yaml
# docker-compose.yml for RoadRunner with Laravel
version: '3.8'
services:
  app:
    image: ghcr.io/roadrunner-server/roadrunner:2024
    working_dir: /var/www
    volumes:
      - ./:/var/www
      - ./rr.yaml:/var/www/.rr.yaml
    ports:
      - "8080:8080"
    command: serve -c .rr.yaml

  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
```

RoadRunner's plugin architecture is a key differentiator. Beyond HTTP serving, it includes built-in support for:
- **gRPC**: Serve gRPC endpoints alongside HTTP
- **Jobs/Queues**: Replaces Laravel Horizon with a Go-native job consumer
- **KV Storage**: In-memory key-value store with TTL
- **Temporal**: Workflow orchestration engine integration
- **Metrics**: Prometheus metrics out of the box

RoadRunner is the most conservative choice — it works with unmodified PHP code (blocking I/O is fine since each worker is isolated), and the Go server provides excellent performance for static file serving, TLS termination, and protocol handling.

### FrankenPHP

FrankenPHP is the newest contender, built by Kevin Dunglas (creator of API Platform). It embeds PHP directly into a Go worker thread using Caddy as the web server. Each PHP request runs in a separate goroutine, with the PHP interpreter compiled as a shared library loaded into the Go process.

FrankenPHP's biggest advantage is that it bundles everything — HTTP server, TLS (automatic Let's Encrypt via Caddy), HTTP/2 and HTTP/3 support, and PHP all in a single binary. No separate Nginx or Caddy reverse proxy is needed.

```yaml
# docker-compose.yml for FrankenPHP with Symfony
version: '3.8'
services:
  app:
    image: dunglas/frankenphp:latest-php8.3
    working_dir: /app
    volumes:
      - ./:/app
      - caddy_data:/data
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3
    environment:
      - SERVER_NAME=:80
      - FRANKENPHP_CONFIG="worker ./public/index.php"

  database:
    image: postgres:16-alpine
    environment:
      - POSTGRES_PASSWORD=secret
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  caddy_data:
  pg_data:
```

FrankenPHP's "worker mode" is where it shines for production. Instead of starting a fresh PHP process per request, it boots your application once and then handles requests in a loop. This is similar to RoadRunner's worker pool but with less overhead since there's no process boundary between Go and PHP.

FrankenPHP supports HTTP/3 (QUIC) out of the box, making it the only PHP server that can serve content over the next-generation protocol without additional infrastructure.

## Why Self-Host Your PHP Application Server?

Running your own PHP application server gives you several advantages over managed PHP hosting or traditional PHP-FPM setups:

**Cost efficiency**: A single FrankenPHP instance on a $20/month VPS can handle the same traffic as 3-5 PHP-FPM servers. The persistent memory model means you can serve more requests with fewer resources, directly reducing your cloud bill.

**Architectural simplicity**: With FrankenPHP, you eliminate the Nginx/Apache reverse proxy layer entirely. One binary handles TLS, HTTP/2, HTTP/3, static files, and PHP. Fewer moving parts means fewer things to debug at 3 AM.

**WebSocket without extra infrastructure**: Swoole and FrankenPHP can serve WebSocket connections directly alongside HTTP, eliminating the need for separate services like Pusher or Soketi. Your real-time features run on the same server, simplifying deployment and reducing costs.

**Connection pooling**: RoadRunner and Swoole can maintain persistent database connections, Redis pools, and HTTP client pools across requests. This eliminates the connection setup overhead that PHP-FPM pays on every request and dramatically improves response times for database-heavy applications.

For production deployment strategies, see our [self-hosted container orchestration guide](../2026-04-28-buildpacks-vs-tilt-vs-skaffold-self-hosted-container-build-guide-2026/). If you are running multiple PHP applications, our [reverse proxy comparison](../self-hosted-cdn-edge-caching-varnish-traffic-server-squid-nginx-guide/) covers caching and load balancing strategies.

## Performance Benchmarks

While exact numbers depend on your application, here are representative benchmarks from the Laravel Octane documentation (simple "Hello World" route, 16-core server, 100 concurrent connections):

| Server | Requests/sec | P50 Latency | P99 Latency | Memory/Worker |
|--------|-------------|-------------|-------------|---------------|
| PHP-FPM (static) | 4,200 | 24ms | 85ms | 85MB |
| Swoole | 38,500 | 2.6ms | 8ms | 35MB |
| RoadRunner | 28,100 | 3.5ms | 12ms | 55MB |
| FrankenPHP (worker) | 32,700 | 3.0ms | 9ms | 45MB |

All three application servers deliver dramatic improvements over PHP-FPM. The specific winner depends on your use case: Swoole leads in raw throughput, FrankenPHP offers the simplest deployment, and RoadRunner provides the most extensive plugin ecosystem.

## Choosing the Right PHP Application Server

**Choose Swoole if**: You need maximum performance and are willing to adapt your code to an async/coroutine model. Swoole is ideal for microservices, APIs handling thousands of concurrent connections, and real-time WebSocket applications. The Hyperf framework built on Swoole delivers near-Go performance for PHP.

**Choose RoadRunner if**: You have existing PHP code with blocking I/O that you cannot refactor. RoadRunner's worker pool model preserves PHP's traditional execution model while eliminating cold starts. The plugin ecosystem (gRPC, job queues, Temporal, KV store) makes it a full-featured application platform.

**Choose FrankenPHP if**: You want the simplest deployment story. One binary includes everything — no separate web server, no TLS certificate management, no HTTP/3 reverse proxy. FrankenPHP is excellent for greenfield projects, API Platform applications, and teams that value operational simplicity.

## FAQ

### Do I need to change my PHP code to use these servers?

It depends. RoadRunner and FrankenPHP (worker mode) run standard PHP code without modification — your Laravel or Symfony application works as-is. Swoole requires you to use coroutine-aware I/O functions (Swoole's HTTP client instead of Guzzle, Swoole's MySQL instead of PDO) to avoid blocking the event loop. If you use Laravel Octane, much of this is abstracted away.

### What about session handling and file uploads?

All three servers handle sessions and file uploads correctly. Swoole and FrankenPHP have built-in support for `$_SESSION` and `$_FILES`. With RoadRunner, file uploads are handled by the Go server and passed to PHP workers via the Goridge protocol. For large file uploads (100MB+), FrankenPHP and RoadRunner handle streaming uploads efficiently without buffering the entire file in PHP memory.

### Are these production-ready?

Yes. Swoole has been used in production since 2017 by companies like Tencent and Baidu handling billions of requests daily. RoadRunner powers Spiral Framework applications in production at companies like Rozetka (one of Eastern Europe's largest e-commerce platforms). FrankenPHP is newer (2023) but built on Caddy, which is widely deployed, and is used in production at Les-Tilleuls.coop for API Platform deployments.

### How do I handle deployments with zero downtime?

All three support graceful reloads. Swoole's `server->reload()` restarts workers without dropping connections. RoadRunner's `rr reset` reloads worker pools with the new code. FrankenPHP leverages Caddy's graceful reload, which spawns a new process and drains connections from the old one — the standard for zero-downtime deployments.

### Can I run multiple PHP applications on one server?

Yes, but the approach differs. With Swoole, you typically run one Swoole server per application (on different ports) with Nginx/Caddy as a reverse proxy. RoadRunner supports multiple app servers from a single RoadRunner instance. FrankenPHP can serve multiple PHP applications from different directories using Caddy's virtual host routing — define separate `php_server` blocks for each application in the Caddyfile.

### Do they work with WordPress or Drupal?

RoadRunner and FrankenPHP can serve WordPress and Drupal in worker mode, reducing page load times by 40-60% compared to PHP-FPM. However, some plugins that rely on per-request state may need adjustments. Swoole is not recommended for WordPress due to the extensive use of blocking I/O throughout the WordPress codebase.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform, where you can bet on anything from election outcomes to tech regulation timelines. Unlike gambling, this is a genuine information market: the more you know, the better your odds. I have profited by predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PHP Application Servers: Swoole vs RoadRunner vs FrankenPHP",
  "description": "Comprehensive comparison of Swoole, RoadRunner, and FrankenPHP — three self-hosted PHP application servers that dramatically improve performance over PHP-FPM with persistent memory models, coroutine concurrency, and built-in WebSocket support. Includes Docker Compose configs, benchmarks, and deployment guidance.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
