---
title: "Self-Hosted SMTP Test Servers: smtp4dev vs MailDev vs FakeSMTP"
date: "2026-05-12"
tags: ["email-testing", "smtp", "development-tools", "mail-server", "smtp4dev", "maildev"]
draft: false
---

Every application that sends email needs a testing strategy. Sending real emails during development risks spamming users, hitting rate limits, and cluttering inboxes. SMTP test servers solve this by intercepting outbound email traffic, capturing messages locally, and providing a web interface to inspect them — all without delivering anything to real recipients.

This guide compares three popular open-source SMTP test servers: **smtp4dev**, **MailDev**, and **FakeSMTP**, covering features, deployment, and integration with development workflows.

## Overview of SMTP Test Servers

| Feature | smtp4dev | MailDev | FakeSMTP |
|---------|----------|---------|----------|
| **GitHub Stars** | 3,889 | 5,920 | 1,007 |
| **Language** | .NET (C#) | Node.js | Java |
| **Web UI** | ✅ Modern Razor pages | ✅ Angular-based | ✅ JavaFX desktop GUI |
| **API** | ✅ REST + SignalR | ✅ REST API | ❌ None |
| **SMTP Auth** | ✅ LOGIN, PLAIN | ✅ LOGIN, PLAIN | ❌ No auth |
| **TLS Support** | ✅ StartTLS | ✅ StartTLS | ❌ No TLS |
| **Message Search** | ✅ Full-text search | ✅ Basic search | ❌ No search |
| **HTML Preview** | ✅ Rendered HTML | ✅ Rendered HTML | ✅ Basic viewer |
| **Attachment Download** | ✅ | ✅ | ✅ |
| **Relay to Real SMTP** | ✅ Configurable | ❌ | ❌ |
| **Docker Image** | ✅ Official | ✅ Official | ❌ Community only |
| **Webhook Support** | ✅ | ✅ | ❌ |

### smtp4dev

smtp4dev is a .NET-based SMTP test server that captures emails and displays them through a modern web interface. It supports SMTP authentication, TLS encryption, message forwarding/relaying, and a REST API for programmatic access. smtp4dev can also relay messages to real SMTP servers when you need to test end-to-end delivery.

### MailDev

MailDev is a Node.js SMTP test server with a feature-rich Angular-based web interface. It provides a REST API, webhook support, and the ability to preview HTML emails with full CSS rendering. MailDev is popular in JavaScript/Node.js development environments due to its native npm package and Docker support.

### FakeSMTP

FakeSMTP is a Java-based dummy SMTP server with a JavaFX desktop GUI. It provides the simplest setup of the three — just start the JAR file and it listens on port 25. FakeSMTP is ideal for quick, local testing where a web interface isn't needed and you just want to capture emails to disk.

## Deploying smtp4dev with Docker Compose

```yaml
# docker-compose.yml for smtp4dev
version: '3.8'
services:
  smtp4dev:
    image: rnwood/smtp4dev:latest
    container_name: smtp4dev
    ports:
      - "25:25"
      - "80:80"
      - "443:443"
    volumes:
      - smtp4dev-data:/smtp4dev
    environment:
      - ServerOptions__HostName=smtp4dev.local
      - ServerOptions__Port=25
      - ServerOptions__AllowRemoteConnections=true
    restart: unless-stopped

volumes:
  smtp4dev-data:
```

smtp4dev starts with a web UI on port 80 and SMTP listener on port 25. Access the dashboard at `http://localhost:80` to view captured messages, search, and inspect email content.

Advanced configuration with SMTP relay and authentication:

```yaml
    environment:
      - ServerOptions__HostName=smtp4dev.local
      - ServerOptions__SmtpPort=25
      - ServerOptions__HttpPort=80
      - RelayOptions__HostName=smtp.yourdomain.com
      - RelayOptions__Port=587
      - RelayOptions__Login=your-smtp-user
      - RelayOptions__Password=your-smtp-password
      - RelayOptions__TlsMode=StartTls
      - RelayOptions__AllowedRecipients=test@yourdomain.com
```

## Deploying MailDev with Docker Compose

```yaml
# docker-compose.yml for MailDev
version: '3.8'
services:
  maildev:
    image: maildev/maildev:latest
    container_name: maildev
    ports:
      - "1025:1025"
      - "1080:1080"
    environment:
      - MAILDEV_SMTP_PORT=1025
      - MAILDEV_WEB_PORT=1080
      - MAILDEV_OUTGOING_USER=
      - MAILDEV_OUTGOING_PASS=
    restart: unless-stopped
```

MailDev uses port 1025 for SMTP and 1080 for the web interface by default. Access the dashboard at `http://localhost:1080`.

Configure MailDev with webhook integration:

```bash
# Set webhook URL for real-time notification
docker run -d --name maildev   -p 1025:1025 -p 1080:1080   -e MAILDEV_WEB_USER=admin   -e MAILDEV_WEB_PASS=admin   maildev/maildev:latest   --webhook-url http://your-app.test/api/email-webhook   --webhook-events new,receive,delete
```

## Running FakeSMTP

FakeSMTP is distributed as a standalone JAR file:

```bash
# Download FakeSMTP
wget https://github.com/Nilhcem/FakeSMTP/releases/download/2.0/fakeSMTP-2.0.jar

# Run with default settings (port 25, saves to ~/Maildir)
java -jar fakeSMTP-2.0.jar

# Run in headless mode (no GUI, saves to specified directory)
java -jar fakeSMTP-2.0.jar -s -p 2525 -o /tmp/fake-emails/
```

For Docker usage (community image):

```yaml
# docker-compose.yml for FakeSMTP (community image)
version: '3.8'
services:
  fakesmtp:
    image: gessnerfl/fake-smtp-server:latest
    container_name: fakesmtp
    ports:
      - "2525:25"
      - "8025:8025"
    volumes:
      - fakesmtp-data:/output
    restart: unless-stopped

volumes:
  fakesmtp-data:
```

## Integration with Application Frameworks

### Python (Django/Flask)

```python
# settings.py (Django)
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025  # MailDev default
EMAIL_USE_TLS = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

# Or for smtp4dev on port 25:
EMAIL_PORT = 25
```

### Node.js (Nodemailer)

```javascript
const nodemailer = require('nodemailer');

const transporter = nodemailer.createTransport({
  host: 'localhost',
  port: 1025,
  secure: false,
  auth: {
    user: '',
    pass: ''
  }
});

transporter.sendMail({
  from: 'test@dev.local',
  to: 'developer@dev.local',
  subject: 'Test Email',
  html: '<h1>Hello from development!</h1>'
});
```

### PHP (SwiftMailer / Symfony Mailer)

```php
// .env.local
MAILER_DSN=smtp://localhost:1025

// Or with authentication:
MAILER_DSN=smtp://user:pass@localhost:25
```

### Java (Spring Boot)

```yaml
# application.yml
spring:
  mail:
    host: localhost
    port: 2525
    properties:
      mail.smtp.auth: false
      mail.smtp.starttls.enable: false
```

## Feature Comparison in Practice

### Message Inspection

**smtp4dev** provides the most comprehensive message inspection with full MIME tree viewing, raw source display, HTML rendering with CSS, and attachment preview. Its SignalR integration provides real-time message updates in the browser.

**MailDev** offers similar inspection capabilities with a clean Angular-based UI. It renders HTML emails accurately and provides raw message source viewing. The REST API allows programmatic access to messages for automated testing.

**FakeSMTP** provides basic email viewing — you can see sender, recipient, subject, and body. The JavaFX GUI is functional but less polished than the web-based alternatives.

### Automated Testing

**smtp4dev** and **MailDev** both support automated testing through their REST APIs. You can verify email delivery, check content, and validate templates programmatically:

```bash
# MailDev: List all messages
curl http://localhost:1080/email

# smtp4dev: List messages via REST API
curl http://localhost:80/api/Messages

# MailDev: Delete all messages (test cleanup)
curl -X DELETE http://localhost:1080/email/all
```

**FakeSMTP** has no API, making automated testing more difficult. You would need to parse saved email files directly.

### Production-Like Testing

**smtp4dev** uniquely supports relaying messages to real SMTP servers for specific recipients. This allows you to test most traffic locally while selectively forwarding test emails to real inboxes for final verification:

```yaml
# smtp4dev relay config - only forward to specific addresses
RelayOptions__AllowedRecipients="real-user@domain.com;qa-team@domain.com"
RelayOptions__DeniedRecipients="*@spam-domain.com"
```

## Choosing the Right SMTP Test Server

### Choose smtp4dev if:
- You need SMTP authentication and TLS support in your test environment
- You want the ability to selectively relay messages to real SMTP servers
- Your team uses .NET and wants native integration
- You need real-time message updates via SignalR

### Choose MailDev if:
- You work primarily in Node.js/JavaScript environments
- You need webhook support for real-time email notifications
- You want a REST API for automated testing pipelines
- You prefer a lightweight, fast-starting container

### Choose FakeSMTP if:
- You need the simplest possible setup (just run a JAR)
- You want a desktop application rather than a web service
- You're doing quick, ad-hoc testing during development
- You don't need TLS, authentication, or API access

## Why Use SMTP Test Servers in Development?

**Prevent accidental emails to users**: The most common reason teams use SMTP test servers is to avoid sending real emails to customers during development and testing. A misconfigured staging server sending password reset emails to production users is a common and embarrassing mistake.

**Faster feedback loops**: SMTP test servers capture emails instantly with zero delivery latency. You don't need to wait for emails to arrive in an inbox, deal with spam filters, or check multiple email clients. Everything is available immediately through the web interface.

**Template debugging**: Email rendering varies across clients. SMTP test servers let you preview HTML email templates with full CSS rendering, check attachment encoding, and verify MIME structure — all without sending a single real email.

**CI/CD integration**: Both smtp4dev and MailDev can be spun up as Docker containers in CI/CD pipelines. Automated tests can send emails to the test server, then use the REST API to verify delivery, subject lines, and content — all without external dependencies.

**Cost savings**: Transactional email services (SendGrid, Mailgun, SES) charge per email. During development, thousands of test emails can accumulate significant costs. SMTP test servers capture all emails locally at zero cost.

For development teams managing CI/CD pipelines, see our [CI/CD pipeline guide](../2026-04-22-buildbot-vs-gocd-vs-concourse-self-hosted-cicd-pipeline-guide/) and [container networking deep dive](../2026-05-24-self-hosted-container-cni-plugins-linux-bridge-ipvlan-macvlan-deep-dive/). If you need full mail server testing, our [mail server management tools](../2026-04-26-postfixadmin-vs-modoboa-vs-iredadmin-self-hosted/) cover administrative interfaces.
For teams managing email at scale, see our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-rel) and [mail server management guide](../2026-04-26-postfixadmin-vs-modoboa-vs-iredadmin-self-hosted-). If you need to test full mail delivery pipelines, our [email campaign platform comparison](../2026-05-02-self-hosted-email-campaign-delivery-tracking-postal-listmonk-mailtrain-guide/) covers self-hosted mailing solutions.

## FAQ

### Can SMTP test servers receive inbound email?

No. SMTP test servers only act as SMTP servers that accept outbound email from your application. They do not fetch email from external mailboxes or act as full mail servers. They intercept email your application tries to send, not email sent to your application.

### Do SMTP test servers support IMAP/POP3?

No. smtp4dev, MailDev, and FakeSMTP are SMTP-only servers. They do not provide IMAP or POP3 access. If you need full mail server testing including IMAP, consider deploying a complete mail server like Stalwart or Mailu in your test environment.

### Can I use SMTP test servers in production?

Generally no. SMTP test servers discard all received emails (or save them locally). They are designed for development and testing only. However, smtp4dev's relay feature can be used in staging environments to forward specific emails to real recipients while capturing everything else.

### How do I clear captured messages between test runs?

**MailDev**: `curl -X DELETE http://localhost:1080/email/all` or restart the container. **smtp4dev**: Use the "Clear All" button in the web UI or call the REST API. **FakeSMTP**: Delete the output directory contents or restart with a fresh output path.

### Do these tools support email templates with variable substitution?

SMTP test servers capture raw email content — they don't process templates. Template substitution happens in your application before the email reaches the SMTP server. Use your application's templating engine (Jinja2, Handlebars, Thymeleaf) and verify the rendered output in the test server's web UI.

### What happens to messages when the container restarts?

**smtp4dev**: Messages are persisted in a volume and survive restarts. **MailDev**: Messages are in-memory by default; use the `--mail-directory` flag for persistence. **FakeSMTP**: Messages are saved to disk and persist across restarts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP Test Servers: smtp4dev vs MailDev vs FakeSMTP",
  "description": "Compare smtp4dev, MailDev, and FakeSMTP — three open-source SMTP test servers for intercepting and inspecting emails during development.",
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
