---
title: "Self-Hosted C++ Filesystem Libraries: std::filesystem vs ghc::filesystem vs Boost.Filesystem"
date: "2026-06-22"
tags: ["c++", "filesystem", "boost", "c++17", "cross-platform", "development"]
draft: false
---

Filesystem operations — traversing directories, checking file permissions, copying and moving files — are fundamental to almost every non-trivial C++ application. Before C++17, developers relied on platform-specific APIs (POSIX `dirent.h`, Windows `FindFirstFile`) or third-party libraries. The standardization of `std::filesystem` in C++17 changed the landscape, but real-world projects still face practical challenges: legacy C++11/14 codebases, incomplete compiler support, and the need for extended functionality beyond the standard.

This article compares three approaches to C++ filesystem programming: **std::filesystem** (the C++17 standard library), **ghc::filesystem** (a standalone implementation), and **Boost.Filesystem** (the library that inspired the standard). We examine their APIs, compatibility matrices, performance characteristics, and real-world deployment considerations.

## Why Filesystem Libraries Matter

Working with the filesystem using raw POSIX or Win32 APIs is tedious and error-prone. A dedicated filesystem library provides:

- **Cross-platform portability**: Write once, compile on Linux, macOS, and Windows without `#ifdef` guards
- **Path abstraction**: `std::filesystem::path` handles forward/backward slashes, Unicode, and root naming transparently
- **RAII error handling**: Exceptions or `std::error_code` for every operation instead of checking `errno`
- **Directory iteration**: Range-based for loops over directory contents with recursive traversal
- **File metadata**: `file_size()`, `last_write_time()`, `permissions()` without platform-specific structs

## Library Comparison

| Feature | std::filesystem | ghc::filesystem | Boost.Filesystem |
|---------|----------------|-----------------|------------------|
| Stars | N/A (std lib) | 1,543 | 177 (Boost submodule) |
| C++ Standard | C++17 minimum | C++11 compatible | C++11 compatible |
| Platform | GCC 8+, Clang 7+, MSVC 19.14+ | GCC 5+, Clang 3.5+, MSVC 2015+ | GCC 5+, Clang 3.5+, MSVC 2015+ |
| Header | `<filesystem>` | `<ghc/filesystem.hpp>` | `<boost/filesystem.hpp>` |
| Unicode Support | Native (std::filesystem::path) | Native (std::wstring on Win) | Native (boost::filesystem::path) |
| Test Suite Size | ~200 assertions | ~1,500 assertions | ~500 assertions |
| Maintainer | ISO C++ Committee | Steffen Schümann | Boost.Filesystem Maintainers |

## std::filesystem: The Standard Solution

`std::filesystem` became part of the C++17 standard after being published as a Technical Specification (TS). It was based on Boost.Filesystem v3 and provides a comprehensive API for filesystem operations.

**Key strengths:**
- Zero external dependencies (part of the standard library)
- Guaranteed ABI stability on each platform
- `std::filesystem::path` with native `char8_t` support in C++20
- `std::filesystem::directory_entry` caching for efficient iteration

**Limitations:**
- Requires C++17 compiler support (GCC 8+, Clang 7+, MSVC 2017 15.7+)
- No support for pre-C++17 codebases
- Linker flag `-lstdc++fs` required on GCC < 9

Here is a complete example demonstrating common filesystem operations:

```cpp
#include <filesystem>
#include <iostream>
#include <algorithm>

namespace fs = std::filesystem;

void analyze_directory(const fs::path& dir_path) {
    size_t total_size = 0;
    size_t file_count = 0;
    std::vector<std::pair<std::string, uintmax_t>> largest_files;
    
    // Recursive directory iteration
    for (const auto& entry : fs::recursive_directory_iterator(dir_path)) {
        if (entry.is_regular_file()) {
            auto size = entry.file_size();
            total_size += size;
            file_count++;
            
            largest_files.emplace_back(entry.path().filename().string(), size);
            std::partial_sort(
                largest_files.begin(),
                largest_files.begin() + std::min<size_t>(5, largest_files.size()),
                largest_files.end(),
                [](auto& a, auto& b) { return a.second > b.second; }
            );
            if (largest_files.size() > 5) largest_files.resize(5);
        }
    }
    
    std::cout << "Directory: " << dir_path << "\n";
    std::cout << "Files: " << file_count << "\n";
    std::cout << "Total size: " << total_size / 1024 / 1024 << " MB\n";
    std::cout << "Largest files:\n";
    for (auto& [name, size] : largest_files) {
        std::cout << "  " << name << ": " << size / 1024 << " KB\n";
    }
}

int main() {
    // Path manipulation
    fs::path project_root = fs::current_path();
    fs::path config = project_root / "config" / "app.toml";
    
    // File existence and type checks
    if (fs::exists(config)) {
        std::cout << "Config file: " << fs::canonical(config) << "\n";
        auto ftime = fs::last_write_time(config);
        std::cout << "Last modified: " 
                  << std::chrono::duration_cast<std::chrono::hours>(
                         ftime.time_since_epoch()).count() / 24 
                  << " days since epoch\n";
    }
    
    // Permission checking
    auto perms = fs::status(config).permissions();
    if ((perms & fs::perms::owner_write) != fs::perms::none) {
        std::cout << "Config is writable\n";
    }
    
    // Directory operations
    fs::create_directories(project_root / "output" / "reports");
    
    // Copy with overwrite protection
    std::error_code ec;
    fs::copy_file(config, project_root / "output" / "config.backup.toml",
                  fs::copy_options::skip_existing, ec);
    
    analyze_directory(project_root);
    return 0;
}
```

## ghc::filesystem: The Polyfill Champion

ghc::filesystem implements the C++17 `std::filesystem` API for C++11, C++14, and beyond. It is the most widely-used filesystem polyfill with over 1,500 stars on GitHub and extensive test coverage.

**Key strengths:**
- **Drop-in compatibility**: Code written for `std::filesystem` compiles with ghc by changing the namespace and header
- **Broad platform support**: Works on GCC 5+, Clang 3.5+, MSVC 2015+, and even Emscripten (WebAssembly)
- **Comprehensive test suite**: 1,500+ assertions testing edge cases across platforms
- **Single-header option**: Can be used as a single amalgamated header for simple integration

```cpp
// For projects targeting C++14 with ghc::filesystem
#include <ghc/filesystem.hpp>
#include <iostream>

namespace fs = ghc::filesystem;

// Same API as std::filesystem!
void list_files_by_extension(const fs::path& dir, const std::string& ext) {
    for (const auto& entry : fs::directory_iterator(dir)) {
        if (entry.path().extension() == ext) {
            std::cout << entry.path().filename() << "\n";
        }
    }
}

// Portable path construction with app data
fs::path get_app_data_dir() {
    fs::path base;
#ifdef _WIN32
    base = fs::path(std::getenv("APPDATA"));
#elif __APPLE__
    base = fs::path(std::getenv("HOME")) / "Library/Application Support";
#else
    base = fs::path(std::getenv("XDG_DATA_HOME") ? 
                    std::getenv("XDG_DATA_HOME") :
                    fs::path(std::getenv("HOME")) / ".local/share");
#endif
    base /= "myapp";
    fs::create_directories(base);
    return base;
}
```

## Boost.Filesystem: The Pioneer

Boost.Filesystem was the original cross-platform filesystem library that inspired the ISO standard. It was developed by Beman Dawes and became part of Boost in 2003, then evolved into the `std::filesystem` TS and eventually the C++17 standard.

**Key strengths:**
- **Boost ecosystem integration**: Works seamlessly with other Boost libraries (Asio, Beast, Program Options)
- **Historical stability**: V3 API (current) has been stable since 2015
- **Extended functionality**: Some features not yet in the standard, like `boost::filesystem::unique_path()`

**Limitations:**
- Requires the entire Boost distribution (or at minimum Boost.System, Boost.Config, Boost.Assert)
- V3 API is slightly different from `std::filesystem` (uses `branch_path()` not `parent_path()`)
- Boost compile times can be significant in large projects

Here is a Docker-based development environment for cross-platform testing:

```dockerfile
# Dockerfile for C++ filesystem cross-platform testing
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    g++-14 \
    cmake \
    libboost-filesystem-dev \
    && rm -rf /var/lib/apt/lists/*

# ghc::filesystem (header-only, from source)
RUN git clone --depth 1 https://github.com/gulrak/filesystem.git /opt/ghc_filesystem

WORKDIR /app
COPY . .

# Build with std::filesystem, ghc::filesystem, and Boost.Filesystem
RUN g++-14 -std=c++17 -o test_std main.cpp -lstdc++fs && \
    g++-14 -std=c++14 -o test_ghc main_ghc.cpp \
            -I/opt/ghc_filesystem/include && \
    g++-14 -std=c++14 -o test_boost main_boost.cpp \
            -lboost_filesystem -lboost_system
```

## Migration Strategy

When migrating between filesystem libraries, plan your approach carefully:

1. **Greenfield C++17 project**: Use `std::filesystem` directly — it's the standard and will be supported indefinitely
2. **C++14 project adding filesystem support**: Use ghc::filesystem with a namespace alias so you can easily switch later
3. **Existing Boost project**: Stick with Boost.Filesystem if you already depend on Boost — adding ghc adds a second dependency for no benefit
4. **Library code (consumed by others)**: Use ghc::filesystem to maximize platform reach with C++11 minimum

## Minimizing Third-Party Dependencies

In CI/CD pipelines and container-based deployments, every dependency adds build time and potential supply chain risk. For a typical C++17 project using ghc::filesystem on an Ubuntu 24.04 Docker image:

```yaml
# CI pipeline for ghc::filesystem
build:
  image: ubuntu:24.04
  script:
    - apt-get update && apt-get install -y g++-14 cmake git
    - mkdir build && cd build
    - cmake .. -DCMAKE_CXX_STANDARD=17
    - cmake --build .
    - ctest --output-on-failure
```

## FAQ

### When should I use ghc::filesystem instead of std::filesystem?

Use ghc::filesystem when you need to support C++11 or C++14 toolchains, or when you need to target platforms with incomplete `<filesystem>` support (older Android NDK, Emscripten, some embedded Linux toolchains). For C++17+ projects with GCC 9+/Clang 9+/MSVC 2019+, `std::filesystem` is preferred.

### Does std::filesystem handle Unicode paths correctly?

On Windows, `std::filesystem::path` stores paths as `std::wstring` internally, ensuring full Unicode support. On POSIX systems, paths are stored as byte strings in the native encoding (typically UTF-8 on modern Linux). Use `std::filesystem::u8path()` in C++20 for explicit UTF-8 handling.

### What's the performance impact of recursive_directory_iterator?

`recursive_directory_iterator` can be significantly slower than a hand-rolled loop using `directory_iterator` + manual recursion on deeply nested directory trees. The overhead is typically 5-15% on Linux and 10-25% on Windows due to additional stat calls for directory entry caching. For performance-critical paths, benchmark with your actual file counts and consider `readdir`-based alternatives.

### Is Boost.Filesystem being deprecated now that std::filesystem exists?

Boost.Filesystem is not being deprecated — it continues to receive updates and supports C++11 toolchains that cannot use `std::filesystem`. The V4 API is under development to align more closely with the standard. However, for new C++17 projects, `std::filesystem` is recommended.

### How do I handle filesystem errors gracefully?

Use the `std::error_code` overloads for non-throwing operations:

```cpp
std::error_code ec;
auto size = fs::file_size("missing_file.txt", ec);
if (ec) {
    std::cerr << "Error: " << ec.message() << "\n";
    // Handle gracefully — don't crash on missing files
}
```

The non-throwing overloads are essential for operations on user-provided paths where failures are expected.

### Can I use these libraries in a container without installing a full boost dependency?

Yes. ghc::filesystem is header-only — just include it. For Boost.Filesystem, build Boost with `--with-filesystem --with-system` to get only the required libraries (about 2 MB compiled). `std::filesystem` requires no additional packages on GCC 9+.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Filesystem Libraries: std::filesystem vs ghc::filesystem vs Boost.Filesystem",
  "description": "In-depth comparison of C++ filesystem libraries including std::filesystem (C++17), ghc::filesystem polyfill, and Boost.Filesystem. Covers API differences, compatibility, performance, and migration strategies.",
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

For more C++ infrastructure topics, see our [high-performance data structure comparison](../2026-06-22-high-performance-data-structure-libraries-boost-container-abseil-eastl-plf-colony/) and [dependency injection containers guide](../2026-06-22-cpp-dependency-injection-containers-boost-di-google-fruit-kangaru/). For numeric computing libraries, check our [arbitrary precision arithmetic comparison](../2026-06-22-arbitrary-precision-arithmetic-gmp-mpfr-flint-boost-multiprecision/).
