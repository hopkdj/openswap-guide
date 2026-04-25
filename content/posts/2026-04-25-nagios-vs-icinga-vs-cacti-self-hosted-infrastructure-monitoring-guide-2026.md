---
title: "Nagios vs Icinga vs Cacti: Best Self-Hosted Infrastructure Monitoring 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "monitoring", "infrastructure"]
draft: false
description: "Compare Nagios, Icinga 2, and Cacti for self-hosted infrastructure monitoring. Includes Docker deployment guides, feature comparisons, and configuration examples for 2026."
---

When it comes to monitoring servers, networks, and services, three open-source tools have defined the landscape for decades: **Nagios**, **Icinga**, and **Cacti**. Each takes a fundamentally different approach to infrastructure monitoring, and choosing the right one depends on what you need to monitor, how many hosts you manage, and what kind of visibility you require.

In this guide, we compare these three monitoring platforms head-to-head, covering architecture, features, deployment options, and real-world use cases — all with verified data from their official repositories as of April 2026.

## Why Self-Host Your Infrastructure Monitoring

Cloud-based monitoring services like Datadog, New Relic, and Uptime Robot are convenient, but they come with recurring costs, data privacy concerns, and vendor lock-in. Self-hosted monitoring keeps your infrastructure data on your own servers, giving you full control over retention, alerting rules, and integrations.

For organizations managing dozens or hundreds of servers, network devices, and services, a self-hosted monitoring stack eliminates per-host pricing, supports custom plugins for proprietary systems, and keeps sensitive topology data off third-party servers. The three tools we cover here are mature, well-documented, and backed by active communities.

For a broader look at modern monitoring alternatives, see our [Zabbix vs LibreNMS vs Netdata guide](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) and our [endpoint monitoring comparison](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/).

## Nagios Core: The Original Monitoring Engine

**Nagios Core** is the grandfather of infrastructure monitoring. First released in 1999, it introduced the plugin-based monitoring model that nearly every modern tool still follows. The project is maintained by Nagios Enterprises and remains freely available under the GPL.

**Current stats** (from [GitHub](https://github.com/NagiosEnterprises/nagioscore)):
- **Stars**: 1,979
- **Language**: C
- **Last updated**: April 13, 2026

Nagios Core monitors hosts and services using a polling model. Checks are executed at configurable intervals, and results are evaluated against thresholds to determine service states (OK, WARNING, CRITICAL, UNKNOWN). The web interface provides a read-only dashboard of current status, historical data, and acknowledged issues.

### Key Features

- **Plugin ecosystem**: Over 5,000 community plugins for checking everything from HTTP response times to database replication lag
- **Flexible notification system**: Email, SMS, and custom notification scripts with escalation policies
- **Host and service dependencies**: Prevent alert storms by defining dependency chains
- **Event handlers**: Automatically restart failed services or clear caches when problems are detected
- **NRPE (Nagios Remote Plugin Executor)**: Run checks on remote hosts behind firewalls

### How Nagios Works

Nagios reads a configuration directory containing host definitions, service definitions, contact groups, and time periods. The scheduler executes check plugins at defined intervals, parses their exit codes (0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN), and updates the status log. The CGI-based web interface reads these logs to display the current state.

```cfg
# Example Nagios host definition (hosts.cfg)
define host {
    use             linux-server
    host_name       web-prod-01
    alias           Production Web Server
    address         192.168.1.10
    check_period    24x7
    check_command   check-host-alive
    max_check_attempts  5
    notification_interval 60
    contact_groups  admins
}

# Service definition (services.cfg)
define service {
    use                 generic-service
    host_name           web-prod-01
    service_description HTTP
    check_command       check_http!-H 192.168.1.10 -u /health
    check_interval      5
    retry_interval      1
    max_check_attempts  3
}
```

### Installing Nagios Core on Ubuntu

```bash
# Install build dependencies
sudo apt update
sudo apt install -y build-essential apache2 php libapache2-mod-php \
    libgd-dev libssl-dev libcurl4-openssl-dev pkg-config

# Download and compile
wget https://github.com/NagiosEnterprises/nagioscore/releases/download/nagios-4.5.2/nagios-4.5.2.tar.gz
tar xzf nagios-4.5.2.tar.gz
cd nagios-4.5.2
./configure --with-httpd-conf=/etc/apache2/sites-enabled
make all
sudo make install
sudo make install-init
sudo make install-config
sudo make install-commandmode
sudo make install-webconf

# Install plugins
sudo apt install -y nagios-plugins
sudo systemctl enable nagios
sudo systemctl start nagios
```

### Running Nagios with Docker

While Nagios doesn't provide an official Docker image, the community-maintained `jasonrivers/nagios` image packages Nagios Core with the standard plugins:

```yaml
# docker-compose-nagios.yml
version: "3.8"

services:
  nagios:
    image: jasonrivers/nagios:latest
    container_name: nagios
    ports:
      - "8080:80"
    volumes:
      - ./nagios-config/etc:/opt/nagios/etc
      - ./nagios-config/var:/opt/nagios/var
      - ./nagios-plugins:/opt/nagios/libexec
    environment:
      - NAGIOS_FQDN=nagios.example.com
      - NAGIOS_ADMIN_USER=admin
      - NAGIOS_ADMIN_PASS=changeme
    restart: unless-stopped
```

After starting, the web interface is available at `http://localhost:8080/nagios`.

## Icinga 2: The Nagios Fork with Modern Architecture

**Icinga 2** started as a fork of Nagios in 2009, created by developers who wanted a more modern architecture with better scalability, a configuration language, and native clustering. Today it is a fully independent project with a distinct codebase, written in C++ with a powerful domain-specific configuration language.

**Current stats** (from [GitHub](https://github.com/Icinga/icinga2)):
- **Stars**: 2,197
- **Language**: C++
- **Last updated**: April 24, 2026

Icinga 2 retains Nagios plugin compatibility while adding native features that Nagios requires plugins for: distributed monitoring, a REST API, a modern web interface (Icinga Web 2), and a configuration language with objects, templates, and inheritance.

### Key Features

- **Icinga DSL**: Object-oriented configuration language with templates, inheritance, and apply rules
- **REST API**: Full read/write API for automation, integration, and external tooling
- **Distributed monitoring**: Master-satellite-cluster topology for monitoring across multiple sites
- **Icinga DB**: Real-time state synchronization using Redis, replacing the legacy IDO database
- **Icinga Web 2**: Modern, responsive web interface with dashboards, modules, and customizable views
- **Business process monitoring**: Visualize complex service dependencies as business process graphs

### How Icinga 2 Architecture Works

Icinga 2 uses a hierarchical architecture. A master node receives check results from satellite nodes, which in turn collect results from agent nodes running on monitored hosts. Configuration is defined on the master and distributed downward. The Icinga DB component syncs state data to Redis, which the web interface reads in real time.

```conf
# Example Icinga 2 host definition (conf.d/hosts.conf)
object Host "web-prod-01" {
  import "generic-host"
  address = "192.168.1.10"
  vars.os = "Linux"
  vars.http_vhosts["main-site"] = {
    http_uri = "/health"
    http_sni = true
    http_ssl = true
  }
}

# Apply rule for HTTP checks on all hosts with http_vhosts
apply Service for (http_vhost => config in host.vars.http_vhosts) {
  import "generic-service"
  check_command = "http"
  vars += config
  assign where host.vars.http_vhosts
}
```

### Installing Icinga 2 on Ubuntu

```bash
# Add the Icinga repository
apt update
apt install -y apt-transport-https wget gnupg
wget -O - https://packages.icinga.com/icinga.key | gpg --dearmor -o /usr/share/keyrings/icinga.gpg
echo "deb [signed-by=/usr/share/keyrings/icinga.gpg] https://packages.icinga.com/ubuntu icinga-$(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/icinga.list

apt update
apt install -y icinga2 icinga2-ido-mysql monitoring-plugins

# Enable features
icinga2 feature enable ido-mysql
icinga2 feature enable command
systemctl enable icinga2
systemctl start icinga2

# Set up the IDO database
mysql -u root -e "CREATE DATABASE icinga_ido; GRANT ALL ON icinga_ido.* TO 'icinga'@'localhost' IDENTIFIED BY 'icinga';"
```

### Running Icinga 2 with Docker

Icinga provides an official Docker image with over 1.4 million pulls:

```yaml
# docker-compose-icinga2.yml
version: "3.8"

services:
  icinga2:
    image: icinga/icinga2:latest
    container_name: icinga2
    ports:
      - "5665:5665"
    volumes:
      - ./icinga2-conf/etc/icinga2:/etc/icinga2
      - ./icinga2-conf/var/lib/icinga2:/var/lib/icinga2
    environment:
      - ICINGA2_API_USER=icingaadmin
      - ICINGA2_API_PASS=icinga
    restart: unless-stopped

  # Optional: Icinga Web 2 for the dashboard
  icingaweb2:
    image: icinga/icingaweb2:latest
    container_name: icingaweb2
    ports:
      - "8080:80"
    volumes:
      - ./icingaweb2-conf/etc/icingaweb2:/etc/icingaweb2
      - ./icingaweb2-conf/var/lib/icingaweb2:/var/lib/icingaweb2
    depends_on:
      - icinga2
    restart: unless-stopped
```

## Cacti: Network Graphing and Performance Monitoring

**Cacti** takes a fundamentally different approach from Nagios and Icinga. Rather than focusing on alert-driven monitoring, Cacti specializes in **performance graphing** using RRDtool (Round Robin Database). It collects metrics via SNMP at regular intervals and generates time-series graphs for network devices, servers, and services.

**Current stats** (from [GitHub](https://github.com/Cacti/cacti)):
- **Stars**: 1,820
- **Language**: PHP
- **Last updated**: April 22, 2026

Cacti excels at historical trend analysis. While Nagios tells you "the server is down right now," Cacti shows you "CPU utilization has been climbing steadily for three weeks." For capacity planning and performance baselining, Cacti is unmatched among the three.

### Key Features

- **RRDtool integration**: High-performance time-series data storage with automatic data consolidation
- **SNMP polling**: Built-in SNMP support for network devices — switches, routers, firewalls, UPS units
- **Template system**: Host templates, graph templates, and data templates for rapid deployment
- **Thold plugin**: Threshold-based alerting that sends notifications when metrics exceed defined limits
- **Discovery module**: Automatic device discovery on network subnets
- **Plugin architecture**: Boost, Real-time, Syslog, and Weathermap plugins extend functionality

### How Cacti Works

Cacti runs a PHP-based polling process (spine or cmd.php) that queries SNMP data sources on a configurable schedule. The collected data is stored in RRD files, and a web interface generates graphs from the historical data. The poller runs via cron, typically every 1-5 minutes.

### Running Cacti with Docker

Cacti provides an official `docker-compose.yml` in its repository. Here's a production-oriented setup based on the official configuration:

```yaml
# docker-compose-cacti.yml
version: "3.8"

services:
  cacti:
    image: cacti/cacti:latest
    container_name: cacti
    ports:
      - "8080:80"
      - "8443:443"
    volumes:
      - cacti_data:/var/lib/cacti
      - cacti_log:/var/log/cacti
    environment:
      - TZ=UTC
      - DB_HOST=cacti_db
      - DB_PORT=3306
      - DB_USER=cacti
      - DB_PASS=cacti_password
      - DB_NAME=cacti
      - CRON=1
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: mariadb:11.8
    container_name: cacti_db
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: cacti
      MYSQL_USER: cacti
      MYSQL_PASSWORD: cacti_password
      TZ: UTC
    volumes:
      - cacti_db:/var/lib/mysql
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --max-connections=200
      - --innodb-buffer-pool-size=1G
      - --innodb-flush-log-at-timeout=3
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  cacti_data:
  cacti_log:
  cacti_db:
```

Access the web installer at `http://localhost:8080` to complete the initial setup. The database schema is auto-imported on first start.

### Installing Cacti from Packages

For systems without Docker:

```bash
# Install dependencies on Ubuntu
sudo apt update
sudo apt install -y apache2 mariadb-server mariadb-client \
    php php-{mysql,snmp,xml,mbstring,gd,intl,ldap,gmp} \
    snmp snmpd rrdtool

# Download Cacti
wget https://www.cacti.net/downloads/cacti-latest.tar.gz
tar xzf cacti-latest.tar.gz
sudo mv cacti-*/ /var/www/html/cacti

# Set up the database
sudo mysql -u root -e "CREATE DATABASE cacti CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -u root -e "CREATE USER 'cacti'@'localhost' IDENTIFIED BY 'cacti_password';"
sudo mysql -u root -e "GRANT ALL ON cacti.* TO 'cacti'@'localhost';"
sudo mysql -u root -e "GRANT SELECT ON mysql.time_zone_name TO 'cacti'@'localhost';"

# Import timezone data and Cacti schema
sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root mysql
sudo mysql -u root cacti < /var/www/html/cacti/cacti.sql

# Set up the poller cron job
echo "*/5 * * * * www-data php /var/www/html/cacti/poller.php > /dev/null 2>&1" \
  | sudo tee /etc/cron.d/cacti
```

## Feature Comparison: Nagios vs Icinga 2 vs Cacti

| Feature | Nagios Core | Icinga 2 | Cacti |
|---------|-------------|----------|-------|
| **Primary focus** | Alert-driven monitoring | Alert-driven monitoring | Performance graphing |
| **Language** | C | C++ | PHP |
| **GitHub stars** | 1,979 | 2,197 | 1,820 |
| **Configuration** | Text files (CFG) | DSL (object-oriented) | Web UI + database |
| **Check mechanism** | Plugins (polling) | Plugins + agents (polling) | SNMP + scripts (polling) |
| **Built-in graphing** | No (requires addons) | No (requires Grafana) | Yes (RRDtool native) |
| **REST API** | No (requires addons) | Yes (built-in) | Limited (via plugins) |
| **Distributed monitoring** | Via nsca/nrpe addons | Native master-satellite | Via remote pollers |
| **Database backend** | Flat files + optional IDO | MySQL/PostgreSQL + Redis | MySQL/MariaDB |
| **SNMP support** | Via plugins | Via plugins | Native |
| **Auto-discovery** | No (requires addons) | Limited | Yes (built-in) |
| **Web interface** | Basic CGI | Modern (Icinga Web 2) | Full web app |
| **Plugin compatibility** | Native (defines the standard) | Nagios-compatible | Limited |
| **Docker support** | Community images only | Official image | Official compose |
| **Best for** | Small-medium infrastructure, simple setups | Large-scale, distributed, automation-heavy | Network teams, capacity planning, trend analysis |

## Choosing the Right Tool

### Choose Nagios Core When

- You need a simple, reliable monitoring system for a small to medium infrastructure (up to a few hundred hosts)
- Your team already has Nagios configuration expertise and a library of existing check scripts
- You want the widest plugin compatibility — Nagios plugins work everywhere
- Budget constraints prevent commercial tool adoption but you need enterprise-grade monitoring
- You're monitoring legacy systems that require custom shell script checks

Nagios Core remains the most widely deployed open-source monitoring system. Its plugin ecosystem is unmatched, and if you can describe a check in a shell script, Nagios can run it.

### Choose Icinga 2 When

- You need distributed monitoring across multiple sites or data centers
- Automation is important — the REST API enables CI/CD integration and infrastructure-as-code workflows
- You want a modern web interface with customizable dashboards and role-based access control
- You're scaling beyond what a single Nagios instance can handle
- You want Nagios plugin compatibility with a more maintainable configuration system

Icinga 2 is the natural evolution of the Nagios monitoring model. It accepts all Nagios plugins while adding distributed architecture, a REST API, and a configuration language that scales.

### Choose Cacti When

- Your primary need is **network performance monitoring** and capacity planning
- You manage many SNMP-enabled devices — switches, routers, firewalls, load balancers
- Historical trending matters more than instant alerting
- You want to visualize bandwidth utilization, interface errors, and device resource trends
- You need automated device discovery on large network segments

Cacti fills a different niche. It's not a replacement for Nagios or Icinga — it's a complement. Many organizations run Cacti alongside Nagios or Icinga: one for alerting and incident response, the other for performance trending and capacity planning.

## Monitoring Architecture Recommendations

### Small Team, Single Site (Under 50 Hosts)

```
[Nagios Core] → [Plugins] → [Hosts/Services]
      ↓
  [Email/SMS alerts]
```

Start simple. Nagios Core with standard plugins covers 90% of monitoring needs for small infrastructures. The learning curve is well-documented, and the community support is extensive.

### Multi-Site Organization (50-500 Hosts)

```
              [Icinga 2 Master]
             /        |         \
    [Satellite A] [Satellite B] [Satellite C]
         |              |             |
    [Local hosts]  [Local hosts]  [Local hosts]
```

Icinga 2's master-satellite architecture lets you deploy monitoring agents at each site. Check results flow upstream to the master, which handles alerting, reporting, and the web interface. If a satellite loses connectivity to the master, it buffers results locally.

### Network-Focused Team (Any Size)

```
[Cacti Poller] → [SNMP] → [Switches/Routers/Firewalls]
      ↓                    ↓
  [RRD Files]        [Performance Graphs]
      ↓                    ↓
  [Web Dashboard] ← [Thold Alerts]
```

Deploy Cacti for network device monitoring and pair it with Nagios or Icinga for server-level alerting. This hybrid approach gives you both real-time incident detection and long-term performance trending.

For teams looking to round out their monitoring stack, consider our guide to [self-hosted alerting tools](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting-2026/) for notification management across any of these platforms.

## FAQ

### Is Nagios Core still actively maintained?

Yes. Nagios Core receives regular updates from Nagios Enterprises. The latest release was published in April 2026, and the project continues to receive bug fixes and security patches. However, major feature development has slowed compared to its derivatives like Icinga 2. The community plugin ecosystem remains vibrant and continues to grow.

### Can I migrate from Nagios to Icinga 2?

Yes. Icinga 2 is designed to be a drop-in replacement for Nagios. It uses the same plugin interface, so your existing check commands and plugins work without modification. Icinga 2 even includes a configuration migration tool (`icinga2 wizard`) that can convert Nagios-style configuration files to the Icinga DSL. The migration path is well-documented in the official Icinga documentation.

### Does Cacti support alerting?

Out of the box, Cacti focuses on graphing rather than alerting. However, the **Thold plugin** (Threshold) adds threshold-based notifications. You can define upper and lower bounds for any data source and configure email, SMS, or webhook notifications when thresholds are breached. For comprehensive alerting, many teams pair Cacti with a dedicated alerting system like Prometheus Alertmanager.

### Which tool is easiest to set up?

Cacti has the most guided setup experience — its web installer walks you through database configuration, poller selection, and initial device discovery. Nagios Core requires manual configuration file editing but has extensive documentation and community tutorials. Icinga 2 has the steepest initial learning curve due to its DSL and multi-component architecture, but pays off with better scalability and automation capabilities once configured.

### Can I run all three tools together?

Absolutely. This is a common pattern: Nagios or Icinga 2 handles real-time alerting and incident management, while Cacti collects SNMP performance data for capacity planning and trend analysis. Since they use different data storage backends and polling mechanisms, they don't conflict. You can even use Icinga 2's notification system to alert on thresholds detected by Cacti's Thold plugin through webhook integrations.

### What are the hardware requirements?

- **Nagios Core**: 1 CPU, 512MB RAM for up to 100 hosts. Scales linearly — 2-4 CPUs recommended for 500+ hosts.
- **Icinga 2**: 2 CPUs, 2GB RAM minimum (includes Icinga DB Redis). The master-satellite architecture distributes load across nodes.
- **Cacti**: 2 CPUs, 4GB RAM, fast disk I/O (RRD files benefit from SSDs). The poller process is I/O-intensive on large deployments.

All three tools benefit from SSD storage for their data directories, and all can run comfortably on a modest VPS for small deployments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nagios vs Icinga vs Cacti: Best Self-Hosted Infrastructure Monitoring 2026",
  "description": "Compare Nagios, Icinga 2, and Cacti for self-hosted infrastructure monitoring. Includes Docker deployment guides, feature comparisons, and configuration examples for 2026.",
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
