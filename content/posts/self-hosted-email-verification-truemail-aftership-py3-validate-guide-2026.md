---
title: "Self-Hosted Email Verification: Truemail vs AfterShip vs py3-validate-email (2026)"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "email", "validation"]
draft: false
description: "Compare the best self-hosted email verification tools — Truemail, AfterShip email-verifier, and py3-validate-email — with Docker setup guides, feature comparisons, and deployment best practices for 2026."
---

If you run a self-hosted email server, mailing list, or web application that accepts user registrations, email validation is one of the most impactful quality-of-life improvements you can make. Bounced emails hurt your sender reputation, waste storage, and inflate infrastructure costs. This guide compares three open-source, self-hosted email verification tools so you can choose the right one for your stack.

## Why Self-Host Email Verification?

Commercial email verification services like ZeroBounce, Hunter, or Mailgun's validation API charge per lookup — costs that add up quickly at scale. Self-hosting gives you:

- **Unlimited lookups** — verify millions of addresses with no per-query fees
- **Data privacy** — email addresses never leave your infrastructure, critical for GDPR and HIPAA compliance
- **Full control** — configure verification depth, timeouts, and disposable domain lists to match your needs
- **Integration flexibility** — embed validation in registration forms, cron jobs, or API pipelines without vendor lock-in

For teams already running [self-hosted email servers with Postfix and Dovecot](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/), adding a verification layer is a natural extension. If you're testing email delivery locally, tools like [Mailpit or Mailhog](../mailpit-vs-mailhog-vs-mailcatcher-self-hosted-email-testing-sandbox-2026/) handle the sandbox side, while the tools below handle the validation side.

## How Email Verification Works

Email verification operates at three levels, each providing increasing confidence:

1. **Syntax validation** — checks that the address conforms to RFC 5322 format (e.g., `user@domain.tld`). Fast, but catches only obvious typos.
2. **Domain/MX verification** — confirms the domain exists and has valid MX (mail exchange) DNS records. Catches non-existent domains and domains that cannot receive mail.
3. **SMTP mailbox verification** — initiates an SMTP connection to the target mail server, performs a `RCPT TO` probe, and checks whether the mailbox exists. Most accurate but slowest and most resource-intensive.

A complete verification pipeline runs all three checks in sequence, failing fast on syntax or domain errors before attempting expensive SMTP probes. Additionally, a **disposable email detection** layer catches temporary addresses from services like Mailinator or Guerrilla Mail, which are commonly used for spam registrations.

## Truemail — Full-Stack Email Verification Server

**GitHub:** [truemail-rb/truemail](https://github.com/truemail-rb/truemail) · 1,264 stars · Last updated: April 2024

Truemail is the most comprehensive self-hosted email verification solution available. Written in Ruby, it supports all three verification levels (syntax, MX, SMTP) and includes a built-in web API server via the companion [truemail-rack](https://github.com/truemail-rb/truemail-rack) project (34 stars).

### Key Features

- Configurable verification depth per domain pattern
- SMTP connection with custom HELO/EHLO identity
- DNSBL (DNS-based blacklist) checking for known spam sources
- Whitelist/blacklist domain management
- JSON and XML API output via truemail-rack
- Ruby gem for direct application integration
- Regular expression-based domain matching for custom rules

### Docker Deployment

While Truemail itself is a Ruby gem, truemail-rack provides a ready-to-deploy API server. Here's a Docker Compose setup:

```yaml
version: "3.8"

services:
  truemail:
    image: ruby:3.3-slim
    container_name: truemail-api
    restart: unless-stopped
    ports:
      - "9292:9292"
    volumes:
      - ./truemail-config:/app/config
      - ./Gemfile:/app/Gemfile
    working_dir: /app
    command: >
      bash -c "
        gem install truemail-rack puma &&
        puma -C config/puma.rb config.ru
      "
    environment:
      - TRUEMAIL_VERIFICATION_LEVEL=smtp
      - TRUEMAIL_DNS_PORT=53
      - TRUEMAIL_CONNECTION_TIMEOUT=2
      - TRUEMAIL_RESPONSE_TIMEOUT=2
    networks:
      - email-net

networks:
  email-net:
    driver: bridge
```

### Configuration Example

Truemail uses a Ruby configuration block. Here's a production-ready setup:

```ruby
Truemail.configure do |config|
  # Required: specify the sender email for SMTP verification
  config.verifier_email = "verify@yourdomain.com"

  # Verification level: :regex, :mx, or :smtp
  config.default_validation_type = :smtp

  # Timeouts
  config.connection_timeout = 2
  config.response_timeout = 2

  # Custom DNS server (optional — uses system resolver by default)
  config.dns = ["1.1.1.1", "8.8.8.8"]

  # Domain whitelists/blacklists
  config.whitelist_domains = ["yourdomain.com", "partner.org"]
  config.blacklist_domains = ["mailinator.com", "guerrillamail.com"]

  # SMTP port (default 25)
  config.smtp_port = 25

  # SMTP safe check — doesn't close connection after RCPT TO probe
  config.smtp_safe_check = true
end
```

### API Usage

Once truemail-rack is running, verify an email with a simple HTTP request:

```bash
curl -s "http://localhost:9292/api/v1/verify?email=user@example.com" | python3 -m json.tool
```

Response:

```json
{
  "success": true,
  "email": "user@example.com",
  "did_you_mean": null,
  "validation_type": "smtp",
  "smtp_debug": [
    {
      "host": "mx.example.com",
      "port": 25,
      "response": "250 OK",
      "success": true
    }
  ]
}
```

## AfterShip email-verifier — Go-Based Library

**GitHub:** [AfterShip/email-verifier](https://github.com/AfterShip/email-verifier) · 1,553 stars · Last updated: February 2026

AfterShip's email-verifier is a Go library that provides fast, programmatic email verification. It's designed to be imported directly into Go applications rather than run as a standalone service, making it ideal for backend validation in Go-based web applications.

### Key Features

- Syntax validation with RFC 5322 compliance
- Domain and MX record lookup
- SMTP mailbox verification with configurable timeouts
- Disposable email detection via built-in domain list
- Role-based email detection (e.g., `admin@`, `postmaster@`)
- Free email provider detection (Gmail, Yahoo, Outlook)
- No external dependencies beyond Go standard library + DNS resolver

### Go Integration

Add the library to your Go project:

```bash
go get github.com/AfterShip/email-verifier
```

```go
package main

import (
    "fmt"
    "log"
    "github.com/AfterShip/email-verifier"
)

func main() {
    verifier := emailverifier.NewVerifier().
        EnableSMTPCheck().
        EnableDomainSuggest().
        SetTimeout(5)

    result, err := verifier.Verify("user@example.com")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Valid: %v\n", result.IsValid())
    fmt.Printf("Disposable: %v\n", result.Disposable)
    fmt.Printf("Role account: %v\n", result.RoleAccount)
    fmt.Printf("Free provider: %v\n", result.FreeEmail)
    fmt.Printf("MX records: %v\n", result.MXRecords)
}
```

### Standalone API Wrapper

Since email-verifier is a library (not a server), you can wrap it in a lightweight HTTP API using Go's built-in `net/http`:

```go
package main

import (
    "encoding/json"
    "net/http"
    emailverifier "github.com/AfterShip/email-verifier"
)

var verifier = emailverifier.NewVerifier().EnableSMTPCheck()

func handleVerify(w http.ResponseWriter, r *http.Request) {
    email := r.URL.Query().Get("email")
    if email == "" {
        http.Error(w, "email parameter required", 400)
        return
    }

    result, err := verifier.Verify(email)
    if err != nil {
        http.Error(w, err.Error(), 500)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(result)
}

func main() {
    http.HandleFunc("/verify", handleVerify)
    http.ListenAndServe(":8080", nil)
}
```

Build and run:

```bash
go build -o email-verifier-api main.go
./email-verifier-api &
```

## py3-validate-email — Python Email Verification

**GitHub:** [martinr92/py3-validate-email](https://github.com/martinr92/py3-validate-email) · Active Python package

py3-validate-email is a Python library that performs comprehensive email verification with a simple API. It's the go-to choice for Python-based applications, Django projects, and FastAPI backends.

### Key Features

- RFC 5322 syntax validation
- DNS MX record verification
- SMTP mailbox probing
- Disposable email domain detection (updated list)
- Role-based address detection
- Typo suggestion for common domain misspellings
- Async support for high-throughput verification

### Installation

```bash
pip install py3-validate-email
```

### Python Usage

```python
from validate_email import validate_email

# Full verification (syntax + MX + SMTP)
is_valid = validate_email(
    email_address="user@example.com",
    check_format=True,
    check_dns=True,
    check_smtp=True,
    smtp_from_address="verify@yourdomain.com",
    smtp_timeout=5,
)

print(f"Email valid: {is_valid}")
```

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from validate_email import validate_email

app = FastAPI()

@app.get("/verify/{email}")
async def verify_email(email: str):
    result = validate_email(
        email_address=email,
        check_format=True,
        check_dns=True,
        check_smtp=True,
    )
    if result is None:
        return {"email": email, "valid": False, "reason": "verification failed"}
    return {"email": email, "valid": True}
```

Run with:

```bash
pip install fastapi uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Disposable Email Detection

Regardless of which verification tool you choose, maintaining an up-to-date disposable email domain list is essential. Two popular open-source repositories track these domains:

- **[martenson/disposable-email-domains](https://github.com/martenson/disposable-email-domains)** — 4,971 stars, Python, updated April 2026
- **[FGRibreau/mailchecker](https://github.com/FGRibreau/mailchecker)** — 1,877 stars, PHP with cross-language bindings, updated April 2026

Both projects maintain curated lists of known disposable and temporary email providers. You can integrate these lists into any of the three tools above by updating their blacklist configurations:

```bash
# Download the latest disposable domain list
curl -sL https://raw.githubusercontent.com/martenson/disposable-email-domains/master/disposable_email_blocklist.conf \
  -o /etc/truemail/disposable_domains.txt

# Use in Truemail config
config.blacklist_file = "/etc/truemail/disposable_domains.txt"
```

## Comparison Table

| Feature | Truemail | AfterShip email-verifier | py3-validate-email |
|---|---|---|---|
| **Language** | Ruby | Go | Python |
| **Syntax validation** | ✅ RFC 5322 | ✅ RFC 5322 | ✅ RFC 5322 |
| **MX verification** | ✅ | ✅ | ✅ |
| **SMTP verification** | ✅ | ✅ | ✅ |
| **Disposable detection** | ✅ (custom lists) | ✅ (built-in) | ✅ (built-in) |
| **Role account detection** | ❌ | ✅ | ✅ |
| **Free provider detection** | ❌ | ✅ | ❌ |
| **Typo suggestion** | ❌ | ✅ | ✅ |
| **DNSBL checking** | ✅ | ❌ | ❌ |
| **Standalone API server** | ✅ (truemail-rack) | ⚠️ Requires wrapper | ⚠️ Requires wrapper |
| **Library integration** | ✅ Ruby gem | ✅ Go package | ✅ Python pip |
| **Async support** | ❌ | ❌ | ✅ |
| **Docker-ready** | ✅ | ❌ | ❌ |
| **Stars** | 1,264 | 1,553 | Active |

## Choosing the Right Tool

**Choose Truemail if:**
- You want a ready-to-deploy API server with Docker
- You need DNSBL checking for spam source detection
- Your stack is Ruby-based or you need an HTTP API
- You require fine-grained per-domain configuration

**Choose AfterShip email-verifier if:**
- Your application is written in Go
- You need role account and free provider detection
- You want the fastest verification (Go's compiled performance)
- You prefer a library over a standalone service

**Choose py3-validate-email if:**
- Your application is Python-based (Django, FastAPI, Flask)
- You need async verification for high-throughput pipelines
- You want typo suggestions for common domain misspellings
- You're building a data-cleaning script for existing user databases

## Deployment Best Practices

### Rate Limiting SMTP Probes

When verifying large lists, target mail servers may rate-limit or block your IP. Implement delays between probes:

```bash
# Batch verification with delay
while read email; do
    curl -s "http://localhost:9292/api/v1/verify?email=$email" >> results.jsonl
    sleep 1  # 1-second delay between probes
done < emails_to_verify.txt
```

### Docker Compose for Production

Here's a full production stack combining Truemail with Redis for caching results:

```yaml
version: "3.8"

services:
  truemail:
    image: ruby:3.3-slim
    container_name: truemail-api
    restart: unless-stopped
    ports:
      - "9292:9292"
    volumes:
      - ./config:/app/config
      - ./disposable_domains.txt:/app/disposable_domains.txt
    working_dir: /app
    command: >
      bash -c "
        gem install truemail-rack puma redis &&
        puma -C config/puma.rb config.ru
      "
    environment:
      - TRUEMAIL_VERIFICATION_LEVEL=smtp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - email-net

  redis:
    image: redis:7-alpine
    container_name: truemail-cache
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - email-net

volumes:
  redis-data:

networks:
  email-net:
    driver: bridge
```

### Monitoring and Logging

Configure Truemail's SMTP safe check and logging to monitor verification success rates:

```ruby
config.smtp_safe_check = true
config.logger = Logger.new(STDOUT)
config.logger.level = Logger::INFO
```

For teams running [self-hosted email marketing with Listmonk or Mautic](../self-hosted-email-marketing-listmonk-mautic-postal-guide/), integrating email verification into your subscriber import pipeline reduces bounce rates from day one.

## FAQ

### What is the difference between email syntax validation and SMTP verification?

Syntax validation only checks whether an email address is properly formatted (e.g., contains `@`, valid domain structure). SMTP verification goes further by connecting to the target mail server and checking whether the specific mailbox actually exists. Syntax validation takes milliseconds; SMTP verification takes 1-5 seconds per address but is significantly more accurate.

### Can self-hosted email verification tools detect disposable email addresses?

Yes. Truemail supports custom blacklist files, AfterShip email-verifier includes a built-in disposable domain list, and py3-validate-email also checks against known disposable providers. For the most up-to-date lists, use community-maintained repositories like `martenson/disposable-email-domains` which are updated regularly.

### Is SMTP email verification legal?

SMTP verification uses the standard `RCPT TO` command followed by `QUIT` — the same protocol any mail server uses to deliver messages. It does not send an actual email. This is considered legitimate use of the SMTP protocol. However, excessive probing from a single IP may trigger rate limiting or blocking by target mail servers, so implement delays between requests.

### How many emails per hour can Truemail verify?

With default timeouts (2 seconds connection + 2 seconds response), Truemail can verify approximately 900 emails per hour per worker. Running multiple truemail-rack instances behind a load balancer scales this linearly. For bulk verification of large lists, consider running verification as a background job with queued processing.

### Which tool is fastest for bulk email verification?

AfterShip email-verifier (Go) is the fastest in terms of raw verification speed due to Go's compiled performance and efficient goroutine-based concurrency. For bulk operations, combine it with Go's worker pool pattern to process thousands of emails concurrently. py3-validate-email with async support is a close second for Python-based pipelines.

### Can I use these tools with my existing self-hosted email server?

Absolutely. These verification tools are independent of your mail server. They work with Postfix, Dovecot, Stalwart, Mailcow, or any other SMTP server. In fact, integrating verification with your [self-hosted email infrastructure](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) is the recommended approach for complete email quality control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Verification: Truemail vs AfterShip vs py3-validate-email (2026)",
  "description": "Compare the best self-hosted email verification tools — Truemail, AfterShip email-verifier, and py3-validate-email — with Docker setup guides, feature comparisons, and deployment best practices for 2026.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
