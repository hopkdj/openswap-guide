---
title: "Self-Hosted API Mocking Tools: WireMock vs Mockoon vs MockServer (2026)"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "api", "testing"]
draft: false
description: "Complete guide to self-hosted API mocking tools in 2026 — WireMock, Mockoon, and MockServer compared. Docker setup, configuration, and practical examples for testing APIs without external dependencies."
---

Building and testing applications often requires talking to external APIs — payment gateways, weather services, third-party data providers, or internal microservices that are not yet ready. Waiting for these services to be available slows down development. Relying on production APIs in tests makes your test suite flaky and unpredictable. The solution is API mocking: simulating API responses locally so your development and testing can proceed independently of external dependencies.

In this guide, we will explore the three most popular open-source, self-hosted API mocking tools available in 2026: **WireMock**, **Mockoon**, and **MockServer**. We will cover what each tool does, how to install and configure them, and how they compare so you can pick the right one for your workflow.

## Why Self-Host Your API Mocking Infrastructure

Before comparing tools, it is worth understanding why self-hosting API mocks matters.

**Eliminate external dependencies in tests.** When your tests hit real external APIs, they become slow, brittle, and dependent on network availability. A self-hosted mock server responds instantly and consistently every time, turning a five-second HTTP call into a two-millisecond local request.

**Test edge cases that are hard to reproduce.** How do you test what happens when a payment gateway returns a 503 error? Or when an API rate-limits you? Or when a response payload is malformed? With a mock server, you define these scenarios explicitly. No need to hope an external service misbehaves at the right moment.

**Develop against APIs that do not exist yet.** In microservice architectures, your service might need to call another team's API that is still in development. A mock server lets both teams agree on a contract and start building immediately, without waiting for each other.

**Avoid costs and rate limits.** Many APIs charge per request or impose strict rate limits. Running a mock server during development and testing means you only hit the real API when you absolutely need to — typically during integration tests or production deployment verification.

**Keep sensitive data local.** Mock servers can be configured with realistic but fake response data. No real customer data, API keys, or credentials ever leave your environment. This is especially valuable when developing against APIs that handle personal or financial information.

**Offline development.** A self-hosted mock server works on a laptop in an airplane, a development VM with no internet access, or an isolated CI/CD environment. Your development workflow should not depend on network connectivity.

## WireMock: The Industry Standard

WireMock is the most widely used API mocking tool in the Java and broader software development ecosystem. Created by Tom Akehurst and now maintained as an open-source project, it supports HTTP/HTTPS mocking, request matching, response templating, request recording, and fault simulation.

### Key Features

- **Request matching.** Match incoming requests by URL, method, headers, query parameters, body content (JSON, XML, plain text), and even custom matchers using regular expressions or JSONPath.
- **Response templating.** Use Handlebars templates to generate dynamic responses that adapt to the incoming request — different status codes based on headers, parameterized JSON bodies, or time-dependent responses.
- **Record and playback.** Point WireMock at a real API, let it record the interactions, and then replay them as stubs. This is the fastest way to create mocks for existing APIs.
- **Fault simulation.** Inject connection timeouts, malformed responses, random delays, and HTTP error codes to test your application's resilience.
- **Admin API.** Configure stubs programmatically via a REST API, making it easy to set up and tear down mock state in automated test suites.
- **Extensions.** A plugin system that lets you write custom request matchers, response transformers, and webhook simulators in Java.

### Installing WireMock

The fastest way to get WireMock running is via Docker:

```yaml
# docker-compose.yml
version: "3.8"

services:
  wiremock:
    image: wiremock/wiremock:3.5.4
    container_name: wiremock
    ports:
      - "8080:8080"
    volumes:
      - ./mappings:/home/wiremock/mappings
      - ./__files:/home/wiremock/__files
    command:
      - "--verbose"
      - "--global-response-templating"
      - "--root-dir=/home/wiremock"
```

Create a stub mapping file at `./mappings/get-users.json`:

```json
{
  "request": {
    "method": "GET",
    "urlPattern": "/api/v1/users/[0-9]+"
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "jsonBody": {
      "id": "{{request.path.[3]}}",
      "name": "John Doe",
      "email": "john@example.com",
      "role": "admin"
    },
    "transformers": ["response-template"]
  }
}
```

Start the server:

```bash
docker compose up -d
curl http://localhost:8080/api/v1/users/42
# Returns: {"id":"42","name":"John Doe","email":"john@example.com","role":"admin"}
```

### Creating a Fault Simulation Stub

One of WireMock's strengths is testing failure scenarios. Here is how you simulate a slow response followed by a timeout:

```json
{
  "request": {
    "method": "POST",
    "url": "/api/v1/payments"
  },
  "response": {
    "fixedDelayMilliseconds": 5000,
    "status": 504,
    "jsonBody": {
      "error": "Gateway Timeout",
      "message": "Payment provider did not respond in time"
    },
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

### Using WireMock in CI/CD

WireMock integrates naturally into CI pipelines. You can start it as a service container, load a set of predefined stubs, run your tests against it, and then shut it down. Here is a GitHub Actions example:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      wiremock:
        image: wiremock/wiremock:3.5.4
        ports:
          - 8080:8080
        volumes:
          - ./wiremock-mappings:/home/wiremock/mappings
        options: >-
          --health-cmd "curl -f http://localhost:8080/__admin/health"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        env:
          API_BASE_URL: http://localhost:8080
        run: |
          npm install
          npm test
```

## Mockoon: The Developer-Friendly GUI Tool

Mockoon takes a different approach. Instead of defining mocks through JSON configuration files, Mockoon provides a desktop application and a CLI tool with a visual interface. It is designed for developers who want to quickly prototype API responses without writing configuration files by hand.

### Key Features

- **Visual interface.** Create, edit, and manage mock endpoints through a graphical user interface. Click to add routes, define response bodies, set headers, and configure rules — no JSON files needed.
- **CLI for automation.** The `mockoon-cli` package lets you start, stop, and manage mock environments from the command line, making it suitable for CI/CD pipelines.
- **Route rules and templating.** Define conditions that determine which response to return based on request body, headers, or query parameters. Uses Handlebars templating for dynamic content.
- **Proxy mode.** Forward requests that do not match any stub to a real upstream API. This lets you mock only specific endpoints while letting others pass through to the real service.
- **Data generation.** Built-in Faker.js integration for generating realistic fake data — names, emails, addresses, dates, UUIDs, and more.
- **Environment sharing.** Export and import mock environments as JSON files that your team can share via version control.

### Installing Mockoon CLI

```bash
npm install -g @mockoon/cli
```

Create a mock environment file called `api-mock.json`:

```json
{
  "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "E-commerce API",
  "port": 3000,
  "routes": [
    {
      "uuid": "route-001",
      "method": "get",
      "endpoint": "products",
      "responses": [
        {
          "uuid": "resp-001",
          "body": "[{{# repeat (faker 'number.int' 3 10) }}{\n  \"id\": {{ faker 'number.int' 1 1000 }},\n  \"name\": \"{{ faker 'commerce.productName' }}\",\n  \"price\": {{ faker 'commerce.price' }},\n  \"inStock\": {{ faker 'datatype.boolean' }}\n}{{#unless @last}},{{/unless}}{{/ repeat }}]",
          "latency": 0,
          "statusCode": 200,
          "headers": [
            { "key": "Content-Type", "value": "application/json" }
          ]
        }
      ]
    },
    {
      "uuid": "route-002",
      "method": "post",
      "endpoint": "orders",
      "responses": [
        {
          "uuid": "resp-002",
          "body": "{\n  \"orderId\": \"{{ faker 'string.uuid' }}\",\n  \"status\": \"confirmed\",\n  \"estimatedDelivery\": \"{{ faker 'date.future' }}\"\n}",
          "statusCode": 201,
          "headers": [
            { "key": "Content-Type", "value": "application/json" }
          ]
        }
      ]
    }
  ],
  "proxyMode": false
}
```

Start the mock server:

```bash
mockoon-cli start --data ./api-mock.json
curl http://localhost:3000/products
# Returns an array of 3-10 randomly generated products with fake names and prices
```

### Running Mockoon in Docker

While Mockoon is primarily a desktop tool, the CLI can run in a container:

```dockerfile
FROM node:20-alpine
RUN npm install -g @mockoon/cli
COPY api-mock.json /app/api-mock.json
EXPOSE 3000
CMD ["mockoon-cli", "start", "--data", "/app/api-mock.json", "--port", "3000"]
```

```bash
docker build -t my-api-mock .
docker run -p 3000:3000 my-api-mock
```

## MockServer: The Powerful Contract Testing Tool

MockServer (not to be confused with the `mock-server` npm package) is a Java-based tool that focuses on contract testing and complex request matching. It is particularly popular in enterprise environments where API contracts between services need to be strictly enforced.

### Key Features

- **Expectation-based model.** Instead of defining static stubs, you set "expectations" — rules that describe what requests to expect and what responses to return. The server tracks which expectations were matched and which were not, making it easy to verify that your application made the correct API calls.
- **Verification.** After running your tests, you can query MockServer to confirm that specific requests were made with the correct method, path, headers, and body. This is invaluable for contract testing.
- **Request matching engine.** Supports regex matching, JSON schema validation, XPath matching, and forward chaining — the ability to chain multiple responses for a single request.
- **Port forwarding.** Forward specific requests to a real upstream server while mocking others. This is useful for incremental migration from real APIs to mocks.
- **OpenAPI integration.** Generate expectations directly from an OpenAPI (Swagger) specification. If you have an API spec, MockServer can auto-generate a full mock server from it.
- **Java, JavaScript, and REST clients.** Configure expectations programmatically from your test code using the MockServer client library, or via the REST API.

### Installing MockServer

```yaml
# docker-compose.yml
version: "3.8"

services:
  mockserver:
    image: mockserver/mockserver:5.15.0
    container_name: mockserver
    ports:
      - "1080:1080"
    environment:
      MOCKSERVER_WATCH_INITIALIZATION_JSON: "true"
      MOCKSERVER_PROPERTY_FILE: /config/mockserver.properties
      MOCKSERVER_INITIALIZATION_JSON_PATH: /config/expectations.json
    volumes:
      - ./config:/config
```

Create an expectations file at `./config/expectations.json`:

```json
[
  {
    "httpRequest": {
      "method": "GET",
      "path": "/api/v1/users/.*",
      "pathParameters": {
        "id": ["[0-9]+"]
      }
    },
    "httpResponse": {
      "statusCode": 200,
      "headers": {
        "Content-Type": ["application/json"]
      },
      "body": "{\"id\": ${json.path.request.path}, \"name\": \"Jane Smith\", \"email\": \"jane@example.com\", \"createdAt\": \"2026-01-15T08:30:00Z\"}"
    }
  },
  {
    "httpRequest": {
      "method": "POST",
      "path": "/api/v1/users",
      "body": {
        "type": "JSON",
        "matchType": "STRICT",
        "json": "{\"name\": \".*\", \"email\": \".*@.*\"}"
      }
    },
    "httpResponse": {
      "statusCode": 201,
      "headers": {
        "Content-Type": ["application/json"],
        "Location": ["/api/v1/users/12345"]
      },
      "body": "{\"id\": 12345, \"status\": \"created\"}"
    }
  }
]
```

Start and test:

```bash
docker compose up -d

# Test GET
curl http://localhost:1080/api/v1/users/99
# Returns: {"id": 99, "name": "Jane Smith", ...}

# Verify requests were made
curl http://localhost:1080/mockserver/retrieve?type=REQUESTS
```

### Using MockServer for Contract Testing

The real power of MockServer shines in contract testing. Instead of just mocking responses, you verify that your application sends the right requests:

```bash
# After running your test suite, check what requests were received
curl -s http://localhost:1080/mockserver/retrieve?type=REQUESTS | python -m json.tool

# Verify specific expectations were matched
curl -s http://localhost:1080/mockserver/retrieve?type=REQUEST_MATCHING_EXPECTATIONS
```

This lets you confirm that your application:
- Called the correct endpoint
- Used the right HTTP method
- Sent the expected headers (authentication, content type)
- Included the correct request body structure

## Comparison: WireMock vs Mockoon vs MockServer

| Feature | WireMock | Mockoon | MockServer |
|---------|----------|---------|------------|
| **Primary interface** | JSON files + REST API | Desktop GUI + CLI | JSON/Java client + REST API |
| **Learning curve** | Moderate | Low | Steep |
| **Request matching** | URL, headers, body, regex, JSONPath | URL, headers, body, query params | URL, headers, body, regex, JSON schema, XPath |
| **Response templating** | Handlebars | Handlebars + Faker.js | Velocity templates |
| **Dynamic data generation** | Via custom extensions | Built-in Faker.js | Via templates |
| **Record and playback** | Yes | No | No |
| **Fault injection** | Delays, timeouts, resets, malformed responses | Delays | Delays, connection resets |
| **Contract testing / verification** | Via verification API | No | Built-in expectation verification |
| **OpenAPI / Swagger import** | Via community tools | Via third-party converters | Built-in |
| **Docker support** | Official image | Community (CLI-based) | Official image |
| **CI/CD friendliness** | Excellent | Good (via CLI) | Excellent |
| **Multi-port support** | Yes (multiple instances) | Yes (multiple environments) | Yes (multiple ports per instance) |
| **HTTPS support** | Yes (built-in CA) | No (use reverse proxy) | Yes (built-in) |
| **Language** | Java | Node.js | Java |
| **License** | Apache 2.0 | MIT | Apache 2.0 |
| **Best for** | General-purpose API mocking | Quick prototyping and developer experience | Enterprise contract testing |

## Choosing the Right Tool

Your choice depends on your specific needs and team workflow:

**Choose WireMock if** you need a battle-tested, feature-rich mocking tool that works well in CI/CD pipelines. Its record-and-playback capability makes it the fastest option for mocking existing APIs. The large ecosystem of extensions and the strong community support make it the safest long-term bet. It is the default choice for Java-based projects and works well with any language through its REST API.

**Choose Mockoon if** you value developer experience and want to prototype APIs quickly without writing configuration files. The visual interface is a significant advantage for teams that include non-technical stakeholders who need to understand or modify mock responses. The built-in fake data generation means your mock responses look realistic out of the box. It is ideal for frontend developers who need a quick backend to test against.

**Choose MockServer if** you need contract testing and want to verify that your application makes the correct API calls. The expectation verification system is unique among the three tools and is particularly valuable in microservice architectures where multiple teams need to agree on API contracts. The OpenAPI integration lets you generate a full mock server from your API specification in minutes.

## Production Deployment Considerations

When deploying a mock server for shared team use or CI/CD, keep these points in mind:

**Resource allocation.** Mock servers are lightweight. WireMock and MockServer each need about 256-512 MB of RAM. Mockoon CLI needs around 128 MB. A small VPS or container with 1 GB of RAM can easily run multiple mock instances.

**Persistence.** Store your stub and expectation definitions in version control. This makes them reviewable, shareable, and recoverable. Use the Docker volume mount pattern shown above to keep configuration outside the container.

**Authentication.** If your mock server is accessible over a network, protect it. Use a reverse proxy (Nginx, Caddy, or Traefik) with basic auth or token-based authentication. The mock server itself typically has no built-in auth.

**Monitoring.** Log all requests that hit your mock server. This helps you understand which endpoints are being used, identify mismatches between your mocks and the real API, and debug test failures. WireMock and MockServer both have built-in request logging accessible via their admin APIs.

**Stale mocks.** As the real API evolves, your mocks can become outdated. Set up a periodic review process to compare mock responses against the real API. WireMock's record mode is useful here — temporarily switch to recording mode, capture a few real responses, and compare them to your existing stubs.

## Conclusion

Self-hosted API mocking is one of the highest-return infrastructure investments a development team can make. It eliminates external dependencies from tests, enables offline development, and lets you test edge cases that would be impossible or expensive to reproduce against real services. WireMock, Mockoon, and MockServer each bring different strengths to the table, and any one of them will dramatically improve your development workflow compared to testing against live APIs. Start with a simple Docker setup, mock the most critical endpoints first, and expand your coverage as your confidence in the tool grows.
