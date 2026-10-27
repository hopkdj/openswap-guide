---
title: "RustFS vs VaultS3 vs Alarik in 2026: Three MinIO Alternatives That Fit in 200 MB of RAM"
date: "2026-10-28"
tags: ["object-storage", "s3", "self-hosted", "minio", "infrastructure"]
draft: false
cover: "/img/screenshots/vaults3-dashboard.jpg"
---

# RustFS vs VaultS3 vs Alarik in 2026: Three MinIO Alternatives That Fit in 200 MB of RAM

MinIO spent years as the default answer to "I need S3 on my own hardware." Then its console and administrative capabilities started moving behind a commercial tier, and a lot of people who had built backup pipelines on the community edition discovered they were now renting back something they thought they owned. That is not a licensing debate — it is an operational risk that showed up in production for anyone running MinIO as the storage layer under Restic, Velero or Loki.

Three replacements have emerged with real traction in 2026: **RustFS** (35,459 stars, Apache-2.0), **VaultS3** (1,642 stars, AGPL-3.0) and **Alarik** (573 stars, Apache-2.0). Their memory footprints are **17 MB to ~185 MiB** against MinIO's multi-hundred-MB baseline, and each makes a different bet about what an object store should be.

## TL;DR — The 30-Second Verdict

- **You want the safest drop-in with the biggest community and a migration path from MinIO:** pick **RustFS**. 35K stars, Helm chart, site replication, a full web console, and an explicit MinIO/Ceph coexistence story.
- **You want a single binary that idles at 17 MB and never needs a control plane:** pick **VaultS3**. Two volumes, one container, 80+ S3 operations, a built-in dashboard, encryption at rest.
- **You want distributed, multi-node with replication targets and benchmarking against MinIO:** pick **Alarik**. Written in Swift, designed from day one as a distributed system with a separate console.
- **You store under 1 TB and back up one laptop:** none of these. `restic` to a cheap VPS with `rclone` is cheaper than the electricity.

## Comparison Table (stats pulled 2026-10-28)

| Dimension | RustFS | VaultS3 | Alarik |
|---|---|---|---|
| GitHub stars | 35,459 | 1,642 | 573 |
| Licence | Apache-2.0 | AGPL-3.0 | Apache-2.0 |
| Language | Rust | Go | Swift |
| Last push | 2026-10-27 | 2026-10-27 | 2026-09-19 |
| Idle memory | Higher than VaultS3 (full console) | ~17 MB | Container + console baseline |
| Peak memory | Scales with concurrency | ~185 MiB writing 64 MiB objects at c=16 | Not published |
| Deployment model | Single node or distributed, Helm chart | Single binary / one container | Distributed API + separate console |
| S3 API coverage | Broad, with console + SSO | 80+ operations, dashboard | S3-compatible core, replication |
| Admin UI | Full console on port 9001 | Built-in dashboard on 9000 | Separate Nuxt console on 3000 |
| Auth beyond keys | OIDC / SSO | Access key + secret | OIDC SSO (admin-managed providers) |
| MinIO migration story | Explicit coexistence + migration | Manual (`mc mirror`) | Replication targets |
| Best fit | Production clusters | Edge, homelab, small prod | Multi-node with replication |

## Decision Matrix

| Your situation | Pick | Reason |
|---|---|---|
| Kubernetes with persistent object storage | **RustFS** | Official Helm chart at charts.rustfs.com |
| One box, 2 TB of backups, no ops team | **VaultS3** | One container, `/data` + `/metadata`, done |
| Three nodes, need cross-site copies | **Alarik** | Replication targets are a core primitive |
| You need SSO for bucket access | **RustFS** or **Alarik** | Both support OIDC; VaultS3 does not |
| You are migrating 40 TB off MinIO | **RustFS** | Coexistence and migration tooling are documented |
| You run on ARM SBCs | **VaultS3** | Single Go binary, 17 MB idle |

## RustFS — The One That Won the Star Count

![RustFS web console bucket listing](/img/screenshots/rustfs-console.jpg "RustFS console bucket list")

35,459 stars is not a hobby project. RustFS is a Rust implementation of an S3-compatible object store with explicit support for **migration and coexistence with MinIO and Ceph** — which is exactly what you need when you cannot cut over in one weekend.

```bash
# one-click install script
curl -O https://rustfs.com/install_rustfs.sh && bash install_rustfs.sh

# or Docker, S3 API on 9000, console on 9001
docker run -d -p 9000:9000 -p 9001:9001 \
  -v $(pwd)/data:/data -v $(pwd)/logs:/logs \
  rustfs/rustfs:1.0.4

# Podman users (SELinux labels included)
podman run -d -p 9000:9000 -p 9001:9001 \
  -v $(pwd)/data:/data:Z,U -v $(pwd)/logs:/logs:Z,U \
  rustfs/rustfs:latest

# Kubernetes
# follow the Helm chart README at charts.rustfs.com
```

Two port conventions to internalise: **9000 is the S3 API, 9001 is the console**. Clients that worked against MinIO on 9000 need no change; humans need to be told about 9001 or they will report the console as broken.

The console is the differentiator among these three. It is a real management UI — buckets, policies, replication status, user management — not a thin file browser. If your team includes people who do not live in `mc`, that matters more than raw throughput.

**Where it breaks:** it is the heaviest of the three at idle, because a full console costs memory. On a 1 GB VPS you will notice. It also moves fast, so pin a tag (`rustfs/rustfs:1.0.4`) rather than chasing `latest` on a storage tier.

## VaultS3 — 17 MB and a Refusal to Grow

![VaultS3 dashboard showing buckets](/img/screenshots/vaults3-dashboard.jpg "VaultS3 bucket dashboard")

VaultS3's README opens with the author explaining why it exists: running MinIO, watching the pieces he depended on move behind a paid tier, and deciding not to rent back what he already had. The result is deliberately small — a single Go binary, **~17 MB idle**, peaking around **185 MiB** while writing 64 MiB objects at concurrency 16.

```bash
docker run -p 9000:9000 \
  -e VAULTS3_ACCESS_KEY=myadmin \
  -e VAULTS3_SECRET_KEY=mysupersecret \
  -v vaults3-data:/data -v vaults3-meta:/metadata \
  eniz1806/vaults3
```

The critical operational detail is the **two-volume split**. `/data` holds objects; `/metadata` holds the index. Keep them on separate volumes — and ideally separate disks — because they have different failure profiles and different resize needs. Snapshot both, restore both, or you restore a bucket list pointing at objects that no longer exist.

Default buckets can be seeded declaratively, which is genuinely useful for reproducible deployments:

```bash
docker run -p 9000:9000 \
  -e VAULTS3_DEFAULT_BUCKETS=app-data,backups \
  -v ./data:/data -v ./metadata:/metadata \
  eniz1806/vaults3
```

Or in `vaults3.yaml`:

```yaml
storage:
  default_buckets: ["app-data", "backups"]
```

**Where it breaks:** there is no SSO, no distributed mode, no erasure coding. It is one binary on one host, and that is the whole design. Encryption at rest is built in, but do not mistake it for replication — if the host dies, the bucket dies with it. Pair it with snapshots or an offsite `rclone sync`.

## Alarik — Swift, Distributed, and Honest About Benchmarks

Alarik is written in **Swift 6.2+**, which is unusual enough to be a maintenance question you should ask before adopting it. It is also the only one of the three that ships **benchmark screenshots against MinIO inside the repository** rather than a marketing claim.

The deployment is two containers by design: the API and a separate Nuxt console.

```yaml
services:
  alarik:
    image: ghcr.io/achtungsoftware/alarik:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - API_BASE_URL=http://localhost:8080
      - CONSOLE_BASE_URL=http://localhost:3000
      - ADMIN_USERNAME=alarik
      - ADMIN_PASSWORD=alarik
      - JWT=YOUR_SECURE_JWT_KEY
      - ALLOW_ACCOUNT_CREATION=false
    volumes:
      - alarik-storage:/app/Storage

  console:
    image: ghcr.io/achtungsoftware/alarik-console:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NUXT_PUBLIC_API_BASE_URL=http://localhost:8080
      - NUXT_PUBLIC_CONSOLE_BASE_URL=http://localhost:3000
      - NUXT_PUBLIC_ALLOW_ACCOUNT_CREATION=false
    depends_on:
      - alarik

volumes:
  alarik-storage:
```

Three environment variables decide whether this is safe in production:

- **`JWT` is mandatory in production.** A node started with `--env production` and no `JWT` refuses to boot rather than falling back to the default key that sits in a public repository. Generate one with `openssl rand -base64 48`, and use the same value on every node — a session issued by one node must verify on the next.
- **`ALARIK_REGION` defaults to `us-east-1`** and must match what clients sign for. A request signed for a different region gets `400 AuthorizationHeaderMalformed`, exactly like real S3. This is the number-one cause of "my client works against MinIO but not here."
- **`ALARIK_FSYNC=true` by default.** Turning it off buys throughput and silently trades durability: writes stay atomic, but an acknowledged upload can be lost in a power failure. Leave it on for anything you would cry about.

**Where it breaks:** fewest stars, youngest project, and a Swift toolchain requirement if you ever need to build rather than pull. The console is a second service to monitor. OIDC providers are admin-managed in the console rather than set by environment variable — good for security, annoying for GitOps.

## Pitfalls Before You Migrate Off MinIO

- **Test `mc mirror` in both directions first.** Every one of these implements the S3 API, not every S3 extension. Lifecycle rules, object locking and bucket notifications are where compatibility quietly stops.
- **Do not put `/data` and `/metadata` on the same disk.** VaultS3 documents it, and the same logic applies to any metadata-heavy store: one full disk should not corrupt both layers at once.
- **Pin image tags and record the digest.** These are young projects shipping fast. `latest` on a storage backend is how you discover a regression during a restore.
- **Signature region mismatches look like auth failures.** If `aws s3 ls` returns 403 against a working cluster, check the region and clock skew before you touch credentials.
- **Plan the backup of the object store itself.** Bucket replication is not a backup; it replicates deletions too. Our [Garage vs SeaweedFS vs Ceph RGW comparison](../2026-05-14-self-hosted-s3-object-storage-garage-vs-seaweedfs-vs-ceph-rgw-guide/) covers the mature incumbents if you want a second opinion on replication topology.

## Why Self-Host Object Storage At All?

Because the API is a commodity and your data is not. S3 compatibility means the client library you already use — Restic, Velero, Loki, Paperclip, a hundred others — works unchanged against a box in your rack. The migration cost is a configuration flag, not a rewrite. That is the entire argument for self-hosting object storage, and it is a good one.

The second argument is cost shape. Cloud object storage charges for requests and egress; a self-hosted store charges for the disk you already bought. For a workload that reads the same 200 GB of media every day, the egress line alone usually settles the decision.

The third argument is the one that made this article possible: **post-2025 licensing risk**. When a project you depend on re-scopes its community edition, your options are to pay, to stay on a frozen version, or to move. Keeping your data behind a plain S3 API means the third option stays cheap. That is portable infrastructure, and it is worth an afternoon of migration testing.

The counter-argument is real too. You now own durability: backups, scrubbing, disk replacement, and the monitoring that tells you a drive is dying before a bucket is unreadable. If nobody on the team wants that job, managed storage is the honest answer. If you do want it, our [cold storage comparison](../2026-05-10-self-hosted-cold-storage-solutions-minio-ceph-seaweedfs-guide/) is where to plan the tiering, and our [binary repository comparison](../2026-04-28-artifactory-oss-vs-nexus-vs-pulp-self-hosted-binary-repository-guide/) covers the neighbouring problem of artefact storage.

## FAQ

### Is RustFS a drop-in replacement for MinIO?

For the S3 API, largely yes — clients pointed at port 9000 keep working, and the project documents coexistence and migration from MinIO and Ceph. What changes is the console: RustFS serves its own UI on port 9001, so any runbook that says "open the MinIO console" needs updating.

### How much RAM does VaultS3 actually need?

Around 17 MB idle, and roughly 185 MiB while writing 64 MiB objects at concurrency 16, measured by the project in August 2026 with `docker stats`. Budget 512 MB for the host and you have headroom; the number that matters is peak, not idle.

### Does Alarik work without the console container?

Yes for the S3 API — the console is a separate Nuxt service on port 3000. You can run the API alone on 8080 and manage buckets with `aws s3`, `mc`, or `rclone`. You lose OIDC provider management and the web UI, not the storage.

### Can I run any of these in a cluster?

RustFS supports distributed deployments and ships a Helm chart for Kubernetes. Alarik is designed as a distributed system with replication targets between instances. VaultS3 is explicitly single-node — if you need multi-node durability, it is the wrong tool.

### Which one should replace MinIO on a 2 TB homelab box?

VaultS3. One container, two volumes, 17 MB of RAM, a dashboard, and no control plane to babysit. Move to RustFS when you need SSO, a fuller console, or Kubernetes-native deployment; move to Alarik when you need cross-site replication and can take on a younger codebase.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "RustFS vs VaultS3 vs Alarik in 2026: Three MinIO Alternatives That Fit in 200 MB of RAM",
  "description": "Comparison of RustFS, VaultS3 and Alarik as self-hosted S3-compatible object storage: memory footprint, deployment, replication, SSO and real install commands.",
  "datePublished": "2026-10-28",
  "dateModified": "2026-10-28",
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
