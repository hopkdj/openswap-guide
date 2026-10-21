---
title: "Apache Polaris vs Lakekeeper vs Gravitino in 2026: Which Iceberg Catalog Should You Actually Run?"
date: "2026-10-21"
tags: ["data-lakehouse", "iceberg", "self-hosted", "data-engineering", "comparison"]
draft: false
cover: "/img/screenshots/lakekeeper-catalog-ui.jpg"
description: "Hands-on comparison of Apache Polaris, Lakekeeper and Apache Gravitino as Iceberg REST catalogs — real Docker configs, credential vending, auth backends and the failure modes nobody warns you about."
---

Your Iceberg tables are not the hard part anymore. Every engine speaks the format, and object storage is cheap. What breaks at 3am is the **catalog**: the thing that answers "where does this table live, who may read it, and which storage credential do I hand out?" Get that wrong and you end up with three engines writing to the same bucket under three different metadata pointers, and a data lake that quietly forks itself.

In 2026 there are three credible open-source answers, all Apache-2.0, all shipping an Iceberg REST Catalog endpoint: **Apache Polaris**, **Lakekeeper**, and **Apache Gravitino**. They look interchangeable in a feature matrix. They are not.

## TL;DR — the 30-second verdict

- **Run Lakekeeper** if you want the smallest operational surface and real credential vending in a single Rust binary. It is the one I would deploy on a Friday.
- **Run Apache Polaris** if you need ASF governance, multi-realm multi-tenancy, and you are already a Java shop that can afford a slower, Quarkus-flavoured operations story.
- **Run Apache Gravitino** only if your problem is *federation* — Iceberg plus Hive plus MySQL plus Kafka metadata behind one namespace. As a pure Iceberg catalog it is heavier than the other two for no benefit.

## The comparison table (data pulled from GitHub on 2026-10-21)

| Dimension | Apache Polaris | Lakekeeper | Apache Gravitino |
|---|---|---|---|
| Stars | **2,095** | 1,485 | **3,259** |
| Last push | 2026-10-21 | 2026-10-21 | 2026-10-21 |
| Language | Java (Quarkus) | **Rust** | Java |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Catalog protocol | Iceberg REST | Iceberg REST | Iceberg REST + own metalake API |
| Metadata backend | JDBC (Postgres), in-memory for dev | **Postgres only** | MySQL/Postgres + Hive Metastore |
| Auth backends | OAuth2/OIDC, internal | OIDC, OpenFGA, allow-all for dev | OAuth2, Ranger integration |
| Credential vending | Yes (S3/GCS/Azure) | **Yes (S3, STS AssumeRole)** | Yes (S3, plus HDFS/Kerberos paths) |
| Web UI | Minimal / API-first | **Yes, built-in** | Yes, plus CLI |
| Multi-table-format | Iceberg | Iceberg, Delta, Lance (generic tables) | **Iceberg, Hudi, Paimon, Delta + federated RDBMS** |
| Container image | `apache/polaris` | `quay.io/lakekeeper/catalog` | `apache/gravitino` |
| Ops complexity | Medium-high | **Low** | High |

Stars and push dates are live from `gh repo view` at publication time. Everything else comes from reading each project's own compose files and docs, not from marketing pages.

## Decision matrix — pick in ten seconds

| Your situation | Recommended | Why |
|---|---|---|
| One team, S3 + Iceberg, Spark/Trino/DuckDB readers | **Lakekeeper** | Single binary + Postgres, vending works out of the box, UI for warehouse setup |
| Regulated enterprise, needs ASF release train and multi-realm isolation | **Apache Polaris** | Realm-per-tenant model, ASF governance, storage credential scoping per catalog |
| You must expose Hive tables, MySQL and Iceberg under one namespace | **Apache Gravitino** | Metalake federation is its entire reason to exist |
| Air-gapped cluster, no external IdP | **Lakekeeper** with `allowall` temporarily, then OIDC | Fewer moving parts; swap auth later |
| You want zero new stateful services | None — use a Hadoop-style metastore and accept the pain | All three need a relational backend in production |

## What a catalog actually does (and why the REST spec matters)

The Iceberg REST Catalog spec is deceptively small: a handful of endpoints under `/v1/{prefix}/namespaces` and `/v1/{prefix}/namespaces/{ns}/tables`, plus `/v1/config` for bootstrapping. The value is that **the client never holds storage credentials**. It asks the catalog to load a table, the catalog checks permissions, and the catalog returns a short-lived credential plus the metadata file location.

That last part — credential vending — is where these three projects diverge most, and it is the single feature that decides whether your lake is secure or whether every analyst has a long-lived S3 key in a `.env` file.

## Apache Polaris — the ASF heavyweight

Polaris was donated to the Apache Software Foundation and reached the point where "Polaris" and "Iceberg REST catalog" are nearly synonymous in enterprise decks. The architecture is a Quarkus service in front of a relational metastore, with a **realm** concept: each realm is an isolated tenant with its own principal roster and its own catalog definitions. One Polaris deployment can serve `finance` and `marketing` without either seeing the other's namespaces.

The official getting-started compose from the repo (trimmed to the catalog service) is genuinely the best starting point because it encodes the environment variables that are otherwise undocumented:

```yaml
services:
  polaris:
    image: apache/polaris:latest
    ports:
      - "8181:8181"
      - "8182"
    environment:
      AWS_REGION: us-west-2
      AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID
      AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY
      POLARIS_BOOTSTRAP_CREDENTIALS: POLARIS,root,s3cr3t
      polaris.realm-context.realms: POLARIS
      polaris.features."ALLOW_INSECURE_STORAGE_TYPES": "true"
      polaris.features."SUPPORTED_CATALOG_STORAGE_TYPES": "[\"FILE\",\"S3\",\"GCS\",\"AZURE\"]"
    healthcheck:
      test: ["CMD", "curl", "http://localhost:8182/healthcheck"]
      interval: 10s
      timeout: 10s
      retries: 5
```

Two things in that file are traps. `POLARIS_BOOTSTRAP_CREDENTIALS` creates the root principal on first boot — if you leave the default `root:s3cr3t` in production, you have published your catalog. And `ALLOW_INSECURE_STORAGE_TYPES: "true"` is required only because the getting-started flow uses local file storage; with real S3 you remove it and let Polaris mint scoped STS credentials instead.

Creating a catalog is a plain REST call, which is refreshingly honest:

```bash
curl -X POST http://localhost:8181/api/management/v1/catalogs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog": {
      "name": "lake",
      "type": "INTERNAL",
      "properties": {
        "default-base-location": "s3://analytics-lake/warehouse"
      },
      "storageConfigInfo": {
        "storageType": "S3",
        "roleArn": "arn:aws:iam::123456789012:role/polaris-vend",
        "region": "us-west-2"
      }
    }
  }'
```

**Where Polaris hurts:** JVM tuning, a management API that is separate from the Iceberg API (`/api/management/v1` vs `/api/catalog/v1`), and documentation that still assumes you are reading the source. Expect a day of setup, not an hour.

## Lakekeeper — the one that respects your time

Lakekeeper is the youngest of the three and the only one written in Rust. That shows up as a ~30MB container and startup measured in milliseconds rather than seconds. It stores all state in Postgres — no embedded H2, no separate metastore — and ships a real web UI for creating warehouses and minting client credentials.

![Lakekeeper catalog UI — warehouse creation](/img/screenshots/lakekeeper-catalog-ui.jpg "Lakekeeper's built-in UI walks you through warehouse creation and storage credential setup")

The repo's `docker-compose/docker-compose.yaml` is production-shaped, not a toy: it separates a `migrate` one-shot task from the `serve` process so you never race schema changes against traffic.

```yaml
services:
  lakekeeper:
    image: quay.io/lakekeeper/catalog:latest-main
    environment:
      - LAKEKEEPER__PG_ENCRYPTION_KEY=change-me-32-bytes-minimum
      - LAKEKEEPER__PG_DATABASE_URL_READ=postgresql://postgres:secret@db:5432/postgres
      - LAKEKEEPER__PG_DATABASE_URL_WRITE=postgresql://postgres:secret@db:5432/postgres
      - LAKEKEEPER__AUTHZ_BACKEND=allowall
    command: ["serve"]
    depends_on:
      migrate:
        condition: service_completed_successfully
    ports:
      - "8181:8181"

  migrate:
    image: quay.io/lakekeeper/catalog:latest-main
    environment:
      - LAKEKEEPER__PG_DATABASE_URL_WRITE=postgresql://postgres:secret@db:5432/postgres
      - LAKEKEEPER__PG_ENCRYPTION_KEY=change-me-32-bytes-minimum
    command: ["migrate"]
    restart: "no"

  db:
    image: postgres:17
    environment:
      - POSTGRES_PASSWORD=secret
```

Three operational notes that the README does not stress:

1. **`LAKEKEEPER__PG_ENCRYPTION_KEY` must match between the migrate and serve containers.** Rotate it carelessly and every stored storage secret becomes unreadable — the service starts, then fails on the first table load.
2. **`AUTHZ_BACKEND=allowall` is a development switch**, full stop. Production is either OIDC (via `LAKEKEEPER__OPENID_PROVIDER_URI` and `LAKEKEEPER__OPENID_AUDIENCE`) or OpenFGA if you need relationship-based access.
3. Lakekeeper also handles **Delta and Lance** tables as "generic tables" alongside Iceberg. If you are hedging on table format, this is the only one of the three that will not force a migration later.

Pointing Spark or Trino at it is a two-line config change, because it implements the same REST spec:

```properties
spark.sql.catalog.lake=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.lake.type=rest
spark.sql.catalog.lake.uri=http://lakekeeper:8181/catalog
spark.sql.catalog.lake.warehouse=lake
spark.sql.catalog.lake.credential=root:s3cr3t
```

## Apache Gravitino — federation, not a catalog

Gravitino's pitch is different enough that comparing it head-to-head with the other two is slightly unfair. Its core abstraction is a **metalake**: a namespace that can hold not only Iceberg catalogs but also Hive Metastore schemas, MySQL databases, Kafka topics and filesets. It then exposes each through a unified REST surface.

```bash
docker run -d --name gravitino \
  -p 8090:8090 \
  -e GRAVITINO_METALAKE=analytics \
  apache/gravitino:latest
```

For a pure Iceberg shop, that metalake layer is pure overhead: an extra API to learn, an extra object to create before you can create a catalog, and a heavier JVM footprint than Polaris. Where it wins decisively is the "we have 40 MySQL databases and a Hive cluster and nobody knows what exists" problem — Gravitino lets a single query engine enumerate all of it through one endpoint, with Ranger plugged in for column-level policy.

**Pick it for the federation, review it as a catalog.** If a vendor tells you Gravitino is a drop-in Polaris replacement for a single Iceberg warehouse, they are selling you a forklift to move a chair.

## Head-to-head: the three things that actually bite

**1. Credential vending scope.** All three vend, but the blast radius differs. Polaris scopes credentials to a catalog, Lakekeeper scopes to a warehouse plus table location, Gravitino scopes per metalake catalog. If you have one bucket shared by five teams, Polaris and Gravitino will happily hand out access to the whole prefix — you need per-catalog buckets or you have not solved anything.

**2. Metadata lock-in.** None of these stores metadata in a proprietary way — the Iceberg metadata JSON lives in your bucket, and the catalog is just an index. That means **you can migrate catalogs** by re-registering tables. Test this before you commit: create a table, export the metadata pointer, drop the catalog, and re-register it in a second instance. Teams that skip this test discover during an outage that their "stateless" catalog is load-bearing.

**3. Cache invalidation across engines.** Every engine caches table metadata. With three engines hitting one catalog, a schema change can take minutes to propagate. Lakekeeper's `ETag`-based conditional loads are the most predictable in my testing; Polaris requires you to know whether your client is using the `/v1/config` overrides; Gravitino adds a metalake-level cache on top.

## Operations pitfalls worth reading twice

- **Do not put the catalog's Postgres on the same disk as your object storage gateway.** A catalog that cannot write its own metadata table will refuse all writes, and recovery means restoring a database, not a bucket.
- **Set `warehouse` explicitly on every client.** The default empty warehouse silently resolves to the catalog's default base location; when you later add a second warehouse, clients start writing to the wrong prefix.
- **Keep `allowall` auth off in staging, not just production.** Staging is where people copy configs from.
- **Bootstrap credentials are forever.** Polaris and Lakekeeper both create a root principal at first boot. Rotate it in the same change window as deployment or you will never do it.
- **Version-pin the image.** `latest-main` (Lakekeeper) and `latest` (Polaris) move daily. A Saturday `docker compose pull` is a change-management event whether you filed a ticket or not.

## Why self-host the catalog instead of buying a managed one

Managed lakehouse catalogs charge per table, per request, or per seat, and they all assume your compute lives in the same cloud. A self-hosted catalog costs one Postgres instance and a container, works identically in an air-gapped rack, and — critically — **keeps the metadata index inside your trust boundary**. The metadata is not the data, but it is the map: table names, schemas, column comments, and the lineage of every snapshot. Handing the map to a vendor is a bigger decision than handing over raw Parquet.

If you are still assembling the rest of the stack, our [Iceberg vs Hudi vs Delta Lake format comparison](../apache-iceberg-vs-hudi-vs-delta-lake-open-data-lakehouse-formats-2026/) covers the table-format decision that has to come first, and the [Trino vs Presto vs StarRocks query engine guide](../2026-04-19-trino-vs-presto-vs-starrocks-distributed-sql-query-engines-guide-2026/) covers what sits on top of the catalog. You will also need object storage you control — see the [Garage vs SeaweedFS vs Ceph RGW comparison](../2026-05-14-self-hosted-s3-object-storage-garage-vs-seaweedfs-vs-ceph-rgw-guide-2026/) for the S3-compatible layer underneath.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Apache Polaris vs Lakekeeper vs Gravitino in 2026: Which Iceberg Catalog Should You Actually Run?",
  "description": "Hands-on comparison of Apache Polaris, Lakekeeper and Apache Gravitino as Iceberg REST catalogs, with real Docker configs, credential vending behaviour and operational pitfalls.",
  "datePublished": "2026-10-21",
  "dateModified": "2026-10-21",
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

**Which Iceberg catalog is fastest to deploy in 2026?**
Lakekeeper. A Postgres container plus the Lakekeeper image, two commands (`migrate` then `serve`), and you have a working REST catalog with a UI. Polaris needs a management-API round trip to create a catalog and a realm configured correctly before clients can connect; Gravitino needs a metalake created before a catalog.

**Do I need a catalog at all if I only use one engine?**
Technically no — Spark can use a Hadoop-style metastore with a warehouse path. Practically yes, as soon as a second engine or a second team appears. The catalog is what prevents two writers from producing divergent metadata for the same table name.

**Can I migrate from Polaris to Lakekeeper without rewriting tables?**
Yes, because both are indexes over the same Iceberg metadata files in object storage. Use Iceberg's `register_table` to point the new catalog at the existing metadata JSON. The migration risk is not data loss, it is losing track of which snapshot each engine last saw — so freeze writes during the switch.

**Is Gravitino a superset of Polaris?**
No. Gravitino federates more metadata sources, but it does not implement Polaris's realm-based multi-tenancy, and its Iceberg support is one connector among many rather than the core abstraction. Treat them as different tools that happen to both expose an Iceberg REST endpoint.

**What happens if the catalog database goes down?**
Existing queries that already loaded a table keep running (metadata is cached client-side), but any new table load fails. This is why the catalog Postgres deserves the same backup policy as your production application database, not a `docker volume` nobody looks at.

**Does Lakekeeper's generic table support mean I can skip Iceberg?**
You can store Delta and Lance tables through it, but you still need a query engine that understands the format. Generic tables make Lakekeeper a hedge, not an escape hatch from choosing a table format.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
