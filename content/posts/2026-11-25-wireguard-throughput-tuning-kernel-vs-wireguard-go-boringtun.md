---
title: "WireGuard Throughput Tuning in 2026: Kernel vs wireguard-go vs BoringTun (MTU, Buffers, Multi-Queue)"
date: "2026-11-25"
tags: ["wireguard", "vpn", "networking", "performance", "tuning", "linux"]
draft: false
---

You moved a 1 Gbps site-to-site link from OpenVPN to WireGuard, expected the usual 3–4× jump, and got 280 Mbit/s. The tunnel is up, `wg show` reports no errors, and both endpoints show idle CPUs. Nine times out of ten this is not WireGuard being slow — it is a userspace implementation in the datapath, an MTU that forces fragmentation, or a single flow pinned to a single core.

WireGuard's kernel implementation is fast because it does almost nothing: no cipher negotiation, no options, a fixed handshake, and a datapath that runs in the same context as the sending socket. Everything that goes wrong with throughput is therefore outside the protocol. This guide covers where the ceiling actually is, how the three common implementations differ, and the five tuning steps that matter.

## Quick Verdict (TL;DR)

- **Use the in-kernel module.** It has been in mainline Linux since 5.6 and is the only implementation that reaches line rate on 10 GbE with parallel flows. In 2026 there is no reason to run a userspace implementation on a Linux router or server.
- **Run `wireguard-go` or BoringTun only where you cannot load kernel modules** — FreeBSD jails without the kernel option, some container environments, unprivileged CI runners, or a research prototype.
- **Set the MTU deliberately** (1420 over IPv4 transit, lower over PPPoE or another tunnel). Fragmentation and PMTU black holes cost more throughput than any sysctl.
- **Parallelise flows, not packets.** A single WireGuard flow is processed on one CPU. `iperf3 -P 8` will show 4–8× the throughput of `iperf3 -P 1` on a multi-core box — that is expected, not a bug.
- **Check `ethtool -S` for drops before touching sysctls.** Offloads and queue counts are worth more than `rmem_max`.

## The Four Implementations

| Implementation | Datapath | Repo activity | Throughput class | CPU cost | Use when |
|---|---|---|---|---|---|
| **Kernel module** (in-tree since 5.6) | Native netdevice, no copies | `WireGuard/wireguard-linux` mirror, **2,074 stars**, pushed 2026-11-10 | Line rate, scales with cores | Lowest | Any Linux host or router you control |
| **wireguard-go** | TUN device, packet copied kernel→userspace→kernel | `WireGuard/wireguard-go`, **4,566 stars**, pushed 2026-10-24 | Hundreds of Mbit/s per core | High (two copies, Go runtime) | Userspace-only environments, embedded, tests |
| **BoringTun** | TUN device, Rust + BoringSSL | `cloudflare/boringtun`, **7,276 stars**, pushed 2026-06-29 | Similar class to wireguard-go, sometimes faster per core | Medium-high | Where you need a memory-safe userspace datapath (Cloudflare WARP lineage) |
| **AmneziaWG** | Kernel module or Go fork with obfuscation | `amnezia-vpn/amneziawg-go`, **1,994 stars**, pushed 2026-11-16 | Kernel variant near-parity; Go variant like wireguard-go | Low (kernel) / high (Go) | Networks where plain WireGuard handshakes are blocked by DPI |

The honest summary: kernel beats userspace by a wide margin, and the margin grows with packet rate (small packets, many flows). Userspace implementations exist for portability, not performance. If you are choosing between `wireguard-go` and BoringTun for a production tunnel, you have already accepted a large throughput penalty.

## Decision Matrix

| Your constraint | Choice | Why |
|---|---|---|
| Linux server or router, root access | Kernel module | Only path to line rate; zero extra processes |
| Container without `CAP_NET_ADMIN` / module loading | `wireguard-go` | TUN in userspace, no kernel module needed |
| FreeBSD/macOS endpoint | Kernel (FreeBSD) or `wireguard-go` (macOS) | Native where available |
| Censored network, handshake blocked | AmneziaWG (kernel variant) | Adds junk packets and header obfuscation at low cost |
| Fleet of roaming clients behind NAT | Kernel + `PersistentKeepalive = 25` | Keeps the UDP mapping alive without polling |
| Multi-tenant host with per-tenant tunnels | Kernel + network namespaces + cgroup CPU isolation | One namespace per tenant, no shared userspace daemon |

## Step 1 — Confirm You Are Actually on the Kernel Module

Half of all "WireGuard is slow" reports end here. Check the interface type and whether a userspace process owns it:

```bash
# Kernel interfaces are type wireguard
ip -d link show wg0 | head -3

# Userspace implementations own a TUN device — look for the process
sudo lsof /dev/net/tun 2>/dev/null
ps aux | grep -E "wireguard-go|boringtun" | grep -v grep

# Traffic counters, handshake age, and per-peer endpoints
sudo wg show all
```

If `ip -d link show` prints `wireguard` and no process owns a TUN device, you are on the kernel datapath and can stop looking for an implementation problem. If you see a `wireguard-go` process, that is your throughput ceiling.

## Step 2 — Get the MTU Right

WireGuard's overhead is fixed: 20 bytes IPv4 + 8 bytes UDP + 32 bytes WireGuard = 60 bytes over an IPv4 underlay, or 80 bytes when the outer transport is IPv6. `wg-quick` derives the interface MTU from the route MTU automatically, but in static configurations people copy `1420` from a blog post into a network that needs something else.

```bash
# Inspect the current values on both ends
ip link show wg0 | grep mtu
ip route get 203.0.113.10 | head -1     # path MTU toward the peer

# Correct value: underlay MTU minus 80 (IPv6 outer) or minus 60 (IPv4 outer), minus any
# additional encapsulation already in the path (PPPoE = 1492, IPsec = lower still)
sudo ip link set dev wg0 mtu 1420
```

`wg-quick` configuration form:

```ini
[Interface]
Address = 10.9.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>
MTU = 1420
# Pin the socket so the tunnel's own traffic does not route back into the tunnel
Fwmark = 0xca6c

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.9.0.2/32
PersistentKeepalive = 25
```

The diagnostic that proves MTU is your problem: large pings work inside the tunnel but TCP connections stall after the handshake, `iperf3` transmits at full speed for one second and then falls off a cliff, or `ping -M do -s 1400` fails while `-s 1200` succeeds.

```bash
ping -M do -s 1400 -c 3 10.9.0.2       # path MTU probe inside the tunnel
tracepath -n 10.9.0.2                  # finds the actual PMTU
```

## Step 3 — Parallelise Flows Before Blaming the CPU

The kernel implementation processes a flow in the sending socket's context. One TCP stream over WireGuard therefore uses roughly one CPU core, no matter how many cores you have. This is not a WireGuard limitation so much as how socket-based crypto works — but it produces misleading benchmark numbers.

```bash
# Single flow
iperf3 -c 10.9.0.2 -t 30

# Eight parallel flows — the realistic aggregate
iperf3 -c 10.9.0.2 -t 30 -P 8

# Watch per-core utilisation while the test runs
mpstat -P ALL 1
```

If `-P 1` gives you 900 Mbit/s on a 1 Gbps link, you are done. If it gives 300 Mbit/s while one core is pinned at 100% and the others idle, you are single-core bound and parallel flows (or a beefier per-core clock speed) are the only fix. If every core is idle and throughput is still low, the bottleneck is elsewhere: the NIC, the virtualisation layer, or the receiving end.

## Step 4 — Offloads, Queues, and Buffers

These are the settings that turn "almost line rate" into line rate. Verify each with real counters instead of applying them blindly.

```bash
# 1. Check for drops and errors first — this tells you where to look
ethtool -S eth0 | grep -Ei "drop|error|miss|no_buffer" | head -20

# 2. Make sure the physical NIC has enough queues for your core count
ethtool -l eth0
sudo ethtool -L eth0 combined 8        # or the maximum reported by the line above

# 3. Keep GRO/GSO on — the tunnel inherits segmentation benefits from the underlay
ethtool -k eth0 | grep -E "generic-receive-offload|generic-segmentation-offload|tcp-segmentation-offload"

# 4. UDP socket buffers: raise them if you see "no_buffer" or receive drops under load
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
sudo sysctl -w net.core.netdev_max_backlog=5000

# 5. Spread softirq processing if a single core handles all RX interrupts
sudo sysctl -w net.core.rps_sock_flow_entries=32768
echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus   # example: cores 0-3
```

Persist sysctls in `/etc/sysctl.d/99-wireguard.conf`. Do not raise buffers on a 256 MB router "because a guide said so" — every buffer is memory the kernel cannot use for conntrack or the page cache, and oversized UDP buffers do nothing if the sender never fills them.

For tunnels on a hypervisor, two more settings matter: enable multiqueue on the VirtIO NIC (`ethtool -L eth0 combined N` inside the guest), and keep the tunnel's own packets out of the tunnel with `Fwmark` plus a routing rule, or you will build a routing loop that looks exactly like packet loss.

## Step 5 — Measure Honestly

`wg show` gives you the only counters that matter at the protocol layer:

```bash
sudo wg show wg0 transfer        # bytes received / sent per peer
sudo wg show wg0 latest-handshakes
watch -n1 'wg show wg0 transfer'
```

If `transfer` rises but your application throughput does not, the tunnel is fine and the application is the limit. If bytes are retransmitted inside the tunnel, look at MTU. If the handshake keeps re-establishing (age resets every few seconds), your NAT mapping is expiring — set `PersistentKeepalive = 25` on the peer behind NAT, not on both sides.

When you need more than raw throughput, `tc` and cgroup `net_cls`/`net_prio` style shaping still apply to the `wg0` interface just like a physical NIC, so bandwidth caps and priority classes work unchanged.

For the broader picture, our [WireGuard vs OpenVPN vs Tailscale comparison](../self-hosted-vpn-solutions-wireguard-openvpn-tailscale-guide/) covers protocol-level trade-offs and roaming behaviour, while [wireguard-ui and wg-easy compared](../wg-easy-vs-wireguard-ui-vs-wg-gen-web-self-hosted-wireguard-management-2026/) covers the management layer if you are running more than a handful of peers. If your goal is identity-aware access rather than a flat tunnel, the [zero-trust overlay comparison](../2026-05-03-headscale-vs-netbird-vs-openziti-self-hosted-zero-trust-network-access-ztna-guide/) is the better starting point — those systems sit on top of WireGuard and add their own datapath costs.

## Pitfalls That Look Like Protocol Bugs

1. **Running `wireguard-go` on a Linux server.** It works, and it caps you well below what the kernel module delivers. Check for a TUN-owning process before investigating anything else.
2. **Copying MTU 1420 into a PPPoE or nested-tunnel uplink.** Overhead stacks. A tunnel inside a 1492-byte PPPoE link inside a WireGuard tunnel needs a much smaller MTU; PMTU black holes then present as "TCP connects but transfers hang".
3. **Benchmarking with one flow and concluding WireGuard is slow.** Single flow means single core. Use `-P 8` for aggregate numbers and report both.
4. **Setting `PersistentKeepalive` on both peers.** Only the peer behind NAT needs it; leave the public side at 0 to avoid pointless keepalive traffic.
5. **Raising UDP buffers on a memory-constrained router.** You trade a throughput number for OOM kills under load.
6. **Forgetting `Fwmark` on a default-route tunnel.** The encapsulated packets route back into the tunnel, producing a loop that reads as total packet loss.
7. **Ignoring `ethtool -S` drops.** If the NIC is dropping, no amount of tunnel tuning helps — fix queues and offloads first.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "WireGuard Throughput Tuning in 2026: Kernel vs wireguard-go vs BoringTun",
  "description": "Why WireGuard tunnels underperform and how to fix it: kernel vs userspace datapaths, MTU and PMTU, parallel flows, NIC queues, UDP buffers, and honest benchmarking with iperf3.",
  "datePublished": "2026-11-25",
  "dateModified": "2026-11-25",
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

## FAQ

**Why is my WireGuard tunnel slower than expected?**
The three usual causes, in order: a userspace implementation (`wireguard-go`, BoringTun) in the datapath instead of the kernel module, an MTU that causes fragmentation or a PMTU black hole, and a single flow pinned to one CPU core. Check `ip -d link show wg0`, probe the path MTU, then benchmark with parallel flows.

**Does WireGuard scale across CPU cores?**
Aggregate throughput scales with cores because each flow is processed in the context of the sending socket, so many flows spread across many cores. A single flow, however, is processed on essentially one core — that is why one stream tops out well below link rate on a multi-gigabit link.

**What MTU should a WireGuard interface use?**
The underlay MTU minus the encapsulation overhead: 60 bytes over an IPv4 outer transport and 80 bytes over IPv6. On a standard 1500-byte Ethernet underlay that gives 1420 as a safe default; reduce further for PPPoE (1492), IPsec, or another tunnel in the path.

**Is BoringTun faster than wireguard-go?**
Both are userspace TUN-based implementations and both pay for copying packets between kernel and userspace, so both sit far below the kernel module. BoringTun is written in Rust with BoringSSL and is generally competitive per core, but neither is a performance upgrade over the in-kernel datapath.

**Do UDP buffer sysctls actually help?**
They help when the kernel reports buffer-related drops under high packet rates — check `ethtool -S` and `netstat -su` for receive errors before changing anything. Raising `rmem_max` and `wmem_max` on a device that is not dropping does nothing except consume memory.

**How do I test WireGuard throughput properly?**
Use `iperf3` with both a single flow (`-P 1`) and parallel flows (`-P 8`), watch per-core utilisation with `mpstat -P ALL 1`, and confirm with `wg show transfer` that bytes are actually moving through the tunnel. Testing through the tunnel with the tunnel as a bottleneck, but the application as the limit, produces misleading results.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
