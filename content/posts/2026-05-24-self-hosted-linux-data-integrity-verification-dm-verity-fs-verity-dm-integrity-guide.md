---
title: "Self-Hosted Linux Data Integrity Verification — dm-verity vs fs-verity vs dm-integrity"
date: "2026-05-24"
tags: ["linux-storage", "data-integrity", "dm-verity", "fs-verity", "security"]
draft: false
---

Data integrity verification ensures that stored data has not been tampered with or corrupted. Linux provides three complementary integrity mechanisms: **dm-verity** (block-device verification), **fs-verity** (file-level verification), and **dm-integrity** (sector-level integrity with authentication). This guide compares their architectures, use cases, and deployment patterns for self-hosted servers.

## What Is Data Integrity Verification?

Data integrity verification answers a critical question: **has this data changed since I wrote it?** For self-hosted servers, this protects against:

- **Silent corruption** — Disk bit rot, memory errors, filesystem bugs
- **Tampering** — Unauthorized modifications by attackers or malware
- **Supply chain attacks** — Compromised packages or binaries
- **Hardware failures** — Bad sectors, failing controllers, corrupted writes

Unlike backup verification (which checks backup completeness), integrity verification continuously validates live data against cryptographic hashes computed at write time.

## dm-verity: Block Device Verification

**GitHub**: kernel source (built into Linux 3.7+) | **Stars**: N/A (in-tree)

dm-verity (Device Mapper Verity) provides read-only block device integrity verification. It constructs a Merkle tree of hash values for every block on the device, storing the root hash separately. On every read, the kernel verifies the block's hash chain up to the trusted root.

### Key Features

- **Block-level verification** — Every 4K block is cryptographically verified
- **Merkle tree structure** — Efficient verification with logarithmic overhead
- **Read-only enforcement** — Verity devices are inherently read-only
- **No false positives** — Hardware errors that corrupt data will be detected

### How dm-verity Works

```
Root Hash (trusted)
    |
    +-- Hash Block Level 2
    |       |
    |       +-- Hash Block Level 1
    |               |
    |               +-- Data Blocks (4K each)
```

When reading block N:
1. Read the data block
2. Compute its SHA-256 hash
3. Compare with the stored hash at level 1
4. Continue up the tree until reaching the trusted root hash
5. If any hash mismatches, return I/O error

### Creating a dm-verity Volume

```bash
# 1. Create a backing device (disk image or partition)
dd if=/dev/zero of=backing.img bs=1M count=512

# 2. Write data to the backing device
mkfs.ext4 backing.img
mount -o loop backing.img /mnt/data
cp -r /usr/bin/* /mnt/data/
umount /mnt/data

# 3. Build the verity hash tree
veritysetup format backing.img hash.img

# 4. Activate the verified device
veritysetup create vroot backing.img hash.img   <root-hash>   --hash-algorithm=sha256   --data-block-size=4096   --hash-block-size=4096

# 5. Mount the verified read-only filesystem
mount -o ro /dev/mapper/vroot /mnt/verified
```

### Docker Compose with dm-verity

```yaml
version: "3.8"
services:
  verified-service:
    image: alpine:latest
    volumes:
      - /dev/mapper/vroot:/verified-data:ro
    security_opt:
      - seccomp:unconfined
    command: >
      sh -c "
        # Only read from verified data
        cp /verified-data/config /app/config &&
        exec /app/server
      "
    devices:
      - /dev/mapper/vroot:/dev/mapper/vroot:r
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

## fs-verity: File-Level Integrity

**GitHub**: kernel source (built into Linux 5.4+) | **Stars**: N/A (in-tree)

fs-verity provides per-file integrity verification for ext4, f2fs, and btrfs filesystems. Unlike dm-verity (which verifies entire block devices), fs-verity verifies individual files. Each file has its own Merkle tree and root hash stored as an extended attribute.

### Key Features

- **Per-file verification** — Each file has independent integrity metadata
- **Kernel-enforced** — Verification happens in the VFS layer
- **Supports large files** — Merkle tree scales to multi-GB files
- **Multiple hash algorithms** — SHA-256, SHA-512, and others

### Enabling fs-verity

```bash
# Check if filesystem supports fs-verity
tune2fs -l /dev/sda1 | grep -i verity

# Enable fs-verity on a file
fsverity enable /usr/bin/my-application

# Verify a file's integrity
fsverity measure /usr/bin/my-application

# Output: sha256:abc123def456...  /usr/bin/my-application
```

### Using fs-verity with IMA (Integrity Measurement Architecture)

```bash
# Enable IMA appraisal with fs-verity
echo "appraise_tcb" > /sys/kernel/security/ima/policy

# All fs-verity files will be appraised on access
# Accessing a modified file will be denied
cat /usr/bin/my-application  # Returns EACCES if hash mismatches
```

### Docker Compose with fs-verity

```yaml
version: "3.8"
services:
  fsverity-service:
    image: ubuntu:22.04
    volumes:
      - ./verified-binaries:/usr/local/bin:ro
    security_opt:
      - apparmor:unconfined
    command: >
      sh -c "
        # Verify all binaries before use
        for f in /usr/local/bin/*; do
          fsverity measure "\$f" || exit 1
        done
        exec /usr/local/bin/server
      "
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

## dm-integrity: Sector-Level Authenticated Integrity

**GitHub**: kernel source (built into Linux 4.12+) | **Stars**: N/A (in-tree)

dm-integrity provides authenticated sector-level integrity with optional encryption. Unlike dm-verity (read-only verification), dm-integrity supports read-write devices with per-sector authentication tags (HMAC or MAC).

### Key Features

- **Read-write support** — Unlike dm-verity, supports writes with automatic tag updates
- **Per-sector authentication** — Each sector has a MAC/HMAC tag
- **Optional encryption** — Can be combined with dm-crypt for encrypted integrity
- **Journal support** — Ensures consistency after crashes

### Creating a dm-integrity Volume

```bash
# 1. Create backing device
dd if=/dev/zero of=integrity.img bs=1M count=1024

# 2. Set up dm-integrity
integritysetup format integrity.img

# 3. Activate the integrity device
integritysetup create ivol integrity.img   --integrity-algorithm=hmac-sha256   --integrity-key-file <key-file>   --journal-watermark=50

# 4. Create filesystem on the integrity device
mkfs.ext4 /dev/mapper/ivol

# 5. Mount normally (read-write)
mount /dev/mapper/ivol /mnt/integrity
```

### Docker Compose with dm-integrity

```yaml
version: "3.8"
services:
  integrity-service:
    image: ubuntu:22.04
    volumes:
      - /dev/mapper/ivol:/integrity-data
    security_opt:
      - seccomp:unconfined
    command: >
      sh -c "
        # Service reads and writes to integrity-protected storage
        exec /app/database-server --data-dir /integrity-data
      "
    devices:
      - /dev/mapper/ivol:/dev/mapper/ivol:rw
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

## Comparison: dm-verity vs fs-verity vs dm-integrity

| Feature | dm-verity | fs-verity | dm-integrity |
|---|---|---|---|
| **Granularity** | Block device (4K blocks) | Per-file | Per-sector |
| **Read/Write** | Read-only | Read-only (verification) | Read-write |
| **Hash Storage** | Separate hash device | File extended attributes | Per-sector tags |
| **Tree Structure** | Merkle tree | Merkle tree | Linear tags |
| **Kernel Version** | 3.7+ | 5.4+ | 4.12+ |
| **Filesystem Support** | Any (block-level) | ext4, f2fs, btrfs | Any (block-level) |
| **Encryption** | No (combine with dm-crypt) | No | Optional (with dm-crypt) |
| **Performance Overhead** | ~1-3% reads | ~1-2% reads | ~3-5% reads/writes |
| **Best For** | Verified boot images | Application binary verification | Authenticated storage |

## Choosing the Right Integrity Mechanism

### Use dm-verity When:
- You need to verify **entire filesystem images** (container images, boot partitions)
- The data is **read-only** (OS images, application binaries)
- You want **hardware-independent** verification (works on any filesystem)

### Use fs-verity When:
- You need **per-file** integrity (individual binaries, configuration files)
- The data is on a **supported filesystem** (ext4, f2fs, btrfs)
- You want **flexible granularity** (verify some files, not others)

### Use dm-integrity When:
- You need **read-write** integrity (databases, user data)
- You need **authenticated** integrity (HMAC with a secret key)
- You want to **detect silent corruption** in real-time

## Why Self-Host Data Integrity Verification?

Self-hosted servers often store sensitive data — customer information, application state, financial records. Without integrity verification, silent data corruption or undetected tampering can have serious consequences:

**Regulatory compliance** — Standards like PCI DSS and HIPAA require data integrity controls. dm-verity and fs-verity provide cryptographically verifiable integrity guarantees that satisfy audit requirements.

**Supply chain security** — Verifying that deployed binaries match their expected hashes prevents supply chain attacks. fs-verity ensures that any modification to a verified binary is immediately detected at the kernel level.

**Hardware reliability** — Consumer-grade storage (SSDs, HDDs) experiences bit rot and silent corruption. dm-integrity detects and reports these errors before they propagate to application data.

**Forensic integrity** — For incident response, integrity-verified storage provides a trusted baseline. If dm-verity reports no errors, you can be confident the underlying data has not been modified.

For filesystem encryption, see our [Linux filesystem encryption guide](../2026-05-23-self-hosted-linux-native-filesystem-encryption-fscrypt-vs-ecryptfs-vs-dm-crypt/). For kernel sandboxing, our [Linux sandboxing frameworks comparison](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-seccomp-bubblewrap-guide/) covers complementary security mechanisms.

## FAQ

### What is the difference between dm-verity and fs-verity?

dm-verity verifies entire block devices using a Merkle tree stored on a separate hash device. It operates at the block layer and works with any filesystem. fs-verity verifies individual files, storing the Merkle tree as an extended attribute within the file itself. fs-verity is more flexible (per-file control) but requires filesystem support (ext4, f2fs, btrfs).

### Can I use dm-verity with a read-write filesystem?

No. dm-verity devices are inherently read-only because any write would invalidate the Merkle tree. For read-write integrity, use dm-integrity instead, which supports writes with per-sector authentication tags that are updated automatically.

### Does fs-verity work with Docker containers?

Yes, fs-verity works with Docker containers as long as the underlying filesystem supports it (ext4, f2fs, btrfs). The container's read-only layers can have fs-verity enabled, and the kernel will verify each file access. Note that overlayfs (Docker's default storage driver) does not currently support fs-verity on the overlay layer itself.

### What is the performance overhead of integrity verification?

dm-verity adds approximately 1-3% overhead to read operations (hash verification per block). fs-verity adds 1-2% overhead for file reads. dm-integrity adds 3-5% overhead for both reads and writes (tag computation and verification). For most self-hosted workloads, this overhead is negligible compared to network or application latency.

### Can I combine dm-verity with dm-crypt for encrypted integrity?

Yes. You can stack dm-crypt on top of dm-verity (encrypt first, then verify) or dm-verity on top of dm-crypt (verify first, then decrypt). The recommended approach is dm-crypt on top of dm-verity — verify the encrypted data's integrity before decrypting, which prevents oracle attacks.

### How do I detect tampering with the root hash?

The root hash is the trust anchor for dm-verity and fs-verity. Store it securely: in TPM hardware, on a read-only USB stick, or embedded in the bootloader (for verified boot). If the root hash itself is compromised, the entire verification chain is compromised.

### Is dm-integrity a replacement for backups?

No. dm-integrity detects corruption and tampering but does not prevent data loss. If a sector is corrupted, dm-integrity will detect it and return an I/O error — but the original data is lost. Always combine integrity verification with regular backups for complete data protection.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Data Integrity Verification — dm-verity vs fs-verity vs dm-integrity",
  "description": "Comprehensive comparison of Linux data integrity mechanisms: dm-verity (block verification), fs-verity (file verification), and dm-integrity (authenticated sector integrity) for self-hosted servers.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
