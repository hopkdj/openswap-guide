---
title: "Smalltalk Web Stacks in 2026: Pharo + Seaside vs Squeak vs GNU Smalltalk"
date: "2026-09-15"
tags: ["self-hosted", "web-frameworks", "smalltalk", "open-source"]
draft: false
cover: "/img/screenshots/seaside-control-panel.jpg"
---

Smalltalk invented the ideas the rest of us spent thirty years rediscovering: MVC, the object browser, live programming, and — most relevant here — **deploying a running system by saving a snapshot of its live memory**. In 2026 that makes it the strangest and most efficient web stack you can put on a server: your production process is a file you can copy, version, and restart in seconds.

This guide compares the three Smalltalk implementations that still matter for server-side web work in 2026 — **Pharo** (with Seaside), **Squeak** (plus its TruffleSqueak and SqueakJS runtimes), and **GNU Smalltalk** — using live repository data rather than fond memories of the 1990s.

## TL;DR — Quick Verdict

**Choose Pharo + Seaside if you are building a real web application.** It has the largest community, the most active repository, a documented minimal image built specifically for headless server deployment, and the only first-class Seaside install path. **Choose Squeak (or TruffleSqueak) if you want the friendly graphical image and modern JVM hosting** — TruffleSqueak runs Squeak on GraalVM, which means your Smalltalk web app can live inside your existing Java infrastructure. **Choose GNU Smalltalk only for scripting**, not for web work: it is a small, fast, file-based Smalltalk with no supported Seaside path and no image-snapshot workflow.

## The Comparison Table (Live GitHub Data)

Star counts and last-push dates pulled from the GitHub API on 2026-09-15.

| Project | What It Is | Stars | Last Push | Deployment Unit | Seaside Support |
|---|---|---|---|---|---|
| **Pharo** (`pharo-project/pharo`) | Full image-based environment, language + IDE + OS-like tooling | 1,484 | 2026-09-12 | Image + VM file pair (+ minimal image for servers) | Yes — primary target |
| **Seaside** (`SeasideSt/Seaside`) | Continuation-based web framework | 561 | 2026-08-08 | Loaded into a Pharo/Squeak/GemStone image | It *is* the framework |
| **Squeak / TruffleSqueak** (`hpi-swa/trufflesqueak`) | Squeak image on GraalVM's Truffle framework | 319 | 2026-09-07 | Image running on the JVM | Yes |
| **SqueakJS** (`codefrau/SqueakJS`) | Squeak VM in the browser | 409 | 2025-09-19 | Static files served over HTTP | Yes (in-browser) |
| **GNU Smalltalk** (`gnu-smalltalk/smalltalk`) | Classic file-based Smalltalk interpreter | 200 | 2026-01-21 | Regular process + `.st` source files | Not a supported target |

The number to notice is not the star counts — it is **2026-09-12**: Pharo is pushing commits this week. A stack almost nobody talks about is still being actively maintained by a small, stubborn community.

## Decision Matrix: Pick in 10 Seconds

| Your Use Case | Recommended Stack | Why |
|---|---|---|
| Ship a real Smalltalk web app to a VPS today | **Pharo + Seaside** | Only supported combination with a documented server image |
| Run Smalltalk inside existing JVM infrastructure | **TruffleSqueak** | Squeak image on GraalVM; same tooling as your Java fleet |
| Teach OOP or demo a live system in a browser | **SqueakJS** | Zero install; the image runs in a browser tab |
| Glue scripts, text processing, one-file utilities | **GNU Smalltalk** | Tiny interpreter, plain source files, no image management |
| Hot-swap code in a running production server | **Pharo + Seaside** | Deployment *is* saving the live image |
| Long-running stateful interactive app (wizards, workflow) | **Pharo + Seaside** | Continuations make multi-step flows trivial |

## Pharo + Seaside — The Stack That Actually Deploys

Pharo is the modern, aggressively maintained Smalltalk: a language, an IDE, and an environment shipped as a single *image* file executed by a small virtual machine. For web work, the pairing is Pharo as the runtime and **Seaside** as the framework.

Getting a running image is a download, not a build:

```bash
# Full image with the graphical environment (development)
# https://pharo.org/download  OR the automated builds:
curl -LO http://files.pharo.org/image/120/latest-64.zip

# Minimal image WITHOUT the graphical interface — built for server deployment
curl -LO http://files.pharo.org/image/120/latest-minimal-64.zip
unzip latest-minimal-64.zip
```

That minimal image is the part most people never hear about. The project describes it plainly: it *"contains the basic Pharo packages without the graphical user interface. It is useful as a base for server-side applications deployment."* In other words, a headless production image is an officially published artifact, not a hack.

Next, load Seaside. This is the **verbatim install snippet from the Seaside README**, executed inside the image (via the Pharo playground or the command line):

```smalltalk
Metacello new
 baseline:'Seaside3';
 repository: 'github://SeasideSt/Seaside:master/repository';
 load
```

To pin a release instead of tracking `master` — which you should do in production — the README's versioned form is:

```smalltalk
Metacello new
 baseline:'Seaside3';
 repository: 'github://SeasideSt/Seaside:v3.4.5/repository';
 load
```

After loading, the `Welcome` package starts a default server adaptor on **port 8080**. The Seaside Control Panel appears in the *Library* menu of the Pharo toolbar, which is where you manage adaptors, sessions, and filters:

![Seaside control panel running in Pharo](/img/screenshots/seaside-control-panel.jpg "The Seaside Control Panel managing a server adaptor inside Pharo")

For a headless server, the operational model is refreshingly simple compared to a typical container stack:

1. Build and test the full application image locally.
2. Save the image (this is your build artifact — a single file).
3. Copy the image file and the matching VM binary to the server.
4. Start the VM headless; it restores the running system, adaptors included.
5. Deploy an update by saving a new image, swapping the file, and restarting the VM.

A systemd unit makes the lifecycle explicit and restartable:

```ini
# /etc/systemd/system/seaside.service
[Unit]
Description=Pharo Seaside application
After=network.target

[Service]
User=smalltalk
WorkingDirectory=/opt/seaside
ExecStart=/opt/seaside/pharo --headless /opt/seaside/App.image --no-quit
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Put Caddy or Nginx in front for TLS and static assets, keep 8080 on loopback, and you have a web app whose entire runtime state is two files on disk.

## Squeak, TruffleSqueak, and SqueakJS — Same Image, Three Very Different Hosts

Squeak is the direct descendant of the original Smalltalk-80 work and remains the friendliest graphical image. In 2026 its most interesting variants are about *where* the image runs:

- **TruffleSqueak (319 stars, last push 2026-09-07)** runs the Squeak image on **GraalVM's Truffle framework**. Practically, that means Smalltalk code gets a modern JIT and the image can run on the same JVM infrastructure, monitoring, and container base images as your Java services. If your organisation already runs a JVM fleet and someone wants to write a Seaside app, this is the path with the least friction.
- **SqueakJS (409 stars)** implements the Squeak virtual machine in JavaScript, so the image runs directly in a browser tab with no plugin and no install. That makes it the cheapest possible way to publish an interactive Smalltalk demo — and a genuinely unusual option for teaching, since students see a live object system without installing anything.
- **Seaside itself** lists Squeak among its supported platforms alongside Pharo, GemStone, and the VAST Platform, so the framework layer is not the limiting factor here.

## GNU Smalltalk — Excellent at the Job It Was Not Designed For

GNU Smalltalk takes the opposite approach to Pharo: no image snapshot to manage, no IDE, just an interpreter that runs `.st` files. It is packaged in most distributions, which is why it still turns up in tutorials:

```bash
sudo apt install gnu-smalltalk
gst hello.st
```

Where it shines: command-line scripting, text munging, and acting as an embeddable scripting language in a larger system — all in a few megabytes with no snapshot semantics to reason about. Where it does not: **the Seaside README lists Pharo, GemStone, Squeak, and the VAST Platform as its supported starting platforms. GNU Smalltalk is not among them.** If your plan is "GNU Smalltalk plus Seaside," you are choosing the one combination in this article with no supported install path — pick Pharo instead.

## Pitfalls: Image-Based Deployment Bites Back

- **Never overwrite a running image.** Pharo writes the snapshot in place. Save a new image under a new name, verify it starts, then move your service to it. Overwriting the live file is how people lose an afternoon.
- **Images are tied to a VM version and CPU architecture.** A 64-bit ARM image does not run on an x86-64 VM binary. Ship the VM alongside the image, and pin both.
- **Saving is not a backup.** A corrupt image is a corrupt application. Keep at least the previous two images plus your source packages (Metacello baselines make the source reproducible).
- **Seaside sessions and reverse proxies.** Seaside keeps server-side session state; if you scale to multiple images, you need sticky sessions or a shared session store. A single-image deployment with a reverse proxy avoids the problem entirely — which is exactly why clubs and small teams run it that way.
- **Port 8080 is the default adaptor port.** Change it, or bind to loopback and let your proxy own the public port.
- **No official Docker image to lean on.** You will wrap the VM and image yourself. That is a five-line Dockerfile, but it means base-image updates are your job.
- **Don't run a graphical image on a headless server.** Use the minimal image — pulling X11 dependencies onto a VPS for no reason is the classic first-deployment mistake.

## FAQ

**Is Smalltalk still a viable choice for a new web application in 2026?**
Yes, with the right expectations. Pharo is actively developed (commits within days of writing this), Seaside is maintained, and the deployment model is simpler than a container stack for small applications. The real constraint is hiring and library breadth, not the technology.

**What is a Smalltalk image, in one sentence?**
It is a single file containing the entire live object memory of a running system — code, tools, and application state — which the virtual machine restores on startup, making "deployment" equivalent to saving and copying a file.

**Why does Seaside not need routes like other frameworks?**
Seaside applications are built from components with their own state and callbacks, and the framework uses continuations so a multi-step flow (a checkout, a wizard, a configuration assistant) is expressed as ordinary method calls rather than URL routing rules. That model is why Smalltalk teams describe it as the fastest way to build stateful interactive apps.

**Should I choose Pharo or Squeak for a server project?**
Pharo for new work: it has the larger community, more frequent releases, and a published minimal image intended for headless deployment. Choose Squeak when you specifically want the graphical image, or TruffleSqueak when you need the JVM runtime.

**Can I run Smalltalk without any server at all?**
Yes — SqueakJS runs the Squeak virtual machine in JavaScript, so the image executes in a browser tab. It is ideal for demos and teaching, and a poor fit for anything needing persistent server-side storage.

**How much memory does a Pharo deployment need?**
Plan for the VM plus your image in RAM, typically a few hundred megabytes for a small Seaside app — comfortably smaller than the average Node.js or JVM stack, and with no external runtime to keep patched. The bigger operational win is that a restart takes seconds, since the system restores from a snapshot instead of re-reading and re-initialising your application.

For related reading, see our [Common Lisp web stack comparison](../2026-09-11-common-lisp-web-stack-hunchentoot-caveman-clack/) for another long-lived dynamic language that still ships web frameworks, our [Scheme implementations guide](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) for how to pick among the surviving Lisp dialects, and our [Prolog engine comparison](../2026-09-13-prolog-engines-swi-prolog-scryer-trealla-comparison/) if you want a logic-programming runtime on the same kind of hardware.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Smalltalk Web Stacks in 2026: Pharo + Seaside vs Squeak vs GNU Smalltalk",
  "description": "Compare Pharo with Seaside, Squeak, TruffleSqueak, SqueakJS and GNU Smalltalk for server-side web development in 2026, with real install snippets and a production deployment model.",
  "datePublished": "2026-09-15",
  "dateModified": "2026-09-15",
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
