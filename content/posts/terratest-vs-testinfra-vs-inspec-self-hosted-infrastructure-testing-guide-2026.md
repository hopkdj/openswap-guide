---
title: "Terratest vs Testinfra vs InSpec: Best Infrastructure Testing Frameworks 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "testing", "infrastructure", "devops"]
draft: false
description: "Compare Terratest, Testinfra, and InSpec — the top open-source infrastructure testing frameworks. Learn which tool fits your Terraform, Ansible, or compliance testing workflow with practical examples and Docker setups."
---

Infrastructure-as-Code (IaC) has become the standard for managing servers, networks, and cloud resources. But writing configuration code without testing it is a recipe for costly outages. Infrastructure testing frameworks close this gap by letting you validate that your servers, containers, and cloud resources are configured exactly as expected — before changes hit production.

In this guide, we compare three leading open-source infrastructure testing tools: **Terratest** (Go), **Testinfra** (Python), and **InSpec** (Ruby). Each takes a different approach to the same problem — verifying that your infrastructure matches its intended state.

## Why Test Your Infrastructure?

Manual verification doesn't scale. When you manage dozens of servers or hundreds of Terraform modules, you need automated tests that catch misconfigurations before they cause downtime. Infrastructure testing provides:

- **Regression detection** — catch breaking changes in Terraform modules or Ansible roles before merging
- **Compliance verification** — prove that production systems meet security baselines (CIS benchmarks, PCI-DSS, HIPAA)
- **Configuration drift detection** — verify that no unauthorized changes have been made to running systems
- **Documentation as code** — tests serve as living documentation of what your infrastructure should look like

For related reading on infrastructure security, see our [IaC security scanning guide](../checkov-vs-tfsec-vs-trivy-self-hosted-iac-security-scanning-2026/) and [configuration management comparison](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/).

## Terratest: Go-Powered Terraform Testing

[Terratest](https://github.com/gruntwork-io/terratest) is an open-source Go library maintained by Gruntwork. With **7,897 stars** and active development (last updated April 2026), it is the most popular infrastructure testing framework on GitHub.

Terratest specializes in testing Terraform modules, Packer templates, Docker images, and Kubernetes manifests. It deploys real resources, runs assertions against them, and tears everything down — providing end-to-end integration testing for your IaC.

**Key features:**
- Native support for Terraform, Packer, Docker, Kubernetes, and Helm
- Built-in helpers for AWS, GCP, and Azure resource verification
- Parallel test execution with isolated temporary directories
- HTTP, SSH, and database connectivity testing modules
- 50+ Go modules covering common infrastructure patterns

### Installation

Terratest is a Go library — add it as a dependency in your Go module:

```bash
mkdir -p infra-tests && cd infra-tests
go mod init infra-tests
go get github.com/gruntwork-io/terratest/modules/terraform
go get github.com/gruntwork-io/terratest/modules/aws
go get github.com/stretchr/testify
```

### Docker Compose Testing Example

Terratest can validate Docker Compose configurations. Here is a complete test that builds and runs a Docker Compose service, then asserts on stdout output:

```yaml
# examples/docker-compose-stdout-example/docker-compose.yml
version: '2.0'
services:
  bash_script:
    build:
      context: .
    entrypoint: bash_script.sh
```

```go
// test/docker_stdout_example_test.go
package test_test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/docker"
    "github.com/stretchr/testify/assert"
)

func TestDockerComposeStdoutExample(t *testing.T) {
    t.Parallel()

    dockerComposeFile := "../examples/docker-compose-stdout-example/docker-compose.yml"

    // Build first so build output doesn't pollute stdout
    docker.RunDockerComposeContext(
        t, t.Context(), &docker.Options{},
        "-f", dockerComposeFile, "build",
    )

    // Run the Docker image and capture stdout
    output := docker.RunDockerComposeAndGetStdOutContext(
        t, t.Context(), &docker.Options{},
        "-f", dockerComposeFile, "run", "bash_script",
    )

    assert.Contains(t, output, "stdout: message")
    assert.NotContains(t, output, "stderr: error")
}
```

### Terraform Module Testing Example

Here is how you test a real Terraform AWS module — deploy an EC2 instance, verify tags, then destroy:

```go
package test_test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/aws"
    "github.com/gruntwork-io/terratest/modules/random"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestTerraformAwsExample(t *testing.T) {
    t.Parallel()

    exampleFolder := "../examples/terraform-aws-example"
    expectedName := "terratest-aws-example-" + random.UniqueID()
    awsRegion := aws.GetRandomStableRegionContext(t, t.Context(), nil, nil)

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: exampleFolder,
        Vars: map[string]interface{}{
            "instance_name": expectedName,
            "instance_type": "t3.micro",
        },
        EnvVars: map[string]string{
            "AWS_DEFAULT_REGION": awsRegion,
        },
    })

    defer terraform.DestroyContext(t, t.Context(), terraformOptions)
    terraform.InitAndApplyContext(t, t.Context(), terraformOptions)

    instanceID := terraform.OutputContext(t, t.Context(), terraformOptions, "instance_id")
    instanceTags := aws.GetTagsForEc2InstanceContext(t, t.Context(), awsRegion, instanceID)

    assert.True(t, instanceTags["Name"] == expectedName)
}
```

Run with: `go test -v -timeout 30m -tags=aws ./...`

## Testinfra: Python Infrastructure Testing

[Testinfra](https://github.com/pytest-dev/pytest-testinfra) is a pytest plugin that lets you write infrastructure tests in Python. With **2,459 stars**, it is ideal for teams already using Python and pytest.

Testinfra verifies the actual state of servers managed by Ansible, Salt, Puppet, or Chef. It connects to hosts via SSH, local execution, or Docker, and runs assertions using familiar pytest syntax.

**Note:** Testinfra is in maintenance mode (last update November 2025). Contributions are still accepted, but new feature development has slowed. Consider this when choosing for long-term projects.

**Key features:**
- Write tests in Python using pytest — no new DSL to learn
- Connect to hosts via SSH, local, Docker, or Ansible inventory
- Rich host API: file, package, service, port, socket, user, group, command
- Integrates seamlessly with Molecule for Ansible role testing
- Parametrize tests across multiple hosts

### Installation

```bash
pip install pytest-testinfra
```

### Writing Your First Tests

Create `test_server.py`:

```python
def test_ssh_config(host):
    sshd_config = host.file("/etc/ssh/sshd_config")
    assert sshd_config.exists
    assert sshd_config.user == "root"
    assert sshd_config.group == "root"
    assert sshd_config.mode == 0o600


def test_nginx_installed(host):
    nginx = host.package("nginx")
    assert nginx.is_installed
    assert nginx.version.startswith("1.24")


def test_nginx_running(host):
    nginx = host.service("nginx")
    assert nginx.is_running
    assert nginx.is_enabled


def test_port_80_listening(host):
    socket = host.socket("tcp://0.0.0.0:80")
    assert socket.is_listening


def test_no_telnet(host):
    telnet = host.package("telnetd")
    assert not telnet.is_installed
```

Run against a remote host:

```bash
pytest -v test_server.py --hosts=ssh://admin@192.168.1.100
```

Run against a Docker container:

```bash
pytest -v test_server.py --hosts=docker://my_container
```

### Molecule Integration for Ansible Testing

Testinfra is the default verifier for Molecule, the Ansible testing framework:

```yaml
# molecule.yml
verifier:
  name: testinfra

# tests/test_default.py
def test_webapp(host):
    app = host.package("my-webapp")
    assert app.is_installed

    config = host.file("/etc/my-webapp/config.yml")
    assert config.exists
    assert config.contains("listen: 8080")
```

```bash
molecule test
```

## InSpec: Compliance-Focused Infrastructure Testing

[InSpec](https://github.com/inspec/inspec) by Chef is an open-source auditing and testing framework with **3,061 stars**. It uses a human-readable Ruby DSL to define compliance, security, and policy controls.

Unlike Terratest (which tests infrastructure code) and Testinfra (which tests server state), InSpec bridges both worlds — it can run against local systems, remote SSH hosts, Docker containers, and cloud APIs, all from the same profile.

**Key features:**
- Human-readable compliance DSL in Ruby
- Built-in controls for CIS benchmarks, PCI-DSS, and HIPAA
- Run locally, over SSH, via WinRM, or against Docker containers
- JSON and HTML reporting for audit trails
- Profile sharing via Chef Supermarket and GitHub
- Active development with regular releases

### Installation

```bash
# Via RubyGems
gem install inspec-bin

# Or use the official installer script (requires license acceptance)
curl https://chefdownload-commercial.chef.io/install.sh | sudo bash -s -- -P inspec
```

### Docker Setup

InSpec provides an official Docker image:

```dockerfile
FROM chef/inspec:latest
COPY profiles/ /profiles/
CMD ["inspec", "exec", "/profiles/my-profile"]
```

Build and run:

```bash
docker build -t inspec-runner .
docker run --rm inspec-runner
```

For testing a running container:

```bash
docker run --rm chef/inspec exec profile.rb -t docker://container_id
```

### Writing Compliance Controls

InSpec profiles use a Ruby DSL that reads like documentation. Here is a real-world example based on the [dev-sec/linux-baseline](https://github.com/dev-sec/linux-baseline) profile (868 stars):

```ruby
# controls/package_spec.rb
control 'package-01' do
  impact 1.0
  title 'Do not run deprecated inetd or xinetd'
  desc 'Remove deprecated network daemons per CIS Benchmark 2.1.1'

  describe package('inetd') do
    it { should_not be_installed }
  end

  describe package('xinetd') do
    it { should_not be_installed }
  end
end

control 'ssh-01' do
  impact 0.7
  title 'SSH Protocol version must be 2'

  describe sshd_config do
    its('Protocol') { should eq 2 }
  end
end

control 'file-perm-01' do
  impact 0.5
  title '/etc/passwd permissions must be 644'

  describe file('/etc/passwd') do
    it { should exist }
    its('mode') { should cmp '0644' }
    its('owner') { should eq 'root' }
    its('group') { should eq 'root' }
  end
end
```

Run the profile locally:

```bash
inspec exec profile.rb
```

Run against a remote server via SSH:

```bash
inspec exec profile.rb -t ssh://admin@192.168.1.100 -i ~/.ssh/id_rsa
```

Generate an HTML compliance report:

```bash
inspec exec profile.rb --reporter html:report.html --reporter json:report.json
```

## Feature Comparison

| Feature | Terratest | Testinfra | InSpec |
|---------|-----------|-----------|--------|
| **Language** | Go | Python | Ruby |
| **GitHub Stars** | 7,897 | 2,459 | 3,061 |
| **Primary Use Case** | Terraform/Packer/Docker testing | Server state verification | Compliance auditing |
| **Test Style** | Go unit tests (testify) | Python pytest assertions | Ruby DSL (describe/it) |
| **Target Systems** | Cloud APIs, containers | SSH hosts, Docker, local | SSH, WinRM, Docker, cloud APIs |
| **Terraform Testing** | Native (init/apply/destroy) | No | No |
| **Ansible Integration** | Manual | Molecule (built-in) | No |
| **Compliance Profiles** | No | No | Yes (CIS, PCI-DSS) |
| **Reporting** | Go test output + JUnit | pytest output + JUnit | JSON, HTML, CLI |
| **Cloud Providers** | AWS, GCP, Azure (native) | Via SSH/commands | Via SSH/commands |
| **Container Testing** | Docker, Kubernetes, Helm | Docker | Docker |
| **Active Maintenance** | Yes (updated April 2026) | Maintenance mode (Nov 2025) | Yes (updated April 2026) |
| **Learning Curve** | Moderate (Go required) | Low (Python/pytest) | Low (Ruby DSL) |

## When to Choose Which Tool

### Choose Terratest if:
- You write Terraform modules and need integration tests
- You want to test Packer images, Docker builds, or Kubernetes manifests
- Your team is comfortable with Go or willing to learn it
- You need to deploy real cloud resources, verify them, and tear down automatically
- You want parallel test execution with isolated test environments

### Choose Testinfra if:
- Your team uses Python and pytest already
- You need to verify server configuration after Ansible/Salt/Puppet runs
- You want Molecule integration for Ansible role testing
- You prefer a simple, readable assertion syntax over a custom DSL
- You test against multiple hosts using pytest parametrization

### Choose InSpec if:
- Compliance auditing is your primary goal (CIS benchmarks, PCI-DSS)
- You need human-readable compliance reports for auditors
- You want pre-built profiles from the Chef Supermarket
- You test across mixed environments (Linux, Windows, containers, cloud APIs)
- You need JSON/HTML reporting for compliance documentation

## Docker Compose Setup for CI/CD

Here is a Docker Compose configuration for running all three testing frameworks in CI:

```yaml
version: "3.8"

services:
  terratest:
    image: golang:1.22
    working_dir: /app
    volumes:
      - ./infra-tests:/app
      - ~/.aws:/root/.aws:ro
    environment:
      - AWS_REGION=us-east-1
    command: go test -v -timeout 30m -tags=aws ./...

  testinfra:
    image: python:3.12
    working_dir: /app
    volumes:
      - ./server-tests:/app
      - ~/.ssh:/root/.ssh:ro
    command: |
      pip install pytest-testinfra
      pytest -v test_server.py --hosts=ssh://admin@staging-server

  inspec:
    image: chef/inspec:latest
    volumes:
      - ./compliance-profiles:/profiles
      - ~/.ssh:/root/.ssh:ro
    command: inspec exec /profiles/linux-baseline -t ssh://admin@production --reporter cli
```

## Pricing and Licensing

All three tools are **free and open-source**:

| Tool | License | Commercial Support |
|------|---------|-------------------|
| **Terratest** | Apache 2.0 | Gruntwork subscription (paid) |
| **Testinfra** | Apache 2.0 | Community only |
| **InSpec** | Apache 2.0 (inspec-core) / Chef EULA (inspec-bin) | Progress Chef (paid) |

InSpec has a dual-licensing model: `inspec-core` is fully open-source but lacks some commercial features. The `inspec-bin` package requires EULA acceptance. For most self-hosted testing needs, the open-source versions are sufficient.

## FAQ

### Q: Can I use Terratest without deploying real cloud resources?

A: Terratest is designed for integration testing with real resources. For unit-level testing of Terraform without deployment, use `terraform validate`, `tflint`, or `checkov` instead. Terratest does offer a `terraform plan` verification mode that checks the plan output without applying, but full validation requires actual deployment.

### Q: Is Testinfra still actively maintained?

A: As of late 2025, Testinfra is in maintenance mode. The project accepts contributions and bug fixes, but new feature development has slowed significantly. For new projects, consider whether the stability of a mature project outweighs the benefit of active feature development. The core functionality remains solid and well-tested.

### Q: How do I run InSpec tests in a CI/CD pipeline?

A: Use the official Docker image `chef/inspec:latest` in your pipeline. Mount your compliance profiles as a volume, then run `inspec exec /profiles/my-profile -t ssh://user@host`. InSpec supports JSON output for parsing results in CI, and can generate JUnit-format reports compatible with most CI systems.

### Q: Can I test Kubernetes deployments with these tools?

A: Terratest has native Kubernetes and Helm testing modules — it is the best choice for K8s testing. Testinfra can connect to K8s nodes via SSH to verify node-level configuration. InSpec can test K8s node compliance but does not have native Kubernetes API support. For K8s-focused testing, Terratest is the clear winner.

### Q: Which tool is best for CIS benchmark compliance testing?

A: InSpec is purpose-built for this use case. The [dev-sec](https://github.com/dev-sec) project provides free InSpec profiles for Linux, Windows, Apache, Nginx, Docker, and more — covering CIS benchmarks and hardening standards. You can run these profiles against any SSH-accessible host and generate audit-ready HTML reports.

### Q: Can I combine multiple testing frameworks in one project?

A: Yes. A common pattern is to use Terratest for Terraform module integration tests (deploy → verify → destroy), Testinfra for post-deployment server state verification, and InSpec for periodic compliance audits. They complement each other and can run in the same CI pipeline.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Terratest vs Testinfra vs InSpec: Best Infrastructure Testing Frameworks 2026",
  "description": "Compare Terratest, Testinfra, and InSpec — the top open-source infrastructure testing frameworks. Learn which tool fits your Terraform, Ansible, or compliance testing workflow with practical examples and Docker setups.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
