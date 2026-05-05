---
title: "Self-Hosted Diagram-as-Code Tools: D2 vs Structurizr vs Python Diagrams"
date: 2026-05-07
tags: ["diagrams", "documentation", "devtools", "architecture", "c4-model"]
draft: false
---

Documentation that stays current is documentation that lives in code. Diagram-as-code tools let you define architecture diagrams, system designs, and flowcharts using plain text — version-controlled alongside your source code, reviewable in pull requests, and rendered automatically in CI/CD pipelines.

This guide compares three leading open-source diagram-as-code frameworks: **D2** (Declarative Diagramming), **Structurizr** (C4 model implementation), and **Python Diagrams** (cloud architecture prototyping). Each targets a different use case, from general-purpose diagrams to formal architecture modeling.

## Comparison at a Glance

| Feature | D2 | Structurizr | Python Diagrams |
|---------|----|-------------|-----------------|
| **Language** | Custom DSL (D2 markup) | Java DSL, Kotlin DSL, CLI (JSON/workspace) | Python API |
| **Diagram Types** | Flowcharts, sequence, class, state, ERD, architecture | C4 model (context, container, component, code) | Cloud architecture diagrams |
| **Output Formats** | SVG, PNG, PDF, HTML | PNG, SVG, PlantUML, Mermaid, JSON | PNG, SVG |
| **Cloud Provider Icons** | Generic icons | Generic + custom icons | AWS, GCP, Azure, Alibaba, OCI, DigitalOcean |
| **C4 Model Support** | Manual (no built-in enforcement) | Native (C4 model is the core design) | No |
| **Self-Hosting** | CLI binary, Docker, Go library | Java JAR, Docker, web app | Python package (pip) |
| **Live Preview** | d2lang.com playground, VS Code extension | Structurizr Lite (local web server) | None (script execution) |
| **GitHub Stars** | 23,600+ | 560+ (CLI), larger for Java DSL | 42,200+ |
| **License** | Elastic 2.0 | MIT | MIT |
| **Best For** | General-purpose diagramming | Formal software architecture | Cloud infrastructure documentation |

## D2: Modern Declarative Diagramming

[D2](https://github.com/terrastruct/d2) by Terrastruct is a modern diagram scripting language designed to be both human-readable and powerful. It supports flowcharts, sequence diagrams, entity-relationship diagrams, state machines, and class diagrams — all from a single DSL.

### How It Works

D2 uses a clean, intuitive syntax that resembles markdown for diagrams. You define objects, connections, and layouts in plain text, and D2 renders them into beautiful SVG or PNG output.

```d2
# Simple architecture diagram in D2
architecture: {
  client: {
    shape: person
    style: {
      font-size: 14
    }
  }

  api: {
    shape: rectangle
    label: "API Gateway"
    style: {
      fill: "#e1f5fe"
      stroke: "#0288d1"
    }
  }

  db: {
    shape: cylinder
    label: "PostgreSQL"
    style: {
      fill: "#e8f5e9"
    }
  }

  client -> api: HTTPS
  api -> db: "SQL queries"
}
```

### Docker-Based Rendering Pipeline

```yaml
version: '3.8'

services:
  d2-renderer:
    image: ghcr.io/terrastruct/d2:latest
    volumes:
      - ./diagrams:/diagrams
      - ./output:/output
    working_dir: /diagrams
    command: >
      sh -c "
        for f in *.d2; do
          d2 $f /output/${f%.d2}.svg
        done
      "
```

### CI/CD Integration

```yaml
# GitHub Actions for D2 diagram rendering
name: Render D2 Diagrams
on:
  push:
    paths: ['diagrams/**/*.d2']

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup D2
        run: |
          curl -fsSL https://d2lang.com/install.sh | sh -s --
      - name: Render diagrams
        run: |
          mkdir -p output
          for f in diagrams/*.d2; do
            d2 $f output/$(basename $f).svg
          done
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "auto: update rendered diagrams"
          file_pattern: 'output/*.svg'
```

### Key Strengths

- **Clean syntax**: Easier to read and write than PlantUML or Graphviz
- **Layout engine**: Multiple layout options (DAGRE, ELK, TALA) for different visual styles
- **Rich icon library**: Built-in icons for cloud services, databases, and common architecture patterns
- **Theme support**: Built-in themes (neutral, flagship terra, origami) for consistent branding

### Limitations

- Elastic License 2.0 — not OSI-approved open source (free for most uses, but restrictions on competing with D2)
- No built-in C4 model enforcement
- Younger ecosystem than PlantUML or Mermaid

## Structurizr: Formal Software Architecture with the C4 Model

[Structurizr](https://structurizr.com) implements the C4 model for software architecture, created by Simon Brown. It provides formal semantics for describing software systems at four levels of abstraction: Context, Container, Component, and Code.

### How It Works

Structurizr uses a workspace model where you define software systems, containers, components, and their relationships using a DSL (or JSON). The CLI renders these definitions into C4-compliant diagrams.

```dsl
// Structurizr DSL - C4 Context Diagram
workspace {
  model {
    user = person "User" "A user of the system"
    softwareSystem = softwareSystem "Web Application" "A web application"
    
    user -> softwareSystem "Uses"
  }
  
  views {
    systemContext softwareSystem {
      include *
      autoLayout
    }
    styles {
      element "Person" {
        background "#08427b"
        color "#ffffff"
      }
    }
  }
}
```

### Structurizr Lite (Self-Hosted)

Structurizr Lite is a self-hosted, read-only viewer for Structurizr workspaces:

```yaml
version: '3.8'

services:
  structurizr:
    image: structurizr/lite:latest
    ports:
      - "8080:8080"
    volumes:
      - ./workspace:/usr/local/structurizr
    environment:
      - STRUCTURIZR_URL=http://localhost:8080
```

The workspace directory should contain a `workspace.dsl` or `workspace.json` file. Navigate to `http://localhost:8080` to view your diagrams.

### Key Strengths

- **C4 model enforcement**: Built-in semantics ensure consistent architecture documentation
- **Multiple views**: Same model generates context, container, and component diagrams
- **Integration exports**: Export to PlantUML, Mermaid, WebSequenceDiagrams, and more
- **Team collaboration**: Define architecture once, generate many views

### Limitations

- DSL learning curve (though JSON alternative exists)
- Structurizr Lite is read-only — editing requires the commercial SaaS or Structurizr CLI
- Smaller community compared to general-purpose diagram tools

## Python Diagrams: Cloud Architecture Prototyping

[Python Diagrams](https://github.com/mingrammer/diagrams) lets you draw cloud system architecture diagrams in pure Python. It supports major cloud providers (AWS, GCP, Azure) with accurate icons and automatic layout.

### How It Works

You write Python scripts that import node types from the diagrams library and connect them using Python operators. The result is a rendered PNG or SVG diagram.

```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.database import RDS, DynamoDB
from diagrams.aws.network import ELB, Route53
from diagrams.onprem.client import Users

with Diagram("Web Application Architecture", filename="webapp", direction="LR"):
    dns = Route53("DNS")
    lb = ELB("Load Balancer")
    
    with Cluster("Web Tier"):
        web_servers = [EC2("Web Server 1"), EC2("Web Server 2")]
    
    with Cluster("Data Tier"):
        primary_db = RDS("Primary")
        read_replica = RDS("Replica")
    
    Users >> dns >> lb >> web_servers >> primary_db
    primary_db >> read_replica
```

### Docker-Based Rendering

```yaml
version: '3.8'

services:
  diagrams:
    image: python:3.11-slim
    volumes:
      - ./diagrams:/diagrams
      - ./output:/output
    working_dir: /diagrams
    command: >
      sh -c "
        pip install diagrams &&
        python render_all.py
      "
```

```python
# render_all.py - batch render all diagram scripts
import os, subprocess

os.makedirs("/output", exist_ok=True)
for f in os.listdir("."):
    if f.endswith(".py") and f != "render_all.py":
        subprocess.run(["python", f], check=True)
        # Move output files
        base = f.replace(".py", "")
        for ext in [".png", ".svg"]:
            src = f"{base}{ext}"
            if os.path.exists(src):
                os.rename(src, f"/output/{src}")
```

### Key Strengths

- **Python-native**: Leverage Python full ecosystem (loops, functions, imports)
- **Rich cloud icons**: Accurate, up-to-date icons for AWS, GCP, Azure, and more
- **Programmatic generation**: Generate diagrams dynamically from inventory data
- **Simple API**: Clean, intuitive syntax — draw diagrams like writing code

### Limitations

- Python-only — no DSL or markup language
- No built-in web preview (requires running the script)
- Diagram customization is limited compared to D2 or PlantUML
- No standard output format beyond PNG/SVG

## Choosing the Right Tool

| Use Case | Recommended Tool |
|----------|-----------------|
| General-purpose diagrams (flowcharts, ERD, sequence) | **D2** |
| Formal software architecture documentation | **Structurizr** |
| Cloud infrastructure diagrams | **Python Diagrams** |
| C4 model compliance | **Structurizr** |
| CI/CD diagram generation | **D2** or **Python Diagrams** |
| Multi-cloud architecture docs | **Python Diagrams** |
| Architecture review documentation | **Structurizr** |

For broader diagram generation (including PlantUML and Mermaid), see our [text-to-diagram platforms guide](../self-hosted-text-to-diagram-platforms-kroki-plantuml-mermaid-guide-2026/). For API documentation, check our [API documentation tools comparison](../2026-04-25-self-hosted-api-documentation-scalar-redoc-rapiddoc-openapi-guide/).

## Why Self-Host Diagram Generation?

Self-hosted diagram-as-code tools keep your architecture documentation private and version-controlled. Unlike SaaS diagram tools, they:
- Integrate directly into your CI/CD pipeline for automatic diagram updates
- Work offline — no internet connection required
- Avoid vendor lock-in — diagrams are plain text, stored in your git repository
- Support code review — diagram changes appear as diffs in pull requests

## FAQ

### Is D2 truly open source?

D2 uses the Elastic License 2.0, which allows free use, modification, and distribution for most purposes. However, it prohibits creating a competing D2 service. For most personal and commercial uses, this is effectively free. If you need a strictly OSI-approved license, consider PlantUML, Mermaid, or Python Diagrams.

### What is the C4 model and why does it matter?

The C4 model is a hierarchical approach to software architecture documentation with four levels: Context (system and external dependencies), Container (deployable units), Component (modules within containers), and Code (classes/functions). Structurizr enforces this model, ensuring architecture docs are consistent and comprehensive.

### Can I convert D2 diagrams to Mermaid or PlantUML?

D2 does not natively export to Mermaid or PlantUML formats. However, you can render D2 diagrams as SVG and embed them in Mermaid-compatible documentation. For direct format conversion, tools like Kroki support multiple diagram languages through a unified API.

### How do I version-control diagram changes?

Since diagram-as-code tools store diagrams as plain text (DSL files, Python scripts, or JSON), they work natively with git. Every diagram change produces a clean diff in pull requests, making architecture evolution trackable over time.

### Can Python Diagrams generate interactive diagrams?

Python Diagrams generates static PNG/SVG output only. For interactive diagrams, consider using D2 HTML output or Structurizr web viewer, which support clickable elements and drill-down navigation between architecture levels.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Diagram-as-Code Tools: D2 vs Structurizr vs Python Diagrams",
  "description": "Compare three open-source diagram-as-code tools — D2 for general-purpose diagramming, Structurizr for C4 model architecture, and Python Diagrams for cloud infrastructure documentation.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
