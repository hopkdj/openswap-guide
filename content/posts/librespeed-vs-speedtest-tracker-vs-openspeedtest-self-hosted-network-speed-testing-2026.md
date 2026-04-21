---
title: "LibreSpeed vs Speedtest-Tracker vs OpenSpeedTest: Self-Hosted Network Speed Testing 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "networking", "monitoring"]
draft: false
description: "Compare LibreSpeed, Speedtest-Tracker, and OpenSpeedTest for self-hosted network speed testing. Complete Docker setup guides, feature comparisons, and deployment recommendations for monitoring internet connections in 2026."
---

Internet speed tests are everywhere — but every time you click "Go" on a commercial speed test site, your results contribute to someone else's dataset. Your ISP's actual throughput, your connection latency, your peak and off-peak performance patterns — all harvested. For homelab operators, network administrators, and privacy-conscious users, running a self-hosted speed test server puts that data back under your control.

This guide covers three leading open-source options for self-hosted network speed testing — **LibreSpeed**, **Speedtest-Tracker**, and **OpenSpeedTest** — with practical [docker](https://www.docker.com/) deployment instructions so you can measure your connection performance on your own infrastructure.

## Why Self-Host Your Network Speed Tests

Commercial speed test services like Ookla's Speedtest.net, Fast.com, and others are convenient, but self-hosting delivers concrete advantages:

- **Data privacy**: Your speed test results never leave your network. No third party collects your bandwidth profiles, usage patterns, or connection quality data.
- **Accurate local measurements**: Testing to a server on your own LAN eliminates the variable of internet hop latency. You measure raw throughput between your device and your server, giving you a baseline for your local network performance.
- **ISP monitoring**: Run scheduled speed tests from your server to external nodes and log the results over time. Build a historical record of your ISP's actual delivered speeds versus what you pay for.
- **No ads or redirects**: Commercial speed test sites are increasingly cluttered with ads, auto-play videos, and redirects to premium services. Self-hosted tools are clean and focused.
- **Multi-point testing**: Deploy speed test servers in multiple locations (home, office, remote VPS) and compare performance between them.
- **Offline capability**: A self-hosted speed test on your LAN works even when your internet connection is down, letting you troubleshoot whether the problem is your ISP or your local network.

For anyone running a home server, managing a small office network, or simply wanting to hold their ISP accountable, a self-hosted speed test setup is one of the most practical first projects. If you are already running [network monitoring with Zabbix, LibreNMS, or Netdata](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/), adding speed test data gives you a complete picture of both local infrastructure health and ISP performance. For broader context on securing your home network, check out our [network traffic analysis guide with Zeek and Arkime](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide/) and [NAS setup comparison](../self-hosted-nas-solutions-openmediavault-truenas-rockstor-guide-2026/).

## The Three Tools Compared

Each tool approaches speed testing differently:

| Feature | LibreSpeed | Speedtest-Tracker | OpenSpeedTest |
|---|---|---|---|
| **Primary Purpose** | Speed test server for users | Automated connection monitoring | Simple HTML5 speed test |
| **Stars** | 14,551 | 5,514 | 3,530 |
| **Language** | JavaScript/PHP | PHP (Laravel) | Vanilla JavaScript |
| **Database** | SQLite, MySQL, PostgreSQL | PostgreSQL | None (stateless) |
| **Historical Tracking** | Yes (with database) | Yes (built-in, dashboard) | No |
| **Scheduling** | No (manual tests only) | Yes (cron-based, automated) | No (manual tests only) |
| **ISP Monitoring** | Via results database | Native (runs Ookla speedtest-cli) | No |
| **Multi-server Support** | Yes (load balancing) | No (single server) | No |
| **Docker Image** | `ghcr.io/librespeed/speedtest` | `lscr.io/linuxserver/speedtest-tracker` | `openspeedtest/latest` |
| **Default Port** | 80 | 8080 | 3001 |
| **Reverse Proxy Ready** | Yes | Yes | Yes |
| **API** | REST (results endpoint) | REST API | None |
| **Authentication** | Optional | Yes (user accounts) | None |

### LibreSpeed — The Most Flexible Self-Hosted Speed Test

[LibreSpeed](https://github.com/librespeed/speedtest) is the most popular self-hosted speed test project, with over 14,500 stars on GitHub. It provides a clean HTML5-based speed test interface that measures download speed, upload speed, ping, and jitter. The engine is written in vanilla JavaScript on the frontend with PHP, Node.js, or Go backends available.

Key strengths:
- **Multiple backend options**: PHP for simple setups, Node.js for high-concurrency environments, Go for maximum performance.
- **Multi-server support**: Deploy multiple speed test servers and let clients automatically connect to the nearest or fastest one.
- **Results database**: Optional MySQL/PostgreSQL/SQLite backend stores test results for historical analysis.
- **Customizable UI**: The test page can be themed, branded, and embedded in existing websites.
- **Telegraf integr[grafana](https://grafana.com/): Export metrics to Grafana via Telegraf for real-time dashboards.

LibreSpeed is best when you want to give users (yourself, your family, your team) a clean speed test interface that runs entirely on your own infrastructure.

### Speedtest-Tracker — Automated ISP Monitoring

[Speedtest-Tracker](https://github.com/alexjustesen/speedtest-tracker) takes a different approach. Instead of providing a user-facing speed test page, it runs Ookla's speedtest-cli on a schedule and stores the results in a database with a Laravel-based web dashboard. It is designed for monitoring your internet connection over time.

Key strengths:
- **Automated scheduling**: Runs speed tests on a configurable schedule (every 15 minutes, hourly, daily) without manual intervention.
- **Historical dashboards**: Built-in web UI shows trends in download/upload speeds, latency, and packet loss over days, weeks, and months.
- **Ookla accuracy**: Uses the official Ookla speedtest-cli binary, so results are directly comparable to Speedtest.net measurements.
- **Notifications**: Can alert you when speeds drop below configurable thresholds.
- **Data export**: Export results as JSON or CSV for external analysis.

Speedtest-Tracker is best when your goal is to monitor your ISP's performance over time and build a record of actual versus advertised speeds.

### OpenSpeedTest — Simple and Dependency-Free

[OpenSpeedTest](https://github.com/openspeedtest/Speed-Test) is the simplest of the three. It is a pure HTML5 speed test written in vanilla JavaScript with no third-party frameworks. It has been in development since 2011 and focuses on being lightweight and easy to deploy.

Key strengths:
- **Zero dependencies**: No PHP, no database, no Node.js. Just serve static files from any web server.
- **Mobile-friendly**: Responsive design works well on phones and tablets.
- **Very lightweight**: The entire application is a few megabytes. Ideal for low-resource servers or embedded devices.
- **Long track record**: Over a decade of development with consistent updates.

OpenSpeedTest is best when you want the simplest possible setup — just drop files on a web server and go. It lacks historical tracking and scheduling, so it pairs well with a monitoring tool like Speedtest-Tracker.

## Docker Deployment Guides

### Deploying LibreSpeed

LibreSpeed's official Docker image runs on `ghcr.io/librespeed/speedtest`. Here is a production-ready compose configuration with a PostgreSQL database for storing test results:

```yaml
# docker-compose.librespeed.yml
name: librespeed

services:
  speedtest:
    image: ghcr.io/librespeed/speedtest:latest
    container_name: librespeed
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - DB_HOSTNAME=librespeed-db
      - DB_NAME=librespeed
      - DB_USERNAME=librespeed
      - DB_PASSWORD=librespeed_secret_password
      - DB_TYPE=pgsql
      - TELEMETRY=true
      - ENABLE_ID_OBFUSCATION=true
      - PASSWORD=password_for_admin_panel
    depends_on:
      - librespeed-db
    networks:
      - librespeed-net

  librespeed-db:
    image: postgres:16-alpine
    container_name: librespeed-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=librespeed
      - POSTGRES_USER=librespeed
      - POSTGRES_PASSWORD=librespeed_secret_password
    volumes:
      - librespeed-data:/var/lib/postgresql/data
    networks:
      - librespeed-net

volumes:
  librespeed-data:

networks:
  librespeed-net:
    driver: bridge
```

Start the stack:

```bash
docker compose -f docker-compose.librespeed.yml up -d
```

Access the speed test at `http://your-server-ip:8080`. The results page (with historical data) is available at `http://your-server-ip:8080/results.php`.

For a simpler setup without a database, omit the PostgreSQL service and set `TELEMETRY=false` in the environment.

### Deploying Speedtest-Tracker

Speedtest-Tracker is available via LinuxServer.io's image, which provides consistent environment variable patterns and multi-arch support:

```yaml
# docker-compose.speedtest-tracker.yml
name: speedtest-tracker

services:
  speedtest-tracker:
    image: lscr.io/linuxserver/speedtest-tracker:latest
    container_name: speedtest-tracker
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - APP_KEY=base64:$(openssl rand -base64 32)
      - DB_CONNECTION=sqlite
      - SPEEDTEST_SCHEDULE="0 */6 * * *"
      - PRUNE_RESULTS_OLDER_THAN=365
    ports:
      - "8081:80"
      - "8443:443"
    volumes:
      - speedtest-data:/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  speedtest-data:
```

Generate an application key before starting:

```bash
export APP_KEY=$(openssl rand -base64 32)
```

Then replace `base64:$(openssl rand -base64 32)` in the compose file with the generated value, or use Docker's variable substitution:

```bash
docker compose -f docker-compose.speedtest-tracker.yml up -d
```

The dashboard is available at `http://your-server-ip:8081`. On first launch, you will be prompted to create an admin account. The `SPEEDTEST_SCHEDULE` cron expression controls how often tests run — the example above runs every 6 hours. Adjust to your needs.

### Deploying OpenSpeedTest

OpenSpeedTest is the simplest deployment. Use the official Docker image:

```yaml
# docker-compose.openspeedtest.yml
name: openspeedtest

services:
  openspeedtest:
    image: openspeedtest/latest:latest
    container_name: openspeedtest
    restart: unless-stopped
    ports:
      - "3001:3000"
```

Start it:

```bash
docker compose -f docker-compose.openspeedtest.yml up -d
```

That is it. The speed test interface is immediately available at `http://your-server-ip:3001`. No database, no configuration, no authentication. The trade-off is that results are not stored and there is no scheduling.

## Choosing the Right Tool

The choice depends on your use case:

| Scenario | Recommended Tool |
|---|---|
| Give users a self-hosted speed test page | LibreSpeed |
| Monitor ISP performance over time | Speedtest-Tracker |
| Quick, zero-config speed test on a server | OpenSpeedTest |
| Need multi-server load balancing | LibreSpeed |
| Want Grafana dashboards with historical data | Speedtest-Tracker + LibreSpeed |
| Minimal resource usage | OpenSpeedTest |
| Need API access to results | LibreSpeed or Speedtest-Tracker |

For the most complete setup, run **both** LibreSpeed and Speedtest-Tracker: LibreSpeed provides the user-facing speed test page for on-demand testing, while Speedtest-Tracker runs in the background logging your connection quality on a schedule. The combined setup costs virtually nothing on a modest server and gives you both real-time testing and historical monitoring.

## Reverse Proxy Configuration

All t[nginx](https://nginx.org/)tools work behind a reverse proxy. Here is an Nginx configuration example for LibreSpeed:

```nginx
server {
    listen 443 ssl http2;
    server_name speedtest.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/speedtest.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/speedtest.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase buffer for large speed test payloads
        proxy_buffering off;
        client_max_body_size 100m;
    }
}
```

For Speedtest-Tracker, point the proxy at port 8081. For OpenSpeedTest, use port 3001.

## FAQ

### What is the difference between LibreSpeed and Speedtest-Tracker?

LibreSpeed is a user-facing speed test server — it provides a web page where anyone can manually run a speed test. Speedtest-Tracker is an automated monitoring tool — it runs Ookla's speedtest-cli on a schedule and logs results to a dashboard. They serve complementary purposes: on-demand testing versus continuous monitoring.

### Can I use LibreSpeed without a database?

Yes. Set the `TELEMETRY=false` environment variable and LibreSpeed will run as a stateless speed test server. Results will not be stored, but the test interface will function normally. This is the simplest configuration for a quick deployment.

### Does Speedtest-Tracker require Ookla's CLI?

Yes, Speedtest-Tracker bundles and uses Ookla's official speedtest-cli binary for running tests. This means results are directly comparable to what you would see on Speedtest.net. The LinuxServer.io Docker image includes the binary pre-installed.

### Which tool is best for monitoring my ISP's actual speeds?

Speedtest-Tracker is purpose-built for this. It runs scheduled tests and stores results with timestamps, allowing you to build charts showing your actual download/upload speeds over weeks and months. This is the most reliable way to document whether your ISP is delivering the speeds you pay for.

### Can I deploy multiple LibreSpeed servers for geographic coverage?

Yes. LibreSpeed supports multi-server deployments. Each server registers with a central endpoint, and the client automatically selects the server with the lowest latency. This is useful if you have servers in multiple data centers or want to offer speed tests to users in different regions.

### Is OpenSpeedTest truly free and open source?

Yes. OpenSpeedTest is released under an open-source license and has been in development since 2011. It uses only built-in browser APIs (XMLHttpRequest, HTML, CSS, JavaScript, SVG) with no third-party frameworks or external dependencies.

### How much server resources do these tools require?

OpenSpeedTest is the lightest — it serves static files and needs only a few megabytes of RAM. LibreSpeed with a database requires around 256-512 MB RAM (PostgreSQL is the main consumer). Speedtest-Tracker requires similar resources (512 MB recommended) because it runs a Laravel application with SQLite or PostgreSQL. All three run comfortably on a Raspberry Pi 4 or any low-end VPS.

### How do I secure my self-hosted speed test server?

For LibreSpeed, set a password via the `PASSWORD` environment variable to restrict access to the admin panel and results page. For Speedtest-Tracker, create a user account on first launch and enable authentication. For all tools, place them behind a reverse proxy with HTTPS (Let's Encrypt) and consider restricting access by IP range if the server is internet-facing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "LibreSpeed vs Speedtest-Tracker vs OpenSpeedTest: Self-Hosted Network Speed Testing 2026",
  "description": "Compare LibreSpeed, Speedtest-Tracker, and OpenSpeedTest for self-hosted network speed testing. Complete Docker setup guides, feature comparisons, and deployment recommendations for monitoring internet connections in 2026.",
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
