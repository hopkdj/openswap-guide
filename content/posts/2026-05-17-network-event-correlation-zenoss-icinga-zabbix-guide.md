---
title: "Self-Hosted Network Event Correlation: Zenoss vs Icinga vs Zabbix (2026)"
date: "2026-05-17"
tags: ["event-correlation", "zenoss", "icinga", "zabbix", "monitoring", "networking"]
draft: false
---

Network event correlation is the process of analyzing multiple monitoring alerts to identify root causes, suppress noise, and provide actionable insights. In a typical enterprise network with hundreds of devices and thousands of metrics, a single network failure can trigger dozens or hundreds of individual alerts. Event correlation transforms this alert flood into a single, meaningful incident.

In this guide, we compare three self-hosted monitoring platforms for their **network event correlation capabilities**: **Zenoss Core**, **Icinga**, and **Zabbix**. Each offers a different approach to correlating events, from Zenoss's service-model-driven correlation to Icinga's business process monitoring and Zabbix's built-in event correlation engine.

## What is Network Event Correlation?

Event correlation solves the "alert storm" problem. When a core switch fails, you might receive:
- 50+ device unreachable alerts (SNMP polling failures)
- 200+ interface down alerts
- 30+ BGP session down alerts
- 15+ application health alerts (services behind the switch)
- 5+ storage connectivity alerts

Without correlation, your NOC team sees 300+ individual alerts. With correlation, you see: **"Core Switch SW-01 down — 305 dependent alerts suppressed."**

Key event correlation techniques:
- **Topology-based correlation**: Map alerts to network topology to identify the root device
- **Temporal correlation**: Group alerts occurring within the same time window
- **Rule-based correlation**: Define custom rules (if A AND B occur, trigger incident C)
- **Statistical correlation**: Use pattern recognition to identify recurring alert combinations
- **Service model correlation**: Map infrastructure alerts to business service impact

## Tool Comparison

| Feature | Zenoss Core | Icinga | Zabbix |
|---|---|---|---|
| **Correlation Engine** | Service model (CMDB-driven) | Business process monitoring | Built-in event correlation rules |
| **Auto-Discovery** | Yes (network auto-discovery) | Partial (via agents/API) | Yes (network discovery rules) |
| **Topology Mapping** | Automatic (SNMP + Layer 2/3) | Manual (via host groups) | Partial (via dependency rules) |
| **Root Cause Analysis** | Yes (service impact analysis) | Via business processes | Via event correlation rules |
| **Alert Deduplication** | Yes (event class grouping) | Yes (problem deduplication) | Yes (event suppression) |
| **Custom Rules** | Transform rules (Python) | Business process definitions | Event correlation tags/rules |
| **Web UI** | Full web dashboard | Icinga Web 2 | Full web interface |
| **API** | REST API | REST API | REST API |
| **Scalability** | 10,000+ devices | 5,000+ hosts | 100,000+ items |
| **Docker Support** | Community images | Official images | Official images |
| **GitHub Stars** | 800+ (zenoss/zenoss) | 1,300+ (Icinga) | N/A (sourceforge) |

## Zenoss Core Event Correlation

Zenoss Core takes a **service model-driven approach** to event correlation. It automatically discovers network topology, builds a service model (CMDB), and correlates alerts based on infrastructure dependencies.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  zenoss-core:
    image: zenoss/core:latest
    container_name: zenoss-core
    hostname: zenoss-01
    ports:
      - "8080:8080"   # Web UI
      - "162:162/udp" # SNMP traps
      - "514:514/udp" # Syslog
    volumes:
      - zenoss-data:/opt/zenoss/var
      - zenoss-etc:/opt/zenoss/etc
    environment:
      - ZENOSS_ADMIN_PASSWORD=admin
    restart: unless-stopped

  zenoss-snmptrapd:
    image: zenoss/core:latest
    container_name: zenoss-snmptrapd
    ports:
      - "162:162/udp"
    command: ["snmptrapd", "-f", "-Lo", "-c", "/etc/snmp/snmptrapd.conf"]
    restart: unless-stopped

volumes:
  zenoss-data:
  zenoss-etc:
```

### Event Correlation Configuration

Zenoss uses **event classes** and **transforms** for correlation:

```python
# Event transform: correlate interface down alerts to device down
# Location: /zport/dmd/Events/Status/DeviceDown/manage

# If a device is already marked down, suppress interface alerts
if device.getDeviceState() == 'DOWN':
    evt._action = 'drop'
    evt.summary = 'Suppressed: device already down'

# Correlation rule: group BGP session alerts by peer group
if evt.eventClass == '/Network/BGP/PeerDown':
    # Find all BGP peers for this router
    peer_group = device.getPrimaryPeerGroup()
    evt.setSummary(f'BGP peer down on {peer_group}: {evt.component}')
    evt.setSeverity(evt.WARNING)
```

Zenoss correlation strengths:
- **Automatic topology discovery**: SNMP-based Layer 2/3 topology mapping
- **Service impact analysis**: Correlates infrastructure events to business service impact
- **Event class hierarchy**: Organizes events into a tree for intelligent grouping
- **Python transforms**: Custom correlation logic using Python scripts
- **CMDB integration**: Configuration management database for asset-aware correlation

## Icinga Event Correlation

Icinga approaches event correlation through **business process monitoring** and **host/service dependencies**. It maps infrastructure components to business services and correlates alerts based on dependency chains.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  icinga:
    image: jordan/icinga2:latest
    container_name: icinga-core
    hostname: icinga-01
    ports:
      - "5665:5665"   # Icinga API
      - "8080:80"     # Icinga Web 2
    volumes:
      - ./icinga-conf:/etc/icinga2:rw
      - ./icinga-web:/etc/icingaweb2:rw
      - icinga-data:/var/lib/icinga2
    environment:
      - ICINGA_WEB_ADMIN_USER=admin
      - ICINGA_WEB_ADMIN_PASSWORD=admin
    restart: unless-stopped

  icinga-db:
    image: postgres:15
    container_name: icinga-db
    environment:
      - POSTGRES_PASSWORD=icinga
      - POSTGRES_DB=icinga
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  icinga-data:
  postgres-data:
```

### Icinga Dependency-Based Correlation

```
// Host dependency: child host alerts suppressed when parent is down
object Host "core-switch-01" {
    import "generic-host"
    address = "192.168.1.1"
    check_command = "hostalive"
}

object Host "access-switch-01" {
    import "generic-host"
    address = "192.168.2.1"
    check_command = "hostalive"
    
    // Suppress alerts if core switch is down
    vars.parent = "core-switch-01"
}

// Business process: define service impact
object BusinessProcess "core-network" {
    display_name = "Core Network Infrastructure"
    
    // Process tree: if any child fails, the parent is impacted
    add_service("core-switch-01", "ping4")
    add_service("core-switch-01", "snmp")
    add_service("access-switch-01", "ping4")
    add_service("access-switch-01", "snmp")
    
    // Correlation: if 2+ children fail, trigger parent alert
    vars.correlation_rule = "count(CRITICAL) >= 2"
}
```

Icinga correlation strengths:
- **Dependency trees**: Parent-child host relationships for automatic alert suppression
- **Business process monitoring**: Map infrastructure to business services
- **Icinga Web 2 BP module**: Visual business process graphs
- **Elasticsearch integration**: Advanced event analysis and correlation
- **Notification escalation**: Route correlated alerts to the right team

## Zabbix Event Correlation

Zabbix includes a **built-in event correlation engine** with tag-based rules, making it straightforward to define complex correlation logic without custom scripting.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  zabbix-server:
    image: zabbix/zabbix-server-mysql:latest
    container_name: zabbix-server
    hostname: zabbix-01
    ports:
      - "10051:10051"  # Zabbix server
      - "8080:8080"    # Zabbix web UI
    environment:
      - DB_SERVER_HOST=zabbix-db
      - MYSQL_DATABASE=zabbix
      - MYSQL_USER=zabbix
      - MYSQL_PASSWORD=zabbix
      - MYSQL_ROOT_PASSWORD=root
    volumes:
      - zabbix-data:/var/lib/zabbix
    depends_on:
      - zabbix-db
    restart: unless-stopped

  zabbix-db:
    image: mysql:8.0
    container_name: zabbix-db
    environment:
      - MYSQL_DATABASE=zabbix
      - MYSQL_USER=zabbix
      - MYSQL_PASSWORD=zabbix
      - MYSQL_ROOT_PASSWORD=root
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

  zabbix-agent:
    image: zabbix/zabbix-agent2:latest
    container_name: zabbix-agent
    hostname: zabbix-agent-01
    environment:
      - ZBX_SERVER_HOST=zabbix-server
    restart: unless-stopped

volumes:
  zabbix-data:
  mysql-data:
```

### Zabbix Event Correlation Rules

Zabbix uses **event correlation tags** and **correlation rules** defined in the web UI:

```
// Correlation Rule: "Network Device Down"
// Name: Suppress dependent alerts when device is unreachable
// Tags: event.source = network, event.object = device

// Condition:
// Tag: event.source = network
// AND Tag: event.object = device
// AND Trigger severity >= Average

// Operation:
// Close old events with matching tags
// Suppress new events with matching dependency tags

// Correlation Rule: "BGP Session Flapping"
// Name: Detect and suppress BGP flapping alerts
// Tags: service = bgp, event.type = flapping

// Condition:
// Tag: service = bgp
// AND Trigger name contains "BGP session"
// AND Event count > 5 in 300 seconds

// Operation:
// Group events by peer address
// Escalate to network team if count > 10 in 300 seconds
```

Zabbix correlation strengths:
- **Tag-based correlation**: Flexible event tagging for grouping and filtering
- **Built-in engine**: No plugins or custom code required
- **Time-based rules**: Correlate events within specific time windows
- **Old event closure**: Automatically close resolved events when root cause is fixed
- **Massive scale**: Handles 100,000+ items with efficient event processing
- **API-driven**: All correlation rules manageable via REST API

## Building a Network Event Correlation Pipeline

A robust event correlation pipeline combines multiple techniques:

```
┌─────────────────────────────────────────────────────────┐
│                    Raw Alert Sources                      │
│  SNMP Traps  │  Syslog  │  API Health  │  Agent Checks   │
└────────┬──────────┬───────────┬────────────┬─────────────┘
         │          │           │            │
         ▼          ▼           ▼            ▼
┌─────────────────────────────────────────────────────────┐
│              Event Normalization Layer                    │
│   Standardize format, enrich with topology metadata       │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Correlation Engine                           │
│   Deduplicate → Group by topology → Identify root cause   │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Alert Dispatch                               │
│   Route to correct team with root cause + impact info     │
└─────────────────────────────────────────────────────────┘
```

### Correlation Rule Examples

```python
# Rule 1: Topology-based root cause analysis
def correlate_topology(events, topology_graph):
    """Find the root device causing cascading failures."""
    # Build affected device set
    affected = {e.device_id for e in events if e.severity >= 'WARNING'}
    
    # Find the device with most dependents affected
    root_cause = max(affected, 
                     key=lambda d: len(topology_graph.get_dependents(d) & affected))
    
    # Suppress alerts for dependents
    for e in events:
        if e.device_id != root_cause and e.device_id in topology_graph.get_dependents(root_cause):
            e.suppress(f"Root cause: {root_cause}")
    
    return root_cause

# Rule 2: Temporal correlation
def correlate_temporal(events, window_seconds=300):
    """Group events occurring within the same time window."""
    groups = []
    current_group = [events[0]]
    
    for e in events[1:]:
        if (e.timestamp - current_group[0].timestamp).seconds <= window_seconds:
            current_group.append(e)
        else:
            groups.append(current_group)
            current_group = [e]
    
    groups.append(current_group)
    return groups

# Rule 3: BGP session correlation
def correlate_bgp(events):
    """Correlate BGP session alerts by AS number."""
    bgp_events = [e for e in events if e.service == 'bgp']
    as_groups = {}
    
    for e in bgp_events:
        asn = e.peer_as
        if asn not in as_groups:
            as_groups[asn] = []
        as_groups[asn].append(e)
    
    return {asn: evts for asn, evts in as_groups.items() if len(evts) >= 2}
```

## Why Self-Host Your Network Event Correlation?

### Alert Noise Reduction
Enterprise networks generate thousands of alerts daily. Without correlation, NOC teams waste hours triaging duplicate and cascading alerts. Self-hosted event correlation reduces alert volume by 80-95%, allowing teams to focus on actual incidents.

### Faster Mean Time to Resolution (MTTR)
By identifying the root cause of cascading failures, correlated alerts reduce MTTR significantly. Instead of investigating 50 individual alerts, your team investigates the single root cause device or service.

For **BGP peer monitoring**, see our [BGP peer session monitoring guide](../2026-05-17-bgp-peer-session-monitoring-gobgp-frrouting-bird-guide/). For **OSPF adjacency monitoring**, our [OSPF monitoring article](../2026-05-15-self-hosted-ospf-monitoring-frr-bird-gobgp-guide/) covers link-state protocol health. For **network configuration management**, our [Ansible vs Nornir vs NetBox guide](../2026-05-05-self-hosted-network-configuration-management-ansible-nornir-netbox-guide/) covers infrastructure automation.

### Data Privacy and Compliance
Network event data contains sensitive information about your infrastructure topology, device configurations, and service dependencies. Keeping this data on-premises ensures compliance with data sovereignty requirements and prevents exposure to third-party SaaS monitoring platforms.

## FAQ

### What is the difference between event correlation and alert aggregation?

**Alert aggregation** simply groups similar alerts together (e.g., "10 interface down alerts"). **Event correlation** goes further by identifying the root cause and causal relationships between alerts (e.g., "Core switch failure caused 10 interface down alerts — suppress dependent alerts"). Correlation uses topology, timing, and custom rules to determine causality.

### Which tool is best for small networks (< 100 devices)?

For small networks, **Zabbix** offers the best balance of features and simplicity. Its built-in event correlation engine requires no additional configuration beyond defining tags and rules. Zenoss may be overkill for small networks due to its service model complexity.

### Can I use Prometheus with event correlation?

Prometheus itself does not include event correlation. However, you can build a correlation layer on top:
- **Prometheus Alertmanager** for alert grouping and inhibition rules
- **Cortex/Mimir** for multi-tenant alert management
- **Custom correlation service** using Prometheus API and topology data
- **Grafana OnCall** for incident correlation and escalation

### How do I define correlation rules for BGP session failures?

BGP correlation rules should consider:
1. **Single peer failure**: Alert immediately (possible peer issue)
2. **Multiple peers on same router fail**: Correlate to router failure
3. **All peers in same AS fail**: Correlate to AS-level issue
4. **BFD + BGP alerts**: Suppress BGP alerts if BFD already triggered
Use tag-based correlation (Zabbix) or service model dependencies (Zenoss) to implement these rules.

### What is the "alert storm" problem and how does correlation solve it?

The alert storm occurs when a single infrastructure failure triggers dozens of dependent alerts. For example, a firewall failure causes alerts for: device unreachable, all interface down, all BGP sessions down, all application health checks failing, and storage connectivity loss. Event correlation identifies the firewall as the root cause and suppresses the 50+ dependent alerts, presenting only the root cause to the NOC team.

### How do I measure the effectiveness of event correlation?

Key metrics:
- **Alert reduction ratio**: (Total alerts - Correlated alerts) / Total alerts
- **Mean Time to Root Cause (MTRC)**: Time from first alert to root cause identification
- **False positive rate**: Percentage of correlated alerts that were not the actual root cause
- **NOC team response time**: Time from alert to first action
- **Customer impact duration**: Time from incident start to customer resolution

### Can event correlation work with multi-vendor networks?

Yes. All three platforms support multi-vendor environments through:
- **SNMP**: Standard MIBs for device monitoring
- **Syslog**: Universal log ingestion
- **Agent-based monitoring**: Platform-specific agents for detailed metrics
- **API integration**: Vendor-specific APIs for proprietary data
The correlation logic operates at the event level, independent of the underlying device vendor.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Event Correlation: Zenoss vs Icinga vs Zabbix (2026)",
  "description": "Compare network event correlation capabilities of Zenoss Core, Icinga, and Zabbix. Includes Docker Compose configs, correlation rules, and alert noise reduction strategies.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
