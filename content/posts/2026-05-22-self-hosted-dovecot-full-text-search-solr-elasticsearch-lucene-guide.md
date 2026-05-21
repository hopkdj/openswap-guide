---
title: "Self-Hosted Dovecot Full-Text Search: Solr vs Elasticsearch vs Lucene"
date: "2026-05-22"
tags: ["email", "full-text-search", "dovecot", "solr", "elasticsearch"]
draft: false
---

Full-text search (FTS) is essential for modern email servers. Without it, searching through thousands of emails means scanning every message on disk — a slow, resource-intensive operation. Dovecot, the leading open-source IMAP/POP3 server, supports multiple FTS backends that index email content for instant search.

In this guide, we compare three FTS backends for Dovecot: **Apache Solr**, **Elasticsearch**, and **Lucene** (Dovecot's built-in option). Each offers different trade-offs in performance, resource usage, and operational complexity.

## Why Full-Text Search for Email?

Email search requirements are unique:
- **Large corpora**: Mailboxes often contain tens of thousands of messages
- **Rich content**: Search across subject, body, headers, attachments
- **Real-time indexing**: New emails must be searchable immediately
- **Multi-language support**: Users write emails in many languages
- **Fuzzy matching**: Typo-tolerant search for partially remembered subjects

Without FTS, IMAP SEARCH commands scan every message sequentially. With FTS, search results return in milliseconds regardless of mailbox size.

---

## Dovecot FTS with Apache Solr

Apache Solr is a mature, enterprise-grade search platform built on Apache Lucene. It provides powerful full-text search with faceting, highlighting, and distributed search capabilities.

### Architecture

Dovecot communicates with Solr via HTTP/REST API. The `dovecot-fts-solr` plugin sends indexing requests and search queries to a Solr server. Solr handles tokenization, stemming, and ranking internally.

### Key Features

- **Advanced query language**: Solr's query syntax supports wildcards, proximity, and boosting
- **Faceted search**: Filter results by sender, date range, folder, or attachment type
- **Highlighting**: Return search result snippets with highlighted matches
- **Distributed search**: SolrCloud enables horizontal scaling across multiple nodes
- **Schema flexibility**: Define custom field types and analyzers
- **Mature ecosystem**: Extensive documentation, community, and third-party integrations

### Docker Compose Deployment

```yaml
services:
  solr:
    image: solr:9-slim
    ports:
      - "8983:8983"
    volumes:
      - solr-data:/var/solr
      - ./solr-config:/opt/solr-config:ro
    environment:
      - SOLR_HEAP=1g
      - SOLR_JAVA_MEM=-Xms1g -Xmx1g
    command: >
      bash -c "
        solr create_core -c dovecot -d /opt/solr-config &&
        exec solr -f
      "
    restart: unless-stopped

  dovecot:
    image: dovecot/dovecot:latest
    ports:
      - "143:143"
      - "993:993"
    volumes:
      - ./mail:/var/mail
      - ./dovecot:/etc/dovecot:ro
    depends_on:
      - solr
    restart: unless-stopped

volumes:
  solr-data:
```

Dovecot FTS configuration (`/etc/dovecot/conf.d/10-mail.conf`):

```
mail_plugins = $mail_plugins fts fts_solr

plugin {
  fts = solr
  fts_autoindex = yes
  fts_solr = url=http://solr:8983/solr/dovecot/
}
```

### When to Use Solr

- You need advanced search features (faceting, highlighting, suggestions)
- You already run Solr for other search needs
- You want a mature, well-documented solution
- You need distributed search across multiple nodes

---

## Dovecot FTS with Elasticsearch

Elasticsearch is the most popular open-source search and analytics engine, also built on Apache Lucene. It provides a RESTful API, powerful query DSL, and real-time indexing.

### Architecture

Dovecot communicates with Elasticsearch via HTTP. The `dovecot-fts-elastic` plugin (available in Dovecot 2.3+) handles indexing and querying. Elasticsearch's inverted index provides fast, scalable search across all indexed email content.

### Key Features

- **Rich query DSL**: Bool queries, fuzzy matching, range queries, and more
- **Real-time indexing**: Documents are searchable within seconds of indexing
- **Aggregations**: Complex analytics on search results
- **Scalability**: Horizontal scaling with automatic shard management
- **Security**: TLS, authentication, and role-based access control
- **Elastic Stack integration**: Combine with Kibana for email analytics dashboards

### Docker Compose Deployment

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
      - xpack.security.enabled=false
      - xpack.security.enrollment.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ulimits:
      memlock:
        soft: -1
        hard: -1
    restart: unless-stopped

  dovecot:
    image: dovecot/dovecot:latest
    ports:
      - "143:143"
      - "993:993"
    volumes:
      - ./mail:/var/mail
      - ./dovecot:/etc/dovecot:ro
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  es-data:
```

Dovecot FTS configuration (`/etc/dovecot/conf.d/10-mail.conf`):

```
mail_plugins = $mail_plugins fts fts_elastic

plugin {
  fts = elastic
  fts_autoindex = yes
  fts_elastic = url=http://elasticsearch:9200/ bulk_size=5000000
  fts_languages = en
  fts_tokenizers = generic algorithm=uas
}
```

### When to Use Elasticsearch

- You already run Elasticsearch for log analytics or other search needs
- You need the richest query capabilities and real-time indexing
- You want integration with the Elastic Stack (Kibana, Logstash, Beats)
- You have the resources to run Elasticsearch (memory-intensive)

---

## Dovecot FTS with Lucene (Built-In)

Dovecot ships with a built-in Lucene-based FTS backend that requires no external search server. It uses Apache Lucene directly via JNI, running as part of the Dovecot process.

### Architecture

The `dovecot-fts-lucene` plugin embeds Lucene within Dovecot. Indexes are stored on disk alongside mail directories. No separate search server is needed — everything runs within the Dovecot process.

### Key Features

- **Zero external dependencies**: No separate search server to manage
- **Simple deployment**: Just enable the plugin and Dovecot handles everything
- **Low resource usage**: Minimal memory overhead compared to Solr/Elasticsearch
- **Automatic indexing**: Indexes new messages as they arrive
- **Per-user indexes**: Each mailbox has its own Lucene index
- **No network dependency**: Search works even if external services are down

### Configuration

Enable the Lucene plugin in Dovecot:

```bash
# Install the Lucene FTS plugin
apt install dovecot-lucene
# or
yum install dovecot-fts-lucene
```

```
mail_plugins = $mail_plugins fts fts_lucene

plugin {
  fts = lucene
  fts_autoindex = yes
  fts_lucene = whitespace_chars=@.
}
```

### When to Use Lucene

- You want the simplest possible setup with no external dependencies
- You're running on resource-constrained hardware
- You don't need advanced search features (faceting, distributed search)
- You have a small number of mailboxes (hundreds, not thousands)

---

## Comparison Table

| Feature | Dovecot + Solr | Dovecot + Elasticsearch | Dovecot + Lucene |
|---------|---------------|------------------------|-----------------|
| **External Server Required** | Yes (Solr) | Yes (Elasticsearch) | No (built-in) |
| **Minimum RAM** | 1 GB (Solr) | 2 GB (ES) | 128 MB extra |
| **Setup Complexity** | Medium | Medium-High | Low |
| **Query Language** | Solr query syntax | Elasticsearch DSL | Lucene query syntax |
| **Faceted Search** | Yes | Yes | No |
| **Highlighting** | Yes | Yes | Limited |
| **Distributed Search** | Yes (SolrCloud) | Yes (cluster) | No (local only) |
| **Real-time Indexing** | Near real-time | Real-time | Near real-time |
| **Multi-language** | Yes (analyzers) | Yes (analyzers) | Basic |
| **Maintenance Overhead** | Medium | High | Low |
| **Best For** | Advanced search needs | Elastic Stack users | Simple deployments |

## Why Self-Host Email FTS?

Cloud email providers (Gmail, Outlook) include powerful search by default. Self-hosted email servers need equivalent capabilities:

- **Data privacy**: Email content never leaves your infrastructure
- **Custom ranking**: Tune search relevance for your organization's needs
- **No usage limits**: Cloud FTS APIs charge per query or have rate limits
- **Compliance**: Keep search indexes within your data jurisdiction
- **Integration**: Combine email search with other internal search indexes

For mail servers handling thousands of users, FTS backends reduce search latency from seconds to milliseconds, dramatically improving user experience with IMAP clients like Thunderbird, Roundcube, or mobile email apps.

### Performance Tuning Tips

1. **Index warm-up**: Run `doveadm fts rescan -A && doveadm fts optimize -A` after major configuration changes
2. **Auto-indexing**: Set `fts_autoindex = yes` to index messages as they arrive
3. **Batch indexing**: For bulk migrations, use `doveadm fts index -A` to index all existing mail
4. **Memory tuning**: Allocate at least 512MB heap for Solr/Elasticsearch with 10K+ mailboxes
5. **Disk I/O**: Place Lucene indexes on SSD storage for faster search performance
6. **Shard management**: For Elasticsearch, configure 1-2 shards per index for email workloads

For related reading on email infrastructure, see our [email auth guide](../2026-05-14-self-hosted-email-authentication-opendkim-rspamd-opendmarc-guide/) and [SMTP bounce handling comparison](../2026-04-30-self-hosted-smtp-bounce-dsn-handling-postal-bouncr-postfix-guide/). For IMAP synchronization tools, check our [IMAP sync guide](../2026-05-10-self-hosted-imap-sync-imapsync-offlineimap3-dovecot-dsync-guide/).

## FAQ

### Which FTS backend should I choose for Dovecot?

For most users, start with the built-in Lucene backend — it requires zero configuration and works well for small to medium mail servers. Upgrade to Solr or Elasticsearch when you need advanced features (faceting, distributed search) or when Lucene becomes a performance bottleneck with large mailboxes.

### How much disk space does FTS indexing consume?

Rule of thumb: FTS indexes consume 30-50% of the original mailbox size. A 10 GB mailbox will need approximately 3-5 GB for the search index. Elasticsearch and Solr indexes may use slightly more due to additional metadata and shard overhead.

### Can I switch FTS backends without losing my email?

Yes. FTS backends only manage search indexes, not the actual email data. To switch backends: (1) disable the current FTS plugin, (2) run `doveadm fts rescan -A` to clear old indexes, (3) enable the new plugin, (4) run `doveadm fts index -A` to rebuild indexes. Email messages are never affected by FTS changes.

### Does Dovecot FTS support searching email attachments?

By default, Dovecot FTS indexes the email body, subject, and headers — not attachment content. To index attachments, you need additional tools like Apache Tika (which can be integrated with both Solr and Elasticsearch) to extract text from PDFs, Word documents, and other file types before indexing.

### How do I troubleshoot slow FTS search results?

First, check if the index is up to date: `doveadm fts rescan -A`. If the index is stale, rebuild it with `doveadm fts index -A`. For Solr/Elasticsearch, verify the server is responding: `curl http://localhost:8983/solr/` or `curl http://localhost:9200/`. Check server logs for indexing errors. For Lucene, ensure the `lucene` plugin is properly installed (`doveconf -n | grep fts`).

### Can I use multiple FTS backends simultaneously?

Dovecot supports only one active FTS backend per user. However, you can configure different backends for different users using Dovecot's userdb settings. For example, power users could use Elasticsearch while regular users use Lucene.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Dovecot Full-Text Search: Solr vs Elasticsearch vs Lucene",
  "description": "Compare three full-text search backends for Dovecot email server: Apache Solr, Elasticsearch, and built-in Lucene. Covers deployment, performance, and configuration.",
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
