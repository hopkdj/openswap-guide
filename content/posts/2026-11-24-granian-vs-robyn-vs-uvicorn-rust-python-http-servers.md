---
title: "Granian vs Robyn vs Uvicorn in 2026: Do Rust-Backed Python Servers Actually Win?"
date: "2026-11-24"
tags: ["python", "web-servers", "asgi", "granian", "robyn", "uvicorn", "performance"]
draft: false
cover: "/img/screenshots/robyn-multiprocess-architecture.jpg"
description: "Granian, Robyn and Uvicorn compared in 2026: Rust-backed HTTP runtimes vs pure-Python ASGI, real CLI flags, worker models, and how to benchmark them honestly."
---

Every Python web service eventually hits the same wall: the application code is fine, the database is fine, and the process is still sitting at 100% of one core while requests queue up. The usual fix is more containers — which means more memory, more cold starts, and a bigger bill. The other fix is replacing the thing that accepts and parses the requests in the first place.

That is the promise behind **Granian** (5,798 stars, Rust HTTP server for Python apps) and **Robyn** (7,433 stars, async framework with a Rust runtime). Both move request parsing, connection handling and the event loop hot path into compiled code, leaving your Python handlers untouched. **Uvicorn** (11,141 stars) stays pure Python and remains the default everyone benchmarks against.

This is a working engineer's comparison, not a leaderboard: what each server actually does differently, the real flags, the worker models, and how to measure the difference on your own workload instead of trusting a blog post's bar chart.

## TL;DR — the verdict up front

- **You have a FastAPI/Starlette/Django-ASGI app and want a drop-in speedup:** run **Granian** with `granian --interface asgi app:app`. Same application, same ASGI contract, Rust HTTP/1.1 + HTTP/2 stack, no code changes. This is the lowest-risk upgrade in the whole Python serving space.
- **You are starting a new high-throughput service and control the framework choice:** consider **Robyn**. Its Rust runtime is baked into the framework (routing, JSON serialization, multiprocess orchestration), so you get the compiled path without bolting a server onto someone else's framework — at the cost of Robyn's own API surface.
- **You want boring, battle-tested, documented everywhere, and your bottleneck is your code not your server:** stay on **Uvicorn**. It is pure Python, predictable, and every deployment guide on the internet assumes it.

Rule of thumb: **Granian is an upgrade, Robyn is a rewrite, Uvicorn is the baseline.** Measure before you migrate — on I/O-bound apps the server is often not the bottleneck at all.

## Side-by-side comparison

Live GitHub figures pulled 2026-11-24.

| Dimension | Granian | Robyn | Uvicorn |
|---|---|---|---|
| Stars | 5,798 | 7,433 | 11,141 |
| Last push | 2026-11-20 | 2026-11-23 | 2026-11-24 |
| Core written in | Rust (PyO3) | Rust runtime + Python API | Pure Python |
| Interfaces supported | ASGI/3, RSGI, WSGI | Robyn's own API | ASGI/3 |
| HTTP/2 | Yes (`--http 2`) | Yes | No (HTTP/1.1 only) |
| Event loops | asyncio, uvloop, rloop, winloop | Built-in Rust loop | asyncio, uvloop |
| Worker model | `--workers N`, `--blocking-threads` | `--processes N`, `--workers N` | `--workers N` |
| Drop-in for FastAPI | Yes | No (own routing API) | Yes |
| Static file serving | Via app/middleware | Built-in `app.add_directory` | Via app/middleware |
| WebSocket | Via ASGI | Built-in decorators | Via ASGI |
| Best fit | Existing ASGI apps | Greenfield services | Default / maximum compatibility |

## Decision matrix

| Your situation | Pick | Reason |
|---|---|---|
| FastAPI app, want faster request parsing today | Granian | Pass `app:app`, keep the codebase |
| Need HTTP/2 termination without a reverse proxy | Granian | Native `--http 2` support |
| Legacy Flask/WSGI app | Granian | `--interface wsgi`, no gunicorn needed |
| New service, want routing + server from one stack | Robyn | Rust routing, built-in WebSocket and static files |
| Team unfamiliar with anything but FastAPI | Uvicorn | Zero learning curve, universal docs |
| Multi-tenant SaaS at modest scale | Uvicorn | Simplicity beats 15% throughput gains |
| CPU-heavy handlers | None of them | Move work to a worker queue first |
| Running behind nginx/ALB doing TLS | Any | Server choice matters less than connection reuse |

## Granian: the least invasive upgrade

Granian's design decision is the one that makes it easy to adopt: it is a **server only**. You keep FastAPI, Starlette, Django, Litestar or plain ASGI, and Granian replaces Uvicorn underneath. The README documents the three interfaces directly:

```bash
pip install granian

# ASGI (FastAPI, Starlette, Django, Litestar...)
granian --interface asgi main:app

# RSGI (Granian's own fast in-process spec, supported by Emmett)
granian --interface rsgi main:app

# WSGI (Flask, Django classic)
granian --interface wsgi main:app
```

The flags that actually matter in production come straight from `granian --help`:

```bash
granian --interface asgi main:app \
  --host 0.0.0.0 --port 8000 \
  --workers 4 \
  --http 2 \
  --loop uvloop \
  --blocking-threads 8 \
  --http1-keep-alive \
  --workers-max-rss 2048 \
  --workers-lifetime 3600
```

Three of those deserve explanation, because they are the reason people get burned:

- **`--workers` is processes, not threads.** With `--workers 4` you get four Python interpreters, each with its own GIL. Size it to cores, not to "how many requests per second I want."
- **`--blocking-threads` bounds the thread pool used for sync handlers.** Without it, a single slow `def` endpoint (as opposed to `async def`) can starve the loop. Set it deliberately and monitor it.
- **`--workers-max-rss` and `--workers-lifetime` are self-healing controls.** They recycle workers on memory growth or age, which is exactly what you want for long-lived services with creeping leaks.

Install extras for the loop and HTTP parser:

```bash
pip install granian[uvloop]
```

Deployment footprint stays boring — a systemd unit calling the binary:

```ini
# /etc/systemd/system/api.service
[Unit]
Description=Granian ASGI service
After=network.target

[Service]
WorkingDirectory=/srv/api
Environment="PATH=/srv/api/.venv/bin"
ExecStart=/srv/api/.venv/bin/granian --interface asgi main:app \
  --host 127.0.0.1 --port 8000 --workers 4 --http 2 --loop uvloop
Restart=always
RestartSec=2
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

Where Granian does *not* help: if your endpoint awaits a database round trip for 40 ms, moving the parser into Rust saves microseconds and changes nothing. This is a throughput and tail-latency tool for connection-heavy workloads, not a fix for slow SQL.

## Robyn: framework and server in one binary

Robyn takes the opposite approach: the Rust part is not just the socket layer, it is the router, the multiprocess orchestrator and the Python bindings, all shipped as a compiled wheel. You write against Robyn's own decorator API — not FastAPI's — which is the real cost of entry.

The starter app from the official README:

```python
from robyn import Robyn

app = Robyn(__file__)

@app.get("/")
async def h(request):
    return "Hello, world!"

app.start(port=8080)
```

Run it directly, with the CLI flags the README documents:

```bash
python3 app.py --processes 4 --workers 2 --log-level info
# development mode with file watching and auto-reload:
python3 app.py --dev
```

Extras install pulls in the optional integrations:

```bash
pip install "robyn[all]"
```

Robyn's architecture is worth understanding before you adopt it, because it explains both the upside and the constraint: Python handler processes run alongside a Rust main process that owns the sockets, distributes requests, and handles JSON serialization boundary crossings. That is why a single `app.start()` can spawn multiple processes without a gunicorn-style master, and why Robyn can serve static directories and WebSockets without extra dependencies.

![Robyn multiprocess architecture: Rust main process distributing work across Python workers](/img/screenshots/robyn-multiprocess-architecture.jpg "Robyn's multiprocess model — the Rust process owns the socket and routes requests to Python workers")

The migrations that hurt are the invisible ones: dependency injection patterned on FastAPI's `Depends`, Pydantic-based request models used as documentation, OpenAPI schema generation, and every middleware written against Starlette. Robyn has equivalents for some of this, but the port is a project, not an afternoon. Choose Robyn for new services where you can commit to its idioms.

## Uvicorn: the baseline that keeps winning on boring

Uvicorn is pure Python and that is not an insult — it is the reason it runs everywhere, debugs with normal Python tooling, and has a documented answer for every deployment question. It also supports the two accelerators that matter, and most teams do not enable them:

```bash
pip install "uvicorn[standard]"

uvicorn main:app \
  --host 0.0.0.0 --port 8000 \
  --workers 4 \
  --loop uvloop \
  --http httptools \
  --no-server-header
```

`uvicorn[standard]` pulls in `uvloop` (libuv-based event loop) and `httptools` (Node's HTTP parser). Those two alone close a meaningful part of the gap with compiled servers for many workloads, without changing a line of application code. If you are on plain `uvicorn` with defaults, you are benchmarking the slowest possible configuration of the most popular server and blaming Python for it.

Uvicorn also has the least surprising failure modes: a stack trace points at Python, `--reload` works identically in dev and CI, and every container base image has a recipe for it. For services under a few hundred requests per second, that operational simplicity is worth more than raw throughput.

If you want the wider context on ASGI servers and how they differ from pure framework choices, our [ASGI server comparison covering Hypercorn, Daphne and Uvicorn](../2026-05-07-asgi-servers-hypercorn-daphne-uvicorn-guide/) goes deeper on protocol coverage and shutdown semantics, and the [async framework comparison of aiohttp, Starlette and Sanic](../2026-08-10-python-async-web-frameworks-aiohttp-starlette-sanic/) explains where framework design, not the server, sets your ceiling.

## Benchmarking honestly — a procedure, not a number

Any article that hands you a requests-per-second figure for "Python servers" is telling you about its own hardware, its own endpoint and its own payload size. The only number that matters is yours. Here is the procedure that produces a defensible one.

**Step 1: freeze a realistic endpoint.** Not `/`, not "hello world". Use an endpoint that does one database query and returns 5–10 KB of JSON, because that is what production traffic looks like.

```python
# bench_app.py — FastAPI, identical for Granian and Uvicorn
from fastapi import FastAPI
app = FastAPI()

PAYLOAD = [{"id": i, "name": f"item-{i}", "price": i * 1.25} for i in range(50)]

@app.get("/api/items")
async def items():
    return {"items": PAYLOAD}
```

**Step 2: run each server with the same worker count and the same loop.**

```bash
# Uvicorn, accelerated
uvicorn bench_app:app --workers 4 --loop uvloop --http httptools --port 8001

# Granian, ASGI interface
granian --interface asgi bench_app:app --workers 4 --loop uvloop --port 8002
```

**Step 3: measure with a fixed connection count and record p99, not just mean.**

```bash
# install a load generator once
# apt install wrk   OR   go install github.com/hatoo/oha@latest

wrk -t4 -c200 -d60s --latency http://127.0.0.1:8001/api/items
wrk -t4 -c200 -d60s --latency http://127.0.0.1:8002/api/items
```

**Step 4: watch the thing you forgot — memory and file descriptors.**

```bash
pidstat -r -p $(pgrep -f "granian|uvicorn" | tr '\n' ',') 2 5
ss -s
```

Run each configuration three times, discard the first (warm-up), and compare p99 latency at a fixed request rate rather than maximum throughput. A server that peaks higher but has a 300 ms p99 under load is worse for users than one that peaks lower and stays flat.

## Pitfalls that cost real incidents

**1. Mixing worker flags with container CPU limits.** `--workers 4` inside a container limited to 1 CPU produces four processes fighting over one core and a scheduler that thrashes. Match workers to the CPU limit, not the host.

**2. Forgetting `--blocking-threads` on sync handlers.** With Granian, sync `def` endpoints run in a bounded pool. Too small and requests queue behind each other; too large and you re-create the memory problems the Rust runtime was supposed to avoid.

**3. Assuming HTTP/2 helps through a proxy.** If nginx or an ALB terminates TLS and speaks HTTP/1.1 to your app, `--http 2` does nothing for clients. Enable HTTP/2 at the edge, and keep the backend on HTTP/1.1 with keep-alive.

**4. Migrating a FastAPI app to Robyn "for speed".** Request models, dependency injection, OpenAPI output and middleware all change. Budget the rewrite honestly, or take Granian's drop-in path instead.

**5. Benchmarking with `--reload` enabled.** Reload mode wraps the app in a watcher process and single-worker configuration. Every "slow" server result produced with reload on is invalid.

**6. Ignoring `LimitNOFILE`.** All three servers will hit the default file descriptor limit under high concurrency, and the symptom is not a clean error — it is sporadic connection resets. Set it in the unit file or the container's ulimits.

**7. Pinning to `latest` in production.** Robyn ships compiled wheels per Python version and platform; Granian's Rust extensions are the same story. Pin exact versions in `requirements.txt`/`uv.lock` and rebuild images on a schedule you control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Granian vs Robyn vs Uvicorn in 2026: Do Rust-Backed Python Servers Actually Win?",
  "description": "Granian, Robyn and Uvicorn compared in 2026: Rust-backed HTTP runtimes vs pure-Python ASGI, real CLI flags, worker models, and how to benchmark them honestly.",
  "datePublished": "2026-11-24",
  "dateModified": "2026-11-24",
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

**Is Granian faster than Uvicorn in practice?**
It can be, especially for connection-heavy workloads and HTTP/2, because request parsing and connection handling happen in Rust instead of Python. Whether it is faster *for you* depends on where your time actually goes. If handlers await a database for tens of milliseconds, the server accounts for a small fraction of total latency and the difference will be within noise. Benchmark your own endpoint with the procedure above before migrating.

**Can I use Granian with FastAPI without changing my code?**
Yes. Granian implements the ASGI interface, so `granian --interface asgi main:app` serves the same FastAPI/Starlette app object that `uvicorn main:app` serves. Watch for server-specific assumptions such as `uvicorn` lifespan handling in tests, and re-check your WebSocket middleware.

**Does Robyn work with FastAPI-style dependency injection and Pydantic models?**
Not directly. Robyn has its own request/response API and its own dependency handling, and it does not expose FastAPI's `Depends` or automatic OpenAPI generation. Treat a Robyn migration as a port: handlers, validation and middleware all need review.

**Should I run these behind nginx or Traefik?**
Usually yes for TLS termination, connection buffering and static assets. Two exceptions: Granian's native HTTP/2 support is redundant if the edge terminates HTTP/2 already, and Robyn's built-in static file serving is fine for small deployments. Keep the backend on keep-alive HTTP/1.1 in most setups.

**How many workers should I run?**
Start with one worker per available CPU, then measure. I/O-bound services often peak with fewer workers than cores; CPU-bound Python services rarely benefit from more than core count because of the GIL. Never exceed your container's CPU limit, and verify with `pidstat` that workers are not competing.

**Do any of these support WSGI apps like Flask?**
Granian does: `granian --interface wsgi main:app`. Uvicorn does not — it is ASGI-only, so Flask needs Gunicorn or Granian. Robyn is its own framework and does not host WSGI apps.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
