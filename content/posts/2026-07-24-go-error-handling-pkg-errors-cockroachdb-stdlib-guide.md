---
title: "Go Error Handling Libraries: pkg/errors vs cockroachdb/errors vs stdlib — Complete Comparison 2026"
date: "2026-07-24"
tags: ["go", "golang", "error-handling", "errors", "pkg-errors", "cockroachdb", "stdlib", "debugging"]
draft: false
---

## Introduction

Error handling is the most debated topic in Go. Unlike languages with try/catch exceptions, Go makes errors explicit return values — every function that can fail returns `(result, error)`. This explicitness is Go's strength, but it also creates challenges: how do you add context to errors as they propagate up the call stack? How do you preserve the original error for type checking? How do you attach stack traces for debugging?

The Go ecosystem provides three distinct approaches: the **standard library `errors` package** (zero dependencies), **`pkg/errors`** by Dave Cheney (8,258 stars, the original error-wrapping library), and **`cockroachdb/errors`** (2,449 stars, enterprise-grade error handling from Cockroach Labs). This guide compares all three with practical code examples and explains when to use each.

## Comparison at a Glance

| Feature | stdlib `errors` | `pkg/errors` | `cockroachdb/errors` |
|---------|----------------|--------------|---------------------|
| **Wrapping** | `fmt.Errorf("%w", err)` | `errors.Wrap(err, "msg")` | `errors.Wrap(err, "msg")` |
| **Unwrapping** | `errors.Unwrap()` | `errors.Cause()` | `errors.Unwrap()` / `errors.Cause()` |
| **Stack Traces** | No | Yes (via `%+v`) | Yes (via `%+v` or `GetSafeDetails`) |
| **Error Isolation** | `errors.Is()` | No (use `errors.Is` from stdlib) | `errors.Is()` |
| **Type Assertion** | `errors.As()` | No (use `errors.As` from stdlib) | `errors.As()` |
| **Error Markers** | `errors.New("sentinel")` | `errors.New("sentinel")` | `errors.New("sentinel")` + markers |
| **Network Portability** | No | No | Yes (encode/decode errors across network) |
| **Multi-Errors** | `errors.Join()` (Go 1.20+) | No | `errors.CombineErrors()` |
| **Safe Details** | N/A | N/A | Yes (separate safe/unsafe error details) |
| **Telemetry Keys** | No | No | Yes (structured error metadata) |
| **GitHub Stars** | Bundled with Go | 8,258 | 2,449 |
| **Last Updated** | Go release cycle | March 2026 | July 2026 |
| **Go Version** | Go 1.13+ features | Any Go version | Go 1.13+ recommended |

## Go Standard Library `errors`: The Modern Foundation

Go 1.13 introduced three game-changing features in the standard `errors` package: error wrapping with `%w`, `errors.Is()` for sentinel checking, and `errors.As()` for type assertion. Go 1.20 added `errors.Join()` for combining multiple errors. Together, these make the stdlib a viable choice for most applications without any external dependencies.

### Basic Usage

```go
package main

import (
    "errors"
    "fmt"
)

var ErrNotFound = errors.New("resource not found")
var ErrPermissionDenied = errors.New("permission denied")

func findUser(id int) (*User, error) {
    user, err := db.Query("SELECT * FROM users WHERE id = ?", id)
    if err != nil {
        return nil, fmt.Errorf("findUser(%d): %w", id, err)
    }
    if user == nil {
        return nil, fmt.Errorf("findUser(%d): %w", id, ErrNotFound)
    }
    return user, nil
}

func getUserProfile(id int) error {
    user, err := findUser(id)
    if err != nil {
        return fmt.Errorf("getUserProfile: %w", err)
    }
    _ = user
    return nil
}

func main() {
    err := getUserProfile(42)
    if err != nil {
        if errors.Is(err, ErrNotFound) {
            fmt.Println("User not found, showing 404")
            return
        }
        if errors.Is(err, ErrPermissionDenied) {
            fmt.Println("Access denied, showing 403")
            return
        }
        fmt.Printf("Unexpected error: %v\n", err)
    }
}
```

### Unwrapping and Type Assertion

```go
type ValidationError struct {
    Field string
    Value interface{}
    Msg   string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Msg)
}

func validateInput(data map[string]interface{}) error {
    return &ValidationError{
        Field: "email",
        Value: data["email"],
        Msg:   "invalid format",
    }
}

func processForm(data map[string]interface{}) error {
    err := validateInput(data)
    if err != nil {
        return fmt.Errorf("processForm: %w", err)
    }
    return nil
}

func handler() {
    err := processForm(formData)
    if err != nil {
        var valErr *ValidationError
        if errors.As(err, &valErr) {
            fmt.Printf("Field '%s' is invalid: %s\n", valErr.Field, valErr.Msg)
        }
    }
}
```

### Go 1.20+ Multi-Errors

```go
func validateAll(user *User) error {
    var errs []error

    if user.Name == "" {
        errs = append(errs, fmt.Errorf("name is required"))
    }
    if user.Age < 0 {
        errs = append(errs, fmt.Errorf("age must be positive"))
    }
    if !isValidEmail(user.Email) {
        errs = append(errs, fmt.Errorf("email is invalid"))
    }

    return errors.Join(errs...)
}

func main() {
    err := validateAll(&User{Name: "", Age: -5, Email: "bad"})
    if err != nil {
        fmt.Println(err)
        // Output: name is required
        //         age must be positive
        //         email is invalid
    }
}
```

### Strengths

- **Zero dependencies** — ships with Go itself
- **`errors.Is()` and `errors.As()`** — clean chain traversal without `==` comparisons
- **`errors.Join()`** — first-class multi-error support since Go 1.20
- **Universally supported** — every Go library uses stdlib errors
- **No learning curve** — if you know Go, you know the stdlib errors package

### Weaknesses

- **No stack traces** — you get an error message but no file/line information
- **Manual wrapping** — `fmt.Errorf("context: %w", err)` at every level is verbose
- **No error metadata** — can't attach structured key-value pairs to errors
- **String-based wrapping** — error messages are the only context mechanism

## pkg/errors: The Community Standard

Dave Cheney's `pkg/errors` was the de facto standard for Go error handling before Go 1.13. It introduced error wrapping and stack trace capture to the Go community. While the author now recommends the standard library for new projects, `pkg/errors` remains valuable for its stack trace capture and the `errors.Cause()` pattern.

### Installation

```bash
go get github.com/pkg/errors
```

### Basic Usage

```go
package main

import (
    "fmt"
    "github.com/pkg/errors"
)

func readConfig(path string) ([]byte, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, errors.Wrap(err, "failed to read config file")
    }
    return data, nil
}

func parseConfig(data []byte) (*Config, error) {
    var cfg Config
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return nil, errors.Wrap(err, "failed to parse config")
    }
    return &cfg, nil
}

func LoadConfig(path string) (*Config, error) {
    data, err := readConfig(path)
    if err != nil {
        return nil, errors.Wrap(err, "LoadConfig failed")
    }

    cfg, err := parseConfig(data)
    if err != nil {
        return nil, errors.Wrap(err, "LoadConfig failed")
    }

    return cfg, nil
}

func main() {
    cfg, err := LoadConfig("/etc/app/config.yaml")
    if err != nil {
        // Print with stack trace
        fmt.Printf("%+v\n", err)

        // Get the root cause
        rootCause := errors.Cause(err)
        fmt.Printf("Root cause: %v\n", rootCause)
    }
    _ = cfg
}
```

### Stack Trace Output

When you use `%+v`, `pkg/errors` produces detailed output including file paths and line numbers:

```
failed to read config file: open /etc/app/config.yaml: no such file or directory
main.readConfig
    /app/config.go:15
main.LoadConfig
    /app/config.go:28
main.main
    /app/main.go:10
runtime.main
    /usr/local/go/src/runtime/proc.go:250
```

### Creating New Errors

```go
var ErrConnectionRefused = errors.New("connection refused")

// With message wrapping
return errors.Wrap(ErrConnectionRefused, "database ping failed")

// With formatted message
return errors.Wrapf(err, "failed to process user %d", userID)

// With message only (no wrapping)
return errors.WithMessage(err, "operation timed out")
```

### Strengths

- **Stack traces** — `%+v` reveals the full call path where the error occurred
- **`errors.Wrap()`** — idiomatic, concise error wrapping
- **`errors.Cause()`** — retrieve the original error for type checking
- **Widely adopted** — 8,258 stars, used in Docker, Kubernetes, and Terraform historically
- **Lightweight** — one file, no dependencies

### Weaknesses

- **No `errors.Is()` / `errors.As()` support** — must use stdlib versions on top of `errors.Cause()`
- **Archived mindset** — the author recommends stdlib for new projects
- **Verbose wrapping** — `Wrap()` at every level adds boilerplate
- **No structured metadata** — stack traces are the only added context
- **Stdlib compatibility gap** — `errors.Unwrap()` on a wrapped chain may not reach the root

## cockroachdb/errors: Enterprise Error Infrastructure

CockroachDB's error library is the most sophisticated error handling system in the Go ecosystem. Built for a distributed SQL database that spans continents, it provides features you won't find anywhere else: network-safe error serialization, separate safe (customer-visible) and unsafe (internal) error details, structured telemetry keys, and domain-specific error hierarchies.

### Architecture

cockroachdb/errors introduces the concept of **error barriers** and **safe details**. Every error wrapping adds a layer that can be classified as "safe" (can be shown to end users) or "unsafe" (internal debugging data). When an error crosses a network boundary (gRPC, HTTP), only safe details are serialized — internal paths, SQL queries, and stack traces are stripped. This is critical for multi-tenant SaaS applications where error messages must not leak internal architecture.

### Installation

```bash
go get github.com/cockroachdb/errors
```

### Basic Usage

```go
package main

import (
    "fmt"
    "github.com/cockroachdb/errors"
)

func queryDatabase(query string) error {
    return errors.New("connection refused on port 5432")
}

func getOrder(orderID string) (*Order, error) {
    _, err := queryDatabase(fmt.Sprintf("SELECT * FROM orders WHERE id = '%s'", orderID))
    if err != nil {
        return nil, errors.Wrapf(err, "failed to retrieve order %s", orderID)
    }
    return &Order{}, nil
}

func GetOrderHandler(orderID string) (*Order, error) {
    order, err := getOrder(orderID)
    if err != nil {
        return nil, errors.WithDetailf(err, "request timed out after 30s")
    }
    return order, nil
}

func main() {
    _, err := GetOrderHandler("ORD-12345")
    if err != nil {
        fmt.Printf("Internal: %+v\n\n", err)
        fmt.Printf("Safe: %v\n", errors.GetSafeDetails(err))
    }
}
```

### Markers and Error Hierarchies

```go
var (
    ErrTemporary  = errors.NewMarker("temporary error")
    ErrPermanent  = errors.NewMarker("permanent error")
    ErrConnection = errors.NewMarker("connection issue")
)

func handleDatabaseOp() error {
    err := db.Ping()
    if err != nil {
        if isNetworkError(err) {
            return errors.Mark(
                errors.Wrap(err, "database ping failed"),
                ErrTemporary, ErrConnection,
            )
        }
        return errors.Mark(
            errors.Wrap(err, "database ping failed"),
            ErrPermanent,
        )
    }
    return nil
}

func retryLogic() error {
    err := handleDatabaseOp()
    if err != nil {
        if errors.Is(err, ErrTemporary) {
            fmt.Println("Retrying due to temporary error...")
            return nil
        }
        return err
    }
    return nil
}
```

### Network-Safe Error Serialization

```go
func encodeError(err error) error {
    if err == nil {
        return nil
    }
    encoded := errors.EncodeError(
        context.Background(), err,
        errors.WithSafety(errors.SafeDetailsOnly),
    )
    return encoded
}

func decodeError(encodedErr error) error {
    if encodedErr == nil {
        return nil
    }
    return errors.DecodeError(context.Background(), encodedErr)
}
```

### Structured Telemetry Keys

```go
err := errors.WithContextTags(err,
    "user_id", "u_12345",
    "tenant", "acme-corp",
    "region", "us-east-1",
    "query_latency_ms", 245,
)

if tags := errors.GetContextTags(err); tags != nil {
    for _, tag := range tags.GetAll() {
        fmt.Printf("Tag: %s = %v\n", tag.Key, tag.Value())
    }
}
```

### Strengths

- **Network portability** — safe/unsafe detail separation for multi-service architectures
- **Error markers** — lightweight typed error classification without sentinel values
- **Structured telemetry** — attach key-value metadata to errors for monitoring
- **Barriers** — prevent internal details from leaking across API boundaries
- **Multi-error** — `errors.CombineErrors()` for aggregating multiple failures
- **Full stdlib compatibility** — implements `Unwrap()`, `Is()`, `As()`

### Weaknesses

- **Heavy** — large dependency tree suitable for complex distributed systems
- **Overkill for simple apps** — a CLI tool doesn't need network-safe error encoding
- **Smaller community** — 2,449 stars vs 8,258 for `pkg/errors`
- **CockroachDB-specific concepts** — markers, barriers, and telemetry keys add learning curve
- **API surface** — large (100+ functions) compared to `pkg/errors` (10 functions)

## Architecture Decision Guide

### Choose stdlib `errors` when:
- You're building a simple application or microservice with a single binary
- You want zero external dependencies
- You're using Go 1.20+ and can leverage `errors.Join()` for multi-errors
- Stack traces aren't critical for your debugging workflow
- Your team values simplicity over features

### Choose `pkg/errors` when:
- Stack traces are essential for debugging (monolithic applications)
- You're maintaining a legacy codebase that already uses `pkg/errors`
- You need a lightweight wrapper beyond the stdlib without a heavy dependency
- You want the `errors.Cause()` pattern for root-cause analysis

### Choose `cockroachdb/errors` when:
- You're building a distributed system with microservices
- Errors cross network boundaries (gRPC, HTTP APIs)
- You need to hide internal implementation details from API consumers
- You want structured error metadata for monitoring dashboards
- You need error classification via markers (not just sentinel values)

## Practical Patterns

### Combining pkg/errors with stdlib

Most real-world Go projects that use `pkg/errors` benefit from using stdlib's `errors.Is()` and `errors.As()` for checking, while using `errors.Wrap()` and `%+v` for stack traces:

```go
// Create with pkg/errors
err := errors.Wrap(sql.ErrNoRows, "user not found")

// Check with stdlib
if errors.Is(err, sql.ErrNoRows) {
    // Handle not found
}

// Print with pkg/errors
fmt.Printf("%+v\n", err)  // Includes stack trace
```

### Migration: pkg/errors to stdlib

```go
// Before (pkg/errors)
if err != nil {
    return errors.Wrap(err, "failed to load user")
}

// After (stdlib)
if err != nil {
    return fmt.Errorf("failed to load user: %w", err)
}
```

## Why Self-Host Your Go Error Handling Strategy?

Error handling in Go is a design philosophy, not just a library choice. The decision between stdlib, `pkg/errors`, and `cockroachdb/errors` shapes how your team debugs production issues, monitors service health, and communicates failure modes to API consumers. Open-source libraries let you own this strategy entirely — no vendor restrictions on what error data you can collect or how you format it.

For Go testing patterns that exercise your error handling, see our [Go testing frameworks guide](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/). For code quality tools that can enforce error-handling lint rules, check our [Go code quality tools comparison](../2026-07-23-go-code-quality-tools-golangci-lint-staticcheck-revive-gofumpt-gosec/). For state machines where error handling patterns differ, see our [Go state machine libraries guide](../2026-07-23-go-state-machine-libraries-looplab-fsm-stateless-gofsm/).

## FAQ

### Do I still need pkg/errors in Go 1.20+?

For most new projects, **no**. The standard library now covers the three core use cases that `pkg/errors` originally solved: error wrapping (`fmt.Errorf` with `%w`), error checking (`errors.Is()` and `errors.As()`), and multi-errors (`errors.Join()`). The one feature the stdlib still lacks is stack trace capture — if you need `%+v` to print file paths and line numbers in error output, `pkg/errors` (or `cockroachdb/errors`) is still valuable.

### How do I add stack traces without pkg/errors?

If you want stack traces without external dependencies, you can use the `runtime` package manually:

```go
func wrapWithStack(err error, msg string) error {
    pc, file, line, _ := runtime.Caller(1)
    fn := runtime.FuncForPC(pc)
    return fmt.Errorf("%s: %w [at %s:%d %s]",
        msg, err, file, line, fn.Name())
}
```

This is more verbose than `pkg/errors.Wrap()` but maintains zero external dependencies. For production use, however, `pkg/errors` or `cockroachdb/errors` are more reliable and tested.

### Can I use cockroachdb/errors in a non-CockroachDB project?

Absolutely. Despite its name, `cockroachdb/errors` is a standalone library used in many Go projects outside Cockroach Labs. Its feature set (network-safe serialization, markers, telemetry keys) is specifically designed for distributed systems of any kind — microservice architectures, SaaS platforms, and multi-tenant APIs all benefit from these patterns.

### What's the performance impact of stack trace capture?

`pkg/errors.Wrap()` captures a stack trace using `runtime.Callers()` which involves walking the call stack — typically 1-5 microseconds on modern hardware. This is negligible for most applications but can add up in hot paths (e.g., inside a tight loop that fails frequently). For performance-sensitive code, consider wrapping errors at higher levels of the call stack rather than at every `if err != nil` check.

### How should I handle errors in gRPC services?

For gRPC services, `cockroachdb/errors` is the strongest choice. It provides first-class support for encoding errors across the network with separate safe/unsafe detail separation. Your gRPC interceptors can automatically strip stack traces and internal file paths before sending errors to clients, while preserving full debugging information for your internal logging. This is a common source of security vulnerabilities in Go microservices — exposing internal paths and SQL queries in error responses.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Error Handling Libraries: pkg/errors vs cockroachdb/errors vs stdlib — Complete Comparison 2026",
  "description": "In-depth comparison of Go error handling: standard library errors package, pkg/errors (8.2K stars) with stack traces, and cockroachdb/errors (2.4K stars) with network-safe serialization for distributed systems.",
  "datePublished": "2026-07-24",
  "dateModified": "2026-07-24",
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
