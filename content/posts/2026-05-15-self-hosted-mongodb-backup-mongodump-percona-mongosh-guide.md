---
title: "Self-Hosted MongoDB Backup Solutions: mongodump vs Percona Backup vs Mongosh"
date: "2026-05-15"
tags: ["mongodb", "backup", "database", "disaster-recovery"]
draft: false
---

MongoDB stores critical application data — user profiles, transaction records, content catalogs, and operational logs. Without a reliable backup strategy, hardware failures, operator errors, or software bugs can result in irreversible data loss. This guide compares three self-hosted MongoDB backup approaches: the built-in **mongodump** utility, **Percona Backup for MongoDB** (enterprise-grade consistency), and **Mongosh-based scripting** (flexible custom backups).

We will cover installation, Docker Compose deployments, backup consistency guarantees, recovery procedures, and the trade-offs between each approach.

## mongodump: The Built-In Backup Utility

mongodump is MongoDB's official logical backup tool, shipped with every MongoDB installation. It connects to a running MongoDB instance, reads all data, and writes BSON files to disk.

### How It Works

mongodump iterates through every collection in every database, issuing queries to retrieve all documents. The output is a directory structure of BSON and JSON metadata files that can be restored using mongorestore. For replica sets, mongodump can connect to any member (primary or secondary) and will read from the connected node.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  mongodb:
    image: mongo:7
    command: ["--replSet", "rs0", "--bind_ip_all"]
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: SecureMongoPass123
    volumes:
      - mongodb-data:/data/db
      - ./init-replica.js:/docker-entrypoint-initdb.d/init-replica.js:ro

  mongobackup:
    image: mongo:7
    command: >
      mongodump --host mongodb:27017
      --username admin --password SecureMongoPass123
      --authenticationDatabase admin
      --gzip --archive=/backup/mongodump-DATESTAMP.gz
    volumes:
      - ./backups:/backup
    depends_on:
      - mongodb

volumes:
  mongodb-data:
```

Initialization script (`init-replica.js`) to set up a single-node replica set (required for oplog-based backups):

```javascript
rs.initiate({
  _id: "rs0",
  members: [{ _id: 0, host: "mongodb:27017" }]
});
```

### Running Backups

```bash
# Full backup with compression
docker compose run mongobackup

# Backup a specific database
docker compose run mongobackup mongodump   --host mongodb:27017   --username admin --password SecureMongoPass123   --authenticationDatabase admin   --db production --gzip   --archive=/backup/production-backup.gz

# Backup with query filter
docker compose run mongobackup mongodump   --host mongodb:27017   --username admin --password SecureMongoPass123   --db production --collection users   --query '{"status": "active"}'   --gzip --archive=/backup/active-users.gz
```

### Consistency and Limitations

mongodump provides **eventually consistent** snapshots by default. Because it reads collections sequentially, writes that occur during the backup may be partially captured. For point-in-time consistency, you must use it against a secondary with `--oplog`, which captures the oplog during the dump and allows mongorestore to replay changes up to a consistent point.

Key limitations:
- No built-in scheduling or retention management
- No incremental backups (each run is a full dump)
- Consistency requires oplog access (replica set or sharded cluster)
- Large databases can take hours to dump, during which the database is not locked

## Percona Backup for MongoDB: Enterprise-Grade Consistency

Percona Backup for MongoDB (PBM) is an open-source tool designed for consistent, point-in-time backups of MongoDB replica sets and sharded clusters. It coordinates backups across all nodes, captures oplog data, and supports incremental backups with configurable retention policies.

### How It Works

PBM installs an agent on each MongoDB node. A central PBM controller coordinates backup operations across agents, ensuring all nodes start and stop at consistent points. It stores backups in S3-compatible object storage or local filesystem, and supports full, incremental, and point-in-time recovery.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  mongodb-rs1:
    image: mongo:7
    command: ["--replSet", "rs0", "--bind_ip_all"]
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: SecureMongoPass123
    volumes:
      - mongo-rs1-data:/data/db
      - ./init-replica.js:/docker-entrypoint-initdb.d/init-replica.js:ro

  pbm-agent:
    image: percona/percona-backup-mongodb:latest
    environment:
      PBM_MONGODB_URI: "mongodb://admin:SecureMongoPass123@mongodb-rs1:27017/?authSource=admin&replicaSet=rs0"
    depends_on:
      - mongodb-rs1

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minio-secret-key
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data

volumes:
  mongo-rs1-data:
  minio-data:
```

### PBM Configuration

After starting the services, configure PBM to use your S3-compatible storage:

```bash
# Connect to the PBM agent container
docker compose exec pbm-agent pbm config --file /tmp/pbm-config.yaml
```

PBM configuration file (`pbm-config.yaml`):

```yaml
storage:
  type: s3
  s3:
    region: us-east-1
    bucket: mongo-backups
    prefix: ""
    credentials:
      access-key-id: minioadmin
      secret-access-key: minio-secret-key
    endpointUrl: http://minio:9000
    forcePathStyle: true
```

### Running Backups with PBM

```bash
# Start a full backup
docker compose exec pbm-agent pbm backup

# List available backups
docker compose exec pbm-agent pbm list

# Restore to a specific backup
docker compose exec pbm-agent pbm restore 2026-05-15T10:30:00Z

# Point-in-time recovery
docker compose exec pbm-agent pbm restore --time 2026-05-15T10:30:00Z

# Set retention policy (keep backups for 30 days)
docker compose exec pbm-agent pbm config --set "storage.s3.backupRetentionDays=30"
```

### Consistency Guarantees

PBM provides **strictly consistent** point-in-time snapshots. It coordinates across all replica set members to ensure a consistent view of data at the backup start time. The oplog is captured continuously, enabling recovery to any second within the oplog window. Incremental backups reduce storage usage by only capturing changes since the last full or incremental backup.

## Mongosh-Based Custom Backup Scripting

Mongosh (the MongoDB Shell) can be used to create custom backup scripts that leverage JavaScript/JavaScript-compatible syntax for flexible, application-aware backups. This approach is ideal when you need selective backups, data transformations, or integration with external systems.

### How It Works

Instead of dumping all data blindly, mongosh scripts can filter collections, aggregate data before export, apply transformations, and integrate with backup destinations (S3, GCS, local storage). The script runs as a scheduled job (cron, systemd timer) and can be tailored to specific business requirements.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  mongodb:
    image: mongo:7
    command: ["--replSet", "rs0", "--bind_ip_all"]
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: SecureMongoPass123
    volumes:
      - mongodb-data:/data/db

  backup-runner:
    image: mongo:7
    entrypoint: ["mongosh"]
    command: >
      "mongodb://admin:SecureMongoPass123@mongodb:27017/?authSource=admin"
      --eval '
        const dbs = db.adminCommand({ listDatabases: 1 }).databases;
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        dbs.forEach(d => {
          if (d.name === "admin" || d.name === "local" || d.name === "config") return;
          const collections = db.getSiblingDB(d.name).getCollectionNames();
          collections.forEach(col => {
            const count = db.getSiblingDB(d.name).getCollection(col).countDocuments();
            if (count > 0) {
              print(`Backing up ${d.name}.${col}: ${count} documents`);
            }
          });
        });
        print("Backup metadata scan complete");
      '
    volumes:
      - ./backup-scripts:/scripts:ro
      - ./backup-data:/backup
    depends_on:
      - mongodb

volumes:
  mongodb-data:
```

### Advanced Backup Script Example

Create a file `backup-script.js`:

```javascript
// backup-script.js - Custom MongoDB backup with filtering
const timestamp = new Date().toISOString().split('T')[0];
const backupDir = `/backup/${timestamp}`;

// List databases to backup
const targetDbs = ['production', 'analytics', 'sessions'];

targetDbs.forEach(dbName => {
  const db = db.getSiblingDB(dbName);
  const collections = db.getCollectionNames();
  
  collections.forEach(colName => {
    // Skip system collections
    if (colName.startsWith('system.')) return;
    
    const count = db.getCollection(colName).countDocuments();
    print(`${dbName}.${colName}: ${count} documents`);
    
    if (count > 0 && count < 10000000) {
      // Export to JSON for small collections
      const cursor = db.getCollection(colName).find();
      let docs = [];
      cursor.forEach(doc => {
        doc._id = doc._id.toString();
        docs.push(doc);
      });
      const json = JSON.stringify(docs);
      // In production, write to file or upload to S3
      print(`Exported ${docs.length} documents from ${dbName}.${colName}`);
    }
  });
});

print(`Backup scan completed at ${new Date().toISOString()}`);
```

Run with:
```bash
mongosh "mongodb://admin:password@localhost:27017/?authSource=admin" backup-script.js
```

### When to Use Custom Scripts

Mongosh-based backups are ideal when:
- You need application-level data transformations before export
- You want to backup only specific collections or filtered subsets
- You need to integrate with custom retention or notification systems
- You want to generate backup reports (row counts, size estimates) before running full dumps

## Comparison: mongodump vs Percona Backup vs Mongosh

| Feature | mongodump | Percona Backup (PBM) | Mongosh Scripts |
|---------|-----------|---------------------|-----------------|
| **Consistency** | Eventually consistent (or oplog-based) | Strictly consistent point-in-time | Depends on script |
| **Incremental backups** | No | Yes | Custom implementation |
| **Point-in-time recovery** | No (without oplog replay) | Yes | No |
| **Scheduling** | Manual or external cron | Built-in scheduler | External cron/systemd |
| **Retention management** | Manual | Built-in policies | Custom implementation |
| **Storage backend** | Local filesystem | S3, Azure Blob, local | Any (script-dependent) |
| **Sharded cluster support** | Yes (via mongos) | Yes (coordinated across shards) | Custom implementation |
| **Compression** | gzip, zstandard | gzip, snappy, s2 | Depends on script |
| **Parallel execution** | No (single thread per collection) | Yes (per-node agents) | Depends on script |
| **Docker image** | mongo:7 (official) | percona/percona-backup-mongodb | mongo:7 (official) |
| **License** | SSPL | Apache 2.0 | SSPL |
| **GitHub stars** | N/A (part of mongodb/mongo) | 550+ | N/A (part of mongodb/mongo) |
| **Best for** | Simple full backups, ad-hoc dumps | Production-grade HA backups | Custom selective backups |

## Why Self-Host Your MongoDB Backup Infrastructure?

Self-hosting backup solutions gives you complete control over backup schedules, retention policies, encryption, and storage locations. Cloud-managed MongoDB backup services are convenient but introduce vendor lock-in, egress costs, and limited customization. With self-hosted backups, you can:

- Store backups on-premises or in any S3-compatible storage (MinIO, Ceph, Backblaze B2)
- Encrypt backups with your own keys before transmission
- Implement custom retention policies aligned with compliance requirements
- Test restore procedures on your own infrastructure without cloud costs
- Avoid per-GB backup storage fees charged by managed database providers

For database sharding strategies that reduce the need for frequent full backups, see our [Vitess vs Citus vs ShardingSphere guide](../2026-05-09-oci-container-runtimes-crun-runc-youki-guide/). If you manage database high availability at the cluster level, our [Patroni vs Galera vs Repmgr guide](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide/) covers PostgreSQL. For Kubernetes-level backup orchestration that can complement database backups, our [Velero vs Stash vs Volsync comparison](../velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide-2026/) covers persistent volume protection.

## FAQ

### Does mongodump lock the database during backup?

No. mongodump reads data without acquiring locks on the database. It uses cursors to iterate through collections, which means writes can continue during the backup. However, this also means the backup is not point-in-time consistent unless you use the `--oplog` flag on a replica set.

### Can Percona Backup for MongoDB work with a single MongoDB node?

PBM requires a replica set (minimum 2 nodes) because it coordinates backups across multiple agents. A single standalone MongoDB instance cannot use PBM. You can convert a standalone instance to a single-node replica set using `rs.initiate()`.

### How much storage does an incremental PBM backup consume?

Incremental backups only store the changes (WiredTiger data blocks) since the last full or incremental backup. For workloads with low write rates, incremental backups are typically 1-5% of the full backup size. For high-write workloads, they can be 10-30% of the full backup size.

### Can I restore a mongodump to a different MongoDB version?

Generally yes, mongodump creates BSON files that are compatible across MongoDB versions. However, restoring to a newer major version may require additional steps if the new version has incompatible features. Always test restore procedures against your target version.

### How do I automate mongodump with retention?

Use a cron job that runs mongodump with timestamped filenames, combined with a cleanup script that removes backups older than a threshold:

```bash
#!/bin/bash
BACKUP_DIR="/backup"
RETENTION_DAYS=30
DATESTAMP=$(date +%Y-%m-%d_%H%M%S)

mongodump --host localhost --db production --gzip --archive=$BACKUP_DIR/backup-$DATESTAMP.gz

# Remove backups older than retention period
find $BACKUP_DIR -name "backup-*.gz" -mtime +$RETENTION_DAYS -delete
```

### Is mongosh backup scripting production-ready?

Mongosh-based backups are production-ready for selective or filtered backups where you need application-level control. However, they do not provide the consistency guarantees of PBM or the simplicity of mongodump. For full-database disaster recovery, prefer PBM or mongodump with oplog. Use mongosh scripts for supplementary backups (specific collections, transformed data, validation reports).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MongoDB Backup Solutions: mongodump vs Percona Backup vs Mongosh",
  "description": "Compare three MongoDB backup approaches: mongodump for simple dumps, Percona Backup for consistent production backups, and mongosh scripts for custom selective exports. Includes Docker Compose configs.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
