---
title: "Self-Hosted Design Feedback & Review Platforms: Penpot Review vs Pastel vs Saber"
date: "2026-06-19"
tags: ["design-review", "design-feedback", "collaboration", "annotation", "penpot", "ux-review", "self-hosted"]
draft: false
---

## Introduction

Design review is a critical part of any product development workflow. Teams need to collect feedback on mockups, annotate specific UI elements, track revision requests, and ensure design consistency before engineering implementation begins. While Figma's commenting system and tools like Zeplin have set the standard for design handoff, the open-source ecosystem now offers self-hosted alternatives that give teams complete control over their design review process.

This guide compares three approaches to self-hosted design feedback: Penpot's built-in review and commenting system, Pastel's canvas-based feedback collection, and Saber's annotation-focused workflow. Each takes a different approach to solving the design feedback problem.

## Comparison Table

| Feature | Penpot | Pastel (Canvas) | Saber (Review) |
|---------|--------|-----------------|----------------|
| **GitHub Stars** | 50,348+ | Community-driven | Annotation-focused |
| **Primary Use** | Full design tool + review | Visual feedback canvas | PDF/image annotation |
| **Self-Hosted** | ✅ Docker, full self-host | ✅ Self-hostable | ✅ Docker deployment |
| **Comment Threads** | ✅ Inline comments | ✅ Canvas comments | ✅ Annotations on files |
| **Version Comparison** | ✅ Design version history | ❌ | ❌ |
| **Prototype Review** | ✅ Interactive prototypes | ❌ Static only | ❌ |
| **Annotation Tools** | ✅ Pin, rectangle, freehand | ✅ Arrow, highlight | ✅ Stamps, text, shapes |
| **Email Notifications** | ✅ SMTP integration | ✅ Configurable | ✅ Email alerts |
| **Slack Integration** | ✅ Webhooks | ✅ Integrations | ❌ |
| **Guest Review** | ✅ Shareable links | ✅ Public canvases | ✅ Shareable review links |
| **Design Handoff** | ✅ Code specs, CSS export | ❌ | ❌ |
| **Deployment** | Docker Compose | Docker | Docker |
| **License** | MPL 2.0 | MIT | Open source |

## Penpot: Design + Review in One Platform

[Penpot](https://github.com/penpot/penpot) is the leading open-source design and prototyping platform, with over 50,000 GitHub stars. Unlike standalone review tools, Penpot integrates design creation and feedback in a single platform — designers create mockups in Penpot, and stakeholders leave comments directly on the design canvas. This eliminates the "export to image → upload to review tool → collect feedback → update design file" cycle.

Penpot's review features include threaded comments pinned to specific design elements, version history for comparing iterations, and shareable prototype links that allow stakeholders to click through interactive prototypes and leave feedback at specific screens. The platform supports real-time collaboration, so multiple reviewers can comment simultaneously.

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  penpot-frontend:
    image: penpotapp/frontend:latest
    ports:
      - "9001:80"
    volumes:
      - penpot_assets:/opt/data/assets
    depends_on:
      - penpot-backend
    environment:
      - PENPOT_FLAGS=enable-registration enable-login-with-password

  penpot-backend:
    image: penpotapp/backend:latest
    volumes:
      - penpot_assets:/opt/data/assets
    depends_on:
      - penpot-postgres
      - penpot-redis
    environment:
      - PENPOT_PUBLIC_URI=https://design.yourdomain.com
      - PENPOT_DATABASE_URI=postgresql://penpot:password@penpot-postgres/penpot
      - PENPOT_REDIS_URI=redis://penpot-redis/0
      - PENPOT_ASSETS_STORAGE_BACKEND=assets-fs
      - PENPOT_STORAGE_ASSETS_FS_DIRECTORY=/opt/data/assets
      - PENPOT_SMTP_HOST=mail.yourdomain.com
      - PENPOT_SMTP_PORT=587
      - PENPOT_SMTP_USER=your_email
      - PENPOT_SMTP_PASSWORD=your_password

  penpot-postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_USER=penpot
    volumes:
      - pg_data:/var/lib/postgresql/data

  penpot-redis:
    image: redis:7-alpine

volumes:
  penpot_assets:
  pg_data:
```

## Pastel: Canvas-Based Visual Feedback

Pastel takes a different approach — instead of being a full design tool, it focuses specifically on visual feedback collection. You upload a design mockup (PNG, JPG, or PDF), and reviewers add comments, annotations, and reactions directly on the image canvas. Pastel is ideal for teams that create designs in various tools (Figma, Sketch, Photoshop) and need a centralized feedback platform.

Pastel's canvas-based system organizes feedback into "canvases" — each canvas represents a design screen or page. Reviewers can add arrow annotations, highlight areas, and leave threaded comments. The lightweight approach means Pastel is faster to deploy and requires less infrastructure than full design tools. It is particularly useful for agencies that need to collect client feedback on multiple design iterations.

## Saber: Annotation-Focused Document Review

Saber is an open-source document review and annotation platform designed for reviewing PDFs, images, and design specifications. Unlike Pastel's canvas approach, Saber focuses on precise annotations — reviewers can add stamps (approved, rejected, needs changes), draw shapes, add text comments, and measure dimensions directly on uploaded files.

Saber is well-suited for technical design reviews where precise feedback is required — for example, reviewing UI specification documents, design system PDFs, or accessibility audit reports. The annotation tools include measurement rulers, color pickers, and comparison modes for side-by-side review of design iterations.

## Why Self-Host Your Design Review Process?

Design files contain sensitive intellectual property — unreleased product designs, branding assets, and strategic UI decisions. Self-hosting your design review platform keeps these assets within your infrastructure rather than on a third-party SaaS server. This is particularly important for agencies working with enterprise clients who have strict data residency requirements.

Self-hosting also provides unlimited reviewer seats. Commercial tools typically charge per reviewer or per project, which adds up quickly for agencies with many clients or large organizations with multiple stakeholder groups. For teams that also need prototyping capabilities, see our [UX prototyping tools guide](../2026-06-02-linux-power-analysis-powertop-powerstat-turbostat-guide/). If your team uses design systems, our [design token management comparison](../2026-05-01-countly-vs-posthog-vs-matomo-self-hosted-product-analytics-platforms/) covers self-hosted alternatives.

## Choosing the Right Tool

**Choose Penpot if:** Your team needs both design creation and review in a single platform. Penpot replaces Figma entirely — you design, prototype, and collect feedback without switching tools. Best for teams that want to move their entire design workflow to open-source.

**Choose Pastel if:** Your team creates designs in various tools and needs a lightweight, centralized feedback platform. Pastel's canvas-based approach is intuitive for non-designer stakeholders and requires minimal training.

**Choose Saber if:** Your review process involves detailed technical annotations on PDF specifications, design system documents, or accessibility reports. Saber's precision annotation tools are best for formal design QA reviews.
## Integrating Design Review into CI/CD Pipelines

Modern design teams are increasingly adopting DevOps-style workflows where design reviews are automated and integrated into the development pipeline. By connecting your self-hosted design review platform to CI/CD systems, you can automatically trigger reviews when designs change, generate visual regression reports, and block deployments if design inconsistencies are detected.

For Penpot users, the platform's webhook system can notify CI/CD pipelines when design files are updated. You can configure a GitHub Actions workflow that runs visual regression tests (using tools like BackstopJS or Percy CLI) comparing the latest design exports against production screenshots, and posts the results back to Penpot as review comments. Pastel's webhook integration allows triggering Slack notifications and Jira task creation when feedback is submitted, creating an automated bridge between design review and development task tracking. Saber's annotation data can be exported as structured JSON and consumed by CI/CD scripts to generate compliance reports for design QA audits. This pipeline integration transforms design review from a manual, ad-hoc process into an automated quality gate — ensuring that every UI change passes design review before reaching production.


## FAQ

### Can these tools replace Figma's commenting system?

Penpot comes closest to replacing Figma's full workflow — it handles both design creation and commenting in a single platform. Pastel and Saber complement Figma rather than replace it — you export mockups from Figma and use Pastel/Saber for stakeholder feedback. If your team is already using Figma and only needs better feedback collection, Pastel provides a dedicated review canvas without requiring designers to switch tools.

### How do I invite external reviewers (clients, stakeholders)?

All three platforms support guest review. Penpot allows sharing prototype links that anyone can view and comment on without an account. Pastel generates shareable canvas links with optional password protection. Saber creates review links that external users can access to leave annotations. Email notifications keep reviewers informed of new comments and updates.

### What about design handoff to developers?

This is where Penpot excels — it generates CSS code, measures distances between elements, and exports assets in multiple formats directly from designs. Developers can inspect designs, copy CSS properties, and download assets without needing design tool access. Pastel and Saber do not have dedicated developer handoff features — they focus on the review and feedback stage. For comprehensive handoff, combine Pastel for stakeholder review with Penpot's inspect mode for developer handoff.

### Can I integrate these tools with project management platforms?

Penpot supports webhooks that can send comment notifications to Slack, Discord, or custom endpoints. Pastel can trigger webhooks on comment activity. Saber supports SMTP email notifications. For automated task creation, you can use integration platforms like n8n or Node-RED to listen for webhook events and create tasks in your project management tool. None of the three have native Jira/Linear/Asana integrations out of the box.

### How much storage do I need for a design review server?

Design files and review annotations are relatively lightweight. A design team of 10 people creating 50 mockups per week with feedback will use approximately 5-10 GB of storage per month. Penpot requires more storage since it stores full design files with version history. Pastel and Saber primarily store compressed images and annotation data, requiring less space. All three support external storage backends (S3, MinIO) for scaling.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Design Feedback & Review Platforms: Penpot Review vs Pastel vs Saber",
  "description": "Compare self-hosted design review and feedback platforms: Penpot, Pastel, and Saber. Includes Docker Compose deployment, annotation tools comparison, and guide to choosing the right design review workflow.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
  "author": {
    "@type": "Organization",
    "name": "Pi Stack"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Pi Stack",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
