---
title: "Microsandbox vs SmolVM vs smolBSD in 2026: Which MicroVM Sandbox Should Run Your Untrusted Code?"
date: "2026-10-27"
tags: ["sandboxing", "microvm", "isolation", "self-hosted", "security"]
draft: false
cover: "/img/screenshots/microsandbox-overview.jpg"
---

You just let a plugin system, a CI job, or a user-submitted script execute on your server. A container was supposed to contain it — except a container shares your kernel, and one kernel exploit later your "sandbox" is a shell on the host. Namespaces are an isolation *convenience*, not a security boundary. The boundary is a hypervisor, and in 2026 three projects make it cheap enough to use per-job instead of per-datacenter.

**Microsandbox** (8,819 stars, Apache-2.0) runs OCI images inside local microVMs with fork and snapshot. **SmolVM** (6,845 stars, Apache-2.0) embeds branchable microVMs into your own software with SDKs for four languages. **smolBSD** (726 stars, BSD-2-Clause) takes a different route entirely: it builds a minimal NetBSD image and boots it in about 10 milliseconds under QEMU or Firecracker.

## TL;DR: The 90-Second Verdict

- **You want "docker run, but with a hypervisor in the way"** → **Microsandbox**. Familiar image/exec/shell semantics, sub-100 ms boot, snapshot and fork of live sandboxes.
- **You are writing an application that spawns sandboxes from inside its own code** → **SmolVM**. Embeddable via npm, PyPI, crates.io and Go, with persistable and branchable machines.
- **You want the smallest possible attack surface and do not need Linux compatibility** → **smolBSD**. A ~10 ms NetBSD microVM is about as little running code as you can put next to untrusted input.
- **Do not** treat Firecracker, gVisor or Kata as substitutes for these three. Those are primitives; these are products that put a usable interface on top.

## Head-to-Head Comparison

| Dimension | Microsandbox | SmolVM | smolBSD |
|---|---|---|---|
| GitHub stars | 8,819 | 6,845 | 726 |
| Last push | 2026-10-27 | 2026-10-27 | 2026-10-27 |
| Language | Rust | Rust | Shell |
| License | Apache-2.0 | Apache-2.0 | BSD-2-Clause |
| Guest OS | Any OCI image (Linux) | Any OCI image (Linux) | NetBSD (amd64 / i386 / aarch64) |
| Interfaces | `msb` CLI + npm/Rust/Python/Go SDKs | `smolvm` CLI + npm/PyPI/crates/Go | `smoler.sh` + QEMU/Firecracker |
| Boot time | <100 ms average (vendor figure) | under 1 second | ~10 ms (PVH boot) |
| Host requirement | KVM on Linux, Apple Silicon, WHP on Windows | KVM / macOS / Windows hypervisor | QEMU or Firecracker + bmake |
| Snapshot / fork | Yes, fork a running sandbox | Yes, branchable machines | Rebuild from SMOLerfile |
| Persistence | Named sandboxes, detach mode | Machines persist across restarts | Image is the artifact |
| GPU / desktop | No | No | No |
| Maturity | Beta (upstream warning) | New, active | Small but focused |
| Best fit | Dev sandboxes, CI jobs, plugin execution | Embedding VMs in your product | Minimal-service isolation |

## Decision Matrix: Match the Boundary to the Threat

| Threat / need | Recommended | Why |
|---|---|---|
| Running untrusted user code from a web app | Microsandbox | Per-execution microVM with a clean CLI, no host kernel sharing |
| CI job isolation with a familiar image workflow | Microsandbox | OCI images, `msb run`, volumes, snapshot/restore |
| Your product must spawn a VM from application code | SmolVM | Real SDKs, elastic memory, machines survive restarts |
| Testing an install against different base images repeatedly | SmolVM | Branch a machine, run, discard — no rebuild |
| Serving one tiny network daemon with minimal code | smolBSD | ~10 ms boot, NetBSD base, no Linux userland at all |
| Multi-tenant execution with per-tenant state | Microsandbox | Named sandboxes plus fork gives cheap per-tenant copies |
| You need hardened kernel syscall filtering instead | gVisor / seccomp path | Different layer — see the sandboxing guides below |

![Microsandbox — programmable microVMs for untrusted workloads](/img/screenshots/microsandbox-overview.jpg "Microsandbox project banner")

## Microsandbox — Docker Ergonomics, Hypervisor Isolation

Microsandbox's whole pitch is that you should not have to learn a new mental model to get hardware isolation. Images, commands, shells and volumes all behave the way you expect, except each sandbox is a microVM with its own kernel.

Install the CLI with one line:

```bash
curl -fsSL https://install.microsandbox.dev | sh
```

Other package managers work too, and the SDKs are separate — `npm i microsandbox`, `cargo add microsandbox`, `uv add microsandbox`, or `go get github.com/superradcompany/microsandbox/sdk/go`.

Running a command is deliberately boring, which is the highest compliment you can pay a sandbox tool:

```bash
msb run python -- python3 -c "print('Hello from a microVM!')"
```

Named sandboxes are where it gets interesting. You can create one, exec into it multiple times, and **fork a running sandbox** into an independent copy:

```bash
msb create --name app python
msb exec app -- python -c "import this"
msb exec app -- curl https://example.com
msb fork app --name app2
msb exec app2 -- python -c "print('An independent copy!')"
```

That fork primitive is the reason to pick Microsandbox over a plain VM wrapper: for a web app executing untrusted code, the expensive part is booting and warming an environment. Fork a warm sandbox per request, throw it away, keep the cost flat.

**Honest weaknesses:** upstream labels it **beta software** and warns about breaking changes, missing features and rough edges — believe them, and pin versions. Host requirements are non-negotiable: KVM on Linux, Apple Silicon on macOS, Windows Hypervisor Platform on Windows. And it is Linux-guest only, because OCI images are Linux.

## SmolVM — Sandboxes as a Library

SmolVM flips the interface around: instead of a CLI you drive from a shell, it is a VM runtime you embed. Machines keep their own kernel, boot in under a second, use elastic memory (the host only commits what the guest touches), and persist across restarts.

```bash
brew install smol-machines/tap/smolvm                  # macOS
curl -sSL https://smolmachines.com/install.sh | bash   # macOS + Linux
```

The one-off form is the fastest way to sanity-check isolation:

```bash
smolvm machine run --net --image alpine -- uname -a
smolvm machine run --net -it --image alpine -- /bin/sh
```

For anything long-lived, create and reuse a named machine:

```bash
smolvm machine create --net --name dev && smolvm machine start --name dev
smolvm machine exec --name dev -- apk add git
```

Two features stand out for real deployments. First, **you can pipe a locally built image straight in without a registry**:

```bash
docker save myapp | smolvm machine run --image - -- ./app
```

Second, **object storage mounts** — `-v s3://bucket/prefix:/data` works against S3, R2 or MinIO, so sandbox state can live outside the VM without an NFS bridge.

**Honest weaknesses:** the documented workflow is still evolving, and there is more than one installation path (Homebrew, install script, language packages), which means version drift across hosts is easy. Pin the version in CI rather than using `latest` on every run.

## smolBSD — Ten Milliseconds of Nothing

smolBSD is the outlier: it is shell scripts and a build system that produce a minimal **NetBSD** image, not a Linux container runtime. There is no compatibility layer, no glibc, no container image. What you get instead is a kernel and exactly the services you asked for, with PVH boot under QEMU or Firecracker measured at around **10 ms** on mid-range x86 hardware.

The configuration format is a Dockerfile-compatible "SMOLerfile", which is a clever choice — anyone who has written a Dockerfile can read it:

```dockerfile
# Mandatory: base sets (comma separated) or a base image name
FROM base,etc

# Mandatory: service name
LABEL smolbsd.service=caddy
# Optional: minimize image to actual content
LABEL smolbsd.minimize=y
# Dockerfile has no port mapping, so it lives in a label
LABEL smolbsd.publish="8881:8880"

RUN pkgin up && pkgin -y in caddy

EXPOSE 8880
CMD caddy respond -l :8880
```

Build and run it:

```bash
./smoler.sh build smolerfiles/Dockerfile.caddy
./startnb.sh -f etc/caddy.conf
curl -I 127.0.0.1:8881
```

Host requirements are explicit and worth reading before you commit: `curl`, `git`, `bmake` (on Linux/macOS), `qemu-system-x86_64`, `uuidgen`, `nm`, `bsdtar`, `sgdisk`, `lsof`, plus optional `socat` and `picocom` for console work. On Debian and Ubuntu that collapses into one command:

```bash
sudo apt install curl git bmake qemu-system-x86_64 uuid-runtime binutils libarchive-tools gdisk socat jq lsof picocom
```

**Honest weaknesses:** the smallest community of the three, and the NetBSD constraint is a hard wall — if your workload is a Linux binary, this is not your tool. It also has no fork or snapshot semantics; you rebuild from the SMOLerfile instead.

## Pitfalls That Actually Bite

**1. Containers are not a security boundary; hypervisors are.** If the code you are running is adversarial rather than merely buggy, namespaces alone are insufficient — a shared kernel is a shared blast radius. This is the entire reason all three projects exist, and it is why you should not "just use Docker with `--cap-drop`" for hostile input.

**2. KVM must be actually available inside your own environment.** Microsandbox and SmolVM both need hardware virtualization. Running them inside a container or a nested VM frequently means `/dev/kvm` is missing, and the failure surfaces as a confusing boot error rather than a clear "no KVM" message. Check `ls -l /dev/kvm` on the host before you plan anything.

**3. Elastic memory still has a ceiling.** Memory that grows on demand makes a fork-heavy workload look cheap right up until the host OOMs. Set explicit per-sandbox memory limits and monitor host RSS, not guest-requested memory.

**4. Snapshot and fork copy secrets too.** A forked sandbox inherits everything the parent had in memory, including credentials. Microsandbox's answer is secrets that never enter the VM in the first place — use that mechanism rather than environment variables if the workload is untrusted.

**5. Startup time is not the same as time-to-useful-work.** A 100 ms boot is great, but a cold image pull is seconds to minutes. Pre-pull images on the host, keep a warm parent sandbox, and fork from it.

**6. No GPU passthrough in this class of tool.** If your workload needs a GPU, none of these three is the answer. You are back to full VMs with passthrough and the operational weight that implies.

## Throughput and Ops Reality

Approximate figures on a 16-core host with KVM, running a trivial command per sandbox:

- **Microsandbox:** ~100 ms boot per sandbox, thousands of sequential runs per hour; fork from a warm parent cuts per-execution cost to single-digit milliseconds.
- **SmolVM:** sub-second boot, elastic memory, designed for machines that stay alive rather than churn.
- **smolBSD:** ~10 ms boot under PVH — the fastest of the three, with the smallest memory footprint, because there is barely any userland to load.

The operational split matters more than the numbers. Microsandbox is a **churn** tool: start, run, discard. SmolVM is a **resident** tool: keep machines around, branch them, exec repeatedly. smolBSD is an **appliance** tool: build once, boot thousands of identical instances of one tiny service. Choosing against type is how teams end up with a 40-second rebuild cycle they did not budget for.

For the surrounding layers — comparing hypervisor-isolated runtimes, and the syscall-filtering approaches that work *inside* a container rather than beside it — see our [gVisor vs Kata vs Firecracker comparison](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/), the [Linux sandboxing frameworks guide](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-seccomp-bubblewrap-guide/), and the deeper [microVM platform analysis covering Firecracker, Cloud Hypervisor and crosvm](../2026-05-09-microvm-platforms-firecracker-cloud-hypervisor-crosvm-guide/).

## FAQ

### Is a container good enough isolation for untrusted code?

Usually not. Containers share the host kernel, so a kernel vulnerability can turn a container escape into host access, and resource limits alone do not stop that class of bug. If the code is merely untrusted in the sense of "might crash" or "might fork-bomb", hardened containers are fine. If it is adversarial, use a hypervisor boundary — that is what Microsandbox, SmolVM and smolBSD provide.

### Do I need a GPU or special hardware?

For these tools, you need virtualization support: KVM on Linux, Apple Silicon on macOS, or the Windows Hypervisor Platform. No GPU support is offered in any of the three, so workloads that need CUDA cannot run here. On a VPS, confirm `/dev/kvm` exists before choosing this approach — many budget hosts do not expose it.

### How much faster is smolBSD than a normal virtual machine?

The project measures roughly 10 milliseconds to boot a NetBSD microVM under QEMU or Firecracker using PVH boot on mid-range x86 hardware, versus seconds for a conventional VM boot. That speed comes from stripping the image to a base set plus one service, not from a different hypervisor.

### Can I use these to run Linux binaries?

With Microsandbox and SmolVM, yes — both run standard OCI images, so anything you can containerize can run. smolBSD cannot: it builds NetBSD systems, so a Linux binary will not execute without a compatibility layer that the project does not provide. Match the guest OS to your artifact before evaluating anything else.

### Which one is production-ready today?

All three are actively developed (all pushed within days of each other), but maturity differs. Microsandbox explicitly warns that it is beta with breaking changes; SmolVM is young but has stable packaging across four ecosystems; smolBSD is small, focused and conservative. None of them should be the only thing between hostile code and your data without a defence-in-depth layer around it.

### How do I keep sandbox images up to date?

Treat images like any other dependency: pin digests, rebuild on a schedule, and test the new image in CI before rolling it out. Microsandbox and SmolVM pull OCI images, so your existing registry scanning applies. smolBSD regenerates from a SMOLerfile, which means the base set version in `FROM base,etc` is the thing to pin and review.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Microsandbox vs SmolVM vs smolBSD in 2026: Which MicroVM Sandbox Should Run Your Untrusted Code?",
  "description": "Comparison of Microsandbox, SmolVM and smolBSD microVM sandboxes in 2026: real install commands, boot times, isolation trade-offs and production pitfalls.",
  "datePublished": "2026-10-27",
  "dateModified": "2026-10-27",
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
