---
title: "OpenVEX vs CSAF vs CycloneDX VEX in 2026: Which Format Actually Silences Your Scanner?"
date: "2026-11-26"
tags: ["security", "sbom", "vulnerability-management", "supply-chain", "devsecops"]
draft: false
---

A typical container image scan on a mid-sized Rust or Go service returns **300 to 600 findings**. In most engineering organisations, somewhere between 60% and 90% of those CVEs are not exploitable in that specific product: the vulnerable function is never called, the package is present only in a build stage, or the code path is unreachable behind a feature flag. Teams deal with this the way they deal with all noise — they ignore the scanner. Then a genuinely critical finding arrives and nobody looks.

VEX (*Vulnerability Exploitability eXchange*) exists to fix exactly that: it is a machine-readable, signed statement that says **"this CVE does not affect this product, and here is why"**. Three formats compete for the job in 2026 — **OpenVEX**, **CSAF 2.0**, and **CycloneDX VEX** — and they are not interchangeable. Choosing wrong means your suppressions never reach your scanner.

## TL;DR — Quick Verdict

- **You want Trivy, Grype, or a CI gate to stop failing on non-exploitable CVEs** → **OpenVEX**. It is the smallest format, easiest to generate, and the one open-source scanners actually parse.
- **You publish advisories to customers, a regulator, or a CERT** → **CSAF 2.0**. It is a ratified OASIS standard with signatures, provider metadata, and aggregator feeds.
- **You already ship CycloneDX SBOMs and use Dependency-Track** → **CycloneDX VEX**. One artifact, one signature, one platform.

The blunt rule: **OpenVEX is for suppressing, CSAF is for publishing, CycloneDX VEX is for shipping alongside your SBOM.** Teams that need all three usually generate OpenVEX internally and derive CSAF for external distribution.

## Format Comparison (data pulled 2026-11-26)

| Dimension | OpenVEX | CSAF 2.0 (VEX profile) | CycloneDX VEX |
|---|---|---|---|
| **Reference tool** | `openvex/vexctl` | `gocsaf/csaf` | `CycloneDX/cyclonedx-cli` |
| **GitHub stars** | 222 | 73 | 564 |
| **Last commit** | 2026-11-25 | 2026-11-26 | 2026-10-19 |
| **Tool language** | Go | Go | C# |
| **Spec body** | OpenVEX (openvex.dev) | OASIS standard | CycloneDX / OWASP |
| **Document shape** | Flat `statements[]` array | Nested `product_tree` + `vulnerabilities[]` | `vulnerabilities[]` inside a BOM |
| **Typical size for 50 CVEs** | ~15 KB | ~120 KB | ~40 KB (without components) |
| **Signing** | sigstore attestation via `cosign` | OpenPGP / detached signatures | BOM signature (`cyclonedx-cli sign`) |
| **Machine distribution** | Attached to image or stored in repo | ROLIE feeds + `provider-metadata.json` | SBOM registry / dependency platform |
| **Open-source scanner support** | Trivy, Grype | Limited | Dependency-Track, some scanners |
| **Learning curve** | Minutes | Days | Hours |
| **Best for** | CI suppression | Regulated advisory publishing | SBOM-native pipelines |

The star counts are tiny by comparison with infrastructure projects — 222, 73, and 564 — and that is the most important signal in this table. VEX tooling is young. Budget for reading source code, not just documentation.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Recommended format | Why |
|---|---|---|
| CI blocks merges on 400 CVEs, 380 unreachable | **OpenVEX** | Scanners parse it; `vexctl create` is a one-liner |
| You must answer a customer security questionnaire | **CSAF** | Signed advisory with machine-readable product tree |
| Regulator or national CERT requires advisory feeds | **CSAF** | ROLIE + provider metadata is the standard delivery mechanism |
| You already run Dependency-Track | **CycloneDX VEX** | Native ingestion, no conversion step |
| You need one signed artifact per release | **CycloneDX VEX** | BOM signing plus VEX in the same file |
| You need per-image suppressions in a registry | **OpenVEX** | Attestation attaches to the image digest |
| You sell software into the EU public sector | **CSAF** + **OpenVEX** | Publish CSAF, suppress internally with OpenVEX |

## OpenVEX — The Format Scanners Actually Read

OpenVEX is deliberately minimal. A document is an `@context`, an author, a timestamp, a version, and a flat array of statements. Each statement names a vulnerability, a set of products (as package URLs), a status, and — for `not_affected` — a justification from a fixed list.

```bash
# Install
go install github.com/openvex/vexctl@latest
# or: brew install vexctl
```

Creating a statement is a single command. This one declares that a Wolfi package is unaffected because the mitigation is already in the distribution:

```bash
vexctl create \
  --product="pkg:apk/wolfi/git@2.38.1-r0?arch=x86_64" \
  --vuln="CVE-2014-123456" \
  --status="not_affected" \
  --justification="inline_mitigations_already_exist" \
  --file=git.vex.json
```

The result is small enough to review in a pull request:

```json
{
  "@context": "https://openvex.dev/ns/v0.2.0",
  "@id": "https://openvex.dev/docs/public/vex-adc52fe6c8d2ba0feee7f4343f9b40c90e8cdb077817f880a6650502aece82bc",
  "author": "Unknown Author",
  "timestamp": "2026-11-26T09:12:07Z",
  "version": 1,
  "statements": [
    {
      "vulnerability": { "name": "CVE-2014-123456" },
      "timestamp": "2026-11-26T09:12:07Z",
      "products": [
        { "@id": "pkg:apk/wolfi/git@2.38.1-r0?arch=x86_64" }
      ],
      "status": "not_affected",
      "justification": "inline_mitigations_already_exist"
    }
  ]
}
```

Three operational commands matter more than creation:

```bash
# Validate against the spec before committing — catches typos in status enums
vexctl validate vex.json
vexctl validate --strict .openvex/*.json      # fail on warnings too
vexctl validate --format=json vex.json         # machine-readable output

# Merge statements from multiple teams into one current assessment
vexctl merge --product=pkg:apk/wolfi/bash@1.0.0 \
  team-a.vex.json team-b.vex.json > merged.vex.json

# Attach a signed attestation to a container image digest
vexctl attest --attach --sign service.vex.json \
  registry.internal/api@sha256:e4cf37d568d195b4...
```

Merging matters more than it sounds: when two stakeholders issue statements about the same CVE, `vexctl merge` produces the current truth (for example `under_investigation` followed by `fixed` four hours later) instead of leaving a conflict for a human to untangle.

**The trap:** OpenVEX suppressions only work if the product identifier in the statement matches what the scanner reports. Scanners usually identify components by purl, so a statement about `pkg:apk/wolfi/git@2.38.1-r0` silently fails to suppress a finding for `pkg:apk/wolfi/git@2.38.1-r1`. Pin exact versions and regenerate VEX on every dependency bump, or your CI gate will quietly start failing again.

## CSAF 2.0 — Publishing Advisories Like a Vendor

CSAF (Common Security Advisory Framework) is the heavyweight option, and it is the only one of the three that is an OASIS standard with a governance process behind it. A CSAF document contains a `document` block (tracking ID, publisher, revision history), a `product_tree` describing every affected product by branch and full product name, `vulnerabilities` with remediations and threat intelligence, and optional VEX status per product.

That structure is why it is verbose — and why it is trusted by CERTs and regulators. German authorities in particular have pushed CSAF hard, and the BSI-funded `gocsaf/csaf` toolkit (73 stars, updated as recently as 2026-11-26) is the reference implementation, shipping six separate binaries:

```bash
# Prebuilt binaries are recommended over building from source
./csaf_downloader example.com -d ./advisories
./csaf_downloader -d ./advisories --worker=4 --time_range="P30D" vendor.example

# Other tools in the same release:
#   csaf_checker    — validate a provider's feed and metadata
#   csaf_validator  — validate individual documents
#   csaf_aggregator — aggregate feeds from several providers
#   csaf_uploader   — publish documents to a csaf_provider instance
#   csaf_provider    — serve your own ROLIE feed
```

Publishing is file-based and boring on purpose: drop documents into a directory served over HTTPS, expose `provider-metadata.json` under `/.well-known/csaf/`, and consumers discover everything through the ROLIE feed. `csaf_checker` then verifies that the whole chain — metadata, feed, signatures, document schema — is valid.

**The trap:** CSAF's `product_tree` is where most implementations fail. A `full_product_name` must be unambiguous across your entire catalogue, and consumers match on it. If your product tree names the same binary two different ways across two advisories, aggregation breaks silently. Also, OpenPGP signing keys must be published and rotated on a schedule that external consumers can follow — a stale key turns every future advisory into an unverifiable one.

## CycloneDX VEX — VEX Inside the BOM

CycloneDX takes a third approach: VEX is not a separate document at all, it is a `vulnerabilities` array inside the BOM you already produce. Each vulnerability entry carries an `analysis` object with a `state` (`resolved`, `resolved_with_pedigree`, `exploitable`, `in_triage`, `false_positive`, `not_affected`), a `justification`, and a `response` array.

That single-artifact design is genuinely convenient: one file lists components, their hashes, and your assessment of their vulnerabilities, all signed together.

```bash
# Validate the BOM (and thus the embedded VEX analysis)
cyclonedx-cli validate --input-file bom.json --input-format json

# Merge VEX from several teams into one BOM
cyclonedx-cli merge --input-files api.json worker.json --output-file merged.json

# Convert for consumers that require XML or SPDX
cyclonedx-cli convert --input-file merged.json --output-file merged.xml

# Same for SPDX consumers
cat merged.json | cyclonedx-cli convert \
  --input-format json --output-format spdxjson > merged.spdx.json
```

`cyclonedx-cli` also supports `diff`, `sign`, `verify`, and `keygen`, which makes it viable as the single tool in a pipeline that must produce signed, diffable artifacts per release. Dependency-Track ingests CycloneDX natively, including the `analysis` block, which makes this the path of least resistance for teams already on that platform.

**The trap:** CycloneDX VEX is only as good as the BOM's completeness. If your SBOM generation misses transitive dependencies or records them without purls, the VEX statements cannot be matched and the platform shows the vulnerability as unanalysed. Validate that every component in a sample BOM has a purl before you invest in writing suppressions.

## Why Suppressions Keep Failing (And How to Fix Them)

After talking to teams that have run VEX in production, the failures cluster into four causes — and none of them are format problems:

1. **Identifier mismatch.** VEX keyed on CPE, scanner reporting purl (or vice versa). Fix: standardise on purl everywhere and assert it in CI.
2. **Stale statements after upgrades.** A `not_affected` justification based on "vulnerable function not in execute path" becomes a lie the moment someone refactors the call path. Fix: expire VEX statements on a schedule, regenerate on dependency bumps, and review justifications quarterly.
3. **Authority confusion.** Only the supplier can credibly assert `not_affected` for a product. If you consume third-party VEX from an upstream project, treat it as `under_investigation` in your own risk model until you verify it.
4. **Silent non-application.** The scanner exits 0 but keeps reporting the CVE because the flag was never passed, or the VEX file was not loaded. Fix: assert in CI that the finding count actually dropped after VEX is applied — a test that catches the whole class of problem.

If your SBOM pipeline is still being built, start with [container SBOM generators: Syft, Trivy and SPDX](../2026-05-19-self-hosted-container-sbom-generators-syft-trivy-spdx-guide/) and then move to [Dependency-Track, ORT and Syft for SBOM analysis](../2026-05-01-self-hosted-sbom-analysis-dependency-track-ort-syft-guide/). For a platform-level view of ingesting and acting on these documents, our [SBOM dependency tracking guide](../self-hosted-sbom-dependency-tracking-dependency-track-syft-cyclonedx-guide-2026/) covers the operational side.

## FAQ

### What does VEX actually do — does it delete findings?

No. VEX does not remove a component or change an SBOM; it records an assessment that a specific vulnerability does not affect a specific product, with a justification. Whether a finding disappears from your dashboard depends on the consuming tool: some scanners suppress matching findings, others annotate them. Always confirm the behaviour of your specific scanner version rather than assuming suppression happened.

### Is OpenVEX enough, or do I need CSAF?

For internal CI suppression, OpenVEX is enough — it is what Trivy, Grype, and similar tools parse, and `vexctl` covers creation, merge, validation, and signed attestation. You need CSAF when you must publish advisories to external parties (customers, CERTs, regulators) with a formal product tree and feed metadata. Many organisations generate OpenVEX internally and publish CSAF externally.

### Can I convert between the three formats?

Not losslessly. Conversion tools cover parts of the mapping — OpenVEX statements map to CSAF vulnerability entries, and CycloneDX carries similar analysis states — but CSAF's product tree and OpenVEX's flat statement array have different expressive power. The practical approach is to keep one source of truth (usually structured YAML or a database of justifications) and generate each output format from it.

### Which VEX statuses and justifications are valid?

OpenVEX uses four statuses: `not_affected`, `affected`, `fixed`, and `under_investigation`. `not_affected` requires a justification such as `component_not_present`, `vulnerable_code_not_present`, `vulnerable_code_not_in_execute_path`, `vulnerable_code_cannot_be_controlled_by_adversary`, or `inline_mitigations_already_exist`. CycloneDX uses a different state enum plus a separate justification list, and CSAF embeds status inside each product entry. Validate every document before publishing — enum typos are the single most common reason a suppression silently does nothing.

### Do I need to sign VEX documents?

Sign them if anyone outside your team consumes them. `vexctl attest` produces sigstore attestations that attach to an image digest, `cyclonedx-cli sign` signs the BOM, and CSAF expects OpenPGP signatures verified by consumers. Unsigned VEX is fine as an internal CI artifact; signed VEX is mandatory as a supply-chain statement.

### How often should VEX be regenerated?

On every dependency change, plus a scheduled quarterly review of justifications. The biggest real-world risk is a VEX statement that was true six months ago: an upgrade adds the vulnerable code path back, or a refactor makes a previously unreachable function reachable, and the suppression keeps hiding a real finding. Treat VEX like code — version it, review it, and expire it.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenVEX vs CSAF vs CycloneDX VEX in 2026: Which Format Actually Silences Your Scanner?",
  "description": "A practical comparison of the three VEX formats in 2026: OpenVEX with vexctl, CSAF 2.0 advisory publishing, and CycloneDX VEX inside SBOMs — with real commands, scanner support, and failure modes.",
  "datePublished": "2026-11-26",
  "dateModified": "2026-11-26",
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
