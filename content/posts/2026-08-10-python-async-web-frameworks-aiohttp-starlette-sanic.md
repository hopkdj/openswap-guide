---
title: "Python Async Web Frameworks in 2026: aiohttp vs Starlette vs Sanic — Which One Should You Use?"
date: "2026-08-10"
tags: ["python", "asyncio", "aiohttp", "starlette", "sanic", "web-frameworks", "backend"]
draft: false
---

## The GIL Is Not Your Bottleneck Anymore

A typical Flask service spends 90% of its request time waiting on a database, a cache, or an upstream API — and every one of those seconds pins a thread that could have served a hundred other requests. Asyncio changed that: with cooperative concurrency, one event loop multiplexes thousands of in-flight requests across a handful of threads. The hard part is choosing the framework. **aiohttp**, **Starlette**, and **Sanic** are the three serious async-native options in Python, and despite overlapping feature sets, they target fundamentally different users.

## TL;DR / Quick Verdict

If you want **battle-tested async with a built-in HTTP client, WebSocket support, and no dependency on external servers**, use **aiohttp** — it is the most mature asyncio framework and the backbone of the async ecosystem. If you are building an **API on top of ASGI** and want the smallest, most composable toolkit (the foundation FastAPI is built on), use **Starlette**. If you want **maximum raw throughput with batteries included** — an opinionated server built into the framework, async ORM integration, and plugin system — use **Sanic**. All three are actively maintained in 2026.

## Quick Comparison Table

| Dimension | aiohttp | Starlette | Sanic |
|---|---|---|---|
| GitHub stars | 16,514 | 12,534 | 18,645 |
| Last pushed | 2026-08-10 | 2026-08-10 | 2026-07-29 |
| License | Apache-2.0 | BSD-3-Clause | MIT |
| Server model | Bring your own (aiohttp ships `run_app`) | ASGI app — needs Uvicorn/Hypercorn | Built-in high-performance server |
| ASGI compatible | No (native asyncio) | Yes | Partial (own protocol, ASGI via adapter) |
| HTTP client included | Yes (`aiohttp.ClientSession`) | No (use httpx/anyio) | No (use httpx) |
| WebSockets | Yes (native) | Yes (via ASGI) | Yes (native) |
| Templating / static files | Views + static | Via plugins (Jinja2, StaticFiles) | Built-in static + templating |
| Plugin ecosystem | Rich | Rich (FastAPI, Litestar on top) | Official plugin registry |
| Learning curve | Steep | Low (if you know ASGI) | Moderate |
| Best for | Async SDKs, scraping, real-time apps | ASGI microservices, building frameworks | High-throughput self-contained servers |

## Decision Matrix: Pick in 10 Seconds

| Use Case | Recommended | Why |
|---|---|---|
| Async SDK / client + server in one library | aiohttp | `ClientSession` + server in a single dependency, zero external moving parts |
| REST API that must run on Uvicorn with the ASGI ecosystem | Starlette | Native ASGI, minimal core, plays with every ASGI middleware |
| WebSocket-heavy real-time application | aiohttp or Sanic | Both ship first-class WebSocket support without third-party glue |
| Maximum requests-per-second on modest hardware | Sanic | Built-in tuned server; benchmarked consistently fastest of the three |
| Building your own framework | Starlette | It *is* the toolkit FastAPI and Litestar are built on — composable by design |
| Long-lived background workers + web API | aiohttp | Mature asyncio patterns; pairs cleanly with aiohttp-based task loops |

## aiohttp — The Async Workhorse

aiohttp (16,514 stars, last push 2026-08-10) is the oldest and most battle-tested async web library in Python, and it is unique among the three: it provides **both an HTTP client and an HTTP server** in one package. The `ClientSession` is the de-facto standard async HTTP client across the Python ecosystem — libraries like Home Assistant's API layer and countless scraper pipelines run on it. The server side is explicit rather than magical:

```python
from aiohttp import web

async def handle(request):
    name = request.match_info.get('name', 'anonymous')
    return web.json_response({'hello': name})

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(f'echo: {msg.data}')
    return ws

app = web.Application()
app.router.add_get('/hello/{name}', handle)
app.router.add_get('/ws', websocket_handler)
web.run_app(app, port=8080)
```

What you get with aiohttp: first-class **WebSockets**, **middleware** (`@middleware` decorators), **streaming responses**, server-side **keep-alive tuning**, and deep asyncio integration that has survived a decade of production abuse. It is the safest choice when correctness and ecosystem maturity outrank syntactic sugar.

The trade-off: aiohttp's API is **verbose and imperative**. You write request handlers, not declarative routes; there is no auto-validation, no dependency injection, and no built-in OpenAPI generation. You will assemble those pieces yourself. For teams that want a framework with batteries, aiohttp feels like working closer to the metal — which is exactly why its raw power is also its biggest learning curve.

## Starlette — The Minimal ASGI Toolkit

Starlette (12,534 stars, last push 2026-08-10) describes itself as "the little ASGI framework that shines," and the description is accurate: it is a small, composable toolkit that implements the **ASGI specification** — the async successor to WSGI — and nothing more. It has no server of its own; you run it under Uvicorn or Hypercorn (see our [ASGI server comparison](../2026-05-07-asgi-servers-hypercorn-daphne-uvicorn-guide/)). Its real claim to fame is being the foundation of **FastAPI** and **Litestar**, which layer validation, dependency injection, and OpenAPI on top of it. If you understand Starlette, you understand the whole modern Python API stack:

```python
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.background import BackgroundTask
import uvicorn

async def homepage(request):
    return JSONResponse({'message': 'Hello'})

async def slow_task():
    await asyncio.sleep(2)  # runs after the response is sent

async def with_background(request):
    return JSONResponse({'ok': True},
        background=BackgroundTask(slow_task))

app = Starlette(routes=[
    Route('/', homepage),
    Route('/bg', with_background),
])
uvicorn.run(app, host='0.0.0.0', port=8000)
```

Starlette's core delivers **routing, middleware, WebSockets, Server-Sent Events, background tasks, streaming responses, and static files** in roughly 5,000 lines of code — small enough that an experienced engineer can read the entire codebase. It integrates with every ASGI middleware (CORS, GZip, TrustedHost, and ecosystem packages like `python-multipart` for forms), and because it is ASGI-native, anything written for ASGI works with it.

The trade-offs: Starlette is a **toolkit, not an application framework**. There is no built-in ORM integration, no validation, no admin, no template opinion. You compose those layers — or pick FastAPI/Litestar when you want them preassembled. Also, because it relies on an external ASGI server, deployment involves two packages and their version compatibility.

## Sanic — The Built-In Speed Demon

Sanic (18,645 stars, last push 2026-07-29) started in 2016 as "Flask with async support" and grew into a full framework with an **integrated high-performance HTTP server** — no Uvicorn needed. It is the most opinionated of the three: decorator-based routes like Flask, a plugin registry, built-in static file serving, and first-class support for async database drivers. Its performance focus shows in the details: sanic's own benchmarks put it consistently at the top of pure-Python frameworks for requests per second, and its server can be tuned with `workers=N` for multi-process deployments:

```python
from sanic import Sanic
from sanic.response import json

app = Sanic("MyApp")

@app.get("/hello/<name>")
async def hello(request, name):
    return json({"hello": name})

@app.websocket("/ws")
async def ws_handler(request, ws):
    while True:
        data = await ws.recv()
        await ws.send(f"echo: {data}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, workers=4)
```

Sanic's strengths: **one command to run** (`sanic app:app` or `app.run()`), an official **plugin registry** (sanic-ext adds OpenAPI, CORS, and validation), **asyncio-native ORM support** (SQLAlchemy async, Tortoise), and the **cleanest developer experience** of the three for teams coming from Flask. The framework also handles graceful shutdown, request timeouts, and signal handling for you.

The trade-offs: Sanic implements its **own protocol layer** rather than pure ASGI, so some ASGI middleware is incompatible without an adapter — the ecosystem is smaller than Starlette's. Its opinionation also means you follow Sanic's way: class-based views, its own `sanic.response` module, and its plugin conventions. And while the built-in server is fast, running under Gunicorn with `sanic.worker.GunicornWorker` requires an extra dependency.

## Common Pitfalls With Async Web Frameworks

**Blocking calls inside the event loop.** Any synchronous `time.sleep()`, `requests.get()`, or CPU-bound loop blocks *every* request on that worker. Use `await asyncio.sleep()`, async clients (`aiohttp.ClientSession`, httpx with `AsyncClient`), and offload CPU work to a thread pool via `loop.run_in_executor()` or `anyio.to_thread`.

**Mixing sync and async database drivers.** SQLAlchemy's sync engine blocks the loop; use the async engine or the driver's async adapter (asyncpg, aiomysql). One blocking query per request defeats the entire concurrency model — see our [Python asyncio library roundup](../2026-07-26-python-asyncio-libraries-aiodns-aiofiles-aiomysql-aiopg-aioredis/) for the right async drivers.

**Choosing the wrong worker model.** `uvicorn.run(app)` defaults to a single process — good for development, weak for production. Run multiple workers (Uvicorn `--workers N`, Sanic `workers=N`) but remember each worker has its own event loop and in-memory state; shared state needs Redis or a database.

**Deadlocks from nested loops.** Calling `loop.run_until_complete()` from inside a coroutine raises `RuntimeError: This event loop is already running`. Never start a new loop inside a handler; await directly or use `asyncio.create_task()` for fire-and-forget work.

**WebSocket backpressure.** Sending faster than the client reads eventually buffers in memory. In aiohttp, check `ws._waiters` behavior or implement your own send queue; in Sanic, respect `ws.recv()` flow and catch `ConnectionClosed`.

**Version drift between ASGI server and framework.** Uvicorn and Starlette/FastAPI evolve quickly; pin compatible versions or CI will surprise you with a `TypeError` from mismatched ASGI lifecycle events. Check our [Python API framework comparison](../2026-07-28-python-api-frameworks-fastapi-flask-django-ninja-litestar-comparison/) before committing a stack.

**Ignoring graceful shutdown.** Async frameworks need explicit shutdown to drain in-flight requests and close client sessions. Register `on_shutdown` / `@app.listener('before_server_stop')` handlers and always `await client_session.close()` — leaked aiohttp sessions are a classic production memory leak.

## FAQ

### Is aiohttp a server or a client library?

Both. aiohttp provides `web.Application` (server) and `ClientSession` (client) in a single package. That dual nature makes it popular for SDKs and tools that must both consume and expose HTTP APIs without adding dependencies.

### What is the difference between Starlette and FastAPI?

FastAPI is built on top of Starlette: Starlette provides routing, middleware, and ASGI support; FastAPI adds Pydantic validation, dependency injection, and OpenAPI generation. If you need those features, use FastAPI directly; if you want a minimal toolkit, use Starlette.

### Which Python async framework is fastest?

In community benchmarks, Sanic typically leads pure-Python async frameworks in requests per second thanks to its tuned built-in server, with aiohttp and Starlette (under Uvicorn) close behind. Real-world throughput is dominated by database and I/O latency, so benchmark before you migrate.

### Do I need Uvicorn with Sanic?

No. Sanic ships its own production HTTP server — `app.run()` or the `sanic` CLI is all you need. Starlette and aiohttp both run under Uvicorn, though aiohttp also ships `web.run_app()` for a self-contained server.

### Can I use these frameworks with Django or Flask code?

Not directly — they are async-native and use different request/response models. You can run Flask in a thread pool inside an async app for gradual migration, but the clean path is rewriting handlers. Sanic's decorator style is the easiest migration for Flask developers.

### Which framework should I pick for WebSockets?

All three support WebSockets natively. aiohttp's implementation is the most battle-tested; Sanic's is the simplest to write; Starlette's is ASGI-standard. For heavy real-time workloads, aiohttp or Sanic are the safer bets.

### How do async frameworks handle background tasks?

Starlette has first-class `BackgroundTask` support attached to responses; aiohttp uses `asyncio.create_task()` or middleware patterns; Sanic provides `app.add_task()`. For durable background work across restarts, prefer a proper task queue — see our [Python async concurrency models guide](../2026-07-27-python-async-concurrency-models-gevent-eventlet-trio-asyncio/) for the full landscape.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python Async Web Frameworks in 2026: aiohttp vs Starlette vs Sanic",
  "description": "Deep comparison of Python's three async-native web frameworks: aiohttp, Starlette, and Sanic, with real code examples, GitHub stats, decision matrices, and production pitfalls.",
  "datePublished": "2026-08-10",
  "dateModified": "2026-08-10",
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
