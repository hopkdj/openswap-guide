---
title: "Self-Hosted Shell Script Linting: ShellCheck vs shfmt vs bashate"
date: "2026-06-17"
tags: ["shell-scripting", "linting", "code-quality", "dev-tools", "bash", "shellcheck", "shfmt"]
draft: false
---

Shell scripts power everything from CI/CD pipelines to server provisioning. A single unquoted variable or missing error check can turn a maintenance script into a production outage. Shell linting and formatting tools catch these issues before they reach production — and they're essential for any team that writes or maintains shell scripts.

This guide compares three open-source shell script quality tools: **ShellCheck** (static analysis with 39,000+ GitHub stars), **shfmt** (formatting and syntax checking with 8,800+ stars), and **bashate** (style enforcement from OpenStack's ecosystem). While each addresses shell script quality, they serve different roles in a development workflow.

## Why Shell Script Linting Matters

Shell scripts are deceptively dangerous. Unlike compiled languages that catch errors at build time, shell scripts can silently fail or produce unexpected results due to subtle syntax issues. Consider these common pitfalls:

```bash
# WRONG: Unquoted variable breaks on filenames with spaces
rm -rf $TEMP_DIR/$filename

# WRONG: Missing error handling on critical operations
cd /important/directory
rm -rf *

# WRONG: `[` vs `[[` — different parsing rules
if [ $a == $b ]  # breaks if $a or $b is empty
```

ShellCheck catches all three of these patterns automatically. Adding a linter to your shell scripting workflow is one of the highest-ROI quality investments a DevOps team can make — ShellCheck alone has prevented countless production incidents since its release in 2012.

For related reading, see our [Shell Customization Frameworks comparison](../2026-06-17-self-hosted-shell-customization-frameworks-ohmyzsh-starship-bashit/) and our [Dotfile Management guide](../2026-06-16-self-hosted-dotfile-management-chezmoi-yadm-homeshick/). For terminal-based development workflows, check our [Terminal Multiplexer comparison](../self-hosted-terminal-multiplexer-tmux-screen-abduco-remote-dev-guide-2026/).

## Tool Comparison

| Feature | ShellCheck | shfmt | bashate |
|---------|-----------|-------|---------|
| **Primary function** | Static analysis & bug detection | Formatting & syntax parsing | Style enforcement |
| **Language** | Haskell | Go | Python |
| **GitHub Stars** | 39,573 | 8,824 | 394 |
| **Last updated** | June 2026 | June 2026 | November 2024 |
| **Install method** | Package manager / prebuilt binary | `go install` / binary | `pip install` |
| **CI integration** | Native GitHub Action, pre-commit | pre-commit hook | pre-commit, Tox |
| **Editor support** | VSCode, Vim, Emacs, JetBrains | VSCode, Vim, Emacs | VSCode, Vim |
| **Shell support** | bash, sh, dash, ksh | bash, zsh, mksh | bash only |
| **Checks included** | 450+ rules | Syntax + formatting | 38 style rules |
| **Configurability** | `.shellcheckrc` directives | `.editorconfig` flags | `.bashaterc` ignore rules |
| **Output formats** | tty, gcc, checkstyle, json | diff, compact | stdout, pep8-style |

## ShellCheck: The Bug Hunter

ShellCheck is the gold standard for shell script analysis, with over 450 individual checks covering everything from quoting errors to security vulnerabilities. It uses Haskell's powerful pattern matching to perform deep semantic analysis that goes far beyond simple regex-based linting.

**Installation:**

```bash
# Ubuntu/Debian
apt install shellcheck

# macOS
brew install shellcheck

# Via pre-commit
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.10.0
    hooks:
      - id: shellcheck
```

**Key capability — deep semantic analysis:**

```bash
#!/bin/bash
# ShellCheck catches issues that simpler tools miss:
# SC2086: Double quote to prevent globbing and word splitting.
echo $1

# SC2068: Double quote array expansions to avoid re-splitting elements.
for i in ${arr[*]}; do echo "$i"; done

# SC2164: Use 'cd ... || exit' or 'cd ... || return' in case cd fails.
cd /some/directory
rm -rf ./*
```

ShellCheck uses dataflow analysis to track how variables are used across functions, detecting issues like uninitialized variables, unused assignments, and command injection vulnerabilities. It's designed to catch the bugs that cause real outages — not just enforce style preferences.

**Running ShellCheck:**

```bash
# Check a single file
shellcheck deploy.sh

# Check all shell scripts in a directory
find . -name "*.sh" -exec shellcheck {} +

# JSON output for CI integration
shellcheck -f json script.sh

# Suppress specific checks with inline comments
shellcheck -e SC1091 script.sh  # ignore missing source warnings
```

For CI/CD pipelines, ShellCheck provides a zero-config GitHub Action that runs on every pull request. Combined with pre-commit hooks, it ensures no shell script with detectable bugs reaches production. The project is actively maintained with commits as recent as June 2026.

## shfmt: The Formatter and Parser

shfmt (from the `mvdan/sh` project) takes a different approach — it formats shell scripts to a consistent style and validates syntax, making it the ideal complement to ShellCheck's semantic analysis. Where ShellCheck asks "does this script have bugs?", shfmt asks "is this script syntactically valid and consistently formatted?"

**Installation:**

```bash
# Go install
go install mvdan.cc/sh/v3/cmd/shfmt@latest

# macOS
brew install shfmt

# Download prebuilt binary
curl -L -o shfmt https://github.com/mvdan/sh/releases/latest/download/shfmt_linux_amd64
chmod +x shfmt
```

**Key features:**

```bash
# Format with default settings (tabs, 0 indent)
shfmt -w script.sh

# Use spaces instead of tabs (2-space indent)
shfmt -i 2 -w script.sh

# Simplify redundant constructs
shfmt -s script.sh

# Find syntax errors without modifying files
shfmt -f script.sh  # returns non-zero exit if invalid

# List files that would be changed
shfmt -l script.sh

# Diff mode to see what would change
shfmt -d script.sh
```

The `-s` (simplify) flag is particularly valuable — it automatically converts `$()` to backticks where appropriate, removes unnecessary quoting, and reduces `$((expression))` to simpler forms. Combined with the `-mn` (minify) option, shfmt can produce the smallest valid equivalent of any shell script.

**EditorConfig integration:**

```ini
# .editorconfig
[*.sh]
indent_style = space
indent_size = 2
shell_variant = bash
binary_next_line = true
switch_case_indent = true
space_redirects = true
keep_padding = false
```

shfmt respects `.editorconfig` files, making team-wide formatting standards trivially enforceable. The formatter handles edge cases that trip up simpler tools — here documents with complex quoting, nested command substitutions, and multi-line array declarations all format correctly.

## bashate: The Style Enforcer

bashate comes from the OpenStack project, where it enforces a specific set of 38 style rules across thousands of shell scripts maintained by hundreds of contributors. While less feature-rich than ShellCheck or shfmt, it fills a specific niche: enforcing a team's coding style standard with minimal configuration.

**Installation:**

```bash
pip install bashate
```

**Key rules enforced:**

| Rule | Description | Example violation |
|------|-------------|-------------------|
| E001 | Check trailing whitespace | `echo "hello"   ` |
| E002 | Tab indentation | Tab characters in indentation |
| E003 | Indent not multiple of 4 | 2-space or 3-space indents |
| E010 | `do` not on same line as `for` | `for i in *; do` |
| E011 | `then` not on same line as `if` | `if [ -f file ]; then` |
| E020 | Function declaration format | Missing `function` keyword |
| E040 | Syntax error detection | Any bash syntax error |
| E041 | Arithmetic error detection | `$(())` without proper operators |
| E043 | Arithmetic using `$` prefix | `$(( $a + 1 ))` vs `$(( a + 1 ))` |

**Usage:**

```bash
# Check a single file
bashate script.sh

# Check a directory recursively
bashate scripts/

# Ignore specific rules
bashate -i E001,E002 script.sh

# Show error codes
bashate -v script.sh

# Output in pep8 format
bashate --format pep8 script.sh
```

bashate's strength is its simplicity — 38 rules that are easy to understand and enforce. For teams that want a lightweight style checker without the overhead of ShellCheck's 450+ rules or shfmt's aggressive reformatting, bashate hits a sweet spot. It's also the only tool of the three specifically designed for CI/CD pipeline integration with Tox.

## Setting Up a Complete Shell Quality Pipeline

The three tools work best together, each handling a different aspect of shell script quality:

```yaml
# .pre-commit-config.yaml — combined shell quality pipeline
repos:
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.10.0
    hooks:
      - id: shellcheck
        args: ["--severity=warning"]

  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.8.0-1
    hooks:
      - id: shfmt
        args: ["-i", "2", "-ci", "-s", "-w"]

  - repo: https://github.com/openstack/bashate
    rev: 2.1.1
    hooks:
      - id: bashate
        args: ["--ignore", "E001,E003"]
```

**CI/CD pipeline integration (GitHub Actions):**

```yaml
# .github/workflows/shell-lint.yml
name: Shell Script Linting
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ShellCheck
        uses: ludeeus/action-shellcheck@master
      - name: Run shfmt
        run: |
          go install mvdan.cc/sh/v3/cmd/shfmt@latest
          shfmt -d .
      - name: Run bashate
        run: |
          pip install bashate
          bashate scripts/
```

## Choosing the Right Tool

Every team writing shell scripts should use at least one of these tools. The optimal setup depends on your team's priorities:

- **Start with ShellCheck** if you want maximum bug detection. Its 450+ rules catch the issues that cause real production problems, and the zero-config defaults work well for most teams.
- **Add shfmt** when you want consistent formatting across a team. The EditorConfig integration makes it trivial to enforce a shared style, and the syntax validation catches errors that ShellCheck might not flag.
- **Use bashate** for lightweight style enforcement in OpenStack-adjacent projects, or as a complement to ShellCheck when you want separate tools for bugs vs. style.

For maximum coverage, run all three in your pre-commit hooks as shown above. ShellCheck catches the bugs, shfmt enforces the formatting, and bashate provides the extra style guardrails.

## FAQ

### Do I really need all three tools?

No — ShellCheck alone provides excellent coverage for most teams. Add shfmt if you care about consistent formatting (especially across multiple contributors), and add bashate if you work in the OpenStack ecosystem or want a lightweight second opinion on style. The three tools complement rather than duplicate each other.

### Can ShellCheck handle POSIX sh scripts, or is it bash-only?

ShellCheck supports bash, sh, dash, ksh, and POSIX sh. Use the `-s` flag to specify the shell dialect: `shellcheck -s sh script.sh`. You can also add a `# shellcheck shell=sh` directive at the top of your script. ShellCheck automatically detects the shebang line and adjusts its rule set accordingly.

### What's the difference between `shellcheck -e` and inline directives?

`shellcheck -e SC2086` suppresses a rule globally for the entire run, while inline directives like `# shellcheck disable=SC2086` suppress the rule for a specific line. Use inline directives when the rule is a false positive on one line but valid elsewhere. Use `-e` only when you want to permanently disable a check you disagree with.

### Does shfmt change the behavior of my scripts?

No — shfmt only reformats syntax and simplifies constructs (with `-s`). It produces semantically equivalent output. All behavior is preserved, including edge cases like here-document whitespace, command grouping, and subshell semantics. The `-d` (diff) mode lets you preview changes before applying them.

### Can I use these tools without installing them locally?

Yes — all three are available as pre-commit hooks that run automatically on `git commit`. ShellCheck also offers a web interface at shellcheck.net for quick one-off checks. For CI/CD, GitHub Actions marketplace has verified actions for all three tools.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Shell Script Linting: ShellCheck vs shfmt vs bashate",
  "description": "Comprehensive comparison of ShellCheck, shfmt, and bashate for shell script linting, formatting, and code quality — with CI/CD integration patterns and pre-commit configurations.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  },
  "about": {
    "@type": "SoftwareApplication",
    "name": "ShellCheck",
    "applicationCategory": "DeveloperApplication",
    "url": "https://www.shellcheck.net/"
  }
}
</script>
