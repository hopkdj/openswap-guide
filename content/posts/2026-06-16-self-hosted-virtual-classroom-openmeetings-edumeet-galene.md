---
title: "Self-Hosted Virtual Classroom Platforms: OpenMeetings vs EduMeet vs Galène Compared (2026)"
date: "2026-06-16"
tags: ["virtual-classroom", "webrtc", "video-conferencing", "education", "self-hosted", "open-source", "remote-learning"]
draft: false
---

Remote learning and virtual classrooms have become permanent fixtures in education and corporate training. While commercial platforms like Zoom and Microsoft Teams dominate the market, open-source alternatives offer cost savings, data sovereignty, and customization that proprietary solutions cannot match. Whether you run an online school, a corporate training program, or community workshops, a self-hosted virtual classroom gives you complete control over your learning environment.

In this guide, we compare three open-source virtual classroom and web conferencing platforms — **Apache OpenMeetings**, **EduMeet**, and **Galène** — covering their features, deployment options, and ideal use cases.

## Why Self-Host Your Virtual Classroom?

Self-hosting a virtual classroom platform puts you in control of your educational infrastructure. First, **data privacy and sovereignty** — student data, recordings, and meeting content remain on your servers, not in a third-party cloud. For educational institutions subject to FERPA, GDPR, or local data protection laws, this is non-negotiable.

Second, **cost predictability** — commercial platforms charge per-host licenses, per-minute meeting fees, or per-student seat costs that scale unpredictably with growth. A self-hosted open-source platform costs only your server infrastructure, which you control directly. For an institution with 500 concurrent students, the savings can exceed $10,000 per year.

Third, **customization and integration** — open-source platforms let you integrate with your existing LMS (Moodle, Canvas), authentication systems (LDAP, SAML), and branding requirements. You can add custom features, white-label the interface, and adapt the platform to your specific teaching methodology.

For complementary self-hosted communication tools, see our [video conferencing guide](../bigbluebutton-vs-mirotalk-self-hosted-video-conferencing-guide-2026/), [WebRTC SFU comparison](../2026-04-25-janus-gateway-vs-mediasoup-vs-livekit-self-hosted-webrtc-sfu-guide-2026/), and [TURN/STUN server guide](../self-hosted-turn-stun-servers-coturn-restund-pion-webrtc-guide-2026/).

## Comparison Table

| Feature | Apache OpenMeetings | EduMeet | Galène |
|---------|---------------------|---------|--------|
| **Stars** | 677 | 1,343 | 1,332 |
| **Language** | Java | JavaScript (Node.js) | Go |
| **License** | Apache 2.0 | MIT | MIT |
| **Whiteboard** | Yes (full-featured) | No | No |
| **Breakout Rooms** | Yes | Via mediasoup | Manual |
| **Screen Sharing** | Yes | Yes | Yes |
| **Recording** | Yes (server-side) | No (browser-based) | No (disk writer plugin) |
| **File Sharing** | Yes (in-room) | No | No |
| **Polls & Quizzes** | Yes | No | No |
| **Room Management** | Calendar + invite | Link-based rooms | Token-based rooms |
| **Auth Integration** | LDAP, OAuth, DB | OIDC (optional) | LDAP (plugin) |
| **Docker Support** | Yes | Yes | Yes |
| **Resource Usage** | High (Java backend) | Medium (Node.js) | Low (Go binary) |
| **Best For** | Full LMS-like classroom | Lightweight WebRTC meetings | Minimalist video calls |

## Apache OpenMeetings: The Full-Featured Virtual Classroom

[Apache OpenMeetings](https://github.com/apache/openmeetings) (677 stars) is the most feature-complete open-source virtual classroom platform. As an Apache Software Foundation project, it benefits from mature governance, extensive documentation, and a long history of production use in educational institutions worldwide.

OpenMeetings goes beyond video conferencing — it provides a complete virtual classroom experience with an interactive whiteboard, document sharing (PDF, Office, images), screen sharing, session recording, polls and quizzes, and a calendar-based scheduling system. It is closer to a Learning Management System (LMS) than a simple video conferencing tool.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  openmeetings:
    image: apache/openmeetings:latest
    container_name: openmeetings
    ports:
      - "5443:5443"
      - "8888:8888"
    volumes:
      - om_data:/opt/openmeetings/data
    environment:
      - OM_DB_TYPE=postgresql
      - OM_DB_HOST=db
      - OM_DB_NAME=openmeetings
      - OM_DB_USER=openmeetings
      - OM_DB_PASS=changeme
      - OM_ADMIN_USER=admin
      - OM_ADMIN_PASS=changeme
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    container_name: om_db
    volumes:
      - om_pg:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=openmeetings
      - POSTGRES_PASSWORD=changeme
      - POSTGRES_DB=openmeetings
    restart: unless-stopped

volumes:
  om_data:
  om_pg:
```

OpenMeetings integrates with LDAP and OAuth for institutional authentication, supports calendar integration (CalDAV), and provides REST APIs for integration with external LMS platforms. The built-in recording feature captures both video and whiteboard activity, producing downloadable recordings that students can review asynchronously.

For institutions that need a comprehensive virtual classroom with whiteboarding, file sharing, breakout rooms, and quizzing in a single platform, OpenMeetings is unmatched among open-source options. The trade-off is resource usage — the Java backend requires more memory (4 GB minimum recommended) than the lighter alternatives.

## EduMeet: Modern WebRTC with mediasoup

[EduMeet](https://github.com/edumeet/edumeet) (1,343 stars) takes a modern approach to virtual classrooms. Built on WebRTC with the mediasoup Selective Forwarding Unit (SFU), it delivers low-latency, high-quality video and audio without the overhead of a traditional application server.

Unlike OpenMeetings, EduMeet does not include whiteboarding, quizzes, or file sharing out of the box. It focuses on being the best possible multiparty video meeting platform — and it excels at that. The mediasoup SFU architecture means it can handle 50+ participants in a single room with minimal server resources.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  edumeet-server:
    image: edumeet/edumeet:latest
    container_name: edumeet_server
    ports:
      - "443:443"
      - "40000-49999:40000-49999/udp"
    volumes:
      - ./config:/usr/src/app/config
    environment:
      - MEDIASOUP_LISTEN_IP=0.0.0.0
      - MEDIASOUP_ANNOUNCED_IP=your.public.ip
      - MEDIASOUP_MIN_PORT=40000
      - MEDIASOUP_MAX_PORT=49999
      - AUTH_OIDC_ENABLED=false
    restart: unless-stopped
```

EduMeet's minimalist philosophy has advantages: the interface is clean and intuitive, with virtually no learning curve. Participants join via a simple link and immediately see each other's video. There are no downloads, no plugins, and no account creation required for guests.

For organizations that already have a separate LMS (Moodle, Canvas) and just need a reliable, high-quality video component, EduMeet is an excellent fit. Its resource efficiency — a single server can support hundreds of concurrent users — makes it the most cost-effective option for large-scale deployments.

## Galène: Minimalist Go-Based Video Conferencing

[Galène](https://github.com/jech/galene) (1,332 stars) is a videoconference server written in Go that prioritizes simplicity and performance above all else. Its entire server is a single Go binary with no external dependencies — no database, no message queue, no application server.

Galène provides pure video and audio conferencing with screen sharing, chat, and (with plugins) recording and LDAP authentication. It uses WebRTC with Pion, a pure-Go WebRTC implementation, making it extremely resource-efficient.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  galene:
    image: jech/galene:latest
    container_name: galene
    ports:
      - "8443:8443"
      - "1194:1194/udp"
    volumes:
      - ./data:/data
      - ./groups:/groups
      - ./records:/records
    command:
      - "-http=:8443"
      - "-turn=:1194"
      - "-data=/data"
      - "-groups=/groups"
      - "-insecure"
    restart: unless-stopped
```

Galène's group-based room system is unique — rooms are configured via JSON files with access tokens, rather than through a web UI. This makes it highly scriptable but less user-friendly for non-technical administrators:

```json
{
    "op": {
        "display-name": "Operators",
        "op": [{"username": "alice"}],
        "presenter": [{}],
        "allow-recording": true,
        "allow-subgroups": true
    },
    "public": {
        "display-name": "Public discussion",
        "op": [{"username": "bob"}],
        "presenter": [{"username": "bob"}],
        "allow-anonymous": true
    }
}
```

Galène is ideal for technical teams that want a fast, reliable video conferencing server with minimal resource usage. A Galène instance uses approximately 50 MB of RAM at idle and can handle 100+ participants on a modest VPS. For hackathons, developer standups, and ad-hoc technical meetings, its no-frills approach is often exactly what is needed.

## Deployment Considerations for Production

Running a virtual classroom in production requires attention to network configuration and scaling. Here are key recommendations:

**TURN/STUN servers are essential** — WebRTC needs a TURN server for participants behind symmetric NATs (common in corporate and university networks). Deploy coturn alongside your virtual classroom:

```yaml
services:
  coturn:
    image: coturn/coturn:latest
    network_mode: host
    command:
      - "-n"
      - "--log-file=stdout"
      - "--external-ip=$$(detect-external-ip)"
      - "--min-port=49160"
      - "--max-port=49200"
      - "--lt-cred-mech"
      - "--user=turnuser:turnpassword"
      - "--realm=yourdomain.com"
```

**Reverse proxy for SSL termination** — all three platforms support running behind Nginx or Caddy for automatic HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name meet.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/meet.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meet.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Scaling strategy** — OpenMeetings scales vertically (bigger server). EduMeet scales horizontally (multiple SFU instances) thanks to mediasoup's architecture. Galène scales both ways, but rooms are bound to a single server. For 500+ concurrent users, deploy multiple Galène or EduMeet instances behind a load balancer.

## FAQ

### Can these platforms replace Zoom for my school?

Yes, with caveats. OpenMeetings comes closest to the Zoom feature set, with whiteboarding, breakout rooms, polling, and recording. However, it requires more server administration than Zoom's SaaS model. For large institutions (1,000+ concurrent users), you will need dedicated infrastructure and an IT team comfortable with server management. EduMeet and Galène are lighter but lack built-in classroom features like whiteboarding — pair them with external tools if needed.

### How many participants can each platform support?

OpenMeetings supports 50-100 participants per room on a server with 8 GB RAM. EduMeet handles 50-200 participants per room via mediasoup's efficient SFU architecture, and multiple rooms can run simultaneously. Galène handles 100-200 participants on modest hardware (2 GB RAM) thanks to its Go-based architecture. All three scale better with more server resources — the primary bottleneck is usually bandwidth, not CPU.

### Do I need a TURN server for these platforms?

Yes, for production deployments. WebRTC uses peer-to-peer connections by default, but approximately 10-15% of participants (those behind symmetric NATs or restrictive firewalls) will need TURN relay. Without a TURN server, these users either cannot connect or experience one-way audio/video. Deploy coturn on the same server and configure it in your platform settings.

### Can I record virtual classroom sessions?

OpenMeetings supports server-side recording natively — recordings capture video, audio, and whiteboard activity and are stored as downloadable files. Galène supports recording via its disk writer plugin, which saves WebRTC streams to disk. EduMeet does not include built-in recording (it relies on browser-based MediaRecorder API, which requires client-side effort). For compliance-heavy use cases, OpenMeetings is the best choice.

### How do these compare to BigBlueButton?

BigBlueButton is another popular open-source virtual classroom platform, and we have a [dedicated comparison of BigBlueButton vs MiroTalk](../bigbluebutton-vs-mirotalk-self-hosted-video-conferencing-guide-2026/). In brief: BigBlueButton is more feature-rich than OpenMeetings in some areas (integrated LMS plugins, HTML5 client) but has a heavier server footprint. OpenMeetings offers a more traditional Java web application experience. EduMeet and Galène are fundamentally different — they focus on video quality over classroom features.

### What is the minimum hardware requirement?

Galène: 1 vCPU, 512 MB RAM (yes, really — it is that efficient). EduMeet: 2 vCPU, 2 GB RAM for a small deployment (1-2 rooms, 10-20 users). OpenMeetings: 4 vCPU, 4 GB RAM minimum (Java application server + PostgreSQL). All three benefit from SSD storage for recordings. For any deployment, budget at least 1 Mbps of upload bandwidth per concurrent video participant.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Virtual Classroom Platforms: OpenMeetings vs EduMeet vs Galène Compared (2026)",
  "description": "Compare three open-source virtual classroom platforms — Apache OpenMeetings, EduMeet, and Galène — with Docker Compose deployment examples, performance benchmarks, and selection guide for education and training.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
