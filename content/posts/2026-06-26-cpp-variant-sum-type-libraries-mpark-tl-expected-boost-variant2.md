---
title: "Self-Hosted C++ Variant and Sum Type Libraries: mpark/variant vs tl::expected vs Boost.Variant2"
date: "2026-06-26"
tags: ["cpp", "variant", "sum-type", "header-only", "functional-programming", "error-handling", "c++17", "c++20"]
draft: false
---

## Introduction

Before `std::variant` arrived in C++17, representing a value that could be one of several types required either a tagged union (error-prone, no type safety) or inheritance-based polymorphism (heap allocation, virtual dispatch overhead). Even with `std::variant` available, there are important use cases that the standard library doesn't fully address: backporting to older C++ standards, never-valueless guarantees, and monadic error handling for function return types.

This article compares three leading C++ sum type and variant libraries: **mpark/variant** (the reference implementation that became `std::variant`), **tl::expected** (monadic error handling), and **Boost.Variant2** (a never-valueless variant).

## Comparison Table

| Feature | mpark/variant | tl::expected | Boost.Variant2 |
|---------|-------------|-------------|----------------|
| GitHub Stars | 712 | 1,860 | 71 (Boost module) |
| C++ Standard | C++11/14/17 | C++11/14/17 | C++11/14/17 |
| Header-Only | Yes | Yes | Yes |
| Pattern | Discriminated Union | Result/Option Type | Discriminated Union |
| Never-Valueless | No | N/A (binary) | ✅ (strong guarantee) |
| std::variant Drop-in | ✅ | N/A | ✅ |
| Monadic Operations | ❌ | ✅ (map, and_then, or_else) | ❌ |
| Variadic Type Support | Up to 20 types | 2 types (T, E) | Arbitrary |
| Visitor Support | ✅ (mpark::visit) | N/A (pattern match) | ✅ (boost::apply_visitor) |
| constexpr Support | Full constexpr | constexpr (C++17+) | Full constexpr |
| Exception-Free Path | ⚠️ (valueless state) | ✅ (error code path) | ✅ (never valueless) |
| Latest Update | 2022-12-07 | 2025-09-01 | 2026-04-22 |

## mpark/variant: The C++17 std::variant Backport

[mpark/variant](https://github.com/mpark/variant) by Michael Park is the reference implementation that was adopted into the C++17 standard as `std::variant`. If you need `std::variant` semantics on C++11 or C++14 compilers, this library provides a perfect drop-in replacement — change `std::variant` to `mpark::variant` and `std::visit` to `mpark::visit`, and everything else works identically.

### Installation

```cmake
FetchContent_Declare(
  mpark_variant
  GIT_REPOSITORY https://github.com/mpark/variant.git
  GIT_TAG        v1.4.0
)
FetchContent_MakeAvailable(mpark_variant)
target_link_libraries(your_target PRIVATE mpark_variant)
```

### Basic Usage

```cpp
#include <mpark/variant.hpp>

using Value = mpark::variant<int, double, std::string>;

Value v = 42;
v = std::string("hello");
v = 3.14;

// Type-safe visitor pattern
auto visitor = [](const auto& val) {
    std::cout << val << std::endl;
};
mpark::visit(visitor, v);

// Type-checked access
if (auto* p = mpark::get_if<double>(&v)) {
    std::cout << "double: " << *p << std::endl;
}
```

The main caveat with mpark/variant is the **valueless-by-exception** state: if an exception is thrown during assignment, the variant can enter a "valueless" state where `valueless_by_exception()` returns true. While this is the standard-mandated behavior, it creates a rarely-tested code path that surprises developers.

## tl::expected: Monadic Error Handling

[tl::expected](https://github.com/TartanLlama/expected) by Sy Brand (TartanLlama) implements the proposed `std::expected<T, E>` type — a sum type representing either an expected value `T` or an error `E`. This is the C++ equivalent of Rust's `Result<T, E>` and Haskell's `Either`. While `std::expected` was standardized in C++23, tl::expected works on C++11 and provides powerful **monadic operations** that the standard version lacks.

### Installation

```cmake
FetchContent_Declare(
  tl_expected
  GIT_REPOSITORY https://github.com/TartanLlama/expected.git
  GIT_TAG        v1.1.0
)
FetchContent_MakeAvailable(tl_expected)
target_link_libraries(your_target PRIVATE tl::expected)
```

### Monadic Pipeline

```cpp
#include <tl/expected.hpp>

tl::expected<int, std::string> parse_number(const std::string& s) {
    try {
        return std::stoi(s);
    } catch (...) {
        return tl::make_unexpected("Invalid number: " + s);
    }
}

tl::expected<int, std::string> reciprocal(int n) {
    if (n == 0) return tl::make_unexpected("Division by zero");
    return 1.0 / n;
}

// Monadic composition with map + and_then
auto result = parse_number("10")
    .and_then(reciprocal)
    .map([](double d) { return d * 100; })
    .or_else([](const std::string& err) {
        std::cerr << "Error: " << err << std::endl;
    });
```

This monadic chain replaces deeply nested `if-else` error checks with a linear, composable pipeline. Each step only executes if the previous step succeeded — failed results short-circuit through `and_then` directly to `or_else`.

### Comparison with Exceptions

```cpp
// Traditional exceptions (unpredictable control flow)
try {
    auto n = std::stoi(s);
    auto r = 1.0 / n;
    return r * 100;
} catch (const std::exception& e) {
    // Which step failed? Unknown without multiple try blocks
}

// tl::expected (explicit control flow)
return parse_number(s)
    .and_then(reciprocal)
    .map([](double d) { return d * 100; });
```

## Boost.Variant2: The Never-Valueless Variant

[Boost.Variant2](https://github.com/boostorg/variant2) by Peter Dimov is a redesign of `std::variant` that provides a **strong never-valueless guarantee**. Even when an exception is thrown during assignment, `boost::variant2::variant` maintains its previous value — it never enters the "valueless" state that `std::variant` can.

```cpp
#include <boost/variant2/variant.hpp>

struct ThrowingMove {
    ThrowingMove() = default;
    ThrowingMove(ThrowingMove&&) { throw std::runtime_error("boom"); }
    ThrowingMove& operator=(ThrowingMove&&) { throw std::runtime_error("boom"); return *this; }
};

boost::variant2::variant<ThrowingMove, int> v(42);
try {
    v = ThrowingMove{}; // throws during move construction
} catch (...) {
    // v still holds int(42) — never entered valueless state
    assert(boost::variant2::get<int>(&v) != nullptr); // passes
}
```

This guarantee eliminates an entire class of bugs where code incorrectly assumes a variant always holds a value. For safety-critical systems, real-time applications, and any codebase where exceptions are enabled, Boost.Variant2 provides valuable resilience.

## Build System Integration

```cmake
cmake_minimum_required(VERSION 3.20)
project(VariantDemo CXX)

set(CMAKE_CXX_STANDARD 17)

FetchContent_Declare(mpark_variant GIT_REPOSITORY https://github.com/mpark/variant.git GIT_TAG v1.4.0)
FetchContent_MakeAvailable(mpark_variant)

FetchContent_Declare(tl_expected GIT_REPOSITORY https://github.com/TartanLlama/expected.git GIT_TAG v1.1.0)
FetchContent_MakeAvailable(tl_expected)

# Boost.Variant2 requires Boost or can be used standalone via FetchContent
FetchContent_Declare(boost_variant2 GIT_REPOSITORY https://github.com/boostorg/variant2.git GIT_TAG boost-1.87.0)
FetchContent_MakeAvailable(boost_variant2)

add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE mpark_variant tl::expected boost_variant2)
```



For schema-based serialization with these types, see our [Protobuf and FlatBuffers comparison](../2026-06-19-schema-serialization-frameworks-protobuf-capnproto-flatbuffers-thrift/).

If you're building event-sourced systems, our [self-hosted event store guide](../2026-06-14-self-hosted-stream-processing-management-uis-nifi-streampark-streampipes/) covers the processing pipeline side.
## Choosing the Right Library

For **backporting std::variant to older C++ standards**, use **mpark/variant**. It's the battle-tested reference implementation with identical semantics — when you eventually upgrade to C++17, change `mpark::` to `std::` and nothing else breaks.

For **error handling and function return types**, use **tl::expected**. The monadic `map`/`and_then`/`or_else` operations transform verbose error-checking code into readable pipelines. This pattern is especially valuable in data processing pipelines, parser combinators, and network protocol handlers where each step depends on the previous step's success.

For **safety-critical systems with exceptions disabled** or when you need the **never-valueless guarantee**, use **Boost.Variant2**. The stronger invariants mean fewer edge cases to test and higher confidence in code correctness.

## Why Self-Host Sum Types?

Sum types (discriminated unions) model domain logic more precisely than inheritance hierarchies. A parsing result that's either a valid AST or an error message maps naturally to `expected<AST, ParseError>` rather than a base `ParseResult` class with dynamic_cast checks. This eliminates an entire category of bugs: accessing data in the wrong state is caught at compile time by `get<T>()` rather than at runtime by a segfault.

For embedded and resource-constrained systems, sum types avoid heap allocation entirely — the variant stores all alternatives inline within a single stack allocation. Compared to `std::unique_ptr<Base>` with virtual dispatch, this saves both memory (no vtable pointer) and indirection (no pointer chase).

For serialization protocols like Protobuf and FlatBuffers (see our [schema serialization comparison](../2026-06-19-schema-serialization-frameworks-protobuf-capnproto-flatbuffers-thrift/)), sum types model `oneof` unions directly in C++ type systems, enabling zero-copy deserialization with compile-time validation.

## Integration with Serialization and Network Protocols

Sum types pair naturally with binary protocols. When deserializing a protobuf `oneof` field, the generated code maps directly to a variant — the tag byte selects which alternative to construct, and `get_if<>()` provides type-safe access without manual `switch` on raw integers. This eliminates an entire class of "tag byte mismatch" bugs that plague C-style union-based parsers.

For JSON configuration files, `expected<T, ParseError>` enables robust parsing pipelines: `parse_int → and_then(validate_range) → map(apply_defaults)`. Each step can fail independently with rich error context, and the monadic chain short-circuits on the first failure — unlike exceptions which unwind the entire call stack regardless of which step failed.

In network protocol handlers, Boost.Variant2's never-valueless guarantee prevents denial-of-service attacks where a carefully crafted packet triggers an exception during variant assignment, leaving the connection handler in an invalid state. For safety-critical protocol implementations, the extra double-buffering cost is a small price for eliminating this failure mode entirely.

## FAQ

### When should I use tl::expected instead of throwing exceptions?

Use tl::expected when errors are **expected and recoverable** (invalid user input, network timeouts, parse failures). Use exceptions for truly exceptional conditions (out of memory, logic errors indicating a bug). tl::expected makes error handling explicit and visible in function signatures, which improves API documentation and forces callers to acknowledge failure paths.

### Does mpark/variant work with std::visit from C++17?

Yes. mpark/variant is API-compatible with std::variant. You can use `mpark::visit` when targeting C++11/14, and switch to `std::visit` when you upgrade to C++17. The library also provides `mpark::get`, `mpark::get_if`, and `mpark::holds_alternative` — all direct equivalents of the std counterparts.

### How does Boost.Variant2 achieve the never-valueless guarantee?

Boost.Variant2 uses double-buffering internally: it constructs the new value in a separate buffer before destroying the old one. If construction throws, the separate buffer is cleaned up and the original value remains intact. This trades a small amount of temporary stack space for the safety guarantee. The overhead is negligible for most types but may matter for very large variants (>1KB alternatives).

### Can I chain monadic operations across different error types?

tl::expected's `and_then` expects the function to return `expected<U, E>` with the **same error type** `E`. To chain across different error types, use `.map_error()` to convert errors first, or create a common error variant type. For heterogeneous error handling, consider wrapping errors in a variant: `expected<T, variant<ParseError, NetworkError, IOError>>`.

### Are these libraries compatible with C++23 std::expected?

tl::expected was the basis for the C++23 standardization proposal, so the API is very similar. The main difference is that the standardized `std::expected` omits the monadic operations — tl::expected retains them. If you use tl::expected's `map`/`and_then` functionality, you'll want to continue using the library even on C++23 compilers.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Variant and Sum Type Libraries: mpark/variant vs tl::expected vs Boost.Variant2",
  "description": "Compare C++ sum type libraries for discriminated unions, monadic error handling, and never-valueless variants with backport support for C++11/14/17.",
  "datePublished": "2026-06-26",
  "dateModified": "2026-06-26",
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
