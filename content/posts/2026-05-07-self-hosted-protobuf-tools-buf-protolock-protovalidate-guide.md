---
title: "Self-Hosted Protobuf Tooling: buf vs protolock vs protovalidate 2026"
date: "2026-05-07"
tags: ["comparison", "guide", "self-hosted", "protobuf", "api", "devops", "grpc"]
draft: false
---

Protocol Buffers (protobuf) have become the standard for defining APIs and serializing structured data in microservices architectures. But managing `.proto` files across teams and repositories introduces challenges: schema drift, breaking changes, inconsistent code generation, and missing validation rules.

This guide compares three essential protobuf tooling options you can self-host and integrate into your CI/CD pipeline: **buf** (the modern protobuf toolkit), **protolock** (schema change tracking), and **protovalidate** (runtime message validation).

## Overview

| Feature | buf | protolock | protovalidate |
|---------|-----|-----------|---------------|
| GitHub Stars | 11,000+ | 630+ | 1,490+ |
| Last Updated | May 2026 | Feb 2024 | Apr 2026 |
| Organization | bufbuild | nilslice | bufbuild |
| Primary Purpose | Full protobuf toolkit | Schema change detection | Runtime validation |
| Language Support | Go, multi-language | Go (CLI) | Go, Java, Python, C++, JS |
| Linting | ✅ Built-in | ❌ | ❌ |
| Breaking Change Detection | ✅ Built-in | ✅ File-based | ❌ |
| Code Generation | ✅ Plugin system | ❌ | ❌ |
| Schema Registry | ✅ BSR | ❌ | ❌ |
| Message Validation | ❌ | ❌ | ✅ CEL-based rules |
| Docker Support | ✅ Official image | ❌ | ✅ Sidecar pattern |

## buf: The Modern Protobuf Toolkit

[buf](https://github.com/bufbuild/buf) is a comprehensive protobuf toolkit that replaces the traditional `protoc` compiler workflow. It provides linting, breaking change detection, code generation, and a schema registry (BSR — Buf Schema Registry) all in one tool.

### Key Features

- **`buf lint`** — Enforces consistent protobuf style rules (e.g., field naming, package structure, reserved field usage)
- **`buf breaking`** — Detects breaking changes between versions of your proto files using semantic versioning awareness
- **`buf generate`** — Generates code for any language using plugins, with built-in dependency management
- **`buf push`** — Publishes proto files to the Buf Schema Registry for centralized versioning
- **`buf mod`** — Manages protobuf dependencies like package managers

### Self-Hosting with Docker Compose

buf's BSR (Schema Registry) can be self-hosted for internal use:

```yaml
# docker-compose.yml for buf BSR
version: "3.8"
services:
  bsr:
    image: bufbuild/bsr:latest
    ports:
      - "8080:8080"
      - "443:8443"
    environment:
      BSR_CONFIG: /etc/bsr/config.yaml
      BSR_DATABASE_URL: postgresql://bsr:password@postgres:5432/bsr
    volumes:
      - ./bsr-config:/etc/bsr
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: bsr
      POSTGRES_PASSWORD: password
      POSTGRES_DB: bsr
    volumes:
      - bsr-data:/var/lib/postgresql/data

volumes:
  bsr-data:
```

### CI/CD Integration

```yaml
# .github/workflows/buf-ci.yml
name: Protobuf CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bufbuild/buf-setup-action@v1
      - run: buf lint
      - run: buf breaking --against '.git#branch=main'
```

### buf.yaml Configuration

```yaml
version: v2
lint:
  use:
    - DEFAULT
    - COMMENTS
    - FILE_LOWER_SNAKE_CASE
  except:
    - SERVICE_SUFFIX
  ignore:
    - third_party
breaking:
  use:
    - FILE
  except:
    - FIELD_SAME_DEFAULT
```

## protolock: Schema Change Tracking

[protolock](https://github.com/nilslice/protolock) is a lightweight tool focused on one thing: tracking changes to your protobuf schema files and preventing breaking modifications. It maintains a `.proto.lock` file that records the current state of your schema.

### Key Features

- **`protolock init`** — Creates a `.proto.lock` file from existing proto definitions
- **`protolock status`** — Checks if current proto files differ from the locked state
- **`protolock commit`** — Updates the lock file with current schema state
- **`protolock warnings`** — Reports potential breaking changes before they're committed
- Works with any protobuf project regardless of language or framework

### Installation and Usage

```bash
# Install protolock
go install github.com/nilslice/protolock/cmd/protolock@latest

# Initialize lock file from your proto directory
protolock init --protoroot=./proto

# Check for breaking changes
protolock status --protoroot=./proto

# Update lock file after intentional changes
protolock commit --protoroot=./proto
```

### CI/CD Integration

```yaml
# .github/workflows/protolock.yml
name: Protolock Schema Check
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.22"
      - run: go install github.com/nilslice/protolock/cmd/protolock@latest
      - run: protolock status --protoroot=./proto
        name: Check for breaking schema changes
```

### Docker Compose Setup

```yaml
# docker-compose.yml for protolock CI runner
version: "3.8"
services:
  protolock:
    image: golang:1.22-alpine
    working_dir: /workspace
    volumes:
      - ./proto:/workspace/proto
      - ./proto.lock:/workspace/proto.lock
    command: >
      sh -c "
        go install github.com/nilslice/protolock/cmd/protolock@latest &&
        protolock status --protoroot=./proto
      "
```

## protovalidate: Runtime Message Validation

[protovalidate](https://github.com/bufbuild/protovalidate) adds constraint-based validation directly to protobuf messages using CEL (Common Expression Language) rules. Instead of writing validation logic in your application code, you define rules in your `.proto` files.

### Key Features

- **Declarative validation** — Define constraints directly in `.proto` files using CEL expressions
- **Multi-language support** — Runtime libraries for Go, Java, Python, C++, and JavaScript/TypeScript
- **Built-in constraints** — String length, numeric ranges, regex patterns, repeated field constraints
- **Custom validators** — Extend with custom CEL functions for domain-specific rules
- **gRPC integration** — Automatic validation on gRPC request/response messages

### Defining Validation Rules

```protobuf
syntax = "proto3";
package user.v1;

import "buf/validate/validate.proto";

message CreateUserRequest {
  string username = 1 [
    (buf.validate.field).string.min_len = 3,
    (buf.validate.field).string.max_len = 32,
    (buf.validate.field).string.pattern = "^[a-z0-9_]+$"
  ];

  string email = 2 [
    (buf.validate.field).string.email = true
  ];

  int32 age = 3 [
    (buf.validate.field).int32.gte = 0,
    (buf.validate.field).int32.lte = 150
  ];

  repeated string tags = 4 [
    (buf.validate.field).repeated.min_items = 1,
    (buf.validate.field).repeated.max_items = 10,
    (buf.validate.field).repeated.items.string.max_len = 20
  ];
}
```

### Go Integration Example

```go
package main

import (
    "fmt"
    "google.golang.org/protobuf/proto"
    "github.com/bufbuild/protovalidate-go"
    pb "your/proto/package"
)

func main() {
    validator, _ := protovalidate.New()
    
    req := &pb.CreateUserRequest{
        Username: "ab",  // Too short (min 3 chars)
        Email:    "not-an-email",
        Age:      200,   // Too old (max 150)
    }
    
    err := validator.Validate(req)
    if err != nil {
        fmt.Println("Validation failed:", err)
    }
}
```

### Docker Compose for Validation Sidecar

```yaml
# docker-compose.yml for protovalidate sidecar
version: "3.8"
services:
  api:
    image: your-api:latest
    ports:
      - "8080:8080"
    environment:
      PROTOVALIDATE_MODE: "enforce"

  proto-validator:
    image: bufbuild/protovalidate:latest
    volumes:
      - ./proto:/proto
    command: ["--proto-path", "/proto", "--validate"]
```

## Comparison: When to Use Each Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| New protobuf project starting from scratch | **buf** — provides the full toolchain out of the box |
| Existing project needing change tracking | **protolock** — minimal disruption, lock-file approach |
| gRPC services needing input validation | **protovalidate** — declarative rules in proto files |
| Multi-team proto file sharing | **buf** — BSR provides centralized schema management |
| CI/CD breaking change prevention | **buf** or **protolock** — both integrate well |
| Runtime safety without application code changes | **protovalidate** — validation at the protobuf layer |
| Lightweight, single-purpose tool | **protolock** — does one thing well |

## Why Self-Host Protobuf Tooling?

Self-hosting protobuf tooling gives your team full control over the schema lifecycle without depending on external SaaS services. When you self-host the Buf Schema Registry (or run protolock checks locally), your `.proto` files never leave your infrastructure — critical for organizations handling sensitive API contracts or proprietary data formats.

For API governance, see our [API lifecycle management guide](../2026-04-26-self-hosted-api-lifecycle-management-kong-apisix-tyk-gravitee-krakend-guide-2026/). If you're building gRPC services, our [gRPC client tools comparison](../2026-04-27-grpcurl-vs-grpcui-vs-evans-self-hosted-grpc-client-tools-guide-2026/) covers testing and debugging utilities. For schema management at the service level, check our [schema registry guide](../2026-04-20-apicurio-vs-karapace-vs-confluent-schema-registry-guide-2026/).

Organizations that self-host protobuf tooling benefit from:

- **Data sovereignty** — Proto definitions stay within your network perimeter
- **Offline development** — Teams can lint, validate, and generate code without internet access
- **Custom rule enforcement** — Define organization-specific lint rules that reflect your architectural standards
- **Audit trails** — Track schema changes with full git history and lock file diffs
- **Cost control** — Avoid per-developer or per-API costs from SaaS schema registries

## FAQ

### What is the difference between buf and protoc?

buf is a higher-level tool that wraps protoc and adds linting, breaking change detection, dependency management, and code generation plugins. protoc is the raw compiler that only generates code. buf provides a more developer-friendly experience with sensible defaults and a plugin ecosystem.

### Can protolock detect all breaking changes?

protolock detects most breaking changes including field removal, type changes, and number reassignments. However, it works at the file level and may miss some semantic breaking changes that buf's `breaking` command catches by analyzing the compiled descriptor sets.

### Does protovalidate replace application-level validation?

protovalidate handles structural and constraint validation at the serialization layer. You may still need application-level validation for business logic rules (e.g., "user must have sufficient balance"). protovalidate excels at format, range, and pattern validation.

### Is the Buf Schema Registry free to self-host?

The BSR has a cloud-hosted free tier. For self-hosted deployments, bufbuild offers enterprise licensing. You can run the core buf CLI tools (lint, breaking, generate) for free without any registry.

### How does protolock handle proto file dependencies?

protolock tracks each `.proto` file independently. It records message definitions, field numbers, types, and options. When you run `protolock status`, it compares the current state against the locked state and reports any differences that could break backward compatibility.

### Can I use protovalidate with existing protobuf messages?

Yes. You add validation annotations to your existing `.proto` files incrementally. protovalidate is backward compatible — messages without validation rules pass through unchanged. You can adopt validation field-by-field.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Protobuf Tooling: buf vs protolock vs protovalidate 2026",
  "description": "Compare self-hosted protobuf tooling: buf for full toolkit, protolock for schema change tracking, and protovalidate for runtime message validation. Includes Docker Compose configs and CI/CD integration.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
