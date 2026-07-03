---
title: "Rust Configuration Libraries Compared: config vs Figment vs envy"
date: "2026-07-03"
tags: ["rust", "configuration", "config-rs", "figment", "envy", "rust-crates", "twelve-factor", "devops"]
draft: false
---

## Introduction

Configuration management is a foundational concern for any Rust application. Whether you're building a CLI tool, a web server, or a background worker, you need a reliable way to load settings from multiple sources — files, environment variables, command-line arguments — and merge them with sensible defaults. Rust's strong type system makes configuration handling particularly satisfying: configuration errors are caught at startup, not at 3 AM when a production service fails because of a missing env var. This article compares three leading Rust configuration crates: config, Figment, and envy.

## Library Comparison

| Feature | config | Figment | envy |
|---------|--------|---------|------|
| **GitHub Stars** | ~2,600 | ~700 | ~800 |
| **Developer** | mehcode | Sergio Benitez (Rocket) | softprops |
| **Config Sources** | JSON, YAML, TOML, INI, Env, CLI | JSON, YAML, TOML, Env (profiles) | Environment Variables only |
| **Layered Merging** | Yes (ordered sources) | Yes (profiles + providers) | No (single source) |
| **Struct Deserialization** | Yes (serde) | Yes (serde) | Yes (serde + custom derive) |
| **Default Values** | Via serde + set_default | Via serde + join | Via serde |
| **Nested Configuration** | Yes | Yes (profiles) | N/A (flat env vars) |
| **Hot Reload** | No | No | No |
| **Async Support** | Yes (async sources) | No | No |
| **Watch for Changes** | No | No | No |

## config: The Swiss Army Knife

config is the most widely used Rust configuration crate. It supports reading from a wide range of sources — JSON, YAML, TOML, INI, environment variables, and custom sources — and merging them in a specified priority order. It's designed for applications that need to pull settings from multiple places.

```rust
use config::{Config, File, Environment};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Settings {
    database: DatabaseSettings,
    server: ServerSettings,
    logging: LoggingSettings,
}

#[derive(Debug, Deserialize)]
struct DatabaseSettings {
    url: String,
    pool_size: u32,
}

#[derive(Debug, Deserialize)]
struct ServerSettings {
    host: String,
    port: u16,
}

#[derive(Debug, Deserialize)]
struct LoggingSettings {
    level: String,
    format: String,
}

fn load_config() -> Result<Settings, config::ConfigError> {
    let settings = Config::builder()
        // Start with defaults
        .set_default("server.host", "127.0.0.1")?
        .set_default("server.port", 8080)?
        .set_default("logging.level", "info")?
        .set_default("logging.format", "json")?
        // Override with config file
        .add_source(File::with_name("config/default"))
        // Override with environment-specific config
        .add_source(File::with_name("config/production").required(false))
        // Override with environment variables (DATABASE__POOL_SIZE format)
        .add_source(Environment::default().separator("__"))
        .build()?;

    settings.try_deserialize()
}
```

The layered approach is powerful: environment variables take highest priority (great for Docker/Kubernetes deployments), followed by environment-specific files, followed by defaults. The double-underscore separator (`DATABASE__POOL_SIZE`) is a common convention for nested env vars.

**Key strengths:** Multiple source types, ordered layering, async sources, large ecosystem adoption, excellent documentation.

## Figment: Profiles and Providers from the Rocket Ecosystem

Figment was created by Sergio Benitez for the Rocket web framework but works independently. It introduces the concept of "profiles" — named configuration sets (debug, release, staging, production) — and "providers" that supply configuration data with explicit priority.

```rust
use figment::{Figment, providers::{Json, Toml, Yaml, Env, Format}};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Config {
    database_url: String,
    redis_url: String,
    jwt_secret: String,
    workers: u32,
}

fn load_config() -> Result<Config, figment::Error> {
    Figment::new()
        .merge(("workers", 4))                  // Raw default
        .merge(("database_url", "postgres://localhost/dev"))
        .merge(Toml::file("Cargo.toml"))        // Read from Cargo.toml metadata
        .merge(Env::prefixed("APP_"))            // APP_DATABASE_URL, APP_REDIS_URL, etc.
        .merge(Json::file("config.json"))        // Override from JSON file
        .extract()
}
```

Figment's `merge()` pattern is intuitive: each call adds a new provider, and later providers override earlier ones. The `Env::prefixed("APP_")` provider maps `APP_DATABASE_URL` to `database_url`, following the Twelve-Factor App convention. Figment also supports reading from non-standard sources like `Cargo.toml` metadata, which is useful for build-time configuration.

**Key strengths:** Intuitive merge API, profile support, Rocket ecosystem integration, environment variable prefixing, readable builder pattern.

## envy: Twelve-Factor, Environment-First

envy takes the simplest approach: deserialize environment variables directly into a struct. It's designed for Twelve-Factor App deployments where all configuration comes from the environment — no config files, no merging, no layering.

```rust
use serde::Deserialize;

#[derive(Deserialize, Debug)]
struct Config {
    #[serde(default = "default_port")]
    port: u16,
    database_url: String,
    redis_url: String,
    #[serde(default = "default_workers")]
    workers: u32,
    #[serde(default)]
    enable_cache: bool,
}

fn default_port() -> u16 { 8080 }
fn default_workers() -> u32 { 4 }

fn main() -> Result<(), envy::Error> {
    let config = envy::from_env::<Config>()?;
    println!("Starting server on port {}", config.port);
    Ok(())
}
```

That's it — no builders, no file sources, no merge logic. The environment is the single source of truth. envy automatically converts `DATABASE_URL` env var to the `database_url` field (snake_case conversion), handles `Option<T>` for optional fields, and respects serde's `#[serde(default)]` for defaults.

**Key strengths:** Dead simple, zero-config approach, Twelve-Factor compliant, minimal dependencies, predictable behavior.

## Choosing Between Them: A Decision Framework

The choice depends on your deployment model:

- **Kubernetes / Docker Compose / Twelve-Factor**: envy is the natural fit. All configuration comes from environment variables injected by the orchestrator. No config files to mount, no file watching needed.

- **Monolith or CLI with multiple config sources**: config is the best choice. Its layering model handles defaults, config files, env vars, and CLI args elegantly.

- **Rocket web applications and multi-environment deployments**: Figment integrates seamlessly with Rocket and provides the profile concept that maps naturally to dev/staging/production environments.

```rust
// Pattern: Combine envy with config for the best of both worlds
use config::{Config, Environment, File};

fn load_settings() -> Result<Settings, config::ConfigError> {
    Config::builder()
        .add_source(File::with_name("config/default"))
        .add_source(File::with_name(&format!("config/{}", std::env::var("APP_ENV").unwrap_or("development".into()))).required(false))
        .add_source(Environment::default().separator("__"))
        .build()?
        .try_deserialize()
}
```

## Why Strongly-Typed Configuration Matters for Self-Hosted Deployments

Self-hosted applications often run in diverse environments — a Raspberry Pi at home, a VPS in the cloud, a Kubernetes cluster at work. Each environment has different database URLs, port assignments, and resource limits. Using strongly-typed configuration with serde means these differences are validated at startup: if `DATABASE_URL` is missing or `PORT` is not a valid integer, the application fails immediately with a clear error message rather than crashing later with an opaque runtime error.

For Rust developers building self-hosted services, well-structured configuration is the first line of defense against production incidents. Our [Rust error handling libraries guide](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/) shows how to propagate configuration errors cleanly. For data persistence, check our [Rust database libraries comparison](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/) which covers how to inject your typed config into database connection pools. For sharing your compiled Rust binaries, see our [Rust crate registry guide](../2026-06-16-self-hosted-rust-crate-registries-kellnr-alexandrie-panamax/).

## Error Handling and Validation Patterns

Strongly-typed configuration with serde catches most errors at deserialization time, but production applications need additional validation. Here are patterns that work across all three libraries:

**Post-deserialization validation:**
```rust
fn load_and_validate() -> Result<Settings, Box<dyn std::error::Error>> {
    let settings: Settings = Config::builder()
        .add_source(File::with_name("config/default"))
        .add_source(Environment::default().separator("__"))
        .build()?
        .try_deserialize()?;

    // Custom validation
    if settings.server.port < 1024 && !cfg!(target_os = "linux") {
        anyhow::bail!("Port {} requires root privileges on this OS", settings.server.port);
    }
    if settings.database.pool_size == 0 {
        anyhow::bail!("database.pool_size must be greater than 0");
    }
    Ok(settings)
}
```

**Using anyhow for ergonomic error messages:**
All three libraries produce clear error messages, but wrapping them with `anyhow::Context` adds deployment-specific context that helps operators debug configuration issues quickly:

```rust
use anyhow::Context;

let settings: Settings = config::Config::builder()
    .add_source(File::with_name("config/production"))
    .build()
    .context("Failed to load production config — check that config/production.toml exists")?
    .try_deserialize()
    .context("Failed to parse config — check for missing or mistyped fields")?;
```

**Testing with different configurations:**
For integration tests, create a `config/test.toml` with test-specific values and point your config loader at it via an environment variable. This pattern keeps tests isolated and avoids accidentally connecting to production databases during test runs.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    fn test_config() -> Settings {
        std::env::set_var("APP_ENV", "test");
        Config::builder()
            .add_source(File::with_name("config/test"))
            .build()
            .unwrap()
            .try_deserialize()
            .unwrap()
    }
}
```


## FAQ

### Can I use config and envy together?

Yes, and this is a common pattern. Use config's `Environment` source with a custom prefix to achieve envy-like behavior within config's layering model. Or use envy for the environment layer and pass the deserialized struct into config as a default. The crates are complementary, not mutually exclusive.

### How do I handle secrets (API keys, passwords) in configuration?

Never hard-code secrets in config files. Use environment variables for secrets (all three libraries support this). For production, consider a secrets manager (Hashicorp Vault, AWS Secrets Manager) and load secrets at startup via a custom config source. config supports custom `Source` implementations — you can write one that fetches from Vault. Figment supports custom `Provider` implementations for the same purpose.

### Does Figment work outside of the Rocket framework?

Absolutely. Figment is a standalone crate that happens to be maintained by the Rocket project. It has no dependency on Rocket and works well with any Rust application, including Actix-Web, Axum, and CLI tools. Its API is clean and well-documented independently of Rocket.

### How should I structure config files for different environments?

The standard approach is to have a `config/` directory with `default.toml` (base settings), and environment-specific overrides like `development.toml`, `staging.toml`, `production.toml`. Use the `APP_ENV` environment variable to select which override to load. Both config and Figment support this pattern. Your Docker Compose or Kubernetes manifests set `APP_ENV=production` and inject secrets via environment variables.

### What about configuration for CLI tools?

For CLI tools, config pairs well with `clap` for argument parsing. The typical pattern: set defaults in code, apply config file overrides, apply environment variable overrides, and apply command-line argument overrides (highest priority). config's layering model handles this naturally. Figment can also accept `clap`-derived values as a provider. envy is less suitable for CLI tools since it only reads environment variables.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Configuration Libraries Compared: config vs Figment vs envy",
  "description": "Comparison of Rust configuration management crates covering layered merging, Twelve-Factor compliance, serde integration, and best practices for self-hosted deployments.",
  "datePublished": "2026-07-03",
  "dateModified": "2026-07-03",
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
