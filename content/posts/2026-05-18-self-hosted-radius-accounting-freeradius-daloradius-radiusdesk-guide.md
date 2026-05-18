---
title: "Self-Hosted RADIUS Accounting: FreeRADIUS radacct vs Daloradius vs RadiusDesk"
date: "2026-05-18"
tags: ["radius", "accounting", "network-management", "self-hosted", "aaa"]
draft: false
---

RADIUS accounting provides detailed session tracking for network access — recording when users connect, how long they stay, how much data they transfer, and when they disconnect. While RADIUS authentication verifies who can access the network, accounting tracks what they do once connected. This guide compares three open-source approaches to RADIUS accounting: **FreeRADIUS radacct**, **Daloradius**, and **RadiusDesk**.

## What Is RADIUS Accounting?

RADIUS (Remote Authentication Dial-In User Service) accounting is a sub-protocol of RADIUS that records session data. When a user authenticates to a network access server (NAS), the NAS sends Accounting-Start packets to the RADIUS server. During the session, periodic Accounting-Interim-Update packets report usage metrics. When the user disconnects, an Accounting-Stop packet finalizes the record.

Accounting records include:
- **Session duration** — connect and disconnect timestamps
- **Data usage** — bytes sent and received (input/output octets)
- **Connection details** — NAS IP, calling/called station IDs, framed IP
- **User identity** — username, MAC address, VLAN assignment
- **Termination cause** — why the session ended (user request, timeout, admin reset)

## Comparison: FreeRADIUS radacct vs Daloradius vs RadiusDesk

| Feature | FreeRADIUS radacct | Daloradius | RadiusDesk |
|---------|-------------------|------------|------------|
| **Type** | Built-in module | Web GUI + reporting | Full management platform |
| **Backend** | SQL (MySQL/PostgreSQL) | MySQL | MySQL |
| **Web Interface** | None (CLI only) | Yes (PHP) | Yes (CakePHP) |
| **Real-time Monitoring** | Via radclient | Yes | Yes |
| **Reporting** | SQL queries required | Built-in charts | Built-in dashboards |
| **Billing Integration** | Manual | Partial | Yes (payment gateway) |
| **User Self-Service** | No | Limited | Yes (user portal) |
| **Hotspot/Captive Portal** | Manual setup | Yes | Yes |
| **Multi-tenant** | Via SQL views | Yes | Yes |
| **REST API** | No | Limited | Yes |
| **Docker Support** | Official image | Community images | Manual setup |
| **Stars / Activity** | 2,300+ (FreeRADIUS) | 500+ (GitHub) | 100+ (GitHub) |
| **Learning Curve** | Low (if familiar with FreeRADIUS) | Medium | Medium-High |

## Deploying FreeRADIUS with Accounting Module

FreeRADIUS includes built-in accounting support through the `radacct` SQL module. This is the most flexible but requires manual SQL queries for reporting.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: freeradius-acct
    restart: unless-stopped
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
    volumes:
      - ./freeradius-config:/etc/freeradius:ro
    environment:
      - FREERADIUS_DIR=/etc/freeradius
    depends_on:
      - mysql
    networks:
      - radius-net

  mysql:
    image: mysql:8
    container_name: radius-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: root-password
      MYSQL_DATABASE: radius
      MYSQL_USER: radius
      MYSQL_PASSWORD: radius-password
    volumes:
      - mysql-data:/var/lib/mysql
      - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro
    networks:
      - radius-net

volumes:
  mysql-data:

networks:
  radius-net:
    driver: bridge
```

### FreeRADIUS Accounting Configuration

Enable the SQL accounting module in `mods-enabled/sql`:

```conf
sql {
    driver = "rlm_sql_mysql"
    dialect = "mysql"
    server = "mysql"
    port = 3306
    login = "radius"
    password = "radius-password"
    radius_db = "radius"

    # Accounting queries
    accounting {
        start = "INSERT INTO radacct (acctsessionid, username, nasipaddress, nasportid,                   nasporttype, acctstarttime, acctsessiontime, acctauthentic,                   connectinfo_start, framedipaddress, acctstartdelay, acctinputoctets,                   acctoutputoctets)                   VALUES ('%{Acct-Session-Id}', '%{SQL-User-Name}', '%{NAS-IP-Address}',                   '%{NAS-Port}', '%{NAS-Port-Type}', FROM_UNIXTIME(%{integer:Event-Timestamp}),                   '%{Acct-Session-Time}', '%{Acct-Authentic}', '%{Connect-Info}',                   '%{Framed-IP-Address}', '%{Acct-Delay-Time}', '%{Acct-Input-Gigawords}',                   '%{Acct-Output-Gigawords}')"

        interim = "UPDATE radacct SET acctupdatetime = FROM_UNIXTIME(%{integer:Event-Timestamp}),                    acctsessiontime = '%{Acct-Session-Time}',                    acctinputoctets = '%{Acct-Input-Gigawords}',                    acctoutputoctets = '%{Acct-Output-Gigawords}'                    WHERE acctsessionid = '%{Acct-Session-Id}'"

        stop = "UPDATE radacct SET acctstoptime = FROM_UNIXTIME(%{integer:Event-Timestamp}),                 acctsessiontime = '%{Acct-Session-Time}',                 acctterminatecause = '%{Acct-Terminate-Cause}',                 acctinputoctets = '%{Acct-Input-Gigawords}',                 acctoutputoctets = '%{Acct-Output-Gigawords}'                 WHERE acctsessionid = '%{Acct-Session-Id}'"
    }
}
```

### Querying Accounting Data

```bash
# Active sessions
mysql -u radius -p radius -e "
  SELECT username, nasipaddress, acctstarttime, acctsessiontime,
         acctinputoctets, acctoutputoctets
  FROM radacct WHERE acctstoptime IS NULL;"

# Total bandwidth per user (last 30 days)
mysql -u radius -p radius -e "
  SELECT username,
         SUM(acctinputoctets) as bytes_in,
         SUM(acctoutputoctets) as bytes_out,
         COUNT(*) as sessions
  FROM radacct
  WHERE acctstarttime > DATE_SUB(NOW(), INTERVAL 30 DAY)
  GROUP BY username;"

# Peak concurrent sessions
mysql -u radius -p radius -e "
  SELECT DATE(acctstarttime) as day, COUNT(*) as sessions
  FROM radacct
  GROUP BY DATE(acctstarttime)
  ORDER BY sessions DESC LIMIT 10;"
```

## Deploying Daloradius

Daloradius provides a web-based management interface on top of FreeRADIUS with MySQL, adding reporting charts and user management.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  daloradius:
    image: freeradius/daloradius:latest
    container_name: daloradius
    restart: unless-stopped
    ports:
      - "80:80"
    environment:
      - DALORADIUS_DB_HOST=mysql
      - DALORADIUS_DB_NAME=radius
      - DALORADIUS_DB_USER=radius
      - DALORADIUS_DB_PASS=radius-password
      - FREERADIUS_SQL=yes
    depends_on:
      - mysql
    networks:
      - radius-net

  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: daloradius-freeradius
    restart: unless-stopped
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
    volumes:
      - ./freeradius-config:/etc/freeradius:ro
    environment:
      - FREERADIUS_DIR=/etc/freeradius
    depends_on:
      - mysql
    networks:
      - radius-net

  mysql:
    image: mysql:8
    container_name: daloradius-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: root-password
      MYSQL_DATABASE: radius
      MYSQL_USER: radius
      MYSQL_PASSWORD: radius-password
    volumes:
      - daloradius-mysql-data:/var/lib/mysql
    networks:
      - radius-net

volumes:
  daloradius-mysql-data:

networks:
  radius-net:
    driver: bridge
```

### Daloradius Key Features

- **Web dashboard** — graphical overview of active sessions, NAS status, and user counts
- **Reporting engine** — pre-built reports for top users, session history, and bandwidth usage
- **User management** — create, modify, and delete RADIUS users through the web interface
- **Batch user creation** — upload CSV files to create multiple accounts at once
- **Hotspot management** — captive portal integration for guest Wi-Fi

## Deploying RadiusDesk

RadiusDesk is the most feature-complete open-source RADIUS management platform, including a user self-service portal, payment gateway integration, and multi-tenant support.

### Installation

RadiusDesk does not have official Docker images. The recommended deployment is on Ubuntu:

```bash
# Install dependencies
sudo apt-get install -y nginx mysql-server php-fpm php-mysql

# Clone RadiusDesk
git clone https://github.com/wiredpulse/radiusdesk.git /opt/radiusdesk

# Run the installation script
cd /opt/radiusdesk
sudo bash install.sh

# Configure Nginx
sudo cp /opt/radiusdesk/nginx/radiusdesk.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/radiusdesk.conf /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

### RadiusDesk Key Features

- **User self-service portal** — users can view their own usage, change passwords, and purchase credits
- **Payment gateway integration** — supports Stripe, PayPal, and local payment methods
- **Multi-tenant architecture** — manage multiple organizations from a single installation
- **Dynamic RADIUS profiles** — assign bandwidth limits, session timeouts, and VLANs based on user plans
- **Captive portal** — built-in hotspot login page with customizable themes
- **Real-time session monitoring** — view active sessions, disconnect users, and send CoA (Change of Authorization) requests

## Monitoring RADIUS Accounting

```bash
# Test accounting with radclient
echo "Acct-Status-Type = Start
Acct-Session-Id = test-session-001
User-Name = testuser
NAS-IP-Address = 192.168.1.1
Acct-Session-Time = 0" | radclient -x localhost:1813 acct testing123

# Check real-time accounting packets
tcpdump -i any -n port 1813

# FreeRADIUS debug mode for accounting
freeradius -X | grep -i "acct"
```

## Choosing the Right Accounting Solution

| Scenario | Recommendation |
|----------|---------------|
| Simple accounting, CLI-only | **FreeRADIUS radacct** — direct SQL access, maximum flexibility |
| Web UI for basic reporting | **Daloradius** — easy setup, good for small-to-medium deployments |
| Full-featured ISP platform | **RadiusDesk** — billing, self-service, multi-tenant, captive portal |
| Custom reporting needs | **FreeRADIUS radacct** — write your own SQL queries and dashboards |
| Guest Wi-Fi with self-service | **RadiusDesk** — built-in user portal and payment integration |

## Why Self-Host RADIUS Accounting?

**Usage visibility** is the primary reason to implement RADIUS accounting. Without it, you cannot answer basic operational questions: Who is consuming the most bandwidth? How long do sessions typically last? Which access points are under the heaviest load? Accounting data provides the foundation for capacity planning and troubleshooting.

**Billing and monetization** requires accurate usage records. Whether you operate a paid Wi-Fi hotspot, a residential ISP, or a corporate network with departmental chargebacks, RADIUS accounting provides the metered usage data that billing systems depend on. Self-hosting eliminates the per-record fees that commercial RADIUS accounting platforms charge.

**Security auditing** benefits from complete session logs. When investigating a security incident, RADIUS accounting records provide a timeline of who was connected, from where, and for how long. This is essential for compliance frameworks that require network access audit trails.

For broader AAA infrastructure, our [FreeRADIUS AAA comparison](../2026-04-25-freeradius-vs-toughradius-vs-tac-plus-self-hosted-aaa-servers-2026/) covers authentication and authorization platforms. For RADIUS management interfaces, our [RADIUS management guide](../2026-05-04-self-hosted-radius-management-platforms-daloradius-freeradius-manager-guide/) covers web-based administration tools. For network access control, our [NAC comparison](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/) covers enterprise access control platforms.

## FAQ

### What is the difference between RADIUS authentication and accounting?

RADIUS authentication verifies user credentials and grants or denies network access. RADIUS accounting tracks what happens after authentication — session start/stop times, data usage, and connection details. They use different UDP ports: 1812 for authentication, 1813 for accounting.

### Can I use FreeRADIUS accounting without a web interface?

Yes. FreeRADIUS radacct writes directly to SQL tables. You can query the data with any SQL client, build custom dashboards with Grafana, or export reports with cron jobs and scripts. A web interface is optional.

### How much disk space does RADIUS accounting data consume?

For a typical deployment with 1,000 users averaging 2 sessions per day, accounting data consumes roughly 50-100 MB per month. At scale (10,000+ users), you should implement data retention policies — archive old records to cold storage and purge the active table after 90-180 days.

### Can Daloradius handle multiple NAS devices?

Yes. Daloradius supports multiple NAS entries in its database, each with its own shared secret. You can add NAS devices through the web interface and assign them to specific realms or groups.

### Does RadiusDesk support CoA (Change of Authorization)?

Yes. RadiusDesk can send CoA requests to dynamically change user session parameters (bandwidth, VLAN) or disconnect active users without requiring them to re-authenticate.

### How do I integrate RADIUS accounting with Grafana for dashboards?

Configure the MySQL data source in Grafana pointing to your FreeRADIUS database. Write SQL queries as Grafana panels: active sessions count, bandwidth over time, top users by data consumption, session duration histograms, and NAS health metrics. The radacct table schema is well-documented and Grafana SQL plugins handle the rendering.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RADIUS Accounting: FreeRADIUS radacct vs Daloradius vs RadiusDesk",
  "description": "Compare FreeRADIUS radacct, Daloradius, and RadiusDesk for self-hosted RADIUS accounting. Includes Docker Compose configs, SQL queries, and deployment guides.",
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
