---
title: "Self-Hosted Mail Routing and Transport Management: Postfix vs Exim vs Haraka"
date: "2026-05-10T08:00:00+00:00"
tags: ["email", "mail-routing", "transport", "postfix", "exim", "haraka", "mta", "smtp", "mail-server"]
draft: false
---

Mail routing is the backbone of any email infrastructure. When your organization hosts multiple domains, manages subdomain-based services, or needs to route mail between internal and external systems, a well-configured mail transport layer is essential. The three most widely used self-hosted solutions for mail routing are **Postfix**, **Exim**, and **Haraka** — each with fundamentally different architectures and routing philosophies.

Postfix and Exim are traditional Message Transfer Agents (MTAs) that handle the full SMTP lifecycle — receiving, routing, and delivering email. Haraka is a modern Node.js-based SMTP server designed for high-throughput scenarios with a plugin-based architecture. Understanding how each handles mail transport and routing is critical for building reliable self-hosted email infrastructure.

This guide compares the mail routing capabilities, transport configuration, and extensibility of these three platforms for self-hosted deployments.

## Mail Routing Fundamentals

Mail routing determines how an email is delivered after it arrives at your server. Key routing decisions include:

- **Local delivery** — placing the message in a local mailbox (Maildir/mbox)
- **Relay delivery** — forwarding the message to another SMTP server (internal or external)
- **Virtual domain routing** — routing mail for hosted domains to different backends
- **Transport mapping** — selecting the delivery method based on recipient address, domain, or header
- **Content-based routing** — routing messages based on content, headers, or metadata

A robust mail routing setup enables multi-tenant email hosting, automatic forwarding, mailing lists, and integration with downstream processing systems (spam filters, archiving, ticketing).

## Postfix Transport Maps

Postfix (the world's most deployed MTA) uses a powerful and flexible transport map system. Transport maps define how mail should be delivered based on recipient address patterns, supporting SMTP relay, local delivery, pipe to external commands, and more.

### Key Features

- **Hash/BTree/LMDB lookup tables** — fast, efficient transport lookups
- **Pattern matching** — wildcards, regex, and CIDR-based routing rules
- **Nested tables** — `hash:/etc/postfix/transport` can reference other tables
- **Multiple transport types** — `smtp`, `lmtp`, `local`, `virtual`, `pipe`, `discard`
- **Per-domain and per-address routing** — granular control over delivery paths
- **Relayhost support** — default upstream relay for all outbound mail

### Transport Map Configuration

```ini
# /etc/postfix/transport
# Route all mail for example.com to a specific server
example.com          smtp:[mail.example.com]:587

# Route subdomain mail to a different backend
*.sub.example.com    smtp:[internal-mail.internal]:25

# Pipe mail for a specific address to a script
noreply@example.com  pipe:
  user=mailhandler argv=/usr/local/bin/process-noreply.sh ${sender}

# Deliver to LMTP server (e.g., Dovecot)
example.com          lmtp:unix:private/dovecot-lmtp

# Discard mail to a specific address (silent drop)
spamtrap@example.com discard:
```

Build the lookup table after editing:

```bash
postmap /etc/postfix/transport
systemctl reload postfix
```

### Advanced Routing with PCRE Tables

```ini
# /etc/postfix/transport.pcre
# Route based on recipient domain pattern
/^.*@([a-z]+)\.example\.com$/    smtp:[mail-$1.internal]:25

# Route based on sender domain
/^noreply@partner\.com$/          smtp:[partner-mail.partner.com]:587

# Route all bounced mail to a dedicated handler
/^.*-bounce@.*$/                  pipe:
  user=bounce argv=/opt/bounce-handler ${recipient}
```

```ini
# /etc/postfix/main.cf
transport_maps = hash:/etc/postfix/transport, pcre:/etc/postfix/transport.pcre
```

### Docker Compose

```yaml
version: '3.8'

services:
  postfix:
    image: postfixadmin/postfix:latest
    ports:
      - "25:25"
      - "587:587"
    environment:
      - POSTFIX_myhostname=mail.example.com
      - POSTFIX_mydomain=example.com
      - POSTFIX_mynetworks=127.0.0.0/8,10.0.0.0/8
    volumes:
      - ./postfix-config/main.cf:/etc/postfix/main.cf:ro
      - ./postfix-config/transport:/etc/postfix/transport:ro
      - postfix-data:/var/mail
    restart: unless-stopped

volumes:
  postfix-data: {}
```

## Exim Router Configuration

Exim takes a different approach to mail routing. Instead of lookup tables, Exim uses a sequential router configuration where each router is evaluated in order. The first router that matches the recipient determines the delivery path. This gives Exim more flexibility for complex conditional routing.

### Key Features

- **Sequential router evaluation** — each router is checked in order until one matches
- **Condition-based routing** — complex conditions using expansion strings
- **Multiple delivery transports** — SMTP, LMTP, pipe, appendfile, autoreply
- **Built-in redirect support** — `.forward` files, vacation auto-replies
- **ACL (Access Control Lists)** — fine-grained control at SMTP connection, HELO, MAIL FROM, RCPT TO, and DATA stages
- **Highly customizable** — often called the most flexible MTA for routing

### Router Configuration Example

```ini
# /etc/exim4/conf.d/router/
# Router 1: Local delivery for local domains
local_user:
  driver = accept
  domains = +local_domains
  check_local_user
  transport = local_delivery
  cannot_route_message = Unknown user

# Router 2: Virtual domain delivery (multi-tenant)
virtual_domains:
  driver = accept
  domains = dsearch;/etc/exim4/virtual/
  transport = virtual_delivery
  cannot_route_message = Unknown virtual user

# Router 3: Specific address routing
nOREply_router:
  driver = redirect
  data = |/usr/local/bin/process-noreply.sh
  domains = example.com
  local_parts = noreply

# Router 4: Catch-all for a domain
domain_catchall:
  driver = redirect
  data = catchall@example.com
  domains = example.com
  local_parts = *

# Router 5: Default relay for non-local domains
dnslookup:
  driver = dnslookup
  domains = !+local_domains
  transport = remote_smtp
  ignore_target_hosts = 0.0.0.0 : 127.0.0.0/8
  no_more
```

### Transport Configuration

```ini
# /etc/exim4/conf.d/transport/
# Local delivery to Maildir
local_delivery:
  driver = appendfile
  directory = /home/${local_part}/Maildir
  maildir_format
  create_directory

# Virtual domain delivery
virtual_delivery:
  driver = appendfile
  directory = /var/mail/virtual/${domain}/${local_part}/Maildir
  maildir_format
  user = vmail
  group = vmail
  create_directory
```

### Docker Deployment

```yaml
version: '3.8'

services:
  exim4:
    image: devture/exim-relay:latest
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./exim-config/exim4.conf:/etc/exim4/exim4.conf:ro
      - ./exim-config/virtual/:/etc/exim4/virtual/:ro
      - exim-data:/var/mail
    environment:
      - RELAY_FROM_HOSTS=10.0.0.0/8:127.0.0.0/8
    restart: unless-stopped

volumes:
  exim-data: {}
```

## Haraka Plugin-Based Routing

Haraka is a modern SMTP server written in Node.js (5,500+ GitHub stars) that uses a plugin-based architecture for all functionality, including mail routing. Unlike Postfix and Exim, which are compiled MTAs with configuration-driven routing, Haraka handles routing through JavaScript plugins that can implement arbitrary logic.

### Key Features

- **Plugin architecture** — every feature is a plugin, including routing
- **Node.js ecosystem** — access to NPM packages for database access, HTTP APIs, etc.
- **Event-driven** — handles thousands of concurrent connections efficiently
- **Hot-reload plugins** — modify routing logic without restarting the server
- **Built-in queue** — in-memory or Redis-backed mail queue
- **Custom routing logic** — implement complex routing via JavaScript plugins

### Installation and Plugin Setup

```bash
# Install Haraka
npm install -g Haraka

# Create a new Haraka instance
haraka -i /etc/haraka
cd /etc/haraka

# Enable routing plugins
echo "relay" >> config/plugins
echo "queue/smtp-forward" >> config/plugins
echo "mail_from.is_resolvable" >> config/plugins
```

### Routing Plugin Configuration

```ini
# config/relay.ini
# Allow relaying for authenticated users and specific IPs
[relay]
acl=1
max_connections=100

# config/smtp_forward.ini
# Route mail based on recipient domain
[example.com]
host=mail.example.com
port=587
auth_type=plain
auth_user=router@example.com
auth_password=router_password

# Default route for unmatched domains
[default]
host=upstream-smtp.internal
port=25
```

### Custom Routing Plugin

```javascript
// plugins/route_by_header.js
// Route mail based on custom X-Route-To header
exports.hook_data_post = function (next, connection) {
    const txn = connection.transaction;
    const routeHeader = txn.header.get('X-Route-To');
    
    if (routeHeader) {
        const routeTo = routeHeader.trim();
        // Set routing via queue config
        connection.notes.route_to = routeTo;
        connection.loginfo(this, 'Routing to: ' + routeTo);
    }
    next();
};

exports.hook_queue = function (next, connection) {
    const routeTo = connection.notes.route_to;
    if (routeTo) {
        // Forward to specific host
        connection.transaction.notes.forward_host = routeTo;
    }
    next(OK);
};
```

### Docker Compose

```yaml
version: '3.8'

services:
  haraka:
    image: homeassistant/haraka:latest
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./haraka/config:/haraka/config:ro
      - ./haraka/plugins:/haraka/plugins:ro
      - haraka-queue:/haraka/queue
    environment:
      - NODE_ENV=production
    restart: unless-stopped

volumes:
  haraka-queue: {}
```

## Comparison: Mail Routing Capabilities

| Feature | Postfix | Exim | Haraka |
|---------|---------|------|--------|
| **Architecture** | Modular MTA | Monolithic MTA | Node.js plugin server |
| **Routing Mechanism** | Transport maps (lookup tables) | Sequential routers | JavaScript plugins |
| **Configuration Language** | Key-value + lookup tables | Custom config syntax | JavaScript/JSON/INI |
| **Pattern Matching** | Hash, PCRE, LDAP, MySQL | Expansion strings, regex | Full JavaScript |
| **Content-Based Routing** | Via `header_checks`/`body_checks` | Via ACL + conditionals | Via custom plugins |
| **Performance** | Very high (C) | High (C) | High (async Node.js) |
| **Ease of Use** | Moderate | Complex | Easy (if you know JS) |
| **Plugin Ecosystem** | Limited | Limited | Extensive (NPM) |
| **Hot-Reload Config** | Yes (postfix reload) | Partial | Yes (plugins) |
| **Docker Image** | Community | Community | Community/Official |
| **GitHub Stars** | N/A (not on GitHub) | N/A (not on GitHub) | 5,556+ |
| **Best For** | Standard mail routing | Complex conditional routing | Custom routing logic |

## Choosing the Right Mail Routing Solution

**Choose Postfix when:**
- You need a proven, well-documented MTA with straightforward transport maps
- Your routing needs are pattern-based (domain, address, or header matching)
- You want the widest community support and most tutorials available
- You are running a standard multi-domain mail server

**Choose Exim when:**
- You need highly complex conditional routing (multi-level conditions, database lookups)
- You are already using Debian's default MTA (Exim4)
- You need per-recipient routing with database-backed virtual domains
- You want ACL-level control at every SMTP transaction stage

**Choose Haraka when:**
- You need custom routing logic that goes beyond pattern matching
- Your team is comfortable with JavaScript and the NPM ecosystem
- You want hot-reloadable plugins for rapid iteration
- You need to integrate mail routing with HTTP APIs, webhooks, or microservices

## Why Self-Host Mail Routing?

Running your own mail routing infrastructure gives you complete control over how email flows through your organization. Cloud email providers route mail through their infrastructure with limited customization. With self-hosted routing, you can implement domain-specific policies, route mail through internal compliance scanners, forward to different backends based on content, and maintain full audit trails of every message that passes through your systems.

For organizations with regulatory requirements (HIPAA, GDPR, financial services), self-hosted mail routing ensures that sensitive communications never leave your controlled infrastructure. You can implement mandatory archiving, content inspection, and delivery logging that cloud providers do not offer at the routing layer.

For related reading, see our [MTA comparison guide](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide-2026/), [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/), and [email alias management guide](../2026-04-20-simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide-2026/).

## FAQ

### What is the difference between a transport map and a virtual mailbox map in Postfix?
Transport maps define HOW mail is delivered (SMTP relay, local delivery, pipe to a command, etc.), while virtual mailbox maps define WHERE mail is delivered (which mailbox file or directory). Transport maps select the delivery method; virtual mailbox maps select the destination within that method. You can use both together — a transport map routes mail to a virtual delivery agent, which then uses the virtual mailbox map to find the specific mailbox.

### Can Exim route mail based on the message content?
Yes, Exim can inspect message headers and body content during the ACL phase and make routing decisions based on what it finds. The `acl_smtp_data` hook runs after the message body is received, allowing you to examine content and set delivery options. You can redirect messages, add headers, change the transport, or even reject messages based on content patterns, attachment types, or embedded URLs.

### Does Haraka support traditional MTA features like queue management and retry?
Haraka has a built-in queue system that supports both in-memory queuing and Redis-backed persistent queuing. Failed deliveries are automatically retried with exponential backoff. The `queue/smtp-forward` plugin handles outbound SMTP delivery with retry logic similar to traditional MTAs. For production deployments, always use Redis-backed queuing to survive server restarts.

### How do I handle mail routing for multiple domains with different backends?
All three solutions support multi-domain routing. In Postfix, use `virtual_mailbox_domains` and `transport_maps` to route each domain to a different backend. In Exim, use `dsearch` to look up domain configurations from a directory or database. In Haraka, write a plugin that reads domain-to-backend mappings from a JSON file or database and sets the appropriate forwarding target.

### Which MTA is easiest to set up for basic mail routing?
Postfix has the lowest learning curve for basic routing. Its transport map system is straightforward: define a lookup table, build it with `postmap`, and reference it in `main.cf`. Exim's router-based approach is more powerful but requires understanding the sequential evaluation order. Haraka is easy if you know JavaScript, but requires setting up a Node.js environment and understanding its plugin architecture.

### How do I monitor mail routing and delivery status?
Postfix logs all delivery attempts to syslog with detailed status codes. Use `postqueue -p` to view the mail queue and `postcat -q QUEUE_ID` to inspect individual messages. Exim provides `exim -bp` for queue listing and `exim -Mvl QUEUE_ID` for delivery logs. Haraka logs to stdout/stderr by default and can be configured to write to files or a logging service. For all three, integrate with log aggregation (ELK, Loki) for centralized monitoring.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Routing and Transport Management: Postfix vs Exim vs Haraka",
  "description": "Compare Postfix, Exim, and Haraka for self-hosted mail routing and transport management. Learn transport maps, router configuration, and plugin-based routing for email infrastructure.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
