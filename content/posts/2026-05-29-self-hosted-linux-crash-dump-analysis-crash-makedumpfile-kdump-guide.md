---
title: "Self-Hosted Linux Crash Dump Analysis: crash vs makedumpfile vs kdump"
date: "2026-05-23"
tags: ["linux", "crash-analysis", "system-administration", "debugging", "kdump"]
draft: false
---

When a Linux kernel panics, the system loses all in-memory diagnostic information unless a crash dump mechanism is configured. **Kernel crash dumps** capture the complete memory state at the moment of failure, enabling post-mortem analysis that identifies root causes of system crashes. This guide compares three essential tools for Linux crash dump analysis and management.

## Why Crash Dump Analysis Matters

Production Linux servers crash due to kernel bugs, hardware failures, driver issues, or resource exhaustion. Without a crash dump, administrators are left guessing about the root cause. With a proper crash dump, you can:

- **Identify the exact kernel function** that triggered the panic
- **Examine memory contents** of corrupted data structures
- **Trace call stacks** leading to the failure
- **Correlate crashes** with specific workloads or configuration changes
- **Build evidence** for bug reports to kernel maintainers

For organizations running mission-critical infrastructure, crash dump analysis is not optional — it is a fundamental component of incident response and root cause analysis.

## kdump: The Crash Dump Capture Framework

**GitHub:** [horms/kexec-tools](https://github.com/horms/kexec-tools) | **Stars:** 80+ | **Last Updated:** May 2026

kdump is the standard Linux kernel crash dump capture mechanism, built on top of kexec. It reserves a small portion of memory for a **crash kernel** that boots when the primary kernel panics, then captures the primary kernel memory to disk.

### How kdump Works

```
+-----------------------------------------+
|            Primary Kernel               |
|  (running production workloads)         |
|                                         |
|  +-------------------+                  |
|  |   Crash Kernel    |  <- Reserved memory
|  |   (minimal init)  |     region
|  +-------------------+                  |
+-----------------------------------------+

On panic -> kexec boots crash kernel -> dumps memory to disk
```

### kdump Configuration

```bash
# Install kdump tools
sudo apt install linux-crashdump  # Debian/Ubuntu
sudo yum install kexec-tools       # RHEL/CentOS

# Configure crash kernel memory reservation (in /etc/default/grub)
GRUB_CMDLINE_LINUX="... crashkernel=256M"

# Update GRUB and reboot
sudo update-grub  # or grub2-mkconfig -o /boot/grub2/grub.cfg
sudo reboot

# Enable and start kdump
sudo systemctl enable kdump
sudo systemctl start kdump
sudo systemctl status kdump

# Test kdump (CAUTION: this will crash the system)
echo 1 | sudo tee /proc/sys/kernel/sysrq
echo c | sudo tee /proc/sysrq-trigger
```

### kdump Storage Configuration

```ini
# /etc/kdump.conf - where to save crash dumps

# Save to local filesystem
path /var/crash

# Save to remote server via SSH
ssh user@dump-server
sshkey /root/.ssh/kdump_id_rsa
path /var/crash/dumps

# Save to NFS mount
nfs dump-server:/export/crashes

# Compression
core_collector makedumpfile -l --message-level 1 -d 31
```

### kdump Advantages

- **Industry standard:** Pre-installed on most major Linux distributions
- **Flexible storage:** Supports local disk, SSH, NFS, and raw devices
- **Integration:** Works seamlessly with systemd and standard Linux tooling
- **Proven reliability:** Used in production by thousands of enterprises worldwide

### kdump Limitations

- **Memory overhead:** Requires reserving RAM for the crash kernel (typically 256MB-1GB)
- **Single dump:** Only captures the most recent crash (older dumps must be manually archived)
- **No analysis built in:** kdump captures the dump but requires separate tools for analysis

## crash: The Kernel Crash Analysis Utility

**GitHub:** [crash-utility/crash](https://github.com/crash-utility/crash) | **Stars:** 949+ | **Last Updated:** May 2026

The `crash` utility is the primary tool for analyzing Linux kernel crash dumps. It provides an interactive debugging interface similar to GDB, but specialized for kernel memory analysis.

### How crash Works

```bash
# Install crash
sudo apt install crash        # Debian/Ubuntu
sudo yum install crash        # RHEL/CentOS

# Analyze a crash dump
crash /usr/lib/debug/lib/modules/$(uname -r)/vmlinux /var/crash/20260523/vmcore

# Basic analysis commands
crash> bt              # Backtrace of all tasks
crash> ps              # Process list
crash> log             # Kernel log buffer (dmesg)
crash> vm              # Virtual memory info
crash> sys             # System information
crash> rd <address>    # Read memory at address
crash> struct task_struct  # Display structure definition
crash> kmem -i         # Kernel memory usage
crash> runq            # Run queue state
```

### Common crash Analysis Workflows

**Finding the panic cause:**

```bash
crash> log
# Look for the panic message and call trace

crash> bt
# Shows the backtrace of all processes at crash time

crash> rd -f
# Display the panic frame
```

**Examining memory corruption:**

```bash
crash> ps
# Find processes running at crash time

crash> struct task_struct <address>
# Examine specific process memory

crash> kmem -s
# Show slab cache usage

crash> vm -p <pid>
# Show page tables for a specific process
```

### crash Advantages

- **Comprehensive analysis:** Full kernel debugging capabilities
- **Interactive interface:** Explore memory, structures, and state freely
- **Scriptable:** Supports crash scripts for automated analysis
- **Cross-platform:** Works on x86, ARM, ARM64, and other architectures

### crash Limitations

- **Steep learning curve:** Requires deep kernel knowledge to use effectively
- **Manual analysis:** No automated root cause identification
- **Debug symbols required:** Needs vmlinux with debug symbols for full functionality

## makedumpfile: Crash Dump Compression and Filtering

**GitHub:** [makedumpfile/makedumpfile](https://github.com/makedumpfile/makedumpfile) | **Stars:** 61+ | **Last Updated:** May 2026

`makedumpfile` is a specialized tool for reducing the size of kernel crash dumps by filtering out unnecessary pages and compressing the remaining data. A full memory dump of a 64GB server can exceed 64GB in size — makedumpfile typically reduces this by 80-95%.

### How makedumpfile Works

```bash
# Create a filtered and compressed dump
makedumpfile -l --message-level 1 -d 31 /proc/kcore /var/crash/vmcore.dump

# Options explained:
# -l              : Use LZO compression (faster)
# --message-level : Verbosity (1 = errors only)
# -d 31           : Exclude zero, cache, user, and free pages

# Convert a dumpfile back to the original format
makedumpfile -R /var/crash/vmcore < /var/crash/vmcore.dump

# Extract specific data from a dump
makedumpfile --dump-dmesg /var/crash/vmcore.dump > dmesg.txt
```

### Dump Level Filtering

| Dump Level | Pages Excluded | Typical Size Reduction |
|------------|---------------|----------------------|
| `-d 1`     | Zero pages    | 10-20%               |
| `-d 3`     | Zero + Cache  | 30-50%               |
| `-d 7`     | Zero + Cache + User | 50-70%          |
| `-d 15`    | Zero + Cache + User + Free | 60-80%    |
| `-d 31`    | All above + others | 80-95%          |

### makedumpfile with kdump

The most common use case is integrating makedumpfile with kdump as the core collector:

```ini
# /etc/kdump.conf
core_collector makedumpfile -l --message-level 1 -d 31

# Or with compression level tuning:
core_collector makedumpfile -c -l --message-level 1 -d 31
```

### makedumpfile Advantages

- **Massive size reduction:** 80-95% smaller dumps save significant storage
- **Faster capture:** Less data to write means shorter dump times
- **Configurable filtering:** Choose what data to keep based on analysis needs
- **Standard integration:** Works as kdump core_collector out of the box

### makedumpfile Limitations

- **Data loss risk:** Aggressive filtering may exclude pages needed for analysis
- **Architecture dependency:** Some filter options are architecture-specific
- **Version compatibility:** makedumpfile versions must match the kernel version being analyzed

## Comparison Table

| Feature | kdump | crash | makedumpfile |
|---------|-------|-------|--------------|
| **Purpose** | Capture crash dumps | Analyze crash dumps | Compress/filter dumps |
| **GitHub Stars** | 80+ (kexec-tools) | 949+ | 61+ |
| **Type** | Framework | Analysis tool | Filter/compression tool |
| **Memory Required** | 256MB-1GB reserved | None (post-capture) | None (post-capture) |
| **Interactive** | No | Yes | No |
| **Automation** | Automatic on panic | Manual analysis | Scriptable |
| **Storage** | Local, SSH, NFS, raw | N/A (reads dump files) | N/A (processes dump files) |
| **Size Reduction** | No (raw dump) | N/A | 80-95% reduction |
| **Architecture Support** | x86, ARM, ARM64, PPC | x86, ARM, ARM64, PPC | x86, ARM, ARM64 |
| **Distribution Support** | All major distros | All major distros | All major distros |
| **Learning Curve** | Low (configure once) | High (kernel debugging) | Low (command-line options) |

## Complete Crash Dump Workflow

### Step 1: Configure kdump

```bash
# Reserve memory for crash kernel
echo 'GRUB_CMDLINE_LINUX="${GRUB_CMDLINE_LINUX} crashkernel=512M"' >> /etc/default/grub
sudo update-grub
sudo reboot

# Enable kdump
sudo systemctl enable kdump
sudo systemctl start kdump

# Configure storage and compression
echo 'core_collector makedumpfile -l --message-level 1 -d 31' | sudo tee -a /etc/kdump.conf
echo 'path /var/crash' | sudo tee -a /etc/kdump.conf
sudo systemctl restart kdump
```

### Step 2: Capture a Crash Dump

When the kernel panics, kdump automatically boots the crash kernel and captures memory. The dump is saved to `/var/crash/<timestamp>/vmcore`.

### Step 3: Compress with makedumpfile

If not configured as the core_collector, compress manually:

```bash
makedumpfile -l --message-level 1 -d 31 /var/crash/vmcore /var/crash/vmcore.dump
```

### Step 4: Analyze with crash

```bash
# Install debug symbols
sudo apt install linux-image-$(uname -r)-dbgsym  # Debian/Ubuntu

# Launch crash
crash /usr/lib/debug/lib/modules/$(uname -r)/vmlinux /var/crash/vmcore.dump

# Analyze
crash> bt          # Find the crash backtrace
crash> log         # Read kernel messages
crash> ps          # See running processes
crash> sys         # System state
```

## Why Self-Host Crash Dump Analysis?

Self-hosted crash dump analysis tools give your team complete control over the diagnostic process:

- **Data privacy:** Crash dumps may contain sensitive memory contents — keeping them on-premises avoids exposing proprietary data to third-party analysis services
- **Custom analysis scripts:** Build automated analysis workflows tailored to your specific workloads and common failure patterns
- **Historical comparison:** Maintain a crash dump archive for trend analysis, identifying recurring issues across kernel versions or hardware generations
- **No subscription costs:** All three tools are open source and free to use, unlike commercial crash analysis platforms
- **Integration with existing tooling:** Feed crash data into your existing monitoring, alerting, and incident management systems

For related Linux system administration topics, see our [Linux performance profiling guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) and [disk encryption automation guide](../2026-05-22-self-hosted-disk-encryption-automation-clevis-tang-luks2-tpm2-systemd-guide/).

## FAQ

### What happens when a Linux kernel panics without kdump configured?

Without kdump, the kernel halts immediately and all in-memory diagnostic information is lost. The system must be rebooted manually, and the only available information is what was written to disk before the panic (typically just the last few lines of the kernel log via pstore or serial console).

### How much memory does kdump reserve for the crash kernel?

The recommended crash kernel size is 256MB for systems with up to 8GB RAM, 512MB for systems with 8-32GB RAM, and 1GB for systems with more than 32GB RAM. Larger systems with complex memory layouts may need more reserved memory.

### Can I analyze a crash dump from a different kernel version?

No. The `crash` utility requires debug symbols (vmlinux) that exactly match the kernel version and build that generated the dump. Using mismatched symbols will produce incorrect analysis results or fail to load.

### How do I reduce crash dump size without losing important data?

Use makedumpfile with dump level `-d 31` for maximum compression. This excludes zero pages, cache pages, user pages, and free memory. If you need user-space memory for analysis, use `-d 7` instead, which keeps user pages but still excludes zero, cache, and free pages.

### Is crash dump analysis only useful for kernel developers?

No. System administrators can use crash dumps to identify hardware failures (ECC memory errors, disk controller issues), driver problems (recently installed or updated drivers), and configuration issues (memory pressure, resource exhaustion). Even basic commands like `bt` and `log` provide valuable diagnostic information.

### How do I automate crash dump analysis?

Write crash scripts that run specific commands and save the output:

```bash
cat << 'EOF' > analysis.crash
bt
log
ps
sys
kmem -i
EOF
crash -s analysis.crash /path/to/vmlinux /path/to/vmcore
```

### Can kdump capture crashes caused by hardware failures?

Yes, if the hardware failure does not prevent the crash kernel from booting. Memory errors (ECC), CPU failures, and PCI device errors can all be captured. However, storage controller failures may prevent the dump from being written to disk — in such cases, configure kdump to save to a network location (SSH or NFS).

### What is the difference between a full dump and a filtered dump?

A full dump captures all kernel memory pages exactly as they are in RAM. A filtered dump (created with makedumpfile) excludes pages that are unlikely to be useful for analysis — such as zero-filled pages, page cache, and free memory — significantly reducing the dump file size.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Crash Dump Analysis: crash vs makedumpfile vs kdump",
  "description": "Compare crash, makedumpfile, and kdump for Linux kernel crash dump capture, compression, and post-mortem analysis on self-hosted servers.",
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
