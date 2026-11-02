---
title: "Phoenix LiveView vs Laravel Livewire vs Hotwire Turbo in 2026: Which Server-Rendered UI Stack Wins?"
date: "2026-11-02"
tags: ["elixir", "php", "ruby", "web-frameworks", "hotwire"]
draft: false
cover: "/img/screenshots/livewire-logo.jpg"
description: "LiveView, Livewire and Hotwire Turbo compared in 2026: real code, latency models, websocket scaling costs, and how to choose between stateful Elixir, request-per-click PHP, and HTML-over-the-wire Rails."
---

Single-page apps promised snappy interfaces and delivered a second backend: a JSON API, a state store, a router, and a build pipeline to keep them in sync. By 2026 a lot of teams have quietly walked that back — not to jQuery-style spaghetti, but to a third model where the server renders HTML and pushes updates over a socket, and the browser holds almost no application state.

Three stacks dominate that model, and they are not interchangeable:

- **Phoenix LiveView** (Elixir) — long-lived stateful process per connection.
- **Laravel Livewire** (PHP) — a request per interaction, with state rehydrated each round trip.
- **Hotwire Turbo** (Ruby on Rails, also usable elsewhere) — HTML over the wire with frames and streams, minimal custom JavaScript.

## TL;DR: the verdict

**Choose LiveView if you can run Elixir.** A persistent process per session means no rehydration cost, sub-100 ms interactions on a decent connection, and a programming model where a "component" is just a function with assigns. The price is BEAM operations: memory per connection and a runtime your team may not know.

**Choose Livewire if you are already on Laravel.** It gets you 90% of the interactivity for 10% of the rewrite, the ecosystem is enormous (23,585 stars and daily commits), and PHP hosting is cheap and boring. The price is a round trip per interaction and a state payload shipped on every request.

**Choose Turbo if you have a mature Rails app that mostly renders pages.** Frames and Streams turn existing controllers into dynamic UI without inventing a component protocol. The price is that fine-grained interactivity eventually needs Stimulus, and you are writing more JavaScript than the pitch suggests.

**Do not migrate a working app to change this layer.** All three are good. The failure mode is a rewrite that trades a solved problem for an operational one.

## Comparison table (live GitHub data, November 2026)

| | **Phoenix LiveView** | **Laravel Livewire** | **Hotwire Turbo** |
|---|---|---|---|
| Repo stars | 6,835 | 23,585 | 2,397 (turbo-rails) |
| Last push | 2026-10-30 | 2026-11-01 | 2026-07-01 |
| Language | Elixir | PHP | Ruby (Rails integration) |
| Update transport | WebSocket (persistent) | HTTP per interaction | WebSocket / SSE (Turbo Streams) |
| Server state | Kept per connection | Rehydrated per request | Mostly none |
| Interaction latency | Lowest (no round-trip state cost) | Round trip + rehydrate | Round trip, or broadcast |
| Memory per session | Highest | Lowest | Low |
| JS you must write | Near zero | Near zero | Low, grows with complexity |
| Best fit | Dashboards, live apps | Laravel CRUD apps | Content-heavy Rails apps |

Note on stars: `turbo-rails` is the Rails integration; the JavaScript core lives in `hotwired/turbo`, so raw popularity comparisons between these repos are not apples to apples.

## Decision matrix

| Your situation | Choose | Why |
|---|---|---|
| New real-time dashboard, team knows Elixir | LiveView | Processes map cleanly to user sessions |
| Existing Laravel app, forms feel clunky | Livewire | Add a component, keep the rest of the app |
| Rails monolith with server-rendered pages | Turbo | Frames upgrade what you already have |
| Team has zero Elixir/PHP/Rails experience | Turbo or Livewire | Smaller runtime learning curve than the BEAM |
| Thousands of idle connections on one box | LiveView | One process each, still cheap by web standards |
| Strict per-connection memory budget | Livewire | No persistent session state at all |
| Offline-tolerant or mobile-first UI | None of these | Ship a real client app |

## Phoenix LiveView: stateful processes, no rehydration

LiveView keeps a GenServer per connected user, holding assigns in memory. An event goes to the socket, the server runs your handler, and only the diff travels back.

```elixir
# mix.exs
defp deps do
  [
    {:phoenix, "~> 1.7"},
    {:phoenix_live_view, "~> 1.1"},
    {:phoenix_html, "~> 4.1"}
  ]
end
```

```elixir
# router.ex
scope "/", MyAppWeb do
  pipe_through :browser
  live "/counter", CounterLive
end
```

```elixir
# lib/my_app_web/live/counter_live.ex
defmodule MyAppWeb.CounterLive do
  use MyAppWeb, :live_view

  def mount(_params, _session, socket) do
    {:ok, assign(socket, count: 0, step: 1)}
  end

  def handle_event("increment", _params, socket) do
    {:noreply, update(socket, :count, &(&1 + socket.assigns.step))}
  end

  def handle_event("set_step", %{"step" => step}, socket) do
    {:noreply, assign(socket, step: String.to_integer(step))}
  end

  def render(assigns) do
    ~H"""
    <div>
      <p>Count: {@count}</p>
      <button phx-click="increment">+{@step}</button>
      <form phx-change="set_step">
        <select name="step">
          <option value="1">1</option>
          <option value="10">10</option>
        </select>
      </form>
    </div>
    """
  end
end
```

Because state lives in the process, `handle_event` reads and mutates assigns directly — there is no serialization step. That is also why LiveView can do things the other two cannot cheaply: `Phoenix.PubSub` broadcasts reach every subscribed socket, so one database change updates ten thousand dashboards without writing any client code.

```elixir
def handle_info({:order_updated, order}, socket) do
  {:noreply, assign(socket, order: order)}
end
```

Scale planning is concrete: each connected LiveView is a BEAM process, typically tens of kilobytes, and the BEAM schedules them across cores efficiently. What actually limits you is memory, not CPU — and the usual mistake is holding large query results in assigns instead of paginating.

## Laravel Livewire: components with a round trip

Livewire's model is refreshingly simple: a PHP class with public properties, a Blade template, and an HTTP request per interaction. The framework serializes public state into the page, then rehydrates it server-side on each click.

```bash
composer require livewire/livewire
php artisan make:livewire Counter
```

```php
<?php
// app/Livewire/Counter.php
namespace App\Livewire;

use Livewire\Component;

class Counter extends Component
{
    public int $count = 0;
    public int $step = 1;

    public function increment(): void
    {
        $this->count += $this->step;
    }

    public function updatedStep(): void
    {
        $this->count = 0;
    }

    public function render()
    {
        return view('livewire.counter');
    }
}
```

```blade
{{-- resources/views/livewire/counter.blade.php --}}
<div>
    <p>Count: {{ $count }}</p>
    <button wire:click="increment">+{{ $step }}</button>
    <select wire:model.live="step">
        <option value="1">1</option>
        <option value="10">10</option>
    </select>
</div>
```

Three details matter in practice. `wire:model.live` sends an update on every change (use `wire:model.blur` or `wire:model.lazy` when you do not want that). `wire:key` on list items prevents DOM reuse bugs when items are reordered. And `#[Locked]` on sensitive public properties stops a client from tampering with them — public properties are client-controlled by design, which surprises people once per project.

Livewire 3's biggest operational win over version 2 is that it no longer requires a per-component JavaScript payload bootstrapped on page load; components are registered once, and navigation between Livewire pages can use `wire:navigate` for SPA-like transitions while keeping the request-per-interaction model.

## Hotwire Turbo: HTML over the wire

Turbo replaces the full page swap with partial updates. Turbo Frames scope a request to one element; Turbo Streams push multi-target updates over a socket or SSE.

```ruby
# Gemfile
gem "turbo-rails"
```

```erb
<%# app/views/orders/_order.html.erb %>
<%= turbo_frame_tag dom_id(order) do %>
  <p><%= order.reference %> — <%= order.status %></p>
  <%= button_to "Ship", ship_order_path(order), method: :patch %>
<% end %>
```

The controller stays ordinary Rails — no special responder — as long as the response renders inside the same frame:

```ruby
class OrdersController < ApplicationController
  def ship
    order = Order.find(params[:id])
    order.ship!
    respond_to do |format|
      format.turbo_stream
      format.html { redirect_to orders_path }
    end
  end
end
```

```erb
<%# app/views/orders/ship.turbo_stream.erb %>
<%= turbo_stream.replace dom_id(@order) do %>
  <%= render @order %>
<% end %>
```

Broadcasts make it push-based without writing a client:

```erb
<%# app/models/order.rb %>
after_update_commit -> {
  broadcast_replace_later_to "orders", target: self
}
```

Turbo 8 added page morphing, which refreshes a page while preserving scroll position and form state — a genuine improvement for content sites where a full reload loses the reader's place. The honest limitation: Turbo gives you coarse-grained updates. A live-search box with debouncing, keyboard shortcuts, and optimistic UI still needs Stimulus controllers, and the "no JavaScript" promise quietly becomes "less JavaScript, in a different place."

## Pitfalls that show up in production

**1. LiveView memory grows with assigns, not users.** Holding a full result set in assigns multiplies by connections. Paginate, and stream large lists with `stream/3` instead of assigning a big array.

**2. Livewire public properties are user input.** Anything `public` can be set by the client unless marked `#[Locked]`. Validate on the server in `updated*` hooks; never trust a hidden property for authorization.

**3. Websocket reconnection is not free.** LiveView reconnects and re-mounts by default, losing in-memory state unless you persist it. Design forms so a reconnect does not wipe a half-typed record.

**4. Turbo Frames cannot jump outside their frame.** A redirect that targets a different frame fails silently — the classic symptom is "the button does nothing." Use `turbo_stream` responses or `data-turbo-frame="_top"` deliberately.

**5. Latency is physical.** Livewire's per-interaction round trip is fine on a 30 ms connection and painful on a 300 ms mobile link. Show pending states (`wire:loading`) or the UI feels broken on exactly the users you care about.

**6. Sticky sessions bite on multi-node deploys.** LiveView requires socket affinity per connection; Livewire needs consistent session storage; Turbo Streams need a shared pub/sub (Redis) across nodes. Plan the infrastructure before the feature.

## FAQ

**Is LiveView faster than Livewire?**
For interaction latency, usually yes: LiveView keeps state in memory and sends only diffs, while Livewire pays a full HTTP round trip plus state rehydration per interaction. On a fast connection the difference is imperceptible; on poor mobile networks it is noticeable.

**Can I use Livewire without Laravel?**
It is tightly coupled to Laravel's container, Blade, and session handling. Technically some pieces can be adapted, but the supported path is Laravel — if you are not on Laravel, evaluate Turbo or LiveView instead.

**Does Hotwire require Rails?**
No. Turbo is framework-agnostic JavaScript and works with any server that returns HTML; the `turbo-rails` gem provides the Rails integration. Most documentation and examples assume Rails, which shapes the ecosystem more than the technology does.

**Which stack uses the least server memory per user?**
Livewire, because nothing persists between requests. LiveView holds a process per connection, which is still cheap relative to a thread-per-connection model but measurable at tens of thousands of concurrent sessions.

**Do any of these work without JavaScript?**
All three degrade to normal HTML for initial page loads, but interactive updates require JavaScript. Turbo is the most forgiving: links and forms still work as plain HTTP requests if the JavaScript fails to load.

**What about SEO?**
All three render real HTML on first load, so crawlers see complete pages — a structural advantage over client-rendered SPAs. LiveView and Turbo pass the initial content in the response body; Livewire does the same for the first render.

## Related reading

For the framework layer beneath these UI stacks, our [Elixir web frameworks comparison](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) covers Phoenix itself, and the [Erlang web frameworks guide](../2026-10-01-erlang-web-frameworks-nitrogen-nova-zotonic-comparison/) shows where the BEAM's older stacks fit. If you are weighing a Node-based alternative, the [Node.js HTTP frameworks comparison](../2026-07-28-nodejs-http-frameworks-express-koa-fastify-hono-comparison/) covers the request/response side of the same decision.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Phoenix LiveView vs Laravel Livewire vs Hotwire Turbo in 2026: Which Server-Rendered UI Stack Wins?",
  "description": "LiveView, Livewire and Hotwire Turbo compared in 2026: real code, latency models, websocket scaling costs, and how to choose between stateful Elixir, request-per-click PHP, and HTML-over-the-wire Rails.",
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
