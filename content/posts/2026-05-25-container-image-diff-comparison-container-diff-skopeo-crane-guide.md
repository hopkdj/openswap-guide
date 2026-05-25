---
title: "Container Image Diff & Comparison — container-diff vs Skopeo vs Crane Guide (2026)"
date: "2026-05-25"
tags: ["containers", "docker", "devops", "ci-cd", "image-analysis", "container-diff", "skopeo", "crane"]
draft: false
---

When managing containerized applications across multiple environments, comparing Docker and OCI images is a routine operational task. Whether you are auditing which packages changed between releases, verifying that a rebuild produced identical artifacts, or troubleshooting why a newer image fails in production, having reliable tools to diff container images is essential.

This guide compares three widely-used tools for container image comparison: Google's **container-diff**, Red Hat's **skopeo**, and Google's **crane** (part of the go-containerregistry project). Each approaches the problem from a different angle — high-level package comparison, low-level metadata inspection, and registry-native image manipulation respectively.

## Understanding Container Image Comparison

Container images are built as layered filesystems. Each layer is a tar archive of filesystem changes (added, modified, or deleted files). When comparing two images, you can analyze differences at multiple levels:

- **Filesystem level**: Which files were added, removed, or changed between images?
- **Package level**: Which installed packages (apt, rpm, pip, npm) differ?
- **Metadata level**: Do the labels, environment variables, or exposed ports differ?
- **Layer level**: How many layers differ, and what is the size impact?

Each of the three tools we cover excels at different levels of this analysis.

## container-diff: Package-Focused Comparison

[container-diff](https://github.com/GoogleContainerTools/container-diff) was built by Google specifically to diff Docker container images. Its primary strength is **package-level analysis** — it can compare installed packages across multiple package managers.

**Key features:**

- Compares apt, rpm, pip, npm, and go packages between images
- Supports comparing local Docker daemon images, tar files, and remote registry images
- Outputs diff in human-readable table format or JSON
- Can analyze a single image to list its packages (useful for SBOM-style inventory)
- File-level diff showing added, deleted, and modified files

**How it works:**

container-diff pulls or loads both images, extracts their filesystem layers, and runs package manager database parsers against each filesystem. The output shows packages present in one image but not the other, along with version changes.

```bash
# Compare two images by package type
container-diff diff docker://myapp:v1 docker://myapp:v2 --type=apt --type=pip

# Analyze a single image for all package types
container-diff analyze docker://myapp:v2 --type=apt --type=pip --type=npm

# Compare local daemon images
container-diff diff daemon://myapp:v1 daemon://myapp:v2 --type=file

# Output as JSON for CI/CD pipeline integration
container-diff diff docker://myapp:v1 docker://myapp:v2 --type=apt --json
```

**Strengths:**

- Best-in-class package comparison across multiple ecosystems
- No registry credentials needed for public images
- JSON output integrates easily with CI/CD pipelines

**Limitations:**

- Project is in maintenance mode (last significant update in 2024)
- Only compares two images at a time
- Does not compare image metadata (labels, env vars, entrypoint)

## Skopeo: Comprehensive Image Inspection and Diff

[skopeo](https://github.com/containers/skopeo) is part of the containers ecosystem (alongside Podman, Buildah, and containerd). While it is primarily known for copying and signing images between registries, it also provides robust image inspection and diff capabilities.

**Key features:**

- `skopeo diff` compares two images and outputs filesystem-level differences
- `skopeo inspect` provides detailed metadata (labels, env vars, layers, architecture)
- Works with OCI, Docker v2s2, and other image formats
- Supports Docker, Podman, and containerd storage backends
- Can copy images between registries, local storage, and tar archives without a daemon
- Supports image signing and verification

```bash
# Compare filesystem differences between two images
skopeo diff docker://registry.example.com/myapp:v1 docker://registry.example.com/myapp:v2

# Inspect image metadata (no pull required)
skopeo inspect docker://registry.example.com/myapp:v2

# Compare layer counts and sizes
skopeo inspect --raw docker://myapp:v1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Layers: {len(d["layers"])}')"

# Copy image between registries for comparison
skopeo copy docker://registry-a.example.com/app:v1 docker://registry-b.example.com/app:v1

# Export image to OCI directory format for offline analysis
skopeo copy docker://myapp:v2 oci:/tmp/myapp-v2:latest
```

**Strengths:**

- Actively maintained with regular releases (10,895+ GitHub stars)
- No Docker daemon required — works directly with registries
- Comprehensive metadata inspection beyond just filesystem diffs
- Part of a broader container tooling ecosystem (Podman, Buildah)

**Limitations:**

- No package-level comparison (filesystem diffs only)
- Output format is less structured than container-diff's JSON
- Requires downloading image layers for filesystem comparison

## Crane: Registry-Native Image Manipulation

[crane](https://github.com/google/go-containerregistry) is a CLI tool from Google's go-containerregistry project. While it is primarily designed for registry operations (push, pull, copy, delete), it provides unique capabilities for image comparison through its low-level access to image manifests and layer content.

**Key features:**

- `crane diff` compares two images at the filesystem level
- `crane manifest` retrieves and compares image manifests
- `crane config` retrieves image configuration (labels, env vars, entrypoint)
- `crane export` extracts full filesystem to stdout for piping to diff tools
- Works directly with OCI registries without a Docker daemon
- Go library can be imported for programmatic image comparison

```bash
# Compare filesystem differences
crane diff registry.example.com/myapp:v1 registry.example.com/myapp:v2

# Compare image manifests (JSON output)
crane manifest registry.example.com/myapp:v1
crane manifest registry.example.com/myapp:v2

# Compare image configurations
crane config registry.example.com/myapp:v1
crane config registry.example.com/myapp:v2

# Export full filesystem and diff with standard tools
crane export registry.example.com/myapp:v1 - | tar -t > v1-files.txt
crane export registry.example.com/myapp:v2 - | tar -t > v2-files.txt
diff v1-files.txt v2-files.txt | head -30

# Pull image to local tarball for offline comparison
crane pull registry.example.com/myapp:v1 myapp-v1.tar
crane pull registry.example.com/myapp:v2 myapp-v2.tar
```

**Strengths:**

- Direct registry access without daemon overhead
- Go library enables programmatic comparison in CI/CD pipelines
- Lightweight binary with minimal dependencies
- Active development (3,881+ GitHub stars)

**Limitations:**

- No package-level comparison
- Filesystem diff output is basic (added/deleted/modified file lists)
- Less user-friendly than container-diff for package comparison

## Comparison Table

| Feature | container-diff | Skopeo | Crane |
|---------|---------------|--------|-------|
| Package diff (apt/rpm/pip/npm) | Yes | No | No |
| Filesystem diff | Yes | Yes | Yes |
| Metadata comparison | No | Yes | Yes |
| Manifest comparison | No | Yes (`inspect --raw`) | Yes (`manifest`) |
| Local daemon support | Yes | Yes | No |
| Registry-to-registry diff | Yes | Yes | Yes |
| JSON output | Yes | No | No (raw JSON for manifests) |
| Image signing | No | Yes | No |
| Image copying | No | Yes | Yes |
| Docker daemon required | Optional | No | No |
| GitHub stars | 3,801 | 10,895 | 3,881 |
| Last active | 2024-03 | 2026-05 | 2026-05 |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Choosing the Right Tool

**Use container-diff when:**
- You need to compare installed packages between image versions
- You are auditing dependency changes (security patch verification)
- You need structured JSON output for automated pipelines
- You are working with Python, Node.js, or Go application images

**Use skopeo when:**
- You need comprehensive image metadata inspection
- You want to compare image labels, environment variables, or architecture
- You need to copy images between registries as part of your workflow
- You are working in a Podman/Buidah ecosystem

**Use crane when:**
- You need programmatic image comparison in Go applications
- You want to compare image manifests and configurations
- You prefer a minimal, single-binary CLI tool
- You are working directly with OCI registries in CI/CD pipelines

## Deployment and Installation

### Installing container-diff

```bash
# Download latest release
curl -LO https://github.com/GoogleContainerTools/container-diff/releases/download/v0.17.0/container-diff-linux-amd64
chmod +x container-diff-linux-amd64
sudo mv container-diff-linux-amd64 /usr/local/bin/container-diff

# Verify installation
container-diff version
```

### Installing Skopeo

```bash
# Debian/Ubuntu
sudo apt-get install -y skopeo

# RHEL/CentOS/Fedora
sudo dnf install -y skopeo

# macOS
brew install skopeo

# Verify
skopeo --version
```

### Installing Crane

```bash
# Using Go
go install github.com/google/go-containerregistry/cmd/crane@latest

# Or download binary
curl -LO https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz
tar -xzf go-containerregistry_Linux_x86_64.tar.gz crane
sudo mv crane /usr/local/bin/

# Verify
crane version
```

## Docker-Based Comparison Workflow

For CI/CD pipelines, running these tools in containers ensures consistent behavior across environments:

```yaml
version: "3.8"
services:
  image-diff:
    image: quay.io/skopeo/stable:latest
    volumes:
      - ./output:/output:rw
    command: |
      skopeo diff docker://myapp:v1 docker://myapp:v2 > /output/diff.txt

  image-inspect:
    image: gcr.io/go-containerregistry/crane:latest
    volumes:
      - ./output:/output:rw
    command: |
      crane manifest registry.example.com/myapp:v1 > /output/v1-manifest.json
      crane manifest registry.example.com/myapp:v2 > /output/v2-manifest.json
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Container Image Diff & Comparison — container-diff vs Skopeo vs Crane Guide (2026)",
  "description": "Compare container image diff tools — Google container-diff, Red Hat skopeo, and Google crane. Learn which tool is best for package comparison, filesystem diff, and metadata inspection in CI/CD pipelines.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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

### What is the difference between container-diff and skopeo diff?

container-diff focuses on **package-level comparison** — it parses apt, rpm, pip, npm, and Go package databases to show which packages changed between images. Skopeo diff performs **filesystem-level comparison**, showing which files were added, removed, or modified. Use container-diff for dependency auditing, skopeo for filesystem change tracking.

### Can I compare images without pulling them locally?

Skopeo and crane both support registry-level operations that minimize local downloads. Skopeo `inspect` retrieves metadata without pulling layers. Crane `manifest` and `config` fetch only the image manifest and configuration blobs. However, filesystem-level diffs require downloading layer content. container-diff requires full image access for package parsing.

### Does container-diff still receive updates?

container-diff entered maintenance mode in 2024. It still works reliably for package comparison but does not receive feature updates. For actively maintained alternatives, skopeo and crane are both under active development.

### Which tool is best for CI/CD pipeline integration?

container-diff provides structured JSON output (`--json` flag) that is easiest to parse in automated pipelines. crane also supports JSON output for manifest and config inspection. skopeo's output is primarily human-readable text, though `inspect --format` supports Go templates for custom formatting.

### Can these tools compare images across different registries?

Yes. All three tools support comparing images from different registries (Docker Hub, GHCR, Quay, private registries). You simply pass the full image reference including the registry hostname. For private registries, configure authentication via Docker config.json or tool-specific credential flags.

### How do I compare image sizes between versions?

skopeo `inspect` shows the total image size and individual layer sizes. crane `manifest` provides layer digests and sizes in the JSON output. container-diff does not include size information in its diff output.

## Why Compare Container Images?

Tracking changes between container image versions is critical for reliable deployments. When a new image version causes issues in production, being able to quickly identify what changed — whether it is a package version bump, a new file, a removed dependency, or a changed environment variable — can dramatically reduce mean time to resolution.

For broader container image lifecycle management, see our [container image lifecycle guide](../2026-05-02-self-hosted-container-image-lifecycle-management-harbor-registry-ui/), [container image optimization techniques](../2026-04-28-dive-vs-slimtoolkit-vs-hadolint-container-image-optimization-guide-2026/), and [container image scanning workflows](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/).

Regular image comparison also supports compliance requirements — proving that production images match approved builds, detecting unauthorized package installations, and verifying that security patches were applied correctly across all deployed images.
