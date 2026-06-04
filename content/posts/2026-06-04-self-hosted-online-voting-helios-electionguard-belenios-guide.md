---
title: "Self-Hosted Online Voting Systems: Helios vs ElectionGuard vs Belenios Comparison"
date: "2026-06-04"
tags: ["online-voting", "secure-voting", "election-systems", "helios", "electionguard", "belenios", "self-hosted", "cryptography"]
draft: false
---

## Introduction

Secure online voting is one of the hardest problems in computer science — and one of the most consequential. Whether you're running a student government election, a corporate board vote, an HOA ballot, or a union contract ratification, the platform handling those votes must guarantee ballot secrecy, prevent tampering, and produce publicly verifiable results. Open-source cryptographic voting systems solve this by making the entire election process mathematically auditable.

In this guide, we compare three leading open-source verifiable voting platforms: **Helios** (pioneered by cryptographer Ben Adida), **Microsoft ElectionGuard** (backed by Microsoft Research), and **Belenios** (developed by French academic institutions). Each provides end-to-end verifiability — meaning voters can confirm their vote was counted correctly without trusting the server operator.

## Feature Comparison Table

| Feature | Helios | ElectionGuard | Belenios |
|---------|--------|---------------|----------|
| **Language** | Python (Django) | Python | OCaml |
| **GitHub Stars** | 903 | 167 | 150 |
| **License** | GPL 3.0 | MIT | AGPL 3.0 |
| **Cryptographic Scheme** | Benaloh homomorphic tallying | ElGamal + Non-Interactive Zero-Knowledge Proofs | Helios-inspired + threshold decryption |
| **Verifiability** | End-to-end (individual + universal) | End-to-end (individual + universal) | End-to-end (individual + universal) |
| **Ballot Secrecy** | Homomorphic encryption | Homomorphic encryption | Homomorphic encryption + mixnets |
| **Threshold Decryption** | Single trustee | Multiple trustees (threshold) | Multiple trustees (threshold) |
| **Voter Authentication** | Email + password, Google OAuth | External (bring your own auth) | CAS, SAML, OAuth, password |
| **Admin Interface** | Web-based (Django admin) | API-based (no built-in UI) | Web-based (custom UI) |
| **Audit Trail** | Public bulletin board | Public bulletin board + verifier SDK | Public bulletin board + W3C-compatible |
| **Multi-Language** | Limited | Unicode-capable | English + French |
| **Deployment** | Django app + PostgreSQL | Python SDK (BYOFrontend) | OCaml binary + PostgreSQL |
| **Active Development** | Yes (maintained) | Yes (Microsoft Research) | Yes (INRIA/CNRS) |

## Helios — The Pioneer of Internet Voting

[Helios](https://heliosvoting.org/) was created in 2008 by cryptographer Ben Adida and remains the most widely deployed open-source verifiable voting system. It was used by the International Association for Cryptologic Research (IACR) for their board elections, by universities for faculty senates, and by numerous organizations worldwide. Helios introduced the concept of "open-audit voting" — the idea that any observer can independently verify the election outcome without trusting the server.

**Key strengths:**
- **Proven track record**: 16+ years of deployment in real elections, extensive academic analysis, and multiple security audits
- **Simplicity**: Clean, intuitive web interface for election administrators and voters. Create an election in minutes with a step-by-step wizard
- **Benaloh challenge**: Voters can cryptographically verify that their encrypted ballot matches their intended choices before casting — a feature unique to Helios
- **Public bulletin board**: All encrypted ballots are published on a public append-only bulletin board, enabling anyone to independently tally the election
- **Lightweight deployment**: Runs on modest hardware; a basic Django application with PostgreSQL backend

**Installation & Deployment:**

```bash
# Clone Helios repository
git clone https://github.com/benadida/helios-server.git
cd helios-server

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure database
cp helios/settings.py.example helios/settings.py
# Edit settings.py: set DATABASE_URL, SECRET_KEY, EMAIL settings

# Run migrations and start
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  helios:
    build: .
    container_name: helios
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://helios:secure_pass@helios_db:5432/helios
      - SECRET_KEY=generate_a_cryptographically_random_64_char_string
      - EMAIL_HOST=smtp.example.com
      - EMAIL_PORT=587
      - EMAIL_USER=notifications@example.com
      - EMAIL_PASSWORD=your_smtp_password
      - HELIOS_SITE_URL=https://vote.example.com
    depends_on:
      - helios_db
    networks:
      - helios_net

  helios_db:
    image: postgres:16-alpine
    container_name: helios_db
    restart: unless-stopped
    volumes:
      - helios_pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=helios
      - POSTGRES_USER=helios
      - POSTGRES_PASSWORD=secure_pass
    networks:
      - helios_net

networks:
  helios_net:
    driver: bridge

volumes:
  helios_pgdata:
```

## Microsoft ElectionGuard — SDK-Based Voting Infrastructure

[ElectionGuard](https://www.electionguard.vote/) takes a fundamentally different approach from Helios. Rather than providing a complete voting application, ElectionGuard is a **software development kit (SDK)** — a cryptographic library that any voting system vendor or developer can integrate into their own frontend. Backed by Microsoft Research and developed in partnership with voting system manufacturers, ElectionGuard aims to make end-to-end verifiability a standard component of all voting systems.

**Key strengths:**
- **Frontend-agnostic**: Integrate ElectionGuard into any existing voting application — web, mobile, or hardware-based. You build the user interface; ElectionGuard handles the cryptography
- **Independent verifier SDK**: A separate verifier application (written in any language) can independently confirm that an election's encrypted tally matches the published results — no trust in the voting server required
- **Threshold decryption with guardians**: Multiple trustees each hold a share of the decryption key. A configurable threshold (e.g., 3 of 5) must cooperate to decrypt results, preventing any single party from accessing individual ballots
- **Hardware-backed key protection**: ElectionGuard supports TPM and HSM integration for production deployments requiring hardware-grade key security
- **Python + multi-language bindings**: Core SDK in Python with community ports to Rust, C#, and TypeScript

**Using ElectionGuard in a Python voting application:**

```python
from electionguard.election import CiphertextElectionContext
from electionguard.ballot import PlaintextBallot
from electionguard.encrypt import encrypt_ballot
from electionguard.tally import tally_ballots

# Set up election parameters
election = setup_election(
    number_of_guardians=5,
    quorum=3,
    manifest=election_manifest
)

# Encrypt a voter's ballot
encrypted_ballot = encrypt_ballot(
    ballot=plaintext_ballot,
    context=election_context,
    public_key=guardian_public_key
)

# After election closes, tally all encrypted ballots
tally = tally_ballots(
    encrypted_ballots=all_ballots,
    context=election_context
)

# Decrypt results with guardian cooperation
decrypted_tally = decrypt_tally(
    tally=tally,
    guardian_shares=guardian_shares
)
```

ElectionGuard's SDK approach means there is no standard "docker-compose up and vote" experience — you or your development team must build the voting frontend. This makes ElectionGuard ideal for organizations that already have a voting platform and want to add verifiability, but less suitable for groups seeking an out-of-the-box solution.

## Belenios — Academic Rigor with Real-World Deployments

[Belenios](https://www.belenios.org/) was developed by researchers at INRIA (French National Institute for Research in Digital Science and Technology) and CNRS. It takes Helios's cryptographic foundations and adds practical improvements for real-world elections: threshold decryption (no single-person control over results), a modern web interface, and support for complex ballot types including ranked-choice and cumulative voting.

**Key strengths:**
- **Threshold decryption by design**: Unlike Helios's single-trustee model, Belenios requires multiple trustees to cooperate for decryption — essential for elections where no single party should control the outcome
- **Complex ballot support**: Supports single-vote, multi-vote (approval voting), ranked-choice (Condorcet/Schulze methods), and cumulative voting ballot types
- **Credential-based authentication**: Voters receive unique, anonymous credentials that allow them to vote without revealing their identity — the server knows a valid credential was used but not who cast which ballot
- **W3C Verifiable Credentials compatibility**: Belenios election results can be formatted as W3C Verifiable Credentials, enabling integration with digital identity ecosystems
- **Production deployments**: Used by French universities, CNRS research institutes, and several European organizations for statutory elections

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  belenios:
    image: beleniosplatform/belenios:latest
    container_name: belenios
    restart: unless-stopped
    ports:
      - "8081:8081"
    volumes:
      - belenios_data:/var/lib/belenios
      - belenios_config:/etc/belenios
    environment:
      - BELENIOS_DB_HOST=belenios_db
      - BELENIOS_DB_NAME=belenios
      - BELENIOS_DB_USER=belenios
      - BELENIOS_DB_PASSWORD=secure_db_pass
      - BELENIOS_SITE_URL=https://vote.example.com
      - BELENIOS_ADMIN_EMAIL=admin@example.com
    depends_on:
      - belenios_db
    networks:
      - belenios_net

  belenios_db:
    image: postgres:16-alpine
    container_name: belenios_db
    restart: unless-stopped
    volumes:
      - belenios_pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=belenios
      - POSTGRES_USER=belenios
      - POSTGRES_PASSWORD=secure_db_pass
    networks:
      - belenios_net

networks:
  belenios_net:
    driver: bridge

volumes:
  belenios_data:
  belenios_config:
  belenios_pgdata:
```

After starting, access `http://localhost:8081` to complete the setup wizard, configure your organization, and create your first election.

## Comparison: Which Voting System Fits Your Use Case?

- **Choose Helios** if you need a battle-tested, complete voting application with a polished web interface. It is the simplest to deploy and operate — ideal for university student government, professional association board elections, and organizational referenda with a single election administrator.
- **Choose ElectionGuard** if your organization already has a voting platform and needs to add cryptographically verifiable tallying. It is a developer SDK, not an application — expect to invest engineering time building or integrating the voter-facing interface. Best for voting system vendors and organizations with existing custom voting infrastructure.
- **Choose Belenios** if you need threshold decryption (multiple trustees must cooperate to reveal results), support for complex ballot types (ranked-choice, cumulative), or plan to integrate with European digital identity systems. Its academic backing and production deployments at French institutions make it the strongest choice for statutory elections requiring multi-party oversight.

For related reading, see our [self-hosted survey platforms guide](../2026-05-09-self-hosted-survey-platforms-limesurvey-vs-kobotoolbox-vs-formbricks-guide/) for less formal polling needs, and our [secrets management comparison](../2026-04-23-mozilla-sops-vs-git-crypt-vs-age-self-hosted-secrets-encryption-git-guide-2026/) for cryptographic key management infrastructure that supports secure election administration.

## FAQ

### Is online voting actually secure enough for real elections?

Cryptographic voting systems like Helios, ElectionGuard, and Belenios provide a security property called **end-to-end verifiability**, which is fundamentally different from the "black box" voting systems used in commercial electronic voting. With end-to-end verifiability, every voter receives a cryptographic receipt they can use to confirm their vote was included in the tally, and any observer can independently recompute the election result from the published encrypted ballots. This does not make online voting immune to all attacks — client-side malware remains a concern — but it eliminates trust in the server operator. For low-stakes elections (university boards, cooperatives, unions), these systems provide security far beyond commercial survey tools.

### What prevents someone from voting multiple times?

These platforms use different approaches. Helios and Belenios maintain an election-specific voter roll — only registered voters with unique credentials can cast ballots, and each credential can be used exactly once. The public bulletin board shows the total number of ballots cast, allowing anyone to verify that the count matches the voter roll size. ElectionGuard leaves authentication to the frontend application, allowing integration with existing identity systems (OAuth, SAML, LDAP). None of these platforms reveal who voted for what — the cryptographic separation between authentication and ballot encryption preserves vote secrecy.

### Can these systems handle ranked-choice or preferential voting?

Belenios natively supports ranked-choice voting through the Condorcet-Schulze method, as well as approval voting (select all candidates you approve of) and cumulative voting (distribute points among candidates). Helios supports single-vote and multi-vote elections but does not have built-in ranked-choice tallying. ElectionGuard supports arbitrary ballot formats defined by the manifest file — ranked-choice, score voting, and other methods can be implemented through the SDK.

### How are election results audited?

All three platforms publish the complete set of encrypted ballots on a public bulletin board. After the election closes, anyone can download these ballots and run the tally algorithm independently. For Helios, the auditor runs `helios-verifier` with the election data and receives a confirmation or rejection of the published result. ElectionGuard provides a separate verifier SDK that recomputes the tally from encrypted ballots and compares it to the announced result. Belenios includes a `belenios-tool verify` command that performs the same independent verification. The key insight: if the published result and the independent recomputation match, the election was tallied correctly — regardless of whether you trust the server operator.

### What hardware resources do these voting systems require?

All three are lightweight server applications. Helios runs comfortably on 512MB RAM with PostgreSQL, handling elections with up to 50,000 voters on modest hardware (2 vCPU, 1GB RAM). Belenios requires similar resources — the OCaml binary is highly efficient. ElectionGuard's resource usage depends on the frontend application built on top of it; the SDK itself processes ballots efficiently. Cryptographic operations (ballot encryption, tallying) are CPU-intensive but short-lived — a 10,000-voter election tally completes in under 30 seconds on modern hardware. For production deployments, 2 vCPU and 2GB RAM provide comfortable headroom for concurrent voter access.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Online Voting Systems: Helios vs ElectionGuard vs Belenios Comparison",
  "description": "Compare three open-source end-to-end verifiable voting systems — Helios, Microsoft ElectionGuard, and Belenios — with Docker Compose deployment, cryptographic comparison, and election security analysis for organizational and institutional voting.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform, where you can bet on everything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've made good returns predicting tech-related event outcomes. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)
