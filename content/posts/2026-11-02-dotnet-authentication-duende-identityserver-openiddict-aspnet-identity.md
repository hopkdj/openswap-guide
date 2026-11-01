---
title: "Duende vs OpenIddict vs ASP.NET Core Identity in 2026: Pick the Wrong One and You'll Rewrite Auth Twice"
date: "2026-11-02"
tags: ["dotnet", "csharp", "authentication", "oauth", "self-hosted"]
draft: false
description: "Duende IdentityServer, OpenIddict and ASP.NET Core Identity compared on real 2026 data: licensing, protocol support, working code and the auth traps that cost teams weeks."
---

Every .NET team builds the same thing twice. First they add a login form, a `User` table, and a JWT — done in a weekend. Eighteen months later a partner needs SSO, a mobile app needs refresh tokens, a second service needs to validate tokens, and someone asks for "Sign in with Microsoft". That is when the weekend decision becomes an architecture problem.

There are three names you will hit: **Duende IdentityServer**, **OpenIddict**, and **ASP.NET Core Identity**. They are not three versions of the same product. One is a commercial OIDC/OAuth server, one is an open-source OIDC/OAuth server, and one is a user store that speaks no protocol at all. Confusing them is the single most expensive mistake in .NET auth.

## TL;DR — Quick Verdict

- **Need a full OIDC/OAuth authorization server and have budget or qualify for the free tier?** **Duende IdentityServer** (v8.0.10, Oct 2026). The most complete, best documented option, with admin UI and operational tooling available.
- **Need the same protocols but cannot take a commercial dependency?** **OpenIddict** (7.7.2, Apache-2.0). Leaner, fully open source, actively maintained, and config-first.
- **You only need user accounts, password hashing, 2FA and cookie login inside one app?** **ASP.NET Core Identity** is already in the box — do not install a protocol server you do not need.
- **Wrong answer to avoid:** using ASP.NET Core Identity as your OIDC provider for third-party clients. It issues cookies, not standards-compliant tokens.

## The Real Numbers (fetched November 2026)

| | Duende IdentityServer | OpenIddict | ASP.NET Core Identity |
|---|---|---|---|
| GitHub repo | `DuendeSoftware/IdentityServer` | `openiddict/openiddict-core` | `dotnet/aspnetcore` |
| Stars | **1,613** | **5,292** | **38,498** (whole framework) |
| Latest release | **is-8.0.10** (2026-10-15) | **7.7.2** (2026-10-10) | ships with .NET |
| License | Commercial (free under revenue threshold) | **Apache-2.0** | **MIT** |
| OIDC / OAuth 2.x server | **yes, full** | **yes, full** | **no** (cookie auth only) |
| Token issuance | yes | yes | needs extra libraries or a custom implementation |
| Admin UI | commercial add-on | none (bring your own) | scaffolding pages |
| Persistence | EF Core stores + migrations | EF Core / MongoDB / custom | EF Core |
| Multi-tenancy | supported | supported via issuer per tenant | not applicable |
| Best fit | product auth, enterprise SSO | open-source products, embedded auth | single-app user accounts |

The star counts mislead here. Duende's repo is smaller because the product is commercial and forks are not the distribution mechanism. OpenIddict's stars reflect exactly what you would expect from the default open-source OIDC stack for .NET.

## Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| SaaS with partners, SSO, and third-party API clients | **Duende** | Full protocol coverage, documented extensibility, support contracts |
| Open-source product that must stay dependency-clean | **OpenIddict** | Apache-2.0, no revenue threshold, no license key in startup |
| Internal admin app with email + password only | **ASP.NET Core Identity** | Already installed, no extra service to operate |
| Microservices needing token validation only | **Duende** or **OpenIddict** (as the issuer) + JwtBearer on services | You need an issuer; Identity alone cannot be one |
| You must support device flow, PAR, token exchange | **Duende** | Broadest flow coverage with first-class docs |
| You want auth embedded in your existing app process | **OpenIddict** | Designed to be hosted in your own ASP.NET Core app |

## Duende IdentityServer — The Complete Option

Duende is the continuation of the original IdentityServer4 by its creators, and it shows: the model is mature, the docs are a book, and the extension points are named the way you would name them.

```csharp
var isBuilder = builder.Services
    .AddIdentityServer(options =>
    {
        options.Events.RaiseErrorEvents = true;
        options.Events.RaiseInformationEvents = true;
        options.Events.RaiseFailureEvents = true;
        options.Events.RaiseSuccessEvents = true;

        options.ServerSideSessions.UserDisplayNameClaimType = "name";
    })
    .AddTestUsers(TestUsers.Users)
    // clients, resources, CORS from the database
    .AddConfigurationStore(options =>
    {
        options.ConfigureDbContext = b =>
            b.UseSqlite(connectionString,
                dbOpts => dbOpts.MigrationsAssembly(typeof(Program).Assembly.FullName));
    })
    // codes, tokens, consents
    .AddOperationalStore(options =>
    {
        options.ConfigureDbContext = b =>
            b.UseSqlite(connectionString,
                dbOpts => dbOpts.MigrationsAssembly(typeof(Program).Assembly.FullName));
    })
    .AddServerSideSessions()
    .AddLicenseSummary();
```

That snippet is lifted from the official v8 template, and it exposes the two-persistence-model design you must understand before production: **configuration store** (clients, API resources, identity resources) and **operational store** (authorization codes, reference tokens, consents, device codes). The operational store grows forever — you need a cleanup job, and the default template does not ship one.

Then:

```csharp
var app = builder.Build();
app.UseIdentityServer();   // must come before UseAuthorization
app.UseAuthorization();
app.MapDefaultControllerRoute();
app.Run();
```

**The licensing reality.** Duende is free for development and for organizations under a revenue threshold (currently one million USD annually), and requires a paid license above it. In v8 the license is surfaced through `AddLicenseSummary()`, and an unlicensed production deployment logs warnings rather than hard-failing — which means it can silently ship. Check this before you go live; a surprise compliance conversation with procurement is worse than a surprise invoice.

What you get for the money: an admin UI (commercial), full OIDC conformance, dynamic client registration, server-side sessions, and a support contract. For a SaaS with paying customers, that trade is usually correct.

## OpenIddict — The Open-Source Protocol Server

OpenIddict does the same protocol work with a different philosophy: configuration in code, no license key, Apache-2.0, and everything lives inside your ASP.NET Core application.

```csharp
builder.Services.AddOpenIddict()
    .AddCore(options =>
    {
        options.UseEntityFrameworkCore()
               .UseDbContext<ApplicationDbContext>();
    })
    .AddServer(options =>
    {
        options.SetAuthorizationEndpointUris("connect/authorize")
               .SetDeviceAuthorizationEndpointUris("connect/device")
               .SetEndSessionEndpointUris("connect/endsession")
               .SetIntrospectionEndpointUris("connect/introspect")
               .SetPushedAuthorizationEndpointUris("connect/par")
               .SetRevocationEndpointUris("connect/revoke")
               .SetTokenEndpointUris("connect/token")
               .SetUserInfoEndpointUris("connect/userinfo");

        options.AllowAuthorizationCodeFlow()
               .AllowDeviceAuthorizationFlow()
               .AllowRefreshTokenFlow()
               .AllowTokenExchangeFlow();

        options.RegisterScopes(Scopes.Email, Scopes.Profile, Scopes.Roles, "demo_api");

        options.AddDevelopmentEncryptionCertificate()
               .AddDevelopmentSigningCertificate();

        options.UseAspNetCore()
               .EnableAuthorizationEndpointPassthrough()
               .EnableTokenEndpointPassthrough()
               .EnableUserInfoEndpointPassthrough();
    });
```

That is real configuration from the official sandbox and it reads like a checklist of what you must decide: endpoints, flows, scopes, credentials, host integration. Nothing is hidden, nothing is magic, and there is no feature that phones home.

Two things to plan for. First, `AddDevelopmentEncryptionCertificate()` and `AddDevelopmentSigningCertificate()` **must** be replaced in production with certificates loaded from a store (Key Vault, AWS Secrets Manager, a mounted PFX). Shipping development certificates means every token becomes forgeable by anyone who finds the well-known dev key. Second, OpenIddict has no admin UI. You will build client management yourself — which is a day of Razor pages, but it is your day.

In exchange you get: no revenue threshold, no license key, Apache-2.0 clarity for legal review, and a smaller surface area. For open-source products and internal platforms, this is usually the right call.

## ASP.NET Core Identity — Not an Authorization Server

This is where teams go wrong. `AddIdentity<TUser, TRole>()` gives you a user store, password hashing (PBKDF2 with iteration counts managed by the framework), lockout, 2FA, email confirmation, and cookie authentication.

```csharp
builder.Services.AddIdentity<IdentityUser, IdentityRole>(options =>
    {
        options.SignIn.RequireConfirmedAccount = true;
        options.Lockout.MaxFailedAccessAttempts = 5;
    })
    .AddEntityFrameworkStores<ApplicationDbContext>()
    .AddDefaultTokenProviders();

builder.Services.ConfigureApplicationCookie(options =>
{
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Lax;
    options.ExpireTimeSpan = TimeSpan.FromHours(8);
    options.SlidingExpiration = true;
});

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
```

This is genuinely good at what it does, and it is free. What it does **not** do is speak OIDC. It will not serve `/.well-known/openid-configuration`, it will not issue ID tokens, it will not run an authorization code flow, and it will not do token introspection. If your mobile app needs to authenticate against your API, cookies in a WebView are not an answer.

The honest pattern is: **Identity for the user store, Duende or OpenIddict for the protocol.** Both integrate with Identity's `UserManager` and `SignInManager` directly — OpenIddict's samples use Identity as the account backend, and Duende's templates support ASP.NET Core Identity out of the box. That combination is the standard production shape.

## Deployment Notes

Any of these sit behind a reverse proxy as a normal ASP.NET Core app. A minimal Dockerfile that matches current .NET container images:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish src/Auth/Auth.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app
COPY --from=build /app/publish .
ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080
USER $APP_UID
ENTRYPOINT ["dotnet", "Auth.dll"]
```

Two proxy settings matter more than people expect: forwarded headers (so the issuer URI matches the public URL) and **data protection key persistence**. If keys live in the container filesystem, every redeploy invalidates every cookie and antiforgery token. Mount a shared key ring or use a persisted store.

If you self-host the identity provider alongside other services, the reverse proxy is the same shape as any other stack — see our notes on [self-hosted OIDC and SSO](../2026-04-25-dex-vs-kanidm-vs-rauthy-self-hosted-oidc-sso-guide-2026/) for the surrounding architecture and on [mock OAuth2 servers for testing](../2026-05-16-self-hosted-mock-oauth2-servers-navikt-mockserver-keycloak-guide/) for a safe place to exercise flows before production.

## Pitfalls That Cost Real Weeks

**1. Development signing certificates in production.** Both Duende's template and OpenIddict's sandbox use development credentials for convenience. Anyone can extract them. Replace them with real certificates and rotate them on a schedule — with a published JWKS overlap window so clients do not break mid-rotation.

**2. Putting `UseIdentityServer()` in the wrong order.** It must run before `UseAuthorization()`, and after `UseRouting()`. Silent 401s on every endpoint usually trace back to middleware ordering, not to token problems.

**3. Missing data protection key persistence.** Containers get replaced, keys disappear, every session dies, and nobody can reproduce it in development because the key ring survives there. This is the classic .NET auth incident.

**4. Operational store growth.** Reference tokens, consents and device codes accumulate. Without a cleanup job (Duende ships `Duende.IdentityServer.EntityFramework` cleanup APIs; OpenIddict expects you to prune), your auth database becomes the largest thing you own.

**5. Treating refresh tokens as infinite.** Refresh token rotation exists because stolen refresh tokens are the most valuable thing an attacker can get. Short lifetimes, rotation, and reuse detection — Duende enables reuse detection by default in recent versions; verify your configuration instead of assuming.

**6. Claims mapping surprises.** `JwtSecurityTokenHandler.DefaultMapInboundClaims = false` appears in the official templates for a reason: the default maps short claim names (`sub` → a long URI), which breaks `User.FindFirst("sub")`. Set it explicitly in every API, not just the issuer.

**7. Testing only the happy path.** Expired tokens, clock skew, wrong audience, revoked clients — these are the paths that break in production. Wire integration tests against a test issuer early.

## FAQ

**Is Duende IdentityServer still free?**
It is free for development and for organizations below the revenue threshold defined in its license (currently one million USD annual revenue); above that, a commercial license is required. The software will run unlicensed, but that is a compliance problem, not a technical one.

**Can I use OpenIddict in production without paying anything?**
Yes. OpenIddict is Apache-2.0 with no revenue threshold. You pay in engineering time: no admin UI, and you own client management.

**Do I need IdentityServer at all if I use ASP.NET Core Identity?**
Only if you need OIDC/OAuth. For a single server-rendered app with cookie login, Identity alone is sufficient and simpler. The moment a separate client (mobile, SPA, partner) needs tokens, you need a protocol server.

**Which is faster to get running?**
ASP.NET Core Identity by an hour; OpenIddict in a day if you follow the sandbox closely; Duende in a few hours with the template, longer once you configure the persistence stores and licensing correctly.

**Can Duende and OpenIddict coexist?**
Technically they can, but there is no good reason. Pick one issuer per trust domain. Two issuers means two key sets, two metadata documents, and confused clients.

**How do I migrate from IdentityServer4?**
IdentityServer4 is archived. Duende provides a migration path (package rename, namespace changes, licensing); OpenIddict requires re-implementing configuration but keeps your Identity user store intact. If you are starting fresh in 2026, do not start on IdentityServer4.

## Related Reading

For the dependency-injection plumbing both servers rely on, see our [C# DI containers comparison](../2026-07-04-csharp-di-containers-autofac-ninject-castle-windsor-simpleinjector-lamar/). If your tokens carry timestamps that clients must parse consistently, the [.NET datetime libraries comparison](../2026-09-18-dotnet-datetime-libraries-nodatime-timezoneconverter-timeperiodlibrary/) covers the serialization traps.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Duende vs OpenIddict vs ASP.NET Core Identity in 2026",
  "description": "Comparison of the three main .NET authentication options in 2026: Duende IdentityServer 8, OpenIddict 7 and ASP.NET Core Identity, with real version data, code and production pitfalls.",
  "datePublished": "2026-11-02",
  "dateModified": "2026-11-02",
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
