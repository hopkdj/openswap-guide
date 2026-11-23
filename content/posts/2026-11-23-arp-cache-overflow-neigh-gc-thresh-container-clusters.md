---
title: "ARP Cache Overflow in 2026: Why 1,024 Neighbour Entries Break Container Clusters"
date: "2026-11-23"
tags: ["linux", "networking", "troubleshooting", "kubernetes", "kernel"]
draft: false
description: "neighbour: arp_cache: neighbor table overflow explained with real kernel counters, the gc_thresh watermarks, and the Kubernetes-sized fix."
---

The kernel log line is short and easy to miss until it is happening a thousand times a second:

```console
$ dmesg -T | grep -c "neighbor table overflow"
1841
kernel: neighbour: arp_cache: neighbor table overflow!
```

Nothing crashed. No OOM killer ran, no CPU spike, no disk full. What happens instead is subtler and far more damaging: **new flows to hosts that are not already in the ARP cache silently fail to resolve**, existing entries get recycled in a tight loop, and latency climbs on exactly the traffic that has to reach a host the node has never talked to before. Health checks to a freshly scheduled pod start timing out while established connections keep working fine — which is why teams spend days blaming the application.

The root cause is one number most people never look at: `net.ipv4.neigh.default.gc_thresh3`, the hard ceiling on neighbour table entries. On this Ubuntu 24.04 host it is still **1,024**.

```console
$ sysctl net.ipv4.neigh.default.gc_thresh1 net.ipv4.neigh.default.gc_thresh2 net.ipv4.neigh.default.gc_thresh3
net.ipv4.neigh.default.gc_thresh1 = 128
net.ipv4.neigh.default.gc_thresh2 = 512
net.ipv4.neigh.default.gc_thresh3 = 1024
```

On a laptop talking to a router, 1,024 is generous. On a Kubernetes node running 250 pods, an IPVS load balancer with a few thousand backends, or a Ceph cluster with hundreds of OSDs, it is a cliff edge.

## TL;DR — The 60-Second Version

- **The three `gc_thresh` values are watermarks, not limits you hit gradually.** Below `gc_thresh1` the garbage collector does nothing. Above `gc_thresh2` it runs once per second (actually every 5 seconds by default). Above `gc_thresh3` every new entry is refused and the kernel logs `neighbor table overflow`.
- **Size `gc_thresh3` to the number of distinct layer-2 neighbours, not the number of hosts you own.** Count pods with their own MAC (macvlan, ipvlan in L2 mode), IPVS backends, and any address that leaves the subnet via a gateway you ARP for.
- **`ip neigh show | wc -l` is the wrong metric.** STALE entries linger by design; the number that matters is how close you run to the watermark during peak churn.
- **Raising the ceiling without watching `forced_gc_runs` hides a leak.** If the table is full on a host with 40 real neighbours, something is creating entries faster than they expire — usually a scanner or a /32 route scheme.
- **For Kubernetes, set it at the node level, not in a pod.** The neighbour table is per network namespace, so a pod-level sysctl only affects that pod's namespace and does nothing for the host that is actually overflowing.

## What the Neighbour Table Actually Holds

Every IP packet that leaves the machine toward an on-link destination needs a MAC address. The kernel keeps a per-interface (strictly, per-network-namespace) table mapping IPv4 and IPv6 addresses to link-layer addresses, along with a state machine per entry: `REACHABLE`, `STALE`, `DELAY`, `PROBE`, `FAILED`, `INCOMPLETE`.

The states matter because they change how many entries exist at once. An entry does not disappear when it goes `STALE` — it stays as a cheap lookup hint and is only probed when traffic arrives for it. That is a deliberate design decision: it makes repeat traffic fast and makes garbage collection essential. The garbage collector runs periodically and deletes stale entries once the table is large, using the three watermarks:

| Sysctl | Value on this host | Meaning when crossed |
|---|---|---|
| `gc_thresh1` | 128 | **Floor.** While the table has fewer entries than this, the periodic GC never deletes anything. |
| `gc_thresh2` | 512 | **Soft pressure.** Once exceeded, the GC runs on its normal interval and starts reclaiming STALE entries aggressively. |
| `gc_thresh3` | 1024 | **Hard ceiling.** No new entries may be allocated. Kernel logs `neighbor table overflow!` and resolution fails. |

Two more knobs live in the same directory and are frequently confused with capacity settings:

```console
$ sysctl net.ipv4.neigh.default.gc_stale_time net.ipv4.neigh.default.ucast_solicit net.ipv4.neigh.default.base_reachable_time_ms
net.ipv4.neigh.default.gc_stale_time = 60
net.ipv4.neigh.default.ucast_solicit = 3
net.ipv4.neigh.default.base_reachable_time_ms = 30000
```

`gc_stale_time` (60 s) is how long an entry may sit unused before being marked STALE and eligible for reclaim. `ucast_solicit` is how many ARP requests are sent before the entry is declared `FAILED` — raising it makes failure detection slower, not the table bigger. `base_reachable_time_ms` determines how long a REACHABLE entry is trusted, randomised between half and 1.5× the value.

A common mistake is to raise `gc_thresh3` and leave `gc_thresh2` at 512. The result is a table that fills to 1,024 entries with the GC working at its normal rate, then refuses new entries anyway, because between GC passes the table can still overshoot. Scale all three together.

## Real Numbers From a Live Host

Theory is cheap. Here is the actual state on the machine that produced this article, which serves a small home/lab network with eleven neighbours and no container churn:

```console
$ ip neigh show | wc -l
11
$ ip -s neigh show | awk '{print $NF}' | sort | uniq -c
      9 STALE
      2 REACHABLE
$ wc -l /proc/net/arp
11 /proc/net/arp
```

Eleven entries against a ceiling of 1,024 — 1% utilisation, exactly what you would expect. The interesting data is not the table itself but the counters the kernel keeps about cache behaviour:

```console
$ cat /proc/net/stat/arp_cache
entries  allocs   destroys hash_grows lookups  hits     res_failed rcv_probes_ucast periodic_gc_runs forced_gc_runs unresolved_discards table_fulls
00000010 0000006c 00000023 00000001   00494703 00415df6 0000000d   00000000         000247d1         00000000       00000000            00000000
00000010 0000000c 0000000d 00000000   0000000c 00000000 0000000c   00000000         000197a0         00000000       00000000            00000000
```

The file is **hexadecimal** and **per CPU** — there is one line per core, and the first line is not a total. Decoding the first line by hand is a rite of passage:

| Column | Hex | Decimal | What it means here |
|---|---|---|---|
| `entries` | `10` | 16 | Current table size for this namespace |
| `allocs` | `6c` | 108 | Entries ever allocated — 108 allocations for 11 live entries shows normal recycle |
| `destroys` | `23` | 35 | Entries ever freed |
| `lookups` | `494703` | 4,802,307 | ARP cache lookups |
| `hits` | `415df6` | 4,283,894 | Lookups answered from cache → **89.2% hit rate** |
| `res_failed` | `0d` | 13 | Resolutions that failed (host down, or probe unanswered) |
| `periodic_gc_runs` | `247d1` | 149,457 | Normal GC passes |
| `forced_gc_runs` | `0` | 0 | Emergency GC when the table hits the ceiling |
| `table_fulls` | `0` | 0 | **Times a new entry was refused** |

That last column is the one to alert on. `table_fulls > 0` is the authoritative, precise signal that you hit `gc_thresh3` — it is far better than grepping `dmesg`, because the kernel rate-limits those log messages and you can overflow the table without seeing the warning at all in a busy log pipeline. If you monitor one thing from this article, monitor `table_fulls`.

Second to it is `forced_gc_runs`. A slow, non-zero trickle of forced GCs is survivable — the kernel reclaims and moves on. `forced_gc_runs` climbing in lockstep with `table_fulls` means the workload genuinely needs a larger table. `forced_gc_runs` climbing on a host that only talks to a handful of addresses means something is generating entries, and you should find it before you raise the number and forget about it.

## The Workloads That Actually Overflow

The pattern is always the same: many distinct layer-2 destinations, short-lived. Four offenders dominate.

**1. Kubernetes with macvlan, ipvlan in L2 mode, or a CNI that assigns one IP per pod on the same subnet.** Every pod is a separate ARP neighbour from the node's perspective. A 250-pod node with a rolling deployment can touch several hundred distinct MACs in minutes. 1,024 entries sounds like four times the pod count until you add the previous ReplicaSet's pods, the service VIPs, the ingress addresses, and the STALE entries from the last three deploys.

**2. IPVS / kube-proxy in IPVS mode with large Services.** IPVS programs a virtual server per Service IP and real servers per endpoint; traffic to external endpoints leaves the node and needs resolution. Thousands of backends across hundreds of Services is routine in a mid-size cluster, and each one may require an ARP entry.

**3. Anything that routes with /32 or /128 host routes.** Cilium's native routing, Calico with `ipipMode: Never` and per-pod routes, and many SDN overlays that avoid encapsulation. Host routes mean "the next hop is the destination" — which means the node must resolve the MAC of every peer it talks to directly. This is the design that gets the most performance and the one that most reliably empties the neighbour table.

**4. Scanning, monitoring sweeps and subnet-wide health checks.** A single `nmap -sn 10.0.0.0/16` or an ICMP sweep from a monitoring box creates an entry attempt per address. Do that from a node with a small table and you will see `table_fulls` increment by hundreds in seconds, even though the traffic is meaningless.

> A useful rule of thumb: `gc_thresh3` should be at least **2× the maximum number of concurrent distinct layer-2 peers**, and never below 4,096 on any node that runs containers with per-pod IPs.

## Raising It Correctly

Never use `sysctl -w` for this. It works, it fixes the symptom for one boot, and it guarantees the next person to rebuild the node inherits the bug. Write a drop-in file instead:

```ini
# /etc/sysctl.d/99-neighbour-table.conf
# Sized for a node with up to ~500 layer-2 peers (pods with per-pod IPs,
# IPVS backends, storage cluster). Roughly 4x headroom over observed peak.
net.ipv4.neigh.default.gc_thresh1 = 1024
net.ipv4.neigh.default.gc_thresh2 = 4096
net.ipv4.neigh.default.gc_thresh3 = 8192

# Same watermarks for IPv6 — a separate table with its own ceiling.
net.ipv6.neigh.default.gc_thresh1 = 1024
net.ipv6.neigh.default.gc_thresh2 = 4096
net.ipv6.neigh.default.gc_thresh3 = 8192
```

```console
$ sudo sysctl --system
* Applying /etc/sysctl.d/99-neighbour-table.conf ...
net.ipv4.neigh.default.gc_thresh1 = 1024
net.ipv4.neigh.default.gc_thresh2 = 4096
net.ipv4.neigh.default.gc_thresh3 = 8192
$ sysctl net.ipv4.neigh.default.gc_thresh3
net.ipv4.neigh.default.gc_thresh3 = 8192
```

Four details decide whether this actually takes effect:

- **IPv4 and IPv6 are separate tables with separate sysctls.** Raising only the `ipv4` keys is a classic half-fix; a dual-stack cluster overflows the v6 table while v4 looks healthy.
- **`default` applies to interfaces created later; existing interfaces get their own copy.** On a long-lived host, also set `net.ipv4.neigh.<ifname>.gc_thresh3` for the real uplink, or reboot. Verify per-interface values with `sysctl -a | grep gc_thresh3`.
- **The table is per network namespace.** A container with `--network=host` shares the host table. A container with its own netns has its own table with its own 1,024 ceiling — which is why a fat pod doing thousands of outbound connections can overflow *inside its namespace* while the host looks fine.
- **Raising the ceiling raises worst-case kernel memory.** Each entry is small (a few hundred bytes), so 8,192 entries costs a couple of megabytes. This is not a memory risk; treat it as free.

## Sizing for Kubernetes Without Guessing

Kubernetes does not expose this as a pod-level setting because it is not a namespaced value in any useful sense. The two workable patterns are a node bootstrap template (cloud-init, ignition, or your image build) and a privileged DaemonSet that writes the sysctl on every node:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: neigh-table-tuning
  namespace: kube-system
spec:
  selector:
    matchLabels: {app: neigh-table-tuning}
  template:
    metadata:
      labels: {app: neigh-table-tuning}
    spec:
      hostNetwork: true
      hostPID: true
      tolerations:
        - operator: Exists
      initContainers:
        - name: tune
          image: busybox:1.36
          securityContext:
            privileged: true
          command:
            - sh
            - -c
            - |
              sysctl -w net.ipv4.neigh.default.gc_thresh1=1024
              sysctl -w net.ipv4.neigh.default.gc_thresh2=4096
              sysctl -w net.ipv4.neigh.default.gc_thresh3=8192
              sysctl -w net.ipv6.neigh.default.gc_thresh1=1024
              sysctl -w net.ipv6.neigh.default.gc_thresh2=4096
              sysctl -w net.ipv6.neigh.default.gc_thresh3=8192
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
```

The DaemonSet approach is a compromise: it runs at boot and after every kubelet restart, but it does not survive a node reboot before the DaemonSet is scheduled. Put the same values in your node image and use the DaemonSet only as a safety net for nodes you cannot rebuild.

## Decision Matrix

| Situation | Action | Why |
|---|---|---|
| Home lab, one subnet, <50 devices | Leave defaults | 1,024 is four times your worst case; touching it adds risk for no gain |
| Single Docker host, bridge networking | Leave defaults | Containers behind NAT share one neighbour (the bridge), not one per container |
| Node with macvlan/ipvlan pods | Raise to 4,096–8,192 | Every pod with per-pod IP is a separate ARP neighbour |
| IPVS kube-proxy, 500+ Services | Raise to 8,192, monitor `table_fulls` | IPVS backends and VIPs both consume entries |
| `table_fulls` increasing, <50 real peers | **Investigate, do not raise** | A scanner, a leak, or a flap loop is generating entries |
| IPv6-only or dual-stack cluster | Raise both `ipv4` and `ipv6` keys | Two independent tables, two independent ceilings |
| Fat pod doing thousands of outbound connects | Check the pod's own netns | Each namespace has its own table and its own 1,024 ceiling |

## Pitfalls

- **The `dmesg` warning is rate-limited and can be missing entirely.** The kernel throttles `neighbor table overflow` messages; a busy host can refuse thousands of entries with a nearly silent log. Trust `/proc/net/stat/arp_cache` column `table_fulls`, not `dmesg`.
- **`table_fulls` is a cumulative counter since boot.** Alert on the *rate of increase*, not on the value being non-zero, or every long-lived node will alarm forever after one incident.
- **"neighbour" is spelled the British way everywhere in the kernel** — `neigh`, `neighbour`, `neighbor table overflow`. Grepping for "neighbor" alone misses half the sysctl names.
- **A full table is not the same as an unreachable host.** If `res_failed` climbs but `table_fulls` is zero, you have real ARP failures (VLAN mismatch, port security, MAC limits on the switch). Raising `gc_thresh3` will never fix those.
- **Switch-side MAC limits produce identical symptoms.** A campus switch port with `port-security maximum 1` drops the ARP replies from extra MACs; the node sees `res_failed` climbing and blames the kernel. Ask the network team before you tune anything.
- **Changing the sysctl does not clear the table.** Existing FAILED entries persist until they age out; `ip neigh flush all` gives you a clean measurement but also a brief broadcast burst, so do not run it during peak traffic.
- **Monitoring for network drops at the socket layer misses this entirely.** Packets are not dropped at the socket here — they fail before transmission because there is no MAC to put in the frame. See our [packet loss diagnosis walkthrough](../2026-11-22-packet-loss-diagnosis-softnet-dropwatch-nic-to-socket/) for the layers below this one, and the [IPv6 neighbour discovery guide](../2026-05-13-self-hosted-ipv6-neighbor-discovery-ndppd-corerad-ndp-library-guide/) for the v6-specific behaviour where NDP replaces ARP but keeps the same watermarks.

If you run containers with per-pod addressing, this is one of a handful of host-level settings you must audit before trusting the platform. Our [Docker Compose hardening checklist](../2026-11-19-docker-compose-hardening-checklist-2026/) covers the rest of the list, and the [general sysctl, tuned and systool guide](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/) explains how the `tuned` profiles interact with hand-written drop-ins — including the profiles that silently overwrite your neighbour settings on a package update.

## FAQ

**What exactly triggers `neighbor table overflow`?**
The neighbour table reached `net.ipv4.neigh.default.gc_thresh3` entries and the kernel refused to allocate another. It logs the warning (rate-limited) and fails to resolve the new address, so the packet cannot be transmitted.

**Is `gc_thresh3` a hard limit or a garbage-collection trigger?**
Both. It is the absolute ceiling on entries. When the table is above `gc_thresh2` the collector runs at its normal interval; when the table hits `gc_thresh3` the kernel performs a forced collection and, if that cannot free enough entries, refuses the new allocation.

**Why does the table fill up when I only have a few dozen hosts?**
Because "hosts" is the wrong unit. Count distinct layer-2 neighbours: pods with per-pod IPs, IPVS real servers, STALE entries from recent deploys, and every address touched by a subnet scan. A single `nmap -sn` sweep across a /16 can create tens of thousands of resolution attempts.

**Does raising `gc_thresh3` cost memory?**
Marginally — a few hundred bytes per entry, so 8,192 entries is on the order of a couple of megabytes. The real cost is that a larger table can delay GC, which is why you scale `gc_thresh2` and `gc_thresh3` together instead of only raising the ceiling.

**Do I need to set both IPv4 and IPv6 values?**
Yes. `net.ipv4.neigh.*` and `net.ipv6.neigh.*` are separate tables with separate counters and separate ceilings. A dual-stack node with only the v4 keys raised will overflow on v6 under the same load.

**Why does `ip neigh show | wc -l` show far fewer entries than my pod count?**
STALE entries are reclaimed and re-created constantly, and containers in their own network namespace have their own tables that `ip neigh` in the host namespace cannot see. Use `nsenter -t <pid> -n ip neigh show` to inspect a container's table.

**Is there a way to alert on this before users notice?**
Yes — collect `table_fulls` and `forced_gc_runs` from `/proc/net/stat/arp_cache`, sum across all per-CPU lines, and alert on the delta per minute. That fires minutes before health checks start failing, whereas `dmesg` may never fire at all.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ARP Cache Overflow in 2026: Why 1,024 Neighbour Entries Break Container Clusters",
  "description": "neighbour: arp_cache: neighbor table overflow explained with real kernel counters, the gc_thresh watermarks and the node-level Kubernetes fix.",
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
