---
title: "PHP GraphQL in 2026: webonyx/graphql-php vs Lighthouse vs GraphQLite — Which Should You Ship?"
date: "2026-11-02"
tags: ["graphql", "php", "api", "laravel", "developer-tools"]
draft: false
cover: "/img/screenshots/lighthouse-graphql-playground.jpg"
description: "A hands-on comparison of the three real PHP GraphQL server options in 2026: webonyx/graphql-php, Lighthouse and GraphQLite. Code, trade-offs and the traps nobody warns you about."
---

REST endpoints multiply like rabbits. You add `/orders`, then `/orders/{id}`, then `/orders/{id}/items`, then a mobile client asks for a trimmed payload and you bolt on `?fields=` — and three months later your API surface is 40 routes nobody can document. That is exactly the wall where PHP teams start typing `composer require` something with "graphql" in the name.

The problem: PHP has three serious GraphQL server libraries, and they are **not** interchangeable. One is a spec engine, one is a Laravel framework, one is an attribute-driven API layer. Pick wrong and you will rewrite your resolver layer in six months.

I dug through all three repos, pulled their current release tags, and wired each one up. Here is what actually matters.

## TL;DR — Quick Verdict

- **Building a Laravel app?** Use **Lighthouse**. You keep Eloquent, you keep policies, and your schema lives in a `.graphql` file that a frontend dev can read without touching PHP.
- **Framework-agnostic, or you hate schema-first SDL?** Use **webonyx/graphql-php**. It is the engine the other two sit on, it has zero framework opinions, and it is the safest long-term bet.
- **You already have a fat service layer and want GraphQL to be a thin annotation on top?** Use **GraphQLite**. Attributes on your existing classes, no SDL file to maintain.
- **Do not** pick Lighthouse if you are on Symfony or Slim. It is Laravel-only, full stop.

## The Real Numbers (fetched November 2026)

| | webonyx/graphql-php | Lighthouse | GraphQLite |
|---|---|---|---|
| GitHub stars | **4,708** | **3,498** | **578** |
| Latest release | v15.39.0 (2026-10-25) | v6.74.0 (2026-10-25) | v8.3.1 (2026-07-16) |
| Last commit | active (Oct 2026) | active (Oct 2026) | active (Oct 2026) |
| License | MIT | MIT | MIT |
| Install | `composer require webonyx/graphql-php` | `composer require nuwave/lighthouse` | `composer require thecodingmachine/graphqlite` |
| Schema definition | PHP type objects **or** SDL | SDL file + directives | PHP attributes on classes |
| Framework lock-in | none | Laravel only | none (Laravel/Symfony/Slim bridges) |
| Resolver model | closures per field | `@field` resolver classes | annotated controller methods |
| Built-in N+1 batching | no | yes (`@hasMany`, batch loading) | partial (via prefetch) |
| Learning curve | steep (verbose) | medium | low if you know your domain classes |

The star gap is not a quality verdict. graphql-php is plumbing — people depend on it transitively and never star it. GraphQLite's 578 stars reflect a smaller but very stable user base, not abandonment: it shipped v8.3.1 four months ago.

## Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Laravel 9+ app with Eloquent models and Policies | **Lighthouse** | Directives map straight onto your models; auth goes through existing guards |
| Symfony / Slim / plain PHP, no framework | **webonyx/graphql-php** | Only option with no framework assumptions |
| Legacy service layer you refuse to rewrite | **GraphQLite** | Attributes decorate existing classes instead of replacing them |
| You need a public API with strict cost limits | **webonyx/graphql-php** | You own the validation rules, so you can enforce query depth and complexity exactly |
| Frontend team owns the schema contract | **Lighthouse** | `graphql/schema.graphql` is a real file they can diff in PRs |
| You want GraphQL as an internal read layer only | **GraphQLite** | Least ceremony, fastest to a working query |

## webonyx/graphql-php — The Engine Underneath

This is the reference-grade PHP implementation. It gives you a type system, a parser, an executor and an error formatter. It gives you **nothing** else — no HTTP handling, no auth, no batching. That is the point.

```bash
composer require webonyx/graphql-php:^15.39
```

A minimal schema is built with type objects:

```php
<?php
use GraphQL\Type\Definition\ObjectType;
use GraphQL\Type\Definition\Type;
use GraphQL\Type\Schema;
use GraphQL\GraphQL;

$queryType = new ObjectType([
    'name' => 'Query',
    'fields' => [
        'order' => [
            'type' => Type::string(),
            'args' => [
                'id' => Type::nonNull(Type::id()),
            ],
            'resolve' => fn ($root, array $args) => "order-{$args['id']}",
        ],
    ],
]);

$schema = new Schema(['query' => $queryType]);

$result = GraphQL::executeQuery($schema, '{ order(id: 42) }');
echo json_encode($result->toArray());
```

Two things to notice. First, `executeQuery` is synchronous — no promises, no async resolvers. Second, every field needs a `resolve` callable, so on a 60-field schema you write 60 closures unless you generate them.

Where graphql-php genuinely wins is **control**. Because you build the schema yourself, you can wrap the executor:

```php
use GraphQL\Validator\Rules\QueryDepth;
use GraphQL\Validator\Rules\DisableIntrospection;

$schema->getConfig()->validationRules = [
    new QueryDepth(8),
    // keep introspection for internal tooling but cap the depth
];
```

If introspection must be closed in production, that is a one-liner instead of a directive flag hunt. For a public API under abuse pressure, this is the difference between sleeping and not.

## Lighthouse — Schema-First, Laravel-Native

Lighthouse is the reason most PHP GraphQL APIs exist. It takes an SDL file and turns directives into resolvers, so the schema *is* the implementation contract.

```bash
composer require nuwave/lighthouse:^6.74
php artisan vendor:publish --tag=lighthouse-config
```

Your schema lands in `graphql/schema.graphql`:

```graphql
type Query {
    orders(first: Int!, after: String): OrderPaginator! @paginate
    order(id: ID! @eq): Order @find
}

type Order @model(class: "App\\Models\\Order") {
    id: ID!
    reference: String!
    total: Float! @rename(attribute: "total_amount")
    items: [OrderItem!]! @hasMany
    customer: User! @belongsTo
}
```

That is the entire CRUD read layer. `@paginate` handles cursor pagination, `@hasMany` handles the relationship, and the generated SQL is actually reasonable — Lighthouse builds eager loads from the requested selection set, which is how it dodges the N+1 problem that eats naive resolvers alive.

![Lighthouse GraphQL Playground running against a Laravel schema](/img/screenshots/lighthouse-graphql-playground.jpg "Lighthouse ships an interactive GraphQL playground for local schema exploration")

Auth is handled with guards rather than a custom middleware stack:

```graphql
type Mutation {
    cancelOrder(id: ID!): Order
        @guard(with: ["api"])
        @can(ability: "cancel", find: "id")
        @field(resolver: "App\\GraphQL\\Mutations\\CancelOrder")
}
```

`@can` routes through Laravel Policies, so your authorization logic stays in one place instead of getting duplicated into resolver code.

The cost: **Laravel only**. No Laravel, no Lighthouse. And directives are magic — when `@paginate` produces a query you did not expect, you will be reading vendor source to understand why.

## GraphQLite — Attributes on Your Existing Classes

GraphQLite inverts the model. Instead of writing a schema and pointing it at code, you annotate code and it derives the schema.

```bash
composer require thecodingmachine/graphqlite:^8.3
```

```php
<?php
namespace App\Api;

use TheCodingMachine\GraphQLite\Annotations\Query;
use TheCodingMachine\GraphQLite\Annotations\Type;
use TheCodingMachine\GraphQLite\Annotations\Field;

#[Type]
class Order
{
    public function __construct(
        private string $reference,
        private float $total,
    ) {}

    #[Field]
    public function getReference(): string
    {
        return $this->reference;
    }

    #[Field(name: "total")]
    public function getTotalWithTax(): float
    {
        return round($this->total * 1.2, 2);
    }
}
```

```php
#[Query]
public function order(string $id): Order
{
    return $this->repository->findOrFail($id);
}
```

![GraphQLite deriving a schema from PHP attributes](/img/screenshots/graphqlite-annotation-query.jpg "GraphQLite exposes existing PHP classes through attributes — no separate SDL file")

The win is real for legacy code: your `Order` entity does not move, does not get a duplicate DTO, and does not need a schema file kept in sync by hand. The `name:` argument on `#[Field]` even lets you expose `getTotalWithTax()` as `total`, which is how you avoid leaking internal method names into a public contract.

The loss is visibility. There is no single file that answers "what does this API expose?" — you answer it by running introspection or grepping for attributes. On a team of 12, that gets old.

For N+1, GraphQLite offers prefetch hints (`@Prefetch` / `prefetchMethod`) so a list query can load related rows in one batch rather than per item. It works, but it is opt-in per field. Miss one and you ship a 200-query page.

## Deployment Reality Check

All three run fine behind PHP-FPM. A minimal Nginx block that works for any of them:

```nginx
server {
    listen 80;
    server_name api.example.com;
    root /var/www/app/public;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass unix:/run/php/php8.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_read_timeout 60s;
    }
}
```

If you want a container instead, the official `php:8.4-fpm` image plus Nginx is the boring, correct choice — avoid community images that bundle a web server and hide the PHP config you need to tune.

## Pitfalls Nobody Warns You About

**1. Unguarded introspection is a schema leak.** All three expose full introspection by default. On a public endpoint that hands attackers your entire data model, including fields you thought were internal. Disable it in production or gate it behind a header.

**2. Depth limits are not optional.** A three-line nested query can expand to millions of resolver calls. `QueryDepth` in graphql-php, `@limit` / config-level complexity rules in Lighthouse, and a reverse-proxy timeout as backstop. If you skip this, your first hostile request is a denial-of-service.

**3. N+1 is the default failure mode.** graphql-php gives you nothing. Lighthouse batches relationships it knows about through directives — but a custom `@field` resolver still executes per item unless you batch it. GraphQLite needs prefetch declared per field. Budget time for query counting (`EXPLAIN` logs) before launch, not after.

**4. Error messages leak SQL.** The default formatter in graphql-php includes exception messages. A failed constraint dumps your table and column names into the response. Map exceptions to generic codes and log the details server-side.

**5. Caching is per-query, not per-field.** None of these ship a persisted-query cache out of the box. Lighthouse has `@cache` for simple cases; for anything else put a reverse proxy or a query allowlist in front. Clients sending arbitrary query strings also means you cannot cache at the CDN layer effectively — persisted queries fix that.

**6. Version pinning matters more than usual.** graphql-php v15 is the current major; Lighthouse v6 requires it. Mixing a v14 transitive dependency will produce confusing "type not found" errors at runtime rather than install time.

## FAQ

**Which PHP GraphQL library is fastest?**
Raw execution speed is dominated by your resolvers and database, not the library. graphql-php has the thinnest layer between the request and your code, Lighthouse adds directive parsing and eager-load planning, GraphQLite adds attribute reflection (which it caches). In practice, a well-indexed query with batched relations beats a micro-optimized schema every time. Benchmark your own resolvers, not the frameworks.

**Can I use Lighthouse without Laravel?**
No. Lighthouse is built on Laravel's container, Eloquent and authorization stack. On Symfony, use graphql-php or GraphQLite with its Symfony bundle.

**Does GraphQLite require a schema file?**
No — that is its main selling point. The schema is derived from PHP attributes at runtime and cached. You lose the single-file API contract but gain zero-duplication mapping onto existing domain classes.

**How do I stop expensive queries?**
Three layers: a hard query depth limit, a complexity/cost score per field, and an HTTP timeout. graphql-php exposes validation rules directly; Lighthouse supports complexity limits in its config; GraphQLite relies on the underlying webonyx validation you configure.

**Which one should a small team pick in 2026?**
If the app is Laravel, Lighthouse — it removes the most boilerplate. If it is not, graphql-php, because it will still be maintained in five years and every other PHP GraphQL tool depends on it.

**Is GraphQL worth it over REST for a PHP API?**
Only if clients have genuinely different data needs (mobile vs web vs partner integrations). If every consumer wants the same payload, a few well-designed REST endpoints plus HTTP caching will outperform GraphQL on both latency and operational complexity.

## Related Reading

If you are comparing server implementations across ecosystems, our [Java GraphQL libraries comparison](../2026-07-22-java-graphql-libraries-graphql-java-dgs-graphql-spqr/) covers the JVM equivalents, and the [GraphQL server libraries roundup](../2026-06-20-graphql-server-libraries-apollo-yoga-mercurius-strawberry-hotchocolate/) covers the Node and Python side. For teams weighing a managed engine against hand-written resolvers, see [Hasura vs Directus vs PostGraphile](../hasura-vs-directus-vs-postgraphile-self-hosted-graphql-api-engines-2026/). If your schema exposes timestamps, the [PHP datetime libraries comparison](../2026-11-01-php-datetime-libraries-carbon-chronos-brick/) is worth ten minutes before you commit to a serialization format.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP GraphQL in 2026: webonyx/graphql-php vs Lighthouse vs GraphQLite",
  "description": "Hands-on comparison of the three serious PHP GraphQL server libraries in 2026, with real version data, code samples, deployment config and production pitfalls.",
  "datePublished": "2026-11-02",
  "dateModified": "2026-11-02",
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
