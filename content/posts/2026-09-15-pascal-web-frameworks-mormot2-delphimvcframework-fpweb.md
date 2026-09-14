---
title: "Open-Source Pascal Web Frameworks in 2026: mORMot 2 vs DelphiMVCFramework vs fpWeb"
date: "2026-09-15"
tags: ["self-hosted", "web-frameworks", "object-pascal", "open-source"]
draft: false
cover: "/img/screenshots/dmvc-logo.jpg"
---

Object Pascal quietly runs a staggering amount of critical infrastructure: check-in terminals, laboratory instruments, warehouse scanners, and back-office systems that have been compiling with the same toolchain for fifteen years. The catch is that the server side of those systems is usually locked behind a commercial licence — until you look at what the open-source side has been doing.

Three options dominate in 2026: **mORMot 2**, **DelphiMVCFramework**, and **fcl-web (fpWeb)**, which ships with Free Pascal itself. Two of them shipped commits within a day of this article. Here is the honest comparison, with live repository data and the actual code each framework expects you to write.

## TL;DR — Quick Verdict

**Pick mORMot 2 if you want the most capability per line of code**: an optimised RTL, client/server ORM, SOA/MVC layers, JSON kernel, and nightly regression tests across Windows, Linux, macOS, and BSD — all under one roof. **Pick DelphiMVCFramework if you are building a REST or JSON-RPC API and your team lives in the Delphi IDE**: it gives you Richardson Maturity Model Level 3 REST, JSON-RPC 2.0 with automatic object remotisation, OpenAPI/Swagger generation, and TLS 1.3 negotiation out of the box. **Pick fpWeb only when "no dependencies at all" is the requirement** — it is part of Free Pascal's own runtime library, so `fpc` is the entire installation.

## The Comparison Table (Live GitHub Data)

Star counts and last-push dates come from the GitHub API on 2026-09-15.

| Framework | Repository | Stars | Last Push | Language Targets | Killer Feature |
|---|---|---|---|---|---|
| **mORMot 2** | `synopse/mORMot2` | 713 | 2026-09-14 | Delphi 7 → 12.3, FPC 3.2/trunk | Full ORM + SOA + MVC stack with an optimised RTL |
| **DelphiMVCFramework** | `danieleteti/delphimvcframework` | 1,404 | 2026-09-14 | Object Pascal (Delphi IDE workflow) | REST level 3 + JSON-RPC 2.0 + OpenAPI generation |
| **mORMot 1.18** | `synopse/mORMot` | 825 | 2026-06-05 | Legacy Delphi/FPC | Maintenance-only; migrate to mORMot 2 |
| **fcl-web / fpWeb** | Ships inside Free Pascal (`packages/fcl-web`) | — | tracks FPC releases | FPC (all supported platforms) | Zero extra dependencies; `TFPWebModule` in the compiler's own library |

Two data points matter more than the star counts: **DelphiMVCFramework and mORMot 2 both pushed on 2026-09-14**, and mORMot's README states that regression tests are *"built and run nightly from FPC fixes-3_2 to most versions of Windows 7-11, and several Linux and MacOS distributions on i386/x86_64/arm32/aarch64."* That is a wider CI matrix than most modern Node.js projects bother with.

## Decision Matrix: Pick in 10 Seconds

| Your Use Case | Recommended Framework | Why |
|---|---|---|
| REST API with generated OpenAPI docs on day one | **DelphiMVCFramework** | Swagger/OpenAPI generation is a documented feature, not a plugin |
| One stack for ORM + services + HTML views | **mORMot 2** | ORM, SOA, and MVC ship together with the RTL |
| Linux server binary, cross-compiled from Pascal | **mORMot 2 with FPC** | Explicit cross-platform server target list and nightly Linux testing |
| Existing Delphi team, minimal retraining | **DelphiMVCFramework** | IDE-first install plus a project template in the IDE menu |
| No dependency downloads allowed | **fcl-web (fpWeb)** | Distributed with the Free Pascal compiler |
| Maintaining a 2015-era mORMot 1.x codebase | **Plan a mORMot 2 migration** | Version 1.18 is explicitly in maintenance-only mode |

## mORMot 2 — The Full Stack in One Repository

mORMot 2 is best understood as a complete Object Pascal platform rather than a web framework. The README describes it as an optimised RTL with a client-server ORM/SOA/MVC framework, and the repository layout backs that up:

- `src/` — the library itself, including `src/rest/mormot.rest.http.server.pas` for the HTTP server layer
- `ex/` — runnable samples, including `ex/http-server-raw` and `ex/http-server-files`, each shipping both a `.dpr` (Delphi) and `.lpi` (Lazarus) project
- `static/` — prebuilt `.o`/`.obj` files needed for static linking on FPC and Delphi
- `packages/lazarus/mormot2.lpk` — the Lazarus package that compiles the whole library

Installing it in a Lazarus environment is therefore a two-step operation with no package manager involved:

```bash
git clone https://github.com/synopse/mORMot2.git
cd mORMot2
# Open and compile the Lazarus package
lazbuild packages/lazarus/mormot2.lpk
# Optional: run the regression suite on your own machine
# open test/mormot2tests.dpr in Lazarus and run it
```

The README's own instructions say the same thing in IDE terms: open and compile the `.lpk`, then build `test/mormot2tests.dpr` to run the regression tests locally. For a server project, copy `ex/http-server-raw` and adapt it — the samples are the documentation.

Two version constraints are worth memorising before you start:

1. **Use FPC 3.2.3 or the `fixes-3_2` branch.** The README flags a specific regression in FPC 3.2.2 involving variant late binding, and points at the upstream issue.
2. **Delphi's general units target Windows only.** The README is explicit that on Delphi only the Windows target is available for the general units, that cross-platform client units work everywhere, and that *"FPC is a much better and consistent cross-platform compiler."* If your deployment target is a Linux VPS or a BSD appliance, Free Pascal is the intended path — not a workaround.

Deployment on Linux is an ordinary compiled binary, which is exactly what makes this stack pleasant to operate:

```ini
# /etc/systemd/system/pascal-api.service
[Unit]
Description=Object Pascal REST API (mORMot 2)
After=network.target

[Service]
User=pascalapi
WorkingDirectory=/opt/pascal-api
ExecStart=/opt/pascal-api/api-server --port 8080
Restart=always
RestartSec=2
# no interpreter, no runtime dependencies beyond libc

[Install]
WantedBy=multi-user.target
```

Put Nginx or Caddy in front for TLS and static assets, bind the API to loopback, and ship the binary as a single file. There is no interpreter to patch, no virtual environment to rebuild, and no lockfile to resolve at deploy time.

## DelphiMVCFramework — REST and JSON-RPC for Delphi Teams

DelphiMVCFramework (DMVC) is the pragmatic choice when the team already has Delphi licences and wants standard HTTP semantics rather than a whole platform. Its feature list maps almost one-to-one onto what an API team is asked for: RESTful controllers following Richardson Maturity Model Level 3, JSON-RPC 2.0 with automatic object remotisation, MVC controller inheritance, a middleware pipeline, dependency injection, OpenAPI/Swagger documentation generation, full TLS 1.3 support with automatic negotiation of the highest available version, and a built-in ORM layer.

Installation follows the Delphi way of doing things. The official installation guide documents two methods:

```text
Method 1 — GitHub Releases
  Download the release package from
  https://github.com/danieleteti/delphimvcframework/releases/latest
  and install it into the IDE.

Method 2 — Git clone (for contributors)
  git clone https://github.com/danieleteti/delphimvcframework.git
  cd delphimvcframework
```

Once installed, the IDE gains a project template: the guide instructs you to verify that **Delphi Project → DMVC → DelphiMVCFramework Project** is available. That menu entry is the fastest path from an empty project to a running server.

Controllers are attribute-driven, which is why DMVC code stays readable. This is the framework's own `basicdemo_server` sample controller, quoted from the repository:

```pascal
unit App1MainControllerU;

interface

{$I dmvcframework.inc}

uses
  MVCFramework,
  MVCFramework.Logger,
  MVCFramework.Commons,
  Web.HTTPApp;

type

  [MVCPath('/')]
  TApp1MainController = class(TMVCController)
  public
    [MVCPath('/')]
    [MVCHTTPMethod([httpGET])]
    procedure Index;

    [MVCPath('/hello')]
    [MVCHTTPMethod([httpGET])]
    [MVCProduces(TMVCMediaType.TEXT_HTML)]
    procedure HelloWorld;

    [MVCPath('/div/($par1)/($par2)')]
    [MVCHTTPMethod([httpGET])]
    procedure RaiseException(const par1, par2: integer);
  end;
```

Read the path attributes carefully — `/div/($par1)/($par2)` is how DMVC expresses typed path parameters, and `MVCProduces` declares the response media type. There is no separate routing DSL to learn: the route lives on the method that serves it, which keeps controllers self-documenting.

![Creating a DelphiMVCFramework project in the IDE](/img/screenshots/dmvc-ide-wizard.jpg "The DMVC project template installed into the IDE by the framework's installer")

## fcl-web / fpWeb — The Option With Nothing to Install

Free Pascal ships a web package, `fcl-web`, inside the compiler's own runtime library. The units you build on are real and stable — `TFPWebModule`, `TFPWebAction`, `TFPWebActions`, `TFPWebTemplate`, plus the `TRequest`/`TResponse` pair from the `httpdefs` layer. Because it is distributed with the compiler, "installation" is:

```bash
# Debian/Ubuntu: the compiler plus the FCL web units
sudo apt install fpc fp-units-fcl
```

What you get for that is a module/action dispatch model: a `TFPWebModule` owns a set of `TFPWebAction` objects, each with a name, a default event handler, and a URL pattern, and `TFPWebTemplate` renders dynamic HTML. What you do not get is an ORM, dependency injection, JSON-RPC, or OpenAPI generation. fpWeb is the correct answer for a small internal service or a server that must build on a machine where downloading third-party packages is not possible — and the wrong answer the moment your requirements include the words "OpenAPI" or "JSON-RPC."

## Pitfalls: Pascal Server Development in the Real World

- **FPC 3.2.2 will bite you with mORMot 2.** The variant late-binding regression documented in the project README produces confusing failures. Use 3.2.3 or the `fixes-3_2` branch and save yourself the debugging session.
- **Delphi is not a Linux compiler for general units.** Cross-platform server work belongs to Free Pascal. Teams that assume "Delphi can target Linux anyway" hit the README's caveat late in the project.
- **Static linking needs the bundled object files.** Both compilers require the prebuilt `.o`/`.obj` files from mORMot's `static/` directory when linking statically. Clone the repository; do not copy a subset of `src/`.
- **Windows service vs Linux daemon.** A Pascal server started as a console application behaves differently under a service manager — handle signals and shutdown paths explicitly, and always test a restart, not just a start.
- **TLS certificates are your job.** DMVC negotiates TLS 1.3 for you, but certificate issuance, renewal, and path configuration are deployment concerns. Terminating TLS at a reverse proxy is usually simpler than managing certificates inside the application.
- **Migration is not optional for mORMot 1.x.** Version 1.18 is maintenance-only. Its README asks users to upgrade to mORMot 2, and starting new work on 1.x means adopting a codebase nobody is extending.
- **Sample code is version-sensitive.** Both projects keep samples in-repo; when an attribute or unit name does not exist in your installed version, check the sample's commit date against your release rather than rewriting from memory.

## FAQ

**Is Object Pascal still worth using for a new web service in 2026?**
Yes, in the specific case where your organisation already maintains Pascal code or Delphi licences. Both mORMot 2 and DelphiMVCFramework are actively developed, deploy as small native binaries, and avoid the runtime dependency churn that container-based stacks bring. For greenfield projects in a polyglot team, the hiring pool — not the framework — is the limiting factor.

**What is the difference between mORMot 2 and DelphiMVCFramework?**
mORMot 2 is a platform: ORM, service layer, MVC, JSON kernel, RTL, and HTTP server, all in one repository with a single package to compile. DelphiMVCFramework is a focused web/API framework built around controllers and attributes, with strong REST and JSON-RPC support and OpenAPI generation. Choose by scope: platform versus framework.

**Can I deploy either framework on a Linux VPS?**
Yes — with Free Pascal. mORMot 2 explicitly targets Windows, Linux, BSD, and macOS for servers and runs nightly regression tests on Linux distributions, while Delphi's general units are Windows-only. The output is a native binary, which makes it easy to run under systemd behind a reverse proxy.

**Do I need Lazarus to use mORMot 2?**
No, but it is the smoothest path in 2026: the repository ships `packages/lazarus/mormot2.lpk`, and the README documents compiling it directly. Delphi users build the `.dpr` samples instead — just remember the Windows-only caveat for general units.

**When should I use fpWeb instead of the other two?**
When you need a small HTTP service with no third-party dependencies. `fcl-web` is part of the Free Pascal distribution and provides module/action dispatch and templating, but it does not provide an ORM, DI container, JSON-RPC, or OpenAPI generation. The moment any of those appears in your requirements, move to mORMot 2 or DelphiMVCFramework.

**How do these compare on performance?**
All three compile to native code with no interpreter or garbage-collected runtime in the request path, which is why Pascal services are common in latency-sensitive industrial and point-of-sale systems. mORMot 2's optimised RTL and JSON kernel are the most aggressively tuned of the three; fpWeb is minimal by design. Benchmark your own endpoints — allocation and database access will dominate, exactly as in any other stack.

For related reading, see our [Java web frameworks comparison](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/) for the same framework-selection logic applied to a compiled, statically typed ecosystem, our [F# web frameworks guide](../2026-08-13-fsharp-web-frameworks-giraffe-falco-saturn/) for another statically typed stack with a small deployment footprint, and our [OCaml web frameworks comparison](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/) if you are weighing native-code web servers more broadly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Open-Source Pascal Web Frameworks in 2026: mORMot 2 vs DelphiMVCFramework vs fpWeb",
  "description": "Compare mORMot 2, DelphiMVCFramework and Free Pascal's fcl-web (fpWeb) for building REST APIs and web applications in Object Pascal in 2026, with real install steps and sample code.",
  "datePublished": "2026-09-15",
  "dateModified": "2026-09-15",
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
