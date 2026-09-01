---
title: "Better Auth vs Auth.js vs Passport in 2026: Which Node.js Auth Library Should You Actually Use?"
date: "2026-09-01"
tags: ["comparison", "guide", "developer-tools", "authentication", "nodejs", "typescript", "security"]
draft: false
description: "Compare Better Auth, Auth.js (NextAuth), and Passport — the three dominant Node.js and TypeScript authentication libraries — across session strategy, MFA, OAuth providers, edge runtime support, and maintenance activity. Includes real configs, security pitfalls, and a decision matrix for 2026."
---

Authentication is the only code you write where a mistake costs you accounts instead of uptime. In 2026 the Node.js auth landscape shifted more than in any year since Passport appeared in 2011: the classic middleware has not had a commit since August 2024, Auth.js finally stabilized its v5 rewrite, and **Better Auth — a library that did not exist two years ago — crossed 29,000 GitHub stars with commits landing daily**. Choose wrong and you are either maintaining a zombie dependency or rebuilding your session layer twice a year. This guide compares all three with real data, real configs, and a clear verdict.

## TL;DR — Quick Verdict

- **Choose Better Auth** for any new TypeScript project — it is framework-agnostic (Express, Hono, Fastify, Next.js, SvelteKit), ships MFA, passkeys, organizations, and an admin dashboard as plugins, and is the only one of the three with commits this week.
- **Choose Auth.js** if you live in Next.js and want the path of least resistance — native App Router integration, 70+ OAuth providers, and a huge community, at the cost of framework coupling and occasional API churn.
- **Keep Passport only for legacy Express apps** where its 500+ strategy catalog still beats everything else. Do not start a new project with it in 2026.

## Comparison at a Glance

| Dimension | Better Auth | Auth.js (NextAuth) | Passport |
|---|---|---|---|
| License | MIT | ISC | MIT |
| First released | 2024 | 2016 (as NextAuth) | 2011 |
| GitHub stars (Sep 2026) | **29,786** | **28,357** | **23,534** |
| Last commit | **Sep 2026** | Jul 2026 | **Aug 2024** |
| Framework focus | Any (Express/Hono/Fastify/Next) | Next.js first, adapters for SvelteKit/SolidStart | Express / Connect |
| Session strategy | Database or JWT, configurable | JWT default, database optional | Manual via express-session |
| MFA / TOTP | Built-in plugin | Community guides only | Third-party strategies |
| OAuth / social providers | Built-in providers + OIDC plugin | 70+ built-in providers | 500+ strategies |
| Admin UI for user management | Built-in plugin | Community projects | None |
| Rate limiting on auth routes | Built-in plugin | External middleware required | External middleware required |
| Edge runtime (Vercel Edge, Workers) | Yes | Yes | **No (Node-only)** |
| Database adapters | 20+ (Drizzle, Prisma, Kysely, MongoDB) | Prisma, Drizzle, Kysely, MongoDB | None — bring your own |
| Passkey support | Built-in plugin | Experimental | Via strategy |
| TypeScript quality | First-class, end-to-end inferred types | First-class | Third-party `@types/passport` |

## Decision Matrix

| Use case | Recommended tool | Why |
|---|---|---|
| New Next.js App Router app, fastest possible setup | **Auth.js** | Native handlers export, 5-minute integration, largest community of the three |
| New TypeScript API on Hono, Fastify, or Express | **Better Auth** | Framework-agnostic, plugins for MFA/admin/orgs, active development |
| Legacy Express app with years of Passport strategies | **Passport** | 500+ strategies still unmatched; migration cost outweighs maintenance risk |
| Serverless edge deployment (Vercel Edge, Cloudflare Workers) | **Better Auth or Auth.js** | Both run on edge; Passport is Node-only |
| Team needs a user-management admin UI without building one | **Better Auth** | Admin plugin renders a full dashboard from your schema |
| You want to delegate auth to a self-hosted SSO instead | Neither — see below | Application libraries are the wrong tool when you need organization-wide identity |

## Better Auth — The New Default (29,786★, last commit Sep 2026)

Better Auth is a TypeScript-first authentication framework built by the team behind the `harshhhdev` open-source work, and it has become the fastest-growing auth library in the ecosystem. Its core idea: you declare your auth configuration once, and it generates the REST endpoints, database schema, and client-side hooks from it. Sessions can live in your database or in signed JWTs, and everything from two-factor TOTP to passkeys to multi-tenant organizations is a one-line plugin instead of a weekend project.

The architecture is deliberately framework-agnostic. You create an auth instance, then mount its handler on whatever HTTP framework you already use:

```ts
// src/lib/auth.ts
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  emailAndPassword: { enabled: true },
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    },
  },
});

// src/index.ts — mount on Hono
import { Hono } from "hono";
import { auth } from "./lib/auth";

const app = new Hono();
app.on(["POST", "GET"], "/api/auth/*", (c) => auth.handler(c.req.raw));
```

The same `auth` object works with Express, Fastify, Next.js route handlers, SvelteKit, or Astro. Database integration uses schema-first adapters — you run `npx @better-auth/cli generate` and it produces the Drizzle or Prisma schema for your session, user, and account tables, then the client SDK gives you typed `signIn.email()`, `signUp.email()`, and `useSession()` hooks.

**The honest trade-offs:** Better Auth is young. Version 2 of the API landed in 2025 and moved several plugin interfaces between minor releases; you should pin versions and read migration notes. The plugin ecosystem is smaller than Passport's strategy catalog, though the built-in coverage (MFA, passkeys, magic links, phone numbers, organizations, admin dashboard, OIDC server) covers what most products actually need. For a new project this is the best risk-adjusted choice in 2026.

## Auth.js (NextAuth) — The Next.js Native (28,357★, last commit Jul 2026)

Auth.js started life as NextAuth.js in 2016, became the default authentication answer for Next.js, and in v5 pivoted to a framework-adapter model while remaining deeply integrated with the Next.js App Router. The mental model is provider-centric: you list providers (OAuth, credentials, email), choose a session strategy (JWT by default, database if you need revocation), and export framework-specific handlers.

```ts
// app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import Credentials from "next-auth/providers/credentials";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    GitHub,
    Credentials({ credentials: { email: {}, password: {} } }),
  ],
  session: { strategy: "jwt" },
});

export const { GET, POST } = handlers;
```

Server components call `auth()` to get the session; client components use `useSession()`; `signIn()` and `signOut()` handle the flow. For the 90% case — a Next.js app that needs Google/GitHub login plus a protected dashboard — this is still the least code you can write, and the community answers for almost any problem already exist.

**The honest trade-offs:** the v4-to-v5 migration was painful (middleware rewrites, `getServerSession` removal, new `auth()` API), and v5 has shipped breaking changes faster than many teams expected. Credentials-based login is actively discouraged in the docs in favor of OAuth, and MFA still requires rolling your own flow with third-party libraries. If you are not on Next.js, the adapter story (SvelteKit, SolidStart) works but the docs and examples are visibly Next-first.

## Passport — The Veteran That Stopped Moving (23,534★, last commit Aug 2024)

Passport is the authentication middleware that defined Node.js auth for a decade. It uses a strategy pattern — `passport-local`, `passport-google-oauth20`, `passport-jwt`, and roughly 500 more — and composes with Express sessions cleanly:

```js
// Express + Passport classic local strategy
const passport = require("passport");
const LocalStrategy = require("passport-local").Strategy;

passport.use(new LocalStrategy({ usernameField: "email" },
  async (email, password, done) => {
    const user = await User.findOne({ email });
    if (!user || !(await user.verifyPassword(password))) return done(null, false);
    return done(null, user);
  }
));

app.post("/login", passport.authenticate("local", { failureRedirect: "/login" }));
```

**The hard truth:** the core repo has had no meaningful commit since August 2024, TypeScript types come from a third-party package, and the 500+ strategy ecosystem is a graveyard of half-maintained integrations — some official-looking strategies have unfixed vulnerabilities. It is not that Passport is broken; it is that it is *done*, and "done" means nobody is watching the door. For existing Express codebases that already run Passport, staying put is defensible. For anything greenfield, it is the wrong default in 2026.

## Pitfalls: What Actually Goes Wrong

1. **JWT sessions you cannot revoke.** Auth.js defaults to JWT sessions; a stolen token stays valid until expiry. If you need "log out everywhere" or per-user bans, switch to database sessions — Better Auth makes the choice explicit, Auth.js requires an adapter, Passport leaves it entirely to you.
2. **Login endpoints without rate limiting are a brute-force invitation.** Better Auth ships a rate-limiter plugin; with Auth.js you need Upstash/Redis middleware or similar; with Passport you need `express-rate-limit` and helmet configured correctly. Do not ship without it.
3. **Passport's dormancy is a security decision.** When the core library stops receiving updates, you inherit the risk of every unpatched edge case in its session handling. Budget for a migration if you are building new features on it.
4. **Auth.js API churn.** v5 changed middleware and session APIs between minor versions. Pin exact versions, read the release notes, and keep your `auth()` wrapper thin so upgrades are localized.
5. **Better Auth's youth.** Plugin interfaces moved between v1 and v2. Lock versions and subscribe to migration guides before upgrading major versions.
6. **OAuth state and CSRF.** Libraries handle the state parameter and CSRF tokens — hand-rolled OAuth flows routinely forget one of them. Use the library's built-in flow, never reimplement the redirect dance.
7. **Cookie flags.** `Secure`, `HttpOnly`, and `SameSite=Lax` are non-negotiable for session cookies in production; every library lets you misconfigure them, none will stop you.
8. **When not to use any of them.** If your organization needs centralized identity across many services, an application-level auth library is the wrong layer entirely. Delegate to a self-hosted identity provider instead — see our [Casdoor vs Zitadel vs Authentik lightweight SSO comparison](../2026-04-21-casdoor-vs-zitadel-vs-authentik-lightweight-sso-guide-2026/) for OpenID Connect at the platform level, [Dex vs Kanidm vs Rauthy for self-hosted OIDC providers](../2026-04-25-dex-vs-kanidm-vs-rauthy-self-hosted-oidc-sso-guide-2026/), and [LLDAP vs Glauth for lightweight LDAP directory auth](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/) when you have non-web services to authenticate.

## Migration Notes: Moving Between Libraries

If you are migrating away from Passport or from Auth.js v4, plan the session table first. All three libraries handle `user`, `session`, and `account` differently: Passport leaves persistence entirely to you, Auth.js v5 expects adapter-specific session models, and Better Auth generates its own schema via the CLI. The pragmatic sequence is: (1) stand up the target library on a staging route prefix, (2) migrate users and password hashes (bcrypt/argon2 hashes are portable — plaintext or MD5 is not), (3) dual-run for one release cycle, (4) cut over and revoke all legacy sessions in one shot. Teams that skip step 2 are the ones that end up forcing a "reset your password" email to every customer.

## FAQ

**Is Passport still maintained in 2026?**
The core `jaredhanson/passport` repository has not received a commit since August 2024. It remains functional and hugely popular (23,534 stars), but it is effectively in maintenance limbo — no new features, and security fixes are not guaranteed. Do not start new projects on it.

**What is the difference between Auth.js and NextAuth?**
NextAuth was renamed to Auth.js during the v5 rewrite. "NextAuth" usually refers to the older v4 API (`getServerSession`, pages directory style), while Auth.js is the current framework-adapter implementation. The package name is still `next-auth` on npm for the Next.js integration.

**Does Better Auth work with Next.js App Router?**
Yes — you mount the auth handler in a route handler (`app/api/auth/[...all]/route.ts`) and use the client SDK hooks. Many teams choose Better Auth over Auth.js specifically because it works identically across Next.js, Express, Hono, and other frameworks, which keeps options open.

**Which library supports MFA out of the box?**
Only Better Auth ships TOTP two-factor authentication as a built-in plugin. Auth.js requires a community or hand-rolled implementation, and Passport relies on third-party strategies of varying quality.

**Can I use these libraries with a self-hosted identity provider?**
Yes. Better Auth includes an OIDC plugin and supports standard OAuth flows against providers like Keycloak, Zitadel, or Authelia; Auth.js supports any OAuth 2.0/OIDC provider through its provider interface. If you need organization-wide single sign-on across multiple applications, consider delegating auth entirely to a self-hosted SSO platform instead of embedding a library.

**What is the safest session configuration in 2026?**
Database-backed sessions with short TTLs, rotating session IDs on privilege change, `HttpOnly` + `Secure` + `SameSite=Lax` cookies, and mandatory rate limiting on login and password-reset endpoints. Prefer database sessions whenever you need server-side revocation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Better Auth vs Auth.js vs Passport in 2026: Which Node.js Auth Library Should You Actually Use?",
  "description": "Compare Better Auth, Auth.js (NextAuth), and Passport — the three dominant Node.js and TypeScript authentication libraries — across session strategy, MFA, OAuth providers, edge runtime support, and maintenance activity. Includes real configs, security pitfalls, and a decision matrix for 2026.",
  "datePublished": "2026-09-01",
  "dateModified": "2026-09-01",
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
