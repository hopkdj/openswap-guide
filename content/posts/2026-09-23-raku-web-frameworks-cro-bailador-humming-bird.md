---
title: "Raku Web Frameworks in 2026: Cro vs Bailador vs Humming-Bird (Honest Verdict)"
date: "2026-09-23"
tags: ["raku", "perl", "web-frameworks", "self-hosted", "api", "language-ecosystems"]
categories: ["self-hosted"]
cover: "/img/screenshots/raku-camelia.jpg"
description: "Cro, Bailador and Humming-Bird compared for building HTTP services in Raku in 2026: real install commands, router code from the official repos, maintenance status, deployment with the official container image, and the risks nobody writes about."
draft: false
---

Raku — the language formerly known as Perl 6 — has an actively maintained toolchain (Rakudo at 1,900 stars, MoarVM at 779, both committing within the last day) and a genuinely small web framework ecosystem. That combination is exactly why this comparison is useful: if you are considering Raku for a service, there are only three realistic answers, and two of them are not what you would pick for production in 2026.

Here is the honest version, with upstream commit dates instead of marketing copy.

## TL;DR — Quick Verdict

- **Choose Cro** if you are building anything production-facing: it is the only one with an HTTP/2-capable server stack, WebSocket support, and a service-stubbing tool that generates a working project skeleton.
- **Choose Humming-Bird** if you want a small, modern, actively developed router for an internal API and you like explicit handler signatures.
- **Choose Bailador** only for reading legacy code or learning Raku: the router is pleasant, but the last upstream commit was in 2019.

Blunt summary: **Raku's web story is Cro plus a challenger.** Everything else is history or a weekend project.

## Comparison at a Glance (September 2026)

| Dimension | Cro | Humming-Bird | Bailador |
|---|---|---|---|
| GitHub stars | 94 (core) / 49 (cro-http) | 48 | 178 |
| Last upstream push | 2026-06-02 (cro-http) | 2026-07-11 | 2019-08-18 |
| License | Artistic-2.0 | MIT | MIT |
| Install | `zef install --/test cro` | `zef install Humming-Bird` | `zef install Bailador` |
| Router style | `route { get -> ... }` (supply-based) | `get('/', -> $req, $res { ... })` | `get '/' => sub { ... }` |
| Async model | Raku supplies/streams, composable pipelines | Blocking handlers, backend pluggable | Blocking handlers |
| HTTP/2 | Yes (`cro-http`) | No | No |
| WebSocket | Yes (`cro-websocket`) | No (third-party) | No |
| Server backends | `Cro::HTTP::Server` | `HTTP::Server`, pluggable backend | `HTTP::Server` |
| Project scaffolding | `cro stub` templates | Manual | Manual |
| Deployment maturity | Containers, env-driven ports/TLS | Manual | Manual |
| Maintenance risk | Low-moderate | Low | High (unmaintained) |
| Best fit | Distributed services, APIs, internal platforms | Small APIs, internal tooling | Legacy maintenance |

Read the star counts in context: this is a language ecosystem with roughly two thousand interested developers in total, so 94 stars on Cro is not a red flag, and 48 on Humming-Bird in a repo created recently is normal. The maintenance column is what should drive your decision.

## Decision Matrix: Use Case → Tool → Reason

| Use case | Tool | Why |
|---|---|---|
| Production HTTP API with WebSockets | **Cro** | Only option with maintained HTTP/2 and WebSocket libraries |
| Distributed system with multiple cooperating services | **Cro** | Designed for service composition and links between services |
| Internal admin or metrics endpoint | **Humming-Bird** | Tiny dependency surface, simple handler model |
| Learning Raku through a web project | **Humming-Bird** or **Bailador** | Small codebases, readable routers |
| Reviving an old Perl 6 codebase | **Bailador** | Same router shape, no rewrite needed |
| Static-asset or file-upload service | **Cro** | Mature body/streaming handling in `cro-http` |
| Long-lived platform you will still run in 2031 | **Cro** | Upstream work continues; plan to vendor it if needed |
| Anything with hard latency budgets | none of these | Pick a Raku-adjacent option only if you have measured it yourself |

## Installing Raku and the Package Manager

All three frameworks install through `zef`, Raku's module manager. Start with Rakudo Star (the bundled distribution) or the official container image, which is far less painful than bootstrapping a compiler:

```bash
# Option A: official Rakudo Star container image (Docker Hub "library/rakudo-star")
docker run --rm -it -v "$(pwd)":/app -w /app rakudo-star:latest raku -v

# Option B: local install via the Rakudo Star distribution, then zef
zef update
zef search cro
```

Once `zef` is available, installs are one-liners — note Cro's `--/test` flag, which skips its (large) test suite during installation:

```bash
zef install --/test cro          # Cro toolchain
zef install Humming-Bird         # stable release
zef install Bailador             # legacy framework
```

A container recipe that keeps the runtime reproducible:

```yaml
# compose.yaml — Raku service with pinned image
services:
  raku-api:
    image: rakudo-star:2026.07
    working_dir: /app
    volumes:
      - ./app:/app
    ports:
      - "3000:3000"
    command: raku -Ilib app.raku
```

## Cro — The Only Production-Grade Option

Cro is not a single framework but a set of libraries: `cro-http` for HTTP/1.1 and HTTP/2, `cro-websocket` for sockets, plus templating and service-discovery pieces. Routing is supply-based and reads like a declarative pipeline:

```raku
use Cro::HTTP::Router;
use Cro::HTTP::Server;

my $application = route {
    get -> 'greet', $name {
        content 'text/plain', "Hello, $name!";
    }
    get -> 'health' {
        content 'application/json', '{"status":"ok"}';
    }
}

my Cro::Service $http = Cro::HTTP::Server.new(
    http        => <1.1>,
    host        => '0.0.0.0',
    port        => 3000,
    application => $application,
);

$http.start;
react whenever signal(SIGINT) { $http.stop; exit; }
```

The reason Cro wins on maintenance is its tooling. `cro stub` generates a complete, working service skeleton from a template, including environment-driven port and certificate configuration:

```bash
# General form (from the Cro tool documentation)
cro stub <service-type> <service-id> <path> ['links-and-options']

# HTTP service with WebSocket support, no self-signed TLS
cro stub http foo services/foo ':!secure :websocket'

# Service that links to another service in the same system
cro stub http flashcard-backend backend/flashcards
```

That last form is Cro's real differentiator: the stub can wire a service to another service by link name, which fits the microservice topology many teams actually deploy. The generated project is ordinary Raku source, so you can review it like any other code.

**Where Cro hurts:** the meta-repository (`croservices/cro`) shows a 2025-01 commit date while `cro-http` was updated in June 2026 — documentation lags code, and you will end up reading source for edge cases. The dependency tree also pulls a lot of Raku modules, so audit it before pinning in a regulated environment.

## Humming-Bird — Small, Modern, Actively Developed

Humming-Bird takes the opposite approach: a compact router with explicit handler signatures and a request/response object you mutate. The official simple example is four lines of logic:

```raku
use v6.d;
use Humming-Bird::Core;

get('/', -> $request, $response {
    $response.html('<h1>Hello World</h1>');
});

listen(8080);
```

A JSON API looks like this (taken from the project's README, trimmed to the routing essentials):

```raku
use v6.d;
use Humming-Bird::Core;
use JSON::Fast;   # bundled dependency of Humming-Bird

my %users = Map.new('bob', %('name', 'bob'), 'joe', %('name', 'joe'));

get('/users/:user', -> $request, $response {
    my $user = $request.param('user');
    if %users{$user}:exists {
        $response.json(to-json %users{$user});
    } else {
        $response.status(404).html("Sorry, $user does not exist.");
    }
});

post('/users', -> $request, $response {
    my %user = $request.content;   # decoded into a Map when possible
    %users{%user<name>} = %user;
    $response.status(201);
});

listen(8080);
```

Notable design choices worth knowing before you commit: `$request.content` decodes bodies into Raku data structures for you, routes persist across repeated `use` statements, and the backend is pluggable — the project benchmarks its `HTTPServer` backend against Ruby's Sinatra. The obvious gaps are also real: no built-in WebSocket or HTTP/2 support, no scaffolding tool, and a much smaller install base.

**Where Humming-Bird hurts:** ecosystem. When you need rate limiting, sessions, or server-sent events, you will be writing them. That is fine for an internal API with a bounded feature list and painful for a public product.

## Bailador — Read It, Do Not Start With It

Bailador was the approachable Perl 6 web framework of its era, and its route syntax is still the friendliest thing in this comparison:

```perl6
# Bailador routing style (from the project README)
get '/' => sub {
    'Hello, world!';
};
```

Installing it still works exactly as documented:

```bash
zef update
zef install Bailador
```

But the repository's last push was **2019-08-18**. No HTTP/2, no WebSockets, no security release process you can point an auditor at. If you inherit a Bailador application, treat the framework as a vendored dependency you own: pin it, wrap the routing layer, and keep the door open to migration. If you are starting fresh, picking Bailador in 2026 is choosing a framework with no upstream maintenance window.

## Deployment and Operations

Because all three are Raku libraries, deployment is the same shape: a Raku runtime, your source tree, and a process supervisor. In practice you want a container image and a reverse proxy in front for TLS termination and request logging:

- Keep the runtime pinned — `rakudo-star:2026.07`, not `latest` — because Raku module resolution can break across compiler releases.
- Terminate TLS at the proxy, not in the application, so certificate rotation does not require a redeploy.
- Run the service under a supervisor that restarts on crash and sends a signal the app handles; Cro's `react whenever signal(SIGINT)` pattern is the idiomatic graceful shutdown.
- Health-check an endpoint that touches your datastore, not just the router.

If your stack spans multiple languages, the same operational questions were covered for [Perl's Mojolicious/Dancer2/Catalyst trio](../2026-08-01-perl-web-frameworks-mojolicious-dancer2-catalyst-comparison/), for [Gleam HTTP servers](../2026-09-12-gleam-http-servers-mist-wisp-cowboy-comparison/), and for [OCaml's Dream/Opium/Ocsigen stack](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/). The pattern repeats: mature ecosystem beats elegant language every time you have to page someone at 3 a.m.

## Pitfalls and Migration Notes

- **Module breakage across Rakudo releases.** Pin the compiler version in your image and re-run your test suite before upgrading; Raku's module ecosystem does not have the compatibility guarantees of CPAN's Perl 5 lineage.
- **`zef install` compiles from source.** First installs are slow and need build tooling in the image. Multi-stage builds keep the final image small.
- **Cro's documentation lags its code.** Read the `cro-http` source when the docs are thin, and vendor the modules you depend on if you need reproducible builds.
- **Do not assume concurrency for free.** Cro's supply-based model composes asynchronously, but a blocking handler inside it stalls the pipeline. Humming-Bird's blocking model is simpler *and* easier to get wrong under load.
- **Benchmark before promising numbers.** Raku performance is respectable for I/O-bound services and unremarkable for CPU-bound work; the JIT needs warm-up, so measure a steady state.
- **Hiring and knowledge transfer are real costs.** Choosing Raku for a service means a very small talent pool. Budget extra onboarding time, or accept that your team keeps the system alive.

## FAQ

**Is Raku the same as Perl 6?**
Yes. Perl 6 was renamed to Raku in 2019, and the implementation is called Rakudo, running on the MoarVM virtual machine. Perl 5 and Raku are separate languages with separate module ecosystems.

**Which Raku web framework should a beginner learn?**
Start with Humming-Bird to learn the language through small HTTP handlers, then move to Cro when you need WebSockets, HTTP/2, or multi-service wiring. Skip Bailador except for reading older code.

**Can I deploy Cro or Humming-Bird in Docker?**
Yes. The official `rakudo-star` image on Docker Hub gives you a working runtime and `zef`, so a standard multi-stage build produces a deployable image. Pin a dated tag rather than `latest`.

**How mature is Cro really, given only ~94 stars?**
Stars measure community interest, not engineering quality. Cro has maintained HTTP/2 and WebSocket libraries, a scaffolding tool, and active work in `cro-http` as of mid-2026. The honest caveat is documentation lag and a small contributor base, so plan to read source and possibly vendor modules.

**Should I choose Raku for a new public-facing service in 2026?**
Only if your team already knows Raku or has a specific reason to use it. For most teams, the operational risk of a small framework ecosystem outweighs the language's genuine strengths in expressiveness and concurrency composition.

**What is the biggest operational risk with these frameworks?**
Dependency resolution across compiler versions. A module that installed cleanly on one Rakudo release can fail to build on the next, so pin both the runtime tag and your module versions, and treat upgrades as a planned change with a full regression run.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Raku Web Frameworks in 2026: Cro vs Bailador vs Humming-Bird (Honest Verdict)",
  "description": "Cro, Bailador and Humming-Bird compared for Raku HTTP services in 2026: real install commands, router code from official repos, maintenance status, container deployment and operational risks.",
  "datePublished": "2026-09-23",
  "dateModified": "2026-09-23",
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
