---
title: ".NET 10 vs .NET 11 in 2026: The Upgrade Guide Nobody Wrote (and Why .NET 8 and 9 Died on the Same Day)"
date: "2026-11-28"
tags: ["dotnet", "csharp", "upgrade", "self-hosted", "migration"]
draft: false
cover: "/img/screenshots/dotnet-10-upgrade.jpg"
---

On **10 November 2026**, two things happened within hours of each other. .NET 11 shipped. And both .NET 8 and .NET 9 stopped receiving security patches — the same day, on purpose, because Microsoft aligns every STS release's end-of-life with the LTS release that replaces it.

If you are running a self-hosted ASP.NET Core service on .NET 8 right now, you are three weeks into an unsupported runtime. Not "approaching end of life." Unsupported. Every CVE filed against the runtime from here forward has no patch for your version, and the fix is not a config change — it is a framework move.

This guide is the upgrade plan I would hand a team that has one maintenance window and no appetite for a two-week surprise. It covers what actually breaks when you cross into .NET 10, why .NET 11 is *not* an upgrade in the way you think it is, and three migration paths compared on downtime and rollback risk.

## TL;DR: The Quick Verdict

**On .NET 8 or 9: move to .NET 10 LTS, not .NET 11.** .NET 10 is the long-term-support release with three years of patches (through **14 November 2028**) and a mature, battle-tested patch stream at 10.0.15. .NET 11 is Standard Term Support with only two years — and it ends on **exactly the same date** as .NET 10, so choosing it buys you nothing in calendar coverage.

**Already on .NET 10: do not upgrade to 11 for support reasons.** There are none. Upgrade only if you specifically need an .NET 11 feature, and budget for landing on .NET 12 LTS in November 2027 regardless. The trap here is that 10 and 11 share a sunset, so the only thing .NET 11 gives you is a second migration bill for the same deadline.

## .NET release and support status, November 2026

The dates below come from the official release notes in the `dotnet/core` repository, which is where Microsoft publishes the authoritative support windows.

| Release | Type | Released | Latest patch | Support ends | Verdict for production |
|---|---|---|---|---|---|
| **.NET 11** | STS (2 yr) | 2026-11-10 | 11.0.0 | 2028-11-14 | New, no patch history. Only for feature need |
| **.NET 10** | **LTS (3 yr)** | 2025-11-11 | 10.0.15 | 2028-11-14 | **Target this.** 15 patches of maturity |
| .NET 9 | STS | 2024-11-12 | 9.0.23 | **2026-11-10 (EOL)** | No patches. Migrate this sprint |
| .NET 8 | LTS | 2023-11-14 | 8.0.34 | **2026-11-10 (EOL)** | No patches. Was LTS — this one stings |
| .NET 7 | STS | 2022-11-08 | 7.0.20 | 2024-05-14 | Dead for two years |

The repository itself is very much alive: **22,075 stars**, last push **26 November 2026**. Star counts do not matter to your upgrade, but the release cadence does. Microsoft ships a new major every November, and every STS release expires when its successor-plus-one lands. That means the "upgrade every couple of years" habit that worked fine in the .NET Framework era will leave you permanently one cycle out of support.

### The support-window trap: 10 and 11 share a gravestone

Read the table again and notice the two identical dates on the right. .NET 10's end-of-support and .NET 11's end-of-support are both **14 November 2028**.

That is not a typo, and it is not a coincidence — it is the policy. An STS release gets two years; the LTS that precedes it gets three, and they converge. Practically:

- Upgrade 8 → 10: you gain support until November 2028.
- Upgrade 10 → 11: you gain **zero days** of support. You only gain features.
- To get past November 2028 on either line, you must be on **.NET 12 LTS** (expected November 2027).

If your planning document says "we'll go to 11 because it's newer," that document is wrong and it will cost you a second migration for the same deadline.

## What actually breaks when you cross into .NET 10

The official compatibility list for .NET 10 is short, which is exactly why teams get complacent. Short lists in a framework upgrade mean "few breaking changes," not "few affected applications" — a single item on this list can hit every service in your estate.

**1. HTTP warnings promoted to errors.** The runtime now raises errors where it previously logged warnings in specific HTTP paths. Code that has been quietly logging a warning for two years starts throwing. If your services parse or forward headers permissively, this is the item that takes you down at 2 a.m.

**2. HTTP/3 support disabled by default with `PublishTrimmed`.** Trimming plus HTTP/3 was producing broken assemblies, so the combination now defaults to off. If you self-publish trimmed binaries and your load balancer speaks HTTP/3, clients silently fall back to HTTP/2 — no error, just a latency profile change nobody attributes to the upgrade.

**3. Streaming HTTP responses enabled by default in browser HTTP clients.** This changes buffering behavior in `HttpClient` call sites running in browser contexts. Code that assumed a fully buffered `HttpResponseMessage` may now observe partial content during concurrent reads.

**4. `DriveInfo.DriveFormat` returns Linux filesystem types.** On Linux, this property previously reported a generic value; it now returns the real filesystem (for example `ext4`, `xfs`, `overlay`). Any code doing an equality check against the old generic string — a surprisingly common pattern in disk-health endpoints — starts returning "unknown" to your monitoring.

**5. C# 14 overload resolution with span parameters.** Span conversions participate differently in overload resolution, so a method call that used to bind to the `string` overload can now bind to the `ReadOnlySpan<char>` overload. This is the classic source of "it compiles on the new SDK and behaves differently" bugs, and it is invisible in code review.

**6. NuGet audit sources no longer allow insecure HTTP by default, and `NUGET_ENABLE_ENHANCED_HTTP_RETRY` is removed.** If you run an internal NuGet mirror over plain HTTP — extremely common in air-gapped build farms — restores fail until you either add a trusted certificate or explicitly opt out of the audit source. The removed environment variable is the second half: your retry tuning now does nothing.

**7. Entity Framework Core and ASP.NET Core 10 carry their own breaking changes**, including query translation adjustments and middleware pipeline defaults. If you are on EF Core, check the provider's own 10.x notes before the runtime notes, because provider-level breaks land harder than framework-level ones.

## The three migration paths, compared

Once you accept that the target is .NET 10, the question becomes *how*. There are three honest options and one dishonest one (the dishonest one is "just bump the target framework and see what happens").

| Path | Mechanism | Downtime | Rollback | Best for |
|---|---|---|---|---|
| **A. Side-by-side SDK pin** | Install 10.x SDK alongside 8.x/9.x, pin per app with `global.json` | None | Delete `global.json`, old SDK still present | Multi-service repos on different cadences |
| **B. Container rebuild** | Rebuild image on `mcr.microsoft.com/dotnet/sdk:10.0-*` and `aspnet:10.0-*` | Rolling, per-replica | Redeploy the previous image tag | Containerized services — the default answer |
| **C. Runtime-only patch** | Install the 10.x runtime, keep the app compiled for 9 | Minutes | Uninstall runtime package | Emergency CVE response only |

Path C deserves a warning you will not find in the release notes: **it does not work the way people expect.** A framework-dependent app built for `net9.0` will not roll forward to the 10.x runtime by default. You either set a roll-forward policy or you rebuild. And even when roll-forward is forced, the runtime's own breaking changes still apply to code that was never compiled against them. Path C buys you hours, not months.

### Path A: pin the SDK so one repo can host two cadences

If you maintain a monorepo where three services upgrade this month and four next quarter, install the 10.x SDK globally and pin each project. `global.json` is the whole mechanism:

```json
{
  "sdk": {
    "version": "10.0.100",
    "rollForward": "latestFeature",
    "allowPrerelease": false
  }
}
```

Drop that at the root of a service directory and every `dotnet build` under it uses 10.x, while sibling directories keep whatever they were pinned to. Set `"rollForward": "latestFeature"` so patch and feature-band updates land without editing the file every month, but never `"latestMajor"` — that hands your build reproducibility to whatever SDK happens to be installed on the CI runner.

Verify what the machine actually has before you trust the pin:

```bash
dotnet --list-sdks
dotnet --list-runtimes
```

The common failure here is a CI image with only the 9.x SDK. `dotnet build` fails with `SDK not found` rather than silently using the wrong one, which is the good news.

### Path B: rebuild the container image

This is the path for anyone shipping containers, and it is the one with the most predictable rollback: the old image is still in your registry.

The official image tags are published in `dotnet/dotnet-docker`. For .NET 10 the Alpine line is `10.0-alpine3.24`; for .NET 11 it is `11.0-alpine3.24`. A standard multi-stage build:

```dockerfile
# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine3.24 AS build
WORKDIR /src
COPY *.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine3.24 AS final
WORKDIR /app
COPY --from=build /app .
ENV DOTNET_EnableDiagnostics=0 \
    ASPNETCORE_HTTP_PORTS=8080
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "MyService.dll"]
```

Two details that matter more than they look. First, `USER $APP_UID` is set by the official image and running as non-root is now the documented default — if your previous Dockerfile ran as root and wrote to a volume, the rebuild will fail on permissions, not on .NET. Second, if you use native AOT, the tag becomes `11.0-alpine3.24-aot` or `10.0-alpine3.24-aot`; mixing an AOT tag with a non-AOT project produces a publish error that reads like a toolchain problem.

### Path C: the emergency runtime install

For a CVE with a same-day exploit and no time to rebuild, install the 10.x runtime, force roll-forward, and accept the risk knowingly:

```bash
# Debian/Ubuntu, from the Microsoft package feed
sudo apt-get update
sudo apt-get install -y dotnet-runtime-10.0 aspnetcore-runtime-10.0

# Force the app to roll forward onto the newer major
export DOTNET_ROLL_FORWARD=Major
```

`DOTNET_ROLL_FORWARD=Major` is the knob that makes a `net9.0` app run on the 10.x runtime. Use it in a container entrypoint or systemd unit, not globally, because it applies to every .NET process in that environment — including build tools that may not tolerate it.

## Verification: prove the upgrade landed

The most common post-upgrade failure is believing you upgraded. A host can have 8.x, 9.x, and 10.x runtimes installed simultaneously, and a stale `DOTNET_ROOT` or a `PATH` ordering issue will quietly run the old one.

```bash
# What is actually installed
dotnet --list-runtimes | grep -E "Microsoft\.(NETCore|AspNetCore)\.App"

# What a running process actually loaded (Linux)
ls -l /proc/$(pgrep -f MyService.dll | head -1)/exe

# Inside a container
docker exec my-service dotnet --info | head -20
```

Then check the one thing the runtime will not tell you: whether your workload set survived. Major-version upgrades invalidate installed workloads (`android`, `maui`, `wasm-tools`), and a partially restored workload set fails at publish time, not at build time:

```bash
dotnet workload list
dotnet workload repair
```

## Pitfalls that turn a one-hour upgrade into a two-day rollback

**Reinstall workloads before you need them.** Workload manifests are versioned per SDK band. A CI runner that upgrades its base image will report missing workloads mid-pipeline, and `dotnet workload repair` is the fix — but only if the manifest feed is reachable from that runner.

**`PublishTrimmed` plus reflection is still a trap.** Trimming behavior changed with HTTP/3 in this release. If you trim, run your integration suite against the *published* trimmed artifact, not against `dotnet run`. Reflection-discovered serializers and DI registrations fail only in the trimmed output.

**Self-contained vs framework-dependent is a support decision, not a size decision.** Self-contained publishes avoid runtime-installation drift entirely, at the cost of ~70 MB per app. If your upgrade pain comes from hosts with mismatched runtimes, self-contained is the permanent fix:

```bash
dotnet publish -c Release -r linux-x64 --self-contained true \
  -p:PublishSingleFile=true
```

**Do not skip the nullable and analyzer baseline.** C# 14's span overload resolution changes binding in ways that produce no warning by default. Turn on `TreatWarningsAsErrors` *after* the upgrade succeeds, not during it, or you will drown the real signal in pre-existing warnings — except for the HTTP-warning path, which is already an error now.

## Why do the work yourself instead of moving to a managed runtime?

Because the upgrade is not the hard part — knowing what your app actually depends on is, and that knowledge lives in your infrastructure. Managed platform services hide the runtime version until the day they force it, and then you inherit *their* schedule and *their* breaking-change window. A self-hosted ASP.NET Core deployment on your own images lets you pick the week, test the exact tag, and roll back to a byte-identical previous image.

If you are mapping out the rest of the .NET stack while you are in here, our [C# web frameworks comparison](../2026-08-15-csharp-web-frameworks-aspnet-core-servicestack-carter-comparison/) covers what changes when you move off bare ASP.NET Core, the [C# ORM comparison](../2026-07-06-csharp-orm-libraries-entity-framework-core-dapper-nhibernate/) explains why an EF Core 10 upgrade is its own project, and the [C# HTTP client guide](../2026-08-02-csharp-http-client-libraries-restsharp-refit-httpclientfactory/) is worth reading before you touch the HTTP defaults that this release just changed.

## FAQ

**Is .NET 11 faster than .NET 10?**
Marginally, and it is the wrong question. .NET 11 is an STS release whose support ends on the same date as .NET 10 (14 November 2028). You get runtime improvements without additional support coverage, so adopt it only for a specific feature — not as a support strategy.

**Can I upgrade straight from .NET 8 to .NET 11?**
Technically yes — there is no enforced hop requirement across majors. Practically you should not, because you would be landing on a release with zero patch history while skipping the maturity of 10.0.15. Go 8 → 10, then evaluate 11 separately.

**Does .NET 8 still work after end of life?**
It runs, and it will keep running. It will not receive security fixes. Every future runtime CVE remains unpatched on your hosts, which turns a routine patch into a permanent accepted risk that you now have to document for auditors.

**How long does a typical ASP.NET Core 8 to 10 upgrade take?**
For a framework-dependent web API without trimming, an afternoon: bump the target framework, rebuild on the `10.0` SDK, fix the HTTP-warning errors, run the integration suite. Add a day if you use `PublishTrimmed` or native AOT, because both need publish-time verification rather than build-time.

**Do I need to change my Docker base image tags?**
Yes if you rebuild. `mcr.microsoft.com/dotnet/sdk:10.0-alpine3.24` and `aspnet:10.0-alpine3.24` are the current tags; the `10.0-alpine` floating tag resolves to the same family. Pin the specific minor tag if you want reproducible builds.

**What is the safest rollback if the upgrade fails in production?**
For containers, redeploy the previous image tag — that is why Path B is the default recommendation, and why you should never delete the old tag until the new one has survived a full traffic cycle. For in-place hosts, keep the 8.x/9.x runtime installed alongside 10.x so reverting is an environment-variable change rather than a reinstall.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": ".NET 10 vs .NET 11 in 2026: The Upgrade Guide Nobody Wrote (and Why .NET 8 and 9 Died on the Same Day)",
  "description": "A production-focused .NET upgrade guide covering the November 2026 end of support for .NET 8 and 9, the breaking changes in .NET 10, and three migration paths compared by downtime and rollback risk.",
  "datePublished": "2026-11-28",
  "dateModified": "2026-11-28",
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
