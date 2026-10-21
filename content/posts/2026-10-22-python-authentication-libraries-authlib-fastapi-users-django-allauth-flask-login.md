---
title: "Python Auth in 2026: Authlib vs FastAPI-Users vs django-allauth vs Flask-Login"
date: "2026-10-22"
tags: ["python", "authentication", "security", "web-development"]
draft: false
---

Most Python authentication incidents are not cryptography failures. They are integration failures: a session cookie that outlives a password reset, a JWT that nobody can revoke, a social login flow that silently creates duplicate accounts. The library you pick decides whether those problems are solved for you or handed to you.

This guide compares the four libraries that actually carry production Python auth in 2026 — **Authlib**, **FastAPI-Users**, **django-allauth**, and **Flask-Login** — with live repository data, working configuration, and the failure modes each one invites.

## TL;DR: Pick By Framework, Then By Job

- **Django project, any size** → **django-allauth**. It is the only option here with mature social login, MFA, and account lifecycle in one package.
- **FastAPI or Starlette** → **FastAPI-Users** if you want users, registration, and JWT wired in a day; **Authlib** if you need to *issue* OAuth2/OIDC tokens, not just consume them.
- **Flask** → **Flask-Login** for session-based auth plus **Authlib** for any OAuth client work. Do not try to make Flask-Login do social login.
- **You are building the identity provider** (your own OIDC server for other apps) → **Authlib**, full stop.
- **You only need to verify tokens issued elsewhere** → skip all four and use **PyJWT** with a cached JWKS client.

The honest summary: these libraries are not really competitors. They solve different problems, and picking the wrong category is the expensive mistake.

## Comparison Table (Live Repository Data, October 2026)

| Project | Stars | Last commit | Model | Social login | MFA built in | Can act as OIDC provider | Framework fit | License |
|---|---|---|---|---|---|---|---|---|
| **Authlib** (`lepture/authlib`) | 5,440 | 2026-10-20 | OAuth2/OIDC client + server, JOSE | Yes (client side) | No | **Yes** | Framework agnostic | BSD-3 |
| **FastAPI-Users** (`fastapi-users/fastapi-users`) | 6,255 | 2026-08-17 | JWT or database sessions | Yes (OAuth routers) | No | No | FastAPI | MIT |
| **django-allauth** (`pennersr/django-allauth`) | 10,381 | 2026-10-20 | Django sessions | **Yes, 100+ providers** | **Yes (TOTP, recovery codes)** | No | Django | MIT |
| **Flask-Login** (`maxcountryman/flask-login`) | 3,678 | 2026-10-07 | Signed session cookie | No | No | No | Flask | MIT |
| **PyJWT** (`jpadilla/pyjwt`) | 5,720 | 2026-10-19 | Stateless tokens only | No | No | No | Any | MIT |

Read that table as a warning about scope. django-allauth's 10,381 stars come from doing one narrow thing inside one framework extremely well. Authlib's 5,440 come from being the only mature Python library that lets *you* be the OAuth2 server. Neither is a drop-in replacement for the other.

## Decision Matrix: Match the Job, Not the Star Count

| Your situation | Use | Why |
|---|---|---|
| Django app that needs Google/GitHub login next week | django-allauth | Provider list is already written; adding a provider is a settings change |
| Django app with compliance pressure for MFA | django-allauth + `allauth.mfa` | TOTP, recovery codes, and WebAuthn are maintained in-tree |
| FastAPI service with email/password + JWT | FastAPI-Users | Users model, routers, and password reset come prebuilt |
| FastAPI service that must issue tokens to third-party apps | Authlib | Authorization code + PKCE, client registration, JWKS endpoint |
| Flask app with server-rendered pages | Flask-Login | Small, stable, and does session auth correctly |
| Microservice that only validates tokens | PyJWT + JWKS cache | No user database, no session store, no framework coupling |
| Mixed stack where one service is the IdP | Authlib as IdP, others validate | One source of truth for identities |

## Authlib — When You Are the Identity Provider

Authlib is the only library in this comparison that can run an authorization server. If your architecture has three internal apps and you are tired of duplicating user tables, Authlib turns one of them into an OIDC provider and the other two become clients.

The minimal server registration looks like this (from the project's own Flask OAuth2 examples):

```python
# oauth2_server.py — Authlib as an OIDC provider
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import grants
from authlib.oidc.core import UserInfo, CodeIDToken
from flask import Flask

app = Flask(__name__)
server = AuthorizationServer(app)

class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def authenticate_user(self, username, password):
        user = User.query.filter_by(email=username).first()
        if user and user.check_password(password):
            return user
        return None

server.register_grant(PasswordGrant)
server.register_grant(grants.AuthorizationCodeGrant)
```

Client-side usage is where most teams start, and it is pleasantly short:

```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)
oauth.register(
    name="github",
    client_id=os.environ["GH_CLIENT_ID"],
    client_secret=os.environ["GH_CLIENT_SECRET"],
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)
```

**Strengths:** correct PKCE support, JOSE primitives (JWS, JWE, JWK) in one dependency, and a real OIDC discovery document. **Weaknesses:** it is a toolkit, not a product. You write the user model, the consent screen, and the token storage. Budget a week, not an afternoon.

## FastAPI-Users — Batteries Included, With Sharp Edges

FastAPI-Users is the pragmatic choice for a FastAPI service that needs email/password auth today. It ships a `SQLAlchemyUserDatabase` adapter, ready-made routers, and pluggable transports (JWT or database-backed sessions).

```python
# users.py
from fastapi_users import FastAPIUsers, BaseUserManager
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt")
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth")
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth")
```

**The sharp edge:** default JWT strategy is stateless, so *logout does not revoke anything*. If your threat model includes stolen tokens, switch to the database strategy or maintain a token version column that you bump on password change. This one detail causes more real-world incidents than any other in this list.

## django-allauth — The Django Default That Earned It

django-allauth is what "just use the framework" looks like when the framework's ecosystem is healthy. Social providers are declared in settings, email verification and account lifecycle are handled, and MFA is a first-party app.

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "allauth.mfa",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
SOCIALACCOUNT_PROVIDERS = {
    "github": {"SCOPE": ["read:user", "user:email"], "VERIFIED_EMAIL": True},
}
```

MFA enrollment then lives behind one URL include and one settings flag (`MFA_TOTP_ISSUER`, `MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]`). **Strength:** account lifecycle is the hard part of auth and this package has already done it — email confirmation, dangling social accounts, reauthentication for sensitive views. **Weakness:** it is Django-shaped. If you leave Django, none of it transfers.

## Flask-Login — Sessions Only, and That Is the Point

Flask-Login has one job: put a user ID in a signed session cookie and load the user on each request. It is small enough to audit in an afternoon, which is exactly why it is still the standard.

```python
from flask_login import LoginManager, login_required, login_user

login_manager = LoginManager(app)
login_manager.session_protection = "strong"   # binds session to client fingerprint
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))

@app.post("/login")
def login():
    user = User.query.filter_by(email=request.form["email"]).first()
    if user and user.check_password(request.form["password"]):
        login_user(user, remember=False)
        return redirect(url_for("dashboard"))
    return "Invalid credentials", 401
```

**Do not** attempt social login with Flask-Login. Use Authlib for the OAuth dance, then call `login_user()` with the resolved account. **Do not** store roles or permissions in the session either — they go stale the moment an admin changes them.

## Stateless Tokens: Where PyJWT Fits

If a service only needs to verify tokens minted by your identity provider, adding a full auth library is over-engineering. A cached JWKS client plus PyJWT is correct and fast:

```python
import jwt
from jwt import PyJWKClient

jwks = PyJWKClient("https://id.example.com/.well-known/jwks.json", cache_keys=True)

def verify(token: str) -> dict:
    key = jwks.get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience="internal-api",
        issuer="https://id.example.com",
        options={"require": ["exp", "iat", "aud", "iss"]},
    )
```

Two non-negotiables: pin `algorithms` to an explicit list (never `algorithms=None`, never a list containing `none`), and validate `aud` and `iss`. Skipping either is the classic JWT vulnerability.

## Security Pitfalls That Bite Every Python Auth Project

**Session fixation after login.** Regenerate the session ID on privilege change. Flask does this on `login_user` only when `session_protection` is configured correctly; Django rotates the session key automatically in `login()`. Verify it in a test.

**Password hashing defaults drift.** Argon2id with sane parameters is the 2026 default. Django 5.x prefers Argon2 when `argon2-cffi` is installed; passlib projects should check that their pinned bcrypt work factor is still adequate. Do not invent your own KDF chain.

**Password reset does not invalidate sessions.** A reset that changes the hash but leaves existing cookies valid is a live vulnerability. Either bump a `session_version` column checked in your user loader, or use server-side sessions you can delete.

**Cookie flags are not optional.** `Secure`, `HttpOnly`, and `SameSite=Lax` (or `Strict` for admin surfaces) on every auth cookie. Behind a reverse proxy, make sure the framework knows the original scheme or `Secure` may be silently dropped.

**Duplicate accounts from social login.** Enable email verification and link social identities to existing verified emails only. Otherwise "Sign in with GitHub" quietly creates a second account for a user who already registered with a password.

**Missing rate limits.** Login and password-reset endpoints need per-IP *and* per-account throttling. A credential-stuffing run against an unthrottled endpoint will succeed; a library cannot fix an absent policy.

## Migration and Coexistence Notes

Moving between these libraries is usually a session migration, not a data migration. The user rows survive; the session format does not. If you run two frameworks side by side during a rewrite, put both behind one identity provider (Authlib) and let each app validate tokens — trying to share session cookies across frameworks costs more than the rewrite.

For token-based services, support two signing keys during rotation (publish both in JWKS, sign with the new one) so that validators never see an unknown `kid`. For Django projects adding MFA to an existing user base, ship recovery codes *before* enforcing enrollment, or your support queue becomes the recovery mechanism.

Whichever library you choose, keep the configuration in version control and cover three flows with tests: login, logout-with-revocation, and password reset. Those three catch the majority of integration mistakes before they reach production.

If you are tightening the rest of the stack at the same time, our [Python configuration library comparison](../2026-06-22-python-configuration-libraries-pydantic-dynaconf-decouple-environs-guide/) covers how to load secrets and keys safely, the [Python cryptography library guide](../2026-07-01-python-cryptography-libraries-pyca-pycryptodome-pynacl/) explains the primitives behind token signing, and the [Python rate limiting comparison](../2026-07-02-python-rate-limiting-limits-slowapi-flask-limiter-django-ratelimit/) covers the throttling layer that every login endpoint needs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python Auth in 2026: Authlib vs FastAPI-Users vs django-allauth vs Flask-Login",
  "description": "A hands-on comparison of Python authentication libraries in 2026: Authlib, FastAPI-Users, django-allauth, Flask-Login and PyJWT, with live repository data, working configuration and security pitfalls.",
  "datePublished": "2026-10-22",
  "dateModified": "2026-10-22",
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

### Which Python authentication library should a new FastAPI project use in 2026?

Use **FastAPI-Users** if you need email/password registration, password reset, and JWT issuance without writing glue code. Use **Authlib** instead if the service must act as an OAuth2/OIDC provider for other applications. Many teams run both: Authlib for the identity provider, FastAPI-Users inside services that need local accounts.

### Is django-allauth enough on its own for a production Django app?

For most Django apps, yes. django-allauth covers registration, email verification, social providers, and MFA in one maintained package. You still need to add rate limiting on login endpoints, enforce `Secure`/`HttpOnly` cookie flags behind your proxy, and test session invalidation after password resets.

### Can Flask-Login handle OAuth or social login?

No. Flask-Login only manages session-based login state. Pair it with **Authlib** for the OAuth client flow, then call `login_user()` once you have resolved the provider account to a local user. Trying to bolt provider callbacks onto Flask-Login directly leads to hand-rolled state handling and CSRF gaps.

### How do I revoke a JWT when a user logs out?

You cannot revoke a stateless JWT without extra state. Choose one: (a) short access tokens (5–15 minutes) plus a refresh token you can delete, (b) a `session_version` column compared on every request, or (c) server-side sessions. If immediate revocation is a hard requirement, do not use pure stateless tokens.

### Do I still need PyJWT if I already use Authlib?

Usually not — Authlib includes JOSE support for decoding and verifying tokens. PyJWT earns its place in small services that only validate tokens from an external issuer and want a single, tiny dependency. Never run two different verification paths against the same tokens; pick one and pin the accepted algorithms explicitly.

### What is the minimum test suite for authentication?

Cover four flows as integration tests: successful login, failed login with rate limiting asserted, logout with token or session invalidation asserted, and password reset followed by a request using the pre-reset session. These catch the integration bugs that unit-testing a hashing function never will.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
