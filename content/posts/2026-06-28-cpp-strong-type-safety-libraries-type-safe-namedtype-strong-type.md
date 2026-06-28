---
title: "Self-Hosted C++ Type-Safe Programming: type_safe vs NamedType vs strong_type — Preventing Bugs at Compile Time"
date: "2026-06-28"
tags: ["cpp", "type-safety", "developer-tools", "compile-time", "static-analysis", "code-quality"]
draft: false
---

## Introduction

The C++ type system is a powerful tool for catching bugs before they reach production, but raw built-in types (`int`, `double`, `std::string`) carry no semantic meaning. A function `void transfer(int from_account, int to_account, double amount)` compiles just fine when you accidentally swap the account IDs — because both are just `int`.

**Strong typing** solves this by wrapping primitive types in distinct, non-interchangeable wrapper types. If `AccountId` and `Amount` are different types, the compiler rejects the swapped-argument mistake at compile time — a category of bug that is impossible to introduce.

This article compares three modern C++ libraries that make strong typing practical and ergonomic: **type_safe** by Jonathan Müller (foonathan), **NamedType** by Jonathan Boccara, and **strong_type** by Björn Fahller (rollbear). Each takes a different approach to the same fundamental problem.

| Feature | type_safe | NamedType | strong_type |
|---------|-----------|-----------|-------------|
| **Stars** | 1,641 | 825 | 481 |
| **Approach** | Zero-overhead wrappers | CRTP mixin-based | Additive composition |
| **Arithmetic support** | Yes (checked) | Via skill mixins | Via modifiers |
| **Comparison operators** | Full | Opt-in | Automatic |
| **Streaming (<<)** | Yes | Opt-in | Opt-in |
| **C++ standard** | C++11/14 | C++14 | C++14/17/20 |
| **Header-only** | Yes | Yes | Yes |
| **Integrates with existing code** | Explicit conversions | Implicit via `get()` | Explicit `.value()` |
| **Serialization support** | Manual | Via skill | Manual |
| **Documentation quality** | Reference + blog | Extensive blog series | Header + examples |

## type_safe: The Zero-Overhead Safety Net

**type_safe** (`foonathan/type_safe`) by Jonathan Müller is the most comprehensive type-safety library in the C++ ecosystem. At 1,641 stars, it's widely adopted in safety-critical and embedded systems where preventing bugs at compile time is paramount.

type_safe goes beyond simple strong typedefs and provides safe alternatives to common C++ primitives: `ts::integer<T>` (checked arithmetic), `ts::floating_point<T>` (no NaN/Inf), `ts::boolean` (no implicit int conversion), and `ts::constrained_type` (runtime value validation).

### CMake Integration

```cmake
FetchContent_Declare(type_safe
    GIT_REPOSITORY https://github.com/foonathan/type_safe.git
    GIT_TAG v0.2.4
)
FetchContent_MakeAvailable(type_safe)
target_link_libraries(your_target PRIVATE foonathan::type_safe)
```

### Strong Typedefs with Arithmetic

```cpp
#include <type_safe/strong_typedef.hpp>
#include <type_safe/integer.hpp>

// Define domain types
struct kilogram_tag {};
using Kilogram = ts::strong_typedef<kilogram_tag, double>;

struct meter_tag {};
using Meter = ts::strong_typedef<meter_tag, double>;

struct velocity_tag {};
using Velocity = ts::strong_typedef<velocity_tag, double,
    ts::strong_typedef_op::addition,
    ts::strong_typedef_op::subtraction,
    ts::strong_typedef_op::output_operator
>;

// Custom operations (type-safe division)
Velocity operator/(Kilogram kg, Meter m) {
    return Velocity(static_cast<double>(kg) / static_cast<double>(m));
}

void physics_example() {
    Kilogram mass(5.0);
    Meter distance(10.0);
    
    // This compiles — explicit conversion
    Velocity v = mass / distance;
    
    // Compile error! Cannot add Kilogram + Meter
    // auto invalid = mass + distance;  // error: no match for operator+
    
    std::cout << "Velocity: " << v << " m/s
";
}
```

The `ts::strong_typedef_op` template parameters control which operators are generated — addition, subtraction, comparison, hashing, I/O — giving fine-grained control over what operations are permitted on each domain type.

### Checked Integer Arithmetic

```cpp
#include <type_safe/integer.hpp>

void safe_calculation() {
    ts::integer<int> balance(100);
    ts::integer<int> withdrawal(30);
    
    // Checked subtraction — throws ts::overflow_error on overflow
    balance -= withdrawal;
    
    // Narrowing conversions are explicit
    ts::integer<short> small = ts::narrow<short>(balance);
    
    // Underflow is caught
    try {
        balance -= ts::integer<int>(200);  // throws!
    } catch (const ts::overflow_error& e) {
        std::cerr << "Overflow detected: " << e.what() << '
';
    }
}
```

type_safe's `ts::integer<T>` wraps any integer type with checked arithmetic — additions, subtractions, and multiplications that would overflow throw exceptions rather than silently wrapping around. This is invaluable for financial calculations, embedded systems, and any domain where integer overflow could have serious consequences.

## NamedType: The Fluent API Approach

**NamedType** (`joboccara/NamedType`) by Jonathan Boccara takes a different philosophical approach. Instead of providing a rigid set of safety wrappers, it uses CRTP (Curiously Recurring Template Pattern) with composable "skills" — mixins that add specific capabilities to your strong type.

### Installation

```cmake
FetchContent_Declare(NamedType
    GIT_REPOSITORY https://github.com/joboccara/NamedType.git
    GIT_TAG main
)
FetchContent_MakeAvailable(NamedType)
# NamedType is header-only — just include the directory
target_include_directories(your_target PRIVATE ${namedtype_SOURCE_DIR}/include)
```

### Composable Skills Pattern

```cpp
#include <NamedType/named_type.hpp>

// Define a strong type with specific skills
using Meter = fluent::NamedType<double, struct MeterTag,
    fluent::Addable,           // operator+
    fluent::Comparable,        // operator<, ==, etc.
    fluent::Printable,         // operator<<
    fluent::Multiplicable,     // operator*
    fluent::Dividable          // operator/
>;

using Second = fluent::NamedType<double, struct SecondTag,
    fluent::Comparable,
    fluent::Printable
>;

// Each skill adds specific capabilities to the type
void named_type_example() {
    Meter length(15.0);
    Meter width(10.0);
    
    // Arithmetic: Addable skill enables this
    Meter perimeter = length + width + length + width;
    std::cout << "Perimeter: " << perimeter.get() << " meters
";
    
    // Comparisons: Comparable skill enables this
    if (length > width) {
        std::cout << "Length is greater
";
    }
    
    // No implicit conversion!
    // Second time(5.0);
    // auto invalid = length + time;  // COMPILE ERROR!
}
```

The skill-based approach is particularly elegant for domain modeling — you define exactly which operations make sense for each type, and the compiler enforces them. A `UserId` might be `Comparable` and `Printable` but not `Addable`, while a `Distance` would be `Addable` and `Multiplicable`.

## strong_type: Additive Composition for Modern C++

**strong_type** (`rollbear/strong_type`) by Björn Fahller represents the most modern approach, leveraging C++17 and C++20 features for maximum ergonomics. Rather than CRTP mixins, it uses an additive composition model where you specify which properties (modifiers) your type should have.

### CMake FetchContent

```cmake
FetchContent_Declare(strong_type
    GIT_REPOSITORY https://github.com/rollbear/strong_type.git
    GIT_TAG main
)
FetchContent_MakeAvailable(strong_type)
target_include_directories(your_target PRIVATE ${strong_type_SOURCE_DIR}/include)
```

### Modern Composition API

```cpp
#include <strong_type/strong_type.hpp>
#include <strong_type/equality.hpp>
#include <strong_type/ordered.hpp>
#include <strong_type/arithmetic.hpp>
#include <strong_type/iostream.hpp>

// Compose a type with the properties you need
using Temperature = strong::type<double, struct TemperatureTag,
    strong::equality,          // operator==, !=
    strong::ordered,           // operator<, >, <=, >=
    strong::ordered_with<int>, // compare with plain int
    strong::ostreamable,       // operator<<
    strong::arithmetic         // +, -, *, /
>;

using Pressure = strong::type<double, struct PressureTag,
    strong::equality,
    strong::ordered,
    strong::ostreamable
    // Note: no arithmetic — Pressure * Pressure doesn't make physical sense
>;

void weather_station() {
    Temperature indoor_temp(21.5);
    Temperature outdoor_temp(15.0);
    
    // Arithmetic on Temperature
    Temperature avg = (indoor_temp + outdoor_temp) / 2.0;
    std::cout << "Average temp: " << avg << "°C
";
    
    // Comparisons with plain int
    if (outdoor_temp < 18) {
        std::cout << "Cold outside!
";
    }
    
    // Type safety: Temperature and Pressure are different types
    Pressure p(1013.25);
    // auto error = indoor_temp + p;  // COMPILE ERROR!
}
```

strong_type's additive model is particularly clean — you can see at a glance exactly what operations a type supports by reading its template parameter list. The library also supports difference types (subtracting two `Temperature` values produces a `Temperature::difference`), which is useful for dimensional analysis.

## Real-World Integration Pattern

Here's a practical example combining strong types with a REST API handler, where type safety prevents common API parameter bugs:

```cpp
#include <strong_type/strong_type.hpp>

// API parameter types
using UserId = strong::type<int64_t, struct UserIdTag, 
    strong::equality, strong::ordered, strong::ostreamable>;

using AccountId = strong::type<int64_t, struct AccountIdTag,
    strong::equality, strong::ostreamable>;

using Amount = strong::type<double, struct AmountTag,
    strong::equality, strong::ordered, strong::arithmetic>;

// The compiler now prevents parameter-swapping bugs
class BankingService {
public:
    void transfer(UserId from_user, AccountId from_account, 
                  AccountId to_account, Amount value) {
        // Compiler enforces correct argument order — impossible to swap UserId/AccountId
        validate_user(from_user);
        debit_account(from_account, value);
        credit_account(to_account, value);
    }
};

// Usage:
// service.transfer(user_42, acct_A, acct_B, Amount(100.0));  // CORRECT
// service.transfer(acct_A, user_42, acct_B, Amount(100.0));   // COMPILE ERROR!
```

For developers working with physical quantities, strong types pair naturally with our [C++ Units of Measurement Libraries guide](../2026-06-28-cpp-units-of-measurement-libraries-mp-units-nholthaus-boost-units/) — dimensional analysis libraries use the same strong typing principles to prevent mixing meters with seconds. If you're building APIs that benefit from type-level validation, our [C++ Enum Reflection Libraries overview](../2026-06-26-cpp-enum-reflection-magic-enum-better-enums-wise-enum/) covers complementary techniques for making enum types safer and more expressive. For a different angle on type safety, see our [C++ Template Linear Algebra Libraries comparison](../2026-06-27-cpp-template-linear-algebra-libraries-armadillo-blaze-xtensor/) where matrix dimensions are enforced at compile time.


## FAQ

### Do strong types incur runtime overhead?

**No.** All three libraries are designed for zero runtime overhead — the type wrappers are templates that the compiler optimizes away entirely. A `strong::type<double, Tag>` has the same memory layout and assembly as a plain `double`. The type checking happens at compile time; at runtime, the code is identical to using raw types. This is confirmed by compiler explorer: the generated assembly for operations on strong types is bit-for-bit identical to operations on the underlying type at any optimization level `-O1` or above.

### How do these libraries compare to `std::chrono`?

`std::chrono::duration` is actually a strong type built into the standard library — it prevents adding seconds to meters and converts between units automatically. The libraries in this comparison generalize that concept to ANY domain type. If you've used `std::chrono` and appreciated never accidentally mixing seconds with milliseconds, you already understand the value proposition of strong typing. type_safe, NamedType, and strong_type extend this safety to account IDs, temperatures, distances, voltages, and every other numeric value in your codebase.

### Can I serialize strong types to JSON/Protobuf?

Yes, but you need to handle conversion explicitly. The safest pattern is to extract the underlying value for serialization and reconstruct the strong type on deserialization:

```cpp
// Serialization (to JSON)
json j;
j["temperature"] = static_cast<double>(indoor_temp);  // explicit extraction

// Deserialization (from JSON)
Temperature t(j["temperature"].get<double>());  // explicit construction
```

For Protobuf, store the raw value in the message and wrap it in the strong type when constructing domain objects. This is actually a feature — the explicit boundary between serialization format and domain types is where bugs are most likely to be caught.

### Which library should I choose for a new C++20 project?

For C++20, **strong_type** offers the cleanest API with its additive composition model. The syntax `strong::type<double, Tag, strong::equality, strong::arithmetic>` makes it immediately clear what operations a type supports, and the C++20 concepts integration provides excellent compiler error messages. For projects requiring C++14/17 compatibility, **NamedType**'s skill-based approach is equally capable. If you need checked arithmetic (overflow detection) in addition to strong typing, **type_safe** is the best choice — it includes `ts::integer<T>` with built-in overflow checking that the other two libraries don't provide.

### How do strong types interact with template code and generic algorithms?

Strong types work well with template code, but you may need to be explicit about conversions:

```cpp
template<typename T>
T square(T value) {
    return value * value;  // Works if T has operator*
}

Temperature t(10.0);
Temperature result = square(t);  // ✓ Works — strong_type has arithmetic modifier

// For generic algorithms expecting raw values:
std::vector<Temperature> temps = {Temperature(20), Temperature(22), Temperature(19)};
double sum = std::accumulate(temps.begin(), temps.end(), 0.0,
    [](double acc, Temperature t) { return acc + static_cast<double>(t); });
```

The libraries provide `get()` or `value()` methods or `static_cast` for accessing the underlying value when interfacing with generic code that expects raw numeric types. Note that `std::accumulate` needs the explicit conversion in the lambda — this is intentional: the library forces you to be explicit at the boundary between strongly-typed domain code and generic numeric algorithms.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Type-Safe Programming: type_safe vs NamedType vs strong_type — Preventing Bugs at Compile Time",
  "description": "Comprehensive comparison of three C++ strong typing libraries: type_safe (zero-overhead safety wrappers), NamedType (CRTP skill-based mixins), and strong_type (additive composition). Includes CMake integration, real-world API safety patterns, and zero-overhead guarantee analysis.",
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
