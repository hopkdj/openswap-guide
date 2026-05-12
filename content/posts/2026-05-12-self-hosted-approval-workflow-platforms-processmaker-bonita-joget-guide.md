---
title: "Self-Hosted Approval Workflow Platforms: ProcessMaker vs Bonita vs Joget"
date: "2026-05-12"
tags: ["workflow", "bpm", "approval", "business-process", "self-hosted", "automation"]
draft: false
---

Approval workflows are the backbone of organizational processes — from purchase order approvals and employee onboarding to compliance sign-offs and change management. While cloud-based solutions like ServiceNow and Approve.com dominate the market, several mature open-source platforms let you self-host approval workflows with full data control and no per-user licensing fees.

This guide compares three leading self-hosted approval workflow platforms: **ProcessMaker**, **Bonita**, and **Joget**. Each offers visual process designers, user management, and approval routing — but they differ significantly in architecture, extensibility, and deployment complexity.

## Why Self-Host Approval Workflows?

Approval workflows often handle sensitive organizational data: financial requests, HR decisions, compliance documentation, and proprietary processes. Self-hosting these platforms gives you complete control over data sovereignty, eliminates per-user subscription costs, and allows deep customization that cloud SaaS platforms restrict.

For organizations with strict compliance requirements (SOC 2, HIPAA, GDPR), self-hosted workflow platforms avoid the data residency concerns of cloud BPM services. You control the database, the file storage, and the audit logs — critical factors for regulated industries.

For broader workflow orchestration options, see our [workflow orchestration comparison](../2026-04-24-dagu-vs-netflix-conductor-vs-airflow-self-hosted-workflow-orchestration-guide-2026/) and [BPMN engines guide](../2026-04-30-flowable-vs-activiti-vs-camunda-self-hosted-bpmn-engines-guide/).

## Comparison Overview

| Feature | ProcessMaker | Bonita | Joget |
|---------|-------------|--------|-------|
| **License** | GPL-3.0 (Community) | LGPL-2.1 (Community) | GPL-3.0 (Community) |
| **GitHub Stars** | 534 | 175 | 607 |
| **Process Engine** | BPMN 2.0 | BPMN 2.0 | Proprietary + BPMN |
| **Form Builder** | Drag-and-drop | Drag-and-drop | Drag-and-drop |
| **UI Framework** | Vue.js | Angular | Custom |
| **Database Support** | MySQL, PostgreSQL | PostgreSQL, MySQL, Oracle | MySQL, PostgreSQL, Oracle |
| **API** | REST | REST, Java API | REST, Plugin API |
| **Docker Support** | Official images | Official images | Docker available |
| **Plugin System** | Limited | Extensive (Java) | Extensive (OSGi) |
| **Multi-tenancy** | Yes (Enterprise) | Yes | Yes |
| **Best For** | Enterprise process automation | Developer-centric workflows | Low-code application building |

## ProcessMaker

ProcessMaker is a mature business process management platform with a strong focus on visual process design and approval routing. The Community edition provides core BPMN modeling, form building, and task management features.

### Key Features

- **BPMN 2.0 visual designer**: Drag-and-drop process modeling with approval gates, conditional routing, and parallel branches
- **Dynform builder**: Create complex approval forms with conditional fields, validators, and calculated values
- **Case management**: Track approval instances from initiation to completion with full audit trails
- **REST API**: Integrate with external systems for automated approval triggering and status queries
- **Role-based access control**: Define who can initiate, approve, or view each process step

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  processmaker:
    image: processmaker/processmaker:4
    container_name: processmaker
    ports:
      - "8080:80"
      - "8443:443"
    environment:
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_DATABASE=processmaker
      - DB_USERNAME=pm_user
      - DB_PASSWORD=pm_secret
      - ADMIN_USER=admin
      - ADMIN_PASSWORD=admin123
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - pm-storage:/var/processmaker/storage
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: processmaker-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=processmaker
      - MYSQL_USER=pm_user
      - MYSQL_PASSWORD=pm_secret
    volumes:
      - pm-mysql:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pm-storage:
  pm-mysql:
```

### Creating an Approval Process

ProcessMaker uses a visual BPMN designer to model approval flows. A typical purchase order approval process follows this pattern:

1. **Start Event**: Employee submits purchase request form
2. **User Task**: Manager review with approve/reject decision
3. **Exclusive Gateway**: Route based on decision
   - If approved and amount > $10,000: route to Finance Director
   - If approved and amount <= $10,000: proceed to procurement
   - If rejected: notify requestor and end
4. **End Event**: Process complete with notification

## Bonita

Bonita (formerly Bonita BPM) is a developer-friendly process automation platform built on the BPMN 2.0 standard. It emphasizes clean separation between process modeling (business users) and technical implementation (developers).

### Key Features

- **Bonita Studio**: Eclipse-based IDE for process modeling, form design, and connector configuration
- **Actor filters**: Dynamic user assignment based on organizational hierarchy, roles, or data conditions
- **Business Data Model (BDM)**: Define custom data structures tied to process variables
- **Connectors**: Pre-built integrations for REST, SOAP, email, database, and more
- **REST API**: Full API coverage for process management, task assignment, and reporting
- **Migration tools**: Export/import processes between environments

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  bonita:
    image: bonitasoft/bonita:2023.2
    container_name: bonita
    ports:
      - "8080:8080"
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=bonita
      - DB_USER=bonita
      - DB_PASS=bonita_secret
      - BIZ_DB_NAME=bonita_bdm
      - BIZ_DB_USER=bonita
      - BIZ_DB_PASS=bonita_secret
      - PLATFORM_LOGIN=platformAdmin
      - PLATFORM_PASSWORD=platform_secret
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - bonita-data:/opt/bonita
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: bonita-db
    environment:
      - POSTGRES_USER=bonita
      - POSTGRES_PASSWORD=bonita_secret
      - POSTGRES_DB=bonita
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bonita"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  bonita-data:
  postgres-data:
```

### Building an Approval Flow in Bonita

Bonita's approach separates the process model from the implementation:

1. **Design the BPMN diagram** in Bonita Studio with approval tasks and gateways
2. **Define the Business Data Model** for approval request data
3. **Create UI forms** using the built-in form designer or custom HTML/Angular forms
4. **Configure actor filters** to assign tasks dynamically (e.g., "assign to the requester's department manager")
5. **Add connectors** for email notifications, database updates, and external API calls
6. **Deploy** to the Bonita runtime for execution

## Joget

Joget is an open-source no-code/low-code platform that combines workflow management with application building. It is particularly strong for organizations that want approval workflows embedded within custom applications.

### Key Features

- **App Designer**: Visual builder for forms, lists, and workflows without coding
- **Workflow Designer**: BPMN-based process modeling with approval routing
- **Plugin marketplace**: 200+ plugins for integrations, UI components, and data connectors
- **Multi-app support**: Deploy multiple workflow applications on a single instance
- **Userview**: Custom user-facing dashboards for tracking and managing approvals
- **Mobile-ready**: Responsive forms and approval interfaces

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  joget:
    image: jogetworkflow/jw-community:8.0
    container_name: joget
    ports:
      - "8080:8080"
    environment:
      - DATABASE_DRIVER=com.mysql.cj.jdbc.Driver
      - DATABASE_URL=jdbc:mysql://mysql:3306/jwdb?characterEncoding=UTF-8
      - DATABASE_USER=joget
      - DATABASE_PASSWORD=joget_secret
      - JOGET_ADMIN_PASSWORD=admin123
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - joget-data:/opt/joget/wflow
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: joget-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=jwdb
      - MYSQL_USER=joget
      - MYSQL_PASSWORD=joget_secret
    volumes:
      - joget-mysql:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  joget-data:
  joget-mysql:
```

### Approval Workflow Architecture

Joget's workflow engine supports:

- **Sequential approval**: Multi-level approval chains (submitter → manager → director → finance)
- **Parallel approval**: Multiple approvers who can approve independently
- **Conditional routing**: Dynamic paths based on form data (amount, department, urgency)
- **Delegation**: Approvers can delegate tasks to substitutes during absence
- **SLA tracking**: Monitor approval times and escalate overdue tasks

## Deployment Architecture Comparison

All three platforms follow a similar architecture:

| Component | ProcessMaker | Bonita | Joget |
|-----------|-------------|--------|-------|
| **Web Server** | Nginx/Apache (included) | Tomcat (included) | Tomcat (included) |
| **Runtime** | PHP/Laravel | Java/Tomcat | Java/Tomcat |
| **Database** | MySQL 8.0+ | PostgreSQL 14+ | MySQL 8.0+ |
| **Search** | Elasticsearch (optional) | Elasticsearch (optional) | Lucene (built-in) |
| **Min. RAM** | 4 GB | 4 GB | 2 GB |
| **Recommended RAM** | 8 GB | 8 GB | 4 GB |

For IT service management workflows, also see our [incident management guide](../self-hosted-incident-management-oncall-alerta-openduty-2026/) and [project management tools comparison](../plane-vs-huly-vs-taiga-self-hosted-project-management-guide-2026/).

## FAQ

### What is the difference between approval workflow platforms and workflow orchestration tools?

Approval workflow platforms (ProcessMaker, Bonita, Joget) focus on human-centric processes where people review, approve, or reject requests. Workflow orchestration tools (Airflow, Dagster, Conductor) focus on automated, machine-driven pipelines for data processing and service coordination. Use approval platforms for business processes; use orchestration for technical workflows.

### Can these platforms integrate with existing identity providers?

All three support LDAP/Active Directory integration in their enterprise editions. ProcessMaker and Bonita offer SAML and OAuth 2.0 connectors. Joget provides plugin-based authentication that supports SAML, LDAP, and OAuth through its plugin marketplace. The Community editions typically support local user management and basic LDAP.

### How do I migrate approval workflows between environments?

ProcessMaker uses process export/import packages (.pmx files). Bonita has organization and process export/import with the Studio IDE. Joget exports applications as .jwb files that can be imported into any Joget instance. All three support versioning so you can track changes across deployments.

### Which platform is best for non-technical users?

Joget is the most accessible for non-technical users thanks to its no-code app designer and visual workflow builder. ProcessMaker's Dynform builder is also very user-friendly. Bonita's Eclipse-based Studio requires more technical knowledge and is better suited for developer teams building custom process applications.

### Do these platforms support mobile approval?

All three platforms have responsive web interfaces that work on mobile browsers. Joget and ProcessMaker offer dedicated mobile-friendly views for approval tasks. Bonita's custom forms can be designed with mobile responsiveness. For native mobile apps, all three provide REST APIs that can be consumed by custom mobile applications.

### What is the licensing model for the Community editions?

ProcessMaker Community (GPL-3.0) includes core BPMN modeling, form building, and case management but lacks enterprise features like SSO, multi-tenancy, and advanced reporting. Bonita Community (LGPL-2.1) includes the full Studio IDE and runtime but excludes enterprise connectors and monitoring. Joget Community (GPL-3.0) includes the full app and workflow designers but limits some enterprise plugins.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Approval Workflow Platforms: ProcessMaker vs Bonita vs Joget",
  "description": "Compare open-source approval workflow platforms: ProcessMaker, Bonita, and Joget for self-hosted business process automation.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
