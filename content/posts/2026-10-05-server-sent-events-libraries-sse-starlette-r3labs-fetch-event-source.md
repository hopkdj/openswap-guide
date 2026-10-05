---
title: "Server-Sent Events in 2026: sse-starlette vs r3labs/sse vs fetch-event-source vs eventsource"
date: "2026-10-05"
tags: ["developer-tools", "libraries", "real-time", "sse", "python", "golang", "javascript"]
draft: false
---

Here is a decision that derails more projects than it should: you need to push updates from server to browser, and you reach for WebSockets by reflex. Then you discover you have to hand-write reconnection with exponential backoff, track your own last-received-message ID, and negotiate heartbeats to keep corporate proxies from killing idle connections — all of which **Server-Sent Events already give you, in the HTTP standard, for free**.

SSE is a one-way, text-based stream over plain HTTP. It reconnects automatically, it resumes with `Last-Event-ID` without any client-side code, and it works through every proxy that already passes HTTP. If your data flows one direction, SSE is the smaller, more reliable tool. This guide compares the four libraries worth using in 2026, with real API examples from their official repositories.

## Quick Verdict

On the **server side in Python**, use **sse-starlette** — it integrates cleanly with Starlette and FastAPI and handles heartbeats for you. On the **server side in Go**, use **r3labs/sse** for its built-in stream broker. In the **browser**, use the native `EventSource` where it fits, and reach for **@microsoft/fetch-event-source** the moment you need `POST`, custom headers, or auth tokens. For **Node.js or bundler-agnostic clients**, use **eventsource**, the maintained reference implementation with buffer limits and custom-fetch support.

**The rule: if you never need to send data from the client to the server mid-stream, do not use WebSockets. Use SSE and delete your reconnection code.**

## The Four SSE Libraries Compared

| Library | Side | Language | Stars | Last Push | Auto-reconnect | Custom headers | Heartbeat built-in |
|---|---|---|---|---|---|---|---|
| [sse-starlette](https://github.com/sysid/sse-starlette) | Server | Python | 855 | 2026-09-28 | n/a (server) | n/a | Yes (`ping`) |
| [r3labs/sse](https://github.com/r3labs/sse) | Server + client | Go | 1,047 | 2024-06 | Client-side | Via client | Stream broker |
| [@microsoft/fetch-event-source](https://github.com/Azure/fetch-event-source) | Client | TypeScript | 2,881 | 2026-02 | Yes, with retry policy | Yes | n/a |
| [eventsource](https://github.com/EventSource/eventsource) | Client | TypeScript | 1,159 | 2026-09-21 | Yes | Yes (custom `fetch`) | n/a |

Stars are pulled live from the GitHub API at publish time. Note that `r3labs/sse` has received less attention than the other three — check whether its maintenance cadence fits your risk tolerance before adopting it for a new service.

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| FastAPI or Starlette backend streaming progress updates | **sse-starlette** | Native `EventSourceResponse` plus configurable ping intervals |
| Go service broadcasting many independent event streams | **r3labs/sse** | Built-in stream registry; clients subscribe by stream name |
| Browser client that must `POST` a body to start the stream | **@microsoft/fetch-event-source** | Implements SSE on top of `fetch`, so methods and headers are fully controllable |
| Node.js or edge worker consuming an SSE feed | **eventsource** | Runs outside the DOM with memory-safe buffering |
| You need auth on the stream | **fetch-event-source** or **eventsource** | Both let you set headers; the native browser `EventSource` cannot |

## sse-starlette — Streaming from Python

Install:

```bash
pip install sse-starlette
# or, with uv:
uv add sse-starlette
```

The API is a generator wrapped in a response class. This example, adapted from the project README, streams ten events one second apart:

```python
from starlette.applications import Starlette
from starlette.routing import Route
from sse_starlette import EventSourceResponse
import asyncio

async def generate_events():
    for i in range(10):
        yield {"data": f"Event {i}"}
        await asyncio.sleep(1)

async def sse_endpoint(request):
    return EventSourceResponse(generate_events())

app = Starlette(routes=[Route("/events", sse_endpoint)])
```

Two things matter operationally. First, **the generator must yield**; a blocking function will stall the event loop and starve every other request. Second, `EventSourceResponse` sends periodic comment pings by default, which is exactly what keeps intermediate proxies from closing an idle connection. If you have ever written a server where streams "randomly die after 60 seconds", a ping interval is the fix, and this library ships it.

## r3labs/sse — A Stream Broker for Go

Install:

```bash
go get github.com/r3labs/sse/v2
```

Unlike the Python library, `r3labs/sse` gives you a **server object that owns named streams** — clients subscribe by name rather than by URL path. From the README:

```go
func main() {
	server := sse.New()

	// Create a new Mux and set the handler
	mux := http.NewServeMux()
	mux.HandleFunc("/events", server.ServeHTTP)

	http.ListenAndServe(":8080", mux)
}
```

Clients connect by naming the stream as a query parameter:

```
http://server/events?stream=messages
```

And the same package provides a client, which is convenient when your Go service both consumes and produces streams:

```go
client := sse.NewClient("http://server/events")

client.Subscribe("messages", func(msg *sse.Event) {
	// Got some data!
	fmt.Println(msg.Data)
})
```

That named-stream model is the library's real advantage: you can broadcast one event to every subscriber of `orders` without tracking connections yourself. The trade-off is the maintenance cadence noted above, so pin your version and test upgrades deliberately.

## @microsoft/fetch-event-source — SSE with Full HTTP Control

Install:

```bash
npm install @microsoft/fetch-event-source
```

The native `EventSource` API cannot send a request body or set an `Authorization` header — a hard blocker for most authenticated products. This library rebuilds SSE on top of `fetch`, so you keep the event-stream semantics and get HTTP verbs, headers and abort signals:

```ts
import { fetchEventSource } from '@microsoft/fetch-event-source';

await fetchEventSource('/api/sse', {
    onmessage(ev) {
        console.log(ev.data);
    }
});
```

Because it is `fetch` underneath, you can `POST` a payload to start a stream:

```ts
const ctrl = new AbortController();

fetchEventSource('/api/sse', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        foo: 'bar'
    }),
});
```

Its retry model is explicit rather than magic: `onopen` inspects the response, `onclose` fires when the server ends the stream, and `onerror` receives the exception. Throw `RetriableError` to reconnect with backoff or `FatalError` to stop permanently — which is the correct way to distinguish "the network blipped" from "your token expired and retrying will never help".

## eventsource — The Maintained Reference Client

Install:

```bash
npm install --save eventsource
```

This is the de-facto standard implementation, usable in the browser and in Node.js. Its API deliberately mirrors the native one:

```ts
import { EventSource } from 'eventsource';

const es = new EventSource('https://my-server.com/sse');

es.addEventListener('notice', (e) => {
    console.log(e.data);
});
```

Where it beats the browser built-in is configuration. You can cap memory with `maxBufferSize`:

```ts
const es = new EventSource('https://my-server.com/sse', {
  maxBufferSize: 10 * 1024 * 1024, // 10 MB
});
```

…and you can supply your own `fetch` implementation, which is the escape hatch for adding auth headers without switching libraries:

```ts
const es = new EventSource('https://my-server.com/sse', {
  fetch: (input, init) =>
    fetch(input, {
      ...init,
      headers: { ...init.headers, Authorization: 'Bearer token' },
    }),
});
```

The `maxBufferSize` option is not cosmetic. An SSE connection is a live socket; without a cap, a server that emits faster than the client consumes will grow the client's buffer until the tab dies.

## Common Pitfalls

**1. Reverse proxies buffer your stream and it looks "broken".** nginx buffers proxied responses by default, so events arrive in bursts or not at all. Set `proxy_buffering off;` for the stream location, send an `X-Accel-Buffering: no` header, and make sure compression is disabled for `text/event-stream` — gzip buffers until it has enough data to flush.

**2. HTTP/1.1 limits you to six connections per domain.** Six tabs streaming from the same host exhausts the browser's connection pool and blocks your other requests. Serve SSE over HTTP/2, where multiplexing removes the limit.

**3. Idle timeouts kill silent streams.** If nothing is sent for 30–60 seconds, load balancers and corporate proxies close the connection. Send a comment ping (`: ping\n\n`) on an interval — sse-starlette does this for you; on other stacks, build it in.

**4. Resumption is a contract you must honour on the server.** The browser sends `Last-Event-ID` when it reconnects. If your server ignores that header, clients silently lose every event produced during the outage. If you use `id:` fields, you must implement replay.

**5. SSE is UTF-8 text only.** There is no binary mode. For binary payloads, base64-encode and accept the ~33% overhead, or switch protocol — do not try to shove raw bytes into a `data:` field.

**6. Slow consumers need backpressure.** An unbounded generator writing to a stalled client will consume server memory. Bound your per-connection queue and drop or disconnect clients that fall too far behind.

For the bidirectional case — where the client really must push data mid-stream — see our [WebSocket client libraries comparison](../2026-06-20-websocket-client-libraries-gorilla-ws-websocketclient-tokio-tungstenite/). If you are layering reconnection logic on top of any of these, our [retry and backoff libraries guide](../2026-06-21-retry-backoff-libraries-tenacity-polly-spring-retry-retry-go/) covers the correct policy shapes, and for device-level telemetry where SSE is the wrong fit, the [MQTT broker guide](../2026-06-05-mqtt-sn-rsmb-paho-emqx-sensor-network-guide/) is the better starting point.

## FAQ

**When should I use SSE instead of WebSockets?**
Use SSE when data flows only from server to client: notifications, progress bars, live logs, tickers, and dashboards. Use WebSockets when the client must send messages on the same long-lived connection, or when you need binary frames.

**Does Server-Sent Events reconnect automatically?**
Yes. The browser `EventSource` reconnects on its own and sends the `Last-Event-ID` header so the server can resume. You only need to implement the replay side on the server.

**Can I send an `Authorization` header with SSE?**
Not with the native browser `EventSource`. Use **@microsoft/fetch-event-source** or **eventsource** with a custom `fetch`, both of which let you set headers. Alternatively, authenticate with a cookie or a short-lived query token.

**Why does my SSE stream stop working behind nginx?**
Almost always response buffering. Disable `proxy_buffering` for the stream location and send `X-Accel-Buffering: no`. Compressing `text/event-stream` causes the same symptom because the compressor holds data until it has a full block.

**Is SSE compatible with HTTP/2?**
Yes, and it is better there. HTTP/2 multiplexes many streams over one connection, removing the HTTP/1.1 six-connections-per-domain ceiling that otherwise limits how many tabs can subscribe.

**How do I keep an SSE connection alive through a load balancer?**
Send a heartbeat comment every 15–30 seconds. That traffic resets idle timers on every hop. Most libraries, including sse-starlette, provide a ping interval setting for exactly this purpose.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Server-Sent Events in 2026: sse-starlette vs r3labs/sse vs fetch-event-source vs eventsource",
  "description": "A practical 2026 comparison of Server-Sent Events libraries for Python, Go, TypeScript and Node.js, with real API examples, proxy pitfalls and reconnection behaviour.",
  "datePublished": "2026-10-05",
  "dateModified": "2026-10-05",
  "author": { "@type": "Organization", "name": "OpenSwap Guide" },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": { "@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png" }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
