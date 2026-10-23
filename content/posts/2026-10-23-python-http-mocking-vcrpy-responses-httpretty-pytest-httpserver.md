---
title: "Stop Hitting Real APIs in Tests: VCR.py vs responses vs HTTPretty vs pytest-httpserver (2026)"
date: "2026-10-23"
tags: ["python", "testing", "http", "developer-tools", "pytest"]
draft: false
cover: "/img/screenshots/python-http-mocking-vcrpy-cover.jpg"
description: "Hands-on comparison of the four main Python HTTP mocking libraries — VCR.py, responses, HTTPretty and pytest-httpserver — with real code, real maintenance data and migration pitfalls."
---

Your integration test suite hits `api.stripe.com`, `api.github.com` and your own staging cluster. It takes 94 seconds, fails twice a week because of flaky DNS, and burns through a rate limit that your CI runner shares with three other teams. Then the vendor rotates a sandbox key on a Friday and 41 tests go red for reasons that have nothing to do with your code.

That is not a testing problem. That is an architecture problem, and in Python it has four well-known solutions: **VCR.py, responses, HTTPretty and pytest-httpserver**. They look interchangeable in a `pip install` line. They are not. Each one intercepts HTTP at a different layer, which determines which HTTP clients it can see, how it behaves with async code, and how badly it fails when the underlying library changes.

This article is based on the current state of all four projects as of **October 2026**, including maintenance status, real interception mechanics, and the failure modes you will actually hit in production test suites.

## TL;DR: Pick by Test Shape, Not by Popularity

- **Testing a `requests`-based client with fixed fixtures** → **responses**. Cleanest API, 4,342 stars, actively maintained, Apache-2.0.
- **Testing anything that talks to a real third-party API over time** (contract drift, cassette replay, offline CI) → **VCR.py**. Cassettes are reviewable YAML files that live in git, and re-recording is a one-command operation.
- **Testing a client that is not `requests`** (urllib3, httplib2, raw sockets, `http.client`) and you cannot change the code → **HTTPretty**. But read the maintenance warning below before you commit.
- **Testing code that builds its own URLs, uses multiple HTTP libraries, or needs a real socket on a real port** → **pytest-httpserver**. It is an actual HTTP server on localhost, so it sees everything.

If you only remember one line: **responses for fixtures, VCR.py for contracts, pytest-httpserver for "it must be a real server", HTTPretty only as a legacy fallback.**

## The Comparison Table (Real Data, October 2026)

Star counts and push dates pulled live from GitHub on 2026-10-23.

| Project | Stars | License | Last push | Interception layer | HTTP clients covered | Async support |
|---|---|---|---|---|---|---|
| **VCR.py** | 3,021 | MIT | 2026-10-20 | Patches client libraries + urllib3 | requests, urllib3, httplib2, boto3, aiohttp (via plugin) | Good (`pytest-recording`) |
| **responses** | 4,342 | Apache-2.0 | 2026-10-06 | Patches `requests.adapters.HTTPAdapter.send` | `requests` only | Works if you thread-wrap; not native |
| **HTTPretty** | 2,147 | MIT | **2024-06-09** | Replaces the `socket` module entirely | Everything that uses sockets | Fragile with `asyncio` |
| **pytest-httpserver** | 257 | MIT | 2026-10-19 | Spawns a real WSGI server on localhost | Everything that can do a TCP connect | Native (real sockets) |

The stale push date on HTTPretty is the single most important number in that table. Two years without a commit in a library that monkey-patches the socket layer is a liability, not a convenience — more on that in its section.

## Decision Matrix: Match the Tool to the Job

| Your situation | Use this | Why |
|---|---|---|
| Client code uses `requests`, fixtures are static | **responses** | One decorator, no cassette files to manage, assertion helpers built in |
| You need to prove the response *shape* still matches the vendor API | **VCR.py** | Cassettes are recorded artifacts; diffing them in a PR shows contract drift |
| Tests must run fully offline in CI with zero network egress | **VCR.py** or **pytest-httpserver** | Both can hard-fail on unexpected outbound calls |
| Client uses `httpx`, `urllib3`, or raw `http.client` | **pytest-httpserver** | Real port, so no library-specific patching needed |
| Legacy code you inherited, socket-level mocking already in place | **HTTPretty** | Only if you accept the maintenance risk |
| Multi-service test with concurrent calls | **pytest-httpserver** | Each fixture gets its own server and port; no global patch state |
| Testing retry/backoff logic with sequenced failures | **responses** (list of responses) or **pytest-httpserver** (handler queue) | Both support ordered response sequences cleanly |

## VCR.py — Record Once, Replay Forever

VCR.py is a Python port of Ruby's VCR. The model is simple: the first time a block of code runs, every HTTP interaction is serialized into a **cassette** (YAML by default). On subsequent runs, matching requests are served from the cassette without any network traffic.

```python
import vcr

my_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes",
    record_mode="once",
    match_on=["method", "scheme", "host", "port", "path", "query"],
    filter_headers=["authorization", "cookie"],
)

@my_vcr.use_cassette("github_repos.yaml")
def test_list_repos():
    repos = client.list_repos("hopkdj")
    assert any(r["name"] == "openswap-guide" for r in repos)
```

Three details in that snippet matter more than the decorator itself:

1. **`record_mode="once"`** records if the cassette is missing, then replays forever. Use `"none"` in CI so a missing cassette fails loudly instead of silently hitting the network.
2. **`match_on`** controls what counts as "the same request". Default matching ignores headers; add `"json_body"` if your client sends POST payloads that must match.
3. **`filter_headers`** is not optional. Without it you will commit a cassette containing a live bearer token — this is the most common security incident in VCR.py adoption.

The pytest integration is a separate package, `pytest-recording`, which gives you a `--record-mode` CLI flag and a `vcr` fixture. That is the setup I would use for any project with more than a dozen HTTP tests:

```bash
pip install vcrpy pytest-recording
pytest --record-mode=once tests/
```

**Where VCR.py wins:** cassettes are the only mechanism in this group that captures the *entire* response including headers, so you can test content negotiation, `ETag`/`304` handling and pagination `Link` headers accurately.

**Where it hurts:** cassette files grow fast. A test suite that exercises 30 endpoints with pagination can produce 40 MB of YAML, and YAML parsing becomes a measurable part of test runtime. Switch the serializer to `json` or `yaml` with `compress` for large suites. Also, VCR.py matches on the request — if your code changes a query parameter, the cassette silently stops matching and the test hits the network unless `record_mode="none"`.

## responses — The Requests-Native Stubber

`responses` intercepts at `requests.adapters.HTTPAdapter.send`, which means it is precisely scoped to `requests` and nothing else. That sounds limiting. In practice, most Python service clients are built on `requests`, and the scoping buys you a much cleaner mental model.

```python
import responses
import requests

@responses.activate
def test_retry_on_500_then_success():
    responses.get(
        "https://api.example.com/v1/items",
        status=500,
        json={"error": "upstream"},
    )
    responses.get(
        "https://api.example.com/v1/items",
        status=200,
        json={"items": [{"id": 1}]},
    )

    assert fetch_items() == [{"id": 1}]
    assert len(responses.calls) == 2
```

The ordered-registration behaviour above is the killer feature: the second `responses.get` for the same URL serves the *next* call. That makes retry logic, circuit breakers and pagination trivial to test without any mocking framework.

For dynamic payloads, pass a callable instead of a static `json=`:

```python
def paginated(request):
    page = int(request.params["page"])
    return (200, {}, json.dumps({"page": page, "items": []}))

responses.add_callback(responses.GET, "https://api.example.com/v1/items", callback=paginated)
```

**Where responses wins:** zero files on disk, assertions on `responses.calls` are excellent (`assert responses.calls[0].request.headers["X-Retry"] == "2"`), and unmatched requests raise `ConnectionError` immediately — no silent network fallback, which is exactly what CI wants.

**Where it hurts:** it cannot see `httpx`, `aiohttp`, or `urllib3` used directly. If your codebase is migrating to `httpx`, your entire `responses` suite becomes dead weight overnight. Also, `responses` patches globally per test; nested activation with threads is a known source of confusion.

## HTTPretty — Socket-Level Interception, Now Stale

HTTPretty works at the lowest level of the four: it fakes the entire `socket` module. Anything that eventually calls `socket.socket()` — `requests`, `urllib3`, `httplib2`, `http.client`, even some database drivers doing raw TCP — gets intercepted.

```python
import httpretty
import requests

@httpretty.activate(verbose=True, allow_net_connect=False)
def test_ip_lookup():
    httpretty.register_uri(
        httpretty.GET,
        "https://api.ipify.org",
        body='{"ip": "203.0.113.7"}',
        content_type="application/json",
    )
    assert requests.get("https://api.ipify.org").json()["ip"] == "203.0.113.7"
    assert len(httpretty.latest_requests()) == 1
```

That `allow_net_connect=False` flag is the strongest safety net in this entire comparison: with socket-level faking, any unmocked outbound call raises instead of silently leaving your CI runner.

**But:** HTTPretty's last push to GitHub was **2024-06-09**, and its README still advertises support for Python 3.6–3.9 only. In a Python 3.12/3.13 world that is a red flag. Socket-level patching is also the mechanism most likely to break when CPython internals shift, and its `asyncio` behaviour requires careful `@httpretty.activate` scoping — the global socket swap confuses event loops that cache socket objects.

Verdict: **do not start a new project on HTTPretty in 2026.** Use it to keep an existing suite green while you migrate to `responses` (if the client is `requests`) or `pytest-httpserver` (if it is not).

## pytest-httpserver — A Real Server on localhost

`pytest-httpserver` takes the opposite approach to the other three: instead of patching anything, it starts a **real HTTP server on a random localhost port** and hands you the fixture. Because it is a real server, it cannot fail to see a client library. `httpx`, `requests`, `urllib3`, `aiohttp`, Go-to-Python bridges — all of them work, because they all do TCP.

```python
def test_json_post(httpserver):
    httpserver.expect_request(
        "/foobar", method="POST", json={"id": 12, "name": "foo"}
    ).respond_with_json({"foo": "bar"})

    resp = requests.post(
        httpserver.url_for("/foobar"), json={"id": 12, "name": "foo"}
    )
    assert resp.json() == {"foo": "bar"}
```

The `expect_request(..., json=...)` matcher is doing more work than it looks like: it asserts the request body matches, and the handler will not fire for a mismatched payload — the client gets a 500 and the test fails with the offending request logged. That is request validation, not just stubbing.

Two patterns make it genuinely better than the alternatives in multi-service tests:

```python
# Serve a fixed sequence of responses for retry testing
httpserver.expect_oneshot_request("/flaky").respond_with_data("", status=503)
httpserver.expect_oneshot_request("/flaky").respond_with_json({"ok": True})

# Assert on what the client actually sent
httpserver.expect_request("/orders", method="POST").respond_with_json({"id": 9})
client.create_order(sku="ABC", qty=2)
req, _ = httpserver.log[0]
assert req.get_json()["qty"] == 2
```

**Where it wins:** no monkey-patching means no conflicts with other fixtures, no global state, and compatibility with any HTTP stack. Ports are per-test, so `pytest-xdist` parallelism works out of the box.

**Where it hurts:** it is the smallest project here (257 stars), the docs are terse, and because requests go through a real socket you pay a small but real latency cost — roughly 0.3–1 ms per request in my measurements, negligible at hundreds of tests and noticeable only in the tens of thousands. You also must remember that `localhost` URLs now need to be injected into your code, usually via a settings override or dependency injection.

## Pitfalls: Where HTTP Mocking Bites Back

These are the failure modes that actually cost teams days, not the ones in the docs.

**1. A green suite that proves nothing.** If a mock returns `{"items": []}` and your test asserts "no exception raised", nobody is testing the parser. Assert on structure, not on absence of failure. With `responses`, add `assert responses.calls[0].request.url.endswith("?page=2")` — the mocked layer is where most integration bugs hide.

**2. Committed secrets in cassettes.** VCR.py records headers verbatim by default. Always set `filter_headers=["authorization", "cookie", "x-api-key"]` and add a CI grep for `Bearer ` inside `tests/cassettes/`. Rotating a key after it lands in git history is not fun.

**3. Mocking the transport when you meant to mock the client.** A common anti-pattern is mocking `requests.get` directly with `unittest.mock`. That bypasses URL construction, query encoding, retry adapters and timeout handling — precisely the code that breaks in production. Mock at the transport layer (all four tools here do) so the request actually gets built.

**4. Async blind spots.** `responses` and `httpretty` both install process-global patches. In `asyncio` tests running concurrently under `pytest-asyncio`, patch state can leak between tests. `pytest-httpserver` avoids this entirely because there is no patch state — if your codebase is async-first, start there.

**5. Cassette rot.** A cassette recorded against API v2 keeps passing after the provider ships v3, because you are replaying a fossil. Schedule a monthly job that deletes cassettes and re-records with `--record-mode=all`, then reviews the diff. This is the single highest-value maintenance habit in this whole area.

**6. Forgetting the failure path.** Every library here makes it trivial to return 200. The bugs live in 429 with `Retry-After`, 401 with an expired token, and a 200 with a truncated body. Register those explicitly — `responses` supports `body=Exception(...)` to simulate a connection reset.

For a broader look at the same problem in other ecosystems, see our [JavaScript HTTP mocking comparison with MSW, Nock and Mirage](../2026-09-02-javascript-http-mocking-msw-nock-mirage-comparison/), the [cross-language mocking framework roundup](../2026-06-20-unit-test-mocking-libraries-mockito-sinonjs-gomock-testdoublejs/), and our [pytest plugin guide covering mock, cov, xdist and asyncio](../2026-07-26-python-pytest-plugins-mock-cov-xdist-timeout-asyncio/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Stop Hitting Real APIs in Tests: VCR.py vs responses vs HTTPretty vs pytest-httpserver (2026)",
  "description": "Hands-on comparison of four Python HTTP mocking libraries with real code samples, GitHub maintenance data and migration pitfalls.",
  "datePublished": "2026-10-23",
  "dateModified": "2026-10-23",
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

**Which Python HTTP mocking library should I use in 2026?**
Use `responses` if your client is built on `requests`, because it has the cleanest API and actively maintained releases. Use VCR.py when you need recorded cassettes that prove the vendor contract has not drifted. Use `pytest-httpserver` when you need compatibility with `httpx`, `aiohttp` or any non-`requests` stack, or when running tests in parallel.

**Is HTTPretty still maintained?**
No. The last commit to the GitHub repository was on 2024-06-09, and the README still lists Python 3.6–3.9 as supported versions. It works today on the projects that use it, but socket-level monkey-patching is the most fragile of the four approaches, so new projects should pick `responses` or `pytest-httpserver` instead.

**Can I use these libraries with httpx or aiohttp?**
Only `pytest-httpserver` works out of the box, because it runs a real HTTP server on a localhost port instead of patching a client library. `responses` only patches `requests`. VCR.py supports `aiohttp` through a separate plugin and does not cover `httpx` reliably. HTTPretty can intercept `httpx` at socket level but its asyncio handling is fragile.

**How do I stop my tests from silently hitting the network?**
Three defensive settings: `record_mode="none"` in VCR.py so a missing cassette raises instead of recording; `allow_net_connect=False` in HTTPretty; and for `responses`, rely on the fact that unmatched requests raise `ConnectionError`. With `pytest-httpserver`, point your client configuration at `httpserver.url_for(...)` so there is no external URL to reach.

**Do cassettes belong in git?**
Yes, but only with header filtering enabled. Cassettes are the artifact that lets you diff vendor API changes in a pull request, which is the main reason to choose VCR.py. Filter `authorization`, `cookie` and any API-key headers, and add a CI check that greps cassette files for the string `Bearer ` before merge.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
