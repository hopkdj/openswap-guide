---
title: "Ada Web Frameworks in 2026: Ada Web Server vs AWA vs Gnoga — The Stack Nobody Talks About"
date: "2026-09-15"
tags: ["ada", "web-frameworks", "programming-languages", "self-hosted", "comparison"]
draft: false
cover: "/img/screenshots/ada-awa-features.png"
---

Ada runs fly-by-wire systems, rail signalling, and satellite ground stations — and it also has a web stack. Not a hypothetical one: three distinct projects, all still reachable in 2026, all capable of serving production HTTP. The catch is that the ecosystem is so small that **public repositories have between 18 and 162 stars**. That number tells you something important: you will not find a Stack Overflow answer for your Ada web problem. What you will find is code with no runtime, no garbage collector surprises under load, and a compiler that refuses to let you ship the mistake in the first place.

Here is an honest, live-data comparison of the three realistic options.

## TL;DR — Quick Verdict

**Use Ada Web Server (AWS) if you want to embed an HTTP server inside an Ada application.** It is the foundation everything else builds on, it has the most recent release of the three (**v25.2.0**, November 2025) and active commits through **September 2026**. **Use AWA if you want a full web application** — login, permissions, blog, wiki, and question-and-answer modules already written, with an official Docker image. **Use Gnoga if you want to build a browser-targeted GUI in Ada** rather than a classic request/response web service. Do not choose any of them expecting a hiring pool; choose them when certification, determinism, and long-term binary stability matter more than ecosystem size.

## Ada Web Stacks Compared

| Dimension | **Ada Web Server (AWS)** | **Ada Web Application (AWA)** | **Gnoga** |
|---|---|---|---|
| GitHub stars | 162 | 113 | 18 (mirror of SourceForge upstream) |
| Last commit | 2026-09-11 | 2026-09-15 | 2026-08-27 |
| Latest release | v25.2.0 (Nov 2025) | 2.5.0 (Oct 2023), 2.6.0 in development | rolling (SNOGA/Gnoga 2.2 line) |
| License | GPL-3.0 **with runtime exception** | Apache-2.0 (Ada LZMA under MIT) | GPL with runtime exception |
| Architecture | Embeddable HTTP server library | Full-stack framework on AWS | GUI framework with a browser target |
| Views | Your own callbacks | Ada Server Faces (XHTML + EL) | Widget tree rendered into the browser |
| Persistence | None (bring your own) | ADO: PostgreSQL, MySQL/MariaDB, SQLite | None |
| Async/events | Thread pool + server push | Same as AWS | WebSocket event loop |
| Official container | No (compile your own) | `ciceron/ada-awa` on Docker Hub | No |
| Best for | APIs, embedded HTTP services | Business apps, CMS-style portals | Instrument panels, browser GUIs |

Read the table as a stack diagram rather than a competition. AWA depends on AWS. Gnoga takes the opposite approach entirely: instead of serving pages, it runs your Ada program and drives a browser front-end over a WebSocket connection. Comparing them is only fair once you decide which model you actually want.

## Decision Matrix: One Row, One Answer

| Your Use Case | Recommended Tool | Why |
|---|---|---|
| REST API inside an existing Ada binary | **AWS** | Zero dependencies beyond the AWS library itself |
| Add a status page to a control system | **AWS** | Hotplug modules, administrative status page built in |
| Multi-user portal with logins and permissions | **AWA** | The auth, permission, blog, wiki and Q&A modules already exist |
| SOAP/WSDL integration with an old enterprise system | **AWS** | Ships `ada2wsdl` and `wsdl2aws` code generators |
| Browser-based operator interface | **Gnoga** | Event-driven widget tree, not request/response |
| You need to try something in 15 minutes | **AWA Docker image** | `docker pull ciceron/ada-awa` skips the toolchain entirely |

## Ada Web Server — The Foundation

AWS describes itself as "a small yet powerful HTTP component to embed in any applications. It means that you can communicate with your application using a standard Web browser and this without the need for a Web Server." That last clause is the key architectural difference from a Python or PHP deployment: your Ada program *is* the server. There is no upstream process, no FastCGI bridge, and no interpreter startup cost.

![Ada Web Server project logo](/img/screenshots/ada-aws-logo.png "Ada Web Server (AWS) project logo")

The canonical example from the official AWS documentation is short enough to read in one pass:

```ada
with AWS.Response;
with AWS.Server;
with AWS.Status;

procedure Hello_World is

  WS : AWS.Server.HTTP;

  function HW_CB (Request : in AWS.Status.Data)
    return AWS.Response.Data
  is
     URI : constant String := AWS.Status.URI (Request);
  begin
     if URI = "/hello" then
        return AWS.Response.Build ("text/html", "<p>Hello world !");
     else
        return AWS.Response.Build ("text/html", "<p>Hum...");
     end if;
  end HW_CB;

begin
   AWS.Server.Start
     (WS, "Hello World", Callback => HW_CB'Unrestricted_Access);
   delay 30.0;
end Hello_World;
```

Build and install it from source with the documented makefile targets. The `SOCKET` variable selects the TLS backend, and AWS requires you to rerun `setup` after editing `makefile.conf`:

```bash
# Build AWS with OpenSSL support, then install to /opt
git clone --recursive -b 20.2 https://github.com/AdaCore/aws
cd aws
make SOCKET=openssl setup
make build
make prefix=/opt install
```

Two details worth knowing before you commit. First, AWS is licensed **GPL-3.0 with a runtime exception** — the repository contains a `COPYING.RUNTIME` file precisely so you can distribute proprietary software linked against it. Second, AWS supports **server push, HTTPS/SSL, hotplug modules, SOAP/WSDL, client HTTP, and an administrative status page** out of the box, which is an unusual amount of protocol surface for a library with this footprint.

## AWA — The Full-Stack Option

AWA (Ada Web Application) is a framework, not a server: it wires AWS together with Ada Server Faces, Ada Servlet, ADO (the database layer), Ada Security, Ada Wiki, and a set of ready-made modules — **login and authentication, users, permissions, comments, tags, votes, documents, images, a blog, a question-and-answer module, and a wiki**. Version 2.5.0 shipped in October 2023; version 2.6.0 is under active development and has been moving through 2026 with features like sitemap generation and an SEO module.

![AWA module architecture overview from the official documentation](/img/screenshots/ada-awa-architecture.png "Ada Web Application module architecture from the AWA documentation")

The build is autotools-style, and the README is explicit about the database clients you need present:

```bash
# Ubuntu development host (from the AWA README)
sudo apt-get install unzip liblzma-dev libcurl4-openssl-dev libpq-dev

git clone --recursive https://github.com/stcarrez/ada-awa.git
cd ada-awa
./configure --prefix=/usr/local
make
make install
```

Note the `--recursive`: AWA uses git submodules for its sibling projects, so a plain clone gives you a tree that will not build. Once installed, project scaffolding is a single command that generates a compilable application with the modules you asked for:

```bash
dynamo create-project -l apache atlas your-email@domain.com
cd atlas
./configure
make generate build
./bin/atlas-server setup
```

The generated server binary takes subcommands (database setup, schema migration, user creation) rather than requiring you to write migration scripts by hand — a small thing that matters a lot in operations.

If you want to evaluate it without touching a compiler, use the official image:

```bash
docker pull ciceron/ada-awa
```

### Self-Hosting an AWA Application

AWA applications are ordinary processes serving HTTP on a local port. Put a reverse proxy in front, and run it under systemd with the binary the generator produced:

```nginx
server {
    listen 443 ssl http2;
    server_name apps.example.com;

    ssl_certificate     /etc/letsencrypt/live/apps.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/apps.example.com/privkey.pem;

    client_max_body_size 25m;   # match AWA's --max-upload-size setting

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

```ini
[Unit]
Description=AWA application server
After=network-online.target postgresql.service

[Service]
Type=simple
User=awa
WorkingDirectory=/opt/atlas
ExecStart=/opt/atlas/bin/atlas-server start
Restart=always
RestartSec=5
Environment=APP_ENV=production
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

PostgreSQL, MySQL/MariaDB, and SQLite are all supported through ADO, and the configure step fails deliberately if it cannot find at least one database driver — which is a helpful blunt-instrument check during deployment.

## Gnoga — A Different Model Entirely

Gnoga stands for the **GNU Omnificent GUI for Ada**, and it is not a web framework in the request/response sense. You write an Ada GUI application using a widget tree, and Gnoga runs your program while serving a browser front-end over WebSockets — the official README tells you to start the app and then "open a web browser with URL like `http://127.0.0.1:8080`". HTTP and WebSocket transport come from a bundled copy of Dmitry A. Kazakov's Simple Components library.

Installation follows the Alire package manager, which is now the recommended entry point for Ada libraries:

```bash
# In your own Alire project
alr with gnoga
# then, in your GPR project file:
# with "lib_gnoga.gpr";
```

The upstream source repository lives on SourceForge (`git clone git://git.code.sf.net/p/gnoga/code gnoga-code`), with a GitHub mirror carrying only a small fraction of the community reach. The build is makefile-driven, and the repository ships demos — including a Snake game and a tutorial set — that you run from `bin/` to verify the browser target works before writing a line of your own code.

Choose Gnoga when the problem is "operators need a control panel driven directly by this Ada process," not when the problem is "serve a public website." For that second problem, AWS plus your own HTML is simpler and has a far larger user base.

## Production Pitfalls in the Ada Web Ecosystem

**1. Toolchain pinning is mandatory, not optional.** Ada's build tooling expects a specific GNAT version, and AWA's own README warns that the AWS shipped with GNAT 2021 will not work with OAuth because it lacks SSL support. Always install the compiler and the libraries together — through Alire where possible — and record the exact versions in your build image.

**2. `--recursive` or nothing.** AWA and AWS (when built with submodules) require recursive clones. A shallow, non-recursive clone produces confusing "file not found" errors from `gprbuild` that look like source corruption but are missing submodules.

**3. The GPL runtime exception is your compliance anchor.** AWS and Gnoga are distributed under GPL with a runtime exception (see `COPYING.RUNTIME` in the AWS repository). Read that file before your legal team reads the GPL header, and keep the exception text with your licence inventory.

**4. `UPLOAD_DIR` and body-size limits are separate settings.** Large file uploads fail in two places: the reverse proxy (`client_max_body_size` in nginx) and the server itself (`--max-upload-size` / `--max-form-size`). Raising only one produces a request that dies halfway through with no useful error on either side.

**5. There is no ORM outside AWA/ADO.** If you use bare AWS, you write your own persistence. That is a feature in a control system and a liability in a CRUD application — which is exactly why AWA exists.

**6. Expect to read source, not search engines.** With repositories in the tens-to-hundreds of stars, your debugging loop will be `grep` over the library sources and the `regtests` directory. The official test suites are the documentation of record.

**7. Cross-compilation is a first-class use case, not an afterthought.** AWS supports cross targets explicitly (for example `make TARGET=powerpc-wrs-vxworks setup build`), so the same HTTP layer you test on x86 can be built for the embedded board. Pin your target triple in CI and treat the host build as a separate artifact.

## Related Reading

If you are exploring small, compiled-language ecosystems, our [D web framework comparison](../2026-09-15-d-web-frameworks-vibe-d-hunt-diamond-comparison/) covers the same bus-factor tradeoff in a language with a much friendlier package manager, and the [Haskell web framework comparison](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) shows how a formally verified language builds its web layer with a type-driven API. For the underlying language-selection question, the [Zig vs Rust vs Go systems programming guide](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) puts the compiled-runtime argument in perspective.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ada Web Frameworks in 2026: Ada Web Server vs AWA vs Gnoga — The Stack Nobody Talks About",
  "description": "Live-data comparison of the three production-ready Ada web frameworks: Ada Web Server (AWS), Ada Web Application (AWA) and Gnoga, including official build commands, a documented hello-world callback, docker and systemd deployment configurations, licensing notes and a use-case decision matrix.",
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

## FAQ

**Is Ada a realistic choice for a web application in 2026?**
It is realistic for a specific class of application: systems where certification, deterministic behaviour, or a long support horizon matter more than developer supply. AWS has releases through 2025 with commits into 2026, and AWA's 2.6.0 line is under active development. If your team already knows Ada — common in aerospace, rail, and medical device organisations — adding a browser interface with AWS is cheaper than introducing a second language and its runtime.

**What is the difference between Ada Web Server and Ada Web Application?**
AWS is an embeddable HTTP server library: you write callbacks, and it handles the protocol. AWA is a full application framework built on top of AWS plus Ada Server Faces, ADO, Ada Security, and a wiki module. Choose AWS when you are adding HTTP to an existing program; choose AWA when you are building a multi-user application with login, permissions, and content modules.

**Do I need to install a compiler to try AWA?**
No. The project publishes an official container as `ciceron/ada-awa` on Docker Hub, which is the fastest way to see the generated application UI. For development you will need GNAT plus the database client libraries (`libpq-dev` for PostgreSQL, `libmariadb-dev` for MariaDB, `libsqlite3-dev` for SQLite) — the configure script intentionally fails if no database driver is found.

**How do I use AWS in a commercial closed-source product?**
AWS is GPL-3.0 with a runtime exception, and the repository ships the exception text in `COPYING.RUNTIME`. That exception exists specifically so proprietary applications can link against AWS. Include the file in your licence inventory and confirm the version you are shipping carries the same exception, since the exception is a per-release artefact.

**Why does Gnoga serve a browser interface instead of HTML pages?**
Because it is a GUI framework, not a web framework. Your Ada program holds the widget tree and communicates with the browser over a WebSocket connection, which is why the README instructs you to open `http://127.0.0.1:8080` after starting a demo binary. That model suits operator panels and instrument dashboards driven directly by the Ada process, and it is a poor fit for public websites where search engines and HTTP caching matter.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
