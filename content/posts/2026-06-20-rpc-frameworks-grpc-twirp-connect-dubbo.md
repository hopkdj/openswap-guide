---
title: "Open Source RPC Frameworks: gRPC vs Twirp vs Connect RPC vs Apache Dubbo Compared"
date: "2026-06-20"
tags: ["rpc", "microservices", "api", "grpc", "protobuf", "service-communication", "developer-tools"]
draft: false
---

Modern distributed systems depend on efficient service-to-service communication. While REST dominates public APIs, Remote Procedure Call (RPC) frameworks offer protocol buffers, binary serialization, streaming, and lower latency for internal microservice communication. This guide compares four leading open source RPC frameworks — **gRPC**, **Twirp**, **Connect RPC**, and **Apache Dubbo** — across features, performance, ecosystem, and self-hosting considerations.

## Why Your Microservices Need a Dedicated RPC Framework

REST with JSON works fine for browser-to-server communication, but when your backend services talk to each other at scale, the overhead adds up. JSON serialization burns CPU cycles, HTTP/1.1 connection reuse is limited, and hand-writing client libraries for every language is tedious.

Protocol Buffers (protobuf) solve the serialization problem — they are 3-10x smaller and 20-100x faster to encode/decode than JSON. An RPC framework wraps protobuf service definitions, generates type-safe client and server code, and handles transport, authentication, and streaming automatically. The right choice saves months of boilerplate and reduces latency by 40-70% compared to hand-rolled REST endpoints.

If you are already using protocol buffers for schema management, see our [Protobuf tools comparison](../2026-05-07-self-hosted-protobuf-tools-buf-protolock-protovalidate-guide/). For testing and debugging RPC endpoints, our [gRPC client tools guide](../2026-04-27-grpcurl-vs-grpcui-vs-evans-self-hosted-grpc-client-tools-guide/) covers interactive debugging tools.

## Framework Comparison

| Feature | gRPC | Twirp | Connect RPC | Apache Dubbo |
|---------|------|-------|-------------|--------------|
| **Started** | 2015 (Google) | 2018 (Twitch) | 2022 (Buf) | 2011 (Alibaba) |
| **GitHub Stars** | 44,903 | 7,517 | 3,953 | 41,521 |
| **Language** | C++ core, 12+ langs | Go-native | Go, TypeScript, Swift, Kotlin | Java ecosystem, Go, Rust, Node.js |
| **Transport** | HTTP/2 only | HTTP/1.1 + HTTP/2 | HTTP/1.1 + HTTP/2 | TCP, HTTP/2, HTTP/1.1 |
| **Streaming** | Bidirectional, client, server | Unary only | Unary + server streaming | Bidirectional, client, server |
| **Serialization** | Protobuf only | Protobuf + JSON | Protobuf + JSON | 20+ protocols (Hessian, Kryo, FST, Protobuf) |
| **Service Discovery** | External (DNS, Envoy) | External | External | Built-in (ZooKeeper, Nacos, Consul, Redis) |
| **Load Balancing** | Proxy-based (Envoy/Linkerd) | Proxy-based | Proxy-based | Built-in client-side LB |
| **Last Update** | June 2026 | August 2024 | June 2026 | June 2026 |
| **Best For** | Polyglot large-scale systems | Simple Go microservices | Modern TypeScript/Go stacks | Java enterprise + governance-heavy orgs |

## gRPC: The Industry Standard

gRPC is the de facto RPC framework with first-class support across C++, Java, Go, Python, C#, Node.js, Ruby, PHP, Dart, Kotlin, and Swift. Its HTTP/2 transport enables bidirectional streaming — a chat server can push messages to clients, a file upload service can stream chunks, and a live metrics dashboard can receive Server-Sent Events.

**Basic gRPC server in Go:**

```go
package main

import (
    "context"
    "log"
    "net"
    "google.golang.org/grpc"
    pb "your-project/api/v1"
)

type server struct {
    pb.UnimplementedGreeterServer
}

func (s *server) SayHello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloReply, error) {
    return &pb.HelloReply{Message: "Hello, " + req.Name}, nil
}

func main() {
    lis, _ := net.Listen("tcp", ":50051")
    s := grpc.NewServer()
    pb.RegisterGreeterServer(s, &server{})
    log.Println("gRPC server on :50051")
    s.Serve(lis)
}
```

**Docker Compose for a gRPC microservice stack:**

```yaml
version: "3.8"
services:
  grpc-server:
    image: your-org/grpc-server:latest
    ports:
      - "50051:50051"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
    healthcheck:
      test: ["CMD", "grpc-health-probe", "-addr=:50051"]
      interval: 10s

  envoy-proxy:
    image: envoyproxy/envoy:v1.29
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml
    ports:
      - "8080:8080"
      - "9901:9901"

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: grpcdb

  redis:
    image: redis:7-alpine
```

gRPC's weakness is the HTTP/2 requirement — older load balancers, CDNs, and some corporate firewalls do not support it. The gRPC-Gateway plugin can generate REST endpoints from the same protobuf definitions, but adds complexity. For REST-to-gRPC translation patterns, see our [gRPC gateway comparison](../2026-04-24-grpc-gateway-vs-connect-vs-grpc-web-self-hosted-rest-proxy-guide/).

## Twirp: Simplicity First

Twirp was built by Twitch to replace a complex gRPC setup. It strips out streaming support and uses HTTP/1.1 with protobuf-encoded bodies, making it compatible with any HTTP proxy, load balancer, or CDN. The entire Twirp code generator fits in a single Go binary.

**Twirp server in Go:**

```go
package main

import (
    "net/http"
    "github.com/twitchtv/twirp"
    "your-project/rpc/haberdasher"
)

type haberdasherServer struct{}

func (s *haberdasherServer) MakeHat(ctx context.Context, size *haberdasher.Size) (*haberdasher.Hat, error) {
    if size.Inches <= 0 {
        return nil, twirp.InvalidArgumentError("inches", "must be positive")
    }
    return &haberdasher.Hat{Size: size.Inches, Color: "black"}, nil
}

func main() {
    server := &haberdasherServer{}
    twirpHandler := haberdasher.NewHaberdasherServer(server)
    http.ListenAndServe(":8080", twirpHandler)
}
```

The tradeoff is clear: no streaming (requests are fire-and-forget), and the Go-only code generator means non-Go teams need to maintain their own generators. Twirp's last commit was August 2024 — the project is stable but no longer actively developed by Twitch. For teams already standardized on Go and needing simple RPC, Twirp remains a solid choice.

## Connect RPC: Protocol-Agnostic

Connect RPC from Buf Technologies is the newest entrant, supporting three protocols from a single codebase: the Connect protocol (gRPC-compatible but works over HTTP/1.1), gRPC protocol (full HTTP/2 streaming), and gRPC-Web (browser-compatible). This means a single server can handle browser clients, mobile apps, and backend services without protocol translation.

**Connect RPC server in TypeScript:**

```typescript
import { ConnectRouter } from "@connectrpc/connect";
import { ElizaService } from "./gen/eliza_pb";

export default (router: ConnectRouter) =>
  router.service(ElizaService, {
    async say(req) {
      return { sentence: `You said: ${req.sentence}` };
    },
  });
```

**Docker Compose for Connect RPC with Buf Schema Registry:**

```yaml
version: "3.8"
services:
  connect-server:
    image: node:20-alpine
    working_dir: /app
    command: ["node", "dist/server.js"]
    ports:
      - "8080:8080"
    volumes:
      - ./:/app
    environment:
      - BUF_TOKEN=${BUF_TOKEN}

  envoy:
    image: envoyproxy/envoy:v1.29
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml
    ports:
      - "443:443"
```

Connect RPC's killer feature is its gRPC-Web support — browsers can make typed RPC calls without a proxy, great for SPAs and mobile web. The Buf ecosystem (schema registry, linting, breaking change detection) is a significant advantage over plain protobuf.

## Apache Dubbo: The Enterprise Powerhouse

Apache Dubbo is the dominant RPC framework in China's internet ecosystem, powering Alibaba, JD.com, and Didi. Unlike the other three, Dubbo is an entire microservice governance platform — service discovery, load balancing, circuit breaking, rate limiting, metrics, and tracing are all built-in.

**Dubbo provider in Java with Spring Boot:**

```java
@DubboService
public class GreetingServiceImpl implements GreetingService {
    @Override
    public String sayHello(String name) {
        return "Hello, " + name;
    }
}

@SpringBootApplication
@EnableDubbo
public class ProviderApplication {
    public static void main(String[] args) {
        SpringApplication.run(ProviderApplication.class, args);
    }
}
```

**Dubbo with Nacos service discovery (Docker Compose):**

```yaml
version: "3.8"
services:
  nacos:
    image: nacos/nacos-server:v2.3.0
    ports:
      - "8848:8848"
    environment:
      - MODE=standalone

  dubbo-provider:
    image: openjdk:17-slim
    command: ["java", "-jar", "/app/provider.jar"]
    ports:
      - "20880:20880"
    environment:
      - DUBBO_REGISTRY_ADDRESS=nacos://nacos:8848
```

Dubbo supports over 20 serialization protocols and can connect heterogeneous systems that use different wire formats. Its governance dashboard provides real-time traffic management, service topology graphs, and dynamic configuration without restarts. For Java-centric organizations managing hundreds of microservices with complex routing requirements, Dubbo is unmatched.

## Deployment Architecture

When self-hosting RPC frameworks, the deployment pattern typically looks like this:

```
┌──────────┐    ┌─────────────┐    ┌──────────────────┐
│ Client   │───▶│ Load        │───▶│ RPC Server       │
│ (gRPC/   │    │ Balancer    │    │ (Go/Java/TS)     │
│  Connect)│    │ (Envoy/NGINX│    │                  │
└──────────┘    │ /Traefik)   │    │ ┌──────────────┐ │
                └─────────────┘    │ │ Service      │ │
                                   │ │ Registry     │ │
┌──────────┐    ┌─────────────┐    │ │ (Consul/     │ │
│ Metrics  │◀───│ Prometheus  │◀───│ │  ZooKeeper/  │ │
│ (Grafana)│    │ /OpenTelemetry│  │ │  Nacos)      │ │
└──────────┘    └─────────────┘    │ └──────────────┘ │
                                   └──────────────────┘
```

For production self-hosting, pair your RPC framework with a service mesh like Envoy or Linkerd for mutual TLS, retry policies, and distributed tracing. gRPC and Connect RPC use Envoy natively; Dubbo includes its own mesh support.

## FAQ

### When should I use gRPC over REST?
Use gRPC when you need sub-10ms service-to-service latency, bidirectional streaming (chat, live updates, file transfers), or strongly typed contracts across multiple programming languages. Stick with REST for public-facing APIs consumed by third parties, as REST is universally understood and tooled.

### Is Twirp dead since it hasn't been updated since 2024?
Twirp is in maintenance mode — the protocol is stable, the Go implementation is battle-tested at Twitch scale, and the code generator is simple enough to fork if needed. For new projects without an investment in the Twirp ecosystem, Connect RPC offers the same simplicity with active development and broader language support.

### How does Connect RPC differ from gRPC-Web?
gRPC-Web requires a proxy (Envoy) to translate between HTTP/2 gRPC and the browser. Connect RPC's gRPC-Web implementation works without a proxy — the browser calls the server directly over HTTP/1.1 or HTTP/2. Connect also supports the gRPC protocol for backend-to-backend calls from the same codebase.

### Can I migrate from REST to gRPC incrementally?
Yes. You can run gRPC alongside REST on different ports, add gRPC endpoints to existing services using protobuf annotations, or use the gRPC-Gateway plugin to auto-generate a REST API from your protobuf definitions. Many teams start by adding gRPC for new internal services while maintaining REST for existing external APIs.

### Which framework has the best performance?
gRPC with C++ or Rust backends offers the highest raw throughput for streaming workloads. Connect RPC matches gRPC for unary calls and is slightly faster for gRPC-Web. Dubbo with Kryo serialization excels at Java-to-Java communication in the tens of thousands of TPS range. For most applications, the performance differences are negligible compared to database queries and business logic — choose based on ecosystem and team expertise.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Open Source RPC Frameworks: gRPC vs Twirp vs Connect RPC vs Apache Dubbo Compared",
  "description": "Comprehensive comparison of open source RPC frameworks for microservice communication: gRPC, Twirp, Connect RPC, and Apache Dubbo. Covers performance, streaming support, Docker deployment, and self-hosting best practices.",
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
