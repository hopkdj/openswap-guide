---
title: "nginx vs Angie vs Freenginx in 2026: Which Fork Should Actually Serve Your Traffic?"
date: "2026-11-13"
tags: ["nginx", "web-server", "self-hosted", "reverse-proxy", "comparison"]
draft: false
description: "nginx, Angie and Freenginx compared as production web servers in 2026 — configuration differences, built-in metrics, module compatibility, migration steps and the traps that break a drop-in swap."
---

The web server that terminates TLS for half the internet is now three projects. **nginx** (32,115 GitHub stars on the official mirror, BSD-2) is the one everyone knows. **Angie** (2,616 stars, BSD-2, latest release 1.12.4 shipped 2026-10-16) is a fork maintained by former nginx core developers who wanted features upstream would not take. **Freenginx** is the other fork, created in February 2024 after the maintainer of nginx's public development objected to corporate control of the process — and it deliberately has no company behind it at all.

Choosing between them is not a religious question. It comes down to whether you need features nginx does not ship, whether you need a governance model that cannot be bought, and whether your deployment can survive without vendor binary packages. All three run the same configuration language, which makes the decision easier to get wrong than it looks.

## TL;DR — the 30-second verdict

- **Stay on nginx** for anything with a commercial support contract, a hardened distro package, or third-party modules compiled against nginx headers. It is still the safest default and it is not standing still.
- **Move to Angie** if you want the features nginx keeps out: built-in Prometheus metrics, sticky upstream sessions, an MQTT proxy, and native ACME certificate issuance — without bolting on Lua or a sidecar exporter.
- **Move to Freenginx** only if governance is your actual requirement, and only if you are comfortable building from source. There are no official binary packages, and that is a deliberate design decision, not a gap waiting to be filled.

## The comparison table (data pulled from GitHub and project releases on 2026-11-13)

| Dimension | nginx | Angie | Freenginx |
|---|---|---|---|
| GitHub stars (mirror) | 32,115 | 2,616 | No official GitHub repo |
| Last activity | 2026-11-09 | 2026-11-12 (1.12.4, 2026-10-16) | Mercurial, `hg.nginx.org/freenginx` |
| License | BSD-2 | BSD-2 | BSD-2 |
| Governance | F5 / NGINX Inc. | Web Server LLC (fork team) | Maintainer-led, no corporate owner |
| Config compatibility | Baseline | Drop-in with nginx configs | Drop-in with nginx configs |
| Official binary packages | Yes, broad distro coverage | Yes: RHEL, Debian, Ubuntu, Alpine, Docker | No, source builds |
| Built-in Prometheus metrics | No (needs exporter or Plus) | Yes | No |
| Sticky upstream sessions | No (Plus only) | Yes | No |
| MQTT proxying | No | Yes, native module | No |
| Built-in ACME client | No | Yes | No |
| HTTP/3 | Yes | Yes | Yes, tracks upstream |
| Dynamic module ecosystem | Large | Own packages, nginx modules do not load | Same as nginx |

## Decision matrix: pick by constraint

| Your situation | Pick | Why |
|---|---|---|
| You run distro-packaged nginx and it works | **nginx** | Zero migration risk, security updates arrive through apt/dnf |
| You need per-request metrics without a sidecar | **Angie** | The `api` and `status` modules expose JSON and Prometheus output natively |
| You terminate TLS for hundreds of vhosts | **Angie** | Automatic certificate reload and built-in ACME remove a whole cron job |
| You proxy MQTT for IoT devices | **Angie** | Native `mqtt` module instead of an extra broker hop |
| You need session affinity without nginx Plus | **Angie** | `sticky` directive in upstream blocks |
| You refuse to depend on a single vendor | **Freenginx** | Development happens in public, no commercial roadmap gate |
| You cannot build from source | **nginx** or **Angie** | Freenginx ships no binaries |

## nginx — the baseline that everything is compared against

nginx's model has not changed in years: a master process, worker processes, an event loop, and configuration files that are re-read on `nginx -s reload`. What has changed is that the free version has quietly accumulated the features people used to buy Plus for — HTTP/3, `limit_req` improvements, and in recent versions a much better stream module.

A minimal production reverse proxy, unchanged across all three forks:

```nginx
# /etc/nginx/nginx.conf (excerpt)
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 8192;
    multi_accept on;
}

http {
    # TLS 1.3 + HTTP/2 + HTTP/3 on the same listener
    server {
        listen 443 ssl;
        listen 443 quic reuseport;
        http2 on;
        http3 on;

        server_name app.example.com;
        ssl_certificate     /etc/nginx/certs/app.crt;
        ssl_certificate_key /etc/nginx/certs/app.key;

        add_header Alt-Svc 'h3=":443"; ma=86400' always;

        location / {
            proxy_pass http://127.0.0.1:8080;
            proxy_set_header Host              $host;
            proxy_set_header X-Real-IP         $remote_addr;
            proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
        }
    }
}
```

The honest limitation is observability. If you want per-vhost request counts, upstream latency histograms or active connection gauges, you install `nginx-prometheus-exporter` and a stub_status endpoint, or you pay for Plus. That exporter gives you global counters, not the per-zone breakdown most operators actually want.

## Angie — the fork that shipped the missing features

Angie is developed by a team that includes people who wrote parts of nginx itself, and its pitch is not "we forked out of anger" but "here are the features you have been asking for." The list is unusually concrete.

**Built-in metrics.** Angie's `status_zone` plus the `api` module gives you a JSON REST endpoint, and the status module renders Prometheus-format output. No exporter, no Lua, no sidecar:

```nginx
# /etc/angie/angie.conf (excerpt)
upstream app_backend {
    zone app_backend 64k;
    server 10.0.0.11:8080;
    server 10.0.0.12:8080;
    sticky cookie srv_id expires=1h path=/;
}

server {
    listen 443 ssl;
    http3 on;
    server_name app.example.com;
    status_zone app_vhost;

    location / {
        proxy_pass http://app_backend;
    }

    # JSON API for metrics, scraped over the internal network only
    location /status/ {
        api /status/;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

`sticky cookie` is the feature that makes people switch. Session affinity without Plus, implemented in the upstream block rather than in a Lua script that has to hash and rewrite cookies.

**Other features worth naming:** a native `mqtt` proxy module (useful if you run IoT devices and do not want a broker hop in front of TCP), automatic TLS certificate reload when files change on disk, and a built-in ACME client so certificate issuance no longer requires certbot and a reload hook.

Deployment is the part that decides it for most teams. Angie publishes packages for the major RPM and DEB distributions and an official container image, so migration is a package swap plus a `angie -t` config test:

```bash
# Debian/Ubuntu, official Angie repository
sudo apt install -y angie angie-modules
sudo angie -t
sudo systemctl enable --now angie
```

Note `angie-modules` — Angie ships its own module packages, and that detail matters for the next section.

## Freenginx — governance as the feature

Freenginx exists because its maintainer objected to the way nginx development was being managed after the fork announcement of early 2024: security fixes routed through corporate channels, changes shipped without public discussion, and the public repository becoming a downstream of an internal one. The fork's stated goal is narrower and more political than Angie's: keep nginx development open, keep security work in public, and let the people who write the code decide what goes in.

Practically, this means:

- **No binary packages.** You build from Mercurial sources. If your organisation's patching pipeline assumes `apt upgrade` covers your web server, this fork is not for you.
- **No new feature marketing.** Freenginx tracks upstream's release numbering from the 1.25.3 fork point and focuses on correctness and security rather than a feature list.
- **Configuration is identical.** It is nginx. Same directives, same module API, same reload semantics.

A build looks like this, and it is the normal nginx build process with a different source URL:

```bash
# Build Freenginx from source (Debian/Ubuntu)
sudo apt install -y build-essential libpcre2-dev zlib1g-dev libssl-dev
hg clone https://freenginx.org/hg/nginx freenginx
cd freenginx
./auto/configure \
  --prefix=/opt/freenginx \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_v3_module \
  --with-http_realip_module \
  --with-http_stub_status_module
make -j"$(nproc)"
sudo make install
```

Then you own the upgrade path. Pin the revision, build a package, test it in staging, and treat it like any other piece of software you compile yourself. Teams that already build their own PostgreSQL or HAProxy will find this unremarkable. Teams that do not will find it exhausting within two release cycles.

## Migration pitfalls: what breaks in a "drop-in" swap

**1. Dynamic modules are not portable between projects.** A `.so` compiled against nginx headers will not load in Angie, and vice versa. Angie ships its own module packages; third-party modules must be rebuilt against Angie sources. If your stack depends on a niche module — an auth connector, a custom filter — verify it builds before you migrate, not after.

**2. `nginx -t` becomes `angie -t`, and so does everything else.** Service names, config paths (`/etc/angie/`) and log locations differ. Any automation that greps nginx paths needs updating, and that includes your monitoring checks.

**3. HTTP/3 needs a UDP port, not just a config line.** `listen 443 quic reuseport` requires the UDP port to be open in your firewall and load balancer. A TLS-only security group rule will silently give you HTTP/2 fallback and you will conclude HTTP/3 does not work.

**4. Certificate reload behaviour differs.** If you rely on a cron job that copies certificates and runs `nginx -s reload`, switching to a server that reloads certificates automatically is fine — but keep the cron job until you have verified the automatic path on your filesystem layout. Silent certificate staleness is the worst failure mode in this space.

**5. Sticky sessions need a fallback plan.** Cookie-based affinity breaks when a client strips cookies, and it does not survive a backend being drained. Pair `sticky` with health checks and a defined session store, or you have moved the problem rather than solved it.

**6. Metrics endpoints must never be public.** Angie's `api` directive is a full JSON status surface. Put it behind an `allow`/`deny` block on an internal interface, as in the example above. An exposed status API leaks upstream addresses, request rates and sometimes request URIs.

**7. Test with your real configuration, not the sample.** `angie -t` catches syntax errors. It does not catch a `map` block that behaves subtly differently, or a module that silently does not load. Run a canary vhost behind the same config for a week.

## So which one should serve your traffic?

If you are running nginx today and nothing hurts, **stay on nginx**. The free version now has HTTP/3, the distro packages are mature, and "we migrated because a blog post was enthusiastic" is a bad reason to touch your edge tier.

If you have ever written a Lua block to get session affinity, run a sidecar exporter to get per-vhost metrics, or wired certbot into a reload hook, **move to Angie**. You are paying complexity for features that ship natively, and the config language is the same one your team already knows.

If your requirement is that no single company can change the roadmap of your web server, **Freenginx** is the only project of the three that answers that question — and you should go in knowing that you are now maintaining a build pipeline, not just a config file.

The one thing you should not do is run two of them on the same host "to compare." Pick one, put it behind your real traffic in staging, and measure the thing you actually care about: p99 latency at your peak request rate, with your real TLS handshakes and your real upstream timeouts.

## Related reading

If you want to compare against the other major free servers rather than the forks, our [OpenResty vs nginx vs Caddy comparison](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) covers the Lua-scriptable and automatic-HTTPS options in the same depth. For the certificate automation that Angie now builds in, the [ACME client comparison](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) explains what you are replacing. And if rate limiting is why you are looking at the edge tier at all, the [nginx vs Caddy vs Envoy rate limiting guide](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-2026/) is the practical follow-up.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "nginx vs Angie vs Freenginx in 2026: Which Fork Should Actually Serve Your Traffic?",
  "description": "nginx, Angie and Freenginx compared as production web servers in 2026 — configuration differences, built-in metrics, module compatibility and migration traps.",
  "datePublished": "2026-11-13",
  "dateModified": "2026-11-13",
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

**Is Angie a drop-in replacement for nginx?**
For configuration, essentially yes: Angie reads nginx configuration syntax and the same directive names, so a typical reverse-proxy config moves over unchanged. What does not move is compiled modules — dynamic modules built for nginx must be rebuilt for Angie, and binary paths, service names and config directories differ.

**Does Freenginx have binary packages?**
No official packages. Freenginx is distributed as source through Mercurial at `freenginx.org/hg/nginx`, and you build it yourself. Some third-party repositories package it, but they are community efforts with their own lag, so verify before you depend on one.

**Why did Freenginx fork from nginx?**
Because of a governance dispute, not a technical one. The maintainer objected to security fixes and development decisions being handled through non-public corporate channels, and started the fork in February 2024 to keep development and security work in the open. Functionally it remains close to upstream nginx.

**Can I get nginx Plus features for free with Angie?**
Some of them, notably sticky upstream sessions, an active health-check-adjacent status API and built-in metrics. Angie does not clone the Plus control plane, the Plus API or commercial support. If you specifically need vendor support with an SLA, Angie's commercial offering is separate and worth pricing before assuming parity.

**Does HTTP/3 work on all three?**
Yes, all three build with `--with-http_v3_module` and support `listen 443 quic`. The practical requirement is a UDP port open on every hop, including cloud load balancers that often default to TCP-only listeners. If HTTP/3 silently falls back to HTTP/2, check the UDP path first.

**What happens to my Lua configs if I migrate to Angie?**
Lua support comes from the `ngx_http_lua_module`, which is third-party and must be rebuilt against Angie sources — Angie's own module packages include a compatible build, but you should verify the version. If your setup depends heavily on OpenResty-specific APIs, the honest answer is that OpenResty remains the better fit.

**Which one should I use for a single small VPS?**
nginx, from your distribution's repository. It is one `apt install` away, security updates arrive automatically, and none of the fork-only features — per-vhost metrics, sticky sessions, native ACME — matter much at single-digit requests per second.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
