---
title: "tcp_mem in 2026: Why Linux Refuses New Sockets With 11 GB of RAM Free"
date: "2026-11-23"
tags: ["linux", "networking", "troubleshooting", "kernel", "performance"]
draft: false
description: "Kernel TCP memory accounting explained with real sockstat, skmem and nstat counters — why tcp_mem pressure has nothing to do with free RAM."
---

The message in `dmesg` reads like a joke when `free -h` shows eleven gigabytes available:

```console
$ dmesg -T | grep -i "tcp.*memory"
[Thu Nov 20 03:14:07 2026] TCP: out of memory -- consider tuning tcp_mem
```

No process was killed. No container restarted. Instead, throughput to one service collapsed, `ss` showed connections stuck in `SYN-SENT` and `CLOSE-WAIT`, log shipping fell behind, and every dashboard blamed the application. The kernel was not out of memory at all — it had exhausted a **per-protocol, page-counted accounting limit** that has almost nothing to do with how much RAM the machine has left.

That limit is `net.ipv4.tcp_mem`, and the way it is set, counted and confused with `net.core.rmem_max` is one of the most reliable sources of multi-hour outages in self-hosted infrastructure.

## TL;DR — What To Do When Sockets Get Refused

- **`tcp_mem` is measured in 4 KB pages, not bytes, and it is sum across every TCP socket.** On this 27.7 GB host the default is `330804 441075 661608` pages — 1.29 GB, 1.72 GB and 2.58 GB respectively, i.e. roughly 4.7%, 6.2% and 9.3% of RAM.
- **The third number is a hard wall.** Above it, the kernel refuses to grow socket buffers and logs `TCP: out of memory -- consider tuning tcp_mem`. Free pages elsewhere are irrelevant; accounting is against the limit, not against `MemAvailable`.
- **The usual culprit is per-socket buffer autotuning multiplied by socket count**, not a single fat connection. A thousand sockets each allowed a 2.6 MB send buffer is 2.6 GB of accounted memory — more than the default ceiling.
- **Fix the leak before the number.** Orphaned sockets stuck in `CLOSE-WAIT`/`FIN-WAIT-2`, or an application that never reads its receive queue, will refill any ceiling you set.
- **Do not touch `net.core.rmem_max` expecting to change `tcp_mem` behaviour.** They are different layers: `rmem_max` is a per-socket ceiling chosen by the application, `tcp_mem` is a global protocol-wide budget chosen by the kernel.

## Reading the Three Watermarks

```console
$ sysctl net.ipv4.tcp_mem net.ipv4.tcp_rmem net.ipv4.tcp_wmem
net.ipv4.tcp_mem = 330804	441075	661608
net.ipv4.tcp_rmem = 4096	131072	33554432
net.ipv4.tcp_wmem = 4096	16384	4194304
$ getconf PAGE_SIZE
4096
```

The kernel computes `tcp_mem` at boot from a fraction of physical memory, then keeps it fixed. Converting the three values into something a human can reason about:

| Watermark | Pages | Bytes | ≈ Size | What crossing it does |
|---|---|---|---|---|
| Low | 330,804 | 1,354,973,184 | **1.29 GB** | Below this the kernel does not care; buffers are free to grow |
| Pressure | 441,075 | 1,806,643,200 | **1.72 GB** | Enters *memory pressure* mode: buffer autotuning stops growing, receive queues get pruned defensively |
| Max | 661,608 | 2,709,946,368 | **2.58 GB** | **Hard refusal.** No new allocations; `TCP: out of memory` is logged; new connections may fail |

Three properties follow from that table and they explain nearly every confusing symptom:

1. **Crossing "pressure" degrades silently.** Autotuning freezes at the current window size, so throughput on long-fat-path connections quietly plateaus. Nothing is logged. This is the stage where you notice "the transfer is stuck at 40 Mbit" and find nothing in the logs.
2. **Crossing "max" fails loudly but late.** By the time you see the message, accepted sockets are already being starved.
3. **The budget is shared by every socket on the host.** One noisy neighbour — a backup job with 200 parallel streams, a metrics agent fanning out to 5,000 endpoints — spends the budget for every other service too.

## The Real Numbers From This Host

Right now this machine is nearly idle, which makes the accounting visible:

```console
$ cat /proc/net/sockstat
sockets: used 1432
TCP: inuse 58 orphan 0 tw 6 alloc 72 mem 0
UDP: inuse 43 mem 1612
UDPLITE: inuse 0
RAW: inuse 0
FRAG: inuse 0 memory 0
```

`sockstat`'s `mem` field is **in pages**, and it is the number compared against `tcp_mem`. Zero pages means nothing is queued. Note that during an incident this same field is the fastest possible signal: if `mem` is within a few percent of the *low* watermark, you are already in pressure mode.

Per-socket detail comes from `ss -m`, which exposes the kernel's `skmem` accounting:

```console
$ ss -tmi | sed -n '1,8p'
State      Recv-Q Send-Q   Local Address:Port        Peer Address:Port
ESTAB      0      0        192.168.3.7:microsoft-ds   192.168.3.25:63876
	 skmem:(r0,rb1223762,t0,tb2245632,f0,w0,o0,bl0,d16265) cubic ...
ESTAB      0      0        198.18.0.1:37222         198.18.1.198:https
	 skmem:(r0,rb218543,t0,tb2626560,f0,w0,o0,bl0,d0) cubic ...
CLOSE-WAIT 25     0        198.18.0.1:40622         198.18.10.47:https
	 skmem:(r984,rb131072,t0,tb2626560,f3112,w0,o0,bl0,d0) cubic ...
```

| Field | Meaning | Why you care |
|---|---|---|
| `r` / `t` | Bytes currently queued in receive / transmit | The only fields that consume the `tcp_mem` budget |
| `rb` / `tb` | Allocated receive / transmit buffer size | **This is the accounting charge**, even when empty |
| `f` | Socket "forward" allocation (kernel overhead) | Adds up across thousands of sockets |
| `w` | Bytes waiting for the socket lock | Non-zero = contention, often a single hot listener |
| `o` | Out-of-order queue bytes | Non-zero with `TCPOFOQueue` climbing = packet reordering or loss |
| `d` | Drops on this socket | Rising `d` with `Recv-Q` pinned = application not reading |

That second socket is the whole story in one line: `tb2626560` — a **2.6 MB transmit buffer** allocated for an HTTPS connection. It is not in use (`t0`), but it is charged. Multiply by the number of concurrent connections and you get the budget.

Here is the arithmetic that catches people: **1,024 sockets × 2.6 MB = 2.66 GB**, which exceeds this host's 2.58 GB ceiling — while `MemAvailable` reads 11 GB. The kernel will refuse to grow buffers, log `TCP: out of memory`, and the machine will look completely healthy in every memory graph.

For comparison, the same host's cumulative counters tell you whether it has actually happened:

```console
$ nstat -az | grep -E "PruneCalled|TCPMemoryPressures|TCPAbortOnMemory|TCPRcvCollapsed|TCPOFOQueue"
TcpExtPruneCalled               1514               0.0
TcpExtTCPRcvCollapsed           26898              0.0
TcpExtTCPAbortOnMemory          0                  0.0
TcpExtTCPMemoryPressures        0                  0.0
TcpExtTCPOFOQueue               2722200            0.0
```

`TCPMemoryPressures = 0` means the global wall was never hit here. `PruneCalled = 1514` and `TCPRcvCollapsed = 26898` mean the *per-socket* pruning path ran — the receive queue was collapsed because the application was not draining it fast enough. **These are two different problems with similar names**, and conflating them sends you tuning the wrong knob for days:

| Counter | Raised by | Fix |
|---|---|---|
| `TcpExtTCPMemoryPressures` | Host-wide TCP budget crossed | Raise `tcp_mem`, reduce socket count or per-socket buffers |
| `TcpExtPruneCalled` | One socket's receive queue too full | Make the application read faster; check `Recv-Q` in `ss` |
| `TcpExtTCPAbortOnMemory` | Socket killed for exceeding its own limit | Look for `SO_RCVBUF` misuse or an unbounded queue |
| `TcpExtTCPOFOQueue` | Reordering / loss on the path | Nothing to tune on the host — see the packet-loss path |

## The Four Real Causes of `tcp_mem` Pressure

**1. Orphaned sockets.** When an application closes a socket without reading the remaining data, or a proxy dies mid-transfer, the socket lingers in `FIN-WAIT-2` or `CLOSE-WAIT` holding its buffers. `net.ipv4.tcp_max_orphans = 131072` on this host means up to 131,072 orphans are tolerated — that is a lot of leaked memory before the kernel intervenes. `ss -tan state close-wait` is the single highest-value command in this entire article; a `CLOSE-WAIT` count that only grows is a leak, and no sysctl will save you.

**2. Buffer autotuning with many concurrent connections.** `net.ipv4.tcp_wmem = 4096 16384 4194304` lets any single socket grow its send buffer to 4 MB, and `tcp_rmem` allows 32 MB of receive buffer. Both are per-socket and both count against `tcp_mem`. A service that keeps 500 connections to a slow upstream can legitimately claim gigabytes.

**3. Receive-side backpressure.** A consumer that cannot keep up causes the receive queue to fill, the window to shrink to zero, and the queue to be collapsed — all of which keep memory charged to the socket for as long as the connection lives.

**4. Container and namespace multiplication.** `/proc/net/sockstat` is **per network namespace**. A host with forty containers, each in its own netns, has forty TCP budgets that the host-level `sysctl` does not describe. If a container refuses connections, look inside its namespace:

```console
$ nsenter -t $(docker inspect -f '{{.State.Pid}}' myservice) -n cat /proc/net/sockstat
TCP: inuse 812 orphan 3 tw 240 alloc 818 mem 391204
```

391,204 pages is 1.53 GB inside a container whose limit may still be the host's default.

## Tuning It Without Making Things Worse

The correct order is: prove the cause, fix the app, then raise the ceiling. Here is the drop-in for the last step:

```ini
# /etc/sysctl.d/99-tcp-memory.conf
# Raise the global TCP budget for a host that legitimately holds
# thousands of concurrent connections (reverse proxy, log shipper,
# storage gateway). Values are in 4 KB pages.
net.ipv4.tcp_mem = 262144 524288 1048576

# Cap per-socket growth so a single connection cannot eat the budget.
# 16 MB max receive / 8 MB max send is generous for LAN and WAN alike.
net.ipv4.tcp_rmem = 4096 262144 16777216
net.ipv4.tcp_wmem = 4096 65536 8388608

# Give the kernel a ceiling for the socket-level overrides apps request.
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
```

Those `tcp_mem` values are 1 GB / 2 GB / 4 GB — a 55% increase over the default ceiling, enough for roughly 1,500 sockets at the new 8 MB send-buffer cap. Verify:

```console
$ sudo sysctl --system >/dev/null && sysctl net.ipv4.tcp_mem
net.ipv4.tcp_mem = 262144	524288	1048576
$ for v in $(sysctl -n net.ipv4.tcp_mem); do echo "$v pages = $((v*4/1024)) MB"; done
262144 pages = 1024 MB
524288 pages = 2048 MB
1048576 pages = 4096 MB
```

Two rules keep this safe. **Never set `tcp_mem` max above ~20% of RAM** — a TCP budget that large lets the protocol stack starve the page cache before the OOM killer is even a factor. And **never raise `tcp_mem` without also capping `tcp_rmem`/`tcp_wmem`**, or you have simply moved the wall further out while leaving the per-socket growth unbounded.

## Decision Matrix

| Symptom | Most likely cause | Action |
|---|---|---|
| `TCP: out of memory` in `dmesg`, `MemAvailable` high | Global TCP budget exhausted | Raise `tcp_mem` **and** cap `tcp_rmem`/`tcp_wmem` |
| Throughput plateaus, nothing in logs | Pressure mode — autotuning frozen | Check `sockstat` `mem` vs the low watermark |
| `CLOSE-WAIT` count climbing steadily | Application or proxy not closing sockets | Fix the app; `tcp_max_orphans` only delays it |
| `Recv-Q` pinned on one socket | Consumer too slow | Scale the consumer; `PruneCalled` will confirm it |
| Connections refused inside one container only | Per-netns budget | `nsenter` into the netns and inspect `sockstat` |
| `SYN-SENT` piling up, few established | Not `tcp_mem` at all | Check backlog and filtering — see the queue guide below |

## Pitfalls

- **`tcp_mem` is in pages, everywhere, always.** A value of `661608` is 2.58 GB on 4 KB pages, not 661 KB. Reading it as bytes leads to "my limit is 646 KB, that can't be right" and an hour of confusion.
- **`net.core.rmem_max` does not gate `tcp_rmem`'s third value.** They interact only when an application calls `setsockopt(SO_RCVBUF)`: the kernel clamps to `rmem_max`. Autotuning uses `tcp_rmem` regardless, which is why raising `rmem_max` alone changes nothing.
- **Lowering `tcp_mem` on a busy host causes an immediate incident.** The kernel does not shrink existing buffers to fit; it just refuses the next allocation. Change it in a maintenance window, not during a slowdown.
- **`sockstat` is per namespace, and `mem` is not a total.** Sum across namespaces if you want the host-wide figure — `for ns in /var/run/netns/*; do ip netns exec ... done` or read each container's `sockstat`.
- **IPv6 has its own accounting.** `TCP6` in `sockstat6` is counted separately, and a dual-stack service can exhaust one while the other looks fine.
- **`TCPOFOQueue` climbing is not a memory problem.** It is packet reordering or loss; tuning `tcp_mem` will not move it, but the [packet loss diagnosis walkthrough](../2026-11-22-packet-loss-diagnosis-softnet-dropwatch-nic-to-socket/) will.
- **`tcp_notsent_lowat` interacts with send-buffer pressure.** This host has it at `4294967295` (effectively "queue everything"), which maximises the chance a slow peer keeps a full send buffer charged. Setting a few hundred kilobytes is a cheap win for proxies and log shippers.

If your symptom is not memory pressure but *connection acceptance* — `SYN` retries, `ListenDrops`, `accept queue overflow` — the [listen backlog and accept queue guide](../2026-11-23-listen-backlog-accept-queue-overflow-diagnosis/) covers that failure mode, and if you are running out of ephemeral ports instead, read the [TIME_WAIT port exhaustion diagnosis](../2026-11-22-time-wait-port-exhaustion-diagnosis/). Both produce failures that look like `tcp_mem` pressure when read from a dashboard, and neither is fixed by sysctl tuning.

## FAQ

**Why does the kernel say "out of memory" when `free -h` shows plenty?**
Because `tcp_mem` is not a measure of physical memory availability. It is a fixed budget the kernel reserves for TCP socket buffers, computed at boot as a fraction of RAM. Accounting is against that budget, so a host with 11 GB available can still refuse to grow a socket buffer.

**What are the three numbers in `tcp_mem`?**
Low, pressure and max, in 4 KB pages. Below low nothing happens. Above pressure the kernel stops autotuning buffer growth and prunes defensively while logging nothing. Above max it refuses new allocations and logs `TCP: out of memory -- consider tuning tcp_mem`.

**Is `tcp_mem` shared across containers?**
No — it is per network namespace, and it is initialised from the host value when the namespace is created. A container can exhaust its own budget while the host is idle, so always inspect `/proc/net/sockstat` inside the namespace.

**Should I raise `tcp_mem` or `tcp_rmem`?**
Both, in that order of importance. `tcp_mem` is the wall you are hitting; `tcp_rmem`/`tcp_wmem` determine how fast any single socket consumes it. Raising only the ceiling lets one socket take a larger share of a larger budget.

**How do I see which sockets are consuming the budget right now?**
`ss -tmi` prints per-socket `skmem` accounting including allocated buffer sizes. Sort by the `tb`/`rb` values to find the top consumers, then check whether those bytes are actually queued (`t`/`r`) or just allocated and idle.

**Does raising `tcp_mem` to a huge value fix slow transfers?**
No. Slow transfers with no logs are usually the *pressure* watermark freezing autotuning, or receive-side backpressure from a slow consumer. A larger budget helps only if `TCPMemoryPressures` is actually incrementing.

**What is a safe upper bound for `tcp_mem` max?**
Keep it under roughly 20% of physical RAM. Beyond that the TCP stack can consume memory the page cache and other subsystems need, and you trade a clean `out of memory` log line for system-wide reclaim stalls.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "tcp_mem in 2026: Why Linux Refuses New Sockets With 11 GB of RAM Free",
  "description": "Kernel TCP memory accounting explained with real sockstat, skmem and nstat counters, plus the safe way to raise tcp_mem and cap per-socket buffers.",
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
