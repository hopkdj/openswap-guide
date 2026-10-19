---
title: "Vulnerable Lab Environments in 2026: Vulhub vs OWASP Juice Shop vs WebGoat"
date: "2026-10-18"
tags: ["security", "docker", "penetration-testing", "self-hosted", "comparison"]
draft: false
cover: "/img/screenshots/juice-shop.jpg"
---

# Vulnerable Lab Environments in 2026: Vulhub vs OWASP Juice Shop vs WebGoat

You can spin up a container that is genuinely, deliberately exploitable in under two minutes. That is either the best training tool you will use this year or the fastest way to hand an attacker a shell on your network — and the difference is entirely in how you isolate it.

Three projects dominate self-hosted practice labs, with **49,000+ GitHub stars between them**: Vulhub (real CVE reproductions), OWASP Juice Shop (a modern single application with 100+ challenges), and WebGoat (a guided lesson platform). They teach different skills, and picking the wrong one wastes weeks.

## TL;DR — Quick Verdict

**Vulhub is the only one that teaches you to exploit real CVEs.** If your goal is "understand how CVE-2017-5638 actually works, from payload to reverse shell", nothing else comes close. It is 300+ compose files, each reproducing a specific historical vulnerability.

**Juice Shop is the best single target for modern web testing.** It looks like a real single-page shop, scores you automatically, and covers broken access control, business-logic flaws, and client-side issues that CVE replays never touch.

**WebGoat is the best structured curriculum.** If you are onboarding a junior engineer or studying for a certification, its guided lessons with hints and explanations beat dropping someone into a vulnerable container and wishing them luck.

**Use all three, in this order: WebGoat for concepts, Juice Shop for application testing, Vulhub for CVE reproduction.**

## Head-to-Head Comparison

| Dimension | Vulhub | OWASP Juice Shop | WebGoat |
|---|---|---|---|
| GitHub stars | **21,365** | **14,130** | **9,416** |
| Last push | 2026-10-17 | 2026-10-17 | 2026-10-13 |
| Model | CVE reproductions | Single modern app | Guided lessons |
| Number of targets | 300+ compose stacks | 1 app, 100+ challenges | 1 app, 30+ lessons |
| Scoring / progress | None | Built-in scoreboard | Built-in lesson tracker |
| Exploit realism | **Very high (real CVEs)** | Medium (simulated flaws) | Low–medium (teaching flaws) |
| Setup per target | One compose file | One container | One container |
| Reset cost | Recreate stack | Restart container | Restart container |
| Best skill taught | CVE analysis, RCE chains | App pentesting, logic flaws | Concepts, exam prep |
| Risk if exposed | **Critical (real RCE)** | High | Medium |

That last row deserves emphasis. Vulhub containers are not "vulnerable-ish" — several of them will give an unauthenticated attacker remote code execution by design, and some spawn reverse shells to whatever connects to them.

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Studying a specific CVE from a bug bounty report | Vulhub | Exact version, exact exploit path |
| Practising a full web app assessment end to end | Juice Shop | Realistic flows, automated scoring |
| Training a new hire on OWASP Top 10 | WebGoat | Lesson structure with explanations |
| Building a CTF for a team event | Vulhub + Juice Shop | Breadth plus a polished target |
| Need a target for scanner tuning | Juice Shop | Stable, known-good baseline |
| Verifying a WAF rule against a real exploit | Vulhub | Real payloads, real CVE traffic |
| Limited disk and RAM | WebGoat | Single lightweight container |

## Vulhub — The CVE Library

Vulhub is not one application; it is a directory tree of reproducible vulnerabilities. Each folder contains a `docker-compose.yml` pinned to the vulnerable version plus a README explaining the flaw and the exploit.

The workflow is deliberately boring, which is a compliment:

```bash
git clone https://github.com/vulhub/vulhub.git
cd vulhub/struts2/s2-001
docker compose up -d
docker compose ps
```

You now have the vulnerable Struts2 instance running. Tear it down with `docker compose down -v` when you are done, and move to the next CVE. Because every stack is self-contained, there is no cross-contamination between labs.

**What it does well:** authenticity. You are attacking the actual vulnerable software version, not a simulation. That matters more than it sounds — real exploits fail for messy reasons (a missing dependency, a wrong header, an encoding quirk), and those failure modes are exactly what you need to learn. Vulhub also documents the underlying cause in each README, so it doubles as a reading list.

**Where it hurts:** there is no curriculum and no scoring. You need to know what you want to practise. Some stacks require extra steps (a database init, a specific hostname, a `/etc/hosts` entry), and a few are architecture-specific — if you run on ARM, check the image manifest before assuming a stack will start.

**The safety problem is real.** These containers run the vulnerable service with default credentials, no TLS, and often no authentication at all. One of them is a Java deserialization endpoint that will happily execute whatever you send. Bind to `127.0.0.1`, never `0.0.0.0`.

## OWASP Juice Shop — A Realistic Target

Juice Shop is a single-page e-commerce application, deliberately full of flaws, wrapped in a scoring engine. The official container is one command:

```bash
docker run --rm -p 127.0.0.1:3000:3000 bkimminich/juice-shop
```

Then open `http://localhost:3000`. The scoreboard lives at `/#/score-board` and tracks which challenges you have solved, including a "find the scoreboard" challenge that is itself part of the game.

**What it does well:** it feels like software. There is a product catalogue, a basket, a login, a feedback form, an admin section, and a REST API backing all of it. That means you practise the parts of a real assessment that CVE replays cannot teach: enumerating an API, chaining an IDOR into privilege escalation, abusing a business-logic flaw in the checkout flow, and reading client-side code for leaked secrets.

The challenge set spans injection, broken authentication, sensitive data exposure, XXE, broken access control, security misconfiguration, XSS, insecure deserialization, and vulnerable components. Because scoring is automatic, you get a progress signal without writing your own harness.

**Where it hurts:** it is one application, so the variety is bounded. Once you have solved the challenges, there is nothing left to discover. It also trains you on flaws that are intentionally findable — real applications hide them in far more noise.

## WebGoat — The Guided Curriculum

WebGoat is maintained by OWASP and structured as lessons rather than a sandbox. The documented container invocation:

```bash
docker run -it -p 127.0.0.1:8080:8080 -p 127.0.0.1:9090:9090 webgoat/webgoat
```

Open `http://localhost:8080/WebGoat`. Port 9090 serves the companion "WebWolf" application, which gives you an attacker-controlled mail server and file host — essential for lessons involving out-of-band interaction.

**What it does well:** explanation before exploitation. Each lesson states the concept, gives you a task, and provides hints. For someone who has never exploited SQL injection, that scaffolding is the difference between learning and quitting. It is also the closest of the three to a certification study path.

**Where it hurts:** the lessons are intentionally simplified, so the techniques do not transfer one-to-one to messy production targets. And the interface is dated compared with Juice Shop — you are there for the content, not the experience.

## Pitfalls That Will Cost You More Than an Evening

**1. Never expose a lab to the internet. Not once.** A Vulhub stack with an unauthenticated RCE is a compromised host waiting for the first scanner. Even "just for ten minutes while I test from my laptop" is how lab hosts get recruited into botnets. Bind every port to `127.0.0.1` and tunnel with SSH if you need remote access.

**2. Run labs on a disposable host or a dedicated VM.** Several vulnerabilities allow file write or command execution inside the container, and container escapes are not theoretical when the container runs privileged. If the lab shares a host with your production services, you have removed the isolation that made the lab safe.

**3. Default credentials are everywhere and that is the point.** Do not "harden" a lab — you will break the challenges. Equally, do not reuse any credential from the lab on real systems, because you will inevitably type them into the wrong terminal.

**4. `docker compose down` is not enough for Vulhub.** Use `down -v` to remove volumes, and prune old images periodically. A few dozen CVE stacks will consume tens of gigabytes without you noticing.

**5. Apple Silicon and ARM hosts will break some stacks.** Check the image architecture before you debug a container that exits immediately. Some older Java and PHP images are amd64-only and need emulation, which is slow and sometimes subtly wrong.

**6. Juice Shop's scoreboard can be reset — and so can your progress.** If you are tracking a learner's progress, extract the results before you recreate the container, because the state lives inside it.

**7. Document your exploit chain, not just the flag.** The value of a lab is the write-up. A solved challenge with no notes is a forgotten skill in three weeks.

## FAQ

### Which lab should a complete beginner start with?

WebGoat. Its lessons explain the vulnerability class before asking you to exploit it, and it provides hints when you stall. Juice Shop is the natural second step, and Vulhub should come after you are comfortable with HTTP tooling and reading source code.

### Is it legal to run these?

Running deliberately vulnerable software on your own machine is legal and is exactly what these projects are published for. What is not legal is attacking systems you do not own or have written authorisation to test. Keep labs on localhost, and never point a scanner at an address you have not been authorised to touch.

### Can I use Vulhub to validate my WAF or scanner?

Yes — that is one of its best uses. Because each stack reproduces a real CVE with a documented payload, you get a ground-truth signal for detection rules. Pair it with a reverse proxy in front of the lab container and check whether your rules fire on the real exploit traffic rather than a synthetic string.

### How much RAM and disk do I need?

Juice Shop and WebGoat run comfortably in 1–2 GB. Vulhub varies wildly: a single PHP stack needs almost nothing, while the Java and Elasticsearch-based stacks want 2–4 GB each. Run one stack at a time on a small host, and keep at least 40 GB free if you plan to pull many images.

### Do these replace hands-on certification labs?

No. They are excellent for technique and concepts, but the structured exam labs include scoring nuance, time pressure, and reporting requirements. Use these to build fluency, then practise reporting separately — writing a clear finding is a different skill from exploiting one.

### Can I keep the labs running permanently?

You can, but you should not. A permanently running vulnerable service is a permanent liability, especially if it sits on a network with other machines. Start labs on demand, tear them down after, and treat the compose file as the artifact worth keeping.

## Related Reading

Once you have found a weakness, the next question is detection: our [server security auditing comparison](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide-2026/) covers Lynis, OpenSCAP, and Goss, and the [SSH auditing guide](../2026-06-01-self-hosted-ssh-security-auditing-ssh-audit-sshscan-lynis-guide/) addresses the most commonly misconfigured service on any lab host. If you are testing whether a WAF blocks what you just exploited, the [ModSecurity vs Coraza vs BunkerWeb comparison](../2026-05-06-self-hosted-web-application-firewalls-modsecurity-coraza-bunkerweb-guide/) will save you a week of trial and error.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Vulnerable Lab Environments in 2026: Vulhub vs OWASP Juice Shop vs WebGoat",
  "description": "Comparison of three self-hosted security practice labs: Vulhub for real CVE reproduction, OWASP Juice Shop for modern web application testing, and WebGoat for guided lessons, including Docker commands and isolation pitfalls.",
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
