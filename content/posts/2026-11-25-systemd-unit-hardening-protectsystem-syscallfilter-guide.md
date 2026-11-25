---
title: "systemd Hardening in 2026: 12 Unit Directives That Take a Service From 9.6 UNSAFE to Under 3.0"
date: "2026-11-25"
tags: ["systemd", "security", "linux", "hardening", "sysadmin", "self-hosted"]
draft: false
cover: "/img/screenshots/systemd-hardening-cover.jpg"
---

Run `systemd-analyze security` against a typical self-hosted service and the report is brutal. On the Ubuntu 24.04 host I used for this article, the gateway service scored **9.6 UNSAFE** — with `ProtectSystem=`, `PrivateTmp=`, `PrivateNetwork=`, `ProtectProc=`, `RestrictAddressFamilies=` and every syscall filter group listed as unset. That service is not unusual. It is the default: most unit files shipped by distros and vendors harden nothing at all, and the process runs with full access to the OS file hierarchy, the host network, other users' temporary files, and every device node.

The fix does not require containers, SELinux policy authoring, or a rewrite. systemd has shipped a complete sandboxing toolkit since v232, and the host in question runs **systemd 255.4**. This guide covers the twelve directives that carry the most weight in the exposure score, the order to apply them, and how to avoid the three failure modes that make people give up and revert everything.

## Quick Verdict (TL;DR)

- **Highest return for the least risk:** `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `ProtectKernelTunables=yes`, `ProtectKernelModules=yes`, `ProtectControlGroups=yes`, `RestrictSUIDSGID=yes`, `LockPersonality=yes`. These break almost nothing that runs as a normal service.
- **Highest return with real breakage risk:** `SystemCallFilter=@system-service`, `RestrictAddressFamilies=`, `CapabilityBoundingSet=`, `DynamicUser=yes`. Apply one at a time and watch the service logs.
- **Do not** enable `MemoryDenyWriteExecute=yes` on anything with a JIT — PHP's `opcache.jit`, any JVM, Node with V8 code cache, or a LuaJIT service will die with `SIGSEGV` on start.
- Realistic target: **9.6 → 2.0-3.5** for a normal network daemon. Below 2.0 usually requires removing network access entirely.

## How the Exposure Score Actually Works

`systemd-analyze security <unit>` inspects the unit's effective settings and adds a weighted penalty for each missing protection. The weights are visible in the output, and they tell you where to spend effort:

| Finding (from a real 9.6-rated unit) | Exposure added | Meaning |
|---|---|---|
| `PrivateNetwork=` unset | **0.5** | Service can reach the host network and every peer |
| `CapabilityBoundingSet=~CAP_SYS_ADMIN` | **0.3** | Full administrator privileges retained |
| `RestrictAddressFamilies=~AF_(INET\|INET6)` | 0.3 | Can allocate Internet sockets regardless of intent |
| `CapabilityBoundingSet=~CAP_SET(UID\|GID\|PCAP)` | 0.3 | Can change identities and capabilities |
| `CapabilityBoundingSet=~CAP_SYS_PTRACE` | 0.3 | Can debug and read other processes |
| `ProtectSystem=` unset | 0.2 | Full write access to the OS file hierarchy |
| `PrivateTmp=` unset | 0.2 | Shares `/tmp` with every other service |
| `ProtectProc=` unset | 0.2 | Full visibility into the process tree |
| `ProtectHome=` unset | 0.2 | Full access to home directories |
| `PrivateUsers=` unset | 0.2 | Shares the host user namespace |
| `SystemCallFilter=` unset (each group) | 0.1-0.2 | Eleven syscall groups unfiltered |
| `UMask=` unset | 0.1 | Files created world-readable |

Two conclusions follow directly. First, **capability drops are worth as much as filesystem protection** — a service that keeps `CAP_SYS_ADMIN` has not been meaningfully hardened no matter how many `Protect*` lines you add. Second, the syscall filter groups add up: clearing all eleven is worth roughly **1.5 points** on its own.

Audit the whole system, not one unit:

```bash
# every service, sorted worst-first
systemd-analyze security --no-pager | sort -k2 -r | head -20

# one unit, machine-readable
systemd-analyze security --no-pager --json=short sshd.service

# audit a unit file that is not loaded on this host
systemd-analyze security --offline=true ./myapp.service
```

## The Decision Matrix

| Workload | Hardening profile | Skip these |
|---|---|---|
| Stateless web/API daemon | Full profile, `DynamicUser=yes` if it needs no persistent UID | Nothing major |
| Service with persistent data in `/var/lib` | Full profile + `StateDirectory=` | `DynamicUser` if UID ownership matters externally |
| Reverse proxy / load balancer | Full profile + `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` | `PrivateNetwork` |
| Backup / sync agent | Full profile, read-only `ProtectSystem=strict` + `ReadWritePaths=` | `PrivateDevices` if it touches raw disks |
| JIT runtime (PHP JIT, JVM, V8) | Full profile **minus** `MemoryDenyWriteExecute` | `MemoryDenyWriteExecute=yes` |
| Monitoring agent needing host metrics | Filesystem profile + capabilities left intact | `PrivateNetwork`, `ProtectProc=invisible` |

## Layer 1: Filesystem — `ProtectSystem=strict` and Friends

```ini
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/myapp /var/log/myapp
UMask=0077
```

- **`ProtectSystem=strict`** mounts the entire filesystem hierarchy read-only except `/dev`, `/proc`, and `/sys`. This is the setting most people should use; `full` only makes `/usr`, `/boot`, and `/etc` read-only, which is far weaker.
- **`ReadWritePaths=`** punches the necessary holes. Prefer the automatic directory directives instead where possible: `StateDirectory=myapp` creates `/var/lib/myapp`, `CacheDirectory=`, `LogsDirectory=`, and `RuntimeDirectory=` do the same for their trees, and all of them are correctly owned when combined with `DynamicUser=yes`.
- **`ProtectHome=yes`** makes `/home`, `/root`, and `/run/user` inaccessible. Use `read-only` or `tmpfs` if the service genuinely reads from a home directory.
- **`UMask=0077`** stops the classic incident where a service writes a config dump or a session file that is world-readable.

Verify what the service actually sees, rather than assuming:

```bash
systemctl show -p ProtectSystem -p ReadWritePaths -p StateDirectory myapp.service
```

## Layer 2: Privileges — Capabilities, `DynamicUser`, `NoNewPrivileges`

```ini
NoNewPrivileges=yes
CapabilityBoundingSet=
AmbientCapabilities=
RestrictSUIDSGID=yes
LockPersonality=yes
PrivateUsers=yes
DynamicUser=yes
```

An **empty `CapabilityBoundingSet=`** removes all capabilities from the bounding set, which is correct for the overwhelming majority of services. A reverse proxy that must bind port 80 as a non-root user needs exactly one exception:

```ini
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
```

`AmbientCapabilities` is what actually survives `execve` into the service process; setting only the bounding set is a common half-fix.

**`DynamicUser=yes`** allocates a transient UID/GID from the 61184-65519 range at start and releases it at stop. Combined with `StateDirectory=`, systemd places data under `/var/lib/private/myapp` and symlinks it, so the service has persistent storage without a permanent account. Do not use it when an external system (NFS with fixed UID mapping, a database grant, a bind mount owned by a static UID) depends on a stable numeric ID.

`PrivateUsers=yes` maps the service into its own user namespace. It composes badly with `DynamicUser` on some kernels — test both together on the target distro before shipping.

## Layer 3: Syscall Filtering — the 1.5-Point Group

```ini
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources @obsolete @mount @debug @cpu-emulation @swap @reboot @module @raw-io
SystemCallErrorNumber=EPERM
SystemCallArchitectures=native
```

`@system-service` is a curated allowlist covering what ordinary daemons need. Subtracting the dangerous groups afterwards is belt-and-braces: `@privileged` (mount, ptrace, setuid), `@resources` (setrlimit abuse, `ioprio_set`), `@module` (kernel module loading), `@raw-io` (`ioperm`, `iopl`), `@reboot`, `@swap`, `@obsolete`, `@cpu-emulation`, `@debug`, and `@mount`.

`SystemCallErrorNumber=EPERM` makes blocked calls fail with a permission error instead of killing the process with `SIGSYS`. That single line converts "service crashes mysteriously" into "service logs a permission error and keeps running" — which is exactly what you want during rollout.

`SystemCallArchitectures=native` blocks the 32-bit compatibility ABI, closing a well-known filter-bypass path on x86_64 hosts.

## Layer 4: Kernel, Devices, and Process Visibility

```ini
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectClock=yes
ProtectControlGroups=yes
ProtectProc=invisible
ProcSubset=pid
PrivateDevices=yes
DevicePolicy=closed
```

`ProtectKernelTunables` blocks writes to `/proc/sys`, `/sys`, and the BPF filesystem. `ProtectKernelModules` blocks `init_module`/`finit_module`/`delete_module`. `ProtectKernelLogs` closes `/dev/kmsg`. `ProtectClock` blocks clock changes — relevant for anything that could otherwise shift timestamps to hide activity. `ProtectControlGroups` makes the cgroup tree read-only, preventing a compromised service from escaping its CPU or memory limits.

`ProtectProc=invisible` plus `ProcSubset=pid` hides processes outside the service's own namespace from `/proc`. This is one of the cheapest wins in the whole list, and it breaks only tools that enumerate host processes (some monitoring agents).

`PrivateDevices=yes` provides a minimal `/dev` with only pseudo-devices. A service that needs a real device gets an explicit `DeviceAllow=` entry:

```ini
PrivateDevices=no
DevicePolicy=closed
DeviceAllow=/dev/dri/renderD128 rw
```

## Layer 5: Network Surface

```ini
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
IPAddressDeny=any
IPAddressAllow=localhost
SocketBindDeny=any
SocketBindAllow=8080
```

`RestrictAddressFamilies` is the one to apply first: leaving `AF_PACKET` and `AF_NETLINK` available to a web application is what turns a request-parsing bug into a local network attack. `IPAddressDeny=any` with an allowlist is implemented with cgroup BPF and gives you an egress firewall that follows the service even if its iptables rules change. `SocketBindDeny=any` prevents a compromised process from opening a listener you never intended.

Do not stack `PrivateNetwork=yes` on a service that must reach the network — it removes connectivity entirely, which is why it carries the largest single weight (0.5) in the score.

## A Complete Hardened Unit

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=MyApp API
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=myapp
Group=myapp
ExecStart=/usr/local/bin/myapp --config /etc/myapp/config.yaml
Restart=on-failure
RestartSec=3

# filesystem
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
DevicePolicy=closed
ReadWritePaths=/var/lib/myapp
StateDirectory=myapp
LogsDirectory=myapp
UMask=0077

# privileges
NoNewPrivileges=yes
CapabilityBoundingSet=
AmbientCapabilities=
RestrictSUIDSGID=yes
LockPersonality=yes
RestrictRealtime=yes

# kernel and process visibility
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectClock=yes
ProtectControlGroups=yes
ProtectProc=invisible
ProcSubset=pid

# syscalls
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources @obsolete @mount @debug @cpu-emulation @swap @reboot @module @raw-io
SystemCallErrorNumber=EPERM

# network
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SocketBindDeny=any
SocketBindAllow=8443

# resource limits
LimitNOFILE=65536
MemoryMax=2G
TasksMax=512

[Install]
WantedBy=multi-user.target
```

Then measure, do not assume:

```bash
systemctl daemon-reload
systemctl restart myapp.service
systemd-analyze security --no-pager myapp.service | tail -3
journalctl -u myapp.service -n 30 --no-pager
```

A unit hardened along these lines typically reports **2.0-3.5**. The residual score comes almost entirely from keeping the network reachable and the capability bounding set non-empty in cases where the app needs one.

If the service is a PHP pool, the same directives apply to the `php8.5-fpm.service` unit and to the pool's own limits — our [PHP 8.5 tuning guide](../2026-11-25-php-85-performance-tuning-opcache-jit-fpm-pools/) covers the `pm.max_children`, slowlog, and OPcache side of that deployment. For the layer below systemd, the [Linux sandboxing frameworks comparison](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-seccomp-bubblewrap-guide/) explains when Landlock or bubblewrap adds value beyond unit-level confinement. And if you are also locking down boot, the [initramfs builders comparison](../2026-05-22-self-hosted-initramfs-builders-dracut-vs-mkinitcpio-vs-initramfs-tools-guide/) covers the dracut and mkinitcpio knobs that decide what your hardened unit starts inside of.

## Boot and Host-Wide Verification

Unit hardening is only one layer. Two quick checks keep the surrounding host honest:

```bash
# what is actually running unhardened
systemd-analyze security --no-pager | awk '$2+0 > 6.0'

# which units deviate from the vendor version on disk
systemd-delta --type=overridden | head -20
```

![systemd-boot menu on a hardened host](/img/screenshots/systemd-boot-menu.jpg "Real systemd-boot menu screenshot from the official systemd repository")

`systemd-delta` matters because a hardened drop-in that was silently overridden by a later package update is a very common audit finding — the file exists, the protection does not apply.

## Pitfalls That Cause Reverts

1. **`MemoryDenyWriteExecute=yes` on a JIT runtime.** Immediate segfault. PHP with `opcache.jit`, any JVM, Node with code cache enabled, and LuaJIT all need writable-executable mappings. Exclude this directive for those services.
2. **`ProtectSystem=strict` without `ReadWritePaths=`.** The service starts, then fails the first time it writes a PID file, a cache, or a log. Check `journalctl` for `Read-only file system` and add the specific path — never disable `strict`.
3. **Empty `CapabilityBoundingSet=` on a service that binds a privileged port.** It fails with `EACCES` before logging anything useful. Add `CAP_NET_BIND_SERVICE` via `AmbientCapabilities`.
4. **`PrivateTmp=yes` with a service that shares a UNIX socket through `/tmp`.** The socket becomes invisible to peers. Move it to `/run/myapp/` and use `RuntimeDirectory=myapp`.
5. **`DynamicUser=yes` with bind-mounted data owned by a static UID.** Permission denied on every write. Use a static system user for data-bearing services.
6. **Applying `SystemCallFilter` and `CapabilityBoundingSet` in the same restart.** When it breaks you cannot tell which directive did it. Change one layer per restart.

## FAQ

**Does `systemd-analyze security` work on units that are not running?**
Yes, with `--offline=true` on systemd 250 and newer: `systemd-analyze security --offline=true ./myapp.service`. Without it the tool needs a running manager and a loaded unit, which is why auditing a unit on a build machine used to require installing it first.

**What is a good exposure score for a network-facing service?**
Between 2.0 and 4.0 is a realistic target for anything that must accept connections. Scores below 2.0 generally require `PrivateNetwork=yes`, which removes network access — appropriate for batch jobs and local workers, not for an API server. Anything above 6.0 means the service is effectively unconfined and should be treated as a finding.

**Will hardening break my application's ability to write logs?**
Only if it writes outside the paths you allowed. Use `LogsDirectory=myapp` (which maps to `/var/log/myapp`) or log to journald via stdout. With `ProtectSystem=strict`, writing to `/var/log/myapp` directly without a matching `ReadWritePaths=` or `LogsDirectory=` fails with `Read-only file system`.

**Do I need SELinux or AppArmor on top of systemd hardening?**
They cover different layers. systemd directives constrain what the process can see and which syscalls and capabilities it has; mandatory access control constrains file labels and transitions. systemd hardening is far cheaper to deploy, works identically across distros, and is enough for most self-hosted services. Add MAC when you need to confine a service that must keep broad capabilities.

**How do I roll this out without an outage?**
Apply the filesystem and kernel-protection layers first — they break almost nothing. Restart, confirm health, then add privileges, then syscall filters, then network restrictions. Keep `SystemCallErrorNumber=EPERM` set during rollout so blocked calls log instead of killing the process, and keep `systemctl cat myapp.service` output in version control so the next admin can see what was intentionally changed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "systemd Hardening in 2026: 12 Unit Directives That Take a Service From 9.6 UNSAFE to Under 3.0",
  "description": "A practical systemd unit hardening guide: ProtectSystem, DynamicUser, CapabilityBoundingSet, SystemCallFilter and network restrictions, with real systemd-analyze security weights and a complete hardened unit file.",
  "datePublished": "2026-11-25",
  "dateModified": "2026-11-25",
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
