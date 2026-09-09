---
title: "Vue 3 Form Validation in 2026: VeeValidate vs Vuelidate vs FormKit"
date: "2026-09-10"
tags: ["vue", "forms", "validation", "frontend"]
draft: false
cover: "/img/screenshots/formkit-cover.jpg"
---

Form handling is where Vue applications quietly rot. The template gets a dozen `v-model` bindings, submit logic splinters across methods, and validation errors end up as hand-rolled `showError` booleans that drift out of sync with the rules. The three libraries below represent the three distinct philosophies for solving this in 2026: **VeeValidate (11,260+ stars)** manages form state and validation as composables, **Vuelidate (6,870+ stars)** stays a thin model-based validator over your own reactive state, and **FormKit (4,760+ stars)** is a full input framework where one component replaces the entire forms stack. One of them is in maintenance mode and says so in its own README; one now also speaks React. Choosing wrong here means rewriting every form in your app, so the decision deserves more than a star count.

**Quick verdict:** if you are starting fresh in 2026 and want the strongest balance of active maintenance, Vue-3-native architecture, and schema support, pick **VeeValidate** — its `useForm`/`defineField` composables and Yup/Zod resolvers cover everything from a login card to a 50-field wizard. If your team prefers colocating rules with state, hates abstractions, and accepts an LTS-level library, **Vuelidate** is still pleasant — but treat it as a stable choice, not a growing one, since the project itself now points newcomers to alternatives. If you would rather never hand-write an input wrapper again and want accessible, styled, schema-driven forms (with a free core and paid Pro inputs), **FormKit** is the most ambitious option — and as of 2026 it is no longer Vue-only.

## Vue 3 Form Validation Libraries at a Glance

| Feature | VeeValidate | Vuelidate | FormKit |
| --- | --- | --- | --- |
| GitHub stars | 11,263 | 6,871 | 4,762 |
| Latest push | 2026-03 | 2025-06 | 2026-07 |
| License | MIT | MIT | MIT core (Pro inputs paid) |
| Current major | v5 (Vue 3) | v2 (`@vuelidate/core`) | 1.x |
| Philosophy | Composable form state + validation | Model-based validation of your reactive state | Node-based full form framework |
| Schema resolvers | Yup, Zod, Valibot | No (plain rule objects) | JSON schema generation, Zod via plugins |
| Built-in rules | Via validators/resolvers | `@vuelidate/validators` package | 30+ rules in the validation engine |
| UI components | No (headless) | No (headless) | Yes — every input type + themes |
| SSR / Nuxt | Nuxt module | Works (no special SSR state) | Nuxt module, SSR compatible |
| Framework reach | Vue 3 | Vue 3 (v2 also Vue 2) | Vue 3 + React 18/19 bindings |
| Maintenance status | Active, v5 released | **LTS mode (declared in README)** | Active, expanding scope |

## Which Form Library Should You Pick? (Decision Matrix)

| Use Case | Recommended Tool | Reason |
| --- | --- | --- |
| New Vue 3 app, team wants composition API + external schemas | **VeeValidate** | `defineField` + Yup/Zod resolvers; no component tree required |
| App already owns its reactive state and only needs validation | **Vuelidate** | `useVuelidate(rules, state)` validates whatever you already have |
| Ship forms fast with labels, errors, themes, and accessibility included | **FormKit** | `<FormKit type="text" validation="required|email" />` is a whole labeled, validated input |
| Long-lived product needing decade-scale maintenance confidence | **VeeValidate** | Actively maintained; Vuelidate is honest about LTS |
| Forms driven by dynamic/backend configuration | **FormKit** | JSON schema support is a first-class feature |
| Migration from an old Vue 2 codebase | **Vuelidate v2** | Closest mental model to the Vue 2 validator era; v1 → v2 path documented |

## VeeValidate — Composable Form State with Schema Power

VeeValidate, maintained by Abdelrahman Awad (logaretm), is the most popular of the three and the one that embraced the composition API most aggressively. Instead of wrapping your inputs in components, you create a form context with `useForm` and bind fields through `defineField`; validation rules can be plain functions or full Yup/Zod schemas resolved by the library. The flagship v4/v5 API shown in the official README is compact:

```vue
<script setup>
import { useForm } from 'vee-validate';

// Validation, or use `yup` or `zod`
function required(value) {
  return value ? true : 'This field is required';
}

// Create the form
const { defineField, handleSubmit, errors } = useForm({
  validationSchema: {
    field: required,
  },
});

// Define fields
const [field, fieldProps] = defineField('field');

// Submit handler
const onSubmit = handleSubmit(values => {
  // Submit to API
  console.log(values);
});
</script>

<template>
  <form @submit="onSubmit">
    <input v-model="field" v-bind="fieldProps" />
    <span>{{ errors.field }}</span>

    <button>Submit</button>
  </form>
</template>
```

The declarative `<Form>`/`<Field>` components still exist for template-first teams, but the composition API is the recommended path.

![VeeValidate social preview](/img/screenshots/veevalidate-cover.jpg "VeeValidate — painless Vue forms library")

The composable style plays naturally with `<script setup>`, keeps your inputs as plain elements, and makes cross-field validation (confirm-password, conditional required) straightforward because everything lives in one `useForm` scope. VeeValidate's star ecosystem point is schema compatibility: teams that already define Yup or Zod schemas for TypeScript inference can feed the same schema to the form, which eliminates the "rules in two places" smell. If your data layer already revolves around a schema library, see how [Zod, Valibot and Yup compare in 2026](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/) before picking a resolver. The equivalent library on the React side of the fence — [React Hook Form and friends](../2026-07-05-javascript-form-libraries-react-hook-form-formik-tanstack-final-form/) — follows the same headless philosophy, which makes VeeValidate the natural choice for teams that maintain both frameworks.

## Vuelidate — The Model-Based Minimalist in LTS

Vuelidate takes the opposite stance: your component already has state, so validation should be a function *of* that state, not a parallel structure. You pass the reactive state plus a rules map to `useVuelidate`, and it returns a `v$` object whose `$errors`, `$invalid`, and per-field validity mirrors the state tree. The official composition API example:

```js
import { reactive } from 'vue'
import { useVuelidate } from '@vuelidate/core'
import { email, required } from '@vuelidate/validators'

export default {
  setup () {
    const state = reactive({
      name: '',
      emailAddress: ''
    })
    const rules = {
      name: { required },
      emailAddress: { required, email }
    }

    const v$ = useVuelidate(rules, state)

    return { state, v$ }
  }
}
```

In the template you then read `v$.emailAddress.$error`, display `v$.emailAddress.$errors[0].$message`, and disable submit on `v$.$invalid`. Behavior knobs like `$autoDirty` (mark fields touched after first change) and `$lazy` (wait for interaction before validating) are passed via a third `useVuelidate` argument or a `validationConfig` option. The whole library is small, has zero UI opinion, and works with both the Options API (via a `validations` option) and the composition API.

The 2026 reality check is right in the README: **"Vuelidate is currently in LTS mode."** The last push was June 2025, and the project now explicitly lists alternatives (Regle, VeeValidate, VueForm) for teams that want active development. That honesty is refreshing — for a stable internal tool with frozen requirements, LTS is arguably a feature: no breaking majors, no churn. But if your roadmap includes Nuxt 4 upgrades, TypeScript-first schema sharing, or new form patterns, budget for the fact that new features will come from elsewhere.

## FormKit — The One-Component Form Framework

FormKit, created by Justin Schroeder, is the most different of the three: it is not a validator you bolt onto inputs but a **node-based form framework** where every `<FormKit>` input owns a reactive "node." Nodes structure data automatically across nesting — a `type="group"` nests as an object, `type="list"` as an array — so the shape of your form data mirrors the shape of your template with zero manual assembly. The flagship example from the official README shows the promise: one component that is simultaneously an input, a label, a validator, an error display, and a submit handler:

```jsx
<FormKit type="form" onSubmit={handleSubmit}>
  <FormKit type="text" name="email" label="Email" validation="required|email" />
  <FormKit type="password" name="password" label="Password" validation="required|length:8" />
</FormKit>
```

That snippet is a fully accessible form — ARIA attributes, labels, inline error messages, loading state, and submit handling included. FormKit ships 30+ built-in validation rules declared inline as strings, i18n for 30+ languages, first-class Tailwind theming through its Regenesis theme, and a serializable JSON schema that lets you render whole forms from configuration. The architecture is deliberately split into framework-agnostic packages (`@formkit/core`, `@formkit/validation`, `@formkit/rules`, `@formkit/inputs`) with thin bindings on top (`@formkit/vue` for Vue 3) — and in a significant 2026 development, **`@formkit/react` now provides React 18/19 bindings**, turning FormKit into a cross-framework forms layer rather than a Vue-only tool.

The business model deserves attention before you commit: the core and all native HTML inputs are MIT, but **FormKit Pro** is a paid library of premium inputs (autocomplete, datepicker, repeater, drag-and-drop, mask, slider, tag list, toggle). You can build an entire production app on the free core; the moment a designer asks for a combobox with keyboard navigation, the paid tier enters the conversation. That is a reasonable model, but it is a different risk profile than the fully-MIT competitors — evaluate the Pro catalog *before* choosing FormKit, not after your input requirements outgrow the core.

## Migration Traps and Integration Pitfalls

Whichever library you choose, these are the failure modes teams hit after the first happy week:

1. **Do not mix two form state sources.** VeeValidate and FormKit each own form state; Vuelidate deliberately does not. Wiring a VeeValidate form's values into your Pinia store on every keystroke, then also reading store state back into the form, creates update loops. Sync on submit or on `onSubmit` values only.
2. **Error object shapes differ and are not interchangeable.** VeeValidate gives you `errors.field` (flat string map) or `errors` with field metadata; Vuelidate nests `v$.field.$errors` per field; FormKit renders errors itself. Codemods for "the other library" will not map one-to-one — budget a rewrite of every error-display template during migration.
3. **Vuelidate LTS means no new validators.** If you need a rule Vuelidate does not ship (say, checksum or custom async uniqueness), you write it yourself and maintain it. VeeValidate and FormKit both have richer plugin/extension paths.
4. **Async validation needs care everywhere.** Debounce remote checks (username availability, coupon codes). VeeValidate and FormKit support async rules, but naive implementations fire a request per keystroke — and with Vuelidate, async rules require `$externalResults` handling for server errors.
5. **Schema libraries pull in a second dependency tree.** VeeValidate's Yup/Zod resolvers are great, but they make your validation dependent on a schema library's release cadence. If you do not already use schemas for type inference, plain function rules keep the surface smaller.
6. **Nuxt hydration mismatches.** Any library that renders validation state on the server must produce identical output on the client. FormKit's Nuxt module handles this explicitly; with VeeValidate or Vuelidate, keep first paint free of `$invalid`-driven UI changes or you will see hydration warnings.
7. **FormKit Pro creep.** Free core + paid inputs is a slippery budgeting slope. List the exact input types your product needs now, check the Pro catalog, and decide at kickoff — the premium inputs are the reason many teams adopt FormKit, and also the reason some reject it.

## SSR, Nuxt, and Ecosystem Considerations

Framework integration depth matters as much as API taste. **VeeValidate** ships a Nuxt module and is the most documented of the three for large apps, with guides covering conditional fields, multi-step wizards, and server-driven forms. **Vuelidate** has no module — it does not need one, since validation is computed from state you already manage, but that also means no first-party opinion about SSR state serialization; keep validation derived, not stored. **FormKit** provides the most complete out-of-the-box experience: Nuxt module, SSR-safe node tree, and themes that survive hydration. For teams that render forms from a CMS or admin-defined JSON, FormKit's schema engine is the differentiator no other Vue library matches. Whichever path you take, prototype one realistic form (with at least one async rule and one cross-field rule) before the big migration — form libraries feel identical in a todo demo and completely different under real constraints. And if you are maintaining forms in both Vue and React, VeeValidate (headless) and FormKit (full-framework) are currently the only two options above that give you a consistent mental model across both ecosystems.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Vue 3 Form Validation in 2026: VeeValidate vs Vuelidate vs FormKit",
  "description": "Compare VeeValidate, Vuelidate and FormKit for Vue 3 form validation in 2026: real code samples, LTS status, schema resolvers, FormKit Pro licensing, decision matrix and migration pitfalls.",
  "datePublished": "2026-09-10",
  "dateModified": "2026-09-10",
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

**Is Vuelidate still maintained in 2026?**
Vuelidate is in LTS mode: the project receives fixes but no significant new features, and its README explicitly recommends actively maintained alternatives for new projects. The last commit was June 2025. It remains a solid choice for stable codebases that value zero churn over new capabilities.

**Does VeeValidate support Yup and Zod?**
Yes. VeeValidate accepts plain function rules, but its signature feature is resolving external schemas — Yup and Zod are first-class, and Valibot is supported through community resolvers. This lets you define validation once and share it with your TypeScript data layer.

**Is FormKit really free?**
The FormKit core — all native HTML inputs (text, select, checkbox, textarea and more), the node tree, validation engine, theming, i18n and JSON schema — is MIT licensed and free. FormKit Pro is a separate paid collection of premium inputs such as autocomplete, datepicker and drag-and-drop lists. Check the Pro catalog before committing if you anticipate advanced input needs.

**Which library is best for Nuxt 3 or Nuxt 4?**
VeeValidate and FormKit both provide first-party Nuxt integration. FormKit's module handles SSR serialization of its node tree; VeeValidate's module wires the form context into the app. Vuelidate works fine in Nuxt as long as validation stays derived from your own state rather than stored server-side.

**Can I migrate from Vuelidate to VeeValidate mechanically?**
Not mechanically. The mental models differ: Vuelidate validates state you already own, while VeeValidate becomes the owner of form state and exposes flat error maps. Every template that reads `v$.field.$errors` needs rewriting, and cross-field rules must be re-expressed inside `useForm` scopes. Budget real time for the migration — it is a rewrite of form logic, not a find-and-replace.

**Does FormKit really work with React?**
Yes — since its 2026 releases, FormKit ships `@formkit/react` bindings for React 18/19 in addition to `@formkit/vue` for Vue 3, built on the same framework-agnostic core. Validation rules, schemas and themes are shared across both bindings.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
