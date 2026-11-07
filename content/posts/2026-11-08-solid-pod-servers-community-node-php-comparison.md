---
title: "Community Solid Server vs Node Solid Server vs PHP Solid Server: Self-Hosted Solid Pods in 2026"
date: "2026-11-08"
tags: ["self-hosted", "privacy", "solid", "data-ownership", "decentralized"]
cover: "/img/screenshots/solid-pod.jpg"
draft: false
---

Every cloud service you use holds a copy of your life: your calendar, your photos, your medical records, your half-finished novel. Solid flips that arrangement — instead of applications owning data, a **pod** (personal online data store) owns it, and applications request access through open protocols. Run your own pod server and the storage URL in your profile is a hostname you control.

The catch is that "run a Solid pod" has three very different answers in 2026, and the three implementations disagree about maturity, storage model and how much of the specification they actually ship. I deployed all three, read their configs, and compared what breaks first.

## TL;DR / Quick Verdict

- **Starting fresh, want the reference implementation with active development and modern access control** → **Community Solid Server (CSS)**. MIT licensed, TypeScript, modular config, v7.3.0, commits landing every week.
- **You need the original, most widely-deployed implementation with the largest body of documentation and existing pod migrations** → **Node Solid Server (NSS)**. 1,796 stars, `solid-server` 6.0.0, still maintained, but visibly slower-moving than CSS.
- **You want a pod on cheap shared PHP hosting with no Node runtime** → **PHP Solid Server** from pdsinterop. Small community (50 stars) but actively committed and genuinely deployable where Node is not an option.

The honest one-liner: **CSS is where the specification is being built, NSS is where the installed base is, and PHP Solid Server is for people who cannot run Node at all.** If you are unsure, run CSS.

## Comparison Table (live GitHub data, 2026-11-08)

| Dimension | Community Solid Server | Node Solid Server | PHP Solid Server (pdsinterop) |
|---|---|---|---|
| GitHub stars | 610 | 1,796 | 50 |
| Language | TypeScript | JavaScript | PHP |
| License | MIT | MIT-style (repo: Other) | MIT |
| Last commit | 2026-11-02 | 2026-08-08 | 2026-10-16 |
| Latest package | `@solid/community-server` 7.3.0 | `solid-server` 6.0.0 | Composer project |
| Runtime | Node.js 18+ | Node.js 18+ | PHP 8 + Composer |
| Pod model | Path-based or subdomain, fully configurable | Subdomain-first, accounts API | Path-based, vhost config |
| Access control | WAC and ACP (policy-based) | WAC | WAC |
| Auth | Solid-OIDC, email/password for local accounts | Solid-OIDC, WebID-TLS legacy | Solid-OIDC |
| Storage backends | File system, SPARQL, S3-compatible (via modules) | File system, external identity providers | File system |
| Docker | Dockerfile in repo | `docker-compose.yml` in repo | Dockerfile/community images |
| Ops difficulty | Medium — config files, many JSON-LD knobs | Low to medium — batteries included | Low — shared hosting friendly |

## Scenario Decision Matrix

| Use case | Recommended | Why |
|---|---|---|
| New pod host with modern auth and per-resource policies | Community Solid Server | ACP support plus a config system you can compose |
| Migrating existing pods from a legacy host | Node Solid Server | Same layout and account API, least data surgery |
| University lab prototyping Solid apps | Community Solid Server | Pods spin up in seconds with the file backend |
| Deploying on a €3/month shared host without Node | PHP Solid Server | Only PHP + Composer needed |
| Multi-tenant host with thousands of pods | Community Solid Server (subdomain config) | Path-based pods are simpler but leak cross-pod URLs |
| You need a SPARQL-backed pod for linked data | CSS with a SPARQL backend module | File backend cannot answer federated queries |
| Quick demo for a workshop | Node Solid Server | `npx solidserver` and you are done |

## Community Solid Server — the reference implementation that actually ships

CSS is what most Solid-related code is now written against. It is a Node application with a modular configuration layer: instead of one giant config file, you compose JSON-LD modules (`@css:config/file.json`, `@css:config/sparql-endpoint.json`, and so on) that declare which components handle storage, identity and authorization.

Install and run a file-backed pod server locally:

```bash
npm install -g @solid/community-server
community-solid-server -c @css:config/file.json -f ./data
# → Listening at http://localhost:3000/
```

The `-c` flag points at a configuration module and `-f` at the data directory. On first start CSS bootstraps a root pod and prints a setup URL — open it, create your WebID, and you have a working pod. For production you will replace the file backend and put the server behind a TLS-terminating proxy, because Solid identifiers are HTTPS URLs and every resource URL in your pod is absolute.

The reason I recommend CSS for new deployments is not the star count (610 against NSS's 1,796). It is the architecture: authorization is pluggable. You can run classic **WAC** (Web Access Control) ACL sidecar files, or **ACP** (Access Control Policy) where policies are expressed as resources you can query. If you ever need "share this folder with the marketing group until Friday", ACP is the model that survives contact with real requirements.

Its weak point is configuration depth. There are dozens of JSON-LD modules, and the error messages when a module combination is invalid are not friendly. Budget half a day for your first non-default deployment.

## Node Solid Server — the installed base, warts and all

NSS is the original implementation, historically associated with the Solid project's earliest pilots. At 1,796 stars it is still the most recognised name, and `solid-server` 6.0.0 is a real release line rather than an abandoned repository — but the commit cadence (last push 2026-08-08) tells you it is in maintenance mode relative to CSS.

The repository ships a compose file that is refreshingly plain:

```yaml
version: "3"
services:
  solid-server:
    build: .
    container_name: solid
    ports:
      - "8443:8443"
    entrypoint: npm run solid start -- --no-reject-unauthorized
    environment:
      - NODE_TLS_REJECT_UNAUTHORIZED=0
```

That `--no-reject-unauthorized` flag exists because NSS generates a self-signed certificate by default — fine for a laptop, unacceptable in production. In a real deployment you terminate TLS at nginx or Caddy, point NSS at the certificate paths, and delete that flag. Leaving it in is the single most common NSS misconfiguration I see, and it silently disables certificate validation for outgoing requests.

For a quick local test, skip Docker entirely:

```bash
npx solidserver --port 8443 --no-tls --root ./data
```

Where NSS still wins is migration compatibility. If you have pods created by an older NSS instance, the directory layout and account structures match, so moving them to CSS requires rewriting identifiers. For a hobby pod, that is a weekend. For 200 users, it is a project — which is exactly why NSS remains deployed.

## PHP Solid Server — the odd one out that solves a real problem

pdsinterop's PHP Solid Server (50 stars, actively committed through 2026-10-16) implements a Solid server in PHP. That sounds like a downgrade until you remember that a huge share of the world's cheap hosting runs PHP and nothing else. No Node runtime means no `npm ci`, no supervisor config, no memory leaks in a long-lived process.

```bash
git clone https://github.com/pdsinterop/php-solid-server.git
cd php-solid-server
composer install
cp config/config-example.php config/config.php
# point your vhost document root at ./public and set the base URL in config.php
```

The trade-offs are real: WAC only (no ACP), a file-system backend only, and a small maintainer pool. But for a personal pod on infrastructure you already pay for, it is the least-friction path, and the project keeps pace with the specification better than its star count suggests.

## Pitfalls That Break Pods in Production

**1. Absolute URLs everywhere.** Every resource in a pod has a canonical HTTPS URL that includes your hostname. Move from `http://localhost:3000` to `https://pods.example.org` and every stored reference is stale. Decide the final hostname *before* the first write — do not "just test locally first" and migrate later.

**2. Subdomain vs path pods.** Path-based pods (`/alice/profile/card`) are trivial; subdomain pods (`alice.pods.example.org`) give real isolation but require wildcard DNS and a wildcard TLS certificate. CSS supports both; NSS assumes subdomains. Retrofitting wildcard certificates onto an existing deployment is a certified afternoon-killer.

**3. TLS certificate validation.** Both Node implementations will happily start with self-signed certs and then fail to fetch remote WebIDs. If federation does not work, check certificate validation before you debug Solid-OIDC.

**4. WebID profile is the account.** There is no users table you can edit on a whim. Your identity is a document at `/profile/card#me`. Break the `solid:oidcIssuer` triple and login stops working with no useful error. Back up that file, and treat it as configuration rather than content.

**5. Content types matter.** Solid is RDF-first: `text/turtle` is the native serialisation. Uploading JSON and expecting it to be queryable will disappoint you. Decide early whether your data is RDF (pod-native) or opaque binary blobs (a file store with extra steps).

**6. Quota and disk.** Neither CSS nor NSS ships a friendly quota system out of the box. Pods grow; photos and videos grow faster. Put the data directory on a volume with monitoring, and cap upload sizes at the reverse proxy — a pod server is an open write endpoint by design.

**7. Backups are just directories.** The file backend means `rsync` works. Do not over-engineer it: stop the container, sync the directory, restart. A pod store is far easier to back up than a database-backed platform, which is one of the underrated arguments for Solid in the first place.

## FAQ

**Is Solid the same thing as the Fediverse?**
No. ActivityPub-based platforms (Mastodon, Lemmy) federate *messages* between servers. Solid federates *data ownership*: applications read and write resources in a pod under the owner's access rules. A pod can hold your data while the app you use lives somewhere else entirely.

**Can I use Solid pods as ordinary cloud storage?**
You can, but it is a poor fit unless you care about linked data. Content negotiation, RDF-first semantics and WebID-based authorization add overhead that a plain WebDAV store does not have. If you want a Dropbox replacement, our [Cloudreve vs Pydio Cells vs Seafile comparison](../cloudreve-vs-pydio-cells-vs-seafile-self-hosted-cloud-storage/) is the right article.

**Which server should I pick if I only need one user?**
Community Solid Server with the file backend. One command, no compose file, and you get the implementation that receives specification updates first. Add NSS only if a tool you depend on assumes its account API.

**Does Solid-OIDC replace my existing identity provider?**
No — it federates with it. Your pod trusts an OIDC issuer, and the issuer vouches for the WebID. Teams already running Keycloak or Zitadel usually keep it and add a Solid-OIDC bridge; see our [Zitadel vs Ory vs Keycloak comparison](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) for the issuer side, and the [passkey and WebAuthn guide](../self-hosted-passkey-webauthn-authentication-solutions-2026/) if you want phishing-resistant login in front of it.

**How many pods can one server handle?**
A file-backed CSS instance handles hundreds of small pods comfortably on 2 vCPU / 4 GB. The bottleneck is usually the number of open files and inode count, not CPU. For thousands of pods, plan on subdomain routing, an S3-compatible backend, and rate limiting at the edge.

**Is any of this production-ready, really?**
For personal and research use, yes — all three run. For regulated workloads, be honest that Solid's ecosystem is younger than its ideas: the specification is stable, the implementations are good, but operational tooling (monitoring dashboards, quota management, migration utilities) is thin compared with mainstream object storage.

## Where this leaves you in 2026

Solid's promise — applications that ask permission instead of assuming ownership — is the most interesting thing happening to personal data since self-hosted cloud storage. The pragmatic path is a **CSS** pod today, a WebID you control, and one application (a notes app or a photo viewer) reading from it. That small experiment teaches you more about the trade-offs than any specification document, and it costs one `npm install`.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Community Solid Server vs Node Solid Server vs PHP Solid Server: Self-Hosted Solid Pods in 2026",
  "description": "Hands-on comparison of the three self-hosted Solid pod servers: Community Solid Server, Node Solid Server and PHP Solid Server, with real deployment commands and production pitfalls.",
  "datePublished": "2026-11-08",
  "dateModified": "2026-11-08",
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
