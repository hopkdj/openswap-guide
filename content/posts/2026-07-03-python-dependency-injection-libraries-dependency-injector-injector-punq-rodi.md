---
title: "Python Dependency Injection Libraries: dependency-injector vs injector vs punq vs rodi"
date: "2026-07-03"
tags: ["python", "dependency-injection", "di-container", "inversion-of-control", "software-architecture", "python-libraries"]
draft: false
---

## Introduction

Dependency Injection (DI) is a design pattern that decouples object creation from object usage, making code more testable, maintainable, and flexible. While Python's dynamic nature means you can often get by without a formal DI container, larger applications — especially those following Clean Architecture or Domain-Driven Design — benefit significantly from structured DI. This article compares four popular Python DI libraries: dependency-injector, injector, punq, and rodi, evaluating them on API design, performance, async support, and real-world usability.

## Library Comparison at a Glance

| Feature | dependency-injector | injector | punq | rodi |
|---------|---------------------|----------|------|------|
| **GitHub Stars** | ~3,800 | ~1,200 | ~200 | ~200 |
| **Design Inspiration** | Spring/Guice | Guice (Java) | .NET DI | .NET Core DI |
| **Container Type** | Declarative + Programmatic | Declarative (Modules) | Programmatic | Programmatic |
| **Async Support** | Yes (providers) | No | No | Yes (native) |
| **Singleton Scoping** | Yes | Yes | Yes | Yes |
| **Scoped/Request Lifecycle** | Yes | Yes | Via Factory | Yes |
| **Configuration Integration** | Yes (YAML/INI) | No | No | No |
| **Type Hints Support** | Partial | Yes | Yes | Yes |
| **Overhead (import time)** | ~5-10ms | ~2-5ms | ~1-3ms | ~1-3ms |
| **Python Version** | 3.7+ | 3.7+ | 3.8+ | 3.7+ |

## dependency-injector: The Enterprise-Grade Solution

dependency-injector is the most feature-complete DI framework for Python. It provides containers, providers, and declarative wiring that mirrors patterns familiar to Spring and Guice developers. It supports singleton, factory, and delegated providers, along with configuration injection from YAML, INI, and environment variables.

```python
from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    db_engine = providers.Singleton(
        create_engine,
        config.database.url,
    )
    
    db_session = providers.Factory(
        sessionmaker,
        bind=db_engine,
    )
    
    user_repository = providers.Factory(
        UserRepository,
        session=db_session,
    )
    
    user_service = providers.Factory(
        UserService,
        repository=user_repository,
    )

# Application bootstrap
container = Container()
container.config.from_dict({
    "database": {
        "url": "postgresql://user:pass@localhost:5432/mydb"
    }
})

user_service = container.user_service()
```

The `providers` system is powerful: `Singleton` caches one instance, `Factory` creates a new instance on each call, `Callable` wraps any callable, and `Resource` manages initialization and shutdown (great for database connections). You can even override providers in tests by inheriting from a base container.

**Key strengths:** Rich provider types, configuration integration, resource lifecycle management, wiring of large applications with hundreds of dependencies.

## injector: Guice-Inspired Minimalism

injector brings Google Guice's module-based approach to Python. You define bindings in `Module` classes, and the injector resolves them at runtime. It relies heavily on type hints and decorators for wiring.

```python
from injector import inject, Module, provider, singleton, Injector

class DatabaseModule(Module):
    @singleton
    @provider
    def provide_engine(self) -> Engine:
        return create_engine("postgresql://user:pass@localhost:5432/mydb")
    
    @provider
    def provide_session(self, engine: Engine) -> Session:
        return sessionmaker(bind=engine)()

class UserRepository:
    @inject
    def __init__(self, session: Session):
        self.session = session

class UserService:
    @inject
    def __init__(self, repository: UserRepository):
        self.repository = repository

# Bootstrap
injector = Injector([DatabaseModule()])
user_service = injector.get(UserService)
```

injector's design is clean and minimal — there's no explicit container, no provider factories to configure. Dependencies are resolved by matching argument type hints to registered bindings. The `@inject` decorator marks constructors that should be auto-wired, and `@provider` methods supply bound types.

**Key strengths:** Simple API, Guice-like mental model, automatic type resolution, minimal boilerplate.

## punq: .NET-Style DI with Type Registration

punq brings a Microsoft.Extensions.DependencyInjection-style API to Python. You register services by type with specific lifetimes, and the container resolves them. It's purely programmatic and very explicit.

```python
import punq

container = punq.Container()

# Register services
container.register(Engine, factory=lambda: create_engine("postgresql://..."))
container.register(Session, factory=lambda: sessionmaker(bind=container.resolve(Engine))())
container.register(UserRepository)
container.register(UserService)

# Resolve
user_service = container.resolve(UserService)
```

punq is refreshingly straightforward: register types, resolve types. It supports `singleton`, `scoped` (per-resolution-graph), and `transient` lifetimes. It also supports generic type registration (`List[T]`, `Optional[T]`) and can auto-register concrete types that have resolvable constructors.

**Key strengths:** Simple mental model, .NET developer familiarity, lightweight, generic type support.

## rodi: Async-First, Modern Python DI

rodi is designed for modern async Python applications. It supports both sync and async resolution, automatic constructor inspection, and a clean decorator-free API. It's particularly well-suited for FastAPI and async web applications.

```python
from rodi import Container

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

# Build container
container = Container()
container.add_scoped_by_factory(
    lambda: sessionmaker(bind=create_engine("postgresql://..."))()
)

# Automatic registration by type scanning
container.add_transient(UserRepository)
container.add_transient(UserService)

# Resolve
user_service = container.resolve(UserService)
```

rodi supports `transient`, `scoped`, and `singleton` lifetimes, plus an `alias` mechanism for binding interfaces to implementations. Its async-aware design means you can register async factory functions, and the container will properly await them during resolution when used in an async context.

**Key strengths:** Async-native design, no decorators needed, automatic type resolution, FastAPI integration.

## Practical Patterns: Testing with DI

DI's primary benefit is testability. Here's how testing looks across all four libraries with a common pattern:

```python
# Using dependency-injector — override providers
class TestContainer(Container):
    pass

container = TestContainer()
container.db_session.override(MockSession())
# Tests use overridden container

# Using injector — pass test module
class TestModule(Module):
    @provider
    def provide_session(self) -> Session:
        return MockSession()

injector = Injector([TestModule()])

# Using punq — re-register
container = punq.Container()
container.register(Session, instance=MockSession())

# Using rodi — override
container = Container()
container.add_instance(MockSession(), Session)
```

All four libraries make testing straightforward by allowing you to swap real implementations for mocks or stubs without modifying production code.

## Why Your Python Project Needs a DI Container

As Python applications grow beyond simple scripts, managing dependencies manually becomes a maintenance burden. Without DI, you end up with imports scattered across modules, hard-coded database connections, and global state that makes testing difficult. A DI container centralizes all wiring in one place — typically your application's composition root.

For data-heavy self-hosted applications, DI containers make it trivial to swap between database backends (SQLite for development, PostgreSQL for production) without touching business logic. They also enable clean separation between configuration (environment variables, config files), infrastructure (database connections, caches, message queues), and domain logic.

For more on structuring Python applications, see our [Python ORM libraries comparison](../2026-07-01-python-orm-libraries-sqlalchemy-peewee-tortoise-ponyorm-sqlmodel/) which pairs well with DI for data access. For structured data handling, check our [Python data class libraries guide](../2026-07-03-python-data-class-libraries-dataclasses-attrs-pydantic-cattrs/). If your services need observability, our [Python logging libraries comparison](../2026-07-01-python-logging-libraries-loguru-structlog-logbook-jsonlogger-picologging/) covers structured logging with DI integration patterns.

## Integration with Python Web Frameworks

Each DI library integrates differently with popular Python web frameworks. Here is how to wire them into FastAPI, Flask, and Django:

**FastAPI + dependency-injector:**
```python
from fastapi import FastAPI, Depends
from dependency_injector.wiring import inject, Provide

app = FastAPI()
container = Container()
container.wire(modules=[__name__])

@app.get("/api/users")
@inject
async def get_users(service: UserService = Depends(Provide[Container.user_service])):
    return await service.get_all()
```

**Flask + rodi:**
```python
from flask import Flask
from rodi import Container

app = Flask(__name__)
container = Container()
container.add_singleton(UserService)

@app.route("/api/users")
def get_users():
    service = container.resolve(UserService)
    return service.get_all()
```

**Django + injector:**
Django's class-based views work well with injector's module system. Register your services in a Django `AppConfig.ready()` method, and use a custom mixin that calls `injector.get()` in the view's `__init__`. This keeps Django's ORM and injector's DI container cleanly separated — each manages its own concern.


## FAQ

### Do I really need a DI container in Python?

For small scripts and simple applications, no. Python's dynamic nature means you can often inject dependencies manually — passing database sessions as function arguments, using module-level singletons, or relying on context managers. DI containers become valuable when your application has 20+ services with complex dependency graphs, when you need request-scoped lifecycles (e.g., one database session per HTTP request), or when you want to swap implementations for testing without patching.

### How does DI work with async Python frameworks like FastAPI?

Most DI libraries integrate with FastAPI through FastAPI's own dependency injection system (`Depends`). rodi has the best async support natively. dependency-injector provides async resource providers. The common pattern is to use FastAPI's `Depends` for request-scoped dependencies and a DI container for application-level singletons. FastAPI's `app.dependency_overrides` dictionary can also swap dependencies in tests.

### Which library has the smallest performance overhead?

punq and rodi are the lightest at runtime, with negligible resolution overhead (<1ms for typical graphs). dependency-injector adds a small overhead due to its provider proxy system (~2-5ms for first resolution). injector's overhead is similar. In practice, DI resolution time is dwarfed by I/O operations (database queries, HTTP calls), so performance differences between libraries rarely matter in production.

### Can I mix DI containers with FastAPI's built-in Depends?

Yes — this is a common pattern. Use FastAPI's `Depends` for request-scoped, per-endpoint dependencies, and use a DI container for application-level singletons (database engine, configuration, service classes). The container can be attached to `app.state` and accessed in endpoint functions. This gives you the best of both worlds: FastAPI's ergonomic request injection and a container's centralized composition.

### What if I need to inject dependencies into a class that I don't control?

All four libraries support factory-based injection: instead of registering the class itself, you register a factory function that constructs the object with injected dependencies. For example, with sqlalchemy sessions, you'd register a factory that creates a `sessionmaker` bound to an injected `Engine`, rather than trying to inject into SQLAlchemy classes directly.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python Dependency Injection Libraries: dependency-injector vs injector vs punq vs rodi",
  "description": "In-depth comparison of four Python dependency injection libraries for building maintainable, testable applications with Clean Architecture and Domain-Driven Design patterns.",
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
