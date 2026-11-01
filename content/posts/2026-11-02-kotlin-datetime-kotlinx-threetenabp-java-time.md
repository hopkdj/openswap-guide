---
title: "kotlinx-datetime vs ThreeTenABP vs java.time in 2026: The Kotlin Date Trap Nobody Documents"
date: "2026-11-02"
tags: ["kotlin", "android", "datetime", "jvm", "developer-tools"]
draft: false
description: "kotlinx-datetime 0.8, ThreeTenABP and the built-in java.time compared for Kotlin and Android in 2026 — including the 0.8.0 Instant migration that breaks builds."
---

Here is a bug that ships to production more often than any other in Kotlin: a meeting scheduled for 9:00 tomorrow shows up at 8:00 or 10:00 for half your users. Nothing crashed, no test failed, and the code looked correct. Someone stored a `LocalDateTime` and later converted it to an instant using the *server's* zone.

Kotlin has three ways to handle dates — kotlinx-datetime, ThreeTenABP, and plain `java.time` — and the differences are not cosmetic. They differ in API, in minimum SDK, in thread-safety guarantees, and in what happens when you upgrade a minor version.

## TL;DR — Quick Verdict

- **Kotlin Multiplatform, or a new Android project on minSdk 26+?** Use **kotlinx-datetime** (v0.8.0). It is the only option that works identically on JVM, Android, iOS and JS.
- **Stuck supporting Android API 21–25 and cannot enable desugaring?** Use **ThreeTenABP** (1.4.9). It is the JSR-310 backport that made Android date handling sane before API 26.
- **Plain JVM backend?** Use **`java.time`** directly. It is in the JDK, it needs no dependency, and it is what the other two are built on.
- **Do not** mix all three in one module. The conversion boilerplate will outlive the feature you were building.

## The Real Numbers (fetched November 2026)

| | kotlinx-datetime | ThreeTenABP | java.time (JSR-310) |
|---|---|---|---|
| Repo | `Kotlin/kotlinx-datetime` | `JakeWharton/ThreeTenABP` | OpenJDK (platform) |
| Stars | **2,824** | **3,544** | n/a |
| Version | **0.8.0** (2026-05-07) | **1.4.9** | ships with JDK 8+ |
| Last commit | Oct 2026 | Aug 2025 | continuous |
| License | Apache-2.0 | Apache-2.0 | GPLv2+CE |
| Platforms | JVM, Android, Native, JS, Wasm | Android only | JVM |
| API style | Kotlin-idiomatic, multiplatform types | Java types, backported | Java types |
| Minimum SDK | any (with desugaring caveats) | API 14+ | API 26+ on Android |
| Dependency size | small, KMP artifacts | small | zero |

ThreeTenABP's last release being 2025 is not neglect — the JSR-310 backport is feature-complete. It exists because Android shipped without `java.time` until API 26, and that gap will stay closed.

## Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Kotlin Multiplatform shared module | **kotlinx-datetime** | Only option compiling to iOS/JS/Native |
| Android minSdk 21–25, desugaring disabled | **ThreeTenABP** | Backport with the same API as `java.time` |
| Android minSdk 26+ | **`java.time`** | No dependency, no wrapper |
| Android with core library desugaring enabled | **`java.time`** | Desugaring already provides the API on old devices |
| Spring Boot / Ktor backend | **`java.time`** | Library ecosystem expects it |
| Shared module used by both KMP and Android | **kotlinx-datetime** + convert at the boundary | Keep one type per layer |

## kotlinx-datetime — Multiplatform by Design

kotlinx-datetime gives you `Instant`, `LocalDate`, `LocalDateTime`, `TimeZone` and `DateTimePeriod` as Kotlin types that compile everywhere. If your shared module needs to compute "the start of next month in the user's time zone", this is the tool.

```kotlin
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-datetime:0.8.0")
}
```

Current usage on 0.8.x:

```kotlin
import kotlin.time.Clock
import kotlin.time.Instant
import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.TimeZone
import kotlinx.datetime.TimeZoneContext
import kotlinx.datetime.toLocalDateTime

val now: Instant = Clock.System.now()
val inUtc: LocalDateTime = now.toLocalDateTime(TimeZone.UTC)

val berlin = TimeZoneContext.System.get("Europe/Berlin")
val local: LocalDateTime = now.toLocalDateTime(berlin)
```

**This is where people lose an afternoon.** In 0.8.0, `Instant` and `Clock` moved to `kotlin.time` — the types are now `kotlin.time.Instant` and `kotlin.time.Clock`, and time zone lookups go through `TimeZoneContext` rather than the old static `TimeZone.of(...)` shape. Code written against 0.6 or 0.7 will either fail to compile or, worse, compile against a deprecated alias in a different package and produce confusing overload-resolution errors.

Practical rule: **pin the version and read the changelog before upgrading.** kotlinx-datetime is pre-1.0 and has changed its type locations across minor releases. Semantic-versioning expectations do not apply.

What it does well:

- `LocalDate.plus(DateTimePeriod(months = 1))` handles month arithmetic correctly, including 31 January plus one month.
- Conversions are explicit — there is no implicit system default zone, which is why the bug from the intro is harder to write.
- It serializes cleanly with kotlinx-serialization using ISO-8601 strings when you register the right serializers.

What it does not do: format dates for humans. There is no `DateTimeFormatter` equivalent. You either convert to `java.time` on JVM or use `kotlinx-datetime`'s ISO formatting plus your own presentation layer. That is a real limitation for apps that show "3 hours ago" or locale-aware month names.

## ThreeTenABP — The Android Backport That Still Matters

ThreeTenABP packages the JSR-310 backport (`threetenbp`) for Android, with time zone data loaded from the APK instead of the platform. That last detail is the reason it is still installed in apps that target API 26+: it ships its own tzdb, so a device with stale zone data still computes correctly.

```kotlin
dependencies {
    implementation("com.jakewharton.threetenabp:threetenabp:1.4.9")
}
```

```kotlin
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        AndroidThreeTen.init(this)
    }
}
```

Then the API is exactly `java.time`:

```kotlin
import org.threeten.bp.Instant
import org.threeten.bp.ZoneId
import org.threeten.bp.format.DateTimeFormatter

val now = Instant.now()
val tokyo = now.atZone(ZoneId.of("Asia/Tokyo"))
val label = tokyo.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))
```

The trap: `org.threeten.bp.*` types are **not** `java.time.*` types. They do not interoperate. If a library returns `java.time.Instant` and your code uses `org.threeten.bp.Instant`, you write conversion functions everywhere — and every one of them is a place to lose a zone.

If you control the build, you probably do not need ThreeTenABP in 2026. **Core library desugaring** gives you `java.time` on old API levels, is supported by AGP, and avoids a parallel type hierarchy:

```kotlin
android {
    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.5")
}
```

The cost is a slightly larger DEX and build configuration that must be consistent across every module. The benefit is one date API in the entire codebase. For most teams that trade is worth it; ThreeTenABP remains the right answer only when desugaring is blocked by an old toolchain or a vendor build.

## java.time — The Baseline You Should Default To

On the JVM there is no reason to add a dependency. `java.time` is immutable, thread-safe, and correctly handles DST gaps and overlaps.

```kotlin
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

val instant: Instant = Instant.now()
val zone = ZoneId.of("America/New_York")
val zoned = instant.atZone(zone)

// future events: keep the zone, do not pre-compute the instant
val meeting = LocalDate.parse("2026-11-05").atTime(9, 0).atZone(zone)
```

Two design rules that prevent the majority of date bugs:

**Rule 1 — Past events → `Instant`. Future events → zoned date-time.** A past event happened at a fixed point in time; store the instant. A future event is a *human agreement* ("9:00 in New York"), and if the rules change before then, the event should move. Converting future events to instants too early bakes in a decision that may become wrong — this is why kotlinx-datetime's docs warn against it too.

**Rule 2 — Never use the default zone implicitly.** `LocalDateTime.now()` on a server in UTC and a laptop in UTC+8 produce different values from identical code. Always pass `Clock.systemUTC()` or an explicit `ZoneId`.

`java.time` also gives you the formatting and parsing layer everyone eventually needs: `DateTimeFormatter.ofPattern`, `ofLocalizedDateTime(FormatStyle.MEDIUM)`, and `ZoneId.SHORT_IDS` for legacy three-letter codes (with all their ambiguity).

## Interop Without Losing Your Mind

If you use kotlinx-datetime in a shared module and `java.time` on the JVM, convert at the boundary — never in the middle of business logic:

```kotlin
// KMP -> JVM
fun kotlin.time.Instant.toJavaInstant(): java.time.Instant =
    java.time.Instant.ofEpochSecond(epochSeconds, nanosecondsOfSecond.toLong())

// JVM -> KMP
fun java.time.Instant.toKotlinInstant(): kotlin.time.Instant =
    kotlin.time.Instant.fromEpochSeconds(epochSecond, nano)
```

Converting through epoch seconds and nanoseconds is lossless and unambiguous. Converting through strings is not — the formatting choice silently truncates sub-second precision, and that shows up later as "duplicate" records that differ by microseconds.

For serialization, use ISO-8601 everywhere on the wire and convert at the edges. If you use kotlinx-serialization, our [Kotlin serialization libraries comparison](../2026-07-13-kotlin-serialization-libraries-kotlinx-moshi-klaxon/) covers the serializer registration details, and the [datetime parsing libraries roundup](../2026-06-20-self-hosted-datetime-parsing-libraries-dateparser-chrono-jodatime-dateutil/) covers the parsing side across languages. Backend teams building the API in front of these apps will find the HTTP client trade-offs in our [Ktor vs Fuel vs http4k comparison](../2026-08-01-kotlin-http-clients-ktor-fuel-http4k-comparison/) relevant when choosing how to send those payloads.

## Pitfalls That Actually Bite

**1. The 0.8.0 type move.** `kotlinx.datetime.Instant` → `kotlin.time.Instant`, and `TimeZone.of()` → `TimeZoneContext.System.get()`. Upgrade one dependency at a time and recompile the whole module graph; stale transitive pins cause "unresolved reference" errors that look like IDE problems.

**2. DST gaps are not errors.** In a zone that skips 02:00–03:00, `LocalDateTime` of 02:30 simply does not exist. `atZone()` silently shifts it forward. If your scheduling feature promises "9:00 local", test in a zone with DST and in one without (Asia/Tokyo).

**3. Ambiguous local times happen twice a year.** During a fall-back hour, 01:30 occurs twice. `atZone()` picks the earlier offset; if that matters for billing or attendance, store the offset explicitly.

**4. Time zone database staleness.** Governments change rules with little notice. ThreeTenABP ships tzdb in the APK; `java.time` relies on the JDK's copy; kotlinx-datetime relies on the platform. Any of them can be months behind on an old device. For scheduling features, validate against a server that maintains its own tzdb.

**5. `System.currentTimeMillis()` is not a date API.** Millisecond longs lose the zone entirely and turn into unreadable debugging sessions. Use `Instant` and convert for storage only.

**6. Duration formatting is missing from kotlinx-datetime.** There is no "2 hours 15 minutes" formatter. You either use `java.time.Duration` on JVM or write the presentation logic. Budget for it — it is always more work than expected because of pluralization and locale.

**7. Comparing dates with `==` across types.** `LocalDate` equals only `LocalDate`. Comparing a `LocalDateTime` to a `LocalDate` does not do what you want, and the compiler will not stop you when types are inferred.

## FAQ

**Which library should a new Kotlin Multiplatform project use in 2026?**
kotlinx-datetime 0.8.0. It is the only option that compiles to JVM, Android, iOS, JS and Wasm with the same API. Pin the version and read the release notes before upgrading, because the library is still pre-1.0.

**Do I still need ThreeTenABP on Android?**
Only if you cannot enable core library desugaring or must support API levels below 26 on an old toolchain. On minSdk 26+, `java.time` is available natively. With desugaring enabled, `java.time` also works on older devices.

**Why did my code break after upgrading kotlinx-datetime to 0.8.0?**
Because `Instant` and `Clock` moved to the `kotlin.time` package and time zone lookups go through `TimeZoneContext`. Update imports across the whole module graph, and check that no dependency pins an older version transitively.

**Should I store timestamps as `Instant` or `LocalDateTime` in my database?**
Events that already happened: `Instant` (or a UTC timestamp column). Future scheduled events: store the local date-time plus the zone identifier, and resolve to an instant as late as possible.

**Is `java.time` thread-safe?**
Yes. All core types are immutable, and `DateTimeFormatter` is immutable and thread-safe — unlike the old `SimpleDateFormat`, which was the source of countless concurrency bugs.

**Can I use kotlinx-datetime on a plain JVM backend?**
You can, but you gain little. It adds a dependency without adding capability the JDK lacks, and most backend libraries expect `java.time` types. Use it in shared multiplatform code and convert at the boundary.

## Related Reading

If you are standardizing async date handling — coroutines that produce timestamps, flows that batch them — our [Kotlin concurrency comparison](../2026-08-26-kotlin-concurrency-coroutines-rxjava-flow-comparison/) covers the execution models, and our [JVM bytecode tooling guide](../2026-09-11-jvm-bytecode-engineering-byte-buddy-javassist-asm/) covers the build-level details if you are shipping libraries rather than apps.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "kotlinx-datetime vs ThreeTenABP vs java.time in 2026",
  "description": "Comparison of Kotlin date and time libraries in 2026: kotlinx-datetime 0.8, ThreeTenABP 1.4.9 and the built-in java.time, including the 0.8.0 Instant migration and DST pitfalls.",
  "datePublished": "2026-11-02",
  "dateModified": "2026-11-02",
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
