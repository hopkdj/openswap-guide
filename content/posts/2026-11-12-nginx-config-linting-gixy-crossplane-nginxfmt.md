---
title: "Nginx Config Linting in 2026: Gixy vs Crossplane vs nginxfmt"
date: "2026-11-12"
tags: ["nginx", "linting", "security", "configuration-management", "ci-cd"]
draft: false
cover: "/img/screenshots/gixy-nginx-lint.jpg"
---

`nginx -t` tells you your configuration parses. It does not tell you that your `alias` directive lets anyone read `/etc/passwd`, that your `add_header` inheritance drops the security headers you just carefully set, or that a `$uri` captured from a regex can smuggle a newline into a response header.

Those are configuration bugs, not code bugs, and they are invisible to every test in your repository. Nginx config has become the largest untested surface in most self-hosted stacks — hundreds of lines of directives, hand-edited during incidents, reviewed by nobody, deployed with `reload`.

Three tools address this gap, and they do completely different jobs: **Gixy** finds security misconfigurations, **Crossplane** turns configs into a parseable syntax tree, and **nginxfmt** normalizes them so the diff you review is the change you meant. Used together, they turn nginx config into something you can actually gate in CI.

## TL;DR: Quick Verdict

- **Want the single highest-value command today: `gixy /etc/nginx/nginx.conf`.** It is the only mature static security analyzer for nginx, with plugins for SSRF, HTTP splitting, `alias` path traversal, host header spoofing, and `add_header` redefinition. Read the maintenance caveat below before you build a pipeline on it.
- **Choose `crossplane` when you need structure, not opinions.** It converts nginx config to JSON and back, which makes it the right foundation for custom policy checks, migrations between proxy stacks, or generating configs programmatically.
- **Choose `nginxfmt` when the problem is that nobody can review the diff.** Consistent indentation, brace placement, and blank-line handling turn a 400-line whitespace storm into a readable change.

The honest summary: nginx tooling is thinner than Kubernetes or Terraform tooling, and the best security analyzer has not had a commit since 2024. Plan accordingly.

## Side-by-Side Comparison

| Dimension | Gixy | Crossplane | nginxfmt |
|---|---|---|---|
| Stars | **8,563** | 764 | 422 |
| Latest release | v0.1.21 | v0.5.8 | 1.4.0 (PyPI) |
| Last push | **2024-07-28** | 2026-03-31 | 2026-03-09 |
| Language | Python | Python | Python |
| License | MPL-2.0 (per project) | Apache-2.0 | Apache-2.0 |
| What it does | Security static analysis | Parse/build config as JSON | Format/beautify config |
| Understands `include` | Yes | Yes | No (file-local) |
| Output | Severity-ranked findings | JSON tree | Rewritten config |
| CI exit code on problems | Yes (non-zero on issues) | Not a linter | Not a linter |
| Maintenance status | **Stale (2+ years)** | Active-ish | Active-ish |

Gixy's star count is 11x Crossplane's, but its last push is more than two years behind. That combination — huge adoption, no recent maintenance — is the single most important fact in this article, and it shapes how you should deploy it.

## Decision Matrix: Pick in Ten Seconds

| Your problem | Use this | Why |
|---|---|---|
| "Are we vulnerable to config-level attacks?" | **Gixy** | Eight targeted security plugins, severity ranked |
| "I need to enforce our own nginx conventions in CI" | **Crossplane** | Parse to JSON, write your own checks |
| "Migrating 200 server blocks from nginx to another proxy" | **Crossplane** | `parse` then `build` gives a programmatic path |
| "Every config diff is unreadable whitespace" | **nginxfmt** | Deterministic formatting |
| "Reviewers keep missing the one real change" | **nginxfmt** + **Gixy** | Normalize first, then scan for security deltas |
| "We just want the cheapest possible gate" | **Gixy** | One command, non-zero exit on findings |

## Gixy: Security Analysis That Still Earns Its Stars

Gixy walks the nginx configuration tree, resolves includes, and applies plugins that encode known misconfiguration patterns. The README lists eight:

- `[ssrf]` server-side request forgery
- `[http_splitting]` HTTP splitting via newline injection
- `[origins]` referrer/origin validation problems
- `[add_header_redefinition]` response headers silently dropped by redefining `add_header`
- `[host_spoofing]` Host header forgery
- `[valid_referers]` `none` in `valid_referers`
- `[add_header_multiline]` multiline response headers
- `[alias_traversal]` path traversal via misconfigured `alias`

Installation and use are two commands:

```bash
pip install gixy
gixy /etc/nginx/nginx.conf
```

By default it analyzes `/etc/nginx/nginx.conf`, so on most hosts you can run `gixy` with no arguments. A real finding looks like this, taken from the project's own README:

```plaintext
Problem: [http_splitting] Possible HTTP-Splitting vulnerability.
Description: Using variables that can contain "\n" may lead to http injection.
Reason: At least variable "$action" can contain "\n"
Pseudo config:
include /etc/nginx/sites/default.conf;

  server {
    location ~ /v1/((?<action>[^.]*)\.json)?$ {
      add_header X-Action $action;
    }
  }
```

That output is worth studying: it does not just say "line 42 is bad," it reconstructs the effective configuration after `include` resolution. That is why Gixy finds problems humans miss — the vulnerability lives in the interaction between a directive in `sites/default.conf` and a regex location in another file.

Suppressing a plugin you have consciously accepted:

```bash
gixy --skips http_splitting /etc/nginx/nginx.conf
```

**The maintenance caveat, stated plainly.** Gixy's last push was 2024-07-28, its release is v0.1.21, and its README still lists supported Python versions as 2.7, 3.5, 3.6, and 3.7. On a modern distribution, a bare `pip install gixy` is a gamble. Treat it as a pinned, isolated dependency — a container or a dedicated virtualenv — rather than something you install into a shared CI image and hope keeps working.

A pragmatic container invocation keeps the host clean and the version fixed:

```bash
docker run --rm -v /etc/nginx:/etc/nginx:ro \
  python:3.7-slim \
  sh -c "pip install --no-cache-dir gixy==0.1.21 && gixy /etc/nginx/nginx.conf"
```

Two properties make this worth the friction: the config is mounted **read-only**, so the analyzer cannot modify production, and the Python version is pinned, so the tool cannot break when the base image moves.

![Crossplane logo, the nginx configuration parser that converts configs to JSON and back](/img/screenshots/crossplane-nginx-parse.jpg "Crossplane by NGINX converts nginx configuration into JSON, enabling custom policy checks and programmatic migrations")

## Crossplane: Turn Config Into Data

Crossplane is not a linter and does not pretend to be. It is a parser — maintained under the `nginxinc` organization — that converts nginx configuration into a JSON document and back again.

```bash
pip install crossplane
crossplane parse --indent=4 /etc/nginx/nginx.conf
```

The output contains the parsed directive tree, per-file status, and any errors, which makes it the right input for policy checks nginx itself cannot express:

```bash
crossplane parse /etc/nginx/nginx.conf -o config.json
```

Beyond `parse`, the CLI ships `build`, `lex`, `minify`, and `format`. The `build` direction is the interesting one for migrations:

```bash
crossplane build config.json -d /etc/nginx/rebuilt/
```

The README is explicit about the guarantee: saving the output of `parse` and rebuilding with `build` should produce no content differences, only formatting differences. That property is what makes Crossplane viable for bulk edits — parse 200 server blocks, modify the JSON with a script, rebuild, then diff the result and review only what actually changed.

Its own `format` subcommand is described in the README as "quick and dirty," explicitly a demonstration of the parsing API rather than a full formatter. If formatting is your goal, use the dedicated tool below instead of bolting a script onto Crossplane.

**Where it hurts:** it validates syntax, not intent. `crossplane parse` will happily return a perfectly structured tree for a configuration that leaks files through `alias`. It is infrastructure for your checks, not a check.

## nginxfmt: Make the Diff Reviewable

The most underrated failure in configuration management is review fatigue. When every pull request reformats the whole file, reviewers approve without reading, and the one dangerous directive change rides along unnoticed.

`nginxfmt` fixes that by enforcing a deterministic style: four spaces per level (configurable), neighboring blank lines collapsed to at most two, Java-style brace placement, whitespace collapsed outside quotes and comments, and configurable line endings.

```bash
pip install nginxfmt
nginxfmt /etc/nginx/nginx.conf
```

Useful flags, straight from its help output:

```bash
nginxfmt -i 2 nginx.conf      # two-space indent
nginxfmt -p nginx.conf        # print result, leave the original untouched
nginxfmt -b nginx.conf        # back up the original as nginx.conf~
cat nginx.conf | nginxfmt -   # pipe mode
```

The workflow that matters: run it once across the repository as an isolated commit, then add a check that the file is already formatted. From that point on, every diff shows only semantic changes.

**Where it hurts:** it has no notion of `include` — it formats one file at a time — and it has no opinions about whether the configuration is correct. Formatting is not validation, and a beautifully indented config can still be a security incident.

## A CI Pipeline That Gates Nginx Config

This is the sequence that works: format check, structural parse, then security scan. Ordering matters — the security scan runs last so its findings are not buried in formatting noise.

```yaml
name: nginx-config
on:
  pull_request:
    paths:
      - "nginx/**"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Syntax check with the real binary
        run: docker run --rm -v "$PWD/nginx:/etc/nginx:ro" nginx:1.27 nginx -t

      - name: Structural parse
        run: |
          pip install crossplane==0.5.8
          crossplane parse nginx/nginx.conf -o /tmp/config.json

      - name: Security scan
        run: |
          docker run --rm -v "$PWD/nginx:/etc/nginx:ro" python:3.7-slim \
            sh -c "pip install --no-cache-dir gixy==0.1.21 && gixy /etc/nginx/nginx.conf"
```

Note the first step: `nginx -t` inside the exact image tag you deploy. A config that parses under nginx 1.24 may fail on 1.27 because a directive was removed, and linting tools will not catch that — only the real binary will.

## Pitfalls That Will Bite You

**A green lint does not mean a safe config.** Gixy covers eight vulnerability classes. It does not know your application, your authentication model, or whether `proxy_pass` points at something it should not. Static analysis reduces the search space; it does not close it.

**`add_header` inheritance is the most common self-inflicted wound.** Defining `add_header` inside a `location` block discards `add_header` directives inherited from the parent `server` block. Teams add one cache header and silently lose HSTS. Gixy's `add_header_redefinition` plugin exists precisely because this bites so often.

**Unmaintained tooling needs pinning, not trust.** Gixy is excellent and stale at the same time. Pin the version, isolate it in a container, and re-evaluate quarterly. If a hosted fork appears with active maintenance, migrate.

**Formatting changes must land before the gate, not with it.** If you enable a format check in the same pull request that reformats the tree, the check will fail on the reformat itself and nobody will know which change broke what.

**`include` resolution is where real configs live.** Any tool that reads a single file sees a fraction of the effective configuration. Crossplane and Gixy both resolve includes; a naive grep-based check does not.

**Testing config in production is still testing in production.** `nginx -t` plus a reload is not a test — it validates syntax and starts serving traffic with whatever semantics you wrote. Stage the config behind a canary upstream when the change touches routing.

For the broader picture, our [OpenResty vs nginx vs Caddy web server comparison](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) covers when nginx is the right server at all, the [self-hosted DDoS protection guide covering nginx, HAProxy, BunkerWeb and CrowdSec](../2026-04-26-self-hosted-ddos-protection-nginx-haproxy-bunkerweb-crowdsec-guide/) shows where edge filtering belongs relative to config-level defenses, and teams that prefer a UI over hand-edited configs should read the [nginx-proxy-manager vs SWAG vs Caddy Docker Proxy comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nginx Config Linting in 2026: Gixy vs Crossplane vs nginxfmt",
  "description": "How to lint, parse and format nginx configuration: Gixy for security static analysis, Crossplane for JSON-based structural validation and nginxfmt for reviewable diffs, with a CI pipeline that gates config changes.",
  "datePublished": "2026-11-12",
  "dateModified": "2026-11-12",
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

### Does `nginx -t` already validate my configuration?

It validates syntax and loadability only. `nginx -t` will not tell you that an `alias` directive permits path traversal or that redefining `add_header` dropped your security headers. You need a static analyzer like Gixy for those classes of bug.

### Is Gixy still maintained?

Not actively. Its last repository push was 2024-07-28, the current release is v0.1.21, and its documented Python support stops at 3.7. It remains the most capable nginx security analyzer available, so the practical answer is to pin the version and run it in an isolated container rather than skip it.

### What is the difference between Crossplane and a linter?

Crossplane is a parser. It converts nginx configuration to JSON and back, reporting structural errors only. A linter encodes opinions about what a good configuration looks like. Crossplane gives you the data structure to write those opinions yourself; it does not ship them.

### Can these tools handle configs that use `include`?

Gixy and Crossplane resolve `include` directives and analyze the effective configuration across files, which is essential because a vulnerability often spans a `server` block in one file and a `location` in another. `nginxfmt` formats one file at a time and has no include awareness.

### How do I add nginx config checks to CI without breaking every pull request?

Sequence it: run `nginxfmt` once as an isolated reformat commit, then add `nginx -t` in your deployed image tag, then `crossplane parse` for structure, then `gixy` for security. Introduce each step separately so failures are attributable.

### What is the most common nginx misconfiguration found in practice?

`add_header` inheritance. A directive added inside a `location` block silently discards headers inherited from the parent block, which is how sites lose HSTS or `X-Frame-Options` after a routine cache-header change. Gixy's `add_header_redefinition` plugin targets exactly this failure.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
