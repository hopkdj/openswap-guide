---
title: "PHP HTTP Client Libraries: Guzzle vs Saloon vs Httpful — Which One for Your API Integration?"
date: "2026-07-13"
tags: ["php", "http-client", "guzzle", "saloon", "httpful", "api-integration", "backend", "rest-api"]
draft: false
---

Every PHP application that talks to external services needs an HTTP client. Whether you're calling REST APIs, downloading files, or sending webhook payloads, the quality of your HTTP client library directly impacts reliability, error handling, and developer productivity.

PHP has a rich ecosystem of HTTP client libraries, but three stand out: **Guzzle** — the de facto standard used by Laravel, Symfony, and AWS SDK; **Saloon** — a modern, class-based API integration framework; and **Httpful** — a lightweight, readable HTTP client for simple needs.

In this guide, we compare these three libraries across features, ergonomics, middleware support, and production readiness to help you choose the right HTTP client for your PHP application.

## Library Overview

| Feature | Guzzle | Saloon | Httpful |
|---------|--------|--------|---------|
| **GitHub Stars** | ~23K | ~5K | ~2.5K |
| **PSR-18 Compliant** | Yes (guzzlehttp/psr7) | Via Guzzle adapter | Yes |
| **Async Support** | Full (promises, curl multi) | No (sync only) | No |
| **Middleware** | HandlerStack + middleware | Plugins + pipeline | Hooks |
| **Request/Response Body** | Streams (PSR-7) | PSR-7 streams | String only |
| **Testing/Mocking** | MockHandler | Built-in FakeSender | None |
| **Retry Support** | Via retry middleware | Built-in | Manual |
| **OAuth2 Support** | Via league/oauth2-client | Built-in authenticators | Manual |
| **PHP Version** | 7.2+ (8.1+ for v7) | 8.1+ | 5.6+ (8.0+ for v1) |

## Getting Started: Code Examples

### Guzzle

Guzzle is the Swiss Army knife of PHP HTTP clients. It's PSR-7 and PSR-18 compliant, meaning it integrates with every major PHP framework and library:

```php
<?php
require 'vendor/autoload.php';

use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;
use GuzzleHttp\Psr7\Request;

$client = new Client([
    'base_uri' => 'https://api.example.com',
    'timeout'  => 5.0,
    'headers'  => [
        'Authorization' => 'Bearer YOUR_TOKEN',
        'Accept'        => 'application/json',
    ],
]);

// Synchronous request
try {
    $response = $client->get('/v1/users', [
        'query' => ['page' => 1, 'per_page' => 20]
    ]);
    $users = json_decode($response->getBody(), true);
    echo "Found " . count($users['data']) . " users\n";
} catch (RequestException $e) {
    echo "Request failed: " . $e->getMessage() . "\n";
    if ($e->hasResponse()) {
        echo "Status: " . $e->getResponse()->getStatusCode() . "\n";
    }
}

// Async with promises
$promise = $client->getAsync('/v1/analytics');
$promise->then(
    function ($response) {
        echo "Analytics received\n";
    },
    function ($exception) {
        echo "Failed: " . $exception->getMessage() . "\n";
    }
);
$promise->wait();
```

Guzzle's HandlerStack middleware system lets you compose middleware layers for logging, retry, caching, and authentication:

```php
use GuzzleHttp\HandlerStack;
use GuzzleHttp\Middleware;

$stack = HandlerStack::create();
$stack->push(Middleware::retry(function ($retries, $request, $response, $exception) {
    return $retries < 3 && ($response && $response->getStatusCode() >= 500);
}));
$stack->push(Middleware::log($logger, new MessageFormatter()));
```

### Saloon

Saloon takes a different approach — it's an API integration framework built on top of Guzzle. You define your API as PHP classes, making integrations reusable and testable:

```php
<?php
use Saloon\Http\SaloonRequest;
use Saloon\Http\SaloonConnector;

// 1. Define your API connector
class GitHubConnector extends SaloonConnector
{
    public function resolveBaseUrl(): string
    {
        return 'https://api.github.com';
    }

    protected function defaultHeaders(): array
    {
        return [
            'Accept' => 'application/vnd.github+json',
            'Authorization' => 'Bearer ' . env('GITHUB_TOKEN'),
        ];
    }
}

// 2. Define a request
class GetRepositoryRequest extends SaloonRequest
{
    protected string $method = 'GET';

    public function __construct(
        protected string $owner,
        protected string $repo
    ) {}

    public function resolveEndpoint(): string
    {
        return "/repos/{$this->owner}/{$this->repo}";
    }
}

// 3. Use it
$connector = new GitHubConnector();
$request = new GetRepositoryRequest('laravel', 'laravel');
$response = $connector->send($request);

if ($response->successful()) {
    $repo = $response->json();
    echo "Stars: " . $repo['stargazers_count'] . "\n";
}
```

Saloon's class-based approach shines in large projects with many external API integrations. Each API becomes a dedicated connector, keeping your codebase organized.

### Httpful

Httpful is a lightweight, readable HTTP client for simple use cases. It prioritizes developer ergonomics over middleware complexity:

```php
<?php
require 'vendor/autoload.php';

use Httpful\Request;

// Simple GET
$response = Request::get('https://api.example.com/users')
    ->addHeader('Authorization', 'Bearer YOUR_TOKEN')
    ->send();

echo "Status: " . $response->code . "\n";
echo "Body: " . $response->raw_body . "\n";

// POST with JSON body
$response = Request::post('https://api.example.com/users')
    ->sendsJson()
    ->body(json_encode([
        'name'  => 'John Doe',
        'email' => 'john@example.com',
    ]))
    ->send();

// Templated URIs
$template = Request::init()
    ->withMethod('GET')
    ->uri('https://api.example.com/users/{id}')
    ->withoutStrictSsl(); // for dev environments
$request = clone $template;
$request->uri('https://api.example.com/users/42')->send();
```

Httpful supports file uploads, form submissions, and basic authentication out of the box. It's ideal for scripts, CLI tools, and simple integrations where a full middleware stack is overkill.

## Testing and Mocking HTTP Requests

Testing code that makes HTTP requests requires mock responses. Each library handles this differently:

**Guzzle** provides `MockHandler` for queueing responses:

```php
use GuzzleHttp\Client;
use GuzzleHttp\Handler\MockHandler;
use GuzzleHttp\HandlerStack;
use GuzzleHttp\Psr7\Response;

$mock = new MockHandler([
    new Response(200, ['X-RateLimit-Remaining' => '4999'], json_encode(['login' => 'octocat'])),
    new Response(404, [], 'Not Found'),
]);

$client = new Client(['handler' => HandlerStack::create($mock)]);
```

**Saloon** has a built-in `FakeSender` that intercepts requests:

```php
$fakeSender = new FakeSender();
$fakeSender->addResponses([
    GetUserRequest::class => new SaloonResponse(200, [], json_encode(['id' => 1])),
]);

$connector = new GitHubConnector();
$connector->withSender($fakeSender);
```

**Httpful** doesn't include testing utilities — you would typically mock at the HTTP level using PHP-VCR or wrap Httpful calls in a repository class that can be mocked.

## Deployment with Docker Compose

Running a PHP application that uses these HTTP clients is straightforward with Docker:

```yaml
version: "3.9"
services:
  php-app:
    image: php:8.2-fpm-alpine
    volumes:
      - ./src:/var/www/html
    working_dir: /var/www/html
    command: php -S 0.0.0.0:8000 -t public
    ports:
      - "8000:8000"
    environment:
      - API_TOKEN=${API_TOKEN}
      - APP_ENV=production
    restart: unless-stopped

  # Optional: Redis for response caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

## Why Self-Host Your PHP API Integrations?

Self-hosting PHP applications that integrate with external APIs gives you control over rate limiting, caching, and retry logic at the infrastructure level. Unlike managed API gateway services that charge per request, your self-hosted PHP backend running on a $10 VPS can handle millions of API calls per month at a fixed cost.

For related PHP tooling, see our [PHP ORM libraries comparison](../2026-07-06-php-orm-libraries-laravel-eloquent-doctrine-propel/) for database integration patterns. For session management in web applications, check our [PHP session management guide](../2026-07-05-php-session-management-native-symfony-laravel/). If you're building APIs that need to be exposed to external consumers, our [self-hosted API gateway guide](../self-hosted-api-gateway-apisix-kong-tyk-guide/) covers the reverse proxy layer.

## Performance and Production Patterns

For high-throughput API integrations, Guzzle's async support with curl multi-handle is the clear winner. It can send hundreds of concurrent requests without blocking your PHP process. Here's a production pattern for batch API calls:

```php
use GuzzleHttp\Client;
use GuzzleHttp\Pool;
use GuzzleHttp\Psr7\Request;

$client = new Client(['concurrency' => 25]);
$requests = function ($total) {
    for ($i = 1; $i <= $total; $i++) {
        yield new Request('GET', "https://api.example.com/users/{$i}");
    }
};

$pool = new Pool($client, $requests(100), [
    'concurrency' => 25,
    'fulfilled' => function ($response, $index) {
        echo "Request {$index} completed\n";
    },
    'rejected' => function ($reason, $index) {
        echo "Request {$index} failed: {$reason}\n";
    },
]);

$pool->promise()->wait();
```

## FAQ

### Which PHP HTTP client should I choose for a Laravel project?

Laravel's HTTP client is built on top of Guzzle, so Guzzle is the natural choice. Laravel's HTTP facade wraps Guzzle with an expressive, testable API. If you need to integrate multiple external services, consider Saloon for organizing API-specific code into dedicated connector classes.

### Is Guzzle still actively maintained?

Yes — Guzzle v7 is actively maintained with regular releases. The library is mission-critical for thousands of PHP projects including Laravel, Symfony, AWS SDK for PHP, and the Google Cloud PHP client library. It has 10+ years of development history and a massive community.

### Can I use Guzzle with PHP 8.2 and 8.3?

Yes. Guzzle 7.x supports PHP 7.2 through 8.3. For modern PHP versions (8.1+), all features work optimally including typed properties, readonly classes, and fibers.

### How do I handle retries and circuit breaking in PHP HTTP clients?

Guzzle offers a retry middleware that can be configured by status code, exception type, or custom logic. For circuit breaking, combine Guzzle with a library like `PHP-Circuit-Breaker` or use a reverse proxy (Envoy, Nginx) for infrastructure-level circuit breaking. Saloon has built-in retry support through its pipeline system.

### What's the best approach for long-running API polling?

For long-running API polling (e.g., checking async job status), use Guzzle's promise-based async with a polling loop and exponential backoff. Avoid blocking the PHP process — if you're using Laravel Octane, async requests won't block other workers. For very long-running operations, offload to a job queue (Laravel Horizon, RabbitMQ) rather than holding an HTTP connection open.

### Does Saloon replace Guzzle entirely?

No — Saloon is built on top of Guzzle's HTTP transport layer. Saloon provides the API integration structure (connectors, requests, authentication) while Guzzle handles the actual HTTP communication. You can configure Saloon to use different HTTP senders, but Guzzle is the default and recommended transport.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP HTTP Client Libraries: Guzzle vs Saloon vs Httpful — Which One for Your API Integration?",
  "description": "A comprehensive comparison of PHP HTTP client libraries Guzzle, Saloon, and Httpful covering async support, middleware, testing, deployment, and production patterns for API integrations.",
  "datePublished": "2026-07-13",
  "dateModified": "2026-07-13",
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
