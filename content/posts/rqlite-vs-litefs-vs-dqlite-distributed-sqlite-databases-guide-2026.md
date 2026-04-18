---
title: "rqlite vs LiteFS vs dqlite: Best Distributed SQLite Database 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "database", "sqlite", "distributed"]
draft: false
description: "Compare rqlite, LiteFS, and dqlite — three approaches to distributed SQLite for self-hosted applications. Learn which tool fits your architecture."
---

SQLite is the world's most deployed database engine, embedded in billions of devices. Its simplicity, zero-configuration setup, and single-file architecture make it ideal for self-hosted applications. But SQLite alone does not handle replication, high availability, or multi-node clustering.

Three open-source projects solve this problem in fundamentally different ways: **rqlite**, **LiteFS**, and **dqlite**. This guide compares their architectures, trade-offs, and deployment patterns so you can choose the right distributed SQLite solution for your infrastructure.

## Why Use a Distributed SQLite Database

SQLite stores data in a single file on disk. This is brilliant for local applications but becomes a liability when you need:

- **High availability** — if the server crashes, the database goes offline with it
- **Read scaling** — a single SQLite file can only serve one write at a time
- **Automatic failover** — manual intervention to restore a crashed node
- **Multi-region access** — latency becomes unacceptable when clients connect across data centers

Distributed SQLite solutions address these by replicating data across multiple nodes. Instead of replacing SQLite, they layer consensus or replication on top of it, preserving SQLite's SQL compatibility while adding fault tolerance. For self-hosters running lightweight infrastructure, this means you get the simplicity of SQLite with the resilience of a clustered database.

If you need more traditional distributed SQL databases with full PostgreSQL or MySQL compatibility, see our [CockroachDB vs YugabyteDB vs TiDB comparison](../cockroachdb-vs-yugabyte-vs-tidb-distributed-sql-guide-2026/) and [PostgreSQL vs MySQL vs MariaDB guide](../postgresql-vs-mysql-mariadb-database-comparison-guide/).

## Architecture Comparison

Each project takes a different approach to distribution:

| Feature | rqlite | LiteFS | dqlite |
|---|---|---|---|
| **Approach** | Raft consensus on SQLite commands | FUSE filesystem replication | Raft consensus on SQLite internals |
| **Language** | Go | Go | C |
| **Consensus** | Raft (hashicorp/raft) | Primary-based via Fly.io LIFX | Raft (custom implementation) |
| **Write Model** | Leader only, replicated via Raft log | Primary node writes, replicas pull via LIFX | Leader only, replicated via Raft log |
| **Read Model** | Weak reads on any node; strong reads from leader | Local reads on any replica | Strong reads from any node |
| **Storage** | SQLite file per node | FUSE-mounted SQLite file per node | In-memory SQLite state + disk WAL |
| **Transactions** | Full SQLite transactions | Full SQLite transactions | Full SQLite transactions |
| **GitHub Stars** | 17,429 | 4,743 | 4,303 |
| **License** | MIT | Apache-2.0 | AGPL-3.0 (with commercial option) |
| **Maintained by** | Independent community | Superfly (Fly.io) | Canonical (Ubuntu) |

### rqlite — Raft on Top of SQLite

rqlite wraps a standard SQLite database with a Raft consensus layer. Every SQL command (INSERT, UPDATE, DELETE) is written to the Raft log and replicated to all nodes before being applied. This guarantees that all nodes converge to the same state.

The key insight: rqlite does not modify SQLite itself. It uses the standard `mattn/go-sqlite3` driver and treats SQLite as a black box. The Raft layer ensures command ordering and replication.

**Strengths:**
- Simple deployment — single binary with no external dependencies
- Strong consistency with Raft consensus
- Built-in HTTP/REST API for easy integration
- Automatic leader election and failover
- Snapshot support for fast node recovery

**Limitations:**
- Write throughput limited by Raft consensus latency
- Not a drop-in replacement for SQLite (must use HTTP API or go client)
- No native connection pooling

### LiteFS — FUSE Filesystem Replication

LiteFS, developed by Superfly (the company behind Fly.io), uses a FUSE (Filesystem in Userspace) mount to intercept SQLite file operations. The primary node writes to the database normally, while LiteFS streams the Write-Ahead Log (WAL) to replica nodes. Replicas receive and replay the WAL, keeping their local SQLite files in sync.

Unlike rqlite, LiteFS does not use a consensus algorithm. Instead, it relies on a single primary node for writes, with replicas pulling changes asynchronously.

**Strengths:**
- Transparent to SQLite — any SQLite application works without modification
- Low read latency — replicas serve reads from local files
- Simpler architecture — no consensus overhead for writes
- Designed for edge deployments with Fly.io integration

**Limitations:**
- Single primary node — no automatic failover without external orchestration
- Requires FUSE support on the host OS (not available on all platforms)
- Replicas have eventual consistency, not strong consistency
- Tied to Fly.io's LIFX service for primary election

### dqlite — Raft Embedded in SQLite

dqlite, developed by Canonical, embeds the Raft consensus layer directly into SQLite's internal architecture. Rather than treating SQLite as a black box (like rqlite), dqlite hooks into SQLite's VFS (Virtual File System) layer. This allows it to replicate at a lower level — Raft log entries contain individual page writes rather than full SQL commands.

**Strengths:**
- Very low latency — page-level replication is faster than SQL-level
- Native SQLite wire protocol — applications connect as if using standard SQLite
- Used in production by Canonical (MicroK8s, LXD, Juju)
- Strong consistency with automatic failover

**Limitations:**
- C codebase — harder to modify and contribute to compared to Go alternatives
- AGPL-3.0 license may not suit all use cases
- Requires a C compiler and libuv for building from source
- Less community adoption than rqlite

## Installation and Deployment

### Installing rqlite

rqlite ships as a single binary. Download it directly or use the Docker image:

```bash
# Quick install script
curl -L https://get.rqlite.io | sh
sudo mv rqlited rqlite /usr/local/bin/

# Or build from source
git clone https://github.com/rqlite/rqlite.git
cd rqlite
go build ./cmd/rqlited
```

Start a 3-node cluster:

```bash
# Node 1 (leader)
rqlited -http-addr :4001 -raft-addr :4002 ~/node.1

# Node 2
rqlited -http-addr :4003 -raft-addr :4004 -join http://localhost:4001 ~/node.2

# Node 3
rqlited -http-addr :4005 -raft-addr :4006 -join http://localhost:4001 ~/node.3
```

Query the cluster:

```bash
rqlite -H localhost -P 4001
127.0.0.1:4001> CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)
127.0.0.1:4001> INSERT INTO users(name) VALUES ("alice")
127.0.0.1:4001> SELECT * FROM users
```

#### Docker Compose for rqlite

```yaml
version: "3.8"

services:
  rqlite1:
    image: rqlite/rqlite:latest
    container_name: rqlite1
    ports:
      - "4001:4001"
      - "4002:4002"
    volumes:
      - ./data/node1:/root/data
    command: ["rqlited", "-http-addr", "0.0.0.0:4001", "-raft-addr", "0.0.0.0:4002", "/root/data"]

  rqlite2:
    image: rqlite/rqlite:latest
    container_name: rqlite2
    ports:
      - "4003:4001"
      - "4004:4002"
    volumes:
      - ./data/node2:/root/data
    command: ["rqlited", "-http-addr", "0.0.0.0:4001", "-raft-addr", "0.0.0.0:4002", "-join", "http://rqlite1:4002", "/root/data"]
    depends_on:
      - rqlite1

  rqlite3:
    image: rqlite/rqlite:latest
    container_name: rqlite3
    ports:
      - "4005:4001"
      - "4006:4002"
    volumes:
      - ./data/node3:/root/data
    command: ["rqlited", "-http-addr", "0.0.0.0:4001", "-raft-addr", "0.0.0.0:4002", "-join", "http://rqlite1:4002", "/root/data"]
    depends_on:
      - rqlite1
```

### Installing LiteFS

LiteFS requires FUSE support on the host. On Debian/Ubuntu:

```bash
# Install FUSE
sudo apt-get install -y fuse libfuse-dev

# Install LiteFS from GitHub releases
curl -L https://github.com/superfly/litefs/releases/latest/download/litefs-linux-amd64.tar.gz | tar xz
sudo mv litefs /usr/local/bin/
```

LiteFS configuration file (`/etc/litefs.yml`):

```yaml
fuse:
  dir: "/litefs"

data:
  dir: "/var/lib/litefs"

exec:
  - cmd: "python3 app.py"

lease:
  type: "consul"
  candidate: true
  advertise-url: "http://${HOSTNAME}:20202"

  consul:
    url: "${CONSUL_URL}"
    key: "litefs/primary"

  candidate: true
```

```yaml
version: "3.8"

services:
  app-primary:
    image: your-app:latest
    devices:
      - /dev/fuse:/dev/fuse
    cap_add:
      - SYS_ADMIN
    volumes:
      - litefs-data:/var/lib/litefs
      - litefs-fuse:/litefs
    environment:
      - LITEFS_CANDIDATE=true
      - CONSUL_URL=http://consul:8500

  app-replica:
    image: your-app:latest
    devices:
      - /dev/fuse:/dev/fuse
    cap_add:
      - SYS_ADMIN
    volumes:
      - litefs-data:/var/lib/litefs
      - litefs-fuse:/litefs
    environment:
      - LITEFS_CANDIDATE=false
      - CONSUL_URL=http://consul:8500

  consul:
    image: consul:latest
    command: ["agent", "-dev", "-client", "0.0.0.0"]
    ports:
      - "8500:8500"

volumes:
  litefs-data:
  litefs-fuse:
```

### Installing dqlite

dqlite is used as a C library embedded in your application, but you can also run it standalone:

```bash
# Install dependencies
sudo apt-get install -y libuv1-dev libsqlite3-dev liblz4-dev pkg-config

# Build from source
git clone https://github.com/canonical/dqlite.git
cd dqlite
./configure
make
sudo make install

# Verify installation
dqlite --version
```

Example usage with a Go application using the Go dqlite driver:

```go
package main

import (
    "database/sql"
    "fmt"
    "os"
    _ "github.com/canonical/go-dqlite/driver"
)

func main()
    db, err := sql.Open("dqlite", "file:mydb?mode=rwc")
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
    defer db.Close()

    _, err = db.Exec("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)")
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error creating table: %v\n", err)
        os.Exit(1)
    }

    _, err = db.Exec("INSERT INTO items (name) VALUES (?)", "example-item")
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error inserting: %v\n", err)
        os.Exit(1)
    }

    rows, err := db.Query("SELECT * FROM items")
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error querying: %v\n", err)
        os.Exit(1)
    }
    defer rows.Close()

    for rows.Next() {
        var id int
        var name string
        rows.Scan(&id, &name)
        fmt.Printf("ID: %d, Name: %s\n", id, name)
    }
}
```

## Performance Characteristics

Understanding performance trade-offs is critical for choosing the right tool:

| Metric | rqlite | LiteFS | dqlite |
|---|---|---|---|
| **Write Latency** | ~5-20ms (Raft roundtrip) | ~1-5ms (local write) | ~1-10ms (Raft, page-level) |
| **Read Latency (local)** | ~0.1ms | ~0.1ms | ~0.1ms |
| **Read Latency (remote)** | ~0.5ms (weak consistency) | ~0.1ms (local file) | ~0.5ms (strong) |
| **Throughput** | ~1,000 writes/sec (3-node) | ~10,000 writes/sec (primary) | ~5,000 writes/sec (3-node) |
| **Failover Time** | < 1 second (automatic) | Manual or via LIFX | < 1 second (automatic) |
| **Storage Overhead** | ~2x (SQLite + Raft log) | ~1x per replica | ~2x (SQLite + Raft log) |

**When to choose each:**

- **rqlite**: Best for general-purpose distributed SQLite with strong consistency. Ideal when you want a simple, self-contained solution with automatic leader election. The HTTP API makes it easy to integrate with any programming language.

- **LiteFS**: Best when you want zero application changes. Since LiteFS sits at the filesystem level, any existing SQLite application works without modification. However, the FUSE dependency and eventual consistency model may not suit all use cases.

- **dqlite**: Best for performance-critical applications that need low-latency replication. The page-level Raft replication is faster than SQL-level approaches. Canonical's production use in MicroK8s and LXD proves its maturity.

## Use Case Recommendations

### Microservices with Shared State

For microservices that need a shared, lightweight database, **rqlite** is the strongest choice. Its HTTP API and REST-compatible endpoints make it easy for services in different languages to query the same data without custom drivers.

### Edge Deployments

For edge computing scenarios where nodes may have intermittent connectivity, **LiteFS** shines. Its primary-replica model allows edge nodes to serve reads locally from cached SQLite files, even when disconnected from the primary.

### Kubernetes Operators

For Kubernetes-native deployments, **dqlite** integrates seamlessly. Canonical uses it as the backing store for MicroK8s, and its Go bindings make it straightforward to embed in custom operators.

### High-Availability Web Applications

For web applications requiring HA, **rqlite** provides the simplest deployment model. Drop it in behind a load balancer, and the built-in leader election handles failover automatically. For more complete database high availability patterns, see our [Patroni vs Galera Cluster vs repmgr guide](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/).

## Migration from Single-Node SQLite

Migrating an existing single-node SQLite database to a distributed setup varies by tool:

```bash
# rqlite — import from SQLite dump
sqlite3 mydb.db .dump | rqlite -H localhost -P 4001 -s

# LiteFS — copy the SQLite file to the FUSE mount
cp mydb.db /litefs/mydb.db
# LiteFS will replicate the file to all nodes automatically

# dqlite — use the dqlite CLI to import
sqlite3 mydb.db .dump > dump.sql
# Then load through the dqlite driver in your application
```

For any of these approaches, always backup your original SQLite file before migration. If you're also running a self-hosted backup strategy, see our [Restic vs Borg vs Kopia comparison](../restic-vs-borg-vs-kopia-backup-guide/) for database backup tools.

## FAQ

### Which distributed SQLite solution is the easiest to set up?

**rqlite** is the easiest to set up. It ships as a single binary, requires no external dependencies, and starts a cluster with just a few command-line flags. You can have a 3-node cluster running in under a minute. LiteFS requires FUSE support and a consul or LIFX service for primary election, while dqlite requires building from source with C dependencies.

### Can I use LiteFS without Fly.io?

Yes, but with limitations. LiteFS supports two lease types: `consul` and `static`. The `consul` lease type works with any self-hosted Consul instance, making it usable outside of Fly.io's infrastructure. The `static` lease type allows you to manually designate a primary node. However, some of LiteFS's most polished features (like automatic primary election via LIFX) are Fly.io-specific.

### Is dqlite a drop-in replacement for SQLite?

dqlite is designed to be wire-compatible with SQLite, meaning applications using standard SQLite client libraries can connect to dqlite without code changes — as long as they use the dqlite driver. The key difference is that dqlite runs as a separate process that your application connects to, whereas standard SQLite is embedded in-process. rqlite, by contrast, requires using its HTTP API or Go client.

### How many nodes can each solution support?

rqlite supports clusters of 3 to 7 nodes (odd numbers for Raft quorum). LiteFS supports any number of replicas, limited only by network bandwidth for WAL streaming. dqlite also supports 3 to 7 node clusters. For large-scale deployments with more nodes, consider traditional distributed databases like CockroachDB or TiDB.

### What happens when the leader/primary node fails?

In **rqlite**, the Raft consensus automatically elects a new leader within ~1 second. In **LiteFS**, failover is not automatic — you need external orchestration (Consul, Kubernetes, or manual intervention) to promote a replica to primary. In **dqlite**, Raft consensus handles automatic leader election similarly to rqlite, with failover completing in under a second.

### Which solution has the best write performance?

**LiteFS** has the best raw write performance because it avoids consensus overhead — writes go directly to the local SQLite file on the primary node, with WAL streaming happening asynchronously. However, this comes at the cost of eventual consistency. **dqlite** offers the best write performance among consensus-based solutions due to its page-level Raft replication, which is faster than rqlite's SQL-level replication.

### Are these solutions production-ready?

Yes. **rqlite** has been in production since 2015 with 17,000+ GitHub stars and active community development. **LiteFS** is used in production by Fly.io to power their edge database infrastructure. **dqlite** is the database layer for Canonical's MicroK8s, LXD, and Juju, serving millions of deployments worldwide.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "rqlite vs LiteFS vs dqlite: Best Distributed SQLite Database 2026",
  "description": "Compare rqlite, LiteFS, and dqlite — three open-source approaches to distributed SQLite for self-hosted applications. Learn which tool fits your architecture.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
