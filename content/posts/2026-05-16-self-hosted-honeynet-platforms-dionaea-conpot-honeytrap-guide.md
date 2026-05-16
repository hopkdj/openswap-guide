---
title: "Self-Hosted Honeynet Platforms: Dionaea vs Conpot vs HoneyTrap"
date: "2026-05-16"
tags: ["honeypot", "security", "network-security", "threat-intelligence", "deception-technology"]
draft: false
---

Honeynets are networks of honeypots designed to attract, trap, and analyze malicious activity. Unlike a single honeypot that simulates one service, a honeynet platform provides a coordinated framework for deploying multiple honeypots across different network segments, capturing attacker behavior at scale.

This guide compares three open-source honeynet platforms — **Dionaea**, **Conpot**, and **HoneyTrap** — each taking a different approach to deception technology. We will cover Docker Compose deployments, configuration patterns, and help you choose the right platform for your threat intelligence needs.

## Understanding Honeynet Platforms

A honeynet is a controlled network environment populated with honeypots — intentionally vulnerable services designed to be attacked. The goal is not to protect production systems but to study attacker techniques, collect malware samples, and gather threat intelligence.

| Feature | Dionaea | Conpot | HoneyTrap |
|---------|---------|--------|-----------|
| **Primary Focus** | Malware capture & analysis | ICS/SCADA honeypot | Multi-protocol framework |
| **GitHub Stars** | 802 | 1,474 | 1,300 |
| **Last Updated** | Aug 2024 | May 2026 | Oct 2023 |
| **Protocols** | SMB, HTTP, FTP, MSSQL, TFTP, SIP | S7comm, BACnet, Modbus, HTTP, SNMP | SSH, HTTP, Telnet, and extensible |
| **Language** | Python/C | Python | Go |
| **Docker Support** | Official image | Official image | Official image |
| **Best For** | Malware collection, botnet tracking | Industrial security research | Custom honeypot deployments |

## Dionaea — Malware Capture Honeypot

[Dionaea](https://github.com/DinoTools/dionaea) is a low-interaction honeypot designed to trap malware exploiting vulnerabilities in network services. It emulates services like SMB, HTTP, FTP, and MSSQL, captures exploit payloads, and stores malware samples for analysis.

### Key Features

- **Exploit capture**: Accepts and stores malicious payloads delivered through service emulation
- **Multi-protocol support**: SMB, HTTP, FTP, TFTP, MSSQL, SIP, and more
- **LogSQL backend**: Stores attack data in SQLite or MySQL for querying and analysis
- **VirusTotal integration**: Automatically submits captured samples for analysis
- **iFilters**: Modular filter system for processing captured payloads

### Docker Compose Deployment

```yaml
services:
  dionaea:
    image: dinotools/dionaea:latest
    container_name: dionaea
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./dionaea-config:/opt/dionaea/etc
      - ./dionaea-logs:/opt/dionaea/var/log
      - ./dionaea-bistreams:/opt/dionaea/var/dionaea
    environment:
      - DIONAEA_LISTEN_ALL=true
    cap_add:
      - NET_ADMIN
```

For production deployments, use `network_mode: host` so Dionaea can bind to the actual network interfaces you want to monitor. The volume mounts persist captured malware samples and attack logs.

### Configuration

Dionaea's configuration lives in `/opt/dionaea/etc/dionaea/dionaea.conf`. Key settings include:

```ini
handlers {
  logsql {
    url = "sqlite:///opt/dionaea/var/dionaea/logsql.sqlite"
  }
}

modules {
  python {
    src_dir = "/opt/dionaea/lib/dionaea/python"
    scripts = "ihandlers"
  }
}

services {
  smb {
    ports = ["tcp:445"]
  }
  http {
    ports = ["tcp:80", "tcp:8080"]
  }
}
```

## Conpot — ICS/SCADA Honeypot

[Conpot](https://github.com/mushorg/conpot) is an open-source honeypot targeting Industrial Control Systems (ICS) and SCADA networks. It emulates industrial protocols like S7comm (Siemens), BACnet, and Modbus, making it invaluable for organizations securing critical infrastructure.

### Key Features

- **ICS protocol emulation**: S7comm, BACnet, Modbus/TCP, EnIP
- **Template-based configuration**: Pre-built templates for Siemens S7-200, IP-Camera, and generic ICS devices
- **SNMP support**: Emulates SNMP agents with configurable MIB trees
- **HTTP/HTTPS emulation**: Serves industrial-looking web interfaces
- **Logging**: Syslog, JSON file, and TAXII server output

### Docker Compose Deployment

```yaml
services:
  conpot:
    image: mushorg/conpot:latest
    container_name: conpot
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./conpot-config:/etc/conpot
      - ./conpot-logs:/var/log/conpot
    command: ["--template", "default", "--json"]
    cap_add:
      - NET_ADMIN
```

### Configuration

Conpot uses XML-based templates to define device behavior. The default template emulates a generic industrial device:

```xml
<!-- conpot/templates/default/template.xml -->
<conpot_template xmlns="http://conpot.org/template/1.0">
  <groups>
    <group id="modbus" name="Modbus">
      <device>
        <protocol>modbus</protocol>
        <unit_id>1</unit_id>
      </device>
    </group>
    <group id="s7" name="S7comm">
      <device>
        <protocol>s7comm</protocol>
        <cpu>1200</cpu>
      </device>
    </group>
  </groups>
</conpot_template>
```

Deploy with the `--template` flag to select a specific device profile, or create custom templates for your target environment.

## HoneyTrap — Multi-Protocol Honeypot Framework

[HoneyTrap](https://github.com/honeytrap/honeytrap) is a highly extensible honeypot framework written in Go. Unlike Dionaea and Conpot, HoneyTrap is a framework first — it provides a channel-based architecture where you can chain services, observers, and attackers together to create complex deception environments.

### Key Features

- **Go-based performance**: High-throughput, low-overhead service emulation
- **Channel architecture**: Connect services to observers, stores, and attackers via configurable channels
- **Multi-protocol**: SSH, HTTP, Telnet, and custom protocol handlers
- **Docker-native**: Designed for containerized deployments
- **Extensible**: Plugin system for custom service emulators

### Docker Compose Deployment

```yaml
services:
  honeytrap:
    image: honeytrap/honeytrap:latest
    container_name: honeytrap
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./honeytrap-config:/etc/honeytrap
      - ./honeytrap-data:/var/lib/honeytrap
    command: ["--config", "/etc/honeytrap/config.toml"]
```

### Configuration

HoneyTrap uses TOML configuration to define services and channel routing:

```toml
[services.ssh]
enabled = true
port = 22

[services.http]
enabled = true
port = 80
banner = "Apache/2.4.41 (Ubuntu)"

[channels]
[[channels]]
name = "default"
observers = ["store", "log"]
attackers = ["response"]

[stores.files]
directory = "/var/lib/honeytrap/attacks"

[observers.log]
format = "json"
output = "/var/lib/honeytrap/logs/attacks.log"
```

The channel system is HoneyTrap's key differentiator — you can route different protocols to different observers and storage backends, creating a flexible analysis pipeline.

## Comparison: Malware Collection vs ICS vs Framework

| Aspect | Dionaea | Conpot | HoneyTrap |
|--------|---------|--------|-----------|
| **Malware Samples** | Excellent — captures payloads automatically | Limited — focuses on protocol analysis | Good — captures attack payloads |
| **Protocol Coverage** | Standard IT services (SMB, HTTP, FTP) | Industrial protocols (S7, BACnet, Modbus) | Extensible — SSH, HTTP, custom |
| **Setup Complexity** | Medium — needs iFilter configuration | Low — template-based, works out of box | Medium-High — channel configuration required |
| **Performance** | Good — Python/C hybrid | Good — lightweight Python | Excellent — native Go |
| **Community** | Active DinoTools community | MUSH community, T-Pot integration | Smaller but dedicated |
| **Production Readiness** | High — widely deployed | High — used in critical infra research | Medium — framework, needs customization |

## When to Use Each Platform

**Dionaea** is your best choice when:
- You need to collect malware samples from automated attacks
- You want to monitor standard IT service ports (445, 80, 21)
- You need integration with threat intelligence feeds (VirusTotal, MISP)
- You are studying botnet behavior and exploit trends

**Conpot** excels when:
- You operate or secure industrial/ICS environments
- You need to understand attacks targeting SCADA systems
- You want to emulate specific industrial devices (Siemens PLCs, IP cameras)
- You are researching nation-state targeting of critical infrastructure

**HoneyTrap** is ideal when:
- You need a customizable framework rather than a fixed honeypot
- You want to chain multiple services and observers together
- You need high-performance service emulation in Go
- You are building a research-grade deception platform

## Security Best Practices for Honeynet Deployment

1. **Network isolation**: Deploy honeynets on isolated VLANs or separate physical networks. Never place a honeypot on the same network segment as production systems.
2. **No sensitive data**: Ensure honeypot volumes contain no credentials, keys, or internal network information.
3. **Logging to remote storage**: Forward all honeypot logs to a separate logging server (see our [self-hosted log aggregation guide](../2026-05-07-self-hosted-log-sampling-vector-fluentbit-loki-guide/) for Vector and Fluent Bit setups).
4. **Bandwidth limits**: Use `tc` or Docker resource limits to prevent compromised honeypots from being used as attack amplifiers.
5. **Regular updates**: Keep honeypot software updated to ensure you are capturing the latest attack patterns, not known signatures.

## Integration with Threat Intelligence Platforms

Honeynet data becomes significantly more valuable when fed into threat intelligence platforms. Captured malware hashes can be correlated with known threat actors, and attack patterns can be mapped to MITRE ATT&CK techniques. For building a complete threat intelligence pipeline, consider pairing your honeypots with a [self-hosted threat intelligence platform like MISP](../misp-vs-opencti-vs-intelowl-self-hosted-threat-intelligence-platform-guide-2026/).

Additionally, if you are running honeynets alongside intrusion detection systems, the combined data provides a much richer security picture. Check our [runtime security monitoring guide](../2026-05-07-kubearmor-vs-falco-vs-tetragon-runtime-security-guide/) for Falco and Tetragon deployments that complement honeynet data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Honeynet Platforms: Dionaea vs Conpot vs HoneyTrap",
  "description": "Compare three open-source honeynet platforms for threat intelligence: Dionaea for malware capture, Conpot for ICS/SCADA, and HoneyTrap for multi-protocol deception.",
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

## FAQ

### What is the difference between a honeypot and a honeynet?

A honeypot is a single decoy system or service designed to attract attackers. A honeynet is a network of multiple honeypots connected together, providing a broader view of attacker behavior across different services and network segments. Honeynets can include firewalls, IDS sensors, and data analysis tools in addition to honeypots.

### Is it legal to run a honeypot?

In most jurisdictions, running a honeypot on your own network is legal. However, actively engaging with attackers (honeytrap-style active defense) may have legal implications depending on your jurisdiction. Always consult legal counsel before deploying honeynet systems, especially if they capture data from attackers.

### Can honeypots be detected by attackers?

Yes, experienced attackers can identify honeypots through service fingerprinting, response time analysis, and checking for unrealistic system configurations. Low-interaction honeypots (like Dionaea) are easier to detect than high-interaction ones. Using HoneyTrap's custom service emulation can make detection harder by providing more realistic responses.

### How much disk space do I need for a honeynet?

Malware-capturing honeypots like Dionaea can accumulate hundreds of megabytes per day depending on attack volume. Plan for at least 50-100 GB of storage for the first month, with log rotation enabled. Conpot and HoneyTrap use less disk space since they focus on protocol analysis rather than payload capture.

### Can I run multiple honeypots on the same host?

Yes, but you need to manage port conflicts. Each honeypot service requires unique ports. With Docker, you can use different `network_mode` settings or port mapping to run Dionaea (ports 445, 80, 21) and Conpot (ports 102, 502, 47808) on the same host. HoneyTrap's flexible port configuration makes it easy to coexist with other honeypots.

### Should I expose honeypots to the internet?

Most honeypot deployments are internet-facing to capture real-world attack traffic. However, ensure proper network isolation so that a compromised honeypot cannot pivot to internal networks. Use firewall rules to allow inbound traffic to honeypot ports while blocking all outbound connections except to your logging server.
