---
title: "Umbraco vs OrchardCore vs Piranha CMS in 2026: Which .NET CMS Should You Self-Host?"
date: "2026-10-01"
tags: ["cms", "dotnet", "self-hosted", "comparison", "aspnet-core"]
draft: false
cover: "/img/screenshots/umbraco-backoffice-dashboard.jpg"
---

If you are running a .NET shop, your CMS shortlist is brutal: pay five figures a year for a proprietary platform, or trust a PHP stack your team cannot debug. That gap is exactly why **Umbraco, OrchardCore and Piranha CMS** keep winning enterprise RFPs in 2026 — all three are open source, all three run on ASP.NET Core, and all three can be self-hosted on a $12/month VPS until you actually need scale.

But "open source .NET CMS" is not one product category. Umbraco is a mature commercial-grade platform, OrchardCore is a modular application framework that happens to ship a CMS, and Piranha is a lean, editor-focused CMS built for developers who hate bloat. Pick wrong and you will spend six months fighting the architecture instead of shipping pages.

![Umbraco backoffice dashboard](/img/screenshots/umbraco-backoffice-dashboard.jpg "Umbraco 18 backoffice dashboard with content and health checks")

## Quick Verdict

**Choose Umbraco** if you need a battle-tested platform with a huge editor community, a marketplace of packages, and predictable enterprise support. **Choose OrchardCore** if you want a modular, multi-tenant framework you can bend into a SaaS product. **Choose Piranha CMS** if you want a small, headless-capable CMS you can fully understand in a weekend and deploy as a single container. If you only remember one line: **Umbraco for teams, OrchardCore for platforms, Piranha for products.**

## Head-to-Head Comparison

Live GitHub data pulled on 2026-10-01:

| Dimension | Umbraco | OrchardCore | Piranha CMS |
|---|---|---|---|
| GitHub stars | 5,258 | 8,192 | 2,197 |
| Latest release | 18.2.0 (2026-09-17) | 3.0.1 (2026-07-09) | 12.2 (2026-07-16) |
| License | MIT | BSD-3-Clause | MIT |
| Runtime | ASP.NET Core (long-term supported line) | ASP.NET Core (net10.0 in the official Dockerfile) | .NET 8 + EF Core |
| Database | SQL Server, SQLite (community PostgreSQL via packages) | SQL Server, SQLite, PostgreSQL, MySQL | SQLite, SQL Server, PostgreSQL, MySQL (EF Core providers) |
| Multi-tenant | No (one installation per site) | Yes, first-class tenants | No (headless multi-site via apps) |
| Headless / API | Content Delivery API + Management API | GraphQL + REST (decoupled by design) | REST API, decoupled-ready |
| Official Docker image | Yes (`umbraco/umbraco-cms`) | Community + GitHub Actions images | Community images, template-first workflow |
| Editor experience | Best-in-class, WYSIWYG-first | Powerful but admin-heavy | Clean, deliberately minimal |
| Time to first page | Hours | Days (tenant + recipes setup) | Under an hour |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| Marketing team of 10+ editors, agency handing over the site | **Umbraco** | Mature editor UX, package ecosystem, documented upgrade path |
| Building a multi-tenant SaaS or a product with modular features | **OrchardCore** | Tenants, feature toggles and modules are architectural primitives |
| Shipping a small marketing site or a headless backend for a mobile app | **Piranha CMS** | Tiny footprint, EF Core simplicity, headless API out of the box |
| You must run on SQLite in a single container | **Piranha** or **Umbraco** | OrchardCore wants a real database for production tenants |
| Your team already lives in ASP.NET Core DI and middleware | Any — but **OrchardCore** rewards that knowledge the most | Its module system is idiomatic ASP.NET Core |
| You need GraphQL as a first-class citizen | **OrchardCore** | GraphQL ships as a core module |
| You want the lowest long-term learning curve for a small team | **Piranha CMS** | The whole framework fits in your head |

## Umbraco 18 — The Enterprise Workhorse

Umbraco is the safest bet in this comparison. Version **18.2.0** shipped on **2026-09-17** with **5,258 stars** and an MIT license, and the project has been shipping major releases on a predictable cadence for over a decade. It is the CMS you see in public-sector tenders because it has formal long-term-support lines, a commercial backing company, and an audit trail longer than most startups' entire existence.

Deployment is container-friendly thanks to the official `umbraco/umbraco-cms` image. The project's own documentation is explicit about what you must persist: Umbraco writes logs to `/umbraco/Logs/` and temporary data to `/umbraco/Data/`, and the official guidance is to mount volumes for both rather than rely on the container's writable layer. Here is a production-shaped compose file built from the project's own Docker documentation and the environment variables used in the Umbraco repository's own dev container:

```yaml
services:
  umbraco:
    image: umbraco/umbraco-cms:18.2.0
    ports:
      - "8080:8080"
    environment:
      ASPNETCORE_URLS: "http://+:8080"
      ConnectionStrings__umbracoDbDSN: "Server=db,1433;Database=umbraco;User Id=sa;Password=${DB_PASSWORD};TrustServerCertificate=True;"
      ConnectionStrings__umbracoDbDSN_ProviderName: "Microsoft.Data.SqlClient"
      # Unattended install: the same variables Umbraco's own dev container uses
      Umbraco__CMS__Unattended__InstallUnattended: "true"
      Umbraco__CMS__Unattended__UnattendedUserName: "Admin"
      Umbraco__CMS__Unattended__UnattendedUserEmail: "admin@example.com"
      Umbraco__CMS__Unattended__UnattendedUserPassword: "${ADMIN_PASSWORD}"
    volumes:
      - umbraco-data:/umbraco/Data
      - umbraco-logs:/umbraco/Logs
    depends_on:
      - db

  db:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "${DB_PASSWORD}"
    volumes:
      - mssql-data:/var/opt/mssql

volumes:
  umbraco-data:
  umbraco-logs:
  mssql-data:
```

Two operational details bite people in production. First, if you terminate TLS at a reverse proxy, Umbraco's secure-connection health check and HTTPS validator will fail the app. The documented fix is to disable the `HstsCheck` health check by ID in configuration (`E2048C48-21C5-4BE1-A80B-8062162DF124`) rather than weakening the whole pipeline. Second, do not create or edit templates and stylesheets through the backoffice when running in Docker — the official guidance is to build those into the image and use the Models Builder in "source code" mode, because files written to the container's writable layer disappear on redeploy.

## OrchardCore 3.0 — The Modular Platform

OrchardCore is the most starred project here at **8,192 stars**, and the reason is architectural: it is not really "a CMS", it is a modular ASP.NET Core application framework that ships a CMS on top. Tenants, features, content types, workflows and GraphQL are all first-party modules. Release **3.0.1** landed on **2026-07-09**, and the official build definition already targets **net10.0**.

That power has a price: OrchardCore is the slowest of the three to get to a first rendered page, because you configure a tenant, enable the feature set you want, and wire the content model before an editor ever logs in. The payoff is that multi-tenancy is a primitive rather than a hack — one installation can serve hundreds of sites with isolated content, which is exactly why agencies and SaaS builders pick it.

The repository ships a real multi-stage Dockerfile, and you should reuse its structure rather than improvise. Its key lines publish the CMS web project and expose the app on port 80:

```dockerfile
FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0 AS build-env
WORKDIR /source
COPY ./src ./src
COPY Directory.Build.props .
COPY Directory.Packages.props .
RUN dotnet publish src/OrchardCore.Cms.Web/OrchardCore.Cms.Web.csproj \
    -c Release -o /app --framework net10.0 /p:RunAnalyzers=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS build_linux
EXPOSE 80
ENV ASPNETCORE_URLS=http://+:80
WORKDIR /app
COPY --from=build-env /app/ .
ENTRYPOINT ["dotnet", "OrchardCore.Cms.Web.dll"]
```

The single most common self-hosting mistake is forgetting that OrchardCore persists tenants, media and the Data Protection keys under the app's `App_Data` and `Media` folders. If those are not on a volume or a shared filesystem, you will silently lose encryption keys on every redeploy and your tenants will be unable to decrypt stored secrets. Mount them explicitly, and do not run tenants on SQLite in production — the documentation is candid that SQLite is for development and small single-tenant installs.

![OrchardCore admin content items view](/img/screenshots/orchardcore-admin-content.jpg "OrchardCore admin listing content items after a decoupled CMS setup")

## Piranha CMS 12.2 — The Minimalist

Piranha is what you pick when a 400 MB container and a 40-module admin feels absurd for a brochure site. Version **12.2** was released on **2026-07-16** with **2,197 stars** under MIT, and the framework is deliberately small: a manager UI, content types defined in code, and an optional REST layer for headless use.

Getting started is template-first, straight from the project's README:

```bash
# Install the official project templates
dotnet new install Piranha.Templates

# Create an empty folder, then scaffold a Razor Pages site
mkdir mysite && cd mysite
dotnet new piranha.razor

dotnet run
```

The README carries one genuine trap worth pinning on your wall: **never name the project `Piranha`**, because the resulting namespace collides with the framework packages and `dotnet restore` fails with a circular reference. It sounds trivial until it costs you an afternoon.

Because Piranha is built on Entity Framework Core, the database is just a connection string plus a provider package. SQLite is the default for a reason — a single file-backed database keeps the whole deployment to one container. PostgreSQL and SQL Server are supported by swapping the provider in `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "piranha": "Host=db;Database=piranha;Username=piranha;Password=${DB_PASSWORD}"
  }
}
```

Where Piranha genuinely wins is comprehensibility. A developer can read the content model, the manager extensions and the API surface in an afternoon. That is also its limit: there is no package marketplace comparable to Umbraco's, and no first-class multi-tenant story like OrchardCore's. For a single product or a headless backend, neither matters.

## Pitfalls and Migration Notes

**Do not pick a CMS by star count.** OrchardCore has the most stars and is the wrong answer for a small team that just needs an editable website; Umbraco has fewer stars and a far larger professional editor base.

**Budget for the content model, not the install.** All three install in an afternoon via Docker or the .NET CLI. The real cost is modelling content types, permissions and workflows — that is where projects slip, and where OrchardCore's flexibility can turn into unbounded scope.

**Test your upgrade path before you commit.** Umbraco and OrchardCore both ship frequent major versions; Piranha's majors are smaller in blast radius. Pin versions in your compose file exactly as shown above, and never float `latest` in production.

**Plan media storage deliberately.** Umbraco's docs push external blob storage for media in containerised deployments; OrchardCore keeps media on disk by default; Piranha stores uploads in the configured filesystem. None of them are magic — attach a volume or object storage from day one.

**Reverse proxies change application behaviour.** HTTPS termination, forwarded headers and health checks are the three areas that break first. Read the host's own documentation for these rather than copying a generic Nginx snippet.

If you are comparing content architectures more broadly, our [headless CMS comparison](../2026-05-04-payload-cms-vs-strapi-vs-directus-self-hosted-headless-cms/) covers the JavaScript-side options, and the [Strapi vs Directus vs Ghost guide](../strapi-vs-directus-vs-ghost-headless-cms-guide/) is a useful contrast to a full .NET platform. If your stack is JVM-first, the [application server comparison](../2026-04-27-tomcat-vs-wildfly-vs-gunicorn-self-hosted-application-servers-guide-2026/) is the equivalent trade-off discussion.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Umbraco vs OrchardCore vs Piranha CMS in 2026: Which .NET CMS Should You Self-Host?",
  "description": "Hands-on comparison of Umbraco 18, OrchardCore 3.0 and Piranha CMS 12.2 for self-hosting on .NET: real Docker configs, licenses, database support and selection criteria.",
  "datePublished": "2026-10-01",
  "dateModified": "2026-10-01",
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

## FAQ

**Is Umbraco really free to self-host?**
Yes. The core CMS is MIT-licensed and free to run on your own infrastructure. Costs appear only for optional commercial products in the Umbraco ecosystem and for official cloud hosting, neither of which is required.

**Can OrchardCore run without SQL Server?**
Yes. OrchardCore supports SQLite, SQL Server, PostgreSQL and MySQL. SQLite is fine for development and small single-tenant installs, but production multi-tenant deployments should use a server database for reliability and concurrency.

**Which of the three is the best headless CMS?**
OrchardCore and Piranha are both comfortable headless: OrchardCore ships GraphQL and REST modules, while Piranha exposes a REST API over its EF Core content model. Umbraco added a Content Delivery API, so it is competitive, but its centre of gravity remains the coupled editor experience.

**How long does a self-hosted deployment actually take?**
A running container takes under an hour for all three. The realistic timeline, including content modelling and editor training, is one to two weeks for Piranha, three to six weeks for Umbraco, and one to three months for a serious OrchardCore platform.

**Do I need Kubernetes to run these in production?**
No. A single Docker Compose stack with a mounted data volume and a reverse proxy handles small to medium traffic comfortably. Move to orchestration when you need horizontal scaling or zero-downtime deploys, not before.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
