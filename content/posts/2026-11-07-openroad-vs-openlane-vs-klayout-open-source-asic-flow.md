---
title: "OpenROAD vs OpenLane vs KLayout in 2026: The Open-Source Chip Design Stack Compared"
date: "2026-11-07"
tags: ["open-source-eda", "chip-design", "asic", "hardware", "developer-tools"]
draft: false
cover: "/img/screenshots/openroad-ibex-floorplan.jpg"
---

A single 5nm mask set costs more than $15 million. That number is why most hardware startups never see their own silicon. But the economics changed at the older nodes: with an open PDK such as SkyWater SKY130 or GlobalFoundries GF180MCU, a small team can push real RTL through place-and-route, DRC, LVS and stream out a GDSII file for a few thousand dollars in shuttle fees. The toolchain that makes this possible is fully open source — and it is the same stack used on silicon that has actually shipped.

The confusion starts with the names. **OpenROAD**, **OpenLane** and **KLayout** get compared in the same breath, yet they do different jobs: OpenROAD is the place-and-route engine and flow infrastructure, OpenLane is a turnkey wrapper that chains OpenROAD with Yosys, Magic and KLayout, and KLayout is the layout editor and verification toolkit you open when something looks wrong. Picking the wrong one wastes weeks.

## TL;DR: Quick Verdict

- **You have RTL and want a GDSII file with the least setup friction** → use **OpenLane** (or the OpenROAD-flow-scripts image it wraps). One `make`, one design config, one command.
- **You want scriptable control, CI integration, or a custom flow** → use **OpenROAD / OpenROAD-flow-scripts** directly. It is the engine, and the Makefile-based flow is what you want in a pipeline.
- **You need to inspect a GDS, write DRC/LVS decks, or hand-edit a cell** → use **KLayout**. It is not a replacement for a place-and-route flow, and treating it as one is the single most common beginner mistake.

If you only remember one line: **OpenLane is the product, OpenROAD is the engine, KLayout is the microscope.**

## Side-by-Side Comparison

All statistics below were pulled from GitHub on 2026-11-07.

| Dimension | OpenROAD | OpenLane | KLayout |
|---|---|---|---|
| Primary role | RTL-to-GDS engine + flow scripts | Turnkey automated flow | Layout editor, GDS/OASIS viewer, DRC/LVS scripting |
| GitHub stars | 3,263 | 1,999 | 1,255 |
| License | BSD-3-Clause | Apache-2.0 | GPL-3.0 |
| Last push | 2026-11-07 | 2026-03-25 | 2026-11-05 |
| Language / scripting | C++ core, Tcl + Python bindings | Tcl (1.x), Python (2.x) | C++ core, Ruby + Python + Qt |
| Container image | `openroad/orfs` | `efabless/openlane` | Distro packages, AppImage |
| Learns fastest if you… | know Tcl/Make and want control | want a working GDS today | need to debug layouts visually |
| Weak spot | you assemble the flow yourself | thinner maintenance cadence | no place-and-route |
| Best fit | custom flows, research, CI | first tapeout, fixed flows | verification, mask prep, DRC decks |

OpenROAD's commit history is the liveliest of the three — a push on the day this article was written — while OpenLane's last push (2026-03-25) reflects its shift toward the Python-based OpenLane 2 line and Nix packaging. That difference matters when you are choosing what to depend on for the next two years.

## Decision Matrix: Pick by Situation

| Your situation | Recommended tool | Why |
|---|---|---|
| First ASIC attempt, SKY130 or GF180, deadline in weeks | OpenLane | Design config in JSON, `./flow.tcl -design <name>` and it runs the whole chain |
| Existing RTL, need repeatable CI builds | OpenROAD-flow-scripts | Makefile targets, pinned container tag, per-design `config.mk` |
| Debugging DRC violations after a run | KLayout | Fast viewer, marker browser, scriptable rule decks |
| Writing a custom DRC deck for a new PDK | KLayout | Ruby/Python API for region operations |
| Analog or custom digital cell layout | KLayout + Magic | Magic handles extraction; KLayout handles viewing and DRC |
| Academic paper / reproducible experiment | OpenROAD + ORFS | Deterministic flow with versioned configs |
| Just need to convert or merge GDS files | KLayout | `klayout -b -r script.py`, no GUI required |

## OpenROAD: The Engine Under Everything

OpenROAD is a unified application that performs floorplanning, placement, clock tree synthesis, routing and timing analysis, exposed through Tcl commands and a Python API. The companion repository, **OpenROAD-flow-scripts (ORFS)**, is the piece you actually install: it wires OpenROAD together with Yosys for synthesis, plus KLayout and Magic for the final checks.

The documented way to start is the prebuilt container, which avoids the dependency spiral of building Boost, Qt and the rest from source:

```bash
# Pull the flow image (includes OpenROAD, Yosys, KLayout, Magic)
docker pull openroad/orfs

# Run it with your flow directory mounted, as your own UID
cd ~/OpenROAD-flow-scripts
docker run --rm -it \
  -u $(id -u ${USER}):$(id -g ${USER}) \
  -v $(pwd)/flow:/OpenROAD-flow-scripts/flow \
  openroad/orfs
```

Inside the container, a full RTL-to-GDS run is a single `make` invocation driven by a per-design `config.mk`:

```bash
cd /OpenROAD-flow-scripts/flow

# Run the gcd example on the Nangate45 platform
make DESIGN_CONFIG=./designs/nangate45/gcd/config.mk
```

A minimal `config.mk` for your own design looks like this — this is the entire contract between your RTL and the flow:

```make
export DESIGN_NAME = my_block
export PLATFORM    = sky130hd

export VERILOG_FILES = $(DESIGN_HOME)/src/my_block/my_block.v
export SDC_FILE      = $(DESIGN_HOME)/src/my_block/constraint.sdc
export CORE_UTILIZATION = 40
export PLACE_DENSITY    = 0.60
```

Two things make OpenROAD attractive for teams rather than individuals. First, every stage is individually addressable: `make floorplan`, `make place`, `make cts`, `make route`, `make finish`, so a failure at detailed routing does not force you to rerun synthesis. Second, the metrics land in machine-readable reports, which means you can gate merges on WNS, DRC count or area instead of eyeballing a log.

![Ibex RISC-V core floorplan produced by the OpenROAD flow](/img/screenshots/openroad-ibex-floorplan.jpg "OpenROAD floorplan of the Ibex RISC-V core, from the official repository")

The screenshot above is the flow's own output for the Ibex RISC-V core: placement density, macro placement and pin access are all visible. When people say "open-source EDA looks like a real tool now," this is what they mean.

The trade-off is real. ORFS assumes you understand Make, Tcl and the concept of a platform directory. Its error messages are precise but unforgiving, and a missing `SDC_FILE` produces a failure three stages later rather than at parse time.

## OpenLane: The Turnkey Flow

OpenLane exists because most people do not want to assemble a flow. It bundles OpenROAD, Yosys, Magic, Netgen, KLayout, a SPEF extractor and a set of methodology scripts into one automated RTL-to-GDSII pipeline with a single entry point.

The documented installation is deliberately boring:

```bash
cd $HOME
git clone https://github.com/The-OpenROAD-Project/OpenLane
cd OpenLane
make        # builds the container environment
make test   # runs the smoke test
make mount  # drops you into the flow environment
```

Once mounted, hardening a design is one command:

```bash
./flow.tcl -design spm
```

That runs synthesis, floorplan, placement, CTS, routing, parasitics extraction, STA and the signoff checks for the bundled `spm` design, producing a GDSII plus a full report tree. For a design of your own, you add a directory under `designs/` with a `config.json`:

```json
{
  "DESIGN_NAME": "my_block",
  "VERILOG_FILES": "dir::src/*.v",
  "CLOCK_PORT": "clk",
  "CLOCK_PERIOD": 10.0,
  "FP_CORE_UTIL": 40,
  "PL_TARGET_DENSITY": 0.6
}
```

The value proposition is speed to first silicon. The JSON config is smaller than an equivalent `config.mk`, the defaults are sane for SKY130, and the reports are pre-rendered into something a non-specialist can read. If your goal is "I have never taped out before and want to see a GDS this month," OpenLane is the shortest path.

The caveat is project trajectory. OpenLane 1.x lives in Tcl and carries a lot of historical methodology; the 2.x rewrite moved to Python with Nix-based reproducibility, and the repository's last push in March 2026 signals that the classic line is in maintenance rather than active development. Pin a container tag, and do not build a five-year strategy on the Tcl interface.

![Final GDSII layout generated by the OpenLane flow](/img/screenshots/openlane-final-gds.jpg "Final GDSII layout of a hardened design, from the OpenLane documentation")

## KLayout: The Microscope, Not the Flow

KLayout is a GDSII/OASIS viewer and editor with a serious scripting engine. It will open a 10 GB layout in seconds, compute boolean operations on millions of polygons, run DRC decks written in Ruby or Python, and stream out mask data. What it will not do is place and route your design.

Ubuntu and Debian users get it from the archive; Python users can also drive it headlessly through the `klayout` module:

```bash
sudo apt install klayout

# Or the Python bindings, useful for CI-side GDS checks
pip install klayout
```

A headless DRC or geometry script is where KLayout earns its place in a pipeline — this runs without a GUI and exits non-zero on violations:

```python
import klayout.db as db

layout = db.Layout()
layout.read("results/final/gds/my_block.gds")
top = layout.top_cell()

# Example check: find all shapes on the metal1 layer smaller than 0.14 um
m1 = layout.layer(68, 20)
region = db.Region(top.begin_shapes_rec(m1))
too_small = region.sized(-0.07).sized(0.07)
print(f"violations: {too_small.count()}")
```

For analog and custom digital work, KLayout is normally paired with **Magic VLSI** (729 stars, last push 2026-11-06). Magic handles interactive layout and parasitic extraction, KLayout handles viewing, DRC and file conversion. Neither replaces OpenROAD for automated place-and-route, and OpenROAD does not replace either for hand-drawn cells.

## Pitfalls That Cost Real Weeks

**1. PDK access is the actual gate, not the tools.** SKY130 and GF180MCU are open, and IHP's SG13G2 is available under an open-ish process design kit. Advanced-node PDKs are not. Teams burn weeks installing OpenROAD before discovering they cannot legally obtain the deck they need.

**2. Memory is the silent failure.** A modest 100k-instance design can push detailed routing past 32 GB. If the container dies with no message, check `dmesg` for the OOM killer before you debug the flow.

**3. Docker bind mounts on macOS are slow enough to look like a hang.** ORFS reads and writes thousands of small files. Run on Linux, or on macOS use a named volume for the flow directory — a 4x slowdown on the wrong filesystem is common.

**4. OpenLane 1.x and 2.x configs are not interchangeable.** The Tcl config keys and the Python configuration schema diverge. Decide which line you are on and pin the image tag in your own CI.

**5. KLayout's DRC decks are PDK-specific and unofficial by default.** Running a generic rule file against SKY130 produces false violations. Use the deck shipped with the PDK (usually in `libs.tech/klayout`), not a random script from a tutorial.

**6. Do not skip LVS.** A clean DRC run means the geometry is legal, not that the netlist matches your RTL. Netgen-based LVS in the OpenLane flow is the step that catches a swapped pin before you pay for a shuttle slot.

**7. Signoff claims need context.** The open flow closes timing on open PDKs at 130 nm and 180 nm. Treat results at advanced nodes as research, not as production signoff.

If you are also setting up the server side of a hardware lab, our guides to the [open-source FPGA toolchain with Yosys, iverilog and nextpnr](../2026-06-07-open-source-fpga-development-toolchain-yosys-iverilog-ghdl-nextpnr/) and to [hardware verification with cocotb, VUnit and UVM](../2026-11-07-cocotb-vs-vunit-vs-uvm-hardware-verification-frameworks/) cover the two steps that come before place-and-route. For teams building minimal immutable images to run CI runners for this kind of workload, the [unikernel comparison](../2026-06-04-self-hosted-unikernel-platforms-unikraft-nanos-includeos-mirageos-guide/) is a useful complement.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenROAD vs OpenLane vs KLayout in 2026: The Open-Source Chip Design Stack Compared",
  "description": "A practical 2026 comparison of the open-source ASIC design stack: OpenROAD as the RTL-to-GDS engine, OpenLane as the turnkey flow, and KLayout as the layout editor and DRC toolkit, with real install commands, configs and pitfalls.",
  "datePublished": "2026-11-07",
  "dateModified": "2026-11-07",
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

**Can I really tape out a chip with only open-source tools?**
Yes, at open nodes. The OpenROAD/OpenLane stack has been used for SKY130 and GF180MCU shuttle runs, including RISC-V cores. The toolchain is not the blocker — the PDK, the shuttle slot and the verification effort are.

**Do I need KLayout if I use OpenLane?**
Not to run the flow, but you will want it the first time a DRC violation appears. OpenLane calls KLayout internally for stream-out and some checks; having the GUI available turns a cryptic marker file into a visual debug session.

**Is OpenLane abandoned?**
No, but the classic Tcl-based 1.x line is in maintenance, with the last repository push in March 2026. Active development moved to the Python/Nix-based OpenLane 2. Pin a tag either way.

**How much RAM does place-and-route need?**
Plan on 16 GB for small designs on SKY130, 32 GB for anything with hundreds of thousands of instances, and more for large macros or wide datapaths. Detailed routing is the stage that spikes.

**Which one should a beginner learn first?**
OpenLane. You get a complete GDS and a report tree without learning the flow's internals. Move to OpenROAD-flow-scripts when you need to change how a stage runs, and to KLayout when you need to see why.

**Does OpenROAD work on Apple Silicon?**
The container runs under emulation, which is functional but slow enough to be frustrating for real designs. Linux x86-64 or a remote build host is the practical choice.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
