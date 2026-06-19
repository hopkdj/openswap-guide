---
title: "Open-Source Fixed-Point Arithmetic Libraries: libfixmath vs fpm vs CNL vs shopspring/decimal"
date: "2026-06-19"
tags: ["fixed-point", "numeric-libraries", "embedded-systems", "financial-computing", "cpp-libraries", "golang", "deterministic-math"]
draft: false
---

## Introduction

Floating-point arithmetic is not always the right tool. In embedded systems without hardware FPUs, financial applications that demand exact decimal precision, and deterministic simulations that must produce identical results across platforms, **fixed-point arithmetic** provides a compelling alternative. Fixed-point numbers represent fractional values using integer types with an implicit scale factor — trading dynamic range for exact, deterministic computation.

This article compares four leading open-source fixed-point libraries: **libfixmath** (C, cross-platform), **fpm** (C++ header-only), **CNL** (Compositional Numeric Library, C++), and **shopspring/decimal** (Go). Whether you're developing firmware for a microcontroller, building a trading engine, or writing deterministic physics, understanding fixed-point options will save you from floating-point headaches.

| Feature | libfixmath | fpm | CNL | shopspring/decimal |
|--------|-----------|-----|-----|-------------------|
| **Language** | C (ANSI C89) | C++14 header-only | C++17/20 | Go |
| **Fixed Types** | Q16.16 (int32_t) | Custom Qm.n (any int type) | Custom with unit/dimension safety | Arbitrary-precision decimal |
| **Base Type** | Hardware int32 | Any integer (int8 to int64) | Compile-time composable | big.Int |
| **Overflow Handling** | Saturating, wraparound | Configurable | Compile-time range-checked | Panic-capable |
| **Trig Functions** | sin, cos, tan, sqrt, exp, log | User-extendable via templates | Via composition | No (decimal only) |
| **License** | MIT | MIT | Boost 1.0 | MIT |
| **Stars** | 867 | 823 | 691 | 7,414 |
| **Last Updated** | February 2026 | March 2026 | April 2024 | Active (Go ecosystem) |
| **Deterministic** | Yes | Yes | Yes | Yes |

## Understanding Fixed-Point Representation

A fixed-point number in Qm.n format uses m bits for the integer part and n bits for the fractional part, with an implicit binary point between them. For example, Q16.16 format (31 usable bits + 1 sign) represents values from approximately -32,768 to +32,767.99998 with 16 bits of fractional precision (~0.000015 resolution).

```
Q16.16 (int32_t):   |s|iiiiiii iiii iiii|ffff ffff ffff ffff|
                        16 integer bits      16 fractional bits
                    value = integer_part + (fractional_part / 65536)
```

This contrasts with IEEE 754 single-precision float, which uses 23 bits of mantissa and an 8-bit exponent — giving it enormous dynamic range but non-uniform precision that can cause accumulation errors.

### libfixmath: The C Standard-Bearer

libfixmath implements Q16.16 fixed-point math in portable C89, making it usable on virtually any platform — from 8-bit AVR microcontrollers to modern x86 servers. It provides a comprehensive math function library including trigonometry, logarithms, and exponentials, all implemented with lookup tables and polynomial approximations.

```c
// libfixmath example: computing sine on an embedded system
#include <fixmath.h>

fix16_t angle = fix16_from_float(1.5708f);  // pi/2
fix16_t result = fix16_sin(angle);           // should be ~1.0 (Q16.16: 65536)

// Conversion utilities
float f = fix16_to_float(result);            // back to float for display
int32_t raw = result;                        // raw integer for storage/transmission
printf("sin(pi/2) = %f\n", f);              // prints 1.000000
```

libfixmath's trigonometric functions use a 512-entry lookup table with quadratic interpolation, achieving ±0.00003 maximum error for sine and cosine — suitable for motor control, sensor fusion, and display rendering on MCUs without FPUs.

### fpm: Modern C++ Header-Only

fpm (fixed-point math) is a C++14 header-only library that provides arithmetic type `fpm::fixed_point<B, I, F>` where B is the base integer type, I is the number of integer bits, and F is the number of fractional bits. This template-based design means you get compile-time guarantees about value ranges.

```cpp
// fpm example: custom fixed-point type for audio DSP
#include <fpm/fixed.hpp>
#include <fpm/math.hpp>

using audio_sample = fpm::fixed_point<std::int32_t, fpm::fixed_range{1, 30}>;
// 1 integer bit (+1.0 to -1.0 range), 30 fractional bits (very precise)

audio_sample mix(audio_sample a, audio_sample b) {
    return fpm::multiply(a, b);  // saturating multiply, no overflow UB
}

// Automatic promotion prevents precision loss
auto precise = fpm::fixed_point<std::int64_t, fpm::fixed_range{16, 47}>{3.14159};
```

fpm's key innovation is **type-safe arithmetic** — the compiler prevents mixing different fixed-point formats accidentally. Multiplication of a Q8.8 by a Q16.16 automatically promotes to a Q24.24 intermediate, avoiding silent truncation.

### CNL: Compositional Numeric Library

CNL (Compositional Numeric Library) by John McFarlane takes a more ambitious approach — it models numeric types as composable components, similar to how `std::chrono` models time durations. CNL's fixed-point types can express not just value ranges but also physical dimensions and units.

```cpp
// CNL example: dimensional analysis with fixed-point types
#include <cnl/all.h>

using meters = cnl::fixed_point<std::int32_t, cnl::power<-16>>;  // Q16.16
using seconds = cnl::fixed_point<std::int32_t, cnl::power<-12>>; // Q20.12

// Velocity: meters per second, automatically composes units
constexpr auto velocity = cnl::quotient<meters, seconds>{};
auto v = meters{100} / seconds{9};  // Compile-time dimensional safety

// CNL prevents unit errors: assigning meters to seconds is a compile error
// auto oops = seconds{meters{5}};  // ERROR: cannot convert meters to seconds
```

CNL's dimensional analysis prevents entire classes of bugs — like mistaking radians for degrees or confusing velocity with acceleration — at compile time with zero runtime overhead.

### shopspring/decimal: Arbitrary-Precision for Financial Go

shopspring/decimal is the de facto standard for exact decimal arithmetic in Go. Unlike hardware binary types, it stores numbers as arbitrary-precision decimal strings, avoiding the infamous `0.1 + 0.2 != 0.3` floating-point problem entirely.

```go
// shopspring/decimal: financial calculation without rounding errors
import "github.com/shopspring/decimal"

price := decimal.NewFromFloat(19.99)
quantity := decimal.NewFromInt(3)
taxRate := decimal.NewFromFloat(0.0875)

subtotal := price.Mul(quantity)         // 59.97
tax := subtotal.Mul(taxRate).Round(2)   // 5.25 (exact)
total := subtotal.Add(tax)              // 65.22

// Never: float64 total = 19.99 * 3 * 1.0875  // 65.21624999999999... oops!
```

For payment processing, accounting systems, and any domain where "close enough" isn't acceptable, shopspring/decimal is the standard choice in the Go ecosystem.

## Performance Characteristics

Fixed-point arithmetic on integer hardware is generally faster than software-emulated floating-point, but the exact advantage depends on the target architecture:

| Operation | Q16.16 (libfixmath) | IEEE 754 float | Advantage |
|-----------|-------------------|----------------|-----------|
| Add/Subtract | 1 cycle (int32 ADD) | 1 cycle (hardware FPU) | Equal |
| Multiply | ~3 cycles (MUL + SHR) | 1-5 cycles | Depends on FPU |
| Divide | ~20-40 cycles (SDIV) | 14-30 cycles | Variable |
| sin/cos (LUT) | ~30 cycles | 100+ cycles (software) | 3× faster on MCU |
| Memory | 4 bytes | 4 bytes | Equal |

On microcontrollers without hardware FPUs (ARM Cortex-M0, M3, AVR), fixed-point provides **10-50× speedup** over soft-float emulation for trigonometric and transcendental functions.

## Why Self-Host Fixed-Point Math Libraries?

Embedded systems running on bare metal need deterministic, FPU-independent math that produces identical results regardless of the underlying hardware. Fixed-point libraries guarantee bit-exact reproducibility — crucial for safety-critical systems like motor controllers, medical devices, and avionics where "close enough" can have serious consequences.

For more on embedded development infrastructure, see our guide on [embedded Linux build systems](../2026-06-05-embedded-linux-build-yocto-buildroot-openembedded-guide/). For other algorithm-focused library comparisons, check out our [sorting algorithm libraries guide](../2026-06-19-sorting-algorithm-libraries-pdqsort-quadsort-ips4o-glidesort/). And for deterministic simulations that benefit from fixed-point reproducibility, see our [scientific simulation platforms overview](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/).

## Choosing Your Fixed-Point Library

- **libfixmath**: Best for C projects and deeply embedded systems. Battle-tested, portable to C89, comprehensive math function library. Use when you need trigonometric functions on a microcontroller without an FPU.

- **fpm**: Best for modern C++ projects that want type safety without complexity. The template-based design catches precision bugs at compile time. Use for audio DSP, game physics, and any domain where mixing different fixed-point formats is a risk.

- **CNL**: Best for projects that want dimensional analysis alongside fixed-point accuracy. If you need to track units (meters, seconds, radians) through your computation pipeline, CNL's compositional approach prevents entire classes of bugs.

- **shopspring/decimal**: The only choice for Go financial applications. If you're processing payments, invoices, or any monetary values in Go, this library is essentially mandatory for correctness.

## FAQ

### When should I use fixed-point instead of floating-point?

Use fixed-point when: (a) your hardware lacks an FPU (microcontrollers, some embedded Linux boards), (b) you need bit-exact deterministic results across platforms, (c) you're working with financial data where decimal exactness matters, (d) you have a known, bounded value range and want deterministic performance without NaN or infinity edge cases.

### What precision does Q16.16 actually give me?

Q16.16 provides approximately 4.8 decimal digits of fractional precision (1/65536 ≈ 0.000015). For integer values up to ±32767, each fractional step is about 15 microseconds worth of resolution. This is sufficient for motor control, sensor readings, 3D graphics on retro hardware, and audio effects processing.

### Can fixed-point overflow or wrap around?

Yes — fixed-point types based on integer hardware will wrap, saturate, or trigger undefined behavior on overflow depending on the library and compiler settings. libfixmath provides saturating arithmetic (clamps to max/min), fpm makes overflow behavior configurable, and CNL offers compile-time overflow checks via contract programming. Always test with boundary values.

### Is shopspring/decimal the only Go option for decimal math?

There's also `cockroachdb/apd` (arbitrary precision decimal, designed for CockroachDB) and `ericlagergren/decimal` (high-performance Go decimal). shopspring/decimal is the most widely used with 7,400+ stars and the largest ecosystem of integrations, but `apd` from CockroachDB has stronger correctness guarantees for database workloads.

### Do these libraries work on 64-bit hardware efficiently?

On 64-bit hardware with hardware FPU, floating-point may actually be faster than fixed-point for basic arithmetic. The advantage of fixed-point shifts to determinism, exact decimal representation, and avoidance of NaN/infinity — not raw throughput on modern server CPUs. Use fixed-point on 64-bit hardware only when you specifically need one of those properties.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Open-Source Fixed-Point Arithmetic Libraries: libfixmath vs fpm vs CNL vs shopspring/decimal",
  "description": "Compare four open-source fixed-point arithmetic libraries: libfixmath (C), fpm (C++14), CNL (C++ compositional), and shopspring/decimal (Go). Covers Q16.16 format, trigonometric functions, dimensional analysis, and financial decimal arithmetic.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
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
