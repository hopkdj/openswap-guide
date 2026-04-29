---
title: "Hoverfly vs Mountebank vs Microcks: Self-Hosted Service Virtualization Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "testing", "api", "devops"]
draft: false
description: "Compare Hoverfly, Mountebank, and Microcks for self-hosted service virtualization. Complete guide with Docker Compose configs, API mocking strategies, and deployment instructions."
---

When building and testing distributed systems, one of the hardest problems is managing dependencies on services that aren't always available. Third-party APIs might have rate limits, staging environments could be down, and downstream microservices may not be ready yet. Service virtualization solves this by replacing real dependencies with controllable test doubles that simulate their behavior.

The dominant SaaS solutions for API mocking and service virtualization come with significant tradeoffs: vendor lock-in, data leaving your infrastructure, response limits on free tiers, and recurring subscription costs that scale unpredictably. Self-hosted alternatives give you full control over every mock response, every recording session, and every test scenario.

This guide compares three leading open-source service virtualization platforms — Hoverfly, Mountebank, and Microcks — with hands-on Docker deployment instructions and a detailed feature comparison.

## Why Self-Host Service Virtualization

**Unlimited mocking without paywalls.** SaaS API mocking tools charge per mock, per request, or per user. Self-hosted platforms have no artificial limits — create thousands of mock endpoints and run millions of test requests without additional cost.

**Record real traffic safely.** Tools like Hoverfly can capture live HTTP traffic and replay it as mock responses. When self-hosted, this traffic never leaves your network, keeping sensitive API payloads, authentication tokens, and internal URLs under your control.

**Team-wide mock consistency.** Instead of each developer maintaining their own local mock scripts, a self-hosted service virtualization server provides a single source of truth. Every team member — and every CI pipeline — hits the same mocks with the same behavior.

**Protocol support beyond HTTP.** Modern service virtualization platforms handle gRPC, GraphQL, WebSocket, and async protocols like Kafka and NATS. Open-source tools are often faster to adopt new protocols than commercial vendors.

**CI/CD pipeline integration.** Self-hosted mocking servers integrate directly into your CI pipelines without requiring external SaaS credentials, API keys, or network egress to third-party endpoints.

## Hoverfly: Lightweight Go-Based Service Virtualization

[Hoverfly](https://github.com/SpectoLabs/hoverfly) is a lightweight, Go-based service virtualization tool designed for developers and testers. It operates as a proxy that can record, simulate, and modify HTTP traffic in real time. With 2,485+ GitHub stars and active development (latest commit April 2026), Hoverfly is one of the most mature open-source options in this space.

Hoverfly works in two primary modes: **simulate** (serving pre-configured mock responses) and **capture** (recording real traffic to build a simulation from live API calls). Its middleware system allows you to transform requests and responses using Python, Java, or WebAssembly extensions.

### Hoverfly Docker Compose Deployment

Hoverfly exposes two ports: `8500` for the admin API and `8888` as the proxy port. Here is a minimal Docker Compose setup:

```yaml
services:
  hoverfly:
    image: spectolabs/hoverfly:latest
    container_name: hoverfly
    ports:
      - "8500:8500"   # Admin API
      - "8888:8888"   # Proxy port
    command: ["-listen-on-host=0.0.0.0", "-webserver", "-port=8500"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8500/api/v2/hoverfly"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Start the container and switch Hoverfly to capture mode:

```bash
docker compose up -d

# Put Hoverfly in capture mode
curl -X PUT http://localhost:8500/api/v2/hoverfly-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "capture"}'

# Make requests through the proxy — they will be recorded
curl -x http://localhost:8888 https://jsonplaceholder.typicode.com/posts/1

# Switch to simulate mode to replay recorded responses
curl -X PUT http://localhost:8500/api/v2/hoverfly-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulate"}'

# The same request now returns the cached mock
curl -x http://localhost:8888 https://jsonplaceholder.typicode.com/posts/1
```

You can also create simulations manually using Hoverfly's JSON simulation format:

```bash
curl -X PUT http://localhost:8500/api/v2/simulation \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "pairs": [
        {
          "request": {
            "method": "GET",
            "destination": "api.example.com",
            "path": "/users/1",
            "query": {}
          },
          "response": {
            "status": 200,
            "body": "{\"id\": 1, \"name\": \"Test User\"}",
            "encodedBody": false,
            "headers": {"Content-Type": ["application/json"]}
          }
        }
      ]
    }
  }'
```

Hoverfly also supports **delay simulation** to mimic slow APIs and **stateful scenarios** for testing multi-step workflows where response behavior depends on previous requests.

## Mountebank: Multi-Protocol Service Virtualization

[Mountebank](https://github.com/bbyars/mountebank) takes a different approach. Rather than operating as a proxy, Mountebank runs as a server where you define "imposters" — test doubles that respond on configurable ports. With 2,092+ GitHub stars and a JavaScript/Node.js codebase, Mountebank excels at protocol flexibility.

Mountebank supports HTTP/HTTPS, TCP, SMTP, and gRPC imposters out of the box. Its JavaScript predicate system allows you to match requests based on complex conditions — headers, query parameters, request bodies, and even XPath selectors on XML payloads.

### Mountebank Docker Compose Deployment

Mountebank runs on a single port (default `2525` for the API) and creates additional ports for each imposter you configure:

```yaml
services:
  mountebank:
    image: bbyars/mountebank:latest
    container_name: mountebank
    ports:
      - "2525:2525"   # Mountebank API
      - "4545-4555:4545-4555"  # Imposter ports range
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:2525/imposters"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Create an HTTP imposter via the Mountebank API:

```bash
docker compose up -d

# Create a simple HTTP imposter on port 4545
curl -X POST http://localhost:2525/imposters \
  -H "Content-Type: application/json" \
  -d '{
    "port": 4545,
    "protocol": "http",
    "stubs": [
      {
        "responses": [
          {
            "is": {
              "statusCode": 200,
              "headers": { "Content-Type": "application/json" },
              "body": "{\"status\": \"ok\", \"version\": \"1.0\"}"
            }
          }
        ]
      }
    ]
  }'

# Test the imposter
curl http://localhost:4545/test
# Returns: {"status": "ok", "version": "1.0"}
```

Mountebank supports **response injection** using JavaScript functions, enabling you to generate dynamic mock responses based on request data:

```json
{
  "port": 4546,
  "protocol": "http",
  "stubs": [
    {
      "responses": [
        {
          "inject": "function(config, logger) { return { statusCode: 200, body: JSON.stringify({ path: config.path, timestamp: new Date().toISOString() }) }; }"
        }
      ]
    }
  ]
}
```

This makes Mountebank particularly useful for testing edge cases — you can program imposters to return error codes, timeouts, or malformed responses on demand.

## Microcks: Cloud-Native API Mocking and Testing

[Microcks](https://github.com/microcks/microcks) is the most feature-rich option in this comparison. As a CNCF Sandbox project with 1,873+ GitHub stars, Microcks provides a full web UI for API mocking, contract testing, and schema validation. It supports OpenAPI/Swagger, AsyncAPI, GraphQL, gRPC, and Postman collections.

Unlike Hoverfly and Mountebank which are primarily developer tools, Microcks is designed as a platform. It imports API definitions (OpenAPI specs, AsyncAPI docs) and automatically generates mock servers with realistic responses based on your API schemas. It also performs contract testing by replaying Postman collections against your running services.

### Microcks Docker Compose Deployment

Microcks requires MongoDB for persistence and Keycloak for authentication. The official compose file sets up all four services:

```yaml
services:
  mongo:
    image: mongo:4.4.29
    container_name: microcks-db
    volumes:
      - microcks-data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 5s
      retries: 3

  keycloak:
    image: quay.io/keycloak/keycloak:26.0.0
    container_name: microcks-sso
    ports:
      - "18080:8080"
    environment:
      KEYCLOAK_ADMIN: "admin"
      KEYCLOAK_ADMIN_PASSWORD: "admin"
    command: ["start-dev", "--import-realm", "--health-enabled=true"]
    healthcheck:
      test: ["CMD-SHELL", "exec 3<>/dev/tcp/localhost/8080; echo -e 'GET /health/live HTTP/1.1\r\nHost: localhost\r\n\r\n' >&3; timeout 2 cat <&3 | grep -q 200"]
      interval: 15s
      timeout: 5s
      retries: 5

  postman-runtime:
    image: quay.io/microcks/microcks-postman-runtime:0.7.1
    container_name: microcks-postman-runtime
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 20s
      timeout: 5s
      retries: 3

  microcks:
    image: quay.io/microcks/microcks:latest
    container_name: microcks-app
    depends_on:
      mongo:
        condition: service_healthy
      keycloak:
        condition: service_healthy
      postman-runtime:
        condition: service_healthy
    ports:
      - "8080:8080"
      - "9090:9090"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - SPRING_DATA_MONGODB_URI=mongodb://mongo:27017
      - KEYCLOAK_URL=http://keycloak:8080
      - MICROCKS_URL=http://microcks:8080
    restart: unless-stopped

volumes:
  microcks-data:
```

Once running, access the Microcks web UI at `http://localhost:8080` and import your OpenAPI specification. Microcks automatically generates a mock endpoint with sample responses derived from your schema examples.

For teams already using Microcks, you can also import artifacts via the CLI:

```bash
# Import an OpenAPI spec
curl -X POST "http://localhost:8080/api/resources" \
  -F "artifact=@./my-openapi-spec.yaml" \
  -F "mainArtifact=true"

# Import a Postman collection for contract testing
curl -X POST "http://localhost:8080/api/resources" \
  -F "artifact=@./my-postman-collection.json"
```

## Feature Comparison

| Feature | Hoverfly | Mountebank | Microcks |
|---------|----------|------------|----------|
| **Language** | Go | JavaScript (Node.js) | Java (Spring Boot) |
| **GitHub Stars** | 2,485 | 2,092 | 1,873 |
| **Primary Use** | Proxy-based recording & simulation | Multi-protocol imposter server | API mock & contract testing platform |
| **HTTP Mocking** | Yes | Yes | Yes |
| **gRPC Mocking** | Yes | Yes | Yes |
| **GraphQL Mocking** | Yes | Via TCP imposter | Yes |
| **Async Protocols** | No | No | Yes (Kafka, NATS, AMQP) |
| **Traffic Recording** | Yes (capture mode) | No | No |
| **Web UI** | Basic admin panel | No | Full web dashboard |
| **OpenAPI Import** | Via middleware | No | Native |
| **AsyncAPI Support** | No | No | Yes |
| **Postman Integration** | No | No | Yes (contract testing) |
| **Middleware/Extensions** | Python, Java, WASM | JavaScript injection | Java extensions |
| **Stateful Scenarios** | Yes | Yes (via JS) | Yes |
| **Docker Image** | `spectolabs/hoverfly` | `bbyars/mountebank` | `quay.io/microcks/microcks` |
| **Dependencies** | None (single binary) | None (single process) | MongoDB + Keycloak |
| **Resource Footprint** | ~20 MB RAM | ~50 MB RAM | ~500+ MB RAM |
| **License** | Apache 2.0 | MIT | Apache 2.0 |
| **CNCF Status** | No | No | Sandbox Project |

## How to Choose

**Choose Hoverfly if** you need a lightweight, proxy-based solution with traffic recording capabilities. It is ideal for teams that want to capture real API traffic from staging or production and replay it as mocks during testing. Its Go-based architecture means minimal resource usage — a single container with no external dependencies.

**Choose Mountebank if** you need multi-protocol support beyond HTTP and want fine-grained control over mock behavior through JavaScript injection. Mountebank excels at testing edge cases — program your imposters to return specific error codes, introduce randomized delays, or match requests using complex XPath and JSON path predicates. It is the best choice for teams that mock TCP services, SMTP servers, or custom protocols alongside HTTP APIs.

**Choose Microcks if** you need a full-featured API mock management platform with a web UI, OpenAPI-native mocking, and async protocol support. Microcks is the right fit for organizations that already maintain OpenAPI specifications, use Postman for testing, or need to mock Kafka/NATS event streams. The tradeoff is higher resource requirements — Microcks needs MongoDB and Keycloak as dependencies, making it heavier than Hoverfly or Mountebank.

For a complete CI/CD testing strategy, consider combining these tools. Use Hoverfly for recording and replaying HTTP traffic, Mountebank for custom protocol imposters, and Microcks for OpenAPI-driven mock servers and contract validation. Pairing service virtualization with [contract testing tools like Pact](../pact-vs-specmatic-vs-spring-cloud-contract-self-hosted-contract-testing-guide-2026/) ensures your mocks stay in sync with real API behavior. For fault injection and resilience testing, tools like [Toxiproxy or Chaos Monkey](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/) complement service virtualization by injecting network failures into your mock responses. And if you are already using [API mocking tools like WireMock or Mockoon](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/), the tools covered here provide complementary capabilities — particularly around traffic recording (Hoverfly), multi-protocol imposters (Mountebank), and async event mocking (Microcks).

## FAQ

### What is service virtualization and how does it differ from API mocking?

Service virtualization is a broader concept than API mocking. While API mocking focuses on simulating individual API endpoints with predefined responses, service virtualization simulates entire service behaviors including stateful workflows, protocol-specific interactions (gRPC, Kafka), and complex request-response patterns. Tools like Microcks and Mountebank support full service virtualization, while simpler mock servers only handle basic HTTP endpoint stubs.

### Can Hoverfly record traffic from production environments safely?

Yes, Hoverfly's capture mode can record live HTTP traffic through its proxy. When deployed within your infrastructure, all captured data stays on your servers. You can filter which destinations to capture, strip sensitive headers (like Authorization tokens), and export simulations as JSON files for version control. Always review captured simulations before committing them to ensure no sensitive data is included.

### Does Mountebank support HTTPS imposters?

Yes, Mountebank can create HTTPS imposters. When creating an imposter, set `"protocol": "https"` and Mountebank will generate a self-signed certificate automatically. For production use, you can provide your own TLS certificates through the `cert` and `key` configuration options in the imposter definition.

### Can Microcks mock async protocols like Kafka and NATS?

Yes, Microcks supports async protocol mocking through its AsyncAPI integration. You can import AsyncAPI specifications and Microcks will publish mock messages to your Kafka or NATS brokers. The official Docker Compose setup includes optional addon files (`kafdrop-addon.yml`, `nats-addon.yml`) that configure the necessary broker connections.

### How do I integrate Hoverfly or Mountebank into a CI pipeline?

Both tools can be started as Docker containers in your CI pipeline. For GitLab CI, GitHub Actions, or Jenkins:

```yaml
# GitHub Actions example with Hoverfly
services:
  hoverfly:
    image: spectolabs/hoverfly:latest
    ports:
      - 8500:8500
      - 8888:8888
    options: >-
      --health-cmd "wget --spider -q http://localhost:8500/api/v2/hoverfly"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 3

steps:
  - name: Load simulation
    run: curl -X PUT http://localhost:8500/api/v2/simulation -d @simulation.json
  - name: Run tests
    run: ./run-tests.sh --proxy http://localhost:8888
```

### Which tool has the lowest resource footprint?

Hoverfly has the smallest footprint — it is a single Go binary with no external dependencies, typically using under 20 MB of RAM. Mountebank (Node.js) uses around 50 MB. Microcks requires the most resources due to its MongoDB and Keycloak dependencies, needing 500+ MB of RAM for the full stack.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hoverfly vs Mountebank vs Microcks: Self-Hosted Service Virtualization Guide 2026",
  "description": "Compare Hoverfly, Mountebank, and Microcks for self-hosted service virtualization. Complete guide with Docker Compose configs, API mocking strategies, and deployment instructions.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
