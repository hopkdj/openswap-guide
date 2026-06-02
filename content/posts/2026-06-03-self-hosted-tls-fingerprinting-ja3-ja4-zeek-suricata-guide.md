---
title: "Self-Hosted TLS Fingerprinting for Network Security: JA3/JA4 vs Zeek SSL vs Suricata TLS Analysis"
date: "2026-06-03"
tags: ["tls", "ssl", "fingerprinting", "network-security", "zeek", "suricata", "traffic-analysis"]
draft: false
---

## Introduction

TLS fingerprinting is a passive network monitoring technique that identifies client applications and malware by analyzing the unique characteristics of their TLS handshakes. Every TLS client — whether it is Chrome, a Python script, or a malware command-and-control beacon — produces a distinctive fingerprint based on its supported cipher suites, TLS extensions, elliptic curves, and signature algorithms. By capturing and analyzing these fingerprints, security teams can detect unauthorized applications, identify malware families, and enforce network policy without decrypting traffic.

This guide compares three approaches to self-hosted TLS fingerprinting: **JA3/JA4**, the industry-standard fingerprinting libraries from Salesforce and FoxIO; **Zeek** with its built-in SSL analysis and JA3 plugin; and **Suricata** with TLS fingerprinting and signature-based detection. Each tool serves a different operational niche, from lightweight Python-based fingerprint generation to full-scale network security monitoring platforms.

## JA3/JA4 Fingerprinting Libraries

JA3 (created by Salesforce) and JA4+ (created by FoxIO) are the de facto standards for TLS client fingerprinting. Both operate on the same principle: they compute a hash of the TLS Client Hello message parameters (cipher suites, extensions, elliptic curves, and elliptic curve point formats), producing a compact fingerprint string like `6734f37431670b3ab4292b8f60f29984`.

### How JA3 Works

JA3 concatenates five fields from the Client Hello into a string and computes its MD5 hash:
1. TLS version
2. Accepted cipher suites (in order)
3. List of extensions (in order)
4. Supported elliptic curves
5. Elliptic curve point formats

The resulting 32-character MD5 hash is the JA3 fingerprint.

### How JA4+ Differs

JA4+ improves on JA3 in several ways:
- **SHA-256** instead of MD5 for collision resistance
- **Multi-protocol support** — JA4 (TLS client), JA4S (TLS server), JA4H (HTTP), JA4X (X.509), JA4SSH (SSH)
- **Human-readable** fingerprint format instead of raw hashes
- **Better GREASE handling** — correctly ignores GREASE values that Chrome inserts
- **QUIC support** — fingerprints for QUIC/HTTP3 handshakes

### Python Installation and Usage

```bash
# Install JA3
pip install ja3

# Install JA4+
pip install ja4
```

JA3 Python example:
```python
import ja3

# Fingerprint a TLS Client Hello packet
with open('client_hello.bin', 'rb') as f:
    data = f.read()
fingerprint = ja3.calc_ja3(data)
print(f"JA3: {fingerprint}")
# Output: JA3: 6734f37431670b3ab4292b8f60f29984
```

JA4+ Python example:
```python
from ja4 import JA4

ja4 = JA4()
# Fingerprint from raw bytes
fp = ja4.fingerprint(client_hello_bytes)
print(f"JA4: {fp}")
# Output: JA4: t13d1516h2_8daaf6152771_02713d6af862
```

### Docker Compose for Automated Fingerprinting

```yaml
version: "3.8"
services:
  ja4-collector:
    image: python:3.12-slim
    container_name: ja4-collector
    network_mode: host
    volumes:
      - ./ja4/scripts:/app
      - ./ja4/output:/output
    command: |
      bash -c "pip install ja4 scapy && python /app/collector.py"
    restart: unless-stopped
```

### Pros and Cons

- ✅ Lightweight — single Python library, minimal dependencies
- ✅ Industry standard — JA3/JA4 fingerprints are widely recognized
- ✅ Easy to integrate with existing Python tooling
- ❌ Library only — requires custom scripting for continuous monitoring
- ❌ No built-in UI, database, or alerting
- ❌ MD5-based JA3 has known hash collisions (fixed in JA4+)

## Zeek SSL Analysis

Zeek (formerly Bro) is a powerful network security monitoring platform that passively analyzes network traffic and generates comprehensive logs. Its built-in SSL/TLS analyzer extracts detailed information from every TLS handshake, including JA3 fingerprints when the JA3 plugin is enabled.

### Key Features
- **Built-in SSL analyzer** — extracts certificates, cipher suites, SNI, TLS versions
- **JA3 plugin** — computes JA3 and JA3S fingerprints for every connection
- **Connection logging** — `ssl.log`, `conn.log`, `x509.log` for comprehensive analysis
- **Scripting language** — Zeek scripts for custom detection logic
- **Integration ecosystem** — feeds into Elasticsearch, Splunk, Kafka

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  zeek:
    image: zeekurity/zeek:7.0
    container_name: zeek-ssl
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./zeek/logs:/usr/local/zeek/logs
      - ./zeek/scripts:/usr/local/zeek/share/zeek/site/scripts
      - ./zeek/local.zeek:/usr/local/zeek/share/zeek/site/local.zeek
    command: zeek -i eth0 local
    restart: unless-stopped
```

### Zeek SSL Analysis Configuration

In `local.zeek`, enable SSL logging and JA3 fingerprinting:

```
# Load SSL/TLS analysis
@load protocols/ssl/validate-certs
@load protocols/ssl/log-hostcerts-only
@load protocols/ssl/ja3

# Log all SSL connections
redef SSL::log_every_certificate = T;

# Enable JA3 fingerprinting
redef SSL::ja3_fingerprints = T;
```

Example query to find unique JA3 fingerprints in Zeek logs:
```bash
# Extract unique JA3 fingerprints and associated server names
cat ssl.log | zeek-cut ja3 server_name | sort | uniq -c | sort -rn | head -20
```

Example output showing the most common TLS fingerprints on your network:
```
    142 6734f37431670b3ab4292b8f60f29984 api.github.com
     89 51c64b3f1abe71729a07352e9477805a www.google.com
     56 cd08e31494f9531f7b4e6e72b9d3c433 login.microsoftonline.com
```

### Detection Script Example

Zeek can alert on suspicious TLS fingerprints:

```
# detect_malware_ja3.zeek
global malware_ja3: set[string] = {
    "e35df3e00ca4ef31d42b34bebaa2cf92",  # TrickBot
    "51c64b3f1abe71729a07352e9477805a",  # Emotet
};

event ssl_established(c: connection) {
    if (c$ssl?$ja3 && c$ssl$ja3 in malware_ja3) {
        NOTICE([$note=Weird::Activity,
                $msg=fmt("Malware JA3 fingerprint detected: %s from %s", 
                          c$ssl$ja3, c$id$orig_h),
                $conn=c]);
    }
}
```

### Pros and Cons

- ✅ Full network security monitoring platform — not just fingerprinting
- ✅ Comprehensive SSL/TLS logging with certificates, SNI, cipher details
- ✅ Powerful scripting language for custom detection rules
- ✅ Large community with shared threat intelligence scripts
- ❌ Heavier than JA3/JA4 library alone — requires continuous packet capture
- ❌ Steeper learning curve — Zeek scripting language has its own syntax
- ❌ No built-in web dashboard — needs external tools for visualization

## Suricata TLS Fingerprinting

Suricata is a high-performance Network Intrusion Detection System (NIDS) that includes TLS fingerprinting as part of its deep packet inspection engine. Suricata can extract TLS metadata, compute JA3 fingerprints, and trigger alerts based on TLS characteristics using its signature language.

### Key Features
- **TLS logging** — extracts SNI, cipher suites, TLS version, certificate details
- **JA3 fingerprinting** — built-in JA3 computation in the TLS parser
- **Signature-based detection** — write rules that trigger on specific TLS fingerprints
- **High performance** — multi-threaded, GPU-accelerated, runs at line rate
- **EVE JSON output** — structured JSON logs for ingestion into SIEM platforms

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  suricata:
    image: jasonish/suricata:7.0
    container_name: suricata-tls
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - SYS_NICE
    volumes:
      - ./suricata/logs:/var/log/suricata
      - ./suricata/config:/etc/suricata
      - ./suricata/rules:/var/lib/suricata/rules
    command: suricata -i eth0 -c /etc/suricata/suricata.yaml
    restart: unless-stopped
```

### Suricata TLS Configuration

In `suricata.yaml`, enable TLS logging with JA3:

```yaml
outputs:
  - eve-log:
      enabled: yes
      types:
        - tls:
            extended: yes
            ja3-fingerprints: yes
```

### Signature Rules for TLS Fingerprinting

Suricata signatures can match on TLS fingerprints and certificate details:

```
# Alert on known malicious JA3 fingerprint
alert tls any any -> any any (
    msg:"MALWARE TrickBot TLS Fingerprint Detected";
    tls.ja3_hash; content:"e35df3e00ca4ef31d42b34bebaa2cf92";
    classtype:trojan-activity;
    sid:1000001;
    rev:1;
)

# Alert on self-signed certificates to internal IPs
alert tls any any -> any any (
    msg:"SELF-SIGNED Certificate to Suspicious Host";
    tls.subject; content:"CN=localhost"; nocase;
    tls.issuerdn; content:"CN=localhost"; nocase;
    classtype:policy-violation;
    sid:1000002;
    rev:1;
)

# Detect expired certificates
alert tls any any -> any any (
    msg:"EXPIRED TLS Certificate Detected";
    tls_cert_expired;
    classtype:bad-unknown;
    sid:1000003;
    rev:1;
)
```

### Pros and Cons

- ✅ High-performance packet processing with multi-threading
- ✅ Signature language for precise detection rules
- ✅ Unified IDS/IPS — TLS fingerprinting alongside broader threat detection
- ✅ EVE JSON output for SIEM integration (Elasticsearch, Splunk)
- ❌ Signature syntax has a learning curve
- ❌ Rules require ongoing maintenance and tuning
- ❌ False positives if rules are too broad

## Comparison Table

| Feature | JA3/JA4 Libraries | Zeek SSL Analysis | Suricata TLS |
|---------|-------------------|-------------------|--------------|
| **Stars** | 3,102★ / 1,958★ | 7,200★+ | 6,300★+ |
| **Type** | Python libraries | Network monitoring platform | IDS/IPS platform |
| **Fingerprint Method** | JA3 (MD5) / JA4+ (SHA-256) | JA3 (via plugin) | JA3 (built-in) |
| **Multi-Protocol** | TLS only / TLS+HTTP+SSH+QUIC | TLS + many other protocols | TLS + many other protocols |
| **Web Dashboard** | None | External (ELK/Splunk) | External (EVE JSON) |
| **Detection Engine** | Manual (Python scripts) | Zeek scripts | Signature rules |
| **Performance** | N/A (library) | Good (single-threaded) | Excellent (multi-threaded) |
| **Setup Complexity** | Low (pip install) | Medium | Medium |
| **Best For** | Custom tooling, research | Security monitoring, forensics | Real-time IDS/IPS detection |
| **Primary Language** | Python | C++ / Zeek script | C |

## Why Self-Host Your TLS Fingerprinting?

TLS fingerprinting provides visibility into encrypted traffic without breaking encryption — a capability that becomes increasingly critical as TLS 1.3 adoption approaches 95% of web traffic. By analyzing Client Hello fingerprints, security teams can detect unauthorized applications on the corporate network, identify malware command-and-control beacons using known malicious JA3 signatures, and enforce acceptable-use policies without deploying TLS interception proxies.

For organizations that already operate self-hosted network monitoring infrastructure, adding TLS fingerprinting is straightforward. Zeek and Suricata can be deployed on an existing monitoring server or virtual machine, passively tapping a mirror port on the network switch. The TLS analysis happens alongside other protocol analysis with minimal additional overhead. For broader network traffic analysis capabilities, see our [network traffic analysis guide](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/).

Compliance is another driver. Regulations like PCI DSS require visibility into encrypted traffic flows, and TLS fingerprinting provides that visibility without the privacy and performance concerns of full TLS decryption. By maintaining an inventory of TLS fingerprints on your network, you can demonstrate which applications are communicating, with what TLS parameters, and whether any deprecated cipher suites or TLS versions remain in use. For managing TLS certificates and PKI infrastructure, see our [certificate lifecycle management guide](../2026-06-01-openssl-certificate-management-cli-openssl-gnutls-cfssl-mkcert-guide/).
For securing your TLS termination endpoints, see our [TLS termination proxy comparison guide](../self-hosted-tls-termination-proxy-traefik-caddy-haproxy-guide-2026/).

## FAQ

### Can JA3/JA4 fingerprints be spoofed?

Yes. A sophisticated attacker can modify their TLS client to mimic a known browser fingerprint. However, this is non-trivial because the fingerprint depends on the TLS library's internal behavior. Changing the cipher suite order or adding specific extensions requires modifying the TLS stack, which most commodity malware does not do. JA4+ adds additional entropy from the TLS state machine and HTTP headers, making spoofing harder. In practice, JA3/JA4 is a strong indicator, not a definitive identification mechanism — use it as one signal among many in your detection pipeline.

### Does TLS 1.3 change fingerprinting?

TLS 1.3 simplifies the handshake significantly, which actually makes fingerprinting more reliable. With fewer variable fields in the Client Hello, the remaining fields (supported groups, signature algorithms, key share groups) become even more distinctive between different clients. JA4+ explicitly targets TLS 1.3 with its `t13` prefix format. Both JA3 and JA4+ work correctly with TLS 1.3.

### What is the difference between JA3 and JA3S?

JA3 fingerprints the TLS *client* (the initiator of the connection), while JA3S fingerprints the TLS *server* (based on the Server Hello message). Server fingerprints are less distinctive than client fingerprints because most servers respond with a single cipher suite and fewer extensions. However, JA3S can identify specific server software versions (e.g., Apache httpd 2.4.57 vs nginx 1.25.3) when their TLS configurations differ.

### How do I build a database of known JA3 fingerprints?

Several community-maintained resources exist:
- **JA3 Fingerprints** (https://github.com/salesforce/ja3) — Salesforce's reference implementation includes sample fingerprints
- **SSL Blacklist** (https://sslbl.abuse.ch/) — Abuse.ch maintains JA3 fingerprints for malware
- **JA4+ Database** (https://github.com/FoxIO-LLC/ja4) — FoxIO's repository includes common fingerprints

For your own environment, run Zeek or Suricata for a week and collect all unique JA3 hashes with their associated SNI values. This gives you a baseline of normal TLS fingerprints for your network, making anomalies stand out.

### Can I use TLS fingerprinting without deploying a full NIDS?

Yes. The JA3/JA4 Python libraries can be used with TShark or tcpdump to fingerprint traffic from pcap files. A lightweight approach is:

```bash
# Capture traffic for 60 seconds
tcpdump -i eth0 -w capture.pcap -G 60 -W 1 'tcp port 443'

# Extract Client Hello packets and compute fingerprints
tshark -r capture.pcap -Y "tls.handshake.type == 1" -T fields   -e tls.handshake.ja3 | sort | uniq -c | sort -rn
```

This requires no persistent daemon — just periodic captures and analysis.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on anything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've profited by predicting tech-related event trajectories. Sign up with my invite link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TLS Fingerprinting for Network Security: JA3/JA4 vs Zeek SSL vs Suricata TLS Analysis",
  "description": "Comprehensive comparison of JA3/JA4 fingerprinting libraries, Zeek SSL analysis, and Suricata TLS detection for self-hosted network security monitoring — Docker Compose configs, detection rules, and operational guidance.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
