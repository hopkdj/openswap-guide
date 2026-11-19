---
title: "Burn In Before You Deploy: The 24-Hour Acceptance Test for Any Self-Hosted Server (2026)"
date: "2026-11-20"
tags: ["homelab", "hardware", "self-hosting", "reliability", "server-hardware"]
draft: false
description: "A complete 24-hour burn-in and acceptance test for new or used servers: memtest86+, stress-ng, fio, smartctl, ECC counters, thermal checks and the pass criteria that tell you to RMA instead of deploy."
---

The server arrives, you rack it, install the hypervisor, migrate eight virtual machines onto it, and six weeks later a DIMM throws correctable errors under load — corrupting a ZFS block that you only discover during a restore. The replacement part is free. The weekend is not.

Hardware defects cluster in two windows: the first 48 hours, and the 18 months after thermal paste has dried out. The first window is the one you control. **Twenty-four hours of deliberate abuse before a machine holds production data converts a class of future outages into a return shipment** — and on used hardware it is the difference between a bargain and a paperweight.

## TL;DR

**Minimum viable burn-in: 24 hours, split as 8 h memory, 2 h CPU/thermal, 8 h storage, 1 h network, 5 h mixed soak.** Run it on bare metal before you install a hypervisor — errors at the hypervisor layer are indistinguishable from hardware faults, and you will waste a day chasing the wrong layer.

**Memtest86+ for four full passes is non-negotiable.** One correctable ECC error in the first four passes means RMA, not "it's probably fine". Memory faults are silent, random, and corrupt data written months earlier.

**Watch for what the spec sheet does not tell you:** reallocated sectors on "new" drives, 30,000 power-on hours on a "refurbished" unit, firmware from 2021, fan curves that only exist in the vendor's Windows tool, and NICs that pass ping but drop frames under load.

**Document the result.** A one-page report per machine (model, serials, drive hours, test outcomes, thresholds hit) is what turns a hobby into an operation — and it is the only thing that gets you a warranty replacement six months later.

## The Test Matrix

Twenty-four hours, in this order. Overlap where it makes sense; do not skip memory.

| Stage | Component | Tool | Duration | Pass criteria |
|---|---|---|---|---|
| 1 | RAM | `memtest86+` (4 passes) | 6–10 h | **0 errors**; ECC corrected errors 0 |
| 2 | RAM (OS level) | `stressapptest` | 1 h | 0 mismatches, 0 ECC counters |
| 3 | CPU + cooler | `stress-ng --cpu 0` | 2 h | No throttle below base clock; package temp < Tjmax − 15 °C |
| 4 | Storage integrity | `badblocks -wsv` (destructive) | 4–12 h | 0 bad blocks |
| 5 | Storage health | `smartctl -t long`, `nvme self-test` | 2–8 h | 0 reallocated, 0 pending, 0 media errors |
| 6 | Storage throughput | `fio` (4k random + 1M sequential) | 30 min | Within 10% of drive spec; no latency spikes > 5× |
| 7 | Network | `iperf3` bidirectional + `ethtool -S` | 20 min | ≥90% line rate, 0 CRC/dropped errors |
| 8 | Power + thermals | `ipmitool sdr`, `sensors`, `turbostat` | throughout | Rails within ±5%, no fan stalls, inlet < 30 °C |
| 9 | Firmware | vendor BIOS/BMC tools | 1 h | Latest stable BIOS, BMC, NIC, NVMe firmware |
| 10 | Mixed soak | real workload + `dmesg -w` | 5 h | No MCE, no ATA/NVMe resets, no OOM |

## Stage 1–2: Memory Is Where Silent Corruption Lives

Install Memtest86+ on a USB stick and let it run four complete passes — not two, not "until it looks fine". Faulty DIMMs frequently pass the first pass and fail when the module is warm:

```bash
# Build the USB image (or use the vendor's prebuilt ISO)
git clone --depth 1 https://github.com/memtest86plus/memtest86plus.git
cd memtest86plus && make      # produces mt86plus.bin; write to USB with dd
sudo dd if=mt86plus.bin of=/dev/sdX bs=1M conv=fsync status=progress
```

Then, from the installed OS, hammer the same memory with a different access pattern — two tools catch different fault classes:

```bash
# 1 hour, 28 GB of the 32 GB, 8 threads, with a disk-backed verify pass
stressapptest -s 3600 -M 28000 -m 8 --disk /var/tmp/stressfile --disk-threads 4 -v

# ECC telemetry — must stay at zero on a healthy machine
sudo dmidecode -t 16 | grep -E "Maximum Capacity|Error Correction"
sudo edac-util -v          # corrected/uncorrected counts per controller
sudo rasdaemon -r -f       # or: journalctl -k | grep -iE "machine check|edac|corrected"
```

**Interpretation rule:** a single corrected ECC error during burn-in is a failed DIMM. Do not "monitor it". Correctable errors mean the module is already marginal, and uncorrectable errors in a ZFS pool are data loss. Swap the stick, re-run, ship the old one back.

## Stage 3: CPU, Cooler and the Throttle Trap

`stress-ng` exercises every execution unit, but the number that matters is not the load average — it is whether the CPU holds its clocks:

```bash
# All cores, every method, with metrics
stress-ng --cpu 0 --cpu-method all --metrics-brief --timeout 7200s

# In a second terminal: watch for throttling and thermal headroom
sudo turbostat --quiet --show CoreTmp,PkgTmp,PkgWatt,Busy%,Bzy_MHz --interval 5
watch -n5 'sensors | grep -E "Package|Core|fan"'
```

Failure signatures worth acting on:

- **Clocks dropping to base or below while temperature is high** → cooler contact or airflow problem. Re-seat the heatsink before blaming the CPU.
- **Package temperature above 85 °C at stock clocks** → repaste, check fan curve, verify the chassis has front-to-back airflow and blanking panels.
- **`dmesg` shows `CPU0: Core temperature above threshold, cpu clock throttled`** → the machine will be unstable in summer even if it is fine today.
- **Machine check exceptions (`mce`) during load** → stop. Either the CPU, the board, or the PSU is marginal; test the PSU first, it is the cheapest swap.

If the fans only ramp under the vendor's Windows utility, fix the curve at the BMC level and verify with `ipmitool sdr type Fan` — a server that cannot cool itself without a proprietary userspace daemon is a server that will cook itself during a kernel upgrade.

## Stage 4–6: Storage — Destructive Tests First, Data Second

New drives deserve suspicion. Enterprise SSDs are counterfeited, "refurbished" HDDs are relabelled with wiped SMART data, and SATA cables cause more phantom errors than any other component in a server.

```bash
# 1. Baseline every drive BEFORE writing data
for d in /dev/sd{a,b,c,d}; do
  echo "== $d"; sudo smartctl -i "$d" | grep -E "Model|Serial|Power_On|Rotation"
  sudo smartctl -A "$d" | grep -E "Reallocated|Pending|Uncorrect|CRC|Temperature"
done
sudo nvme list && for n in /dev/nvme0 /dev/nvme1; do sudo nvme smart-log "$n"; done

# 2. Destructive surface scan (wipes the drive — do this on day zero only)
sudo badblocks -wsv -b 4096 /dev/sdb

# 3. Drive-managed self-test, then read the result 2-8 hours later
sudo smartctl -t long /dev/sdb
sudo smartctl -l selftest /dev/sdb
```

Pass criteria, applied strictly:

| Reading | Healthy | Return the drive |
|---|---|---|
| `Reallocated_Sector_Ct` | 0 | **Any non-zero value on a "new" drive** |
| `Current_Pending_Sector` | 0 | Any non-zero after a full write pass |
| `UDMA_CRC_Error_Count` | 0 | Growing during tests — replace cable, then drive |
| `Power_On_Hours` | < 100 on new | > 5,000 on "new" |
| NVMe `media_errors` | 0 | Any non-zero |
| `Percentage Used` (NVMe) | 0–2% | > 10% on "new" |

Then measure what you actually bought. Datasheet IOPS are measured on an empty drive with a perfect queue depth; your workload is neither:

```bash
# 4k random read, 32 outstanding I/Os — the number that predicts database latency
fio --name=randread --ioengine=libaio --direct=1 --bs=4k --iodepth=32 \
    --numjobs=4 --size=4G --rw=randread --runtime=300 --time_group_report \
    --group_reporting --output-format=json > /var/log/burnin/fio-4k.json

# 1M sequential write — the number that predicts backup windows
fio --name=seqwrite --ioengine=libaio --direct=1 --bs=1M --iodepth=16 \
    --numjobs=2 --size=8G --rw=write --runtime=300 --group_reporting
```

If 4k random read lands below 60% of the datasheet figure on an otherwise idle machine, either the drive is SMR/QLC masquerading as something better, or the HBA/cable path is degraded. Both are return-and-replace situations on day zero. For interpreting the deeper counters, our [RAID health monitoring guide](../2026-06-03-linux-raid-health-monitoring-mdadm-smartctl-raid-check-guide/) covers what each SMART attribute actually predicts, and the [fio and io_uring benchmarking guide](../2026-05-23-self-hosted-linux-io-uring-tool-ecosystem-liburing-fio-uring-bench-guide/) covers squeezing reliable numbers out of modern kernels.

## Stage 7–8: Network, Power and Thermals

Network faults hide behind working pings. Push real bytes in both directions and read the error counters afterwards:

```bash
# On the peer: iperf3 -s
iperf3 -c 10.0.0.2 -t 60 -P 4            # upload
iperf3 -c 10.0.0.2 -t 60 -P 4 -R         # download
ethtool -S eth0 | grep -Ei "err|drop|crc|miss|overrun"

# Power rails, fans, inlet temperature — sample during the CPU stress stage
sudo ipmitool sdr type "Power Supply" ; sudo ipmitool sdr type Fan
sudo ipmitool sel elist | tail -20       # system event log: PSU, thermal, ECC events
```

Expect **≥90% of line rate** on 1 Gbit and 10 Gbit links with jumbo frames tested separately. Any increment in `rx_crc_errors`, `rx_frame_errors`, or `rx_missed_errors` during a clean 60-second run is a cabling or NIC fault. Swap the cable first — it is €8 — then the NIC.

A note on `ipmitool`: the upstream GitHub repository has not been updated since **2023** (1,638 stars), so build from your distribution's package instead of the repo, and prefer `ipmitool` 1.8.19 or later for modern BMCs:

```bash
sudo apt install ipmitool && ipmitool -V
sudo ipmitool lan print 1        # confirm BMC network isolation before you rack it
```

## Stage 9–10: Firmware, Then a Real Workload

Update firmware **before** you install anything you care about, and update the BMC before the BIOS so a failed BIOS flash is still recoverable remotely. Then run a mixed soak with the actual workload — a ZFS scrub plus a VM migration plus a backup job — while watching the kernel log:

```bash
# 5-hour mixed soak with continuous error capture
dmesg -wT > /var/log/burnin/dmesg.log &
zpool scrub tank
stress-ng --vm 2 --vm-bytes 8G --hdd 2 --hdd-bytes 4G --timeout 5h --metrics-brief
grep -iE "mce|edac|ata.*error|nvme.*reset|I/O error|link down" /var/log/burnin/dmesg.log
```

Any line matching that grep after a completed burn-in is a defect, not noise. `nvme ... reset` during sequential writes on a healthy drive does not happen.

## When a Test Fails: Keep, Fix or Return

| Finding | Action | Why |
|---|---|---|
| Any ECC error in 4 passes | **Return DIMM** | Marginal modules fail under summer heat |
| Reallocated sectors > 0 on new HDD | **Return drive** | Remap events cluster; this one is already going |
| Power-on hours > 5,000 on "new" | **Return or renegotiate** | Refurb sold as new; expect shortened life |
| Thermal throttle at stock clocks | Fix cooling, then re-test | Repaste/airflow, not a warranty claim |
| NIC CRC errors with new cable | **Return NIC** | PHY fault; will resurface under load |
| PSU rail drift > 5% | **Return PSU** | Cheapest component, most catastrophic failure |
| One bad block late in `badblocks` | Return drive | Late-surface defects indicate platter damage |
| Cosmetic dents, functional pass | Keep, document | Note it in the report; affects resale, not uptime |

Write the result down. A minimal report per machine — model, serial, BIOS/BMC version, drive serials with power-on hours, each stage's outcome, and any threshold that failed — is what you attach to an RMA six months later when the vendor claims the part was fine on arrival.

## Pitfalls

- **Running burn-in inside a hypervisor.** Hypervisor-level I/O errors, ballooning, and emulated devices mask real hardware faults. Test on bare metal, then install.
- **Using `badblocks` on a drive with data.** It is destructive by design. On a machine already in service, use `smartctl -t long` plus a scrub instead.
- **Skipping the ECC counters because memtest passed.** Memtest does not always surface corrected errors that the kernel logs; check `edac-util` and `rasdaemon` after the OS is up.
- **Trusting SMART on USB bridges.** Many USB-SATA bridges hide SMART data entirely; test drives on a real HBA or SATA port.
- **Ignoring inlet temperature.** A server that passes in a 19 °C room can throttle in a 32 °C closet. Measure ambient at the front of the chassis, not at the back of the rack.
- **Forgetting the second-hand PSU.** Redundant PSUs fail one at a time and nobody notices until the second one goes. Pull one during the soak test and confirm the machine stays up.
- **Not retesting after firmware updates.** A BIOS update can change fan curves and memory training. Re-run the 2-hour CPU/thermal stage afterwards. For chassis-level cooling automation once the machine is in service, see the [fan control guide](../2026-05-23-self-hosted-linux-fan-control-thinkfan-nbfc-thermal-daemon-guide/).

## FAQ

**How long should a burn-in actually run?**
Twenty-four hours is the practical floor for a single machine: 8 hours memory, 2 hours CPU/thermal, 8 hours storage, and the remainder as mixed soak. For used enterprise hardware or anything holding the only copy of data, extend to 72 hours — the defect rate curve flattens but does not reach zero before then.

**Can I burn in a VPS or cloud instance?**
Partially. You can run `stress-ng`, `fio`, and `iperf3` to validate the instance's real CPU steal time and disk IOPS, which is genuinely useful before committing to a provider. You cannot test memory integrity or firmware, and a VPS that passes today can be migrated to different hardware tomorrow.

**Does memtest86+ work with ECC RAM?**
Yes, and it will report ECC-corrected errors it triggers. However, some server platforms do not expose full ECC telemetry to memtest; always cross-check with `edac-util` and `rasdaemon` from the installed OS, because a machine can be silently correcting errors that memtest never sees.

**Is `badblocks -wsv` safe to run on an SSD?**
It writes and verifies the full surface, which consumes a small fraction of an SSD's endurance — acceptable on a new drive as a one-time check. On an SSD already in service, use `smartctl -t long` and the NVMe self-test instead, combined with a full filesystem scrub.

**What temperature should I consider a failure?**
For most server CPUs, sustained package temperature above **85 °C** at stock clocks, or any throttling below base clock, indicates a cooling defect. Inlet air above **30 °C** at the front of the chassis means the room or rack airflow is the problem, not the server.

**How do I test a used server I bought on an auction site?**
Run the full 24-hour suite before installing anything, and add: read every drive's `Power_On_Hours` and `Reallocated_Sector_Ct`, check the BMC system event log (`ipmitool sel elist`) for historical ECC or thermal events, verify ECC is actually populated per `dmidecode -t memory`, and pull one PSU during the soak. Historical SEL entries reveal problems the seller never mentioned.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Burn In Before You Deploy: The 24-Hour Acceptance Test for Any Self-Hosted Server (2026)",
  "description": "A complete 24-hour server burn-in and acceptance test using memtest86+, stress-ng, fio, smartctl and ECC telemetry, with explicit pass criteria and RMA decision rules.",
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
