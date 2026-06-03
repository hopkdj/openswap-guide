---
title: "Self-Hosted Syslog Encryption: rsyslog TLS vs syslog-ng TLS vs RELP"
date: "2026-06-03"
tags: ["syslog", "logging", "tls", "security", "encryption", "self-hosted", "infrastructure", "rsyslog", "syslog-ng"]
draft: false
---

## Introduction

Syslog has been the backbone of Linux system logging for decades, but the default UDP transport sends log messages in plaintext over the network. In regulated environments, security-sensitive deployments, or any scenario where logs traverse untrusted networks, encrypting syslog traffic is not optional — it is a compliance requirement. PCI DSS, HIPAA, SOC 2, and GDPR all require protection of log data in transit, and unencrypted syslog is a common audit finding.

This guide compares three approaches to encrypted syslog transport: **rsyslog with TLS**, using the `imtcp`/`gtls` module stack; **syslog-ng with TLS**, leveraging its flexible network driver; and **RELP over TLS**, a reliable delivery protocol that adds application-layer acknowledgments to prevent message loss. We provide production-ready configuration examples and a decision framework for choosing the right approach.

## Why Encrypt Syslog Traffic?

Syslog messages contain sensitive information. Authentication events record usernames and source IPs. Application logs may contain session tokens, PII, or business logic details. Firewall logs document network access patterns. When these logs flow in plaintext between servers, a network tap or compromised switch exposes all of this data.

Encrypted syslog transport addresses three security objectives:

**Confidentiality**. TLS encryption ensures that log content cannot be read by network observers. Even if packets are captured, the payload remains opaque.

**Integrity**. TLS provides tamper detection. An attacker cannot modify log messages in transit without detection, which is important when logs serve as forensic evidence.

**Authentication**. Mutual TLS (mTLS) verifies both the client and server identity, preventing log injection from unauthorized sources.

| Feature | rsyslog TLS | syslog-ng TLS | RELP over TLS |
|---------|------------|---------------|---------------|
| TLS Library | GnuTLS | OpenSSL | OpenSSL (via rsyslog) |
| Mutual TLS | Yes | Yes | Yes |
| Certificate Revocation | CRL support | CRL + OCSP | CRL support |
| Protocol Framing | Octet-counting (RFC 6587) | Octet-counting + legacy | Octet-counting (RELP) |
| Application ACKs | No (TCP only) | No (TCP only) | Yes (RELP protocol) |
| Message Loss Protection | TCP guarantees | TCP guarantees | RELP ACKs + retransmit |
| Queue/Disk Buffer | Yes (action queues) | Yes (disk-buffer) | Yes (action queues) |
| Performance | 50K-100K msg/sec | 45K-90K msg/sec | 30K-60K msg/sec |
| GitHub Stars | 2,292 | 2,345 | N/A (rsyslog module) |
| Configuration Complexity | Moderate | Moderate | Low |

## rsyslog with TLS: The Industry Standard

rsyslog is the default syslog daemon on most Linux distributions. Its TLS support uses GnuTLS and the Network Stream driver, providing encrypted transport for both TCP and RELP connections.

**Docker Compose deployment (rsyslog TLS server):**

```yaml
version: '3.8'
services:
  rsyslog-tls:
    image: rsyslog/rsyslog:latest
    container_name: rsyslog-tls-server
    ports:
      - "6514:6514"
    volumes:
      - ./rsyslog-tls.conf:/etc/rsyslog.conf:ro
      - ./certs:/etc/rsyslog/certs:ro
      - ./logs:/var/log/remote
    restart: unless-stopped
```

**rsyslog TLS server configuration:**

```
module(load="imtcp"
       StreamDriver.Name="gtls"
       StreamDriver.Mode="1"
       StreamDriver.AuthMode="x509/name"
       PermittedPeer=["*.example.com"])

input(type="imtcp" port="6514")

# Certificate configuration
global(
    DefaultNetstreamDriver="gtls"
    DefaultNetstreamDriverCAFile="/etc/rsyslog/certs/ca.pem"
    DefaultNetstreamDriverCertFile="/etc/rsyslog/certs/server-cert.pem"
    DefaultNetstreamDriverKeyFile="/etc/rsyslog/certs/server-key.pem"
)

# Store encrypted logs
template(name="RemoteLogs" type="string"
         string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")
*.* ?RemoteLogs
```

**rsyslog TLS client configuration:**

```
module(load="omfwd")
action(type="omfwd"
       target="log-server.example.com"
       port="6514"
       protocol="tcp"
       StreamDriver="gtls"
       StreamDriverMode="1"
       StreamDriverAuthMode="x509/name"
       StreamDriverPermittedPeers="log-server.example.com")

global(
    DefaultNetstreamDriverCAFile="/etc/rsyslog/certs/ca.pem"
    DefaultNetstreamDriverCertFile="/etc/rsyslog/certs/client-cert.pem"
    DefaultNetstreamDriverKeyFile="/etc/rsyslog/certs/client-key.pem"
)
```

**Best for**: Teams running rsyslog on standard Linux distributions. The GnuTLS integration is well-tested and the action queue system provides built-in disk buffering for network outages.

## syslog-ng with TLS: Flexible and Powerful

syslog-ng is the feature-rich alternative to rsyslog, known for its flexible pipeline architecture and powerful message parsing. Its TLS support uses OpenSSL and integrates cleanly with the network source/destination drivers.

**Docker Compose deployment (syslog-ng TLS server):**

```yaml
version: '3.8'
services:
  syslog-ng-tls:
    image: balabit/syslog-ng:latest
    container_name: syslog-ng-tls-server
    ports:
      - "6514:6514"
    volumes:
      - ./syslog-ng-tls.conf:/etc/syslog-ng/syslog-ng.conf:ro
      - ./certs:/etc/syslog-ng/certs:ro
      - ./logs:/var/log/remote
    restart: unless-stopped
```

**syslog-ng TLS server configuration:**

```
@version: 4.7
@include "scl.conf"

source s_encrypted {
    network(
        ip(0.0.0.0)
        port(6514)
        transport("tls")
        tls(
            key-file("/etc/syslog-ng/certs/server-key.pem")
            cert-file("/etc/syslog-ng/certs/server-cert.pem")
            ca-file("/etc/syslog-ng/certs/ca.pem")
            peer-verify(required-trusted)
        )
    );
};

destination d_remote {
    file(
        "/var/log/remote/${HOST}/${PROGRAM}.log"
        create-dirs(yes)
    );
};

log {
    source(s_encrypted);
    destination(d_remote);
};
```

**syslog-ng TLS client configuration:**

```
destination d_tls_server {
    network(
        "log-server.example.com"
        port(6514)
        transport("tls")
        tls(
            ca-file("/etc/syslog-ng/certs/ca.pem")
            cert-file("/etc/syslog-ng/certs/client-cert.pem")
            key-file("/etc/syslog-ng/certs/client-key.pem")
        )
        disk-buffer(
            mem-buf-size(16384)
            disk-buf-size(2147483648)
            reliable(yes)
        )
    );
};
```

**Best for**: Environments that need advanced message parsing and filtering before transmission. syslog-ng's pipeline architecture allows you to enrich, transform, and route messages before sending them over encrypted channels.

## RELP over TLS: Guaranteed Delivery

RELP (Reliable Event Logging Protocol) adds application-layer acknowledgments on top of TCP. While TCP guarantees packet delivery, it does not guarantee that the application actually processed the message — a server crash between TCP receipt and disk write can lose messages. RELP solves this by requiring explicit acknowledgment from the receiver for each message.

**rsyslog RELP server with TLS:**

```
module(load="imrelp"
       ruleset="relp")

input(type="imrelp" port="2514"
      tls="on"
      tls.caCert="/etc/rsyslog/certs/ca.pem"
      tls.myCert="/etc/rsyslog/certs/server-cert.pem"
      tls.myPrivKey="/etc/rsyslog/certs/server-key.pem"
      tls.authMode="name"
      tls.permittedPeer=["*.example.com"])
```

**rsyslog RELP client:**

```
module(load="omrelp")
action(type="omrelp"
       target="log-server.example.com"
       port="2514"
       tls="on"
       tls.caCert="/etc/rsyslog/certs/ca.pem"
       tls.myCert="/etc/rsyslog/certs/client-cert.pem"
       tls.myPrivKey="/etc/rsyslog/certs/client-key.pem"
       tls.authMode="name"
       tls.permittedPeer="log-server.example.com"
       action.resumeRetryCount="-1"
       queue.type="LinkedList"
       queue.filename="relp_queue"
       queue.maxDiskSpace="2g"
       queue.saveOnShutdown="on")
```

**Best for**: Environments where log completeness is mission-critical — financial transaction logging, security audit trails, and compliance-mandated log retention. The application-layer acknowledgment guarantees that every log message is received and acknowledged before the sender discards it.

## Certificate Management for Syslog TLS

Generating TLS certificates for syslog encryption follows standard PKI practices. Here is a minimal certificate generation workflow:

```bash
# Generate CA key and certificate
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca.pem   -subj "/CN=Syslog CA"

# Generate server certificate
openssl genrsa -out server-key.pem 2048
openssl req -new -key server-key.pem -out server.csr   -subj "/CN=log-server.example.com"
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca-key.pem   -CAcreateserial -out server-cert.pem -days 365

# Generate client certificate
openssl genrsa -out client-key.pem 2048
openssl req -new -key client-key.pem -out client.csr   -subj "/CN=app-server.example.com"
openssl x509 -req -in client.csr -CA ca.pem -CAkey ca-key.pem   -CAcreateserial -out client-cert.pem -days 365
```

## Why Self-Host Your Syslog Encryption

Managed logging services charge per gigabyte of ingestion, and encrypted transport is often a premium feature. Self-hosting syslog encryption keeps log data entirely within your infrastructure — no third party ever sees your server authentication events, application logs, or network telemetry. For organizations subject to data residency requirements, self-hosted encrypted syslog ensures logs never leave your jurisdiction.

The operational maturity gained from managing your own log transport encryption extends beyond compliance. Understanding certificate rotation, mTLS debugging, and protocol-level observability for your logging infrastructure transfers directly to other TLS-dependent systems — database replication, message queues, and API gateways.

For comprehensive log management infrastructure, see our [self-hosted log management platform comparison](../self-hosted-log-management-loki-graylog-opensearch/). If you need to ship logs from containers and applications securely, our [log shipping tools guide](../self-hosted-log-shipping-vector-fluentbit-logstash-guide-2026/) covers the major collectors. For security monitoring, our [SIEM comparison guide](../self-hosted-siem-wazuh-security-onion-elastic-guide/) covers integrated log analysis and threat detection.

## FAQ

### Does TLS significantly impact syslog throughput?

Yes, but the impact is manageable. TLS encryption adds approximately 20-30% CPU overhead compared to plain TCP. On modern hardware, rsyslog with TLS can handle 50,000-100,000 messages per second. If throughput is critical, consider using TLS offload at a load balancer (HAProxy or Nginx stream proxy) to terminate TLS before forwarding plaintext to syslog servers on a trusted network segment.

### Should I use TLS or a VPN for syslog encryption?

Both approaches are valid, but TLS is generally preferred for syslog specifically. TLS provides endpoint authentication (you know exactly which server sent the log), operates at the application layer with protocol awareness, and integrates directly with syslog daemon configuration. A VPN (WireGuard, IPsec) encrypts everything at the network layer and protects all traffic between hosts — useful if you need to protect multiple services, but it does not provide per-application authentication. Many deployments use both: WireGuard for the network tunnel and TLS for application-level authentication.

### How do I handle certificate rotation without log loss?

Both rsyslog and syslog-ng support certificate reload without service restart. In rsyslog, send a HUP signal (`kill -HUP $(cat /var/run/rsyslogd.pid)`) and the daemon reloads its configuration including new certificates while preserving in-flight connections. syslog-ng supports `syslog-ng-ctl reload`. For zero-downtime rotation, deploy the new certificate alongside the old one for a transition period, reload the daemon, then remove the old certificate and reload again.

### What happens when the TLS connection drops?

rsyslog with action queues buffers messages to disk when the connection fails and retries indefinitely (configured via `action.resumeRetryCount="-1"`). syslog-ng uses `disk-buffer` with the `reliable(yes)` option. RELP adds an additional layer — the sender knows exactly which messages the receiver acknowledged and only resends unacknowledged messages after reconnection. Plain TCP syslog without RELP may lose the last few messages if the connection drops mid-transmission, which is why RELP exists.

### Can I use Let's Encrypt certificates for syslog TLS?

Yes. Let's Encrypt certificates work perfectly for syslog TLS. The ACME client (certbot, acme.sh, lego) handles automated renewal. Configure your syslog daemon's certificate paths to point to the Let's Encrypt live directory (`/etc/letsencrypt/live/log-server.example.com/`) and set up a post-renewal hook to reload the syslog daemon: `certbot renew --deploy-hook "systemctl reload rsyslog"`. For environments requiring internal-only certificates, a private CA (step-ca or OpenSSL) provides the same automation without internet dependency.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Syslog Encryption: rsyslog TLS vs syslog-ng TLS vs RELP",
  "description": "Complete guide to encrypting syslog transport with TLS using rsyslog, syslog-ng, and RELP. Includes Docker Compose configs, certificate management, and production deployment patterns.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
