---
title: "Self-Hosted C++ Performance Profiling: Tracy vs Optick vs Remotery vs MicroProfile"
date: "2026-06-21"
tags: ["cplusplus", "developer-tools", "profiling", "performance", "debugging", "open-source", "game-development"]
draft: false
---

## Introduction

Finding performance bottlenecks in C++ applications often feels like detective work without the right tools. Printf-debugging with timestamps tells you *that* something is slow but not *why* — and it certainly cannot reveal cache misses, thread contention, or GPU pipeline stalls. Purpose-built profiling libraries instrument your code with lightweight markers, capture timing data across frames or requests, and present visual timelines that make bottlenecks immediately obvious.

We compare four open-source C++ profiling libraries: **Tracy** (16,181 stars), **Optick** (3,138 stars), **Remotery** (3,305 stars), and **MicroProfile** (496 stars). Each provides a client library that instruments your application and a server/visualizer that displays the collected data in real time via a web interface or native GUI.

| Feature | Tracy | Optick | Remotery | MicroProfile |
|---|---|---|---|---|
| **GitHub Stars** | 16,181 | 3,138 | 3,305 | 496 |
| **Last Updated** | Jun 2026 | May 2024 | Aug 2024 | May 2023 |
| **Client Language** | C++ (C API available) | C++ | C (single file) | C++ (single header) |
| **Visualizer** | Native GUI (ImGui-based) | Native GUI | Web-based (HTML5) | Web-based (HTML5) |
| **GPU Profiling** | Yes (Vulkan, OpenGL, D3D12) | Yes (D3D12, Vulkan) | Yes (OpenGL, D3D11) | Yes (OpenGL) |
| **Memory Profiling** | Yes (built-in) | Yes | No | No |
| **Lock Contention** | Yes | No | No | No |
| **Network Profiling** | Yes (client-server) | No (in-process) | Yes (WebSocket) | No (in-process) |
| **Sampling Profiler** | Yes (callstack sampling) | No | No | No |
| **Compile-time Overhead** | Moderate | Low | Very low (single C file) | Very low (single header) |
| **Thread Naming** | Yes (fiber support) | Yes | Yes | Yes |
| **CI Integration** | Yes (CSV/JSON export) | Limited | No | No |
| **License** | BSD-3-Clause | MIT | Apache-2.0 | Public Domain |

## Tracy: The Gold Standard for C++ Profiling

Tracy by Bartosz Tyszka (wolfpld) is the most feature-complete C++ profiler available. It instruments CPU, GPU, memory allocations, lock contention, and system call traces — all captured in a real-time client-server architecture. The server application (Tracy profiler GUI) connects to your instrumented application over TCP and displays everything as interactive flame graphs, timelines, and statistics.

**Integration (CMake):**

```cmake
# Add Tracy as a subdirectory
add_subdirectory(tracy)

# Link against the Tracy client
target_link_libraries(my_app PRIVATE TracyClient)
target_compile_definitions(my_app PRIVATE TRACY_ENABLE)
```

**Basic instrumentation:**

```cpp
#include <tracy/Tracy.hpp>

void render_frame() {
    ZoneScoped;  // automatically scoped to this function

    {
        ZoneScopedN("Physics Update");
        update_physics();  // shows as "Physics Update" in timeline
    }

    {
        ZoneScopedN("Draw Calls");
        TracyGpuZone("GPU Draw");  // GPU timeline marker
        execute_draw_calls();
    }

    // Track a value over time
    static int64_t frame_counter = 0;
    TracyPlot("Frame Number", frame_counter++);
}

int main() {
    // Optional: set thread name for better visualization
    tracy::SetThreadName("Main Thread");

    while (running) {
        FrameMark;  // marks frame boundary
        render_frame();
    }
    return 0;
}
```

Tracy's most powerful features are its **memory profiler** and **lock contention analyzer**. By wrapping memory allocations, you can see exactly which allocations are hot, how much memory each system uses, and whether there are leaks:

```cpp
// Memory tracking
void* ptr = TracyAlloc(1024, 16);  // 1024 bytes, 16-byte alignment
// ... use ptr ...
TracyFree(ptr);

// Lock tracking
static tracy::LockableCtx lock_ctx;
lock_ctx.Mark(lock);          // mark before acquire
std::lock_guard<std::mutex> guard(lock);
// Tracy shows wait time, hold time, contention
```

The overhead of Tracy instrumentation is typically 5-50 nanoseconds per zone depending on the sampling mode. You can ship Tracy-instrumented builds to production with `TRACY_ON_DEMAND` — the profiler only activates when a server connects, so idle overhead is zero.

## Optick: Game Development Focus

Optick by bombomby is designed specifically for game engines and real-time rendering applications. It provides a C++ instrumentation API with a standalone GUI profiler that visualizes frame timelines, GPU events, and thread activity. Unlike Tracy's client-server model, Optick captures data to memory and writes it to a `.optick` capture file that you open in the GUI.

**Integration:**

```cmake
# Clone and add Optick
add_subdirectory(optick)
target_link_libraries(my_app PRIVATE OptickCore)
```

**Basic usage:**

```cpp
#include <optick.h>

void game_loop() {
    OPTICK_FRAME("MainThread");

    {
        OPTICK_EVENT("World Tick");
        world.tick(delta_time);
    }

    {
        OPTICK_EVENT("Render Scene");
        OPTICK_GPU_EVENT("Draw Geometry");
        renderer.draw_geometry();
    }

    {
        OPTICK_EVENT("Audio Mix");
        OPTICK_CATEGORY("Audio", Optick::Category::Audio);
        audio.mix();
    }
}

// Initialization
int main() {
    OPTICK_APP("My Game");
    Optick::StartCapture(Optick::Mode::Default);
    // ... game loop ...
    Optick::StopCapture();
    Optick::SaveCapture("profile.optick");
    return 0;
}
```

Optick's strengths lie in its **GPU debugging** features. It can capture D3D12 and Vulkan command buffer timings with Perfetto backend support, display resource barriers, and visualize render passes. For game developers working with Unreal Engine or custom engines targeting consoles, Optick provides a familiar workflow: instrument your code, capture a frame, and analyze in the desktop GUI.

**Limitation:** Optick has not seen updates since May 2024. The project is stable but may accumulate build issues with newer compilers and graphics APIs. For new projects targeting Vulkan 1.4 or D3D13, Tracy is a more future-proof choice.

## Remotery: Zero-Dependency Web-Based Profiler

Remotery by Celtoys takes a minimalist approach: the entire profiler is a single C file (`Remotery.c`) that you drop into your project. It runs an embedded WebSocket server inside your application, and you view profiling data through any web browser. No separate GUI application needed.

**Integration:**

```bash
# Copy the single C file into your project
cp Remotery/lib/Remotery.c src/
cp Remotery/lib/Remotery.h include/

# CMakeLists.txt
add_executable(my_app src/main.cpp src/Remotery.c)
target_include_directories(my_app PRIVATE include)
target_link_libraries(my_app PRIVATE pthread)
```

**Basic usage:**

```c
#include "Remotery.h"

int main() {
    Remotery* rmt;
    rmt_CreateGlobalInstance(&rmt);

    while (running) {
        rmt_BeginCPUSample(render_frame, 0);
        render_frame();
        rmt_EndCPUSample();
    }

    rmt_DestroyGlobalInstance(rmt);
    return 0;
}
```

Open `http://localhost:17815/rmt` in any browser to see the live profiling timeline. The web interface updates in real time and provides CPU sample trees, aggregated statistics, and exportable JSON data. Remotery's single-file design makes it trivially portable — there are no build system dependencies, no CMake find_package requirements, and no third-party library chains.

**Limitation:** Remotery does not support GPU profiling, memory tracking, or lock contention analysis. It is a CPU-only sampling profiler. For GPU-bound applications, you need Tracy or Optick. For applications where the simplicity of a single C file outweighs feature depth, Remotery is unmatched.

## MicroProfile: Embeddable and Web-Enabled

MicroProfile by Arseny Kapoulkine (zeux) is a single-header C++ profiling library with an HTML5 web viewer. Like Remotery, it embeds a web server for real-time visualization, but it adds GPU scope markers and more detailed counter tracking.

**Integration:**

```cpp
// Single header - just include it
#define MICROPROFILE_ENABLED 1
#define MICROPROFILE_WEBSERVER 1
#include "microprofile.h"

int main() {
    MicroProfileOnThreadCreate("Main");
    MicroProfileSetEnableAllGroups(true);
    MicroProfileWebServerStart(1338);

    while (running) {
        MICROPROFILE_SCOPE(Frame);
        {
            MICROPROFILE_SCOPE(Physics);
            simulate_physics();
        }
        {
            MICROPROFILE_SCOPEI("Render", "Render", 0x00FF00);
            render();
        }
        MicroProfileFlip();  // flips frame
    }

    MicroProfileShutdown();
    return 0;
}
```

Navigate to `http://localhost:1338/microprofile.html` to see the profiling timeline. MicroProfile's key differentiator is its **timer API** — you can track custom counters, GPU times, and network I/O with labeled timers that appear alongside CPU scopes. The overhead per scope is approximately 20-40 CPU cycles, making it suitable for high-frequency instrumentation (>10,000 scopes per frame).

**Limitation:** MicroProfile has not been updated since May 2023 and the project appears to be in maintenance mode. For new projects, Tracy provides a superset of MicroProfile's features with better tooling and active development. Use MicroProfile only if you need the specific single-header distribution model and are comfortable with unmaintained code.

## Choosing the Right Profiler

| Your Situation | Best Choice |
|---|---|
| Production C++ server application | Tracy (connect on-demand) |
| Game engine with Vulkan/D3D12 | Tracy or Optick |
| Embedded system, minimal deps | Remotery |
| Quick profiling during development | Remotery or MicroProfile |
| Memory leak hunting | Tracy |
| Multi-threaded lock contention | Tracy |
| CI/CD performance regression testing | Tracy (CSV/JSON export) |
| Web-based visualization required | Remotery |
| Single-developer indie game | Optick or Tracy Lite |

For general performance measurement beyond profiling, our [C++ microbenchmarking libraries guide](../2026-06-21-cpp-microbenchmarking-libraries-google-benchmark-celero-nanobench/) covers Google Benchmark, Celero, and Nanobench. If your profiler reveals that lock-free data structures would help, see our [lock-free data structure comparison](../2026-06-20-lock-free-data-structure-libraries-concurrentqueue-readerwriterqueue-boost/). And for optimizing I/O-bound applications, check our [async I/O runtime comparison](../2026-06-20-async-io-runtime-libraries-libuv-boost-asio-tokio/).

## FAQ

### Can I use Tracy in a shipping production build?

Yes. Tracy supports `TRACY_ON_DEMAND` mode: compile with Tracy linked but the profiler only activates when the Tracy server connects. When no server is connected, instrumentation macros reduce to no-ops with zero runtime cost. Many game studios ship Tracy-instrumented builds to production for debugging customer-reported performance issues remotely — just ask the customer to run the Tracy GUI and connect.

### How does Remotery's web server work? Does it create security risks?

Remotery binds to `localhost:17815` by default, so the profiling interface is only accessible from the local machine. It uses a lightweight custom HTTP/WebSocket server implemented in its single C file. Do NOT bind Remotery to `0.0.0.0` in production — the profiling data includes function names, file paths, and call stacks, which is sensitive information. For remote profiling, use SSH port forwarding: `ssh -L 17815:localhost:17815 user@server`.

### What is the minimum overhead per profiling scope?

MicroProfile: ~20-40 CPU cycles (~5-10ns at 4GHz). Tracy: ~50ns in default mode, ~5ns in fiber mode. Optick: ~30-60ns. Remotery: ~50-100ns. For reference, a `std::function` call is ~5-10ns. In practice, profiling overhead is negligible for scopes that execute more than a few hundred instructions. If you are profiling very tight loops (>1M iterations), use sampling mode or aggregate statistics manually.

### Can these profilers handle applications with hundreds of threads?

Tracy handles up to 128 threads natively and displays them all in the timeline. Optick and Remotery handle ~64 threads gracefully. MicroProfile starts showing UI performance degradation above ~32 threads. For thread pools with very short-lived worker threads, Tracy's fiber API allows tracking logical fibers rather than OS threads, which is cleaner for coroutine-heavy codebases.

### Do I need to recompile my entire application to add profiling?

For Tracy and Optick, yes — the instrumentation macros are compile-time. However, you can compile with profiling enabled in your build system (`-DTRACY_ENABLE`) and use `TRACY_ON_DEMAND` to make it runtime-conditional. For Remotery, since it operates through a C API, you can wrap profiling calls in a function that conditionally calls `rmt_BeginCPUSample` based on an environment variable, avoiding recompilation. MicroProfile supports runtime enable/disable via `MicroProfileSetEnableAllGroups()`.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Performance Profiling: Tracy vs Optick vs Remotery vs MicroProfile",
  "description": "Detailed comparison of four open-source C++ performance profiling libraries: Tracy, Optick, Remotery, and MicroProfile. Covers instrumentation, GPU profiling, memory tracking, real-time visualization, and CI/CD integration.",
  "datePublished": "2026-06-21",
  "dateModified": "2026-06-21",
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
