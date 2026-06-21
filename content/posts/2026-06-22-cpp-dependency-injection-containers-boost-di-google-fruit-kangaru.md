---
title: "Self-Hosted C++ Dependency Injection Containers: Boost.DI vs Google Fruit vs Kangaru"
date: "2026-06-22"
tags: ["c-plus-plus", "dependency-injection", "software-architecture", "design-patterns", "ioc-container", "developer-tools"]
draft: false
---

## Introduction

Dependency Injection (DI) is a cornerstone of modern software architecture, enabling loose coupling, testability, and maintainability. While Java developers have long enjoyed mature DI frameworks like Spring and Guice, the C++ ecosystem has developed its own robust solutions tailored to the language's compile-time philosophy and zero-overhead performance requirements.

In this guide, we compare three leading C++ dependency injection containers: **Boost.DI**, **Google Fruit**, and **Kangaru** — examining their API design, compile-time vs runtime trade-offs, performance characteristics, and real-world suitability.

## Why Use Dependency Injection in C++?

Manual dependency management in large C++ codebases quickly becomes unmanageable. Factory functions proliferate, constructors grow unwieldy, and unit testing becomes a nightmare of mock wiring. A DI container automates object graph construction, centralizes configuration, and decouples component implementations from their consumers.

For C++ specifically, DI containers offer additional benefits: compile-time validation of the dependency graph, zero-runtime-overhead injection through template metaprogramming, and automatic deduction of constructor parameters. These are not merely "Java-isms" ported to C++ — they leverage C++'s unique strengths to deliver safety and performance that runtime-reflection-based DI frameworks cannot match.

For managing your C++ project dependencies at the package level, see our [C++ package management guide](../2026-06-18-self-hosted-c-cpp-package-management-conan-vcpkg-spack/). If you're setting up a build pipeline for these libraries, check our [C++ build systems comparison](../2026-04-29-bazel-vs-pants-vs-please-self-hosted-build-systems-guide-2026/).

## Comparison Table

| Feature | Boost.DI | Google Fruit | Kangaru |
|---------|----------|-------------|---------|
| **Stars** | 1,264 | 1,885 | 550 |
| **Approach** | Compile-time (header-only) | Runtime + compile-time | Compile-time (header-only) |
| **C++ Standard** | C++14 | C++11 | C++11 / C++14+ |
| **Configuration Style** | Macro-free, pure C++ | Component-based with modules | Service maps with traits |
| **Error Messages** | Compile-time, detailed | Runtime (with compile safety) | Compile-time, SFINAE-based |
| **Performance** | Zero overhead | Minimal overhead | Zero overhead |
| **Learning Curve** | Moderate | Moderate-High | Low-Moderate |
| **Last Update** | Apr 2026 | Apr 2026 | Jun 2026 |
| **License** | Boost | Apache 2.0 | MIT |

## Boost.DI: Compile-Time Purity

Boost.DI (part of Boost's experimental libraries) takes an uncompromising compile-time approach. There are no macros, no code generation, and no runtime type information. Everything is resolved through C++ template metaprogramming, meaning the dependency graph is validated at compile time.

```cpp
// Boost.DI example — constructor injection with automatic wiring
#include <boost/di.hpp>
namespace di = boost::di;

class ILogger {
public:
    virtual ~ILogger() = default;
    virtual void log(const std::string& msg) = 0;
};

class ConsoleLogger : public ILogger {
public:
    void log(const std::string& msg) override {
        std::cout << "[LOG] " << msg << std::endl;
    }
};

class FileLogger : public ILogger {
    std::ofstream file_;
public:
    explicit FileLogger(const std::string& path) : file_(path) {}
    void log(const std::string& msg) override { file_ << msg << std::endl; }
};

class UserService {
    std::shared_ptr<ILogger> logger_;
public:
    explicit UserService(std::shared_ptr<ILogger> logger) : logger_(logger) {}
    void createUser(const std::string& name) {
        logger_->log("Creating user: " + name);
    }
};

int main() {
    auto injector = di::make_injector(
        di::bind<ILogger>.to<ConsoleLogger>()
    );
    auto service = injector.create<UserService>();
    service.createUser("Alice");
}
```

Boost.DI's strength is that invalid bindings are caught at compile time — there is no runtime discovery of missing dependencies. The library auto-wires constructors using template argument deduction, so simple cases require zero configuration. For complex scenarios, it supports named parameters, assisted injection (factory methods), and module-based organization.

### Integration with CMake

```cmake
# FetchContent integration — no system package required
include(FetchContent)
FetchContent_Declare(
    boost_di
    GIT_REPOSITORY https://github.com/boost-ext/di.git
    GIT_TAG v1.3.0
)
FetchContent_MakeAvailable(boost_di)
target_link_libraries(myapp PRIVATE boost_di)
```

## Google Fruit: Component-Based Runtime DI

Google Fruit takes a hybrid approach, combining compile-time dependency checking with a runtime injector. It introduces a "component" abstraction — a self-contained module that declares what it provides and what it requires.

```cpp
// Google Fruit example — component-based injection
#include <fruit/fruit.h>

class ILogger {
public:
    virtual void log(const std::string& msg) = 0;
};

class ConsoleLogger : public ILogger {
public:
    INJECT(ConsoleLogger()) = default;
    void log(const std::string& msg) override {
        std::cout << "[FRUIT] " << msg << std::endl;
    }
};

class UserService {
private:
    ILogger* logger_;
public:
    INJECT(UserService(ILogger* logger)) : logger_(logger) {}
    void createUser(const std::string& name) {
        logger_->log("Creating user: " + name);
    }
};

// Component declaration — explicit provides/requires
fruit::Component<ILogger> getLoggerComponent() {
    return fruit::createComponent()
        .bind<ILogger, ConsoleLogger>();
}

fruit::Component<UserService> getServiceComponent() {
    return fruit::createComponent()
        .install(getLoggerComponent);  // tells Fruit what's needed
}

int main() {
    fruit::Injector<UserService> injector(getServiceComponent);
    UserService* service = injector.get<UserService*>();
    service->createUser("Bob");
}
```

Fruit's component model shines in large codebases where dependency boundaries need to be explicit. Each component declares its API surface (provides/requires), and Fruit validates the full graph at injector creation time. This explicitness is a double-edged sword — it forces disciplined architecture but adds boilerplate.

Performance-wise, Fruit uses a lazy singleton pattern and caches resolved objects. For most applications the overhead is negligible, but in tight loops or embedded contexts Boost.DI's compile-time-only approach may be preferable.

## Kangaru: Modern C++17 Service Maps

Kangaru is the youngest of the three, designed for C++11 and later with an emphasis on ergonomics. It uses a "service map" pattern where each service is defined as a struct with traits specifying its dependencies and lifecycle.

```cpp
// Kangaru example — service definition with traits
#include <kangaru/kangaru.hpp>

struct ILogger {
    virtual void log(const std::string& msg) = 0;
};

struct ConsoleLogger : ILogger {
    void log(const std::string& msg) override {
        std::cout << "[KANGARU] " << msg << std::endl;
    }
};

// Service definition for ConsoleLogger
struct ConsoleLoggerService : kgr::single_service<ConsoleLogger> {};

struct UserService {
    std::shared_ptr<ILogger> logger;
    // Kangaru auto-injects based on service definitions
};

// Map ConsoleLoggerService to ILogger interface
auto service_map(ILogger const&) -> ConsoleLoggerService;

int main() {
    kgr::container container;
    auto& service = container.service<UserService>();
    service.logger->log("Hello from Kangaru");
}
```

Kangaru's distinctive feature is its service definition approach — rather than binding interfaces to implementations at the injector level, you define service mappings that Kangaru resolves through overload resolution. This makes the code more declarative and easier to refactor.

For comprehensive C++ code quality analysis when adopting these patterns, see our [C++ static analysis tools guide](../2026-06-02-linux-static-code-analysis-cppcheck-clang-flawfinder-infer/).

## Choosing the Right DI Container

| Scenario | Recommended |
|----------|-------------|
| **Maximum compile-time safety** | Boost.DI |
| **Large teams with explicit contracts** | Google Fruit |
| **Modern C++17 codebase, ease of use** | Kangaru |
| **Embedded / zero-overhead requirement** | Boost.DI or Kangaru |
| **Runtime plugin system integration** | Google Fruit |
| **Quick prototyping** | Kangaru |

All three libraries are mature, actively maintained, and production-tested. The choice ultimately depends on your team's philosophy toward explicitness and your tolerance for template-heavy error messages.

## Why Self-Host Your Dependency Injection Strategy?

Choosing a DI container is fundamentally an architectural decision that shapes your entire codebase. Once entrenched, migrating between containers is painful — the bindings permeate every module. Investing time upfront to evaluate Boost.DI, Google Fruit, and Kangaru pays dividends for years.

Unlike managed-language DI frameworks that rely on runtime reflection, C++ DI containers leverage the type system for safety. This means they catch wiring errors at build time, not in production. The self-hosting philosophy extends here: you own your object graph, you control your component lifecycles, and no opaque runtime framework makes decisions behind your back.

Performance-conscious teams will appreciate that C++ DI containers — particularly Boost.DI and Kangaru — compile down to direct constructor calls with zero virtual dispatch overhead beyond what you explicitly declare. The container is a build-time tool, not a runtime dependency.

For related reading on modular C++ architecture, see our guide on [embeddable plugin systems](../2026-06-20-embeddable-plugin-systems-extism-pluggy-abi-stable-libloading/) which explores runtime extension patterns that complement compile-time DI.

## FAQ

### Which DI container has the best compile-time error messages?

Boost.DI provides the most detailed compile-time errors through static assertions and custom type traits. When a dependency cannot be resolved, it produces a human-readable message explaining which binding is missing. Kangaru uses SFINAE-based errors which can be cryptic, while Fruit reports errors at injector creation time with clear descriptions.

### Can I use these DI containers with CMake FetchContent?

Yes. All three libraries support CMake integration. Boost.DI and Kangaru are header-only and can be included via FetchContent or a simple `add_subdirectory`. Google Fruit requires compilation but provides CMake export targets. See the code examples above for FetchContent configurations.

### How do these compare to Java's Spring or Guice?

C++ DI containers are fundamentally different from Java frameworks. Java DI uses runtime reflection and annotation processing, which adds measurable overhead. C++ DI containers resolve dependencies at compile time through template metaprogramming, producing direct constructor calls with zero runtime dispatch. The trade-off is that C++ DI cannot support runtime reconfiguration (e.g., changing bindings without recompiling), whereas Java DI can.

### Are DI containers necessary for small C++ projects?

For projects under 10,000 lines with simple dependency graphs, manual constructor injection is often sufficient. DI containers become valuable when: (a) you have 20+ components with non-trivial dependencies, (b) you need to swap implementations for testing, or (c) your team is growing and needs explicit dependency contracts to prevent spaghetti code.

### Can I mix DI containers with manual dependency injection?

Absolutely. Most teams adopt DI containers incrementally — starting with the most complex subsystems and leaving simpler components with manual wiring. Google Fruit's component model is particularly well-suited to gradual adoption since each component is self-contained and can be composed with manual injection at the boundaries.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Dependency Injection Containers: Boost.DI vs Google Fruit vs Kangaru",
  "description": "Comprehensive comparison of three C++ dependency injection containers — Boost.DI, Google Fruit, and Kangaru — covering API design, compile-time vs runtime trade-offs, performance, and real-world integration patterns with CMake and modern C++ toolchains.",
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
