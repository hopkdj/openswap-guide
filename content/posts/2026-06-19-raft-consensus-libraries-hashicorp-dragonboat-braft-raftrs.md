---
title: "Self-Hosted Raft Consensus Libraries: HashiCorp Raft vs Dragonboat vs braft vs raft-rs"
date: "2026-06-19"
tags: ["distributed-systems", "consensus", "raft", "libraries", "golang", "rust", "cpp", "backend"]
draft: false
---

## What Are Raft Consensus Libraries?

When building distributed systems, one of the hardest problems is getting multiple nodes to agree on state. The Raft consensus algorithm, designed by Diego Ongaro and John Ousterhout in 2014, has become the de facto standard for implementing replicated state machines due to its understandability compared to Paxos.

While etcd and Consul provide complete key-value stores with Raft under the hood, many applications need to embed consensus directly into their own services. Standalone Raft libraries provide the consensus primitive without the overhead of a full key-value store.

This article compares four of the most popular open-source Raft implementations across Go, C++, and Rust ecosystems.

## The Contenders at a Glance

| Library | Language | Stars | Last Updated | Multi-Raft | Key Feature |
|---------|----------|-------|--------------|------------|-------------|
| [HashiCorp Raft](https://github.com/hashicorp/raft) | Go | 9,040+ | Jun 2026 | No | Battle-tested in Consul and Nomad |
| [Dragonboat](https://github.com/lni/dragonboat) | Go | 5,307+ | Jul 2025 | Yes | High-performance multi-raft |
| [braft](https://github.com/baidu/braft) | C++ | 4,214+ | Oct 2024 | No | Industrial-grade, brpc-based |
| [raft-rs](https://github.com/tikv/raft-rs) | Rust | 3,351+ | May 2026 | No | Powers TiKV, production-proven |

## HashiCorp Raft: The Gold Standard

HashiCorp Raft is the most widely deployed Go Raft library, powering HashiCorp Consul and Nomad. It is a single-group implementation that focuses on correctness and simplicity.

```go
// Basic HashiCorp Raft setup
package main

import (
    "net"
    "os"
    "time"
    
    "github.com/hashicorp/raft"
    raftboltdb "github.com/hashicorp/raft-boltdb"
)

func main() {
    config := raft.DefaultConfig()
    config.LocalID = raft.ServerID("node-1")
    
    addr, _ := net.ResolveTCPAddr("tcp", "127.0.0.1:7000")
    transport, _ := raft.NewTCPTransport(
        "127.0.0.1:7000", addr, 3, 10*time.Second, os.Stderr,
    )
    
    logStore, _ := raftboltdb.NewBoltStore("/tmp/raft-log.db")
    stableStore, _ := raftboltdb.NewBoltStore("/tmp/raft-stable.db")
    snapshotStore := raft.NewInmemSnapshotStore()
    
    r, _ := raft.NewRaft(
        config, nil, logStore, stableStore, snapshotStore, transport,
    )
    
    configuration := raft.Configuration{
        Servers: []raft.Server{
            {ID: config.LocalID, Address: transport.LocalAddr()},
        },
    }
    r.BootstrapCluster(configuration)
}
```

HashiCorp Raft uses a clean interface: implement `raft.FSM` (Finite State Machine) with `Apply()` and `Snapshot()` methods, and Raft handles the rest.

**Strengths:**
- Production-proven in Consul, Nomad, and Vault
- Excellent documentation and examples
- Active maintenance by HashiCorp
- Clean Go interface with FSM abstraction

**Limitations:**
- Single Raft group only (no multi-raft)
- Go-only (no C FFI or cross-language bindings)
- No built-in membership reconfiguration beyond basic add/remove

## Dragonboat: Multi-Raft for High Throughput

Dragonboat takes a different approach by implementing multi-raft: the ability to run thousands of Raft groups in a single process. Each group manages its own state machine, enabling extremely high aggregate throughput.

```go
// Dragonboat multi-group setup
package main

import (
    "github.com/lni/dragonboat/v4"
    "github.com/lni/dragonboat/v4/config"
)

func main() {
    nodeHostConfig := config.NodeHostConfig{
        WALDir:          "/tmp/dragonboat-wal",
        NodeHostDir:     "/tmp/dragonboat-data",
        RTTMillisecond:  5,
        RaftAddress:     "127.0.0.1:63001",
    }
    nh, _ := dragonboat.NewNodeHost(nodeHostConfig)
    defer nh.Stop()
    
    clusterConfig := config.Config{
        NodeID:             1,
        ClusterID:          100,
        ElectionRTT:        10,
        HeartbeatRTT:       1,
        CheckQuorum:        true,
        SnapshotEntries:    10000,
        CompactionOverhead: 5000,
    }
    
    nodeAddresses := map[uint64]string{
        1: "127.0.0.1:63001",
        2: "127.0.0.1:63002",
        3: "127.0.0.1:63003",
    }
    
    nh.StartCluster(nodeAddresses, false, nil, clusterConfig)
}
```

Dragonboat's multi-group architecture is ideal for sharded systems where each shard gets its own Raft group. It supports on-disk state machines via RocksDB integration and zero-copy read operations.

**Strengths:**
- Multi-raft: thousands of groups per process
- On-disk state machine support (RocksDB)
- Optimistic read (zero-copy reads from leader)
- C++ binding available for cross-language use

**Limitations:**
- More complex configuration than single-group libraries
- Less active maintenance (last significant update mid-2025)
- Heavier dependency footprint

## braft: Industrial-Grade C++ Raft

braft is Baidu's open-source C++ Raft implementation, built on top of brpc (Baidu's high-performance RPC framework). It is used extensively within Baidu for distributed storage and coordination services.

```cpp
// braft basic usage
#include <braft/raft.h>
#include <braft/storage.h>
#include <braft/util.h>
#include <brpc/server.h>

class MyStateMachine : public braft::StateMachine {
public:
    void on_apply(braft::Iterator& iter) override {
        for (; iter.valid(); iter.next()) {
            const butil::IOBuf& data = iter.data();
            // Apply committed entries to state machine
        }
    }
    
    void on_snapshot_save(braft::SnapshotWriter* writer,
                          braft::Closure* done) override {
        // Save state machine snapshot
        done->Run();
    }
    
    int on_snapshot_load(braft::SnapshotReader* reader) override {
        // Load state machine snapshot
        return 0;
    }
};

int main() {
    brpc::Server server;
    
    braft::NodeOptions options;
    options.election_timeout_ms = 1000;
    options.snapshot_interval_s = 3600;
    
    std::string group_id = "my_raft_group";
    butil::EndPoint addr(butil::my_ip(), 8200);
    
    braft::Node* node = new braft::Node(group_id, braft::PeerId(addr));
    MyStateMachine fsm;
    
    node->init(options);
    server.RunUntilAskedToQuit();
    return 0;
}
```

braft inherits brpc's performance characteristics: single-digit microsecond RPC latency and high throughput. It is used in Baidu's internal infrastructure handling petabytes of data.

**Strengths:**
- Industrial-grade performance via brpc
- Battle-tested at Baidu's scale
- Rich configuration options for production tuning
- Good C++ ecosystem integration

**Limitations:**
- C++ only (no Go/Rust/Python bindings)
- Documentation primarily in Chinese
- Less active community outside Baidu ecosystem
- Build system depends on brpc toolchain

## raft-rs: Rust-Native Raft

raft-rs is the Raft library powering TiKV, the distributed transactional key-value store behind TiDB. Written in Rust, it emphasizes safety and performance through Rust's ownership model.

```rust
// raft-rs basic usage pattern
use raft::prelude::*;
use raft::{storage::MemStorage, Config};

fn main() {
    let config = Config {
        id: 1,
        election_tick: 10,
        heartbeat_tick: 3,
        applied: 0,
        max_size_per_msg: 1024 * 1024 * 1024,
        max_inflight_msgs: 256,
        ..Default::default()
    };
    
    let storage = MemStorage::new_with_conf_state((vec![1, 2, 3], vec![]));
    let mut raft_group = RawNode::new(&config, storage, &Default::default()).unwrap();
    
    loop {
        if !raft_group.has_ready() {
            continue;
        }
        
        let mut ready = raft_group.ready();
        
        // 1. Persist HardState and Entries
        // 2. Send messages to peers
        // 3. Apply committed entries to state machine
        // 4. Advance the Raft state
        
        raft_group.advance(ready);
    }
}
```

raft-rs provides a low-level `RawNode` API that gives fine-grained control over the Raft event loop, making it ideal for systems that need custom storage, networking, and state machine implementations.

**Strengths:**
- Memory safety via Rust's ownership model
- Powers TiKV (TI Cloud's distributed KV store)
- Active development with regular releases
- Excellent concurrency support through async Rust

**Limitations:**
- Lower-level API (more work to integrate)
- Rust learning curve for teams using other languages
- Smaller community compared to Go alternatives
- Documentation assumes familiarity with Raft internals

## Choosing the Right Raft Library

Your choice depends primarily on three factors: programming language ecosystem, whether you need multi-raft, and performance requirements.

| Criterion | HashiCorp Raft | Dragonboat | braft | raft-rs |
|-----------|---------------|------------|-------|---------|
| **Language** | Go | Go (+C++ binding) | C++ | Rust |
| **Multi-Raft** | No | Yes | No | No |
| **Production Users** | Consul, Nomad, Vault | Internal systems | Baidu internal | TiKV, TiDB |
| **Docs Quality** | Excellent | Good | Fair | Good |
| **Ease of Use** | Very easy | Moderate | Moderate | Advanced |
| **Performance** | Good | Excellent | Excellent | Very good |

For most Go applications, HashiCorp Raft is the safe, well-documented choice. If you need multi-raft for sharded architectures, Dragonboat is unmatched. C++ teams at scale should consider braft for its battle-tested brpc integration, and Rust teams building production distributed databases will find raft-rs to be the natural fit alongside TiKV.

For more on distributed coordination, see our [etcd cluster management guide](../2026-05-10-self-hosted-etcd-cluster-management-operator-cloud-operator-etcdadm-guide/) and [distributed locking comparison](../2026-05-17-self-hosted-distributed-key-value-stores-tikv-dragonflydb-etcd-guide/).

## FAQ

### What is the difference between consensus libraries and coordination services like etcd or ZooKeeper?

Consensus libraries embed the Raft/Paxos algorithm directly into your application process. Your app manages its own state machine, log replication, and leader election. Coordination services like etcd are standalone servers that your application connects to via a client API. Libraries give you more control and lower latency (no network hop to an external service), but coordination services handle cluster management, membership, and failure detection out of the box.

### Do I need a Raft library if I am already using Kubernetes for orchestration?

It depends on your application's state management needs. Kubernetes handles pod lifecycle but does not provide consensus for your application's internal state. If your application maintains state that must be consistent across replicas (such as a distributed cache, a leader-elected worker, or a replicated metadata store), you still need a consensus mechanism. Raft libraries let you embed that directly without external dependencies.

### Can I use these libraries for production systems handling financial data?

Yes, HashiCorp Raft and raft-rs both power production financial and infrastructure systems. HashiCorp Raft underpins Vault (secret management used by banks) and Consul (service discovery in financial data centers). raft-rs powers TiKV, used in production at financial services companies via TiDB. The key is proper configuration: adequate election timeouts, persistent storage, and monitoring of leader changes and log replication lag.

### How do these libraries handle network partitions and split-brain scenarios?

All four implement the Raft safety guarantees: a leader can only be elected if it has support from a majority of nodes (quorum). During a network partition, the minority partition cannot elect a new leader or commit entries, preventing split-brain. The majority partition continues operating normally. When the partition heals, the minority catches up by receiving missing log entries from the new leader.

### What is the minimum number of nodes I should run?

Raft requires an odd number of nodes for optimal operation. Three nodes can tolerate one failure (3-1=2, still has majority). Five nodes can tolerate two failures (5-2=3, still has majority). Three nodes is the practical minimum for production; running fewer compromises fault tolerance.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Raft Consensus Libraries: HashiCorp Raft vs Dragonboat vs braft vs raft-rs",
  "description": "Comprehensive comparison of four open-source Raft consensus library implementations: HashiCorp Raft (Go), Dragonboat (Go multi-raft), braft (C++), and raft-rs (Rust). Includes code examples, performance characteristics, and selection guide for distributed systems engineers.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
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

**Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading -- the world's largest prediction market platform where you can bet on everything from election results to technology regulation timelines. Unlike gambling, this is a true information market: the more you know, the better your odds. I've made good money predicting technology-related events. Sign up with my invite link: **[Polymarket.com](https://polymarket.com/?r=fc8a0)
