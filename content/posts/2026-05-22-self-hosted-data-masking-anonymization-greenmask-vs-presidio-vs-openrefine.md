---
title: "Self-Hosted Data Masking and Anonymization: Greenmask vs Microsoft Presidio vs OpenRefine"
date: "2026-05-22"
tags: ["data-privacy", "security", "anonymization", "compliance", "database"]
draft: false
---

Production databases contain sensitive information — personally identifiable information (PII), payment details, health records, and proprietary business data. When you need to share data with development teams, testing environments, or third-party analytics, exposing raw production data creates compliance risks and potential breach liability. This guide compares three self-hosted data masking and anonymization tools — **Greenmask**, **Microsoft Presidio**, and **OpenRefine** — to help you sanitize data before it leaves your production environment.

## Why Self-Host Data Anonymization Tools?

Data privacy regulations including GDPR, HIPAA, CCPA, and PCI DSS impose strict requirements on how personal data is handled, stored, and shared. Copying production data to staging or development environments without anonymization is one of the most common compliance violations found in security audits. Anonymization tools transform sensitive fields into realistic but fictitious values, preserving data structure and statistical properties while removing identifiable information.

Self-hosting these tools keeps your data processing pipeline entirely within your infrastructure boundary. Cloud-based anonymization services require uploading your production data to external servers for processing — a data transfer that may itself violate compliance requirements or internal security policies. A self-hosted tool processes data locally, ensuring sensitive values never traverse public networks.

The operational benefit extends to reproducibility. Self-hosted anonymization pipelines can be version-controlled, tested, and integrated into your existing CI/CD workflows. You can define masking rules as code, run them against database dumps as part of your deployment pipeline, and verify that the output meets your anonymization standards before any data reaches non-production environments.

For organizations managing multiple database systems, having a dedicated anonymization layer provides a consistent approach across PostgreSQL, MySQL, MongoDB, and other data stores. Instead of writing custom scripts for each database type, a purpose-built tool handles the complexity of maintaining referential integrity, preserving data distributions, and generating realistic test data.

If you manage database infrastructure broadly, see our [database monitoring guide](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) and [supply chain security practices](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/) for complementary security practices.

## Greenmask

**GitHub:** [Greenmaskio/greenmask](https://github.com/Greenmaskio/greenmask) | **Stars:** 1,676 | **Last Updated:** May 2026

Greenmask is an open-source PostgreSQL data anonymization and backup tool designed specifically for database teams. It combines logical backup capabilities with comprehensive data masking transformations, making it suitable for both disaster recovery and test data generation workflows.

### Key Features

- **PostgreSQL-native** — Designed specifically for PostgreSQL with deep understanding of data types and constraints
- **Logical backup with masking** — Create anonymized database dumps in a single operation
- **Transformation library** — 30+ built-in transformers including randomization, hashing, masking, and format-preserving encryption
- **Referential integrity** — Maintains foreign key relationships across anonymized tables
- **Deterministic masking** — Same input always produces same output, enabling cross-environment data correlation
- **Incremental backups** — Support for incremental backup strategies alongside masking
- **YAML configuration** — Define masking rules in declarative configuration files
- **Dump and restore** — Standard PostgreSQL-compatible dump format that works with pg_restore

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: your-password
      POSTGRES_DB: production_db
    volumes:
      - pg-data:/var/lib/postgresql/data
    networks:
      - pg-net

  greenmask:
    image: greenmask/greenmask:latest
    container_name: greenmask
    restart: "no"
    volumes:
      - ./greenmask-config.yaml:/etc/greenmask/config.yaml
      - ./backups:/backups
    environment:
      - GREENMASK_CONFIG=/etc/greenmask/config.yaml
    command: greenmask dump --config /etc/greenmask/config.yaml
    depends_on:
      - postgres
    networks:
      - pg-net

volumes:
  pg-data:

networks:
  pg-net:
    driver: bridge
```

Example masking configuration (`greenmask-config.yaml`):

```yaml
storage:
  type: directory
  path: /backups

dump:
  pg_dump_options:
    host: postgres
    port: 5432
    user: postgres
    password: your-password
    database: production_db

transformations:
  - schema: public
    name: users
    columns:
      - name: email
        transformer: random_email
        params:
          domain: example.com
      - name: phone
        transformer: random_phone
        params:
          country: US
      - name: ssn
        transformer: random_string
        params:
          length: 11
          format: "XXX-XX-XXXX"
      - name: credit_card
        transformer: mask
        params:
          mask_char: "X"
          keep_first: 4
          keep_last: 4
```

### Limitations

Greenmask is PostgreSQL-only — it does not support MySQL, MongoDB, or other database systems. The project is relatively young, and the transformer library, while growing, does not yet cover every data type you might encounter. The documentation is thorough but assumes familiarity with PostgreSQL internals.

## Microsoft Presidio

**GitHub:** [microsoft/presidio](https://github.com/microsoft/presidio) | **Stars:** 7,988 | **Last Updated:** May 2026

Presidio is a data anonymization SDK and service from Microsoft Research, designed to detect and anonymize PII in both structured and unstructured text. Unlike Greenmask, which operates at the database level, Presidio works on text streams — making it suitable for log sanitization, document processing, and API response anonymization.

### Key Features

- **PII detection** — Identifies 50+ PII entity types including names, emails, phone numbers, SSNs, credit cards, and addresses
- **Contextual analysis** — Uses NLP models to improve detection accuracy by considering surrounding text
- **Custom recognizers** — Define pattern-based recognizers for organization-specific PII types
- **Multiple anonymization strategies** — Replace, mask, hash, encrypt, or redact detected entities
- **Structured and unstructured** — Works with free text, JSON, CSV, and database columns
- **REST API service** — Deploy as a microservice for on-demand text anonymization
- **Python SDK** — Integrate directly into Python data processing pipelines
- **Extensible architecture** — Add custom entity recognizers and anonymization operators

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  presidio-analyzer:
    image: mcr.microsoft.com/presidio-analyzer:latest
    container_name: presidio-analyzer
    restart: unless-stopped
    ports:
      - "5002:3000"
    environment:
      - LOG_LEVEL=INFO
    networks:
      - presidio-net

  presidio-anonymizer:
    image: mcr.microsoft.com/presidio-anonymizer:latest
    container_name: presidio-anonymizer
    restart: unless-stopped
    ports:
      - "5001:3000"
    networks:
      - presidio-net

networks:
  presidio-net:
    driver: bridge
```

Example API usage:

```bash
# Detect PII in text
curl -X POST http://localhost:5002/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "My name is John Smith and my email is john@example.com", "language": "en"}'

# Anonymize detected PII
curl -X POST http://localhost:5001/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My name is John Smith and my email is john@example.com",
    "anonymizers": {
      "PERSON": {"type": "replace", "new_value": "<REDACTED>"},
      "EMAIL_ADDRESS": {"type": "mask", "masking_char": "*", "chars_to_mask": 4, "from_end": false}
    }
  }'
```

### Limitations

Presidio is designed for text processing, not database-level anonymization. It does not understand database schemas, foreign key relationships, or data types. You must build the integration layer yourself to apply Presidio to database exports. The NLP-based detection, while accurate, adds processing overhead compared to pattern-based approaches.

## OpenRefine

**GitHub:** [OpenRefine/OpenRefine](https://github.com/OpenRefine/OpenRefine) | **Stars:** 11,821 | **Last Updated:** May 2026

OpenRefine (formerly Google Refine) is a powerful desktop-grade data transformation tool that runs as a local web application. While not purpose-built for anonymization, its robust data manipulation capabilities — clustering, transformation, faceting, and reconciliation — make it a flexible option for manual and semi-automated data masking workflows.

### Key Features

- **Data exploration** — Faceted browsing to quickly identify PII columns and value distributions
- **Clustering** — Find and merge similar values (e.g., "Jon Smith", "J. Smith", "Jonathan Smith")
- **GREL expressions** — Powerful transformation language for custom masking logic
- **Reconciliation** — Match values against external datasets for validation
- **Undo/redo history** — Full operation history that can be saved and replayed on new datasets
- **Multiple formats** — Import/export CSV, TSV, Excel, JSON, XML, and RDF
- **Extension system** — Add functionality through community extensions
- **Batch processing** — Apply saved operation histories to multiple files

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  openrefine:
    image: openrefine/openrefine:latest
    container_name: openrefine
    restart: unless-stopped
    ports:
      - "3333:3333"
    volumes:
      - ./data:/data
    environment:
      - JAVA_OPTS=-Xmx4g
    networks:
      - refine-net

networks:
  refine-net:
    driver: bridge
```

### Limitations

OpenRefine is fundamentally an interactive tool, not an automated pipeline. It requires manual operation — you load data, apply transformations through the web UI, and export the result. It cannot be scripted as part of a CI/CD pipeline without significant custom automation. The memory usage scales with dataset size — large exports may require substantial JVM heap allocation.

## Feature Comparison

| Feature | Greenmask | Presidio | OpenRefine |
|---------|-----------|----------|------------|
| **GitHub Stars** | 1,676 | 7,988 | 11,821 |
| **Last Updated** | May 2026 | May 2026 | May 2026 |
| **Primary Use** | Database anonymization | Text PII detection | Data transformation |
| **Database Support** | PostgreSQL | None (text only) | None (file import) |
| **Automated Pipeline** | Yes | Yes (API) | No (manual) |
| **PII Detection** | No (rule-based) | Yes (NLP + regex) | No (manual) |
| **Referential Integrity** | Yes | N/A | N/A |
| **Deterministic Output** | Yes | Yes | Yes |
| **REST API** | No | Yes | No |
| **Docker Deployment** | Yes | Yes | Yes |
| **CI/CD Integration** | Yes | Yes | Limited |
| **Free/Open Source** | Yes (Apache 2.0) | Yes (MIT) | Yes (BSD-3) |

## Choosing the Right Data Anonymization Tool

**Choose Greenmask** if you need PostgreSQL database anonymization with referential integrity. It is the only tool in this comparison that understands database schemas and can produce anonymized dumps that maintain foreign key relationships. The YAML configuration approach makes it suitable for automated CI/CD pipelines.

**Choose Microsoft Presidio** if you need to detect and anonymize PII in free text, logs, or API responses. Its NLP-powered detection catches PII that pattern-based tools miss — names embedded in unstructured text, addresses in customer notes, and mixed-format identifiers. The REST API makes it easy to integrate into existing data processing workflows.

**Choose OpenRefine** if you need flexible, interactive data transformation for one-off or ad-hoc anonymization tasks. Its faceting and clustering features are unmatched for exploratory data analysis before defining permanent masking rules. However, it is not suitable for automated, repeatable anonymization pipelines.

For a comprehensive data governance strategy, combine these tools — use Greenmask for database sanitization, Presidio for text log scrubbing, and OpenRefine for ad-hoc data exploration and transformation.

## FAQ

### Can Greenmask anonymize MySQL or MongoDB databases?

No, Greenmask is designed exclusively for PostgreSQL. For MySQL, consider writing custom transformation scripts or using Percona's data masking tools. For MongoDB, export collections as JSON and process them with Presidio or OpenRefine before re-importing.

### How accurate is Presidio's PII detection?

Presidio's built-in recognizers achieve 85-95% accuracy on standard PII types (emails, phone numbers, SSNs, credit cards) in English text. Accuracy drops for non-English text and custom identifier formats. You can improve results by training custom NER models or adding organization-specific pattern recognizers.

### Is OpenRefine suitable for GDPR-compliant data anonymization?

OpenRefine can produce properly anonymized data, but the manual workflow makes it difficult to prove consistent anonymization across multiple exports. For GDPR compliance documentation, you need reproducible, auditable processes — Greenmask's YAML configuration or Presidio's API approach provide better auditability.

### Can I run these tools against production databases directly?

Greenmask connects to production PostgreSQL to create anonymized backups — this is its intended use case. Presidio and OpenRefine work on exported data copies, not live databases. Never run destructive transformations directly against production data.

### How do I verify that anonymization was successful?

Implement automated checks that scan the anonymized output for known PII patterns. For database dumps, query for original email domains, phone number patterns, or known test values. For text, run Presidio's analyzer against the anonymized output to confirm no entities remain undetected.

### Does Greenmask preserve data statistics after anonymization?

Greenmask offers transformers that preserve statistical properties — date ranges, numeric distributions, and categorical value frequencies. Use the `random_date` transformer with min/max bounds, `random_number` with distribution parameters, and `random_choice` for categorical columns to maintain statistical fidelity.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Data Masking and Anonymization: Greenmask vs Microsoft Presidio vs OpenRefine",
  "description": "Compare three self-hosted data anonymization tools — Greenmask for PostgreSQL, Microsoft Presidio for text PII detection, and OpenRefine for interactive data transformation — with Docker configs.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
