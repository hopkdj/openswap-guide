---
title: "Self-Hosted Real-Time Databases: RethinkDB vs GunDB vs RxDB"
date: "2026-06-17"
tags: ["database", "realtime", "self-hosted", "rethinkdb", "gundb", "rxdb", "nosql", "opensource"]
draft: false
---

## Introduction

Real-time applications — from collaborative editors to live dashboards and multiplayer games — require databases that can push changes to clients the moment they happen. Traditional polling architectures waste bandwidth and add latency. Self-hosted real-time databases solve this by maintaining persistent connections and streaming updates directly to subscribers.

In this guide, we compare three leading open-source real-time databases: **RethinkDB**, the original real-time database with a powerful query language; **GunDB**, a decentralized graph database that syncs peer-to-peer; and **RxDB**, a local-first reactive database that replicates with existing backends.

## Comparison Table

| Feature | RethinkDB | GunDB | RxDB |
|---------|-----------|-------|------|
| **Architecture** | Client-server with changefeeds | Decentralized P2P mesh | Local-first with replication |
| **Query Language** | ReQL (fluent API) | Gun chain API | RxJS-based reactive queries |
| **Consistency Model** | Strong consistency | Eventually consistent (CRDT-based) | Eventually consistent (CRDT-based) |
| **Offline Support** | Limited | Full offline-first | Full offline-first |
| **Scaling Model** | Sharding + replication | P2P relay network | Client-side + server sync |
| **GitHub Stars** | ~27,000 | ~19,000 | ~23,000 |
| **Language** | C++, JavaScript, Python drivers | JavaScript (Node.js) | TypeScript |
| **Docker Support** | Official image available | Community images | Server plugin available |
| **License** | Apache 2.0 | MIT / Zlib | Apache 2.0 |

## RethinkDB: The Changefeed Pioneer

RethinkDB pioneered the concept of *changefeeds* — continuous queries that push real-time updates to connected clients. Instead of polling `SELECT * FROM table WHERE updated > last_check`, you simply subscribe to a changefeed:

```javascript
r.table('messages')
  .changes()
  .run(conn, (err, cursor) => {
    cursor.each((err, row) => {
      io.emit('message', row.new_val);
    });
  });
```

RethinkDB uses a custom query language called ReQL, which chains operations fluently:

```javascript
r.table('users')
  .filter(r.row('age').gt(18))
  .orderBy(r.desc('score'))
  .limit(10)
  .run(conn);
```

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  rethinkdb:
    image: rethinkdb:latest
    container_name: rethinkdb
    ports:
      - "8080:8080"   # Web admin UI
      - "28015:28015" # Client driver port
      - "29015:29015" # Cluster port
    volumes:
      - rethinkdb_data:/data
    command: rethinkdb --bind all --cache-size 2048

volumes:
  rethinkdb_data:
```

RethinkDB includes a built-in web administration dashboard at port 8080, making cluster management straightforward.

**Strengths:**
- Battle-tested query language with joins, aggregations, and geospatial queries
- Built-in web admin UI for monitoring and sharding
- Strong consistency guarantees for critical data
- Active community fork (rethinkdb/rethinkdb) maintained after company closure

**Limitations:**
- No built-in offline support — clients must stay connected
- Requires server infrastructure (not P2P)
- Smaller ecosystem than MongoDB or PostgreSQL

## GunDB: The Decentralized Graph

GunDB takes a fundamentally different approach: instead of a central server, it creates a peer-to-peer mesh network where every node can store and sync data. GunDB uses Conflict-Free Replicated Data Types (CRDTs) to handle concurrent edits without conflicts:

```javascript
const Gun = require('gun');
const gun = Gun({ peers: ['http://server1:8765/gun', 'http://server2:8765/gun'] });

// Write data — automatically syncs to all peers
gun.get('users').get('alice').put({
  name: 'Alice',
  online: true
});

// Subscribe to real-time changes
gun.get('users').get('alice').on((data) => {
  console.log('Alice updated:', data);
});
```

GunDB stores data as a graph, making it natural for relational data without JOINs:

```javascript
// Create relationships
gun.get('posts').get('post1').put({ title: 'Hello World' });
gun.get('users').get('alice').get('posts').set(gun.get('posts').get('post1'));
```

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  gun-relay:
    image: ghcr.io/amark/gun:latest
    container_name: gun-relay
    ports:
      - "8765:8765"
    environment:
      - GUN_ENV=production
    volumes:
      - gun_data:/data

volumes:
  gun_data:
```

**Strengths:**
- Built-in offline-first — works without internet, syncs when reconnected
- Decentralized architecture with no single point of failure
- Military-grade encryption (SEA — Security, Encryption, Authorization)
- Zero-dependency — can run in browsers, Node.js, and React Native

**Limitations:**
- Eventual consistency may not suit all use cases
- Custom query API (not SQL-compatible)
- Community is smaller than RethinkDB/RxDB

## RxDB: Local-First Reactive Database

RxDB is a local-first database that runs inside the client application (browser, Node.js, React Native) and replicates with any backend. It uses RxJS Observables for reactive queries, meaning your UI automatically updates when data changes:

```typescript
import { createRxDatabase } from 'rxdb';

const db = await createRxDatabase({ name: 'myapp', storage: getRxStorageDexie() });

await db.addCollections({
  todos: {
    schema: {
      version: 0,
      type: 'object',
      properties: {
        id: { type: 'string' },
        title: { type: 'string' },
        completed: { type: 'boolean' }
      }
    }
  }
});

// Reactive query — updates automatically
db.todos.find({ selector: { completed: false } }).$.subscribe(todos => {
  console.log('Active todos:', todos);
});
```

RxDB supports multiple replication protocols, including CouchDB sync, GraphQL, WebSocket, and custom backends:

```typescript
// Sync with CouchDB backend
const replicationState = db.todos.syncCouchDB({
  remote: 'http://couchdb:5984/todos',
  direction: { push: true, pull: true },
  live: true
});
```

### Server-Side RxDB with Express

```javascript
const express = require('express');
const { createRxDatabase, getRxStorageDexie } = require('rxdb');

const app = express();
app.use(express.json());

const db = await createRxDatabase({ name: 'server', storage: getRxStorageDexie() });
await db.addCollections({ /* schemas */ });

app.get('/api/todos', async (req, res) => {
  const docs = await db.todos.find().exec();
  res.json(docs);
});
```

**Strengths:**
- Full offline-first with conflict resolution
- Works with any backend — CouchDB, GraphQL, REST, custom
- Encryption, compression, and attachments built in
- JSON Schema validation for data integrity
- Largest community (23K+ stars, active development as of June 2026)

**Limitations:**
- Client-centric — server-side usage requires additional setup
- Schema required (not schemaless)
- Storage abstraction adds complexity for simple use cases

## Choosing the Right Real-Time Database

Different use cases call for different architectures. Consider these scenarios:

- **Choose RethinkDB** if you need a traditional server-side database with powerful queries, changefeeds for real-time UI, and a built-in admin dashboard. Best for collaborative dashboards, live analytics, and applications where the server is the source of truth.

- **Choose GunDB** if you need decentralized architecture with offline-first capability and built-in encryption. Best for peer-to-peer applications, field-deployed systems with intermittent connectivity, and privacy-focused apps that can't rely on a central server.

- **Choose RxDB** if you're building a modern web or mobile application that needs local-first data with reactive UI bindings. Best for Progressive Web Apps (PWAs), mobile apps with offline mode, and applications that need to sync with existing backends like CouchDB or GraphQL.

## Why Self-Host Your Real-Time Database?

Running your own real-time database infrastructure gives you complete control over data locality, latency, and privacy. Unlike managed cloud services that charge per-operation or per-connection, self-hosted databases have predictable costs tied to your own hardware. For applications handling sensitive real-time data — healthcare monitoring, financial dashboards, or industrial IoT — keeping data on-premises eliminates third-party access risks.

The open-source nature of RethinkDB, GunDB, and RxDB means you can audit the code for security vulnerabilities, customize behavior for your workload, and avoid vendor lock-in. RethinkDB's community fork continues to receive updates years after the original company closed, demonstrating the resilience of open-source ecosystems. For related database infrastructure, see our guide on [self-hosted graph databases](../self-hosted-graph-databases-neo4j-arangodb-nebulagraph-guide-2026/). If you need version-controlled database capabilities, check out our [version-controlled databases comparison](../2026-04-21-dolt-vs-terminusdb-vs-couchdb-version-controlled-databases-guide-2026/).

For teams evaluating real-time infrastructure, the total cost of ownership for self-hosted databases is typically 40-60% lower than equivalent cloud services over a three-year period, especially at scale where per-connection pricing becomes prohibitive.

## FAQ

### Is RethinkDB still maintained after the company shut down?

Yes. The open-source community maintains RethinkDB under the original `rethinkdb/rethinkdb` repository. It receives updates, bug fixes, and performance improvements. The project remains stable and production-ready, with an active community forum and documentation.

### Can GunDB handle large datasets with millions of records?

GunDB is optimized for real-time synchronization of frequently accessed data rather than bulk storage. For millions of records, you would typically use GunDB as a sync layer for hot data while keeping cold data in a traditional database. The P2P architecture means each peer only stores data it has accessed, reducing per-node storage requirements.

### How does RxDB handle conflicts when multiple users edit the same data offline?

RxDB uses CRDT-based conflict resolution through its replication protocol. When two users edit the same document while offline and then sync, RxDB applies a deterministic merge strategy. For CouchDB replication, it uses CouchDB's built-in revision-based conflict resolution. You can also implement custom conflict handlers.

### What are the hardware requirements for running these databases?

RethinkDB recommends 2GB+ RAM for production deployments, with additional memory proportional to dataset size. GunDB relays are lightweight (512MB RAM for moderate loads). RxDB server components are minimal, as the heavy lifting happens client-side. All three run comfortably on modest VPS instances or Raspberry Pi 4+ for small deployments.

### Can I use these databases with Kubernetes?

Yes. All three databases can be deployed on Kubernetes. RethinkDB has official Helm charts. GunDB relays are stateless and ideal for horizontal scaling. RxDB server components can be deployed as standard Node.js containers. RethinkDB's native sharding integrates well with StatefulSet patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Real-Time Databases: RethinkDB vs GunDB vs RxDB",
  "description": "Comprehensive comparison of open-source real-time databases RethinkDB, GunDB, and RxDB for self-hosted deployments. Includes Docker Compose configs, code examples, and use case guidance.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
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
