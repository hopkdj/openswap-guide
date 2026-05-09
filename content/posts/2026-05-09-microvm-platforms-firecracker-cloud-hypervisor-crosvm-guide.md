---
title: "Best Self-Hosted MicroVM Platforms 2026: Firecracker vs Cloud-Hypervisor vs crosvm"
date: "2026-05-09"
tags: ["virtualization", "microvm", "serverless", "containers", "firecracker", "cloud-hypervisor", "crosvm"]
draft: false
---

MicroVMs are lightweight virtual machines that combine the isolation and security of traditional VMs with the startup speed and resource efficiency of containers. They have become the backbone of serverless computing platforms, secure container runtimes, and multi-tenant cloud infrastructure.

In this guide, we compare three leading open-source microVM monitors: **Firecracker** (by AWS), **Cloud-Hypervisor** (by Rust-VMM), and **crosvm** (by Google/Chromium OS). Each takes a different approach to balancing security, performance, and ease of use.

## What Are MicroVMs?

MicroVMs strip down the traditional hypervisor to its essentials:

- **Minimal device emulation**: Only virtio devices (network, block), no legacy hardware
- **Reduced attack surface**: Smaller TCB (Trusted Computing Base) than full VMs
- **Fast boot times**: Sub-125ms startup vs. seconds for traditional VMs
- **Low memory overhead**: ~5MB per microVM vs. 100MB+ for full VMs
- **Strong isolation**: Hardware-enforced boundaries via KVM

This makes microVMs ideal for serverless functions, secure container sandboxes, and multi-tenant edge computing.

## Firecracker

**Stars**: 34,188+ | **Language**: Rust | **License**: Apache 2.0 | **GitHub**: [firecracker-microvm/firecracker](https://github.com/firecracker-microvm/firecracker)

Firecracker is the most widely adopted microVM solution, developed by AWS to power Lambda and Fargate. It prioritizes security and simplicity over feature richness.

### Architecture

Firecracker uses a minimalistic design:

- Single-process architecture (no daemon)
- KVM-based hardware virtualization
- Only virtio-net and virtio-block device emulation
- No legacy device support (no VGA, no ACPI beyond basics)
- Built-in rate limiting for network and I/O

### Deployment

Firecracker provides a RESTful API via its binary:

```bash
# Download Firecracker
curl -L -o firecracker https://github.com/firecracker-microvm/firecracker/releases/download/v1.11.0/firecracker-v1.11.0-x86_64
chmod +x firecracker

# Start Firecracker with a config
./firecracker --api-sock /tmp/firecracker.socket --config-file vm-config.json
```

A typical VM configuration:

```json
{
  "boot-source": {
    "kernel_image_path": "./vmlinux.bin",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "./rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "AA:FC:00:00:00:01",
      "host_dev_name": "tap0"
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 512,
    "smt": false
  }
}
```

### Docker Compose Setup

For containerized management, use `firecracker-containerd`:

```yaml
version: "3.8"
services:
  firecracker-containerd:
    image: public.ecr.aws/firecracker-containerd/firecracker-containerd:latest
    privileged: true
    volumes:
      - /dev/kvm:/dev/kvm
      - ./config:/etc/firecracker-containerd
    ports:
      - "2376:2376"
    restart: unless-stopped
```

## Cloud-Hypervisor

**Stars**: 5,615+ | **Language**: Rust | **License**: Apache 2.0 | **GitHub**: [cloud-hypervisor/cloud-hypervisor](https://github.com/cloud-hypervisor/cloud-hypervisor)

Cloud-Hypervisor is a next-generation VMM focused on modern cloud workloads. It supports a broader feature set than Firecracker while maintaining a strong security posture.

### Key Features

- **CPU/memory hotplug**: Add resources to running VMs
- **Device hotplug**: Add/remove virtio devices at runtime
- **Multiple architectures**: x86_64 and AArch64 support
- **vhost-user devices**: Offload networking and storage to external processes
- **Direct kernel boot**: No BIOS required
- **TDX/SEV support**: Hardware memory encryption for enhanced security

### Deployment

```bash
# Install from source
git clone https://github.com/cloud-hypervisor/cloud-hypervisor.git
cd cloud-hypervisor
cargo build --release

# Or install via package manager
sudo apt install cloud-hypervisor
```

Launch a VM:

```bash
cloud-hypervisor \
  --kernel ./hypervisor-fw \
  --disk path=./focal-server-cloudimg.img \
  --cpus boot=4 \
  --memory size=1024M \
  --net tap=,mac=,ip=,mask=
```

Cloud-Hypervisor also supports a REST API:

```bash
cloud-hypervisor --api-socket /tmp/ch-api.socket &
curl --unix-socket /tmp/ch-api.socket -i http://localhost/api/v1/vm.create \
  --json '{"cpus":{"boot_vcpus":2},"memory":{"size":536870912}}'
```

### Docker Compose

```yaml
version: "3.8"
services:
  cloud-hypervisor:
    image: ghcr.io/cloud-hypervisor/cloud-hypervisor:latest
    privileged: true
    devices:
      - /dev/kvm:/dev/kvm
    volumes:
      - ./images:/images
      - ./configs:/configs
    command: ["--api-socket", "/tmp/ch-api.socket"]
    restart: unless-stopped
```

## crosvm (Chrome OS Virtual Machine Monitor)

**Stars**: 1,203+ | **Language**: Rust | **License**: BSD-3-Clause | **Source**: [chromium.googlesource.com/crosvm](https://chromium.googlesource.com/chromiumos/platform/crosvm/)

crosvm is the VMM powering Chrome OS Linux VM support (Crostini). It is optimized for running Linux desktop workloads inside isolated VMs and has expanded to support server use cases.

### Key Features

- **Wayland/GPU forwarding**: Share host GPU with guest VMs
- **Sound forwarding**: Pipe audio between host and guest
- **File sharing**: 9p/virtiofs for seamless host-guest file access
- **USB passthrough**: Direct USB device access
- **Sandboxed devices**: Each device runs in a separate sandbox process

### Running a VM

```bash
crosvm run \
  --kernel ./vmlinux \
  --disable-sandbox \
  -r ./rootfs.ext4 \
  -p "console=ttyS0" \
  -c 2 \
  -m 512
```

For server deployments without desktop features:

```yaml
version: "3.8"
services:
  crosvm:
    image: ghcr.io/nicknisi/crosvm:latest
    privileged: true
    devices:
      - /dev/kvm:/dev/kvm
    volumes:
      - ./images:/images
    command: ["run", "--disable-sandbox", "--kernel", "/images/vmlinux", "-r", "/images/rootfs.ext4"]
    restart: unless-stopped
```

## Comparison Table

| Feature | Firecracker | Cloud-Hypervisor | crosvm |
|---------|-------------|-------------------|--------|
| **Stars** | 34,188+ | 5,615+ | 1,203+ |
| **Language** | Rust | Rust | Rust |
| **License** | Apache 2.0 | Apache 2.0 | BSD-3-Clause |
| **CPU Hotplug** | No | Yes | No |
| **Memory Hotplug** | No | Yes | No |
| **Device Hotplug** | No | Yes | Partial |
| **vhost-user** | No | Yes | Partial |
| **TDX/SEV** | No | Yes | No |
| **GPU Forwarding** | No | Partial (virgl) | Yes (Wayland) |
| **Multi-arch** | x86_64, ARM64 | x86_64, AArch64 | x86_64, ARM64 |
| **API** | REST (Unix socket) | REST (Unix socket) | CLI only |
| **Best For** | Serverless, Lambda-style | Cloud VMs, Kubernetes | Desktop VMs, Chrome OS |

## Performance Comparison

| Metric | Firecracker | Cloud-Hypervisor | crosvm |
|--------|-------------|-------------------|--------|
| **Boot Time** | 125ms | 200ms | 300ms |
| **Memory Overhead** | ~5MB | ~10MB | ~15MB |
| **Network Throughput** | ~25 Gbps | ~30 Gbps | ~20 Gbps |
| **Disk IOPS** | ~100K | ~120K | ~80K |
| **Max vCPUs** | 32 | 512 | 24 |
| **Max Memory** | 128 GB | 1 TB | 64 GB |

## Choosing the Right MicroVM Platform

### Choose Firecracker if:
- You need battle-tested security (powers AWS Lambda and Fargate)
- Your workload fits the serverless model (short-lived, stateless functions)
- You want the smallest possible attack surface
- You need mature tooling (firecracker-containerd, Ignite)

### Choose Cloud-Hypervisor if:
- You need CPU/memory hotplug for dynamic resource allocation
- You run long-lived workloads that need resource scaling
- You require hardware memory encryption (TDX/SEV)
- You want broader device support while keeping a Rust-based security model

### Choose crosvm if:
- You need GPU acceleration or desktop workload support
- You are building Chrome OS-compatible environments
- You need seamless file sharing between host and guest
- You want Wayland display forwarding

## Security Considerations

All three platforms share strong security foundations:

- **Rust memory safety**: No buffer overflows, use-after-free, or null pointer dereferences
- **KVM isolation**: Hardware-enforced VM boundaries
- **Minimal device model**: Fewer emulated devices means smaller attack surface
- **Seccomp filters**: Syscall restriction to prevent escape

Additional hardening steps:

1. **Run with minimal privileges**: Drop all capabilities except CAP_SYS_ADMIN for KVM access
2. **Use read-only root filesystems**: Prevent guest-side persistence attacks
3. **Network isolation**: Use dedicated TAP interfaces with firewall rules
4. **Rate limiting**: Firecracker has built-in rate limiting; others require external configuration
5. **Audit logs**: Monitor VM creation, destruction, and resource usage

## Why Self-Host MicroVMs?

Running your own microVM infrastructure gives you several advantages over managed serverless platforms:

**Cost efficiency**: At scale, self-hosted microVMs are significantly cheaper than AWS Lambda or Google Cloud Run. You pay only for hardware and electricity, with no per-invocation markup. For workloads with millions of daily invocations, the savings are substantial.

**Data sovereignty**: All compute happens on your hardware. There is no risk of your code or data being accessed by cloud provider staff or subject to foreign jurisdiction subpoenas. This is critical for healthcare, financial services, and government workloads.

**Custom runtime support**: Managed serverless platforms restrict the languages and runtimes you can use. With self-hosted microVMs, you can run any binary — custom runtimes, native code, or proprietary software — without vendor approval.

**No cold start penalties**: While managed serverless platforms have notorious cold start times of several seconds, a self-hosted microVM pool can maintain warm instances ready to accept traffic in under 100ms. You control the lifecycle entirely.

**Network control**: Full control over VPC configuration, routing, and security groups. No NAT gateway charges, no VPC peering complexity, and direct access to on-premises resources.

For container security sandboxing, see our [gVisor vs Kata Containers vs Firecracker guide](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/). For container virtualization alternatives, check our [Incus vs LXD vs Podman comparison](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide-2026/). For immutable container OS options, read our [Talos Linux vs Flatcar vs Bottlerocket guide](../2026-04-21-talos-linux-vs-flatcar-vs-bottlerocket-immutable-container-os-guide-2026/).

## FAQ

### What is the difference between a microVM and a container?

MicroVMs use hardware virtualization (KVM) to provide strong isolation between workloads, while containers share the host kernel with namespace-based isolation. MicroVMs offer better security boundaries — a kernel exploit in one microVM cannot affect the host or other VMs. Containers are lighter but share the kernel attack surface. MicroVMs are ideal for multi-tenant environments where untrusted code runs alongside other workloads.

### Can Firecracker run Windows guests?

No. Firecracker deliberately does not support Windows or any OS requiring BIOS/UEFI. It only supports Linux guests with direct kernel boot. If you need Windows VMs, Cloud-Hypervisor has partial Windows support, though it is not optimized for desktop workloads.

### How does Cloud-Hypervisor compare to QEMU?

Cloud-Hypervisor is much more focused than QEMU. While QEMU emulates hundreds of legacy devices (VGA, IDE, serial, parallel ports), Cloud-Hypervisor only supports virtio devices. This makes it faster, more secure, and simpler to audit. QEMU boot times are typically 2-5 seconds; Cloud-Hypervisor achieves sub-second boots.

### Is crosvm production-ready for server workloads?

crosvm is production-ready for its primary use case (Chrome OS Linux VMs). For server workloads, it is less mature than Firecracker or Cloud-Hypervisor. The lack of a REST API and limited device hotplug support make it harder to manage in automated environments. However, its GPU forwarding and file sharing capabilities are unmatched.

### How many microVMs can run on a single host?

This depends on your workload. Firecracker is designed to run thousands of microVMs per host. AWS Lambda runs millions of microVMs across its fleet. A typical 64-core server with 256GB RAM can comfortably host 500-1,000 microVMs running lightweight serverless functions. Memory is usually the limiting factor, not CPU.

### Do microVMs support GPU passthrough?

Firecracker does not support GPU passthrough. Cloud-Hypervisor supports virgl for virtual GPU rendering. crosvm has the best GPU support with Wayland forwarding, allowing the guest to use the host GPU for acceleration. For ML workloads requiring GPU access, crosvm or Cloud-Hypervisor are the better choices.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted MicroVM Platforms 2026: Firecracker vs Cloud-Hypervisor vs crosvm",
  "description": "Compare the top open-source microVM monitors — Firecracker, Cloud-Hypervisor, and crosvm — with Docker Compose setups, performance benchmarks, and security analysis.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
