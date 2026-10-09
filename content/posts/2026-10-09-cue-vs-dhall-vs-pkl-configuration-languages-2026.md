---
title: "CUE vs Dhall vs Pkl in 2026: Which Configuration Language Should You Actually Use?"
date: "2026-10-09"
tags: ["configuration-management", "developer-tools", "devops", "infrastructure-as-code", "yaml"]
draft: false
cover: "/img/screenshots/pkl-logo.jpg"
---

YAML does not have variables, and yet every large deployment ends up reinventing them. You copy a block of config, change three values, forget one, and a staging environment silently pointed at the production database for a week. Anchors and aliases bandage the problem until the file becomes unreadable, and then someone writes a Python script to generate the YAML — at which point you have a configuration language with none of the type safety, none of the tooling, and none of the documentation.

That is the gap **CUE**, **Dhall** and **Pkl** were built to fill. All three let you write configuration as code that is validated *before* it reaches production, and all three compile down to the YAML and JSON your existing tools already consume. They take radically different approaches to that goal, and the differences matter more than the feature checklists suggest.

## TL;DR — The Quick Verdict

- **Choose CUE** if your main problem is **validating and merging configuration** — especially Kubernetes manifests, JSON and YAML you do not fully control. It is a unification language that merges data and constraints, and it has the strongest infrastructure-as-code ecosystem of the three.
- **Choose Dhall** if you want a **provably safe configuration language** — total, non-Turing-complete, with cryptographic integrity checks on every import. Nothing in a Dhall file can hang, loop forever, or run arbitrary code.
- **Choose Pkl** if you want a **full programming language with gradual typing and excellent tooling** — Apple's entry is the most conventional to learn, the fastest-moving, and the one with the widest output format support.

Short version: **CUE to validate and merge, Dhall for safety and determinism, Pkl for developer experience.**

## Quick Comparison: CUE vs Dhall vs Pkl

| Dimension | CUE | Dhall | Pkl |
|---|---|---|---|
| **Model** | Unification of types and values | Total functional language | Configuration-as-code with gradual typing |
| **Typing** | Static, structural | Static, full type inference | Gradual (types optional, checked when present) |
| **Turing complete?** | No (deliberately constrained) | No — guaranteed to terminate | Yes (general-purpose language) |
| **Primary outputs** | JSON, YAML, native CUE | JSON, YAML, TOML, Bash, text | JSON, YAML, XML, plist, properties |
| **Integrations** | Go API, Kubernetes tooling, protobuf/OpenAPI | CLI converters, JSON/YAML `dhall-to-*` tools | Official bindings for JVM, Swift, Go, Python |
| **Import security** | Module system | Every remote import pinned by semantic hash | Standard module imports |
| **Language base** | Purpose-built | Purpose-built (Haskell implementation) | JVM/Kotlin-inspired |
| **License** | Apache-2.0 | BSD-3-Clause | Apache-2.0 |
| **Latest release** | v0.17.1 | 1.42.2 | 0.32.1 |
| **GitHub stars / last push** | 6,280★, 2026‑10‑08 | 4,487★, 2026‑10‑06 | 11,542★, 2026‑10‑08 |
| **Best for** | Config validation, platform schemas | Security-sensitive pipelines, deterministic builds | Application config, broad format support |

All three projects pushed code within the last three days of this writing, and all three are permissively licensed. **Pkl leads on stars with 11,542**, but it also had Apple's launch momentum behind it — star count is a poor proxy for maturity in this space, because CUE has been battle-tested in far more production Kubernetes stacks.

## Decision Matrix — Pick in Ten Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| You must validate third-party YAML/JSON you did not write | **CUE** | Unification lets you layer constraints over existing data without owning it |
| Platform teams defining a schema every service must satisfy | **CUE** | Structural types + `cue vet` in CI catch drift before apply |
| Air-gapped or security-sensitive environment | **Dhall** | Remote imports are hashed; nothing can execute arbitrary code |
| You want config that cannot loop forever or hang a pipeline | **Dhall** | Non-Turing-complete by construction |
| Application developers who already know Java/Kotlin/Swift | **Pkl** | Familiar object-oriented syntax, rich IDE support, gradual typing |
| You need to emit XML, plist or properties files | **Pkl** | The broadest built-in output format set |
| You generate configuration from Go code | **CUE** | First-class Go API and the deepest K8s tooling integration |
| You want the largest community and fastest-moving project | **Pkl** | 11.5K stars and near-daily commits |

## CUE — Validation Through Unification

CUE's central idea is that **types and values are the same thing**. A field is not "typed as an integer" — it *is* an integer constraint, and you refine it by unifying further constraints. Where YAML forces you to choose between a schema and a document, CUE lets you write both at once and merge them.

A minimal example that validates a port range and supplies a default:

```cue
#Server: {
	host: string
	port: int & >=1024 & <=65535
	tls:  bool | *false
}

server: #Server & {
	host: "api.example.com"
	port: 8443
}
```

Run `cue vet` in CI and invalid data fails before it is ever rendered. Run `cue export` and you get JSON. Run `cue export -e server -o yaml` and you get YAML for the tool that consumes it.

Installation is a single Go command, and there is an official container image for pipeline use:

```bash
# Install from source (requires Go 1.26+)
go install cuelang.org/go/cmd/cue@latest

# Or use the official Docker image
docker run --rm -v "$PWD":/work -w /work cuelang/cue:latest \
  cue vet ./...
```

The Kubernetes ecosystem is where CUE earns its keep. Because it can import and validate existing YAML without rewriting it, teams adopt it incrementally — first as a validator bolted onto an existing Helm or Kustomize workflow, then progressively as the source of truth for platform schemas.

## Dhall — Safety by Construction

Dhall attacks the problem from the opposite direction: instead of maximizing expressiveness, it removes the ability to misbehave. Dhall is **total** — every program terminates — and it is **non-Turing-complete by design**, so there is no way to write an infinite loop or a recursive explosion inside a config file.

The feature that wins security reviews is import integrity. A remote Dhall import is pinned to the **semantic hash of its normal form**, so a change to the imported expression breaks the build rather than silently altering your deployment:

```bash
# Pin every remote import to a cryptographic hash
dhall freeze --inplace ./config.dhall
```

A real configuration looks like ordinary records, with the type system doing the work:

```dhall
let Server = { host : Text, port : Natural, tls : Bool }

let server : Server =
      { host = "api.example.com", port = 8443, tls = True }

in  server
```

Convert it to whatever the consuming tool wants:

```bash
# Render to JSON for a service, or YAML for a manifest
dhall-to-json --file config.dhall > config.json
dhall-to-yaml --file config.dhall > config.yaml
```

Static binaries make installation trivial — the release page ships `dhall-1.42.2-x86_64-linux.tar.bz2` alongside macOS and Windows builds, and a Haskell toolchain or package manager gets you the whole utility set (`dhall-to-json`, `dhall-to-yaml`, `dhall fmt`, `dhall lint`, and an editor server).

The honest trade-off: Dhall's syntax and error messages have a reputation for being unfriendly, and the ecosystem is smaller. Its type inference is genuinely powerful, but developers used to YAML spend their first day fighting `let` bindings and explicit type annotations.

![Dhall — a programmable configuration language that you can think of as a typed, functional YAML](/img/screenshots/dhall-logo.jpg "Dhall guarantees termination and pins remote imports by hash")

## Pkl — Configuration as a First-Class Language

Pkl, released by Apple, takes the most familiar approach: it is a real programming language with classes, modules, functions and gradual typing, designed specifically for producing configuration. If your team writes Java, Kotlin or Swift, Pkl's syntax will feel immediately readable.

```pkl
module ServerConfig

class Server {
  host: String
  port: UInt16
  tls: Boolean = false
}

server: Server = new {
  host = "api.example.com"
  port = 8443
  tls = true
}
```

Evaluate it to any supported format:

```bash
pkl eval -f json config.pkl
pkl eval -f yaml config.pkl
```

Installation is straightforward across platforms:

```bash
# macOS / Linux via Homebrew
brew install pkl

# Or pin a version with mise
mise use -g pkl@0.32.1

# Or grab the release binary for your architecture
# https://github.com/apple/pkl/releases/latest  (pkl-linux-aarch64, pkl-linux-amd64, ...)
```

Pkl's real differentiator is the tooling layer: a language server for editor completion and diagnostics, official embedder libraries for the JVM, Swift, Go and Python so applications can evaluate Pkl configs at runtime, and built-in renderers for JSON, YAML, XML, plist and properties. The cost of that expressiveness is that Pkl *is* a general-purpose language — the termination guarantee Dhall offers simply does not exist here, so review discipline matters.

If you are already templating manifests rather than managing configuration as data, our [Kubernetes resource templates comparison](../2026-05-16-kubernetes-resource-templates-cdk8s-jsonnet-kcl/) puts cdk8s, Jsonnet and KCL side by side — Jsonnet in particular is a direct alternative to all three tools here at the "generate YAML" layer. For day-to-day YAML manipulation, the [yq vs dasel guide](../2026-06-17-self-hosted-yaml-data-processors-yq-vs-dasel/) covers the tooling you will use alongside these languages, and teams running Helm should read the [Helm management workflow comparison](../2026-05-06-self-hosted-helm-management-helmfile-flux-argocd-guide/) before deciding where a config language fits.

## Common Pitfalls

- **Adopting a config language for its own sake.** If you have four small YAML files that rarely change, none of these tools earns its complexity. The payoff appears when configuration is duplicated across environments or validated by machines.
- **Expecting Pkl-style programming in Dhall.** Dhall is deliberately not a general-purpose language. Teams that fight the type system instead of designing with it burn weeks.
- **Forgetting to pin imports in Dhall.** `dhall freeze` converts loose remote imports into hash-pinned ones. Skip it and you have reintroduced the supply-chain risk you adopted Dhall to remove.
- **Treating CUE as "just a YAML validator".** Its unification model can express schema-plus-data in one pass; teams that use it only for linting leave most of the value on the table.
- **Assuming full Turing completeness is a feature.** For deployment configuration it usually is not. Loops around production endpoint lists are how outages start.
- **Ignoring the emission path.** A config language is only as good as its output. Check that your target consumes one of the supported formats before migrating anything.

## FAQ

### Which is best for Kubernetes: CUE, Dhall or Pkl?

CUE, for most teams. It has the deepest Kubernetes integration, can validate existing YAML without rewriting it, and is used by infrastructure projects like Timoni. Dhall works well for generating manifests in a deterministic pipeline, and Pkl can emit any manifest shape, but neither matches CUE's K8s ecosystem depth.

### Is Dhall actually safer than the alternatives?

Yes, under specific definitions of safe. Dhall is total — every program terminates — and every remote import is pinned by a semantic hash, so imports cannot silently change. CUE is also non-Turing-complete, while Pkl is a general-purpose language with no termination guarantee.

### Can I use these tools with my existing YAML files?

Yes for CUE and Dhall, largely yes for Pkl. CUE can read, validate and merge existing YAML and JSON in place, which makes incremental adoption realistic. Dhall and Pkl generate YAML rather than consuming it, so the migration is typically a rewrite of the affected files.

### What are the real output formats?

CUE exports JSON, YAML and native CUE. Dhall ships `dhall-to-json`, `dhall-to-yaml`, `dhall-to-toml`, `dhall-to-bash` and generic text renderers. Pkl supports JSON, YAML, XML, plist and Java properties natively — the widest built-in set of the three.

### Is Pkl production-ready despite being the newest?

By adoption signals, yes: 11,542 GitHub stars, commits within days, official language bindings, and a released language server. The caveat is that Pkl is Turing complete, so unlike Dhall it offers no termination guarantee — treat configuration review with the same seriousness as application code.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CUE vs Dhall vs Pkl in 2026: Which Configuration Language Should You Actually Use?",
  "description": "A 2026 comparison of CUE, Dhall and Pkl configuration languages: unification vs totality vs gradual typing, output formats, Kubernetes fit, licenses and pitfalls.",
  "datePublished": "2026-10-09",
  "dateModified": "2026-10-09",
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
