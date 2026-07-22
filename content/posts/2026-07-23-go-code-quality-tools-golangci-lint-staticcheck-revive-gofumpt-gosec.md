---
title: "Self-Hosted Go Code Quality Tools: golangci-lint vs staticcheck vs revive vs gofumpt vs gosec"
date: "2026-07-23"
tags: ["go", "golang", "code-quality", "linting", "static-analysis", "security", "devops"]
draft: false
---

## Introduction

Go's philosophy of simplicity extends to its tooling — `go fmt` ships with the compiler and settles formatting debates permanently. But format consistency is just the first layer of code quality. Modern Go projects need static analysis to catch bugs, security scanning to prevent vulnerabilities, and style enforcement to maintain readability across teams.

The Go ecosystem has responded with a rich set of code quality tools that go far beyond the standard library. golangci-lint bundles dozens of linters into a unified runner. staticcheck provides deep static analysis that catches correctness issues missed by the compiler. revive offers a highly configurable, extensible linting framework. gofumpt enforces a stricter, more opinionated formatting standard. And gosec scans for common security vulnerabilities in Go source code.

In this guide, we compare these five tools, show how to integrate them into development workflows, and provide configuration examples for teams of all sizes.

## Tool Comparison

| Feature | golangci-lint | staticcheck | revive | gofumpt | gosec |
|---------|---------------|-------------|--------|---------|-------|
| **Type** | Linter aggregator | Static analyzer | Linter framework | Formatter | Security scanner |
| **Stars** | ~16,000 | ~7,000 | ~5,000 | ~3,000 | ~8,000 |
| **Linters/Checks** | 50+ bundled | 150+ checks | 80+ rules | N/A (formatter) | 30+ rules |
| **Configuration** | YAML (.golangci.yml) | Config file (optional) | TOML (revive.toml) | CLI flags | CLI flags + config |
| **Performance** | Fast (parallel) | Fast (~2s/project) | Fast | Very fast | Moderate |
| **Auto-fix** | Via --fix flag | Some auto-fixes | No | Yes (always) | No |
| **CI Integration** | GitHub Actions, GitLab CI | GitHub Actions | GitHub Actions | Pre-commit hook | GitHub Actions |
| **Custom Rules** | Via plugins | No | Yes (custom rules) | No | Via custom rules |
| **IDE Support** | VS Code, GoLand | VS Code, GoLand | VS Code, GoLand | Built into Go toolchain | VS Code, GoLand |

## golangci-lint: The Unified Linter Runner

golangci-lint integrates over 50 linters — including staticcheck, gosec, revive, errcheck, and govet — behind a single command. It runs linters in parallel, caches results, and provides a unified output format.

```bash
# Install via Go
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Run all linters
golangci-lint run ./...

# Run with auto-fix
golangci-lint run --fix ./...

# Generate recommended config
golangci-lint config path
```

```yaml
# .golangci.yml — production-grade configuration
run:
  timeout: 5m
  tests: true
  modules-download-mode: readonly

linters:
  enable:
    - errcheck       # Check unchecked errors
    - gosimple       # Simplify code suggestions
    - govet          # Go vet checks
    - ineffassign    # Detect ineffectual assignments
    - staticcheck    # Deep static analysis
    - unused         # Find unused code
    - gosec          # Security checks
    - revive         # Style and linting
    - gofumpt        # Stricter formatting
    - gocognit       # Cognitive complexity
    - gocyclo        # Cyclomatic complexity
    - dupl           # Code duplication
    - goconst        # Repeated strings to const
    - nakedret       # Naked returns in long funcs
    - prealloc       # Slice preallocation hints

linters-settings:
  gocognit:
    min-complexity: 15
  gocyclo:
    min-complexity: 12
  dupl:
    threshold: 200
  revive:
    rules:
      - name: exported
        severity: warning
        arguments:
          - checkPrivateReceivers: true
      - name: context-as-argument
        severity: warning

issues:
  exclude-rules:
    - path: _test\.go
      linters:
        - gocyclo
        - dupl
        - gosec
    - path: internal/mocks/
      linters:
        - all
  max-issues-per-linter: 0
  max-same-issues: 3
```

golangci-lint's key advantage is running all linters in a **single pass**. Without it, you'd run staticcheck, gosec, revive, errcheck, and go vet separately — each parsing the AST independently. By sharing the AST across linters, golangci-lint reduces total analysis time by 60-70% compared to sequential execution.

## staticcheck: Deep Static Analysis

staticcheck (package `honnef.co/go/tools`) performs sophisticated static analysis that catches bugs the Go compiler cannot detect. It's maintained by Dominik Honnef and is the most thorough static analyzer in the Go ecosystem.

```bash
go install honnef.co/go/tools/cmd/staticcheck@latest
staticcheck ./...
```

```go
// Examples of issues staticcheck catches

// SA4000: identical expressions on both sides of binary operator
func isZero(x int) bool {
    return x == x // always true — bug!
}

// SA1019: using deprecated function
import "golang.org/x/crypto/ssh/terminal"
func readPassword() (string, error) {
    return terminal.ReadPassword(0) // deprecated, use terminal.ReadPassword(int(os.Stdin.Fd()))
}

// SA4006: variable never used after assignment
func processUsers(ids []int) []User {
    users := fetchUsers(ids)
    users = filterActive(users)
    return nil // users assigned but returned nil — likely bug
}

// SA1025: time.Tick leaks if not stopped
func monitor() {
    for range time.Tick(time.Second) { // leaks — use time.NewTicker
        checkHealth()
    }
}

// S1009: omit redundant nil check on slice
func getNames(users []User) []string {
    if users != nil && len(users) > 0 { // redundant: len(nil) == 0
        // ...
    }
    return nil
}
```

staticcheck's checks are organized into categories: **SA** (static analysis, correctness), **S** (simplifications), **ST** (style), and **QF** (quick fixes). The SA checks are the most valuable — they detect nil pointer dereferences, infinite recursion, time.Tick leaks, mutex copy issues, and incorrectly formatted struct tags. At ~7,000 stars, staticcheck is widely trusted; it's included in golangci-lint's default enabled linters.

## revive: Extensible Linting

revive is a drop-in replacement for golint that adds speed, extensibility, and configurability. Each rule is a standalone Go package, making it trivial to write custom rules for your organization's conventions.

```bash
go install github.com/mgechev/revive@latest
revive -config revive.toml ./...
```

```toml
# revive.toml
ignoreGeneratedHeader = false
severity = "warning"
confidence = 0.8
errorCode = 0
warningCode = 0

[rule.atomic]
[rule.blank-imports]
[rule.bool-literal-in-expr]
[rule.call-to-gc]
[rule.confusing-naming]
[rule.confusing-results]
[rule.constant-logical-expr]
[rule.context-as-argument]
    arguments = [{ allowTypesBefore = "testing.T,context.Context,testing.F" }]
[rule.context-keys-type]
[rule.cyclomatic]
    arguments = [10]
[rule.deep-exit]
[rule.defer]
    arguments = [["call-chain", "loop"]]
[rule.dot-imports]
[rule.duplicated-imports]
[rule.early-return]
[rule.error-naming]
[rule.error-return]
[rule.error-strings]
[rule.errorf]
[rule.exported]
    arguments = ["checkPrivateReceivers"]
[rule.flag-parameter]
[rule.function-result-limit]
    arguments = [3]
[rule.get-return]
[rule.identify-unused-parameters]
[rule.if-return]
[rule.increment-decrement]
[rule.indent-error-flow]
[rule.line-length-limit]
    arguments = [120]
[rule.max-public-structs]
    arguments = [5]
[rule.modifies-parameter]
[rule.modifies-value-receiver]
[rule.package-comments]
[rule.range]
[rule.receiver-naming]
[rule.redefines-builtin-id]
[rule.string-of-int]
[rule.superfluous-else]
[rule.time-equal]
[rule.time-naming]
[rule.unchecked-type-assertion]
[rule.unexported-naming]
[rule.unexported-return]
[rule.unnecessary-stmt]
[rule.unreachable-code]
[rule.unused-parameter]
[rule.unused-receiver]
[rule.use-any]
[rule.var-declaration]
[rule.waitgroup-by-value]
```

revive's extensibility is its standout feature. Writing a custom rule takes under 50 lines:

```go
// Example: custom revive rule banning "utils" package names
package rule

import "github.com/mgechev/revive/lint"

type BanUtilsPackage struct{}

func (r *BanUtilsPackage) Apply(file *lint.File, _ lint.Arguments) []lint.Failure {
    pkgName := file.Pkg.Name()
    if pkgName == "utils" || pkgName == "util" || pkgName == "helpers" {
        return []lint.Failure{{
            Confidence: 1,
            Failure:    "package name 'utils' is discouraged; prefer descriptive names",
            Node:       file.AST,
        }}
    }
    return nil
}

func (*BanUtilsPackage) Name() string { return "ban-utils-package" }
```

## gofumpt: Stricter Formatting

gofumpt (`mvdan.cc/gofumpt`) is a stricter `go fmt` that enforces additional formatting rules. It's fully backward-compatible — any `gofumpt`-formatted code passes `go fmt`.

```bash
go install mvdan.cc/gofumpt@latest

# Format entire project
gofumpt -l -w .

# Check formatting in CI (non-zero exit if changes needed)
gofumpt -d . | grep -q "." && exit 1
```

Key differences from `go fmt`:
- **No empty lines** at the beginning and end of functions
- **Composite literals** use consistent field alignment
- **Octal literals** must use `0o` prefix (not legacy `0` prefix)
- **Comments** in empty `case` clauses are formatted consistently
- **Multi-line function signatures** collapse extra lines

```go
// go fmt output:
func ProcessUsers(
    users []User,
    options ProcessingOptions,
) ([]Result, error) {
    return nil, nil
}

// gofumpt output (note: removes wrapping for short signatures):
func ProcessUsers(users []User, options ProcessingOptions) ([]Result, error) {
    return nil, nil
}
```

gofumpt integrates into golangci-lint by adding `gofumpt` to the enabled linters list. It's also available as a VS Code format-on-save provider via the Go extension settings.

## gosec: Security Scanning

gosec (`github.com/securego/gosec`) inspects Go source code for security vulnerabilities by examining the AST for unsafe patterns. It detects SQL injection, hardcoded credentials, weak crypto, file inclusion, and TLS misconfigurations.

```bash
go install github.com/securego/gosec/v2/cmd/gosec@latest
gosec ./...

# Output severity above medium, output as JSON for CI
gosec -severity=medium -fmt=json -out=results.json ./...
```

```go
// Issues gosec flags

// G101: Hardcoded credentials
const apiKey = "sk-proj-abc123..." // flagged

// G201: SQL query built with user input (SQL injection)
func getUser(db *sql.DB, id string) (*User, error) {
    query := "SELECT * FROM users WHERE id = " + id // flagged — use placeholders
    return db.Query(query)
}

// G401: Weak cryptographic algorithm
import "crypto/md5"
func hashPassword(pw string) string {
    return fmt.Sprintf("%x", md5.Sum([]byte(pw))) // flagged — use bcrypt
}

// G402: TLS MinVersion too low
func makeServer() *http.Server {
    return &http.Server{
        TLSConfig: &tls.Config{
            MinVersion: tls.VersionTLS10, // flagged — use TLS 1.2 minimum
        },
    }
}

// G404: Weak random number generator
import "math/rand"
func generateToken() string {
    return fmt.Sprintf("%d", rand.Int()) // flagged — use crypto/rand
}

// G601: Implicit memory aliasing in range loop
func getNames(items []*Item) []string {
    var names []string
    for _, item := range items {
        if item.Name != "" {
            names = append(names, item.Name) // flagged in Go < 1.22
        }
    }
    return names
}
```

gosec's rules are organized by severity (low/medium/high) and confidence. In CI pipelines, it's common to fail builds on `medium` severity and above. The `#nosec` annotation suppresses false positives on specific lines.

## CI/CD Integration Pipeline

All five tools integrate into a unified CI workflow. Here's a production-grade GitHub Actions configuration:

```yaml
# .github/workflows/code-quality.yml
name: Go Code Quality
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.23'
          cache: true

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v6
        with:
          version: latest
          args: --timeout=5m --out-format=colored-line-number

      - name: gofumpt check
        run: |
          go install mvdan.cc/gofumpt@latest
          if gofumpt -l . | grep -q "."; then
            echo "::error::Files not formatted with gofumpt"
            gofumpt -d .
            exit 1
          fi

      - name: gosec security scan
        run: |
          go install github.com/securego/gosec/v2/cmd/gosec@latest
          gosec -severity=medium -no-fail -fmt=sarif -out=gosec.sarif ./...
        continue-on-error: true

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: gosec.sarif
```

## Performance and Integration Patterns

golangci-lint caches results aggressively — on the second run with an unchanged codebase, analysis completes in under 100ms. The `--new-from-rev` flag checks only changed code relative to a git reference, making it practical to run in pre-commit hooks:

```bash
# In .git/hooks/pre-commit — lint only changed code
golangci-lint run --new-from-rev=HEAD~1 --fix ./...
```

For monorepos with multiple Go modules, golangci-lint's `--path-prefix` flag handles per-module configurations. Each module can have its own `.golangci.yml`, with a root config defining shared baseline settings.

## Why Go Code Quality Tooling Is Exceptional

Go's tooling ecosystem is uniquely cohesive among compiled languages. While Rust relies on `clippy` and `rustfmt` as separate workflows, and C++ requires external tools with complex build integration, Go's code quality tools are all installable via `go install`, operate on the standard AST, and compose through golangci-lint's unified interface. This integration quality is one reason Go teams report fewer style debates and security incidents than teams in other ecosystems. For a broader look at code quality across languages, see our comparison of [code linter and formatter tools](../2026-06-20-code-linter-formatter-tools-eslint-prettier-ruff-black-rubocop/) and our guide to [Go testing frameworks](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/).

## FAQ

### What's the difference between go fmt, gofumpt, and goimports?

`go fmt` is the standard formatter shipped with Go — it handles indentation, spacing, and line breaks. `gofumpt` adds stricter rules on top (no empty lines, consistent composite literal alignment, octal literal enforcement). `goimports` handles import organization and unused import removal. They're complementary: use `gofumpt` for formatting and `goimports` for import management. golangci-lint can run all three.

### Should I use golangci-lint or run linters individually?

Use golangci-lint. It's faster (shared AST parsing), produces unified output, and is the de facto standard for Go projects. Individual linters make sense when you need a specific feature golangci-lint doesn't support, but for 95% of projects, golangci-lint is all you need.

### How do I handle false positives from gosec?

gosec's security checks are intentionally cautious — false positives happen. Suppress them on specific lines with a `// #nosec` comment, or exclude entire rules in the golangci-lint config under `issues.exclude-rules`. Avoid disabling gosec globally — the noise is a signal that your code has patterns worth reviewing.

### Can I use revive instead of golangci-lint?

revive is a single linter (style and correctness rules), while golangci-lint runs revive plus 50+ other linters. You can run revive standalone for its custom rules feature, but for most teams, running revive as part of golangci-lint gives you revive's checks plus staticcheck, gosec, errcheck, and others in one command. If you need custom revive rules, configure them in `.golangci.yml` under `linters-settings.revive.rules`.

### How do I enforce code quality in a legacy Go codebase?

Start with `golangci-lint run --new-from-rev=HEAD~1` to only check changed code. Configure a minimal linter set (govet, errcheck, staticcheck) initially. Use `--issues-exit-code=0` to report issues without failing CI. Over several sprints, gradually enable additional linters (gocognit, gocyclo, gosec) and increase severity. Auto-fix what you can with `--fix`. For a related approach to testing legacy codebases, see our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Go Code Quality Tools: golangci-lint vs staticcheck vs revive vs gofumpt vs gosec",
  "description": "Comprehensive comparison of five Go code quality tools: golangci-lint, staticcheck, revive, gofumpt, and gosec. Covers static analysis, linting configuration, security scanning, CI/CD integration, and team workflows for 2026.",
  "datePublished": "2026-07-23",
  "dateModified": "2026-07-23",
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
