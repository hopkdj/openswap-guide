---
title: "Node.js 26 LTS vs 24 vs 22 in 2026: Which Runtime Should Your Self-Hosted Apps Actually Run?"
date: "2026-11-27"
tags: ["nodejs", "javascript", "self-hosted", "docker", "upgrade-guide"]
draft: false
cover: "/img/screenshots/nodejs-26-logo.jpg"
description: "Node.js 26 became LTS on October 28, 2026, Node 24 left active support on October 20, and Node 20 is already end-of-life. Here is the support matrix, the breaking changes that break Docker images, and a migration path that does not take down production."
---

Three Node.js release lines changed status inside six weeks. **Node.js 26 entered long-term support on October 28, 2026** (current patch 26.13.1). **Node 24 left active support on October 20, 2026** and is now maintenance-only until April 2028. **Node 20 reached end-of-life on April 30, 2026** and receives no patches at all — including security patches.

If your `Dockerfile` still says `FROM node:20`, you are running an unpatched runtime with a published CVE history behind it. That is the actual emergency, not the version number on your `package.json` engines field.

## TL;DR

- **Run Node 26 LTS** for anything new, and for anything internet-facing. LTS since October 28, 2026, supported until **April 30, 2029**.
- **Keep Node 24 only** if a native addon or framework has not published prebuilt binaries for 26 yet. Node 24 gets security fixes until April 2028 but no longer receives minor features.
- **Node 22 is a bridge, not a destination** — security support ends April 2027.
- **Migrate off Node 20 immediately.** There is no supported path where staying is cheaper than a two-hour Docker rebuild.

## Support status right now (November 27, 2026)

| | **Node 26** | **Node 24** | **Node 22** | **Node 20** |
|---|---|---|---|---|
| Current patch | 26.13.1 (2026-11-11) | 24.22.3 (2026-11-11) | 22.23.5 (2026-11-11) | 20.20.2 (2026-03-24) |
| LTS since | 2026-10-28 | 2025-10-28 | 2024-10-29 | 2023-10-24 |
| Active support until | 2027-10-27 | **2026-10-20 (ended)** | 2025-10-21 (ended) | 2024-10-22 (ended) |
| Security support until | 2029-04-30 | 2028-04-30 | 2027-04-30 | **2026-04-30 (EOL)** |
| V8 | 14.6 (Chromium 146) | 13.x | 12.x | 11.3 |
| Notable runtime API | Temporal enabled by default | Stable fetch/Undici 7 | Native test runner maturing | — |
| Verdict | **Default choice** | Hold if blocked | Short-term only | **Migrate now** |

## Decision matrix

| Your situation | Runtime | Why |
|---|---|---|
| New service, standard dependencies | **Node 26** | Four and a half years of security coverage, current V8 |
| Service with `better-sqlite3`, `sharp`, `bcrypt` | **Node 26 after a rebuild test** | Native addons must be recompiled against V8 14.6 |
| Framework pinned to an older major | **Node 24** | Still patched until 2028 while you upgrade the framework |
| Lambda-style container you rebuild monthly | **Node 26** | Base image rebuild is already part of your pipeline |
| Anything still on 20 | **Node 26 this week** | No patches since April 2026 |

## What Node.js 26 changes that breaks containers

![Node.js logo](/img/screenshots/nodejs-26-logo.jpg "Node.js 26 LTS runtime selection guide")

Node 26 is not a cosmetic release. Five changes account for almost every failed upgrade:

**1. Temporal is enabled by default.** `Temporal` is now a global. Libraries that shipped their own `Temporal` polyfill and assigned `globalThis.Temporal` will now shadow or conflict with the built-in. Search your dependency tree before upgrading:

```bash
# Find packages that might bundle a Temporal polyfill
npm ls --all 2>/dev/null | grep -i temporal
grep -rl "globalThis.Temporal" node_modules --include=*.js | head
```

If a polyfill is present, remove it and import `Temporal` directly. The built-in is faster and spec-aligned.

**2. `http.Server.prototype.writeHeader()` is fully removed.** It was deprecated for years; in 26 it is gone. Any vendored middleware calling it throws `TypeError: res.writeHeader is not a function`. Replace with `writeHead()`:

```js
// Broken on Node 26
res.writeHeader(200, { 'Content-Type': 'application/json' });

// Correct
res.writeHead(200, { 'Content-Type': 'application/json' });
```

**3. The legacy `_stream_*` modules are gone.** `_stream_wrap`, `_stream_readable`, `_stream_writable`, `_stream_duplex`, `_stream_transform` and `_stream_passthrough` no longer exist. Old copies of `readable-stream` bundled inside transitive dependencies are the usual culprit. Fix by upgrading the offending package rather than patching `node_modules`.

**4. `--experimental-transform-types` was removed.** If your start script relied on Node stripping TypeScript enums or namespaces, that flag no longer exists. Either compile ahead of time or use the supported type-stripping path.

**5. Build requirements moved.** Node 26 requires **GCC 13.2 or newer** to compile from source and drops Python 3.9 from the build toolchain. Docker images based on Debian 12 build fine; older Alpine and CentOS 7 style bases do not.

## Upgrading a Dockerised service without downtime

The safe pattern is a multi-stage image pinned to a digest, health-checked, and rolled out behind your existing proxy. This is the compose service shape I use:

```yaml
services:
  api:
    build:
      context: .
      args:
        NODE_VERSION: "26.13.1"
    image: registry.example.com/api:node26
    restart: unless-stopped
    environment:
      NODE_ENV: production
      NODE_OPTIONS: "--max-old-space-size=1536"
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://127.0.0.1:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 15s
      timeout: 3s
      retries: 5
      start_period: 20s
    ports:
      - "127.0.0.1:3000:3000"
```

And the matching `Dockerfile`, with the version pinned so a rebuild is reproducible:

```dockerfile
ARG NODE_VERSION=26.13.1
FROM node:${NODE_VERSION}-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

FROM node:${NODE_VERSION}-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:${NODE_VERSION}-alpine
RUN apk add --no-cache tini
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
USER node
EXPOSE 3000
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/server.js"]
```

Two details matter more than they look. **`tini` as PID 1** makes signal handling correct in containers, so `docker stop` actually drains connections instead of killing them. **Pinning the patch version** means a rebuild next month does not silently pick up a different runtime than the one you tested.

If you run Node under a process supervisor instead of a container, the equivalent is an `nvm` install plus a systemd unit — our [process manager comparison](../2026-08-17-nodejs-process-managers-pm2-nodemon-forever-comparison/) covers when `pm2` still earns its place versus plain systemd.

## The rebuild test that catches 90% of failures

Run this against the new image before it sees traffic. It exercises the native addons, the date API, and the removed HTTP method in one pass:

```bash
docker run --rm -e NODE_ENV=production registry.example.com/api:node26 \
  node -e "
    const assert = require('node:assert');
    assert.strictEqual(typeof Temporal.Now.instant, 'function', 'Temporal missing');
    require('better-sqlite3');
    require('sharp');
    const http = require('node:http');
    assert.strictEqual(http.ServerResponse.prototype.writeHeader, undefined, 'writeHeader still present');
    console.log('runtime checks passed');
  "
```

If `require('better-sqlite3')` throws `NODE_MODULE_VERSION` mismatch, the addon was compiled against an older V8. Rebuild it in the `deps` stage — `npm ci` from scratch, not `npm rebuild` on a copied `node_modules` volume.

## Pitfalls worth knowing before you flip the tag

**Do not reuse a host-mounted `node_modules` volume.** A volume created under Node 20 contains binaries compiled for a different ABI. The container starts, then crashes on the first database call with a module version error. Delete the volume, do not "fix" it.

**Alpine's musl build is not interchangeable with the glibc build** for prebuilt native addons. If a package only ships glibc binaries, use `node:26-bookworm-slim` instead of Alpine rather than compiling from source in production.

**Memory defaults changed with V8 14.6.** The old-space heuristic on large hosts can now grow beyond what a container limit allows, and the OOM killer arrives before the garbage collector does. Set `--max-old-space-size` explicitly in `NODE_OPTIONS` to roughly 75% of the container limit.

**Temporal changes date arithmetic subtly.** `Temporal.PlainDate` has no time zone; code that previously used a polyfill with different defaults can produce off-by-one-day results around DST. Add a test that crosses a DST boundary before rolling out.

**`module.register()` is now runtime-deprecated.** Custom ESM loaders should move to the current `module.registerHooks` API. This is a warning today, not a failure, but it will be removed in a future major.

## Why self-host Node instead of moving to a managed runtime

Managed JavaScript runtimes price per request and hide the version you actually run. Self-hosting gives you the patch cadence, the memory limit, and the ability to test a major upgrade on staging before production sees it. For a comparison of the runtimes themselves — including Bun and Deno — see our [Node vs Bun vs Deno breakdown](../2026-08-28-nodejs-vs-bun-vs-deno-javascript-runtimes-comparison/). If you standardise on Node, keep observability boring: structured logs from [Pino or Winston](../2026-08-10-nodejs-logging-libraries-winston-pino-bunyan/) make a botched upgrade obvious in minutes rather than days.

## FAQ

**Is Node.js 26 an LTS release?**
Yes. Node 26 entered long-term support on **October 28, 2026** and receives security fixes until **April 30, 2029**. The current patch as of November 27, 2026 is 26.13.1.

**Node 24 still gets security patches, so why upgrade?**
Because it no longer gets active support — only critical fixes, on a slower cadence, until April 2028. More importantly, every month you wait increases the number of breaking changes you face at once. Upgrading one major with a tested pipeline is cheaper than skipping two.

**Will Node 26 break my native modules?**
Only if they are not rebuilt. Anything compiled against V8 13.x must be recompiled for V8 14.6. `npm ci` in a fresh build stage handles it; copying `node_modules` from an old host does not.

**Can I run Node 26 on Alpine?**
Yes, `node:26-alpine` is published. The caveat is musl versus glibc for prebuilt native addons — if a dependency ships only glibc binaries, use `node:26-bookworm-slim`.

**How do I roll back if the upgrade misbehaves?**
Keep the previous image tag (`api:node24`) deployed and pinned in your compose file. A rollback is then a one-line tag change and a `docker compose up -d`, with no rebuild and no data migration, because Node majors do not change your application data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js 26 LTS vs 24 vs 22 in 2026: Which Runtime Should Your Self-Hosted Apps Actually Run?",
  "description": "Node.js 26 became LTS on October 28, 2026, Node 24 left active support, and Node 20 is end-of-life. Compare support windows, breaking changes, and a safe Docker migration path.",
  "datePublished": "2026-11-27",
  "dateModified": "2026-11-27",
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
