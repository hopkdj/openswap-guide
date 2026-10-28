---
title: "Hister vs YaCy vs Stract in 2026: Which Self-Hosted Search Engine Is Actually Worth Running?"
date: "2026-10-28"
tags: ["self-hosted", "search-engine", "privacy", "docker", "comparison"]
cover: "/img/screenshots/hister-search.jpg"
description: "Hister, YaCy and Stract solve three completely different problems. A 2026 hands-on comparison of self-hosted search: index ownership, Docker deployment, resource cost and maintenance risk."
draft: false
---

Search is the one utility almost nobody self-hosts, and the reason is a misunderstanding. People hear "self-hosted search engine" and assume they must out-crawl Google. They do not. The useful question is narrower: which of your own information should be searchable without a third party in the loop?

That question produces three different answers, and the three projects in this comparison are not competitors at all. Hister indexes the pages and files **you** visit. YaCy builds a shared index across peers or crawls your intranet. Stract is a real web search engine you have to feed an index yourself.

Choosing wrong wastes a weekend. Here is the honest breakdown.

## TL;DR — Quick Verdict

**If you want to find things you have already read, deploy Hister.** It is a 6K-star Go binary with a browser extension, full-text indexing of visited pages and local directories, a container that runs in under 100 MB, and a published Compose file. This is the highest-value self-hosted search project in 2026.

**If you need to search an intranet, a document archive, or want to participate in a peer-to-peer index, deploy YaCy.** It is the only mature option that crawls and shares at scale — and it costs you 1-2 GB of RAM and a 2000s-era admin UI to get there.

**If you want to study or fork a modern search engine, clone Stract.** Do not deploy it expecting a Google replacement: it has no Docker image, requires building a Rust toolchain stack, and its last commit was **2025-03-24** — roughly 19 months before this article. Use the hosted instance instead.

Everything else — SearXNG, Whoogle, LibreX — is a proxy in front of someone else's index, which is an entirely different category we covered separately in our [privacy metasearch comparison](../searxng-vs-whoogle-vs-librex-self-hosted-privacy-search-engines-2026/).

## Comparison Table (verified 2026-10-28)

| Dimension | Hister | YaCy | Stract |
|---|---|---|---|
| GitHub stars | **6,169** | 4,084 | 2,373 |
| Language | Go | Java | Rust |
| License | AGPL-3.0 | GPL-family (SPDX not declared) | AGPL-3.0 |
| Last push | **2026-10-27** | 2026-09-23 | 2025-03-24 |
| Forks | 278 | **504** | 62 |
| Open issues | 60 | 245 | 43 |
| Index source | Pages you visit + local files | Peer-to-peer crawl / intranet crawl | You supply a web crawl |
| Official container | **Yes (GHCR)** | Yes (Docker Hub + GHCR) | No |
| Default port | 4433 | 8090 / 8443 | 8000 (dev server) |
| RAM footprint | ~100-200 MB | 1-2 GB | 2 GB+ |
| Query syntax | Simple + filters | YaCy-specific operators | `site:`, `intitle:`, bangs, optics |
| Share index with peers | No (by design) | **Yes** | No |
| Realistic use | Personal knowledge search | Intranet / P2P search | Engine development |

The column that matters most is "index source", not stars. A search engine is only as good as what it has crawled, and these three disagree fundamentally about where that corpus comes from.

![YaCy web search interface with result ranking controls](/img/screenshots/yacy-search.jpg "YaCy web search results page showing ranking configuration controls")

## Decision Matrix — Pick in 10 Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| "I read an article last month and can't find it" | **Hister** | Indexes full page text automatically via extension |
| You want to search PDFs and notes on a NAS | **Hister** | Local directory indexing is built in |
| You must search an internal wiki or file server | **YaCy** | Intranet crawl mode with no external dependency |
| You like the idea of a shared, non-corporate index | **YaCy** | P2P mode is the only mainstream implementation |
| You are building a search product or studying ranking | **Stract** | Clean Rust codebase, Tantivy-backed, optics ranking |
| You want a Google-substitute in a browser bar | **None of these** | Use a metasearch front end instead |
| You have a 1 GB VPS | **Hister** | YaCy will swap; Stract will not build comfortably |
| You need something maintained for the next 3 years | **Hister** | Daily commits vs a 19-month gap on Stract |

## Hister — Your Own Reading Index

Hister's premise is the most defensible of the three: the web you actually care about is the web you have already visited. Instead of crawling anything, it indexes page contents as you browse, plus whatever directories you point it at, and exposes the result through a web UI, a terminal UI, a CLI and an MCP endpoint.

The repository is AGPL-3.0, written in Go, at **6,169 stars** with a push on 2026-10-27. It ships a Compose file in the repo root, which is unusual for projects this young:

```yaml
services:
  hister:
    image: ghcr.io/asciimoo/hister:latest
    container_name: hister
    init: true
    restart: unless-stopped
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    ports:
      - '4433:4433'
    volumes:
      - hister_data:/hister/data
    tmpfs:
      - /tmp:noexec,nosuid,size=64m
    environment:
      HISTER__SERVER__ADDRESS: 0.0.0.0:4433
      HISTER__SERVER__BASE_URL: http://localhost:4433

volumes:
  hister_data:
```

Note the operational choices: read-only root filesystem, all capabilities dropped, no external database, single volume. That is a container you can leave running on a small VPS for years without thinking about it. The only thing to change is `HISTER__SERVER__BASE_URL` — set it to the URL you will actually open, or the browser extension will post to the wrong origin.

The workflow is: run the container, install the Firefox or Chrome extension, point the extension at your instance, and browse normally. Everything you read becomes searchable full text, not just titles and URLs. You can also import browser history, bookmarks, local directories and loose files, which is the fastest way to populate an empty index.

The honest limitation: Hister cannot answer a question about the web at large. It answers questions about **your** web. If that is what you want — and for most technical users it is — it is the right tool, and it is not close.

## YaCy — Peer-to-Peer Search That Still Works

YaCy has been the "decentralized search engine" since long before that phrase was fashionable. It runs a crawler, stores an inverted index locally, and can exchange index fragments with other peers over a P2P network. In intranet mode it quietly indexes internal HTTP servers without talking to anyone.

**4,084 stars**, written in Java, pushed 2026-09-23, 504 forks. The official images are on Docker Hub and GHCR, and the documented run command is a single line:

```bash
docker run -d --name yacy \
  -p 8090:8090 -p 8443:8443 \
  -v yacy_data:/opt/yacy_search_server/DATA \
  --log-opt max-size=200m --log-opt max-file=2 \
  yacy/yacy_search_server:latest
```

Or as Compose, matching the project's own Docker README:

```yaml
services:
  yacy:
    image: yacy/yacy_search_server:latest
    container_name: yacy
    ports:
      - "8090:8090"
      - "8443:8443"
    volumes:
      - yacy_data:/opt/yacy_search_server/DATA
    restart: unless-stopped
volumes:
  yacy_data:
```

Then open `http://your-host:8090`. The admin console is at `/Admin.html`, and every crawler setting lives there rather than in environment variables — a design choice from another era. Plan for **1-2 GB of RAM**, because the JVM heap and the index both live in the same process.

Two warnings from experience. First, P2P mode means your node serves index fragments to strangers and downloads theirs; on a metered VPS that is real bandwidth, and on a shared IP it can look like scraping traffic. Second, the default install is not hardened: set the admin password immediately and never expose port 8090 to the open internet without a reverse proxy and auth.

Where YaCy genuinely wins is intranet and archive search: point it at internal wikis, documentation servers, a legacy file portal, and it will index them with no external service involved. Nothing else in the self-hosted ecosystem does that as completely.

## Stract — A Real Search Engine, With a Real Caveat

Stract is the most technically interesting project here and the least deployable. It is a complete open-source search engine: its own crawler, an inverted index built on Tantivy, `site:` and `intitle:` syntax, DuckDuckGo-style bangs, tracker-based de-ranking, and a ranking-customization system it calls optics — you can write a file that reweights signals per query class.

**2,373 stars**, Rust, AGPL-3.0, 43 open issues, 62 forks. And a last push of **2025-03-24**. That is the whole story: an excellent design that has not received a commit in about 19 months.

There is no official Docker image and no Compose file. The README points at `CONTRIBUTING.md`, which is honest about the toolchain: native build dependencies, `just`, `wasm-pack`, a Python virtualenv created by the setup script, and a local sample index before the dev server will answer on port 8000.

```bash
# Debian-family prerequisites, from CONTRIBUTING.md
sudo apt install liburing-dev
cargo install just
cargo install wasm-pack

# Configure environment and build a small local index
just configure

# Start the search server + frontend on 0.0.0.0:8000
just dev
```

That gets a **development** instance with a toy index. Running it over a real crawl means operating a crawler fleet, storing WARC files, and building indexes — a multi-machine job, not a `docker compose up`.

**Verdict:** clone it, read it, learn from it, run the hosted instance for daily searching. Deploying Stract yourself in 2026 is a research project, not an infrastructure task.

![Stract search results page with sidebar and query controls](/img/screenshots/stract-search.jpg "Stract web search results showing sidebar and advanced query syntax")

## Pitfalls Before You Deploy Any of Them

**Do not confuse "search engine" with "metasearch proxy".** SearXNG, Whoogle and LibreX forward your query to upstream engines; they store nothing. Hister, YaCy and Stract build and own an index. If your goal is privacy from Google, a proxy solves it in ten minutes. If your goal is finding your own material, only an index helps.

**Set the base URL before you index anything.** Hister's extension posts to the origin configured in `HISTER__SERVER__BASE_URL`. Index for a week behind `http://localhost:4433`, then move to a domain, and you will spend an evening re-pointing clients.

**Treat the index as the asset, not the container.** For Hister that is the `hister_data` volume; for YaCy, `/opt/yacy_search_server/DATA`. A `docker compose down -v` destroys months of indexed content that cannot be re-downloaded, because the pages may no longer exist.

**Put auth in front of YaCy.** Its admin console can start crawls and change P2P settings. Either bind to a private interface or terminate TLS at a reverse proxy with authentication.

**Check the maintenance signal before you build workflows on top.** Hister pushes daily; YaCy pushes weekly; Stract has been quiet since March 2025. All three are useful, but only two are safe bets for a service you will run for years.

**Budget disk, not just RAM.** A personal Hister index of a few thousand pages is tens of megabytes. A YaCy crawl of a mid-size intranet is gigabytes. Full-text indexes compress worse than you expect.

## How This Fits With Full-Text Search Infrastructure

If your actual need is "search this corpus with an API", none of the three above is the right answer — you want a search library or server. Our [Sphinx vs Manticore vs Solr comparison](../2026-05-17-self-hosted-fulltext-search-sphinx-manticore-solr-guide/) covers that layer, and the [Meilisearch vs Typesense vs SearXNG breakdown](../meilisearch-vs-typesense-vs-searxng/) covers the lighter-weight end where a JSON API matters more than a crawler.

The practical stack many people end up with is two layers: Hister for personal recall, and Manticore or Meilisearch for application search. YaCy slots in only when the corpus is a live intranet, and Stract is a research reference rather than a runtime dependency.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hister vs YaCy vs Stract in 2026: Which Self-Hosted Search Engine Is Actually Worth Running?",
  "description": "Hister, YaCy and Stract solve three completely different problems. A 2026 hands-on comparison of self-hosted search: index ownership, Docker deployment, resource cost and maintenance risk.",
  "datePublished": "2026-10-28",
  "dateModified": "2026-10-28",
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

## FAQ

**Is Hister a replacement for Google?**

No. Hister indexes the pages you visit and the files you keep, so it answers "where did I read that" rather than "what exists on the internet". For general web search you still need a search provider or a metasearch front end such as SearXNG.

**Can YaCy really crawl the whole web?**

Technically it crawls and shares index fragments with peers, but a single node cannot compete with commercial crawlers. YaCy is realistic for intranets, documentation servers, small topical crawls, and as one participant in the P2P network — not as a Google substitute.

**Why is Stract's last commit so old?**

The repository shows a last push of 2025-03-24. The project is developed alongside the hosted service at stract.com, and the open-source engine has not seen commits for roughly 19 months. Treat the code as a reference implementation and use the hosted version for actual searching.

**Which one uses the least RAM?**

Hister, by a wide margin — roughly 100-200 MB for a container with a personal index. YaCy needs 1-2 GB because of the JVM heap and its local index. A Stract build is happiest with 2 GB or more once you add a real index and the crawler tooling.

**Do these engines need a GPU or special hardware?**

No. Hister is a static Go binary, YaCy runs on a standard JVM, and Stract compiles to native code with Rust. Any 2-core VPS handles the first two comfortably; Stract's cost is build time and index storage, not compute acceleration.

**Can I run Hister and YaCy on the same server?**

Yes, and it is a sensible pairing: Hister on port 4433 for personal recall, YaCy on 8090 for intranet crawling, with about 2 GB of RAM total. Put both behind one reverse proxy with TLS and separate auth, and keep the volumes on the same backup schedule.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
