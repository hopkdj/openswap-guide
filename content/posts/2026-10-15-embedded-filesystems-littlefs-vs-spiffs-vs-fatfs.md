---
title: "LittleFS vs SPIFFS vs FatFs in 2026: Which Embedded Filesystem Should You Actually Use?"
date: "2026-10-15"
description: "A hands-on comparison of LittleFS, SPIFFS and FatFs for microcontrollers: power-loss safety, wear leveling, RAM cost, real API examples and migration notes for 2026."
tags: ["embedded", "filesystem", "microcontroller", "storage", "flash", "firmware"]
draft: false
---

Your firmware passed every test in the lab. Then a field unit loses power during a config write and comes back with an unreadable flash region — and suddenly your support queue is full of RMAs. On microcontrollers, the filesystem is not a detail you bolt on at the end. It is the component that decides whether a power cut corrupts your users' data or is a non-event.

Three names dominate embedded storage in 2026: **LittleFS**, **SPIFFS**, and **FatFs**. They look interchangeable in a BOM and behave nothing alike under stress. This guide compares them on the things that actually bite: power-loss behavior, wear leveling, RAM footprint, directory support, and how much work each one costs you when your flash geometry changes.

## TL;DR — Quick Verdict

**New firmware on raw NOR or NAND flash: use LittleFS.** It is power-loss resilient by design, has bounded RAM, and is the filesystem ESP-IDF and Zephyr both steer you toward in 2026.

**Removable SD cards that a laptop must also read: use FatFs.** Nothing else gives you interchangeability with Windows, macOS and cameras — just accept that FatFs does no wear leveling itself.

**Still running SPIFFS: migrate.** SPIFFS is marked deprecated in ESP-IDF, its upstream repo has sat on release 0.3.7, and its flat namespace plus high RAM-per-open-file cost are exactly the problems LittleFS was written to fix. Migration is a read-write loop, not a rewrite.

## The 2026 Landscape at a Glance

All numbers below were pulled live from GitHub on 2026-10-15.

| | **LittleFS** | **SPIFFS** | **FatFs** |
|---|---|---|---|
| Repo | littlefs-project/littlefs | pellepl/spiffs | ChaN FatFs (abbrev/fatfs mirror) |
| Stars | 6,972 | 1,632 | 362 (mirror counts only) |
| Latest release | v2.11.3 | 0.3.7 | R0.16 |
| Last commit | 2026-10-08 | 2026-07-16 | 2026-07-09 |
| License | MIT | MIT | FatFs permissive license |
| Wear leveling | Built in (dynamic) | Built in (static + dynamic) | **None** |
| Power-loss safe | Yes — copy-on-write, atomic commits | Partial — no atomic multi-page updates | No — FAT tables can be left inconsistent |
| Directories | Yes | No (flat namespace) | Yes (full FAT tree) |
| RAM per open file | ~32 bytes + shared cache | Several KB with cache buffers | ~550 bytes (higher with LFN) |
| Media | Raw NOR/NAND flash | Raw SPI NOR flash | SD/eMMC/block devices with an FTL |
| PC compatibility | No (needs custom tooling) | No | Yes — standard FAT12/16/32/exFAT |
| Actively recommended | Yes (ESP-IDF, Zephyr) | No (deprecated in ESP-IDF) | Yes, for removable media |

The single most important row is wear leveling. FatFs is not broken — it simply assumes the media underneath handles wear, which is true for SD cards with their own controller and false for bare NOR flash with a 100,000-cycle erase limit per sector.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Use | Why |
|---|---|---|
| New MCU product, on-board SPI NOR flash | **LittleFS** | Atomic commits survive brown-outs; no erase-cycle hotspots |
| Data logger writing a file every few seconds | **LittleFS** | Wear leveling spreads writes; bounded RAM keeps the RTOS healthy |
| Device must expose files to a PC via card reader | **FatFs** | Only option with real FAT/exFAT interoperability |
| Existing SPIFFS firmware, stable hardware | **LittleFS** (after migration) | Same flash, same API shape, better failure semantics |
| Large removable media (>32 GB) | **FatFs with exFAT enabled** | FAT32 cannot address volumes that large |
| Read-only asset blobs, firmware-versioned | LittleFS or an immutable partition | Simpler than a filesystem you never write to |
| Hard real-time loop with no heap | **LittleFS with static buffers** | `LFS_NO_MALLOC` removes dynamic allocation entirely |

## LittleFS — The Modern Default for Raw Flash

LittleFS was written at ARM for exactly the failure mode most filesystems ignore: a device that can lose power at any instruction. Every metadata update is a copy-on-write commit to a new pair of blocks, so the previous state stays valid until the new state is complete. You get wear leveling, dynamic block allocation and bounded RAM without a journaling layer you have to tune.

Configuration is a single struct that describes your block device and tradeoffs. This mirrors the structure documented in `lfs.h`:

```c
#include "lfs.h"

static int bd_read(const struct lfs_config *c, lfs_block_t block,
                   lfs_off_t off, void *buffer, lfs_size_t size);
static int bd_prog(const struct lfs_config *c, lfs_block_t block,
                   lfs_off_t off, const void *buffer, lfs_size_t size);
static int bd_erase(const struct lfs_config *c, lfs_block_t block);
static int bd_sync(const struct lfs_config *c);

const struct lfs_config cfg = {
    // block device operations
    .read  = bd_read,
    .prog  = bd_prog,
    .erase = bd_erase,
    .sync  = bd_sync,

    // block device configuration — MUST match your flash datasheet
    .read_size      = 16,
    .prog_size      = 16,
    .block_size     = 4096,
    .block_count    = 128,      // 512 KiB total
    .cache_size     = 16,
    .lookahead_size = 16,
    .block_cycles   = 500,      // wear-leveling aggressiveness
};

lfs_t lfs;
lfs_file_t file;

// mount, formatting only if the filesystem is missing
int err = lfs_mount(&lfs, &cfg);
if (err) {
    lfs_format(&lfs, &cfg);
    lfs_mount(&lfs, &cfg);
}

// write a config file atomically
lfs_file_open(&lfs, &file, "settings.json", LFS_O_WRONLY | LFS_O_CREAT | LFS_O_TRUNC);
lfs_file_write(&lfs, &file, payload, payload_len);
lfs_file_close(&lfs, &file);   // commit happens here
```

`lfs_file_close()` is the commit point. If power dies before it returns, the old file survives intact — that single guarantee is the reason LittleFS displaced ad-hoc flash logging code in so many products.

Two settings deserve attention. `.block_cycles` controls how aggressively blocks are retired; the default of 500 is a sensible balance for small flash. And if your target forbids the heap, define `LFS_NO_MALLOC` and provide static buffers — LittleFS supports it, SPIFFS' cached mode does not do it as cleanly.

## SPIFFS — The Legacy Choice You Should Migrate Away From

SPIFFS solved a real problem in 2013: a small, wear-leveled filesystem for SPI NOR flash on the ESP8266. A decade later its constraints define it. There are **no directories** — every file lives in one flat namespace at the root. Metadata for the whole device is scanned and cached, which is why opening a file can cost kilobytes of RAM rather than bytes.

Its API is still pleasant, which is why so much firmware still calls it:

```c
spiffs_config cfg = {
    .hal_read_f  = my_spi_read,
    .hal_write_f = my_spi_write,
    .hal_erase_f = my_spi_erase,
    .phys_size        = 2 * 1024 * 1024,
    .phys_addr        = 0x100000,
    .phys_erase_block = 4096,
    .log_block_size   = 65536,
    .log_page_size    = 256,
};

s32_t res = SPIFFS_mount(&fs, &cfg, work_buf, fd_buf, sizeof(fd_buf),
                         cache_buf, sizeof(cache_buf), my_spiffs_check);

if (res == SPIFFS_ERR_NOT_A_FS) {
    SPIFFS_format(&fs);
    res = SPIFFS_mount(&fs, &cfg, work_buf, fd_buf, sizeof(fd_buf),
                       cache_buf, sizeof(cache_buf), my_spiffs_check);
}

spiffs_file fd = SPIFFS_open(&fs, "settings.json", SPIFFS_CREAT | SPIFFS_TRUNC | SPIFFS_RDWR, 0);
SPIFFS_write(&fs, fd, payload, payload_len);
SPIFFS_close(&fs, fd);
```

The problem is not the API — it is the failure semantics. SPIFFS updates a page in place when it can, so a power cut mid-write can leave a partially written page plus metadata that no longer agrees with it. A consistency check helps, but on a battery-powered sensor with an unreliable rail, "helps" is not the bar.

Add the maintenance reality: ESP-IDF documents SPIFFS as deprecated in favour of LittleFS and FatFs, the upstream repository has not cut a release since 0.3.7, and the flat namespace means renaming every file when you want a `/logs/` directory. The pragmatic 2026 answer is a one-time migration: mount SPIFFS read-only, stream every file into LittleFS, verify a checksum, then erase the SPIFFS partition. Budget a day, not a sprint.

## FatFs — Still the Right Answer for SD Cards

FatFs is the opposite tradeoff, and it wins decisively on one axis: interchangeability. Log to an SD card with FatFs and a technician can pull the card, plug it into a laptop and open the file in a spreadsheet. No proprietary tooling, no custom driver, no translation step. That alone keeps FatFs in production in millions of devices.

It is also the most portable option in the group: you implement four functions in `diskio.c`, and the rest runs unchanged on any MCU with a C compiler. Configuration happens at compile time in `ffconf.h`:

```c
#include "ff.h"

FATFS fs;          // one per volume
FIL   fil;
UINT  bw;
FRESULT fr;

fr = f_mount(&fs, "0:", 1);              // mount (1 = mount now)
if (fr != FR_OK) {
    // format a 32 GB card as exFAT-compatible FAT32 where possible
    f_mkfs("0:", NULL, work, sizeof(work));
    f_mount(&fs, "0:", 1);
}

fr = f_open(&fil, "0:/log/data.csv", FA_WRITE | FA_OPEN_APPEND);
if (fr == FR_OK) {
    f_write(&fil, line, line_len, &bw);
    f_sync(&fil);                         // flush the FAT metadata
    f_close(&fil);
}
```

The catch is entirely in the media contract. FatFs assumes the block device hides erase limits and completes writes in reasonable time. Hand it raw NOR flash and you will erase the same FAT sector thousands of times until it dies, because there is no wear leveling layer at all. It also assumes your `disk_ioctl` correctly reports sector size and that SPI SD card calls tolerate 100 ms-class latencies — a common source of `FR_DISK_ERR` on first-week hardware.

Feature flags matter more here than in the other two. Enable `FF_USE_LFN` for long file names (and budget the extra RAM), and enable `FF_FS_EXFAT` if you ship cards larger than 32 GB. Leave both off and you will discover the limit at the worst possible moment — with a customer's full card in hand.

## Performance and Wear: What Actually Kills Flash

Raw write throughput is the wrong metric to optimise. Three things actually determine longevity:

- **Erase cycles per sector.** NOR flash typically tolerates ~100,000 erases per 4 KB sector. Overwriting one 512-byte config block every minute without wear leveling burns a sector in about 70 days. LittleFS and SPIFFS rotate blocks; FatFs does not.
- **Write amplification.** LittleFS' copy-on-write metadata means a small write touches metadata blocks as well as data. It costs write endurance but buys crash safety — a tradeoff worth taking for configuration, less so for high-rate telemetry.
- **Mount time and RAM ceiling.** SPIFFS' full metadata scan grows with device size and can be slow on 4 MB parts. LittleFS keeps mount time bounded, which matters if your device must be functional within milliseconds of brown-out recovery.

If you are choosing storage for a data-recording device, read our comparison of [embedded key-value stores such as LevelDB, RocksDB, LMDB and BadgerDB](../2026-06-17-self-hosted-embedded-key-value-stores-leveldb-rocksdb-lmdb-badgerdb/) — for append-heavy logs, a key-value store plus a filesystem for asset files often beats a filesystem alone. And if your product runs an RTOS, the [Zephyr vs NuttX vs RIOT-OS comparison](../2026-09-23-embedded-rtos-zephyr-nuttx-riot-os-comparison/) covers which kernels ship LittleFS and FatFs as first-class modules.

## Common Pitfalls and Migration Notes

**Get the geometry from the datasheet, not from an example.** `read_size`, `prog_size` and `block_size` must match the physical part. A 256-byte page size on a part with 512-byte pages produces `LFS_ERR_CORRUPT` long before it produces a helpful error message.

**Block count must satisfy your wear-leveling budget.** LittleFS needs at least a handful of blocks free to compact metadata. A 32-block configuration with `block_cycles = 100` wears out fast; measure before shipping.

**Never put FatFs on raw flash.** If you must reuse a FAT-based workflow on bare NOR, put a flash translation layer underneath — otherwise you are trading convenience for a guaranteed field failure.

**Thread safety is opt-in everywhere.** LittleFS needs `LFS_THREADSAFE` plus a mutex; SPIFFS needs a global lock; FatFs needs `FF_FS_REENTRANT`. RTOS tasks that write concurrently without this will corrupt data in ways that only appear on customer hardware.

**Migrate at boot, not in the field.** The safest SPIFFS-to-LittleFS migration runs during a firmware update: read the old partition, write into the new one, verify, then stop mounting SPIFFS. Shipping a dual-mount migration to devices you cannot reach is a support liability.

For teams standardising the rest of the board, our [embedded Linux build-system guide covering Yocto, Buildroot and OpenEmbedded](../2026-06-05-embedded-linux-build-yocto-buildroot-openembedded-guide/) covers how these filesystems get packaged into images, and [embedded database engines such as libmdbx, LMDB and UnQLite](../2026-06-13-self-hosted-embedded-database-engines-libmdbx-lmdb-unqlite-vedis/) covers the layer above if you need queries rather than files. Devices that log sensor data at low rate — like the [open-source homebrewing controllers BrewPiLess, CraftBeerPi and Fermentrack](../2026-06-04-self-hosted-homebrewing-controllers-brewpiless-craftbeerpi-fermentrack-guide/) — are a good real-world example of why a crash-safe filesystem matters more than peak write speed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "LittleFS vs SPIFFS vs FatFs in 2026: Which Embedded Filesystem Should You Actually Use?",
  "description": "Hands-on comparison of LittleFS, SPIFFS and FatFs for microcontrollers: power-loss safety, wear leveling, RAM cost, real API examples and migration notes.",
  "datePublished": "2026-10-15",
  "dateModified": "2026-10-15",
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

**Is SPIFFS still maintained in 2026?**
No. SPIFFS sits on release 0.3.7, and ESP-IDF documents it as deprecated in favour of LittleFS and FatFs. The upstream repository still receives occasional commits, but it is not where new development happens. If you are starting a project, choose LittleFS.

**Can LittleFS run on an SD card instead of FatFs?**
Technically yes — LittleFS only needs block read, program, erase and sync callbacks, and an SD card can provide them. Practically, the tradeoff is interoperability: LittleFS volumes cannot be read by a laptop without custom tooling. Use FatFs when the card must travel between devices.

**Does FatFs work on raw NOR flash?**
Not safely. FatFs implements no wear leveling, so repeatedly rewriting the FAT or the same file burns through the erase-cycle limit of the flash sector and the volume fails permanently. Use LittleFS on bare flash, or add a flash translation layer underneath FatFs.

**How much RAM does each filesystem need?**
LittleFS needs roughly 32 bytes per open file plus a shared cache you size yourself, and it can avoid the heap entirely with static buffers. SPIFFS can consume several kilobytes per open file in cached mode. FatFs is around 550 bytes per `FIL` object, more when long file names are enabled — the exact figure depends on `FF_USE_LFN` and the LFN buffer setting.

**What is the safest way to migrate from SPIFFS to LittleFS?**
Do it during a firmware update with both filesystems mounted: mount SPIFFS read-only, stream each file into LittleFS, verify a checksum per file, then disable the SPIFFS partition and reclaim its space. Never ship a migration that depends on a device rebooting cleanly in the field.

**Can I use two filesystems at once on the same device?**
Yes, and it is common: LittleFS on the internal flash for settings and logs, FatFs on a removable SD card for user data. They occupy separate flash partitions or media, and Zephyr ships both as modules, so mixing them costs no extra porting work.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
