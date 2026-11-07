---
title: "mkosi vs debos vs LinuxKit in 2026: Which Reproducible OS Image Builder Should You Use?"
date: "2026-11-07"
tags: ["linux", "image-build", "immutable-infrastructure", "devops", "self-hosted"]
draft: false
cover: "/img/screenshots/linuxkit-logo.jpg"
---

Your base image is the largest unowned artifact in your fleet. A stock cloud image carries a package set you never audited, a bootloader you never configured, and a kernel you cannot rebuild identically twice. Then a CVE lands in a package that only exists because the vendor put it there, and the only remediation is to wait for an upstream refresh.

Three projects solve that problem from different angles: **mkosi**, the systemd project's image builder; **debos**, the Go tool that builds Debian's own ARM images; and **LinuxKit**, the toolkit that has shipped inside Docker Desktop's virtual machines for years. All three are actively maintained, all three are Apache or LGPL licensed, and all three produce bootable images from a text file in version control. Choosing wrong costs you weeks of fighting a build system that does not match how your team deploys.

## TL;DR: Quick Verdict

- **You want distribution-native images** with the same packages, users and systemd units you already ship on servers → **mkosi**. It drives `dnf`, `apt`, `pacman` or `zypper` from a single INI-style config and supports incremental builds.
- **You are building Debian or Ubuntu images for boards, and you want recipe-as-YAML with a real VM boundary** → **debos**. This is what Debian uses for its own cloud and ARM images.
- **You want a minimal, immutable appliance image where applications are containers** → **LinuxKit**. No package manager, no drift, and the whole root filesystem is declarative.

If you only remember one line: **mkosi builds the OS you already run, debos builds a distro image reproducibly, LinuxKit builds an appliance.**

## Side-by-Side Comparison

GitHub data pulled on 2026-11-07.

| Dimension | mkosi | debos | LinuxKit |
|---|---|---|---|
| GitHub stars | 2,046 | 737 | 8,668 |
| License | LGPL-2.1-or-later | Apache-2.0 | Apache-2.0 |
| Implementation | Python | Go | Go |
| Input format | `mkosi.conf` (INI sections) | YAML recipe with actions | YAML image definition |
| Output formats | disk, directory, UKI, initrd, tar, repart | raw disk, tarball, OSTree commit | raw, qcow2, ISO, VHD, GCP/AWS images |
| Package source | Native package manager in a chroot | `debootstrap` + `apt` in a VM | Container images, no package manager |
| Build isolation | Namespaces + optional tools tree | fakemachine (KVM/QEMU VM) | Build containers |
| Needs `/dev/kvm` | No | Yes for fakemachine | No |
| Reproducibility lever | `Incremental=`, pinned release, `ToolsTree=` | Pinned snapshot + recipe in git | Pinned image digests |
| Last push | 2026-11-05 | 2026-11-03 | 2026-11-05 |
| Best fit | Fleet images, VM images, UKIs | Debian/Ubuntu board images | Appliances, hypervisor VMs |

The star counts tell you about mindshare, not fit: LinuxKit's 8,668 reflect its role inside Docker Desktop, while debos' 737 understate its importance — Debian's official cloud images depend on it.

## Decision Matrix: Pick by Situation

| Your situation | Recommended tool | Why |
|---|---|---|
| Golden VM image with your existing cloud-init config | mkosi | Produces bootable disk images with your packages, users and units |
| Unified Kernel Image for Secure Boot | mkosi | First-class UKI and `systemd-repart` output |
| Debian/Ubuntu image for a Raspberry Pi fleet | debos | Native `debootstrap` flow, OSTree support, proven on ARM |
| Reproducible build in CI with no privileged daemon | mkosi | No KVM required, no docker-in-docker |
| Minimal appliance for Kubernetes nodes | LinuxKit | Immutable root, only the services you declare |
| Boot a container as the OS (container-native) | bootc | OCI image as the update unit, closest to Docker workflows |
| Custom initrd only | mkosi | `mkosi-initrd` builds one without a full image |

The last row matters more than it looks: if you only need an initrd for a kernel-install hook, mkosi has a dedicated mode and you should not build a whole disk image for it.

## mkosi: Distribution-Native Images, Declaratively

mkosi is a wrapper around `dnf --installroot`, `apt`, `pacman` and `zypper` that produces images rather than installing into the host. That sentence is the whole design: you get the package manager you already trust, but the output is a disk image, a directory tree, an initrd or a Unified Kernel Image.

Installation is unglamorous, which is a feature. Distro packages work if they are v16 or newer; otherwise use the git shim or pipx:

```bash
# Distro package (check the version)
sudo apt install mkosi
mkosi --version

# Or the upstream shim, which always tracks main
git clone https://github.com/systemd/mkosi
ln -s $PWD/mkosi/bin/mkosi ~/.local/bin/mkosi

# Or pipx, which isolates the Python dependencies
pipx install git+https://github.com/systemd/mkosi.git
```

A minimal configuration is a single INI file. This is a realistic starting point rather than a toy — it pins the distribution, produces a bootable disk, and installs three packages:

```ini
[Distribution]
Distribution=ubuntu
Release=noble

[Output]
Format=disk
Bootable=yes

[Content]
Packages=openssh-server
        curl
        systemd-resolved
```

The upstream repository's own config shows the patterns that make mkosi pleasant at scale: a cache directory, a tools tree so the build does not depend on host packages, and incremental builds that reuse previous output:

```ini
[Build]
CacheDirectory=mkosi.cache
History=yes
ToolsTree=yes
Incremental=yes
BuildSources=.

[Output]
Format=directory
OutputDirectory=mkosi.output

[Content]
Packages=
        binutils
        gdb
        wireless-regdb
```

The commands are short enough to live in a Makefile:

```bash
mkosi              # build the image described by mkosi.conf
mkosi -f           # force a clean rebuild
mkosi qemu         # boot the result in a VM
mkosi ssh          # SSH into the running VM
mkosi serve        # serve output over HTTP for netboot
```

![systemd project logo](/img/screenshots/mkosi-systemd-logo.jpg "mkosi is maintained inside the systemd project")

Where mkosi wins is the intersection of "we already run Ubuntu or Fedora" and "we need a repeatable image". Your package list, your repositories, your systemd units, your kernel command line — all in one file, all diffable. Where it loses is heterogeneity: you are building images for the same family of distributions you build packages for.

## debos: Recipes, Actions, and a Real VM Boundary

debos makes Debian-based images from a YAML recipe. Each recipe is a list of actions executed in order inside a fakemachine — a throwaway KVM-backed VM — so a bad `run` action cannot modify your build host.

The official container is the supported entry point. Note that it is used as an executable, and that it needs KVM:

```bash
cd /path/to/recipe-dir
docker run --rm -it --device /dev/kvm --user $(id -u) \
  --workdir /recipes \
  --mount "type=bind,source=$(pwd),destination=/recipes" \
  --security-opt label=disable \
  ghcr.io/go-debos/debos:latest recipe.yaml
```

A real recipe from the project's own test suite is deliberately tiny, which makes the action model obvious:

```yaml
architecture: amd64

actions:
  - action: unpack
    compression: gz
    origin: recipe
    file: base.tar.gz

  - action: overlay
    source: A

  - action: run
    command: find ${ROOTDIR}
```

Real images use the fuller action set — `debootstrap` to create the rootfs, `apt` to install packages, `image-partition` and `filesystem-deploy` to lay down a partitioned disk, then `pack` or `ostree-commit`:

```yaml
architecture: arm64

actions:
  - action: debootstrap
    suite: trixie
    components: [main]
    mirror: https://deb.debian.org/debian

  - action: apt
    packages: [systemd-sysv, openssh-server, ca-certificates]

  - action: image-partition
    imagename: debian-arm64.img
    imagesize: 2GB
    partitiontype: msdos
    partitions:
      - name: root
        fs: ext4
        start: 0%
        end: 100%

  - action: filesystem-deploy
    description: Deploy the rootfs onto the image
```

Running it in GitHub Actions is a documented pattern, which is the strongest argument for debos in a Debian shop:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/go-debos/debos:main
      options: --device=/dev/kvm
    steps:
      - uses: actions/checkout@v4
      - run: debos --fakemachine-backend=kvm --print-recipe recipe.yaml
```

The trade-off is scope. debos is Debian-centric by design: `debootstrap`, `apt` and `ostree` actions assume a Debian-family target. If you need Fedora or Arch images, it is the wrong tool, and the action model that makes it predictable is exactly what you would have to work around.

## LinuxKit: Build an Appliance, Not a Distro

LinuxKit takes the most radical position: the OS is a set of containers. There is no package manager, no `apt upgrade`, no drift. A YAML file lists the kernel, the init images, one-shot boot services and long-running services; `linuxkit build` assembles them into a bootable artifact.

Building the tool is a `make`, and images come from a YAML definition:

```bash
# Install the CLI
go install github.com/linuxkit/linuxkit/src/cmd/linuxkit@latest

# Build the example image as a raw BIOS disk
linuxkit build linuxkit.yml
linuxkit build --format iso-efi linuxkit.yml
linuxkit build --format qcow2 linuxkit.yml
```

The upstream `linuxkit.yml` shows the full model — every component is a pinned image digest, and services are declared rather than installed:

```yaml
kernel:
  image: linuxkit/kernel:6.12.59
  cmdline: "console=tty0 console=ttyS0 console=ttyAMA0"
init:
  - linuxkit/init:075ff447b68e23feef95589c90010a039533e5b5
  - linuxkit/runc:9442aa234715e751a16144f1d4ae3fd1a00fd492
  - linuxkit/containerd:eb5daf20704109ea58abb38d2b808e0c3a7e3717
  - linuxkit/ca-certificates:695574301bd08dda987dccb31e384f7fab3c5c05
onboot:
  - name: dhcpcd
    image: linuxkit/dhcpcd:b87e9ececac55a65eaa592f4dd8b4e0c3009afdb
    command: ["/sbin/dhcpcd", "--nobackground", "-f", "/dhcpcd.conf", "-1"]
services:
  - name: nginx
    image: nginx:1.19.5-alpine
    capabilities:
      - CAP_NET_BIND_SERVICE
      - CAP_CHOWN
      - CAP_SETUID
      - CAP_SETGID
      - CAP_DAC_OVERRIDE
```

Booting and testing is local:

```bash
linuxkit run myimage
linuxkit run --console myimage.qcow2
```

This is the cleanest model for edge appliances and hypervisor VMs: a 60 MB image with a pinned kernel, no shell by default, and an update path that is "replace the image". It is also the worst model for a general-purpose server, because there is no package manager — every new requirement becomes a container or a custom package build. Teams that want container-native OS updates but a more familiar workflow should look at **bootc** (2,338 stars, 2026-11-06), which treats an OCI image as the OS.

## Pitfalls That Cost Real Builds

**1. mkosi version skew is the top support issue.** Distributions still ship mkosi v14-v16, and the config schema changed repeatedly. Check `mkosi --version` before following current documentation; anything below v16 will reject modern keys.

**2. debos without `/dev/kvm` is unusably slow.** Falling back to the QEMU backend turns a two-minute build into twenty. In containers, pass `--device /dev/kvm` and, if the group permissions are unusual, `--group-add "$(stat -c '%g' /dev/kvm)"`.

**3. Recipes are not idempotent.** Neither debos nor mkosi protects you from a `run` action that appends to a file twice during incremental builds. Keep actions declarative, or force clean builds in CI and accept the time cost.

**4. Reproducibility is a pinning discipline, not a feature.** All three tools will produce different images next week unless you pin package snapshots, container digests and base releases. mkosi gives you `Incremental=` and a tools tree; debos gives you git-versioned recipes; LinuxKit gives you digests. None of them give you a lockfile automatically.

**5. ARM64 builds need binfmt or native runners.** `qemu-user-static` plus `binfmt_misc` makes cross-building work, but systemd units that call binaries during the build will run under emulation and occasionally misbehave. Native ARM runners are slower to provision and faster to trust.

**6. An appliance image is not a server image.** LinuxKit's minimalism means no `apt`, no `dnf`, and no rescue shell by default. Plan your debugging path — `linuxkit run --console` and a getty service — before you ship it to a remote site.

**7. Image size grows silently.** Every `Packages=` line and every service image adds up, and a 400 MB "minimal" image is common on the first attempt. mkosi's `Format=directory` output plus `du -sh` per subdirectory catches the biggest offenders early.

**8. Secure Boot needs an explicit decision.** mkosi supports unsigned shim bootloaders and UKI signing; LinuxKit needs signed kernels for locked-down firmware. Decide before you build a fleet, not after the first boot failure.

For adjacent reads: [cloud-init vs Ignition vs Butane](../2026-04-24-cloud-init-vs-ignition-vs-butane-self-hosted-server-bootstrapping-guide-2026/) covers what runs at first boot inside these images, [Packer vs Vagrant vs Multipass](../2026-05-20-self-hosted-dev-environment-tools-packer-vagrant-multipass-guide-2026/) covers the layer above, and [Talos Linux vs Flatcar vs Bottlerocket](../2026-04-21-talos-linux-vs-flatcar-vs-bottlerocket-immutable-container-os-guide-2026/) is the comparison to read if you would rather consume a prebuilt immutable OS than build one. If your build pipeline also produces application containers, our [kaniko vs Buildah vs BuildKit](../2026-06-02-container-image-builders-kaniko-buildah-buildkit/) breakdown covers that half of the chain.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "mkosi vs debos vs LinuxKit in 2026: Which Reproducible OS Image Builder Should You Use?",
  "description": "A 2026 comparison of mkosi, debos and LinuxKit for building reproducible Linux images: real configuration files, install commands, output formats, CI integration and the pitfalls that break builds.",
  "datePublished": "2026-11-07",
  "dateModified": "2026-11-07",
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

**Is mkosi a replacement for Packer?**
Partly. mkosi builds the image itself from a distribution's package repositories; Packer orchestrates builds across multiple builders and clouds. Many teams use mkosi to produce the artifact and keep Packer only for uploading it.

**Does debos require root on the build host?**
No. That is the point of fakemachine: the recipe runs inside a KVM-backed VM, and the container invocation passes your UID. You do need access to `/dev/kvm`.

**Can LinuxKit run a normal Ubuntu workload?**
Not directly. There is no package manager and no writable root by default. You either build your application into a container image and declare it as a service, or you choose a different tool.

**Which one is most reproducible?**
All three can be, but mkosi has the strongest built-in levers (`ToolsTree=`, `Incremental=`, pinned releases and history) and LinuxKit's digest-pinned images are the easiest to audit. debos depends on your apt snapshot discipline.

**Do these tools work in GitHub Actions?**
Yes. mkosi needs no privileged daemon and is the simplest in CI. debos publishes an official action pattern with `--device=/dev/kvm`, which requires a runner that exposes KVM. LinuxKit builds with Docker and works on standard runners.

**What about building images for Raspberry Pi?**
debos is the best-supported path for Debian on ARM boards, including partition layouts and firmware packages. mkosi can target arm64 but expects UEFI-style boot, which the Pi only partially provides.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
