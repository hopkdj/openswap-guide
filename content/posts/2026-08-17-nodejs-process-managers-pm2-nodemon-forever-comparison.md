---
title: "Node.js Process Managers in 2026: pm2 vs nodemon vs forever — Which Do You Need?"
date: "2026-08-17"
tags: ["nodejs", "process-manager", "pm2", "nodemon", "forever", "devops", "developer-tools", "backend"]
draft: false
cover: "/img/screenshots/pm2-cover.jpg"
---

"Process manager" means two completely different things to a Node.js developer, and the confusion costs people real outages. In development it means *restart my server when I save a file* — that is nodemon's job. In production it means *keep my app alive, restart it when it crashes, and load-balance across my CPUs* — that is what pm2 does with **43,269 GitHub stars**. And then there is forever, the tool that did the production job before pm2 existed, now parked at 13,830 stars with its last commit in May 2023.

Most teams use the wrong tool for the wrong phase at least once. This guide compares the three tools you will actually encounter — pm2, nodemon, and forever — with real code from the official repositories and live repository data as of August 2026, so you can wire up a workflow that does not bite you at 2 a.m.

## TL;DR: Quick Verdict

**Use pm2 for production** — it is the only one of the three that daemonizes processes, survives SSH disconnects, restarts on crash, and can cluster across cores with a built-in load balancer. **Use nodemon for development only** — it watches your files and restarts on change, and it is not a process supervisor. **Do not start new projects with forever** — it is in maintenance mode (no commits since 2023) and pm2 is a strict superset of its features. The standard setup: nodemon in `devDependencies` for local work, pm2 with an `ecosystem.config.js` file in production, and pm2's cluster mode if you run on a multi-core box.

## Quick Comparison: Feature by Feature

| Feature | pm2 | nodemon | forever |
|---|---|---|---|
| GitHub stars (2026-08) | 43,269 | 26,681 | 13,830 |
| Last push (2026-08) | 2026-07-02 | 2026-08-03 | 2023-05-21 |
| Primary role | Production process manager | Dev auto-restart watcher | Legacy production runner |
| Daemonizes (survives logout) | Yes | No | Yes |
| Auto-restart on crash | Yes | Yes (for watched file) | Yes |
| Cluster / load balancing | Yes (`-i max`) | No | No |
| File watching | Yes (watch mode) | Yes (core feature) | No |
| Log management | Built-in + rotation | Streams to stdout | Log files + `forever logs` |
| Startup on boot | Yes (`pm2 startup`) | No | Via init scripts |
| Graceful shutdown / reload | Yes (`pm2 reload`) | No | Limited |
| Active development (2026) | Active | Active | Maintenance mode |

The starkest row in that table is the last one. pm2 and nodemon are both actively maintained — pushed within the last six weeks — while forever has been untouched for more than three years. Whatever forever once offered, pm2 now provides a superset of it with an active maintainer.

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Local development with hot reload | **nodemon** | Watch + restart on save is its entire job; instant setup |
| Production server on a VPS | **pm2** | Daemon mode, crash restarts, `pm2 save` + `pm2 startup` |
| Multi-core production box | **pm2 cluster mode** | `-i max` forks one process per core with built-in LB |
| Dockerized Node app | **pm2-runtime** | Foreground mode designed for containers, PID 1 safe |
| Legacy app still on forever | **pm2 (migrate)** | Same CLI shape, active maintenance, log + startup tooling |
| CI pipeline needing a long-running process | **pm2** | Scriptable `pm2 start`/`pm2 kill` lifecycle in CI |

## pm2: The Production Process Manager

pm2 calls itself a "Node.js/Bun Production Process Manager with a built-in Load Balancer," and the description is accurate. Install it globally, start your app, and pm2 takes over: it daemonizes the process so it survives your SSH session ending, restarts it when it crashes, and keeps logs under its own management.

```bash
npm install pm2 -g
pm2 start app.js
pm2 list          # status, pid, restarts, uptime
pm2 logs app      # tail the app's logs
pm2 monit         # live CPU / memory dashboard
pm2 restart app   # or: pm2 restart all
```

The moment that changes operations is cluster mode. From the official README: *"Cluster mode starts multiple Node.js processes and load-balances HTTP/TCP/UDP queries between them. This significantly increases throughput on multi-core machines and improves reliability (faster socket re-balancing in case of unhandled errors)."* One flag is all it takes:

```bash
pm2 start app.js -i max
```

`-i max` spawns one worker per CPU core and pm2's built-in load balancer distributes connections between them. If a worker dies, it is respawned automatically while the others keep serving — a genuine availability upgrade with zero code changes.

For anything beyond a toy deployment, put the config in a file so the whole team runs the same setup. An `ecosystem.config.js` at the repo root becomes the single source of truth:

```js
module.exports = {
  apps: [{
    name: 'api',
    script: './src/server.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: { NODE_ENV: 'production', PORT: 3000 },
    max_memory_restart: '512M',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
  }],
};
```

Then `pm2 start ecosystem.config.js`, and the two commands that make restarts survive reboots:

```bash
pm2 save        # snapshot the current process list
pm2 startup     # generate a systemd unit to restore it on boot
```

pm2 also now supports Bun as a first-class runtime — `bun install pm2 -g` works, and on Bun-only machines you symlink `node` to `bun` so pm2's shebang resolves. For the logging side of production Node, pm2 pairs well with structured loggers — see our [Node.js logging libraries comparison](../2026-08-10-nodejs-logging-libraries-winston-pino-bunyan/) for how pino and winston interact with pm2's log capture.

## nodemon: The Development Watchdog

nodemon has one job: watch your source files and restart the process when they change. It is a development tool — the README calls it "a tool that helps develop node.js based applications by automatically restarting the node application when file changes in the directory are detected." It is not a daemon, it does not cluster, and it does not survive your terminal closing. Used in production, it is a footgun; used in development, it is the difference between a fast loop and a tedious one.

```bash
npm install --save-dev nodemon
nodemon ./server.js
```

That is the whole happy path: edit a file, nodemon restarts, you keep your train of thought. Configuration belongs in `package.json` under `nodemonConfig`, so it travels with the project:

```json
{
  "name": "my-api",
  "scripts": { "dev": "nodemon ./src/server.js" },
  "nodemonConfig": {
    "ignore": ["**/test/**", "**/docs/**"],
    "delay": 2500
  }
}
```

The `delay` key is worth knowing: it debounces restarts, so saving three files in quick succession triggers one restart instead of three. `ignore` keeps test runs and generated directories from restarting your server in a loop. And nodemon is not Node-only — the `--exec` flag runs anything:

```bash
nodemon --exec "python -v" ./app.py
```

It will watch `.py` files and restart Python on change, which makes it a handy universal dev loop for polyglot repos. If you pair it with a scheduler library for cron-style jobs, our [Node.js job scheduling comparison](../2026-08-10-nodejs-job-scheduling-libraries-node-cron-bree-agenda/) shows the ecosystem around long-running Node processes.

## forever: The Reliable Legacy

forever was the standard answer to "my Node app dies when I close SSH" from 2013 to 2016 — a simple CLI that keeps a script running "forever" and gives you a list of managed processes. Its basic shape is still clean:

```bash
npm install forever -g
forever start app.js
forever list        # managed processes with uid, pid, uptime
forever logs 0      # tail logs for process index 0
forever stop 0      # stop by index or uid
forever restart app
```

It works — and that is precisely the problem. The repository has seen **no commits since May 2023**, the issues queue accumulates open bug reports, and every feature it has (crash restart, log files, process listing) exists in pm2 with more polish, cluster mode, and an active maintainer. There is no scenario in 2026 where starting fresh with forever is the right call. The only reason to know it is legacy migrations, which the next section covers.

## Migration and Coexistence Strategies

**The standard two-phase setup.** Put nodemon in `devDependencies` and wire it to your `npm run dev` script; put pm2 in production with an `ecosystem.config.js`. The environment variable is the switch — your `dev` script sets `NODE_ENV=development` and uses nodemon, your production start command uses pm2. Nothing about the application code changes between phases.

**Migrating from forever to pm2** is a twenty-minute job with no code changes:

```bash
forever list               # see what is running
forever stop 0             # stop each managed process
# or: forever stopall

pm2 start ecosystem.config.js   # start the same apps under pm2
pm2 save                        # persist the list
pm2 startup                     # survive reboots
```

The process list, log paths, and restart behavior map one-to-one. The one thing to verify during migration is **log rotation** — forever wrote single growing files, while pm2's `pm2-logrotate` module rotates and compresses them. Install it or your disk fills up in a month on a chatty app.

**Docker and pm2 — the subtle one.** Inside a container, pm2's daemon mode is wrong: a daemonized process makes PID 1 exit, and the container dies. Use `pm2-runtime` instead, which runs pm2 in foreground with the process list as PID 1. And in Kubernetes you typically drop pm2 entirely — the orchestrator does restarts and scaling, and your app should be a single process per pod. pm2's cluster mode and K8s replicas do the same job; running both double-schedules your workers.

**CI considerations.** A common CI pattern is starting the app with pm2, running integration tests, then tearing it down — `pm2 start app.js && npm test && pm2 kill`. Works fine, but remember pm2 keeps a daemon alive between jobs on shared runners; always `pm2 kill` at the end or the next job inherits your process list.

## Common Pitfalls and Performance Traps

**1. Running nodemon in production.** It restarts on every file change — including log files and uploads if you ignore nothing — and it does not daemonize, so your process dies with the deploy SSH session. If you need file-watching in production, use pm2's `--watch` mode, which is designed for it.

**2. Cluster mode with in-memory state.** Each cluster worker is a separate process. Sessions, socket rooms, and in-process caches are per-worker — sticky sessions or a shared store (Redis, Postgres) are mandatory once you scale past one instance. The same applies to `for` loop counters and other accidental global state.

**3. Forgetting `pm2 save` + `pm2 startup`.** Without them, your beautifully configured process list evaporates on reboot. The README pattern is `pm2 save` immediately after a stable config, `pm2 startup` once per machine — and verify the generated systemd unit actually starts pm2 at boot.

**4. `max_memory_restart` set too low.** A Node process with a 256M cap that legitimately needs 400M will restart in an endless crash loop, and pm2's restart counter will climb silently. Set the cap from real memory measurements, then leave headroom.

**5. Single-process log file growth.** pm2's default log files grow forever. Install `pm2-logrotate` (built by the pm2 team) and configure `max_size`, `retain`, and compression on day one.

**6. forever orphans.** forever processes are plain children of the init system with no health checking. After a crash loop, old log files and zombie processes accumulate — `forever cleanlogs` exists precisely because this was a known pain.

**7. Port conflicts in cluster mode.** If your app binds a fixed port, pm2's cluster LB handles distribution — but if you bind `0.0.0.0:PORT` inside a Docker container while also using `-i max`, workers fight over the port. Let pm2 own the port in cluster mode; in Docker use one instance per container.

## FAQ

**What is the difference between nodemon and pm2?**
nodemon is a development tool that restarts your app when source files change; pm2 is a production process manager that daemonizes your app, restarts it on crash, balances load across cores, and restores it after reboot. Many projects use both: nodemon for the dev loop, pm2 in production.

**Is forever still maintained?**
Effectively no. The forever repository's last push was May 2023, and it receives no active maintenance. It still works for simple cases, but pm2 provides every feature it has plus clustering, log rotation, and active development.

**Does pm2 work with Bun?**
Yes — pm2 explicitly supports Bun as a runtime (`bun install pm2 -g`), and on Bun-only systems you can symlink `node` to `bun` so pm2's shebang resolves. Cluster mode and process management work the same way.

**Do I need pm2 if I use Docker or Kubernetes?**
In Docker, use `pm2-runtime` (foreground mode) or skip pm2 entirely and rely on the container runtime. In Kubernetes, the orchestrator already provides restarts and scaling — run one Node process per pod and let K8s manage lifecycle. pm2 shines on bare VPS and VM deployments.

**How do I make pm2 start my app after a server reboot?**
Run `pm2 save` to snapshot your process list, then `pm2 startup`, which generates a systemd (or equivalent) unit that restores pm2's processes at boot. Test with a reboot — it is the most commonly skipped production step.

**Can nodemon watch non-JavaScript files?**
Yes. Use `nodemon --exec "command" ./file.ext` to run and watch other languages, and the `execMap` option in `nodemon.json` to define custom defaults per extension.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Process Managers in 2026: pm2 vs nodemon vs forever — Which Do You Need?",
  "description": "Compare pm2, nodemon, and forever for Node.js process management in 2026: features, cluster mode, migration strategies, Docker considerations, and a use-case decision matrix.",
  "datePublished": "2026-08-17",
  "dateModified": "2026-08-17",
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
