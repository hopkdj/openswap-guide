---
title: "JPlag vs Dolos vs compare50: Self-Hosted Code Plagiarism Detection Guide 2026"
date: 2026-05-05
tags: ["comparison", "guide", "self-hosted", "education", "code-analysis", "plagiarism"]
draft: false
---

Academic integrity in programming courses is increasingly challenged by online code sharing, copilot suggestions, and peer collaboration that crosses into copying. Self-hosted code plagiarism detection tools help educators identify structural similarities in student submissions without sending source code to third-party services.

This guide compares three leading open-source plagiarism detection tools: **JPlag**, **Dolos**, and **compare50**.

## Quick Comparison

| Feature | JPlag | Dolos | compare50 |
|---------|-------|-------|-----------|
| GitHub Stars | 1,873 | 342 | 230 |
| Language | Java | TypeScript/JavaScript | Python/Rust |
| Languages Supported | 20+ (Java, C, C++, Python, Kotlin, Swift, etc.) | JavaScript, TypeScript, Python, Java, C, C++, R, Solidity | C, C++, Python, Java, Rust, Haskell, Scheme |
| Web UI | Yes (built-in) | Yes (built-in) | No (CLI only, results in HTML) |
| Installation | JAR file, Docker (community) | npm, Docker | Python pip |
| Algorithm | Greedy string tiling | Winnowing (k-gram fingerprinting) | Suffix tree comparison |
| Last Updated | May 2026 | May 2026 | January 2026 |
| License | BSD-3-Clause | MIT | MIT |

## JPlag: The Industry Standard

[JPlag](https://github.com/jplag/JPlag) is the most widely used open-source plagiarism detection tool, developed at Karlsruhe Institute of Technology. It supports over 20 programming languages and has been refined over 25+ years of academic use.

### Key Features

- **20+ language support** including Java, C/C++, Python, Kotlin, Swift, and more
- **Web UI** for visualizing comparison results
- **Greedy string tiling algorithm** — finds the longest common substrings between submissions
- **Batch processing** — compare hundreds of submissions at once
- **Extensible** — add new language parsers via the plugin API

### Docker Compose Setup

```yaml
services:
  jplag:
    image: ghcr.io/jplag/jplag:latest
    volumes:
      - ./submissions:/submissions:ro
      - ./results:/results
    command: >
      -l java
      -m 4
      -r /results
      /submissions
    restart: "no"

  jplag-viewer:
    image: ghcr.io/jplag/jplag-viewer:latest
    ports:
      - "8080:8080"
    volumes:
      - ./results:/results:ro
    restart: unless-stopped
```

### Running JPlag

```bash
# Compare Java submissions
java -jar jplag.jar -l java -m 4 -r results/ submissions/

# View results
open results/index.html
```

## Dolos: Modern Plagiarism Detection

[Dolos](https://github.com/dodona-edu/dolos) from Ghent University uses a modern **winnowing algorithm** for k-gram fingerprinting. It is designed to be faster and more accurate than traditional approaches, especially for JavaScript and TypeScript code.

### Key Features

- **Winnowing algorithm** — more robust against variable renaming and code reordering
- **Built-in web UI** with interactive similarity visualization
- **Language-agnostic core** — add new languages via tree-sitter parsers
- **Fast processing** — handles large submission sets efficiently
- **Export to PDF** for documentation

### Docker Compose Setup

```yaml
services:
  dolos:
    image: dodona/dolos:latest
    ports:
      - "3000:3000"
    volumes:
      - ./submissions:/submissions:ro
    command: >
      dolos run
      -l javascript
      -o /submissions
    restart: "no"
```

### Running Dolos

```bash
# Analyze JavaScript submissions
npx dolos run -l javascript submissions/*.js

# Launch the web viewer
npx dolos web
```

## compare50: CS50's Plagiarism Detector

[compare50](https://github.com/cs50/compare50) is Harvard CS50's plagiarism detection tool, built for speed and extensibility. It uses suffix tree comparison to find structural similarities.

### Key Features

- **Suffix tree algorithm** — efficient O(n) string comparison
- **Multi-language support** — C, C++, Python, Java, Rust, Haskell, Scheme
- **Fast processing** — designed for large CS course submissions
- **HTML reports** with color-coded similarity highlighting
- **Token-based comparison** — ignores whitespace and comments

### Installation and Usage

```bash
# Install via pip
pip install compare50

# Compare Python files
compare50 *.py

# View results (opens HTML in browser)
open compare50/index.html
```

## Algorithm Comparison

| Aspect | Greedy String Tiling (JPlag) | Winnowing (Dolos) | Suffix Tree (compare50) |
|--------|------------------------------|--------------------|------------------------|
| Speed | Medium | Fast | Fastest |
| Accuracy | High | Very High | High |
| Memory | High | Medium | Low |
| Rename resistance | Medium | High | Medium |
| Reorder resistance | Low | High | Low |

## When to Use Each Tool

**Choose JPlag** when you need broad language support and a mature, well-tested tool with a long academic track record. It is the safest choice for mixed-language courses.

**Choose Dolos** when your course focuses on JavaScript/TypeScript or when you want the most robust detection against code obfuscation techniques like variable renaming and statement reordering.

**Choose compare50** when you process large volumes of C/C++ or Python submissions and need the fastest possible analysis with minimal memory overhead.

## Related Guides

For code quality analysis, see our [SonarQube vs Semgrep vs CodeQL guide](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/). For code review workflows, check our [Gerrit vs Review Board vs Phorge comparison](../gerrit-vs-review-board-vs-phorge-self-hosted-code-review-guide/).

## FAQ

### Can these tools detect automatically generated code?
These tools detect structural similarity between submissions regardless of the source. If two students produce similar code through any means, these tools will flag the structural overlap. They do not analyze whether code was generated by a particular tool.

### Does JPlag support Python?
Yes, JPlag supports Python along with 20+ other languages including Java, C, C++, C#, Kotlin, Swift, Scheme, and more. Use `-l python` to specify the language.

### How does Dolos handle code obfuscation?
Dolos uses the winnowing algorithm which is specifically designed to be robust against common obfuscation techniques: variable renaming, comment changes, whitespace modifications, and statement reordering.

### Can I run these tools in CI/CD pipelines?
Yes. All three tools are CLI-based and can be integrated into CI/CD pipelines. JPlag and compare50 output machine-readable results (JSON/XML) that can be parsed for automated threshold checking.

### Is there a web-based dashboard for managing submissions?
JPlag includes a built-in web viewer. Dolos has an interactive web UI. compare50 generates static HTML reports — no running server needed for viewing results.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JPlag vs Dolos vs compare50: Self-Hosted Code Plagiarism Detection Guide 2026",
  "description": "Compare self-hosted code plagiarism detection tools: JPlag, Dolos, and compare50. Setup guides, algorithm comparison, and Docker configs included.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
