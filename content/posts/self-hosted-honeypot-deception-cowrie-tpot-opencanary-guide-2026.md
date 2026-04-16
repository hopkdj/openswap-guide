---
title: "Best Self-Hosted Honeypot Solutions: Cowrie vs T-Pot vs OpenCanary 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "security", "honeypot"]
draft: false
description: "Complete guide to self-hosted honeypot and deception platforms in 2026. Compare Cowrie, T-Pot, and OpenCanary with installation guides, Docker configs, and feature comparisons."
---

If you run any internet-facing services at home or in a small business, you already know that automated scanners, credential-stuffing bots, and opportunistic attackers probe your network around the clock. Instead of simply blocking them, a **honeypot** turns that constant noise into actionable intelligence. By deploying decoy services that appear vulnerable but are actually instrumented traps, you can observe attack patterns in real time, collect malware samples, and — most importantly — generate alerts that tell you when someone is actively targeting your infrastructure.

This guide compares the three most practical self-hosted honeypot platforms available in 2026: **Cowrie**, **T-Pot**, and **OpenCanary**. Each takes a different approach, and the right choice depends on whether you want deep SSH/Telnet interaction, a multi-sensor security platform, or a lightweight distributed deception framework.

## Why Run a Self-Hosted Honeypot in 2026?

You might wonder why you would intentionally expose something that looks vulnerable on your own network. The answer comes down to visibility.

### Detect Attacks Before They Hit Production Services

A honeypot is a canary in the coal mine. Because no legitimate user should ever connect to it, **any** interaction is suspicious by definition. When an IP address hits your honeypot, you get an immediate signal that there is active reconnaissance or an ongoing attack targeting your network. This zero-false-positive property makes honeypots uniquely valuable compared to traditional IDS/IPS systems that generate thousands of alerts daily.

### Collect Real-World Threat Intelligence

Honeypots capture attacker behavior as it happens — the commands they type after gaining access, the payloads they try to execute, the malware binaries they attempt to download. This data is invaluable for understanding what's targeting your specific infrastructure and for feeding threat intelligence feeds like MISP.

### Divert Attackers Away from Real Assets

A well-configured honeypot can absorb automated scanning and brute-force attacks that would otherwise consume resources on your real services. When combined with firewall rules that auto-block honeypot-interacting IPs, you get a simple but effective defense layer.

### Zero Licensing Costs, Full Data Ownership

Commercial deception platforms can cost thousands of dollars per year. The tools covered here are completely free, open source, and run on hardware you already own. Every byte of captured data stays under your control — no third-party cloud processing, no privacy concerns.

## Cowrie: The SSH/Telnet Honeypot

**Cowrie** is a medium-interaction honeypot that emulates SSH and Telnet servers. It has been one of the most widely deployed open-source honeypots for over a decade and excels at capturing brute-force attacks and post-exploitation behavior.

### Key Features

- **Medium-interaction shell emulation**: Attackers can log in with stolen credentials and interact with a fake filesystem. Their commands are logged, and Cowrie simulates realistic outputs for common commands like `ls`, `uname`, `wget`, and `cat`.
- **Malware collection**: When attackers attempt to download malicious binaries via `wget` or `curl`, Cowrie saves the files for analysis.
- **Credential harvesting**: Every username/password combination used during login attempts is recorded, building a picture of active credential-stuffing campaigns.
- **Audit logging**: Every keystroke is logged, providing a complete session replay.
- **JSON output and MISP integration**: Logs can be forwarded to Elasticsearch, Logstash, Splunk, or MISP for analysis.

### Architecture

Cowrie runs as a Python application and supports two modes:

1. **Proxy mode**: Forwards connections to a real SSH server, logging credentials in transit. This is useful for detecting compromised accounts on your own servers.
2. **Emulation mode** (default): Presents a fully emulated environment with a fake filesystem, making attackers believe they have gained access to a real system.

### Docker Installation

```yaml
# docker-compose.yml for Cowrie
services:
  cowrie:
    image: cowrie/cowrie:latest
    container_name: cowrie-honeypot
    restart: unless-stopped
    ports:
      - "2222:2222"    # SSH honeypot
      - "2223:2223"    # Telnet honeypot
    volumes:
      - ./cowrie/cowrie.cfg:/cowrie/cowrie-git/etc/cowrie/cowrie.cfg:ro
      - ./cowrie/data:/cowrie/cowrie-git/var
      - ./cowrie/log:/cowrie/cowrie-git/log
    environment:
      - COWRIE_LOG_LEVEL=info
```

Create a minimal configuration:

```bash
mkdir -p cowrie
cat > cowrie/cowrie.cfg << 'EOF'
[honeypot]
hostname = prod-web-01
listen_endpoints = tcp:2222:interface=0.0.0.0,tcp:2223:interface=0.0.0.0

[output_jsonlog]
enabled = true
logfile = log/cowrie.json

[output_misp]
enabled = false
# Set to true and configure MISP URL + API key for threat intel sharing
EOF
```

```bash
docker compose up -d
```

Within hours, you'll start seeing SSH brute-force attempts from around the world. The `cowrie.json` log file captures every interaction in structured JSON format.

### Strengths and Limitations

| Strengths | Limitations |
|-----------|-------------|
| Excellent SSH/Telnet coverage | Only covers SSH and Telnet protocols |
| Realistic shell emulation | Sophisticated attackers may detect the fake environment |
| Built-in malware collection | No web application honeypot capability |
| Easy Docker deployment | Single-purpose — needs other tools for broader coverage |
| Active community and documentation | Manual output configuration for SIEM integration |

Cowrie is the right choice when you want a focused, lightweight SSH/Telnet honeypot that captures detailed interaction data without requiring significant resources.

## T-Pot: The Multi-Sensor Honeypot Platform

**T-Pot** is an all-in-one honeypot platform built on Debian Linux. It bundles more than 20 individual honeypot sensors into a single deployment, each emulating a different service. Think of it as a Swiss Army knife of network deception.

### Included Honeypots

T-Pot ships with a comprehensive collection of sensors, each targeting different attack vectors:

| Sensor | Protocol | What It Emulates |
|--------|----------|-----------------|
| **Cowrie** | SSH/Telnet | Shell interaction, credential harvesting |
| **Dionaea** | SMB/HTTP/FTP | Malware download and analysis |
| **Conpot** | ICS/SCADA | Industrial control systems |
| **Mailoney** | SMTP | Email server attacks |
| **Elasticpot** | Elasticsearch | Database API probing |
| **Glutton** | Multiple | Protocol-agnostic TCP honeypot |
| **Heralding** | Auth proxy | Credential capture for various services |
| **CitrixHoneypot** | Citrix | Citrix Gateway exploitation attempts |
| **Redishoneypot** | Redis | Redis server attacks |
| **Tanner** | Web | Web application vulnerability scanning |

### Security Stack

Beyond the honeypots, T-Pot includes:

- **Elasticsearch**: Log storage and search
- **Kibana**: Visualization dashboards with pre-built honeypot-specific panels
- **Filebeat/Logstash**: Log collection and processing
- **Suricata**: Network intrusion detection
- **CyberChef**: In-browser data decoding and analysis

### System Requirements

T-Pot is resource-intensive because it runs multiple services simultaneously:

- **Minimum**: 4 CPU cores, 8 GB RAM, 128 GB SSD
- **Recommended**: 8 CPU cores, 16 GB RAM, 256 GB SSD
- **Network**: Must be directly internet-facing (not behind NAT)

### Installation

T-Pot is designed to run on a dedicated Debian system. The installation script handles everything:

```bash
# Download the T-Pot installer
wget -O install.sh https://raw.githubusercontent.com/telekom-security/tpotce/master/install/install.sh

# Make it executable and run
chmod +x install.sh
sudo ./install.sh --type=user
```

The installer presents an interactive menu where you choose:

1. **T-Pot edition**: Standard (all honeypots) or Industrial (ICS-focused sensors)
2. **Network interface**: Select the interface connected to the internet
3. **Installer type**: Standard install on existing Debian or ISO-based bare-metal install

After installation, the web dashboard is available at `https://<your-ip>:64297` with Kibana dashboards showing real-time attack maps, credential statistics, and protocol breakdowns.

### Docker-Based Quick Start

For a lighter setup, T-Pot also offers a Docker Compose configuration:

```yaml
# T-Pot minimal Docker Compose (single sensor example)
services:
  tpot-base:
    image: tpot/tpot:latest
    container_name: tpot
    restart: unless-stopped
    network_mode: host
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
      - ./tpot/data:/data
      - ./tpot/config:/opt/tpot/etc
    environment:
      - TZ=UTC
    cap_add:
      - NET_ADMIN
      - SYS_PTRACE
    security_opt:
      - no-new-privileges:true
```

```bash
# Full T-Pot with all sensors uses the official compose file:
wget https://raw.githubusercontent.com/telekom-security/tpotce/master/docker-compose.yml
docker compose -f docker-compose.yml up -d
```

### Web Dashboard and Monitoring

The Kibana interface provides several pre-configured dashboards:

- **Overview**: Geographic attack map, top attacking IPs, protocol distribution
- **Cowrie**: Session replays, command frequency, downloaded malware
- **Dionaea**: Malware hash analysis, connection graphs
- **Suricata**: Network-based detection alerts correlated with honeypot events

### Strengths and Limitations

| Strengths | Limitations |
|-----------|-------------|
| 20+ honeypot sensors in one package | Resource-heavy — needs a dedicated machine |
| Pre-built Kibana dashboards | Complex to customize individual sensors |
| Includes Suricata IDS | Requires direct internet exposure |
| Active development by Deutsche Telekom | Overwhelming amount of data for small deployments |
| Covers SSH, HTTP, SMB, ICS, SMTP, and more | Not suitable for virtual machines with limited resources |

T-Pot is ideal when you want comprehensive network-wide visibility and have the hardware to support it. It's the closest thing to a commercial deception platform in the open-source world.

## OpenCanary: The Lightweight Distributed Honeypot

**OpenCanary** by Thinkst takes a fundamentally different approach. Instead of running one monolithic honeypot, it deploys lightweight "canaries" — small, protocol-specific monitors that you scatter across your network. Each canary watches for activity on a single protocol and sends alerts when triggered.

### Key Features

- **Modular design**: Each protocol runs as an independent module. Enable only what you need.
- **Distributed deployment**: Run instances on multiple machines, Raspberry Pis, or containers.
- **Alert flexibility**: Notifications via email, Slack, webhooks, syslog, or SNMP traps.
- **Low resource usage**: Each instance uses minimal CPU and memory — a Raspberry Pi Zero can run several canaries.
- **Custom banners and responses**: Configure believable service banners that match your environment.

### Supported Protocols

| Module | Port | Detects |
|--------|------|---------|
| **SSH** | 22 | Brute-force login attempts |
| **HTTP** | 80 | Web scanner probing, admin panel access |
| **FTP** | 21 | Anonymous login attempts, credential stuffing |
| **SMB** | 445 | Windows share enumeration, WannaCry-style scanning |
| **RDP** | 3389 | Remote Desktop brute-force |
| **SNMP** | 161 | SNMP community string guessing |
| **NTP** | 123 | NTP amplification scanning |
| **MySQL** | 3306 | Database credential probing |
| **Redis** | 6379 | Redis unauthorized access attempts |
| **TCP Banner** | Any | Custom TCP service emulation |

### Installation and Configuration

```bash
# Install OpenCanary
pip install opencanary

# Generate default configuration
opencanaryd --copyconfig

# The config is saved to ~/.opencanary.conf
# Edit it to enable the modules you want:
```

```json
{
  "device.node_id": "canary-office-server-01",
  "ssh.enabled": true,
  "ssh.port": 22,
  "ftp.enabled": true,
  "ftp.port": 21,
  "ftp.banner": "FTP server ready",
  "http.enabled": true,
  "http.port": 80,
  "http.skin": "nasLogin",
  "smb.enabled": true,
  "smb.filelog.enabled": true,
  "mysql.enabled": true,
  "mysql.port": 3306,
  "redis.enabled": true,
  "redis.port": 6379,
  "logger": {
    "class": "PyLogger",
    "kwargs": {
      "formatters": {
        "plain": {
          "format": "%(message)s"
        }
      },
      "handlers": {
        "console": {
          "class": "logging.StreamHandler",
          "stream": "ext://sys.stdout"
        },
        "slack": {
          "class": "opencanary.logger.SlackHandler",
          "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        },
        "email": {
          "class": "logging.handlers.SMTPHandler",
          "mailhost": ["smtp.example.com", 587],
          "fromaddr": "canary@example.com",
          "toaddrs": ["admin@example.com"],
          "subject": "OpenCanary Alert",
          "credentials": ["user", "password"]
        }
      }
    }
  }
}
```

### Docker Deployment

```yaml
# docker-compose.yml for OpenCanary
services:
  opencanary:
    image: opencanary/opencanary:latest
    container_name: opencanary
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./opencanary.conf:/root/.opencanary.conf:ro
      - ./opencanary-logs:/var/log/opencanary
    environment:
      - OC_NODE_ID=canary-docker-01
```

```bash
docker compose up -d
```

For a multi-canary setup, deploy the same container on different machines with different `OC_NODE_ID` values. Each instance sends centralized alerts, giving you network-wide coverage from a single Slack channel or email inbox.

### Strengths and Limitations

| Strengths | Limitations |
|-----------|-------------|
| Extremely lightweight — runs on Raspberry Pi | Low interaction — doesn't capture detailed attacker behavior |
| Easy distributed deployment | No malware collection capability |
| Flexible alerting (Slack, email, webhook, syslog) | Less detailed session data than Cowrie |
| Customizable service banners | Requires manual setup on each target host |
| Low false-positive rate | No built-in analytics dashboard |

OpenCanary is the best fit when you want broad, lightweight coverage across many machines and prefer immediate alerts over deep forensic data.

## Feature Comparison at a Glance

| Feature | Cowrie | T-Pot | OpenCanary |
|---------|--------|-------|------------|
| **Interaction Level** | Medium (shell emulation) | High (real services) | Low (banner/response) |
| **Protocols Covered** | SSH, Telnet | 20+ (SSH, HTTP, SMB, ICS, SMTP, etc.) | 10+ (modular) |
| **Malware Collection** | Yes | Yes (via Dionaea) | No |
| **Credential Harvesting** | Yes | Yes (via multiple sensors) | Yes (basic) |
| **Dashboard** | No (needs external ELK) | Yes (Kibana included) | No (log/alerts only) |
| **Docker Support** | Excellent | Good (official compose) | Good |
| **Min. RAM** | 512 MB | 8 GB | 256 MB |
| **Installation Time** | 5 minutes | 30–60 minutes | 10 minutes |
| **Alert Integration** | JSON/MISP/ELK | Kibana dashboards | Slack/email/webhook/syslog |
| **Best Use Case** | Focused SSH/Telnet monitoring | Comprehensive network deception | Lightweight distributed canaries |
| **Development Status** | Active | Active | Active |

## Recommended Deployment Strategies

### The Layered Approach

The most effective setup combines all three tools at different network layers:

1. **Perimeter layer**: Deploy T-Pot on a dedicated internet-facing server to catch broad-spectrum scanning and collect malware samples.
2. **Service layer**: Run Cowrie on port 2222 alongside your real SSH server (on port 22) to catch SSH-specific attacks targeting your infrastructure.
3. **Internal layer**: Place OpenCanary instances on internal network segments — a canary on each subnet detects lateral movement if an attacker breaches your perimeter.

### Quick-Start Single Machine

If you have limited hardware and want the most coverage from a single box:

```bash
# 1. Install T-Pot for broad coverage (needs 8+ GB RAM)
sudo ./install.sh --type=user

# 2. If RAM is limited, use Cowrie + OpenCanary instead
docker compose up -d  # Cowrie on ports 2222/2223

# Install OpenCanary for additional protocol coverage
pip install opencanary
opencanaryd --start
```

### Auto-Blocking with Fail2ban

Regardless of which honeypot you choose, integrate it with fail2ban to automatically ban attacking IPs:

```bash
# Cowrie fail2ban filter
cat > /etc/fail2ban/filter.d/cowrie.conf << 'EOF'
[Definition]
failregex = ^.*"src_ip":"<HOST>".*"eventid":"cowrie.login.failed".*$
            ^.*"src_ip":"<HOST>".*"eventid":"cowrie.session.connect".*$
EOF

# Jail configuration
cat >> /etc/fail2ban/jail.local << 'EOF'
[cowrie]
enabled = true
filter = cowrie
logpath = /var/log/cowrie/cowrie.json
maxretry = 1
bantime = 86400
findtime = 3600
action = iptables-allports[name=cowrie]
EOF

sudo systemctl restart fail2ban
```

With `maxretry = 1`, any IP that touches your honeypot gets banned for 24 hours — a simple but effective automated defense.

## Analyzing Your Honeypot Data

The value of a honeypot is proportional to what you do with the data. Here are practical analysis approaches:

**Credential Analysis**: Export login attempts and check for patterns. Common findings include:
- Default credentials (`admin/admin`, `root/root`)
- Credential lists from known breaches
- Targeted username patterns that reveal attacker reconnaissance

**Geographic Mapping**: T-Pot's Kibana dashboards provide built-in geo-IP mapping. For Cowrie, pipe JSON logs to a simple script:

```python
import json
from collections import Counter

attacks = Counter()
with open('/var/log/cowrie/cowrie.json') as f:
    for line in f:
        event = json.loads(line)
        if 'src_ip' in event:
            attacks[event['src_ip']] += 1

for ip, count in attacks.most_common(20):
    print(f"{ip}: {count} attempts")
```

**Malware Analysis**: Files captured by Cowrie or Dionaea can be submitted to VirusTotal or analyzed locally with `file`, `strings`, and `yara` rules to identify threat families.

## Final Recommendation

- **Choose Cowrie** if you want a focused, easy-to-deploy SSH/Telnet honeypot with detailed session logging and malware collection. It's the best starting point for most self-hosters.
- **Choose T-Pot** if you have a dedicated machine, want comprehensive multi-protocol coverage, and value the built-in Kibana analytics. It's the most powerful option but requires significant resources.
- **Choose OpenCanary** if you want lightweight, distributed coverage across many machines with immediate alert notifications. It's ideal for detecting lateral movement on internal networks.

For the best results, deploy them together in layers — each tool covers different blind spots, and the combined intelligence gives you a far more complete picture of who's targeting your infrastructure and how.
