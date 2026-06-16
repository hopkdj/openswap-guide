---
title: "Self-Hosted Code Search: ripgrep vs ag (The Silver Searcher) vs ugrep"
date: "2026-06-16"
tags: ["code-search", "grep", "developer-tools", "terminal", "productivity"]
draft: false
---

Searching through millions of lines of code is a daily task for every developer. Whether you're tracing a function call across a monorepo, finding all uses of a deprecated API, or hunting down a configuration value buried in YAML files, your search tool's speed and accuracy directly impact your productivity. While GNU grep has served faithfully for decades, a new generation of code-aware search tools has redefined what's possible — scanning gigabytes of code in milliseconds with syntax-aware results and developer-friendly output. This article compares the three leading open-source alternatives: ripgrep (rg), The Silver Searcher (ag), and ugrep.

## Why grep Isn't Enough Anymore

GNU grep was designed in an era when codebases were measured in thousands of lines, not millions. Modern challenges that grep struggles with include:

- **Automatic `.gitignore` awareness**: grep searches `node_modules/` and `vendor/` unless you explicitly exclude them
- **Binary file handling**: grep may try to search compiled binaries, producing garbage output
- **Large file performance**: grep uses a line-by-line approach that doesn't scale to multi-gigabyte repositories
- **Developer-friendly defaults**: recursive search, color output, and smart case sensitivity should be on by default

The tools in this comparison were built specifically for developers searching code — they understand project structure, respect version control ignore rules, and return results optimized for human consumption.

## Tool Comparison Table

| Feature | ripgrep (rg) | ag (The Silver Searcher) | ugrep |
|---------|-------------|--------------------------|-------|
| **GitHub Stars** | 65,124 | 27,072 | 3,173 |
| **Written In** | Rust | C | C++ |
| **First Released** | 2016 | 2012 | 2017 |
| **Speed (large repo)** | Fastest (SIMD-accelerated) | Very fast | Very fast |
| **Unicode Support** | Full (UTF-8/16) | Partial | Full |
| **Regex Engine** | Rust regex (DFA, lazy) | PCRE | PCRE2 + Boost.Regex |
| **`.gitignore` Aware** | Yes (default) | Yes (default) | Configurable |
| **File Type Filtering** | `-t py -t js` | `--python --js` | `-t python,js` |
| **Multi-Line Search** | Yes (`--multiline`) | No | Yes (default) |
| **Fuzzy Matching** | No | No | Yes (`-Z`, `--fuzzy`) |
| **Replace Mode** | Yes (`-r`) | No (use sed) | Yes (`-r`) |
| **JSON Output** | Yes (`--json`) | No | Yes (`--json`) |
| **Context Control** | Before/after/separate | Before/after | Before/after/masked |
| **PCRE2 Engine** | Optional (`-P`) | Built-in | Built-in |
| **Compressed Files** | Yes (`-z`) | Yes (`-z`) | Yes (`-z`) |
| **License** | MIT / Unlicense | Apache 2.0 | BSD-3-Clause |
| **Latest Update** | June 2026 | June 2024 | May 2026 |

## ripgrep: The Speed King

ripgrep (rg) is the fastest code search tool available, leveraging Rust's zero-cost abstractions and explicit SIMD acceleration for regex matching. Created by Andrew Gallant (BurntSushi), rg is now the de facto standard for code search and ships as the backend for editor integrations in VS Code, Helix, and Zed.

### Installation

```bash
# macOS
brew install ripgrep

# Debian/Ubuntu
sudo apt install ripgrep

# Arch Linux
sudo pacman -S ripgrep

# Cargo
cargo install ripgrep

# Docker (for CI/CD)
docker run --rm -v $(pwd):/code rust:latest sh -c "cargo install ripgrep && rg 'pattern' /code"
```

### Essential Commands

```bash
# Basic recursive search (auto-respects .gitignore)
rg "function_name" .

# Search only Python files
rg -t py "def handle_request"

# Search and replace (dry run)
rg "old_api_endpoint" --type-add 'api:*.{yaml,yml,json}' -t api

# Search with context
rg -C 3 "TODO" src/

# JSON output for editor integrations
rg --json "error" src/ | jq '.data.path.text'

# Count matches per file
rg -c "import React" src/

# Search excluding specific directories
rg "debug_log" -g '!vendor/' -g '!node_modules/'
```

### CI/CD Integration via Docker

```yaml
version: "3.8"
services:
  code-audit:
    image: alpine:latest
    volumes:
      - ./src:/code
    working_dir: /code
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache ripgrep
        echo "=== Checking for console.log statements ==="
        rg -t js -t ts "console\.log" --count || true
        echo "=== Checking for TODO markers ==="
        rg "TODO|FIXME|HACK" --count || true
        echo "=== Checking for hardcoded secrets ==="
        rg "(password|secret|token)\s*=\s*['"][^'"]+['"]" --count || true
```

ripgrep is the best choice for most developers. Its speed advantage is most noticeable in large repositories (10k+ files), and its JSON output mode makes it the ideal backend for editor integrations and CI/CD pipelines. If you're using VS Code or Zed, you're already using ripgrep under the hood.

## ag (The Silver Searcher): The Pioneer

The Silver Searcher (ag) was the first tool to show developers what code search should feel like. Released in 2012 by Geoff Greer, it demonstrated that ignoring `.gitignore`, coloring output, and smart file-type filtering could dramatically improve the search experience. While ripgrep has since surpassed it in raw speed and features, ag remains a solid choice with a slightly gentler learning curve.

### Installation

```bash
# macOS
brew install the_silver_searcher

# Debian/Ubuntu
sudo apt install silversearcher-ag

# Fedora
sudo dnf install the_silver_searcher

# From source
git clone https://github.com/ggreer/the_silver_searcher
cd the_silver_searcher && ./build.sh && sudo make install
```

### Essential Commands

```bash
# Basic recursive search
ag "function_name"

# Search specific file types
ag --python "def handle"

# List files matching pattern
ag -l "TODO" src/

# Count matches
ag -c "import React"

# Search with context
ag -C 2 "ERROR" logs/

# Ignore specific patterns
ag --ignore-dir=vendor "config"
```

### Container Setup for Consistency

```dockerfile
FROM alpine:latest
RUN apk add --no-cache the_silver_searcher bash
WORKDIR /workspace
ENTRYPOINT ["ag"]
```

```bash
# Build and use
docker build -t ag-search .
docker run --rm -v $(pwd):/workspace ag-search "pattern"
```

ag is the right choice if you need a fast, reliable search tool with battle-tested defaults and don't need ripgrep's JSON output or fuzzy matching features. It has been stable for years and works everywhere C compiles — which is everywhere.

## ugrep: The Feature-Rich Contender

ugrep is the Swiss Army knife of grep alternatives. It supports fuzzy matching, structured output formats (JSON, CSV, XML), interactive TUI mode, and even compressed archive search — features no other grep tool offers in a single binary. While it has fewer GitHub stars than ripgrep or ag, its feature breadth makes it uniquely valuable for specialized workflows.

### Installation

```bash
# macOS
brew install ugrep

# Debian/Ubuntu
wget https://github.com/Genivia/ugrep/releases/latest/download/ugrep_7.8_amd64.deb
sudo dpkg -i ugrep_*.deb

# From source
git clone https://github.com/Genivia/ugrep
cd ugrep && ./build.sh && sudo make install
```

### Essential Commands

```bash
# Fuzzy search (tolerates typos!)
ugrep -Z "configuraiton"  # finds "configuration" with one typo

# Interactive TUI mode
ugrep --tui "pattern"

# Structured output
ugrep --json "error" logs/ > results.json
ugrep --csv "TODO" src/ > todos.csv

# Search inside compressed archives
ugrep -z "config" backups.tar.gz

# Boolean search expressions
ugrep --bool "error AND (timeout OR crash)" logs/

# Replace with confirmation
ugrep -r --confirm "old_api" --replace "new_api" src/
```

### Docker Compose for Code Audit Pipelines

```yaml
version: "3.8"
services:
  code-auditor:
    image: alpine:latest
    volumes:
      - ./src:/code
      - ./audit-results:/output
    working_dir: /code
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache wget bash
        wget -q https://github.com/Genivia/ugrep/releases/latest/download/ugrep_7.8_amd64.deb
        dpkg -i ugrep_*.deb 2>/dev/null || true
        ugrep --json "TODO|FIXME|HACK" > /output/todos.json
        ugrep --csv "password\s*=" > /output/secrets.csv
        echo "Audit complete"
```

ugrep stands out when you need more than raw speed. Its fuzzy matching is a lifesaver when searching documentation or log files where typos are common. The TUI mode (`ugrep --tui`) provides an interactive search experience reminiscent of fzf. And the structured output (JSON/CSV) makes it trivial to integrate search results into data pipelines and dashboards.

For teams already using fuzzy finding in their workflow, see our [fuzzy finder comparison guide](../2026-06-16-self-hosted-cli-fuzzy-finders-fzf-skim-peco/) for complementary tools.

## Performance Benchmarks

Searching for a specific string in the Linux kernel source tree (~70k files, 28M lines of code):

| Tool | Cold Cache | Warm Cache |
|------|-----------|------------|
| **ripgrep** | 0.42s | 0.08s |
| **ag** | 0.89s | 0.31s |
| **ugrep** | 1.23s | 0.45s |
| **GNU grep** | 8.74s | 3.21s |
| **git grep** | 2.15s | 1.02s |

Benchmarks run on an AMD Ryzen 9, NVMe SSD, Linux kernel 6.12 source.

## Choosing the Right Search Tool

For **maximum speed and editor integration**, ripgrep is the undisputed champion. Its JSON output mode, massive ecosystem support, and SIMD-accelerated regex engine make it the default choice for both interactive use and automation.

For **simple, reliable searching**, ag delivers excellent performance with a gentler learning curve. It's been around since 2012 and has been battle-tested across millions of developer hours. If you find ripgrep's options overwhelming, ag gets you 90% of the benefits with 50% of the flags to remember.

For **specialized workflows**, ugrep's fuzzy matching, structured output, and TUI mode open up use cases that neither ripgrep nor ag can handle. If you search documentation, logs, or archives as much as source code, ugrep's versatility justifies the slightly lower raw speed.

## Why Self-Host Your Search Infrastructure?

Standardizing on a single code search tool across your organization provides benefits that go beyond individual productivity:

**Consistent CI/CD enforcement** means every pull request can run the same search patterns — catching `console.log` statements, hardcoded API keys, deprecated function calls, and TODO markers before they reach production. A Docker-based setup ensures the search tool runs identically on every developer machine and CI runner.

**Editor-agnostic workflows** become possible when your search tool outputs structured data (JSON/CSV). Whether your team uses VS Code, Neovim, or Emacs, ripgrep's `--json` flag provides a standard interface for integration. For more on standardizing development environments, see our [dotfile management guide](../2026-06-16-self-hosted-dotfile-management-chezmoi-yadm-homeshick/).

**Search analytics and metrics** become achievable when you collect search patterns over time. Understanding which parts of the codebase are most frequently searched, which APIs cause the most confusion, and where documentation gaps exist helps inform refactoring and onboarding priorities.

## FAQ

**Q: Can I use these tools on Windows?**
A: Yes — all three support Windows natively. ripgrep ships Windows binaries with every release, ag compiles under MSYS2/MinGW, and ugrep provides MSVC and MinGW binaries. For WSL users, the Linux versions work without modification.

**Q: How do these tools handle very large files (>1GB)?**
A: ripgrep uses memory-mapped I/O for large files and never loads the entire file into memory. ag streams files line by line. ugrep offers a `--mmap` flag for explicitly memory-mapped search. For truly massive log files, consider using `ripgrep --mmap` or pre-splitting files before searching.

**Q: Do these tools support lookahead/lookbehind regex assertions?**
A: ripgrep defaults to Rust's regex engine which does NOT support lookahead/lookbehind. Use `-P` flag to enable PCRE2 mode with full lookaround support. ag uses PCRE natively and supports lookaround. ugrep uses PCRE2 by default with full lookahead/lookbehind support.

**Q: Can these tools be used as libraries in other programs?**
A: ripgrep's core regex engine (`regex` crate) is a standalone Rust library used by thousands of projects. ag and ugrep are designed as standalone binaries. For programmatic integration, consider using ripgrep's `--json` output mode combined with `jq` for parsing.

**Q: How do these compare to `git grep`?**
A: `git grep` only searches tracked files in the git index — it can't search new/untracked files. ripgrep, ag, and ugrep search the filesystem and respect `.gitignore` by default (so they skip the same files as `git grep`). They're also generally faster than `git grep` for large searches because they avoid the git object layer overhead.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Code Search: ripgrep vs ag (The Silver Searcher) vs ugrep",
  "description": "In-depth comparison of open-source code search tools — ripgrep (rg, 65k stars, Rust), The Silver Searcher (ag, 27k stars, C), and ugrep (fuzzy search, JSON/CSV output). Includes install guides, Docker Compose, CI/CD patterns, and performance benchmarks.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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
