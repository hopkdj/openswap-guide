---
title: "Self-Hosted Employee Intranet Platforms: HumHub vs Liferay vs eXo Platform"
date: "2026-06-04"
tags: ["intranet", "collaboration", "employee-portal", "self-hosted", "enterprise", "knowledge-management"]
draft: false
---

A well-designed employee intranet serves as the digital headquarters for your organization — a central hub where teams communicate, collaborate, find information, and stay aligned. While SaaS options like Microsoft SharePoint and Google Workspace dominate the enterprise market, self-hosted open-source intranet platforms offer data sovereignty, customization flexibility, and long-term cost control. This article compares three leading self-hosted solutions: HumHub, Liferay Portal, and eXo Platform.

## Why Self-Host Your Company Intranet?

**Data sovereignty**: Your employee communications, HR documents, and internal discussions remain on servers you control. This is critical for organizations in regulated industries (healthcare, finance, government) or regions with strict data residency requirements.

**Unlimited customization**: Open-source intranet platforms can be tailored to your specific workflows without waiting for a vendor's feature roadmap. Want to integrate with your custom ERP? Add a widget. Need a specific approval workflow? Build it.

**Cost predictability**: Self-hosted platforms have no per-user pricing. Whether you have 50 employees or 50,000, your infrastructure costs scale linearly with hardware, not exponentially with SaaS licensing fees. A $100/month dedicated server can serve a 500-person intranet comfortably.

**Integration depth**: Self-hosted platforms can connect directly to your internal systems — LDAP/Active Directory for authentication, internal APIs for data feeds, and SMTP servers for notifications — without data leaving your network.

For related team collaboration tools, see our [project management comparison](../self-hosted-project-management-openproject-taiga-leantime-guide-2026/) and [self-hosted CRM guide](../2026-05-07-monica-vs-espocrm-vs-suitecrm-self-hosted-crm-guide/).

## Tool Comparison

| Feature | HumHub | Liferay | eXo Platform |
|---------|--------|---------|--------------|
| **GitHub Stars** | 6,691 | 2,249 | Community (docker) |
| **Language** | PHP (Yii2) | Java | Java |
| **License** | AGPLv3 | LGPL 2.1 | AGPLv3 |
| **Database** | MySQL/MariaDB, PostgreSQL | MySQL, PostgreSQL, Oracle, DB2 | MySQL, PostgreSQL, Oracle |
| **Social Features** | Spaces, posts, comments, likes | Message boards, blogs, wikis | Activity streams, spaces, forums |
| **File Management** | Built-in file sharing | Document library with versioning | Documents with preview |
| **Calendar** | Built-in | Built-in | Built-in |
| **Mobile** | PWA (responsive) | Native mobile SDK | Mobile apps (iOS/Android) |
| **LDAP/SSO** | LDAP, OAuth2, SAML | LDAP, SAML, OAuth, OpenID | LDAP, SAML, OAuth2 |
| **Custom Modules** | Marketplace (100+ modules) | Extensive plugin ecosystem | Add-ons marketplace |
| **API** | REST API | REST, SOAP, GraphQL | REST API |
| **Docker Support** | Official (docker-compose) | Official | Community Docker |
| **Learning Curve** | Low (familiar social UX) | High (enterprise complexity) | Medium |

### HumHub

HumHub is a PHP-based social intranet platform built on the Yii2 framework. It is designed around the concept of "Spaces" — dedicated areas for teams, projects, or departments — each with its own stream of posts, files, tasks, and wikis.

The interface is immediately familiar to anyone who has used Facebook or LinkedIn: a content feed, user profiles, notifications, and the ability to follow/unfollow topics. This low learning curve is HumHub's greatest strength — employees adopt it naturally without training.

```yaml
# docker-compose.yml for HumHub
version: '3.8'
services:
  humhub:
    image: humhub/humhub:latest
    ports:
      - "8080:80"
    volumes:
      - humhub_config:/var/www/localhost/htdocs/protected/config
      - humhub_uploads:/var/www/localhost/htdocs/protected/uploads
      - humhub_modules:/var/www/localhost/htdocs/protected/modules
      - humhub_themes:/var/www/localhost/htdocs/protected/themes
    environment:
      HUMHUB_DB_HOST: db
      HUMHUB_DB_NAME: humhub
      HUMHUB_DB_USER: humhub
      HUMHUB_DB_PASSWORD: changeme
      HUMHUB_AUTO_INSTALL: "true"
      HUMHUB_ADMIN_EMAIL: admin@example.com
      HUMHUB_ADMIN_USERNAME: admin
      HUMHUB_ADMIN_PASSWORD: changeme

  db:
    image: mariadb:11
    volumes:
      - humhub_db:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: humhub
      MYSQL_USER: humhub
      MYSQL_PASSWORD: changeme

volumes:
  humhub_config:
  humhub_uploads:
  humhub_modules:
  humhub_themes:
  humhub_db:
```

HumHub's module marketplace is extensive, with over 100 free and paid modules including:
- **Tasks**: Kanban boards and to-do lists within spaces
- **Polls**: Create and manage surveys
- **Calendar**: Shared calendars with iCal import/export
- **Wiki**: Collaborative documentation pages
- **JWT SSO**: Single sign-on with JWT tokens
- **OnlyOffice/SOGo integration**: Document editing and email

HumHub is ideal for small-to-medium organizations (10-500 employees) that want a social, engaging intranet without enterprise complexity. It excels at company-wide announcements, team collaboration, and knowledge sharing through its space-based model.

### Liferay Portal

Liferay is a Java-based enterprise portal platform that has been in development since 2004. Unlike HumHub's social-first approach, Liferay is a full-featured digital experience platform (DXP) that can power intranets, customer portals, and public websites from a single installation.

Liferay's architecture is built around portlets (JSR-362 compliant widget components), content management, and user segmentation. Everything is modular: you can deploy a simple intranet or a complex multi-site portal with personalization rules and workflow automation.

```yaml
# docker-compose.yml for Liferay Portal
version: '3.8'
services:
  liferay:
    image: liferay/portal:7.4-ga112
    ports:
      - "8080:8080"
    volumes:
      - liferay_data:/opt/liferay/data
      - liferay_deploy:/opt/liferay/deploy
    environment:
      LIFERAY_JDBC_PERIOD_DEFAULT_PERIOD_DRIVER_UPPERCASEC_LASS_UPPERCASEN_AME: com.mysql.cj.jdbc.Driver
      LIFERAY_JDBC_PERIOD_DEFAULT_PERIOD_URL: jdbc:mysql://db/liferay?useSSL=false
      LIFERAY_JDBC_PERIOD_DEFAULT_PERIOD_USER_UPPERCASEN_AME: liferay
      LIFERAY_JDBC_PERIOD_DEFAULT_PERIOD_PASSWORD: changeme

  db:
    image: mysql:8.0
    volumes:
      - liferay_db:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: liferay
      MYSQL_USER: liferay
      MYSQL_PASSWORD: changeme

volumes:
  liferay_data:
  liferay_deploy:
  liferay_db:
```

Key Liferay capabilities for intranet use:
- **Content Management System**: Full WYSIWYG editing, versioning, workflows, and staging environments
- **Document Library**: Enterprise document management with check-in/check-out, version history, and WebDAV access
- **Message Boards**: Threaded discussions with categories, subscriptions, and moderation
- **Blogs and Wikis**: Built-in publishing tools
- **Forms**: Drag-and-drop form builder with workflow integration
- **Audience Targeting**: Display different content to different user segments based on roles, departments, or custom attributes
- **Search**: Elasticsearch-backed full-text search across all content types

Liferay is best suited for organizations with 500+ employees that need a comprehensive enterprise portal with content management, personalization, and workflow automation. The learning curve is significant — expect several weeks of setup and configuration for a production deployment.

### eXo Platform

eXo Platform is a Java-based digital workplace platform that combines social collaboration, content management, and knowledge management. It is positioned as a middle ground between HumHub's simplicity and Liferay's enterprise complexity.

eXo's key concept is the activity stream — a unified feed that aggregates content from spaces, documents, forums, and wikis. The platform emphasizes user engagement through gamification elements like badges, points, and leaderboards.

```yaml
# docker-compose.yml for eXo Platform Community
version: '3.8'
services:
  exo:
    image: exoplatform/exo-community:latest
    ports:
      - "8080:8080"
    volumes:
      - exo_data:/srv/exo
      - exo_logs:/var/log/exo
    environment:
      EXO_DB_HOST: db
      EXO_DB_PORT: 3306
      EXO_DB_NAME: exo
      EXO_DB_USER: exo
      EXO_DB_PASSWORD: changeme

  db:
    image: mysql:8.0
    volumes:
      - exo_db:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: exo
      MYSQL_USER: exo
      MYSQL_PASSWORD: changeme

volumes:
  exo_data:
  exo_logs:
  exo_db:
```

eXo Platform features include:
- **Spaces**: Team and project workspaces with forums, documents, wikis, and calendars
- **Social Networking**: Activity streams, user profiles, connections, and kudos
- **Content Management**: Web content authoring, document management, and digital asset management
- **Knowledge Base**: FAQ management and collaborative article authoring
- **Gamification**: Points, levels, badges, and leaderboards to drive engagement
- **Mobile**: Native iOS and Android apps with offline support

eXo Platform is a good fit for mid-size organizations (100-500 employees) that want social collaboration features with formal content management capabilities, especially if gamification and employee engagement are priorities.

## Deployment Architecture Considerations

When planning your intranet deployment, consider these architectural patterns:

**Single-server deployment**: For organizations under 200 employees, all three platforms run comfortably on a single VPS or dedicated server with 4 vCPUs, 8GB RAM, and SSD storage. Docker Compose simplifies the setup with bundled database and application containers.

**High-availability deployment**: For larger organizations, separate the database to a managed service or dedicated cluster. Use a load balancer (HAProxy or Nginx) in front of multiple application instances. Liferay supports clustering natively; HumHub and eXo require shared session storage (Redis) for multi-instance deployments.

**Hybrid deployment**: Run the application server on-premises for data sovereignty while using a CDN for static assets. All three platforms can be placed behind a reverse proxy with TLS termination — see our guide on [self-hosted reverse proxies](../self-hosted-cdn-edge-caching-varnish-traffic-server-squid-nginx-guide/).

## FAQ

### How do I migrate from SharePoint or Google Workspace?

All three platforms provide import tools and APIs for content migration. HumHub offers CSV-based user and space imports. Liferay has bulk import capabilities for documents and user data. eXo Platform supports standards-based migration via CMIS and WebDAV. Plan for a phased migration: start with user accounts and basic content, then gradually move workflows and complex documents.

### Can these intranets connect to our existing Active Directory or LDAP?

Yes. All three support LDAP/Active Directory integration for user authentication and group synchronization. Liferay offers the most comprehensive identity integration with support for SAML 2.0, OAuth 2.0, OpenID Connect, and custom identity providers. HumHub and eXo support LDAP and OAuth-based SSO.

### What about compliance and audit requirements?

For regulated industries, Liferay offers the most robust compliance features: full audit logging, content retention policies, and granular permission models down to individual portlet instances. HumHub's permission model is simpler (space-level and global roles) but sufficient for most SMB needs. eXo includes basic audit trails for content modifications and user actions.

### How do I ensure employee adoption?

The biggest challenge with any intranet is getting employees to use it. Strategy recommendations: (1) Start with a pilot group of 20-30 enthusiastic users before company-wide rollout. (2) Make the intranet the single source of truth for one critical workflow (e.g., company announcements, HR forms) to create a usage habit. (3) Appoint "space champions" in each department who maintain content freshness. (4) Use HumHub's social design or eXo's gamification to make participation rewarding rather than mandatory.

### What hardware do I need for 500 users?

For 500 concurrent users, a server with 8 vCPUs, 16GB RAM, and SSD storage is recommended for all three platforms. Liferay benefits from additional memory for the JVM (allocate 8-10GB). Database performance is the bottleneck for most intranet deployments — use a dedicated database server or a managed database service for optimal performance.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform, where you can bet on anything from election outcomes to tech regulation timelines. Unlike gambling, this is a genuine information market: the more you know, the better your odds. I have profited by predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Employee Intranet Platforms: HumHub vs Liferay vs eXo Platform",
  "description": "Compare HumHub, Liferay Portal, and eXo Platform — three self-hosted employee intranet solutions with Docker Compose deployment guides. Covers social collaboration, content management, enterprise features, and adoption strategies.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
