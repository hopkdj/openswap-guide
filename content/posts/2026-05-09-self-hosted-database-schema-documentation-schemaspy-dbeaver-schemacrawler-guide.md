---
title: "Self-Hosted Database Schema Documentation 2026: SchemaSpy vs DBeaver ERD vs SchemaCrawler"
date: "2026-05-09"
tags: ["database", "schema", "documentation", "schemaspy", "dbeaver", "diagram", "docker"]
draft: false
---

Database schema documentation is critical for team collaboration, onboarding, and maintaining data governance. When databases grow to hundreds of tables with complex relationships, having up-to-date, auto-generated documentation becomes essential. This guide compares three open-source tools for self-hosted database schema documentation: **SchemaSpy**, **DBeaver ER Diagrams**, and **SchemaCrawler**.

## Why Database Schema Documentation Matters

As teams grow and databases evolve, understanding table relationships, column types, constraints, and indexes becomes increasingly difficult. Auto-generated schema documentation provides a single source of truth that stays synchronized with the actual database structure, reducing onboarding time for new developers and preventing costly schema misunderstandings.

Without proper documentation, developers waste time reverse-engineering database structures through trial and error. New team members spend their first weeks asking questions like "What does this column mean?" and "Why does this table exist?" Auto-generated schema docs answer these questions instantly and stay accurate because they reflect the live database, not someone's outdated wiki page.

## Common Schema Documentation Patterns

There are several patterns for maintaining database schema documentation in self-hosted environments:

**Automated HTML portals:** Tools like SchemaSpy generate a complete browsable website with table listings, relationship diagrams, and column details. Teams bookmark the portal and use it as a daily reference. This is the most common pattern for organizations with 10+ databases.

**Interactive desktop diagrams:** DBeaver and similar tools provide real-time ER diagrams within a database management IDE. Developers generate diagrams on-demand during query development or schema design. This pattern suits individual contributors who need quick visual understanding.

**Machine-readable metadata exports:** SchemaCrawler and similar tools export schema information as JSON, YAML, or XML. These outputs feed into downstream tools — data catalogs, governance dashboards, or custom documentation systems. This pattern is ideal for organizations with established data governance pipelines.

**CI/CD-integrated documentation:** Schema documentation tools run as pipeline steps, regenerating docs after every migration. The output is published to an internal website, ensuring documentation is always current. This pattern eliminates documentation drift entirely.

## SchemaSpy

**SchemaSpy** is a Java-based tool that analyzes database metadata and generates a visual, browsable HTML documentation site. It has been one of the most popular open-source schema documentation tools for over a decade.

**Key Features:**
- Auto-generated HTML documentation with interactive diagrams
- Entity-relationship diagrams (ERD) using Graphviz
- Table-level and column-level documentation with constraints and indexes
- Anomaly detection (tables without indexes, orphan tables, etc.)
- Support for MySQL, PostgreSQL, Oracle, SQL Server, SQLite, and more
- Customizable templates and themes
- Command-line driven for CI/CD integration

**GitHub:** [schemaspy/schemaspy](https://github.com/schemaspy/schemaspy) — 3,500+ stars

**Deployment:** Java JAR or Docker container. Connects directly to your database via JDBC drivers.

## DBeaver ER Diagrams

**DBeaver** is primarily a universal database management tool, but its built-in ER Diagram feature provides interactive schema visualization. While not a dedicated documentation generator, DBeaver's ER diagrams are excellent for exploratory database analysis and quick relationship mapping.

**Key Features:**
- Interactive ER diagrams with drag-and-drop layout
- Real-time schema browsing alongside visual diagrams
- Support for 80+ database systems
- Inline column details, foreign key relationships, and indexes
- Export diagrams to PNG, SVG, or PDF
- Part of a full-featured database IDE (query editor, data editor, etc.)
- Community Edition is free and open-source

**GitHub:** [dbeaver/dbeaver](https://github.com/dbeaver/dbeaver) — 50,000+ stars, very active

**Deployment:** Desktop application (Windows, macOS, Linux). Server deployment via DBeaver Cloud (paid) or by running the desktop app on a jump host.

## SchemaCrawler

**SchemaCrawler** is a comprehensive database schema discovery and comprehension tool. It goes beyond visual diagrams to provide detailed metadata reports, comparison capabilities, and scripting support.

**Key Features:**
- Schema discovery across 18+ database systems
- Multiple output formats: text, HTML, JSON, YAML, XML, and PNG diagrams
- Schema comparison (diff) between database versions
- Groovy scripting for custom reports and analysis
- Detailed metadata: tables, columns, indexes, constraints, routines, triggers
- Command-line tool designed for automation and CI/CD
- Database documentation linting (identifies missing comments, undocumented columns)

**GitHub:** [schemacrawler/schemacrawler](https://github.com/schemacrawler/schemacrawler) — 1,800+ stars, actively maintained

**Deployment:** Command-line tool or Docker container. Designed for headless/automated use.

## Comparison Table

| Feature | SchemaSpy | DBeaver ERD | SchemaCrawler |
|---------|-----------|-------------|---------------|
| License | LGPL 3.0 | Apache 2.0 | EPL 1.0 |
| Primary Output | Interactive HTML | Interactive desktop diagrams | Text/HTML/JSON/XML |
| Database Support | JDBC-compatible (15+) | 80+ databases | 18+ databases |
| ER Diagrams | Yes (Graphviz) | Yes (built-in) | Yes (PlantUML/PNG) |
| Schema Diff | No | Manual comparison | Yes (built-in) |
| CI/CD Friendly | Yes (CLI) | No (desktop) | Yes (CLI) |
| Custom Reports | Templates only | No | Groovy scripting |
| Anomaly Detection | Yes | No | Yes (linting) |
| Docker Support | Yes | No | Yes |
| Metadata Export | HTML | PNG/PDF/SVG | HTML, JSON, YAML, XML |
| Learning Curve | Low | Low | Medium |
| Best For | Team documentation portals | Individual exploration | Automated schema audits |

## Docker Compose Deployment

### SchemaSpy

```yaml
version: "3.8"
services:
  schemaspy:
    image: schemaspy/schemaspy:latest
    container_name: schemaspy
    volumes:
      - ./output:/output
      - ./drivers:/drivers
    command: >
      -t pgsql
      -host db.internal
      -port 5432
      -db myapp
      -u app_user
      -p mypassword
      -s public
      -o /output
      -connprops useSSL\=false
    restart: "no"
```

### SchemaCrawler

```yaml
version: "3.8"
services:
  schemacrawler:
    image: schemacrawler/schemacrawler:latest
    container_name: schemacrawler
    volumes:
      - ./output:/output
    environment:
      - SC_CMDLINE=-server=postgresql://db.internal:5432/myapp -user=app_user -password=mypassword -info-level=maximum -command=schema -output-format=html -output-file=/output/schema.html
    restart: "no"
```

### DBeaver (Desktop Installation)

DBeaver runs as a desktop application. For team access, deploy it on a shared jump host or use DBeaver Cloud:

```bash
# Linux installation
sudo snap install dbeaver-ce

# Or download from https://dbeaver.io/download/
# Generate ER diagram: Open connection -> Diagrams tab -> Select tables
```

## Which Schema Documentation Tool Should You Choose?

**Choose SchemaSpy if:** You need a team-accessible, browsable HTML documentation site with relationship diagrams. It is ideal for generating a permanent documentation portal that developers can bookmark and reference daily.

**Choose DBeaver ER Diagrams if:** You want interactive, real-time schema exploration as part of your daily database management workflow. It is best for individual developers and DBAs who need quick visual understanding of database structure.

**Choose SchemaCrawler if:** You need automated schema auditing, diff capabilities between environments, and programmatic access to schema metadata. It is the best choice for CI/CD pipelines, compliance audits, and schema governance.

## Why Self-Host Your Schema Documentation?

**Data security:** Schema documentation reveals your database structure, table names, column types, and relationships. This is sensitive information that should not be sent to third-party documentation services. Self-hosting keeps your schema metadata within your controlled environment.

**Always up to date:** Self-hosted documentation tools can be integrated into your CI/CD pipeline to regenerate documentation on every schema migration. This ensures your docs never drift from the actual database structure — a common problem with manually maintained documentation.

**No cost per database:** Commercial schema documentation tools often charge per-database or per-developer seat. Open-source self-hosted alternatives have no such limits, making them practical for organizations with dozens of databases and hundreds of developers.

**Customization:** Self-hosted tools can be extended with custom templates, report formats, and automation scripts. You control exactly what information is documented and how it is presented to your team.

For database migration management, see our [Bytebase vs Flyway vs Liquibase guide](../bytebase-vs-flyway-vs-liquibase-self-hosted-database-migration-guide-2026/). For web-based SQL query tools, check our [SQLPad vs CloudBeaver vs Adminer comparison](../2026-04-27-sqlpad-vs-cloudbeaver-vs-adminer-self-hosted-web-sql-query-editor-guide-2026/).

## FAQ

### What is the difference between SchemaSpy and SchemaCrawler?

SchemaSpy focuses on generating an interactive HTML documentation website with visual ER diagrams, making it ideal for team reference. SchemaCrawler is a command-line tool that provides multiple output formats (text, JSON, YAML, XML) and includes schema comparison and linting capabilities, making it better for automation and audits.

### Can SchemaSpy generate documentation for NoSQL databases?

SchemaSpy primarily supports relational databases via JDBC drivers (MySQL, PostgreSQL, Oracle, SQL Server, SQLite, MariaDB, etc.). For NoSQL databases like MongoDB or Cassandra, SchemaCrawler offers limited support, while DBeaver can browse schemas visually for many NoSQL systems.

### How do I integrate schema documentation into my CI/CD pipeline?

Both SchemaSpy and SchemaCrawler are command-line tools that can be run as pipeline steps. Configure them to connect to your staging database, generate documentation, and publish the output as build artifacts. Run this step after every migration to keep docs synchronized.

### Does DBeaver support automatic schema documentation generation?

DBeaver's ER diagrams are interactive and generated on-demand within the desktop application. While you can export diagrams to image files, DBeaver does not have a batch/documentation-generation mode like SchemaSpy or SchemaCrawler. For automated documentation, use one of the CLI-based tools.

### How often should I regenerate schema documentation?

Ideally, regenerate documentation after every schema migration. When integrated into CI/CD, this happens automatically. For teams without automated pipelines, weekly or bi-weekly regeneration is a reasonable minimum to prevent documentation drift.

### Can these tools document stored procedures and functions?

SchemaCrawler has the most comprehensive support for database programmability objects, including stored procedures, functions, triggers, and views. SchemaSpy includes some support for routines depending on the database driver. DBeaver displays these objects in its database navigator but does not generate detailed documentation for them.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Schema Documentation 2026: SchemaSpy vs DBeaver ERD vs SchemaCrawler",
  "description": "Compare three open-source tools for self-hosted database schema documentation: SchemaSpy, DBeaver ER Diagrams, and SchemaCrawler. Includes Docker setup.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
