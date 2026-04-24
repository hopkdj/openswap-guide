---
title: "gRPC Gateway vs Connect vs gRPC-Web: Bridge gRPC Services to REST & Web Clients 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "api", "grpc", "microservices"]
draft: false
description: "Compare grpc-gateway, connectrpc, and gRPC-Web for exposing gRPC services as REST APIs. Includes Docker deployment, protoc setup, and practical configuration examples for self-hosted microservices."
---

If you are running gRPC services internally, you have already discovered the performance and type-safety benefits of Protocol Buffers. But external clients — web browsers, mobile apps, third-party integrations — cannot speak gRPC directly. Browsers have no native gRPC support, and many external partners expect standard REST/JSON APIs.

This is where a gRPC gateway or bridge becomes essential. Instead of manually maintaining a parallel REST API alongside your gRPC service, you use a code-generation or protocol-translation layer to expose the same service over HTTP/1.1 with JSON payloads. In this guide, we compare the three most widely used open-source solutions for bridging gRPC to REST and web clients.

## Why Bridge gRPC to REST and Web Clients

gRPC uses HTTP/2 binary framing, which browsers and many HTTP/1.1 clients cannot consume. A gRPC bridge solves several real-world problems:

- **Browser compatibility**: Web applications need HTTP/1.1 + JSON. A bridge translates gRPC calls into something a browser `fetch()` can understand.
- **Third-party integrations**: External partners typically consume REST APIs. A gateway generates a standard API without rewriting your service logic.
- **API documentation**: Tools like Swagger/OpenAPI generate interactive docs from gRPC service definitions, but only when paired with a gateway that maps gRPC to REST semantics.
- **Gradual migration**: Organizations moving from REST to gRPC can expose both protocols simultaneously during the transition period.
- **Load balancer compatibility**: Many on-premises load balancers and API gateways only understand HTTP/1.1. A bridge lets you keep gRPC internally while serving HTTP externally.

For related reading on routing traffic to self-hosted services, see our [API gateway comparison (APISix vs Kong vs Tyk)](../self-hosted-api-gateway-apisix-kong-tyk-guide/) and [reverse proxy GUI guide (Nginx Proxy Manager vs SWAG vs Caddy)](../nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide/).

## The Three Contenders at a Glance

We evaluated each project using live GitHub data as of April 2026:

| Feature | grpc-gateway | connectrpc/connect | gRPC-Web |
|---------|-------------|-------------------|----------|
| **GitHub Stars** | 19,879 | 3,868 (Go) | 4,474 |
| **Last Updated** | 2026-04-24 | 2026-04-23 | 2023-09-23 |
| **Language** | Go (protoc plugin) | Go, TS, Java, Python, more | TypeScript + Go |
| **Protocol** | gRPC → REST/JSON (reverse proxy) | Connect Protocol (HTTP/1.1 + HTTP/2) | gRPC-Web spec (HTTP/1.1) |
| **Code Generation** | protoc plugin | protoc plugin (buf) | protoc plugin |
| **OpenAPI/Swagger** | Built-in (protoc-gen-openapiv2/v3) | External tools needed | Not built-in |
| **Streaming** | Limited (server-side only) | Full (uni + bidi) | Server streaming only |
| **CORS Support** | Via reverse proxy | Built-in | Via reverse proxy |
| **Browser Support** | Yes (via generated REST API) | Yes (Connect-Web SDK) | Yes (gRPC-Web protocol) |
| **Maturity** | High (CNCF incubating) | Medium (growing ecosystem) | Low (maintenance mode) |

The star counts and update dates reflect real-time data fetched via the GitHub API on the day of publication.

## grpc-gateway (protoc-gen-grpc-gateway)

**Repository**: [grpc-ecosystem/grpc-gateway](https://github.com/grpc-ecosystem/grpc-gateway) — 19,879 stars

grpc-gateway is the most mature and widely adopted solution. It is a `protoc` plugin that reads your `.proto` service definitions and generates a reverse-proxy server that translates RESTful HTTP requests into gRPC calls.

### How It Works

You annotate your `.proto` file with HTTP mapping rules using the `google.api.http` option. The gateway reads these annotations and generates Go code that routes incoming HTTP requests to the appropriate gRPC handler, converting JSON request bodies to protobuf and vice versa.

### Installation

```bash
# Install the protoc plugins
go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest
go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
```

### Proto File with HTTP Annotations

```protobuf
syntax = "proto3";
package echo.v1;

option go_package = "github.com/example/echo/proto/echo/v1;echov1";

import "google/api/annotations.proto";

service EchoService {
  rpc Echo(EchoRequest) returns (EchoResponse) {
    option (google.api.http) = {
      post: "/v1/echo"
      body: "*"
    };
  }
  rpc GetStatus(StatusRequest) returns (StatusResponse) {
    option (google.api.http) = {
      get: "/v1/status"
    };
  }
}

message EchoRequest {
  string message = 1;
  int32 repeat = 2;
}

message EchoResponse {
  repeated string messages = 1;
}

message StatusRequest {}

message StatusResponse {
  string version = 1;
  bool healthy = 2;
}
```

### Code Generation

```bash
protoc -I . \
  --go_out . --go_opt paths=source_relative \
  --go-grpc_out . --go-grpc_opt paths=source_relative \
  --grpc-gateway_out . --grpc-gateway_opt paths=source_relative \
  --openapiv2_out . --openapiv2_opt logtostderr=true \
  proto/echo/v1/echo.proto
```

### Server Implementation

```go
package main

import (
    "context"
    "flag"
    "net"
    "net/http"

    "github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    echov1 "github.com/example/echo/proto/echo/v1"
    "google.golang.org/grpc/reflection"
)

type echoServer struct {
    echov1.UnimplementedEchoServiceServer
}

func (s *echoServer) Echo(ctx context.Context, req *echov1.EchoRequest) (*echov1.EchoResponse, error) {
    messages := make([]string, req.Repeat)
    for i := int32(0); i < req.Repeat; i++ {
        messages[i] = req.Message
    }
    return &echov1.EchoResponse{Messages: messages}, nil
}

func (s *echoServer) GetStatus(ctx context.Context, req *echov1.StatusRequest) (*echov1.StatusResponse, error) {
    return &echov1.StatusResponse{Version: "1.0.0", Healthy: true}, nil
}

func main() {
    grpcPort := flag.Int("grpc-port", 9090, "gRPC server port")
    httpPort := flag.Int("http-port", 8080, "HTTP gateway port")
    flag.Parse()

    // Start gRPC server
    grpcLis, _ := net.Listen("tcp", net.JoinHostPort("0.0.0.0", string(*grpcPort)))
    grpcSrv := grpc.NewServer()
    echov1.RegisterEchoServiceServer(grpcSrv, &echoServer{})
    reflection.Register(grpcSrv)
    go grpcSrv.Serve(grpcLis)

    // Start HTTP gateway
    ctx := context.Background()
    mux := runtime.NewServeMux()
    opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}
    target := net.JoinHostPort("0.0.0.0", string(*grpcPort))
    _ = echov1.RegisterEchoServiceHandlerFromEndpoint(ctx, mux, target, opts)

    http.ListenAndServe(net.JoinHostPort("0.0.0.0", string(*httpPort)), mux)
}
```

### Docker Deployment

```yaml
services:
  echo-service:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "9090:9090"  # gRPC
      - "8080:8080"  # HTTP/REST gateway
    environment:
      - GRPC_PORT=9090
      - HTTP_PORT=8080
    restart: unless-stopped
```

### Strengths

- **Largest ecosystem**: Most widely adopted, extensive documentation, active CNCF project
- **OpenAPI generation**: Automatic Swagger UI from proto files — huge for API documentation
- **HTTP mapping flexibility**: Full control over URL paths, methods, and body mappings via proto annotations
- **Backwards compatible**: Your gRPC service code remains unchanged

### Limitations

- **Go-only runtime**: The generated gateway runs only in Go
- **Limited streaming**: Server-side streaming works, but client-side and bidirectional streaming are not supported over the REST gateway
- **Requires proto annotations**: Every RPC needs explicit `google.api.http` annotations

## connectrpc/connect — Modern Alternative

**Repository**: [connectrpc/connect-go](https://github.com/connectrpc/connect-go) — 3,868 stars

Connect is a newer approach developed by Buf (now connectrpc). Instead of generating a reverse proxy, it defines a new wire protocol — the **Connect Protocol** — that works natively over HTTP/1.1 and HTTP/2 without requiring a separate gateway process.

### How It Works

Connect uses the same `.proto` service definitions as gRPC but implements a simpler wire protocol that browsers can consume directly. The `connect-go` server library handles both gRPC and Connect protocol requests on the same port, so you do not need a separate gateway process.

### Installation

```bash
# Install the Connect Go SDK
go get connectrpc.com/connect

# Install the protoc plugin via buf
go install connectrpc.com/cmd/protoc-gen-connect-go@latest
```

### Proto File (Standard — No Extra Annotations Needed)

```protobuf
syntax = "proto3";
package greet.v1;

option go_package = "github.com/example/greet/proto/greet/v1;greetv1";

message GreetRequest {
  string name = 1;
}

message GreetResponse {
  string greeting = 1;
}

service GreetService {
  rpc Greet(GreetRequest) returns (GreetResponse);
  rpc GreetStream(GreetRequest) returns (stream GreetResponse);
}
```

### Server Implementation

```go
package main

import (
    "context"
    "log"
    "net/http"

    "connectrpc.com/connect"
    greetv1 "github.com/example/greet/proto/greet/v1"
)

type greetServer struct {
    greetv1.UnimplementedGreetServiceHandler
}

func (s *greetServer) Greet(ctx context.Context, req *connect.Request[greetv1.GreetRequest]) (*connect.Response[greetv1.GreetResponse], error) {
    return connect.NewResponse(&greetv1.GreetResponse{
        Greeting: "Hello, " + req.Msg.Name + "!",
    }), nil
}

func main() {
    mux := http.NewServeMux()
    path, handler := greetv1.NewGreetServiceHandler(&greetServer{})
    mux.Handle(path, handler)

    log.Println("Listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", mux))
}
```

### Docker Compose for Connect Service

```yaml
services:
  greet-service:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/greet.v1.GreetService/Greet"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Client-Side (Browser) with Connect-Web

```typescript
import { createConnectTransport } from "@connectrpc/connect-web";
import { GreetService } from "./gen/greet/v1/greet_connect";

const transport = createConnectTransport({
  baseUrl: "http://localhost:8080",
});

const client = createPromiseClient(GreetService, transport);

const response = await client.greet({ name: "World" });
console.log(response.greeting); // "Hello, World!"
```

### Strengths

- **No separate gateway**: The same server binary handles both gRPC and Connect protocol requests
- **Full streaming support**: Unary, server streaming, client streaming, and bidirectional streaming all work
- **Multiple languages**: Go, TypeScript, Java, Python, Swift, Kotlin, Dart, and more
- **Browser-first design**: Connect-Web SDK makes calling services from browsers trivial
- **Built by Buf**: Created by the team behind `buf` CLI, ensuring tight tooling integration

### Limitations

- **Smaller ecosystem**: Newer project, fewer community resources than grpc-gateway
- **No OpenAPI generation**: Swagger docs require additional tooling (e.g., `protoc-gen-openapi` from outside the Connect ecosystem)
- **Requires client SDK**: Browser clients need the Connect-Web library, not plain `fetch()`

## gRPC-Web (improbable-eng)

**Repository**: [improbable-eng/grpc-web](https://github.com/improbable-eng/grpc-web) — 4,474 stars

gRPC-Web is the original browser-compatible gRPC protocol. It defines a spec for sending gRPC requests over HTTP/1.1 with a binary wire format. A proxy (typically Envoy) sits between the browser and the gRPC server to translate the protocol.

**Important**: This repository has not received updates since September 2023 and is effectively in maintenance mode. The official `grpc/grpc-web` repository (by the gRPC team) is the recommended alternative for new projects.

### Architecture

```
Browser (gRPC-Web JS client)
    ↓ HTTP/1.1 + binary frames
Envoy Proxy (grpc-web filter)
    ↓ HTTP/2 gRPC
gRPC Backend Service
```

### Required Envoy Configuration

```yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: local_service
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: grpc_backend
                http_filters:
                  - name: envoy.filters.http.grpc_web
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.grpc_web.v3.GrpcWeb
                  - name: envoy.filters.http.cors
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.cors.v3.Cors
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
    - name: grpc_backend
      connect_timeout: 0.25s
      type: logical_dns
      lb_policy: round_robin
      load_assignment:
        cluster_name: grpc_backend
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: grpc-service
                      port_value: 9090
```

### Docker Compose with Envoy Proxy

```yaml
services:
  grpc-service:
    image: myapp/grpc-backend:latest
    ports:
      - "9090:9090"
    restart: unless-stopped

  envoy:
    image: envoyproxy/envoy:v1.30-latest
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
    ports:
      - "8080:8080"
    depends_on:
      - grpc-service
    restart: unless-stopped
```

### Strengths

- **Official spec**: Defined by the gRPC team, supported by major proxies
- **Binary efficiency**: Uses binary protobuf over HTTP/1.1, smaller payloads than JSON
- **Works with existing gRPC servers**: No server-side changes needed, only the proxy

### Limitations

- **Requires Envoy proxy**: You must deploy and maintain a separate proxy container
- **Server streaming only**: Client and bidirectional streaming are not supported
- **Maintenance mode**: The Improbable repository has been inactive since 2023
- **Complex setup**: Three components (client, proxy, server) instead of two

## Choosing the Right Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Need OpenAPI/Swagger docs | grpc-gateway |
| Browser-first app, full streaming | connectrpc/connect |
| Existing Envoy infrastructure | gRPC-Web |
| Go-only stack, mature ecosystem | grpc-gateway |
| Multi-language clients (Go, TS, Java) | connectrpc/connect |
| Binary payload efficiency required | gRPC-Web |
| Minimal infrastructure footprint | connectrpc/connect (no proxy needed) |

## Quick Start Decision Tree

1. **Do you need Swagger/OpenAPI documentation?** → Use **grpc-gateway**. It generates Swagger specs directly from your proto files.
2. **Are you building a browser-heavy application with streaming needs?** → Use **connectrpc/connect**. The Connect-Web SDK handles streaming in browsers without a proxy.
3. **Do you already run Envoy as your edge proxy?** → Use **gRPC-Web**. Envoy's grpc-web filter is battle-tested.
4. **Starting a greenfield project?** → **connectrpc/connect** is the modern choice with the simplest architecture (no separate gateway process).

For teams already managing service-to-service communication, our [service mesh guide (Consul vs Linkerd vs Istio)](../self-hosted-service-mesh-consul-linkerd-istio-guide/) covers the infrastructure layer that sits above these protocol bridges.

## FAQ

### What is the main difference between grpc-gateway and gRPC-Web?

grpc-gateway generates a REST/JSON API from your gRPC service definitions, making it consumable by any HTTP client. gRPC-Web keeps the binary protobuf format but adapts the protocol for HTTP/1.1, requiring a proxy like Envoy. grpc-gateway outputs human-readable JSON; gRPC-Web outputs binary data.

### Does connectrpc/connect replace gRPC entirely?

No. Connect is a compatible protocol that sits alongside gRPC. A single connect-go server can accept both gRPC clients (over HTTP/2) and Connect clients (over HTTP/1.1 or HTTP/2) on the same port. Your existing gRPC clients continue to work unchanged.

### Can I use grpc-gateway with languages other than Go?

The gateway itself runs only in Go. However, the gRPC service it proxies can be written in any language (Python, Java, C++, etc.). The gateway is just a reverse proxy — it does not need to know the implementation language of the backend service.

### Is gRPC-Web still actively maintained?

The `improbable-eng/grpc-web` repository has been in maintenance mode since September 2023. For new projects, consider using the official `grpc/grpc-web` repository by the gRPC team, or evaluate connectrpc/connect as a more modern alternative.

### Do I need Envoy to use any of these tools?

Only gRPC-Web requires Envoy (or a compatible proxy). grpc-gateway generates a standalone Go binary that runs independently. connectrpc/connect needs no proxy at all — the server handles both protocols directly.

### How do I handle authentication with a gRPC gateway?

With grpc-gateway, you can configure the gateway to forward `Authorization` headers from incoming HTTP requests to the gRPC backend. Connect has built-in interceptor support for middleware. gRPC-Web relies on Envoy's auth filters. All three approaches let you validate tokens (JWT, API keys) before requests reach your service.

### Can I generate client SDKs for multiple languages?

Yes. All three approaches use `.proto` files as the source of truth. With `protoc` and language-specific plugins, you can generate clients for Go, TypeScript, Python, Java, Swift, and more. Connect additionally provides hand-crafted SDKs for several languages that offer a more ergonomic developer experience than raw generated code.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "gRPC Gateway vs Connect vs gRPC-Web: Bridge gRPC Services to REST & Web Clients 2026",
  "description": "Compare grpc-gateway, connectrpc, and gRPC-Web for exposing gRPC services as REST APIs. Includes Docker deployment, protoc setup, and practical configuration examples for self-hosted microservices.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
