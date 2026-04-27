---
title: "Pretalx vs Frab vs OSEM: Self-Hosted Conference CFP & Program Management 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "conference"]
draft: false
description: "Complete comparison of self-hosted conference program management tools — Pretalx, Frab, and OSEM. Docker setup guides, CFP workflows, speaker management, and schedule building for tech conferences and open-source events."
---

## Why Self-Host Your Conference CFP and Program Management?

If you organize tech conferences, open-source summits, academic symposia, or community meetups, managing the Call for Papers (CFP), speaker submissions, session scheduling, and program publication is one of the most operationally complex parts of the job. Commercial platforms like Sessionize, Eventify, and Whova charge per-event fees, lock your data into proprietary systems, and limit customization.

Self-hosting a conference management platform gives you:

- **Zero per-event costs** — no matter how large your conference grows, there are no per-submission or per-attendee fees
- **Full data ownership** — speaker bios, talk abstracts, review scores, and attendee preferences stay on your servers
- **Unlimited customization** — custom review criteria, multi-stage selection workflows, branded submission forms, and program layouts tailored to your event
- **Long-term archival** — keep program data from past conferences accessible and searchable for years
- **Integration freedom** — connect directly to your own ticketing system, website, streaming platform, and mobile app without API rate limits

Here is how the three leading open-source conference program management tools compare in 2026.

## Overview: The Three Platforms

### Pretalx

Pretalx is a Python/Django-based conference planning tool designed specifically for managing Calls for Papers, speaker submissions, peer reviews, and schedule building. It powers many well-known open-source conferences including PyCon DE, FrOSCon, and EuroPython. As of April 2026, it has **897 GitHub stars** and was last updated within the past week. The official Docker image `pretalx/pretalx` has over 500,000 pulls.

**Best for**: Tech conferences and open-source events that need a polished CFP workflow with strong review management.

### Frab

Frab is a Ruby on Rails conference management system that originated from the Chaos Communication Congress (CCC) community. It handles CFP management, event scheduling, room assignments, and program publication. With **727 GitHub stars** and regular updates, it remains a popular choice for unconferences, hacker conferences, and community events across Europe.

**Best for**: Community-run conferences, unconferences, and events inspired by the CCC model.

### OSEM (Open Source Event Manager)

OSEM is a Ruby on Rails event management tool built by the openSUSE project for organizing openSUSE conferences (oSC). It covers the full conference lifecycle: CFP management, paper submission, review, scheduling, and ticketing integration. With **915 GitHub stars** and active development by the openSUSE community, it is designed for large-scale open-source conferences.

**Best for**: Large open-source conferences that need a full-featured event management platform with strong community integration.

## Feature Comparison

| Feature | Pretalx | Frab | OSEM |
|---|---|---|---|
| **Language** | Python (Django) | Ruby on Rails | Ruby on Rails |
| **GitHub Stars** | 897 | 727 | 915 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **CFP Management** | ✅ Multi-event, customizable forms | ✅ Event-level CFP | ✅ Full CFP lifecycle |
| **Paper Submission** | ✅ Rich text, file attachments | ✅ Text submission | ✅ Full submission workflow |
| **Peer Review** | ✅ Score-based, multi-reviewer | ✅ Event review system | ✅ Review and voting system |
| **Schedule Builder** | ✅ Drag-and-drop, conflict detection | ✅ Manual schedule creation | ✅ Schedule grid with rooms |
| **Room/Track Management** | ✅ Multiple rooms and tracks | ✅ Room assignments | ✅ Room and track support |
| **Speaker Profiles** | ✅ Bio, avatar, past talks | ✅ Speaker management | ✅ Speaker profiles |
| **Program Export** | ✅ JSON, XML, iCal, HTML | ✅ XML, iCal, HTML | ✅ XML, iCal, PDF |
| **Announcements** | ✅ Email notifications | ✅ Email system | ✅ Email notifications |
| **Ticketing Integration** | ✅ Via Pretix integration | ❌ No built-in ticketing | ✅ Built-in registration |
| **Multi-Event Support** | ✅ Multiple events per install | ❌ Single event per install | ✅ Multiple events |
| **Public Program Page** | ✅ Branded, customizable | ✅ Basic program page | ✅ Full program pages |
| **REST API** | ✅ Full REST API | ❌ Limited API | ✅ REST API |
| **Docker Support** | ✅ Official image | ✅ docker-compose.yml | ✅ Docker Compose |

## Deployment: Docker Compose Guides

### Pretalx Docker Setup

Pretalx does not include a `docker-compose.yml` file in its source repository, but the official Docker image is well-documented and widely used. Here is a production-ready setup:

```yaml
version: "3.8"

services:
  pretalx:
    image: pretalx/pretalx:latest
    ports:
      - "8080:80"
    environment:
      - PRETALX_SITE_URL=https://cfp.yourconference.org
      - PRETALX_DB_NAME=pretalx
      - PRETALX_DB_USER=pretalx
      - PRETALX_DB_PASS=pretalx_secret_db
      - PRETALX_SECRET_KEY=change-this-to-a-long-random-string
    volumes:
      - pretalx-data:/data
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=pretalx
      - POSTGRES_USER=pretalx
      - POSTGRES_PASSWORD=pretalx_secret_db
    volumes:
      - pretalx-db:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - pretalx-redis:/data

volumes:
  pretalx-data:
  pretalx-db:
  pretalx-redis:
```

Key configuration steps:

1. Replace `PRETALX_SECRET_KEY` with a cryptographically random string (`openssl rand -base64 48`)
2. Set `PRETALX_SITE_URL` to your public domain
3. Run `docker compose up -d` to start
4. Access the admin interface at `http://localhost:8080/orga/` to create your first event and open the CFP

For email sending, configure an SMTP backend via `PRETALX_MAIL_FROM`, `PRETALX_MAIL_HOST`, and related variables.

### Frab Docker Setup

Frab includes a `docker-compose.yml` file in its repository root:

```yaml
version: "3.8"

services:
  web:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://frab:frab_password@db/frab_production
      - RAILS_SERVE_STATIC_FILES=true
      - SECRET_KEY_BASE=change-this-to-a-long-random-string
      - FROM_EMAIL=noreply@yourconference.org
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=frab
      - POSTGRES_PASSWORD=frab_password
      - POSTGRES_DB=frab_production
    volumes:
      - frab-db:/var/lib/postgresql/data

volumes:
  frab-db:
```

Key configuration steps:

1. Clone the Frab repository: `git clone https://github.com/frab/frab.git && cd frab`
2. Generate a secret key: `bin/rails secret` and set it as `SECRET_KEY_BASE`
3. Run `docker compose up -d` to start the application and database
4. Navigate to `http://localhost:3000` and create an admin account
5. Create a new event and configure the CFP period, track categories, and review criteria

For production deployments, place Frab behind a reverse proxy like Caddy or Nginx with TLS termination.

### OSEM Docker Setup

OSEM can be deployed using Docker Compose with PostgreSQL and Redis:

```yaml
version: "3.8"

services:
  web:
    image: opensuse/osem:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://osem:osem_password@db/osem_production
      - RAILS_ENV=production
      - SECRET_KEY_BASE=change-this-to-a-long-random-string
      - MAIL_FROM=noreply@yourconference.org
      - SITE_URL=https://conference.yourdomain.org
    depends_on:
      - db
      - redis

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=osem
      - POSTGRES_PASSWORD=osem_password
      - POSTGRES_DB=osem_production
    volumes:
      - osem-db:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - osem-redis:/data

volumes:
  osem-db:
  osem-redis:
```

Key configuration steps:

1. Pull the official image: `docker pull opensuse/osem:latest`
2. Generate a secret key and update `SECRET_KEY_BASE`
3. Run `docker compose up -d` to launch the full stack
4. Access the application at `http://localhost:3000` and register the first admin user
5. Create a conference, configure the CFP timeline, and publish the call for proposals

OSEM includes built-in registration, so you can manage both the program and attendee registration from the same platform.

## CFP Workflow Comparison

### Pretalx Workflow

1. **Create event** — Set conference name, dates, timezone, and submission types (talk, workshop, lightning talk)
2. **Open CFP** — Define submission fields (title, abstract, bio, session notes, attachments) and deadline
3. **Collect submissions** — Speakers submit talks through a public CFP page with your branding
4. **Peer review** — Reviewers score submissions on criteria like topic relevance, speaker experience, and audience interest. Pretalx supports multi-round reviews with anonymized submissions
5. **Accept/reject** — Program committee reviews scores and makes decisions. Accepted speakers receive automated notification emails
6. **Schedule building** — Drag-and-drop accepted talks into time slots and rooms. Conflict detection prevents double-booking speakers
7. **Publish program** — Public schedule goes live with real-time updates via the API

### Frab Workflow

1. **Create event** — Set conference name, dates, venue, and event type
2. **Configure CFP** — Define event types (lecture, workshop, panel), track categories, and submission deadline
3. **Collect submissions** — Speakers register and submit proposals through the CFP form
4. **Review submissions** — Organizers review, rate, and categorize submissions. The system supports email-based discussion among reviewers
5. **Schedule creation** — Assign talks to rooms and time slots using the scheduling interface
6. **Publish program** — Generate iCal feeds, XML exports, and HTML program pages

### OSEM Workflow

1. **Create conference** — Set event name, dates, venue details, and registration settings
2. **Configure CFP** — Define event types, difficulty levels, and submission fields
3. **Collect submissions** — Speakers submit proposals through the public conference page
4. **Review and voting** — Community members and organizers vote on submissions. OSEM supports public voting for community-selected tracks
5. **Program assembly** — Schedule accepted events into rooms and time slots using the visual schedule editor
6. **Publish and manage** — Program pages go live with integrated registration. Real-time schedule updates are available via the API

## Integration Ecosystem

### Pretalx Integrations

- **Pretix** — Direct integration with the Pretix ticketing platform for unified registration and CFP management
- **Matrix** — Bot integration for speaker notifications and schedule updates
- **frab XML export** — Export programs in frab-compatible XML for interoperability
- **Custom plugins** — Plugin system for custom review criteria, email templates, and export formats
- **REST API** — Full API for program data, enabling integration with mobile apps and static site generators

### Frab Integrations

- **Pentabarf compatibility** — Exports pentabarf-compatible XML, making it usable with conference apps like FOSDEM's mobile app
- **iCal feeds** — Per-track and per-room iCal calendar feeds
- **XML exports** — Schedule XML for third-party program viewers
- **Static site generation** — Export programs as static HTML for hosting on any web server

### OSEM Integrations

- **OpenSUSE infrastructure** — Deep integration with openSUSE community tools and infrastructure
- **Registration system** — Built-in attendee registration, eliminating the need for a separate ticketing tool
- **Email notifications** — Automated speaker and attendee communication
- **REST API** — API access for schedule data and speaker information

## When to Choose Each Platform

### Choose Pretalx if:

- You are running a tech conference or open-source event with a structured CFP process
- You need sophisticated review management with scoring, anonymization, and multi-round reviews
- You want Pretix ticketing integration
- You need a modern REST API for program data
- You prefer Python/Django over Ruby

### Choose Frab if:

- You are organizing a community conference, unconference, or CCC-style event
- You need pentabarf-compatible XML export for conference app compatibility
- You prefer a simpler, more lightweight system
- You want the proven tool that has powered Chaos Communication Congress for years
- Ruby on Rails is your preferred technology stack

### Choose OSEM if:

- You are running a large open-source conference with hundreds of submissions
- You need integrated registration alongside CFP management in a single platform
- You want community voting features for session selection
- You prefer a full-featured event management system over a specialized CFP tool
- You are part of the openSUSE community or want similar infrastructure

## Cost Comparison

| Cost Factor | Pretalx | Frab | OSEM |
|---|---|---|---|
| **Software License** | Apache 2.0 (free) | MIT (free) | MIT (free) |
| **Hosting (VPS)** | ~$10-20/month | ~$10-20/month | ~$15-25/month |
| **Per-Event Fees** | $0 | $0 | $0 |
| **At 1,000 Submissions** | $0 | $0 | $0 |
| **Compared to Sessionize** | Save ~$500-1500/event | Save ~$500-1500/event | Save ~$500-1500/event |
| **Compared to Whova** | Save ~$1000-3000/event | Save ~$1000-3000/event | Save ~$1000-3000/event |

Commercial platforms typically charge $500-$3,000 per event depending on attendee count and feature requirements. Self-hosting eliminates these recurring costs entirely, with only server infrastructure expenses remaining.

For related reading, see our [Pretix vs Indico vs Open Event event management guide](../pretix-vs-indico-vs-openevent-self-hosted-event-management-guide-2026/) for ticketing and registration tools, our [MRBS vs Booked vs GRR room booking guide](../mrbs-vs-booked-vs-grr-self-hosted-room-booking-guide-2026/) for scheduling meeting spaces, and our [Cal.com vs Easy Appointments booking platform comparison](../self-hosted-scheduling-booking-platforms-cal-com-easy-appointments-2026/) for general scheduling solutions.

## FAQ

### What is the difference between CFP management and event ticketing?

CFP (Call for Papers) management focuses on the speaker and program side of a conference: collecting talk proposals, managing peer reviews, selecting sessions, and building the schedule. Event ticketing handles the attendee side: registration, payment processing, and ticket distribution. Pretalx specializes in CFP management while integrating with Pretix for ticketing. OSEM combines both in a single platform. Frab focuses purely on CFP and program management.

### Can I migrate my conference data between these platforms?

Limited migration is possible. Frab and OSEM both support pentabarf XML export, and Pretalx can import/export frab-compatible XML formats. For custom data (reviews, scores, speaker notes), you will need to export manually via each platform's API or database export tools. Plan your platform choice early to avoid migration pain.

### Do these platforms support virtual or hybrid conferences?

None of the three platforms have built-in video conferencing. However, they all allow you to add virtual room links and streaming URLs to schedule entries. Pretalx is the most flexible for this, as you can define custom session fields for recording URLs and streaming links. You would pair these tools with Jitsi, BigBlueButton, or your own streaming infrastructure for the actual video component.

### How many speakers and submissions can these platforms handle?

All three platforms are designed for conferences with hundreds of submissions. Pretalx has been tested with 1,000+ submissions at large events like EuroPython. Frab handles the Chaos Communication Congress schedule with hundreds of talks across multiple tracks. OSEM manages the openSUSE Conference with similar scale. For typical community conferences (50-500 submissions), all three perform well on modest hardware.

### Which platform has the best mobile app support?

None of the platforms ship a native mobile app, but all three generate standard conference data formats (iCal, XML, JSON) that can be consumed by third-party conference apps. Frab's pentabarf XML compatibility means it works with the widest range of existing conference apps. Pretalx's REST API is the best option for building a custom mobile experience.

### Are these platforms suitable for non-technical conference organizers?

Pretalx has the most polished user interface and is the most accessible to non-technical organizers. The CFP submission flow is intuitive, and the review interface is well-designed. Frab and OSEM have more utilitarian interfaces that assume some familiarity with conference management workflows. All three provide public program pages that look professional without any custom CSS work.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Pretalx vs Frab vs OSEM: Self-Hosted Conference CFP & Program Management 2026",
  "description": "Complete comparison of self-hosted conference program management tools — Pretalx, Frab, and OSEM. Docker setup guides, CFP workflows, speaker management, and schedule building for tech conferences and open-source events.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
