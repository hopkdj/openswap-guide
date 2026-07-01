---
title: "Python Terminal UI Libraries: Textual vs Rich vs prompt_toolkit vs urwid (2026 Comparison)"
date: "2026-07-01"
tags: ["python", "terminal", "tui", "cli", "developer-tools", "libraries", "textual", "rich", "prompt-toolkit", "urwid"]
draft: false
---

## Introduction

Command-line interfaces don't have to be plain text streams. Modern Python terminal UI libraries can render rich layouts with colors, tables, progress bars, interactive widgets, and even full TUI applications that rival GUI tools in usability. Whether you're building a developer dashboard, a system monitoring tool, or an interactive REPL, the right terminal library transforms the user experience.

This guide compares four leading Python terminal UI libraries: Textual, Rich, prompt_toolkit, and urwid — covering their strengths, use cases, and practical code examples.

## Library Overview

### Textual (36,444 ⭐)

Textual is a Rapid Application Development framework for terminal applications. Built by Textualize (the creators of Rich), it provides a reactive, widget-based architecture inspired by modern web frameworks. You build TUIs by composing widgets like buttons, data tables, and input fields, with CSS-like styling.

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class MyApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Hello, Terminal World!")
        yield Footer()

if __name__ == "__main__":
    MyApp().run()
```

### Rich (56,738 ⭐)

Rich is the Swiss Army knife of terminal output formatting. It adds colors, styled tables, markdown rendering, syntax-highlighted code, progress bars, and tree displays to your Python scripts. Rich is not a full TUI framework — it enhances existing output rather than building interactive applications.

```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="Server Status")
table.add_column("Server")
table.add_column("Status")
table.add_row("web-01", "[green]Running[/green]")
table.add_row("db-01", "[red]Down[/red]")
console.print(table)
```

### prompt_toolkit (10,517 ⭐)

prompt_toolkit focuses on building powerful interactive command-line input experiences. It handles syntax highlighting, autocompletion, multi-line editing, and key bindings. It's the engine behind IPython, ptpython, and many other interactive shells.

```python
from prompt_toolkit import prompt

text = prompt("Enter your name: ")
print(f"Hello, {text}!")
```

### urwid (3,010 ⭐)

urwid is the veteran of Python terminal UI libraries — stable, lightweight, and battle-tested. It provides a canvas-based widget system for building full-screen terminal applications. urwid is used by tools like bpython and pudb.

```python
import urwid

def on_keypress(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()

text = urwid.Text("Hello, urwid world! Press Q to quit.")
fill = urwid.Filler(text, 'top')
loop = urwid.MainLoop(fill, unhandled_input=on_keypress)
loop.run()
```

## Feature Comparison Table

| Feature | Textual | Rich | prompt_toolkit | urwid |
|---------|---------|------|---------------|-------|
| GitHub Stars | 36,444 | 56,738 | 10,517 | 3,010 |
| Type | Full TUI Framework | Output Formatting | Input/REPL | Full TUI Framework |
| Widget System | Yes (reactive) | No | Yes (input) | Yes (canvas) |
| CSS Styling | Yes | No | No | No |
| Tables | Yes | Yes (excellent) | No | Limited |
| Syntax Highlighting | Via Rich | Yes | Yes | No |
| Code/Log Rendering | Via Rich | Yes (excellent) | Yes | No |
| Progress Bars | No (use Rich) | Yes (excellent) | No | No |
| Trees/Panels | No (use Rich) | Yes | No | No |
| Markdown Rendering | No (use Rich) | Yes | No | No |
| Autocompletion | No | No | Yes (excellent) | No |
| Key Bindings | Yes | No | Yes (excellent) | Yes |
| Mouse Support | Yes | No | Yes | Yes |
| ANSI Support | Full | Full | Full | Full |
| Async Support | Yes | Partial | Yes | Yes (event loop) |
| Learning Curve | Moderate | Low | Moderate | High |
| License | MIT | MIT | BSD | LGPL |

## When to Use Each Library

**Textual** is the go-to choice for building full-featured terminal applications. If you need multiple screens, data tables, forms, and a modern widget-based architecture, Textual's reactive design patterns will save you months of work compared to lower-level frameworks. It's ideal for dashboards, admin panels, and interactive tools.

**Rich** should be in every Python developer's toolkit. Use it to add colored log output, formatted tables, progress bars for long-running scripts, and syntax-highlighted code displays. Rich complements all the other libraries — Textual and prompt_toolkit both use Rich internally for rendering.

**prompt_toolkit** is essential when you need a sophisticated interactive input experience. Use it to build custom REPLs, CLI tools with autocompletion, and multi-line code editors. It's the power behind IPython and is battle-tested at massive scale.

**urwid** is the pragmatic choice for resource-constrained environments or when you need maximum control over terminal rendering. It's lightweight (~200KB), has no external dependencies beyond the standard library, and its canvas model gives you pixel-perfect control.

## Real-World Application: System Dashboard with Textual + Rich

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Container
import psutil
import asyncio

class SystemDashboard(App):
    CSS = """
    #stats { height: auto; margin: 1; }
    DataTable { height: 20; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("System Dashboard", id="stats"),
            DataTable(id="processes"),
        )
        yield Footer()

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("PID", "Name", "CPU%", "Memory")
        self.update_table()

    def update_table(self):
        table = self.query_one(DataTable)
        table.clear()
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            info = proc.info
            table.add_row(
                str(info['pid']),
                info['name'] or '',
                f"{info['cpu_percent'] or 0:.1f}",
                f"{info['memory_percent'] or 0:.1f}%",
            )

if __name__ == "__main__":
    SystemDashboard().run()
```

## Interactive REPL with prompt_toolkit

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

commands = WordCompleter(['help', 'status', 'connect', 'disconnect', 'exit'])
session = PromptSession(
    completer=commands,
    history=FileHistory('.mycli_history'),
    auto_suggest=AutoSuggestFromHistory(),
)

while True:
    try:
        text = session.prompt('myapp> ')
        if text == 'exit':
            break
        print(f"Executing: {text}")
    except KeyboardInterrupt:
        continue
    except EOFError:
        break
```

## Deployment and Installation

```bash
# Install all four libraries
pip install textual rich prompt_toolkit urwid

# Or individually
pip install textual     # Full TUI framework
pip install rich        # Output formatting
pip install prompt_toolkit  # Interactive input
pip install urwid       # Lightweight TUI
```

For related terminal tools, see our [Terminal Rendering Libraries guide](../2026-06-25-terminal-rendering-libraries-libvterm-crossterm-notcurses-libvaxis/), our [C++ Terminal UI Libraries comparison](../2026-06-26-cpp-terminal-ui-libraries-ftxui-replxx-linenoise-tabulate/), and our [Terminal Sharing tools guide](../self-hosted-terminal-sharing-tmate-ttyd-wetty-2026/).

## Why Choose Python Terminal UI Libraries?

Building CLI tools has evolved far beyond `print()` statements and `input()` prompts. Today's developers expect rich formatting, interactive navigation, and visually informative displays — even in the terminal. Python's diverse terminal UI ecosystem gives you options ranging from simple colored output (Rich) to full application frameworks (Textual). Whether you're building an internal tool for your team, a system monitoring dashboard, or a developer-facing CLI, investing in terminal UI polish significantly improves usability and adoption.

## Performance and Ecosystem Integration

When choosing a terminal UI library, raw rendering speed is rarely the bottleneck — modern terminals handle ANSI escape sequences at thousands of frames per second. The real performance considerations are startup time, memory usage for large datasets, and event loop efficiency.

Rich is the undisputed performance leader for output formatting. It uses lazy rendering — content is only computed when displayed — and its `Live` display context manager efficiently updates only changed portions of the terminal. For scripts that process large logs or streaming data, Rich's incremental rendering can handle millions of lines without memory growth.

Textual's reactive architecture includes a CSS layout engine and a widget tree, giving it a larger memory footprint but enabling complex UI patterns that would be impractical with lower-level libraries. For applications with hundreds of interactive widgets, Textual's virtual DOM approach batches terminal updates and only re-renders widgets whose state has changed. The Textualize team actively benchmarks against popular terminal applications and maintains sub-16ms render times on modern hardware.

prompt_toolkit's event loop architecture is finely tuned for interactive latency. It renders input buffers asynchronously and pre-computes completions in background threads. For applications with complex syntax highlighting (like IPython's code editor), prompt_toolkit's lexer cache and incremental parser keep keystroke-to-display latency under 10ms.

urwid's canvas model is the most memory-efficient — it allocates a fixed grid of terminal cells and paints directly to it. For embedded systems or constrained environments where every megabyte counts, urwid's ~200KB footprint and zero-dependency design are significant advantages. However, urwid's event loop requires more manual wiring compared to Textual or prompt_toolkit's async-native designs.

All four libraries support TrueColor (24-bit) terminals, which are now standard on modern systems. If your application targets older terminals or SSH sessions with limited color support, both urwid and prompt_toolkit offer graceful degradation to 256-color and 16-color palettes. Rich and Textual assume a TrueColor-capable terminal by default.

For testing terminal applications, Textual provides a built-in testing framework with snapshot-based assertions (`textual run --dev`). prompt_toolkit includes an `Application` test harness for simulating key presses. Rich and urwid require manual terminal emulation for testing but integrate well with standard Python test runners.

## FAQ

### Which library should I use for a simple CLI tool?

Start with Rich for formatting output. It's minimal effort and instantly improves readability with colored text, tables, and progress bars. Add prompt_toolkit if you need interactive input with autocompletion. Only reach for Textual or urwid when you need a full-screen application.

### Can I use Textual and Rich together?

Yes — Textual is built on top of Rich and uses it for all terminal rendering. When you install Textual, you get Rich as a dependency. You can use Rich's API directly within a Textual application for custom rendering.

### Is Textual suitable for production applications?

Textual is production-ready and actively maintained (updated daily). Companies like Textualize use it commercially, and it has a growing ecosystem of plugins and widgets. The framework handles terminal resizing, focus management, and keyboard navigation automatically.

### What terminal emulators are supported?

All four libraries support modern terminal emulators with full ANSI/TrueColor support. Textual requires a relatively modern terminal (iTerm2, Windows Terminal, kitty, or gnome-terminal). urwid works with any terminal including legacy VT100/ANSI terminals.

### How does prompt_toolkit compare to GNU readline?

prompt_toolkit is significantly more powerful than readline. It supports syntax highlighting, multi-line editing, asynchronous completions, floating autocomplete menus, and custom key bindings. It works cross-platform (Linux, macOS, Windows) without the GPL licensing constraints of readline.

### What about performance for large data displays?

Rich handles millions of rows efficiently through its `Live` display and `Progress` column rendering. Textual uses virtual scrolling for large DataTables — it only renders the visible rows. For raw throughput, urwid's canvas model is the most efficient as it paints directly to the terminal buffer.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python Terminal UI Libraries: Textual vs Rich vs prompt_toolkit vs urwid (2026 Comparison)",
  "description": "In-depth comparison of four Python terminal UI libraries — Textual, Rich, prompt_toolkit, and urwid — covering widget systems, styling, interactive input, and deployment for CLI applications.",
  "datePublished": "2026-07-01",
  "dateModified": "2026-07-01",
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

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on anything from election outcomes to tech regulatory timelines. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've made solid returns predicting tech-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)
