---
title: "Temporal vs Camunda vs Flowable: Best Self-Hosted Workflow Orchestration 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "workflow", "orchestration"]
draft: false
description: "Compare Temporal, Camunda, and Flowable — the top self-hosted workflow orchestration platforms in 2026. Full Docker setup guides, feature comparison, and decision framework."
---

## Why Self-Host Your Workflow Orchestration Engine

Workflow orchestration engines coordinate complex, multi-step business processes across distributed systems. They manage state, handle retries, enforce timeouts, and guarantee exactly-once execution semantics — capabilities that cloud services like AWS Step Functions, Azure Logic Apps, and Google Cloud Workflows provide out of the box.

But self-hosting your workflow engine offers critical advantages that cloud platforms cannot match:

- **Complete data sovereignty** — sensitive business logic and state never leave your infrastructure. This matters for healthcare, finance, and government workloads subject to HIPAA, PCI-DSS, or GDPR requirements.
- **No vendor lock-in** — open-source orchestration engines use standard protocols and portable workflow definitions. Migrate between clouds or on-premises deployments without rewriting processes.
- **Cost predictability at scale** — cloud workflow services charge per execution, state transition, and duration. Self-hosted engines have fixed infrastructure costs that amortize favorably as volume grows.
- **Deep customization** — full access to source code means you can extend schedulers, add custom persistence backends, integrate with proprietary systems, and optimize for your specific workload patterns.
- **Offline operation** — critical workflows continue running even during cloud provider outages or network partitions.

Three platforms dominate the open-source workflow orchestration space in 2026: **Temporal**, **Camunda 8**, and **Flowable**. Each takes a fundamentally different architectural approach to solving the same problem. This guide compares them across every dimension that matters and provides production-ready Docker deployment instructions.

---

## Temporal: Code-First Durable Execution

Temporal emerged from Uber's Cadence project and reimagines workflow orchestration around **durable execution** — the idea that workflow code should look like normal synchronous code, with the platform transparently persisting state and replaying execution after failures.

### Architecture

Temporal separates concerns into four components:

- **Temporal Server** — the orchestration engine that schedules workflow tasks, manages event history, and guarantees durability
- **Workers** — your application processes that execute workflow and activity code
- **SDK** — client libraries in Go, Java, TypeScript, Python, and .NET that wrap your code in durable execution primitives
- **Web UI** — built-in dashboard for monitoring workflows, viewing event histories, and replaying executions

The key innovation is **event sourcing with replay**. Every workflow event is persisted to an append-only log. When a worker resumes a workflow, it replays the entire event history to reconstruct state, then continues from the last completed event. This means your workflow code never needs to manage checkpoints or state serialization — the SDK handles it transparently.

### Docker Compose Deployment

```yaml
version: "3.9"

services:
  postgresql:
    image: postgres:16
    environment:
      POSTGRES_USER: temporal
      POSTGRES_PASSWORD: temporal_password
      POSTGRES_DB: temporal
    volumes:
      - temporal_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U temporal"]
      interval: 5s
      retries: 5

  temporal:
    image: temporalio/auto-setup:1.25
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal_password
      - POSTGRES_SEEDS=postgresql
      - DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development-sql.yaml
    depends_on:
      postgresql:
        condition: service_healthy
    volumes:
      - ./dynamicconfig:/etc/temporal/config/dynamicconfig

  temporal-ui:
    image: temporalio/ui:2.30
    ports:
      - "8080:8080"
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
      - TEMPORAL_CORS_ORIGINS=http://localhost:3000
    depends_on:
      - temporal

volumes:
  temporal_postgres_data:
```

Save this as `docker-compose.yml` and start the stack:

```bash
docker compose up -d
```

Verify the server is accepting connections:

```bash
docker exec -it openswap-guide-temporal-1 \
  tctl --address localhost:7233 cluster health
```

### Writing Your First Workflow

Here's a real-world order processing workflow in TypeScript:

```typescript
import { proxyActivities, defineSignal, setHandler } from "@temporalio/workflow";
import type * as activities from "./activities";

const {
  validatePayment,
  reserveInventory,
  shipOrder,
  sendConfirmationEmail,
  refundPayment,
} = proxyActivities<typeof activities>({
  startToCloseTimeout: "30 seconds",
  retry: {
    initialInterval: "1s",
    maximumInterval: "30s",
    maximumAttempts: 5,
  },
});

export async function processOrder(orderId: string, items: string[], total: number): Promise<void> {
  // Step 1: Validate payment
  const paymentId = await validatePayment(orderId, total);

  // Step 2: Reserve inventory
  try {
    await reserveInventory(items);
  } catch (err) {
    // Compensating transaction: refund if inventory unavailable
    await refundPayment(paymentId);
    throw new Error(`Insufficient inventory for order ${orderId}`);
  }

  // Step 3: Ship the order
  const trackingNumber = await shipOrder(orderId, items);

  // Step 4: Send confirmation
  await sendConfirmationEmail(orderId, trackingNumber);
}
```

The `proxyActivities` call creates stubs for activity functions. Temporal ensures each activity executes exactly once, even if the worker crashes mid-execution. If any activity fails, Temporal retries according to the configured policy. The compensating `refundPayment` call implements the saga pattern — undoing completed steps when a later step fails.

### When to Choose Temporal

- **Durable execution is your primary need** — you want workflow code that looks like normal code with automatic retry and replay
- **Microservices architecture** — workers can be deployed independently across your service mesh
- **Multi-language teams** — SDKs in five languages let each team use their preferred stack
- **High-throughput workloads** — Temporal scales horizontally with partitioned task queues and can handle millions of concurrent workflows

---

## Camunda 8: BPMN 2.0 Standard with Zeebe Engine

Camunda 8 represents a complete rewrite of the platform around the **Zeebe** workflow engine — a cloud-native, horizontally scalable process engine that executes BPMN 2.0 workflows using a log-structured architecture inspired by Apache Kafka.

### Architecture

Camunda 8's architecture consists of:

- **Zeebe Gateway** — routes workflow commands to partition leaders and provides the gRPC/REST API
- **Zeebe Brokers** — store workflow state in partitioned event logs, execute jobs, and manage workflow instances
- **Operate** — web application for monitoring running workflows, identifying stuck instances, and managing incidents
- **Tasklist** — user task management interface for human-in-the-loop workflows
- **Optimize** — process analytics dashboard with KPI tracking and bottleneck identification
- **Connectors** — pre-built integrations for REST APIs, Kafka, RabbitMQ, email, and 100+ services

Zeebe uses **command sourcing** rather than event sourcing. Every action on a workflow instance (start, complete job, cancel) is a command appended to a partitioned log. Workers poll for jobs rather than receiving pushed tasks, which simplifies network topology and enables natural load balancing.

### Docker Compose Deployment

```yaml
version: "3.9"

services:
  zeebe:
    image: camunda/zeebe:8.6.0
    ports:
      - "26500:26500"
      - "9600:9600"
    environment:
      - ZEEBE_LOG_LEVEL=info
      - ZEEBE_BROKER_EXPORTERS_ELASTICSEARCH_CLASSNAME=io.camunda.zeebe.exporter.ElasticsearchExporter
      - ZEEBE_BROKER_EXPORTERS_ELASTICSEARCH_ARGS_URL=http://elasticsearch:9200
      - ZEEBE_BROKER_GATEWAY_ENABLE=true
    volumes:
      - zeebe_data:/usr/local/zeebe/data
      - ./application.yaml:/usr/local/zeebe/conf/application.yaml

  operate:
    image: camunda/operate:8.6.0
    ports:
      - "8081:8080"
    environment:
      - CAMUNDA_OPERATE_ZEEBE_GATEWAYADDRESS=zeebe:26500
      - CAMUNDA_OPERATE_ELASTICSEARCH_URL=http://elasticsearch:9200
      - CAMUNDA_OPERATE_ZEEBEELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - zeebe
      - elasticsearch

  tasklist:
    image: camunda/tasklist:8.6.0
    ports:
      - "8082:8080"
    environment:
      - CAMUNDA_TASKLIST_ZEEBE_GATEWAYADDRESS=zeebe:26500
      - CAMUNDA_TASKLIST_ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - zeebe
      - elasticsearch

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    volumes:
      - es_data:/usr/share/elasticsearch/data

  connectors:
    image: camunda/connectors-bundle:8.6.0
    ports:
      - "8085:8080"
    environment:
      - ZEEBE_CLIENT_BROKER_GATEWAY-ADDRESS=zeebe:26500
      - ZEEBE_CLIENT_SECURITY_PLAINTEXT=true
      - CAMUNDA_OPERATE_CLIENT_URL=http://operate:8080
      - CAMUNDA_OPERATE_CLIENT_AUTH_TYPE=none
    depends_on:
      - zeebe
      - operate

volumes:
  zeebe_data:
  es_data:
```

Start the stack:

```bash
docker compose up -d
```

Access the monitoring interfaces:

- Operate: `http://localhost:8081`
- Tasklist: `http://localhost:8082`
- Connectors: `http://localhost:8085`

### Defining a Workflow with BPMN

Camunda workflows are defined as BPMN 2.0 XML diagrams. Here's a simplified order fulfillment process:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="order-fulfillment"
                  targetNamespace="http://openswap.guide/workflows">

  <bpmn:process id="OrderFulfillment" name="Order Fulfillment Process" isExecutable="true">

    <bpmn:startEvent id="StartOrder" name="Order Received"/>

    <bpmn:serviceTask id="ValidatePayment" name="Validate Payment">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="payment:validate" />
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <bpmn:exclusiveGateway id="PaymentDecision" name="Payment Valid?"/>

    <bpmn:serviceTask id="ReserveInventory" name="Reserve Inventory">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="inventory:reserve" />
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <bpmn:serviceTask id="ShipOrder" name="Ship Order">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="shipping:create" />
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <bpmn:endEvent id="OrderComplete" name="Order Completed"/>

    <bpmn:sequenceFlow id="flow1" sourceRef="StartOrder" targetRef="ValidatePayment"/>
    <bpmn:sequenceFlow id="flow2" sourceRef="ValidatePayment" targetRef="PaymentDecision"/>
    <bpmn:sequenceFlow id="flow3" name="Valid" sourceRef="PaymentDecision" targetRef="ReserveInventory">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">= payment.valid</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="flow4" name="Invalid" sourceRef="PaymentDecision" targetRef="OrderComplete">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">= !payment.valid</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="flow5" sourceRef="ReserveInventory" targetRef="ShipOrder"/>
    <bpmn:sequenceFlow id="flow6" sourceRef="ShipOrder" targetRef="OrderComplete"/>

  </bpmn:process>
</bpmn:definitions>
```

Deploy this workflow using the Zeebe CLI:

```bash
zbctl deploy process order-fulfillment.bpmn \
  --address localhost:26500
```

Workers in any language then poll for jobs by their type (`payment:validate`, `inventory:reserve`, `shipping:create`).

### When to Choose Camunda

- **BPMN 2.0 standard compliance** — business analysts model workflows visually using BPMN diagrams in Camunda Modeler
- **Human-in-the-loop workflows** — Tasklist provides a built-in interface for user tasks with forms and assignments
- **Enterprise process management** — Operate, Optimize, and Modeler form a complete process lifecycle suite
- **Migration from Camunda 7** — existing Camunda 7 BPMN models migrate to Camunda 8 with minimal changes

---

## Flowable: Lightweight Java Process Engine

Flowable is a fork of Activiti 6 that has evolved into a comprehensive process engine supporting BPMN 2.0, CMMN 1.1 (case management), and DMN 1.3 (decision tables) — all within a single lightweight JAR.

### Architecture

Flowable's architecture is notably simpler than Camunda 8 or Temporal:

- **Flowable Engine** — a single Java library that embeds directly into Spring Boot applications
- **Flowable UI** — web applications for modeling (Modeler), managing runtime instances (Task), and administering the engine (Admin)
- **Relational Database** — stores all workflow state in standard SQL tables (PostgreSQL, MySQL, Oracle, H2)
- **REST API** — OpenAPI-compliant REST endpoints for all engine operations

Unlike Zeebe's partitioned log architecture, Flowable uses a **relational data model** with tables tracking process instances, executions, tasks, variables, and history. This makes it familiar to developers comfortable with traditional ORM patterns and enables standard SQL reporting without a separate indexing layer.

### Docker Compose Deployment

```yaml
version: "3.9"

services:
  postgresql:
    image: postgres:16
    environment:
      POSTGRES_USER: flowable
      POSTGRES_PASSWORD: flowable_password
      POSTGRES_DB: flowable
    volumes:
      - flowable_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flowable"]
      interval: 5s
      retries: 5

  flowable-ui:
    image: flowable/flowable-ui:6.8.0
    ports:
      - "8080:8080"
    environment:
      - spring.datasource.url=jdbc:postgresql://postgresql:5432/flowable
      - spring.datasource.username=flowable
      - spring.datasource.password=flowable_password
      - spring.datasource.driver-class-name=org.postgresql.Driver
    depends_on:
      postgresql:
        condition: service_healthy

  flowable-rest:
    image: flowable/flowable-rest:6.8.0
    ports:
      - "8081:8080"
    environment:
      - spring.datasource.url=jdbc:postgresql://postgresql:5432/flowable
      - spring.datasource.username=flowable
      - spring.datasource.password=flowable_password
      - spring.datasource.driver-class-name=org.postgresql.Driver
    depends_on:
      postgresql:
        condition: service_healthy

volumes:
  flowable_postgres_data:
```

Start the deployment:

```bash
docker compose up -d
```

The Flowable UI is available at `http://localhost:8080/flowable-ui` with default credentials `admin/test`. The REST API is at `http://localhost:8081/flowable-rest`.

### Embedding in Spring Boot

For production use, embedding the engine in your application gives the most control:

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.flowable</groupId>
    <artifactId>flowable-spring-boot-starter</artifactId>
    <version>6.8.0</version>
</dependency>
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.7.3</version>
</dependency>
```

```java
// Flowable configuration in application.yml
// spring:
//   datasource:
//     url: jdbc:postgresql://localhost:5432/flowable
//     username: flowable
//     password: flowable_password
```

```java
@Service
public class OrderService {

    private final RuntimeService runtimeService;
    private final TaskService taskService;

    public OrderService(RuntimeService runtimeService, TaskService taskService) {
        this.runtimeService = runtimeService;
        this.taskService = taskService;
    }

    public String startOrderProcess(String orderId, String customerId) {
        Map<String, Object> variables = Map.of(
            "orderId", orderId,
            "customerId", customerId
        );
        ProcessInstance instance = runtimeService.startProcessInstanceByKey(
            "orderFulfillment", orderId, variables
        );
        return instance.getId();
    }

    public void completeApprovalTask(String processInstanceId, boolean approved) {
        Task task = taskService.createTaskQuery()
            .processInstanceId(processInstanceId)
            .taskDefinitionKey("approveOrder")
            .singleResult();

        if (task != null) {
            taskService.complete(task.getId(), Map.of("approved", approved));
        }
    }
}
```

### When to Choose Flowable

- **Spring Boot ecosystem** — native Spring Boot integration with auto-configuration and embedded engine
- **Relational database preference** — workflow state stored in standard SQL tables enables direct querying and reporting
- **CMMN and DMN requirements** — built-in case management and decision table support alongside BPMN
- **Lightweight footprint** — single JAR deployment with no external message broker or log store required
- **Familiar programming model** — Java/Spring developers work with standard service classes and repositories

---

## Feature Comparison Matrix

| Feature | Temporal | Camunda 8 (Zeebe) | Flowable |
|---------|----------|-------------------|----------|
| **Workflow Model** | Code-first (SDK) | BPMN 2.0 diagrams | BPMN 2.0, CMMN 1.1, DMN 1.3 |
| **Storage** | Append-only event log | Partitioned log + Elasticsearch | Relational database (SQL) |
| **Execution Model** | Durable execution with replay | Command sourcing with job polling | Relational state machine |
| **Languages** | Go, Java, TypeScript, Python, .NET | Java, Go, Python, Node.js, C#, PHP, Rust | Java (primary), REST API for others |
| **Human Tasks** | Via signals and activity code | Tasklist UI with forms | Built-in task management |
| **Monitoring** | Web UI with event history | Operate + Optimize dashboards | Admin UI + REST API |
| **Horizontal Scale** | Partitioned workflows + workers | Partitioned log + brokers | Single engine (cluster via DB) |
| **Compensation** | Manual (catch + compensating activity) | BPMN compensation events | BPMN compensation events |
| **Message Correlation** | Signal-based and external event | Message start events and correlation | Message correlation API |
| **Timer Support** | Native in workflow code | BPMN timer events | BPMN timer events |
| **External Dependencies** | SQL database (PostgreSQL/MySQL) | Elasticsearch, Zeebe brokers | SQL database only |
| **License** | MIT | Camunda Self-Managed (source available) | Apache 2.0 |
| **GitHub Stars** | 12,000+ | 4,000+ | 3,500+ |
| **Min. RAM (Single Node)** | ~512 MB | ~4 GB (with Elasticsearch) | ~512 MB |

---

## Performance and Scalability

### Temporal

Temporal's event sourcing architecture is optimized for **massive concurrency**. Each workflow partition handles approximately 10,000 concurrent workflows with sub-second task scheduling latency. The system scales horizontally by adding partitions — each partition operates independently with its own task queue and history shard.

Production benchmarks show Temporal handling 100,000 workflow starts per second on a 6-node cluster with PostgreSQL. The replay mechanism adds minimal overhead: a workflow with 500 events replays in under 10ms on modern hardware.

### Camunda 8

Zeebe's log-structured architecture targets **high-throughput process execution**. A single broker partition processes approximately 1,000 workflow instances per second. With 3 partitions (the typical starting configuration), throughput reaches 3,000 instances per second.

The Elasticsearch exporter introduces write amplification — every workflow event is written to the Zeebe log and then exported to Elasticsearch. For deployments processing over 10,000 events per second, plan for separate Elasticsearch clusters sized at 2x the Zeebe broker capacity.

### Flowable

Flowable's relational storage model prioritizes **consistency and queryability** over raw throughput. A single engine instance processes approximately 500–1,000 workflow instances per second depending on process complexity.

Horizontal scaling requires database-level clustering (read replicas for queries, primary for writes). This approach works well for moderate loads but does not match the partition-level parallelism of Temporal or Zeebe. For most enterprise workloads under 5,000 instances per second, Flowable's single-node performance is sufficient.

---

## Decision Framework

### Choose Temporal if:

- Your workflows are primarily code-driven service orchestrations
- You need guaranteed exactly-once execution with automatic retry
- Your team works across multiple programming languages
- You want the simplest operational model for developers (no BPMN diagrams to maintain)
- Throughput requirements exceed 10,000 concurrent workflows

### Choose Camunda 8 if:

- Business analysts need to model and modify workflows visually
- Human approval workflows are a core requirement
- You want a complete process management suite (Modeler, Operate, Optimize, Tasklist)
- You have existing BPMN 2.0 processes to migrate
- Process analytics and KPI tracking are important

### Choose Flowable if:

- Your stack is Java/Spring Boot and you want embedded execution
- You need case management (CMMN) or decision tables (DMN) alongside workflows
- You want to query workflow state directly via SQL for custom reporting
- Operational simplicity matters — a single database dependency is preferable
- You need Apache 2.0 licensing without enterprise edition restrictions

---

## Production Deployment Checklist

Regardless of which platform you choose, follow these practices for production readiness:

1. **TLS everywhere** — encrypt all inter-service communication. Temporal supports mTLS out of the box; Camunda and Flowable require reverse proxy configuration.
2. **Database backups** — configure automated snapshots of your PostgreSQL or MySQL databases. For Camunda, also back up Elasticsearch indices.
3. **Resource limits** — set CPU and memory limits on all containers. Zeebe brokers benefit from 4 GB minimum; Temporal workers scale with workload complexity.
4. **Health checks** — configure liveness and readiness probes. Temporal provides `/health` endpoints; Camunda exposes metrics on port 9600; Flowable uses Spring Boot Actuator.
5. **Log aggregation** — ship all engine logs to a centralized system. Workflow execution histories are valuable for debugging and compliance audits.
6. **Monitoring** — track workflow completion rates, average execution duration, failed workflow counts, and queue depths. All three platforms export Prometheus metrics.
7. **Version management** — never deploy incompatible workflow definition changes alongside running instances. Use canary deployments for worker updates and maintain backward-compatible versioning.

---

## Conclusion

The choice between Temporal, Camunda 8, and Flowable comes down to your team's workflow modeling preferences, operational constraints, and scaling requirements.

**Temporal** offers the most developer-friendly experience with code-first durable execution that eliminates checkpoint management entirely. It excels in microservices environments where workflows are expressed as code rather than diagrams.

**Camunda 8** provides the most complete enterprise process management platform with visual BPMN modeling, human task management, and process analytics. It's the natural choice when business stakeholders need to define and modify workflows.

**Flowable** delivers the simplest deployment model with embedded execution in a Spring Boot application and standard SQL storage. It's ideal for Java-centric teams that value operational simplicity and direct data access.

All three platforms are production-ready, actively maintained, and capable of orchestrating complex business processes at scale. The best approach is to prototype your most critical workflow on each platform and evaluate developer experience, operational overhead, and performance under your specific workload.
