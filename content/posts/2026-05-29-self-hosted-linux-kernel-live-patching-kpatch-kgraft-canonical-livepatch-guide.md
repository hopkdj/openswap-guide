---
title: "Self-Hosted Linux Kernel Live Patching: kpatch vs kgraft vs Canonical Livepatch"
date: "2026-05-23"
tags: ["linux", "kernel", "system-administration", "live-patching", "security"]
draft: false
---

Linux kernel live patching allows system administrators to apply critical security patches and bug fixes to a running kernel **without rebooting**. For production servers handling enterprise workloads, even a few minutes of planned downtime can translate into significant revenue loss, SLA violations, or disrupted user experiences. This guide compares the three major open-source live patching solutions available for self-hosted Linux environments.

## What Is Kernel Live Patching?

Kernel live patching works by loading a small kernel module that redirects function calls from vulnerable kernel code to patched replacement code. The original code remains in memory, but execution is transparently diverted to the fixed version. Once all processes have exited the old code paths, the patch becomes fully active.

The key advantage is **zero-downtime security patching**: critical CVEs can be addressed immediately without scheduling maintenance windows or interrupting running services. This is especially valuable for:

- **Database servers** handling thousands of concurrent transactions
- **Web servers** serving millions of requests per day
- **Container hosts** running dozens of workloads that would be disrupted by reboot
- **Network infrastructure** where even brief outages cascade to dependent systems
- **High-availability clusters** where node reboots trigger failover events

## kpatch (Red Hat)

**GitHub:** [dynup/kpatch](https://github.com/dynup/kpatch) | **Stars:** 1,682+ | **Last Updated:** May 2026

kpatch is Red Hat's kernel live patching framework. It consists of two components:

1. **kpatch-build** — Compiles kernel source patches into live patch modules
2. **kpatch** — Loads and manages live patch modules at runtime

### How kpatch Works

kpatch uses kernel function tracer (ftrace) to redirect calls. When a patch module is loaded:

```bash
# Install kpatch
sudo apt install kpatch  # Debian/Ubuntu
sudo yum install kpatch   # RHEL/CentOS

# List available patches
kpatch list

# Install a specific patch
sudo kpatch install kpatch-xxxxx

# View loaded patches
kpatch list --loaded
```

### kpatch Architecture

The kpatch workflow follows these steps:

1. **Patch creation:** A source-level diff against the kernel tree is compiled into a kernel module using `kpatch-build`
2. **Module loading:** The `kpatch` command loads the module via `insmod`
3. **Function redirection:** ftrace hooks redirect calls from old to new functions
4. **Safety verification:** The kernel ensures no threads are executing in the old function before activation

### kpatch Limitations

- **Patch availability:** Patches must be built by the distribution vendor or compiled manually
- **Kernel version specificity:** Each patch is tied to a specific kernel version and build
- **Complexity of patching:** Some kernel changes (data structure modifications, function signature changes) cannot be live patched
- **Deprecation notice:** The upstream kpatch project has been marked as deprecated; Red Hat now maintains its own internal version

## kgraft (SUSE)

kgraft is SUSE's kernel live patching solution, integrated directly into the SUSE Linux Enterprise Server (SLES) kernel. Unlike kpatch's ftrace-based approach, kgraft uses a more conservative patching model.

### How kgraft Works

kgraft operates at the kernel level with built-in support:

```bash
# On SLES, live patches are delivered through the standard update mechanism
sudo zypper patch

# Verify live patching is enabled
cat /sys/kernel/livepatch/enabled

# List applied patches
ls /sys/kernel/livepatch/
```

### kgraft Architecture

kgraft's key differentiator is its **kernel-integrated** approach:

1. **Built into the kernel:** No separate framework module needed — live patching support is compiled into the kernel itself
2. **Conservative model:** Patches are applied only when safe — the kernel tracks which functions are being executed and waits for a safe transition point
3. **SUSE-maintained patches:** SUSE delivers live patches through its standard update channels

### kgraft Advantages Over kpatch

- **No separate framework:** Since live patching is built into the kernel, there's no external tool dependency
- **Better integration with SUSE infrastructure:** Patches are delivered through zypper, the standard package manager
- **Conservative safety model:** More restrictive about which patches can be applied, reducing risk

### kgraft Limitations

- **SLES-only:** Primarily designed for SUSE Linux Enterprise Server, limited support for other distributions
- **Smaller patch ecosystem:** Fewer community-contributed patches compared to kpatch
- **Less flexible:** Cannot easily apply community patches without SUSE's involvement

## Canonical Livepatch (Ubuntu)

Canonical Livepatch is Ubuntu's enterprise live patching service, available for Ubuntu LTS releases. Unlike kpatch and kgraft which are open-source frameworks, Canonical Livepatch is a **service-delivered** solution.

### How Canonical Livepatch Works

```bash
# Install the livepatch client
sudo snap install canonical-livepatch

# Enable with your token (free for up to 3 machines)
sudo canonical-livepatch enable YOUR-TOKEN

# Check status
canonical-livepatch status --verbose
```

### Canonical Livepatch Architecture

Canonical Livepatch operates as a cloud-managed service:

1. **Client daemon:** The `canonical-livepatch` snap runs on each machine, checking for available patches
2. **Cloud delivery:** Canonical builds and signs patches centrally, distributing them to registered machines
3. **Automatic application:** Patches are downloaded and applied automatically without user intervention
4. **Verification:** Each patch is cryptographically signed and verified before loading

### Canonical Livepatch Advantages

- **Zero configuration:** Once enabled, patches are applied automatically — no manual intervention required
- **Free tier:** Up to 3 Ubuntu LTS machines can use live patching at no cost
- **Enterprise support:** Full support through Canonical's Ubuntu Advantage program
- **Timely delivery:** Patches are typically available within hours of upstream kernel fixes

### Canonical Livepatch Limitations

- **Ubuntu LTS only:** Available exclusively on Ubuntu LTS releases
- **Cloud dependency:** Requires internet connectivity to Canonical's servers
- **Proprietary service:** While the client is open source, the patch delivery infrastructure is not
- **Token limits:** Free tier limited to 3 machines; additional machines require Ubuntu Advantage subscription

## Comparison Table

| Feature | kpatch | kgraft | Canonical Livepatch |
|---------|--------|--------|---------------------|
| **Vendor** | Red Hat | SUSE | Canonical |
| **License** | GPL-2.0 | GPL-2.0 | Client: GPL, Service: Proprietary |
| **Stars** | 1,682+ | N/A (kernel-integrated) | N/A (snap package) |
| **Supported Distros** | RHEL, CentOS, Fedora | SLES, openSUSE | Ubuntu LTS |
| **Patch Delivery** | Manual / yum | zypper | Cloud service (automatic) |
| **Free Tier** | Yes (open source) | Yes (SLES license) | Yes (3 machines) |
| **Architecture** | ftrace-based | Kernel-integrated | Client-server |
| **Manual Patch Building** | Yes | No | No |
| **Automatic Application** | No | Via zypper | Yes |
| **Community Patches** | Yes | Limited | No |
| **Enterprise Support** | Red Hat Subscription | SUSE Subscription | Ubuntu Advantage |
| **Kernel Version Support** | Specific builds | SLES kernels | Ubuntu LTS kernels |

## Installation and Configuration

### kpatch on Debian/Ubuntu

```bash
# Install kpatch tools
sudo apt update
sudo apt install kpatch kpatch-build

# Build a patch from source
cd /tmp
git clone https://github.com/dynup/kpatch.git
cd kpatch
# Create a patch file for your kernel version
kpatch-build /path/to/patch.diff

# Load the patch
sudo kpatch install kpatch-xxxxx.ko
sudo kpatch load kpatch-xxxxx.ko

# Verify
kpatch list --loaded
```

### kgraft on SLES

```bash
# Enable live patching repository
sudo SUSEConnect --list-extensions

# Install live patches through standard update
sudo zypper patch

# Check which patches are applied
ls -la /sys/kernel/livepatch/
```

### Canonical Livepatch on Ubuntu

```bash
# Install the snap
sudo snap install canonical-livepatch

# Get a token from https://livepatch.canonical.com
sudo canonical-livepatch enable YOUR-TOKEN

# Verify installation
canonical-livepatch status --verbose

# Disable (if needed)
sudo canonical-livepatch disable
```

## When to Use Each Solution

### Choose kpatch if:
- You run RHEL, CentOS, or Fedora servers
- You need the ability to build and test custom patches
- You want full open-source transparency for the entire stack
- Your team has kernel compilation expertise

### Choose kgraft if:
- You run SUSE Linux Enterprise Server
- You prefer kernel-integrated solutions over external frameworks
- You want live patching delivered through your standard update workflow
- You value conservative safety over patch availability

### Choose Canonical Livepatch if:
- You run Ubuntu LTS servers
- You want zero-configuration automatic patching
- You have fewer than 3 machines (free tier) or an Ubuntu Advantage subscription
- You prefer managed services over self-maintained tooling

## Why Self-Host Live Patching?

Running your own live patching infrastructure gives you complete control over which patches are applied, when they are applied, and how they are tested. While managed services like Canonical Livepatch offer convenience, self-hosted solutions provide several advantages for organizations with strict compliance requirements:

- **Audit trail:** Every patch application is logged locally, providing a complete record for compliance audits
- **Custom testing:** You can test patches against your specific workload before deployment, ensuring compatibility with proprietary applications
- **No external dependency:** Self-hosted solutions do not require internet connectivity to third-party servers, making them suitable for air-gapped environments
- **Patch customization:** You can modify upstream patches to address organization-specific issues or backport fixes to older kernel versions
- **Cost control:** Open-source solutions avoid per-machine licensing fees, which can be significant for large server fleets

For organizations managing heterogeneous Linux environments, a multi-vendor strategy may be necessary — kpatch for RHEL systems, Canonical Livepatch for Ubuntu servers, and manual kernel updates for SLES installations. The key is ensuring that every production server has a live patching strategy in place to minimize security exposure windows.

For broader Linux system hardening, see our [disk encryption automation guide](../2026-05-22-self-hosted-disk-encryption-automation-clevis-tang-luks2-tpm2-systemd-guide/) and [Linux performance profiling comparison](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/).

## FAQ

### What is kernel live patching and why is it important?

Kernel live patching is a technique that applies security fixes and bug patches to a running Linux kernel without requiring a system reboot. It is important because it eliminates the need for maintenance windows, allowing critical CVEs to be addressed immediately while keeping production services running uninterrupted.

### Can live patching fix all kernel vulnerabilities?

No. Live patching works by redirecting function calls to patched versions, which means it can only fix vulnerabilities in code paths that can be safely redirected. Changes to kernel data structures, function signatures, or initialization code often cannot be live patched and still require a reboot.

### Is kpatch still actively maintained?

The upstream dynup/kpatch repository has been marked as deprecated. However, Red Hat continues to maintain its own internal version of kpatch for RHEL and CentOS systems. Community users should check with their distribution vendor for current live patching support.

### How does Canonical Livepatch differ from kpatch and kgraft?

Canonical Livepatch is a managed service that automatically delivers patches to registered Ubuntu machines, while kpatch and kgraft are frameworks that require manual patch building or distribution-specific update channels. Canonical Livepatch is free for up to 3 machines but requires internet connectivity to Canonical servers.

### Can I use live patching on non-LTS Ubuntu releases?

Canonical Livepatch is only available for Ubuntu LTS releases. Non-LTS releases receive a shorter support window and are expected to be upgraded rather than live patched. For non-LTS systems, standard kernel updates through apt are the recommended approach.

### Does live patching affect system performance?

Live patching introduces minimal overhead. The ftrace-based redirection used by kpatch adds a negligible performance cost (typically less than 1% CPU overhead). kgraft kernel-integrated approach has essentially zero overhead. Canonical Livepatch applies the same underlying kernel mechanisms with no additional performance impact.

### How do I verify that a live patch has been applied?

For kpatch, run `kpatch list --loaded`. For kgraft, check `/sys/kernel/livepatch/`. For Canonical Livepatch, run `canonical-livepatch status --verbose`. All three methods show which patches are currently active and their application status.

### Can live patches be rolled back?

Yes. kpatch supports `kpatch unload` to remove a specific patch module. kgraft patches can be removed through zypper rollback mechanism. Canonical Livepatch patches can be disabled, though the service typically manages patch lifecycle automatically.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Kernel Live Patching: kpatch vs kgraft vs Canonical Livepatch",
  "description": "Compare three major Linux kernel live patching solutions — kpatch, kgraft, and Canonical Livepatch — for zero-downtime security patching on self-hosted servers.",
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
