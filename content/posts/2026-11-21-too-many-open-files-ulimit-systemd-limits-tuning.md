---
title: "Too Many Open Files in 2026: ulimit, systemd Limits and Kernel Tuning Explained"
date: "2026-11-21"
tags: ["linux", "systemd", "performance", "troubleshooting", "ulimit", "containers"]
draft: false
description: "A complete 2026 walkthrough of Linux file descriptor limits: the six independent layers that can each return EMFILE, how to measure them, and the exact systemd, PAM and kernel settings that fix it without a reboot."
---

The error arrives at the worst possible moment: `accept() failed (24: Too many open files)` in nginx, `OSError: [Errno 24] Too many open files` in a Python worker, or a Postgres backend that dies with `could not open file`. You raise `ulimit -n` in your shell, restart the service… and nothing changes. That is because **`ulimit` was never the setting that mattered**.

On a modern Linux host there are at least six independent layers capping file descriptors, and the effective limit is the *minimum* of all of them. Getting the number right requires knowing which layer your process actually inherits from. This guide maps every layer, shows how to measure the real value inside a running process, and gives copy-paste fixes for systemd services, containers, and kernel-wide settings.

## TL;DR: the 60-second answer

- **A systemd service hitting EMFILE** → set `LimitNOFILE=` in the unit, then `systemctl daemon-reload && systemctl restart <svc>`. Editing `/etc/security/limits.conf` will do nothing, because systemd does not read it.
- **Everything on the host hitting EMFILE at once** → check `cat /proc/sys/fs/file-nr`. If the first column is near the third, raise `fs.file-max` **and** `fs.nr_open`.
- **A container hitting EMFILE** → the limit comes from the runtime (`--ulimit nofile=`), or from the daemon default. Kubernetes pods inherit no meaningful default; set it explicitly in the pod spec.
- **A shell or SSH session hitting EMFILE** → `pam_limits` via `/etc/security/limits.conf` is the right layer, but it only applies to new login sessions, not to services.
- **Never debug this with `ulimit -n` alone.** Read `/proc/<pid>/limits` instead — it shows what the process is actually using.

## The six layers that cap file descriptors

| Layer | Where it is configured | Applies to | Default on a typical 2026 distro | Survives restart? |
|---|---|---|---|---|
| Shell soft/hard limit | `ulimit -Sn` / `ulimit -Hn` | Current shell and children | 1024 soft / 1048576 hard | No |
| PAM limits | `/etc/security/limits.conf`, `/etc/security/limits.d/*.conf` | Login sessions (sshd, login, su, cron with pam_limits) | 1024 or unset | Yes |
| systemd service | `LimitNOFILE=` in unit, or `DefaultLimitNOFILE=` in `/etc/systemd/system.conf` | Units started by PID 1 | 1024:524288 (distro-dependent) | Yes |
| Container runtime | `docker run --ulimit nofile=`, containerd/CRI config, `LimitNOFILE` for systemd-run scopes | Container processes | Inherits daemon or 1024 | Yes |
| Kernel per-process ceiling | `fs.nr_open` | Any process raising its own hard limit | 1048576 | Yes (sysctl) |
| Kernel system-wide | `fs.file-max` | All open file handles on the host | ~9.2 × 10¹⁸ (effectively unlimited) | Yes (sysctl) |

The trap is layer 3 versus layer 2. `systemd/systemd` — **17,054 stars, last pushed 2026-11-20** — deliberately ignores `/etc/security/limits.conf` for services because the file is a PAM module configuration, and services do not go through a PAM login session. Anyone who has spent an afternoon editing `limits.conf` and restarting nginx has met this exact wall.

## Decision matrix: where to set the limit

| Symptom | Correct layer | Command |
|---|---|---|
| One systemd service dies under load | Unit file `LimitNOFILE` | `systemctl edit nginx` → `[Service] LimitNOFILE=65535` |
| Every service on the host needs more | systemd manager default | `DefaultLimitNOFILE=65535` in `/etc/systemd/system.conf` |
| Interactive shells / SSH sessions | PAM limits | `/etc/security/limits.d/99-nofile.conf` |
| Docker container | Runtime flag | `--ulimit nofile=65535:65535` |
| Kubernetes pod | Pod spec | `securityContext` + node kubelet defaults |
| Host-wide exhaustion (`file-nr` near max) | Kernel sysctl | `fs.file-max`, `fs.nr_open` |
| File-watch exhaustion (`ENOSPC`) | inotify sysctls | `fs.inotify.max_user_watches` |
| Socket leak that grows forever | Application fix, not limits | Find the unclosed fd with `lsof` |

## How the kernel actually counts open files

Three numbers describe kernel-wide usage, and confusing them is the second most common mistake:

```bash
cat /proc/sys/fs/file-nr
# 2752    0    9223372036854775807
#  ^      ^    ^
#  |      |    +-- fs.file-max: system-wide ceiling
#  |      +------- allocated but unused file handles (always 0 since Linux 2.6)
#  +-------------- currently allocated file handles
```

If the third column is a giant number, `fs.file-max` is not your problem — it is effectively unlimited on any modern kernel. The real ceiling in that case is either `fs.nr_open` (per-process hard limit) or the process's own soft limit.

```bash
# Per-process reality: THE command to use instead of ulimit
cat /proc/$(pgrep -n nginx)/limits | grep -i "open files"

# Alternative, friendlier formatting
prlimit --pid $(pgrep -n nginx) --nofile

# Total sockets and their states on the host
ss -s
```

`prlimit` comes from `util-linux` (**3,254 stars, pushed 2026-11-19**) and can also *change* the limit of a running process, which is the only way to fix a live process without a restart:

```bash
# Raise the soft limit of a running PID up to its hard limit
prlimit --pid 4242 --nofile=65535:65535

# Verify
prlimit --pid 4242 --nofile
```

This is a genuinely underused capability. If a service has `LimitNOFILE=65535` hard but a soft limit of 1024 because it inherited a bad default, `prlimit` fixes it in place — no restart, no dropped connections.

## Measuring which process is eating the descriptors

Raising the limit without understanding the growth curve is how you turn a crash into a slow leak that takes down the host at 3 a.m. Measure first.

```bash
# Top 10 processes by open descriptor count
for p in /proc/[0-9]*; do
  printf "%6s %6s %s\n" "$(ls "$p/fd" 2>/dev/null | wc -l)" "${p#/proc/}" \
    "$(cat "$p/comm" 2>/dev/null)"
done | sort -rn | head -10

# What exactly does the worst offender hold? (REG, DIR, FIFO, sock, IPv4...)
lsof -p 4242 2>/dev/null | awk 'NR>1 {print $5}' | sort | uniq -c | sort -rn | head

# Drill into sockets only, with peer addresses
lsof -p 4242 -a -i 2>/dev/null | head -20
```

`lsof-org/lsof` sits at **578 stars with commits on 2026-11-17** — still the most precise tool for answering "what is this process holding". For leaks that only appear under load, sample the count over time and look at the slope:

```bash
# One line per 10 seconds: does the fd count climb monotonically?
while sleep 10; do
  printf "%s %s\n" "$(date +%H:%M:%S)" "$(ls /proc/4242/fd 2>/dev/null | wc -l)"
done
```

A count that plateaus is normal connection churn. A count that rises linearly with requests — never dropping — is an application leak, and no `LimitNOFILE` value will fix it. In nginx that is almost always a missing `proxy_http_version 1.1` / keepalive configuration or an upstream that never returns a response. In Python it is an unclosed `requests.Session` or a file opened outside a `with` block.

## The systemd fix, done properly

```bash
# Per-service (recommended): creates a drop-in, survives package upgrades
systemctl edit nginx
```

```ini
[Service]
LimitNOFILE=65535
LimitMEMLOCK=infinity
```

```bash
systemctl daemon-reload
systemctl restart nginx
systemctl show nginx -p LimitNOFILE
# LimitNOFILE=65535
```

Two details that catch people out. First, `LimitNOFILE=65535` sets **both** soft and hard to the same value; `LimitNOFILE=1024:65535` sets soft 1024 and hard 65535, which is usually not what you want for a busy daemon. Second, systemd's manager-level default is often **1024:524288**, so a service that never declares anything gets a soft limit of 1024 while its hard limit is already 524288 — the exact situation where `prlimit` saves you a restart.

For hosts running many high-connection services, set the manager default once:

```ini
# /etc/systemd/system.conf
[Manager]
DefaultLimitNOFILE=65535:524288
```

```bash
systemctl daemon-reexec   # applies manager defaults without a reboot
```

`daemon-reexec` is the correct command here — `daemon-reload` re-reads unit files but does not re-apply manager settings to PID 1's own limits.

## PAM limits: correct for logins, wrong for services

```bash
# /etc/security/limits.d/99-nofile.conf
*        soft    nofile    65535
*        hard    nofile    65535
root     soft    nofile    65535
root     hard    nofile    65535
```

`pam_limits` only takes effect for sessions opened through a PAM stack that includes it. Check whether sshd does:

```bash
grep -i pam_limits /etc/pam.d/sshd /etc/pam.d/login /etc/pam.d/su 2>/dev/null
```

If `UsePAM no` is set in `sshd_config`, `limits.conf` is ignored entirely for SSH sessions. And if `sshd` is started by systemd (it always is), the *daemon's* own limit comes from its unit file, not from `limits.conf` — a distinction that matters when you are trying to support 5,000 concurrent SSH sessions rather than 5,000 processes per session.

`cron` and `at` also need `pam_limits` in their PAM config, otherwise scheduled jobs inherit the systemd default of 1024 regardless of `limits.conf`.

## Containers and Kubernetes

Docker applies a default nofile limit that comes from the daemon, and `--ulimit` overrides it per container:

```bash
docker run -d --ulimit nofile=65535:65535 nginx:alpine
docker inspect --format '{{.HostConfig.Ulimits}}' <container>
```

With Compose:

```yaml
services:
  api:
    image: myorg/api:2026.11
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
    # Verify from inside: cat /proc/1/limits
```

Kubernetes does **not** set a useful default. The container inherits the runtime default, which on many nodes is 1048576 hard / 1024 soft. Set it explicitly:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api
spec:
  containers:
    - name: api
      image: myorg/api:2026.11
      securityContext:
        capabilities:
          drop: ["ALL"]
      # No nofile field exists in the pod spec. The limit comes from the
      # container runtime, so set it there (see below) or raise it in the
      # image entrypoint before the main process starts.
      command: ["/bin/sh", "-c", "ulimit -n 65535 && exec /app/server"]
```

Because the pod spec has no `nofile` field, the durable fix belongs one level down — on the runtime's systemd unit, which every container on the node then inherits:

```ini
# systemctl edit containerd
[Service]
LimitNOFILE=1048576
```

```bash
systemctl daemon-reload && systemctl restart containerd
# Every container started afterwards inherits the higher limit
```

## Kernel sysctls: the ceilings above everything else

```bash
# /etc/sysctl.d/99-files.conf
fs.file-max = 2097152
fs.nr_open = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 1024
```

```bash
sysctl --system
```

Order matters: **`fs.nr_open` must be greater than or equal to any per-process hard limit you set.** If a unit declares `LimitNOFILE=4194304` while `fs.nr_open` is 1048576, systemd will silently clamp it, and you will spend another hour wondering why `prlimit` shows a lower number than the unit file says. Verify with:

```bash
sysctl fs.nr_open fs.file-max
systemctl show myservice -p LimitNOFILE
```

The inotify settings are a separate exhaustion mode that produces a confusingly similar error — `ENOSPC: inotify watch limit reached`. `inotify-tools` (**3,438 stars, pushed 2026-11-18**) is the standard way to see how many watches your tree actually needs:

```bash
# How many watches does this tree require?
find /srv/app -type d | wc -l

# Live event stream while you reproduce the failure
inotifywait -m -r -e create,delete,modify /srv/app | head -20
```

Every directory under a recursive watch costs one inotify watch. A Node.js dev server watching a monorepo with 300,000 directories needs `max_user_watches` well above the 8,192 default that many distributions still ship.

## Sizing math worth memorizing

- **nginx**: each worker can hold up to `worker_connections` descriptors, and each proxied request consumes **two** (client + upstream). With `worker_connections 8192` and 4 workers you need at least 32,768 descriptors, plus headroom.
- **HAProxy**: `maxconn` is per process; the process needs `maxconn + listeners + logs`. Setting `maxconn 60000` with a 1024 soft limit produces exactly the EMFILE storm you are trying to avoid.
- **PostgreSQL**: one descriptor per backend connection plus one per open relation. `max_connections = 500` with a heavy schema can exceed 3,000 descriptors.
- **Redis**: one descriptor per client plus persistence files. `maxclients 10000` needs at least 10,032.
- **Java services**: each socket plus each opened file plus JAR files on the classpath. A Spring Boot app with 40 dependencies can hold several hundred descriptors before serving a single request.

## Pitfalls that keep this bug alive

- **Editing `limits.conf` and restarting a systemd service.** systemd never reads it. Use `LimitNOFILE`.
- **Setting only the soft limit.** Applications frequently try to raise their own limit; if the hard limit is 1024, the raise fails silently.
- **Forgetting `fs.nr_open`.** Per-process limits above `fs.nr_open` are clamped without a warning.
- **Assuming `ulimit -n` in your shell reflects the service.** It reflects *your shell*, and only if you started it after the change.
- **Raising limits to hide a leak.** An fd count that grows monotonically under steady load is a bug. Raising the ceiling from 1024 to 1,048,576 buys you time and a much larger blast radius.
- **Ignoring `file-nr`'s third column.** If it is `9223372036854775807`, the host-wide ceiling is not the constraint and you should stop tuning `fs.file-max`.
- **Setting `LimitNOFILE` higher than needed on every unit.** Extremely high hard limits weaken the protection against runaway processes. Size it to the workload.
- **Forgetting the sidecar.** In a pod with a service mesh proxy, the proxy holds a second copy of every connection; both containers need the limit.

## Verification checklist after any change

```bash
# 1. Effective limit inside the running process
cat /proc/$(pgrep -n myservice)/limits | grep -i "open files"

# 2. systemd's view of the unit
systemctl show myservice -p LimitNOFILE

# 3. Kernel ceilings
sysctl fs.nr_open fs.file-max

# 4. Current usage and headroom
cat /proc/sys/fs/file-nr

# 5. Per-process usage trend under load
watch -n2 'ls /proc/$(pgrep -n myservice)/fd | wc -l'
```

If steps 1 and 2 disagree, you have an override somewhere: a drop-in in `/etc/systemd/system/<unit>.d/`, a slice (`Slice=` inherits from the parent slice's limits), or a container runtime default layered on top.

Related reading on this site: the [OOM prevention guide](../2026-05-27-self-hosted-linux-oom-prevention-earlyoom-systemd-oomd-psi-guide/) covers the other resource-exhaustion failure mode and how `systemd-oomd` interacts with service limits, the [block I/O latency tracing walkthrough](../2026-05-24-self-hosted-block-io-latency-tracing-blktrace-vs-ioping-vs-iotop-guide/) helps when EMFILE symptoms are actually I/O stalls, and the [sysctl and tuned tuning guide](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/) covers the kernel parameters that sit above the per-process limits described here.

## FAQ

**Why does `ulimit -n` show 1024 when I set 65535 in limits.conf?**
Because `limits.conf` is applied by `pam_limits` at login, and only for PAM-aware sessions opened after the change. Existing shells, systemd services, and containers keep their original limits. Log out and back in, use `prlimit` on a running process, or set `LimitNOFILE` for systemd units.

**Does raising `fs.file-max` fix "Too many open files"?**
Only if `/proc/sys/fs/file-nr` shows the first column approaching the third. On modern kernels the default `fs.file-max` is astronomically large (`9223372036854775807`), so the practical ceiling is almost always `fs.nr_open` or the process's own soft limit.

**What is the difference between soft and hard limits?**
The soft limit is what the kernel enforces right now; the hard limit is the ceiling a process may raise its soft limit to without privileges. `LimitNOFILE=65535` in a unit sets both. `LimitNOFILE=1024:65535` sets soft 1024, and the application must raise it — which many daemons never do.

**How do I fix EMFILE in a container without rebuilding the image?**
Restart the container with `--ulimit nofile=65535:65535` (Docker) or set the limit in the pod spec / runtime config (Kubernetes, containerd). You cannot raise a container's hard limit from inside it. For a running process you control, `prlimit --pid` works only up to the hard limit the container was started with.

**Is a high `LimitNOFILE` dangerous?**
It removes a safety net. A leaking process with a 1,048,576 limit will consume memory for descriptor tables and can starve other services of kernel memory before anyone notices. Size the limit to roughly 2× your measured peak and alert on descriptor growth rate, not just on the limit.

**Why do I get `ENOSPC` instead of `EMFILE` when watching files?**
inotify exhaustion reports `ENOSPC`, not `EMFILE`. Raise `fs.inotify.max_user_watches` and `fs.inotify.max_user_instances`, and check whether a single process is recursively watching a directory tree with hundreds of thousands of subdirectories.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Too Many Open Files in 2026: ulimit, systemd Limits and Kernel Tuning Explained",
  "description": "Complete guide to Linux file descriptor limits: the six independent layers including ulimit, pam_limits, systemd LimitNOFILE, container runtimes, fs.nr_open and fs.file-max, with measurement commands and copy-paste fixes.",
  "datePublished": "2026-11-21",
  "dateModified": "2026-11-21",
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
