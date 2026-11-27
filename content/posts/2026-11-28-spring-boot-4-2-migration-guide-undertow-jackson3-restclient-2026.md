---
title: "Spring Boot 4.2 Migration Guide 2026: Undertow Removed, Jackson 3 Default, RestTemplate Sunset"
date: "2026-11-28"
tags: ["spring-boot", "java", "upgrade", "self-hosted", "migration"]
draft: false
cover: "/img/screenshots/spring-boot-4-2-logo.jpg"
---

Spring Boot 3.5 left open-source support on **30 June 2026**. Spring Boot 4.0 — the release most teams upgraded *to* when they finally moved off 3.5 — leaves support on **31 December 2026**, five weeks from today. And 4.2.0 went GA on **20 November 2026** with a change that will surprise anyone who waited: `RestTemplate` and `TestRestTemplate` are now formally deprecated, because Spring Framework 7.1 deprecated them.

That is an unusual spot to be in. The version you upgraded to last winter is itself about to expire, and the replacement for the version after that already has a deprecation clock on it. This guide maps the actual requirements, the removals that break compilation, and the property renames that break *runtime* — which is the harder category, because `mvn verify` passes and the app fails to start in staging.

## TL;DR: The Quick Verdict

**If you are on 3.5: skip 4.0 entirely and go to 4.1 or 4.2.** The jump is the same size in breaking-change terms, but 4.0's support window closes in five weeks. **If you are on 4.0: move to 4.2 now** — 4.1 is the safe intermediate if your dependency tree is messy, since 4.1 keeps `RestTemplate` un-deprecated. **If you are on 4.1: 4.2 is mostly a rename task** plus multipart limits and relative-redirect defaults that change behavior silently. Run `spring-boot-properties-migrator` before you trust any config file, and delete Undertow from your POM before you do anything else — it cannot work on a Servlet 6.1 baseline.

## Spring Boot support status, November 2026

| Release | Latest patch | GA | Java range | Framework | OSS support ends | Verdict |
|---|---|---|---|---|---|---|
| **4.2** | 4.2.0 | 2026-11-20 | 17 – 27 | 7.1 | 2027-12-31 | **Target.** Nine days old, longest runway |
| 4.1 | 4.1.3 | 2026-06-30 | 17 – 26 | 7.1 | 2027-07-31 | Safe intermediate, still supported |
| 4.0 | 4.0.10 | 2025-11-30 | 17 – 25 | 7.0 | **2026-12-31** | Leave it. Five weeks left |
| 3.5 | 3.5.16 | 2025-05-31 | 17 – 25 | 6.2 | **2026-06-30 (EOL)** | Unsupported for five months |

The project itself is healthy — **81,983 stars** on `spring-projects/spring-boot`, last commit **27 November 2026**; Spring Framework is at **60,335 stars** with the same-day activity. The problem is not project health, it is that the OSS support windows are now short enough that "upgrade every two years" no longer fits inside one.

## What 4.0 changed structurally, and why it still matters in 4.2

Boot 4 replaced several large jars with a modular layout: every module is named `spring-boot-<technology>`, every test module is `spring-boot-<technology>-test`, and the starters were realigned to match. If you jump from 3.5 straight to 4.2 you inherit all of it at once, so it is worth understanding the dependency mapping before you touch code.

| What you are wiring | Starter in Boot 4.x | Notes |
|---|---|---|
| Imperative HTTP client (`RestClient`, `RestTemplate`) | `spring-boot-starter-restclient` | Plus `-test` variant for `TestRestTemplate` |
| Reactive `WebClient` | `spring-boot-starter-webclient` | Plus `-test` variant |
| Tomcat | `spring-boot-starter-tomcat` | Still the default servlet container |
| Jetty | `spring-boot-starter-jetty` | Servlet 6.1 capable; 4,102 stars on the Jetty repo |
| Undertow | — | **Removed.** No starter exists |
| Kotlin Serialization | `spring-boot-starter-kotlinx-serialization-json` | Contributes a configured `Json` bean |

Two consequences people miss. First, **auto-configuration classes are no longer public API** — every public member except constants was removed. If your code extends or calls a `*AutoConfiguration` class directly (it happens in test slices), it will not compile. Second, `org.springframework.boot.env.EnvironmentPostProcessor` was replaced by `org.springframework.boot.EnvironmentPostProcessor`; the old interface survives in deprecated form only, so `spring.factories` entries keep working for now but are debt.

## The removals that break the build immediately

**Undertow is gone.** Boot 4 requires a Servlet 6.1 baseline and Undertow is not compatible with it, so the starter and embedded-server support were dropped. Two migration options: accept Tomcat (zero code change, just delete the exclusion), or move to Jetty (`spring-boot-starter-jetty`). Do not try to force Undertow by pinning an older servlet API — you will be fighting the framework's own baseline checks.

**Embedded launch scripts are gone.** The trick that produced "fully executable" jars with a shell preamble stamped into them has been removed. If your deploy pipeline does `java -jar` on a jar that was made executable and launched as `./app.jar`, switch to `java -jar` or a proper service unit. This one hits systemd templates and old Dockerfiles more often than application code.

**Spring Session for Hazelcast and MongoDB** are no longer supported directly inside Boot — the auto-configuration was removed. You can still use those stores, but the wiring becomes yours. **Spock integration** was also dropped, because Spock does not yet support Groovy 5. If your test suite is Groovy-based, that is a hard blocker on 4.x and worth discovering in week one rather than week four.

**Pulsar** is a two-stage story: reactive auto-configuration was removed in 4.0, and in 4.2 the Pulsar support including `spring-boot-starter-pulsar` is deprecated. If Pulsar is central to your architecture, treat 4.2 as a scouting release and plan accordingly.

## Jackson 3 is the default — the package rename is the work

Boot 4 prefers Jackson 3. The group ID and package root move from `com.fasterxml.jackson` to `tools.jackson`, while annotation packages stay at `com.fasterxml.jackson.annotation`. That split is the entire gotcha: your `@JsonProperty` imports keep compiling, and your `ObjectMapper` construction/`JsonMapper` wiring does not.

Boot still manages Jackson 2 dependencies and will happily run a Jackson 2 `ObjectMapper` alongside its Jackson 3 auto-configuration if a library forces it. So the migration is usually incremental: get the app booting with mixed versions first, then eliminate Jackson 2 module by module. If you serialize with Kotlin, the new `spring-boot-starter-kotlinx-serialization-json` is often a cleaner exit than porting every DTO to Jackson 3.

```xml
<!-- pom.xml: the version you actually want in November 2026 -->
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>4.2.0</version>
  <relativePath/>
</parent>

<properties>
  <java.version>17</java.version>
</properties>
```

```groovy
// build.gradle — same version, plugins DSL
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.2.0'
    id 'io.spring.dependency-management' version '1.1.7'
}
java { toolchain { languageVersion = JavaLanguageVersion.of(17) } }
```

## RestTemplate is deprecated — what to do about it

Framework 7.1 deprecated `RestTemplate`, and Boot 4.2 followed by deprecating its supporting infrastructure and `TestRestTemplate`. Deprecated is not removed: your 4.2 upgrade will still compile and run. But this is the clearest signal yet that `RestClient` is the imperative client going forward, and the refactor is mechanical enough to do in an afternoon.

```java
// Before: RestTemplate, now deprecated in 4.2
RestTemplate rest = new RestTemplate();
Quote quote = rest.getForObject("https://api.example.com/quotes/42", Quote.class);

// After: RestClient — same blocking model, fluent API, no extra dependency
RestClient client = RestClient.builder()
        .baseUrl("https://api.example.com")
        .defaultHeader("Accept", "application/json")
        .build();

Quote quote = client.get()
        .uri("/quotes/{id}", 42)
        .retrieve()
        .body(Quote.class);
```

In tests, swap `TestRestTemplate` for `RestTestClient` or `WebTestClient` depending on whether the slice is servlet or reactive. The important part is to do it *while* both exist, not after the removal release.

## Configuration properties: the silent runtime failure

Renamed properties do not fail compilation. They fail at startup with a binding error, or worse, silently keep a default. Boot ships a migrator for exactly this:

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-properties-migrator</artifactId>
  <scope>runtime</scope>
</dependency>
```

Add it, boot the app in staging, and read the diagnostics it prints at startup. Remove the dependency before you ship. The renames I would check by hand regardless, because they change behavior rather than just names:

```yaml
server:
  # 4.2: renamed — the old key is deprecated
  request:
    header:
      forwarded:
        strategy: native
  tomcat:
    servlet:
      # 4.2: defaults to true now — relative redirects behind a proxy
      use-relative-redirects: true
spring:
  threads:
    virtual:
      enabled: true   # JDK-HttpClient-backed auto-configured clients now use virtual threads
```

`management.metrics.observations.ignored-meters` was removed and `LongTaskTimer` is no longer configured by default, so any dashboard built on that meter needs a new source. Janino dependency management was removed after Logback dropped Janino support — if you relied on Boot to pin Janino, pin it yourself or drop the conditional logging config that needed it. WebFlux multipart requests now have default limits, which will reject uploads that used to pass.

## API versioning is finally built in

This is the one genuinely new capability worth adopting in 4.2: API versioning is auto-configured for Spring MVC and WebFlux, driven by properties rather than custom `HandlerInterceptor` code.

```yaml
spring:
  mvc:
    apiversion:
      enabled: true
      default-version: 1
      use:
        header: X-API-Version
```

Behind a proxy or gateway, also set `server.request.header.forwarded.strategy` deliberately — Framework 7.1 now requires you to choose between the standard `Forwarded` header and the legacy `X-Forwarded-*` family instead of silently supporting both.

## Decision matrix: which version to target

| Your situation | Target | Why |
|---|---|---|
| On 3.5, heavy Groovy/Spock test suite | **4.1, with a Spock exit plan** | 4.x drops Spock integration; 4.1 buys time with support into mid-2027 |
| On 3.5, standard MVC + JPA | **4.2 directly** | Same breaking set as 4.0, longest support runway |
| On 4.0 with clean dependencies | **4.2** | 4.0 expires 31 Dec 2026 |
| On 4.1, `RestTemplate` everywhere | **4.1 for now, `RestClient` refactor next** | 4.2 deprecates but does not remove; refactor on your schedule |
| Running Undertow for its non-blocking behavior | **Jetty** | Servlet 6.1 compatible and actively maintained |
| GraalVM native images | **4.2 + GraalVM 25+** | Native image baseline moved; older GraalVM will not build |

## Pitfalls I would put in the change ticket

1. **Do not pin Spring Framework yourself.** Boot 4 requires Framework 7.x specifically; a stray 6.2 BOM in a parent POM produces `NoSuchMethodError` at startup, not a dependency convergence error.
2. **`spring-boot-properties-migrator` is temporary.** Leaving it in production logs deprecation noise on every boot and masks the real configuration state.
3. **Relative redirects now default to `true`** on Tomcat. If your app constructs absolute redirect URLs and terminates TLS at a proxy, verify the Location header before and after.
4. **Multipart limits are new defaults in WebFlux.** Upload tests that passed on 4.1 can fail on 4.2 without a single code change.
5. **Auto-configuration is no longer extensible API.** Any subclass of a `*AutoConfiguration` class breaks; the supported extension point is a bean or a `BeanPostProcessor`.
6. **Kotlin 2.2 minimum.** If you build Kotlin and your plugin pins 1.9, the app compiles and the runtime metadata mismatches — bump the Kotlin plugin first.
7. **Test slices moved.** With modular test jars, `@WebMvcTest`-style slices may need the new `spring-boot-<technology>-test` dependency explicitly on the test classpath.

## FAQ

**Is Spring Boot 4.2 compatible with Java 17?**
Yes. Boot 4.2 supports Java 17 through Java 27, so you do not have to move the JDK to upgrade the framework. Boot 4.0 requires Java 17 or later as well; the Java floor has not moved since 3.x, which is why the framework upgrade is usually cheaper than teams expect.

**Can I upgrade from 3.5 straight to 4.2?**
Yes, and for most teams it is the better call than stopping at 4.0 — the breaking changes are the same set, and 4.0's open-source support ends 31 December 2026. Stop at 4.1 only if a specific blocker (Spock, Undertow, a Hazelcast session store) needs its own project plan.

**Why was Undertow removed instead of updated?**
Because Boot 4 requires a Servlet 6.1 baseline and Undertow is not compatible with it. Rather than ship a container that cannot satisfy the baseline, the starter and embedded-server support were removed. Tomcat remains the default; Jetty is the supported non-Tomcat option.

**Does the RestTemplate deprecation break my 4.2 build?**
No. Deprecated classes still compile and run in 4.2. The deprecation exists because Spring Framework 7.1 deprecated `RestTemplate` in favor of `RestClient`; removal will happen in a later generation, so treat it as a scheduled refactor rather than an emergency.

**Where did Jackson 2 go?**
Nowhere yet. Boot 4 prefers Jackson 3 (`tools.jackson` package root, annotations still under `com.fasterxml.jackson.annotation`) and continues to manage Jackson 2 so libraries that need it still resolve. The migration is usually mixed-mode first, then eliminate Jackson 2 module by module.

**How do I find renamed configuration properties?**
Add `spring-boot-properties-migrator` as a runtime dependency, boot in staging, and read the startup diagnostics — it both reports and temporarily maps old keys. Remove it before production and commit the corrected YAML.

If you are still deciding whether Spring is the right framework at all, our [Java web frameworks comparison](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/) puts Boot next to Quarkus, Micronaut, Helidon and Javalin with the same kind of build-and-run detail. For build-side changes that interact with the Boot plugin, see the [JVM build tools comparison](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/), and if your migration touches JSON serialization end to end, the [Java JSON libraries guide](../2026-06-22-java-json-libraries-jackson-gson-moshi-guide/) covers the Jackson 2 to 3 package split in more depth.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Spring Boot 4.2 Migration Guide 2026: Undertow Removed, Jackson 3 Default, RestTemplate Sunset",
  "description": "A practical Spring Boot 4.2 migration guide for 2026: support windows for 3.5, 4.0, 4.1 and 4.2, the Undertow removal, Jackson 3 package rename, RestClient migration and configuration property renames.",
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
