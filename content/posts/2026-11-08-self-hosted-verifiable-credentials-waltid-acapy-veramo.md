---
title: "walt.id vs ACA-Py vs Veramo in 2026: Which Self-Hosted Verifiable Credential Stack Should You Run?"
date: "2026-11-08"
tags: ["digital-identity", "self-hosted", "verifiable-credentials", "privacy", "authentication"]
cover: "/img/screenshots/waltid-banner.jpg"
draft: false
---

The EU's digital identity deadline is not a thought experiment anymore. Under eIDAS 2.0, member states must give citizens a working EU Digital Identity Wallet by the end of 2026 — which means thousands of organisations suddenly need to *issue* and *verify* digital credentials from their own infrastructure. Not from a vendor's multi-tenant SaaS, and not from a demo playground that disappears next quarter.

The problem: "verifiable credentials" is a stack of half-overlapping specifications (W3C VC Data Model 2.0, SD-JWT VC, mdoc/mDL, OpenID4VCI 1.0, OpenID4VP 1.0, DIDComm v2), and the three projects that matter most — **walt.id**, **ACA-Py** and **Veramo** — picked different roads through that mess. Picking wrong means months of rewriting signing logic and a wallet that interoperates with nobody.

I ran all three in containers, read their compose files, and compared what you actually get after `docker compose up`.

## TL;DR / Quick Verdict

- **You need OpenID4VCI + OpenID4VP today, with mDL and SD-JWT support and a clean HTTP API** → **walt.id Community Stack**. Best eIDAS 2.0 story, ready-made issuer/verifier/wallet services, Apache-2.0.
- **You are building a product in TypeScript, need credentials wired into your own business logic, and want an SDK rather than a platform** → **Veramo**. It is a framework, not a service — you write the agent.
- **You need DIDComm messaging between agents, ledger-anchored DIDs, or an Aries-compatible ecosystem with mobile wallets** → **ACA-Py**. The most battle-tested agent, but you will write Python the whole way.

If you only remember one line: **walt.id is a product, ACA-Py is a protocol engine, Veramo is a toolkit.** Pick by which of those three shapes your team can ship.

## Comparison Table (live GitHub data, 2026-11-08)

| Dimension | walt.id Community Stack | ACA-Py (Aries Cloud Agent Python) | Veramo |
|---|---|---|---|
| GitHub stars | 325 | 493 | 544 |
| Language | Kotlin (JVM) | Python | TypeScript |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Last commit | 2026-11-07 | 2026-11-03 | 2026-11-06 |
| Ships as | Compose stack: issuer-api2, verifier-api2, wallet-api2 | Single agent container + admin API | npm library / CLI |
| Credential formats | W3C VC, SD-JWT VC, mdoc/mDL | AnonCreds, W3C VC, SD-JWT (via plugins) | W3C VC, SD-JWT (via plugins) |
| Exchange protocols | OID4VCI 1.0, OID4VP 1.0, DIDComm (partial) | DIDComm v2 first-class, OID4VCI/VP via plugins | OID4VCI/VP via plugins |
| DID methods | did:web, did:key, did:jwk, did:ebsi, did:ion, did:indy | did:sov, did:indy, did:web, did:key | did:ethr, did:web, did:key, did:pkh, did:jwk |
| Wallet included | Yes (wallet-api2 + Android app) | No (pairs with mobile wallets) | No |
| Database | PostgreSQL | SQLite / PostgreSQL (or Indy ledger wallets) | Any TypeORM driver |
| Ops complexity | Low (compose file, 6 services) | Medium (provisioning, ledger config, mediator) | High (you build the service) |

## Scenario Decision Matrix

| Use case | Recommended | Why |
|---|---|---|
| eIDAS 2.0 PID / mDL issuance pilot | walt.id | OID4VCI 1.0 + mdoc support out of the box; you edit YAML, not crypto |
| Employee badge wallet for a 5,000-person company | walt.id | Issuer + verifier + wallet in one compose project, minimal glue code |
| Government verifier portal that must accept foreign wallets | walt.id | OID4VP 1.0 conformance is the product's core selling point |
| DIDComm agents exchanging proofs across organisations | ACA-Py | DIDComm v2 is native; mediation and routing are solved problems |
| Indy/AnonCreds credential with zero-knowledge predicates | ACA-Py | AnonCreds is the only stack here with mature range proofs |
| Adding credential signing to an existing Node/TS backend | Veramo | Import a few plugins into your process; no new service to operate |
| Multi-tenant credential SaaS you intend to sell | Veramo or walt.id | Veramo gives you the data model; walt.id gives you tenant APIs |
| Long-lived verifiable "licence to operate" with revocation | Any + StatusList2021 | Revocation is a design decision, not a checkbox — see pitfalls |

## walt.id Community Stack — the "it's already a product" option

walt.id's community edition (325 stars, Apache-2.0, Kotlin) is the only one of the three that ships as a *finished service topology*. Clone the repo and the `docker-compose/` directory gives you:

```bash
git clone https://github.com/walt-id/waltid-identity.git
cd waltid-identity/docker-compose
cp .env .env.local   # edit SERVICE_HOST, POSTGRES_*, and signing keys
docker compose --profile all up -d
```

The compose file defines separate services rather than one monolith: `issuer-api2`, `verifier-api2`, `wallet-api2`, a PostgreSQL instance, and a Caddy reverse proxy that terminates TLS and routes by hostname. Because they are separate images, you can deploy only the issuer in one environment and only the verifier in another — which is exactly what an enterprise segregation-of-duties review will ask for.

What you get that the other two do not: **OID4VCI 1.0 and OID4VP 1.0 as primary interfaces**. That matters because wallets in the field (EUDI reference wallet, Google Wallet's mDL path, commercial wallets) speak OpenID flows. If your issuer only speaks DIDComm, a wallet vendor will tell you to come back later.

Credential formats supported by the issuer API include W3C VC (JWT and LDP), SD-JWT VC for selective disclosure, and mdoc/mDL for mobile driving licences. In practice, SD-JWT is the format you want for anything containing personal data: the holder can reveal birth date without revealing address.

![walt.id wallet credential flow](/img/screenshots/waltid-wallet.jpg "walt.id wallet flow: key generation and DID creation screens from the official Android wallet")

Two honest caveats. First, the community edition is a subset of the commercial product — some multi-tenant and enterprise features live behind a licence, and the docs will quietly point you there. Second, the stack is JVM-heavy: six containers at ~500 MB each means you want a real host, not a 1 GB VPS. Resource budget: 4 vCPU / 8 GB RAM for a pilot with Postgres alongside.

## ACA-Py — the protocol engine that has seen real deployments

ACA-Py (493 stars, Apache-2.0, Python) is the Python implementation of Aries Cloud Agent. It is *not* a credential portal; it is a long-running agent with an admin REST API that speaks DIDComm, holds a wallet, and negotiates credential exchanges.

Minimal run, using the maintained container image referenced by the project's own docs:

```bash
docker run -d --name acapy \
  -p 8030:8030 -p 8031:8031 \
  -e ACAPY_LABEL="issuer-01" \
  -e ACAPY_WALLET_NAME=issuer \
  -e ACAPY_WALLET_KEY=change-me-now \
  -e ACAPY_GENESIS_URL="https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/genesis_files/pool_transactions_genesis" \
  -e ACAPY_ADMIN=[0.0.0.0]=8031 \
  -e ACAPY_ENDPOINT="https://issuer.example.org" \
  ghcr.io/openwallet-foundation/acapy-agent:py3.13-1.6-lts start \
  --inbound-transport http 0.0.0.0 8030 \
  --outbound-transport http
```

Then drive it over the admin API. Every operation is a POST:

```bash
# create a DID anchored to the ledger
curl -X POST http://localhost:8031/wallet/did/create \
  -H 'Content-Type: application/json' \
  -d '{"method":"sov","options":{"key_type":"ed25519"}}'

# register the credential definition (schema first, then cred-def)
curl -X POST http://localhost:8031/credential-definitions \
  -H 'Content-Type: application/json' \
  -d '{"schema_id":"WgWxqztr...:2:membership:1.0","tag":"default"}'
```

The strength here is AnonCreds: zero-knowledge predicates ("prove you are over 18 without revealing your birth date") and link-secret-based revocation have been running in production networks for years. The weakness is that the ecosystem's centre of gravity is still ledger-based DIDs (did:sov / did:indy), which carries operational baggage — a ledger to reach, a mediator to run for mobile holders, and a wallet that implements Aries protocols.

Choose ACA-Py when credential exchange is *agent-to-agent*: supply chain attestations, inter-organisation KYC, or anything where peers must message each other repeatedly. Do not choose it if all you want is "issue a badge via a QR code and verify it on a website" — you will spend a week on mediation before your first credential.

## Veramo — the toolkit you embed

Veramo (544 stars, Apache-2.0, TypeScript) has no service to deploy. You `npm install` a set of plugins into your existing Node backend and build an agent object. That is both the appeal and the trap.

```typescript
import { createAgent } from '@veramo/core'
import { Agent } from '@veramo/core'
import { DIDManager } from '@veramo/did-manager'
import { KeyManager } from '@veramo/key-manager'
import { CredentialPlugin } from '@veramo/credential-w3c'
import { KeyStore, DIDStore, DataStore, DataStoreORM } from '@veramo/data-store'
import { WebDIDProvider } from '@veramo/did-provider-web'

const agent = createAgent({
  plugins: [
    new KeyManager({ store: new KeyStore(db), kms: { local: new MemoryKeyStore() } }),
    new DIDManager({
      store: new DIDStore(db),
      defaultProvider: 'did:web',
      providers: { 'did:web': new WebDIDProvider({ defaultKms: 'local' }) },
    }),
    new CredentialPlugin(),
    new DataStore(db),
    new DataStoreORM(db),
  ],
})

const credential = await agent.createVerifiableCredential({
  credential: {
    issuer: { id: 'did:web:issuer.example.org' },
    issuanceDate: new Date().toISOString(),
    credentialSubject: { id: 'did:key:z6Mk...', membership: 'gold' },
  },
  proofFormat: 'jwt',
})
```

That is the whole appeal: credentials become rows in your database and calls in your service layer. No new container, no new network hop, no second auth system. Teams building a credential feature *inside* a product (ticketing, HR, education) usually find this faster than adopting a platform.

The cost is that you own everything the platform would have given you: key custody (you must configure a KMS plugin properly, not the memory store in the snippet above), revocation lists, status endpoints, OID4VCI endpoints, tenant isolation, and upgrades when a plugin's peer dependency drifts. Veramo is a library with a healthy release cadence (last commit 2026-11-06) but it is not a turnkey issuer.

## Pitfalls That Bite in Production

**1. DID method choice is nearly irreversible.** did:web is trivial to deploy (host a `did.json` over HTTPS) but ties the identifier to your DNS name — change domains and every credential you issued points at a dead identifier. did:key cannot rotate keys. did:indy needs a ledger. Write this decision down before your first issuance; migrating 50,000 credentials later is a project, not a task.

**2. Credential format churn is real.** SD-JWT VC and mdoc are both "the future" depending on who you ask, and wallet support differs by country. Issue in a format your target wallets already accept, and keep the signing keys in a KMS so you can re-issue in a second format later without changing custody.

**3. Verification is not authentication.** A verified credential proves the issuer signed a claim. It does not prove the person in front of you is the holder unless you also bind the holder key (holder binding / `cnf` claim) and check it. Half the "wallet login" implementations I have audited skip this.

**4. Revocation is a separate service.** StatusList2021 or Token Status List means publishing a signed bitstring at a stable URL and refreshing it on a schedule. Forget the refresh cron and your revoked credentials stay valid forever.

**5. Trust registries are the unglamorous blocker.** Your verifier must decide *which issuers to trust*. walt.id ships trust-list configuration; ACA-Py and Veramo leave it to you. Budget time for this — it is where pilots die.

**6. X.509 and clock skew.** mDL and several OID4VP flows lean on certificate chains. In containers, a clock drift of 90 seconds breaks signature validation with an error message that mentions none of this.

## FAQ

**Is walt.id really open source, or is it open-core?**
The Community Stack in `walt-id/waltid-identity` is Apache-2.0 and includes issuer, verifier and wallet APIs. The commercial edition adds enterprise features (multi-tenancy, HSM integrations, support). For a single-organisation pilot the community edition is sufficient; read the feature matrix before promising a client multi-tenant behaviour.

**Can I use ACA-Py without an Indy ledger?**
Yes. Recent releases support did:web, did:key and non-ledger AnonCreds, but you lose the ledger-anchored revocation registry that most Aries deployments rely on. If you are starting greenfield and do not need ZK predicates, walt.id or Veramo will get you to production faster.

**Which stack works with the EUDI reference wallet?**
walt.id positions its issuer/verifier around OID4VCI 1.0 and OID4VP 1.0, which is what EUDI-aligned wallets implement. ACA-Py can reach the same endpoints via plugins but is DIDComm-first. Test against the actual wallet build you plan to support — conformance claims age quickly.

**Do I need a blockchain for verifiable credentials?**
No. Only did:ethr, did:indy and did:pkh style identifiers touch a ledger. did:web plus a KMS gives you a fully self-hosted, ledger-free issuer that any OID4VP verifier can resolve.

**How much RAM does a minimal pilot need?**
walt.id with the full compose profile: ~8 GB (six JVM containers plus Postgres). ACA-Py alone: ~1 GB. Veramo inside an existing Node service: whatever your service already uses.

**What about key custody?**
None of the three will save you from storing seeds in environment variables. Use a KMS plugin (PKCS#11, Vault Transit, cloud KMS) and treat the credential signing key as a crown jewel — it can mint identity claims for your entire user base.

## Related reading

If you are still assembling the authentication layer around all this, our [passkey and WebAuthn self-hosting guide](../self-hosted-passkey-webauthn-authentication-solutions-2026/) covers the authenticator side, and the [Zitadel vs Ory vs Keycloak IAM comparison](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) covers OIDC session management. For hardware-token MFA in the same stack, see [privacyIDEA vs LinOTP](../privacyidea-vs-linotp-self-hosted-mfa-server-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "walt.id vs ACA-Py vs Veramo in 2026: Which Self-Hosted Verifiable Credential Stack Should You Run?",
  "description": "Hands-on comparison of walt.id, ACA-Py and Veramo for self-hosted verifiable credential issuance and verification, including deployment commands, protocol support and production pitfalls.",
  "datePublished": "2026-11-08",
  "dateModified": "2026-11-08",
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
