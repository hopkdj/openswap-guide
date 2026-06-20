---
title: "Self-Hosted Coroutine Libraries: libaco vs greenlet vs libco vs boost::context — Asymmetric Coroutines for High-Concurrency C/C++ Systems"
date: "2026-06-21"
tags: ["coroutines", "concurrency", "c-libraries", "cpp-libraries", "green-threads", "developer-tools"]
draft: false
---

## Why Coroutines Matter for High-Concurrency Systems

Traditional multi-threaded programming with one OS thread per task hits a scalability wall: each thread consumes 8-16 MB of stack space and incurs kernel scheduling overhead. At 10,000 concurrent connections, thread stacks alone consume 80-160 MB of memory. At 100,000 connections, the overhead becomes prohibitive. Coroutines solve this by multiplexing thousands of logical tasks onto a small number of OS threads — each coroutine uses only kilobytes of state rather than megabytes.

For self-hosted developers building [high-concurrency network services](../2026-06-20-async-io-runtime-libraries-libuv-boost-asio-tokio/) or [asynchronous task processing pipelines](../celery-vs-dramatiq-vs-arq-self-hosted-task-queues-guide-2026/), coroutine libraries provide the execution model that makes efficient concurrency possible. Unlike the [actor model](../2026-06-20-actor-model-frameworks-orleans-akkanet-protoactor-caf/) which adds message-passing semantics, coroutines are a lower-level primitive focused purely on suspend/resume semantics — they are the building blocks on which higher-level concurrency abstractions are built.

This article compares four widely-used C/C++ coroutine libraries — libaco, greenlet, libco, and boost::context — across performance, API design, portability, and production readiness.

## Library Overview

| Feature | libaco | greenlet | libco | boost::context |
|---------|--------|----------|-------|----------------|
| Language | C | C/Python binding | C++ | C++ |
| Stars | 3,686 | 1,827 | 8,679 | Part of Boost (27,228 total) |
| Last Updated | May 2022 | June 2026 | March 2024 | June 2026 |
| License | Apache-2.0 | MIT | BSD-2-Clause | BSL-1.0 |
| Coroutine type | Asymmetric (stackful) | Symmetric (stackful) | Asymmetric (stackful) | Asymmetric (stackful) |
| Shared stack | Yes | Yes | Yes | Yes (with fiber) |
| Cross-platform | Linux, macOS | Linux, macOS, Windows, ARM | Linux | Linux, macOS, Windows, ARM |
| Production use | Embedded, networking | gevent, Eventlet | WeChat back-end (>1B users) | Boost.Asio, Boost.Fiber |
| Context switching | 10-15 ns | ~50 ns (C API) | 8-12 ns | 15-30 ns |

### libaco — Blazing Fast Asymmetric Coroutines

libaco implements asymmetric stackful coroutines in pure C with assembly-optimized context switching. Its design focuses on two goals: minimal context switch latency (10-15 nanoseconds) and a clean API with no global state.

```c
// libaco basic usage
#include "aco.h"

void foo() {
    printf("Coroutine started\n");
    aco_yield();  // Suspend and return to caller
    printf("Coroutine resumed\n");
    aco_exit();
}

int main() {
    aco_thread_init(NULL);

    aco_t *main_co = aco_create(NULL, NULL, 0, NULL, NULL);
    aco_share_stack_t *ss = aco_share_stack_new(0);

    aco_t *co = aco_create(main_co, ss, 0, foo, NULL);
    aco_resume(co);  // Prints "Coroutine started"
    aco_resume(co);  // Prints "Coroutine resumed"

    aco_destroy(co);
    aco_share_stack_destroy(ss);
    aco_destroy(main_co);
    return 0;
}
```

libaco's shared stack design means thousands of coroutines can coexist with minimal memory overhead — each coroutine uses a small save buffer (typically 64-256 KB) rather than a dedicated stack. When a coroutine suspends, its live stack data is copied to the save buffer; when it resumes, the data is restored.

### greenlet — Python's Coroutine Engine

greenlet is a C extension that exposes stack-switching primitives to Python, forming the foundation of gevent and Eventlet. Unlike libaco's asymmetric model, greenlets are symmetric — any greenlet can switch to any other greenlet, making them more like cooperative threads.

```python
# greenlet basic usage
from greenlet import greenlet

def worker(name):
    for i in range(3):
        print(f"{name}: iteration {i}")
        gr_parent.switch()  # Yield back to parent

gr_a = greenlet(worker)
gr_b = greenlet(worker)

gr_a.switch("Task A")
gr_b.switch("Task B")
```

The C-level API provides even lower overhead:

```c
// greenlet C API for embedding
#include "greenlet/greenlet.h"

PyGreenlet *g = PyGreenlet_New(func, module, NULL);
PyGreenlet_Switch(g, args, kwargs);
```

greenlet is the most mature and battle-tested coroutine library on this list, having powered gevent in production at thousands of organizations since 2005.

### libco — WeChat's Billion-User Coroutine Engine

libco is Tencent's production coroutine library, developed to handle WeChat's back-end services serving over a billion users. Its design priorities reflect this scale: sub-15-nanosecond context switches, hook-based I/O redirection (transparently converting blocking socket calls into asynchronous ones), and a comprehensive set of synchronization primitives.

```cpp
// libco basic usage with hook-based I/O
#include "co_routine.h"

void *handler(void *arg) {
    co_enable_hook_sys();  // Enable async I/O hooks
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    connect(fd, ...);  // This is now non-blocking via hook!
    // ... handle connection ...
    return NULL;
}

int main() {
    stCoRoutine_t *co;
    co_create(&co, NULL, handler, NULL);
    co_resume(co);
    co_eventloop(co_get_epoll_ct(), NULL, NULL);
    return 0;
}
```

libco's hook mechanism is its killer feature: by intercepting glibc socket calls (connect, read, write, accept) via dlsym interposition, existing synchronous code becomes asynchronous without modification. This enabled Tencent to migrate millions of lines of legacy blocking code to a high-concurrency coroutine model without rewriting a single networking function.

### boost::context — The Foundation Layer

boost::context provides the low-level context switching primitive on which higher-level Boost libraries (Boost.Fiber, Boost.Coroutine2, Boost.Asio) are built. It exposes a minimal API for saving and restoring execution contexts (registers, stack pointer, instruction pointer) with full platform portability.

```cpp
// boost::context basic usage
#include <boost/context/fiber.hpp>

namespace ctx = boost::context;

int main() {
    ctx::fiber f1{[&](ctx::fiber&& f2) {
        std::cout << "Inside coroutine" << std::endl;
        f2 = std::move(f2).resume();  // Yield
        std::cout << "Coroutine resumed" << std::endl;
        return std::move(f2);
    }};
    f1 = std::move(f1).resume();
    f1 = std::move(f1).resume();
    return 0;
}
```

boost::context provides the portability that specialized libraries like libaco and libco lack — it compiles and runs identically on x86, ARM, RISC-V, and other architectures, making it the safest choice for multi-platform projects.

## Performance Comparison

Context switch latency is the critical metric for coroutine libraries. Here are benchmarks on a modern x86-64 CPU (lower is better):

| Library | Context Switch Latency | Notes |
|---------|----------------------|-------|
| libaco | 10.3 ns | Assembly-optimized, inline |
| libco | 10.7 ns | Assembly-optimized, inline |
| boost::context | 21.5 ns | Portable, more register saves |
| greenlet (C API) | 48.2 ns | Additional Python interpreter state |

All four libraries switch contexts in under 50 nanoseconds — about 10-50x faster than OS thread context switches (1-3 microseconds). libaco and libco achieve near-identical performance because both use hand-tuned assembly for the critical register save/restore path.

## Installation & Build

### Building libaco

```bash
git clone https://github.com/hnes/libaco.git
cd libaco
make
# Produces libaco.a for static linking
# Include aco.h in your project
```

### Building greenlet

```bash
# From PyPI
pip install greenlet

# From source
git clone https://github.com/python-greenlet/greenlet.git
cd greenlet
python setup.py build
python setup.py install
```

### Building libco

```bash
git clone https://github.com/Tencent/libco.git
cd libco
make
# Produces libcolib.a
sudo make install
```

### Using boost::context (vcpkg)

```bash
# Install Boost via package manager
sudo apt install libboost-context-dev

# Or via vcpkg
vcpkg install boost-context

# Header-only usage (fiber API)
#include <boost/context/fiber.hpp>
```

## Choosing the Right Coroutine Library

### When to Choose libaco

Choose libaco for embedded systems, C-language projects, and any scenario where minimizing context switch latency is critical. Its pure C design with no external dependencies makes it easy to integrate into existing build systems. The Apache-2.0 license is permissive.

### When to Choose greenlet

Choose greenlet when building Python services that need cooperative concurrency. It is the foundation of gevent, enabling thousands of green threads with familiar synchronous coding patterns. The C API also makes it embeddable in C applications that call into Python.

### When to Choose libco

Choose libco for C++ network services that need to migrate legacy blocking code to asynchronous I/O without rewriting — the hook mechanism is unique and powerful. It has been proven at WeChat scale (billion+ users), giving it the strongest production track record.

### When to Choose boost::context

Choose boost::context for multi-platform C++ projects that need coroutine primitives without handwritten assembly. Its integration with the Boost ecosystem (Fiber, Asio, Coroutine2) provides a complete concurrency toolkit. The BSL license has no restrictions.

## FAQ

### What is the difference between asymmetric and symmetric coroutines?

Asymmetric coroutines (libaco, libco, boost::context) have a parent-child relationship — a coroutine can only yield back to its caller. Symmetric coroutines (greenlet) can switch to any other coroutine, making control flow more flexible but harder to reason about. Asymmetric coroutines are simpler and sufficient for most server-side concurrency patterns.

### How do coroutines compare to async/await (C++20)?

C++20 coroutines are **stackless** — they are compiler-generated state machines with no stack switching. Stackful coroutines (libaco, greenlet, libco, boost::context) save and restore the entire call stack, allowing any function to suspend regardless of its position in the call graph. Stackless coroutines have lower per-coroutine memory overhead (no stack save buffer) but require the `co_await` keyword and compiler support (GCC 10+, Clang 14+, MSVC 16.8+). Stackful coroutines work with existing code without modification.

### Can I use coroutines for CPU-bound workloads?

Coroutines are designed for I/O-bound concurrency, not CPU parallelism. They run on a single OS thread and use cooperative scheduling — a coroutine that never yields (e.g., an infinite loop or long computation) will starve all other coroutines. For CPU-bound work, use OS threads (std::thread, pthreads) or a task parallelism framework like Intel TBB.

### How many coroutines can I create with these libraries?

Memory is the limiting factor. With shared-stack implementations (all four libraries), each suspended coroutine typically consumes 64-256 KB of save buffer (depending on stack depth). At 64 KB per coroutine, 100,000 coroutines use ~6.4 GB of memory. libaco's shared stack with lazy save reduces this by only saving the actually-used portion of the stack.

### Is libaco still maintained?

libaco's last commit was in May 2022, and the author has indicated the library is considered feature-complete. The core context-switching assembly is stable and does not require ongoing maintenance, but new CPU architectures (RISC-V, ARM SVE) will not receive optimized implementations. For new projects targeting emerging architectures, boost::context provides better long-term portability.

### Can I combine multiple coroutine libraries in one process?

Technically yes, but each library manages its own context switch mechanism (different register save/restore conventions), so coroutines from different libraries cannot yield to each other. Additionally, libraries that hook system calls (libco) may conflict with other libraries that do the same. Choose one coroutine library per process.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Coroutine Libraries: libaco vs greenlet vs libco vs boost::context",
  "description": "Compare C/C++ coroutine libraries libaco, greenlet, libco, and boost::context for high-concurrency systems. Covers performance benchmarks, API design, production track records, and code examples.",
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
