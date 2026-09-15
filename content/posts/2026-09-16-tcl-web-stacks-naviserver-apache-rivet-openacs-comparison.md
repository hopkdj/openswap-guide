---
title: "Tcl Web Stacks in 2026: NaviServer vs Apache Rivet vs OpenACS Compared"
date: "2026-09-16"
tags: ["tcl", "web-frameworks", "self-hosted", "deployment", "server-software", "open-source"]
draft: false
cover: "/img/screenshots/naviserver-arch.jpg"
---

Most developers write off Tcl as a language that died with the dot-com boom. Then you check the commit log: **NaviServer's repository received a commit on September 15, 2026**, Apache Tcl Rivet was pushed on **August 30, 2026**, and OpenACS core on **August 31, 2026**. These are not museum pieces on life support — they are small, focused, actively maintained codebases that still serve real deployments, and they solve a problem most modern stacks handle badly: **running long-lived, single-process business logic with almost no memory overhead.**

If you are evaluating a Tcl web stack in 2026 — whether for a legacy migration, an embedded control panel, or just to escape the JavaScript build-tool treadmill — you have exactly three credible options. This guide compares them with live repository data, real build commands pulled from the official sources, and honest notes on where each one will hurt you.

## TL;DR — Quick Verdict

**Pick NaviServer** if you want a standalone, multithreaded application server that speaks HTTP(S) and a dozen other protocols and can be extended in both C and Tcl. **Pick Apache Rivet** if Apache httpd 2.4 is already your web tier and you want Tcl pages served as a plain module instead of standing up another daemon. **Pick OpenACS** if you need an actual application framework — users, permissions, packages, upgrade paths — on top of NaviServer with PostgreSQL. If you only need to serve static files or a single script, none of them are worth the build time; use nginx or Caddy and run a Tcl script under `tclsh`.

## Comparison Table: NaviServer vs Apache Rivet vs OpenACS (September 2026)

| Dimension | NaviServer | Apache Tcl Rivet | OpenACS |
|---|---|---|---|
| Role | Standalone multithreaded app server | Apache httpd 2.4 module | Application toolkit on top of NaviServer |
| Written in | C + Tcl (extensible in both) | C (module) + Tcl pages | Tcl + SQL data model |
| GitHub repository | `naviserver-project/naviserver` | `apache/tcl-rivet` | `openacs/openacs-core` |
| Stars (live) | **53** | **35** | **50** |
| Last push (live) | **2026-09-15** | **2026-08-30** | **2026-08-31** |
| Current line | NaviServer 5 (also 4.99.x) | Rivet 3.2 | OpenACS 5.10.x |
| Tcl support | NaviServer 5 adds **Tcl 9**; 4.99.x needs Tcl 8.5/8.6 | Tcl 8.6+ | Tcl 8.6/9 via NaviServer |
| Install method | Source build (`autogen.sh` / `configure` / `make`) | Autotools + `apxs`, `make install` | `install-oacs.sh` + interactive installer |
| Config format | Tcl file (`nsd-config.tcl`) | Apache directives | Tcl file (`openacs-config.tcl`) |
| Persistence | Scripted (`nsdb`, raw driver calls) | Whatever Tcl packages you load | **Full data model** with PostgreSQL or Oracle |
| Package manager | No | No | **APM** (packages, versions, upgrades) |
| Best fit | Protocol servers, APIs, control planes | Adding Tcl to an existing httpd | Multi-user apps, universities, portals |
| Container story | Build-your-own (env vars use the `nsd_` prefix) | Build-your-own module + httpd image | Build-your-own via installer script |

## Decision Matrix: Match the Tool to the Job

| Your situation | Pick | Why |
|---|---|---|
| You need a Tcl HTTP/API service with no Apache in front | **NaviServer** | Thread-pooled server, no separate web tier to babysit |
| Apache 2.4 is already your front door | **Apache Rivet** | Add a module, keep the existing vhosts and TLS config |
| You need logins, roles, groups, and packages | **OpenACS** | Per-user permissions and APM are already built |
| You want a Tcl control plane talking non-HTTP protocols | **NaviServer** | Multiprotocol design, extensible in C and Tcl |
| You need a database-agnostic Tcl service | **Apache Rivet** | You choose the driver; no imposed schema |
| You need a university-grade portal today | **OpenACS** | The `.LRN` lineage has been shipping since 1999 |
| You are prototyping for a weekend | **None of these** | `tclsh` plus a socket is faster to start |

## NaviServer — The Standalone Multithreaded Server

![NaviServer project logo from the official repository](/img/screenshots/naviserver-logo.jpg)

NaviServer is the direct descendant of the AOLserver line: a C core with an embedded Tcl interpreter per thread, designed so that one process can serve many concurrent connections without forking per request. The official README describes it as "a versatile multiprotocol (HTTP(S), etc.) server written in C/Tcl… designed to be easily extended in either language."

The build path on Linux is deliberately boring, and every command below comes from the project's own README:

```bash
# 1. Tcl with threads enabled, installed into the same prefix as NaviServer
gunzip < tcl8.6.18-src.tar.gz | tar xvf -
cd tcl8.6.18/unix
./configure --prefix=/usr/local/ns --enable-threads --enable-symbols
make install

# 2. NaviServer itself (source checkout)
cd /path/to/naviserver
./autogen.sh
./configure --prefix=/usr/local/ns --with-tcl=/usr/local/ns/lib
make && make install
```

The project also maintains a **Unix install script** at `gustafn/install-ns` (`install-ns.sh`) that wraps the whole process — Tcl, NaviServer, optional modules — with flags for the allocator and other build-time choices. That is the path to take if you do not want to hand-tune configure flags.

Configuration is not YAML or INI; it is Tcl evaluated at startup. NaviServer 5 ships a generated `conf/nsd-config.tcl` that is assembled from fragment files in `conf/nsd-config.d/`, and the header states the precedence rules explicitly: variables set directly in the file win, then environment variables with the **`nsd_` prefix**, then the built-in `defaultConfig` values. That env-var layer is what makes twelve-factor-ish container setups practical:

```tcl
# /usr/local/ns/conf/nsd-config.tcl (excerpt style, NaviServer 5)
ns_section "ns/server/${server}/module/nscgi"
ns_param   map "GET  /cgi-bin /usr/local/ns/cgi-bin"
ns_param   map "POST /cgi-bin /usr/local/ns/cgi-bin"

ns_section "ns/server/${server}/modules"
ns_param   nscgi  nscgi.so

ns_section "ns/threads"
ns_param   maxthreads   20
```

Pages are written either as plain Tcl procedures or as `.adp` templates that mix markup and Tcl blocks:

```tcl
# /usr/local/ns/pages/status.adp
<h1>@title@</h1>
<%
    set title "Service status"
    ns_return 200 text/plain "threads: [ns_info threads]"
%>
```

**Where it hurts:** no official container image, so you own the build pipeline. And because one interpreter lives per thread, unsynchronized global state is a genuine bug class — use `nsv_*` shared variables or a mutex instead of a bare `set ::counter`.

## Apache Rivet — Tcl Inside Your Existing httpd

Apache Tcl Rivet is not a server. It is a module that compiles into Apache httpd 2.4 and hands `.rvt` pages to an embedded Tcl interpreter. The build uses the standard autotools dance, with the exact configure options documented in the repository's `INSTALL` file:

```bash
./configure --with-tcl=/usr/lib/tcl8.6                   \
            --with-apache=/usr/local/apache2             \
            --with-apxs=/usr/local/apache2/bin/apxs      \
            --with-rivet-target-dir=/usr/local/lib/rivet3.2 \
            --enable-version-display
make
sudo make install
```

The module loads into httpd the same way any other module does — the `rivet_module` identifier appears in the project's own install documentation:

```apache
LoadModule rivet_module modules/mod_rivet.so

<Directory "/usr/local/apache2/htdocs">
    Options Indexes FollowSymLinks
    AddHandler rivet-page .rvt
</Directory>
```

Since Rivet 2.x the command set lives in the `::rivet` namespace and is fully qualified by default. That means page code reads like ordinary Tcl with an explicit I/O vocabulary — request variables in, generated HTML out:

```tcl
<!DOCTYPE html>
<html>
<body>
<%
    set name [::rivet::var get name]
    if {$name eq ""} { set name "world" }
    ::rivet::html "<p>Hello, $name</p>"
%>
</body>
</html>
```

**Where it hurts:** you inherit Apache's operational model, for better and worse — thread tuning, module ordering, and version pinning. Rivet 3.x targets **Apache 2.4**; if you are running an older httpd, you are on the legacy Rivet 2.x line. The upside is real, though: TLS, reverse proxying, rate limits, and log shipping are already solved by httpd, and you never introduce a second daemon.

## OpenACS — The Application Toolkit

OpenACS is the heavyweight of the three: a Tcl application framework with a real data model, users, groups, permissions, and its own package manager, running on NaviServer with PostgreSQL as the primary database. The repository at `openacs/openacs-core` is the core package set — 50 stars, last pushed August 31, 2026.

The practical difference from the other two is `APM`. Instead of writing ad-hoc login code, you query the installed package registry that the framework maintains:

```bash
psql -U openacs -d openacs \
  -c "select package_key, version from apm_package_installed order by package_key limit 10;"
```

Installation is driven by the same toolchain family as NaviServer: the installer repository ships both `install-ns.sh` (build NaviServer) and `install-oacs.sh` (build and bootstrap OpenACS). The interactive installer creates the database, loads the core data model, and installs the base packages. Configuration then lives in `conf/openacs-config.tcl`, which is included from `conf/openacs-config.d/` fragments in the NaviServer 5 line.

**Where it hurts:** upgrades. You are not deploying a binary, you are upgrading a database plus a package graph, and the official guidance is to read the release notes and test the upgrade on a clone first. OpenACS also assumes PostgreSQL (Oracle support is a legacy path), so "just swap the database" is not a realistic escape hatch.

## Performance, Threading, and Scaling Notes

None of these stacks publish modern, reproducible benchmark suites, so anyone quoting "X requests per second" for them is guessing. What you can reason about is the architecture. NaviServer and OpenACS use a **thread pool with one Tcl interpreter per thread**; the cheap tuning knobs are `maxthreads` and connection limits in `nsd-config.tcl`, and the expensive mistake is performing blocking I/O inside a request handler on a short thread pool. Rivet inherits Apache's MPM — the prefork MPM gives you process isolation at the cost of memory, while event/worker MPMs are far more efficient for Tcl pages that wait on I/O.

A realistic production layout for all three pushes TLS and static assets to a reverse proxy (nginx or Caddy), keeps the Tcl process on a private interface, and uses connection keep-alive to hide interpreter spin-up. Log with `ns_log` or Apache's `%D` timing so you can attribute latency to Tcl code rather than the network — you cannot tune what you have not measured.

## Migration and Coexistence Pitfalls

- **AOLserver is the ancestor, not an option.** If you are migrating an AOLserver codebase, the supported path is NaviServer; the old server itself is unmaintained.
- **Tcl version drift is a real trap.** NaviServer 5 added Tcl 9 support while the 4.99.x line requires Tcl 8.5/8.6. Extensions and database drivers compiled against one may not load under the other — pin your Tcl version in the same image as NaviServer.
- **Do not split a migration across stacks.** Porting a page from Rivet to NaviServer means replacing Apache request plumbing with NaviServer's connection API. Doing it page by page creates two authentication models; do it in a module at a time instead.
- **Global state is poison.** With one interpreter per thread, `set ::total` is a per-thread variable that looks like a counter and behaves like a random number generator. Use `nsv_*` shared variables or `ns_mutex`.
- **Budget for the build.** With no official container image for any of these, a reproducible image is your responsibility. Use a two-stage Dockerfile so the compiler toolchain never ships to production:

```dockerfile
FROM debian:bookworm-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl build-essential autoconf m4 tcl-dev libssl-dev
WORKDIR /src
# build Tcl, then NaviServer into /usr/local/ns
COPY --from=builder /usr/local/ns /usr/local/ns
EXPOSE 8080
CMD ["/usr/local/ns/bin/nsd", "-c", "/usr/local/ns/conf/nsd-config.tcl", "-f"]
```

## Why Self-Host a Tcl Web Stack?

Self-hosting these stacks is not nostalgia — it is an ownership decision. A NaviServer or Rivet deployment is a single process with a plain-text configuration file you can read end to end, no package registry round trips, no toolchain vendored into your image, and a memory footprint that lets a $5 VPS host several services. When something breaks you get a Tcl stack trace, not a wall of bundled JavaScript. For control planes, internal APIs, and long-lived line-of-business logic, that trade — a smaller ecosystem in exchange for a system you fully understand — is often the right one.

The same reasoning drives the rest of the niche-language stack comparisons on this site. If you like the "small runtime, long lifespan" trade, our [Ada web frameworks comparison](../2026-09-15-ada-web-frameworks-aws-awa-gnoga-comparison/) covers AWS, AWA, and Gnoga, and the [Pascal web frameworks guide](../2026-09-15-pascal-web-frameworks-mormot2-delphimvcframework-fpweb/) looks at Mormot2, DelphiMVCFramework, and fpWeb. For an equally long-lived but object-oriented alternative, see the [Smalltalk web stacks comparison](../2026-09-15-smalltalk-web-stacks-pharo-seaside-squeak-gnu-smalltalk/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Tcl Web Stacks in 2026: NaviServer vs Apache Rivet vs OpenACS Compared",
  "description": "NaviServer vs Apache Rivet vs OpenACS compared with live GitHub data, real build commands, threading notes, and migration pitfalls for Tcl web development in 2026.",
  "datePublished": "2026-09-16",
  "dateModified": "2026-09-16",
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

### Is Tcl web development dead in 2026?

No. All three stacks received commits within the last three weeks of September 2026: NaviServer on September 15, Apache Tcl Rivet on August 30, and OpenACS core on August 31. The ecosystems are small, but the maintainers are active and the tooling still builds from source on current Linux distributions.

### Should I choose NaviServer or Apache Rivet?

Choose NaviServer if you want a standalone server that also speaks non-HTTP protocols and can be extended in C as well as Tcl. Choose Apache Rivet if Apache httpd 2.4 is already your web tier and you would rather add a module than run a second daemon. They solve the same problem at different layers.

### Can I run NaviServer in Docker?

Yes, but you build the image yourself. There is no official container image, so the practical pattern is a two-stage Dockerfile that compiles Tcl and NaviServer with the `install-ns.sh` script and copies `/usr/local/ns` into a slim runtime image. NaviServer 5's configuration layer reads `nsd_`-prefixed environment variables, which makes per-environment overrides straightforward.

### Does OpenACS still have an active community?

Yes. The core package repository was pushed on August 31, 2026, and the project still publishes releases with upgrade instructions. Activity is concentrated in maintenance and security work rather than headline features, and the community is small — expect forum-based support rather than a large vendor ecosystem.

### What is the fastest way to try a Tcl web app?

Install Tcl, then run NaviServer from source with the `install-ns.sh` script. You will have a working server, sample configuration, and ADP template directory in a few minutes. If you already run Apache, installing Rivet and adding a single `.rvt` page is even faster.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
