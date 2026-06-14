---
title: "Self-Hosted Quiz & Assessment Platforms: ClassQuiz vs QuizMaster vs HeyForm"
date: "2026-06-15"
tags: ["quiz", "assessment", "education", "self-hosted", "open-source", "e-learning", "interactive"]
draft: false
---

## Why Self-Host Your Quiz Platform?

Online quizzes and assessments have become essential tools for educators, corporate trainers, and community organizers. Whether you're running a classroom, hosting a pub quiz night, or conducting employee training assessments, having control over your quiz infrastructure matters.

Self-hosting your quiz platform gives you complete ownership of participant data, eliminates per-user licensing fees, and allows you to customize the experience to your specific needs. Unlike SaaS quiz tools that lock you into their ecosystem and pricing tiers, open-source quiz platforms can be deployed on your own server with full control over branding, question banks, and result analytics.

For organizations handling sensitive assessment data — such as schools with student records or companies with employee training results — self-hosting ensures compliance with data privacy regulations. You decide where the data lives and who can access it.

If you're already running a self-hosted LMS for course delivery, check out our [comparison of ILIAS, Sakai, and Canvas](../2026-06-13-self-hosted-lms-beyond-moodle-ilias-sakai-canvas/). For interactive learning experiences beyond quizzes, see our [guide to Oppia, Kolibri, and Adapt](../2026-06-07-self-hosted-interactive-learning-platforms-oppia-kolibri-adapt-guide/).

## Comparison at a Glance

| Feature | ClassQuiz | QuizMaster | HeyForm |
|---------|-----------|------------|---------|
| **GitHub Stars** | 698+ | 322+ | 8,828+ |
| **Primary Language** | Svelte | Scala | TypeScript |
| **License** | AGPL-3.0 | MIT | AGPL-3.0 |
| **Docker Support** | ✅ docker-compose | Manual setup | Manual deploy |
| **Real-time Multiplayer** | ✅ Yes | ✅ Yes | ❌ Forms-based |
| **Question Types** | Multiple choice, true/false, open text | Multiple choice, open question, numeric | Multiple choice, rating, file upload, 20+ types |
| **Self-Hosted Web UI** | ✅ Full SPA | ✅ Web app | ✅ Full web app |
| **Participant Mode** | PIN-based join | Direct link join | Shareable form link |
| **Analytics Dashboard** | ✅ Built-in | ❌ Minimal | ✅ Built-in |
| **API** | REST API | REST API | REST API |
| **Authentication** | Local + OIDC | Local | Local + OAuth |
| **Last Update** | June 2026 | April 2025 | June 2026 |

## ClassQuiz: The Kahoot! Alternative

ClassQuiz is the closest open-source equivalent to Kahoot!, designed specifically for classroom-style interactive quizzing. Built with Svelte for a fast, modern frontend experience, it supports real-time multiplayer sessions where participants join via a PIN code — exactly like the commercial platforms educators are familiar with.

**Key Strengths:**
- Real-time quiz sessions with leaderboards
- Teacher dashboard for managing question banks and sessions
- Student accounts and class management
- OIDC integration for school SSO systems
- Active development with regular updates

**Docker Compose Deployment:**

```yaml
version: "3.8"
services:
  classquiz:
    image: ghcr.io/mawoka-myblock/classquiz:latest
    container_name: classquiz
    ports:
      - "8080:80"
    environment:
      - CQ_SECRET_KEY=your-secret-key-here
      - CQ_DATABASE_URL=postgresql://classquiz:password@db:5432/classquiz
      - CQ_REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    container_name: classquiz-db
    environment:
      - POSTGRES_USER=classquiz
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=classquiz
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: classquiz-redis
    restart: unless-stopped
```

## QuizMaster: Self-Hosted Pub Quiz & Trivia

QuizMaster takes a different approach — it's designed for conducting quizzes over the internet with a focus on trivia competitions and pub-style quiz events. Written in Scala, it provides a lightweight web application where a quizmaster creates questions and participants answer through their browsers.

**Key Strengths:**
- Minimal server requirements
- Real-time scoring and answer validation
- Support for open-ended questions with manual grading
- Clean, straightforward interface
- MIT licensed for maximum flexibility

**Installation (Docker Build):**

```bash
# Clone and build
git clone https://github.com/nymanjens/quizmaster.git
cd quizmaster

# Start with sbt
sbt run

# Or build Docker image manually
sbt docker:publishLocal
docker run -d -p 9000:9000 quizmaster:latest
```

## HeyForm: Forms That Can Quiz

While HeyForm is primarily an open-source form builder, its extensive question type support (20+ types including quizzes, ratings, file uploads) makes it a viable platform for assessment-style quizzing. At 8,828+ GitHub stars, it has by far the largest community of the three tools.

**Key Strengths:**
- Extensive question type library (20+ types)
- Beautiful, modern UI with drag-and-drop builder
- Built-in analytics and response visualization
- OAuth authentication support
- Active development with rapid feature additions

**Self-Hosted Setup:**

```bash
# Clone the repository
git clone https://github.com/heyform/heyform.git
cd heyform

# Install dependencies
pnpm install

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Start development server
pnpm dev

# Or build for production
pnpm build
pnpm start
```

## Choosing the Right Platform

Your choice depends on your primary use case:

- **Choose ClassQuiz** if you need a classroom-style interactive experience with real-time multiplayer, PIN-based joining, and teacher-centric dashboards. It's the most polished Kahoot! replacement.

- **Choose QuizMaster** if you're running trivia events or pub quizzes where simplicity matters, and you don't need extensive analytics or authentication infrastructure.

- **Choose HeyForm** if your assessment needs go beyond simple quizzes — you need form-building flexibility, rich question types, file uploads for assignments, and detailed response analytics.

For organizations that need both quiz and comprehensive LMS functionality, our [comparison of exam platforms like TCExam and Moodle](../tcexam-vs-chamilo-vs-moodle-self-hosted-online-exam-platform-guide-2026/) covers more formal assessment scenarios including proctoring and certification.

## Deployment Architecture

For production deployments, consider placing your quiz platform behind a reverse proxy with SSL termination:

```nginx
server {
    listen 443 ssl;
    server_name quiz.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/quiz.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/quiz.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

All three platforms can benefit from database backups (especially for question banks) and regular updates. ClassQuiz and HeyForm are under active development; QuizMaster has slower release cycles but remains functional.

## Security Considerations

When hosting quiz platforms with participant data, ensure you:
- Use HTTPS for all connections (never serve quizzes over plain HTTP)
- Configure rate limiting to prevent answer brute-forcing
- Implement proper authentication if storing PII (student data)
- Regular backups of question banks and results
- Keep dependencies updated — especially database and Redis versions

For school deployments handling student data, ClassQuiz's OIDC integration allows you to hook into existing identity providers for proper access control.

## Performance Optimization and Scaling

For high-traffic quiz events with hundreds of simultaneous participants, consider these optimizations. ClassQuiz relies on Redis for real-time score synchronization — use Redis persistence (AOF) to prevent data loss if the service restarts mid-quiz. For HeyForm, enable PostgreSQL connection pooling (PgBouncer) if you expect thousands of concurrent form submissions.

Database performance is the bottleneck for all three platforms. Each quiz answer or form submission generates a database write. For events with 500+ participants submitting simultaneously, ensure your PostgreSQL instance has sufficient IOPS — cloud VPS SSDs typically handle 3,000-10,000 IOPS, which is adequate for all but the largest deployments.

Network latency matters for real-time quizzes. ClassQuiz uses WebSockets for instant leaderboard updates — ensure your reverse proxy (Nginx/Caddy) has WebSocket support enabled. For geographically distributed participants, deploy the quiz server in a region close to your primary audience, or use a CDN for static assets while keeping the WebSocket connection to a central server.

For long-term question bank management, all three platforms store questions in their databases. Schedule regular PostgreSQL dumps for backup, and consider version-controlling your question exports in Git for collaborative question authoring workflows.


## FAQ

### Can I use these platforms for corporate training assessments?

Yes. ClassQuiz works well for interactive training sessions with real-time results. HeyForm excels at creating compliance assessments, employee satisfaction surveys, and training evaluation forms with its rich question type library. Both support self-hosted deployment on internal networks.

### Do any of these support SCORM or xAPI for LMS integration?

ClassQuiz and QuizMaster do not natively support SCORM or xAPI. HeyForm can export results that can be manually imported into LMS platforms. For formal LMS-integrated assessments, consider our [exam platform comparison](../tcexam-vs-chamilo-vs-moodle-self-hosted-online-exam-platform-guide-2026/).

### How do these compare to Google Forms or Microsoft Forms?

Google Forms and Microsoft Forms are cloud-only solutions that store your data on their servers. Self-hosted alternatives give you data ownership and customization. HeyForm is the closest open-source alternative to Google Forms with a modern builder interface, while ClassQuiz adds real-time multiplayer features that neither Google nor Microsoft Forms provide.

### What are the resource requirements for hosting?

All three are lightweight. ClassQuiz requires PostgreSQL + Redis (about 512MB RAM minimum). QuizMaster is the lightest, running on a single JVM. HeyForm runs on Node.js with PostgreSQL (1GB RAM recommended). All three can run on a $5-10/month VPS.

### Can I import questions from other quiz platforms?

ClassQuiz supports importing questions via its REST API. HeyForm can import from its own format. For bulk migration between platforms, you may need to write a custom script using the respective APIs. Most platforms support CSV export of results.

### Is there a self-hosted alternative that works without JavaScript?

QuizMaster provides basic functionality without JavaScript for quiz-takers, though the quizmaster interface requires it. For fully server-rendered quiz experiences, you'd need to look at more traditional LMS platforms like Moodle that support progressive enhancement.

---

<section>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Quiz & Assessment Platforms: ClassQuiz vs QuizMaster vs HeyForm",
  "description": "Comprehensive comparison of open-source self-hosted quiz and assessment platforms. Compare ClassQuiz (Kahoot! alternative), QuizMaster (trivia engine), and HeyForm (form builder with quiz capabilities) — deployment guides with Docker Compose, feature comparison, and architecture recommendations.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
