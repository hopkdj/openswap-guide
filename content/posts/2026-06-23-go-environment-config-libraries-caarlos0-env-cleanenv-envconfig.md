---
title: "Self-Hosted Go Environment Configuration Libraries: caarlos0/env vs cleanenv vs envconfig"
date: "2026-06-23"
tags: ["go", "golang", "configuration", "environment-variables", "settings", "developer-libraries", "comparison"]
draft: false
---

## Why Environment Variables Still Rule Configuration

Twelve-factor app methodology has cemented environment variables as the universal configuration transport. Unlike config files (YAML, TOML, JSON), environment variables flow naturally through Docker, Kubernetes, systemd, and every cloud platform without format conversion. Your PostgreSQL password doesn't need to be parsed from YAML inside a ConfigMap — it's just `$DB_PASSWORD`.

But reading environment variables manually in Go is tedious and error-prone:

```go
port := os.Getenv("PORT")
if port == "" {
    port = "8080"
}
dbURL := os.Getenv("DATABASE_URL")
if dbURL == "" {
    panic("DATABASE_URL is required")
}
```

Multiply this by 20+ configuration values and you've got hundreds of lines of boilerplate, inconsistent defaults, and no validation. The Go ecosystem provides three mature libraries that eliminate this boilerplate through struct tags and reflection: **caarlos0/env** (2,100+ stars, parse env vars into any struct), **cleanenv** (1,600+ stars, reads from env, files, or both), and **envconfig** (5,000+ stars, the veteran by Kelsey Hightower).

Each takes a different approach to the same fundamental problem: mapping `DATABASE_MAX_CONNECTIONS=50` to `Config.Database.MaxConnections int`.

## Feature Comparison

| Feature | caarlos0/env | cleanenv | envconfig |
|---------|-------------|----------|-----------|
| **GitHub Stars** | ~2,100 | ~1,600 | ~5,000 |
| **Env Var Parsing** | Yes | Yes | Yes |
| **Config File Support** | No | Yes (YAML, JSON, TOML, ENV, EDN) | No |
| **Default Values** | Yes (tags) | Yes (tags) | Yes (tags) |
| **Required Validation** | Yes | Yes | Yes |
| **Nested Structs** | Yes (prefix) | Yes (prefix or dot) | No (flat only) |
| **Slices/Maps** | Yes | Yes | No |
| **Custom Parsers** | Yes | Yes (Setter interface) | No |
| **Prefix Filtering** | Yes | Yes | Yes |
| **Struct Tag** | `env:"VAR"` | `env:"VAR"` | `envconfig:"VAR"` |
| **Description in Usage** | No | Yes (env-description) | No |
| **Zero Dependencies** | Yes | Yes (except yaml/json/toml) | Yes |
| **Go Version** | 1.18+ | 1.21+ | 1.13+ |
| **Last Active** | Active | Active | Maintenance mode |

## caarlos0/env: Parse Everything, Depend on Nothing

Built by Carlos Becker (the goreleaser maintainer), `env` is the most feature-rich environment variable parser in Go. It handles nested structs with configurable prefixes, slices separated by commas or custom delimiters, maps from `KEY=value` formatted variables, time durations, and custom parsers through the `encoding.TextUnmarshaler` interface.

```go
package main

import (
    "fmt"
    "time"
    "github.com/caarlos0/env/v11"
)

type Config struct {
    Port        int           `env:"PORT" envDefault:"8080"`
    DatabaseURL string        `env:"DATABASE_URL,required"`
    Debug       bool          `env:"DEBUG" envDefault:"false"`
    Timeout     time.Duration `env:"TIMEOUT" envDefault:"30s"`
    AllowedIPs  []string      `env:"ALLOWED_IPS" envSeparator:","`
    Redis       RedisConfig   `envPrefix:"REDIS_"`
}

type RedisConfig struct {
    Host     string `env:"HOST" envDefault:"localhost"`
    Port     int    `env:"PORT" envDefault:"6379"`
    Password string `env:"PASSWORD"`
}

func main() {
    cfg := Config{}
    if err := env.Parse(&cfg); err != nil {
        panic(err)
    }
    fmt.Printf("Starting on :%d, Redis at %s:%d\n",
        cfg.Port, cfg.Redis.Host, cfg.Redis.Port)
}
```

With `envPrefix:"REDIS_"`, the nested `RedisConfig` automatically reads from `REDIS_HOST`, `REDIS_PORT`, etc. This is a pattern that both `cleanenv` and `envconfig` struggle with — `envconfig` requires manually mapping each field without prefix support, and `cleanenv` requires the `env-default` tag to explicitly set a prefix.

caarlos0/env also handles `time.Duration` parsing natively (strings like "30s", "5m", "1h"), `url.URL`, and any type implementing `encoding.TextUnmarshaler`. For truly custom parsing, implement your own unmarshal logic by using a custom type.

**Strengths:** Most feature-complete env var parser, nested struct prefixes, native slice/map support, zero dependencies, excellent test coverage, actively maintained by goreleaser team.

**Weaknesses:** No config file support (pure env vars only), no built-in usage/help generation, newer major versions (v11) may break older code that uses `env:"VAR,required"` syntax.

## cleanenv: Hybrid File + Environment

cleanenv bridges the gap between config files and environment variables. It can read configuration from YAML, JSON, TOML, ENV, or EDN files while still allowing overrides via environment variables — the best of both worlds for teams that want a config file for local development and env vars for production.

```go
package main

import (
    "fmt"
    "github.com/ilyakaznacheev/cleanenv"
)

type Config struct {
    Port       int      `yaml:"port" env:"PORT" env-default:"8080"`
    DBHost     string   `yaml:"db_host" env:"DB_HOST" env-default:"localhost"`
    DBPort     int      `yaml:"db_port" env:"DB_PORT" env-default:"5432"`
    DBUser     string   `yaml:"db_user" env:"DB_USER" env-default:"postgres"`
    DBPassword string   `yaml:"db_password" env:"DB_PASSWORD,required"`
    AllowedIPs []string `yaml:"allowed_ips" env:"ALLOWED_IPS" env-separator:","`
}

func main() {
    var cfg Config
    
    // Try config.yml first, fall back to env vars
    err := cleanenv.ReadConfig("config.yml", &cfg)
    if err != nil {
        // If no config file, use env vars only
        err = cleanenv.ReadEnv(&cfg)
        if err != nil {
            panic(err)
        }
    }
    
    fmt.Printf("DB: %s:%s@%s:%d\n",
        cfg.DBUser, "****", cfg.DBHost, cfg.DBPort)
}
```

cleanenv's `ReadConfig()` method attempts to open a file first — if it exists, values are read from the file, but environment variables with the matching `env` tag override file values. This precedence (env vars > config file > defaults) follows the standard twelve-factor priority.

For configuration documentation, cleanenv supports `env-description:"..."` tags that generate help text:

```go
type Config struct {
    Port int `env:"PORT" env-default:"8080" env-description:"HTTP listen port"`
}
// Use cleanenv.GetDescription(&cfg, nil) to generate help output
```

**Docker Compose pattern with cleanenv:**

```yaml
version: "3.8"
services:
  api:
    build: .
    environment:
      - PORT=8080
      - DB_HOST=postgres
      - DB_PASSWORD=${DB_PASSWORD}
      - ALLOWED_IPS=10.0.0.1,10.0.0.2
    volumes:
      - ./config.yml:/app/config.yml:ro
    ports:
      - "8080:8080"
```

**Strengths:** Hybrid config file + env var support, readable YAML configs for local development, env overrides for production, usage/help generation, supports multiple file formats.

**Weaknesses:** Slightly more complex API (multiple read methods), config file format detection can be finicky, nested struct prefix support is less intuitive than caarlos0/env, depends on yaml/json/toml parsers.

## envconfig: The Battle-Tested Original

Kelsey Hightower's envconfig started the Go struct-tag-for-env-vars pattern. With 5,000+ stars and usage in Kubernetes ecosystem tools, it's the most battle-tested option. However, it intentionally stays minimal — no nested structs, no slices, no maps, no config file support.

```go
package main

import (
    "fmt"
    "github.com/kelseyhightower/envconfig"
)

type Config struct {
    Port         int    `envconfig:"PORT" default:"8080"`
    DatabaseURL  string `envconfig:"DATABASE_URL" required:"true"`
    Debug        bool   `envconfig:"DEBUG" default:"false"`
    MaxWorkers   int    `envconfig:"MAX_WORKERS" default:"10"`
}

func main() {
    var cfg Config
    err := envconfig.Process("myapp", &cfg)
    if err != nil {
        panic(err)
    }
    fmt.Printf("Starting on :%d with %d workers\n", cfg.Port, cfg.MaxWorkers)
}
```

envconfig adds an optional prefix (`"myapp"` above means it reads `MYAPP_PORT`, `MYAPP_DATABASE_URL`, etc.) — useful when multiple services share the same environment. It also provides `envconfig.Usage("myapp", &cfg)` which prints formatted documentation for all expected variables.

One underappreciated feature: envconfig validates that all fields are exportable (capitalized) at compile time. If you accidentally make a field private, `Process()` returns an error rather than silently ignoring it.

**Strengths:** Minimal API, zero dependencies, rock-solid stability (last breaking change was years ago), excellent for simple flat configs, prefix support for multi-service environments, usage documentation generation.

**Weaknesses:** No nested structs — all configuration must be flat (you can't have a `Database.Host` sub-struct), no slice/map support (comma-separated strings must be parsed manually), no config file support, in maintenance mode (no new major features planned), single-prefix only (can't prefix sub-groups differently).

## Workarounds for envconfig's Limitations

Since envconfig doesn't support nested structs, teams often work around this by flattening config:

```go
// Instead of:
type Config struct {
    Database DBConfig
}
type DBConfig struct {
    Host string `envconfig:"HOST"`
}

// Use flat struct with descriptive names:
type Config struct {
    DatabaseHost string `envconfig:"DATABASE_HOST" default:"localhost"`
    DatabasePort int    `envconfig:"DATABASE_PORT" default:"5432"`
    RedisHost    string `envconfig:"REDIS_HOST" default:"localhost"`
    RedisPort    int    `envconfig:"REDIS_PORT" default:"6379"`
}
```

For slices, parse manually:
```go
allowedIPs := strings.Split(os.Getenv("ALLOWED_IPS"), ",")
```

This pattern works for simple services but becomes unwieldy beyond ~15 configuration values. If you need nested configs or slices, caarlos0/env or cleanenv are more appropriate.

## Deployment Architecture: Environment Variables in Production

For Kubernetes deployments, environment variables map naturally to ConfigMap and Secret references:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        env:
        - name: PORT
          value: "8080"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: ALLOWED_IPS
          value: "10.0.1.0/24,10.0.2.0/24"
```

All three libraries handle this pattern seamlessly — the environment variables are injected by the orchestrator and parsed by the library at startup.

## Why Self-Host Your Configuration Knowledge?

Configuration bugs are among the hardest to debug in production. A missing `DATABASE_URL` env var causes a crash loop. An unset `TIMEOUT` defaults to zero, causing every request to time out. Understanding your configuration library — how it handles defaults, validation, and precedence — prevents these failures before they reach production.

For more Go infrastructure guidance, see our comparison of [Go dependency injection containers](../2026-06-19-self-hosted-go-dependency-injection-containers-wire-fx-do/) for wiring up your application components. If you're building command-line tools, our [Go CLI libraries guide](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/) covers argument parsing and terminal UI patterns. For broader configuration management across services, we've covered [application configuration libraries across multiple languages](../2026-06-21-application-configuration-libraries-viper-koanf-configrs-typesaf/).

## FAQ

### Which library should I use for a new Go microservice?

Start with **caarlos0/env** if you only need environment variables — it handles nested structs elegantly and has zero dependencies. Choose **cleanenv** if you want config file support for local development with environment variable overrides for production. Use **envconfig** only if you have a flat config structure and value simplicity above features.

### Can I use multiple configuration sources with these libraries?

Only **cleanenv** supports hybrid config files + environment variables. With caarlos0/env and envconfig, you're limited to environment variables only. If you need a file-based config with env overrides, structure your startup to read the file first with a YAML/JSON parser, then call `env.Parse()` to merge in environment overrides.

### How do these libraries handle 12-factor app principles?

All three align with twelve-factor methodology: store config in environment variables, keep code and config separate, and use env vars for deploy-specific settings. cleanenv goes further by supporting config files for development while prioritizing env vars for production overrides, which many teams find practical.

### Are there security concerns with parsing environment variables?

Environment variables are accessible to any process with the same UID on Linux, and they appear in `/proc/<pid>/environ`. Never store long-lived secrets directly in environment variables — use a secrets manager (Vault, AWS Secrets Manager) and inject them at startup. All three libraries treat values as opaque strings — they don't log or persist anything.

### Can envconfig handle configuration for multi-tenant services?

envconfig's `Process("prefix", &cfg)` with a prefix is designed for this — different tenants can use different prefixes reading from different env var namespaces. However, for complex multi-tenant setups with hundreds of config values, caarlos0/env's nested struct support scales better.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Go Environment Configuration Libraries: caarlos0/env vs cleanenv vs envconfig",
  "description": "Comprehensive comparison of Go environment variable configuration libraries: caarlos0/env, cleanenv, and envconfig. Covers env var parsing, config file support, nested structs, default values, validation, and twelve-factor best practices.",
  "datePublished": "2026-06-23",
  "dateModified": "2026-06-23",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
