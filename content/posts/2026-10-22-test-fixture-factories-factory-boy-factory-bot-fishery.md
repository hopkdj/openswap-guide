---
title: "factory_boy vs FactoryBot vs Fishery in 2026: Which Fixture Factory Wins?"
date: "2026-10-22"
tags: ["testing", "developer-tools", "factory-boy", "factory-bot", "typescript", "python", "ruby"]
description: "A practical comparison of the three dominant fixture-factory libraries — Python's factory_boy, Ruby's FactoryBot and TypeScript's Fishery — with real code, performance traps and migration notes."
draft: false
---

Your test suite takes 40 seconds to boot and 31 of those seconds are spent building objects you do not care about. Someone on the team suggests "just use fixtures", someone else says fixtures are the reason the suite is unmaintainable, and you end up reading three README files that all promise the same thing: declarative test data.

Fixture factories are one of the few testing patterns that genuinely survived a decade of framework churn. The idea is simple — describe the default shape of a valid object once, then override only the fields that matter for each test. But the three libraries that dominate this space make very different bets about what "building an object" means, and those bets determine whether your suite gets faster or slower.

This comparison covers **factory_boy 3.3.3** (Python), **FactoryBot 6.6.0** (Ruby) and **Fishery 2.4.0** (TypeScript/JavaScript), with live repository data as of 22 October 2026.

## TL;DR — Quick Verdict

- **Django, SQLAlchemy or MongoEngine project** → **factory_boy**. The ORM integrations (`DjangoModelFactory`, `SQLAlchemyModelFactory`) save you real work, and `factory.Trait` / `factory.Maybe` handle conditional data better than anything else in this comparison.
- **Rails application** → **FactoryBot**. It is effectively part of the Rails testing culture, `build_stubbed` is the fastest escape from database round trips, and every Rails developer you hire already knows the syntax.
- **TypeScript service with Prisma, Kysely or plain objects** → **Fishery**. Full type inference from your domain types, no database opinions, and a `build()` path that never touches the network unless you explicitly define `onCreate`.

There is no scenario where you should mix two of these in one codebase. Pick the one that matches your language and never think about it again.

## Head-to-Head Comparison

| Dimension | factory_boy | FactoryBot | Fishery |
|---|---|---|---|
| GitHub stars | 3,811 | 8,167 | 1,035 |
| Last push | 2026-01-01 | 2026-10-13 | 2026-02-26 |
| Latest version | 3.3.3 | 6.6.0 | 2.4.0 |
| Language | Python | Ruby | TypeScript / JavaScript |
| Licence | MIT | MIT | MIT |
| ORM coupling | First-class Django, SQLAlchemy, MongoEngine | Active Record assumptions | None — ORM agnostic |
| Build without persisting | `Strategy` system (`build`, `create`, `stub`) | `build` / `build_stubbed` | `build()` |
| Async persistence hook | Not applicable | Not applicable | `onCreate` returns a promise |
| Traits / conditional data | `factory.Trait`, `factory.Maybe` | Native `trait` blocks | Transient params + composition |
| Type safety | Runtime only | Runtime only | Compile-time inference |
| Learning curve | Medium | Low for Rails devs | Low |

The star gap is mostly cultural, not technical: FactoryBot has been the default in Rails since 2010 under its original `factory_girl` name, and Ruby developers adopt it without evaluating alternatives. Fishery's 1,035 stars are not a quality signal — it is simply younger and confined to the TypeScript ecosystem.

## Decision Matrix

| Your stack / need | Recommendation | Reason |
|---|---|---|
| Django models with foreign keys and M2M | factory_boy | `DjangoModelFactory` knows how to persist relations correctly |
| SQLAlchemy session-bound objects | factory_boy | `SQLAlchemyModelFactory` injects the session |
| Rails monolith | FactoryBot | Convention match with Active Record, `build_stubbed` is excellent |
| RSpec system specs | FactoryBot | `attributes_for` feeds controller params cleanly |
| TypeScript + Prisma / Kysely | Fishery | Typed factories against your own interfaces |
| Node service with a test database | Fishery | `onCreate` lets you decide exactly when persistence happens |
| Polyglot monorepo | Judge per language | Do not force one pattern across runtimes |

## factory_boy — The Python ORM Workhorse

factory_boy is explicitly modelled on thoughtbot's Ruby gem — its README says so in the first line — but it diverged where Python's ORM culture required it. The core value is that a factory can be bound to a model class and inherit the persistence behaviour of that ORM.

Install it with pip:

```bash
pip install factory_boy
# or, with your project's tooling
uv add --dev factory_boy
```

A Django factory that handles relations, unique sequences and Faker-backed fields looks like this:

```python
import factory
from factory.django import DjangoModelFactory
from factory.faker import Faker

from accounts.models import User, Profile


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.LazyAttribute(lambda o: "%s@example.com" % o.username)
    display_name = Faker("name")
    is_active = True

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if not create:
            return
        Profile.objects.create(user=self, **kwargs)
```

Three details in that snippet are worth understanding before you copy it:

- **`factory.Sequence`** guarantees uniqueness across the whole test session. If a test repeats the same sequence number because the process was recycled, a unique constraint will fail intermittently — a classic flaky-test source.
- **`factory.LazyAttribute`** receives the partially built object, so `email` can depend on `username`. Order matters: lazies are evaluated in declaration order, and referencing a field declared later raises an error.
- **`skip_postgeneration_save = True`** avoids a redundant `save()` after post-generation hooks, which Django warns about in recent versions. Set it explicitly instead of living with the deprecation notice.

The build strategy system is the part teams underuse. `UserFactory.build()` returns an unsaved instance, `UserFactory.create()` persists it, `UserFactory.build_batch(20)` returns a list, and `factory.build(dict, FACTORY_CLASS=UserFactory)` gives you a plain dictionary for tests that never needed a model object at all. Most slow Python suites are slow because every factory call defaults to `create()` when a plain dict would have sufficed.

Conditional data is handled by `factory.Trait` and `factory.Maybe`, which beats hand-rolled helper functions:

```python
class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    status = "pending"

    class Params:
        paid = factory.Trait(status="paid", paid_at=factory.LazyFunction(timezone.now))
        expedited = factory.Trait(shipping="express")
```

Now `OrderFactory(paid=True, expedited=True)` produces one object with two orthogonal variations, and the combinations are declared once instead of scattered across test files.

## FactoryBot — The Ruby Convention You Inherit

FactoryBot is not a library you evaluate in a Rails shop; it is a library you are handed on day one. That is not a criticism. The API is compact, the defaults are sensible, and `build_stubbed` is arguably the best performance feature in this entire comparison.

Add it through Bundler:

```ruby
# Gemfile
group :test do
  gem "factory_bot_rails"
end
```

A factory with a sequence, a trait, an association and a persistence hook:

```ruby
FactoryBot.define do
  factory :user do
    sequence(:username) { |n| "user#{n}" }
    email { "#{username}@example.com" }
    active { true }

    association :account

    trait :admin do
      role { "admin" }
    end

    after(:create) { |user| user.confirm! }
  end
end
```

Usage reads almost like English:

```ruby
user   = create(:user, :admin)
ghost  = build_stubbed(:user)          # no database at all
params = attributes_for(:user)         # hash for controller specs
team   = create_list(:user, 5, :admin) # five persisted records
```

The critical distinction is between the three build strategies:

| Strategy | Persists? | Runs `after(:create)`? | Speed |
|---|---|---|---|
| `create` | Yes | Yes | Slowest |
| `build` | No | No | Fast |
| `build_stubbed` | No | No, uses fake IDs | Fastest |
| `attributes_for` | No | No | Fast, returns a hash |

Switching a controller spec from `create` to `build_stubbed` often cuts the runtime of that file by more than half, because it removes the insert, the transaction and the callback chain. The catch is that `build_stubbed` assigns fake primary keys and disallows database access on the returned object — associations are stubbed too, so any code path that calls `reload`, runs a query, or depends on real timestamps will break loudly. That is a feature: it tells you the test was secretly an integration test.

`FactoryBot.lint` is the most underrated feature in the gem. It instantiates every factory once and reports invalid records, catching the "this factory has been broken since someone added a NOT NULL column" problem before it surfaces as a confusing failure in an unrelated spec.

## Fishery — Typed Factories for TypeScript

Fishery is a deliberately small library: a factory is a function that returns your object, with a few injected helpers for sequences, transient parameters, associations and hooks. Because it is written in TypeScript and generic over your type, a factory that drifts from your domain model fails at compile time rather than at 3 a.m. in CI.

Install as a dev dependency:

```bash
npm install --save-dev fishery
# or
pnpm add -D fishery
```

A typed factory with a sequence, nested object and associations:

```typescript
// factories/user.ts
import { Factory } from 'fishery';
import type { User } from '../types';
import { postFactory } from './post';

export const userFactory = Factory.define<User>(({ sequence, params, associations, afterBuild }) => ({
  id: sequence,
  name: 'Rosa',
  email: `user-${sequence}@example.com`,
  address: { city: 'Austin', state: 'TX', country: 'USA' },
  posts: postFactory.buildList(2),
  ...params,
}));
```

Building objects with partial overrides deep-merges the nested structure, which is exactly what you want for an address:

```typescript
const user = userFactory.build({
  name: 'Susan',
  address: { city: 'El Paso' },
});

user.name;          // Susan
user.address.city;  // El Paso
user.address.state; // TX — preserved from the factory default
```

Persistence is opt-in and asynchronous. Nothing happens until you define `onCreate`:

```typescript
const userFactory = Factory.define<User>(({ onCreate }) => {
  onCreate((user) => db.user.create({ data: user }));

  return {
    id: 0,
    name: 'Rosa',
    email: 'rosa@example.com',
  };
});

const user = await userFactory.create({ name: 'Maria' });
```

That design is the reason Fishery suites stay fast. There is no hidden database call behind `build()`, no implicit transaction, and no callback chain you forgot about. The cost is that you must write the persistence adapter yourself — Fishery has no idea what Prisma or Kysely is, and it never will.

## Pitfalls That Actually Bite

**Sequence collisions in parallel test runs.** factory_boy's `Sequence` and FactoryBot's `sequence` are per-process counters. Run tests in parallel workers and two workers will happily produce `user1`, which breaks unique constraints. Give each worker a prefix derived from the worker index, or use UUID-based identifiers for fields with unique indexes.

**`create` by default is the single biggest performance mistake.** In all three libraries the convenient path persists data. In factory_boy, prefer `build()` unless the test asserts on the database. In FactoryBot, prefer `build_stubbed`. In Fishery, `build()` is already the default — do not add `onCreate` until a test genuinely needs a row.

**Callbacks hide work.** FactoryBot's `after(:create)` and factory_boy's `@factory.post_generation` run silently. A factory that creates three related records looks identical to one that creates none, and your 200-test suite quietly performs 600 inserts. Audit factories that call other factories before blaming the framework for slow tests.

**Overriding deeply nested relations is where factory libraries diverge.** factory_boy uses `customer__is_vip=True` style double-underscore traversal, which is powerful and easy to typo. FactoryBot expects you to build associations explicitly. Fishery deep-merges plain objects. Know which one you are using before you write 40 tests against the wrong assumption.

**Factory drift is invisible until it is not.** The moment a model gains a required field, every factory that does not set it becomes a landmine. Run FactoryBot's `lint`, run factory_boy factories in a dedicated smoke test, and keep a single test that instantiates every factory. It takes minutes to add and saves hours of debugging.

**Do not use factories as fixtures.** Loading a factory once per suite and sharing the object between tests creates order-dependent tests that pass alone and fail together. Factories are for per-test data; shared state belongs in an explicitly managed setup step.

## FAQ

### Is factory_boy the same as FactoryBot?

No. factory_boy is a Python library that borrowed the declarative style from thoughtbot's Ruby gem. They share concepts — sequences, lazy attributes, traits — but the APIs are not compatible and the Python version has its own ORM integration layer. The naming similarity confuses people constantly.

### Which library is fastest?

Fishery, for the simple reason that `build()` never persists anything unless you define `onCreate`. FactoryBot's `build_stubbed` is comparably fast within Ruby. factory_boy can be equally fast with `build()`, but its Django integration makes `create()` the path of least resistance, which is why Python suites tend to be slower in practice.

### Do I need a database to use these libraries?

No, and that is the point. factory_boy's `build()` strategy, FactoryBot's `build_stubbed` and Fishery's `build()` all return in-memory objects. Persistence only happens when you ask for it. Tests that only exercise business logic should never touch a database through a factory.

### Can I use FactoryBot outside Rails?

Yes. Install the `factory_bot` gem without the Rails integration and call `FactoryBot.define` in a support file. You lose the automatic factory path configuration and the Rails generators, but the core DSL works with plain Ruby objects.

### How do I handle unique email addresses across parallel tests?

Use a per-worker namespace. In factory_boy, thread the worker id into the sequence prefix; in FactoryBot, read `ENV["TEST_ENV_NUMBER"]`; in Fishery, seed the sequence from a helper. Relying on a bare incrementing counter is the most common cause of intermittent unique-constraint failures in parallel suites.

### What about generating realistic field values?

Fixture factories define structure; they are not great at producing realistic content. Pair them with a data generation library — our [test data generation comparison](../2026-09-21-test-data-generation-libraries-faker-gofakeit-mimesis-datafaker/) covers Faker and its ports in detail. For tests that must explore input space rather than specific examples, the [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) explains where generated data beats hand-written factories entirely, and the [Java assertion library comparison](../2026-07-24-java-testing-libraries-assertj-hamcrest-truth/) covers the assertion side of the same test suite.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "factory_boy vs FactoryBot vs Fishery in 2026: Which Fixture Factory Wins?",
  "description": "Practical comparison of factory_boy, FactoryBot and Fishery for building test fixtures, including real code samples, build strategies and performance pitfalls.",
  "datePublished": "2026-10-22",
  "dateModified": "2026-10-22",
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
