---
title: "C++ Crash Reporting & Stack Trace Libraries: backward-cpp vs Breakpad vs Crashpad"
date: "2026-06-22"
tags: ["c++", "debugging", "crash-reporting", "backtrace", "stack-trace", "error-handling", "developer-tools"]
draft: false
---

When your C++ application crashes in production, the default experience is a cryptic `SIGSEGV` with no context. Was it a null pointer? Buffer overflow? Use-after-free? Without a stack trace, you're debugging blind. Crash reporting and backtrace libraries capture the call stack at the moment of failure — turning "it crashed" into "it crashed at `ConnectionPool::reconnect()`, called from `HealthChecker::run()`, with `this=0x0`."

This guide compares three production-grade C++ crash reporting libraries: **backward-cpp** (beautiful stack traces during development), **Google Breakpad** (crash dumps for distributed systems), and **Chromium Crashpad** (Breakpad's modern successor). We'll cover their architectures, integration points, and when to choose each.

## Why Crash Reporting Is Non-Negotiable

Production crashes cost real money. For a SaaS service processing 1,000 requests per second, a 30-minute outage caused by an unknown crash is $18,000+ in lost revenue (at $10 CPM). The most expensive part isn't the crash — it's the time spent **reproducing** it. Crash reporting libraries eliminate reproduction time by capturing the exact state at failure:

1. **Full stack trace with symbols** — function names, file paths, and line numbers, not raw hex addresses
2. **Register state** — CPU registers at crash time, critical for diagnosing memory corruption
3. **Loaded modules** — which shared libraries were loaded, at which addresses
4. **Minidump files** — portable crash snapshots that can be analyzed offline on a different machine

## Library Comparison

| Feature | backward-cpp | Breakpad | Crashpad |
|---------|-------------|----------|----------|
| GitHub Stars | 4,287 | 2,886 | 577 |
| Maintainer | Community (bombela) | Google | Google/Chromium |
| Primary Use Case | Development/debugging | Production crash reporting | Production crash reporting (modern) |
| Output Format | Colorized terminal stack trace | Minidump files | Minidump files + annotations |
| Out-of-Process Handler | No | Yes (separate process) | Yes (separate process) |
| Symbol Server Support | No | Yes | Yes |
| Upload Mechanism | No (print to stderr) | HTTP upload (via sender) | HTTP/HTTPS upload (built-in) |
| Platform Support | Linux, macOS, Windows | Linux, macOS, Windows, Android | Linux, macOS, Windows, Android, Fuchsia |
| Thread Safety | Signal-safe output | Signal-safe minidump write | Signal-safe minidump write |
| Inline in Binary | Header-only | Static library + tools | Static library + tools |

## backward-cpp: Beautiful Stack Traces for Development

[backward-cpp](https://github.com/bombela/backward-cpp) by François-Xavier Bourlet is a header-only library that produces beautiful, colorized stack traces with resolved symbols. It's designed for the development workflow: when your program crashes, you get an immediate, readable trace in your terminal.

```cpp
#include <backward.hpp>
#include <iostream>
#include <csignal>

namespace backward {
    SignalHandling sh; // Install signal handlers automatically
}

void level3() {
    int* p = nullptr;
    *p = 42;  // SIGSEGV — backward-cpp prints a beautiful backtrace
}

void level2() { level3(); }
void level1() { level2(); }

int main() {
    level1();
    return 0;
}
```

When this crashes, backward-cpp produces output like:

```
Stack trace (most recent call last):
#0  Object "crash_example", at 0x401234, in level3() + 0x1a
    at /home/user/project/src/main.cpp:8
#1  Object "crash_example", at 0x401256, in level2() + 0x9
    at /home/user/project/src/main.cpp:12
#2  Object "crash_example", at 0x401278, in level1() + 0x9
    at /home/user/project/src/main.cpp:13
#3  Object "crash_example", at 0x40129a, in main + 0x14
    at /home/user/project/src/main.cpp:16
```

backward-cpp's strength is zero-configuration integration. Drop the header, add `-ldw` or `-ldbghelp`, and every segfault and abort becomes self-documenting. For CI pipelines and developer machines, it's indispensable.

**Integration**:
```cmake
# CMake integration — backward-cpp is header-only
include(FetchContent)
FetchContent_Declare(backward GIT_REPOSITORY https://github.com/bombela/backward-cpp)
FetchContent_MakeAvailable(backward)
target_link_libraries(my_app PRIVATE backward)
```

## Google Breakpad: Production-Grade Crash Dumps

[Breakpad](https://github.com/google/breakpad) is Google's battle-tested crash reporting library, used in Chrome, Firefox, and thousands of production services. Unlike backward-cpp which prints to stderr, Breakpad writes **minidump files** — compact binary snapshots of the crashed process that can be collected, stored, and analyzed offline.

```
Architecture:
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Crashed   │────▶│   Breakpad   │────▶│   Minidump  │
│   Process   │     │   Handler    │     │   (.dmp)    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌──────────────┐     ┌──────▼──────┐
                    │   Symbol     │◀────│   Crash     │
                    │   Server     │     │   Uploader  │
                    └──────────────┘     └─────────────┘
```

```cpp
#include <client/linux/handler/exception_handler.h>
#include <iostream>

static bool MinidumpCallback(const google_breakpad::MinidumpDescriptor& descriptor,
                             void* context, bool succeeded) {
    std::cerr << "Crash dump written to: " << descriptor.path() << std::endl;
    // Upload the minidump to your collection server
    // system(("curl -F file=@" + descriptor.path() + " https://crash.example.com/upload").c_str());
    return succeeded;
}

int main() {
    google_breakpad::MinidumpDescriptor descriptor("/tmp/crashes");
    google_breakpad::ExceptionHandler eh(descriptor,
                                         nullptr,           // No filter
                                         MinidumpCallback,  // Callback on crash
                                         nullptr,           // No callback context
                                         true,              // Install handlers
                                         -1);               // No FD for in-process

    // Application code — if it crashes, Breakpad writes /tmp/crashes/<uuid>.dmp
    int* p = nullptr;
    *p = 42;
    return 0;
}
```

Breakpad's key innovation is the **out-of-process handler**: the crash handler runs in a separate process, so even if the crashed process has corrupted its own heap, the minidump gets written safely. Post-crash, you use Breakpad's `minidump_stackwalk` tool to convert the binary minidump into a human-readable stack trace, using debug symbols from your build.

## Crashpad: Breakpad's Modern Successor

[Crashpad](https://chromium.googlesource.com/crashpad/crashpad/) is Chromium's evolution of Breakpad, designed from the ground up for modern requirements: database-backed crash storage, structured annotations, and HTTP/HTTPS upload with retry logic baked into the library itself (Breakpad required a separate upload script).

```cpp
#include <client/crashpad_client.h>
#include <client/crash_report_database.h>
#include <client/settings.h>

int main() {
    // Persistent database for crash reports (survives across restarts)
    auto database = crashpad::CrashReportDatabase::Initialize(
        base::FilePath("/var/lib/myapp/crashes"));

    crashpad::CrashpadClient client;
    std::map<std::string, std::string> annotations;
    annotations["version"] = "2.1.0";
    annotations["channel"] = "production";
    annotations["datacenter"] = "us-east-1";

    std::vector<std::string> arguments;
    arguments.push_back("--no-rate-limit");

    client.StartHandler(
        base::FilePath("/usr/local/bin/crashpad_handler"),
        base::FilePath("/var/lib/myapp/crashes"),
        base::FilePath("/var/lib/myapp/metrics"),
        "https://crash.example.com/submit",  // Upload URL
        annotations,
        arguments,
        true,    // Restartable
        false    // Asynchronous start
    );

    // Application code — Crashpad handles everything automatically
    int* p = nullptr;
    *p = 42;
    return 0;
}
```

Crashpad's major improvement over Breakpad is **persistent crash databases**. If your application crashes and the network is down, the crash report isn't lost — it's stored locally and uploaded when connectivity returns. It also supports **extended file attachments** (log files, core dumps, custom diagnostic data) that Breakpad's minidump format couldn't handle.

## Selecting the Right Library

| Scenario | Recommended Library |
|----------|-------------------|
| Development/debugging — quick crash analysis on dev machines | **backward-cpp** |
| Production SaaS — collect crash dumps from 100+ servers | **Breakpad** (mature, widely deployed) |
| New project, need crash DB + structured metadata | **Crashpad** (modern, annotation-rich) |
| Embedded/IoT — minimal overhead, no out-of-process handler | **backward-cpp** (header-only) |
| Desktop application — crash reporting for end users | **Crashpad** (built-in upload with retry) |

For most new projects, Crashpad is the forward-looking choice. Its persistent database and structured annotations solve real operational problems that Breakpad's file-based approach leaves to external tooling. However, if you need proven stability at massive scale (Google Chrome-level traffic), Breakpad has 15+ years of production hardening.

## Integrating Into Your Workflow

The most effective crash reporting setup combines both approaches: backward-cpp in debug builds for fast local diagnosis, and Crashpad (or Breakpad) in release builds for production monitoring. This is easy to configure in CMake:

```cmake
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_link_libraries(my_app PRIVATE backward)
    target_compile_definitions(my_app PRIVATE USE_BACKWARD_CRASH_HANDLER)
else()
    find_package(crashpad REQUIRED)
    target_link_libraries(my_app PRIVATE crashpad::client)
endif()
```

For related debugging and profiling tooling, see our [C++ performance profiling guide](../2026-06-21-cpp-performance-profiling-tracy-optick-remotery-microprofile/) and our [memory safety sanitizers comparison](../2026-06-21-memory-safety-sanitizers-addresssanitizer-valgrind-threadsanitizer-ubsan/) which covers AddressSanitizer, ThreadSanitizer, and UBSan. For memory-specific debugging, our [Linux memory profiling tools guide](../2026-06-02-linux-memory-profiling-memray-heaptrack-massif-gperftools/) covers complementary heap analysis.

## FAQ

### What's the difference between backward-cpp and Breakpad/Crashpad?

backward-cpp is a development tool that prints human-readable stack traces to stderr when your program crashes. Breakpad and Crashpad are production crash reporting systems that write portable minidump files for offline analysis. Use backward-cpp for local debugging; use Breakpad/Crashpad when you need to collect crashes from thousands of production instances.

### Can I use both backward-cpp and Crashpad in the same binary?

Yes — but only one can install the signal handler. In debug builds, install backward-cpp's handler for immediate terminal output. In release builds, install Crashpad's handler for minidump generation and remote upload. Use `#ifdef DEBUG` / `#ifndef NDEBUG` to switch between them at compile time.

### How do I symbolicate minidump files?

Use Breakpad's `minidump_stackwalk` tool with your debug symbols: `minidump_stackwalk crash.dmp /path/to/symbols > crash.txt`. For Crashpad, `crashpad_database_util` provides similar functionality. Both require that you've extracted debug symbols from your release binary with `dump_syms` and organized them in Breakpad's symbol directory format.

### Does backward-cpp work in release builds with stripped binaries?

Partially. Without debug symbols (compiled with `-g` or on stripped binaries), backward-cpp can only show function addresses, not names or line numbers. Always keep a debug symbol copy of your release binaries (`objcopy --only-keep-debug`) for offline symbolication.

### Where can I install these libraries?

```bash
# backward-cpp (header-only, no install needed)
git clone https://github.com/bombela/backward-cpp

# Breakpad
git clone https://github.com/google/breakpad
cd breakpad && ./configure && make && sudo make install

# Crashpad
git clone https://chromium.googlesource.com/crashpad/crashpad
# Build with GN + ninja (Chromium build system)
```

All three are compile-from-source C++ libraries, not Docker services. They link directly into your application binary.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Crash Reporting & Stack Trace Libraries: backward-cpp vs Breakpad vs Crashpad",
  "description": "Comprehensive comparison of C++ crash reporting libraries — backward-cpp, Google Breakpad, and Chromium Crashpad — covering minidump generation, stack trace resolution, production crash collection, and integration patterns.",
  "datePublished": "2026-06-22",
  "dateModified": "2026-06-22",
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
