---
title: "Regular Expression Engine Libraries Compared: RE2 vs PCRE2 vs Hyperscan vs Oniguruma"
date: "2026-06-22"
tags: ["c++", "regex", "pattern-matching", "text-processing", "developer-tools", "open-source", "libraries", "performance", "comparison"]
draft: false
---

Regular expressions are one of the most widely used tools in software engineering, powering everything from log parsing and input validation to network intrusion detection and search engines. But not all regex engines are created equal. The underlying algorithm — backtracking versus finite automaton — determines whether your regex will complete in microseconds or hang indefinitely on certain inputs.

In this article, we compare four leading C/C++ regular expression libraries: **RE2** (9,709 stars), **Hyperscan** (5,423 stars), **Oniguruma** (2,524 stars), and **PCRE2** (1,302 stars). Each represents a fundamentally different approach to pattern matching, and choosing the right one depends heavily on your use case.

## Library Overview

| Library | Stars | Algorithm | Thread Safety | Best For |
|---------|-------|-----------|--------------|----------|
| **RE2** | 9,709 | DFA/NFA (linear time) | Yes | Safe user-input regex, server applications |
| **Hyperscan** | 5,423 | SIMD-accelerated NFA/DFA | Yes (streaming) | High-throughput pattern matching, IDS/IPS |
| **Oniguruma** | 2,524 | Backtracking NFA | No (global state) | Feature-rich matching, Ruby/PHP ecosystem |
| **PCRE2** | 1,302 | Backtracking NFA (JIT) | Re-entrant | Perl-compatible syntax, legacy compatibility |

## RE2: Safe, Linear-Time Matching

[RE2](https://github.com/google/re2) was designed by Google specifically to address the catastrophic backtracking problem that affects traditional regex engines. It guarantees linear-time matching by using automata-based algorithms (DFA and NFA simulation) instead of backtracking. This means you can safely accept regular expressions from untrusted users without risk of ReDoS (Regular Expression Denial of Service) attacks.

```cpp
#include <re2/re2.h>
#include <iostream>

int main() {
    // RE2 patterns compile explicitly — no hidden global state
    RE2 pattern(R"((\d{4})-(\d{2})-(\d{2}))");
    if (!pattern.ok()) {
        std::cerr << "Pattern error: " << pattern.error() << "\n";
        return 1;
    }

    std::string date_str = "Event date: 2026-06-22";
    std::string year, month, day;

    if (RE2::PartialMatch(date_str, pattern, &year, &month, &day)) {
        std::cout << "Year: " << year << "\n";
        std::cout << "Month: " << month << "\n";
        std::cout << "Day: " << day << "\n";
    }

    // Full-match with extraction
    std::string extracted;
    RE2::FullMatch("hello@example.com",
                   RE2(R"(([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}))"),
                   &extracted);
    std::cout << "Username: " << extracted << "\n";

    // Global replace
    std::string text = "foo123bar456baz";
    RE2::GlobalReplace(&text, RE2(R"(\d+)"), "NUM");
    // text = "fooNUMbarNUMbaz"
    return 0;
}
```

**Key features:**
- Linear-time matching guarantee — no pathological cases
- Thread-safe: multiple threads can match against the same compiled pattern
- Small, predictable memory usage
- Full Unicode support
- Limited feature set (no backreferences, no look-around assertions)
- C++ and Go implementations available

**When to use RE2:** Any server application that processes user-supplied regex patterns, input validation in web services, log parsing pipelines, and situations where predictable performance is more important than regex feature completeness.

## PCRE2: Perl-Compatible Feature Completeness

[PCRE2](https://github.com/PCRE2Project/pcre2) is the successor to the original PCRE library and provides the most feature-complete Perl-compatible regex engine available in C. It's the engine underlying countless programming languages and tools, from PHP's `preg_*` functions to the Apache HTTP server.

```c
#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>
#include <stdio.h>

int main() {
    int errcode;
    PCRE2_SIZE erroffset;

    // Compile with JIT for maximum performance
    pcre2_code *re = pcre2_compile(
        (PCRE2_SPTR)"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})",
        PCRE2_ZERO_TERMINATED,
        0,
        &errcode, &erroffset, NULL);

    if (!re) {
        PCRE2_UCHAR buffer[256];
        pcre2_get_error_message(errcode, buffer, sizeof(buffer));
        fprintf(stderr, "PCRE2 error: %s\n", buffer);
        return 1;
    }

    // JIT compile for faster matching
    pcre2_jit_compile(re, PCRE2_JIT_COMPLETE);

    PCRE2_SPTR subject = (PCRE2_SPTR)"Date: 2026-06-22";
    pcre2_match_data *match = pcre2_match_data_create_from_pattern(re, NULL);

    int rc = pcre2_match(re, subject, PCRE2_ZERO_TERMINATED,
                         0, 0, match, NULL);

    if (rc >= 0) {
        PCRE2_SIZE *ovector = pcre2_get_ovector_pointer(match);
        printf("Full match at %zu-%zu\n", ovector[0], ovector[1]);
        // Named substrings accessible via pcre2_substring_number_from_name()
    }

    pcre2_match_data_free(match);
    pcre2_code_free(re);
    return 0;
}
```

**Key features:**
- Perl-compatible syntax with full feature set (backreferences, look-ahead, look-behind)
- JIT compilation for 5-20x speedup on supported platforms
- Callout support for application-defined matching logic
- Extensive Unicode properties
- Partial matching (streaming) support
- Substitution with backreferences

**When to use PCRE2:** Porting Perl/PHP regexes to C/C++, needing advanced regex features (recursive patterns, conditional subpatterns), situations where JIT-compiled backtracking with full features is acceptable, and legacy codebases that already depend on PCRE.

## Hyperscan: SIMD-Accelerated High Throughput

[Hyperscan](https://github.com/intel/hyperscan) takes a radically different approach: it uses SIMD instructions (SSE4.2, AVX2, AVX-512) to match hundreds of patterns simultaneously against streaming data. Originally developed for network intrusion detection, it's now used anywhere massive-scale pattern matching is needed.

```cpp
#include <hs/hs.h>
#include <vector>
#include <iostream>

// Callback invoked for each match
static int onMatch(unsigned int id, unsigned long long from,
                   unsigned long long to, unsigned int flags, void *ctx) {
    std::cout << "Pattern " << id << " matched at byte "
              << from << " to " << to << "\n";
    return 0;  // Continue matching
}

int main() {
    hs_database_t *database = nullptr;
    hs_compile_error_t *compile_err = nullptr;

    // Compile multiple patterns as a pattern set
    const char *patterns[] = {
        "\bERROR\b",
        "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  // IPv4
        "[a-f0-9]{32}",  // MD5 hash
    };
    unsigned int flags[] = {HS_FLAG_CASELESS, 0, 0};
    unsigned int ids[] = {100, 200, 300};

    hs_error_t err = hs_compile_multi(
        patterns, flags, ids, 3,
        HS_MODE_BLOCK, nullptr, &database, &compile_err);

    if (err != HS_SUCCESS) {
        std::cerr << "Compile error: " << compile_err->message << "\n";
        hs_free_compile_error(compile_err);
        return 1;
    }

    // Scan a buffer (could be a network packet, log chunk, etc.)
    const char *data = "ERROR: Connection failed from 192.168.1.100";
    hs_scratch_t *scratch = nullptr;
    hs_alloc_scratch(database, &scratch);

    hs_scan(database, data, strlen(data), 0, scratch, onMatch, nullptr);

    hs_free_scratch(scratch);
    hs_free_database(database);
    return 0;
}
```

**Key features:**
- Simultaneous matching of thousands of patterns
- SIMD acceleration (SSE4.2 required, AVX2/AVX-512 recommended)
- Streaming mode for network packet inspection
- Subset of PCRE syntax (no backreferences, limited look-around)
- Designed for throughput, not single-match latency
- Logical combinations and extended parameter support

**When to use Hyperscan:** Network intrusion detection/prevention (IDS/IPS), deep packet inspection, log analysis at scale, real-time data stream filtering, and any scenario where you need to match hundreds or thousands of patterns against high-throughput data.

## Oniguruma: The Polyglot Regex Engine

[Oniguruma](https://github.com/kkos/oniguruma) is the regex engine that powers Ruby (both CRuby and JRuby), PHP's `mb_ereg` functions, and TextMate/Sublime Text syntax highlighting. It's known for its extensive encoding support and rich feature set.

```c
#include <oniguruma.h>
#include <stdio.h>

int main() {
    OnigRegex regex;
    OnigRegion *region;
    int r;

    // Initialize with UTF-8 encoding
    OnigEncoding encodings[] = {ONIG_ENCODING_UTF8};
    onig_initialize(encodings, 1);

    const UChar *pattern = (const UChar*)"(?<year>\d{4})-(?<month>\d{2})";
    const UChar *str = (const UChar*)"2026-06-22";

    OnigErrorInfo einfo;
    r = onig_new(&regex, pattern,
                 pattern + strlen((const char*)pattern),
                 ONIG_OPTION_DEFAULT,
                 ONIG_ENCODING_UTF8,
                 ONIG_SYNTAX_DEFAULT,
                 &einfo);

    if (r != ONIG_NORMAL) {
        OnigUChar s[ONIG_MAX_ERROR_MESSAGE_LEN];
        onig_error_code_to_str(s, r, &einfo);
        fprintf(stderr, "Error: %s\n", s);
        return 1;
    }

    region = onig_region_new();
    r = onig_search(regex, str,
                    str + strlen((const char*)str),
                    str,
                    str + strlen((const char*)str),
                    region, ONIG_OPTION_NONE);

    if (r >= 0) {
        printf("Match at position %d, length %ld\n", r,
               region->end[0] - region->beg[0]);

        // Named groups via onig_name_to_backref_number()
        int year_idx = onig_name_to_backref_number(
            regex, (const UChar*)"year", (const UChar*)"year" + 4, region);
        printf("Named group 'year': %d\n", year_idx);
    }

    onig_region_free(region, 1);
    onig_free(regex);
    onig_end();
    return 0;
}
```

**Key features:**
- 20+ character encodings (UTF-8, UTF-16, EUC-JP, Shift_JIS, GB 18030, etc.)
- Named groups, backreferences, look-ahead, look-behind
- Subexpressions and conditional patterns
- Callback-based match iteration
- Used by Ruby, PHP, Atom, TextMate, jq

**When to use Oniguruma:** Multi-encoding text processing, syntax highlighting engines, Ruby or PHP ecosystems, any application needing broad character encoding support with comprehensive regex features.

## Performance Characteristics

Performance varies dramatically based on pattern complexity and input size. Here's a qualitative comparison:

| Scenario | Best Performer | Reason |
|----------|---------------|--------|
| Single pattern, simple input | PCRE2 (JIT) | JIT compilation optimizes for the specific pattern |
| Thousands of patterns, streaming | Hyperscan | SIMD parallelism handles bulk matching |
| User-supplied patterns (safety) | RE2 | Linear-time guarantee prevents ReDoS |
| Unicode-heavy, multi-encoding | Oniguruma | Native support for 20+ encodings |
| Complex backtracking patterns | PCRE2 | Full feature set with JIT speed |

**Benchmark insight:** For typical server workloads (single pattern, 10KB input), PCRE2-JIT is typically 2-5x faster than RE2. However, RE2's linear-time guarantee makes it the safe default: PCRE2 can become 100x slower on pathological patterns like `(a+)+b` against input `aaaaaaaaac`, while RE2 maintains consistent performance.

## Choosing Your Regex Engine

- **Server applications accepting user patterns** → **RE2** (safety first)
- **Network security, IDS/IPS, log scanning at scale** → **Hyperscan**
- **Full regex features with JIT speed** → **PCRE2**
- **Ruby/PHP integration, multi-encoding support** → **Oniguruma**

## Why Choosing the Right Regex Engine Matters

The regex engine you choose directly impacts your application's security, performance, and reliability. Here's why this decision deserves careful consideration:

**ReDoS Prevention Is a Security Requirement.** Regular Expression Denial of Service attacks exploit backtracking engines with carefully crafted patterns and inputs that cause exponential matching time. In 2019, Cloudflare experienced a global outage caused by a single catastrophic backtracking regex in their WAF. RE2 fundamentally prevents this class of vulnerability — a guarantee that no amount of pattern review or input sanitization can provide with backtracking engines.

**Throughput Determines Operational Cost.** For log analysis platforms processing terabytes per day, the difference between Hyperscan's SIMD-accelerated matching (500+ MB/s) and a naive regex loop (5-10 MB/s) translates directly to infrastructure costs. One Hyperscan-enabled server can replace 50 servers running conventional regex, cutting hardware, power, and cooling expenses proportionally.

**Encoding Bugs Are Silent Data Corruption.** Oniguruma's multi-encoding support isn't a luxury feature — it prevents silent failures when processing international text. A regex engine that assumes ASCII on Japanese-language input will silently skip matches, drop data, or produce incorrect results. For global-scale applications, proper encoding handling is not optional.

**Library Selection Outlives Initial Development.** Regex engines are deeply embedded in application code — migrating from PCRE2 to RE2 after launch means rewriting every regex pattern to avoid unsupported features (backreferences, look-around). Making the right choice at architecture time avoids a multi-month migration project down the road.

For related text processing infrastructure, see our [JSON parser libraries comparison](../2026-06-19-self-hosted-json-parser-libraries-simdjson-rapidjson-orjson-ultrajson/) covering structured data parsing. For broader parsing and tokenization tools, our [parser generator guide](../2026-06-20-parser-generator-combinator-libraries-antlr-treesitter-nom-pest-nearley/) covers grammar-based approaches. For search infrastructure that builds on pattern matching, see our [code search tools comparison](../2026-06-16-code-search-tools-ripgrep-ag-silver-searcher-ugrep/).

## FAQ

### Why doesn't RE2 support backreferences?

Backreferences make regular expression matching NP-complete — in the worst case, matching requires exponential time. RE2 was specifically designed to guarantee linear-time matching, which is only possible with regular languages (those representable as finite automata). Backreferences go beyond regular languages into context-free territory. The trade-off is deliberate: you give up specific advanced features in exchange for the guarantee that no input, no matter how pathological, will cause catastrophic slowdown.

### Can I use Hyperscan as a drop-in replacement for PCRE2?

No. Hyperscan implements a subset of PCRE syntax and has different APIs. It's designed for matching many patterns against streaming data, not for single-pattern, feature-rich matching. Hyperscan also requires SSE4.2 or newer x86 hardware — it won't work on ARM processors (though an ARM port is in development as of 2026). If you need PCRE compatibility, stick with PCRE2-JIT for performance.

### Is Oniguruma thread-safe?

No — Oniguruma uses global state for encoding tables and must be initialized once at process startup. Individual compiled regex objects (`regex_t`) can be used from multiple threads if properly synchronized, but the library itself is not inherently thread-safe. For multi-threaded server applications, RE2 is the better choice. Oniguruma's typical use case is in language runtimes (Ruby, PHP) where the interpreter handles thread safety.

### How do I choose between RE2 and std::regex?

Avoid `std::regex`. Despite being in the C++ standard, `std::regex` implementations vary dramatically in quality — GCC's implementation is notoriously slow (often 10-50x slower than RE2), and MSVC's has correctness issues with Unicode. RE2 is faster, safer, and more consistent across platforms. The C++ standards committee has acknowledged these issues, and proposals exist to add a better regex library to a future standard, but for now, RE2 is the de facto standard for C++ regex.

### Does Hyperscan work for small-scale applications?

Hyperscan's overhead (SIMD initialization, scratch space allocation, pattern compilation) makes it unsuitable for occasional pattern matching on small inputs. The library is optimized for matching hundreds or thousands of patterns against multi-kilobyte or larger buffers. For a typical web application validating user input against one or two patterns, RE2 or PCRE2-JIT will be faster and simpler.

### What about Boost.Regex?

Boost.Regex was the basis for `std::regex` and shares its fundamental design (backtracking NFA with optional recursion). It supports more features than `std::regex` (named captures, partial match, Unicode character classes) and is well-tested, but it still uses backtracking and is subject to ReDoS. For new projects, RE2 or PCRE2 are better choices. Boost.Regex remains relevant primarily for maintaining codebases that already use it.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Regular Expression Engine Libraries Compared: RE2 vs PCRE2 vs Hyperscan vs Oniguruma",
  "description": "Comparison of four regex engine libraries — RE2 (linear-time safety), Hyperscan (SIMD-accelerated throughput), PCRE2 (full-featured JIT), and Oniguruma (multi-encoding — for high-performance pattern matching in C/C++ applications.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)