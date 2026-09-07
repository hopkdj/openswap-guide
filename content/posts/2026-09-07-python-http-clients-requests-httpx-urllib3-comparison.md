---
title: "Python HTTP Clients in 2026: requests vs httpx vs urllib3 — Which One Should You Actually Use?"
date: "2026-09-07"
tags: ["python", "http", "http-clients", "developer-tools", "libraries"]
draft: false
---

Every Python project talks to an HTTP API eventually, and that is exactly when most teams discover they have been using the wrong tool without knowing it. **requests (54,286 stars) is the friendly face you already know. urllib3 (4,053 stars) is the engine underneath it — requests literally imports urllib3 and inherits its connection pooling, retries, and TLS handling. httpx (15,462 stars) is the modern challenger that re-implemented everything from scratch to give you one API that works synchronously and asynchronously, with HTTP/2 support.** Pick requests for scripts and you lose async; pick httpx for an async service and you lose nothing except muscle memory; pick urllib3 directly and you get the control that library authors need but a learning curve that application developers do not.

## TL;DR — Quick Verdict

**Writing scripts, glue code, or small services that run top-to-bottom? Use requests** — it is the most readable HTTP API in the language, it wraps urllib3 so you inherit production-grade pooling and retries for free, and it remains actively maintained (last push September 2026). **Building a modern async application — FastAPI service, data pipeline, anything with `async def`? Use httpx** — its `AsyncClient` mirrors the sync API exactly, it speaks HTTP/2, and its default 5-second timeout is a feature, not a bug. **Authoring a library, or need raw control over connection pools, retries, and low-level behavior? Use urllib3 directly** — it is what requests trusts under the hood, and using it directly means one less dependency layer between your code and the socket. If you already use requests everywhere and everything works: keep using it — but add httpx the day a codebase goes async.

## Quick Comparison Table

| Dimension | requests | httpx | urllib3 |
|---|---|---|---|
| GitHub stars | 54,286 | 15,462 | 4,053 |
| Last push (2026) | Sep 02 | Mar 29 | Sep 05 |
| License | Apache-2.0 | BSD-3-Clause | MIT |
| Sync API | Yes (only) | Yes + async (`AsyncClient`) | Yes (only) |
| HTTP/2 | No | Yes (`httpx[http2]` extra) | No |
| Built on | urllib3 | httpcore + h11/h2 | Pure Python + stdlib |
| Default timeout | None (must set) | 5 seconds | None (must set) |
| Connection pooling | Via urllib3 | Built-in `Client` | Core feature (`PoolManager`) |
| Configurable retries | Via urllib3 | `transport` retries / manual | First-class `Retry` policy |
| Typed API (PEP 561) | Stubs only | Native | Native |
| File upload / streaming | Yes | Yes | Yes (lower-level) |
| Ideal for | Scripts, glue, teaching | Async apps, HTTP/2, typed code | Libraries, embedding, control |

## Decision Matrix — Pick in 10 Seconds

| Use Case | Recommended Client | Why |
|---|---|---|
| Quick script or REPL session against a REST API | requests | One-liner readability; you already know it |
| FastAPI/async service calling other services | httpx | `AsyncClient` integrates with your event loop |
| Need HTTP/2 or typed clients in a modern codebase | httpx | Only one of the three with HTTP/2 and native typing |
| You maintain a library that other code imports | urllib3 | Minimal deps, no API churn, full control; let callers choose a wrapper |
| Legacy service with requests everywhere, no async | requests | Zero migration value in churning working code |
| Very long-running worker needing precise retry/backoff | urllib3 | `Retry(total=…, backoff_factor=…)` is explicit and testable |

## urllib3 — The Engine Room

urllib3 is the oldest and lowest-level of the three: a pure-Python HTTP client built on the standard library, whose superpower is **connection pooling** — it keeps alive and reuses TCP/TLS connections to the same host, which is the single biggest practical performance win in HTTP clients. Its v2 API added a module-level convenience function that makes casual use almost as simple as requests:

```python
>>> import urllib3
>>> resp = urllib3.request("GET", "http://httpbin.org/robots.txt")
>>> resp.status
200
>>> resp.data
b"User-agent: *\nDisallow: /deny\n"
```

Note that `resp.data` is **bytes** — urllib3 does not guess encodings or parse JSON for you, because it is not trying to be a friendly API; it is trying to be a correct, controllable one. The real power lives in `PoolManager` and `Retry`, which is where production behavior like bounded retries with exponential backoff is configured:

```python
import urllib3

http = urllib3.PoolManager(retries=urllib3.Retry(total=3, backoff_factor=1.0))
resp = http.request("GET", "https://api.example.com/items", timeout=urllib3.Timeout(connect=2, read=10))
```

Because requests is built directly on urllib3, every requests session is already using urllib3's pools and retry machinery — you are just not seeing it. urllib3 also powers much of the AWS SDK's HTTP layer and is one of the most-downloaded packages on PyPI, which makes its **backward-compatibility discipline** unusually important: its maintainers treat breaking changes as a years-long migration, not a release-note bullet. Use urllib3 directly when you are writing a library (one lean dependency instead of the requests stack) or when you need retry/backoff semantics that are precise and inspectable.

## requests — HTTP for Humans, Still

requests, born in 2011, defined what a friendly HTTP API looks like: `requests.get(url)` returns a `Response` whose `.text`, `.json()`, `.headers`, and `.status_code` are exactly what you expect. The quickstart from the project README is still the cleanest demonstration of the philosophy — authentication is an argument, not a dance:

```python
>>> import requests
>>> r = requests.get('https://httpbin.org/basic-auth/user/pass', auth=('user', 'pass'))
>>> r.status_code
200
>>> r.headers['content-type']
'application/json; charset=utf8'
>>> r.encoding
'utf-8'
>>> r.text
'{"authenticated": true, ...'
>>> r.json()
{'authenticated': True, ...}
```

The critical detail for production use is the one the README does not shout about: **requests has no default timeout**. A `requests.get(url)` call can hang forever if the server stops responding — every production call should set `timeout=`, e.g. `requests.get(url, timeout=10)`. On the maintenance question: requests is not dead. The project pushed updates in September 2026 and remains the default choice for scripts, teaching, and any synchronous code where readability matters more than async support. But it is also deliberately feature-complete: no HTTP/2, no native async, and the typed experience comes only via third-party stubs. Those are not bugs — they are the boundaries of a design that has not needed to change in a decade.

## httpx — The Modern, Async-First Challenger

httpx was built to answer one question requests could not: what if the same elegant API worked in `async def` code, spoke HTTP/2, and shipped with native type hints? Its README quickstart looks almost identical to requests — by design:

```python
>>> import httpx
>>> r = httpx.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

The async half of the API is where httpx separates from requests. You create one `AsyncClient` and reuse it — that is what gives you connection pooling in an event-loop world — then `await` calls that mirror the sync signatures:

```python
import httpx

async with httpx.AsyncClient(base_url="https://api.example.com", timeout=10.0) as client:
    r = await client.get("/items", params={"page": 2})
    r.raise_for_status()
    items = r.json()
```

Three practical notes. First, HTTP/2 is opt-in via an extra: `pip install httpx[http2]`. Second, httpx ships a default 5-second timeout — a deliberate safety choice that has saved many a production job from hanging, and one you can override per-call or per-client. Third, httpx does **not** use urllib3: it is built on its own `httpcore` layer with `h11`/`h2` for protocol handling, which means you can use requests and httpx in the same project without fighting over urllib3 versions — a real migration relief. The project's release cadence has slowed (last push March 2026), which reflects a mature, steady-state maintenance mode rather than abandonment.

## Pitfalls — What the Tutorials Do Not Tell You

**Version conflicts between requests and urllib3 are the classic dependency headache.** requests allows `urllib3>=1.21.1,<3`, and older requests releases pinned `<2` — if another package in your environment forces urllib3 1.x or a too-new 2.x, `pip` resolution can stall or produce a broken install. Fix: keep requests updated (modern requests handles urllib3 2.x fine), and use `pip-tools`/lock files rather than letting a resolver negotiate at deploy time. httpx sidesteps this entirely by not depending on urllib3.

**Timeouts: two of the three default to "hang forever."** requests and urllib3 both use no default timeout — a stalled connection can block a worker indefinitely. Set `timeout=` explicitly on every call in requests (`timeout=10`), pass `urllib3.Timeout(connect=…, read=…)` for urllib3, and enjoy httpx's built-in 5-second default, which you can raise per-client. A missing timeout is the single most common cause of "my pipeline randomly freezes" in production Python.

**Async clients must be reused, not recreated.** Creating an `httpx.AsyncClient` per request defeats connection pooling and leaks event-loop resources; create one client per application (or per task group) and `await` many requests through it. The same principle applies to `requests.Session()` in threaded code — a session per thread, not per request, is what makes keep-alive work.

**`r.json()` failing is a feature, not a bug — but only if you handle it.** `requests` and `httpx` both raise on invalid JSON; check `resp.raise_for_status()` first (or `resp.is_success`) so you do not mistake a 502 HTML error page for an empty JSON document. For large downloads, use streaming (`stream=True` + `iter_content` in requests; `client.stream(...)` in httpx) instead of loading whole bodies into memory.

**Proxies and environment variables behave differently than you expect.** All three honor `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` via their "trust environment" defaults, but the matching rules differ: requests' `trust_env` on sessions, httpx's `trust_env` on clients, and urllib3's proxy support via `ProxyManager`. If your code runs behind a corporate proxy, test the `NO_PROXY` behavior explicitly — wildcard matching is where the three diverge most in practice.

**Choosing an HTTP client is also choosing its neighbors.** Our [TypeScript HTTP client comparison](../2026-07-28-typescript-http-client-libraries-axios-got-undici-ky-node-fetch-comparison/) and [Go HTTP client comparison](../2026-08-17-go-http-client-libraries-resty-vs-fasthttp-vs-req-comparison/) cover the same decision in other ecosystems, and our [Python async web frameworks guide](../2026-08-10-python-async-web-frameworks-aiohttp-starlette-sanic/) shows where httpx typically runs — inside FastAPI and Starlette services. If you are still managing dependencies with pip directly, our [Python dependency management comparison](../2026-06-22-python-dependency-management-poetry-pipenv-hatch-pdm/) is the natural next read.

## FAQ

**Is requests dead or unmaintained in 2026?**
No. The project is in maintenance-heavy but active development — the repository saw commits in September 2026, and requests remains one of the most-downloaded packages on PyPI. What is true is that it is feature-complete: the maintainers have consistently declined HTTP/2 and native async support to preserve API stability. "Unmaintained" is wrong; "deliberately frozen in design" is accurate.

**Does httpx use urllib3 under the hood?**
No. httpx is built on its own `httpcore` transport layer with `h11` (HTTP/1.1) and `h2` (HTTP/2) protocol implementations. This independence is a practical advantage: migrating a project from requests to httpx cannot trigger the urllib3 version conflicts that sometimes appear when two urllib3-dependent packages disagree.

**When should I use urllib3 directly instead of requests?**
Three situations: (1) you are writing a library and want one lean dependency with a stable API your users will not see; (2) you need precise, inspectable retry policies (`Retry(total=…, backoff_factor=…)`) or low-level control over pools, certificates, and connection reuse; (3) you are embedding HTTP into a tool where requests' magic (auto-encoding, JSON guessing) is more liability than convenience. Application code — scripts, services, glue — is almost always better served by requests or httpx.

**Is httpx faster than requests?**
For typical JSON/CRUD workloads, the difference is small and usually irrelevant — both are bounded by the network and the server. httpx's real advantages are HTTP/2 multiplexing (when the server supports it), native async (no thread pool needed in async apps), and connection reuse that is easy to get right by default. urllib3's pooling gives requests comparable keep-alive behavior; benchmark before you assume one is "faster."

**How do I migrate a codebase from requests to httpx?**
The APIs align closely: `requests.get(url, params=…)` becomes `httpx.get(url, params=…)`; `requests.Session()` becomes `httpx.Client()`; `session.get(...).json()` works the same on both; `requests.exceptions.RequestException` maps to `httpx.HTTPError`. The differences to watch: httpx's default 5-second timeout (raise it if your services are slow), `auth=(user, pass)` tuples need `httpx.BasicAuth(user, pass)` in older httpx versions (modern httpx accepts tuples again), and streaming uses `client.stream(...)` context managers. Run a small surface first — a single service — before a repo-wide sweep.

**Which client should I teach a beginner?**
requests. Its API is the language of HTTP in Python — most documentation, tutorials, and Stack Overflow answers use it, and the concepts (session, response, timeout, auth) transfer directly to httpx when the learner later needs async or HTTP/2. Teaching requests first means teaching the concepts; teaching httpx first means teaching the concepts plus a sync/async duality that beginners do not need on day one.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python HTTP Clients in 2026: requests vs httpx vs urllib3 — Which One Should You Actually Use?",
  "description": "Compare Python HTTP clients in 2026: requests 54k stars vs httpx 15k stars vs urllib3. Sync vs async, HTTP/2, timeouts, retries, connection pooling — with code examples and a decision matrix.",
  "datePublished": "2026-09-07",
  "dateModified": "2026-09-07",
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
