---
title: "CLI Spinner Libraries: ora vs yaspin vs indicatif vs halo"
date: "2026-07-27"
tags: ["cli", "developer-tools", "nodejs", "python", "rust", "terminal", "ux"]
draft: false
---

A well-designed command-line tool communicates progress to the user. When a task takes more than a second — whether it is fetching data from an API, building a project, or processing a file — an animated spinner transforms an opaque wait into a clear signal that work is happening. This guide compares the leading CLI spinner libraries across JavaScript, Python, and Rust, covering animation quality, composability with progress bars, and integration patterns.

## Why Spinners Matter

Without visual feedback during long-running operations, users are left wondering if the tool has frozen. A spinner with descriptive text — "Installing dependencies..." followed by a green checkmark — turns anxiety into confidence. The best spinner libraries provide dozens of built-in animation styles, automatic terminal handling (hiding the cursor, clearing the line), and composability with progress bars for measurable tasks.

| Feature | ora (JS) | yaspin (Python) | indicatif (Rust) | halo (Python) |
|---|---|---|---|---|
| **Language** | JavaScript/TypeScript | Python | Rust | Python |
| **GitHub Stars** | 9,729 | 912 | 5,189 | 3,024 |
| **Spinner Styles** | 70+ (cli-spinners) | 60+ | 12+ built-in | 60+ |
| **Progress Bars** | Separate | Separate | Built-in (composable) | No |
| **Custom Spinners** | Yes | Yes | Yes | Yes |
| **Non-TTY Safe** | Yes | Yes | Yes | Yes |
| **Async Support** | Native Promise | Context manager | Sync | Context manager |
| **Color Output** | Via chalk | Via termcolor | Built-in | Via termcolor |
| **Last Update** | June 2026 | Feb 2026 | July 2026 | June 2024 |

## ora: The JavaScript Spinner Standard

ora is the most popular terminal spinner library in the npm ecosystem, with nearly 10,000 stars and over 5 million weekly downloads. It provides 70+ built-in spinner animations from the `cli-spinners` package and a clean, chainable API.

```javascript
import ora from 'ora';

const spinner = ora('Installing dependencies...').start();

try {
    // Simulate a long-running task
    await installDependencies();
    spinner.succeed('Dependencies installed successfully');
} catch (error) {
    spinner.fail('Installation failed');
}

// With progress text updates
const buildSpinner = ora('Building project').start();
await delay(500);
buildSpinner.text = 'Compiling TypeScript...';
await delay(800);
buildSpinner.text = 'Bundling assets...';
await delay(600);
buildSpinner.succeed('Build complete (2.3s)');

// Custom spinner style
const customSpinner = ora({
    text: 'Processing data',
    spinner: 'dots12',
    color: 'cyan',
}).start();
```

ora's strengths include its vast animation library, built-in color support via `chalk`, and straightforward API. For progress bars, JavaScript developers typically pair ora with `cli-progress` or use `listr2` (which wraps ora for multi-step task lists).

## yaspin: Python's Lightweight Spinner

yaspin ("Yet Another SPINner") brings elegant terminal spinners to Python with a focus on simplicity and context-manager ergonomics. It supports 60+ spinner styles and integrates naturally with Python's `with` statement pattern.

```python
from yaspin import yaspin
from yaspin.spinners import Spinners
import time

# Basic usage with context manager
with yaspin(text="Loading data from API...", color="cyan") as sp:
    time.sleep(2)
    sp.text = "Processing 1,432 records..."
    time.sleep(1.5)
    sp.ok("✔ Data loaded successfully")

# Manual control for dynamic updates
sp = yaspin(Spinners.dots12, text="Downloading file...", color="yellow")
sp.start()

try:
    for chunk in download_file():
        sp.text = f"Downloading... {chunk.percent:.1f}%"
    sp.green.ok("✔ Download complete")
except Exception:
    sp.red.fail("✘ Download failed")

# Using different spinner styles
spinners_to_try = [
    Spinners.dots, Spinners.line, Spinners.moon,
    Spinners.arc, Spinners.star, Spinners.bouncingBar,
]

for spinner_style in spinners_to_try:
    with yaspin(spinner_style, text=f"Style: {spinner_style.name}") as sp:
        time.sleep(1.5)
```

yaspin's `ok()` and `fail()` methods automatically stop the spinner and replace it with a success or failure symbol — a pattern that works well in scripts with clear start/finish boundaries. The `Spinners` enum provides access to all animations from the `cli-spinners` JSON specification.

## indicatif: Rust's Progress Powerhouse

indicatif takes a broader approach than pure spinner libraries — it provides both spinners and progress bars in a unified library with first-class composability. With over 5,000 GitHub stars, it is the standard for terminal progress in the Rust ecosystem, used by tools like `cargo`, `rustup`, and `fd`.

```rust
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};
use std::{thread, time::Duration};

fn main() {
    // Single spinner with template
    let spinner = ProgressBar::new_spinner();
    spinner.set_style(
        ProgressStyle::with_template("{spinner:.green} {msg}")
            .unwrap()
            .tick_strings(&["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    );
    spinner.set_message("Compiling...");
    
    for _ in 0..30 {
        spinner.tick();
        thread::sleep(Duration::from_millis(50));
    }
    spinner.finish_with_message("✓ Compiled successfully");

    // Composable multi-progress: spinner + progress bars
    let multi = MultiProgress::new();
    
    let main_spinner = multi.add(ProgressBar::new_spinner());
    main_spinner.set_message("Building project...");
    
    let compile_bar = multi.add(ProgressBar::new(100));
    compile_bar.set_style(
        ProgressStyle::with_template(
            "  [{bar:40.cyan/blue}] {percent}% {msg}"
        ).unwrap()
    );
    compile_bar.set_message("TypeScript → JS");
    
    for i in 0..=100 {
        compile_bar.set_position(i);
        main_spinner.tick();
        thread::sleep(Duration::from_millis(20));
    }
    compile_bar.finish_with_message("✓ TypeScript compiled");
    main_spinner.finish_with_message("✓ Build complete");
}
```

indicatif's `MultiProgress` allows multiple progress bars and spinners to render simultaneously without terminal flickering — a feature that JavaScript and Python spinner libraries typically require additional packages to achieve. The template-based style system, while powerful, requires more upfront configuration than ora or yaspin.

## halo: Python's Styled Alternative

halo brings a specific aesthetic to Python terminal spinners — it supports colored output, text placement around the spinner, and Jupyter notebook integration out of the box. With 3,024 GitHub stars, it predates yaspin and influenced the Python spinner ecosystem.

```python
import halo
import time

# Basic spinner with halo
spinner = halo.Halo(text='Loading', spinner='dots', color='magenta')
spinner.start()
time.sleep(2)
spinner.succeed('Loaded successfully')

# Nesting spinners for sub-tasks
with halo.Halo(text='Installing packages', spinner='line', color='cyan') as main_sp:
    # Simulate sub-steps
    time.sleep(0.8)
    main_sp.text = 'Installing numpy (1/3)'
    time.sleep(1.2)
    main_sp.text = 'Installing pandas (2/3)'
    time.sleep(0.9)
    main_sp.text = 'Installing scikit-learn (3/3)'
    time.sleep(1.0)
    main_sp.succeed('3 packages installed')
```

halo's main differentiator is Jupyter/IPython support — it renders spinners correctly in notebook cells, whereas yaspin focuses on terminal environments. However, halo has been less actively maintained (last release June 2024), and for new Python projects, yaspin or `rich.console.Status` are generally preferred.

## Integration Patterns

**Pairing with progress bars:** In production CLIs, spinners signal ongoing work for indeterminate-duration tasks, while progress bars show completion percentage for measurable tasks. Rust's indicatif handles both natively. In JavaScript, `listr2` wraps ora for multi-step task lists. In Python, `rich` provides both `Status` (spinner) and `Progress` in a single library.

**Non-TTY environments:** All four libraries degrade gracefully in non-interactive terminals (CI pipelines, redirected output). They suppress animations and output plain text instead.

**Error handling:** ora, yaspin, and halo all provide `.fail()` methods that replace the spinner with a red X and error message. indicatif uses `.finish_with_message()` or `.abandon_with_message()`.

For more terminal tooling comparisons, explore our [Go CLI Libraries guide](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/), our [Terminal History Sync comparison](../2026-04-29-atuin-vs-mcfly-vs-bash-history-self-hosted-terminal-history-sync-guide-2026/), and our [JSON Processing CLI Tools overview](../2026-06-17-self-hosted-json-processing-cli-tools-jq-vs-fx-vs-jid/).

## Composability with Task Runners and Observability

Modern CLI tools rarely use spinners in isolation — they are part of a broader output strategy that includes structured logging, progress bars, and task orchestration.

**ora + listr2 (JavaScript):** The `listr2` library wraps ora spinners to create elegant multi-step task lists. Each step gets its own spinner with a title, and steps can run sequentially or in parallel. When a step completes, its spinner transforms into a checkmark. This pattern is used by tools like `create-react-app` and `nx` for project scaffolding.

```javascript
import { Listr } from 'listr2';

const tasks = new Listr([
    { title: 'Installing dependencies', task: () => installDeps() },
    { title: 'Configuring TypeScript', task: () => setupTS() },
    { title: 'Setting up ESLint', task: () => setupLint() },
], { concurrent: false });

await tasks.run();
```

**indicatif + tracing (Rust):** indicatif integrates with the `tracing` ecosystem through `tracing-indicatif`. This allows structured log spans to automatically get progress bars or spinners — when a span is entered, indicatif renders a spinner; when it exits, the spinner is replaced with timing information. This bridges the gap between developer-oriented structured logs and user-facing terminal output.

**yaspin + rich (Python):** For Python tools that need both formatted output and spinners, `rich` provides `Progress` and `Status` (spinner) that work alongside its table, syntax highlighting, and layout features. However, if you only need a spinner, yaspin's 60+ animation styles provide more variety than `rich.status`. Many projects use yaspin for the spinner and `rich` for everything else.


## FAQ

### When should I use a spinner vs. a progress bar?

Use a spinner when the duration is unknown (API calls, network operations) and a progress bar when you know the total work amount (file downloads, batch processing). Many libraries allow transitioning from spinner to progress bar when the total becomes known mid-operation.

### Can I display multiple spinners simultaneously?

indicatif (Rust) supports this natively via `MultiProgress`. In JavaScript, `listr2` provides multi-step task lists with individual spinners. In Python, `rich` offers `Live` displays for multiple concurrent renderables.

### Which library works best in Docker/CI environments?

All four libraries detect non-TTY environments and disable animations automatically. indicatif and ora are particularly well-tested in CI pipelines. yaspin uses the `TERM` environment variable for detection and falls back to plain text.

### How do I create custom spinner animations?

ora and yaspin accept custom frame arrays (arrays of strings that cycle frame by frame). You can define custom animations like `["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]` for a moon phase spinner. indicatif uses `tick_strings()` for custom frame sequences.

### What is the best overall choice for a new project?

For JavaScript/TypeScript: ora (9,729 stars, actively maintained, huge ecosystem). For Python: yaspin if you want just spinners, `rich` if you want spinners + progress bars + tables + syntax highlighting in one library. For Rust: indicatif is the clear winner with built-in composability and adoption by the Rust toolchain itself.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CLI Spinner Libraries: ora vs yaspin vs indicatif vs halo",
  "description": "Cross-language comparison of terminal spinner libraries — ora (JavaScript), yaspin (Python), indicatif (Rust), and halo (Python) — covering animation styles, progress bar composability, and integration patterns for polished CLI tools.",
  "datePublished": "2026-07-27",
  "dateModified": "2026-07-27",
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
