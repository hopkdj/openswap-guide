---
title: "Go WebSocket Libraries Compared: Gorilla WebSocket vs nhooyr.io/websocket vs gobwas/ws"
date: "2026-07-26"
tags: ["golang", "websocket", "networking", "real-time", "go-libraries"]
draft: false
---

## Introduction

WebSocket is the backbone of real-time communication on the modern web. For Go developers building chat applications, live dashboards, gaming servers, or collaborative tools, choosing the right WebSocket library directly impacts performance, reliability, and maintainability. Three libraries dominate the Go WebSocket landscape: **Gorilla WebSocket** (24,821 stars), **nhooyr.io/websocket** (5,352 stars), and **gobwas/ws** (6,464 stars). Each takes a fundamentally different approach to WebSocket handling, from the battle-tested and widely adopted to the minimal and idiomatic.

In this comparison, we examine API design, performance characteristics, connection management, protocol compliance, and production readiness across all three libraries. Whether you're building a chat server serving millions of concurrent connections or a lightweight WebSocket proxy, this guide helps you pick the right tool.

## Feature Comparison

| Feature | Gorilla WebSocket | nhooyr.io/websocket | gobwas/ws |
|---------|------------------|---------------------|-----------|
| Stars | 24,821 | 5,352 | 6,464 |
| API Style | Traditional callback | Context-aware, idiomatic | Zero-copy, low-level |
| Context Support | Manual timeout | Native context.Context | Partial |
| Compression | Built-in (flate) | Built-in | Manual |
| Subprotocol Negotiation | Yes | Yes | Yes |
| Proxy Support | Manual | Built-in Dialer | Built-in |
| Net.Conn Compatibility | No | Yes | Yes |
| Zero-copy Reads | No | No | Yes |
| Read Deadline Per Message | No | Yes | No |
| Go Module Support | Yes (v1.5+) | Yes | Yes |

## Library Deep Dives

### Gorilla WebSocket (`gorilla/websocket`)

Gorilla WebSocket is the de facto WebSocket library for Go, with over a decade of production use. It provides a comprehensive API that covers nearly every WebSocket use case: upgrading HTTP connections, reading and writing messages with type discrimination (text vs binary), handling control frames (ping/pong/close), and managing compression.

```go
package main

import (
    "log"
    "net/http"
    "github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
    CheckOrigin: func(r *http.Request) bool {
        return true
    },
}

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Printf("upgrade error: %v", err)
        return
    }
    defer conn.Close()

    for {
        messageType, message, err := conn.ReadMessage()
        if err != nil {
            log.Printf("read error: %v", err)
            break
        }
        log.Printf("received: %s", message)

        if err := conn.WriteMessage(messageType, message); err != nil {
            log.Printf("write error: %v", err)
            break
        }
    }
}

func main() {
    http.HandleFunc("/ws", handleWebSocket)
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Strengths:** Extensive documentation, huge community, battle-tested at scale (used by Docker, Kubernetes tools, and countless production systems). The `Upgrader` type provides fine-grained control over the WebSocket handshake with configurable buffer sizes, origin checking, subprotocol selection, and compression.

**Weaknesses:** The API predates `context.Context` and requires manual deadline management. Connection lifecycle is error-prone — forgetting to set read deadlines can leak goroutines. The library uses a traditional blocking I/O model that doesn't leverage Go's newer net.Conn abstractions.

### nhooyr.io/websocket (`nhooyr.io/websocket`)

nhooyr.io/websocket takes a modern, minimal approach. Built from the ground up with `context.Context`, it provides idiomatic Go APIs that feel natural in contemporary Go codebases. Every operation accepts a context, making timeout management, cancellation, and tracing straightforward.

```go
package main

import (
    "context"
    "log"
    "net/http"
    "nhooyr.io/websocket"
    "nhooyr.io/websocket/wsjson"
    "time"
)

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
    conn, err := websocket.Accept(w, r, &websocket.AcceptOptions{
        InsecureSkipVerify: true,
    })
    if err != nil {
        log.Printf("accept error: %v", err)
        return
    }
    defer conn.Close(websocket.StatusNormalClosure, "closing")

    ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
    defer cancel()

    var v interface{}
    if err := wsjson.Read(ctx, conn, &v); err != nil {
        log.Printf("read error: %v", err)
        return
    }

    if err := wsjson.Write(ctx, conn, v); err != nil {
        log.Printf("write error: %v", err)
    }
}

func main() {
    http.HandlerFunc("/ws", handleWebSocket)
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Strengths:** Clean, minimal API designed for modern Go. Built-in support for reading/writing JSON via the `wsjson` sub-package. The `net.Conn` wrapper (`websocket.NetConn()`) allows using the WebSocket connection with any code expecting a standard `net.Conn`. Per-message read deadlines eliminate a common class of timeout bugs. Automatic ping/pong handling.

**Weaknesses:** Smaller community and fewer production references compared to Gorilla. Limited extension support beyond basic compression. The `InsecureSkipVerify` option (required for local development) can be accidentally left enabled in production. Less flexible buffer management than Gorilla.

### gobwas/ws (`github.com/gobwas/ws`)

gobwas/ws is built for raw performance. It exposes WebSocket frame-level operations, giving developers complete control over how messages are read and written. This zero-copy approach makes it ideal for high-throughput proxies, protocol gateways, and scenarios where every allocation matters.

```go
package main

import (
    "log"
    "net"
    "net/http"
    "github.com/gobwas/ws"
    "github.com/gobwas/ws/wsutil"
)

func handleConnection(rawConn net.Conn) {
    conn, _, _, err := ws.UpgradeHTTP(rawConn)
    if err != nil {
        log.Printf("upgrade error: %v", err)
        return
    }
    defer conn.Close()

    for {
        msg, op, err := wsutil.ReadClientData(conn)
        if err != nil {
            log.Printf("read error: %v", err)
            break
        }
        log.Printf("received op=%v: %s", op, msg)

        if err := wsutil.WriteServerMessage(conn, op, msg); err != nil {
            log.Printf("write error: %v", err)
            break
        }
    }
}

func main() {
    http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
        conn, _, _, err := ws.UpgradeHTTP(r, w)
        if err != nil {
            log.Printf("upgrade error: %v", err)
            return
        }
        go handleConnection(conn)
    })
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Strengths:** Zero-copy frame reading and writing keeps allocations minimal. Direct access to WebSocket frame headers for protocol-level inspection. The `wsutil` package provides helper functions for common patterns while retaining low-level control. Excellent for building WebSocket proxies that forward frames without parsing payloads. Supports both client and server upgrades with full frame type control.

**Weaknesses:** Steeper learning curve — developers must understand WebSocket frame semantics. Less community documentation and fewer tutorials. No built-in JSON or text message helpers (you handle payload encoding yourself). More verbose code for common use cases compared to Gorilla or nhooyr.

## Performance Characteristics

When benchmarking these libraries, several patterns emerge. **Gorilla WebSocket** provides solid throughput for most workloads but allocates more memory due to its buffer management strategy and message copying. **nhooyr.io/websocket** balances performance with API cleanliness — its context-aware design adds minimal overhead while improving correctness. **gobwas/ws** consistently achieves the highest throughput and lowest allocations in benchmarks involving high message rates, thanks to its zero-copy frame handling.

For a typical chat server with moderate message rates (<10,000 messages/second), any of the three libraries performs well. The performance differences only become significant at scale — WebSocket proxies handling millions of concurrent connections or real-time gaming servers with sub-millisecond latency requirements benefit most from gobwas/ws's allocation-free design.

## Choosing the Right Library

| Use Case | Recommended Library |
|----------|-------------------|
| Standard web app with WebSocket support | Gorilla WebSocket |
| Modern Go microservice (context-heavy) | nhooyr.io/websocket |
| High-throughput proxy or gateway | gobwas/ws |
| Maximum community support & documentation | Gorilla WebSocket |
| Minimal dependencies & clean API | nhooyr.io/websocket |
| Frame-level control & zero allocations | gobwas/ws |

For new projects adopting modern Go patterns (Go 1.18+ with generics, heavy context usage), nhooyr.io/websocket offers the best developer experience. For brownfield projects already using Gorilla, the migration cost may not justify switching. For infrastructure components where performance is paramount, gobwas/ws delivers measurable gains.

## Why Self-Host Your WebSocket Infrastructure?

Running your own WebSocket server gives you complete control over connection lifecycle, message routing, and authentication. Unlike managed services (Pusher, Ably, PubNub), self-hosted WebSocket solutions eliminate per-message pricing, avoid vendor lock-in, and keep sensitive real-time data within your network perimeter.

For building robust Go-based web servers, see our [Go HTTP middleware comparison](../2026-06-24-go-http-middleware-libraries-negroni-alice-gorilla-mux/). If you're writing comprehensive test suites for your WebSocket handlers, check our [Go testing frameworks guide](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/). For proper error propagation in your WebSocket server, our [Go error handling comparison](../2026-07-24-go-error-handling-pkg-errors-cockroachdb-stdlib-guide/) covers best practices.

Whether you choose Gorilla for its maturity, nhooyr for its modern API, or gobwas for raw performance, Go's WebSocket ecosystem has a library for every use case. The key is matching your performance requirements and team's familiarity with the right abstraction level.

## FAQ

### Which Go WebSocket library has the best performance?

gobwas/ws consistently achieves the highest throughput and lowest memory allocations in benchmarks due to its zero-copy frame handling. However, for most applications, the performance difference between all three libraries is negligible — choose based on API design and team familiarity rather than microbenchmarks.

### Is Gorilla WebSocket still maintained?

Yes, Gorilla WebSocket remains actively maintained with regular releases. Version 1.5+ added full Go module support and several performance improvements. With 24,821 stars and widespread production use, it remains the safest choice for production deployments.

### Can I use nhooyr.io/websocket with the standard net/http server?

Yes. nhooyr.io/websocket is designed to work seamlessly with net/http. It provides an `Accept()` function that upgrades standard HTTP connections and a `NetConn()` wrapper for compatibility with any code expecting a `net.Conn` interface.

### What is the difference between gobwas/ws and the other libraries?

gobwas/ws operates at the WebSocket frame level rather than the message level. This means you work directly with individual WebSocket frames (continuation, text, binary, close, ping, pong) instead of complete messages. This gives you full control but requires understanding the WebSocket protocol (RFC 6455) in detail.

### How do I handle reconnection with these libraries?

None of these libraries provide built-in reconnection logic — that's a client-side concern. On the server side, implement connection tracking with unique session IDs and handle cleanup in defer blocks. For client reconnection, use a separate goroutine with exponential backoff that creates new connections when the existing one drops.

### Which library is best for a production chat application?

For a production chat application, start with Gorilla WebSocket if you value community support and extensive documentation. If your team prefers modern Go patterns with context propagation, nhooyr.io/websocket provides a cleaner experience. For chat applications with hundreds of thousands of concurrent connections, gobwas/ws's allocation efficiency becomes meaningful.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go WebSocket Libraries Compared: Gorilla WebSocket vs nhooyr.io/websocket vs gobwas/ws",
  "description": "In-depth comparison of three Go WebSocket libraries: Gorilla WebSocket (24,821 stars), nhooyr.io/websocket (5,352 stars), and gobwas/ws (6,464 stars). Covers API design, performance, and production readiness.",
  "datePublished": "2026-07-26",
  "dateModified": "2026-07-26",
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
