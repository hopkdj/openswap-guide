---
title: "Best Self-Hosted CAPTCHA Alternatives to reCAPTCHA in 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted and privacy-friendly CAPTCHA alternatives including mCaptcha, Cloudflare Turnstile, hCaptcha, and DIY solutions with Docker setup instructions."
---

Google reCAPTCHA has been the default bot-protection choice for over a decade. But in 2026, privacy regulations, GDPR enforcement, and growing distrust of Google's data-collection practices make it a liability for many website owners. If you run a self-hosted stack, relying on an external Google service contradicts the entire philosophy of keeping your data under your own control.

This guide covers the best self-hosted and privacy-respecting CAPTCHA alternatives available today, complete with [docker](https://www.docker.com/) deployment instructions, integration examples, and a detailed comparison to help you pick the right solution.

## Why Replace reCAPTCHA in 2026

There are several compelling reasons to move away from Google reCAPTCHA:

### Privacy and GDPR Compliance

reCAPTCHA loads scripts from `google.com` and `gstatic.com` domains, sending visitor IP addresses, browser fingerprints, mouse movements, and behavioral data to Google's servers. Under GDPR, this constitutes personal data processing that requires explicit user consent. Many European websites have been fined for loading reCAPTCHA without proper consent banners.

Self-hosted alternatives keep all data within your infrastructure. No third-party cookies, no cross-site tracking, no Google Analytics-adjacent data harvesting.

### Performance Impact

reCAPTCHA adds significant page weight. The v3 script alone is roughly 35KB gzipped, and the challenge widget can add another 100KB+ of JavaScript, CSS, and iframe resources. For privacy-conscious users running script blockers, the widget often breaks entirely, locking them out of your forms.

Lightweight self-hosted solutions typically load under 10KB and don't depend on external CDNs.

### Reliability and Vendor Lock-in

When Google's reCAPTCHA service experiences an outage, every form on your site stops working. You have zero control over uptime, rate limits, or policy changes. Google has already deprecated reCAPTCHA v1 and v2 Invisible at various points, forcing migrations on developers.

Self-hosted solutions run on your own servers with no external dependencies.

### Accessibility

Many CAPTCHA systems are notoriously difficult for users with visual or motor impairments. Audio alternatives are often unintelligible, and visual puzzles can be impossible to solve for certain disabilities. Modern privacy-friendly alternatives use behavioral signals or simple logic puzzles that are far more accessible.

## mCaptcha — Fully Open-Source and Self-Hosted

[mCaptcha](https://mcaptcha.org/) is a proof-of-work based CAPTCHA system that is 100% open-source (AGPL-3.0) and designed to be self-hosted. Instead of presenting visual puzzles, it challenges the browser to solve a computational puzzle — something that is trivial for a real browser but expensive for automated bots.

### How It Works

When a user visits a form, mCaptcha issues a computational challenge (a hash preimage problem). The browser solves it in the background using JavaScript, typically taking 1-3 seconds for a human user's device. Bots would need to solve millions of these to mount a meaningful attack, which is computationally infeasible.

No images, no audio, no behavioral tracking — just math.

### Docker Deployment

```yaml
version: "3.8"

services:
  mcaptcha:
    image: mcaptcha/mcaptcha:latest
    container_name: mcaptcha
    restart: unless-stopped
    ports:
      - "7860:7860"
    environment:
      MCAPTCHA_db_URL: "postgres://mcaptcha:mcaptcha@mcaptcha_db:5432/mcaptcha"
      MCAPTCHA_secret: "your-super-secret-key-change-this"
      MCAPTCHA_siteURL: "https://mcaptcha.example.com"
    depends_on:
      mcaptcha_db:
        condition: service_healthy
    networks:
      - mcaptcha_net

  mcaptcha_db:
    image: postgres:16-alpine
    container_name: mcaptcha_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: mcaptcha
      POSTGRES_PASSWORD: mcaptcha
      POSTGRES_DB: mcaptcha
    volumes:
      - mcaptcha_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mcaptcha"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - mcaptcha_net

  mcaptcha_cache:
    image: redis:7-alpine
    container_name: mcaptcha_cache
    restart: unless-stopped
    networks:
      - mcaptcha_net

volumes:
  mcaptcha_data:

networks:
  mcaptcha_net:
    driver: bridge
```

Save this as `docker-compose.yml` and run:

```bash
docker compose up -d
```

Your mCaptcha instance will be available at `http://localhost:7860`. Place it behind a reverse proxy with TLS for production use.

### Integration Example

Once deployed, integrate mCaptcha into your HTML forms:

```html
<!-- Add the mCaptcha widget -->
<script src="https://mcaptcha.example.com/widget.js" data-sitekey="YOUR_SITE_KEY"></script>

<!-- On form submit, verify the token server-side -->
<!-- Example with Node.js / Express -->
const verify = await fetch("https://mcaptcha.example.com/api/v1/verify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    sitekey: "YOUR_SITE_KEY",
    secret: "YOUR_SECRET_KEY",
    response: token,
  }),
});
const result = await verify.json();
```

### Pros and Cons

| Aspect | Details |
|--------|---------|
| License | AGPL-3.0 (fully open-source) |
| Self-hosted | Yes, complete independence |
| Privacy | No tracking, no data collection |
| Performance | ~8KB widget, no external requests |
| Accessibility | Excellent — no visual/audio challenges |
| Setup com[plex](https://www.plex.tv/)ity | Moderate (requires PostgreSQL) |
| Bot protection | Strong proof-of-work model |
| Mobile support | Works on all modern browsers |

## Cloudflare Turnstile — Free, No Visible Challenge

[Cloudflare Turnstile](https://www.cloudflare.com/products/turnstile/) is a free CAPTCHA alternative that replaces puzzles and image grids with invisible behavioral analysis. While not self-hosted in the strict sense, it is significantly more privacy-friendly than reCAPTCHA and doesn't require users to solve challenges in most cases.

### How It Works

Turnstile analyzes browser signals, TLS fingerprints, and behavioral patterns to distinguish humans from bots. When confidence is high, the user sees nothing — the verification happens silently. Only in edge cases does it present a simple checkbox.

Unlike reCAPTCHA, Turnstile does not use the data for advertising purposes and does not build user profiles across sites.

### Quick Integration

```html
<!-- Add the Turnstile script -->
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>

<!-- Widget in your form -->
<form action="/submit" method="POST">
  <div class="cf-turnstile" data-sitekey="your_site_key"></div>
  <button type="submit">Submit</button>
</form>

<!-- Server-side verification (PHP example) -->
<?php
$secret = "your_secret_key";
$response = $_POST["cf-turnstile-response"];
$remoteip = $_SERVER["REMOTE_ADDR"];

$verify = file_get_contents(
  "https://challenges.cloudflare.com/turnstile/v0/siteverify",
  false,
  stream_context_create([
    "http" => [
      "method" => "POST",
      "header" => "Content-Type: application/x-www-form-urlencoded",
      "content" => http_build_query([
        "secret" => $secret,
        "response" => $response,
        "remoteip" => $remoteip,
      ]),
    ],
  ])
);
$result = json_decode($verify);

if ($result->success) {
  // Human verified — process the form
} else {
  // Verification failed
}
?>
```

### Docker-Based Reverse Proxy Setup

For users who want to proxy Turnstile through their own domain (to avoid loading any Cloudflare domains directly):

```yaml
ver[nginx](https://nginx.org/) "3.8"

services:
  captcha-proxy:
    image: nginx:alpine
    container_name: captcha-proxy
    restart: unless-stopped
    ports:
      - "8443:443"
    volumes:
      - ./proxy.conf:/etc/nginx/conf.d/default.conf
      - ./certs:/etc/nginx/certs:ro
    networks:
      - proxy_net

networks:
  proxy_net:
    driver: bridge
```

With `proxy.conf`:

```nginx
server {
  listen 443 ssl;
  server_name captcha.yourdomain.com;

  ssl_certificate /etc/nginx/certs/cert.pem;
  ssl_certificate_key /etc/nginx/certs/key.pem;

  location /turnstile/ {
    proxy_pass https://challenges.cloudflare.com/turnstile/;
    proxy_set_header Host challenges.cloudflare.com;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location /api/verify {
    proxy_pass https://challenges.cloudflare.com/turnstile/v0/siteverify;
    proxy_set_header Host challenges.cloudflare.com;
    proxy_method POST;
    proxy_set_body $request_body;
  }
}
```

### Pros and Cons

| Aspect | Details |
|--------|---------|
| License | Proprietary (free to use) |
| Self-hosted | No, but proxyable |
| Privacy | No ad profiling, limited data retention |
| Performance | ~15KB, invisible in most cases |
| Accessibility | Good — rarely presents challenges |
| Setup complexity | Low — just add a script tag |
| Bot protection | Strong behavioral analysis |
| Cost | Free up to 1M requests/month |

## hCaptcha — Privacy-First with Self-Hosted Option

[hCaptcha](https://www.hcaptcha.com/) positions itself as a privacy-friendly reCAPTCHA replacement. While their hosted service is the most common deployment model, they also offer an **on-premise/enterprise self-hosted option** for organizations that need full data control.

### How It Works

hCaptcha presents image-selection challenges similar to reCAPTCHA v2, but with stronger privacy guarantees. Their hosted service does not use verification data for advertising, and they offer GDPR-compliant data processing agreements. The enterprise self-hosted version runs entirely within your infrastructure.

### Hosted Quick Start

```html
<script src="https://js.hcaptcha.com/1/api.js" async defer></script>

<form action="/submit" method="POST">
  <div class="h-captcha" data-sitekey="your_site_key"></div>
  <button type="submit">Submit</button>
</form>
```

### Enterprise Self-Hosted Deployment

For the self-hosted enterprise version, hCaptcha provides a Docker-based deployment:

```yaml
version: "3.8"

services:
  hcaptcha-onprem:
    image: hcaptcha/onpremise:latest
    container_name: hcaptcha-onprem
    restart: unless-stopped
    ports:
      - "9090:8080"
    environment:
      HC_LICENSE_KEY: "your-enterprise-license-key"
      HC_DATABASE_URL: "postgres://hcaptcha:password@hcaptcha_db:5432/hcaptcha"
      HC_SECRET_KEY: "your-hmac-secret-key"
    volumes:
      - hcaptcha_models:/models
    depends_on:
      - hcaptcha_db
    networks:
      - hcaptcha_net

  hcaptcha_db:
    image: postgres:16-alpine
    container_name: hcaptcha_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: hcaptcha
      POSTGRES_PASSWORD: password
      POSTGRES_DB: hcaptcha
    volumes:
      - hcaptcha_data:/var/lib/postgresql/data
    networks:
      - hcaptcha_net

volumes:
  hcaptcha_models:
  hcaptcha_data:

networks:
  hcaptcha_net:
    driver: bridge
```

Note: The self-hosted version requires an enterprise license. The hosted version has a generous free tier (1M requests/month).

### Server-Side Verification

```bash
# Verify hCaptcha response with curl
curl https://hcaptcha.com/siteverify \
  -d "secret=YOUR_SECRET" \
  -d "response=USER_TOKEN" \
  -d "remoteip=USER_IP"
```

### Pros and Cons

| Aspect | Details |
|--------|---------|
| License | Proprietary (hosted: free tier; self-hosted: enterprise) |
| Self-hosted | Yes (enterprise license required) |
| Privacy | No ad profiling, GDPR compliant |
| Performance | ~25KB widget |
| Accessibility | Moderate — visual image challenges |
| Setup complexity | Low (hosted), high (self-hosted) |
| Bot protection | Very strong — widely deployed |
| Cost | Free tier available; self-hosted requires license |

## FriendlyCaptcha — Puzzle-Based, Developer-Friendly

[FriendlyCaptcha](https://friendlycaptcha.com/) takes a different approach entirely. Instead of image grids or behavioral analysis, it uses cryptographic puzzles that are solved in the browser. It's designed to be developer-friendly with clean APIs and SDKs for every major framework.

### How It Works

FriendlyCaptcha generates a unique puzzle for each form submission. The browser solves it in the background using WebAssembly for optimal performance. The puzzle takes about 1-2 seconds on modern devices but would take automated bots significantly longer to solve at scale.

### Integration

```html
<script
  src="https://cdn.jsdelivr.net/npm/friendly-challenge@0.9.16/widget.min.js"
  async
  defer
></script>

<form action="/submit" method="POST">
  <div
    class="frc-captcha"
    data-sitekey="your_site_key"
    data-start="auto"
  ></div>
  <button type="submit">Submit</button>
</form>
```

### Self-Hosted Widget Proxy

While the verification API is cloud-hosted, you can self-host the widget assets to eliminate external CDN dependencies:

```bash
# Download and serve the widget locally
mkdir -p /var/www/captcha-widget
cd /var/www/captcha-widget

curl -O https://cdn.jsdelivr.net/npm/friendly-challenge@0.9.16/widget.min.js
curl -O https://cdn.jsdelivr.net/npm/friendly-challenge@0.9.16/widget.min.js.map

# Serve with Caddy
cat > Caddyfile << 'EOF'
captcha-assets.yourdomain.com {
  root * /var/www/captcha-widget
  file_server
  encode gzip
}
EOF

caddy run --config Caddyfile
```

Then reference your local copy:

```html
<script src="https://captcha-assets.yourdomain.com/widget.min.js" async defer></script>
```

### Pros and Cons

| Aspect | Details |
|--------|---------|
| License | Proprietary (free tier for open-source) |
| Self-hosted | Partially (widget can be self-hosted) |
| Privacy | No tracking, GDPR compliant |
| Performance | ~12KB, WebAssembly optimized |
| Accessibility | Excellent — no visual challenges |
| Setup complexity | Low |
| Bot protection | Strong cryptographic puzzles |
| Cost | Free for open-source; paid tiers for commercial |

## DIY CAPTCHA — Build Your Own

For developers who want complete control, building a custom CAPTCHA system is more feasible than ever. Here are three practical approaches:

### Approach 1: Simple Math Challenge

The simplest DIY CAPTCHA generates basic arithmetic problems:

```python
# Python / Flask example
import random
from flask import Flask, render_template_string, request, session

app = Flask(__name__)
app.secret_key = "change-this-to-a-real-secret"

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        a = int(session.get("captcha_a", 0))
        b = int(session.get("captcha_b", 0))
        answer = request.form.get("captcha_answer", "")

        if str(a + b) != answer:
            return "CAPTCHA failed. Please try again.", 400

        # Process the form
        return "Form submitted successfully!"

    # Generate new CAPTCHA
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    session["captcha_a"] = a
    session["captcha_b"] = b

    return render_template_string("""
    <form method="POST">
      <label>What is {{ a }} + {{ b }}?</label>
      <input type="text" name="captcha_answer" required>
      <button type="submit">Submit</button>
    </form>
    """, a=a, b=b)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

While basic, this approach is fully self-hosted, zero-dependency, and respects user privacy. It's suitable for low-traffic sites and internal tools.

### Approach 2: Honeypot + Rate Limiting

A more sophisticated DIY approach combines honeypot fields with rate limiting:

```nginx
# Nginx rate limiting configuration
limit_req_zone $binary_remote_addr zone=contact_form:10m rate=5r/m;

server {
  location /api/contact {
    limit_req zone=contact_form burst=10 nodelay;

    # Proxy to your backend
    proxy_pass http://127.0.0.1:3000;
  }
}
```

```html
<!-- Honeypot field in your form -->
<form action="/api/contact" method="POST">
  <!-- Hidden honeypot — bots will fill it, humans won't see it -->
  <input
    type="text"
    name="website"
    style="display:none"
    tabindex="-1"
    autocomplete="off"
  >

  <label for="message">Message:</label>
  <textarea name="message" required></textarea>

  <button type="submit">Send</button>
</form>
```

```python
# Backend validation
@app.route("/api/contact", methods=["POST"])
def contact():
    # Check honeypot
    if request.form.get("website"):
        return "Bot detected", 403

    # Check timestamp (form should not be submitted instantly)
    submit_time = time.time()
    form_loaded = float(request.form.get("_loaded_at", 0))

    if submit_time - form_loaded < 2:
        return "Too fast — possible bot", 403

    # Process the legitimate form
    return "OK", 200
```

This combination blocks most automated bots without any visual challenges or external services.

### Approach 3: Time-Based Token with HMAC

For a more robust DIY solution, use time-limited HMAC tokens:

```python
import hmac
import hashlib
import time
import os

SECRET = os.environ.get("CAPTCHA_SECRET", "change-me")

def generate_token():
    timestamp = int(time.time())
    message = f"{timestamp}:{SECRET}"
    token = hmac.new(
        SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return f"{timestamp}:{token}"

def verify_token(token, max_age=300):
    try:
        timestamp_str, received_hash = token.split(":", 1)
        timestamp = int(timestamp_str)

        if time.time() - timestamp > max_age:
            return False

        message = f"{timestamp_str}:{SECRET}"
        expected = hmac.new(
            SECRET.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(received_hash, expected)
    except (ValueError, TypeError):
        return False
```

This approach ensures that each form token is unique, time-limited, and tamper-proof. Bots cannot reuse old tokens or forge new ones without knowing the secret.

## Comparison Table

| Feature | mCaptcha | Turnstile | hCaptcha | FriendlyCaptcha | DIY |
|---------|----------|-----------|----------|-----------------|-----|
| **Fully open-source** | Yes | No | No | No | Yes |
| **Self-hosted** | Yes | No (proxyable) | Yes (enterprise) | Partial | Yes |
| **Cost** | Free | Free | Free tier | Free for OSS | Free |
| **Visual challenges** | No | Rarely | Yes | No | Customizable |
| **Data sent to third party** | None | Minimal | Moderate | Minimal | None |
| **GDPR compliant** | Yes | Yes | Yes | Yes | Yes |
| **Setup difficulty** | Medium | Easy | Easy | Easy | Varies |
| **Bot protection strength** | Strong | Very strong | Very strong | Strong | Moderate |
| **Widget size** | ~8KB | ~15KB | ~25KB | ~12KB | <5KB |
| **Mobile friendly** | Yes | Yes | Yes | Yes | Yes |
| **Best for** | Privacy purists | Easy migration | High-traffic sites | Developer experience | Full control |

## Which Should You Choose?

**For maximum privacy and independence:** Deploy **mCaptcha**. It's fully open-source, self-hosted, and keeps all data within your infrastructure. The proof-of-work model is elegant and effective.

**For easy migration from reCAPTCHA:** Use **Cloudflare Turnstile**. It's free, invisible to most users, and the migration is as simple as swapping a script tag. While not self-hosted, it respects privacy far more than Google.

**For enterprise-grade protection:** **hCaptcha's** self-hosted enterprise option provides the strongest bot detection with full data control, though it requires a commercial license.

**For developer experience:** **FriendlyCaptcha** offers the cleanest APIs, best documentation, and free open-source licenses.

**For full control and zero dependencies:** Build a **DIY solution** combining honeypots, rate limiting, and HMAC tokens. It won't stop nation-state actors, but it blocks 99% of automated spam for small to medium sites.

## Final Thoughts

The era of blindly embedding Google reCAPTCHA on every form is over. With mature self-hosted alternatives available, there's no reason to send your visitors' behavioral data to a third-party advertising company. Whether you choose mCaptcha for full independence, Turnstile for simplicity, or a custom DIY solution, your users will benefit from a faster, more private, and more accessible experience.

The best CAPTCHA is the one your users never notice — and that doesn't sell their data.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
