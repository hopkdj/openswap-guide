---
title: "Self-Hosted Disk Usage Analysis: dust vs ncdu vs dua Guide 2026"
date: "2026-05-08"
tags: ["server-admin", "disk-usage", "storage", "dust", "ncdu", "dua", "monitoring"]
draft: false
---

Disk space management is one of the most fundamental tasks in server administration. When a filesystem fills up, services stop working, databases refuse to write, and applications crash. Finding what is consuming disk space quickly is essential — especially on production servers with terabytes of storage and millions of files. This guide compares three excellent open-source disk usage analyzers: **dust**, **ncdu**, and **dua**.

## What Are Disk Usage Analyzers?

Disk usage analyzers scan a filesystem directory tree and present a visual representation of space consumption. Instead of manually running `du -sh *` on each directory, these tools recursively measure file and directory sizes, sort results by size, and provide interactive navigation to drill down into the largest consumers. They are essential for identifying log bloat, orphaned temporary files, and runaway data growth.

## ncdu: The Classic Terminal Disk Usage Analyzer

**ncdu** (NCurses Disk Usage) is a terminal-based disk usage analyzer built on the ncurses library. It has been the go-to tool for system administrators for over a decade, offering an intuitive interactive interface for exploring filesystem usage.

### Key Features

- Interactive ncurses interface
- Directory navigation with arrow keys
- File deletion directly from the interface
- Export results to flat file for offline analysis
- Incremental display (shows results as scanning progresses)
- Low memory footprint
- Supports hard link counting

### Installation

```bash
# Debian/Ubuntu
sudo apt install ncdu

# RHEL/CentOS
sudo yum install ncdu

# Build from source
git clone https://github.com/rofl0r/ncdu.git
cd ncdu
./autogen.sh
./configure
make
sudo make install
```

### Basic Usage

```bash
# Scan current directory
ncdu

# Scan specific directory
ncdu /var/log

# Export results for later analysis
ncdu -o /tmp/scan-results.json /var

# Read previously exported results
ncdu -f /tmp/scan-results.json

# Quiet mode (no progress display)
ncdu -q /home

# Follow symlinks
ncdu -L /data
```

### Docker Usage

```bash
# Run ncdu in a Docker container
docker run --rm -v /:/host:ro -it ubuntu:22.04 bash -c "
  apt-get update && apt-get install -y ncdu &&
  ncdu /host
"
```

## dust: A Modern Rust-Based Disk Usage Tool

**dust** (du + rust) is a more intuitive way to use disk space. Written in Rust, it displays a visual tree of directory sizes with percentage bars, making it immediately obvious which directories consume the most space. Unlike ncdu, it is not interactive — it produces a single output that summarizes the entire directory tree at a glance.

### Key Features

- Visual percentage bar display
- Tree-style output showing directory hierarchy
- Written in Rust (fast and safe)
- Configurable depth limit
- Color-coded output for easy visual scanning
- Reverse sorting options
- File count display
- Cross-platform (Linux, macOS, Windows)

### Installation

```bash
# Using cargo (Rust package manager)
cargo install du-dust

# Debian/Ubuntu (from GitHub releases)
curl -sL https://github.com/bootandy/dust/releases/latest/download/dust-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv dust /usr/local/bin/

# Homebrew (macOS/Linux)
brew install dust
```

### Basic Usage

```bash
# Scan current directory
dust

# Limit depth to 2 levels
dust -d 2 /var

# Show file count instead of size
dust -c /home

# Reverse sort (smallest first)
dust -r /tmp

# No percentage bars (plain output)
dust -p /var/log

# Output only top 10 entries
dust -n 10 /
```

### Docker Compose

```yaml
version: "3.8"
services:
  disk-analyzer:
    image: alpine:latest
    container_name: disk-usage-check
    volumes:
      - /:/host:ro
      - ./scripts:/scripts
    command: >
      sh -c "
        apk add --no-cache curl &&
        curl -sL https://github.com/bootandy/dust/releases/latest/download/dust-x86_64-unknown-linux-musl.tar.gz | tar xz &&
        ./dust -d 3 -n 20 /host
      "
    restart: "no"
```

## dua: Fast Disk Usage Analyzer with Parallel Traversal

**dua** (Disk Usage Analyzer) is a Rust-based tool optimized for speed. It uses parallel filesystem traversal to analyze directories significantly faster than traditional tools. It offers both an interactive terminal UI (similar to ncdu) and a non-interactive mode for scripting.

### Key Features

- Parallel filesystem traversal for maximum speed
- Interactive terminal interface
- Non-interactive mode for scripting
- Written in Rust (memory safe, no buffer overflows)
- Cross-platform support
- Directory deletion from the interactive UI
- Byte-accurate size reporting
- Configurable number of threads

### Installation

```bash
# Using cargo
cargo install dua-cli

# Debian/Ubuntu (from GitHub releases)
curl -sL https://github.com/Byron/dua-cli/releases/latest/download/dua-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv dua /usr/local/bin/

# Homebrew (macOS/Linux)
brew install dua
```

### Basic Usage

```bash
# Interactive mode (default)
dua

# Interactive mode on specific directory
dua interactive /var/log

# Non-interactive (print results)
dua /var/log

# Non-interactive with apparent size (not disk usage)
dua -a /home

# Limit traversal depth
dua -d 3 /data

# Show entry count
dua -e /tmp

# Delete files/directories (interactive mode: press 'd')
dua interactive /var/log
```

### Docker Deployment

```yaml
version: "3.8"
services:
  dua-scanner:
    image: alpine:latest
    container_name: dua-disk-scan
    volumes:
      - /:/host:ro
    command: >
      sh -c "
        apk add --no-cache curl &&
        curl -sL https://github.com/Byron/dua-cli/releases/latest/download/dua-x86_64-unknown-linux-musl.tar.gz | tar xz &&
        ./dua -d 4 /host 2>/dev/null | head -50
      "
    restart: "no"
```

## Comparison Table

| Feature | ncdu | dust | dua |
|---------|------|------|-----|
| **Interface** | Interactive (ncurses) | Non-interactive (stdout) | Both modes |
| **Language** | C | Rust | Rust |
| **Parallel Traversal** | No | No | Yes |
| **File Deletion** | Yes (interactive) | No | Yes (interactive) |
| **Export Results** | Yes (JSON) | No | No |
| **Visual Bars** | No | Yes | No |
| **Color Output** | Yes | Yes | Yes |
| **Follow Symlinks** | Yes (`-L`) | No | Yes |
| **Cross-Platform** | Linux, macOS, BSD | Linux, macOS, Windows | Linux, macOS, Windows |
| **Scriptable** | Partial (`-o` export) | Yes (stdout) | Yes (non-interactive mode) |
| **Last Active** | 2025 | 2025 | 2025 |
| **GitHub Stars** | 1,400+ (rofl0r/ncdu) | 11,000+ (bootandy/dust) | 7,500+ (Byron/dua-cli) |
| **License** | MIT | MIT | MIT/Apache-2.0 |
| **Package Manager** | apt, yum, brew | cargo, brew | cargo, brew |

## Why Self-Host Disk Usage Analysis Tools

Server administrators managing their own infrastructure need immediate access to disk space analysis capabilities. When a filesystem reaches 95% capacity, the time between discovery and resolution directly impacts service availability. Having disk usage analysis tools pre-installed on every server means you can start investigating immediately, without waiting for package downloads or dealing with network restrictions during an outage.

Self-hosted analysis tools also protect sensitive filesystem metadata. Cloud-based disk analysis services require uploading your directory structure — information that reveals your application architecture, data volumes, and usage patterns. For organizations handling regulated data (healthcare, finance, government), this metadata must not leave the premises. Running dust, ncdu, or dua locally keeps all filesystem information on your own infrastructure.

Furthermore, self-hosted tools can be integrated into automated monitoring and alerting workflows. You can schedule disk scans during off-peak hours, compare results against baseline measurements, and trigger alerts when directory growth exceeds expected thresholds. For example, a weekly ncdu export of `/var/log` compared against the previous week's data immediately reveals log rotation failures or unexpectedly verbose application logging.

For organizations managing log aggregation infrastructure, understanding disk consumption patterns across log storage is critical. Our [log aggregation comparison](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) covers how to centralize logs, and disk usage tools help you monitor the storage footprint of your log infrastructure to prevent capacity issues before they cause log loss.

When planning backup strategies, knowing exactly where disk space is consumed informs retention policies and storage provisioning decisions. Our [backup verification guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guid/) covers ensuring backup integrity, and disk usage analysis helps you identify which directories warrant backup coverage based on their size and growth rate.

For email server administrators, monitoring mailbox storage and queue directories prevents delivery failures. Our [email archiving guide](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/) covers email storage management, and disk usage tools help you track the growth of mailbox databases and archive stores over time.

## Choosing the Right Disk Usage Tool

- **Use ncdu** when you need a reliable, battle-tested interactive tool for exploring filesystem usage. Its incremental display shows results as scanning progresses, and its export feature lets you save analysis results for later review. It is the safest choice for production servers due to its low resource usage and decades of stability.
- **Use dust** when you need a quick visual overview of disk usage without interactive navigation. Its percentage bars and tree display make it immediately obvious which directories are the largest consumers. It is ideal for one-off checks and for including in automated reports where you need human-readable output.
- **Use dua** when speed matters — especially on filesystems with millions of files. Its parallel traversal can be 2-4x faster than ncdu on large directory trees. The interactive mode provides a modern ncurses interface, while the non-interactive mode works well in scripts and CI pipelines.

## FAQ

### How fast are these tools compared to the standard du command?

For small directories (fewer than 10,000 files), all three tools are comparable to `du -sh`. For large directories (millions of files), dua's parallel traversal provides the most significant speedup — typically 2-4x faster than ncdu and `du`. dust is comparable to ncdu in speed since both use single-threaded traversal. The exact performance depends on filesystem type, disk speed (SSD vs HDD), and directory depth.

### Can I run these tools remotely over SSH?

Yes. All three tools work over SSH. For ncdu and dua's interactive mode: `ssh user@server 'ncdu /var'` or `ssh -t user@server 'dua /var'`. For dust's non-interactive output: `ssh user@server 'dust -d 2 /var'`. If the remote server does not have the tool installed, you can use Docker: `ssh user@server 'docker run --rm -v /:/host:ro -it ubuntu ncdu /host'`.

### How do I schedule automated disk usage reports?

Use ncdu's export feature combined with cron. Example: schedule `ncdu -o /var/reports/weekly-$(date +\%Y\%m\%d).json /var` every Sunday, then use a script to compare consecutive reports and alert on directories that grew by more than a threshold. For dust, capture stdout: `dust -d 3 -n 20 /var > /var/reports/dust-$(date +\%Y\%m\%d).txt`.

### Do these tools work on network filesystems (NFS, CIFS)?

Yes, but with caveats. On NFS, traversal speed is limited by network latency — each `stat()` call requires a round trip to the server. dua's parallel approach may help on high-latency NFS mounts. On CIFS/SMB, some metadata operations may be slower. For large network filesystems, consider running the tool on the server side rather than mounting remotely.

### Can these tools show file age or modification dates?

No. dust, ncdu, and dua focus on size analysis, not temporal metadata. To find old files consuming space, combine these tools with `find`: `find /var/log -type f -mtime +90 -exec ls -lh {} \; | sort -k5 -h`. Some administrators use ncdu to identify the largest directories, then use `find` within those directories to locate old files for cleanup.

### What happens if I delete files through ncdu or dua?

Both ncdu (press `d`) and dua (press `d` in interactive mode) delete the selected file or directory. This is permanent — deleted files are not sent to a trash bin. On production servers, use caution: deleting active log files or database files can cause service failures. It is safer to identify files using the tool, then delete them manually using `rm` after verifying they are safe to remove.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Disk Usage Analysis: dust vs ncdu vs dua Guide 2026",
  "description": "Compare dust, ncdu, and dua for self-hosted disk usage analysis. Includes Docker Compose configs, installation guides, and usage examples for server storage management.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
