---
title: "Java Embedded HTTP Servers: Jetty vs Netty vs Undertow vs Apache Tomcat Comparison 2026"
date: "2026-07-04"
tags: ["java", "http-server", "jetty", "netty", "undertow", "tomcat", "embedded-server", "web-framework", "developer-tools"]
draft: false
---

## Introduction

Choosing the right embedded HTTP server for your Java application can dramatically affect performance, resource usage, and developer experience. Whether you are building a microservice, a REST API, or embedding a server inside a desktop application, four options dominate the Java ecosystem: **Jetty**, **Netty**, **Undertow**, and **Apache Tomcat**.

Each of these servers takes a different architectural approach. Jetty focuses on standards compliance and embeddability. Netty prioritizes raw throughput with its event-driven, non-blocking design. Undertow emphasizes low memory footprint and composable handlers. Apache Tomcat remains the gold standard for Servlet API compatibility with decades of production hardening.

In this article, we compare these embedded servers across performance, ease of use, protocol support, and production readiness to help you choose the right one for your next Java project.

## Quick Comparison Table

| Feature | Jetty | Netty | Undertow | Apache Tomcat |
|---------|-------|-------|----------|---------------|
| **Stars** | 4,089 | 35,000 | 3,751 | 8,192 |
| **Architecture** | Thread pool + async | Event loop (NIO) | XNIO (non-blocking) | Thread-per-request + NIO |
| **Servlet Support** | Full (5.0/6.0) | Via adapter | Full (5.0/6.0) | Full (5.0/6.0) |
| **HTTP/2** | Yes (native) | Yes (codec) | Yes (native) | Yes (native) |
| **HTTP/3** | Yes (experimental) | Via quiche | No | No |
| **WebSocket** | Yes | Yes | Yes | Yes |
| **Memory Footprint** | ~8-12 MB | ~6-8 MB | ~4-6 MB | ~12-20 MB |
| **Embeddability** | Excellent | Excellent | Excellent | Good (needs config) |
| **Spring Boot** | Default (embedded) | Reactor Netty | Supported | Default (traditional) |
| **License** | EPL 2.0 / Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Embedded Server Setup Examples

### Jetty Embedded

Jetty can be embedded with just a few lines of code. Add the Maven dependency:

```xml
<dependency>
    <groupId>org.eclipse.jetty</groupId>
    <artifactId>jetty-server</artifactId>
    <version>12.0.16</version>
</dependency>
```

Basic embedded server:

```java
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.handler.DefaultHandler;

public class JettyApp {
    public static void main(String[] args) throws Exception {
        Server server = new Server(8080);
        server.setHandler(new DefaultHandler());
        server.start();
        server.join();
    }
}
```

### Netty Embedded

Netty uses a channel-based architecture. Maven dependency:

```xml
<dependency>
    <groupId>io.netty</groupId>
    <artifactId>netty-all</artifactId>
    <version>4.1.115.Final</version>
</dependency>
```

Basic HTTP server:

```java
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.nio.NioServerSocketChannel;

public class NettyApp {
    public static void main(String[] args) throws Exception {
        NioEventLoopGroup bossGroup = new NioEventLoopGroup(1);
        NioEventLoopGroup workerGroup = new NioEventLoopGroup();
        try {
            ServerBootstrap bootstrap = new ServerBootstrap();
            bootstrap.group(bossGroup, workerGroup)
                .channel(NioServerSocketChannel.class)
                .childHandler(new HttpServerInitializer());
            bootstrap.bind(8080).sync().channel().closeFuture().sync();
        } finally {
            bossGroup.shutdownGracefully();
            workerGroup.shutdownGracefully();
        }
    }
}
```

### Undertow Embedded

Undertow provides a fluent builder API. Maven dependency:

```xml
<dependency>
    <groupId>io.undertow</groupId>
    <artifactId>undertow-core</artifactId>
    <version>2.3.17.Final</version>
</dependency>
```

Minimal server:

```java
import io.undertow.Undertow;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;

public class UndertowApp {
    public static void main(String[] args) {
        Undertow server = Undertow.builder()
            .addHttpListener(8080, "0.0.0.0")
            .setHandler(exchange -> {
                exchange.getResponseSender().send("Hello from Undertow!");
            })
            .build();
        server.start();
    }
}
```

### Apache Tomcat Embedded

Tomcat embedded requires more configuration but provides full Servlet support:

```xml
<dependency>
    <groupId>org.apache.tomcat.embed</groupId>
    <artifactId>tomcat-embed-core</artifactId>
    <version>10.1.34</version>
</dependency>
```

Setup example:

```java
import org.apache.catalina.startup.Tomcat;
import org.apache.catalina.Context;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

public class TomcatApp {
    public static void main(String[] args) throws Exception {
        Tomcat tomcat = new Tomcat();
        tomcat.setPort(8080);
        tomcat.getConnector();
        
        Context ctx = tomcat.addContext("", null);
        Tomcat.addServlet(ctx, "hello", new HttpServlet() {
            @Override
            protected void doGet(HttpServletRequest req, HttpServletResponse resp) {
                resp.getWriter().write("Hello from Tomcat!");
            }
        });
        ctx.addServletMappingDecoded("/*", "hello");
        
        tomcat.start();
        tomcat.getServer().await();
    }
}
```

## Performance Considerations

### Throughput Benchmarks

Netty consistently leads in raw throughput benchmarks due to its zero-copy buffer management and optimized event loop architecture. It can handle over 500,000 requests per second on modest hardware for simple workloads.

Undertow comes second, with its lightweight XNIO transport layer providing excellent performance for both blocking and non-blocking handlers. Its memory usage is typically the lowest among all four options, making it ideal for containerized deployments.

Jetty offers solid performance with its hybrid threading model. Recent versions (12.x) have significantly improved throughput with enhanced virtual thread support and optimized I/O handling.

Apache Tomcat, while historically thread-per-request, has embraced NIO connectors since version 8. Modern Tomcat with the NIO2 connector performs well for most workloads, though memory usage tends to be higher due to its broader feature set.

### Virtual Thread Support (Project Loom)

Java 21 introduced virtual threads, and all four servers have adapted:

- **Jetty 12** has first-class virtual thread support with `VirtualThreadPool`
- **Netty** can leverage virtual threads for blocking operations while keeping the event loop
- **Undertow** supports virtual thread executors via its XNIO worker configuration
- **Tomcat 10.1+** provides `VirtualThreadExecutor` for request processing

For I/O-bound workloads with high concurrency, enabling virtual threads can significantly reduce resource consumption across all four servers.

## Protocol Support Matrix

| Protocol | Jetty | Netty | Undertow | Tomcat |
|----------|-------|-------|----------|--------|
| HTTP/1.1 | Full | Full | Full | Full |
| HTTP/2 (h2c) | Yes | Yes | Yes | Yes |
| HTTP/2 (h2) | Yes | Yes | Yes | Yes |
| HTTP/3 (QUIC) | Yes (12+) | Via extension | No | No |
| WebSocket | Native | Native | Native | Native (JSR 356) |
| Server-Sent Events | Yes | Manual | Yes | Yes |
| gRPC | Via ALPN | Via library | Via ALPN | Via ALPN |

## Production Deployment with Docker

### Jetty Docker Compose

```yaml
version: "3.8"
services:
  jetty-app:
    image: jetty:12-jre21
    ports:
      - "8080:8080"
    volumes:
      - ./target/myapp.war:/var/lib/jetty/webapps/ROOT.war
    environment:
      - JAVA_OPTIONS=-Xmx512m -Xms256m
```

### Netty Dockerfile

```dockerfile
FROM eclipse-temurin:21-jre
COPY target/netty-app.jar /app/app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-Xmx512m", "-jar", "/app/app.jar"]
```

### Undertow Docker

```yaml
version: "3.8"
services:
  undertow-app:
    image: eclipse-temurin:21-jre
    ports:
      - "8080:8080"
    volumes:
      - ./target/undertow-app.jar:/app/app.jar
    command: ["java", "-Xmx256m", "-jar", "/app/app.jar"]
    environment:
      - UNDT_HOST=0.0.0.0
      - UNDT_PORT=8080
```

## Choosing the Right Server

### When to Choose Jetty

Jetty is the best choice when you need full Servlet API compliance in an embeddable package. It is the default embedded server in Spring Boot for traditional Servlet-based applications and has excellent documentation. Choose Jetty for:

- Servlet-based microservices
- Applications requiring HTTP/3 support
- Projects needing mature WebSocket support
- Environments where standards compliance matters

### When to Choose Netty

Netty excels in high-throughput, low-latency scenarios where you are willing to trade some simplicity for raw performance. It powers frameworks like gRPC, Apache Cassandra, and Elasticsearch internally. Choose Netty for:

- High-performance API gateways
- Custom protocol implementations
- Applications requiring maximum throughput
- Reactive applications using Spring WebFlux

### When to Choose Undertow

Undertow is ideal for resource-constrained environments where memory efficiency matters. It is the default server in WildFly (JBoss) and provides a clean, composable handler API. Choose Undertow for:

- Containerized microservices with tight memory limits
- Applications needing both blocking and non-blocking handlers
- Projects already using the WildFly ecosystem
- Lightweight REST APIs

### When to Choose Apache Tomcat

Tomcat is the veteran of the group with over 25 years of production use. Its Servlet container implementation is the reference implementation and most thoroughly debugged. Choose Tomcat for:

- Traditional enterprise Java applications
- Applications requiring maximum Servlet API compatibility
- Projects with existing Tomcat operational expertise
- Environments needing JMX-based monitoring out of the box

For broader server deployment strategies, see our [self-hosted web server guide](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/). If you are monitoring Java application performance, check our [Java APM tools comparison](../2026-06-04-self-hosted-java-apm-scouter-glowroot-kamon-guide/). For API contract testing with Spring-based services, see our [API contract management guide](../2026-05-19-self-hosted-api-contract-management-microcks-specmatic-spring-cloud-contract-guide/).

## FAQ

### Which embedded server does Spring Boot use by default?
Spring Boot uses Apache Tomcat by default for traditional (Servlet-based) applications. For reactive applications built with Spring WebFlux, it uses Reactor Netty as the default embedded server. You can easily switch to Jetty or Undertow by excluding the default starter and adding the respective Spring Boot starter dependency.

### Does Netty support the Servlet API?
Netty does not natively support the Servlet API. It provides its own channel-based abstraction layer. If you need Servlet support with Netty, you can use a bridge adapter like the `netty-servlet` module, but for most use cases, Jetty or Tomcat are better choices when Servlet compliance is required.

### What is the memory difference between these servers?
Undertow typically uses the least memory (4-6 MB baseline), followed by Netty (6-8 MB), Jetty (8-12 MB), and Tomcat (12-20 MB). However, actual memory usage depends heavily on your application code, the number of concurrent connections, and configured thread pools. For containerized deployments where every megabyte counts, Undertow and Netty have an advantage.

### Can I use HTTP/3 with any of these embedded servers?
As of 2026, Jetty 12.x provides the most mature HTTP/3 support among embedded Java servers. Netty can support HTTP/3 through the `netty-incubator-codec-quic` module, which wraps Cloudflare's quiche library. Undertow and Tomcat have not yet shipped HTTP/3 support in their stable releases.

### Which server is best for gRPC services?
Netty is the best choice for gRPC services. The official gRPC-Java library uses Netty as its default transport, providing first-class support for HTTP/2 trailers, streaming RPCs, and flow control. Both Jetty and Tomcat can serve gRPC through ALPN-based HTTP/2 negotiation, but Netty offers the most mature integration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Java Embedded HTTP Servers: Jetty vs Netty vs Undertow vs Apache Tomcat Comparison 2026",
  "description": "Comprehensive comparison of Java embedded HTTP servers: Jetty, Netty, Undertow, and Apache Tomcat. Includes code examples, performance benchmarks, Docker deployment, and selection guide.",
  "datePublished": "2026-07-04",
  "dateModified": "2026-07-04",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

