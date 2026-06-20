---
title: "CLI Progress Bar Libraries Compared: tqdm vs indicatif vs cli-progress vs rich.progress"
date: "2026-06-20"
tags: ["cli", "terminal", "libraries", "progress-bar", "developer-tools", "python", "rust", "nodejs"]
draft: false
---

Command-line applications often perform long-running operations — downloading large files, processing datasets, or running batch transformations. Without visual feedback, users are left wondering whether the program is working or frozen. Progress bar libraries solve this by rendering animated progress indicators, estimated time remaining, and throughput statistics directly in the terminal.

This guide compares four leading open-source progress bar libraries: Python's ubiquitous **tqdm** (31K+ stars), Rust's elegant **indicatif** (5.1K+ stars), Node.js **cli-progress** (1.2K+ stars), and Python's feature-rich **rich.progress** (part of Rich, 56K+ stars). We cover API design, customization, multi-progress support, and integration patterns.

## Why Progress Bars Matter in CLI Tools

A well-implemented progress bar transforms the user experience from uncertainty to confidence. It shows:

- **Completion percentage** — how much work is done
- **Elapsed and estimated time** — when will it finish?
- **Throughput** — items/second or bytes/second
- **Current item** — what's being processed right now

For self-hosted tools and automation scripts, progress bars provide operational visibility without requiring a web dashboard. You can monitor backups, data migrations, and batch processing directly from the terminal.

## Feature Comparison

| Feature | tqdm (Python) | indicatif (Rust) | cli-progress (Node) | rich.progress (Python) |
|---------|-------------|-----------------|-------------------|---------------------|
| Stars | 31,211 ⭐ | 5,168 ⭐ | 1,251 ⭐ | 56,655 ⭐ (Rich) |
| Language | Python | Rust | JavaScript/TS | Python |
| Multi-bar | ✅ tqdm.write | ✅ MultiProgress | ✅ MultiBar | ✅ Progress columns |
| Nested bars | ✅ | ✅ | ❌ | ✅ |
| Custom styles | ✅ format strings | ✅ Template | ✅ Presets + custom | ✅ Columns system |
| File-like wrapper | ✅ tqdm.wrapattr | ❌ | ❌ | ✅ open/wrap |
| Jupyter support | ✅ tqdm.notebook | ❌ | ❌ | ✅ rich.jupyter |
| Async support | ✅ tqdm.asyncio | ✅ tokio | ✅ async iteration | ✅ rich.live |
| Throughput stats | ✅ | ✅ | ✅ | ✅ SpeedColumn |
| ETA calculation | ✅ averaged | ✅ exponential | ✅ linear | ✅ smoothed |
| License | MPL-2.0 / MIT | MIT | MIT | MIT |

## tqdm (Python)

tqdm (taqaddum, Arabic for "progress") is the most widely used progress bar library in the Python ecosystem. It wraps any iterable with a single function call and automatically computes speed, ETA, and elapsed time.

```python
from tqdm import tqdm
import time

# Basic usage — wrap any iterable
for item in tqdm(range(1000), desc="Processing", unit="items"):
    time.sleep(0.001)

# Manual update mode
pbar = tqdm(total=500, desc="Downloading", unit="B", unit_scale=True)
for chunk in download_stream():
    pbar.update(len(chunk))
pbar.close()

# Nested progress bars
for i in tqdm(range(5), desc="Outer"):
    for j in tqdm(range(100), desc="Inner", leave=False):
        process(i, j)

# File copying with progress
with tqdm.wrapattr(open('output.bin', 'wb'), 'write',
                   total=file_size, desc="Copying") as fout:
    for chunk in iter(lambda: fin.read(8192), b''):
        fout.write(chunk)
```

tqdm's simplicity is its superpower — 90% of use cases are covered by `tqdm(iterable)`. For more control, the `tqdm` object exposes `set_description()`, `set_postfix()`, and `refresh()` methods. It also integrates with pandas via `tqdm.pandas()` for progress bars on DataFrame operations.

## indicatif (Rust)

indicatif brings Rust's performance and type safety to terminal progress reporting. Its `ProgressBar`, `MultiProgress`, and `ProgressStyle` types compose elegantly for complex progress UIs.

```rust
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};
use std::thread;
use std::time::Duration;

fn main() {
    // Single progress bar
    let pb = ProgressBar::new(1000);
    pb.set_style(ProgressStyle::default_bar()
        .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta})")
        .unwrap()
        .progress_chars("#>-"));

    for _ in 0..1000 {
        pb.inc(1);
        thread::sleep(Duration::from_millis(1));
    }
    pb.finish_with_message("Done!");

    // Multi-progress with parallel downloads
    let m = MultiProgress::new();
    let bars: Vec<_> = (0..4).map(|i| {
        let bar = m.add(ProgressBar::new(500));
        bar.set_message(format!("File {}", i));
        bar
    }).collect();
    // ... spawn threads updating each bar
}
```

indicatif excels in Rust's async ecosystem — combine with tokio for progress on async streams. The `ProgressBar::wrap_*` family provides file-like wrappers similar to tqdm.

## rich.progress (Python)

Rich's `Progress` system takes a column-based approach: you compose a progress display from TimeElapsedColumn, BarColumn, TextColumn, and custom columns.

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
import time

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TimeElapsedColumn(),
) as progress:
    task = progress.add_task("[green]Processing...", total=1000)
    while not progress.finished:
        progress.update(task, advance=1)
        time.sleep(0.001)

# Multiple tasks with live display
with Progress() as progress:
    download = progress.add_task("[cyan]Downloading", total=file_size)
    extract = progress.add_task("[magenta]Extracting", total=archive_count)
    while not progress.finished:
        progress.update(download, advance=chunk_size)
        if download_done:
            progress.update(extract, advance=1)
```

Rich integrates naturally with its own `Live` display system — you can mix progress bars with live-updating tables, syntax-highlighted code, and styled text in the same terminal output.

## Choosing the Right Library

For Python projects, tqdm offers the lowest friction — one import, one function call. If you need rich terminal output beyond progress bars (tables, Markdown rendering, syntax highlighting), use rich.progress for consistency. For Rust applications, indicatif is the clear choice with its expressive API and MultiProgress support. Node.js developers building CLI tools should reach for cli-progress with its pluggable preset system.

For more terminal tooling comparisons, see our guide on [self-hosted terminal multiplexers](../self-hosted-terminal-multiplexer-tmux-screen-abduco-remote-dev-guide-2026/), our [terminal system monitor comparison](../self-hosted-terminal-dashboard-btop-glances-bottom-system-monitoring-guide-2026/), and our [shell script linting tools guide](../2026-06-17-shell-script-linting-shellcheck-shfmt-bashate/).

## Advanced Customization and Styling

Progress bar customization goes beyond changing colors and characters. Each library offers a distinct styling system:

**tqdm format strings** use a mini-DSL inside curly braces: `{l_bar}{bar}{r_bar}`. The `bar_format` parameter supports nested expressions for building complex displays:

```python
from tqdm import tqdm

tqdm(iterable, bar_format='{desc:<20}{percentage:3.0f}%|{bar:30}| '
      '{n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')
```

**indicatif templates** combine static text with `{placeholders}` enclosed in square brackets for styled segments:

```rust
pb.set_style(ProgressStyle::with_template(
    "{spinner} [{elapsed_precise}] [{wide_bar:.cyan/blue}] {bytes}/{total_bytes} ({eta})"
).unwrap());
```

**rich.progress columns** decompose the display into independent widgets — `BarColumn`, `TextColumn`, `TaskProgressColumn`, and custom `ProgressColumn` subclasses. This composable architecture makes it the most flexible for complex layouts:

```python
from rich.progress import Progress, BarColumn, TextColumn

Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    TextColumn("{task.completed} of {task.total}"),
)
```

**Choosing the right style** depends on your audience. Data engineers prefer throughput numbers (items/sec, MB/s). End users appreciate percentage + ETA. DevOps scripts benefit from compact single-line formats for log-friendly output. All four libraries support conditional formatting — display different information based on whether the total is known or the operation is complete.

## CLI Progress in Containerized and CI/CD Environments

When running in Docker containers or CI/CD pipelines, terminal progress bars encounter unique challenges. Non-TTY stdout (common in CI runners like GitHub Actions and GitLab CI) disables ANSI escape sequences, causing progress bars to render as repeated lines instead of in-place updates:

- **tqdm** auto-detects non-TTY output and falls back to logging with `tqdm(..., position=0, miniters=1)` producing one log line per update
- **indicatif** checks `Term::is_term()` and should be wrapped with `ProgressBar::with_draw_target(ProgressDrawTarget::stdout_nohz())` for CI environments to suppress terminal control sequences
- **cli-progress** provides a `noTTYOutput` option and `fps` limiter to control output rate in logs
- **rich.progress** offers `Progress(..., transient=False)` which renders full progress lines instead of ANSI-refresh sequences, ideal for log-friendly progress tracking

For Docker deployments, ensure your Dockerfile sets `ENV TERM=xterm-256color` if you want interactive progress in `docker run -it` sessions, and use `--progress=plain` with BuildKit for build-time progress output. When piping command output through tools like `tee`, all libraries should be configured for non-TTY mode to prevent log file corruption with escape code sequences.

## FAQ

### When should I use a spinner instead of a progress bar?

Use spinners when you can't determine total work upfront — API calls, database queries, or network operations with unknown size. Progress bars are better when you have a known total (file size, item count). Both tqdm and indicatif support spinners as a display mode.

### How do I display progress across multiple threads?

Use each library's multi-progress API: `MultiProgress` in indicatif, `MultiBar` in cli-progress, or multiple tasks in rich.progress. These render multiple progress bars simultaneously without terminal corruption. tqdm's `position` parameter handles multi-bar layout when using `tqdm.write()` for message output.

### Can I use progress bars in CI/CD logs?

Yes, but disable dynamic rendering for non-TTY outputs. tqdm auto-detects TTY and falls back to periodic log lines. indicatif checks `indicatif::Term::is_term()`. rich.progress uses `Progress(..., transient=False)`. Most CI platforms pipe output and automatically disable ANSI refresh sequences.

### Do these libraries support milliseconds in time estimates?

All four support sub-second updates but ETA precision varies. tqdm's `mininterval` parameter controls refresh rate (default 0.1s). indicatif uses configurable tick rates. rich.progress defaults to 10 FPS refresh. For sub-second operations (< 1 second duration), progress bars add overhead — consider skipping them.

### How do I log messages alongside a running progress bar?

Use each library's logging channel to avoid corrupting the progress display: `tqdm.write()` in tqdm, `progress.println()` in indicatif, `progress.console.log()` in rich, and `multiBar.log()` in cli-progress. These ensure log lines appear above the progress bar without visual artifacts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CLI Progress Bar Libraries Compared: tqdm vs indicatif vs cli-progress vs rich.progress",
  "description": "In-depth comparison of open-source command-line progress bar libraries — tqdm, indicatif, cli-progress, and rich.progress — with code examples and integration patterns for self-hosted CLI tools.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
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
