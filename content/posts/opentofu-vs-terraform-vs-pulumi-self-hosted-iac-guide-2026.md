---
title: "OpenTofu vs Terraform vs Pulumi: Self-Hosted IaC Guide 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "infrastructure", "devops"]
draft: false
description: "Complete guide to self-hosted Infrastructure as Code in 2026. Compare OpenTofu, Terraform, and Pulumi with practical installation, configuration, and migration examples."
---

Infrastructure as Code (IaC) has become the backbone of modern infrastructure management. But when your organization needs full control over the tooling — no cloud licensing, no vendor lock-in, no telemetry — the landscape narrows quickly. This guide covers the three leading self-hosted IaC platforms in 2026: **OpenTofu**, **Terraform**, and **Pulumi**.

## Why Self-Host Your IaC Tooling

Running IaC tools entirely on your own infrastructure gives you several advantages that cloud-hosted alternatives simply cannot match:

- **No licensing surprises** — OpenTofu is fully open-source under the MPL 2.0 license. There are no enterprise-only features hidden behind paywalls for core functionality.
- **Zero telemetry** — When you self-host, no usage data leaves your network. Your infrastructure topology, resource counts, and deployment patterns stay private.
- **Full state control** — State files contain sensitive data about your entire infrastructure. Self-hosting means you decide where state is stored, how it is encrypted, and who can access it.
- **Air-gapped environments** — Many organizations operate in isolated networks. Self-hosted IaC tools can run without any outbound internet connectivity.
- **Custom provider development** — When you control the toolchain, you can build and distribute custom providers tailored to your internal APIs and hardware.
- **Compliance and auditability** — Every binary is built from source. Every deployment is reproducible. Auditors can trace exactly what code runs in your environment.

For teams managing hundreds of servers, Kubernetes clusters, or hybrid cloud environments, these factors make self-hosted IaC not just a preference — a requirement.

## OpenTofu: The Open-Source Terraform Fork

OpenTofu emerged in 2023 as a community-driven fork of Terraform, created after HashiCorp changed Terraform's license from the open-source MPL 2.0 to the Business Source License (BSL). It maintains full backward compatibility with existing Terraform configurations and modules, making it the lowest-friction migration path for teams leaving Terraform.

### Key Features

- Drop-in replacement for Terraform 1.5.x with identical HCL syntax
- Built-in state encryption and remote state backend support
- No telemetry or license checks
- Active Linux Foundation backing with transparent governance
- Growing provider ecosystem with 3,000+ community providers

### Installing OpenTofu

The simplest way to install OpenTofu on a self-hosted workstation or CI runner:

```bash
# Add the official repository (Debian/Ubuntu)
curl -fsSL https://get.opentofu.org/install/opentofu.sh -o install-opentofu.sh
chmod +x install-opentofu.sh
sudo ./install-opentofu.sh --install-method deb
```

For air-gapped environments, download the binary directly:

```bash
# Manual binary installation (works anywhere)
OPENTOFU_VERSION="1.9.0"
wget https://github.com/opentofu/opentofu/releases/download/v${OPENTOFU_VERSION}/tofu_${OPENTOFU_VERSION}_linux_amd64.zip
unzip tofu_${OPENTOFU_VERSION}_linux_amd64.zip
sudo mv tofu /usr/local/bin/
tofu --version
```

### Running OpenTofu with Docker

For reproducible builds in CI/CD pipelines, containerize your IaC workflow:

```dockerfile
FROM alpine:3.21

ARG OPENTOFU_VERSION=1.9.0
RUN apk add --no-cache curl unzip bash git openssh-client && \
    curl -fsSL https://github.com/opentofu/opentofu/releases/download/v${OPENTOFU_VERSION}/tofu_${OPENTOFU_VERSION}_linux_amd64.zip \
    -o /tmp/tofu.zip && \
    unzip /tmp/tofu.zip -d /usr/local/bin/ && \
    rm /tmp/tofu.zip && \
    chmod +x /usr/local/bin/tofu

WORKDIR /workspace
ENTRYPOINT ["tofu"]
```

Build and use:

```bash
docker build -t iac-runner:latest .
docker run --rm -v $(pwd):/workspace iac-runner:latest init
docker run --rm -v $(pwd):/workspace iac-runner:latest plan
```

## Terraform: The Industry Standard Under BSL

Terraform remains the most widely adopted IaC tool. The BSL license change means it is no longer open source, but the CLI binary is still free to download and use. The restriction applies to building competing products using Terraform's source code, not to end users provisioning infrastructure.

### Key Considerations for Self-Hosting

- The CLI remains free for infrastructure provisioning
- Terraform Cloud/Enterprise features require a separate license
- State management must be self-hosted (S3 + DynamoDB, Consul, or PostgreSQL)
- Provider registry is still accessible for standard providers

### Self-Hosted State Backend with MinIO and PostgreSQL

A production-grade self-hosted state backend pairs object storage with locking:

```hcl
# backend.tf
terraform {
  backend "pg" {
    conn_str = "postgresql://tfuser:securepass@db.internal:5432/terraform_state?sslmode=require"
    schema_name = "production"
  }
}
```

Set up the PostgreSQL backend:

```bash
# Create the database and user
psql -h db.internal -U postgres <<'SQL'
CREATE USER tfuser WITH PASSWORD 'securepass';
CREATE DATABASE terraform_state OWNER tfuser;
\c terraform_state
GRANT ALL ON SCHEMA public TO tfuser;
SQL

# Initialize with the backend
tofu init -backend-config="conn_str=postgresql://tfuser:securepass@db.internal:5432/terraform_state"
```

### Dockerized Terraform Environment

```yaml
# docker-compose.yml
version: "3.9"

services:
  terraform:
    image: hashicorp/terraform:1.10
    volumes:
      - ./:/workspace
      - ~/.aws:/root/.aws:ro
    environment:
      - TF_VAR_region=us-east-1
    working_dir: /workspace

  state-db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: terraform_state
      POSTGRES_USER: tfuser
      POSTGRES_PASSWORD: securepass
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  pgdata:
```

## Pulumi: Infrastructure as Real Code

Pulumi takes a fundamentally different approach. Instead of HCL configuration files, you write infrastructure definitions in general-purpose programming languages — Python, TypeScript, Go, C#, Java, or YAML.

### Key Features

- Write infrastructure in Python, TypeScript, Go, Java, C#, or YAML
- Native Kubernetes support with first-class Kubernetes resource classes
- Component abstractions for reusable infrastructure patterns
- Built-in secrets encryption with multiple backend options
- Policy as Code with CrossGuard for governance enforcement

### Installing Pulumi Self-Hosted

```bash
# Install via official script
curl -fsSL https://get.pulumi.com | sh

# Or via package manager (macOS)
brew install pulumi

# Verify installation
pulumi version
```

### Self-Hosted Backend (Community Edition)

Pulumi offers a self-hosted backend that stores state locally or in any object storage, without requiring Pulumi Cloud:

```bash
# Use local filesystem backend
pulumi login --local

# Or use self-hosted object storage
pulumi login s3://pulumi-state-bucket?region=us-east-1&endpoint=https://minio.internal:9000
```

### Python Example: Provisioning a Complete Stack

```python
import pulumi
import pulumi_aws as aws

# Create a VPC
vpc = aws.ec2.Vpc("app-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={"Name": "application-vpc", "Environment": "production"}
)

# Create a public subnet
subnet = aws.ec2.Subnet("app-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="us-east-1a",
    map_public_ip_on_launch=True,
    tags={"Name": "public-subnet"}
)

# Security group
sg = aws.ec2.SecurityGroup("app-sg",
    vpc_id=vpc.id,
    description="Allow HTTP and SSH",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
            description="SSH access"
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
            description="HTTP access"
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ]
)

# Launch template
lt = aws.ec2.LaunchTemplate("app-lt",
    image_id="ami-0c55b159cbfafe1f0",
    instance_type="t3.micro",
    vpc_security_group_ids=[sg.id],
    user_data="""#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "Hello from self-hosted IaC" > /var/www/html/index.html
""",
    tag_specifications=[
        aws.ec2.LaunchTemplateTagSpecificationArgs(
            resource_type="instance",
            tags={"Name": "web-server"}
        )
    ]
)

# Auto Scaling group
asg = aws.autoscaling.Group("app-asg",
    desired_capacity=2,
    max_size=4,
    min_size=1,
    vpc_zone_identifiers=[subnet.id],
    launch_template=aws.autoscaling.GroupLaunchTemplateArgs(
        id=lt.id,
        version="$Latest"
    ),
    tags=[
        aws.autoscaling.GroupTagArgs(
            key="Name",
            value="web-asg",
            propagate_at_launch=True
        )
    ]
)

# Outputs
pulumi.export("vpc_id", vpc.id)
pulumi.export("asg_name", asg.name)
```

Deploy:

```bash
pulumi stack init production
pulumi config set aws:region us-east-1
pulumi up
```

## Head-to-Head Comparison

| Feature | OpenTofu | Terraform | Pulumi |
|---------|----------|-----------|--------|
| **License** | MPL 2.0 (fully open) | BSL (source available) | Apache 2.0 |
| **Language** | HCL | HCL | Python, TS, Go, Java, C#, YAML |
| **State Backend** | S3, GCS, Azurerm, HTTP, Consul, PG | S3, GCS, Azurerm, HTTP, Consul | Local, S3, GCS, Azurerm, HTTP, PG |
| **State Encryption** | Built-in (age encryption) | Cloud-only feature | Built-in (multiple KMS options) |
| **Self-Hosted CI** | Full support | Full support | Full support |
| **Air-Gapped** | Yes (full offline) | Yes (with mirror) | Partial (needs registry) |
| **Module Registry** | OpenTofu Registry | Private Registry (paid) | pulumi/packages (open) |
| **Policy as Code** | OPA/Sentinel via plugins | Sentinel (Cloud-only) | CrossGuard (built-in) |
| **Kubernetes Native** | Via provider | Via provider | First-class SDK support |
| **Telemetry** | None | Opt-out required | Opt-out required |
| **Community Size** | Growing fast | Largest | Medium, language-focused |
| **Learning Curve** | Low (HCL) | Low (HCL) | Medium (requires programming) |
| **Migration from TF** | Drop-in (1:1) | N/A | Manual rewrite |
| **Cost** | Free | Free CLI, paid Cloud | Free OSS, paid Cloud |
| **Governance** | Linux Foundation | HashiCorp | Pulumi Corp |

## Migrating from Terraform to OpenTofu

If you are already using Terraform and want to move to a fully open-source toolchain, the migration is straightforward:

```bash
# Step 1: Install OpenTofu (see installation section above)

# Step 2: Your existing .tf files work without changes
# No syntax changes needed for Terraform 1.5.x configurations

# Step 3: Re-initialize with OpenTofu
cd /path/to/your/infrastructure
tofu init

# Step 4: Verify your state is compatible
tofu state list

# Step 5: Run a plan to confirm no changes
tofu plan

# If the plan shows no changes, the migration is complete.
# OpenTofu reads your existing state files natively.
```

For teams using Terraform modules from the public registry, you may need to mirror modules locally:

```bash
# Create a local module mirror
mkdir -p /opt/tofu-modules
cd /opt/tofu-modules

# Download and cache modules
tofu init -plugin-dir=/opt/tofu-plugins
```

## CI/CD Pipeline Integration

### GitHub Actions with Self-Hosted Runner

```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  plan:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4

      - name: Setup OpenTofu
        uses: opentofu/setup-opentofu@v1
        with:
          tofu_version: 1.9.0

      - name: tofu init
        run: tofu init
        env:
          TF_PLUGIN_CACHE_DIR: /opt/tofu-plugin-cache

      - name: tofu plan
        run: tofu plan -out=tfplan
        env:
          TF_STATE_ENCRYPTION_PASSWORD: ${{ secrets.ENCRYPTION_KEY }}

      - name: tofu apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: tofu apply -auto-approve tfplan
```

### GitLab CI with OpenTofu

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - plan
  - apply

variables:
  TF_STATE_URL: "https://gitlab.example.com/api/v4/projects/${CI_PROJECT_ID}/terraform/state/infrastructure"

validate:
  stage: validate
  image: opentofu/opentofu:1.9.0
  script:
    - tofu init -backend-config="address=${TF_STATE_URL}"
    - tofu validate

plan:
  stage: plan
  image: opentofu/opentofu:1.9.0
  script:
    - tofu init -backend-config="address=${TF_STATE_URL}"
    - tofu plan -out=tfplan
  artifacts:
    paths:
      - tfplan
    expire_in: 1 hour

apply:
  stage: apply
  image: opentofu/opentofu:1.9.0
  script:
    - tofu init -backend-config="address=${TF_STATE_URL}"
    - tofu apply -auto-approve tfplan
  when: manual
  only:
    - main
```

## Security Best Practices for Self-Hosted IaC

Managing IaC tools on your own infrastructure requires disciplined security practices:

### 1. Encrypt State at Rest

State files contain sensitive data including passwords, certificates, and resource identifiers. Always encrypt:

```bash
# OpenTofu built-in encryption
tofu init -backend-config="encrypt=true"

# For S3 backends, use server-side encryption
tofu init -backend-config="bucket=my-state-bucket" \
  -backend-config="key=prod/terraform.tfstate" \
  -backend-config="encrypt=true" \
  -backend-config="sse_algorithm=aws:kms"
```

### 2. Isolate Credentials

Never store cloud provider credentials in your IaC repository. Use environment variables or a secrets manager:

```bash
# Use environment variables (recommended for CI)
export AWS_ACCESS_KEY_ID="${VAULT_AWS_KEY}"
export AWS_SECRET_ACCESS_KEY="${VAULT_AWS_SECRET}"

# Or use HashiCorp Vault agent
vault agent -config=vault-agent.hcl &
tofu apply  # Credentials injected via env template
```

### 3. Implement State File Locking

Prevent concurrent modifications that corrupt state:

```hcl
# DynamoDB locking table (create once)
resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

# Backend configuration with locking
terraform {
  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

### 4. Pin Provider Versions

Always pin provider versions to ensure reproducible builds:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.32"
    }
  }

  required_version = ">= 1.9.0"
}
```

## Which Tool Should You Choose?

The decision comes down to your team's existing skills and organizational requirements:

**Choose OpenTofu if:**
- You already have Terraform configurations and want a drop-in replacement
- You need a truly open-source license with no restrictions
- You want built-in state encryption without paying for cloud features
- Your team values community governance over corporate control

**Choose Terraform if:**
- Your organization has existing HashiCorp Enterprise subscriptions
- You rely on Terraform Cloud's remote run features
- Your team is already trained and certified on Terraform
- You need Sentinel policy enforcement at enterprise scale

**Choose Pulumi if:**
- Your team prefers writing infrastructure in general-purpose languages
- You need complex logic, loops, and conditionals in your infrastructure code
- You want first-class Kubernetes SDK support
- You are building reusable infrastructure libraries with testing frameworks

For most organizations looking for a self-hosted, open-source IaC solution in 2026, **OpenTofu** offers the smoothest transition from Terraform with the strongest open-source guarantees. Teams starting fresh with infrastructure automation and comfortable in Python or TypeScript should seriously consider **Pulumi** for its expressive programming model.

## Getting Started Today

Here is the fastest path to running your first self-hosted IaC deployment:

```bash
# 1. Install OpenTofu
curl -fsSL https://get.opentofu.org/install/opentofu.sh | bash

# 2. Create a project directory
mkdir my-infra && cd my-infra

# 3. Write your configuration
cat > main.tf << 'EOF'
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name        = "self-hosted-iac"
    ManagedBy   = "opentofu"
    Environment = "production"
  }
}
EOF

# 4. Initialize and deploy
tofu init
tofu plan
tofu apply
```

The infrastructure you manage should be under your control — including the tools that define it. Self-hosted IaC gives you that control, and in 2026, the options have never been stronger.
