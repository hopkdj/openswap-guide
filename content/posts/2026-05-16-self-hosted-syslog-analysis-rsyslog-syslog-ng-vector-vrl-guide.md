---
title: "Self-Hosted Syslog Analysis: rsyslog mmjsonparse vs syslog-ng PatternDB vs Vector VRL"
date: "2026-05-16"
tags: ["syslog", "logging", "log-analysis", "rsyslog", "syslog-ng", "vector", "observability"]
draft: false
---

Raw syslog messages are unstructured text streams that are difficult to search, alert on, and analyze at scale. Syslog analysis engines transform unstructured log data into structured, queryable formats by parsing fields, extracting patterns, and enriching messages with contextual metadata. This guide compares three powerful approaches to syslog analysis: rsyslog with mmjsonparse, syslog-ng with PatternDB, and Vector with Vector Remap Language (VRL).

## Why Structured Syslog Analysis Matters

Traditional syslog servers collect raw text messages in flat files. While this approach preserves the original data, it makes operational analysis extremely difficult:

- **Searching requires regex**: Finding specific events across millions of log lines demands complex regular expressions
- **Alerting is fragile**: Threshold-based alerts on unstructured text produce false positives and miss critical events
- **Correlation is impossible**: Without parsed fields, correlating events across services, hosts, and time windows is manual and error-prone
- **Compliance reporting is tedious**: Audit reports require extracting specific fields (user, action, timestamp, source IP) from variable-format text

Structured syslog analysis solves these problems by parsing raw log messages into named fields at ingestion time. Instead of searching raw text, you query structured data: `source_ip=10.0.1.5 AND severity=error AND facility=auth`.

For foundational syslog server setup, see our [rsyslog vs syslog-ng vs Vector comparison](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/). If you need log forwarding to centralized systems, check our [Fluent Bit vs Vector vs OTEL Collector guide](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/). For log sampling strategies, our [log sampling guide](../2026-05-07-self-hosted-log-sampling-vector-fluentbit-loki-guide/) covers volume reduction techniques.

## rsyslog mmjsonparse: JSON-Aware Syslog Processing

[rsyslog](https://www.rsyslog.com/) is the default syslog daemon on most Linux distributions. Its `mmjsonparse` module provides JSON parsing capabilities, enabling rsyslog to extract structured data from JSON-formatted syslog messages and CEE/Lumberjack format logs.

### How mmjsonparse Works

The mmjsonparse module intercepts syslog messages as they arrive, attempts to parse the message payload as JSON, and if successful, makes the parsed fields available to rsyslog templates and output actions. It supports the CEE cookie prefix (`@cee:`) that indicates JSON-formatted content within syslog messages.

### Installation and Configuration

```bash
# Install rsyslog (usually pre-installed)
# On Ubuntu/Debian:
sudo apt install rsyslog

# On RHEL/CentOS/Rocky:
sudo dnf install rsyslog
```

```conf
# /etc/rsyslog.d/10-json-parse.conf

# Load required modules
module(load="mmjsonparse")
module(load="mmnormalize")

# Parse JSON from messages with @cee: prefix
action(type="mmjsonparse")

# Alternative: parse all messages (without @cee: prefix requirement)
# action(type="mmjsonparse" name="parse-all")

# Extract fields and write to structured output
template(name="structured-json" type="string"
  string="{"timestamp":"%timegenerated:::date-rfc3339%","host":"%hostname%","severity":"%syslogseverity-text%","facility":"%syslogfacility-text%","tag":"%syslogtag%","message":"%msg:::json%"}
"
)

# Route parsed messages to Elasticsearch
action(
  type="omelasticsearch"
  server="http://elasticsearch:9200"
  template="structured-json"
  searchIndex="syslog-%$YEAR%.%$MONTH%.%$DAY%"
    searchType="syslog"
    errorfile="/var/log/rsyslog/es-errors.log"
)

# Also write parsed messages to local structured log
action(
  type="omfile"
  file="/var/log/syslog-structured.log"
  template="structured-json"
)
```

### Advanced: mmnormalize for Pattern-Based Parsing

When log messages are not JSON-formatted, the `mmnormalize` module uses liblognorm rulebases to parse arbitrary text formats:

```conf
# /etc/rsyslog.d/20-normalize.conf
module(load="mmnormalize")

# Load rulebase file
action(type="mmnormalize"
  ruleBase="/etc/rsyslog.d/rules.rb"
)

# Example rulebase (rules.rb):
# version=2
# rule=:%app_name:word%[%pid:number%]: %severity:word%: %message:rest%
```

### Docker Compose for rsyslog Processing Stack

```yaml
version: "3.8"
services:
  rsyslog:
    image: rsyslog/syslog_appliance_alpine:latest
    container_name: rsyslog
    ports:
      - "514:514/udp"
      - "514:514/tcp"
    volumes:
      - ./rsyslog.conf:/etc/rsyslog.conf
      - ./rules.rb:/etc/rsyslog.d/rules.rb
      - syslog-data:/var/spool/rsyslog
    restart: unless-stopped

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  syslog-data:
  es-data:
```

### Pros and Cons

| Feature | rsyslog mmjsonparse |
|---------|---------------------|
| JSON parsing | Native (@cee: format) |
| Pattern parsing | Via mmnormalize + liblognorm |
| Performance | Very high (C-based) |
| Installation | Pre-installed on most distros |
| Learning curve | Medium (rsyslog config syntax) |
| Output destinations | 80+ modules (file, ES, Kafka, etc.) |
| Field extraction | Template-based |
| Enrichment | Limited (property replacer) |

## syslog-ng PatternDB: Database-Driven Log Classification

[syslog-ng](https://www.syslog-ng.com/) offers PatternDB, a powerful log classification and parsing engine that uses XML-defined pattern databases to parse, classify, and enrich syslog messages in real time.

### How PatternDB Works

PatternDB matches incoming log messages against a database of predefined patterns. When a match is found, it extracts named fields, assigns classification tags (security, system, application), and can generate alerts based on message context. Unlike simple regex matching, PatternDB uses a decision-tree algorithm for efficient pattern matching at scale.

### PatternDB Configuration

```conf
# /etc/syslog-ng/syslog-ng.conf

@version: 4.3

source s_network {
  syslog(transport(tcp) port(514));
  syslog(transport(udp) port(514));
};

# Load PatternDB parser
parser p_classify {
  db-parser(
    file("/etc/syslog-ng/patterndb.xml")
    drop-unmatched(no)
  );
};

# Enrich matched messages
filter f_security {
  match("security" value(".classifier.class"))
  or match("violation" value(".classifier.class"));
};

# Route classified messages
destination d_security {
  file("/var/log/security-classified.log"
    template("${ISODATE} ${HOST} ${CLASSIFIER.CLASS} ${CLASSIFIER.RULE_ID} ${MESSAGE}
")
  );
};

destination d_elasticsearch {
  elasticsearch2(
    index("syslog-${YEAR}.${MONTH}.${DAY}")
    type("")
    url("http://elasticsearch:9200")
    template("$(format-json --scope rfc5424 --scope nv-pairs --exclude DATE --key ISODATE)")
  );
};

log {
  source(s_network);
  parser(p_classify);
  filter(f_security);
  destination(d_security);
  flags(final);
};

log {
  source(s_network);
  parser(p_classify);
  destination(d_elasticsearch);
};
```

### PatternDB XML Definition

```xml
<!-- /etc/syslog-ng/patterndb.xml -->
<patterndb version="4" pub_date="2026-05-16">
  <ruleset name="sshd" id="ssh-ruleset">
    <pattern>sshd</pattern>
    <rules>
      <rule provider="openswap" id="sshd-accepted" class="system">
        <patterns>
          <pattern>Accepted @ESTRING:AUTH_METHOD: @for @ESTRING:USERNAME: @from @ESTRING:SOURCE_IP: @port @ESTRING:PORT_NUMBER: @ssh2</pattern>
          <pattern>Accepted publickey for @ESTRING:USERNAME: @from @ESTRING:SOURCE_IP: @port @ESTRING:PORT_NUMBER: @ssh2</pattern>
        </patterns>
        <examples>
          <example>
            <test_message program="sshd">Accepted publickey for admin from 192.168.1.50 port 52314 ssh2</test_message>
            <test_values>
              <test_value name="USERNAME">admin</test_value>
              <test_value name="SOURCE_IP">192.168.1.50</test_value>
              <test_value name="PORT_NUMBER">52314</test_value>
              <test_value name="AUTH_METHOD">publickey</test_value>
            </test_values>
          </example>
        </examples>
      </rule>
      <rule provider="openswap" id="sshd-failed" class="security">
        <patterns>
          <pattern>Failed @ESTRING:AUTH_METHOD: @for @ESTRING:USERNAME: @from @ESTRING:SOURCE_IP: @port @ESTRING:PORT_NUMBER: @ssh2</pattern>
        </patterns>
        <values>
          <value name="ALERT_LEVEL">high</value>
        </values>
      </rule>
    </rules>
  </ruleset>
</patterndb>
```

### Docker Compose for syslog-ng Stack

```yaml
version: "3.8"
services:
  syslog-ng:
    image: balabit/syslog-ng:4.3
    container_name: syslog-ng
    ports:
      - "514:514/udp"
      - "514:514/tcp"
      - "601:601/tcp"
    volumes:
      - ./syslog-ng.conf:/etc/syslog-ng/syslog-ng.conf
      - ./patterndb.xml:/etc/syslog-ng/patterndb.xml
    restart: unless-stopped

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

volumes:
  es-data:
```

### Pros and Cons

| Feature | syslog-ng PatternDB |
|---------|---------------------|
| Pattern matching | Decision-tree based (fast) |
| Classification | Built-in class system |
| Field extraction | Named field extraction from patterns |
| Alerting | Value-based alert generation |
| Pattern authoring | XML format with examples/testing |
| Performance | High (optimized C implementation) |
| Community patterns | Limited (custom authoring required) |
| Learning curve | Medium to high (XML pattern syntax) |

## Vector VRL: Programmable Log Transformation

[Vector](https://vector.dev/) by Datadog is a high-performance observability data pipeline that uses Vector Remap Language (VRL) for log parsing, transformation, and enrichment. VRL is a purpose-built language for data processing that combines the expressiveness of programming languages with the safety of static type checking.

### How VRL Works

VRL scripts are applied to each event as it flows through the Vector pipeline. The language provides built-in functions for parsing (regex, JSON, key-value, CSV), type conversion, conditional logic, and enrichment. Unlike regex-based parsers, VRL programs are statically analyzed before execution, ensuring type safety and catching errors at configuration time.

### Vector Configuration with VRL

```yaml
# vector.yaml
sources:
  syslog:
    type: syslog
    address: "0.0.0.0:514"
    mode: tcp
    max_length: 102400

transforms:
  parse_syslog:
    type: remap
    inputs:
      - syslog
    source: |
      # Parse standard syslog header
      . = parse_syslog!(.message)

      # Parse application-specific JSON payload
      if starts_with!(.message, "@cee:") {
        payload = parse_json!(strip!(.message, ["@cee:", " "]))
        ., err = merge(., payload)
      }

      # Enrich with geo data for source IPs
      if exists(.source_ip) {
        geo = get_enrichment_table_record("geoip", { "ip": .source_ip })
        if !is_null(geo) {
          .geo_country = geo.country_iso_code
          .geo_city = geo.city_name
        }
      }

      # Classify security events
      .event_class = if contains!(.message, "Failed password") {
        "auth_failure"
      } else if contains!(.message, "Accepted") {
        "auth_success"
      } else if contains!(.message, "sudo") {
        "privilege_escalation"
      } else {
        "other"
      }

      # Set severity level
      .severity_label = if .severity >= 4 {
        "error"
      } else if .severity >= 3 {
        "warning"
      } else {
        "info"
      }

sinks:
  elasticsearch:
    type: elasticsearch
    inputs:
      - parse_syslog
    endpoints:
      - "http://elasticsearch:9200"
    index: "syslog-%Y.%m.%d"
    encoding:
      codec: json

  local_file:
    type: file
    inputs:
      - parse_syslog
    path: "/var/log/vector/syslog-structured.log"
    encoding:
      codec: json
```

### Advanced VRL: Custom Parsing Functions

```yaml
transforms:
  parse_apache:
    type: remap
    inputs:
      - syslog
    source: |
      # Parse Apache/Nginx combined log format
      parsed, err = parse_regex(.message, r'^(?P<remote_addr>\S+) \S+ (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\] "(?P<request>[^"]*)" (?P<status>\d+) (?P<body_bytes_sent>\d+) "(?P<http_referer>[^"]*)" "(?P<http_user_agent>[^"]*)"')

      if err == null {
        .http = parsed
        .http.status = to_int!(parsed.status)
        .http.body_bytes_sent = to_int!(parsed.body_bytes_sent)

        # Classify response status
        .http.status_class = if .http.status >= 500 {
          "5xx"
        } else if .http.status >= 400 {
          "4xx"
        } else if .http.status >= 300 {
          "3xx"
        } else {
          "2xx"
        }

        # Extract request method and path
        req_parts, _ = parse_regex(.http.request, r'^(?P<method>\S+) (?P<path>\S+)')
        if req_parts != null {
          .http.method = req_parts.method
          .http.path = req_parts.path
        }
      }
```

### Docker Compose for Vector Pipeline

```yaml
version: "3.8"
services:
  vector:
    image: timberio/vector:0.38.0-alpine
    container_name: vector
    ports:
      - "514:514/tcp"
      - "514:514/udp"
      - "8686:8686"  # Vector API
    volumes:
      - ./vector.yaml:/etc/vector/vector.yaml:ro
      - vector-data:/var/lib/vector
    restart: unless-stopped

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

volumes:
  vector-data:
  es-data:
```

### Pros and Cons

| Feature | Vector VRL |
|---------|-----------|
| Language | Purpose-built remap language |
| Type safety | Static type checking at config time |
| Parsing functions | JSON, regex, key-value, CSV, syslog, grok |
| Performance | Very high (Rust-based) |
| Enrichment | Built-in lookup tables (geoip, etc.) |
| Error handling | Graceful error handling in scripts |
| Learning curve | Low to medium (VRL is designed for simplicity) |
| Community | Growing (Datadobacked) |

## Comparison Summary

| Feature | rsyslog mmjsonparse | syslog-ng PatternDB | Vector VRL |
|---------|---------------------|---------------------|------------|
| Parsing approach | JSON module + liblognorm | XML pattern database | VRL scripts |
| Performance | Very high | High | Very high |
| Pattern authoring | Rule files (.rb) | XML with test cases | VRL code |
| Type safety | None | Schema validation | Static type checking |
| Enrichment | Limited | Classifier values | Lookup tables |
| Installation | Pre-installed (Linux) | Package manager | Binary/Docker |
| Learning curve | Medium | High | Low-medium |
| Best for | Traditional Linux sysadmins | Enterprise log classification | Modern observability pipelines |

## Choosing the Right Syslog Analysis Engine

- **rsyslog mmjsonparse** is ideal when you need maximum compatibility with existing Linux infrastructure. It is pre-installed on most distributions and provides solid JSON and pattern-based parsing with minimal additional setup.

- **syslog-ng PatternDB** excels in environments that require structured log classification with formal pattern definitions. The XML-based pattern authoring with embedded test cases makes it suitable for compliance-heavy environments where parsing rules must be documented and validated.

- **Vector VRL** is the best choice for modern observability pipelines that need flexible, programmable log transformation. Its static type checking catches configuration errors before deployment, and its performance makes it suitable for high-volume log processing.

## FAQ

### Can rsyslog parse non-JSON log formats?
Yes. The `mmnormalize` module uses liblognorm rulebases to parse arbitrary text formats. You define patterns in `.rb` rule files that extract named fields from structured log messages (e.g., Apache access logs, sudo logs, SSH logs). This is more manual than VRL or PatternDB but works well for consistent log formats.

### Does syslog-ng PatternDB support dynamic pattern updates?
PatternDB patterns are loaded from XML files at startup. To update patterns, you must modify the XML file and reload syslog-ng (`systemctl reload syslog-ng`). Some deployments use a configuration management tool (Ansible, Puppet) to manage PatternDB files and trigger reloads automatically.

### Is VRL a general-purpose programming language?
No. VRL is a domain-specific language designed specifically for log transformation. It does not support loops, recursion, or arbitrary computation. This intentional limitation ensures that VRL programs always terminate and cannot introduce performance issues or security vulnerabilities into the data pipeline.

### Can I combine multiple syslog analysis engines?
Yes. A common pattern is to use rsyslog or syslog-ng as the syslog receiver (collecting from network devices and servers), then forward structured output to Vector for additional transformation and routing to multiple destinations (Elasticsearch, Loki, cloud storage).

### How do I test syslog parsing rules before deploying?
For rsyslog, use `rsyslogd -N1` to validate configuration syntax. For syslog-ng, use `syslog-ng --syntax-only`. For Vector, use `vector validate --config-yaml vector.yaml` to check VRL syntax and type safety. Vector also provides an online VRL playground at play.vrl.dev for testing scripts interactively.

### Which engine handles the highest log volume?
All three engines are high-performance. rsyslog and syslog-ng can process hundreds of thousands of messages per second on modern hardware. Vector, being written in Rust, achieves similar throughput with lower memory usage. For most deployments, the bottleneck is the output destination (Elasticsearch, disk I/O) rather than the parsing engine.

### Can these engines parse Windows Event Logs forwarded via syslog?
Windows Event Logs forwarded through NXLog or Winlogbeat as syslog can be parsed by all three engines. Vector has built-in `parse_windows_eventlog` function. rsyslog and syslog-ng require custom patterns or JSON parsing (if the forwarder sends JSON-formatted events).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Syslog Analysis: rsyslog mmjsonparse vs syslog-ng PatternDB vs Vector VRL",
  "description": "Compare rsyslog mmjsonparse, syslog-ng PatternDB, and Vector VRL for parsing, classifying, and enriching syslog messages into structured, queryable data.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
