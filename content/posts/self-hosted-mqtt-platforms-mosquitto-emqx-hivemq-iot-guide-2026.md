---
title: "Best Self-Hosted MQTT Platforms for IoT: Mosquitto vs EMQX vs HiveMQ CE 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "privacy", "iot", "mqtt", "home-automation"]
draft: false
description: "Complete guide to self-hosted MQTT brokers for IoT and home automation. Compare Eclipse Mosquitto, EMQX, and HiveMQ Community Edition with Docker setup, configuration, and performance benchmarks."
---

The MQTT (Message Queuing Telemetry Transport) protocol has become the backbone of modern IoT communication. From smart home sensors to industrial telemetry systems, MQTT's lightweight publish-subscribe model makes it the go-to choice for device-to-device messaging. But relying on a cloud-hosted MQTT broker means your sensor data, home automation commands, and industrial metrics flow through someone else's servers. Self-hosting your MQTT broker gives you full control over your data, eliminates latency from distant cloud endpoints, and keeps your IoT ecosystem operational even when the internet goes down.

## Why Self-Host Your MQTT Broker

Running your own MQTT broker is one of the highest-impact upgrades you can make to a smart home or IoT infrastructure. Here is why self-hosting matters:

**Complete data ownership.** Every temperature reading, motion detection event, and device state change stays within your network. No telemetry data leaves your premises, no third-party analytics track your device usage patterns, and no cloud provider can monetize your sensor data.

**Zero-latency local control.** When your motion sensor triggers a light or your thermostat adjusts the HVAC, the round trip happens in milliseconds — not seconds. Cloud-hosted brokers add network latency that can make real-time automations feel sluggish. With a local broker, your smart home responds instantly.

**Offline resilience.** Internet outages should not brick your home automation. A self-hosted MQTT broker continues routing messages between local devices even when your WAN connection is down. Your lights, locks, and sensors keep working.

**Cost savings at scale.** Cloud MQTT services charge per connection, per message, or per bandwidth tier. Once you have dozens of sensors, cameras, and actuators, those costs add up. A self-hosted broker on a Raspberry Pi or a low-end VPS handles thousands of concurrent connections for the cost of electricity.

**Protocol compliance and customization.** Self-hosted brokers let you tune QoS levels, configure persistent sessions, set custom authentication backends, and implement bridge connections to other brokers — all without waiting for a cloud provider to add the feature.

## What Is MQTT and How Does It Work?

MQTT is a publish-subscribe messaging protocol designed for constrained devices and low-bandwidth networks. The architecture is simple:

1. **Publishers** send messages to a **topic** on the broker (e.g., `home/living-room/temperature`).
2. **Subscribers** register interest in one or more topics and receive matching messages.
3. The **broker** routes messages from publishers to all matching subscribers.

Key concepts that make MQTT powerful:

- **Quality of Service (QoS):** Level 0 (fire-and-forget), Level 1 (at-least-once delivery with acknowledgment), Level 2 (exactly-once delivery with four-step handshake).
- **Retained messages:** The broker stores the last message on a topic and delivers it immediately to new subscribers.
- **Last Will and Testament (LWT):** A message the broker publishes automatically if a client disconnects unexpectedly.
- **Topic wildcards:** `+` matches a single topic level (`home/+/temperature`), `#` matches multiple levels (`home/floor1/#`).
- **Bridging:** Connect two or more brokers to share messages across networks or geographic locations.

The current standard is MQTT 5.0, which adds reason codes, shared subscriptions, topic aliases, and message expiry. All three brokers covered in this guide support MQTT 5.0.

## Option 1: Eclipse Mosquitto

Mosquitto is the most widely deployed open-source MQTT broker, maintained by the Eclipse Foundation. It is lightweight, battle-tested, and the default broker for many home automation platforms including [home assistant](https://www.home-assistant.io/).

### Key Features

- Lightweight C implementation — uses ~5 MB RAM with no clients connected
- MQTT 3.1, 3.1.1, and 5.0 support
- Built-in WebSocket support for browser-based clients
- TLS/SSL encryption with certificate-based authentication
- Password file and plugin-based authentication
- Bridging to other MQTT brokers
- Available on virtua[docker](https://www.docker.com/)ery Linux distribution

### Docker Setup

The fastest way to get Mosquitto running:

```yaml
# docker-compose.yml
services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"    # MQTT
      - "9001:9001"    # WebSocket
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - iot-network

networks:
  iot-network:
    driver: bridge
```

Create the configuration file at `./mosquitto/config/mosquitto.conf`:

```conf
# mosquitto.conf
persistence true
persistence_location /mosquitto/data/

log_dest file /mosquitto/log/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information

# Require authentication
allow_anonymous false
password_file /mosquitto/config/passwd

# Listener configuration
listener 1883
protocol mqtt

listener 9001
protocol websockets

# TLS (uncomment and configure for production)
# listener 8883
# protocol mqtt
# cafile /mosquitto/config/ca.crt
# certfile /mosquitto/config/server.crt
# keyfile /mosquitto/config/server.key

# Auto-expire old retained messages (MQTT 5.0)
# max_packet_size 268435456
```

Generate a password file and start the broker:

```bash
# Create directory structure
mkdir -p mosquitto/{config,data,log}

# Create password file
docker run --rm -v $(pwd)/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto:2.0 \
  mosquitto_passwd -b /mosquitto/config/passwd mqttuser "your-secure-password"

# Start the broker
docker compose up -d
```

### Testing Your Mosquitto Instance

```bash
# Subscribe to all topics
docker exec mosquitto mosquitto_sub -u mqttuser -P "your-secure-password" -t "#" -v

# Publish a test message from another terminal
docker exec mosquitto mosquitto_pub -u mqttuser -P "your-secure-password" \
  -t "home/test" -m '{"temperature": 22.5, "humidity": 45}'
```

### Best Use Cases

Mosquitto excels in small-to-medium deployments: home automation with Home Assistant, Raspberry Pi projects, and scenarios where resource efficiency matters most. Its plugin ecosystem supports ACL rules, HTTP authentication, and Redis-backed persistence. The trade-off is that Mosquitto is a single-process broker — it does not support horizontal clustering natively. If you need high availability, you must use bridging with multiple independent instances.

## Option 2: EMQX

EMQX is a high-performance, distributed MQTT broker built in Erlang/OTP. It is designed for enterprise-scale IoT deployments with millions of concurrent connections and supports native clustering out of the box.

### Key Features

- Horizontally scalable cluster architecture — add nodes to increase capacity
- Millions of concurrent connections per cluster
- MQTT 3.1.1 and 5.0 with full feature support
- Built-in rule engine for data transformation and forwarding
- WebSocket, SSL/TLS, and HTTP API support
- Dashboard for monitoring and configuration (Web UI)
- Supports Kafka, PostgreSQL, MySQL, Redis, and MongoDB integration
- Multi-tenant support with virtual hosts
- Open-source core under Apache 2.0 license

### Docker Setup

EMQX runs as a single node for small deployments and scales to a cluster:

```yaml
# docker-compose.yml - Single Node
services:
  emqx:
    image: emqx/emqx:5.8
    container_name: emqx
    restart: unless-stopped
    environment:
      - EMQX_NAME=emqx-node1
      - EMQX_HOST=node1.emqx.local
      - EMQX_DASHBOARD__DEFAULT_PASSWORD=your-dashboard-password
    ports:
      - "1883:1883"       # MQTT TCP
      - "8883:8883"       # MQTT TLS
      - "8083:8083"       # MQTT WebSocket
      - "8084:8084"       # MQTT WebSocket TLS
      - "18083:18083"     # Dashboard
    volumes:
      - emqx-data:/opt/emqx/data
    networks:
      - iot-network

volumes:
  emqx-data:
    driver: local

networks:
  iot-network:
    driver: bridge
```

Start the broker:

```bash
docker compose up -d
```

Access the dashboard at `http://your-server:18083` with username `admin` and the password you set via `EMQX_DASHBOARD__DEFAULT_PASSWORD`.

### Configuring Authentication and ACL

Through the dashboard or via the API, you can create users and define access control lists. Here is an example using the REST API:

```bash
# Create an authentication user
curl -X POST "http://localhost:18083/api/v5/authentication" \
  -u "admin:your-dashboard-password" \
  -H "Content-Type: application/json" \
  -d '{
    "mechanism": "password_based",
    "backend": "built_in_database",
    "user_id_type": "username"
  }'

# Add a user to the built-in database
curl -X POST "http://localhost:18083/api/v5/authentication/built_in_database/users" \
  -u "admin:your-dashboard-password" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "sensor-gateway",
    "password": "sensor-secret"
  }'

# Create an ACL rule (only publish to sensor topics)
curl -X POST "http://localhost:18083/api/v5/authorization/rules" \
  -u "admin:your-dashboard-password" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "sensors/+/telemetry",
    "action": "publish",
    "access": "allow",
    "clientid": "sensor-gateway"
  }'
```

### Setting Up a Rule for Data Forwarding

EMQX's rule engine can transform and forward MQTT messages to external systems without custom code. This SQL-like rule forwards all temperature readings to a PostgreSQL database:

```sql
SELECT
  payload.temperature AS temp,
  payload.humidity AS hum,
  topic AS sensor_topic,
  NOW() AS timestamp
FROM
  "sensors/+/telemetry"
WHERE
  payload.temperature IS NOT NULL
```

Configure the action to insert into PostgreSQL:

```json
{
  "sql": "SELECT payload.temperature AS temp, payload.humidity AS hum, topic AS sensor_topic FROM \"sensors/+/telemetry\" WHERE payload.temperature IS NOT NULL",
  "actions": [
    {
      "type": "data_to_pgsql",
      "args": {
        "server": "postgres:5432",
        "database": "iot_data",
        "username": "iot_user",
        "password": "iot_password",
        "sql": "INSERT INTO sensor_readings (temperature, humidity, topic, recorded_at) VALUES (${temp}, ${hum}, ${sensor_topic}, ${timestamp})"
      }
    }
  ]
}
```

### Best Use Cases

EMQX is the right choice when you need enterprise-grade scalability. It handles millions of connections in a clustered setup, offers a powerful rule engine for data pipelines, and provides a polished dashboard for operations. Use it for industrial IoT, smart city deployments, large-scale home automation setups with hundreds of devices, or any scenario where you need built-in data transformation and forwarding.

## Option 3: HiveMQ Community Edition

HiveMQ Community Edition (CE) is the open-source version of the enterprise HiveMQ platform. Written in Java, it provides a robust MQTT 5.0 broker with a plugin-based extension system.

### Key Features

- Full MQTT 5.0 and 3.1.1 support
- Plugin-based extension architecture
- WebSocket support
- TLS/SSL encryption
- Retained message support with persistence
- Cluster support (limited in CE — full clustering is enterprise-only)
- Java-based, runs on any JVM platform
- Apache 2.0 open-source license
- Active community and commercial support option

### Docker Setup

```yaml
# docker-compose.yml
services:
  hivemq:
    image: hivemq/hivemq4:4.16
    container_name: hivemq-ce
    restart: unless-stopped
    ports:
      - "1883:1883"    # MQTT
      - "8000:8000"    # WebSocket
      - "8080:8080"    # Control Center
    volumes:
      - ./hivemq/conf:/opt/hivemq/conf
      - ./hivemq/data:/opt/hivemq/data
      - ./hivemq/extensions:/opt/hivemq/extensions
    environment:
      - HIVEMQ_LICENSE=community
    networks:
      - iot-network

networks:
  iot-network:
    driver: bridge
```

### Basic Configuration

HiveMQ's configuration uses XML. Create `./hivemq/conf/config.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<hivemq>
  <listeners>
    <!-- MQTT TCP listener -->
    <tcp-listener>
      <port>1883</port>
      <bind-address>0.0.0.0</bind-address>
    </tcp-listener>

    <!-- WebSocket listener -->
    <websocket-listener>
      <port>8000</port>
      <bind-address>0.0.0.0</bind-address>
    </websocket-listener>
  </listeners>

  <!-- Persistence configuration -->
  <persistence>
    <persist-client-sessions>true</persist-client-sessions>
    <persist-retained-messages>true</persist-retained-messages>
    <persist-queued-messages>true</persist-queued-messages>
  </persistence>

  <!-- Cluster mode (requires enterprise for full features) -->
  <cluster>
    <enabled>false</enabled>
  </cluster>

  <!-- Security: enable TLS for production -->
  <!--
  <tls-tcp-listener>
    <port>8883</port>
    <tls>
      <keystore>
        <path>/opt/hivemq/conf/keystore.jks</path>
        <password>keystore-password</password>
      </keystore>
    </tls>
  </tls-tcp-listener>
  -->
</hivemq>
```

Start the broker:

```bash
mkdir -p hivemq/{conf,data,extensions}
docker compose up -d
```

### Extending HiveMQ with Plugins

HiveMQ's strength is its extension system. You can drop Java JAR files into the `extensions/` directory to add authentication, authorization, message transformation, and more. Here is an example of the directory structure for a custom authentication extension:

```
hivemq/extensions/
└── custom-auth/
    ├── extension.xml          # Extension metadata
    ├── custom-auth-1.0.jar    # Your plugin JAR
    └── config/
        └── auth-config.xml    # Plugin configuration
```

The `extension.xml` descriptor:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<extension>
  <id>custom-auth</id>
  <name>Custom Authentication Extension</name>
  <version>1.0.0</version>
  <start-priority>1000</start-priority>
  <start-required>true</start-required>
</extension>
```

HiveMQ also offers official extensions for file-based authentication, Redis integration, and Kafka forwarding — all available for free from the HiveMQ extension marketplace.

### Best Use Cases

HiveMQ CE is ideal for organizations already running Java infrastructure that want a standards-compliant MQTT 5.0 broker with extensibility. The plugin architecture is mature and well-documented, making it easy to integrate with existing authentication systems (LDAP, databases, custom APIs). It is a good fit for enterprise IoT backends, industrial telemetry, and scenarios where you need a Java-native solution with commercial support available as an upgrade path.

## Comparison: Mosquitto vs EMQX vs HiveMQ CE

| Feature | Eclipse Mosquitto | EMQX | HiveMQ CE |
|---------|------------------|------|-----------|
| **Language** | C | Erlang/OTP | Java |
| **License** | EPL-2.0 / EDL-1.0 | Apache 2.0 | Apache 2.0 |
| **MQTT Version** | 3.1, 3.1.1, 5.0 | 3.1.1, 5.0 | 3.1.1, 5.0 |
| **WebSocket** | Yes | Yes | Yes |
| **Clustering** | No (bridging only) | Yes, native | Limited (CE), full (Enterprise) |
| **Max Connections** | ~10,000 (single node) | Millions (clustered) | ~100,000+ (depends on JVM) |
| **RAM Usage (idle)** | ~5 MB | ~80 MB | ~300 MB |
| **Dashboard** | No (CLI only) | Yes, full Web UI | Control Center (limited in CE) |
| **Rule Engine** | No | Yes, SQL-based | Via plugins |
| **Authentication** | Password file, plugins | Built-in, LDAP, HTTP, JWT | Plugin-based |
| **Data Forwarding** | Via plugins | Kafka, DB, HTTP, Redis, MongoDB | Kafka, plugins |
| **Home Assistant** | Default/first-class | Supported via integration | Supported via MQTT integration |
| **Docker Image Size** | ~15 MB | ~180 MB | ~350 MB |
| **Best For** | Home labs, single node | Enterprise, large scale | Java shops, enterprise IoT |

## Performance Benchmarks

Benchmarks from independent testing with a 4-core / 8 GB RAM server:

| Broker | Messages/sec (10K clients) | Messages/sec (100K clients) | P99 Latency |
|--------|---------------------------|----------------------------|-------------|
| Mosquitto 2.0 | ~85,000 | N/A (does not scale) | 2 ms |
| EMQX 5.8 | ~500,000 | ~1,200,000 | 5 ms |
| HiveMQ CE 4.16 | ~120,000 | ~350,000 | 8 ms |

For a typical home setup with 20-50 devices, all three brokers are overkill — any of them will handle the load with minimal resource usage. The differences matter when you scale past thousands of connections or need high availability.

## Choosing the Right Broker

**Choose Mosquitto if:** You are building a home automation system with Home Assistant, running on a Raspberry Pi, or want the lightest possible broker. It is the default for a reason — simple to configure, minimal resources, and rock-solid reliability.

**Choose EMQX if:** You need horizontal scaling, a built-in rule engine for data pipelines, or a dashboard for monitoring hundreds of devices. It is the most feature-rich open-source option and scales from a single node to a distributed cluster without changing your application code.

**Choose HiveMQ CE if:** You are already running a Java stack, need a plugin-based architecture for custom integrations, or want a clear upgrade path to enterprise support. The extension ecosystem is mature and well-documented.

## Production Hardening Checklist

Regardless of which broker you choose, apply these security measures before exposing your MQTT broker to any network beyond localhost:

```bash
# 1. Always require authentication — never allow anonymous access
# Mosquitto: allow_anonymous false
# EMQX: Set default authentication to deny
# HiveMQ CE: Enable authentication extension

# 2. Enable TLS for all listeners
# Generate self-signed certificates (or use Let's Encrypt)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days 365 -nodes -subj "/CN=mqtt.yourdomain.com"

# 3. Use ACL rules to restrict topic access
# Mosquitto: Create an ACL file with topic patterns per user
# EMQX: Use the dashboard or API to define authorization rules
# HiveMQ CE: Implement via the authorization extension

# 4. Isolate the broker in a Docker network
docker network create iot-network

# 5. Set up a reverse proxy with TLS termination for WebSocket access
# Use Caddy, Traefik, or Nginx to handle HTTPS for browser clients

# 6. Monitor broker health
# Mosquitto: Monitor log files [prometheus](https://prometheus.io/)tion counts
# EMQX: Use the built-in dashboard and Prometheus metrics endpoint
# HiveMQ CE: Use JMX metrics or the Control Center

# 7. Back up your configuration and persistent data
# Include: config files, password databases, retained message store
```

## Conclusion

Self-hosting an MQTT broker is one of the highest-return infrastructure decisions you can make for an IoT or home automation setup. Mosquitto remains the best choice for lightweight, single-node deployments — especially with Home Assistant. EMQX brings enterprise-grade clustering and a powerful rule engine to the open-source world. HiveMQ CE offers a mature Java-based platform with extensive plugin support.

All three are production-ready, support MQTT 5.0, and can be deployed with Docker in under five minutes. The right choice depends on your scale, existing infrastructure, and feature requirements — but any of them will give you the speed, privacy, and reliability that cloud-hosted MQTT services simply cannot match.

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
