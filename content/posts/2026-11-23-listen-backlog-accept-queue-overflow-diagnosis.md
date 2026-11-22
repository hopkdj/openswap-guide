---
title: "Listen Backlog Overflow: Why Connections Time Out While Your Server Sits Idle"
date: "2026-11-23"
tags: ["linux", "networking", "troubleshooting", "nginx", "performance"]
draft: false
description: "Your CPU is idle, your app is healthy, and clients still time out. A practical guide to the two TCP accept queues, somaxconn, and the counters that prove overflow."
---

A client reports intermittent timeouts. You check the box: load average 0.4, CPU 3%, memory fine, application logs full of successful requests, zero errors. The reverse proxy says upstream responded in 12ms. And yet a small, consistent slice of connections never completes — no 502, no 503, just nothing until the client gives up.

If that describes your incident, the culprit is almost never resource starvation. It is one of **two kernel queues that sit between the network card and your `accept()` call**, and both are *silent* by default: when the accept queue overflows, Linux drops the final ACK of the handshake and says nothing to the client. The client retransmits, waits, and eventually times out — while your server reports that it is perfectly idle. It is, in a sense, telling the truth.

Here is what the queues look like on the host that produced this article:

```console
$ sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog net.ipv4.tcp_abort_on_overflow net.ipv4.tcp_syncookies
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_abort_on_overflow = 0
net.ipv4.tcp_syncookies = 1

$ ss -lnt | head -6
State  Recv-Q Send-Q      Local Address:Port
LISTEN 0      200             127.0.0.1:5432
LISTEN 0      2048                0.0.0.0:8090
LISTEN 0      4096              192.168.3.7:443
LISTEN 0      128             127.0.0.1:7001
LISTEN 0      4096           127.0.0.53%lo:53
```

Every one of those `Send-Q` values is a **different application's idea of how many pending connections it can tolerate** — 200 for the database, 2,048 for a Python service, 4,096 for the Caddy listener that simply inherited `somaxconn`. Nothing on this host is tuned consistently, which is the normal state of the world.

## TL;DR — The Two Queues and the One Column That Matters

- **`Send-Q` on a LISTEN socket is not a queue depth. It is the backlog ceiling** — the value passed to `listen()`, clamped by `net.core.somaxconn`.
- **`Recv-Q` on a LISTEN socket is the live accept-queue depth** — fully handshaked connections your application has not `accept()`ed yet. If `Recv-Q` sits at `Send-Q`, your accept queue is full and clients are being timed out right now.
- **Two overflow counters prove it after the fact:** `TcpExtListenOverflows` and `TcpExtListenDrops` (visible via `nstat -az` or `netstat -s`).
- **Fix the accept rate first, the backlog second.** Raising `somaxconn` on a server whose app accepts 50 connections/second under a 5,000/second flood just makes the queue a bigger coffin.
- **Set `net.ipv4.tcp_abort_on_overflow=1` in staging only** — it converts silent timeouts into immediate resets, which makes the problem visible without waiting for a client complaint.

## The Two Queues, Visualized

Most guides blur these together. They are separate, they have separate limits, and they fail with separate counters.

| Queue | What sits in it | Bound by | Overflow counter | Client experience |
|---|---|---|---|---|
| **SYN queue** (incomplete) | Half-open connections: SYN received, final ACK not yet | `net.ipv4.tcp_max_syn_backlog` | `TcpExtTCPReqQFullDrop` (syncookies off) or `TcpExtSyncookiesSent` | Slower connect under SYN flood |
| **Accept queue** (completed) | Handshake finished, waiting for `accept()` | `min(app_backlog, net.core.somaxconn)` | `TcpExtListenOverflows`, `TcpExtListenDrops` | **Silent timeout**, no error either side |
| **NIC ring** | Frames not yet picked up by the driver | `ethtool -G rx` | `rx_dropped` / `rx_fifo_errors` | Retransmits, jitter |
| **Softnet backlog** | Frames queued for the network stack | `net.core.netdev_max_backlog` | `softnet_stat` column 2 | Retransmits, uneven latency |

Only the accept queue produces the classic "idle server, timing-out client" signature — because the kernel's response to a full accept queue (with `tcp_abort_on_overflow=0`) is to **drop the ACK and rely on the client's retransmission timer**. That is not a bug; it is a deliberate design that assumes the application will catch up within a retransmit interval or two. When it does not, the client sees a 1s/3s/7s backoff and then a timeout.

## Proving It Happened: The Counters

Run this first. It answers the question in one shot, without touching production config:

```bash
nstat -az | grep -iE "ListenOverflows|ListenDrops|ReqQFull|SyncookiesSent|DeferAccept"
```

Real output from this host:

```console
TcpExtListenOverflows           0     0.0
TcpExtListenDrops               0     0.0
TcpExtTCPReqQFullDrop           0     0.0
TcpExtSyncookiesSent            0     0.0
TcpExtTCPDeferAcceptDrop    81009     0.0
TcpExtTCPFastOpenListenOverflow 0     0.0
```

Interpretation matters more than the numbers:

- **`ListenOverflows = 0`** means the accept queue never filled on this host. Good — but this is a quiet box. On a busy one, any non-zero value that keeps climbing with traffic is proof of overflow.
- **`TCPDeferAcceptDrop = 81,009`** is the interesting one. `TCP_DEFER_ACCEPT` makes the kernel wait for the first byte of data before waking the application; connections that handshake but never send data (health probes, port scanners, load-balancer checks that connect and immediately close) get dropped and counted here. It looks alarming and is usually benign — but a sharp rise in this counter alongside rising `ListenOverflows` means your accept loop is being woken constantly by junk connections and starved of time for real ones.

Rate-based reading is what you want. `nstat` shows per-second deltas when run without `-a`:

```bash
# 10-second observation of listen-queue behaviour
nstat -n -i 10 >/dev/null 2>&1; sleep 10; nstat | grep -iE "Listen|ReqQFull"
```

## The Clamp That Confuses Everyone

The backlog you configure in your application is a **request, not a guarantee**. Since Linux 4.x the kernel uses:

```
effective_backlog = min(backlog_argument, net.core.somaxconn)
```

So with `somaxconn = 4096` (this host), Caddy listening with a 4096 request gets 4096. But raise `somaxconn` to 65535 and Caddy keeps accepting at 4096 because it passes 4096 to `listen()` — only the `somaxconn` side of the `min()` changed. This is why "I raised somaxconn and nothing happened" is such a common report.

The table below shows the *actual* per-application defaults, which is what you are really living with:

| Service | How backlog is set | Typical effective value |
|---|---|---|
| Caddy | no knob; uses `somaxconn` | 4096 (as observed) |
| nginx | `listen ... backlog=` (default 511) | clamped by `somaxconn` |
| Gunicorn | `--backlog` (default 2048) | 2048 |
| Redis | `tcp-backlog` (default 511) | 511 |
| Node.js `http` | `server.listen({backlog})` (default 511) | 511 |
| Go `net/http` | not configurable; reads `somaxconn` | 4096 |
| systemd socket activation | `Backlog=` (default 4096) | 4096 |
| PostgreSQL | derived internally from connection limits | 200 (as observed) |

Verify rather than assume — `ss` prints the resolved value, not the requested one:

```bash
ss -lntp | grep -E ":(443|5432|8090)\b"
```

## Reading `Recv-Q` Live (The Smoke Test)

If you only take one command from this article, take this one. It distinguishes "queue full" from "app slow" in a single sample:

```bash
# sample accept-queue depth every 0.5s for 5 seconds
for i in $(seq 1 10); do ss -lnt | awk 'NR>1 && $1=="LISTEN" {printf "%s RecvQ=%s SendQ=%s\n", $4, $2, $3}'; sleep 0.5; done
```

Rules of thumb:

- `Recv-Q = 0` always → nothing is queuing; look elsewhere (softnet, qdisc, upstream).
- `Recv-Q` briefly spikes → normal burst absorption; the app is keeping up.
- **`Recv-Q` pinned at `Send-Q`** → accept queue saturated. Each additional connection is dropped after handshake. This is your incident.
- `Recv-Q` grows while `Send-Q` stays large → the ceiling is fine but the app is not accepting fast enough; the next step is profiling the event loop, not increasing the backlog.

The deeper per-socket view includes the drop counters that `ss -lnt` omits:

```bash
ss -lnti | grep -A1 ":443"
# skmem:(r0,rb212992,t0,tb212992,f4096,w0,o0,bl0,d0)
# d0 is drops attributed to the socket buffer
```

## Why the App Is Slow to Accept

Backlog overflow is a symptom. The causes, in rough order of frequency on self-hosted boxes:

1. **Blocking work inside the accept path.** A connection handler that does a synchronous DNS lookup, a Redis `KEYS`, or a `fsync` before returning to `accept()` stalls the whole loop. Every millisecond of that stall is queue growth.
2. **`accept()` in a supervisor that spawns processes.** Process-per-connection designs (PHP-FPM with `pm=dynamic`, some CGI setups) are bounded by process count, not by the socket backlog. The queue fills while `fork()` work is in flight.
3. **Keep-alive starvation.** A high `keepalive_requests` combined with a small worker pool means workers are held by idle keep-alive connections while new connections queue. Lowering `keepalive_timeout` often fixes "random" timeouts that no backlog change ever fixed.
4. **Health-check storms.** Load balancers probing every 2 seconds across many backends can consume a measurable share of the accept queue. `TCPDeferAcceptDrop` counts the ones that connect and send nothing.
5. **Single-threaded event loops doing CPU work.** A JSON serialization of a large payload on the same thread as `epoll_wait` is a queue-growth generator.

## Configuration That Actually Fixes It

**Step 1 — raise the ceiling** (kernel side), sized to what the app can drain:

```ini
# /etc/sysctl.d/99-network-queue.conf
net.core.somaxconn = 16384
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_abort_on_overflow = 0
```

```bash
sysctl --system
```

**Step 2 — raise the application's request** to match, or the clamp eats the change. For nginx:

```nginx
server {
    listen 443 ssl backlog=8192;
    # ...
}
```

For Gunicorn:

```bash
gunicorn app:wsgi --backlog 8192 --workers 8 --keepalive 5
```

For Redis:

```
# redis.conf
tcp-backlog 8192
```

**Step 3 — make overflow visible in staging**, so you never again learn about it from a customer:

```bash
# staging only: turn silent drops into immediate RSTs
sysctl -w net.ipv4.tcp_abort_on_overflow=1
```

With this set, clients get a fast `connection reset` instead of a 30-second timeout. That is a worse user experience and a much better diagnostic — which is exactly the trade you want while tuning, and exactly the trade you do not want in production.

**Step 4 — alarm on the counters, not on latency.** Scrape these and alert on any increase:

```bash
nstat -az TcpExtListenOverflows TcpExtListenDrops
```

A rate of zero is the only acceptable steady state for a healthy listener.

## Pitfalls and Migration Notes

- **`Send-Q` is not "queue is backed up."** On LISTEN sockets it is the backlog value. Reading it as occupancy produces the wrong conclusion 100% of the time.
- **`somaxconn` alone never fixes an app that accepts slowly.** It converts a fast, visible failure into a slow, invisible one.
- **Inside containers, the listener's backlog lives in the container's network namespace**, but `somaxconn` is read from that namespace's sysctls — which may differ from the host's. `docker run --sysctl net.core.somaxconn=8192` is often required, and Kubernetes pods cannot always set it (it is namespaced, but some runtimes reject it) — in that case the host value wins.
- **Userspace proxies add a second queue.** Docker's `docker-proxy` and many CNI plugins terminate connections in userspace and open a *new* connection to the backend with *their own* default backlog. You can tune the backend perfectly and still overflow at the proxy.
- **Syncookies mask SYN-queue overflow but degrade connections.** With `tcp_syncookies=1`, overflowed SYNs are answered with a cookie that cannot carry window-scaling and SACK options; those connections still work but are slower. Watch `TcpExtSyncookiesSent` — a steady non-zero rate means your SYN backlog is too small, not that you are under attack.
- **`systemd` socket activation has its own backlog** (`Backlog=`, default 4096) and it is applied by systemd, not by your app. Tuning the app's `listen()` call has no effect when systemd owns the socket.
- **Enabling `tcp_abort_on_overflow=1` in production trades timeouts for resets.** Some clients and mobile networks retry RSTs poorly; measure before standardizing on it.

## FAQ

**What is the difference between `Recv-Q` and `Send-Q` for a LISTEN socket?**
For listening sockets, `Recv-Q` is the current number of fully-established connections waiting in the accept queue, and `Send-Q` is the maximum backlog configured for that socket. On an established (non-LISTEN) socket the meaning flips back to bytes buffered in each direction.

**Which limit actually caps my backlog — `somaxconn` or what I pass to `listen()`?**
Both, because the kernel takes the smaller of the two: `min(backlog, net.core.somaxconn)`. Raising only `somaxconn` does nothing if the application still requests 511, and raising only the application's value does nothing if `somaxconn` is 128.

**Why do clients time out but the application log shows no errors at all?**
Because with `net.ipv4.tcp_abort_on_overflow=0` the kernel silently discards the handshake's final ACK when the accept queue is full. The application never sees the connection, so it cannot log anything, and the client only notices when its retransmissions exhaust the timeout.

**Which counters prove accept-queue overflow?**
`TcpExtListenOverflows` and `TcpExtListenDrops`, read with `nstat -az`. `TcpExtTCPReqQFullDrop` indicates SYN-queue drops when syncookies are disabled, and `TcpExtTCPDeferAcceptDrop` counts connections dropped for sending no data after the handshake — benign for probes, suspicious when it tracks traffic.

**Is a bigger backlog always better?**
No. A large backlog absorbs bursts, but it also converts an overload into high latency instead of a fast failure, and it hides an accept loop that cannot keep up. Size the backlog from measured peak accept rates, fix the accept path first, and alert on overflow counters so a bigger queue never becomes a silent substitute for capacity.

For the layer beneath this one, see our [packet loss diagnosis walkthrough covering the NIC ring, softnet backlog and socket buffers](../2026-11-22-packet-loss-diagnosis-softnet-dropwatch-nic-to-socket/). If your symptom is connect failures rather than slow handshakes, the [TIME_WAIT and ephemeral port exhaustion guide](../2026-11-22-time-wait-port-exhaustion-diagnosis/) covers the client side, and the broader [sysctl and tuned tuning reference](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/) explains how these values survive reboots. Servers that run out of workers rather than sockets should read our [PID and thread exhaustion field guide](../2026-11-23-pid-thread-exhaustion-fork-storm-diagnosis/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Listen Backlog Overflow: Why Connections Time Out While Your Server Sits Idle",
  "description": "A practical guide to the TCP SYN queue and accept queue, somaxconn clamping, and the counters that prove backlog overflow.",
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
