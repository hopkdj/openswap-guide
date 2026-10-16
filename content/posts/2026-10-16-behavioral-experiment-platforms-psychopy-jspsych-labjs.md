---
title: "PsychoPy vs jsPsych vs lab.js in 2026: Which Open-Source Platform Should Run Your Behavioral Experiment?"
date: "2026-10-16"
tags: ["research-tools", "psychology", "experiments", "psychopy", "jspsych", "open-science", "python"]
draft: false
cover: "/img/screenshots/psychopy-builder.jpg"
---

Every behavioral lab hits the same wall. The stimulus presentation software that defined the field — E-Prime, Presentation, SuperLab — is licensed per seat, per machine, and per year, and the licence rarely covers running participants online. Meanwhile half the subjects you need are at home with a laptop, not in your lab with a calibrated monitor.

Three open-source platforms now cover nearly all of it: **PsychoPy**, **jsPsych** and **lab.js**. They overlap, they are not interchangeable, and the choice determines whether your online replication works at all. Here is the honest breakdown, with live project data and code from the official documentation.

## Quick Verdict (TL;DR)

- **Choose PsychoPy** for laboratory work with precise timing, hardware integration (eye trackers, response boxes, EEG triggers) and a GUI Builder that students can use on day one. Python underneath, so analysis can live in the same repository.
- **Choose jsPsych** for browser experiments that must run anywhere — large online samples, panel providers, or classroom studies. It is the most widely used JavaScript framework for behavioral research and it deploys as static files.
- **Choose lab.js** if you want a browser-based graphical builder aimed at teaching and rapid design iteration, and you accept a smaller ecosystem and slower release cadence.
- **The pragmatic answer for most labs:** design in PsychoPy for the lab, and reimplement the critical conditions in jsPsych for online data collection, validating that the two produce comparable results before you scale up.

## Live Comparison (October 2026)

| Platform | GitHub stars | Last commit | Language | Build & run | Best for | Licence |
|---|---|---|---|---|---|---|
| **PsychoPy** | 2,097 | 2026-10-15 | Python | Desktop app (Builder or code) | Lab timing precision, hardware triggers | GPLv3 |
| **jsPsych** | 1,227 | 2026-10-13 | JavaScript | Static site, runs in browser | Online samples at scale | MIT |
| **lab.js** | 291 | 2025-10-30 | JavaScript | Static site, runs in browser | Teaching, quick browser studies | Permissive |

A caveat that matters more than stars: release cadence correlates with browser-compatibility maintenance. Browsers break APIs regularly, so an actively maintained browser framework is worth more than a feature-rich one that lagged a year behind Web Audio changes.

## Decision Matrix

| Your situation | Best choice | Why |
|---|---|---|
| Millisecond-precision reaction times in a controlled lab | PsychoPy | Native desktop timing, frame-accurate stimulus control, hardware sync |
| Eye tracking, button boxes, EEG triggers | PsychoPy | Established hardware integrations instead of custom bridges |
| 800 participants from an online panel | jsPsych | Runs in the browser, deploys as static files, no install for subjects |
| Participants on unknown laptops and tablets | jsPsych | Handles variable refresh rates and input latency explicitly |
| Undergraduate lab course teaching experiment design | lab.js | Browser builder, gentle learning curve, results exportable |
| Teaching a course that also needs Python skills | PsychoPy | Students learn experiment logic and Python at once |
| Analysis and experiment in one repository | PsychoPy | Same language and environment as your stats pipeline |

## PsychoPy: Precision and Hardware, in Python

PsychoPy is a Python experiment library with a graphical Builder on top. The Builder matters pedagogically — students assemble routines, loops and conditions, then export runnable Python they can read and edit. For timing-critical designs, the underlying library gives you frame-level control.

A minimal grating stimulus loop, in the library's own idiom:

```python
from psychopy import visual, core, event

win = visual.Window(size=(1024, 768), units="height", fullscr=False)
grating = visual.GratingStim(win, tex="sin", mask="gauss", size=0.4, sf=3.0)

for frame in range(120):
    grating.setPhase(0.05, "+")
    grating.draw()
    win.flip()

core.quit()
```

![PsychoPy Builder interface from the official documentation](/img/screenshots/psychopy-builder.jpg)

Installation is a single pip command (`pip install psychopy`), and the ecosystem is the practical argument: hardware vendors document PsychoPy integration for response boxes and eye trackers, and the same Python environment runs your pandas analysis afterwards. The GPLv3 licence is a non-issue for research use and a consideration if you plan to ship a commercial product built on it.

The limit is deployment. PsychoPy is a desktop install, so an online study means either a hosted conversion path or a second implementation. That is precisely the gap jsPsych fills.

## jsPsych: Browser Experiments That Scale

jsPsych is a JavaScript framework for building behavioral experiments that run in a browser. The plugin model separates task structure from trial behaviour: you declare a timeline, each entry names a plugin and carries its parameters, and the framework handles stimulus timing, response collection and data output.

```javascript
const jsPsych = initJsPsych();

const timeline = [
  {
    type: jsPsychHtmlButtonResponse,
    stimulus: "<p>Was the second tone higher or lower than the first?</p>",
    choices: ["Higher", "Lower"],
    data: { task: "pitch_discrimination", condition: "practice" }
  }
];

jsPsych.run(timeline);
```

Two operational details make it the default for online work. **Deployment is static files**: build the study, upload it, and participants only need a URL. **The plugin catalogue is broad** — keyboard responses, sliders, audio and video stimuli, surveys, and timing extensions for synchronization with external measurement.

The honest caveats: **browser timing is not lab timing.** You are at the mercy of variable refresh rates, input latency and background tabs, so designs that depend on sub-10 ms precision should either measure and model the variance or stay in the lab. jsPsych's approach is to let you record timing diagnostics and analyse them, not to promise precision it cannot deliver. Also note that plugin APIs evolve between major versions, so pin a version in your build and archive the exact study bundle you ran.

## lab.js: The Teaching-Friendly Browser Builder

lab.js takes the browser-based approach and adds a visual builder: a study is a structure of nested pages and sequences you assemble in the interface, with generated JavaScript behind it. With 291 stars and a slower commit cadence, it is the smallest project of the three, and that shows in ecosystem breadth rather than in concept.

Where it earns its place is teaching and rapid prototyping. A student can assemble a working study, run it in the browser and export the data without touching a terminal — the lowest-friction path from idea to pilot. If your project grows into a high-stakes online study with complex randomization and panel integration, migrating the design to jsPsych is a reasonable next step, because both produce browser studies and the concepts transfer.

## Pitfalls That Cost Real Datasets

**Validate your online replication against the lab version.** The same task in PsychoPy and jsPsych will not produce identical distributions. Run both with a small in-person sample, compare distributions, and report the difference rather than assuming equivalence.

**Pin dependency versions and archive the built study.** A behavior change in a browser or a plugin update can silently alter stimulus timing. Archive the exact bundle that produced your dataset — future-you will need it during review.

**Test on the worst device, not your laptop.** Recruit a tablet and a low-end laptop before launch. Audio latency and touch input are the two most common sources of unusable online data.

**Do not treat practice and main trials as one condition.** Label data rows explicitly at trial definition time (`data: { condition: ... }`), because reconstructing condition labels afterwards from row order is error-prone at scale.

**Plan your stimulus files as part of the build.** Audio and image stimuli need preloading logic and licence-compatible sourcing. Studies that stream stimuli mid-trial produce missing-data rows that look like participant attrition but are infrastructure failures.

**Keep the analysis language consistent.** If PsychoPy builds your stimuli, Python already reads your data. Mixing platforms across studies without a shared tidy-data convention costs more time than the licenses you saved.

For related infrastructure, see our guides to the [electronic lab notebook platforms](../2026-05-04-self-hosted-electronic-lab-notebook-elabftw-chemotion-labkey-guide/), [lab instrument control servers](../2026-06-08-self-hosted-lab-instrument-control-servers-lxi-tools-pyvisa-scpi-parser/) and [scientific data management systems](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/), which cover what happens to the data after the experiment ends.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PsychoPy vs jsPsych vs lab.js in 2026: Which Open-Source Platform Should Run Your Behavioral Experiment?",
  "description": "Comparison of PsychoPy, jsPsych and lab.js for laboratory and online behavioral experiments, covering timing precision, hardware integration, browser deployment, licence terms and replication pitfalls, with code from official documentation.",
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

**Is jsPsych accurate enough for reaction time experiments?**

It is accurate enough for many reaction time designs, but not for sub-10 millisecond claims without validation. Browsers introduce variable refresh rates and input latency, so record timing diagnostics, compare against a lab implementation with a pilot sample, and report how timing was handled rather than assuming equivalence.

**Can PsychoPy run experiments online?**

PsychoPy has an online delivery path, but most labs that need large browser samples either use that route with testing or reimplement the task in jsPsych. The deciding factor is usually whether your design depends on hardware integration or sub-frame timing, which the browser cannot deliver reliably.

**Do subjects need to install anything for jsPsych or lab.js?**

No. Both produce static web studies that run in a browser from a URL, which is why they dominate online data collection. That also means you must handle browser compatibility, device variability and stimulus preloading yourself.

**Which platform should a beginner use?**

For a browser study or a teaching course, lab.js — the visual builder and export path keep the learning curve short. If your lab is Python-based or needs hardware integration, learn PsychoPy instead; the Builder produces readable Python and the skill compounds into your analysis workflow.

**What replaces the per-seat licences of E-Prime and Presentation?**

These three platforms do, in most cases, and all of them are free. The cost you take on instead is engineering time: deploy browser studies, validate timing, archive exact builds, and reconcile data schemas across platforms. For a typical lab that is a one-off cost per study rather than an annual licence.

**How do I keep data from two platforms comparable?**

Define a single tidy data schema before running either version — one row per trial, with explicit columns for participant, condition, stimulus parameters, response and timing diagnostics. Then each platform only needs a thin export adapter, and your analysis code never learns which platform produced a row.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
