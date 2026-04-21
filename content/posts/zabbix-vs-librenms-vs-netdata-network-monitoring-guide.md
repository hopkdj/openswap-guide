---
title: "Zabbix vs LibreNMS vs Netdata: Best Self-Hosted Network Monitoring 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy", "monitoring", "networking"]
draft: false
description: "Compare Zabbix, LibreNMS, and Netdata for self-hosted network monitoring. Complete Docker setup guides, SNMP configuration, feature comparison, and alerting strategies for 2026."
---

## Why Self-Host Your Network Monitoring?

Commercial network monitoring platforms charge per-device licensing fees, cap data retention, and ship your infrastructure telemetry to third-party clouds. Self-hosting your monitoring stack gives you full control over every metric, alert, and dashboard:

- **Unlimited device monitoring** — track hundreds of routers, switches, servers, and IoT endpoints without per-node licensing costs
- **Complete data sovereignty** — all SNMP data, flow records, and performance metrics remain on your own hardware
- **Deep internal visibility** — monitor private subnets, management VLANs, and internal services that cloud monitors cannot reach
- **Custom alerting pipelines** — integrate with your existing notification infrastructure without vendor lock-in
- **Long-term retention** — keep years of historical data for capacity planning and compliance audits without paying for premium storage tiers
- **No egress fees** — network flow data (NetFlow, sFlow, IPFIX) generates significant bandwidth — keeping it local saves money

For network administrators, homelab operators, and MSPs, a self-hosted monitoring solution is essential infrastructure. This guide compares the three leading open-source options and walks you through production-ready deployments.

## Feature Comparison: Zabbix vs LibreNMS vs Netdata

| Feature | Zabbix | LibreNMS | Netdata |
|---------|--------|----------|---------|
| **License** | GPL-2.0 | GPL-3.0 | GPL-3.0 |
| **Primary Focus** | Enterprise monitoring (any metric) | Network device monitoring (SNMP-first) | Real-time system performance |
| **Monitoring Protocol** | Agent, SNMP, IPMI, JMX, HTTP, custom | SNMP, WMI, SSH, API, BGP, OSPF | Agent (collectors), SNMP plugin |
| **Auto-Discovery** | ✅ Network discovery rules | ✅ Excellent auto-discovery | ❌ Manual node registration |
| **SNMP Support** | ✅ v1/v2c/v3 | ✅ v1/v2c/v3 (primary) | ✅ via go.d plugin |
| **Network Topology Maps** | ✅ Manual + auto-generated | ✅ Automatic LLDP/CDP maps | ❌ |
| **Flow Collection** | ❌ (external tools needed) | ✅ NetFlow, sFlow, IPFIX, NSEL | ❌ |
| **Real-Time Dashboards** | Configurable widgets | [grafana](https://grafana.com/) integration | ⚡ Built-in, sub-second |
| **Alerting Engine** | Powerful trigger expressions | Alert templates + macros | Alert config files |
| **Notification Channels** | 40+ (email, webhook, Slack, Telegram, etc.) | 20+ (email, Slack, Discord, Matrix, webhooks) | 100+ (via alarm_notify.sh and integrations) |
| **[docker](https://www.docker.com/) Support** | ✅ Official images | ✅ Official image | ✅ Official image |
| **Scalability** | Proxies for distributed monitoring | Horizontal via polling workers | Parent-child streaming |
| **BGP Monitoring** | Manual OID polling | ✅ Native BGP session tracking | ❌ |
| **Wireless Controller Support** | Limited | ✅ UniFi, Cisco WLC, Aruba | ❌ |
| **Resource Usage** | Moderate (MySQL + PHP backend) | Moderate (MySQL/MariaDB + RRDtool) | Low (optimized C daemon) |
| **Learning Curve** | Steep | Moderate | Low |
| **Best For** | Enterprise IT, mixed environments | Network ops teams, ISPs, MSPs | DevOps, real-time system visibility |

### Which One Should You Choose?

- **Zabbix** is the Swiss Army knife — monitor servers, networks, applications, cloud resources, and custom metrics from a single platform. It excels in heterogeneous environments where you need one tool for everything.
- **LibreNMS** is the network specialist — it auto-discovers devices, builds topology maps from LLDP/CDP, tracks BGP sessions, and collects network flows. If your primary focus is network infrastructure, this is your best choice.
- **Netdata** is the real-time performance engine — it provides second-by-second visibility into CPU, memory, disk I/O, network throughput, and application metrics with zero configuration. It's ideal for troubleshooting and live dashboards.

Many organizations run **Netdata + LibreNMS** (or **Netdata + Zabbix**) together — Netdata for real-time per-host visibility and LibreNMS/Zabbix for network-wide monitoring, alerting, and historical trending.

## Zabbix: Enterprise-Grade Monitoring

Zabbix has been the gold standard for open-source monitoring since 2001. Its template-based architecture lets you monitor virtually any device or service.

### Architecture

Zabbix uses a server-proxy-agent model:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Zabbix     │────▶│   Database    │     │  Web UI     │
│  Server     │     │ (MySQL/PG)   │◀────│  (PHP)      │
└──────┬──────┘     └──────────────┘     └─────────────┘
       │
       ├──▶ Zabbix Proxy (optional, remote sites)
       │      ├──▶ Agent (Linux/Windows)
       │      ├──▶ SNMP device (router, switch)
       │      └──▶ IPMI/BMC (hardware sensors)
       │
       ├──▶ Agent (local server)
       ├──▶ SNMP device (network equipment)
       └──▶ JMX application (Java services)
```

### Docker Compose Deployment

```bash
mkdir -p ~/zabbix/{mysql,data}
cd ~/zabbix
```

Create `docker-compose.yml`:

```yaml
services:
  zabbix-mysql:
    image: mysql:8.4
    container_name: zabbix-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: zabbix_root_pass
      MYSQL_DATABASE: zabbix
      MYSQL_USER: zabbix
      MYSQL_PASSWORD: zabbix_db_pass
      MYSQL_CHARSET: utf8mb4
    volumes:
      - ./mysql:/var/lib/mysql
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_bin
      --default-authentication-plugin=mysql_native_password
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  zabbix-server:
    image: zabbix/zabbix-server-mysql:alpine-7.2-latest
    container_name: zabbix-server
    restart: unless-stopped
    depends_on:
      zabbix-mysql:
        condition: service_healthy
    ports:
      - "10051:10051"
    environment:
      DB_SERVER_HOST: zabbix-mysql
      MYSQL_DATABASE: zabbix
      MYSQL_USER: zabbix
      MYSQL_PASSWORD: zabbix_db_pass
      MYSQL_ROOT_PASSWORD: zabbix_root_pass
    volumes:
      - ./data:/var/lib/zabbix
      - /etc/localtime:/etc/localtime:ro

  zabbix-web:
    image: zabbix/zabbix-web-nginx-mysql:alpine-7.2-latest
    container_name: zabbix-web
    restart: unless-stopped
    depends_on:
      - zabbix-mysql
      - zabbix-server
    ports:
      - "8080:8080"
    environment:
      DB_SERVER_HOST: zabbix-mysql
      MYSQL_DATABASE: zabbix
      MYSQL_USER: zabbix
      MYSQL_PASSWORD: zabbix_db_pass
      MYSQL_ROOT_PASSWORD: zabbix_root_pass
      ZBX_SERVER_HOST: zabbix-server
      PHP_TZ: UTC
    volumes:
      - /etc/localtime:/etc/localtime:ro

  zabbix-agent:
    image: zabbix/zabbix-agent2:alpine-7.2-latest
    container_name: zabbix-agent
    restart: unless-stopped
    privileged: true
    pid: host
    network_mode: host
    environment:
      ZBX_SERVER_HOST: "127.0.0.1"
      ZBX_HOSTNAME: "docker-host"
```

Start the stack:

```bash
docker compose up -d
```

Access the web interface at `http://your-server:8080`. Default credentials are `Admin` / `zabbix`.

### Adding SNMP Network Devices

1. Go to **Configuration → Hosts → Create host**
2. Set host name, add to a group (e.g., "Network Devices")
3. Add an **SNMP interface** with the device IP and port 161
4. Link the appropriate template:
   - `Cisco IOS SNMP` — for Cisco routers and switches
   - `Generic SNMP` — for generic SNMP-capable devices
   - `MikroTik SNMP` — for RouterOS devices
   - `Ubiquiti AirMAX SNMP` — for UniFi/EdgeMAX devices

For bulk SNMP v3 configuration, create a **host macro** at the template level:

```
{$SNMP_COMMUNITY} = public
{$SNMP_USERNAME} = monitor_user
{$SNMP_SECURITY_NAME} = monitor_user
{$SNMP_AUTH_PROTOCOL} = SHA
{$SNMP_AUTH_PASSPHRASE} = your_auth_password
{$SNMP_PRIV_PROTOCOL} = AES
{$SNMP_PRIV_PASSPHRASE} = your_priv_password
```

### Configuring Alert Triggers

Zabbix uses expression-based triggers. Here are practical examples:

```
# Router CPU over 80% for 5 minutes
{Template Net Cisco IOS SNMPv2:system.cpu.util[5min].avg(5m)}>80

# Interface utilization over 90%
{Template Net Cisco IOS SNMPv2:net.if.in[ifHCInOctets["{#IFNAME}"],bps].avg(3m)}>90000000

# Device unreachable (ICMP ping failure)
{Template Net ICMP Ping:icmpping.count(#3,0)}>2

# BGP session down
{Template Net Cisco IOS SNMPv2:ciscoBgPeerState["{#BGPPEER}"].last()}<>6
```

Set up notification actions under **Configuration → Actions** to route alerts to email, Slack, Telegram, or webhook endpoints.

## LibreNMS: Network-First Monitoring

LibreNMS was built specifically for network device monitoring. Its auto-discovery, automatic topology mapping, and built-in flow collection make it the go-to choice for network operations teams.

### Docker Compose Deployment

```bash
mkdir -p ~/librenms/{config,rrd,logs,db}
cd ~/librenms
```

Create `docker-compose.yml`:

```yaml
services:
  librenms:
    image: librenms/librenms:latest
    container_name: librenms
    restart: unless-stopped
    ports:
      - "8443:443"
      - "8080:80"
      - "514:514/udp"
      - "162:162/udp"
    environment:
      - TZ=UTC
      - DB_HOST=librenms-db
      - DB_NAME=librenms
      - DB_USER=librenms
      - DB_PASSWORD=librenms_secret
      - DB_TIMEOUT=30
      - REDIS_HOST=librenms-redis
      - LIBRENMS_SNMP_COMMUNITY=public
      - PUID=1000
      - PGID=1000
      - POLLERS=16
      - RRDCACHED_ADDRESS=librenms-rrdcached:42217
    volumes:
      - ./config:/data/config
      - ./rrd:/data/rrd
      - ./logs:/data/logs
      - ./librenms:/opt/librenms
    depends_on:
      librenms-db:
        condition: service_healthy
      librenms-redis:
        condition: service_started
    networks:
      monitoring:
        ipv4_address: 172.20.0.10

  librenms-db:
    image: mariadb:10.11
    container_name: librenms-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=librenms
      - MYSQL_USER=librenms
      - MYSQL_PASSWORD=librenms_secret
      - MYSQL_CHARSET=utf8mb4
    volumes:
      - ./db:/var/lib/mysql
    command: >
      --innodb-file-per-table=1
      --lower-case-table-names=0
      --max-connections=512
      --wait=60
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      monitoring:
        ipv4_address: 172.20.0.11

  librenms-redis:
    image: redis:7-alpine
    container_name: librenms-redis
    restart: unless-stopped
    networks:
      monitoring:
        ipv4_address: 172.20.0.12

  librenms-rrdcached:
    image: crazymax/rrdcached:latest
    container_name: librenms-rrdcached
    restart: unless-stopped
    environment:
      - LOG_LEVEL=LOG_INFO
      - WRITE_JOURNAL=true
      - WRITE_TIMEOUT=1800
      - WRITE_JDELAY=1800
      - FLUSH_DEAD_DATA_INTERVAL=3600
    volumes:
      - ./rrd:/data/db
      - ./rrd/journal:/data/journal
    networks:
      monitoring:
        ipv4_address: 172.20.0.13

  librenms-smtp:
    image: mwader/postfix-relay
    container_name: librenms-smtp
    restart: unless-stopped
    environment:
      - POSTFIX_myhostname=librenms.local
    networks:
      monitoring:
        ipv4_address: 172.20.0.14

networks:
  monitoring:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

```bash
docker compose up -d
```

Access at `http://your-server:8080`. Default credentials are `librenms` / `password` — **change this immediately**.

### SNMP Configuration for LibreNMS

Configure SNMP on your network devices. Here are examples for common platforms:

**Cisco IOS/IOS-XE:**
```
snmp-server community public RO
snmp-server host <librenms-ip> version 2c public
snmp-server enable traps
snmp-server ifindex persist
```

**Cisco IOS-XE with SNMP v3:**
```
snmp-server view READONLY iso included
snmp-server group MONITOR v3 auth read READONLY
snmp-server user monitor_user MONITOR v3 auth sha monitor_auth123 priv aes 128 monitor_priv123
snmp-server host <librenms-ip> version 3 auth monitor_user
```

**MikroTik RouterOS:**
```
/snmp community
add address=172.20.0.10/32 name=librenms security=authorized
/snmp
set enabled=yes contact="admin@example.com" location="Data Center Rack A1"
```

**Linux (net-snmp):**
```bash
sudo apt install snmpd
```

Edit `/etc/snmp/snmpd.conf`:
```
rocommunity public 172.20.0.10
sysLocation "Server Room"
sysContact "admin@example.com"
extend .1.3.6.1.4.1.2021.51 mem_used /bin/cat /proc/meminfo
```

```bash
sudo systemctl restart snmpd
```

### Auto-Discovery Setup

LibreNMS can automatically discover devices on your network:

1. Go to **Global Settings → Discovery**
2. Add discovery networks (e.g., `10.0.0.0/16`, `192.168.1.0/24`)
3. Configure SNMP communities for auto-discovery
4. Set up **OS detection** and **port association** rules

Add a cron entry for periodic discovery:

```bash
docker exec librenms /opt/librenms/discovery.php -h new
docker exec librenms /opt/librenms/poller.php -h new
```

### Network Flow Collection

Enable NetFlow/sFlow/IPFIX collection for traffic analysis:

**On Cisco switch:**
```
flow record LIBRENMS
  match ipv4 source address
  match ipv4 destination address
  match transport source-port
  match transport destination-port
  collect counter bytes
  collect counter packets
!
flow exporter LIBRENMS_EXPORT
  destination <librenms-ip>
  transport udp 9995
!
interface GigabitEthernet0/1
  ip flow monitor LIBRENMS_INPUT input
  ip flow monitor LIBRENMS_OUTPUT output
```

Then in LibreNMS, go to **Ports → Flow Settings** and configure the listening port (9995 by default). The Docker compose already exposes the UDP port for flow ingestion.

### Alert Configuration

LibreNMS uses alert templates with macro-based rules:

1. Go to **Alerts → Alert Rules → Add Rule**
2. Configure conditions:

```
# Device down (no response to ICMP)
devices.status = 0

# Port utilization over 85%
ports.ifInErrors_delta > 0 || ports.ifOutErrors_delta > 0

# BGP session state changed
bgpPeers.bgpPeerState != 6

# Disk usage over 90%
storage.storage_perc > 90

# Wireless client count dropped below threshold
devices.wireless_clients < 5
```

3. Set up alert transports under **Alerts → Alert Transports**:
   - **Email** — via the SMTP relay container
   - **Slack** — incoming webhook URL
   - **Discord** — webhook URL
   - **Matrix** — via HTTP transport
   - **PagerDuty** — for critical alerts

## Netdata: Real-Time System Performance

Netdata provides second-by-second metrics with a beautiful real-time dashboard. It's designed for immediate visibility — not historical trending.

### Docker Compose Deployment

```bash
mkdir -p ~/netdata/{config,data,cache}
cd ~/netdata
```

Create `docker-compose.yml`:

```yaml
services:
  netdata:
    image: netdata/netdata:stable
    container_name: netdata
    restart: unless-stopped
    hostname: monitoring-server
    cap_add:
      - SYS_PTRACE
      - SYS_ADMIN
    security_opt:
      - apparmor:unconfined
    ports:
      - "19999:19999"
    volumes:
      - ./config:/etc/netdata
      - ./data:/var/lib/netdata
      - ./cache:/var/cache/netdata
      - /etc/passwd:/host/etc/passwd:ro
      - /etc/group:/host/etc/group:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /etc/os-release:/host/etc/os-release:ro
      - /var/log:/host/var/log:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - NETDATA_CLAIM_TOKEN=your-claim-token
      - NETDATA_CLAIM_URL=https://app.netdata.cloud
      - DOCKER_HOST=unix:///var/run/docker.sock
      - TZ=UTC
```

```bash
docker compose up -d
```

Access the dashboard at `http://your-server:19999`. Netdata works out of the box with **zero configuration** — it auto-detects running services, containers, and hardware.

### Monitoring Network Devices via SNMP

Netdata can poll SNMP devices using its `go.d.plugin`. Enable SNMP collection:

```bash
docker exec netdata cd /etc/netdata && \
  cp go.d/snmp.conf edit-config go.d/snmp.conf
```

Create `/etc/netdata/go.d/snmp.conf`:

```yaml
jobs:
  - name: core_switch
    update_every: 10
    priority: 1
    timeout: 2
    retries: 3
    host: 10.0.1.1
    community: public
    options:
      - check_response: true
    charts:
      - id: switch_port_traffic
        title: Core Switch Port Traffic
        units: kb/s
        family: traffic
        context: snmp.port_traffic
        chart_type: area
        priority: 1
        multiply: 8
        divide: 1000
    response_mappings:
      - match: "IF-MIB::ifInOctets\\.(\\d+)"
        variable: "ifInOctets"
        label: "port-{1}-in"
        dimension: "in"
        algorithm: "incremental"
```

Restart to apply:

```bash
docker exec netdata killall -HUP netdata
```

### Parent-Child Streaming for Multiple Nodes

For monitoring multiple servers, use Netdata's parent-child architecture:

**Parent node (central collector):**
```yaml
services:
  netdata-parent:
    image: netdata/netdata:stable
    container_name: netdata-parent
    restart: unless-stopped
    hostname: netdata-parent
    ports:
      - "19999:19999"
      - "19998:19998"
    volumes:
      - ./parent-config:/etc/netdata
      - ./parent-data:/var/lib/netdata
      - ./parent-cache:/var/cache/netdata
```

**Child node (on each monitored server):**

Create `/etc/netdata/stream.conf`:
```ini
[stream]
    enabled = yes
    destination = parent-server-ip:19998
    api key = YOUR_API_KEY
```

On the parent, create `/etc/netdata/stream.conf`:
```ini
[YOUR_API_KEY]
    enabled = yes
    default history = 3600
    default memory mode = dbengine
    health enabled by default = auto
```

### Configuring Alerts

Netdata alerts are defined in YAML under `/etc/netdata/health.d/`. Create a custom alert file:

```bash
docker exec netdata edit-config health.d/cpu.conf
```

Example custom alert for network interface errors:

```yaml
alert: network_interface_errors
   on: net.errors
lookup: max -1s
  every: 10s
   warn: $this > (($status >= $WARNING)  ? ( 5) : (10))
   crit: $this > (($status == $CRITICAL) ? (10) : (20))
   info: network interface errors per second
   to: sysadmin
```

Notification configuration is in `health_alarm_notify.conf`:

```bash
docker exec netdata edit-config health_alarm_notify.conf
```

Configure multiple notification channels:

```ini
# Email
SEND_EMAIL="YES"
DEFAULT_RECIPIENT_EMAIL="admin@example.com"

# Slack
SEND_SLACK="YES"
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/yyy/zzz"
DEFAULT_RECIPIENT_SLACK="#network-alerts"

# Discord
SEND_DISCORD="YES"
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxx/yyy"
DEFAULT_RECIPIENT_DISCORD="network-monitoring"

# Telegram
SEND_TELEGRAM="YES"
TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
DEFAULT_RECIPIENT_TELEGRAM="-1001234567890"
```

## Advanced: Combining Netdata + LibreNMS

For comprehensive coverage, run both tools together. Netdata handles real-time per-node visibility while LibreNMS handles network-wide discovery, topology, and flow collection.

### Unified Docker Compose Stack

```yaml
services:
  # LibreNMS for network device monitoring
  librenms:
    image: librenms/librenms:latest
    container_name: librenms
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - DB_HOST=librenms-db
      - DB_NAME=librenms
      - DB_USER=librenms
      - DB_PASSWORD=librenms_secret
    volumes:
      - librenms-config:/data/config
      - librenms-rrd:/data/rrd
      - librenms-logs:/data/logs

  librenms-db:
    image: mariadb:10.11
    restart: unless-stopped
    environment:
      - MYSQL_DATABASE=librenms
      - MYSQL_USER=librenms
      - MYSQL_PASSWORD=librenms_secret
      - MYSQL_ROOT_PASSWORD=root_secret
    volumes:
      - librenms-db:/var/lib/mysql

  # Netdata for real-time system metrics
  netdata:
    image: netdata/netdata:stable
    container_name: netdata
    restart: unless-stopped
    hostname: monitoring-host
    cap_add:
      - SYS_PTRACE
    security_opt:
      - apparmor:unconfined
    ports:
      - "19999:19999"
    volumes:
      - netdata-config:/etc/netdata
      - netdata-data:/var/lib/netdata
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro

  # Grafana for unified dashboards (optional)
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=grafana_admin
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-piechart-panel
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  librenms-config:
  librenms-rrd:
  librenms-logs:
  librenms-db:
  netdata-config:
  netdata-data:
  grafana-data:
```

### Grafana as Unified Dashboard

Both LibreNMS and Netdata can feed into Grafana:

1. **LibreNMS Grafana Plugin** — built into LibreNMS. Enable it under **Global Settings → External → Grafana Integration**. Install the Grafana plugin:

```bash
docker exec librenms apt-get update && \
  docker exec librenms apt-get install -y php-json php-curl
```

2. **Netdata as Grafana Data So[prometheus](https://prometheus.io/)etdata exposes a Prometheus-compatible endpoint at `http://netdata:19999/api/v1/allmetrics?format=prometheus`. Add this as a Prometheus data source in Grafana.

3. **LibreNMS MySQL as Data Source** — point Grafana at the LibreNMS MariaDB instance for custom SQL queries on historical port utilization, device availability, and BGP session data.

## Security Best Practices

Regardless of which tool you choose, follow these security practices:

### Reverse Proxy with TLS

Never expose monitoring dashboards directly to the internet. Use a reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name monitoring.example.com;

    ssl_certificate /etc/letsencrypt/live/monitoring.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoring.example.com/privkey.pem;

    # Restrict to internal networks
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;

    # Zabbix
    location /zabbix {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # LibreNMS
    location /librenms {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Netdata
    location /netdata {
        proxy_pass http://127.0.0.1:19999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### SNMP Hardening

Always prefer SNMP v3 over v2c:

```bash
# Create SNMP v3 user with auth and privacy
net-snmp-create-v3-user -ro -A auth_password -X priv_password -a SHA -X AES monitor_user
```

SNMP v2c community strings are sent in plaintext — only use them on isolated management VLANs.

### Database Backups

Monitoring data is valuable for trend analysis. Back up your databases:

```bash
#!/bin/bash
# backup-monitoring-db.sh
BACKUP_DIR="/backup/monitoring"
DATE=$(date +%Y%m%d_%H%M%S)

# LibreNMS / Zabbix database backup
docker exec librenms-db mysqldump -u librenms -plibrenms_secret librenms | \
  gzip > "${BACKUP_DIR}/librenms_${DATE}.sql.gz"

# Keep 30 days of backups
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```
0 2 * * * /root/backup-monitoring-db.sh
```

## Performance Tuning

### Zabbix
- Use **database partitioning** for large installations (history table partitioning)
- Deploy **Zabbix proxies** for remote sites to reduce server load
- Increase `StartPollers` and `StartTrappers` in `zabbix_server.conf` for high-volume environments
- Use `CacheSize=128M` and `HistoryCacheSize=64M` for environments with 500+ hosts

### LibreNMS
- Increase poller count: set `POLLERS=16` or higher in the Docker environment
- Use **RRDcached** (included in the compose file above) for efficient RRD writes
- Run `daily.sh` for automatic updates and database optimization:
  ```bash
  docker exec librenms /opt/librenms/daily.sh
  ```
- Enable `memcached` or `redis` for distributed polling sessions

### Netdata
- Set `memory mode = dbengine` for long-term storage with compression
- Configure `page cache size` based on available RAM (1-4 GB recommended)
- Use `dbengine multihost disk space = 256` for 256 MB of compressed storage per host
- Enable `streaming compression = lz4` for parent-child data transfer

## Conclusion

All three tools are mature, production-ready, and entirely free. Your choice depends on your primary use case:

- **Zabbix** — choose when you need a single platform for servers, networks, applications, and custom metrics. Its template ecosystem covers virtually everything.
- **LibreNMS** — choose when network infrastructure is your primary concern. Auto-discovery, topology maps, BGP monitoring, and flow collection are unmatched.
- **Netdata** — choose when you need immediate, second-by-second visibility into system performance with zero configuration overhead.

For maximum coverage, pair **Netdata** (real-time per-node metrics) with **LibreNMS** (network-wide discovery and trending) — many organizations find this combination covers both the forest and the trees.

All three integrate cleanly with reverse proxies, support containerized deployment, and offer robust alerting pipelines. Pick the tool that matches your team's expertise and your infrastructure's needs — you can't go wrong with any of them.

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
