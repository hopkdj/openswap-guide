---
title: "Self-Hosted Newsroom Stack in 2026: Superdesk vs Wagtail vs Coral Compared"
date: "2026-09-30"
tags: ["self-hosted", "cms", "publishing", "newsroom", "journalism", "open-source", "wagtail"]
cover: "/img/screenshots/wagtail-admin-2026.jpg"
draft: false
---

Enterprise publishing platforms quote **six figures per year** for a mid-size newsroom, which is why news organisations with shrinking budgets keep rebuilding their stack out of open-source parts. The catch is that "newsroom software" is not one product — it is three problems: an editing and production workflow, a content management system that renders the site, and an audience engagement layer that keeps readers arguing productively in the comments.

This guide covers one serious open-source option for each layer, with live GitHub data pulled on 2026-09-30: **Superdesk** (production and editorial workflow), **Wagtail** (publishing CMS), and **Coral** (commenting and engagement). Used together they replace a proprietary suite; used individually each is a solid answer to one specific problem.

## TL;DR — Quick Verdict

- **Running a wire-style newsroom with planning, ingest and multi-desk workflows?** Use **Superdesk** (754⭐). It is the only open-source system in this list built around editorial production rather than pages.
- **Just need to publish articles, landing pages and data journalism with a clean editorial UI?** Use **Wagtail** (20,510⭐). It is a mature Django CMS with the best admin experience in open source, and 26× the community of Superdesk.
- **Your problem is comments, not content?** Use **Coral** (1,999⭐). Vox Media's commenting platform is a drop-in engagement layer that works with any CMS.

The honest summary: if you expect one tool to do all three jobs, you will be disappointed by all three. Pick the layer that hurts most and start there.

## Comparison Table

| Project | Layer | Stars | Last push | Stack | Deployment | Best for |
|---|---|---|---|---|---|---|
| **Superdesk** | Editorial production | 754⭐ | 2026-09-29 | Python, MongoDB, Elasticsearch, Redis, JS client | Docker Compose (official images) | Planning, ingest, multi-desk newsrooms |
| **Wagtail** | Publishing CMS | 20,510⭐ | 2026-09-29 | Python, Django, PostgreSQL | pip install or container | Article sites, data journalism, landing pages |
| **Coral** | Audience engagement | 1,999⭐ | 2026-09-04 | TypeScript, Node.js, MongoDB, Redis | Docker Compose | Comments, moderation, reader Q&A |

All three are production software with years of deployment history behind them, not weekend projects. The differences are architectural: Superdesk is an operational system for a newsroom *process*, Wagtail is a developer-friendly CMS, and Coral is a service you bolt onto whatever you already publish with.

## Scenario Decision Matrix

| Your situation | Recommended stack | Why |
|---|---|---|
| 20+ journalists, planning meetings, wires, multiple desks | Superdesk (+ Wagtail for public site) | Superdesk models planning items, assignments and desks; a page CMS does not |
| Small digital publication, 3–10 writers, heavy SEO and data stories | Wagtail alone | Faster to launch, easier to theme, largest talent pool for hiring contributors |
| Existing site on WordPress or a static generator, comments are chaos | Coral | Adds comment threading, moderation queues and reader accounts without migrating content |
| Public broadcaster with archive requirements | Superdesk + object storage | Editorial metadata and versioning survive site redesigns |
| Developer-heavy team that wants content as structured data | Wagtail + headless API | StreamField gives structured, reusable content blocks; our [headless CMS comparison](../2026-05-04-payload-cms-vs-strapi-vs-directus-self-hosted-headless-cms/) covers the API-first alternatives |

## Superdesk — Editorial Production, Not Page Building

Superdesk comes from Sourcefabric, the organisation behind long-running journalism infrastructure, and it is built around the workflow of a newsroom: ingest from wires, a planning module for assignments and coverage, desks with configurable stages, and publishing destinations. Article output can fan out to multiple targets — a website, an app, a wire partner.

Its Compose file shows the production shape honestly, including dependencies that are worth noticing:

```yaml
services:
  mongodb:
    image: mongo:4
  redis:
    image: redis:3
  elastic:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.29
  superdesk:
    image: sourcefabricoss/superdesk:latest
    environment:
      - REDIS_URL=redis://redis:6379/1
      - DEFAULT_TIMEZONE=Europe/Prague
      - SECRET_KEY=generate-your-own
    ports:
      - "8080:8080"
  superdesk-client:
    image: sourcefabricoss/superdesk-client:latest
    environment:
      - SUPERDESK_URL=http://localhost:8080/api
      - SUPERDESK_WS_URL=ws://localhost:8080/ws
    ports:
      - "8080:80"
```

Two immediate operational notes. First, **replace `SECRET_KEY` with a generated value** — the upstream file ships a literal example. Second, the pinned dependency versions (MongoDB 4, Redis 3) are older than what you would choose for a greenfield deployment; treat them as a baseline to modernise rather than a target, and test thoroughly if you bump the majors, because Superdesk's data layer is opinionated.

The payoff is real: this is the only open-source system here that models *editorial operations* — who is covering what, which items are ready, what published where. Building that on top of a page CMS is a project; Superdesk gives it to you as a product.

## Wagtail — The Publishing CMS With the Best Editorial UI

Wagtail is the pragmatic choice for most digital publications. It is a Django CMS with a well-designed admin, a structured content approach (StreamField) that lets editors assemble pages from typed blocks, and an ecosystem that supports versioning, moderation workflow, multi-language content and image renditions out of the box.

![Wagtail admin interface](/img/screenshots/wagtail-admin-2026.jpg "Wagtail's page editing interface — the admin UI that makes it the default choice for digital publications")

Getting a working site takes minutes:

```bash
python -m venv .venv && source .venv/bin/activate
pip install wagtail
wagtail start newsroom
cd newsroom
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# admin: http://localhost:8000/admin/
```

For production, the standard Django checklist applies — PostgreSQL instead of SQLite, `DEBUG=False`, a real `ALLOWED_HOSTS`, static files served by your reverse proxy, and a task runner for image renditions so page requests stay fast. The reason to pick Wagtail over a headless CMS is the editorial experience: reporters and editors get a WYSIWYG page builder, not a JSON editor. The reason to pick it over Superdesk is scope — if you do not need desk-based production workflows, you should not pay for that complexity.

## Coral — Commenting and Engagement as a Service You Own

Coral started at Vox Media and is still the most credible open-source answer to the "our comments are a cesspool" problem. It provides threaded comments, reader accounts, moderation queues, reaction features and optional offline/online state synchronisation, and it talks to any CMS over its API — meaning you can keep publishing with Wagtail, WordPress or a static generator and still get a real engagement layer.

Its server Compose file is small enough to reason about completely:

```yaml
services:
  jobs:
    image: coralproject/talk:7
    restart: always
    environment:
      - MONGODB_URI=${MONGODB_URI:-mongodb://mongo:27017/coral}
      - REDIS_URI=${REDIS_URI:-redis://redis:6379}
      - SIGNING_SECRET=${SIGNING_SECRET}
  nginx:
    image: nginx:latest
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - jobs
    ports:
      - "4000:4000"
```

Set `SIGNING_SECRET` from your environment, never from the repository, and terminate TLS in front of the nginx container. The operational work that matters is not the deployment — it is moderation staffing and a written comment policy. Coral gives you the tools; it does not give you a community.

## Pitfalls, Migration Notes and Operational Traps

1. **Do not pick a platform for a problem you do not have.** Superdesk before you have a desk structure wastes months. Coral before you have moderation capacity creates a liability. Start with the layer that is actually broken.
2. **Pin and modernise your dependencies deliberately.** The Superdesk Compose file's MongoDB 4 and Redis 3 baselines will not match your hardening standards. Plan a version-bump sprint with a full data restore test rather than upgrading in place.
3. **Media storage is where budgets die.** Article images, video and audio grow without limit. Put media in object storage (S3-compatible) with a lifecycle policy from the start; moving a multi-terabyte media library later is painful.
4. **Search relevance is a product decision.** Superdesk depends on Elasticsearch, and Wagtail's default search is intentionally basic. Decide what readers and editors should be able to find — by desk, by author, by section, by date — before you tune anything.
5. **Editorial metadata outlives your design.** Store bylines, desks, tags, licences and corrections as structured fields, not inside HTML body fields. When you redesign in three years, the metadata survives and the HTML does not.
6. **Treat comments as regulated data.** Reader accounts, IP logs and comment content have privacy implications in most jurisdictions. Have a retention policy, a takedown process and a documented moderation escalation path before launch.
7. **Back up content and database together, and test restores.** A CMS restore that recovers posts but not media (or the reverse) produces a site that looks published and renders broken. Our [backup integrity verification workflow](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/) is the pattern to copy.
8. **Plan the front end as a separate concern.** Both Superdesk and Wagtail are strongest when the public theme is a thin layer over well-structured content — that is also what makes a later migration survivable. Related reading: our [knowledge base comparison](../2026-04-24-docmost-vs-outline-vs-affine-self-hosted-knowledge-base-guide-2026/) and [self-hosted wiki engines guide](../2026-04-23-mediawiki-vs-xwiki-vs-dokuwiki-self-hosted-wiki-engines-guide-2026/) cover the internal-documentation side of the same problem.

## FAQ

### Can open-source tools really replace an enterprise newsroom platform?

For content production, page rendering and comments: yes, and many small and mid-size publications already run exactly this way. What you give up is an integrated suite with one vendor, one support contract and one upsell path for every new requirement. What you gain is control over your archive and no per-seat pricing. Newsrooms that struggle usually underestimate the integration work between the layers, not the software itself.

### Superdesk or Wagtail — which should I start with?

Ask whether your bottleneck is *process* or *publishing*. If you run planning meetings, assignments and multiple desks feeding a shared output, Superdesk models that reality. If your bottleneck is simply producing and publishing well-structured articles quickly, Wagtail will get you live in days and Superdesk will get you live in months. Some organisations run both: Superdesk for production, a CMS for the public site.

### Is Coral still maintained?

Coral's repository was last pushed on 2026-09-04 and it remains the reference open-source commenting platform, originally from Vox Media. It is a mature codebase rather than a fast-moving one, which is usually fine for a component whose job is to store and moderate comments — but budget time to review the codebase yourself if your compliance requirements are strict.

### How much infrastructure does this stack need?

A realistic minimum for a small publication is one application host with 4 vCPU and 8 GB RAM for the CMS plus database, and a separate instance if you run Superdesk's Elasticsearch, MongoDB and Redis alongside it. Coral adds MongoDB and Redis as well. Container orchestration is not mandatory, but centralised logs and monitored backups are — editorial content is irreplaceable.

### What about migrating content later?

Export early and export in plain text. All three systems can produce structured exports; none of them can ingest another platform's database dump. Keep a canonical export of every article as Markdown or JSON with its metadata sidecar, refreshed monthly, and any future migration becomes a rendering exercise instead of an archaeology project.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Newsroom Stack in 2026: Superdesk vs Wagtail vs Coral Compared",
  "description": "Comparison of open-source newsroom software layers: Superdesk for editorial production, Wagtail as the publishing CMS and Coral for audience engagement, with live GitHub data, Docker Compose configs and migration pitfalls.",
  "datePublished": "2026-09-30",
  "dateModified": "2026-09-30",
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
