---
title: "Linux Open File Inspection: lsof vs fuser vs /proc/PID/fd — Self-Hosted Process File Monitoring"
date: "2026-05-23"
tags: ["linux", "system-administration", "process-monitoring", "file-descriptors", "troubleshooting"]
draft: false
---

When a Linux server runs out of disk space due to deleted-but-still-open files, or when you need to figure out which process is holding a mount point busy during unmount, the ability to inspect which processes have which files open becomes critical. Three approaches dominate this space on Linux: **lsof** (the Swiss Army knife), **fuser** (the quick checker), and direct **/proc/PID/fd** inspection (the kernel-native method). Each serves different operational scenarios — from quick terminal checks to automated monitoring scripts.

## Why Inspect Open Files on Linux?

Linux follows the Unix philosophy that "everything is a file." Every socket, pipe, device node, regular file, and directory opened by a process is tracked by the kernel through file descriptors. Understanding which processes hold which file descriptors open is fundamental to server administration for several reasons:

**Recovering disk space.** When you delete a log file that a running process still has open, the disk space isn't freed until the process closes its file descriptor or terminates. Administrators routinely encounter servers reporting 100% disk usage even after deleting large files — the culprit is always an open file descriptor. Knowing which process holds the deleted file lets you either restart the service or signal it to reopen its log files (SIGHUP).

**Unmounting busy filesystems.** The dreaded "device is busy" error during `umount` happens when some process has an open file, working directory, or memory-mapped file on that filesystem. Identifying the offending process is the first step to safely unmounting — whether by stopping the service, changing its working directory, or killing the process.

**Security auditing.** Suspicious open files can reveal compromised processes — a web server process opening `/etc/shadow`, or an unknown process with network sockets to foreign IPs. Regular file descriptor inspection is a lightweight security monitoring technique that requires no additional agents.

**Troubleshooting application errors.** When an application reports "too many open files" (EMFILE/ENFILE), you need to identify which process is leaking file descriptors and what files it's holding. This is a common production issue with connection-pooled services, log rotation failures, and misconfigured applications.

**Container debugging.** In containerized environments, understanding file descriptor inheritance across container boundaries helps debug volume mount issues, socket sharing problems, and resource leaks in orchestration platforms.

## Understanding File Descriptors in Linux

Every Linux process has a file descriptor table maintained by the kernel. File descriptors 0, 1, and 2 are reserved for stdin, stdout, and stderr. Beyond that, each `open()`, `socket()`, `pipe()`, or `epoll_create()` call allocates a new descriptor. The kernel tracks the file type, permissions, current position (for seekable files), and the underlying inode.

The limits are controlled by two parameters: the per-process soft limit (`ulimit -n`, typically 1024 by default) and the system-wide maximum (`/proc/sys/fs/file-max`). When either limit is reached, new file operations fail with EMFILE (process limit) or ENFILE (system limit).

For self-hosted server administration, the default 1024 file descriptor limit is often insufficient — database servers, web proxies, and message brokers routinely need tens of thousands of open connections. The tools we'll compare help you audit current usage and identify which processes need higher limits.

## lsof — List Open Files

[lsof](https://github.com/lsof-org/lsof) (List Open Files) is the most comprehensive file descriptor inspection tool on Linux. Written by Victor A. Abell and maintained as an open-source project with over 550 GitHub stars, lsof has been the go-to tool for file descriptor inspection since 1995.

### What lsof Can Do

lsof reports on **all** open file types: regular files, directories, block special files, character special files, executing text references, libraries, streams, network files (Internet sockets, NFS files, UNIX domain sockets), and more. Its output columns include:

| Column | Description |
|--------|-------------|
| COMMAND | Process name |
| PID | Process ID |
| TID | Thread ID (if applicable) |
| USER | Process owner |
| FD | File descriptor number and type |
| TYPE | File type (REG, DIR, CHR, BLK, FIFO, IPv4, etc.) |
| DEVICE | Device numbers or network addresses |
| SIZE/OFF | File size or offset |
| NODE | Inode number |
| NAME | File path or network endpoint |

### Common lsof Commands

```bash
# List all open files system-wide
lsof

# Find processes using a specific file
lsof /var/log/syslog

# Find all open files by a user
lsof -u www-data

# Find all network connections (TCP and UDP)
lsof -i

# Find processes listening on a specific port
lsof -i :8080

# Find deleted files still held open
lsof +L1

# Find processes with files open on a specific mount
lsof +D /mnt/data

# List open files for a specific PID
lsof -p 1234

# Find processes using IPv4 connections only
lsof -i4

# Monitor lsof output in repeat mode
lsof -r 5 -i :443
```

### Docker Deployment

lsof can be run in a Docker container for isolated inspection:

```yaml
version: "3.8"
services:
  lsof-inspect:
    image: ubuntu:24.04
    command: ["bash", "-c", "apt-get update && apt-get install -y lsof && lsof -i"]
    network_mode: "host"
    pid: "host"
    volumes:
      - /proc:/proc:ro
      - /etc:/etc:ro
    read_only: true
    tmpfs:
      - /tmp
```

Running lsof in a container requires `--pid=host` to see all processes and `--network=host` to see network file descriptors. The `/proc` mount must be read-only for safety.

### Installation

```bash
# Debian/Ubuntu
sudo apt install lsof

# RHEL/CentOS/Fedora
sudo dnf install lsof

# Alpine (Docker)
apk add lsof

# Build from source
git clone https://github.com/lsof-org/lsof.git
cd lsof
./Configure linux
make
sudo make install
```

### Performance Considerations

lsof scans `/proc` extensively and can be slow on systems with thousands of processes and tens of thousands of open file descriptors. A full `lsof` on a busy server may take 5-30 seconds. Use targeted queries (`-p`, `-u`, `-i`) to minimize overhead. For automated monitoring, consider running lsof during off-peak hours or using the repeat mode (`-r`) at long intervals.

## fuser — Find Processes Using Files

**fuser** (file user) is a lighter-weight alternative included in the **psmisc** package. It answers a single question: "which process is using this file or filesystem?" Unlike lsof's comprehensive output, fuser returns only PIDs — making it ideal for scripts and quick checks.

### Common fuser Commands

```bash
# Find processes using a specific file
fuser /var/log/syslog

# Find processes using a mount point (shows all files on that fs)
fuser -m /mnt/data

# Kill all processes using a mount point
fuser -km /mnt/data

# Show detailed information (user, access type)
fuser -v /var/log/syslog

# Find processes using a TCP port
fuser 8080/tcp

# Find processes using a UDP port
fuser 53/udp

# Send a specific signal instead of SIGKILL
fuser -k -SIGHUP /var/log/app.log
```

### Output Format

fuser's default output is minimal — just PIDs separated by spaces:

```bash
$ fuser /var/log/syslog
/var/log/syslog:  1234

$ fuser -v /var/log/syslog
                     USER        PID ACCESS COMMAND
/var/log/syslog:     root       1234 F.... rsyslogd
```

The ACCESS codes indicate how the file is being used:
- `c` — current directory
- `e` — executable being run
- `f` — open file (default, omitted in display)
- `F` — open file for writing
- `r` — root directory
- `m` — mmap'ed file or shared library

### Docker Deployment

```yaml
version: "3.8"
services:
  fuser-check:
    image: alpine:latest
    command: ["sh", "-c", "apk add psmisc && fuser -v /etc/passwd"]
    pid: "host"
    volumes:
      - /proc:/proc:ro
    read_only: true
```

### When to Use fuser Over lsof

fuser excels in three scenarios where lsof is overkill:

1. **Quick unmount checks** — `fuser -m /mnt/data` instantly tells you if anything is using a mount point, without the overhead of scanning the entire file descriptor table.
2. **Script automation** — fuser's exit code indicates whether processes were found (0 = yes, 1 = no), making it perfect for conditional logic in bash scripts.
3. **Force unmount** — `fuser -km` is the fastest way to kill everything using a filesystem before unmounting, useful in emergency recovery situations.

## /proc/PID/fd — Direct Kernel Inspection

The **/proc filesystem** provides direct access to kernel data structures, including every process's file descriptor table. Each process has a `/proc/PID/fd/` directory containing symbolic links to every open file descriptor:

```bash
$ ls -la /proc/1234/fd/
lrwx------ 1 root root 64 May 23 10:00 0 -> /dev/null
lrwx------ 1 root root 64 May 23 10:00 1 -> /var/log/syslog
lrwx------ 1 root root 64 May 23 10:00 2 -> /var/log/syslog
lr-x------ 1 root root 64 May 23 10:00 3 -> /etc/passwd
lrwx------ 1 root root 64 May 23 10:00 4 -> socket:[45678]
```

### Reading /proc/PID/fd Directly

```bash
# List all file descriptors for PID 1234
ls -la /proc/1234/fd/

# Count open file descriptors for all processes
for pid in /proc/[0-9]*/fd; do
    count=$(ls "$pid" 2>/dev/null | wc -l)
    echo "${pid}: $count fds"
done | sort -t: -k2 -rn | head -10

# Find deleted files (links point to "(deleted)")
find /proc/[0-9]*/fd -lname '*(deleted)*' -ls 2>/dev/null

# Find all socket file descriptors
find /proc/[0-9]*/fd -lname 'socket:*' 2>/dev/null | wc -l

# Check a specific process's FD count
ls /proc/$$/fd/ | wc -l
```

### /proc/PID/fdinfo — Extended Information

Beyond the symlinks in `/proc/PID/fd/`, the `/proc/PID/fdinfo/` directory provides detailed information about each file descriptor:

```bash
$ cat /proc/1234/fdinfo/3
pos:    0
flags:  0100002
mnt_id: 23
ino:    131073
```

This includes the file position (offset), open flags, mount ID, and inode number — information not available through lsof or fuser.

### Network Socket Details via /proc/net

For network file descriptors, `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/udp`, and `/proc/net/udp6` provide raw kernel socket tables:

```bash
# View all TCP sockets (hex format)
cat /proc/net/tcp

# Decode a socket inode to find the owning process
grep "45678" /proc/net/tcp
for pid in /proc/[0-9]*/fd; do
    ls -la "$pid" 2>/dev/null | grep "45678"
done
```

### When to Use /proc Directly

Direct `/proc` inspection is the best approach when:

1. **lsof is not installed** — on minimal Docker containers or embedded systems, `/proc` is always available.
2. **You need programmatic access** — scripts can parse `/proc/PID/fd` without depending on external tools or parsing lsof's formatted output.
3. **You need fdinfo details** — file positions, flags, and mount IDs are only available through `/proc/PID/fdinfo/`.
4. **Performance matters** — reading `/proc` directly is faster than running lsof, which parses the same `/proc` data but adds formatting overhead.

## Comparison: lsof vs fuser vs /proc/PID/fd

| Feature | lsof | fuser | /proc/PID/fd |
|---------|------|-------|-------------|
| **File types** | All types | Files, sockets, mounts | All types |
| **Network info** | Full (IP, port, state) | Port numbers only | Via /proc/net/* |
| **Deleted files** | Yes (`+L1`) | No | Yes (`(deleted)` symlink) |
| **Output format** | Detailed table | PIDs or brief table | Symlink listing |
| **Script-friendly** | Parse required | Exit codes available | Direct file access |
| **Installation** | Separate package | psmisc (usually pre-installed) | Always available |
| **Performance** | Slow (full scan) | Fast (targeted) | Fastest (direct) |
| **File positions** | No | No | Yes (fdinfo) |
| **Kill processes** | No | Yes (`-k`) | No |
| **Container support** | Requires host PID | Requires host PID | Always in host |

## Choosing the Right Tool

**Use lsof** when you need comprehensive information about what files are open, who owns them, and what network connections exist. It's the best tool for deep troubleshooting and security auditing. The detailed output format makes it ideal for interactive investigation.

**Use fuser** when you need a quick answer to "what's using this file?" or need to kill processes holding a filesystem. Its simplicity and exit code behavior make it perfect for automation scripts and emergency recovery procedures.

**Use /proc/PID/fd** when you're working in minimal environments without lsof installed, need programmatic access for custom monitoring tools, or require file descriptor metadata (positions, flags) that neither lsof nor fuser provides.

For a robust self-hosted server administration toolkit, install all three: lsof for deep investigation, fuser for quick checks and scripts, and rely on `/proc` for environments where packages cannot be installed.

## Why Self-Host Your File Monitoring?

Understanding open file descriptors on your own Linux servers gives you complete visibility into resource consumption without depending on commercial monitoring platforms. Self-hosted file descriptor inspection:

**Catches resource leaks early.** File descriptor leaks are a common cause of service crashes. By regularly auditing open file counts across processes, you can identify leaking services before they hit system limits and cause cascading failures. For related guidance, see our [Linux service restart detection tools](../2026-05-29-self-hosted-linux-service-restart-detection-needrestart-checkrestart-debsums-guide/) for automating service recovery.

**Enables zero-cost troubleshooting.** Commercial APM platforms charge per host for file descriptor monitoring. The native Linux tools described here provide the same information at zero cost — no agents, no subscriptions, no vendor lock-in. If you're interested in broader system profiling approaches, our [Linux performance profiling comparison](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) covers complementary tools.

**Improves security posture.** Unauthorized file access is a common indicator of compromise. Regular file descriptor audits can reveal processes reading sensitive files they shouldn't access, or network connections to unexpected destinations. For kernel-level security hardening, check our [Linux kernel security auditing guide](../2026-05-23-self-hosted-linux-kernel-security-auditing-kconfig-hardened-check-checksec-guide/).

**Supports capacity planning.** Tracking file descriptor usage trends over time helps predict when you'll need to increase system-wide limits or add server capacity. This data feeds directly into capacity planning decisions without requiring external monitoring infrastructure.

## FAQ

### What does "too many open files" mean in Linux?

This error (EMFILE or ENFILE) occurs when a process or the system has reached its maximum number of simultaneously open file descriptors. The per-process default limit is typically 1024 (`ulimit -n`), and the system-wide limit is defined in `/proc/sys/fs/file-max`. Use `lsof -p <PID> | wc -l` to count a process's open files, then increase limits in `/etc/security/limits.conf` if needed.

### How do I find which process is holding a deleted file open?

Run `lsof +L1` to list all files with link count less than 1 (i.e., deleted but still open). The output shows the process name, PID, and file path. To recover disk space, either restart the process or send it SIGHUP to reopen its log files: `kill -HUP <PID>`.

### Can fuser find processes using a network port?

Yes. Use `fuser <port>/tcp` or `fuser <port>/udp` to find processes listening on or connected to a specific port. For example, `fuser 80/tcp` shows all processes using TCP port 80. This is equivalent to `lsof -i :80` but with simpler output.

### Is /proc/PID/fd safe to read for all processes?

Reading `/proc/PID/fd/` symlinks is safe — it doesn't modify the process or kernel state. However, you need appropriate permissions (typically root) to read other users' file descriptors. On systems with hidepid mount option for `/proc`, you may only see your own process's file descriptors.

### How do I increase the file descriptor limit for a systemd service?

Add `LimitNOFILE=65536` (or your desired limit) to the service's `[Service]` section in its systemd unit file, then run `systemctl daemon-reload` and `systemctl restart <service>`. You can verify the new limit with `cat /proc/<PID>/limits | grep "Max open files"`.

### What's the difference between lsof's -i and -i4/-i6 flags?

`-i` shows all network file descriptors (both IPv4 and IPv6). `-i4` filters to IPv4 only, and `-i6` filters to IPv6 only. You can also specify protocols (`-i tcp`, `-i udp`), ports (`-i :80`), or addresses (`-i @192.168.1.1`) for more targeted queries.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linux Open File Inspection: lsof vs fuser vs /proc/PID/fd — Self-Hosted Process File Monitoring",
  "description": "Compare three approaches to inspecting open file descriptors on Linux servers — lsof for comprehensive analysis, fuser for quick checks, and /proc/PID/fd for direct kernel access.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
