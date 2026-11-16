---
title: "Confidential VMs in 2026: AMD SEV-SNP vs Intel TDX vs AWS Nitro Enclaves"
date: "2026-11-17"
tags: ["confidential-computing", "virtualization", "security", "kubernetes", "cloud"]
description: "A hands-on comparison of AMD SEV-SNP, Intel TDX and AWS Nitro Enclaves: launch flags, attestation flows, performance trade-offs and when each one actually makes sense."
cover: "/img/screenshots/confidential-vms-kata-architecture.jpg"
draft: false
---

Your database is encrypted at rest. Your traffic is wrapped in TLS. And the hypervisor operator can still read every byte of your guest memory with a single `gcore`. That is the gap confidential computing closes — and in 2026 it is no longer a research demo. All three major implementations ship in mainline Linux, and two of them run on hardware you can rent by the hour.

This guide compares the three stacks you can actually deploy today: **AMD SEV-SNP**, **Intel TDX**, and **AWS Nitro Enclaves**. Not marketing slides — launch commands, attestation tooling, and the operational traps that bite teams in production.

## TL;DR — Quick Verdict

**Pick AMD SEV-SNP** if you need confidential VMs on hardware you already own or rent from a mainstream cloud. It has the widest availability, the simplest KVM/QEMU path, and the most mature open-source attestation tooling.

**Pick Intel TDX** if you are on 4th-gen Xeon or newer, need a larger confidential VM footprint, or your compliance story already runs through Intel's attestation stack.

**Pick AWS Nitro Enclaves** only if you are on AWS and need a hard isolation boundary for one specific workload — key custody, PIN verification, or log signing — where you never want the parent instance's root user to see plaintext.

If you want the one-line version: **SEV-SNP is the default, TDX is the performance-and-scale play, Nitro Enclaves is the narrow-purpose isolation primitive.** None of them is a drop-in replacement for the others.

## Comparison Table: The Three Stacks Side by Side

| Dimension | AMD SEV-SNP | Intel TDX | AWS Nitro Enclaves |
|---|---|---|---|
| **Isolation unit** | Encrypted VM (per-VM key, RMP integrity) | Encrypted VM with TDX module mediation | Enclave carved from an EC2 instance |
| **Where it runs** | AMD EPYC 7003+ (Milan and later) | 4th-gen Xeon (Sapphire Rapids) and newer | Nitro-based EC2, `*.metal` and large instances |
| **Host kernel support** | Linux 5.19+ (KVM SEV-SNP) | Linux 6.13+ for TDX host, 6.8+ guest | Managed by AWS, invisible to you |
| **Guest kernel** | 5.19+ (`/dev/sev-guest`) | 6.8+ (`/dev/tdx_guest`) | Custom image built from your container |
| **Attestation** | SNP report signed by VCEK, verified against AMD KDS | TD Quote verified against Intel PCS | NSM-signed document plus PCRs |
| **Live migration** | Not supported for SNP guests | Not supported | Not applicable |
| **Networking inside** | Normal virtio (protected against host DMA) | Normal virtio with shared-bit page conversion | **Only vsock** — no IP stack at all |
| **Persistence** | Normal disks (encrypted with guest-held keys) | Normal disks | **None** — enclave memory dies with the enclave |
| **Tooling maturity** | Good — `sevctl`, `snpguest`, libvirt XML | Good and improving — `tdx-tools`, configfs-tsm | Narrow but stable — `nitro-cli` |
| **License** | Kernel + QEMU (GPL/LGPL upstream) | Kernel + QEMU (upstream) | `nitro-cli` Apache-2.0 |
| **Best fit** | Self-hosted KVM, OpenStack, generic clouds | Xeon fleets, Kubernetes confidential containers | AWS key custody, secrets brokering |

## Decision Matrix: Match the Tool to the Job

| Your situation | Recommended | Why |
|---|---|---|
| Run confidential VMs on your own KVM hosts | SEV-SNP | Works with stock QEMU and libvirt; no vendor module required |
| Multi-tenant Kubernetes with confidential pods | Kata Containers on SEV-SNP or TDX | Runtime-level boundary with a config toggle per node |
| Regulatory requirement that the cloud operator cannot read memory | SEV-SNP or TDX | Both produce hardware-signed attestation reports you can verify yourself |
| Single secret-handling microservice on AWS | Nitro Enclaves | Strongest boundary per unit of effort; parent instance cannot enter it |
| Large-memory confidential database (hundreds of GB) | TDX | Currently the more comfortable option for very large confidential VMs |
| You want to avoid changing application code | Nitro Enclaves (for one service) or SEV-SNP | No code change, but Nitro forces a vsock-only design |
| You need live migration of confidential guests | None of the above | Every option here is deliberately non-migratable |

## AMD SEV-SNP — The Practical Default

SEV-SNP (Secure Nested Paging) is the third generation of AMD's memory encryption line. SEV encrypted memory with one key per VM; SEV-ES added register-state protection; SNP added the **Reverse Map Table (RMP)**, which gives the hypervisor a way to prove it has not remapped a guest page behind the guest's back. That integrity property, not the encryption, is what makes SNP defensible in an audit.

Booting an SNP guest on a stock KVM host is unglamorous — just QEMU objects:

```bash
qemu-system-x86_64 \
  -enable-kvm -cpu EPYC-v4 -smp 4 -m 8G \
  -object memory-backend-memfd,id=ram1,size=8G,share=true,prealloc=true \
  -machine q35,confidential-guest-support=sev0,memory-backend=ram1 \
  -object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1,policy=0x30000 \
  -drive file=guest.qcow2,if=virtio,format=qcow2 \
  -nographic
```

Three flags matter more than the rest: `share=true` on the memory backend (SNP guests cannot use private anonymous memory), `prealloc=true` (memory must be pinned), and `policy=0x30000` (require SNP, disable legacy SEV downgrade). If `prealloc` is missing you will get a boot that hangs at "Allocating guest memory" with no useful error.

Inside the guest, `/dev/sev-guest` exposes the report interface. The `snpguest` binary from the `virtee/sev` project handles the whole flow:

```bash
# Generate a report bound to 64 bytes of caller-supplied data
snpguest report report.bin request-data.txt --random

# Fetch the VCEK certificate for this exact chip + firmware level
snpguest fetch vcek pem certs/

# Verify the report chain against AMD's root of trust
snpguest verify certs certs/
snpguest verify attestation certs/ report.bin
```

The **request-data** is your channel binding: put a TLS public key hash or a nonce in it, and the report proves that key was generated inside a genuine SNP guest running the measurement you expect. Skip that step and attestation becomes theatre.

Operational reality: SNP guests cannot be live-migrated, cannot use hugepages through the normal path on all kernel versions, and pay a measurable cost on memory-bound workloads because every page-table walk touches encrypted memory. Budget single-digit CPU overhead for compute-heavy services and test memory-bandwidth-bound services (in-memory caches, columnar analytics) before you commit.

## Intel TDX — Bigger VMs, Xeon-Only

TDX (Trust Domain Extensions) inverts the trust model slightly. Instead of the hypervisor enforcing page ownership against a reverse map, a small **TDX module** running in a privileged CPU mode mediates between the host and the trust domain (TD). The host still schedules and manages the VM, but it cannot read TD memory, and the shared/private page distinction is explicit.

Host prerequisites are the sticking point. You need a 4th-gen Xeon or newer, TDX enabled in firmware, and a host kernel new enough to expose the TDX module interface. The launch looks like this:

```bash
qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 8 -m 16G \
  -object memory-backend-memfd,id=ram1,size=16G,share=true,prealloc=true \
  -machine q35,confidential-guest-support=tdx0,kernel_irqchip=split,memory-backend=ram1 \
  -object tdx-guest,id=tdx0,quote-generation-service=vsock:2:4050 \
  -drive file=td.qcow2,if=virtio,format=qcow2 \
  -nographic
```

The `kernel_irqchip=split` flag is mandatory — the legacy in-kernel irqchip cannot mediate interrupts for a trust domain. The `quote-generation-service` points at your quoting enclave, normally the `sgx-dcap`-style service shipped with `tdx-tools`.

Guest-side attestation goes through the kernel's generic **configfs-tsm** interface, which is the same abstraction used for SEV-SNP guest reports and ARM CCA. That is a real advantage: write one attestation client and it works across TDX and SNP.

```bash
# Ask the kernel for a TD quote with 64 bytes of caller data
mkdir /sys/kernel/config/tsm/report/req0
printf '77616e7465642d6e6f6e6365' > /sys/kernel/config/tsm/report/req0/inblob
cat /sys/kernel/config/tsm/report/req0/outblob > quote.bin
cat /sys/kernel/config/tsm/report/req0/provider   # prints "tdx_guest"
rmdir /sys/kernel/config/tsm/report/req0
```

Practical notes: TDX guests also cannot live-migrate. Host-side memory preallocation is not optional. And on early firmware revisions, certain PCI passthrough configurations simply do not work — check your BIOS level before you promise a confidential GPU workload.

## AWS Nitro Enclaves — Isolation Without a Hypervisor Story

Nitro Enclaves is not a VM technology you operate; it is a feature of the Nitro platform. You carve an enclave out of an EC2 instance, hand it a container image, and it gets dedicated vCPUs and memory that the parent instance **cannot** read, even as root, even with kernel modules.

The mental model shift is severe. An enclave has:

- **No networking.** Only a vsock channel to the parent, on a CID you choose.
- **No persistent storage.** Every byte lives in enclave memory; restart means re-provision.
- **No shell.** Debugging happens by streaming logs out through vsock.

Building and running is a two-command flow once `nitro-cli` is installed on the parent:

```bash
# Build an EIF (enclave image file) from a Docker image
nitro-cli build-enclave \
  --docker-uri registry.example.com/kms-broker:1.4 \
  --output-file kms-broker.eif

# Allocate 2 vCPUs and 1024 MiB, expose vsock CID 16
nitro-cli run-enclave \
  --eif-path kms-broker.eif \
  --cpu-count 2 \
  --memory 1024 \
  --enclave-cid 16

nitro-cli describe-enclaves
```

Attestation comes from the **Nitro Security Module**: the enclave talks to `/dev/nsm`, gets a signed document that includes PCR values over the EIF (image) and the enclave's public key, and the parent cannot forge it. Your key-release service verifies that document against the AWS Nitro root certificate before handing over any secret.

Where teams go wrong: they try to move an entire application into an enclave. Don't. The winning pattern is a **small** enclave that holds one secret and does one operation — decrypt a data key, sign a log batch, verify a PIN — while the main application stays outside and talks to it over vsock. That keeps the image small, the integration surface auditable, and the failure mode recoverable.

## Running Confidential Pods with Kata Containers

If you already run Kubernetes, wiring every launch flag by hand does not scale. Kata Containers ships confidential-guest configurations that turn a pod into a hardware-isolated VM with one runtime class switch.

```toml
# /opt/kata/share/defaults/kata-containers/configuration-qemu-snp.toml (excerpt)
[hypervisor.qemu]
path = "/opt/kata/bin/qemu-system-x86_64"
kernel = "/opt/kata/share/kata-containers/vmlinuz-confidential.container"
image = "/opt/kata/share/kata-containers/kata-containers-confidential.img"
machine_type = "q35"
confidential_guest = true
enable_annotations = ["kernel_params"]

[hypervisor.qemu.kernel_params]
kernel_params = "agent.log=debug console=hvc0"
```

Register it as a runtime class and reference it from the pod spec:

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata-qemu-snp
handler: kata-qemu-snp
---
apiVersion: v1
kind: Pod
metadata:
  name: payroll-worker
spec:
  runtimeClassName: kata-qemu-snp
  containers:
    - name: worker
      image: registry.example.com/payroll-worker:2.1
      resources:
        requests: { memory: "2Gi", cpu: "1" }
```

The pod now runs inside an SNP-encrypted VM, and the kubelet — which is effectively a hypervisor operator — cannot read its memory. Attestation is handled out-of-band by a key broker service that verifies the guest report before releasing the disk encryption key. This is the pattern most regulated deployments converge on.

## Pitfalls and Migration Notes

**No live migration, anywhere.** Every stack here breaks it on purpose. If your platform depends on DRS-style evacuation, confidential VMs will strand. Plan for drain-and-recreate.

**Memory is pinned and preallocated.** A confidential guest costs its full memory footprint up front. Overcommit ratios that worked fine for normal VMs will OOM the host.

**Attestation verification is your job.** A report you never verify is a PDF with a signature you didn't check. Pin the expected measurement, verify the certificate chain to the vendor root, and reject anything else — including silent firmware upgrades that change the measurement.

**Swap and core dumps leak.** `/proc/kcore`, hibernation, and swap to unencrypted block devices all undermine the guarantee. Disable them in confidential images.

**Debugging gets worse before it gets better.** There is no host-side introspection. Build a log channel through vsock (Nitro) or the guest agent (SEV-SNP/TDX) before you need it.

**Not every accelerator works.** PCI passthrough under SNP and TDX has firmware and IOMMU dependencies. Validate GPU passthrough with the exact BIOS and kernel you plan to ship.

**Encrypted guest does not mean encrypted disk.** Pair the VM boundary with LUKS or a key broker, otherwise the disk image on the host is still readable.

For adjacent isolation models, see our [microVM platform comparison](../2026-05-09-microvm-platforms-firecracker-cloud-hypervisor-crosvm-guide/) and the [Linux sandboxing guide covering Landlock, seccomp and bubblewrap](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-seccomp-bubblewrap-guide/). If you are weighing a single-application kernel instead of a confidential VM, the [unikernel comparison](../2026-06-04-self-hosted-unikernel-platforms-unikraft-nanos-includeos-mirageos-guide/) is the right starting point.

## FAQ

### Is AMD SEV-SNP the same thing as SEV or SEV-ES?

No. SEV encrypts guest memory with a per-VM key. SEV-ES additionally encrypts register state on VM exits. SEV-SNP adds the Reverse Map Table, which prevents the hypervisor from aliasing or remapping guest pages, and adds attestation reports bound to the guest's launch measurement. Only SNP gives you integrity, not just confidentiality.

### Can I run confidential VMs on a normal cloud instance?

Only if the provider exposes the feature. You need bare-metal or explicitly labeled confidential instances, plus a CPU generation that supports the technology — EPYC 7003 or later for SNP, 4th-gen Xeon or later for TDX. Standard shared-tenancy instances typically do not expose `/dev/sev-guest` or `/dev/tdx_guest`.

### Do confidential VMs hurt performance?

Compute-bound workloads usually see single-digit percentage overhead. Memory-bandwidth-bound workloads see more, because page-table walks and DMA bounce buffers touch encrypted memory. Measure your own workload: an in-memory cache or columnar analytics engine will feel it far more than an HTTP API.

### How do I know the VM is really confidential and not just labeled that way?

Verify the attestation report yourself. Request a report with a nonce or public-key hash you generated, verify the signature chain to the vendor root (AMD KDS, Intel PCS, or the AWS Nitro root), and compare the reported measurement against the one you built. If your key broker does not do this before releasing secrets, the guarantee is unenforced.

### Are Nitro Enclaves a replacement for confidential VMs?

No. Enclaves have no networking, no persistent storage, and no shell, so they fit narrow secret-handling services rather than general workloads. Use enclaves to protect one small, high-value operation on AWS, and use SEV-SNP or TDX when you need whole-VM confidentiality you operate yourself.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Confidential VMs in 2026: AMD SEV-SNP vs Intel TDX vs AWS Nitro Enclaves",
  "description": "Hands-on comparison of AMD SEV-SNP, Intel TDX and AWS Nitro Enclaves with launch flags, attestation commands and operational trade-offs.",
  "datePublished": "2026-11-17",
  "dateModified": "2026-11-17",
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
