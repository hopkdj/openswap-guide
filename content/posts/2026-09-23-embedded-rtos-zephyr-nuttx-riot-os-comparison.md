---
title: "Zephyr vs NuttX vs RIOT OS in 2026: Which Open-Source RTOS Should You Actually Ship?"
date: "2026-09-23"
tags: ["embedded", "rtos", "zephyr", "nuttx", "riot-os", "iot", "firmware", "open-source"]
categories: ["self-hosted"]
cover: "/img/screenshots/nuttx-rtos.jpg"
description: "A hands-on 2026 comparison of Zephyr, Apache NuttX and RIOT OS: real build commands, footprint numbers, board support, toolchain and CI setup, plus the pitfalls that bite teams 6 months into a product."
draft: false
---

Three commercial RTOS vendors still quote five-figure annual seat licenses to firmware teams in 2026, while Zephyr (16,586 GitHub stars), RIOT OS (5,804) and Apache NuttX (4,044) all shipped commits within the last 24 hours of writing. The real question is no longer "can open source run my product" — it is "which of the three open-source kernels matches my board, my team and my certification path".

This guide compares them the way an engineer actually evaluates an RTOS: build system, footprint, board support, networking stack, tooling and long-term maintenance risk — using commands pulled from each project's official documentation, not from memory.

## TL;DR — Quick Verdict

- **Choose Zephyr** if you are building a connected product on ARM Cortex-M/A, RISC-V or x86 with vendor silicon support, want one build tool (`west`), and need a CI harness (`twister`) that scales to hundreds of boards.
- **Choose Apache NuttX** if you want a **POSIX-shaped** API, need to reuse existing Linux C code, or want to prototype a whole application on your laptop before the hardware arrives — NuttX has a first-class `sim` board.
- **Choose RIOT OS** if your device is battery-constrained, speaks 6LoWPAN/Thread/BLE, and you value a small, readable codebase and a `Makefile`-based build you can fully understand in an afternoon.

All three are permissively licensed enough for commercial closed-source products (Zephyr and NuttX are Apache-2.0, RIOT is LGPL-2.1 with a static-linking exception in practice — read the notice if your legal team is strict).

## Side-by-Side Comparison (September 2026 data)

| Dimension | Zephyr | Apache NuttX | RIOT OS |
|---|---|---|---|
| GitHub stars | 16,586 | 4,044 | 5,804 |
| License | Apache-2.0 | Apache-2.0 | LGPL-2.1 |
| Governance | Linux Foundation project | Apache Software Foundation | RIOT-OS community (Freie Universität Berlin roots) |
| Language | C + Kconfig/CMake + devicetree | C, POSIX/ANSI-first | C, Make-based |
| Build system | `west` (CMake + Ninja under the hood) | `configure.sh` + `make` (Kconfig, CMake also supported) | plain `make` with `BOARD=` |
| Typical footprint | ~8–64 KB flash entry configurations | ~8 KB+ (scalable 8-bit to 64-bit) | ~5 KB+ on Cortex-M |
| Arch support | ARM Cortex-M/R/A, RISC-V, x86, ARC, Xtensa, SPARC, MIPS | ARM, RISC-V, x86, Xtensa, AVR, MIPS, sim | AVR, MSP430, ESP8266, ESP32, RISC-V, ARM7, Cortex-M, native |
| Board count | 1,000+ boards/devicetrees | board:config profiles across dozens of families | 200+ |
| Networking | LwM2M, MQTT, CoAP, Thread, Zigbee, BLE, Wi-Fi, Ethernet | BSD sockets, MQTT, CoAP, IEEE 802.15.4 | 6LoWPAN, GNRC, Thread, CoAP, MQTT-SN, BLE |
| Official container | `zephyrprojectrtos/zephyr-build` (194k+ pulls) | native toolchain or `sim` board | `riot/riotbuild` (132k+ pulls) |
| Test harness | `twister` | `nuttx-testing` / per-board configs | `make test` + Murdock CI |
| Last upstream push | 2026-09-22 | 2026-09-22 | 2026-09-22 |

Every project in that table is actively maintained — that matters more than any single feature, because an abandoned RTOS means you own the kernel forever.

## Decision Matrix: Match the Kernel to the Job

| Your situation | Pick | Why |
|---|---|---|
| Connected consumer product with a silicon vendor's eval board | **Zephyr** | Vendor devicetrees, upstream HAL integration, `west build -b <board>` gets you blinking an LED in minutes |
| Brownfield codebase full of `pthread`, `open()`, `select()` | **NuttX** | POSIX-compatible APIs and a simulator board let you port incrementally |
| Sub-100 KB wireless sensor mesh | **RIOT** | Smallest readable core, native 6LoWPAN/GNRC stack |
| Prototype before hardware exists | **NuttX** | `sim:nsh` runs a full shell in your terminal |
| Real-time control loop with hard deadlines | **Zephyr** or **RIOT** | Both offer tickless operation, priority inheritance and defined latency classes |
| Certification-bound (industrial/medical) | **Zephyr** | Largest ecosystem of vendor-assisted certification activity |
| You want to read the entire kernel this week | **RIOT** | A few hundred readable C files, Make-based build |
| Linux-adjacent edge gateway | **NuttX** | POSIX feature set makes Linux userland habits transferable |

## Zephyr — The Ecosystem Play

![Zephyr project official logo](/img/screenshots/zephyr-rtos.jpg "Zephyr RTOS official project logo")

Zephyr is the only one of the three with a full Linux-Foundation-style release cadence, a devicetree-based hardware description and a vendor onboarding pipeline. That shows up immediately in the workflow — the documented Ubuntu setup is:

```bash
# Official Zephyr getting-started dependencies (Ubuntu)
sudo apt install --no-install-recommends git cmake ninja-build gperf \
  ccache dfu-util device-tree-compiler wget python3-dev python3-venv python3-tk \
  xz-utils file make gcc gcc-multilib g++-multilib libsdl2-dev libmagic1

python3 -m venv ~/zephyrproject/.venv
source ~/zephyrproject/.venv/bin/activate
pip install west

# Create the west workspace and pull ~all vendor HALs
west init -m https://github.com/zephyrproject-rtos/zephyr ~/zephyrproject
cd ~/zephyrproject
west update
west zephyr-export
pip install -r ~/zephyrproject/zephyr/scripts/requirements.txt
```

Then a build against the emulated Cortex-M3 board, with the run goal handled by QEMU under the hood:

```bash
cd ~/zephyrproject/zephyr
west build -b qemu_cortex_m3 samples/hello_world
west build -t run          # boots the image in QEMU
```

If you would rather not pollute your host machine, the project publishes an official build container:

```yaml
# compose.yaml — reproducible Zephyr build environment
services:
  zephyr-build:
    image: zephyrprojectrtos/zephyr-build:latest
    working_dir: /workdir
    volumes:
      - ./zephyrproject:/workdir
    environment:
      - ZEPHYR_BASE=/workdir/zephyr
    command: west build -b qemu_cortex_m3 -d /workdir/build /workdir/zephyr/samples/hello_world
```

Configuration lives in Kconfig fragments (`prj.conf`), which is one of Zephyr's genuine strengths — you can diff a product configuration like any other source file:

```ini
# prj.conf — minimal networking build
CONFIG_NETWORKING=y
CONFIG_NET_IPV4=y
CONFIG_NET_TCP=y
CONFIG_MQTT_LIB=y
CONFIG_LOG=y
CONFIG_REBOOT=y
```

**Where Zephyr hurts:** the `west update` workspace pulls gigabytes of vendor HALs, so first-time setup is slow and offline builds need a pre-warmed mirror. Board ports churn — a board can be marked deprecated between LTS releases, and devicetree overlays mean your hardware description is code that has to be reviewed like code. Governance is also centralized: if your issue sits outside a silicon vendor's interest area, you may wait.

## Apache NuttX — POSIX on Bare Metal

NuttX takes the opposite bet: instead of a bespoke driver model, it implements POSIX and ANSI interfaces (plus selected VxWorks-style calls) on microcontrollers. For teams porting existing C code, that is the single most valuable property any RTOS can have — `pthread_create`, `open`, `poll` and `ioctl` behave the way your engineers already expect.

The killer feature for prototyping is the simulator board. You do not need hardware to run a real NuttX shell:

```bash
git clone https://github.com/apache/nuttx.git nuttx
git clone https://github.com/apache/nuttx-apps.git apps

cd nuttx
make distclean
./tools/configure.sh sim:nsh     # shell profile on the POSIX simulator
make -j$(nproc)
./nuttx                          # you are now in a NuttX NSH shell
```

Other documented simulator profiles include `sim:lvgl_fb` for graphics work and `sim:vncserver` for remote display experiments — genuinely useful when you want to develop a UI before the display hardware arrives:

```bash
./tools/configure.sh sim:lvgl_fb
make -j$(nproc)
```

Build modes matter as soon as you approach certification: NuttX supports flat, protected and kernel builds, so you can start with a single address space and move to memory-protected user tasks later without changing platforms. The price is configuration sprawl — `board:config` profiles number in the thousands across the tree, and app code lives in a *separate* repository (`nuttx-apps`) that must be kept in sync with the kernel. Documentation quality is improving (the `Documentation/` tree is now the canonical source) but older wiki content is still the top search hit for many topics.

## RIOT OS — Small, Readable, Network-First

RIOT's design goal is a microkernel-flavoured core with a clean module system and a build you can debug. Its board list spans AVR, MSP430, ESP8266, ESP32, RISC-V, ARM7 and Cortex-M — 200+ boards — and the official build container is a single `docker run` away:

```bash
git clone https://github.com/RIOT-OS/RIOT.git
cd RIOT/examples/hello-world

# Host-native build: RIOT runs as a normal process for fast iteration
make BOARD=native all
make term          # attaches the console

# Or build inside the official container (riot/riotbuild)
docker run --rm -it -v "$(pwd)":/data -w /data \
  riot/riotbuild make BOARD=native all
```

Networking is where RIOT shines. GNRC, its own IPv6/6LoWPAN stack, is upstream and integrated rather than bolted on, which is why it keeps appearing in Thread, CoAP and MQTT-SN sensor-mesh deployments. Modules are explicit in the Makefile, so your binary size is visibly tied to your feature list:

```makefile
# Makefile — pick exactly the modules you ship
USEMODULE += gnrc_ipv6_default
USEMODULE += gnrc_udp
USEMODULE += sock_udp
USEMODULE += netdev_default

include $(RIOTBASE)/Makefile.include
```

**Where RIOT hurts:** the Make-based build sits awkwardly next to the CMake-centric expectations of modern CI, and commercial silicon vendors contribute less than they do to Zephyr — so if your chip is exotic, you may be writing the port yourself. Ecosystem size also shows up in third-party library availability.

## Firmware CI Without Hardware: Emulation and HIL

One underrated advantage of all three projects is that each can run in an emulator, which lets you put firmware builds in a self-hosted pipeline without a bench full of dev boards. Zephyr ships QEMU board targets (`qemu_cortex_m3`, `qemu_x86`, `qemu_riscv32`), NuttX has the `sim` target, and RIOT has the `native` board plus QEMU targets for ARM and RISC-V.

That means your CI job can compile *and* boot the firmware on every push. Pair it with a container-based runner and a workload scheduler and you get a firmware pipeline that looks like a web pipeline:

- [Open-source FPGA and HDL toolchain guide](../2026-06-07-open-source-fpga-development-toolchain-yosys-iverilog-ghdl-nextpnr/) — the synthesis and simulation side of the same workflow.
- [Self-hosted HPC workload managers](../2026-05-02-slurm-vs-openpbs-vs-htcondor-self-hosted-hpc-workload-managers-guide/) — if your regression suite grows into a nightly job queue.
- [Embedded C HTTP libraries](../2026-09-04-embedded-c-http-libraries-mongoose-civetweb-libmicrohttpd/) — what to put on top of the TCP stack once the board is online.

If you want the emulation layer specifically, a dedicated comparison of full-system simulators is the next step — QEMU, Renode and gem5 each solve a different part of that problem.

## Cost Reality: What You Stop Paying For

Commercial RTOS licensing is usually a per-seat developer fee plus a per-unit royalty. On a 50,000-unit product with a mid-range royalty, the three-year delta between an open-source kernel and a commercial one is frequently six figures — and that is before support contracts. What you buy instead with open source is engineering time: bring-up, porting, and the discipline to pin a release and test upgrades yourself.

The honest counter-argument: you are trading license capex for maintenance opex. If nobody on your team owns the kernel upgrade, you will still be running a 2027 LTS in 2031 — which is fine, as long as you decided that on purpose.

## Pitfalls and Migration Traps

- **Do not start from `main`.** All three projects move fast. Zephyr's LTS releases, NuttX's release tags and RIOT release branches exist for a reason: pin, then upgrade deliberately.
- **Footprint claims come from minimal configs.** The headline "5 KB" figures assume no networking, no logging, no shell. Budget 3–5× once you enable a TCP stack, TLS and logging.
- **The build system is the biggest migration cost,** not the API. Moving a product from a Make-based build to `west` is a real project; evaluate the toolchain before you evaluate features.
- **Vendor HALs are where support dies.** If your chip's vendor publishes a Zephyr module, that is a strong signal. If it publishes nothing, budget for writing the port.
- **License files deserve a legal read.** Apache-2.0 is unambiguous for closed products; LGPL-2.1 requires attention to static-versus-dynamic linking decisions.
- **Keep an emulator in CI from day one.** Retrofitting QEMU or `sim` targets after the product ships is far harder than starting with a bootable emulated target.

## FAQ

**Is Zephyr really free for commercial products?**
Yes. Zephyr is Apache-2.0, so you can ship closed-source firmware with no royalty. You pay only for optional commercial support or the engineering time to maintain your own fork.

**Can NuttX run Linux applications unchanged?**
Close, but not identical. NuttX implements POSIX and ANSI APIs, so most portable C code compiles with small changes. Anything Linux-specific — epoll edge cases, cgroups, complex `ioctl` surfaces, or heavy dynamic linking — will need work.

**Which RTOS has the smallest footprint?**
RIOT OS generally has the smallest core, followed by NuttX, with Zephyr largest once networking and logging are enabled. Exact numbers depend entirely on configuration, so always measure your own build with `arm-none-eabi-size` or `size` rather than trusting a blog table.

**Can I run these without physical hardware?**
Yes. NuttX's `sim:nsh` profile runs a full shell on your development machine, RIOT's `BOARD=native` compiles to a host process, and Zephyr ships QEMU board targets such as `qemu_cortex_m3`.

**Which one should a single developer pick for a side project?**
RIOT if you want to understand every line and target a sensor node; Zephyr if you want the richest out-of-the-box feature set and the largest pile of tutorials; NuttX if you are porting existing C and want a familiar API surface.

**How often do these projects break APIs?**
Zephyr changes APIs between minor releases, which is why LTS branches exist. NuttX evolves more conservatively around POSIX. RIOT changes module names occasionally but keeps a stable core. In all three cases, pinning a release and testing upgrades before merging is the only reliable strategy.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Zephyr vs NuttX vs RIOT OS in 2026: Which Open-Source RTOS Should You Actually Ship?",
  "description": "Hands-on 2026 comparison of Zephyr, Apache NuttX and RIOT OS: build systems, footprint, board support, networking stacks, CI tooling and migration pitfalls.",
  "datePublished": "2026-09-23",
  "dateModified": "2026-09-23",
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
