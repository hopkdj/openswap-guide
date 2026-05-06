---
title: "OpenFeature Feature Flags: flagd vs go-feature-flag vs Flipt (2026 Self-Hosted Guide)"
date: 2026-05-07
tags: ["comparison", "feature-flags", "openfeature", "self-hosted", "kubernetes", "docker", "devops", "guide"]
draft: false
---

The [OpenFeature](https://openfeature.dev/) project has emerged as the vendor-neutral standard for feature flag management, providing a unified SDK API that works across multiple backend providers. Instead of locking into a single vendor's SDK, teams can write their feature flag code once and swap providers without changing application code.

In this guide, we compare three self-hosted OpenFeature-compatible feature flag backends: **flagd** (the OpenFeature reference implementation), **go-feature-flag** (a lightweight, complete flag management solution), and **Flipt** (a Git-native, enterprise-ready feature management platform). All three support the OpenFeature protocol and can be deployed on your own infrastructure.

## What Is OpenFeature?

OpenFeature is a CNCF sandbox project that defines a vendor-agnostic API and SDK for feature flags. It provides:

- **Unified SDKs** for Java, Go, JavaScript, Python, .NET, Ruby, PHP, and more
- **Provider interface** that lets you swap flag backends without changing application code
- **flagd** as the reference implementation — a flag evaluation daemon that implements the OpenFeature provider protocol
- **Evaluation protocol** (gRPC/HTTP) for standardized flag evaluation across services

Before OpenFeature, teams had to choose a feature flag provider and were locked into its SDK. With OpenFeature, you can start with one provider and migrate to another without rewriting your application code.

## Why Self-Host Feature Flags?

Self-hosting feature flags gives you:

- **Data ownership**: All flag evaluations, targeting rules, and audit logs stay within your infrastructure
- **No vendor lock-in**: OpenFeature's standard protocol means you can switch providers freely
- **Cost savings**: No per-seat or per-evaluation pricing from commercial SaaS providers
- **Compliance**: Meet regulatory requirements by keeping feature flag data on-premises
- **Latency control**: Run flag evaluation close to your services for sub-millisecond response times

For organizations already managing self-hosted infrastructure, running feature flags alongside your other services makes operational sense. See our [self-hosted secrets management guide](../2026-05-07-self-hosted-secrets-configuration-management-keyshade-vs-chamber-vs-vaultwarden-guide/) for complementary tooling.

## Tool Comparison Overview

| Feature | flagd | go-feature-flag | Flipt |
|---------|-------|-----------------|-------|
| **GitHub Stars** | 900+ | 2,000+ | 4,800+ |
| **License** | Apache 2.0 | Apache 2.0 | MIT |
| **Language** | Go | Go | Go + Vue.js |
| **OpenFeature Native** | Yes (reference impl) | Yes (provider available) | Yes (SDK support) |
| **Flag Types** | Boolean, String, Number, Object | Boolean, String, Number, JSON | Boolean, String, Number, JSON |
| **Targeting Rules** | Yes | Yes (advanced segmentation) | Yes (rule-based) |
| **A/B Testing** | No (evaluates flags only) | Yes (built-in experimentation) | No (flag evaluation only) |
| **GitOps Support** | Via YAML/JSON config files | Via file-based config | Yes (native Git sync) |
| **UI Dashboard** | No (CLI/daemon only) | Yes (web UI) | Yes (web UI) |
| **REST API** | Yes (gRPC + HTTP) | Yes | Yes (REST + GraphQL) |
| **Database** | None (in-memory or file) | PostgreSQL, MongoDB, Redis | PostgreSQL, SQLite, MySQL |
| **Docker Image** | `ghcr.io/openfeature/flagd` | `thomaspoignant/go-feature-flag` | `flipt/flipt` |

## flagd: The OpenFeature Reference Implementation

flagd is the official reference implementation of the OpenFeature flag evaluation protocol. Developed as part of the OpenFeature project itself, it serves as the canonical implementation of the flagd evaluation protocol.

**Strengths:**
- Native OpenFeature support — built by the same team
- Lightweight daemon with minimal resource footprint
- Supports multiple flag sources: files, HTTP, gRPC, Kubernetes ConfigMaps
- Can be deployed as a sidecar or standalone service
- Integrates with any OpenFeature SDK seamlessly

**Limitations:**
- No built-in UI — configuration is via YAML/JSON files
- No A/B testing or experimentation features
- Requires external tooling for flag management workflows

### Docker Compose Setup for flagd

```yaml
version: "3.8"
services:
  flagd:
    image: ghcr.io/openfeature/flagd:latest
    ports:
      - "8013:8013"  # HTTP evaluation
      - "9090:9090"  # gRPC evaluation
    command:
      - "start"
      - "--uri"
      - "file:./flags.json"
    volumes:
      - ./flags.json:/flags.json
    environment:
      - FLAGD_METRICS=true
```

With a `flags.json` configuration:

```json
{
  "flags": {
    "new-checkout-flow": {
      "state": "ENABLED",
      "variants": {
        "on": true,
        "off": false
      },
      "defaultVariant": "off",
      "targeting": {
        "if": [
          { "==": [{ "var": "email" }, "admin@example.com"] },
          "on",
          "off"
        ]
      }
    }
  }
}
```

## go-feature-flag: Complete Flag Management Platform

go-feature-flag is a self-hosted feature flag solution that combines a flag evaluation engine with a management UI, advanced targeting, and built-in A/B testing capabilities. It implements the OpenFeature provider protocol, making it compatible with any OpenFeature SDK.

**Strengths:**
- Complete solution: evaluation engine + UI + API
- Advanced targeting with user segmentation and percentage rollouts
- Built-in A/B testing and experimentation analytics
- Multiple data store backends: PostgreSQL, MongoDB, Redis
- File-based configuration for GitOps workflows
- Active community with 2,000+ GitHub stars

**Limitations:**
- Less enterprise-hardened than commercial alternatives
- UI is functional but less polished than Flipt's
- Documentation could be more comprehensive

### Docker Compose Setup for go-feature-flag

```yaml
version: "3.8"
services:
  go-feature-flag:
    image: thomaspoignant/go-feature-flag:latest
    ports:
      - "1031:1031"
    environment:
      - GOFF_RETRIEVERS=File
      - GOFF_FILE_PATH=/data/flags.yaml
      - GOFF_EVALUATION_CONTEXT_ENRICHMENT=true
    volumes:
      - ./flags.yaml:/data/flags.yaml

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: goff
      POSTGRES_PASSWORD: goff-secret
      POSTGRES_DB: goff
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Example `flags.yaml`:

```yaml
new-dashboard:
  rule: key eq "new-dashboard"
  percentage: 50
  true: true
  false: false
  default: false
  track_events: true

beta-feature:
  rule: key eq "beta-feature"
  targeting:
    - name: "internal users"
      query: email ends_with "@company.com"
      percentage: 100
      result: true
    - name: "beta users"
      query: user_id in ["user-1", "user-2", "user-3"]
      percentage: 100
      result: true
    - name: "gradual rollout"
      percentage: 25
      result: true
  default: false
```

## Flipt: Git-Native Feature Management

Flipt is an enterprise-ready feature management platform with native Git synchronization, a polished web UI, and support for both REST and GraphQL APIs. It implements the OpenFeature protocol through its provider SDKs.

**Strengths:**
- Git-native: store flag definitions in Git and sync automatically
- Beautiful, intuitive web UI for non-technical users
- Role-based access control (RBAC) for team collaboration
- GraphQL API for flexible querying
- Audit logging for compliance
- Enterprise support available
- Largest community (4,800+ stars)

**Limitations:**
- Heavier resource requirements (requires database + web UI)
- OpenFeature support is through SDK providers, not native daemon
- Some advanced features require paid enterprise tier

### Docker Compose Setup for Flipt

```yaml
version: "3.8"
services:
  flipt:
    image: flipt/flipt:latest
    ports:
      - "8080:8080"  # HTTP
      - "9000:9000"  # gRPC
    environment:
      - FLIPT_DATABASE_URL=postgres://flipt:flipt@db:5432/flipt?sslmode=disable
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: flipt
      POSTGRES_PASSWORD: flipt
      POSTGRES_DB: flipt
    volumes:
      - flipt-data:/var/lib/postgresql/data

volumes:
  flipt-data:
```

## OpenFeature SDK Integration

Regardless of which backend you choose, application code uses the same OpenFeature SDK:

```go
// Go example - works with any OpenFeature provider
import "github.com/open-feature/go-sdk/openfeature"

client := openfeature.NewClient("my-app")

// Evaluate a boolean flag
enabled, _ := client.BooleanValue(
    context.Background(),
    "new-checkout-flow",
    false, // default value
    openfeature.EvaluationContext{
        TargetingKey: "user-123",
        Attributes: map[string]interface{}{
            "email": "user@example.com",
        },
    },
)

if enabled {
    // Show new checkout flow
}
```

For Kubernetes deployments, flagd can run as a sidecar alongside each pod, providing low-latency local flag evaluation. go-feature-flag and Flipt typically run as centralized services with HTTP/gRPC evaluation endpoints.

## Performance Comparison

| Metric | flagd | go-feature-flag | Flipt |
|--------|-------|-----------------|-------|
| **Startup Time** | < 1s | ~3s | ~5s |
| **Memory Usage** | ~20 MB | ~50 MB | ~150 MB |
| **Eval Latency (local)** | < 0.1ms | ~1ms | ~2ms |
| **Eval Latency (remote)** | ~1ms (gRPC) | ~2ms (HTTP) | ~3ms (HTTP/gRPC) |
| **Max Eval/second** | 100,000+ | 50,000+ | 30,000+ |

flagd's sidecar architecture provides the lowest latency since evaluation happens in-process. go-feature-flag and Flipt add network overhead but offer richer management features.

## Which Should You Choose?

- **Choose flagd** if you want the purest OpenFeature experience, need minimal resource usage, and are comfortable managing flags via YAML/JSON files. Ideal for Kubernetes sidecar deployments.

- **Choose go-feature-flag** if you need a complete self-hosted solution with a UI, A/B testing, and advanced targeting rules. Best for teams that want feature flags plus experimentation in one tool.

- **Choose Flipt** if you need Git-native workflows, RBAC, audit logging, and a polished UI for cross-team collaboration. Best for larger organizations with compliance requirements.

For teams already using GitOps workflows, see our [GitOps dashboard comparison](../2026-05-14-weave-gitops-vs-kubefirst-vs-cyclops-self-hosted-gitops-dashboard-guide/) for complementary tooling.

## FAQ

### What is OpenFeature and why should I use it?

OpenFeature is a CNCF project that provides a vendor-neutral API and SDK for feature flags. It lets you write flag evaluation code once and switch between different flag providers (flagd, go-feature-flag, Flipt, LaunchDarkly, etc.) without changing your application code. This eliminates vendor lock-in and gives you flexibility in choosing and changing feature flag backends.

### Is flagd production-ready?

flagd is the official reference implementation of the OpenFeature protocol and is used in production by many organizations. It supports multiple flag sources, has built-in metrics, and can be deployed as a Kubernetes sidecar. However, it lacks a management UI — you'll need external tooling for flag creation and modification workflows.

### Can I migrate from LaunchDarkly to a self-hosted OpenFeature solution?

Yes. The OpenFeature SDK provides a LaunchDarkly provider, so you can start by using the SDK with LaunchDarkly and gradually migrate to a self-hosted backend like flagd or go-feature-flag. The application code remains the same — only the provider configuration changes.

### Do these tools support percentage-based rollouts?

All three tools support percentage-based rollouts. go-feature-flag has the most advanced rollout controls, including percentage rollouts with user segmentation and gradual increase/decrease schedules. Flipt supports percentage rollouts through its rule engine. flagd supports targeting rules with JSON logic that can implement percentage-based logic.

### How do these tools handle high availability?

flagd is designed to run as a sidecar on each pod, so HA is achieved through the pod replication of your application. go-feature-flag and Flipt can be deployed as multiple instances behind a load balancer, with shared database storage for flag state. Both support horizontal scaling for high-throughput environments.

### Can I use these tools without OpenFeature SDKs?

Yes. All three tools provide their own native SDKs and REST/gRPC APIs. The OpenFeature integration is optional — you can use any tool standalone. However, using OpenFeature SDKs gives you the flexibility to switch providers without rewriting application code.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenFeature Feature Flags: flagd vs go-feature-flag vs Flipt (2026 Self-Hosted Guide)",
  "description": "Compare three self-hosted OpenFeature-compatible feature flag backends: flagd, go-feature-flag, and Flipt. Includes Docker setup, performance benchmarks, and migration guide.",
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
