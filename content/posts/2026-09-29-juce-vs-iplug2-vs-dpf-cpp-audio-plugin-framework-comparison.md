---
title: "JUCE vs iPlug2 vs DPF in 2026: Which C++ Audio Plug-in Framework Should You Actually Use?"
date: "2026-09-29"
tags: ["audio", "cpp", "plugin-development", "developer-tools", "cmake"]
draft: false
---

Shipping an audio plug-in that has to load inside Ableton Live, Logic Pro, Reaper and Bitwig means exporting three or four plug-in formats, building on three operating systems, and keeping real-time DSP code free of locks and allocations. The framework you choose in week one decides whether that stays manageable or turns into two years of rework. JUCE, iPlug2 and DPF all solve the same core problem — one C++ codebase, many plug-in formats — but they optimise for very different teams. JUCE targets commercial products that want every format plus a deep widget library. iPlug2 targets fast iteration and permissive licensing. DPF targets lean, Linux-first plug-ins that ship LV2 and CLAP without ceremony.

This guide compares the three on licence terms, format coverage, build systems, GUI options and real-world trade-offs, with **live GitHub numbers as of September 29, 2026**.

## TL;DR: The Quick Verdict

**Pick JUCE** if you are building a commercial plug-in and can accept AGPLv3-or-paid licensing — it has the widest format coverage (VST3, AU, AUv3, AAX, LV2, standalone), the largest community and the biggest hiring pool. **Pick iPlug2** if you want the fastest build-iterate loop, desktop plus AUv3 iOS plus web (WAM) from one codebase, and a permissive licence that explicitly allows commercial use. **Pick DPF** if you are shipping open-source, Linux-friendly plug-ins (LADSPA, DSSI, LV2, VST2, VST3, CLAP) and care about a tiny dependency footprint and an ISC licence.

Short version: **JUCE for products, iPlug2 for prototypes and cross-platform reach, DPF for open-source Linux plug-ins.** If you have no budget and you intend to keep your source closed, cross JUCE off the list before you write a single line.

## JUCE vs iPlug2 vs DPF at a Glance

| Dimension | JUCE | iPlug2 | DPF |
|---|---|---|---|
| GitHub stars | **8,935** | **2,418** | **869** |
| Last commit | 2026-09-28 | 2026-09-15 | 2026-09-28 |
| Licence | AGPLv3 **or** commercial | Permissive (zlib-style) | ISC |
| Export formats | VST3, AU, AUv3, AAX, LV2, standalone | VST3, AU, AUv3, AAX, web (WAM), standalone | LADSPA, DSSI, LV2, VST2, VST3, CLAP, JACK/standalone |
| GUI toolkit | Built-in widget set | IGraphics (NanoVG or Skia) | Cairo, OpenGL, custom |
| Build system | CMake 3.22+, Projucer | Xcode/VS projects, out-of-source template, CI containers | Makefile and CMake |
| Repo | `juce-framework/JUCE` | `iPlug2/iPlug2` | `DISTRHO/DPF` |
| Best for | Commercial products, hiring, tutorials | Fast iteration, web + iOS from one codebase | Open-source Linux plug-ins, minimal deps |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended | Why |
|---|---|---|
| Commercial closed-source plug-in, licence budget available | **JUCE** | Broadest format coverage, mature widget library, commercial licence clears AGPLv3 obligations |
| Open-source hobby plug-in, want it in the Linux audio stack | **DPF** | LV2/CLAP/LADSPA are first-class, ISC licence, almost no dependencies |
| Need iOS AUv3 plus desktop plus a web build | **iPlug2** | Single codebase with NanoVG/Skia graphics, WAM target in the same repo |
| Smallest possible shipping binary | **DPF** | No widget framework drag, formats are thin wrappers |
| Fastest path to a polished custom UI | **JUCE** or **iPlug2** | JUCE ships widgets; iPlug2's IGraphics controls are plug-in shaped |
| Team hires plug-in developers with existing experience | **JUCE** | Largest ecosystem and the most published tutorials |
| Format coverage including AAX and Pro Tools | **JUCE** or **iPlug2** | Both export AAX; signing tools come from Avid |
| Vintage format support (DSSI, VST2, LADSPA) | **DPF** | The others dropped or never shipped those formats |

## JUCE — The Commercial Standard (8,935 stars)

JUCE is a full application framework that happens to be excellent at audio plug-ins. Its `juce::AudioProcessor` handles host callbacks, parameter automation, state save/restore and bus layouts; `juce::AudioProcessorEditor` gives you a widget set that already looks like a plug-in.

The licensing is the decision that matters. JUCE is dual-licensed **AGPLv3 or commercial**. AGPLv3 works if your plug-in is open source under a compatible licence; a closed-source binary shipped to customers requires the commercial licence. Read `LICENSE.md` in the repository before you plan a product.

Building with CMake is straightforward — the official README documents this exact flow, and CMake 3.22 or newer is required:

```bash
git clone https://github.com/juce-framework/JUCE.git
cd JUCE
cmake . -B cmake-build -DJUCE_BUILD_EXAMPLES=ON -DJUCE_BUILD_EXTRAS=ON
cmake --build cmake-build --target DemoRunner
```

For your own plug-in, the CMake API is the modern path. A minimal plug-in target looks like this:

```cmake
cmake_minimum_required(VERSION 3.22)
project(MyPlugin VERSION 1.0.0)

add_subdirectory(JUCE)

juce_add_plugin(MyPlugin
    COMPANY_NAME "Example Audio"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    PLUGIN_MANUFACTURER_CODE Exam
    PLUGIN_CODE Mypl
    FORMATS AU VST3 Standalone)

target_sources(MyPlugin PRIVATE Source/PluginProcessor.cpp Source/PluginEditor.cpp)
target_compile_definitions(MyPlugin PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
```

The `Projucer` is still supported and generates Xcode, Visual Studio, Android Studio and Linux Makefile projects from a single configuration file — genuinely useful if your team is not CMake-native.

**Where JUCE wins:** format breadth, a huge library of community tutorials, and a hiring market where "JUCE developer" already means something. **Where it hurts:** the licence obligation, a heavier dependency footprint, and a plugin GUI that can drift towards looking like every other JUCE plug-in unless you invest in custom design.

## iPlug2 — Fast Iteration with a Permissive Licence (2,418 stars)

iPlug2 splits the problem in two: `IPlug` abstracts the plug-in host and formats, and `IGraphics` abstracts the drawing backend, which can be **NanoVG** or **Skia** — both GPU-accelerated and HiDPI-aware. That separation is why the same DSP layer can sit under a C++ UI, an HTML/CSS layer on the web, or SwiftUI on Apple platforms.

Its licence is a permissive, zlib-style grant: permission to use the software for any purpose, **including commercial applications**, with attribution conditions. If AGPLv3 is a blocker and you still want iOS plus web coverage, this is the pragmatic answer.

The recommended 2025-onward workflow is the out-of-source template, which keeps dependencies pinned in your own repository and is designed for container-based development and cloud CI:

```bash
git clone https://github.com/iPlug2/iPlug2OOS.git --recursive
cd iPlug2OOS
git submodule update --init --recursive
```

The template ships VSCode dev-container configuration and GitHub Codespaces support, so a collaborator can open the repo and build without hand-installing SDKs. The in-repo `Examples/IPlugEffect` project remains the canonical "hello world" and the fastest way to read real DSP plus UI code side by side.

A plug-in skeleton follows a consistent shape — host callbacks are virtuals you override:

```cpp
#include "IPlug_include_in_plug_hdr.h"

class IPlugEffect final : public iplug::Plugin
{
public:
  IPlugEffect(IPlugInstanceInfo instanceInfo);
  void OnReset() override;
  void OnParamChange(int paramIdx) override;
  void ProcessBlock(sample** inputs, sample** outputs, int nFrames) override;
};
```

**Where iPlug2 wins:** iteration speed, permissive licensing, one codebase across desktop, AUv3 and web, and a graphics layer that gives you vector UI without dragging in a full application framework. **Where it hurts:** a smaller community than JUCE, thinner third-party documentation, and fewer ready-made commercial UI patterns — expect to write more of your own controls.

## DPF — Minimal Footprint, Maximum Format Coverage (869 stars)

DPF (DISTRHO Plugin Framework) is designed so that "new plug-in" is a small task: subclass `Plugin`, implement DSP and optional UI, and let the framework export LADSPA, DSSI, LV2, VST2, VST3 and CLAP plus a JACK/standalone mode from the same source.

It is ISC-licensed, which is about as permissive as it gets — use it, modify it, sell products built with it, keep the copyright notice. For Linux audio developers it is often the only framework that covers vintage formats and modern ones in one build.

Both a Makefile workflow and a CMake workflow are maintained in CI. Building the framework and its example plug-ins:

```bash
git clone --recursive https://github.com/DISTRHO/DPF.git
cd DPF
make
```

Per-plug-in configuration is deliberately plain — a `Makefile` names the DSP and UI translation units:

```make
NAME = MyPlugin
FILES_DSP = MyPlugin.cpp
FILES_UI  = MyPluginUI.cpp
```

And the DSP side is a small, explicit interface:

```cpp
#include "DistrhoPlugin.hpp"

START_NAMESPACE_DISTRHO

class MyPlugin : public Plugin
{
public:
    MyPlugin() : Plugin(3, 0, 0) {}   // 3 parameters, no states, no programs

protected:
    void initParameter(uint32_t index, Parameter& parameter) override;
    void run(const float** inputs, float** outputs, uint32_t frames) override;
};

END_NAMESPACE_DISTRHO
```

UI-to-DSP communication uses key-value string messages that the host persists when required, which keeps state handling simple and avoids a bespoke serialisation layer.

**Where DPF wins:** format coverage per line of code, ISC licensing, tiny binaries, and honest Linux-first design. **Where it hurts:** the widget toolkit is minimal (Cairo or OpenGL, plus examples), the community is small, and there is far less tutorial material than for JUCE — you will read framework sources.

## Common Pitfalls When Choosing an Audio Plug-in Framework

- **Licence contamination is the expensive mistake.** AGPLv3 is a strong copyleft: if you ship a closed-source binary built on JUCE without the commercial licence you are exposed. Check `LICENSE.md`, then check your legal position, before building a product roadmap.
- **Do not allocate, lock or log in the audio callback.** All three frameworks hand you a real-time thread. Build a lock-free queue between UI and DSP, preallocate buffers in `OnReset`/`init`, and never call `new`, `printf` or a mutex in the process block.
- **Sample-rate and block-size assumptions break in the field.** Hosts choose block sizes from 16 to 4096 frames and sample rates from 44.1 kHz to 192 kHz. Test with an offline render at a non-44.1 kHz rate before you ship; denormal handling matters here too.
- **AAX signing is a separate toolchain.** Pro Tools AAX builds need Avid's signing tools and a valid certificate; budget extra release time for that path regardless of framework.
- **Cross-format state compatibility.** If you ship VST3 and AU versions of the same product, users will expect presets to move between them. Version your state structure from day one.
- **Test in more than one host.** `pluginval` plus at least two DAWs (Reaper and Bitwig are common references) catches most automation and bus-layout bugs; macOS users should also run `auval`.
- **Web and iOS targets are not free.** iPlug2's WAM and AUv3 targets work, but expect to debug platform-specific UI behaviour that never appears on desktop.

For deeper background on the surrounding stack, see our guides to [audio processing libraries like PortAudio, miniAudio and OpenAL Soft](../2026-06-20-self-hosted-audio-processing-libraries-portaudio-miniaudio-openal-soft/), [Python audio libraries for DSP prototyping](../2026-08-02-python-audio-processing-libraries-pydub-librosa-soundfile/), and [MIDI network routing with rtpmidid, QMidiNet and JACK](../2026-06-05-self-hosted-midi-network-routing-rtpmidid-qmidinet-jack-matchmaker-guide/).

## FAQ

**Is JUCE free for commercial plug-ins?**
JUCE is dual-licensed under AGPLv3 or a paid commercial licence. Open-source projects using a compatible licence can use it at no cost. If you distribute a closed-source binary commercially, you need the commercial licence — confirm the current terms in the repository's `LICENSE.md` and the vendor's site before shipping.

**Can all three frameworks export VST3 and AU from one codebase?**
Yes. JUCE and iPlug2 export VST3, AU and AUv3 (plus AAX and standalone). DPF is the odd one out for Apple formats — it targets LADSPA, DSSI, LV2, VST2, VST3, CLAP and JACK on Linux first, which is exactly why Linux audio developers like it.

**Which framework is best for LV2 and CLAP plug-ins?**
DPF. Both formats are first-class exports, the licence is ISC, and the dependency footprint is small. JUCE's LV2 story is weaker and CLAP typically requires an additional compatibility layer.

**Do I have to use the framework's GUI toolkit?**
No. All three separate DSP from UI to some degree. iPlug2's `IGraphics` can host HTML/CSS or SwiftUI; DPF lets you write a Cairo or OpenGL view and even a standalone GUI; JUCE lets you build an `AudioProcessorEditor` with custom painting, though you will usually still use its component model.

**How do I test a plug-in across hosts without buying every DAW?**
Start with `pluginval` for automated VST3/AU validation, then test in two free or inexpensive DAWs with different architectures (one that renders offline aggressively, one that streams). On macOS, run `auval` for the Audio Unit build and check both Intel and Apple silicon binaries.

**Which framework should a beginner choose?**
JUCE if you want the most tutorials, videos and answered forum threads. DPF if you want to understand every line of what you ship and you are building for Linux. iPlug2 if you already know C++ and want a permissive licence without giving up format coverage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JUCE vs iPlug2 vs DPF in 2026: Which C++ Audio Plug-in Framework Should You Actually Use?",
  "description": "A hands-on comparison of JUCE, iPlug2 and DISTRHO Plugin Framework for C++ audio plug-in development in 2026: licences, export formats, build systems, GUI toolkits and real code examples.",
  "datePublished": "2026-09-29",
  "dateModified": "2026-09-29",
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
