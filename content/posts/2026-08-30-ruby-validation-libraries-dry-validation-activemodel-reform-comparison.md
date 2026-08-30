---
title: "dry-validation vs ActiveModel::Validations vs Reform in 2026: Which Ruby Validation Library?"
date: "2026-08-30"
tags: ["ruby", "validation", "dry-rb", "rails", "reform", "activemodel"]
draft: false
cover: "/img/screenshots/dry-validation-cover.jpg"
---

Every Ruby developer eventually hits the same wall: the model file bloats with 40 lines of `validates` macros, the controller starts duplicating rules for API input, and nobody can tell you where validation logic is *supposed* to live. In 2026 the Ruby ecosystem offers three mature answers — ActiveModel::Validations baked into Rails, the dry-rb ecosystem's dry-validation, and Trailblazer's Reform form objects — and they represent fundamentally different philosophies about where validation belongs. This guide compares them with real code, current GitHub data, and migration advice so you can stop guessing.

## TL;DR / Quick Verdict

**If you live inside Rails and your validation needs are conventional, use ActiveModel::Validations** — zero extra gems, i18n out of the box, and every tutorial on earth covers it. **If you want schema-first, composable validation that works outside Rails and handles complex coercion, use dry-validation.** **If your pain is "validation rules crammed into models," use Reform** — it moves validation into form objects and keeps models as dumb data holders. For a greenfield Rails API, the pragmatic 2026 answer is dry-validation with a thin ActiveModel compatibility layer, or Reform if you buy the Trailblazer architecture.

## Quick Comparison Table (August 2026, live GitHub data)

| Dimension | ActiveModel::Validations | dry-validation | Reform |
|---|---|---|---|
| GitHub repo | rails/rails | dry-rb/dry-validation | trailblazer/reform |
| GitHub stars | 58,741★ | 1,422★ | 2,488★ |
| Last commit | 2026-08-30 | 2026-05-10 | 2025-08-25 |
| License | MIT | MIT | MIT |
| First released | 2004 (Rails 1.0) | 2014 | 2014 |
| Paradigm | Model-centric macros | Schema-first, functional | Form objects |
| Works without Rails | Yes (active_model gem) | Yes (zero Rails deps) | Yes (needs reform-rails for Rails) |
| Coercion built in | No | Yes (params schema) | Yes (via dry-types/ActiveModel) |
| i18n error messages | Built-in | Via dry-schema | Delegates to ActiveModel |
| Nested object validation | Through accepts_nested_attributes | Yes (schemas compose) | Yes (nested forms) |
| Community size | Massive | Medium (dry-rb family) | Small but committed |
| Best for | Rails apps, quick wins | Complex input schemas, API contracts | Separation of concerns at scale |

## Scenario Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Conventional Rails model validation | ActiveModel::Validations | Zero setup, i18n, generators, and every plugin integrates with it |
| API request/response contract validation | dry-validation | Schema DSL handles params, coercion, and nested structures cleanly |
| Validation logic leaking into models | Reform | Form objects isolate validation from persistence |
| Multi-model forms (has_many editing) | Reform | Nested forms mirror the object graph |
| Non-Rails Ruby app (Sinatra, dry-web) | dry-validation | No Rails dependency at all |
| Quick prototype on Rails | ActiveModel::Validations | Fastest path; migrate later if pain appears |

## ActiveModel::Validations — The Rails Default

ActiveModel::Validations is the validation subsystem extracted from Rails into the standalone `active_model` gem. The `rails/rails` repo sits at **58,741★ with commits through 2026-08-30** — it is the most used validation stack in Ruby by an enormous margin. The core idea: include `ActiveModel::Validations` in any class, declare `validates` macros, and get `valid?`, `errors`, and `save`-time checking for free.

```ruby
class User
  include ActiveModel::Validations
  attr_accessor :email, :age

  validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :age, numericality: { only_integer: true, greater_than: 0 }
end

user = User.new(email: "not-an-email", age: -3)
user.valid?                          # => false
user.errors.full_messages
# => ["Email is invalid", "Age must be greater than 0"]
```

What makes it the default:

- **Zero installation.** In Rails it is already loaded; outside Rails, `gem "activemodel"` gives you the same API.
- **i18n built in.** Error messages come from locale files; `errors.full_messages` localizes automatically.
- **Rich validator library.** `presence`, `format`, `numericality`, `length`, `inclusion`, `uniqueness` (with ActiveRecord), `confirmation`, plus custom validators via `validate` and `validates_with`.
- **Ecosystem gravity.** Gems like `validates_timeliness`, `email_validator`, and `strong_parameters` all assume this API.

**Where it hurts:** validation and business rules live on the model, so models grow fat; coercion is not built in (`before_validation` hooks get ugly fast); and the DSL is imperative rather than declarative about *structure*. For a simple app this is a feature, not a bug. For a large one, it is the exact pain Reform and dry-validation exist to solve.

## dry-validation — Schema-First Validation Outside Rails

dry-validation is the validation layer of the dry-rb ecosystem, sitting at **1,422★ with its last commit on 2026-05-10** in `dry-rb/dry-validation`. It is built on dry-schema and dry-types, and it flips the ActiveModel model: instead of attaching rules to objects, you define a standalone *contract* — a schema with coercion rules plus custom rules — and execute it against any input hash. This makes it ideal for API boundaries, service objects, and anything where input is untrusted.

```ruby
require "dry/validation"

class NewUserContract < Dry::Validation::Contract
  params do
    required(:email).filled(:string, format?: URI::MailTo::EMAIL_REGEXP)
    required(:age).filled(:integer, gt?: 0)
  end

  rule(:age) do
    key.failure("must be at least 18") if value < 18
  end
end

contract = NewUserContract.new
result = contract.call(email: "bad", age: "12")
result.success?          # => false
result.errors.to_h
# => { email: ["is in invalid format"], age: ["must be at least 18"] }
```

Why teams adopt it:

- **Coercion is first-class.** `params` blocks coerce strings to integers, strip unknown keys, and type-check via dry-types. `age: "12"` becomes `12` before your rule runs.
- **Composable contracts.** A contract can embed another contract (`required(:address).hash(AddressContract.schema)`), so you build a validation tree instead of one giant class.
- **Rails-agnostic.** Zero Rails dependencies; runs in Sinatra, dry-web, plain scripts, and background jobs.
- **Functional API.** `call` returns an immutable `Result` — no global state, trivially testable.

**Where it hurts:** the API changed significantly between 0.x and 1.x (`Dry::Validation.Params` → `Dry::Validation::Contract`), old tutorials are misleading, and error message i18n requires dry-schema configuration. Also, it does not integrate with ActiveRecord automatically — you write the adapter glue yourself.

## Reform — Form Objects That Rescue Fat Models

Reform, from the Trailblazer framework family, is at **2,488★ with its last commit on 2025-08-25** in `trailblazer/reform`. Its thesis is simple: validation does not belong on the model. You define a `Reform::Form` class that declares properties, validations, and nesting — then call `validate`, `sync`, and `save` against it. The model stays a dumb data holder, and the form is the only place business rules live.

```ruby
class AlbumForm < Reform::Form
  property :title
  validates :title, presence: true

  property :artist do
    property :name
    validates :name, presence: true
  end
end

form = AlbumForm.new(album)
form.validate(title: "The Wall", artist: { name: "Pink Floyd" }) # => true
form.sync                       # writes back to the model
form.save                       # persists (optional, calls model.save)
```

Key characteristics:

- **Validation moves out of models.** `form.validate(params)` runs all rules; `form.errors` returns ActiveModel-style messages.
- **Nested forms.** `property :artist do ... end` mirrors has_one/has_many — editing a parent and its children in one form is the flagship use case.
- **Coercion and composition.** Forms can use dry-validation or ActiveModel under the hood (via `reform-rails` for Rails integration), and a form can `compose` multiple models.
- **Small, clean API.** `initialize`, `validate`, `errors`, `sync`, `save`, `prepopulate!` — five methods do almost everything.

**Where it hurts:** it is the least actively maintained of the three (last push 2025-08-25) and the community is small. Reform 2.2 no longer auto-loads Rails files — you must add `reform-rails` — and mixing Trailblazer concepts into a conventional Rails app has a real learning curve. If your team is not on board with the form-object philosophy, Reform will feel like ceremony.

## Migration and Adoption Pitfalls

- **dry-validation 0.x → 1.x is a breaking migration.** `Dry::Validation.Params { ... }` schemas must be rewritten as `Dry::Validation::Contract` with explicit `params` and `rule` blocks. Old blog posts from 2018–2020 will actively mislead you; follow the dry-rb.org docs.
- **Don't mix three philosophies in one codebase.** Choose model-based, schema-based, or form-based validation and stay consistent. Mixed stacks produce "why does this model validate but that one doesn't" bugs that cost real debugging hours.
- **Coercion hides type errors.** dry-validation's `params` block silently coerces `"12"` → `12`. That is usually what you want at an API boundary, but if you need strictness, use `schema` blocks (no coercion) for internal service calls.
- **Reform needs reform-rails in Rails.** Reform 2.2 dropped automatic Rails loading. Forgetting the `reform-rails` gem produces confusing `ActiveModel::Validations` constant errors at boot.
- **Uniqueness validation needs a database.** `validates_uniqueness_of` is an ActiveRecord feature, not an ActiveModel one. Neither dry-validation nor Reform validates uniqueness without a persistence layer — do it in the model or the repository.
- **Error message consistency matters for API consumers.** If you expose `errors.to_h` from dry-validation to a frontend that expects ActiveModel's `errors.full_messages`, you will get format drift. Standardize the error envelope at the API boundary, not per controller.
- **Performance is rarely the problem; structure is.** All three are fast enough for web request volumes. Choose based on where rules live, not micro-benchmarks.

## How They Compare in Practice

**Rails API with JSON input:** dry-validation contracts at the controller/service boundary, with ActiveModel::Validations still on models for database-backed rules like uniqueness. This is the most common production pattern in 2026.

**Legacy Rails monolith:** stick with ActiveModel::Validations. The migration cost of moving hundreds of model validations into forms or contracts far exceeds any benefit unless the model files are genuinely unmaintainable.

**Non-Rails Ruby services (Sinatra, dry-system, plain workers):** dry-validation is the natural fit — no Rails baggage, standalone contracts, and its functional style plays well with service objects.

**Complex multi-model screens (admin panels, checkout flows):** Reform's nested forms are the strongest tool here, provided the team accepts the Trailblazer idiom. The has_many editing flow — where one form handles a parent plus its children — is painful in both ActiveModel and dry-validation by comparison.

For more Ruby ecosystem comparisons, see our [Ruby ORM roundup covering ActiveRecord, Sequel, and ROM.rb](../2026-07-30-ruby-orm-libraries-activerecord-sequel-rom-rb/), the [Ruby micro-framework comparison of Sinatra, Roda, and Grape](../2026-07-06-ruby-micro-web-frameworks-sinatra-roda-grape/), and our [Ruby background job processor guide for Sidekiq, Shoryuken, and Sucker Punch](../2026-07-28-ruby-background-job-processors-sidekiq-shoryuken-faktory-sucker-punch-comparison/) — the trio of articles that cover the typical Rails service stack.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "dry-validation vs ActiveModel::Validations vs Reform in 2026: Which Ruby Validation Library?",
  "description": "2026 comparison of Ruby validation libraries: ActiveModel::Validations (rails 58,741 stars), dry-validation (dry-rb), and Reform (Trailblazer). Real code, migration pitfalls, and scenario-based recommendations.",
  "datePublished": "2026-08-30",
  "dateModified": "2026-08-30",
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

## FAQ

**Is ActiveModel::Validations usable outside Rails?** Yes. The `activemodel` gem is standalone — `gem "activemodel"` and `include ActiveModel::Validations` works in any Ruby project, though database-backed validators like uniqueness require ActiveRecord.

**Is dry-validation still maintained in 2026?** Yes. The `dry-rb/dry-validation` repo had its last commit on 2026-05-10 and the dry-rb family is actively developed, but the 1.x API is stable and the ecosystem has moved its focus to dry-schema and dry-types, which underpin it.

**Does Reform work with Rails 8?** Yes, with the `reform-rails` gem. Reform 2.2+ requires explicitly loading `reform-rails` for ActiveModel integration; the form API itself is framework-agnostic.

**Which library should I use for validating API request params?** dry-validation. Its `params` schema coerces types, strips unknown keys, and produces structured error hashes — exactly what API boundaries need. ActiveModel works but lacks built-in coercion.

**Can I combine dry-validation with ActiveRecord?** Yes. A common pattern: dry-validation contracts at the API boundary, plus a small adapter that maps contract errors into `ActiveModel::Errors` for form rendering. Some teams skip the adapter and render contract errors directly.

**Which is better for a large legacy Rails app?** ActiveModel::Validations, unless model bloat is actively hurting you. Migrating hundreds of `validates` macros to forms or contracts is expensive; do it incrementally for the worst models only.

**Do these libraries support localization of error messages?** ActiveModel has first-class i18n. dry-validation supports i18n via dry-schema configuration. Reform delegates to ActiveModel's error handling when integrated, so it inherits i18n automatically.

**How does Reform handle nested has_many forms?** With nested forms: `collection :songs do ... end` inside a form class. `validate(params)` populates the nested forms, and `sync`/`save` write the whole graph — the strongest multi-model workflow of the three.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
