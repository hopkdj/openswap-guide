---
title: "TextBee vs Jasmin vs Kalkun: Best Self-Hosted SMS Gateway 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "sms", "messaging", "communication"]
draft: false
description: "Compare TextBee, Jasmin, and Kalkun — the top open-source self-hosted SMS gateway solutions. Deployment guides, feature comparison, and Docker configs for building your own messaging infrastructure."
---

Sending and receiving SMS messages at scale doesn't require expensive cloud services. Whether you need two-factor authentication, marketing campaigns, transactional alerts, or a messaging API for your applications, self-hosted SMS gateways give you full control over costs, data, and routing.

In this guide, we compare three mature open-source SMS gateway platforms: **TextBee**, **Jasmin**, and **Kalkun**. Each takes a fundamentally different approach — from Android phone-based routing to enterprise SMPP infrastructure — so understanding their trade-offs is critical before you commit to one.

## Why Self-Host an SMS Gateway?

Commercial SMS APIs like Twilio, MessageBird, and Vonage are convenient, but they come with significant drawbacks:

- **Cost per message** — Volume pricing still adds up quickly for high-throughput applications
- **Vendor lock-in** — Your messaging pipeline depends on a single provider's API and uptime
- **Data privacy** — Message content, recipient lists, and delivery metadata flow through third-party servers
- **Routing control** — You cannot optimize for regional pricing or prefer specific carrier routes

A self-hosted SMS gateway solves these problems. You connect to SMPP providers, USB modems, or Android phones directly, route messages through your own infrastructure, and maintain complete visibility into every step of the pipeline. Combined with [self-hosted live chat solutions](../self-hosted-live-chat-chatwoot-papercups-tiledesk-guide/) and [push notification servers](../gotify-vs-ntfy-self-hosted-push-notifications/), you can build an entire self-hosted messaging stack.

## TextBee: Turn Any Android Phone into an SMS Gateway

**TextBee** ([vernu/textbee](https://github.com/vernu/textbee)) is the most popular open-source SMS gateway by GitHub stars, with over 2,500 stars and active development. Its unique approach: install a companion app on an Android phone, and that phone becomes your SMS modem.

### Architecture

TextBee uses a modern TypeScript stack:
- **API Server** — NestJS REST API for sending/receiving messages
- **Web Dashboard** — Next.js frontend for management and analytics
- **Android Companion** — Runs on any Android device, handles actual SMS send/receive
- **MongoDB** — Message storage, user accounts, and device management
- **[redis](https://redis.io/)** — Message queue for high-throughput scenarios

### Real-Time Stats (April 2026)

| Metric | Value |
|--------|-------|
| GitHub Stars | 2,529 |
| Primary Language | TypeScript |
| Last Updated | April 5, 2026 |
| Architecture | NestJS + Next.js + MongoDB + Redis |
| License | MIT |

### [docker](https://www.docker.com/) Compose Deployment

TextBee provides an official `docker-compose.yaml` that spins up the full stack:

```yaml
services:
  textbee-db:
    container_name: textbee-db
    image: mongo:latest
    restart: always
    environment:
      - MONGO_INITDB_ROOT_USERNAME=adminUser
      - MONGO_INITDB_ROOT_PASSWORD=adminPassword
      - MONGO_INITDB_DATABASE=textbee
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27018:27017"
    networks:
      - textbee-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  textbee-api:
    container_name: textbee-api
    build:
      context: ./api
      dockerfile: Dockerfile
    restart: always
    ports:
      - "3001:3001"
    environment:
      - PORT=3001
      - REDIS_URL=redis://textbee-redis:6379
    depends_on:
      textbee-db:
        condition: service_healthy
    networks:
      - textbee-network

  textbee-web:
    container_name: textbee-web
    build:
      context: ./web
      dockerfile: Dockerfile
    restart: always
    ports:
      - "3000:3000"
    environment:
      - PORT=3000
      - NEXT_PUBLIC_API_BASE_URL=http://localhost:3001/api/v1
    depends_on:
      - textbee-api
    networks:
      - textbee-network

  textbee-redis:
    container_name: textbee-redis
    image: redis:alpine
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - textbee-network
    command: redis-server --appendonly yes

networks:
  textbee-network:
    driver: bridge

volumes:
  mongodb_data:
  redis_data:
```

Quick start:

```bash
git clone https://github.com/vernu/textbee.git
cd textbee
docker compose up -d
```

### Sending SMS via API

```bash
curl -X POST http://localhost:3001/api/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "receiver": "+1234567890",
    "message": "Hello from self-hosted SMS!",
    "simSlot": 1
  }'
```

### Best Use Cases

- Low-cost SMS for startups and small businesses
- Developers who already have spare Android phones
- Applications needing moderate SMS throughput (hundreds per day)
- Teams wanting a modern web dashboard out of the box

## Jasmin: Enterprise-Grade SMPP SMS Gateway

**Jasmin** ([jookies/jasmin](https://github.com/jookies/jasmin)) is the most mature and feature-rich open-source SMS gateway. Written in Python, it has been actively maintained for years and handles enterprise-scale SMS routing with advanced features like load balancing, failover, and billing.

### Architecture

Jasmin is built around the SMPP (Short Message Peer-to-Peer) protocol:
- **SMPP Server** — Accepts connections from applications and upstream providers
- **SMPP Client** — Connects to upstream SMS aggregators and carriers
- **Router** — Intelligent message routing with MTR (message throughput rating), failover, and load balancing
- **HTTP API** — REST interface for sending SMS from web applications
- **Redis** — Session [rabbitmq](https://www.rabbitmq.com/)nt and queuing
- **RabbitMQ** — High-performance message broker for routing

### Real-Time Stats (April 2026)

| Metric | Value |
|--------|-------|
| GitHub Stars | 1,171 |
| Primary Language | Python |
| Last Updated | April 17, 2026 |
| Architecture | Python + SMPP + Redis + RabbitMQ |
| License | Commercial (free trial available) |

### Docker Compose Deployment

Jasmin's `docker-compose.yml` (on the `master` branch) sets up the core services:

```yaml
services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    healthcheck:
      test: redis-cli ping | grep PONG
    deploy:
      resources:
        limits:
          cpus: '0.2'
          memory: 128M
    security_opt:
      - no-new-privileges:true

  rabbit-mq:
    image: rabbitmq:3.10-management-alpine
    restart: unless-stopped
    healthcheck:
      test: rabbitmq-diagnostics -q ping
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 525M
    security_opt:
      - no-new-privileges:true

  jasmin:
    build:
      context: ./
      dockerfile: ./docker/Dockerfile.dev
    restart: unless-stopped
    volumes:
      - ./jasmin:/usr/jasmin/jasmin
    ports:
      - 2775:2775   # SMPP port
      - 8990:8990   # HTTP API
      - 1401:1401   # CLI telnet
    depends_on:
      redis:
        condition: service_healthy
      rabbit-mq:
        condition: service_healthy
    environment:
      REDIS_CLIENT_HOST: redis
      AMQP_BROKER_HOST: rabbit-mq

networks:
  default:
    driver: bridge
```

Quick start:

```bash
git clone https://github.com/jookies/jasmin.git
cd jasmin
git checkout master
docker compose up -d
```

### Configuring an SMPP Connector

Connect to Jasmin's CLI (port 1401) and set up a connector to your upstream SMPP provider:

```bash
telnet localhost 1401
# Default credentials: jcliadmin / jclipwd

jcliadmin> connector -a
> cid: upstream-provider
> protocol: smppclient
> host: smpp.your-provider.com
> port: 2775
> username: your_smpp_user
> password: your_smpp_pass
> ok

jcliadmin> mt-route -a
> cid: upstream-provider
> order: 0
> type: staticmt
> filters:
> ok

jcliadmin> persist
```

### Sending SMS via HTTP API

```bash
curl "http://localhost:8990/send?username=test&password=test&to=1234567890&content=Hello+from+Jasmin"
```

### Best Use Cases

- High-volume SMS routing (thousands to millions per day)
- Telecom operators and MVNOs
- Applications requiring SMPP protocol support
- Scenarios needing intelligent routing, load balancing, and failover
- Billing and accounting for SMS traffic

## Kalkun: Web-Based SMS Manager with Gammu Backend

**Kalkun** ([kalkun-sms/Kalkun](https://github.com/kalkun-sms/Kalkun)) is a PHP-based web application that manages SMS through Gammu, an open-source library for communicating with GSM modems and phones. It provides a clean web interface for sending, receiving, and organizing SMS messages.

### Architecture

Kalkun uses a traditional LAMP/LEMP stack:
- **PHP Web Application** — CodeIgniter-based frontend for SMS management
- **Gammu** — SMS daemon that communicates with GSM modems via serial/USB
- **MySQL/MariaDB** — Message storage and user management
- **Gammu SMSD** — Background daemon for continuous SMS monitoring

### Real-Time Stats (April 2026)

| Metric | Value |
|--------|-------|
| GitHub Stars | 229 |
| Primary Language | PHP |
| Last Updated | February 18, 2026 |
| Architecture | PHP (CodeIgniter) + Gammu + MySQL |
| License | GPLv3 |

### Manual Installation (No Docker Compose)

Kalkun does not provide an official Docker compose setup. Here is a standard installation on Ubuntu:

```bash
# Install dependencies
sudo apt update
sudo apt install -y apache2 mysql-server php php-mysql php-curl gammu gammu-smsd

# Configure Gammu (edit /etc/gammu-smsdrc)
cat > /etc/gammu-smsdrc << 'GAMMU_EOF'
[gammu]
port = /dev/ttyUSB0
connection = at115200

[smsd]
service = files
logfile = /var/log/gammu-smsd.log
PIN = 1234

# MySQL backend
driver = native_mysql
logfile = /var/log/gammu-smsd.log
user = kalkun
password = kalkun_pass
database = kalkun
host = localhost

# Paths for incoming/outgoing messages
inboxpath = /var/spool/gammu/inbox/
outgoingpath = /var/spool/gammu/outbox/
GAMMU_EOF

# Start Gammu SMS daemon
sudo systemctl enable gammu-smsd
sudo systemctl start gammu-smsd

# Download and set up Kalkun
cd /var/www/html
sudo git clone https://github.com/kalkun-sms/Kalkun.git kalkun
cd kalkun
sudo cp application/config/database.php.sample application/config/database.php

# Configure database credentials
sudo nano application/config/database.php

# Set Apache document root to Kalkun directory
sudo nano /etc/apache2/sites-available/kalkun.conf
```

Apache virtual host configuration:

```apache
<VirtualHost *:80>
    ServerName sms.yourdomain.com
    DocumentRoot /var/www/html/kalkun

    <Directory /var/www/html/kalkun>
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/kalkun-error.log
    CustomLog ${APACHE_LOG_DIR}/kalkun-access.log combined
</VirtualHost>
```

### Best Use Cases

- Small-scale SMS management with a web interface
- Organizations already using USB GSM modems or dongles
- Users who prefer PHP-based applications on LAMP stacks
- Environments where a simple inbox/outbox workflow is sufficient

## Feature Comparison

| Feature | TextBee | Jasmin | Kalkun |
|---------|---------|--------|--------|
| **GitHub Stars** | 2,529 | 1,171 | 229 |
| **Language** | TypeScript | Python | PHP |
| **Protocol** | Android API | SMPP | Gammu (AT commands) |
| **Docker Support** | Official compose | Official compose | Manual install |
| **Web Dashboard** | Next.js (built-in) | No (CLI/HTTP API) | CodeIgniter (built-in) |
| **Message Queue** | Redis | RabbitMQ | File-based / MySQL |
| **Load Balancing** | No | Yes (MTR routing) | No |
| **Failover Routing** | No | Yes | No |
| **Billing** | No | Yes | No |
| **Multi-SIM** | Yes (simSlot) | Yes (multiple connectors) | Yes (multiple modems) |
| **HTTP API** | REST (NestJS) | HTTP GET/POST | Web interface only |
| **Database** | MongoDB | Redis (runtime) | MySQL/MariaDB |
| **License** | MIT | Commercial | GPLv3 |
| **Best For** | Startups, developers | Telecom, enterprise | Small-scale, hobbyist |

## Which Should You Choose?

### Choose TextBee if:
- You want the easiest setup with a modern web dashboard
- You have Android phones available to use as modems
- Your SMS volume is moderate (hundreds per day)
- You prefer a fully Docker-deployable stack

### Choose Jasmin if:
- You need enterprise-scale SMS routing and SMPP connectivity
- Your volume is high (thousands+ per day)
- You require intelligent routing, load balancing, and failover
- You need billing and accounting features

### Choose Kalkun if:
- You already have GSM modems/dongles connected via USB
- You prefer a PHP-based web application
- Your use case is simple inbox/outbox management
- You are comfortable with manual LAMP stack configuration

## FAQ

### What is the difference between SMPP and GSM modem-based SMS gateways?

SMPP (Short Message Peer-to-Peer) is a telecom industry protocol used for high-volume SMS routing between applications and carriers. GSM modem-based gateways use AT commands sent over serial/USB connections to physical SIM cards. SMPP gateways like Jasmin handle thousands of messages per second and support carrier-grade features, while GSM modem solutions like Kalkun are simpler but limited by the physical modem's throughput (typically 10-30 messages per minute).

### Can I use TextBee without an Android phone?

No. TextBee's core architecture requires the Android companion app to send and receive actual SMS messages. The server components (API, web dashboard, database) manage the routing and storage, but the physical SMS transmission happens through the Android device. If you need server-side SMS without a phone, consider Jasmin with an SMPP provider.

### Does Jasmin have a free tier?

Jasmin is commercial software with a free trial available for evaluation. The trial provides full functionality for testing but is time-limited. For production use, you need to purchase a license. Check the [jookies/jasmin](https://github.com/jookies/jasmin) repository for current pricing details.

### Can Kalkun handle incoming SMS?

Yes. Kalkun monitors connected GSM modems through Gammu SMSD, which polls for new messages and stores them in the MySQL database. The web interface then displays them in an inbox view, similar to a traditional SMS messaging app. You can set up rules for automatic replies or forwarding.

### How do I scale SMS throughput beyond a single device?

With TextBee, you can register multiple Android devices and distribute messages across them. With Jasmin, you configure multiple SMPP connectors and use the routing engine to load-balance across providers. With Kalkun, you can connect multiple GSM modems to the same Gammu instance. For the highest throughput, Jasmin with multiple SMPP upstream providers is the most scalable option.

### Is it legal to self-host an SMS gateway?

Yes, self-hosting an SMS gateway is legal. However, you must comply with your country's telecommunications regulations, including anti-spam laws (like the TCPA in the US or GDPR for EU recipients), opt-in/opt-out requirements, and any licensing requirements for operating as an SMS provider. Always consult local regulations before sending commercial or bulk SMS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TextBee vs Jasmin vs Kalkun: Best Self-Hosted SMS Gateway 2026",
  "description": "Compare TextBee, Jasmin, and Kalkun — the top open-source self-hosted SMS gateway solutions. Deployment guides, feature comparison, and Docker configs.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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

For related reading, see our guide to [self-hosted live chat solutions](../self-hosted-live-chat-chatwoot-papercups-tiledesk-guide/) and [push notification servers](../gotify-vs-ntfy-self-hosted-push-notifications/). If you are building a complete messaging stack, also check our [VoIP PBX comparison](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/).
