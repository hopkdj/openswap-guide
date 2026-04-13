---
title: "Self-Hosted Leantime: Strategic Project Management Platform 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy", "project-management"]
draft: false
description: "Complete guide to self-hosting Leantime for strategic project management. Docker deployment, configuration, and why it beats commercial tools like Asana and Monday.com."
---

## Why Self-Host Your Project Management Platform?

Commercial project management platforms like Asana, Monday.com, and ClickUp charge escalating per-user subscription fees, gate essential features behind expensive tiers, and store every detail of your workflows, strategies, and timelines on their servers. Self-hosting flips this model entirely:

- **Zero per-seat pricing** — onboard your entire organization without licensing costs scaling with headcount
- **Complete data sovereignty** — project plans, strategic documents, and milestone data never leave your infrastructure
- **Unlimited projects and workspaces** — run hundreds of concurrent initiatives without artificial caps
- **Full customization** — modify the platform to match your methodology instead of reshaping your methodology to fit the tool
- **Deep integrations** — connect directly to your self-hosted Git server, CI/CD pipeline, and internal communication systems
- **No vendor lock-in** — your project history and strategic planning data remain accessible regardless of any company's business decisions

For startups, agencies, research teams, and privacy-focused organizations, a self-hosted project management platform delivers enterprise-grade functionality with complete operational autonomy. This guide covers Leantime, an open-source strategic project management system designed for teams that think in roadmaps, not just task lists.

## What Is Leantime?

Leantime is an open-source project management platform built around strategic planning methodologies rather than simple task tracking. Unlike traditional tools that start with individual to-do items, Leantime starts with business objectives and works downward through ideation, research, and execution. It is particularly well-suited for product teams, agencies, and organizations that need to connect high-level strategy with day-to-day work.

Key differentiators include:

- **Idea boards** — capture, evaluate, and prioritize ideas before they become tasks
- **Research boards** — document user research, competitive analysis, and market data alongside project plans
- **Strategy canvases** — visual frameworks like Lean Canvas and SWOT analysis built directly into the platform
- **Milestone-driven planning** — group tasks into meaningful deliverables rather than flat lists
- **Built-in time tracking** — log effort against tasks and generate utilization reports
- **Retrospectives** — structured review templates for continuous improvement
- **Gantt charts and roadmaps** — visualize timelines and dependencies across projects
- **Multiple project views** — Kanban boards, table views, calendar views, and list views for the same data

Leantime is released under the Affero General Public License (AGPL-3.0), meaning you can self-host it freely and modify the source code to fit your needs.

## Leantime vs Commercial Alternatives

| Feature | Leantime (Self-Hosted) | Asana (Business) | Monday.com (Standard) | ClickUp (Business) |
|---------|------------------------|------------------|----------------------|-------------------|
| **License** | AGPL-3.0 | Proprietary SaaS | Proprietary SaaS | Proprietary SaaS |
| **Cost** | Free (your infrastructure) | $24.99/user/month | $12/user/month | $12/user/month |
| **Data Location** | Your servers | Vendor cloud | Vendor cloud | Vendor cloud |
| **Idea Management** | ✅ Built-in | ❌ Workaround required | ❌ Workaround required | ⚠️ Whiteboards add-on |
| **Research Boards** | ✅ Built-in | ❌ No | ❌ No | ❌ No |
| **Strategy Canvases** | ✅ Lean, SWOT, Business Model | ❌ No | ⚠️ Templates only | ⚠️ Docs only |
| **Gantt Charts** | ✅ Included | ✅ Included | ✅ Included | ✅ Included |
| **Kanban Boards** | ✅ Included | ✅ Included | ✅ Included | ✅ Included |
| **Time Tracking** | ✅ Built-in | ⚠️ Third-party | ⚠️ Third-party | ✅ Built-in |
| **Retrospectives** | ✅ Built-in | ❌ No | ❌ No | ❌ No |
| **API Access** | ✅ REST API | ✅ REST + GraphQL | ✅ API | ✅ REST + GraphQL |
| **Offline Capability** | ⚠️ Web-based | ⚠️ Limited | ⚠️ Limited | ⚠️ Limited |
| **User Limit** | Unlimited | Per-seat billing | Per-seat billing | Per-seat billing |
| **Custom Branding** | ✅ Full | ❌ No | ⚠️ Paid tier only | ⚠️ Paid tier only |

For a team of 20 people, the annual savings are substantial: Asana Business would cost $5,998/year, Monday.com Standard would cost $2,880/year, and ClickUp Business would cost $2,880/year. Leantime costs nothing beyond your server infrastructure — typically $5–20/month for a small VPS.

## System Requirements

Leantime is a PHP-based application with modest resource requirements:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 1 core | 2 cores |
| **RAM** | 512 MB | 1 GB |
| **Storage** | 5 GB | 20 GB+ (for file uploads) |
| **Database** | MySQL 8.0 / MariaDB 10.5 | MySQL 8.0 / MariaDB 10.11 |
| **PHP** | 8.1 | 8.3 |
| **Web Server** | Apache 2.4 / NGINX | NGINX with PHP-FPM |

For a team of up to 50 users, a $6/month VPS with 2 vCPUs and 2 GB RAM handles Leantime comfortably alongside the database.

## Deployment with Docker Compose

The fastest way to deploy Leantime is with Docker Compose. This setup runs Leantime alongside a MariaDB database with persistent volumes and automatic restart policies.

Create a directory for your deployment:

```bash
mkdir -p ~/leantime && cd ~/leantime
```

Create the `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  leantime-db:
    image: mariadb:11
    container_name: leantime-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: leantime
      MYSQL_USER: leantime
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5

  leantime:
    image: leantime/leantime:latest
    container_name: leantime
    restart: unless-stopped
    depends_on:
      leantime-db:
        condition: service_healthy
    ports:
      - "8080:80"
    environment:
      LEAN_DB_HOST: leantime-db
      LEAN_DB_USER: leantime
      LEAN_DB_PASSWORD: ${DB_PASSWORD}
      LEAN_DB_NAME: leantime
      LEAN_EMAIL_USE_SMTP: "true"
      LEAN_EMAIL_RETURN: noreply@yourdomain.com
      LEAN_EMAIL_SMTP_HOSTS: ${SMTP_HOST}
      LEAN_EMAIL_SMTP_USERNAME: ${SMTP_USER}
      LEAN_EMAIL_SMTP_PASSWORD: ${SMTP_PASSWORD}
      LEAN_EMAIL_SMTP_AUTO_TLS: "true"
      LEAN_EMAIL_SMTP_PORT: "587"
      LEAN_EMAIL_SMTP_SECURE: tls
    volumes:
      - leantime-public:/var/www/html/public/userfiles

volumes:
  db-data:
    driver: local
  leantime-public:
    driver: local
```

Create an `.env` file with your credentials:

```bash
# Database credentials
DB_ROOT_PASSWORD=generate-a-strong-root-password
DB_PASSWORD=generate-a-strong-app-password

# SMTP settings for email notifications
SMTP_HOST=smtp.yourdomain.com
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password
```

Generate secure passwords:

```bash
# Generate random passwords
DB_ROOT_PASSWORD=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 32)
echo "DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD" >> .env
echo "DB_PASSWORD=$DB_PASSWORD" >> .env
```

Start the services:

```bash
docker compose up -d
```

Verify the deployment:

```bash
docker compose ps
docker compose logs --tail=20 leantime
```

Leantime will be available at `http://your-server-ip:8080`. On first access, you will be prompted to create an administrator account.

## Production Deployment with NGINX Reverse Proxy

For production use, place Leantime behind an NGINX reverse proxy with TLS termination. This setup adds HTTPS, security headers, and connection buffering.

Install NGINX and obtain a TLS certificate:

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d projects.yourdomain.com
```

Create the NGINX configuration at `/etc/nginx/sites-available/leantime`:

```nginx
server {
    listen 443 ssl http2;
    server_name projects.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/projects.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/projects.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data:; img-src 'self' data: blob: https:; font-src 'self' data: https:;" always;

    # Upload size limit (adjust as needed)
    client_max_body_size 50M;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Block access to sensitive paths
    location ~ /\.(env|git|ht) {
        deny all;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name projects.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

Enable the site and reload NGINX:

```bash
sudo ln -s /etc/nginx/sites-available/leantime /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Update your Docker Compose to bind to localhost only:

```yaml
    ports:
      - "127.0.0.1:8080:80"
```

Then restart:

```bash
docker compose down && docker compose up -d
```

## Configuring Leantime for Your Team

### Setting Up Your First Project

After logging in as administrator, follow this workflow to configure your workspace:

1. **Create a project** — Click "Add Project" and enter the project name, description, and start date
2. **Define milestones** — Go to Milestones and create deliverable-based milestones with target dates
3. **Set up the idea board** — Navigate to Ideas and populate it with initial concepts, feature requests, and strategic initiatives
4. **Configure the research board** — Add user research findings, competitive analysis, and market data to the Research section
5. **Add team members** — Go to Settings > Users and invite team members with appropriate roles (Administrator, Editor, Commenter, or Reader)
6. **Create your first sprint** — Under the Kanban board, set up a sprint with a defined start and end date

### Using Strategy Canvases

Leantime includes several built-in strategic frameworks. Access them from the left sidebar under "Strategy":

- **Lean Canvas** — Fill in Problem, Solution, Key Metrics, Unique Value Proposition, Channels, Customer Segments, Cost Structure, and Revenue Streams on a single page
- **SWOT Analysis** — Document Strengths, Weaknesses, Opportunities, and Threats for any project or initiative
- **Business Model Canvas** — Map out the complete business model including Key Partners, Key Activities, Key Resources, and Value Propositions

Each canvas generates a shareable report that can be exported as PDF for stakeholder presentations.

### Configuring Email Notifications

Leantime sends email notifications for task assignments, comments, deadline reminders, and sprint updates. Ensure SMTP is configured correctly in your `.env` file as shown in the Docker Compose setup above. Test the configuration by assigning a task to a team member and verifying they receive the notification.

For teams using internal mail servers, you can configure Leantime to use a local SMTP relay:

```bash
LEAN_EMAIL_USE_SMTP: "true"
LEAN_EMAIL_RETURN: noreply@yourdomain.com
LEAN_EMAIL_SMTP_HOSTS: localhost
LEAN_EMAIL_SMTP_PORT: "25"
LEAN_EMAIL_SMTP_AUTO_TLS: "false"
```

### Backup and Restore

Regular backups are essential for any self-hosted application. Leantime stores data in two locations: the database and the file upload directory.

Create a backup script:

```bash
#!/bin/bash
# leantime-backup.sh
BACKUP_DIR="/backup/leantime/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Backup the database
docker exec leantime-db mysqldump \
  -u leantime -p"${DB_PASSWORD}" leantime \
  > "$BACKUP_DIR/leantime-db.sql"

# Backup uploaded files
docker cp leantime:/var/www/html/public/userfiles "$BACKUP_DIR/userfiles"

# Compress the backup
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

# Keep only last 30 days of backups
find /backup/leantime -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

Make it executable and schedule it with cron:

```bash
chmod +x ~/leantime/leantime-backup.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /root/leantime/leantime-backup.sh") | crontab -
```

Restore from a backup:

```bash
# Stop Leantime
docker compose stop leantime

# Restore the database
docker exec -i leantime-db mysql -u leantime -p"${DB_PASSWORD}" leantime < backup/leantime-db.sql

# Restore files
docker cp userfiles leantime:/var/www/html/public/

# Restart
docker compose start leantime
```

## Upgrading Leantime

Leantime releases updates regularly with new features, bug fixes, and security patches. Upgrading is straightforward:

```bash
cd ~/leantime

# Pull the latest image
docker compose pull leantime

# Recreate the container
docker compose up -d leantime

# Verify the new version
docker compose exec leantime cat /var/www/html/version.txt
```

The database schema is migrated automatically on first run after an upgrade. Always create a backup before upgrading:

```bash
./leantime-backup.sh
docker compose pull leantime
docker compose up -d leantime
```

## Performance Tuning

For teams with 50+ concurrent users or large file attachments, consider these optimizations:

### PHP-FPM Configuration

If running without Docker, tune PHP-FPM settings in `/etc/php/8.3/fpm/pool.d/www.conf`:

```ini
pm = dynamic
pm.max_children = 50
pm.start_servers = 10
pm.min_spare_servers = 5
pm.max_spare_servers = 15
pm.max_requests = 500
```

### Database Optimization

Add indexes for frequently queried columns and tune MariaDB:

```sql
-- Add index for task lookups
ALTER TABLE zp_tasks ADD INDEX idx_state_project (state, projectid);
ALTER TABLE zp_tasks ADD INDEX idx_assigned_user (assigned_to, status);
ALTER TABLE zp_todolines ADD INDEX idx_milestone (milestoneid, sorted);
```

In `my.cnf`, increase the buffer pool for dedicated database servers:

```ini
[mysqld]
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
max_connections = 100
query_cache_size = 64M
```

### File Storage

For teams with heavy file attachment usage, mount a separate volume for uploads:

```yaml
    volumes:
      - /mnt/storage/leantime-files:/var/www/html/public/userfiles
```

Consider offloading to S3-compatible storage using a tool like `s3fs` or `rclone mount` for very large deployments.

## Troubleshooting

### Database Connection Errors

If Leantime cannot connect to the database after a restart:

```bash
# Check database health
docker compose exec leantime-db mysqladmin -u leantime -p status

# Verify the database container is healthy
docker compose ps leantime-db

# Check database logs
docker compose logs leantime-db
```

### Email Not Sending

If notifications are not being delivered:

```bash
# Test SMTP connectivity
docker compose exec leantime bash -c "echo 'EHLO test' | nc -w 5 ${SMTP_HOST} 587"

# Check Leantime mail logs
docker compose logs leantime | grep -i mail
```

### File Upload Failures

If file uploads fail or timeout:

```bash
# Check volume permissions
docker exec leantime ls -la /var/www/html/public/userfiles

# Verify PHP upload limits
docker exec leantime php -r "echo ini_get('upload_max_filesize');"
docker exec leantime php -r "echo ini_get('post_max_size');"
```

### High Memory Usage

Monitor and limit resource consumption:

```bash
# Set Docker memory limits in docker-compose.yml
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

## Migration from Other Tools

Leantime provides import functionality for migrating from other project management systems:

- **CSV import** — Export tasks from any tool as CSV and import via the Tasks > Import menu
- **Asana migration** — Use Asana's CSV export, then map columns to Leantime fields during import
- **Trello migration** — Export board data via Trello's JSON export, then use a conversion script to transform cards into Leantime tasks with milestones
- **Jira migration** — Export issues as CSV from Jira, ensuring the CSV includes status, assignee, priority, and description fields

For complex migrations involving multiple projects with custom fields, consider a phased approach: migrate completed projects as read-only archives, then start fresh with active projects in Leantime.

## Conclusion

Leantime fills a distinct niche in the self-hosted project management landscape. While tools like Vikunja and Taiga excel at task tracking and Kanban workflows, Leantime is designed for teams that need to connect strategic planning with execution. The built-in idea boards, research boards, and strategy canvases provide a structured framework for going from concept to delivery without switching between multiple tools.

Combined with the zero per-seat pricing model, complete data ownership, and straightforward Docker deployment, Leantime is a compelling choice for product teams, agencies, and organizations that want enterprise-grade project management without the enterprise price tag or the privacy compromises of cloud-hosted solutions.
