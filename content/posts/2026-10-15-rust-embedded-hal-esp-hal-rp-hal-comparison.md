---
title: "Rust on Microcontrollers in 2026: embedded-hal vs esp-hal vs rp-hal Compared"
date: "2026-10-15"
description: "embedded-hal, esp-hal and rp-hal compared for 2026 embedded Rust projects: trait families, supported silicon, target setup, real cargo configuration, async options and the version pitfalls that break builds."
tags: ["rust", "embedded", "microcontroller", "hardware-abstraction", "comparison"]
draft: false
cover: "/img/screenshots/esp-hal-logo.jpg"
---

Embedded Rust stopped being an experiment the moment its interfaces stabilised. In 2026 the practical question is no longer "can I write firmware in Rust?" but "which HAL do I write my driver against, and what breaks when the silicon vendor changes it?" The three repositories that answer that question — `embedded-hal`, `esp-hal` and `rp-hal` — sit at different layers of the same stack, which is why comparing them as rivals misses the point and comparing them as collaborators is what actually ships products.

Here is the layer model worth internalising before you pick: **`embedded-hal` is a set of traits** (an interface specification), while **`esp-hal` and `rp-hal` are implementations** for specific silicon. Your driver code should depend on the traits; your `main` function depends on the implementation.

## TL;DR: The 2026 Verdict

**Write every driver against `embedded-hal` traits** — that is what makes an I2C sensor or SPI display driver portable across chips and even across vendors. **Pick `esp-hal`** if you are targeting Espressif parts (ESP32 series through the ESP32-P4), where the crate has reached a tagged 1.0 release line and ships a `no_std` HAL covering the whole family. **Pick `rp-hal`** for Raspberry Pi RP2040 and RP235x boards, where you get per-chip crates plus ready-made board support packages for Pico-class hardware.

If you only remember one rule: your *application* is vendor-specific, your *library* is not. Libraries built on `embedded-hal` traits outlive every chip you will ship on.

## Comparison Table: embedded-hal vs esp-hal vs rp-hal

| Dimension | embedded-hal | esp-hal | rp-hal |
|---|---|---|---|
| GitHub stars | **2,667** | **2,151** | **1,928** |
| Last upstream activity | 2026-05-26 | 2026-10-15 | 2026-10-13 |
| What it is | Trait definitions (interface spec) | Vendor HAL for Espressif chips | Vendor HAL for RP2040 / RP235x |
| License | MIT OR Apache-2.0 | MIT OR Apache-2.0 | MIT OR Apache-2.0 |
| Silicon coverage | None (hardware-independent) | ESP32, C2, C3, C6, H2, P4, S2, S3 (+ low-power cores via `esp-lp-hal`) | RP2040, RP235x (Arm and RISC-V cores) |
| `no_std` | N/A (it is a trait crate) | Yes, bare-metal by design | Yes |
| Trait families shipped | `embedded-hal`, `-async`, `-nb`, `embedded-can`, `embedded-io`, `embedded-io-async`, `embedded-io-adapters` | Hardware APIs for the vendor peripherals | Hardware APIs for the vendor peripherals |
| Board support packages | N/A | Examples plus Espressif tooling | **Separate `rp-hal-boards` repo with Pico BSPs** |
| Flashing tooling | N/A | `espflash` (esp-rs tooling) | `probe-rs` over SWD, or `picotool` for UF2 |
| Async story | `embedded-hal-async` traits | Used with async runtimes | Used with async runtimes |

The star counts and last-push dates above come from the live GitHub API at publish time. Note how the activity dates differ: the trait crate moves slowly on purpose (interfaces must be stable), while vendor HALs move weekly.

## Decision Matrix: What to Depend On

| Your goal | Depend on | Why |
|---|---|---|
| Ship a reusable sensor/display driver | **embedded-hal traits** | Compiles for any chip whose HAL implements the traits |
| Target ESP32-C6 or ESP32-P4 | **esp-hal** | Vendor HAL for the whole Espressif family, including low-power cores |
| Target Raspberry Pi Pico / Pico 2 | **rp-hal + rp-hal-boards** | Per-chip crates plus a BSP per board |
| Same driver on both ESP32 and RP2350 | **embedded-hal traits + two HALs** | Only the initialisation code differs |
| Need async peripherals without blocking | **embedded-hal-async + an async runtime** | Async trait variants exist alongside the blocking ones |
| Want the smallest possible dependency tree | **embedded-hal (blocking traits only)** | Trait crates carry no hardware code |

## embedded-hal — The Interface Layer

`embedded-hal` exists to answer one question: what does an I2C bus *look like* to a driver that has never seen your chip? It is a family of crates rather than a single library — the README lists the blocking core traits, an async variant, a polling variant built on the `nb` crate, CAN traits, and blocking plus async I/O traits with adapters between them and standard traits.

```toml
[dependencies]
embedded-hal = "1.0"
embedded-hal-async = "1.0"
```

A portable driver is then nothing more than a generic type bounded by those traits:

```rust
use embedded_hal::i2c::I2c;
use embedded_hal::delay::DelayNs;

pub struct Sensor<I2C> {
    i2c: I2C,
}

impl<I2C: I2c> Sensor<I2C> {
    pub fn new(i2c: I2C) -> Self {
        Self { i2c }
    }

    pub fn read_register(&mut self, reg: u8) -> Result<u8, I2C::Error> {
        let mut buf = [0u8; 1];
        self.i2c.write_read(0x40, &[reg], &mut buf)?;
        Ok(buf[0])
    }
}

// Non-I2C helpers stay generic too
pub fn settle<D: DelayNs>(delay: &mut D) {
    delay.delay_ms(10);
}
```

That function compiles unchanged on an ESP32-C6, an RP2350 and any future chip whose HAL implements `i2c::I2c`. Two operational notes from the project itself: the trait crates are careful about backwards compatibility but explicitly reserve the right to tighten requirements in patch releases, so pin your versions; and adding a new trait is a documented, reviewed process rather than a `cargo add`, which is exactly why the interface has stayed usable.

Drivers sharing a bus is a real hardware-architecture question, and the documentation ships diagrams for it:

![embedded-hal shared I2C bus documentation diagram](/img/screenshots/embedded-hal-i2c-diagram.jpg "embedded-hal documentation diagram for a shared I2C bus")

## esp-hal — The Espressif Vendor HAL

`esp-hal` is a bare-metal (`no_std`) hardware abstraction layer for Espressif devices, and the chip list is broad: ESP32, ESP32-C2, C3, C6, H2, P4, S2 and S3. It also covers the low-power RISC-V cores inside the C6, S2 and S3 through a separate `esp-lp-hal` package — relevant if you are building something that sleeps for months.

Two practical details matter more than the feature list. First, the repository is on a release-tag cadence: the README recommends browsing examples at the tag matching your release (for example `esp-hal-v1.0.0`) because `main` is the development branch and API changes land there first. Second, the dependency spec it recommends uses the tilde operator so a `cargo update` cannot silently pull a minor version:

```toml
[dependencies]
esp-hal = { version = "~1.0.0", features = ["esp32c6"] }
```

Because the crate is `no_std`, you do not get `std` conveniences — no `println!` unless you wire a peripheral to it. Flashing and monitoring are handled by the esp-rs tooling (the `espflash` tool), and the project points readers at the Rust on ESP book and the `no_std` training material rather than duplicating it. The project also states plainly which crates are more or less mature, which is more useful than a marketing maturity badge: advanced peripherals may lag the common ones.

## rp-hal — Per-Chip Crates Plus Board Support

`rp-hal` covers Raspberry Pi microcontrollers with separate crates per chip family: `rp2040-hal` for the RP2040 and `rp235x-hal` for the RP235x, each with its own examples folder. Board-specific work lives in the companion `rp-hal-boards` repository, which is where you will find a BSP and examples for the Pico and similar boards — the README's advice is to start from a project template rather than the bare HAL when one exists for your board.

Setup is explicit about targets, which is the single most common source of "it does not build" complaints in embedded Rust:

```sh
rustup self update
rustup update stable
rustup target add thumbv6m-none-eabi           # RP2040 (Cortex-M0+)
rustup target add thumbv8m.main-none-eabihf    # RP235x (Cortex-M33)
rustup target add riscv32imac-unknown-none-elf # RP235x (RISC-V)

# Flash and debug over SWD with a debug probe
cargo install --locked probe-rs-tools
```

If you would rather flash over USB instead of a debug probe, the README points at `picotool` for producing UF2 images for the bootloader. That combination matters for production: `probe-rs` gives you full debug attach during development, while UF2 images let a technician update a board with a file copy — the same trade-off as the USB-based firmware update flow described in our [MCUboot, OpenBLT and TinyUF2 comparison](../2026-10-15-mcu-bootloaders-mcuboot-openblt-tinyuf2-secure-ota-comparison/).

Which HAL sits under which firmware architecture is easiest to see once you have picked an RTOS; our [Zephyr, NuttX and RIOT comparison](../2026-09-23-embedded-rtos-zephyr-nuttx-riot-os-comparison/) covers the C-side equivalents, and the storage decisions on the same board usually come down to [LittleFS, SPIFFS or FatFs](../2026-10-15-embedded-filesystems-littlefs-vs-spiffs-vs-fatfs/).

## The Async Layer Above the Traits

The reason `embedded-hal` ships both blocking and async trait variants is the async ecosystem that implements them. A framework such as `embassy` (a widely used embedded async framework, with project activity in October 2026) provides executors and drivers that implement the `embedded-hal-async` traits, which means a driver written against async traits moves between vendor HALs the same way a blocking driver does.

The practical rule: decide blocking versus async **once**, at the architectural level. Maintaining both a blocking and an async version of every driver is the fastest way to double your maintenance surface for no user-visible benefit.

## Pitfalls That Cost Embedded Rust Teams Weeks

**Trait version skew.** Vendor HALs pin compatible versions of the trait crates. Mixing a driver written for one trait release with a HAL built against another produces trait-bound errors that read like compiler noise. Pin `embedded-hal` in `Cargo.toml` and update deliberately.

**Wrong target triple.** `thumbv6m-none-eabi` for an RP2040 and `thumbv8m.main-none-eabihf` for the RP235x are not interchangeable, and a missing `rustup target add` surfaces as a linker error rather than a helpful message. Add the targets before you start the project, not during a debug session.

**Using the development branch as a dependency.** `esp-hal`'s own README warns that `main` carries in-progress API changes and recommends pinning to a release tag — and using `~` in the version spec so a `cargo update` cannot drag you onto a different minor line. The same discipline applies to any Git-sourced fork.

**Assuming `std` exists.** These are bare-metal crates. Logging, panic handlers, allocators and delays are all things you either bring or do without — which is why probe-based debug tooling matters so much more than it does on a host.

**Reinventing a driver that exists.** Because drivers are trait-generic, an existing `embedded-hal` driver for your sensor usually works unchanged. Check before writing a vendor-specific port that will need rewriting on your next board revision.

**Locking the HAL to a board revision.** Board-level configuration belongs in your BSP layer, not sprinkled through application code. The `rp-hal-boards` split exists precisely because mixing them makes a hardware revision spin into a firmware rewrite.

## FAQ

### Should I use embedded-hal or a vendor HAL?

Use both, in different layers. `embedded-hal` defines the traits your reusable drivers depend on, while a vendor HAL such as `esp-hal` or `rp-hal` implements those traits for specific silicon and provides the initialisation code your `main` function needs.

### Does esp-hal support all ESP32 chips?

`esp-hal` is a bare-metal HAL covering ESP32, ESP32-C2, C3, C6, H2, P4, S2 and S3, with support for the low-power RISC-V cores on the C6, S2 and S3 provided by the separate `esp-lp-hal` package. Check per-crate maturity notes before relying on an advanced peripheral.

### What target triple do I need for an RP2040 or RP235x?

Add `thumbv6m-none-eabi` for the RP2040, `thumbv8m.main-none-eabihf` for the RP235x Arm cores, and `riscv32imac-unknown-none-elf` if you are building for the RP235x RISC-V cores. Installing `probe-rs-tools` gives you flashing and debug over SWD.

### Can I write one driver that works on both ESP32 and Raspberry Pi boards?

Yes, if the driver depends only on `embedded-hal` traits rather than on vendor types. The driver code stays identical; only the hardware initialisation in your application changes between the two HALs.

### Is embedded Rust ready for production in 2026?

For common peripherals it is. The trait interface has stabilised, vendor HALs ship release-tagged versions and their own examples, and flashing and debug tooling is mature on both major families. The remaining risk is version churn inside vendor HALs, which pinning and release tags mitigate.

### Why does the trait crate see so few commits compared with the vendor HALs?

Because it is an interface specification. Trait crates change only when an interface must evolve, while vendor HALs track silicon errata, new chips and new peripherals — which is why `embedded-hal` shows months between pushes and `esp-hal` shows pushes in the same week.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust on Microcontrollers in 2026: embedded-hal vs esp-hal vs rp-hal Compared",
  "description": "Comparison of embedded-hal, esp-hal and rp-hal for embedded Rust in 2026: trait families, supported chips, target setup, cargo configuration, async options and version pitfalls.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
