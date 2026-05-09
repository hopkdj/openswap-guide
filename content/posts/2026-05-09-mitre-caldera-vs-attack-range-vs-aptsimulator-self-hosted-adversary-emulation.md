---
title: "MITRE Caldera vs Splunk Attack Range vs APTSimulator: Self-Hosted Adversary Emulation Platforms (2026)"
date: "2026-05-09"
tags: ["security", "adversary-emulation", "penetration-testing", "red-team", "threat-detection"]
draft: false
---

Adversary emulation platforms allow security teams to simulate real-world attack techniques against their own infrastructure, validating detection capabilities and improving incident response readiness. Rather than waiting for a real breach to expose gaps in monitoring, these tools proactively test your defenses using tactics, techniques, and procedures (TTPs) modeled after actual threat actors.

This guide compares three self-hosted adversary emulation platforms: **MITRE Caldera**, **Splunk Attack Range**, and **Nextron APTSimulator**. Each takes a different approach to adversary simulation — from automated red team operations to instrumented attack environments and APT victim simulation.

## What Is Adversary Emulation?

Adversary emulation differs from traditional penetration testing. While pentesting finds individual vulnerabilities, emulation replicates the full attack lifecycle of a specific threat actor or campaign. This includes initial access, persistence, lateral movement, privilege escalation, and data exfiltration — mapped to frameworks like MITRE ATT&CK.

Key benefits of running adversary emulation in-house:

- **Detection validation** — Verify that your SIEM, EDR, and IDS tools catch known attack patterns
- **Blue team training** — Give security analysts realistic attack scenarios to practice against
- **Compliance requirements** — Frameworks like NIST 800-53 and PCI DSS require regular security testing
- **Gap identification** — Find blind spots in logging, alerting, and response procedures before real attackers exploit them
- **Continuous improvement** — Run emulation campaigns regularly to measure security posture over time

Self-hosting these platforms keeps all attack data, credentials, and test results within your own infrastructure — critical for organizations handling sensitive systems.

## Quick Comparison

| Feature | MITRE Caldera | Splunk Attack Range | APTSimulator |
|---------|--------------|---------------------|-------------|
| **GitHub Stars** | 6,953+ | 2,485+ | 2,741+ |
| **Language** | Python | Python | PowerShell/Python |
| **Primary Use** | Automated adversary emulation | Vulnerable instrumented environments | APT victim simulation |
| **ATT&CK Mapping** | Full TTP coverage | ATT&CK-based scenarios | APT-group specific techniques |
| **Web UI** | Yes | CLI + Terraform | No (CLI only) |
| **Docker Support** | Yes | Yes | Limited |
| **Cloud Support** | AWS, Azure, GCP | AWS, Azure, GCP | Local Windows only |
| **License** | Apache 2.0 | Apache 2.0 | GPL 3.0 |
| **Last Updated** | May 2026 | May 2026 | Sep 2025 |

## MITRE Caldera: Automated Adversary Emulation Platform

[Caldera](https://github.com/mitre/caldera) is the MITRE Corporation's open-source adversary emulation platform. It provides a web-based interface for planning and executing adversarial operations against your own network, with full integration into the MITRE ATT&CK framework.

### Key Features

- **Automated agent deployment** — Agents (SANDCAT, MANX, HTTP) deploy to target systems and execute commands
- **ATT&CK technique mapping** — Every operation maps directly to MITRE ATT&CK technique IDs
- **Adversary profiles** — Pre-built profiles for known APT groups (APT28, APT29, Lazarus, etc.)
- **Plugin ecosystem** — Extend capabilities with plugins for response, training, and reporting
- **Multi-platform agents** — Windows, Linux, and macOS agent support
- **Operation planning** — Plan multi-step attack campaigns with specific objectives

### Docker Compose Deployment

Caldera provides an official Docker Compose configuration for self-hosted deployment:

```yaml
version: '3'

services:
  caldera:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        TZ: "UTC"
        VARIANT: "full"
    image: caldera:latest
    container_name: caldera
    ports:
      - "8888:8888"
      - "8443:8443"
      - "7010:7010"
      - "7011:7011/udp"
    volumes:
      - ./:/usr/src/app
      - /usr/src/app/plugins/magma
    command: --log DEBUG
```

Deploy with:

```bash
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
docker compose up -d
```

Access the web UI at `http://localhost:8888` with default credentials `red/admin`.

### Installation (Non-Docker)

```bash
# Install system dependencies
pip3 install -r requirements.txt

# Start Caldera server
python3 server.py --log DEBUG

# Access at http://localhost:8888
```

## Splunk Attack Range: Instrumented Attack Environments

[Splunk Attack Range](https://github.com/splunk/attack_range) takes a different approach. Instead of deploying agents to your production network, it builds instrumented, vulnerable lab environments where you can safely execute attacks and collect telemetry data.

### Key Features

- **Terraform-powered infrastructure** — Spin up realistic attack labs in AWS, Azure, or GCP
- **Pre-built attack scenarios** — 50+ ATT&CK-mapped attack simulations
- **Splunk integration** — Automatic forwarding of all telemetry to Splunk for analysis
- **Atomic Red Team integration** — Execute tests from the Atomic Red Team library
- **Customizable environments** — Add your own detection rules and attack scenarios
- **Multi-machine topologies** — Simulate domain controllers, workstations, and servers

### Docker Compose Deployment

The Attack Range provides a Docker-based CLI for managing cloud deployments:

```yaml
services:
  attack_range:
    profiles:
      - cli
    build:
      context: ..
      dockerfile: docker/Dockerfile
    image: attack_range:all
    volumes:
      - ../config:/attack_range/config
      - ../templates:/attack_range/templates
      - ../ssh_keys:/attack_range/ssh_keys
      - ../apps:/attack_range/apps
    entrypoint: ["python3.12", "attack_range.py"]
    networks:
      - attack-range-network
```

Usage:

```bash
git clone https://github.com/splunk/attack_range.git
cd attack_range/docker
docker compose run --rm attack_range build
docker compose run --rm attack_range configure

# Deploy attack range in AWS
docker compose run --rm attack_range build --action build
```

### Running Simulations

```bash
# Execute a specific ATT&CK technique
docker compose run --rm attack_range simulate --technique T1059.001 --target win-wks-01

# Run all simulations and collect data
docker compose run --rm attack_range simulate --all
```

## Nextron APTSimulator: APT Victim Simulation

[APTSimulator](https://github.com/NextronSystems/APTSimulator) by Nextron Systems takes yet another approach. Instead of executing attacks against your infrastructure, it makes a system **look** like it was already compromised by an APT group. This is invaluable for testing incident response procedures and forensic analysis capabilities.

### Key Features

- **APT artifact generation** — Creates realistic indicators of compromise (IOCs) on target systems
- **Multiple APT profiles** — Simulates artifacts from APT28, APT29, Carbanak, and other groups
- **Windows-focused** — Generates Windows-specific artifacts (registry keys, scheduled tasks, files)
- **No network activity** — All artifacts are local, making it safe for isolated test environments
- **Modular design** — Each module simulates a different attack technique or persistence mechanism

### Deployment

APTSimulator runs directly on Windows systems. Download and execute:

```powershell
# Download APTSimulator
Invoke-WebRequest -Uri "https://github.com/NextronSystems/APTSimulator/releases/download/v0.9.5/APTSimulator_v0.9.5.zip" -OutFile "APTSimulator.zip"
Expand-Archive -Path "APTSimulator.zip" -DestinationPath "C:\APTSimulator"

# Run all APT simulations
cd C:\APTSimulator
.\APTSimulator.bat -a

# Run specific APT group simulation
.\APTSimulator.bat -m apt28
```

### Generated Artifacts Include

- Malicious scheduled tasks and services
- Suspicious registry entries and WMI events
- Known-bad file hashes and file paths
- C2 communication indicators (without actual network traffic)
- Persistence mechanisms matching real APT groups

## Choosing the Right Platform

| Scenario | Recommended Tool |
|----------|-----------------|
| Automated red team operations with ATT&CK mapping | **MITRE Caldera** |
| Building instrumented lab environments for detection engineering | **Splunk Attack Range** |
| Testing incident response and forensic capabilities | **APTSimulator** |
| Training blue team analysts | **Caldera** or **Attack Range** |
| Compliance testing (PCI DSS, NIST) | **Caldera** |
| Windows endpoint detection testing | **APTSimulator** |
| Cloud attack simulation | **Splunk Attack Range** |

## Why Self-Host Adversary Emulation?

Running adversary emulation platforms on your own infrastructure offers several critical advantages over cloud-hosted or SaaS alternatives:

**Data sovereignty and confidentiality** — Attack simulations generate detailed logs of your network topology, security gaps, and detection capabilities. Self-hosting ensures this sensitive intelligence never leaves your controlled environment. For regulated industries and government organizations, keeping adversary emulation data on-premises is often a compliance requirement.

**Realistic network testing** — Cloud-based emulators cannot simulate attacks against your actual network topology, internal services, or custom applications. Self-hosted platforms deploy directly into your environment, testing real defenses against real attack techniques. This produces far more actionable results than simulated tests in isolated cloud environments.

**Cost efficiency** — Enterprise adversary emulation SaaS platforms charge per-seat or per-operation licensing fees that scale quickly. Self-hosted open-source platforms like Caldera and Attack Range have no per-operation costs, making continuous testing economically viable even for large organizations.

**Customization and integration** — Open-source platforms can be modified to target your specific technology stack, integrate with your existing SIEM and SOAR tools, and simulate threat actors relevant to your industry vertical. Caldera's plugin system and Attack Range's Terraform templates provide deep customization options.

**Isolation for safety** — Adversary emulation involves executing attack techniques. Self-hosted platforms can be deployed in isolated network segments with strict egress controls, ensuring simulated attacks never impact production systems or trigger external alerts.

For related security testing tools, see our [chaos engineering comparison](../2026-05-06-chaosblade-vs-pumba-vs-toxiproxy-chaos-engineering/) and [container security scanning guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening/). If you need to test your email security posture, our [phishing simulation guide](../self-hosted-phishing-simulation-security-awareness-training-gophish-2026/) covers that angle.

## FAQ

### What is the difference between adversary emulation and penetration testing?

Penetration testing focuses on finding individual vulnerabilities in specific systems or applications. Adversary emulation replicates the complete attack lifecycle of a real threat actor, including reconnaissance, initial access, lateral movement, privilege escalation, and data exfiltration. Emulation validates your detection and response capabilities, while pentesting validates your vulnerability management.

### Is it legal to run adversary emulation against my own infrastructure?

Yes, running adversary emulation against infrastructure you own or have explicit authorization to test is legal. However, you should coordinate with your IT team, establish clear rules of engagement, and ensure all testing occurs within authorized time windows. Never run emulation against production systems without proper change management approval.

### Do I need a dedicated lab environment for adversary emulation?

For Caldera and Attack Range, a dedicated lab environment is strongly recommended. These tools execute real attack techniques that could disrupt production services. APTSimulator is safer for production-adjacent testing since it generates artifacts without executing actual attacks, but even then, isolated test systems are preferred.

### How often should I run adversary emulation campaigns?

Best practice is to run emulation campaigns quarterly or after significant infrastructure changes. Continuous emulation — running small-scale tests weekly — is becoming more common as organizations mature their security programs. Caldera supports automated scheduling, and Attack Range can integrate into CI/CD pipelines for continuous detection testing.

### Can these tools test cloud environments?

Yes. Splunk Attack Range natively supports deploying attack scenarios in AWS, Azure, and GCP using Terraform. MITRE Caldera has cloud-specific agents and can target cloud workloads. APTSimulator is Windows-focused and works on cloud-hosted Windows instances.

### What skill level is required to operate these platforms?

Caldera requires moderate security expertise — understanding of MITRE ATT&CK, networking, and basic scripting. Attack Range requires infrastructure-as-code knowledge (Terraform) and cloud platform familiarity. APTSimulator is the most accessible, requiring only basic Windows administration skills to execute.

### Do these platforms integrate with SIEM tools?

Caldera generates logs that can be forwarded to any SIEM via its logging plugin. Attack Range is designed specifically for Splunk integration but supports forwarding to other SIEMs. APTSimulator generates local artifacts that can be detected by your existing EDR and SIEM tools — the value is in testing whether they actually detect the simulated indicators.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MITRE Caldera vs Splunk Attack Range vs APTSimulator: Self-Hosted Adversary Emulation Platforms (2026)",
  "description": "Compare MITRE Caldera, Splunk Attack Range, and APTSimulator for self-hosted adversary emulation. Learn which platform best fits your security testing needs.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
