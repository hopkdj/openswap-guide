---
title: "Best Self-Hosted Learning Management Systems 2026: Moodle vs Open edX vs Chamilo"
date: 2026-04-17T07:02:00Z
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare the top open-source learning management systems you can self-host in 2026. Complete Docker deployment guides for Moodle, Open edX, and Chamilo with feature comparison and setup instructions."
---

Running your own learning platform means full control over course content, student data, and pedagogical tools — without per-student licensing fees or data leaving your infrastructure. Self-hosted learning management systems (LMS) are used by universities, corporate training departments, and independent educators worldwide.

In 2026, three open-source LMS platforms dominate the self-hosted space: **Moodle**, the world's most widely deployed LMS; **Open edX**, the enterprise-grade platform built by MIT and Harvard; and **Chamilo**, the lightweight alternative focused on ease of use. This guide compares all three, provides Docker deployment configurations, and helps you choose the right platform for your needs.

## Why Self-Host Your Learning Platform

Cloud-based LMS solutions like Canvas, Blackboard, and Teachable charge per student, per course, or per institution. They also control your data, your integrations, and your feature roadmap. Self-hosting flips that model:

- **Zero per-student costs**: Whether you have 10 students or 10,000, your infrastructure cost is fixed. No surprise bills when enrollment spikes.
- **Complete data ownership**: Student grades, progress records, discussion posts, and assessment data stay on your servers. This matters for GDPR compliance, institutional data policies, and research ethics.
- **Unlimited courses and enrollments**: Create as many courses, enroll as many students, and run as many sessions as your hardware can handle. No tiered pricing plans.
- **Deep customization**: Modify themes, add plugins, integrate with your existing identity providers (LDAP, SAML, CAS), and customize assessment workflows to match your pedagogy.
- **Offline and low-bandwidth operation**: In regions with unreliable internet, a self-hosted LMS on a local server serves content over LAN or a small cellular link without depending on cloud infrastructure in another continent.
- **Long-term course archiving**: Keep courses accessible for years without paying a vendor to maintain them. Export course content to standard formats (SCORM, QTI, Common Cartridge) and reimport whenever needed.

## Moodle: The Universal Standard

[Moodle](https://moodle.org) is the most widely used open-source LMS in the world, powering over 200,000 sites and serving hundreds of millions of learners. It is the default choice for universities, schools, and organizations that need a comprehensive, extensible platform.

### Key Features

- Course management with sections, activities, and resources
- 40+ activity types: quizzes, assignments, forums, wikis, databases, glossaries
- Advanced gradebook with custom calculation formulas and weighted categories
- Question bank with 13 question types and random question selection
- Competency-based education with learning plans and evidence tracking
- H5P interactive content integration (built-in since Moodle 4.x)
- SCORM 1.2 and 2004 package support
- Workshop activity for peer assessment with configurable grading strategies
- Calendar, messaging, and notification system
- Mobile app with offline content access
- Over 2,000 plugins in the official directory
- Multi-language content and interface translation

### Docker Deployment

```yaml
# docker-compose.yml for Moodle
version: "3.8"

services:
  moodle:
    image: bitnami/moodle:4.5
    ports:
      - "8080:8080"
    environment:
      - MOODLE_DATABASE_HOST=moodle-db
      - MOODLE_DATABASE_PORT_NUMBER=3306
      - MOODLE_DATABASE_USER=bn_moodle
      - MOODLE_DATABASE_PASSWORD=moodle_db_pass
      - MOODLE_DATABASE_NAME=bitnami_moodle
      - MOODLE_USERNAME=admin
      - MOODLE_PASSWORD=admin_password
      - MOODLE_EMAIL=admin@example.com
      - MOODLE_SITE_NAME=My Learning Platform
    volumes:
      - moodle-data:/bitnami/moodle
      - moodledata:/bitnami/moodledata
    depends_on:
      - moodle-db

  moodle-db:
    image: bitnami/mariadb:11.4
    environment:
      - ALLOW_EMPTY_PASSWORD=no
      - MARIADB_ROOT_PASSWORD=root_pass
      - MARIADB_USER=bn_moodle
      - MARIADB_PASSWORD=moodle_db_pass
      - MARIADB_DATABASE=bitnami_moodle
    volumes:
      - mariadb-data:/bitnami/mariadb

volumes:
  moodle-data:
  moodledata:
  mariadb-data:
```

```bash
# Start the stack
docker compose up -d

# Wait for initialization (about 2 minutes)
docker compose logs -f moodle

# Access at http://localhost:8080
# Login: admin / admin_password
```

### Essential Post-Installation Configuration

After the initial setup, configure these settings for a production deployment:

```bash
# 1. Set up cron (required for Moodle background tasks)
docker compose exec moodle \
  /opt/bitnami/php/bin/php /opt/bitnami/moodle/admin/cli/cron.php

# Add to host crontab for automated execution:
# */1 * * * * docker compose exec -T moodle /opt/bitnami/php/bin/php /opt/bitnami/moodle/admin/cli/cron.php >/dev/null 2>&1
```

**Recommended settings via the admin interface:**

1. **Site administration → Security → Site security settings**: Enable HTTPS-only cookies, enforce password policies
2. **Site administration → Server → Session handling**: Set session timeout to 4 hours
3. **Site administration → Plugins → Activity modules → Assignment**: Configure submission types and feedback settings
4. **Site administration → Appearance → Additional HTML**: Add custom CSS/JS for branding
5. **Site administration → Server → System paths**: Set paths to `aspell`, `dot`, and `du` if installed

### Moodle's Question Types

Moodle's question bank supports 13 question types out of the box:

| Question Type | Description |
|---------------|-------------|
| Multiple Choice | Single or multiple correct answers |
| True/False | Binary choice questions |
| Matching | Pair items from two columns |
| Short Answer | Free-text response with pattern matching |
| Numerical | Numeric answers with tolerance ranges |
| Calculated | Questions with variables and formulas |
| Essay | Long-form written responses |
| Drag and Drop | Visual matching and ordering |
| Drag and Drop onto Image | Label parts of a diagram |
| Drag and Drop into Text | Fill-in-the-blank with drag items |
| Select Missing Words | Dropdown fill-in-the-blank |
| Embedded Answers (Cloze) | Multiple question types in one passage |
| Description | Informational text (not graded) |

### When to Choose Moodle

Moodle is the right choice for most institutions. It has the largest plugin ecosystem, the most comprehensive feature set, and the biggest community. If you need a platform that can handle everything from K-12 courses to university-level assessments with peer review, competencies, and detailed gradebook calculations, Moodle is the default. The trade-off is that its interface can feel dense — there are hundreds of settings, and the administration interface has a learning curve.

## Open edX: The Enterprise-Scale Platform

[Open edX](https://open.edx.org) was created by MIT and Harvard to deliver massive open online courses (MOOCs) at scale. It is the platform behind edX.org and is used by universities and corporations worldwide for large-scale course delivery. The current release (Dogwood through Palm and beyond) uses a microservices architecture with separate services for the learner-facing frontend (MFEs — Micro-Frontends) and the authoring experience (Studio).

### Key Features

- Course Studio for visual course authoring with component-based content blocks
- XBlock plugin architecture for custom content types
- Micro-Frontend (MFE) architecture for modular, independently deployable UI components
- Discussion forums with threaded conversations and peer endorsements
- Proctored exam integration support
- Certificates with customizable templates and digital signatures
- A/B testing for course content optimization
- Enterprise reporting and analytics dashboards
- Internationalization with RTL language support
- Responsive design for mobile and tablet access
- LTI 1.3 integration for external tool interoperability
- Bulk enrollment and CSV-based student management

### Docker Deployment (Tutor)

The recommended way to deploy Open edX is via [Tutor](https://docs.tutor.edly.io), the official Docker-based distribution:

```bash
# Install Tutor
pip install "tutor[full]"

# Initialize configuration
tutor local quickstart

# During setup, you will be prompted for:
# - Platform name (e.g., "My University LMS")
# - Platform domain (e.g., "lms.example.com")
# - Admin username and email
# - SMTP configuration for email notifications

# After quickstart, the platform is available at:
# https://lms.example.com (LMS frontend)
# https://studio.example.com (course authoring)
```

Tutor manages the entire stack — 15+ Docker containers including MySQL, MongoDB, Redis, Nginx, the LMS service, Studio, and the various MFE services:

```bash
# Start the platform
tutor local start -d

# Check service health
tutor local status

# View logs
tutor local logs --follow lms

# Run management commands
tutor local run lms ./manage.py lms shell -c "from django.contrib.auth.models import User; print(User.objects.count())"

# Stop the platform
tutor local stop
```

### Custom Domain and TLS Configuration

```bash
# Configure your platform domain
tutor config save --set LMS_HOST=lms.example.com --set CMS_HOST=studio.example.com

# Let Tutor handle TLS via Caddy (built-in)
tutor local quickstart

# Or configure with your own reverse proxy:
# Stop Tutor's built-in Caddy
tutor config save --set ENABLE_WEB_PROXY=false

# Then configure Nginx on the host:
```

```nginx
# /etc/nginx/sites-available/lms.example.com
upstream lms_backend {
    server 127.0.0.1:8000;
}

upstream studio_backend {
    server 127.0.0.1:8001;
}

server {
    listen 443 ssl http2;
    server_name lms.example.com;

    ssl_certificate /etc/letsencrypt/live/lms.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lms.example.com/privkey.pem;

    location / {
        proxy_pass http://lms_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Creating Your First Course in Studio

1. Open `https://studio.example.com` and log in
2. Click **Create a New Course**
3. Select a course template (Demo Course, Empty Course, or import from library)
4. In the Outline view, add sections, subsections, and units
5. In each unit, add components:
   - **Text** — HTML content with embedded media
   - **Video** — YouTube URLs or uploaded MP4 files
   - **Problem** — Multiple choice, numeric input, or text response
   - **Discussion** — Threaded conversation forum
   - **HTML** — Custom HTML with JavaScript
6. Publish the course and set the enrollment start date
7. Students access the course at `https://lms.example.com/courses`

### When to Choose Open edX

Open edX is the choice for large-scale course delivery — think universities with thousands of concurrent learners, corporate training programs across multiple departments, or organizations running MOOCs. Its Studio authoring interface is intuitive for content creators, and the MFE architecture means you can customize the learner experience without touching the backend. The trade-off is infrastructure complexity: a full Open edX deployment requires 15+ containers, 4+ GB of RAM, and careful operational management.

## Chamilo: The Lightweight Alternative

[Chamilo](https://chamilo.org) was forked from the original Dokeos project with a focus on simplicity, speed, and user-friendliness. It is particularly popular in European schools, vocational training centers, and small-to-medium organizations that need a capable LMS without the complexity of Moodle or the infrastructure demands of Open edX.

### Key Features

- Intuitive, modern interface with minimal learning curve
- Course creation wizard with pre-built templates
- Learning paths — sequenced content delivery with progress tracking
- Interactive exercises with 15+ question types
- Survey and questionnaire builder
- Gradebook with custom weight calculations
- Social networking features: groups, messaging, user profiles
- Conference and chat integration (via BigBlueButton)
- SCORM import and export
- Document management with version control
- Calendar with event sharing
- Responsive mobile-friendly design
- Multi-portal support (single installation, multiple branded sites)

### Docker Deployment

```yaml
# docker-compose.yml for Chamilo
version: "3.8"

services:
  chamilo:
    image: chamilo/chamilo-lms:2.1
    ports:
      - "8080:80"
    environment:
      - CHAMILO_DB_HOST=chamilo-db
      - CHAMILO_DB_PORT=3306
      - CHAMILO_DB_NAME=chamilo
      - CHAMILO_DB_USER=chamilo
      - CHAMILO_DB_PASSWORD=chamilo_pass
      - CHAMILO_ADMIN_USER=admin
      - CHAMILO_ADMIN_PASS=admin_password
      - CHAMILO_ADMIN_EMAIL=admin@example.com
      - CHAMILO_SITE_NAME=My Learning Portal
    volumes:
      - chamilo-data:/var/www/html
    depends_on:
      - chamilo-db

  chamilo-db:
    image: mariadb:11.4
    environment:
      - MYSQL_ROOT_PASSWORD=root_pass
      - MYSQL_DATABASE=chamilo
      - MYSQL_USER=chamilo
      - MYSQL_PASSWORD=chamilo_pass
    volumes:
      - chamilo-db-data:/var/lib/mysql

volumes:
  chamilo-data:
  chamilo-db-data:
```

```bash
# Start the stack
docker compose up -d

# Access at http://localhost:8080
# Login: admin / admin_password
```

### Chamilo's Learning Paths

Chamilo's standout feature is its **Learning Path** system — a sequenced, step-by-step content delivery mechanism:

1. Go to your course → **Learning Paths** → **Create Learning Path**
2. Add steps in order: documents, videos, exercises, forums, or links
3. Configure conditions: require completion of previous step, set minimum scores
4. Enable progress tracking so students see their advancement
5. Students navigate through the path linearly, completing each step before moving on

This is particularly effective for compliance training, certification programs, and structured curricula where content must be consumed in a specific order.

```bash
# Import a SCORM package via CLI (if you have packages to bulk-import)
docker compose exec chamilo \
  php /var/www/html/main/scorm/import_scorm.php \
  --course=course_code \
  --file=/tmp/training-module.zip
```

### When to Choose Chamilo

Chamilo is ideal for organizations that want a capable LMS with a fraction of the setup complexity. It installs quickly, runs on modest hardware (1 CPU, 2 GB RAM is sufficient for small deployments), and its interface is approachable for non-technical instructors. If you are running a vocational training center, a corporate onboarding program, or a school with limited IT staff, Chamilo delivers the essential LMS features without overwhelming users or administrators.

## Feature Comparison

| Feature | Moodle | Open edX | Chamilo |
|---------|--------|----------|---------|
| **Primary Focus** | Comprehensive education platform | Large-scale course delivery | Simplicity and ease of use |
| **Course Authoring** | In-platform with activity builder | Studio (separate interface) | In-platform with wizard |
| **Content Sequencing** | Conditional activities + restriction plugins | Learning sequences + XBlock | Built-in Learning Paths |
| **Question Types** | 13 types + plugin extensions | 8+ core types + XBlock | 15+ built-in types |
| **Gradebook** | Advanced with formulas, categories, weights | Basic grade tracking | Weighted categories |
| **Peer Assessment** | Workshop activity with rubrics | ORA2 (Open Response Assessment) | Not built-in |
| **Discussion Forums** | Forum activity with ratings and modes | Threaded discussions with endorsements | Forum with social features |
| **SCORM Support** | 1.2 and 2004 | Via XBlock | Import and export |
| **H5P Integration** | Built-in (since 4.x) | Via plugin | Via plugin |
| **Mobile App** | Official Moodle app | Official Open edX app | Responsive web only |
| **Multi-tenancy** | Via separate sites or multi-tenancy plugins | Multiple sites per installation | Built-in multi-portal |
| **Plugin Ecosystem** | 2,000+ plugins | 100+ XBlocks and plugins | 50+ plugins |
| **Infrastructure** | 2 containers (app + DB) | 15+ containers (microservices) | 2 containers (app + DB) |
| **Min. RAM** | 2 GB | 4 GB (8 GB recommended) | 1 GB |
| **Learning Curve** | Moderate to steep | Steep (Studio + MFE concepts) | Easy |
| **Best For** | Universities, schools, any institution | MOOCs, large-scale training, enterprises | Small/medium orgs, vocational training |
| **License** | GPL-3.0 | AGPL-3.0 | GPL-3.0 |

## Choosing the Right LMS

The decision comes down to your scale, technical capacity, and pedagogical requirements:

**Choose Moodle if** you need the most flexible, extensible platform available. It handles everything from primary school homework submissions to university-level peer assessment workshops. The plugin ecosystem means there is likely already a solution for your specific need — whether that is plagiarism detection, attendance tracking, or integration with a student information system. Moodle is the safe default for any educational institution.

**Choose Open edX if** you are delivering courses at scale — hundreds or thousands of concurrent learners — and need a polished, professional learner experience. Its Studio authoring interface separates content creation from platform administration, which is valuable when you have dedicated course designers and a separate IT team. The microservices architecture also means you can scale individual components independently as demand grows.

**Choose Chamilo if** you need to get a learning platform running quickly with minimal infrastructure and training. It is the fastest path from zero to a functioning LMS with course content, exercises, and student enrollment. The multi-portal feature lets a single installation serve multiple departments or organizations with branded frontends. For small teams without dedicated IT staff, Chamilo's simplicity is a feature, not a limitation.

## Production Deployment Checklist

Regardless of which LMS you choose, ensure these are configured before going live:

### TLS and Reverse Proxy

```nginx
# /etc/nginx/sites-available/lms.example.com
server {
    listen 443 ssl http2;
    server_name lms.example.com;

    ssl_certificate /etc/letsencrypt/live/lms.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lms.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # File upload size limit
    client_max_body_size 100M;
}
```

### Automated Backups

```bash
#!/bin/bash
# backup-lms.sh — daily LMS backup

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/opt/backups/lms/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

# Backup application data
docker compose cp moodle:/bitnami/moodle "${BACKUP_DIR}/moodle-app"
docker compose cp moodle:/bitnami/moodledata "${BACKUP_DIR}/moodledata"

# Backup database
docker compose exec -T moodle-db \
  mariadb-dump -u bn_moodle -pmoodle_db_pass bitnami_moodle \
  > "${BACKUP_DIR}/moodle-db.sql"

# Compress
tar czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "${BACKUP_DIR}")" "${TIMESTAMP}"
rm -rf "${BACKUP_DIR}"

# Clean backups older than 30 days
find /opt/backups/lms -name "*.tar.gz" -mtime +30 -delete

echo "Backup complete: ${TIMESTAMP}"
```

### Monitoring and Health Checks

```yaml
# Add to docker-compose.yml
services:
  moodle:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/login/index.php"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 120s
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## Conclusion

Self-hosting a learning management system in 2026 is straightforward with Docker and gives you complete control over your educational platform. Moodle offers unmatched flexibility and the largest ecosystem, Open edX delivers enterprise-scale course delivery with a polished authoring experience, and Chamilo provides a lightweight, quick-to-deploy option for smaller organizations.

All three are open-source, free to use, and respect your data sovereignty. Pick the one that matches your scale and technical capacity, deploy it behind a reverse proxy with TLS, set up automated backups, and start building courses — without per-student fees or data leaving your servers.
