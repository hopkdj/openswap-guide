---
title: "Windows and macOS in Docker in 2026: dockur/windows vs Docker-OSX vs Plain QEMU"
date: "2026-10-18"
tags: ["docker", "virtualization", "qemu", "self-hosted", "comparison"]
draft: false
cover: "/img/screenshots/windows-docker.jpg"
---

# Windows and macOS in Docker in 2026: dockur/windows vs Docker-OSX vs Plain QEMU

A `docker compose up` that boots a licensed copy of Windows 11, hands you a browser-based console on port 8006, and lets you RDP into it — that is not a thought experiment anymore. Two projects with a combined **106,000+ GitHub stars** have turned "foreign OS in a container" into a supported workflow. The catch is that the three approaches people actually use (dockur/windows, Docker-OSX, and raw QEMU) solve different problems, and two of them carry licensing obligations that will bite you in production.

I have deployed all three on KVM-capable Linux hosts. Here is what actually works, what breaks, and which one to pick.

## TL;DR — Quick Verdict

**Use `dockur/windows` if you need a disposable Windows desktop for testing, RDP access, or running Windows-only tooling from a Linux server.** It is the most polished of the three: automatic ISO download, VNC web console, and a compose file you can read in 20 seconds.

**Use `sickcodes/Docker-OSX` only for security research or CI jobs that need a real macOS userland** — and only on Apple hardware if you care about the EULA. It is powerful, but it has not been pushed to in almost a year.

**Skip both and use plain QEMU with libvirt if the VM is long-lived, needs GPU passthrough, or is part of your infrastructure.** Containers are a packaging convenience here, not a virtualization layer — underneath, everything is QEMU/KVM.

## Head-to-Head Comparison

| Dimension | dockur/windows | Docker-OSX | Plain QEMU + libvirt |
|---|---|---|---|
| GitHub stars | **53,645** | **52,988** | 13,871 (mirror) |
| Last push | 2026-10-08 | 2025-11-11 | 2026-10-17 |
| Guest OS | Windows 11/10/Server, Tiny11 | macOS Catalina → Sonoma | Anything |
| Requires `/dev/kvm` | Yes | Yes | Yes (or TCG, very slow) |
| Web console | Built in, port 8006 | VNC on port 5999 | External (noVNC) |
| Auto-install ISO | Yes (downloads from Microsoft) | Yes (recovery images) | No, manual |
| GPU passthrough | Limited | No | **Full VFIO** |
| Persistence | `/storage` volume | `/home/arch/OSX-KVM` | Any qcow2/raw |
| Config effort | 10 minutes | 20–40 minutes | 1–3 hours |
| Best for | Windows tooling | macOS research/CI | Production VMs |

The star counts are close, but the maintenance signals are not. dockur/windows shipped changes in the last two weeks; Docker-OSX's last commit was in November 2025. For a homelab that is fine. For anything you depend on, it matters.

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Need IE/Edge-only legacy app on a Linux box | dockur/windows | ISO automation + RDP, nothing else to configure |
| CI job must build/sign a macOS binary | Docker-OSX | Real Darwin userland, X11 forwarding baked in |
| Need a Windows VM with a passed-through GPU | QEMU + VFIO | Containers wrap QEMU but hide the PCI topology |
| Testing ransomware behaviour in isolation | QEMU with snapshots | Snapshot rollback is trivial, container is not |
| Running 5+ Windows VMs on one host | QEMU + libvirt | One daemon, one API, real resource scheduling |
| One-off Windows install to test an MSI | dockur/windows | Fastest path from zero to desktop |

## dockur/windows — Windows in a Compose File

The project wraps QEMU, KVM, a noVNC console, and an automated Windows installer into a single image. On first boot it downloads the ISO from Microsoft's CDN, runs an unattended install, and exposes the desktop at `http://host:8006`.

The real compose definition from the repo:

```yaml
services:
  windows:
    image: dockurr/windows
    container_name: windows
    environment:
      VERSION: "11"
    devices:
      - /dev/kvm
      - /dev/net/tun
    cap_add:
      - NET_ADMIN
    ports:
      - 8006:8006
      - 3389:3389/tcp
      - 3389:3389/udp
    volumes:
      - ./windows:/storage
    restart: always
    stop_grace_period: 2m
```

Bring it up with `docker compose up -d` and watch the install at `http://localhost:8006`. Supported `VERSION` values include `11`, `10`, `8.1`, `2022`, `2019`, and `tiny11`. You can also point `VERSION` at a custom ISO URL, which is how you install an existing image or a non-English build.

**What it does well:** the unattended install is genuinely unattended. There is no "press any key to boot from CD" race, no manual partitioning, no VirtIO driver hunting — the image injects the drivers and autounattend answer file for you. For a homelab workflow of "I need Windows for 45 minutes", this is the lowest-friction option I have used.

**Where it hurts:** you are trusting a third-party image to fetch and patch an OS. Pin the image digest in production, and keep `/storage` on a filesystem that supports the disk sizes you need — the default disk grows to 64 GB, allocated sparsely. Also note `cap_add: NET_ADMIN` is required for the built-in NAT/DHCP networking; if you drop it, the guest boots without a network.

## Docker-OSX — macOS Without an Apple Logo on the Case

Docker-OSX predates dockur/windows and does the same trick for macOS: QEMU + OpenCore bootloader + a recovery image, packaged in Docker. The canonical invocation from its README is deliberately minimal:

```bash
docker run -it \
    --device /dev/kvm \
    -p 50922:10022 \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e "DISPLAY=${DISPLAY:-:0.0}" \
    sickcodes/docker-osx:latest
```

Variants exist for each macOS release (`docker-osx:sonoma`, `docker-osx:ventura`, `docker-osx:catalina`), plus an `auto` tag that builds a fully automated installer with a configurable disk size and CPU count.

**What it does well:** it is the only practical way to get a real Darwin userland in CI for cross-compiling, codesigning, or reproducing macOS-only bugs. X11 forwarding means the GUI shows up in your existing session. The project also documents USB passthrough for iPhone/iOS work, which is unusual and genuinely useful for mobile QA.

**Where it hurts:** performance is the big one. Without Apple's Virtualization.framework, you get QEMU's emulation of Apple's hardware quirks — expect a login that takes minutes and a UI that feels like 2012 hardware. Networking is another trap: the default user-mode network gives you outbound access but no inbound except the SSH port you map.

**The licensing point is not a footnote.** Apple's software licence permits macOS virtualization only on Apple-branded hardware. Running Docker-OSX on a rented Linux box is a licence violation regardless of what the kernel module allows. If that risk matters to your organisation, this option is off the table.

## Plain QEMU — What the Containers Are Hiding

Both projects are wrappers. A minimal Windows VM directly on QEMU looks like this:

```bash
qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 4 -m 8192 \
  -drive file=win11.qcow2,if=virtio,format=qcow2 \
  -cdrom Win11_24H2_English_x64.iso \
  -boot d \
  -device virtio-net-pci,netdev=n0 \
  -netdev user,id=n0,hostfwd=tcp::3389-:3389 \
  -vga qxl -display none -vnc :1
```

Then connect with any VNC client to port 5901, or add `-spice` and use a SPICE viewer for clipboard and USB redirection.

**What it does well:** everything the containers cannot. `-device vfio-pci,host=01:00.0` gives the guest a real GPU. `qemu-img snapshot` gives you instant rollback. `virsh` gives you an API, autostart, and resource limits that survive reboots. Cloud-init and `virt-install` make provisioning repeatable.

**Where it hurts:** the Windows installer will not see your VirtIO disk without loading drivers. You need the `virtio-win.iso` attached as a second CD-ROM and a manual "Load driver" step during setup. That single detail is why most people reach for dockur/windows first — it is the exact friction the wrapper removes.

## Pitfalls That Will Cost You an Evening

**1. `/dev/kvm` is not optional.** Without it QEMU falls back to TCG software emulation and a Windows boot goes from 40 seconds to 25 minutes. Check with `ls -l /dev/kvm` and confirm your user is in the `kvm` group. Inside a VM, you need nested virtualization enabled on the host (`kvm_intel.nested=1`), and on many cloud providers the instance type simply does not expose it.

**2. Never expose the console port.** Port 8006 is an unauthenticated VNC session by default. Bind it to localhost and reach it through an SSH tunnel or a reverse proxy with auth. The same applies to RDP: put it behind a VPN, not on a public IP.

**3. Stop the guest, do not kill the container.** A `docker rm -f` on a running Windows guest is equivalent to yanking the power cord. Use `docker stop` and respect the `stop_grace_period: 2m` in the compose file — Windows needs that time to flush NTFS journals.

**4. Disk images grow and never shrink.** A qcow2 that has seen a Windows update will not return space when you delete files inside the guest. Plan capacity, or run `virt-sparsify` during maintenance windows.

**5. Activation and licensing travel with the image.** Copying a `/storage` volume to another host clones the machine identity. Windows will deactivate, and for macOS you have moved a licensed install to different hardware.

**6. Clock drift breaks TLS.** Guests that sleep and resume can drift minutes out of sync, which shows up as certificate errors inside the guest. Install the guest agent or enable NTP in the guest, not just on the host.

## FAQ

### Can I run Windows in Docker without KVM?

Technically yes, with `VERSION=tcg` or by overriding the QEMU flags, but it is unusable for a desktop. Booting takes tens of minutes and the UI is measured in seconds per frame. Without `/dev/kvm`, use a real hypervisor or a cloud VM.

### Is running Windows in a container legal?

The container is just packaging; the licence question is about Windows itself. You need a valid Windows licence for the edition you install, and Microsoft's terms do not permit arbitrary re-imaging. For short-lived testing, use a volume licence or a dev subscription. macOS is stricter: virtualisation is only licensed on Apple hardware.

### Which project is faster, dockur/windows or Docker-OSX?

For Windows, dockur/windows is effectively native KVM speed with VirtIO drivers — near bare metal for CPU-bound work. Docker-OSX is noticeably slower because macOS expects Apple's own virtualisation stack; expect a sluggish UI even on fast hardware.

### Can I get GPU acceleration inside the container?

Not really. Docker's device mapping does not give you clean PCI passthrough for a GPU. If you need CUDA, DirectX, or hardware video encode inside the guest, run QEMU directly with VFIO and pass the whole PCI device — containers add a layer that obscures IOMMU grouping.

### How do I back up a Windows container VM?

Stop the container, then copy the `/storage` directory — it contains the qcow2 disk and the UEFI variables. Restoring is the reverse. For consistent backups of a running guest, use `qemu-img snapshot` from the host instead of copying a live disk.

### Does this replace a real hypervisor?

No. If you are running more than a couple of guests, need live migration, snapshots, or a management API, use libvirt, Proxmox, or XCP-ng. Docker is a delivery mechanism for a single QEMU process, not a virtualisation platform.

## Related Reading

If you want a web UI in front of your KVM guests instead of raw compose files, our [KVM web management comparison](../2026-06-03-self-hosted-kvm-web-management-webvirtcloud-kimchi-cockpit-guide/) covers WebVirtCloud, Kimchi, and Cockpit. For emulating non-x86 hardware and firmware rather than whole desktop OSes, see the [firmware emulation guide](../2026-09-23-firmware-emulation-renode-qemu-gem5-comparison/). And if you are standardising container operations across hosts, the [self-hosted Docker control panel comparison](../2026-10-07-self-hosted-docker-control-panels-dokploy-komodo-arcane/) is the natural next step.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Windows and macOS in Docker in 2026: dockur/windows vs Docker-OSX vs Plain QEMU",
  "description": "A practical comparison of running Windows and macOS virtual machines inside Docker containers using dockur/windows, Docker-OSX, and plain QEMU with KVM, including real compose configs, licensing constraints, and performance pitfalls.",
  "datePublished": "2026-10-18",
  "dateModified": "2026-10-18",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
