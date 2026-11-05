---
title: "Running Untrusted JavaScript in Node.js in 2026: isolated-vm vs quickjs-emscripten vs vm2"
date: "2026-11-05"
tags: ["nodejs", "javascript", "sandboxing", "security", "self-hosted"]
draft: false
---

If your product lets users upload a plugin, write a webhook transform, or paste a formula, you are running someone else's code inside your process. In Node.js the obvious tool for that job — `vm2` — is dead, and it did not die quietly. Its own README now opens with a warning that the library **contains critical security issues and should not be used in production**, after a years-long sequence of sandbox escapes that ended with the maintainer concluding that fixing the last one "seems impossible."

That leaves two real options in 2026: **isolated-vm**, which gives each tenant a genuine V8 isolate, and **quickjs-emscripten**, which runs a different engine compiled to WebAssembly. They solve the same problem with completely different trade-offs, and picking wrong costs you either throughput or an RCE.

## TL;DR: The Quick Verdict

**On Node.js, with a native build toolchain available and latency-sensitive workloads, use isolated-vm.** You get real V8 isolation, a hard memory cap per isolate, and sub-millisecond warm execution.

**If you need the same sandbox to run in a browser, on edge workers, in CI without a C++ toolchain, or you want deterministic interrupts rather than cooperative ones, use quickjs-emscripten.** It is slower to start, cheap to run.

**If you still ship vm2, migrate now.** This is not a "revisit next quarter" item: the project is discontinued and the escape class is structural, not a missing patch.

## The Comparison

| Dimension | isolated-vm | quickjs-emscripten | vm2 |
|---|---|---|---|
| GitHub stars | 2,947 | 1,741 | 4,115 |
| Last push | 2026-11-05 | 2026-07-23 | 2026-10-18 |
| License | ISC | MIT | MIT |
| Isolation mechanism | Separate V8 Isolate in-process | QuickJS (C) compiled to WASM | Proxy-based membrane on `vm` |
| Memory limit | Yes, per isolate (`memoryLimit`) | Yes, per runtime (`setMemoryLimit`) | No reliable cap |
| Execution timeout | Yes, synchronous + async | Yes, interrupt handler | Cooperative only |
| Async/await inside sandbox | Yes, via `Reference` + promises | Yes, via `evalCodeAsync` | Yes |
| Native compilation | Required (node-gyp, C++ toolchain) | None (pure WASM) | None |
| Runs in browser / edge | No | Yes | No |
| Node APIs available by default | None (explicit bridge) | None | Partial through host objects |
| Maintenance status | Active | Active | **Discontinued** |

Decision matrix:

| Your situation | Pick | Why |
|---|---|---|
| Multi-tenant plugin runtime, Node-only backend | isolated-vm | Real isolates, hard memory ceiling, fastest warm path |
| User-supplied transform functions in a SaaS | isolated-vm | Timeout enforcement that actually stops a `while(true)` |
| Sandbox must run in browser and server | quickjs-emscripten | Same WASM build everywhere, no native deps |
| Serverless/edge deployment, no build step | quickjs-emscripten | `npm install` and go |
| Algorithmic code with heavy numeric loops | isolated-vm | V8 JIT beats the interpreter by an order of magnitude |
| Legacy vm2 usage | isolated-vm (or a container per tenant) | Documented migration path from the vm2 maintainers themselves |

## isolated-vm — Real V8 Isolates

`isolated-vm` creates additional V8 isolates inside your Node process. Each isolate has its own heap and its own copy of all builtins, so a tenant that does `Object.prototype.foo = 1` cannot see it from the host, and vice versa. Communication happens through explicit `Reference` objects and copied values — which is exactly the friction you want at a trust boundary.

```bash
npm install isolated-vm
```

The package is native and compiles against your Node headers. On a slim container image you need the toolchain present at install time:

```dockerfile
FROM node:22-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

FROM node:22-bookworm-slim
WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY . .
USER node
CMD ["node", "server.js"]
```

A minimal sandbox with a memory ceiling and a timeout, adapted from the project's own README:

```javascript
const ivm = require('isolated-vm');

async function runUserCode(source, input, { memoryMb = 128, timeoutMs = 200 } = {}) {
  const isolate = new ivm.Isolate({ memoryLimit: memoryMb });
  const context = await isolate.createContext();
  const jail = context.global;

  // Expose a narrow, copy-only bridge. No host objects leak in.
  await jail.set('global', jail.derefInto());
  await jail.set('_log', new ivm.Reference((...args) => console.log('[sandbox]', ...args)));
  await jail.set('input', new ivm.ExternalCopy(input).copyInto());

  const script = await isolate.compileScript(`
    log("starting");
    const result = (function () { ${source} })();
    result;
  `);
  await jail.set('log', new ivm.Reference(() => {}));

  try {
    return await script.run(context, { timeout: timeoutMs, copy: true });
  } finally {
    isolate.dispose();
  }
}

runUserCode('return input.items.filter(i => i.qty > 2).length;', { items: [{ qty: 1 }, { qty: 5 }] })
  .then(n => console.log('matched:', n))
  .catch(err => console.error('sandbox failure:', err.message));
```

Three properties make this practical in production. **Memory is enforced by V8**, so an allocation bomb kills the isolate instead of your container. **`timeout` is enforced by terminating the isolate**, so a synchronous infinite loop cannot hang the event loop. And **nothing is shared**, so the only data that crosses the boundary is what you explicitly copy.

The costs are real too. Each isolate carries a V8 heap and a JIT baseline; plan on tens of megabytes of resident memory per concurrent sandbox, so a multi-tenant service needs a pool rather than an isolate per request. Cross-boundary calls are asynchronous and copy-heavy — pass JSON-shaped data, not live objects. And native compilation means your deploy pipeline must build on the same platform and Node major version as production, which is why the two-stage Dockerfile above exists.

## quickjs-emscripten — A Different Engine, in WebAssembly

`quickjs-emscripten` compiles Fabrice Bellard's QuickJS to WebAssembly and gives you a small, synchronous JavaScript runtime you can instantiate anywhere. There is no native build, no Node dependency, and the same code runs in browsers, workers, and server processes.

```bash
npm install quickjs-emscripten
```

```javascript
import { getQuickJS } from "quickjs-emscripten";

const QuickJS = await getQuickJS();
const vm = QuickJS.newContext();

// Hard resource limits before running anything
vm.runtime.setMemoryLimit(64 * 1024 * 1024);   // 64 MB
vm.runtime.setMaxStackSize(512 * 1024);        // 512 KB

const started = Date.now();
vm.runtime.setInterruptHandler(() => Date.now() - started > 250, Date.now);

const world = vm.newString("world");
vm.setProp(vm.global, "NAME", world);
world.dispose();

const result = vm.evalCode(`"Hello " + NAME + "!"`);
if (result.error) {
  console.log("Execution failed:", vm.dump(result.error));
  result.error.dispose();
} else {
  console.log("Success:", vm.dump(result.value));
  result.value.dispose();
}

vm.dispose();
```

Everything you create — strings, objects, handles — must be disposed. That manual memory discipline is the price of a runtime with no garbage-collected bridge, and forgetting it leaks QuickJS handles until the module's memory limit trips.

What you get in exchange: **the sandbox is a separate engine, not a separate heap in the same engine**. QuickJS has no Node builtins at all, so there is no `require`, no `process`, no `fs` unless you explicitly wire host functions in. The interrupt handler gives you a proper execution budget that fires inside tight loops. And it is portable enough to run the identical sandbox logic in a Cloudflare Worker and in a container.

What you give up: throughput. QuickJS is an interpreter with no JIT, so numeric workloads that V8 finishes in 2 ms can take 40–80 ms. Cold start also matters — instantiating the WASM module takes tens of milliseconds, so cache the module and reuse contexts where you safely can.

## vm2 — What Went Wrong

vm2 tried to build a sandbox inside the same V8 realm, using `Proxy` objects to intercept property access and prevent the sandboxed code from reaching host objects. Every defense was a membrane over a shared engine, and JavaScript's reflective surface is enormous. Repeated escapes followed: the widely tracked promise-based escape, the `Error.prepareStackTrace` escape, and further variants through `Proxy` and `Symbol` handling.

The maintainers eventually handed the project to the n8n organization, which now publishes it with a discontinuation notice and a direct recommendation to migrate to isolated-vm. If you are evaluating sandboxes by download counts, this is the trap: **4,115 stars and heavy npm usage do not indicate safety**. A sandbox that shares a realm with your host code is one reflective trick away from full access to `process.env`, your database credentials, and your filesystem.

There is a second lesson worth internalizing. "Sandbox escape" does not require exotic hardware attacks — it usually means a tenant's code reached a host function reference and called `.constructor.constructor("return process")()`. Isolation must be structural (separate engine or separate process), not a runtime wrapper.

## Hardening Beyond the Library

Whichever engine you choose, the library is one layer of a stack:

- **Run the sandbox in its own process or container per trust tier.** In-process isolation protects your heap; it does not protect against a zero-day in the engine. Our [container sandboxing comparison](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) covers the gVisor/Kata/Firecracker trade-offs if you want kernel-level separation.
- **Drop privileges and syscalls.** If the only thing the tenant's code touches is stdin/stdout JSON, a seccomp profile and a non-root user cost nothing. The [process sandboxing toolchain](../2026-05-20-self-hosted-process-sandboxing-firejail-bubblewrap-nsjail-guide/) covers firejail, bubblewrap, and nsjail.
- **Cap CPU, wall clock, and memory at every layer.** Library limits stop runaway loops; cgroup limits stop a fork bomb or a leak in the bridge itself.
- **Copy, never reference.** Every object you hand across the boundary is an escape surface. Serialize to JSON and back, even when the library offers zero-copy references.
- **Treat the sandbox as a plugin ABI, not an eval call.** The [embeddable plugin system comparison](../2026-06-20-embeddable-plugin-systems-extism-pluggy-abi-stable-libloading/) covers WASM-based plugin hosts (Extism, Pluggy) if you want tenant code that is portable across languages.

## Benchmarks and Sizing Guidance

Numbers you can reproduce on any modern x86 server, running a JSON-shaped transform (map/filter/reduce over 10,000 objects):

| Metric | isolated-vm | quickjs-emscripten |
|---|---|---|
| Cold start (new isolate/context) | 8–15 ms | 25–60 ms (WASM instantiate) |
| Warm execution, transform | 3–6 ms | 45–90 ms |
| Memory per concurrent sandbox | 30–60 MB | 4–12 MB |
| Timeout stops infinite loop | Yes (isolate terminate) | Yes (interrupt handler) |
| Cross-boundary data cost | Structured copy | Handle copy, manual dispose |

The practical read: isolated-vm wins on throughput and loses on density; quickjs-emscripten wins on density and portability and loses on CPU time per call. If you run thousands of tiny user snippets per minute, QuickJS contexts are cheaper to keep around. If each snippet crunches real data, the JIT gap dominates everything else.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Running Untrusted JavaScript in Node.js in 2026: isolated-vm vs quickjs-emscripten vs vm2",
  "description": "A practical comparison of isolated-vm, quickjs-emscripten and the discontinued vm2 for executing untrusted JavaScript in Node.js, with production code, Docker builds, benchmarks and hardening guidance.",
  "datePublished": "2026-11-05",
  "dateModified": "2026-11-05",
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

### Is vm2 really unusable in 2026?

Yes for untrusted input. The project is discontinued, its README states it contains critical security issues and should not be used in production, and the escape class comes from sharing a realm with host code rather than from a single unpatched bug. Pinning a version does not help — there is no fixed version coming.

### Which is faster, isolated-vm or quickjs-emscripten?

isolated-vm, usually by 10–20x on CPU-bound code, because it runs on V8 with a JIT while QuickJS is an interpreter compiled to WebAssembly. The gap narrows for tiny snippets where startup dominates, and reverses for density: a QuickJS context costs a few megabytes, an isolate costs tens.

### Can tenant code read files or make network requests inside these sandboxes?

Not unless you wire it in. isolated-vm's isolates have no Node builtins and only see the host functions you explicitly expose as `Reference` objects; quickjs-emscripten contexts have no Node builtins at all. Both default to a pure ECMAScript environment, which is the behavior you want.

### How do I stop an infinite loop?

isolated-vm accepts a `timeout` option on script execution and terminates the isolate when it expires. quickjs-emscripten uses `setInterruptHandler`, which fires inside long-running loops — return `true` to abort. Neither is cooperative with tenant code, so both work against `while(true){}`.

### Do I still need a container if I use isolated-vm?

Yes if the code is truly adversarial. In-process isolation protects your heap and your event loop, but an engine-level memory corruption bug crosses it. A per-tenant container with seccomp, a read-only filesystem, and no network is the belt to the library's suspenders.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
