---
title: "LVGL vs Slint vs Nuklear in 2026: Which Embedded GUI Toolkit Should You Actually Use?"
date: "2026-10-16"
tags: ["embedded", "gui-toolkits", "lvgl", "slint", "c-plus-plus", "rust", "developer-tools"]
draft: false
cover: "/img/screenshots/lvgl-ui.jpg"
---

Your device ships with a 320x240 display, 256 KB of RAM, and a project manager who wants the UI done yesterday. On the proprietary side, TouchGFX, emWin and Crank Storyboard all want per-seat licenses and NDA paperwork before you can read the docs. On the open side, three toolkits dominate every forum thread: **LVGL**, **Slint** and **Nuklear**. Picking wrong costs you months — a widget set that cannot fit your memory budget, or a project that stopped receiving commits in 2020.

This guide compares the three with live repository data, real code from each project's own README, and an honest verdict on which one to bet on in 2026.

## Quick Verdict (TL;DR)

- **Pick LVGL** if you have a classic MCU, a framebuffer or any RTOS, and you want the largest widget set plus third-party visual designers. It is the safe default and the most actively maintained of the three.
- **Pick Slint** if you are building an MPU-class device (Linux, Yocto, embedded Linux) and your team writes Rust, C++, or JavaScript. Its declarative markup plus live-preview tooling is the fastest path from design to pixels.
- **Pick Nuklear only for maintenance** of an existing single-header project. Its last commit was **January 2020** — as a fresh 2026 dependency it is a liability, not a choice.
- **Consider GuiLite** if you need the absolute smallest header-only footprint (about 4 KLOC) and you are willing to trade away widget richness.

## Feature and Health Comparison (live data, October 2026)

| Toolkit | GitHub stars | Last commit | Language | License model | Rendering model | Visual designer |
|---|---|---|---|---|---|---|
| **LVGL** | 24,926 | 2026-10-16 | C (any C99 toolchain) | MIT | Retained-mode object tree | LVGL Pro, SquareLine, EEZ Studio |
| **Slint** | 24,196 | 2026-10-16 | Rust, C++, JS, Python | GPLv3 or commercial | Declarative, compiled to native | Slint live-preview, Figma plugin |
| **Nuklear** | 13,972 | 2020-01-03 | Single-header ANSI C | Public domain / MIT | Immediate-mode | None |
| **GuiLite** | 7,778 | 2025-10-22 | Header-only C++ | Permissive (see repo) | Retained, minimal | None |

Two numbers should decide the argument for most teams: LVGL and Slint are both around **24,000 stars** with commits landing *today*, while Nuklear has been frozen for over six years. Star counts are not quality, but commit recency is a maintenance contract — and Nuklear's contract expired.

## Decision Matrix: Match the Toolkit to the Job

| Your situation | Recommended toolkit | Why |
|---|---|---|
| Cortex-M MCU, 64-256 KB RAM, no OS | LVGL | Smallest sensible RAM footprint with a real widget set; runs on bare metal or FreeRTOS |
| Embedded Linux / Yocto device, Rust team | Slint | Compiles to native code, GPU or software renderer, markup separates design from logic |
| Yocto device with a C++-only team | Slint (C++ API) | Same declarative UI, no Rust requirement in application code |
| Legacy single-header project you inherited | Nuklear | Rewriting working code is not a priority; pin the version and vendor it |
| Watch-class UI, tiny flash budget | GuiLite or LVGL | GuiLite is ~4 KLOC; LVGL can be trimmed via config macros |
| Dashboard needing charts, tables, animations | LVGL | Chart, table, animation and image-decoder widgets ship in-tree |
| Design-driven workflow with Figma handoff | Slint | Official Figma plugin plus live preview from the markup file |

## LVGL: The Pragmatic Default

LVGL (Light and Versatile Graphics Library) is a retained-mode C library: you build a tree of objects, and the library redraws invalidated regions. It runs on bare-metal MCUs, RTOS targets, and Linux framebuffer devices, and upstream describes it as covering *"devices from small MCUs to 3D-capable MPUs."*

A button with a callback and a label, straight from the project README:

```c
static void button_clicked_cb(lv_event_t * e)
{
    printf("Clicked\n");
}

/* ... */

lv_obj_t * button = lv_button_create(lv_screen_active());
lv_obj_center(button);
lv_obj_add_event_cb(button, button_clicked_cb,
                    LV_EVENT_CLICKED, NULL);

lv_obj_t * label = lv_label_create(button);
lv_label_set_text(label, "Hello from LVGL!");
```

Since LVGL 9, the same UI can be declared in XML and loaded at runtime — useful when a designer, not a firmware engineer, owns the layout:

```xml
<screen>
  <view>
    <lv_button align="center">
      <event_cb callback="button_clicked_cb" />
      <lv_label text="Hello from LVGL!" />
    </lv_button>
  </view>
</screen>
```

A typical board bring-up is three calls after you wire the display flush callback:

```c
#include "lvgl/lvgl.h" /*Define LV_LVGL_H_INCLUDE_SIMPLE to include as "lvgl.h"*/

#define TFT_HOR_RES 320
#define TFT_VER_RES 240

lv_init();
/* lv_display_create(TFT_HOR_RES, TFT_VER_RES) + flush callback */
/* lv_tick_inc(1) from a 1 ms timer, then lv_timer_handler() in your main loop */
```

The practical reason to choose LVGL is the ecosystem. Commercial and free visual editors (LVGL Pro, SquareLine Studio, EEZ Studio) emit code against the same API, and the widget catalogue — charts, tables, spinners, calendars, plus SDL, framebuffer and driver backends — means you rarely write a widget from scratch. The trade-off is that LVGL expects you to own the porting layer: display flush, input read, tick source. On a well-documented board that is an afternoon; on an undocumented panel controller it is a week.

## Slint: Declarative UI That Compiles to Native Code

Slint takes the opposite philosophy. You write `.slint` markup, and a compiler turns it into native code for Rust, C++, JavaScript or Python. There is no interpreter and no runtime tree walking in the hot path — the generated code draws what the markup describes.

From the official README:

```slint
export component HelloWorld inherits Window {
    width: 400px;
    height: 400px;

    Text {
       y: parent.width / 2;
       x: parent.x + 200px;
       text: "Hello, world";
       color: blue;
    }
}
```

Two workflow details make Slint attractive on MPU-class hardware. First, **live preview**: the `slint-viewer` re-renders as you type, and can be pointed at a debug build running on the target so the device UI updates live over the network. Second, the **Figma plugin** exports designs directly to `.slint`, which removes the hand-translation step that usually rots within a sprint.

![Slint live design preview with a running target device](/img/screenshots/slint-ui.jpg)

The honest caveats: the licensing is **GPLv3 or commercial**, so closed-source products need either compliance work or a paid license — budget for that conversation before you commit. Slint's sweet spot is Linux-class hardware (Yocto, Buildroot, Debian) where you have hundreds of megabytes of RAM and a real GPU or a fast software renderer. On a 64 KB MCU with no FPU, LVGL remains the more realistic option.

## Nuklear: Excellent Design, Frozen Maintenance

Nuklear is a single-header ANSI C immediate-mode library. Immediate-mode means you rebuild the UI every frame in code: no retained object tree, no callbacks, no allocation policy to fight. For tool panels, debug overlays and internal tools, it is genuinely pleasant — drop one header into your project and draw.

The problem is not the design, it is the calendar. **The last commit to `vurtun/nuklear` was on 2020-01-03.** In 2026 that means no CVE triage, no support for newer compilers and sanitizers without your own patches, and no upstream answer when the renderer misbehaves on a new panel. Using it for new firmware means you are effectively forking a library and inheriting maintainership.

There is a reasonable middle path: many teams use a *fork or re-implementation* that is actively maintained, while treating upstream as a reference implementation. If you go that route, vendor the code into your tree (single header makes this trivial), pin a commit hash, and add it to your dependency review — do not let a package manager silently resolve a 2020 snapshot.

## GuiLite: The Footprint Minimalist

GuiLite sits at the other end of the spectrum from LVGL's feature list. It is a header-only C++ library of roughly **4,000 lines** and 7,778 stars, aimed at "all platforms" with the smallest possible footprint. For a monochrome status display, a watch face, or a device where every kilobyte of flash is negotiated, that minimalism is the feature. What you give up is depth: fewer widgets, fewer third-party tools, and a smaller community answering questions. It is a strong fit for a narrow problem and a poor fit for a general-purpose product UI.

## Migration and Deployment Traps

**Do not trust RAM figures from blog posts.** Measure. LVGL's memory use depends on your `lv_conf.h`: colour depth, font files, and the draw buffer size dominate. A 16-bit colour depth with two full-screen buffers can consume more RAM than the application logic.

**Pin your toolkit version.** Every one of these projects changes API surface between minor releases — LVGL 8 to 9 moved from `lv_scr_act()` to `lv_screen_active()` and dropped several legacy widget names. Vendoring the source (all four are vendorable) turns an upgrade into a deliberate, reviewable diff.

**Treat the tick source as a correctness bug, not a detail.** If your millisecond tick drifts, animations stutter and timeouts fire late. On MCUs, drive it from a hardware timer interrupt and verify with a logic analyser before blaming the toolkit.

**Budget the designer handoff early.** Teams that adopt a visual editor late usually have a generated-code layer nobody owns. Decide up front whether the markup is the source of truth (Slint, LVGL XML) or whether designers export and engineers refactor.

**Check the licence against your shipping model.** MIT (LVGL) and the permissive GuiLite terms are easy. Slint's GPLv3 means closed firmware needs a commercial licence; that is a procurement task, not an engineering one, and it belongs on the schedule before the first sprint.

For related reading in this stack, see our [comparison of embedded build toolchains](../2026-10-16-embedded-build-toolchains-platformio-esp-idf-arduino-cli-comparison/) and the guide to [embedded scripting engines](../2026-06-22-embedded-scripting-engines-duktape-quickjs-jerryscript-cpp/). If you are bringing up a Linux-class board instead of bare metal, the [embedded Linux build guide](../2026-06-05-embedded-linux-build-yocto-buildroot-openembedded-guide/) covers Yocto and Buildroot.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "LVGL vs Slint vs Nuklear in 2026: Which Embedded GUI Toolkit Should You Actually Use?",
  "description": "Hands-on comparison of LVGL, Slint, Nuklear and GuiLite for embedded MCU and MPU user interfaces, with live repository data, real code from official READMEs, decision matrix and migration traps.",
  "datePublished": "2026-10-16",
  "dateModified": "2026-10-16",
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

**Is LVGL fast enough for a 240 MHz Cortex-M4 with a 320x240 SPI display?**

Yes, with the right buffer strategy. Use a partial draw buffer sized to a few display lines plus DMA, and let LVGL redraw only invalidated areas. The bottleneck is almost always the SPI flush, not the widget tree — measure the flush time first.

**Can Slint run on a microcontroller without an operating system?**

There is an official MCU build path, but it targets "microcontroller-class" hardware with a proper software renderer and is more restrictive than LVGL on very small devices. For a 64 KB RAM target with no FPU, LVGL is the lower-risk choice; Slint's advantage grows with available RAM and CPU.

**Should I use Nuklear for a new project in 2026?**

Only if you accept maintainership. Upstream's last commit is January 2020, so you would be adopting a frozen dependency. For new firmware, LVGL or Slint have active release trains and security review; if you like the immediate-mode model, use a maintained fork and vendor a pinned commit.

**Is Slint really free for commercial products?**

Slint is dual-licensed: GPLv3, or a commercial licence for closed-source use. Shipping proprietary firmware without disclosing source under GPLv3 requires the commercial licence — decide this before design work, because switching licences after the fact is expensive.

**Which toolkit handles animations and charts with the least code?**

LVGL. Charts, tables, gradients, animations and image decoders ship in-tree, so a dashboard is mostly object configuration rather than custom drawing. Slint's animation syntax is cleaner for hand-written transitions, but its widget catalogue is narrower.

**How do I keep any of these from bloating my flash image?**

Vendor the source, then compile with a trimmed configuration: LVGL reads `lv_conf.h` (disable unused fonts, colour depths and widgets), Slint's compiler strips unused markup, and the single-header libraries only cost what you instantiate. Measure the linked binary, not the library size on disk.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
