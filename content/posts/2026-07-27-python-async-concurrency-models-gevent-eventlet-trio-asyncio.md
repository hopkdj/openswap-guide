---
title: "Python Async Concurrency Models Compared: gevent vs eventlet vs trio vs asyncio"
date: "2026-07-27"
tags: ["python", "async", "concurrency", "performance", "networking"]
draft: false
---

Python's concurrency story has evolved dramatically over the past decade. From the early days of threads and callbacks, through the greenlet revolution, to the standardized async/await syntax — Python developers now have multiple mature options for writing concurrent code. But which approach fits your use case?

This guide compares four major Python concurrency models — **gevent**, **eventlet**, **trio**, and the standard library's **asyncio** — across ecosystem compatibility, ergonomics, scalability, and real-world deployment patterns.

## Understanding the Concurrency Landscape

Python has a fundamental constraint: the Global Interpreter Lock (GIL) prevents true parallel execution of Python bytecode. Concurrency in Python is about **cooperative multitasking** — rapidly switching between tasks waiting on I/O. Different libraries implement this switching differently:

- **Greenlet-based (gevent, eventlet):** Uses lightweight "green threads" that yield control implicitly during I/O operations. Monkey-patches the standard library to make blocking calls cooperative.
- **Async/await (asyncio, trio):** Uses language-level coroutines with explicit `await` points. Requires async-compatible libraries.
- **Structured concurrency (trio):** A refinement of async/await that enforces a hierarchical task model, preventing orphaned tasks.

## Comparison Table

| Feature | gevent | eventlet | trio | asyncio |
|---------|--------|----------|------|---------|
| GitHub Stars | 6,444 | 1,274 | 7,307 | stdlib |
| Concurrency Model | Green threads | Green threads | Structured async | Async/await |
| Monkey-Patching | Required (automatic) | Required (explicit) | None | None |
| Async/Await | No | No | Yes | Yes |
| Learning Curve | Low (transparent) | Low (transparent) | Moderate (nurseries) | Moderate |
| Ecosystem | Vast (patches stdlib) | Moderate | Growing (trio-*) | Largest |
| Cancellation | Cooperative | Cooperative | Strict (nurseries) | Task.cancel() |
| Debugging | Harder (implicit) | Harder (implicit) | Excellent | Good |
| Last Commit | Jul 2026 | Jul 2026 | Jul 2026 | stdlib |

## gevent: The Transparent Concurrency Workhorse

`gevent` makes concurrency nearly invisible. Import it early, and it monkey-patches the standard library so that `socket`, `time.sleep()`, and even database drivers yield to other greenlets automatically. Existing synchronous code becomes concurrent without modification.

```python
# requirements.txt
# gevent==24.11.1

import gevent
from gevent import monkey; monkey.patch_all()

import requests
import time

def fetch_url(url, index):
    print(f"[{index}] Fetching {url}")
    response = requests.get(url)
    print(f"[{index}] {url} → {response.status_code}")
    return response.status_code

urls = ["https://httpbin.org/delay/1"] * 5
start = time.time()

# Spawn greenlets for each URL fetch
jobs = [gevent.spawn(fetch_url, url, i) for i, url in enumerate(urls)]
gevent.joinall(jobs)

print(f"Total: {time.time() - start:.2f}s — all 5 requests in parallel!")
```

The magic: `monkey.patch_all()` replaces `socket.socket()` with gevent's cooperative version, so `requests.get()` yields to other greenlets during network I/O. Five 1-second requests complete in ~1 second.

**Best for:** Existing synchronous codebases that need concurrency without rewrite, web scraping, network-heavy applications.

## eventlet: Lightweight Green Threading

`eventlet` pioneered the green thread approach for Python. Like gevent, it monkey-patches and uses cooperative scheduling — but with a smaller footprint and a focus on networking primitives.

```python
# requirements.txt
# eventlet==0.39.0

import eventlet
eventlet.monkey_patch()

import time
from eventlet.green import urllib.request

def fetch(url, index):
    print(f"[{index}] Starting {url}")
    response = urllib.request.urlopen(url)
    print(f"[{index}] {url} → {response.getcode()}")

pool = eventlet.GreenPool(size=10)
urls = ["https://httpbin.org/delay/1"] * 5
start = time.time()

for i, url in enumerate(urls):
    pool.spawn_n(fetch, url, i)
pool.waitall()

print(f"Total: {time.time() - start:.2f}s")
```

`eventlet` provides its own `GreenPool` for concurrency limiting and `green` module replacements for common stdlib modules. Its `wsgi` server powers many production deployments.

**Best for:** Lightweight networking services, WSGI servers, projects that need green threading with minimal dependencies.

## trio: Structured Concurrency Done Right

`trio` represents a philosophical shift in async Python. Instead of spawning independent tasks and hoping they don't leak, `trio` enforces **structured concurrency** through nurseries — all child tasks must complete before the parent continues. This eliminates entire classes of bugs: orphaned tasks, unexpected cancellations, resource leaks.

```python
# requirements.txt
# trio==0.27.0
# httpx  # for async HTTP

import trio
import httpx
import time

async def fetch(client, url, index):
    print(f"[{index}] Fetching {url}")
    response = await client.get(url)
    print(f"[{index}] {url} → {response.status_code}")

async def main():
    async with httpx.AsyncClient() as client:
        async with trio.open_nursery() as nursery:
            urls = ["https://httpbin.org/delay/1"] * 5
            for i, url in enumerate(urls):
                nursery.start_soon(fetch, client, url, i)
    # All tasks are guaranteed complete here — no leaks!

start = time.time()
trio.run(main)
print(f"Total: {time.time() - start:.2f}s")
```

The nursery pattern means if any child task raises an exception, all sibling tasks are cancelled cleanly — no hanging coroutines. Trio's cancellation is **strict**: it can't be ignored by misbehaving tasks.

**Best for:** New async projects, correctness-critical applications, teams that want predictable task lifetimes.

## asyncio: The Standard Library Foundation

`asyncio` is Python's built-in async framework. Since Python 3.7, it provides the event loop, task management, synchronization primitives, and a growing standard library of async-compatible modules. Most third-party async libraries target asyncio first.

```python
import asyncio
import httpx
import time

async def fetch(client, url, index):
    print(f"[{index}] Fetching {url}")
    response = await client.get(url)
    print(f"[{index}] {url} → {response.status_code}")

async def main():
    async with httpx.AsyncClient() as client:
        urls = ["https://httpbin.org/delay/1"] * 5
        tasks = [fetch(client, url, i) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)

start = time.time()
asyncio.run(main())
print(f"Total: {time.time() - start:.2f}s")
```

`asyncio` has the largest ecosystem: `aiohttp`, `asyncpg`, `aioredis`, `httpx`, `FastAPI`, and thousands of other libraries. Recent Python versions have added `asyncio.TaskGroup` (3.11+) which brings structured concurrency to asyncio — inspired by trio's nurseries.

**Best for:** Any new Python async project, web servers (FastAPI, aiohttp), projects needing the widest third-party library support.

## Why Self-Host Your Async Services?

Running async Python services on your own infrastructure gives you control over event loop tuning, resource allocation, and observability. Gevent and eventlet services benefit from long-running process models with connection pooling — patterns that work well with Docker and Kubernetes. Trio and asyncio services integrate naturally with modern async monitoring tools and structured logging pipelines.

For related async infrastructure guides, see our [Python asyncio libraries comparison](../2026-07-26-python-asyncio-libraries-aiodns-aiofiles-aiomysql-aiopg-aioredis/), our [Python async Redis clients guide](../2026-07-04-python-async-redis-clients-redis-py-aioredis-aredis-fakeredis-walrus/), and our [Python benchmarking tools overview](../2026-07-02-python-benchmarking-pytest-benchmark-codspeed-pyperf-asv/).

## Integration Patterns: Mixing Concurrency Models

Real-world applications often need to bridge between concurrency models. For example, a Flask (synchronous) application using `gevent` as its WSGI server while calling async `trio`-based services. Here are the key integration patterns:

**gevent + asyncio bridge:** Use `gevent.spawn()` for synchronous I/O and `asyncio.run()` for specific async operations. The `gevent-asyncio` compatibility layer (via `gevent.selectors`) allows them to share an event loop, though it requires careful setup.

**Eventlet + async libraries:** Eventlet has limited compatibility with native asyncio. The recommended pattern is to wrap async calls in a thread pool executor: `eventlet.tpool.execute(lambda: asyncio.run(async_func()))`. This trades some efficiency for compatibility.

**Trio + synchronous code:** Trio provides `trio.to_thread.run_sync()` for running blocking code in a worker thread without blocking the event loop. This is the cleanest bridge — the sync function runs in a real OS thread, and trio continues processing other async tasks.

**asyncio + gevent coexistence:** Use `asyncio.run_coroutine_threadsafe()` from a gevent greenlet to submit work to a running asyncio event loop in another thread. This pattern is useful when incrementally migrating from gevent to asyncio.

## Performance and Scalability

Greenlet-based models (gevent, eventlet) generally have lower per-task overhead than async/await because they don't require explicit stack management for each coroutine. However, async/await models (trio, asyncio) have better debugging support and more predictable cancellation behavior.

For C10K-class problems (10,000+ concurrent connections), all four models perform adequately on modern hardware. The bottleneck shifts to application logic and I/O throughput rather than the concurrency model itself.

## FAQ

### Should I use gevent or asyncio for a new project?

For new projects, prefer `asyncio`. It's the standard library, has the largest ecosystem, and async/await is the direction Python is heading. Use `gevent` if you have an existing synchronous codebase you want to make concurrent without rewriting, or if you depend on libraries that aren't async-compatible.

### Is monkey-patching safe in production?

Mostly yes — `gevent` and `eventlet` have been used in production for over a decade (OpenStack uses eventlet extensively). The main risk is third-party C extensions that bypass Python's socket layer. Test thoroughly, especially with database drivers and C-accelerated libraries. Always `monkey.patch_all()` at the very top of your entry point, before any other imports.

### What makes trio's structured concurrency different?

In standard asyncio, if you spawn a task and forget to await it, it becomes an orphan — running in the background, possibly raising unhandled exceptions. Trio's nurseries enforce that all child tasks must complete (or be cancelled) before the parent exits. This makes task lifetimes explicit and prevents resource leaks. Python 3.11's `asyncio.TaskGroup` brings similar guarantees to asyncio.

### Can I use async/await with gevent?

Not natively — gevent uses greenlets, which are a different concurrency primitive than coroutines. There are experimental bridges (`gevent-asyncio`), but they're complex. If you want async/await syntax, use asyncio or trio directly.

### How do I profile async Python applications?

Use `py-spy` for sampling-based profiling (works with all concurrency models), `trio-instrument` for trio-specific tracing, and Python 3.12+'s `sys.monitoring` API for low-overhead event tracing. For asyncio, `asyncio.Task.all_tasks()` helps identify stuck or leaked tasks during debugging.
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python Async Concurrency Models Compared: gevent vs eventlet vs trio vs asyncio",
  "description": "In-depth comparison of Python concurrency approaches — gevent, eventlet, trio, and asyncio — covering green threads vs async/await, monkey-patching, structured concurrency, and real-world deployment patterns.",
  "datePublished": "2026-07-27",
  "dateModified": "2026-07-27",
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
