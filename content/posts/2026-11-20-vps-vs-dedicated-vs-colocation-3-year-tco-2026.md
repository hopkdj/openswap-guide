---
title: "VPS vs Dedicated Server vs Colocation in 2026: The Real 3-Year TCO Numbers"
date: "2026-11-20"
tags: ["self-hosting", "cost-optimization", "infrastructure", "dedicated-servers", "capacity-planning"]
draft: false
description: "A line-by-line 3-year total cost of ownership model for VPS, dedicated servers, and 1U colocation — including the egress, IPv4, backup, and labour costs that quote pages hide."
---

A €4 VPS feels free until you need 64 GB of RAM. Then the same provider quotes you **€110/month** for a virtual machine whose CPU is still shared with three noisy neighbours — and you start wondering whether the €46 dedicated box in the same datacenter, or a €1,800 server you own outright in a €55/month rack unit, is actually the cheaper answer.

It usually is. But not always, and the difference is decided by four numbers most comparison pages never print: egress volume, storage growth, your hourly rate, and how long you keep the hardware. This guide builds the model properly, with prices you can verify today.

## TL;DR

**Under 16 GB RAM and under 2 TB of traffic: rent a VPS.** The management overhead dominates; a hyperscaler-style control plane plus snapshots is worth more than the €20 you'd save.

**16–128 GB RAM, predictable load, you can tolerate 20–60 minutes of hardware-swap downtime: buy a dedicated server.** At 64 GB / 16 threads / 4 TB NVMe, dedicated lands around **€45–65/month** versus **€100–140/month** for the equivalent virtual machine — a 55–60% saving that compounds to €2,000+ over three years.

**You need more than 128 GB RAM, 10+ TB of storage, your own IP space, or hardware you already own: colocate.** Colocation only wins when the capital is already sunk or amortised over 5+ years, and only if you can physically reach the facility.

**Never colocate a single server you depend on** unless you have a second one somewhere else. Colocation is a cost play, not a resilience play.

## Raw Cost Comparison

List prices, EUR excluding VAT, November 2026. Verify before you commit — providers reprice constantly.

| Dimension | Cloud VPS (shared vCPU) | Cloud VPS (dedicated vCPU) | Dedicated server (rented) | 1U colocation (own hardware) |
|---|---|---|---|---|
| 64 GB RAM tier | ~€105–130/mo | ~€150–190/mo | **~€45–65/mo** | €0 hardware rental + ~€50–70/mo space |
| CPU guarantee | Burstable, steal time 0–15% | Dedicated cores | Full physical cores | Full physical cores |
| Storage included | 300–500 GB NVMe | 500 GB NVMe | 2×512 GB – 2×1 TB NVMe | Whatever you buy |
| Traffic included | 20–32 TB/mo | 20–32 TB/mo | 20–32 TB/mo (1 Gbit) | Depends on contract |
| Setup time | 30 seconds | 30 seconds | 2–24 hours (often instant) | 2–6 weeks |
| Hardware failure | Provider replaces, ~5 min | Provider replaces, ~5 min | Provider replaces, 1–4 h | **You** replace, 4 h–5 days |
| Remote console | Web console | Web console | IPMI/KVM | IPMI over VPN |
| Snapshot/rollback | Native, €0.01/GB | Native | Manual (LVM/ZFS + rsync) | Manual |
| Upfront capital | €0 | €0 | €0 (some ask 1 month) | **€1,500–2,500 per node** |
| Minimum commitment | Hourly | Hourly | Monthly | 12–24 months |

The single most misleading row is "RAM tier". A 64 GB shared-vCPU instance is not the same product as a 64 GB dedicated box, but it is priced as if it were — and it is the row people compare.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Choose | Because |
|---|---|---|
| Side project, <8 GB RAM, traffic spiky | VPS | Hourly billing, snapshots, zero ops |
| Production app, 32–64 GB, steady load | Dedicated | 55–60% cheaper, no steal time |
| Postgres >200 GB with heavy random I/O | Dedicated | Local NVMe, no noisy-neighbour I/O stalls |
| Media transcoding / CI runners / game servers | Dedicated | Sustained full-core load is exactly what VPS pricing punishes |
| 256 GB+ RAM, 20 TB+ storage | Colocation | Rental pricing scales linearly; owned hardware doesn't |
| You already own 2+ servers | Colocation | Sunk capital, marginal cost is rack space only |
| You have no remote hands and no spare parts | VPS or dedicated | Colo without a parts plan is an outage plan |
| Compliance requires physical custody of disks | Colocation | You hold the drives, not a hypervisor admin |
| Team of one, no on-call | VPS | Managed failure domain is the product |

## VPS: What You're Actually Paying For

You are buying four things: instant provisioning, a hypervisor you never patch, snapshots, and someone else's spare-parts inventory. At small scale that's a bargain. At 64 GB it's a tax.

The trap is **steal time**. Shared-vCPU plans oversubscribe physical cores, so a database that looks fine at 30% CPU will spike to 400 ms query latency whenever a neighbour compacts a table. Measure before you migrate anything important:

```bash
# Baseline the instance before you trust it: steal time, CPU model, disk latency
nproc; grep -m1 "model name" /proc/cpuinfo
vmstat 1 10 | awk '{print $1, $15, $16, $17}'   # us sy id wa  (+st in column 17 on Linux)
top -bn1 | grep -i "%Cpu"
# 4k random read IOPS as the provider actually delivers them
fio --name=randread --ioengine=libaio --direct=1 --bs=4k --iodepth=32 \
    --numjobs=4 --size=1G --rw=randread --runtime=30 --time_based \
    --group_reporting --output-format=terse | cut -f8,9,39,40
```

If steal time sits above **2% sustained**, or 4k random read IOPS land under **5,000**, that "dedicated vCPU" plan is not dedicated and should not host a write-heavy database.

Provider pricing is also machine-readable, which makes it easy to keep the model honest instead of relying on a blog post (including this one):

```bash
# Current list prices for a provider's server types, as JSON
curl -s https://api.hetzner.cloud/v1/server_types | jq -r '.server_types[] |
  "\(.name)\t\(.cores)c/\(.memory)GB\t€\(.prices[0].monthly.gross)"' | column -t
curl -s https://api.hetzner.cloud/v1/pricing | jq '.pricing.traffic_price_per_tb'
```

## Dedicated Servers: The Sweet Spot Nobody Markets

A rented dedicated server is the only tier where price and capability scale together. You get full physical cores, local NVMe that isn't throttled by a shared storage fabric, and — critically — the ability to run **your own kernel**, your own ZFS pool, and your own KVM guests.

The costs providers don't quote:

- **Replacement delay.** Consumer-grade dedicated boxes (desktop Ryzen, non-ECC RAM) fail more often than enterprise VPS hosts. Budget a hot spare or accept 4–24 hours down. Ask the provider for their hardware SLA in writing; many promise "best effort" and mean it.
- **Backup is yours.** A €5/month storage box plus `restic` covers most cases. See our [server sizing and RAM budgeting guide](../2026-11-19-self-hosted-server-sizing-ram-cpu-guide/) before you pick the RAM tier — overbuying RAM is the most common dedicated-server mistake.
- **No snapshot rollback.** Set up ZFS or LVM snapshots on day one, not after the first bad upgrade:

```bash
# Cheap insurance on a dedicated box: ZFS boot environments + hourly snapshots
zfs create -o mountpoint=/srv/data rpool/data
# hourly, keep 48; daily, keep 14
cat >/etc/cron.d/zfs-snap <<'EOF'
0 * * * * root /sbin/zfs snapshot rpool/data@hourly-$(date +\%Y\%m\%d\%H) && /sbin/zfs list -t snapshot -o name -s creation -H rpool/data | head -n -48 | xargs -r -n1 /sbin/zfs destroy
EOF
systemctl restart cron
```

Also check the box's real hardware the day it arrives — `dmidecode -t memory` for ECC support, `smartctl -a` for drive hours, `ipmitool sdr` for fan and PSU telemetry. A "new" server with 30,000 power-on hours is a return, not a bargain.

## Colocation: Only Math That Survives Contact With Reality

Colocation prices look unbeatable on a spreadsheet — €50/month for 1U, power included — until you add the parts you must own: a €1,800 server, a €400 rail kit and PDU, spare disks, a spare PSU, a KVM-over-IP dongle, and a 4-hour round trip to the facility the day a fan dies.

Where it genuinely wins is **density and duration**. One 1U chassis holding 256 GB of RAM and 60 TB of NVMe costs the same €50–70/month as one holding 32 GB. Amortise the hardware over 5 years — realistic, since server CPUs age slowly — and the effective monthly cost of the 256 GB node drops to roughly **€85–95 including power**, versus €400+ for the nearest rented equivalent.

```yaml
# ansible/inventory/colo.yml — treat colocated metal as cattle, not pets
all:
  children:
    colo_nodes:
      hosts:
        node-a.example.net:
          ipmi_address: 10.0.10.11
          zfs_pool: rpool
          rack: "A12/U34"
        node-b.example.net:
          ipmi_address: 10.0.10.12
          zfs_pool: rpool
          rack: "A12/U35"
      vars:
        ansible_user: ops
        ansible_python_interpreter: /usr/bin/python3
        monitoring_agent: node_exporter
        backup_target: "sftp:backup@10.0.10.5:/srv/restic"
```

The colocation rules that keep you out of trouble:

1. **Two identical nodes minimum.** Not one node and "we'll rebuild from backups" — restore time is measured in days, not minutes.
2. **Contract the remote-hands SLA.** Confirm smart-hands pricing per incident; €75/hour is normal and a single 20-minute disk swap can cost more than the monthly rack fee.
3. **Ship spare disks and a spare PSU with the server.** Buying a replacement locally at retail price on a Saturday is the most expensive disk you will ever own.
4. **Budget the trip.** Fuel, tolls, and a day of your time are real costs; two unplanned visits per year can add €600.

## Three-Year TCO Model

The scenario: 16 threads, 64 GB RAM, 4 TB usable NVMe, 8 TB/month egress, one production workload that matters. All figures EUR, three years, excluding VAT. Labour priced at €60/hour.

| Cost line | Cloud VPS (64 GB, dedicated vCPU) | Dedicated (rented) | Colocation (own 1U) |
|---|---|---|---|
| Compute/space, 36 months | €5,760 (€160/mo) | €1,980 (€55/mo) | €2,160 (€60/mo) |
| Hardware capital | €0 | €0 | €2,400 |
| Storage upgrade to 4 TB | €480 | €0 (included) | €0 (in capex) |
| Egress overage (8 TB/mo) | €0–300 | €0 | €0–200 |
| Backups (offsite, 2 TB) | €540 | €180 | €180 |
| Snapshots / block storage | €360 | €0 (ZFS) | €0 (ZFS) |
| Spare parts & shipping | €0 | €0 | €500 |
| On-site visits (2/yr × 3 yrs) | €0 | €0 | €900 |
| Ops labour, setup + patching | 40 h → €2,400 | 70 h → €4,200 | 110 h → €6,600 |
| **3-year total** | **€9,840** | **€6,360** | **€12,940** |
| **Effective monthly** | **€273** | **€177** | **€359** |

Read that carefully: **dedicated wins by €3,480 over three years**, and colocation loses to both — because at this size the labour and spare-parts lines swamp the rack fee. Colocation only flips positive when one rack unit carries far more RAM and storage than the model above, or when the hardware is already paid for.

Cut the labour line to zero (you enjoy this, and the hours are evenings) and the picture changes: VPS €2,760, dedicated €2,160, colocation €6,340 in cash terms. **Dedicated still wins.** That is the real finding — the usual "colocation is cheapest" claim assumes free labour and free hardware.

## Pitfalls That Blow Up the Model

- **Pricing IPv4 as free.** Colocation and some dedicated providers charge €1–3/month per address; extra addresses on a VPS often cost more than the instance's CPU upgrade.
- **Forgetting egress asymmetry.** Rented dedicated tiers usually include 20–32 TB on a 1 Gbit port. Cloud VPS egress is where the surprise bills live — model your actual monthly bytes from logs before signing anything, not from the marketing page.
- **Buying desktop-grade hardware for colocation.** Non-ECC RAM and consumer NVMe in a rack is a false economy: one silent bit flip in a database page costs more than the €300 you saved.
- **Ignoring power caps.** A 1U contract usually includes 0.3–0.5 A at 230 V (roughly 70–115 W). A modern 16-core server idle draws 60–90 W and peaks near 200 W; overage is billed per kWh at painful rates.
- **Assuming backups are portable.** A provider's snapshot is not a backup — it lives on the same storage fabric. Always keep one copy you can restore without the provider's API; our [cost estimation tooling comparison](../2026-05-07-self-hosted-cloud-cost-estimation-infracost-opencost-cloud-custodian-guide/) covers the modelling side.
- **Migrating before measuring.** Run the workload on a VPS for two weeks with `node_exporter` and a proper dashboard first. Moving to metal because "it feels slow" without IOPS and steal-time numbers is how people end up with a €60/month server that is just as slow.

For teams already running Kubernetes, the same logic applies one layer up — see the [Kubernetes cost management comparison](../2026-05-17-self-hosted-kubernetes-cost-management-opencost-vs-goldilocks-vs-kubecost-guide/) for where cluster-level waste hides.

## FAQ

**Is a dedicated server always cheaper than a VPS?**
No. Below roughly 16 GB RAM the rental price gap is €10–20/month, which is less than the value of native snapshots, instant rebuilds, and provider-managed hardware failure. Dedicated becomes clearly cheaper from about 32 GB upward, and dramatically so at 64 GB and beyond.

**How much RAM do I actually need before moving off a VPS?**
Measure peak resident usage over 30 days, add 30% headroom, then check the price of the next tier up. If the VPS tier that fits costs more than 1.8× the equivalent dedicated box, move. Our [sizing guide](../2026-11-19-self-hosted-server-sizing-ram-cpu-guide/) has per-service RAM tables.

**Can I colocate a single server safely?**
Only if you accept that any hardware failure means multi-day downtime and a physical trip. A single colocated node is a cost optimisation for non-critical workloads or a second copy of data that lives elsewhere. Never for the only copy of production.

**Do I need ECC RAM on a dedicated or colocated server?**
For anything storing data you cannot recompute, yes. Silent memory corruption in a ZFS pool or a database is exactly the failure mode that ECC exists to prevent, and it is undetectable after the fact. Consumer Ryzen boards often support ECC with the right CPU and motherboard pairing — verify with `dmidecode -t 16` before buying.

**What is the break-even point for colocation?**
Roughly 128 GB RAM and 8 TB of storage per rack unit, held for four or more years, with a second node for redundancy and labour you do not bill. Below that, rented metal wins; above it, colocation's fixed rack fee amortises across capacity you would otherwise rent at a linear price.

**How do I avoid a surprise bill when migrating?**
Snapshot two weeks of `node_exporter` metrics — CPU steal, IOPS, network bytes, disk growth — and price each tier against those numbers. Then run the new box in parallel for a week before cutting DNS over.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "VPS vs Dedicated Server vs Colocation in 2026: The Real 3-Year TCO Numbers",
  "description": "A line-by-line 3-year total cost of ownership model for VPS, dedicated servers, and 1U colocation, including egress, IPv4, backup and labour costs.",
  "datePublished": "2026-11-20",
  "dateModified": "2026-11-20",
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
