---
title: "Self-Hosted Log Shipping: Vector vs Fluent Bit vs Logstash Complete Guide 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "monitoring", "devops"]
draft: false
description: "Compare Vector, Fluent Bit, and Logstash for self-hosted log shipping and log forwarding. Complete Docker setup guides, performance benchmarks, and architecture patterns."
---

Every distributed system generates logs — application output, access logs, error traces, audit events, and metrics. Getting those logs from dozens or hundreds of services into a central location for search, alerting, and analysis is one of the most fundamental infrastructure challenges. That is where log shippers come in.

Log shippers (also called log forwarders or log agents) collect logs from various sources, transform and enrich them, and ship them to a central destination like Elasticsearch, Loki, OpenSearch, or a cloud storage bucket. Running this pipeline yourself means full control over what data leaves your servers, how it is processed, and where it ends up.

In this guide, we compare the three most widely-used open-source log shippers: **Vector** by Datadog, **Fluent Bit** by CNCF, and **Logstash** by Elastic. We cover installation, configuration, performance characteristics, and the architecture patterns that make each tool shine.

## Why Self-Host Log Shipping?

Log data is often the most sensitive telemetry you collect. It contains user identifiers, internal IP addresses, application secrets that accidentally leak to stderr, database queries, and the full topology of your infrastructure. Self-hosting your log pipeline gives you several advantages:

**Data sovereignty.** Logs never traverse third-party networks. For regulated industries (healthcare, finance, government), keeping log data within your own infrastructure is often a compliance requirement.

**Cost control.** Commercial log ingestion services charge per gigabyte ingested. At scale, this can become the single largest line item in your observability budget. Self-hosted shippers let you send logs to your own storage — S3-compatible buckets, local filesystems, or self-hosted Elasticsearch clusters — without per-GB fees.

**Custom transformation.** Every team has unique log formats. Self-hosted shippers let you write custom parsing rules, redact sensitive fields, add metadata, and reshape events before they reach your storage layer.

**Resilience.** When your central logging backend goes down, a self-hosted shipper can buffer logs locally and retry delivery, preventing data loss during outages.

**No vendor lock-in.** Your log pipeline configuration is portable. Switch your backend from Elasticsearch to Loki to OpenSearch without changing your collection layer.

## Vector: Best for Performance and Reliability

Vector is a high-performance observability data pipeline built in Rust by Datadog. It collects, transforms, and routes logs, metrics, and traces with a focus on reliability, speed, and memory safety. Vector has become the go-to choice for teams that need to process large volumes of telemetry with minimal resource overhead.

### Key Features

- **Built in Rust** — memory-safe, zero garbage collection pauses, minimal CPU overhead
- **At-least-once delivery** — disk-buffered queues ensure no data is lost during restarts or network failures
- **Built-in transforms** — remap language for parsing, redacting, enriching, and reshaping events
- **Multi-format support** — collects logs, metrics, and traces in a single agent
- **Topology awareness** — understand exactly how data flows through your pipeline with the `vector top` command
- **Hot-reloadable configuration** — change pipelines without restarting the agent

### Installation with [docker](https://www.docker.com/) Compose

Run Vector as a daemon on each node, collecting logs from local files, Docker containers, or systemd journal:

```yaml
# docker-compose-vector.yml
services:
  vector-agent:
    image: timberio/vector:0.46.0-distroless-libc
    volumes:
      - ./vector.toml:/etc/vector/vector.toml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/log:/var/log:ro
      - vector-data:/var/lib/vector
    ports:
      - "8686:8686"
    environment:
      - VECTOR_LOG=info
    restart: unless-stopped

volumes:
  vector-data:
```

### Configuration Example

Vector uses TOML configuration. Here is a production setup that collects Docker container logs, parses JSON output, redacts sensitive fields, and ships to Loki:

```toml
# vector.toml

[sources.docker_logs]
type = "docker_logs"
include_containers = ["api-server", "web-frontend", "worker"]

[sources.syslog]
type = "syslog"
address = "0.0.0.0:5514"
mode = "tcp"

[transforms.parse_json]
type = "remap"
inputs = ["docker_logs"]
source = '''
. = parse_json!(.message) ?? .
del(.stream)
del(.container.created_at)
'''

[transforms.redact_secrets]
type = "remap"
inputs = ["parse_json", "syslog"]
source = '''
if exists(.password) { .password = "[REDACTED]" }
if exists(.token) { .token = "[REDACTED]" }
if exists(.api_key) { .api_key = "[REDACTED]" }
if exists(.authorization) { .authorization = "[REDACTED]" }
.host = get_hostname!()
'''

[sinks.loki]
type = "loki"
inputs = ["redact_secrets"]
endpoint = "http://loki:3100"
encoding.codec = "json"

[sinks.loki.labels]
host = "{{ host }}"
service = "{{ service_name }}"
environment = "production"

[sinks.loki.buffer]
type = "disk"
max_size = 1073741824  # 1 GB disk buffer

[api]
enabled = true
address = "0.0.0.0:8686"
```

Start the agent:

```bash
docker compose -f docker-compose-vector.yml up -[kubernetes](https://kubernetes.io/) Collecting from Kubernetes

Vector can run as a DaemonSet in Kubernetes, collecting logs from every node:

```yaml
# vector-k8s-daemonset.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vector-agent-config
  namespace: logging
data:
  vector.toml: |
    [sources.k8s_logs]
    type = "kubernetes_logs"

    [transforms.k8s_enrich]
    type = "remap"
    inputs = ["k8s_logs"]
    source = '''
    .cluster = "production-us-east-1"
    .environment = "production"
    '''

    [sinks.loki]
    type = "loki"
    inputs = ["k8s_enrich"]
    endpoint = "http://loki.logging.svc:3100"
    encoding.codec = "json"

---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: vector-agent
  namespace: logging
spec:
  selector:
    matchLabels:
      app: vector-agent
  template:
    metadata:
      labels:
        app: vector-agent
    spec:
      containers:
        - name: vector
          image: timberio/vector:0.46.0-distroless-libc
          args: ["--config", "/etc/vector/vector.toml"]
          volumeMounts:
            - name: config
              mountPath: /etc/vector
            - name: data
              mountPath: /var/lib/vector
            - name: var-log
              mountPath: /var/log
            - name: var-lib
              mountPath: /var/lib
          resources:
            limits:
              memory: "256Mi"
              cpu: "200m"
      volumes:
        - name: config
          configMap:
            name: vector-agent-config
        - name: data
          emptyDir: {}
        - name: var-log
          hostPath:
            path: /var/log
        - name: var-lib
          hostPath:
            path: /var/lib
```

Apply with `kubectl apply -f vector-k8s-daemonset.yaml`.

## Fluent Bit: Best for Lightweight Edge Collection

Fluent Bit is a fast and lightweight log processor and forwarder built in C. It is a CNCF graduated project and the de facto standard for edge log collection, especially in resource-constrained environments. Fluent Bit is designed to run with minimal memory (often under 10 MB) and low CPU usage.

### Key Features

- **Written in C** — extremely low memory footprint and CPU usage
- **CNCF graduated project** — production-hardened, widely adopted in Kubernetes
- **Rich plugin ecosystem** — 100+ input, filter, and output plugins
- **Native Kubernetes integration** — automatic pod and namespace metadata enrichment
- **Stream processing** — SQL-like queries for real-time log analysis
- **Multi-tenant routing** — route different log streams to different backends

### Installation with Docker Compose

```yaml
# docker-compose-fluentbit.yml
services:
  fluent-bit:
    image: fluent/fluent-bit:3.2
    volumes:
      - ./fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro
      - ./parsers.conf:/fluent-bit/etc/parsers.conf:ro
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    ports:
      - "2020:2020"
      - "5514:5514"
      - "5514:5514/udp"
    restart: unless-stopped
```

### Configuration Example

Fluent Bit uses an INI-style configuration with sections for inputs, filters, and outputs:

```ini
# fluent-bit.conf

[SERVICE]
    Flush        5
    Daemon       Off
    Log_Level    info
    Parsers_File parsers.conf
    HTTP_Server  On
    HTTP_Listen  0.0.0.0
    HTTP_Port    2020

[INPUT]
    Name         tail
    Path         /var/log/containers/*.log
    Parser       docker
    Tag          kube.*
    Refresh_Interval 10
    Mem_Buf_Limit 5MB
    Skip_Long_Lines On
    DB           /tmp/flb_kube.db

[INPUT]
    Name         syslog
    Listen       0.0.0.0
    Port         5514
    Mode         tcp
    Parser       syslog-rfc5424
    Tag          syslog.*

[FILTER]
    Name         kubernetes
    Match        kube.*
    Kube_URL     https://kubernetes.default.svc:443
    Kube_CA_File /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File /var/run/secrets/kubernetes.io/serviceaccount/token
    Merge_Log    On
    K8S-Logging.Parser On
    K8S-Logging.Exclude On

[FILTER]
    Name         grep
    Match        kube.*
    Exclude      log ^\s*$

[FILTER]
    Name         nest
    Match        kube.*
    Operation    lift
    Nested_under kubernetes
    Add_prefix   kubernetes.

[OUTPUT]
    Name         loki
    Match        *
    Url          http://loki:3100/loki/api/v1/push
    Labels       job=fluentbit, host=${HOSTNAME}, env=production
    Auto_Kubernetes_Labels On
    Line_Format  json

[OUTPUT]
    Name         file
    Match        syslog.*
    Path         /var/log/archive
    File         syslog-%Y%m%d.log
```

```ini
# parsers.conf

[PARSER]
    Name         docker
    Format       json
    Time_Key     time
    Time_Format  %Y-%m-%dT%H:%M:%S.%L%z
    Time_Keep    On
    Decode_Field_As json message

[PARSER]
    Name         syslog-rfc5424
    Format       regex
    Regex        ^\<(?<pri>[0-9]{1,5})\>1 (?<time>[^ ]+) (?<host>[^ ]+) (?<ident>[^ ]+) (?<pid>[-0-9]+) (?<msgid>[^ ]+) (?<extradata>(\[(.*?)\]|-)) (?<message>.+)$
    Time_Key     time
    Time_Format  %Y-%m-%dT%H:%M:%S.%L%z
```

Start the collector:

```bash
docker compose -f docker-compose-fluentbit.yml up -d
```

### Fluent Bit Stream Processing

Fluent Bit includes a stream processing engine that lets you run SQL-like queries on log streams in real time:

```sql
-- Count error logs per service over 1-minute windows
CREATE STREAM error_counts AS
SELECT
  kubernetes_labels['app'] AS service,
  COUNT(*) AS error_count
FROM STREAM:kube.*
WHERE log LIKE '%ERROR%'
WINDOW TUMBLING (1 MINUTE);
```

## Logstash: Best for Com[plex](https://www.plex.tv/) Transformation Pipelines

Logstash is the oldest and most feature-rich log shipper in the Elastic ecosystem. Written in Java with JRuby for its plugin system, Logstash excels at complex data transformation, enrichment, and multi-stage processing pipelines. If your log processing requirements involve heavy parsing, external API lookups, geo-IP enrichment, or multi-step data manipulation, Logstash is the most capable option.

### Key Features

- **200+ plugins** — the largest plugin ecosystem of any log shipper
- **Powerful filter pipeline** — grok parsing, mutate, geoip, dns, ruby, and more
- **JRuby plugin system** — write custom filters in Ruby for unlimited flexibility
- **Deep Elastic integration** — native Elasticsearch, Beats, and Kibana support
- **Dead letter queue** — captures events that fail processing for later analysis
- **Persistent queues** — disk-based queues for reliable delivery

### Installation with Docker Compose

```yaml
# docker-compose-logstash.yml
services:
  logstash:
    image: docker.elastic.co/logstash/logstash:8.17.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
      - ./logstash.yml:/usr/share/logstash/config/logstash.yml:ro
      - logstash-data:/usr/share/logstash/data
    ports:
      - "5044:5044"
      - "5514:5514"
      - "9600:9600"
    environment:
      - LS_JAVA_OPTS=-Xmx1g -Xms1g
    restart: unless-stopped

volumes:
  logstash-data:
```

### Configuration Example

Logstash configuration uses a three-stage pipeline: input, filter, and output:

```ruby
# logstash.conf

input {
  beats {
    port => 5044
    type => "beats"
  }

  tcp {
    port => 5514
    type => "syslog"
  }

  file {
    path => "/var/log/app/*.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    type => "app-log"
  }
}

filter {
  # Parse syslog messages
  if [type] == "syslog" {
    grok {
      match => { "message" => "%{SYSLOG5424PRI:priority}%{NONNEGINT:version} +(?:%{TIMESTAMP_ISO8601:timestamp}|-) +(?:%{HOSTNAME:hostname}|-) +(?:%{NOTSPACE:app_name}|-) +(?:%{NOTSPACE:proc_id}|-) +(?:%{NOTSPACE:msg_id}|-) +(?:%{DATA:structured_data}|-) +%{GREEDYDATA:log_message}" }
    }
    date {
      match => [ "timestamp", "ISO8601" ]
      target => "@timestamp"
    }
  }

  # Parse application JSON logs
  if [type] == "app-log" {
    json {
      source => "message"
      target => "parsed"
    }
    mutate {
      rename => { "[parsed][level]" => "log_level" }
      rename => { "[parsed][msg]" => "message" }
      remove_field => [ "parsed" ]
    }
  }

  # Add geo-IP data for client addresses
  if [client_ip] {
    geoip {
      source => "client_ip"
      target => "geoip"
      database => "/usr/share/logstash/GeoLite2-City.mmdb"
    }
  }

  # Redact sensitive fields
  mutate {
    gsub => [
      "message", "(password[\"': ]+)[^\"',}]+", "\1[REDACTED]",
      "message", "(token[\"': ]+)[^\"',}]+", "\1[REDACTED]",
      "message", "(api_key[\"': ]+)[^\"',}]+", "\1[REDACTED]"
    ]
  }

  # Add metadata
  mutate {
    add_field => {
      "environment" => "production"
      "datacenter" => "us-east-1"
    }
  }
}

output {
  # Primary destination: Loki
  loki {
    url => "http://loki:3100/loki/api/v1/push"
    include_labels => ["type", "hostname", "environment", "log_level"]
  }

  # Secondary: Elasticsearch for deep search
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
    user => "elastic"
    password => "${ES_PASSWORD}"
  }

  # Fallback: local file for disaster recovery
  file {
    path => "/var/log/logstash/fallback-%{+YYYY-MM-dd}.log"
    codec => json_lines
  }
}
```

```yaml
# logstash.yml
node.name: logstash-prod-01
path.data: /usr/share/logstash/data
pipeline.workers: 4
pipeline.batch.size: 250
pipeline.batch.delay: 50
http.host: "0.0.0.0"
http.port: 9600
log.level: info
```

Start Logstash:

```bash
docker compose -f docker-compose-logstash.yml up -d
```

### Using the Dead Letter Queue

Logstash can capture events that fail processing — useful for debugging pipeline issues:

```ruby
# logstash.yml - enable dead letter queue
dead_letter_queue.enable: true
dead_letter_queue.max_bytes: 1073741824  # 1 GB
dead_letter_queue.storage_policy: drop_oldest
```

Failed events are stored and can be consumed by a separate Logstash pipeline for analysis:

```ruby
# dead-letter-pipeline.conf
input {
  dead_letter_queue {
    path => "/usr/share/logstash/data/dead_letter_queue"
    commit_offsets => true
  }
}

output {
  file {
    path => "/var/log/logstash/dlq/%{+YYYY-MM-dd}/failed-events.log"
    codec => json_lines
  }
}
```

## Head-to-Head Comparison

| Feature | Vector | Fluent Bit | Logstash |
|---|---|---|---|
| **Language** | Rust | C | Java (JRuby plugins) |
| **Memory usage** | 50-150 MB | 5-30 MB | 500 MB - 2 GB |
| **CPU overhead** | Very low | Extremely low | Moderate to high |
| **Throughput** | 500K+ events/sec | 200K+ events/sec | 50K-100K events/sec |
| **Guaranteed delivery** | ✅ Disk-buffered queues | ⚠️ Limited buffering | ✅ Persistent queues |
| **Log collection** | ✅ Files, Docker, K8s, syslog, TCP/UDP, HTTP | ✅ Files, Docker, K8s, syslog, TCP/UDP, HTTP | ✅ Files, Beats, syslog, TCP/UDP, HTTP, JDBC |
| **Transformation** | VRL (Remap language) | Lua, Stream Processor, grep/nest/modify | Grok, mutate, geoip, Ruby, 200+ filters |
| **Multi-format** | ✅ Logs + metrics + traces | ✅ Logs + metrics + traces | ✅ Logs + metrics |
| **Output destinations** | 40+ (Loki, ES, S3, Kafka, HTTP, etc.) | 60+ (Loki, ES, S3, Kafka, HTTP, etc.) | 100+ (ES, Loki, S3, Kafka, HTTP, etc.) |
| **Kubernetes native** | ✅ DaemonSet with K8s source | ✅ CNCF graduated, K8s filter | ⚠️ Requires Beats or Filebeat |
| **Configuration** | TOML (declarative) | INI-style (sections) | Ruby DSL (pipeline) |
| **Hot reload** | ✅ Config changes without restart | ⚠️ Limited | ⚠️ Pipeline reload (some plugins) |
| **Metrics endpoint** | ✅ Built-in Prometheus metrics | ✅ HTTP monitoring | ✅ HTTP + JMX |
| **Plugin ecosystem** | Growing (Rust-based) | Large (C-based) | Largest (JRuby-based) |
| **Best for** | High-throughput, low-resource pipelines | Edge collection, IoT, containers | Complex transformation, Elastic stack |

## Choosing the Right Log Shipper

**Choose Vector if:**
- You need the highest throughput with the lowest resource usage
- You want guaranteed delivery with disk-buffered queues
- You value memory safety and zero garbage collection pauses
- You need a unified pipeline for logs, metrics, and traces
- You want a modern, actively developed tool with excellent ergonomics

**Choose Fluent Bit if:**
- You are running in resource-constrained environments (edge, IoT, small VMs)
- You need the smallest possible memory footprint
- You want a CNCF graduated project with massive community adoption
- You run Kubernetes and want the standard DaemonSet log collector
- You need stream processing with SQL-like queries on log data

**Choose Logstash if:**
- You need complex, multi-stage transformation pipelines
- You already run the Elastic Stack (Elasticsearch, Kibana, Beats)
- You need geo-IP enrichment, DNS lookups, or external API calls during processing
- You want the largest plugin ecosystem with 200+ inputs, filters, and outputs
- You need the dead letter queue for debugging failed events

## Production Architecture: Combining All Three

In large-scale deployments, the best architecture often combines multiple shippers at different layers:

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  App Server  │  │  App Server  │  │  App Server  │
│  Fluent Bit  │  │  Fluent Bit  │  │  Fluent Bit  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └────────┬────────┘────────┬────────┘
                │                 │
         ┌──────▼──────┐   ┌──────▼──────┐
         │   Vector    │   │   Vector    │
         │  (aggregator│   │  (aggregator│
         │   layer)    │   │   layer)    │
         └──────┬──────┘   └──────┬──────┘
                │                 │
                └────────┬────────┘
                         │
                  ┌──────▼──────┐
                  │  Logstash   │
                  │(transform   │
                  │   layer)    │
                  └──────┬──────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │  Loki  │ │  S3    │ │  ES    │
         │(search)│ │(archive│ │(deep   │
         │        │ │ store) │ │ search)│
         └────────┘ └────────┘ └────────┘
```

In this architecture:
1. **Fluent Bit** runs on every node, collecting logs with minimal overhead
2. **Vector** aggregates and routes logs from multiple nodes, handling retries and buffering
3. **Logstash** performs heavy transformation, enrichment, and multi-output routing
4. Logs reach **Loki** for fast search, **S3** for long-term archival, and **Elasticsearch** for deep analysis

This layered approach gives you the lightweight collection of Fluent Bit, the reliability of Vector, and the transformation power of Logstash — each doing what it does best.

## Monitoring Your Log Pipeline

Whichever shipper you choose, monitor the pipeline itself:

```bash
# Vector health check
curl http://localhost:8686/health

# Fluent Bit health check
curl http://localhost:2020/api/v1/metrics/prometheus

# Logstash health check
curl http://localhost:9600/_node/stats

# Check disk buffer usage (Vector)
curl http://localhost:8686/health | jq '.components.buffers'
```

Set up alerts for buffer fullness, error rates, and output lag:

```bash
# Alert on Vector buffer exceeding 80% capacity
curl -s http://localhost:8686/metrics | \
  grep vector_buffer_max_size_bytes | \
  awk '{if ($2 > 858993459) print "ALERT: Vector buffer > 80% full"}'
```

## Conclusion

Self-hosted log shipping is the foundation of any serious observability stack. Vector leads on performance and reliability with its Rust implementation and guaranteed delivery semantics. Fluent Bit dominates the edge collection space with its tiny footprint and CNCF pedigree. Logstash remains unmatched for complex transformation pipelines with its vast plugin ecosystem and deep Elastic Stack integration.

Start with the tool that matches your constraints: Fluent Bit for resource-limited environments, Vector for high-throughput production systems, or Logstash for heavy data transformation needs. As your infrastructure grows, combine them in a layered architecture where each handles the workload it was designed for. Your logs are too important to lose — build a pipeline you can trust.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
