---
title: "Rails View Layers in 2026: Phlex vs ViewComponent vs Slim vs Haml"
date: "2026-10-22"
tags: ["ruby", "rails", "web-development", "frontend"]
draft: false
---

Rails applications do not usually rot in the model layer. They rot in `app/views` — a directory that starts with twelve tidy ERB files and ends with four hundred partials, three naming conventions, and a `shared/` folder nobody dares delete. The view layer decision you make in month one sets the ceiling on how painful the next three years are.

This is a practical comparison of the four options that matter in 2026: **Phlex**, **ViewComponent**, **Slim**, and **Haml** — measured against plain **ERB**, which is still what most teams actually ship.

## TL;DR: The Verdict in Five Lines

- **Starting a new Rails app with a design system** → **ViewComponent**. Sidecar templates, slots, previews, and a test story that scales.
- **You want views to be plain Ruby objects with no template files** → **Phlex**. Fastest of the four in practice, and the most testable.
- **You have a large Haml or Slim codebase that works** → **stay**. Migration cost is real and neither gem is in danger.
- **You want concise templates without adopting a component framework** → **Slim**, provided your team accepts whitespace-sensitive syntax.
- **You are unsure** → **ERB with strict locals**. It is the default for a reason, and Rails 7.1+ fixed its worst ergonomics problem.

The mistake to avoid: adopting a component framework on a legacy codebase and rewriting views before you have a component library worth reusing. That project fails in the same way every time.

## Comparison Table (Live Repository Data, October 2026)

| Option | Stars | Last commit | Unit of code | Template files | Composition | Testability | Escaping | Maturity risk |
|---|---|---|---|---|---|---|---|---|
| **Phlex** (`phlex-ruby/phlex`) | 1,530 | 2026-10-13 | Ruby class | None | Methods + `render` blocks | High (call `call` and assert) | Automatic, always | Low (small but active) |
| **ViewComponent** (`ViewComponent/view_component`) | 3,571 | 2026-10-21 | Ruby class + sidecar | `.html.erb` (or Slim/Haml) | Slots, collections, `with_` API | High (`render_inline`, Capybara matchers) | Automatic | Low (GitHub-maintained) |
| **Slim** (`slim-template/slim`) | 5,375 | 2026-10-04 | Template | `.slim` | Partials only | Medium (rendered output tests) | Automatic | Low (slow, steady) |
| **Haml** (`haml/haml`) | 3,828 | 2026-09-01 | Template | `.haml` | Partials only | Medium | Automatic | Low (maintenance mode) |
| **ERB** (Ruby stdlib / Rails) | — | — | Template | `.erb` | Partials + locals | Medium | Automatic | None (bundled) |

Stars are not a quality ranking here. Slim's 5,375 reflect fifteen years of adoption; Phlex's 1,530 reflect a four-year-old library that is nonetheless used in production by teams that benchmark their rendering.

## Decision Matrix: Ten Seconds to a Decision

| Your situation | Choose | Why |
|---|---|---|
| New app, multiple teams, shared UI kit | ViewComponent | Slots and previews give designers and QA a stable surface |
| API + a handful of server-rendered pages | ERB with strict locals | Zero new abstractions, nothing to maintain |
| Rendering-heavy pages (feeds, tables, dashboards) | Phlex | No template file parsing on the hot path; components are methods |
| Legacy Haml app with working views | Haml (unchanged) | Rewriting for style alone returns nothing |
| Team prefers indentation-based templates, no component framework | Slim | Concise output, good Rails integration |
| You need view tests that do not boot a browser | ViewComponent or Phlex | Both render to strings in-process |
| You are migrating a design system incrementally | ViewComponent | It coexists with ERB in the same view tree |

## ViewComponent — The Institutional Choice

ViewComponent treats a view as a Ruby class with an explicit interface. That sounds bureaucratic until you have three engineers editing the same partial and nobody knows which locals are required.

```ruby
# app/components/alert_component.rb
class AlertComponent < ViewComponent::Base
  def initialize(kind: :info, dismissible: false)
    @kind = kind
    @dismissible = dismissible
  end

  def css_class
    "alert alert--#{@kind}"
  end
end
```

```erb
<%# app/components/alert_component.html.erb %>
<div class="<%= css_class %>" role="alert">
  <%= content %>
  <% if @dismissible %>
    <button data-action="alert#dismiss" aria-label="Dismiss">&times;</button>
  <% end %>
</div>
```

Calling it is explicit, which is the entire point:

```erb
<%= render AlertComponent.new(kind: :warning, dismissible: true) do %>
  Your export is still processing.
<% end %>
```

Previews turn design review into a URL instead of a staging database hack:

```ruby
# test/components/previews/alert_component_preview.rb
class AlertComponentPreview < ViewComponent::Preview
  def warning_dismissible
    render AlertComponent.new(kind: :warning, dismissible: true) { "Disk usage above 90%" }
  end
end
```

And the test is a string assertion, not a browser session:

```ruby
class AlertComponentTest < ViewComponent::TestCase
  def test_renders_warning_class
    render_inline(AlertComponent.new(kind: :warning))
    assert_selector ".alert--warning"
    assert_selector ".alert[role='alert']"
  end
end
```

**Where it hurts:** the sidecar file convention means every component is two or three files, and `with_collection` plus slots can produce APIs that are harder to read than the partial they replaced. It also adds a `.html.erb` template indirection that Phlex removes entirely.

## Phlex — Views as Pure Ruby

Phlex components are Ruby objects whose `view_template` method builds HTML through a DSL. There is no template file, no `locals` hash, and no ERB compilation step at render time.

```ruby
# app/views/components/card.rb
class Components::Card < Phlex::HTML
  def initialize(title:, tone: :neutral)
    @title = title
    @tone = tone
  end

  def view_template(&block)
    article(class: "card card--#{@tone}") do
      h2(class: "card__title") { @title }
      div(class: "card__body", &block)
    end
  end
end
```

Rendering inside a Rails view or controller needs the `phlex-rails` integration gem, which wires helpers, `flash`, and `url_for` into the component context:

```ruby
# Gemfile
gem "phlex-rails"
```

```ruby
# app/views/posts/index.rb — a Phlex page object rendered by the controller
class Views::Posts::Index < Views::Base
  def initialize(posts:)
    @posts = posts
  end

  def view_template
    h1 { "Posts" }
    @posts.each do |post|
      render Components::Card.new(title: post.title, tone: :neutral) do
        p { truncate(post.body, length: 160) }
      end
    end
  end
end
```

**Where it hurts:** Phlex is younger. Gems that inject helpers into ERB (pagination, form builders, some admin panels) need adapters, and the `phlex-rails` layer occasionally trails a new Rails release. If your app depends on three such gems, check compatibility before committing.

## Slim — Concise Templates, Real Tradeoffs

Slim keeps the template-file model but strips HTML to its essentials. It is the least disruptive way to reduce view verbosity without adopting a component architecture.

```ruby
# Gemfile
gem "slim-rails"
```

```slim
/ app/views/posts/index.html.slim
h1 Posts

- @posts.each do |post|
  article.card
    h2.card__title = post.title
    p = truncate(post.body, length: 160)
    = link_to "Read more", post_path(post), class: "card__link"
```

**Where it hurts:** indentation is syntax. A misaligned line does not produce a lint error, it produces markup that renders almost correctly — the worst kind of bug. Editors handle it well; code review on a phone does not. Slim's release cadence is also slow, which is stability rather than abandonment, but plan for it.

## Haml — Still Fine, No Longer Exciting

Haml pioneered readable indentation-based markup and remains in maintenance mode with steady commits. If your application is already Haml, there is no technical reason to leave.

```haml
-# app/views/posts/index.html.haml
%h1 Posts

- @posts.each do |post|
  %article.card
    %h2.card__title= post.title
    %p= truncate(post.body, length: 160)
    = link_to "Read more", post_path(post), class: "card__link"
```

**Where it hurts:** the ecosystem has moved on. New component libraries and admin frameworks ship ERB or ViewComponent first, and Haml support arrives later or never. Staying is rational; starting fresh in Haml in 2026 is not.

## Does the Template Engine Actually Matter for Performance?

Yes, but less than most benchmarks imply. The mechanism matters more than the number:

- **Phlex** avoids parsing and compiling a template per render path; components are ordinary Ruby method calls.
- **ViewComponent** compiles its sidecar templates once and caches compiled methods, so steady-state rendering is close to ERB.
- **Slim and Haml** compile to Ruby methods on first render, so the runtime cost is comparable to ERB; their overhead shows up in compile time during development reloads.

Do not trust anyone's numbers, including published ones — measure your own pages. A minimal harness:

```ruby
# script/view_benchmark.rb
require "benchmark"
require_relative "../config/environment"

component = AlertComponent.new(kind: :info, dismissible: true)
iterations = 5_000

Benchmark.bm(24) do |x|
  x.report("ViewComponent") { iterations.times { ApplicationController.render(component, layout: false) } }
  x.report("ERB partial")    { iterations.times { ApplicationController.render(partial: "shared/alert", layout: false) } }
end
```

Run it against your heaviest page, not a synthetic card. In practice the difference between these engines is a few percent of total request time; the difference between a page that queries 40 rows and one that queries 400 is a factor of ten. Indexing and query count dominate.

## Pitfalls That Cost Real Weeks

**Tailwind and CSS scanning.** Class names built by interpolation (`"card--#{@tone}"`) are invisible to Tailwind's content scanner. Either safelist the variants in `tailwind.config.js` or write full class strings in a lookup table. This bites every component-framework migration.

**Escaping and `html_safe`.** All four options escape by default. The moment someone calls `raw` or `html_safe` on interpolated user data, the safety net is gone. In Phlex, `raw` is explicit and greppable — enforce a rule that it only appears in a reviewed allowlist.

**Whitespace-sensitive output.** Slim and Haml can change rendered whitespace, which breaks `inline-block` layouts and snapshot tests. When migrating, diff the HTML output, not the visual result.

**Caching keys.** Fragment caching keys must include the component's arguments. `cache @post do` silently serves the wrong variant when a component depends on `current_user`; use `cache [@post, current_user.role]` or a component-level `cache_key`.

**Helpers that assume a controller.** ViewComponent and Phlex both execute outside the traditional view context. Gems calling `controller.` or `request.` directly will fail. Wrap them in a component that receives the needed data as arguments — that is the correct dependency direction anyway.

**Rewriting everything at once.** The only migration that reliably finishes is incremental: new components in the new framework, old partials left alone, one page converted per sprint. A freeze-and-rewrite of the view layer competes with feature work and loses.

## Migration and Coexistence Notes

ViewComponent coexists cleanly with ERB — you can render a component from an ERB partial and vice versa, which makes incremental adoption low-risk. Phlex coexists too, but needs `phlex-rails` mounted and a `Views::Base` class for shared helpers. Slim and Haml coexist with ERB per-file, since Rails resolves templates by extension; keep one engine per directory to avoid confusion about which file wins.

Whichever route you take, treat the component API as the contract: keyword arguments with defaults, no reaching into `@` variables from templates, and a test per public component. Get that right and the engine underneath becomes a detail you can revisit later.

Before you commit, it is worth right-sizing the rest of the stack too. Our [Ruby app server comparison](../2026-09-08-ruby-app-servers-puma-passenger-unicorn-comparison/) covers the process model that renders these views, the [Ruby micro-framework guide](../2026-07-06-ruby-micro-web-frameworks-sinatra-roda-grape/) shows what the view layer looks like outside Rails, and the [Ruby validation library comparison](../2026-08-30-ruby-validation-libraries-dry-validation-activemodel-reform-comparison/) covers the input side of the same request.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rails View Layers in 2026: Phlex vs ViewComponent vs Slim vs Haml",
  "description": "Phlex, ViewComponent, Slim, Haml and ERB compared for Rails in 2026: live repository data, working component code, a decision matrix, performance mechanisms and the pitfalls that cost real weeks.",
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

## FAQ

### Is ViewComponent worth it for a small Rails app?

Usually not on day one. ViewComponent pays off when more than one person edits views or when the same UI element appears in several places with variants. For a single-developer app with a dozen templates, ERB with strict locals is simpler and faster to change.

### Phlex or ViewComponent: which is faster?

Phlex has a structural advantage because components are plain Ruby method calls with no template parsing, and in most reports it renders somewhat faster than template-based engines. The practical difference is small relative to database time. Benchmark your own heaviest page before treating speed as the deciding factor.

### Should I migrate an existing Haml codebase to ViewComponent?

Only if you have another reason to touch those views. A migration that produces identical HTML has no user-visible payoff and consumes the sprints you could spend on features. Convert opportunistically: new screens in ViewComponent, old Haml untouched until it needs changes anyway.

### Does Slim or Haml work with ViewComponent?

Yes. ViewComponent sidecar templates can be `.html.slim` or `.html.haml` if the corresponding Rails template handler gem is installed. You get component composition with indentation-based markup, at the cost of two abstractions instead of one.

### What happened to Hamlit and other Haml accelerators?

Hamlit and similar projects existed to make Haml fast enough to compete with ERB. Modern Haml compilation plus Rails template caching removed most of that gap, so the accelerators are no longer necessary for new work. Do not add one to a working application unless you have a profile showing view rendering as the bottleneck.

### How do I test views without a browser?

With ViewComponent use `render_inline` plus Capybara matchers in a component test, or `render_in_view_context` when helpers are needed. With Phlex, instantiate the component and call `call`, then assert on the returned string. For ERB, use `ApplicationController.render` in a request or view spec. None of these require a real browser.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
