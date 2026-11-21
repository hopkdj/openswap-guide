---
title: "fsync() Is Not Durability: How Linux Storage Lies About Writes in 2026"
date: "2026-11-22"
description: "fsync() returned 0 and your data still vanished. A hands-on guide to proving write durability with fio, dm-flakey and pg_test_fsync, plus the exact syscall semantics that decide whether a committed write survives a power cut."
tags: ["storage", "linux", "filesystem", "performance", "durability", "benchmarking"]
draft: false
---

Your application called `fsync()`. The kernel returned `0`. Two seconds later the rack lost power, and the row your customer paid for was not in the database. No error was logged, no alert fired, and the backup was 40 minutes old. This is the single most common silent data-loss bug in production, and it is not a database bug — it is a misunderstanding of what `fsync()` actually promises.

`fsync()` does not put your bytes on the platter or in the NAND. It asks the kernel to hand the data to the storage device and wait for the device to *report* that it is persisted. If the device has a volatile write cache and nobody told it to flush that cache to media, the device can acknowledge the write while the data is still sitting in DRAM on the drive controller. Cut power at that instant and the write never happened — but every layer above it believed it did.

**The fix is not "call fsync harder."** It is knowing which syscall gives you which guarantee, verifying that your drive honors cache flushes, and testing the failure path instead of hoping. This guide does all three with tools you can run today.

## TL;DR — Quick Verdict

- **If you need durability for a database or a payment ledger:** use `fsync()` (or `fdatasync()` when metadata is irrelevant), keep `fsync=on`, and verify the drive does not have a lying volatile cache. Anything else is a latency optimization that spends durability.
- **If you need fsync per write and want to know the real cost:** benchmark with **fio** first — its `--fsync=1` job is the cheapest way to discover that your cloud volume does 400 fsyncs/sec instead of 40,000.
- **If you want to prove your recovery path works:** inject real lost writes with **dm-flakey** (`drop_writes`), then watch whether your database notices.
- **If you run PostgreSQL:** run **pg_test_fsync** once per host before you tune anything. It measures the five `wal_sync_method` options on *your* filesystem in about 30 seconds.
- **Do not:** trust `sync_file_range()`, trust `barrier=0`, trust `synchronous_commit=off` with money, or trust a benchmark run on a laptop NVMe to predict a network-attached cloud volume.

## Syscall Semantics: What Each Call Actually Guarantees

Most teams lose data because they picked the wrong call from this table, or because they assumed two of these rows were equivalent.

| Call | Flushes data | Flushes file metadata (size, mtime) | Flushes directory entry | Waits for device cache flush | Typical relative cost |
|---|---|---|---|---|---|
| `fsync(fd)` | Yes | Yes | No | Yes, if device supports flush | Highest |
| `fdatasync(fd)` | Yes | Only what is needed to read the data back | No | Yes | High (cheaper than fsync on ext4/XFS) |
| `open(..., O_SYNC)` | Yes, per write | Yes, per write | No | Yes, per write | Very high — penalizes every `write()` |
| `open(..., O_DSYNC)` | Yes, per write | Only size-relevant metadata | No | Yes, per write | High |
| `sync_file_range(fd)` | Starts writeback | No | No | **No** | Cheap — not a durability call |
| `syncfs(fd)` | Yes, whole filesystem | Yes | Yes | Yes | Highest, unscoped |
| `msync(addr, len, MS_SYNC)` | Yes, mapped pages | Depends | No | Yes | High |

Two rows deserve a warning label. `sync_file_range()` is a *writeback scheduling hint* — it is legal for the kernel to return before anything reaches the device, and it does not order metadata. Code that replaced `fsync()` with `sync_file_range()` for "performance" is not durable, full stop. And `O_SYNC` on every `write()` is usually slower than batching writes and calling `fdatasync()` once, because it forces a device flush per syscall instead of per transaction.

The second thing the table hides: **`fsync()` on a file does not persist the file's name.** If you write a temp file and `rename()` it into place, you must also `fsync()` the parent directory, or a crash can leave you with the new content on disk and the old directory entry — or no entry at all.

```c
int fd = open("/var/lib/app/data.tmp", O_WRONLY | O_CREAT | O_TRUNC, 0644);
write(fd, buf, len);
fsync(fd);          /* content is durable */
close(fd);

rename("/var/lib/app/data.tmp", "/var/lib/app/data.bin");

int dfd = open("/var/lib/app", O_RDONLY | O_DIRECTORY);
fsync(dfd);         /* the rename itself is durable */
close(dfd);
```

Skip that last `fsync(dfd)` and you have written a durable file that nothing can find after a crash. It is the most common filesystem-level mistake in hand-rolled storage code, and it is invisible in testing because the page cache keeps the name alive until the machine dies.

## Why a Device Can Acknowledge a Write It Has Not Persisted

A modern drive is a small computer. It has DRAM (or SRAM) cache, a firmware scheduler, and a mapping table. When the kernel issues a write, the drive can accept it into that cache and report completion immediately. Its *volatile write cache* is exactly what makes it fast — and exactly what makes your `fsync()` a lie if the cache is not flushed.

The kernel's defense is the **cache flush** command (ATA `FLUSH CACHE`, SCSI/NVMe `FLUSH`). `fsync()` triggers it, but only if the block layer believes the device needs it. That belief comes from the device's advertised capabilities, and it can be wrong in both directions:

- **Write cache enabled but not advertised** (cheap USB bridges, some virtual disks): the kernel skips the flush, the drive keeps lying.
- **Flush advertised but ignored** (firmware bugs, some RAID controllers with a "write-back" policy and no battery): the flush returns success without doing anything.
- **Filesystem barriers disabled** by an admin chasing benchmark numbers (`barrier=0` on ext4, `nobarrier` on XFS, `noflush` style options elsewhere): the filesystem stops emitting flushes entirely.

Check the device before you write a single line of durable code:

```bash
# ATA/SATA: is the write cache on?
sudo hdparm -W /dev/sda
# /dev/sda:
#  write-caching =  1 (on)

# NVMe: does the controller advertise a volatile write cache? (VWC bit)
sudo nvme id-ctrl /dev/nvme0 | grep -i vwc
# vwc       : 0x1

# SMART view for SATA, including cache state as the firmware reports it
sudo smartctl -i /dev/sda | grep -i -A1 "write cache"
```

If `vwc` is `0x1` on NVMe, a flush is mandatory and `fsync()` is doing real work — which is also why your write latency is bound by flush latency, not by bandwidth. If `hdparm -W` reports the cache is on for a drive that has **no power-loss protection**, you are one `hdparm -W 0` (or one uninterruptible power supply) away from a durable system.

On ext4 there is one more detail worth knowing: since kernel 4.13, writeback errors are tracked per file and **a failed `fsync()` returns `EIO`**, and *subsequent* `fsync()` calls on the same file also return `EIO` instead of silently succeeding. Before that change, a failed writeback could be reported once and then forgotten. If your code ignores `fsync()` return values, you are discarding the only signal the kernel gives you.

## Tool 1: fio — Measuring the Real Cost of Durability

`fio` (6,436 stars, last pushed 2026-11-20) is the reference I/O workload generator, and it is the only realistic way to find out what a flush costs on your hardware instead of guessing from a spec sheet. Install it from your distribution (`apt install fio`, `dnf install fio`, `apk add fio`) — it has no runtime dependencies worth mentioning.

A job that does one 4 KiB random write followed by one `fsync`, with `O_DIRECT` to bypass the page cache:

```ini
[global]
ioengine=libaio
direct=1
filename=/mnt/test/durability.dat
size=512M
iodepth=1
runtime=60
time_based=1

[fsync-per-write]
rw=randwrite
bs=4k
fsync=1
```

`fsync=1` means "issue an fsync after every 1 write operation". Compare it against the same job with `fdatasync=1`, and against a variant with no sync at all. The gap between the third and the first is your durability tax, and it is routinely two to three orders of magnitude on network-attached block storage.

```bash
fio --name=durability --filename=/mnt/test/fio.dat --size=512M \
    --bs=4k --rw=randwrite --iodepth=1 --fsync=1 \
    --ioengine=libaio --direct=1 --runtime=60 --time_based
```

Then verify rather than assume — this is the part almost nobody runs. A verification job writes a known pattern, forces flushes, and checks every block on a second pass:

```bash
fio --name=verify-durability --filename=/mnt/test/verify.dat --size=512M \
    --bs=4k --rw=randwrite --fsync=1 --verify=crc32c \
    --verify_fatal=1 --ioengine=libaio --direct=1
```

`--verify_fatal=1` makes fio stop on the first mismatch instead of continuing. If you run this on a device that lies about flushes and you cut power mid-run, you get the names of the blocks that vanished — which is exactly the evidence your storage vendor will ask for and exactly the evidence most teams cannot produce.

For a broader picture of what the same box does under sequential, random, and mixed load, our [storage benchmarking walkthrough](../2026-06-16-self-hosted-storage-benchmarking-fio-sysbench-bonniepp/) covers the job files worth keeping in a repo.

## Tool 2: dm-flakey — Injecting the Power Cut You Cannot Schedule

You cannot ask a cloud provider to yank the power at the exact microsecond you want. You can, however, make the block layer drop writes on a schedule. The device-mapper `flakey` target does precisely that: it presents a working device, then periodically stops honoring writes.

```bash
# Writes are accepted for 600s, then silently dropped for 60s, repeatedly.
# "drop_writes" behaves like a power loss with a lost write cache:
# the I/O completes successfully and the data never lands.
SECTORS=$(blockdev --getsz /dev/sdb1)
sudo dmsetup create flakey-test --table \
  "0 $SECTORS flakey /dev/sdb1 0 600 60 1 drop_writes"
sudo mkfs.ext4 /dev/mapper/flakey-test
```

The `drop_writes` feature is the important one. The alternatives tell a different story: `error_writes` returns `EIO` (a *polite* failure your application can handle), `corrupt_bio_byte` flips a byte (good for checksum testing), and no feature at all just truncates the device (good for simulating a smaller disk). Real power loss is `drop_writes`, because real power loss is silent.

Run your database on the flakey device for ten minutes, kill it during a down window, remount, and see what the recovery path does. Two outcomes are acceptable: the database starts and the last committed transaction is present, or the database starts, reports lost transactions loudly, and is consistent. One outcome is not: the database starts silently with a torn page or a half-written WAL record. That third outcome is how people discover their `full_page_writes` setting is off during an incident instead of during a test.

```bash
sudo dmsetup suspend flakey-test
sudo dmsetup resume flakey-test
sudo dmsetup remove flakey-test
```

Clean up with `remove` when you are done, and never leave a flakey device in `/etc/fstab` on a machine you care about.

If you use this to test a filesystem rather than a database, pair it with a real integrity check afterwards — our [fsck, xfs_repair and btrfs check guide](../2026-06-01-linux-filesystem-integrity-check-fsck-xfs-repair-btrfs-guide/) covers which tool is authoritative for which filesystem and which ones can make things worse.

## Tool 3: pg_test_fsync — The Five Ways PostgreSQL Can Flush

PostgreSQL exposes `wal_sync_method` with five platform-dependent values, and the difference between them on a given filesystem is not something to guess. `pg_test_fsync` ships with PostgreSQL (so it is already installed on every database host you own) and measures each method for a few seconds.

```bash
sudo -u postgres pg_test_fsync -s 3 -f /var/lib/postgresql/18/main
```

Sample output shape (your numbers will differ — that is the entire point):

```text
Compare file sync methods using one 8kB write:
(in wal_sync_method preference order, except fdatasync is Linux's default)
        open_datasync                      1821.443 ops/sec
        fdatasync                          1794.006 ops/sec
        fsync                              1204.882 ops/sec
        fsync_writethrough                  not supported
        open_sync                          1103.517 ops/sec
```

Read it as: on this filesystem, `open_datasync` and `fdatasync` were roughly 50% faster than `fsync`, because `fsync` also pushes an inode metadata update that a WAL append does not need. On most Linux filesystems the default `fdatasync` is already the right answer; on some network filesystems the ranking inverts. The concrete rule: **pick the fastest method that is actually durable**, and re-run this after any storage migration. A tuning decision copied from a blog post about ext4 on local NVMe is not a tuning decision.

While you are on the host, confirm the settings that make fsync meaningful:

```sql
SHOW fsync;               -- must be on. off means "corrupt me".
SHOW full_page_writes;    -- must be on.
SHOW synchronous_commit;  -- on/remote_apply for money; off buys latency with durability.
SHOW wal_sync_method;     -- whatever pg_test_fsync says is fast AND durable
```

`synchronous_commit = off` is a legitimate setting for analytics or session data. It is not legitimate for a ledger: the server acknowledges the commit before the WAL is flushed, so a crash loses the last window of transactions (bounded roughly by `wal_writer_delay`, default 200 ms, but larger under write pressure). The performance win is real — often 2-3x on write-heavy transactions — which is exactly why it gets enabled by accident and discovered during a postmortem.

## Application-Level Durability: What Your Frameworks Actually Promise

The syscall layer is only half the story; your language runtime and database driver decide which call gets used and when.

**Python** — the stdlib gives you all three levels, and the directory fsync too:

```python
import os

path = "/var/lib/app/data.bin"
tmp = path + ".tmp"

fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
try:
    os.write(fd, payload)
    os.fdatasync(fd)          # data + size, skips mtime/atime
finally:
    os.close(fd)

os.replace(tmp, path)

dfd = os.open("/var/lib/app", os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(dfd)             # persist the rename
finally:
    os.close(dfd)
```

**Go** — `File.Sync()` maps to `fsync(2)`, so it is the strong version:

```go
f, err := os.OpenFile(tmp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0o644)
if err != nil { return err }
if _, err := f.Write(payload); err != nil { return err }
if err := f.Sync(); err != nil { return err }   // fsync
if err := f.Close(); err != nil { return err }
if err := os.Rename(tmp, path); err != nil { return err }

d, err := os.Open(filepath.Dir(path))
if err != nil { return err }
defer d.Close()
return d.Sync()                                  // persist the rename
```

**Rust** — `sync_data()` is `fdatasync`, `sync_all()` is `fsync`. Choosing `sync_data()` for an append-only log is a free win:

```rust
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::Path;

fn append_durable(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let mut f = OpenOptions::new().create(true).append(true).open(path)?;
    f.write_all(bytes)?;
    f.sync_data()?;      // fdatasync: no inode metadata flush
    Ok(())
}
```

**SQLite** — the defaults are safer than most people assume, and the "fast" settings are the dangerous ones:

```sql
PRAGMA journal_mode = WAL;      -- better concurrency
PRAGMA synchronous = FULL;      -- fsync on every commit (default, durable)
-- PRAGMA synchronous = NORMAL; -- WAL: durable against app crash, NOT against power loss
-- PRAGMA synchronous = OFF;    -- benchmark-only. Never in production.
```

WAL + `synchronous=NORMAL` is a reasonable choice for a cache or a session store. It is not reasonable for anything you would restore from backup after losing it.

## The Five Durability Traps That Actually Bite

1. **Testing durability on the wrong storage.** Local NVMe can complete an fsync in tens of microseconds; a network-attached cloud volume can take milliseconds. Same code, same filesystem, 50x different commit latency. Benchmark where you deploy.
2. **`sync_file_range()` in place of `fsync()`.** It is a writeback hint. It does not wait, it does not order metadata, and it will happily return before your data reaches the device.
3. **Forgetting the directory fsync after `rename()`.** File content durable, filename gone. Add the `O_DIRECTORY` fsync.
4. **Mount options that disable barriers.** `barrier=0`, `nobarrier`, or a hypervisor cache mode like `cache=unsafe` removes the flush entirely. Someone enabled it to make a benchmark look good; the bill arrives as a corrupted database.
5. **Trusting a RAID controller's write-back cache without a battery or capacitor.** A controller advertising write-back with no power-loss protection has the same failure mode as a lying drive, and it is much harder to detect because the drives themselves look honest.

One more, specific to containers: **`O_DIRECT` on tmpfs is silently ignored**, and tmpfs has no durability at all. A `--direct=1` fio run against `/dev/shm` measures nothing. The same is true of many overlay filesystems in ways that depend on the backing store — check what your container runtime actually mounted before you trust a benchmark.

## FAQ

### Does fsync() guarantee data is on physical media?

No. It guarantees the kernel issued a cache-flush command to the block device and the device reported completion. If the device has a volatile write cache that ignores or misreports flushes — some USB bridges, some RAID controllers, some virtual disks — the data can still be lost on power failure. `fsync()` plus a device that honors `FLUSH` is durability; `fsync()` alone is a request.

### Is fdatasync() faster than fsync(), and is it safe?

On ext4 and XFS, `fdatasync()` is usually measurably faster because it skips the inode metadata update that `fsync()` forces (mtime, atime). It is safe whenever you only need the file's *content and size* to survive — appending to a WAL or a log file is the canonical case. If you rely on metadata such as permissions or timestamps surviving, use `fsync()`.

### Why did my database lose the last transactions after a power cut?

Three usual causes, in order of frequency: `synchronous_commit = off` (PostgreSQL) or `PRAGMA synchronous = NORMAL` in WAL mode (SQLite), both of which acknowledge commits before the flush completes; a storage stack with a volatile cache that does not honor flushes; or an application-level write path that never called `fsync()` on the file or the parent directory at all.

### Can I disable the write cache to make fsync() honest?

Yes — `hdparm -W 0` on SATA, or disable the controller cache in firmware — but expect write throughput to collapse, often by an order of magnitude, because every write now waits for media. The better answer is a device with power-loss protection (enterprise SSD with capacitors, or a RAID controller with a battery/capacitor-backed cache) so the cache is honest by construction, not by configuration.

### How do I test whether my storage actually loses unflushed writes?

Use `dm-flakey` with the `drop_writes` feature to silently discard writes on a schedule, run your workload against the mapped device, then restart and check recovery. Pair it with a fio `--verify=crc32c` run to see exactly which blocks disappear. If your application notices and recovers, you are durable; if it starts cleanly with wrong data, you are not.

### Does the page cache affect durability testing?

Yes, heavily. Reads and writes hit the page cache by default, so a "durable" write can appear instant and a verification read can come from RAM instead of the device. Use `--direct=1` in fio, `O_DIRECT` in application code, or drop caches between phases — our [page cache inspection guide](../2026-05-23-linux-page-cache-inspection-pcstat-vmtouch-fincore-guide/) covers `pcstat`, `vmtouch` and `fincore` for proving what is actually resident.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "fsync() Is Not Durability: How Linux Storage Lies About Writes in 2026",
  "description": "fsync() returned 0 and your data still vanished. A hands-on guide to proving write durability with fio, dm-flakey and pg_test_fsync, plus the exact syscall semantics that decide whether a committed write survives a power cut.",
  "datePublished": "2026-11-22",
  "dateModified": "2026-11-22",
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
