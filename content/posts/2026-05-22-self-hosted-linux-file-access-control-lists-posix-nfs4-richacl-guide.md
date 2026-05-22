---
title: "Self-Hosted File Access Control Lists: POSIX ACL vs NFSv4 ACL vs RichACL"
date: "2026-05-22"
tags: ["linux", "security", "filesystem", "access-control", "comparison"]
draft: false
---

Standard Unix file permissions (owner/group/other with read/write/execute) are simple but limited. When you need fine-grained access control — allowing specific users or groups access without changing ownership or creating complex group hierarchies — **Access Control Lists (ACLs)** provide the solution.

This guide compares three ACL implementations available on Linux servers: **POSIX ACLs** (the standard extended permission model), **NFSv4 ACLs** (rich ACLs for networked filesystems), and **RichACLs** (extended POSIX ACLs for local filesystems). Understanding the differences helps you choose the right ACL system for your self-hosted infrastructure.

## Why Standard Unix Permissions Fall Short

The traditional Unix permission model uses three permission sets (user, group, other) with three bits each (read, write, execute). This works for simple scenarios but creates challenges in multi-user environments:

- **No per-user permissions** — you cannot grant write access to one specific user without adding them to the file's group
- **Group proliferation** — managing dozens of groups for different access combinations becomes unwieldy
- **No inheritance** — newly created files in a directory do not automatically inherit the directory's ACL
- **No deny rules** — you cannot explicitly deny access to a specific user while allowing a group
- **Limited audit granularity** — standard permissions provide no logging of access decisions

ACLs address these limitations by allowing multiple named users and groups to have independent permissions on the same file or directory.

## ACL Implementation Comparison

| Feature | POSIX ACL | NFSv4 ACL | RichACL |
|---------|-----------|-----------|---------|
| **Standard** | POSIX.1e (draft) | RFC 5661 | Experimental (ext4 patch) |
| **Tools** | `setfacl`, `getfacl` | `nfs4_getfacl`, `nfs4_setfacl` | `richacl` (kernel module) |
| **Package** | `acl` (installed by default) | `nfs4-acl-tools` | Not in mainline kernel |
| **Filesystem Support** | ext4, XFS, btrfs, zfs | NFSv4, zfs, btrfs | ext4 (patched) |
| **Permission Granularity** | rwx per user/group | 14 permission bits | 14 permission bits |
| **Inheritance** | Yes (default ACL) | Yes (inheritance flags) | Yes |
| **Deny Entries** | No (allow only) | Yes (A:deny) | Yes |
| **Named Users** | Yes | Yes | Yes |
| **Named Groups** | Yes | Yes | Yes |
| **Mask Entry** | Yes (limits named entries) | No mask needed | No mask |
| **Network Sharing** | Via NFSv3 (mapped) | Native (NFSv4 protocol) | Local only |
| **Windows ACL Mapping** | Partial | Full | Partial |

### POSIX ACLs: The Linux Standard

POSIX ACLs extend the traditional Unix permission model by adding named user and group entries. They are supported by all major Linux filesystems and are the default ACL implementation on most distributions.

The permission model adds:
- **User entries** — per-user permissions beyond the file owner
- **Group entries** — per-group permissions beyond the file's owning group
- **Mask** — limits the maximum permissions for named users and groups (acts like a group permission cap)
- **Default ACL** — inherited by new files and directories created within a directory

```bash
# View current ACL
getfacl /data/shared/project

# Grant read-write access to specific user
setfacl -m u:developer:rw /data/shared/project

# Grant read access to a group
setfacl -m g:auditors:r /data/shared/project

# Set default ACL for new files in directory
setfacl -d -m u:intern:r /data/shared/project

# Remove a specific ACL entry
setfacl -x u:developer /data/shared/project

# Remove all extended ACL entries
setfacl -b /data/shared/project
```

### NFSv4 ACLs: Network-Aware Permissions

NFSv4 ACLs provide a richer permission model designed for networked environments. They support 14 distinct permission types (compared to POSIX's 3) and include native deny entries.

The 14 NFSv4 permission bits:
- `read_data`, `write_data`, `append_data`
- `read_xattr`, `write_xattr`
- `execute`, `delete_child`, `delete`
- `read_acl`, `write_acl`, `write_owner`
- `read_attributes`, `write_attributes`, `synchronize`

```bash
# View NFSv4 ACL
nfs4_getfacl /mnt/nfs/shared

# Grant read access to a user
nfs4_setfacl -a "A::developer@domain:RX" /mnt/nfs/shared

# Deny write access to a specific user
nfs4_setfacl -a "A:d:contractor:W" /mnt/nfs/shared

# Set inherited permissions for new files
nfs4_setfacl -a "A:fdi:team@domain:RWX" /mnt/nfs/shared

# Remove an ACE (Access Control Entry)
nfs4_setfacl -x "A::developer@domain:RX" /mnt/nfs/shared
```

### RichACLs: Extended POSIX for Local Filesystems

RichACLs are an experimental kernel patch set for ext4 that brings NFSv4-style ACLs to local filesystems. They are not in the mainline kernel but have been discussed for inclusion.

RichACLs combine the familiarity of POSIX ACL tools with the granularity of NFSv4 ACLs:
- Uses the same `setfacl`/`getfacl` interface as POSIX ACLs
- Supports deny entries (like NFSv4)
- No mask entry (simpler permission model)
- Supports the full 14-permission set

Since RichACLs are not in mainline, they require a patched kernel and are primarily of academic interest for most administrators. In practice, POSIX ACLs (for local) and NFSv4 ACLs (for networked) cover virtually all production use cases.

## Practical Configuration Examples

### Shared Project Directory with POSIX ACLs

A common scenario: a shared directory where multiple teams need different access levels.

```bash
# Create the shared directory
mkdir -p /data/projects/alpha
chmod 2770 /data/projects/alpha  # Set setgid bit for group inheritance
chgrp alpha-team /data/projects/alpha

# Set base ACL for the team
setfacl -m g:alpha-team:rwx /data/projects/alpha

# Grant specific access to individual users
setfacl -m u:alice:rwx /data/projects/alpha
setfacl -m u:bob:rx /data/projects/alpha
setfacl -m u:charlie:r /data/projects/alpha

# Set default ACL so new files inherit team access
setfacl -d -m g:alpha-team:rwx /data/projects/alpha
setfacl -d -m u:alice:rwx /data/projects/alpha

# Verify the complete ACL
getfacl /data/projects/alpha
# Output:
# file: data/projects/alpha
# owner: root
# group: alpha-team
# flags: -s-
# user::rwx
# user:alice:rwx
# user:bob:r-x
# user:charlie:r--
# group::rwx
# group:alpha-team:rwx
# mask::rwx
# other::---
# default:user::rwx
# default:user:alice:rwx
# default:group::rwx
# default:group:alpha-team:rwx
# default:mask::rwx
# default:other::---
```

### NFSv4 Export with Fine-Grained ACLs

Setting up NFSv4 exports with ACL-based access control:

```bash
# NFS server: configure export in /etc/exports
/data/shared    *(rw,sync,no_subtree_check,sec=sys)

# Set NFSv4 ACL on the server
nfs4_setfacl -a "A::admin@domain:RWX" /data/shared
nfs4_setfacl -a "A::developers@domain:RWX" /data/shared
nfs4_setfacl -a "A::viewers@domain:RX" /data/shared
nfs4_setfacl -a "A:d:external:R" /data/shared

# Client mounts with NFSv4
mount -t nfs4 -o vers=4.2 server:/data/shared /mnt/shared

# Verify ACL on client
nfs4_getfacl /mnt/shared
```

### Backup and Restore ACLs

When migrating data between servers, preserving ACLs is critical.

```bash
# Backup POSIX ACLs
getfacl -R /data/ > /backup/acl-backup.txt

# Restore POSIX ACLs
setfacl --restore=/backup/acl-backup.txt

# Backup with rsync (preserves ACLs)
rsync -aAX /data/ /backup/data/
# -A = preserve ACLs, -X = preserve extended attributes

# Copy ACLs from one file to another
getfacl source-file | setfacl --set-file=- target-file
```

## Filesystem Requirements

Not all filesystems support all ACL types. Plan your storage accordingly.

| Filesystem | POSIX ACL | NFSv4 ACL | RichACL |
|-----------|-----------|-----------|---------|
| ext4 | Yes (`acl` mount option, default) | No | Experimental (patch) |
| XFS | Yes (default) | No | No |
| btrfs | Yes (default) | Yes (experimental) | No |
| ZFS | Yes | Yes | No |
| NFSv3 | Via server ACLs | No | No |
| NFSv4 | Via mapping | Yes (native) | No |
| CIFS/SMB | Via mapping | Via mapping | No |

For ext4, ensure the `acl` mount option is enabled (it is the default on modern distributions):

```bash
# Check current mount options
mount | grep "on / "
# Look for 'acl' in the options

# Enable ACL on an ext4 filesystem (if not default)
tune2fs -o acl /dev/sda1
# Or via fstab:
# /dev/sda1  /data  ext4  defaults,acl  0  2
```

## Security Best Practices for ACL Management

- **Regular ACL audits** — run `find /data -name '*.txt' -exec getfacl {} \; | grep -v "^#"` to audit extended ACLs across your filesystem
- **Avoid overly permissive masks** — the POSIX ACL mask limits all named entries; a mask of `rwx` effectively removes the mask's protective function
- **Use default ACLs for directories** — always set default ACLs on shared directories to ensure new files inherit appropriate permissions
- **Document ACL policies** — maintain documentation of which users and groups have access to which directories, especially in multi-team environments
- **Test before deploying** — use `setfacl -m` with `--test` flag (where available) or test on a non-production directory first
- **Monitor ACL changes** — use `auditd` rules to log `setfacl` and `chmod` executions: `-a always,exit -F arch=b64 -S setxattr -F exe=/usr/bin/setfacl`

## Related Guides

For filesystem auditing and compliance, see our [Linux audit framework with auditd guide](../2026-05-16-self-hosted-linux-audit-framework-auditd-goaudit-auditbeat-guide/).
If you manage container security, check our [container capabilities management guide](../2026-05-22-linux-container-capabilities-management-capsh-bubblewrap-native-docker-guide/).
For server security auditing tools, our [Lynis vs OpenSCAP vs Goss comparison](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide-2026/) covers compliance scanning.

## Frequently Asked Questions

### Does the POSIX ACL mask affect the file owner?

No. The mask only limits permissions for named users, named groups, and the owning group. The file owner's permissions are always evaluated directly, bypassing the mask. This is a common point of confusion — the mask appears as the "group" permission in `ls -l` output.

### Can I use ACLs on NFS mounts?

Yes, but the behavior depends on the NFS version. NFSv3 maps ACLs to standard Unix permissions, losing the extended entries. NFSv4.2 supports full ACL preservation across the network. For best results, use NFSv4.2 or later when sharing directories with complex ACLs.

### What happens to ACLs when I copy a file?

Standard `cp` does NOT preserve ACLs. Use `cp --preserve=all` or `cp -a` to retain ACLs during copy. For cross-filesystem copies, `rsync -aAX` is the most reliable option — it preserves ownership, permissions, ACLs, and extended attributes.

### How do I check if a filesystem supports ACLs?

Run `tune2fs -l /dev/sda1 | grep "Default mount options"` for ext4, or check mount options with `mount | grep acl`. For XFS, ACLs are always enabled. For btrfs, check with `btrfs filesystem show`. Most modern Linux distributions enable ACLs by default on all supported filesystems.

### Can ACLs replace group-based permissions?

ACLs complement, not replace, group-based permissions. For simple scenarios (all team members need the same access), standard group permissions are simpler and more maintainable. Use ACLs when you need exceptions to the group rule — specific users with elevated or restricted access that do not fit the group model.

### Do ACLs impact filesystem performance?

The performance impact of POSIX ACLs is minimal — typically less than 1% overhead for metadata operations. NFSv4 ACLs have slightly higher overhead due to the larger ACL structures, but this is negligible for most workloads. The primary performance consideration is the number of ACL entries per file — directories with hundreds of named user entries may see slower `ls` and `stat` operations.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted File Access Control Lists: POSIX ACL vs NFSv4 ACL vs RichACL",
  "description": "Compare three Linux ACL implementations: POSIX ACL, NFSv4 ACL, and RichACL. Covers configuration, tools, filesystem support, and security best practices.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
