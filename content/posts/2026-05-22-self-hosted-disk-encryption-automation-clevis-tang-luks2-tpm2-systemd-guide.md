---
title: "Self-Hosted Network-Bound Disk Encryption: Clevis/Tang vs LUKS2+TPM2 vs systemd-cryptenroll"
date: "2026-05-22"
tags: ["encryption", "security", "self-hosted", "luks", "disk", "linux"]
draft: false
description: "Compare self-hosted disk encryption automation: Clevis/Tang NBDE, LUKS2 with TPM2, and systemd-cryptenroll. Full configs, deployment guides, and security analysis."
---

Full-disk encryption with LUKS (Linux Unified Key Setup) protects data at rest, but introduces a critical operational challenge: how to unlock encrypted volumes at boot without manual passphrase entry? For headless servers, data centers, and edge deployments, automated disk unlocking is essential — but it must not compromise security.

Three mainstream approaches solve this problem on Linux: Clevis with Tang (Network-Bound Disk Encryption, NBDE), LUKS2 with TPM2 (Trusted Platform Module) binding, and systemd-cryptenroll (systemd's native LUKS2 key management). Each offers a different security model, infrastructure requirements, and operational characteristics.

This guide compares all three approaches, covering architecture, configuration, security trade-offs, and production deployment patterns.

## Understanding Automated Disk Unlocking

LUKS encrypts block devices with a master key protected by one or more keyslots. Each keyslot contains the master key encrypted with a different passphrase or key. Automated unlocking works by storing a key in a location the system can access at boot:

- **Network-based** (Clevis/Tang): Key is stored on a network server (Tang), released only when the client proves its identity
- **Hardware-based** (TPM2): Key is sealed to the TPM chip, released only when platform state matches expected PCR values
- **Local-based** (systemd-cryptenroll): Key is stored locally in LUKS2 header, protected by systemd's credential system

The security model of each approach differs fundamentally: NBDE protects against physical theft of the server (attacker needs network access to Tang), TPM2 protects against disk cloning (key is bound to specific hardware), and systemd-cryptenroll simplifies management but stores keys locally.

## Clevis and Tang (NBDE)

Clevis is a pluggable framework for automated decryption, and Tang is a server that implements the NBDE protocol. Together, they enable servers to unlock encrypted volumes automatically by fetching keys from a Tang server over the network.

**GitHub**: `latchset/clevis` | **GitHub**: `latchset/tang` | **Stars**: 160+ / 240+ | **Language**: C

### Architecture

Clevis runs on the client (encrypted server) as a dracut module that contacts the Tang server during boot. Tang holds the key shares and releases them when the client presents a valid identity proof. The protocol uses asymmetric cryptography (JWE/JWS) so Tang never learns the client's decryption key.

### Tang Server Deployment

```yaml
version: "3.8"

services:
  tang-server:
    image: docker.io/season/tang:latest
    container_name: tang-server
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./tang-db:/var/db/tang
    environment:
      - THRESHOLD=1
    networks:
      - nbde-net

networks:
  nbde-net:
    driver: bridge
```

### Client Configuration

Register a Tang key on an encrypted LUKS volume:

```bash
# Bind LUKS slot to Tang server
clevis bind luks -d /dev/sda1 tang url='http://tang-server.example.com'

# Verify the binding
clevis luks list -d /dev/sda1

# Regenerate initramfs to include Clevis
dracut -f
```

For multiple Tang servers (high availability), use Shamir's Secret Sharing:

```bash
clevis bind luks -d /dev/sda1 sss   '{"t":1,"pins":{"tang":[{"url":"http://tang1.example.com"},{"url":"http://tang2.example.com"}]}}'
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| Zero-touch boot unlock | Yes |
| Hardware dependency | None (network only) |
| Centralized key management | Yes (Tang server) |
| Multi-server HA | Yes (SSS threshold) |
| Physical theft protection | Yes (needs network + Tang) |
| Disk clone protection | No (key is network-accessible) |
| Offline boot | No (requires Tang at boot) |
| Key rotation | Yes (Tang key rotation) |

## LUKS2 with TPM2

LUKS2 (the current LUKS version) supports TPM2-bound keys, sealing the disk encryption key to the Trusted Platform Module's Platform Configuration Registers (PCRs). The key is only released when the system boots with an expected firmware/kernel state.

### Architecture

TPM2 sealing binds the LUKS key to specific PCR values (measured boot state). If the bootloader, kernel, or initramfs changes, PCR values change and the TPM refuses to release the key — preventing offline attacks on modified systems.

### Setup Commands

```bash
# Check TPM2 availability
tpm2_pcrread

# Enroll TPM2-bound key on LUKS volume
systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=0,7 /dev/sda1

# Verify enrollment
systemd-cryptenroll /dev/sda1

# The system will use TPM2 automatically at boot
# via systemd-cryptsetup
```

For more granular control, use `tpm2-tools` directly:

```bash
# Create a primary key in TPM
tpm2_createprimary -c primary.ctx

# Seal the LUKS passphrase to PCR 7 (boot loader)
tpm2_create -C primary.ctx -p PCR:7 -u seal.pub -r seal.priv -i /tmp/luks-passphrase

# Load the sealed key
tpm2_load -C primary.ctx -u seal.pub -r seal.priv -c seal.ctx

# Unseal to verify
tpm2_unseal -c seal.ctx
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| Zero-touch boot unlock | Yes |
| Hardware dependency | Yes (requires TPM2 chip) |
| Centralized key management | No (per-device) |
| Multi-server HA | N/A (local hardware) |
| Physical theft protection | Yes (key bound to TPM) |
| Disk clone protection | Yes (TPM is hardware-unique) |
| Offline boot | Yes (no network needed) |
| Key rotation | Manual (re-enroll) |

## systemd-cryptenroll

`systemd-cryptenroll` is systemd's native tool for managing LUKS2 keyslots. It supports TPM2, PKCS#11, FIDO2, and recovery key enrollment through a unified interface, integrated with systemd-cryptsetup for automatic unlocking.

**Part of**: `systemd` | **Version**: 248+ | **Language**: C

### Architecture

systemd-cryptenroll manages LUKS2 keyslots directly, storing metadata about key types (TPM2, PKCS#11, FIDO2) in the LUKS2 header. At boot, systemd-cryptsetup reads this metadata and attempts each enrolled key type automatically.

### Enrollment Commands

```bash
# Enroll a recovery key (printed on screen)
systemd-cryptenroll --recovery-key /dev/sda1

# Enroll a PKCS#11 token (smart card)
systemd-cryptenroll --pkcs11-token-uri=pkcs11: /dev/sda1

# Enroll a FIDO2 security key
systemd-cryptenroll --fido2-device=auto /dev/sda1

# List all enrolled keys
systemd-cryptenroll /dev/sda1

# Wipe a specific keyslot
systemd-cryptenroll --wipe-slot=4 /dev/sda1
```

### /etc/crypttab Configuration

```
# Auto-unlock with TPM2 at boot
data /dev/sda1 - tpm2-device=auto,luks

# Fallback to passphrase if TPM2 fails
boot /dev/nvme0n1p3 - tpm2-device=auto,headless=true
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| Zero-touch boot unlock | Yes (with TPM2/FIDO2) |
| Hardware dependency | Optional (TPM2/FIDO2/PKCS#11) |
| Centralized key management | No (per-device) |
| Multi-server HA | N/A (local) |
| Physical theft protection | Partial (FIDO2 requires key) |
| Disk clone protection | Yes (with TPM2) |
| Offline boot | Yes |
| Key rotation | Easy (enroll/wipe commands) |

## Security Comparison

| Criterion | Clevis/Tang NBDE | LUKS2+TPM2 | systemd-cryptenroll |
|-----------|-----------------|------------|---------------------|
| Key storage | Tang server (remote) | TPM2 chip (hardware) | LUKS2 header (local) |
| Attack surface | Network + Tang server | TPM2 firmware | Local disk header |
| Brute-force resistance | Cryptographic (JWE) | Hardware-bound | Passphrase quality |
| Key escrow | Tang holds key shares | No escrow possible | No escrow (unless enrolled) |
| Forensic analysis | Tang logs all accesses | TPM2 audit logs | systemd journal logs |
| Disaster recovery | Tang key backup + SSS | Recovery key required | Recovery key printed |
| Best for | Fleet management | Single-server security | Simplified operations |

## Deployment Recommendations

**Use Clevis/Tang NBDE** when managing a fleet of servers where centralized key management is essential. Tang provides audit logs of all key releases, and Shamir's Secret Sharing enables high-availability key distribution. This approach is common in cloud and data center environments.

**Use LUKS2+TPM2** for single-server deployments where physical security matters most. TPM2 binding ensures that even if an attacker physically removes the disk, they cannot decrypt it without the specific TPM chip. This is ideal for edge servers and on-premise hardware.

**Use systemd-cryptenroll** for simplified operations, especially when combining multiple key types (TPM2 primary + FIDO2 fallback + recovery key). The unified enrollment interface and systemd integration make it the most operator-friendly option for mixed environments.

## Why Self-Host Disk Encryption Infrastructure?

Managing your own disk encryption infrastructure ensures:

- **Complete data control** — Encryption keys never leave your infrastructure. NBDE Tang servers run on your hardware, TPM2 keys are device-bound, and recovery keys are stored in your vault.
- **Compliance requirements** — Many regulations (PCI-DSS, HIPAA, GDPR) mandate encryption at rest with documented key management. Self-hosted NBDE and TPM2 solutions provide auditable key access logs.
- **No vendor dependency** — Cloud provider encryption (AWS EBS encryption, GCP CMEK) ties your data to specific platforms. LUKS-based encryption is portable across any Linux system.
- **Fleet-scale automation** — Clevis/Tang enables automated disk provisioning across hundreds of servers without manual passphrase entry or hardware token distribution.
- **Measured boot integration** — TPM2-bound encryption integrates with Secure Boot and measured boot chains, creating a verifiable trust chain from firmware to filesystem.

For server security auditing workflows, see our [Lynis vs OpenSCAP vs Goss guide](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide-2026/). For container-level security, the [AppArmor management tools comparison](../2026-05-28-self-hosted-apparmor-management-tools-aagenprof-aalogprof-utils-guide/) covers Linux security module administration.

## FAQ

### What is the difference between Clevis and Tang?

Clevis is the client-side framework that handles automated decryption on the encrypted server. Tang is the server-side component that stores and releases key shares. They work together: Clevis contacts Tang during boot, Tang verifies the client identity and releases the key share, and Clevis uses it to unlock the LUKS volume.

### Can I use NBDE without an internet connection?

Yes, but the Tang server must be reachable on your local network. NBDE requires network connectivity between the encrypted server and the Tang server at boot time. If the network is unavailable, the server will fall back to manual passphrase entry (if configured).

### What happens if the Tang server is compromised?

If an attacker compromises the Tang server, they can potentially release key shares to unauthorized clients. However, Shamir's Secret Sharing (SSS) mitigates this risk: with a threshold of 2 out of 3 Tang servers, a single compromised server cannot unlock volumes alone. Always deploy multiple Tang servers with SSS.

### Does TPM2 protect against cold-boot attacks?

TPM2 provides protection against disk removal and offline attacks, but cold-boot attacks (reading RAM contents shortly after power-off) can potentially extract encryption keys from memory. For maximum security, combine TPM2 binding with RAM scrubbing on shutdown.

### Can I combine multiple unlocking methods?

Yes. LUKS2 supports multiple keyslots simultaneously. You can enroll TPM2 as the primary unlock method, a FIDO2 key as a fallback, and a recovery passphrase for emergency access. systemd-cryptenroll makes this straightforward with its `--tpm2-device`, `--fido2-device`, and `--recovery-key` options.

### Is NBDE suitable for laptops?

NBDE is generally not recommended for laptops because it requires network connectivity to the Tang server at boot. If a laptop boots outside the network (e.g., at home or on the road), it cannot unlock automatically. TPM2 or FIDO2-based unlocking via systemd-cryptenroll is better suited for mobile devices.

### How do I rotate Tang server keys?

Tang key rotation is automatic — Tang generates new key pairs periodically. Existing Clevis bindings continue to work with old keys during a transition period. To force rotation, restart the Tang service (keys are stored in `/var/db/tang`). For production, use multiple Tang servers with SSS to avoid downtime during rotation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network-Bound Disk Encryption: Clevis/Tang vs LUKS2+TPM2 vs systemd-cryptenroll",
  "description": "Compare self-hosted disk encryption automation: Clevis/Tang NBDE, LUKS2 with TPM2, and systemd-cryptenroll. Full configs, deployment guides, and security analysis.",
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
