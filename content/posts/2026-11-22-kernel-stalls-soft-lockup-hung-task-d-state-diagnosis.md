---
title: "When the Kernel Stops Answering: Soft Lockups, Hung Tasks and D-State Storms in 2026"
date: "2026-11-22"
tags: ["linux", "kernel", "troubleshooting", "performance-tuning", "reliability"]
draft: false
description: "How to read Linux kernel stall detectors - soft lockup, hard lockup, hung task, RCU stall - and capture the evidence before the machine recovers and forgets."
---

Fifteen minutes ago, SSH into the box hung. No prompt, no error, no disconnect — the connection just sat there. Then it came back on its own, and everything looks normal. `top` shows nothing wrong. The application logged nothing. No OOM kill, no panic, no reboot.

There is exactly one piece of evidence, and it is in a ring buffer that gets overwritten:

```text
[4123351.882701] INFO: task java:2491 blocked for more than 120 seconds.
[4123351.882744]       Not tainted 6.17.0-14-generic #14-Ubuntu
[4123351.882790] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
[4123351.882831] task:java            state:D stack:    0 pid: 2491 ppid:     1 flags:0x00000000
[4123351.882912] Call Trace:
[4123351.882948]  <TASK>
[4123351.882963]  __schedule+0x3d1/0x8a0
[4123351.883001]  schedule+0x63/0x110
[4123351.883042]  io_schedule+0x46/0x70
[4123351.883081]  folio_wait_bit_common+0x13a/0x320
```

That is the kernel telling you a thread was stuck in uninterruptible sleep for two minutes, inside a page-fault path waiting on a folio. **The machine did not crash — it stalled, and the only record is this trace.** This guide is about reading those traces and, more importantly, capturing them before they scroll away.

## TL;DR — Quick Verdict

- **Linux has five independent stall detectors** — soft lockup, hard lockup, hung task, RCU stall, and plain D-state accumulation. Each has its own dmesg signature and its own timeout knob. Learn the signatures and triage takes seconds.
- **`INFO: task ... blocked for more than 120 seconds` is not the bug.** It is a symptom report from the hung-task detector. The `Call Trace:` below it is the actual evidence — read the frame above `schedule`.
- **High load average with idle CPUs means D-state tasks.** `/proc/loadavg` counts uninterruptible sleep as load. A D-state storm produces load 40 on an idle 16-core box.
- **You cannot `kill -9` a D-state process.** Signals are delivered on return to userspace, and it will never return while wedged in the kernel. Fix the resource it is waiting on.
- **`kernel.sysrq` is usually a bitmask that does not include process dumps.** On a default Ubuntu host it is `176`, which silently disables `sysrq-w` — the exact command you need mid-incident.

## The Five Detectors, Compared

| Detector | dmesg signature | Default trigger | Reports | Timeout knob |
|---|---|---|---|---|
| Soft lockup | `watchdog: BUG: soft lockup - CPU#3 stuck for 23s!` | One task holds a CPU >20s without scheduling | Kernel code spinning in a loop without yielding | `kernel.watchdog_thresh` (10s, trigger is 2x) |
| Hard lockup | `watchdog: BUG: hard LOCKUP` / `NMI watchdog: hard LOCKUP` | CPU stops responding to interrupts | Interrupts disabled forever, or CPU fully wedged | `kernel.nmi_watchdog=1` + `watchdog_thresh` |
| Hung task | `INFO: task X:pid blocked for more than 120s` | Task in `D` state >120s | A thread stuck in uninterruptible sleep | `kernel.hung_task_timeout_secs` |
| RCU stall | `INFO: rcu_preempt detected stalls on CPUs/tasks` | Grace period not completing | A CPU not passing through quiescent states | `kernel.rcu_cpu_stall_timeout` |
| D-state accumulation | nothing — only visible in `loadavg` / `ps` | — | Storage or network I/O that never completes | none (symptom only) |

The distinction that matters operationally: **soft lockup and hard lockup are CPU-side bugs, hung task and D-state are I/O-side waits, and RCU stall is usually a consequence of either.** If you see all of them at once, fix the first one — the others are downstream noise.

## Reading the Signatures

**Soft lockup** — a kernel thread or syscall spun on one CPU for more than twice `watchdog_thresh`. The message names the CPU and the task that was running when the watchdog fired:

```text
watchdog: BUG: soft lockup - CPU#3 stuck for 23s! [kworker/3:1:1842]
Modules linked in: nf_tables ...
CPU: 3 PID: 1842 Comm: kworker/3:1 Not tainted 6.17.0-14-generic
RIP: 0010:queue_work_on+0x2c/0x60
Call Trace:
 <IRQ>
 nf_hook_slow+0x...
```

The `RIP:` line is the instruction being executed — that is your bug, not the stack trace.

**Hung task** — a userspace thread sat in `D` state for `hung_task_timeout_secs` (120s default). The trace shows the wait: `io_schedule` means block I/O, `rpc_wait_bit_killable` means NFS, `__flush_work` means a workqueue is stuck behind something else.

**RCU stall** — a CPU failed to report a quiescent state for a full grace period. On virtualized hosts this is frequently caused by steal: the vCPU simply was not scheduled (see our [CPU steal time guide](../2026-11-22-cpu-steal-time-vm-diagnosis-mpstat-per-vcpu/) for how to confirm that). On bare metal it usually accompanies a soft lockup.

## The D-State Trap: Load Average Lies

`/proc/loadavg` counts **runnable + uninterruptible** tasks. Read the fields carefully:

```text
$ cat /proc/loadavg
2.47 1.93 1.81 3/2095 2321874
```

Fields: 1-min, 5-min, 15-min averages, then `runnable/total_threads`, then the last PID. Here 3 of 2,095 threads are runnable, and load 2.47 on a 16-core host is trivial.

Now the classic incident: load average 60 on a 16-core box where every CPU reads 95% idle. That is not a CPU problem — **60 tasks are stuck in `D` state**, almost always waiting on storage or a network filesystem. Count them:

```bash
$ ps -eo state | grep -c "^D"
0

$ ps -eo pid,stat,wchan:30,comm | awk '$2 ~ /^D/'
```

On the healthy host above the count is zero. On a sick host this command names the culprit and, in `wchan`, the kernel function it is sleeping in — `io_schedule`, `nfs_wait_bit_killable`, `rwsem_down_read_slowpath`. One line, and you know whether to look at the disk or at a lock.

Two practical corollaries:

1. **`kill -9` does nothing.** A `D`-state task cannot run the signal handler. It will die only when the underlying I/O completes or times out. Containers make this worse: in `D` state the container's `SIGKILL` also fails, so `docker stop` hangs for its full 10-second grace and then reports failure even though the container is technically still there.
2. **Alerts on load average are misleading.** Alert on `node_load1` and you will page on a stuck NFS mount with idle CPUs. Alert on PSI `io.pressure` or on `D`-state counts instead.

## Capturing Evidence While It Is Happening

The hardest part of these incidents is that they self-heal. Everything below must be issued **during** the stall, or configured in advance.

**1. `sysrq-t` / `sysrq-w` — dump all tasks or only blocked tasks.** These go straight to the kernel ring buffer, so they work even when userspace is unusable:

```bash
echo t > /proc/sysrq-trigger   # all tasks, with kernel stacks
echo w > /proc/sysrq-trigger   # only uninterruptible (D) tasks
echo l > /proc/sysrq-trigger   # backtrace every CPU (NMI)
echo m > /proc/sysrq-trigger   # memory state
```

**The trap:** `/proc/sysrq-trigger` requires the corresponding bit in `kernel.sysrq`. Check it before you need it — real value from a stock host:

```text
$ cat /proc/sys/kernel/sysrq
176
```

176 = 128 (reboot/poweroff) + 32 (remount read-only) + 16 (sync). **Bit 8 — "debugging dumps of processes" — is not set**, so `echo w` above silently does nothing. `sysrq-w` needs 184 (`176 + 8`); process signalling (`sysrq-i`, `sysrq-k`) needs 64, giving 240. Set the value you need:

```bash
sysctl -w kernel.sysrq=1      # everything: fine on a dev box, risky on prod
sysctl -w kernel.sysrq=184    # dumps + sync + remount-ro + reboot
```

**2. `/proc/<pid>/stack` — the kernel stack of a specific task, no sysrq needed:**

```bash
$ cat /proc/2491/stack
[<0>] folio_wait_bit_common+0x13a/0x320
[<0>] filemap_fault+0x...
[<0>] __do_fault+0x...
[<0>] handle_mm_fault+0x...
[<0>] do_user_addr_fault+0x...
```

This is the single highest-value command in the entire workflow. It answers "what is it waiting on" in one file read, requires only root, and is safe on production.

**3. `perf` to catch a spinning CPU.** For soft lockups, sample the stack from another CPU:

```bash
perf top -C 3                 # which symbol is burning CPU 3
perf record -C 3 -g -- sleep 10 && perf report --stdio | head -40
```

If `perf` shows 100% of samples in a single kernel function, you have found the loop. For long-term capture, `perf record -a -g -- sleep 30` during the stall gives you a flamegraph afterwards.

## Tuning the Detectors So They Help You

Defaults are conservative. These are real values from a 16-core host running kernel 6.17:

```text
$ sysctl kernel.hung_task_timeout_secs kernel.hung_task_warnings kernel.hung_task_panic \
         kernel.softlockup_panic kernel.watchdog_thresh kernel.nmi_watchdog
kernel.hung_task_timeout_secs = 120
kernel.hung_task_warnings = 10
kernel.hung_task_panic = 0
kernel.softlockup_panic = 0
kernel.watchdog_thresh = 10
kernel.nmi_watchdog = 1
```

Recommended production profile, written to `/etc/sysctl.d/90-stall-detection.conf`:

```ini
# Report stalls sooner, but never reboot automatically
kernel.hung_task_timeout_secs = 60
kernel.hung_task_warnings = 20
kernel.hung_task_panic = 0
kernel.softlockup_panic = 0
kernel.watchdog_thresh = 10
kernel.nmi_watchdog = 1
kernel.sysrq = 184

# Persist kernel messages across a crash
kernel.panic_on_oops = 0
kernel.panic = 10
```

Apply with `sysctl --system`. Two rules that matter more than the numbers:

- **Never set `hung_task_panic=1` unless you have working kdump.** Turning a 60-second stall into a reboot loses the evidence and the availability. The [crash dump analysis workflow](../2026-05-29-self-hosted-linux-crash-dump-analysis-crash-makedumpfile-kdump-guide/) is the prerequisite, not the follow-up.
- **`hung_task_warnings` caps the number of reports**, not the timeout. On a host with many stuck threads, the default of 10 means the interesting task is often the eleventh. Raise it to 20-50.

## Making the Evidence Survive a Reboot

The ring buffer is a few megabytes and gets overwritten under log pressure. Two ways to prevent losing the trace:

```bash
# 1. Forward kernel messages off-box in real time (works even when the disk is stuck)
modprobe netconsole netconsole=@10.0.0.5/eth0,@10.0.0.9/514
```

The persistent version belongs in `/etc/modprobe.d/netconsole.conf` plus a matching `rsyslog` listener on the collector — covered in detail in the [kernel remote logging guide](../2026-06-01-linux-kernel-remote-logging-netconsole-rsyslog-pstore-guide/).

```ini
# 2. /etc/systemd/system.conf — let systemd catch a wedged userspace
RuntimeWatchdogSec=20
RebootWatchdogSec=10min
```

`RuntimeWatchdogSec` makes PID 1 pet the hardware watchdog. If userspace stops scheduling for 20 seconds, the machine reboots instead of hanging indefinitely — a blunt instrument, but it converts an unbounded outage into a 30-second one.

## The Five Mistakes That Turn a 60-Second Stall into a 6-Hour Outage

1. **Greping `dmesg` for `error` and finding nothing.** None of these messages contain the word "error". They contain `BUG`, `INFO`, and `blocked`. Search for `lockup|blocked for more than|stall`.
2. **Assuming a D-state process can be killed.** `kill -9` queues a signal the task cannot receive. Restarting the container is not enough either — the kernel task survives, and a new one piles onto the same wedged mount.
3. **Setting `hung_task_panic=1` without kdump.** You get a reboot loop with no crash dump and less information than before.
4. **Chasing a soft lockup with I/O tuning.** A soft lockup is a CPU-side spin. Look at `RIP:` and `perf`, not at `iostat`. Conversely, chasing a hung task with `nice` and CPU pinning wastes hours on what is really a dead disk.
5. **Reading the trace bottom-up.** The frames *below* `schedule` are generic scheduler machinery — identical in every hung-task report. The frame immediately **above** `schedule` is the specific wait, and that is the only interesting line.

And when the wait is on storage rather than on a lock, the [fsync durability investigation](../2026-11-22-fsync-durability-lies-linux-storage-write-cache/) explains why an apparently successful write can still leave a thread blocked for minutes.

## FAQ

**What is the difference between a soft lockup and a hung task?**
A soft lockup means kernel code held a CPU for more than twice `watchdog_thresh` (20 seconds by default) without voluntarily yielding — it is a CPU-side spin or a very long loop. A hung task means a thread has been in uninterruptible (`D`) sleep for over 120 seconds, almost always waiting on I/O. Soft lockups are kernel bugs; hung tasks are usually environmental failures the kernel is reporting.

**Why did my `echo w > /proc/sysrq-trigger` produce no output at all?**
Because `kernel.sysrq` is a bitmask and the process-dump bit (8) is not set. A value of `176` — common on Ubuntu — allows sync, remount-read-only and reboot, but silently disables `sysrq-w` and `sysrq-t`. Set `kernel.sysrq=184` to add process dumps, or `1` to enable everything.

**Can a D-state process be killed?**
Not directly. Signals are delivered when the task returns to userspace, and an uninterruptible task never gets there. You must resolve the resource it waits on — restart the NFS server, replace the failing disk, clear the blocked device — and the task will then exit or finally accept the queued `SIGKILL`. In containers this means `docker stop` will time out while the task remains in `D`.

**Why is the load average 60 when every CPU is 95% idle?**
Because Linux load average counts tasks in `D` state as load. Sixty stuck tasks with idle CPUs is the canonical D-state storm, usually a dead storage path or an unresponsive network filesystem. Confirm with `ps -eo state | grep -c "^D"` and inspect `ps -eo pid,stat,wchan:30,comm` to see which kernel function each is sleeping in.

**Do RCU stalls matter on their own?**
Sometimes not. On a virtualized host, an RCU stall often just means the vCPU was descheduled long enough to miss a grace period — the same mechanism that produces high `%steal`. On bare metal, an RCU stall paired with a soft lockup means the CPU was wedged. Treat RCU stalls as a corroborating signal and resolve the underlying lockup or steal issue.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "When the Kernel Stops Answering: Soft Lockups, Hung Tasks and D-State Storms in 2026",
  "description": "How to read Linux kernel stall detectors - soft lockup, hard lockup, hung task, RCU stall - capture kernel stacks mid-incident, and avoid the sysrq bitmask trap.",
  "datePublished": "2026-11-22",
  "dateModified": "2026-11-22",
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
