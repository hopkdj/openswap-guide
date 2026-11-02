---
title: "Ruby GraphQL in 2026: graphql-ruby vs graphql-batch vs graphql-guard — Which One Do You Actually Need?"
date: "2026-11-02"
tags: ["ruby", "graphql", "api", "performance"]
draft: false
cover: "/img/screenshots/graphql-ruby-logo.jpg"
description: "A practical 2026 comparison of graphql-ruby, graphql-batch and graphql-guard: N+1 query batching, field-level authorization, real code, and which gem is now dead weight."
---

Your GraphQL endpoint returns 200 OK in 40 ms locally. In production it takes 2.3 seconds, and the database log shows the same `SELECT * FROM posts WHERE id = $1` repeated 340 times in a single request. Nothing is broken — you just shipped a graph without a batching layer, and every nested field fired its own query.

That is the exact failure mode this comparison addresses. Ruby's GraphQL ecosystem has three gems people install together by reflex, but only two of them still earn their place in a 2026 `Gemfile`:

- **`graphql` (graphql-ruby)** — the schema, execution engine, and since 2.0 a built-in dataloader.
- **`graphql-batch`** — Shopify's batching executor, still useful but no longer the only option.
- **`graphql-guard`** — field-level authorization, last committed in **September 2022**.

## TL;DR: the 2026 verdict

**Use `graphql-ruby` plus its built-in `GraphQL::Dataloader` for new projects.** It removes the N+1 problem without adding a second gem, and it is maintained by the same people who maintain the schema engine.

**Add `graphql-batch` only if** you are on an older schema (pre-2.0 patterns), you rely on its promise-based API throughout your resolvers, or you need its `Loader` semantics for non-ActiveRecord sources that your team already understands.

**Do not add `graphql-guard` to a new project.** Its last release predates the current `graphql-ruby` authorization hooks, it has no maintainer activity since 2022, and the built-in `authorized?` hook plus Pundit covers the same ground with code you already have. Keep it only if it is already wired into a large existing schema and you have tests around it.

## Side-by-side comparison (live GitHub data, November 2026)

| | **graphql-ruby** | **graphql-batch** | **graphql-guard** |
|---|---|---|---|
| Stars | 5,446 | 1,444 | 466 |
| Last push | 2026-10-31 | 2026-07-27 | **2022-09-12** |
| Primary role | Schema + execution engine | N+1 batching executor | Field-level authorization |
| Maintained | Yes, actively | Yes, low-churn but alive | **No** |
| Install | `gem "graphql"` | `gem "graphql-batch"` | `gem "graphql-guard"` |
| Replaces | — | Built-in `GraphQL::Dataloader` | `authorized?` + Pundit |
| Required for a schema | Yes | No | No |
| Breakage risk in 2026 | Low | Low | **Medium** (unmaintained, ecosystem drift) |

The star counts are not the story here. The `pushedAt` column is: `graphql-batch` still receives commits, `graphql-guard` has been frozen for four years, and `graphql-ruby` shipped a batching primitive that makes a third-party executor optional for most teams.

## Decision matrix: pick by situation, not by popularity

| Your situation | Use this | Why |
|---|---|---|
| New Rails API, nested types returning lists | `graphql-ruby` + `GraphQL::Dataloader` | One gem, one mental model, no extra dependency |
| Existing schema using `GraphQL::Batch::Loader` everywhere | Keep `graphql-batch` | Migration has zero product value if it already works |
| Field-level permissions on 20+ fields | `authorized?` + Pundit policies | No dead dependency, policies reusable in controllers |
| Already using `graphql-guard` with tests | Leave it, plan an exit | Rewriting working authorization invites security bugs |
| Public schema with hostile clients | `graphql-ruby` max_depth / max_complexity | Query cost limits matter more than batching |
| Multi-tenant SaaS with per-tenant scoping | Dataloader + policy scope in resolvers | Batching and authorization must share the same context |

## graphql-ruby: the engine, and now the batcher

`graphql-ruby` is the reference Ruby implementation: SDL or class-based schemas, a middleware stack for instrumentation, complexity analysis, and a fiber-based dataloader. If you write GraphQL in Ruby at all, this gem is already in your lockfile.

A minimal class-based schema looks like this:

```ruby
# Gemfile
gem "graphql", "~> 2.5"
gem "pundit"
```

```ruby
# app/graphql/types/query_type.rb
module Types
  class QueryType < Types::BaseObject
    field :post, Types::PostType, null: true do
      argument :id, ID, required: true
    end

    field :posts, [Types::PostType], null: false do
      argument :limit, Integer, required: false, default_value: 20
    end

    def post(id:)
      dataloader.with(Sources::RecordSource, Post).load(id)
    end

    def posts(limit:)
      Post.order(created_at: :desc).limit(limit)
    end
  end
end
```

The dataloader source is where the batching actually happens. Every `.load(id)` call inside one execution tick is collected, then `fetch` receives the whole array:

```ruby
# app/graphql/sources/record_source.rb
module Sources
  class RecordSource < GraphQL::Dataloader::Source
    def initialize(model)
      @model = model
    end

    def fetch(ids)
      records = @model.where(id: ids).index_by(&:id)
      ids.map { |id| records[id] }
    end
  end
end
```

With that in place, resolving `posts { author { name } }` for 50 posts issues **two** queries — one for the posts, one for all 50 authors — instead of 51. The fiber-based implementation means you do not have to thread promises through your resolver signatures; the engine suspends the fiber and resumes it when the batch resolves.

Two schema-level protections belong next to it, because a public graph is an unbounded API surface:

```ruby
class AppSchema < GraphQL::Schema
  max_depth 15
  max_complexity 300
  default_max_page_size 100

  use GraphQL::Dataloader
end
```

`max_depth` and `max_complexity` are the difference between a slow query and a self-inflicted denial of service. Set them before you have traffic, not after.

## graphql-batch: still correct, now optional

`graphql-batch` solved N+1 in Ruby before the engine had an answer. The API is a promise-based loader:

```ruby
# Gemfile
gem "graphql-batch"
```

```ruby
class RecordLoader < GraphQL::Batch::Loader
  def initialize(model)
    @model = model
  end

  def perform(ids)
    @model.where(id: ids).each { |record| fulfill(record.id, record) }
    ids.each { |id| fulfill(id, nil) unless fulfilled?(id) }
  end
end

# in a resolver
RecordLoader.for(Post).load(id)
```

Its real strength is the explicit `fulfill` contract: you decide what happens for missing records, and unfulfilled keys are how you signal `nil` versus an error. It also integrates cleanly with `graphql-ruby`'s promise-based lazy execution, which is why large Shopify-style schemas still run on it.

The cost is conceptual overhead. You now have two batching mental models available in the same codebase — `GraphQL::Batch::Loader` and `GraphQL::Dataloader::Source` — and a team that mixes them gets batches that silently do not merge. If you are starting today, choose one. The engine's dataloader is the one that will still be there when the third-party gem's maintenance slows down.

Where `graphql-batch` still wins: you need batching for non-database sources (an internal HTTP service, a Redis-backed counter) and your team already has loader classes with tests. Rewriting them buys nothing a reader can see.

## graphql-guard: the honest assessment

`graphql-guard` did one thing well in 2018: a per-field lambda that runs before the resolver.

```ruby
# Gemfile — think twice before adding this in 2026
gem "graphql-guard"
```

```ruby
field :email, String, null: false,
      guard: ->(obj, args, ctx) { ctx[:current_user]&.admin? }
```

The problem is not the idea, it is the maintenance. Last push: **2022-09-12**. In four years `graphql-ruby` moved its execution model, added fibers, changed how context flows, and shipped a first-class `authorized?` hook. A gem that patches field resolution has to keep up with all of that, and this one has not.

The built-in replacement requires no gem at all:

```ruby
module Types
  class PostType < Types::BaseObject
    field :title, String, null: false
    field :internal_notes, String, null: true

    def self.authorized?(object, context)
      super && Pundit.policy!(context[:current_user], object).show?
    end

    def internal_notes
      return nil unless Pundit.policy!(context[:current_user], object).internal_notes?
      object.internal_notes
    end
  end
end
```

Two rules make this safe. First, `authorized?` runs per object, so a policy that returns false on a record propagates as an error instead of leaking a field. Second, field-level checks belong in the resolver, not in a lambda in the type definition, because that is where you can also express the reason (log it, raise a typed error, return `nil`).

The migration path from `graphql-guard` is mechanical: every `guard:` lambda becomes a policy method, and the lambda body moves into the resolver. Do it with a test suite that asserts each role's field access — authorization rewrites without tests are how tenants see each other's data.

## Pitfalls that cost real debugging hours

**1. Batching across authorization boundaries.** A dataloader source that queries `Post.where(id: ids)` without tenant scoping batches records that the current user must not see. Always scope inside `fetch` using the request context, or scope in the resolver before calling `.load`.

**2. `fulfill` gaps look like `nil`, not errors.** In `graphql-batch`, a key you never fulfill resolves to `nil`. That silently turns an authorization failure into an empty field. Fulfill every requested key explicitly, including the missing ones.

**3. Depth limits interact with fragments.** `max_depth` counts fragment spreads after they are expanded, so a query that looks shallow in the client can exceed the limit. Test your limit with the actual client queries, not with hand-written minimal ones.

**4. N+1 hides in `count` and `exists?`.** Batching loads records, not aggregates. `posts { comments_count }` that calls `.count` per post still issues one query per row. Use a counter cache or a batched aggregate source.

**5. Adding all three gems "just in case"** is the most common configuration mistake. Each one adds a layer that must be understood by whoever debugs the next slow request. Two of them solve the same problem.

## FAQ

**Do I still need graphql-batch with graphql-ruby 2.x?**
No, for most applications. `GraphQL::Dataloader` is built into the engine and covers the record-loading case. Keep `graphql-batch` if you already have working loader classes or need its explicit `fulfill` contract for non-database sources.

**Is graphql-guard abandoned?**
Effectively yes. Its last commit was in September 2022, and it has not tracked the execution-model changes in `graphql-ruby`. Use the built-in `authorized?` hook with Pundit instead of adding a new dependency.

**How much does batching actually help?**
It changes query count from O(rows) to O(types). A list of 50 posts each with an author goes from 51 queries to 2. The latency win depends on your database round-trip time, but the query-count reduction is deterministic.

**Can I use graphql-batch and GraphQL::Dataloader together?**
Technically yes, and that is the problem: two batch queues mean some loads merge and some do not, which is very hard to reason about under load. Pick one per project.

**What about query cost limits on a public API?**
Use `max_depth` and `max_complexity` in the schema. They are the cheapest protection against hostile queries and require no extra gem.

**Does any of this work with Rails engines or multiple schemas?**
Yes. Dataloader sources are per-execution, so each schema and each request gets its own batch queue; nothing is shared across requests.

## Related reading

If you are tightening the rest of the stack, our [Ruby authentication comparison](../2026-11-01-ruby-authentication-devise-vs-rodauth-vs-sorcery/) covers session and token strategies that pair with GraphQL authorization policies. For a language-level view of the same trade-offs, see [Python GraphQL libraries compared](../2026-07-22-python-graphql-libraries-graphene-strawberry-ariadne/), and for the JavaScript and .NET side of the ecosystem, our [GraphQL server libraries guide](../2026-06-20-graphql-server-libraries-apollo-yoga-mercurius-strawberry-hotchocolate/) covers where those implementations put their batching layers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ruby GraphQL in 2026: graphql-ruby vs graphql-batch vs graphql-guard — Which One Do You Actually Need?",
  "description": "A practical 2026 comparison of graphql-ruby, graphql-batch and graphql-guard covering N+1 batching, field authorization, real code examples, and which gem is now dead weight.",
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
