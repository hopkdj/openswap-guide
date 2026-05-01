---
title: "Self-Hosted Recruiting & ATS: OpenCATS Complete Deployment Guide (2026)"
date: 2026-05-02
tags: ["guide", "self-hosted", "recruiting", "hr", "ats", "deployment"]
draft: false
description: "Deploy OpenCATS, the leading open-source applicant tracking system, on your own infrastructure. Complete guide with Docker Compose setup, configuration, and customization for self-hosted recruiting workflows."
---

Managing recruitment processes through proprietary SaaS platforms means your candidate data lives on someone else's servers, often with limited customization and recurring subscription fees. Self-hosting an applicant tracking system (ATS) gives you full control over candidate data, custom workflows, and zero per-user licensing costs.

This guide walks you through deploying OpenCATS — the most mature open-source ATS — on your own infrastructure, with complete Docker Compose configuration, database setup, and production hardening instructions.

## Why Self-Host Your ATS?

An applicant tracking system manages the entire recruitment pipeline: job postings, candidate applications, resume parsing, interview scheduling, and offer management. Self-hosting provides:

- **Data sovereignty**: Candidate PII stays on your infrastructure — critical for GDPR and data protection compliance
- **Zero per-seat licensing**: No per-recruiter monthly fees regardless of team size
- **Custom workflows**: Tailor the pipeline stages, email templates, and scoring criteria to your process
- **Integration control**: Connect directly to your internal HR systems, email servers, and calendars
- **Long-term cost savings**: One server vs. recurring SaaS subscriptions that scale with headcount

For broader HR system comparisons, see our [OrangeHRM vs IceHRM vs Sentrifugo guide](../2026-04-21-orangehrm-vs-icehrm-vs-sentrifugo-self-hosted-hrms-guide-2026/) covering self-hosted HR management platforms.

## Self-Hosted ATS Landscape

Before diving into OpenCATS, it's worth understanding the broader self-hosted ATS ecosystem. While several platforms exist, most open-source options are either abandoned or designed for narrow use cases.

### Comparison: Open Source ATS Platforms

| Feature | OpenCATS | Vikunja (PM-focused) | Monica CRM |
|---|---|---|---|
| **Primary Focus** | Recruiting & ATS | Project management | Personal CRM |
| **GitHub Stars** | 671 | 9,663 | 22,000+ |
| **Language** | PHP | Go + Vue | PHP |
| **Database** | MySQL/MariaDB | SQLite/PostgreSQL/MySQL | MySQL/PostgreSQL |
| **Docker Support** | Community images | Official image | Official image |
| **Pipeline Stages** | Yes (customizable) | No | Limited |
| **Resume Parsing** | Yes | No | No |
| **Job Order Mgmt** | Yes | No | No |
| **Email Integration** | Yes (SMTP) | No | Limited |
| **REST API** | Yes | Yes | Yes |
| **Multi-user** | Yes (role-based) | Yes | Yes |
| **Best For** | Staffing & HR teams | Task tracking | Relationship tracking |

OpenCATS remains the only purpose-built, actively maintained open-source ATS with full recruitment workflow support. Other platforms like Monica CRM or Vikunja handle related functions (contact management and project tracking) but lack the specialized recruiting features that staffing teams need.

## OpenCATS Overview

[OpenCATS](https://github.com/opencats/OpenCATS) is an open-source ATS and recruitment CRM designed for staffing agencies and internal hiring teams. With over 670 GitHub stars and active development through 2026, it is one of the few self-hosted ATS projects that remains actively maintained.

### Key Features

- **Candidate management**: Store resumes, contact info, notes, and activity history
- **Job order tracking**: Create and manage open positions with custom fields
- **Pipeline workflow**: Customizable stages from application to hire
- **Email integration**: Built-in email client for candidate communication
- **Resume parsing**: Automatic extraction of contact details from uploaded resumes
- **Reporting**: Pipeline analytics, time-to-hire metrics, and source tracking
- **Calendar integration**: Schedule interviews and track availability
- **Role-based access**: Different permissions for recruiters, hiring managers, and admins
- **REST API**: Programmatic access for integrations with external systems

### Architecture

OpenCATS is a PHP/MySQL web application:

- **Frontend**: PHP with HTML/CSS/JavaScript, runs on Apache
- **Database**: MySQL or MariaDB
- **Search**: Built-in MySQL full-text search for resume and candidate queries
- **Email**: SMTP integration for candidate communication
- **File storage**: Local filesystem for resume and document storage

## Docker Compose Deployment

### Prerequisites

- Docker and Docker Compose installed on your server
- A domain name pointed to your server (for TLS certificates)
- 2 GB RAM minimum (more if handling many concurrent users)

### Docker Compose Configuration

Create a directory and deployment file:

```bash
mkdir -p /opt/opencats/{database,files}
cd /opt/opencats
```

```yaml
version: "3.8"
services:
  db:
    image: mariadb:10.11
    container_name: opencats-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: opencats
      MYSQL_USER: opencats
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./database:/var/lib/mysql
    networks:
      - opencats-net
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    image: linuxserver/opencats:latest
    container_name: opencats-app
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - DB_HOST=db
      - DB_NAME=opencats
      - DB_USER=opencats
      - DB_PASS=${DB_PASSWORD}
    volumes:
      - ./files:/config
    ports:
      - "8080:80"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - opencats-net

networks:
  opencats-net:
    driver: bridge
```

### Environment Variables

Create a `.env` file for secure credentials:

```bash
DB_ROOT_PASSWORD=your-secure-root-password
DB_PASSWORD=your-opencats-db-password
```

### Launch the Stack

```bash
docker compose up -d
```

Wait 30-60 seconds for the database to initialize, then visit `http://your-server:8080` to complete the web-based setup wizard.

## Reverse Proxy with TLS

For production use, place OpenCATS behind a reverse proxy with automatic TLS:

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name ats.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ats.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ats.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ats.yourdomain.com/privkey.pem;

    client_max_body_size 20M;  # Allow resume uploads up to 20 MB

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Certbot for TLS

```bash
sudo certbot --nginx -d ats.yourdomain.com
sudo certbot renew --dry-run  # Verify auto-renewal works
```

## Configuration and Customization

### SMTP Setup for Email

Configure SMTP in the OpenCATS admin panel to enable candidate email communication:

```php
// In config.php
define('MAIL_MAILER', 'smtp');
define('MAIL_HOST', 'smtp.yourdomain.com');
define('MAIL_PORT', 587);
define('MAIL_USERNAME', 'recruiting@yourdomain.com');
define('MAIL_PASSWORD', 'your-smtp-password');
define('MAIL_ENCRYPTION', 'tls');
```

### Custom Pipeline Stages

OpenCATS supports customizable pipeline stages per job order:

1. Navigate to **Settings > Pipeline**
2. Add custom stages (e.g., "Phone Screen", "Technical Assessment", "On-site Interview")
3. Set required actions for each stage transition
4. Configure automated email templates for stage changes

### Resume Import

For bulk candidate imports:

1. Go to **Import > Candidates**
2. Upload a CSV with columns: first_name, last_name, email, phone, current_employer
3. Map CSV columns to OpenCATS fields
4. Review and confirm import

### API Integration

OpenCATS provides a REST API for programmatic access:

```bash
# Get all active job orders
curl -s "https://ats.yourdomain.com/api?entityName=JobOrder&action=list&sessionKey=YOUR_SESSION"

# Add a new candidate
curl -s -X POST "https://ats.yourdomain.com/api?entityName=Candidate&action=create&sessionKey=YOUR_SESSION" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Jane", "last_name": "Smith", "email": "jane@example.com"}'
```

## Backup and Maintenance

### Database Backup

```bash
# Automated daily backup via cron
0 2 * * * docker exec opencats-db mysqldump -u opencats -p'${DB_PASSWORD}' opencats | gzip > /backup/opencats-$(date +\%Y\%m\%d).sql.gz
```

### File Backup

```bash
# Backup uploaded resumes and attachments
tar czf /backup/opencats-files-$(date +\%Y\%m\%d).tar.gz /opt/opencats/files/
```

### Updates

```bash
# Pull latest image and restart
cd /opt/opencats
docker compose pull
docker compose up -d
```

## Security Hardening

1. **Firewall**: Only expose ports 80 and 443 externally
2. **Strong passwords**: Use 16+ character passwords for database and admin accounts
3. **HTTPS only**: Never run OpenCATS without TLS — it handles sensitive PII
4. **Rate limiting**: Add fail2ban rules for the login page
5. **Regular backups**: Daily database backups with off-site storage
6. **Access control**: Limit admin panel access to specific IP ranges if possible

## Integration with Existing Tools

OpenCATS can integrate with your existing self-hosted infrastructure:

- **CalDAV calendar**: Link to [Radicale or Baikal](../radicale-vs-baikal-vs-xandikos-self-hosted-calenda/) for interview scheduling
- **Email server**: Connect to your [Stalwart or Postal](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hoste/) mail server for candidate communication
- **Document management**: Store offer letters and contracts in a [Mayan EDMS or Docspell](../2026-04-27-mayan-edms-vs-teedy-vs-docspell-self-hosted-document-management-2026/) system

## FAQ

### Is OpenCATS suitable for small internal HR teams?
Yes. While originally designed for staffing agencies, OpenCATS works well for internal HR teams of any size. You can simplify the interface by hiding staffing-specific features and using the pipeline stages that match your internal hiring process.

### Can OpenCATS handle high-volume recruiting?
OpenCATS can comfortably handle hundreds of active job orders and thousands of candidate records on a modest server (2-4 GB RAM, 2 CPU cores). For enterprise-scale recruiting (10,000+ candidates), consider database optimization or migrating to a more modern stack.

### Does OpenCATS support multi-language interfaces?
OpenCATS supports multiple interface translations. The core is in English, but community-contributed translations exist for Spanish, Portuguese, French, and several other languages. You can also create custom translation files.

### How do I migrate from a SaaS ATS like Greenhouse or Lever?
Most SATS platforms provide CSV export functionality. Export your candidates, job orders, and activity history as CSV files, then use OpenCATS's import tools to migrate the data. Field mapping may be required — plan for a few hours of data cleanup.

### Can I customize the application form that candidates see?
Yes. OpenCATS allows you to add custom fields to the candidate profile and job application. You can also modify the application form template to match your branding and collect additional information like portfolio links, GitHub profiles, or work authorization status.

### Is there a mobile app for OpenCATS?
OpenCATS does not have an official mobile app, but the web interface is responsive and works on mobile browsers. For recruiting on-the-go, the responsive web UI provides access to candidate profiles, pipeline status, and interview scheduling from any device.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Recruiting & ATS: OpenCATS Complete Deployment Guide (2026)",
  "description": "Deploy OpenCATS, the leading open-source applicant tracking system, on your own infrastructure. Complete guide with Docker Compose setup, configuration, and customization for self-hosted recruiting workflows.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
