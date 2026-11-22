---
title: "Your Linux Box Is Dropping Packets Silently: A 2026 Field Guide from NIC to Socket"
date: "2026-11-22"
tags: ["linux", "networking", "performance-tuning", "troubleshooting", "kernel"]
draft: false
description: "A counter-by-counter guide to finding where Linux drops packets: NIC ring buffers, softnet backlog, qdisc queues and socket buffers, with real kernel output."
---

Latency graphs look fine. CPU is idle. Nothing in `dmesg`. And yet requests time out, gRPC calls hit deadline exceeded, and your UDP-based telemetry is missing samples.

Here is a real machine, sitting quietly, with no alerts firing:

```text
$ nstat -az
TcpRetransSegs                  1656295            0.0
TcpExtTCPLostRetransmit         1241523            0.0
UdpRcvbufErrors                 4489733            0.0
IpInDiscards                          0            0.0
```

**4.5 million UDP datagrams were thrown away by the kernel's socket receive buffer**, and 1.24 million retransmissions were themselves lost on the wire. Not one application logged a warning. That is the core problem with packet loss on Linux: the kernel counts every drop in a different file, and almost none of them are on by default in your monitoring.

This guide gives you the exact counter for each of the four places a packet can die, plus the one-line command that proves it.

## TL;DR — Quick Verdict

- **Packet loss is always counted somewhere.** Start with `nstat -az` (protocol layer) and `/proc/net/softnet_stat` (driver layer). If both are clean, the drop is in the socket buffer — check `ss -s` and `UdpRcvbufErrors`.
- **`ifconfig` drop counters are nearly useless.** They miss softnet backlog, qdisc, and socket-level drops, which is where 90% of real losses happen on modern kernels.
- **If `softnet_stat` column 2 grows**, you have a receive-path scheduling problem — fix with RPS or more RSS queues, not with bigger buffers.
- **If `softnet_stat` column 3 grows but column 2 stays at zero**, nothing is lost; the softirq just ran out of budget. That is a latency signal, not a loss signal.
- **For UDP receivers, `rmem_max` is almost always the culprit**, and `SO_RCVBUF` set by the app overrides everything you do in `sysctl`.

## The Four Places a Packet Can Die

Every ingress packet on Linux passes through four queueing stages. Each has its own drop counter, its own tuning knob, and its own failure signature.

| Stage | Where it lives | Counter that proves loss | Knob | Typical symptom |
|---|---|---|---|---|
| NIC ring buffer | Driver / hardware | `ethtool -S <dev>` → `rx_no_buffer_count`, `rx_fifo_errors` | `ethtool -G <dev> rx N` | Bursty traffic, high pps, lost at wire speed |
| Softnet backlog | Per-CPU softirq | `/proc/net/softnet_stat` column 2 | RPS/RFS, more RX queues | One hot CPU, `%soft` pinned at 100 on a single core |
| Qdisc (egress) | Traffic control | `tc -s qdisc show` → `dropped` | `txqueuelen`, fq_codel limits | Upload slower than download, `requeues` climbing |
| Socket receive buffer | TCP/UDP stack | `nstat` → `UdpRcvbufErrors`, `TcpExtTCPRcvCollapsed` | `net.core.rmem_max`, `SO_RCVBUF` | App slow to `read()`, drops scale with burst size |

The ordering matters: a packet dropped in the ring buffer never reaches softnet, and a packet dropped in softnet never reaches your socket. **Always diagnose from the bottom up** — driver first, then softirq, then qdisc, then socket. If you start at the socket layer you will spend hours raising `rmem_max` for a problem that lives in the NIC.

## Stage 1: The NIC Ring Buffer

The ring buffer is a fixed-size DMA region shared between the NIC and the driver. When it fills, the NIC has nowhere to put the next frame and drops it in hardware.

```bash
# Per-queue ring sizes and drop counters (driver dependent)
ethtool -S enp2s0 | grep -iE "drop|no_buffer|fifo|miss|err"
ethtool -g enp2s0                 # current vs maximum ring size
ethtool --show-channels enp2s0    # how many RX/TX queues exist
```

Counter names are driver-specific — `rx_no_buffer_count` on `ixgbe`/`i40e`, `rx_fifo_errors` on `e1000e`, `rx_dropped` in `/proc/net/dev` for generic. What you are looking for is a counter that only moves under load. Snapshot it twice, ten seconds apart, under real traffic:

```bash
ethtool -S enp2s0 | grep rx_no_buffer_count
sleep 10
ethtool -S enp2s0 | grep rx_no_buffer_count
```

If the number moved, raise the ring: `ethtool -G enp2s0 rx 4096`. Two caveats that bite people:

1. **The ring must be raised on every boot.** `ethtool -G` is not persistent — put it in a systemd unit or NetworkManager dispatcher script, or it silently reverts on the next reboot.
2. **A bigger ring hides latency, it does not fix it.** You have added milliseconds of buffering before the kernel even sees the packet. If the ring overflows constantly, the real fix is more RX queues (`ethtool -L`) or RPS.

## Stage 2: Softnet Backlog — the Counter Nobody Reads

`/proc/net/softnet_stat` has one line per CPU and no header, which is why it gets ignored. Here is real output from a 16-core host:

```text
$ cat /proc/net/softnet_stat
062fe3ce 00000000 000000b4 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
0663a206 00000000 000000e4 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000001 00000000 00000000
0708390f 00000000 000000db 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000002 00000000 00000000
```

All values are hexadecimal. The columns you care about:

| Column | Field | Meaning |
|---|---|---|
| 1 | `processed` | Packets handled by this CPU's softirq |
| 2 | `dropped` | **Packets dropped because the backlog was full** |
| 3 | `time_squeeze` | Times `net_rx_action` exhausted its budget with work left |
| 4 | `cpu_collision` | Contention on the per-CPU backlog lock |
| 5 | `received_rps` | Packets redirected here by RPS |
| 13 | `index` | CPU number this line belongs to |

In the sample above, **column 2 is zero on every CPU** — nothing is being dropped. But `time_squeeze` (column 3) is 180, 228 and 219 respectively, which means `net_rx_action` repeatedly hit its time budget with packets still queued. That is not loss; it is *deferred* work, and it shows up as jitter, not as errors.

A quick decoder so you never have to count columns by eye again:

```bash
awk '{printf "cpu%d processed=%d dropped=%d time_squeeze=%d\n", strtonum("0x"$13), strtonum("0x"$1), strtonum("0x"$2), strtonum("0x"$3)}' /proc/net/softnet_stat
```

If column 2 is climbing:

- **One CPU hot, rest idle** → this is the classic single-queue NIC problem. Enable RPS so the softirq work spreads across cores: `echo ffff > /sys/class/net/enp2s0/queues/rx-0/rps_cpus`.
- **All CPUs hot** → you are genuinely out of packet-processing capacity. Add RX queues with `ethtool -L enp2s0 combined N`, and check whether `%soft` in `mpstat -P ALL 1` is saturated.

## Stage 3: The Qdisc — Drops on the Way Out

Ingress gets the attention, but egress drops are more common than people expect because they are invisible to the receiver's retransmit counters.

```text
$ tc -s qdisc show dev enp2s0
qdisc mq 0: dev enp2s0 root
 Sent 238069761384 bytes 534770667 pkt (dropped 3, overlimits 0 requeues 2819540)
 backlog 0b 0p requeues 2819540
qdisc fq_codel 0: dev enp2s0 parent :4 limit 10240p flows 1024 quantum 1514 target 5ms interval 100ms memory_limit 32Mb ecn drop_batch 64
 Sent 24719826232 bytes 88526825 pkt (dropped 1, overlimits 0 requeues 81076)
```

Two numbers matter here, and they mean opposite things:

- **`dropped`** — packets the qdisc discarded because the queue was full. Real loss, and the sender will retransmit.
- **`requeues`** — the driver could not take the packet because the device TX ring was full, so it was put back. **2.8 million requeues on the root `mq` qdisc is a strong signal that the transmit ring is undersized or the link is genuinely saturated.** Requeues are not loss, but they add queueing delay that TCP reads as congestion.

If `dropped` is climbing on `fq_codel`, do not simply raise `limit`. Check whether you have a bulk flow starving everything else: `tc -s qdisc show` per-flow accounting plus `ss -tin` will show a single socket holding a huge `cwnd`.

## Stage 4: The Socket Receive Buffer

By the time a packet reaches this stage, every earlier stage accepted it. The kernel puts the datagram in the socket's receive queue; if that queue is full, the drop is charged to the socket, not the interface.

The `nstat` output at the top of this article is the canonical example:

```text
UdpRcvbufErrors                 4489733            0.0
```

**4.49 million datagrams dropped at the socket boundary.** This is the single most common silent failure in observability pipelines — metrics agents, syslog-over-UDP, and statsd exporters. The sender has no idea; UDP has no retransmission.

For TCP the equivalent signals are `TcpExtTCPRcvCollapsed` (out-of-order queue collapsed) and a receive queue that never drains, visible here:

```text
$ ss -tin
State  Recv-Q Send-Q  Local Address:Port
ESTAB  0      0       192.168.3.7:445
	 cubic wscale:8,10 rto:246 rtt:45.689/6.516 mss:1460 cwnd:10 ssthresh:346
	 bytes_sent:1341628665 bytes_retrans:12364 bytes_acked:1341616301
	 retrans:0/144 dsack_dups:144 send 2556414bps delivery_rate 297959176bps
```

Read `bytes_retrans` against `bytes_sent`: **12,364 retransmitted bytes out of 1.34 GB is 0.0009% — completely healthy.** A persistently non-zero `Recv-Q` on a busy listener, on the other hand, means userspace is not reading fast enough.

The fix for UDP receivers is a two-part change, and doing only half of it does nothing:

```bash
# 1. Raise the kernel ceiling
sysctl -w net.core.rmem_max=33554432
sysctl -w net.core.rmem_default=2097152

# 2. The application must actually ask for it — SO_RCVBUF overrides rmem_default
```

That second point is where most tuning attempts fail. `rmem_max` is only a *permission*; the socket gets `rmem_default` unless the program calls `setsockopt(SO_RCVBUF)`. Check what a live socket actually negotiated:

```bash
ss -uam    # Mem column shows the real bytes allocated to the receive queue
```

If `Mem` is stuck at 212992 (the classic 208 KB default) while you have set `rmem_max` to 32 MB, the application never asked — and no `sysctl` will save you.

## Finding the Drop Point with Tracing

Counters tell you where loss *accumulated*; tracing tells you *why the kernel discarded this specific packet*. `dropwatch` and a three-line `bpftrace` script both hook `kfree_skb`, the function the kernel calls when it frees a packet that never reached its destination.

```bash
# Debian/Ubuntu
apt install -y dropwatch
dropwatch -l kas      # requires kernel symbols; prints the caller of kfree_skb
```

The modern, symbol-free equivalent — this prints the kernel stack for every dropped packet, which immediately names the stage:

```bash
bpftrace -e '
kprobe:kfree_skb /arg1 != 0/ {
  @drops[kstack] = count();
}
interval:s:10 { print(@drops); clear(@drops); }'
```

If the stack ends in `__udp_queue_rcv_skb`, the drop is a full socket buffer. If it ends in `enqueue_to_backlog`, it is the softnet backlog. If it ends in `qdisc_drop` / `fq_codel_drop`, it is egress shaping. One ten-second trace replaces an hour of `sysctl` guessing.

## The Five Mistakes That Waste Your Afternoon

1. **Trusting `ifconfig`/`ip -s link` drop counts.** They report driver-level drops only. `IpInDiscards` was **0** on the machine above while 4.49 million datagrams were being dropped at the socket layer. The interface was innocent.
2. **Raising buffers before measuring.** Doubling `rmem_max` when `softnet_stat` column 2 is climbing adds memory and fixes nothing. Measure first, then tune the stage that is actually losing packets.
3. **Forgetting `time_squeeze` is not a drop counter.** Teams chase column 3 as if it were loss, then waste days on ring buffers when the real issue is scheduling jitter.
4. **Ignoring `requeues`.** 2.8 million requeues will not appear in any drop counter, but they add the queueing delay that makes TCP collapse its window and your p99 spike.
5. **Assuming a 0.0 rate means nothing happened.** Every `nstat` row above shows `0.0` in the rate column because the counters were not moving *at that instant*. They moved millions of times earlier. Always read the absolute counter, and compare two snapshots — never a single instantaneous rate.

For the adjacent failure modes, see our guide to [TIME_WAIT storms and ephemeral port exhaustion](../2026-11-22-time-wait-port-exhaustion-diagnosis/) and the [connection tracking comparison](../2026-05-23-linux-connection-tracking-conntrack-tools-vs-nftables-vs-iptables-guide/), which covers `nf_conntrack: table full` — a drop message that *does* reach the logs. If your sockets are dying rather than their buffers filling, the [file descriptor and ulimit tuning guide](../2026-11-21-too-many-open-files-ulimit-systemd-limits-tuning/) is the right next read. And when you need to prove a network path is actually clean before blaming the kernel, use the [network performance measurement toolchain](../2026-05-13-self-hosted-network-performance-measurement-perfsonar-iperf-smokeping-guide/).

## FAQ

**Why does `ip -s link` show zero drops when my application is losing packets?**
Because interface counters only cover the driver and qdisc stages. Drops inside the socket receive buffer (`UdpRcvbufErrors`) and inside the softnet backlog (`softnet_stat` column 2) never touch interface statistics. Check `nstat -az` and `/proc/net/softnet_stat` first.

**Is a growing `time_squeeze` counter a problem?**
Not by itself. `time_squeeze` means the softirq ran out of its time budget with packets still queued, so processing was deferred to `ksoftirqd`. It causes jitter and higher tail latency, but no packets are lost. Only column 2 (`dropped`) indicates actual loss at that stage.

**I set `net.core.rmem_max` to 64 MB but UDP drops did not improve. Why?**
`rmem_max` is a ceiling, not a default. The application must call `setsockopt(SO_RCVBUF)` to request a larger buffer, and the kernel silently clamps anything above `rmem_max`. Verify what the socket really got with `ss -uam` and look at the `Mem` column. If it is ~208 KB, the program never asked for more.

**What is a normal TCP retransmission ratio?**
Under 0.1% on a healthy local network, and under 1% on a long-haul path. Compare `bytes_retrans` to `bytes_sent` in `ss -ti`. Watch `TcpExtTCPLostRetransmit` in particular: if it is a large fraction of `TcpRetransSegs` — as in the sample above, 1.24 M lost retransmits against 1.66 M retransmissions — the path is dropping the recovery traffic too, and TCP will stall for full RTO backoffs.

**Does a packet capture always reveal the drops?**
No. `tcpdump` taps the packet path at the socket-ish layer, so packets dropped in the NIC ring buffer or discarded before the tap point never appear. If `tcpdump` shows a clean stream but the receiver's counters disagree, the loss happened *below* the capture point.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Your Linux Box Is Dropping Packets Silently: A 2026 Field Guide from NIC to Socket",
  "description": "Counter-by-counter guide to locating Linux packet loss across NIC ring buffers, softnet backlog, qdisc queues and socket receive buffers, with real kernel output.",
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
