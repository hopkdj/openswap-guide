---
title: "Self-Hosted Code Duplication Detection: jscpd vs PMD CPD vs Duplo"
date: "2026-06-15"
tags: ["code-quality", "static-analysis", "devops", "ci-cd", "code-review", "refactoring"]
draft: false
---

## Introduction

Duplicate code is one of the most persistent problems in software development. Studies show that 5-23% of code in typical codebases is duplicated — copy-pasted logic that increases maintenance burden, introduces inconsistent bug fixes, and bloats repository sizes. When the same logic exists in multiple places, fixing a bug once leaves the duplicates still broken.

Detecting duplicate code automatically in your CI/CD pipeline is a critical part of maintaining a healthy codebase. Unlike linters that catch syntax issues or formatters that enforce style, duplication detectors find semantic redundancy — logic that was copied rather than abstracted.

This guide compares three leading open-source code duplication detection tools — **jscpd**, **PMD CPD**, and **Duplo** — covering their detection strategies, language support, performance characteristics, and how to integrate them into your development workflow.

## Comparison: jscpd vs PMD CPD vs Duplo

| Feature | jscpd | PMD CPD | Duplo |
|---------|-------|---------|-------|
| **Language** | TypeScript | Java | C++ |
| **GitHub Stars** | 5,774 | 5,424 | 125 |
| **Detection Method** | Rabin-Karp fingerprinting | Token-based (Karp-Rabin) | Text-line hashing |
| **Languages Supported** | 150+ (all text files) | 30+ (Java, JS, Python, etc.) | C, C++, Java, C#, TypeScript |
| **Output Formats** | JSON, XML, HTML, CSV | XML, CSV, text, HTML | Text, XML |
| **Minimum Token Threshold** | Configurable (default 30) | Configurable (default 100) | Configurable (default 30 lines) |
| **Near-Miss Detection** | Yes (Mode + Rabin-Karp) | Limited (exact token match) | Yes (fuzzy matching) |
| **CI Integration** | Native reporters | Ant/Maven/Gradle plugins | CLI-based |
| **Last Update** | June 2026 | June 2026 | June 2026 |
| **License** | MIT | BSD/Apache | MIT |

## How Code Duplication Detection Works

### jscpd: The Universal Detector

jscpd (JavaScript Copy/Paste Detector) is written in TypeScript but detects duplicates across 150+ file formats. It uses the Rabin-Karp string matching algorithm with a rolling hash to find identical or near-identical code blocks efficiently. Unlike token-based approaches, jscpd can detect duplicates across files with different formatting or variable names.

jscpd supports multiple detection modes:
- **Strict mode**: Exact character-level matching
- **Mild mode**: Ignores whitespace and comments
- **Weak mode**: Normalizes identifiers before comparison

**Installation and usage:**

```bash
# Install globally via npm
npm install -g jscpd

# Run detection on your project
jscpd /path/to/your/project --min-tokens 50 --min-lines 5

# Generate HTML report
jscpd /path/to/project --reporters html --output ./reports

# Run in CI with JSON output
jscpd ./src --reporter json --output jscpd-report.json
```

**Docker-based usage:**

```bash
# Run jscpd via Docker
docker run -v $(pwd):/code -w /code node:20-alpine sh -c \
  "npm install -g jscpd && jscpd /code --min-tokens 50"
```

### PMD CPD: The Battle-Tested Analyzer

PMD's Copy/Paste Detector (CPD) has been analyzing Java code for over two decades. It tokenizes source code and uses the same Karp-Rabin fingerprinting algorithm to find matching token sequences. CPD is language-aware — it parses files according to their language grammar, ignoring comments and string literals, which reduces false positives.

CPD integrates deeply with Java build tools but also works as a standalone CLI for other languages.

**Installation and usage:**

```bash
# Download PMD distribution
wget https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.9.0/pmd-dist-7.9.0-bin.zip
unzip pmd-dist-7.9.0-bin.zip

# Run CPD on Java code
./pmd-bin-7.9.0/bin/run.sh cpd \
  --minimum-tokens 100 \
  --files /path/to/project \
  --language java \
  --format xml

# Run CPD on multiple languages
./pmd-bin-7.9.0/bin/run.sh cpd \
  --minimum-tokens 75 \
  --files /path/to/project \
  --format xml > cpd-report.xml
```

**Maven integration:**

```xml
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-pmd-plugin</artifactId>
  <version>3.24.0</version>
  <configuration>
    <minimumTokens>100</minimumTokens>
    <skipEmptyFiles>true</skipEmptyFiles>
    <failOnViolation>false</failOnViolation>
  </configuration>
</plugin>
```

### Duplo: The Lightweight Specialist

Duplo takes a different approach — it compares source lines as text hashes rather than tokenizing them. This simple strategy makes it extremely fast but less sophisticated at detecting near-miss duplicates where variable names differ. Duplo is written in C++ and designed for speed on large C/C++ codebases.

Despite its simplicity, Duplo is surprisingly effective for detecting straightforward copy-paste in languages like C, C++, and Java where formatting tends to be consistent.

**Installation and usage:**

```bash
# Build from source
git clone https://github.com/dlidstrom/Duplo.git
cd Duplo
make

# Run on a project
./duplo /path/to/project/src/*.cpp

# Set minimum block size
./duplo -min-block 4 /path/to/project/**/*.java

# XML output for CI integration
./duplo -xml /path/to/project/*.cpp > duplo-report.xml
```

## Integration with CI/CD Pipelines

All three tools can be integrated into CI/CD pipelines to fail builds when excessive duplication is detected.

**GitHub Actions example (jscpd):**

```yaml
name: Code Duplication Check
on: [push, pull_request]
jobs:
  jscpd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check for code duplication
        run: |
          npm install -g jscpd
          jscpd ./src --min-tokens 50 --reporters consoleFull
```

**GitLab CI example (PMD CPD):**

```yaml
pmd-cpd:
  image: openjdk:21-slim
  script:
    - wget -q https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.9.0/pmd-dist-7.9.0-bin.zip
    - unzip -q pmd-dist-7.9.0-bin.zip
    - ./pmd-bin-7.9.0/bin/run.sh cpd --minimum-tokens 100 --files src/ --language java
```

## Choosing the Right Duplication Detector

The choice between these tools depends on your tech stack and detection needs:

- **jscpd** is the best choice for multi-language projects with diverse file types. Its 150+ format support, multiple detection modes, and modern output formats make it the most versatile option. Choose jscpd when you need broad compatibility and don't want to configure language-specific parsers.

- **PMD CPD** excels in JVM ecosystems (Java, Kotlin, Groovy) where its language-aware tokenization produces the fewest false positives. It's also the best choice if you're already using PMD for static analysis, since CPD shares the same distribution and Maven/Gradle integration.

- **Duplo** is ideal for large C/C++ codebases where speed matters more than near-miss detection. Its text-hash approach runs orders of magnitude faster than tokenizers on multi-million-line projects.

For maximum coverage, run **both** jscpd and CPD in your CI pipeline — jscpd catches cross-language duplicates and near-misses, while CPD provides language-aware precision for your primary language.

## Why Self-Host Your Code Quality Pipeline?

Running code duplication detection in your own infrastructure gives you complete control over your quality pipeline. Unlike cloud services that charge per-seat or per-scan, self-hosted tools cost nothing beyond the compute resources you already have in your CI/CD environment. Your source code never leaves your infrastructure — a critical consideration for proprietary codebases and compliance-regulated industries.

Self-hosting also means you can customize detection thresholds, integrate with your existing build tools, and maintain historical duplication trend data without monthly subscription fees. As your team grows from 5 to 50 engineers, your duplication detection costs stay flat — no per-seat licensing surprises.

For teams already running Jenkins, GitLab CI, or GitHub Actions, adding these tools is a matter of a few lines of configuration. See our [comprehensive CI/CD pipeline guide](../2026-04-22-buildbot-vs-gocd-vs-concourse-self-hosted-cicd-pipeline-guide/) for setting up robust build infrastructure.

Beyond duplication detection, maintaining code quality requires a multi-layered approach. Our [self-hosted linting guide](../2026-04-23-megalinter-vs-super-linter-vs-reviewdog-self-hosted-linting-guide-2026/) covers how to combine linters with duplication detection for comprehensive quality enforcement. For broader DevOps visibility, our [CI/CD dashboard comparison](../2026-05-05-gocd-vs-buildbot-vs-jenkins-self-hosted-cicd-dashboard-guide/) helps you track build health across projects.

## FAQ

### How is code duplication detection different from static analysis?

Static analysis tools (linters, SAST scanners) look for patterns that violate rules — unused variables, security vulnerabilities, coding style violations. Code duplication detection specifically looks for repeated code blocks. The two are complementary: linters catch rule violations in single files, while duplication detectors find redundancy across files. Running both gives you comprehensive code quality coverage.

### What minimum token threshold should I use?

For jscpd, start with 30 tokens. For CPD, 100 tokens is the standard default. For Duplo, 4 lines is a good starting point. Lower thresholds catch more duplicates but produce more false positives. For a first-time scan, use the defaults, review the results, and adjust based on what you consider a meaningful duplication in your codebase.

### Can these tools detect near-miss duplicates (similar but not identical code)?

jscpd offers the best near-miss detection through its Rabin-Karp mode and configurable hash detail levels. It can detect code that differs in whitespace, variable naming, and formatting. PMD CPD performs exact token matching, so it won't catch code where variable names differ. Duplo's text-hash approach can catch some near-misses depending on block size configuration.

### How do I handle generated code in duplication reports?

All three tools can exclude directories and file patterns. For jscpd, use `--ignore "**/generated/**"`. For CPD, use `--exclude "**/target/**"`. For Duplo, simply don't include generated directories in the file list. Configure exclusions for build output directories, generated protobuf/GraphQL types, and vendored dependencies.

### What's the performance impact on large codebases?

jscpd processes about 10,000 lines per second on modern hardware. CPD is roughly 2-3x slower due to language-aware tokenization. Duplo is the fastest, processing 50,000+ lines per second. For a 1-million-line codebase, expect jscpd to complete in ~2 minutes, CPD in ~5 minutes, and Duplo in ~30 seconds.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Code Duplication Detection: jscpd vs PMD CPD vs Duplo",
  "description": "Compare three open-source code duplication detection tools — jscpd, PMD CPD, and Duplo — for finding copy-pasted code in your CI/CD pipeline. Features comparison table, installation guides, and CI integration examples.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
