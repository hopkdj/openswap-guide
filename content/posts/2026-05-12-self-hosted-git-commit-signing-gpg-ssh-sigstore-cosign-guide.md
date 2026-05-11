---
title: "Self-Hosted Git Commit Signing: GPG vs SSH vs Sigstore Cosign Guide 2026"
date: "2026-05-12"
tags: ["git", "security", "supply-chain", "code-signing"]
draft: false
---

Every commit pushed to a shared repository carries an implicit claim about authorship, but without cryptographic verification, anyone can forge another developer's identity in the commit log. Git commit signing solves this by attaching a cryptographic signature to each commit, proving that the code originated from a trusted key holder.

In this guide, we compare three approaches to Git commit signing — the traditional GPG/PGP method, the modern SSH-based signing built into Git 2.34+, and Sigstore cosign for keyless, cloud-native signing — helping you choose the right approach for your team and self-hosted infrastructure.

## Why Sign Git Commits

Unsigned commits create several risks in collaborative development:

- **Identity forgery**: Any developer can commit with any name and email address, making it impossible to verify who actually wrote the code
- **Supply chain attacks**: Malicious actors can inject code under the guise of a trusted maintainer, as demonstrated by the 2024 xz Utils backdoor incident
- **Compliance requirements**: Industries like healthcare, finance, and government increasingly require cryptographic proof of code provenance
- **Merge integrity**: Signed commits prevent tampering during the merge process, ensuring the code you review is exactly what gets deployed

For teams running self-hosted Git platforms like Gitea, Forgejo, or GitLab, local signing verification provides an additional layer of trust that doesn't depend on third-party services.

## GPG/PGP Commit Signing

GPG (GNU Privacy Guard) is the traditional and most widely supported method for signing Git commits. It uses OpenPGP keys to create detached signatures that Git embeds in each commit object.

### How It Works

When you sign a commit with GPG, Git creates a cryptographic hash of the commit content and signs it with your private key. The signature is stored alongside the commit, and platforms like GitHub, GitLab, and Gitea can verify it using your public key.

### Setup

```bash
# Generate a GPG key
gpg --full-generate-key
# Select RSA (4096), set expiration, provide name/email

# List your keys
gpg --list-secret-keys --keyid-format=long

# Configure Git to use the key
git config --global user.signingkey YOUR_KEY_ID
git config --global commit.gpgsign true
```

For automated signing on CI/CD runners:

```yaml
# GitHub Actions example
- name: Import GPG Key
  run: |
    echo "$GPG_PRIVATE_KEY" | gpg --batch --import
    git config --global user.signingkey "$GPG_KEY_ID"
    git config --global commit.gpgsign true
```

### Docker Compose: Self-Hosted GPG Key Server

```yaml
version: "3.8"
services:
  keys-server:
    image: sikemul/keyserver:latest
    container_name: gpg-keyserver
    ports:
      - "11371:11371"
    volumes:
      - keyserver-data:/data
    restart: unless-stopped
    environment:
      - KEYSERVER_HKP_PORT=11371

volumes:
  keyserver-data:
```

### Pros and Cons

| Feature | Assessment |
|---------|-----------|
| Compatibility | Universal — supported by all Git platforms since 2013 |
| Key management | Manual — you manage key generation, distribution, and revocation |
| Key expiration | Configurable — keys can expire and be rotated |
| CI/CD integration | Complex — requires secure key injection into pipelines |
| Learning curve | Moderate — GPG concepts (web of trust, subkeys) can be confusing |

## SSH Commit Signing

Starting with Git 2.34 (Q4 2021), Git can use SSH keys to sign commits. This eliminates the need for GPG entirely, leveraging the SSH keys most developers already have.

### How It Works

Git uses your SSH private key to sign commit content via the `ssh-keygen -Y sign` mechanism. The signature format is compatible with SSH's existing `ssh-keygen -Y verify` tool, making verification straightforward.

### Setup

```bash
# Generate an SSH signing key (or reuse existing)
ssh-keygen -t ed25519 -C "commits@yourdomain.com" -f ~/.ssh/id_ed25519_signing

# Configure Git
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true

# Create an allowed_signers file for verification
echo "developer@yourdomain.com $(cat ~/.ssh/id_ed25519_signing.pub)" > ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

### Docker Compose: SSH Signing Key Management Service

```yaml
version: "3.8"
services:
  key-vault:
    image: hashicorp/vault:1.15
    container_name: ssh-key-vault
    ports:
      - "8200:8200"
    volumes:
      - vault-data:/vault/file
    environment:
      - VAULT_ADDR=http://0.0.0.0:8200
      - VAULT_LOCAL_CONFIG={"storage":{"file":{"path":"/vault/file"}},"listener":{"tcp":{"address":"0.0.0.0:8200","tls_disable":"true"}}}
    command: vault server -config=/vault/local/config/local.json
    restart: unless-stopped

volumes:
  vault-data:
```

### Pros and Cons

| Feature | Assessment |
|---------|-----------|
| Compatibility | Requires Git 2.34+ — widely available but not universal |
| Key management | Familiar — SSH keys are already managed by most teams |
| Key rotation | Simple — replace the key file and update allowed_signers |
| CI/CD integration | Easy — SSH keys are natively supported by most CI systems |
| Learning curve | Low — if you already use SSH, there's little new to learn |

## Sigstore Cosign for Commit Signing

Sigstore cosign brings keyless signing to Git commits, using OpenID Connect (OIDC) identity tokens tied to short-lived certificates. This approach eliminates key management entirely.

### How It Works

When you sign a commit with cosign, it authenticates you through an OIDC provider (Google, GitHub, Microsoft), obtains a short-lived certificate from Fulcio (Sigstore's certificate authority), and uses it to sign the commit. Verification happens through Rekor, Sigstore's transparency log, which provides an immutable record of all signatures.

### Setup

```bash
# Install cosign
curl -sL https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64   -o /usr/local/bin/cosign && chmod +x /usr/local/bin/cosign

# Sign a commit (interactive OIDC flow)
cosign sign-blob --output-signature commit.sig --output-certificate commit.crt   --bundle commit.bundle <(git cat-file blob HEAD)

# Verify the signature
cosign verify-blob --signature commit.sig --certificate commit.crt   --certificate-identity developer@yourdomain.com   --certificate-oidc-issuer https://accounts.google.com   <(git cat-file blob HEAD)
```

### Docker Compose: Self-Hosted Sigstore Fulcio and Rekor

```yaml
version: "3.8"
services:
  rekor-server:
    image: gcr.io/projectsigstore/rekor-server:v1.3.6
    container_name: rekor-server
    ports:
      - "3000:3000"
    environment:
      - REKOR_SERVER_ADDRESS=0.0.0.0
      - REKOR_SERVER_PORT=3000
      - REKOR_LOGTYPE=merkle
      - REKOR_TRILLIAN_LOG_SERVER=localhost:8000
    restart: unless-stopped

  fulcio-server:
    image: gcr.io/projectsigstore/fulcio:v1.4.4
    container_name: fulcio-server
    ports:
      - "5555:5555"
    environment:
      - FULCIO_CT_LOG_URL=http://rekor-server:3000
    restart: unless-stopped

  trillian-log-server:
    image: gcr.io/trillian-opensource-trial/log-server:v1.5.2
    container_name: trillian-log-server
    ports:
      - "8000:8000"
    environment:
      - MYSQL_URI=root:password@tcp(mysql:3306)/trillian
    depends_on:
      - mysql
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: trillian-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=trillian
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mysql-data:
```

### Pros and Cons

| Feature | Assessment |
|---------|-----------|
| Compatibility | Requires cosign — not natively supported by Git yet |
| Key management | Zero — keys are ephemeral, identity comes from OIDC |
| Key rotation | Automatic — certificates expire in minutes |
| CI/CD integration | Excellent — native support in GitHub Actions, GitLab CI |
| Learning curve | Moderate — OIDC concepts and Sigstore ecosystem require understanding |

## Comparison Table

| Feature | GPG/PGP | SSH Signing | Sigstore Cosign |
|---------|---------|-------------|-----------------|
| Git version required | 1.7.9+ | 2.34+ | Any (external tool) |
| Key management | Manual (GPG keyring) | Manual (SSH files) | Automatic (OIDC) |
| Key expiration | Configurable | Manual rotation | Minutes (ephemeral) |
| Platform support | GitHub, GitLab, Gitea, Forgejo | GitHub, GitLab, Forgejo | Limited (via cosign) |
| CI/CD friendliness | Moderate (key injection) | High (SSH native) | Excellent (OIDC native) |
| Self-hosted friendly | Yes | Yes | Partial (need Fulcio/Rekor) |
| Transparency log | No | No | Yes (Rekor) |
| Learning curve | Moderate | Low | Moderate-High |

## Choosing the Right Signing Method

For **individual developers** or small teams, SSH signing offers the best balance of simplicity and security. You likely already have SSH keys, and Git's native support means no additional tooling.

For **enterprise environments** with compliance requirements, GPG remains the gold standard. It has the broadest platform support and integrates with existing PKI infrastructure through X.509 certificate signing.

For **CI/CD pipelines and automated workflows**, Sigstore cosign's keyless approach eliminates the risk of long-lived signing keys being compromised in your build infrastructure. The transparency log also provides an audit trail that GPG and SSH cannot match.

Many organizations adopt a **hybrid approach**: SSH signing for developer commits, cosign for CI/CD pipeline commits, and GPG for release tags that require long-term verifiability.

## FAQ

### Do I need to sign every commit?

For high-security projects, yes — enabling `commit.gpgsign true` ensures every commit is signed. For lower-security projects, you can sign selectively with `git commit -S` or sign merge commits only with `merge.gpgsign true`.

### Can I use an existing SSH key for commit signing?

Yes, but it's recommended to create a dedicated signing key. Reusing your authentication key means any compromise of your signing key also compromises your server access. Generate a separate key with `ssh-keygen -t ed25519 -C "commits@yourdomain.com"`.

### How does Sigstore cosign work offline?

Cosign requires internet access for the OIDC authentication flow. For air-gapped environments, you can use `cosign sign` with a local key (`COSIGN_KEY` environment variable) instead of the OIDC flow, though this sacrifices the keyless benefit.

### Will signed commits slow down Git operations?

Negligibly. GPG signing adds approximately 50-200ms per commit, SSH signing adds 10-50ms, and cosign adds 1-3 seconds (due to OIDC authentication). For most workflows, this overhead is imperceptible.

### Can I backdate a signed commit?

Yes — `git commit --date="2024-01-01T00:00:00" -S` will create a signed commit with a custom date. However, the signature covers the commit content including the date, so any post-signing modification will invalidate the signature.

### How do I migrate from GPG to SSH signing?

Set `gpg.format ssh` in your Git config, point `user.signingkey` to your SSH public key file, and create an `allowed_signers` file. Existing GPG-signed commits remain valid — the signature format is stored per-commit, not globally configured.

### What happens if I lose my signing key?

For GPG: generate a new key, update your Git config, and revoke the old key on keyservers. For SSH: generate a new key and update `allowed_signers`. For cosign: nothing — keys are ephemeral and regenerated per-signing session.

## Why Self-Host Your Commit Signing Infrastructure?

Running your own Git signing verification infrastructure gives you complete control over key management, identity verification, and audit trails. When you self-host platforms like Gitea or Forgejo with integrated signature verification, you eliminate dependency on third-party services for validating commit authenticity.

For organizations handling sensitive intellectual property, self-hosted signing verification ensures that commit signatures never leave your infrastructure. Combined with internal GPG keyservers or Vault-based SSH key management, you maintain a complete chain of custody from code creation through deployment.

For teams already running self-hosted CI/CD, integrating commit signing into your pipeline means automated verification before code reaches production. This is especially valuable when combined with [supply chain security tools](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/) and [Git platform security practices](../2026-04-26-gogs-vs-gitbucket-vs-onedev-lightweight-self-hosted-git-platforms-2026/).

For organizations managing complex deployment pipelines, [Git hooks management](../2026-04-26-pre-commit-vs-lefthook-vs-husky-git-hooks-management-guide/) can enforce signing policies automatically, ensuring no unsigned commit reaches your main branch.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Git Commit Signing: GPG vs SSH vs Sigstore Cosign Guide 2026",
  "description": "Compare three approaches to Git commit signing — GPG/PGP, SSH-based signing, and Sigstore cosign — with setup guides, Docker configs, and a decision framework for teams.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
