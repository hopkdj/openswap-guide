---
title: "Elixir HTTP Clients in 2026: Tesla vs Req vs HTTPoison — Which One Should You Actually Use?"
date: "2026-08-21"
tags: ["elixir", "http", "api-client", "developer-tools"]
cover: "/img/screenshots/req-cover.jpg"
draft: false
---

Every Elixir application that talks to the outside world — a Phoenix backend calling a payment gateway, a worker fetching third-party data, a script that pings a REST API — starts with the same question: which HTTP client? The three serious contenders in 2026 approach the problem from completely different directions: HTTPoison is the simple hackney-based workhorse that dominated the early ecosystem, Tesla is a middleware pipeline inspired by Ruby's Faraday, and Req is the batteries-included, step-based client from Elixir core team member Wojtek Mach that has become the de-facto modern default. This guide compares all three with live GitHub stats and code taken directly from the official repositories.

**TL;DR:** Use **Req** for new projects — it ships batteries included (automatic JSON encoding/decoding, redirects, retries, base URLs, auth helpers, streaming) with a step-based design that stays extensible, and it is maintained by an Elixir core team member. Reach for **Tesla** when you want an explicit, middleware-style pipeline you can inspect and reuse across many API clients, and you are comfortable choosing and configuring your own adapter. **HTTPoison** remains a fine, minimal client — but its hackney foundation now requires Erlang/OTP 27+, and it offers none of the conveniences of Req, so reserve it for legacy codebases. One rule of thumb: greenfield Phoenix project → Req; many small API clients sharing middleware → Tesla; inheriting a 2020-era codebase → HTTPoison.

## Quick Comparison: Tesla vs Req vs HTTPoison

| Dimension | Tesla | Req | HTTPoison |
|---|---|---|---|
| **Repository** | `elixir-tesla/tesla` | `wojtekmach/req` | `edgurgel/httpoison` |
| **GitHub stars** | 2,076 | 1,325 | 2,290 |
| **Last push** | 2026-08-19 | 2026-08-19 | 2026-07-05 |
| **License** | MIT | Apache-2.0 | MIT |
| **Architecture** | Middleware stack + pluggable adapters | Steps pipeline (v0.8: step wrappers) | Thin wrapper over hackney |
| **Default adapter** | `:httpc` (Erlang built-in) | Finch | hackney |
| **Auto JSON encode/decode** | Via `Tesla.Middleware.JSON` | Built-in | No |
| **Automatic retries** | `Tesla.Middleware.Retry` | Built-in | No |
| **Streaming responses** | Via adapter | `Req.stream/4` | No |
| **Test helpers** | Mock adapter | `Req.Test` (Plug-based) | Manual pattern matching |
| **OTP requirement** | Any | Any | OTP 27+ (v3.x) |

The star counts are close — HTTPoison still leads the trio at 2,290 — but the maintenance trajectory favors Req and Tesla, both of which were pushed within days of this article's publication. HTTPoison's 3.x line tightened its requirements (Erlang/OTP 27 or later, Elixir 1.17 or later) to track its hackney 4.0 dependency, which is a real constraint for older deployments.

## Use-Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| New Phoenix/Elixir project, first HTTP call | **Req** | Batteries included: JSON, redirects, retries, auth, streaming |
| Many small API clients sharing behavior | **Tesla** | Compose reusable middleware once, reuse across clients |
| Test HTTP calls against a Plug router | **Req** | `Req.Test` mounts a plug and stubs requests in-process |
| Simple synchronous GET/POST in a script | **HTTPoison** or **Req** | Both do it in one line; Req adds auto-decode |
| Streaming large responses (SSE, downloads) | **Req** | `Req.stream/4` with callbacks or `into:` collectable |
| Legacy codebase already on hackney | **HTTPoison** (stay) | Stable and functional; migrate when adding new features |
| Fine-grained control of the socket layer | **Tesla** | Explicit adapter choice (Mint, Finch, Hackney, Gun) |
| AWS API calls with SigV4 | **Req** | Built-in `put_aws_sigv4` step |

## Req — The Batteries-Included Default

Req (1,325 stars, Apache-2.0, last push 2026-08-19) is maintained by Wojtek Mach, a core Elixir team member, and its README's pitch is a one-liner that demonstrates the whole philosophy:

```elixir
Mix.install([
  {:req, "~> 0.8.0-rc"}
])

Req.get!("https://api.github.com/repos/wojtekmach/req").body["description"]
#=> "Req is a batteries-included HTTP client for Elixir."
```

That single call gets you response body decoding, redirect following, retry on errors, and more — because virtually every feature is implemented as a composable *step* in a request pipeline. A POST with JSON is equally direct:

```elixir
iex> Req.post!("https://httpbingo.org/post", json: %{x: 1, y: 2}).body["json"]
%{"x" => 1, "y" => 2}
```

The feature list from the official README reads like a checklist of what production clients actually need: request body compression, opt-in decompression (gzip, brotli, zstd), urlencoded/multipart/JSON encoding, base URLs, templated path params, Basic/Digest/Bearer/netrc auth, AWS SigV4, range requests, request and response streaming, checksum verification, and `Req.Test` — Plug-based HTTP mocks and stubs that let you test against an in-process plug instead of a live server. The default adapter is Finch, the performance-focused HTTP client built on Mint and NimblePool.

One thing to know before upgrading: **Req v0.8 revamped the internals**. If you wrote custom steps or plugins against older versions, response and error steps are deprecated in favor of *step wrappers*. End users are mostly unaffected, but plugin authors need to read the migration notes in the `Req.Request` documentation. The lesson: Req is stable in *behavior*, but its internals are still evolving as the maintainer iterates toward 1.0.

## Tesla — Middleware, Adapters, and Explicit Pipelines

Tesla (2,076 stars, MIT, last push 2026-08-19) is explicitly modeled on Ruby's Faraday: an HTTP client built around a composable middleware stack running over a swappable adapter. You declare the pipeline when you build a client:

```elixir
iex> client = Tesla.client([
...>  {Tesla.Middleware.BaseUrl, "https://httpbin.org/"},
...>  Tesla.Middleware.JSON,
...> ])

iex> Tesla.get!(client, "/json").body
# => %{"slideshow" => ...}
```

The middleware catalog in the README covers the standard needs — `BaseUrl`, `Headers`, `Query`, `FollowRedirects`, `Logger`, `Retry`, `Timeout`, `Fuse` (circuit breaker integration), `FormUrlencoded`, `JSON`, `Compression`, and auth middlewares (`BasicAuth`, `BearerAuth`, `DigestAuth`). Adapters are a first-class concept: `:httpc` (default), Hackney, Ibrowse, Gun, Mint, and Finch. The default deserves attention — the README explicitly warns that the built-in `:httpc` adapter is *not recommended for production* because it does not validate SSL certificates, and recommends Mint, Finch, or Hackney instead:

```elixir
# config/config.exs
config :tesla, adapter: Tesla.Adapter.Mint
```

Tesla's strength is reuse: define your middleware stack once per API and every request through that client inherits it. Its weakness is that nothing is automatic — JSON handling, retries, and redirects are all middleware you must remember to add, and the default adapter is a footgun. Teams that adopt Tesla tend to standardize on a project-specific client module that encodes the "right" stack, so the footgun is hit once and documented.

## HTTPoison — The Simple Workhorse, Now With a Hard OTP Requirement

HTTPoison (2,290 stars, MIT, last push 2026-07-05) is the oldest of the three: a thin, friendly wrapper around hackney that defined Elixir's early HTTP idioms. The API is minimal — `HTTPoison.get!`, `HTTPoison.post`, and friends return or raise on `HTTPoison.Response`/`HTTPoison.Error` structs:

```elixir
iex> HTTPoison.get! "https://postman-echo.com/get"
%HTTPoison.Response{
  status_code: 200,
  body: "{...}",
  headers: [ ... ]
}
```

The idiomatic pattern-match style the README demonstrates is still one of the cleanest ways to handle responses in Elixir:

```elixir
case HTTPoison.get(url) do
  {:ok, %HTTPoison.Response{status_code: 200, body: body}} ->
    IO.puts body
  {:ok, %HTTPoison.Response{status_code: 404}} ->
    IO.puts "Not found :("
  {:error, %HTTPoison.Error{reason: reason}} ->
    IO.inspect reason
end
```

For building API clients, `HTTPoison.Base` provides a module-macro pattern for wrapping endpoints, processing URLs, and decoding bodies — the README shows a complete GitHub API client built this way. What HTTPoison does *not* do: no automatic JSON handling, no retries, no redirect following, no streaming helpers, no test utilities. And the ecosystem tax is now visible: **HTTPoison 3.x depends on hackney 4.0, which requires Erlang/OTP 27 or later and therefore Elixir 1.17 or later**. If your deployment runs an older OTP release, you are pinned to the 2.x line. That requirement, plus the absence of conveniences, is why most greenfield projects pick Req — but for a stable, dependency-light, predictable client, HTTPoison still works exactly as documented.

## Common Pitfalls and Migration Gotchas

1. **Tesla's default `:httpc` adapter does not validate SSL certificates.** The README is explicit about this. If you ship a Tesla client without configuring an adapter, production HTTPS calls can silently accept invalid certificates. Always set `config :tesla, adapter: Tesla.Adapter.Mint` (or Finch/Hackney) in `config/config.exs`.
2. **Req v0.8 custom-step breakage.** If you built plugins or custom steps on Req < 0.8, response/error steps are deprecated in favor of step wrappers. Audit `Req.Request` docs before upgrading; user-facing request code rarely changes, but plugin code does.
3. **HTTPoison's OTP 27 requirement.** Upgrading HTTPoison to 3.x on an OTP 26 deployment will fail at compile or runtime. Check your OTP version first (`elixir -e 'IO.puts System.otp_release()'`), and pin `{:httpoison, "~> 2.2"}` if you must stay on older OTP.
4. **`get!` vs `get` exceptions.** The bang variants raise on errors, the non-bang variants return `{:error, %HTTPoison.Error{}}` tuples. Mixing them in a codebase causes silent crash handling confusion — pick one convention per codebase, and note that Req's `get!` raises only on transport errors, returning error-tagged responses you inspect with `response.status`.
5. **Forgetting JSON middleware in Tesla.** A Tesla client without `Tesla.Middleware.JSON` will not encode maps or decode JSON bodies — you get raw strings and must handle `Poison`/`Jason` yourself. The failure shows up as confusing `Protocol.UndefinedError` in the field.
6. **Req.Test only intercepts requests routed through the test.** `Req.Test` works by plugging into the request pipeline with a mock transport — requests made by code that constructs its own `Req` instances outside the tested process are not intercepted. Stub via `Req.Test.stub(:any, ...)` and pass the same `Req` struct through your application.
7. **Connection pools and startup.** Finch (Req's default adapter) runs as a supervised process. If you call Req before your application starts Finch (e.g., in config or an early GenServer init), you get pool errors. Start the app or use `Req.new(finch: ...)` with a manually started pool.
8. **Streaming without draining.** `Req.stream/4` keeps the connection open until the stream is consumed or closed. Abandoning a stream leaks connections in the pool; always consume or close it.

Elixir's JSON layer interacts with every client here — our [Elixir JSON libraries comparison](../2026-07-25-elixir-json-libraries-jason-poison-jsex-jsonrs/) covers Jason, which Tesla and Req both use under the hood. If you are choosing the whole web stack, the [Phoenix vs Plug vs Ash comparison](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) shows where the HTTP client fits in an application, and our [TypeScript HTTP clients guide](../2026-07-28-typescript-http-client-libraries-axios-got-undici-ky-node-fetch-comparison/) and [Ruby HTTP clients comparison](../2026-08-15-ruby-http-clients-faraday-httparty-http-rb-comparison/) show how other ecosystems solve the same three-way choice — notably that Ruby's Faraday is the direct inspiration for Tesla.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Elixir HTTP Clients in 2026: Tesla vs Req vs HTTPoison — Which One Should You Actually Use?",
  "description": "Compare Tesla, Req, and HTTPoison with live GitHub stats and official code examples. Learn which Elixir HTTP client fits your project: middleware pipelines, batteries-included steps, or hackney-based simplicity.",
  "datePublished": "2026-08-21",
  "dateModified": "2026-08-21",
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

### Which Elixir HTTP client should I use in 2026?

For new projects, Req — it is batteries-included (JSON encoding/decoding, redirects, retries, auth, streaming), actively maintained by an Elixir core team member, and the default choice in modern Phoenix workflows. Choose Tesla for middleware-heavy multi-client setups, and HTTPoison for legacy hackney-based code.

### What is the difference between Req and Tesla?

Req is a step-based client with batteries included — most features work out of the box and are customizable through steps. Tesla is a middleware pipeline modeled on Ruby's Faraday: you explicitly compose middleware (JSON, retries, auth) and pick an adapter, which gives more control at the cost of more configuration.

### Does HTTPoison still require Erlang/OTP 27?

HTTPoison 3.x depends on hackney 4.0, which requires Erlang/OTP 27 or later (and Elixir 1.17 or later). If your deployment uses an older OTP release, you must stay on the 2.x line.

### Is Tesla's default adapter safe for production?

No. The default `:httpc` adapter does not validate SSL certificates, and the README recommends Mint, Finch, or Hackney for production use. Always configure an explicit adapter in `config/config.exs`.

### How do I test HTTP calls in Elixir?

Req ships `Req.Test`, which mounts a Plug router and lets you stub responses in-process. Tesla provides a mock adapter, and HTTPoison relies on pattern-matching responses or injecting a mocked module behind a behaviour (often with Mox — see our Elixir testing guide).

### Does Req support streaming?

Yes. `Req.stream/4` streams response bodies with a callback, and you can stream request bodies by passing an enumerable or function as `body`. It also supports `into: collectable` and `into: :self` for accumulation.

### What happened in Req v0.8?

Req v0.8 revamped the internals: response and error steps are deprecated in favor of step wrappers. End-user request code is mostly unaffected, but developers who wrote custom steps or plugins need to migrate following the `Req.Request` documentation.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
