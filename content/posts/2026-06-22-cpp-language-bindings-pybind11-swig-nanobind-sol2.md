---
title: "Self-Hosted C++ Language Bindings: pybind11 vs SWIG vs nanobind vs sol2 for Cross-Language Interop"
date: "2026-06-22"
tags: ["c-plus-plus", "language-bindings", "cross-language", "python", "lua", "ffi", "developer-tools"]
draft: false
---

## Introduction

The C++ ecosystem doesn't exist in isolation. High-performance C++ libraries often need to expose their functionality to Python for data science workflows, to Lua for game scripting, or to multiple languages simultaneously for broad ecosystem reach. Language binding libraries bridge this gap, automatically generating the glue code that connects C++'s type system to higher-level language runtimes.

In this guide, we compare four leading C++ language binding tools: **pybind11** (C++ to Python), **SWIG** (multi-language), **nanobind** (modern C++ to Python), and **sol2** (C++ to Lua). Each represents a different philosophy in the binding design space.

## Why Use Language Bindings Instead of FFI?

Foreign Function Interface (FFI) libraries like Python's `ctypes` or LuaJIT's FFI can call C functions directly, but they cannot handle C++ classes, templates, overloaded functions, or move semantics. A binding generator understands C++ semantics and can produce idiomatic wrappers that feel natural in the target language — Python objects that behave like Python objects, despite being backed by C++.

For serialization between languages, which often accompanies binding workflows, see our [schema serialization frameworks guide](../2026-06-19-schema-serialization-frameworks-protobuf-capnproto-flatbuffers-thrift/). For managing the C++ dependencies these libraries introduce, see our [C++ package management comparison](../2026-06-18-self-hosted-c-cpp-package-management-conan-vcpkg-spack/).

## Comparison Table

| Feature | pybind11 | SWIG | nanobind | sol2 |
|---------|----------|------|----------|------|
| **Stars** | 17,921 | 6,296 | 3,576 | 5,080 |
| **Target Languages** | Python | 20+ languages | Python | Lua |
| **C++ Standard** | C++11+ | C++98+ | C++17+ | C++17 |
| **Binding Style** | Header-only, inline C++ | Interface files (.i) | Header-only, inline C++ | Header-only, inline C++ |
| **STL Support** | Extensive (vector, map, optional) | Limited | Extensive, optimized | N/A (Lua tables) |
| **Performance** | Fast | Moderate | Very fast (smaller binaries) | Fast |
| **Build System** | CMake / setuptools | Custom (swig CLI) | CMake / scikit-build | CMake |
| **Last Update** | Jun 2026 | Jun 2026 | Jun 2026 | Mar 2025 |
| **License** | BSD | GPL/Commercial | BSD | MIT |
| **Learning Curve** | Low | High | Low | Low |

## pybind11: The Python Standard-Bearer

pybind11 is the de facto standard for C++/Python bindings, with over 17,000 stars and adoption by major projects including PyTorch, TensorFlow's C++ API, and OpenCV. It uses modern C++ template metaprogramming to automatically generate Python bindings from C++ declarations.

```cpp
// pybind11 — auto-generate Python module from C++ class
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>

namespace py = pybind11;

class DataProcessor {
    std::vector<double> data_;
public:
    DataProcessor() = default;

    void add_sample(double value) { data_.push_back(value); }

    double compute_mean() const {
        if (data_.empty()) return 0.0;
        double sum = 0.0;
        for (auto v : data_) sum += v;
        return sum / data_.size();
    }

    std::vector<double> get_data() const { return data_; }
};

PYBIND11_MODULE(mylib, m) {
    m.doc() = "High-performance data processing library";

    py::class_<DataProcessor>(m, "DataProcessor")
        .def(py::init<>())
        .def("add_sample", &DataProcessor::add_sample,
             "Add a sample value to the dataset")
        .def("compute_mean", &DataProcessor::compute_mean,
             "Compute arithmetic mean of all samples")
        .def("get_data", &DataProcessor::get_data,
             "Return the raw data vector");
}
```

From Python, the bound class is used as naturally as any Python object:

```python
import mylib
processor = mylib.DataProcessor()
processor.add_sample(10.5)
processor.add_sample(20.3)
print(processor.compute_mean())  # 15.4
```

pybind11 handles automatic type conversion for `std::vector`, `std::map`, `std::optional`, and `std::function`. It supports keyword arguments, default values, inheritance, virtual method overriding from Python, and pickle serialization. For large codebases, the `pybind11-stubgen` tool generates `.pyi` type stubs for IDE autocompletion.

For RPC-based alternatives to direct language binding, see our [RPC frameworks comparison](../2026-06-20-rpc-frameworks-grpc-twirp-connect-dubbo/).

## SWIG: The Multi-Language Veteran

SWIG (Simplified Wrapper and Interface Generator) has been generating bindings since 1996 and supports over 20 target languages including Python, Java, C#, Ruby, R, Go, Lua, and PHP. It uses a declarative interface file (`.i`) to describe the bindings, then generates C++ wrapper code and target-language modules.

```swig
// SWIG interface file (mylib.i)
%module mylib

%include "std_vector.i"
%include "std_string.i"

%template(DoubleVector) std::vector<double>;

class DataProcessor {
public:
    DataProcessor();
    void add_sample(double value);
    double compute_mean() const;
    std::vector<double> get_data() const;
};
```

```bash
# Generate bindings for Python + Java from a single interface file
swig -c++ -python mylib.i
swig -c++ -java mylib.i
g++ -shared -fPIC mylib_wrap.cxx DataProcessor.cpp -o _mylib.so     $(python3-config --includes) $(python3-config --ldflags)
```

SWIG's key advantage is write-once, bind-many: a single interface file generates bindings for every language your library needs to support. This is invaluable for projects like libraries that serve data science (Python), enterprise backend (Java), and embedded scripting (Lua) simultaneously.

The trade-off is complexity. SWIG's interface files use a custom DSL with its own syntax quirks, and debugging generated wrapper code can be challenging. For C++17 features like structured bindings or `std::optional`, SWIG support lags behind pybind11 and nanobind.

## nanobind: pybind11's Leaner Successor

nanobind is a ground-up redesign of pybind11 by the same author (Wenzel Jakob), targeting smaller binary sizes, faster compilation, and C++17 idioms. It reduces the generated binary size by 50-70% compared to equivalent pybind11 bindings.

```cpp
// nanobind — cleaner C++17 syntax, smaller binaries
#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include <vector>

namespace nb = nanobind;

class DataProcessor { /* same as before */ };

NB_MODULE(mylib, m) {
    m.doc() = "High-performance data processing (nanobind)";

    nb::class_<DataProcessor>(m, "DataProcessor")
        .def(nb::init<>())
        .def("add_sample", &DataProcessor::add_sample)
        .def("compute_mean", &DataProcessor::compute_mean)
        .def("get_data", &DataProcessor::get_data);
}
```

The API is intentionally similar to pybind11's, making migration straightforward. Key improvements include DLPack support for zero-copy tensor exchange with NumPy/PyTorch, faster compilation through reduced template instantiation depth, and a 30-50% reduction in import time for large modules.

nanobind requires C++17 and Python 3.8+, which may exclude some legacy codebases. For new projects targeting Python, nanobind is becoming the recommended choice — it's already used by Mitsuba 3 (the physically-based renderer) and several scientific computing projects.

## sol2: C++/Lua Binding with Modern Ergonomics

sol2 takes a different approach: it targets Lua specifically, leveraging Lua's lightweight, embeddable nature for game scripting, configuration, and plugin systems. Unlike SWIG's generated approach, sol2 uses template metaprogramming to create bindings inline in C++.

```cpp
// sol2 — C++ to Lua bindings with idiomatic Lua feel
#include <sol/sol.hpp>

class DataProcessor {
    std::vector<double> data_;
public:
    void add_sample(double value) { data_.push_back(value); }
    double compute_mean() const {
        if (data_.empty()) return 0.0;
        double sum = 0.0;
        for (auto v : data_) sum += v;
        return sum / data_.size();
    }
};

int main() {
    sol::state lua;
    lua.open_libraries(sol::lib::base, sol::lib::math);

    // Bind C++ class to Lua
    lua.new_usertype<DataProcessor>("DataProcessor",
        sol::constructors<>(),
        "add_sample", &DataProcessor::add_sample,
        "compute_mean", &DataProcessor::compute_mean
    );

    // Execute Lua that uses the bound class
    lua.script(R"(
        local dp = DataProcessor.new()
        for i = 1, 100 do
            dp:add_sample(math.random() * 100)
        end
        print("Mean: " .. dp:compute_mean())
    )");

    return 0;
}
```

sol2 supports all Lua versions (5.1 through 5.4 and LuaJIT), handles C++ exceptions by converting them to Lua errors, and provides automatic conversion between C++ containers (`std::vector`, `std::map`) and Lua tables. It's widely used in game engines, trading systems, and any application where Lua serves as the scripting layer. For more on embedding scripting runtimes, see our [embedded scripting engines guide](../2026-06-22-embedded-scripting-engines-duktape-quickjs-jerryscript-cpp/).

## Choosing the Right Binding Tool

| Scenario | Recommended |
|----------|-------------|
| **Python data science / ML** | pybind11 or nanobind |
| **Multi-language support** | SWIG |
| **New Python project (C++17+)** | nanobind |
| **Game scripting (Lua)** | sol2 |
| **Legacy C++98 codebase** | SWIG |
| **Binary size constrained** | nanobind |
| **IDE type stubs needed** | pybind11 + pybind11-stubgen |

## Why Self-Host Your Language Bindings?

Language bindings are the gateway through which your C++ library reaches the wider developer ecosystem. Python's scientific computing stack — NumPy, SciPy, PyTorch — is built on C++ libraries exposed through binding tools. A well-designed binding layer multiplies your library's impact by orders of magnitude.

Self-hosting the binding code means you control the API surface, the error handling semantics, and the performance characteristics. Unlike manual C API wrappers, binding generators handle the tedious aspects — reference counting, type conversion, exception translation — while giving you full control over the public interface.

The build integration cost is minimal: pybind11 and nanobind are available through vcpkg, Conan, and system package managers; SWIG is typically a system package (`apt install swig`); sol2 is a single header. The long-term maintenance benefit — automatically supporting new Python/Lua versions through upstream updates — far outweighs the initial integration effort.

## FAQ

### When should I use nanobind instead of pybind11?

Choose nanobind for new C++17+ Python projects where binary size matters (embedded systems, Python wheels distributed via PyPI with size limits) or where import time is critical (CLI tools, serverless functions). Stay with pybind11 if you need C++11/14 compatibility or rely on third-party extensions built on pybind11's internals. Migration complexity is low — the APIs are nearly identical.

### Does SWIG support modern C++ features like move semantics?

SWIG 4.x added partial support for C++11 features including move constructors and `std::shared_ptr`. However, C++17 features like `std::optional`, `std::variant`, and structured bindings require manual interface file annotations. For projects heavily using modern C++, pybind11 or nanobind provide better out-of-the-box support.

### How much overhead do bindings add to function calls?

pybind11 and nanobind function call overhead is typically 50-200 nanoseconds per call — negligible for most applications. SWIG has slightly higher overhead due to its generated wrapper layer. sol2's overhead is similar to pybind11. The main performance concern is not call overhead but data marshaling: converting large arrays between C++ and Python/Lua. Use zero-copy mechanisms (pybind11's `py::array`, nanobind's DLPack, sol2's userdata) for large data transfers.

### Can I use these tools with CMake-based projects?

Yes. All four tools have first-class CMake support. pybind11 and nanobind provide CMake config packages (`find_package(pybind11)`). SWIG integrates via CMake's `UseSWIG` module. sol2 can be included via `FetchContent` or a simple `add_subdirectory`. See the code examples throughout this guide for CMake integration patterns.

### What about Rust — do these tools help with C++/Rust interop?

No. pybind11, SWIG, nanobind, and sol2 are designed for binding C++ to higher-level languages (Python, Lua, Java, etc.), not to Rust. For C++/Rust interop, use `cxx` (safe C++/Rust bridge), `bindgen` (generate Rust FFI from C headers), or manual C ABI wrappers. These are complementary tools — you might use pybind11 for Python access and cxx for Rust access to the same C++ library.

### Is there a performance difference between pybind11 and nanobind for large data transfers?

nanobind is significantly better for large data transfers due to its DLPack integration, which enables zero-copy tensor sharing with NumPy, PyTorch, JAX, and CuPy. pybind11's `py::array` also supports zero-copy but with a less standardized protocol. For scalar function calls, both have near-identical performance. nanobind's binary size advantage (50-70% smaller) is most noticeable when distributing many small extension modules.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Language Bindings: pybind11 vs SWIG vs nanobind vs sol2 for Cross-Language Interop",
  "description": "Comprehensive comparison of C++ language binding tools — pybind11, SWIG, nanobind, and sol2 — covering Python, Lua, and multi-language binding patterns, performance characteristics, build system integration, and migration strategies.",
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
