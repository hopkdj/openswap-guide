---
title: "Swift Logging Libraries in 2026: swift-log vs CocoaLumberjack vs SwiftyBeaver"
date: "2026-08-13"
tags: ["swift", "logging", "developer-tools", "ios"]
draft: false
cover: "/img/screenshots/swiftybeaver-console.png"
---

Your app is crashing in production and the log file tells you nothing. Or worse — the log file is 2 GB and the crash happened 40 minutes ago, buried under `print()` spam that never got removed. Every Swift developer hits this wall eventually: the built-in `print()` approach that worked for a two-file project becomes an unmanageable mess the moment your codebase grows, ships to production, or runs server-side.

The good news: Swift's logging ecosystem has matured dramatically. You now have three serious contenders — Apple's official **swift-log**, the veteran **CocoaLumberjack**, and the developer-friendly **SwiftyBeaver**. They take fundamentally different approaches, and picking the wrong one means reworking every log call in your codebase a year from now. This guide compares them with real code, real metrics, and clear recommendations.

## TL;DR — Quick Verdict

**Choose swift-log if you want the official, dependency-free API backed by Apple** — it's the default choice for server-side Swift (Vapor, Hummingbird) and integrates with everything via `LogHandler` backends. **Choose CocoaLumberjack if you need battle-tested file logging with log rotation and crash-safe output** — it's been running in production iOS apps since 2011 and has the largest community (13,330 stars). **Choose SwiftyBeaver if you want the best-looking console output and zero-config setup** — its colored, formatted console and encryption support make it the fastest path from zero to useful logs.

## Comparison at a Glance

| Feature | swift-log (Apple) | CocoaLumberjack | SwiftyBeaver |
|---|---|---|---|
| GitHub Stars | 4,043 | 13,330 | 6,058 |
| Last Update | Aug 2026 | Aug 2026 | Nov 2024 |
| License | Apache 2.0 | BSD-3-Clause | MIT |
| Primary Platform | All Swift (esp. server) | iOS/macOS (Apple platforms) | iOS/macOS/watchOS/tvOS |
| Log Levels | trace, debug, info, notice, warning, error, critical | verbose, debug, info, warn, error | verbose, debug, info, warning, error |
| File Logging | Via backends (e.g. FileLogHandler) | Built-in `DDFileLogger` with rolling | Built-in `FileDestination` |
| Log Rotation | Backend-dependent | Native (24h rolling, count/size limits) | Size-based |
| Console Colors | Via backend | Xcode colors | Native colored output |
| Encryption | Via backend | No | AES-256 built-in |
| Metadata Support | First-class (`metadata` dict) | Via log message formatting | Via formatting tokens |
| Async Logging | Backend-dependent | Native GCD-based async | Native queue |
| Server-side (Linux) | ✅ Fully supported | ⚠️ Limited | ⚠️ Limited |
| Ecosystem | 100+ community backends | Large, mature plugin set | Small but focused |

## Decision Matrix — Which One for Your Use Case?

| Use Case | Recommended Tool | Why |
|---|---|---|
| Server-side Swift (Vapor, Hummingbird, gRPC) | **swift-log** | Apple's API is the standard; every server framework integrates with it natively |
| Long-running iOS app with file-based audit trails | **CocoaLumberjack** | `DDFileLogger` gives you rolling, size-capped, crash-safe file output out of the box |
| Open-source library that other devs will consume | **swift-log** | Libraries should only log via the `Logging` API; consumers choose the backend |
| Startup/indie dev who wants logs working in 5 minutes | **SwiftyBeaver** | 3 lines of code, beautiful console output, no configuration ceremony |
| App with sensitive data in logs | **SwiftyBeaver** | Built-in AES-256 encryption for destinations |
| Team already standardized on OSLog/Unified Logging | **swift-log + OSLog backend** | `StreamLogHandler` and community OSLog backends bridge both worlds |

## swift-log — The Official Logging API

Swift-log is Apple's answer to a problem the ecosystem had been circling for years: every server-side framework (Vapor, Kitura, Perfect) had its own logging API, so libraries couldn't interoperate. Swift-log defines a **single API** with a pluggable backend system. Your library code calls `Logger(label:)`; the application decides where logs actually go by setting `LoggingSystem.bootstrap()`.

```swift
// swift-tools-version: 6.1
import PackageDescription

let package = Package(
    name: "YourApp",
    dependencies: [
        .package(url: "https://github.com/apple/swift-log", from: "1.6.0")
    ],
    targets: [
        .target(
            name: "YourApp",
            dependencies: [
                .product(name: "Logging", package: "swift-log")
            ]
        )
    ]
)
```

Then start logging:

```swift
import Logging

// Create a logger
let logger = Logger(label: "com.example.YourApp")

// Log at different levels
logger.info("Application started")
logger.warning("This is a warning")
logger.error("Something went wrong", metadata: ["error": "\(error)"])

// Add metadata for context
var requestLogger = logger
requestLogger[metadataKey: "request-id"] = "\(UUID())"
requestLogger.info("Processing request")
```

The metadata system is where swift-log shines: you attach structured key-value pairs to log statements, and backends can index, filter, or forward them to structured collectors. The `LoggingSystem.bootstrap` mechanism means an app can swap from console output to JSON output to a remote collector without touching library code. At 4,043 stars and with Apple's backing, it's the safest long-term investment — but the core package is deliberately minimal, so you must pick a backend for real-world file or remote logging.

## CocoaLumberjack — The Production Veteran

CocoaLumberjack has been the default choice for serious iOS logging since 2011. It predates Swift and grew up on Objective-C, but its Swift support is now first-class. Its killer features are **file logging and log rotation**: `DDFileLogger` writes to disk with configurable rolling frequency and retention, which is exactly what you need for diagnosing issues that only reproduce on user devices.

```swift
import CocoaLumberjackSwift

DDLog.add(DDOSLogger.sharedInstance) // Uses os_log

let fileLogger: DDFileLogger = DDFileLogger() // File Logger
fileLogger.rollingFrequency = 60 * 60 * 24 // 24 hours
fileLogger.logFileManager.maximumNumberOfLogFiles = 7
DDLog.add(fileLogger)

// Log at every level
DDLogVerbose("Verbose")
DDLogDebug("Debug")
DDLogInfo("Info")
DDLogWarn("Warn")
DDLogError("Error")
```

Installation is flexible — Swift Package Manager, CocoaPods (`pod 'CocoaLumberjack/Swift'`), or Carthage all work. The async logging is built on GCD and is famously fast: Lumberjack claims logging at a rate that won't block the main thread even under heavy load. The `DDFileLogger` crash-safety means log lines already written are never lost even if the app is killed mid-write.

The trade-off: the API is older and more verbose (global `DDLog*` functions versus instance-based loggers), and its server-side/Linux story is limited. If your target is iOS/macOS apps that need durable file logs, it remains the strongest choice — 13,330 stars and two decades of production hardening back that up.

## SwiftyBeaver — Zero-Friction Developer Experience

SwiftyBeaver's pitch is simple: **beautiful logs in minutes**. One global `log` object, three destinations (console, file, cloud), and you're done. Its console output is colorized with configurable format tokens, which makes skimming a busy debug session dramatically easier than plain text.

```swift
import SwiftyBeaver
let log = SwiftyBeaver.self

// add log destinations. at least one is needed!
let console = ConsoleDestination()  // log to Xcode Console
let file = FileDestination()  // log to default swiftybeaver.log file

// use custom format and set console output to short time, log level & message
console.format = "$DHH:mm:ss$d $L $M"
// or use this for JSON output: console.format = "$J"

// In Xcode 15+, specify the logging method as .logger to display color,
// subsystem, and category information in the console (relies on OSLog API)
console.logPrintWay = .logger(subsystem: "Main", category: "UI")
```

SwiftyBeaver's standout differentiator is **encryption**: `FileDestination` and `CloudDestination` support AES-256 encryption via a password you set in code, which is rare among logging frameworks and valuable for apps handling sensitive user data. The cloud destination (`sbcloud.io`) even gives you a hosted log viewer without standing up your own infrastructure — though that part is a paid service, and privacy-conscious teams will prefer self-hosted options.

The catch: development slowed (last push November 2024) and the ecosystem is small compared to CocoaLumberjack's plugin set. It's also weaker on server-side Swift. For a solo developer or small team shipping an Apple-platform app, though, nothing beats its time-to-value.

## Pitfalls and Migration Notes

**1. Don't mix global `print()` with a logging framework.** Log frameworks buffer and format asynchronously; `print()` writes synchronously and bypasses your level filters. Grep for `print(` before release and replace or gate them. Xcode's build settings can help: define a `DEBUG` flag and wrap debug-only prints.

**2. Log level naming differs between libraries.** swift-log uses `trace/debug/info/notice/warning/error/critical` (RFC 5424 style); CocoaLumberjack uses `verbose/debug/info/warn/error`; SwiftyBeaver uses `verbose/debug/info/warning/error`. A naive port of `logger.error` from one to another is fine, but `warning` vs `warn` and the absence of `notice`/`critical` in the older two cause silent level mismatches. Map levels explicitly during migration.

**3. Metadata does not port automatically.** If you move from SwiftBeaver format tokens (`$L`, `$M`, `$D`) to swift-log's structured metadata, you must rewrite every call site that relied on formatting. Consider adopting swift-log's `metadata` dictionary even in libraries so a future backend swap is painless.

**4. File rotation defaults differ — set them explicitly.** CocoaLumberjack's default `rollingFrequency` is 24 hours; SwiftyBeaver rotates by file size (default 50 MB). If your app logs heavily, 50 MB rotates far too rarely and you'll ship a 500 MB log file. Set both frequency and count limits consciously.

**5. OSLog integration is not free.** CocoaLumberjack's `DDOSLogger` and SwiftyBeaver's `.logger` mode both route through the unified logging system. That gives you Console.app visibility but adds overhead and, on older OS versions, message truncation limits. Profile if you log in hot paths.

**6. Server-side teams should standardize on swift-log.** If your backend is Vapor or Hummingbird, every framework already logs through `LoggingSystem`; introducing a second logging stack for app-level code fragments your log pipeline and breaks centralized collection.

## FAQ

**Is swift-log compatible with OSLog / unified logging?**
Yes. Swift-log is an API layer, not a specific sink. Community backends (like `LoggingOSLog` or `LoggingSystem.bootstrap` with a custom `LogHandler`) forward records to the unified logging system, giving you Console.app and `log stream` access while keeping the standard API.

**Can I use CocoaLumberjack on Linux for server-side Swift?**
Only with significant effort. CocoaLumberjack historically targets Apple platforms (it relies on Foundation/UIKit-adjacent APIs). For server-side Swift, use swift-log with a file or JSON backend instead — it's the ecosystem standard.

**Which library is fastest?**
CocoaLumberjack advertises the strongest performance story thanks to GCD-based async logging and 20 years of optimization; swift-log is deliberately lightweight and fast, but real throughput depends on your chosen backend. SwiftyBeaver is fast enough for nearly all apps but has no published benchmark arms race. For hot paths, measure with your own workload rather than trusting marketing numbers.

**Does SwiftyBeaver's encryption actually protect log files?**
It encrypts destination files with AES-256 using a key derived from your configured password. That protects logs at rest on the device. It does not protect against a compromised app binary that contains the password — treat it as a deterrent for casual access, not a security boundary.

**What's the best way to add log levels to a library I'm publishing?**
Use swift-log. Your library should `import Logging` and create a `Logger(label: "com.yourorg.yourlib")`. Consumers then decide the backend and verbosity. This is the pattern Apple recommends and every major Swift package follows.

**How do I remove debug-only logging for production?**
Configure level filtering at bootstrap: set the minimum level to `info` or `warning` in release builds. With swift-log you can pass the level to `StreamLogHandler` or a custom handler; with CocoaLumberjack, set `dynamicLogLevel = .info`; with SwiftyBeaver, set `console.minLevel = .warning`. Compiler-based removal (wrapping calls in `#if DEBUG`) is a last resort that hurts readability.

## Related Reading

Want to go deeper on the Swift ecosystem? Check out our [Swift HTTP client library comparison](../2026-07-27-swift-http-client-libraries-alamofire-urlsession-moya-asynchttpclient/), the [Swift server-side frameworks face-off](../2026-07-06-swift-server-side-frameworks-vapor-hummingbird-grpc-swift/), and the [Swift testing framework guide](../2026-07-23-swift-testing-frameworks-xctest-quick-nimble-snapshottesting/). For how the same logging problem plays out in other languages, see our [Rust logging libraries comparison](../2026-07-27-rust-logging-libraries-env-logger-log4rs-tracing-slog/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Swift Logging Libraries in 2026: swift-log vs CocoaLumberjack vs SwiftyBeaver",
  "description": "Compare Apple's swift-log, CocoaLumberjack, and SwiftyBeaver for Swift logging in 2026. Real code examples, GitHub stats, decision matrix, and migration pitfalls.",
  "datePublished": "2026-08-13",
  "dateModified": "2026-08-13",
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
