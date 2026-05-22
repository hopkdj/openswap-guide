---
title: "Self-Hosted Remote Attestation Platforms: Keylime vs CoCo vs IMA/EVM"
date: "2026-05-22"
tags: ["security", "attestation", "self-hosted", "tpm", "linux", "integrity"]
draft: false
description: "Compare self-hosted remote attestation platforms: Keylime, Confidential Containers, and IMA/EVM. Docker deployment guides, architecture comparisons, and security analysis."
---

Remote attestation is the process of cryptographically verifying that a remote system is running trusted software in a known-good state. For self-hosted infrastructure, remote attestation provides critical security assurance: before deploying workloads to a server, you can verify its firmware, bootloader, kernel, and application integrity — detecting tampering, rootkits, or unauthorized modifications.

Three open-source approaches provide remote attestation capabilities on Linux: Keylime (a CNCF project for edge and cloud trust management), Confidential Containers (CoCo, enabling verifiable container workloads), and IMA/EVM (the Linux kernel's Integrity Measurement Architecture and Extended Verification Module). Each targets different threat models and infrastructure scales.

This guide compares all three platforms, covering architecture, deployment, security guarantees, and production integration patterns.

## What Is Remote Attestation?

Remote attestation uses hardware roots of trust (typically TPM 2.0 chips) to create a verifiable chain of measurements from boot to runtime:

1. **Boot measurement** — Firmware measures the bootloader, which measures the kernel, which measures the initramfs
2. **PCR accumulation** — Each measurement extends a Platform Configuration Register (PCR) in the TPM using cryptographic hashing
3. **Attestation quote** — The TPM signs the current PCR values with its Attestation Key (AK), creating a verifiable quote
4. **Verification** — A verifier service checks the quote against known-good PCR values, confirming the system booted correctly

This process enables zero-trust infrastructure: no server receives sensitive workloads until its integrity is cryptographically verified.

## Keylime

Keylime is a CNCF sandbox project that provides remote attestation, secure key provisioning, and runtime integrity monitoring for edge, cloud, and IoT systems. It uses TPM 2.0 for hardware-rooted trust and supports multiple attestation protocols.

**GitHub**: `keylime/keylime` | **Stars**: 537+ | **Language**: Python/Rust | **Status**: CNCF Sandbox

### Architecture

Keylime has three components:
- **Registrar** — Catalogs agents and their TPM public keys
- **Verifier** — Performs attestation checks against agents, comparing PCR quotes against known-good values
- **Agent** — Runs on target systems, providing TPM quotes and receiving verified keys

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  keylime-verifier:
    image: docker.io/keylime/keylime-verifier:latest
    container_name: keylime-verifier
    restart: unless-stopped
    ports:
      - "8881:8881"
    volumes:
      - ./keylime-config:/etc/keylime
      - ./keylime-data:/var/lib/keylime
    environment:
      - KEYLIME_VERIFIER_PORT=8881
    networks:
      - keylime-net

  keylime-registrar:
    image: docker.io/keylime/keylime-registrar:latest
    container_name: keylime-registrar
    restart: unless-stopped
    ports:
      - "8890:8890"
      - "8891:8891"
    volumes:
      - ./keylime-config:/etc/keylime
    networks:
      - keylime-net

  keylime-db:
    image: docker.io/postgres:16
    container_name: keylime-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=keylime
      - POSTGRES_USER=keylime
      - POSTGRES_PASSWORD=keylime_secret
    volumes:
      - ./keylime-db-data:/var/lib/postgresql/data
    networks:
      - keylime-net

networks:
  keylime-net:
    driver: bridge
```

### Agent Registration

```bash
# Install keylime-agent on target system
pip install keylime-agent

# Configure the agent
cat > /etc/keylime/agent.conf << 'EOF'
[agent]
server_ip = verifier.example.com
server_port = 8881
registrar_ip = registrar.example.com
registrar_port = 8890
EOF

# Start the agent
keylime_agent
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| TPM 2.0 support | Full |
| Runtime integrity monitoring | Yes (IMA integration) |
| Secure key provisioning | Yes (after attestation) |
| Multi-agent fleet management | Yes |
| REST API | Yes |
| Kubernetes integration | Available |
| Active development | Yes (CNCF) |
| Maturity | Medium (2018+) |

## Confidential Containers (CoCo)

Confidential Containers (CoCo) is a CNCF project that extends container runtimes with hardware-backed confidentiality and remote attestation. It enables verifiable container workloads running in trusted execution environments (TEEs) like Intel TDX, AMD SEV-SNP, and AMD SEV-ES.

**GitHub**: `confidential-containers/guest-components` | **Stars**: 120+ | **Language**: Rust | **Status**: CNCF Sandbox

### Architecture

CoCo integrates with container runtimes (containerd, CRI-O) to launch containers inside TEEs. The attestation flow:
1. Guest components measure the container image and runtime state
2. The TEE hardware generates an attestation report
3. A remote verifier validates the report against the expected image digest
4. Secrets are provisioned only after successful verification

### Deployment with Kubernetes

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata-clh
handler: kata-clh
---
apiVersion: v1
kind: Pod
metadata:
  name: attested-workload
spec:
  runtimeClassName: kata-clh
  containers:
  - name: workload
    image: docker.io/library/nginx:latest
    resources:
      limits:
        cpu: "2"
        memory: "2Gi"
```

### Attestation Service Configuration

```bash
# Install CoCo attestation service
cargo install coco-as

# Configure the attestation service
cat > /etc/coco-as/config.toml << 'EOF'
[attestation]
policy = "reference"
evidence_format = "ccel"
EOF

# Start the service
coco-as serve --config /etc/coco-as/config.toml
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| TEE hardware support | Intel TDX, AMD SEV-SNP |
| Container runtime integration | containerd, CRI-O |
| Image digest verification | Yes |
| Kubernetes-native | Yes (RuntimeClass) |
| Multi-tenant isolation | Yes (per-container TEE) |
| CPU overhead | Moderate (TEE encryption) |
| Hardware requirement | TEE-capable CPU |
| Active development | Very active |

## IMA/EVM (Integrity Measurement Architecture)

IMA (Integrity Measurement Architecture) and EVM (Extended Verification Module) are Linux kernel subsystems that measure and verify file integrity at runtime. IMA measures files on access, storing hashes in the kernel's measurement list. EVM protects file metadata (permissions, SELinux labels, capabilities) with cryptographic signatures.

**Part of**: Linux kernel | **Language**: C | **Status**: Mainline kernel (since 2.6.x)

### Architecture

IMA operates as a Linux Security Module (LSM) hook:
1. **Measurement** — Every file access triggers a hash measurement, appended to the kernel measurement list
2. **Appraisal** — Files can be required to have known-good signatures before execution
3. **Audit** — Measurements are logged and can be remotely attested via `/sys/kernel/security/ima/ascii_runtime_measurements`

EVM extends IMA by protecting extended attributes (xattrs) from offline tampering:

```bash
# Enable IMA measurement policy
mount -t securityfs securityfs /sys/kernel/security
echo "measure func=BPRM_CHECK mask=MAY_EXEC" > /sys/kernel/security/ima/policy

# Check runtime measurements
cat /sys/kernel/security/ima/ascii_runtime_measurements

# Verify EVM signature on a file
getfattr -n security.evm /bin/ls
```

### IMA Policy Configuration

```bash
# Measure all executable files
echo "measure func=BPRM_CHECK mask=MAY_EXEC" > /sys/kernel/security/ima/policy

# Measure all file reads (comprehensive)
echo "measure func=FILE_CHECK mask=MAY_READ uid=0" >> /sys/kernel/security/ima/policy

# Require signatures for kernel modules
echo "appraise func=MODULE_CHECK appraise_type=imasig" >> /sys/kernel/security/ima/policy
```

### Remote Attestation Integration

IMA measurements can be remotely attested by sending the measurement list to a verifier:

```bash
# Export measurement list for remote verification
cat /sys/kernel/security/ima/binary_runtime_measurements > /tmp/ima-measurements.bin

# Send to Keylime verifier for comparison
curl -X POST http://verifier.example.com:8881/agents/measurements   -H "Content-Type: application/octet-stream"   --data-binary @/tmp/ima-measurements.bin
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| Kernel-level integration | Native (no additional software) |
| File integrity measurement | Yes (all file operations) |
| Metadata protection | Yes (EVM xattr signing) |
| Runtime enforcement | Yes (appraisal mode) |
| Remote attestation | Via Keylime or custom verifier |
| Performance overhead | Low (hash computation) |
| Hardware requirement | None (software-only) |
| Maturity | Very High (kernel mainline) |

## Feature Comparison

| Feature | Keylime | CoCo Attestation | IMA/EVM |
|---------|---------|-----------------|---------|
| Attestation type | Remote (TPM quote) | TEE-based (hardware report) | Local measurement list |
| Hardware requirement | TPM 2.0 | TEE CPU (TDX/SEV-SNP) | None |
| Boot verification | Yes (PCR measurement) | Yes (TEE launch measurement) | No (runtime only) |
| Runtime monitoring | Yes (IMA integration) | Yes (container image verification) | Yes (file access measurement) |
| Key provisioning | Yes (post-attestation) | Yes (post-attestation) | No |
| Fleet management | Yes (registrar + verifier) | Via Kubernetes orchestration | No (per-system) |
| Container support | Via agent | Native (RuntimeClass) | Via host kernel |
| Kubernetes integration | Available | Native | Via DaemonSet |
| Maturity | Medium (2018+) | Early (2022+) | Very High (kernel mainline) |
| Best for | Edge/IoT fleets | Confidential cloud workloads | Server integrity monitoring |

## Choosing the Right Attestation Platform

**Choose Keylime** when managing fleets of edge, cloud, or IoT devices that need automated remote attestation and secure key provisioning. Keylime's registrar/verifier architecture scales to hundreds of agents, and its IMA integration provides runtime integrity monitoring alongside boot attestation.

**Choose Confidential Containers** when running workloads that require hardware-enforced confidentiality (multi-tenant clouds, regulated workloads). CoCo's TEE-based attestation provides stronger isolation than software-only approaches, and its Kubernetes-native integration simplifies deployment for container orchestration environments.

**Choose IMA/EVM** when you need lightweight, software-only file integrity monitoring without additional infrastructure. IMA is built into every modern Linux kernel, requires no external services, and provides comprehensive runtime measurement of all file operations. Combine with Keylime for remote attestation of IMA measurements.

## Why Self-Host Remote Attestation Infrastructure?

Running your own attestation infrastructure ensures:

- **Zero-trust verification** — No server receives sensitive workloads until its integrity is cryptographically verified. Self-hosted verifiers control the trust policy and known-good baseline.
- **Hardware-rooted trust** — TPM 2.0 and TEE hardware provide tamper-evident measurement chains from firmware to application. Self-hosted attestation keeps these chains within your infrastructure.
- **Compliance and auditability** — Remote attestation provides cryptographically verifiable evidence of system integrity for compliance frameworks (SOC 2, ISO 27001, FedRAMP).
- **Supply chain security** — Verifying boot measurements and file integrity detects unauthorized modifications from compromised packages, supply chain attacks, or insider threats.
- **No third-party dependency** — Cloud provider attestation services (AWS Nitro, Azure Confidential Computing) tie your trust chain to specific platforms. Self-hosted attestation is hardware-agnostic.

For comprehensive server security auditing, see our [Lynis vs OpenSCAP vs Goss comparison](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide-2026/). For container runtime security, the [Falco vs Tetragon vs Tracee guide](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide-2026/) covers real-time threat detection.

## FAQ

### What is the difference between boot attestation and runtime attestation?

Boot attestation verifies the system started with trusted firmware, bootloader, and kernel by checking TPM PCR values against known-good baselines. Runtime attestation monitors file integrity during operation (via IMA measurements), detecting unauthorized modifications after boot. Keylime supports both; IMA/EVM provides runtime only; CoCo verifies container image integrity at launch.

### Do I need a TPM chip for remote attestation?

For hardware-rooted boot attestation, yes — TPM 2.0 provides the cryptographic foundation for PCR measurement and signed attestation quotes. IMA/EVM works without a TPM but provides software-only measurement that can be tampered with by a compromised kernel. CoCo requires TEE-capable CPUs (Intel TDX or AMD SEV-SNP).

### Can Keylime attest virtual machines?

Yes, Keylime supports vTPM (virtual TPM) attestation for virtual machines. Hypervisors like QEMU/KVM can provide vTPM devices to guests, enabling the same attestation flow as physical hardware. Cloud providers using KVM can deploy Keylime for tenant VM attestation.

### How does CoCo differ from standard container security?

Standard containers share the host kernel and rely on namespaces/cgroups for isolation. CoCo runs containers inside TEEs (Trusted Execution Environments) that provide hardware-enforced memory encryption and remote attestation. Even a compromised host kernel cannot read container memory or tamper with execution.

### What is the performance overhead of IMA measurement?

IMA measurement adds approximately 1-3% CPU overhead for file access operations, as each accessed file is hashed and the measurement appended to the kernel list. In appraisal mode (requiring signatures), overhead increases due to signature verification. For most server workloads, the overhead is negligible.

### How do I establish a known-good baseline for attestation?

Build a reference system with known-good software versions, measure its PCR values (for boot attestation) and file hashes (for IMA), and store these baselines in your verifier. Keylime stores baselines in its database; CoCo uses image digests; IMA baselines can be stored as whitelist files. Re-baseline after every verified software update.

### Can I use remote attestation with existing configuration management?

Yes. Integrate attestation checks into your deployment pipeline: Ansible, Puppet, or Salt can verify system integrity before applying configurations. Keylime's REST API enables programmatic attestation checks that gate deployment actions. Failed attestation can trigger alerts or quarantine the affected system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Remote Attestation Platforms: Keylime vs CoCo vs IMA/EVM",
  "description": "Compare self-hosted remote attestation platforms: Keylime, Confidential Containers, and IMA/EVM. Docker deployment guides, architecture comparisons, and security analysis.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
