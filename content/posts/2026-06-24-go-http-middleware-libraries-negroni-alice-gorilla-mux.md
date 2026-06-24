---
title: "Self-Hosted Go HTTP Middleware Libraries: Negroni vs Alice vs Gorilla/Mux"
date: "2026-06-24"
tags: ["go", "golang", "middleware", "http", "web-server", "negroni", "alice", "gorilla-mux", "rest-api", "backend"]
draft: false
---

## Introduction

Go's standard library `net/http` provides a solid foundation for building web services, but real-world applications quickly outgrow its basic handler model. Logging, authentication, rate limiting, CORS handling, and request tracing all need to compose cleanly — and that's where HTTP middleware libraries shine.

This guide compares three approaches to Go HTTP middleware: **Negroni** (idiomatic middleware chaining), **Alice** (functional middleware composition), and **Gorilla/Mux** (full-featured router with middleware support). Each represents a different philosophy about how middleware should work in Go.

## Library Overview

| Feature | Negroni | Alice | Gorilla/Mux |
|---------|---------|-------|-------------|
| **GitHub Stars** | 7,530 | 3,362 | 21,840 |
| **Approach** | Classic `http.Handler` wrapping | Functional middleware chaining | Full HTTP router + middleware |
| **Middleware Model** | HandlerFunc with `next()` | Standard `http.Handler` | `MiddlewareFunc` type |
| **Router** | Bring your own (stdlib) | Bring your own (stdlib) | Built-in powerful router |
| **Path Parameters** | No (use stdlib) | No (use stdlib) | Yes (`{name}`, regex) |
| **Subrouters** | N/A | N/A | Yes |
| **Go Version** | Go 1.x+ | Go 1.x+ | Go 1.22+ |
| **Dependencies** | Minimal | Zero | Minimal |
| **Last Updated** | May 2025 | June 2024 | Aug 2024 |
| **License** | MIT | MIT | BSD-3 |

## Negroni: The Idiomatic Classic

Negroni, created by the same team behind the popular `urfave/cli` library, is the most widely recognized Go middleware library with 7,530 stars. It takes the classic approach: middleware is a function that receives the request, response writer, and a `next` handler — mirroring patterns from Express.js and other web frameworks.

### Core Negroni Middleware

```go
package main

import (
    "fmt"
    "log"
    "net/http"
    "time"

    "github.com/urfave/negroni"
)

func LoggerMiddleware(rw http.ResponseWriter, r *http.Request, next http.HandlerFunc) {
    start := time.Now()
    log.Printf("→ %s %s", r.Method, r.URL.Path)
    next(rw, r)
    log.Printf("← %s %s (%v)", r.Method, r.URL.Path, time.Since(start))
}

func AuthMiddleware(rw http.ResponseWriter, r *http.Request, next http.HandlerFunc) {
    token := r.Header.Get("Authorization")
    if token == "" {
        http.Error(rw, "Unauthorized", http.StatusUnauthorized)
        return
    }
    // Validate token...
    next(rw, r)
}

func RecoveryMiddleware(rw http.ResponseWriter, r *http.Request, next http.HandlerFunc) {
    defer func() {
        if err := recover(); err != nil {
            log.Printf("PANIC: %v", err)
            http.Error(rw, "Internal Server Error", http.StatusInternalServerError)
        }
    }()
    next(rw, r)
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/api/users", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, `{"users":["alice","bob","charlie"]}`)
    })
    mux.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, `{"status":"healthy"}`)
    })

    n := negroni.New()
    n.Use(negroni.NewRecovery())  // Built-in recovery
    n.Use(negroni.NewLogger())    // Built-in logger
    n.Use(negroni.HandlerFunc(AuthMiddleware))
    n.Use(negroni.HandlerFunc(LoggerMiddleware))
    n.UseHandler(mux)

    log.Println("Server starting on :8080")
    http.ListenAndServe(":8080", n)
}
```

### Custom Negroni Handler with Context

```go
func RequestIDMiddleware(rw http.ResponseWriter, r *http.Request, next http.HandlerFunc) {
    requestID := r.Header.Get("X-Request-ID")
    if requestID == "" {
        requestID = generateUUID()
    }
    rw.Header().Set("X-Request-ID", requestID)
    
    // Add to context for downstream handlers
    ctx := context.WithValue(r.Context(), "requestID", requestID)
    next(rw, r.WithContext(ctx))
}

// Negroni's With() helper for conditional middleware
func RateLimitMiddleware(limit int) negroni.HandlerFunc {
    limiter := NewTokenBucket(limit, time.Second)
    return func(rw http.ResponseWriter, r *http.Request, next http.HandlerFunc) {
        if !limiter.Allow() {
            http.Error(rw, "Rate limit exceeded", http.StatusTooManyRequests)
            return
        }
        next(rw, r)
    }
}

// Conditional middleware application
n := negroni.New()
n.Use(negroni.HandlerFunc(RequestIDMiddleware))

// Apply rate limiting only to API routes
if isProduction() {
    n.Use(RateLimitMiddleware(100))
}
n.UseHandler(mux)
```

Negroni's strength is its simplicity and familiarity. The `next()` pattern is immediately intuitive to anyone who's used Express, Koa, or similar middleware systems. The `With()` helper elegantly handles conditional middleware without complex chaining logic.

## Alice: Functional Middleware Elegance

Alice takes a fundamentally different approach — instead of a middleware-specific type, it uses standard `http.Handler` throughout. Middleware is just a function that wraps a handler: `func(http.Handler) http.Handler`. This makes Alice middleware fully interoperable with the entire Go ecosystem without adapters.

### Core Alice Pattern

```go
package main

import (
    "fmt"
    "log"
    "net/http"
    "time"

    "github.com/justinas/alice"
)

// Alice middleware: standard func(http.Handler) http.Handler
func Logger(h http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        log.Printf("→ %s %s", r.Method, r.URL.Path)
        h.ServeHTTP(w, r)
        log.Printf("← %s %s (%v)", r.Method, r.URL.Path, time.Since(start))
    })
}

func Auth(h http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        if token == "" || !validateToken(token) {
            http.Error(w, "Unauthorized", http.StatusUnauthorized)
            return
        }
        h.ServeHTTP(w, r)
    })
}

func CORS(h http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Access-Control-Allow-Origin", "*")
        w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
        
        if r.Method == "OPTIONS" {
            w.WriteHeader(http.StatusOK)
            return
        }
        h.ServeHTTP(w, r)
    })
}

func RequestMetrics(h http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        metrics.Inc("http.requests", tags{r.Method, r.URL.Path})
        wrapped := &responseWriter{ResponseWriter: w, statusCode: 200}
        h.ServeHTTP(wrapped, r)
        metrics.Observe("http.duration", time.Since(start), tags{wrapped.statusCode})
    })
}

// Reusable middleware chains
var (
    PublicChain  = alice.New(Logger, CORS, RequestMetrics)
    PrivateChain = alice.New(Logger, Auth, CORS, RequestMetrics)
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/api/health", healthHandler)
    mux.HandleFunc("/api/users", usersHandler)
    
    // Public routes with minimal middleware
    mux.Handle("/api/public/", PublicChain.ThenFunc(publicHandler))
    
    // Private routes with full middleware
    mux.Handle("/api/private/", PrivateChain.ThenFunc(privateHandler))
    
    log.Println("Server starting on :8080")
    http.ListenAndServe(":8080", mux)
}
```

### Composing Chains from Chains

Alice's killer feature is chain composition — you can build middleware stacks from other stacks:

```go
// Base middleware for all routes
base := alice.New(Logger, Recovery, RequestID)

// Auth variations
adminOnly := base.Append(AuthAdmin)
userOnly := base.Append(AuthUser)

// Rate-limited API endpoints  
api := base.Append(RateLimit(100, time.Minute))

// Compose them
adminAPI := adminOnly.Append(api...)
userAPI := userOnly.Append(api...)

// Apply to handlers
router.Handle("/admin/users", adminAPI.ThenFunc(adminUsersHandler))
router.Handle("/api/profile", userAPI.ThenFunc(profileHandler))
```

The key insight: because Alice uses `func(http.Handler) http.Handler`, any standard library middleware, third-party middleware from any ecosystem, or custom function works without adapters. This interoperability is Alice's superpower.

## Gorilla/Mux: The Full-Featured Router

Gorilla/Mux is the most comprehensive option with 21,840 stars. It's a full HTTP request router and URL matcher that includes built-in middleware support, path parameter extraction, subrouters, and regex-based route matching. It's not just a middleware library — it's a complete routing solution.

### Gorilla/Mux Middleware with Router

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"

    "github.com/gorilla/mux"
)

// Gorilla/Mux MiddlewareFunc
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        log.Printf("%s %s", r.Method, r.RequestURI)
        next.ServeHTTP(w, r)
    })
}

func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Header.Get("X-API-Key") == "" {
            http.Error(w, `{"error":"missing API key"}`, http.StatusUnauthorized)
            return
        }
        next.ServeHTTP(w, r)
    })
}

func contentTypeMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        next.ServeHTTP(w, r)
    })
}

func main() {
    r := mux.NewRouter()
    
    // Global middleware
    r.Use(loggingMiddleware)
    r.Use(contentTypeMiddleware)
    
    // Public routes
    r.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
    }).Methods("GET")
    
    // API subrouter with auth middleware
    api := r.PathPrefix("/api").Subrouter()
    api.Use(authMiddleware)
    
    // User routes with path parameters
    api.HandleFunc("/users", listUsers).Methods("GET")
    api.HandleFunc("/users/{id:[0-9]+}", getUser).Methods("GET")
    api.HandleFunc("/users", createUser).Methods("POST")
    api.HandleFunc("/users/{id:[0-9]+}", updateUser).Methods("PUT")
    api.HandleFunc("/users/{id:[0-9]+}", deleteUser).Methods("DELETE")
    
    // Admin subrouter with stricter middleware
    admin := r.PathPrefix("/admin").Subrouter()
    admin.Use(authMiddleware, adminOnlyMiddleware)
    admin.HandleFunc("/users", adminListUsers).Methods("GET")
    admin.HandleFunc("/stats", adminStats).Methods("GET")
    
    // Host-based routing
    apiHost := r.Host("api.example.com").Subrouter()
    apiHost.HandleFunc("/v1/{resource}", apiV1Handler)
    
    log.Println("Server starting on :8080")
    http.ListenAndServe(":8080", r)
}
```

### Advanced Route Patterns

```go
r := mux.NewRouter()

// Path prefix matching
r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./public/"))))

// Query parameter matching
r.HandleFunc("/search", searchHandler).Queries("q", "{query}")

// Custom matcher
r.HandleFunc("/products/{category}", categoryHandler).MatcherFunc(func(r *http.Request, rm *mux.RouteMatch) bool {
    category := mux.Vars(r)["category"]
    return category == "electronics" || category == "books"
})

// Strict slash handling
r.StrictSlash(true)  // /users → /users/ (or vice versa)

// Method-based routing
r.HandleFunc("/api/items", createItem).Methods("POST")
r.HandleFunc("/api/items/{id}", getItem).Methods("GET")
r.HandleFunc("/api/items/{id}", updateItem).Methods("PUT", "PATCH")
```

### Middleware for Specific Routes

```go
r := mux.NewRouter()

// Apply middleware only to specific routes
r.Handle("/api/sensitive", 
    authMiddleware(
        rateLimitMiddleware(
            http.HandlerFunc(sensitiveHandler),
        ),
    ),
).Methods("GET")

// Or use the Route.Subrouter pattern for groups
v2 := r.PathPrefix("/api/v2").Subrouter()
v2.Use(apiVersionMiddleware("2.0"))
v2.HandleFunc("/users", v2UsersHandler)
```

## Why Self-Host Go Middleware Patterns Matter

Self-hosting Go services means you control the entire request pipeline — from TLS termination to response delivery. Middleware libraries are the key to keeping this pipeline maintainable as your service grows. Rather than embedding logging, auth, and metrics into every handler (creating a tangled mess), middleware lets you compose these concerns orthogonally.

**Separation of concerns** is the primary benefit. Your business logic handlers deal only with domain logic, while middleware handles cross-cutting concerns independently. When you need to add distributed tracing or change your auth mechanism, you modify one middleware function instead of touching every handler in your codebase.

For self-hosted deployments on modest hardware, Go's efficiency combined with clean middleware patterns means you can serve thousands of requests per second with minimal resource usage. A well-structured Go service using any of these middleware libraries typically consumes 15-50MB of RAM — an order of magnitude less than equivalent JVM or Node.js deployments.

For more Go ecosystem guidance, see our [Go CLI libraries comparison](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/), our [Go environment configuration libraries guide](../2026-06-23-go-environment-config-libraries-caarlos0-env-cleanenv-envconfig/), and our [Go Redis client libraries comparison](../2026-06-23-go-redis-client-libraries-go-redis-rueidis-redigo/). For WebSocket middleware patterns using the Gorilla toolkit, check our [WebSocket client libraries guide](../2026-06-20-websocket-client-libraries-gorilla-ws-websocketclient-tokio-tungstenite/).

## FAQ

### Which library should I use for a new Go project in 2026?

If you need a full-featured router with path parameters, subrouters, and regex matching, **Gorilla/Mux** is the clear winner — it provides everything in one package. If you're using Go 1.22+'s enhanced `http.ServeMux` for routing and just need middleware composition, choose **Alice** for its zero-dependency, standard-library-compatible approach. Choose **Negroni** if you prefer the classic `next()` middleware pattern and want built-in recovery/logging helpers.

### Can I use more than one of these libraries together?

Yes. You can use **Alice** to compose middleware chains that feed into **Gorilla/Mux** as the router. You can also use **Negroni** as the top-level handler with **Gorilla/Mux** as the handler it wraps. The libraries are interoperable because they all work at the `http.Handler` level.

### Is Negroni still maintained?

Negroni was last updated in May 2025 and is considered feature-complete. Its creator (the urfave team) has stated that `net/http` middleware is a solved problem — Negroni does what it needs to do and doesn't require active feature development. It's stable and safe to use in production.

### What about the `chi` router?

Chi is another popular Go HTTP router with middleware support that we didn't include in this comparison. It provides similar functionality to Gorilla/Mux with a somewhat lighter footprint and built-in middleware for common concerns. Chi is worth evaluating if Gorilla/Mux's feature set is more than you need.

### How do I test middleware in Go?

All three libraries work with Go's standard `httptest` package. Create a test handler, wrap it with your middleware, and use `httptest.NewRecorder()` to verify status codes, headers, and body content. Alice's `func(http.Handler) http.Handler` signature makes it especially testable — you can test each middleware function in isolation.

### Does middleware order matter?

Absolutely. Middleware executes in the order it's registered. A typical order is: Recovery (innermost), RequestID, Logging, CORS, Auth, RateLimit, Business Logic. Put recovery first so it catches panics from everything downstream. Put auth before rate limiting so unauthenticated requests don't consume rate limit quotas.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Go HTTP Middleware Libraries: Negroni vs Alice vs Gorilla/Mux",
  "description": "Compare three approaches to Go HTTP middleware — Negroni, Alice, and Gorilla/Mux — with code examples, middleware composition patterns, and guidance on choosing the right library for self-hosted Go web services.",
  "datePublished": "2026-06-24",
  "dateModified": "2026-06-24",
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
