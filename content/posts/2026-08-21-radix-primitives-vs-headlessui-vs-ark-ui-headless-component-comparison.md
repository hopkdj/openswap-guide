---
title: "Radix Primitives vs Headless UI vs Ark UI in 2026: Which Headless Component Library Wins?"
date: "2026-08-21"
tags: ["react", "frontend", "ui-components", "accessibility", "javascript"]
draft: false
cover: "/img/screenshots/radix-cover.jpg"
---

Your design team just handed you a beautiful, custom component spec — rounded tabs, an animated dialog with a focus trap, a combobox that's actually usable on a phone. You reach for your component library of record and hit a wall: it's styled, opinionated, and fights your design system every time you try to deviate. That's the moment teams discover **headless component libraries** — UI primitives that ship behavior and accessibility but zero styling, so your CSS (and only your CSS) decides how they look. In 2026 the three names that matter are **Radix Primitives**, **Headless UI**, and **Ark UI**, and they are not the same thing — one is built for maximal control, one for Tailwind velocity, and one is a state-machine-powered multi-framework bet.

This guide compares all three with live GitHub data, real code, and the migration traps nobody warns you about.

## TL;DR — Quick Verdict

If you're building a serious design system or shadcn-style component set, **Radix Primitives** is the safe default — the largest component catalog, the most granular control, and the ecosystem gravity (shadcn/ui is built on it). If you're a **Tailwind-first** shop that wants accessible components without fighting APIs, **Headless UI** is the fastest path and the most opinionated in the good ways. If you ship the same app in **React, Vue, and Solid**, **Ark UI** is the only one of the three with identical APIs across frameworks, powered by Zag.js state machines. Pick based on your styling approach and framework count — not on star count alone.

## Headless Component Libraries at a Glance

| Feature | Radix Primitives | Headless UI | Ark UI |
|---|---|---|---|
| **GitHub repo** | radix-ui/primitives | tailwindlabs/headlessui | chakra-ui/ark |
| **Stars (Aug 2026)** | 19,193 | 28,714 | 5,350 |
| **Last push (Aug 2026)** | 2026-08-08 | 2026-04-13 | 2026-08-20 |
| **Frameworks** | React | React, Vue | React, Vue, Solid, Svelte |
| **Styling** | Fully unstyled | Fully unstyled (data attributes) | Fully unstyled |
| **Component count** | ~60+ (per-package) | ~10 core components | ~40+ components |
| **Architecture** | Composition + controlled state | Hooks + render props | Zag.js state machines |
| **License** | MIT (WorkOS) | MIT | MIT |
| **Notable users** | shadcn/ui, Vercel, Linear | Tailwind ecosystem | Chakra UI v3 |
| **Best for** | Design systems, max control | Tailwind-first teams | Multi-framework orgs |

## Decision Matrix: Which Headless Library for Your Team?

| Use Case | Recommendation | Why |
|---|---|---|
| Building a design system from scratch | **Radix Primitives** | Granular, composable primitives with full state control; the de-facto base for copy-paste component ecosystems |
| Tailwind shop, want speed over control | **Headless UI** | Data-attribute styling model fits Tailwind perfectly; minimal API; Transition component built in |
| Same product in React + Vue + Solid + Svelte | **Ark UI** | One identical API across four frameworks via Zag.js state machines — write once, run everywhere |
| Need a specific exotic component (tree, splitter, file upload) | **Ark UI** | Ships components Radix and Headless UI don't offer, like Splitter and FileUpload |
| Accessibility as a hard compliance requirement | **Any of the three** | All three are WCAG-focused and tested with assistive tech; Radix and Ark are explicit about it, Headless UI inherits Tailwind Labs' care |
| You already use shadcn/ui | **Radix Primitives** | shadcn/ui components are Radix under the hood — extending them means staying in the same family |

## Radix Primitives — The Design-System Standard

Radix Primitives is a low-level React component library maintained by WorkOS, focused on accessibility, customization, and developer experience. Its defining architectural decision is **one npm package per component** — you install only what you use, so a dialog costs you `@radix-ui/react-dialog` plus its tiny dependency tree, not a 100 MB monolith. Every component supports controlled and uncontrolled state, composes through a namespaced API, and exposes a `Slot` pattern that lets you render your own DOM elements while inheriting behavior.

```bash
npm install @radix-ui/react-dialog
```

```tsx
import * as Dialog from '@radix-ui/react-dialog';

function ConfirmDialog() {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button className="btn">Delete project</button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
          <Dialog.Title>Delete this project?</Dialog.Title>
          <Dialog.Description>
            This action cannot be undone. All data will be lost.
          </Dialog.Description>
          <Dialog.Close>Cancel</Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

The `asChild` prop (built on the `Slot` primitive) is the key to Radix's styling freedom: instead of a styled `<button>`, Radix renders *your* button and attaches the behavior. Focus management, escape-key dismissal, scroll locking, and the ARIA wiring all come for free — the markup is yours. With 60+ primitives including Accordion, Combobox, Context Menu, Tooltip, Tabs, and Toast, it covers essentially every interaction pattern a product needs. The ecosystem gravity is the real moat: **shadcn/ui — the most-starred component project of 2026 — is Radix underneath**, so thousands of copy-paste components, themes, and tutorials all assume Radix APIs.

## Headless UI — Tailwind's Answer to Accessible Components

Headless UI is Tailwind Labs' unstyled component library for React and Vue, designed to "integrate beautifully with Tailwind CSS." Its philosophy is minimalism: about ten core components (Menu, Listbox, Combobox, Dialog, Popover, Tabs, Transition, Disclosure, Switch, Radio Group), each with a small, memorizable API. Instead of a `Slot` system, it exposes **data attributes** (`data-open`, `data-focus`, `data-selected`) so you style state changes directly in Tailwind.

```bash
npm install @headlessui/react@latest
```

```tsx
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/react';

function AccountMenu() {
  return (
    <Menu>
      <MenuButton className="rounded-md bg-slate-900 px-4 py-2 text-white">
        Account
      </MenuButton>
      <MenuItems className="mt-2 w-48 rounded-lg bg-white p-1 shadow-lg">
        <MenuItem>
          <a className="block px-3 py-2 data-[focus]:bg-slate-100" href="/profile">
            Profile
          </a>
        </MenuItem>
        <MenuItem>
          <a className="block px-3 py-2 data-[focus]:bg-slate-100" href="/settings">
            Settings
          </a>
        </MenuItem>
        <MenuItem>
          <a className="block px-3 py-2 data-[focus]:bg-slate-100" href="/logout">
            Sign out
          </a>
        </MenuItem>
      </MenuItems>
    </Menu>
  );
}
```

The standout is the **Transition** component — a dedicated wrapper for enter/leave animations that coordinates with Tailwind's `transition-*` utilities and removes the most annoying part of building accessible menus and dialogs. Headless UI is deliberately less granular than Radix: you get a well-trodden set of behaviors, not a toolkit for inventing your own. That trade-off is exactly right for product teams that want consistency and speed. One honest caveat: the docs and examples are Tailwind-centric, and while the components work with any CSS, the ergonomics are clearly designed around Tailwind's data-attribute utilities.

## Ark UI — State Machines for Every Framework

Ark UI comes from the Chakra UI team (whose v3 was rebuilt on top of it) and is the most architecturally interesting of the three. Every component's behavior — open/close, selection, focus, keyboard handling — is modeled as a **finite state machine in Zag.js**, a framework-agnostic state-machine library. The React, Vue, Solid, and Svelte packages are thin renderers over the same logic, which means **the API is identical across all four frameworks**: a component you build in React port to Vue by changing the import.

```bash
npm install @ark-ui/react
```

```tsx
import { Dialog } from '@ark-ui/react';

function ConfirmDialog() {
  return (
    <Dialog.Root>
      <Dialog.Trigger>Delete project</Dialog.Trigger>
      <Dialog.Backdrop className="fixed inset-0 bg-black/40" />
      <Dialog.Content className="rounded-lg bg-white p-6 shadow-xl">
        <Dialog.Title>Delete this project?</Dialog.Title>
        <Dialog.Description>This action cannot be undone.</Dialog.Description>
        <Dialog.CloseTrigger>Cancel</Dialog.CloseTrigger>
      </Dialog.Content>
    </Dialog.Root>
  );
}
```

Because behavior lives in state machines, edge cases that plague hand-rolled components (rapid open/close, focus restore after unmount, interruption mid-transition) are handled by construction — the machine always knows what state it's in. Ark also ships components the other two lack: **Splitter** (resizable panels), **FileUpload**, **ColorPicker**, **TreeView**, and **SignaturePad**. The trade-off is maturity: at 5,350 stars with a fast release cadence, Ark moves quickly and its young ecosystem means fewer third-party examples and more breaking changes than Radix. For organizations that ship the same product across React, Vue, Solid, and Svelte, that API parity is worth more than any star count.

## Common Pitfalls and How to Avoid Them

**1. "Headless" still means you style everything.** Portals, z-index, focus rings, overlay backdrops — all of it is your CSS. Teams new to headless libraries routinely ship dialogs that render behind the page (missing z-index on portal content) or buttons with no focus-visible ring (accessibility regression nobody catches in review). Budget real time for styling state, not just the resting state.

**2. Portals create stacking-context surprises.** Radix portals content to `document.body`; Headless UI and Ark do similar. CSS `transform`, `filter`, or `will-change` on an ancestor creates a new stacking context that can trap the portal behind it. The fix is a consistent z-index scale for overlay layers, applied inside the portal, not on the trigger.

**3. Radix's per-package versioning means lockfile churn.** Each of the 60+ packages versions independently, so `npm update` touches many transitive deps and a single breaking change can ripple across components. Upgrade component-by-component with a test suite that exercises the interactions, not bulk `npm update`.

**4. Don't mix two headless libraries in one app.** Duplicated portal management, competing focus traps, and two versions of scroll-lock will fight each other. Pick one family per product and migrate wholesale.

**5. Server components and state machines don't mix by default.** Ark's behavior lives in client-side state machines, and Radix/Headless UI components that track state also need client components in React Server Component architectures. Plan your `'use client'` boundaries before adopting — your whole dialog tree may need to be client-side.

**6. Accessibility is default-on, not free.** All three ship ARIA-correct markup and focus handling, but you still own labels, keyboard affordances, and interaction tests. A dialog with no `Dialog.Title` (Radix warns about it) fails screen-reader semantics even though the primitive is "accessible."

**7. Young-library breaking changes.** Ark UI's fast cadence is a feature and a hazard: pin versions, read the changelog, and keep an upgrade test for every state-machine-driven component.

## Choosing by Ecosystem, Not Just Stars

The star counts tell a story — Headless UI's 28.7k reflects Tailwind's enormous reach; Radix's 19.2k reflects design-system builders; Ark's 5.4k reflects its youth — but the decision matrix above is what actually matters. **Radix** wins when you're building the foundation of a design system or extending a shadcn/ui-style component set. **Headless UI** wins when you live in Tailwind and want maximum velocity on standard components. **Ark UI** wins when framework parity is a hard requirement. All three pair naturally with the styling approaches we've compared elsewhere on this site: your [Tailwind vs UnoCSS vs Open Props choice](../2026-08-10-tailwind-vs-unocss-vs-open-props-css-frameworks-guide/) determines how Headless UI's data attributes feel, and [CSS-in-JS libraries](../2026-08-15-css-in-js-styled-components-emotion-linaria-comparison/) give Radix and Ark their styling layer. If you came from the styled-library world, our [shadcn/ui vs Mantine vs Chakra comparison](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/) shows exactly where headless primitives fit — and for Vue teams, the [Vuetify vs Element Plus vs Naive UI guide](../2026-08-19-vuetify-vs-element-plus-vs-naive-ui-vue-component-libraries-comparison/) is the styled counterpart to Ark's Vue bindings.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Radix Primitives vs Headless UI vs Ark UI in 2026: Which Headless Component Library Wins?",
  "description": "Deep comparison of Radix Primitives, Headless UI, and Ark UI with live GitHub stats, real code examples, and migration pitfalls for headless React, Vue, Solid, and Svelte components.",
  "datePublished": "2026-08-21",
  "dateModified": "2026-08-21",
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

### What does "headless" mean in a component library?

A headless component library ships behavior, accessibility, and state management without any visual styling. You bring your own CSS — Tailwind, CSS-in-JS, plain CSS, or a design system. Radix Primitives, Headless UI, and Ark UI are all headless; libraries like Mantine or Vuetify are styled alternatives that render their own look out of the box.

### Is Headless UI only usable with Tailwind CSS?

No. The components are framework-agnostic regarding styling and work with plain CSS or any CSS framework. However, the styling model is built around data attributes (`data-open`, `data-focus`, `data-selected`) that map directly to Tailwind utilities, so the documentation and examples are Tailwind-centric. Teams not using Tailwind often find Radix or Ark ergonomics more neutral.

### Which headless library should I use with shadcn/ui?

shadcn/ui is built on Radix Primitives — its dialogs, dropdowns, and popovers are Radix components with Tailwind styling. If you use shadcn/ui, staying in the Radix family makes extensions and customization natural. Mixing in Headless UI or Ark components inside a shadcn app creates the two-library conflict that causes portal and focus-trap bugs.

### Does Ark UI really support React, Vue, Solid, and Svelte with one API?

Yes. Ark UI's behavior layer is implemented as Zag.js state machines that are framework-agnostic, and the React, Vue, Solid, and Svelte packages are thin bindings over the same machines. The component API (namespaced, e.g. `Dialog.Root`, `Dialog.Content`) is identical across frameworks, which makes porting a component mostly a matter of changing the import path.

### Which library is best for accessibility?

All three take accessibility seriously: Radix and Ark explicitly target WCAG compliance and test with assistive technologies, and Headless UI inherits Tailwind Labs' quality bar. Radix has the most mature track record for complex patterns like dialogs, comboboxes, and context menus. Regardless of choice, you still own labels, focus-visible styles, and interaction testing.

### Do these libraries work with React Server Components?

Partially. Stateful components (dialogs, menus, comboboxes) need to run in client components in Next.js-style RSC architectures. Radix and Headless UI have documented SSR stories, and Ark's state-machine logic is inherently client-side. Plan `'use client'` boundaries when you adopt any of them.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
