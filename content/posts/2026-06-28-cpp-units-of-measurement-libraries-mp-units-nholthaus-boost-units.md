---
title: "C++ Units of Measurement Libraries: mp-units vs nholthaus/units vs Boost.Units — Type-Safe Dimensional Analysis"
date: "2026-06-28"
tags: ["c++", "units", "dimensional-analysis", "type-safety", "scientific-computing", "metaprogramming", "developer-libraries", "comparison", "guide"]
draft: false
---

## Introduction

In 1999, NASA lost the $125 million Mars Climate Orbiter because one team used metric units (newton-seconds) while another used imperial units (pound-seconds). The spacecraft entered the Martian atmosphere at the wrong altitude and disintegrated. Twenty-five years later, unit conversion errors still cause bugs in everything from medical device firmware to financial trading systems.

C++ units libraries solve this by encoding physical dimensions directly into the type system. When you multiply a `Length` by a `Force`, the compiler can verify the result is an `Energy` — at compile time, with zero runtime overhead. This article compares three leading C++ libraries that bring type-safe dimensional analysis to your code: **mp-units** (1,438 stars, C++20), **nholthaus/units** (1,050 stars, C++14), and **Boost.Units** (39 stars as standalone module, part of Boost).

## Comparison Table

| Feature | mp-units | nholthaus/units | Boost.Units |
|---------|----------|-----------------|-------------|
| **GitHub Stars** | 1,438 | 1,050 | 39 (module) |
| **C++ Standard** | C++20 (concepts) | C++14 | C++11 |
| **License** | MIT | MIT | Boost Software License |
| **Compile-Time Safety** | Full (concepts) | Full (templates) | Full (templates) |
| **Custom Units** | Easy | Easy | Verbose |
| **ISO 80000 Compliance** | Yes | Partial | No |
| **Quantity Kinds** | Strong typing (length≠width) | Weak (same dimension) | Weak (same dimension) |
| **User-Defined Literals** | Yes (`_m`, `_kg`, `_s`) | Yes | Limited |
| **Output Formatting** | Built-in (`{fmt}`) | Stream operators | Stream operators |
| **Non-SI Systems** | Imperial, CGS, Natural | Imperial, maritime | Custom only |
| **Documentation Quality** | Excellent (mpusz.github.io) | Good (README + tests) | Good (Boost docs) |
| **Header-Only** | Yes | Yes | Yes |
| **Active Maintenance** | Yes (weekly commits, 2026) | Moderate (last 2026-01) | Stable (Boost release cycle) |

## mp-units: The C++20 Standard Approach

mp-units by Mateusz Pusz represents the cutting edge of C++ units libraries. It leverages C++20 concepts to provide the richest compile-time safety guarantees available, and its design has influenced the proposed C++ standard units library (P1935).

**Installation:**
```bash
# Via Conan
conan install --requires=mp-units/2.3.0

# Or fetch the header-only library
git clone https://github.com/mpusz/mp-units
```

A basic example demonstrating mp-units' type safety:

```cpp
#include <mp-units/systems/si/si.h>
using namespace mp_units;
using namespace mp_units::si::unit_symbols;

// Compile-time dimensional analysis
QuantityOf<isq::length> auto height = 1.8 * m;       // 1.8 meters
QuantityOf<isq::mass> auto weight = 75.0 * kg;        // 75 kilograms
QuantityOf<isq::time> auto duration = 10.0 * s;       // 10 seconds

// Computed quantities preserve type safety
QuantityOf<isq::speed> auto velocity = height / duration;  // 0.18 m/s
QuantityOf<isq::energy> auto kinetic = 0.5 * weight * velocity * velocity;

// This WOULD NOT COMPILE — adding length to mass is a type error:
// auto nonsense = height + weight;  // ERROR: incompatible quantity kinds

// Output with automatic unit formatting
std::cout << fmt::format("Kinetic energy: {} ({} J)
",
    kinetic, kinetic.in(J));
```

mp-units distinguishes between **quantity kinds** — for example, `length` and `width` are both physically dimensionless but semantically different. The library prevents you from accidentally assigning a width to a length variable, even though both are meters:

```cpp
QuantityOf<isq::length> auto len = 5.0 * m;   // length
QuantityOf<isq::width> auto wid = 3.0 * m;     // width

// len = wid;  // COMPILE ERROR: cannot assign width to length
len = 5.0 * m;  // OK: literal '5.0 * m' is a generic length
```

This level of type safety extends to derived units. If your physics simulation calculates torque (newton-meters) and your control system expects work (joules), mp-units prevents the mix-up — even though both are expressed in the same base units (kg·m²/s²).

## nholthaus/units: Pragmatic C++14 Compatibility

Nic Holthaus's units library takes a more pragmatic approach, targeting C++14 compatibility for projects that can't yet adopt C++20. Despite the lower language requirement, it delivers impressive compile-time safety with a clean, readable API.

**Installation:**
```bash
git clone https://github.com/nholthaus/units
# Header-only — just include the path
```

Basic usage:

```cpp
#include "units.h"
using namespace units::literals;

// Type-safe unit arithmetic
auto distance = 150.0_m;          // meters
auto time = 9.58_s;               // seconds
auto speed = distance / time;     // meters/second — type is deduced

// Convert between unit systems
auto speed_mph = speed.convert<units::miles_per_hour>();
std::cout << "Speed: " << speed_mph() << " mph\n";

// Prevent unit errors at compile time
auto mass = 80.0_kg;              // kilograms
auto force = mass * 9.81_mps2;    // newtons (kg·m/s²) — type is deduced
auto energy = force * distance;   // joules — compiler verifies dimensions
```

nholthaus/units includes built-in support for imperial and maritime units:

```cpp
using namespace units::imperial::literals;

auto altitude = 35000.0_ft;       // feet
auto fuel = 12000.0_lb;           // pounds
auto range = 3500.0_nmi;          // nautical miles

// Convert to SI for calculations
auto altitude_m = altitude.convert<units::meter>();
```

The library's strength is its balance between type safety and ease of adoption. Since it only requires C++14, it can be integrated into older codebases, embedded systems with limited compiler support, and projects that haven't migrated to C++20 concepts.

## Boost.Units: The Established Standard

Boost.Units has been part of the Boost C++ Libraries since 2007, making it the most battle-tested option. While it predates modern C++ features, it provides rock-solid dimensional analysis with extensive documentation and community support.

**Installation:**
```bash
# Via package manager
apt install libboost-dev        # Debian/Ubuntu
brew install boost              # macOS

# Or via Conan
conan install --requires=boost/1.85.0
```

Basic usage:

```cpp
#include <boost/units/systems/si.hpp>
#include <boost/units/systems/si/io.hpp>
#include <iostream>
using namespace boost::units;

// Define quantities with explicit types
quantity<si::length> distance = 100.0 * si::meters;
quantity<si::time> duration = 9.58 * si::seconds;
quantity<si::velocity> speed = distance / duration;  // type-safe

// Conversion between units
quantity<si::length> height(30000.0 * si::feet);  // imperial → SI
std::cout << "Height: " << height << std::endl;   // prints in meters

// Custom unit system example
struct pixel_base_unit : base_unit<pixel_base_unit, length_dimension, 1> {};
typedef make_system<pixel_base_unit>::type pixel_system;
typedef unit<length_dimension, pixel_system> pixel_length;

quantity<pixel_length> screen_width(1920.0 * pixel_length());
```

Boost.Units' main limitation is verbosity. Defining custom units requires substantial boilerplate compared to mp-units or nholthaus/units. It also doesn't distinguish between quantity kinds — two `si::length` values can be freely assigned regardless of whether they represent height, width, or depth.

## Deployment Architecture: Integrating Units Libraries into Build Pipelines

When adding a units library to an existing C++ project, the header-only nature of all three options simplifies integration:

```cmake
# CMakeLists.txt — choose one:

# mp-units (C++20 required)
find_package(mp-units REQUIRED)
target_link_libraries(my_app PRIVATE mp-units::mp-units)

# nholthaus/units (C++14+)
target_include_directories(my_app PRIVATE ${UNITS_INCLUDE_DIR})
target_compile_features(my_app PRIVATE cxx_std_14)

# Boost.Units
find_package(Boost REQUIRED COMPONENTS units)
target_link_libraries(my_app PRIVATE Boost::units)
```

For build performance, all three libraries are compile-time only — they add zero runtime overhead after optimization. Modern compilers (GCC 13+, Clang 18+) optimize away all unit wrapper types, producing identical assembly to raw `double` arithmetic.

For related scientific computing tooling, see our [C++ scientific computing libraries guide](../2026-06-27-cpp-scientific-computing-libraries-gsl-alglib-boostmath/). If you're managing C++ dependencies, our [package management comparison](../2026-06-18-self-hosted-c-cpp-package-management-conan-vcpkg-spack/) covers Conan, vcpkg, and Spack. For ensuring correctness, the [C++ unit testing frameworks guide](../2026-06-21-cpp-unit-testing-frameworks-catch2-doctest-gtest-boost-test/) covers Catch2, doctest, and Google Test.

## FAQ

### Do units libraries add runtime overhead?

No — all three libraries are designed for zero-overhead abstraction. After compiler optimization (-O2 or higher), the unit wrapper types are completely eliminated, and the generated machine code is identical to raw `double` arithmetic. The type checking happens entirely at compile time.

### Can I use these libraries in embedded systems?

Yes, particularly nholthaus/units which requires only C++14 and has no dependencies. Since the libraries are header-only and generate no runtime code beyond the arithmetic itself, they're suitable for resource-constrained environments. mp-units requires C++20, so your embedded toolchain must support that standard.

### How do I add support for a custom unit not in the library?

mp-units makes this simplest with its quantity point system:
```cpp
inline constexpr struct smoot : named_unit<"smoot", mag<1.702> * si::metre> {} smoot;
QuantityOf<isq::length> auto bridge = 364.4 * smoot;  // Harvard Bridge
```
nholthaus/units uses unit definition macros, while Boost.Units requires defining a new unit system with base dimensions.

### What happens if I mix units from different systems in one expression?

In mp-units and nholthaus/units, the conversion happens automatically when the underlying physical dimension matches. For example, multiplying `5.0 * ft` by `3.0 * m` produces an area in square meters. Boost.Units requires explicit conversion between systems. All three catch dimension mismatches (e.g., adding meters to kilograms) at compile time.

### Is mp-units going to become the C++ standard library solution?

mp-units' design heavily influenced P1935 (the C++ units proposal), and its author Mateusz Pusz is a key contributor to the standardization effort. While the final standardized library will likely differ in API details, adopting mp-units now provides the clearest migration path. The library is actively maintained and tracks the evolving proposal.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election outcomes to technology regulation timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've made good returns predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Units of Measurement Libraries: mp-units vs nholthaus/units vs Boost.Units — Type-Safe Dimensional Analysis",
  "description": "Comprehensive comparison of three C++ dimensional analysis libraries: mp-units (C++20 concepts, 1.4K stars), nholthaus/units (C++14, 1K stars), and Boost.Units (stable, 17 years old). Covers type safety, compile-time guarantees, ISO 80000 compliance, and integration patterns.",
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
