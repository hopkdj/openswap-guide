---
title: "Self-Hosted CBOR Binary Serialization Libraries: libcbor vs tinycbor vs QCBOR vs libbinn"
date: "2026-06-21"
tags: ["cbor", "serialization", "binary-encoding", "developer-tools", "open-source", "iot", "embedded"]
draft: false
---

**CBOR** (Concise Binary Object Representation, RFC 8949) is rapidly becoming the go-to binary serialization format for resource-constrained environments. Unlike JSON, which wastes bandwidth on repeated field names and whitespace, CBOR encodes data in a compact binary form while preserving JSON's flexible data model — objects, arrays, strings, numbers, booleans, and null. It is the backbone of the **IETF's COSE** (CBOR Object Signing and Encryption) standard and is used in **FIDO2 WebAuthn**, **W3C Web of Things**, and **Constrained Application Protocol (CoAP)**.

For C and C++ developers working in embedded systems, IoT firmware, or protocol implementation, choosing the right CBOR library is critical. In this guide, we compare **four open-source CBOR libraries** — libcbor, tinycbor, QCBOR, and libbinn — across API design, memory footprint, standard compliance, and integration ease.

## What Makes CBOR Different from JSON and Protocol Buffers?

| Feature | JSON | Protocol Buffers | CBOR |
|---------|------|-----------------|------|
| **Encoding** | Text (UTF-8) | Binary (schema) | Binary (self-describing) |
| **Size Overhead** | High (field names, punctuation) | Low | Very Low |
| **Schema Required** | No | Yes (.proto) | No |
| **Streaming Parsing** | Limited | Yes | Yes |
| **Integer Representation** | IEEE 754 double only | Fixed/variable encoding | Native int64/uint64/bigint/float |
| **Map Key Types** | String only | Integer/string | Any CBOR type |
| **Binary Data** | Base64-encoded | Native bytes | Native byte strings |
| **Standard** | RFC 8259 | Google-defined | RFC 8949 (IETF) |
| **Ideal For** | Web APIs, config | RPC, microservices | IoT, firmware, security tokens |

CBOR's key advantage is that it is **self-describing** (no schema required) yet **compact** (binary encoding). This makes it ideal for firmware update packages, sensor telemetry, and cryptographic message formats.

## libcbor: The Reference Implementation

**libcbor** ([github.com/PJK/libcbor](https://github.com/PJK/libcbor)) is the most feature-complete and standards-compliant CBOR implementation for C. Written by Petr Krajča, it closely tracks the RFC 8949 specification and supports the full CBOR data model including indefinite-length strings, big integers (`bignum`), decimal fractions, and tags.

```c
#include <cbor.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    cbor_item_t *root = cbor_new_definite_map(3);

    // Add string key -> integer value
    cbor_map_add(root, (struct cbor_pair) {
        .key = cbor_move(cbor_build_string("temperature")),
        .value = cbor_move(cbor_build_uint32(237))
    });

    // Add string key -> array value
    cbor_item_t *coords = cbor_new_definite_array(2);
    cbor_array_push(coords, cbor_move(cbor_build_float8(51.5074)));
    cbor_array_push(coords, cbor_move(cbor_build_float8(-0.1278)));
    cbor_map_add(root, (struct cbor_pair) {
        .key = cbor_move(cbor_build_string("location")),
        .value = cbor_move(coords)
    });

    // Serialize to buffer
    unsigned char *buffer;
    size_t buffer_size;
    cbor_serialize_alloc(root, &buffer, &buffer_size);
    printf("Encoded %zu bytes\n", buffer_size);

    cbor_decref(&root);
    free(buffer);
    return 0;
}
```

**Integration** via CMake or pkg-config:
```cmake
find_package(libcbor REQUIRED)
target_link_libraries(my_app PRIVATE libcbor::cbor)
```
```bash
# Or via system package manager
sudo apt install libcbor-dev
```

**Key strengths:**
- Complete RFC 8949 compliance (all major types, all tags)
- Streaming parser API for memory-constrained environments
- Reference counting for safe memory management
- Active maintenance (last commit April 2026)
- Thorough test suite with > 1,200 test vectors

**Limitations:** Larger code size (~40KB compiled) compared to tinycbor, C-only (no C++ convenience wrappers), and the reference-counting API has a steeper learning curve.

## tinycbor: Intel's Embedded-First CBOR

**tinycbor** ([github.com/intel/tinycbor](https://github.com/intel/tinycbor)) was developed by Intel for resource-constrained embedded systems. It is designed to compile to minimal binary size and uses a simple iterator-based API that avoids dynamic memory allocation.

```c
#include <tinycbor/cbor.h>
#include <stdio.h>
#include <string.h>

int main() {
    uint8_t buf[256];
    CborEncoder encoder, map_encoder;
    cbor_encoder_init(&encoder, buf, sizeof(buf), 0);
    
    cbor_encoder_create_map(&encoder, &map_encoder, 2);
    cbor_encode_text_stringz(&map_encoder, "sensor");
    cbor_encode_text_stringz(&map_encoder, "bme280");
    cbor_encode_text_stringz(&map_encoder, "humidity");
    cbor_encode_double(&map_encoder, 62.5);
    cbor_encoder_close_container(&encoder, &map_encoder);

    size_t len = cbor_encoder_get_buffer_size(&encoder, buf);
    printf("Encoded %zu bytes\n", len);

    // Decoding
    CborParser parser;
    CborValue it;
    cbor_parser_init(buf, len, 0, &parser, &it);
    cbor_value_enter_container(&it, &it);
    
    while (!cbor_value_at_end(&it)) {
        char key[32]; size_t keylen = sizeof(key);
        cbor_value_copy_text_string(&it, key, &keylen, NULL);
        cbor_value_advance(&it);
        if (cbor_value_is_double(&it)) {
            double val;
            cbor_value_get_double(&it, &val);
            printf("  %s: %.1f\n", key, val);
        }
        cbor_value_advance(&it);
    }
    return 0;
}
```

**Key strengths:**
- Tiny binary footprint (~8KB compiled with `-Os`)
- Iterator-based pull parser — zero heap allocations
- Supports C89 for maximum embedded compatibility
- Active maintenance by Intel (last commit June 2026)
- Used in OpenThread, Zephyr RTOS, and mbed OS

**Limitations:** C-only API (verbose for C++ projects), fewer tag type helpers than libcbor, and no built-in schema validation.

## QCBOR: Security and Standards Compliance

**QCBOR** ([github.com/laurencelundblade/QCBOR](https://github.com/laurencelundblade/QCBOR)) stands out for its focus on **security and standards compliance**. Developed by Laurence Lundblade (a former Qualcomm engineer and IETF COSE co-author), QCBOR is designed specifically for cryptographic applications — it is used in the **IETF SUIT** (firmware update manifest) and **COSE** (CBOR Object Signing and Encryption) standards.

```c
#include <qcbor/qcbor.h>
#include <qcbor/qcbor_spiffy_decode.h>
#include <stdio.h>

int main() {
    UsefulBuf_MAKE_STACK_UB(buffer, 300);
    QCBOREncodeContext ec;
    QCBOREncode_Init(&ec, buffer);
    
    QCBOREncode_OpenMap(&ec);
    QCBOREncode_AddTextToMap(&ec, "algorithm");
    QCBOREncode_AddInt64ToMap(&ec, -7);  // ES256
    QCBOREncode_AddTextToMap(&ec, "key_id");
    QCBOREncode_AddBytesToMap(&ec, (UsefulBufC){"device1", 7});
    QCBOREncode_CloseMap(&ec);

    UsefulBufC encoded;
    QCBORError err = QCBOREncode_Finish(&ec, &encoded);
    if (err == QCBOR_SUCCESS) {
        printf("Encoded %zu bytes of COSE structure\n", encoded.len);
    }
    return 0;
}
```

```cmake
# QCBOR is distributed as source files — just add to your build
add_library(qcbor qcbor/src/qcbor_encode.c qcbor/src/qcbor_decode.c
            qcbor/src/ieee754.c qcbor/src/qcbor_err_to_str.c)
target_include_directories(qcbor PUBLIC qcbor/inc)
target_link_libraries(my_app PRIVATE qcbor)
```

**Key strengths:**
- Purpose-built for cryptographic standards (COSE, SUIT, CWT)
- Spiffy decode API — type-safe, float-compatible decoding
- Detailed error codes for robust error handling
- Designed for deterministic encoding (critical for digital signatures)
- No dynamic memory allocation in the core encode/decode path

**Limitations:** Narrower focus than libcbor (prioritizes crypto use cases), no streaming encoder, and the `UsefulBuf` abstraction takes time to learn.

## libbinn: A Lighter Alternative

**libbinn** ([github.com/liteserver/binn](https://github.com/liteserver/binn)) is not strictly a CBOR library — it uses its own compact binary format that is conceptually similar and was designed to be even simpler than CBOR. It uses a minimal API surface and is popular in game development and real-time systems.

```c
#include <binn.h>
#include <stdio.h>

int main() {
    binn *obj = binn_object();
    binn_object_set_int32(obj, "id", 42);
    binn_object_set_str(obj, "name", "temperature_sensor");
    binn_object_set_double(obj, "value", 23.7);

    int size = binn_size(obj);
    printf("Encoded %d bytes\n", size);

    // Decode
    binn *read = binn_open(binn_ptr(obj));
    printf("ID: %d\n", binn_object_int32(read, "id"));
    printf("Name: %s\n", binn_object_str(read, "name"));
    printf("Value: %.1f\n", binn_object_double(read, "value"));

    binn_free(obj);
    binn_free(read);
    return 0;
}
```

**Key strengths:**
- Extremely simple API — three functions cover 90% of use cases
- Faster than CBOR for simple data types (no tag system overhead)
- Portable (no external dependencies)
- Good for inter-process communication and save files
- Single .c/.h pair

**Limitations:** Not CBOR-compliant (proprietary format), slower for complex nested structures, no streaming support, and less active maintenance (last update July 2025).

## Library Comparison Matrix

| Criterion | libcbor | tinycbor | QCBOR | libbinn |
|-----------|---------|----------|-------|---------|
| **GitHub Stars** | 401 | 615 | 231 | 481 |
| **Standard** | Full RFC 8949 | Full RFC 8949 | RFC 8949 (COSE focus) | Proprietary |
| **Binary Size** | ~40KB | ~8KB | ~15KB | ~10KB |
| **Allocation** | Heap (ref-counted) | Stack/static | Stack/static | Heap |
| **Streaming Parser** | Yes | Yes (pull parser) | No | No |
| **Tag Support** | All RFC tags | Common tags | COSE-specific | None |
| **Floating Point** | Half/single/double | Half/single/double | Half/single/double | Single/double |
| **Big Integer** | Yes (`bignum`) | Yes (`biguint`) | Yes | No |
| **Indefinite Length** | Yes | Yes | No | No |
| **C++ Wrapper** | No (C-only) | No (C-only) | No (C-only) | C++ compatible |

## Integration Patterns for IoT Firmware

When deploying CBOR in embedded Linux or bare-metal environments, the key concerns are memory allocation and binary size. Here is a typical firmware message pipeline using tinycbor:

```c
// Sensor telemetry encoding for CoAP over 6LoWPAN
uint8_t telemetry_buf[128];
CborEncoder enc;
cbor_encoder_init(&enc, telemetry_buf, sizeof(telemetry_buf), 0);

CborEncoder map;
cbor_encoder_create_map(&enc, &map, CborIndefiniteLength);

cbor_encode_uint(&map, 1);  // CBOR label for "timestamp"
cbor_encode_uint(&map, get_unix_time());

cbor_encode_uint(&map, 2);  // CBOR label for "readings"
CborEncoder arr;
cbor_encoder_create_array(&map, &arr, CborIndefiniteLength);
for (int i = 0; i < sensor_count; i++) {
    cbor_encode_double(&arr, sensor_readings[i]);
}
cbor_encoder_close_container(&map, &arr);
cbor_encoder_close_container(&enc, &map);

// Transmit via CoAP
coap_send(telemetry_buf, cbor_encoder_get_buffer_size(&enc, telemetry_buf));
```

For broader protocol integration, see our [binary serialization frameworks guide](../2026-06-19-binary-serialization-frameworks-bincode-borsh-postcard-rkyv/) comparing Rust-native alternatives, and our [schema-based serialization comparison](../2026-06-19-schema-serialization-frameworks-protobuf-capnproto-flatbuffers-thrift/) covering Protocol Buffers, Cap'n Proto, and FlatBuffers.

## Choosing Based on Your Use Case

- **IoT firmware with tight memory constraints**: **tinycbor** — smallest binary, pull parser with zero heap allocation
- **Cryptographic protocol implementation (COSE, CWT)**: **QCBOR** — designed specifically for these standards
- **General-purpose CBOR with full RFC compliance**: **libcbor** — most complete implementation
- **Game development or IPC with minimal API surface**: **libbinn** — simplest API, fast for simple data

For JSON-based workflows, see our [self-hosted JSON parser comparison](../2026-06-19-self-hosted-json-parser-libraries-simdjson-rapidjson-orjson-ultrajson/) covering simdjson, RapidJSON, and orjson.

## FAQ

### Why use CBOR instead of JSON for IoT?
JSON requires text encoding (5 bytes for `"temp"`, plus quotes and colons), while CBOR encodes the same data in 1-2 bytes per field. For a typical sensor payload of 100 bytes in JSON, CBOR often reduces it to 30-50 bytes — critical when transmitting over LPWAN (LoRaWAN, NB-IoT) where every byte costs battery life.

### Is CBOR faster to parse than JSON?
Yes, significantly. Binary integer parsing is O(1) while JSON number parsing requires scanning ASCII digits, handling scientific notation, and converting to binary. Benchmarks show CBOR parsing is 3-5x faster than equivalent JSON for typical payloads.

### Can CBOR handle cyclic data structures?
No. Like JSON, CBOR is a tree-structured format and does not support object references or cycles. Use a graph serialization library or design your data structures to avoid cycles.

### What is CBOR diagnostic notation?
CBOR diagnostic notation is a human-readable text representation defined in RFC 8949 Appendix G. For example, the CBOR bytes `¡ÿ` map to `{1: 255}` in diagnostic notation. All four libraries support diagnostic output for debugging.

### Does libbinn interoperate with standard CBOR implementations?
No. libbinn uses its own binary format that is not CBOR-compliant. If interoperability with CBOR-speaking services (FIDO2 servers, CoAP endpoints) is required, use libcbor, tinycbor, or QCBOR instead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CBOR Binary Serialization Libraries: libcbor vs tinycbor vs QCBOR vs libbinn",
  "description": "In-depth comparison of four CBOR and binary serialization libraries for C/C++ — libcbor, tinycbor, QCBOR, and libbinn — covering RFC 8949 compliance, memory footprint, IoT/embedded integration, and cryptographic standards support.",
  "datePublished": "2026-06-21",
  "dateModified": "2026-06-21",
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
