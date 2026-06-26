---
title: "C++ Compression Libraries: LZ4 vs Zstd vs Brotli vs Snappy vs miniz"
date: "2026-06-27"
tags: ["c++", "compression", "data-compression", "performance", "lz4", "zstd", "brotli", "snappy", "c++17"]
draft: false
---

## Introduction

Data compression is a fundamental building block in modern systems engineering — it powers everything from database storage engines and network protocols to log aggregation and file archiving. While command-line tools like gzip and xz are ubiquitous, developers integrating compression into C++ applications need library-level APIs that can compress and decompress data in memory with minimal overhead.

The C++ ecosystem offers several high-quality compression libraries, each optimized for different tradeoffs between compression ratio, speed, and memory usage. This article compares five leading open-source compression libraries with native C/C++ APIs: **LZ4**, **Zstandard (Zstd)**, **Brotli**, **Snappy**, and **miniz**.

## Comparison Table

| Feature | LZ4 | Zstd | Brotli | Snappy | miniz |
|---------|-----|------|--------|--------|-------|
| **Compression Speed** | 500+ MB/s | 350-450 MB/s | 100-150 MB/s | 250-400 MB/s | 80-120 MB/s |
| **Decompression Speed** | 2000+ MB/s | 800-1200 MB/s | 400-600 MB/s | 500-700 MB/s | 200-300 MB/s |
| **Compression Ratio** | 2.0-2.5:1 | 3.0-3.5:1 | 3.5-4.0:1 | 2.0-2.5:1 | 2.0-2.5:1 |
| **Algorithm** | LZ77 variant | Finite state entropy + LZ77 | LZ77 + Huffman + context modeling | LZ77 variant | Deflate (zlib-compatible) |
| **Dictionary Support** | No | Yes (pre-trained) | Yes (shared dict) | No | No |
| **Streaming API** | Yes | Yes | Yes | Yes | Yes |
| **Multi-threading** | No | Yes (built-in) | No | No | No |
| **Header-only Option** | No | No | No | No | Yes (single source file) |
| **GitHub Stars** | 11,890 | 27,291 | 14,771 | 6,585 | 2,803 |
| **Standard Reference** | LZ4 frame format | RFC 8878 | RFC 7932 | Google Snappy format | RFC 1951 (Deflate) |

## LZ4: The Speed King

[LZ4](https://github.com/lz4/lz4) by Yann Collet is the gold standard for extremely fast compression and decompression. Its signature feature is decompression speed exceeding 2 GB/s on modern hardware, making it ideal for real-time applications where latency matters more than compression ratio.

### Installation

```bash
# Ubuntu/Debian
sudo apt install liblz4-dev

# macOS
brew install lz4

# Build from source
git clone https://github.com/lz4/lz4.git
cd lz4
make -j$(nproc)
sudo make install
```

### C++ API Usage

```cpp
#include <lz4.h>
#include <lz4frame.h>
#include <vector>
#include <iostream>
#include <cstring>

int main() {
    const char* original = "Hello World! This is a test of LZ4 compression. "
                           "Repeated content compresses better. Repeated content compresses better.";
    int src_size = strlen(original) + 1;
    
    // Allocate compression buffer (worst case bound)
    int max_compressed = LZ4_compressBound(src_size);
    std::vector<char> compressed(max_compressed);
    
    // Compress with default acceleration
    int compressed_size = LZ4_compress_default(
        original, compressed.data(), src_size, max_compressed);
    
    if (compressed_size <= 0) {
        std::cerr << "Compression failed!" << std::endl;
        return 1;
    }
    
    std::cout << "Original: " << src_size << " bytes" << std::endl;
    std::cout << "Compressed: " << compressed_size << " bytes" << std::endl;
    std::cout << "Ratio: " << (float)compressed_size / src_size << std::endl;
    
    // Decompress
    std::vector<char> decompressed(src_size);
    int decompressed_size = LZ4_decompress_safe(
        compressed.data(), decompressed.data(), compressed_size, src_size);
    
    std::cout << "Decompressed: " << decompressed.data() << std::endl;
    std::cout << "Match: " << (strcmp(original, decompressed.data()) == 0 ? "YES" : "NO") 
              << std::endl;
    
    // Streaming compression with frame format
    LZ4F_compressionContext_t ctx;
    LZ4F_createCompressionContext(&ctx, LZ4F_VERSION);
    
    // Configure for high compression
    LZ4F_preferences_t prefs;
    memset(&prefs, 0, sizeof(prefs));
    prefs.compressionLevel = 9;  // 1-12, higher = better compression
    prefs.frameInfo.blockSizeID = LZ4F_max64KB;
    
    // ... streaming API usage with LZ4F_compressUpdate
    LZ4F_freeCompressionContext(ctx);
    
    return 0;
}
```

### Build Configuration

```cmake
find_package(PkgConfig REQUIRED)
pkg_check_modules(LZ4 REQUIRED liblz4)
target_link_libraries(my_app ${LZ4_LIBRARIES})
target_include_directories(my_app PRIVATE ${LZ4_INCLUDE_DIRS})
```

### When to Use LZ4

- Real-time data streaming and network protocols
- Database write-ahead logs and replication streams
- In-memory compression where latency budgets are tight (< 10μs)
- Filesystem compression (ZFS, Btrfs, SquashFS all support LZ4)

## Zstandard (Zstd): The Balanced Champion

[Zstandard](https://github.com/facebook/zstd) by Yann Collet (also the creator of LZ4) was developed at Facebook to provide compression ratios approaching `zlib` while maintaining speeds competitive with LZ4. It has become the default compression engine for many modern systems including the Linux kernel, PostgreSQL, and the `.zst` archive format.

### Installation

```bash
# Ubuntu/Debian
sudo apt install libzstd-dev

# macOS
brew install zstd

# Build from source
git clone https://github.com/facebook/zstd.git
cd zstd
make -j$(nproc)
sudo make install
```

### C++ API Usage

```cpp
#include <zstd.h>
#include <vector>
#include <iostream>
#include <cstring>

int main() {
    const char* original = "The Zstandard compression algorithm uses a combination "
                           "of LZ77 matching and finite state entropy coding to "
                           "achieve excellent compression ratios at high speeds.";
    size_t src_size = strlen(original) + 1;
    
    // Allocate compression buffer
    size_t max_compressed = ZSTD_compressBound(src_size);
    std::vector<char> compressed(max_compressed);
    
    // Compress — level 3 is default, 1-22 range
    size_t compressed_size = ZSTD_compress(
        compressed.data(), max_compressed,
        original, src_size,
        3);  // compression level
    
    std::cout << "Original: " << src_size << " bytes" << std::endl;
    std::cout << "Compressed: " << compressed_size << " bytes" << std::endl;
    
    // Get compression frame info
    unsigned long long decompressed_size = ZSTD_getFrameContentSize(
        compressed.data(), compressed_size);
    
    // Decompress
    std::vector<char> decompressed(decompressed_size);
    size_t result = ZSTD_decompress(
        decompressed.data(), decompressed_size,
        compressed.data(), compressed_size);
    
    if (ZSTD_isError(result)) {
        std::cerr << "Decompression error: " << ZSTD_getErrorName(result) << std::endl;
        return 1;
    }
    
    std::cout << "Match: " << (strcmp(original, decompressed.data()) == 0 ? "YES" : "NO") 
              << std::endl;
    
    // Multi-threaded compression
    size_t mt_result = ZSTD_compress2(
        ZSTD_createCCtx(),  // compression context
        compressed.data(), max_compressed,
        original, src_size);
    
    // Using a pre-trained dictionary for small data
    // ZSTD_CCtx_loadDictionary(ctx, dict_data, dict_size);
    
    return 0;
}
```

Zstd's killer feature is its **compression level slider**: levels 1-3 offer LZ4-class speed, levels 4-9 provide gzip-class ratio, and levels 10-22 deliver xz-class compression ratio with extreme CPU usage. This adaptability means a single library can serve both hot-path and cold-storage use cases.

### When to Use Zstd

- General-purpose compression for file formats and network protocols
- Database storage engines (MongoDB, PostgreSQL, RocksDB)
- Package managers and container image layers
- When you need a single library that covers both speed and ratio extremes

## Brotli: Web-Optimized Compression

[Google Brotli](https://github.com/google/brotli) was designed specifically for web content compression — HTML, CSS, JavaScript, and fonts. It achieves some of the best compression ratios available through its combination of LZ77, Huffman coding, and second-order context modeling with a large static dictionary pre-loaded with common web strings.

### Installation

```bash
# Ubuntu/Debian
sudo apt install libbrotli-dev

# macOS
brew install brotli

# Build from source
git clone https://github.com/google/brotli.git
cd brotli
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

### C++ API Usage

```cpp
#include <brotli/encode.h>
#include <brotli/decode.h>
#include <vector>
#include <iostream>
#include <cstring>

int main() {
    const char* original = R"HTML(
        <!DOCTYPE html><html><head><title>Test Page</title>
        </head><body><h1>Hello World</h1>
        <p>Brotli excels at compressing web content with its
        built-in static dictionary containing common HTML tags,
        CSS properties, and JavaScript keywords.</p></body></html>
    )HTML";
    size_t src_size = strlen(original);
    
    // Compress — quality 1-11 (default 11)
    size_t max_compressed = BrotliEncoderMaxCompressedSize(src_size);
    std::vector<uint8_t> compressed(max_compressed);
    size_t compressed_size = max_compressed;
    
    BROTLI_BOOL ok = BrotliEncoderCompress(
        BROTLI_DEFAULT_QUALITY,  // 11 = maximum
        BROTLI_DEFAULT_WINDOW,   // 22 = 4MB window
        BROTLI_DEFAULT_MODE,     // generic
        src_size,
        (const uint8_t*)original,
        &compressed_size,
        compressed.data());
    
    if (ok != BROTLI_TRUE) {
        std::cerr << "Compression failed!" << std::endl;
        return 1;
    }
    
    std::cout << "Original: " << src_size << " bytes" << std::endl;
    std::cout << "Compressed: " << compressed_size << " bytes" << std::endl;
    
    // Decompress
    std::vector<uint8_t> decompressed(src_size);
    size_t decompressed_size = src_size;
    
    BrotliDecoderDecompress(
        compressed_size, compressed.data(),
        &decompressed_size, decompressed.data());
    
    std::cout << "Decompressed size: " << decompressed_size << std::endl;
    std::cout << "Match: " << (memcmp(original, decompressed.data(), src_size) == 0 ? "YES" : "NO")
              << std::endl;
    
    // Streaming encode with custom quality
    BrotliEncoderState* encoder = BrotliEncoderCreateInstance(nullptr, nullptr, nullptr);
    if (encoder) {
        BrotliEncoderSetParameter(encoder, BROTLI_PARAM_QUALITY, 6);
        BrotliEncoderSetParameter(encoder, BROTLI_PARAM_SIZE_HINT, src_size);
        // ... streaming API with BrotliEncoderCompressStream
        BrotliEncoderDestroyInstance(encoder);
    }
    
    return 0;
}
```

### When to Use Brotli

- Web content delivery (HTTP Content-Encoding: br)
- Compressing text-based formats (JSON, XML, HTML, CSS)
- Font compression (WOFF2 format uses Brotli internally)
- Static asset compression for CDNs and web servers

## Snappy: Google's Speed-First Compressor

[Snappy](https://github.com/google/snappy) was developed at Google for their internal Bigtable storage system. It prioritizes speed over compression ratio — the design goal was "fast enough for live RPC traffic."

### Installation

```bash
# Ubuntu/Debian
sudo apt install libsnappy-dev

# macOS
brew install snappy

# Build from source
git clone https://github.com/google/snappy.git
cd snappy
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DSNAPPY_BUILD_TESTS=OFF
make -j$(nproc)
sudo make install
```

### C++ API Usage

```cpp
#include <snappy.h>
#include <snappy-sinksource.h>
#include <string>
#include <iostream>

int main() {
    std::string original = "Snappy is optimized for speed. It aims for "
                           "200-400 MB/s compression and 500-700 MB/s "
                           "decompression on a single CPU core.";
    
    // Simple compress/decompress
    std::string compressed;
    snappy::Compress(original.data(), original.size(), &compressed);
    
    std::cout << "Original: " << original.size() << " bytes" << std::endl;
    std::cout << "Compressed: " << compressed.size() << " bytes" << std::endl;
    
    // Decompress
    std::string decompressed;
    bool ok = snappy::Uncompress(compressed.data(), compressed.size(), &decompressed);
    
    if (!ok) {
        std::cerr << "Decompression failed!" << std::endl;
        return 1;
    }
    
    std::cout << "Match: " << (original == decompressed ? "YES" : "NO") << std::endl;
    
    // Get uncompressed length without decompressing
    size_t uncompressed_len;
    if (snappy::GetUncompressedLength(compressed.data(), compressed.size(), 
                                       &uncompressed_len)) {
        std::cout << "Uncompressed length from header: " << uncompressed_len << std::endl;
    }
    
    return 0;
}
```

### When to Use Snappy

- Database storage engines (LevelDB, RocksDB, Cassandra)
- RPC serialization (Google's Protocol Buffers integration)
- In-memory caching layers
- When you need predictable, low-variance compression latency

## miniz: Single-File Deflate Implementation

[miniz](https://github.com/richgel999/miniz) is a unique entry in this comparison — it's a single C source file that implements the entire Deflate/zlib/gzip compression stack with zero dependencies. Originally extracted from the `stb_image` ecosystem, miniz has grown to support full zlib compatibility, ZIP archive creation, and even a basic PNG writer.

### Installation

```bash
# Just copy the two files into your project
wget https://raw.githubusercontent.com/richgel999/miniz/master/miniz.h
wget https://raw.githubusercontent.com/richgel999/miniz/master/miniz.c
```

### C++ API Usage

```cpp
// In one .cpp file:
#define MINIZ_HEADER_FILE_ONLY
#include "miniz.h"

// In another .cpp file with the implementation:
#include "miniz.c"

// Usage:
#include "miniz.h"
#include <vector>
#include <iostream>
#include <cstring>

int main() {
    const char* original = "miniz provides a complete zlib-compatible compression "
                           "stack in a single file with no external dependencies.";
    mz_ulong src_len = strlen(original);
    
    // Compress with Deflate
    mz_ulong compressed_len = compressBound(src_len);
    std::vector<unsigned char> compressed(compressed_len);
    
    int result = compress(
        compressed.data(), &compressed_len,
        (const unsigned char*)original, src_len);
    
    if (result != Z_OK) {
        std::cerr << "Compression failed!" << std::endl;
        return 1;
    }
    
    // Decompress
    std::vector<unsigned char> decompressed(src_len);
    mz_ulong decompressed_len = src_len;
    
    result = uncompress(
        decompressed.data(), &decompressed_len,
        compressed.data(), compressed_len);
    
    std::cout << "Match: " << (memcmp(original, decompressed.data(), src_len) == 0 ? "YES" : "NO")
              << std::endl;
    
    // High-level API with compression levels
    size_t high_quality_size = tdefl_compress_bound(src_len);
    std::vector<unsigned char> high_quality(high_quality_size);
    
    int level = MZ_BEST_COMPRESSION;  // 9 = maximum zlib level
    
    // ... use tdefl/tinfl API for more control
    
    return 0;
}
```

### When to Use miniz

- Embedded systems and game engines where dependency minimization matters
- Projects that need zlib compatibility without linking an external library
- ZIP/DEFLATE format support in cross-platform applications
- Learning compression internals (the single-file code is well-commented)

## Compression Speed vs Ratio Tradeoff

The fundamental tradeoff in compression is between CPU time and output size. Here's how the libraries rank:

```
    Compression Ratio (higher is better)
    ┌────────────────────────────────────────┐
    │ Brotli ████████████████████████████ 3.8:1
    │ Zstd L19█████████████████████████   3.5:1
    │ Zstd L3  ███████████████████       2.8:1
    │ LZ4      ██████████████            2.2:1
    │ Snappy   █████████████             2.1:1
    │ miniz    █████████████             2.2:1
    └────────────────────────────────────────┘

    Compression Speed (higher is better)
    ┌────────────────────────────────────────┐
    │ LZ4      ████████████████████████████ 500 MB/s
    │ Snappy   ████████████████████████    400 MB/s
    │ Zstd L1  ███████████████████████     350 MB/s
    │ Brotli L1█████████████              180 MB/s
    │ miniz    ████████                   100 MB/s
    └────────────────────────────────────────┘
```

## Choosing the Right Library

- **Choose LZ4** when decompression speed is the top priority (real-time systems, databases, filesystems)
- **Choose Zstd** for the best balance of speed and ratio, or when you need a single library that covers multiple use cases
- **Choose Brotli** for web content and text-heavy data where ratio matters more than speed
- **Choose Snappy** for predictable, low-variance performance in storage systems
- **Choose miniz** for embedded projects, zero-dependency builds, or zlib format compatibility

## FAQ

### Can I use these libraries for streaming compression?

Yes, all five libraries support streaming compression. LZ4, Zstd, and Brotli have well-designed streaming APIs that can process arbitrarily large data in chunks. Snappy and miniz also support streaming but with slightly more manual buffer management required.

### Which library handles small data best?

For very small payloads (< 1KB), LZ4 and Snappy have the lowest overhead. Brotli includes a static dictionary that can dramatically improve compression of small web content. Zstd offers dictionary training — you can pre-train a dictionary on representative samples of your data for highly efficient small-payload compression.

### How do these compare to gzip?

gzip (Deflate) is the baseline. LZ4 is 5-10x faster at compression and 10-20x faster at decompression with slightly worse ratio. Zstd at level 3 matches gzip's ratio at 3-5x the speed. Brotli produces 15-20% smaller output than gzip for text but is slower. miniz is a zlib-compatible implementation, so it directly provides gzip-level compression.

### What about encryption?

None of these libraries provide built-in encryption. The standard approach is to compress first, then encrypt the compressed data. For integrated authenticated encryption with compression, consider using libsodium's `crypto_aead` combined with any of these compression libraries.

### Which library has the best ecosystem?

Zstd has by far the widest ecosystem support — it's used in the Linux kernel, PostgreSQL, MongoDB, Docker/OCI images, the RPM package format, and the `.zst` archive format. Its RFC standardization (RFC 8878) ensures long-term stability and cross-platform compatibility. For related system tools, see our [Linux compression tools guide](../2026-06-01-linux-compression-tools-zstd-brotli-lz4-gzip/). For binary serialization that pairs well with compression, check our [schema serialization guide](../2026-06-19-schema-serialization-frameworks-protobuf-capnproto-flatbuffers-thrift/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Compression Libraries: LZ4 vs Zstd vs Brotli vs Snappy vs miniz",
  "description": "Compare five leading C/C++ compression libraries: LZ4 (speed king at 2GB/s decompression), Zstd (balanced champion), Brotli (web-optimized), Snappy (Google's speed-first), and miniz (single-file zero-dependency). Includes code examples, benchmarks, and use-case recommendations.",
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
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
