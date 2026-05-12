---
title: "Self-Hosted TPM Management: tpm2-tools vs swtpm vs tpm2-tss Guide"
date: "2026-05-12"
description: "Compare open-source TPM 2.0 management tools for hardware security, key storage, and attestation. Deployment guides with Docker compose configs."
tags: ["tpm", "hardware-security", "key-management", "self-hosted", "security"]
draft: false
---

Trusted Platform Module (TPM) 2.0 is a hardware-based security standard that provides cryptographic key storage, platform attestation, and measured boot capabilities. For organizations managing TPM-equipped servers or building secure infrastructure, having the right management tooling is essential for provisioning, testing, and operating TPM functions at scale.

This guide compares three open-source TPM management solutions — **tpm2-tools**, **swtpm**, and **tpm2-tss** — covering their architectures, deployment options, and use cases for self-hosted environments.

## What Is TPM 2.0 and Why Manage It?

The Trusted Computing Group's TPM 2.0 specification defines a secure cryptoprocessor that stores cryptographic keys, performs cryptographic operations, and provides hardware-rooted trust. TPM capabilities include:

- **Secure key storage** — keys never leave the TPM boundary, protecting against software extraction
- **Platform attestation** — cryptographically proving the system boot state hasn't been tampered with
- **Measured boot** — recording each boot stage measurement in Platform Configuration Registers (PCRs)
- **Sealed storage** — encrypting data that only decrypts when specific PCR values match
- **Remote attestation** — allowing a remote party to verify platform integrity

Without proper management tools, TPM functionality remains inaccessible. The three tools below serve different roles in the TPM software stack.

## Tool Comparison Overview

| Feature | tpm2-tools | swtpm | tpm2-tss |
|---------|-----------|-------|----------|
| Type | CLI utilities | TPM emulator | Software stack library |
| Hardware required | Real TPM chip | None (emulated) | Real TPM or emulator |
| TPM version | TPM 2.0 | TPM 2.0 | TPM 2.0 |
| Docker deployment | Yes (via device passthrough) | Yes (standalone container) | Yes (library dependency) |
| Primary use | Key management, attestation | Testing, development, CI/CD | Application integration |
| GitHub stars | 860+ | 785+ | 880+ |
| Language | C (CLI wrappers) | C | C |
| Maintained by | Intel (tpm2-software) | IBM (Stefan Berger) | Intel (tpm2-software) |
| Last active | 2026 | 2026 | 2026 |

## tpm2-tools: CLI Management Suite

**tpm2-tools** is a collection of command-line utilities built on top of the tpm2-tss stack. It provides direct access to TPM 2.0 functions through a consistent CLI interface, making it the go-to tool for TPM provisioning, key management, and attestation operations.

### Key Capabilities

- **Key generation and management** — create RSA, ECC, and symmetric keys inside the TPM
- **Sealing and unsealing** — encrypt data bound to specific PCR states
- **Platform attestation** — read and verify PCR values, generate attestation quotes
- **NV index management** — create and manage non-volatile storage areas
- **Policy-based authorization** — complex multi-factor authorization policies
- **Session handling** — HMAC and policy sessions for secure TPM communication

### Installation and Deployment

**Package installation** (Debian/Ubuntu):
```bash
sudo apt update
sudo apt install tpm2-tools tpm2-abrmd
```

**Docker deployment** with device passthrough:
```yaml
version: "3.8"
services:
  tpm-tools:
    image: ubuntu:24.04
    devices:
      - /dev/tpmrm0:/dev/tpmrm0
    volumes:
      - tpm-data:/data
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        apt-get update && apt-get install -y tpm2-tools
        tpm2_pcrread
        tpm2_createprimary -C o -c primary.ctx
        tpm2_readpublic -c primary.ctx
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: []

volumes:
  tpm-data:
```

For systems with a TPM Resource Manager (`tpm2-abrmd`), multiple containers can share TPM access safely:

```yaml
services:
  tpm-abrmd:
    image: ubuntu:24.04
    devices:
      - /dev/tpmrm0:/dev/tpmrm0
    cap_add:
      - SYS_ADMIN
    command: >
      bash -c "
        apt-get update && apt-get install -y tpm2-abrmd tpm2-tools dbus
        mkdir -p /run/dbus && dbus-daemon --system
        tpm2-abrmd --tcti=device:/dev/tpmrm0 &
        sleep infinity
      "
    networks:
      - tpm-net

  tpm-client:
    image: ubuntu:24.04
    depends_on:
      - tpm-abrmd
    command: bash -c "apt-get update && apt-get install -y tpm2-tools && tpm2_pcrread -T mssim"
    networks:
      - tpm-net

networks:
  tpm-net:
    driver: bridge
```

## swtpm: Software TPM Emulator

**swtpm** (Software TPM) provides a fully functional TPM 2.0 emulator that runs entirely in software. It implements the TPM 2.0 specification without requiring physical TPM hardware, making it invaluable for testing, development, and CI/CD pipelines where real TPM chips aren't available.

### Key Capabilities

- **Full TPM 2.0 emulation** — implements the complete TPM 2.0 command set
- **Multiple interfaces** — socket (TCP), CUSE (character device), and Linux chardev interfaces
- **Persistent state** — saves TPM state to disk for persistence across reboots
- **Migration support** — transfer TPM state between hosts
- **libtpms backend** — uses IBM's libtpms for cryptographic operations
- **Test and development** — ideal for automated testing of TPM-dependent applications

### Installation and Deployment

**Package installation** (Debian/Ubuntu):
```bash
sudo apt update
sudo apt install swtpm libtpms-tools
```

**Docker Compose deployment**:
```yaml
version: "3.8"
services:
  swtpm:
    image: ubuntu:24.04
    volumes:
      - swtpm-state:/var/lib/swtpm
    ports:
      - "2321:2321"
    command: >
      bash -c "
        apt-get update && apt-get install -y swtpm libtpms-tools tpm2-tools
        mkdir -p /var/lib/swtpm
        swtpm_setup --tpmstate /var/lib/swtpm --create-ek-cert --create-platform-cert
        swtpm socket --tpmstate dir=/var/lib/swtpm --server type=tcp,port=2321 --flags not-need-init &
        sleep 2
        tpm2_pcrread -T mssim:port=2321
        sleep infinity
      "
    restart: unless-stopped

volumes:
  swtpm-state:
```

**Testing with tpm2-tools against swtpm**:
```bash
# Start swtpm in background
swtpm socket --tpmstate dir=/tmp/mytpm --server type=tcp,port=2321 --flags not-need-init &

# Run tpm2-tools commands against the emulator
tpm2_pcrread -T mssim:port=2321
tpm2_createprimary -C o -c primary.ctx -T mssim:port=2321
tpm2_create -C primary.ctx -G rsa2048 -u pub.key -r priv.key -T mssim:port=2321

# Verify the key was created
tpm2_load -C primary.ctx -u pub.key -r priv.key -c key.ctx -T mssim:port=2321
```

## tpm2-tss: TPM Software Stack Library

**tpm2-tss** (Trusted Software Stack) is the reference implementation of the TCG TPM 2.0 Software Stack specification. It provides the foundational library layer that tpm2-tools and other TPM applications depend on. While not a user-facing tool itself, understanding tpm2-tss is critical for anyone building TPM-integrated applications.

### Architecture Layers

The TCG TPM 2.0 software stack follows a layered architecture:

```
┌─────────────────────────────────────────────────┐
│  Application Layer (your software)               │
├─────────────────────────────────────────────────┤
│  FAPI (Feature API) - High-level API            │
├─────────────────────────────────────────────────┤
│  ESAPI (Enhanced System API) - Medium-level API  │
├─────────────────────────────────────────────────┤
│  SAPI (System API) - Low-level API              │
├─────────────────────────────────────────────────┤
│  TCTI (TPM Command Transmission Interface)      │
├─────────────────────────────────────────────────┤
│  TPM Device (hardware or swtpm emulator)        │
└─────────────────────────────────────────────────┘
```

- **FAPI** — High-level API for common TPM operations (key creation, sealing, attestation) with simplified configuration
- **ESAPI** — Enhanced System API providing direct TPM command access with session management
- **SAPI** — Low-level System API for raw TPM command marshaling
- **TCTI** — Transmission interface handling communication with the TPM (device, socket, or abrmd)

### Building Applications with tpm2-tss

**Install development libraries**:
```bash
sudo apt install libtss2-dev libtss2-fapi-dev pkg-config
```

**Minimal C application using ESAPI**:
```c
#include <tss2/tss2_esys.h>
#include <stdio.h>

int main() {
    ESYS_CONTEXT *esys_ctx = NULL;
    TSS2_RC rc;

    // Initialize ESAPI context
    rc = Esys_Initialize(&esys_ctx, NULL, NULL);
    if (rc != TSS2_RC_SUCCESS) {
        fprintf(stderr, "Esys_Initialize failed: 0x%x\n", rc);
        return 1;
    }

    // Read PCR values
    TPM2B_DIGEST *pcr_values = NULL;
    TPML_PCR_SELECTION *pcr_selection = NULL;
    rc = Esys_PCR_Read(esys_ctx, ESYS_TR_NONE, ESYS_TR_NONE, ESYS_TR_NONE,
                       NULL, NULL, &pcr_values);
    
    Esys_Finalize(&esys_ctx);
    printf("ESAPI initialized and cleaned up successfully\n");
    return 0;
}
```

**Compile and link**:
```bash
gcc -o tpm_app tpm_app.c $(pkg-config --cflags --libs tss2-esys)
```

## Choosing the Right TPM Tool

| Scenario | Recommended Tool | Rationale |
|----------|-----------------|-----------|
| Production TPM key management | tpm2-tools | Direct CLI access to real TPM hardware |
| Automated testing / CI/CD | swtpm | No hardware dependency, fully emulated |
| Building TPM-integrated apps | tpm2-tss | Programmatic library with full API coverage |
| Development environment | swtpm + tpm2-tools | Emulator + CLI for interactive testing |
| Enterprise deployment | tpm2-tools + tpm2-abrmd | Resource manager enables multi-tenant TPM access |
| Remote attestation server | tpm2-tools + tpm2-tss | Full attestation quote generation and verification |

## Why Self-Host TPM Management?

Managing TPM infrastructure in-house gives organizations complete control over their hardware security posture. When TPM operations are handled by cloud providers or third-party services, cryptographic keys, attestation data, and platform integrity measurements pass through external systems — creating additional audit surfaces and compliance complexities.

Self-hosted TPM management ensures that all cryptographic operations happen within your own infrastructure boundary. Keys generated inside the TPM never leave the chip, attestation quotes are verified locally, and the entire chain of trust from hardware root to application layer remains under your direct control.

For organizations subject to regulatory requirements like FIPS 140-2, Common Criteria, or industry-specific standards, having TPM management tools running on-premises simplifies compliance audits. Every TPM operation can be logged, every key creation event can be tracked, and the entire security boundary is physically contained within your datacenter.

Additionally, self-hosted TPM tooling eliminates vendor lock-in. The tpm2-software stack (tpm2-tools and tpm2-tss) works with any TPM 2.0-compliant chip regardless of manufacturer, and swtpm provides a hardware-independent testing environment that works identically across all platforms.

For related hardware security management, see our [IPMI, Redfish, and OpenBMC hardware monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/) and [supply chain security tools](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/).

## FAQ

### What is the difference between tpm2-tools and tpm2-tss?

tpm2-tools is a command-line utility suite that provides user-facing TPM operations like key creation, PCR reading, and attestation. tpm2-tss is the underlying software stack library that tpm2-tools depends on — it implements the TCG TPM 2.0 Software Stack specification and provides APIs (FAPI, ESAPI, SAPI) for applications to communicate with TPM hardware. Think of tpm2-tss as the engine and tpm2-tools as the steering wheel.

### Can I use swtpm in production environments?

swtpm is designed primarily for testing, development, and CI/CD pipelines. It emulates TPM 2.0 functionality in software, meaning the cryptographic keys it generates are NOT protected by hardware boundaries. For production key storage and attestation, you need real TPM hardware. However, swtpm is production-grade for its intended use case — automated testing of TPM-dependent applications without requiring physical TPM chips on every test machine.

### How do I verify my system has a TPM 2.0 chip?

Run `dmesg | grep -i tpm` to check kernel messages for TPM detection. Alternatively, run `ls -la /dev/tpm*` to see if TPM device nodes exist. The command `tpm2_pcrread` (from tpm2-tools) will return PCR values if a TPM is present and accessible. On systems with TPM 2.0, you should see `/dev/tpmrm0` (resource manager device) available.

### What is the TPM Resource Manager (tpm2-abrmd) and why do I need it?

The TPM Access Broker and Resource Manager (tpm2-abrmd) allows multiple applications to share a single TPM chip safely. Without it, only one process can access the TPM at a time. The resource manager handles context switching, session management, and resource allocation, enabling containerized and multi-tenant TPM access. It's essential for Docker deployments where multiple containers need TPM operations.

### How does TPM sealing work and when should I use it?

TPM sealing encrypts data such that it can only be decrypted when specific Platform Configuration Register (PCR) values match the state at sealing time. If the system boot process changes (different kernel, modified initrd, changed BIOS settings), the PCR values change and the sealed data becomes inaccessible. Use sealing for: disk encryption key protection, configuration file encryption tied to known-good boot states, and automated decryption in trusted boot chains.

### Is swtpm state portable between different host machines?

Yes. swtpm stores its complete TPM state (including all keys, NV indices, and PCR values) in a directory on the host filesystem. You can copy this directory to another machine and start swtpm with `--tpmstate dir=/path/to/copied/state` — the TPM will resume with all previous keys and measurements intact. This is useful for migrating test environments or creating pre-provisioned TPM templates for CI/CD pipelines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TPM Management: tpm2-tools vs swtpm vs tpm2-tss Guide",
  "description": "Compare open-source TPM 2.0 management tools for hardware security, key storage, and attestation. Deployment guides with Docker compose configs.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
