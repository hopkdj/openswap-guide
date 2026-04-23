---
title: "LocalStack vs s3ninja vs S3Mock: Self-Hosted S3 Testing Tools 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "testing", "aws", "s3", "developer-tools"]
draft: false
description: "Compare LocalStack, s3ninja, and Adobe S3Mock for self-hosted S3 API testing and development. Docker configs, setup guides, and feature comparison for offline AWS development."
---

When building applications that interact with AWS S3, testing against the live cloud service is slow, expensive, and unreliable for CI/CD pipelines. Self-hosted S3 mock servers solve this by emulating the S3 API locally — giving you fast, deterministic, and cost-free testing environments.

In this guide, we compare three leading open-source S3 testing tools: **LocalStack** (the full local AWS cloud stack), **s3ninja** (a lightweight S3-only emulator), and **Adobe S3Mock** (a Java/Kotlin S3 mock built for enterprise testing workflows). Whether you need a comprehensive AWS mock, a minimal S3 emulator, or a Java-native testing library, this comparison will help you choose the right tool.

## Why Self-Host Your S3 Testing Environment

Running S3 integration tests against real AWS introduces several problems:

- **Latency**: Every API call requires a network round-trip, slowing down test suites
- **Cost**: Each PUT, GET, and LIST operation costs money, even in test environments
- **Reliability**: Network outages, rate limits, and AWS maintenance windows break CI/CD pipelines
- **Data isolation**: Test data persists in the cloud between runs, causing flaky tests
- **Privacy**: Sensitive test data leaves your infrastructure

A self-hosted S3 mock eliminates all of these issues. Tests run in milliseconds, cost nothing, work offline, start with clean state every time, and never transmit data outside your network.

## Tool Overview

| Feature | LocalStack | s3ninja | Adobe S3Mock |
|---|---|---|---|
| **GitHub Stars** | 64,866 | 551 | 1,091 |
| **Language** | Python | Java | Kotlin |
| **Last Updated** | 2026-03-23 | 2026-04-23 | 2026-04-22 |
| **Docker Image** | `localstack/localstack` | `scireum/s3ninja` | `adobe/s3mock` |
| **Default Port** | 4566 | 9000 | 9090 (HTTP), 9191 (HTTPS) |
| **Scope** | Full AWS (60+ services) | S3 only | S3 only |
| **Testcontainers** | Yes | No | Yes (native Kotlin) |
| **Persistence** | Volume-backed | Volume-backed | In-memory or disk |
| **Web UI** | Yes | Yes | No |
| **License** | Elastic License 2.0 | MIT | Apache 2.0 |

## LocalStack: The Full Local AWS Stack

[LocalStack](https://github.com/localstack/localstack) is the most popular and feature-rich local AWS development environment. It emulates over 60 AWS services including S3, Lambda, DynamoDB, SQS, SNS, API Gateway, and many more — all running in a single Docker container.

For teams building serverless applications or microservices that depend on multiple AWS services, LocalStack provides the most comprehensive testing experience. You can test an entire cloud architecture locally without any internet connection.

### Docker Compose Setup

```yaml
services:
  localstack:
    container_name: "localstack-main"
    image: localstack/localstack
    ports:
      - "127.0.0.1:4566:4566"
      - "127.0.0.1:4510-4559:4510-4559"
    environment:
      - DEBUG=0
      - SERVICES=s3,lambda,dynamodb,sqs
    volumes:
      - "./localstack-data:/var/lib/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
```

Start it with `docker compose up -d` and access the S3 API at `http://localhost:4566`.

### Using with AWS CLI

```bash
# Configure a local profile
aws configure set endpoint_url http://localhost:4566 --profile localstack
aws configure set aws_access_key_id test --profile localstack
aws configure set aws_secret_access_key test --profile localstack

# Create a bucket
aws --profile localstack s3 mb s3://my-test-bucket

# Upload a file
aws --profile localstack s3 cp test.txt s3://my-test-bucket/

# List buckets
aws --profile localstack s3 ls
```

### Using with SDK (Python/boto3)

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
    config=Config(signature_version="s3v4"),
)

s3.create_bucket(Bucket="my-app-data")
s3.put_object(Bucket="my-app-data", Key="config.json", Body=b'{"env": "test"}')
response = s3.get_object(Bucket="my-app-data", Key="config.json")
print(response["Body"].read().decode())
```

### Key Features

- **60+ AWS services** — S3, Lambda, DynamoDB, SQS, SNS, API Gateway, ECS, ECR, and more
- **Infrastructure-as-Code support** — Deploy CloudFormation templates, Terraform configs, and SAM applications locally
- **Event-driven testing** — Trigger Lambda functions from S3 events, SQS messages, or DynamoDB streams
- **Web dashboard** — Visual resource explorer at `http://localhost:4566/_localstack`
- **CI/CD friendly** — Pre-built Docker images for GitHub Actions, GitLab CI, and Jenkins

### When to Choose LocalStack

Pick LocalStack when your application uses multiple AWS services beyond S3. If you need to test Lambda functions triggered by S3 uploads, or DynamoDB tables populated by SQS messages, LocalStack is the only tool in this comparison that can handle those scenarios.

## s3ninja: Lightweight S3 Emulator

[s3ninja](https://github.com/scireum/s3ninja) is a focused, lightweight S3 API emulator that does one thing well: it speaks the S3 protocol. Written in Java, it runs on a minimal footprint and is ideal when you only need S3 compatibility without the overhead of a full AWS stack.

### Docker Compose Setup

```yaml
services:
  s3ninja:
    image: scireum/s3ninja:latest
    container_name: s3ninja-local
    ports:
      - "9444:9000"
    volumes:
      - "./s3ninja-data:/home/sirius/data"
      - "./s3ninja-logs:/home/sirius/logs"
    environment:
      - JAVA_XMX=1g
      - S3NINJA_PORT=9000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/ui"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Using with AWS CLI

```bash
# Set up alias for convenience
alias s3ninja-aws="aws --endpoint-url http://localhost:9444 \
  --aws-access-key-id AKIAIOSFODNN7EXAMPLE \
  --aws-secret-access-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Create and use a bucket
s3ninja-aws s3 mb s3://test-bucket
s3ninja-aws s3 cp local-file.txt s3://test-bucket/
s3ninja-aws s3 ls s3://test-bucket/
```

### Using with SDK (Python/boto3)

```python
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9444",
    aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
    aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region_name="us-east-1",
)

s3.create_bucket(Bucket="ninja-test")
s3.put_object(Bucket="ninja-test", Key="data.json", Body=b'{"status": "ok"}')
```

### Key Features

- **MIT licensed** — Completely open source with no restrictions
- **Built-in web UI** — Browse buckets and objects at `http://localhost:9444/ui`
- **Small footprint** — Runs comfortably with 512MB RAM
- **S3 API coverage** — Supports all core S3 operations including multipart uploads
- **Simple configuration** — No complex setup, just set the port and run

### When to Choose s3ninja

Choose s3ninja when you need a simple, MIT-licensed S3 emulator with a web UI. It is perfect for teams that want to test S3 uploads and downloads without the complexity of a full AWS mock. Its small resource footprint makes it ideal for CI/CD runners with limited memory.

## Adobe S3Mock: Enterprise-Grade S3 Testing

[Adobe S3Mock](https://github.com/adobe/S3Mock) is a Kotlin-based S3 mock designed specifically for Java/Kotlin testing workflows. It integrates natively with JUnit, TestNG, and Testcontainers, making it the preferred choice for JVM-based projects that need S3 testing.

### Docker Compose Setup

```yaml
services:
  s3mock:
    image: adobe/s3mock:latest
    environment:
      - COM_ADOBE_TESTING_S3MOCK_STORE_INITIAL_BUCKETS=test-bucket,integration-data
      - COM_ADOBE_TESTING_S3MOCK_STORE_ROOT=/containers3root
      - COM_ADOBE_TESTING_S3MOCK_STORE_RETAIN_FILES_ON_EXIT=true
    ports:
      - "9090:9090"
      - "9191:9191"
    volumes:
      - "./s3mock-data:/containers3root"
```

### Using with AWS CLI

```bash
# Target the HTTP port
aws --endpoint-url http://localhost:9090 \
  --aws-access-key-id test \
  --aws-secret-access-key test \
  s3 mb s3://test-bucket

# Upload with HTTPS port (port 9191)
aws --endpoint-url https://localhost:9191 \
  --no-verify-ssl \
  s3 cp data.csv s3://test-bucket/
```

### Using with SDK (Java)

```java
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.regions.Region;
import java.net.URI;

S3Client s3 = S3Client.builder()
    .endpointOverride(URI.create("http://localhost:9090"))
    .region(Region.US_EAST_1)
    .build();

s3.createBucket(CreateBucketRequest.builder()
    .bucket("java-test-bucket")
    .build());
```

### Using with Testcontainers (JUnit 5)

```java
import com.adobe.testing.s3mock.testcontainers.S3MockContainer;
import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@Testcontainers
class MyS3Test {

    @Container
    static S3MockContainer s3Mock = new S3MockContainer("latest")
        .withInitialBucket("my-bucket");

    @Test
    void testS3Upload() {
        String endpoint = s3Mock.getHttpEndpoint();
        // Use the endpoint with AWS SDK
        // Buckets are pre-created
    }
}
```

### Key Features

- **Apache 2.0 licensed** — Permissive license for commercial use
- **Native Testcontainers support** — Drop-in JUnit integration
- **Dual-port support** — HTTP (9090) and HTTPS (9191) out of the box
- **Pre-seeded buckets** — Define initial buckets via environment variables
- **File retention** — Persist data between container restarts for debugging
- **Maven/Gradle friendly** — Published to Maven Central as `com.adobe.testing:s3mock`

### When to Choose Adobe S3Mock

Choose Adobe S3Mock when your codebase is Java or Kotlin and you want tight integration with your existing test framework. The Testcontainers support means S3Mock spins up automatically as part of your test suite, with no manual Docker management required.

## Feature Comparison

| Criteria | LocalStack | s3ninja | Adobe S3Mock |
|---|---|---|---|
| **S3 API Coverage** | Full (including advanced features) | Core S3 operations | Core S3 operations |
| **Other AWS Services** | 60+ (Lambda, DynamoDB, SQS, etc.) | None | None |
| **Docker Image Size** | ~1.5 GB | ~200 MB | ~300 MB |
| **Memory Usage** | 2-4 GB | 512 MB - 1 GB | 512 MB - 1 GB |
| **Startup Time** | 30-60 seconds | 5-10 seconds | 10-20 seconds |
| **CI/CD Overhead** | Higher (large image) | Low | Low |
| **Test Framework Integration** | Python/JS SDKs | None | JUnit 4/5, TestNG, Testcontainers |
| **License** | Elastic License 2.0 | MIT | Apache 2.0 |
| **Commercial Use** | Restricted (free tier available) | Unrestricted | Unrestricted |

## Quick Start Recommendations

### For Full-Stack AWS Development

If your application uses S3 alongside Lambda, DynamoDB, or other AWS services, LocalStack is the clear choice. The single Docker container gives you the entire AWS ecosystem locally:

```yaml
services:
  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,lambda,dynamodb,sqs,apigateway
    volumes:
      - "./.localstack:/var/lib/localstack"
```

### For S3-Only Testing in CI/CD

If your CI pipeline only needs to test S3 uploads and downloads, s3ninja's small footprint and MIT license make it ideal:

```yaml
# GitHub Actions example
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      s3:
        image: scireum/s3ninja:latest
        ports:
          - "9000:9000"
        options: >-
          --health-cmd "curl -f http://localhost:9000/ui"
          --health-interval 10s
          --health-retries 5
    steps:
      - run: echo "S3 endpoint: http://localhost:9000"
```

### For Java/Kotlin Projects

When writing tests in Java or Kotlin, Adobe S3Mock's Testcontainers integration provides the smoothest developer experience:

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("com.adobe.testing:s3mock-testcontainers:5.+")
    testImplementation("org.testcontainers:junit-jupiter:1.+")
}
```

For related reading, see our [MinIO self-hosted S3 storage guide](../minio-self-hosted-s3-object-storage-guide-2026/) for production S3-compatible storage, our [API mocking and testing tools guide](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/) for broader API testing strategies, and the [email testing sandbox comparison](../mailpit-vs-mailhog-vs-mailcatcher-self-hosted-email-testing-sandbox-2026/) which covers a similar pattern of local service emulation for testing.

## FAQ

### What is the difference between LocalStack and s3ninja?

LocalStack emulates over 60 AWS services including S3, Lambda, DynamoDB, SQS, and more — making it a complete local AWS environment. s3ninja focuses exclusively on the S3 API, offering a lightweight emulator with a smaller Docker image (~200 MB vs ~1.5 GB) and lower memory requirements. Choose LocalStack if you need multi-service testing; choose s3ninja for simple S3-only scenarios.

### Can I use these tools for production S3 storage?

No. These tools are designed for development and testing purposes only. They lack the durability, redundancy, and performance guarantees required for production workloads. For production S3-compatible storage, use a purpose-built solution like [MinIO](../minio-self-hosted-s3-object-storage-guide-2026/) or SeaweedFS.

### Is LocalStack free for commercial use?

LocalStack uses the Elastic License 2.0, which allows free use for development and testing but restricts offering LocalStack as a managed service to third parties. The core functionality is available in the Community Edition at no cost. s3ninja (MIT) and Adobe S3Mock (Apache 2.0) have no commercial use restrictions.

### How do I configure my AWS SDK to use a local S3 mock?

Set the `endpoint_url` parameter in your SDK client to point to the mock server's address (e.g., `http://localhost:4566` for LocalStack, `http://localhost:9000` for s3ninja, or `http://localhost:9090` for S3Mock). Use any access key and secret key — mock servers accept arbitrary credentials.

### Which tool has the best S3 API compatibility?

LocalStack offers the most comprehensive S3 API coverage, including advanced features like lifecycle policies, versioning, and event notifications. s3ninja covers all core S3 operations including multipart uploads. Adobe S3Mock focuses on the most commonly used S3 operations needed for testing workflows. For most application testing scenarios, all three provide sufficient API coverage.

### Can I run these tools in GitHub Actions or GitLab CI?

Yes, all three provide Docker images that work in CI/CD pipelines. s3ninja and Adobe S3Mock start fastest (5-20 seconds) and have the smallest images, making them ideal for CI. LocalStack takes longer to start (30-60 seconds) but provides a more complete testing environment if your tests depend on multiple AWS services.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "LocalStack vs s3ninja vs S3Mock: Self-Hosted S3 Testing Tools 2026",
  "description": "Compare LocalStack, s3ninja, and Adobe S3Mock for self-hosted S3 API testing and development. Docker configs, setup guides, and feature comparison for offline AWS development.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
