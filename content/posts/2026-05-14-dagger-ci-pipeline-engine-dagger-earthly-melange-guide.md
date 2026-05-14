---
title: "Self-Hosted Dagger CI/CD Pipeline Engine: Dagger vs Earthly vs Melange"
date: "2026-05-14"
tags: ["cicd", "pipeline", "container", "build-tools"]
draft: false
---

Modern software delivery demands reproducible, portable build pipelines that work identically across developer laptops, CI runners, and production environments. Three projects address this challenge from different angles: Dagger provides a programmable CI/CD engine built on container primitives, Earthly offers Makefile-like syntax for containerized builds, and Melange delivers APK-based package building for supply chain security. This guide compares their architectures, capabilities, and ideal use cases.

## The Problem with Traditional CI/CD

Traditional CI/CD pipelines depend heavily on the execution environment. A GitHub Actions workflow that works perfectly may fail on GitLab CI due to different base images, tool versions, or filesystem layouts. This "works on my CI" problem wastes developer time and creates inconsistent build artifacts.

The solution is container-native pipeline engines that encapsulate every build step in a container, ensuring identical behavior regardless of the host environment. These tools guarantee that if a pipeline runs on one machine, it runs identically everywhere.

## Dagger: Programmable CI/CD Engine

Dagger takes a unique approach by treating the entire pipeline as a programmable graph of container operations. Instead of writing YAML workflows, you define pipelines in code using Python, Go, TypeScript, or any language with Dagger SDK bindings.

**Key features:**
- SDK-based pipeline definition (Python, Go, TypeScript, Java)
- Engine runs as a local daemon or in CI
- Composable pipeline functions — build once, reuse everywhere
- Built-in caching for dependency layers and build steps
- Works identically on local machines and CI runners
- Support for multi-platform builds (cross-compilation)

Dagger's core innovation is the "Dagger Engine" — a persistent process that manages container execution, caching, and artifact passing between pipeline steps. The SDK lets you write pipelines as regular code with full access to loops, conditionals, and functions.

```python
# dagger.py - Python SDK
import dagger
from dagger import Container, Directory

async def build():
    async with dagger.Connection() as client:
        # Start from a base image
        builder = (
            client.container()
            .from_("golang:1.22-alpine")
            .with_directory("/src", client.host().directory("./"))
            .with_workdir("/src")
            .with_exec(["go", "mod", "download"])
            .with_exec(["go", "build", "-o", "/app/myapp", "./cmd/myapp"])
        )
        
        # Create final image
        final = (
            client.container()
            .from_("alpine:3.19")
            .with_file("/app/myapp", builder.file("/app/myapp"))
            .with_exec(["/app/myapp", "--version"])
        )
        
        # Export the built image
        await final.export("myapp:latest")

if __name__ == "__main__":
    import asyncio
    asyncio.run(build())
```

Dagger pipelines run with `dagger run python dagger.py` locally and with the same command in any CI environment. The engine handles caching, parallelism, and container lifecycle management automatically.

For multi-stage builds, Dagger composes functions that return Container objects:

```python
def test(src: Directory) -> Container:
    return (
        client.container()
        .from_("python:3.12-slim")
        .with_directory("/app", src)
        .with_workdir("/app")
        .with_exec(["pip", "install", "-r", "requirements.txt"])
        .with_exec(["pytest", "--junitxml=/tmp/results.xml"])
    )
```

This composability means you can test the same build function locally that runs in CI, with identical caching behavior and results.

## Earthly: Containerized Makefiles

Earthly brings the familiarity of Makefiles to container-native builds. Its syntax (`Earthfile`) looks like a combination of Dockerfile and Makefile, making it immediately accessible to developers who know either format.

**Key features:**
- Earthfile syntax combining Dockerfile and Makefile patterns
- Built-in caching with automatic cache key generation
- Remote caching support (S3, GCS, Azure Blob)
- Target dependencies and parallel execution
- Secret management with built-in masking
- SAT solver for optimal target execution order

Earthly's `Earthfile` defines targets that reference other targets as dependencies, similar to Make rules. Each target runs in an isolated container, and Earthly automatically determines the execution order based on dependency graphs.

```dockerfile
# Earthfile
VERSION 0.8

build:
    FROM golang:1.22-alpine
    WORKDIR /src
    COPY go.mod go.sum ./
    RUN go mod download
    COPY . .
    RUN go build -o /output/myapp ./cmd/myapp
    SAVE ARTIFACT /output/myapp AS LOCAL ./bin/myapp

test:
    FROM golang:1.22-alpine
    WORKDIR /src
    COPY go.mod go.sum ./
    RUN go mod download
    COPY . .
    RUN go test -v ./...
    SAVE ARTIFACT /tmp/results.xml AS LOCAL ./test-results.xml

docker:
    FROM alpine:3.19
    COPY +build/bin/myapp /app/myapp
    ENTRYPOINT ["/app/myapp"]
    SAVE IMAGE myapp:latest
```

Run targets with `earthly +build` or `earthly +docker`. Earthly automatically handles dependencies — running `earthly +docker` will execute `+build` first.

Earthly's SAT solver is particularly powerful for large build graphs. It analyzes all target dependencies and executes independent targets in parallel, minimizing total build time. For monorepos with dozens of services, this parallelism can reduce CI duration by 50% or more.

## Melange: Secure APK Package Building

Melange, developed by Chainguard, takes a fundamentally different approach — it builds APK packages (Alpine Linux packages) from source in a reproducible, secure pipeline. Rather than a general-purpose CI/CD engine, Melange specializes in creating verifiable, supply-chain-secure software packages.

**Key features:**
- YAML-based pipeline definition
- Builds APK packages for Alpine Linux
- Runs in isolated containers for reproducibility
- Supports SBOM (Software Bill of Materials) generation
- Designed for supply chain security
- Integrates with apko for container image building

Melange is purpose-built for organizations that need to maintain custom package repositories or rebuild upstream packages with additional hardening. It integrates tightly with apko, which uses APK packages to build minimal container images.

```yaml
# melange.yaml
package:
  name: myapp
  version: 1.0.0
  epoch: 0
  description: "My application packaged for Alpine Linux"
  target-architecture:
    - x86_64
    - aarch64

environment:
  contents:
    repositories:
      - https://dl-cdn.alpinelinux.org/alpine/edge/main
    packages:
      - build-base
      - go

pipeline:
  - uses: fetch
    with:
      uri: https://github.com/example/myapp/archive/v${{package.version}}.tar.gz
      expected-sha256: abc123...
  - uses: go/build
    with:
      output: myapp
      packages: ./cmd/myapp
  - uses: strip
```

Build the package with `melange build melange.yaml`. The pipeline runs in an isolated environment, fetching source code, compiling it, and producing a signed APK package. The resulting package can be installed on any Alpine Linux system or used by apko to build container images.

## Comparison Table

| Feature | Dagger | Earthly | Melange |
|---------|--------|---------|---------|
| **Pipeline Definition** | Code (Python, Go, TS) | Earthfile (Dockerfile+Make) | YAML |
| **Primary Use Case** | General CI/CD pipelines | Build/test pipelines | APK package building |
| **Caching** | Built-in engine cache | Local + remote (S3, GCS) | Build context cache |
| **Parallelism** | Manual (code-level) | SAT solver (automatic) | Per-package |
| **Local Execution** | Full parity with CI | Full parity with CI | Yes |
| **Container Building** | Yes (multi-stage) | Yes (SAVE IMAGE) | Via apko integration |
| **SBOM Generation** | Via SDK | No built-in | Yes (built-in) |
| **Language** | Go (engine) + SDK | Go | Go |
| **GitHub Stars** | 12,500+ | 14,000+ | 4,500+ |
| **Best For** | Programmable pipelines | Makefile-like CI builds | Secure package building |

## Choosing the Right Tool

**Use Dagger** when you need a programmable, composable pipeline that works identically everywhere. Its SDK approach means pipeline logic lives in your application code, enabling unit testing, code review, and reuse across projects. Ideal for organizations that want to treat pipeline logic as application code.

**Use Earthly** when your team is comfortable with Makefiles and Dockerfiles. The Earthfile syntax has a gentle learning curve, and the SAT solver automatically optimizes build graphs for maximum parallelism. Best for monorepos and projects with complex build dependency chains.

**Use Melange** when you need to build and maintain custom APK package repositories for Alpine Linux. It is purpose-built for supply chain security with SBOM generation, reproducible builds, and signature verification. Essential for organizations running Alpine-based infrastructure that need verified package sources.

## Why Self-Host Your CI/CD Pipeline Engine?

Self-hosting your pipeline infrastructure gives you complete control over build environments, artifact storage, and execution scheduling. Unlike SaaS CI/CD platforms, self-hosted engines keep your source code, build secrets, and artifacts within your network perimeter.

For container build optimization, see our [buildpacks vs tilt vs skaffold comparison](../2026-04-28-buildpacks-vs-tilt-vs-skaffold-self-hosted-container-build-guide-2026/) which covers alternative approaches to containerized application builds. If you manage NixOS infrastructure, our [deployment systems guide](../{today}-nix-deployment-systems-nixops-colmena-deploy-rs-guide/) complements these CI/CD tools with infrastructure-as-code deployment patterns. For WebAssembly workloads, our [WASM runtime comparison](../2026-04-21-wasmedge-vs-wasmtime-vs-wasmer-self-hosted-webassembly-runtimes-guide-2026/) covers runtime options for portable application deployment.

Self-hosted pipeline engines eliminate per-minute pricing that scales with team size. Instead of paying for compute minutes, you pay for the hardware running your builds — which can be shared across all projects and teams. This cost model becomes significantly cheaper as your build volume grows.

Reproducibility is another major advantage. Self-hosted engines let you pin exact tool versions, base images, and build environments. When a production issue requires rebuilding an artifact from six months ago, a self-hosted pipeline with version-pinned dependencies produces bit-identical output. Cloud CI platforms often update their base images and toolchains automatically, making historical builds non-reproducible.

Security control extends to artifact storage as well. Build artifacts, container images, and SBOM documents never leave your infrastructure. This matters for compliance frameworks like SOC 2, HIPAA, and FedRAMP, which require audit trails for all build and deployment activities.

## FAQ

### Can Dagger pipelines run without a local Docker daemon?

Yes. The Dagger Engine manages its own container runtime and does not require a Docker daemon on the host. It uses containerd internally, which is bundled with the engine binary. This means Dagger pipelines run on machines without Docker installed, as long as the Dagger Engine is present.

### How does Earthly handle secrets in CI environments?

Earthly provides built-in secret management through the `--secret` flag and the `--ci` mode. In CI mode, secrets are read from environment variables and masked in build output. Earthly also supports loading secrets from files and external secret managers like HashiCorp Vault. Secrets are never cached or persisted in build layers.

### What is the difference between Melange and apko?

Melange builds APK packages from source code, while apko uses APK packages to build container images. They work together in the Chainguard toolchain: Melange creates the packages, and apko assembles them into minimal, verifiable container images. You typically use both tools in sequence.

### Do these tools support Windows builds?

Earthly supports building Windows containers when running on a Windows host with containerd. Dagger currently focuses on Linux containers, though its SDK works on Windows hosts that connect to remote Linux Dagger Engines. Melange targets Alpine Linux packages and does not support Windows.

### Can I use Dagger with GitHub Actions?

Yes. Dagger provides a GitHub Action that installs the Dagger Engine and runs your pipeline. The pipeline definition (Python, Go, or TypeScript code) lives in your repository, and the Action simply executes `dagger run`. This gives you the same pipeline definition locally and in CI.

### How do these tools handle multi-architecture builds?

Dagger supports multi-platform builds through its SDK — you can specify target architectures and the engine handles cross-compilation and multi-arch image creation. Earthly supports multi-arch builds with the `--platform` flag and can produce multi-manifest images. Melange builds packages for each target architecture specified in the `target-architecture` field, and apko can assemble them into multi-arch container images.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Dagger CI/CD Pipeline Engine: Dagger vs Earthly vs Melange",
  "description": "Compare Dagger, Earthly, and Melange for self-hosted CI/CD pipeline execution — programmable engines, Makefile-like builds, and secure package building.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
