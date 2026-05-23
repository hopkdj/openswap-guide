---
title: "Self-Hosted Linux Secure Boot Management — sbctl, shim, and pesign Guide"
date: "2026-05-23"
tags: ["linux", "security", "secure-boot", "uefi", "kernel"]
draft: false
---

**Secure Boot** is a UEFI firmware feature that verifies the cryptographic signature of every component in the boot chain — from the bootloader to the kernel to kernel modules. On self-hosted servers, Secure Boot provides a critical defense against bootkits, rootkits, and unauthorized kernel modifications.

However, the default Secure Boot setup (Microsoft-signed keys) only boots kernels signed by major distributions. For **custom kernels, out-of-tree modules, or self-compiled software**, you need to manage your own Secure Boot keys. This guide compares three open-source tools for this purpose: **sbctl**, **shim**, and **pesign**.

## Understanding Secure Boot

Secure Boot relies on a chain of trust anchored in UEFI firmware variables:

1. **Platform Key (PK)** — the root of trust; only the PK owner can update other keys
2. **Key Exchange Key (KEK)** — used to update the signature database
3. **Signature Database (db)** — contains allowed signing keys
4. **Forbidden Signature Database (dbx)** — contains revoked keys

When Secure Boot is enabled, the firmware checks each boot component against the `db`. If a component is signed by a key in `db`, it boots. Otherwise, it is rejected.

### Why Self-Manage Secure Boot Keys?

- **Custom kernels** — compile your own kernel without relying on distribution signatures
- **Out-of-tree drivers** — load proprietary or custom kernel modules (ZFS, NVIDIA, VirtualBox)
- **Supply chain verification** — ensure only your signed code runs on your hardware
- **Compliance requirements** — meet security standards requiring boot integrity verification
- **Tamper detection** — detect unauthorized boot-level modifications

## Comparing Secure Boot Tools

### sbctl — Secure Boot Key Manager

**sbctl** (⭐2,138) is a modern, user-friendly Secure Boot key management tool written in Go. It handles the entire lifecycle: generating keys, enrolling them in UEFI, and signing kernels and modules.

**Key features:**
- Simple CLI: `sbctl create-keys`, `sbctl enroll-keys`, `sbctl sign`
- Automatic kernel and module signing
- Checks Secure Boot status with `sbctl status`
- Supports TPM-based key sealing
- Written in Go — no C dependencies
- Active development on GitHub

**Best for:** Single-server setups, desktop Linux users, administrators who want a simple CLI workflow.

### shim — UEFI First-Stage Bootloader

**shim** (⭐1,066) is a minimal UEFI bootloader developed by Red Hat. It serves as a **first-stage bootloader** that validates the second-stage bootloader (GRUB, systemd-boot) against enrolled keys. shim is the foundation of Secure Boot on most Linux distributions.

**Key features:**
- Minimal, auditable codebase (designed for security review)
- Machine Owner Key (MOK) management for user-enrolled keys
- Compatible with all major Linux distributions
- Supports certificate-based verification
- Used by Ubuntu, Fedora, RHEL, and SUSE

**Best for:** Distribution maintainers, multi-boot setups, environments requiring MOK-based key enrollment.

### pesign — PE Signature Utility

**pesign** (⭐128) is a command-line tool for signing and verifying **PE (Portable Executable)** files — the format used for UEFI boot components. It operates at a lower level than sbctl or shim, providing fine-grained control over the signing process.

**Key features:**
- Sign and verify individual PE files (kernels, bootloaders, drivers)
- Certificate management for signing keys
- Compatible with both EFI and PE file formats
- Used by Red Hat and Fedora for kernel module signing
- Low-level, scriptable interface

**Best for:** Automated signing pipelines, custom build systems, administrators who need programmatic control over the signing process.

## Comparison Table

| Feature | sbctl | shim | pesign |
|---------|-------|------|--------|
| **Primary role** | Key management + signing | First-stage bootloader | PE file signing |
| **GitHub stars** | 2,138 | 1,066 | 128 |
| **Language** | Go | C | C |
| **Key generation** | ✅ Built-in | ❌ (uses existing) | ❌ (uses existing) |
| **Key enrollment** | ✅ One-step | ✅ MOK enrollment | ❌ Manual |
| **Kernel signing** | ✅ Automatic | ❌ (delegates) | ✅ Manual |
| **Module signing** | ✅ Automatic | ❌ | ✅ Manual |
| **Status checking** | ✅ `sbctl status` | ❌ | ❌ |
| **TPM integration** | ✅ Yes | ❌ | ❌ |
| **Ease of use** | High | Medium | Low |
| **Automation-friendly** | ✅ Good | ⚠️ Moderate | ✅ Good |
| **Distribution support** | Arch, Fedora, openSUSE | All major distros | RHEL, Fedora |

## Installation and Setup

### sbctl

```bash
# Arch Linux
pacman -S sbctl

# Fedora
dnf install sbctl

# Build from source
git clone https://github.com/Foxboron/sbctl.git
cd sbctl
make
make install

# Create and enroll keys
sudo sbctl create-keys
sudo sbctl enroll-keys

# Sign your kernel
sudo sbctl sign -s /boot/vmlinuz-linux
sudo sbctl sign /boot/EFI/Linux/arch-linux.efi

# Check status
sbctl status
```

### shim

```bash
# Ubuntu/Debian
apt install -y shim-signed shim-unsigned

# Fedora
dnf install -y shim

# Enroll a Machine Owner Key (MOK)
sudo mokutil --import /path/to/your-key.der
# Reboot and follow the MOK enrollment wizard
```

### pesign

```bash
# Fedora/RHEL
dnf install -y pesign

# Build from source
git clone https://github.com/rhboot/pesign.git
cd pesign
make

# Generate a signing certificate
pesign -n /etc/pki/pesign -c "My Signing Key" -i
pesign-client -c "My Signing Key" -a

# Sign a kernel
pesign -i /boot/vmlinuz -o /boot/vmlinuz-signed -c "My Signing Key" -s

# Verify a signed file
pesign -i /boot/vmlinuz-signed -S
```

## Docker-Based Signing Pipeline

For automated kernel/module signing in CI/CD pipelines:

```yaml
version: "3.8"
services:
  secure-boot-signer:
    image: fedora:40
    volumes:
      - ./keys:/keys
      - ./output:/output
      - ./kernels:/kernels
    command: |
      bash -c '
        dnf install -y pesign sbsigntools

        # Import signing key
        pesign -n /keys/pesign-db -c "CI Signing Key" -i

        # Sign all kernels in the input directory
        for kernel in /kernels/vmlinuz-*; do
          basename=$$(basename $$kernel)
          pesign -i $$kernel -o /output/$$basename -c "CI Signing Key" -s
          echo "Signed: $$basename"
        done
      '
    restart: "no"
```

## Why Self-Host with Custom Secure Boot Keys?

Running your own Secure Boot infrastructure ensures that only **your code** executes on your hardware. For self-hosted servers, this means:

- **Custom kernel builds** with specific patches or features compile and boot without disabling Secure Boot
- **Third-party kernel modules** (ZFS, NVIDIA drivers, WireGuard) can be signed with your own key
- **Supply chain integrity** — you control exactly what boots, eliminating reliance on distribution signing keys that may change or be compromised
- **Compliance** — many security frameworks (SOC 2, ISO 27001) require boot integrity controls

For kernel security auditing, check our [Linux kernel security guide](../2026-05-23-self-hosted-linux-kernel-security-auditing-kconfig-hardened-check-checksec/). For hardware inventory, see our [Linux hardware discovery guide](../2026-05-23-self-hosted-linux-hardware-inventory-dmidecode-lshw-hwinfo-guide/).

## Secure Boot Best Practices

Implementing Secure Boot on self-hosted infrastructure requires more than just enrolling keys. Follow these best practices:

### Key Management

- **Backup your keys** — store PK, KEK, and db keys in a secure offline location (encrypted USB, hardware security module). Losing your PK requires resetting to Setup Mode, which temporarily disables Secure Boot.
- **Rotate keys periodically** — update signing keys on a regular schedule (quarterly or annually) and re-sign all boot components.
- **Use hardware-backed keys** — if your server has a TPM, use `sbctl`'s TPM integration to seal keys to hardware.

### Module Signing Workflow

For out-of-tree kernel modules, establish a signing workflow:

```bash
# Create a signing script
cat > /usr/local/bin/sign-modules.sh << 'EOF'
#!/bin/bash
KERNEL_VERSION=$(uname -r)
MODULES=$(find /lib/modules/$KERNEL_VERSION/extra -name "*.ko")

for mod in $MODULES; do
    if ! sbctl verify "$mod" 2>/dev/null; then
        sbctl sign "$mod"
        echo "Signed: $mod"
    fi
done
EOF

chmod +x /usr/local/bin/sign-modules.sh

# Run after kernel updates
sudo /usr/local/bin/sign-modules.sh
```

### Monitoring Secure Boot Status

```bash
# Check if Secure Boot is enabled
sbctl status

# Verify a specific file is signed
sbctl verify /boot/vmlinuz-linux
sbctl verify /lib/modules/$(uname -r)/extra/zfs.ko

# List all enrolled keys
sbctl list-enrolled-keys
```


## FAQ

### What happens if I lose my Secure Boot keys?
If you lose your Platform Key (PK), you can reset Secure Boot to Setup Mode through your UEFI firmware settings. This clears all enrolled keys, allowing you to create new ones. However, any signed boot components will need to be re-signed with the new keys.

### Can I use sbctl with any Linux distribution?
sbctl works best on distributions that do not pre-enroll Secure Boot keys (Arch Linux, openSUSE). On distributions that already use Secure Boot (Ubuntu, Fedora), you may need to remove existing keys first or use shim's MOK enrollment instead.

### Is Secure Boot necessary for servers?
Secure Boot provides protection against boot-level malware and unauthorized kernel modifications. For internet-facing servers, it is a valuable defense-in-depth measure. For isolated or air-gapped servers, the risk is lower but the protection is still beneficial.

### Does Secure Boot prevent running unsigned kernel modules?
Yes. When Secure Boot is enabled, all kernel modules must be signed by a key in the `db`. Unsigned modules will fail to load with a "Required key not available" error. Use `sbctl sign` or `pesign` to sign your custom modules.

### Can I disable Secure Boot if I need to?
Yes. Secure Boot can be disabled from the UEFI firmware settings at any time. However, this removes boot-level verification protection. For self-hosted infrastructure, it is recommended to keep Secure Boot enabled and manage your own keys instead.

### How do I sign kernel modules for Secure Boot?
Use `sbctl sign-file` or `pesign` to sign individual kernel modules:

```bash
# With sbctl
sudo sbctl sign-file /lib/modules/$(uname -r)/extra/zfs.ko

# With pesign
pesign -i zfs.ko -o zfs-signed.ko -c "My Signing Key" -s
```

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Secure Boot Management — sbctl, shim, and pesign Guide",
  "description": "Compare open-source Secure Boot management tools — sbctl for simple key management, shim for MOK-based enrollment, and pesign for automated PE file signing pipelines.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
