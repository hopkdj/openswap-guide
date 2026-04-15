---
title: "Self-Hosted Graph Databases: Neo4j vs ArangoDB vs NebulaGraph 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "database"]
draft: false
description: "Compare Neo4j, ArangoDB, and NebulaGraph for self-hosted graph database deployments. Docker setup guides, query language comparison, performance benchmarks, and real-world use cases."
---

## Why Self-Host a Graph Database

Graph databases excel at modeling and querying highly connected data — relationships are first-class citizens, not an afterthought computed via expensive JOINs at query time. They power recommendation engines, fraud detection pipelines, knowledge graphs, network topology maps, and social network analytics.

Self-hosting a graph database gives you complete control over your data:

- **Data sovereignty**: No third-party cloud vendor reads or monetizes your relationship data
- **Cost predictability**: Enterprise cloud graph databases charge per query or per connection — self-hosted pricing is a flat server cost regardless of query volume
- **Custom integrations**: Full access to the database engine, backup tooling, and monitoring APIs
- **Compliance**: Meet GDPR, HIPAA, or internal data residency requirements by keeping everything on your own infrastructure
- **Performance tuning**: Adjust memory allocation, storage engines, and replication factors to match your specific workload

Whether you are building a product recommendation system for an e-commerce store, modeling an IT infrastructure for a security audit, or running a knowledge graph over your organization's documentation, a self-hosted graph database is the right choice.

---

## What Is a Graph Database?

A graph database stores data as **nodes** (entities), **edges** (relationships), and **properties** (key-value pairs on both). Unlike relational databases where relationships are implicit (foreign keys resolved at query time), graph databases store relationships as physical pointers — traversing a million-hop path is essentially the same cost as a single hop.

### Core Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| **Node** | An entity or object | `User`, `Product`, `Server` |
| **Edge** | A directed relationship between two nodes | `FRIEND_OF`, `BOUGHT`, `CONNECTED_TO` |
| **Property** | Key-value data attached to a node or edge | `name: "Alice"`, `since: 2023` |
| **Label/Type** | Category classification for nodes or edges | `Person`, `Company` |
| **Path** | A sequence of connected nodes and edges | `Alice → FRIEND_OF → Bob → BOUGHT → Laptop` |

---

## The Three Contenders

### Neo4j — The Industry Standard

Neo4j is the most widely adopted graph database, created in 2007. It pioneered the property graph model and the Cypher query language. Available in a free Community Edition (self-hosted, single-node) and a paid Enterprise Edition (clustering, causal consistency, online backups).

**Best for**: Teams that need mature tooling, extensive documentation, and the widest ecosystem support.

### ArangoDB — The Multi-Model Contender

ArangoDB supports three data models in one engine: graph, document (JSON), and key-value. It uses AQL (ArangoDB Query Language), a SQL-like syntax extended with graph traversal operators. The open-source Community Edition is fully self-hostable and includes graph algorithms.

**Best for**: Teams that need graph capabilities alongside document storage without running separate databases.

### NebulaGraph — The Distributed Scale-Out Option

NebulaGraph is designed from the ground up for massive, distributed graph workloads. It separates compute (graphd), storage (storaged), and metadata (metad) into independent services, allowing each to scale horizontally. It uses nGQL, a SQL-inspired query language. The Community Edition is open source and fully self-hostable.

**Best for**: Large-scale deployments with billions of nodes and trillions of edges where horizontal scaling is non-negotiable.

---

## Feature Comparison

| Feature | Neo4j (Community) | ArangoDB (Community) | NebulaGraph (Community) |
|---------|:-----------------:|:--------------------:|:-----------------------:|
| **License** | GPL-3.0 | Apache-2.0 | Apache-2.0 |
| **Query Language** | Cypher | AQL | nGQL |
| **Data Model** | Property graph only | Multi-model (graph + document + key-value) | Property graph |
| **Architecture** | Single-node (CE) | Single-node or active-active cluster | Distributed (compute + storage separation) |
| **Max Graph Size** | ~34B nodes/edges (single node) | Limited by RAM/disk on single node | Virtually unlimited (horizontal scale) |
| **ACID Transactions** | ✅ Full | ✅ Full | ✅ Full |
| **Graph Algorithms** | ❌ (Enterprise only) | ✅ Built-in (Pregel framework) | ✅ via NebulaGraph Algorithm |
| **Full-Text Search** | ❌ (requires plugin) | ✅ Built-in | ⚠️ Via Elasticsearch plugin |
| **Web UI** | Neo4j Browser | ArangoDB Web UI | NebulaGraph Studio |
| **Docker Support** | ✅ Official image | ✅ Official image | ✅ Official compose |
| **Kubernetes** | ✅ Helm chart | ✅ Helm chart (KubeArangoDB) | ✅ Helm chart |
| **Language Drivers** | Java, Python, Go, .NET, JS, Rust | Java, Python, Go, .NET, JS, Rust, C# | Java, Python, Go, C++, Rust |
| **Import Tools** | `neo4j-admin`, APOC | `arangoimp` (CSV, JSON, TSV) | `nebula-importer` |

---

## Query Language Comparison

All three databases let you express the same fundamental operations, but the syntax differs significantly.

### Creating Nodes and Relationships

**Neo4j (Cypher)**:

```cypher
CREATE (alice:Person {name: "Alice", age: 30})
CREATE (bob:Person {name: "Bob", age: 25})
CREATE (laptop:Product {name: "ThinkPad X1", price: 1299})
CREATE (alice)-[:FRIEND_OF {since: 2020}]->(bob)
CREATE (alice)-[:BOUGHT {date: "2024-01-15"}]->(laptop)
```

**ArangoDB (AQL)**:

```aql
LET alice = INSERT { _key: "alice", name: "Alice", age: 30 } INTO Person
LET bob = INSERT { _key: "bob", name: "Bob", age: 25 } INTO Person
LET laptop = INSERT { _key: "laptop", name: "ThinkPad X1", price: 1299 } INTO Product
INSERT { _from: CONCAT("Person/", alice._key), _to: CONCAT("Person/", bob._key), since: 2020 } INTO FriendOf
INSERT { _from: CONCAT("Person/", alice._key), _to: CONCAT("Product/", laptop._key), date: "2024-01-15" } INTO Bought
```

**NebulaGraph (nGQL)**:

```ngql
INSERT VERTEX Person(name, age) VALUES "alice":("Alice", 30);
INSERT VERTEX Person(name, age) VALUES "bob":("Bob", 25);
INSERT VERTEX Product(name, price) VALUES "laptop":("ThinkPad X1", 1299);
INSERT EDGE friend_of(since) VALUES "alice"->"bob":(2020);
INSERT EDGE bought(date) VALUES "alice"->"laptop":("2024-01-15");
```

### Querying: Find All Products Bought by Friends of Alice

**Neo4j (Cypher)**:

```cypher
MATCH (alice:Person {name: "Alice"})-[:FRIEND_OF]->(friend)-[:BOUGHT]->(product)
RETURN friend.name, product.name, product.price
ORDER BY product.price DESC
```

**ArangoDB (AQL)**:

```aql
FOR alice IN Person
  FILTER alice.name == "Alice"
  FOR friend IN 1..1 OUTBOUND alice FriendOf
    FOR product IN 1..1 OUTBOUND friend Bought
      RETURN { friend: friend.name, product: product.name, price: product.price }
```

**NebulaGraph (nGQL)**:

```ngql
MATCH (alice:Person {name: "Alice"})-[:friend_of]->(friend:Person)-[:bought]->(product:Product)
RETURN friend.name, product.name, product.price
ORDER BY product.price DESC
```

### Key Takeaway

Cypher (Neo4j) has the most intuitive syntax — it visually resembles the graph you are querying. AQL (ArangoDB) feels closer to SQL with graph traversal extensions. nGQL (NebulaGraph) is also SQL-inspired but requires a schema definition phase before you can insert data.

---

## Self-Hosted Installation Guides

### Neo4j Community Edition

Neo4j Community runs as a single-node instance. It is straightforward to deploy with Docker.

```bash
# Create persistent data directories
mkdir -p ~/neo4j/{data,logs,import,plugins}

# Run Neo4j Community via Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -v ~/neo4j/data:/data \
  -v ~/neo4j/logs:/logs \
  -v ~/neo4j/import:/var/lib/neo4j/import \
  -v ~/neo4j/plugins:/plugins \
  -e NEO4J_AUTH=neo4j/selfhosted-password-2026 \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_apoc_import_file_use__neo4j__config=true \
  neo4j:5.26-community
```

After startup, access the web interface at `http://localhost:7474`. The default credentials are `neo4j` / `selfhosted-password-2026`.

**Docker Compose (persistent setup)**:

```yaml
services:
  neo4j:
    image: neo4j:5.26-community
    container_name: neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/my-strong-password
      - NEO4J_dbms_memory_heap_initial__size=1G
      - NEO4J_dbms_memory_heap_max__size=4G
      - NEO4J_dbms_tx__log_rotation_retention__policy=false
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
      - neo4j-import:/var/lib/neo4j/import
      - neo4j-plugins:/plugins

volumes:
  neo4j-data:
  neo4j-logs:
  neo4j-import:
  neo4j-plugins:
```

### ArangoDB Community Edition

ArangoDB supports both single-node and active-active cluster deployments.

```bash
# Run ArangoDB single node
docker run -d \
  --name arangodb \
  -p 8529:8529 \
  -e ARANGO_ROOT_PASSWORD=selfhosted-root-2026 \
  -v ~/arangodb/data:/var/lib/arangodb3 \
  -v ~/arangodb/apps:/var/lib/arangodb3-apps \
  arangodb:3.12-community
```

Access the web UI at `http://localhost:8529`.

**Docker Compose with ArangoDB**:

```yaml
services:
  arangodb:
    image: arangodb:3.12-community
    container_name: arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=my-root-password
      - ARANGO_NO_AUTH=0
    volumes:
      - arangodb-data:/var/lib/arangodb3
      - arangodb-apps:/var/lib/arangodb3-apps
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

volumes:
  arangodb-data:
  arangodb-apps:
```

### NebulaGraph Community Edition

NebulaGraph uses a multi-service architecture. The recommended approach is Docker Compose with the official template.

```bash
# Clone the official Docker Compose repository
git clone https://github.com/vesoft-inc/nebula-docker-compose.git
cd nebula-docker-compose

# Start the full cluster (graphd + storaged + metad)
docker compose up -d

# Verify the cluster is running
docker compose ps
```

**Custom Docker Compose**:

```yaml
services:
  metad0:
    image: vesoft/nebula-metad:v3.6.0
    environment:
      USER: root
    command:
      - --meta_server_addrs=metad0:9559
      - --local_ip=metad0
      - --ws_ip=metad0
      - --port=9559
      - --ws_http_port=19559
      - --data_path=/data/meta
      - --log_dir=/logs
    volumes:
      - ./data/meta0:/data/meta
      - ./logs/meta0:/logs
    networks:
      - nebula-net

  storaged0:
    image: vesoft/nebula-storaged:v3.6.0
    environment:
      USER: root
    depends_on:
      - metad0
    command:
      - --meta_server_addrs=metad0:9559
      - --local_ip=storaged0
      - --ws_ip=storaged0
      - --port=9779
      - --ws_http_port=19779
      - --data_path=/data/storage
      - --log_dir=/logs
    volumes:
      - ./data/storage0:/data/storage
      - ./logs/storage0:/logs
    networks:
      - nebula-net

  graphd:
    image: vesoft/nebula-graphd:v3.6.0
    environment:
      USER: root
    depends_on:
      - storaged0
    command:
      - --meta_server_addrs=metad0:9559
      - --port=9669
      - --local_ip=graphd
      - --ws_ip=graphd
      - --ws_http_port=19669
      - --log_dir=/logs
    ports:
      - "9669:9669"
      - "19669:19669"
    volumes:
      - ./logs/graph:/logs
    networks:
      - nebula-net

networks:
  nebula-net:
    driver: bridge
```

Connect to the cluster using the Nebula Console:

```bash
docker run --rm -it --network nebula-docker-compose_nebula-net \
  vesoft/nebula-console:v3.6.0 \
  --addr graphd --port 9669 --user root --password nebula
```

---

## Schema Design: Modeling a Social Network

To illustrate the practical differences, here is how you would model a social network with users, posts, likes, and follows in each database.

### Neo4j Schema

Neo4j is schema-free — you create nodes and relationships on the fly:

```cypher
-- Create users
CREATE (u1:User {id: 1, username: "alice", created_at: datetime()})
CREATE (u2:User {id: 2, username: "bob", created_at: datetime()})
CREATE (u3:User {id: 3, username: "charlie", created_at: datetime()})

-- Create posts
CREATE (p1:Post {id: 101, content: "Hello world!", created_at: datetime()})
CREATE (p2:Post {id: 102, content: "Graph databases are great", created_at: datetime()})

-- Create relationships
CREATE (u1)-[:FOLLOWS]->(u2)
CREATE (u1)-[:FOLLOWS]->(u3)
CREATE (u2)-[:FOLLOWS]->(u1)
CREATE (u1)-[:POSTED]->(p1)
CREATE (u2)-[:POSTED]->(p2)
CREATE (u1)-[:LIKES]->(p2)
CREATE (u3)-[:LIKES]->(p1)

-- Find all posts liked by people Alice follows
MATCH (alice:User {username: "alice"})-[:FOLLOWS]->(friend)-[:LIKES]->(post)
RETURN post.content, friend.username
```

### ArangoDB Schema

ArangoDB requires you to define vertex and edge collections:

```aql
-- Create collections (run in ArangoShell or web UI)
db._create("User")
db._create("Post")
db._createEdgeCollection("Follows")
db._createEdgeCollection("Likes")
db._createEdgeCollection("Posted")

-- Insert vertices
db.User.insert({ _key: "alice", id: 1, username: "alice" })
db.User.insert({ _key: "bob", id: 2, username: "bob" })
db.User.insert({ _key: "charlie", id: 3, username: "charlie" })
db.Post.insert({ _key: "p101", id: 101, content: "Hello world!" })
db.Post.insert({ _key: "p102", id: 102, content: "Graph databases are great" })

-- Insert edges
db.Follows.insert({ _from: "User/alice", _to: "User/bob" })
db.Follows.insert({ _from: "User/alice", _to: "User/charlie" })
db.Likes.insert({ _from: "User/alice", _to: "Post/p102" })

-- Query: posts liked by people Alice follows
FOR alice IN User
  FILTER alice.username == "alice"
  FOR friend IN 1..1 OUTBOUND alice Follows
    FOR post IN 1..1 INBOUND friend Likes
      RETURN { post: post.content, friend: friend.username }
```

### NebulaGraph Schema

NebulaGraph requires explicit schema definition before any data insertion:

```ngql
-- Create space (equivalent to a database)
CREATE SPACE social_network(partition_num=10, replica_factor=1);
USE social_network;

-- Create tags (node types)
CREATE TAG User(id int, username string);
CREATE TAG Post(id int, content string);

-- Create edge types
CREATE EDGE FOLLOWS();
CREATE EDGE LIKES();
CREATE EDGE POSTED();

-- Rebuild the index for tag and edge creation
REBUILD TAG INDEX;
REBUILD EDGE INDEX;

-- Insert data
INSERT VERTEX User(id, username) VALUES "u1":(1, "alice");
INSERT VERTEX User(id, username) VALUES "u2":(2, "bob");
INSERT VERTEX Post(id, content) VALUES "p101":(101, "Hello world!");

-- Create edges
INSERT EDGE FOLLOWS() VALUES "u1"->"u2":();
INSERT EDGE LIKES() VALUES "u1"->"p101":();

-- Query
MATCH (u:User)-[:FOLLOWS]->(f:User)-[:LIKES]->(p:Post)
WHERE u.username == "alice"
RETURN f.username, p.content
```

---

## Performance Characteristics

### When to Choose Each Database

| Scenario | Recommended | Why |
|----------|------------|-----|
| **Prototype / learn graph databases** | Neo4j | Best documentation, largest community, Cypher is intuitive |
| **Small to medium graphs (< 1B edges)** | Neo4j or ArangoDB | Single-node performance is excellent for moderate datasets |
| **Multi-model workloads** | ArangoDB | Graph + document + key-value in one engine reduces infrastructure complexity |
| **Large-scale graphs (10B+ edges)** | NebulaGraph | Horizontal scale-out with storage-compute separation |
| **Graph algorithms (PageRank, Louvain, shortest path)** | ArangoDB | Built-in Pregel framework in Community Edition |
| **Existing SQL team** | ArangoDB or NebulaGraph | AQL and nGQL are SQL-inspired and feel familiar |
| **Kubernetes-native deployment** | NebulaGraph | Purpose-built for cloud-native with independent service scaling |
| **Full-text search alongside graph** | ArangoDB | Built-in full-text indexes without additional services |

### Resource Requirements (Minimum)

| Database | RAM | CPU | Disk | Notes |
|----------|-----|-----|------|-------|
| **Neo4j CE** | 4 GB | 2 cores | 10 GB | JVM-based; heap size is the primary tuning knob |
| **ArangoDB** | 2 GB | 2 cores | 5 GB | RocksDB storage engine; V8 engine for AQL functions |
| **NebulaGraph** | 8 GB | 4 cores | 20 GB | Three services running; each needs its own resources |

---

## Backup and Recovery

### Neo4j

```bash
# Online backup using neo4j-admin (Enterprise only)
# Community Edition: use volume snapshots or docker volume backup

# Cold backup (stop the database first)
docker stop neo4j
tar czf neo4j-backup-$(date +%F).tar.gz -C ~/neo4j data logs
docker start neo4j

# Restore
docker stop neo4j
rm -rf ~/neo4j/data ~/neo4j/logs
tar xzf neo4j-backup-2026-04-15.tar.gz -C ~/neo4j
docker start neo4j
```

### ArangoDB

```bash
# Logical backup with arangodump
docker exec arangodb arangodump \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.username root \
  --server.password my-root-password \
  --output-directory /tmp/backup

# Copy backup out of container
docker cp arangodb:/tmp/backup ~/arangodb-backups/$(date +%F)

# Restore with arangorestore
docker exec arangodb arangorestore \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.username root \
  --server.password my-root-password \
  --input-directory /tmp/backup
```

### NebulaGraph

```bash
# Full backup using nebula-br (backup and restore tool)
docker run --rm --network host \
  -v ~/nebula-backup:/backup \
  vesoft/nebula-br:v3.6.0 \
  backup full \
  --meta "metad0:9559" \
  --storage "127.0.0.1:9779" \
  --target /backup/full-$(date +%F)

# Restore
docker run --rm --network host \
  -v ~/nebula-backup:/backup \
  vesoft/nebula-br:v3.6.0 \
  restore \
  --meta "metad0:9559" \
  --storage "127.0.0.1:9779" \
  --backup /backup/full-2026-04-15
```

---

## Monitoring

All three databases expose metrics that integrate with Prometheus and Grafana.

### Neo4j Metrics

```yaml
# Add JMX exporter sidecar to Docker Compose
  neo4j-exporter:
    image: bitnami/jmx-exporter:latest
    ports:
      - "5556:5556"
    volumes:
      - ./jmx-config.yml:/opt/bitnami/jmx-exporter/config.yml
    depends_on:
      - neo4j
```

### ArangoDB Metrics

ArangoDB includes a built-in `_admin/metrics` endpoint:

```bash
# Scrape metrics from Prometheus
curl http://localhost:8529/_admin/metrics
```

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: arangodb
    static_configs:
      - targets: ["localhost:8529"]
    metrics_path: /_admin/metrics
    basic_auth:
      username: root
      password: my-root-password
```

### NebulaGraph Metrics

```yaml
scrape_configs:
  - job_name: nebula-graphd
    static_configs:
      - targets: ["localhost:19669"]
  - job_name: nebula-storaged
    static_configs:
      - targets: ["localhost:19779"]
  - job_name: nebula-metad
    static_configs:
      - targets: ["localhost:19559"]
```

---

## Security Hardening

Regardless of which database you choose, follow these practices for production self-hosted deployments:

1. **Never use default passwords** — change all default credentials immediately after first startup
2. **Bind to localhost or internal network only** — use a reverse proxy (Traefik, Caddy, or Nginx Proxy Manager) for external access with TLS termination
3. **Enable TLS for client connections** — all three support encrypted connections between clients and the database server
4. **Restrict network access** — use firewall rules to limit which IPs can reach database ports
5. **Enable audit logging** — track all queries and administrative actions for compliance
6. **Regular backups** — automate daily backups and test restoration procedures monthly
7. **Keep the database updated** — graph databases receive regular security patches; subscribe to release notifications

### Example: Reverse Proxy with Caddy

```caddyfile
graph.example.com {
  reverse_proxy localhost:7474
  tls internal
  encode gzip
}

arangodb.example.com {
  reverse_proxy localhost:8529
  tls internal
  encode gzip
}

nebula.example.com:9669 {
  # Note: NebulaGraph uses binary protocol on 9669
  # Use TCP reverse proxy (not HTTP) for production
}
```

---

## Migration Between Graph Databases

If you need to migrate data between databases, the recommended approach is:

1. **Export to a neutral format** — CSV or JSON with explicit node and edge files
2. **Transform the data** — adapt property names, types, and relationship directions
3. **Import into the target** — use the target database's bulk import tool

### Example: Export from Neo4j to CSV

```cypher
-- Export nodes
CALL apoc.export.csv.all("/var/lib/neo4j/import/export.csv", {useTypes: true})

-- Or export specific node types
CALL apoc.export.csv.query(
  "MATCH (n:Person) RETURN n.id, n.name, n.age",
  "persons.csv",
  {useTypes: true}
)
```

### Example: Import CSV into NebulaGraph

```yaml
# nebula-importer config (config.yaml)
version: v3
description: Import from Neo4j export
clientSettings:
  retry: 3
  concurrency: 10
  channelBufferSize: 128
  space: social_network
  connection:
    user: root
    password: nebula
    address: graphd:9669
  postStart:
    commands: |
      UPDATE CONFIGS storage:wal_ttl=3600
  preStop:
    commands: |
      UPDATE CONFIGS storage:wal_ttl=86400
logPath: ./importer.log
files:
  - path: ./persons.csv
    failDataPath: ./persons.err
    batchSize: 256
    type: csv
    csv:
      withHeader: true
      withLabel: false
    schema:
      type: vertex
      vertex:
        vid:
          type: string
          index: 0
        tags:
          - name: Person
            props:
              - name: id
                type: int
                index: 1
              - name: name
                type: string
                index: 2
```

```bash
nebula-importer --config config.yaml
```

---

## Final Verdict

**Choose Neo4j** if you value the largest ecosystem, the most intuitive query language, and have a dataset that fits on a single node. It is the safest choice for teams new to graph databases. The Community Edition is sufficient for development, prototyping, and moderate production workloads.

**Choose ArangoDB** if you need graph capabilities alongside document or key-value storage in a single engine. Its built-in graph algorithms, full-text search, and SQL-like query language make it the most versatile option. The active-active cluster mode (Enterprise) provides high availability.

**Choose NebulaGraph** if you are dealing with massive graphs that exceed single-node capacity. Its storage-compute separation architecture, horizontal scalability, and cloud-native design make it the only practical choice for billion-node, trillion-edge graphs at scale.

All three are production-ready, open source, and fully self-hostable. The best choice depends on your data volume, team expertise, and infrastructure requirements.
