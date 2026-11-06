---
title: "Nix vs Guix in 2026: Which Declarative Package Manager Should Run Your Servers?"
date: "2026-11-07"
tags: ["nix", "guix", "package-management", "reproducible-builds", "linux", "self-hosted", "devops"]
draft: false
cover: "/img/screenshots/nix-logo.jpg"
description: "A hands-on comparison of Nix and GNU Guix in 2026 — reproducibility, server deployment, Docker image builds, flake locks vs channels, and the operational traps nobody warns you about."
---

Your build server and your laptop disagree about which version of OpenSSL is installed. Your Docker image was reproducible last Tuesday and mysteriously isn't today. A dependency you never declared got upgraded because something in `node_modules` pulled it in sideways.

This is the problem declarative package management actually solves — not by pinning versions in a lockfile that describes *what* you want, but by making the entire dependency graph, including the compiler and libc, a first-class content-addressed value. Two systems have done this properly for over a decade: **Nix** and **GNU Guix**. Both are alive, both shipped releases in 2026, and both will happily run your infrastructure. They are also very different in ways that matter once you're past the tutorial.

## TL;DR — Quick Verdict

**Choose Nix if you want the ecosystem.** Nix has 17,978 GitHub stars on the core, 26,736 on nixpkgs, a package set well past 100,000 definitions, native Docker images, and every third-party deployment tool (Colmena, deploy-rs, nixops) targets it. It is the pragmatic choice for production servers in 2026.

**Choose Guix if you want the ideology to be load-bearing.** Guix is GPL-3.0, bootstrappable from a 357-byte binary seed, written in Guile Scheme, and refuses to ship anything that isn't free software by default. It's the only system where "auditable from source" is literally true rather than aspirational.

**If you just want reproducible dev shells and don't care about the OS layer, use Nix** — the tooling gap is not close. Guix wins on principle and auditability; Nix wins on everything you'll touch on a Tuesday afternoon.

## Head-to-Head Comparison

| Dimension | Nix / NixOS | GNU Guix / Guix System |
|---|---|---|
| Core repo | `NixOS/nix` — **17,978 ⭐** | Self-hosted on Codeberg; GitHub mirror **obsolete** (271 ⭐) |
| Package set | `nixpkgs` — **26,736 ⭐**, 100,000+ definitions | ~24,000 packages |
| Latest release | **Nix 2.35.4** (tags, no GH releases) | Guix 1.4.x series |
| Last commit | **2026-11-06** | Active (Codeberg) |
| License | LGPL-2.1 | **GPL-3.0** |
| Implementation language | C++ (with a lazy functional evaluator) | **Guile Scheme** |
| Init system | systemd | **GNU Shepherd** |
| Declarative OS | NixOS | Guix System |
| Pinning mechanism | `flake.lock` (content-addressed) | `channels.scm` + `guix time-machine` |
| Docker support | Official `nixos/nix` image | `guix pack -f docker` |
| Non-free software | Opt-in via `allowUnfree` | Separate `nonguix` channel |
| Learning curve | Steep (Nix language) | Steeper (Scheme + functional OS config) |
| Ecosystem / third-party tooling | Large | Small but coherent |

The star counts are live as of this writing. Note the Guix number: the GitHub repository `guix-mirror/guix` states plainly that it is an obsolete mirror and that development moved to Codeberg. If you evaluate Guix by GitHub activity you will draw exactly the wrong conclusion.

## Decision Matrix — Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| Production Linux fleet, need config management | **NixOS + Colmena** | Mature deploy tooling, systemd, large package set |
| Reproducible CI containers | **Nix flakes** | `flake.lock` pins the whole graph; official Docker base |
| Strict free-software compliance or audit trail | **Guix** | GPL-3.0, bootstrappable, no binary blobs by default |
| Academic/HPC environment already using Scheme tooling | **Guix** | Shepherd + Guile integrate with existing workflows |
| You need a package that isn't in the repo | **Nix** | Far more likely to already exist |
| You want to learn one and never revisit | **Nix** | Bigger community means more answers when stuck |
| Embedding reproducible builds into an existing distro | **Guix `pack`** | Produces relocatable tarballs/docker without changing the host |
| Long-term archival rebuild of old software | **Guix `time-machine`** | Can reconstruct a 2019 environment exactly |

## Nix — The Ecosystem Play

Nix treats a package as a pure function of its inputs. The store path `/nix/store/<hash>-openssl-3.x` embeds a hash of *everything* that went into producing it, so two builds with identical inputs land on the identical path — and any difference in inputs produces a different path instead of silently overwriting.

Install on any Linux or macOS host:

```bash
sh <(curl -L https://nixos.org/nix/install) --daemon
```

The `--daemon` flag sets up the multi-user installation, which is what you want on a server: builds run as an unprivileged `nixbld` user and the store is writable only by the daemon.

### Flakes: the pinning mechanism that actually works

A flake is a directory with a `flake.nix` that declares its inputs and outputs. `flake.lock` records the exact revision of every input, so `nix build` on a colleague's machine three months later resolves the same graph.

```nix
{
  description = "Reproducible service build";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: nixpkgs.lib.genAttrs systems
        (system: f nixpkgs.legacyPackages.${system});
    in {
      packages = forAll (pkgs: {
        default = pkgs.buildGoModule {
          pname = "demo-api";
          version = "1.4.0";
          src = ./.;
          vendorHash = null;
        };
      });

      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = [ pkgs.go pkgs.postgresql_17 pkgs.just ];
        };
      });
    };
}
```

Day-to-day usage is three commands:

```bash
nix develop                 # enter the dev shell defined above
nix build .#default         # produce ./result symlink into the store
nix profile install nixpkgs#ripgrep   # install a tool imperatively
```

Because `go`, `postgresql_17`, and the exact glibc are all store paths, `nix develop` gives every engineer byte-identical toolchains. No version manager, no "did you install Go 1.23 or 1.24", no `asdf` plugin roulette.

![Nix user environments: profiles, generations, and the store](/img/screenshots/nix-user-environments.jpg "Nix manual figure showing how profiles and generations point into the immutable store")

### NixOS for servers

NixOS makes the *entire machine* a declarative value. `/etc/nixos/configuration.nix` declares users, services, firewall rules, and kernel parameters; `nixos-rebuild switch` builds a new system generation and flips a symlink. Rollback is `nixos-rebuild switch --rollback` and takes about two seconds — the previous generation is still in the store, untouched.

For multi-host fleets, pair NixOS with a deployment tool. Our [Nix deployment systems comparison](../2026-05-14-nix-deployment-systems-nixops-colmena-deploy-rs-guide/) covers Colmena, deploy-rs, and nixops in depth, and [the binary cache guide](../2026-04-27-attic-vs-harmonia-vs-niks3-self-hosted-nix-binary-cache-guide-2026/) explains how to avoid rebuilding everything on every host.

A usable container base is one line:

```bash
docker run -it nixos/nix
```

## GNU Guix — The Auditable Play

Guix is Nix's ideas reimplemented in Guile Scheme with a hard commitment to software freedom. Its distinguishing feature is **bootstrappability**: the entire distribution can be rebuilt from a 357-byte binary seed, using a staged sequence of increasingly capable compilers. No opaque binary blobs hide at the bottom of the trust chain.

Install via the official script:

```bash
# download and run the installer (verify the signature first in production)
wget https://git.savannah.gnu.org/cgi-bin/gitweb.cgi?p=guix.git\;a=blob_plain\;f=etc/guix-install.sh\;hb=HEAD -O guix-install.sh
chmod +x guix-install.sh && ./guix-install.sh
```

Package operations mirror Nix's:

```bash
guix install nginx postgresql
guix upgrade
guix describe -f channels > channels.scm   # snapshot the exact channel revisions
guix time-machine -C channels.scm -- install python@3.11   # rebuild the old world
```

`guix time-machine` is the feature that quietly justifies the whole system for archival work: you can reconstruct an environment as it existed on a specific date, because the channel file pins every package definition *and* the Guix revision that evaluated them.

### Producing containers without Docker as a build dependency

Guix doesn't need a Docker daemon to emit a container:

```bash
guix pack -f docker -S /bin=bin nginx
docker load < /gnu/store/xxxxxxxx-nginx-docker-image.tar.gz
docker run --rm -p 8080:80 nginx
```

The `-S /bin=bin` flag creates the `/bin` symlink that most images assume exists. This produces a genuinely minimal image because only the closure of `nginx` is included — no shell, no package manager, no base OS.

### Guix System

The OS layer is a Scheme record. This is a complete, bootable server definition:

```scheme
(use-modules (gnu) (gnu services ssh) (gnu services web))
(use-service-modules networking ssh web)

(operating-system
  (host-name "edge-01")
  (timezone "Europe/Berlin")
  (locale "en_US.utf8")
  (bootloader (bootloader-configuration
                (bootloader grub-efi-bootloader)
                (targets '("/boot/efi"))))
  (file-systems (cons (file-system
                        (device (file-system-label "guix-root"))
                        (mount-point "/")
                        (type "ext4"))
                      %base-file-systems))
  (users (cons (user-account
                 (name "deploy")
                 (group "users")
                 (supplementary-groups '("wheel" "netdev")))
               %base-user-accounts))
  (services
    (append (list (service nginx-service-type)
                  (service openssh-service-type))
            %base-services)))
```

`guix system reconfigure /etc/config.scm` builds and activates it; the previous generation stays selectable at the GRUB menu. The init system is GNU Shepherd, not systemd — a Scheme-based service manager that is elegant, far smaller, and the single biggest practical adjustment for anyone arriving from a conventional distro.

## Where Both Systems Bite You

These are the traps that cost real hours, not the ones in the marketing pages.

**Store growth is unbounded.** Every generation, every dev shell, every `nix build` leaves content in `/nix/store` forever until you collect it. On Nix: `nix-collect-garbage -d` deletes all old generations; `nix store gc` is the gentler current form. On Guix: `guix gc -d 30d` deletes generations older than 30 days. A default cloud VM with a 20 GB disk will fill up within weeks of active flake development. Mount `/nix` or `/gnu` on a separate volume from day one.

**Shebangs and hardcoded paths break.** Scripts that begin `#!/bin/bash` or reference `/usr/bin/env python3` fail inside a pure build sandbox, because those paths don't exist. Fix shebangs with `patchShebangs` on Nix or `patch-shebang` phases on Guix, and never hardcode interpreter paths in your own scripts.

**Non-free software is deliberately awkward** — and this is where the two systems diverge sharply. Nix requires `nixpkgs.config.allowUnfree = true;`. Guix requires adding the `nonguix` channel, which the project does not endorse. If you depend on a proprietary firmware blob, a vendor JDK, or NVIDIA drivers, budget an afternoon for either.

**`/etc` is not yours to edit.** On both systems, hand-editing files under `/etc` produces changes that vanish at the next rebuild. Declare them via `environment.etc` (Nix) or `extra-special-file` / service configuration (Guix). This is the single most common migration failure for teams coming from Ansible-managed hosts.

**Flake locks don't update themselves.** `nix flake update` is a deliberate action. Teams that never run it accumulate a year of frozen dependencies and then face one enormous, unbisectable upgrade. Schedule it quarterly.

**Guix's package set is roughly a quarter the size** of nixpkgs, and packages that exist may lag upstream by months. Check availability *before* committing to the migration, not after.

## Why Bother With Either?

The case is operational, not aesthetic. When a CVE lands in glibc, you want to answer "which of my 40 hosts are affected" in one query rather than 40 SSH sessions. When a build breaks, you want the previous artifact still addressable so rollback is a symlink flip. When an auditor asks what's in the production image, you want a derivation graph rather than a `docker history` output full of `RUN apt-get install` layers.

Both systems deliver that. Nix delivers it with a large community, a familiar init system, and near-total package coverage. Guix delivers it with a stronger guarantee about what's actually inside the binary you're running.

If you're still deciding how far to go, our [comparison of devbox, Nix, and dev containers](../2026-05-03-devbox-vs-nix-vs-dev-containers-self-hosted-dev-environment-managers/) is the lighter-weight starting point — it covers adopting reproducible toolchains without taking on a new OS.

## FAQ

### Is Guix just a Nix clone?

No. Guix shares the functional-derivation model and the content-addressed store concept, but it is an independent implementation in Guile Scheme, uses GNU Shepherd instead of systemd, has its own package definitions, and enforces free-software policy by default. The two are conceptually siblings and operationally incompatible — you cannot mix a Nix store and a Guix store.

### Can I run Nix or Guix on an existing Ubuntu or Debian server?

Yes, both install as a package manager alongside your existing system, without replacing it. Nix's `--daemon` installer and Guix's install script both work on a conventional distro. The OS layer (NixOS, Guix System) is a separate, optional commitment.

### Which one produces smaller container images?

Guix typically produces smaller images for simple services because `guix pack -f docker` includes only the exact closure of the requested package — no shell, no package manager. With Nix you can achieve similar results using `dockerTools.buildImage` with a minimal `contents` list, but the default `nixos/nix` base image is a full toolchain and should never be your production base.

### How much disk space does the store actually use?

A fresh NixOS installation with a few services sits around 4–8 GB. Active flake development adds several GB per week until garbage collection runs. Guix is comparable. Treat 40 GB as a realistic minimum for `/nix` or `/gnu` on a development machine, and enable automatic GC (`nix.gc.automatic` on NixOS) from the start.

### Do either of these work on ARM and in CI?

Both support `aarch64-linux` and `x86_64-linux` fully, and both have `darwin` support (Nix natively, Guix experimentally via `arm64` ports). For CI, the practical pattern is a binary cache: build once on a trusted builder, push to a cache like Attic or Cachix, and let every other machine substitute rather than rebuild.

### Which should I learn in 2026 if I only learn one?

Nix. The tooling ecosystem, the volume of written material, and the odds that your next employer already uses it all favor Nix. Learn Guix afterward if you care about bootstrap auditability or work in free-software-committed environments — the mental model transfers almost entirely, and Guix's Scheme configuration is arguably the more pleasant of the two once it clicks.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nix vs Guix in 2026: Which Declarative Package Manager Should Run Your Servers?",
  "description": "Hands-on comparison of Nix and GNU Guix in 2026: reproducibility, server deployment, Docker image builds, flake locks vs channels, and operational traps.",
  "datePublished": "2026-11-07",
  "dateModified": "2026-11-07",
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
