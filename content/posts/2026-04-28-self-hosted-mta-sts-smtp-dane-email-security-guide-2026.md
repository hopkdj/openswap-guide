---
title: "Self-Hosted MTA-STS & SMTP DANE: Complete Email Security Guide 2026"
date: 2026-04-28T08:00:00Z
tags: ["comparison", "guide", "self-hosted", "email", "security", "tls", "smtp"]
draft: false
description: "Complete guide to deploying MTA-STS and SMTP DANE for self-hosted email servers. Prevent SMTP man-in-the-middle attacks with DNS-based TLS enforcement."
---

## Why Self-Host MTA-STS and SMTP DANE?

SMTP email delivery has a fundamental vulnerability: the initial connection between mail servers typically negotiates TLS opportunistically. An attacker performing a man-in-the-middle (MITM) attack can strip the TLS upgrade during the SMTP handshake (a "STARTTLS downgrade attack") and intercept email in plaintext. This has been demonstrated against major providers and is a well-documented risk.

MTA-STS (Mail Transfer Agent Strict Transport Security) and SMTP DANE (DNS-based Authentication of Named Entities) solve this problem by allowing domain owners to **publish policies that mandate encrypted email delivery**. When both sender and receiver implement these protocols, email traffic between your servers and theirs is guaranteed to be encrypted — and if encryption fails, the message is rejected rather than delivered insecurely.

For anyone running a self-hosted mail server with Postfix, Stalwart, Haraka, or any other MTA, implementing MTA-STS and DANE is one of the highest-impact security improvements you can make. If you're setting up a mail server from scratch, check out our [complete email server guide with Postfix, Dovecot, and Rspamd](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) first, then return here to add MTA-STS and DANE hardening. It ensures your outbound mail is always encrypted in transit and that inbound mail from other MTA-STS/DANE-supporting servers reaches you over verified TLS connections.

## MTA-STS vs SMTP DANE: How They Compare

MTA-STS and DANE achieve similar goals through different mechanisms. Understanding the distinction is key to choosing the right approach for your infrastructure.

| Feature | MTA-STS | SMTP DANE |
|---------|---------|-----------|
| **Mechanism** | HTTPS policy file + DNS TXT record | DNS TLSA record |
| **Requires** | Valid TLS certificate on `mta-sts.yourdomain.com` | DNSSEC-signed zone |
| **Policy Location** | `https://mta-sts.yourdomain.com/.well-known/mta-sts.txt` | TLSA record in DNS zone |
| **Trust Model** | TLS certificate authority (CA) | DNSSEC chain of trust |
| **Deployment Complexity** | Low to moderate | Moderate (requires DNSSEC) |
| **Policy Flexibility** | Enforce, Testing, None modes | Certificate matching (SPKI, cert) |
| **Adoption** | Growing (Gmail, Yahoo, Microsoft support) | Established (Postfix, Exim support) |
| **Fallback** | DNS TXT record indicates policy exists | DNSSEC validation required |
| **Best For** | Domains with TLS certificates and web hosting | Domains with DNSSEC-enabled DNS |

### MTA-STS Explained

MTA-STS works by publishing two pieces of information:

1. A **DNS TXT record** at `_mta-sts.yourdomain.com` indicating that a policy exists
2. An **HTTPS-hosted policy file** at `https://mta-sts.yourdomain.com/.well-known/mta-sts.txt` specifying which MX hosts require TLS and what the minimum TLS version is

When a sending MTA looks up your domain, it checks for the MTA-STS DNS record. If found, it fetches the policy file over HTTPS and enforces TLS requirements for delivery.

### SMTP DANE Explained

DANE takes a different approach. It uses DNS TLSA records to publish the expected TLS certificate (or public key) for your mail server. The sending MTA validates:

1. DNSSEC-signed DNS response for the TLSA record
2. TLS certificate presented by the receiving server matches the TLSA record
3. If validation fails, delivery is rejected

DANE does not require a separate HTTPS endpoint — everything is published directly in DNS. However, it **requires your DNS zone to be DNSSEC-signed**, which adds operational complexity.

## Deploying MTA-STS: Step-by-Step

### Step 1: Create the MTA-STS DNS TXT Record

Add the following TXT record to your DNS zone:

```dns
_mta-sts.example.com. IN TXT "v=STSv1; id=2026042801;"
```

The `id` field is a policy version identifier. Increment it (e.g., `2026042802`) whenever you update the policy file. Use a timestamp or sequential number.

### Step 2: Set Up the MTA-STS Subdomain

You need a subdomain `mta-sts.yourdomain.com` that serves the policy file over HTTPS. This requires:

- A DNS A/AAAA record for `mta-sts.example.com`
- A valid TLS certificate covering `mta-sts.example.com` (a wildcard cert for `*.example.com` works)

For automated TLS certificate provisioning, see our [cert-manager vs Lego vs ACME.sh guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) to set up Let's Encrypt certificates.

Create the DNS record:

```dns
mta-sts.example.com. IN A 203.0.113.10
mta-sts.example.com. IN AAAA 2001:db8::10
```

### Step 3: Create the MTA-STS Policy File

The policy file must be served at `https://mta-sts.yourdomain.com/.well-known/mta-sts.txt`:

```
version: STSv1
mode: enforce
mx: mail.example.com
mx: mail2.example.com
max_age: 86400
```

**Policy fields explained:**

- `version`: Always `STSv1`
- `mode`: 
  - `enforce` — reject delivery if TLS requirements cannot be met (use this in production)
  - `testing` — log failures but do not reject (use during deployment)
  - `none` — disable policy (for emergency rollback)
- `mx`: Each MX hostname that requires TLS enforcement
- `max_age`: Cache duration in seconds (recommended: 86400 = 24 hours, max: 604800 = 7 days)

### Step 4: Serve the Policy File via Nginx

Here's a minimal Nginx configuration to serve the MTA-STS policy file:

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mta-sts.example.com;

    ssl_certificate /etc/letsencrypt/live/mta-sts.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mta-sts.example.com/privkey.pem;

    # Only serve the MTA-STS policy file
    location = /.well-known/mta-sts.txt {
        alias /var/www/mta-sts/mta-sts.txt;
        default_type text/plain;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Strict-Transport-Security "max-age=31536000" always;
    }

    # Deny everything else
    location / {
        return 404;
    }
}
```

Create the directory and policy file:

```bash
sudo mkdir -p /var/www/mta-sts/.well-known
sudo cp /path/to/mta-sts.txt /var/www/mta-sts/.well-known/
sudo chmod 644 /var/www/mta-sts/.well-known/mta-sts.txt
```

### Step 5: Serve via Caddy (Simpler Alternative)

Caddy handles TLS automatically and provides a simpler configuration:

```caddy
mta-sts.example.com {
    header {
        Strict-Transport-Security "max-age=31536000"
        Content-Type "text/plain"
    }

    handle /.well-known/mta-sts.txt {
        respond "version: STSv1\nmode: enforce\nmx: mail.example.com\nmax_age: 86400\n" 200
    }

    handle {
        respond "Not Found" 404
    }
}
```

With a Docker Compose deployment:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

### Step 6: Validate Your MTA-STS Deployment

Use the [MTA-STS Validator](https://hardenize.com) or test with `curl`:

```bash
# Verify DNS record
dig +short TXT _mta-sts.example.com
# Expected: "v=STSv1; id=2026042801;"

# Verify HTTPS policy file
curl -sI https://mta-sts.example.com/.well-known/mta-sts.txt
# Should return: HTTP/2 200, Content-Type: text/plain

# Verify content
curl -s https://mta-sts.example.com/.well-known/mta-sts.txt
# Should show your policy
```

### Step 7: Configure Your MTA for MTA-STS

#### Postfix MTA-STS Configuration

Postfix 3.4+ supports MTA-STS via the `smtp_tls_security_level` setting. For Postfix 3.6+:

```bash
# /etc/postfix/main.cf
smtp_tls_security_level = dane
smtp_dns_support_level = dnssec
smtp_tls_mandatory_protocols = >=TLSv1.2
smtp_tls_loglevel = 1

# MTA-STS support requires postscreen or additional configuration
# Postfix 3.6+ includes native MTA-STS support via:
smtp_mta-sts_policy = enforce
smtp_mta-sts_responder = mta-sts.example.com
```

#### Stalwart Mail Server

Stalwart has built-in MTA-STS support. For a comparison of Stalwart with other SMTP relay options, see our [Postal vs Stalwart vs Haraka guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/). Enable MTA-STS in the configuration:

```toml
# /opt/stalwart-imap/etc/config.toml
[session.inbound.mta-sts]
enabled = true
mode = "enforce"

[session.outbound.mta-sts]
enabled = true
policy-check = true
```

Deploy via Docker Compose:

```yaml
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    ports:
      - "25:25"
      - "587:587"
      - "993:993"
    volumes:
      - ./data:/opt/stalwart-imap/data
      - ./config:/opt/stalwart-imap/etc
      - ./certs:/opt/stalwart-imap/etc/certs
    environment:
      - SERVER_HOSTNAME=mail.example.com
    restart: unless-stopped
```

## Deploying SMTP DANE: Step-by-Step

### Step 1: Enable DNSSEC on Your Zone

DANE requires DNSSEC. If your DNS provider doesn't support DNSSEC, consider switching to one that does (Cloudflare, Amazon Route 53, or self-hosted PowerDNS).

For PowerDNS with DNSSEC:

```bash
# Enable DNSSEC for your zone
pdnsutil secure-zone example.com

# Verify DNSSEC is active
pdnsutil check-zone example.com
```

### Step 2: Obtain Your Mail Server TLS Certificate Hash

Generate the SHA256 hash of your mail server's TLS public key:

```bash
# Extract public key from your certificate
openssl x509 -in /etc/ssl/certs/mail.example.com.pem -pubkey -noout | \
  openssl pkey -pubin -outform DER | \
  openssl dgst -sha256 -binary | \
  openssl enc -base64
```

This produces a base64-encoded SHA256 hash, for example: `dQw4W9XgX9Kj7LmN3OpQ5RsT8UvW2XyZ4AbC6DeFgHi=`

### Step 3: Create the TLSA DNS Record

Add a TLSA record to your DNS zone for your MX hostname:

```dns
_25._tcp.mail.example.com. IN TLSA 3 0 1 dQw4W9XgX9Kj7LmN3OpQ5RsT8UvW2XyZ4AbC6DeFgHi=
```

**TLSA record format: `usage selector matching-type certificate-association-data`**

- `usage` (3): DANE-EE (Domain Issued Certificate) — validates the exact certificate
- `selector` (0): Full certificate (use `1` for SubjectPublicKeyInfo only)
- `matching-type` (1): SHA256 hash (use `0` for exact match, `2` for SHA512)
- `certificate-association-data`: The base64-encoded hash from step 2

### Step 4: Verify DANE Records

```bash
# Query TLSA record
dig +short TLSA _25._tcp.mail.example.com
# Expected: 3 0 1 <hash>

# Verify DNSSEC signing
dig +dnssec +short TLSA _25._tcp.mail.example.com
# Should return RRSIG records alongside TLSA
```

### Step 5: Configure Postfix for DANE

```bash
# /etc/postfix/main.cf
# Outbound: validate DANE for remote servers
smtp_tls_security_level = dane
smtp_dns_support_level = dnssec

# Inbound: require TLS from remote senders
smtpd_tls_security_level = may
smtpd_tls_received_header = yes

# TLS protocol requirements
smtp_tls_mandatory_protocols = >=TLSv1.2
smtpd_tls_mandatory_protocols = >=TLSv1.2
smtp_tls_mandatory_ciphers = high
```

### Step 6: Deploy DNSSEC with Docker

For self-hosted DNSSEC management with PowerDNS:

```yaml
services:
  pdns:
    image: pschiffe/pdns-mysql:4.9
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8081:8081"
    environment:
      - PDNS_master=yes
      - PDNS_api=yes
      - PDNS_api_key=your-api-key
      - PDNS_webserver=yes
      - PDNS_webserver_address=0.0.0.0
      - PDNS_webserver_password=webserver-password
      - PDNS_default_ttl=3600
      - PDNS_default_soa_mail=admin.example.com
      - PDNS_dnssec=yes
      - PDNS_dnssec_algorithm=ecdsa256
    volumes:
      - pdns_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  pdns_data:
```

## MTA-STS vs DANE: Which Should You Deploy?

In an ideal world, you would deploy **both**. They complement each other and provide defense in depth. However, here's how to decide:

### Choose MTA-STS if:

- You already have TLS certificates for your mail server
- You don't have DNSSEC on your DNS zone
- You want a simpler deployment path
- Your audience includes Gmail, Yahoo, and Microsoft 365 users

### Choose DANE if:

- Your DNS zone is already DNSSEC-signed
- You want certificate validation without a CA dependency
- You need fine-grained control over which certificates are accepted
- You prefer a purely DNS-based solution

### Deploy Both for Maximum Protection

The two protocols are not mutually exclusive. MTA-STS provides a policy-based approach that works without DNSSEC, while DANE provides cryptographic certificate validation via DNSSEC. When both are deployed:

- Receivers that support MTA-STS will enforce TLS based on your published policy
- Receivers that support DANE will validate your certificate against DNS records
- If one validation mechanism fails, the other may still succeed

## Monitoring and TLS Reporting

Both MTA-STS and DANE support TLS reporting (RFC 8460), which sends aggregate reports about TLS connection failures to a designated email address.

### Set Up TLS-RPT DNS Record

```dns
_smtp._tls.example.com. IN TXT "v=TLSRPTv1; rua=mailto:tls-reports@example.com"
```

### Process TLS Reports

TLS reports are JSON-formatted aggregate reports sent daily. You can process them with:

```bash
# Example: Parse a TLS-RPT JSON report
cat tls-report.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for policy in data.get('policies', []):
    domain = policy.get('policy-type', 'unknown')
    summary = policy.get('summary', {})
    print(f\"Policy: {domain}\")
    print(f\"  Total sessions: {summary.get('total-successful-session-count', 0)}\")
    print(f\"  Failures: {summary.get('total-failure-count', 0)}\")
"
```

For self-hosted report processing, consider deploying a simple Python service that receives and stores reports:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

class TLSReportHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        report = self.rfile.read(content_length)
        data = json.loads(report)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        with open(f'/var/tls-reports/{timestamp}.json', 'wb') as f:
            f.write(report)
        
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8080), TLSReportHandler)
    server.serve_forever()
```

## Troubleshooting Common Issues

### MTA-STS Policy Not Found

```bash
# Check DNS TXT record
dig TXT _mta-sts.example.com +short
# If missing: add the TXT record to your DNS zone

# Check HTTPS policy file
curl -v https://mta-sts.example.com/.well-known/mta-sts.txt
# If 404: verify the file exists at the correct path
# If SSL error: verify TLS certificate covers mta-sts subdomain
```

### DANE TLSA Record Validation Fails

```bash
# Verify TLSA record exists
dig TLSA _25._tcp.mail.example.com +short

# Verify DNSSEC is active
dig DNSKEY example.com +short
# If empty: DNSSEC is not enabled on your zone

# Verify certificate matches TLSA record
openssl s_client -connect mail.example.com:25 -starttls smtp </dev/null 2>/dev/null | \
  openssl x509 -pubkey -noout | \
  openssl pkey -pubin -outform DER | \
  openssl dgst -sha256 -binary | \
  openssl enc -base64
# Compare output with your TLSA record hash
```

### Policy Not Being Cached

```bash
# Check max_age value in policy file
cat /var/www/mta-sts/.well-known/mta-sts.txt
# Ensure max_age is set (recommended: 86400)

# Check HTTP cache headers
curl -sI https://mta-sts.example.com/.well-known/mta-sts.txt | grep -i cache
```

## FAQ

### What is MTA-STS and why do I need it?

MTA-STS (Mail Transfer Agent Strict Transport Security) is a protocol that lets domain owners publish a policy requiring email servers to use TLS encryption when sending mail to their domain. Without MTA-STS, SMTP connections default to opportunistic TLS, meaning an attacker can perform a STARTTLS downgrade attack and intercept email in plaintext. MTA-STS prevents this by mandating TLS and rejecting delivery if encryption cannot be established.

### Do I need DNSSEC for MTA-STS?

No. MTA-STS does not require DNSSEC. It uses a DNS TXT record to indicate that a policy exists, but the policy itself is fetched over HTTPS using standard TLS certificate validation. This makes MTA-STS simpler to deploy than DANE, which does require DNSSEC.

### What's the difference between MTA-STS and DANE?

MTA-STS uses an HTTPS-hosted policy file to specify TLS requirements, while DANE uses DNS TLSA records to validate the exact certificate or public key of the receiving server. MTA-STS requires a valid TLS certificate on a subdomain; DANE requires DNSSEC. Both prevent STARTTLS downgrade attacks but use different trust models.

### Can I use both MTA-STS and DANE together?

Yes, and it's recommended. They provide complementary protection: MTA-STS enforces TLS policy via HTTPS, while DANE validates certificates via DNSSEC. Deploying both gives you defense in depth — if one mechanism has an issue, the other may still protect your email delivery.

### How do I test if my MTA-STS deployment is working?

Use online validators like Hardenize (hardenize.com) or MTA-STS.info to check your deployment. You can also test manually by verifying the DNS TXT record exists (`dig TXT _mta-sts.yourdomain.com`) and the policy file is accessible over HTTPS (`curl https://mta-sts.yourdomain.com/.well-known/mta-sts.txt`). Major email providers like Gmail and Yahoo will automatically begin enforcing your policy once deployed.

### How often should I update my MTA-STS policy?

Update your MTA-STS policy whenever you change MX records, add or remove mail servers, or change TLS certificate configurations. Always increment the `id` field in the DNS TXT record when you update the policy file — this signals to sending servers that they should re-fetch the policy. Start in `testing` mode and switch to `enforce` after confirming no legitimate mail is being rejected.

### What happens if a sending server doesn't support MTA-STS or DANE?

Nothing changes for non-supporting servers. They will deliver email using opportunistic TLS (or plaintext if TLS is unavailable), exactly as they do today. MTA-STS and DANE are strictly additive — they only affect servers that implement these protocols. As adoption grows, an increasing percentage of your inbound email will be verified as encrypted.

### Is MTA-STS supported by major email providers?

Yes. Gmail has supported MTA-STS since 2019. Yahoo, Microsoft 365, and many other providers also support it. As of 2026, the majority of email traffic between major providers already uses MTA-STS enforcement. DANE is widely supported by Postfix and Exim installations, though adoption among large consumer providers is more limited.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MTA-STS & SMTP DANE: Complete Email Security Guide 2026",
  "description": "Complete guide to deploying MTA-STS and SMTP DANE for self-hosted email servers. Prevent SMTP man-in-the-middle attacks with DNS-based TLS enforcement.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
