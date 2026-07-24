---
title: "Self-Hosted Elixir JSON Libraries: Jason vs Poison vs Jsonex vs Jsonrs"
date: "2026-07-25"
tags: ["elixir", "json", "serialization", "functional-programming", "beam", "erlang", "libraries", "performance"]
draft: false
---

## Introduction

In the Elixir ecosystem, JSON parsing and encoding is one of the most common operations — from API responses to configuration files and message passing between services. While Erlang's built-in string handling is powerful, Elixir's functional programming paradigm demands libraries that are both fast and idiomatic. Choosing the right JSON library affects your entire application's throughput, especially in high-traffic Phoenix web applications and real-time systems.

The BEAM VM's unique characteristics — lightweight processes, immutability, and preemptive scheduling — mean that JSON library performance doesn't follow the same rules as in Python or JavaScript. Libraries that leverage dirty schedulers, NIFs (Native Implemented Functions), and binary pattern matching can achieve dramatic speed improvements over pure-Erlang implementations.

This article compares the four most widely-used JSON libraries in the Elixir ecosystem: Jason, Poison, Jsonex, and Jsonrs — covering performance, API design, Phoenix integration, and real-world deployment considerations.

## Comparison Table

| Feature | Jason | Poison | Jsonex | Jsonrs |
|---------|-------|--------|--------|--------|
| GitHub Stars | ~1,700 | ~2,100 | ~200 | ~300 |
| Implementation | Pure Elixir + NIFs | Pure Elixir (legacy) | Erlang native | Rust NIF via Rustler |
| Phoenix Default | ✅ Yes (since 1.4) | ❌ No | ❌ No | ❌ No |
| Encoding Speed | Fast | Moderate | Very Fast | Extremely Fast |
| Decoding Speed | Fast | Moderate | Fast | Extremely Fast |
| Streaming Support | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Custom Encoders | ✅ Protocol-based | ✅ Protocol-based | ✅ Callback-based | ✅ Derive macro |
| Memory Efficiency | Good | Moderate | Excellent | Excellent |
| Active Maintenance | ✅ Yes | ⚠️ Minimal | ✅ Yes | ✅ Yes |

## Jason: The Modern Standard

Jason (JSON Aeson) is the de-facto standard JSON library for Elixir, serving as the default JSON engine in Phoenix since version 1.4. It was built as a drop-in replacement for Poison with significant performance improvements using binary pattern matching and NIF optimizations.

### Installation

Add to your `mix.exs`:

```elixir
defp deps do
  [
    {:jason, "~> 1.4"}
  ]
end
```

### Basic Usage

```elixir
# Encoding
json = %{name: "Elixir", type: "functional", year: 2011}
|> Jason.encode!()
# => "{\"name\":\"Elixir\",\"type\":\"functional\",\"year\":2011}"

# Decoding
{:ok, map} = Jason.decode(~s({"version":"1.16"}))
# => {:ok, %{"version" => "1.16"}}

# With atoms as keys
{:ok, map} = Jason.decode(~s({"key":"value"}), keys: :atoms)
# => {:ok, %{key: "value"}}

# Pretty printing
Jason.encode!(%{data: [1, 2, 3]}, pretty: true)
```

### Phoenix Integration

```elixir
# config/config.exs
config :phoenix, :json_library, Jason

# In a controller
def show(conn, %{"id" => id}) do
  user = Accounts.get_user!(id)
  json(conn, %{name: user.name, email: user.email})
end
```

### Protocol-Based Custom Encoders

```elixir
defimpl Jason.Encoder, for: User do
  def encode(%User{name: name, email: email}, opts) do
    Jason.Encode.map(%{name: name, email: email}, opts)
  end
end
```

Jason's key advantage is its deep integration with the Elixir ecosystem. Plug, Phoenix, Ecto, and Absinthe all use Jason as their default JSON codec. Its protocol-based extension system (via `Jason.Encoder`) integrates cleanly with Elixir's behaviours.

## Poison: The Original Pioneer

Poison was the original high-performance JSON library for Elixir, first released in 2014. It set the standard for Elixir JSON handling and inspired Jason's API design. While still functional, Poison has been largely superseded by Jason for new projects.

```elixir
# mix.exs
defp deps do
  [{:poison, "~> 5.0"}]
end

# Encoding with Poison
Poison.encode!(%{status: "ok", count: 42})
# => "{\"status\":\"ok\",\"count\":42}"

# Decoding
Poison.decode!(~s({"key":"value"}))
# => %{"key" => "value"}

# Custom encoder protocol
defimpl Poison.Encoder, for: MyStruct do
  def encode(struct, options) do
    Map.from_struct(struct) |> Poison.Encoder.Map.encode(options)
  end
end
```

Poison remains useful for legacy applications that haven't migrated to Jason, and for projects that specifically depend on its decoding behaviour for edge cases. However, it's no longer actively maintained (last significant release was in 2020), and new projects should use Jason unless there's a specific compatibility requirement.

## Jsonex: The Erlang-Native Speedster

Jsonex is built directly in Erlang and leverages the BEAM VM's binary matching capabilities at a lower level than pure-Elixir libraries can. It uses Erlang's native record types and pattern matching on binaries for extremely fast parsing.

```elixir
# mix.exs — Jsonex is an Erlang library with Elixir wrapper
defp deps do
  [{:jsonex, "~> 0.3"}]
end

# Decoding with Jsonex
{:ok, result} = Jsonex.decode(~s({"items":[1,2,3]}))
# => {:ok, %{"items" => [1, 2, 3]}}

# Encoding
{:ok, json} = Jsonex.encode(%{hello: "world"})
# => {:ok, "{\"hello\":\"world\"}"}

# Strict mode for production
result = Jsonex.decode!(~s([1,2,3]), strict: true)
```

Jsonex excels in scenarios where every microsecond counts — message brokers, WebSocket handlers, and telemetry pipelines where JSON parsing is the bottleneck. Its Erlang foundation means it integrates naturally with OTP applications and can be called from both Elixir and Erlang code.

## Jsonrs: The Rust-Powered Newcomer

Jsonrs leverages Rust's serde ecosystem via Rustler NIFs to bring C/Rust-level performance to Elixir JSON processing. It's the newest entrant but shows the most aggressive benchmark results.

```elixir
# mix.exs
defp deps do
  [{:jsonrs, "~> 0.3"}]
end

# Encoding (returns iodata for zero-copy output)
iodata = Jsonrs.encode!(%{items: [1, 2, 3, 4, 5]})
# Returns iodata for efficient socket writes

# Decoding
{:ok, result} = Jsonrs.decode(~s({"count":1000}))
# => {:ok, %{"count" => 1000}}

# Derive macro for automatic struct encoding
defmodule Order do
  @derive {Jsonrs, only: [:id, :total, :status]}
  defstruct [:id, :total, :status, :internal_note]
end
```

Jsonrs is particularly effective for applications that process large JSON payloads — log aggregation pipelines, data import/export services, and API gateways handling hundreds of megabytes of JSON per second. The Rust NIF approach means the JSON parsing runs on a separate dirty scheduler thread, avoiding blocking the BEAM's main scheduler.

## Performance Benchmarks and Scaling Considerations

In independent benchmarks comparing these libraries, Jsonrs consistently leads in both encoding and decoding throughput, particularly for payloads larger than 1KB. On a standard 8-core server:

- Jsonrs decodes a 100KB JSON payload approximately 3-4x faster than Jason and 10-12x faster than Poison
- Jason performs respectably for small payloads (< 1KB) where its NIF overhead is negligible
- Jsonex matches or exceeds Jason for decoding but doesn't support streaming
- For encoding, Jsonrs returns iodata (lists of binaries) which enables zero-copy socket writes — a critical advantage for HTTP servers

For Phoenix applications, the practical recommendation is to use Jason for most use cases (it's the default and well-tested) and only switch to Jsonrs or Jsonex when profiling shows JSON processing as a measurable bottleneck. Pre-mature optimization to Rust NIFs adds deployment complexity (Rust toolchain requirement) without proportional benefit for typical CRUD applications.

For API gateways or event processing pipelines that handle millions of JSON documents daily, Jsonrs or Jsonex can reduce CPU usage by 40-60% compared to Jason alone, translating directly to lower cloud infrastructure costs.

## Why Self-Host Your Elixir JSON Pipeline?

Building a self-hosted data pipeline in Elixir gives you complete control over serialization performance. Unlike managed API gateways where you pay per request, a Phoenix application using Jason or Jsonrs processes JSON at the speed of the BEAM VM — no external service calls, no per-GB fees, no vendor-specific JSON quirks. The entire JSON pipeline runs in your own OTP application, where you control encoding formats, error handling, and performance tuning.

For teams already using Elixir and Phoenix, the JSON library choice is a zero-cost optimization — switching from Poison to Jason is often a single-line config change with no code modifications. For organizations processing telemetry data, WebSocket messages, or ETL pipelines, see our [binary serialization comparison](../2026-06-19-binary-serialization-frameworks-bincode-borsh-postcard-rkyv/) for alternatives when JSON overhead becomes the bottleneck.

If you're evaluating the broader functional programming landscape, our [Haskell web frameworks guide](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) explores how other functional ecosystems handle web serialization, and our [C# functional programming patterns](../2026-07-05-csharp-functional-programming-languageext-fsharp-patterns/) covers cross-paradigm serialization approaches.

## FAQ

### Should I use Jason or Poison for a new Phoenix project?

Use Jason. It's the default in Phoenix since 1.4, actively maintained, and faster than Poison in all common scenarios. Poison is effectively in maintenance mode and only needed for legacy codebases.

### When should I switch to Jsonrs or Jsonex?

Switch when profiling shows JSON encoding/decoding consuming more than 10% of your application's CPU time. Jsonrs is ideal for high-throughput APIs processing large payloads; Jsonex is better when you want to avoid Rust NIF complexity while still getting Erlang-native speed.

### Does Jason support streaming large JSON arrays?

Yes. Jason provides `Jason.Argonaut` for streaming decode, and you can use `Enum.reduce/3` with `Jason.decode/2` on individual chunks. For very large files, consider using Erlang's `jsx` library with streaming callbacks.

### How do I handle JSON keys with atoms vs strings in Elixir?

Jason decodes JSON object keys as strings by default (safe). Use `keys: :atoms` to convert keys to atoms, but only for trusted input — creating atoms from user input can exhaust the atom table. For untrusted data, use `keys: :atoms!` or manually convert with `Map.new(fn {k, v} -> {String.to_existing_atom(k), v} end)`.

### Can I use multiple JSON libraries in the same project?

Yes. Elixir modules are namespaced, so `Jason.encode!/1` and `Poison.encode!/1` coexist without conflicts. This is useful during migrations: use Jason for new code while existing Poison-dependent modules continue to work.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Elixir JSON Libraries: Jason vs Poison vs Jsonex vs Jsonrs",
  "description": "Comprehensive comparison of Elixir JSON libraries for self-hosted Phoenix and BEAM applications: Jason, Poison, Jsonex, and Jsonrs covering performance, API design, and production deployment patterns.",
  "datePublished": "2026-07-25",
  "dateModified": "2026-07-25",
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
  },
  "articleSection": "Elixir, JSON, Serialization",
  "keywords": ["elixir", "json", "jason", "poison", "jsonex", "jsonrs", "serialization", "phoenix", "beam", "erlang"]
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
