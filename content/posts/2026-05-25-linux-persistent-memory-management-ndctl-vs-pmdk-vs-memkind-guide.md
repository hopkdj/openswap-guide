---
title: "Self-Hosted Linux Persistent Memory Management: ndctl vs PMDK vs memkind"
date: "2026-05-25"
tags: ["linux", "persistent-memory", "ndctl", "pmdk", "memory-management"]
draft: false
---

Persistent memory (PMEM) sits between traditional DRAM and SSD storage — it provides byte-addressable access like RAM while retaining data across power cycles like flash. Managing PMEM on Linux requires specialized tooling. Three projects lead this space: **ndctl** (device-level management), **PMDK** (persistent memory development kit with libraries and tools), and **memkind** (memory allocator for heterogeneous memory systems).

This guide covers how to install, configure, and use each tool for managing persistent memory in self-hosted infrastructure environments.

## What Is Persistent Memory?

Persistent memory modules (Intel Optane DC Persistent Memory, Samsung PMEM) plug into standard DDR4/DDR5 DIMM slots but behave differently from regular RAM. The Linux kernel exposes them through three access modes:

- **Memory mode** — PMEM acts as volatile RAM extension (transparent to applications, no data persistence)
- **App Direct mode** — applications access PMEM directly via memory-mapped files or DAX (Direct Access) filesystems
- **Mixed mode** — some regions in Memory mode, others in App Direct mode

For self-hosted infrastructure, App Direct mode is most interesting because it enables persistent data structures, fast restart recovery, and durable in-memory databases.

## ndctl: Device-Level PMEM Management

**ndctl** (NVDIMM Control) is the primary command-line tool for managing NVDIMM (Non-Volatile DIMM) devices on Linux. It handles namespace creation, region configuration, firmware updates, and health monitoring. Developed by Intel and hosted at `github.com/pmem/ndctl`, it is the foundation tool that all other PMEM software depends on.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y ndctl daxctl
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y ndctl daxctl
```

On Alpine Linux:

```bash
apk add ndctl
```

### Docker Deployment

ndctl requires direct access to NVDIMM devices and sysfs, so it runs best as a host-installed tool. For containerized management:

```yaml
version: "3.8"
services:
  ndctl-monitor:
    image: ubuntu:24.04
    container_name: ndctl-monitor
    privileged: true
    volumes:
      - /sys:/sys:rw
      - /dev:/dev:rw
      - /lib/modules:/lib/modules:ro
      - ./monitor-scripts:/scripts:ro
      - ./ndctl-output:/output
    command: >
      bash -c "
        apt-get update && apt-get install -y ndctl &&
        echo '=== NVDIMM List ===' > /output/ndctl-status.txt &&
        ndctl list --verbose >> /output/ndctl-status.txt &&
        echo '=== Namespace List ===' >> /output/ndctl-status.txt &&
        ndctl list --namespaces >> /output/ndctl-status.txt &&
        echo '=== Health Status ===' >> /output/ndctl-status.txt &&
        ndctl health >> /output/ndctl-status.txt
      "
    restart: "no"
```

### Core Usage Patterns

**List all NVDIMM devices and regions:**

```bash
sudo ndctl list --regions
sudo ndctl list --dimms
```

**Create a persistent namespace in App Direct mode:**

```bash
sudo ndctl create-namespace --mode=fsdax --region=region0
```

This creates a block device (`/dev/pmem0`) that supports DAX (Direct Access), allowing applications to bypass the page cache and access persistent memory directly.

**Create a raw (sector) namespace for traditional block access:**

```bash
sudo ndctl create-namespace --mode=sector --region=region0 --size=100G
```

**Create a device-dax namespace for character device access:**

```bash
sudo ndctl create-namespace --mode=devdax --region=region0
```

**Monitor NVDIMM health:**

```bash
sudo ndctl list --dimms --health
```

**Update NVDIMM firmware:**

```bash
sudo ndctl update-firmware /dev/nmem0
```

**Destroy a namespace:**

```bash
sudo ndctl destroy-namespace namespace0.0
```

### Strengths and Weaknesses

| Aspect | Details |
|--------|---------|
| **Scope** | Device-level management (regions, namespaces, DIMMs) |
| **Application Support** | None — purely infrastructure tool |
| **DAX Support** | Yes — creates DAX-enabled block and character devices |
| **Health Monitoring** | Yes — temperature, SMART data, error counts |
| **Firmware Updates** | Yes — in-place firmware flashing |
| **Dependencies** | Linux kernel with NVDIMM support (4.2+) |

## PMDK: Persistent Memory Development Kit

**PMDK** (Persistent Memory Development Kit) is a collection of libraries and tools for building applications that use persistent memory. It includes `libpmem` (core PMEM access), `libpmemobj` (transactional object store), `libpmemlog` (persistent log), `libpmemblk` (persistent block store), and various utilities like `pmemcheck` and `pmempool`.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y libpmem-dev libpmemobj-dev libpmemlog-dev libpmemblk-dev pmempool
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y libpmem-devel libpmemobj-devel pmdk-tools
```

Build from source:

```bash
git clone https://github.com/pmem/pmdk.git
cd pmdk
make -j$(nproc)
sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  pmdk-app:
    image: ubuntu:24.04
    container_name: pmdk-demo
    privileged: true
    volumes:
      - /dev/dax0.0:/dev/dax0.0
      - /dev/pmem0:/dev/pmem0
      - /mnt/pmem:/mnt/pmem
      - ./pmdk-app:/app:ro
    environment:
      - PMEM_DIR=/mnt/pmem
    command: >
      bash -c "
        apt-get update && apt-get install -y libpmemobj-dev libpmem-dev &&
        mkfs.ext4 -b 4096 -F /dev/pmem0 &&
        mount -o dax /dev/pmem0 /mnt/pmem &&
        cd /app && make && ./pmdk-demo
      "
    restart: "no"
```

### Core Usage Patterns

**Write directly to persistent memory:**

```c
#include <libpmem.h>
#include <stdio.h>
#include <string.h>

int main() {
    const char *path = "/mnt/pmem/test.dat";
    size_t len = 4096;
    
    /* Check if path is on a PMEM-aware filesystem */
    if (!pmem_is_pmem(path, &len)) {
        printf("Path is not on persistent memory
");
        return 1;
    }
    
    /* Memory-map the file */
    void *addr = pmem_map_file(path, len,
        PMEM_FILE_CREATE|PMEM_FILE_EXCL, 0666, &len, NULL);
    if (addr == NULL) {
        perror("pmem_map_file");
        return 1;
    }
    
    /* Write data with persistence guarantee */
    const char *message = "Hello from persistent memory!";
    pmem_memcpy_persist(addr, message, strlen(message) + 1);
    
    /* Unmap when done */
    pmem_unmap(addr, len);
    return 0;
}
```

Compile and run:
```bash
gcc -o pmem-write pmem-write.c -lpmem
./pmem-write
```

**Use the persistent object store:**

```c
#include <libpmemobj.h>
#include <stdio.h>

#define LAYOUT_NAME "demo_layout"

POBJ_LAYOUT_BEGIN(demo);
    POBJ_LAYOUT_ROOT(demo, struct my_root) {
        int64_t counter;
        char message[256];
    };
POBJ_LAYOUT_END(demo);

int main() {
    PMEMobjpool *pop = pmemobj_create("/mnt/pmem/pool.obj",
        POBJ_LAYOUT_NAME(demo), PMEMOBJ_MIN_POOL, 0666);
    if (pop == NULL) {
        perror("pmemobj_create");
        return 1;
    }
    
    TOID(struct my_root) root = POBJ_ROOT(pop, struct my_root);
    D_RW(root)->counter++;
    pmemobj_persist(pop, &D_RO(root)->counter, sizeof(int64_t));
    
    pmemobj_close(pop);
    return 0;
}
```

### Strengths and Weaknesses

| Aspect | Details |
|--------|---------|
| **Scope** | Application-level (libraries for building PMEM-aware apps) |
| **Transactions** | Yes — libpmemobj provides ACID-like transactions |
| **Language Support** | C/C++ (primary), Python bindings available |
| **Data Structures** | Persistent linked lists, trees, hash maps |
| **Debugging** | pmemcheck (Valgrind-like tool for PMEM bugs) |
| **Learning Curve** | Steep — requires understanding of PMEM programming model |

## memkind: Memory Allocator for Heterogeneous Memory

**memkind** is a user-extensible heap manager optimized for NUMA architectures and heterogeneous memory systems including persistent memory. It provides a `malloc`-compatible API that lets applications allocate memory from specific memory types (DRAM, PMEM, HBM) without changing application code.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y libmemkind-dev memkind
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y memkind-devel
```

Build from source:

```bash
git clone https://github.com/memkind/memkind.git
cd memkind
./build.sh -h
sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  memkind-demo:
    image: ubuntu:24.04
    container_name: memkind-demo
    privileged: true
    volumes:
      - /dev/dax0.0:/dev/dax0.0
      - /sys:/sys:ro
      - ./memkind-app:/app:ro
    command: >
      bash -c "
        apt-get update && apt-get install -y libmemkind-dev &&
        cd /app && make && LD_PRELOAD=libmemkind.so ./memkind-app
      "
    restart: "no"
```

### Core Usage Patterns

**Use memkind API directly:**

```c
#include <memkind.h>
#include <stdio.h>
#include <string.h>

int main() {
    /* Initialize memkind with default DAX path */
    int err = memkind_create_pmem("/mnt/pmem", 0, NULL);
    if (err != 0) {
        fprintf(stderr, "memkind_create_pmem failed: %d
", err);
        return 1;
    }
    
    /* Allocate from persistent memory */
    struct memkind *pmem_kind = MEMKIND_DAX_KMEM;
    char *data = memkind_malloc(pmem_kind, 1024);
    if (data == NULL) {
        perror("memkind_malloc");
        return 1;
    }
    
    strcpy(data, "Data allocated in persistent memory");
    printf("Allocated at: %p
", (void *)data);
    
    /* Free when done */
    memkind_free(pmem_kind, data);
    return 0;
}
```

**Use LD_PRELOAD for drop-in replacement:**

```bash
# Allocate all malloc() calls from PMEM
LD_PRELOAD=libmemkind.so ./your-application

# Use specific memkind allocator
MEMKIND_INSTANTIATION=PMEM LD_PRELOAD=libmemkind.so ./your-application
```

### Strengths and Weaknesses

| Aspect | Details |
|--------|---------|
| **Scope** | Memory allocation layer (drop-in malloc replacement) |
| **API Compatibility** | malloc/free compatible — minimal code changes needed |
| **NUMA Awareness** | Yes — optimized for NUMA-aware allocation |
| **PMEM Support** | Yes — via MEMKIND_DAX_KMEM kind |
| **HBM Support** | Yes — high-bandwidth memory allocation |
| **Transaction Support** | No — pure allocator, no persistence guarantees |

## Comparison Table

| Feature | ndctl | PMDK | memkind |
|---------|-------|------|---------|
| **Primary Role** | Device management | Application libraries | Memory allocator |
| **Abstraction Level** | Lowest (kernel devices) | Mid (data structures) | Highest (malloc API) |
| **Transactions** | No | Yes (libpmemobj) | No |
| **DAX Support** | Yes (creates DAX devices) | Yes (uses DAX devices) | Yes (allocates on DAX) |
| **Language** | C CLI tool | C/C++ libraries | C library |
| **Drop-in Usage** | N/A | No | Yes (LD_PRELOAD) |
| **Health Monitoring** | Yes (SMART, temperature) | No | No |
| **Namespace Mgmt** | Yes (create/destroy) | No | No |
| **GitHub Stars** | 700+ | 1,300+ | 800+ |
| **Best For** | Sysadmins managing PMEM hardware | Developers building PMEM apps | Apps needing PMEM with zero code changes |

## Choosing the Right PMEM Tool

These tools serve different roles in the PMEM stack — you will typically use **all three together**:

1. **ndctl** provisions namespaces and creates DAX-enabled devices (`/dev/pmem0`)
2. **PMDK** provides libraries for applications that need transactional persistence on PMEM
3. **memkind** provides a drop-in allocator for applications that want PMEM benefits without code changes

**Choose ndctl when:**
- You need to create, configure, or destroy PMEM namespaces
- You want to monitor NVDIMM health and update firmware
- You are provisioning DAX block or character devices for applications
- You are the system administrator managing the physical PMEM hardware

**Choose PMDK when:**
- You are developing applications that require transactional persistence
- You need durable data structures (persistent hash maps, logs, object stores)
- You want fine-grained control over PMEM access patterns
- You can modify application source code to use PMDK libraries

**Choose memkind when:**
- You want to use PMEM without modifying application source code
- Your application uses `malloc`/`free` and you want PMEM-backed allocation
- You need NUMA-aware memory allocation on heterogeneous systems
- You want a quick way to test PMEM benefits before committing to PMDK integration

## Why Self-Host Persistent Memory Infrastructure

Running persistent memory management tools on your own servers delivers unique advantages for data-intensive workloads:

**Sub-microsecond persistence.** PMEM provides latency closer to DRAM (~100-300ns) than NVMe SSD (~10-50us). For self-hosted databases, key-value stores, and transaction logs, this means durable writes that are 100x faster than disk-backed alternatives.

**Crash-consistent data structures.** With PMDK's transactional object store, your data structures survive power failures in a consistent state. No recovery journals, no replay logs — the data is simply there when the system boots. This eliminates the complex crash-recovery logic that traditional databases must implement.

**Reduced infrastructure complexity.** Persistent memory eliminates the need for separate caching layers (Redis, Memcached) for many workloads. Data lives in addressable memory and persists across reboots, combining the speed of in-memory storage with the durability of disk.

**Data locality and compliance.** For regulated industries (finance, healthcare, government), keeping sensitive data on-premises in PMEM — never written to external storage or transmitted over networks — simplifies compliance audits and reduces the attack surface.

**Cost efficiency at scale.** PMEM costs more per GB than DRAM but less than enterprise NVMe SSDs. For workloads that need both speed and persistence, PMEM can replace the combination of DRAM + battery-backed RAID, reducing total infrastructure cost by 30-50%.

For related memory optimization topics, see our [Linux HugePages management guide](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) and [Linux compressed swap management](../2026-05-29-self-hosted-linux-compressed-swap-management-zram-generator-systemd-swap-zramd-guide/). For kernel-level tracing of memory operations, our [kernel dynamic tracing guide](../2026-05-25-linux-kernel-dynamic-tracing-trace-cmd-vs-systemtap-vs-perf-probe-guide/) covers tools to monitor PMEM access patterns.

## FAQ

### What hardware do I need for persistent memory?

You need a server platform that supports NVDIMM (Non-Volatile DIMM) modules. Intel Optane DC Persistent Memory (100/200/300 series) was the most common option, though Intel discontinued the product line in 2025. Samsung and SK Hynix also produce PMEM modules. Your motherboard must support NVDIMM in the BIOS/UEFI, and the Linux kernel must be 4.2 or newer. For testing without hardware, PMDK provides a simulation mode (`libpmemobj` with `PMEM_IS_PMEM_FORCE=1`) that emulates PMEM using regular files.

### Can I use persistent memory with Docker containers?

Yes. The key requirement is exposing the PMEM device (`/dev/pmem0` or `/dev/dax0.0`) to the container and mounting a DAX-enabled filesystem inside it. Use `--privileged` or specific device capabilities (`--device=/dev/pmem0`). The Docker Compose examples in this guide show the full configuration. Note that PMEM-aware containers need the PMDK or memkind libraries installed inside the container image.

### What filesystems support DAX (Direct Access)?

The main DAX-capable filesystems on Linux are **ext4** (with the `dax` mount option), **xfs** (with `dax` or `dax=always`), and **xfs** with reflink support. The `dax` mount option bypasses the page cache, allowing applications to access PMEM directly through memory-mapped files. Without DAX, PMEM data goes through the kernel page cache, adding latency and losing the direct-access advantage.

### Is persistent memory the same as NVDIMM?

NVDIMM is the hardware form factor (a DIMM module with non-volatile storage). Persistent memory is the general concept — NVDIMM is one implementation. Other PMEM implementations include M.2/NVMe devices with persistent memory semantics and CXL-attached memory. The ndctl tool manages NVDIMM devices specifically.

### How does PMEM compare to battery-backed RAM?

Battery-backed RAM (BBU) uses regular DRAM with a battery that writes contents to flash on power loss. PMEM is inherently persistent — it does not need a battery because the memory cells retain data without power. PMEM is cheaper, more reliable, and faster to recover from power loss than BBU solutions.

### What happens to PMEM data during a kernel crash?

Data in PMEM App Direct mode survives kernel crashes and power failures because the persistence is handled by the hardware, not the OS. However, any in-flight writes (data in CPU caches not yet flushed to PMEM) may be lost. PMDK's `pmem_persist()` and `pmem_memcpy_persist()` functions ensure data is flushed through all cache levels to the persistent domain before returning.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Persistent Memory Management: ndctl vs PMDK vs memkind",
  "description": "Compare three persistent memory management tools on Linux: ndctl (device management), PMDK (application libraries), and memkind (memory allocator). Includes Docker Compose configs and C code examples.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
