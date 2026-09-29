---
title: "Tired of Out-of-Sync Subtitles? ffsubsync vs alass vs libass in 2026"
date: "2026-09-29"
tags: ["subtitles", "media-server", "ffmpeg", "self-hosted", "video"]
draft: false
cover: "/img/screenshots/ffsubsync-subtitle-sync.jpg"
---

Twenty minutes into a film, the dialogue drifts four seconds ahead of the picture. You nudge the offset in your player, and it holds — until the ad break in the source cut, where it snaps out of alignment again. Across a library of a few hundred files, roughly one in five subtitles has this problem, and fixing them by hand is a genuinely terrible use of an evening.

The good news: subtitle alignment is a solved problem with three mature open-source tools — **ffsubsync**, **alass** and **libass** — plus **pysubs2** for the editing and conversion layer around them. The bad news is that people install the wrong one, feed it the wrong reference, and conclude the tooling is broken.

## TL;DR / Quick Verdict

- **Subtitles are merely offset from the audio, and you have the video file?** Use **ffsubsync**. It extracts speech from the audio track and aligns the subtitle timing to it. One command, no reference subtitle needed.
- **You have a correctly-synced subtitle in another language, and the source has ad-break cuts or a different framerate?** Use **alass**. It solves for constant offsets *and* splits, which is exactly the case ffsubsync handles least gracefully.
- **You need to convert, retime, or restyle thousands of files programmatically?** Use **pysubs2** as the editing layer, regardless of which sync tool you chose.
- **You need the subtitles burned into the video, with ASS styling intact?** That is **libass**, working as an FFmpeg filter or inside mpv/VLC.

## Why Subtitle Drift Happens

Subtitle desync is rarely random. It comes from four predictable sources:

1. **A constant offset** — the release group's timing master differed by a couple of seconds from yours. This is the easy case.
2. **Framerate mismatch** — a 23.976 fps timing sheet applied to a 25 fps encode drifts progressively; the error grows linearly from zero to the length of the film.
3. **Ad-break or scene cuts** — a broadcast rip with inserted segments, or a director's cut with added scenes. Everything after a cut is shifted, but only after that cut.
4. **Bad initial timing** — the subtitle file was retimed for a different source entirely, or produced by an automated pipeline with a broken clock.

Knowing which one you have tells you which tool to reach for. A constant offset is a one-liner. A cut-heavy source needs a solver.

## Comparison Table (live GitHub data, September 2026)

| Tool | Role in the pipeline | Language | Latest release | Last commit | Stars |
|---|---|---|---|---|---|
| **ffsubsync** | Automatic sync against speech in the audio track | Python | 0.5.1 | 2026-07-24 | 7,889 ⭐ |
| **alass** | Automatic sync against a reference subtitle, handles splits | Rust | 2.0.0 | 2023-12-28 | 1,451 ⭐ |
| **libass** | ASS/SSA subtitle renderer (players, FFmpeg, burn-in) | C | 0.17.5 (2026-06-24) | 2026-09-17 | 1,178 ⭐ |
| **pysubs2** | Format conversion, retiming, batch editing | Python | 1.9.0 | 2026-09-27 | 440 ⭐ |

Note the maintenance signals: libass and pysubs2 are actively developed, ffsubsync is maintained with steady releases, and alass has had no commits since December 2023. That does not make alass unusable — its algorithm is still the best option for split-heavy material — but it does mean you should treat it as a stable, frozen component rather than something that will grow new features.

![ffsubsync synced subtitles demo](/img/screenshots/ffsubsync-synced-subtitles.jpg "Subtitle timing after ffsubsync aligns speech to subtitle cues")

## Scenario Decision Matrix

| Situation | Tool | Why |
|---|---|---|
| Single file, unknown offset, audio available | ffsubsync | Aligns to detected speech; no reference file needed |
| Cleaning a whole library unattended | ffsubsync in batch mode | Auto-detects sibling `.srt` files and skips already-synced outputs |
| Ad breaks / director's cut / inserted scenes | alass | Splits the timeline instead of applying one global offset |
| Framerate mismatch (23.976 vs 25 fps) | alass | Solves framerate and offset together |
| Only a foreign-language subtitle to use as truth | Either, plus a reference file | ffsubsync accepts a subtitle as the reference too |
| Convert SRT ⇄ ASS ⇄ WebVTT at scale | pysubs2 | CLI plus a clean Python API |
| Permanently burn subtitles into video | libass via FFmpeg | Renders ASS styling properly, unlike naive overlays |

## ffsubsync — Sync Against the Audio Itself

ffsubsync's core idea is to sidestep the need for a reference subtitle. It runs voice activity detection over the audio track, compares that speech pattern against the subtitle cues, and finds the offset that best aligns them. Because it works on the *pattern* of speech rather than the language, it is language-agnostic: a German subtitle works fine for an English audio track.

Basic usage after `pip install ffsubsync` (FFmpeg must be installed first):

```bash
# Sync one file
ffs movie.mp4 -i unsynchronized.srt -o synchronized.srt

# Auto-detect sibling subtitles (movie.srt, movie.en.srt, ...)
# and write movie.synced.srt next to each, leaving originals untouched
ffs movie.mp4

# Use a correctly-timed subtitle in another language as the reference
ffsubsync reference.srt -i unsynchronized.srt -o synchronized.srt
```

The no-`-i` form is what makes it practical for libraries: it discovers subtitles sitting next to the reference that share its name, writes `<name>.synced.srt` for each, and safely skips files it has already produced. Re-running the same command is idempotent, which matters when you put it in a scheduled job. Add `--overwrite-input` if you want in-place replacement instead.

Two more flags earn their keep. `--max-duration-seconds N` processes only the first N seconds of a long reference — useful because for remote sources FFmpeg stops downloading once that duration is reached:

```bash
ffs "https://example.com/movie.mp4" -i unsync.srt -o sync.srt --max-duration-seconds 600
```

And remote references are supported over `http(s)`, `rtmp`, `rtsp` and `ftp`, so a NAS-hosted file or a stream URL both work. For very unstable sources, download first: the tool streams the reference over the network and depends on that connection staying alive.

Where ffsubsync struggles is material with structural edits. A single global offset cannot describe a timeline that is shifted by 30 seconds after an ad break — that is a different mathematical problem.

## alass — The Split-Aware Solver

alass solves for three things at once: constant offsets, splits (ad breaks, director's cuts), and differing framerates. It is written in Rust and ships both as a Linux binary and a Windows executable, and it needs `ffmpeg` and `ffprobe` available on the path.

```bash
# Align a subtitle to the movie's audio
alass movie.mp4 incorrect_subtitle.srt output.srt

# Align directly to a correctly-timed reference subtitle (no audio analysis)
alass reference_subtitle.ssa incorrect_subtitle.srt output.srt

# Tune how eagerly the solver introduces splits (default 7; useful range 5-20)
alass reference_subtitle.ssa incorrect.srt output.srt --split-penalty 10

# Fast path: constant shift only, no split detection
alass movie.mp4 incorrect.srt output.srt --no-splits
```

The `--split-penalty` knob is the one to understand. Values below 5 introduce many unnecessary splits; values above 20 miss real ones. The author's guidance — stay between 5 and 20 — is worth following literally. If you know the problem is a plain offset, `--no-splits` is dramatically faster because the search space collapses to a single shift.

You can also point alass at a non-standard FFmpeg install with `ALASS_FFMPEG_PATH` and `ALASS_FFPROBE_PATH`, which is the usual fix inside containers and Nix-like environments where binaries are not on the default path.

The honest caveat: last commit December 2023, releases frozen at 2.0.0. It works, it is widely packaged, and if your library is full of broadcast rips it is still the right tool. Just do not expect fixes for edge cases you hit.

## libass — The Rendering Layer People Forget

Every sync tool above produces correct *timing*. libass is what makes subtitles look right on screen. It is a portable ASS/SSA renderer, mostly compatible with VSFilter, and it is embedded in the players and transcoders you already use rather than being something you run directly.

In practice you meet libass through FFmpeg's subtitle filters:

```bash
# Burn subtitles into the video, applying ASS styling
ffmpeg -i movie.mkv \
  -vf "subtitles=movie.srt:force_style='FontName=Inter,FontSize=22,Outline=1,Shadow=0'" \
  -c:v libx264 -crf 18 -preset slow -c:a copy movie-burned.mkv

# Render a styled ASS file (full styling, not just text)
ffmpeg -i movie.mkv -vf "ass=movie.ass" -c:a copy movie-styled.mkv
```

Two details make the difference between "burned subtitles" and "subtitles the viewer wishes were off". First, encoding: if the file is legacy-encoded, pass `charenc=CP1252` (or the appropriate codepage) inside the filter, or you will get mojibake that looks like a sync problem but is not. Second, fonts: `force_style` overrides the subtitle's own styling, so only use it when you deliberately want a uniform look — it silently discards the typesetting a fansub group spent hours on.

Building libass from source, if your distribution's package is too old, is a short Meson build:

```bash
meson setup build && meson compile -C build
sudo meson install -C build
```

## pysubs2 — The Editing Layer

Once timing is correct, the remaining work is format conversion and mass edits: converting a folder of ASS files to SRT for a device that cannot read ASS, shifting everything by 0.3 seconds because your encoder added a delay, or stripping styling tags before an upload.

pysubs2 handles SRT, ASS/SSA, WebVTT, TTML, MicroDVD, MPL2, TMP and SAMI, converting internally to an ASS-based representation. It is pure Python with no extra dependencies, and the current release requires Python 3.12 or newer — check your interpreter before wiring it into an older container.

```bash
pip install pysubs2
pysubs2 --shift 0.3s *.srt      # nudge timing by 300 ms
pysubs2 --to srt *.ass          # convert a folder to SRT
```

```python
import pysubs2

subs = pysubs2.load("my_subtitles.ass", encoding="utf-8")
subs.shift(s=2.5)                     # +2.5 seconds to every cue
for line in subs:
    line.text = "{\\be1}" + line.text  # ASS blur tag, applied line by line
subs.save("my_subtitles_edited.ass")
```

That programmatic path is the reason pysubs2 belongs in the pipeline even when you use ffsubsync or alass for alignment: you can post-process thousands of files in one script instead of running a CLI per file.

## Putting It Together: A Batch Pipeline

There are no official container images for these tools, so build a small image that bundles FFmpeg (which provides libass) with the Python sync and edit layers:

```dockerfile
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libass9 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir ffsubsync pysubs2
WORKDIR /media
ENTRYPOINT ["ffsubsync"]
```

Then a sync-then-normalise loop over a library:

```bash
#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob
for video in /media/**/*.mkv /media/**/*.mp4; do
  # 1. Align every sibling subtitle to the audio, writing *.synced.srt
  ffsubsync "$video" || echo "sync failed: $video"
  # 2. Convert results to plain SRT for devices that cannot read ASS
  pysubs2 --to srt "${video%.*}"*.synced.srt || true
done
```

Deliberately non-fatal: one corrupt file should not abort a 500-file overnight run.

## Pitfalls and Migration Notes

1. **Do not sync against a subtitle that is already wrong.** ffsubsync trusts its reference. Feeding it a mis-timed file as the reference produces confidently wrong output.
2. **Voice activity detection needs speech.** A music-only documentary, a film with long silent stretches, or a badly mixed audio track will defeat audio-based alignment. Supply a reference subtitle instead.
3. **Check framerate before reaching for a solver.** `ffprobe` on the video and the subtitle's declared FPS comparison takes ten seconds; if they differ, alass is the correct tool and ffsubsync will only partially help.
4. **Keep originals.** Both ffsubsync's auto mode and `pysubs2 --shift` can overwrite if told to. Version your subtitle directory, or at minimum work on copies for the first batch.
5. **Mojibake is not desync.** If text renders as garbage, fix the encoding (`charenc` in the FFmpeg filter, `encoding=` in pysubs2). Re-running a sync will not help.
6. **Frozen software still runs.** alass is unmaintained; pin a known-good binary in your image rather than fetching "latest" on every build.

## FAQ

**Is ffsubsync better than alass?**
For different problems. ffsubsync aligns to speech in the audio and needs no reference subtitle, which makes it ideal for a library where you only have the video. alass is better when the timeline has structural cuts or a framerate mismatch, because it solves for splits rather than one global offset. Many people keep both and pick per file.

**Can I sync subtitles without the video file?**
Yes, if you have a correctly-synced subtitle in any language. Both ffsubsync and alass accept a subtitle as the reference, which is the standard workflow when your audio is a stream or you only have a plain audio rip.

**Does subtitle sync work on 4K and HDR files?**
Yes. Alignment operates on the audio track, so resolution and dynamic range are irrelevant. Burn-in is a different story: rendering subtitles into an HDR pipeline requires HDR-aware colour handling, or the subtitles will look washed out.

**Why did my subtitle shift again after the ad break?**
That is a split, not a constant offset. Use alass and leave `--split-penalty` near its default of 7 so the solver is allowed to introduce additional break points.

**Do I need FFmpeg for all of this?**
For ffsubsync, alass and any burn-in, yes — they shell out to `ffmpeg`/`ffprobe` for decoding and rendering. pysubs2 alone is pure Python and needs no FFmpeg, which makes it a good fit for converting files on a machine where you cannot install system packages.

**Can subtitles be synced in the browser instead of installed locally?**
ffsubsync publishes a browser build that runs locally using a WebAssembly build of FFmpeg; files stay on your machine. It is convenient for a single file, but for a library a scheduled container job is far less tedious.

For related reading, see our [video transcoding comparison](../tdarr-vs-unmanic-vs-handbrake-self-hosted-video-transcoding-guide-2026/) and the [self-hosted media server comparison](../jellyfin-vs-plex-vs-emby/). If you are building the audio side of this pipeline, the [audio codec libraries guide](../2026-06-22-cpp-audio-codec-libraries-libopus-libflac-libvorbis/) covers the encoders involved.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Tired of Out-of-Sync Subtitles? ffsubsync vs alass vs libass in 2026",
  "description": "A practical comparison of ffsubsync, alass, libass and pysubs2 for automatic subtitle synchronization, referencing and rendering, with a batch pipeline, Docker example and troubleshooting guide.",
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
