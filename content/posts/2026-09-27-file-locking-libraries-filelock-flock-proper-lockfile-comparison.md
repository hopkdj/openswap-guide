---
title: "File Locking Libraries in 2026: filelock vs flock vs proper-lockfile"
date: "2026-09-27"
tags: ["file-locking", "concurrency", "developer-tools", "python", "go", "nodejs", "php", "rust"]
draft: false
cover: "/img/screenshots/filelock-python-library-logo.jpg"
description: "How to stop two processes from corrupting the same file: a hands-on comparison of tox-dev/filelock, gofrs/flock, node-proper-lockfile, symfony/lock and Rust's fs4, with real code, live star counts and the advisory-lock traps that bite on NFS."
---

Two replicas of your self-hosted job runner wake up at 02:00. Both decide it is their turn to rebuild the nightly report. Both read the same state file, both write the same output, and by morning you have a half-written CSV plus a duplicate charge in your invoicing table. Nothing in your infrastructure was misconfigured — you simply never told the two processes that the file is a shared resource. That is a *file locking* problem, and it is solved in application code, not by adding another container.

This is a practical comparison of the five libraries that do the work in 2026 — **tox-dev/filelock (978 stars), gofrs/flock (759), symfony/lock (516), node-proper-lockfile (285) and Rust's fs4 (120)** — with live repository data pulled on 2026-09-27 and code taken from each project's own documentation.

## TL;DR — Quick Verdict

- **Python**: [tox-dev/filelock](https://github.com/tox-dev/filelock). One `with` block, a real `Timeout` exception, and an asyncio variant in the same package. This is the default answer.
- **Go**: [gofrs/flock](https://github.com/gofrs/flock). Thread-safe wrapper over `flock(2)` on Unix and `LockFileEx` on Windows, with a `TryLock` you can retry on.
- **Node.js**: [moxystudio/node-proper-lockfile](https://github.com/moxystudio/node-proper-lockfile). The `mkdir` strategy is the only approach that behaves on network filesystems — but its **last commit was 2023-10-25**, so treat it as feature-frozen and pin the version.
- **PHP**: [symfony/lock](https://github.com/symfony/lock). Pluggable stores, and `Key` serialization when a job has to hold a lock across requests.
- **Rust**: [fs4](https://github.com/al8n/fs4) (the maintained fork of `fs2`) when you need async or rustix; otherwise the standard library's own file-locking methods cover the simple case.
- **Multiple hosts**: none of the above. A file lock is exclusive *per filesystem*, not per cluster — for that you need a real distributed lock coordinator.

## Live Comparison Table (2026-09-27)

| Library | Language | Stars | License | Last commit | Mechanism | Safe on network FS? | Stale locks |
|---|---|---|---|---|---|---|---|
| tox-dev/filelock | Python | **978** | MIT | 2026-09-26 | `flock`/`LockFileEx` via Unix & Windows classes, plus `SoftFileLock` | same caveats as the underlying syscall | configurable `timeout`, `Timeout` exception |
| gofrs/flock | Go | **759** | BSD-3-Clause | 2026-09-01 | `flock(2)` on Unix, `LockFileEx` on Windows | advisory; depends on mount options | `TryLock` + your own retry loop |
| symfony/lock | PHP | **516** | MIT | 2026-09-22 | pluggable stores (`SemaphoreStore`, `FlockStore`, …) | store-dependent | TTL/expiry, blocking `acquire(true)` |
| node-proper-lockfile | Node.js | **285** | MIT | 2023-10-25 | `mkdir` + lockfile `mtime` heartbeat | **yes** — `mkdir` is atomic anywhere | `stale` (default 10s) + `onCompromised` |
| fs4 | Rust | **120** | Apache-2.0 | 2026-04-28 | fork of `fs2` using rustix, sync + async | advisory | caller-managed |

One row deserves emphasis before anything else: three of these have shipped commits within the last week, and one has not had a commit in nearly three years. `node-proper-lockfile` is still the correct choice in Node when you must lock across a network mount, precisely because it avoids OS lock semantics entirely — but you are depending on behaviour that will not change, so pin it.

## Decision Matrix

| Your situation | Pick this | Why |
|---|---|---|
| A Python cron job that must not run twice | tox-dev/filelock | Smallest correct API: `with FileLock(path)` and a `Timeout` you can log |
| Python async service with a shared cache directory | tox-dev/filelock (`filelock.asyncio`) | Same semantics without blocking the event loop |
| Go CLI doing an in-place file update | gofrs/flock | `TryLock` gives you the "skip this run" path without spawning a goroutine |
| Workers writing to a shared NFS/SMB mount | node-proper-lockfile | `mkdir` is atomic on network filesystems where `flock` is not honoured |
| Symfony/Laravel command that must not overlap | symfony/lock | `LockFactory` + store, plus `Key` if the job spans requests |
| Rust with an async runtime | fs4 | Async features over rustix, maintained past `fs2` |
| You need exclusion across several machines | a distributed coordinator | File locks are filesystem-scoped; see our [distributed locking comparison](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/) |

## The Libraries in Depth

### tox-dev/filelock — the Python default

filelock is a platform-independent file lock built as a context manager, and it is the smallest amount of code that correctly expresses "one writer at a time". Install it, then take the lock with an explicit timeout so a stuck holder cannot hang your job forever:

```bash
pip install filelock
```

```python
from filelock import FileLock, Timeout

lock = FileLock("work.lock", timeout=10)

try:
    with lock:
        # This will wait up to 10 seconds for the lock
        print("Got the lock!")
except Timeout:
    print("Couldn't get the lock after 10 seconds")
```

The timeout can also be passed per acquisition, which is how you keep one long-running holder from blocking a fast path:

```python
lock = FileLock("work.lock")

try:
    with lock.acquire(timeout=5):
        print("Got the lock!")
except Timeout:
    print("Timeout after 5 seconds")
```

Two design constraints from the project's own documentation are worth internalising. First, **all contenders must agree on the path** — a lock is a rendezvous on one pathname, so resolve symlinks and relative paths identically everywhere. Bind-mounted containers make this easy to get wrong: same file, two paths, no exclusion. Second, filelock creates the *lock file's* parent directories automatically, but **not** the directories of the resource you are protecting.

With filelock you can also implement the best-effort pattern used by caches: the lock exists to prevent duplicated work, not to guarantee correctness, so losing the lock is a performance event rather than a data-integrity event:

```python
def get(target: Path, produce) -> bytes:
    lock = FileLock(f"{target}.lock")
    try:
        with lock.acquire(timeout=30):
            if not target.exists():
                populate(target, produce)
    except Timeout:
        if not target.exists():  # the lock only saved duplicate work; do the work anyway
            populate(target, produce)
    return target.read_bytes()
```

That is only safe because the writer publishes with an atomic rename (`os.replace` is atomic within a filesystem), so a reader always observes a complete file. If your writer can leave a partial file behind, the lock is a correctness requirement and you must not fall through on `Timeout`.

### gofrs/flock — Go, with a TryLock you can retry

The Go library is a thin, thread-safe layer over the platform's native advisory lock, which is exactly what you want: no custom file formats, no heartbeat threads, and the kernel releases the lock if the process dies.

```bash
go get -u github.com/gofrs/flock
```

```go
import "github.com/gofrs/flock"

fileLock := flock.New("/var/lock/go-lock.lock")

locked, err := fileLock.TryLock()

if err != nil {
	// handle locking error
}

if locked {
	// do work
	fileLock.Unlock()
}
```

The idiomatic pattern for a self-hosted scheduler is `TryLock` in a bounded retry loop: if the lock is held, another instance is already doing the work, so log it and exit 0. Blocking with `Lock()` is what turns a healthy overlap into a pile of stuck processes.

Two caveats belong in your design document. The lock is **advisory**: any process that does not use `flock` can still write the file, so you cannot treat this as protection against a rogue cron script or a misconfigured backup agent. And the lock file path itself is the rendezvous — two services that construct the path differently, or run in containers with different mount namespaces, will lock two different files and believe they are safe.

### symfony/lock — stores, factories and serialisable keys

The Symfony component decouples *what* is locked from *how* it is enforced. A `LockFactory` is built around a store, and the factory creates locks by resource name:

```php
use Symfony\Component\Lock\LockFactory;
use Symfony\Component\Lock\Store\SemaphoreStore;

$store = new SemaphoreStore();
$factory = new LockFactory($store);
```

```php
// ...
$lock = $factory->createLock('pdf-creation');

if ($lock->acquire()) {
    // The resource "pdf-creation" is locked.
    // You can compute and generate the invoice safely here.

    $lock->release();
}
```

Swapping `SemaphoreStore` for a filesystem store is a one-line change, and the blocking variant is explicit rather than implicit:

```php
use Symfony\Component\Lock\LockFactory;
use Symfony\Component\Lock\Store\FlockStore;

$store = new FlockStore('/var/stores');
$factory = new LockFactory($store);

$lock = $factory->createLock('pdf-creation');
// $lock->acquire(true) blocks until the lock is available
```

Three behaviours in the documentation are easy to miss and expensive to discover in production. Locks are released automatically when the lock instance is destroyed unless you pass `false` as the third argument to `createLock()` — which is how you hold a lock across several requests. Locks distinguish *instances* even for the same resource, so services that must coordinate have to share the same `Lock` instance from the factory. And `Symfony\Component\Lock\Key` is serialisable, so a long job can acquire in a web request and release from a worker.

### node-proper-lockfile — the network-filesystem answer

The Node library deliberately does not use OS locking. It creates a directory next to the file, because `mkdir` fails atomically everywhere, including NFS and SMB mounts where `flock` semantics are unreliable:

```bash
npm install proper-lockfile
```

```javascript
lockfile.lock('some/file')
.then((release) => {
    // Do something while the file is locked

    // Call the provided release function when you're done,
    // which will also return a promise
    return release();
})
.catch((e) => {
    // handle failure to get a lock
});
```

The mechanism is documented precisely: the lockfile path is the target path suffixed with `.lock`, and while the lock is held its `mtime` is periodically refreshed so that staleness can be detected by comparing `mtime` against a threshold. If refreshing fails repeatedly, the lock is considered compromised and `onCompromised` fires. The options that matter:

| Option | Default | What it controls |
|---|---|---|
| `stale` | 10000 ms (min 5000) | Age at which a lock is considered abandoned |
| `update` | `stale / 2` (min 1000, max `stale/2`) | Heartbeat interval that refreshes `mtime` |
| `retries` | 0 | Number of retries, or a retry options object |
| `realpath` | true | Resolve symlinks — the target file must already exist |
| `lockfilePath` | `<file>.lock` | Custom lockfile location, e.g. inside a locked directory |
| `onCompromised` | throws | Called when the mtime heartbeat fails |

Set `stale` above your worst-case job duration, not below it. A `stale` that is too short means a slow-but-healthy job gets its lock stolen mid-write, which is the exact corruption you installed the library to prevent.

### fs4 — the Rust option, and what the standard library already does

`fs4` is the maintained fork of `fs2`: same lock API, but built on rustix and extended with async support. Installation is feature-gated, so you pick the runtime you actually have:

```toml
[dependencies]
fs4 = { version = "1", features = ["sync"] }
```

```toml
[dependencies]
fs4 = { version = "1", features = ["async-std"] }
```

Rust's standard library has also grown file-locking methods on `File`, which narrows the reason to reach for a crate to two cases: async runtimes that cannot block a thread on a lock, and Linux-specific behaviour that the portable API does not expose. If you are writing a synchronous CLI, evaluate the standard library first; if you need `async-std`/Tokio integration, fs4 is the crate that is actually maintained.

## Pitfalls That Cost You Data

**1. Advisory does not mean enforced.** `flock`, `LockFileEx` and fs4 all take *advisory* locks. A process that does not ask for the lock can write the file anyway. If a misconfigured backup or editor agent writes the same path, nothing will stop it — lock discipline is a property of your whole system, not of one library.

**2. A lock is a pathname, not a file.** All contenders must agree on the resolved path. Symlinks, relative paths and bind mounts inside containers routinely produce two paths for one file, and two locks that exclude nothing. Resolve with `realpath` (proper-lockfile does this by default) and log the resolved path at startup.

**3. `SoftFileLock` protects only against the well-behaved.** A soft lock is implemented without OS support and is fine for pure-Python single-host coordination, but it cannot exclude a different process, a different language, or a crashed holder. Never use a soft lock as the only protection for shared state.

**4. Locks do not survive an atomic replace.** If your writer publishes by writing a temp file and renaming it over the target, you have replaced the inode that was locked. Lock a *separate* lock file, never the file you are about to rename into place.

**5. Short `stale` values steal locks from healthy jobs.** The proper-lockfile heartbeat exists so fast readers do not wait forever. If your job legitimately runs 45 minutes and `stale` is 10 seconds, the lock will be taken mid-write.

**6. Reentrancy is library-specific.** filelock is reentrant within a process; gofrs/flock expects you to manage the instance yourself. Do not assume that nesting two locks on the same resource is harmless in every ecosystem.

**7. File locks are not distributed locks.** Across hosts and containers you need a coordinator with a real consensus or TTL model. Reaching for a shared NFS directory as a lock manager is a classic way to build a system that fails only when a node is slow.

**8. Always take a timeout.** A cron job that blocks forever on a lock is worse than one that fails loudly: it burns a slot in your scheduler and hides the real problem. Every example above has a timeout path for a reason.

## Why Self-Hosted Stacks Hit This First

Managed platforms quietly give you one process, one volume, one writer, and a platform-level job scheduler that never runs the same task twice. Self-hosting removes all of that at once: you deploy two replicas for availability, you mount a shared volume for persistence, and you run a cron-like scheduler that fires on every replica. That is a textbook recipe for concurrent writers.

The operational countermeasures are cheap if you apply them together. Keep writers exclusive per resource with a library from this table. Publish output atomically with a rename so readers never see partial files. Treat shared mounts as a filesystem with the weakest possible lock semantics — our [distributed filesystem comparison](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/) covers where that assumption breaks down. And if the data crosses hosts, sync it deliberately rather than assuming a lock travels with it: the file-sync tools in our [rsync vs rclone vs lsyncd guide](../2026-04-26-rsync-vs-rclone-vs-lsyncd-self-hosted-file-sync-tools-guide-2026/) show how differently each tool handles a file that changes mid-transfer.

None of these libraries needs a compose file. They are ordinary dependencies — `pip install filelock`, `go get github.com/gofrs/flock`, `npm install proper-lockfile`, `composer require symfony/lock`, `fs4 = "1"` — so the deployment decision is only where the lock paths live. Put them on a local disk when hosts are the scope, and on the shared mount only when every contender resolves the exact same path.

## FAQ

**What is the difference between a file lock and a distributed lock?**
A file lock excludes processes that see the same filesystem; the kernel (or a `mkdir` race) decides who wins. A distributed lock excludes processes across machines and needs a coordinator with TTLs or consensus, such as etcd, ZooKeeper, Consul or Redis. A file lock on a shared NFS mount is not a substitute, because NFS lock semantics vary by version and mount option.

**Which library should I use for Python?**
tox-dev/filelock unless you have a specific reason not to. It supports the Unix and Windows lock primitives behind one API, exposes a `Timeout` exception for the timeout path, ships an asyncio variant in the same package, and is actively maintained — its most recent commit was 2026-09-26.

**Is node-proper-lockfile abandoned?**
Its most recent commit is 2023-10-25, so it is feature-frozen rather than dead: 285 stars, MIT-licensed, and still the only mainstream Node option that locks reliably across network filesystems because it uses an atomic `mkdir` instead of OS lock calls. Pin the version you tested and add a test for the stale-lock path.

**How do I stop a cron job from running twice?**
Take a non-blocking lock at start-up and exit cleanly if it fails. In Python: `FileLock(path, timeout=0)` inside a `try`/`except Timeout`. In Go: `TryLock()` and return if `locked == false`. The important part is that the second invocation exits 0 and does nothing, so your scheduler does not record a failure.

**Does a file lock survive a crash?**
With OS-backed locks, yes — the kernel drops the lock when the file descriptor closes, including on process death. With lockfile-style approaches such as proper-lockfile, no: you rely on the staleness threshold and the `mtime` heartbeat, which is why `onCompromised` exists.

**Why does my lock stop working on NFS?**
Because NFS lock support depends on the client, server and mount options, and older configurations silently ignore `flock`. The portable answer is an atomic `mkdir` (proper-lockfile) or a dedicated coordinator; the fast answer is to keep the lock on a local filesystem and treat the shared mount as data, not as a lock namespace.

**Should I lock the file I am writing, or a separate lock file?**
A separate lock file. If your write path publishes via an atomic rename, locking the target locks an inode that is about to be replaced, leaving the actual writer unprotected.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "File Locking Libraries in 2026: filelock vs flock vs proper-lockfile",
  "description": "How to stop two processes from corrupting the same file: a hands-on comparison of tox-dev/filelock, gofrs/flock, node-proper-lockfile, symfony/lock and Rust's fs4, with real code, live star counts and the advisory-lock traps that bite on NFS.",
  "datePublished": "2026-09-27",
  "dateModified": "2026-09-27",
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
