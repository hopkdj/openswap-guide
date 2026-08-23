---
title: "react-select vs Downshift vs React Aria in 2026: Which React Select Library Should You Use?"
date: "2026-08-24"
tags: ["react", "javascript", "components", "accessibility", "npm-libraries"]
draft: false
cover: "/img/screenshots/react-select-cover.jpg"
---

The native `<select>` element is the most stubbornly bad control in HTML: you cannot style the dropdown, keyboard navigation is inconsistent across browsers, search is non-existent, and multi-select with tags is simply not possible. So every React team eventually reaches for a select/combobox library — and then discovers that react-select, Downshift, and React Aria approach the problem from three completely different philosophies. Pick the wrong one and you either inherit 100 KB of unstoppable styling you cannot override, or you spend a week wiring up ARIA attributes by hand.

**react-select** (28,037 stars) is the batteries-included component: styled, searchable, creatable, virtualized, and drop-in in ten minutes. **Downshift** (12,309 stars) is a headless primitive that gives you the keyboard handling and WAI-ARIA combobox logic with zero styling — you own the entire look. **React Aria** (15,815 stars in the Adobe React Spectrum monorepo) is Adobe's accessibility-first hook library that provides the behavior layer for select and dozens of other components, designed to sit under your design system.

## TL;DR: Quick Verdict

**If you need a working select today and don't care about pixel-perfect branding, use react-select** — it is the fastest path from zero to shipped, with async loading, creatable options, and virtualization built in. **If you have a design system or a custom UI and you want a library that stays out of your stylesheet, use Downshift** — it is the React-idiomatic headless approach and the natural upgrade path from react-select's styling fights. **If you are building a component library or your product has serious accessibility requirements, use React Aria** — it implements the ARIA 1.2 combobox pattern with state management you would otherwise have to write and verify yourself.

## Feature Comparison: react-select vs Downshift vs React Aria

| Capability | react-select | Downshift | React Aria |
|---|---|---|---|
| Philosophy | Styled component | Headless primitives | Unstyled hooks |
| Ships CSS/styling | ✅ (emotion-based) | ❌ (bring your own) | ❌ (bring your own) |
| Keyboard navigation | ✅ built-in | ✅ via hooks | ✅ via hooks |
| WAI-ARIA combobox pattern | ✅ | ✅ (ARIA 1.2 in v7+) | ✅ (ARIA 1.2) |
| Async option loading | ✅ | ❌ (you build it) | ❌ (you build it) |
| Creatable options | ✅ (CreatableSelect) | ⚠️ via state | ⚠️ via state |
| Multi-select with tags | ✅ | ⚠️ via `useMultipleSelection` | ⚠️ via state |
| Option virtualization | ✅ (react-window based) | ❌ | ❌ |
| Custom components API | ✅ (Component Injection) | Render props / hooks | Hooks only |
| SSR support | ✅ | ✅ | ✅ |
| License | MIT | MIT | Apache-2.0 |
| GitHub stars | 28,037 | 12,309 | 15,815 (monorepo) |
| Last push | 2026-07-16 | 2026-06-30 | 2026-08-21 |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Internal admin tool, ship it this sprint | **react-select** | Zero styling work, sensible defaults, async + creatable out of the box |
| Customer-facing UI with brand design | **Downshift** | Headless means your CSS is the only CSS; no override battles |
| Building a reusable component library | **React Aria** | Hooks compose with your own markup; the a11y contract is already solved |
| Compliance-sensitive product (WCAG audits) | **React Aria** | Adobe's implementation is the reference for the ARIA 1.2 combobox pattern |
| Tag multi-select with custom chips | **Downshift** + `useMultipleSelection` | The primitives compose without fighting a monolithic API |
| Country/city picker with search over 10k options | **react-select** with virtualization | Built-in; Downshift/React Aria would need a virtual list library on top |
| Teams already on a component library (Mantine, Chakra) | **Use the library's own select** | Wrapping a second select framework inside a component library duplicates state and a11y work |

## react-select — The Batteries-Included Select

react-select is the default answer for a reason: it is the most complete select component in the ecosystem, funded by Thinkmill and Atlassian and used across the npm ecosystem. The getting-started path is genuinely two steps:

```bash
yarn add react-select
```

```jsx
import React, { useState } from 'react';
import Select from 'react-select';

const options = [
  { value: 'chocolate', label: 'Chocolate' },
  { value: 'strawberry', label: 'Strawberry' },
  { value: 'vanilla', label: 'Vanilla' },
];

export default function App() {
  const [selectedOption, setSelectedOption] = useState(null);

  return (
    <div className="App">
      <Select
        defaultValue={selectedOption}
        onChange={setSelectedOption}
        options={options}
      />
    </div>
  );
}
```

That is the entire API for the 80% case. The remaining 20% is where react-select's power lives: `AsyncSelect` for promise-based option loading, `CreatableSelect` for user-entered options, `isMulti` for tag-style multi-select, and `components` prop for surgically replacing individual pieces (the menu, the option row, the clear indicator) with your own React components. Styling is handled through the `styles` prop — a function-based API where every sub-component (control, menu, option, indicator) receives state (`isFocused`, `isSelected`, `isDisabled`) and returns a style object.

The trade-offs are real. react-select pulls in **emotion** for its default styling, which adds roughly 100 KB to your bundle if you are not already using it. And its styling API, while powerful, is the #1 source of developer frustration: deep overrides require understanding its component model, and aggressive custom themes often end up fighting the library's defaults. It also reimplements rather than composes — if you need a virtualized list, a custom portal target, or a radically different interaction, you are extending react-select rather than building with primitives.

## Downshift — Headless Select, Your Styles

Downshift, created by Kent C. Dodds and now maintained by the Downshift team, takes the opposite position: the library owns *behavior only*. It gives you the state machine, the keyboard interactions, the ARIA wiring, and the event handlers — and returns props you spread onto your own elements. You write every class, every transition, every pixel.

The modern API is hooks. `useSelect` implements a single-select dropdown; `useCombobox` implements the combobox/autocomplete pattern; `useMultipleSelection` handles tag-style multi-select:

```jsx
import { useSelect } from 'downshift';

const items = ['Red', 'Orange', 'Green'];

function Select() {
  const {
    isOpen,
    selectedItem,
    getToggleButtonProps,
    getMenuProps,
    getItemProps,
  } = useSelect({ items });

  return (
    <div>
      <button type="button" {...getToggleButtonProps()}>
        {selectedItem ?? 'Select a color'}
      </button>
      <ul {...getMenuProps()}>
        {isOpen &&
          items.map((item, index) => (
            <li key={item} {...getItemProps({ item, index })}>
              {item}
            </li>
          ))}
      </ul>
    </div>
  );
}
```

Note what is and is not there: the button, the list, the conditional rendering — all yours. The hook supplies `getToggleButtonProps`, `getMenuProps`, and `getItemProps`, which inject the `role`, `aria-expanded`, `aria-activedescendant`, `id`, and keyboard handlers that make the plain markup behave like a proper combobox. Version 7 migrated the hooks to the **ARIA 1.2 combobox pattern** — a deliberate correctness fix, since ARIA 1.1's combobox role had genuine browser inconsistencies — and the README is explicit that the hooks are the recommended API over the original render-prop `Downshift` component.

Downshift's cost is visible the moment your select needs anything beyond the basics. Async loading, creatable options, and virtualization are all *you*: you orchestrate fetch state, you manage the options array, you compose `useCombobox` with a virtual list. For a one-off admin dropdown that is overkill; for a design system it is exactly the freedom you want.

## React Aria — Accessibility as the API

React Aria is Adobe's collection of unstyled React hooks and components, part of the React Spectrum monorepo (15,815 stars). It is the reference implementation of accessible behavior: `useSelect` provides the combobox logic, `useListBox`/`useOption` the list semantics, `useButton` the press handling — all based on the ARIA 1.2 pattern and tested across browsers and assistive technologies as part of Adobe's accessibility program.

```jsx
import { useSelect } from '@react-aria/select';
import { useSelectState } from '@react-stately/select';
import { useButton } from '@react-aria/button';
import { useRef } from 'react';

function Select({ label, children, items }) {
  const state = useSelectState({ label, items, children });
  const ref = useRef(null);
  const { triggerProps, menuProps } = useSelect({ label, children }, state, ref);
  const { buttonProps } = useButton(triggerProps, ref);

  return (
    <>
      <span id={label}>{label}</span>
      <button ref={ref} {...buttonProps}>…</button>
      <ul {...menuProps}>…</ul>
    </>
  );
}
```

The pattern is a strict separation of concerns: `@react-stately/*` packages own state (selection, open/close, focus), `@react-aria/*` packages own behavior (event handlers, ARIA props), and you own the markup and styling. That split is what makes React Aria different from Downshift — it is not a select library, it is a *framework for building* selects and every other interactive component (menu, dialog, combobox, date picker, slider) with the same architecture.

Adopting React Aria is a commitment. It assumes TypeScript, it has a learning curve (you must understand the state/behavior split to use it well), and it is overkill for a single select in a CRUD app. Its payoff is the strongest accessibility story of the three: if WCAG compliance is a contractual requirement, React Aria's implementation is the one you can point auditors at. Its license is Apache-2.0, and it is the most actively pushed of the three (last commit 2026-08-21).

## Pitfalls and Migration Gotchas

**1. Bundle size is a feature decision, not a detail.** react-select adds emotion (~100 KB) if you are not already on it; Downshift and React Aria are tree-shakeable hooks that add single-digit KB. Measure with a bundle analyzer before committing — not after the design system is built on the wrong foundation.

**2. Downshift v7 changed the ARIA pattern.** The ARIA 1.2 combobox uses a different role structure (`combobox` on the input, `listbox` as sibling, no `aria-owns` requirement the same way). If you are upgrading from v6, read the migration guide — your custom styling hooks into the ARIA attributes and may need updating.

**3. react-select styling overrides are a black hole.** The `styles` prop API looks simple and is not: nested selectors, `menuPortal` for overflow clipping, `theme` for global tokens. If you find yourself overriding more than a handful of sub-components, you are fighting the library — consider Downshift or React Aria instead.

**4. Overflow clipping breaks menus.** Any `overflow: hidden`/`auto` ancestor (modal, table container, drawer) clips react-select's dropdown menu. Use `menuPortalTarget={document.body}` and accept the z-index management that comes with portals. Downshift/React Aria users have the same problem and the same portal answer — it is just their own code.

**5. Search in large lists needs virtualization.** A 10,000-item options array renders fine until the menu opens and the DOM dies. react-select has built-in virtualization; with Downshift or React Aria you must compose a virtual list (e.g. react-window) yourself — our [drag-and-drop libraries guide](../2026-08-14-react-drag-and-drop-libraries-dnd-kit-react-dnd-sortablejs-guide/) covers the same compose-primitives trade-off from the DnD angle.

**6. `aria-activedescendant` vs real focus.** Combobox implementations that use `aria-activedescendant` (react-select and both headless options) keep focus on the input and announce the highlighted option via AT. This is correct, but it breaks naive "focus the option" assumptions in your own key handlers — never mix your own arrow-key logic with the library's.

**7. SSR and hydration.** All three support SSR, but react-select's menu/portal DOM and Downshift's focus management need consistent initial state between server and client render. In Next.js App Router, render selects only after mount if you see hydration mismatches.

**8. Don't nest a second select framework inside a component library.** If your app already uses Mantine, Chakra, or another library with its own select, that library's select is wired to its own theme and a11y system — see our [component libraries comparison](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/). Introduce a standalone select library only for bespoke cases, not as a global replacement.

For the form-level patterns these selects plug into, our [React form libraries comparison](../2026-07-05-javascript-form-libraries-react-hook-form-formik-tanstack-final-form/) is the companion read, and if you are choosing hooks-based libraries generally, the [React hooks libraries comparison](../2026-08-22-react-hooks-libraries-ahooks-usehooks-ts-react-use-comparison/) covers the ecosystem context.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "react-select vs Downshift vs React Aria in 2026: Which React Select Library Should You Use?",
  "description": "Compare the three React select approaches: styled react-select, headless Downshift, and accessibility-first React Aria hooks. Feature table, decision matrix, real code, and pitfalls.",
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

### What is the difference between Downshift and React Aria for building selects?

Downshift is a focused headless select/combobox primitive: it gives you the keyboard handling and ARIA wiring for select-like components and stops there. React Aria is a general behavior framework: `useSelect` is one of dozens of hooks (menu, dialog, combobox, date picker, slider), split into `@react-stately` state hooks and `@react-aria` behavior hooks. Choose Downshift for a select-only dependency, React Aria when you are building a whole component system with consistent accessibility.

### Is react-select too heavy for a small app?

It depends on your budget. react-select plus emotion adds roughly 100 KB to the bundle, which matters on mobile networks but is negligible for internal tools and desktop admin apps. If bundle size is a hard constraint, Downshift (or React Aria) with your own markup keeps the addition to a few KB.

### Does react-select support server-side rendering?

Yes. react-select works with SSR frameworks including Next.js App Router, but the default (non-portal) menu is fine as long as initial selected state is deterministic. If you need `menuPortalTarget`, render the select client-side or guard the portal element with a mounted check to avoid hydration mismatches.

### Which library has the best keyboard navigation?

All three implement the WAI-ARIA combobox keyboard model (arrow keys, Home/End, type-ahead, Escape). React Aria is the strictest about the ARIA 1.2 pattern and is tested against assistive technology as part of Adobe's program. Downshift migrated to ARIA 1.2 in v7. react-select implements its own menu model that is solid but historically lagged on edge cases.

### Can I build a multi-select with tags in Downshift?

Yes — combine `useSelect` or `useCombobox` with `useMultipleSelection`, which tracks selected items and their removal interactions. It is more wiring than react-select's `isMulti`, but you control chip rendering, animations, and layout entirely.

### Is React Aria only for Adobe Spectrum users?

No. React Aria is unstyled and design-system agnostic; React Spectrum is Adobe's *styled* component library built on top of it. You can use React Aria's hooks with your own design tokens — that is exactly the separation the project is designed for.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
