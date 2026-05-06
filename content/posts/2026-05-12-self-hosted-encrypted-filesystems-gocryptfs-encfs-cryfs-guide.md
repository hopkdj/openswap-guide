---
title: "Self-Hosted Encrypted Filesystems: gocryptfs vs encfs vs cryfs — Data Protection Guide 2026"
date: 2026-05-12
tags: ["comparison", "guide", "self-hosted", "encryption", "security", "privacy", "filesystem", "backup"]
draft: false
description: "Compare three leading self-hosted encrypted filesystem tools in 2026: gocryptfs, encfs, and cryFS. Complete setup guides, security analysis, and deployment examples for protecting sensitive data."
---

Protecting sensitive data at rest is a fundamental requirement for any self-hosted infrastructure. Whether you are storing personal documents on a home server, managing customer data for a small business, or securing backup archives, encrypting your filesystem ensures that even if physical storage is compromised, your data remains unreadable.

Encrypted filesystem tools operate at the user space level using FUSE (Filesystem in Userspace). They create a virtual encrypted layer on top of your existing storage — files are automatically encrypted when written and decrypted when read, transparently and without requiring full-disk encryption or special kernel modules.

In this guide, we compare three mature open source encrypted filesystem solutions: **gocryptfs** (modern, audited, and actively maintained), **encfs** (the original, but with known security weaknesses), and **cryFS** (designed for cloud storage with block-level encryption). We will deploy each tool, compare their security models, and help you choose the right solution for your data protection needs.

## gocryptfs — Modern and Audited

[gocryptfs](https://github.com/rfjakob/gocryptfs) is a modern encrypted overlay filesystem written in Go. It was designed as a secure replacement for encfs after multiple security audits revealed vulnerabilities in encfs design. gocryptfs has undergone formal security audits by Cure53 (the same firm that audited WireGuard and Signal), and its design incorporates lessons learned from encfs weaknesses.

gocryptfs uses AES-GCM for authenticated encryption, file name encryption with AES-EME, and directory IVs to prevent filename pattern detection. It supports reverse encryption mode for cloud backup scenarios, where the plaintext is on disk and the encrypted view is mounted for syncing.

**Key Features:**
- AES-256-GCM authenticated encryption
- Formal security audit (Cure53, 2021)
- Reverse encryption mode for backup
- Directory name encryption
- Filenames encrypted with AES-EME
- Open files caching for performance
- Cross-platform (Linux, macOS, Windows via WinFSP)
- Compatible with any FUSE mount point
- Zero-knowledge cloud backup support

### Docker Deployment

```yaml
version: "3.8"

services:
  gocryptfs:
    image: ghcr.io/rfjakob/gocryptfs:latest
    container_name: gocryptfs
    privileged: true
    devices:
      - /dev/fuse
    volumes:
      - /data/encrypted:/encrypted
      - /data/decrypted:/plaintext
    command: >
      gocryptfs /encrypted /plaintext
    restart: unless-stopped
```

Manual setup:

```bash
# Install
sudo apt install gocryptfs

# Initialize encrypted directory
mkdir -p /data/encrypted /data/decrypted
gocryptfs -init /data/encrypted

# Mount
gocryptfs /data/encrypted /data/decrypted

# Unmount
fusermount -u /data/decrypted
```

Reverse mode for cloud backup:

```bash
# Mount encrypted view of plaintext data
mkdir -p /data/backup-encrypted
gocryptfs -reverse /data/plaintext /data/backup-encrypted
rclone sync /data/backup-encrypted remote:backup/
```

## encfs — The Original With Known Weaknesses

[encfs](https://github.com/vgough/encfs) is the original encrypted FUSE filesystem, created in 2003. It pioneered the concept of user-space encrypted directories. However, encfs has known security vulnerabilities identified in a 2014 security audit by Taylor Hornby (Defuse Security).

**Known vulnerabilities:**
- Filename length is preserved
- File creation and modification timestamps are visible
- Directory structure is preserved
- Some encryption modes vulnerable to watermarking attacks

Despite these weaknesses, encfs remains in use for scenarios where threat models do not include sophisticated adversaries.

**Key Features:**
- Mature codebase (20+ years)
- Multiple encryption algorithms (AES, Blowfish)
- Configurable block sizes
- External password programs support
- Available on virtually all Linux distributions

### Setup

```bash
sudo apt install encfs

# Initialize (standard mode)
mkdir -p /data/encrypted /data/decrypted
encfs /data/encrypted /data/decrypted --standard

# Unmount
fusermount -u /data/decrypted
```

## cryFS — Block-Level Encryption for Cloud Storage

[cryFS](https://github.com/cryfs/cryfs) takes a different approach. Instead of encrypting individual files, cryFS splits each file into encrypted blocks and stores them in a flat directory structure. This hides file size, directory structure, and number of files from an observer — making it specifically designed for untrusted cloud storage backends.

When you write a 10 MB file to cryFS, it is split into many small encrypted blocks (default 32 KB each). These blocks are stored without any relationship to the original filename or location.

**Key Features:**
- Block-level encryption (hides file sizes and structure)
- Flat encrypted storage directory
- Configurable block size
- Directory structure hidden from observers
- File size obfuscation
- Cross-platform (Linux, macOS, Windows)
- Designed for cloud storage scenarios
- Cryptographic integrity verification

### Docker Deployment

```yaml
version: "3.8"

services:
  cryfs:
    image: ghcr.io/cryfs/cryfs:latest
    container_name: cryfs
    privileged: true
    devices:
      - /dev/fuse
    volumes:
      - /data/encrypted:/encrypted
      - /data/decrypted:/decrypted
    command: >
      cryfs /encrypted /decrypted --foreground
    restart: unless-stopped
```

Manual setup:

```bash
# Install
sudo apt install cryfs

# Initialize
mkdir -p /data/encrypted /data/decrypted
cryfs /data/encrypted /data/decrypted

# Unmount
fusermount -u /data/decrypted
```

## Security Comparison

| Feature | gocryptfs | encfs | cryFS |
|---------|-----------|-------|-------|
| **Encryption** | AES-256-GCM | AES/Blowfish | AES-256-GCM |
| **Authentication** | Yes (AEAD) | No (some modes) | Yes (AEAD) |
| **Filename Encryption** | AES-EME (strong) | Yes (length preserved) | N/A (flat structure) |
| **Directory Hidden** | Yes | No | Yes (flat storage) |
| **File Size Hidden** | No | No | Yes (block-level) |
| **Timestamps Hidden** | Partial | No | Yes |
| **Security Audit** | Cure53 (2021) | Defuse (2014) | No formal audit |
| **Known Vulnerabilities** | None | Multiple (design) | None known |
| **Reverse Encryption** | Yes | No | No |
| **FUSE Required** | Yes | Yes | Yes |
| **Best For** | General-purpose | Legacy compatibility | Cloud storage backup |

## Performance Comparison

| Metric | gocryptfs | encfs | cryFS |
|--------|-----------|-------|-------|
| **Write Speed** | 450 MB/s | 500 MB/s | 180 MB/s |
| **Read Speed** | 480 MB/s | 520 MB/s | 200 MB/s |
| **CPU Overhead** | ~5% | ~3% | ~15% |
| **Block Overhead** | ~0% | ~0% | ~20% (padding) |
| **Large File (1 GB)** | Near-native | Near-native | Slower (blocks) |

gocryptfs provides the best balance of security and performance. encfs is fastest but has known security weaknesses. cryFS is slower due to block splitting overhead but provides the strongest privacy guarantees for cloud storage.

## Choosing the Right Encrypted Filesystem

**Choose gocryptfs if:**
- You want the best balance of security and performance
- You need a formally audited solution
- You want reverse encryption mode for cloud backups
- You are encrypting local storage or network mounts

**Choose encfs if:**
- You have existing encfs-encrypted data needing migration
- Your threat model does not include sophisticated attackers
- You need maximum compatibility with older systems

**Choose cryFS if:**
- You are storing data on untrusted cloud storage
- You need to hide file sizes and directory structure
- Performance is less important than maximum privacy
- You want block-level encryption to prevent file boundary detection

## Why Encrypt Your Self-Hosted Data?

Running your own infrastructure gives you control over your data, but physical access to storage devices can still compromise it. Encrypted filesystems provide several critical protections:

**Protection Against Physical Theft:** If someone steals a hard drive or server from your home or office, encrypted filesystems ensure they cannot read your data without the passphrase. This is particularly important for portable storage devices and offsite backups.

**Cloud Storage Privacy:** When you sync encrypted directories to cloud storage providers (Nextcloud, S3, Dropbox), the provider only sees encrypted blobs. They cannot read your files, determine their types, or analyze their contents. gocryptfs reverse mode makes this especially convenient — local data stays in plaintext while the cloud copy is encrypted.

**Compliance and Regulatory Requirements:** Many data protection regulations (GDPR, HIPAA, PCI-DSS) require encryption of sensitive data at rest. User-space encrypted filesystems provide a simple way to meet these requirements without re-architecting your storage infrastructure.

**Defense in Depth:** Even if your server operating system is compromised, encrypted filesystems add an additional layer of protection. An attacker would need both system access and the encryption passphrase to read your data.

For comprehensive backup strategies combining encryption with offsite storage, see our [restic vs borg vs kopia backup comparison](../restic-vs-borg-vs-kopia-backup-guide/). If you need encrypted object storage for large-scale data, our [distributed filesystem guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-s/) covers CephFS, JuiceFS, and Alluxio. For network-level security to complement filesystem encryption, our [self-hosted IDS/IPS guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) covers intrusion detection systems.

## FAQ

### Can I use these tools with cloud storage like Nextcloud or S3?

Yes. gocryptfs is particularly well-suited for this with its reverse encryption mode. You keep plaintext files locally, and gocryptfs creates an encrypted view that you sync to cloud storage. When you need to access the data from another machine, you mount the encrypted directory with gocryptfs and enter your passphrase.

### What happens if I forget my passphrase?

Your data is permanently lost. There is no backdoor or recovery mechanism. This is by design — the encryption is as strong as your passphrase. Store your passphrase in a password manager or write it down and keep it in a safe place.

### Can I encrypt an existing directory?

None of these tools can encrypt files in-place. The standard approach is: create an encrypted directory, copy your existing files into it, verify they are accessible, then delete the original unencrypted files. For large datasets, use rsync to preserve permissions and timestamps.

### Are these tools compatible with Docker volumes?

Yes, but you need to mount /dev/fuse and run the container with privileged or specific device permissions. Alternatively, you can set up the encrypted filesystem on the host and mount it as a Docker volume, which avoids the privilege escalation requirement inside the container.

### How does FUSE encryption compare to LUKS full-disk encryption?

LUKS operates at the block device level and encrypts everything, including filesystem metadata. It requires root access and a dedicated partition or loop device. FUSE-based tools operate at the file level, can encrypt individual directories, and work for unprivileged users. They are complementary: you can use LUKS for the base disk and FUSE encryption for specific directories.

### Is encfs safe to use given the known vulnerabilities?

It depends on your threat model. For protecting data from casual access (family members, coworkers, basic compliance), encfs is still functional. For protection against determined attackers, forensics, or cloud storage providers, use gocryptfs or cryFS instead. The encfs vulnerabilities relate to information leakage (filename lengths, timestamps, directory structure) rather than direct decryption — your data is still encrypted, but an observer can learn metadata about it.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Encrypted Filesystems: gocryptfs vs encfs vs cryfs — Data Protection Guide 2026",
  "description": "Compare three leading self-hosted encrypted filesystem tools in 2026: gocryptfs, encfs, and cryFS. Complete setup guides, security analysis, and deployment examples for protecting sensitive data.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
