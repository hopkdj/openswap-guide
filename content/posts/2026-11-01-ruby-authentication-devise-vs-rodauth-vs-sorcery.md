---
title: "Ruby Authentication in 2026: Devise vs Rodauth vs Sorcery — Which One Actually Fits?"
date: "2026-11-01"
tags: ["ruby", "rails", "authentication", "security", "web-development"]
draft: false
---

Devise has 24,356 GitHub stars and shows up in essentially every Rails tutorial, which is exactly why so many teams install it without asking what they bought. What they bought is **ten modules compiled into one model** — `database_authenticatable`, `registerable`, `recoverable`, `rememberable`, `trackable`, `validatable`, `confirmable`, `lockable`, `timeoutable`, `omniauthable` — most of which they will never configure correctly, and two of which shipped **security advisories in 2026**.

Rodauth takes the opposite stance: nothing is enabled until you name it, and every feature is a modular plugin on a single `accounts` table. Sorcery sits in the middle — a lightweight ActiveRecord mixin with opt-in submodules, popular in 2013, and now maintained at a slower cadence than either.

This is not a "Devise is bad" article. Devise is the correct choice for a large share of Rails apps. The point is that **the three libraries encode three different answers to "how much auth do you want to own?"** and picking against your team's appetite is how you end up with a 900-line `User` model.

## The 30-Second Verdict

**Use Devise** if you are on Rails, want the standard feature set (signup, confirmation, password reset, remember-me, lockout), and would rather follow a decade of Stack Overflow answers than write auth code. It is boring in the best way — provided you keep it patched.

**Use Rodauth** if you need multi-factor authentication, WebAuthn, password-less login, account expiry, or per-feature auditing, and you are willing to configure a real auth system instead of inheriting one. It is the only one of the three where "enable 2FA" is a one-line change rather than a gem-plus-migration project.

**Use Sorcery only for legacy codebases or tiny apps** where you genuinely want `current_user` and nothing else. Its submodule model is clean, but its release cadence trails the other two by months, and its documentation lives mostly in a wiki.

The one-line heuristic: **Devise = batteries included. Rodauth = batteries selectable. Sorcery = bring your own batteries.**

## Comparison Table

| Dimension | Devise | Rodauth | Sorcery |
|---|---|---|---|
| Latest version | 5.0.4 | 2.49.0 | 0.18.0 |
| GitHub stars | 24,356 | 1,945 | 1,460 |
| Last repo activity | 2026-10-06 | 2026-10-27 | 2026-07-08 |
| License | MIT | MIT | MIT |
| Framework coupling | Rails (railties >= 7.0) | Roda (Rails via `rodauth-rails`) | Rails, ActiveRecord |
| Model footprint | 10 modules by default | Zero — config DSL | Opt-in submodules |
| Database schema | Adds ~12 columns to `users` | Single `accounts` table + feature tables | Adds columns per submodule |
| Two-factor auth | Third-party gems | Built in (`otp`, `webauthn`, `sms`) | Not provided |
| WebAuthn / passkeys | Third-party | Built in | Not provided |
| Built-in rate limiting | No (use rack-attack) | Yes, per feature | No |
| Security advisories in 2026 | Two (fixed in 5.0.3, 5.0.4) | None published | None published |
| Config surface | Initializer + model DSL | One `configure` block | Initializer + model mixin |
| Learning curve | Low (huge ecosystem) | Medium-steep | Low |

Note the star ratio: 12:1 in Devise's favour. That is not a quality signal, it is an age signal — Devise shipped in 2009, Rodauth in 2015. What matters at decision time is that **Rodauth's repo saw activity five weeks more recently than Devise's**, despite being a fraction of the size.

## Decision Matrix

| Your situation | Choose | Why |
|---|---|---|
| Standard Rails SaaS, email + password | Devise | Confirmation, reset, lockout for free |
| Rails app needing passkeys or TOTP | Rodauth (via `rodauth-rails`) | Native `webauthn`, `otp`, `recovery_codes` |
| Roda or Sinatra app | Rodauth | It is a Roda plugin first |
| API-only Rails with JWT | None of these — build on `has_secure_password` | All three are session-oriented |
| Existing Devise app with custom modules | Keep Devise | Migration cost exceeds benefit |
| Multi-tenant with separate auth rules | Rodauth | Feature enables are per-configuration |
| Internal admin tool, 5 users | Sorcery or `has_secure_password` | Minimum ceremony |
| Auth audit / compliance requirements | Rodauth | Per-feature hooks and logging built in |

## Devise 5 — The Default That Earns Its Place

Install:

```bash
bundle add devise
rails generate devise:install
rails generate devise User
rails db:migrate
```

That produces a `User` model with modules selected in the generator output. Trim them deliberately — every module you keep is a column, a route, and a controller you now own:

```ruby
class User < ApplicationRecord
  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :validatable,
         :confirmable, :lockable, :timeoutable, :trackable
end
```

Routes come from one line:

```ruby
Rails.application.routes.draw do
  devise_for :users, controllers: { sessions: "users/sessions" }
end
```

Customising views is a generator, and it is worth doing before you restyle anything:

```bash
rails generate devise:views users
```

Three Devise realities you should plan for:

**1. Patch cadence is security-critical.** Devise 5.0.3 (March 2026) fixed **CVE-2026-32700**, a race condition in the confirmable "change email" flow that let an attacker confirm an address they did not own. Devise 5.0.4 (May 2026) fixed **CVE-2026-40295**, an open redirect in `FailureApp` via an unvalidated `Referer` header on non-GET session timeouts. Both are the kind of bug that only matters if you are exposed — which you are.

**2. `paranoid` mode changes timing behaviour.** With `config.paranoid = true`, Devise returns a generic "Invalid email or password" message and, in older versions, ran a dummy bcrypt comparison to equalise response time. Verify your version still does; user enumeration by timing is a real attack, not a theoretical one.

**3. Confirmation emails need a working queue.** `confirmable` blocks login until `confirmed_at` is set. If ActionMailer delivery fails silently — wrong SMTP creds, a queue worker that is not running — every new signup is dead on arrival and support gets the tickets. Test the full signup-to-confirm path in staging with real mail delivery before launch.

Devise 5 dropped Ruby < 2.7 and Rails < 7.0, removed the `:bypass` sign-in option in favour of `bypass_sign_in`, and replaced `Devise::TestHelpers` with `Devise::Test::ControllerHelpers`. If you are upgrading from 4.x, those three are the breakages you will actually hit.

## Rodauth — Auth as a Set of Switches

Rodauth is a Roda plugin. In a plain Roda app:

```ruby
require "roda"

class App < Roda
  plugin :sessions, secret: ENV["SESSION_SECRET"]
  plugin :rodauth do
    enable :login, :logout, :create_account, :verify_account,
           :reset_password, :remember, :lockout

    accounts_table :accounts
    db Sequel.postgres("app")

    after_login do
      LOGGER.info "#{account[:email]} logged in from #{request.ip}"
    end

    # Optional but strongly recommended
    enable :otp, :recovery_codes
  end

  route do |r|
    r.rodauth
    r.root { "signed in as #{rodauth.account[:email] || "guest"}" }
  end
end
```

For Rails, the `rodauth-rails` gem wraps the same configuration in an initializer-style class:

```ruby
# app/misc/rodauth_main.rb
class RodauthMain < Rodauth::Rails::Auth
  configure do
    enable :create_account, :verify_account, :login, :logout,
           :reset_password, :remember, :lockout, :otp,
           :recovery_codes, :webauthn, :password_expiration,
           :disallow_password_reuse

    accounts_table :accounts
    password_hash_cost 12
    max_invalid_logins 5

    after_create_account do
      Profile.create!(account_id: account_id)
    end
  end
end
```

The migration generator creates the `accounts` table plus one table per feature (`account_otp_keys`, `account_recovery_codes`, `account_webauthn_keys`, `account_login_failures`). That schema is the part people underestimate: **Rodauth does not stuff 30 columns into your `users` table**, so enabling a feature is a migration that adds a table, and disabling one deletes it cleanly.

What you get that Devise does not ship: `otp` (TOTP, works with any authenticator app), `webauthn` (passkeys and hardware keys), `sms` codes, `password_expiration`, `disallow_password_reuse`, `lockout` with exponential backoff, `account_expiration`, per-feature rate limiting, and `internal_request` for triggering flows from background jobs or the console:

```ruby
rodauth.internal_request.create_account(login: "ops@example.com", password: SecureRandom.hex(20))
```

The cost is configuration density. A full Rodauth setup is 60–120 lines of DSL, and getting the `email_base_url`, `hmac_secret`, and `session_key` right is on you. There is no `rails g` that guesses your intent, and the docs assume you will read the configuration reference rather than copy a blog post.

One migration caveat: Rodauth's default password hash is bcrypt, same algorithm family as Devise, so a **Devise → Rodauth migration can preserve existing hashes** by copying the `encrypted_password` value into `accounts.password_hash` and verifying in place. The account IDs, however, change — every foreign key pointing at `users.id` needs a mapping table or a Rails-level `account_id` column. Plan that before you start.

## Sorcery — The Lightweight Option

Install with the submodules you actually want:

```bash
bundle add sorcery
rails generate sorcery:install remember_me reset_password
# or, to pick submodules explicitly:
rails generate sorcery:install http_basic_auth external remember_me --only-submodules
```

```ruby
class User < ApplicationRecord
  authenticates_with_sorcery!
end
```

```ruby
class SessionsController < ApplicationController
  def create
    if login(params[:email], params[:password])
      redirect_to root_path
    else
      flash.now[:alert] = "Invalid credentials"
      render :new
    end
  end

  def destroy
    logout
    redirect_to root_path
  end
end
```

Controllers get `require_login` as a `before_action`, views get `current_user` and `logged_in?`. Password reset and remember-me are submodules with their own generators, and external providers (OAuth) use `login_at`, `login_from`, and `create_from`.

Sorcery's genuine advantage is **readability**: there is no DSL indirection, so a new developer can trace the login flow in one file. Its genuine disadvantage is that every non-trivial feature — 2FA, WebAuthn, session expiry policies, rate limiting — is something you build. In 2026 that is a hard sell: passkeys are now a baseline expectation for consumer apps, and building WebAuthn correctly is a two-week project with subtle attestation pitfalls.

Also budget for the maintenance gap. Sorcery 0.18.0 shipped in 2026, but the `0.x` version number is honest: APIs can move, and the wiki remains the primary documentation.

## Pitfalls That Actually Bite

**1. bcrypt cost and login latency.** Default cost is 12 in Rodauth, 12 in Devise's `stretches`. A cost-12 bcrypt verify costs roughly 250–350 ms of CPU. Twenty concurrent logins saturate a small VPS. Either accept the latency, raise your Puma thread count, or move to argon2id (Rodauth supports it natively; Devise requires a custom strategy).

**2. Session fixation.** All three rotate the session on login, but only if the session cookie is actually being set by them. If your load balancer terminates TLS and your app is behind two Puma workers without a shared session store, users bounce between workers and appear logged out. Store sessions in Redis or the database, not in cookie-only mode, once you have more than one process.

**3. Remember-me tokens are bearer credentials.** A leaked remember token is a login. Scope them (`rememberable` has `token_ttl`), expire them server-side on password change, and never log them. Devise's `rememberable_value` ends up in logs more often than anyone expects.

**4. Lockout is a denial-of-service vector.** `lockable` with 20 attempts lets anyone lock any account by guessing wrong 20 times. Use progressive delays (Rodauth's `lockout` with exponential backoff) or per-IP rate limiting via `rack-attack` rather than account-level hard locks.

**5. Email as a login identifier is a schema decision.** Changing the login column later means migrating every session, every remember token, and every password reset link. Decide `email` versus `username` versus both before the first migration, and if you need both, Rodauth's `login_column` plus a separate identifier table is the cleaner path.

**6. Test helpers differ, so test suites lie.** Devise uses `sign_in(user)` in controller specs, Rodauth drives the real login form, Sorcery provides `login_user(user)`. A test suite migrated halfway will show green while the actual login path is broken. Rewrite the auth specs first when migrating.

For the layers around auth, our [Ruby ORM comparison](../2026-07-30-ruby-orm-libraries-activerecord-sequel-rom-rb/) covers the ActiveRecord and Sequel models these libraries live on, the [Ruby validation libraries guide](../2026-08-30-ruby-validation-libraries-dry-validation-activemodel-reform-comparison/) covers signup validation, the [Ruby app servers comparison](../2026-09-08-ruby-app-servers-puma-passenger-unicorn-comparison/) explains the concurrency model that determines your bcrypt throughput ceiling, and if you are on Roda rather than Rails, the [Ruby micro-framework comparison](../2026-07-06-ruby-micro-web-frameworks-sinatra-roda-grape/) is the place to start.

## FAQ

**Is Devise still maintained in 2026?**
Yes. Devise 5.0.4 shipped in May 2026 with a security fix, and the 5.0.x series has addressed two CVEs this year. It requires Rails 7.0+ and Ruby 2.7+. What has changed is the pace of feature work — Devise is in maintenance-and-security mode rather than active feature development.

**Can I use Rodauth with Rails instead of Roda?**
Yes, via the `rodauth-rails` gem, which mounts Rodauth as a Rack app inside Rails and provides generators and a `Rodauth::Rails::Auth` base class. The Rails integration is officially supported and actively maintained, though it is a separate gem from `rodauth` itself.

**Do all three store passwords with bcrypt?**
Devise and Sorcery default to bcrypt. Rodauth defaults to bcrypt but supports argon2 and any custom `password_hash` implementation. Any of them can be extended, but only Rodauth makes it a configuration option rather than a custom strategy class.

**Which is easiest to add passkeys to?**
Rodauth, by a wide margin — `enable :webauthn` plus a migration for `account_webauthn_keys`. Devise and Sorcery require third-party gems or hand-written WebAuthn ceremony code including challenge storage, attestation verification, and credential management.

**How hard is migrating from Devise to Rodauth?**
Mechanically: copy `encrypted_password` into `password_hash` (both bcrypt), keep the cost factor, and map user IDs to new account IDs. Operationally: every foreign key to `users.id`, every `current_user` helper, and every auth spec needs attention. Teams typically budget one to three weeks for a mid-sized app, with a dual-run period.

**What about API-only applications?**
None of these three is the right tool. Use `has_secure_password` with signed tokens, or an OAuth2/OIDC provider. Devise and Rodauth both assume browser sessions, CSRF protection, and HTML forms; fighting that for a JSON API costs more than writing the token layer yourself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ruby Authentication in 2026: Devise vs Rodauth vs Sorcery",
  "description": "Devise, Rodauth, and Sorcery compared for Ruby and Rails authentication: real install commands, 2FA and passkey support, 2026 CVEs, migration paths, and pitfalls.",
  "datePublished": "2026-11-01",
  "dateModified": "2026-11-01",
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
