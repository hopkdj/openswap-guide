---
title: "In-Place Linux Upgrades in 2026: Leapp vs ELevate vs do-release-upgrade (And When Reinstalling Wins)"
date: "2026-11-20"
tags: ["linux", "operations", "upgrade", "rhel", "ubuntu", "debian", "lifecycle"]
draft: false
---

Your audit window closes in six weeks, and the fleet has 180 hosts running a distribution release that stopped receiving security fixes eight months ago. The instinct is to rebuild them all from images. The realistic option, at that scale, is an in-place upgrade — and the difference between a two-hour-per-host success story and a weekend of console recovery is almost entirely **which upgrade path you pick and how well you rehearsed it**.

This guide compares the three upgrade engines that actually exist in 2026 for production Linux, with the command sequences, the lifecycle dates that force the decision, and an honest list of when reinstalling is the cheaper answer.

## Quick Verdict

- **RHEL, Rocky Linux, AlmaLinux 8 → 9:** Leapp for RHEL-proper, **ELevate** for the rebuilds and for the 7 → 8 → 9 jump. It has a pre-upgrade analyser that produces an inhibitor report — read it before you touch anything.
- **Ubuntu LTS → LTS:** `do-release-upgrade` works and is supported; it fails most often on third-party APT repositories and NVIDIA/DKMS kernel modules, not on the upgrade itself.
- **Debian stable → stable:** the least glamorous and most reliable path in this entire article. Edit `sources.list`, `apt update`, `apt full-upgrade`. Two commands, decades of muscle memory behind them.
- **Alpine and any container base image:** never upgrade in place. Rebuild the image. `apk` will happily upgrade, but a container that has drifted across two Alpine branches is a container you cannot reason about.
- **Reinstall wins when** the host has more than one major version of drift, a custom kernel, hand-installed packages outside the package manager, or a hardware compatibility stack you cannot re-validate in staging.

## The Dates That Force the Decision

Lifecycle is the reason this article exists. Publisher-stated dates as of November 2026 — verify against the vendor page before you build a plan, because extensions get announced:

| Distribution | Current stable | Security/maintenance end | Effective upgrade cadence |
|---|---|---|---|
| RHEL 10 | 10.x | ~2035 (10-year lifecycle) | major every 3 years |
| RHEL 9 | 9.x | 2032-05-31 | upgrade to 10 during 2027-2029 |
| Rocky Linux 9 / AlmaLinux 9 | 9.x | 2032-05-31 | same window as RHEL 9 |
| Ubuntu 24.04 LTS | 24.04.x | 2029-06 standard; 2034 with Pro/ESM | every 2 years (next LTS 2026/2028) |
| Ubuntu 22.04 LTS | 22.04.x | 2027-06 standard; 2032 with Pro/ESM | upgrade now if you are on it |
| Debian 13 (trixie) | 13.x | ~2030 (LTS) | every ~2 years |
| Debian 12 (bookworm) | 12.x | ~2028 (LTS) | plan the 12 → 13 hop |
| Alpine | 3.22 branch | ~2 years per branch | rebuild images, do not migrate |

Two practical consequences. First, **the enterprise Linux rebuilds (Rocky, Alma) track RHEL's dates within days**, so a plan that works for one works for all three. Second, **Ubuntu's ESM window changes the economics entirely**: paying for Pro on a 22.04 fleet can be cheaper than a migration project, and that is a legitimate decision rather than technical debt.

## The Three Engines Compared

| | Leapp | ELevate | do-release-upgrade |
|---|---|---|---|
| Vendor | Red Hat (upstream `oamg/leapp`) | AlmaLinux (leapp-data) | Canonical |
| Supported hops | RHEL 8 → 9, 9 → 10 | EL7 → EL8 → EL9 (cross-distro) | Ubuntu LTS → next LTS |
| Pre-upgrade analysis | Yes (`leapp preupgrade`) | Yes, with cross-distro data packages | Partial (`-d` dry run only checks availability) |
| Rollback | Snapshot / reinstall | Snapshot / reinstall | Snapshot (no built-in rollback) |
| Typical downtime | 45-90 min | 60-120 min | 30-60 min |
| Biggest failure source | Third-party kernel modules, unsupported packages | Same, plus cross-distro package delta | PPA/third-party repos, DKMS modules |
| Rehearsal requirement | High — inhibitors must be cleared | High | Medium |

Repo activity is the honest signal for how maintained each engine is: `oamg/leapp` at **106 stars, last commit 2026-11-13**, `oamg/leapp-repository` at **65 stars, 2026-11-12**, and the ELevate data package `AlmaLinux/leapp-data` at **17 stars, 2026-11-17**. Low star counts here are not a warning — these are distribution plumbing, not developer tools, and they are exercised by every enterprise migration in the field.

## Leapp: The Analyser Is the Product

Leapp's value is not the upgrade transaction; it is the **pre-upgrade report**. It inspects installed packages, kernel modules, storage layout, and authentication configuration, then emits either "ready" or a list of inhibitors you must resolve. Skipping that report is how people end up with an unbootable host at 2 AM.

```bash
# RHEL 8 -> 9
dnf install -y leapp-upgrade
leapp preupgrade --debug          # produces /var/log/leapp/leapp-report.txt
less /var/log/leapp/leapp-report.txt
```

The report has three severities you must treat differently: **inhibitor** (blocks the upgrade), **high** (fix before production), **info** (read and accept). Common inhibitors and their fixes:

```bash
# Example: unsupported kernel module loaded
grep -i "inhibitor" /var/log/leapp/leapp-report.txt

# Example answerfile for known, accepted removals
cat > /var/log/leapp/answerfile <<'EOF'
[remove_pam_pkcs11_module_check]
confirm = True
EOF
```

Once the report is clean:

```bash
leapp upgrade --debug     # stages the new userspace, then reboots into it
```

The host reboots into an upgrade environment, applies the transaction, and reboots again into the target release. **Budget for the second boot to fail** on hosts with out-of-tree storage or network drivers — which is exactly why the next section exists.

## ELevate: The Cross-Distro Path

ELevate is the version of this workflow that also works **across distributions** — CentOS 7 to AlmaLinux 9, Rocky 8 to AlmaLinux 9, and similar combinations. It uses Leapp as the engine and AlmaLinux-maintained data packages to describe the target system.

```bash
# On an EL7 host, migrating toward EL8
dnf install -y \
  http://repo.almalinux.org/elevate/elevate-release-latest-el$(rpm --eval %rhel).noarch.rpm
dnf install -y leapp-upgrade leapp-data-almalinux

leapp preupgrade
leapp upgrade
```

For the full 7 → 9 journey, run the cycle twice: 7 → 8, validate in production for a week, then 8 → 9. **Do not attempt to chain both hops in one maintenance window.** Each hop changes init system details, cryptography defaults, and Python runtime versions; you want a known-good intermediate state you can stop at.

ELevate's honest limitation: cross-distro means the package set on the other side is not identical to what you had. Packages that only existed in EPEL 7, or vendor RPMs built against a specific OpenSSL version, need to be reinstalled from the target's repositories — and some simply do not exist there anymore.

## do-release-upgrade: Ubuntu's Supported Path

Ubuntu's tool is the most forgiving of the three, mostly because Ubuntu's packaging delta between LTS releases is smaller than the EL 7 → 8 → 9 jump.

```bash
apt update && apt full-upgrade -y
apt install -y update-manager-core

# Rehearse first: -d forces the development/next release check on some paths
do-release-upgrade

# Run it detached so an SSH drop does not kill the transaction
nohup do-release-upgrade -f DistUpgradeViewNonInteractive > /var/log/dist-upgrade.log 2>&1 &
```

Two rules that prevent most Ubuntu upgrade failures:

- **Disable every third-party APT source before starting.** PPAs and vendor repositories are the single largest source of `403`/`404` failures mid-transaction. Re-enable them one at a time afterwards.
- **Remove or rebuild DKMS modules first.** NVIDIA, ZFS-on-root, and VirtualBox modules must be rebuilt for the new kernel; if the rebuild fails, the host may not boot into a graphical or storage-capable state.

## Debian: The Boring One That Works

Debian's in-place upgrade is manual and has been stable for twenty years. There is no analyser and no vendor tooling — which is exactly why it fails less often than it is credited for: nothing is guessing on your behalf.

```bash
# Point at the new release
sed -i 's/bookworm/trixie/g' /etc/apt/sources.list /etc/apt/sources.list.d/*.list

apt update
apt upgrade --without-new-pkgs
apt full-upgrade
apt autoremove --purge
```

The middle step (`upgrade --without-new-pkgs`) is the one people skip. It pulls the minimum-viable package set forward so that the subsequent `full-upgrade` only has to resolve genuinely new dependencies. Skipping it dramatically increases the chance of a dependency deadlock halfway through.

## The Rehearsal That Decides the Outcome

No upgrade engine — Leapp, ELevate, or Canonical's — gives you a rollback button. The rollback is the snapshot you take before you start.

If the host uses LVM, that means a thick snapshot with an explicit budget, or a thin snapshot inside a pool with headroom:

```bash
# Root on LVM: reserve real COW space, then watch it
lvcreate -s -n snap_root_preupgrade -L 50G vg_system/lv_root
lvs -o name,snap_percent vg_system
```

```bash
# Root on ZFS: a snapshot costs nothing until blocks change
zfs snapshot rpool/ROOT/ubuntu@preupgrade-$(date +%F)
zfs list -o name,used,usedbysnapshots rpool/ROOT/ubuntu
```

Test the rollback path before the real change, on one host, in staging. The sequence I use:

1. Snapshot the root volume and the database volumes separately.
2. Run `leapp preupgrade` / `do-release-upgrade` rehearsal on a clone of the host.
3. Boot the clone, verify the services that matter (authentication, storage mounts, the monitoring agent).
4. Only then touch the production host, with the snapshot verified and a console session open.

Note the ordering trap: **a thick LVM snapshot invalidates silently if the COW region fills**, and an upgrade writes a lot of data. If you snapshot at 20 GB on a busy root volume, you may discover the snapshot is gone exactly when you need it. Size it at 30% of the write volume for the window, and check `snap_percent` before starting.

## Pitfalls From Real Migrations

- **Re-enabling EPEL or third-party repos mid-upgrade** pulls packages built for the wrong ABI. Disable them, upgrade, reinstall from the target's repositories.
- **Custom kernels bypass the whole safety model.** If `/boot` holds a kernel the distribution does not ship, the upgrade has no idea how to keep it bootable.
- **`/var` or `/home` on a separate filesystem** is fine, but a full `/boot` is not: the transaction needs room for at least two kernels plus initramfs. Check `df -h /boot` first.
- **PostgreSQL/MySQL major versions do not follow the distribution upgrade.** A database that moves from PostgreSQL 13 to 15 needs `pg_upgrade` with its own rehearsal — treat it as a separate project.
- **SELinux relabel is not optional.** On EL rebuilds, a filesystem relabel after the upgrade is normal and slow; if you disable SELinux to "speed things up", you will be debugging denials for weeks.
- **Cloud images behave differently.** Vendor cloud images carry their own agents and metadata services; validate against a fresh instance rather than a converted VM.
- **The post-upgrade kernel is not the running kernel.** Reboot before declaring success, and confirm with `uname -r` against the installed kernel list.

## FAQ

### How long does an in-place RHEL 8 to 9 upgrade take?

Plan 45-90 minutes of downtime per host: roughly 20-40 minutes of package transaction, plus two reboots, plus the application validation window. Hosts with large package sets or slow storage regularly exceed that. The pre-upgrade analysis itself takes 5-15 minutes and can be run during business hours.

### Can ELevate upgrade CentOS 7 directly to AlmaLinux 9?

Not in one step. The supported pattern is 7 → 8, validate, then 8 → 9. Chaining both hops in a single window removes your ability to stop at a known-good intermediate state, and the package delta between EL7 and EL9 is large enough that a single leap surfaces failures you cannot isolate.

### Does do-release-upgrade support rollback?

No. Ubuntu's tool has no rollback mechanism. Your rollback is a filesystem snapshot, a VM snapshot, or a reinstall. Take the snapshot before starting and verify the snapshot's consumption does not approach its budget during the transaction.

### Should I upgrade or reinstall in place?

Upgrade when the host is clean: packages all from official repositories, no custom kernel, no hand-compiled software, and a single major version of drift. Reinstall when the host has accumulated configuration you cannot reproduce, or when it is more than one major version behind — a rebuild from an image is usually faster and always more predictable than a two-hop migration.

### Is upgrading Alpine Linux supported?

Alpine documents editing `/etc/apk/repositories` and running `apk upgrade --available`, but there is no pre-upgrade analyser and no supported rollback. For containers, rebuild the image from a current base instead. For Alpine hosts, treat an in-place jump as a rebuild-with-extra-steps.

### What breaks most often during these upgrades?

Third-party repositories and out-of-tree kernel modules, in that order. Both are fixable in advance: disable the repositories, and check `dkms status` plus `lsmod` against the target kernel's module availability before scheduling the window.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "In-Place Linux Upgrades in 2026: Leapp vs ELevate vs do-release-upgrade",
  "description": "A decision guide to in-place Linux distribution upgrades: Leapp for RHEL, ELevate for EL rebuilds and cross-distro hops, do-release-upgrade for Ubuntu LTS, plus snapshot rehearsal and real failure modes.",
  "datePublished": "2026-11-20",
  "dateModified": "2026-11-20",
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

The rollback strategy in this guide depends on having snapshots with real budgets — our [LVM layout guide](../2026-11-20-lvm-layout-thin-pools-lvmraid-stratis-zfs-2026/) covers the arithmetic, and the [ZFS snapshot management walkthrough](../2026-05-20-self-hosted-zfs-snapshot-management-sanoid-zrepl-zfs-auto-snapshot-guide/) covers retention tooling. If you are planning to rebuild rather than migrate, the [container base image comparison](../2026-05-11-container-base-images-alpine-distroless-debian-slim-comparison/) is the starting point for a lean, reproducible image.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
