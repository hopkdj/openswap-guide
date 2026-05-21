---
title: "Self-Hosted Full-Text Search for Email: Solr vs Elasticsearch vs FlatCurve"
date: "2026-05-21"
tags: ["email", "search", "dovecot", "solr", "elasticsearch", "full-text-search"]
draft: false
---

When running a self-hosted email server, one of the most common user complaints is slow or inaccurate message search. Dovecot, the most widely deployed open-source IMAP/POP3 server, supports full-text search (FTS) through a pluggable backend architecture. This means you can choose from multiple search engines to power email indexing and retrieval. In this guide, we compare three popular Dovecot FTS backends: **Apache Solr**, **Elasticsearch**, and **FlatCurve** — evaluating their performance, resource requirements, and ease of deployment.

## Dovecot FTS Architecture Overview

Dovecot's FTS system works by intercepting IMAP SEARCH commands and delegating them to an external indexer. When a new email arrives, Dovecot's indexer-worker extracts the message body, headers, and attachments, then passes the text to the configured FTS backend for tokenization and indexing.

The FTS plugin configuration lives in `15-fts.conf`:

```conf
# /etc/dovecot/conf.d/15-fts.conf
plugin {
  fts = solr  # or: fts = elasticsearch, fts = flatcurve
  fts_autoindex = yes
  fts_autoindex_exclude = "\\Junk"
  fts_autoindex_exclude2 = "\\Trash"
}
```

Each backend uses a different plugin module (`fts_solr`, `fts_elasticsearch`, or `fts_flatcurve`) that must be compiled or installed alongside Dovecot.

## Apache Solr as Dovecot FTS Backend

Apache Solr is the original Dovecot FTS backend and remains the most battle-tested option. Built on Apache Lucene, Solr provides robust full-text search with faceting, highlighting, and proximity queries.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  solr:
    image: solr:9.6
    container_name: dovecot-solr
    ports:
      - "8983:8983"
    volumes:
      - solr_data:/var/solr
      - ./solr-config:/opt/solr-config:ro
    environment:
      - SOLR_HEAP=2g
    command: >
      bash -c "
        solr create_core -c dovecot -d /opt/solr-config &&
        solr -f
      "
    restart: unless-stopped

volumes:
  solr_data:
```

Dovecot Solr plugin configuration:

```conf
plugin {
  fts_solr = url=http://solr:8983/solr/dovecot/
}
```

### Solr Strengths

| Feature | Details |
|---------|---------|
| Maturity | Production-ready for 15+ years, native Dovecot support |
| Schema | Pre-built Dovecot schema with token filters for email |
| Performance | Handles millions of messages with proper heap sizing |
| Query Language | Solr Query Syntax with proximity, wildcards, fuzzy matching |
| Resource Usage | 2-4 GB heap recommended for large mailboxes |
| Community | Large enterprise community, extensive documentation |

## Elasticsearch as Dovecot FTS Backend

Elasticsearch has become the default choice for many self-hosters who already run it for log aggregation (ELK stack) or application search. The Dovecot Elasticsearch plugin uses the official REST API to index and query messages.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.0
    container_name: dovecot-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
      - cluster.name=dovecot-cluster
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    restart: unless-stopped

volumes:
  es_data:
```

Dovecot Elasticsearch plugin configuration:

```conf
plugin {
  fts_elasticsearch = url=http://elasticsearch:9200/ index=dovecot
}
```

### Elasticsearch Strengths

| Feature | Details |
|---------|---------|
| Ecosystem | Unified with Kibana, Logstash for centralized logging |
| API | RESTful JSON API, easy to debug with curl |
| Performance | Excellent distributed search across multiple nodes |
| Analyzers | Built-in language analyzers for 30+ languages |
| Resource Usage | 2-4 GB JVM heap, similar to Solr |
| Licensing | SSPL (Server Side Public License) for versions 7.11+ |

## FlatCurve as Dovecot FTS Backend

FlatCurve is a lightweight, file-based FTS backend designed specifically for smaller deployments. It uses SQLite's FTS5 virtual table module, eliminating the need for a separate search server process.

### Docker Compose Deployment

FlatCurve doesn't require a separate server — it runs as a Dovecot plugin using local files. However, you can containerize it with Dovecot:

```yaml
version: "3.8"
services:
  dovecot:
    image: dovecot/dovecot:latest
    container_name: mail-dovecot
    ports:
      - "143:143"
      - "993:993"
    volumes:
      - ./dovecot:/etc/dovecot:ro
      - mail_data:/var/mail
      - fts_index:/var/lib/dovecot/fts
    environment:
      - DOVECOT_FTS=flatcurve
    restart: unless-stopped

volumes:
  mail_data:
  fts_index:
```

FlatCurve configuration in Dovecot:

```conf
plugin {
  fts = flatcurve
  fts_flatcurve = autoindex=no
  fts_autoindex = yes
  fts_flatcurve_whitespace_tokenizer = default
  fts_flatcurve_max_index_size = 512M
}
```

### FlatCurve Strengths

| Feature | Details |
|---------|---------|
| Architecture | No separate server process — runs inside Dovecot |
| Storage | SQLite FTS5 database files on local disk |
| Resource Usage | Minimal — 100-200 MB RAM beyond Dovecot base |
| Setup | Zero external dependencies beyond Dovecot + SQLite |
| Performance | Good for up to ~500k messages per mailbox |
| Scaling | Single-node only; not suitable for distributed deployments |

## Comparison: Solr vs Elasticsearch vs FlatCurve

| Criteria | Apache Solr | Elasticsearch | FlatCurve |
|----------|------------|---------------|-----------|
| Architecture | Standalone Java server | Standalone Java server | Embedded SQLite plugin |
| Minimum RAM | 2 GB | 2 GB | ~100 MB extra |
| Distributed | Yes (SolrCloud) | Yes (native) | No (single-node) |
| Max Messages | Millions | Millions | ~500k per mailbox |
| Query Language | Solr Query Syntax | Query DSL (JSON) | SQLite FTS5 syntax |
| Language Support | 30+ analyzers | 30+ analyzers | Basic tokenization |
| Setup Complexity | Medium | Medium | Low |
| License | Apache 2.0 | SSPL (7.11+) | Apache 2.0 |
| GitHub Stars | 1,614 | 76,739 | Community plugin |
| Best For | Large mailboxes, enterprise | ELK stack users, distributed | Small servers, simplicity |

## When to Choose Each Backend

**Choose Apache Solr if:** You need the most mature, stable FTS backend with proven performance on large mailboxes. Solr has been the default Dovecot FTS option for years and handles edge cases (corrupted indexes, partial re-indexing) better than alternatives.

**Choose Elasticsearch if:** You already run an ELK stack or need distributed search across multiple mail servers. The REST API makes debugging indexing issues straightforward, and Kibana can visualize search performance metrics.

**Choose FlatCurve if:** You run a small mail server (< 10 users) and want zero external dependencies. FlatCurve eliminates the operational overhead of maintaining a separate search server, making it ideal for single-machine deployments where simplicity matters most.

## Why Self-Host Your Email Search Infrastructure?

Running your own email full-text search infrastructure is a critical component of a fully self-hosted email stack. When you rely on cloud email providers like Gmail or Outlook, every search query you perform — every keyword, every date range, every sender you look up — is processed on their servers. This means your email search patterns, the topics you investigate, and even the frequency of your searches become part of your digital footprint on their infrastructure.

By self-hosting Dovecot with a dedicated FTS backend, you maintain complete ownership of both your email data and the metadata generated by searching it. No third-party server processes your queries, no analytics engine profiles your search habits, and no corporate policy determines which messages are indexed or how quickly results appear.

From a compliance perspective, self-hosted email search is increasingly important for organizations handling sensitive communications. Healthcare providers, legal firms, and financial institutions often face regulatory requirements (HIPAA, GDPR, SOX) that mandate control over all processing of personal data — including search indexes. When your FTS backend runs on your own infrastructure, you can guarantee that message content never leaves your data center, even during the indexing process.

Performance is another compelling reason. Cloud email providers often impose rate limits on search queries or return truncated results for large mailboxes. With a self-hosted Solr or Elasticsearch instance sized to your workload, search queries return in milliseconds regardless of mailbox size. You control the heap allocation, the index segment size, and the query timeout — no shared-tenancy slowdowns.

Cost savings compound over time. Cloud email storage pricing increases linearly with volume, while a self-hosted Solr node on a $20/month VPS can index and search terabytes of email data. The FlatCurve backend costs nothing beyond the Dovecot license (free, open-source), making it the most economical option for budget-conscious deployments.

For those already running self-hosted email infrastructure, adding an FTS backend is a natural extension. If you manage Dovecot for IMAP delivery, pairing it with Solr, Elasticsearch, or FlatCurve gives your users the full-text search experience they expect from modern email clients — without outsourcing the search processing to external services.

For related reading, see our [Dovecot email archiving guide](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/) and our [complete Sieve filtering setup](../2026-05-12-self-hosted-email-sieve-filtering-pigeonhole-rspamd-cyrus-guide/). If you need IMAP synchronization between servers, our [IMAP sync migration guide](../2026-05-10-self-hosted-imap-synchronization-migration-imapsync-offlineimap3-dovecot-dsync/) covers the tools for that.

## FAQ

### Which Dovecot FTS backend is fastest for initial indexing?

Apache Solr typically provides the fastest initial indexing speed for large mailboxes, processing approximately 500-1,000 messages per second on a standard 4-core server with 4 GB heap. Elasticsearch performs similarly but may be slightly slower due to its default refresh interval. FlatCurve is the slowest for bulk indexing (100-300 messages/second) because it writes to SQLite transactionally, but this is acceptable for mailboxes under 100,000 messages.

### Can I switch FTS backends without re-indexing all mailboxes?

No. Each FTS backend uses a proprietary index format that is not portable. Switching from Solr to Elasticsearch (or to FlatCurve) requires rebuilding the entire index from scratch. Dovecot provides the `doveadm fts rescan` and `doveadm index -u user -q '*'` commands to trigger re-indexing. Plan for downtime proportional to mailbox size — typically 1-4 hours for large deployments.

### How much disk space does the FTS index consume?

For Apache Solr and Elasticsearch, the FTS index typically consumes 30-50% of the raw mailbox size. A 10 GB mailbox produces a 3-5 GB search index. FlatCurve indexes are more compact at 20-30% of mailbox size due to SQLite's efficient storage format, but they lack the compression options available in Solr/Elasticsearch.

### Does FlatCurve support attachment search?

Yes, but with limitations. FlatCurve indexes the text content of plain-text and HTML email bodies effectively. For attachments (PDF, DOCX, ODT), you need Dovecot's `fts_mail_filter` plugin to extract text before indexing. Solr and Elasticsearch have more robust attachment parsers built into their respective Dovecot plugins, supporting a wider range of document formats out of the box.

### Can I run multiple FTS backends simultaneously?

Dovecot allows only one active FTS backend per namespace. However, you can configure different namespaces to use different backends (e.g., Solr for the INBOX, FlatCurve for archive folders). This is configured using namespace-specific plugin overrides in `15-fts.conf`. This approach is useful for migrating from one backend to another incrementally.

### What happens if the FTS server goes down?

If the FTS backend becomes unavailable, Dovecot falls back to non-FTS search (linear mailbox scanning), which is significantly slower but still functional. IMAP SEARCH commands will complete, but response times may increase from milliseconds to seconds for large mailboxes. Dovecot logs warnings in the mail log when the FTS backend is unreachable. For production deployments, configure monitoring alerts on the Solr/Elasticsearch health endpoint.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Full-Text Search for Email: Solr vs Elasticsearch vs FlatCurve",
  "description": "Compare three Dovecot FTS backends for self-hosted email search: Apache Solr, Elasticsearch, and FlatCurve. Includes Docker Compose configs, performance benchmarks, and selection guidance.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
