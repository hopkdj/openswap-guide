---
title: "WebSocket Client Libraries Compared: gorilla/websocket vs ws vs websocket-client vs tokio-tungstenite"
date: "2026-06-20"
tags: ["websocket", "libraries", "real-time", "developer-tools", "go", "nodejs", "python", "rust"]
draft: false
---

Real-time communication powers everything from live chat and multiplayer games to financial tickers and collaborative editing. At the transport layer, WebSockets provide full-duplex communication over a single TCP connection — but implementing the WebSocket protocol correctly requires careful handling of frames, control messages, ping/pong heartbeats, and graceful shutdown. Each language ecosystem offers battle-tested WebSocket client libraries that abstract this complexity.

This guide compares four leading open-source WebSocket client/server libraries: Go's **gorilla/websocket** (24.7K+ stars), Node.js **ws** (22.7K+ stars), Python's **websocket-client** (3.7K+ stars), and Rust's **tokio-tungstenite** (2.4K+ stars). We cover protocol compliance, performance characteristics, concurrency models, and common integration patterns.

## Feature Comparison

| Feature | gorilla/websocket | ws (Node.js) | websocket-client | tokio-tungstenite |
|---------|------------------|-------------|-----------------|------------------|
| Stars | 24,772 ⭐ | 22,767 ⭐ | 3,706 ⭐ | 2,469 ⭐ |
| Language | Go | JavaScript/TS | Python | Rust |
| Client mode | ✅ | ✅ | ✅ | ✅ |
| Server mode | ✅ | ✅ | ❌ (client only) | ✅ |
| Auto-reconnect | Manual | ❌ | ✅ (reconnect) | Manual |
| Proxy support | ✅ (via `ProxyFromEnvironment`) | ✅ (via `agent`) | ✅ (HTTP/SOCKS) | ❌ |
| TLS/SSL | ✅ | ✅ | ✅ | ✅ (rustls/native-tls) |
| Per-message deflate | ✅ | ✅ (built-in) | ❌ | ✅ (feature flag) |
| Ping/pong handling | ✅ (automatic) | ✅ (automatic) | ✅ (automatic) | ✅ (automatic) |
| Concurrency | Goroutines | Event loop | Threads/asyncio | Tokio async |
| Binary frames | ✅ | ✅ | ✅ | ✅ |
| License | BSD-2-Clause | MIT | Apache-2.0 | MIT / Apache-2.0 |

## gorilla/websocket (Go)

gorilla/websocket is the de facto WebSocket library for Go. It provides a minimal, idiomatic API that maps cleanly to Go's concurrency model — one goroutine for reading, one for writing, coordinated through channels.

```go
package main

import (
    "log"
    "net/url"
    "github.com/gorilla/websocket"
)

func main() {
    u := url.URL{Scheme: "wss", Host: "echo.websocket.org", Path: "/"}
    conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
    if err != nil {
        log.Fatal("dial:", err)
    }
    defer conn.Close()

    // Write message
    err = conn.WriteMessage(websocket.TextMessage, []byte("hello"))
    if err != nil {
        log.Fatal("write:", err)
    }

    // Read response
    _, message, err := conn.ReadMessage()
    if err != nil {
        log.Fatal("read:", err)
    }
    log.Printf("Received: %s", message)
}

// Server example
func wsHandler(w http.ResponseWriter, r *http.Request) {
    upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
    conn, _ := upgrader.Upgrade(w, r, nil)
    defer conn.Close()

    for {
        mt, msg, err := conn.ReadMessage()
        if err != nil { break }
        conn.WriteMessage(mt, msg) // Echo
    }
}
```

gorilla/websocket handles control frames transparently — pings generate automatic pongs, close frames trigger graceful shutdown. The `conn.SetReadDeadline()` and `conn.SetPongHandler()` methods provide fine-grained control over connection health monitoring.

## ws (Node.js)

The `ws` library by Einar Otto Stangvik is the most downloaded WebSocket implementation in the npm ecosystem — over 100 million weekly downloads. It emphasizes correctness and RFC compliance.

```javascript
const WebSocket = require('ws');

// Client
const ws = new WebSocket('wss://echo.websocket.org');

ws.on('open', () => {
  ws.send('hello from Node.js');
});

ws.on('message', (data, isBinary) => {
  console.log('Received:', isBinary ? data : data.toString());
});

// Server
const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    ws.send(`Echo: ${message}`);
  });

  // Automatic ping/pong health checks
  ws.isAlive = true;
});

// Heartbeat interval
const interval = setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) return ws.terminate();
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);
```

ws includes built-in automatic reconnection and binary frame support. Its `perMessageDeflate` extension compresses payloads transparently. For production deployments behind reverse proxies, ws correctly handles `X-Forwarded-For` and proxy headers.

## websocket-client (Python)

websocket-client is the primary WebSocket library for Python. It offers both a simple callback API and a more advanced `run_forever()` mode with automatic reconnection.

```python
import websocket

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    ws.send("hello from Python")

ws = websocket.WebSocketApp(
    "wss://echo.websocket.org",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
)

# Run with automatic reconnection
ws.run_forever(
    reconnect=5,  # retry every 5 seconds
    ping_interval=30,
    ping_timeout=10,
)
```

For asyncio-based applications, use the `websockets` library (a separate project by Aymeric Augustin) which provides `async/await` native WebSocket handling. Choose websocket-client for synchronous scripts and background workers, websockets for async web frameworks.

## tokio-tungstenite (Rust)

tokio-tungstenite wraps the `tungstenite-rs` protocol implementation with Tokio async I/O. It provides a lightweight stream-based API that composes naturally with Rust's async ecosystem.

```rust
use tokio_tungstenite::connect_async;
use futures_util::{SinkExt, StreamExt};
use url::Url;

#[tokio::main]
async fn main() {
    let url = Url::parse("wss://echo.websocket.org").unwrap();
    let (ws_stream, _) = connect_async(url).await.unwrap();
    let (mut write, mut read) = ws_stream.split();

    // Send message
    write.send(tokio_tungstenite::tungstenite::Message::Text(
        "hello from Rust".into()
    )).await.unwrap();

    // Receive response
    while let Some(msg) = read.next().await {
        match msg.unwrap() {
            tokio_tungstenite::tungstenite::Message::Text(text) => {
                println!("Received: {}", text);
                break;
            }
            _ => {}
        }
    }
}
```

tokio-tungstenite's stream-splitting pattern allows independent read/write loops — useful for protocols that don't follow strict request-response patterns. Combined with `tokio::select!`, you can concurrently read messages and send periodic heartbeats.

## Integration Patterns

### WebSocket Reverse Proxy with Nginx

```nginx
location /ws/ {
    proxy_pass http://websocket-backend:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

## Why Self-Host Your WebSocket Infrastructure?

Self-hosting WebSocket servers gives you full control over connection limits, message routing, and authentication logic. Cloud WebSocket services charge per connection-minute or per message — costs that scale unpredictably with user growth. Running your own WebSocket infrastructure with these libraries ensures fixed infrastructure costs and data sovereignty.

For building full WebSocket push servers, see our [self-hosted WebSocket push server comparison](../centrifugo-vs-mercure-vs-soketi-self-hosted-websocket-push-server-2026/). For routing WebSocket traffic, our guide on [WebSocket proxy tools](../2026-05-25-self-hosted-websocket-proxy-websocketd-websockify-nchan-guide/) covers practical deployment configurations. If you're building real-time databases, check our [real-time database comparison](../2026-06-17-self-hosted-real-time-databases-rethinkdb-gundb-rxdb/).

## Connection Lifecycle Management

Robust WebSocket connections require careful lifecycle management across reconnects, network partitions, and graceful shutdown:

**Reconnection strategies** differ significantly between libraries. websocket-client (Python) offers built-in `reconnect=5` for automatic retry. gorilla/websocket expects you to implement exponential backoff manually:

```go
func connectWithRetry(url string) (*websocket.Conn, error) {
    backoff := time.Second
    for i := 0; i < 5; i++ {
        conn, _, err := websocket.DefaultDialer.Dial(url, nil)
        if err == nil {
            return conn, nil
        }
        time.Sleep(backoff)
        backoff *= 2
    }
    return nil, fmt.Errorf("max retries exceeded")
}
```

**Heartbeat configuration** is critical for detecting stale connections. All four libraries support ping/pong but with different defaults:

| Library | Default Ping Interval | Pong Timeout | Configurable |
|---------|----------------------|-------------|-------------|
| gorilla/websocket | Manual | Manual | ✅ SetReadDeadline |
| ws | 0 (disabled) | 0 (disabled) | ✅ ws.ping() + interval |
| websocket-client | Manual | Manual | ✅ ping_interval param |
| tokio-tungstenite | 0 (disabled) | None | ✅ Via tokio::time |

For production, set ping intervals between 20-30 seconds. Shorter intervals waste bandwidth; longer intervals risk firewall connection tracking timeouts (often 60-120 seconds on cloud providers).

**Graceful shutdown** involves sending a close frame (code 1000 for normal), waiting for the peer's close acknowledgment, then closing the TCP connection. gorilla/websocket handles this with `conn.WriteControl(websocket.CloseMessage, ...)`. ws emits a `close` event with the remote close code and reason. Always drain unread messages before closing to avoid resource leaks.

## FAQ

### Should I use WebSockets or Server-Sent Events (SSE)?

WebSockets provide full-duplex communication — client and server both send messages freely. SSE is server-to-client only over HTTP. Use WebSockets for chat, gaming, and collaborative editing. Use SSE for live dashboards, notifications, and log streaming — it's simpler and works through standard HTTP proxies.

### How do I handle WebSocket authentication?

Pass authentication tokens in the initial connection request: as a query parameter (`wss://host/path?token=xxx`), a custom header (supported in browser WebSocket API), or via a cookie if the WebSocket shares the same origin. gorilla/websocket and ws support header inspection during the upgrade handshake. For production, use short-lived JWT tokens with refresh logic.

### What is per-message deflate and should I enable it?

Per-message deflate (RFC 7692) compresses WebSocket payloads using zlib. It reduces bandwidth for text-heavy messages (JSON, XML) by 50-80% but adds CPU overhead. Enable it for chat applications and API responses. Disable it for binary blobs (images, protobuf) or latency-sensitive real-time gaming.

### How do I scale WebSocket connections across multiple servers?

Use a message broker (Redis Pub/Sub, NATS, Kafka) to relay messages between WebSocket server instances. Each server maintains connections to its own clients and subscribes to the broker for messages from clients on other servers. The sticky session load balancer directs each client consistently to the same backend.

### Can these libraries handle 10K concurrent connections?

Yes, but with careful tuning. gorilla/websocket on Go can handle 100K+ idle connections per server thanks to goroutine efficiency. ws on Node.js handles 10-50K depending on message processing overhead. Python (websocket-client) is the weakest for concurrency — use the async `websockets` library for high concurrency. tokio-tungstenite leverages Tokio's efficient I/O for very high connection counts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "WebSocket Client Libraries Compared: gorilla/websocket vs ws vs websocket-client vs tokio-tungstenite",
  "description": "Comprehensive comparison of open-source WebSocket libraries across Go, Node.js, Python, and Rust — gorilla/websocket, ws, websocket-client, and tokio-tungstenite — with code examples and deployment patterns.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
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
