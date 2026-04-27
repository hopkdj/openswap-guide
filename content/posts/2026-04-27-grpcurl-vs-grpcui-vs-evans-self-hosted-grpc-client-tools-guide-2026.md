---
title: "gRPCurl vs gRPC UI vs Evans: Best gRPC Client Tools 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "grpc", "api-testing", "developer-tools"]
draft: false
description: "Compare the top open-source gRPC client tools — gRPCurl, gRPC UI, and Evans — for testing and debugging self-hosted gRPC services in 2026."
---

gRPC has become the standard for high-performance internal service communication, but testing and debugging gRPC endpoints is notoriously harder than traditional REST APIs. You cannot simply open a browser or use cURL — gRPC requires binary-encoded Protocol Buffers over HTTP/2.

This guide compares the three leading open-source gRPC client tools: **gRPCurl**, **gRPC UI**, and **Evans**. Each takes a different approach to solving the same problem — making it easy to inspect, test, and interact with self-hosted gRPC services without writing custom client code. For teams also looking to expose gRPC services over REST, check out our [gRPC REST proxy comparison](../2026-04-24-grpc-gateway-vs-connect-vs-grpc-web-self-hosted-rest-proxy-guide-2026/). And for broader API testing needs, see our [API mocking and testing tools guide](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/).

## Why You Need Dedicated gRPC Testing Tools

Unlike REST APIs, which can be tested with any HTTP client, gRPC services present unique challenges:

- **Binary protocol** — gRPC uses Protocol Buffers (protobuf), which are not human-readable in transit
- **HTTP/2 only** — gRPC requires HTTP/2, which many basic HTTP clients do not support
- **Service reflection** — without reflection enabled, clients need `.proto` files to understand available methods
- **Streaming** — gRPC supports unary, server-streaming, client-streaming, and bidirectional streaming RPCs
- **Authentication** — gRPC services often use mTLS, token-based auth, or API keys

The right testing tool solves all these problems, letting you discover service methods, send properly encoded requests, and inspect responses — without writing any client code.

## gRPCurl: The Command-Line Standard

[gRPCurl](https://github.com/fullstorydev/grpcurl) by Fullstory is the most widely adopted gRPC client tool, with over 12,500 stars on GitHub. It is essentially "cURL for gRPC" — a command-line tool that sends gRPC requests from the terminal.

### Key Features

- Full support for unary and streaming RPCs
- Service reflection discovery (auto-discovers methods from server)
- Local `.proto` file loading when reflection is unavailable
- JSON input/output encoding (protobuf ↔ JSON conversion)
- TLS/mTLS support with certificate flags
- Header and metadata injection
- Over 5.5 million Docker Hub pulls

### Installation

**macOS:**
```bash
brew install grpcurl
```

**Linux (prebuilt binary):**
```bash
GRPCURL_VERSION=1.9.2
curl -L https://github.com/fullstorydev/grpcurl/releases/download/v${GRPCURL_VERSION}/grpcurl_${GRPCURL_VERSION}_linux_x86_64.tar.gz | tar xz
sudo mv grpcurl /usr/local/bin/
```

**Docker:**
```bash
docker run fullstorydev/grpcurl:latest -help
```

### Docker Compose Usage

You can run gRPCurl as a one-shot Docker container against any local gRPC service:

```yaml
# docker-compose.yml — gRPC test environment
version: "3.8"

services:
  grpc-server:
    image: your-grpc-server:latest
    ports:
      - "50051:50051"
    environment:
      - GRPC_GO_LOG_VERBOSITY_LEVEL=99

  grpcurl:
    image: fullstorydev/grpcurl:latest
    command:
      - "-plaintext"
      - "-list"
      - "grpc-server:50051"
    depends_on:
      - grpc-server
```

### Usage Examples

List all available services:
```bash
grpcurl -plaintext localhost:50051 list
```

List methods for a specific service:
```bash
grpcurl -plaintext localhost:50051 list myapp.UserService
```

Describe a specific method:
```bash
grpcurl -plaintext localhost:50051 describe myapp.UserService.GetUser
```

Send a unary request with JSON input:
```bash
grpcurl -plaintext \
  -d '{"user_id": "12345"}' \
  localhost:50051 \
  myapp.UserService.GetUser
```

Send a request with TLS:
```bash
grpcurl \
  -cacert ca.pem \
  -cert client.crt \
  -key client.key \
  -d '{"query": "SELECT * FROM users"}' \
  localhost:50051 \
  myapp.QueryService.Execute
```

## gRPC UI: The Interactive Web Console

[gRPC UI](https://github.com/fullstorydev/grpcui) is also by Fullstory and provides a web-based interactive interface for gRPC services — think of it as "Postman for gRPC." It has nearly 6,000 stars on GitHub and over 930,000 Docker Hub pulls.

### Key Features

- Web-based GUI with auto-generated forms from service definitions
- Automatic service discovery via reflection
- Form-based input with field validation
- Response display with syntax highlighting
- Request history within the session
- TLS and plaintext support
- Works with any gRPC server that supports reflection

### Installation

**macOS:**
```bash
brew install grpcui
```

**Linux (prebuilt binary):**
```bash
GRPCUI_VERSION=1.4.2
curl -L https://github.com/fullstorydev/grpcui/releases/download/v${GRPCUI_VERSION}/grpcui_${GRPCUI_VERSION}_linux_x86_64.tar.gz | tar xz
sudo mv grpcui /usr/local/bin/
```

**Docker:**
```bash
docker run -p 8080:8080 fullstorydev/grpcui:latest \
  -plaintext localhost:50051
```

### Docker Compose Setup

Run gRPC UI as a sidecar alongside your gRPC service:

```yaml
# docker-compose.yml — gRPC UI testing stack
version: "3.8"

services:
  grpc-service:
    image: your-grpc-server:latest
    ports:
      - "50051:50051"
    environment:
      - GRPC_GO_LOG_VERBOSITY_LEVEL=99

  grpcui:
    image: fullstorydev/grpcui:latest
    command: ["-plaintext", "grpc-service:50051"]
    ports:
      - "8080:8080"
    depends_on:
      - grpc-service
```

### Usage

Start gRPC UI pointing at your service:
```bash
grpcui -plaintext localhost:50051
```

Then open `http://localhost:8080` in your browser. The interface displays:

1. **Left sidebar** — tree of all available services and methods
2. **Center panel** — auto-generated form with input fields for the selected method
3. **Right panel** — formatted JSON response with headers and trailers

For services with TLS:
```bash
grpcui \
  -cert client.crt \
  -key client.key \
  -cacert ca.pem \
  -port 8443 \
  localhost:50051
```

Using local proto files (when reflection is disabled):
```bash
grpcui -plaintext \
  -proto myservice.proto \
  -proto common.proto \
  localhost:50051
```

## Evans: The Expressive REPL Client

[Evans](https://github.com/ktr0731/evans) by ktr0731 takes a different approach — it is an interactive REPL (Read-Eval-Print Loop) client for gRPC with a focus on expressiveness and workflow efficiency. With over 4,400 stars on GitHub, it is a popular choice among developers who prefer keyboard-driven workflows.

### Key Features

- Interactive REPL mode for conversational gRPC testing
- Auto-completion for service names, method names, and field names
- Request history and navigation within the REPL
- Multiple input modes: JSON, interactive prompt, and raw mode
- Configuration file support for connection profiles
- gRPC web protocol support
- Dark terminal UI with color-coded output

### Installation

**macOS:**
```bash
brew tap ktr0731/evans
brew install evans
```

**Linux (prebuilt binary):**
```bash
EVANS_VERSION=0.10.11
curl -L https://github.com/ktr0731/evans/releases/download/${EVANS_VERSION}/evans_linux_amd64.tar.gz | tar xz
sudo mv evans /usr/local/bin/
```

**From source (requires Go 1.20+):**
```bash
go install github.com/ktr0731/evans@latest
```

### Dockerfile for Evans

Since Evans is not available as an official Docker Hub image, you can build it locally:

```dockerfile
# Dockerfile for Evans gRPC client
FROM golang:1.21-alpine AS builder

WORKDIR /src
RUN go install github.com/ktr0731/evans@latest

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
COPY --from=builder /go/bin/evans /usr/local/bin/evans

ENTRYPOINT ["evans"]
```

Build and run:
```bash
docker build -t evans-grpc .
docker run --rm -it evans-grpc repl --host localhost -p 50051
```

### Usage

Start interactive REPL mode:
```bash
evans repl --host localhost -p 50051
```

Once in the REPL, you can navigate services interactively:
```
myapp.UserService@localhost:50051> show service
+-------------+
|  Service    |
+-------------+
| UserService |
+-------------+

myapp.UserService@localhost:50051> call GetUser
user_id (TYPE_STRING) => 12345
{
  "id": "12345",
  "name": "Jane Smith",
  "email": "jane@example.com"
}
```

Call a method directly (non-REPL mode):
```bash
evans cli call --host localhost -p 50051 \
  -r myapp.UserService.GetUser \
  <<< '{"user_id": "12345"}'
```

Use a configuration profile:
```yaml
# .evans.yaml
default:
  host: localhost
  port: 50051
  proto:
    - ./protos/myservice.proto
    - ./protos/common.proto
```

```bash
evans repl
```

## Feature Comparison Table

| Feature | gRPCurl | gRPC UI | Evans |
|---------|---------|---------|-------|
| **Interface** | CLI (terminal) | Web browser | CLI REPL (terminal) |
| **Stars** | 12,599 | 5,883 | 4,475 |
| **Last Updated** | Jan 2026 | Apr 2026 | Dec 2023 |
| **Language** | Go | JavaScript/Go | Go |
| **Service Discovery** | Reflection + proto files | Reflection + proto files | Reflection + proto files |
| **Unary RPCs** | Yes | Yes | Yes |
| **Server Streaming** | Yes | Yes | Yes |
| **Client Streaming** | Yes | Limited | Yes |
| **Bidirectional Streaming** | Yes | No | Yes |
| **Auto-generated Forms** | No | Yes | No |
| **TLS/mTLS** | Yes | Yes | Yes |
| **Docker Image** | Official (5.5M pulls) | Official (931K pulls) | Community (Dockerfile) |
| **Request History** | No | Session-only | Yes (REPL history) |
| **Auto-completion** | No | No | Yes |
| **gRPC-Web** | No | No | Yes |
| **Best For** | CI/CD, scripts, automation | Visual exploration, quick tests | Interactive development workflow |

## Streaming RPC Support Comparison

One area where these tools differ significantly is streaming support:

### gRPCurl — Full Streaming Support

gRPCurl handles all four gRPC streaming types. For server streaming:

```bash
grpcurl -plaintext localhost:50051 \
  myapp.EventService.Subscribe
```

For bidirectional streaming, pipe input line by line:
```bash
cat events.json | grpcurl -plaintext localhost:50051 \
  myapp.EventService.ProcessStream
```

### gRPC UI — Visual Server Streaming Only

gRPC UI displays server-streaming responses as they arrive in the browser, updating the response panel in real-time. However, it does not support client-streaming or bidirectional streaming due to the limitations of the web-based form interface.

### Evans — Full Interactive Streaming

Evans excels at interactive streaming. In REPL mode, you can send multiple messages to a client-streaming RPC by entering them sequentially:

```
myapp.EventService@localhost:50051> call ProcessStream
event (TYPE_STRING) => {"type": "click", "page": "/home"}
event (TYPE_STRING) => {"type": "scroll", "page": "/home"}
event (TYPE_STRING) => <Ctrl-D>  # End of input
{
  "processed": 2,
  "summary": "2 events from /home"
}
```

## Choosing the Right Tool

| Scenario | Recommended Tool | Why |
|----------|-----------------|-----|
| CI/CD pipeline testing | **gRPCurl** | Scriptable, no GUI needed, works in any container |
| Quick service exploration | **gRPC UI** | Visual forms, auto-discovery, no proto files needed |
| Active development/debugging | **Evans** | REPL with auto-completion, request history, streaming |
| Team demos | **gRPC UI** | Browser-based, shareable via localhost forwarding |
| Production health checks | **gRPCurl** | Lightweight, can run as a sidecar or cron job |
| Learning a new gRPC service | **gRPC UI** | Visual forms make field types and requirements obvious |

### Enable Reflection on Your Server

All three tools work best when your gRPC server has reflection enabled. For Go servers, add the reflection service:

```go
import (
    "google.golang.org/grpc"
    "google.golang.org/grpc/reflection"
)

func main() {
    s := grpc.NewServer()
    // Register your services...
    reflection.Register(s)  // Enable service reflection
    s.Serve(listener)
}
```

For production deployments, you may want to disable reflection and use local `.proto` files instead — all three tools support this mode.

## When to Use Proto Files vs Reflection

While reflection is convenient for development, there are reasons to use `.proto` files:

- **Production security** — reflection exposes your entire service schema
- **Version control** — proto files can be committed alongside your code
- **Offline access** — no need to connect to the server to discover methods
- **Multi-service testing** — load proto files for multiple services simultaneously

All three tools support the `-proto` flag for loading local proto files. For complex projects with many proto files and dependencies:

```bash
# gRPCurl with multiple proto files
grpcurl -plaintext \
  -proto protos/service.proto \
  -proto protos/common.proto \
  -proto protos/auth.proto \
  -import-path protos \
  localhost:50051 \
  list

# gRPC UI with proto files
grpcui -plaintext \
  -proto protos/service.proto \
  -import-path protos \
  localhost:50051

# Evans with proto files
evans repl --host localhost -p 50051 \
  --proto protos/service.proto \
  --proto protos/common.proto \
  --package myapp
```

## FAQ

### What is the difference between gRPCurl and gRPC UI?

gRPCurl is a command-line tool designed for scripting and automation, similar to cURL but for gRPC. gRPC UI is a web-based graphical interface that provides auto-generated forms for interacting with gRPC services. Use gRPCurl for CI/CD pipelines and shell scripts; use gRPC UI for visual exploration and quick manual testing.

### Do I need to enable reflection on my gRPC server?

Reflection is not required but highly recommended for development and testing. Without it, you must provide `.proto` files to any client tool. In Go, enable it with `reflection.Register(s)`. In production, consider disabling reflection to avoid exposing your service schema.

### Can these tools handle TLS/mTLS connections?

Yes, all three tools support TLS and mutual TLS. gRPCurl uses `-cacert`, `-cert`, and `-key` flags. gRPC UI uses the same flags. Evans supports TLS via the `-tls` flag in REPL mode. For self-signed certificates, you can use `-insecure` to skip certificate verification.

### Which tool supports gRPC bidirectional streaming?

gRPCurl and Evans both support bidirectional streaming RPCs. gRPCurl handles it via piped stdin/stdout in the terminal. Evans provides an interactive REPL interface where you can send multiple messages and see streaming responses. gRPC UI does not support bidirectional streaming due to browser limitations.

### Can I use these tools with gRPC-Web services?

Evans is the only tool among the three that natively supports the gRPC-Web protocol. gRPCurl and gRPC UI require standard gRPC over HTTP/2. If your service only exposes gRPC-Web (common in browser-based deployments), Evans is the best choice for server-side testing.

### How do I test a gRPC service running inside Docker?

Use the Docker networking to connect to the service. If your gRPC service is running on port 50051 in a Docker container:

```bash
# From the host machine
grpcurl -plaintext localhost:50051 list

# From another container on the same Docker network
grpcurl -plaintext myservice:50051 list
```

For Docker Compose, add a test service that runs gRPCurl against your target service, as shown in the Docker Compose examples above.

### Are these tools production-ready?

gRPCurl is the most production-hardened, with over 5.5 million Docker Hub pulls and active maintenance by Fullstory. gRPC UI is also well-maintained and recently updated (April 2026). Evans has not been updated since December 2023 but remains stable and functional for most use cases.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "gRPCurl vs gRPC UI vs Evans: Best gRPC Client Tools 2026",
  "description": "Compare the top open-source gRPC client tools — gRPCurl, gRPC UI, and Evans — for testing and debugging self-hosted gRPC services. Includes Docker configs, streaming support, and feature comparison.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
