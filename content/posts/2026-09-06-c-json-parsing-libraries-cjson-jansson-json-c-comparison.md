---
title: "C JSON Parsing in 2026: cJSON vs Jansson vs json-c — Which One Should You Actually Use?"
date: "2026-09-06"
tags: ["c", "json", "embedded", "parsing", "libraries"]
draft: false
---

If your C program touches JSON, you have three realistic choices — and picking wrong means either shipping a parser that leaks memory under load or writing 400 lines of boilerplate to read a config file. **cJSON** (12,977 stars), **Jansson** (3,362 stars) and **json-c** (3,288 stars) are the three JSON libraries every C developer eventually evaluates. They look interchangeable at first glance, but they encode three completely different answers to the same question: *who owns the memory?*

## TL;DR — Quick Verdict

**Embedding a parser into a firmware or single-file project? Pick cJSON.** Its two-file drop-in design and ANSI C compatibility make it the default for constrained systems. **Building a tool that parses untrusted or streamed data and needs precise error reporting? Pick Jansson** — its `json_error_t` structure gives you line numbers and messages instead of a NULL. **Maintaining long-lived JSON object trees with shared references or needing built-in JSON Pointer (RFC 6901)? Pick json-c** — its reference-counted object model exists precisely for that. All three are MIT-licensed, active in 2026, and will happily parse the same bytes — the difference is what happens after the parse.

## Quick Comparison Table

| Dimension | cJSON | Jansson | json-c |
|---|---|---|---|
| GitHub stars | **12,977** | 3,362 | 3,288 |
| Latest release | v1.7.19 | **v2.15.1** | 0.19 (2026-06-27 tag) |
| Last push | 2026-04-09 | 2026-07-09 | 2026-09-02 |
| License | MIT | MIT | MIT |
| C standard | ANSI C (C89) | C99+ | C99+ |
| Distribution | **2 files** (`cJSON.c`/`.h`) | Shared/static lib + headers | Shared/static lib + headers |
| Memory model | Plain malloc/free tree | Refcounted values | **Refcounted values** |
| Parse API | `cJSON_Parse` family | `json_loads`/`json_loadf` | `json_tokener_parse_ex` |
| Error reporting | NULL + `cJSON_GetErrorPtr` | **`json_error_t` (line + text)** | Tokener error enum |
| Incremental/stream parsing | With length APIs | `json_load_callback` | **Tokener is incremental by design** |
| JSON Pointer (RFC 6901) | No | No | **Yes** |
| Serialization control | Formatted/unformatted/buffered | Flags (indent, sort keys, etc.) | `json_object_to_json_string_ext` flags |
| Build system | CMake/Make/Meson + copy-in | CMake + pkg-config | CMake |
| Docs quality | Single README with caveats | **Full tutorial + API reference** | Doxygen + wiki |

## Decision Matrix — Which One for Your Use Case?

| Use case | Recommended tool | Why |
|---|---|---|
| Firmware, embedded, or single-file vendoring | **cJSON** | Copy two files into your tree; no build system or dependency chain |
| Parsing untrusted input with useful failure messages | **Jansson** | `json_error_t` reports line number and text; strict UTF-8 validation |
| Long-lived object trees shared across modules | **json-c** | Reference counting lets child objects outlive their parent safely |
| Streaming a huge JSON document chunk by chunk | **json-c** | `json_tokener_parse_ex` is built as an incremental parser |
| REST API responses in a one-shot CLI tool | **Jansson** | The official tutorial walks through a complete GitHub API client |
| You need JSON Pointer queries | **json-c** | Only one of the three with built-in RFC 6901 support |
| Old compilers, exotic platforms (Amiga, VxWorks-style toolchains) | **cJSON** | ANSI C89; README even documents Amiga builds |

## cJSON — The Two-File Pragmatist

cJSON is the most-starred C JSON library for a reason: the whole library is `cJSON.c` and `cJSON.h`, written in ANSI C (C89) so it compiles almost anywhere. As the README puts it, cJSON "aims to be the dumbest possible parser that you can get your job done with." You can literally copy the two files into your project and start parsing:

```c
cJSON *json = cJSON_Parse(string);
```

If the input may contain embedded null characters, the README recommends the length-aware variant:

```c
cJSON *json = cJSON_ParseWithLength(string, buffer_length);
```

Parsing allocates a tree of `cJSON` items that you are fully responsible for freeing:

```c
cJSON_Delete(json);
```

On failure you can locate the error position with `cJSON_GetErrorPtr`, although the README warns this "can produce race conditions in multithreading scenarios" — there it suggests `cJSON_ParseWithOpts` with a `return_parse_end` pointer instead. The library ships with an entire worked example (building and parsing a monitor-resolution JSON document) in its README, covering both printing:

```c
char *string = cJSON_Print(json);   /* formatted */
char *string = cJSON_PrintUnformatted(json);
```

and the buffered/preallocated variants (`cJSON_PrintBuffered`, `cJSON_PrintPreallocated`) for systems that want to avoid dynamic reallocations entirely. Building is flexible: plain `make`, CMake (with options like `-DENABLE_CJSON_UTILS=On`, `-DENABLE_SANITIZERS=On`), or Meson. The README's Caveats section is worth reading before production use — it explicitly covers zero characters, character encoding, floating-point handling, deep nesting, thread safety, case sensitivity, and duplicate object members, which tells you exactly where the sharp edges are.

**Best for:** constrained environments, quick tooling, and any project that wants zero build-system entanglement. **Trade-off:** the "dumbest possible parser" philosophy means fewer safety rails — input validation, nesting limits, and encoding checks are largely your problem.

## Jansson — Error Messages You Can Actually Use

Jansson is the library you reach for when a NULL return isn't enough information. Its flagship documentation is a full tutorial that builds a real GitHub commits API client, and the error-handling pattern it teaches is the cleanest of the three. Parsing looks like this (verbatim from the official tutorial):

```c
#include <jansson.h>

root = json_loads(text, 0, &error);
free(text);

if(!root)
{
    fprintf(stderr, "error: on line %d: %s\n", error.line, error.text);
    return 1;
}
```

Where cJSON hands you a bare NULL on failure, Jansson fills a `json_error_t` with a **line number and a human-readable message** — the difference between "parse failed somewhere" and "on line 12: 'expected ':' after object key'". The tutorial then walks through validating the shape of the document:

```c
if(!json_is_array(root))
{
    fprintf(stderr, "error: root is not an array\n");
    json_decref(root);
    return 1;
}
```

and iterating it:

```c
for(i = 0; i < json_array_size(root); i++)
{
    json_t *data = json_array_get(root, i);
    ...
}
```

Memory in Jansson is reference-counted: `json_decref()` on the root releases the whole tree, and the tutorial emphasizes that "every object in the tree will have one reference, from its parent." You compile against it with a conventional library link:

```
gcc -o github_commits github_commits.c -ljansson -lcurl
```

**Best for:** applications where parse failures must be diagnosable — config loaders, network clients, anything ingesting third-party data. **Trade-off:** it is a proper installed library (headers + `-ljansson`), not a drop-in pair of files, so cross-compiling for tiny targets is more work than with cJSON.

## json-c — Reference Counting and JSON Pointer

json-c predates both competitors (it started as the JSON implementation behind the original mDNSResponder-era Mac OS X tools) and its design shows its age in the best way: it is built around a reference-counted `json_object` tree, documented as "a reference counting object model that allows you to easily construct JSON objects in C, output them as JSON formatted strings and parse JSON formatted strings back into the C representation." The README's official API guidance splits headers by concern — `json_object.h` for core types, `json_tokener.h` for parsing, `json_pointer.h` for RFC 6901 queries — and explains the ownership rules precisely: "Typically, every object in the tree will have one reference, from its parent. When you are done with the tree of objects, you call json_object_put() on just the root object to free it." If a child must outlive its parent, you increment its refcount with `json_object_get()`.

Parsing is done through an explicit tokener, which makes incremental parsing of large streams natural. The official `json_parse.c` example application (shipped in the repo's `apps/` directory) shows the real-world pattern:

```c
json_tokener *tok;

tok = json_tokener_new_ex(depth);
...
obj = json_tokener_parse_ex(tok, &buf[start_pos], retu - start_pos);
enum json_tokener_error jerr = json_tokener_get_error(tok);
size_t parse_end = json_tokener_get_parse_end(tok);
```

Serialization goes through `json_object_to_json_string_ext()` with flags for formatting. The project is also the only one of the three with **JSON Pointer (RFC 6901) built in** — if your data layer speaks JSON Pointer, json-c saves you from writing your own query engine. Building is standard out-of-tree CMake:

```sh
$ git clone https://github.com/json-c/json-c.git
$ mkdir json-c-build && cd json-c-build
$ cmake ../json-c
$ make && make test
$ sudo make install
```

**Best for:** daemons and services that keep JSON structures alive for the process lifetime, share subtrees between modules, or need JSON Pointer. **Trade-off:** the most ceremony of the three — multiple headers to learn, an explicit tokener lifecycle, and refcount discipline (`json_object_put`/`json_object_get`) that has no equivalent in cJSON.

## Pitfalls and Migration Notes (What Nobody Tells You)

1. **Mixing memory models will leak or crash.** cJSON trees die with `cJSON_Delete`; Jansson trees die with `json_decref`; json-c trees die with `json_object_put`. If you wrap one library and later swap to another, every free-site in your code is a latent bug. Audit all teardown paths before migrating.
2. **cJSON's error pointer is not thread-safe.** `cJSON_GetErrorPtr` is a global; the README says so explicitly. In multithreaded code use `cJSON_ParseWithOpts` with `return_parse_end` instead.
3. **Jansson refuses malformed UTF-8; cJSON does not validate encoding.** If you parse data from third parties, the same byte stream can parse fine in cJSON and fail in Jansson — that is a feature (strictness), not a Jansson bug. Decide which behavior your contract requires.
4. **json-c's serialized string is borrowed, not owned.** The README warns the string returned by `json_object_to_json_string_ext()` "is only valid until the next to_json_string call on that same object" and is freed when the object is freed. Copy it if you need it later.
5. **Deep nesting is a DoS vector in all three.** cJSON documents its nesting caveats; json-c takes a `depth` argument to `json_tokener_new_ex` for exactly this reason. For untrusted input, bound the depth explicitly rather than relying on defaults.
6. **Zero-character handling differs.** cJSON's classic `cJSON_Parse` operates on zero-terminated strings, so embedded `\0` bytes truncate input — use `cJSON_ParseWithLength` for binary-ish payloads. The other two handle length-delimited input more naturally through their load/tokener APIs.
7. **Reference-count cycles in json-c/Jansson** (an object added to itself, directly or transitively) will never free. Keep trees acyclic.

For context on how JSON parsing libraries compare across languages — including the much faster SIMD-accelerated options like simdjson — see our [cross-language JSON parser comparison](../2026-06-19-self-hosted-json-parser-libraries-simdjson-rapidjson-orjson-ultrajson/), and if you are building C services that speak HTTP, our [embedded C HTTP library guide](../2026-09-04-embedded-c-http-libraries-mongoose-civetweb-libmicrohttpd/) covers the server side of the same coin. Once your parser works, our [C unit testing frameworks comparison](../2026-09-06-c-unit-testing-frameworks-unity-criterion-check-comparison/) shows how to keep it honest.

## Which Library Is Actually Maintained?

All three projects are alive in 2026, which is itself noteworthy for C libraries of this age. cJSON's last push was 2026-04-09 with a v1.7.19 tag — the project moves slowly because it is feature-complete, not abandoned. Jansson pushed 2026-07-09 and shipped v2.15.1; it has the most regular release cadence of the three. json-c is the most actively churning: its latest tag is `json-c-0.19-20260627` (June 2026) and it pushed on 2026-09-02, days before this article was written. If "which one will still be maintained in 2030?" is your tiebreaker, json-c's commit activity is the strongest signal, followed by Jansson, with cJSON the most stable-but-slow. All three also have healthy packaging presence (`libcjson-dev`, `libjansson-dev`, and `libjson-c-dev` are standard in Debian/Ubuntu), so distro-level integration is a non-issue for any of them.

## FAQ

**Is cJSON faster than Jansson and json-c?**
For small documents the differences are usually noise; cJSON's advantage is minimal allocation overhead and no refcount bookkeeping, which matters most when you parse millions of tiny objects (for example, in log processing). None of the three is in the same league as SIMD-accelerated parsers like simdjson — see our [JSON parser libraries comparison](../2026-06-19-self-hosted-json-parser-libraries-simdjson-rapidjson-orjson-ultrajson/) for where those fit.

**Can I use these libraries in a C++ project?**
Yes — all three have C-compatible headers that compile cleanly under C++ (cJSON is even used inside several C++ codebases), though C++ developers usually prefer native options. The main caveat is exception safety: no RAII wrapper exists out of the box, so a `throw` between allocate and free leaks. Wrap the library in a small scope-guard class if you use exceptions.

**Which library is best for embedded systems?**
cJSON is the default answer: ANSI C89, no dependencies, and you can vendor the two source files directly into your firmware tree. json-c and Jansson require building and linking a library, which is awkward for bare-metal toolchains, though Jansson is used in some RTOS environments. cJSON's README even documents Amiga and other exotic platform builds.

**Does any of them support JSON Schema or JSON Pointer?**
JSON Pointer (RFC 6901) is built into json-c (`json_pointer.h`) and is its unique differentiator here. For JSON Schema validation you need a separate library in all three cases — nothing in the C JSON ecosystem has schema validation as mature as what higher-level languages enjoy.

**Are these libraries safe to use with untrusted input?**
Each has a different risk profile. cJSON explicitly documents caveats around encoding, deep nesting, and floating point — you must bound depth and validate input yourself. Jansson validates UTF-8 strictly and reports precise errors, which makes it the safest default for hostile input. json-c's tokener takes an explicit `depth` argument and reports granular error codes via `json_tokener_get_error`. In every case, fuzzing your parse path is strongly recommended before exposing it to the network.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C JSON Parsing in 2026: cJSON vs Jansson vs json-c — Which One Should You Actually Use?",
  "description": "Hands-on comparison of the three mainstream C JSON libraries: cJSON, Jansson and json-c. Covers memory models, error handling, JSON Pointer support, licensing, maintenance activity, and migration pitfalls.",
  "datePublished": "2026-09-06",
  "dateModified": "2026-09-06",
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
