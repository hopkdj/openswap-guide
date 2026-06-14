---
title: "Self-Hosted Corpus Linguistics Platforms: BlackLab vs KonText vs ANNIS"
date: "2026-06-14"
tags: ["corpus-linguistics", "text-analysis", "linguistics", "search-engines", "nlp-tools", "academic-research", "self-hosted"]
draft: false
---

## Introduction

Linguistic research increasingly relies on large annotated text corpora — collections of texts enriched with part-of-speech tags, syntactic parses, and semantic annotations. For linguists, lexicographers, and digital humanities researchers, the ability to query these corpora with sophisticated search patterns is essential. Rather than depending on centralized services or desktop tools that limit collaboration, self-hosted corpus linguistics platforms allow research teams to build, query, and share text corpora on their own infrastructure.

In this guide, we compare three leading open-source corpus query platforms — **BlackLab**, **KonText**, and **ANNIS** — each designed for different research workflows and annotation frameworks.

## Platform Overview

| Feature | BlackLab | KonText | ANNIS |
|---------|----------|---------|-------|
| **Primary Use** | Full-text corpus search with linguistic annotations | Corpus management and query frontend for Manatee/NoSketch Engine | Multi-layer annotation search and visualization |
| **Backend Engine** | Apache Lucene (custom) | Manatee-open | PostgreSQL + custom query engine |
| **Query Language** | Corpus Query Language (CQL) + Lucene | CQL + Manatee query syntax | AQL (ANNIS Query Language) |
| **Annotation Support** | Token-level annotations (POS, lemma) | Token-level + metadata | Multi-layer (token, span, tree, discourse) |
| **Deployment** | Java WAR / Docker | Python + TypeScript, Docker | Java WAR / Tomcat |
| **Stars** | 128 | 80 | 79 |
| **License** | Apache 2.0 | GPL v2 | Apache 2.0 |
| **Active Since** | 2014 | 2012 | 2008 |

## BlackLab: High-Performance Corpus Search

BlackLab, developed by the Dutch Language Institute (INT), is a Java-based corpus search engine built on top of Apache Lucene. It is designed for speed, handling corpora with billions of tokens while maintaining sub-second query response times for most Corpus Query Language (CQL) searches.

### Key Features

- **Index-Based Search**: BlackLab indexes annotated corpora using Lucene's inverted index, allowing extremely fast retrieval of complex linguistic patterns like lemma + POS tag combinations.
- **Corpus Query Language**: Full CQL support with extensions for regular expressions on annotations, sequence queries, and proximity constraints.
- **REST API**: BlackLab Server provides a comprehensive REST API for integration with custom frontends or analysis scripts.
- **Hit Visualization**: Built-in support for keyword-in-context (KWIC) views and frequency breakdowns.

### Docker Compose Deployment

BlackLab provides an official Docker Compose configuration for quick deployment:

```yaml
version: "3.8"
services:
  blacklab:
    image: instituutnederlandsetaal/blacklab:latest
    container_name: blacklab-server
    ports:
      - "8080:8080"
    volumes:
      - ./data/blacklab-index:/data/index
      - ./data/blacklab-config:/usr/local/tomcat/webapps/blacklab/WEB-INF/blacklab/
    environment:
      - JAVA_OPTS=-Xmx4g -Xms2g
    restart: unless-stopped
```

Indexing a corpus can be done via the command-line interface:

```bash
# Index a TEI/XML annotated corpus
java -cp blacklab.jar nl.inl.blacklab.tools.IndexTool   create /data/index/my-corpus   /corpora/my-corpus/*.xml   tei-p5

# Query via the REST API
curl "http://localhost:8080/blacklab-server/my-corpus/hits?patt=%5Blemma%3D%22run%22%5D&number=20"
```

## KonText: The All-in-One Corpus Platform

KonText, developed at Charles University in Prague, serves as a modern web frontend for the Manatee-open corpus search engine — the same engine that powers the popular Sketch Engine platform. It provides a complete corpus management interface including corpus creation, query formulation, concordance viewing, and statistical analysis.

### Key Features

- **Integrated Corpus Management**: Upload, configure, and manage multiple corpora through a web interface without command-line operations.
- **Rich Query Builder**: Both a visual query builder for beginners and a CQL editor for advanced users.
- **Frequency Distribution**: Automatic computation of frequency distributions, collocations, and multi-word expressions.
- **Subcorpus Creation**: Dynamically create subcorpora based on metadata filters for targeted analysis.
- **User Management**: Built-in authentication and role-based access control for research teams.

### Docker Compose Setup

KonText provides a Docker-based deployment with separate services for the web application, worker processes, and Redis:

```yaml
version: "3"
services:
  kontext:
    image: czcorpus/kontext:latest
    container_name: kontext-app
    ports:
      - "5000:5000"
    volumes:
      - ./data/kontext-corpora:/opt/kontext/data/corpora
      - ./config/kontext.xml:/opt/kontext/conf/config.xml
    environment:
      - KONTEXT_DB_HOST=postgres
      - KONTEXT_REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=kontext
      - POSTGRES_USER=kontext
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - ./data/postgres:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
```

To register and compile a corpus in KonText:

```bash
# Register a new corpus (after placing data in the corpora directory)
docker exec kontext-app python scripts/addcorpus.py   --name my_corpus   --path /opt/kontext/data/corpora/my_corpus   --lang en

# Compile the corpus for Manatee
docker exec kontext-app compile_corpus my_corpus
```

## ANNIS: Multi-Layer Annotation Search

ANNIS (ANNotation of Information Structure) stands out from BlackLab and KonText by supporting **multi-layer annotations** — the ability to query across different annotation levels (token, syntax tree, coreference, discourse) simultaneously. Developed at multiple German universities, ANNIS handles the kind of complex linguistic data that arises in treebank and discourse analysis research.

### Key Features

- **Multi-Layer Queries**: Query token-level annotations, constituency trees, dependency graphs, and coreference chains in a single query.
- **AQL Query Language**: The ANNIS Query Language supports cross-layer references, dominance relations, and pointing relations between annotation spans.
- **Visual Result Display**: Results are displayed with synchronized views showing the matched spans in their linguistic context across all annotation layers.
- **SaltNPepper Format**: Uses the ISO-standard SaltNPepper data model for representing multi-layer annotated corpora.

### Manual Deployment

Unlike BlackLab and KonText, ANNIS does not provide an official Docker image. However, it can be deployed using a standard Java servlet container:

```bash
# Download the ANNIS service
wget https://corpus-tools.org/annis/download/annis-service-4.8.0-distribution.tar.gz
tar xzf annis-service-4.8.0-distribution.tar.gz
cd annis-service-4.8.0

# Configure PostgreSQL backend
export ANNIS_DB_URL="jdbc:postgresql://localhost:5432/annis"
export ANNIS_DB_USER="annis"
export ANNIS_DB_PASSWORD="secure_password"

# Start the service
./bin/annis-service.sh start

# Import a corpus in the relANNIS format
curl -X POST http://localhost:5711/annis/admin/import   -F "file=@/data/corpora/my_corpus.zip"
```

Alternatively, you can create a custom Docker container using the provided startup scripts:

```dockerfile
FROM tomcat:9.0-jdk17
COPY annis-service.war /usr/local/tomcat/webapps/annis.war
ENV ANNIS_DB_URL=jdbc:postgresql://postgres:5432/annis
EXPOSE 8080
CMD ["catalina.sh", "run"]
```

## Choosing the Right Platform

**Choose BlackLab** if your primary need is high-performance CQL search over large token-annotated corpora with a focus on speed and scalability. Its Lucene-based backend excels at full-text and annotation search across billions of tokens.

**Choose KonText** if you need a complete, user-friendly corpus management platform with built-in frequency analysis, collocation tools, and a visual query builder. It is ideal for research teams that want a Sketch Engine-like experience on their own infrastructure.

**Choose ANNIS** if your linguistic data includes multiple annotation layers beyond token-level tags — syntax trees, coreference chains, discourse structure, or prosodic annotations. ANNIS is the only platform that handles these complex multi-layer queries natively.

## Why Self-Host Your Corpus Linguistics Platform?

Running your own corpus linguistics infrastructure gives you complete control over sensitive language data, which is especially important for research involving proprietary corpora, indigenous language documentation, or medical text analysis. Self-hosting eliminates recurring subscription costs associated with commercial platforms like Sketch Engine, which can run into thousands of euros per year for institutional licenses.

Self-hosted platforms also enable integration with other research infrastructure. A corpus server can feed data into annotation tools like Label Studio or provide query access to computational linguistics scripts that analyze collocations and frequency patterns. For digital humanities projects, having the corpus engine on the same network as your web publishing platform dramatically reduces the latency of interactive text analysis features.

For broader text processing pipelines, see our guide on [self-hosted grammar and style checking tools](../2026-04-29-languagetool-vs-vale-vs-textlint-self-hosted-grammar-style-checking-guide-2026/). If your research involves manual text annotation, our [self-hosted data annotation platform comparison](../2026-04-26-label-studio-vs-doccano-vs-cvat-self-hosted-data-annotation-guide-2026/) covers Label Studio, Doccano, and CVAT. For researchers working with multiple languages, check our [self-hosted language learning platforms guide](../2026-06-12-self-hosted-language-learning-platforms-librelingo-lute-tatoeba/).


## Performance and Scalability Considerations

When deploying corpus linguistics platforms for production research use, consider the following scaling factors. BlackLab's Lucene-based index scales linearly with corpus size — a 1-billion-word corpus typically requires 30-60 GB of indexed storage depending on annotation density. KonText's Manatee backend benefits from SSD storage for fast concordance retrieval, especially when computing collocation statistics across large corpora. ANNIS uses PostgreSQL for annotation storage, making it the most memory-intensive option when querying corpora with complex multi-layer annotations such as discourse parsing trees and coreference graphs.

For high-availability deployments, BlackLab Server can be placed behind a load balancer with read replicas sharing the same index on network-attached storage. KonText's architecture separates the web frontend from the Manatee query engine, allowing independent scaling of query workers during peak usage periods. ANNIS recommends at minimum 8 GB of RAM for corpora exceeding 100 million tokens with tree annotations, and benefits from PostgreSQL connection pooling via PgBouncer for concurrent user access.


## FAQ

### What is Corpus Query Language (CQL)?

CQL is a standardized query language for searching linguistically annotated corpora. It allows you to search for word forms, lemmas, part-of-speech tags, and their combinations. For example, `[lemma="run" & pos="V.*"]` finds all verb forms of the word "run." Both BlackLab and KonText support CQL queries natively.

### Can I use these platforms with non-English corpora?

Yes, all three platforms are language-agnostic. They work with any language as long as the corpus has been properly tokenized and annotated. The annotation pipeline (tokenization, POS tagging, lemmatization) is handled separately — tools like spaCy, Stanza, or UDPipe can pre-process your texts before indexing.

### How much disk space do I need for a corpus?

A general rule of thumb is that the indexed corpus requires about 2-3x the size of the raw text files. A 10 GB corpus of annotated text will typically need 20-30 GB of disk space for the index plus metadata. BlackLab's Lucene-based index is generally the most space-efficient of the three.

### Can multiple users access these platforms simultaneously?

Yes. All three platforms are designed as multi-user web applications. KonText includes built-in user management with role-based access control. BlackLab Server supports multiple concurrent users but relies on external authentication (reverse proxy) for access control. ANNIS supports multiple simultaneous query sessions through its Tomcat servlet container.

### How do I move from a commercial corpus platform like Sketch Engine?

KonText is the most direct migration path from Sketch Engine, as it uses the same Manatee-open backend engine. Corpora compiled with Manatee can be directly imported into KonText. For Sketch Engine users moving to BlackLab, you would need to export your data as TEI XML or CoNLL format and re-index it using BlackLab's indexing tools.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Corpus Linguistics Platforms: BlackLab vs KonText vs ANNIS",
  "description": "Compare three leading open-source corpus linguistics platforms: BlackLab for high-performance corpus search, KonText for integrated corpus management, and ANNIS for multi-layer annotation queries. Includes Docker Compose deployment guides.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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
