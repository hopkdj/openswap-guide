---
title: "Self-Hosted Blockchain Data Indexers: The Graph vs Subsquid vs SubQuery"
date: "2026-06-15"
tags: ["blockchain", "data-indexing", "graphql", "web3", "infrastructure", "analytics"]
draft: false
---

## Introduction

Blockchain data is inherently unstructured. Smart contract events, transaction logs, and state changes are optimized for consensus, not queryability. Anyone building a dApp dashboard, analytics platform, or DeFi protocol needs to transform raw on-chain data into a structured, queryable format. This is where blockchain indexers come in.

Rather than relying on centralized indexing services with rate limits and monthly fees, self-hosting gives you complete control over your data pipeline. This guide compares three leading open-source blockchain indexers: **The Graph** (Graph Node), the established standard; **Subsquid**, a TypeScript-native indexing SDK; and **SubQuery**, a universal multi-chain indexing framework.

## Comparison Table

| Feature | The Graph (Graph Node) | Subsquid | SubQuery |
|---|---|---|---|
| **Stars** | 3,138 | 1,330 | 18,792 |
| **Language** | Rust | TypeScript | TypeScript |
| **License** | Apache 2.0 | Apache 2.0 | GPL v3 |
| **Query Language** | GraphQL | TypeScript SDK | GraphQL |
| **Chains Supported** | 40+ (Ethereum, IPFS, etc.) | 70+ (EVM, Substrate, Solana) | 100+ (EVM, Cosmos, Algorand) |
| **Indexing Model** | AssemblyScript mappings | TypeScript processors | TypeScript mappings |
| **Database Backend** | PostgreSQL | PostgreSQL, S3+Parquet | PostgreSQL |
| **Docker Support** | Official compose.yml | Official Dockerfile | Helm charts |
| **Decentralized Network** | Yes (hosted service + network) | No (standalone) | Yes (managed service available) |
| **Real-time Indexing** | Yes (Firehose) | Yes (batch+stream) | Yes (batch) |
| **RPC Requirements** | Full archive node | Archive node or RPC provider | Full/archive node |

## Self-Hosted Blockchain Indexer Deployment

### The Graph (Graph Node): The Established Standard

The Graph is the most widely adopted blockchain indexing protocol, powering data queries for Uniswap, Aave, Synthetix, and thousands of other dApps. Its architecture separates indexing logic (AssemblyScript subgraph mappings) from the indexing infrastructure (Graph Node + PostgreSQL).

```yaml
# docker-compose.yml for Graph Node
version: "3"
services:
  graph-node:
    image: graphprotocol/graph-node
    ports:
      - "8000:8000"
      - "8001:8001"
      - "8020:8020"
      - "8030:8030"
      - "8040:8040"
    depends_on:
      - ipfs
      - postgres
    environment:
      postgres_host: postgres
      postgres_user: graph-node
      postgres_pass: let-me-in
      postgres_db: graph-node
      ipfs: "ipfs:5001"
      ethereum: "mainnet:https://YOUR_ETHEREUM_RPC"
      GRAPH_LOG: info
      GRAPH_ETHEREUM_MAX_BLOCK_RANGE_SIZE: 2000

  ipfs:
    image: ipfs/kubo:latest
    ports:
      - "5001:5001"
    volumes:
      - ./ipfs-data:/data/ipfs

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: graph-node
      POSTGRES_PASSWORD: let-me-in
      POSTGRES_DB: graph-node
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    command: ["postgres", "-c", "shared_preload_libraries=pg_stat_statements"]
```

```bash
# Deploy Graph Node
docker compose up -d

# Deploy a subgraph to the node
graph create my-subgraph --node http://localhost:8020
graph deploy my-subgraph   --ipfs http://localhost:5001   --node http://localhost:8020
```

The Graph's key advantage is its **mature ecosystem**. Hundreds of pre-built subgraphs are available on the decentralized network, and the AssemblyScript mapping language is well-documented. If your dApp needs to index standard DeFi events (swaps, mints, burns, transfers), there's likely a subgraph template that handles 80% of the work.

However, The Graph's architecture can be resource-intensive. A full Graph Node with complete Ethereum mainnet indexing requires a dedicated PostgreSQL instance with at least 500GB of storage and a powerful CPU for processing blocks in parallel. The Firehose integration for real-time indexing adds another layer of infrastructure complexity.

### Subsquid: TypeScript-First Indexing

Subsquid takes a developer-centric approach, replacing GraphQL schema definitions and AssemblyScript mappings with pure TypeScript. You write data processors, transformations, and API endpoints in a single language, with full access to the npm ecosystem.

```bash
# Install Subsquid CLI and create a project
npm install -g @subsquid/cli
sqd init my-squid --template evm
cd my-squid
npm install

# Define your data model in schema.graphql
cat > schema.graphql << 'EOF'
type Transfer @entity {
  id: ID!
  from: String! @index
  to: String! @index
  amount: BigInt!
  block: Int!
  timestamp: DateTime!
}
EOF

# Write the processor in TypeScript
# The processor.ts file handles block fetching, event filtering, and data transformation

# Run the squid locally
sqd up     # Start PostgreSQL
sqd build  # Compile TypeScript
sqd migrate  # Create database schema
sqd process  # Start indexing
```

```bash
# Deploy with Docker
docker build -t my-squid .
docker run -d   --name my-squid   -e DB_HOST=postgres   -e DB_PORT=5432   -e RPC_ENDPOINT=https://YOUR_ETHEREUM_RPC   -p 4000:4000   my-squid
```

Subsquid's standout feature is its **batch processing model with S3+Parquet archival**. Indexed data is stored both in PostgreSQL for real-time queries and exported to S3-compatible storage in Apache Parquet format for cost-effective long-term archival and analytical queries. This dual-storage architecture is unique among blockchain indexers and makes Subsquid particularly attractive for data analytics workloads.

The SDK supports 70+ chains including EVM, Substrate, Solana, and Fuel, with a unified programming model across all chains. The data sourcing layer is separated from the processing layer, so you can switch between RPC providers, Subsquid's own Archives service, or self-hosted archive nodes without changing your processor code.

### SubQuery: The Universal Indexer

SubQuery is the most starred blockchain indexing framework (18,792 stars), positioning itself as a universal data indexing platform. Its key differentiator is multi-chain support spanning 100+ networks including EVM chains, Cosmos zones, Algorand, NEAR, and Polkadot parachains — all through a single unified SDK.

```yaml
# SubQuery node docker-compose.yml
version: "3"
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  subquery-node:
    image: onfinality/subql-node:latest
    depends_on:
      postgres:
        condition: service_healthy
    restart: always
    environment:
      DB_USER: postgres
      DB_PASS: postgres
      DB_DATABASE: postgres
      DB_HOST: postgres
      DB_PORT: 5432
    volumes:
      - ./project.yaml:/app/project.yaml
      - ./schema.graphql:/app/schema.graphql
      - ./dist:/app/dist
    command:
      - -f=/app
      - --db-schema=app
      - --workers=4
      - --batch-size=30
      - --unfinalized-blocks=true

  graphql-engine:
    image: onfinality/subql-query:latest
    ports:
      - "3000:3000"
    depends_on:
      - postgres
      - subquery-node
    restart: always
    environment:
      DB_USER: postgres
      DB_PASS: postgres
      DB_DATABASE: postgres
      DB_HOST: postgres
      DB_PORT: 5432
    command:
      - --name=app
      - --playground
      - --indexer=http://subquery-node:3000
```

```bash
# Deploy SubQuery
docker compose up -d

# Access the GraphQL playground at http://localhost:3000
```

SubQuery's architecture separates the indexing node from the query service, allowing each to scale independently. The indexing node processes blocks in parallel using configurable worker threads, while the GraphQL query engine serves API requests efficiently. This separation means you can run multiple query engines behind a load balancer for production deployments.

The multi-chain SDK is SubQuery's strongest selling point. If your project spans multiple blockchains (e.g., a cross-chain bridge analytics dashboard), you can use the same TypeScript mapping patterns, the same GraphQL schema definitions, and the same deployment infrastructure across all chains. This dramatically reduces the learning curve compared to maintaining separate indexing pipelines for each chain.

## Deployment Architecture and Scaling

All three indexers use PostgreSQL as their primary database, which means standard PostgreSQL administration practices apply: regular VACUUM operations, connection pooling via PgBouncer, and WAL archiving for disaster recovery. The database is typically the bottleneck — not the indexer process itself.

**RPC infrastructure** is the second critical dependency. Blockchain indexers need reliable, high-throughput access to archive nodes. Rate-limited public RPC endpoints will cause indexing to fall behind the chain tip. Self-hosting an archive node (like Erigon or Reth for Ethereum) alongside the indexer eliminates this dependency but requires 2-4TB of NVMe storage.

**Caching strategy** varies: The Graph uses IPFS for subgraph deployment artifacts, Subsquid uses S3+Parquet for cost-effective archival queries, and SubQuery relies entirely on PostgreSQL for both hot and cold data. For high-volume production deployments, consider adding Redis caching in front of the GraphQL endpoint and using PostgreSQL read replicas for query scaling.

For related blockchain infrastructure, see our [Ethereum node clients guide](../2026-05-03-geth-vs-erigon-vs-reth-self-hosted-ethereum-node-clients-guide-2026/) and our [self-hosted blockchain explorers comparison](../2026-05-03-self-hosted-blockchain-explorers-blockscout-otterscan-solana-explorer-guide/). For decentralized storage, check our [IPFS vs Storj vs Sia guide](../2026-04-25-ipfs-vs-storj-vs-sia-self-hosted-decentralized-storage-guide-2026/).

## FAQ

### Do I need an archive node for blockchain indexing?
For full historical indexing, yes. Standard full nodes prune state that's older than 128 blocks, which means you can only index recent transactions. Archive nodes preserve all historical state and are necessary for indexing from genesis. However, most indexers support "fast sync" modes that use third-party archive data for initial backfill, then switch to a local full node for ongoing indexing.

### How much storage does a production indexer need?
For Ethereum mainnet with popular DeFi subgraphs: 500GB-2TB of PostgreSQL storage, depending on the number of indexed contracts and retention period. Subsquid's S3+Parquet archival can reduce active PostgreSQL storage by 80% by moving older data to cheap object storage.

### Can I use these indexers for private or permissioned chains?
Yes. All three support custom chain configurations. Polygon Edge chains, Hyperledger Besu networks, and Quorum deployments can be indexed by specifying the custom chain ID, RPC endpoint, and block format in the project configuration.

### What's the latency between an on-chain event and it appearing in the index?
With optimized configurations: The Graph (with Firehose) achieves sub-second latency. Subsquid's batch model has 2-10 second latency depending on batch size. SubQuery typically has 6-30 second latency. For real-time dApp UIs, WebSocket subscriptions to the indexer provide instant UI updates after block confirmation.

### Can I query across multiple chains with a single indexer instance?
SubQuery supports this natively through its multi-chain SDK — you define separate project manifests for each chain but use the same indexing infrastructure. Subsquid supports multi-chain queries through separate squid processes that share a common API layer. The Graph requires separate subgraph deployments per chain.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Blockchain Data Indexers: The Graph vs Subsquid vs SubQuery",
  "description": "Compare self-hosted blockchain data indexing solutions: The Graph (Graph Node), Subsquid, and SubQuery. Learn Docker Compose deployment, multi-chain support, and production scaling.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
