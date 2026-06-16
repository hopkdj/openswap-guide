---
title: "Self-Hosted Storage Benchmarking: FIO vs Sysbench vs Bonnie++ Performance Testing Guide"
date: "2026-06-16"
tags: ["storage", "benchmarking", "performance-testing", "self-hosted", "infrastructure"]
draft: false
---

## Introduction

Storage performance directly impacts database latency, application responsiveness, and user experience. Whether you are provisioning a new NAS, evaluating cloud block storage, or validating an NVMe array, systematic benchmarking reveals the true capabilities of your storage infrastructure — beyond manufacturer specifications.

This guide compares three battle-tested open-source storage benchmarking tools: **FIO (Flexible I/O Tester)**, **Sysbench**, and **Bonnie++**. Each excels at different aspects of storage evaluation, from raw I/O performance to database-simulated workloads to filesystem metadata operations.

## Feature Comparison

| Feature | FIO | Sysbench | Bonnie++ |
|---------|-----|----------|----------|
| **GitHub Stars** | 6,255 | 6,354 | Community |
| **Language** | C | C | C++ |
| **License** | GPL-2.0 | GPL-2.0 | GPL-2.0 |
| **I/O Engine Support** | sync, libaio, io_uring, mmap, SPDK | sync, libaio | sync |
| **Workload Types** | Sequential/random read/write, mixed | OLTP, filesystem | Sequential/random, file create/delete |
| **Multi-thread Support** | Yes (native jobs) | Yes (native threads) | Yes (fork-based) |
| **Network Storage** | Yes (NBD, iSCSI) | No | No |
| **Report Format** | JSON, JSON+, Terse, Normal | Tabular, CSV | Tabular, CSV |
| **Docker Support** | Yes (Official Image) | Yes (Community) | Manual Setup |
| **Learning Curve** | High (100+ options) | Medium | Low (simple CLI) |
| **Best For** | Detailed I/O profiling | Database workload simulation | Filesystem metadata testing |

## FIO: The Swiss Army Knife of I/O Benchmarking

FIO (Flexible I/O Tester) is the industry standard for storage performance testing. Originally written by Jens Axboe (Linux kernel block layer maintainer), FIO can simulate virtually any I/O workload pattern — from a simple sequential read to a complex mix of random reads and writes across multiple threads, block sizes, and I/O depths.

### Key Capabilities

- **I/O engines**: Support for sync, libaio, io_uring, mmap, POSIX aio, Solaris aio, Windows aio, SPDK, and more
- **Workload customization**: Define read/write ratios, random/sequential mix, block size distribution, think time
- **Multi-job parallelism**: Run multiple independent I/O streams simultaneously with different parameters
- **Verification**: Built-in data verification (md5, crc32, etc.) to validate write integrity
- **Latency percentiles**: Report p50, p90, p95, p99, p99.9 latency statistics
- **Steady-state detection**: Run tests until performance stabilizes (required for enterprise SSD certification)

### Docker Deployment

```bash
# Run FIO in Docker
docker run --rm -v /mnt/test:/data \
  ljishen/fio \
  --name=random-read \
  --ioengine=libaio \
  --iodepth=32 \
  --rw=randread \
  --bs=4k \
  --direct=1 \
  --size=1G \
  --numjobs=4 \
  --runtime=60 \
  --time_based \
  --group_reporting \
  --filename=/data/testfile \
  --output-format=json
```

### Common FIO Workload Profiles

**Sequential Read (Throughput Test)**:
```bash
fio --name=seq-read --ioengine=libaio --iodepth=1 --rw=read \
    --bs=1M --direct=1 --size=10G --numjobs=1 --runtime=60 \
    --group_reporting --filename=/dev/nvme0n1
```

**Random Write (IOPS Test for SSDs)**:
```bash
fio --name=rand-write --ioengine=libaio --iodepth=32 --rw=randwrite \
    --bs=4k --direct=1 --size=4G --numjobs=4 --runtime=120 \
    --group_reporting --filename=/mnt/ssd/testfile
```

**Mixed Workload (Real-World Simulation)**:
```bash
fio --name=mixed --ioengine=libaio --iodepth=16 --rw=randrw \
    --rwmixread=70 --bs=4k-64k --direct=1 --size=8G --numjobs=8 \
    --runtime=300 --group_reporting --filename=/mnt/data/testfile
```

### Interpreting FIO Results

A typical FIO JSON output includes these key metrics:

```
"read": {
  "iops": 45231,       // I/O operations per second
  "bw": 176,            // Bandwidth in MB/s
  "lat_ns": {
    "mean": 2765431,    // Average latency in nanoseconds
    "stddev": 124321,
    "percentile": {
      "50.000000": 2500,    // p50 = 2.5ms
      "95.000000": 4500,    // p95 = 4.5ms
      "99.000000": 8200,    // p99 = 8.2ms
      "99.900000": 15000    // p99.9 = 15ms
    }
  }
}
```

For databases, pay attention to p99 latency — it represents the "worst normal case" your application will experience.

## Sysbench: Database and System-Level Benchmarking

Sysbench started as a MySQL benchmarking tool and evolved into a general-purpose system performance testing framework. While it includes CPU, memory, and mutex tests, its strongest feature remains filesystem and database benchmarking with realistic OLTP workloads.

### Key Capabilities

- **File I/O test**: Sequential and random read/write with configurable file sizes and thread counts
- **OLTP benchmark**: Simulates database workloads with transactions, point selects, range queries
- **CPU benchmark**: Prime number calculation for CPU performance testing
- **Memory benchmark**: Memory read/write throughput testing
- **Thread/mutex benchmark**: Concurrency and locking performance

### Installation

```bash
# Install sysbench on Debian/Ubuntu
apt-get update && apt-get install -y sysbench

# Or use Docker
docker run --rm -v /mnt/test:/data \
  severalnines/sysbench \
  sysbench fileio --file-total-size=10G prepare
```

### Filesystem Benchmarking

```bash
# Prepare test files
sysbench fileio --file-total-size=10G --file-num=64 prepare

# Run random read/write test
sysbench fileio --file-total-size=10G --file-num=64 \
  --file-test-mode=rndrw --time=120 --max-requests=0 \
  --threads=16 run

# Run sequential read test
sysbench fileio --file-total-size=10G --file-num=1 \
  --file-test-mode=seqrd --time=60 --threads=1 run

# Cleanup
sysbench fileio --file-total-size=10G cleanup
```

### OLTP Database Simulation

```bash
# Prepare test database (MySQL example)
sysbench oltp_read_write \
  --db-driver=mysql \
  --mysql-host=localhost \
  --mysql-user=benchuser \
  --mysql-password=benchpass \
  --mysql-db=benchdb \
  --tables=10 \
  --table-size=100000 \
  prepare

# Run OLTP benchmark
sysbench oltp_read_write \
  --db-driver=mysql \
  --mysql-host=localhost \
  --mysql-user=benchuser \
  --mysql-password=benchpass \
  --mysql-db=benchdb \
  --tables=10 \
  --table-size=100000 \
  --threads=16 \
  --time=120 \
  run
```

## Bonnie++: Filesystem Metadata Performance

Bonnie++ focuses on filesystem-level operations that other tools overlook — creating and deleting thousands of files, directory listing performance, and metadata operations per second. This matters because many real-world workloads (mail servers, web caches, container image storage) are metadata-intensive rather than throughput-bound.

### Key Capabilities

- **Sequential output**: Write speed for large files
- **Sequential input**: Read speed for large files  
- **Random seeks**: Random access latency
- **Sequential create**: File creation rate (files per second)
- **Random create**: Creating files in random directories
- **Sequential delete**: File deletion rate
- **Random delete**: Deleting files from random directories

### Installation and Usage

```bash
# Install on Debian/Ubuntu
apt-get update && apt-get install -y bonnie++

# Basic benchmark (2x RAM size for test file)
bonnie++ -d /mnt/test -s 4G -n 100 -m TEST-RUN -r 2G -u root

# Benchmark with CSV output for analysis
bonnie++ -d /mnt/test -s 8G -n 200 -m PRODUCTION-NAS -r 4G \
  -u root -q 2>&1 | bon_csv2html > /var/www/benchmark.html
```

### Understanding Bonnie++ Output

```
Version  1.98   ------Sequential Output------ --Sequential Input- --Random-
              -Per Chr- --Block-- -Rewrite- -Per Chr- --Block-- --Seeks--
Machine    Size K/sec %CP K/sec %CP K/sec %CP K/sec %CP K/sec %CP  /sec %CP
TEST-RUN    4G   512  99 245000  45 189000  38   780  99 312000  42 345.6   8
              ------Sequential Create------ --------Random Create--------
              -Create-- --Read--- -Delete-- -Create-- --Read--- -Delete--
          files  /sec %CP  /sec %CP  /sec %CP  /sec %CP  /sec %CP  /sec %CP
            100 18456  82 55432  95 32189  78 19234  85 58901  97 29876  81
```

The sequential create section shows how many files per second the filesystem can create, read, and delete — crucial metrics for applications that handle many small files.

## Choosing the Right Benchmark

| Scenario | Recommended Tool | Key Metrics |
|----------|-----------------|-------------|
| Database storage evaluation | FIO + Sysbench | IOPS, p99 latency, TPS |
| NAS/SAN procurement | FIO + Bonnie++ | Throughput, metadata ops |
| NVMe SSD validation | FIO (steady-state) | 4K random IOPS, endurance |
| Kubernetes persistent volume test | FIO | Mixed workload IOPS |
| Email server storage sizing | Bonnie++ | Files/sec create/delete |
| Gaming server storage | FIO (low queue depth) | 4K randread QD1 latency |

## Why Self-Host Your Storage Benchmarking?

Cloud providers and storage vendors publish benchmark numbers from ideal conditions — clean drives, no other workloads, optimal configurations. Your production environment shares storage with other tenants, runs on virtualized hardware, and contends with noisy neighbors. Self-hosted benchmarks reflect YOUR reality, not a vendor's marketing sheet.

For DevOps teams managing on-premises storage, regular benchmarking establishes baselines and detects degradation early. A monthly FIO run on each storage node can reveal a failing drive before SMART data reports errors. For more on infrastructure monitoring, see our [self-hosted NTP monitoring guide](../2026-05-11-self-hosted-ntp-monitoring-chrony-exporter-ntpsec-chronyc-dashboard-g/) and [hardware monitoring with IPMI](../2026-05-19-self-hosted-bmc-ipmi-monitoring-freeipmi-vs-ipmitool-vs-openbmc-guide/).

## FAQ

**How long should I run benchmarks for reliable results?**

For quick comparisons, 60 seconds can be sufficient. For production validation, run each test for at least 5 minutes, and preferably until steady-state is reached. Enterprise SSD certification (per SNIA specification) requires running FIO until performance stabilizes — often 30-60 minutes per test.

**Should I use direct I/O or buffered I/O?**

Use direct I/O (`--direct=1` in FIO) for benchmarking raw storage performance. Buffered I/O goes through the Linux page cache, which masks actual disk performance with memory speed. Direct I/O bypasses the cache and measures what the storage device can actually deliver.

**Why do my FIO numbers not match the manufacturer's specs?**

Manufacturers typically quote peak performance under ideal conditions — QD32, 4 jobs, sequential workload, clean drive. Real-world workloads rarely match those parameters. Also, storage performance degrades as drives fill up. Run benchmarks on a drive that's 50-80% full to get realistic production numbers.

**Can these tools damage SSDs?**

All three tools write data during testing. FIO's verify mode writes and reads back, providing wear-level-appropriate stress. For SSD endurance testing, use FIO's steady-state mode which is designed for NAND flash. For production drives, limit write testing to reasonable sizes (1-10 GB) rather than filling the entire drive repeatedly.

**Which tool is best for comparing cloud block storage (EBS, Persistent Disk)?**

FIO with direct I/O and a moderate I/O depth (4-16) provides the most accurate comparison. Cloud storage has variable performance depending on volume size and provisioned IOPS. Run the same FIO job file on each cloud provider to get apples-to-apples comparisons.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Storage Benchmarking: FIO vs Sysbench vs Bonnie++ Performance Testing Guide",
  "description": "Comprehensive guide to open-source storage benchmarking tools. Compare FIO, Sysbench, and Bonnie++ with Docker deployment, real-world workload examples, and result interpretation.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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
