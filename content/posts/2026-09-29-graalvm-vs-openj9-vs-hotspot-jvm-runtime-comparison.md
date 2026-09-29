---
title: "GraalVM vs OpenJ9 vs HotSpot in 2026: Which JVM Runtime Should You Actually Deploy?"
date: "2026-09-29"
tags: ["java", "jvm", "docker", "performance", "self-hosted"]
draft: false
cover: "/img/screenshots/graalvm-logo.jpg"
---

Your Spring Boot service eats 1.2 GB of RSS to answer 200 requests per second, and your container orchestrator bills you for a pod that spends 40 seconds warming up before it does anything useful. The Java code is fine. The *runtime* underneath it is a decision you probably never consciously made — you inherited whatever `openjdk:17` someone typed into a Dockerfile in 2022.

That decision is worth real money. A JVM runtime controls startup time, resident memory, JIT compilation strategy and peak throughput, and in 2026 there are three genuinely different engines to choose from: **GraalVM**, **Eclipse OpenJ9** and **HotSpot** (the engine inside every standard OpenJDK build). They are not interchangeable, and picking the wrong one for your workload can cost you 3x the memory or 10x the cold start.

## TL;DR / Quick Verdict

- **Deploying containers on Kubernetes with autoscaling, or building CLIs?** Use **GraalVM native image** if you can accept a slower build and some reflection configuration. Millisecond startup, dramatically lower memory.
- **Running long-lived JVM services where memory density is the constraint (many JVMs per host, sidecars, edge boxes)?** Use **Eclipse OpenJ9** with a shared class cache. IBM's own engineering work targets exactly this case.
- **Running anything else — big heaps, heavy throughput, wide library compatibility, zero drama?** Use **HotSpot via Eclipse Temurin**. It is the default for a reason, and the latest LTS builds are genuinely fast.
- **Do not** move a large Spring monolith to native image to "save money" without measuring: the build-time reflection graph is where these projects die.

## Runtime Comparison Table (live GitHub data, September 2026)

| Runtime | Engine | Latest release | Release date | GitHub stars | License |
|---|---|---|---|---|---|
| **GraalVM Community** | Graal JIT + native-image | GraalVM CE 25 Innovation 4 (graal 25.4.4.1.1, JDK 25.0.4.1.1) | 2026-09-22 | 21,719 ⭐ (`oracle/graal`) | GPLv2 + Classpath Exception |
| **Eclipse OpenJ9** | J9 (shared classes, JITServer) | v0.62.0 | 2026-09-15 | 3,546 ⭐ (`eclipse-openj9/openj9`) | EPL 2.0 / Apache 2.0 |
| **HotSpot / Temurin** | C2 JIT (HotSpot) | Temurin 21.0.12.1+1 LTS (JDK 26 build also published) | 2026-08-19 | 23,390 ⭐ (`openjdk/jdk` mainline) | GPLv2 + Classpath Exception |

All three compile the same Java bytecode. What differs is *when* and *how* the machine code gets made, and how much machinery ships alongside it.

![GraalVM Community Edition](/img/screenshots/graalvm-logo.jpg "GraalVM Community Edition — native image and Graal JIT")

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Serverless / scale-to-zero, cold start matters | GraalVM native image | Startup measured in milliseconds, not seconds |
| 20+ JVMs on one 32 GB host | OpenJ9 | Shared class cache and lower per-JVM footprint |
| Sidecar or CLI tool shipped to users | GraalVM native image | Single static binary, no JRE to install |
| Large heap monolith (8 GB+), heavy GC pressure | HotSpot (ZGC / Generational ZGC) | Best-tested low-pause collectors at scale |
| Ancient dependency tree you cannot touch | HotSpot | Zero reflection configuration required |
| Batch jobs on spot instances that start often | OpenJ9 or GraalVM native | Startup cost dominates total runtime |

## GraalVM Community — When You Want the JVM to Disappear

GraalVM's pitch is that the runtime should not be visible at all: either you compile ahead of time into a native executable, or you swap HotSpot's top-tier JIT for the Graal compiler to get better peak optimization on modern workloads.

Native image is the headline. You give up the JIT entirely in exchange for a binary that starts in single-digit milliseconds and does not need a JVM installed:

```dockerfile
# Build stage — official GraalVM Community container image
FROM ghcr.io/graalvm/jdk-community:23.0.0-ol9 AS build
WORKDIR /app
COPY . .
RUN ./mvnw -q -Pnative native:compile -DskipTests

# Runtime stage — no JVM, just the binary
FROM ghcr.io/graalvm/jdk-community:23.0.0-ol9
WORKDIR /app
COPY --from=build /app/target/app /app/app
ENTRYPOINT ["/app/app"]
```

If you prefer to drive `native-image` directly rather than through a build plugin:

```bash
native-image \
  --no-fallback \
  -H:+ReportExceptionStackTraces \
  -march=compatibility \
  -jar target/app.jar app
```

Two flags matter more than the rest. `--no-fallback` makes the build fail loudly instead of silently producing an image that quietly falls back to running on the JVM — without it you can ship a "native" binary that is secretly a slow JVM launcher. `-march=compatibility` keeps the binary portable across CPU generations, which matters if your CI machine has a newer microarchitecture than your production fleet.

The cost is honest and well-documented: reflection, dynamic proxies and resources must be declared in `reflect-config.json` / `resource-config.json`, or replaced with build-time hints. Frameworks with heavy runtime introspection are the ones that hurt. If your app boots and immediately queries a database through a few well-known libraries, the migration is usually a day. If it scans the classpath at startup and wires things dynamically, budget a week and a lot of patience.

For long-running services where you want the Graal JIT but not the native-image build, GraalVM also runs in JVM mode (`java -XX:-UseJITServer ...` style deployments, or simply `java -jar` on the GraalVM JDK). You keep full compatibility and get the Graal compiler as the top tier — a much lower-risk way to try the runtime.

## Eclipse OpenJ9 — Built for Density, Not for Benchmarks

![Eclipse OpenJ9](/img/screenshots/openj9-logo.jpg "Eclipse OpenJ9 — the runtime optimized for small footprint and fast startup")

OpenJ9 comes from IBM's J9 lineage and, unusually for a JVM, it is *optimized against memory footprint first*. The design choices are visible in three options you should know:

```bash
# Shared class cache: parse and verify class metadata once, reuse across JVMs
java -Xshareclasses:name=myapp,cacheDir=/var/cache/j9 -jar app.jar

# Prefer fast startup over peak throughput (pairs well with short-lived jobs)
java -Xquickstart -jar app.jar

# Tune for virtualized/containerized hosts
java -Xtune:virtualized -XX:MaxRAMPercentage=75 -jar app.jar
```

The shared class cache is the interesting one. On a host running many JVMs of the same application, each process can map the same prepared class data instead of rebuilding it in its own heap. That is a memory saving HotSpot's CDS narrows but does not match, and it also cuts startup.

OpenJ9 also ships **JITServer**, which moves the JIT compiler out of each JVM into a shared server process:

```bash
# Server process (one per host or cluster)
java -XX:JITServerPort=38400 -XX:JITServer=...
# Client JVMs connect to it instead of compiling locally
java -XX:+UseJITServer -XX:JITServerAddress=localhost -jar app.jar
```

The trade-off is that you now operate another moving part, and JITServer expects version-matched builds. It is a legitimately powerful pattern for fleets of identical JVMs and a bad idea for a single service.

Where OpenJ9 is weaker: it is not the runtime most libraries are tested against, and peak throughput on long-running compute-heavy workloads has traditionally trailed HotSpot's C2 — IBM's own documentation frames the runtime around footprint and start-up, not raw throughput leadership. Pick it for density, not for winning benchmarks.

## HotSpot (Eclipse Temurin) — The Boring, Correct Default

HotSpot is the engine inside OpenJDK, so "HotSpot" is really shorthand for "whatever the standard builds ship". Use Temurin builds and you get a well-tested, vendor-neutral distribution with a published tag list:

```dockerfile
FROM eclipse-temurin:26-jdk-noble
WORKDIR /app
COPY target/app.jar /app/app.jar
# Container-aware heap sizing + low-pause collector
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+UseZGC -XX:+ExitOnOutOfMemoryError"
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

For containerized services, three flags carry most of the value:

- `-XX:MaxRAMPercentage=75` — size the heap as a percentage of the container limit instead of guessing `-Xmx` per environment. The JVM has been container-aware for years, but only if you let it be.
- `-XX:+UseZGC` — a concurrent collector with sub-millisecond pause targets, available for production use on modern LTS releases. Generational mode is the default direction for new deployments.
- `-XX:ExitOnOutOfMemoryError` — fail fast instead of letting a half-dead pod limp along and blow up your request latency.

For tiny sidecars where startup dominates, `-XX:+UseSerialGC` often beats the big collectors: fewer GC threads means less contention on a 1-vCPU limit. And if the JVM misreads your cgroup CPU quota (a classic in managed Kubernetes), pin it explicitly with `-XX:ActiveProcessorCount=2`.

HotSpot's real advantage is not a flag — it is that every library, agent, profiler and tutorial on earth assumes it. When something breaks at 3 a.m., the first page of search results will describe HotSpot behaviour.

## Migration and Coexistence Notes

You do not have to bet the whole fleet on one runtime. Running GraalVM native for new stateless services while keeping HotSpot for the stateful monolith is normal and safe: the artifacts are independent, and your container registry does not care which engine produced them.

Three traps worth avoiding:

1. **Comparing startup times without warming the filesystem.** First-start numbers on a cold image are dominated by page cache, not the JVM. Run each candidate three times and discard the first.
2. **Judging memory by `-Xmx`.** RSS is what your orchestrator bills and what gets OOM-killed. Measure RSS under load, not heap settings.
3. **Assuming native image shrinks everything.** For a small service, the JVM overhead is real and native image wins clearly. For a fat application with a large native image, the binary itself can be hundreds of megabytes and the win narrows considerably.

## FAQ

**Does GraalVM native image support Spring Boot?**
Yes. Spring Boot has first-class ahead-of-time support, and the Maven/Gradle native plugins generate the reachability metadata for you. The main constraint is that conditional configuration evaluated at runtime must move to build time, which occasionally forces code changes.

**Is Eclipse OpenJ9 still actively maintained?**
Yes — v0.62.0 was released on 2026-09-15 and the repository is actively committed to. It is distributed both as Eclipse OpenJ9 builds and as IBM Semeru Runtime builds.

**Can I just switch from Temurin to OpenJ9 by changing the base image?**
Usually, yes, if you stick to standard JVM options. Non-standard flags (`-Xshareclasses`, `-Xtune:*`, `-Xquickstart`) are OpenJ9-specific, and HotSpot-specific flags like `-XX:+UseZGC` will be rejected. Keep the flags in environment variables per runtime, not baked into application code.

**Which runtime is fastest for a long-running, high-throughput API?**
In most published and reproducible comparisons, HotSpot and GraalVM's JVM mode lead on sustained throughput for large-heap workloads, while native image wins decisively on startup and memory. OpenJ9's advantage is footprint and start-up, not peak throughput — measure your own workload before trusting any table, including this one.

**Do I need to recompile my application for a different JVM?**
No. All three run standard Java bytecode. Only GraalVM native image requires an ahead-of-time compile step; GraalVM in JVM mode, OpenJ9 and HotSpot all consume the same JAR.

**What about JDK version availability?**
Temurin publishes very current builds (a JDK 26 image tag is already on Docker Hub), GraalVM CE tracks recent JDKs (JDK 25.0.4.1.1 in the September 2026 release), and OpenJ9 releases track the OpenJDK LTS lines it supports. Pin an explicit tag in production rather than `latest`.

For related reading, see our [JVM build tools comparison](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/) and the [Java web frameworks guide](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/). If you are tuning container images rather than runtimes, the [base image comparison](../2026-05-11-container-base-images-alpine-distroless-debian-slim-comparison/) covers that decision.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GraalVM vs OpenJ9 vs HotSpot in 2026: Which JVM Runtime Should You Actually Deploy?",
  "description": "Runtime comparison of GraalVM Community, Eclipse OpenJ9 and HotSpot (Eclipse Temurin) with live 2026 release data, Docker examples, container flag tuning and a scenario decision matrix.",
  "datePublished": "2026-09-29",
  "dateModified": "2026-09-29",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
