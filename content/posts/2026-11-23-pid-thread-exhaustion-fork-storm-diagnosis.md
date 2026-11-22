---
title: "PID and Thread Exhaustion in 2026: Why 'Resource Temporarily Unavailable' Hits a Healthy Server"
date: "2026-11-23"
tags: ["linux", "troubleshooting", "systemd", "cgroups", "performance"]
draft: false
description: "Five different kernel limits all report EAGAIN. A field guide to pid_max, threads-max, pids.max, TasksMax and RLIMIT_NPROC, with real values from a 28 GB production host."
---

Your monitoring is green. Memory is fine. Disk is fine. Load average is under 1. And yet at 03:14 the app log fills with `fork: Resource temporarily unavailable`, `pthread_create: EAGAIN`, or Go's `failed to create new OS thread` — and the service stops accepting work until someone restarts it.

Here is the uncomfortable part: **"Resource temporarily unavailable" is not a message about memory.** It is `EAGAIN` from `clone()`/`fork()`, and on a modern Linux box it comes from one of five independent limits, four of which have nothing to do with `kernel.pid_max`. Chasing the wrong one is why the same incident repeats every few weeks.

I pulled the real numbers from the host that generated this article so you can compare against your own box instead of tuning blind:

```console
$ cat /proc/sys/kernel/pid_max /proc/sys/kernel/threads-max
4194304
220852

$ ls /proc | grep -c '^[0-9]'
517
$ ps -eLf | wc -l
2085

$ ulimit -u
110426
$ systemctl show --property=DefaultTasksMax
DefaultTasksMax=33127

$ sysctl fs.nr_open vm.max_map_count
fs.nr_open = 1048576
vm.max_map_count = 1048576
```

517 processes, 2,085 threads, and a PID ceiling of 4.2 million. Nothing here is remotely close to exhaustion — which is exactly the point. **On kernel 5.x+, `pid_max` is almost never the limit that fires.** The limits that fire are per-cgroup, per-service, or per-UID, and they are much smaller than people assume.

## TL;DR — Which Limit Actually Fired?

Read the failing call path first, then act:

- **`fork()` / clone fails, the process itself is a container entrypoint** → check `pids.max` in cgroup v2 for that container. Docker's `--pids-limit` and Kubernetes `pids.max` in the pod cgroup are the usual suspects; the default in many distro systemd setups is **15% of `kernel.threads-max`**, not "unlimited."
- **`fork()` fails for one service under systemd, siblings are fine** → the unit hit `TasksMax`.
- **`pthread_create` fails while `ps` shows almost no processes** → it is thread *stack address space*, i.e. `RLIMIT_STACK × thread count` hitting the mapping ceiling, or `vm.max_map_count`.
- **`su`/`sudo`/`cron` fails with "Resource temporarily unavailable" but root shells work** → `RLIMIT_NPROC` is counted **per UID**, and every container or worker running as that UID shares one budget.
- **Only a full reboot fixes it and PIDs keep climbing** → a genuine fork leak, not a limit. Fix the leak; raising limits only buys days.

Everything else in this article is the "how do I prove which one it was" part.

## The Five Limits, Side by Side

These are the numbers from the host above. Note how far the defaults are from each other — a 4.2 million PID ceiling next to a 33,127 task ceiling is a 127× difference.

| Limit | Real value on this host | Scope | Enforced by | Failing syscall reports |
|---|---|---|---|---|
| `kernel.pid_max` | 4,194,304 | Whole system, PID allocation | kernel | `fork: Resource temporarily unavailable` (very rare) |
| `kernel.threads-max` | 220,852 | Whole system, total tasks | kernel | same `EAGAIN`, printed once with `fork:` |
| `DefaultTasksMax` (systemd) | 33,127 (= 15% of threads-max) | Every `.service` unless overridden | systemd / cgroup `pids.max` | `fork()` in the unit's log, `pids.max` in `cgroup.events` |
| cgroup v2 `pids.max` | per-container, often 512–4096 | Container or slice | cgroup pids controller | `clone: EAGAIN`, runtime-specific messages |
| `RLIMIT_NPROC` (`ulimit -u`) | 110,426 | **Per real UID**, all its tasks | kernel, on `setuid`/`fork` | `su: cannot fork`, `fork: retry` |
| `vm.max_map_count` | 1,048,576 (distro-dependent) | Per process, mapping count | kernel, `mmap` | `pthread_create: EAGAIN`, `Out of memory` on `mmap` |

Read that table once and the incident shape becomes obvious: **the per-container and per-UID numbers are the small ones.** Root on this host can spawn 110k tasks; a container capped at 512 cannot, no matter what `pid_max` says.

## Decision Matrix: Symptom → Layer → Command

| What you see | Likely layer | First command to run |
|---|---|---|
| Container dies, restarts cleanly, only under burst traffic | cgroup `pids.max` | `cat /sys/fs/cgroup/pids.max /sys/fs/cgroup/pids.current` inside the container |
| One systemd service returns 503, others healthy | `TasksMax` on the unit | `systemctl show -p TasksMax -p TasksCurrent <unit>` |
| `su`/`sudo`/backup cron fails, root shell fine | `RLIMIT_NPROC` per UID | `ps -u <user> -L --no-headers \| wc -l` and `grep <uid> /etc/security/limits.conf` |
| `pthread_create` fails, process count looks low | stack reservation / map count | `ulimit -s`, `wc -l < /proc/<pid>/maps`, `sysctl vm.max_map_count` |
| PID count monotonically rising for days | fork leak | `ps -eo pid,ppid,stat,lstart,comm \| grep -c defunct` |
| Everything forks fine until 03:00 | cron/logrotate stampede | `journalctl -S today \| grep -c "session opened"` |

## Reading the Numbers That Actually Bind

Two commands answer 80% of these incidents. First, per-service task accounting:

```console
$ systemctl show --property=TasksMax --property=TasksCurrent hermes-gateway
TasksCurrent=22
TasksMax=33127
```

`TasksCurrent=22` against `TasksMax=33127` is a service with enormous headroom. When `TasksCurrent` sits **at or within 5% of `TasksMax`**, you have found the wall — and you will usually see it before the log message, because systemd reports the throttling in `systemctl status` as a `Tasks` line pinned at the limit.

Second, the container view. Inside a cgroup v2 container:

```bash
# current vs ceiling for this container
cat /sys/fs/cgroup/pids.current
cat /sys/fs/cgroup/pids.max

# did we ever bounce off the ceiling?
grep pids /sys/fs/cgroup/pids.events
# max 1247   <- number of times fork() was rejected
```

That `max` counter in `pids.events` is the single most underused debugging signal on Linux. It increments every time the controller rejects a `fork()`, so a non-zero value proves the limit fired even if the application swallowed the error. If `pids.events` shows `max 0`, stop tuning process limits — your problem is elsewhere.

## The 15% Rule That Surprises Everyone

Look again at the two numbers from this host: `threads-max` is 220,852 and `DefaultTasksMax` is 33,127. That is not a coincidence:

```console
$ python3 -c "print(int(220852 * 0.15))"
33127
```

systemd derives `DefaultTasksMax` from **15% of `kernel.threads-max`**. On a 28 GB machine that yields ~33k — plenty. On a small 2 GB VPS it yields a few thousand, and on a memory-constrained container host with a low `threads-max` it can land under 1,000. A Java service with 200 threads × 40 worker processes can hit that on a busy day, and the failure looks like a random application bug.

Check yours before you need it:

```bash
systemctl show -p DefaultTasksMax
# and for anything that spawns aggressively:
systemctl show -p TasksMax -p TasksCurrent nginx php8.3-fpm postgresql
```

The fix is per-unit, not global:

```ini
# /etc/systemd/system/myapp.service.d/tasks.conf
[Service]
TasksMax=infinity
LimitNPROC=65535
LimitNOFILE=131072
```

```bash
systemctl daemon-reload && systemctl restart myapp
```

**Do not set `TasksMax=infinity` system-wide** by editing `DefaultTasksMax` in `systemd-system.conf`. It disables the only guardrail that stops one runaway unit from consuming the whole PID space and turning a single-service incident into a node-wide outage.

## RLIMIT_NPROC: The Per-UID Trap

`ulimit -u` is 110,426 here, which sounds infinite until you remember the accounting rule: **`RLIMIT_NPROC` counts every task owned by the real UID, across the entire system — including tasks in other containers that share that UID.**

This is the classic shared-hosting failure: `www-data` inside three Docker containers, plus PHP-FPM on the host, plus a log shipper, all running as UID 33. Each container thinks it has its own budget. The kernel does not.

Detect it by counting real tasks per UID, not per process tree:

```bash
# total tasks per UID, sorted
ps -eLo uid --no-headers | sort -n | uniq -c | sort -rn | head

# and the hard ceiling for a user
su -s /bin/sh -c 'ulimit -u' www-data
```

If the count per UID approaches the ceiling, the fix is to give each workload a **distinct UID** (the standard `PUID`/`PGID` pattern used by community container images exists precisely for this) or to raise the limit in `/etc/security/limits.d/`:

```ini
# /etc/security/limits.d/90-webapps.conf
www-data  soft  nproc  32768
www-data  hard  nproc  65536
```

Note that `pam_limits` applies at login/session creation, so a running daemon keeps its old limit until restarted. Userspace tools reading limits from `/proc/<pid>/limits` are the reliable check:

```bash
grep -E "processes|open files" /proc/$(pgrep -o php-fpm)/limits
```

## Thread Exhaustion Without Process Growth

The nastiest variant: `pthread_create` returns `EAGAIN`, `ps` shows 40 processes, and every process limit looks fine. Two mechanisms explain almost all of it.

**1. Stack reservation.** Each thread reserves `RLIMIT_STACK` of *virtual* address space. With the common 8 MB default, 4,000 threads reserve 32 GB of address space before doing any work. On a 64-bit host that is survivable; inside a container with a low `RLIMIT_AS`, it is fatal. Check both sides:

```bash
ulimit -s              # typically 8192 KB
grep -E "Max address space" /proc/<pid>/limits
```

The practical fix is to reduce thread stack size in the application (JVM `-Xss`, Go's `debug.SetMaxStack` is not it — Go uses 8 KB segments and this rarely applies) rather than to raise limits.

**2. `vm.max_map_count`.** Every thread stack, every `mmap`ed file, and every allocator arena is a memory mapping. Glibc's malloc creates up to 8 arenas per core × 8 MB, so a 64-core box with a heavy allocation pattern grows thousands of mappings without leaking a byte. Confirm with a map count:

```bash
for p in $(pgrep -f myapp); do echo "$(wc -l < /proc/$p/maps) $p"; done | sort -rn | head
```

If a single process is above ~20,000 maps, you are within striking distance of the old 65,530 default that Debian 12 and RHEL 8 still ship. Ubuntu 24.04 raised it to 1,048,576 (as on this host), which is why the same container image crashes on one distro and not another. The distro-independent fix:

```bash
# /etc/sysctl.d/99-maps.conf
vm.max_map_count = 1048576
```

```bash
sysctl --system
```

## Fork Storms: Proven Leaks vs. Traffic Spikes

Before you raise any ceiling, prove whether usage is **bounded** or **leaking**. A leak plus a higher limit equals a delayed outage.

```bash
# 1. Is the growth monotonic? sample twice, 60s apart
ls /proc | grep -c '^[0-9]'; sleep 60; ls /proc | grep -c '^[0-9]'

# 2. Zombies indicate a parent that never reaps
ps -eo stat,comm --no-headers | awk '$1 ~ /Z/ {print $2}' | sort | uniq -c | sort -rn | head

# 3. Did something executed via cron/logrotate cluster?
journalctl --since "03:00" --until "03:20" | grep -cE "session opened|Starting Session"
```

If the count returns to baseline, you have a **stampede** — fix it with `RandomizedDelaySec=` in the timer unit or `maxage`/`size` tuning on log rotation. If it only ever climbs, you have a **leak**: every orphaned child, unreaped zombie, or forgotten `subprocess.Popen` consumes a slot forever. Raising `TasksMax` in that scenario just moves the outage to next month.

## Pitfalls and Migration Notes

- **`pid_max` is a red herring on kernels ≥ 5.4.** The default is 4,194,304 (up from 32,768 in ancient kernels). Raising it changes nothing unless you are genuinely on a 4-million-task box.
- **Docker `--pids-limit` is not inherited by grandchildren the way you expect.** It applies to the whole container cgroup, so a build container compiling with `-j64` can starve its own shell.
- **`LimitNPROC` in a systemd unit overrides `limits.conf`** for that service. Setting one and wondering why the other had no effect wastes hours.
- **`TasksMax` counts threads, not processes.** A single Python process with 200 threads uses 200 of the budget.
- **Raising `threads-max` requires enough memory to back the stacks.** `kernel.threads-max` is bounded by `kernel.pid_max` and by available memory; on small VPS instances the memory bound bites first and the resulting messages look like OOM kills, not fork failures.
- **Kubernetes:** `pids.max` lives in the **pod** cgroup, so all containers in a pod share it. A sidecar with chatty subprocess behavior can starve the main container while its own metrics look healthy.

## FAQ

**What does "fork: Resource temporarily unavailable" actually mean?**
It is `EAGAIN` returned by `clone()`/`fork()`. The kernel could not allocate a new task, for one of five reasons: the per-cgroup `pids.max` was hit, the unit's `TasksMax` was hit, the per-UID `RLIMIT_NPROC` was hit, the system-wide `threads-max` was reached, or address-space/mapping limits blocked thread stack creation. Memory pressure is usually *not* the cause, which is why free RAM does not clear the error.

**Is `kernel.pid_max` the limit I should raise first?**
No. On any kernel from the last several years `pid_max` defaults to 4,194,304. Check `pids.max` in the cgroup and `TasksMax` on the unit first — those are orders of magnitude smaller and are what actually fail on healthy hosts.

**How do I see whether a container ever hit its task limit?**
Read `/sys/fs/cgroup/pids.events` inside the container. The `max` counter increments once per rejected `fork()`. A non-zero value proves the limit fired; `max 0` means process limits are not your problem and you should look at `vm.max_map_count` or `RLIMIT_AS` instead.

**Why does the same image crash inside one container runtime and not another?**
Because the limits are inherited from the parent cgroup and from the host's sysctls — not baked into the image. Ubuntu 24.04 ships `vm.max_map_count=1048576` while Debian 12 and RHEL 8 still ship 65530, so a thread-heavy service can die on the older distro with no code change at all.

**Does raising `TasksMax` to infinity fix a fork leak?**
No — it delays the failure. If the process count never returns to baseline after a spike, you are leaking tasks (unreaped zombies or orphaned children), and an unlimited ceiling converts a fast, diagnosable failure into a slow node-wide outage. Find the leak with `ps -eo stat,comm` and fix the reaping, then size the ceiling from measured peaks.

For deeper context on the surrounding limits, see our [guide to systemd, PAM and cgroup v2 resource limits](../2026-05-24-self-hosted-linux-process-resource-limits-systemd-pam-limits-cgroup-v2-guide/), the companion piece on [file descriptor exhaustion and ulimit tuning](../2026-11-21-too-many-open-files-ulimit-systemd-limits-tuning/), and the memory-side view in [RSS vs PSS vs USS container accounting](../2026-11-22-rss-pss-uss-container-memory-accounting/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PID and Thread Exhaustion in 2026: Why 'Resource Temporarily Unavailable' Hits a Healthy Server",
  "description": "Five kernel limits report EAGAIN. Field guide to pid_max, threads-max, pids.max, TasksMax and RLIMIT_NPROC with real production values.",
  "datePublished": "2026-11-23",
  "dateModified": "2026-11-23",
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
