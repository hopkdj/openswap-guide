---
title: "TypeScript HTTP Client Libraries: Axios vs Got vs Undici vs Ky vs node-fetch Comparison"
date: "2026-07-28"
tags: ["typescript", "nodejs", "http-client", "axios", "got", "undici", "ky", "node-fetch", "javascript"]
draft: false
---

## Introduction

Every Node.js application makes HTTP requests — whether calling internal microservices, integrating with third-party APIs, or fetching remote data. While Node.js ships with the built-in `http` and `https` modules, their low-level nature makes them cumbersome for everyday use. A good HTTP client library provides clean Promise-based APIs, interceptors, retries, timeout handling, and TypeScript type safety.

This comparison covers five leading TypeScript/Node.js HTTP client libraries: **Axios** (the most popular, 109K+ stars, isomorphic), **Got** (feature-rich with built-in retries and pagination), **Undici** (Node.js official high-performance HTTP client), **Ky** (minimal Fetch API wrapper by Sindre Sorhus), and **node-fetch** (the Fetch API polyfill that started it all).

## Comparison Overview

| Feature | Axios | Got | Undici | Ky | node-fetch |
|---------|-------|-----|--------|-----|------------|
| **GitHub Stars** | 109,167 | 14,928 | 7,650 | 17,004 | 8,800+ |
| **API Style** | Custom | Custom (chainable) | Fetch API | Fetch API | Fetch API |
| **Browser Support** | Yes | No (Node.js only) | No (Node.js only) | Yes (browser) | Yes |
| **Built-in Retries** | Via interceptor | Yes | Via dispatcher | Via hook | No |
| **HTTP/2 Support** | No (v1.x) | Yes | Yes | Via browser | No |
| **Interceptors** | Yes | Yes (hooks) | Yes (interceptors) | Yes (hooks) | No |
| **Timeout** | Configurable | Configurable | Yes | Via AbortSignal | Via AbortSignal |
| **GZip Decompression** | Automatic | Automatic | Automatic | Browser-native | Manual |
| **Stream Support** | Limited | Yes | Yes | No | Limited |
| **TypeScript** | Built-in | Built-in | Built-in | Built-in | Via @types |
| **Install Size** | ~50 KB | ~150 KB | ~100 KB | ~3 KB | ~15 KB |

## Axios: The Ubiquitous Choice

Axios is by far the most downloaded HTTP client in the JavaScript ecosystem. Its isomorphic design (same API in browser and Node.js), intuitive interceptors, and automatic JSON transformation made it the de facto standard. With 109K+ GitHub stars and over 50 million weekly npm downloads, virtually every JavaScript developer has used Axios at some point.

```bash
npm install axios
```

```typescript
import axios from 'axios';

// Basic GET
const { data } = await axios.get('https://api.example.com/users', {
  params: { page: 1, limit: 10 },
  timeout: 5000,
});

// POST with JSON
const response = await axios.post('https://api.example.com/users', {
  name: 'Alice',
  email: 'alice@example.com',
});

// Request interceptor
axios.interceptors.request.use(config => {
  config.headers['Authorization'] = `Bearer ${getToken()}`;
  return config;
});

// Response interceptor for global error handling
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      redirectToLogin();
    }
    return Promise.reject(error);
  }
);

// Concurrent requests
const [users, posts] = await Promise.all([
  axios.get('/users'),
  axios.get('/posts'),
]);
```

Axios's interceptors are its killer feature — you can globally transform requests and responses, add auth tokens, log timing, or handle errors without touching individual calls. The `axios.create()` factory lets you create pre-configured instances with custom base URLs and defaults.

## Got: Feature-Rich and Extensible

Got is a Node.js-only HTTP client that emphasizes developer experience and advanced features. Unlike Axios, Got has built-in retries (with exponential backoff), pagination support, and hooks that provide more granular control over the request lifecycle than Axios interceptors.

```bash
npm install got
```

```typescript
import got from 'got';

// Basic request with retries
const { body } = await got.get('https://api.example.com/users', {
  responseType: 'json',
  retry: {
    limit: 3,
    methods: ['GET', 'POST'],
    statusCodes: [408, 429, 500, 502, 503, 504],
  },
  timeout: {
    request: 10000,
  },
});

// POST with JSON body
const { statusCode } = await got.post('https://api.example.com/users', {
  json: { name: 'Bob', email: 'bob@example.com' },
});

// Advanced: pagination API
const allUsers = got.paginate.all('https://api.example.com/users', {
  searchParams: { per_page: 100 },
  pagination: {
    transform: (response) => JSON.parse(response.body),
    paginate: (response, allItems, currentItems) => {
      if (currentItems.length === 0) return false;
      return { searchParams: { page: allItems.length / 100 + 1 } };
    },
  },
});

// Hooks (interceptors)
const client = got.extend({
  hooks: {
    beforeRequest: [
      options => {
        options.headers['authorization'] = `Bearer ${getToken()}`;
      }
    ],
    afterResponse: [
      (response, retryWithMergedOptions) => {
        if (response.statusCode === 401) {
          // Refresh token and retry
          const newToken = refreshToken();
          return retryWithMergedOptions({
            headers: { authorization: `Bearer ${newToken}` }
          });
        }
        return response;
      }
    ],
  },
});
```

Got's built-in retry mechanism is more sophisticated than Axios's manual interceptor approach. It handles exponential backoff, respects `Retry-After` headers, and can retry on specific HTTP status codes. The `got.extend()` API creates reusable client configurations with pre-set hooks and options.

## Undici: Node.js Core's High-Performance HTTP

Undici ("eleven" in Italian) is the official Node.js HTTP client, maintained by the Node.js core team. It is the fastest HTTP client for Node.js because it is written with a focus on raw throughput, connection pooling, and HTTP/2 support — all without the overhead of a Promise abstraction layer.

```bash
npm install undici
```

```typescript
import { request } from 'undici';

// Simple request
const { statusCode, body } = await request('https://api.example.com/users');
const data = await body.json();
console.log(`Status: ${statusCode}, Users: ${data.length}`);

// POST with JSON
const { statusCode: postStatus } = await request('https://api.example.com/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'Charlie', email: 'charlie@example.com' }),
});

// Using a client with connection pool
import { Pool } from 'undici';

const pool = new Pool('https://api.example.com', {
  connections: 100,
  pipelining: 1,
});

const responses = await Promise.all([
  pool.request({ path: '/users/1', method: 'GET' }),
  pool.request({ path: '/users/2', method: 'GET' }),
  pool.request({ path: '/users/3', method: 'GET' }),
]);
```

Undici's connection pooling is where it shines — a single Pool handles connection reuse, keep-alive, and pipelining automatically. Benchmarks show Undici processing 2-3x more requests per second than Axios for high-concurrency scenarios. As of Node.js 20+, the global `fetch()` is backed by Undici internally.

## Ky: Minimal Elegance

Ky is a tiny (~3 KB) HTTP client built on the Fetch API by Sindre Sorhus. It is designed for simplicity: if you know `fetch()`, you know Ky. Unlike most alternatives, Ky works in both browsers and Node.js (via a global `fetch` polyfill or Node.js 18+).

```bash
npm install ky
```

```typescript
import ky from 'ky';

// Simple GET with search params
const users = await ky.get('https://api.example.com/users', {
  searchParams: { page: 1, limit: 10 },
}).json();

// POST with JSON body (automatic Content-Type)
const newUser = await ky.post('https://api.example.com/users', {
  json: { name: 'Diana', email: 'diana@example.com' },
}).json();

// Create a pre-configured instance
const api = ky.create({
  prefixUrl: 'https://api.example.com',
  headers: { Authorization: `Bearer ${getToken()}` },
  hooks: {
    beforeRequest: [
      request => console.log(`${request.method} ${request.url}`),
    ],
    afterResponse: [
      (_request, _options, response) => {
        if (!response.ok) {
          console.error(`Request failed: ${response.status}`);
        }
      },
    ],
  },
  retry: { limit: 2 },
  timeout: 10000,
});

// Use the configured instance
const data = await api.get('users').json();

// Aborting requests
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 5000);
const response = await ky.get('https://slow-api.example.com', {
  signal: controller.signal,
}).json();
clearTimeout(timeout);
```

Ky's philosophy is "less is more" — it extends `fetch()` with just enough quality-of-life improvements (JSON handling, retries, hooks, timeout via AbortController) without adding a custom API surface. For developers who value bundle size and API simplicity, Ky is the obvious choice.

## node-fetch: The Pioneer

node-fetch was the original Fetch API implementation for Node.js, predating both Undici and Ky. While it is now in maintenance mode (the Fetch API is natively available in Node.js 18+), it remains widely used in legacy codebases.

```bash
npm install node-fetch
```

```typescript
import fetch from 'node-fetch';

const response = await fetch('https://api.example.com/users');
const users = await response.json();
```

## Performance Benchmarks

In high-concurrency benchmarks (1000 concurrent requests to localhost), Undici consistently leads with approximately 15,000 req/s, followed by Got at about 9,000 req/s, and Axios at about 5,000 req/s. Ky and node-fetch fall between 4,000-7,000 req/s depending on Node.js version and workload characteristics. For the vast majority of applications, the difference is irrelevant — database queries and business logic dominate response time far more than the HTTP client overhead.

## Why Your HTTP Client Choice Matters for Self-Hosted Services

When building self-hosted Node.js applications — API gateways, microservices, or monitoring tools — your HTTP client directly impacts reliability and observability. A client with built-in retry logic prevents transient failures from cascading through your service mesh. Connection pooling reduces TCP handshake overhead when communicating with internal services in a Docker or Kubernetes environment. Hooks and interceptors enable centralized logging, metrics collection, and distributed tracing across all outbound requests.

For example, a self-hosted API gateway built with Node.js needs to forward thousands of requests per minute to backend services. Using Undici with connection pooling ensures connections are reused rather than re-established, cutting latency by 30-50% compared to naive Axios usage without keep-alive. Meanwhile, Got's built-in retry with exponential backoff prevents a temporary backend outage from causing user-facing errors.

For related Node.js development topics, check our guides on [TypeScript Dependency Injection](../2026-07-21-typescript-di-containers-tsyringe-inversifyjs-typedi/) and [TypeScript Schema Validation](../2026-07-24-typescript-schema-validation-typebox-arktype-runtypes/). If you are working across stacks, our [PHP routing comparison](../2026-07-28-php-routing-libraries-fastroute-slim-symfony-routing-league-route-comparison/) and [Ruby background jobs guide](../2026-07-28-ruby-background-job-processors-sidekiq-shoryuken-faktory-sucker-punch-comparison/) cover complementary infrastructure choices.

## FAQ

### Should I switch from Axios to Undici?

If your application makes a high volume of outbound HTTP requests (100+ per second), Undici's connection pooling can meaningfully improve throughput and reduce latency. For most applications, Axios's mature ecosystem, interceptors, and defensive features (XSRF protection) make it the safer choice. Consider Undici for performance-critical proxy or gateway services where every millisecond counts.

### Does Ky work in Node.js?

Yes. Ky supports Node.js via a global `fetch` implementation (Node.js 18+ has `fetch` natively) or the `ky-universal` package. In Node.js 20+, you can use Ky directly without any polyfill. Ky's browser support is also excellent, making it a great choice for isomorphic libraries.

### How do I handle file uploads with Got?

Got supports streaming file uploads with `FormData`. Use `got.post(url, { body: formData })` or the `got.stream.post()` method for large files. For multipart uploads, Got's `FormData` integration is more ergonomic than Axios's approach with the `form-data` module. Got also supports progress events for tracking upload progress.

### Why does Axios need interceptors while Got has hooks?

Both solve the same problem — modifying requests/responses globally — but with different APIs. Axios interceptors are promise-based and sequential. Got hooks fire at specific lifecycle points (`beforeRequest`, `beforeRedirect`, `afterResponse`, `beforeError`, `beforeRetry`). Got's hooks give you more granular control over the request lifecycle, but Axios's interceptor pattern is more familiar to most developers.

### Is node-fetch still maintained?

node-fetch v3 is in maintenance mode with security fixes only. For new projects, use the built-in `fetch()` in Node.js 18+ (backed by Undici), Ky (if you want extra features), or Got (for maximum Node.js-specific capabilities). Migrating from node-fetch to native `fetch` is straightforward since both implement the same Fetch API standard.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TypeScript HTTP Client Libraries: Axios vs Got vs Undici vs Ky vs node-fetch Comparison",
  "description": "Comprehensive comparison of TypeScript/Node.js HTTP client libraries — Axios, Got, Undici, Ky, and node-fetch — with code examples, performance analysis, and migration guidance.",
  "datePublished": "2026-07-28",
  "dateModified": "2026-07-28",
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
