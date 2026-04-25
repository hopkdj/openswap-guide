---
title: "Apollo vs Nacos vs Consul KV: Best Self-Hosted Configuration Management 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "microservices", "configuration"]
draft: false
description: "Compare Apollo, Nacos, and Consul KV for self-hosted configuration management. Includes Docker Compose setups, feature comparison, and deployment strategies for microservice environments."
---

When you are running dozens or hundreds of microservices, managing configuration through environment variables and scattered config files becomes unmanageable. You need a centralized configuration management system that supports dynamic updates, version control, namespace isolation, and audit trails — all running on your own infrastructure.

This guide compares three mature, self-hosted configuration management platforms: **Apollo** (Ctrip/ApolloConfig), **Nacos** (Alibaba), and **Consul KV** (HashiCorp). Each brings a different philosophy to the problem, and the right choice depends on your team size, language ecosystem, and operational maturity.

## Why Self-Host Your Configuration Management

Third-party config services like AWS AppConfig, LaunchDarkly, or Split.io tie your configuration to a vendor. Self-hosting gives you:

- **Full data sovereignty** — configuration data never leaves your infrastructure
- **No per-seat or per-request pricing** — unlimited namespaces and clients at zero marginal cost
- **Low-latency access** — run the config server in your own data center or VPC
- **Deep integration** — connect to your existing authentication, monitoring, and deployment pipelines
- **Offline resilience** — configuration remains available even when external services go down

For organizations running compliance-heavy workloads (healthcare, finance, government), self-hosted configuration management is often a regulatory requirement, not an architectural preference.

## Apollo: Enterprise-Grade Configuration Center

**GitHub**: [apolloconfig/apollo](https://github.com/apolloconfig/apollo) | **Stars**: 29,761 | **Language**: Java | **Last Updated**: April 2026

Apollo was originally built at Ctrip to manage configuration for their massive microservice platform. It has since been open-sourced and adopted by hundreds of companies. Apollo treats configuration as a first-class citizen with a full-featured web portal for managing config across environments.

### Key Features

- **Environment isolation** — built-in DEV, FAT, UAT, and PROD environments with promotion workflows
- **Namespace management** — public and private namespaces with inheritance
- **Gray release** — gradual rollout of configuration changes to specific instances or IPs
- **Version history and rollback** — every change is tracked with full diff and one-click rollback
- **Permission management** — RBAC with department-level isolation
- **Release audit** — complete audit trail of who changed what and when
- **Multi-datacenter support** — cross-datacenter replication for disaster recovery

### Docker Compose Setup

Apollo requires MySQL and has multiple services. Here is a minimal single-node setup:

```yaml
version: "3.8"

services:
  apollo-db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: apollo123
      MYSQL_DATABASE: ApolloConfigDB
    ports:
      - "3306:3306"
    volumes:
      - apollo-db-data:/var/lib/mysql
    command: >
      --default-authentication-plugin=mysql_native_password
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_general_ci

  apollo-configservice:
    image: apolloconfig/apollo-configservice:2.3.0
    environment:
      - spring.datasource.url=jdbc:mysql://apollo-db:3306/ApolloConfigDB?characterEncoding=utf8
      - spring.datasource.username=root
      - spring.datasource.password=apollo123
    ports:
      - "8080:8080"
    depends_on:
      - apollo-db

  apollo-adminservice:
    image: apolloconfig/apollo-adminservice:2.3.0
    environment:
      - spring.datasource.url=jdbc:mysql://apollo-db:3306/ApolloConfigDB?characterEncoding=utf8
      - spring.datasource.username=root
      - spring.datasource.password=apollo123
    ports:
      - "8090:8090"
    depends_on:
      - apollo-db

  apollo-portal:
    image: apolloconfig/apollo-portal:2.3.0
    environment:
      - spring.datasource.url=jdbc:mysql://apollo-db:3306/ApolloConfigDB?characterEncoding=utf8
      - spring.datasource.username=root
      - spring.datasource.password=apollo123
      - APOLLO_PORTAL_ENVS=dev
      - dev_meta=http://apollo-configservice:8080
    ports:
      - "8070:8070"
    depends_on:
      - apollo-configservice
      - apollo-adminservice

volumes:
  apollo-db-data:
```

Apollo initializes its database schema automatically on first startup. You will need to import the SQL initialization scripts from the `scripts/sql` directory if using an external MySQL instance.

### Client Usage

Apollo provides native SDKs for Java, .NET, Node.js, Go, and Python. Here is the Java client setup:

```xml
<dependency>
    <groupId>com.ctrip.framework.apollo</groupId>
    <artifactId>apollo-client</artifactId>
    <version>2.3.0</version>
</dependency>
```

```java
import com.ctrip.framework.apollo.Config;
import com.ctrip.framework.apollo.ConfigChangeListener;
import com.ctrip.framework.apollo.model.ConfigChangeEvent;

// Get the default application config
Config config = ConfigService.getAppConfig();

// Read a property with fallback
String value = config.getProperty("database.url", "jdbc:mysql://localhost:3306/mydb");

// Listen for config changes
config.addChangeListener(new ConfigChangeListener() {
    @Override
    public void onChange(ConfigChangeEvent changeEvent) {
        for (String key : changeEvent.changedKeys()) {
            System.out.println("Config changed: " + key + " = " + changeEvent.getChange(key).getNewValue());
        }
    }
});
```

## Nacos: Dynamic Service Discovery and Configuration

**GitHub**: [alibaba/nacos](https://github.com/alibaba/nacos) | **Stars**: 32,904 | **Language**: Java | **Last Updated**: April 2026

Nacos (Dynamic Naming and Configuration Service) is Alibaba's open-source platform that combines service discovery, configuration management, and service metadata management in a single product. It is the de facto standard in the Spring Cloud Alibaba ecosystem.

### Key Features

- **Dual purpose** — service discovery (registry) and configuration management in one platform
- **Multiple config formats** — supports TEXT, JSON, XML, YAML, HTML, and Properties
- **Group and namespace isolation** — hierarchical organization for multi-tenant setups
- **Config history and diff** — full version history with comparison views
- **Listener-based push** — clients receive config updates via long-polling (no polling interval needed)
- **Beta publishing** — test configuration changes on a subset of instances before full rollout
- **Spring Cloud native** — deep integration with Spring Boot and Spring Cloud Alibaba
- **Cluster mode** — built-in support for multi-node Raft-based consensus

### Docker Compose Setup (Standalone)

Nacos can run in standalone mode for development or small teams, and cluster mode for production:

```yaml
version: "3.8"

services:
  nacos:
    image: nacos/nacos-server:v2.4.3
    container_name: nacos-standalone
    environment:
      - MODE=standalone
      - SPRING_DATASOURCE_PLATFORM=mysql
      - MYSQL_SERVICE_HOST=nacos-mysql
      - MYSQL_SERVICE_DB_NAME=nacos_config
      - MYSQL_SERVICE_USER=nacos
      - MYSQL_SERVICE_PASSWORD=nacos123
      - MYSQL_SERVICE_DB_PARAM=characterEncoding=utf8&connectTimeout=1000&socketTimeout=3000&autoReconnect=true&useSSL=false
    ports:
      - "8848:8848"
      - "9848:9848"
      - "9849:9849"
    depends_on:
      - nacos-mysql

  nacos-mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: nacos_config
      MYSQL_USER: nacos
      MYSQL_PASSWORD: nacos123
    ports:
      - "3306:3306"
    volumes:
      - nacos-db-data:/var/lib/mysql

volumes:
  nacos-db-data:
```

For production, set `MODE=cluster` and provide at least three Nacos nodes with a shared MySQL backend. Nacos uses Raft protocol for data consistency across cluster nodes.

### Client Usage

Nacos provides a REST API and native SDKs for Java, Go, Python, and C++:

```bash
# Publish a configuration via REST API
curl -X POST "http://localhost:8848/nacos/v1/cs/configs" \
  -d "dataId=application.yml&group=DEFAULT_GROUP&content=server:\n  port: 8080"

# Get a configuration
curl -X GET "http://localhost:8848/nacos/v1/cs/configs?dataId=application.yml&group=DEFAULT_GROUP"

# Subscribe to config changes via long-polling
curl -X POST "http://localhost:8848/nacos/v1/cs/configs/listener" \
  -d "Listening-Configs=application.yml+DEFAULT_GROUP+<md5-hash>"
```

For Spring Boot applications, the integration is even simpler:

```properties
# application.properties
spring.cloud.nacos.config.server-addr=localhost:8848
spring.cloud.nacos.config.namespace=your-namespace-id
spring.cloud.nacos.config.group=DEFAULT_GROUP
spring.cloud.nacos.config.file-extension=yaml
```

## Consul KV: Simple, Reliable Key-Value Store

**GitHub**: [hashicorp/consul](https://github.com/hashicorp/consul) | **Stars**: 29,858 | **Language**: Go | **Last Updated**: April 2026

Consul is HashiCorp's service networking platform. While it offers service mesh, service discovery, and service segmentation, its Key-Value (KV) store provides a simple, reliable way to manage configuration data. Consul KV is often chosen by teams already using Consul for service discovery — there is no additional infrastructure to deploy.

### Key Features

- **Consensus-based consistency** — Raft protocol ensures strong consistency across the cluster
- **Hierarchical key structure** — tree-like organization (`app/db/host`, `app/db/port`)
- **Watch mechanism** — blocking queries for real-time config updates (long-poll)
- **ACL integration** — fine-grained access control per key prefix
- **Sessions and locks** — distributed locking for coordination tasks
- **Multi-datacenter** — native cross-datacenter replication
- **mTLS built-in** — all communication encrypted with automatic certificate rotation
- **Lightweight** — single binary, no external database dependency

### Docker Compose Setup

Consul runs as a single binary with no external database requirement:

```yaml
version: "3.8"

services:
  consul-server:
    image: hashicorp/consul:1.20
    container_name: consul-server
    command: "agent -server -bootstrap-expect=1 -ui -client=0.0.0.0 -data-dir=/consul/data"
    ports:
      - "8500:8500"
      - "8600:8600/tcp"
      - "8600:8600/udp"
    volumes:
      - consul-data:/consul/data
      - ./consul-config:/consul/config
    environment:
      - CONSUL_BIND_INTERFACE=eth0

volumes:
  consul-data:
```

For production, use three or more server nodes with `-bootstrap-expect=3`:

```yaml
version: "3.8"

services:
  consul-1:
    image: hashicorp/consul:1.20
    command: "agent -server -bootstrap-expect=3 -ui -client=0.0.0.0 -data-dir=/consul/data -node=consul-1 -bind={{ GetInterfaceIP \"eth0\" }} -retry-join=consul-2 -retry-join=consul-3"
    ports:
      - "8500:8500"

  consul-2:
    image: hashicorp/consul:1.20
    command: "agent -server -bootstrap-expect=3 -client=0.0.0.0 -data-dir=/consul/data -node=consul-2 -bind={{ GetInterfaceIP \"eth0\" }} -retry-join=consul-1 -retry-join=consul-3"

  consul-3:
    image: hashicorp/consul:1.20
    command: "agent -server -bootstrap-expect=3 -client=0.0.0.0 -data-dir=/consul/data -node=consul-3 -bind={{ GetInterfaceIP \"eth0\" }} -retry-join=consul-1 -retry-join=consul-2"
```

### Client Usage

Consul KV is accessible via HTTP API, CLI, and language SDKs:

```bash
# Write a configuration
consul kv put app/database/host "db.internal.example.com"
consul kv put app/database/port "5432"

# Read a configuration
consul kv get app/database/host

# Watch for changes (blocks until value changes)
consul watch -type keyprefix -prefix "app/" /usr/local/bin/config-reload.sh

# Export all config under a prefix
consul kv export app/ > config.json
```

Here is a Go client example:

```go
package main

import (
    "fmt"
    consul "github.com/hashicorp/consul/api"
)

func main() {
    config := consul.DefaultConfig()
    config.Address = "localhost:8500"
    client, _ := consul.NewClient(config)

    // Write
    pair := &consul.KVPair{Key: "app/database/host", Value: []byte("db.internal")}
    client.KV().Put(pair, nil)

    // Read with blocking query (watch)
    opts := &consul.QueryOptions{WaitIndex: 0, WaitTime: 5000000000}
    pair, meta, _ := client.KV().Get("app/database/host", opts)
    fmt.Printf("Value: %s, Index: %d\n", string(pair.Value), meta.LastIndex)
}
```

## Feature Comparison

| Feature | Apollo | Nacos | Consul KV |
|---------|--------|-------|-----------|
| **Primary Purpose** | Config management | Config + service discovery | Service discovery + KV store |
| **Language** | Java | Java | Go |
| **GitHub Stars** | 29,761 | 32,904 | 29,858 |
| **Storage Backend** | MySQL | MySQL/Embedded Derby | Embedded BoltDB |
| **External DB Required** | Yes (MySQL) | Yes for production | No |
| **Web UI** | Full-featured portal | Built-in dashboard | Basic UI |
| **Namespace Isolation** | Yes (public/private) | Yes (hierarchical) | Yes (key prefixes) |
| **Environment Support** | Built-in (DEV/FAT/UAT/PROD) | Via namespace | Via key path |
| **Config Formats** | Properties, XML, JSON, YAML, Text | Properties, JSON, XML, YAML, HTML, Text | Raw key-value strings |
| **Gray Release** | Yes (IP-level targeting) | Yes (beta publishing) | No (manual rollout) |
| **Version History** | Full diff and rollback | Version history with diff | No (external tool needed) |
| **Permission Model** | RBAC with department isolation | Namespace-level ACL | ACL per key prefix |
| **Client Push Model** | Long-polling with fallback | Long-polling | Blocking queries (watch) |
| **Consensus Protocol** | N/A (relies on MySQL) | Raft (cluster mode) | Raft |
| **Multi-Datacenter** | Yes | Yes (sync/async) | Yes (native) |
| **mTLS Support** | Via reverse proxy | Via Nginx/gateway | Built-in |
| **Audit Trail** | Full audit log | Limited | Limited |
| **Ecosystem Integration** | Java, .NET, Go, Python, Node.js | Spring Cloud, Java, Go, Python | HashiCorp ecosystem, Go, all languages via API |
| **Resource Footprint** | High (3+ services + MySQL) | Medium (1 service + MySQL) | Low (single binary) |

## When to Choose Which Platform

### Choose Apollo When

- You need a full-featured configuration management portal with gray releases and audit trails
- Your organization has a Java/.NET-heavy ecosystem
- You need environment promotion workflows (DEV → UAT → PROD)
- You require per-namespace permission management and department-level isolation
- Your team values configuration version history with rollback capabilities

Apollo is the most configuration-focused of the three. It treats config management as a dedicated discipline, not a side feature. The trade-off is operational complexity — you are deploying and maintaining three separate Java services plus MySQL.

### Choose Nacos When

- You want both service discovery and configuration in a single platform
- You are building on Spring Cloud or Spring Cloud Alibaba
- You need multi-format configuration support (YAML, JSON, XML, Properties)
- You prefer a lighter operational footprint than Apollo (one service instead of three)
- You need Raft-based consistency without deploying a separate consensus layer

Nacos is the best "two-in-one" option. If you need a service registry anyway, adding configuration management costs almost nothing extra. The Spring Cloud integration is seamless, making it the default choice for JVM teams in that ecosystem.

### Choose Consul KV When

- You already use Consul for service discovery or service mesh
- You want the simplest possible operational footprint (single binary, no external DB)
- You need hierarchical key-value storage with fine-grained ACLs
- You are in a Go ecosystem or need language-agnostic HTTP API access
- You require mTLS encryption for all config communication out of the box
- You need distributed locking and session management alongside config

Consul KV is the most lightweight and operationally simple option. It is not a dedicated config management platform, so it lacks features like gray releases, version history, and a full UI. But for teams that value simplicity and already use Consul, it is the most natural choice.

## Migration and Interoperability

If you are evaluating a migration between platforms, consider these factors:

- **Apollo to Nacos**: Apollo's namespace and environment model maps to Nacos namespaces. Configuration content can be exported and imported via REST APIs.
- **Nacos to Consul KV**: Nacos group/dataId hierarchy maps to Consul key prefixes. You will need to build custom tooling for migration since Consul KV does not have batch import.
- **Consul KV to Apollo**: You will need to flatten Consul's key hierarchy into Apollo's namespace model. Apollo's import API supports batch creation from JSON.

For hybrid environments, some teams run Nacos for service discovery and Apollo for configuration, or Consul KV for infrastructure config and Nacos for application config. This works but adds operational overhead.

## Performance and Scalability

Apollo handles configuration distribution through its configservice layer, which caches data from MySQL and pushes updates to clients. In production deployments at Ctrip, Apollo manages configuration for tens of thousands of microservices. The bottleneck is typically the MySQL backend, so use a production-grade MySQL setup with read replicas.

Nacos uses embedded Derby for standalone mode and MySQL for cluster mode. Its long-polling mechanism means clients do not waste resources polling for changes. The Raft consensus protocol in cluster mode provides strong consistency across nodes. Nacos can handle hundreds of thousands of configuration items across thousands of clients.

Consul KV is embedded in the Consul agent itself using BoltDB. Read operations are served from local memory, making them extremely fast. Write operations go through Raft consensus, which adds latency but ensures consistency. For large-scale deployments, Consul recommends three to five server nodes per datacenter.

## Security Considerations

All three platforms support encryption in transit, but the implementation differs:

- **Apollo** relies on reverse proxy (Nginx) or application-level HTTPS for encryption. It does not have built-in mTLS.
- **Nacos** supports authentication via its own user system and can integrate with LDAP. HTTPS must be configured at the gateway level.
- **Consul** has built-in mTLS with automatic certificate rotation through its CA system. Every agent-to-agent and client-to-agent communication is encrypted by default.

For organizations with strict security requirements, Consul KV has the strongest out-of-the-box security posture. Apollo and Nacos require additional infrastructure setup to achieve the same level of protection.

For related reading, see our [service discovery comparison](../etcd-vs-consul-vs-zookeeper-self-hosted-service-discovery-guide-2026/) for how these tools compare as registries, our [distributed locking guide](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/) for coordination primitives, and our [configuration management overview](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/) for infrastructure-level alternatives.

## FAQ

### What is the difference between Apollo, Nacos, and Consul KV for configuration management?

Apollo is a dedicated configuration management platform with a full web portal, gray releases, and environment promotion workflows. Nacos combines configuration management with service discovery in a single platform, making it a good two-in-one choice for Spring Cloud teams. Consul KV is a simple key-value store built into the Consul service mesh platform — it is the most lightweight option but lacks advanced config management features like version history and gray releases.

### Can I use these tools without Docker?

Yes. All three platforms can be installed directly on bare metal or virtual machines. Apollo and Nacos require Java (JDK 8+) and MySQL. Consul is a single Go binary that runs without any external dependencies. Docker is recommended for easier deployment and management, but it is not required.

### Which platform has the lowest resource footprint?

Consul KV has the lowest footprint — it runs as a single binary with no external database. A minimal Consul agent uses approximately 100-200 MB of RAM. Nacos requires about 500 MB of RAM plus MySQL. Apollo requires three separate Java services plus MySQL, using approximately 1.5-2 GB of RAM total.

### Do these tools support hot reloading of configuration?

Yes, all three support dynamic configuration updates without restarting the application. Apollo and Nacos use long-polling to push changes to clients. Consul KV uses blocking queries (watch) to notify clients when a key changes. The application must implement a change listener callback to react to updates.

### Is there a free and open-source version of each tool?

Yes, all three are fully open-source and free to use. Apollo is licensed under Apache 2.0, Nacos under Apache 2.0, and Consul under the Mozilla Public License 2.0 (BUSL for newer versions — check the specific version license). HashiCorp changed Consul's license to BUSL 1.1 starting with version 1.17, which restricts commercial competition. For most internal use cases, this is not a concern.

### How do these tools handle configuration for hundreds of microservices?

Apollo uses namespace-based isolation where each microservice can have its own namespace with public and private configuration. Nacos uses a similar approach with groups and namespaces. Consul KV uses hierarchical key paths (e.g., `service-a/config`, `service-b/config`) with ACL policies that restrict access per prefix. All three platforms scale to hundreds or thousands of services when properly configured.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Apollo vs Nacos vs Consul KV: Best Self-Hosted Configuration Management 2026",
  "description": "Compare Apollo, Nacos, and Consul KV for self-hosted configuration management. Includes Docker Compose setups, feature comparison, and deployment strategies for microservice environments.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
