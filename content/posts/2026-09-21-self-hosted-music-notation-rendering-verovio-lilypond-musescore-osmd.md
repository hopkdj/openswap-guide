---
title: "Self-Hosted Music Notation Rendering in 2026: Verovio vs LilyPond vs MuseScore vs OSMD"
date: "2026-09-21"
tags: ["music", "self-hosted", "media", "developer-tools"]
draft: false
cover: "/img/screenshots/vexflow-rendered-score.jpg"
description: "Run your own sheet music engraving pipeline in 2026: Verovio, LilyPond, MuseScore CLI and OpenSheetMusicDisplay compared with real commands, Docker setup and pitfalls."
---

Every choir director, music teacher, sheet-music library and digital archive eventually hits the same wall: the scores live inside somebody else's proprietary notation editor. You cannot script it, you cannot batch-export 4,000 manuscripts, and you cannot embed a rendering view in your own catalogue without a licence. Meanwhile the underlying files — MusicXML, MEI, ABC, MIDI — are open formats your team could process entirely on your own hardware.

This is the 2026 landscape for **self-hosted music notation rendering**: four mature, license-safe renderers that turn machine-readable scores into SVG, PNG or PDF, on your own server, with no per-seat fee and no lock-in. They are built for different jobs, and choosing wrongly means either fighting a typesetting engine that was never meant for real-time output, or shipping a browser-only tool into a batch pipeline.

## TL;DR — Quick Verdict

| Your situation | Use | Why |
|---|---|---|
| Digital archive or web catalogue that must render scores in a browser | **Verovio** | C++ engine compiled to WebAssembly, SVG output, 0 server round-trips after load |
| Print-quality engraved PDFs, deterministic output, text-based sources | **LilyPond** | Best typography in open source, plain-text input that diffs cleanly in Git |
| You already have `.mscz` files and need batch PDF/PNG/MusicXML export | **MuseScore CLI** | Headless `-o` export of the format musicians actually share |
| Web app with no server-side rendering budget, MusicXML only | **OpenSheetMusicDisplay** | Browser-first TypeScript renderer on top of VexFlow, headless-capable with Node |

**Verdict:** Verovio for anything that touches the web or needs MEI support. LilyPond when the output goes to a printer or a publisher. MuseScore CLI when your source material arrives as MuseScore files. OSMD when you want the simplest possible embed inside an existing frontend. Most serious archives run **two** of them — LilyPond for print, Verovio for the web viewer.

## The Comparison (live GitHub data, September 2026)

| Tool | Language / runtime | GitHub stars | Last push | Input formats | Output | License |
|---|---|---|---|---|---|---|
| [Verovio](https://github.com/rism-digital/verovio) | C++20 + JS/Python/Java/Swift/Go bindings | **929** | 2026-09-21 | MEI, MusicXML, Humdrum, ABC, Plaine & Easie, Musedata, EsAC | SVG (also MIDI) | LGPL-3.0 |
| [LilyPond](https://github.com/lilypond/lilypond) | C++ / Scheme (GUI repo is a mirror) | **678** | 2026-09-19 | LilyPond text notation (can import MusicXML via converter) | PDF, SVG, PNG, MIDI | GPL-3.0 |
| [MuseScore](https://github.com/musescore/MuseScore) | C++ / Qt | **15,124** | 2026-09-20 | MSCZ, MusicXML, MIDI, Guitar Pro, MEI export | PDF, PNG, SVG, WAV, MusicXML | GPL-3.0 |
| [OpenSheetMusicDisplay](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay) | TypeScript (VexFlow) | **1,969** | 2026-09-19 | MusicXML | SVG in DOM / canvas | MIT |
| [abcjs](https://github.com/paulrosen/abcjs) | JavaScript | **2,346** | 2026-08-09 | ABC notation | SVG, interactive audio | MIT |

Star counts are not the ranking here — MuseScore is a desktop application with a huge consumer user base, while Verovio is infrastructure used by research libraries. Match the tool to the pipeline, not to the popularity contest.

## Decision Matrix

| Use case | Pick | Reason |
|---|---|---|
| Choral library publishing weekly PDFs from text sources | LilyPond | Engraving quality, Git-friendly source, zero-click batch builds |
| Conservatory archive exposing 10,000 MEI manuscripts on the web | Verovio | MEI-first toolchain, tiny WASM footprint, ships with its own editor |
| Band arrangements arriving as `.mscz` from arrangers | MuseScore CLI | Only tool that opens the format musicians actually exchange |
| React app that must display user-uploaded MusicXML | OSMD | Drop-in viewer component, MIT licence, no server rendering |
| Teaching tool with playback and note highlighting | abcjs or OSMD | Both handle interaction; abcjs wins for ABC-notation folk repertoire |
| Transcription service generating printable scores from MIDI | MuseScore CLI + LilyPond | MuseScore imports MIDI, LilyPond produces the printable score |

## Verovio — The Web Rendering Engine

Verovio is a "fast, portable and lightweight library for engraving Music Encoding Initiative (MEI) digital scores into SVG images", per its own project description — and it also converts Plaine & Easie, Humdrum, Musedata, MusicXML, EsAC and ABC on the fly. It is standard C++20 with bindings for JavaScript, Python, Java, Swift and Go, and it uses the SMuFL specification (Bravura and friends), so glyph output is font-driven and customizable.

The Python binding makes server-side rendering a five-line job:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install verovio
```

```python
import verovio

tk = verovio.toolkit()
tk.setOptions({
    "pageWidth": 2100,       # A4-ish width in MEI units
    "pageHeight": 2970,
    "scale": 40,
    "adjustPageHeight": True,
})

if tk.loadFile("manuscript.mei"):
    svg = tk.renderToSVG(1)          # page 1 as an SVG string
    open("page-1.svg", "w").write(svg)
    print("pages:", tk.getPageCount())
```

For a browser embed you skip the server entirely: Verovio's toolkit ships as WebAssembly, so the same engine that powers `editor.verovio.org` runs in the client. Serving a 20 MB MEI file never touches your application server. For batch conversion from the command line, the standalone build accepts a file and an output path and writes SVG directly.

**Where Verovio hurts:** it renders pages one at a time, and very large scores mean many SVG fragments — plan caching. Its default fonts render Western staff notation; early-music or non-standard notation may need font and layout tweaking.

![OpenSheetMusicDisplay UI panel from the official repository](/img/screenshots/osmd-ui.jpg "OpenSheetMusicDisplay plugin UI — browser-first MusicXML rendering built on VexFlow")

## LilyPond — Text In, Engraving Out

LilyPond's model is the opposite of a WYSIWYG editor: you write plain-text notation describing the *music*, and LilyPond decides the engraving, following traditional plate-making rules. The output is the highest-quality open-source engraving you can produce without hiring a human engraver, and because the source is text, scores live comfortably in Git, review like code, and can be templated with variables.

```bash
# Debian/Ubuntu package (also available as official builds for other platforms)
sudo apt-get install -y lilypond fonts-texgyre

lilypond --pdf anthem.ly          # engrave to PDF
lilypond -dbackend=svg anthem.ly  # or SVG, for the web
```

```lilypond
\version "2.24.0"
\header { title = "Anthem for the Archive" tagline = ##f }

soprano = \relative c'' {
  \key g \major \time 4/4
  g4 g a b | c2 b | \bar "|."
}

\score {
  \new ChoirStaff <<
    \new Staff = "sop" \with { instrumentName = "Soprano" } \soprano
  >>
  \layout { ragged-right = ##f }
}
```

The reproducibility story is excellent: same source plus same LilyPond version equals byte-identical PDFs, which is exactly what you want in an automated publishing job. Pin the version in your container image, or a minor release will silently reflow every page in the archive.

**Where LilyPond hurts:** there is no realistic round-trip from LilyPond back to MusicXML, so it is a publishing target rather than an interchange format, and musicians who expect to edit visually will not adopt it. Use it as the print stage of a pipeline whose source of truth is MusicXML or MEI.

## MuseScore CLI — Batch Export of the Format Everyone Actually Uses

MuseScore is the notation editor most musicians have installed, which makes its file format the de facto submission format for arrangers and teachers. Its command-line interface turns that into a batch pipeline: point it at a file, ask for an output extension, get the file.

```bash
# MuseScore 3/4 expose a CLI with the same batch-export flags
mscore  -o "out/jubilate.pdf"  scores/jubilate.mscz    # MS3-style binary name
mscore4 -o "out/jubilate.png"  scores/jubilate.mscz    # MuseScore 4 naming

# Batch the whole folder, one format at a time
for f in scores/*.mscz; do
  mscore4 -o "out/$(basename "${f%.mscz}").pdf" "$f"
done
```

Running it headless on a server needs an X server or a virtual display in most distributions, because the binary is a Qt GUI application:

```bash
sudo apt-get install -y musescore3 xvfb
xvfb-run -a mscore4 -o "out/score.pdf" scores/score.mscz
```

That `xvfb-run` wrapper is the part nobody documents, and it is the reason a MuseScore render job dies with a display error inside a slim container. Note also that CI containers need fonts installed or exported PDFs come out with missing glyphs.

**Where MuseScore hurts:** heavyweight dependency footprint (Qt plus fonts), slower startup than a library call, and version-to-version layout differences. It is a converter and exporter, not a rendering engine to embed — for that, use the exporter's output.

## A Realistic Self-Hosted Pipeline

The pattern that works in production splits duties: **MuseScore or Verovio ingests**, **LilyPond or Verovio renders**, and one small service exposes it. Here is a container that can do both Verovio and print-quality LilyPond work:

```dockerfile
# Dockerfile — multi-tool engraving worker
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        lilypond fonts-texgyre && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir verovio==4.5.1
WORKDIR /work
# render.sh decides by extension: .ly -> LilyPond, .mei/.xml -> Verovio
COPY render.sh /work/render.sh
ENTRYPOINT ["/work/render.sh"]
```

```bash
docker build -t engraver:1 .
docker run --rm -v "$PWD/scores:/work/in:ro" -v "$PWD/out:/work/out" engraver:1 in/anthem.ly
docker run --rm -v "$PWD/scores:/work/in:ro" -v "$PWD/out:/work/out" engraver:1 in/manuscript.mei
```

Wrap it behind a queue if the archive is large — engraving is CPU-bound but not urgent, so a worker plus a job table beats a synchronous HTTP endpoint that times out on a 400-page orchestral score. If your scores are also streamed to listeners, the [self-hosted music streaming comparison](../2026-05-01-koel-vs-mopidy-vs-snapcast-self-hosted-music-streaming-guide/) covers the audio side, and the [audio DSP guide](../2026-06-07-self-hosted-audio-dsp-room-correction-camilladsp-brutefir-lsp/) is the counterpart for processing the recordings themselves. Teaching material that ships alongside sheet music often lives in [audiobook and ebook servers](../2026-04-19-audiobookshelf-vs-kavita-vs-calibre-web-self-hosted-ebook-audiobook-server-2026/) — worth wiring into the same catalogue.

## Common Pitfalls

**Missing fonts produce empty staves.** SMuFL music fonts (Bravura, Leipzig, Gootville) and text fonts must be present *inside* the container. A score rendered in a slim image with no fonts is not an error — it is a blank page, which is worse.

**First-page-only rendering.** Verovio and OSMD render per page. If your script only asks for page 1, your pipeline silently ships a one-page score for a forty-page mass setting.

**Version pinning.** LilyPond and MuseScore both change layout between releases. Unpinned engraving in a container means your archived PDFs change without anyone touching the source files.

**Unicode titles.** Choral repertoire is full of diacritics and non-Latin scripts. Without CJK and full Unicode fonts in the image, titles render as boxes in the exported PDF.

**MEI versus MusicXML round-trips.** MEI is richer; converting MEI to MusicXML and back loses editorial markup. Keep the MEI master and export derivatives — never the other way around.

**Assuming a GUI binary runs headless.** Anything Qt-based inside a container needs `xvfb-run`, and the failure message ("cannot connect to display") looks like a permissions bug, not a missing display server.

**Licence hygiene.** Verovio is LGPL, LilyPond and MuseScore are GPL, OSMD and abcjs are MIT. Embedding an LGPL engine in a commercial web product is fine; statically linking GPL engravers into a proprietary binary is not. Check before you ship.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Music Notation Rendering in 2026: Verovio vs LilyPond vs MuseScore vs OSMD",
  "description": "A 2026 comparison of self-hosted sheet music rendering tools: Verovio, LilyPond, the MuseScore CLI and OpenSheetMusicDisplay, with real commands, Docker setup, live GitHub metrics and production pitfalls.",
  "datePublished": "2026-09-21",
  "dateModified": "2026-09-21",
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

**What is the best open-source tool for rendering MusicXML to SVG in 2026?**
Verovio is the strongest all-round choice: it accepts MusicXML directly, outputs SVG, and ships as a C++ library, a CLI, a Python package and a WebAssembly build for the browser. OpenSheetMusicDisplay is the simpler option when you only need MusicXML inside a JavaScript frontend and want an MIT-licensed drop-in viewer.

**Can I run MuseScore headless on a server without a desktop environment?**
Yes, but you must provide a virtual display. MuseScore is a Qt application, so wrap it with `xvfb-run -a mscore4 -o out.pdf input.mscz` inside a container that also has the engraving fonts installed. Without the virtual display the process exits with a connection error that looks unrelated to the real cause.

**Is LilyPond better than MuseScore for printing scores?**
For final print output, LilyPond's engraving is generally better because it applies traditional typesetting rules automatically and its output is deterministic — the same source and version always produce the same PDF. MuseScore is better when you need to open, edit and exchange files with musicians, or when you must import MIDI and Guitar Pro sources.

**How do I render only one page of a large score?**
Verovio renders page by page through its toolkit API, so you call the render method with the page number you want; OpenSheetMusicDisplay draws into a container element and can be scrolled or clipped. LilyPond and MuseScore export whole documents, so extract single pages from the PDF afterwards if your catalogue needs thumbnails per movement.

**Do these tools require a paid font licence?**
No. Verovio uses SMuFL-compliant fonts, and the widely used Bravura font family is available under an open licence. LilyPond bundles its own fonts, and MuseScore ships with its notation font set. The practical requirement is that the fonts are installed inside your rendering container, since missing music fonts yield blank staves rather than an error message.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
