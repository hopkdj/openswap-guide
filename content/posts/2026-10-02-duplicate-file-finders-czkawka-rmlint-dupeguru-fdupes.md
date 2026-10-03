---
title: "Czkawka vs rmlint vs dupeGuru vs fdupes in 2026: Which Deduplicator Should You Actually Run?"
date: "2026-10-02"
tags: ["storage", "file-management", "deduplication", "linux", "self-hosted"]
draft: false
cover: "/img/screenshots/rmlint-gui-editor.jpg"
---

Your 4 TB media drive does not hold 4 TB of data. After a decade of camera card dumps, three "final_final" project folders, and a photo library that got re-imported twice, 20–35% of the bytes on a typical homelab disk are the same bits stored more than once. On a 4 TB SMR drive that is 800 GB of wasted spindle — and on a cloud volume it is a line item you pay for every single month.

The fix is not a bigger drive. It is a duplicate finder that is fast enough to run weekly, and careful enough that it never deletes the wrong copy. The four serious contenders in 2026 — **Czkawka, rmlint, dupeGuru and fdupes** — take wildly different approaches to the same problem, and the difference matters most in the one place you cannot afford a mistake: the delete step.

## TL;DR: Quick Verdict

**Pick Czkawka if** you want one Rust binary that finds duplicate files, similar images, broken symlinks, big files, empty folders and near-duplicate music in a single tool — and you want a GUI that a non-sysadmin can use. **Pick rmlint if** you are on a headless server and want the tool to write a reviewable shell script instead of deleting anything itself. **Pick dupeGuru if** your duplicates are *near*-duplicates: re-encoded music, resized photos, and documents that differ by a stray space. **Pick fdupes if** the drive is a rescue-target on a live USB and you need a 200 KB binary that builds in one command with no runtime dependencies.

The short version: **rmlint for servers, Czkawka for workstations, dupeGuru for media libraries, fdupes for emergencies.**

## The Contenders at a Glance

| | **Czkawka** | **rmlint** | **dupeGuru** | **fdupes** |
|---|---|---|---|---|
| **Stars (Oct 2026)** | 33,848 | 2,431 | 7,880 | 3,017 |
| **Language** | Rust | C | Python + Qt5 | C |
| **License** | MIT (CLI/GTK); Krokiet & Cedinia are GPL-3.0-only | GPL-3.0 | GPL-3.0 | Permissive (see repo LICENSE) |
| **Interface** | Krokiet GUI, GTK GUI, CLI, Android | CLI + Shredder GUI | Qt GUI, CLI mode | CLI only |
| **Semantic matching** | Duplicates, similar images, similar music, big files, empty files/folders, broken symlinks | Duplicates, duplicate folders, empty files/dirs, nonstripped binaries, bad links | Duplicates **plus fuzzy matching** for pictures, music and documents | Byte-identical duplicates only |
| **Delete model** | Built-in delete / move / hardlink modes | Writes a shell script you read before running | Interactive GUI delete + CLI | `--delete` with prompt |
| **Best for** | All-round cleanup on a workstation | Unattended scans on a headless box | Media and document libraries | Minimal environments |

## Which Tool for Which Job

| Use case | Recommended | Why |
|---|---|---|
| Weekly cleanup of a 4 TB homelab array | **rmlint** | Generates a script; you review and dry-run before anything is removed |
| Desktop user who wants to see duplicates before deleting | **Czkawka / Krokiet** | Fast GUI, multi-category scanning, no terminal required |
| 60,000 MP3 files with different bitrates | **dupeGuru** | Fuzzy matching finds re-encodes that hashing never will |
| Photo library with resized exports | **dupeGuru** (Picture mode) or Czkawka's similar-images scan | Both tolerate scaling and re-compression |
| Live USB / rescue shell with no package manager | **fdupes** | Tiny C program, zero dependencies, builds with `make` |
| Deduplicating a backup target you must not touch | **rmlint** with `--keep-hardlinked` | Refuses to break hardlinks that hold the backup together |

## Czkawka: The Rust Multitool

Czkawka (Polish for "hiccup") is the most popular entry on this list by a wide margin — **33,848 stars**, last pushed **2026-09-16**. It started as a GTK duplicate finder and grew into a small suite: duplicate files, similar images, similar music, big files, empty files, empty folders, temporary files and broken symlinks. There are now four front ends sharing one Rust core — the legacy GTK GUI, the **Krokiet** Slint GUI, the CLI, and an Android build (`cedinia`).

![Czkawka Krokiet GUI scanning a directory tree](/img/screenshots/czkawka-krokiet.jpg "Czkawka Krokiet interface")

The licensing is worth knowing before you ship it: the **core, the GTK GUI and the CLI are MIT**, but **Krokiet and Cedinia are GPL-3.0-only** because of Slint's license terms. If you are embedding Czkawka in a product, use `czkawka_cli`, not Krokiet.

Install the CLI from the repo:

```bash
# Linux build dependencies for the extended codecs
sudo apt install ffmpeg libraw-dev libheif-dev libavif-dev libdav1d-dev

# build the CLI from source
cargo run --release --bin czkawka_cli
```

Real invocations, straight from the project's CLI documentation:

```bash
# duplicates under /home/rafal, skipping the Obrazy folder, ignoring 7z/rar/IMAGE
# files, using content hashing, writing results, and keeping the oldest file
czkawka dup -d /home/rafal -e /home/rafal/Obrazy -m 25 -x 7z rar IMAGE \
  -s hash -f results.txt -D aeo

# empty folders and empty files
czkawka empty-folders -d /home/rafal/rr /home/gateway -f results.txt
czkawka empty-files -d /home/rafal /home/szczekacz -e /home/rafal/Pulpit -R -f results.txt

# big files over 25 MB, excluding a directory
czkawka big -d /home/rafal/ /home/piszczal -e /home/rafal/Roman -n 25 -x VIDEO -f results.txt

# broken symlinks
czkawka symlinks -d /home/kicikici/ /home/szczek -e /home/kicikici/jestempsem -x jpg -f results.txt
```

Every sub-tool has its own help page — `czkawka_cli --help` lists them, and `czkawka_cli dup --help` documents the parameters for one tool. The `-D` flag carries the **delete-safety policy** (keep oldest, newest, shortest path, case-sensitive first, and so on), and that single flag is the difference between a clean array and a very bad afternoon.

**Verdict:** if you own exactly one deduplication tool, own this one. The breadth (similar images and music, not just identical bytes) is unmatched at this star count, and the CLI is scriptable enough for cron.

## rmlint: Deduplication That Refuses to Delete Anything

rmlint is the opposite philosophy, and for servers it is the right one. It is a **C implementation under GPL-3.0** with **2,431 stars**, and it was pushed **2026-10-01** — one of the most actively maintained tools in this comparison. Its killer feature is that it does not delete. By default it writes out `rmlint.sh`, a shell script containing one `handle_*` function per file category, which you read, dry-run, and only then execute.

The GUI (called **Shredder**, shipped in the same repository as `docs/_static/gui_editor.png`) is literally a script reviewer with a search box, a syntax-highlighted script pane, and a warning panel between you and the destructive button:

```bash
rmlint [TARGET_DIR_OR_FILES ...] [//] [TAGGED_TARGET_DIR_OR_FILES ...] [-] [OPTIONS]
```

The options that matter in practice, taken from the project's man page:

```bash
# default behaviour: write rmlint.sh + pretty + summary + JSON output
rmlint /mnt/archive

# only duplicate files and duplicate directories
rmlint -T "df,dd" /mnt/archive

# everything EXCEPT duplicate files and directories
rmlint -T "all -df -dd" /mnt/archive

# stream JSON to stdout, or add a CSV file alongside the shell script
rmlint -o json /mnt/archive
rmlint -O csv:/tmp/rmlint.csv /mnt/archive

# hardlink duplicates instead of deleting them (same filesystem only)
rmlint -c sh:link /mnt/archive

# find only zero-byte files
rmlint -T df --size 0 /mnt/archive

# deduplicate all executables on $PATH
rmlint -z rx $(echo $PATH | tr ":" " ")
```

The hardlink flags deserve a paragraph of their own. rmlint treats hardlinked files as duplicates **by default** (`--hardlinked`). That is a footgun on a backup volume built from hardlinks, where "duplicate" copies are actually the same inode preserving history. Pass `--keep-hardlinked` and rmlint will leave any file hardlinked to an original alone; pass `-L`/`--no-hardlinked` and only one file of a hardlinked set is reported. Choosing the wrong one on a snapshot-style backup can silently collapse your restore points.

**Verdict:** the default choice for servers, NAS boxes and backup targets. The script-review workflow is the single best safety mechanism in this entire comparison, and the `-c sh:link` mode gives you space back without losing a single filename.

## dupeGuru: Built for Fuzzy, Not Identical

dupeGuru is a **Python + Qt5 application under GPL-3.0** with **7,880 stars**, last pushed **2026-09-07**. Unlike the other three, it does not stop at byte-identical files. Its modes match *similar* content: music files by tag similarity, pictures by visual difference (with adjustable blur/threshold), and documents (PDF, Word, ODF, EPUB, text) by content similarity.

That matters because the most expensive duplicates in a home library are not identical at all. The same album ripped at 192 kbps and 320 kbps is two files with different hashes. A 4000 px JPEG and its 1600 px export are two files with different hashes. A duplicate finder that only compares bytes will report zero duplicates on a library that is 30% redundant.

Because it is Python, installation is from source:

```bash
# distro dependencies (Debian/Ubuntu naming)
sudo apt install python3-pyqt5 python3-pyqt5-dev-tools python3-dev python3-setuptools

# source build
python3 -m venv --system-site-packages ./env
pip install -r requirements.txt -r requirements-extra.txt
python build.py --clean
python package.py
```

There is a CLI mode, but dupeGuru's real value is interactive: you want to *look* at the fuzzy matches before trusting them, because a 90% similarity score can absolutely be two different photos of the same sunset. Documentation lives at `dupeguru.voltaicideas.net`.

**Verdict:** the only tool here worth running against a music or photo library you actually care about. Do not run it headless without reviewing results first — fuzzy matching means false positives are a design feature, not a bug.

## fdupes: The One You Build on a Rescue USB

fdupes is the oldest and smallest tool in this group: **3,017 stars**, plain C, last touched **2026-04-14**. It does one thing — find byte-identical files — and it does it with no runtime dependencies, which is why it is on every rescue image and in every distro's base repository.

Its flag set is tiny and worth memorising:

```bash
fdupes -r -S -m /data        # recurse, show size of each set, print a summary
fdupes -r -d /data           # prompt for which copy to keep, delete the rest
fdupes -r -d -N /data        # keep the first file in each set, delete silently
fdupes -r -d -P /data        # line-based prompt (old behaviour)
fdupes -1 /data              # print matches on one line each
```

The README's own advice is worth repeating verbatim: when using `-d` or `--delete`, *take care to insure against* losing data — there is no undo. `-N`/`--noprompt` in particular deletes without confirmation, so it belongs in a script only after you have dry-run the same command without `-d` and eyeballed the output.

**Verdict:** keep it in your toolkit for the day a filesystem will not mount on a modern machine and you need an answer from a BusyBox shell. As a weekly driver, it lacks the safety rails and the semantic matching of the other three.

## Pitfalls That Bite Everyone Once

**1. Deduplication is pointless on copy-on-write filesystems that already do it.** ZFS, Btrfs, XFS and APFS with reflinks store identical blocks once automatically. If you are running ZFS with `dedup=on` or Btrfs with reflink copies, a duplicate finder mostly harvests directory entries, not bytes. Check `du --apparent-size` versus `du` before believing your "savings".

**2. Never run a delete mode before a read-only pass.** Every tool here can produce a report first. Run the scan, write it to a file, and diff two runs a week apart. Files that appear and disappear between runs are usually application caches, not clutter.

**3. Partial hashing lies about tiny differences.** Most fast finders compare file size and a prefix or suffix sample before doing a full hash. That is a performance win and a correctness risk when two files share a size and a header but differ in a middle block. rmlint's cautious path and fdupes' full comparison are the conservative end; Czkawka's `-s hash` content mode is the middle ground. If you want to go deeper on the primitives themselves and how they collide in practice, our [hash function libraries comparison](../2026-06-19-hash-function-libraries-xxhash-blake3-murmurhash-cityhash-farmhash/) covers xxHash, BLAKE3 and the rest.

**4. Hardlinks and symlinks are not duplicates.** They are the same data. Deleting one "copy" of a hardlink pair frees nothing; deleting the *last* link destroys the file. This is the single most common way people break a backup set with a dedup tool — use `--keep-hardlinked` in rmlint, and in Czkawka exclude the backup target entirely. Before trusting any backup chain that survived a cleanup, run the checks in our [backup verification and integrity testing guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/).

**5. Do not deduplicate across mount points you do not control.** `-x`/`-e`/`--crossdev` style exclusions exist in all four tools. Running a scan that crosses into a network share can hash terabytes over SMB and produce a script whose paths no longer exist by the time you run it.

**6. An unread script is a loaded gun.** This is rmlint's whole design thesis and it applies to every tool: if the tool offers a dry-run flag, use it, then read the generated script. On a 4 TB array the difference between `handle_emptydir` and `handle_duplicate` is often the difference between a tidy filesystem and a missing media library. If you have already learned that the hard way, our [Linux data recovery toolkit guide](../2026-05-25-linux-data-recovery-tools-ddrescue-testdisk-photorec-guide/) is where to start.

## Frequently Asked Questions

**Is Czkawka better than rmlint?**
They solve different problems. Czkawka finds more *kinds* of waste (similar images, similar music, big files, empty folders) and ships a GUI. rmlint is better for unattended servers because it never deletes by itself — it emits a reviewable `rmlint.sh`. If you are not sure, start with rmlint on servers and Czkawka on desktops.

**Can I safely run a duplicate finder on a ZFS or Btrfs pool?**
Yes, but understand what you will get. Both filesystems already share identical blocks (ZFS dedup, Btrfs reflinks), so a byte-level finder may report far less reclaimable space than the raw duplicate count suggests. The real wins on those filesystems are empty directories, orphaned hardlinks and near-duplicates that hashing cannot see.

**How do I find duplicate photos that are not identical?**
Use a tool with perceptual or fuzzy matching: Czkawka's similar-images scan, or dupeGuru's Picture mode with a difference threshold. Both hash visual features rather than bytes, so a resized or re-compressed export still matches the original. Always review the results before deleting — similar is not the same as identical.

**Will deduplicating with hardlinks break my backups?**
It can. Turning duplicates into hardlinks means a later edit to one "copy" changes every link, and a backup tool that does not preserve hardlinks will store full copies anyway. rmlint's `--keep-hardlinked` exists precisely for backup volumes; on snapshot-style stores like ZFS or Btrfs, prefer deleting or reflinking over hardlinking.

**How often should I run a deduplication pass?**
Weekly on a writer-heavy share, monthly on an archive drive. Running more often than you add data mostly wastes I/O. The efficient pattern is a nightly read-only scan that writes a report, plus a manual review-and-apply step once the report stops changing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Czkawka vs rmlint vs dupeGuru vs fdupes in 2026: Which Deduplicator Should You Actually Run?",
  "description": "Hands-on comparison of Czkawka, rmlint, dupeGuru and fdupes for finding and removing duplicate files in 2026, including real CLI examples, delete-safety models, hardlink caveats and filesystem-specific pitfalls.",
  "datePublished": "2026-10-02",
  "dateModified": "2026-10-02",
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
