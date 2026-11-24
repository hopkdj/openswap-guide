---
title: "OpenBao vs HashiCorp Vault vs Infisical in 2026: What Changes After the License Switch"
date: "2026-11-24"
tags: ["secrets-management", "self-hosted", "openbao", "vault", "infisical", "security"]
draft: false
cover: "/img/screenshots/openbao-pki-rotate-dashboard.jpg"
description: "A hands-on comparison of OpenBao, HashiCorp Vault and Infisical in 2026 — licensing, API compatibility, storage backends, HA and a real migration path off BUSL Vault."
---

Your secrets manager is the one service in your stack that must never lose data and must never be replaced in a hurry. That is exactly why HashiCorp's 2023 move of Vault from MPL 2.0 to the Business Source License (BUSL 1.1) caused so much disruption: teams that had built years of automation against the Vault HTTP API suddenly had a licensing question attached to every new deployment, every consultant, and every embedded copy of the binary they shipped inside their own products.

Two years later the dust has settled into three credible answers: **stay on Vault**, **switch to OpenBao** (the community fork, now a Linux Foundation project), or **re-platform onto Infisical** (developer-first, 30k+ stars, its own API and CLI). Each choice has a different migration cost, and the marketing pages will not tell you which one you should pick. This guide does.

## TL;DR — the 30-second verdict

- **You already run Vault, you have no Enterprise contract, and the BUSL is a problem for your product:** migrate to **OpenBao**. It is a drop-in fork of the Vault 1.14 codebase, keeps the same API and the same HCL configuration, and runs the same unseal flow. Most teams migrate by restoring a raft snapshot.
- **You need vendor support, HCP Vault, or Enterprise features like namespaces, MFA-backed SSO and Sentinel policies today:** stay on **HashiCorp Vault**. The support contract is the product.
- **You want secrets consumed by application developers and CI pipelines, not by infrastructure engineers:** use **Infisical**. It ships SDKs, a CLI, a Kubernetes operator and native secret sync to 30+ platforms, and it is the fastest of the three to get a team using on day one.

If you only have five minutes: **OpenBao if you are migrating, Vault if you are buying a contract, Infisical if you are onboarding humans.**

## Feature and project comparison

All figures below were pulled from GitHub on 2026-11-24.

| Dimension | OpenBao | HashiCorp Vault | Infisical |
|---|---|---|---|
| License | MPL 2.0 | BUSL 1.1 (source-available) | MIT (core) |
| GitHub stars | 9,172 | 36,554 | 30,719 |
| Last push | 2026-11-24 | 2026-11-23 | 2026-11-24 |
| API compatibility | Vault 1.14-compatible HTTP API | Native Vault API | Own REST API, not Vault-compatible |
| Config format | HCL, same blocks as Vault | HCL | Environment variables + `.env` |
| Storage backends | Raft, file, PostgreSQL, MySQL, S3, Consul | Raft, file, PostgreSQL, MySQL, S3, Consul, Enterprise backends | PostgreSQL (required) |
| HA model | Raft quorum, active/standby | Raft quorum, active/standby | Stateless containers + Postgres + Redis |
| Auto-unseal | Transit, cloud KMS (AWS/GCP/Azure) | Transit, cloud KMS, HSM | No unseal concept — key from env |
| Dynamic secrets | Yes (databases, PKI, SSH, cloud IAM) | Yes (largest plugin catalog) | Limited (static + some dynamic) |
| Secret sync to third parties | Manual / custom | Enterprise-only for many targets | Built-in, 30+ integrations |
| Kubernetes integration | Vault Agent Injector (compatible) | Vault Agent Injector, VSO | Infisical Operator + CSI driver |
| Governance | Linux Foundation | HashiCorp / IBM | Infisical Inc. |
| Best fit | Vault users escaping BUSL | Enterprises buying support | App teams wanting fast secret delivery |

## Decision matrix: pick by situation, not by feature count

| Your situation | Recommended tool | Why |
|---|---|---|
| Running Vault OSS 1.13/1.14, shipping a commercial product | OpenBao | Same API, MPL 2.0, migration via raft snapshot |
| Regulated industry needing a support SLA and HSM | HashiCorp Vault | Enterprise support, HSM-backed auto-unseal, audit guarantees |
| 20+ microservices, developers complain about secret access | Infisical | CLI/SDKs, per-environment scoping, self-serve onboarding |
| Need dynamic database credentials with short TTLs | Vault or OpenBao | Both implement the database secrets engine properly |
| Kubernetes-only, GitOps-driven secret delivery | Infisical or Vault + VSO | Operator/CSI integrations are first-class in both |
| Air-gapped datacenter, no external KMS | OpenBao or Vault with Shamir unseal | Both support Shamir; plan your unseal ceremony |
| Migrating off cloud secret managers (AWS/GCP) | Infisical | Importers and sync make cloud-to-self-hosted migration mechanical |

## OpenBao: the fork that kept the API

OpenBao's pitch is not "better than Vault" — it is "the same Vault, without the license question." The 9,172-star project forked from Vault 1.14 and has since shipped its own release cadence, including a rebuilt web UI, a reworked PKI engine, and its own plugin registry. Because the HTTP API is wire-compatible, your existing Terraform provider, your `vault kv get` scripts, and your Agent Injector annotations mostly keep working.

The configuration surface is deliberately identical. The official documentation still documents `storage "raft"`, `listener "tcp"` and the standard top-level addresses:

```hcl
# /etc/openbao/config.hcl — mirrors the Vault HCL layout
cluster_addr = "https://127.0.0.1:8201"
api_addr     = "https://127.0.0.1:8200"
ui           = true
disable_mlock = false

storage "raft" {
  path    = "/openbao/data"
  node_id = "bao-1"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/openbao/tls/bao.crt"
  tls_key_file  = "/openbao/tls/bao.key"
}

seal "transit" {
  address         = "https://openbao-vault.internal:8200"
  token           = "env://BAO_TRANSIT_TOKEN"
  disable_renewal = "false"
  key_name        = "autounseal"
  mount_path      = "transit/"
}
```

A single-node container for a lab, using the official image:

```bash
docker run -d --name openbao \
  --cap-add=IPC_LOCK \
  -p 8200:8200 \
  -v /srv/openbao:/openbao/data \
  -e BAO_ADDR=http://0.0.0.0:8200 \
  openbao/openbao:latest server -config=/openbao/config.hcl
```

In practice, the migration from Vault OSS looks like this:

```bash
# On the Vault node — take a raft snapshot
vault operator raft snapshot save /backup/vault-2026.snap

# On the OpenBao node — restore the same snapshot, then unseal with the SAME keys
bao operator raft snapshot restore /backup/vault-2026.snap
bao operator unseal   # repeat with your existing Shamir shares
bao secrets list      # confirm every engine and path survived
```

Two things to watch. First, **plugin binaries must be rebuilt** against OpenBao's SDK; external plugins compiled against `hashicorp/vault/sdk` will not load cleanly, and the failure message is unhelpful. Second, **namespaces are an Enterprise feature in Vault** — if you relied on them, verify how the current OpenBao release exposes multi-tenancy before you promise it to anyone.

![OpenBao web UI rotating a PKI root certificate](/img/screenshots/openbao-pki-rotate-dashboard.jpg "OpenBao UI: PKI root certificate rotation, an operation that requires careful planning in any secrets platform")

For certificate workloads on top of either project, our [SSH certificate authority comparison](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/) covers how step-ca, Teleport and Vault divide the work.

## HashiCorp Vault: still the reference implementation

Vault remains the reference implementation at 36,554 stars: the plugin ecosystem is the widest, the documentation is the deepest, and every third-party integration you can name assumes Vault's API. Its dynamic secrets engines — short-lived database credentials, cloud IAM keys, PKI certificates with TTLs — are still the most complete implementation in the space, and the audit device story is what auditors expect to see.

The trade-off is licensing plus operational weight. BUSL 1.1 means you may not offer Vault as a hosted service, and the license auto-converts to MPL 2.0 four years after each release. For internal use it is fine; for a product you ship to customers, legal review eats weeks.

Local bring-up is a single command, which is why so many tutorials still use it:

```bash
docker run --rm --cap-add=IPC_LOCK \
  -e VAULT_DEV_ROOT_TOKEN_ID=root \
  -p 8200:8200 hashicorp/vault:1.21 server -dev
```

Then the parts people actually forget to automate:

```bash
export VAULT_ADDR=http://127.0.0.1:8200
vault status
vault secrets enable -path=kv kv-v2
vault kv put kv/payments/stripe api_key=sk_live_xxx webhook_secret=whsec_xxx
vault policy write payments-ro - <<'EOF'
path "kv/data/payments/*" { capabilities = ["read"] }
EOF
```

Vault wins when the cost of the license is smaller than the cost of a secrets incident. If you are already on an Enterprise contract with HSM-backed auto-unseal, switching to OpenBao saves license money and costs you your support channel — often a bad trade in regulated environments.

## Infisical: built for application teams, not infrastructure teams

Infisical approaches the problem from the other end. Instead of asking developers to learn a policy language and a CLI with 40 subcommands, it gives them a project with environments (`dev`, `staging`, `prod`), folder-scoped secrets, and a one-line injector. It is MIT-licensed, 30,719 stars, and it is the only one of the three that treats "sync this secret into Vercel/AWS/GitHub Actions/Render" as a first-class feature rather than an Enterprise add-on.

Its official production compose file is genuinely small — Postgres, Redis, one backend container:

```yaml
version: "3"

services:
  backend:
    container_name: infisical-backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    image: infisical/infisical:latest   # pin this to a specific tag
    pull_policy: always
    env_file: .env
    ports:
      - 80:8080
    environment:
      - NODE_ENV=production
    networks:
      - infisical

  redis:
    image: redis
    container_name: infisical-dev-redis
    env_file: .env
    restart: always
    environment:
      - ALLOW_EMPTY_PASSWORD=yes
    networks:
      - infisical
    volumes:
      - redis_data:/data

  db:
    container_name: infisical-db
    image: postgres:14-alpine
    restart: always
    env_file: .env
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - infisical
    healthcheck:
      test: "pg_isready --username=${POSTGRES_USER} && psql --username=${POSTGRES_USER} --list"
      interval: 5s
      timeout: 10s
      retries: 10

volumes:
  pg_data:
    driver: local
  redis_data:
    driver: local

networks:
  infisical:
```

Before starting it you must generate the two key material variables the container refuses to boot without — `ENCRYPTION_KEY` (hex, 16 bytes) and `AUTH_SECRET`:

```bash
echo "ENCRYPTION_KEY=$(openssl rand -hex 16)" >> .env
echo "AUTH_SECRET=$(openssl rand -base64 32)" >> .env
docker compose -f docker-compose.prod.yml up -d
```

Where Infisical really pulls ahead is the developer loop. Installing the CLI and running a service with injected secrets takes one line, and nothing is written to disk:

```bash
npm install -g @infisical/cli
infisical login
infisical run --env=prod --path=/payments -- npm start
```

The honest limitation: Infisical is **not** a drop-in replacement for Vault. Its dynamic secrets support is narrower than Vault's database engine, there is no HSM-backed unseal, and you cannot reuse a single HCL file to describe storage, seal and listeners. If you need short-lived database credentials issued per connection by the secrets platform itself, Vault or OpenBao does that better today.

## Migration pitfalls worth an afternoon of reading

**1. Raft snapshots are version-sensitive in one direction.** Vault snapshot → OpenBao restore generally works when the snapshot comes from Vault 1.14.x. Snapshots from newer Vault releases contain data-model changes OpenBao may not understand. Freeze Vault upgrades before you migrate, and rehearse the restore on a throwaway cluster.

**2. Unseal keys are the migration.** Whatever you do, do not re-initialize the target cluster "to be safe." Re-initializing generates new Shamir shares, and the old snapshot becomes unreadable. Back up `core/unseal-keys` out-of-band and test the ceremony with two people present.

**3. Plugin ABI drift breaks silently.** External secret engines compiled for Vault will not load on OpenBao. Inventory every non-builtin plugin (`bao secrets list -detailed`) before cutover; each one needs a rebuild against the fork's SDK.

**4. Auto-unseal configuration does not transfer automatically.** A Vault cluster sealed with an AWS KMS key needs the equivalent seal stanza plus IAM permissions on the new cluster. Transit-based auto-unseal is easier because the transit secrets engine lives on the old cluster, which you then must keep alive — a bootstrapping dependency people discover during an outage.

**5. Infisical's encryption key is not rotatable without re-encrypting.** Treat `ENCRYPTION_KEY` as permanent and store it in a separate system from the secrets it protects. Losing it means every secret in the database is unrecoverable.

**6. Audit devices are not portable.** Vault and Infisical both support audit logging, but the schemas differ. If compliance requires a continuous audit trail across the migration, run both systems in parallel and mirror to your SIEM for the overlap window.

If your secrets ultimately land in Git or on disk as encrypted blobs, our [SOPS vs git-crypt vs age guide](../2026-04-23-mozilla-sops-vs-git-crypt-vs-age-self-hosted-secrets-encryption-git-guide-2026/) explains where file-level encryption stops being enough. And if you are weighing rotation workflows specifically, the [Vault vs Infisical vs Passbolt rotation comparison](../2026-04-25-vault-vs-infisical-vs-passbolt-self-hosted-secrets-rotation-guide-2026/) goes deeper on that one axis.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenBao vs HashiCorp Vault vs Infisical in 2026: What Changes After the License Switch",
  "description": "A hands-on comparison of OpenBao, HashiCorp Vault and Infisical in 2026 — licensing, API compatibility, storage backends, HA and a real migration path off BUSL Vault.",
  "datePublished": "2026-11-24",
  "dateModified": "2026-11-24",
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

**Is OpenBao a drop-in replacement for HashiCorp Vault?**
For the HTTP API and HCL configuration, largely yes: OpenBao forked from Vault 1.14 and kept the same endpoints, CLI verbs and config blocks. It is not a drop-in replacement for Enterprise features (namespaces, Sentinel, HSM auto-unseal) or for third-party plugins compiled against HashiCorp's SDK. Rebuild plugins and audit any Enterprise-only surface before cutting over.

**Can I migrate from Vault to OpenBao without downtime?**
Not without downtime, but with a short, rehearsed window. Take a raft snapshot on the Vault leader, stop Vault, restore the snapshot into an OpenBao cluster of the same size, unseal with the existing Shamir shares, and point clients at the new address. Realistically plan 30–90 minutes plus a rollback path, and rehearse on a copy of production first.

**Which is more secure: Vault, OpenBao or Infisical?**
They target different threat models. Vault and OpenBao give you dynamic, short-lived credentials, audit devices and auto-unseal backed by a KMS or HSM. Infisical focuses on encrypted secret delivery to applications and CI, with a single encryption key in the environment. For dynamic database credentials and formal audit requirements, Vault or OpenBao is the stronger choice; for fast, low-friction secret distribution to many services, Infisical is usually good enough.

**Does Infisical work with Kubernetes and CI pipelines?**
Yes. Infisical ships a Kubernetes Operator, a CSI driver, a CLI usable in any CI step, and native sync integrations to GitHub Actions, GitLab, Vercel, AWS and others. The typical pattern is `infisical run --env=prod -- <command>` in CI and the operator or CSI driver for pods.

**What happens to Vault's license if I self-host it internally?**
BUSL 1.1 permits internal production use; it restricts offering Vault as a hosted or embedded service to third parties, and each release converts to MPL 2.0 four years after publication. Internal-only deployments are usually fine, but if you redistribute Vault inside a product you sell, have legal review the license before you ship.

**Which project has the healthier long-term outlook?**
Vault has commercial backing and the largest ecosystem; OpenBao has neutral Linux Foundation governance and a growing contributor base with 9k+ stars; Infisical is venture-backed with rapid release cadence. For a ten-year secrets platform decision, governance matters as much as features — OpenBao is the only one of the three you cannot be license-restricted out of.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
