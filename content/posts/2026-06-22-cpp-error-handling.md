---
title: "C++ Error Handling Libraries: Boost.LEAF vs tl::expected vs Boost.Outcome vs std::expected"
date: "2026-06-22"
tags: ["c++", "error-handling", "boost", "developer-tools", "cpp-libraries"]
draft: false
---

Error handling is one of the most debated topics in C++ — exceptions, error codes, `std::optional`, and monadic result types all compete for adoption. Choosing the right strategy directly impacts code readability, performance, and maintainability. This guide compares four modern C++ error handling libraries: Boost.LEAF, tl::expected, Boost.Outcome, and the standard `std::expected` (C++23).

## Why Modern Error Handling Matters in C++

Traditional C++ error handling relies on exceptions or integer return codes. Exceptions introduce invisible control flow, potential performance overhead on the unhappy path, and portability issues in embedded or `-fno-exceptions` environments. Raw error codes are verbose, easy to ignore, and lack context propagation.

Modern error handling libraries provide **deterministic, type-safe, and composable** alternatives:

- **No hidden control flow** — errors travel through return values, not stack unwinding
- **Rich error context** — attach file names, line numbers, and arbitrary metadata
- **Monadic composition** — chain operations with `.and_then()`, `.or_else()`, and `.transform()`
- **Zero-cost abstractions** — the happy path compiles to the same assembly as exception-free code

| Feature | Boost.LEAF | tl::expected | Boost.Outcome | std::expected (C++23) |
|---------|-----------|-------------|--------------|----------------------|
| **Stars** | 339 | 1,859 | 791 | Standard library |
| **C++ Standard** | C++11+ | C++11+ | C++14+ | C++23 |
| **Error Payload** | Arbitrary (multiple objects) | Single `E` type | `EC` + optional `EP` | Single `E` type |
| **No-Alloc Error Path** | Yes (pre-allocated) | Depends on `E` | Yes (with `result`) | Depends on `E` |
| **Exception Interop** | Transport only | None | Via `outcome` type | None |
| **Monadic Operations** | No (uses `handle_error`) | `.and_then()`, `.map()`, `.or_else()` | `.and_then()`, `.map()` | `.and_then()`, `.transform()`, `.or_else()` |
| **Header-Only** | Yes | Yes | Mostly | N/A (compiler) |
| **Last Updated** | Apr 2026 | Sep 2025 | Jun 2026 | Compiler-dependent |

## Boost.LEAF: Lightweight Error Augmentation Framework

Boost.LEAF takes a fundamentally different approach from `expected`-style libraries. Instead of bundling error information into a single object, LEAF transports error objects **on the side** — through a thread-local `error_info` mechanism that avoids allocation on the error path.

```cpp
#include <boost/leaf.hpp>
namespace leaf = boost::leaf;

enum class io_error { timeout, connection_lost, invalid_data };

leaf::result<int> read_sensor(int fd) {
    if (fd < 0)
        return leaf::new_error(io_error::connection_lost,
                               leaf::e_file_name{"sensor0"},
                               leaf::e_errno{errno});
    
    char buffer[256];
    auto bytes = ::read(fd, buffer, sizeof(buffer));
    if (bytes < 0)
        return leaf::new_error(io_error::timeout,
                               leaf::e_errno{errno});
    return static_cast<int>(bytes);
}

// Error handling with type-based matching
leaf::result<void> process() {
    BOOST_LEAF_AUTO(data, read_sensor(3));  // auto-unwrap
    return {};
}

void handle_errors() {
    leaf::try_handle_all(
        []() -> leaf::result<void> { return process(); },
        [](io_error e, leaf::e_file_name name, leaf::e_errno err) {
            std::cerr << "I/O error " << err.value 
                      << " on " << name.value << "\n";
        },
        [](io_error e) {
            std::cerr << "Unknown I/O error\n";
        }
    );
}
```

LEAF's design shines in **embedded systems** and **real-time applications** where exception overhead is unacceptable. The error path allocates nothing — error objects are transported via a pre-allocated slot in the `leaf::result` object.

## tl::expected: The Community Standard

`tl::expected` by Simon Brand (TartanLlama) is the single-header implementation that inspired `std::expected`. With over 1,800 GitHub stars, it's battle-tested across thousands of production codebases.

```cpp
#include <tl/expected.hpp>
#include <string>
#include <system_error>

enum class parse_error { invalid_format, out_of_range, missing_field };

auto parse_int(const std::string& s) -> tl::expected<int, parse_error> {
    try {
        size_t pos;
        int val = std::stoi(s, &pos);
        if (pos != s.length())
            return tl::unexpected(parse_error::invalid_format);
        return val;
    } catch (const std::out_of_range&) {
        return tl::unexpected(parse_error::out_of_range);
    }
}

// Monadic chaining
auto process_config(const std::string& raw) -> tl::expected<int, std::string> {
    return parse_int(raw)
        .map([](int v) { return v * 2; })
        .and_then([](int v) -> tl::expected<int, std::string> {
            if (v > 1000) return tl::unexpected("Value too large");
            return v;
        })
        .or_else([](parse_error e) -> tl::expected<int, std::string> {
            return tl::unexpected("Parse failed: " + std::to_string(static_cast<int>(e)));
        });
}
```

The monadic interface — `.map()`, `.and_then()`, `.or_else()`, `.transform()` — enables **railway-oriented programming**: chain operations that short-circuit on the first error, transforming values along the way.

## Boost.Outcome: The Swiss Army Knife

Boost.Outcome (and its standalone edition by Niall Douglas) provides the richest type system of any C++ error-handling library, with three core types:

```cpp
#include <boost/outcome.hpp>
namespace outcome = BOOST_OUTCOME_V2_NAMESPACE;

// result<T> — either a T or an error_code
outcome::result<int> divide(int a, int b) {
    if (b == 0)
        return std::errc::invalid_argument;
    return a / b;
}

// outcome<T> — T, error_code, OR exception_ptr
outcome::outcome<std::string> read_file(const char* path) {
    try {
        std::ifstream f(path);
        if (!f) return std::errc::no_such_file_or_directory;
        std::string content((std::istreambuf_iterator<char>(f)),
                             std::istreambuf_iterator<char>());
        return content;
    } catch (const std::bad_alloc& e) {
        return std::current_exception();  // transport exception
    }
}

// TRY macro for automatic propagation
outcome::result<int> compute() {
    OUTCOME_TRY(a, divide(10, 2));
    OUTCOME_TRY(b, divide(a, 0));
    return b;  // never reached
}
```

Outcome's key differentiator is its **three-way type system**: `result<T>` (value or error code), `outcome<T>` (value, error code, or exception pointer), and `experimental::status_result<T>` (value or status code with domain). This makes it ideal for **codebases that straddle exception-using and exception-free boundaries**.

## std::expected: The Standard Library Answer (C++23)

C++23 standardizes `std::expected<T, E>` in `<expected>`, drawing heavily from tl::expected's design. It's available in GCC 12+, Clang 16+, and MSVC 2022 17.6+.

```cpp
#include <expected>
#include <string>

enum class db_error { connection_failed, query_error, timeout };

std::expected<int, db_error> fetch_count() {
    auto conn = connect_to_db();
    if (!conn) return std::unexpected(db_error::connection_failed);
    
    auto result = conn->query("SELECT COUNT(*) FROM users");
    if (!result) return std::unexpected(db_error::query_error);
    
    return result->get_int(0);
}

// Monadic operations (C++23)
auto process = fetch_count()
    .transform([](int c) { return c * 100; })
    .and_then([](int c) -> std::expected<double, db_error> {
        if (c > 10000) return std::unexpected(db_error::query_error);
        return static_cast<double>(c) / 7.5;
    })
    .or_else([](db_error e) -> std::expected<double, db_error> {
        std::cerr << "DB error, returning default\n";
        return 0.0;
    });
```

The `std::expected` adoption trajectory is clear: it will become the **default choice** for new C++23 projects, displacing custom result types and `std::optional`-based error patterns.

## Choosing the Right Library

**Use `std::expected`** if you target C++23 and need a standard, well-understood vocabulary type. It's the future-proof choice for greenfield projects.

**Use `tl::expected`** if you're on C++11/14/17 and want a near-identical API to `std::expected` with additional functional-style extensions. It's the most widely deployed expected implementation.

**Use Boost.Outcome** if you need to bridge exception-based and error-code APIs within the same codebase, or if you need the three-way `outcome<T>` type for transporting exception pointers alongside error codes.

**Use Boost.LEAF** if you're in a no-exceptions, no-allocations environment (embedded, real-time, kernel), or if you need to attach **multiple independent error objects** without composing them into a single error type.

## Why Self-Host Your C++ Error Handling Strategy?

Choosing the right error handling library is a foundational architecture decision that affects every function signature in your codebase. Unlike logging or serialization — which can be swapped at module boundaries — error types permeate your entire API surface.

For teams building **performance-critical C++ applications**, the error handling strategy directly impacts binary size, cache locality, and branch predictor performance. Boost.LEAF's no-alloc error path, for example, eliminates malloc traffic on failure paths — critical for real-time trading systems where even a single allocation stall can miss a market window.

If you're working with **unit testing frameworks** to validate error paths, our [C++ unit testing comparison](../2026-06-21-cpp-unit-testing-frameworks-catch2-doctest-gtest-boost-test/) covers Catch2, doctest, and GoogleTest strategies for testing error conditions. For **signal and event propagation** patterns that complement error handling, see our [signal-slot event libraries guide](../2026-06-22-signal-slot-event-libraries-boost-signals2-sigslot-libsigcpp/).

## Deployment Architecture: Integrating Error Handling Libraries

All four libraries are header-only or mostly header-only, making integration straightforward via CMake:

```cmake
# CMakeLists.txt — mix and match as needed
cmake_minimum_required(VERSION 3.16)
project(ErrorHandlingDemo CXX)
set(CMAKE_CXX_STANDARD 20)

# tl::expected — single header drop-in
include(FetchContent)
FetchContent_Declare(tl_expected
    GIT_REPOSITORY https://github.com/TartanLlama/expected.git
    GIT_TAG v1.1.0)
FetchContent_MakeAvailable(tl_expected)

# Boost.LEAF and Boost.Outcome via vcpkg or system Boost
find_package(Boost REQUIRED COMPONENTS leaf)
# Boost.Outcome ships as standalone or via Boost

add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE tl::expected Boost::leaf)
```

For projects using **Conan** package manager:
```bash
# conanfile.txt
[requires]
tl-expected/1.1.0
boost/1.85.0

[generators]
CMakeDeps
CMakeToolchain
```

## FAQ

### When should I use exceptions vs `std::expected`?

Exceptions are appropriate for truly exceptional conditions that the immediate caller cannot handle — out-of-memory, hardware faults, programmer bugs. `std::expected` is better for **expected failures** that are part of normal operation: invalid user input, network timeouts, file-not-found. A useful heuristic: if the caller should always handle this case, use `expected`; if it's reasonable to let it propagate up the stack, use exceptions.

### Can I use multiple libraries in the same project?

Yes — they're not mutually exclusive. A common pattern uses `std::expected` for business logic and Boost.LEAF specifically for I/O-heavy subsystems where rich error context is needed. Libraries can be wrapped with custom adapters to convert between types at API boundaries.

### Is tl::expected compatible with std::expected?

`tl::expected` v1.x predates `std::expected` and has slight API differences (e.g., `tl::expected::map()` vs `std::expected::transform()`). The v2 branch of tl::expected tracks the C++23 standard more closely. Migration between the two is straightforward — mostly renaming methods.

### Does Boost.LEAF support monadic operations?

Boost.LEAF intentionally avoids monadic `.and_then()` chains. Instead, it uses `handle_error()` with a lambda-based dispatch that matches error types at the handling site. This trades monadic ergonomics for **zero-allocation error transport** and multi-object error payloads.

### What about C++26 and beyond?

P2927 (std::expected monadic enhancements) proposes `.or_else_with()`, `.transform_or()`, and other expansions. P2561 proposes a `std::status_code` type for more structured error information. The ecosystem is converging toward a `std::expected`-centric model with richer standard error types.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Error Handling Libraries: Boost.LEAF vs tl::expected vs Boost.Outcome vs std::expected",
  "description": "Comprehensive comparison of modern C++ error handling libraries including Boost.LEAF, tl::expected, Boost.Outcome, and std::expected (C++23). Covers monadic error handling, no-exception strategies, and integration patterns.",
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
