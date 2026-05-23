---
title: "Self-Hosted Linux Native Filesystem Encryption: fscrypt vs eCryptfs vs dm-crypt"
date: "2026-05-23"
tags: ["linux", "encryption", "security", "filesystem", "fscrypt", "dm-crypt"]
draft: false
---

Filesystem encryption is a cornerstone of self-hosted data security. Whether you are protecting sensitive configuration files, encrypting home directories, or securing database volumes, choosing the right encryption approach matters. Linux offers three primary filesystem encryption technologies: **fscrypt** (per-directory native encryption), **eCryptfs** (stacked per-file encryption), and **dm-crypt/LUKS** (full block-device encryption).

This guide compares these three approaches so you can choose the right tool for your self-hosted infrastructure.

## Understanding Linux Filesystem Encryption Layers

Linux provides encryption at three different layers of the storage stack:

- **Block-level (dm-crypt/LUKS)** — encrypts the entire block device before the filesystem is created. Everything on the device is encrypted, including filenames, metadata, and free space.
- **Per-directory (fscrypt)** — encrypts individual directories within an ext4 or f2fs filesystem. Files in unencrypted directories remain readable normally.
- **Per-file stacked (eCryptfs)** — a stacked filesystem that encrypts individual files on top of any underlying filesystem. Each file is encrypted independently.

## Comparison Table: Linux Filesystem Encryption

| Feature | fscrypt | eCryptfs | dm-crypt/LUKS |
|---------|---------|----------|---------------|
| **Encryption Level** | Per-directory | Per-file | Full block device |
| **Filesystem Support** | ext4, f2fs | Any (stacked) | Any (block-level) |
| **Kernel Support** | 4.1+ (ext4), 5.1+ (f2fs) | 2.6.19+ | 2.6+ |
| **Performance Overhead** | ~3-5% | ~15-30% | ~2-8% |
| **Filename Encryption** | Yes | Yes | Yes (entire device) |
| **Granularity** | Directory-level | File-level | Device-level |
| **Docker Compatible** | Yes (with volume mount) | Yes | Yes (via loop device) |
| **Key Management** | Linux keyring, PAM | Passphrase, wrapped keys | LUKS header, keyslots |
| **Recovery** | Per-directory key recovery | Per-file key recovery | Full device key recovery |
| **Cloud VM Friendly** | Yes (directory-only) | Yes (file-level) | Yes (full disk) |
| **Project Stars** | 1,200+ (google/fscrypt) | Kernel (builtin) | 2,600+ (cryptsetup) |

## fscrypt: Per-Directory Native Encryption

[fscrypt](https://github.com/google/fscrypt) is Google's native filesystem encryption framework, developed for Android and Chrome OS but available on any Linux system running ext4 or f2fs. It encrypts at the directory level, meaning you can selectively encrypt specific directories while leaving others unencrypted.

### Installation

```bash
# Debian/Ubuntu
sudo apt install fscrypt

# Arch Linux
sudo pacman -S fscrypt

# Fedora
sudo dnf install fscrypt
```

### Setup and Usage

Initialize fscrypt on your filesystem:

```bash
# Enable fscrypt on the filesystem
sudo fscrypt setup
sudo fscrypt setup /mnt/data

# Create an encrypted directory
mkdir /mnt/data/encrypted-data
fscrypt encrypt /mnt/data/encrypted-data
```

After encryption, files written to the directory are automatically encrypted. The encryption keys are managed through the Linux kernel keyring and can be tied to PAM for automatic unlocking at login:

```bash
# Unlock a directory
fscrypt unlock /mnt/data/encrypted-data

# Lock it again
fscrypt lock /mnt/data/encrypted-data
```

### Docker Integration

fscrypt works well with Docker volumes when the underlying filesystem supports it:

```yaml
version: "3.8"
services:
  encrypted-app:
    image: nginx:alpine
    volumes:
      - /mnt/data/encrypted-data/app:/usr/share/nginx/html:ro
    restart: unless-stopped
```

The Docker container reads the decrypted files normally — fscrypt handles the encryption transparently at the filesystem layer.

## eCryptfs: Stacked Per-File Encryption

eCryptfs is a stacked filesystem that encrypts individual files on top of any underlying filesystem. Unlike fscrypt, it does not require specific filesystem support — it works on ext4, XFS, Btrfs, and any other Linux filesystem.

### Installation

```bash
# Debian/Ubuntu
sudo apt install ecryptfs-utils

# Arch Linux
sudo pacman -S ecryptfs-utils

# Fedora
sudo dnf install ecryptfs-utils
```

### Setup and Usage

Mount an eCryptfs filesystem:

```bash
# Create the underlying and mount directories
mkdir -p ~/.encrypted-raw ~/.encrypted

# Mount eCryptfs
sudo mount -t ecryptfs ~/.encrypted-raw ~/.encrypted

# During setup, you will be prompted for:
# - Passphrase (or select OpenSSL key generation)
# - Cipher (aes recommended)
# - Key bytes (32 for 256-bit)
# - Plaintext passthrough (yes/no)
# - Filename encryption (yes)
```

To make the mount persistent:

```bash
# /etc/fstab
/home/user/.encrypted-raw /home/user/.encrypted ecryptfs   rw,relatime,ecryptfs_sig=SIG,ecryptfs_cipher=aes,  ecryptfs_key_bytes=32,ecryptfs_enable_filename_crypto=y 0 0
```

Each file is encrypted with its own File Encryption Key (FEK), which is then wrapped by the File Encryption Key Encryption Key (FEKEK). This means individual files can be copied or backed up independently — a significant advantage for cloud storage scenarios.

## dm-crypt/LUKS: Full Block-Device Encryption

[cryptsetup](https://gitlab.com/cryptsetup/cryptsetup) with LUKS (Linux Unified Key Setup) provides full block-device encryption. It encrypts everything on the device — filesystem metadata, filenames, free space, and all data — making it the strongest option against physical theft.

### Installation

```bash
# Usually pre-installed on most distributions
sudo apt install cryptsetup-bin   # Debian/Ubuntu
sudo pacman -S cryptsetup          # Arch Linux
sudo dnf install cryptsetup        # Fedora
```

### Setup and Usage

Create an encrypted volume:

```bash
# Create a LUKS container on a block device or file
# Using a file as a loop device (useful for Docker volumes):
dd if=/dev/zero of=/var/lib/encrypted-volume.img bs=1M count=1024
sudo cryptsetup luksFormat /var/lib/encrypted-volume.img

# Open the LUKS container
sudo cryptsetup luksOpen /var/lib/encrypted-volume.img encrypted-vol

# Format and mount the decrypted device
sudo mkfs.ext4 /dev/mapper/encrypted-vol
sudo mkdir -p /mnt/encrypted
sudo mount /dev/mapper/encrypted-vol /mnt/encrypted
```

### LUKS Key Management

LUKS supports up to 8 keyslots, allowing multiple passphrases or keyfiles:

```bash
# Add a keyfile
sudo cryptsetup luksAddKey /dev/sdb1 /path/to/keyfile

# Add a secondary passphrase
sudo cryptsetup luksAddKey /dev/sdb1

# View keyslot status
sudo cryptsetup luksDump /dev/sdb1

# Remove a keyslot
sudo cryptsetup luksKillSlot /dev/sdb1 2
```

### Docker Integration with LUKS

Use LUKS-encrypted volumes with Docker Compose:

```yaml
version: "3.8"
services:
  encrypted-db:
    image: postgres:16-alpine
    volumes:
      - encrypted-pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: secure-password
    restart: unless-stopped

volumes:
  encrypted-pgdata:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/encrypted/postgres
```

## Why Self-Host with Filesystem Encryption?

Self-hosting gives you complete control over encryption keys, algorithms, and key management — unlike cloud storage providers where the provider holds the keys. With filesystem-level encryption, your data remains protected even if physical drives are stolen or decommissioned improperly.

For home labs and small businesses, per-directory encryption (fscrypt) is ideal for protecting specific sensitive directories (database files, configuration, secrets) while keeping the rest of the filesystem accessible. For multi-tenant environments, per-file encryption (eCryptfs) allows each user's files to be encrypted with different keys. For maximum security, full-disk encryption (dm-crypt/LUKS) protects against all physical access attacks.


### Performance Considerations for Encrypted Storage

When selecting an encryption method for your self-hosted infrastructure, consider the I/O patterns of your workloads. Database servers performing random read/write operations benefit from block-level encryption (dm-crypt/LUKS) because the encryption overhead is spread across the entire device. File servers serving large sequential reads (media files, backups) can use per-directory encryption (fscrypt) with negligible performance impact. Web servers with many small files may see higher overhead from per-file encryption (eCryptfs) due to individual file key management.

For containerized workloads, the encryption layer should be positioned below the container runtime. This means setting up LUKS on the host block device or enabling fscrypt on the host filesystem before Docker creates its overlay filesystems. Encrypting at the container level (inside the container) adds an unnecessary layer of complexity and reduces performance.

### Key Management Best Practices

Regardless of which encryption method you choose, key management is critical. Store backup keys offline on encrypted USB drives or in a hardware security module (HSM). For LUKS, maintain at least two active keyslots with different passphrases. For fscrypt, export the policy keys and store them securely. Never store encryption keys on the same physical device as the encrypted data — if the device is stolen, both the data and the key are compromised.

For related reading, see our guide on [secrets encryption for Git repositories](../2026-04-23-mozilla-sops-vs-git-crypt-vs-age-self-hosted-secrets-encryption-git-guide-2026/) and [email encryption solutions](../2026-05-02-self-hosted-email-encryption-pgp-smime-solutions-guide/). For kernel-level security auditing, check our [kernel security guide](../2026-05-23-self-hosted-linux-kernel-security-auditing-kconfig-hardened-check-checksec/).


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Native Filesystem Encryption: fscrypt vs eCryptfs vs dm-crypt",
  "description": "Compare Linux filesystem encryption methods: fscrypt per-directory encryption, eCryptfs per-file stacked encryption, and dm-crypt/LUKS full block-device encryption. Includes Docker integration and key management.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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

### Which encryption method should I choose for my self-hosted server?

For most self-hosted servers, **dm-crypt/LUKS** is the best default choice — it encrypts everything with minimal performance overhead (~2-8%). Use **fscrypt** when you need selective encryption (encrypt only specific directories while keeping others accessible). Use **eCryptfs** when you need per-file encryption with independent keys for each file (useful for cloud backup scenarios).

### Does fscrypt work with Docker containers?

Yes. fscrypt operates at the filesystem layer, so Docker containers read and write to the directories normally. The encryption is transparent — unlocked directories appear as regular filesystem paths to containers. Just ensure the directories are unlocked before starting your containers.

### Can I resize a LUKS-encrypted volume?

Yes. Use `cryptsetup resize` after resizing the underlying block device or image file. For LVM on LUKS (a common setup), you can resize the logical volume with `lvextend` and then resize the filesystem with `resize2fs`.

### What happens if I lose my LUKS passphrase?

Without the passphrase (or a keyfile), the data is irrecoverable. LUKS uses strong AES encryption with no backdoor. This is why you should always store backup keyfiles securely and consider using multiple keyslots with different passphrases for disaster recovery.

### Is eCryptfs still actively maintained?

eCryptfs has been part of the Linux kernel since 2.6.19 but sees less active development than fscrypt. Google and the Linux kernel community have largely shifted focus to fscrypt for native encryption. For new deployments, fscrypt or dm-crypt are recommended over eCryptfs.

### Can I encrypt a running system without reinstalling?

Yes, but it requires careful planning. For LUKS, you can encrypt a non-root partition by copying data, creating the LUKS container, and restoring. For the root filesystem, tools like `cryptsetup-reencrypt` can encrypt in-place, but a full backup is strongly recommended first. fscrypt can be enabled on existing ext4/f2fs filesystems without data migration.
