---
title: "Best Self-Hosted Phishing Simulation Tools: GoPhish vs Alternatives 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "security"]
draft: false
description: "Complete guide to self-hosted phishing simulation and security awareness training platforms. Compare GoPhish, King Phisher, and other open-source tools for running internal security campaigns."
---

Running phishing awareness campaigns inside your organization doesn't require expensive SaaS platforms. Open-source tools like GoPhish, King Phisher, and Social-Engineer Toolkit let you design, launch, and track realistic phishing simulations entirely on your own infrastructure. This guide covers the best self-hosted phishing simulation platforms available in 2026, with full installation instructions and configuration examples.

## Why Self-Host Your Phishing Simulation Platform

Phishing simulations involve sending realistic-looking deceptive emails to employees, tracking who clicks, who enters credentials, and who reports the message. Using a third-party SaaS vendor for this creates several problems:

**Data sovereignty and privacy.** When you use a cloud-based phishing platform, you are sending your employee email addresses, organizational structure, campaign results, and click behavior to a third party. In regulated industries (healthcare, finance, government), this data transfer may violate compliance requirements or internal data governance policies.

**Cost at scale.** SaaS phishing platforms typically charge per-user per-month. For organizations with thousands of employees, annual costs easily exceed $10,000–$30,000. A self-hosted solution runs on a single small VPS or bare-metal server with minimal ongoing costs.

**Full customization.** Self-hosted tools let you clone any landing page, use any sending domain, and customize templates without vendor restrictions. You can integrate with internal identity providers, SIEM systems, and ticketing platforms via local APIs.

**No vendor lock-in.** Your campaign history, templates, and user data remain under your control. Switching between tools or upgrading is entirely your decision.

**Realistic testing.** Self-hosted platforms can send from infrastructure that mirrors real attacker setups more closely than SaaS platforms, which use known sending IPs that spam filters may already flag.

## GoPhish: The Industry Standard

[GoPhish](https://getgophish.com) is the most widely deployed open-source phishing simulation framework. Written in Go, it provides a clean web interface for managing campaigns, email templates, landing pages, and user groups. It tracks opens, clicks, credential submissions, and reporting rates in real time.

### Key Features

- Web-based dashboard with real-time campaign results
- Drag-and-drop email template editor with variable support (`{{.FirstName}}`, `{{.Tracker}}`)
- Clone landing pages from any URL with automatic form capture
- Sending profiles supporting SMTP, SES, and SendGrid
- User group management with CSV import
- Campaign scheduling and automated reporting
- RESTful API for automation and CI/CD integration
- Built-in tracking pixel and click redirect handling

### [docker](https://www.docker.com/) Installation

The fastest way to deploy GoPhish is with Docker Compose. Create a project directory and the following files:

```bash
mkdir -p ~/gophish && cd ~/gophish
```

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  gophish:
    image: gophish/gophish:latest
    container_name: gophish
    restart: unless-stopped
    ports:
      - "3333:3333"   # Admin UI (HTTPS)
      - "80:80"       # HTTP landing pages and click tracking
      - "443:443"     # HTTPS landing pages
    volumes:
      - ./config.json:/opt/gophish/config.json:ro
      - ./db:/opt/gophish/db
      - ./tls:/opt/gophish/tls
    environment:
      - GOPHISH_ADMIN_LISTEN_URL=0.0.0.0:3333
    networks:
      - gophish-net

networks:
  gophish-net:
    driver: bridge
```

Create `config.json`:

```json
{
  "admin_server": {
    "listen_url": "0.0.0.0:3333",
    "use_tls": true,
    "cert_path": "/opt/gophish/tls/cert.pem",
    "key_path": "/opt/gophish/tls/key.pem"
  },
  "phish_server": {
    "listen_url": "0.0.0.0:443",
    "use_tls": true,
    "cert_path": "/opt/gophish/tls/cert.pem",
    "key_path": "/opt/gophish/tls/key.pem"
  },
  "db_name": "sqlite3",
  "db_path": "/opt/gophish/db/gophish.db",
  "migrations_prefix": "db/db_",
  "contact_address": "security@yourdomain.com"
}
```

Generate self-signed certificates (or mount Let's Encrypt certs for production):

```bash
mkdir -p tls
openssl req -x509 -newkey rsa:4096 \
  -keyout tls/key.pem \
  -out tls/cert.pem \
  -days 365 -nodes \
  -subj "/CN=gophish.yourdomain.com"

docker compose up -d
```

On first startup, GoPhish generates a random admin password. Retrieve it from the logs:

```bash
docker logs gophish 2>&1 | grep "password"
```

Navigate to `https://your-server:3333` and log in with username `admin` and the generated password. You will be prompted to change it on first login.

### Configuring a Sending Profile

GoPhish needs an SMTP server to send campaign emails. You can use your own mail server, an internal relay, or a transactional email service. Here is a configuration for a self-hosted Postfix relay:

```yaml
# docker-compose addition for internal Postfix relay
services:
  postfix:
    image: catatnight/postfix
    container_name: gophish-relay
    restart: unless-stopped
    environment:
      - maildomain=yourdomain.com
      - smtp_user=user:password
    ports:
      - "25:25"
    networks:
      - gophish-net
```

Inside GoPhish's web interface, create a sending profile:

- **Name:** Internal Relay
- **Host:** `postfix:25` (or `smtp.yourdomain.com:587` for external)
- **Username/Password:** credentials if required
- **Ignore Certificate Errors:** No (for production)
- Click "Send Test Email" to verify connectivity

### Creating Your First Campaign

1. **Create a Group:** Import employee emails via CSV. Columns should be `First Name`, `Last Name`, `Email`, and optionally `Position`.

2. **Create a Template:** Write a realistic email. Use variables for personalization:

```
Subject: Action Required: Update Your Account Settings

Hello {{.FirstName}},

We have detected unusual activity on your account. Please verify
your identity by clicking the link below within 24 hours:

<a href="{{.URL}}">Verify Your Account</a>

If you did not request this, please ignore this message.

Regards,
IT Security Team
```

3. **Create a Landing Page:** Use the "Import Site" feature to clone a legitimate login page, or build one manually. Enable "Capture Submitted Data" to record credential submissions for reporting purposes.

4. **Launch the Campaign:** Select your group, template, landing page, and sending profile. Choose immediate launch or schedule for a future date.

### API Automation

GoPhish exposes a comprehensive REST API. Here is an example of launching a campaign programmatically:

```bash
#!/bin/bash
# launch-campaign.sh

API_KEY="your-api-key-here"
SERVER="https://gophish.yourdomain.com:3333"

# Create a new campaign
curl -s -X POST "${SERVER}/api/campaigns" \
  -H "Authorization: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q2 Security Awareness Campaign",
    "template": { "name": "Password Reset Template" },
    "url": "https://gophish.yourdomain.com",
    "page": { "name": "Login Clone" },
    "smtp": { "name": "Internal Relay" },
    "groups": [{ "name": "Engineering Team" }],
    "launch_date": "2026-04-20T09:00:00Z"
  }'

echo ""
echo "Campaign launched successfully."
```

You can also fetch results and generate reports:

```bash
# Get campaign results
curl -s "${SERVER}/api/campaigns/1/results" \
  -H "Authorization: ${API_KEY}" \
  | jq '.[] | {email: .email, status: .status}'
```

## King Phisher: The Flexible Alternative

[King Phisher](https://github.com/securestate/king-phisher) takes a different approach from GoPhish. Instead of a monolithic web application, it uses a client-server architecture with a Python-based server and GTK client. It is designed for flexibility and deep customization.

### Key Features

- Client-server architecture with remote deployment support
- Plugin system for extending functionality
- Advanced email threading and reply tracking
- Web server for credential harvesting with customizable templates
- Integration with external threat intelligence feeds
- Detailed campaign analytics and export options
- Support for multi-tenant deployments
- SSH tunneling for secure remote access

### Docker Installation

King Phisher is more com[plex](https://www.plex.tv/) to containerize due to its client-server model, but it can be deployed with Docker:

```yaml
version: "3.8"

services:
  king-phisher-server:
    image: securestate/king-phisher:latest
    container_name: king-phisher-server
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "2222:22"
    volumes:
      - ./server_config.yml:/opt/king-phisher/server_config.yml:ro
      - ./data:/opt/king-phisher/data
      - ./certs:/opt/king-phisher/certs
    environment:
      - KING_PHISHER_DB_URL=postgresql://kingphisher:password@kp-db:5432/kingphisher
    depends_on:
      - kp-db

  kp-db:
    image: postgres:16-alpine
    container_name: kp-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=kingphisher
      - POSTGRES_PASSWORD=secure_password_here
      - POSTGRES_DB=kingphisher
    volumes:
      - pgd[nginx](https://nginx.org/)var/lib/postgresql/data

  kp-web:
    image: nginx:alpine
    container_name: king-phisher-web
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./web_root:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro

volumes:
  pgdata:
```

Create `server_config.yml`:

```yaml
server:
  bind_address: "0.0.0.0"
  port: 2222
  ssl_cert: /opt/king-phisher/certs/server.pem
  ssl_key: /opt/king-phisher/certs/server-key.pem

database:
  connection_string: "postgresql://kingphisher:secure_password_here@kp-db:5432/kingphisher"

webserver:
  enabled: true
  bind_address: "0.0.0.0"
  port: 80
  ssl: true
  ssl_cert: /opt/king-phisher/certs/server.pem
  ssl_key: /opt/king-phisher/certs/server-key.pem

logging:
  level: INFO
  file: /opt/king-phisher/data/king-phisher.log
```

Start the server:

```bash
docker compose up -d
```

The GTK client connects to the server over SSH or direct TCP. On Ubuntu/Debian:

```bash
# Install dependencies
sudo apt install python3-gi python3-gi-cairo python3-cryptography

# Clone and install
git clone https://github.com/securestate/king-phisher-client.git
cd king-phisher-client
pip3 install -r requirements.txt
python3 KingPhisherClient
```

## Social-Engineer Toolkit (SET): The Offensive Framework

[Social-Engineer Toolkit](https://github.com/trustedsec/social-engineer-toolkit) is part of the Kali Linux toolkit and focuses on offensive security testing. While not a dedicated campaign management platform like GoPhish, it provides powerful phishing attack vectors for authorized security assessments.

### When to Use SET

SET is best suited for penetration testing engagements where you need to quickly test specific attack vectors rather than run ongoing awareness campaigns. Key capabilities include:

- Spear-phishing attack generation with custom payloads
- Website attack vectors (credential harvesting, browser exploits, Java applets)
- Infectious media generator for USB-based attacks
- QRCode attack vector generator
- Mass-mailer campaigns
- Third-party module integration (Metasploit, custom payloads)

### Quick Setup

```bash
# On Kali Linux or any Debian-based system
git clone https://github.com/trustedsec/social-engineer-toolkit.git
cd social-engineer-toolkit
pip3 install -r requirements.txt
sudo python3 setup.py install

# Launch
sudo setoolkit
```

The interactive menu guides you through attack selection. For a credential harvesting campaign:

```
Select from the menu:
  1) Social-Engineering Attacks
  2) Penetration Testing (Fast-Track)
  3) Third Party Modules
  4) Update the Social-Engineer Toolkit
  5) Update SET configuration
  6) Help, Credits, and About

set> 1

  1) Spear-Phishing Attack Vectors
  2) Website Attack Vectors
  3) Infectious Media Generator
  4) Create a Payload and Listener
  5) Mass Mailer Attack
  6) Arduino-Based Attack Vector
  7) Wireless Access Point Attack Vector
  8) QRCode Generator Attack Vector
  9) PowerShell Attack Vectors
  10) Third Party Modules

set> 2

  1) Java Applet Attack Method
  2) Metasploit Browser Exploit Method
  3) Credential Harvester Attack Method
  4) Tabnabbing Attack Method
  5) Web Jacking Attack Method
  6) Multi-Attack Web Method
  7) HTA Attack Method
  8) Biased Google Document Attack

set> 3
```

The credential harvester sets up a cloned page that captures entered credentials. SET logs all submissions for later analysis.

## Comparison: GoPhish vs King Phisher vs SET

| Feature | GoPhish | King Phisher | SET |
|---|---|---|---|
| **Primary Use** | Awareness campaigns | Campaign management | Penetration testing |
| **Architecture** | Single binary + web UI | Client-server (GTK + Python) | CLI + Python framework |
| **Web Dashboard** | Yes, built-in | No, separate GTK client | No, terminal-based |
| **Template Editor** | Visual drag-and-drop | Text-based with plugins | Command-line prompts |
| **Landing Page Clone** | Yes, one-click import | Manual setup required | Yes, via harvester |
| **Real-time Tracking** | Opens, clicks, submissions | Full analytics dashboard | Basic logging only |
| **REST API** | Full API with documentation | Limited API | No API |
| **User Management** | Groups, CSV import | Multi-tenant support | None built-in |
| **Email Scheduling** | Yes, cron-style | Yes, flexible scheduling | Manual execution only |
| **Reporting** | Built-in charts + CSV export | Advanced analytics + exports | Manual log review |
| **Database** | SQLite (built-in) | PostgreSQL | File-based logging |
| **Container Support** | Excellent, official image | Community images only | Manual setup |
| **Learning Curve** | Low | Medium | High |
| **Best For** | Ongoing awareness programs | Flexible campaign management | Quick security assessments |

## Choosing the Right Tool

**Choose GoPhish if:** You need to run regular phishing awareness campaigns for employees. It is the easiest to deploy, has the best documentation, and provides everything needed for a complete awareness program. The web interface makes it accessible to non-technical security staff, and the REST API enables automation.

**Choose King Phisher if:** You need multi-tenant support, advanced plugin capabilities, or prefer a client-server architecture with PostgreSQL backing. It is ideal for MSSPs (managed security service providers) running campaigns for multiple clients from a single infrastructure.

**Choose SET if:** You are conducting authorized penetration testing and need rapid attack vector deployment. It integrates with Metasploit for post-exploitation and supports a wider range of attack techniques. However, it is not designed for long-term awareness programs.

## Best Practices for Self-Hosted Phishing Campaigns

### Sending Infrastructure

Your phishing emails need to reach the inbox, not the spam folder. Key steps:

1. **Use a dedicated domain** separate from your production email domain. If attackers spoof `yourcompany.com`, you do not want your simulation domain getting blacklisted.

2. **Configure SPF, DKIM, and DMARC** on your sending domain. Without proper authentication, your campaign emails will be flagged as spam, defeating the purpose of realistic testing.

```bash
# Example DNS records for phishing simulation domain
# TXT record: SPF
"v=spf1 ip4:203.0.113.50 -all"

# TXT record: DKIM (generated via opendkim)
"v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4..."

# TXT record: DMARC
"v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com"
```

3. **Warm up your IP address** before launching large campaigns. Start with small batches (50–100 emails) and gradually increase volume over several days. Sudden high-volume sending from a new IP will trigger spam filters.

4. **Use TLS for sending** wherever possible. Many organizations require encrypted email transport, and unencrypted connections may be blocked.

### Campaign Design

- **Vary timing and templates.** Running the same campaign every quarter with the same email teaches employees to recognize your test, not real phishing. Rotate templates, subjects, and sending times.

- **Test reporting behavior.** Track not only who clicks, but who uses the "Report Phishing" button. This is the most important metric for measuring awareness program effectiveness.

- **Include a teaching moment.** After an employee clicks a simulated phishing link, redirect them to a brief educational page explaining the red flags they missed. This turns failures into learning opportunities.

- **Segment by department.** Different teams face different threats. Finance employees receive invoice fraud attempts; HR receives resume-based phishing; developers receive fake npm or PyPI notifications. Customize campaigns accordingly.

### Legal and Ethical Considerations

- **Get executive approval** before launching any phishing simulation. Ensure your legal team has reviewed the scope, target audience, and data handling procedures.

- **Define clear rules of engagement.** Document which tactics are allowed (credential harvesting, attachment testing) and which are off-limits (targeting executives, using sensitive topics like layoffs).

- **Protect collected data.** Credential submissions from campaigns should be hashed or immediately deleted. Never store actual employee passwords, even from simulations.

- **Comply with local regulations.** In the EU, GDPR applies to processing employee data from campaign results. Document your lawful basis (legitimate interest for security training) and ensure data retention policies are followed.

## Conclusion

Self-hosted phishing simulation platforms offer cost-effective, privacy-preserving alternatives to expensive SaaS solutions. GoPhish remains the best choice for most organizations thanks to its simplicity, active development, and comprehensive feature set. King Phisher serves teams that need multi-tenant flexibility and plugin extensibility, while SET excels for rapid penetration testing engagements.

Whichever tool you choose, the key to a successful awareness program is consistency. Run campaigns regularly, vary your templates and timing, track both click rates and reporting rates, and use results to continuously improve your organization's security posture. Running these tools on your own infrastructure keeps sensitive campaign data under your control and eliminates ongoing per-user licensing costs.

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
