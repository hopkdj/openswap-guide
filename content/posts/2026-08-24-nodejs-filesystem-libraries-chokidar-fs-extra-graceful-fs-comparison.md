---
title: "Chokidar vs fs-extra vs graceful-fs in 2026: Which Node.js File Library Should You Use?"
date: "2026-08-24"
tags: ["nodejs", "filesystem", "developer-tools", "npm-libraries"]
draft: false
cover: "/img/screenshots/chokidar-cover.jpg"
---

Your Node.js process just crashed with `EMFILE: too many open files` at 2 a.m., your file watcher is silently dropping changes on a network drive, or your build script's `rm -rf` + `cp -r` dance is deleting half the files it touches. Every Node developer hits these walls eventually, and the standard library's `fs` module refuses to help. The three libraries in this comparison exist for exactly these three pain points — and picking the wrong one costs you nights of debugging.

**Chokidar** (12,221 stars) is the de facto file-watching library used by webpack, Vite, and nearly every bundler in the ecosystem. **fs-extra** (9,596 stars) wraps the standard `fs` module with the convenience methods everyone ends up writing themselves — `copy()`, `remove()`, `mkdirs()`, `move()`. **graceful-fs** (1,302 stars) is a drop-in patch that makes `fs` resilient to file-descriptor exhaustion, queueing and retrying operations instead of crashing your process.

## TL;DR: Quick Verdict

**If you need to watch files for changes, use Chokidar** — nothing else in the Node ecosystem matches its cross-platform reliability, and its `awaitWriteFinish` option alone solves the "my watcher fired before the file finished writing" class of bugs. **If you need to copy, move, or delete trees of files, use fs-extra** — it is a strict superset of `fs` with sane defaults, so adopting it costs nothing. **graceful-fs is not an alternative to either** — it is a foundation layer that should be added to any long-running process that opens many files, and it is most effective when used together with the other two. The trio is complementary, and production Node applications routinely ship all three.

## Feature Comparison: Chokidar vs fs-extra vs graceful-fs

| Capability | Chokidar | fs-extra | graceful-fs |
|---|---|---|---|
| Primary role | File watching | File operations | fs hardening |
| Recursive directory watching | ✅ Native | ❌ (not a watcher) | ❌ (not a watcher) |
| `copy()` / `move()` / `remove()` helpers | ❌ | ✅ (with `fs.copyFile` fallback) | ❌ |
| `mkdirs()` recursive mkdir | ❌ | ✅ | ❌ |
| EMFILE queueing & retry | ❌ | ❌ | ✅ (incremental backoff) |
| EAGAIN read retry | ❌ | ❌ | ✅ |
| Windows rename retry (antivirus lock) | ❌ | ❌ | ✅ |
| Sync API support | ❌ | ✅ (`copySync`, `removeSync`) | ⚠️ no EMFILE handling in sync calls |
| Dependency footprint | Moderate (uses fsevents on macOS) | Zero runtime deps | Zero runtime deps |
| License | MIT | MIT | BlueOak-1.0.0 |
| GitHub stars | 12,221 | 9,596 | 1,302 |
| Last push | 2026-08-16 | 2026-07-23 | 2025-10 |

The table shows why these are not competitors: **Chokidar watches, fs-extra mutates, graceful-fs hardens.** The overlap is minimal, and the "which one" question only makes sense once you know which problem you are solving.

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Watch source files for a dev server or bundler | **Chokidar** | Production-tested by webpack/Vite; handles atomic saves, editor temp files, and poll fallbacks |
| Rebuild assets after a file finishes writing | **Chokidar** with `awaitWriteFinish: true` | The single most useful option for build pipelines — fires only after writes settle |
| Backup script that copies a directory tree | **fs-extra** | `copy()` with `preserveTimestamps` behaves like `cp -r`, unlike naive `readdir` loops |
| Deploy script that clears and recreates a folder | **fs-extra** | `emptyDir()` + `removeSync()` are exactly the semantics you want |
| Long-running worker that opens hundreds of files | **graceful-fs** | EMFILE backoff prevents the classic fd-exhaustion crash; pair with a higher `ulimit` |
| Electron/main-process file access | **graceful-fs** | Electron's main process is the highest-risk EMFILE environment; it is bundled with the framework for a reason |
| Everything above, in one app | **All three** | They compose cleanly — fs-extra's internals even use graceful-fs semantics when available |

## Chokidar — The File Watcher Everyone Uses

Chokidar has been the industry-standard watcher since 2012. Webpack, Vite, Parcel, and a long tail of build tools depend on it, which means its edge cases are battle-tested to an unusual degree. Its core API is a one-liner:

```javascript
import chokidar from 'chokidar';

// One-liner for current directory
chokidar.watch('.').on('all', (event, path) => {
  console.log(event, path);
});
```

The `event` argument is one of `add`, `change`, `unlink`, `addDir`, `unlinkDir`, or `error`. Under the hood Chokidar uses native `fs.watch` where available (with `fsevents` for deeper macOS recursion) and falls back to a polling mode when you pass `usePolling: true` — the escape hatch for network drives, Docker volumes on macOS, and NFS mounts where inotify/fsevents events never arrive.

The option that pays for the library by itself is `awaitWriteFinish`:

```javascript
chokidar.watch('src', {
  ignoreInitial: true,
  awaitWriteFinish: {
    stabilityThreshold: 2000,   // wait 2s of no writes before emitting
    pollInterval: 100
  }
}).on('add', path => console.log('compiled file ready:', path));
```

Without it, editors that write a file in multiple chunks (Vim, JetBrains IDEs, anything doing atomic save via temp file + rename) trigger `add` or `change` events while the file is still half-written. Build pipelines that read the file immediately then race the writer. `awaitWriteFinish` collapses all that noise into a single event after the write stream goes quiet — **the fix for an entire class of "intermittently broken rebuild" bugs**.

Chokidar also ships `atomic` (debounces writes followed by renames), `ignoreInitial` (skip pre-existing files), and `depth` limits for recursive watching. The maintained project pushes regularly (last commit 2026-08-16) under the MIT license.

## fs-extra — The `fs` Module, Completed

fs-extra began as a grab-bag of convenience methods and became the most-downloaded file library in the ecosystem (hundreds of millions of weekly installs via transitive dependencies). It re-exports the entire standard `fs` module and adds the methods the standard library inexplicably lacks. The killer API is `copy()`:

```javascript
// Async with promises:
fs.copy('/tmp/myfile', '/tmp/mynewfile')
  .then(() => console.log('success!'))
  .catch(err => console.error(err));

// Sync:
try {
  fs.copySync('/tmp/myfile', '/tmp/mynewfile');
  console.log('success!');
} catch (err) {
  console.error(err);
}

// Async/Await:
async function copyFiles() {
  try {
    await fs.copy('/tmp/myfile', '/tmp/mynewfile');
    console.log('success!');
  } catch (err) {
    console.error(err);
  }
}
```

`copy()` recursively copies directories, preserves symlinks and timestamps when you pass `{ preserveTimestamps: true }`, and refuses to overwrite files unless you pass `{ overwrite: true }` — the last one is a deliberate safety default that has saved more than one production deployment from a typo'd path. The other flagship methods are equally boring and equally essential:

```javascript
const fs = require('fs-extra');

await fs.mkdirs('/tmp/some/deeply/nested/dir');   // mkdir -p
await fs.remove('/tmp/old-build');                 // rm -rf
await fs.move('/tmp/from.txt', '/tmp/to.txt');     // mv
await fs.emptyDir('/tmp/cache');                   // rm -rf + mkdir
await fs.readJson('/tmp/config.json');             // read + parse
```

`remove()` is particularly worth calling out: hand-rolled recursive deletion in Node is a minefield (symlink loops, permission errors mid-tree, `fs.rm` semantics changing between Node versions). fs-extra handles it and every edge case with it. The project is dependency-free, MIT-licensed, and actively maintained (last push 2026-07-23).

## graceful-fs — The Crash Preventer

`EMFILE: too many open files` is Node's most infamous production crash. The default per-process file-descriptor limit on Linux is 1024 (`ulimit -n`), and any real workload — a bundler, a test runner, a static analyzer, an Electron main process — can blow through it in seconds when file operations queue up faster than the OS closes descriptors. graceful-fs exists to make that failure mode impossible. It is a drop-in replacement:

```javascript
const fs = require('graceful-fs');
// now fs.open/fs.read/fs.readdir queue and retry on EMFILE/ENFILE
```

Under the hood it queues `open` and `readdir` calls and retries them once a file descriptor frees up, with incremental backoff; retries `read` on `EAGAIN`; and on Windows retries renames for up to a second when antivirus software briefly locks a file (`EACCES`/`EPERM`). It also normalizes `lchmod`/`lutimes` behavior across platforms. The npm ecosystem uses it so aggressively that it is a transitive dependency of npm itself — when you run `npm install`, you are using graceful-fs.

Its one documented limitation matters in practice: **sync methods cannot intercept `EMFILE` or `ENFILE` errors**, because a sync call blocks the event loop and there is no opportunity to queue and retry. If you use `fs.readFileSync` in a tight loop, graceful-fs will not save you — the fix there is structure, not a library. It is also a patching layer: you use it by *replacing* `fs` in your module scope, and you should **never** apply the global `gracefulify` patch to monkey-patch the shared `fs` module in a library, because it silently changes behavior for every consumer of that process.

The project is stable and intentionally quiet (last push 2025-10, 1,302 stars) — that quietness is the point. It is licensed under BlueOak-1.0.0 rather than MIT, which matters only for teams whose legal review insists on MIT-only dependencies.

## Pitfalls and Migration Gotchas

**1. Chokidar and atomic saves.** Editors that write via temp-file-plus-rename (Vim, VS Code with certain settings, most CI checkouts) emit `unlink` + `add` where you expected `change`. Filter with `atomic: true` or embrace `awaitWriteFinish` — do not try to reconstruct state from event pairs.

**2. Chokidar on network mounts.** inotify and fsevents do not work on NFS, SMB, or Docker-for-mac bind mounts. Symptoms: zero events, or events only when you touch a file yourself. Fix: `usePolling: true` with an `interval` — and accept the CPU cost, which is the trade-off you are buying.

**3. Chokidar memory growth.** `watch('.')` on a huge tree (e.g. `node_modules`) builds a file map in memory. Always add `ignored: /node_modules/` (or use `ignored: (path) => path.includes('node_modules')`) — and never watch a directory that is being mutated by the build process you are triggering, or you get feedback-loop rebuilds.

**4. fs-extra `copy()` will not overwrite by default.** The `{ overwrite: true }` flag is off by default, and `copy()` throws on an existing destination file. Scripts migrated from `cp -r` (which overwrites silently) break on the first rerun — decide explicitly which semantics you want.

**5. fs-extra `move()` across devices.** Moving between different filesystems (e.g. tmpfs to disk) is not an atomic rename; fs-extra falls back to copy-plus-delete. That is correct behavior, but it is slow and it means the destination is briefly absent — do not move into a directory your watcher is monitoring without accounting for the gap.

**6. graceful-fs does not fix sync code.** `readFileSync`/`writeFileSync` loops still crash with EMFILE. Restructure to async or batch with `Promise.all` under a concurrency limit; graceful-fs only smooths the async paths.

**7. Raising `ulimit -n` is not a substitute.** Bumping the limit from 1024 to 65536 treats the symptom; graceful-fs treats the cause (bursts of opens outrunning closes). Production Node services should do both — a sane limit plus the backoff layer.

**8. Don't patch global `fs` in a library.** `graceful-fs`'s `gracefulify` patches the module-level `fs` object. In an application that is a legitimate choice; in a published library it is hostile to consumers. Import it locally instead.

If you are building on the Node ecosystem, our [Node.js process managers comparison](../2026-08-17-nodejs-process-managers-pm2-nodemon-forever-comparison/) covers keeping those watchers alive in production, and the [Node.js job scheduling guide](../2026-08-10-nodejs-job-scheduling-libraries-node-cron-bree-agenda/) shows where cron-style file jobs fit. For scripting workflows built around these libraries, see our [Node.js shell scripting comparison](../2026-08-17-nodejs-shell-scripting-zx-shelljs-execa-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Chokidar vs fs-extra vs graceful-fs in 2026: Which Node.js File Library Should You Use?",
  "description": "Deep comparison of Node.js filesystem libraries: Chokidar for file watching, fs-extra for copy/move/remove helpers, graceful-fs for EMFILE resilience. Real code samples, pitfalls, and a use-case decision matrix.",
  "datePublished": "2026-08-24",
  "dateModified": "2026-08-24",
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

### Is Chokidar compatible with Deno and Bun?

Chokidar targets Node.js and browsers, and the core watcher works in Bun via its Node compatibility layer. For Deno, the maintainers recommend the built-in `Deno.watch` API or `@tauri-apps/plugin-fs` watchers; Chokidar is not the default choice there. In Node and Bun it remains the standard.

### What is the difference between fs-extra and the native fs.promises API?

The native `fs.promises` module covers basic read/write/stat operations, but it has no `copy()` that recursively copies directories (Node added `fs.cp` in v16.7, with different defaults), no `mkdirs()`, no `emptyDir()`, and no `remove()`. fs-extra provides those on top of the same promise API and keeps compatibility with older Node versions.

### Does graceful-fs fix EMFILE errors in sync code?

No. Sync methods block the event loop, so there is no chance to queue and retry when file descriptors are exhausted. graceful-fs explicitly documents that it cannot intercept `EMFILE`/`ENFILE` from sync methods — you must restructure to async I/O or raise the process limit.

### Why does Chokidar sometimes miss events on macOS?

On macOS, Chokidar uses `fsevents` for recursive watching. Events can be missed when a watched directory is replaced wholesale (rename), or when the OS coalesces rapid changes. Setting `usePolling: true` for those specific paths, or using `atomic: true` plus `awaitWriteFinish`, resolves the common cases.

### Can I use all three libraries in one project?

Yes — they compose cleanly. A typical production setup uses graceful-fs as the hardened foundation (directly or transitively), fs-extra for build/deploy file operations, and Chokidar for dev-time watching. There is no API overlap that would cause conflicts.

### Is fs-extra still maintained in 2026?

Yes. The project had its most recent push on 2026-07-23, is dependency-free, and remains the most widely installed file helper in the npm ecosystem. Its API is stable, so commits are infrequent but real.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
