---
title: "C++ Code Formatting Tools: clang-format vs Uncrustify vs Astyle"
date: "2026-06-27"
tags: ["cpp", "code-formatting", "clang-format", "uncrustify", "astyle", "development-tools", "code-quality", "developer-libraries"]
draft: false
---

## Introduction

Consistent code formatting is one of the highest-leverage investments a development team can make — it eliminates bikeshedding over brace placement, reduces cognitive load during code review, and ensures every contributor produces code that looks like it belongs. For self-hosted C++ projects, automated formatting tools running in CI/CD pipelines enforce style rules mechanically, freeing developers to focus on logic rather than layout.

This guide compares three battle-tested C++ code formatters — **clang-format** (part of the LLVM project), **Uncrustify**, and **Artistic Style (Astyle)** — examining their configuration flexibility, IDE integration, supported style rules, and performance in self-hosted development workflows.

| Feature | clang-format | Uncrustify | Astyle |
|---------|-------------|------------|--------|
| **Repository** | Part of LLVM | `uncrustify/uncrustify` | SourceForge |
| **Language Support** | C, C++, Java, JS, ObjC, Proto | C, C++, C#, D, Java, ObjC, Pawn, Vala | C, C++, C#, Java |
| **Built-in Styles** | LLVM, Google, Chromium, Mozilla, WebKit, Microsoft, GNU | None (config-driven) | 15+ predefined styles |
| **Configuration Format** | YAML (`.clang-format`) | Custom DSL (`uncrustify.cfg`) | Command-line options |
| **Editor Integration** | Universal (VSCode, Vim, CLion, Emacs) | Via plugins | Via plugins |
| **GitHub Stars** | Part of LLVM (33,000+) | 3,053 | ~4,000 (SourceForge stats) |
| **License** | Apache 2.0 (LLVM) | GPL 2.0 | MIT |
| **Rule Count** | 100+ options | 600+ options | 50+ options |
| **CI Integration** | `clang-format-diff.py`, pre-commit | `uncrustify -c config -f` pipe | `astyle --options=none` |

## clang-format: The Industry Standard

clang-format is a powerful C++ code formatter built on top of the Clang/LLVM compiler infrastructure. Because it uses a real C++ parser (libFormat leverages Clang's tokenizer and AST), it understands the language at a semantic level — not just as text. This gives it superior accuracy for complex formatting rules.

**Key Features:**
- Full C++ language awareness (templates, lambdas, attributes, concepts)
- 7 built-in styles as starting points (LLVM, Google, Chromium, Mozilla, WebKit, Microsoft, GNU)
- YAML configuration with `BasedOnStyle` for easy customization
- `// clang-format off/on` comments for selective disabling
- Native integration with Git (`git-clang-format` for formatting only changed lines)
- Supports C++20 modules and concepts

**Basic configuration (`.clang-format`):**
```yaml
BasedOnStyle: Google
IndentWidth: 4
ColumnLimit: 100
AllowShortFunctionsOnASingleLine: Inline
BreakBeforeBraces: Allman
IncludeBlocks: Regroup
SortIncludes: true
PointerAlignment: Left
SpaceAfterCStyleCast: true
```

**Usage:**
```bash
# Format a single file
clang-format -i src/main.cpp

# Format all C++ files in a directory
find src/ -name "*.cpp" -o -name "*.h" | xargs clang-format -i

# Check formatting in CI (dry-run, exit code 1 if changes needed)
clang-format --dry-run --Werror src/main.cpp

# Format only changed lines in a git diff
git clang-format origin/main
```

**Docker Compose — CI formatting check:**
```yaml
version: "3.8"
services:
  format-check:
    image: silkeh/clang:18
    working_dir: /workspace
    volumes:
      - .:/workspace
    command: >
      bash -c "apt-get update && apt-get install -y python3 git &&
      find src/ -name '*.cpp' -o -name '*.h' | xargs clang-format --dry-run --Werror"
```

## Uncrustify: Maximum Configurability

Uncrustify is a source code beautifier with an astonishing 600+ configurable options — far more than any other C++ formatter. It supports 8 programming languages and provides microscopic control over every formatting decision. This extreme configurability makes it the tool of choice for projects with highly specific or legacy formatting requirements that no built-in style accommodates.

**Key Features:**
- 600+ configuration options covering every formatting aspect
- Supports 8 languages: C, C++, C#, D, Java, Objective-C, Pawn, Vala
- Token-level comment manipulation (align, indent, transform)
- Universal newline support (LF, CRLF, CR) and encoding handling
- Can add/remove spaces, newlines, and comments
- CI integration via pipe mode

**Basic configuration (`uncrustify.cfg`):**
```ini
# Indentation
indent_columns = 4
indent_with_tabs = 0
indent_class = true
indent_namespace = true

# Braces
nl_brace_brace = 0
nl_after_brace_open = true
nl_before_brace_close = true

# Spacing
sp_inside_paren = 0
sp_inside_fparen = 0
sp_before_sparen = 0

# Alignment
align_assign_span = 1
align_assign_thresh = 4

# Newlines
nl_max = 2
nl_after_func_proto = 1
```

**Usage:**
```bash
# Format a file
uncrustify -c uncrustify.cfg --replace src/main.cpp

# Format in CI (check mode)
uncrustify -c uncrustify.cfg --check src/main.cpp

# Format all C++ files and show diff
find src/ -name "*.cpp" -o -name "*.h" | while read f; do
    uncrustify -c uncrustify.cfg -f "$f" | diff "$f" -
done
```

## Astyle: The Lightweight Classic

Artistic Style (Astyle) is a veteran code formatter that's been in continuous development since 1998. It's lightweight, fast, and ships with 15+ predefined code styles. Astyle is often the default formatter in older C++ projects and embedded systems environments where LLVM's full toolchain isn't available.

**Key Features:**
- 15+ predefined code styles (ansi, java, kr, linux, gnu, stroustrup, etc.)
- Minimal dependencies — single binary, no runtime requirements
- Very fast processing (C-based implementation, no C++ parser overhead)
- Command-line only configuration (no config file by default)
- Simple integration with any editor or build system

**Usage:**
```bash
# Format with a built-in style
astyle --style=google src/main.cpp

# Format with custom options
astyle --style=allman --indent=spaces=4 --indent-namespaces \
       --pad-oper --pad-header --unpad-paren src/main.cpp

# Create backup files (safety net)
astyle --style=linux --suffix=.orig src/*.cpp

# Recursive format of a directory
astyle --style=google -r "src/*.cpp" "include/*.h"

# Dry-run to see what would change
astyle --style=google --dry-run src/main.cpp
```

**Installation on self-hosted infrastructure:**
```bash
# Ubuntu/Debian
apt-get install astyle

# Alpine / Docker
apk add astyle

# From source (embedded targets)
git clone https://git.code.sf.net/p/astyle/code astyle
cd astyle && cmake . && make && make install
```

## Choosing the Right Formatter

The choice depends on your project's needs:

- **clang-format** for modern C++ projects that want deep language understanding, excellent IDE integration, and a large community providing built-in styles. It's the safest default for new projects.
- **Uncrustify** for projects with highly specific or legacy formatting rules that no built-in style can replicate. Its 600+ options give you control over every whitespace decision — but that power comes with configuration complexity.
- **Astyle** for lightweight environments (embedded, older toolchains) where the LLVM toolchain isn't available, or for projects that want a fast, proven formatter with no configuration file overhead.

## Integration into CI/CD Pipelines

All three tools can be integrated into a self-hosted CI pipeline to enforce formatting automatically:

```bash
#!/bin/bash
# pre-commit-format-check.sh — reject commits with formatting violations

FORMATTER="clang-format"  # or uncrustify, astyle
FAILED=0

for file in $(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(cpp|h|hpp)$'); do
    if ! $FORMATTER --dry-run --Werror "$file" 2>/dev/null; then
        echo "❌ $file is not properly formatted"
        FAILED=1
    fi
done

if [ $FAILED -eq 1 ]; then
    echo ""
    echo "Run: find . -name '*.cpp' -o -name '*.h' | xargs $FORMATTER -i"
    exit 1
fi
echo "✅ All files properly formatted"
```

## Why Self-Host Code Formatting Infrastructure

Running formatting checks on your own CI infrastructure gives you complete control over style enforcement policies, version pinning, and performance. Cloud-based formatting services introduce latency and dependency risks — when your self-hosted CI pipeline owns the formatting step, every commit is validated locally and instantly.

For catching deeper issues beyond formatting, check our [C++ static code analysis guide](../2026-06-02-linux-static-code-analysis-cppcheck-clang-flawfinder-infer/) covering Cppcheck, Clang Analyzer, Flawfinder, and Facebook Infer.

For the full code quality pipeline, our [SonarQube vs Semgrep vs CodeQL comparison](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/) covers enterprise-grade static analysis platforms that complement formatters.

For verifying code correctness, see our [C++ unit testing frameworks guide](../2026-06-21-cpp-unit-testing-frameworks-catch2-doctest-gtest-boost-test/) covering Catch2, doctest, Google Test, and Boost.Test.

## FAQ

### 1. Can I use multiple formatters in the same project?

Not recommended. Different formatters can "fight" each other — clang-format might fix one thing that Uncrustify then changes back. Pick one formatter for enforcement and stick with it. If you need Uncrustify for legacy code and clang-format for new code, separate them into different directories with different CI checks.

### 2. What's the best way to introduce formatting to an existing large codebase?

Apply formatting in a single "big bang" commit to a separate branch, get team approval, then merge. Never mix formatting changes with logic changes in the same commit — it makes code review impossible. Use `git clang-format origin/main` to only format changed lines if you prefer incremental adoption.

### 3. Can clang-format handle C++20 features like concepts and coroutines?

Yes. Since clang-format uses Clang's actual parser, it understands new C++ language features as they're added to upstream Clang. C++20 modules, concepts, coroutines, and `requires` clauses are fully supported. Uncrustify and Astyle use tokenizers rather than full parsers, so they may struggle with new syntax until manually updated.

### 4. How do I share formatting configuration across multiple repositories?

For clang-format, place a `.clang-format` file at the repository root — it propagates to subdirectories automatically. For organization-wide consistency, use a shared config repository and symlink or copy the `.clang-format` into each project's CI pipeline. Uncrustify and Astyle require explicit config distribution.

### 5. Are these tools fast enough for pre-commit hooks?

Astyle is the fastest (~5ms per typical file). clang-format is moderate (~15ms per file due to parsing overhead). Uncrustify is comparable to clang-format. All three are fast enough for pre-commit hooks on typical codebases. For large monorepos, limit formatting to changed files only (`git diff --name-only`) and use background linting in CI.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Code Formatting Tools: clang-format vs Uncrustify vs Astyle",
  "description": "In-depth comparison of three C++ code formatters — clang-format, Uncrustify, and Astyle — covering configuration flexibility, IDE integration, CI/CD pipeline setup, and self-hosted enforcement strategies.",
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
    "@id": "https://hopkdj.github.io/openswap-guide/posts/2026-06-27-cpp-code-formatting-tools-clang-format-uncrustify-astyle/"
  }
}
</script>
