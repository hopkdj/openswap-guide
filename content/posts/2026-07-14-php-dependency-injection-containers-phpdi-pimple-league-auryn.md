---
title: "PHP Dependency Injection Container Comparison: PHP-DI vs Pimple vs League Container vs Auryn"
date: "2026-07-14"
tags: ["php", "dependency-injection", "di-container", "php-di", "pimple", "league", "composer"]
draft: false
---

Dependency injection (DI) is the cornerstone of maintainable PHP applications. Rather than having classes construct their own dependencies, a DI container manages object creation, resolves dependency graphs, and injects configured instances. This decoupling makes code more testable, more modular, and easier to refactor. In this article, we compare four popular PHP DI containers — **PHP-DI**, **Pimple**, **League Container**, and **Auryn** — analyzing their APIs, autowiring capabilities, performance, and ideal use cases.

## Quick Comparison

| Feature | PHP-DI | Pimple | League Container | Auryn |
|---------|--------|--------|-----------------|-------|
| **GitHub Stars** | ~2.5K | ~2.6K | ~1.5K | ~700 |
| **Autowiring** | Yes (reflection-based) | No | Yes (optional, delegate lookup) | Yes (primary feature) |
| **Configuration** | PHP arrays, annotations, attributes | Closures in ArrayAccess | Service providers | No config (auto-resolves) |
| **PSR-11 Compliance** | Yes | Yes (via pimple/psr11) | Yes (primary goal) | Yes |
| **Compiled Container** | Yes (optional for production) | No | No | No |
| **Circular Dependency** | Detected and reported | Possible (via closures) | Detected and reported | Detected and reported |
| **Lazy Loading** | Yes | Yes (all services are lazy) | Yes | Yes |
| **Framework Integration** | Symfony, Laravel, Slim | Silex (discontinued) | Slim, custom frameworks | Custom applications |
| **Decorator Support** | Yes (via definitions) | Yes (via extend()) | Yes (via delegates) | No |
| **PHP Version** | 8.0+ | 7.2+ | 8.0+ | 7.0+ |

## PHP-DI: Autowiring for Everyone

PHP-DI is the most feature-complete DI container in the PHP ecosystem. It combines autowiring (automatic dependency resolution via reflection), multiple configuration formats, and a rich definition API into a single package that works as both a standalone container and a Symfony/PSR-11 provider.

### Installation

```bash
composer require php-di/php-di
```

### Basic Autowiring

PHP-DI's primary strength is that it requires zero configuration for straightforward cases:

```php
<?php
use DI\ContainerBuilder;

// Classes with type-hinted constructor parameters are auto-resolved
class DatabaseConnection
{
    public function __construct(
        private string $dsn,
        private string $username,
        private string $password
    ) {}
}

class UserRepository
{
    public function __construct(private DatabaseConnection $db) {}
    
    public function find(int $id): array
    {
        // Uses $this->db to query
        return ['id' => $id, 'name' => 'Alice'];
    }
}

class UserController
{
    public function __construct(private UserRepository $users) {}
    
    public function show(int $id): array
    {
        return $this->users->find($id);
    }
}

// With PHP-DI, you configure only primitives
$containerBuilder = new ContainerBuilder();
$containerBuilder->addDefinitions([
    'db.dsn'      => 'mysql:host=localhost;dbname=myapp',
    'db.username' => 'root',
    'db.password' => 'secret',
    DatabaseConnection::class => DI\autowire()
        ->constructorParameter('dsn', DI\get('db.dsn'))
        ->constructorParameter('username', DI\get('db.username'))
        ->constructorParameter('password', DI\get('db.password')),
]);

$container = $containerBuilder->build();

// PHP-DI resolves the entire tree: Controller → Repository → Database
$controller = $container->get(UserController::class);
var_dump($controller->show(1)); // ['id' => 1, 'name' => 'Alice']
```

### Attribute-Based Configuration (PHP 8+)

PHP-DI supports PHP 8 attributes for inline configuration:

```php
<?php
use DI\Attribute\Inject;

class MailerService
{
    #[Inject(['host' => 'smtp.example.com', 'port' => 587])]
    public function __construct(
        private string $host,
        private int $port
    ) {}
    
    public function send(string $to, string $subject, string $body): void
    {
        // Send via $this->host:$this->port
    }
}

// No manual definition needed — PHP-DI reads attributes
$mailer = $container->get(MailerService::class);
```

### Definition Overrides and Caching

For production, PHP-DI can compile the container for performance:

```php
<?php
$containerBuilder = new ContainerBuilder();

// Enable compiled container (only in production)
if (getenv('APP_ENV') === 'production') {
    $containerBuilder->enableCompilation('/tmp/php-di-cache');
}

// Write definitions once via config file
$containerBuilder->addDefinitions(__DIR__ . '/config/di.php');
$container = $containerBuilder->build();
```

### Framework Integration

PHP-DI integrates seamlessly with multiple frameworks:

```php
// Symfony integration
// composer require php-di/symfony-bridge

// Slim Framework integration
// composer require php-di/slim-bridge

// Laravel: use PHP-DI as the underlying container
// composer require php-di/laravel-bridge
```

### Pros and Cons

**Pros:**
- Zero-configuration autowiring for most use cases
- Multiple configuration formats (PHP, YAML, annotations, attributes)
- Production compilation for performance (eliminates reflection overhead)
- Rich ecosystem: Symfony, Slim, and Laravel bridges available
- PSR-11 compliant out of the box

**Cons:**
- Larger footprint than minimal containers (~100KB of source)
- Reflection-based autowiring has a cold-start cost in development (mitigated by compilation)
- Learning curve for the full definition DSL (`DI\factory()`, `DI\decorate()`, etc.)

## Pimple: The Minimalist Champion

Pimple is a tiny (~80 lines of code) DI container built around closures. Created by Fabien Potencier (the author of Symfony), it was the default container for Silex and remains popular for small applications, microservices, and situations where you prefer explicit wiring over magic.

### Installation

```bash
composer require pimple/pimple
```

### How Pimple Works

Pimple is an `ArrayAccess` implementation where each key is a closure that receives the container itself. Services are lazy — the closure only executes on first access:

```php
<?php
use Pimple\Container;

$container = new Container();

// Service definition: closures receive $c (the container)
$container['db.dsn'] = 'mysql:host=localhost;dbname=myapp';
$container['db.user'] = 'root';
$container['db.pass'] = 'secret';

$container['db'] = function (Container $c): PDO {
    return new PDO(
        $c['db.dsn'],
        $c['db.user'],
        $c['db.pass'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
};

$container['user_repository'] = function (Container $c): UserRepository {
    return new UserRepository($c['db']);
};

$container['user_controller'] = function (Container $c): UserController {
    return new UserController($c['user_repository']);
};

// Services are lazy — no PDO connection until first get()
$controller = $container['user_controller'];
$user = $controller->show(1);
```

### Service Factories (New Instance Per Call)

By default, Pimple returns the same instance on every access (shared service). For factory behavior, wrap in `$container->factory()`:

```php
<?php
$container['uuid_generator'] = $container->factory(function (Container $c) {
    return sprintf('%04x%04x-%04x-%04x-%04x-%04x%04x%04x',
        mt_rand(0, 0xffff), mt_rand(0, 0xffff),
        mt_rand(0, 0xffff),
        mt_rand(0, 0x0fff) | 0x4000,
        mt_rand(0, 0x3fff) | 0x8000,
        mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff)
    );
});

// Each call creates a new UUID
$uuid1 = $container['uuid_generator'];
$uuid2 = $container['uuid_generator'];
// $uuid1 !== $uuid2
```

### Extending Services

Pimple provides an `extend()` method for decorator patterns:

```php
<?php
$container['db'] = function (Container $c): PDO {
    return new PDO($c['db.dsn'], $c['db.user'], $c['db.pass']);
};

// Add logging to the database service without modifying the original
$container->extend('db', function (PDO $db, Container $c) {
    $db->setAttribute(PDO::ATTR_STATEMENT_CLASS, [
        LoggingPDOStatement::class, [$c['logger']]
    ]);
    return $db;
});
```

### PSR-11 Compatibility

Pimple can implement PSR-11 via the `pimple/psr11` bridge:

```php
<?php
use Pimple\Psr11\Container as PsrContainer;

$psr11 = new PsrContainer($container);
$db = $psr11->get('db');          // PSR-11::get()
$has = $psr11->has('db');          // PSR-11::has()
```

### Pros and Cons

**Pros:**
- Extremely simple — the entire source fits on a single screen
- Zero magic: every dependency is explicitly wired, making the graph visible
- Lazy by default — no work done until a service is accessed
- The `extend()` method elegantly handles decorator patterns
- Excellent for small applications where full autowiring is overkill

**Cons:**
- No autowiring — every dependency must be manually defined as a closure
- Service IDs are strings with no IDE autocompletion or type checking
- At scale, the single-file closure definitions become unwieldy
- The Silex framework (Pimple's primary use case) was discontinued

## League Container: Standards-First Design

League Container is part of The PHP League's collection of high-quality packages. It's built around the **service provider** pattern and PSR-11, combining explicit configuration with optional autowiring via delegate containers.

### Installation

```bash
composer require league/container
```

### Service Providers

League Container's key innovation is the `ServiceProviderInterface` — each service (or group of related services) is defined in its own provider class:

```php
<?php
use League\Container\Container;
use League\Container\ServiceProvider\AbstractServiceProvider;

class DatabaseServiceProvider extends AbstractServiceProvider
{
    protected array $provides = [
        'db',
        DatabaseConnection::class,
    ];

    public function register(): void
    {
        $container = $this->getContainer();

        $container->add('db.config', [
            'dsn'      => 'mysql:host=localhost;dbname=myapp',
            'username' => 'root',
            'password' => 'secret',
        ]);

        $container->add(DatabaseConnection::class, function () use ($container) {
            $config = $container->get('db.config');
            return new DatabaseConnection(
                $config['dsn'],
                $config['username'],
                $config['password']
            );
        })->setShared(true);
    }
}

class RepositoryServiceProvider extends AbstractServiceProvider
{
    protected array $provides = [
        UserRepository::class,
        OrderRepository::class,
    ];

    public function register(): void
    {
        $container = $this->getContainer();

        $container->add(UserRepository::class, function () use ($container) {
            return new UserRepository($container->get(DatabaseConnection::class));
        })->setShared(true);

        $container->add(OrderRepository::class, function () use ($container) {
            return new OrderRepository($container->get(DatabaseConnection::class));
        })->setShared(true);
    }
}

// Build the container from providers
$container = new Container();
$container->addServiceProvider(new DatabaseServiceProvider());
$container->addServiceProvider(new RepositoryServiceProvider());

// Get a fully-wired repository
$users = $container->get(UserRepository::class);
```

### Autowiring via Delegate Containers

League Container supports autowiring through an external delegate container:

```php
<?php
use League\Container\Container;
use League\Container\ReflectionContainer;

$container = new Container();

// Enable reflection-based autowiring as a fallback
$container->delegate(new ReflectionContainer(true));

// Register only the primitives — everything else auto-resolves
$container->add('db.config', [
    'dsn'      => 'mysql:host=localhost;dbname=myapp',
    'username' => 'root',
    'password' => 'secret',
]);

$container->add(DatabaseConnection::class)
    ->addArgument($container->get('db.config'))
    ->setShared(true);

// These are auto-resolved by the ReflectionContainer delegate
$repo = $container->get(UserRepository::class);    // Auto-resolved
$ctrl = $container->get(UserController::class);    // Auto-resolved
```

### Inflectors (AOP-Style Cross-Cutting)

League Container provides inflectors for applying cross-cutting concerns to all services matching a type:

```php
<?php
// Apply a setter to every instance of LoggerAwareInterface
$container->inflector(LoggerAwareInterface::class)
    ->invokeMethod('setLogger', [MonologLogger::class]);
```

### Pros and Cons

**Pros:**
- Service providers enforce clean separation of configuration
- PSR-11 compliance as a primary design goal
- Inflectors elegantly handle cross-cutting concerns
- Optional autowiring via `ReflectionContainer` delegate
- Well-documented, actively maintained by The PHP League

**Cons:**
- Service providers add boilerplate for simple applications
- Delegate autowiring can silently resolve unintended objects
- Smaller ecosystem than PHP-DI (fewer framework bridges)

## Auryn: Reflection-First Autowiring

Auryn takes autowiring to its logical extreme. It has no explicit service definitions — it reads PHP type hints, resolves the dependency tree, and injects everything automatically. Configuration is done through "rules" that tell Auryn how to handle interfaces, primitives, and special cases.

### Installation

```bash
composer require rdlowrey/auryn
```

### Pure Autowiring

```php
<?php
use Auryn\Injector;

$injector = new Injector();

// Define only the exceptions to the autowiring rule
// 1. Map an interface to a concrete implementation
$injector->alias(CacheInterface::class, RedisCache::class);

// 2. Define primitive values for named parameters
$injector->define(DatabaseConnection::class, [
    ':dsn'      => 'mysql:host=localhost;dbname=myapp',
    ':username' => 'root',
    ':password' => 'secret',
]);

// 3. Share a single instance across all dependents
$injector->share(DatabaseConnection::class);

// Everything else resolves automatically
$controller = $injector->make(UserController::class);
// Auryn recursively resolves: 
//   UserController → UserRepository → DatabaseConnection (shared) → primitives (defined above)
```

### Interface Aliasing and Delegation

Auryn's rule system handles complex wiring scenarios:

```php
<?php
$injector = new Injector();

// Map multiple implementations via aliases
$injector->alias(MailerInterface::class, SmtpMailer::class);

// Delegate complex construction to a factory
$injector->delegate(LoggerInterface::class, function () {
    $logger = new Monolog\Logger('app');
    $logger->pushHandler(new Monolog\Handler\StreamHandler('/var/log/app.log'));
    return $logger;
});

// Parameter-specific definitions (name-based matching)
$injector->define(SmtpMailer::class, [
    ':host' => 'smtp.example.com',
    ':port' => 587,
]);

// Prepare hook: post-construction callback
$injector->prepare(MailerInterface::class, function (MailerInterface $mailer, Injector $injector) {
    $mailer->setDefaultFrom('noreply@example.com');
});
```

### Pros and Cons

**Pros:**
- Minimal configuration: define only exceptions, not every class
- Recursive autowiring resolves entire dependency trees
- `prepare()` hooks for post-construction initialization
- Clean separation of configuration from class definition
- Excellent for applications with many small, type-hinted classes

**Cons:**
- No PSR-11 container wrapper (must implement separately)
- Reflective autowiring can be slow in large applications without caching
- No service provider or modular configuration pattern
- Less popular — smaller community and fewer examples online

## Choosing the Right Container

| Scenario | Recommended Container |
|----------|----------------------|
| New PHP 8+ application with Symfony or Slim | PHP-DI |
| Microservice with <20 services | Pimple |
| Multi-module application requiring service providers | League Container |
| Application with deep, complex dependency graphs | Auryn |
| Need production compilation / maximum performance | PHP-DI |
| Explicit, visible wiring preferred | Pimple |
| Cross-cutting concerns (logging, metrics) on many services | League Container |

For a broader view of PHP development tools, see our [PHP application servers comparison](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/), our [PHP ORM libraries guide](../2026-07-06-php-orm-libraries-laravel-eloquent-doctrine-propel/), and our [PHP HTTP clients comparison](../2026-07-13-php-http-clients-guzzle-saloon-httpful/).

## FAQ

### What's the difference between a service container and a service locator?

A DI container injects dependencies into your objects (typically via constructor injection). A service locator is an object you call to fetch dependencies yourself. DI containers support the "Hollywood Principle" (don't call us, we'll call you) while service locators require you to explicitly pull dependencies, creating hidden coupling. All four containers in this article are primarily DI containers, though they also expose PSR-11's `get()` and `has()` methods which can be used as a service locator if misused.

### Is autowiring slower than manual wiring?

Yes, but only marginally. Reflection to read constructor parameters takes microseconds per class. For development, the convenience is worth it. For production, PHP-DI provides a compiled container that eliminates all reflection overhead. If you're using a framework like Symfony or Laravel, the framework's own container handles this automatically.

### Can I use multiple containers in the same application?

Yes, through PSR-11's `ContainerInterface`. League Container's delegate feature is designed for this: you can have a primary container with explicit service definitions and a `ReflectionContainer` delegate for everything else. PHP-DI and Auryn can also serve as delegate containers for each other.

### How do these containers handle PHP 8's constructor property promotion?

All four containers work seamlessly with constructor property promotion (`public function __construct(private Foo $foo)`). PHP-DI and Auryn read the promoted parameters via reflection just like regular constructor parameters. Pimple and League Container receive the instance after construction, so they're agnostic to the constructor syntax.

### Does using a DI container make unit testing easier or harder?

Easier — that's the primary benefit. When dependencies are injected through the constructor, you can pass mocks or stubs in your tests without the container. The container is only used in your application's composition root (e.g., `index.php` or a bootstrap file). Your actual classes never reference the container, which is the hallmark of proper DI.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP Dependency Injection Container Comparison: PHP-DI vs Pimple vs League Container vs Auryn",
  "description": "Comprehensive comparison of PHP dependency injection containers — PHP-DI, Pimple, League Container, and Auryn — with code examples, autowiring patterns, service providers, and PSR-11 compliance.",
  "datePublished": "2026-07-14",
  "dateModified": "2026-07-14",
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
