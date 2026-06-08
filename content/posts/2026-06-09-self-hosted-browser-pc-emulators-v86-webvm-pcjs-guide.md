---
title: "Self-Hosted Browser-Based PC Emulators: v86 vs WebVM vs PCjs"
date: "2026-06-09"
tags: ["self-hosted", "emulation", "web-development", "retro-computing", "docker", "javascript", "guide", "comparison", "browser-tools", "virtualization"]
draft: false
---

## Introduction

Browser-based PC emulators let you run full x86 operating systems and vintage computers directly in a web browser — no installation, no VMs, no downloads. These tools compile x86 machine code to WebAssembly at runtime, creating a surprisingly capable virtual machine inside a browser tab. Whether you're preserving retro software, teaching operating system concepts, or building a self-hosted computer museum, these projects make it possible to run Windows 95, Linux, DOS, and even classic IBM PC systems from any modern browser.

In this guide, we compare three leading open-source browser-based PC emulators: **v86**, **WebVM**, and **PCjs**. Each takes a different approach to in-browser emulation, from raw x86 JIT compilation to WebAssembly-powered Linux virtual machines to faithful period-accurate hardware recreations.

## Comparison Table

| Feature | v86 | WebVM | PCjs |
|---------|-----|-------|------|
| GitHub Stars | 23,116 | 16,903 | 1,164 |
| Primary Language | JavaScript | JavaScript | JavaScript |
| Emulation Type | x86 JIT compiler | WebAssembly Linux VM | Period-accurate hardware |
| OS Support | Linux, Windows 95/98, DOS, FreeDOS, KolibriOS | Debian Linux (user-mode) | IBM PC, PC XT, PC AT, 386+ |
| Networking | Virtual NIC with NAT, relay-based | Tailscale networking, full TCP/IP | Emulated modem/serial |
| Persistent Storage | 9P filesystem, IndexedDB | 9P filesystem, configurable | Local disk images |
| Graphics | VGA, Cirrus, Bochs VBE | Framebuffer, X11 forwarding | CGA, EGA, VGA, Hercules |
| Sound | SoundBlaster 16, GUS | Limited (no hardware audio) | PC Speaker, AdLib, SoundBlaster |
| Docker Support | Community images | Official Docker image | Static files (nginx) |
| Last Updated | June 2026 | June 2026 | March 2026 |
| License | BSD-2-Clause | Apache 2.0 | MIT |

## v86: The High-Performance x86 Emulator

v86 is the most mature and feature-rich browser-based x86 emulator, with over 23,000 GitHub stars. Created by Fabian Hemmer, it uses a custom x86-to-WebAssembly JIT (Just-In-Time) compiler that translates x86 instructions to WebAssembly at runtime. The result is surprisingly performant — you can boot a Linux kernel or Windows 98 with graphical desktop in seconds, all within a browser tab.

**Key Features:**
- Complete x86 instruction set emulation (including FPU, MMX, SSE)
- Networking via virtual NIC with NAT and WebSocket/VNC relay support
- 9P filesystem for file sharing between host and guest
- Graphics support for VGA, Cirrus Logic, and Bochs VBE
- SoundBlaster 16 and Gravis Ultrasound audio emulation
- Serial port and NE2000 network card emulation

**Self-Hosting with Docker:**

```yaml
version: "3.8"
services:
  v86:
    image: ghcr.io/linuxserver/v86
    container_name: v86
    ports:
      - "8080:80"
    volumes:
      - ./images:/opt/v86/images
      - ./config:/opt/v86/config
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    restart: unless-stopped
```

You can also deploy v86 directly behind nginx with minimal configuration:

```nginx
server {
    listen 80;
    server_name emulator.yourdomain.com;

    root /opt/v86;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # WebSocket support for networking
    location /ws/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

v86 supports an extensive library of pre-built disk images including Arch Linux, Windows 95/98, FreeDOS, and various Linux distributions. The networking relay (available as a separate Node.js service) enables internet connectivity for guest operating systems through a proxy/bridge architecture.

## WebVM: Linux Virtual Machine for the Web

WebVM takes a fundamentally different approach from v86. Instead of emulating x86 hardware instruction-by-instruction, it uses the CheerpX engine to run unmodified x86 Linux binaries in the browser through WebAssembly and a custom Linux-compatible userspace. Created by Leaning Technologies, WebVM provides a complete Debian Linux environment with working networking, a package manager, and full terminal access — all without a hypervisor.

**Key Features:**
- Full Debian Linux userspace in the browser
- Working `apt` package manager (install software on the fly)
- Tailscale-based networking with real TCP/IP connectivity
- X11 forwarding for graphical applications
- 9P filesystem with persistent storage options
- Python, Node.js, GCC, and other development tools pre-installed

**Self-Hosting with Docker:**

```yaml
version: "3.8"
services:
  webvm:
    image: ghcr.io/leaningtech/webvm:latest
    container_name: webvm
    ports:
      - "8080:80"
    volumes:
      - ./data:/storage
    environment:
      - TAILSCALE_AUTHKEY=${TAILSCALE_AUTHKEY}
      - STORAGE_PATH=/storage
    restart: unless-stopped
```

WebVM excels as a development environment and educational tool. With Tailscale integration, your browser-based VM gets its own IP address on your private network, enabling SSH access, file sharing, and even running web servers from within the browser. The CheerpX JIT engine delivers near-native performance for compute-bound workloads.

## PCjs: Faithful Period-Accurate Hardware Emulation

PCjs (PC JavaScript) is a labor of love by Jeff Parsons that recreates historical IBM PC hardware with meticulous attention to detail. Unlike v86 and WebVM which focus on performance and modern use cases, PCjs aims to preserve computing history by emulating specific vintage machines — complete with period-accurate ROMs, disk controllers, and display hardware.

**Key Features:**
- Machine-specific emulation: IBM PC (1981), PC XT, PC AT, COMPAQ, and 386-based systems
- Period-accurate hardware: CGA, EGA, VGA, Hercules, MDA displays
- Original ROM BIOS emulation
- Comprehensive library of vintage software pre-loaded
- XML-based machine configuration for defining custom systems
- PCx86, PDPjs, C1Pjs, and other specialized emulators

**Self-Hosting with Docker:**

```yaml
version: "3.8"
services:
  pcjs:
    image: nginx:alpine
    container_name: pcjs
    ports:
      - "8080:80"
    volumes:
      - ./pcjs:/usr/share/nginx/html:ro
    restart: unless-stopped
```

PCjs is deployed as static files — clone the repository and serve it through any web server. The project includes dozens of pre-configured machine definitions and disk images, from the original IBM PC Model 5150 to 386-class machines running Windows 3.1. Every machine configuration is documented in easily-modifiable XML files.

## Deployment Architecture

When deploying browser-based emulators for multi-user access, consider this architecture:

```yaml
version: "3.8"
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./v86:/var/www/v86:ro
      - ./webvm:/var/www/webvm:ro
      - ./pcjs:/var/www/pcjs:ro
    restart: unless-stopped

  v86-relay:
    image: ghcr.io/nicholasescobar/v86-relay:latest
    ports:
      - "8081:8081"
    restart: unless-stopped

  tailscale-webvm:
    image: tailscale/tailscale:latest
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - TS_AUTHKEY=${TS_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
    volumes:
      - ./tailscale-webvm:/var/lib/tailscale
    restart: unless-stopped
```

This setup serves all three emulators from a single nginx instance with SSL termination, while the v86 relay provides networking capabilities and Tailscale enables WebVM's network features.

## Choosing the Right Emulator

**Choose v86 if:**
- You need broad OS compatibility (Windows, Linux, DOS, BSD)
- You want hardware-level emulation with sound and graphics
- Performance is a priority for compute-heavy workloads
- You're hosting a multi-OS emulation platform for users

**Choose WebVM if:**
- You need a full Linux development environment in the browser
- Networking and internet connectivity are essential
- You want package management and modern toolchains
- You're building an educational or development platform

**Choose PCjs if:**
- You're preserving or teaching computing history
- You need period-accurate hardware emulation
- You want pre-configured vintage software libraries
- You're building a computer history museum or archive

All three emulators can coexist on the same server — use nginx as a reverse proxy to route different subdomains or paths to each emulator's files.

## Why Self-Host Your Browser-Based PC Emulators?

Running these emulators on your own infrastructure gives you complete control over the user experience. Self-hosting eliminates reliance on third-party servers that may go offline, throttle usage, or inject tracking scripts. Your users get faster load times since the WebAssembly payloads are served from your local network or nearby CDN.

Data sovereignty is another critical advantage. When users boot operating systems or run software through a self-hosted emulator, no usage data leaks to external analytics services. For organizations handling sensitive data, this is especially important — you can run legacy applications in the browser without exposing data to cloud services. You also control which disk images and software are available, making it ideal for curated educational environments.

For educational institutions, self-hosting provides a consistent, always-available platform. Students can access Windows 95 for retro computing classes, boot Linux for operating system demonstrations, or explore vintage IBM PC architecture — all from Chromebooks or tablets without installing any software. The zero-install nature of browser-based emulation makes it perfect for BYOD environments.

Cost predictability is another benefit. Cloud-hosted emulation services charge per instance-hour or impose usage quotas. Self-hosted emulators run on your hardware with predictable costs — a modest VPS or home server can serve dozens of concurrent users. For more on self-hosting infrastructure, see our [Android emulation guide](../2026-06-07-self-hosted-android-emulation-waydroid-redroid-anbox-guide/) and [retro gaming console guide](../2026-06-06-self-hosted-retro-gaming-consoles-recalbox-batocera-retropie-lakka/). If you're building a broader development environment, check out our [self-hosted game server management guide](../pterodactyl-self-hosted-game-server-management-guide/).

## FAQ

### Can I run Windows 10 or 11 in a browser-based emulator?

Not practically with these tools. v86 supports up to Windows 98/ME era operating systems; WebVM is Linux-only; PCjs covers IBM PC through early 386 systems. Modern Windows requires UEFI, ACPI, and hardware features that are prohibitively complex to emulate in JavaScript/WebAssembly. For Windows 10/11, you'd need a full hypervisor like KVM or Hyper-V with remote desktop access.

### How is performance compared to native virtual machines?

Browser-based emulators are typically 3-10x slower than native VMs for CPU-bound workloads. v86's JIT compiler achieves roughly 20-40% of native speed for compute-intensive code. WebVM's CheerpX engine performs better for I/O-bound tasks but similarly slower for raw computation. For booting operating systems, browsing files, and running productivity software, the performance is perfectly adequate — operating systems feel responsive. Heavy gaming or video encoding would be frustrating.

### Do these emulators work on mobile devices?

Yes, all three work on mobile browsers, though the experience varies. v86 and WebVM work best on tablets with keyboards due to the need for mouse/keyboard input. PCjs is more usable on phones since vintage systems had simpler interfaces. iOS Safari has historically limited WebAssembly performance, but recent versions have improved significantly. Android Chrome handles all three emulators well.

### Can I make the emulated OS persist data across sessions?

Yes, all three support persistent storage. v86 uses the 9P filesystem protocol to write changes back to a server or IndexedDB. WebVM supports 9P filesystem mounts for persistent state. PCjs saves machine state to disk images. For multi-user deployments, you'll want to configure per-user storage volumes and possibly snapshot/restore capabilities.

### Are there security risks with running arbitrary code in browser emulators?

The emulated code runs entirely within the browser's WebAssembly sandbox, which is isolated from the host system. The x86-to-WASM JIT compilers only generate safe WebAssembly instructions. However, if networking is enabled, the guest OS could potentially reach other devices on your network (especially with WebVM's Tailscale integration). Isolate emulator instances on a separate VLAN or use firewall rules if this is a concern.

### What are the minimum system requirements for hosting?

A server with 2 CPU cores and 4GB RAM can handle 5-10 concurrent users for v86 and PCjs (they're mostly serving static files plus WebAssembly compilation). WebVM is more resource-intensive — each instance uses 512MB-1GB RAM and benefits from more CPU cores. For 20+ concurrent users, plan for 8GB+ RAM and 4+ cores. Storage requirements are modest (a few GB for disk images).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Browser-Based PC Emulators: v86 vs WebVM vs PCjs",
  "description": "Comprehensive comparison of self-hosted browser-based PC emulators: v86, WebVM, and PCjs. Learn how to run x86 operating systems directly in the browser with Docker deployment guides.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
