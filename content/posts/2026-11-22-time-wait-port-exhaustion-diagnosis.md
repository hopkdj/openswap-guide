---
title: "TIME_WAIT Storms in 2026: Why Your Service Runs Out of Ports and What Actually Fixes It"
date: "2026-11-22"
description: "Cannot assign requested address, 28k ephemeral ports, 60 seconds of TIME_WAIT and a CPU that is 4% busy. A practical diagnosis guide covering ss, nstat, tcp_tw_reuse, connection pooling and the sysctls that do nothing."
tags: ["networking", "linux", "tcp", "performance", "troubleshooting", "kubernetes"]
draft: false
---

It is 02:14 and your service starts throwing `connect: cannot assign requested address`. CPU is at 4%, memory is fine, the database is healthy, and the network team swears nothing changed. The host has 28,232 ephemeral ports configured and you are not running anywhere near that many concurrent connections. What ran out is not ports — it is **ports that are still in `TIME_WAIT`**, and each one is held for a full 60 seconds after the connection closes.

This failure mode is a rite of passage for anyone operating a service that opens short-lived TCP connections: HTTP clients without keep-alive, database drivers that reconnect per query, sidecars that dial a new upstream per request, and load balancers doing SNAT without a large enough port pool. It is also surrounded by more folklore than almost any other Linux tuning problem — `tcp_fin_timeout` does not do what the blog posts say, `tcp_tw_recycle` no longer exists, and raising `net.ipv4.ip_local_port_range` buys you less than you think.

Here is how to confirm the diagnosis in under a minute, and how to fix the cause instead of raising a limit.

## TL;DR — Quick Verdict

- **Diagnose first:** `ss -s` shows the `timewait` count; `ss -tan state time-wait '( dport = :5432 )'` proves it is concentrated on one destination. If `timewait` is in the tens of thousands, that is your outage.
- **The real fix is connection reuse.** Enable HTTP keep-alive, use a connection pool or PgBouncer, and stop dialing per request. Everything else is a mitigation.
- **`tcp_tw_reuse = 1`** is the one sysctl worth setting for outbound-heavy clients (Linux defaults to `2`, which only helps loopback). It requires TCP timestamps, which are on by default.
- **Do not** set `tcp_tw_recycle` — it was removed in Linux 4.12 because it breaks clients behind NAT. Do not expect `tcp_fin_timeout` to shorten `TIME_WAIT`; it governs `FIN_WAIT_2` only.
- **Ceiling maths:** with a 60-second `TIME_WAIT` and ~28k ports, a single client IP can sustain roughly **470 new connections per second to one destination**. Above that, you need pooling, more source IPs, or IPv6.

## What TIME_WAIT Is Actually For

`TIME_WAIT` is not a leak and not a bug. It exists to solve two problems in a protocol that has no connection identifiers beyond the 4-tuple:

1. **The final ACK might be lost.** If the client sends the last `ACK` and it disappears, the server retransmits its `FIN`. If the client had already forgotten the connection and a new connection reused the same 4-tuple, that retransmitted `FIN` would kill the new connection. Staying in `TIME_WAIT` for 2×MSL lets the old segments drain.
2. **Delayed duplicates must expire.** Segments from the previous incarnation of a 4-tuple can still be in flight. `TIME_WAIT` guarantees the old incarnation is gone before the tuple is reused.

On Linux this is hard-coded: `TCP_TIMEWAIT_LEN` is **60 seconds**, defined in the kernel source, and it is *not* controlled by `net.ipv4.tcp_fin_timeout`. That sysctl (default 60) controls how long a socket stays in `FIN_WAIT_2` waiting for the peer's `FIN`. Two different states, two different timers, one very persistent myth.

The consequence is a rate limit that surprises people. A connection is identified by `(source IP, source port, destination IP, destination port)`. The ephemeral port range defaults to `32768-60999`, which is 28,232 ports. Each closed connection holds its port for 60 seconds. Therefore:

```text
max new connections/sec to one destination ≈ 28,232 / 60 ≈ 470
```

That number does not care that your CPU is idle. A service doing 800 short-lived queries per second to one database will exhaust its port space in under a minute, every minute, forever.

## The Diagnostic Sequence That Takes Under a Minute

Start with the aggregate counters:

```bash
ss -s
```

```text
Total: 8432
TCP:   8104 (estab 412, closed 128, orphaned 3, timewait 7412, ...)
```

`timewait 7412` is the number that matters. On a client with a healthy pool it should be in the tens or low hundreds; on a client with an affinity for short-lived connections it can exceed 20,000.

Then localise it. `TIME_WAIT` sockets are almost always concentrated on the one destination you talk to most:

```bash
ss -tan state time-wait | awk '{print $4}' | cut -d: -f1 | sort | uniq -c | sort -rn | head
```

```bash
# Count by remote endpoint, which is the useful grouping
ss -tan state time-wait '( dport = :5432 )' | wc -l

# Kernel-level TCP extended counters, including reuse and PAWS events
nstat -az | grep -Ei 'timewait|twreuse|paws'
```

```text
TcpExtTW                    18422    0.0
TcpExtTWRecycled                0    0.0
TcpExtTWKilled                  0    0.0
TcpExtPAWSEstab                12    0.0
TcpExtTCPTimeouts             812    0.0
PAWSEstab means timestamps rejected segments — a signal that some middlebox is rewriting or stripping timestamp options, which also breaks tcp_tw_reuse. `TcpExtTWKilled` climbing means `tcp_max_tw_buckets` was hit and the kernel destroyed `TIME_WAIT` sockets early; that removes the protection and usually logs `TCP: time wait bucket table overflow`.

Confirm the local port range and whether reuse is enabled:

```bash
cat /proc/sys/net/ipv4/ip_local_port_range   # 32768  60999
cat /proc/sys/net/ipv4/tcp_tw_reuse          # 2 (default: loopback only)
cat /proc/sys/net/ipv4/tcp_max_tw_buckets    # e.g. 131072
```

One more check that separates a real port problem from a file descriptor problem: if `ss` shows thousands of sockets but `ulimit -n` is exhausted, the error message is usually `Too many open files`, not `cannot assign requested address`. Different resource, different fix. `EADDRNOTAVAIL` on `connect()` is ports.

## The Sysctls: One That Helps, Two That Do Nothing, One That Is Gone

| Setting | What people expect | What it actually does | Verdict |
|---|---|---|---|
| `net.ipv4.tcp_tw_reuse = 1` | Recycle `TIME_WAIT` sockets instantly | Allows an **outbound** `connect()` to reuse a `TIME_WAIT` 4-tuple when TCP timestamps prove it is safe. Default `2` = loopback only (since 4.12) | **Set it to 1** on outbound-heavy clients |
| `net.ipv4.tcp_fin_timeout` | Shorten `TIME_WAIT` from 60s | Governs `FIN_WAIT_2` duration only. `TIME_WAIT` is a kernel constant | **No effect** on this problem |
| `net.ipv4.tcp_max_tw_buckets` | Raise the ceiling | Caps simultaneous `TIME_WAIT` sockets; over the cap they are destroyed early (unsafe, logs overflow) | Do not tune unless you understand the trade |
| `net.ipv4.tcp_tw_recycle` | Aggressive recycling | **Removed in Linux 4.12.** Broke NAT clients because it required monotonic timestamps per host | **Does not exist** — do not copy old guides |
| `net.ipv4.ip_local_port_range` | More ports | Widens the range toward lower ports; can collide with services that bind low ports | Small help, real risk |
| `SO_REUSEADDR` | Reuse ports | Lets a **listener** bind while old connections sit in `TIME_WAIT`. Does nothing for outbound connections | Server-side only |

Two of these deserve expansion because they are where most tuning attempts go wrong.

**`tcp_tw_reuse` is safe, narrow, and helpful.** It only applies to outgoing connections, it requires TCP timestamps (`net.ipv4.tcp_timestamps = 1`, the default), and the kernel still refuses to reuse a tuple if the timestamp of the new connection would be lower than the previous one — the PAWS check that prevents old duplicates from being accepted. Set it deliberately:

```bash
sysctl -w net.ipv4.tcp_tw_reuse=1
echo 'net.ipv4.tcp_tw_reuse = 1' > /etc/sysctl.d/99-tcp-tw-reuse.conf
sysctl --system
```

One caveat that catches people in containerised environments: **sysctls in `net.ipv4` are per network namespace**. Setting `tcp_tw_reuse` inside a pod affects only that pod's namespace (and some are not namespaced at all, which is why `kubectl` refuses to set them without `--allowed-unsafe-sysctls`). If your sidecar has the problem, tune the sidecar's namespace or the host, not the pod you happen to `exec` into.

**`tcp_max_tw_buckets` is a trap.** Raising it lets you accumulate more sockets in `TIME_WAIT` — which does nothing for the exhaustion problem, because the port range is still finite. Lowering it destroys `TIME_WAIT` sockets early, which reintroduces exactly the protocol hazard `TIME_WAIT` was designed to prevent, and the kernel logs an overflow warning. Leave it alone unless you have a specific, measured reason.

## The Fix That Actually Works: Reuse Connections

Every real solution reduces the number of connections created per second. The sysctls only change the ceiling; pooling changes the demand.

**HTTP clients.** HTTP/1.1 keep-alive is the default *on the wire*, but most client libraries do not pool aggressively unless told to. Two notorious defaults:

- **Go's `http.Transport` uses `MaxIdleConnsPerHost = 2` by default.** A service making 50 concurrent requests per host will open and close connections constantly, generating exactly the `TIME_WAIT` storm you are debugging. Raise it.
- **Node's `http.globalAgent` had `keepAlive: false` by default before Node 19**; if you are on an older runtime, or you construct `new http.Agent()` explicitly, you are disabling reuse.

```go
// Go: reuse connections instead of dialing per request
tr := &http.Transport{
    MaxIdleConns:        256,
    MaxIdleConnsPerHost: 64, // the default of 2 is the usual culprit
    IdleConnTimeout:     90 * time.Second,
    ForceAttemptHTTP2:   true,
}
client := &http.Client{Transport: tr, Timeout: 10 * time.Second}
```

```javascript
// Node: explicit agent with keep-alive (needed on older runtimes)
const http = require('node:http');
// Explicit agent with keep-alive (required on runtimes older than Node 19)
const agent = new http.Agent({ keepAlive: true, maxSockets: 64, keepAliveMsecs: 30000 });
const req = http.request({ host: 'api.internal', port: 80, path: '/items', agent }, res => {
  res.resume();
});
```

**Python's `requests` without a `Session`** opens a new TCP connection per call. That is the single most common cause of `TIME_WAIT` exhaustion in data pipelines:

```python
import requests

# Bad: new connection per call, one TIME_WAIT per call
# requests.get("https://api.internal/items")

# Good: session reuses the connection pool
session = requests.Session()
session.mount("https://", requests.adapters.HTTPAdapter(
    pool_connections=32, pool_maxsize=64, max_retries=2))
for _ in range(1000):
    session.get("https://api.internal/items", timeout=5)
```

**Databases.** Each PostgreSQL connection is a process, and each disconnect-and-reconnect cycle costs a port on the client and a fork on the server. Put PgBouncer in transaction mode in front of the database and the connection count becomes a function of concurrency, not of query rate:

```ini
[databases]
app = host=postgres.internal port=5432 dbname=app

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
pool_mode = transaction
max_client_conn = 2000
default_pool_size = 40
server_idle_timeout = 300
```

With `pool_mode = transaction`, 2,000 application workers share 40 server connections, and the client-side `TIME_WAIT` rate collapses because clients hold long-lived connections to the pooler instead of dialing the database. The same logic applies to Redis (use a client-side pool), MySQL (ProxySQL), and gRPC (a single `Channel` per target, reused — never one per request).

**Load balancers doing SNAT.** If the exhaustion is on the balancer rather than the application, it is the same arithmetic with a different port pool. HAProxy, Envoy and IPVS all have a source-port range for masqueraded traffic; when it is exhausted you see `cannot assign requested address` in the balancer log while backends look idle. Fixes: add source IPs (a second address multiplies the port space by one), enable `tcp_tw_reuse` on the balancer host, or switch to a DSR/tunnel mode that does not masquerade. Our [L4 load balancer comparison](../2026-05-11-self-hosted-tcp-l4-load-balancers-gobetween-mixctl-samaritan-guide/) and the [advanced HAProxy/Envoy middleware guide](../2026-05-03-self-hosted-load-balancer-advanced-haproxy-lua-traefik-middleware-envoy-wasm/) cover the connection-handling differences between those data planes.

**Short-lived HTTP/1.0 clients and health checks.** A health check that opens a connection every second from every node is 86,400 connections a day per target, each holding a port for 60 seconds. Configure health checks to reuse connections (HTTP/1.1 with keep-alive) or lengthen the interval. The same applies to cron jobs that shell out to `curl` in a loop.

## Reproducing the Storm in a Lab

You do not need production to prove the mechanism. This loop opens and closes TCP connections as fast as it can and prints the `TIME_WAIT` count:

```bash
# Terminal 1: a listener
nc -lk 127.0.0.1 9000

# Terminal 2: churn connections, closing immediately
for i in $(seq 1 5000); do
  (exec 3<>/dev/tcp/127.0.0.1/9000; exec 3<&-; exec 3>&-) 2>/dev/null
done

# Terminal 3: watch the count climb
watch -n1 "ss -tan state time-wait '( dport = :9000 )' | wc -l"
```

The counter climbs by roughly the connection rate and then decays with a 60-second half-life once you stop. That shape — a sawtooth that only falls when traffic stops — is the signature of the problem. Compare it against the same loop with a persistent connection (`nc` kept open, or a pooled client): the counter stays near zero, because there is nothing to wait for.

To see the actual failure, shrink the port range in a throwaway network namespace so you hit the wall in seconds instead of minutes:

```bash
sudo unshare -n bash
ip link set lo up
sysctl -w net.ipv4.ip_local_port_range="40000 40010"   # 11 ports
# any burst of short-lived connections now fails with EADDRNOTAVAIL
```

That demo is also the fastest way to teach a team why the ceiling is a rate, not a count.

## Five Traps Worth Memorising

1. **Blaming the port range when the problem is per-destination.** 28k ports is the pool *per destination IP and port*. Ten backends mean ten pools. One hot backend means one pool, and 470 conn/s is the wall.
2. **Setting `tcp_fin_timeout` and declaring victory.** It does not touch `TIME_WAIT`; the 60-second hold is `TCP_TIMEWAIT_LEN`. You will have changed nothing except `FIN_WAIT_2` behaviour.
3. **Following pre-2017 guides to `tcp_tw_recycle`.** The knob was removed in 4.12. On modern kernels the write fails, and on kernels where it still exists it breaks every client behind NAT — the classic "works from my laptop, breaks in the office" incident.
4. **Enabling aggressive tuning on the server instead of the client.** `TIME_WAIT` accumulates on the side that closes first. Usually that is your application (the client), not the database. Tune and pool on the side that owns the sockets doing the churn.
5. **Ignoring IPv6 as a second pool.** Each source address has its own port space. Dual-stack clients that also use IPv6 effectively double the ceiling, and extra loopback or VIP addresses multiply it further — a legitimate stopgap while you fix pooling.

## FAQ

### What does "cannot assign requested address" actually mean?

`connect()` returned `EADDRNOTAVAIL` because the kernel could not find a free local ephemeral port for the destination. On a client this almost always means the ephemeral port range is fully occupied by sockets in `TIME_WAIT` (or by live connections). It is a different failure from `Too many open files`, which is the file-descriptor limit, and from `Connection refused`, which means nothing is listening.

### Does tcp_fin_timeout reduce TIME_WAIT?

No. `net.ipv4.tcp_fin_timeout` controls how long a socket waits in `FIN_WAIT_2` for the peer's `FIN`. `TIME_WAIT` duration is a kernel constant (`TCP_TIMEWAIT_LEN`, 60 seconds on Linux) and cannot be tuned with sysctl. The only ways to reduce the impact are to create fewer connections, reuse tuples with `tcp_tw_reuse`, or add more source addresses.

### Is tcp_tw_reuse safe in production?

For outbound connections, yes — it is designed for exactly this case and is enabled by default for loopback on modern kernels (`= 2`). It still respects TCP timestamps and PAWS, so it will not accept stale duplicate segments. It does nothing for inbound connections or for a server sitting on a fixed port, and it requires timestamps to be enabled on both ends.

### How many connections per second can one host make to a single backend?

With the default range of 32,768-60,999 (28,232 ports) and a 60-second `TIME_WAIT`, roughly **470 new connections per second** to one destination. Under that rate you are fine; above it you accumulate `TIME_WAIT` faster than it drains and eventually fail. Widening `ip_local_port_range` to 10,000-65,535 raises the ceiling to about 925/s, but pooling is the better answer.

### Why does the TIME_WAIT count explode in Kubernetes but not on a VM?

Because of how workloads are packaged: sidecars that dial per request, health probes that open a socket every second, and client libraries with tiny idle-connection pools. All of that is multiplied by pod churn, and each pod has its own ephemeral port range but shares the backend's capacity. Check `ss -s` inside the pod first, then look at the sidecar's connection settings.

### Do HTTP/2 and gRPC help?

Yes, substantially. Both multiplex many requests over a single TCP connection, so the connection count stops tracking the request rate. A gRPC client that creates one `Channel` per target and reuses it will make a handful of connections instead of thousands. The failure mode only returns if code creates a channel or HTTP/2 client per request — which is common in naive retry wrappers. For the transport-level tuning that shapes those connections, our [TCP congestion control guide](../2026-05-21-self-hosted-tcp-congestion-control-bbr-cubic-fq-codel-guide/) covers the kernel-side parameters that interact with them.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TIME_WAIT Storms in 2026: Why Your Service Runs Out of Ports and What Actually Fixes It",
  "description": "Cannot assign requested address, 28k ephemeral ports, 60 seconds of TIME_WAIT and a CPU that is 4% busy. A practical diagnosis guide covering ss, nstat, tcp_tw_reuse, connection pooling and the sysctls that do nothing.",
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
