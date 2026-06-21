---
title: "C++ Template Metaprogramming Libraries: Boost.Hana vs Boost.Mp11 vs Brigand vs Metal"
date: "2026-06-22"
tags: ["c++", "template-metaprogramming", "compile-time", "generic-programming", "developer-tools", "open-source", "libraries", "comparison"]
draft: false
---

C++ template metaprogramming has come a long way from the cryptic SFINAE tricks of C++98. Modern C++11/14/17/20 provides constexpr, fold expressions, concepts, and improved type traits that make compile-time computation both more powerful and more readable. However, working with the raw standard library type traits can still be verbose and error-prone. This is where template metaprogramming libraries step in — they provide higher-level abstractions that make compile-time computation feel almost like runtime programming.

In this article, we compare four leading C++ template metaprogramming libraries: **Boost.Hana** (1,840 stars), **Brigand** (570 stars), **Metal** (331 stars), and **Boost.Mp11** (287 stars).

## Library Overview

| Library | Stars | Standard | Philosophy | Key Abstraction |
|---------|-------|----------|------------|-----------------|
| **Boost.Hana** | 1,840 | C++14 | Heterogeneous computation | `hana::tuple`, `hana::type` |
| **Brigand** | 570 | C++11 | Pure type-level lists | `brigand::list` |
| **Metal** | 331 | C++11 | Minimalist SFINAE-friendly | `metal::list` |
| **Boost.Mp11** | 287 | C++11 | Short names, minimal overhead | `mp11::mp_list` |

Boost.Hana takes a fundamentally different approach from the other three: it performs computations on both types AND values at compile time using a unified interface. Brigand, Metal, and Mp11 operate purely on type lists, transforming sequences of types into new sequences.

## Boost.Hana: Heterogeneous Metaprogramming

[Boost.Hana](https://github.com/boostorg/hana) is the most ambitious library in this comparison. It unifies type-level and value-level computation under a single interface, allowing you to write algorithms that work on types, values, or both simultaneously — all at compile time.

```cpp
#include <boost/hana.hpp>
namespace hana = boost::hana;

// Compile-time type computation
using Types = hana::tuple<int, double, char, float>;

// Filter types by size
auto small_types = hana::filter(Types{}, [](auto t) {
    return hana::size_t<sizeof(typename decltype(t)::type) <= 4>{};
});
// Result: tuple<int, char, float>

// Find a type
auto has_double = hana::contains(Types{}, hana::type_c<double>);  // true

// Transform: get pointer types
auto ptr_types = hana::transform(Types{}, [](auto t) {
    return hana::type_c<typename decltype(t)::type*>;
});
// Result: tuple<int*, double*, char*, float*>

// Compile-time value computation
constexpr auto squares = hana::make_tuple(1, 2, 3, 4, 5);
constexpr auto result = hana::fold(squares, 0, [](auto acc, auto x) {
    return acc + x * x;
});
static_assert(result == 55, "Sum of squares should be 55");
```

**Key strength:** Hana lets you write one algorithm and apply it to both types and values. A single `hana::transform` call can map over a tuple of types (producing new types) or a tuple of values (producing new values). This eliminates the need to learn separate APIs for type-level and value-level computation.

**Trade-offs:** Hana requires C++14 and has significantly higher compile-time overhead than the other three libraries. Including `<boost/hana.hpp>` pulls in a substantial amount of code.

## Brigand: The Pragmatic Workhorse

[Brigand](https://github.com/edouarda/brigand) is a C++11 library focused on pure type-level computation. It's the spiritual successor to Boost.MPL, designed with faster compilation and cleaner error messages in mind. Brigand operates on `brigand::list<...>` — type sequences that can be filtered, transformed, sorted, and queried at compile time.

```cpp
#include <brigand/brigand.hpp>

using Types = brigand::list<int, double, char, float, long>;

// Filter: keep only integral types
using Integrals = brigand::filter<Types, std::is_integral<brigand::_1>>;
// Result: brigand::list<int, char, long>

// Transform: add pointer
using Pointers = brigand::transform<Types, std::add_pointer<brigand::_1>>;

// Sort by size
using BySize = brigand::sort<Types, brigand::less<
    brigand::sizeof_<brigand::_1>,
    brigand::sizeof_<brigand::_2>
>>;
// Result: brigand::list<char, int, float, long, double>

// Fold: find largest alignment
using MaxAlign = brigand::fold<Types,
    brigand::integral_constant<std::size_t, 1>,
    brigand::max<
        brigand::_state,
        brigand::alignof_<brigand::_element>
    >
>;
```

**Key strength:** Brigand compiles fast and produces manageable error messages for a metaprogramming library. It has the most comprehensive algorithm set among the type-list libraries, including `sort`, `partition`, `reverse`, and set operations.

**When to use:** You need heavy type-level computation in C++11, compile times matter, and you don't need Hana's heterogeneous value + type capabilities.

## Boost.Mp11: Minimalist and Standard-Adjacent

[Boost.Mp11](https://github.com/boostorg/mp11) takes the opposite approach from Hana: it's a minimal layer over standard type traits, designed to feel like a natural extension of `<type_traits>`. The naming convention is deliberately short (`mp_list`, `mp_transform`, `mp_find`), and the library adds almost no compile-time overhead.

```cpp
#include <boost/mp11.hpp>
namespace mp = boost::mp11;

using Types = mp::mp_list<int, double, char, float, long>;

// Filter integral types
using Integrals = mp::mp_copy_if<Types, std::is_integral>;

// Transform to const-qualified types
using ConstTypes = mp::mp_transform<std::add_const, Types>;

// Check if all types are trivial
static_assert(mp::mp_all_of<Types, std::is_trivial>::value);

// Find index of a type
constexpr std::size_t idx = mp::mp_find<Types, double>::value;
static_assert(idx == 1);

// Replace a type
using Replaced = mp::mp_replace_at<Types, mp::mp_size_t<1>, std::string>;
// Result: mp_list<int, std::string, char, float, long>

// Compute set intersection
using Set1 = mp::mp_list<int, double, char>;
using Set2 = mp::mp_list<double, float, int>;
using Intersection = mp::mp_set_intersection<Set1, Set2>;
// Result: mp_list<int, double>
```

**Key strength:** Mp11 is already in Boost, which many C++ projects depend on. It uses short, memorable names and provides the best balance of features and compile-time overhead. Mp11 is also the most "standard-like" — many of its patterns are being considered for future C++ standards.

**Trade-offs:** Algorithm coverage is slightly less comprehensive than Brigand (no built-in `sort`), and it's type-only — no value computation like Hana.

## Metal: Minimalist and SFINAE-Friendly

[Metal](https://github.com/brunocodutra/metal) is the most minimalist library in this comparison. It provides exactly one data structure (`metal::list`) and a focused set of algorithms, all designed to be SFINAE-friendly and produce no diagnostics on failure.

```cpp
#include <metal.hpp>

using Types = metal::list<int, double, char, float>;

// Map: apply a lambda to each element
using Pointers = metal::transform<metal::lambda<std::add_pointer>, Types>;

// Find if a type exists (SFINAE-friendly)
using Found = metal::find<Types, double>;  // metal::number<1>

// Count matching types
using Count = metal::count_if<Types, std::is_integral>;  // metal::number<2>

// SFINAE-friendly containment check
template<typename List, typename T>
using contains = metal::not_<std::is_same<
    metal::find<List, T>,
    metal::size<List>
>>;
```

**Key strength:** Metal's SFINAE-friendly design means failed lookups don't produce hard errors — they produce a sentinel value (`metal::size<List>`) that you can check. This is invaluable in generic library code where a type might or might not be present.

**Trade-offs:** The smallest algorithm set. No sort, no set operations. Metal is best used as a building block for other libraries rather than a direct consumption API.

## Choosing the Right Library

| Use Case | Recommended Library |
|----------|-------------------|
| Heterogeneous type + value computation | Boost.Hana |
| Heavy type-level algorithms (sort, set ops) | Brigand |
| Already using Boost, want minimal overhead | Boost.Mp11 |
| Building SFINAE-friendly generic libraries | Metal |
| Standardization-track features | Boost.Mp11 |

## Why Compile-Time Metaprogramming Matters

Compile-time computation isn't just a C++ curiosity — it directly improves runtime performance, safety, and maintainability. Libraries like Hana and Mp11 enable patterns that would otherwise require runtime overhead or code duplication.

**Zero-Cost Abstractions.** Template metaprogramming allows you to generate optimized code paths at compile time. A `hana::if_` branch on a compile-time condition generates only the taken branch — no branch prediction, no dead code, no runtime overhead. This is essential for performance-critical systems like game engines, high-frequency trading, and embedded controllers.

**Type Safety Without Runtime Checks.** Compile-time type manipulation eliminates entire categories of runtime errors. When you use `mp11::mp_all_of` to verify that every type in a list satisfies a trait, the check happens at compile time. If it fails, you get a clear error message before the binary is even produced — not a segfault in production.

**Generic Library Development.** If you're building a C++ library that needs to work with unknown user types, template metaprogramming is the only viable approach. Libraries like Metal are designed specifically for this use case — their SFINAE-friendly API means you can query type properties without triggering hard compilation errors when the property doesn't exist.

**Reduced Code Duplication.** A single `mp11::mp_transform` call replaces dozens of hand-written template specializations. For teams maintaining large C++ codebases, metaprogramming libraries reduce the surface area for bugs and make refactoring safer. The compiler verifies type relationships that would otherwise be implicit conventions documented in comments.

For understanding how these compile-time techniques integrate with modern C++ build systems, see our [Compiler Explorer guide](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) for exploring template instantiation chains. For related C++ developer infrastructure, our [DI containers comparison](../2026-06-22-cpp-dependency-injection-containers-boost-di-google-fruit-kangaru/) shows how compile-time injection benefits from metaprogramming. For signal-slot patterns that use template techniques, see our [event libraries guide](../2026-06-22-signal-slot-event-libraries-boost-signals2-sigslot-libsigcpp/).

## FAQ

### Isn't template metaprogramming being replaced by constexpr?

No — they serve different purposes. Constexpr handles value computation at compile time (math, string operations, data structures). Template metaprogramming handles type computation at compile time (generating new types, type-level algorithms, conditional type selection). They complement each other: Hana explicitly combines both paradigms, and C++20 concepts reduce the need for some SFINAE patterns, but type manipulation is still fundamentally a template-level activity.

### Which library compiles fastest?

Boost.Mp11 adds the least compile-time overhead because it's a thin wrapper over built-in type traits. Brigand is engineered for compilation speed and often outperforms Boost.MPL by 3-5x. Metal is also very fast due to its minimalism. Boost.Hana is the slowest to compile because it instantiates many intermediate types for its heterogeneous value-type computation model. In practice, all four are fast enough for typical use; compilation speed only becomes a concern with thousands of type transformations.

### Can I mix these libraries in the same project?

Yes, with adapter functions. For example, converting between `hana::tuple` and `mp11::mp_list` requires explicit conversion since they use different internal representations. Brigand and Metal lists are relatively easy to convert because they use similar recursive list structures. The most common pattern is to use Mp11 for everyday type traits and Brigand for heavy algorithm work (sorting, set operations).

### Do I need Boost to use Hana or Mp11?

Hana and Mp11 are part of Boost, but both are header-only and depend only on a small subset of Boost (mainly Boost.Config and Boost.Core). You can extract just the library you need using `bcp` (Boost Copy) or use standalone distributions. Mp11 in particular has very few Boost dependencies and is easy to vendor into a project as a single directory.

### Are there C++20 replacements for these libraries?

C++20 introduces concepts, which eliminate many SFINAE use cases, and `requires` clauses simplify constrained templates. However, type-level algorithms (filtering, transforming, sorting type lists) are not addressed by C++20. The Reflection TS (targeting C++26 or later) may eventually provide a standard replacement for some of these patterns. For now, Mp11 remains the closest thing to a "standard" library — several of its patterns are explicitly referenced in WG21 papers as candidates for future standardization.

### How do I debug template metaprogramming errors?

Template error messages are notoriously verbose, but these libraries include static assertions that produce somewhat cleaner messages. For Brigand, failed assertions include the types involved. For Hana, compile-time assertions use `hana::detail::assert_` for readable errors. The most effective debugging technique is to use `static_assert` with `std::is_same` to verify intermediate type computations one step at a time. Compiler Explorer (godbolt.org) with Clang's `-fdiagnostics-show-template-tree` flag is invaluable for tracing template instantiation chains.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Template Metaprogramming Libraries: Boost.Hana vs Boost.Mp11 vs Brigand vs Metal",
  "description": "Deep dive into four C++ template metaprogramming libraries — Boost.Hana, Boost.Mp11, Brigand, and Metal — comparing their approaches to compile-time type computation, algorithm coverage, and practical use cases.",
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