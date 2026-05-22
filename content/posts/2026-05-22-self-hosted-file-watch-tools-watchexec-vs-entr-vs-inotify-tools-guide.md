---
title: "Self-Hosted File Watch Tools: watchexec vs entr vs inotify-tools Guide"
date: "2026-05-22"
tags: ["file-monitoring", "automation", "development-tools", "linux", "inotify"]
draft: false
---

When you need to automatically trigger actions in response to file system changes — reloading a web server, rebuilding a project, syncing directories, or running tests — a reliable file watch tool becomes essential. Linux provides several approaches to file system event monitoring, each with different tradeoffs in portability, performance, and ease of use. This guide compares three of the most popular open-source file watch utilities: **watchexec**, **entr**, and **inotify-tools**, helping you choose the right tool for your workflow.

## Understanding File System Event Monitoring

Linux offers multiple mechanisms for detecting file changes at the kernel level. The primary interface is **inotify** (inode notify), introduced in kernel 2.6.13, which provides a file descriptor-based API for monitoring file system events such as modifications, attribute changes, creation, deletion, and directory movements. Tools built on inotify receive events directly from the kernel, making them efficient and low-latency.

**fanotify** (file access notification), added in kernel 2.6.36, is a newer alternative that operates at the mount level rather than per-inode, making it suitable for broader monitoring scopes. However, most file watch tools use inotify due to its simpler API and wider adoption.

All three tools covered in this guide use inotify as their underlying mechanism, but they differ significantly in how they expose events, handle recursive watching, and integrate into development and production workflows.

## Comparison Table

| Feature | watchexec | entr | inotify-tools |
|---------|-----------|------|---------------|
| GitHub Stars | 6,990+ | 5,577+ | 3,397+ |
| Language | Rust | C | C |
| Recursive Watch | Yes (native) | Yes (via `-d`) | No (manual) |
| Custom Events Filter | Yes | Limited | Full control |
| Debounce Support | Built-in | No | Manual |
| Cross-Platform | Linux, macOS, Windows | Linux, macOS, BSD | Linux only |
| Package Manager | cargo, apt, brew | apt, brew, pkg | apt, yum, pacman |
| Docker Support | Official image available | Easy to install | Pre-installed in most distros |
| Use Case | Dev workflow, automation | Quick CLI tasks | Low-level scripting |
| License | Apache 2.0 | ISC | GPL-2.0 |

## watchexec: Modern, Feature-Rich File Watcher

[watchexec](https://github.com/watchexec/watchexec) is a Rust-based file watcher that has become the go-to tool for development workflows. It provides a clean command-line interface with powerful filtering capabilities, debounce support, and native recursive directory watching.

### Key Features

- **Debouncing**: Built-in event debouncing prevents rapid-fire executions when multiple files change simultaneously (common during git checkouts or IDE saves)
- **Path filtering**: Include/exclude patterns using glob syntax (`--ignore`, `--watch`)
- **Signal handling**: Can send signals (HUP, INT, TERM) to child processes for graceful restarts
- **Event types**: Filter by specific event types (write, create, remove, rename, metadata)
- **Cross-platform**: Works identically on Linux, macOS, and Windows
- **No shell required**: Runs commands directly without shell interpretation

### Installation

```bash
# Ubuntu/Debian
sudo apt install watchexec

# Arch Linux
sudo pacman -S watchexec

# From source (Rust)
cargo install watchexec

# Docker
docker run --rm -v $(pwd):/workspace ghcr.io/watchexec/watchexec:latest watchexec --version
```

### Docker Compose Deployment

For self-hosted automation pipelines, you can run watchexec as a sidecar container:

```yaml
version: "3.8"
services:
  file-watcher:
    image: ghcr.io/watchexec/watchexec:latest
    volumes:
      - ./source:/workspace
      - ./output:/output
    working_dir: /workspace
    command: >
      watchexec
      --watch /workspace
      --exts rs,toml
      --restart
      --debounce 500ms
      "cargo build --release && cp target/release/app /output/"
    restart: unless-stopped
```

### Usage Examples

```bash
# Watch all Rust files and rebuild
watchexec --exts rs,toml "cargo build"

# Watch a specific directory with debounce
watchexec --watch src/ --debounce 1s "make test"

# Restart a web server on file changes
watchexec --restart --exts py "python3 app.py"

# Filter events and ignore build artifacts
watchexec --ignore "target/*" --ignore ".git/*" "cargo test"

# Send SIGTERM before restart
watchexec --signal TERM --exts go "go run main.go"
```

## entr: Event-Driven Command Runner

[entr](https://github.com/eradman/entr) takes a minimalist approach. It reads file paths from standard input and runs a command whenever any of those files change. Its design philosophy is "do one thing well" — it doesn't filter events, debounce, or handle recursive directories natively.

### Key Features

- **Minimal interface**: Reads file list from stdin, simple to pipe into
- **Directory mode**: `-d` flag watches directories for new/removed files
- **Non-interactive**: `-n` flag prevents entr from taking over the terminal
- **Clear screen**: `-c` clears the terminal before each execution
- **Portable**: Runs on Linux, macOS, and BSD systems
- **Tiny footprint**: Single C binary, no dependencies

### Installation

```bash
# Ubuntu/Debian
sudo apt install entr

# Arch Linux
sudo pacman -S entr

# macOS
brew install entr

# From source
git clone https://github.com/eradman/entr.git
cd entr && make && sudo make install
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  entr-watcher:
    image: alpine:latest
    volumes:
      - ./src:/src
    working_dir: /src
    entrypoint: ["sh", "-c"]
    command: >
      "apk add entr make gcc &&
       find /src -type f | entr -d make rebuild"
    restart: unless-stopped
```

### Usage Examples

```bash
# Watch all files in current directory tree
find . -type f | entr make

# Watch specific file types
ls *.py *.cfg | entr -c python3 app.py

# Directory mode (detects new/deleted files)
echo /src/ | entr -d make rebuild

# Run once on startup, then watch
ls *.rs | entr -r "cargo run"

# Non-interactive mode (for scripts/cron)
ls config/* | entr -n systemctl reload myservice
```

## inotify-tools: Low-Level Kernel Interface

[inotify-tools](https://github.com/inotify-tools/inotify-tools) provides the most granular control over file system events. It consists of two command-line utilities: `inotifywait` (blocks until an event occurs) and `inotifywatch` (collects event statistics).

### Key Features

- **Granular control**: Monitor specific event types (modify, create, delete, move, attrib)
- **Recursive support**: `-r` flag for recursive directory monitoring
- **Format output**: Custom output format with `-e` and `--format`
- **Event statistics**: `inotifywatch` counts events by type for analysis
- **Loop mode**: `-m` (monitor) mode for continuous watching
- **Timeout support**: `-t` flag for timed watches

### Installation

```bash
# Ubuntu/Debian (usually pre-installed)
sudo apt install inotify-tools

# Arch Linux
sudo pacman -S inotify-tools

# RHEL/CentOS
sudo yum install inotify-tools
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  inotify-monitor:
    image: alpine:latest
    volumes:
      - ./data:/data
    entrypoint: ["sh", "-c"]
    command: >
      "apk add inotify-tools rsync &&
       inotifywait -m -r -e modify,create,delete --format '%w%f %e' /data |
       while read FILE EVENT; do
         echo "[$(date)] $EVENT: $FILE" >> /data/watch.log
         rsync -a /data/ /backup/
       done"
    restart: unless-stopped
```

### Usage Examples

```bash
# Watch for any modification in a directory
inotifywait -m /var/www/html -e modify,create,delete

# Recursive watch with formatted output
inotifywait -m -r --format '%w%f %e' /src/ -e modify

# Watch specific file types
inotifywait -m /src/ -e modify -e create --include '.*\.py$'

# Event statistics collection
inotifywatch -t 60 /var/log/

# Integration with shell scripts
inotifywait -m -r -e close_write /src/ |
  while read path action file; do
    echo "File $path$file was $action"
    # Trigger deployment
  done
```

## Choosing the Right Tool

### Use watchexec When:
- You need **debouncing** to prevent redundant executions
- Your project uses **multiple file types** and you need include/exclude filtering
- You're building a **cross-platform** development workflow
- You need **graceful process restart** with signal handling
- You want a **modern, maintained** tool with active development

### Use entr When:
- You prefer **simplicity** over features
- You want to **pipe** a file list from `find`, `ls`, or `git`
- You need **portability** across Unix-like systems
- Your workflow is **simple**: watch files, run command, repeat
- You want the **smallest possible** dependency footprint

### Use inotify-tools When:
- You need **granular event filtering** (specific event types)
- You're writing **shell scripts** that need to react to specific changes
- You want **event statistics** (`inotifywatch`) for monitoring
- You need **timeout-based** monitoring
- Your use case requires **low-level control** over the watch behavior

## Why Self-Host File Watch Tools?

Self-hosted file monitoring is critical for development pipelines, CI/CD triggers, and automated build systems. When you control the file watch infrastructure, you gain several advantages:

**Data sovereignty and security**: File change events may reveal sensitive information about your codebase, deployment schedules, or system architecture. Running file watch tools on your own infrastructure means no third-party service has visibility into your development activity patterns.

**Network independence**: Cloud-based file watchers require network connectivity to trigger actions. Self-hosted tools work regardless of internet availability, making them essential for air-gapped environments, edge deployments, and offline development workflows.

**Performance and latency**: Local file watchers detect changes in milliseconds, without the round-trip delay of polling a cloud API. For real-time development workflows — hot reloading, live preview, continuous testing — this latency difference is measurable and significant.

**Cost predictability**: Many SaaS file monitoring services charge per-event or per-minute of watch time. Self-hosted tools have zero marginal cost regardless of how many files you monitor or how frequently they change.

**Custom integration**: Self-hosted file watchers integrate seamlessly with your existing infrastructure — triggering Docker builds, updating load balancer configurations, syncing to distributed storage, or notifying internal chat systems. For related reading, see our [log forwarding guide](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/) and [process management comparison](../2026-04-25-supervisord-vs-s6-overlay-vs-runit-self-hosted-process-management/). If you need container build automation, our [container image build tools comparison](../buildah-vs-kaniko-vs-earthly-self-hosted-container-build-tools/) covers pipeline integration options.

## FAQ

### Which file watch tool is fastest for large directories?

**inotify-tools** is typically the fastest for monitoring large directory trees because it registers watches directly with the kernel without intermediate processing layers. However, it requires manually setting up recursive watches. **watchexec** offers a good balance of speed and convenience with native recursive watching and efficient event batching.

### Can these tools watch network-mounted filesystems?

**inotify-tools** and **entr** rely on the inotify kernel interface, which is not supported on NFS, CIFS, or FUSE mounts. **watchexec** can fall back to polling mode (`--poll`) for network filesystems, though this is less efficient than event-based monitoring.

### How do I prevent duplicate events from triggering multiple executions?

**watchexec** has built-in debouncing with the `--debounce` flag (e.g., `--debounce 500ms`). For **entr**, you can wrap the command in a lock file mechanism. With **inotify-tools**, use a shell variable or lock file to track the last execution time and skip events within a cooldown window.

### Can I watch for changes in Docker volumes?

Yes. When mounting host directories as Docker volumes, the inotify events are propagated to containers on Linux. All three tools work inside containers monitoring mounted volumes. Note that on Docker Desktop (macOS/Windows), file events use a different mechanism and may have delays.

### Which tool is best for production deployments?

For production, **watchexec** is the most robust choice due to its signal handling, debouncing, and error recovery. **inotify-tools** is suitable for custom monitoring scripts where you need fine-grained control over event handling. **entr** is best suited for development and testing rather than production workloads.

### How many files can inotify watch simultaneously?

Linux limits the number of inotify watches per user (default: 8192, configurable via `/proc/sys/fs/inotify/max_user_watches`). For large projects with thousands of files, increase this limit: `echo 524288 | sudo tee /proc/sys/fs/inotify/max_user_watches`. All three tools are affected by this kernel limit.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted File Watch Tools: watchexec vs entr vs inotify-tools Guide",
  "description": "Comprehensive comparison of watchexec, entr, and inotify-tools for file system event monitoring. Learn which file watch tool fits your development and automation workflow.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
