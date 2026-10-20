---
title: "Module Federation vs single-spa vs qiankun in 2026: Which Micro-Frontend Architecture Survives Production?"
date: "2026-10-21"
tags: ["javascript", "frontend", "micro-frontends", "developer-tools", "architecture"]
draft: false
description: "A production-focused comparison of Module Federation 2.9.2, single-spa 6.0.3 and qiankun 2.10.16 — runtime sharing, isolation limits, routing traps and the failure modes each one hides."
---

The pitch for micro-frontends is always the same: forty engineers, one React app, six teams blocked on the same release train. Split the frontend, let each team deploy independently, ship faster. Then eighteen months later the shell takes nine seconds to load, two copies of React are running, a CSS reset from the checkout app is repainting the navbar, and nobody can explain why the payment button works in staging but not in production.

Micro-frontends do not fail because the idea is wrong. They fail because the three mainstream architectures — **Module Federation**, **single-spa** and **qiankun** — solve different problems and hide different costs. In 2026 the current releases are Module Federation **2.9.2** (`@module-federation/enhanced`), single-spa **6.0.3** and qiankun **2.10.16**. All three are MIT-licensed. Only one of them still sees regular commits.

## TL;DR — The 30-Second Verdict

**Choose Module Federation** if your micro-frontends share a framework and you want runtime code sharing without an extra runtime layer. It is the only one of the three where a shared `react` dependency is a first-class concept rather than a documented workaround. Best build-tool coverage (webpack, Rspack, Vite), fastest-moving project, and the only one with a credible server-side rendering story.

**Choose single-spa** if you need framework-agnostic composition — React next to Vue next to Angular next to a legacy jQuery page — and you are willing to own a SystemJS import map. It is the smallest abstraction of the three and the easiest to reason about, but its release cadence has slowed noticeably.

**Choose qiankun** if your teams are on Chinese enterprise stacks, need HTML-entry onboarding (point at a URL, no build changes), and want a JS sandbox plus style isolation out of the box. It is the most batteries-included option and the most opinionated about how apps must behave.

**Avoid all three if** you have fewer than roughly four teams or fewer than three independently deployed apps. A monorepo with good CI beats a distributed system you now have to operate.

## Side-by-Side Comparison

Live data from GitHub and npm on 2026-10-21:

| Dimension | Module Federation | single-spa | qiankun |
|---|---|---|---|
| Package | `@module-federation/enhanced` | `single-spa` | `qiankun` |
| Version | 2.9.2 | 6.0.3 | 2.10.16 |
| GitHub stars | 2,663 | 13,877 | 16,697 |
| Last commit | 2026-10-20 | 2026-02-28 | 2026-10-11 |
| License | MIT | MIT | MIT |
| Composition model | Shared modules at runtime | Route-based app lifecycle | Route-based app lifecycle (HTML entry) |
| Framework agnostic | Mostly (framework-agnostic core) | Fully | Mostly (best with React/Vue) |
| Shared dependency handling | Built in (`shared`, singletons) | Manual via import maps | Manual via externals / shared vendor |
| JS isolation | None (same realm) | None (same realm) | Proxy sandbox |
| CSS isolation | None | None | Scoped + experimental strict mode |
| Routing | Your app's router | `activeWhen` predicates | `activeRule` |
| Onboarding cost | Build config change per app | Import map + lifecycle exports | A URL is enough |
| Vite support | Yes (`@module-federation/vite`) | Yes (via plugin) | Community plugins only |
| Server-side rendering | Yes, with work | No | No |
| Type sharing across remotes | Yes (dts plugin) | No | No |
| Operational complexity | Medium | Medium–high | High |

## Decision Matrix

| Your situation | Use this | Why |
|---|---|---|
| All apps are React 18+, want shared vendor chunks | Module Federation | `shared: { react: { singleton: true } }` is the whole answer |
| Mixing React, Vue and a legacy AngularJS page | single-spa | Lifecycle contract is framework-neutral by design |
| Teams cannot change their build config | qiankun | HTML entry loads an existing deployed URL |
| Need SSR for the shell | Module Federation | Only option with a supported path |
| Legacy app pollutes `window` and global CSS | qiankun | Sandbox plus style isolation, imperfect but real |
| Two teams, one product, shared design system | none of them | Monorepo + package boundaries |
| Strict CSP with no `unsafe-eval` | Module Federation | SystemJS import maps in single-spa often need looser CSP |

## Module Federation 2.9.2 — Runtime Sharing Done Properly

Module Federation's core idea is that a remote application exposes modules, and the host loads them at runtime while both sides share dependencies. In v2 the runtime is decoupled from webpack: you get first-class Rspack support and an official Vite plugin, and remotes are described by a generated `mf-manifest.json` rather than a hand-wired `remoteEntry.js`.

A remote exposes a widget:

```js
// checkout/webpack.config.js
const { ModuleFederationPlugin } = require('@module-federation/enhanced/webpack');

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'checkout',
      filename: 'remoteEntry.js',
      exposes: {
        './CartWidget': './src/CartWidget',
      },
      shared: {
        react: { singleton: true, requiredVersion: '^18.3.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.3.0' },
      },
    }),
  ],
};
```

The host consumes it — declaratively at build time, or dynamically at runtime:

```js
import { init, loadRemote } from '@module-federation/enhanced/runtime';

init({
  name: 'shell',
  remotes: [
    { name: 'checkout', entry: 'https://checkout.example.com/mf-manifest.json' },
  ],
  shared: {
    react: { version: '18.3.1', lib: () => React, shareConfig: { singleton: true } },
  },
});

const { default: CartWidget } = await loadRemote('checkout/CartWidget');
```

That runtime API is the reason to prefer v2 over the classic webpack plugin: the shell can register remotes after boot, which means the list of micro-frontends can come from your service discovery or feature-flag service instead of a compiled constant.

For Vite, the official plugin follows the same manifest contract:

```js
// vite.config.js
import { defineConfig } from 'vite';
import { federation } from '@module-federation/vite';

export default defineConfig({
  plugins: [
    federation({
      name: 'checkout',
      filename: 'remoteEntry.js',
      exposes: { './CartWidget': './src/CartWidget' },
      shared: ['react', 'react-dom'],
    }),
  ],
});
```

**The honest limits.** Module Federation shares a JavaScript realm: one `window`, one `document`, one global CSS scope. It does not isolate anything. Two micro-frontends with conflicting `:root` variables or a stray `body { overflow: hidden }` will fight, and the winner depends on load order. It also makes dependency management a runtime concern — a singleton enforced across apps means one team's React 17 pin can force another team's 18-only feature to fail at runtime, not at build time. And TypeScript types do not cross the boundary unless you enable the dts plugin, so a remote API change silently becomes `any`.

## single-spa 6.0.3 — The Minimal Contract

single-spa does one thing: it watches the URL and mounts or unmounts applications that export three lifecycle functions. Everything else — bundling, module loading, sharing — is yours to decide.

```js
// root-config/src/root-config.js
import { registerApplication, start } from 'single-spa';

registerApplication({
  name: '@acme/navbar',
  app: () => System.import('@acme/navbar'),
  activeWhen: ['/'],
});

registerApplication({
  name: '@acme/checkout',
  app: () => System.import('@acme/checkout'),
  activeWhen: (location) => location.pathname.startsWith('/checkout'),
});

start({ urlRerouteOnly: true });
```

Each micro-frontend exports the contract:

```js
// checkout/src/acme-checkout.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

let root;

export async function bootstrap() {
  console.log('checkout bootstrapped');
}

export async function mount(props) {
  root = ReactDOM.createRoot(props.domElement);
  root.render(<App />);
}

export async function unmount() {
  root.unmount();
  root = null;
}
```

Modules are resolved through an import map served with the shell:

```html
<script type="importmap">
{
  "imports": {
    "@acme/navbar": "https://cdn.example.com/navbar/6.4.2/acme-navbar.js",
    "@acme/checkout": "https://cdn.example.com/checkout/2.1.0/acme-checkout.js",
    "react": "https://cdn.example.com/vendor/react@18.3.1.js",
    "react-dom/client": "https://cdn.example.com/vendor/react-dom@18.3.1-client.js"
  }
}
</script>
<script src="https://cdn.jsdelivr.net/npm/systemjs@6/dist/system.min.js"></script>
```

This explicitness is single-spa's strength. You can see every version in one file, and rollback is a one-line import map change. It is also its weakness: that file becomes a deployment bottleneck, nobody remembers to bump hashes, and stale micro-frontends get served from CDN caches for hours because the URL did not change. Pair it with a cache-busting strategy or you will ship a fix that never reaches users.

Two more caveats. First, `activeWhen` predicates drive everything — overlapping predicates mount multiple apps into the same DOM and the result looks like a CSS argument, not a routing bug. Second, the project's release cadence has slowed: last commit was 2026-02-28, roughly eight months before this article, while qiankun and Module Federation both shipped within days. Slow cadence is not abandonment, but it does mean you should expect to debug edge cases yourself.

## qiankun 2.10.16 — HTML Entry, Sandbox Included

qiankun (built on top of single-spa) flips the onboarding model: instead of exporting lifecycle functions from a bundle you control, you point it at a deployed URL and it fetches the HTML, extracts scripts and styles, and mounts the result into a container.

```js
// shell/src/index.js
import { registerMicroApps, start, initGlobalState } from 'qiankun';

const actions = initGlobalState({ user: null, locale: 'en' });

registerMicroApps(
  [
    {
      name: 'react-checkout',
      entry: '//checkout.example.com',
      container: '#subapp-viewport',
      activeRule: '/checkout',
      props: { actions },
    },
    {
      name: 'vue-reports',
      entry: '//reports.example.com',
      container: '#subapp-viewport',
      activeRule: '/reports',
    },
  ],
  {
    beforeLoad: [(app) => console.log('loading', app.name)],
    afterUnmount: [(app) => console.log('unmounted', app.name)],
  }
);

start({
  sandbox: { experimentalStyleIsolation: true },
  prefetch: 'all',
  singular: false,
});
```

Manual mounting is available for widgets that are not route-driven:

```js
import { loadMicroApp } from 'qiankun';

const app = loadMicroApp({
  name: 'price-widget',
  entry: '//pricing.example.com',
  container: '#price-widget',
});

// later
await app.unmount();
```

Isolation is the differentiator. The default sandbox proxies `window` per application so globals written by one app do not leak into another, and `experimentalStyleIsolation` rewrites CSS selectors with a container prefix. Both are best-effort. The proxy sandbox cannot intercept globals captured at script-evaluation time by libraries that stash references, and it does not stop `document.write`. Style isolation mangles `body` and `html` selectors and breaks component libraries that portal modals into `document.body` — the classic symptom is an Ant Design dialog rendering unstyled and unclickable. `strictStyleIsolation` uses Shadow DOM and fixes leakage more thoroughly, at the cost of breaking any library that relies on document-level styles.

Communication goes through `initGlobalState`, which returns `onGlobalStateChange` and `setGlobalState`. It is a global observable, which means every app can read and overwrite everything. Convenient, and a reliable way to build a distributed monolith with extra steps.

qiankun is also the least Vite-friendly of the three: official support targets webpack, and Vite setups depend on community plugins with varying health. If your teams are standardized on Vite, Module Federation will cost you less.

## Pitfalls That Will Bite You

**1. Two copies of React produce "Invalid hook call".** This is the single most common micro-frontend bug. The message points at hooks; the cause is a duplicated runtime. Fix it at the dependency level — singleton sharing in Module Federation, a single import-map entry in single-spa, `externals` in qiankun — not by patching the component.

**2. CSS is global unless you make it not global.** Only qiankun attempts isolation, and its isolation is partial. The durable fix is architectural: CSS modules or scoped layers for every micro-frontend, no global resets, and design tokens delivered as custom properties on a container rather than on `:root`.

**3. Routing ownership is ambiguous by default.** Decide up front whether the shell owns history and passes a base path to each app, or each app owns its own router. Mixing the two produces URLs that work on refresh but break on in-app navigation.

**4. Version skew fails at runtime, not build time.** A singleton dependency means the first-loaded version wins. Enable strict version checks in staging (`strictVersion` in Module Federation) so mismatch becomes a loud error instead of a mysterious `undefined is not a function`.

**5. Server-side rendering is still hard.** Module Federation supports SSR, but the shell and remotes must hydrate in a coordinated order and shared singletons must be resolved per request, not per process. qiankun and single-spa are client-only; do not promise SSR on top of them.

**6. Observability multiplies.** Each micro-frontend tends to initialize its own error tracker, its own tracing headers and its own session identifiers. Centralize error boundaries in the shell and propagate a correlation ID through props or global state, or your incident response becomes a cross-team scavenger hunt.

**7. Autonomy is a governance claim, not an architecture property.** Micro-frontends let teams deploy independently, but a shared design system, shared auth and a shared shell are still shared code. Teams that skip the governance layer get independent deploys and a broken product.

## FAQ

### Which micro-frontend approach is fastest at runtime?

Module Federation, in most production setups, because shared dependencies are loaded once and remotes are plain ES modules or script chunks. qiankun adds an HTML-fetch-and-parse step plus sandbox setup per activation, which typically costs tens of milliseconds on first mount. single-spa sits between the two depending on your import-map granularity.

### Can I mix Module Federation and single-spa?

Yes, and some large organizations do: single-spa as the top-level router, with individual applications composed internally via Module Federation. The cost is two mental models and two failure surfaces. Only do this if a genuine framework-mixing requirement exists.

### Is qiankun still maintained in 2026?

Yes — release 2.10.16 and commits in October 2026. Note that qiankun 3 is developed in a separate repository, so if you are starting fresh, check the v3 line before committing to the 2.x API surface described here.

### Do micro-frontends hurt Core Web Vitals?

They can, significantly. Each remote adds a network round trip and its own JavaScript payload, and shared-dependency mistakes duplicate framework code. The mitigation is prefetching, aggressive chunk splitting and a strict performance budget per micro-frontend, enforced in CI rather than in review comments.

### How do micro-frontends handle authentication?

Keep auth in the shell. The shell performs the login flow, holds the token, and passes a minimal session object to remotes through props or global state. If each micro-frontend runs its own auth flow, expect divergent token refresh logic and users logged out of one area but not another.

### What is the realistic minimum team size for this architecture?

Around three independently deploying teams with a genuine coupling problem. Below that, a monorepo with package boundaries and a shared CI pipeline gives you most of the deployment independence with none of the distributed-system overhead.

## Related Reading

If you are choosing the build layer underneath these architectures, our [JavaScript bundler comparison](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/) covers Rspack, Vite and the rest. For component-level interoperability instead of application-level composition, see [web components: Lit vs FAST vs Stencil](../2026-10-17-web-components-lit-fast-stencil-comparison/). And since shared state is where most micro-frontend designs go wrong, the [JavaScript state management guide](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/) is worth reading before you decide that global state is the integration layer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Module Federation vs single-spa vs qiankun in 2026: Which Micro-Frontend Architecture Survives Production?",
  "description": "Production-focused comparison of Module Federation 2.9.2, single-spa 6.0.3 and qiankun 2.10.16 covering runtime sharing, isolation limits, routing and observability traps.",
  "datePublished": "2026-10-21",
  "dateModified": "2026-10-21",
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
