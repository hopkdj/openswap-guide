---
title: "Self-Hosted VoIP Monitoring & Analysis: HOMER vs sngrep vs VoIPMonitor"
date: "2026-06-15"
tags: ["voip", "sip", "monitoring", "network-analysis", "self-hosted", "open-source", "telecommunications", "packet-capture"]
draft: false
---

## Why Self-Host Your VoIP Monitoring?

Voice over IP (VoIP) systems carry mission-critical communications for businesses, call centers, and service providers. When call quality degrades, troubleshooting without proper monitoring tools is like debugging a black box — you're guessing at the root cause. Self-hosted VoIP monitoring gives you deep visibility into every SIP transaction, RTP media stream, and call quality metric.

Unlike commercial monitoring solutions that charge per channel or per call, open-source VoIP monitoring tools can be deployed at any scale without licensing costs. For service providers handling thousands of concurrent calls, this cost difference alone justifies the self-hosted approach.

If you're already running a self-hosted PBX for your organization, our [comparison of Kamailio, Asterisk, and FreeSWITCH](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/) covers the infrastructure these monitoring tools complement. For RTP media handling, see our [RTP proxy guide](../2026-05-17-rtp-proxy-rtpengine-rtpproxy-sippy-b2bua-voip-guide/).

## Comparison at a Glance

| Feature | HOMER | sngrep | VoIPMonitor |
|---------|-------|--------|-------------|
| **GitHub Stars** | 1,968+ | 1,179+ | Community |
| **Primary Language** | C/C++ | C | C++/PHP |
| **License** | AGPL-3.0 | GPL-3.0 | GPL-2.0 |
| **Docker Support** | ✅ docker-compose | N/A (terminal) | ISO/package |
| **Web Interface** | ✅ Full dashboard | ❌ Terminal TUI | ✅ Full dashboard |
| **SIP Capture** | ✅ HEP/EEP | ✅ Live + PCAP | ✅ SPAN/mirror |
| **RTP Analysis** | ✅ MOS, jitter, packet loss | ❌ SIP only | ✅ MOS, delay, loss |
| **Call Recording** | ✅ PCAP storage | ❌ No | ✅ WAV/MP3 storage |
| **Alerting** | ✅ Built-in | ❌ No | ✅ SNMP/email |
| **Database** | PostgreSQL + InfluxDB | N/A | MySQL/MariaDB |
| **API** | REST API | N/A | REST API |
| **Real-time Dashboard** | ✅ Grafana integration | ❌ Terminal only | ✅ Built-in |
| **Multi-server** | ✅ Distributed capture | ❌ Single instance | ✅ Centralized |
| **Last Update** | June 2026 | June 2026 | Active |

## HOMER: The Complete SIP Capture System

HOMER (originally "Homer SIP Capture") is the gold standard for open-source VoIP monitoring. It captures SIP signaling and RTP media using the HEP (Homer Encapsulation Protocol) and provides a comprehensive web dashboard for analyzing call flows, quality metrics, and network issues.

**Key Strengths:**
- Full SIP + RTP capture with HEP/EEP protocol
- Grafana-based dashboards with rich visualization
- Distributed capture agents (captagent/heplify) for multi-site deployment
- MOS (Mean Opinion Score) calculation for call quality
- PCAP export for deep packet inspection

**Docker Compose Deployment:**

```yaml
version: "3.8"
services:
  homer-webapp:
    image: sipcapture/homer-webapp:latest
    container_name: homer-webapp
    ports:
      - "9080:80"
    environment:
      - DB_HOST=postgres
      - DB_USER=homer_user
      - DB_PASS=homer_password
      - DB_NAME=homer_data
    depends_on:
      - postgres
    restart: unless-stopped

  homer-heplify:
    image: sipcapture/heplify:latest
    container_name: homer-heplify
    ports:
      - "9060:9060/udp"
    environment:
      - HEPLIFYSERVER_HEPADDR=0.0.0.0:9060
      - HEPLIFYSERVER_DBADDR=postgres:5432
      - HEPLIFYSERVER_DBUSER=homer_user
      - HEPLIFYSERVER_DBPASS=homer_password
      - HEPLIFYSERVER_DBNAME=homer_data
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: homer-db
    environment:
      - POSTGRES_USER=homer_user
      - POSTGRES_PASSWORD=homer_password
      - POSTGRES_DB=homer_data
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped
```

## sngrep: Terminal-Based SIP Troubleshooting

sngrep is the Swiss Army knife for SIP debugging — a terminal-based tool that displays SIP call flows in an intuitive, navigable interface. While it lacks a web dashboard, its speed and directness make it indispensable for real-time troubleshooting.

**Key Strengths:**
- Instant SIP flow visualization in terminal
- Live capture and PCAP file analysis
- Color-coded SIP messages with transaction grouping
- Call flow diagrams rendered in ASCII
- Save filtered captures for later analysis

**Installation:**

```bash
# Ubuntu/Debian
sudo apt-get install sngrep

# CentOS/RHEL
sudo yum install sngrep

# From source
git clone https://github.com/irontec/sngrep.git
cd sngrep
./bootstrap.sh
./configure
make
sudo make install

# Capture all SIP traffic on interface
sudo sngrep -d eth0

# Analyze a PCAP file
sngrep -r capture.pcap

# Filter by caller
sngrep -d eth0 -c "200 OK"
```

## VoIPMonitor: Enterprise-Grade Monitoring

VoIPMonitor is a comprehensive, open-source VoIP quality monitoring solution that combines SIP capture, RTP analysis, call recording, and alerting in a single platform. While its community edition is GPL-licensed, it's the most feature-complete option for organizations needing call quality metrics and compliance recording.

**Key Strengths:**
- Automatic MOS, R-Factor, and quality scoring per call
- Built-in call recording (WAV/MP3) for compliance
- SNMP monitoring and email alerting
- Web dashboard with historical trends
- Multi-sensor architecture for distributed deployment

**Sensor Deployment:**

```bash
# Download and install VoIPMonitor sensor
wget https://www.voipmonitor.org/download/voipmonitor-sensor.tar.gz
tar -xzf voipmonitor-sensor.tar.gz
cd voipmonitor-sensor

# Configure sensor
cp etc/voipmonitor.conf.example etc/voipmonitor.conf
# Edit voipmonitor.conf to set MySQL credentials and capture interface

# Start sensor
./voipmonitor --config etc/voipmonitor.conf
```

## Integrating with Your PBX

To capture SIP traffic for monitoring, configure your PBX or SBC to mirror traffic to the monitoring server:

**For Kamailio — send HEP packets to HOMER:**

```kamailio
loadmodule "siptrace.so"
modparam("siptrace", "trace_on", 1)
modparam("siptrace", "duplicate_uri", "sip:monitoring-server:9060")
modparam("siptrace", "hep_version", 3)

request_route {
    sip_trace();
}
```

**For FreeSWITCH — enable SIP capture:**

```xml
<configuration name="sofia.conf" description="Sofia SIP">
  <profiles>
    <profile name="external">
      <settings>
        <param name="capture-server" value="udp:monitoring-server:9060"/>
        <param name="sip-capture" value="yes"/>
      </settings>
    </profile>
  </profiles>
</configuration>
```

Alternatively, use port mirroring (SPAN) on your network switch to send a copy of all VoIP traffic to the monitoring server's capture interface.

## Choosing the Right Solution

- **Choose HOMER** if you need a full-stack SIP+RTP monitoring platform with web dashboards, API access, and distributed capture capabilities. It's the most complete open-source option.

- **Choose sngrep** for rapid, on-the-spot SIP debugging. Every VoIP engineer should have it installed. It's not a monitoring platform but a diagnostic tool.

- **Choose VoIPMonitor** if you need automatic call quality scoring, compliance call recording, SNMP-based alerting, and enterprise-grade reporting. Its community edition handles most use cases well.

For broader network monitoring that includes VoIP alongside other services, our [LibreNMS + OpenNMS SNMP monitoring guide](../2026-05-18-self-hosted-stp-rstp-network-monitoring-librenms-opennms-snmp-guide/) covers infrastructure-level monitoring.

## Performance Tuning for Large Deployments

When monitoring thousands of concurrent calls, capture performance becomes critical. HOMER's heplify agent can handle 10,000+ packets per second on modern hardware, but database write throughput is the bottleneck. Use the following optimizations:

**Database Partitioning**: HOMER's PostgreSQL database benefits from time-based table partitioning. Create daily or hourly partitions for the SIP capture tables to keep query performance fast and simplify data retention management. A 100-call-per-second deployment generates approximately 500,000 SIP messages per hour.

**Capture Buffer Tuning**: For high-throughput environments, increase the kernel capture buffer size to prevent packet loss during traffic spikes:

```bash
# Increase the network capture buffer
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.rmem_default=134217728
```

**Retention Policies**: Raw SIP/RTP capture data grows quickly. Implement a retention policy — keep detailed data for 7-14 days for troubleshooting recent issues, then aggregate into hourly/daily summaries for trend analysis. VoIPMonitor has built-in data retention configuration; for HOMER, use a cron job with PostgreSQL partition dropping.

**Storage Tiering**: Use fast SSD storage for recent capture data and migrate older data to HDD or object storage. For compliance call recording, VoIPMonitor supports configurable storage backends including NFS mounts for centralized archival.


## FAQ

### Why can't I hear audio issues just from SIP monitoring?

SIP handles call signaling (setup, teardown), but actual audio travels via RTP on separate ports. SIP monitoring shows you call flows and signaling errors, but to detect audio quality issues (jitter, packet loss, one-way audio), you need RTP analysis — which HOMER and VoIPMonitor provide, but sngrep does not.

### How much storage do I need for call recording?

A single hour of G.711 audio (uncompressed) takes about 84MB. For a call center with 100 concurrent agents working 8-hour shifts, that's approximately 67GB per day. VoIPMonitor supports codec compression and call filtering to reduce storage needs. Plan for at least 1TB of storage for a busy deployment.

### Can I monitor encrypted SIP (TLS/SRTP)?

HOMER and VoIPMonitor can capture the encrypted packets, but they cannot decrypt them without access to the private keys. For monitoring encrypted VoIP, deploy the capture agent on the PBX/SBC itself (where TLS terminates) or use a session border controller that strips encryption before mirroring traffic.

### What's the difference between HEP and port mirroring?

HEP (Homer Encapsulation Protocol) is an agent-based approach where your PBX actively sends encapsulated SIP/RTP packets to the monitoring server. Port mirroring (SPAN) is passive — your network switch copies all traffic from a port to the monitoring server. HEP is more efficient and works across network boundaries; SPAN is simpler but requires switch configuration.

### How do these tools compare to commercial solutions like Nectar or Empirix?

Commercial solutions offer polished UIs, vendor support, and pre-built integrations — but charge per session or channel. HOMER + Grafana provides comparable monitoring capabilities for zero licensing cost. For large service providers, the cost savings of open-source monitoring can be substantial.

### Can I use these for WebRTC monitoring?

HOMER can capture WebRTC traffic if your SBC or media server encapsulates it in HEP. sngrep is SIP-only. For native WebRTC monitoring with STUN/TURN analysis, you'll likely need additional tools. Consider deploying a Janus or mediasoup gateway that exports HEP for HOMER integration.

---

<section>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VoIP Monitoring & Analysis: HOMER vs sngrep vs VoIPMonitor",
  "description": "Comprehensive comparison of open-source self-hosted VoIP monitoring and analysis tools. Compare HOMER (SIP capture & dashboard), sngrep (terminal SIP debugger), and VoIPMonitor (enterprise quality monitoring) — deployment guides with Docker Compose, PBX integration, and RTP analysis.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
