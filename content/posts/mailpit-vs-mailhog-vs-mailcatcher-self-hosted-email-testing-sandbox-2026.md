---
title: "Mailpit vs MailHog vs MailCatcher: Best Self-Hosted Email Testing Sandbox 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "developer-tools", "email", "testing"]
draft: false
description: "Compare the top three self-hosted email testing sandboxes — Mailpit, MailHog, and MailCatcher — with installation guides, Docker setups, and integration examples for every major framework."
---

Every application that sends email — whether it's password resets, order confirmations, or notification alerts — needs a reliable way to test those emails during development. Sending test messages to real addresses is risky, unprofessional, and often violates the terms of service of email providers. That's where a self-hosted email testing sandbox comes in.

An email testing sandbox intercepts outgoing SMTP traffic, captures every message, and presents it through a web interface or API so you can inspect headers, view HTML renderings, and verify content — all without a single email leaving your machine.

In this guide, we'll compare the three leading open-source solutions: **Mailpit**, **MailHog**, and **MailCatcher**. We'll cover installation, Docker configurations, framework integrations, and help you pick the right tool for your workflow.

## Why You Need a Self-Hosted Email Testing Sandbox

Testing email delivery is one of the most fragile parts of any development pipeline. Without a sandbox, you're faced with a handful of bad options:

- **Sending to real addresses** — Clutters inboxes, risks accidentally emailing customers, and burns through SMTP quota.
- **Using cloud testing services** — Services like Mailtrap or Mailosaur are convenient but come with monthly costs, rate limits, and privacy concerns since your email content passes through third-party servers.
- **Mocking the SMTP client in tests** — Works for unit tests but doesn't verify actual email formatting, HTML rendering, or attachment handling.

A self-hosted email sandbox solves all of these problems:

1. **Zero cost** — Run it locally or on your CI server with no licensing fees.
2. **Complete privacy** — Email content never leaves your infrastructure.
3. **Full fidelity** — Test real SMTP delivery, HTML rendering, inline images, and attachments.
4. **CI/CD integration** — Automate email verification in your test pipelines via REST APIs.
5. **No rate limits** — Send as many test messages as you need during development.

Whether you're building a SaaS platform, an e-commerce store, or an internal tool, having a reliable email testing sandbox is essential for shipping quality software.

## Quick Comparison Table

| Feature | Mailpit | MailHog | MailCatcher |
|---------|---------|---------|-------------|
| **Language** | Go | Go | Ruby |
| **Last Active** | 2026 (Active) | 2021 (Archived) | 2024 (Maintenance) |
| **SMTP Port** | 1025 (configurable) | 1025 | 1025 |
| **Web UI Port** | 8025 | 8025 | 1080 |
| **Web UI Features** | Modern, responsive | Clean, functional | Basic, dated |
| **REST API** | Yes (OpenAPI spec) | Yes | No |
| **Message Search** | Full-text search | Tag-based filtering | None |
| **Release/Tag Messages** | Yes | Yes | No |
| **HTML Preview** | Yes (embedded renderer) | Yes | Yes (browser-based) |
| **Raw Source View** | Yes | Yes | Yes |
| **Attachment Support** | Full (download, preview) | Full | Basic |
| **TLS/STARTTLS** | Yes | No | No |
| **Authentication** | Yes (SMTP AUTH) | No | No |
| **Message Auto-Delete** | Configurable | No | No |
| **Webhook Integration** | Yes | Yes (via third-party) | No |
| **Multi-User Tags** | Yes | Yes | No |
| **Docker Image Size** | ~25 MB | ~15 MB | ~200+ MB |
| **Cross-Platform Binary** | Yes (single binary) | Yes (single binary) | Ruby gem |

## Mailpit: The Modern Successor

[Mailpit](https://github.com/axllent/mailpit) is the most actively maintained of the three projects and has become the de facto standard for email testing in 2026. Written in Go, it ships as a single binary with a modern web interface, full-text search, and a comprehensive REST API.

### Why Mailpit Stands Out

- **Active development** — Regular releases with new features, bug fixes, and security patches.
- **Full-text search** — Search across sender, recipient, subject, and body content instantly.
- **TLS support** — Test TLS and STARTTLS configurations for secure email delivery.
- **SMTP authentication** — Verify applications that require SMTP AUTH credentials.
- **Webhook support** — Trigger external services when new messages arrive.
- **Lightweight** — A single ~25 MB binary with no runtime dependencies.

### Installing Mailpit

**Via binary download:**

```bash
# Download the latest release for your platform
curl -sL https://github.com/axllent/mailpit/releases/latest/download/mailpit-linux-amd64.tar.gz | tar xz
sudo mv mailpit /usr/local/bin/
mailpit --version
```

**Via Homebrew (macOS/Linux):**

```bash
brew install mailpit
mailpit --version
```

**Via Go:**

```bash
go install github.com/axllent/mailpit/cmd/mailpit@latest
```

### Running Mailpit with Docker

The simplest way to get started is with Docker. Here's a production-ready `docker-compose.yml`:

```yaml
version: "3.8"

services:
  mailpit:
    image: axllent/mailpit:latest
    container_name: mailpit
    restart: unless-stopped
    ports:
      - "1025:1025"   # SMTP server
      - "8025:8025"   # Web UI and API
    environment:
      MP_MAX_MESSAGES: 500        # Auto-delete oldest messages
      MP_SMTP_AUTH_ACCEPT_ANY: 1  # Accept any SMTP credentials
      MP_DATABASE: /data/mailpit.db
    volumes:
      - mailpit-data:/data
    networks:
      - app-network

volumes:
  mailpit-data:
    driver: local

networks:
  app-network:
    driver: bridge
```

### Advanced Mailpit Configuration

For teams that need authentication and TLS testing:

```yaml
services:
  mailpit-secure:
    image: axllent/mailpit:latest
    ports:
      - "1025:1025"
      - "8025:8025"
    environment:
      MP_SMTP_AUTH: "testuser:testpass"
      MP_UI_AUTH: "admin:adminpass"
      MP_TLS: "/certs/mailpit.crt:/certs/mailpit.key"
      MP_SMTP_TLS: "true"
      MP_MAX_MESSAGES: 1000
      MP_MESSAGE_RETENTION: "7d"
    volumes:
      - ./certs:/certs:ro
      - mailpit-secure-data:/data

volumes:
  mailpit-secure-data:
```

Generate self-signed certificates for TLS testing:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout certs/mailpit.key \
  -out certs/mailpit.crt \
  -days 365 -subj "/CN=mailpit.local"
```

### Using the Mailpit REST API

Mailpit provides a full REST API at `http://localhost:8025/api/v1/`:

```bash
# List all messages
curl -s http://localhost:8025/api/v1/messages | jq '.messages[].ID'

# Get a specific message
curl -s http://localhost:8025/api/v1/message/<message-id> | jq .

# Search messages
curl -s "http://localhost:8025/api/v1/search?q=welcome+user" | jq .

# Delete all messages
curl -s -X DELETE http://localhost:8025/api/v1/messages

# Release a message to a real address
curl -s -X POST http://localhost:8025/api/v1/message/<message-id>/release \
  -H "Content-Type: application/json" \
  -d '{"Recipients": ["real-user@example.com"]}'
```

## MailHog: The Established Standard (Now Archived)

[MailHog](https://github.com/mailhog/MailHog) was the dominant email testing tool for years. Written in Go, it pioneered the single-binary approach with a clean web UI and REST API. However, the project has been archived since 2021 with no active maintenance.

### MailHog's Legacy

Despite being unmaintained, MailHog remains relevant because:

- It's baked into countless Docker Compose files and CI pipelines.
- Many tutorials and framework guides still reference it as the default.
- It works perfectly fine for basic email interception needs.
- Mailpit is a direct spiritual successor, maintaining API compatibility.

### Running MailHog with Docker

```yaml
version: "3.8"

services:
  mailhog:
    image: mailhog/mailhog:latest
    container_name: mailhog
    restart: unless-stopped
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI
```

### MailHog Configuration via Environment Variables

```yaml
services:
  mailhog-configured:
    image: mailhog/mailhog:latest
    environment:
      MH_STORAGE: maildir          # Store messages on disk
      MH_MAILDIR_PATH: /data       # Directory for maildir storage
      MH_OUTBOUND_SMTP: ""         # Forward mode (empty = no forwarding)
    volumes:
      - mailhog-data:/data

volumes:
  mailhog-data:
```

### Why You Should Consider Migrating to Mailpit

MailHog's archived status means:

- No security patches for newly discovered vulnerabilities.
- No compatibility updates for modern Go toolchains.
- No support for TLS, SMTP AUTH, or modern email authentication mechanisms.
- Known issues with large message handling that will never be fixed.

If you're already using MailHog, migrating to Mailpit is straightforward — the SMTP and web UI ports are identical by default, and the REST API endpoints are largely compatible.

## MailCatcher: The Ruby Original

[MailCatcher](https://github.com/sj26/mailcatcher) is the oldest of the three, written in Ruby. It introduced the concept of an email testing sandbox and inspired both MailHog and Mailpit. It remains in maintenance mode but receives infrequent updates.

### Where MailCatcher Excels

- **Ruby ecosystem integration** — Works seamlessly with Ruby on Rails applications.
- **Simple gem installation** — `gem install mailcatcher` and you're ready to go.
- **Low resource usage** — Light memory footprint for simple use cases.

### Installing MailCatcher

```bash
# Requires Ruby and development headers
sudo apt install ruby-dev build-essential  # Debian/Ubuntu
# or
brew install ruby                           # macOS

gem install mailcatcher
mailcatcher --version
```

### Running MailCatcher

```bash
# Start the server
mailcatcher --foreground --ip 0.0.0.0

# SMTP listens on 1025, web UI on 1080
# Configure your app to use:
#   SMTP: localhost:1025
#   Web UI: http://localhost:1080
```

### Running MailCatcher with Docker

```yaml
version: "3.8"

services:
  mailcatcher:
    image: sj26/mailcatcher:latest
    container_name: mailcatcher
    restart: unless-stopped
    ports:
      - "1025:1025"   # SMTP
      - "1080:1080"   # Web UI (note: different from MailHog/Mailpit)
```

### MailCatcher Command-Line Options

```bash
# Custom ports
mailcatcher --smtp-ip 0.0.0.0 --smtp-port 2525 --http-ip 0.0.0.0 --http-port 3000

# Verbose logging
mailcatcher --foreground --verbose

# Help
mailcatcher --help
```

## Framework Integration Guides

### Django (Python)

```python
# settings.py or settings/test.py
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
```

Run your Django development server and check `http://localhost:8025` for captured emails.

### Laravel (PHP)

```env
# .env.testing
MAIL_MAILER=smtp
MAIL_HOST=localhost
MAIL_PORT=1025
MAIL_USERNAME=null
MAIL_PASSWORD=null
MAIL_ENCRYPTION=null
MAIL_FROM_ADDRESS="test@example.com"
```

### Ruby on Rails

```ruby
# config/environments/development.rb
config.action_mailer.delivery_method = :smtp
config.action_mailer.smtp_settings = {
  address: "localhost",
  port: 1025
}

# For MailCatcher specifically:
config.action_mailer.delivery_method = :smtp
config.action_mailer.smtp_settings = {
  address: "localhost",
  port: 1025,
  enable_starttls_auto: false  # MailCatcher doesn't support STARTTLS
}
```

### Node.js (Nodemailer)

```javascript
const nodemailer = require("nodemailer");

const transporter = nodemailer.createTransport({
  host: "localhost",
  port: 1025,
  secure: false, // true for port 465, false for 1025
  auth: {
    user: "testuser",
    pass: "testpass",
  },
});

await transporter.sendMail({
  from: '"Test App" <noreply@testapp.com>',
  to: "user@example.com",
  subject: "Password Reset Request",
  html: "<p>Click <a href='https://app.com/reset/abc123'>here</a> to reset.</p>",
});
```

### Spring Boot (Java/Kotlin)

```yaml
# src/main/resources/application-test.yml
spring:
  mail:
    host: localhost
    port: 1025
    username: ""
    password: ""
    properties:
      mail:
        smtp:
          auth: false
          starttls:
            enable: false
```

### .NET (ASP.NET Core)

```json
// appsettings.Development.json
{
  "SmtpSettings": {
    "Host": "localhost",
    "Port": 1025,
    "EnableSsl": false,
    "Username": "",
    "Password": ""
  }
}
```

## CI/CD Integration

### GitHub Actions

Add Mailpit to your CI workflow for automated email testing:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mailpit:
        image: axllent/mailpit:latest
        ports:
          - 1025:1025
          - 8025:8025

    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        run: |
          # Your test command here
          # Configure app to use localhost:1025 for SMTP
          make test

      - name: Verify emails sent
        if: always()
        run: |
          # Use Mailpit API to verify emails were captured
          RESPONSE=$(curl -s http://localhost:8025/api/v1/messages)
          COUNT=$(echo "$RESPONSE" | jq '.total')
          echo "Captured $COUNT emails during tests"

          # Verify specific email content
          SEARCH=$(curl -s "http://localhost:8025/api/v1/search?q=password+reset")
          echo "$SEARCH" | jq '.messages[] | {subject, from}'
```

### GitLab CI

```yaml
test:email:
  image: python:3.12-slim
  services:
    - name: axllent/mailpit:latest
      alias: mailpit

  variables:
    EMAIL_HOST: mailpit
    EMAIL_PORT: "1025"

  script:
    - pip install -r requirements.txt
    - pytest tests/test_email_delivery.py

  after_script:
    - |
      # Check that expected emails were captured
      curl -s http://mailpit:8025/api/v1/messages | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total captured: {data[\"total\"]}')
for msg in data['messages']:
    print(f'  - {msg[\"Subject\"]} -> {msg[\"To\"]}')
"
```

## Advanced: Using Webhooks for Real-Time Email Testing

Mailpit supports webhooks, enabling real-time email processing during development:

```bash
# Start Mailpit with webhook support
mailpit --webhook-url "http://localhost:3000/email-hook"
```

Your webhook receiver can process incoming emails programmatically:

```python
from flask import Flask, request, jsonify
import base64

app = Flask(__name__)

@app.route("/email-hook", methods=["POST"])
def email_hook():
    data = request.json
    message_id = data.get("MessageID", "")

    # Fetch the full message from Mailpit API
    import requests
    resp = requests.get(f"http://localhost:8025/api/v1/message/{message_id}")
    email_data = resp.json()

    print(f"New email: {email_data['Subject']}")
    print(f"From: {email_data['From']}")
    print(f"To: {email_data['To']}")

    # Run automated checks
    assert "unsubscribe" in email_data.get("Text", "").lower(), \
        "Missing unsubscribe link!"
    assert email_data.get("From", "") == "noreply@myapp.com", \
        "Wrong sender address!"

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(port=3000)
```

## Choosing the Right Tool

| Scenario | Recommendation |
|----------|---------------|
| **New project** | **Mailpit** — Active development, modern features, best long-term choice |
| **Ruby on Rails project** | **MailCatcher** — Native Ruby integration, simplest setup for Rails |
| **Legacy Docker Compose with MailHog** | **Mailpit** — Drop-in replacement, same ports, compatible API |
| **CI/CD pipeline** | **Mailpit** — REST API, webhooks, small Docker image |
| **TLS/STARTTLS testing** | **Mailpit** — Only tool that supports encrypted SMTP |
| **Team collaboration** | **Mailpit** — Message tags, release features, multi-user auth |
| **Minimal footprint** | **MailHog** — Smallest binary, but archived |

## Conclusion

For most developers and teams in 2026, **Mailpit** is the clear choice. It's actively maintained, feature-rich, and offers everything you need — from a polished web UI to a full REST API, webhook support, and TLS testing. The migration path from MailHog is smooth, making it easy to upgrade existing setups.

**MailCatcher** remains useful for Ruby-centric workflows where gem-based dependencies are preferred, but its lack of a REST API and dated feature set make it less suitable for modern development teams.

**MailHog** still works and may be present in many existing configurations, but its archived status means no new features, no security updates, and no support for modern email protocols like TLS and SMTP AUTH.

Set up your email testing sandbox today — your future self (and your production email quota) will thank you.
