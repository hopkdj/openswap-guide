---
title: "Pact vs Specmatic vs Spring Cloud Contract: Self-Hosted Contract Testing Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "testing", "api", "contract-testing", "microservices"]
draft: false
description: "Compare Pact, Specmatic, and Spring Cloud Contract for self-hosted contract testing. Learn consumer-driven contract testing with Docker setups, CI/CD integration, and best practices for microservices."
---

Microservices architectures introduce a fundamental challenge: how do you verify that services communicate correctly without running expensive, slow integration tests against every dependent system? Contract testing solves this problem by defining and validating the "contract" between a consumer and a provider independently, allowing teams to test in isolation while catching breaking changes before they reach production.

This guide compares the three leading open-source contract testing tools — **Pact**, **Specmatic**, and **Spring Cloud Contract** — with practical deployment instructions, real project data, and self-hosting configurations.

## Why Contract Testing Matters in Microservices

In a traditional monolith, internal function calls are verified by unit tests. When you split into microservices, those function calls become network requests. Testing these across service boundaries requires either:

- **End-to-end integration tests** — fragile, slow, and require all services running simultaneously
- **Mock servers** — easy to write but drift from the real API as services evolve
- **Contract testing** — formally defines the API contract, generates mocks from the contract, and verifies both consumer expectations and provider compliance automatically

Contract testing gives you the safety of integration tests with the speed of unit tests. Each service can be verified independently against a shared contract, and a broker (a centralized server) tracks which versions of each service are compatible.

## What Is Consumer-Driven Contract Testing?

Consumer-driven contract testing (CDC) flips the traditional API testing model. Instead of the provider defining the API and consumers adapting to it, the **consumer** declares what data it needs, and the **provider** must satisfy those expectations.

The workflow has three steps:

1. **Consumer writes a contract test** — declares the expected request/response shape
2. **Contract is published to a broker** — a central server stores the pact/contract file
3. **Provider verifies against the contract** — the provider runs its own test suite, replaying each consumer's requests and verifying responses match

This approach catches breaking changes early. If a provider removes a field a consumer depends on, the contract verification fails in CI before the change is deployed.

## Tool Comparison at a Glasp

| Feature | Pact | Specmatic | Spring Cloud Contract |
|---------|------|-----------|----------------------|
| **Primary Language** | Ruby (multi-language DSL) | Kotlin/Java | Java |
| **GitHub Stars** | 2,193 | 369 | 730 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Latest Release** | v2.119.0 (Broker) | 2.43.3 | v4.3.3 |
| **Broker Included** | Yes (Pact Broker) | No (requires external) | No (stub runner only) |
| **OpenAPI Support** | Via plugin | Native | Via plugin |
| **Async Messaging** | Yes ([kafka](https://kafka.apache.org/), RabbitMQ) | Yes | Limited |
| **Self-Hosted** | Full support | [docker](https://www.docker.com/) available | Docker + stub runner |
| **CI/CD Integration** | Excellent | Good | Good (Maven/Gradle) |
| **Best For** | Polyglot teams, mature CDC | API-first, spec-driven | Spring ecosystem teams |

## Pact: The Industry Standard

Pact is the most widely adopted contract testing framework. It supports multiple languages (Ruby, JavaScript, Python, Go, Java, .NET) through the Pact Specification, which defines the contract format. The **Pact Broker** is a companion tool that stores, versions, and visualizes contracts between services.

### When to Choose Pact

- Your team uses multiple programming languages and needs a unified contract format
- You want a full-featured broker with compatibility matrices, webhook notifications, and deployment tracking
- You need async message contract testing (Kafka, RabbitMQ)
- Your organization is mature enough to adopt consumer-driven testing at scale

### Self-Hosting Pact Broker with Docker Compose

The Pact Broker requires a PostgreSQL database. Here's the official production-ready Docker Compose configuration:

```yaml
version: "3"

services:
  postgres:
    image: postgres:17
    healthcheck:
      test: psql postgres --command "select 1" -U postgres
    volumes:
      - postgres-volume:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: postgres

  pact-broker:
    image: "pactfoundation/pact-broker:2.137.0-pactbroker2.118.0"
    ports:
      - "9292:9292"
    depends_on:
      - postgres
    environment:
      PACT_BROKER_PORT: '9292'
      PACT_BROKER_DATABASE_URL: "postgres://postgres:password@postgres/postgres"
      PACT_BROKER_LOG_LEVEL: INFO
      PACT_BROKER_DATABASE_CONNECT_MAX_RETRIES: "5"
      PACT_BROKER_BASE_URL: 'http://localhost:9292'

volumes:
  postgres-volume:
```

Start the broker:

```bash
docker-compose up -d
```

Access the Pact Broker UI at `http://localhost:9292`. From here, you can see all consumer-provider relationships, compatibility status, and deployment readiness via the `can-i-deploy` check.

### Publishing and Verifying with Pact CLI

Install the Pact CLI:

```bash
# Using Docker (recommended)
docker pull pactfoundation/pact-cli

# Verify a provider against all consumer contracts
docker run --rm \
  -e PACT_BROKER_BASE_URL=http://localhost:9292 \
  pactfoundation/pact-cli \
  broker can-i-deploy \
  --pacticipant "OrderService" \
  --latest
```

In your consumer project, publish pacts after tests pass:

```bash
pact-broker publish ./pacts \
  --branch main \
  --consumer-app-version "1.0.0" \
  --broker-base-url http://localhost:9292
```

## Specmatic: API-Spec-Driven Contract Testing

Specmatic takes a different approach. Instead of writing tests in a DSL, you define your API using **OpenAPI specifications** and Specmatic automatically generates contract tests from the spec. It also generates mock servers that conform to the spec, eliminating the need to write manual mocks.

### When to Choose Specmatic

- Your team follows an API-first design process with OpenAPI specs
- You want to eliminate manual mock writing — specs become executable contracts automatically
- You need to verify API compliance against a specification, not just pairwise consumer/provider pacts
- Your team prefers a specification-driven over a test-driven approach

### Running Specmatic via Docker

Specmatic is available on Docker Hub with over 41,000 pulls. Since it's a Java/Kotlin application, you run it as a standalone process:

```bash
docker pull znsio/specmatic:latest

# Verify API spec against a running service
docker run --rm \
  -v $(pwd)/specs:/specs \
  znsio/specmatic:latest \
  test /specs/api-spec.yaml --host=http://localhost:8080
```

### Using Specmatic as a Mock Server

One of Specmatic's strongest features is its ability to spin up a mock server from your OpenAPI spec:

```bash
# Start mock server from OpenAPI spec
docker run --rm \
  -v $(pwd)/specs:/specs \
  -p 9000:9000 \
  znsio/specmatic:latest \
  stub /specs/api-spec.yaml --port 9000
```

Your consumer team can now test against the mock without waiting for the provider to be ready. The mock validates that all requests and responses conform to the spec, catching contract violations during development rather than at integration time.

### Specmatic Contract Verification

Specmatic can verify both consumers and providers against the same spec:

```yaml
# specmatic.yaml
sources:
  - provider: http://provider-service:8080/api
    test:
      - /specs/payment-api.yaml
    stub:
      - /specs/payment-api.yaml
```

Run verification:

```bash
specmatic test specmatic.yaml
```

This single command verifies that the provider at `http://provider-service:8080` conforms to the OpenAPI spec and that consumer expectations encoded in the spec are satisfied.

## Spring Cloud Contract: The Spring Ecosystem Choice

Spring Cloud Contract is the contract testing solution built into the Spring Cloud ecosystem. It integrates seamlessly with Spring Boot, Spring Cloud Gateway, and the broader Spring toolchain. It uses a Groovy DSL or YAML for contract definitions and includes a **Stub Runner** that provides mock servers for consumers.

### When to Choose Spring Cloud Contract

- Your entire stack is Spring Boot / Spring Cloud
- You want tight integration with Spring's testing framework (RestAssured, WebTestClient)
- You prefer Gradle/Maven plugins over standalone broker servers
- Your team values convention over configuration for contract definitions

### Setting Up the Stub Runner

Spring Cloud Contract uses a stub runner instead of a broker. The stub runner downloads contract stubs from Maven repositories or a shared location and serves them as mock servers:

```xml
<!-- pom.xml: Add Spring Cloud Contract dependency -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-contract-stub-runner</artifactId>
    <version>4.3.3</version>
    <scope>test</scope>
</dependency>
```

Configure the stub runner in your consumer tests:

```java
@AutoConfigureStubRunner(
    ids = "com.example:provider-service:+:stubs:8090",
    stubsMode = StubRunnerProperties.StubsMode.LOCAL
)
@SpringBootTest
class ConsumerContractTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void shouldGetUserById() {
        ResponseEntity<String> response = restTemplate
            .getForEntity("http://localhost:8090/users/1", String.class);
        assertThat(response.getStatusCodeValue()).isEqualTo(200);
        assertThat(response.getBody()).contains("username");
    }
}
```

### Writing Provider Contracts

On the provider side, define contracts in Groovy DSL:

```groovy
// src/test/resources/contracts/getUser.groovy
org.springframework.cloud.contract.spec.Contract.make {
    request {
        method 'GET'
        url '/users/1'
    }
    response {
        status 200
        body('''
        {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com"
        }
        ''')
        headers {
            contentType(applicationJson())
        }
    }
}
```

Generate and install stubs:

```bash
# Generate stubs and run provider verification tests
./mvnw clean install spring-cloud-contract:generateStubs
```

### Docker-Based Stub Runner

For self-hosted continuous verification, you can containerize the stub runner:

```dockerfile
FROM eclipse-temurin:17-jre
COPY target/provider-service-stubs.jar /app/stubs.jar
EXPOSE 8090
ENTRYPOINT ["java", "-jar", "/app/stubs.jar", \
    "--stubrunner.ids=com.example:provider-service", \
    "--stubrunner.stubs-mode=remote", \
    "--stubrunner.repositoryRoot=https://repo.example.com/maven"]
```

## Integration with CI/CD Pipelines

All three tools integrate with CI/CD, but the patterns differ.

### Pact in CI/CD

```yaml
# GitHub Actions example
name: Contract Tests
on: [push, pull_request]
jobs:
  verify-provider:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - name: Run provider verification
        run: |
          npm run test:provider
        env:
          PACT_BROKER_BASE_URL: http://localhost:9292
      - name: Can I deploy?
        run: |
          npx pact-broker can-i-deploy \
            --pacticipant OrderService \
            --latest \
            --broker-base-url $PACT_BROKER_BASE_URL
```

### Specmatic in CI/CD

```yaml
- name: Verify API against spec
  run: |
    docker run --rm \
      -v $(pwd)/api-specs:/specs \
      znsio/specmatic:latest \
      test /specs/openapi.yaml \
      --host=http://localhost:8080
```

### Spring Cloud Contract in CI/CD

```yaml
- name: Generate and publish stubs
  run: |
    ./mvnw clean deploy -DskipTests \
      -pl :provider-service-stubs
- name: Run stub runner tests
  run: |
    ./mvnw verify \
      -Dstubrunner.repositoryRoot=https://repo.example.com/maven
```

For more on self-hosted CI/CD runners that can execute these contract tests, see our [Wo[gitea](https://gitea.io/)ker CI vs Drone CI vs Gitea Actions comparison](../woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/).

## Choosing the Right Tool

**Choose Pact if:**
- You have a polyglot microservices architecture
- You need a centralized broker with compatibility tracking
- You want the most mature and well-documented contract testing solution
- Your team includes non-Java developers

**Choose Specmatic if:**
- You follow an API-first design workflow with OpenAPI specs
- You want to auto-generate mocks and tests from specifications
- You need to validate API compliance across multiple services simultaneously
- You prefer specification-driven testing over DSL-driven testing

**Choose Spring Cloud Contract if:**
- Your stack is entirely Spring Boot / Spring Cloud
- You want tight integration with existing Spring testing infrastructure
- You prefer Maven/Gradle plugins over standalone servers
- You need simple stub-based testing without a broker

If you're also managing API mocking needs alongside contract testing, our [Wiremock vs Mockoon vs MockServer guide](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/) covers complementary tools that pair well with any of these contract testing frameworks.

## FAQ

### What is the difference between contract testing and integration testing?

Contract testing verifies that two services agree on the shape and semantics of their communication by checking against a defined contract (pact, spec, or stub). It runs in isolation — each service is tested independently without the other running. Integration testing requires all services to be running simultaneously and tests the actual network communication between them. Contract testing is faster, more reliable, and catches API contract violations at build time rather than in staging.

### Do I need a Pact Broker, or can I use Pact without one?

You can use Pact without a broker by sharing pact files through version control or file systems. However, the broker provides critical features: version tracking, compatibility matrices, webhook notifications, and the `can-i-deploy` check. For any team with more than two services, a self-hosted Pact Broker is strongly recommended. The Docker Compose setup above gets you running in minutes with PostgreSQL persistence.

### Can Specmatic replace manual API mocking?

Yes — this is one of Specmatic's core strengths. Given an OpenAPI specification, Specmatic automatically generates a mock server that conforms to the spec. All valid requests return responses matching the schema, and invalid requests are rejected. This eliminates the need to write and maintain manual mock servers. As your API spec evolves, your mocks stay in sync automatically.

### How does Spring Cloud Contract compare to Pact?

Spring Cloud Contract and Pact solve the same problem differently. Pact uses consumer-driven pacts published to a centralized broker, supports multiple languages, and provides rich compatibility tracking. Spring Cloud Contract uses a Groovy/YAML DSL with a stub runner that fetches stubs from Maven repositories, and is tightly integrated with the Spring ecosystem. If you're all-in on Spring, Spring Cloud Contract offers simpler setup. For polyglot environments, Pact is the better choice.

### Can I use contract testing for asynchronous messaging (Kafka, RabbitMQ)?

Pact has first-class support for async messaging contracts via Pact Message Pacts. You define the expected message structure on the consumer side, and the provider verifies it produces messages matching that structure. Specmatic also supports async contracts through its spec-based verification. Spring Cloud Contract has limited async support through Spring Cloud Stream contracts, but it is less mature than Pact's async capabilities.

### Is contract testing a replacement for end-to-end tests?

No. Contract testing replaces the majority of integration tests that exist solely to verify API compatibility between services. You should still maintain a smaller set of end-to-end tests for critical user journeys that span multiple services. The difference is that with contract testing, your end-to-end suite can be 80-90% smaller, making it faster and less brittle.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Pact vs Specmatic vs Spring Cloud Contract: Self-Hosted Contract Testing Guide 2026",
  "description": "Compare Pact, Specmatic, and Spring Cloud Contract for self-hosted contract testing. Learn consumer-driven contract testing with Docker setups, CI/CD integration, and best practices for microservices.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
