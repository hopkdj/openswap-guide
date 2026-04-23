---
title: "Mozilla SOPS vs git-crypt vs age: Encrypt Secrets in Git 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "security", "encryption", "git"]
draft: false
description: "Compare Mozilla SOPS, git-crypt, and age for encrypting secrets and sensitive files in Git repositories. Complete guide with installation, Docker setup, and real-world configuration examples."
---

Storing configuration files in Git is a cornerstone of infrastructure-as-code and self-hosted server management. But configuration files often contain passwords, API keys, TLS certificates, and database credentials. Committing these in plaintext is a security risk that can lead to data breaches, especially in shared repositories.

The solution is encrypting sensitive files before they enter version control. Three open-source tools dominate this space: **Mozilla SOPS**, **git-crypt**, and **age**. Each takes a fundamentally different approach to the problem, and choosing the right one depends on your team size, infrastructure complexity, and threat model.

In this guide, we compare all three tools side-by-side with real configuration examples, so you can pick the best encryption workflow for your self-hosted infrastructure.

## Why Encrypt Secrets in Git?

Version control systems like Git keep every version of every file forever. Once a plaintext password is committed — even briefly — it exists in the repository history permanently. Removing it requires rewriting history with `git filter-branch` or `git filter-repo`, which is disruptive and error-prone.

Encrypting sensitive files before they are committed solves this problem at the source:

- **Prevents accidental exposure** — encrypted files are useless without the decryption key
- **Enables GitOps workflows** — encrypted secrets can be stored alongside application configuration in the same repository
- **Supports team collaboration** — multiple people can encrypt and decrypt files without sharing a single master password
- **Satisfies compliance requirements** — many security standards require secrets to be encrypted at rest

### The Threat Model

The tools covered here protect against **repository compromise** — if someone gains read access to your Git repository (through a leaked token, compromised collaborator account, or backup exposure), encrypted files remain unreadable. They do not protect against:

- Compromised decryption keys on a developer's machine
- Malicious CI/CD pipelines that have decryption access
- Social engineering attacks to obtain key material

Choose your encryption tool accordingly and implement proper key management alongside file encryption.

## Mozilla SOPS

**Mozilla SOPS** (Secrets OPerationS) is a flexible, widely-adopted tool for managing encrypted secrets. It supports YAML, JSON, ENV, INI, and binary file formats, and integrates with multiple key management backends including AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault, and PGP/GPG keys.

| Metric | Value |
|--------|-------|
| **Repository** | [mozilla/sops](https://github.com/mozilla/sops) |
| **Stars** | 21,571 |
| **Language** | Go |
| **Last Active** | April 2026 |
| **License** | MPL-2.0 |

### Key Features

- **Partial encryption** — SOPS encrypts only the *values* in YAML/JSON files, leaving keys in plaintext. This means you can still diff, review, and merge encrypted files without decrypting them.
- **Multiple key backends** — Supports AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault, PGP, and age keys simultaneously.
- **Age integration** — Native support for age keys as a lightweight alternative to PGP.
- **Editor integration** — Seamless editing via `sops <file>` which decrypts to a temp file, opens your editor, and re-encrypts on save.
- **Git hooks** — Works with pre-commit hooks to auto-encrypt files before commit.

### Installation

```bash
# macOS
brew install sops

# Linux (Debian/Ubuntu)
sudo apt install gnupg
curl -LO https://github.com/getsops/sops/releases/download/v3.9.0/sops-v3.9.0.linux.amd64
chmod +x sops-v3.9.0.linux.amd64
sudo mv sops-v3.9.0.linux.amd64 /usr/local/bin/sops

# Using Docker
docker run --rm -it -v $PWD:/data getsops/sops:v3.9.0 file.yaml
```

### Configuration and Usage

Create a `.sops.yaml` configuration file at the root of your repository:

```yaml
creation_rules:
  - path_regex: secrets/.*\.yaml$
    age: >-
      age1q8xmkv3r5yq6z0n7t8u9w0x1y2z3a4b5c6d7e8f9g0h1j2k3l4m5n6p7
  - path_regex: production/.*\.yaml$
    age: >-
      age1q8xmkv3r5yq6z0n7t8u9w0x1y2z3a4b5c6d7e8f9g0h1j2k3l4m5n6p7
    pgp: >-
      ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX234YZ
  - path_regex: \.env$
    age: >-
      age1q8xmkv3r5yq6z0n7t8u9w0x1y2z3a4b5c6d7e8f9g0h1j2k3l4m5n6p7
```

Encrypt a file:

```bash
# Encrypt and edit
sops secrets/database-credentials.yaml

# Encrypt existing file
sops -e -i secrets/app-config.yaml

# Decrypt and view
sops -d secrets/database-credentials.yaml
```

Example encrypted output (note how keys remain readable):

```yaml
database:
    host: db.internal.example.com
    port: 5432
    username: ENC[AES256_GCM,data:abc123==,type:str]
    password: ENC[AES256_GCM,data:xyz789==,type:str]
sops:
    kms: []
    gcp_kms: []
    azure_kv: []
    hc_vault: []
    age:
        - recipient: age1q8xm...
          enc: |
            -----BEGIN AGE ENCRYPTED FILE-----
            YWdlLWVuY3J5cHRpb24ub3JnL3YxCi0+IFgyNTUxOSBhYmMxMjM=
            -----END AGE ENCRYPTED FILE-----
    lastmodified: "2026-04-23T10:00:00Z"
    mac: ENC[AES256_GCM,data:...,type:str]
```

### CI/CD Integration with Docker Compose

Here's a Docker Compose setup for running SOPS in a CI/CD pipeline:

```yaml
version: "3.8"

services:
  decrypt-secrets:
    image: getsops/sops:v3.9.0
    volumes:
      - .:/workspace:ro
      - ./keys:/root/.config/sops/age:ro
    working_dir: /workspace
    entrypoint: ["sh", "-c"]
    command:
      - |
        sops -d secrets/production.yaml > /tmp/decrypted.yaml
        cat /tmp/decrypted.yaml
    environment:
      SOPS_AGE_KEY_FILE: /root/.config/sops/age/keys.txt
```

## git-crypt

**git-crypt** is a Git extension that provides transparent file encryption and decryption using Git's built-in clean/smudge filter mechanism. Files are automatically encrypted on commit and decrypted on checkout, making the encryption completely transparent to your normal Git workflow.

| Metric | Value |
|--------|-------|
| **Repository** | [AGWA/git-crypt](https://github.com/AGWA/git-crypt) |
| **Stars** | 9,601 |
| **Language** | C++ |
| **Last Active** | September 2025 |
| **License** | GPL-2.0 |

### Key Features

- **Transparent encryption** — Files are automatically encrypted when committed and decrypted when checked out. No extra commands needed in your daily workflow.
- **GPG-based key sharing** — Uses GPG public keys to grant decryption access to specific users.
- **File-level granularity** — Specify which files or directories to encrypt via a `.gitattributes` file.
- **Hybrid mode** — Can store encrypted versions of files in the repository while keeping plaintext versions in the working directory.

### Installation

```bash
# macOS
brew install git-crypt

# Debian/Ubuntu
sudo apt install git-crypt

# Build from source
git clone https://github.com/AGWA/git-crypt.git
cd git-crypt
make
sudo make install
```

### Configuration and Usage

Initialize git-crypt in your repository:

```bash
# Initialize with a new symmetric key
git-crypt init

# Or use an existing GPG key
git-crypt init -g <GPG-FINGERPRINT>
```

Configure which files to encrypt via `.gitattributes`:

```gitattributes
# Encrypt all YAML files in the secrets/ directory
secrets/*.yaml filter=git-crypt diff=git-crypt

# Encrypt all .env files
*.env filter=git-crypt diff=git-crypt

# Encrypt specific files
config/database.yml filter=git-crypt diff=git-crypt
config/api-keys.json filter=git-crypt diff=git-crypt

# Never encrypt README or documentation
README.md !filter !diff
```

Add collaborators with their GPG public keys:

```bash
# Grant access to a team member
git-crypt add-gpg-user --trusted <GPG-FINGERPRINT>

# Grant access to multiple users at once
git-crypt add-gpg-user --trusted user1@example.com user2@example.com
```

Commit your files normally — git-crypt handles encryption transparently:

```bash
# Regular git workflow — files are encrypted on commit
git add secrets/database-credentials.yaml
git commit -m "Add production database credentials"
git push
```

### Exporting the Key for CI/CD

For CI/CD pipelines, export the symmetric key and store it as a CI secret:

```bash
# Export the symmetric key to a file
git-crypt export-key /path/to/git-crypt-key

# In CI/CD, import the key before cloning
git-crypt unlock /path/to/git-crypt-key
```

Docker Compose example for a CI pipeline:

```yaml
version: "3.8"

services:
  build:
    build: .
    volumes:
      - .:/workspace
    working_dir: /workspace
    entrypoint: ["sh", "-c"]
    command:
      - |
        git-crypt unlock /keys/git-crypt-key
        cat secrets/production.yaml
        # Run your application with decrypted secrets
    secrets:
      - git-crypt-key

secrets:
  git-crypt-key:
    file: ./ci-secrets/git-crypt-key
```

## age

**age** is a simple, modern encryption tool designed by Filippo Valsorda (a Go core team member and cryptography expert). Unlike SOPS and git-crypt, age is not specifically a Git tool — it's a general-purpose file encryption utility that happens to work excellently for encrypting secrets before storing them in version control.

| Metric | Value |
|--------|-------|
| **Repository** | [FiloSottile/age](https://github.com/FiloSottile/age) |
| **Stars** | 22,071 |
| **Language** | Go |
| **Last Active** | March 2026 |
| **License** | BSD-3-Clause |

### Key Features

- **Minimal design** — No config files, no keyring daemons, no complex setup. Just encrypt and decrypt with a key file.
- **X25519 encryption** — Uses modern, audited cryptography (X25519 key exchange + ChaCha20-Poly1305).
- **Small keys** — Public keys are short, human-readable strings starting with `age1`. Secret keys fit in a single small file.
- **SSH key support** — Can encrypt files using existing SSH public keys (`age -R ~/.ssh/id_ed25519.pub`).
- **Password-based encryption** — Supports passphrase encryption with `--passphrase` for simple single-user scenarios.
- **Multi-recipient** — A single file can be encrypted for multiple recipients (keys).

### Installation

```bash
# macOS
brew install age

# Debian/Ubuntu (11+)
sudo apt install age

# Using go install
go install filippo.io/age/cmd/...@latest

# Direct binary download
curl -LO https://github.com/FiloSottile/age/releases/download/v1.2.0/age-v1.2.0-linux-amd64.tar.gz
tar -xzf age-v1.2.0-linux-amd64.tar.gz
sudo mv age/age age/age-keygen /usr/local/bin/
```

### Configuration and Usage

Generate a key pair:

```bash
age-keygen -o key.txt
# Output: Public key: age1q8xmkv3r5yq6z0n7t8u9w0x1y2z3a4b5c6d7e8f9g0h1j2k3l4m5n6p7
```

Encrypt and decrypt files:

```bash
# Encrypt a file for a specific recipient
age -r age1q8xmkv3r5yq6z0n7t8u9w0x1y2z3a4b5c6d7e8f9g0h1j2k3l4m5n6p7 \
    -o secrets/database.yaml.age \
    secrets/database.yaml

# Decrypt a file
age -d -o secrets/database.yaml -i key.txt secrets/database.yaml.age

# Encrypt for multiple recipients
age -r age1abc... -r age1def... -o config.yaml.age config.yaml

# Encrypt with a passphrase (no key file needed)
age --passphrase -o secrets.yaml.age secrets.yaml
```

Encrypting in a Git workflow requires a pre-commit hook to encrypt before committing and a post-checkout hook to decrypt. Here's a practical `.gitattributes`-inspired workflow using a wrapper script:

```bash
#!/bin/bash
# encrypt-before-commit.sh — call from pre-commit hook
KEY_FILE=~/.config/age/keys.txt
RECIPIENT="age1q8xmkv3r5yq6z0n7t8u9w0x1y2z3a4b5c6d7e8f9g0h1j2k3l4m5n6p7"

for file in secrets/*.yaml; do
    if [ -f "$file" ]; then
        age -r "$RECIPIENT" -o "${file}.age" "$file"
        git add "${file}.age"
        rm "$file"  # Remove plaintext version from working tree
    fi
done
```

### Docker Compose Setup for age

```yaml
version: "3.8"

services:
  app:
    image: your-app:latest
    volumes:
      - ./secrets:/app/secrets:ro
      - ./age-keys:/age-keys:ro
    working_dir: /app
    entrypoint: ["sh", "-c"]
    command:
      - |
        age -d -i /age-keys/keys.txt -o /app/config.yaml /app/secrets/config.yaml.age
        exec your-app --config /app/config.yaml
```

## Head-to-Head Comparison

| Feature | Mozilla SOPS | git-crypt | age |
|---------|-------------|-----------|-----|
| **Primary Focus** | Secrets management in YAML/JSON | Transparent Git encryption | General-purpose file encryption |
| **Encryption Scope** | Values only (keys remain visible) | Entire file | Entire file |
| **Key Management** | AWS KMS, GCP KMS, Azure KV, Vault, PGP, age | GPG | age keys, SSH keys, passphrases |
| **Partial Editing** | Yes — edit encrypted values directly | No — must decrypt full file | No — must decrypt full file |
| **Git Integration** | Manual (CLI commands) | Automatic (clean/smudge filters) | Manual (requires hooks) |
| **File Formats** | YAML, JSON, ENV, INI, binary | Any file type | Any file type |
| **Multi-recipient** | Yes (per backend) | Yes (via GPG) | Yes (native) |
| **CI/CD Friendly** | Excellent | Good (requires key export) | Excellent |
| **Setup Complexity** | Medium | Low-Medium | Low |
| **Learning Curve** | Moderate | Low | Very low |
| **Star Count** | 21,571 | 9,601 | 22,071 |
| **Active Development** | Yes (April 2026) | No (September 2025) | Yes (March 2026) |
| **License** | MPL-2.0 | GPL-2.0 | BSD-3-Clause |

## Choosing the Right Tool

### Choose Mozilla SOPS When:

- You manage **multiple environments** (dev, staging, production) with different access controls
- You need **partial encryption** — want to keep YAML keys visible for code review while encrypting values
- Your team already uses **cloud KMS providers** (AWS KMS, GCP KMS, Azure Key Vault)
- You want **audit trails** through cloud provider KMS logging
- You work primarily with **YAML/JSON configuration files**

SOPS is the industry standard for Kubernetes and cloud-native environments. It pairs well with tools like [Kubernetes secrets management solutions](../external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) when you need to deploy encrypted secrets to clusters.

### Choose git-crypt When:

- You want **zero-friction Git workflow** — encrypt on commit, decrypt on checkout, no extra commands
- Your team already uses **GPG** for code signing and email encryption
- You need **per-file encryption granularity** via `.gitattributes`
- You want to encrypt **any file type** (binary files, certificates, keystores)

git-crypt is ideal for small teams where GPG is already part of the workflow. However, note that development has slowed — the last significant commit was in September 2025.

### Choose age When:

- You want the **simplest possible setup** — generate a key, encrypt, done
- You prefer **modern cryptography** without PGP's complexity
- You need to encrypt **ad-hoc files** outside of a formal secrets management system
- You want a **permissive license** (BSD-3-Clause) for commercial use
- You already use **SSH keys** and want to leverage them for encryption

age is the most popular of the three by GitHub stars and has the lowest barrier to entry. It works well alongside [encrypted backup solutions](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) for protecting configuration backups.

### The Hybrid Approach

Many teams combine these tools:

1. **age** for ad-hoc file encryption and simple single-user scenarios
2. **SOPS** for structured YAML/JSON secrets with cloud KMS integration
3. **git-crypt** for transparent encryption of binary assets (certificates, keystores) in Git

For example, you might use SOPS for Kubernetes manifest files, age for encrypting individual configuration files shared between team members, and git-crypt for encrypting TLS certificates stored in the repository.

## Security Best Practices

Regardless of which tool you choose, follow these security practices:

### Key Management

```bash
# Never commit decryption keys to Git
echo "key.txt" >> .gitignore
echo ".sops.yaml" >> .gitignore  # SOPS config contains public keys, but keep private keys out

# Store keys in a password manager or hardware token
# Use different keys per environment (dev, staging, production)
```

### Access Control

- **Rotate keys regularly** — especially when team members leave
- **Use separate keys per environment** — a compromised dev key should not expose production secrets
- **Audit access** — track who has decryption keys for each environment

### Pre-Commit Hooks

Add a pre-commit hook to prevent accidentally committing unencrypted secrets:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for common secret patterns in staged files
SECRET_PATTERNS=(
    "password\s*[:=]"
    "api_key\s*[:=]"
    "secret_key\s*[:=]"
    "aws_secret_access_key"
    "private_key"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if git diff --cached -U0 | grep -iP "$pattern" > /dev/null 2>&1; then
        echo "ERROR: Potential secret detected in staged files!"
        echo "Pattern matched: $pattern"
        echo "Encrypt your secrets before committing."
        exit 1
    fi
done
```

## Migration Paths

### From Plaintext to SOPS

```bash
# 1. Install SOPS and generate age key
age-keygen -o ~/.config/sops/age/keys.txt

# 2. Create .sops.yaml with your public key
echo "creation_rules:" > .sops.yaml
echo "  - path_regex: '.*\.yaml$'" >> .sops.yaml
echo "    age: $(cat ~/.config/sops/age/keys.txt | grep public | awk '{print $NF}')" >> .sops.yaml

# 3. Encrypt all existing secrets
find secrets/ -name "*.yaml" -exec sops -e -i {} \;

# 4. Commit the encrypted files
git add secrets/ .sops.yaml
git commit -m "Encrypt all secrets with SOPS + age"
```

### From git-crypt to age

```bash
# 1. Unlock all git-crypt files
git-crypt unlock

# 2. Generate age key
age-keygen -o age-key.txt
RECIPIENT=$(grep public age-key.txt | awk '{print $NF}')

# 3. Encrypt each file with age
for f in secrets/*.yaml; do
    age -r "$RECIPIENT" -o "${f}.age" "$f"
done

# 4. Remove git-crypt configuration
git-crypt lock
rm .gitattributes  # or remove git-crypt lines
git add secrets/*.age
git commit -m "Migrate from git-crypt to age encryption"
```

## FAQ

### Which tool is best for encrypting secrets in Git?

For most self-hosted infrastructure teams, **Mozilla SOPS** with age keys provides the best balance of features and simplicity. It encrypts only the values (keeping keys visible for diffs), supports multiple key backends, and integrates seamlessly with YAML/JSON configuration files. For simpler single-user setups, **age** alone is the easiest option.

### Can I use age without Git hooks?

Yes. age is a standalone file encryption tool. You can manually encrypt files with `age -r <key> -o file.yaml.age file.yaml` and commit the `.age` files to Git. However, without hooks, you'll need to remember to encrypt before committing and decrypt after checking out. For a more seamless workflow, combine age with pre-commit/post-checkout Git hooks or use SOPS, which has built-in edit workflows.

### Is git-crypt still actively maintained?

As of early 2026, git-crypt's development has slowed significantly. The last major update was in September 2025. The tool is stable and works well for its intended purpose, but teams concerned about long-term maintenance may prefer SOPS or age, both of which have active development communities.

### How do I rotate encryption keys?

With **SOPS**: update your `.sops.yaml` with the new public key, then run `sops updatekeys <file>` for each encrypted file. With **age**: encrypt a new copy of each file with the new recipient key using `age -r <new-key> -o new-file.age old-file.age`. With **git-crypt**: generate a new GPG key and run `git-crypt add-gpg-user <new-fingerprint>`, then remove the old user with `git-crypt remove-gpg-user <old-fingerprint>`.

### Can I use these tools with CI/CD pipelines?

All three tools work with CI/CD. For **SOPS**, pass the age key file or cloud KMS credentials as CI secrets. For **git-crypt**, export the symmetric key with `git-crypt export-key` and store it as a CI secret, then unlock with `git-crypt unlock <key>` in the pipeline. For **age**, store the key file as a CI secret and use `age -d -i key.txt` to decrypt during builds.

### What happens if I lose my decryption key?

**You permanently lose access to the encrypted files.** There is no backdoor or recovery mechanism in any of these tools. This is by design — it's what makes the encryption secure. Always back up your keys to multiple secure locations (hardware tokens, password managers, offline storage) and consider using multi-recipient encryption so no single key is a single point of failure.

### Does encrypting secrets in Git replace a secrets manager?

No. File encryption in Git solves the problem of storing secrets in version control, but it doesn't address runtime secret delivery, rotation, auditing, or access control. For production systems, consider combining Git-based encryption with a dedicated [secrets management solution](../best-self-hosted-secret-management-vault-infisical-passbolt-2026/) like HashiCorp Vault or Infisical for runtime secret distribution.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Mozilla SOPS vs git-crypt vs age: Encrypt Secrets in Git 2026",
  "description": "Compare Mozilla SOPS, git-crypt, and age for encrypting secrets and sensitive files in Git repositories. Complete guide with installation, Docker setup, and real-world configuration examples.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
