---
title: "Self-Hosted Linux IOMMU/VFIO GPU Passthrough: VFIO, Looking Glass & vendor-reset"
date: "2026-05-23"
tags: ["linux", "virtualization", "gpu", "iommu", "vfio", "kvm"]
draft: false
---

GPU passthrough (also known as VGA passthrough or GPU virtualization) allows you to assign a physical graphics card directly to a virtual machine, giving it near-native graphics performance. This is essential for self-hosted gaming VMs, GPU-accelerated workloads, and media transcoding servers. The Linux IOMMU/VFIO ecosystem provides the kernel infrastructure for device isolation, while tools like Looking Glass and vendor-reset extend the capabilities for practical use.

This guide compares the key components and tools for setting up GPU passthrough on self-hosted Linux systems.

## Understanding IOMMU, VFIO, and GPU Passthrough

The GPU passthrough stack on Linux consists of several layers:

- **IOMMU** (Input/Output Memory Management Unit) — hardware-level memory isolation that prevents devices from accessing unauthorized memory regions. AMD calls this AMD-Vi (formerly IVRS), Intel calls it VT-d.
- **VFIO** (Virtual Function I/O) — the Linux kernel framework that exposes IOMMU-protected devices to userspace, enabling safe device assignment to VMs via KVM/QEMU.
- **GPU passthrough tools** — user-space utilities that manage the binding, configuration, and display aspects of GPU assignment.

Without IOMMU enabled in your BIOS and kernel, VFIO cannot function. The kernel module `vfio-pci` binds to the GPU and prevents the host from claiming it.

## Comparison Table: GPU Passthrough Components

| Feature | VFIO (Kernel) | Looking Glass | vendor-reset |
|---------|--------------|---------------|-------------|
| **Type** | Kernel framework | User-space display client | Kernel module |
| **Purpose** | Device isolation & assignment | Low-latency VM display | GPU reset for re-binding |
| **GitHub Stars** | Kernel (builtin) | 2,300+ | 500+ |
| **License** | GPL v2 | GPL v2 | GPL v2 |
| **Display** | None (bare metal passthrough) | Frame buffer over shared memory | None |
| **GPU Reset** | Manual (unbind/rebind) | N/A | Automatic kernel-level reset |
| **Latency** | Native (0 overhead) | Sub-millisecond | N/A |
| **Multi-GPU** | Yes (multiple VFIO bindings) | One client per VM | One reset per GPU |
| **AMD Support** | Full | Full | Limited |
| **NVIDIA Support** | Full (with workarounds) | Full | Full |

## VFIO Kernel Framework: Device Isolation

VFIO is built into the Linux kernel and provides the foundational device isolation mechanism. When a GPU is bound to `vfio-pci`, it becomes inaccessible to the host OS and can be safely passed through to a KVM virtual machine.

### Enabling IOMMU in the Kernel

For **Intel** processors, add `intel_iommu=on iommu=pt` to your kernel command line:

```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash intel_iommu=on iommu=pt"
sudo update-grub
```

For **AMD** processors, use `amd_iommu=on iommu=pt`:

```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amd_iommu=on iommu=pt"
sudo update-grub
```

After rebooting, verify IOMMU is active:

```bash
dmesg | grep -e DMAR -e IOMMU
# Expected: "DMAR: IOMMU enabled" or "AMD-Vi: IOMMU enabled"
```

### Binding GPU to VFIO-PCI

Identify your GPU's PCI address and vendor/device IDs:

```bash
lspci -nn | grep -i vga
# Example: 01:00.0 VGA compatible controller [0300]: NVIDIA Corporation Device [10de:2489]
```

Configure vfio-pci to claim the GPU at boot:

```bash
# /etc/modprobe.d/vfio.conf
options vfio-pci ids=10de:2489,10de:228b
softdep nvidia pre: vfio-pci
softdep snd_hda_intel pre: vfio-pci
```

The second ID (`10de:228b`) is the GPU's audio controller, which must also be bound to VFIO.

### KVM/QEMU Configuration

Add the GPU to your VM's XML configuration via `virsh edit`:

```xml
<hostdev mode='subsystem' type='pci' managed='yes'>
  <source>
    <address domain='0x0000' bus='0x01' slot='0x00' function='0x0'/>
  </source>
  <rom bar='on'/>
</hostdev>
```

For a full Docker-based VM management setup, you can use [libvirt](https://libvirt.org/) with a Docker Compose wrapper:

```yaml
version: "3.8"
services:
  libvirt:
    image: libvirt/libvirt
    container_name: libvirt
    privileged: true
    volumes:
      - /var/run/libvirt:/var/run/libvirt
      - /dev/vfio:/dev/vfio
      - ./vms:/var/lib/libvirt
    network_mode: host
    restart: unless-stopped
```

## Looking Glass: Low-Latency Display

[Looking Glass](https://github.com/gnif/LookingGlass) solves the biggest problem with GPU passthrough: when the GPU is assigned to the VM, you can no longer see the VM's display on the host monitor. Looking Glass captures the VM's frame buffer via shared memory and renders it on the host with sub-millisecond latency.

### Installation and Configuration

On the **guest VM** (Windows or Linux), install the Looking Glass host:

```bash
# Windows: Download the IVSHMEM driver and Looking Glass host from GitHub releases
# Or via Chocolatey:
choco install looking-glass-host
```

On the **host**, build and run the Looking Glass client:

```bash
# Install dependencies
sudo apt install binutils-dev cmake libfontconfig1-dev   libgl-dev libspice-protocol-dev libwayland-dev   libx11-dev libxfixes-dev libxkbcommon-dev   libxpresent-dev libxss-dev libxrandr-dev   pkg-config wayland-protocols

# Build
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

### Shared Memory Configuration

Looking Glass requires an IVSHMEM device:

```bash
# /etc/modprobe.d/kvmfr.conf
options kvmfr devices=1 static_size_mb=128

# Load the module
sudo modprobe kvmfr

# Set permissions
sudo tee /etc/udev/rules.d/99-kvmfr.rules << 'UDEV'
SUBSYSTEM=="kvmfr", OWNER="your-user", GROUP="libvirt", MODE="0660"
UDEV
sudo udevadm trigger
```

## vendor-reset: GPU Reset for Re-Binding

[vendor-reset](https://github.com/gnif/vendor-reset) is a kernel module that provides GPU reset functionality. This is critical when you need to re-bind a GPU between the host and a VM without rebooting.

### The Problem

When a VM shuts down, some GPUs (especially NVIDIA) do not properly reset, leaving them in a state where the host kernel cannot re-bind them. The only solution was traditionally a full system reboot.

### The Solution

vendor-reset implements vendor-specific reset sequences:

```bash
# Install dependencies
sudo apt install dkms linux-headers-$(uname -r) git

# Clone and build
git clone https://github.com/gnif/vendor-reset.git
cd vendor-reset
sudo dkms add .
sudo dkms install vendor-reset/0.1.0

# Load the module
sudo modprobe vendor-reset
```

### Usage

After loading vendor-reset, you can reset and re-bind a GPU:

```bash
# Reset the GPU
echo 1 | sudo tee /sys/bus/pci/devices/0000:01:00.0/reset

# Unbind from vfio-pci
echo "0000:01:00.0" | sudo tee /sys/bus/pci/drivers/vfio-pci/unbind

# Re-bind to the native driver
echo "0000:01:00.0" | sudo tee /sys/bus/pci/drivers/nvidia/bind
```

## GPU Passthrough in Virtualization Platforms

### Proxmox VE

Proxmox has native VFIO support. Add to `/etc/pve/qemu.conf`:

```
hostpci0: 01:00,pcie=1,x-vga=1
```

Then enable VFIO in the VM hardware settings via the Proxmox web UI.

### KVM with virt-manager

Use the virt-manager GUI to add PCI devices:
1. Open VM settings → Add Hardware → PCI Host Device
2. Select your GPU and its audio controller
3. Enable "ROM Bar" and "PCIe" options

### Docker-Based VM Management

For containerized VM orchestration, combine libvirt with Docker Compose:

```yaml
version: "3.8"
services:
  vm-manager:
    image: dorowu/ubuntu-desktop-lxde-vnc
    container_name: vm-gpu-passthrough
    privileged: true
    devices:
      - /dev/vfio/0
    volumes:
      - /var/run/libvirt:/var/run/libvirt
      - /dev/dri:/dev/dri
    environment:
      - VNC_PASSWORD=your-password
    ports:
      - "6901:6901"
    restart: unless-stopped
```

## Why Self-Host GPU Passthrough?

Running GPU-accelerated VMs on self-hosted hardware offers significant advantages over cloud alternatives. Cloud GPU instances (AWS p3/p4, Azure NC-series, GCP A2) cost $2-15/hour — running a local server with GPU passthrough pays for itself within months for sustained workloads.

For media transcoding servers (Jellyfin, Plex, Emby), GPU passthrough enables hardware-accelerated encoding that handles multiple 4K streams simultaneously. For development and testing, it enables GPU-accelerated container builds, CUDA development environments, and ML inference servers — all running on bare-metal hardware with zero cloud egress fees.

For related reading on GPU management in containerized environments, see our [GPU management in Kubernetes guide](../2026-05-04-self-hosted-gpu-management-kubernetes-nvidia-operator-container-toolkit-volcano/) and [GPU monitoring tools comparison](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/).

If you're interested in the broader eBPF and kernel tracing ecosystem, our [eBPF tracing tools guide](../2026-04-26-bpftrace-vs-bcc-vs-sysdig-self-hosted-ebpf-tracing-guide-2026/) covers the tools used to profile GPU and kernel performance.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux IOMMU/VFIO GPU Passthrough: VFIO, Looking Glass & vendor-reset",
  "description": "Complete guide to Linux GPU passthrough using VFIO, Looking Glass for low-latency display, and vendor-reset for GPU reset management. Compare tools and configure IOMMU device isolation for KVM virtual machines.",
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

### Do I need an IOMMU-compatible CPU for GPU passthrough?

Yes. Your CPU and motherboard must support IOMMU (Intel VT-d or AMD-Vi). Most consumer Intel and AMD CPUs from 2012 onwards support it, but you must enable it in the BIOS/UEFI settings. Check your motherboard manual for the exact option name — it is often listed under "Advanced > CPU Configuration" or "Chipset > IOMMU."

### Can I pass through an NVIDIA GPU to a Linux VM?

Yes, NVIDIA GPUs work with both Windows and Linux VMs. For Linux guests, install the proprietary NVIDIA driver inside the VM. Note that NVIDIA's vGPU (virtual GPU) feature requires enterprise licensing, but full passthrough (assigning the entire GPU to one VM) works with consumer cards using standard drivers.

### What is the "Error 43" issue with NVIDIA GPU passthrough?

Error 43 occurs when the NVIDIA driver detects it is running inside a VM and refuses to initialize. Modern VFIO (Linux kernel 5.1+) hides the hypervisor signature by default, preventing this issue. If you still encounter it, add `kvm hide-kvm=on` to your VM configuration or use the `vendor_id` override in your libvirt XML.

### Is Looking Glass better than RDP or VNC for VM display?

Looking Glass provides significantly lower latency (sub-millisecond vs 30-100ms for RDP/VNC) because it uses shared memory instead of network protocols. It also supports higher refresh rates (up to 240Hz) and does not compress the image. However, it only works when the GPU is passed through to the VM — RDP/VNC work for any VM configuration.

### Can I pass through multiple GPUs to different VMs?

Yes, if your motherboard has multiple PCIe slots and your CPU provides enough PCIe lanes. Each GPU needs its own IOMMU group (or you need ACS override patches). Use `find /sys/kernel/iommu_groups/ -type l` to check IOMMU groupings. GPUs in the same IOMMU group must be passed through together.

### Does vendor-reset work with all GPUs?

No. vendor-reset currently supports specific NVIDIA (Turing, Ampere) and AMD (Navi, Vega) architectures. Check the project's GitHub page for the supported device list. For unsupported GPUs, the traditional unbind/rebind sequence or a full system reboot may still be necessary.
