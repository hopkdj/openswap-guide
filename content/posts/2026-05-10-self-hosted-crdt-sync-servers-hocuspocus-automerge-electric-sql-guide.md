---
title: "Self-Hosted CRDT Sync Servers: Hocuspocus vs Automerge vs Electric SQL (2026)"
date: "2026-05-10"
tags: ["crdt", "real-time", "collaboration", "local-first", "websocket", "sync-server", "yjs"]
draft: false
---

Conflict-free Replicated Data Types (CRDTs) have become the foundation of real-time collaborative applications. While CRDT libraries handle the data merging logic client-side, you still need a server to relay updates between users, manage persistence, and handle authentication. This guide compares the top self-hosted CRDT sync server platforms.

## What Are CRDT Sync Servers?

CRDTs are data structures that can be modified concurrently by different users and automatically merge without conflicts. Think collaborative document editing, shared whiteboards, or multiplayer games. The sync server acts as the relay — it receives document updates from one client, stores them, and broadcasts them to other connected clients. Unlike traditional client-server architectures, CRDT-based apps can work offline and sync when reconnected, since the conflict resolution happens mathematically at the data structure level.

The key insight is that CRDTs guarantee eventual consistency without requiring a central authority to serialize operations. Two users editing the same document simultaneously will produce changes that merge correctly, regardless of the order in which the server receives them.

## Comparison Overview

| Feature | Hocuspocus | Automerge | Electric SQL |
|---|---|---|---|
| GitHub Stars | 2,256+ | 6,260+ | 10,175+ |
| CRDT Engine | Yjs (external) | Automerge (built-in) | PostgreSQL + CRDT |
| Protocol | WebSocket | Sync Protocol | HTTP/REST + WebSocket |
| Language | Node.js/TypeScript | Rust + JS | TypeScript + Rust |
| Persistence | SQLite, PostgreSQL | Custom storage | PostgreSQL (source of truth) |
| Offline Support | Via Yjs | Native | Via embedded SQLite |
| Docker Available | Yes | Yes | Yes |
| License | MIT | MIT | Apache 2.0 |
| Best For | Yjs-based apps | Custom CRDT apps | Full-stack sync platform |

## Hocuspocus: The Yjs WebSocket Backend

Hocuspocus is the official WebSocket backend for Yjs, the most popular CRDT library for collaborative editing. Created by the team behind Tiptap (the ProseMirror-based editor), Hocuspocus provides a production-ready server for Yjs document synchronization.

### Architecture

Hocuspocus follows a simple provider-server model where clients connect via WebSocket and the server manages document state and persistence:

```yaml
services:
  hocuspocus:
    image: ghcr.io/ueberdosis/hocuspocus:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=sqlite:///data/documents.db
      - PORT=3000
    volumes:
      - ./data:/data
    restart: unless-stopped
```

### Key Features

- **Yjs Native**: First-class support for Yjs documents, awareness protocols, and cursor tracking
- **Webhook System**: Extensible lifecycle hooks for `onStoreDocument`, `onLoadDocument`, and `onAuthenticate` events
- **Redis Support**: Horizontal scaling via Redis pub/sub for multi-instance deployments
- **SQLite/PostgreSQL Persistence**: Built-in database adapters for document storage
- **TypeScript**: Fully typed API with custom extension support

## Automerge: CRDT-Native Sync Server

Automerge is both a CRDT library and a sync protocol. Unlike Hocuspocus which relies on an external CRDT library (Yjs), Automerge provides its own CRDT implementation with a purpose-built sync protocol designed for efficient change propagation.

### Architecture

Automerge uses a request-response sync model where peers exchange changesets:

```yaml
services:
  automerge-server:
    image: ghcr.io/automerge/automerge-repo-sync-server:latest
    ports:
      - "3000:3000"
    environment:
      - STORAGE_PATH=/data/automerge
    volumes:
      - ./data:/data/automerge
    restart: unless-stopped
```

### Key Features

- **Built-in CRDT**: Automerge CRDT supports text, maps, arrays, and counters natively
- **Language Agnostic**: Rust core with bindings for JavaScript, Swift, Kotlin, and Rust
- **Change-Based Sync**: Only transmits actual changes, not full document snapshots
- **No Central Authority**: Designed for peer-to-peer sync, but works with central servers
- **Encryption**: Supports encrypted document storage at rest

## Electric SQL: PostgreSQL-Powered Sync

Electric SQL takes a fundamentally different approach — it uses PostgreSQL as the source of truth and syncs a local SQLite database on the client. This means you get full SQL query capabilities on both server and client sides.

### Architecture

Electric SQL acts as a change data capture (CDC) layer between PostgreSQL and clients, reading the write-ahead log for change propagation:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: electric
      POSTGRES_USER: electric
      POSTGRES_PASSWORD: electric
    volumes:
      - pgdata:/var/lib/postgresql/data

  electric:
    image: electricsql/electric:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://electric:electric@postgres:5432/electric
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  pgdata:
```

### Key Features

- **PostgreSQL Source of Truth**: Full ACID transactions, complex queries, and existing tooling
- **Local SQLite**: Clients get a real embedded database with SQL queries
- **Selective Sync**: Subscribe to specific tables or rows, not entire documents
- **Reactive**: Automatic UI updates when data changes via React hooks
- **Offline-First**: Full read/write offline, automatic sync on reconnect

## Choosing the Right CRDT Sync Server

The choice depends on your application architecture and requirements:

- **Choose Hocuspocus** if you are building a collaborative editor with Yjs or Tiptap. It is the most mature option with the largest community and integrates seamlessly with existing Yjs applications.
- **Choose Automerge** if you need a language-agnostic CRDT with multi-platform support. The Rust core and native bindings make it ideal for mobile and desktop applications.
- **Choose Electric SQL** if you want a full-stack sync platform backed by PostgreSQL. It is the most powerful option for data-heavy applications that need complex queries on both server and client.

## Why Self-Host Your CRDT Sync Server?

Running your own sync server gives you complete control over real-time collaboration infrastructure. When you self-host, you own the data pipeline — no third-party service sees your collaborative documents, and you control availability, scaling, and compliance requirements.

Self-hosting also eliminates vendor lock-in. If a hosted sync provider changes pricing, shuts down, or has an outage, your entire application is affected. With a self-hosted server, you control the deployment timeline, can run multiple instances for redundancy, and can customize the server behavior to your specific needs.

For collaborative applications dealing with sensitive data — healthcare records, legal documents, or financial models — self-hosting is often a compliance requirement. Regulations like HIPAA, GDPR, and SOC 2 frequently mandate that data never leaves your infrastructure.

Data sovereignty is another critical factor. Organizations operating in the EU, China, or other jurisdictions with strict data residency laws must ensure that user data is stored and processed within specific geographic boundaries. Self-hosted CRDT servers let you deploy infrastructure in compliant regions.

For real-time file synchronization patterns, see our [file sync comparison](../2026-04-18-self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/).
For distributed data management, our [graph databases guide](../2026-05-02-dgraph-vs-janusgraph-vs-orientdb-self-hosted-graph-databases-guide/) covers server-side options.
And for Kubernetes backup strategies, the [Velero vs Stash guide](../2026-04-22-velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide-2026/) is essential reading.

## Deployment Architecture PatternsFor production CRDT sync server deployments, several architectural patterns emerge based on scale and reliability requirements. Single-instance deployments work for small teams with predictable traffic. Multi-instance deployments add horizontal scalability by running multiple sync server instances behind a load balancer. Hocuspocus achieves this through Redis pub/sub, where each instance publishes document changes to Redis channels. Electric SQL scales differently since the sync layer is stateless, with PostgreSQL handling all persistence.High-availability deployments add redundancy at every layer. For Hocuspocus, this means multiple instances with Redis clustering and PostgreSQL replication. For Electric SQL, this means PostgreSQL with streaming replication and multiple Electric instances.
## FAQ

### What is a CRDT and why do I need a sync server?

A CRDT (Conflict-free Replicated Data Type) is a data structure designed for concurrent modification without conflicts. While CRDTs handle conflict resolution mathematically, you still need a sync server to relay changes between users, persist documents, and manage authentication. Without a server, users cannot collaborate in real-time.

### Can Hocuspocus handle thousands of concurrent users?

Yes. Hocuspocus supports horizontal scaling via Redis pub/sub. Each instance handles WebSocket connections locally, and Redis broadcasts document changes across instances. With proper infrastructure, it can handle tens of thousands of concurrent connections.

### Does Electric SQL work without PostgreSQL?

No. Electric SQL requires PostgreSQL as its source of truth. The entire sync mechanism relies on reading PostgreSQL write-ahead log. However, you can run PostgreSQL locally in Docker so you do not need a managed database service.

### Which CRDT server supports offline editing?

All three support offline editing but in different ways. Hocuspocus relies on Yjs built-in offline support where changes queue locally and sync on reconnect. Automerge is designed for offline-first with its change-based sync. Electric SQL provides full offline read and write via embedded SQLite.

### Is Automerge production-ready?

Automerge 2.0 has been stable and is used in production by several companies. The sync server reference implementation is minimal but functional. For production deployments, you may want to add custom persistence and authentication layers.

### How does Electric SQL handle conflicts?

Electric SQL uses PostgreSQL as the single source of truth, so conflicts are resolved at the database level using standard SQL transactions. Client-side changes are queued and applied sequentially, ensuring consistency.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CRDT Sync Servers: Hocuspocus vs Automerge vs Electric SQL (2026)",
  "description": "Compare self-hosted CRDT sync servers for real-time collaborative applications. Hocuspocus, Automerge, and Electric SQL compared with Docker configs.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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