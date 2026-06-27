---
title: "C++ Serialization Libraries Compared: Cereal vs Boost.Serialization vs Bitsery vs Msgpack-c"
date: "2026-06-27"
tags: ["cpp", "serialization", "cereal", "boost", "msgpack", "bitsery", "development-tools", "developer-libraries"]
draft: false
---

## Introduction

Serialization is the backbone of data interchange in modern C++ applications — it transforms structured data into a format suitable for storage or network transmission, and reconstructs it back. Whether you're building a game engine that saves player state, a distributed system sending messages between nodes, or a configuration manager persisting settings to disk, choosing the right serialization library has a direct impact on performance, binary size, and code maintainability.

Unlike general-purpose schema-based serialization frameworks (Protobuf, FlatBuffers, Cap'n Proto), C++ serialization libraries operate at the language level — they introspect C++ types directly and serialize them with minimal boilerplate. This guide compares four battle-tested C++ serialization libraries: **Cereal**, **Boost.Serialization**, **Bitsery**, and **Msgpack-c**, examining their API design, performance characteristics, format support, and integration complexity.

| Feature | Cereal | Boost.Serialization | Bitsery | Msgpack-c |
|---------|--------|---------------------|---------|-----------|
| **Header-only** | Yes | No (requires linking) | Yes | No (requires linking) |
| **Serialization Formats** | JSON, XML, Binary | Text, XML, Binary | Binary only | MessagePack binary |
| **C++ Standard** | C++11 | C++03+ | C++14 | C99 / C++11 |
| **Zero-copy support** | No | No | Yes (pointer linking) | No |
| **STL container support** | Full | Full | Manual specialization | Full (msgpack-c API) |
| **Intrusive / Non-intrusive** | Both | Both | Both | Non-intrusive |
| **GitHub Stars** | 4,679 | Part of Boost (26,000+) | 1,249 | 3,330 |
| **License** | BSD 3-Clause | Boost 1.0 | MIT | Boost 1.0 |
| **Compile-time overhead** | Moderate | High (heavy templates) | Low | Low |

## Cereal: Modern and Header-Only

Cereal is the de-facto modern C++ serialization library. It's fully header-only, requires no pre-processing step, and supports JSON, XML, and binary archives out of the box. Designed as a spiritual successor to Boost.Serialization (same lead developer), Cereal strips away Boost's dependency chain and provides a cleaner C++11 API.

**Key Features:**
- Three archive types: JSON, XML, and portable binary
- Works with any C++11-compliant compiler
- Minimal boilerplate — a single `serialize()` member function or free function
- Support for smart pointers, polymorphic types, and inheritance
- Built-in versioning for backward compatibility

**Basic usage:**
```cpp
#include <cereal/archives/json.hpp>
#include <cereal/types/vector.hpp>
#include <fstream>

struct Player {
    std::string name;
    int level;
    float health;

    template<class Archive>
    void serialize(Archive & archive) {
        archive(CEREAL_NVP(name), CEREAL_NVP(level), CEREAL_NVP(health));
    }
};

// Serialize to JSON
Player p{"Mage", 42, 98.5f};
std::ofstream os("player.json");
cereal::JSONOutputArchive archive(os);
archive(p);

// Deserialize
std::ifstream is("player.json");
cereal::JSONInputArchive iarchive(is);
Player loaded;
iarchive(loaded);
```

**Docker Compose — Development environment:**
```yaml
version: "3.8"
services:
  cereal-dev:
    image: gcc:13
    working_dir: /workspace
    volumes:
      - ./src:/workspace
    command: >
      bash -c "apt-get update && apt-get install -y cmake &&
      git clone https://github.com/USCiLab/cereal.git /opt/cereal &&
      g++ -std=c++17 -I/opt/cereal/include main.cpp -o main"
```

## Boost.Serialization: The Veteran

Boost.Serialization is the original enterprise-grade C++ serialization library, part of the Boost C++ Libraries collection. It's been battle-tested across two decades of production use and supports an extensive range of archive formats including text, XML, and binary. Its power comes at the cost of compilation time and the Boost dependency.

**Key Features:**
- Deep integration with the Boost ecosystem (smart pointers, containers, variant)
- Support for splitting `save()` and `load()` logic separately
- Non-intrusive serialization via free functions
- Versioning, object tracking, and pointer serialization built-in
- Battle-tested across decades in production systems

**Basic usage:**
```cpp
#include <boost/archive/text_oarchive.hpp>
#include <boost/archive/text_iarchive.hpp>
#include <boost/serialization/vector.hpp>
#include <fstream>

struct GameState {
    std::vector<int> scores;
    std::string player_name;

    template<class Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & scores;
        ar & player_name;
    }
};

// Serialize
GameState state{{100, 200, 150}, "Archer"};
std::ofstream ofs("save.txt");
boost::archive::text_oarchive oa(ofs);
oa << state;

// Deserialize
std::ifstream ifs("save.txt");
boost::archive::text_iarchive ia(ifs);
GameState loaded;
ia >> loaded;
```

## Bitsery: Binary-First Performance

Bitsery is a modern C++14 header-only binary serialization library designed for maximum throughput and minimal overhead. Unlike Cereal and Boost.Serialization, Bitsery is binary-only — but that singular focus gives it a performance edge. It achieves 2-3x faster serialization than Cereal binary archives and produces significantly smaller output.

**Key Features:**
- Zero heap allocations during serialization/deserialization
- Pointer support with ownership tracking (linking context)
- Extension system for custom types without modifying library code
- Compatible with embedded systems — no exceptions, no RTTI
- Flexible buffer adapters for custom memory management

**Basic usage:**
```cpp
#include <bitsery/bitsery.h>
#include <bitsery/adapter/buffer.h>
#include <bitsery/traits/vector.h>

struct Transform {
    float x, y, z;
};

template <typename S>
void serialize(S& s, Transform& t) {
    s.value4b(t.x);
    s.value4b(t.y);
    s.value4b(t.z);
}

// Serialize
Transform t{1.0f, 2.0f, 3.0f};
std::vector<uint8_t> buffer(64);
auto written = bitsery::quickSerialization(
    bitsery::OutputBufferAdapter{buffer}, t);

// Deserialize
Transform loaded{};
auto state = bitsery::quickDeserialization(
    bitsery::InputBufferAdapter{buffer.begin(), written}, loaded);
assert(state.first == bitsery::ReaderError::NoError);
```

Bitsery is ideal for network protocols, embedded systems, and performance-critical game engines where every byte and CPU cycle counts.

## Msgpack-c: Cross-Language Interoperability

Msgpack-c is the official C/C++ implementation of MessagePack — a compact binary serialization format with bindings for 50+ programming languages. Unlike the other three libraries which are C++-centric, Msgpack-c's primary value proposition is cross-language compatibility. If your C++ server needs to exchange data with Python microservices, JavaScript frontends, or Rust tools, MessagePack provides a common format.

**Key Features:**
- Interoperable with MessagePack libraries in 50+ languages
- Schema-free dynamic typing — serialize any value without pre-declared types
- Streaming API for incremental deserialization from network sockets
- C and C++ APIs available (C API for FFI bindings)
- Smaller wire format than JSON (typically 20-30% smaller)

**Basic usage:**
```c
#include <msgpack.h>
#include <stdio.h>

int main() {
    // Create a MessagePack object
    msgpack_sbuffer sbuf;
    msgpack_sbuffer_init(&sbuf);
    msgpack_packer pk;
    msgpack_packer_init(&pk, &sbuf, msgpack_sbuffer_write);

    // Pack a map with 2 key-value pairs
    msgpack_pack_map(&pk, 2);
    msgpack_pack_str(&pk, 4);
    msgpack_pack_str_body(&pk, "name", 4);
    msgpack_pack_str(&pk, 5);
    msgpack_pack_str_body(&pk, "Alice", 5);
    msgpack_pack_str(&pk, 3);
    msgpack_pack_str_body(&pk, "age", 3);
    msgpack_pack_int(&pk, 30);

    printf("Serialized %zu bytes\n", sbuf.size);
    msgpack_sbuffer_destroy(&sbuf);
    return 0;
}
```

## Performance Comparison

Serialization throughput varies dramatically between these libraries, especially for large datasets. In benchmarks with 100,000 structs containing mixed types, Bitsery typically leads by a wide margin:

**Relative throughput (higher is better):**
- Bitsery: ~2,800 MB/s (binary, no heap allocations)
- Cereal (binary archive): ~950 MB/s
- Msgpack-c: ~600 MB/s
- Boost.Serialization (binary): ~300 MB/s

**Output size (100,000 structs):**
- Bitsery: ~1.2 MB (raw binary)
- Msgpack-c: ~1.8 MB (MessagePack encoded)
- Cereal binary: ~2.4 MB
- Boost.Serialization binary: ~3.1 MB

**Compile-time impact:**
- Bitsery: ~1.2s (clean build, single TU)
- Cereal: ~1.8s
- Msgpack-c: ~2.5s (C API wrapper)
- Boost.Serialization: ~5.0s (heavy template instantiation)

## Choosing the Right Library

The choice depends heavily on your use case:

- **Cereal** for general-purpose C++ serialization where JSON readability, XML compatibility, and modern C++ ergonomics matter. It's the best "default choice" for most projects.
- **Boost.Serialization** for projects already using Boost, or when you need enterprise-grade features like split `save/load`, versioning, and deep Boost container support.
- **Bitsery** for performance-critical binary serialization — game engines, real-time systems, embedded platforms, and network protocols where throughput and binary size are paramount.
- **Msgpack-c** for cross-language systems where C++ must interoperate with Python, JavaScript, Go, or Rust services using a common serialization format.

For most new C++ projects, **Cereal** hits the sweet spot of usability, performance, and format flexibility. If absolute speed matters, **Bitsery** is the clear winner. If you're building a polyglot microservice architecture, **Msgpack-c** provides the cross-language bridge.

## Why Self-Host Your C++ Serialization Infrastructure?

Serialization isn't just about library choice — it's about owning your data pipeline. When you self-host your build and testing infrastructure around these libraries, you gain complete control over serialization formats, backward compatibility testing, and performance benchmarking.

For a deeper dive into building C++ applications, see our [C++ package management guide](../2026-06-18-self-hosted-c-cpp-package-management-conan-vcpkg-spack/) which covers how to integrate these serialization libraries via Conan, vcpkg, and Spack.

For understanding how binary formats fit into the broader serialization landscape, check our [schema serialization frameworks comparison](../2026-06-19-schema-serialization-frameworks-protobuf-capnproto-flatbuffers-thrift/) covering Protobuf, Cap'n Proto, FlatBuffers, and Thrift.

If you're working on the string manipulation side, our [C++ string libraries guide](../2026-06-25-cpp-string-libraries-abseil-folly-stringzilla/) helps you choose the right string type for serialized data manipulation.

## FAQ

### 1. Can I use Cereal without C++11?

No. Cereal requires at least C++11 and takes advantage of variadic templates, `std::shared_ptr`, and move semantics throughout. For pre-C++11 codebases, Boost.Serialization supports C++03 and is the best alternative. Bitsery requires C++14.

### 2. Does Bitsery support JSON or XML output?

No. Bitsery is a binary-only serialization library by design. This singular focus is what gives it its performance advantage. If you need human-readable output, use Cereal (JSON/XML) or implement a separate text serialization layer alongside Bitsery for debugging purposes.

### 3. How does MessagePack compare to Protobuf for cross-language serialization?

MessagePack is schema-free — you serialize values directly without a `.proto` definition file. Protobuf requires schema definitions and code generation. MessagePack is simpler for rapid development and small teams; Protobuf provides stronger type safety and backward compatibility guarantees for large-scale systems. For C++ specifically, the msgpack-c library is lighter-weight than protobuf's C++ runtime.

### 4. Can I migrate from Boost.Serialization to Cereal?

Partially. Cereal was designed as a cleaner successor by the same developer, and many Boost.Serialization patterns map directly to Cereal. However, the archive formats are incompatible — you'll need a migration strategy (dual-serialize during transition, or write a one-time conversion tool). Cereal's API is generally simpler (`CEREAL_NVP` vs Boost's `BOOST_SERIALIZATION_NVP`).

### 5. Are these libraries safe for untrusted input?

No — none of these libraries are designed for adversarial input. Deserializing untrusted data can lead to buffer overflows, heap corruption, or arbitrary code execution. For security-sensitive contexts, use schema-based formats with validation (Protobuf with input validation) and never deserialize from untrusted sources without sandboxing the process.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Serialization Libraries Compared: Cereal vs Boost.Serialization vs Bitsery vs Msgpack-c",
  "description": "In-depth comparison of four C++ serialization libraries — Cereal, Boost.Serialization, Bitsery, and Msgpack-c — covering API design, performance benchmarks, format support, and use case recommendations for self-hosted development.",
  "datePublished": "2026-06-27",
  "dateModified": "2026-06-27",
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
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://hopkdj.github.io/openswap-guide/posts/2026-06-27-cpp-serialization-libraries-cereal-boost-bitsery-msgpack/"
  }
}
</script>
