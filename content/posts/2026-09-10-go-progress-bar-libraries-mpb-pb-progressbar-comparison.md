---
title: "Go Progress Bar Libraries in 2026: mpb vs pb vs progressbar"
date: "2026-09-10"
tags: ["go", "cli", "terminal", "developer-tools"]
draft: false
cover: "/img/screenshots/pb-cover.jpg"
---

Nothing ages a command-line tool faster than a silent five-minute operation. Your users stare at a frozen cursor, wonder if the process died, and hit Ctrl+C — so you add a progress bar, and that is where Go developers discover that "just print dots" is a surprisingly deep rabbit hole. The three libraries below are the ones that survived years of real-world use: **pb** (cheggaaa/pb, 3,720+ stars), **mpb** (vbauerster/mpb, 2,500+ stars), and **progressbar** (schollz/progressbar, 4,700+ stars). All three are small, dependency-light, and solve the same core problem — but they render differently, handle multiple bars differently, and integrate with I/O differently. Picking the wrong one means flickering output, interleaved logs, or a bar that only looks right on your machine.

**Quick verdict:** for **one simple, rock-solid bar** with byte counting and an `io.Writer` interface, choose **schollz/progressbar** — it is the least code to a correct result and degrades gracefully when output is not a terminal. For **classic single bars with powerful template customization** (colors, custom elements, IO proxy readers), choose **cheggaaa/pb**, the most popular of the three. For **multiple simultaneous bars** — parallel downloads, worker pools, or per-shard progress in a fan-out job — choose **mpb**, which is the only one of the three built around a rendering container that orchestrates many bars at once.

## Go Progress Bar Libraries at a Glance

| Feature | cheggaaa/pb | vbauerster/mpb | schollz/progressbar |
| --- | --- | --- | --- |
| GitHub stars | 3,724 | 2,509 | 4,703 |
| Latest push | 2026-09-07 | 2026-09-01 | 2026-08-18 |
| License | BSD-3-Clause | The Unlicense (public domain) | MIT |
| Current major | v3 | v8 | v3 |
| Multiple bars | No (single bar per writer) | **Yes — container orchestrates N bars** | No (single bar) |
| Rendering model | Carriage-return updates on one line | Full ANSI redraw of a bar region | Carriage-return updates on one line |
| Thread-safe | Yes | Yes | Yes (explicit design goal) |
| I/O integration | `NewProxyReader` for reads | Decorators + manual increments | Implements `io.Writer` (bytes auto-counted) |
| Unknown-length mode | Template with spinner elements | Possible with dynamic totals | **Automatic spinner when total = -1** |
| Custom templates | text/template with custom elements | Decorators (name, percentage, ETA, bytes, EWMA) | Option functions + theme structs |
| ETA algorithm | Average-based | **EWMA-based decorators** (smooth spikes) | Simple |
| Docs examples | Extensive README + v1 legacy docs | Per-feature `_examples/` directory | README with animated demos |
| Notable users | Widely used in ops tooling | Used where multi-stream progress matters | **croc** (the file-transfer tool) |

## Which Progress Bar Should You Pick? (Decision Matrix)

| Use Case | Recommended Tool | Reason |
| --- | --- | --- |
| Single operation: download, upload, copy, scan | **progressbar** | Two lines of code; byte-aware via `io.Writer`; spinner mode for unknown lengths |
| Tool that ships with a polished, brandable UI | **pb** | text/template elements give you full control of the rendered line |
| Parallel workers with per-worker progress | **mpb** | Multiple bars with synchronized decorator widths in one container |
| Streaming bytes through an `io.Reader`/`io.Copy` | **pb or progressbar** | pb's `NewProxyReader` and progressbar's writer both handle it |
| Library that must never flicker or garble logs | **progressbar** | Simple single-line updates; no full-region redraws |
| Spiky, variable-rate tasks (network transfers) | **mpb** | EWMA-based ETA decorators ignore short-term spikes |

## pb — The Battle-Tested Classic

cheggaaa/pb has been the default answer since the early Go days, and v3 modernized it around a clean builder API while keeping the famous templates. Its rendering model is a single line updated in place, with a built-in refresh rate (default 200 ms) that keeps CPU usage low during tight loops. The quick start from the official README is the entire mental model:

```go
package main

import (
	"time"

	"github.com/cheggaaa/pb/v3"
)

func main() {
	count := 100000

	// create and start new bar
	bar := pb.StartNew(count)

	for i := 0; i < count; i++ {
		bar.Increment()
		time.Sleep(time.Millisecond)
	}

	// finish bar
	bar.Finish()
}
```

pb ships three built-in templates — `Default`, `Simple`, and `Full` (the last includes speed and ETA) — and its real power is the template system, built on Go's `text/template`. You can compose bars from elements like `bar`, `percent`, `speed`, `counters`, and arbitrary colored strings, plus functional helpers:

```go
tmpl := `{{ red "With funcs:" }} {{ bar . "<" "-" (cycle . "↖" "↗" "↘" "↙" ) "." ">"}} {{speed . | rndcolor }} {{percent .}} {{string . "my_green_string" | green}}`

// start bar based on our template
bar := pb.ProgressBarTemplate(tmpl).Start64(limit)

// set values for string elements
bar.Set("my_green_string", "green")
```

For I/O-bound operations, pb's `NewProxyReader` wraps any `io.Reader` so `io.Copy` drives the bar automatically — the classic pattern for downloads, untarring, and database dumps:

```go
bar := pb.Full.Start64(limit)

// create proxy reader
barReader := bar.NewProxyReader(reader)

// copy from proxy reader
io.Copy(writer, barReader)

bar.Finish()
```

Settings cover the usual needs: `SetRefreshRate`, `SetWriter` (default is `os.Stderr` — deliberately not stdout, so `| grep` pipelines do not corrupt bar output), byte formatting via `pb.Bytes`, and SI vs IEC prefix selection. pb is BSD-3-Clause licensed and actively maintained (last push September 7, 2026).

## mpb — Multiple Bars, Orchestrated Rendering

vbauerster/mpb takes a fundamentally different approach: instead of drawing one line, it owns a **render region** of the terminal and repaints every bar in that region on each refresh. You create a container with `mpb.New(...)`, add bars to it, and call `p.Wait()`; the container handles redraws, terminal width, and cleanup. This makes it the only realistic choice when several concurrent operations each need their own bar — parallel downloads, per-shard uploads, fan-out worker pools. The single-bar example from the README shows the container idiom and the decorator API:

```go
p := mpb.New(mpb.WithWidth(64))

total := 100
name := "Single Bar:"
// create a single bar, which will inherit container's width
bar := p.New(int64(total),
	// BarFillerBuilder with custom style
	mpb.BarStyle().Lbound("╢").Filler("▌").Tip("▌").Padding("░").Rbound("╟"),
	mpb.PrependDecorators(
		decor.Name(name, decor.WC{C: decor.DindentRight | decor.DextraSpace}),
		// replace ETA decorator with "done" message, OnComplete event
		decor.OnComplete(decor.AverageETA(decor.ET_STYLE_GO), "done"),
	),
	mpb.AppendDecorators(decor.Percentage()),
)

for range total {
	time.Sleep(time.Duration(rand.Intn(10)+1) * max / 10)
	bar.Increment()
}

// wait for our bar to complete and flush
p.Wait()
```

![mpb dynamic-total demo render](/img/screenshots/mpb-demo.jpg "mpb multi-bar terminal rendering example")

The standout features are **dynamic totals** (a bar's total can change while it runs, which matters when a server reports a content length late), **dynamic add/remove of bars**, **cancellation** of the whole rendering process, and decorators whose widths synchronize across bars (`decor.WCSyncSpace`) so the percentage and ETA columns line up even when bar names differ in length. mpb also ships **EWMA-based ETA decorators** (`decor.EwmaETA`), which smooth over rate spikes — if you feed them per-iteration durations via `bar.EwmaIncrement(time.Since(start))`, the estimate stays sane on networks where throughput fluctuates wildly. The library is published under The Unlicense, meaning public-domain-style freedom with no attribution requirements, and its v8 API is stable and well documented with a dedicated `_examples/` directory per feature. The cost of the container model: you must route all bar updates through mpb's goroutine-safe API and let it own the screen region — you cannot casually `fmt.Println` status lines into the same area while bars are live.

## progressbar — The Simple, Thread-Safe Workhorse

schollz/progressbar was born from a specific frustration: the author needed a bar for **croc**, the peer-to-peer file transfer tool, and found the existing options lacking on some OS. The design goal is stated in the README: *a very simple thread-safe progress bar which should work on every OS without problems* — which is why it deliberately does not support multi-line output. Its basic usage is the shortest of all three:

```golang
bar := progressbar.Default(100)
for i := 0; i < 100; i++ {
	bar.Add(1)
	time.Sleep(40 * time.Millisecond)
}
```

Where progressbar shines is I/O: the bar itself implements `io.Writer`, so any bytes written to it are counted automatically. The canonical download pattern from the README wraps an HTTP response body with an `io.MultiWriter`:

```golang
req, _ := http.NewRequest("GET", "https://dl.google.com/go/go1.14.2.src.tar.gz", nil)
resp, _ := http.DefaultClient.Do(req)
defer resp.Body.Close()

f, _ := os.OpenFile("go1.14.2.src.tar.gz", os.O_CREATE|os.O_WRONLY, 0644)
defer f.Close()

bar := progressbar.DefaultBytes(
	resp.ContentLength,
	"downloading",
)
io.Copy(io.MultiWriter(f, bar), resp.Body)
```

![progressbar basic demo from official examples](/img/screenshots/progressbar-demo.jpg "schollz/progressbar terminal output example")

A clever touch: pass `-1` as the total and the bar **automatically becomes a spinner** — ideal for phases whose duration is unknowable (server polling, retries). Customization is option-function based, including ANSI color codes and full theme replacement:

```golang
bar := progressbar.NewOptions(1000,
	progressbar.OptionSetWriter(ansi.NewAnsiStdout()), // install "github.com/k0kubun/go-ansi"
	progressbar.OptionEnableColorCodes(true),
	progressbar.OptionShowBytes(true),
	progressbar.OptionSetWidth(15),
	progressbar.OptionSetDescription("[cyan][1/3][reset] Writing moshable file..."),
	progressbar.OptionSetTheme(progressbar.Theme{
		Saucer:        "[green]=[reset]",
		SaucerHead:    "[green]>[reset]",
		SaucerPadding: " ",
		BarStart:      "[",
		BarEnd:        "]",
	}))
```

progressbar is MIT licensed with 4,700+ stars, and its conservative single-line design makes it the safest default when your bar shares the terminal with application log output — there is no redraw region to corrupt.

## Terminal Rendering Pitfalls and Integration Traps

Progress bars look trivial until they misbehave in production CLIs. The recurring traps, regardless of library:

1. **Never write bars to stdout by default.** The classic Unix contract is stdout = data, stderr = diagnostics. pb defaults to `os.Stderr` for exactly this reason; if you render to stdout, `mycli | jq` will corrupt the pipeline. progressbar and mpb let you set the writer — make it stderr unless the bar *is* the product output.
2. **Detect non-TTY and disable.** When output is piped to a file or CI log, bar redraws become thousands of noise lines. Gate rendering on `term.IsTerminal` (or your library's check) and fall back to periodic single-line updates or silence. All three libraries tolerate this pattern; none do it for you automatically.
3. **Concurrent log lines interleave with redraws.** With pb/progressbar, a `fmt.Println` from another goroutine lands mid-bar-line. Route all status logging through one writer and render bars on their own goroutine, or use mpb and keep application logs outside its managed region.
4. **ETA lies on spiky workloads.** Average-based ETAs swing wildly when transfer speed oscillates. If your task is network I/O, prefer mpb's EWMA decorators (or compute your own smoothed rate) over the built-in average.
5. **Refresh rate vs. CPU.** Repainting 60 times per second in a tight in-memory loop burns CPU for nothing. The default 200 ms refresh is a good baseline; lower it only for visibly fast operations.
6. **Terminal width changes.** Bars hard-coded to 80 columns look broken in narrow panes and wasteful in wide ones. mpb auto-detects the terminal width (override with `mpb.WithWidth`); progressbar's `OptionSetWidth` defaults to a fixed width that you may want to size from your terminal at startup.
7. **Unicode fillers need font support.** Box-drawing and block characters (`╢▌░`, `↖↗↘↙`) render fine in modern terminals and poorly in some Windows consoles and CI viewers. pb and mpb both let you swap in ASCII fillers — do it behind an env-var or platform check.
8. **`Finish()` vs `Wait()`.** pb/progressbar want a final `Finish()` to print the completed line; mpb wants `p.Wait()` to flush the container. Skipping them leaves a half-drawn bar or a missing newline when the process exits.

## Progress Bars in the Wider CLI Ecosystem

Before you build, ask whether a bar is even the right component. Interactive terminal applications with menus, keybindings, and panels are a different problem class — that is a job for a full terminal UI framework such as Bubble Tea or tview rather than a bar library; see our [Go TUI framework comparison](../2026-09-09-go-tui-frameworks-bubbletea-tview-termui-comparison/) for that decision. If your need is broader CLI feedback — spinners for indeterminate waits, colored status text, and checkmark sequences — the cross-language [spinner library guide](../2026-07-27-cli-spinner-libraries-ora-yaspin-indicatif-halo/) covers the alternatives. And if you are choosing a progress library for a Python or Rust tool rather than Go, the [tqdm vs indicatif vs cliprogress comparison](../2026-06-20-cli-progress-bar-libraries-tqdm-indicatif-cliprogress-rich/) maps the same decision space in those ecosystems. For Go specifically, the three libraries here have converged on the same defaults after a decade of iteration — single-line updates, stderr output, thread safety, and IO-aware counting — so your real differentiator is whether you need one bar (pb or progressbar) or many (mpb).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Progress Bar Libraries in 2026: mpb vs pb vs progressbar",
  "description": "Compare cheggaaa/pb, vbauerster/mpb and schollz/progressbar for Go CLI progress bars in 2026: real code samples, multi-bar rendering, EWMA ETA, io.Writer integration, licensing and terminal pitfalls.",
  "datePublished": "2026-09-10",
  "dateModified": "2026-09-10",
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

**Which Go progress bar library is the most popular?**
schollz/progressbar leads by stars (4,700+) because of its simplicity and its use in the croc file-transfer tool, followed by cheggaaa/pb (3,720+). mpb has fewer stars (2,500+) but is the standard choice when you need multiple simultaneous bars, since it is the only one of the three built around an orchestrated rendering container.

**Can these libraries show multiple progress bars at once?**
Only mpb renders multiple bars reliably — you create one `mpb.New()` container, add a bar per concurrent operation, and let the container repaint the whole region. pb and progressbar are single-line libraries; stacking them requires manual terminal management and is not supported.

**Do these libraries work on Windows?**
All three are cross-platform and work on Windows terminals, but box-drawing characters and full-region redraws (mpb) behave differently across Windows console hosts — Windows Terminal is fine, legacy conhost is not. progressbar was explicitly designed to work on every OS without problems and is the most conservative choice for mixed environments.

**How do I avoid progress bar spam in CI logs?**
Detect whether stdout/stderr is a terminal (for example with `golang.org/x/term`'s `IsTerminal`) and skip bar rendering entirely when it is not. Alternatively render bars to stderr at a low refresh rate. None of the three libraries disable themselves automatically when piped.

**Are these libraries free for commercial use?**
Yes. cheggaaa/pb is BSD-3-Clause, schollz/progressbar is MIT, and mpb is released under The Unlicense (public-domain dedication). There are no paid tiers, telemetry requirements, or copyleft obligations in any of the three.

**Which library handles downloads and byte counting best?**
For byte-oriented progress, schollz/progressbar implements `io.Writer` so `io.Copy(io.MultiWriter(file, bar), resp.Body)` just works, and cheggaaa/pb provides `NewProxyReader` for the same job. mpb tracks bytes through decorators and manual increments, which is more flexible for non-stream workloads but requires more code for a plain download.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
