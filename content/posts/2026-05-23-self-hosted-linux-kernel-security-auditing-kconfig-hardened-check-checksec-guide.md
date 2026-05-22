---
title: "Self-Hosted Linux Kernel Security Auditing: kconfig-hardened-check vs checksec.sh"
date: "2026-05-23"
tags: ["linux", "security", "kernel", "hardening", "auditing", "compliance", "self-hosted"]
draft: false
---

Linux kernel security hardening is a multi-layered process that spans compile-time configuration, runtime sysctl parameters, and binary-level protection features. While distribution kernels come with reasonable defaults, self-hosted server administrators often need to verify that their systems meet specific security standards — whether for compliance, hardening best practices, or threat model requirements.

This guide compares two essential Linux security auditing tools — **kconfig-hardened-check** and **checksec.sh** — that help you verify kernel hardening configuration and binary security features across your infrastructure.

## Understanding Linux Security Layers

Linux security hardening operates at three distinct levels:

1. **Kernel compile-time configuration** (`.config`): Options like `CONFIG_STRICT_DEVMEM`, `CONFIG_SECURITY_YAMA`, and `CONFIG_X86_SMAP` are set when the kernel is built. These cannot be changed without recompiling.
2. **Runtime kernel parameters** (`sysctl`): Settings like `kernel.kptr_restrict`, `kernel.dmesg_restrict`, and `kernel.yama.ptrace_scope` can be tuned at runtime via `/etc/sysctl.conf`.
3. **Binary protection features**: Executable files can have PIE (Position Independent Executable), NX (No-Execute stack), RELRO (Relocation Read-Only), and stack canary protections — each mitigating specific exploitation techniques.

The tools discussed here focus on levels 1 and 3, providing automated verification against established hardening baselines.

## Tool Comparison Overview

| Feature | kconfig-hardened-check | checksec.sh |
|---------|----------------------|-------------|
| **Focus** | Kernel `.config` audit | Binary security features |
| **GitHub Stars** | 2,081+ | 2,326+ |
| **Last Updated** | May 2026 | May 2026 |
| **Language** | Python | Bash |
| **Input** | Kernel `.config` file | Binary/executable file |
| **Output Format** | Terminal report, JSON | Terminal report, CSV |
| **Hardening Standard** | KSPP (Kernel Self-Protection Project) | Binary exploit mitigations |
| **Docker Support** | Yes (Python image) | Yes (Alpine image) |
| **Root Required** | No (needs `.config` file) | No (read-only analysis) |
| **Compliance Mapping** | KSPP recommendations | N/A |
| **Best For** | Kernel config auditing | Binary security verification |

## kconfig-hardened-check: Kernel Configuration Auditor

**kconfig-hardened-check** is a Python tool that compares a Linux kernel `.config` file against the Kernel Self-Protection Project (KSPP) recommended hardening settings. It identifies which security options are enabled, disabled, or missing, and provides a pass/fail assessment for each check.

### Key Characteristics

- **KSPP-aligned**: Based on the Kernel Self-Protection Project's recommended kernel hardening settings
- **Comprehensive**: Checks 100+ kernel configuration options across categories (memory safety, access control, debugging, filesystem, networking)
- **Architecture-aware**: Supports x86_64, ARM64, ARM, RISC-V, and other architectures with different hardening recommendations
- **Version-aware**: Adapts checks based on kernel version (newer kernels have more available options)
- **Actively maintained**: 2,081+ GitHub stars, regular updates for new kernel features

### Installation

```bash
# pip (recommended)
pip install kconfig-hardened-check

# From source
git clone https://github.com/a13xp0p0v/kconfig-hardened-check
cd kconfig-hardened-check
pip install -r requirements.txt
```

### Common Usage Patterns

```bash
# Check current running kernel's config
kconfig-hardened-check -c /proc/config.gz

# Check a specific kernel .config file
kconfig-hardened-check -c /boot/config-$(uname -r)

# Check with architecture specification
kconfig-hardened-check -c /boot/config-$(uname -r) -a x86_64

# JSON output (for automation/CI)
kconfig-hardened-check -c /boot/config-$(uname -r) -m json

# Check against custom policy
kconfig-hardened-check -c /boot/config-$(uname -r) -p my-policy.json
```

### Example Output

```bash
$ kconfig-hardened-check -c /boot/config-$(uname -r)

[+] Config file /boot/config-6.8.0-31-generic
[+] Architecture: x86_64
[+] Kernel version: 6.8.0

[+] 100 security checks performed

[+] 87 checks passed (87.0%)
[+] 5 checks FAILED
[+] 8 checks have no value (N/A for this kernel version)

--- Failed checks ---
[FAIL] CONFIG_BUG: is not set
       → Recommended: is set
       → Reason: Kernel BUG() provides runtime self-testing

[FAIL] CONFIG_STATIC_USERMODEHELPER: is not set
       → Recommended: is set
       → Reason: Prevents usermode helper exploitation

--- Warning checks ---
[WARN] CONFIG_SECURITY_LOCKDOWN_LSM: is not set
       → Recommended: is set
       → Reason: Locks down kernel features in secure boot environments
```

### Docker Usage

```yaml
version: "3.8"
services:
  kconfig-check:
    image: docker.io/library/python:3.12-slim
    container_name: kconfig-hardened-check
    restart: "no"
    command: >
      bash -c "
        pip install kconfig-hardened-check &&
        kconfig-hardened-check -c /boot/config.gz
      "
    volumes:
      - /proc/config.gz:/boot/config.gz:ro
      - /boot:/boot:ro
```

**Note**: `/proc/config.gz` is only available if the kernel was compiled with `CONFIG_IKCONFIG_PROC=y`. If not available, read the config from `/boot/config-$(uname -r)`.

## checksec.sh: Binary Security Feature Auditor

**checksec.sh** is a Bash script that audits Linux executables and the kernel for security hardening features. It checks whether binaries are compiled with exploit mitigations (PIE, NX, RELRO, stack canaries, FORTIFY_SOURCE) and whether the kernel has relevant protections enabled.

### Key Characteristics

- **Binary-focused**: Analyzes compiled executables for exploit mitigation features
- **Kernel checks**: Also reports on kernel-level protections (ASLR, dmesg_restrict, ptrace_scope)
- **Recursive scanning**: Can scan entire directories for binaries with weak protections
- **Multiple output formats**: Text, CSV, JSON for integration with CI/CD pipelines
- **Widely adopted**: 2,326+ GitHub stars, included in many security toolkits

### Installation

```bash
# From GitHub
git clone https://github.com/slimm609/checksec.sh
cd checksec.sh
chmod +x checksec

# Debian/Ubuntu (may be outdated)
sudo apt install checksec

# RHEL/CentOS/Fedora
sudo dnf install checksec
```

### Common Usage Patterns

```bash
# Check a single binary
./checksec --file=/usr/bin/sshd

# Check all binaries in a directory
./checksec --dir=/usr/bin

# Check kernel security features
./checksec --kernel

# Check all loaded kernel modules
./checksec --proc=kmods

# Check running processes
./checksec --proc=all

# Check a specific process by PID
./checksec --proc=1234

# CSV output (for spreadsheet/automation)
./checksec --dir=/usr/sbin --output=csv

# JSON output
./checksec --dir=/usr/sbin --output=json
```

### Example Output: Binary Check

```bash
$ ./checksec --file=/usr/sbin/sshd

RELRO           STACK CANARY    NX            PIE             RPATH      RUNPATH    FORTIFY   Fortified  Fortifiable  FILE
Full RELRO      Canary found    NX enabled    PIE enabled     No RPATH   No RUNPATH  Yes       42          85          /usr/sbin/sshd
```

### Example Output: Kernel Check

```bash
$ ./checksec --kernel

Linux Kernel Hardening Check Results:

ASLR:                     Full randomization (0x2)
Dmesg Restrict:           Enabled (1)
kptr Restrict:            Enabled (2)
Yama Ptrace Scope:        No ptrace (3)
Kernel Lockdown:          integrity
Seccomp:                  Enabled
SMEP:                     Enabled
SMAP:                     Enabled
KASLR:                    Enabled
Page Table Isolation:      Enabled
```

### Docker Usage

```yaml
version: "3.8"
services:
  checksec:
    image: docker.io/library/alpine:latest
    container_name: checksec-scan
    restart: "no"
    command: >
      sh -c "
        apk add --no-cache bash file procps &&
        git clone --depth 1 https://github.com/slimm609/checksec.sh &&
        cd checksec.sh &&
        ./checksec --kernel
      "
    volumes:
      - /proc:/proc:ro
      - /usr/bin:/usr/bin:ro
      - /usr/sbin:/usr/sbin:ro
```

## Integrating Both Tools Into a Security Pipeline

For comprehensive Linux security auditing, use both tools together:

1. **kconfig-hardened-check** verifies that your kernel was compiled with recommended hardening options — this is a **static check** that applies to the kernel build itself.
2. **checksec.sh** verifies that your running system has kernel protections active and that critical binaries (SSH daemon, web servers, database engines) are compiled with exploit mitigations — this is a **runtime check** on the actual deployed system.

### Combined Audit Script

```bash
#!/bin/bash
# Combined kernel + binary security audit

echo "=== Kernel Configuration Audit ==="
kconfig-hardened-check -c /boot/config-$(uname -r) -m json > /var/log/kconfig-audit.json

echo "=== Kernel Runtime Check ==="
checksec --kernel > /var/log/checksec-kernel.log

echo "=== Critical Binary Audit ==="
for binary in /usr/sbin/sshd /usr/sbin/nginx /usr/sbin/postgres /usr/sbin/mysqld; do
    if [ -f "$binary" ]; then
        checksec --file="$binary" >> /var/log/checksec-binaries.log
    fi
done

echo "=== Audit Complete ==="
```

### CI/CD Integration

For automated builds that compile custom kernels or package binaries:

```yaml
# GitHub Actions example
jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Check kernel config
        run: |
          pip install kconfig-hardened-check
          kconfig-hardened-check -c .config -m json -o audit-results.json

      - name: Check binary protections
        run: |
          git clone --depth 1 https://github.com/slimm609/checksec.sh
          ./checksec.sh/checksec --dir=./build/ --output=json > binary-audit.json
```

## Why Self-Host Your Security Auditing?

**Infrastructure visibility and compliance readiness**: Regular kernel and binary security audits provide documented evidence of your hardening posture. For SOC 2, ISO 27001, or internal security reviews, running kconfig-hardened-check and checksec.sh on a scheduled basis generates verifiable, timestamped reports that demonstrate proactive security management.

**Cost savings through proactive hardening**: Identifying missing kernel hardening options or binaries without exploit mitigations before a security incident occurs is far cheaper than responding to a breach. Tools like checksec.sh can scan hundreds of binaries in seconds, revealing which critical services lack PIE, RELRO, or stack canary protections.

**No vendor lock-in or licensing fees**: Both tools are open-source, freely available, and run entirely on your infrastructure. There are no cloud dependencies, no subscription fees, and no data leaving your servers. This makes them suitable for air-gapped networks and high-security environments where external scanning services are prohibited.

**Customizable audit policies**: kconfig-hardened-check supports custom policy files, allowing you to define organization-specific kernel hardening requirements beyond the KSPP baseline. checksec.sh can be integrated into CI/CD pipelines to gate releases based on binary security feature requirements.

For related reading on Linux security frameworks, see our [Linux MAC frameworks guide](../2026-05-16-self-hosted-linux-mac-selinux-apparmor-smack-guide/) covering SELinux, AppArmor, and Smack. If you're interested in server security auditing tools, check our [Lynis vs OpenSCAP comparison](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide/). For comprehensive security monitoring, our [Linux audit framework guide](../2026-05-16-self-hosted-linux-audit-framework-auditd-goaudit-auditbeat-guide/) covers auditd, goaudit, and auditbeat for system call monitoring.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Kernel Security Auditing: kconfig-hardened-check vs checksec.sh",
  "description": "Compare kconfig-hardened-check and checksec.sh for auditing Linux kernel hardening and binary exploit mitigations in self-hosted infrastructure.",
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

## FAQ

### What is the difference between kconfig-hardened-check and checksec.sh?

kconfig-hardened-check audits the kernel's compile-time configuration (`.config` file) against the KSPP recommended hardening settings. checksec.sh audits running binaries and the active kernel for exploit mitigation features (PIE, NX, RELRO, ASLR). They operate at different layers — kconfig-hardened-check verifies what the kernel was built with, while checksec.sh verifies what protections are actually active on the deployed system.

### Do I need to recompile my kernel to fix failed kconfig-hardened-check results?

For kernel configuration options (`.config`), yes — failed checks indicate options that need to be set at compile time. However, many hardening settings can be enforced at runtime via `sysctl` (e.g., `kernel.kptr_restrict`, `kernel.yama.ptrace_scope`). Use checksec.sh to identify runtime protections that can be enabled without recompilation.

### How often should I run these security audits?

Run kconfig-hardened-check whenever you update or change your kernel — each new kernel version may have different default configuration options. Run checksec.sh as part of your regular security audit cycle (weekly or monthly) and after any system update that replaces binaries. For CI/CD pipelines, integrate both tools into the build process to catch regressions automatically.

### Can these tools detect malware or rootkits?

No — neither tool is designed for malware or rootkit detection. kconfig-hardened-check verifies kernel configuration options, and checksec.sh verifies binary protection features. For malware detection, use dedicated tools like rkhunter, chkrootkit, or OSSEC. For file integrity monitoring, use AIDE, Tripwire, or osquery.

### Are there kernel configuration options that trade security for performance?

Yes. Options like `CONFIG_STACKPROTECTOR` (stack canaries) and `CONFIG_FORTIFY_SOURCE` add runtime checks that have a small performance overhead (typically 1-5%). `CONFIG_PAGE_TABLE_ISOLATION` (PTI/KPTI) mitigates Meltdown but can reduce syscall performance by 5-15% on affected CPUs. `CONFIG_RANDOMIZE_MEMORY` (KASLR for memory layout) has negligible overhead. For most server workloads, the security benefits outweigh the performance cost.

### What should I do if checksec.sh reports "Partial RELRO" or "No PIE" for critical binaries?

"Partial RELRO" means the GOT (Global Offset Table) is writable at runtime, enabling GOT overwrite attacks. "No PIE" means the binary loads at a fixed address, enabling return-to-libc attacks. For critical binaries like SSH daemons, web servers, and database engines, you should: (1) Check if updated packages are available with full RELRO and PIE, (2) Recompile from source with `-fPIE -pie -Wl,-z,relro,-z,now` flags, or (3) If source recompilation is not possible, use additional mitigations like SELinux/AppArmor confinement or seccomp filtering to limit exploitation impact.
