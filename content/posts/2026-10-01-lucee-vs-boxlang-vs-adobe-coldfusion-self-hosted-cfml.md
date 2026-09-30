---
title: "Lucee vs BoxLang vs Adobe ColdFusion in 2026: Self-Host CFML Without the Licensing Bill"
date: "2026-10-01"
tags: ["cfml", "coldfusion", "lucee", "jvm", "self-hosted"]
draft: false
cover: "/img/screenshots/lucee-cfml-engine-logo.jpg"
---

ColdFusion shops have the same conversation every renewal cycle: the application works, the team knows it, and the licensing invoice does not care. Adobe ColdFusion is priced per instance with tiers that punish exactly the deployment models people actually want — containers, autoscaling, per-tenant isolation. Meanwhile the CFML ecosystem quietly built two credible open alternatives on the JVM: **Lucee**, a straight CFML engine, and **BoxLang**, a new dynamic JVM language that keeps CFML compatibility as a design goal.

This is the practical comparison for teams asking whether they can move off paid licensing without rewriting a decade of `.cfm` templates. Short answer: usually yes, and the migration is smaller than the fear.

![Lucee CFML engine logo](/img/screenshots/lucee-cfml-engine-logo.jpg "Lucee is an open source CFML engine for the JVM")

## Quick Verdict

**Choose Lucee** if you have an existing CFML/`.cfm` codebase and want the least disruptive drop-in engine — it is a Java CFML runtime, container-friendly, and LGPL-licensed. **Choose BoxLang** if you are starting fresh or want a modern dynamic JVM language with multi-runtime deployment (CLI, mini-server, servlet, lambdas) rather than a pure CFML engine. **Stay with Adobe ColdFusion** only if you depend on a specific Adobe-only feature set, vendor support contracts, or an enterprise procurement process that cannot approve an open source runtime. In one line: **Lucee for existing apps, BoxLang for new ones, Adobe for support contracts you actually use.**

## Head-to-Head Comparison

Live GitHub data pulled on 2026-10-01:

| Dimension | Lucee | BoxLang | Adobe ColdFusion |
|---|---|---|---|
| Model | Open source CFML engine | Modern dynamic JVM language | Commercial CFML platform |
| GitHub stars | 920 | 94 | Closed source (no public repo) |
| Latest release | 7.0.4.34 (2026-06-04) | Active development (repo pushed 2026-09-30) | Versioned commercial releases |
| License / cost | LGPL-2.1, free | Apache-2.0 core, free; commercial tiers exist | Per-instance commercial licensing |
| Runtime | JVM (Tomcat/Jetty, or embedded) | JVM: CLI, mini-server, servlet, lambda, WASM | JVM (own server) |
| CFML compatibility | Yes — primary design goal | Backward-compatible with CFML by design | Native |
| Official container images | Yes (`lucee/lucee`, nginx and tomcat variants) | Yes (`ortussolutions/boxlang`, mini-server variants) | Yes (`ortussolutions/commandbox` carries Adobe images) |
| Deployment flexibility | High | Very high (multiple runtimes from one language) | Constrained by licensing tiers |
| Tooling | CommandBox, cfconfig, classic IDEs | CommandBox, own CLI, debugger and IDE tooling | Adobe tooling |
| Best for | Existing CFML apps, drop-in replacement | New JVM services, gradual CFML modernisation | Shops with signed support requirements |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| 200k lines of working `.cfm` templates | **Lucee** | Drop-in engine, no rewrite, no per-instance licence |
| Deploying to containers or scaling horizontally | **Lucee** | Free per instance — containers stop costing licence money |
| Starting a new service and you like CFML ergonomics | **BoxLang** | Modern language features plus Java interoperability |
| You want one language for CLI tools, web apps and lambdas | **BoxLang** | Multi-runtime design is its core premise |
| Procurement requires a vendor support contract | **Adobe ColdFusion** | That is what the licence actually buys |
| You need to run both CFML and new services side by side | **Lucee + BoxLang** | Both run on the JVM and share CommandBox tooling |
| You need a framework layer over the engine | **CFWheels** on top of Lucee/BoxLang | Convention-based HMVC framework, engine agnostic |

## Lucee — The Drop-In CFML Engine

Lucee is the conservative choice, and for a legacy CFML codebase that is a compliment. It is a CFML engine written in Java, licensed **LGPL-2.1**, at **920 stars**, with release **7.0.4.34** published on **2026-06-04**. Because it implements CFML rather than reimagining it, the migration story for an existing application is mostly datasource and scheduled-task configuration — not code.

Its real advantage over Adobe is deployment economics. Lucee publishes official images under `lucee/lucee`, with tag families for plain servlet containers and nginx-fronted variants. I verified `lucee/lucee:7.0-nginx` and `lucee/lucee:7.0.4.34-nginx` resolve on Docker Hub, so you can pin the exact engine version your app was tested against:

```yaml
services:
  lucee:
    image: lucee/lucee:7.0-nginx
    ports:
      - "8054:80"      # web
      - "8854:8888"    # Lucee admin
    volumes:
      - ./www:/var/www
    environment:
      - LUCEE_ADMIN_PASSWORD=${LUCEE_ADMIN_PASSWORD}
```

The project's own dockerfiles repository ships a compose file in exactly this shape — service image, an admin port alongside the web port, and a bind-mounted `www` directory — which is a good starting point rather than something to hand-roll. Mount your webroot and keep the admin port off the public internet behind your reverse proxy; the admin UI is where datasources, mail servers, scheduled tasks and extensions are configured, and it is a genuine attack surface if exposed.

The catch with Lucee is extensions. Anything your application uses beyond the core — datasource drivers, caching providers, PDF tooling — has to exist as a Lucee extension or a plain Java library. Audit those before you migrate, because that audit, not the CFML syntax, is where migration projects lose weeks.

## BoxLang — A Modern Dynamic JVM Language

BoxLang is the more interesting bet. It is not "another CFML engine" — it is a **dynamic programming language for the JVM** that deliberately keeps CFML compatibility while borrowing ideas from Java, Python, Ruby, Go and PHP. It is **Apache-2.0** licensed at the core with commercial tiers for extra tooling and support, developed in the open at **94 stars** with the repository actively pushed on **2026-09-30**.

The distinguishing feature is runtime targets. The same language runs as a native OS CLI, a mini-server, inside a servlet container, as cloud function handlers, and it compiles down to Java bytecode. For a team that wants one language for a web app, a scheduled job and a CLI utility, that is a real architectural simplification rather than a marketing bullet.

![BoxLang CLI screenshot](/img/screenshots/boxlang-cli.jpg "BoxLang CLI running on the JVM")

Deployment is container-first like Lucee, with official images published under `ortussolutions/boxlang` including mini-server and nginx-fronted variants:

```yaml
services:
  boxlang:
    image: ortussolutions/boxlang:miniserver-nginx-snapshot
    ports:
      - "8080:8080"
    volumes:
      - ./app:/app
```

Because CFML compatibility is a stated design goal, the migration path is gradual rather than binary: you can run existing CFML logic on BoxLang and write new code in the modern syntax in the same deployment. That is the strongest argument for BoxLang over Lucee for greenfield work — you are not choosing between your existing code and a better language, you can have both while you migrate at your own pace.

Be honest about the maturity trade-off. Lucee has a much longer track record in production and a far larger body of community answers. BoxLang is where the energy is, but you are adopting something newer, and "newer" means you will occasionally be the person who finds the bug.

## CommandBox and Wheels — The Migration Tooling

Neither engine choice changes the tooling layer. **CommandBox** (Apache-2.0, **150 stars**, release **v6.3.5** on **2026-09-12**) is the CFML CLI, package manager, embedded server and REPL. It is the tool that turns "spin up a CFML server" from a day of Tomcat configuration into two commands:

```bash
box install
box server start
```

CommandBox also publishes official images (`ortussolutions/commandbox`) with `jdk21-alpine` and `adobe2025` tag families, which is how you produce a container image for a legacy Adobe application before you migrate it — useful for a staged rollout where the engine changes in a separate pull request from the deployment model.

On top of that sits **CFWheels** (Apache-2.0, **203 stars**, release **v4.1.1** on **2026-09-28**), a convention-based HMVC framework that is deliberately engine-agnostic. Its documentation lists Adobe ColdFusion 2018–2025, Lucee 5.x/6.x/7.x and BoxLang 1.x as supported engines, with SQLite, SQL Server, PostgreSQL, MySQL, H2 and Oracle for persistence. Its quickstart is refreshingly short, using a dedicated CLI that ships with Lucee and needs only Java 21:

```bash
brew tap wheels-dev/wheels
brew install wheels
wheels new myapp
```

Supporting three engines in one framework is the clearest signal that the CFML ecosystem has genuinely diversified. If Wheels can target Adobe, Lucee and BoxLang from the same codebase, so can most application code.

## Pitfalls and Migration Notes

**Audit Adobe-only features before you plan anything.** Engine-level CFML is portable; vendor-specific integrations, certain tag implementations and specific admin features are not. Produce a list first, then estimate.

**Licensing models punish the deployment shape you want.** Per-instance commercial licensing is the whole reason container migration becomes attractive: the same architecture that is expensive on a commercial engine is free on Lucee or BoxLang.

**Extension availability is the real migration risk.** Check that every datasource driver and caching provider your app relies on has an equivalent extension before you commit to a cutover weekend.

**Pin your engine version in the image tag.** Both Lucee and BoxLang publish many tag variants (`-nginx`, tomcat/JDK combinations, snapshot channels). Pin exactly what you tested; a floating tag will silently change your JDK underneath you.

**Keep the admin interface off the public internet.** Lucee's admin and any engine management console should sit behind your reverse proxy with authentication, not on a published port.

**Test scheduled tasks and mail configuration explicitly.** These are configured per engine, are rarely covered by unit tests, and are a classic post-migration surprise.

If you are weighing JVM application servers more broadly, our [Java web framework comparison](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/) covers the modern stack, the [application server comparison](../2026-04-27-tomcat-vs-wildfly-vs-gunicorn-self-hosted-application-servers-guide-2026/) covers the servlet tier your CFML engine runs inside, and the [embedded HTTP server comparison](../2026-07-04-java-embedded-http-servers-jetty-netty-undertow-tomcat/) explains the containers Lucee and BoxLang embed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lucee vs BoxLang vs Adobe ColdFusion in 2026: Self-Host CFML Without the Licensing Bill",
  "description": "Comparison of Lucee 7, BoxLang and Adobe ColdFusion for self-hosting CFML on the JVM: licenses, Docker images, migration paths and the CommandBox and Wheels tooling layer.",
  "datePublished": "2026-10-01",
  "dateModified": "2026-10-01",
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

**Can I run existing ColdFusion applications on Lucee without code changes?**
In most cases yes. Lucee implements CFML as its primary purpose, so typical applications migrate with datasource, mail and scheduled-task configuration rather than application code. Applications relying on Adobe-specific features or third-party integrations need a compatibility audit first.

**Is BoxLang a CFML engine or a different language?**
Both. BoxLang is a modern dynamic JVM language that intentionally maintains backward compatibility with CFML, so existing CFML code can run alongside new code written in its own syntax. That makes migration incremental instead of a rewrite.

**What actually replaces Adobe ColdFusion's support contract?**
Commercial support is what an Adobe licence buys, so the replacement is usually a mix of community support and, where needed, commercial support from vendors in the CFML ecosystem — for example BoxLang offers commercially supported tiers. If your procurement genuinely requires a signed support agreement, that requirement is the thing to evaluate, not the technology.

**Do these engines run in Docker and Kubernetes?**
Yes. Lucee and BoxLang both publish official container images, including nginx-fronted and mini-server variants, and both run on the JVM, so standard JVM container and Kubernetes patterns apply.

**What is CommandBox and do I need it?**
CommandBox is a CFML CLI, package manager, embedded server and REPL, licensed under Apache-2.0. You do not strictly need it, but it makes local development, dependency installation and producing container images dramatically simpler, and it works with Adobe, Lucee and BoxLang.

**Which framework should I put on top of the engine?**
If you want convention-based structure, CFWheels is engine-agnostic and documents support for Adobe ColdFusion, Lucee and BoxLang. If you prefer a modern JVM language with its own framework conventions, BoxLang's own framework ecosystem is the alternative.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
