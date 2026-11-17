---
title: "virtiofs vs 9p vs NFS in 2026: The Fastest Way to Share Files With a VM"
date: "2026-11-18"
tags: ["virtualization", "storage", "linux-kernel", "self-hosted"]
draft: false
---

Sharing a host directory into a virtual machine is one of those problems every self-hoster solves badly at least once. You mount a folder with 9p because it is the default in every tutorial, then wonder why `git status` inside the guest takes eight seconds, why `npm install` crawls, or why half your files show up with the wrong ownership. The fix has existed since Linux 5.4, but most guides still point at the 2008 answer.

This is a comparison of the three options that actually matter in 2026 — virtiofs, 9p, and NFS — with the exact invocation each one needs and an honest account of where each breaks.

## TL;DR: virtiofs for Local Shares, NFS for Anything That Crosses a Network

- **Use virtiofs** for sharing a host directory with a local VM. It is a FUSE daemon backed by shared memory rather than a synthetic network protocol, it supports DAX for near-native read performance, and it is the only one of the three designed for this job. Cost: kernel 5.4+ in the guest, Linux guests only.
- **Use 9p** only for compatibility — old guests, unusual kernels, quick throwaway labs. It works everywhere, and it is slow everywhere.
- **Use NFS** when more than one machine needs the data, or when the guest must survive host reboots and live migration without re-establishing a virtio channel. It is the only real multi-client option here.

If your VM is on the same box and runs Linux, **virtiofs is not a marginal improvement over 9p — it is a different category of performance.**

## The Three Approaches Side by Side

| Dimension | virtiofs | 9p (virtio-9p) | NFS (kernel nfsd / Ganesha) |
|---|---|---|---|
| Transport | vhost-user over shared memory | virtio-9p synthetic device | TCP/UDP over the network stack |
| Guest kernel requirement | 5.4+ (`virtio_fs`) | ancient, effectively universal | universal |
| Host daemon | `virtiofsd` (Rust, vhost-user) | inside QEMU | `nfsd` or `nfs-ganesha` |
| Data path | FUSE requests over shared memory queues | per-message 9P round trips | RPC with a page cache on both ends |
| Local performance | near-native for metadata-light IO; DAX for cache-friendly reads | poor for metadata-heavy workloads | good, but with network and RPC overhead |
| DAX / mmap window | yes (`virtiofs` DAX) | no | no (page cache only) |
| Multiple guests at once | yes, one daemon per VM | yes, per QEMU process | yes, that is the point |
| Non-Linux guests | no (Linux only) | yes (Windows, BSD with drivers) | yes (Windows, macOS, BSD natively) |
| Live migration | supported, with caveats | awkward | transparent |
| Typical 2026 use | local VM shares, Kata Containers | legacy labs, BSD/Windows guests | NAS, clusters, mixed-OS fleets |

Notice what is not in that table: a performance number. Anyone quoting a single figure for "virtiofs vs 9p" is measuring one workload, and the ranking flips depending on whether you are doing `ls -l` on 100,000 files or streaming a 20 GB file.

## Decision Matrix

| Your situation | Use | Why |
|---|---|---|
| Linux guest on the same host | **virtiofs** | Shared-memory transport, DAX, proper POSIX semantics including xattrs and ACLs |
| Windows or BSD guest | **NFS** | virtiofs has no Windows client; 9p drivers exist but are unloved |
| Data needed by three VMs and a laptop | **NFS** | Multi-client with real locking and consistent permissions |
| Quick `qemu -virtfs` one-liner for a test box | **9p** | Zero host setup, works on any kernel |
| Guest must live-migrate between hosts | **NFS** | Reconnect is transparent; virtiofs needs the daemon migrated too |
| Container runtime using a VM boundary (Kata) | **virtiofs** | It is the default there for a reason |

## virtiofs: The Modern Default

virtiofs splits the job in two. The guest mounts a filesystem that speaks FUSE; on the host, `virtiofsd` implements the FUSE side as a vhost-user daemon and serves requests from a *shared memory* region rather than from a socket emulating a network protocol. The result keeps FUSE's semantics — full POSIX behavior, xattrs, ACLs, SELinux labels — while removing the round-trip cost that made FUSE-over-virtio slow.

The daemon is written in Rust and lives in its own repository now, built with cargo:

```bash
# build dependencies (Fedora/RHEL family)
sudo dnf install libcap-ng-devel libseccomp-devel
# or Debian/Ubuntu
sudo apt install libcap-ng-dev libseccomp-dev

git clone https://gitlab.com/virtio-fs/virtiofsd.git
cd virtiofsd && cargo build --release
```

The project's own documented example exports `/mnt` on a socket and wires it into QEMU:

```bash
# 1. start the daemon
virtiofsd --socket-path=/tmp/vfsd.sock --shared-dir /mnt \
        --inode-file-handles=mandatory &

# 2. attach it to the VM through vhost-user
qemu-system-x86_64 \
        -chardev socket,id=char0,path=/tmp/vfsd.sock \
        -device vhost-user-fs-pci,queue-size=1024,chardev=char0,tag=myfs \
        -object memory-backend-memfd,id=mem,size=4G,share=on \
        -numa node,memdev=mem \
        -accel kvm -m 4G

# 3. mount inside the guest
mount -t virtiofs myfs /mnt
```

Three details in that command are load-bearing and routinely omitted by tutorials:

**`memory-backend-memfd` with `share=on`, plus `-numa node,memdev=mem`.** The shared memory region is the transport. Without it the device attaches but the guest cannot map the queues, and you get an obscure failure rather than a helpful error.

**`queue-size=1024`.** The default queue depth is much smaller; virtiofsd's documentation explicitly calls for a larger queue when you care about throughput. Metadata-heavy workloads live or die on queue depth.

**`--inode-file-handles=mandatory`.** This makes the daemon reference inodes by file handle instead of holding an `O_PATH` file descriptor per open file. It is required for sane behavior under migration and for very large file counts where file-descriptor exhaustion is otherwise guaranteed.

The daemon must run as root, or as fake root inside a user namespace — `podman unshare -- virtiofsd ...` is the documented pattern for rootless hosts. It drops capabilities aggressively at startup and confines itself with seccomp; `--sandbox` controls whether it chroots. If you are auditing a deployment, those are the knobs that matter.

Caching policy is the other decision: `--cache=auto` (default), `always`, `metadata`, or `never`. For a directory that only the VM touches, `--cache=always` is fastest. For a directory shared with the host, `auto` or `metadata` avoids stale-data surprises. And note `--allow-mmap` is only safe when the VM has exclusive access to the directory — enabling it on a shared folder is how you get silent corruption.

One documented compatibility wart worth knowing: virtiofsd can advertise a filesystem tag through `--tag`, but QEMU 8.1 ignores the config feature, and QEMU 7.1 through 8.0 would crash while trying to log a warning about it. Set the tag on the QEMU side, as in the example above, and skip `--tag`.

## 9p: The Compatibility Fallback

9p is a Plan 9 network protocol that QEMU implements over a synthetic virtio device. It has one real advantage — it exists — and one real cost — every operation is a message exchange, including `stat`. That is why extracting a large archive or listing a big directory over 9p feels like working over a bad VPN even though the data never leaves the machine.

The setup is genuinely short, which is why it survives in tutorials:

```bash
qemu-system-x86_64 \
        -virtfs local,path=/srv/share,mount_tag=hostshare,security_model=mapped-xattr,id=hostshare \
        ...
# inside the guest
mount -t 9p -o trans=virtio,version=9p2000.L hostshare /srv/share
```

`security_model` is where 9p deployments usually go wrong. `passthrough` exposes host UIDs directly and requires the guest to be trusted; `mapped-xattr` and `mapped-file` store ownership metadata in extended attributes or sidecar files, which means your host directory gets littered with `user.virtfs.*` attributes. Neither option gives you clean shared-ownership semantics, and neither supports the full xattr/ACL surface that virtiofs does.

Use 9p when a guest cannot do better — an old distribution, a BSD guest with a 9p driver, a one-off recovery VM. Do not use it for a development share you will touch every day.

## NFS: When the Share Outlives the VM

NFS is the answer to a different question. It is not a local transport; it is a distributed filesystem with a 40-year-old protocol, real locking, and clients in every operating system ever shipped. If two VMs, a laptop, and a container host all need the same data, nothing in this comparison replaces it.

On a modern host you have two servers to choose from. The in-kernel `nfsd` is the default and is configured through `/etc/exports`:

```bash
# /etc/exports
/srv/share  10.0.0.0/24(rw,sync,no_subtree_check,root_squash)
```

NFS-Ganesha (1,808 stars, actively pushed in November 2026) is the userspace alternative: NFSv3, v4.0, and v4.1, pluggable FSAL backends so it can export CephFS or GlusterFS as easily as a local directory, and a single configuration file:

```
NFS_CORE_PARAM {
    Protocols = 3, 4;
    NFS_Port = 2049;
}

EXPORT {
    Export_Id = 1;
    Path = /srv/share;
    Pseudo = /share;
    Access_Type = RW;
    Squash = root_squash;
    FSAL { Name = VFS; }
    CLIENT {
        Clients = 10.0.0.0/24;
        Access_Type = RW;
        Squash = root_squash;
    }
}
```

Ganesha is the right pick when the backend is not a plain local filesystem, or when you want NFSv4.1 with pNFS without depending on kernel version. For a directory on local disk, kernel `nfsd` is simpler and faster.

**Where NFS hurts inside a VM:** the traffic goes through the full network stack even when it is a loopback path, so small-file metadata operations pay RPC overhead. `sync` exports cost you a flush per write. And `root_squash` plus UID mismatch is the number one reason people see "permission denied" on a share that looks correctly configured.

## Performance Reality Check

Benchmark claims for this trio are usually dishonest because they pick one workload. The defensible summary:

- **Large sequential reads and writes:** virtiofs and NFS are both close to native; 9p is far behind.
- **Metadata-heavy operations** (`find`, `git status`, package installs): virtiofs wins clearly, NFS is acceptable, 9p collapses.
- **Multi-client access:** NFS only. virtiofs and 9p are per-VM channels.
- **Memory-mapped access:** virtiofs DAX is the only option that avoids double caching.

If you want numbers rather than rankings, benchmark with your own tree: `fio` for throughput and `fs-mark` or a plain `tar -xf` of your real source tree for metadata. Our [io_uring and fio benchmarking guide](../2026-05-23-self-hosted-linux-io-uring-tool-ecosystem-liburing-fio-uring-bench-guide/) covers the tooling.

## Pitfalls That Bite in Production

**Forgetting the shared memory backend.** virtiofs without `memory-backend-memfd,share=on` and the matching `-numa node,memdev=` will not work, and the error message does not say so.

**Mixing cache policies with host-side writers.** `--cache=always` plus host edits equals stale reads inside the guest. Either give the VM exclusive ownership or drop to `auto`.

**Assuming virtiofs works for Windows guests.** It does not. There is no virtiofs client for Windows; use NFS or SMB.

**Running virtiofsd as an unprivileged user with mismatched UIDs.** The daemon can run rootless, but guest UIDs must line up with the host's effective UID, or you need `--translate-uid`/`--translate-gid`. Otherwise every file appears owned by `nobody`.

**Exporting an NFS share with `root_squash` and then wondering why root in the guest cannot write.** That is the feature working. Map the application UID explicitly or set `no_root_squash` on a trusted, isolated network only.

**Expecting live migration to be free.** virtiofs supports migration, but the daemon and its inode state must move too; NFS reconnects by design. If migration is a hard requirement, NFS is the lower-risk answer.

For the multi-host storage layer underneath NFS, our [NFS high availability guide](../2026-05-11-self-hosted-nfs-high-availability-drbd-glusterfs-pacemaker-guide/) covers DRBD, GlusterFS, and Pacemaker failover. If you are comparing parallel filesystems for a cluster rather than a single share, the [Lustre, BeeGFS and MooseFS comparison](../2026-06-12-self-hosted-hpc-parallel-filesystems-lustre-beegfs-moosefs-guide/) is the next read, and the [block-level NBD guide](../2026-05-14-self-hosted-nbd-storage-server-nbd-server-nbdkit-drbd-guide/) covers what to do when you need a raw device instead of a filesystem.

## FAQ

### Is virtiofs faster than 9p?

Yes, substantially, especially for metadata-heavy work. virtiofs moves FUSE requests over shared memory with a configurable queue depth, while 9p performs a message round trip for operations as small as `stat`. Sequential throughput also favors virtiofs, and only virtiofs offers a DAX window for memory-mapped reads.

### What kernel version do I need for virtiofs in the guest?

Linux 5.4 or newer for the `virtio_fs` driver. The host needs a QEMU with `vhost-user-fs-pci` support and the `virtiofsd` daemon. Distributions shipping 5.15 LTS and later kernels are all fine.

### Can I use virtiofs to share files with a Windows VM?

No. There is no virtiofs client driver for Windows. Use NFS, SMB, or a block device with a native filesystem for Windows guests.

### Do I still need NFS if I use virtiofs?

Only if more than one machine needs the data. virtiofs is a per-VM channel over shared memory — it has no concept of multiple clients, no distributed locking, and no meaning across hosts. For a single Linux guest on the same box, NFS is unnecessary overhead; for three clients, virtiofs cannot do the job.

### Why does my virtiofs mount show every file owned by nobody?

UID mapping. Either run the guest with UIDs that match the host, or pass `--translate-uid`/`--translate-gid` to virtiofsd. The same symptom appears when the daemon runs rootless and the guest uses a different ID range.

### Which one should I use for a Kubernetes or Kata Containers node?

virtiofs. Kata Containers uses it to mount volumes into the guest VM precisely because it provides POSIX semantics with acceptable overhead, which neither 9p nor a network filesystem does well at that layer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "virtiofs vs 9p vs NFS in 2026: The Fastest Way to Share Files With a VM",
  "description": "Performance and configuration comparison of virtiofs, 9p and NFS for sharing host directories with virtual machines, including real virtiofsd and QEMU commands",
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
