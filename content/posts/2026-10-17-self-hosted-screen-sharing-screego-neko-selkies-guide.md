---
title: "Screego vs Neko vs Selkies in 2026: Which Self-Hosted Screen Sharing Stack Actually Works?"
date: "2026-10-17"
tags: ["self-hosted", "webrtc", "screen-sharing", "remote-desktop", "comparison", "docker"]
draft: false
cover: "/img/screenshots/selkies-screenshot.jpg"
---

Sharing your screen should not require a corporate account, a 4-second delay between your cursor and your colleague's monitor, or a subscription that bills per seat. Yet that is exactly what teams put up with every day — and it gets worse when the thing you need to share is not your laptop screen but *an isolated browser session* for testing a checkout flow, or a containerised desktop for a support engineer who is not allowed to install anything locally.

Three open-source projects cover this space in 2026, and they solve genuinely different problems: **Screego** (10,737 stars) is low-latency screen sharing for developers, **Neko** (22,509 stars) streams a disposable browser or full desktop from a container, and **Selkies** (2,337 stars) is a GPU-accelerated WebRTC/WebSocket streaming platform for containerised desktops. Picking the wrong one means fighting an architecture that was never designed for your use case.

## TL;DR — the 30-second verdict

- **Choose Screego** if you want "share my screen with the team, now", with real code legibility and sub-second latency. It is the simplest of the three and has the smallest attack surface.
- **Choose Neko** if you need a throwaway browser in a container — QA on a clean profile, a shared watch-party, or a virtual desktop several people can drive at once.
- **Choose Selkies** if you are streaming a full desktop session (LXQt, XFCE) out of a container or Kubernetes pod and want GPU-accelerated encoding with WebSocket fallback for restrictive networks.

One line to remember: **Screego shares your screen, Neko shares a browser, Selkies shares a whole desktop.**

## Side-by-side comparison (GitHub data, October 2026)

| | Screego | Neko | Selkies |
|---|---|---|---|
| GitHub stars | 10,737 | **22,509** | 2,337 |
| Latest release | v1.12.6 (2026-09-27) | **v3.2.0 (2026-10-15)** | 2.0.0 (2026-09-23) |
| Transport | WebRTC + integrated TURN | WebRTC (Pion) | WebRTC **or** WebSockets (dual mode) |
| What is streamed | The host's own screen | Containerised browser / app / desktop | Containerised Linux desktop |
| Multi-user control | View-only (+ audio) | **Yes — multiple drivers** | Yes (single session) |
| GPU acceleration | Not applicable | Optional (Intel/NVIDIA/RPi images) | **Yes — NVENC, VA-API, /dev/dri** |
| Image size / weight | ~40 MB binary, single container | Large (full browser stack) | Large (desktop + encoder stack) |
| Kubernetes-friendly | Basic | Yes | **Designed for it** |
| Auth model | Room-based, optional TURN creds | User/admin passwords, optional OAuth | Basic auth, HTTPS, TURN secrets |
| Best fit | Dev pairing, reviews | QA, kiosks, shared browsing | VDI, HPC desktops, GPU workloads |

## Decision matrix — pick in ten seconds

| Your use case | Pick | Reason |
|---|---|---|
| Pair programming with a colleague across the ocean | **Screego** | Native-resolution text, sub-second latency, no container overhead |
| Show a design review to 6 people at once | **Screego** | Multi-user rooms, no per-seat cost |
| Test a checkout flow with a clean browser profile | **Neko** | Disposable container, no local state leaking into the test |
| Let two support engineers co-drive the same browser | **Neko** | Multiple controllers by design |
| Run a browser kiosk on a TV in the office | **Neko** | Kiosk image, restart policies, no desktop needed |
| Ship a full Linux desktop to remote staff | **Selkies** | LXQt session streamed from a container |
| Stream a GPU workload (Blender, simulation) | **Selkies** | Hardware encoding and `/dev/dri` passthrough |
| Locked-down network where UDP is blocked | **Selkies** | WebSocket mode works over plain TCP/443 |
| Deploy on Kubernetes at scale | **Selkies** | Built for pods, dashboards and TURN add-ons |

![Neko streaming a containerised browser over WebRTC (official project artwork)](/img/screenshots/neko-social-card.png "Neko browser-in-a-container streaming, from the official m1k1o/neko repository")

## Screego — the fastest path to "look at my screen"

Screego solves one problem and refuses to solve any other. It does not give anyone remote control; it streams your screen at a resolution where code stays readable. The author built it because conferencing tools crushed text quality during code reviews, and that focus shows: the whole server is a single Go binary or one container.

Installation is documented in the project's own repository and works with host networking (recommended, because Screego runs an integrated TURN server):

```bash
# Official Docker one-liner from screego docs/install.md
docker run --net=host -e SCREEGO_EXTERNAL_IP=EXTERNALIP ghcr.io/screego/server:1.12.6
```

If you cannot use host networking, the documented compose form maps the signalling port, the TURN port and the media port range explicitly:

```yaml
# docker-compose.yml — from screego docs/install.md
services:
  screego:
    image: ghcr.io/screego/server:1.12.6
    ports:
      - 5050:5050
      - 3478:3478
      - 50000-50200:50000-50200/udp
    environment:
      SCREEGO_EXTERNAL_IP: "203.0.113.10"
      SCREEGO_TURN_PORT_RANGE: "50000:50200"
```

Two configuration details decide whether Screego works at all. First, **TLS is mandatory** — either terminate it inside Screego or put it behind a reverse proxy. WebRTC screen capture through a browser will not initialise on a plain-HTTP origin. Second, configuration is read in a strict precedence order, and the first value found wins:

```
Environment variables → screego.config.local → screego.config
  → $HOME/.config/screego/server.config → /etc/screego/server.config
```

That means an environment variable in your compose file silently overrides the config file sitting next to the binary. If a setting "will not take effect", check the environment first — it is almost always the culprit.

**Where Screego disappoints:** there is no remote control, no recording, and no persistent session. It is a live screen, nothing more.

## Neko — a disposable browser (or desktop) in a container

Neko inverts the model: nobody shares their own machine. Instead, a container runs Firefox, Chromium, or an entire desktop, and participants join the session over WebRTC. Because the browser lives in the container, every session starts clean — no cookies, no extensions, no logged-in corporate accounts — which makes it the best tool available for reproducing a customer's checkout problem in a sterile environment.

The repository ships several ready-made compose examples; the simple-browser one is the canonical starting point:

```yaml
# docker-compose.yaml — from m1k1o/neko examples/simple-browser
services:
  neko:
    image: "ghcr.io/m1k1o/neko/firefox:latest"
    restart: "unless-stopped"
    shm_size: "2gb"
    ports:
      - "8080:8080"
      - "52000-52100:52000-52100/udp"
    environment:
      NEKO_DESKTOP_SCREEN: '1920x1080@30'
      NEKO_MEMBER_MULTIUSER_USER_PASSWORD: neko
      NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD: admin
      NEKO_WEBRTC_EPR: 52000-52100
      NEKO_WEBRTC_ICELITE: 1
      # NEKO_WEBRTC_NAT1TO1: <your-public-IP>
```

Swap the image for `ghcr.io/m1k1o/neko/chromium`, `google-chrome`, `brave`, `tor-browser` or `microsoft-edge` and you have a different disposable browser with the same settings — a genuinely pleasant design decision. Mount `./profile:/home/neko/.mozilla/firefox/profile.default` if you want bookmarks and extensions to survive a restart.

Three operational notes worth knowing before you deploy:

- **`shm_size: "2gb"` is not optional.** Chromium and Firefox abort on heavy pages with Docker's 64 MB default shared-memory segment. This single line causes more "Neko crashes on YouTube" reports than anything else.
- **`NEKO_WEBRTC_ICELITE: 1`** tells the server it has a public IP and can skip full ICE negotiation. It is correct behind a cloud VM with a public address and wrong behind a NAT — there you need `NEKO_WEBRTC_NAT1TO1` set to the public IP instead.
- **UDP port ranges must survive the firewall.** Ports 52000–52100/udp are the media path; opening only 8080 gives you a black screen with a working control panel, a failure mode that looks like a browser bug but is pure networking.

**Where Neko disappoints:** each session is heavy. You are paying for a full browser stack in RAM per container, and GPU images are worth it only if you actually stream video.

## Selkies — GPU streaming for containerised desktops

Selkies is the infrastructure-grade option: a low-latency streaming platform designed for containers, Kubernetes and HPC clusters, with **dual-mode transport** — WebRTC when UDP is available, WebSockets when it is not. That fallback is why it is the only one of the three that survives a corporate network that blocks everything except 443/TCP.

Its repository ships a development stack with distinct build targets, and the compose file documents each one in comments — build the wheel, build a base session image, then layer the LXQt desktop on top:

```bash
# From the official selkies docker-compose.yml comments
docker compose build dist                 # Python wheel image
docker compose build base desktop         # session container, then the desktop layer
docker compose up desktop                 # serves http://localhost:8080
docker compose --profile gpu up desktop-gpu   # NVIDIA, needs the container toolkit
```

The desktop service is configured entirely through `SELKIES_*` variables, which is convenient because it means one image serves many roles:

```yaml
# Excerpt: selkies desktop service configuration
environment:
  SELKIES_MODE: websockets            # websockets | webrtc | dual
  SELKIES_ENABLE_DUAL_MODE: "true"    # negotiate the best transport per client
  SELKIES_PORT: "8080"
  SELKIES_ENABLE_HTTPS: "false"       # self-signed certificate if none configured
  SELKIES_ENABLE_BASIC_AUTH: "true"
  SELKIES_BASIC_AUTH_USER: operator
  SELKIES_BASIC_AUTH_PASSWORD: change-me-please
  START_LXQT: "true"                  # full desktop session, not just the display server
  SELKIES_WAYLAND: "false"            # true switches the headless backend
```

Leave the TURN variables empty and Selkies starts an internal coTURN instance for WebRTC peers; set `SELKIES_TURN_HOST` and the REST credentials when you already operate a TURN service and want to reuse it. For GPU nodes, the compose file's `desktop-gpu` profile passes `/dev/dri` through for AMD/Intel and requests NVIDIA devices with all capabilities — a configuration that is notoriously fiddly to write by hand and is worth copying verbatim.

**Where Selkies disappoints:** it is a platform, not an appliance. You will edit compose files, choose distribution base images, and think about encoders. Expect half a day of setup rather than ten minutes.

## Pitfalls that will cost you an evening

**TLS everywhere.** Screego refuses to initialise capture on HTTP, Neko's WebRTC handshake fails on insecure origins in modern browsers, and Selkies mints a self-signed certificate by default. Terminate TLS at your reverse proxy and forward `X-Forwarded-Proto`.

**UDP is the media path.** Every one of these tools needs a UDP range open. If your provider's firewall blocks it, WebRTC degrades to a black screen or never connects. Verify with `nc -u -v` from outside the network before blaming the application — and pick Selkies if UDP is truly unavailable.

**Shared memory and file descriptors.** `shm_size` under 1 GB breaks browsers, and running many concurrent sessions needs a raised `nofile` limit. Both are one-line fixes that are invisible until load hits.

**Authentication is not optional on a public IP.** A Neko or Selkies instance reachable from the internet without credentials is a remote desktop for anyone who port-scans you. Always set the member/admin passwords, or put it behind an authenticating proxy.

**Bandwidth assumptions.** A 1080p session runs roughly 3–8 Mbit/s per viewer. Ten people in one Screego room is a 40 Mbit/s upload on the host — check your uplink before inviting the whole company.

## Why self-host screen sharing instead of buying seats?

Three reasons. **Cost:** commercial screen-sharing and remote-desktop products commonly charge $10–$30 per user per month, so a 20-person team crosses $5,000 a year; all three tools here run on a single $10–$20 VPS. **Control:** the media never touches a third-party relay, which matters for regulated work where screen contents can include customer data. **Capability:** containerised browsers and GPU desktops are things SaaS vendors simply do not sell you at a sane price.

If your real need is full remote control of workstations rather than screen viewing, our [Guacamole vs RustDesk vs MeshCentral self-hosted remote desktop guide](../self-hosted-remote-desktop-guacamole-rustdesk-meshcentral-guide/) covers the access-management side properly, and the [VNC server comparison of noVNC, TigerVNC and x11vnc](../2026-04-27-novnc-vs-tigervnc-vs-x11vnc-self-hosted-vnc-guide/) is the right starting point if you are still on legacy protocols. Building a real-time app on top of these transports? The [Janus vs Mediasoup vs LiveKit SFU comparison](../2026-04-25-janus-gateway-vs-mediasoup-vs-livekit-self-hosted-webrtc-sfu-guide-2026/) explains the media-server layer underneath.

## FAQ

### Is Screego a replacement for Zoom or Google Meet?

No, and it does not try to be. Screego shares a screen and nothing else — there is no video grid, no chat history, no meeting recording. It is best used alongside a normal voice call: keep the call where it is and move the screen sharing to your own server for full resolution and low latency.

### Can several people control the same browser in Neko?

Yes. Neko is built as a multi-user environment where participants can be regular users or administrators, and administrators can grant control. That makes it the best fit for collaborative QA sessions, support hand-overs and shared demos where the person driving changes from minute to minute.

### Does Selkies work without WebRTC?

Yes — that is its key differentiator. Selkies supports `websockets`, `webrtc`, or `dual` modes. In WebSocket mode the session is delivered over a normal TCP connection, so it works through restrictive proxies and firewalls that block UDP entirely, at the cost of somewhat higher latency.

### How much RAM does a containerised browser session need?

Budget 2 GB per session for a browser-only container, and 4 GB or more for a full desktop session with a compositor. Compressed and shared memory helps, but browser tabs are still the dominant cost. On a 16 GB host, four to six concurrent sessions is a realistic ceiling before you need more hardware.

### Do I need a GPU for self-hosted screen streaming?

Only if you are streaming video-heavy content or a GPU workload. Screego needs no GPU because it captures the host's screen. Neko and Selkies both run on CPU with software encoding, which is fine for one or two viewers of a mostly static screen, but hardware encoding (NVENC or VA-API) is what makes multi-viewer 1080p streams smooth.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Screego vs Neko vs Selkies in 2026: Which Self-Hosted Screen Sharing Stack Actually Works?",
  "description": "Practical comparison of Screego, Neko and Selkies for self-hosted screen sharing, containerised browsers and GPU-accelerated desktop streaming, with official Docker Compose configs and networking pitfalls.",
  "datePublished": "2026-10-17",
  "dateModified": "2026-10-17",
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
