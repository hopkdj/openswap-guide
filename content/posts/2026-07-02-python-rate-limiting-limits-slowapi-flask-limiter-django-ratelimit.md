---
title: "Self-Hosted Python Rate Limiting: limits vs slowapi vs flask-limiter vs django-ratelimit"
date: "2026-07-02"
tags: ["python", "rate-limiting", "web-development", "api", "flask", "django", "fastapi", "performance", "security"]
draft: false
---

## Introduction

Rate limiting is a critical defense mechanism for web applications. Without it, your API endpoints are vulnerable to brute-force attacks, credential stuffing, resource exhaustion, and runaway automation. A well-implemented rate limiter protects your infrastructure while ensuring fair access for legitimate users.

Python's web ecosystem offers several purpose-built rate limiting libraries, each with different backends, integration patterns, and throttling strategies. This guide compares five leading solutions: **limits** (the flexible core library), **slowapi** (FastAPI/Starlette integration), **Flask-Limiter** (Flask-specific), **Django Ratelimit** (Django decorators), and **ratelimit** (the lightweight decorator).

## Comparison Table

| Feature | limits | slowapi | Flask-Limiter | django-ratelimit | ratelimit |
|---------|--------|---------|---------------|------------------|-----------|
| **Framework** | Agnostic | FastAPI/Starlette | Flask | Django | Agnostic |
| **Backends** | Redis, Memcached, MongoDB, In-Memory | Inherits from limits | Redis, Memcached, In-Memory, DynamoDB | Cache framework | Time-based |
| **Strategies** | Fixed Window, Sliding Window, Token Bucket, Leaky Bucket | Same as limits | Fixed Window, Moving Window | Fixed Window, Per-IP, Per-User | Fixed Window (time-based) |
| **GitHub Stars** | ~4,500 | ~2,000 | ~1,100 | ~1,000 | ~300 |
| **Per-Route Config** | Yes (via decorator) | Yes | Yes | Yes | Yes |
| **Custom Key Func** | Yes | Yes | Yes | Yes | No |
| **Headers** | Customizable | RateLimit-* headers | X-RateLimit-* headers | No | No |
| **Cost-Based** | Yes | Yes | Yes | No | No |
| **Async Support** | Yes | Yes | Limited | Async via 4.2+ | No |
| **Best For** | Custom integrations | FastAPI/ASGI apps | Flask APIs | Django projects | Simple scripts |

## limits: The Core Rate Limiting Library

`limits` is the foundational library that powers most Python rate limiting implementations. It's backend-agnostic, supporting Redis, Memcached, MongoDB, and in-memory storage, and implements all major rate limiting algorithms.

**Installation with Redis backend:**

```bash
pip install limits[redis]
```

**Basic Usage:**

```python
from limits import storage, strategies, parse

# Configure storage backend (Redis recommended for production)
redis_uri = "redis://localhost:6379/0"
store = storage.RedisStorage(redis_uri)
strategy = strategies.MovingWindowRateLimiter(store)

# Check if a request is allowed
rate = parse("100 per minute")
client_id = "user:12345"

if strategy.hit(rate, client_id):
    # Allow the request
    process_request()
else:
    # Return 429 Too Many Requests
    raise HTTPException(status_code=429)
```

`limits` supports four core algorithms:

- **Fixed Window**: `"100 per hour"` — Simple counter resetting at interval boundaries
- **Sliding Window**: `"100 per hour; moving window"` — More accurate, prevents boundary spikes
- **Token Bucket**: `"100 per hour; token bucket"` — Allows bursts while enforcing average rate
- **Leaky Bucket**: Sets a maximum processing rate, queuing excess requests

```python
# Token bucket with burst support
rate = parse("100 per second; token bucket")

# Cost-based limiting (expensive operations cost more)
strategy.hit(rate, "user:12345", cost=5)  # This API call costs 5 tokens
```

## slowapi: FastAPI Integration

slowapi builds on `limits` to provide seamless FastAPI and Starlette integration. It adds middleware-level rate limiting, automatic response headers, and per-endpoint configuration.

**Installation:**

```bash
pip install slowapi
```

**FastAPI Integration:**

```python
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/users")
@limiter.limit("5/minute")
async def get_users(request: Request):
    return {"users": [...]}

@app.get("/heavy")
@limiter.limit("2/minute", cost=3)  # Expensive endpoint costs more
async def heavy_computation(request: Request):
    return {"result": "..."}

# Per-user rate limiting
async def get_user_id(request: Request):
    return request.headers.get("X-User-ID", "anonymous")

@app.get("/protected")
@limiter.limit("100/hour", key_func=get_user_id)
async def protected_endpoint(request: Request):
    return {"data": "..."}
```

slowapi automatically adds `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` headers to responses, making it easy for clients to respect rate limits without parsing API documentation.

## Flask-Limiter: Flask-Specific Solution

Flask-Limiter provides idiomatic Flask integration with decorator-based rate limiting, configurable error responses, and built-in admin monitoring.

**Installation:**

```bash
pip install flask-limiter[redis]
```

**Configuration:**

```python
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379/0",
)

@app.route("/api/data")
@limiter.limit("10 per minute")
def get_data():
    return {"data": "..."}

# Exempt specific routes
@app.route("/health")
@limiter.exempt
def health_check():
    return {"status": "ok"}

# Dynamic limits based on request context
def get_user_limit():
    return get_current_user().rate_limit

@app.route("/api/premium")
@limiter.limit(get_user_limit)
def premium_endpoint():
    return {"premium_data": "..."}
```

Flask-Limiter also supports blueprints, conditional rate limiting, and shared limits across multiple routes:

```python
# Shared limit across related endpoints
shared_limit = limiter.shared_limit("100/hour", scope="api_read")

@shared_limit
@app.route("/api/posts")
def get_posts():
    ...

@shared_limit
@app.route("/api/comments")
def get_comments():
    ...

# Admin dashboard for monitoring
# Access via Flask-Limiter's built-in admin blueprint
```

## django-ratelimit: Django Native

django-ratelimit integrates deeply with Django's request cycle, providing class-based views mixins, function-based view decorators, and admin integration.

**Installation:**

```bash
pip install django-ratelimit
```

**Configuration (settings.py):**

```python
# Set cache backend (Redis recommended for production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

**Usage:**

```python
from django_ratelimit.decorators import ratelimit
from django_ratelimit.mixins import RatelimitMixin
from django.views.generic import View
from django.http import JsonResponse

# Function-based view
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def login_view(request):
    return JsonResponse({'status': 'ok'})

# Class-based view with mixin
class ApiView(RatelimitMixin, View):
    ratelimit_key = 'user'
    ratelimit_rate = '100/h'
    ratelimit_method = ['GET', 'POST']
    ratelimit_block = True

    def get(self, request):
        return JsonResponse({'data': '...'})

# Custom key functions
def user_or_ip(group, request):
    if request.user.is_authenticated:
        return str(request.user.pk)
    return request.META['REMOTE_ADDR']

@ratelimit(key=user_or_ip, rate='50/m', block=True)
def custom_limited_view(request):
    ...
```

## ratelimit: Simple Decorator for Scripts

For simple scripts and CLI tools, `ratelimit` provides a zero-dependency decorator with time-based limits:

```bash
pip install ratelimit
```

```python
from ratelimit import limits, sleep_and_retry

import time

# 15 calls per minute
@sleep_and_retry
@limits(calls=15, period=60)
def call_external_api(endpoint):
    response = requests.get(f"https://api.example.com/{endpoint}")
    return response.json()

# No burst: evenly space calls
@sleep_and_retry
@limits(calls=10, period=60)
def scrape_page(url):
    return fetch_page(url)
```

While simpler than the other options, `ratelimit` is ideal for data pipeline scripts, web scrapers, and any Python script that needs to respect external API rate limits.

## Deployment Architecture

For production deployments, Redis is the recommended backend for all libraries. It provides atomic operations, persistence, and can be shared across multiple application instances for consistent rate limiting across a cluster.

**Docker Compose setup with Redis:**

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

  fastapi-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  redis_data:
```

## Why Self-Host Your Rate Limiting?

Self-hosting rate limiting gives you complete control over your API's security posture. Unlike SaaS API management platforms that charge per request and store your traffic patterns on their infrastructure, self-hosted solutions run entirely within your environment. You own the data, control the algorithms, and pay only for the compute you use.

Rate limiting is also a critical complement to other Python development practices. Our guides on [Python type checking](../2026-07-02-python-type-checkers-mypy-pyright-pyre-pytype-beartype/), [Python logging libraries](../2026-07-01-python-logging-libraries-loguru-structlog-logbook-jsonlogger-picologging/), and [Python ORM libraries](../2026-07-01-python-orm-libraries-sqlalchemy-peewee-tortoise-ponyorm-sqlmodel/) together form a complete quality and security toolkit for Python web applications.

For profiling and performance optimization, see our [Python profiling tools guide](../2026-06-22-python-profiling-tools-py-spy-pyinstrument-scalene-austin/). Combined with rate limiting, you can build APIs that are both fast and resilient.

## FAQ

### Which rate limiting algorithm should I use?

**Fixed Window** is simplest but suffers from boundary spikes (all requests at 11:59 and 12:01 bypassing a "100/hour" limit). **Sliding Window** (Moving Window) eliminates boundary spikes and is the best default. **Token Bucket** is ideal when you want to allow bursts while maintaining an average rate. Use Token Bucket for APIs where occasional bursts are acceptable.

### Why use Redis instead of in-memory storage?

In-memory storage works for single-process applications but fails in multi-worker or multi-server deployments. Two application servers behind a load balancer would each maintain separate counters, effectively doubling the allowed rate. Redis provides a single source of truth accessible by all instances.

### How do I handle rate limiting for authenticated vs. anonymous users?

Use different key functions. For authenticated users, use the user ID as the key (more generous limits). For anonymous users, use the IP address (stricter limits). All five libraries support custom key functions. Example with slowapi:

```python
async def auth_aware_key(request):
    if hasattr(request, 'user') and request.user.is_authenticated:
        return f"user:{request.user.id}"
    return f"ip:{request.client.host}"
```

### What headers should my API return?

Return `X-RateLimit-Limit` (total allowed), `X-RateLimit-Remaining` (calls left in window), `X-RateLimit-Reset` (Unix timestamp when window resets), and optionally `Retry-After` on 429 responses. slowapi and Flask-Limiter include these automatically. For custom implementations with `limits`, add them manually.

### Can I use rate limiting for queue fairness?

Yes. Token Bucket algorithms are particularly good for queue fairness — each consumer gets a consistent token allocation regardless of other consumers' activity. Combine with per-customer key functions to guarantee each customer gets their fair share of API capacity without being crowded out by heavier users.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Python Rate Limiting: limits vs slowapi vs flask-limiter vs django-ratelimit",
  "description": "Comprehensive comparison of Python rate limiting libraries — limits, slowapi, Flask-Limiter, django-ratelimit, and ratelimit — covering algorithms, backends, framework integration, and production deployment patterns.",
  "datePublished": "2026-07-02",
  "dateModified": "2026-07-02",
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
