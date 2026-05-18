---
title: "Self-Hosted Distributed Transaction Solutions — Seata vs CAP vs HMily"
date: "2026-05-18"
tags: ["distributed-transactions", "microservices", "data-consistency", "saga-pattern", "tcc"]
draft: false
---

When microservices span multiple databases and systems, ensuring data consistency across service boundaries becomes one of the hardest problems in distributed computing. Traditional ACID transactions do not work across service boundaries, forcing teams to choose between eventual consistency patterns and distributed transaction coordinators.

This guide compares three leading open-source distributed transaction frameworks — **Apache Seata**, **dotnetcore/CAP**, and **dromara/HMily** — examining their architectures, consistency models, and real-world deployment patterns.

## Understanding Distributed Transaction Patterns

Before diving into tool comparisons, it is important to understand the core patterns these frameworks implement:

- **2PC (Two-Phase Commit)**: A coordinator ensures all participants either commit or rollback, guaranteeing strong consistency at the cost of availability and performance.
- **TCC (Try-Confirm-Cancel)**: Each operation is split into three phases — a try phase that reserves resources, a confirm phase that commits, and a cancel phase that releases reserved resources on failure.
- **Saga Pattern**: A sequence of local transactions where each has a compensating action that undoes its effects if a later step fails.
- **Outbox Pattern**: Events are written to a local outbox table alongside business data, then a relay process publishes them asynchronously.
- **AT (Automatic Transaction)**: Seata proprietary mode that automatically generates undo logs without requiring application code changes.

## Apache Seata — The Comprehensive Distributed Transaction Framework

**GitHub**: [apache/incubator-seata](https://github.com/apache/incubator-seata) | **Stars**: 25,959+ | **Language**: Java

Apache Seata (Simple Extensible Autonomous Transaction Architecture) is the most feature-rich open-source distributed transaction solution. Originally developed by Alibaba, it supports four transaction modes: AT, TCC, SAGA, and XA.

### Key Features

- **AT Mode**: Automatic transaction mode that intercepts SQL and generates undo logs transparently — no application code changes required
- **TCC Mode**: Manual two-phase commit for maximum control and performance
- **SAGA Mode**: Long-running transaction orchestration with compensating actions
- **XA Mode**: Standard XA protocol support for cross-database transactions
- **Multi-registry support**: Nacos, Eureka, Consul, ZooKeeper, etcd

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  seata-server:
    image: seataio/seata-server:latest
    container_name: seata-server
    ports:
      - "8091:8091"
      - "7091:7091"
    environment:
      - SEATA_PORT=8091
      - STORE_MODE=db
      - SEATA_IP=127.0.0.1
    volumes:
      - ./seata-config:/seata-server/resources
    depends_on:
      - mysql

  mysql:
    image: mysql:8.0
    container_name: seata-mysql
    environment:
      MYSQL_ROOT_PASSWORD: seata_pass
      MYSQL_DATABASE: seata
    volumes:
      - seata_data:/var/lib/mysql
    ports:
      - "3307:3306"

volumes:
  seata_data:
```

### Seata Server Configuration

```yaml
# registry.conf
registry {
  type = "nacos"
  nacos {
    application = "seata-server"
    serverAddr = "127.0.0.1:8848"
    namespace = ""
    cluster = "default"
  }
}

config {
  type = "nacos"
  nacos {
    serverAddr = "127.0.0.1:8848"
    namespace = ""
    group = "SEATA_GROUP"
  }
}

# store.mode = "db" for production
store {
  mode = "db"
  db {
    datasource = "druid"
    dbType = "mysql"
    url = "jdbc:mysql://127.0.0.1:3307/seata"
    user = "root"
    password = "seata_pass"
  }
}
```

### Integration Example (Spring Boot)

```java
@GlobalTransactional
public void createOrder(OrderRequest request) {
    // 1. Create order in Order Service
    orderService.create(request);
    
    // 2. Deduct inventory in Inventory Service
    inventoryService.deduct(request.getProductId(), request.getQuantity());
    
    // 3. Deduct balance in Account Service
    accountService.deduct(request.getUserId(), request.getAmount());
}
```

## dotnetcore/CAP — Event Bus with Outbox Pattern

**GitHub**: [dotnetcore/CAP](https://github.com/dotnetcore/CAP) | **Stars**: 7,083+ | **Language**: C#

CAP (Cloud Application Platform) is a .NET library that implements the Outbox pattern, providing eventual consistency through a local message table and event bus. It is lighter-weight than Seata, focusing on event-driven consistency rather than distributed transaction coordination.

### Key Features

- **Outbox Pattern**: Messages are written to a local database table within the same transaction as business data
- **Eventual Consistency**: Retry mechanism with configurable backoff ensures message delivery
- **Multi-transport support**: RabbitMQ, Kafka, Azure Service Bus, Amazon SQS, NATS, Redis Streams
- **Multi-database support**: SQL Server, MySQL, PostgreSQL, MongoDB, SQLite
- **Built-in dashboard**: Web UI for monitoring message status and retries
- **Delay messages**: Scheduled message delivery support

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  rabbitmq:
    image: rabbitmq:3-management
    container_name: cap-rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: cap_user
      RABBITMQ_DEFAULT_PASS: cap_pass

  mysql:
    image: mysql:8.0
    container_name: cap-mysql
    environment:
      MYSQL_ROOT_PASSWORD: cap_pass
      MYSQL_DATABASE: cap_db
    ports:
      - "3308:3306"
    volumes:
      - cap_data:/var/lib/mysql

volumes:
  cap_data:
```

### Integration Example (.NET)

```csharp
public class OrderService
{
    private readonly ICapPublisher _capPublisher;
    private readonly AppDbContext _dbContext;

    public OrderService(ICapPublisher capPublisher, AppDbContext dbContext)
    {
        _capPublisher = capPublisher;
        _dbContext = dbContext;
    }

    public async Task CreateOrderAsync(Order order)
    {
        using var transaction = _dbContext.Database.BeginTransaction(_capPublisher, autoCommit: false);
        
        // Business operation and event published in same transaction
        _dbContext.Orders.Add(order);
        await _dbContext.SaveChangesAsync();
        
        await _capPublisher.PublishAsync("order.created", new
        {
            OrderId = order.Id,
            Total = order.Total
        });
        
        await transaction.CommitAsync();
    }
}
```

## dromara/HMily — TCC and Saga Framework

**GitHub**: [dromara/hmily](https://github.com/dromara/hmily) | **Stars**: 4,183+ | **Language**: Java

HMily is a high-performance distributed transaction framework focusing on TCC and Saga patterns. It is designed for high-concurrency scenarios where the overhead of 2PC-based solutions is unacceptable.

### Key Features

- **TCC Mode**: High-performance two-phase commit with manual resource reservation
- **Saga Mode**: Event-driven long-running transaction orchestration
- **High concurrency**: Designed for scenarios with 10,000+ TPS
- **Multiple coordinators**: ZooKeeper, Nacos, etcd, Consul
- **Multiple databases**: MySQL, Oracle, PostgreSQL, MongoDB, Redis
- **Automatic retry**: Configurable retry policies with exponential backoff
- **Admin dashboard**: Web UI for transaction monitoring and management

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  hmily-admin:
    image: hmily/hmily-admin:latest
    container_name: hmily-admin
    ports:
      - "8089:8089"
    environment:
      - HMILIY_ADMIN_PORT=8089
    depends_on:
      - mysql
      - zookeeper

  zookeeper:
    image: zookeeper:3.8
    container_name: hmily-zk
    ports:
      - "2181:2181"

  mysql:
    image: mysql:8.0
    container_name: hmily-mysql
    environment:
      MYSQL_ROOT_PASSWORD: hmily_pass
      MYSQL_DATABASE: hmily
    ports:
      - "3309:3306"
    volumes:
      - hmily_data:/var/lib/mysql

volumes:
  hmily_data:
```

### Integration Example (Spring Boot)

```java
@HmilyTCC(confirmMethod = "confirmPay", cancelMethod = "cancelPay")
public void pay(Order order) {
    // Try phase: freeze the account balance
    accountService.freeze(order.getUserId(), order.getAmount());
}

public void confirmPay(Order order) {
    // Confirm phase: deduct the frozen amount
    accountService.deduct(order.getUserId(), order.getAmount());
}

public void cancelPay(Order order) {
    // Cancel phase: unfreeze the amount
    accountService.unfreeze(order.getUserId(), order.getAmount());
}
```

## Comparison: Seata vs CAP vs HMily

| Feature | Apache Seata | dotnetcore/CAP | dromara/HMily |
|---------|-------------|----------------|---------------|
| **Primary Pattern** | AT/TCC/SAGA/XA | Outbox + Event Bus | TCC/Saga |
| **Consistency Model** | Strong (AT/XA), Eventual (TCC/Saga) | Eventual | Eventual |
| **Performance** | Moderate (AT adds undo log overhead) | High (asynchronous) | Very High (TCC optimized) |
| **Language** | Java | .NET | Java |
| **Transaction Coordinator** | Built-in TC server | Database outbox table | Coordinator node |
| **Dashboard** | Yes (seata-console) | Yes (built-in web UI) | Yes (hmily-admin) |
| **Saga Orchestration** | Yes | No | Yes |
| **Outbox Pattern** | No | Yes (core feature) | No |
| **Auto Retry** | Yes | Yes (configurable) | Yes |
| **Best For** | Full-featured distributed transactions | Event-driven microservices | High-concurrency TCC scenarios |
| **GitHub Stars** | 25,959+ | 7,083+ | 4,183+ |
| **Docker Support** | Official image | Application-level | Official image |

## Choosing the Right Distributed Transaction Framework

### Choose Apache Seata When:
- You need multiple transaction modes (AT, TCC, Saga, XA)
- You want transparent AT mode with minimal code changes
- Your team works primarily in Java/Spring ecosystem
- You need XA protocol support for cross-database transactions

### Choose dotnetcore/CAP When:
- You are building .NET microservices
- Eventual consistency is acceptable for your use case
- You prefer the Outbox pattern over distributed coordination
- You need multi-transport flexibility (RabbitMQ, Kafka, SQS, NATS)

### Choose dromara/HMily When:
- You need maximum throughput (10,000+ TPS)
- TCC pattern fits your business logic well
- You want lightweight coordination without a central TC server
- Your application can handle manual Try/Confirm/Cancel implementations

## Why Self-Host Distributed Transaction Infrastructure?

Running distributed transaction coordinators on your own infrastructure gives you complete control over consistency guarantees, retry policies, and failure handling. Cloud-managed alternatives often limit configuration options and charge per-transaction fees that scale unpredictably with microservice growth.

Self-hosting ensures your transaction coordinators run in the same network as your services, minimizing latency for the critical coordination phase. It also means you are not dependent on a cloud provider specific distributed transaction offering — your application remains portable across environments.

For organizations managing complex microservice architectures, distributed transaction frameworks work alongside other infrastructure components. For related reading, see our [service mesh comparison](../2026-05-06-self-hosted-service-mesh-gateway-envoy-istio-kong-guide/), [Kubernetes admission controllers guide](../2026-05-16-self-hosted-kubernetes-admission-controllers-kyverno-opa-gatekeeper-kubewarden-guide/), and [event sourcing platforms guide](../2026-04-20-eventstoredb-vs-kafka-vs-pulsar-self-hosted-event-sourcing-guide-2026/).

## FAQ

### What is the difference between strong and eventual consistency in distributed transactions?
Strong consistency (2PC, XA) guarantees that all participants either commit or rollback together, ensuring data is always consistent but sacrificing availability during network partitions. Eventual consistency (Outbox, Saga) allows temporary inconsistency but guarantees all services converge to a consistent state through retries and compensating actions.

### When should I use the Outbox pattern vs TCC?
Use the Outbox pattern when your services communicate asynchronously and eventual consistency is acceptable. Use TCC when you need stronger consistency guarantees and can implement the Try/Confirm/Cancel logic for each operation. TCC is more complex but provides better consistency at higher performance than 2PC.

### Does Apache Seata AT mode affect database performance?
Yes — AT mode intercepts all SQL operations to generate undo logs, adding approximately 10-30% overhead compared to direct database writes. For high-throughput scenarios, consider TCC mode which has lower overhead but requires more application code.

### Can I mix distributed transaction patterns in the same application?
Yes. Many production systems use Seata AT for internal service calls, TCC for critical financial operations, and the Outbox pattern for external notifications. CAP can run alongside Seata for different consistency requirements across service boundaries.

### How do these frameworks handle partial failures during the confirm phase?
Seata TC server retries confirm operations with configurable timeouts. CAP uses its outbox table to retry message publishing until successful. HMily implements automatic retry with exponential backoff. All three frameworks provide admin dashboards for manual intervention when automatic retries fail.

### Is distributed transaction coordination necessary for all microservices?
No. Many microservice architectures work well with eventual consistency, idempotent operations, and compensating actions. Distributed transaction coordinators add operational complexity and should only be used when strong consistency is a business requirement (e.g., financial transactions, inventory management).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Distributed Transaction Solutions — Seata vs CAP vs HMily",
  "description": "Compare open-source distributed transaction frameworks: Apache Seata (AT/TCC/SAGA), dotnetcore/CAP (Outbox pattern), and HMily (TCC/Saga) with Docker deployment configs.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
