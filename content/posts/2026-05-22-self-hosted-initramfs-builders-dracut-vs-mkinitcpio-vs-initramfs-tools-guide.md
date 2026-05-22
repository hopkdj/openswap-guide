---
title: "Self-Hosted Initramfs Builders: dracut vs mkinitcpio vs initramfs-tools"
date: "2026-05-22"
tags: ["linux", "boot", "systemd", "initramfs", "comparison"]
draft: false
---

When a Linux server boots, the kernel needs access to the root filesystem — which may reside on LVM, encrypted volumes, RAID arrays, or network storage. The **initramfs** (initial RAM filesystem) bridges this gap by loading drivers, unlocking encrypted disks, and assembling storage before the real root mounts. But not all initramfs builders are created equal.

This guide compares three major Linux initramfs generators: **dracut**, **mkinitcpio**, and **initramfs-tools** — covering architecture, configuration, module systems, and when to use each one.

## What Is an Initramfs and Why Does It Matter?

The initramfs is a temporary root filesystem loaded into memory during boot. It contains the minimal set of drivers, scripts, and binaries needed to mount the real root filesystem. Without it, the kernel cannot access storage that requires special drivers or setup steps.

For self-hosted servers, a properly configured initramfs is critical for:

- **Disk encryption (LUKS)** — unlocking encrypted root partitions at boot
- **LVM and RAID** — assembling volume groups and mdadm arrays before mounting
- **Network boot** — mounting root over NFS, iSCSI, or HTTP
- **Hardware drivers** — loading storage controller drivers not built into the kernel
- **Remote unlock** — SSH access to unlock encrypted disks on headless servers

A misconfigured initramfs can leave your server unbootable after a kernel update. Understanding your initramfs builder helps you diagnose boot failures, customize the boot process, and optimize boot times.

## Architecture Comparison

Each initramfs builder uses a different philosophy for constructing the boot image.

| Feature | dracut | mkinitcpio | initramfs-tools |
|---------|--------|------------|-----------------|
| **Origin** | Red Hat / Fedora | Arch Linux | Debian / Ubuntu |
| **Approach** | Event-driven, auto-detect | Hook-based, modular | Script-based, modular |
| **Module Loading** | On-demand (udev events) | Explicit hook order | Ordered scripts |
| **Host-Only Mode** | Yes (default) | N/A (always host-specific) | No (includes all drivers) |
| **Default Init System** | systemd or busybox | busybox or systemd | busybox |
| **Network Boot** | dracut-network module | net hook | netboot scripts |
| **LUKS Support** | Yes (crypt module) | Yes (encrypt hook) | Yes (cryptroot) |
| **LVM Support** | Yes (lvm module) | Yes (lvm2 hook) | Yes (lvm2) |
| **NFS Root** | Yes | Yes (net + nfs hooks) | Yes (netboot) |
| **iSCSI Boot** | Yes (iscsi module) | Via custom hook | Via custom script |
| **Configuration** | `/etc/dracut.conf` | `/etc/mkinitcpio.conf` | `/etc/initramfs-tools/` |
| **Image Location** | `/boot/initramfs-*.img` | `/boot/initramfs-*.img` | `/boot/initrd.img-*` |
| **GitHub Stars** | 676+ | Arch GitLab | Debian package |
| **License** | GPLv2 | MIT | GPLv2 |

### dracut: Event-Driven Auto-Detection

dracut takes an event-driven approach. Instead of listing modules manually, it inspects the running system and includes only what is needed. This "host-only" mode produces smaller images and reduces the risk of including unnecessary drivers. dracut uses systemd's udev to detect hardware events during the initramfs stage, loading drivers on demand.

Key dracut modules include:
- `crypt` — LUKS encryption support
- `lvm` — LVM2 volume group activation
- `mdraid` — Software RAID assembly
- `network` / `nfs` / `iscsi` — Network boot support
- `resume` — Hibernation resume from swap
- `drm` — GPU drivers for graphical boot

### mkinitcpio: Explicit Hook Ordering

mkinitcpio uses a hook-based system where you explicitly define the order of operations in `HOOKS=`. This gives fine-grained control over what runs and when. The hook order matters — for example, `udev` must run before `autodetect`, and `encrypt` must run before `lvm2` if your LVM sits inside an encrypted container.

Standard mkinitcpio hooks:
- `systemd` or `udev` — Device detection
- `autodetect` — Remove unused modules
- `modconf` — Module configuration
- `block` — Storage drivers
- `keyboard` / `keymap` — Input support
- `encrypt` — LUKS decryption
- `lvm2` — LVM assembly
- `filesystems` — Root filesystem mount
- `fsck` — Filesystem check before mount

### initramfs-tools: Script-Based Modularity

initramfs-tools (also known as initramfs-tools-core) uses a collection of shell scripts organized into stages: `top`, `top/premount`, `premount`, `mount`, `mount-bottom`, `mount-top`, `bottom`, and `panic`. Each stage runs in order, and scripts within a stage are sorted alphabetically.

The `cryptroot` script handles LUKS unlocking, while `lvm2` handles volume group activation. The modular approach makes it straightforward to add custom scripts — just drop them into the appropriate stage directory.

## Configuration Examples

### dracut Configuration

dracut's main configuration file is `/etc/dracut.conf.d/`. You can add custom module loading or force specific drivers:

```bash
# /etc/dracut.conf.d/custom.conf
# Force include specific kernel modules
add_drivers+=" ahci nvme "
# Force include specific dracut modules
add_dracutmodules+=" crypt lvm resume "
# Exclude modules you don't need
omit_dracutmodules+=" plymouth "
# Enable host-only mode (default on Fedora)
hostonly="yes"
# Rebuild for all installed kernels
kernel_cmdline="root=/dev/mapper/vg0-root resume=/dev/mapper/vg0-swap"
```

Rebuild the initramfs for the current kernel:

```bash
dracut --force
# Or for a specific kernel version:
dracut --force --kver 6.8.0-45-generic
```

### mkinitcpio Configuration

The main configuration file is `/etc/mkinitcpio.conf`:

```bash
# /etc/mkinitcpio.conf
# MODULES: Load before autodetect runs
MODULES=(nvme ahci xfs)

# BINARIES: Include additional binaries in the image
BINARIES=(btrfs)

# FILES: Include additional configuration files
FILES=()

# HOOKS: Execution order is critical
HOOKS=(systemd autodetect modconf block keyboard keymap encrypt lvm2 filesystems fsck)

# COMPRESSION: Choose compression algorithm
COMPRESSION="zstd"
# COMPRESSION_OPTIONS=()
```

Rebuild after editing:

```bash
mkinitcpio -P
# Or for a specific preset:
mkinitcpio -p linux
```

### initramfs-tools Configuration

Configuration is spread across `/etc/initramfs-tools/`:

```bash
# /etc/initramfs-tools/initramfs.conf
# MODULES: dep (auto-detect), most, or netboot
MODULES=dep
# COMPRESS: Compression algorithm (xz, gzip, zstd, lz4)
COMPRESS=xz
# DEVICE: Network device for netboot
#DEVICE=eth0
# NFSROOT: NFS root path
#NFSROOT=auto
```

Custom scripts go in `/etc/initramfs-tools/scripts/`:

```bash
# /etc/initramfs-tools/scripts/local-top/custom-lvm.sh
#!/bin/sh
# Custom LVM setup before root mount
PREREQ=""
prereqs() { echo "$PREREQ"; }
case $1 in
prereqs) prereqs; exit 0 ;;
esac

. /scripts/init-functions
log_begin_msg "Running custom LVM configuration"
vgchange -ay vg0
log_end_msg
```

Rebuild:

```bash
update-initramfs -u
# Or for a specific kernel:
update-initramfs -u -k 6.8.0-45-generic
```

## Boot Time and Image Size Comparison

The initramfs builder you choose affects both boot time and disk usage.

| Metric | dracut (host-only) | mkinitcpio | initramfs-tools |
|--------|-------------------|------------|-----------------|
| **Typical image size** | 15-30 MB | 8-15 MB | 20-40 MB |
| **Boot time (cold)** | ~2-3s initramfs stage | ~1-2s initramfs stage | ~2-4s initramfs stage |
| **Kernel update rebuild** | Automatic (via package hooks) | Manual (`mkinitcpio -P`) | Automatic (via package hooks) |
| **Customization difficulty** | Moderate | Moderate | Easy |

dracut's host-only mode typically produces smaller images than initramfs-tools because it only includes drivers for the current hardware. mkinitcpio images are generally the smallest due to Arch's minimal default configuration. initramfs-tools can produce larger images because it includes a broader set of drivers by default (MODULES=dep still auto-detects but is less aggressive than dracut's host-only).

## Remote Disk Unlock via SSH

For headless servers with encrypted root partitions, all three tools support remote unlock via SSH, but with different implementations.

### dracut with SSH Unlock

dracut includes the `ssh-client` module for network-based unlocking. Combined with `dracut-crypt-ssh` or custom scripts, you can SSH into the initramfs to enter the LUKS passphrase:

```bash
# Install dropbear for lightweight SSH in initramfs
# /etc/dracut.conf.d/ssh.conf
add_dracutmodules+=" network ssh-client crypt "
# Use dropbear instead of full ssh
install_items+=" /usr/sbin/dropbear "
```

### mkinitcpio with dropbear

The Arch Linux wiki provides a well-documented approach using `mkinitcpio-utils` and dropbear:

```bash
# /etc/mkinitcpio.conf
HOOKS=(... encrypt ... filesystems ...)
BINARIES+=(dropbear)
FILES=(/etc/dropbear/dropbear_rsa_host_key)
```

A custom hook script listens on the initramfs network interface and accepts SSH connections for passphrase entry.

### initramfs-tools with cryptroot-ask

initramfs-tools supports dropbear-based remote unlock through the `dropbear-initramfs` package:

```bash
# Install the package
apt install dropbear-initramfs

# Configure the initramfs network interface
# /etc/initramfs-tools/initramfs.conf
DEVICE=eth0
IP=192.168.1.100::192.168.1.1:255.255.255.0:server:eth0:none

# Add your public key for SSH access
# /etc/dropbear/initramfs/authorized_keys
```

## Why Choose One Over Another?

The choice of initramfs builder is often dictated by your Linux distribution. Fedora, RHEL, CentOS, and openSUSE use dracut by default. Arch Linux uses mkinitcpio. Debian, Ubuntu, and derivatives use initramfs-tools. However, you can install alternative builders on any distribution if you have specific needs.

### When to Use dracut

dracut excels when you want automatic hardware detection without manual configuration. Its event-driven model means kernel updates rarely require initramfs tweaks. The host-only mode keeps images lean. dracut is also the most feature-complete for enterprise boot scenarios — iSCSI, FCoE, NBD, and multipath support are all built-in.

If you manage servers across multiple hardware platforms or frequently change storage configurations, dracut's auto-detection saves time.

### When to Use mkinitcpio

mkinitcpio is ideal when you want explicit control over the boot process. The hook system makes it clear exactly what runs and in what order. This transparency simplifies debugging — if boot fails, you know which hook is responsible. The smaller image sizes also benefit boot performance on resource-constrained systems.

Arch Linux users benefit from tight integration with the kernel package — kernel updates automatically trigger `mkinitcpio -P` via pacman hooks.

### When to Use initramfs-tools

initramfs-tools is best for Debian/Ubuntu users who want a stable, well-tested boot pipeline. The script-based system is easy to customize — adding a custom boot script is as simple as dropping a file into `/etc/initramfs-tools/scripts/`. The broader driver inclusion also means fewer "driver not found" issues when migrating disks between machines.

For organizations running Debian-based infrastructure, initramfs-tools offers the best ecosystem compatibility with existing deployment tooling and documentation.

## Related Guides

For server bootstrapping automation, see our [cloud-init vs Ignition vs Butane comparison](../2026-04-24-cloud-init-vs-ignition-vs-butane-self-hosted-server-bootstrapping-guide/).
If you need immutable operating system options, check our [Talos Linux vs Flatcar vs Bottlerocket guide](../2026-04-21-talos-linux-vs-flatcar-vs-bottlerocket-immutable-container-os-guide-2026/).
For centralized log collection during boot, our [systemd journal remote guide](../2026-05-06-self-hosted-centralized-journal-collection-graylog-vector-systemd-journal-remote/) covers remote journal forwarding.

## Frequently Asked Questions

### Can I switch initramfs builders on an existing system?

Yes, but proceed with caution. Install the alternative builder package, generate a new initramfs with it, and keep the old initramfs as a fallback in your bootloader configuration. Test boot with the new initramfs before removing the old one. Always have a live USB available for recovery.

### How do I debug initramfs boot failures?

Add `rd.shell` (dracut), `break=y` (mkinitcpio), or `break=mount` (initramfs-tools) to your kernel command line. This drops you into a shell inside the initramfs where you can inspect loaded modules (`lsmod`), check device availability (`ls /dev`), and manually attempt the mount steps.

### Does the initramfs affect boot security?

Yes. The initramfs contains the LUKS passphrase prompt logic and may include SSH keys for remote unlock. Ensure your initramfs partition is encrypted or that your bootloader validates the initramfs with Secure Boot. Tools like `sbctl` (Secure Boot key management) can sign your initramfs images.

### Can I add custom kernel modules to my initramfs?

All three builders support custom modules. In dracut, use `add_drivers+=" module_name "`. In mkinitcpio, add to `MODULES=()`. In initramfs-tools, add to `/etc/initramfs-tools/modules`. After adding modules, rebuild the initramfs.

### How often should I rebuild the initramfs?

Rebuild after: kernel updates, storage hardware changes, LUKS key changes, LVM configuration changes, or RAID array modifications. Most distributions automate this via package manager hooks, but it is good practice to verify the initramfs was rebuilt after kernel updates.

### What compression should I use for the initramfs?

`zstd` offers the best balance of compression ratio and decompression speed for most systems. `xz` provides smaller images but slower decompression (negatively impacting boot time). `gzip` is fast but produces larger images. `lz4` is the fastest but least compressing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Initramfs Builders: dracut vs mkinitcpio vs initramfs-tools",
  "description": "Compare three major Linux initramfs generators: dracut, mkinitcpio, and initramfs-tools. Covers architecture, configuration, remote unlock, and when to use each.",
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
