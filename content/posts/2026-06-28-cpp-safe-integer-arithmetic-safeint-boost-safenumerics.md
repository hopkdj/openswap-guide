---
title: "Self-Hosted C++ Safe Integer Arithmetic: SafeInt vs Boost.SafeNumerics — Preventing Integer Overflow at Compile Time"
date: "2026-06-28"
tags: ["cpp", "integer-safety", "security", "developer-tools", "static-analysis", "compile-time", "boost"]
draft: false
---

## Introduction

Integer overflow is one of the most insidious bug categories in C and C++ — it silently wraps around, corrupting data without any visible crash or error message. Integer overflow vulnerabilities have caused critical security exploits (Stagefright, Android mediaserver), financial calculation errors, and subtle data corruption in everything from embedded firmware to cloud infrastructure.

The C++ standard's approach to integer overflow has historically been "undefined behavior for signed integers, wrap-around for unsigned" — but neither behavior is usually what the programmer intended. Two libraries address this problem head-on: **SafeInt** (originally by Microsoft, now community-maintained) and **Boost.SafeNumerics**, which brings exhaustive compile-time and runtime overflow detection to C++ arithmetic.

| Feature | SafeInt | Boost.SafeNumerics |
|---------|---------|-------------------|
| **Stars** | 249 | 222 (Boost module) |
| **Arithmetic model** | Runtime checked | Compile-time + runtime checked |
| **Exception policy** | Throws on overflow | Configurable (throw/trap/log/ignore) |
| **Mixed-type operations** | Automatic promotion | Policy-controlled |
| **Integration** | Single header | Boost library (module dependency) |
| **C++ standard** | C++11+ | C++14+ |
| **Performance** | Minimal overhead | Zero overhead for known-safe ops |
| **Compiler support** | GCC, Clang, MSVC | GCC, Clang |
| **Narrowing detection** | Yes | Yes (with trap policy) |
| **Bitwise operations** | Not checked | Configurable |

## SafeInt: Microsoft's Battle-Tested Integer Safety

**SafeInt** (`dcleblanc/SafeInt`) originated in Microsoft's Office and Windows codebases before being open-sourced. At 249 stars, it's a battle-tested single-header library that wraps integer operations with runtime overflow detection. Its API is deliberately minimal — you replace `int` with `SafeInt<int>` and get overflow protection with minimal code changes.

### Integration

SafeInt is a single header file — just copy `SafeInt.hpp` into your project:

```cpp
#include "SafeInt.hpp"

void safeint_example() {
    SafeInt<int> balance(1000000);
    SafeInt<int> deposit(500000);
    SafeInt<int> bonus(2000000);
    
    // These operations are checked at runtime
    SafeInt<int> new_balance = balance + deposit;   // OK: 1,500,000
    std::cout << "Balance: " << new_balance << '
';
    
    try {
        SafeInt<int> overflow = balance + bonus;    // Throws SafeIntException!
    } catch (const SafeIntException& e) {
        std::cerr << "Overflow detected: " << e.what() 
                  << " (error code: " << e.m_code << ")
";
    }
    
    // Mixed integer widths are handled automatically
    SafeInt<int32_t> small(1000);
    SafeInt<int64_t> large(100000000000);
    auto result = small + large;  // Result is SafeInt<int64_t> — safe promotion
}
```

SafeInt handles all the edge cases: adding a large positive number to a large positive (overflow), subtracting from a negative (underflow), multiplication overflow, division by zero, and mixed-type promotions. The library catches these at runtime and throws descriptive exceptions.

### CMake Docker Compose Setup

```yaml
version: "3.8"
services:
  safe-cpp-builder:
    image: gcc:14
    volumes:
      - ./src:/src
      - ./build:/build
    working_dir: /build
    command: >
      bash -c "
        cmake /src -DCMAKE_BUILD_TYPE=Debug &&
        cmake --build . --parallel &&
        ctest --output-on-failure
      "
```

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
project(SafeIntegerDemo)

# Fetch SafeInt header
FetchContent_Declare(SafeInt
    GIT_REPOSITORY https://github.com/dcleblanc/SafeInt.git
    GIT_TAG main
)
FetchContent_MakeAvailable(SafeInt)
target_include_directories(safe_demo PRIVATE ${safeint_SOURCE_DIR})

add_executable(safe_demo main.cpp)
target_link_libraries(safe_demo PRIVATE SafeInt::SafeInt)
```

## Boost.SafeNumerics: Compile-Time Overflow Prevention

**Boost.SafeNumerics** (`boostorg/safe_numerics`) takes a fundamentally different approach: instead of only checking at runtime, it performs exhaustive compile-time analysis to prove that operations cannot overflow. When it can't prove safety at compile time, it inserts runtime checks — and you can configure what happens when those checks fail.

### Three Safety Policies

Boost.SafeNumerics uses a policy-based design with three configurable behaviors:

```cpp
#include <boost/safe_numerics/safe_integer.hpp>
using namespace boost::safe_numerics;

// 1. Throw on error (like SafeInt)
using SafeIntThrow = safe<int, 
    native,                           // promotion policy
    throw_exception                   // exception policy
>;

// 2. Trap on error (compile-time error if possible overflow)
using SafeIntTrap = safe<int,
    native,
    trap_exception                    // makes it a compile error if overflow possible
>;

// 3. Automatic type promotion (widen to prevent overflow)
using SafeIntAuto = safe<int,
    automatic,                        // auto-promote to larger type
    throw_exception
>;

void policy_examples() {
    // Policy 1: Runtime throw
    SafeIntThrow a(1000000);
    SafeIntThrow b(2000000);
    try {
        auto c = a * b;  // Throws at runtime
    } catch (const std::range_error& e) {
        std::cerr << "Runtime check: " << e.what() << '
';
    }
    
    // Policy 2: Compile-time trap
    constexpr SafeIntTrap x(100);
    constexpr SafeIntTrap y(200);
    // constexpr auto z = x * y;  // COMPILE ERROR: overflow detected!
    // Error: "overflow error: positive overflow" at COMPILE TIME
    
    // Policy 3: Auto-promotion (result type becomes larger)
    SafeIntAuto narrow1(2000000);
    SafeIntAuto narrow2(2000000);
    auto wide = narrow1 * narrow2;  // wide is safe<int64_t> — automatically widened
    std::cout << "Auto-promoted result: " << wide << " (fits in 64-bit)
";
}
```

The `trap_exception` policy is particularly powerful: when applied to `constexpr` operations, the compiler proves the arithmetic is safe and rejects the code if an overflow is detected — turning what would be an undetected runtime bug into a compile-time error.

### Real-World: Financial Calculation Safety

```cpp
#include <boost/safe_numerics/safe_integer.hpp>
#include <boost/safe_numerics/automatic.hpp>

template<typename T>
using SafeMoney = boost::safe_numerics::safe<T, 
    boost::safe_numerics::automatic,
    boost::safe_numerics::throw_exception
>;

class FinancialCalculator {
public:
    struct Transaction {
        SafeMoney<int64_t> quantity;
        SafeMoney<int64_t> unit_price_cents;
    };
    
    SafeMoney<int64_t> calculate_total(const Transaction& txn) {
        // Automatic promotion ensures intermediate doesn't overflow
        auto subtotal = txn.quantity * txn.unit_price_cents;
        
        // Apply tax (8.875% in basis points)
        SafeMoney<int64_t> tax_rate(8875);  // 8.875% = 8875 bps
        auto tax = (subtotal * tax_rate) / SafeMoney<int64_t>(100000);
        
        return subtotal + tax;
    }
};
// The compiler verifies: quantity(≤2^63) * unit_price(≤2^63) fits in ≤126 bits
// automatic policy widens to safe<int128_t> or equivalent if needed
```

### Hybrid Approach: SafeInt + UBSan

For teams hesitant to adopt a new integer type throughout their codebase, a pragmatic approach combines SafeInt for critical code paths with compiler sanitizers for global coverage:

```bash
# Build with UndefinedBehaviorSanitizer for integer overflow detection
cmake -B build -DCMAKE_BUILD_TYPE=Debug     -DCMAKE_CXX_FLAGS="-fsanitize=undefined,integer -fno-sanitize-recover=all"
cmake --build build --parallel

# Run tests — UBSan catches any overflow in non-SafeInt code
./build/tests 2>&1 | grep "overflow"
```

This gives you:
- **SafeInt** for arithmetic in security-critical and financial code paths
- **UBSan** for catching overflow bugs in the remaining 95% of the codebase during testing
- Zero runtime overhead in production (no SafeInt wrapping in non-critical paths)

## Performance Considerations

| Operation | Raw int | SafeInt | Boost.SafeNumerics (auto) |
|-----------|---------|---------|--------------------------|
| Addition | 1 cycle | ~3 cycles (branch + check) | ~3 cycles |
| Multiplication | 3-4 cycles | ~8-12 cycles | ~8-15 cycles (wider type promotion) |
| Division | 10-30 cycles | +branch for zero check | +branch for zero check |
| Constexpr add (trap) | 1 cycle | N/A | 0 runtime overhead (compile-time) |

For most applications, the ~2-10 cycle overhead of checked arithmetic is negligible compared to network I/O, database queries, or memory allocation. In hot loops processing millions of integers, consider using `trap_exception` to get compile-time verification without runtime overhead, or batch validation (check range before entering the loop and use raw integers inside it).

For a broader perspective on preventing memory and arithmetic bugs, see our [Memory Allocators comparison guide](../2026-06-02-memory-allocators-jemalloc-tcmalloc-mimalloc-guide/) which covers heap safety and corruption detection. If you're building safety-critical C++ applications, our [C++ Unit Testing Frameworks guide](../2026-06-21-cpp-unit-testing-frameworks-catch2-doctest-gtest-boost-test/) shows how to integrate overflow detection tests into your CI pipeline. For scientific applications where arithmetic precision is critical, our [C++ Scientific Computing Libraries overview](../2026-06-27-cpp-scientific-computing-libraries-gsl-alglib-boostmath/) covers GSL which also includes safe numeric utilities.


## FAQ

### Why not just use `-ftrapv` or UBSan instead of these libraries?

GCC's `-ftrapv` and Clang's UBSan are excellent tools, but they operate at different levels:

- **UBSan** (`-fsanitize=undefined`) catches overflow at test time but adds runtime overhead and can't guarantee coverage of all code paths
- **`-ftrapv`** aborts the program on signed overflow — not suitable for production where you want graceful error handling
- **SafeInt / Boost.SafeNumerics** give you programmatic control: catch exceptions, log errors, use fallback values, or abort based on your application's needs

The best strategy combines them: use SafeInt/Boost.SafeNumerics for critical paths in production, and UBSan for global coverage during CI testing.

### How do these libraries handle integer promotion rules?

Integer promotion in C++ is notoriously complex. `SafeInt` handles promotions automatically — adding a `SafeInt<int16_t>` to a `SafeInt<int32_t>` safely promotes to `SafeInt<int32_t>`. **Boost.SafeNumerics** gives you control via promotion policies: `native` follows standard C++ rules (which may surprise you), `automatic` widens to the smallest type that can hold the result, and `cpp<T>` enforces standard integer promotion semantics if you need strict compatibility with existing code.

### Can I use these in embedded systems with no exceptions?

**SafeInt** requires exceptions — it throws on overflow. For no-exception environments, use **Boost.SafeNumerics** with an alternative exception policy: `trap_exception` makes overflow a compile-time error for constexpr, or you can create a custom policy that calls an error handler, sets `errno`, or asserts. Alternatively, wrap SafeInt operations in a result type:

```cpp
template<typename T>
std::optional<SafeInt<T>> safe_add(SafeInt<T> a, SafeInt<T> b) {
    try { return a + b; }
    catch (const SafeIntException&) { return std::nullopt; }
}
```

For truly embedded (no heap, no exceptions), write a simple `checked_add` function using compiler built-ins like `__builtin_add_overflow`.

### What's the difference between overflow detection and value range analysis?

Overflow detection (SafeInt, Boost.SafeNumerics with `throw_exception`) catches individual operations that would overflow at runtime. Value range analysis (Boost.SafeNumerics with `trap_exception` or `automatic`) understands the range of possible values for each variable and proves at compile time that operations within those ranges can never overflow. Range analysis is more powerful — it can prove that `(x % 100) + (y % 100)` never overflows even if `x` and `y` are `int` — but it requires more sophisticated compiler support and constexpr annotations.

### How do I migrate an existing codebase to use safe integers?

Start with a gradual approach:

1. **Identify hot spots**: Run UBSan on your test suite and find where overflow actually occurs
2. **Wrap entry points**: Replace raw `int` parameters in public APIs with safe types
3. **Propagate inward**: As you modify functions, convert internal variables too
4. **Use type aliases**: Define `using AccountBalance = SafeInt<int64_t>` so the safety is explicit in the type name

Don't try to convert every `int` to `SafeInt` at once — that changes the ABI and breaks serialization. Start with the functions that handle user input, financial data, buffer sizes, and array indices — these are where overflow bugs cause the most damage.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Safe Integer Arithmetic: SafeInt vs Boost.SafeNumerics — Preventing Integer Overflow at Compile Time",
  "description": "Comprehensive comparison of C++ safe integer libraries: SafeInt (Microsoft's battle-tested runtime overflow detection) and Boost.SafeNumerics (compile-time overflow prevention with policy-based design). Includes Docker Compose build setup, UBSan integration, and embedded systems considerations.",
  "datePublished": "2026-06-28",
  "dateModified": "2026-06-28",
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
