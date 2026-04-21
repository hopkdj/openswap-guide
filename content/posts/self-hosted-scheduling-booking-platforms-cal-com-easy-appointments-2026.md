---
title: "Best Self-Hosted Scheduling Platforms in 2026: Cal.com, Easy!Appointments, and More"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted scheduling and booking platforms in 2026. Compare Cal.com, Easy!Appointments, and other open source Calendly alternatives with Docker setup instructions."
---

## Why Self-Host Your Scheduling Platform

Scheduling is one of the most universal business needs, yet most people hand their calendar data over to proprietary SaaS platforms like Calendly, Acuity Scheduling, or Microsoft Bookings. These services collect your meeting data, attendee information, and behavioral patterns — data that is monetized, analyzed, or potentially leaked in breaches.

Self-hosting a scheduling platform gives you complete control over your appointment data, eliminates per-user subscription costs, removes branding and upsell interruptions, and lets you customize booking flows to match your exact workflow. Whether you run a consulting practice, manage a team of sales reps, operate a clinic, or simply want a privacy-respecting way to share your availability, there is an open source solution that fits.

In this guide, we compare the best self-hosted scheduling and booking platforms available in 2026, provide complete [docker](https://www.docker.com/) deployment instructions, and help you pick the right tool for your use case.

---

## The Landscape: Self-Hosted Scheduling Platforms in 2026

| Platform | Best For | Team Support | Payment Integration | Calendar Sync | Multi-Language |
|----------|----------|--------------|---------------------|---------------|----------------|
| **Cal.com** | Modern teams & developers | Yes | Stripe, PayPal | Google, Outlook, Apple | Yes (20+ languages) |
| **Easy!Appointments** | Service businesses | Yes | No built-in | Google Calendar | Yes (15+ languages) |
| **Amie** (open source clone) | Personal scheduling | No | No | Google, CalDAV | Limited |
| **Chap** | Lightweight booking | No | No | iCal export | English only |
| **Schedulista** alternative (Booked) | Resource booking | Yes | No | LDAP sync | Yes |

---

## Cal.com (formerly Calendso)

Cal.com is the most popular open source scheduling infrastructure. Originally forked as a Calendly alternative, it has grown into a full-featured platform used by thousands of teams. It offers a clean UI, extensive integrations, and an API-first architecture.

### Key Features

- **Event types**: Create multiple booking types (15-min intro, 1-hour deep dive, team meeting) with custom durations, buffers, and availability windows
- **Round-robin scheduling**: Distribute meetings across team members automatically
- **Collective events**: Require multiple participants to be available simultaneously
- **Workflows**: Send automated SMS and email reminders, follow-ups, and confirmations
- **Payment collection**: Integrate Stripe and PayPal to charge for bookings upfront
- **Video conferencing**: Built-in integrations with Google Meet, Zoom, Jitsi, and Daily.co
- **API and webhooks**: Full REST API for programmatic booking management
- **Embeddable booking page**: Embed your scheduling widget on any website

### Docker Deployment

Cal.com requires PostgreSQL and Redis as dependencies. Here is a complete Docker Compose setup:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: cal
      POSTGRES_PASSWORD: cal_secret_password
      POSTGRES_DB: cal
    volumes:
      - cal_postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cal"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redis_secret_password
    volumes:
      - cal_redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis_secret_password", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  calcom:
    image: calcom/cal.com:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://cal:cal_secret_password@postgres:5432/cal
      REDIS_URL: redis://:redis_secret_password@redis:6379
      NEXT_PUBLIC_WEBAPP_URL: http://localhost:3000
      NEXT_PUBLIC_WEBSITE_URL: http://localhost:3000
      CALENDSO_ENCRYPTION_KEY: your-32-char-encryption-key-here
      NEXTAUTH_SECRET: your-nextauth-secret-here
      NEXTAUTH_URL: http://localhost:3000
      # Google Calendar OAuth (optional)
      GOOGLE_API_CREDENTIALS: '{"web":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost:3000/auth/callback/google"]}}'
      # Stripe integration (optional)
      STRIPE_API_KEY: sk_live_your_stripe_key
      STRIPE_WEBHOOK_SECRET: whsec_your_webhook_secret
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  cal_postgres:
  cal_redis:
```

Save this as `docker-compose.yml` and start the stack:

```bash
docker compose up -d
```

After the containers start, open `http://localhost:3000` and create your first account. The initial setup wizard guides you through connecting your calendar and creating your first event type.

### Advanced Configu[caddy](https://caddyserver.com/)n: Reverse Proxy with Caddy

For production use, place Cal.com behind a reverse proxy with TLS:

```
# Caddyfile
cal.yourdomain.com {
    reverse_proxy localhost:3000

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

### Team Setup and Round-Robin

One of Cal.com's strongest features is team scheduling. Here is how to configure round-robin assignment:

1. Navigate to **Settings → Teams → Create Team**
2. Add team members via email invitation
3. Create a new event type and select **Round Robin** as the distribution method
4. Set the **Hosts** — all team members who can take these meetings
5. Configure **Assignment logic**: choose between *maximize fairness* (equal distribution) or *prioritize least recently booked*

For API-based booking management, use the Cal.com REST API:

```bash
# Create a booking via API
curl -X POST https://cal.yourdomain.com/api/v2/bookings \
  -H "Authorization: Bearer cal_live_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "eventTypeId": 123,
    "start": "2026-04-20T14:00:00.000Z",
    "responses": {
      "name": "John Doe",
      "email": "john@example.com",
      "location": { "value": "inPerson" }
    }
  }'
```

### Cal.com Pros and Cons

**Pros:**
- Most feature-complete open source scheduling platform
- Excellent UI that rivals Calendly
- Strong API and webhook ecosystem
- Active development with regular releases
- Supports payments, workflows, and video conferencing out of the box
- Multi-tenant architecture supports SaaS-like deployments

**Cons:**
- Heavier resource footprint (Node.js + PostgreSQL + Redis)
- Some advanced features (workflows, team scheduling) require the paid cloud version
- Setup com[plex](https://www.plex.tv/)ity is higher than simpler alternatives

---

## Easy!Appointments

Easy!Appointments is a mature, PHP-based appointment scheduling system designed for service businesses like salons, clinics, and consulting firms. It has been actively developed since 2013 and is known for its simplicity and reliability.

### Key Features

- **Multi-provider support**: Each staff member has their own calendar and availability
- **Service categories**: Organize offerings into categories with custom durations and pricing
- **Customer self-service**: Clients can book, reschedule, and cancel without admin intervention
- **Google Calendar sync**: Two-way synchronization with Google Calendar
- **Custom fields**: Add appointment-specific fields (phone number, notes, service preferences)
- **Notification emails**: Automatic confirmations and reminders via email
- **Responsive design**: Works on mobile and desktop browsers
- **No heavy dependencies**: Runs on a standard LAMP/LEMP stack

### Docker Deployment

Easy!Appointments runs on Apache with PHP and MySQL. Here is a clean Docker Compose setup:

```yaml
version: "3.8"

services:
  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: root_secret
      MYSQL_DATABASE: easyappointments
      MYSQL_USER: ea_user
      MYSQL_PASSWORD: ea_secret_password
    volumes:
      - ea_mysql:/var/lib/mysql
    command: --default-authentication-plugin=mysql_native_password

  easyappointments:
    image: alexgk/easyappointments:latest
    ports:
      - "8080:80"
    environment:
      DB_HOST: mysql
      DB_NAME: easyappointments
      DB_USER: ea_user
      DB_PASSWORD: ea_secret_password
      BASE_URL: http://localhost:8080
    depends_on:
      - mysql

volumes:
  ea_mysql:
```

Start the service:

```bash
docker compose up -d
```

Access the application at `http://localhost:8080`. The first visit launches the installation wizard. Use these credentials for the database step:

- **Database Host**: `mysql`
- **Database Name**: `easyappointments`
- **Username**: `ea_user`
- **Password**: `ea_secret_password`

After installation, set the admin username and password through the wizard.

### Configuring Services and Providers

The core workflow in Easy!Appointments follows a simple hierarchy:

1. **Services** → Define what you offer (e.g., "Haircut – 30 min", "Consultation – 60 min")
2. **Providers** → Assign staff members to services and set their working hours
3. **Customers** → Clients book online and their data is stored for repeat bookings

To configure a provider's schedule via the admin panel:

1. Go to **Users → Providers → Edit**
2. Set **Working Plan** — define start/end times for each day of the week
3. Add **Breaks** — exclude lunch or personal time
4. Assign **Services** — check which services this provider offers

### Backup and Migration

Easy!Appointments stores all data in MySQL. Here is how to back up:

```bash
# Create a backup
docker compose exec mysql mysqldump \
  -u ea_user -pea_secret_password easyappointments \
  > ea_backup_$(date +%Y%m%d).sql

# Restore from backup
docker compose exec -T mysql mysql \
  -u ea_user -pea_secret_password easyappointments \
  < ea_backup_20260413.sql
```

For file-level backups (uploaded assets, custom configurations):

```bash
docker compose cp easyappointments:/var/www/html/uploads/ ./ea_uploads_backup/
```

### Easy!Appointments Pros and Cons

**Pros:**
- Lightweight — runs on minimal hardware (512 MB RAM is sufficient)
- Simple PHP stack, easy to debug and modify
- No external service dependencies beyond the database
- Mature and stable codebase with over a decade of development
- Well-suited for single-location businesses with multiple staff

**Cons:**
- UI feels dated compared to modern alternatives
- No built-in payment processing
- No video conferencing integration
- No REST API (relies on internal PHP endpoints)
- Limited workflow automation (no SMS reminders, no conditional logic)

---

## Booked (formerly phpScheduleIt)

Booked is a resource scheduling system designed for managing shared resources — conference rooms, equipment, vehicles, lab spaces — rather than personal appointments. If your scheduling needs center around "who gets the thing" rather than "who meets whom," Booked is the right choice.

### Key Features

- **Resource management**: Book rooms, equipment, vehicles with conflict prevention
- **Quotas and limits**: Restrict how many bookings a user can make per period
- **Approval workflows**: Require admin approval for certain resources or time slots
- **Credit-based system**: Assign costs to bookings and give users credit budgets
- **LDAP/Active Directory integration**: Connect to existing directory services
- **Custom attributes**: Add metadata to resources and reservations
- **Email notifications**: Configurable reminders, confirmations, and change alerts

### Docker Deployment

```yaml
version: "3.8"

services:
  mysql:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: booked_root
      MYSQL_DATABASE: booked
      MYSQL_USER: booked
      MYSQL_PASSWORD: booked_pass
    volumes:
      - booked_mysql:/var/lib/mysql

  booked:
    image: linuxserver/booked:latest
    ports:
      - "8090:80"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - DB_HOST=mysql
      - DB_USER=booked
      - DB_PASSWORD=booked_pass
      - DB_NAME=booked
    volumes:
      - booked_config:/config

volumes:
  booked_mysql:
  booked_config:
```

```bash
docker compose up -d
```

Visit `http://localhost:8090` and log in with the default credentials (`admin` / `password`). Change the password immediately after first login.

---

## Comparison: Choosing the Right Platform

| Criterion | Cal.com | Easy!Appointments | Booked |
|-----------|---------|-------------------|--------|
| **Primary use case** | Meeting scheduling | Service appointments | Resource booking |
| **Minimum RAM** | 2 GB | 512 MB | 512 MB |
| **Database** | PostgreSQL | MySQL/MariaDB | MySQL/MariaDB |
| **Tech stack** | Node.js/Next.js | PHP/Apache | PHP |
| **API** | Full REST API | None | Limited REST API |
| **Payments** | Stripe, PayPal | None | None |
| **Video calls** | Built-in (Jitsi, Zoom, Meet) | None | None |
| **Multi-tenant** | Yes | No | No |
| **Mobile-friendly** | Yes (responsive) | Yes (responsive) | Yes (responsive) |
| **License** | AGPL-3.0 | GPL-3.0 | GPL-3.0 |
| **GitHub stars** | 30k+ | 2.5k+ | 700+ |
| **Last release** | Weekly | Monthly | Quarterly |

### Decision Flow

- **You need a Calendly replacement with payments, video calls, and team scheduling** → **Cal.com**
- **You run a service business (salon, clinic, consultancy) and need a simple booking system** → **Easy!Appointments**
- **You need to manage shared resources (rooms, equipment, labs)** → **Booked**
- **You want the lightest possible deployment** → **Easy!Appointments** or **Booked**
- **You need API access and developer extensibility** → **Cal.com**

---

## Migration from Calendly to a Self-Hosted Solution

If you are moving from Calendly, here is a practical migration checklist:

### Step 1: Export Your Calendly Data

Calendly allows data export via **Settings → Account → Export Data**. This gives you a CSV of your event types and bookings.

### Step 2: Recreate Event Types

Map your Calendly event types to the new platform:

```
Calendly → Cal.com mapping:
  "30 Minute Meeting"     → Event Type: "Quick Chat" (30 min)
  "1 Hour Consultation"   → Event Type: "Deep Dive" (60 min)
  "Team Standup"          → Round Robin Event (15 min, assigned to team)
  "Group Workshop"        → Group Event (max 10 attendees)
```

### Step 3: Update Booking Links

Replace all Calendly URLs in your email signatures, website, and marketing materials:

```
# Old
https://calendly.com/yourname/30min

# New
https://cal.yourdomain.com/yourname/quick-chat
```

### Step 4: Test the Full Flow

Before going live, test the complete booking flow:

```bash
# 1. Verify availability shows correctly
curl -s "https://cal.yourdomain.com/api/v2/slots?eventTypeId=1&startTime=2026-04-20&endTime=2026-04-27" | jq '.slots'

# 2. Create a test booking
curl -s -X POST "https://cal.yourdomain.com/api/v2/bookings" \
  -H "Content-Type: application/json" \
  -d '{"eventTypeId": 1, "start": "2026-04-20T10:00:00Z", "responses": {"name": "Test", "email": "test@example.com"}}'

# 3. Confirm the booking email arrived (check your mail server logs)
tail -f /var/log/mail.log | grep "booking"
```

### Step 5: Set Up Monitoring

Add health checks to ensure your scheduling platform stays online:

```yaml
# Add to your docker-compose.yml
  calcom:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

---

## Security Best Practices

Regardless of which platform you choose, follow these security guidelines:

1. **Always use HTTPS** — scheduling data includes email addresses, phone numbers, and meeting details. Never serve booking pages over plain HTTP.

2. **Enable rate limiting** — prevent abuse of your booking API. With Caddy:

```
cal.yourdomain.com {
    reverse_proxy localhost:3000
    handle_path /api/* {
        rate_limit 10 1m
        reverse_proxy localhost:3000
    }
}
```

3. **Rotate API keys regularly** — if your platform supports API keys, rotate them every 90 days and store them in a secrets manager.

4. **Back up your database daily** — scheduling data is business-critical. Automate backups:

```bash
#!/bin/bash
# Daily backup script - add to crontab: 0 2 * * * /opt/backups/cal-backup.sh
BACKUP_DIR="/opt/backups/cal"
mkdir -p "$BACKUP_DIR"
docker compose exec -T postgres pg_dump -U cal cal | gzip > "$BACKUP_DIR/cal_$(date +%Y%m%d_%H%M%S).sql.gz"
# Keep only last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

5. **Isolate the database** — do not expose PostgreSQL or MySQL ports to the public internet. Keep database containers on an internal Docker network.

---

## The Bottom Line

Self-hosting your scheduling platform in 2026 is more practical than ever. Cal.com provides the most complete feature set for teams and developers who need a Calendly-grade experience with full data ownership. Easy!Appointments remains the best choice for service businesses that prioritize simplicity and low resource requirements. Booked fills the niche for organizations that need to manage shared resources rather than personal calendars.

All three platforms are open source, free to self-host, and give you full control over your scheduling data. The right choice depends on your specific use case, technical capacity, and team size — but you no longer need to choose between functionality and privacy.

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
