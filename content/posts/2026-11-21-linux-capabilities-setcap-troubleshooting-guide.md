---
title: "setcap Worked, Your Service Still Fails: Debugging Linux Capabilities in 2026"
date: "2026-11-21"
description: "A practical debugging guide to Linux capabilities: why file capabilities are silently ignored, how ambient capabilities differ, and the correct systemd and container patterns for dropping root."
tags: ["linux", "security", "capabilities", "systemd", "containers", "sysadmin", "hardening"]
draft: false
---

You ran `sudo setcap cap_net_bind_service=+ep /usr/local/bin/api`, checked it with `getcap` — it printed the capability back at you — started the service as an unprivileged user, and got `bind: permission denied` anyway. Nothing in the logs explains why.

This is the single most common capability failure in production, and it is almost never about the `setcap` command being wrong. It is about one of the **five capability sets** silently stripping the privilege after the file capability is applied: a missing entry in the bounding set, a `nosuid` mount, `NoNewPrivileges=yes` in a unit file, a shell wrapper, or a container runtime that dropped the capability at the boundary.

This guide is the debugging sequence I use to answer "why is this permission denied" in under five minutes, plus the patterns that survive package upgrades and container rebuilds.

## TL;DR: The Short Verdict

- **File capabilities only work on ELF binaries on non-`nosuid` filesystems, and only when `no_new_privs` is off.** Any one of those three conditions being false makes `setcap` a no-op with zero warnings.
- **Scripts never get file capabilities.** The kernel applies capabilities to the `execve` target; for `#!/bin/sh` that target is the interpreter. Wrap the script in a systemd unit with `AmbientCapabilities=` instead.
- **For long-running services, prefer systemd over `setcap`.** `AmbientCapabilities=` + `CapabilityBoundingSet=` + `User=` is auditable in version control and survives package upgrades; `setcap` is invisible state on a filesystem that `apt upgrade` silently wipes.
- **For containers, drop everything and add back one capability.** `--cap-drop ALL --cap-add NET_BIND_SERVICE` beats the default set of 14 capabilities that most images never need.
- **For ports below 1024, you may not need capabilities at all.** `net.ipv4.ip_unprivileged_port_start=80` removes the restriction globally on modern kernels.

## The Capability Model in 90 Seconds

A process has five capability sets. Confusing them is why debugging stalls.

| Set | Purpose | Where to read it |
|---|---|---|
| **Permitted** | Capabilities the process may ever use | `CapPrm` in `/proc/PID/status` |
| **Effective** | Capabilities currently checked by the kernel | `CapEff` |
| **Inheritable** | Capabilities preserved across `execve` | `CapInh` |
| **Bounding** | Hard ceiling — capabilities that can never be gained | `CapBnd` |
| **Ambient** | Preserved across `execve` of non-privileged binaries | `CapAmb` |

Two rules explain nearly every failure:

1. **A capability not in the bounding set can never be acquired**, no matter what `setcap` says on disk. The bounding set is dropped for containers and is settable in systemd via `CapabilityBoundingSet=`.
2. **File capabilities are ignored entirely when `no_new_privs` is set, the filesystem is mounted `nosuid`, or the file is not ELF.** The kernel does not log a warning; the binary simply starts without the privilege.

## Why `setcap` Silently Fails: Seven Causes

### 1. The bounding set is already stripped

The most common cause in containers and hardened units. Check the ceiling first, always:

```bash
# What is the bounding set for PID 1 of the container / for your shell?
grep -E 'Cap(Inh|Prm|Eff|Bnd|Amb)' /proc/self/status
# CapBnd:  00000000a80425fb

# Decode it into names
capsh --decode=00000000a80425fb
# 0x00000000a80425fb=cap_chown,cap_dac_override,cap_fowner,...
```

If `cap_net_bind_service` is not in the decoded `CapBnd`, investing more time in `setcap` is pointless. Fix the boundary instead:

```bash
# systemd unit: raise the ceiling for the service only
sudo systemctl edit api.service
```

```ini
[Service]
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_NET_RAW
AmbientCapabilities=CAP_NET_BIND_SERVICE
User=api
NoNewPrivileges=yes
```

`NoNewPrivileges=yes` is correct here and does **not** conflict with `AmbientCapabilities=` — ambient capabilities are inherited through `execve`, not gained by it.

### 2. The filesystem is mounted `nosuid`

```bash
findmnt -T /usr/local/bin/api -o TARGET,SOURCE,FSTYPE,OPTIONS
# If OPTIONS contains nosuid, file capabilities are ignored
```

`nosuid` is standard on `/tmp`, many container overlay mounts, and hardened `/home` partitions. A binary that works in `/usr/local/bin` and fails after you copy it to `/data/bin` is almost always this.

### 3. The "binary" is a script

```bash
file /usr/local/bin/api
# /usr/local/bin/api: Bourne-Again shell script, ASCII text executable
```

File capabilities are stored in the `security.capability` extended attribute and applied by the kernel to the executed ELF image. With a shebang, the kernel executes `/bin/bash` and hands it your script as an argument — the script's xattr is never consulted. No amount of `setcap` on a shell script will work.

### 4. A package upgrade replaced the binary

Capabilities live on the inode, not in the package database. Any `dpkg`/`rpm` upgrade that writes a fresh file drops them silently:

```bash
# Detect drift: capability expected but missing
getcap /usr/local/bin/api
# (no output = gone)

# RPM-based systems can restore packaged capabilities
sudo rpm -qa --dump | grep -i ' cap_' | head
```

This is the strongest argument for declaring capabilities in the unit file rather than baking them into the filesystem.

### 5. `no_new_privs` was set by something upstream

`NoNewPrivileges=yes` in a unit file, `--security-opt no-new-privileges` in Docker, or a seccomp profile that sets the prctl flag all disable file capabilities by design. Verify from inside the running process:

```bash
# 1 = no_new_privs is on, file capabilities will be ignored
grep NoNewPrivs /proc/<PID>/status
```

### 6. You set the wrong flag combination

`setcap` flags are not interchangeable:

| Flag | Meaning | Typical use |
|---|---|---|
| `+ep` | effective + permitted | Normal service binary needing the privilege immediately |
| `+p` only | permitted, not effective | Wrapper that raises the cap itself before exec |
| `+ei` | effective + inheritable | Legacy inheritable-chain workflows |
| `=ep` | reset and set exactly | Preferred — avoids leftover flags |

Proof that it took, including the flags:

```bash
sudo setcap -r /usr/local/bin/api                     # start clean
sudo setcap cap_net_bind_service=+ep /usr/local/bin/api
getcap -v /usr/local/bin/api
# /usr/local/bin/api cap_net_bind_service=ep
```

### 7. SELinux or AppArmor denied it anyway

Capabilities are a coarse check; mandatory access control runs after them. On RHEL-family hosts, `ausearch -m avc -ts recent` shows the denial. On AppArmor, `/var/log/kern.log` carries `apparmor="DENIED"` lines naming the profile and the requested capability.

## Choosing the Right Mechanism

| Mechanism | Scope | Survives exec | Works for scripts | Auditable in git | Notes |
|---|---|---|---|---|---|
| `setcap` file capabilities | Filesystem inode | Yes (ELF only) | No | No | Lost on package upgrade; ignored on `nosuid` |
| `setpriv --ambient-caps` | One process invocation | Yes | Yes (for children) | Sometimes | Great for wrappers and CI steps |
| systemd `AmbientCapabilities=` | Unit | Yes | Yes | Yes | Best default for services |
| sudoers `NOPASSWD` | Command | Yes | Yes | Yes | Broad; hard to audit for privilege creep |
| container `--cap-add` | Container | Yes | Yes | Yes (compose file) | Pair with `--cap-drop ALL` |
| `net.ipv4.ip_unprivileged_port_start` | Whole host | N/A | N/A | Sysctl file | Removes the need for the capability at all |

**Decision matrix:**

| Your situation | Use this | Why |
|---|---|---|
| systemd service needs to bind port 443 | `AmbientCapabilities=CAP_NET_BIND_SERVICE` + `User=app` | Declarative, survives upgrades, no setuid |
| Container needs raw sockets for a health probe | `--cap-drop ALL --cap-add NET_RAW` | Smallest blast radius |
| Shell script needs to open a raw socket | systemd `AmbientCapabilities=` or a tiny compiled wrapper | Scripts cannot hold file capabilities |
| One-off CLI invocation as a normal user | `setpriv --ambient-caps=+net_bind_service --inh-caps=+net_bind_service` | No persistent state on disk |
| Dev machine, want ports 80/443 for anything | `sysctl net.ipv4.ip_unprivileged_port_start=80` | Removes the privileged-port concept |
| You are about to use `setcap` on a package-managed binary | Don't | The next upgrade deletes it |

## Working Patterns You Can Copy

### Pattern A: systemd unit with a minimal capability set

```ini
# /etc/systemd/system/api.service
[Unit]
Description=API service
After=network-online.target

[Service]
Type=simple
User=api
Group=api
ExecStart=/usr/local/bin/api --config /etc/api/config.yaml

# The only capability this service gets, ever
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

# Lock everything else down
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
```

Verify the result from the host, without trusting the unit file:

```bash
sudo systemctl daemon-reload
sudo systemctl restart api
PID=$(systemctl show -p MainPID --value api)
sudo grep -E 'Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs' /proc/$PID/status
sudo getpcaps $PID
```

You want `CapEff` decoding to exactly one capability and nothing else. If you see `cap_sys_admin` or `cap_dac_override` in there, something upstream (a `Protect*` directive that needs it, or a wrapper script) reintroduced it.

### Pattern B: ambient capabilities for a wrapper script

```bash
#!/usr/bin/env bash
# Runs a Python service that needs to bind port 443, without root
set -euo pipefail

exec setpriv \
  --reuid=app --regid=app --init-groups \
  --inh-caps=+net_bind_service \
  --ambient-caps=+net_bind_service \
  --bounding-set=+net_bind_service \
  /usr/bin/python3 /opt/app/main.py
```

Ambient capabilities are the only mechanism that carries a capability through `execve` of a *non-privileged* binary — which is exactly what "run this script as an unprivileged user, but let it bind 443" requires.

### Pattern C: containers with an explicit capability budget

```yaml
# compose.yaml
services:
  proxy:
    image: ghcr.io/example/proxy:1.4
    read_only: true
    user: "10001:10001"
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    ports:
      - "443:8443"
```

Then confirm at runtime rather than trusting the manifest:

```bash
docker inspect --format '{{.HostConfig.CapDrop}} {{.HostConfig.CapAdd}}' proxy
docker exec proxy grep Cap /proc/self/status
```

Note the Docker default capability set — `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `FSETID`, `KILL`, `SETGID`, `SETUID`, `SETPCAP`, `NET_BIND_SERVICE`, `NET_RAW`, `SYS_CHROOT`, `MKNOD`, `AUDIT_WRITE`, `SETFCAP` — is generous. `CAP_SETPCAP` in particular lets a process manipulate its own capability sets, which almost no application needs.

### Pattern D: skip the capability entirely

```bash
# Persist across reboots
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/90-unprivileged-ports.conf
sudo sysctl --system

# Now an unprivileged user can bind 80 and above
```

This is a host-wide policy change, so treat it as such: it removes a security boundary for every process on the machine, not just yours. On single-purpose appliances that is a good trade; on multi-tenant hosts it is usually not.

## Auditing What Already Has Privileges

Before adding capabilities, find the ones already granted. The output is often longer than admins expect:

```bash
# Every file capability on the system
sudo getcap -r / 2>/dev/null

# Typical modern output
# /usr/bin/ping cap_net_raw=ep
# /usr/bin/dumpcap cap_net_raw,cap_net_admin=eip
# /usr/lib/x86_64-linux-gnu/gstreamer1.0/gstreamer-1.0/gst-ptp-helper cap_net_bind_service,cap_net_admin=ep
```

```bash
# Capabilities of every running process, decoded
for p in $(pgrep -u root | head -40); do
  echo "== $p $(cat /proc/$p/comm 2>/dev/null)"
  getpcaps $p 2>/dev/null
done | grep -B1 -i "cap_sys_admin\|cap_dac_override" | head -20
```

Anything holding `cap_sys_admin` outside of containers and mount tooling deserves a ticket. It is effectively root for most practical purposes.

## Pitfalls That Cost Real Outages

- **`setcap` on a symlink applies to the target, not the link.** If a package upgrade repoints the symlink, your capability stays on the old inode and the new target has none.
- **Copying a binary drops capabilities.** `cp` does not preserve `security.capability` by default; `cp --preserve=xattr` or `rsync -X` does.
- **`AmbientCapabilities=` without `CapabilityBoundingSet=` sometimes appears to work and then fails after a reboot.** Set both explicitly so the unit is self-documenting.
- **`ProtectSystem=strict` makes `/usr` read-only — that is fine, but `setcap` then fails at runtime** for any unit that tries to apply capabilities to its own binary on start.
- **`MemoryDenyWriteExecute=yes` breaks JIT runtimes** (Node.js, .NET, some Python C extensions). Drop that directive for those services instead of debugging mysterious segfaults.
- **`SystemCallFilter=@system-service` is a blocklist of convenience, not a security proof.** Its contents change between systemd releases; pin behavior with `SystemCallFilter=~@mount` style exclusions when exact syscall policy matters.
- **In Kubernetes, `securityContext.capabilities.drop: ["ALL"]` plus `runAsNonRoot: true` will break images that `chown` at startup** — they need `CAP_CHOWN` or a pre-chowned volume. Failing pods with `permission denied` on `/data` are usually this.

Related reading: if you are building the wider isolation stack around these services, our [sandboxing frameworks guide covering Landlock, seccomp and bubblewrap](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-seccomp-bubblewrap-guide/) goes one layer deeper, the [container seccomp profile guide](../2026-05-10-container-seccomp-profile-management-apparmor-firejail-guide/) covers the syscall filter that runs after capability checks, and [process resource limits with systemd and PAM](../2026-05-24-self-hosted-linux-process-resource-limits-systemd-pam-limits-cgroup-v2-guide/) handles the other half of hardening a service unit.

Reference projects behind the tooling in this article, with live repository data:

| Project | Role | Stars | Last push |
|---|---|---|---|
| [util-linux](https://github.com/util-linux/util-linux) | Provides `setpriv`, `findmnt`, `lsns` | 3,255 | 2026-11-19 |
| [bubblewrap](https://github.com/containers/bubblewrap) | Unprivileged sandboxing used by Flatpak | 9,577 | 2026-10-14 |
| [Firejail](https://github.com/netblue30/firejail) | Namespace + seccomp sandbox with capability profiles | 7,746 | 2026-11-18 |

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "setcap Worked, Your Service Still Fails: Debugging Linux Capabilities in 2026",
  "description": "A practical debugging guide to Linux capabilities: why file capabilities are silently ignored, how ambient capabilities differ, and the correct systemd and container patterns for dropping root.",
  "datePublished": "2026-11-21",
  "dateModified": "2026-11-21",
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

### Why does `setcap` appear to succeed but the program still gets permission denied?

Because `setcap` only writes an extended attribute; the kernel decides at `execve` time whether to honor it. It is ignored when the filesystem is mounted `nosuid`, when the process runs with `no_new_privs` set, when the binary is not ELF (for example a shell script), or when the capability is not in the process bounding set — which is exactly what container runtimes and `CapabilityBoundingSet=` in systemd control. Check `/proc/PID/status` for `CapBnd` and `NoNewPrivs` before changing anything on disk.

### What is the difference between file capabilities and ambient capabilities?

File capabilities are stored on the binary's inode and granted when that exact ELF image is executed. Ambient capabilities belong to the *process* and are preserved across `execve` of unprivileged binaries, so they survive being passed to a shell script or an interpreter. Use file capabilities for a single dedicated binary; use ambient capabilities (`setpriv --ambient-caps`, `systemd AmbientCapabilities=`) when a wrapper or interpreter chain is involved.

### Can I use `setcap` on a shell script?

No. The kernel applies file capabilities to the executable that `execve` loads. With a shebang, that executable is the interpreter (`/bin/bash`, `/usr/bin/python3`), and the script is merely an argument — its extended attributes are never consulted. Grant the capability to the interpreter's execution context instead, typically via a systemd unit with `AmbientCapabilities=`, or compile a small wrapper that sets ambient capabilities and then executes the script.

### Should I use `setcap` or a systemd unit for a service that needs to bind port 443?

Use the systemd unit. `setcap` stores state on a filesystem inode that is invisible to configuration management, is silently erased by package upgrades, and applies to every invocation by every user. `AmbientCapabilities=` plus `CapabilityBoundingSet=` plus `User=` is version-controlled, scoped to one service, and reviewable in a pull request. Reserve `setcap` for third-party binaries you cannot wrap in a unit.

### How do I check which capabilities a running process actually has?

Read `/proc/<PID>/status` and decode `CapEff`, or run `getpcaps <PID>`, which prints the names directly. For a systemd service, `systemctl show -p MainPID --value <unit>` gives you the PID. If `CapEff` decodes to `cap_sys_admin` or `cap_dac_override`, the process effectively has root-equivalent power regardless of which user it runs as.

### Do I still need capabilities if I set `net.ipv4.ip_unprivileged_port_start=80`?

Not for binding low ports — that sysctl removes the privileged-port restriction for the whole host, so any process can bind port 80 or higher without `CAP_NET_BIND_SERVICE`. You still need capabilities for raw sockets (`CAP_NET_RAW`), interface configuration (`CAP_NET_ADMIN`), and changing file ownership (`CAP_CHOWN`). Remember that the sysctl is host-wide: it lowers a boundary for every process, not just the one you are debugging.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
