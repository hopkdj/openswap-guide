---
title: "Tantivy vs Bleve vs Lucene vs Xapian in 2026: Which Embedded Full-Text Search Library Wins?"
date: "2026-10-05"
tags: ["search", "full-text-search", "developer-tools", "rust", "golang", "java"]
draft: false
cover: "/img/screenshots/lucene-logo.jpg"
---

# Tantivy vs Bleve vs Lucene vs Xapian in 2026

Chartering a cargo ship to deliver a single letter is exactly what you do when you spin up a three-node Elasticsearch cluster to search 40,000 notes, log files, or product records baked into your application. You inherit JVM tuning, heap sizing, network hops, security patches, an ops runbook, and a monthly bill — all to answer "which of my documents contain this word?"

An embedded full-text search library collapses that stack into a single dependency inside your own process. You write to a local index directory, you run queries in-process, you ship one binary. The trade-off is that you own the indexing pipeline, the schema, and the commit lifecycle. That trade is almost always worth it below a few tens of millions of documents.

Four libraries dominate this space in 2026, and they map cleanly onto four language ecosystems: **Tantivy** (Rust), **Bleve** (Go), **Apache Lucene** (Java), and **Xapian** (C++, with bindings for Python, Ruby, Perl, and more). This guide compares them on real 2026 data, shows working code for each, and tells you which one to pick without hedging.

## TL;DR: The 30-second verdict

- **Building in Rust, or you want the fastest indexing throughput on the market?** Pick **Tantivy**.
- **Building in Go and you want zero cgo, a single static binary, and BM25 plus vector search out of the box?** Pick **Bleve**.
- **Already on the JVM and you need the richest analyzers, the largest ecosystem, and the implementation everyone else copies?** Pick **Apache Lucene**.
- **Writing C++ (or driving search from Python/Ruby/Perl) and you need a compact, battle-tested engine with first-class bindings?** Pick **Xapian** — but check the GPL.

If you want a search *server* (REST API, replication, dashboards) rather than a library, none of these are the right answer by themselves; keep reading for the exit ramps.

## Library health and feature comparison

All star counts and commit dates below were pulled live from GitHub in October 2026.

| Library | Language | GitHub stars | License | Last commit | Index model | Killer feature |
|---|---|---|---|---|---|---|
| **Tantivy** | Rust | 16,183 | MIT | 2026-10-02 | Immutable columnar segments | Fastest multithreaded indexing; tiny memory footprint |
| **Bleve** | Go | 11,224 | Apache-2.0 | 2026-10-04 | Scorch segment index | Pure Go, no cgo; BM25, geo, and vector search |
| **Apache Lucene** | Java | 3,572 (GitHub mirror) | Apache-2.0 | 2026-10-04 | Classic inverted-index segments | The reference implementation; deepest analysis chain |
| **Xapian** | C++ | 875 | GPL-2.0-or-later | 2026-10-04 | Glass backend | Bindings for a dozen languages; very small footprint |

Two things jump out. First, all four projects are actively maintained — none is abandoned, so this is a genuine engineering choice rather than a "pick the one that still compiles" decision. Second, license matters enormously here: Lucene, Tantivy, and Bleve ship under permissive licenses you can embed in a closed-source product, while **Xapian is GPL-licensed**, which is a hard blocker for many commercial applications.

![Bleve is a pure-Go embedded search library with a single static binary](/img/screenshots/bleve-logo.jpg "Bleve embedded search library logo")

## Which library for which job?

Use this decision matrix when you have ten seconds and one architectural constraint.

| Use case | Recommendation | Why |
|---|---|---|
| Rust service, millions of documents, tight latency budget | **Tantivy** | Segment-parallel indexing and a mmap-based reader; no runtime to host |
| Go microservice shipped as one static binary | **Bleve** | No cgo, no external process, BM25 plus kNN in the same index |
| JVM app needing custom analyzers, stemmers, and token filters | **Apache Lucene** | Dozens of analyzers, synonym graphs, and the analyzers Solr/Elasticsearch reuse |
| C++ desktop or embedded product with a small disk budget | **Xapian** | Compact Glass index and a C++ API that compiles almost anywhere |
| Python or Ruby app that needs a real index, not SQL LIKE | **Xapian** (bindings) | Mature SWIG bindings for Python, Ruby, Perl, and Tcl |
| You actually need clustering, sharding, and a REST API | **None of these** | Use Quickwit, OpenSearch, or a Lucene server instead |

## Tantivy: the Rust speed demon

**16,183 stars · MIT · last commit October 2, 2026**

Tantivy was explicitly inspired by Lucene's design but rebuilt in Rust around immutable segments. Its README makes a claim that is hard to ignore: indexing English Wikipedia takes under three minutes on a desktop machine, using multithreaded indexing. In practice you feel that speed in two places — bulk imports and rebuild-on-schema-change, both of which are where embedded search usually hurts.

Add it to a project with Cargo:

```toml
[dependencies]
tantivy = "0.24"
```

A complete index-and-search loop looks like this:

```rust
use tantivy::collector::TopDocs;
use tantivy::query::QueryParser;
use tantivy::schema::*;
use tantivy::{doc, Index};

fn main() -> tantivy::Result<()> {
    let mut schema_builder = Schema::builder();
    let title = schema_builder.add_text_field("title", TEXT | STORED);
    let body = schema_builder.add_text_field("body", TEXT);
    let schema = schema_builder.build();

    let index = Index::create_in_ram(schema);
    let mut writer = index.writer(50_000_000)?;

    writer.add_document(doc!(
        title => "Tantivy vs Lucene",
        body => "Embedded full-text search in Rust",
    ))?;
    writer.commit()?;

    let reader = index.reader()?;
    let searcher = reader.searcher();
    let parser = QueryParser::for_index(&index, vec![title, body]);
    let query = parser.parse_query("rust")?;

    for (_score, addr) in searcher.search(&query, &TopDocs::with_limit(10))? {
        let doc: TantivyDocument = searcher.doc(addr)?;
        println!("{}", doc.to_json(&schema)?);
    }
    Ok(())
}
```

The one behavior that trips up newcomers: **documents are only searchable after `commit()`**, and existing readers must be reloaded to see new segments. Data in Tantivy is immutable, so updating a document means deleting and re-adding it. Design your ingestion around batching, and commit on a timer rather than after every single write.

## Bleve: search that ships as a single Go binary

**11,224 stars · Apache-2.0 · last commit October 4, 2026**

Bleve is the Go answer, and its selling point is operational simplicity. There is no cgo, no JVM, no separate daemon — your service and its search index are the same artifact. Under the hood the default **Scorch** index delivers segment-based storage with intelligent defaults, and the feature list is broader than most people assume: BM25 and tf-idf scoring, geospatial queries, hierarchical and nested documents, synonyms, and approximate k-nearest-neighbor vector search.

```bash
go get github.com/blevesearch/bleve/v2
```

```go
package main

import (
	"fmt"

	"github.com/blevesearch/bleve/v2"
)

func main() {
	mapping := bleve.NewIndexMapping()
	index, err := bleve.New("example.bleve", mapping)
	if err != nil {
		panic(err)
	}
	defer index.Close()

	type Note struct {
		Title string `json:"title"`
		Body  string `json:"body"`
	}

	index.Index("note-1", Note{Title: "Bleve vs Tantivy", Body: "Pure Go embedded search"})

	query := bleve.NewMatchQuery("embedded")
	req := bleve.NewSearchRequest(query)
	res, err := index.Search(req)
	if err != nil {
		panic(err)
	}
	fmt.Println(res)
}
```

Two production notes. First, indexing is a *separate* operation from searching, and the index is safe to open read-only from many goroutines but writes should be serialized through one writer. Second, if you want a Bleve-backed HTTP service instead of an in-process library, the project's companion tooling and the `bleve/http` utilities give you a thin REST layer without adopting a full search platform.

## Apache Lucene: the reference implementation

**3,572 stars on the GitHub mirror · Apache-2.0 · last commit October 4, 2026**

Lucene is the engine underneath Elasticsearch, OpenSearch, and Solr, and its 25-year head start shows in exactly one place that matters: **analysis**. If you need language-specific stemmers, decompounding, synonym graphs, custom token filters, or analyzers for twenty natural languages, Lucene already has them, and the other three libraries either port Lucene's analyzers or ask you to write your own.

Add the dependency and index a document:

```xml
<dependency>
  <groupId>org.apache.lucene</groupId>
  <artifactId>lucene-core</artifactId>
  <version>10.3.0</version>
</dependency>
```

```java
Directory dir = FSDirectory.open(Path.of("index"));
Analyzer analyzer = new StandardAnalyzer();
IndexWriter writer = new IndexWriter(dir, new IndexWriterConfig(analyzer));

Document doc = new Document();
doc.add(new TextField("title", "Lucene in action", Field.Store.YES));
doc.add(new TextField("body", "Embedded search on the JVM", Field.Store.NO));
writer.addDocument(doc);
writer.commit();
writer.close();

IndexSearcher searcher = new IndexSearcher(DirectoryReader.open(dir));
Query q = new TermQuery(new Term("body", "embedded"));
TopDocs hits = searcher.search(q, 10);
System.out.println(hits.totalHits);
```

The cost of that power is weight: you are running a JVM, you are managing heap, and your deployment artifact is far larger than a Rust or Go binary. Lucene is the right call when the JVM is already your home and analysis quality is the priority — not when you want a 4 MB static binary.

## Xapian: the veteran with bindings everywhere

**875 stars · GPL-2.0-or-later · last commit October 4, 2026**

Xapian has been indexing documents since 2001, and its probabilistic information-retrieval model was doing BM25-style weighting before BM25 was fashionable. The Glass backend it ships today is compact and fast, and Xapian's real differentiator is **SWIG-generated bindings**: you can drive the same C++ engine from Python, Ruby, Perl, Tcl, and more.

```cpp
#include <xapian.h>

Xapian::WritableDatabase db("index", Xapian::DB_CREATE_OR_OPEN);
Xapian::TermGenerator indexer;
Xapian::Document doc;
doc.set_data("Embedded full-text search in C++");
indexer.set_document(doc);
indexer.index_text("Embedded full-text search in C++");
db.add_document(doc);
db.commit();

Xapian::Enquire enquire(Xapian::Database("index"));
enquire.set_query(Xapian::Query("embedded"));
Xapian::MSet matches = enquire.get_mset(0, 10);
```

Pick Xapian when footprint matters more than raw indexing speed, or when your application is written in one of the languages where Xapian is the only serious embedded option (Python and Ruby in particular). Verify the GPL fits your distribution model before you commit, and budget time for its more imperative API — this is not a library that hides its C++ heritage.

## Pitfalls and migration notes

**Commit semantics differ, and they bite.** Tantivy and Xapian make new documents visible only after an explicit `commit()`, and Tantivy readers must reload. Bleve batches too. If your tests pass with tiny fixtures but production search lags by seconds, this is why.

**Tokenizer symmetry is a classic bug.** The analyzer that tokenizes at index time must match the one used to build the query. Swap an analyzer later and previously indexed documents become silently unfindable. Pin your analyzer in the schema and treat changes as a full reindex.

**Numeric and date fields need explicit types.** Storing a number in a text field means it is searched lexicographically, so `"10"` sorts before `"9"`. All four libraries require you to declare field types up front; small type mistakes cause large ranking surprises.

**Index size is not small.** An inverted index commonly lands between 20% and 50% of the raw text size depending on whether you store positions and term frequencies. Position indexing enables phrase queries but roughly doubles the index — turn it off if you never use phrases.

**You are now the search team.** Embedded search means no dashboard, no query profiler, no replication. Add structured logging around index and search latency early, because you have no cluster UI to fall back on.

**Don't embed when you need a server.** If you need multi-node replication, cross-team index sharing, or a query UI, reach for a real search platform. Our [comparison of search stacks for mail full-text search](../2026-05-22-self-hosted-dovecot-full-text-search-solr-elasticsearch-lucene-guide/) shows what that deployment actually costs, and if your documents live in the browser, a [client-side fuzzy search library](../2026-08-18-fusejs-vs-minisearch-vs-lunrjs-client-side-fuzzy-search-comparison/) is a better fit than any of these four. Teams that index structured text before it ever reaches the indexer should also read our [markdown parser library comparison](../2026-06-20-markdown-parser-libraries-pulldown-cmark-goldmark-comrak-commonmarkjs/) for the tokenization half of the pipeline.

## FAQ

### Can I run Tantivy, Bleve, Lucene, or Xapian as a standalone search server?

No. All four are libraries that live inside your process. Tantivy is used by other projects to build search services, Bleve has thin HTTP helpers, and Lucene underpins Solr, Elasticsearch, and OpenSearch, but none of them ships a ready-made REST server with replication. If you need a server, use Quickwit, OpenSearch, or Solr.

### Which embedded search library is fastest?

Tantivy usually wins on raw indexing throughput thanks to multithreaded, immutable-segment indexing — its own benchmarks index English Wikipedia in under three minutes. Lucene is close behind on the JVM and tends to win on query throughput once caches are warm. Bleve is fast enough for most Go services, and Xapian prioritizes footprint over peak speed.

### Do any of these support vector or semantic search?

Bleve supports approximate k-nearest-neighbor vector search natively, and Lucene ships HNSW-based vector fields that power modern vector search on the JVM. Tantivy and Xapian are primarily lexical engines, so adding vector search there means pairing them with a dedicated vector index. For hybrid lexical-plus-vector search, Bleve and Lucene are the shortest paths.

### Are these libraries free for commercial use?

Tantivy (MIT), Bleve (Apache-2.0), and Lucene (Apache-2.0) can be embedded in closed-source commercial products without paying or open-sourcing your code. Xapian is licensed under GPL-2.0-or-later, so if you distribute a product that links it, you must comply with the GPL — check this before designing around Xapian.

### How much memory and disk do I need?

Plan for an index between 20% and 50% of the raw text size, plus mmap-backed page cache that the operating system manages. Tantivy and Xapian map segments into memory; Bleve's Scorch index is also segment-based; Lucene needs an explicitly sized JVM heap. Budget disk first — memory can usually be left to the OS cache.

### Can I migrate from Lucene to Tantivy or Bleve?

There is no drop-in index conversion, because the on-disk formats are entirely different. You reindex from your source of truth. The good news is that the source documents are usually still in a database or on disk, and reindexing is the fastest these libraries ever run — Tantivy's multithreaded pipeline and Bleve's batch API make a full rebuild a minutes-long job, not a migration project.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Tantivy vs Bleve vs Lucene vs Xapian in 2026: Which Embedded Full-Text Search Library Wins?",
  "description": "A 2026 comparison of embedded full-text search libraries Tantivy, Bleve, Apache Lucene, and Xapian, with live GitHub data, working code examples, a decision matrix, and licensing advice.",
  "datePublished": "2026-10-05",
  "dateModified": "2026-10-05",
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
