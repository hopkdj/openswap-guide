---
title: "MySQL 9.7 LTS vs 26.10 Innovation in 2026: Pick the Wrong Track and You Patch Every 3 Months"
date: "2026-11-28"
tags: ["mysql", "database", "upgrade", "self-hosted", "migration"]
draft: false
---

MySQL 8.0 stopped receiving patches on **30 April 2026**. That is seven months ago. If your runbook still starts with "we're on MySQL 8.0.x, it's the LTS, we're fine," then you are maintaining an unsupported database — and worse, the version numbers have moved in a way that makes it very easy to accidentally land on a release that expires in **three months**.

Because MySQL now ships on two tracks with radically different lifetimes, and the numbering scheme changed underneath everyone. The 9.x innovation line produced a new LTS at **9.7** in April 2026. Then the project jumped straight to **26.7** and **26.10** — numbers that look like a completely different product and behave like three-month mayflies.

This guide is about choosing the right track, not about features. Feature lists are in the release notes and they will not save you from a database that falls out of support before your next patch window.

## TL;DR: The Quick Verdict

**Production databases go on MySQL 9.7 LTS. Full stop.** It is the current long-term-support release: released **21 April 2026**, premier support until **30 April 2031**, end of life **30 April 2034**, and already at patch **9.7.4**. That is a decade of runway for a version released this year.

**Never run a 26.x innovation release in production** unless you have accepted a patch treadmill where each release is superseded in roughly one quarter — 26.7 was obsoleted on **20 October 2026**, the same day 26.10 shipped. **If you are on 8.4 LTS, you have until 2029** for premier support; you do not need to rush, but you do need a plan, because 9.7 is where the innovation work has moved.

## MySQL release and support status, November 2026

| Release | Track | Released | Latest patch | Support ends | Verdict for production |
|---|---|---|---|---|---|
| **26.10** | Innovation | 2026-10-20 | 26.10.0 | Superseded by next innovation (~2027-01) | Dev and CI only. Never OLTP |
| 26.7 | Innovation | 2026-07-28 | 26.7.1 | **2026-10-20 (EOL)** | Already expired |
| **9.7** | **LTS** | 2026-04-21 | 9.7.4 | **2034-04-30** (premier 2031-04-30) | **Target this.** |
| 9.6 | Innovation | 2026-01-20 | 9.6.1 | 2026-04-21 (EOL) | Expired |
| **8.4** | **LTS** | 2024-04-30 | 8.4.13 | 2032-04-30 (premier 2029-04-30) | Fine until 2029. Plan the move |
| 8.0 | LTS | 2018-04-19 | 8.0.46 | **2026-04-30 (EOL)** | Unsupported. Migrate now |
| 5.7 | LTS | 2015-10-21 | 5.7.44 | 2023-10-31 | Dead for three years |

The repository is active — **12,534 stars**, last push **26 November 2026** — and it carries the maintainers' own branch layout: `8.0`, `8.4`, `9.7`, and `trunk`. Those branch names are the real statement of intent. Only three of them matter, and `9.7` is the newest one marked long-term.

### What the version numbers actually mean now

You can read the intent straight out of the source tree. The `MYSQL_VERSION` file on each branch is explicit:

```text
# branch 9.7
MYSQL_VERSION_MAJOR=9
MYSQL_VERSION_MINOR=7
MYSQL_VERSION_PATCH=4
MYSQL_VERSION_MATURITY="LTS"

# branch trunk
MYSQL_VERSION_MAJOR=26
MYSQL_VERSION_MINOR=10
MYSQL_VERSION_PATCH=0
MYSQL_VERSION_MATURITY="INNOVATION"
MYSQL_PREVIOUS_LTS_VERSION=9.7.0
```

Two things follow. First, **9.7 is the LTS baseline** — `trunk` itself declares `PREVIOUS_LTS_VERSION=9.7.0`, so everything being developed now is developed against 9.7 as the stable reference. Second, the jump from `9.7` to `26.10` is calendar versioning: 26.7 shipped in **July 2026**, 26.10 shipped in **October 2026**. Year and month. That is why there is no MySQL 10, 11, or 12 — the innovation line stopped counting and started dating itself.

The practical consequence is the whole point of this article: **a version number that looks "higher" is not newer in any way that matters to a production database.** `26.10` is a three-month experiment; `9.7` is a decade of patches.

## Innovation vs LTS: what the cadence costs you operationally

An innovation release gets fixes only until the next innovation release lands, roughly quarterly. That sounds manageable until you map it onto real operations:

- **Your upgrade window becomes quarterly, permanently.** Not annually, not when convenient — every three months or you are unsupported.
- **Every upgrade is a binary in-place upgrade on a live data directory**, which means every upgrade is a risk event with a rollback plan that involves restoring a backup, not redeploying a container.
- **Third-party tooling lags.** Backup agents, monitoring exporters, and managed-platform forks track LTS lines. A quarterly-moving target is where subtle incompatibilities live.
- **Auditors do not accept "innovation track" as a support story.** You will be asked for a vendor support commitment and "next quarter's release supersedes this one" is not one.

Where innovation releases *are* genuinely useful: a CI matrix that exercises your schema against the next generation, so that when the next LTS arrives your migrations and queries are already known-compatible. That is a real, valuable use — and it costs nothing, because CI databases get thrown away.

## Decision matrix: which track for which situation

| Your situation | Recommended release | Why |
|---|---|---|
| Production OLTP, any size | **9.7 LTS (9.7.4)** | Patches to 2034; `trunk` develops against it |
| Still on 8.0 | **9.7 LTS, this sprint** | 8.0 has had no patches since April 2026 |
| On 8.4, stable, no appetite for change | **Stay on 8.4.13 until 2029** | Premier support runs to April 2029 |
| Need a 26.x feature in production | **Wait for it to land in an LTS** | Innovation features are not a support contract |
| CI/dev matrix, schema pre-validation | **26.10 alongside 9.7** | Zero cost, catches breakage early |
| Kubernetes operator-managed MySQL | **9.7 LTS** | Operators pin LTS tags; innovation tags churn |
| Regulated/audited environment | **9.7 LTS** | Longest documented support window |

## Upgrade paths, compared

There are two honest ways to move a MySQL instance between major versions, and one that people attempt anyway.

| Path | Mechanism | Downtime | Rollback | Best for |
|---|---|---|---|---|
| **In-place binary upgrade** | Point new `mysqld` at existing datadir, `--upgrade=FORCE` | Restart-length | Restore backup only | Large datasets, tight windows |
| **Logical dump and restore** | `mysqldump` out, import into new version | Full export/import | Old instance untouched | Under ~100 GB, cleanest rollback |
| **Replication cutover** | New version as replica, promote | Seconds | Demote replica | Zero-downtime requirement |

For anything over a few hundred gigabytes, in-place is the only option that fits a maintenance window — but it is also the one where a failed upgrade leaves you restoring from backup. Logical dump is slow but has the property that your old server keeps running untouched until you are satisfied, which is worth a lot at 3 a.m.

### Step 1: run the upgrade checker before you touch anything

MySQL Shell ships a compatibility checker that reads your actual schema, users, and configuration and reports what will break. Run it before scheduling the window, not during it:

```bash
mysqlsh -- util check-for-server-upgrade root@127.0.0.1:3306 \
  --target-version=9.7.0 \
  --output-format=JSON \
  --connections=16 > /tmp/upgrade-check.json
```

Read the `error` entries first — those block the upgrade — then `warning`. The three that bite most often are authentication plugin changes, `utf8mb3` columns that need converting, and reserved-word collisions in identifier names.

### Step 2: prepare the data directory for a fast, clean shutdown

An in-place binary upgrade needs a clean shutdown so InnoDB's redo logs are flushed. This is not optional and it is the single most common cause of an "upgrade took six hours" story:

```sql
-- before shutting down
SET GLOBAL innodb_fast_shutdown = 0;

-- confirm nothing is mid-flight
SHOW PROCESSLIST;
SELECT COUNT(*) FROM information_schema.innodb_trx;
```

Then stop the server, install the 9.7 binaries or pull the new image, and start with an explicit upgrade mode:

```bash
mysqld --upgrade=FORCE --user=mysql --datadir=/var/lib/mysql
```

`FORCE` re-runs every upgrade step regardless of the recorded version — slower than `AUTO`, but it is what you want after a jump across multiple families, because it revalidates the system tables instead of trusting a version stamp written by a different code path.

### Step 3: run 9.7 in a container

For new deployments, the official image is the shortest path, and the tags are unambiguous — `9.7`, `9.7.4`, `8.4`, `26.10`, plus the floating `lts` and `innovation` aliases:

```yaml
services:
  mysql:
    image: mysql:9.7.4
    container_name: mysql97
    restart: unless-stopped
    command:
      - --innodb-buffer-pool-size=4G
      - --innodb-flush-method=O_DIRECT
      - --max-connections=500
      - --slow-query-log=1
      - --long-query-time=2
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: app
      MYSQL_USER: app
      MYSQL_PASSWORD: ${MYSQL_APP_PASSWORD}
    volumes:
      - mysql97-data:/var/lib/mysql
      - ./conf.d:/etc/mysql/conf.d:ro
    ports:
      - "127.0.0.1:3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "--silent"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  mysql97-data:
```

Pin the patch tag (`9.7.4`), not `latest` and not the bare `9.7` — the floating minor tag will move you across patch releases on your next `docker compose pull`, which is exactly how you end up debugging a version you never chose.

## Verification after the upgrade

Three checks separate "the process started" from "the upgrade worked":

```sql
SELECT VERSION();
SELECT @@version_comment;

-- every table must report the new version's engine capabilities
SELECT table_schema, engine, COUNT(*)
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql','information_schema','performance_schema','sys')
GROUP BY table_schema, engine;

-- users must be on the modern auth plugin
SELECT user, host, plugin FROM mysql.user;
```

Then check the server error log for upgrade-phase messages. MySQL writes explicit lines when it rebuilds system tables, and a silently truncated upgrade shows up there as a warning you can still act on.

## Pitfalls that turn an upgrade into an incident

**`mysql_upgrade` in your runbook is obsolete.** Since 8.0.16 the server performs upgrade steps itself at startup; a runbook step that calls the old binary either fails outright or, worse, gives false confidence. Use `--upgrade=` on the new server instead.

**`innodb_fast_shutdown=1` plus a large buffer pool equals a very long upgrade.** The default fast shutdown skips flushing, forcing the new server to do crash recovery on top of the upgrade. Set it to `0` before the window, and expect the shutdown itself to take minutes on a big instance.

**Authentication plugins changed and clients did not.** Modern MySQL defaults to `caching_sha2_password`. Old drivers, old ORMs, and a surprising number of backup tools still negotiate the legacy plugin. The upgrade checker flags this, but only if you run it — and the failure mode in production is "application cannot connect," not "wrong password."

**Reserved words in identifiers.** New releases add reserved words. A column named after a newly reserved word breaks queries that were valid for years. This is why the checker scans identifiers and why you should not skip it on a "small, simple" schema.

**Replication is version-asymmetric.** A newer replica can read from an older primary, but not indefinitely and not across every feature. If you are using the replication-cutover path, upgrade the replica first, verify, then promote — and do not upgrade the primary while an old-version replica is still streaming.

**The clone plugin is faster than a dump, but it copies the source's version compatibility assumptions.** `INSTALL PLUGIN clone SONAME 'mysql_clone.so'` then `CLONE INSTANCE FROM ...` is the fastest way to seed a new instance, and a great way to validate the new version before cutover. Just remember it clones a *running* server's snapshot, so it is not a substitute for a tested backup.

## Why self-host MySQL at all in 2026?

The tracks are the argument. On a managed service you get whichever version the provider chooses, upgraded on their schedule, with their rollback policy — and when an LTS line ends, your options are "their next tier" or a migration project you did not plan. Self-hosting gives you the choice of staying on 8.4.13 until 2029 while you test 9.7 properly, which is the single most valuable thing you can have during a database upgrade: time.

If the rest of your MySQL estate needs the same treatment, our [MySQL high-availability comparison](../2026-05-11-self-hosted-mysql-high-availability-innodb-cluster-percona-xtradb-orchestrator-guide/) covers InnoDB Cluster versus Percona XtraDB versus Orchestrator under real failover, the [replication topology management guide](../2026-05-09-self-hosted-mysql-replication-topology-management-orchestrator-pmm-shell-guide/) is the companion for the cutover path described above, and the [major-version upgrade guide](../2026-06-02-database-major-version-upgrades-pgupgrade-logical-replication-dump-guide/) puts these three migration strategies side by side with PostgreSQL's equivalents.

## FAQ

**Is MySQL 26.10 newer than 9.7?**
Numerically yes, chronologically yes, and in support terms no. 26.10 is an innovation release superseded roughly every quarter — 26.7 already expired on 20 October 2026. 9.7 is the LTS with premier support to April 2031 and end of life in April 2034. "Newer" is the wrong axis; "supported how long" is the right one.

**How long is MySQL 8.4 supported?**
Premier support until **30 April 2029** and end of life **30 April 2032**. There is no emergency. But the innovation work has moved to the 9.7 baseline, so 8.4 is a stable place to stand while you plan, not a place to stay for the decade.

**Can I upgrade from 8.0 straight to 9.7?**
Yes. MySQL supports upgrading across multiple release families in one step, and the upgrade checker validates the target version directly (`--target-version=9.7.0`). The caveat is that `--upgrade=FORCE` is strongly preferred over `AUTO` for a multi-family jump, because it revalidates system tables rather than trusting a version stamp.

**Do I need to run mysql_upgrade after upgrading?**
No. The server performs upgrade steps at startup since 8.0.16, and `mysql_upgrade` is gone from modern runbooks. If a guide tells you to run it, that guide predates 2019.

**What is the safest rollback if an in-place upgrade fails?**
A verified physical backup taken immediately before the window, with `innodb_fast_shutdown=0` so the backup is clean and consistent. There is no "downgrade" path for a data directory — the newer server rewrites system tables in ways the older binary cannot read. That is precisely why logical dump and replication-cutover exist as alternatives: both leave the old instance intact.

**Which release should CI/CD test against?**
Both. Pin production to `9.7.4` and run a parallel CI matrix job against `26.10` so your schema and queries are validated against the next generation before it becomes an LTS. CI databases are disposable, which makes them the one place where a quarterly-moving target is free.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MySQL 9.7 LTS vs 26.10 Innovation in 2026: Pick the Wrong Track and You Patch Every 3 Months",
  "description": "A production-focused MySQL upgrade guide comparing the 9.7 LTS and 26.x innovation release tracks, with support windows, three migration paths, and the pitfalls that turn a database upgrade into an incident.",
  "datePublished": "2026-11-28",
  "dateModified": "2026-11-28",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
