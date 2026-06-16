---
title: "Self-Hosted Infrastructure Diagram as Code: Diagrams vs Inframap vs Terraform Graph"
date: "2026-06-16"
tags: ["infrastructure", "diagram", "devops", "terraform", "cloud", "visualization", "documentation"]
draft: false
---

## Why Diagram Your Infrastructure as Code?

Cloud infrastructure has become increasingly complex. A typical production environment spans multiple services, regions, and providers — and keeping track of how all the pieces connect is a challenge that whiteboard diagrams and static documentation can't solve.

Infrastructure Diagram as Code (DaC) tools solve this by generating architecture diagrams directly from your actual infrastructure definitions. Instead of manually drawing boxes and arrows in a diagramming tool — and inevitably letting them go stale — DaC tools read your Terraform state files, HCL configurations, or cloud provider APIs and produce accurate, up-to-date visualizations automatically.

In this guide, we compare three leading open-source approaches to infrastructure diagramming: **Python Diagrams** (for authoring diagrams from scratch), **Inframap** (for visualizing existing Terraform state), and **Terraform Graph** plus visualization tools (for dependency analysis). Each serves a different purpose in the infrastructure documentation lifecycle.

## Comparison Table

| Feature | Python Diagrams | Inframap | Terraform Graph + Blast Radius |
|---------|----------------|----------|-------------------------------|
| **Primary Use Case** | Author architecture diagrams | Visualize Terraform state | Analyze Terraform dependencies |
| **Stars** | 42,357 | 2,036 | Varies (built-in + community) |
| **Language** | Python | Go | Go (built into Terraform) |
| **Input Source** | Python code (DSL) | Terraform state/HCL | Terraform state/HCL |
| **Output Format** | PNG, JPG, SVG, PDF | Graphviz DOT, PNG | Graphviz DOT, interactive HTML |
| **Auto-Update** | Manual (re-run script) | Yes (re-read state) | Yes (re-read state) |
| **Cloud Providers** | AWS, Azure, GCP, K8s, etc. | AWS, Azure, GCP, OCI | All Terraform providers |
| **Custom Nodes** | Yes (extensible) | Limited | Limited |
| **CI/CD Integration** | Easy (Python script) | CLI-based | CLI-based |
| **Learning Curve** | Low (Python) | Very Low (single command) | Low-Medium |

## Tool Deep Dive

### Python Diagrams: Code-First Architecture Design

Diagrams (42,357 stars) by MinJae Kwon is the most popular infrastructure diagram tool on GitHub — and for good reason. It lets you describe your cloud architecture using clean, readable Python code and generates professional-quality diagrams automatically.

```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.database import RDS, ElastiCache
from diagrams.aws.network import ELB, Route53
from diagrams.aws.storage import S3

with Diagram("Web Service Architecture", show=False):
    dns = Route53("dns")
    lb = ELB("load balancer")
    
    with Cluster("App Tier"):
        app = [EC2("web1"), EC2("web2"), EC2("web3")]
    
    with Cluster("Data Tier"):
        db = RDS("user db")
        cache = ElastiCache("redis cache")
    
    storage = S3("assets")
    
    dns >> lb >> app
    app >> db
    app >> cache
    app >> storage
```

Diagrams supports all major cloud providers (AWS, Azure, GCP, Alibaba Cloud, Oracle Cloud), Kubernetes, and on-premise components. It's ideal for designing new architectures, creating proposals, and documenting systems where the actual infrastructure doesn't yet exist.

### Inframap: Reverse-Engineering Your Live Infrastructure

Inframap (2,036 stars) by Cycloid takes the opposite approach — instead of authoring diagrams by hand, it reads your existing Terraform state files or HCL configurations and generates a visual map automatically.

```bash
# Install Inframap
wget https://github.com/cycloidio/inframap/releases/latest/download/inframap-linux-amd64.tar.gz
tar xzf inframap-linux-amd64.tar.gz
sudo mv inframap /usr/local/bin/

# Generate a diagram from Terraform state
inframap generate --tfstate terraform.tfstate

# Or directly from HCL files
inframap generate ./terraform/

# Output as PNG
inframap generate --tfstate terraform.tfstate | dot -Tpng > architecture.png
```

Inframap excels in environments where the Terraform code is the source of truth but no diagram was ever drawn. It's particularly useful for onboarding new team members, performing architecture reviews, and documenting legacy infrastructure that was built before DaC practices were adopted.

### Terraform Graph & Blast Radius: Dependency Analysis

Terraform itself ships with a built-in `terraform graph` command that outputs resource dependencies in Graphviz DOT format. While basic, it forms the foundation for several visualization tools:

```bash
# Generate a dependency graph
terraform graph | dot -Tpng > dependencies.png

# Use Blast Radius for interactive visualization
pip install blast-radius
blast-radius --serve ./
# Opens http://localhost:5000 with interactive resource graph
```

Blast Radius adds an interactive web interface on top of `terraform graph`, allowing you to hover over resources, see their attributes, and filter by resource type. It's particularly useful for understanding complex resource dependencies and identifying potential circular dependencies before applying changes.

## Deployment & Automation

All three tools can be integrated into your CI/CD pipeline to generate up-to-date diagrams on every infrastructure change:

```yaml
# Example GitHub Actions workflow
name: Generate Infrastructure Diagrams
on:
  push:
    paths:
      - 'terraform/**'

jobs:
  diagrams:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install tools
        run: |
          pip install diagrams
          wget -qO inframap.tar.gz https://github.com/cycloidio/inframap/releases/latest/download/inframap-linux-amd64.tar.gz
          tar xzf inframap.tar.gz && sudo mv inframap /usr/local/bin/
      - name: Generate diagrams
        run: |
          python3 scripts/architecture.py
          inframap generate ./terraform/ | dot -Tpng > terraform-map.png
      - name: Commit diagrams
        run: |
          git add *.png
          git commit -m "docs: update infrastructure diagrams" || true
          git push
```

## Why Self-Host Your Infrastructure Diagrams?

Keeping architecture diagrams inside your own infrastructure rather than relying on SaaS diagramming tools offers several compelling advantages. First, your infrastructure diagrams contain sensitive information about your system architecture — internal IP ranges, service topologies, resource naming conventions, and dependency relationships. Uploading this data to a third-party cloud service creates an unnecessary security surface.

Second, self-hosted diagram tools integrate directly with your CI/CD pipeline. Every time Terraform applies a change, your diagrams update automatically — no manual export, no screenshotting, no stale documentation. This "documentation as code" approach ensures your diagrams are always synchronized with reality.

Third, cost scales predictably. Commercial diagramming tools like Lucidchart or Cloudcraft charge per user per month, which becomes expensive for growing teams. Self-hosted tools run on your existing infrastructure with zero per-seat licensing costs.

For organizations with compliance requirements (SOC 2, HIPAA, FedRAMP), self-hosting ensures your architecture documentation never leaves your controlled environment. Combined with our [infrastructure drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide/), you can build a complete infrastructure governance pipeline that runs entirely within your own environment.

## Integrating Diagrams into Your Development Workflow

Beyond one-off diagram generation, the real power of Diagram as Code tools comes from integrating them into your daily development workflow. Here's a practical example of how to incorporate infrastructure diagrams into your pull request process:

When a developer proposes a Terraform change, your CI pipeline should:
1. Run `terraform plan` to validate the change
2. Execute the diagram generation tool against the proposed state
3. Upload the generated diagram as a PR comment or artifact
4. Enable reviewers to visually verify the infrastructure impact before approving

This turns infrastructure diagrams from a documentation afterthought into an active review tool. Reviewers can see at a glance whether the proposed change introduces new dependencies, removes critical components, or creates unexpected connections between resources.

For teams using Python Diagrams alongside Terraform, maintain separate diagram scripts in a `docs/diagrams/` directory within your infrastructure repository. These scripts serve double duty — they document the intended architecture and can be compared against Inframap's output (what's actually deployed) to detect configuration drift.


## FAQ

### Do I need to run these tools on every commit?

It depends on your workflow. For design-phase diagrams (Python Diagrams), regenerate them when the architecture changes. For state-based diagrams (Inframap, Terraform Graph), it's best practice to regenerate on every Terraform apply to ensure documentation stays current.

### Can I use these tools with Pulumi or CloudFormation?

Python Diagrams is provider-agnostic and works with any infrastructure tool. Inframap and Terraform Graph are specific to Terraform state/HCL. For Pulumi users, check Pulumi's `pulumi graph` command or export state to a format Inframap can consume.

### How do I handle sensitive information in diagrams?

All three tools read resource metadata (types, names, relationships), not sensitive data like connection strings or passwords. Resource names are included by default — if your naming convention includes sensitive information, use Terraform's resource `tags` to control what appears.

### What's the best tool for documenting existing undocumented infrastructure?

Inframap is the best starting point — run it once against your Terraform state and you'll have a comprehensive diagram in seconds. Use Terraform Graph with Blast Radius if you need to understand specific resource dependencies. Python Diagrams is better suited for planned or proposed architecture rather than reverse-engineering.

### Are there hosted alternatives that don't require self-hosting?

Yes, commercial tools like Cloudcraft, Lucidscale, and Hava offer SaaS-based infrastructure visualization. However, self-hosting these open-source tools gives you full control over your data, integrates directly into your CI/CD pipeline, and avoids per-user licensing costs.

For more on infrastructure management, see our [infrastructure drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide/). If you use Terraform extensively, our [Terragrunt vs Atmos vs Terraspace](../2026-05-18-terragrunt-vs-atmos-vs-terraspace-iac-orchestration-guide/) comparison covers IaC orchestration. For automation, see our [Semaphore vs AWX vs Rundeck](../semaphore-vs-awx-vs-rundeck-self-hosted-ansible-ui-guide-2026/) guide.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Infrastructure Diagram as Code: Diagrams vs Inframap vs Terraform Graph",
  "description": "Compare Python Diagrams, Inframap, and Terraform Graph for self-hosted infrastructure visualization. Automate architecture diagrams from code and Terraform state.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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
