---
title: "Self-Hosted C++ Enum Reflection Libraries: magic_enum vs Better Enums vs Wise Enum"
date: "2026-06-26"
tags: ["cpp", "enum", "reflection", "header-only", "compile-time", "c++17", "c++20"]
draft: false
---

## Introduction

C++ enums are great for type safety, but the language provides no built-in way to convert enum values to strings, iterate over enumerators, or query enum bounds at runtime. This forces developers to maintain hand-written lookup tables, `switch` statements, or preprocessor macros — all of which are error-prone and drift out of sync as enums evolve.

Enum reflection libraries solve this by leveraging **compile-time metaprogramming** to automatically introspect C++ enums. Using modern techniques like `__PRETTY_FUNCTION__` parsing, structured bindings, and `consteval`, these header-only libraries provide zero-cost enum-to-string conversion, enumerator iteration, and bounds checking — all without macros or code generation.

This article compares three leading C++ enum reflection libraries: **magic_enum**, **Better Enums**, and **Wise Enum**.

## Comparison Table

| Feature | magic_enum | Better Enums | Wise Enum |
|---------|-----------|-------------|-----------|
| GitHub Stars | 6,119 | 1,823 | 299 |
| C++ Standard | C++17 | C++98/11/14 | C++14 |
| Enumerator Limit | ~512 | ~64 (configurable) | ~256 |
| Header-Only | Yes | Yes | Yes |
| enum_cast (to/from string) | ✅ | ✅ | ✅ |
| Enumerator Iteration | ✅ (values()) | ✅ (_values) | ✅ |
| Bounds Checking | ✅ (min/max) | ✅ | ✅ |
| Bitmask/Flag Support | ✅ | ❌ | ❌ |
| constexpr Support | Full constexpr | constexpr (enum class) | constexpr |
| Custom Name Mapping | ✅ (customize::enum_name) | Via _name() method | Via adapter |
| Non-contiguous Enums | ✅ (Sequential/flags) | Limited | ✅ |
| JSON / Serialization | ✅ (third-party) | Via macro | ❌ |
| Latest Update | 2026-06-08 | 2024-02-10 | 2024-02-08 |

## magic_enum: The Modern Standard

[magic_enum](https://github.com/Neargye/magic_enum) by Neargye is the most popular and feature-complete C++ enum reflection library with over 6,000 stars. It uses C++17 features — specifically the `__PRETTY_FUNCTION__` / `__FUNCSIG__` compiler intrinsic — to extract enum value names from template instantiation signatures at compile time.

### Installation (CMake FetchContent)

```cmake
include(FetchContent)
FetchContent_Declare(
  magic_enum
  GIT_REPOSITORY https://github.com/Neargye/magic_enum.git
  GIT_TAG        v0.9.7
)
FetchContent_MakeAvailable(magic_enum)
target_link_libraries(your_target PRIVATE magic_enum::magic_enum)
```

### Basic Usage

```cpp
#include <magic_enum/magic_enum.hpp>

enum class Color { Red = -1, Green = 0, Blue = 1, Alpha = 2 };

// Enum to string
auto name = magic_enum::enum_name(Color::Red);  // "Red"

// String to enum
auto val = magic_enum::enum_cast<Color>("Blue"); // std::optional: Blue

// Iterate all enumerators
for (auto c : magic_enum::enum_values<Color>()) {
    std::cout << magic_enum::enum_name(c) << " = " 
              << magic_enum::enum_integer(c) << std::endl;
}

// Enum count
constexpr auto count = magic_enum::enum_count<Color>(); // 4

// Min/max
constexpr auto min_val = magic_enum::enum_integer(magic_enum::min_v<Color>); // -1
```

### Bit Flags Support

magic_enum uniquely supports C++ enum flags (bitmask enums) for decomposing combined values:

```cpp
enum class Permissions : uint8_t { Read = 0x1, Write = 0x2, Execute = 0x4 };

auto perms = Permissions::Read | Permissions::Write;
auto names = magic_enum::enum_flags_name(perms); 
// { "Read", "Write" }
```

## Better Enums: C++98 Compatibility

[Better Enums](https://github.com/aantron/better-enums) takes a different approach — instead of relying on compiler intrinsics, it uses a **macro-based declaration** that generates the enum and its reflection data simultaneously. This makes it compatible all the way back to C++98, while still producing clean `constexpr` code on modern compilers.

### Installation

```bash
# Simply copy the header
wget https://raw.githubusercontent.com/aantron/better-enums/refs/heads/main/enum.h
```

```cmake
# Or via CMake FetchContent
FetchContent_Declare(
  better_enums
  GIT_REPOSITORY https://github.com/aantron/better-enums.git
  GIT_TAG        0.11.3
)
FetchContent_MakeAvailable(better_enums)
```

### Declaration with Macros

```cpp
#include "enum.h"

BETTER_ENUM(Color, int,
    Red = -1, Green = 0, Blue = 1, Alpha = 2
)

// String conversion
const char* name = Color::_name();          // "Blue"
Color c = Color::_from_string("Red");       // Color::Red (throws on invalid)

// Iteration
for (Color c : Color::_values()) {
    std::cout << c._to_string() << " = " << c._to_integral() << std::endl;
}

// Count
constexpr size_t count = Color::_size();    // 4
```

The macro `BETTER_ENUM` expands to a complete class with `_to_string()`, `_from_string()`, `_values()`, `_size()`, and comparison operators — all generated at compile time. While the macro syntax requires a slightly different declaration style, the integration is seamless for projects that can use it from the start.

## Wise Enum: Lightweight C++14

[Wise Enum](https://github.com/quicknir/wise_enum) by Johnathan Wakeley provides enum reflection functionality targeting C++14 while aiming for minimal template instantiation overhead. It uses a **separate adapter struct** pattern rather than modifying the enum declaration itself.

```cpp
#include <wise_enum/wise_enum.h>

enum class Status { Pending, Active, Completed, Cancelled };

// Define the adapter
WISE_ENUM(Status, Pending, Active, Completed, Cancelled)

// String conversion
std::string s = wise_enum::to_string(Status::Active);       // "Active"
auto st = wise_enum::from_string<Status>("Completed");       // Status::Completed

// Iteration
for (auto s : wise_enum::range<Status>()) {
    std::cout << wise_enum::to_string(s) << std::endl;
}
```

Wise Enum's adapter approach means the original enum declaration stays clean (no macros in the enum body), but the boilerplate exists separately in the `WISE_ENUM` macro call. It supports up to ~256 enumerators and provides `constexpr` access on C++17 compilers.

## Build System Integration

All three libraries are header-only and integrate via CMake FetchContent or manual header copying. Here's a complete CMakeLists.txt comparing all three:

```cmake
cmake_minimum_required(VERSION 3.20)
project(EnumReflection CXX)

set(CMAKE_CXX_STANDARD 20)

# magic_enum (recommended for modern projects)
include(FetchContent)
FetchContent_Declare(magic_enum 
  GIT_REPOSITORY https://github.com/Neargye/magic_enum.git
  GIT_TAG v0.9.7
)
FetchContent_MakeAvailable(magic_enum)

# Better Enums (for C++98/11 compatibility)
add_subdirectory(third_party/better-enums)

# Wise Enum
add_subdirectory(third_party/wise_enum)

add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE 
  magic_enum::magic_enum 
  better_enums 
  wise_enum
)
```



For related C++ compile-time techniques, see our [template metaprogramming comparison](../2026-06-22-cpp-template-metaprogramming-libraries-hana-mp11-brigand-metal/).

If you're building large C++ projects, our [monorepo build systems guide](../2026-06-16-self-hosted-monorepo-build-systems-nx-turborepo-bazel/) covers Bazel and Nx integration with header-only libraries.
## Choosing the Right Library

**magic_enum** is the clear recommendation for any C++17+ project. It has the largest community, most features (bit flags, JSON integration, customization points), active maintenance (updated June 2026), and clean integration — just `#include` and use. The only tradeoff is the C++17 requirement.

**Better Enums** shines when you need C++98/11 compatibility or prefer explicit declaration over compiler magic. Its macro-based approach is well-documented and battle-tested, but it requires changing your enum declarations to use the `BETTER_ENUM` macro — which may not be feasible for existing codebases with hundreds of enums.

**Wise Enum** fills the C++14 niche with a design that keeps enum declarations pristine. The adapter pattern means you can add reflection to existing enums without modifying their definitions. It's lighter weight than magic_enum but lacks bit flag support and has a smaller community.

## Why Self-Host Enum Reflection?

Binary size matters in embedded and system-level C++ applications. Enum reflection libraries eliminate manual lookup tables that can bloat data sections — a `switch` statement with 50 enum cases compiles to a jump table, but adding string conversions for logging/debugging traditionally requires a parallel `const char*[]` array of the same size. Magic enum generates this at compile time with zero additional data segment overhead.

For network protocols and serialization, enum-to-string conversion enables human-readable logging of protocol state machines without hand-maintained mapping code. The `enum_cast` from string back to enum enables configuration file parsing — reading "DEBUG" from a JSON config and converting to `LogLevel::Debug` in a type-safe way.

For cross-platform GUI applications, enum iteration enables automatic population of combo boxes and dropdown menus from the enum definition, eliminating the risk of a newly added enumerator being forgotten in the UI code.

## Performance Benchmarks: Compile-Time and Runtime Overhead

While all three libraries are "zero-overhead" at runtime, their compile-time costs differ significantly based on the techniques they use. magic_enum relies on deeply recursive template instantiations to extract enumerator names from compiler intrinsics — for enums with 100+ values, expect 2-5 seconds of additional compilation time per translation unit. This can be mitigated by forward-declaring the reflection in a single `.cpp` file and using `extern template` declarations, though this adds build complexity.

Better Enums uses a more traditional macro-expansion approach that's lighter on the compiler's template machinery. A 64-enumerator `BETTER_ENUM` compiles roughly 3-4x faster than the equivalent magic_enum declaration, because the string data is pre-generated by the preprocessor rather than discovered through template metaprogramming. The tradeoff is the macro-based declaration syntax.

Wise Enum sits between the two — it uses a separate adapter pattern that avoids both deep template recursion and preprocessor macros. For projects where fast incremental build times matter more than feature breadth (especially embedded toolchains with limited C++17 support), Wise Enum's compilation profile is the most predictable.

In microbenchmarks, all three libraries produce equivalent runtime performance: `enum_name()` returns a `string_view` into static storage with zero allocations, and `enum_cast()` performs a binary search over a compile-time-sorted array of name-value pairs — typically 4-8 comparisons for a 128-value enum.

## FAQ

### Can I use magic_enum with C++14 projects?

No — magic_enum requires C++17 or later. The library relies on `if constexpr`, fold expressions, and structured binding decomposition from the `__PRETTY_FUNCTION__` output. For C++14, use Wise Enum. For C++11/98, use Better Enums.

### How many enumerators can magic_enum handle?

By default, magic_enum supports enums with up to **128 enumerators** (defined by `MAGIC_ENUM_RANGE_MAX`). This can be increased up to 512 in the configuration header, at the cost of slightly longer compilation times due to template recursion depth.

### Do these libraries work with scoped enums (enum class)?

Yes, all three libraries support both unscoped (`enum`) and scoped (`enum class`) enumerations. In fact, scoped enums are recommended because they provide better type safety without polluting the enclosing namespace.

### Is there runtime performance overhead?

None. All string generation and lookup happens at compile time. `magic_enum::enum_name()` returns a `std::string_view` pointing to static storage, and `enum_cast` uses compile-time-generated constexpr arrays. Benchmarks show these are consistently faster than hand-written `switch` maps due to better compiler optimization of the generated constexpr data.

### Can I customize the displayed name for specific enumerators?

magic_enum supports this via specialization of the `customize::enum_name` struct. You can override names for individual enumerators without affecting others. Better Enums allows custom names via the `_name()` method override. Wise Enum requires defining a custom adapter.

### Do these libraries support enum flags (bitmask enums)?

Only **magic_enum** provides built-in bitmask support via `enum_flags_name()` and `enum_flags_cast()`. For Better Enums and Wise Enum, you need to implement bitmask handling manually using the per-value iteration and lookup functions.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Enum Reflection Libraries: magic_enum vs Better Enums vs Wise Enum",
  "description": "Compare three header-only C++ enum reflection libraries for automatic enum-to-string conversion, enumerator iteration, and compile-time introspection without macros or code generation.",
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
