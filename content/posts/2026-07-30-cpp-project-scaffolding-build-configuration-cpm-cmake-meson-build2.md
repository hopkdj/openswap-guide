---
title: "C++ Project Scaffolding and Build Configuration: CPM.cmake vs Meson vs build2 in 2026"
date: "2026-07-30"
tags: ["c-plus-plus", "cpp-libraries", "build-systems", "build-tools", "developer-tools", "comparison", "cmake", "meson"]
draft: false
---

## Introduction

C++ project setup has historically been one of the language's biggest pain points. Unlike Rust (cargo), Go (go mod), or Node.js (npm), C++ has no standard build system or package manager. This fragmentation has spawned dozens of build tools, each with different philosophies — from CMake's near-universal dominance to Meson's speed-first design and build2's integrated build-and-package approach.

In 2026, three tools stand out for project scaffolding and dependency management: **CPM.cmake** (a lightweight CMake script for painless dependency management), **Meson** (a fast, user-friendly build system designed as a CMake alternative), and **build2** (an integrated build system and package manager with first-class CI/CD support). This article compares them on setup speed, dependency handling, cross-platform support, and developer experience.

## Quick Comparison Table

| Feature | CPM.cmake | Meson | build2 |
|---------|-----------|-------|--------|
| **Stars** | 4,075 | 6,580 | 664 |
| **Last Updated** | Jul 2026 | Jul 2026 | Jul 2026 |
| **Type** | CMake script (wrapper) | Standalone build system | Build system + package manager |
| **Build Backend** | CMake | Ninja, VS, Xcode | Native |
| **Package Manager** | FetchContent + GitHub | WrapDB (subprojects) | Built-in (cppget.org) |
| **Configuration Language** | CMakeLists.txt | Meson (Python-like DSL) | buildfile (custom DSL) |
| **C++ Standards** | All (via CMake) | C++11 through C++23 | C++11 through C++23 |
| **Windows Support** | Excellent (MSVC, MinGW) | Excellent (MSVC, MinGW) | Good (MSVC, MinGW) |

## CPM.cmake — Dependency Management Without the Overhead

CPM.cmake (CMake Package Manager) is a thin wrapper around CMake's `FetchContent` module. It's a single CMake script file that you include in your project — no installation, no Python dependency, no daemon. It downloads and configures dependencies at configure time, making it the lightest-weight option in this comparison.

### Installation

```bash
# Download the script directly into your project
wget https://github.com/cpm-cmake/CPM.cmake/releases/latest/download/CPM.cmake
# Or use CMake's file(DOWNLOAD ...) in your CMakeLists.txt
```

### Key Features

- **Single-file dependency**: One `CPM.cmake` script is all you need — no system installation required
- **GitHub-native**: Declares dependencies as GitHub repos with optional version tags, branches, or commits
- **Caching**: Downloads are cached in a local directory, shared across projects
- **Composable with existing CMake**: Works seamlessly with existing CMakeLists.txt — just add `include(CPM.cmake)` and declare your dependencies

```cmake
# CMakeLists.txt with CPM.cmake
cmake_minimum_required(VERSION 3.14)
project(MyApp)

# Download and include CPM.cmake
file(DOWNLOAD
    https://github.com/cpm-cmake/CPM.cmake/releases/latest/download/CPM.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/cmake/CPM.cmake
)
include(${CMAKE_CURRENT_BINARY_DIR}/cmake/CPM.cmake)

# Declare dependencies — CPM handles download, configure, and build
CPMAddPackage(
    NAME fmt
    GITHUB_REPOSITORY fmtlib/fmt
    VERSION 11.1.0
)
CPMAddPackage(
    NAME nlohmann_json
    GITHUB_REPOSITORY nlohmann/json
    VERSION 3.11.3
)
CPMAddPackage(
    NAME spdlog
    GITHUB_REPOSITORY gabime/spdlog
    VERSION 1.15.0
)

# Your targets automatically link against these dependencies
add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE fmt::fmt nlohmann_json::nlohmann_json spdlog::spdlog)
```

## Meson — Speed and Developer Ergonomics

Meson is a full build system designed from the ground up to be fast, correct, and user-friendly. It uses Ninja as its default build backend (achieving near-instant incremental builds) and provides a Python-like configuration language that is intentionally not Turing-complete — preventing the build logic spaghetti that plagues complex CMake projects.

### Installation

```bash
pip install meson ninja
# Or via system package manager:
apt install meson ninja-build
```

### Key Features

- **Sub-second configure**: Meson's configure step is an order of magnitude faster than CMake — typically <1 second for medium projects
- **Non-Turing-complete DSL**: The build description language prevents arbitrary code execution during configuration, making builds reproducible and IDE-friendly
- **WrapDB**: A curated package repository (wrapdb.mesonbuild.com) with 500+ pre-configured dependencies
- **First-class cross-compilation**: Cross-compilation is a first-class concept in Meson — not an afterthought patched with toolchain files

```meson
# meson.build
project('myapp', 'cpp',
    version: '1.0.0',
    default_options: ['cpp_std=c++20', 'warning_level=3']
)

# Dependencies via WrapDB
fmt_dep = dependency('fmt', version: '>=11.0')
json_dep = dependency('nlohmann_json', version: '>=3.11')
spdlog_dep = dependency('spdlog', version: '>=1.15')

# Your executable
executable('myapp',
    'src/main.cpp',
    'src/utils.cpp',
    dependencies: [fmt_dep, json_dep, spdlog_dep],
    install: true
)

# Tests
test('unit tests', executable('test_app', 'tests/test_main.cpp',
    dependencies: [fmt_dep],
))
```

Build commands:
```bash
meson setup builddir
meson compile -C builddir
meson test -C builddir
meson install -C builddir
```

## build2 — The Integrated Approach

build2 is an ambitious project that aims to be the "Cargo for C++" — a unified build system, package manager, and CI/CD tool. It provides hermetic, reproducible builds with first-class support for project versioning, dependency resolution, and artifact distribution through cppget.org.

### Installation

```bash
# Using the build2 installer
curl -sSfO https://download.build2.org/0.17.0/build2-install-0.17.0.sh
sh build2-install-0.17.0.sh
```

### Key Features

- **Integrated package management**: `bdep init` creates projects, `bdep sync` resolves dependencies, `bdep ci` runs CI
- **Hermetic builds**: Dependencies are fetched into a local directory with pinned versions, ensuring reproducibility
- **cppget.org**: A centralized package repository with semantic versioning and dependency resolution
- **Buildfile DSL**: A declarative build language that describes targets, prerequisites, and build rules

```
# buildfile
import libs = libfmt%lib{fmt}
import libs = nlohmann_json%lib{nlohmann_json}

libs: $libs

exe{myapp}: {hxx cxx}{**} $libs

# manifest (package declaration)
name: myapp
version: 1.0.0
depends: libfmt ^11.1.0
depends: nlohmann_json ^3.11.3
```

```bash
# Initialize and configure
bdep init -C @gcc cc config.cxx=g++

# Fetch dependencies and build
bdep update
b

# Run tests
b test
```

## Why How You Build Matters

The C++ build system you choose shapes your project for years — it determines how new contributors onboard, how CI/CD pipelines operate, and how smoothly dependencies upgrade. A poor build configuration leads to "works on my machine" problems, multi-hour CI builds, and dependency hell when upgrading libraries.

For teams already invested in CMake, **CPM.cmake** provides a zero-friction upgrade path — it's a single script that eliminates the need for git submodules or manual dependency management without requiring a build system migration. For new projects, **Meson** offers the best developer experience with its fast configure times and clean DSL. Teams building distributable libraries should consider **build2** for its integrated package management and semantic versioning support.

For more C++ development guidance, see our [C++ process management libraries comparison](../2026-06-30-cpp-process-management-reproc-boost-process-cpp-subprocess/) and our [C++ HTTP client libraries guide](../2026-06-30-cpp-http-client-libraries-cpp-httplib-cpr-curlpp-beast/).

## CI/CD Integration and Build Caching Strategies

Build times are the silent productivity killer in C++ projects. A 20-minute full rebuild that blocks every PR merge adds up to hours of developer waiting time per week. Build caching is the primary mitigation, and each tool handles it differently.

**CPM.cmake** leverages CMake's built-in caching through `CPM_SOURCE_CACHE`. Set this environment variable to a persistent directory, and CPM.cmake skips downloads for cached dependencies. Combined with `ccache` or `sccache` for compilation caching, typical incremental builds drop from minutes to seconds. For GitHub Actions, cache the CPM cache directory between workflow runs to avoid re-downloading dependencies on every CI trigger.

**Meson** integrates natively with `ccache` — just add `-Dc_args=-Dccache` to your setup command. Its Ninja backend is already optimized for minimal rebuilds; Ninja's dependency tracking is more precise than Make's, rebuilding only files whose transitive dependencies actually changed. Meson also supports `unity` builds (combining source files into a single translation unit) which can dramatically speed up full rebuilds on CI runners with many cores.

**build2** takes a different approach: its package cache is a first-class concept with version pinning and checksum verification. The `bdep update` command only fetches dependencies whose version constraints changed, and build artifacts for dependencies are cached and shared across projects. For monorepos, build2 supports subprojects with independent versioning — each subproject gets its own build configuration but shares a root-level dependency resolution.

For more on C++ development workflows, see our [C++ compile-time programming guide](../2026-06-30-cpp-compile-time-programming-boost-hana-frozen-ctre/) which covers advanced build optimization through constexpr computation and template metaprogramming.


## FAQ

### Should I migrate from CMake to Meson?

Not necessarily. If your CMake setup works and you use CPM.cmake for dependencies, the migration cost likely outweighs the benefits. Consider Meson for **new** projects where you value fast configure times and a clean DSL, or for cross-compilation-heavy projects where Meson's toolchain handling is superior.

### Does CPM.cmake work without internet access?

CPM.cmake downloads dependencies from GitHub at configure time, so it requires internet access on first build. However, it caches downloads locally (in `CPM_SOURCE_CACHE`), so subsequent builds work offline. For fully offline environments, pre-populate the cache directory.

### How does build2's package management compare to vcpkg or Conan?

build2's package management is more opinionated and integrated than vcpkg or Conan — it expects projects to follow specific conventions and uses its own build system. vcpkg and Conan are designed to work with any build system (CMake, Meson, Autotools), making them more flexible but also more complex to configure.

### What is the learning curve for Meson's DSL?

Meson's DSL is deliberately simple and borrows from Python syntax. Most developers can read and write Meson files within an hour. The language is not Turing-complete by design, which means you cannot write complex build logic in the build file itself — instead, you use `meson.add_install_script()` or external scripts for those cases.

### Can I use CPM.cmake with header-only libraries?

Yes, and it's actually CPM.cmake's sweet spot. For header-only libraries (nlohmann/json, spdlog when configured as header-only, Catch2), CPM.cmake downloads the sources and creates an `INTERFACE` target — no compilation needed. This makes dependency setup for header-only libraries essentially instant.

---


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Project Scaffolding and Build Configuration: CPM.cmake vs Meson vs build2 in 2026",
  "description": "A developer's comparison of three C++ project scaffolding and build configuration tools — CPM.cmake, Meson, and build2 — covering dependency management, cross-platform support, and developer experience.",
  "datePublished": "2026-07-30",
  "dateModified": "2026-07-30",
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
