---
title: "Archive Libraries in 2026: libarchive vs SharpCompress vs Commons Compress vs archiver"
date: "2026-09-27"
tags: ["developer-tools", "libraries", "archives", "compression", "backend"]
draft: false
---

Every service eventually has to accept a file the user controls. The moment that file is a `.zip` — a theme upload, a data import, a log bundle from a customer — you have two options: shell out to `tar`/`unzip` and inherit an argument-injection bug plus a process-per-request cost, or use a real archive library and handle the format's edge cases deliberately.

The edge cases are not academic. Zip has three generations of filename encoding, a 64-bit extension most people forget, and a path traversal footgun that keeps producing CVEs a decade after it was first named. Tar has sparse files, hardlinks and a header checksum. 7z and RAR are not streamable at all.

This comparison covers the archive libraries that production code actually uses in 2026, with live repository data, format coverage taken from each project's own supported-formats documentation, and code samples pulled from their repositories.

## Quick Verdict (TL;DR)

- **Polyglot server / you need everything**: **`libarchive`** — the widest format coverage by far, with bindings for Python, Rust, Ruby, PHP, Go and .NET.
- **.NET**: **`SharpCompress`** — pure managed C#, no native binaries, forward-only reading over non-seekable streams (which is what you want for downloads), and async everywhere.
- **JVM**: **Apache Commons Compress** — the boring, correct choice; streaming APIs and the widest compressor set in Java.
- **Node.js**: **`archiver`** to *write* archives and **`yauzl`** to *read* them. Do not use one library for both jobs; the read/write models are different.
- **Rust**: **`zip2`** (the maintained `zip` crate) for random access, **`tar-rs`** for tar streams.
- **Python**: the standard library's `zipfile`/`tarfile` cover zip and tar; reach for `libarchive-c` when you must open 7z, RAR or ISO.

The single most important decision is not the library — it is whether you can extract **streaming** or need **random access**. That choice eliminates half the options before you benchmark anything.

## Comparison Table (Live Repository Data, September 2026)

| Library | Language | Stars | Last push | Formats | Access model | License |
|---|---|---|---|---|---|---|
| [`libarchive/libarchive`](https://github.com/libarchive/libarchive) | C (+ bindings) | 3624 | 2026-09-27 | tar, zip, 7z, iso9660, cpio, xar, rar (read), ar, mtree, lha | streaming read/write | BSD-2-Clause |
| [`adamhathcock/sharpcompress`](https://github.com/adamhathcock/sharpcompress) | C# / .NET | 2586 | 2026-09-24 | zip, tar, gzip, bzip2, lzip, xz, zstd, 7z (read/write subset); rar, arj, ace, lzw (read) | forward-only **and** random access | MIT |
| [`apache/commons-compress`](https://github.com/apache/commons-compress) | Java | 408 | 2026-09-24 | ar, arj, cpio, dump, tar, zip, 7z, gzip, bzip2, xz, lzma, snappy, zstd, brotli | streaming | Apache-2.0 |
| [`archiverjs/node-archiver`](https://github.com/archiverjs/node-archiver) | JavaScript | 2977 | 2026-09-23 | zip, tar (gzip/bzip2 via plugins) — **write only** | streaming write | MIT |
| [`thejoshwolfe/yauzl`](https://github.com/thejoshwolfe/yauzl) | JavaScript | 825 | 2026-06-07 | zip — **read only** | lazy, streaming read | MIT |
| [`alexcrichton/tar-rs`](https://github.com/alexcrichton/tar-rs) | Rust | 739 | 2026-09-21 | tar (compressors layered separately) | streaming | MIT / Apache-2.0 |
| [`zip-rs/zip2`](https://github.com/zip-rs/zip2) | Rust | 353 | 2026-09-26 | zip | random access + streaming | MIT |

Note the shape of the ecosystem: the two most-starred entries in JavaScript are **single-purpose**. `archiver` cannot read. `yauzl` cannot write. Teams that pick one and expect both end up adding the other anyway.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Use | Why |
|---|---|---|
| Extract any customer-supplied archive format | `libarchive` | Handles tar/zip/7z/iso/xar/cpio/rar with one API; battle-tested C core |
| .NET service streaming an upload straight to disk | `SharpCompress` | Non-seekable stream support is its headline feature; async extraction included |
| .NET, reading zip entries by name | `SharpCompress` (random access) or `System.IO.Compression` for plain zip | Full `ZipArchive` API without native dependencies |
| Java build server, artifact unpacking | Commons Compress | `ArchiveStreamFactory` detects the format from the stream itself |
| Node, producing a downloadable zip | `archiver` | Streaming write API; no buffering of the whole archive in memory |
| Node, parsing an uploaded zip | `yauzl` | Lazy entry iteration keeps memory flat for large archives |
| Rust CLI that inspects an existing .tar.gz | `tar-rs` + `flate2` | Stream-based, composes cleanly with the compression crates |
| Rust service writing per-file entries | `zip2` | Random-access writes, optional AES/zstd/deflate64 features |
| You need AES-encrypted zip output | `zip2` (feature `aes-crypto`) or `7z` via libarchive | Legacy ZipCrypto is broken and should not be used for new data |
| You only ever handle `.tar.gz` on Linux | system `tar` binary | It is right there; just never interpolate user input into the command line |

## libarchive — The Widest Net, and the Simplest Mental Model

`libarchive` is the engine inside `bsdtar`, macOS's `tar`, and a long list of package managers. Its architecture is worth understanding even if you never write C against it: a **read archive object** is paired with **format filters** and **compression filters**, so the same loop handles `foo.tar.xz` and `bar.zip` without branching.

Its repository ships a public-domain, single-file extraction example (`examples/untar.c`) whose own header documents the build line:

```bash
# From the header comment of examples/untar.c in the libarchive repository
gcc -static -Wall -o untar untar.c -larchive
strip untar
# Linux users will usually also need -D_FILE_OFFSET_BITS=64
```

That example is deliberately minimal, and its header explains the trade-off it makes: it uses the uid/gid recorded in the archive rather than doing name lookups, because enabling `archive_write_disk_set_standard_lookup()` can add hundreds of kilobytes to a static binary by pulling in password/NSS/LDAP machinery.

In day-to-day work the CLI is more useful than the C API:

```bash
# Read any supported container without caring which one it is
bsdtar -tf bundle.zip
bsdtar -xf upload.7z -C /srv/import

# Write an archive with an explicit format and filter set
bsdtar --format=zip -cf out.zip dir/
bsdtar --format=tar --zstd -cf out.tar.zst dir/
```

**Verdict:** if you accept arbitrary archive formats from users, `libarchive` is the risk-minimising choice — you get one hardened code path instead of five half-maintained ones. Bind it rather than reimplementing it.

## SharpCompress — The .NET Answer for Non-Seekable Streams

SharpCompress describes itself as a pure C# library that can "unrar, un7zip, unzip, untar, unbzip2, ungzip, unlzip, unxz, unzstd, unarc, unarj, unace, and unlzw with forward-only reading and file random access APIs," with write support for zip, tar, bzip2, gzip, lzip, zstd streams and 7zip archives. Its stated major feature is exactly the case that breaks naive implementations: **non-seekable streams**, so a download can be processed on the fly without buffering to disk first.

```bash
dotnet add package SharpCompress
```

The static entry points come straight from `ArchiveFactory` in the repository:

```csharp
using SharpCompress.Archives;

// Open by path, FileInfo, or Stream — the Stream overload is the non-seekable one
using var archive = ArchiveFactory.OpenArchive(uploadStream);

// Extract every entry into a target directory
archive.WriteToDirectory("/srv/import");

// Detect whether a blob is an archive before you do anything else
if (ArchiveFactory.IsArchive(path, out var type))
    Console.WriteLine($"Detected: {type}");
```

`IsArchive`/`IsArchiveAsync` overloads accept a path, `FileInfo` or `Stream` and return the detected `ArchiveType`, which is precisely the check you want before handing bytes to a parser. Newer releases also expose a `Providers` property on `ReaderOptions`/`WriterOptions` (with `WithProviders(...)` extensions) so you can substitute the compression backend while keeping the same reader, writer and archive APIs.

The README's own format recommendations are refreshingly opinionated and worth quoting: prefer **GZip/BZip2/LZip** for long-term archival because simple formats stream well; treat **zip** as "hap-hazard" due to header variation; avoid **RAR** (proprietary, closed codec); and note that **7z does not support streamable formats** while **XZ has known limitations** — with tar+LZip recommended instead for LZMA-based compression. **Zstandard** is called out as the format that streams well with a tunable speed/ratio trade-off.

**Verdict:** for .NET, this is the library to reach for when the word "stream" appears in your requirements.

## Apache Commons Compress — The JVM Workhorse

Commons Compress is the reference implementation for a long list of formats on the JVM: ar, arj, cpio, dump, tar, zip and 7z archives plus gzip, bzip2, xz, lzma, snappy, zstd and brotli compressors. The API is stream-oriented, and the repository's own `archivers.examples` package (`Archiver`, and the format-specific `SevenZOutputFile` usage) shows the intended pattern: build an `ArchiveOutputStream` from an `ArchiveStreamFactory`, walk the file tree with a `SimpleFileVisitor`, and copy entries.

```xml
<dependency>
  <groupId>org.apache.commons</groupId>
  <artifactId>commons-compress</artifactId>
</dependency>
```

```java
import org.apache.commons.compress.archivers.ArchiveOutputStream;
import org.apache.commons.compress.archivers.ArchiveStreamFactory;
import org.apache.commons.compress.archivers.sevenz.SevenZOutputFile;

// Format is selected by name; the factory keeps the call sites uniform
ArchiveOutputStream out =
    new ArchiveStreamFactory().createArchiveOutputStream("tar", outputStream);
```

Because format detection happens at stream level, a single import path can serve `application/zip`, `application/x-tar` and `application/x-7z-compressed` uploads without a `switch` over content types — with `SeekableByteChannel` support for the parts of the API (like 7z) that cannot work purely forward.

**Verdict:** the correct Java choice, and the one with the fewest surprises. It is a library, not a framework; you will write the directory walk yourself, and you should.

## Node.js — archiver to Write, yauzl to Read

The JavaScript ecosystem split this problem in two, and it is worth respecting that split.

**`archiver`** (2,977 stars) is a streaming interface for *generating* archives. From its README:

```bash
npm install archiver --save
```

```javascript
import fs from "fs";
import { ZipArchive } from "archiver";

const output = fs.createWriteStream(__dirname + "/example.zip");
const archive = new ZipArchive({
  zlib: { level: 9 }, // Sets the compression level.
});
output.on("close", function () {
  console.log(archive.pointer() + " total bytes");
});
```

The important property here is constancy of memory: entries are streamed into the output, so a 5 GB directory does not become a 5 GB Buffer.

**`yauzl`** (825 stars) is the read-side counterpart, built for lazy iteration — nothing is decompressed until you ask for it. The current README leads with an async iteration form and keeps the callback form for older code:

```javascript
const yauzl = require("yauzl");

const zipfile = await yauzl.openPromise("path/to/file.zip");
for await (let entry of zipfile.eachEntry()) {
  if (entry.fileName.endsWith("/")) continue; // directory entry
  const readStream = await zipfile.openReadStreamPromise(entry);
  // pipe to a destination
}
```

Because entries are produced one at a time and you control when the next `readEntry()` happens, you can enforce per-entry limits — maximum uncompressed size, allowed path prefixes, entry count — which is how you defend against decompression bombs without reading the whole archive into memory.

**Verdict:** `archiver` + `yauzl` is the standard Node pair. If you only need plain zip reading and want zero dependencies, `node:zlib` plus a zip parser is not obviously simpler than `yauzl`.

## Rust — tar-rs and the zip crate

Rust's ecosystem splits along the same stream/random-access line. `tar-rs` handles tar streams and leaves compression to companion crates:

```toml
# Cargo.toml
[dependencies]
tar = "0.4"
```

The maintained zip implementation is `zip2` (published as the `zip` crate), whose README documents a feature-flag-driven build so you only compile the codecs you actually need:

```toml
zip = { version = "latest", default-features = false, features = [
    # "aes-crypto",
    # "bzip2",
    # "xz",
    "deflate64",
    "deflate",
    "lzma",
    "time",
    "zstd",
] }
```

That level of granularity matters when you ship a CLI: pulling in xz, zstd and AES by default doubles your dependency tree for formats most users never touch.

**Verdict:** `tar-rs` for streams, `zip2` for zip, `flate2` to glue gzip on top. The Rust crates are narrower than their C and .NET counterparts by design.

## Pitfalls That Cause Real Incidents

**Zip-slip (path traversal).** An entry whose name contains parent-directory segments — two `..` components followed by `etc/cron.d/job`, for instance — will happily escape your extraction root if you join paths without checking. Normalise every entry path, reject absolute paths and any `..` component, and never trust the archive's directory entries to have been sanitised. This remains the single most common archive vulnerability.

**Zip64.** Classic zip caps at 4 GB per file and 65,535 entries. Larger archives need the Zip64 extension — and while modern libraries handle it, the *header order* varies between producers, so test with archives from your actual users, not just ones you created.

**Streaming versus random access.** RAR, and 7z in important respects, cannot be read as a pure forward stream. If your pipeline is "stream the upload and never store it," those formats are not available to you no matter which library you pick — decide the pipeline before choosing the library.

**Encryption is not one thing.** Traditional ZipCrypto is cryptographically broken; AES-encrypted zips need explicit support, and `SevenZOutputFile`-style APIs handle their own encryption. If you accept encrypted uploads, document which scheme you support and reject the rest loudly.

**Filename encoding.** Zip stores names as bytes with an optional UTF-8 flag. Without the flag, producers disagree on whether that byte stream is CP437, Latin-1 or a local ANSI code page. Mojibake in extracted filenames is an encoding bug, not a corruption bug.

**Deterministic archives.** Build pipelines want reproducible output, which means normalising mtimes, entry order, uid/gid and compression level. None of these libraries does it for you by default.

**Decompression bombs.** A 2 MB zip can expand to terabytes. Enforce a maximum expansion ratio and a maximum entry count, and write to a filesystem with a quota.

**Never interpolate user input into a shell command.** `tar -xf $USER_FILE` is an argument-injection vulnerability; a filename starting with `-` is a flag, and a shell metacharacter is a command. Use a library API, or pass arguments as an array with `--` terminating flags.

If your cache layer also stores compressed payloads, the [Linux compression tools comparison](../2026-06-01-linux-compression-tools-zstd-brotli-lz4-gzip/) and the [C++ compression libraries comparison](../2026-06-27-cpp-compression-libraries-lz4-zstd-brotli-snappy-miniz/) go one level deeper on codecs and speed. For archives as a backup target rather than a transport format, our [backup integrity verification guide](../2026-05-11-backup-integrity-verification-restic-borg-borgmatic/) covers verification and restore drills.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Archive Libraries in 2026: libarchive vs SharpCompress vs Commons Compress vs archiver",
  "description": "Compare the archive and zip libraries that ship in production in 2026 - libarchive, SharpCompress, Apache Commons Compress, archiver and yauzl - with live repository data, format coverage and extraction safety pitfalls.",
  "datePublished": "2026-09-27",
  "dateModified": "2026-09-27",
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

**Which archive library supports the most formats?**
`libarchive`. It reads tar, zip, 7z, ISO 9660, cpio, xar, rar (read), ar, mtree and lha through one API, because formats and compression filters are separate layers inside the library. For polyglot services that accept arbitrary uploads, it is the widest and most hardened option.

**What is the best zip library for .NET in 2026?**
`SharpCompress` when you need many formats, non-seekable stream support or async extraction. For plain zip files only, the built-in `System.IO.Compression.ZipArchive` is sufficient and adds no dependency.

**Can I use `archiver` to read a zip file in Node.js?**
No. `archiver` is write-only. Use `yauzl` (or another read-focused zip library) for reading. The Node ecosystem intentionally splits archive generation from archive extraction.

**Why is 7z considered a poor choice for streaming pipelines?**
Because 7z is not a streamable container format — its structure requires seeking. Libraries such as SharpCompress document that 7z does not support streamable formats, so a pipeline that must process an upload without storing it first cannot use 7z.

**What is zip-slip and how do I prevent it?**
Zip-slip is a path traversal attack where an archive entry name climbs out of the extraction directory using parent-directory segments before targeting a sensitive path. Prevent it by normalising entry paths, rejecting absolute paths and any `..` segments, and extracting into a sandboxed directory — never by trusting the archive's own metadata.

**Is it safe to shell out to `tar` or `unzip` from my application?**
Only if the filename is passed as a separate argument with proper separation (an array-based exec call plus a `--` terminator), never interpolated into a shell string. Even then, a library API avoids the argument-injection class of bug entirely and gives you per-entry control.

**Do these libraries limit how much a compressed file can expand?**
Not by default. Decompression-bomb protection is the caller's responsibility: enforce an expansion ratio limit, a maximum entry count and a disk quota on the extraction target.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
