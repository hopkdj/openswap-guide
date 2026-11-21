---
title: "df vs du vs duf vs dust vs gdu in 2026: Why Your Disk Numbers Never Agree"
date: "2026-11-21"
description: "df says 92% full, du says 61 GB used. Both are right. Here is how disk usage analyzers count space differently, and which tool to reach for on a 10 TB volume."
tags: ["linux", "storage", "cli-tools", "disk-usage", "sysadmin", "monitoring", "rust", "golang"]
draft: false
cover: "/img/screenshots/gdu-disk-usage-tui.jpg"
---

`df -h` says the volume is **92% full**. You run `du -sh /data` and it sums to **61 GB** on a 100 GB disk. You delete 20 GB of logs, `df` still says 89%. Somewhere in that gap are deleted-but-open files, reserved blocks, metadata, sparse files and hardlinks — and no single tool shows all of them.

Picking the right analyzer is not a matter of taste. `du` walks the tree with `stat()` on every inode and can take 40 minutes on a cold 10 TB volume. `dust` does the same walk but sorts and prunes as it goes. `gdu` gives you an interactive TUI where you can delete while you browse. `duc` builds a persistent index so repeat queries are instant. `duf` does not walk anything at all — it asks the kernel, which is why it agrees with `df` and disagrees with everything else.

Here is what each one actually measures, when to use it, and how to stop chasing phantom gigabytes.

## TL;DR: Which One Should You Install?

- **Replacing `df`?** Use `duf`. It is `df` with human-readable output, inode usage, and filesystem-type filtering in a single view. 15.4K stars, actively maintained.
- **"What is eating my disk right now"?** Use `dust`. Sorted, depth-limited, one screen, no interaction. Fastest path from question to answer.
- **Interactive exploration and deletion?** Use `gdu`. Arrow keys, `d` to delete, keyboard-driven, noticeably faster than `ncdu` on spinning disks and network mounts.
- **Repeated queries on a 10 TB volume?** Use `duc`. Index once, query forever — the only tool here with a persistent database.
- **Inside a script or cron job?** Use `du`/`df` from coreutils. Stable output, no dependencies, `-x` to stay on one filesystem.
- **Remember:** `du` and `df` measure different things. Neither is wrong. A 30 GB gap is usually deleted-but-open files, reserved blocks, or snapshots.

## The Five Tools, Side by Side

| Tool | Language | Stars | Last push | Method | Interactive | Inode view | Indexed |
|---|---|---|---|---|---|---|---|
| [`duf`](https://github.com/muesli/duf) | Go | 15,399 | 2026-11-15 | `statfs` per mount (no tree walk) | No | Yes | No |
| [`dust`](https://github.com/bootandy/dust) | Rust | 12,671 | 2026-11-19 | Tree walk, sorted output | No | No | No |
| [`gdu`](https://github.com/dundee/gdu) | Go | 6,215 | 2026-11-20 | Parallel tree walk + TUI | Yes | No | No |
| [`duc`](https://github.com/zevv/duc) | C | 721 | 2026-04-15 | Tree walk into on-disk index | Yes | No | **Yes** |
| `du` / `df` (coreutils) | C | — | — | Tree walk / `statfs` | No | Yes (`df -i`, `du --inodes`) | No |

![gdu interactive disk usage browser showing directory sizes](/img/screenshots/gdu-disk-usage-tui.jpg "gdu's TUI: sorted by size, keyboard navigation, delete in place — the fastest way to reclaim space interactively")

## Why `df` and `du` Disagree (the Gap Explained)

Before comparing tools, understand what each measures:

| Question | Answered by | What it counts |
|---|---|---|
| How much space does the filesystem have left? | `df`, `duf`, `statfs` | Allocated blocks minus reserved, per mount |
| How much do these files occupy? | `du`, `dust`, `gdu`, `duc` | Blocks referenced by reachable directory entries |
| How large is the file logically? | `ls -l`, `du --apparent-size` | Byte length, ignoring block rounding |
| How many inodes are free? | `df -i`, `du --inodes` | Inode table / allocation state |

The gap between `df` and `du` has six usual causes:

1. **Deleted files still held open.** A process with an open file descriptor keeps the blocks allocated after `unlink`. `df` counts them, `du` cannot see them. Find them with `sudo lsof +L1`.
2. **Reserved blocks.** ext4 reserves 5% for root by default. On a 4 TB volume that is 200 GB invisible to `du`. Check with `tune2fs -l /dev/sdX | grep "Reserved block count"`.
3. **Sparse files.** A 100 GB sparse database file may occupy 2 GB on disk. `du` reports 2 GB; `ls -l` reports 100 GB. Compare with `du -h --apparent-size` versus `du -h`.
4. **Hardlinks.** `du` counts a hardlinked inode once per traversal pass; multiple paths to the same inode inflate naive sums. Use `du -l` to count links separately when you need to.
5. **Snapshots and reflinks.** LVM, Btrfs and ZFS snapshots consume real blocks that no file in your tree references.
6. **Filesystem overhead.** Journal, inode tables, metadata chunks and CoW bookkeeping all consume `df` space and appear in no `du` output.

That is why "delete 20 GB, `df` barely moves" usually means the space went to deleted-but-open files or a snapshot — not that `df` is lying.

## duf: The `df` Replacement

`duf` does not walk the filesystem tree at all. It calls `statfs` on each mount, which is why it returns in **milliseconds** on a volume where `du` takes 40 minutes, and why its numbers match `df` exactly.

```bash
# Debian 12+ / Ubuntu 22.04+
sudo apt install duf

# Fedora / Arch / macOS
sudo dnf install duf
sudo pacman -S duf
brew install duf

# Only local filesystems, human-readable, with inode usage
duf --only local
```

Typical output, which is the point of the tool — bytes, usage percentage and inode usage on one screen per mount:

```text
╭──────────────────────────────────────────────────────────────────────╮
│ 2 local devices                                                     │
├────────────┬────────┬────────┬────────┬────────┬─────────┬───────────┤
│ Mounted on │  Size  │  Used  │  Avail │ Use %  │ Type    │ Inodes    │
├────────────┼────────┼────────┼────────┼────────┼─────────┼───────────┤
│ /          │  98G   │  61G   │  32G   │  66%   │ ext4    │ 12% used  │
│ /data      │ 3.6T   │ 3.4T   │ 210G   │  94%   │ xfs     │  3% used  │
╰────────────┴────────┴────────┴────────┴────────┴─────────┴───────────╯
```

Use `duf` for the "is this volume actually full" question and for inode percentage at a glance. Do not use it to find what is large — it has no file-level data whatsoever.

## dust: The One-Shot Answer

`dust` gives you the top consumers, sorted, in one screen, with no interaction. It is the tool to run first on an unfamiliar server.

```bash
# Install (binary name is du-dust, command is dust)
cargo install du-dust
sudo dnf install du-dust
brew install dust
sudo snap install dust

# Top 15 directories, two levels deep, biggest last
dust -d 2 -n 15 /var

# Reverse order: biggest first (my default)
dust -r -n 20 /var/log

# Exclude noise, useful on a Kubernetes node
dust -X /var/lib/docker/overlay2 -d 2 /var
```

What separates `dust` from `du | sort -rn | head` is that it does not sort the entire tree in memory — it prunes as it walks, so it stays usable on filesystems with tens of millions of files where `du` output would be hundreds of megabytes of pipe data.

Its blind spot: it is byte-oriented. There is no inode mode, so it will not help with the "disk is full of a million tiny files" class of incident — for that you need `du --inodes`, which we cover in the [inode exhaustion diagnosis guide](../2026-11-21-inode-exhaustion-ext4-xfs-btrfs-diagnosis-guide/).

## gdu: Interactive, Parallel, and Fast

`gdu` walks the tree in parallel goroutines and renders an interactive TUI. On a spinning disk or an NFS mount it is noticeably more responsive than single-threaded walkers, and it lets you delete while browsing — which is the workflow most people actually want at 2 a.m.

```bash
# Grab the prebuilt binary for your architecture from the releases page,
# or use your distro package if available
gdu --version

# Interactive browse of a directory
gdu /var

# Non-interactive report (good for scripts and Tickets)
gdu -n -p /var | head -20

# Maximum depth, useful when the tree is enormous
gdu -d 2 /srv
```

Keys that matter: `↑`/`↓` move, `Enter` descends, `d` deletes the selected entry (with confirmation), `n` sorts by name, `s` sorts by size, `q` quits. Because deletion is a single keypress away, run it as a non-root user first and escalate only when you have found the target.

Trade-off: `gdu` holds directory metadata in memory for the tree it is scanning. On a volume with 50 million files, that is gigabytes of RAM. Scope it to a subtree rather than `/`.

## duc: Index Once, Query Forever

`duc` is the only tool here with a persistent on-disk index. On a 10 TB archive that takes 40 minutes to walk, this changes the workflow completely: index overnight, then answer questions instantly all week.

```bash
# Build (Ubuntu/Debian package)
sudo apt install duc

# Index a large volume once — this is the expensive step
sudo duc index /data --database /var/lib/duc/data.db

# Instant queries afterwards, no re-walk
duc ls -Fg --database /var/lib/duc/data.db /data | head -20
duc ls -Fg --database /var/lib/duc/data.db /data/postgres

# Interactive browser over the index
duc ui --database /var/lib/duc/data.db /data

# Graphical output (SVG/PNG sunburst) for reports
duc graph --database /var/lib/duc/data.db -o /tmp/usage.png /data
```

The catch is staleness: the index reflects the filesystem at indexing time. Schedule a nightly `duc index` and treat the output as "where space was", not "where space is". For incident response on the same day, run a live tool.

## du: Still the Right Answer in Scripts

GNU coreutils `du` remains the correct choice for automation because its output is stable, it is present on every system, and it has no runtime dependencies:

```bash
# Top-level usage, staying on one filesystem, human-readable
du -xhd1 /var 2>/dev/null | sort -h | tail -15

# Apparent size vs actual disk usage (finds sparse files)
du -sh --apparent-size /var/lib/postgresql
du -sh /var/lib/postgresql

# Count inodes, not bytes
du --inodes -x -d1 /var 2>/dev/null | sort -n | tail -10

# Find files larger than 1 GB anywhere under /data
find /data -xdev -type f -size +1G -printf '%s\t%p\n' | sort -n | tail -20
```

Two flags prevent most production mistakes: `-x` (never cross into another mounted filesystem, which is how `/proc` and container mounts turn a 5-minute scan into a 2-hour one) and `2>/dev/null` (permission errors on a rootless scan otherwise flood your output).

## Choosing Under Pressure

| Situation | Tool | Command |
|---|---|---|
| "Is the disk really full?" | `duf` | `duf --only local` |
| "What is big, right now, fast?" | `dust` | `dust -r -n 20 /` |
| "Walk me through it so I can delete" | `gdu` | `gdu /var` |
| "Same question, every day, 10 TB volume" | `duc` | `duc index` + `duc ls -Fg` |
| "Script it into monitoring" | `du`/`df` | `du -xhd1`, `df -i` |
| "df and du disagree by 30 GB" | `lsof` | `sudo lsof +L1` |
| "Out of inodes, not bytes" | `du --inodes` | `du --inodes -x -d1 /` |
| "Per-tenant accounting" | `du` + quotas | see [disk quota management](../2026-05-22-self-hosted-linux-disk-quota-management-quota-quotatool-webmin-guide/) |

## How Fast Are They, Really?

Do not trust published benchmark numbers — page cache state, filesystem type and SSD vs HDD change the result by an order of magnitude. Measure on your own volume:

```bash
# Cold-cache comparison; drop caches first for a fair test
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

time du -sh /data
time dust -d 1 -n 10 /data > /dev/null
time gdu -n -p /data > /dev/null
time duc index /data --database /tmp/bench.db

# Second run is warm-cache — this is the number that matters day to day
time du -sh /data
```

Expect `gdu` to lead on warm cache thanks to parallel walking, `du` to be competitive on small trees, and `duc` to lose badly on the first run and win every subsequent query. `duf` finishes before the others start, because it never touches a single file.

## Pitfalls That Waste Afternoons

- **Without `sudo`, `du` silently under-reports.** It skips unreadable directories, so a root-owned subtree disappears from the total. Always compare a rootless scan against a `sudo` scan once, so you know the size of the blind spot.
- **Never run `du` on `/` without `-x`.** It walks into `/proc`, `/sys`, container overlays and network mounts — slow, noisy, and the totals are meaningless.
- **`dust` and `gdu` do not respect `df` semantics.** They report blocks referenced by files, so a volume can be 94% full by `duf` and show 60 GB of "usage" by `dust`. That is not a bug; it is the deleted-file gap.
- **Deleting through a TUI is permanent.** `gdu`'s `d` key does not use a trash directory. Verify path context before pressing it, especially when the TUI is scoped at `/`.
- **On Btrfs and ZFS, every number is approximate.** Compression, reflinks and snapshots mean logical size, physical size and shared extents all differ. Prefer `btrfs filesystem usage -T` or `zfs list -o space` for capacity decisions.
- **`duc` indexes are not portable across machines** in a meaningful way, and a stale index will confidently show deleted data. Automate reindexing or you will chase files that no longer exist.
- **Watch out for the 32-bit inode/NFS case.** On NFS mounts, `du` can report sizes wildly different from the server if the mount lacks `noatime` or if sparse files are involved. Cross-check on the server when the numbers matter.

If your volumes are filling because of fragmentation rather than genuine data growth, our [defragmentation guide for ext4, XFS and Btrfs](../2026-11-21-filesystem-fragmentation-ext4-xfs-btrfs-defrag-guide/) covers when that is actually worth doing — usually it is not, and the space is simply in use.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "df vs du vs duf vs dust vs gdu in 2026: Why Your Disk Numbers Never Agree",
  "description": "df says 92% full, du says 61 GB used. Both are right. How disk usage analyzers count space differently, and which tool to reach for on a 10 TB volume.",
  "datePublished": "2026-11-21",
  "dateModified": "2026-11-21",
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

### Why does `df` show the disk as full when `du` reports much less usage?

`df` asks the kernel for filesystem-wide allocation, which includes deleted files still held open by a process, reserved blocks (5% on ext4 by default), journal and metadata overhead, and snapshot or reflink extents. `du` only sums blocks reachable from directory entries. The most common culprit is a deleted-but-open file — find it with `sudo lsof +L1` and restart the process holding it, and the space returns immediately.

### Is `duf` a replacement for `df` or for `du`?

For `df`. `duf` calls `statfs` for every mount point, so it reports the same capacity and usage figures as `df`, with a readable table and inode usage included. It never walks directories, so it cannot tell you which file or directory is large. Use `dust`, `gdu` or `duc` for that question.

### Which disk usage tool is fastest on a very large filesystem?

For a single scan, `gdu` is usually fastest on warm cache because it walks directories in parallel; `dust` is competitive and prunes during the walk so its memory footprint stays small. For repeated questions on multi-terabyte volumes, `duc` wins overall because it indexes once and answers subsequent queries from the database in milliseconds. Measure on your own hardware — filesystem type and cache state dominate the result.

### How do I find large files rather than large directories?

Use `find` with a size predicate and print the size, then sort: `find /data -xdev -type f -size +1G -printf '%s\t%p\n' | sort -n | tail -20`. Analyzers that work on directories (`dust`, `gdu`, `duc`) show you where to look; `find` tells you the exact files. Add `-xdev` so the search never crosses onto another mounted filesystem.

### Can these tools count inodes instead of bytes?

`du --inodes` (coreutils 8.22 and later) counts directory entries rather than blocks, and `df -i` reports filesystem-wide inode allocation. `duf` displays inode usage per mount. `dust`, `gdu` and `duc` are byte-oriented and have no inode mode, so for an inode exhaustion incident start with `df -i` and `du --inodes`.

### Why does deleting files not free space on my Btrfs or ZFS volume?

Because both filesystems are copy-on-write: deleting a file frees extents only when no snapshot references them. Until you destroy the snapshots holding those blocks, `df` will keep reporting the space as used. Check with `btrfs subvolume list -s /` or `zfs list -t snapshot -o name,used` before assuming the delete failed.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
