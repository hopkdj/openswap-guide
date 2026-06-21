---
title: "Self-Hosted Embedded Scripting Engines: Duktape vs QuickJS vs JerryScript for C++ Applications"
date: "2026-06-22"
tags: ["embedded-scripting", "javascript-engine", "c-plus-plus", "iot", "game-development", "developer-tools"]
draft: false
---

## Introduction

Embedding a scripting engine into a C++ application unlocks enormous flexibility: configuration as code, live-reloadable game logic, user-defined automation, and plugin systems with full programming language expressiveness. Rather than inventing a custom DSL or configuration format, embedding a JavaScript engine gives your users access to a familiar, battle-tested language with a rich standard library.

In this guide, we compare three production-grade embeddable JavaScript engines for C++ applications: **Duktape**, **QuickJS**, and **JerryScript**. Each targets different use cases, from resource-constrained IoT devices to high-performance server applications.

## Why Embed a JavaScript Engine?

Traditional plugin systems use C ABI with dynamic loading (`dlopen`, `LoadLibrary`), but this has serious drawbacks: platform-specific binaries, ABI fragility across compiler versions, and security risks from native code execution. A JavaScript engine provides a sandboxed, platform-independent execution environment with controlled API exposure.

Embedded engines also enable hot-reloading of game logic, server-side scripting for web applications, and user automation in desktop tools — all without requiring users to install a compiler toolchain. For a broader perspective on plugin architectures, see our [embeddable plugin systems guide](../2026-06-20-embeddable-plugin-systems-extism-pluggy-abi-stable-libloading/).

## Comparison Table

| Feature | Duktape | QuickJS | JerryScript |
|---------|---------|---------|-------------|
| **Stars** | 6,207 | 10,745 | 7,398 |
| **Author** | Sami Vaarala | Fabrice Bellard | JS Foundation |
| **ECMAScript** | ES5.1 + partial ES6 | ES2020 (full) | ES5.1 + partial ES6 |
| **Binary Size** | ~200 KB | ~620 KB | ~170 KB |
| **Memory Footprint** | < 2 MB default | ~3 MB | ~2 MB |
| **Performance** | Moderate (interpreted) | Fast (JIT-compiled) | Moderate (interpreted) |
| **C API** | Simple, well-documented | Clean, minimal | Extensive, IoT-focused |
| **Debugger** | Basic (duk_debug) | Built-in debugger | JerryScript debugger |
| **Last Update** | Mar 2024 | Jun 2026 | Oct 2025 |
| **License** | MIT | MIT | Apache 2.0 |
| **Best For** | Legacy systems, small footprint | Modern JS, full ES2020 | IoT, microcontrollers |

## Duktape: The Minimalist Workhorse

Duktape is designed for portability and compact footprint. It compiles to under 200 KB and can run on platforms from ARM Cortex-M microcontrollers to x86 servers. Its API is refreshingly simple — you can embed a JavaScript engine in fewer than 20 lines of C code.

```c
// Duktape — minimal embedding example
#include "duktape.h"

int main() {
    duk_context *ctx = duk_create_heap_default();

    // Register a C function callable from JavaScript
    duk_push_c_function(ctx, [](duk_context *ctx) -> duk_ret_t {
        const char *msg = duk_to_string(ctx, 0);
        printf("[C++] %s\n", msg);
        return 0;
    }, 1);
    duk_put_global_string(ctx, "nativeLog");

    // Evaluate JavaScript code
    duk_eval_string(ctx, "nativeLog('Hello from JavaScript!');");
    duk_pop(ctx);

    duk_destroy_heap(ctx);
    return 0;
}
```

Duktape's strength is its reliability in constrained environments. With configurable memory limits, a mark-and-sweep garbage collector with emergency compaction, and no external dependencies beyond libc, it runs on virtually any platform. However, its ECMAScript support stops at ES5.1 with partial ES6 — modern JavaScript features like `async/await`, `Proxy`, and `class` syntax are unavailable.

### CMake Integration

```cmake
# Duktape can be vendored directly — single amalgamated source
add_library(duktape duktape.c)
target_include_directories(duktape PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/duktape)
target_link_libraries(myapp PRIVATE duktape m)
```

## QuickJS: Full ES2020 with Surprising Performance

QuickJS, authored by Fabrice Bellard (creator of QEMU and FFmpeg), is remarkable: a complete ES2020 engine in a compact C library. It supports the full modern JavaScript specification including modules, async/await, BigInt, typed arrays, and Proxy objects — all while compiling to just 620 KB.

```c
// QuickJS — modern JavaScript embedding
#include "quickjs.h"

int main() {
    JSRuntime *rt = JS_NewRuntime();
    JSContext *ctx = JS_NewContext(rt);

    // Register a C function
    JSValue global = JS_GetGlobalObject(ctx);
    JS_SetPropertyStr(ctx, global, "nativeLog",
        JS_NewCFunction(ctx, [](JSContext *ctx, JSValueConst this_val,
                                 int argc, JSValueConst *argv) -> JSValue {
            const char *msg = JS_ToCString(ctx, argv[0]);
            printf("[QuickJS] %s\n", msg);
            JS_FreeCString(ctx, msg);
            return JS_UNDEFINED;
        }, "nativeLog", 1));
    JS_FreeValue(ctx, global);

    // Evaluate ES2020 code with async/await support
    const char *code = R"(
        async function main() {
            nativeLog('Starting async task...');
            await new Promise(resolve => setTimeout(resolve, 100));
            nativeLog('Done!');
        }
        main();
    )";
    JS_Eval(ctx, code, strlen(code), "<eval>", JS_EVAL_TYPE_GLOBAL);

    // Process pending jobs (for async/await)
    js_std_loop(ctx);

    JS_FreeContext(ctx);
    JS_FreeRuntime(rt);
    return 0;
}
```

QuickJS compiles JavaScript to bytecode with a register-based interpreter that achieves impressive speeds — often 2-5x faster than Duktape for numerical workloads. It also includes a command-line compiler (`qjsc`) that can compile JavaScript to C, embedding scripts directly into your binary for zero-startup-time execution.

For C++ projects managing these kinds of library dependencies, see our [C++ package management comparison](../2026-06-18-self-hosted-c-cpp-package-management-conan-vcpkg-spack/).

## JerryScript: IoT-Optimized JavaScript

JerryScript was purpose-built for microcontrollers and IoT devices by Samsung and the JS Foundation. It implements ES5.1 with optimizations for extremely constrained memory — the engine can run in under 64 KB of RAM and flash.

```c
// JerryScript — IoT-focused embedding
#include "jerryscript.h"

int main() {
    jerry_init(JERRY_INIT_EMPTY);

    // Register native handler
    jerry_value_t global = jerry_get_global_object();
    jerry_value_t func = jerry_create_external_function(
        [](const jerry_value_t func_obj, const jerry_value_t this_val,
           const jerry_value_t args[], const jerry_length_t argc) -> jerry_value_t {
            jerry_value_t str = jerry_value_to_string(args[0]);
            jerry_size_t len = jerry_get_string_size(str);
            char buffer[256];
            jerry_string_to_char_buffer(str, (jerry_char_t*)buffer, len);
            buffer[len] = '\0';
            printf("[JerryScript] %s\n", buffer);
            jerry_release_value(str);
            return jerry_create_undefined();
        }, NULL);
    jerry_value_t name = jerry_create_string((const jerry_char_t*)"nativeLog");
    jerry_set_property(global, name, func);
    jerry_release_value(name);
    jerry_release_value(func);
    jerry_release_value(global);

    // Execute JavaScript
    const char *script = "nativeLog('Hello from ESP32!');";
    jerry_value_t result = jerry_eval(
        (const jerry_char_t*)script, strlen(script),
        JERRY_PARSE_NO_OPTS);
    jerry_release_value(result);

    jerry_cleanup();
    return 0;
}
```

JerryScript's distinctive features include heap compaction, snapshot execution (pre-compiled bytecode loaded directly into ROM), and per-call memory limits. These aren't just nice-to-haves — they're essential for long-running embedded applications where memory fragmentation can cause failures after weeks of uptime. For additional tools to ensure code quality in embedded C++ projects, see our [C++ static analysis guide](../2026-06-02-linux-static-code-analysis-cppcheck-clang-flawfinder-infer/).

## Why Self-Host Your Scripting Engine?

Choosing to embed a scripting engine rather than building a custom configuration language is a strategic decision that pays dividends in developer productivity and user empowerment. JavaScript is the world's most widely understood programming language — your users and contributors already know it. Custom DSLs, no matter how well-designed, face an adoption cliff.

Self-hosting the engine means you control the sandbox, the API surface, and the execution limits. Unlike cloud-based scripting services, an embedded engine keeps user scripts local, respects air-gapped deployments, and eliminates network latency from the execution path. For security-sensitive applications, the sandbox guarantees that user scripts cannot access the filesystem, network, or process environment unless explicitly granted.

The footprint trade-off is small: Duktape adds 200 KB to your binary, QuickJS 620 KB, and JerryScript 170 KB. In an era where your application likely ships with megabytes of assets, this is negligible. The flexibility gained — live-reloadable game logic, user automation scripts, configurable server middleware — is transformative.

## FAQ

### Which engine should I choose for a new project in 2026?

QuickJS is the default recommendation for most new projects. It supports full ES2020, has active maintenance (Fabrice Bellard released updates in June 2026), and its 620 KB footprint is negligible for desktop, server, and mobile applications. If you need ES2020 features like async/await, modules, or BigInt, QuickJS is the only option among the three. For IoT with sub-512KB flash budgets, JerryScript is the better fit.

### Can I use these engines in a commercial, closed-source product?

Yes. All three engines are distributed under permissive open-source licenses (MIT or Apache 2.0) that explicitly permit commercial use, modification, and distribution in proprietary products. No copyleft restrictions apply.

### How do I debug JavaScript running in an embedded engine?

QuickJS includes the most complete debugging support with a built-in debugger that supports breakpoints, step-through, and variable inspection. Duktape provides `duk_debug` — a debug transport protocol that integrates with Duktape-specific debugger UIs. JerryScript offers a WebSocket-based debugger that connects to browser DevTools. All three also support `console.log`-style debugging via registered C callbacks.

### What about Lua — why JavaScript instead?

Lua is an excellent embedded language with a smaller footprint (~120 KB for LuaJIT). However, JavaScript's larger developer community, richer standard library (especially in ES2020), and wider ecosystem of existing libraries make it a better choice when developer familiarity and code reuse matter. If your team knows Lua and your scripting needs are simple, Lua is equally viable — see sol2 for C++/Lua bindings.

### Can I run untrusted user scripts safely?

Yes, but with caveats. All three engines provide sandboxing: you control the global object, expose only whitelisted native functions, and set resource limits (memory, execution time). However, side-channel attacks and engine bugs are still possible. For running truly untrusted code, consider process-level isolation (sandbox each script in a separate OS process) in addition to engine-level sandboxing.

### Do these engines support multithreading?

Duktape and JerryScript are single-threaded — each context must be accessed from one thread at a time, though you can create multiple independent contexts. QuickJS supports `SharedArrayBuffer` and `Atomics` for inter-context communication, making it suitable for multithreaded server applications that need shared state between script instances.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Embedded Scripting Engines: Duktape vs QuickJS vs JerryScript for C++ Applications",
  "description": "In-depth comparison of three embeddable JavaScript engines — Duktape, QuickJS, and JerryScript — for C++ applications covering ES compliance, memory footprint, performance, API design, and IoT-to-server deployment patterns.",
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
