---
title: "TCExam vs Chamilo vs Moodle: Best Self-Hosted Online Exam Platform 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "education"]
draft: false
description: "Compare TCExam, Chamilo, and Moodle for self-hosted online examinations. Complete guide with Docker deployment, question bank management, and proctoring features."
---

Running exams and assessments online requires more than just a form builder. Institutions need dedicated platforms that handle question banks, timed assessments, automated grading, anti-cheating measures, and detailed result analytics. While full learning management systems offer quiz modules, standalone assessment platforms like TCExam provide laser-focused exam delivery without the overhead of a complete LMS.

This guide compares three mature open-source options for self-hosted online examinations: **TCExam** (dedicated assessment system), **Chamilo** (lightweight LMS with strong exam features), and **Moodle** (the world's most widely deployed open-source learning platform). Whether you're a university, certification body, or corporate training team, this comparison will help you pick the right tool.

## Why Self-Host Your Online Exam Platform

Cloud-based exam platforms charge per-user or per-exam fees that scale poorly. A 500-student exam can cost hundreds of dollars on SaaS platforms, and your assessment data lives on someone else's servers. Self-hosting gives you:

- **Full data ownership** — student records, exam results, and question banks stay on your infrastructure
- **Unlimited users and exams** — no per-seat licensing, no exam credits
- **Custom proctoring rules** — define time limits, randomize questions, lock browser access
- **Integration flexibility** — connect to your existing student information system or identity provider
- **Offline availability** — run exams on internal networks without internet dependency

For related reading, see our [complete LMS platform comparison](../best-self-hosted-lms-platforms-moodle-openedx-chamilo-guide-2026/) and [self-hosted test management tools](../kiwi-tcms-vs-testlink-vs-reportportal-self-hosted-test-management-guide-2026/).

## TCExam vs Chamilo vs Moodle: Quick Comparison

| Feature | TCExam | Chamilo | Moodle |
|---------|--------|---------|--------|
| **Type** | Dedicated assessment system | Lightweight LMS | Full LMS |
| **Language** | PHP | PHP | PHP |
| **Database** | MySQL/MariaDB, PostgreSQL | MySQL/MariaDB | MySQL/MariaDB, PostgreSQL |
| **GitHub Stars** | 614 | 945 | 7,008 |
| **Last Updated** | 2026-04-16 | 2026-04-23 | 2026-04-17 |
| **Question Types** | Multiple choice, free text, numerical, ordering | Multiple choice, matching, fill-in-blank, essay | 20+ types including calculated, drag-and-drop |
| **Randomization** | Question and answer shuffling | Question shuffling | Question bank with random selection |
| **Timed Exams** | Yes | Yes | Yes |
| **Anti-Cheating** | IP restriction, time limits, browser lock | Password protection, time limits | Safe Exam Browser integration, proctoring plugins |
| **Automated Grading** | Yes (MC, numerical, matching) | Yes (MC, matching) | Yes (MC, numerical, calculated, pattern match) |
| **Question Bank** | Yes, with categories and difficulty levels | Yes, shared across courses | Yes, with contexts and tagging |
| **Reporting** | Statistical analysis, item difficulty, reliability | Grade book, progress tracking | Comprehensive analytics, custom reports |
| **Multi-Language** | Yes (30+ languages) | Yes (50+ languages) | Yes (100+ languages) |
| **Docker Support** | Community images | Official Docker | Official Docker |
| **License** | AGPLv3 | GPLv3 | GPLv3 |

## TCExam: Dedicated Computer-Based Assessment

[TCExam](https://www.tcexam.org/) (tecnickcom/tcexam, 614 stars) is purpose-built for creating, delivering, and grading computer-based assessments. Unlike LMS platforms that include quizzes as one feature among many, TCExam's entire architecture revolves around the exam workflow.

### Key Features

- **Author module** — create questions with rich text, images, formulas, and multimedia
- **Delivery module** — schedule exams, set time limits, control access by user group
- **Results module** — statistical analysis including item difficulty index, discrimination index, and Cronbach's alpha reliability scores
- **Question bank** — organize by subject, topic, and difficulty; random selection for each exam attempt
- **Multi-user management** — administrators, teachers, and students with distinct permissions
- **Export formats** — results in PDF, XML, and TSV for further analysis

### Docker Deployment

TCExam doesn't ship an official `docker-compose.yml`, but it runs on any standard LAMP stack. Here's a working Docker Compose configuration:

```yaml
version: "3.8"

services:
  tcexam-db:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: tcexam_root_pass
      MYSQL_DATABASE: tcexam
      MYSQL_USER: tcexam
      MYSQL_PASSWORD: tcexam_pass
    volumes:
      - tcexam-db-data:/var/lib/mysql
    networks:
      - tcexam-net

  tcexam-web:
    image: php:8.2-apache
    environment:
      TCINSTALL: "true"
    volumes:
      - ./tcexam:/var/www/html
      - ./tcexam-config.php:/var/www/html/shared/config/tce_config.php
    ports:
      - "8080:80"
    depends_on:
      - tcexam-db
    networks:
      - tcexam-net
    command: >
      bash -c "
        docker-php-ext-install mysqli pdo_mysql &&
        a2enmod rewrite &&
        apache2-foreground
      "

volumes:
  tcexam-db-data:

networks:
  tcexam-net:
    driver: bridge
```

After starting the containers, run the TCExam installer at `http://localhost:8080/install/install.php` to configure the database connection and create the admin account.

### Manual Installation on Ubuntu/Debian

```bash
# Install dependencies
sudo apt update
sudo apt install -y apache2 mariadb-server php8.2 php8.2-mysql \
  php8.2-gd php8.2-xml php8.2-mbstring php8.2-zip libapache2-mod-php8.2

# Download TCExam
cd /var/www/html
sudo wget https://github.com/tecnickcom/tcexam/archive/refs/heads/main.zip
sudo unzip main.zip
sudo mv tcexam-main tcexam
sudo chown -R www-data:www-data /var/www/html/tcexam

# Configure database
sudo mysql -e "CREATE DATABASE tcexam; CREATE USER 'tcexam'@'localhost' IDENTIFIED BY 'strong_password'; GRANT ALL ON tcexam.* TO 'tcexam'@'localhost'; FLUSH PRIVILEGES;"

# Run installer
# Visit http://your-server/tcexam/install/install.php
```

## Chamilo: Lightweight LMS with Strong Assessment Tools

[Chamilo](https://chamilo.org/) (chamilo/chamilo-lms, 945 stars) is a learning management system designed for simplicity. Its exam module covers the full assessment lifecycle — from question creation to grade reporting — without the complexity of larger platforms.

### Key Features

- **Exercise builder** — linear, random, or sequential question delivery
- **Question types** — multiple choice (single/multiple), fill-in-blank, matching, free answer, hotspot
- **Conditions and prerequisites** — require minimum scores before progressing
- **Grade book** — weighted categories, export to CSV, grade history
- **Certificate generation** — automatic certificates upon passing exams
- **SCORM support** — import and deliver SCORM packages alongside exams
- **Conference tool** — live sessions integrated with course content

### Docker Deployment

Chamilo provides official Docker images through Docker Hub:

```yaml
version: "3.8"

services:
  chamilo-db:
    image: mariadb:11
    environment:
      MARIADB_ROOT_PASSWORD: chamilo_root
      MARIADB_DATABASE: chamilo
      MARIADB_USER: chamilo
      MARIADB_PASSWORD: chamilo_pass
    volumes:
      - chamilo-db-data:/var/lib/mysql
    networks:
      - chamilo-net

  chamilo-web:
    image: chamilo/chamilo:latest
    environment:
      CHAMILO_DATABASE_HOST: chamilo-db
      CHAMILO_DATABASE_NAME: chamilo
      CHAMILO_DATABASE_USER: chamilo
      CHAMILO_DATABASE_PASS: chamilo_pass
      CHAMILO_URL: http://localhost:8081
    ports:
      - "8081:80"
    volumes:
      - chamilo-data:/var/www/html
    depends_on:
      - chamilo-db
    networks:
      - chamilo-net

volumes:
  chamilo-db-data:
  chamilo-data:

networks:
  chamilo-net:
    driver: bridge
```

### Reverse Proxy Configuration (Nginx)

For production deployments, place Chamilo behind Nginx with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name exams.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/exams.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exams.your-domain.com/privkey.pem;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Moodle: Enterprise-Grade Assessment Platform

[Moodle](https://moodle.org/) (moodle/moodle, 7,008 stars) is the most widely deployed open-source LMS globally, used by over 300 million users across 250,000+ sites. Its quiz engine is arguably the most feature-rich of any open-source platform, with over 20 question types and extensive plugin support.

### Key Features

- **Quiz engine** — 20+ question types including calculated, drag-and-drop, crosswords, and pattern match
- **Question bank** — categorized, tagged, and shared across courses; random question selection by category
- **Adaptive mode** — students can retry questions within the same attempt with penalties
- **Interactive with multiple tries** — hint-based progression with feedback
- **Safe Exam Browser** — locks down the student's computer during exams
- **Proctoring plugins** — webcam monitoring, screen recording, plagiarism detection
- **Question behaviour plugins** — deferred feedback, immediate feedback, interactive, adaptive
- **Report plugins** — statistics, responses download, quiz accessibility report
- **Question import/export** — Aiken, GIFT, Moodle XML, Blackboard, IMS QTI, WebCT formats

### Docker Deployment

Moodle's official Docker image simplifies deployment significantly:

```yaml
version: "3.8"

services:
  moodle-db:
    image: mariadb:11
    environment:
      MARIADB_ROOT_PASSWORD: moodle_root
      MARIADB_DATABASE: moodle
      MARIADB_USER: moodle
      MARIADB_PASSWORD: moodle_pass
    volumes:
      - moodle-db-data:/var/lib/mysql
    networks:
      - moodle-net

  moodle-web:
    image: bitnami/moodle:latest
    environment:
      MOODLE_DATABASE_HOST: moodle-db
      MOODLE_DATABASE_PORT_NUMBER: 3306
      MOODLE_DATABASE_USER: moodle
      MOODLE_DATABASE_PASSWORD: moodle_pass
      MOODLE_DATABASE_NAME: moodle
      MOODLE_USERNAME: admin
      MOODLE_PASSWORD: admin_password
      MOODLE_EMAIL: admin@your-domain.com
      MOODLE_SITE_NAME: "My Exam Platform"
    ports:
      - "8082:8080"
      - "8443:8443"
    volumes:
      - moodle-data:/bitnami/moodle
      - moodle-moodledata:/bitnami/moodledata
    depends_on:
      - moodle-db
    networks:
      - moodle-net

volumes:
  moodle-db-data:
  moodle-data:
  moodle-moodledata:

networks:
  moodle-net:
    driver: bridge
```

### Nginx Reverse Proxy with SSL

```nginx
server {
    listen 443 ssl http2;
    server_name learn.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/learn.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/learn.your-domain.com/privkey.pem;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

## Choosing the Right Platform

| Decision Factor | Choose TCExam if... | Choose Chamilo if... | Choose Moodle if... |
|----------------|---------------------|---------------------|---------------------|
| **Primary need** | Exams only, no course management | Simple courses + exams | Full learning ecosystem |
| **Team size** | Small IT team | Small-to-medium team | Dedicated admin staff |
| **Question types** | Standard types suffice | Need 5-8 question types | Need 20+ specialized types |
| **Deployment weight** | Lightweight (~200MB) | Medium (~500MB) | Heavy (~1GB+) |
| **Scalability** | Hundreds of users | Thousands of users | Hundreds of thousands |
| **Proctoring** | Basic (time limits, IP restrict) | Basic (password, timing) | Advanced (SEB, plugins) |
| **Reporting depth** | Statistical (psychometrics) | Grade book + progress | Enterprise analytics |

## FAQ

### What is the difference between TCExam and Moodle?

TCExam is a dedicated computer-based assessment system focused solely on creating, delivering, and grading exams. Moodle is a full-featured learning management system that includes a quiz engine as one of many modules. Choose TCExam if you only need exam functionality; choose Moodle if you also need course management, forums, assignment submission, and grade books.

### Can TCExam handle large-scale exams with thousands of concurrent users?

Yes, TCExam scales well with proper server configuration. The bottleneck is typically the database layer — using MySQL/MariaDB with proper indexing and a read replica can support thousands of simultaneous exam takers. For extreme scale, deploy behind a load balancer with multiple web server instances sharing the same database.

### Does Moodle support Safe Exam Browser for proctoring?

Yes, Moodle integrates with Safe Exam Browser (SEB), a free desktop application that locks down a student's computer during an exam. SEB prevents access to other applications, disables copy/paste, and restricts navigation to the Moodle quiz page only. This is configured in the quiz settings under "Extra restrictions on attempts."

### Which platform has the best question randomization?

All three platforms support question randomization, but Moodle offers the most granular control. You can define question banks by category, set the number of questions to draw randomly from each category, and apply conditions based on difficulty level. TCExam also supports random selection from categorized banks, while Chamilo provides basic randomization across the entire question pool.

### Can I import questions from existing Word documents or spreadsheets?

Moodle has the most flexible import options, supporting Aiken format (plain text), GIFT format (a flexible text-based format), Moodle XML, Blackboard, and IMS QTI. TCExam supports its own XML format and has import tools for common formats. Chamilo supports QTI import. For bulk imports, converting your existing questions to GIFT format (for Moodle) or Aiken format (for TCExam) is the fastest approach.

### How do I backup and restore exam data?

For all three platforms, backup your database and file directories. With Docker deployments, the named volumes contain all persistent data. Run `docker volume backup` or manually copy the volume directories. For TCExam, also back up the `shared/config/` directory containing your configuration. Moodle additionally has built-in course backup functionality that exports courses as `.mbz` files.

### Which platform is best for certification exams with time limits and auto-grading?

TCExam excels at timed, auto-graded certification exams. Its results module automatically calculates statistics like item difficulty and reliability scores, which are essential for maintaining certification quality. Moodle also supports timed auto-graded exams but requires more configuration. Chamilo is simpler but lacks the psychometric analysis features that certification bodies often require.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TCExam vs Chamilo vs Moodle: Best Self-Hosted Online Exam Platform 2026",
  "description": "Compare TCExam, Chamilo, and Moodle for self-hosted online examinations. Complete guide with Docker deployment, question bank management, and proctoring features.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
