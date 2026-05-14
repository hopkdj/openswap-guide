---
title: "Self-Hosted Nix Deployment Systems: NixOps vs Colmena vs deploy-rs"
date: "2026-05-14"
tags: ["nix", "deployment", "infrastructure", "configuration-management"]
draft: false
---

Managing infrastructure across multiple servers requires reliable deployment tooling that handles dependency resolution, rollback capabilities, and reproducible builds. The Nix ecosystem offers three mature deployment systems that take different approaches to the same problem: provisioning and managing NixOS configurations on remote machines. This guide compares NixOps, Colmena, and deploy-rs to help you choose the right tool for your infrastructure needs.

## What Are Nix Deployment Systems?

Nix deployment systems extend the Nix package manager's core guarantee — reproducible builds — to the infrastructure layer. Instead of manually running `nixos-rebuild switch` on each server via SSH, these tools orchestrate deployment across entire fleets. They parse Nix expressions that describe your desired system state, transfer built derivations to remote hosts, and activate new configurations atomically.

The key advantage over traditional configuration management tools like Ansible or Puppet is that Nix deployment tools guarantee idempotency through cryptographic content-addressed storage. Every configuration is a unique derivation in the Nix store, identified by its hash. Rolling back is instantaneous — the previous generation is already on disk and simply needs to be activated.

## NixOps: The Official Deployment Tool

NixOps is the reference deployment tool maintained by the NixOS foundation. It treats infrastructure as Nix expressions that describe both machine configurations and the relationships between them.

**Key features:**
- Declarative network topology definitions
- Built-in support for VirtualBox, EC2, Hetzner, and Libvirt backends
- Automatic SSH key distribution between machines
- Configuration rollback across entire deployments
- State tracking in a local SQLite database

NixOps uses a two-file architecture: a network definition file (`network.nix`) describing machines and their deployment targets, and configuration files for each machine's NixOS settings. This separation makes it straightforward to manage heterogeneous fleets where different servers serve different roles.

```nix
# network.nix
{
  network.description = "Web Application Stack";

  webserver =
    { config, pkgs, ... }:
    {
      deployment.targetHost = "10.0.1.10";
      deployment.targetUser = "root";
      services.nginx.enable = true;
      services.nginx.virtualHosts."example.com" = {
        enableACME = true;
        forceSSL = true;
      };
    };

  database =
    { config, pkgs, ... }:
    {
      deployment.targetHost = "10.0.1.20";
      deployment.targetUser = "root";
      services.postgresql.enable = true;
      services.postgresql.package = pkgs.postgresql_15;
    };
}
```

Deploy with a single command:

```bash
nixops create ./network.nix -d my-deployment
nixops deploy -d my-deployment
```

NixOps tracks deployment state, meaning it knows which machines belong to which deployment and can selectively rebuild only the changed machines. The state database prevents accidental configuration drift.

## Colmena: Fast Parallel Deployments

Colmena takes a different design philosophy — it focuses on fast, parallel deployments to multiple hosts without maintaining persistent state. Instead of a state database, Colmena reads host definitions directly from Nix expressions each time you deploy.

**Key features:**
- Stateless deployment — no database to maintain
- Parallel SSH deployment to all hosts simultaneously
- Built-in host discovery through NixOS configuration
- Support for meta attributes like `deployment.tags`
- Apply configurations to specific host subsets with selectors

Colmena's stateless approach eliminates a common failure mode: corrupted state databases that prevent deployment. Since it reads configuration fresh each time, you can always recover by fixing your Nix expressions and re-deploying.

```nix
# flake.nix excerpt
{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  inputs.colmena.url = "github:zhaofengli/colmena";

  outputs = { self, nixpkgs, colmena, ... }: {
    colmena = {
      meta = {
        nixpkgs = import nixpkgs { system = "x86_64-linux"; };
        specialArgs = { inherit self; };
      };

      webserver = { name, nodes, ... }: {
        deployment = {
          targetHost = "10.0.1.10";
          tags = [ "production" "web" ];
        };
        services.nginx.enable = true;
      };

      database = { name, nodes, ... }: {
        deployment = {
          targetHost = "10.0.1.20";
          tags = [ "production" "database" ];
        };
        services.postgresql.enable = true;
      };
    };
  };
}
```

Deploy all production hosts in parallel:

```bash
colmena apply --on @production
```

The `@production` selector matches all hosts tagged "production", allowing you to deploy to specific subsets of your infrastructure. Colmena evaluates all configurations in parallel before deploying, giving you a complete picture of what will change before any SSH connections are made.

## deploy-rs: Simple and Multi-Platform

deploy-rs is a lightweight, multi-platform deployment tool that works with both NixOS and non-NixOS targets (including macOS and Linux with Nix installed). It uses a Rust implementation for fast SSH operations and focuses on simplicity.

**Key features:**
- Written in Rust for fast, reliable SSH operations
- Supports NixOS and non-NixOS targets
- Works with flakes natively
- Rolling and parallel deployment modes
- Built-in health checks after deployment
- Automatic rollback on failed activation

deploy-rs excels when you need to manage a mixed environment — some servers running NixOS, others running standard Linux distributions with Nix package manager installed. It also provides health check hooks that verify service availability before considering a deployment successful.

```nix
# flake.nix excerpt
{
  inputs.deploy-rs.url = "github:serokell/deploy-rs";

  outputs = { self, nixpkgs, deploy-rs, ... }: {
    deploy.nodes.webserver = {
      hostname = "10.0.1.10";
      profiles.system = {
        user = "root";
        path = deploy-rs.lib.x86_64-linux.activate.nixos self.nixosConfigurations.webserver;
        sshUser = "deploy";
        magicRollback = true;
        autoRollback = true;
      };
    };

    deploy.nodes.database = {
      hostname = "10.0.1.20";
      profiles.system = {
        user = "root";
        path = deploy-rs.lib.x86_64-linux.activate.nixos self.nixosConfigurations.database;
        sshUser = "deploy";
      };
    };

    deploy.rootspec = self.deploy;
  };
}
```

Deploy with automatic rollback protection:

```bash
nix run github:serokell/deploy-rs -- --flake .#webserver
```

The `magicRollback` feature is particularly valuable for production deployments: if the new configuration makes the system unreachable (e.g., SSH configuration broken), deploy-rs automatically rolls back to the previous generation after a timeout.

## Comparison Table

| Feature | NixOps | Colmena | deploy-rs |
|---------|--------|---------|-----------|
| **State Management** | SQLite database | Stateless | Stateless |
| **Parallel Deploy** | Sequential | Yes (parallel SSH) | Yes (configurable) |
| **Backend Support** | VirtualBox, EC2, Hetzner, Libvirt | Any SSH target | Any SSH target |
| **Flake Support** | Limited | Native | Native |
| **Non-NixOS Targets** | No | Limited | Full support |
| **Auto Rollback** | Manual | Manual | Built-in (magicRollback) |
| **Health Checks** | No | No | Built-in |
| **Language** | Python/Nix | Rust/Nix | Rust/Nix |
| **GitHub Stars** | 2,100+ | 1,800+ | 1,500+ |
| **Best For** | Full infrastructure provisioning | Fast parallel rebuilds | Simple, safe deployments |

## Choosing the Right Tool

**Use NixOps** when you need full infrastructure lifecycle management — creating VMs, configuring networks, and deploying services. Its backend support for cloud providers and hypervisors makes it suitable for greenfield deployments where you manage the entire stack from bare metal to services.

**Use Colmena** when you have an established fleet of NixOS servers and need fast, reliable parallel deployments. Its stateless design means no database to corrupt, and tag-based selectors make it easy to deploy to specific groups of servers.

**Use deploy-rs** when you need the simplest possible deployment workflow with safety features built in. The automatic rollback on failed activation is invaluable for production environments where a bad configuration could lock you out of remote servers.

## Why Self-Host Your Deployment Infrastructure?

Self-hosting your deployment infrastructure means maintaining full control over how and when configurations reach your servers. Unlike managed deployment services, self-hosted Nix deployment tools keep your infrastructure definitions, secrets, and deployment state entirely within your network perimeter.

For infrastructure management best practices, see our [SSH certificate management guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/) which covers secure authentication for deployment targets. If you're building immutable infrastructure, our [comparison of Talos Linux, Flatcar, and Bottlerocket](../2026-04-21-talos-linux-vs-flatcar-vs-bottlerocket-immutable-container-os-guide-2026/) provides complementary strategies for reproducible server deployments. For container image provenance, our [container build tools comparison](../2026-04-28-buildpacks-vs-tilt-vs-skaffold-self-hosted-container-build-guide-2026/) covers the CI/CD pipeline side of reproducible infrastructure.

The reproducibility guarantees of Nix deployment systems extend beyond individual machines — they create an auditable chain from source code to running service. Every configuration change is tracked in version control, every build is deterministic, and every deployment is reversible. This makes debugging infrastructure issues dramatically simpler: you can bisect through configuration history to find exactly when a problem was introduced.

Security is another critical advantage. With Nix deployment tools, you never need to install agents on target servers or open additional management ports. Deployment happens over standard SSH using existing infrastructure credentials. The Nix store's content-addressed design means configuration files cannot be tampered with after deployment — any modification would create a different hash and a new derivation.

Cost efficiency matters too. All three tools are free and open-source, with no licensing fees regardless of deployment scale. Whether managing three servers or three hundred, the tooling cost remains zero. The primary investment is in writing and maintaining Nix expressions, which pays dividends through reduced configuration drift and faster incident recovery.

## FAQ

### What is the difference between NixOps and nixos-rebuild?

nixos-rebuild operates on a single machine — it builds and activates a NixOS configuration locally. NixOps extends this to remote machines, managing deployment across multiple servers with state tracking and network topology awareness. NixOps also supports provisioning machines on cloud providers, which nixos-rebuild cannot do.

### Can I use Colmena without flakes?

Yes. Colmena supports both traditional Nix expressions and flakes. For non-flake usage, define your host configurations in a `colmena.nix` file using the `colmena` output format. However, flakes are recommended for their improved dependency management and reproducibility guarantees.

### Does deploy-rs work with non-NixOS Linux distributions?

deploy-rs supports any target with the Nix package manager installed, including Ubuntu, Debian, CentOS, and macOS. However, non-NixOS targets can only use Nix to install packages — they cannot use NixOS module options or system configuration features. Full NixOS integration requires the target to run NixOS.

### How does automatic rollback work in deploy-rs?

When `magicRollback` is enabled, deploy-rs verifies that the deployed system is still reachable after activation. If the system becomes unreachable (e.g., SSH daemon fails to restart with new configuration), deploy-rs waits for a configurable timeout and then automatically activates the previous generation. This prevents lockouts from broken configurations.

### Can I migrate from NixOps to Colmena?

Migration requires rewriting your network definitions. NixOps uses `network.nix` with `deployment.*` attributes, while Colmena uses a different host definition format. The underlying NixOS machine configurations remain unchanged — only the deployment layer needs updating. There is no automated migration tool, but the process is straightforward for small deployments.

### Do these tools support secrets management?

None of these tools include built-in secrets management. They integrate with external solutions like agenix (age-encrypted files), sops-nix (SOPS integration), or pass-secrets. Secrets are decrypted during evaluation and placed in the Nix store, so ensure your Nix store access controls are properly configured.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Nix Deployment Systems: NixOps vs Colmena vs deploy-rs",
  "description": "Compare three Nix deployment tools — NixOps, Colmena, and deploy-rs — for managing NixOS infrastructure across multiple servers with reproducible, atomic deployments.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
