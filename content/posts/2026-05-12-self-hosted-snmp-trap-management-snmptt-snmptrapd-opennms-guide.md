---
title: "Self-Hosted SNMP Trap Management: SNMPTT vs snmptrapd vs OpenNMS Trapd"
date: "2026-05-12"
tags: ["snmp", "network-monitoring", "trap-management", "self-hosted", "infrastructure"]
draft: false
---

SNMP traps are the unsung heroes of network monitoring. Unlike polling-based approaches that ask devices "are you okay?" every few minutes, traps let devices proactively shout "something's wrong!" the moment it happens. But receiving traps is only half the battle — you need a trap manager to decode, filter, correlate, and alert on them. This guide compares three open-source SNMP trap management solutions.

## Why SNMP Trap Management Matters

Network devices generate SNMP traps for critical events: link down, CPU threshold exceeded, fan failure, temperature warnings, BGP session drops, and more. Without proper trap management, these events are lost or buried in log files.

A good SNMP trap management system provides:

- **Real-time event detection** — Receive and process traps within seconds of occurrence
- **Intelligent filtering** — Suppress informational traps and escalate critical ones
- **Trap translation** — Convert cryptic OID numbers into human-readable messages
- **Event correlation** — Group related traps to reduce alert fatigue
- **Historical archive** — Maintain a searchable trap history for incident investigation
- **Integration hooks** — Forward traps to monitoring systems, ticketing platforms, and notification services

For broader network monitoring, see our [network topology mapping guide](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-auto-discovery/) and [SNMP collectors comparison](../2026-04-26-snmp-collectors-snmp-exporter-snmpcollector-telegraf-self-hosted-guide-2026/). If you need infrastructure-wide monitoring, our [Zabbix vs CheckMK guide](../2026-04-26-checkmk-vs-zabbix-vs-nagios-self-hosted-infrastructure-monitoring-2026/) covers full-stack monitoring platforms.

## SNMPTT (SNMP Trap Translator)

**SNMPTT** is the most widely deployed open-source SNMP trap handler on Linux. It receives traps from `snmptrapd`, translates them using MIB files into human-readable format, and can forward them to syslog, email, SQL databases, or custom scripts.

### Key Features

- MIB-based trap translation (human-readable messages)
- Multiple output handlers (syslog, SQL, email, EXEC, FORWARD)
- Trap severity classification (normal, warning, major, critical)
- Event-based filtering and suppression
- Duplicate trap detection
- Custom event handlers (execute scripts on specific traps)
- Supports SNMPv1, SNMPv2c, and SNMPv3

### Installation

```bash
# Debian/Ubuntu
sudo apt install snmptt

# RHEL/CentOS
sudo dnf install net-snmp-utils net-snmp-perl snmptt
```

### Configuration

SNMPTT works as a pass-through from `snmptrapd`. Configure snmptrapd to forward traps to SNMPTT:

```bash
# /etc/snmp/snmptrapd.conf
authCommunity execute,log,net public
authCommunity execute,log,net mycommunity
traphandle default /usr/sbin/snmptthandler
```

Then configure SNMPTT's event definitions:

```ini
# /etc/snmp/snmptt.conf
EVENT coldStart .1.3.6.1.6.3.1.1.5.1 "Status Events" Normal
FORMAT Device reinitialized (coldStart)
EXEC /usr/local/bin/alert_coldstart.sh "$r" "$s"

EVENT linkDown .1.3.6.1.6.3.1.1.5.3 "Link Status" Critical
FORMAT Link down on interface $1. Admin state: $2. Operational state: $3
EXEC /usr/local/bin/alert_linkdown.sh "$r" "$1"

EVENT linkUp .1.3.6.1.6.3.1.1.5.4 "Link Status" Normal
FORMAT Link up on interface $1. Admin state: $2. Operational state: $3
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  snmptrapd:
    image: linuxserver/snmptrapd:latest
    container_name: snmptrapd
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - COMMUNITY=public
    volumes:
      - ./snmptrapd.conf:/config/snmptrapd.conf:ro
      - ./mibs:/usr/share/snmp/mibs:ro
    ports:
      - "162:162/udp"
    restart: unless-stopped

  snmptt:
    image: custom/snmptt:latest
    container_name: snmptt
    volumes:
      - ./snmptt.conf:/etc/snmp/snmptt.conf:ro
      - ./snmptt.ini:/etc/snmp/snmptt.ini:ro
      - trap_data:/var/log/snmptt
    depends_on:
      - snmptrapd
    restart: unless-stopped

volumes:
  trap_data:
```

SNMPTT is the workhorse of SNMP trap processing. Its strength lies in MIB-based translation and flexible output routing. If you need traps converted to readable messages and forwarded to multiple destinations, SNMPTT is the standard choice.

## Net-SNMP snmptrapd

**snmptrapd** is the reference SNMP trap daemon from the Net-SNMP project. It's the most basic trap receiver — it receives traps, optionally logs them, and can execute handlers. Unlike SNMPTT, it doesn't have built-in severity classification or SQL output, but it's always available where Net-SNMP is installed.

### Key Features

- Included with all Net-SNMP installations
- Supports SNMPv1, SNMPv2c, and SNMPv3
- MIB-based trap translation (via `snmptranslate`)
- Configurable log output (file, syslog)
- Pass-through trap handlers (pipe to external scripts)
- ACL-based access control
- Lightweight — minimal resource usage

### Installation

```bash
# Debian/Ubuntu (usually pre-installed with snmpd)
sudo apt install snmp snmptrapd

# RHEL/CentOS
sudo dnf install net-snmp net-snmp-utils
```

### Configuration

```ini
# /etc/snmp/snmptrapd.conf

# Accept traps from specific communities
authCommunity log,execute,net public
authCommunity log,execute,net private

# Log to syslog
doNotLogTraps no
logOption s

# Forward matching traps to a script
traphandle .1.3.6.1.6.3.1.1.5.3 /usr/local/bin/handle_linkdown.sh
traphandle .1.3.6.1.6.3.1.1.5.4 /usr/local/bin/handle_linkup.sh
traphandle default /usr/local/bin/handle_default.sh

# MIB loading (optional, for translation)
mibs +ALL
mibdirs /usr/share/snmp/mibs:/usr/local/share/snmp/mibs
```

### Systemd Service

```ini
# /etc/systemd/system/snmptrapd.service
[Unit]
Description=SNMP Trap Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/snmptrapd -f -Lo -c /etc/snmp/snmptrapd.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Docker Deployment

```yaml
version: "3.8"
services:
  snmptrapd:
    image: alpine:latest
    container_name: snmptrapd
    command: >
      sh -c "apk add net-snmp net-snmp-tools &&
             snmptrapd -f -Lo -c /etc/snmp/snmptrapd.conf"
    volumes:
      - ./snmptrapd.conf:/etc/snmp/snmptrapd.conf:ro
      - ./mibs:/usr/share/snmp/mibs:ro
      - ./handlers:/usr/local/bin:ro
    ports:
      - "162:162/udp"
    restart: unless-stopped
```

snmptrapd is best suited for environments where you need a lightweight trap receiver with custom processing logic. It's the foundation that SNMPTT builds upon — if you don't need SNMPTT's advanced features, snmptrapd alone may be sufficient.

## OpenNMS Trapd

**OpenNMS Trapd** is the SNMP trap receiver component of the OpenNMS network management platform. Unlike standalone tools (SNMPTT, snmptrapd), it's part of a full-featured NMS with event correlation, notification routing, and a web interface.

### Key Features

- Integrated with full OpenNMS NMS platform
- Automatic MIB compilation and trap translation
- Event correlation and deduplication
- Web-based trap browser and search
- Notification escalation (email, SMS, XMPP)
- Trap-to-event mapping with custom logic
- Supports SNMPv1, SNMPv2c, and SNMPv3
- High-availability clustering support
- REST API for trap integration

### Installation

```bash
# Debian/Ubuntu (OpenNMS repository)
echo "deb https://debian.opennms.org stable main" | sudo tee /etc/apt/sources.list.d/opennms.list
wget -O - https://debian.opennms.org/OPENNMS-GPG-KEY | sudo apt-key add -
sudo apt update
sudo apt install opennms
```

### Trap Configuration

OpenNMS uses XML-based event definitions:

```xml
<!-- /opt/opennms/etc/events/traps.custom.xml -->
<events xmlns="http://xmlns.opennms.org/xsd/eventconf">
  <event>
    <mask>
      <maskelement>
        <mename>id</mename>
        <mevalue>.1.3.6.1.6.3.1.1.5.3</mevalue>
      </maskelement>
    </mask>
    <uei>uei.opennms.org/generic/traps/SNMP_Link_Down</uei>
    <event-label>SNMP Trap: Link Down</event-label>
    <descr>A linkDown trap signifies that an interface has transitioned from
      operational to non-operational state. Interface index: %parm[1]%</descr>
    <severity>Major</severity>
    <logmsg dest="logndisplay">
      Link down on interface %parm[1]% on node %nodeid%
    </logmsg>
  </event>
</events>
```

### Docker Compose (Full OpenNMS Stack)

```yaml
version: "3.8"
services:
  opennms:
    image: opennms/horizon:latest
    container_name: opennms
    environment:
      - OPENNMS_DBNAME=opennms
      - OPENNMS_DBUSER=opennms
      - OPENNMS_DBPASS=opennms
    ports:
      - "8980:8980"
      - "162:162/udp"
      - "10514:10514/udp"
    volumes:
      - opennms_data:/opt/opennms/share
      - ./traps.custom.xml:/opt/opennms/etc/events/traps.custom.xml:ro
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: opennms-db
    environment:
      - POSTGRES_DB=opennms
      - POSTGRES_USER=opennms
      - POSTGRES_PASSWORD=opennms
    volumes:
      - pg_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  opennms_data:
  pg_data:
```

OpenNMS Trapd is the heavyweight champion — it provides the most comprehensive trap management features but requires the full OpenNMS platform. It's ideal for enterprises that need a complete network management solution with trap handling as one component.

## Feature Comparison

| Feature | SNMPTT | snmptrapd | OpenNMS Trapd |
|---------|--------|-----------|---------------|
| **Standalone** | Yes | Yes | No (requires OpenNMS) |
| **MIB Translation** | Yes | Yes | Yes (auto-compile) |
| **Severity Classification** | Yes | No (custom) | Yes |
| **SQL Output** | Yes (MySQL/PostgreSQL) | No | Yes (PostgreSQL) |
| **Web Interface** | No | No | Yes |
| **Event Correlation** | Basic | No | Advanced |
| **SNMPv3 Support** | Yes | Yes | Yes |
| **Duplicate Detection** | Yes | No | Yes |
| **Notification Routing** | Email/EXEC | EXEC only | Email/SMS/XMPP/API |
| **HA/Clustering** | No | No | Yes |
| **Resource Usage** | Low | Very Low | High (full NMS) |
| **Setup Complexity** | Moderate | Simple | Complex |

## Choosing the Right Tool

**Use SNMPTT when:**
- You need MIB-based trap translation with severity classification
- You want to forward traps to multiple destinations (syslog, SQL, email, scripts)
- You have an existing monitoring stack and just need a trap processor
- You need duplicate trap detection without a full NMS platform

**Use snmptrapd when:**
- You want the simplest possible trap receiver
- You have custom processing logic (scripts) that handle everything
- You're already running Net-SNMP and don't want additional dependencies
- Resource constraints are tight (snmptrapd uses minimal memory)

**Use OpenNMS Trapd when:**
- You need a complete network management platform, not just trap handling
- Event correlation and deduplication are critical
- You want a web interface for browsing and searching trap history
- You need high-availability clustering for enterprise deployments

## Security Best Practices

1. **Use SNMPv3** — SNMPv1 and v2c transmit community strings in plaintext. SNMPv3 provides authentication and encryption for trap messages.

2. **Restrict trap sources** — Configure your trap receiver to only accept traps from known network device IPs:
   ```ini
   # snmptrapd.conf
   disableAuthorization no
   authAddress 10.0.1.0/24
   authAddress 10.0.2.0/24
   ```

3. **Separate trap network** — Run SNMP traps on a dedicated management VLAN to prevent interception from untrusted networks.

4. **MIB security** — Only load MIBs from trusted sources. Malicious MIB files can contain embedded Perl code that executes during translation.

5. **Rate limiting** — Configure trap flood protection to prevent a misconfigured device from overwhelming your trap handler:
   ```bash
   # iptables rate limit for SNMP traps
   sudo iptables -A INPUT -p udp --dport 162 -m limit --limit 100/sec -j ACCEPT
   sudo iptables -A INPUT -p udp --dport 162 -j DROP
   ```

## FAQ

### What is the difference between SNMP traps and SNMP polling?

SNMP polling is when a management system actively queries devices for data (GET/GETNEXT requests) at regular intervals. SNMP traps are unsolicited notifications sent by devices when specific events occur. Polling tells you the current state; traps tell you about state changes. For comprehensive monitoring, use both — polling for metrics and trends, traps for immediate event notification.

### Can SNMPTT handle SNMPv3 traps?

Yes. SNMPTT supports SNMPv1, SNMPv2c, and SNMPv3 traps. For SNMPv3, configure the users in `/etc/snmp/snmptrapd.conf` with authentication and privacy protocols:
```
createUser -e 0x8000000001020304 trapuser SHA authpass AES privpass
authUser log,execute,net trapuser
```

### How do I convert MIB files to SNMPTT format?

SNMPTT includes the `snmpttconvertmib` script that converts standard MIB files to SNMPTT event definition format:
```bash
snmpttconvertmib --in=/usr/share/snmp/mibs/CISCO-SMI.my --out=/etc/snmp/snmptt.conf.cisco --exec='/usr/local/bin/handler.sh'
```
Not all MIBs convert perfectly — some require manual editing of the generated event definitions.

### Does OpenNMS Trapd work without the full OpenNMS platform?

No. OpenNMS Trapd is tightly integrated with the OpenNMS event processing engine, database, and web UI. If you only need trap handling without the full NMS, use SNMPTT or snmptrapd instead. However, OpenNMS is available as a single package install — you don't need to configure components separately.

### How many traps per second can these tools handle?

snmptrapd can handle 1,000+ traps/sec with minimal CPU usage (it's essentially a UDP listener with logging). SNMPTT adds Perl-based MIB translation overhead — expect 500-1,000 traps/sec on modern hardware. OpenNMS Trapd performance depends on the PostgreSQL backend — typically 200-500 traps/sec with the full event processing pipeline.

### Can I forward SNMP traps to a Slack channel or Teams webhook?

SNMPTT can execute custom scripts via the EXEC handler, making it straightforward to forward traps to webhooks. snmptrapd also supports EXEC handlers. OpenNMS has built-in notification routing that includes webhook destinations. Here's a simple SNMPTT EXEC handler for Slack:
```bash
#!/bin/bash
# /usr/local/bin/trap_to_slack.sh
DEVICE=$1
TRAP=$2
curl -X POST -H 'Content-type: application/json'   --data "{"text":"SNMP Trap from $DEVICE: $TRAP"}"   https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### What happens if the trap receiver goes down?

SNMP traps are sent via UDP (connectionless), so if your trap receiver is down, traps are silently dropped — the sending device does not retry. This is why redundancy matters. For SNMPTT/snmptrapd, run multiple receivers behind a load balancer. OpenNMS supports HA clustering with automatic failover.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SNMP Trap Management: SNMPTT vs snmptrapd vs OpenNMS Trapd",
  "description": "Compare three open-source SNMP trap management solutions — SNMPTT, snmptrapd, and OpenNMS Trapd — with Docker configs, MIB translation, and security best practices.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
