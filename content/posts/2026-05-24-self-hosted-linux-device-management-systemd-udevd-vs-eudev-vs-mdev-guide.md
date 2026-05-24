---
title: "Self-Hosted Linux Device Management: systemd-udevd vs eudev vs mdev (2026)"
date: "2026-05-24"
tags: ["linux", "device-management", "udev", "systemd", "system-administration", "homelab"]
draft: false
---

Linux device management is the unsung hero of every self-hosted infrastructure. When you plug in a USB drive, insert a PCIe card, or attach a network interface, the device manager is what creates the device nodes, sets permissions, and triggers the actions that make hardware usable. For self-hosted server administrators managing bare-metal infrastructure, homelab setups, or container hosts with GPU passthrough, choosing the right device management framework directly impacts system reliability, boot time, and device hot-plug behavior.

This guide compares three Linux device managers: **systemd-udevd** (the default on most modern distributions), **eudev** (the Gentoo fork focused on standalone operation), and **mdev** (the minimalist BusyBox-based manager for embedded and container environments).

## Understanding Linux Device Management

The Linux kernel exposes hardware through the sysfs filesystem (`/sys`) and creates device nodes in devtmpfs (`/dev`). But the kernel doesn't decide what permissions those nodes should have, what symlinks to create, or what actions to trigger when devices appear. That's the job of the userspace device manager.

Device managers watch the kernel's uevent netlink socket for hardware events and respond by:

- Creating or removing device nodes in `/dev`
- Setting ownership and permissions on device nodes
- Creating persistent symlinks (e.g., `/dev/disk/by-id/`)
- Loading kernel modules on demand
- Running custom scripts or systemd units when devices appear
- Managing network interface naming

The three tools compared here approach this problem with very different design philosophies: full-featured integration, distribution independence, and minimal resource usage.

## Tool Comparison at a Glance

| Feature | systemd-udevd | eudev | mdev |
|---------|---------------|-------|------|
| Origin | systemd project | Gentoo (forked from udev) | BusyBox project |
| Package Size | ~2 MB (with systemd) | ~1.5 MB | ~20 KB |
| Rule Syntax | Full udev rules | Full udev rules (compatible) | Simplified regex-based |
| Persistent Naming | Yes (extensive) | Yes (extensive) | No (basic only) |
| Hotplug Support | Full | Full | Basic |
| Dependency | systemd (optional) | None (standalone) | BusyBox only |
| Scripting | RUN+=, systemd units | RUN+=, scripts | Shell commands in config |
| Network Interface Naming | Predictable names | Predictable names | Kernel default naming |
| Best For | Desktop/server distros | systemd-free servers | Embedded, containers, initramfs |
| GitHub | [systemd/systemd](https://github.com/systemd/systemd) (10,800+ ★) | [eudev-project/eudev](https://github.com/eudev-project/eudev) (567 ★) | [mirror/busybox](https://github.com/mirror/busybox) (9,700+ ★) |
| Last Updated | Active (2026) | 2024-09 | Active (in BusyBox) |

## systemd-udevd: The Full-Featured Default

`systemd-udevd` is the device manager shipped with systemd and used by default on virtually every major Linux distribution — Fedora, Ubuntu, Debian, Arch Linux, and RHEL derivatives. It's deeply integrated with the rest of the systemd ecosystem, providing device-triggered service activation, predictable network interface naming, and extensive persistent naming for storage devices.

### Key Features

```bash
# View udev device information
udevadm info /dev/sda
udevadm info -a -p /sys/block/sda  # Full attribute walk

# Test a rule without applying it
udevadm test /sys/block/sda
udevadm test-builtin net_id /sys/class/net/eth0

# Trigger events manually
udevadm trigger --subsystem-match=block
udevadm trigger --action=add

# Monitor uevents in real-time
udevadm monitor --udev --property

# Reload rules after editing
udevadm control --reload
udevadm trigger
```

### Persistent Storage Naming

One of udev's most valuable features is creating stable symlinks for storage devices:

```bash
# These symlinks persist across reboots and disk reordering
ls -la /dev/disk/by-id/
ls -la /dev/disk/by-uuid/
ls -la /dev/disk/by-label/
ls -la /dev/disk/by-path/

# Custom persistent naming via udev rules
# /etc/udev/rules.d/99-custom-disks.rules
SUBSYSTEM=="block", ENV{ID_SERIAL}=="QEMU_Disk_1", SYMLINK+="data/disk1"
SUBSYSTEM=="block", ENV{ID_SERIAL}=="QEMU_Disk_2", SYMLINK+="data/disk2"
```

### GPU Passthrough Rules for Virtualization

For self-hosted virtualization with VFIO GPU passthrough, udev rules are essential:

```bash
# /etc/udev/rules.d/99-vfio.rules
# Bind NVIDIA GPU to vfio-pci on boot
SUBSYSTEM=="pci", DRIVER=="nvidia", RUN+="/sbin/vfio-bind 0000:%k"
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{device}=="0x2786",   DRIVER=="vfio-pci"

# Set permissions for KVM/QEMU GPU passthrough
SUBSYSTEM=="vfio", OWNER="libvirt-qemu", GROUP="kvm", MODE="0660"
```

### Docker Compose for Monitoring

```yaml
services:
  udev-monitor:
    image: ubuntu:latest
    privileged: true
    volumes:
      - /dev:/dev
      - /sys:/sys:ro
      - /run/udev:/run/udev:ro
    command: >
      sh -c "
        apt-get update && apt-get install -y udev
        && udevadm monitor --udev --property --subsystem-match=block
      "
    network_mode: host
    restart: no
```

## eudev: The Standalone Alternative

`eudev` (experimental udev) was forked by Gentoo Linux from the udev codebase when udev became tightly coupled with systemd. It maintains full compatibility with udev rules while operating independently of systemd. This makes it the go-to choice for servers running alternative init systems like OpenRC, runit, or s6.

### When to Choose eudev

- Running Gentoo, Alpine Linux, or Void Linux
- Using OpenRC, runit, s6, or another non-systemd init
- Wanting udev functionality without pulling in systemd dependencies
- Building custom Linux images where minimal dependency trees matter

### Rule Compatibility

eudev uses the exact same rule syntax as systemd-udevd:

```bash
# These rules work identically in both implementations
# /etc/udev/rules.d/99-serial-devices.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523",   SYMLINK+="serial/arduino", MODE="0660", GROUP="dialout"

SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001",   SYMLINK+="serial/ftdi", MODE="0660", GROUP="dialout"
```

### Building and Deploying

```bash
# Alpine Linux (uses eudev by default)
apk add eudev eudev-hwids

# Gentoo
emerge sys-fs/eudev

# Build from source
git clone https://github.com/eudev-project/eudev.git
cd eudev
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc --libdir=/usr/lib
make
make install
```

## mdev: The Minimalist Approach

`mdev` is BusyBox's device manager — a tiny, regex-based alternative that handles the essential device management tasks with a fraction of the code. It's designed for embedded systems, initramfs environments, and container runtimes where systemd's overhead is unacceptable.

### Configuration

mdev uses a simple configuration file format:

```bash
# /etc/mdev.conf format:
# device_regex  uid:gid  permissions  [special_handling]

# Default permissions for all devices
.* root:root 0660

# Specific device overrides
sd[a-z] root:disk 0660 @mkdir -p /dev/disks; ln -s $MDEV /dev/disks/$MDEV
sd[a-z][0-9] root:disk 0660
ttyUSB0 root:dialout 0660
eth0 root:root 0600 *ifup $MDEV

# GPU devices for container passthrough
nvidia[0-9]* root:video 0660
nvidiactl root:video 0660
```

### Command Execution

Unlike udev's rich RUN+= syntax, mdev uses a simpler approach:

```bash
# mdev.conf special commands (@ = run after, $ = run before, * = run both)
sd[a] root:disk 0660 */sbin/mdev-automount

# mdev-automount script
#!/bin/sh
if [ "$ACTION" = "add" ]; then
    mkdir -p /mnt/$MDEV
    mount /dev/$MDEV /mnt/$MDEV
elif [ "$ACTION" = "remove" ]; then
    umount /mnt/$MDEV
    rmdir /mnt/$MDEV
fi
```

### Use Cases

mdev shines in environments where resources are constrained:

- **Initramfs**: Early boot device management before the real root is mounted
- **Containers**: Minimal device node creation without systemd overhead
- **Embedded devices**: Routers, IoT gateways, and single-board computers
- **Rescue systems**: Live USB environments where every megabyte counts

## Why Self-Host with Proper Device Management?

For self-hosted infrastructure, reliable device management is foundational:

**Hardware Passthrough**: GPU passthrough for virtual machines, USB device assignment to containers, and PCIe SR-IOV all depend on udev rules to bind devices to the correct drivers at boot time. Without proper device management, VFIO bindings fail and virtual machines can't access hardware.

**Storage Reliability**: Persistent device naming (`/dev/disk/by-id/`) prevents data corruption when disk ordering changes. Without it, a drive added to the system could shift device node assignments, causing filesystems to mount on the wrong devices.

**Automated Device Actions**: Self-hosted servers benefit from automatic responses to hardware events — mounting backup drives when they're connected, starting services when USB dongles are inserted, or isolating network interfaces when specific adapters appear.

For related reading on Linux device isolation, see our [Linux PID namespace isolation guide](../2026-05-24-self-hosted-linux-pid-namespace-isolation-unshare-bubblewrap-nsenter-guide/). For hardware passthrough configurations, check our [Linux IOMMU VFIO GPU passthrough guide](../2026-05-23-self-hosted-linux-iommu-vfio-gpu-passthrough-looking-glass-guide/).

## Choosing the Right Device Manager

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Standard server/desktop | systemd-udevd | Distribution default, full features |
| Non-systemd server | eudev | Full udev compatibility, no systemd |
| Container/VM base image | mdev | Minimal footprint, adequate for containers |
| Embedded/IoT device | mdev | Tiny size, BusyBox integration |
| Initramfs/rescue | mdev | Already in BusyBox, fast boot |
| GPU passthrough host | systemd-udevd | Rich rule syntax, systemd integration |
| OpenRC-based server | eudev | Native OpenRC support |

## Security Considerations

1. **Device node permissions**: Ensure sensitive devices (`/dev/mem`, `/dev/kmem`) are restricted to root only
2. **RUN rule safety**: udev RUN rules execute as root — validate scripts before deploying
3. **Symlink conflicts**: Custom rules should use unique symlink paths to avoid collisions
4. **Rule ordering**: Rules are processed in filename order — prefix custom rules with high numbers (99-)
5. **Audit device access**: Monitor `/dev` permissions changes for unauthorized modifications

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Device Management: systemd-udevd vs eudev vs mdev (2026)",
  "description": "Compare Linux device managers: systemd-udevd, eudev, and mdev for self-hosted server device management and GPU passthrough.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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

### What is the difference between udev, systemd-udevd, and eudev?

`udev` is the original Linux device manager. `systemd-udevd` is the version integrated into the systemd project — it's the default on most modern distributions. `eudev` is a Gentoo fork that maintains udev functionality while removing systemd dependencies. All three use the same rule syntax, so rules written for one generally work on all three.

### Can I switch from systemd-udevd to eudev?

Yes, on distributions that support it. Gentoo and Alpine Linux use eudev by default. On systemd-based distributions, switching requires replacing the systemd-udev package and adjusting the init configuration. The rule files in `/etc/udev/rules.d/` are compatible, so your custom rules will carry over.

### When should I use mdev instead of udev?

Use mdev when you need minimal resource usage — in containers, initramfs environments, embedded devices, or rescue systems. mdev handles basic device node creation and permission setting but lacks persistent naming, complex rule matching, and systemd integration. If you need `/dev/disk/by-id/` symlinks or network interface naming, you need udev or eudev.

### How do I create a persistent symlink for a USB device?

First, identify the device's attributes:
```bash
udevadm info -a -p /sys/bus/usb/devices/1-1 | grep -E "ATTRS{idVendor}|ATTRS{idProduct}"
```
Then create a rule:
```bash
# /etc/udev/rules.d/99-usb-devices.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ATTR{idProduct}=="5678", SYMLINK+="mydevice"
```
Reload rules: `udevadm control --reload && udevadm trigger`

### Why did my network interface name change after upgrading?

Modern udev implementations use "predictable network interface names" based on firmware, topology, and MAC address (e.g., `enp3s0` instead of `eth0`). If you prefer traditional naming, you can disable predictable names by creating `/etc/udev/rules.d/80-net-setup-link.rules` with:
```
SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", NAME="eth0"
```
Or add `net.ifnames=0` to your kernel boot parameters.

### Does mdev support hotplugging?

mdev supports basic hotplug detection through the kernel's hotplug mechanism. When a device is added or removed, mdev creates or removes the corresponding device node. However, it doesn't support the rich event handling of udev — no property-based matching, no complex rule conditions, and no integration with service managers. For most embedded and container use cases, mdev's hotplug support is sufficient.

