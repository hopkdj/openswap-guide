---
title: "Self-Hosted Python Configuration Libraries: Pydantic Settings vs Dynaconf vs python-decouple vs environs — Complete Guide 2026"
date: "2026-06-22"
tags: ["python", "configuration", "settings", "libraries", "developer-tools", "env-management", "12-factor"]
draft: false
---

## Introduction

Every Python application — whether a Django monolith, a FastAPI microservice, or a CLI tool — needs configuration. The Twelve-Factor App methodology prescribes storing configuration in environment variables, but raw `os.getenv()` calls with manual type coercions become unmaintainable quickly. The Python ecosystem has evolved four mature libraries that bring structure to configuration management: **Pydantic Settings** (type-validated, model-based), **Dynaconf** (multi-source, layered), **python-decouple** (lightweight, env-focused), and **environs** (marshmallow-powered, Flask-friendly).

This guide compares all four with realistic examples that go beyond "hello world" to show how production teams manage configuration across development, staging, and production.

## Library Overview

| Feature | Pydantic Settings | Dynaconf | python-decouple | environs |
|---------|------------------|----------|----------------|----------|
| **GitHub Stars** | 1,365 | 4,305 | 3,039 | 1,367 |
| **Approach** | Pydantic model with validation | Multi-source layered config | Simple .env + casting | Marshmallow schema-based |
| **Type Validation** | Full Pydantic validation | Type casting, validation hooks | Basic casting helpers | Marshmallow field types |
| **Config Sources** | .env, env vars, secrets | .env, .toml, .yaml, .json, .ini, Redis, Vault | .env, .ini | .env, env vars |
| **Nested Config** | Yes (nested models) | Yes (dotted keys) | No | Yes (prefix nesting) |
| **Secrets Support** | SecretsDir, AWS Secrets | Vault, Redis, custom loaders | No | No |
| **Django Integration** | Via pydantic-settings | Native `django-dynaconf` | Via `django-decouple` | Via env vars |
| **Active Maintained** | Yes (June 2026) | Yes (June 2026) | Moderate (Nov 2024) | Yes (June 2026) |

## Pydantic Settings: Type-Validated Configuration Models

[Pydantic Settings](https://github.com/pydantic/pydantic-settings) extends Pydantic's data validation to application configuration. If you already use Pydantic for request/response schemas (FastAPI, Litestar, etc.), configuration models feel natural.

**Installation:**

```bash
pip install pydantic-settings
```

**Basic Usage:**

```python
from pydantic import Field, SecretStr, RedisDsn, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "MyApp"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    db_pool_size: int = 20
    db_pool_timeout: int = 30

    # Redis
    redis_url: RedisDsn = "redis://localhost:6379/0"

    # Secrets
    api_key: SecretStr
    jwt_secret: SecretStr

    # Nested config
    email_settings: "EmailSettings"

class EmailSettings(BaseSettings):
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None

# Loading is one line
settings = Settings()

# Fully typed access
print(settings.database_url.host)      # parsed URL object
print(settings.api_key.get_secret_value())  # explicit secret access
settings.email_settings.smtp_port      # nested config
```

**Key advantages:**
- **Full Pydantic validation**: Custom validators, `AfterValidator`, discriminated unions — all Pydantic features work on config
- **Secret handling**: `SecretStr` / `SecretBytes` mask values in `repr()` and `model_dump()`
- **Nested models**: Group related configuration into sub-models for clean separation
- **Computed fields**: Derive config values from other settings with `@computed_field`

**Multi-environment example:**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{os.getenv('ENV', 'development')}"),
    )
    database_url: str
    sentry_dsn: AnyUrl | None = None
    environment: str = "development"

# .env.production overrides .env defaults when ENV=production
```

## Dynaconf: Multi-Source Layered Configuration

[Dynaconf](https://github.com/dynaconf/dynaconf) is the Swiss Army knife of Python configuration. It reads from `.env`, `.toml`, `.yaml`, `.json`, `.ini`, Redis, HashiCorp Vault, and more — **all simultaneously, with a well-defined precedence order**.

**Installation:**

```bash
pip install dynaconf
```

**Basic Usage (`config.py`):**

```python
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="MYAPP",
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    load_dotenv=True,
)

# Access anywhere
print(settings.DATABASE_URL)
print(settings.get("redis.url", "redis://localhost:6379"))
```

**`settings.toml`:**

```toml
[default]
app_name = "MyApp"
debug = false
database_url = "postgresql://localhost/dev"

[development]
debug = true
database_url = "postgresql://localhost/dev"

[production]
debug = false
database_url = "postgresql://user:pass@prod-host:5432/db"

[production.redis]
url = "redis://prod-redis:6379/0"
pool_size = 50
```

**Switching environments:**

```bash
# Development (default)
python app.py

# Production
ENV_FOR_DYNACONF=production python app.py
# or
export MYAPP_ENV=production && python app.py
```

**External sources:**

```python
# Redis configuration store
settings = Dynaconf(
    environments=True,
    redis_enabled=True,
    redis_host="config-redis.internal",
    redis_port=6379,
)

# Vault secrets
settings = Dynaconf(
    vault_enabled=True,
    vault_url="https://vault.internal:8200",
    vault_token=os.getenv("VAULT_TOKEN"),
)
```

**Key advantages:**
- **Multi-format**: TOML (recommended), YAML, JSON, INI, .env — all simultaneously
- **Layered environments**: `[default]` → `[development]` → `[local]` → env vars — predictable precedence
- **External backends**: Redis, Vault, Consul, etcd for centralized configuration
- **Django/Flask integration**: Official extensions for both frameworks
- **Validation hooks**: `settings.validators.register()` for runtime validation

## python-decouple: Lightweight Env-Centric

[python-decouple](https://github.com/henriquebastos/python-decouple) is the minimalist's choice. It does one thing well: read configuration from `.env` files and environment variables with type casting — no models, no fancy backends, no dependencies beyond the standard library.

**Installation:**

```bash
pip install python-decouple
```

**Basic Usage:**

```python
from decouple import config, Csv

DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost", cast=Csv())
DATABASE_URL = config("DATABASE_URL", default="sqlite:///db.sqlite3")
MAX_CONNECTIONS = config("MAX_CONNECTIONS", default=100, cast=int)
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
CACHE_TIMEOUT = config("CACHE_TIMEOUT", default=3600, cast=int)
```

**`.env` file:**

```
DEBUG=True
SECRET_KEY=my-secret-key-change-me
ALLOWED_HOSTS=example.com,api.example.com,localhost
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
MAX_CONNECTIONS=50
```

**`.ini` file support:**

```ini
[settings]
DEBUG=True
SECRET_KEY=my-secret-key-change-me
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

```python
from decouple import Config, RepositoryIni
ini_config = Config(RepositoryIni("settings.ini"))
DEBUG = ini_config("DEBUG", cast=bool)
```

**Key advantages:**
- **Zero learning curve**: `config('KEY', default=val, cast=type)` — that is the entire API
- **No dependencies**: Pure Python standard library
- **Django-friendly**: Used by Django projects that outgrow `settings.py` hardcoding
- **Fast**: Minimal overhead — just string reads and type casts

**Key disadvantages:**
- **No nested config**: Flat key-value only — no structured or hierarchical configuration
- **No validation**: Type casting is not validation — `config('PORT', cast=int)` accepts negative numbers
- **Limited sources**: Only `.env` and `.ini` files, no YAML/TOML/Vault

## environs: Marshmallow Schema-Based

[environs](https://github.com/sloria/environs) is built on top of Marshmallow, bringing schema-based configuration parsing with rich field types. It is particularly popular in the Flask ecosystem since it shares Marshmallow's validation patterns.

**Installation:**

```bash
pip install environs
```

**Basic Usage:**

```python
from environs import Env

env = Env()
env.read_env()  # reads .env

# Simple access with casting
DEBUG = env.bool("DEBUG", default=False)
PORT = env.int("PORT", default=8000)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])
DATABASE_URL = env.dj_db_url("DATABASE_URL", default="sqlite:///db.sqlite3")
REDIS_URL = env.url("REDIS_URL", default="redis://localhost:6379/0")
LOG_LEVEL = env.log_level("LOG_LEVEL", default="INFO")
```

**Schema-based (Marshmallow):**

```python
from marshmallow import fields, validate
from environs import Env

env = Env()
env.read_env()

# Nested prefix-based config
with env.prefixed("DB_"):
    db_config = {
        "host": env.str("HOST", default="localhost"),
        "port": env.int("PORT", default=5432),
        "user": env.str("USER", default="postgres"),
        "password": env.str("PASSWORD"),
    }

with env.prefixed("REDIS_"):
    redis_config = {
        "url": env.url("URL", default="redis://localhost:6379/0"),
        "max_connections": env.int("MAX_CONNECTIONS", default=20),
    }

# .env file:
# DB_HOST=prod-db.internal
# DB_PORT=5432
# DB_USER=app_user
# DB_PASSWORD=secure-pass
# REDIS_URL=redis://cache.internal:6379/1
```

**Key advantages:**
- **Rich field parsers**: `env.dj_db_url()`, `env.dj_email_url()`, `env.dj_cache_url()` for Django-style URLs
- **Prefix grouping**: `env.prefixed("DB_")` naturally groups related settings
- **Marshmallow integration**: Use full Marshmallow schemas for complex validation
- **Flask-native**: Pairs perfectly with Flask's app factory pattern

## Choosing the Right Configuration Library

**Choose Pydantic Settings if:**
- You already use Pydantic (FastAPI, Litestar, SQLModel, LangChain)
- You need strict type validation at startup (fail fast on bad config)
- You manage secrets with `SecretStr` and want them masked in logs
- Your configuration has nested structures (databases, caches, third-party APIs)

**Choose Dynaconf if:**
- You need to read from multiple sources (TOML for code, env vars for secrets, Redis for dynamic config)
- You manage multiple deployment environments with layered overrides
- You need centralized configuration via Redis or Vault
- You want Django/Flask drop-in integration

**Choose python-decouple if:**
- You need the simplest possible solution — one file, no dependencies
- Your configuration is flat (10–30 key-value pairs)
- You are working on a small to medium Django project
- You value minimalism and zero magic over features

**Choose environs if:**
- You use Flask and want Marshmallow-compatible validation
- You prefer prefix-based nested configuration
- You need Django-style URL parsers for databases, caches, and email backends
- Your team is comfortable with Marshmallow's field patterns

## Production Patterns

**Pydantic Settings with multiple env files:**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.shared", ".env.secrets", f".env.{ENVIRONMENT}"),
        env_nested_delimiter="__",
    )
    database: DatabaseSettings
    redis: RedisSettings

# Access: settings.database.url (from DB__URL=... in env)
```

**Dynaconf with validation hooks:**

```python
from dynaconf import Validator

settings.validators.register(
    Validator("DATABASE_URL", must_exist=True),
    Validator("DEBUG", is_type_of=bool),
    Validator("PORT", gte=1024, lte=65535),
    Validator("SECRET_KEY", len_min=32),
)
settings.validators.validate()
```

For related reading on configuration management, see our [C++ Configuration Libraries guide](../2026-06-22-cpp-configuration-management-libraries-toml11-yamlcpp-tomlplusplus-libconfig/) which covers the same problem in the C++ ecosystem. For infrastructure-level configuration management, see our [CMDB tools comparison](../2026-05-02-self-hosted-cmdb-configuration-management-database-tools-guide/). If you are managing secrets and credentials, our [Secrets Configuration Management guide](../2026-05-07-self-hosted-secrets-configuration-management-keyshade-vs-chamber-vs-vaultwarden-guide/) covers HashiCorp Vault alternatives.

## FAQ

### Which configuration library follows the Twelve-Factor App methodology best?

All four support environment variables as the primary configuration source. Pydantic Settings and Dynaconf are closest to the spirit of Twelve-Factor because they encourage a strict separation of config from code with validation. python-decouple is the most literal implementation — it is essentially a typed wrapper around env vars.

### How do I handle secrets securely with these libraries?

Pydantic Settings uses `SecretStr` which masks values in `repr()`, `str()`, and `model_dump()`. Dynaconf supports HashiCorp Vault natively and can load `.secrets.toml` files excluded from version control. python-decouple and environs rely on `.env` files excluded via `.gitignore`. Never commit `.env` files with real credentials to version control.

### Can I use multiple configuration sources simultaneously?

Dynaconf is designed for this — you combine TOML files, environment variables, and Redis/Vault with a configurable precedence order. Pydantic Settings can load multiple `.env` files with the `env_file=(".env", ".env.local")` pattern but does not natively support Redis or Vault.

### Which library handles nested configuration best?

Pydantic Settings supports nested Pydantic models, letting you group `DatabaseSettings`, `CacheSettings`, and `EmailSettings` as sub-models with their own validation. Dynaconf supports nested keys via TOML sections and dotted key access. environs uses `env.prefixed("DB_")` for flat prefix grouping. python-decouple does not support nesting.

### What about configuration reloading at runtime?

Dynaconf supports reloading: `settings.reload()` re-reads all sources. It also supports `settings.configure(FORCE_DYNACONF_LOADING_FOR_TEST=true)` for test overrides. The other three libraries load configuration once at startup — for runtime changes, you would need to implement a custom reload mechanism or restart the process.

### How do I test code that depends on configuration?

All four libraries support test overrides. Pydantic Settings and Dynaconf support temporary overrides via context managers. python-decouple allows passing a custom `RepositoryEnv` pointing to a test `.env` file. environs supports creating an `Env` instance with no `.env` file and setting values directly. The Twelve-Factor recommendation is to pass config via environment variables in CI/CD pipelines.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Python Configuration Libraries: Pydantic Settings vs Dynaconf vs python-decouple vs environs — Complete Guide 2026",
  "description": "Comprehensive comparison of Python configuration management libraries: Pydantic Settings (type-validated models), Dynaconf (multi-source layered config), python-decouple (lightweight env casting), and environs (Marshmallow schema-based). Includes production patterns and Twelve-Factor App guidance.",
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
