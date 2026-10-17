---
title: "Linux Kiosk Mode in 2026: Cage vs Cog vs Porteus Kiosk Compared"
date: "2026-10-18"
tags: ["self-hosted", "linux", "kiosk", "homelab"]
draft: false
cover: "/img/screenshots/porteus-kiosk-default.jpg"
---

A kiosk is not a computer with a fullscreen browser. A kiosk is an appliance, and the moment a visitor can reach a shell, open a file manager, or press `Ctrl+Alt+F2` into a login prompt, you no longer have a kiosk — you have an unattended Linux machine on your lobby floor with your network credentials in its keyring.

That distinction separates the three main approaches to locked-down Linux displays. **Cage** is a Wayland compositor that runs exactly one maximized window. **Cog** is a single-window WPE WebKit launcher built for embedded hardware. **Porteus Kiosk** is a complete operating system whose only job is to boot into a browser and refuse to do anything else. They solve the same problem at three different layers of the stack, and picking wrong means either fighting your own tooling or shipping an appliance you cannot update.

## TL;DR: Pick Your Layer

- **You already run a Linux distro and want one locked app → Cage.** MIT licensed, 2,101 stars, ~1 MB of compositor code, no desktop environment. `cage -- chromium --kiosk https://dashboard.internal` is the whole concept.
- **You are shipping an embedded panel, a Raspberry Pi, or an ARM device with WPE WebKit → Cog.** MIT licensed, 348 stars, no user interface by design, scriptable through `cogctl` on D-Bus.
- **You want a turnkey appliance you install once and manage remotely → Porteus Kiosk.** A dedicated ISO with a configuration wizard, an encrypted read-only config, and network-based remote management since version 3.3.0.

My verdict: **Cage for homelabs and internal dashboards, Cog for hardware you manufacture or embed, Porteus Kiosk for anything in a public space where nobody will ever SSH in.** If a stranger can physically touch the screen, you want Porteus Kiosk's boot-to-browser model, not your own compositor config with a polite `systemd` unit.

## The Comparison

| Dimension | Cage | Cog | Porteus Kiosk |
|---|---|---|---|
| What it is | Wayland kiosk compositor | WPE WebKit single-window launcher | Complete kiosk operating system |
| Runs on | Your existing distro | Your existing distro, embedded images | Its own ISO (installed to disk or USB) |
| Display stack | Wayland (wlroots 0.20 branch) | WPE WebKit + backend (DRM, FDO) | X11 based appliance image |
| Lockdown model | One maximized surface, no shell | One window, no UI chrome of its own | Whole OS is the kiosk; no desktop |
| Configuration | CLI flags + systemd unit | CLI + `cogctl` over D-Bus | Install-time wizard, encrypted config file |
| Remote management | Your own SSH/Ansible | Your own fleet tooling | **Built in** via network config file |
| Multi-monitor | `-m last` or `-m extend` | Backend dependent | Wizard-defined |
| Persistence | Full OS, whatever you install | Full OS | Read-only system, config locked |
| License | MIT | MIT | Free to use |
| GitHub stars | 2,101 | 348 | N/A (not on GitHub) |
| Last push | 2026-09-08 | 2026-09-01 | Actively maintained ISO releases |

Cage and Cog are libraries-with-a-binary: you own the OS and therefore every patch, every kernel update, and every way a user might escape. Porteus Kiosk is the opposite trade — you give up flexibility and get an appliance with a much smaller attack surface.

## Which One Fits?

| Use case | Recommended | Why |
|---|---|---|
| Wall-mounted dashboard in an office | Cage | One compositor process, trivial to restart, no desktop to break |
| Digital menu board you also update remotely | Porteus Kiosk | Remote config file, no shell for staff to wander into |
| Custom ARM panel with WPE WebKit | Cog | Designed for WPE; no X11 or full compositor needed |
| Trade-show demo of your own web app | Cage | Fast to set up on any laptop with a Wayland session |
| Public lobby terminal, years unattended | Porteus Kiosk | Read-only system, encrypted config, automatic update path |
| Interactive exhibit with custom hardware | Cog + `cogctl` | Programmatic control over what is displayed |

## Cage: One Window, Nothing Else

Cage is deliberately small. It creates a Wayland session, gives one application the entire output, and prevents interaction with anything outside that application. The project targets wlroots 0.20 and supports XWayland at compile time if you need a legacy application in the kiosk.

Install it from your distribution rather than building from source:

```bash
# Debian / Ubuntu
sudo apt install cage

# Arch
sudo pacman -S cage

# Fedora
sudo dnf install cage
```

Then launch the app you want to lock down:

```bash
cage -- chromium \
  --kiosk \
  --no-first-run \
  --no-default-browser-check \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --disable-features=Translate,MediaRouter \
  https://dashboard.internal/
```

The documented options are short enough to memorize, and each one matters in production:

| Flag | Effect | When you need it |
|---|---|---|
| `-d` | Do not draw client-side decorations | Removes window chrome entirely |
| `-m last` | Use only the last connected monitor | Kiosk on one panel, other outputs dark |
| `-m extend` | Extend across all monitors | Video wall spanning several screens |
| `-s` | Allow VT switching | **Leave this off in public deployments** |
| `-D` | Debug logging | Diagnosing why the app never appeared |

For an unattended appliance you need three things beyond the command itself: autologin, a supervised process, and no getty on other virtual terminals. A minimal systemd unit looks like this:

```ini
[Unit]
Description=Cage kiosk
After=systemd-user-sessions.service
Conflicts=getty@tty1.service

[Service]
User=kiosk
PAMName=login
TTYPath=/dev/tty1
StandardInput=tty
StandardOutput=journal
ExecStart=/usr/bin/cage -d -m last -- /usr/bin/chromium \
  --kiosk --no-first-run --overscroll-history-navigation=0 \
  https://dashboard.internal/
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
```

`Restart=always` is not optional. Kiosk browsers crash — a GPU driver hiccup, a page that exhausts memory, a tab that triggers a renderer kill. Without it, your display shows a black screen until someone walks over and power-cycles the machine.

The security work happens outside Cage. Remove or mask `getty@tty2` through `getty@tty6`, disable the magic SysRq keys, and make sure `Ctrl+Alt+F2` cannot reach a login prompt. Cage's `-s` flag is the difference between a kiosk and a workstation, and it defaults to the safe side — keep it that way.

## Cog: A Launcher for WPE WebKit

Cog solves a narrower problem than Cage: it is a single-window launcher for the WebKit WPE port, with no user interface of its own. It exists because embedded hardware often has no desktop stack at all — no X11, no GNOME, no Chromium build that fits in the image — but it does have a GPU and a need to render one web page forever.

It is built with Meson and needs WPE WebKit development packages:

```bash
meson setup build
meson compile -C build
./build/cog https://status.internal/
```

Cog splits into three components: `libcogcore`, the reusable WPE plumbing; `cog`, the launcher; and `cogctl`, which drives a running instance over the D-Bus session bus. That last piece is what makes Cog interesting for integration work — you can change what the kiosk displays from another process instead of restarting the browser. For an exhibit that switches between a video and an information panel, that is far cleaner than killing and relaunching.

The catch is operational maturity. Stable releases track specific WPE WebKit versions (2.28.x in the documented release line), so "just update the browser" is not a thing — you update the whole image. There is no packaged appliance, no wizard, and no remote management. You are the vendor. That is fine when you control the hardware fleet and have a CI pipeline; it is painful when a stranger is expected to reboot the screen.

## Porteus Kiosk: The Appliance Approach

Porteus Kiosk inverts the model. You do not install a desktop and lock it down; you install an operating system whose entire purpose is to boot into a locked browser. The installer presents a wizard that generates the configuration, which is then embedded in the image and stored encrypted in a read-only location — meaning a visitor with physical access cannot edit the kiosk settings, and neither can malware that reaches the filesystem.

![Porteus Kiosk booting straight into a locked browser with no desktop, panels, or address bar](/img/screenshots/porteus-kiosk-locked-browser.jpg "Porteus Kiosk in locked mode — the address bar and navigation controls are removed entirely")

Version 3.3.0 added the feature that makes this practical at scale: **remote management through a single configuration file stored on the network**. Instead of re-imaging every device to change a homepage, you point kiosks at a central config and let them pull it. For a chain of lobby screens or a school lab, that is the difference between a maintainable deployment and a monthly USB-stick ritual.

The trade-offs are real. You are running a purpose-built distribution, so anything outside the wizard's parameter set requires customization the maintainers explicitly scope as a separate conversation — the FAQ addresses exactly this. Hardware support is narrower than a general-purpose distro. And because the system is read-only by design, there is no "quick fix" via package manager; changes go through the config and a rebuild.

For unattended public terminals, those constraints are the point. A read-only appliance with an encrypted config is a fundamentally smaller attack surface than a full Ubuntu install with a kiosk service bolted on, and it fails in predictable ways.

## Where Kiosk Deployments Actually Break

**The escape hatch is usually the browser, not the compositor.** `Ctrl+W`, `Ctrl+N`, `Ctrl+Shift+I`, a download prompt, a print dialog, a certificate warning page with a clickable link — each one is a path out of your app. Launch with `--kiosk`, disable devtools via policy, block downloads and printing with a managed policy file, and test every keyboard shortcut yourself before the device ships.

**Virtual terminal switching is the classic hole.** On a stock install, `Ctrl+Alt+F2` drops to a login prompt. Unplug that path on every tty, and do not enable Cage's `-s` flag.

**Screen blanking and DPMS will make a healthy kiosk look dead.** Disable blanking in the compositor and in the browser, and check whether the monitor itself has an idle timer. Half of "the kiosk froze" tickets are a display that went to sleep.

**Touch input needs an on-screen keyboard.** A locked browser with no keyboard is unusable the moment the page asks for a login. Deploy a keyboard component and make sure it appears above the kiosk surface.

**Certificates expire silently.** A pinned internal dashboard with an expired certificate shows a warning page — which is often an escape route to a browser UI. Automate renewal and monitor the endpoint from outside.

**Read-only systems still need updates.** Porteus Kiosk can auto-update; a Cage deployment needs unattended-upgrades, a restart policy, and a way to roll back. Design for the update before you design the homepage.

**Kiosk mode is not a sandbox.** It stops a bored visitor from browsing, not a determined attacker with physical access. Lock the case, disable USB boot in firmware, set a firmware password, and assume the network the kiosk is on is untrusted.

**GPU and seat permissions bite on minimal images.** Cage needs DRM master and a seat; if you strip logind or run it from a bare init, you will get a black screen with a cryptic wlroots error. Test on the exact image you plan to ship, not your workstation.

## Why Lock It Down Yourself?

Commercial kiosk platforms charge per device, per month, for what is ultimately a compositor flag and a policy file. If you already have a Linux fleet, Cage turns any spare machine into a locked display in about ten minutes, and your dashboard stays on your own network instead of being proxied through a vendor. For internal status boards, build dashboards, warehouse pick screens, and classroom displays, that is a straightforward win.

If your displays show scheduled content rather than a single application, the problem shifts from lockdown to content management — our [digital signage comparison](../anthias-vs-xibo-vs-screenlite-self-hosted-digital-signage-guide-2026/) covers that stack. And if the kiosk has to reach an internal service from a public network, put it behind a private overlay instead of exposing the port: the [zero-trust access comparison](../2026-05-03-headscale-vs-netbird-vs-openziti-self-hosted-zero-trust-network-access-ztna-guide/) explains the options. For kiosks that display a launcher page rather than one app, the [self-hosted dashboard guide](../self-hosted-homepage-dashboards-homepage-dashy-homarr-guide/) is a better starting point than building one.

The pattern is consistent: the appliance model (Porteus Kiosk) trades flexibility for a smaller blast radius, while the compositor model (Cage, Cog) trades safety margin for control. Choose based on who will be physically standing in front of the screen — and whether you will ever be there to fix it.

## FAQ

**Is Cage a browser or a display server?**

Neither. Cage is a Wayland compositor whose only job is to run one maximized application with no way to interact with anything else. You supply the browser — Chromium, Firefox, or a WPE-based launcher — and Cage guarantees it occupies the whole screen and stays in front.

**Can I use Cage with X11 applications?**

Only if Cage is compiled with XWayland support and the system has the XWayland binary installed. The project documents this as a compile-time option, so distribution packages may or may not include it. For a pure browser kiosk it is irrelevant; for legacy applications, verify with your distro's build before committing.

**What makes Porteus Kiosk different from a locked-down Ubuntu?**

The operating system exists only to run the kiosk. There is no desktop environment, no package manager workflow for users, and the configuration is embedded in the image and stored encrypted in a read-only location. That removes entire categories of failure and escape that a general-purpose distro reintroduces with every update.

**How do I update a fleet of kiosks without visiting each one?**

Porteus Kiosk supports remote management through a single configuration file kept on the network, a capability added in version 3.3.0. For Cage or Cog, you own the update path: unattended-upgrades plus a configuration management tool, or an image-based rollout with a rollback slot.

**Does kiosk mode prevent users from reaching a terminal?**

Only if you close the paths yourself. On a general-purpose distro, virtual terminal switching via `Ctrl+Alt+F2` is the usual hole, along with browser shortcuts, download dialogs, and certificate warning pages. Disable the extra getty instances, avoid Cage's `-s` flag, and enforce browser policy so the shortcut keys cannot open new windows or developer tools.

**Can a kiosk be hacked through the keyboard?**

Physical access is the threat model. A kiosk with an exposed USB port and firmware that allows booting from removable media is a machine an attacker can boot their own OS on. Lock the enclosure, disable external boot in firmware, set an administrator password, and treat the device as physically compromised if it ever leaves your sight.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linux Kiosk Mode in 2026: Cage vs Cog vs Porteus Kiosk Compared",
  "description": "Cage vs Cog vs Porteus Kiosk compared for locked-down Linux kiosk deployments, with real command lines, a systemd unit, and the escape hatches that break kiosks.",
  "datePublished": "2026-10-18",
  "dateModified": "2026-10-18",
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
