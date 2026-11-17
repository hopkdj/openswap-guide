---
title: "PCIe DOE vs SPDM vs IDE in 2026: Attesting and Encrypting the Motherboard Bus"
date: "2026-11-18"
tags: ["security", "linux-kernel", "pcie", "confidential-computing"]
draft: false
---

Every disk you encrypt, every TLS session you terminate, every LUKS volume you unlock has the same blind spot: the data crosses the PCIe link in plaintext. An interposer on the slot, a malicious add-in card, or a compromised BMC tapping the bus sees your "encrypted" NVMe writes exactly as the CPU issued them. That is not a theoretical weakness — it is the reason PCIe 7.0 dedicates a section to link encryption, and the reason the Linux kernel grew a TSM subsystem that pulls in two new PCI config symbols.

The confusing part is vocabulary. DOE, SPDM, IDE, and TDISP are discussed as if they were competing options. They are not. They are four layers of one stack, and knowing which layer does what saves you from buying hardware that cannot do the thing you assumed.

## TL;DR: It Is a Stack, Not a Menu

- **DOE** (Data Object Exchange) is the mailbox — a PCIe capability that lets the host exchange arbitrary data objects with a device. It is transport, nothing more.
- **SPDM** (Security Protocol and Data Model) is what you put in that mailbox: a DMTF protocol for discovering what a device claims to be, reading its measurements, and proving it holds a private key.
- **IDE** (Integrity and Data Encryption) is the actual encryption of the link, defined in PCIe 7.0 section 6.33. It protects data in flight between root complex and endpoint.
- **TDISP** is how a confidential VM gets exclusive, measured control of a device — the piece that makes passthrough safe under TDX or SEV-SNP.

If you want to inspect what a device claims, you need **DOE + SPDM**. If you want the wire encrypted, you need **IDE** with platform key management. If you want a GPU or NIC inside a confidential VM, you need **TDISP** on top of both.

## The Four Layers Side by Side

| Layer | What it is | Spec owner | Linux support (2026) | Userspace tooling | Protects against |
|---|---|---|---|---|---|
| DOE | PCIe config-space mailbox for data objects | PCI-SIG | `CONFIG_PCI_DOE` — "Enable PCI Data Object Exchange (DOE) support" | `spdm_utils --doe-pci-cfg`, `lspci -vv` | nothing by itself; it is plumbing |
| SPDM | Challenge/response attestation, measurement collection, certificate chains | DMTF (DSP0274) | consumed through TSM and tooling | libspdm (195★), spdm-utils (22★, Rust), spdm-rs (58★) | impostor devices, tampered firmware, unverified endpoints |
| IDE | AES-GCM encryption of TLPs on the link, with stream IDs | PCI-SIG (PCIe 7.0 §6.33) | `CONFIG_PCI_IDE`, auto-selected by `CONFIG_PCI_TSM` | kernel sysfs + platform firmware/key broker | physical bus taps, malicious add-in cards, interposers |
| TDISP | Device interface security for TEE VMs; bind/unbind, locked memory | PCI-SIG + TEE vendors | `CONFIG_PCI_TSM` — "PCI TSM: Device security protocol support" | kernel TSM, VMM (QEMU) | a compromised host VMM reading guest device memory |

Two practical observations from that table. First, the kernel symbols nest: `PCI_TSM` **selects** `PCI_IDE` and `PCI_DOE`, so enabling device security support pulls in the transport and the encryption layer whether or not you use them directly. Second, only SPDM has a mature, portable userspace implementation you can run today on a laptop — which is why it is the layer to learn first.

## Decision Matrix

| Your goal | What you need | Why |
|---|---|---|
| Check whether a NIC or SSD is genuine | DOE + SPDM tooling | `get-digests`, `get-certificate`, `challenge` answer that question |
| Encrypt traffic on the PCIe link | IDE (plus platform key management) | SPDM alone authenticates, it does not encrypt |
| Give a confidential VM a passthrough GPU | TDISP | Plain VFIO passthrough gives the host VMM full access to device memory |
| Collect firmware measurements for a boot policy | SPDM measurement collection | `get-measurement` over DOE, or over MCTP/NVMe transports |
| Test all of this without special hardware | spdm-utils over TCP, QEMU SPDM emulation | Loopback requester/responder on one machine |
| Nothing above, just want full-disk encryption | LUKS + TPM, not this stack | IDE is link encryption; it does not protect data at rest |

## DOE: The Mailbox Everything Rides On

DOE is deliberately dumb. A DOE instance is a mailbox in PCIe configuration space with a write-data-object doorbell and a read-data-object doorbell. The kernel's job is to serialize access, handle timeouts, and expose the mailbox to in-kernel consumers — that is what `CONFIG_PCI_DOE` provides, described in Kconfig as enabling communication with PCIe DOE mailboxes.

You can see whether a device even has one before installing anything:

```bash
# look for a DOE Extended Capability in the endpoint's config space
lspci -vv -s 01:00.0 | grep -A4 -i "data object exchange"
```

If there is no DOE capability, no amount of software will produce attestation for that device. This is the first hard gate in any deployment plan, and it eliminates a surprising amount of consumer hardware.

DOE's only real design constraint that bites operators is that it is a **shared, single-threaded mailbox**. Long attestation exchanges block other data objects, and multiple consumers (firmware, kernel TSM, userspace tool) contend for it. If your attestation tool hangs, the answer is usually a stuck mailbox, not a broken device.

## SPDM: The Protocol That Actually Answers Questions

SPDM is where the useful semantics live. It defines version and capability negotiation, algorithm negotiation, certificate chains, measurement collection, and challenge-response with a nonce so a device cannot replay yesterday's good answer. SPDM messages travel inside DOE data objects on PCIe, inside MCTP on management buses, or over the NVMe storage transport — the protocol is transport-independent, which is why one tool can talk to a NIC, a BMC, and an NVMe drive.

The reference implementation is DMTF's **libspdm** (195 stars, pushed November 2026). It is deliberately embedded-friendly: the core libraries need only C99 freestanding headers, do no dynamic allocation, and keep all static memory read-only. That design is why the same code runs in firmware and in a Linux CLI.

Build it the documented way on Linux:

```bash
cd libspdm
mkdir build && cd build
cmake -DARCH=x64 -DTOOLCHAIN=GCC -DTARGET=Release -DCRYPTO=openssl ..
make copy_sample_key
make
```

The friendlier front end is **spdm-utils** from Western Digital (22 stars, Rust, Apache-2.0/MIT), which uses libspdm as a backend and speaks DOE, MCTP, NVMe, SCSI, and plain TCP:

```bash
git clone https://github.com/westerndigitalcorporation/spdm-utils.git
cd spdm-utils

# build with PCIe DOE transport support
cargo build --features pci --bin spdm_utils

# talk to a real endpoint through its DOE mailbox
sudo ./target/debug/spdm_utils --pcie-vid 0x144d --pcie-devid 0xa80a \
     --doe-pci-cfg request get-digests

# or negotiate and pull the full certificate chain
sudo ./target/debug/spdm_utils --pcie-vid 0x144d --pcie-devid 0xa80a \
     --doe-pci-cfg request get-version,get-capabilities,negotiate-algorithms,get-certificate
```

The verb set is the protocol in miniature: `get-version` proves the device speaks SPDM at all, `get-digests` returns hashes of each certificate slot so you can compare against a known-good chain without transferring megabytes, `get-measurement` returns firmware measurements, and `challenge` proves the device holds the private key for the certificate it presented. `set-certificate` and `get-csr` exist too — you can provision device certificates from the same CLI.

You do not need special hardware to try any of it. spdm-utils can be both requester and responder over TCP on localhost:

```bash
# terminal 1 — responder
./target/debug/spdm_utils --tcp-server --server-persist response

# terminal 2 — requester
./target/debug/spdm_utils --tcp-client request get-version
```

For a full emulated PCIe environment, DMTF ships **spdm-emu** (68 stars) with `spdm_requester_emu` and `spdm_responder_emu`, and there is a public QEMU SPDM emulation guide (12 stars) that wires a virtual DOE into a guest. A Rust implementation, **spdm-rs** (58 stars, pushed November 2026), exists if you want the protocol without a C dependency, and **SPDM-Responder-Validator** (23 stars) is the conformance harness for people building devices rather than consuming them.

**The gap to plan for:** SPDM tells you the truth about a device. It does not enforce anything by itself. Enforcement requires a policy engine — a boot-time measurement policy, an attestation service, or the kernel's TSM — that decides what to do when `challenge` fails.

## IDE: Encrypting the Link Itself

IDE is the part most people have never touched, because until recently it required platform firmware cooperation that almost nothing shipped. The kernel support is new enough that its source file still carries an Intel copyright of 2024-2025 and cites PCIe r7.0 section 6.33 by number.

The model: the root complex and endpoint agree on keys, and TLPs belonging to a stream are AES-GCM protected with an integrity tag. There are two flavors — **Link IDE**, which encrypts everything on a physical link, and **Selective IDE**, which encrypts only streams associated with specific address ranges, so a switch can carry both protected and unprotected traffic. The kernel code manages stream IDs, reserves them per host bridge, and claims streams that firmware already activated.

You can inspect what the platform exposed:

```bash
# per-endpoint view of IDE stream capacity (present when CONFIG_PCI_IDE is enabled)
cat /sys/bus/pci/devices/0000:01:00.0/available_secure_streams

# kernel log lines from the IDE core look like this
dmesg | grep -i "PCI/IDE"
```

That `available_secure_streams` attribute is the honest signal: if it is absent, your kernel was built without IDE support. If it is present but reads zero, the endpoint does not offer secure streams. Either way you learn the truth in one command instead of after a procurement cycle.

**What IDE does not do:** it does not encrypt data at rest, it does not authenticate the device (that is SPDM's job), and it does not protect against a compromised root complex or CPU. It closes exactly one hole — the wire — and does it well.

**Key management is the hard part.** IDE keys must be established before the link carries protected traffic, which means firmware, a key broker, or a TSM-managed flow. There is no "just enable a sysfs flag" path, and any guide that implies otherwise is describing a lab. Plan for the platform integration first; the kernel side is comparatively simple.

## TDISP: Making Passthrough Safe for Confidential VMs

Assigning a physical GPU or NIC to a VM with VFIO is easy and, in a confidential-computing model, unacceptable: the host VMM still maps the device's BARs and can read or write guest device memory. TDISP fixes that by having the device enter a locked state where its memory is encrypted with guest-owned keys and its configuration is mediated by a TEE Security Manager.

The kernel's `CONFIG_PCI_TSM` — "PCI TSM: Device security protocol support" — is the anchor point. It selects both `PCI_IDE` and `PCI_DOE`, because TDISP needs DOE for the SPDM-based device authentication and IDE for the protected link between device and guest. That nesting is the clearest evidence that these are layers, not alternatives: you cannot have TDISP without the other two.

What this means practically in 2026:

- The hardware list is short and enterprise-skewed. TDISP-capable devices exist, but consumer GPUs are not on the list.
- Firmware support is the gating factor, not the kernel. Check the platform vendor's confidential-computing documentation before designing anything.
- The VMM must be TDISP-aware. A stock QEMU command line that works for VFIO passthrough will not negotiate a TDISP binding.

For self-hosters, TDISP is a "know it exists, verify before you buy" technology. For anyone operating multi-tenant infrastructure with regulatory pressure, it is increasingly the difference between offering confidential VMs and pretending to.

## Pitfalls Worth Knowing Before You Start

**Attestation without a policy is theater.** Running `spdm_utils ... challenge` and printing "PASS" teaches you nothing unless a verifier compares measurements against a known-good reference. Decide the reference values before you deploy.

**DOE capability is not universal, even on server gear.** Verify with `lspci -vv` on the exact SKU you plan to use. Firmware updates have been known to add or remove the capability between revisions of the same product.

**Certificate slots are not interchangeable.** SPDM devices expose several slots with different trust properties — the "alias" certificate used during provisioning is not the immutable device identity certificate. Provisioning scripts that write every slot with the same file will brick the trust chain from the verifier's point of view.

**IDE and TDISP both fail closed, and the failure mode is a device that disappears.** If key negotiation fails after the link is already up, you get timeouts, not a helpful error. Always have out-of-band access when experimenting.

**Do not confuse link encryption with data-at-rest encryption.** IDE protects TLPs in flight. A stolen drive still yields plaintext. If you want the drive protected, that is LUKS with TPM or a network-bound disk unlock scheme — our [TPM 2.0 tooling guide](../2026-05-12-self-hosted-tpm-management-tpm2-tools-swtpm-tpm2-tss-guide/) and the [Clevis/Tang LUKS automation guide](../2026-05-22-self-hosted-disk-encryption-automation-clevis-tang-luks2-tpm2-systemd-guide/) cover that layer properly.

**Passthrough without TDISP is not confidential.** If you are running confidential VMs and handing them devices with plain VFIO, the host can still read guest device memory. Our [IOMMU and VFIO passthrough guide](../2026-05-23-self-hosted-linux-iommu-vfio-gpu-passthrough-looking-glass-vendor-reset/) covers the mechanics of passthrough — read it as the baseline, then add TDISP if the threat model includes the host.

## FAQ

### Is SPDM the same thing as DOE?

No. DOE is a PCIe mailbox capability that moves data objects between host and device; SPDM is a protocol whose messages happen to be carried in those data objects. SPDM can also run over MCTP or the NVMe storage transport, which is why the same tooling works on NICs, BMCs, and SSDs.

### Does PCIe IDE encrypt my disk?

No. IDE encrypts TLPs on the PCIe link between the root complex and the endpoint. Data at rest on the drive is unaffected, so a removed drive still contains plaintext unless you also use full-disk encryption such as LUKS.

### Can I use SPDM on a normal desktop motherboard?

Rarely. The device must expose a DOE capability, which is mostly found on server and enterprise endpoints. Check with `lspci -vv` before assuming support; if there is no DOE capability, no software on the host can add it.

### What kernel options do I need?

`CONFIG_PCI_DOE` for the mailbox, `CONFIG_PCI_IDE` for link encryption, and `CONFIG_PCI_TSM` for device security/TDISP support. Note that `PCI_TSM` selects `PCI_IDE` and `PCI_DOE`, so enabling the top layer pulls in the lower two.

### How do I test any of this without special hardware?

Build spdm-utils with `cargo build --features pci --bin spdm_utils` and run it as both responder and requester over TCP on localhost, or use DMTF's `spdm-emu` with the QEMU SPDM emulation guide to get a virtual DOE inside a guest.

### Is TDISP required for GPU passthrough?

Only if the threat model includes the host. Plain VFIO passthrough is fine for a single-tenant box you control. For confidential VMs where the host VMM must not be able to read guest device memory, TDISP is the mechanism that locks the device to the guest.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PCIe DOE vs SPDM vs IDE in 2026: Attesting and Encrypting the Motherboard Bus",
  "description": "How PCIe DOE, SPDM, IDE and TDISP fit together as a device security stack, with real libspdm and spdm-utils commands plus Linux kernel config options",
  "datePublished": "2026-11-18",
  "dateModified": "2026-11-18",
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
