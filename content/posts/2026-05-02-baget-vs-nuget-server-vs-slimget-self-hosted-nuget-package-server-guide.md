---
title: "BaGet vs NuGet.Server vs SlimGet: Self-Hosted NuGet Package Servers 2026"
date: 2026-05-02T12:00:00+00:00
draft: false
tags: ["nuget", "dotnet", "package-manager", "csharp", "self-hosted", "repository"]
---

For .NET developers, NuGet is the standard package management system — the equivalent of npm for JavaScript or pip for Python. While the public nuget.org repository hosts hundreds of thousands of packages, organizations that build internal libraries, need offline access, or want to control exactly which packages reach their production systems require a self-hosted NuGet server.

In this guide, we compare three open-source self-hosted NuGet servers: **BaGet**, **NuGet.Server**, and **SlimGet**. Each provides a different balance of features, complexity, and maintenance status for internal package distribution.

## Why Self-Host a NuGet Server?

Running your own NuGet server addresses several common .NET development challenges:

- **Internal package distribution** — share libraries across teams without publishing to the public registry
- **Package proxying and caching** — cache upstream NuGet packages locally for faster restores and offline access
- **Version control** — pin specific package versions across projects, preventing unexpected dependency updates
- **Security scanning** — vet packages before they reach developers, blocking known vulnerabilities
- **Bandwidth optimization** — download popular packages once and serve them internally
- **Compliance** — maintain an auditable record of every package version deployed in your organization

For .NET shops managing multiple services and shared libraries, an internal NuGet server becomes essential infrastructure.

## Quick Comparison Table

| Feature | BaGet | NuGet.Server | SlimGet |
|---|---|---|---|
| **Stars** | 2,784 | 610 | 40 |
| **Language** | C# (.NET Core) | C# (.NET Framework) | C# (.NET 6+) |
| **Last Update** | 2024-07 | 2025-03 | 2024-05 |
| **Database** | SQLite, PostgreSQL, MySQL, SQL Server | File-based | SQLite |
| **Package caching** | Yes (upstream proxy) | No | No |
| **Web UI** | Yes (basic) | No | No |
| **REST API** | Full NuGet v3 API | NuGet v2 API only | NuGet v3 API |
| **Authentication** | API keys | None | Basic auth |
| **Docker support** | Official image | Community | Community |
| **Best For** | Full-featured internal server | Simple ASP.NET deployment | Lightweight .NET 6+ server |

## BaGet — Full-Featured NuGet Server with Proxy Caching

**BaGet** is the most feature-rich open-source NuGet server available. Built on .NET Core, it supports multiple database backends, upstream package proxying, a basic web UI, and the complete NuGet v3 API.

### Key Features

- **Upstream package proxy** — cache packages from nuget.org locally, reducing external dependency and speeding up restores
- **Multiple database backends** — SQLite for small deployments, PostgreSQL/MySQL/SQL Server for production
- **Complete NuGet v3 API** — full compatibility with Visual Studio, dotnet CLI, and Rider
- **API key authentication** — control who can publish packages to your server
- **Package search** — discover packages through the web UI or API
- **Symbol server** — host PDB files alongside packages for debugging support
- **Health checks** — built-in monitoring endpoint for container orchestration

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  baget:
    image: loicsharma/baget:latest
    container_name: baget
    environment:
      - Storage__Type=FileSystem
      - Storage__Path=/data/packages
      - Database__Type=Sqlite
      - Database__ConnectionString=Data Source=/data/baget.db
    volumes:
      - ./data:/data
    ports:
      - 5000:80
    restart: unless-stopped
```

### Configuration via Environment Variables

```yaml
environment:
  - Storage__Type=FileSystem
  - Storage__Path=/data/packages
  - Database__Type=PostgreSQL
  - Database__ConnectionString=Host=db;Database=baget;Username=baget;Password=secret
  - Mirror__Enabled=true
  - Mirror__PackageSource=https://api.nuget.org/v3/index.json
```

When mirror mode is enabled, BaGet acts as a proxy cache — if a requested package exists locally, it serves it immediately. If not, it fetches from nuget.org, caches it, then serves it. Subsequent requests hit the local cache.

### Client Configuration

Add your server to `nuget.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="Internal" value="http://baget.internal/v3/index.json" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
  <packageSourceCredentials>
    <Internal>
      <add key="Username" value="api" />
      <add key="ClearTextPassword" value="YOUR_API_KEY" />
    </Internal>
  </packageSourceCredentials>
</configuration>
```

Publish packages with the dotnet CLI:

```bash
dotnet nuget push ./MyLibrary.1.0.0.nupkg \
  --source http://baget.internal/v3/index.json \
  --api-key YOUR_API_KEY
```

## NuGet.Server — Official Microsoft Reference Implementation

**NuGet.Server** is Microsoft's official reference implementation of a NuGet package server. It's a simple ASP.NET application that stores packages on the filesystem and serves them via the NuGet v2 API.

### Key Features

- **Official Microsoft project** — maintained by the NuGet team on GitHub
- **Zero configuration** — drop the package into a folder and it appears in the feed
- **Filesystem-based storage** — no database required, packages stored as `.nupkg` files
- **Simple deployment** — runs on any ASP.NET-compatible web server
- **IIS integration** — native integration with Windows authentication and IIS features
- **Lightweight** — minimal dependencies and low resource requirements

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nuget-server:
    image: sunside/simple-nuget-server:latest
    container_name: nuget-server
    environment:
      - APIKEY=your-secret-api-key
    volumes:
      - ./packages:/var/www/ba-get/Packages
    ports:
      - 5001:80
    restart: unless-stopped
```

### Setup on Windows Server with IIS

For organizations running Windows infrastructure, NuGet.Server integrates naturally:

```powershell
# Install the NuGet.Server package in an empty ASP.NET project
Install-Package NuGet.Server -ProjectName NuGetServer

# Configure the packages directory in web.config
# <add key="packagesPath" value="D:\NuGetPackages" />

# Deploy to IIS and set the application pool identity
# with read/write access to the packages directory
```

NuGet.Server's simplicity is its strength. Drop a `.nupkg` file into the packages folder and it's immediately available. However, it lacks proxy caching, search functionality, and the modern v3 API — making it best suited for small teams with basic needs.

## SlimGet — Minimalist NuGet v3 Server

**SlimGet** is a lightweight, minimalist NuGet server built on modern .NET. It implements the NuGet v3 API with minimal dependencies, making it ideal for developers who want a simple server without the complexity of BaGet.

### Key Features

- **NuGet v3 API support** — modern API compatible with current tooling
- **Minimal dependencies** — no external database required, uses SQLite by default
- **Simple configuration** — single configuration file with sensible defaults
- **Package upload via API** — push packages using the standard dotnet CLI
- **Basic search** — search packages by name and version
- **Lightweight footprint** — suitable for small deployments and development environments

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  slimget:
    image: emzi0767/slimget:latest
    container_name: slimget
    volumes:
      - ./data:/app/data
    ports:
      - 5002:8080
    restart: unless-stopped
```

### Configuration

SlimGet uses an `appsettings.json` configuration file:

```json
{
  "SlimGet": {
    "PackagePath": "/app/data/packages",
    "DatabasePath": "/app/data/slimget.db",
    "ApiKey": "your-secret-api-key",
    "AllowPackageOverwrite": false,
    "EnableSearch": true
  }
}
```

SlimGet's simplicity makes it quick to deploy but it lacks the advanced features of BaGet — no proxy caching, no multiple database backends, and no symbol server support. It's best for small teams that need a basic internal feed without infrastructure complexity.

## Feature Comparison for Production Use

| Scenario | Recommended | Why |
|---|---|---|
| **Enterprise with proxy caching** | BaGet | Only option with upstream proxy and enterprise database backends |
| **Windows/IIS shop** | NuGet.Server | Native IIS integration, zero database setup |
| **Small team, simple needs** | SlimGet | Minimal setup, modern v3 API, low resource usage |
| **Multi-tenant with auth** | BaGet | API key management and user authentication built in |
| **Offline/air-gapped** | BaGet | Pre-populate cache from upstream, then disconnect |

When evaluating these servers, the most critical factor is the NuGet API version. Visual Studio 2022 and modern dotnet CLI prefer the v3 API, which BaGet and SlimGet support. NuGet.Server only provides the v2 API — it still works but lacks search improvements and performance optimizations of v3.

## Why Self-Host Your Package Registry?

An internal NuGet server gives .NET teams control over their dependency pipeline. Instead of relying on the public registry for every build, cached packages restore instantly from local storage. Custom libraries stay private while still being consumable through standard tooling. And for regulated industries, having a self-hosted server means every package version is tracked, versioned, and auditable.

Self-hosted package registries complement broader infrastructure patterns. If you also manage Go modules, our [Go proxy comparison](../2026-04-30-athens-vs-goproxy-self-hosted-go-module-proxy-guide-2026/) covers Athens and GoProxy. For container images, our [Docker registry guide](../docker-registry-proxy-cache-distribution-harbor-zot-guide/) covers self-hosted image storage and proxy caching. And for a broader view of package management across languages, our [binary repository comparison](../2026-04-28-artifactory-oss-vs-nexus-vs-pulp-self-hosted-binary-repository-guide/) covers universal artifact management.

## FAQ

### What is the difference between NuGet v2 and v3 APIs?

NuGet v2 is a simpler, OData-based API that serves package metadata through XML feeds. NuGet v3 uses JSON-based endpoints, CDN-backed package listings, and provides better search and discovery. Modern Visual Studio and dotnet CLI prefer v3, though both remain supported. BaGet and SlimGet support v3; NuGet.Server only supports v2.

### Can BaGet proxy multiple upstream sources?

Yes. BaGet can be configured to proxy packages from nuget.org and additional upstream feeds. When a package is requested, BaGet checks its local database first, then queries configured upstream sources if not found locally.

### Is BaGet still actively maintained?

BaGet's last significant update was in mid-2024. The project is stable and functional for production use, but new feature development has slowed. For organizations concerned about maintenance velocity, evaluating alternatives or contributing to the project directly is recommended.

### How do I migrate packages from nuget.org to my self-hosted server?

With BaGet's proxy mode, packages are automatically cached on first request. For pre-population, use the `dotnet nuget` CLI to download packages and then push them to your server. Alternatively, use tools like NuGetGallery's package export feature to bulk transfer packages.

### Can I use these servers with Azure DevOps or GitHub Packages?

Self-hosted NuGet servers operate independently of cloud services. However, you can configure your `nuget.config` to include multiple sources — your self-hosted server as primary, with Azure DevOps or GitHub Packages as fallback sources.

### How do I secure my NuGet server?

Use HTTPS via a reverse proxy (Nginx, Traefik, Caddy). Enable API key authentication for package publishing. For BaGet, configure database authentication and restrict API key access. Place the server behind your firewall — NuGet feeds should not be publicly accessible.

### What happens if my NuGet server goes down?

Configure fallback sources in `nuget.config` so that developers can still restore packages from nuget.org if the internal server is unavailable. For BaGet's proxy mode, previously cached packages remain available even if the upstream connection is lost.

### Can I host packages for multiple .NET versions?

Yes. NuGet packages are version-agnostic — a single `.nupkg` file can target multiple .NET frameworks through its target framework monikers (TFMs). Your NuGet server simply stores and serves the files; framework compatibility is handled by the client's restore process.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "BaGet vs NuGet.Server vs SlimGet: Self-Hosted NuGet Package Servers 2026",
  "description": "Compare BaGet, NuGet.Server, and SlimGet for self-hosted NuGet package management. Includes Docker Compose configs, proxy caching setup, and production deployment guides for .NET package servers.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
