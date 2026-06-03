---
title: "Self-Hosted IMAP Proxy Servers: Perdition vs Nginx Mail Proxy vs Dovecot Proxy"
date: "2026-06-03"
tags: ["imap", "pop3", "email", "mail-server", "proxy", "self-hosted", "infrastructure", "dovecot", "nginx"]
draft: false
---

## Introduction

When running self-hosted email infrastructure at scale, directing IMAP and POP3 clients directly to your backend mail store creates several problems. Each client connection consumes resources on your Dovecot or Cyrus server, and if you run multiple backend mail stores (for load balancing or migration scenarios), clients need to know which server holds their mailbox. An IMAP proxy server sits between clients and backend mail servers, handling connection multiplexing, authentication routing, and TLS termination — all while reducing load on your primary mail infrastructure.

In this guide, we compare three open-source IMAP/POP3 proxy solutions: **Perdition**, the venerable general-purpose mail retrieval proxy; **Nginx Mail Proxy**, leveraging Nginx's battle-tested event-driven architecture for mail protocols; and **Dovecot Proxy**, using Dovecot's own built-in proxy capabilities for seamless integration with Dovecot backends. Each takes a fundamentally different approach to the same problem.

## Why Use an IMAP Proxy?

An IMAP proxy provides three critical functions for self-hosted email infrastructure:

**Connection Multiplexing**. IMAP clients maintain long-lived TCP connections. A proxy pools backend connections, allowing hundreds of clients to share a handful of backend connections — dramatically reducing memory and file descriptor usage on your mail store.

**Authentication-Based Routing**. In multi-server setups, the proxy inspects the username during the IMAP/POP3 login phase and routes the connection to the correct backend server. This enables transparent migrations, geographic distribution, and tiered storage architectures.

**TLS Termination**. The proxy handles TLS encryption at the edge, offloading CPU-intensive cryptographic operations from backend servers. This also centralizes certificate management.

| Feature | Perdition | Nginx Mail Proxy | Dovecot Proxy |
|---------|-----------|-----------------|---------------|
| Protocol Support | IMAP, POP3, IMAPS, POP3S | IMAP, POP3, SMTP | IMAP, POP3, LMTP |
| Auth Backend | LDAP, MySQL, PAM, GDBM, CDB, regex | HTTP Auth, IMAP Authenticate | Dovecot auth socket, SQL, LDAP |
| TLS Termination | Yes (OpenSSL/GnuTLS) | Yes (OpenSSL) | Yes (OpenSSL) |
| Connection Pooling | Per-backend pools | Proxy protocol passthrough | Per-backend pools |
| Backend Health Check | Basic connection test | Passive (proxy errors) | Active health checks |
| Configuration Style | Daemon config + popmap file | Nginx-style config blocks | Dovecot passdb/userdb |
| GitHub Stars | ~0 (community) | Nginx: 26,000+ (parent) | Dovecot: 2,300+ |
| Memory Footprint | ~5-8 MB | ~10-15 MB | ~15-25 MB |

## Perdition: The Specialized Mail Retrieval Proxy

Perdition is a purpose-built IMAP and POP3 proxy daemon. It is lightweight, highly configurable, and follows the Unix philosophy of doing one thing well — proxying mail retrieval connections.

**Architecture**. Perdition listens on IMAP/POP3 ports and maps incoming connections to backend servers using a "popmap" — a lookup table (file, database, or LDAP query) that maps usernames to backend server addresses. It supports STARTTLS and TLS-wrapped connections.

**Docker Compose deployment:**

```yaml
version: '3.8'
services:
  perdition:
    image: instrumentisto/perdition:latest
    container_name: perdition-imap-proxy
    ports:
      - "143:143"
      - "993:993"
      - "110:110"
      - "995:995"
    volumes:
      - ./perdition.conf:/etc/perdition/perdition.conf:ro
      - ./popmap:/etc/perdition/popmap:ro
    restart: unless-stopped
```

**Key configuration** (`perdition.conf`):

```
listen_port 143
protocol IMAP4
outgoing_port 143
log_facility LOG_MAIL
tls_cert_file /etc/ssl/certs/mail.example.com.crt
tls_key_file /etc/ssl/private/mail.example.com.key
```

**Best for**: Environments that need a lightweight, single-purpose proxy with flexible authentication backends (LDAP, MySQL) and minimal resource usage. Not ideal if you need SMTP submission proxying in the same process.

## Nginx Mail Proxy: Multiprotocol Power

Nginx's mail proxy module extends Nginx's event-driven architecture to IMAP, POP3, and SMTP protocols. This is the same battle-tested engine that powers much of the web.

**Architecture**. Nginx mail proxy uses the familiar server/upstream block configuration. Authentication is delegated to an external HTTP endpoint — Nginx sends client credentials to an auth server, which returns the backend server address and port. This keeps authentication logic completely separate from proxy configuration.

**Docker Compose deployment:**

```yaml
version: '3.8'
services:
  nginx-mail:
    image: nginx:alpine
    container_name: nginx-mail-proxy
    ports:
      - "143:143"
      - "993:993"
      - "110:110"
      - "995:995"
      - "587:587"
    volumes:
      - ./nginx-mail.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    restart: unless-stopped
```

**Nginx mail configuration:**

```nginx
mail {
    server_name mail.example.com;
    auth_http http://auth.example.com:8080/auth;

    proxy_pass_error_message on;
    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    server {
        listen     143;
        protocol   imap;
        starttls   on;
        proxy      on;
    }

    server {
        listen     993 ssl;
        protocol   imap;
        proxy      on;
    }

    server {
        listen     587;
        protocol   smtp;
        starttls   on;
        proxy      on;
        xclient    on;
    }
}
```

**Best for**: Teams already running Nginx for web traffic who want a unified proxy layer. The HTTP auth backend pattern provides maximum flexibility — you can implement complex routing logic in any language. SMTP submission proxy support is a bonus not available in Perdition.

## Dovecot Proxy: Native Integration

Dovecot is primarily an IMAP/POP3 server, but it includes a powerful proxy mode that transforms it into a protocol-aware proxy. When combined with a Dovecot director, it can handle complex multi-backend architectures.

**Architecture**. Dovecot proxy uses its own `passdb` system to look up users and determine which backend server to proxy to. The `proxy` and `proxy_maybe` fields in passdb entries control proxy behavior. A Dovecot director (optional) provides consistent backend-to-user mapping.

**Dovecot proxy configuration** (`dovecot.conf`):

```
protocols = imap pop3

passdb {
    driver = static
    args = proxy=y host=192.168.1.10 port=143 nopassword=y
}

# Or using SQL-based routing:
passdb {
    driver = sql
    args = /etc/dovecot/dovecot-sql.conf.ext
}

service imap-login {
    inet_listener imap {
        port = 143
    }
    inet_listener imaps {
        port = 993
        ssl = yes
    }
}
```

**Docker Compose deployment:**

```yaml
version: '3.8'
services:
  dovecot-proxy:
    image: dovecot/dovecot:latest
    container_name: dovecot-imap-proxy
    ports:
      - "143:143"
      - "993:993"
      - "110:110"
      - "995:995"
    volumes:
      - ./dovecot.conf:/etc/dovecot/dovecot.conf:ro
      - ./conf.d:/etc/dovecot/conf.d:ro
      - ./certs:/etc/dovecot/certs:ro
    restart: unless-stopped
```

**Best for**: Environments already using Dovecot as the backend mail store. The tight integration between Dovecot proxy and Dovecot backend provides seamless proxying with active health checks and automatic failover. The director component enables consistent hashing for distributed setups.

## Choosing the Right Proxy

| Scenario | Recommended Proxy |
|----------|------------------|
| Single backend, minimal overhead | Perdition |
| Already running Nginx, need SMTP proxy | Nginx Mail Proxy |
| Dovecot backends, need director/ring architecture | Dovecot Proxy |
| Complex auth routing (custom HTTP API) | Nginx Mail Proxy |
| LDAP-based user lookup | Perdition or Dovecot |
| Multi-protocol (IMAP + POP3 + SMTP) | Nginx Mail Proxy |

## Why Self-Host Your Mail Proxy Layer?

Running your own IMAP proxy infrastructure gives you control over email access patterns that no SaaS provider can match. When you proxy connections through your own infrastructure, you gain complete visibility into authentication patterns, connection durations, and protocol-level errors — data that is invaluable for security auditing and capacity planning.

For organizations managing multiple domains or migrating between mail platforms, an IMAP proxy is the difference between a seamless client experience and a support nightmare. Rather than asking hundreds of users to reconfigure their email clients, you update the proxy's routing table and connections flow to the new backend transparently.

Security-conscious deployments benefit from centralized TLS management. Instead of maintaining certificates on every backend mail server, you maintain one certificate on the proxy. When a vulnerability like Heartbleed requires certificate rotation, you update one server instead of dozens.

For more on building complete self-hosted email infrastructure, see our [comprehensive email server guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/). If you are evaluating which mail server stack to deploy behind your proxy, our [mail server platform comparison](../stalwart-vs-mailcow-vs-mailu/) covers the major options. For client-side access, check out our [self-hosted webmail clients guide](../roundcube-vs-snappymail-vs-cypht-self-hosted-webmail-guide-2026/).

## FAQ

### Can I use IMAP proxy for POP3 as well?

Yes. All three solutions — Perdition, Nginx Mail Proxy, and Dovecot Proxy — support both IMAP and POP3 protocols. Perdition and Nginx handle both natively. Dovecot proxy supports POP3 proxying but requires the `pop3` protocol to be explicitly enabled in the configuration. The same authentication and routing logic applies regardless of protocol.

### Does IMAP proxying break IDLE (push email)?

No, but it requires proxy-level support. Dovecot proxy natively supports IMAP IDLE passthrough — the client's IDLE command is forwarded to the backend, and notifications propagate back through the proxy. Nginx mail proxy also supports IDLE passthrough. Perdition's IDLE support depends on the version and protocol handler. Verify this in your specific configuration before deploying.

### How does TLS work with IMAP proxying?

There are two common patterns: TLS termination at the proxy (the proxy handles TLS, backend connections are plaintext on a trusted network) and TLS passthrough (the proxy passes encrypted connections through without decrypting). TLS termination at the proxy is the most common pattern — it centralizes certificate management and reduces backend CPU load. All three solutions support TLS termination. Nginx also supports STARTTLS upgrade from plaintext connections.

### Can one proxy handle multiple backend mail server types?

Yes. This is one of the primary use cases. You can proxy IMAP connections from a single public endpoint to Dovecot backends, Cyrus backends, and even proprietary Exchange servers simultaneously — the proxy routes each user to the correct backend based on their authentication credentials. Nginx Mail Proxy is particularly well-suited for this because the HTTP auth backend can implement arbitrarily complex routing logic.

### What about connection limits and rate limiting?

Nginx Mail Proxy provides the most sophisticated connection limiting through its standard Nginx worker configuration. You can set `worker_connections`, rate-limit authentication attempts, and use `limit_conn` zones to prevent abuse. Dovecot proxy supports connection limits via `mail_max_userip_connections`. Perdition has basic connection throttling through `connection_limit` directives. For high-traffic deployments, place the proxy behind a TCP load balancer like HAProxy for additional connection management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IMAP Proxy Servers: Perdition vs Nginx Mail Proxy vs Dovecot Proxy",
  "description": "Comprehensive comparison of self-hosted IMAP and POP3 proxy solutions including Perdition, Nginx Mail Proxy, and Dovecot Proxy with Docker Compose deployment examples.",
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
