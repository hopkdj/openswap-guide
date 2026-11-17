---
title: "ublk vs NBD vs tcmu in 2026: Which Userspace Block Driver Actually Wins?"
date: "2026-11-18"
tags: ["storage", "linux-kernel", "block-devices", "self-hosted"]
draft: false
---

Your kernel's block layer is no longer the only place to implement a disk. Since the `ublk` driver landed in mainline Linux 6.0, "userspace block device" stopped being a synonym for "slow NBD hack" and became a legitimate architecture choice: io_uring-native, multi-queue, and fast enough that distribution kernels now ship it by default. Meanwhile the two older options — NBD and tcmu — did not disappear. They kept their niches, and picking the wrong one costs you a rewrite six months later.

This guide compares all three from the kernel data path up, with the actual commands each one needs.

## TL;DR: Pick by Kernel Version and by Protocol, Not by Benchmark Screenshots

- **Choose ublk** if you run Linux 6.0+ on hardware you control and you are writing new storage logic (qcow2 mapping, encryption, dedup, network-backed disks). It gives you multi-queue blk-mq with per-queue tags and an io_uring passthrough data path.
- **Choose NBD** if the block device must cross a machine boundary over a plain TCP socket, or if you need something that works on a 2016-era kernel and every hypervisor on earth speaks.
- **Choose tcmu** only if you must expose SCSI semantics — iSCSI or Fibre Channel LUNs to external initiators — while the actual storage logic lives in userspace.

If you are building a local virtual disk on a modern kernel, **ublk wins and it is not close**. If you are bridging hosts, **NBD still wins on portability**. tcmu is a specialist tool, and it shows its age.

## The Three Architectures Side by Side

| Dimension | ublk | NBD | tcmu (LIO TCM-User) |
|---|---|---|---|
| In-kernel since | Linux 6.0 (`ublk_drv`) | 2.4 era, two decades of production use | Linux 3.17 (LIO user backstore) |
| Data path | io_uring passthrough (`uring_cmd`) | socket send/recv speaking the NBD wire protocol | UIO ring + netlink, SCSI CDB pass-through |
| Device node | `/dev/ublkb0`, control at `/dev/ublk-control` | `/dev/nbd0` | a LIO LUN, not a local block node |
| Queue model | blk-mq, multi-queue, one tag per request | one socket per connection, commands pipelined | SCSI task per command via one UIO ring |
| Scope | local host only | local or remote (TCP / Unix socket) | local host only, re-exported as SCSI |
| Reference userspace | ublksrv (224★), libublk-rs (62★, active Nov 2026) | nbd-server (551★), nbdkit, nbdublk | tcmu-runner (197★, last push May 2024) + targetcli-fb (124★) |
| What you must implement | all IO semantics yourself | the NBD protocol (already done for you) | SCSI command handling for your backstore |
| Best fit | qcow2, encryption, tiering, test doubles | cross-host block export, VM images | iSCSI/FC targets with userspace backends |
| Ecosystem momentum (2026) | high — actively developed | stable, maintenance-driven | low, effectively frozen |

The momentum column matters more than any microbenchmark. Two of these three projects have commits from this week. One does not.

## Decision Matrix: Ten Seconds to a Choice

| Your situation | Use | Why |
|---|---|---|
| Local virtual disk, kernel ≥ 6.0, custom logic | **ublk** | Multi-queue + io_uring, no protocol overhead, crashes in userspace do not panic the host |
| Export a disk to another physical host today | **NBD** | Only one of the three designed for a network transport |
| Present storage to ESXi, Proxmox iSCSI, or a SAN fabric | **tcmu** | LIO gives you real SCSI target semantics |
| You need qcow2 without QEMU in the loop | **ublk** (qcow2 target) or tcmu qcow handler | Both have qcow handlers; ublk's is actively maintained |
| Kernel 5.15 LTS fleet | **NBD** | ublk is not in 5.15 |
| Containerized storage appliance | **ublk** (with device passthrough) or **NBD** | tcmu's DBus + UIO model is hostile to containers |
| You want the fastest loop device on one box | **ublk** | Kernel docs explicitly position it as the high-performance userspace block implementation |

## ublk: The io_uring-Native Option

The kernel documentation is refreshingly blunt about the motivation: moving virtual block drivers into userspace makes them writable in any language, debuggable with normal tools, installable without rebuilding the kernel, and far less dangerous when they crash. A bug in a userspace block server is a failed device; a bug in an in-kernel block driver is a bad afternoon.

The architecture is a clean split:

- A **control plane** on `/dev/ublk-control` with explicit commands — `UBLK_CMD_ADD_DEV`, `UBLK_CMD_SET_PARAMS`, `UBLK_CMD_START_DEV`, `UBLK_CMD_STOP_DEV`, `UBLK_CMD_DEL_DEV`, plus `UBLK_CMD_GET_QUEUE_AFFINITY` so the server can pin IO threads to the right CPUs.
- A **data plane** where every request to `/dev/ublkb0` is forwarded to the server, handled, and committed back — both directions through io_uring passthrough commands.

That last detail is why ublk exists at all. The kernel docs state plainly that io_uring passthrough gives better IOPS than ordinary block IO, which is what makes ublk a high-performance implementation rather than a convenience wrapper.

Bringing up a loop-style device with `ublksrv` is three commands:

```bash
# load the driver (present in mainline since 6.0)
sudo modprobe ublk_drv

# create a userspace-backed loop device over a file
sudo ublk add -t loop -f /var/lib/ublk/disk0.img

# inspect what the kernel negotiated: queues, depth, device id
sudo ublk list
```

From there it behaves like any block device, which means the ordinary format-and-mount workflow applies:

```bash
sudo mkfs.xfs /dev/ublkb0
sudo mount /dev/ublkb0 /mnt
# every IO on this mount is now handled by the userspace server over io_uring
sudo umount /mnt
sudo ublk del -n 0
```

Two implementation projects matter. **ublksrv** (C/C++, 224 stars, pushed October 2026) provides `libublksrv` plus ready-made loop and null targets. **libublk-rs** (Rust, 62 stars, pushed November 2026) is the crate to reach for if you are writing a new target — it ships runnable examples, so `cargo build --release --examples` is the fastest way to see the control-plane dance in code.

There is even a bridge between two of the tools in this article: Richard W.M. Jones' `nbdublk` implements an NBD client as a ublk target, using `libublksrv`. That is the cleanest illustration of ublk's role — it is a *framework* for block semantics, not a protocol.

**Where ublk hurts:** you own durability, recovery, and every edge case. If your server process dies, the device dies with it. Queue depth and the number of hardware queues are negotiated at `ADD_DEV` time and immutable afterward, so sizing mistakes mean tearing the device down. And if `io_uring` is restricted on the host — for example `kernel.io_uring_disabled` set by a hardened image — ublk simply will not run.

## NBD: Still the Interoperability King

NBD does one thing: it carries block IO over a socket. That narrowness is why it still matters. Nothing else in this comparison can put a block device on a machine across the room, and NBD clients exist in the kernel, in QEMU, in libguestfs, and in more hypervisors than you want to count.

Server side, `nbd-server` is configured with a two-section INI file:

```ini
[generic]
    user = nbd
    group = nbd
    listenaddr = 0.0.0.0
    port = 10809

[export0]
    exportname = /srv/nbd/disk0.img
    authfile = /etc/nbd-server/allow
    readonly = false
```

Client side, the kernel module needs enough partitions pre-allocated before you connect:

```bash
sudo modprobe nbd max_part=16
sudo nbd-client storage.internal 10809 /dev/nbd0
# ... use /dev/nbd0 ...
sudo nbd-client -d /dev/nbd0
```

If you want NBD without the daemon, **nbdkit** is the more modern server: plugin-based, with filters for caching and rate limiting, and the ability to back an export with something that is not a file at all. Its GitHub mirror has been frozen since 2023 because upstream development happens on GitLab — do not read that as abandonment.

**Where NBD hurts:** the protocol has no built-in encryption, so anything leaving the host belongs inside WireGuard or a TLS tunnel. A classic single-connection setup serializes round trips, which is why modern `nbd-client` supports multiple connections per device — turn that on before you blame NBD for latency. And `max_part` defaults to zero, a mistake that produces the confusing symptom of a connected device with no visible partitions.

## tcmu: When You Need SCSI, Not a Block Device

tcmu is not a block driver. It is the userspace side of LIO's TCM-User backstore: a daemon (`tcmu-runner`) that receives UIO/netlink events and SCSI CDBs, dispatches them to a handler plugin, and returns results. You get SCSI semantics — persistent reservations, task management, the full CDB set — with the storage logic in userspace.

Configuration flows through `targetcli`, and every handler takes a `cfgstring`. Using the RADIUS-free, unambiguous rbd example from the project's own README:

```
/> cd /backstores/user:rbd
/backstores/user:rbd> create cfgstring=pool/rbd1;osd_op_timeout=30 name=rbd0 size=1G
Created user-backed storage object rbd0 size 1073741824.
```

The format is worth memorizing because it is where most first attempts fail:

```
cfgstring=<handler args>;<tcmu-runner daemon args>;<handler args>
```

Out of the box, tcmu-runner installs `file`, `zbc`, `glfs`, `qcow`, and `rbd` handlers — so zoned block devices, CephFS files, Ceph RBD images, and qcow2 files can all become LUNs. Exporting one over iSCSI is standard LIO work:

```
/> cd /iscsi
/iscsi> create iqn.2026-11.io.example:storage.target01
/iscsi> cd iqn.2026-11.io.example:storage.target01/tpg1/luns
/iscsi/.../luns> create /backstores/user:rbd/rbd0
```

**Where tcmu hurts:** the project's last push was May 2024, and it depends on a DBus system service plus a UIO device per backstore. That combination is awkward in containers and awkward on modern kernels where UIO is increasingly discouraged. If you need SCSI target semantics today and your backend can be a file or a device, a kernel backstore in LIO is simpler and faster. Reach for tcmu only when the backend genuinely requires userspace code.

## Pitfalls That Cost People Weekends

**Do not benchmark them against each other and draw conclusions about your workload.** ublk's advantage comes from io_uring passthrough on a local device; NBD's cost profile is dominated by network round trips. A single-host fio run will make ublk look transformative and tell you nothing about a cross-host NBD deployment.

**Queue sizing is immutable on ublk.** `nr_hw_queues`, `queue_depth`, and max IO buffer size are negotiated at `UBLK_CMD_ADD_DEV` and set before `UBLK_CMD_START_DEV`. Get them wrong and you must stop and recreate the device — there is no live resize.

**A dead server means a dead device.** All three tools move IO logic out of the kernel, and all three fail closed when the userspace half disappears. Plan a supervisor (systemd with `Restart=always`) and decide in advance whether a hung device should block writes or fail them.

**Privileges do not vanish because the code left the kernel.** ublk needs `/dev/ublk-control` and a server able to create io_uring instances; tcmu needs DBus and UIO; NBD needs the `nbd` module. In containers this usually means `--device` passthrough and additional capabilities, not a plain `docker run`.

**`max_part=0` is the default for NBD.** If `lsblk` shows the disk but no `nbd0p1`, you forgot the module parameter — and you must disconnect and re-modprobe, not just re-run `nbd-client`.

For the io_uring side of the stack, our [liburing and fio benchmarking guide](../2026-05-23-self-hosted-linux-io-uring-tool-ecosystem-liburing-fio-uring-bench-guide/) covers the tooling that makes ublk's data path measurable. If you are comparing transport options rather than local drivers, the [NBD, nbdkit and DRBD guide](../2026-05-14-self-hosted-nbd-storage-server-nbd-server-nbdkit-drbd-guide/) goes deeper on network block storage, and the [NVMe over Fabrics comparison](../2026-06-02-nvme-over-fabrics-spdk-linux-ceph-guide/) is the right next step when a socket-based protocol is not fast enough.

## FAQ

### Is ublk faster than NBD?

For a local disk, yes — usually by a wide margin. ublk forwards requests through io_uring passthrough and the kernel documentation notes this yields better IOPS than ordinary block IO, while NBD pays for a socket protocol even when the server is on the same machine. For a disk that genuinely lives on another host, the network dominates and the comparison is meaningless.

### Can I run ublk on an LTS kernel older than 6.0?

Not from mainline. `ublk_drv` arrived in Linux 6.0. Check with `modinfo ublk_drv` before designing around it; on a 5.15 fleet, NBD is the pragmatic choice and `nbdublk` is not available either.

### Does NBD encrypt traffic?

No. The NBD protocol itself has no encryption layer, so exports that cross an untrusted network should be carried inside WireGuard, IPsec, or a TLS tunnel such as stunnel. If you need per-device encryption at the block layer instead, do it in the ublk server or use dm-crypt underneath.

### Which one should I use to serve qcow2 images?

Both ublk (via the qcow2 target shipped with `ublksrv`) and tcmu (via its `qcow` handler) can map qcow2 files to a block device without QEMU. ublk is the better bet in 2026 purely on maintenance activity — libublk-rs and ublksrv both have commits from this month, while tcmu-runner has not been touched since May 2024.

### Can these be used inside containers?

With care. ublk requires access to `/dev/ublk-control` and permission to create io_uring instances; NBD requires the `nbd` kernel module and typically `--privileged` or explicit device access; tcmu requires a UIO device plus a DBus system bus. In Kubernetes, all three are better run as a DaemonSet on the node than as a sidecar.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ublk vs NBD vs tcmu in 2026: Which Userspace Block Driver Actually Wins?",
  "description": "A technical comparison of Linux userspace block device implementations: ublk (io_uring passthrough), NBD (network block device) and tcmu (LIO TCM-User), with real kernel commands",
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
