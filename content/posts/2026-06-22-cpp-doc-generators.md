---
title: "C++ Documentation Generators: Doxygen vs Standardese vs hdoc vs moxygen"
date: "2026-06-22"
tags: ["c++", "documentation", "doxygen", "developer-tools", "cpp-libraries"]
draft: false
---

Generating API documentation from C++ source code has been dominated by Doxygen for over two decades. But modern alternatives like Standardese, hdoc, and moxygen offer C++-aware parsing, cleaner output, and better integration with contemporary documentation workflows. This guide compares four C++ documentation generators and helps you choose the right tool for your project.

## Why Modern C++ Documentation Tools Matter

Doxygen processes C++ source using a lexer-based approach that doesn't fully understand modern C++ features — template metaprogramming, concepts, constraints, and `requires` clauses are often mangled or ignored. Tools like Standardese and hdoc leverage **Clang's full AST parser** to extract semantically accurate documentation.

Choosing the right generator impacts:

- **Onboarding speed** — developers find answers faster with well-structured, searchable documentation
- **API discoverability** — modern generators expose template constraints and concept requirements
- **Integration** — Markdown, reStructuredText, and static site generator compatibility
- **Maintenance** — keeping docs in sync with code when the generator understands your C++ version

| Feature | Doxygen | Standardese | hdoc | moxygen |
|---------|---------|-------------|------|---------|
| **Stars** | 6,507 | 969 | 339 | 272 |
| **Parser** | Custom lexer | Clang AST (libclang) | Clang AST | Doxygen XML consumer |
| **C++20/23 Support** | Partial (via `CLANG_ASSISTED_PARSING`) | Full (Clang frontend) | Partial | Inherits from Doxygen |
| **Output Formats** | HTML, LaTeX, XML, RTF, Man | Markdown, HTML | HTML (React SPA) | Markdown |
| **Themes** | Built-in + custom CSS | Template-based | Modern SPA UI | N/A (Markdown) |
| **Language** | C++ | C++ | C++ | TypeScript |
| **Last Release** | 2026 | 2025 | 2024 | 2026 |
| **Integration** | CMake, Make, Sphinx | CMake, Sphinx | CMake, GitHub Actions | CMake, CI pipelines |
| **Search** | Server-side or JS | Built-in | Built-in | N/A (Markdown files) |

## Doxygen: The Industry Standard

Doxygen (6,507 stars, first released 1997) remains the most deployed C++ documentation generator. It processes a superset of C++ syntax using a custom lexer and generates documentation in HTML, LaTeX (PDF), RTF, XML, and man pages.

```bash
# Generate Doxygen config
doxygen -g Doxyfile

# Key Doxyfile settings for modern C++
# Doxyfile
EXTRACT_ALL          = YES
EXTRACT_PRIVATE      = YES
RECURSIVE            = YES
GENERATE_LATEX       = NO
USE_MDFILE_AS_MAINPAGE = README.md
CLANG_ASSISTED_PARSING = YES
CLANG_OPTIONS        = -std=c++20
```

```cpp
/**
 * @brief A thread-safe LRU cache with configurable eviction policy.
 * 
 * @tparam Key The key type (must be hashable and equality-comparable)
 * @tparam Value The value type (must be copy-constructible)
 * 
 * The cache uses a combination of std::unordered_map and std::list
 * for O(1) average insert, lookup, and eviction operations.
 * 
 * @code
 *   lru_cache<std::string, int> cache(1000);
 *   cache.put("key", 42);
 *   auto val = cache.get("key");  // std::optional<int>
 * @endcode
 */
template<typename Key, typename Value>
class lru_cache {
public:
    explicit lru_cache(size_t capacity);
    void put(const Key& key, const Value& value);
    std::optional<Value> get(const Key& key);
};
```

**Doxygen strengths:** Massive ecosystem of plugins, themes (Doxygen Awesome, Doxygen Dark), Sphinx integration via Breathe, and extensive `@` command vocabulary. It "just works" for most C++ codebases.

**Doxygen limitations:** Custom parser struggles with C++20 concepts, `requires` clauses, and complex SFINAE patterns. The default HTML output looks dated (mitigated by themes). Cross-referencing between template specializations requires manual `@relates` annotations.

## Standardese: C++ Documentation for the Modern Era

Standardese (969 stars) is a "next-generation Doxygen" that uses **libclang** (Clang's C API) to parse C++ source with full semantic understanding. It generates Markdown-first output designed for static site generators.

```bash
# Install Standardese
# Option 1: Pre-built binary
wget https://github.com/standardese/standardese/releases/latest/download/standardese-linux
chmod +x standardese-linux

# Option 2: Build from source with CMake
git clone https://github.com/standardese/standardese.git
cd standardese && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Generate documentation
standardese --input.source_dir=include/ --output.dir=docs/
```

```cpp
/// A generic ring buffer with fixed capacity.
/// 
/// ## Thread Safety
/// This implementation is NOT thread-safe. Use `synchronized_ring_buffer`
/// for concurrent access.
/// 
/// ## Complexity
/// All operations are O(1).
template<typename T, size_t Capacity>
class ring_buffer {
public:
    /// Pushes an element, overwriting the oldest if full.
    /// @returns A reference to the overwritten element, or std::nullopt.
    auto push(T value) -> std::optional<T>;
    
    /// Pops the oldest element from the buffer.
    auto pop() -> std::optional<T>;
    
    /// Current number of elements in the buffer.
    [[nodiscard]] auto size() const -> size_t;
};
```

Standardese automatically extracts template constraints (`requires` clauses), `noexcept` specifications, and `[[attributes]]` — no manual annotation needed. The Markdown output integrates directly with **MkDocs, Docusaurus, Hugo, and VuePress**.

## hdoc: Modern UI for C++ Documentation

hdoc (339 stars) takes a different approach: it generates a **React-based single-page application** with full-text search, call graphs, and syntax-highlighted source views. It uses Clang's tooling infrastructure for parsing.

```yaml
# .hdoc.yaml — project configuration
project:
  name: "My C++ Library"
  version: "2.1.0"
  
input:
  include_patterns:
    - "include/**/*.hpp"
    - "include/**/*.h"
  
build:
  compile_commands: "build/compile_commands.json"
  
output:
  directory: "docs/hdoc"
  
site:
  logo: "docs/logo.svg"
  favicon: "docs/favicon.ico"
```

```bash
# Generate compile_commands.json (CMake)
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Run hdoc
hdoc --config .hdoc.yaml

# Output is a self-contained static site in docs/hdoc/
```

hdoc's UI features **instant full-text search**, interactive call and inheritance graphs, and dark/light theme support. The single-page application approach eliminates page reloads during navigation, making API exploration feel responsive.

## moxygen: Doxygen XML to Markdown Bridge

moxygen (272 stars) bridges the Doxygen ecosystem with Markdown-based static site generators. It consumes Doxygen's XML output and produces clean, hierarchical Markdown files.

```bash
# Step 1: Generate Doxygen XML
doxygen Doxyfile  # Ensure GENERATE_XML = YES

# Step 2: Convert XML to Markdown
npx moxygen xml/ --output docs/api/ --anchors

# Example output structure:
# docs/api/
#   README.md
#   namespace_myapp.md
#   class_myapp_ring_buffer.md
#   group_concurrency.md
```

```makefile
# Makefile integration
docs: doxygen
	moxygen xml/ --output docs/api/ --anchors
	@echo "Documentation generated in docs/api/"
```

moxygen is ideal for teams already invested in Doxygen who want to **migrate to a Markdown-based static site** without rewriting all their `@` documentation comments. It's also the lightest-weight option — just a single npm package with no build dependencies.

## Choosing the Right Documentation Generator

**Use Doxygen** if you need battle-tested reliability, LaTeX/PDF output, and access to the largest plugin ecosystem. It's the safest choice for large, established C++ codebases.

**Use Standardese** if you target C++17/20/23 with heavy template metaprogramming, concepts, or `requires` clauses. The Clang-based parser accurately captures modern C++ semantics that Doxygen's lexer mangles.

**Use hdoc** if you prioritize **developer experience** — instant search, interactive graphs, and a modern SPA UI. The tradeoff is a smaller community and less flexible output format.

**Use moxygen** as a bridge: keep your Doxygen `@` comments but publish via a Markdown static site generator like [MkDocs or Docusaurus](../mkdocs-vs-docusaurus-vs-vitepress-self-hosted-documentation-generators-2026/).

## Why Self-Host Your C++ Documentation Pipeline?

API documentation is the primary interface between library authors and consumers. A well-documented C++ library sees 3-5x higher adoption than an equivalent undocumented one — developers vote with their time, and they won't spend it deciphering header files.

Self-hosting your documentation pipeline (rather than relying on hosted services) gives you control over branding, search indexing, and accessibility. All four tools in this comparison produce **static HTML or Markdown** that can be served from GitHub Pages, Netlify, or any CDN — no server-side rendering required.

For teams building **API-first C++ libraries**, our [API documentation generators guide](../self-hosted-api-documentation-generators-swagger-redoc-rapidoc-scalar-guide/) covers REST API documentation patterns that complement your C++ reference docs. If you're generating documentation from **Markdown source files**, see our [Markdown parser libraries comparison](../2026-06-20-markdown-parser-libraries-pulldown-cmark-goldmark-comrak-commonmarkjs/).

## FAQ

### Can I use Doxygen with a modern HTML theme?

Yes — the **Doxygen Awesome** theme (1,500+ GitHub stars) provides a clean, responsive CSS rewrite with dark mode support. Simply drop `doxygen-awesome.css` into your `HTML_EXTRA_STYLESHEET` list. **Doxygen Dark** is another popular option with a VS Code-inspired design.

### Does Standardese require a compilation database?

Standardese works best with `compile_commands.json` (generated by CMake with `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`). Without it, you can specify include paths manually via `--input.include_dirs`, but template-heavy code may not parse correctly without the full compilation context.

### Is hdoc free for commercial use?

hdoc offers both a free community edition and paid tiers with advanced features (private documentation hosting, team collaboration). The core parsing engine is open source under MIT, while the hosted platform has commercial licensing.

### How does moxygen handle complex Doxygen commands?

moxygen preserves most Doxygen `@` commands as Markdown equivalents: `@code` becomes fenced code blocks, `@param` becomes bullet lists, `@see` becomes cross-reference links. It falls back to raw HTML for commands without a Markdown equivalent (`@image`, `@dot` graphs).

### Can I mix multiple tools in a single project?

Absolutely. A common pattern: use **Doxygen XML** as the shared parse format, feed it to **moxygen** for Markdown output AND **Breathe** for Sphinx integration. Standardese can run alongside Doxygen since both read source files independently.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Documentation Generators: Doxygen vs Standardese vs hdoc vs moxygen",
  "description": "Comprehensive comparison of C++ API documentation generators: Doxygen, Standardese, hdoc, and moxygen. Covers Clang-based parsing, modern C++20/23 support, Markdown output, and static site integration.",
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
