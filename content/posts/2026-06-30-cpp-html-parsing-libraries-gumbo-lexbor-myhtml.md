---
title: "C++ HTML Parsing Libraries: Gumbo vs Lexbor vs MyHTML — Choosing the Right HTML5 Parser"
date: "2026-06-30"
tags: ["html-parser", "c-plus-plus", "web-scraping", "html5", "lexbor", "gumbo-parser", "myhtml"]
draft: false
---

## Why HTML Parsing Matters in Native Code

When building web scrapers, security scanners, content extractors, or browser engines, you need a fast and reliable HTML parser. While Python developers reach for BeautifulSoup and JavaScript developers use cheerio, C and C++ developers have a different set of options — native libraries that parse HTML5 at the speed of compiled code.

This article compares three of the most popular open-source C/C++ HTML parsing libraries: **Google's Gumbo Parser**, **Lexbor**, and **MyHTML**. Each takes a different approach to the same problem, and the right choice depends on your performance requirements, API preferences, and maintenance expectations.

## Library Overview

| Feature | Gumbo Parser | Lexbor | MyHTML |
|---------|-------------|--------|--------|
| **GitHub Stars** | ~5,189 | ~2,028 | ~1,713 |
| **Language** | C99 | C | C |
| **Last Updated** | Jan 2026 | Jun 2026 | Jan 2025 |
| **HTML5 Spec** | Full | Full | Full |
| **Threading** | Single-threaded | Single-threaded | Multi-threaded |
| **DOM Output** | Parse tree | DOM tree + Render tree | DOM tree |
| **CSS Selectors** | Via third-party | Native | No |
| **Memory Model** | Arena allocator | Custom allocator | Custom allocator |
| **License** | Apache 2.0 | Apache 2.0 | LGPL 2.1 |

## Google Gumbo Parser: The Battle-Tested Standard

Gumbo is an HTML5 parsing library written in pure C99 by Google. It was designed to be a fully conformant HTML5 parser with no external dependencies — just drop the source files into your project and compile.

```c
#include "gumbo.h"

int main() {
    const char* html = "<html><body><h1>Hello World</h1></body></html>";
    GumboOutput* output = gumbo_parse(html);
    
    // Traverse the parse tree
    GumboNode* root = output->root;
    // ... process nodes ...
    
    gumbo_destroy_output(&kGumboDefaultOptions, output);
    return 0;
}
```

**Strengths:**
- **Zero dependencies** — pure C99, compiles everywhere from embedded systems to mainframes
- **Full HTML5 spec compliance** — passes all html5lib-tests
- **Arena-based allocation** — fast, predictable memory usage, excellent for batch processing
- **Simple, stable API** — hasn't changed significantly since release

**Weaknesses:**
- **No CSS selector support** — you must manually traverse the tree or use wrappers like `gumbo-query`
- **Slower update cadence** — last commit was January 2026 after years of minimal changes
- **No streaming API** — must parse the entire document before processing

Gumbo powers many popular projects including the Zircon kernel's documentation tools and several Python HTML parsing backends.

## Lexbor: The Full-Featured Modern Alternative

Lexbor takes a more ambitious approach — it's not just an HTML parser but a complete HTML rendering engine in development. It parses HTML5 into a DOM tree and provides CSS selector matching natively.

```c
#include <lexbor/html/parser.h>
#include <lexbor/dom/interfaces/element.h>

int main() {
    lxb_status_t status;
    lxb_html_document_t *document;
    
    document = lxb_html_document_create();
    
    const char html[] = "<div class='content'><p>Hello Lexbor</p></div>";
    status = lxb_html_document_parse(document, (const lxb_char_t *)html, strlen(html));
    
    // Use CSS selectors natively
    lxb_dom_collection_t *collection;
    collection = lxb_dom_collection_make(&document->dom_document, 16);
    
    lxb_dom_element_t *body = lxb_dom_interface_element(
        lxb_html_document_body_element(document));
    
    // Find elements by CSS selector
    lxb_dom_elements_by_attr_name(
        lxb_dom_interface_node(body), collection,
        (const lxb_char_t *)"class", 5);
    
    lxb_html_document_destroy(document);
    return 0;
}
```

**Strengths:**
- **Native CSS selectors** — query elements without third-party libraries
- **Actively maintained** — latest commit June 2026, vibrant development community
- **Modular architecture** — separate modules for HTML, CSS, URL, encoding
- **Full DOM tree** — supports mutation, insertion, and node manipulation after parsing

**Weaknesses:**
- **Larger codebase** — more complex build system with autotools/cmake
- **Heavier memory footprint** — full DOM with live collections uses more RAM than Gumbo's arena model
- **Less battle-tested** — newer project with smaller deployment base than Gumbo

Lexbor is the best choice when you need CSS selectors without external dependencies and value active development.

## MyHTML: The Multi-Threaded Speed Demon

MyHTML comes from the same developer as Lexbor (Alexander Borisov) but takes a fundamentally different approach. It is designed from the ground up for **threaded parsing** — you can parse multiple HTML documents in parallel using worker threads.

```c
#include <myhtml/api.h>

int main() {
    myhtml_t* myhtml = myhtml_create();
    myhtml_init(myhtml, MyHTML_OPTIONS_PARSE_MODE_SINGLE, 1, 0);
    
    myhtml_tree_t* tree = myhtml_tree_create();
    myhtml_tree_init(tree, myhtml);
    
    const char* html = "<html><head><title>Test</title></head>"
                       "<body><p>Paragraph</p></body></html>";
    
    myhtml_parse(tree, MyENCODING_UTF_8, html, strlen(html));
    
    // Traverse the tree
    myhtml_tree_node_t* root = myhtml_tree_get_document(tree);
    // ... walk nodes ...
    
    myhtml_tree_destroy(tree);
    myhtml_destroy(myhtml);
    return 0;
}
```

**Strengths:**
- **Multi-threaded parsing** — designed for high-throughput scenarios where you need to parse hundreds of documents simultaneously
- **Streaming/chunked parsing** — can parse HTML as it arrives over the network
- **Proven in production** — MyHTML and Lexbor share architectural insights
- **Compact API surface** — smaller and simpler than Lexbor

**Weaknesses:**
- **Slower maintenance** — last update January 2025, effectively in maintenance mode
- **No CSS selectors** — must traverse the DOM tree manually
- **LGPL license** — more restrictive than Apache 2.0 for commercial embedding
- **Documentation gaps** — less comprehensive than Gumbo's docs

## Setting Up Docker Environments for HTML Processing

For projects that need to run HTML parsing in containerized microservices, here is a Docker Compose setup for a C++ HTML processing service:

```yaml
version: '3.8'

services:
  html-parser:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - PARSER_BACKEND=gumbo
      - MAX_DOCUMENT_SIZE=10485760
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  redis-cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

```dockerfile
FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y \
    build-essential cmake git pkg-config

# Build Gumbo
RUN git clone https://github.com/google/gumbo-parser.git /opt/gumbo \
    && cd /opt/gumbo && ./autogen.sh && ./configure && make -j$(nproc) && make install

# Build Lexbor
RUN git clone https://github.com/lexbor/lexbor.git /opt/lexbor \
    && cd /opt/lexbor && cmake . -B build && cmake --build build -j$(nproc) \
    && cmake --install build

FROM ubuntu:24.04
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/include /usr/local/include
COPY ./html-service /app/html-service
RUN ldconfig
CMD ["/app/html-service"]
```

## Performance Considerations

For most use cases, raw parsing speed differs by less than 15% between the three libraries. The real performance differentiators are:

- **Memory allocation strategy**: Gumbo's arena allocator excels at batch processing (parse 10,000 small documents, free them all at once). Lexbor's custom allocator is better for long-running server processes where documents live for different durations.
- **Threading model**: If you process documents in a worker pool, MyHTML's thread-safe design eliminates mutex contention. With Gumbo or Lexbor, you would create one parser instance per thread.
- **Streaming vs batch**: MyHTML supports incremental/chunked parsing, making it the best choice for streaming HTML over network connections where latency matters.

## Why Self-Host Your HTML Processing Pipeline?

Running your own HTML processing infrastructure gives you complete control over data privacy and processing logic. For web scraping at scale, a self-hosted setup avoids the rate limits, IP blocks, and data-sharing risks of third-party scraping APIs. You can also customize the parsing pipeline to extract exactly the data structures your application needs.

For web scraping frameworks, see our [web scraping tools guide](../self-hosted-web-scraping-crawlee-scrapy-playwright-guide-2026/). If you need to parse structured data formats beyond HTML, check our [XML parsing libraries comparison](../2026-06-20-self-hosted-xml-parsing-libraries-lxml-pugixml-xerces-rapidxml/). For URL handling before fetching pages, our [URL parsing libraries guide](../2026-06-21-url-parsing-libraries-ada-uriparser-llhttp-rust-url/) covers the full pipeline.

## FAQ

### Which parser should I choose for a new project in 2026?

For new projects, **Lexbor** offers the best balance of modern features (native CSS selectors, modular design, active maintenance) and performance. Choose **Gumbo** if you need zero-dependency portability or are working in resource-constrained environments. Choose **MyHTML** only if you specifically need multi-threaded or streaming parsing at scale.

### Can I use these libraries from Python or other languages?

Yes. Gumbo has excellent bindings for Python (`gumbo` on PyPI), Ruby, Rust, and Go. Lexbor has Python bindings under active development. MyHTML has Python bindings via `myhtml-py`. For production Python projects, the Gumbo Python bindings are the most mature.

### How do these compare to libxml2's HTML parser?

libxml2's HTML parser (`htmlParser` module) is older and less HTML5-compliant than these three. It handles malformed HTML reasonably well but does not follow the full HTML5 tree construction algorithm. For modern web content with complex HTML5 features (custom elements, templates, Shadow DOM hints), use a dedicated HTML5 parser like Gumbo or Lexbor.

### Are these parsers safe against malicious HTML input?

All three parsers are designed to handle malformed HTML gracefully — that is part of the HTML5 specification. However, they do not include built-in XSS filtering or sanitization. For security applications, pair the parser with a separate sanitizer that strips dangerous elements and attributes. The parser's job is to build a correct tree; sanitization is a separate concern.

### What about performance with very large documents?

For documents over 10MB, Gumbo's arena allocator can cause memory fragmentation if you parse many large documents without freeing. Lexbor's incremental memory management handles large documents more gracefully. MyHTML's streaming mode is ideal for documents where you only need the first N elements and can discard the rest.

### Can these parsers handle non-English content and encodings?

All three support the full HTML5 encoding detection algorithm, including auto-detection of UTF-8, UTF-16, Latin-1, Shift-JIS, GBK, and other common encodings. They also handle bidirectional text, RTL languages, and Unicode normalization correctly as specified by HTML5.

---

**💰 Want to test your market prediction skills? I use [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform. From election outcomes to technology regulation timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've made solid returns predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ HTML Parsing Libraries: Gumbo vs Lexbor vs MyHTML — Choosing the Right HTML5 Parser",
  "description": "Comprehensive comparison of three leading open-source C/C++ HTML5 parsing libraries: Google Gumbo Parser, Lexbor, and MyHTML. Includes Docker Compose setup, performance analysis, and integration guidance.",
  "datePublished": "2026-06-30",
  "dateModified": "2026-06-30",
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
