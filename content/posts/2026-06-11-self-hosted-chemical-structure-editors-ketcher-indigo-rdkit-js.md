---
title: "Self-Hosted Web-Based Chemical Structure Editors: Ketcher vs Indigo vs RDKit JS"
date: "2026-06-11"
tags: ["cheminformatics", "chemistry", "scientific-software", "docker", "molecule-editor", "research-tools", "laboratory"]
draft: false
---

## Introduction

Chemical structure editors are the digital sketchpads of modern chemistry — they allow researchers to draw, visualize, and manipulate molecular structures directly in a web browser. Whether you're designing drug candidates, documenting synthetic pathways, or building chemical databases, a web-based structure editor eliminates the need for desktop software installations and enables collaborative workflows.

In this article, we compare three leading open-source web-based chemical structure tools: **Ketcher** (EPAM's full-featured molecule editor), **Indigo** (the cheminformatics engine powering Ketcher), and **RDKit JS** (the JavaScript compilation of the industry-standard RDKit toolkit).

## Comparison Table

| Feature | Ketcher | Indigo | RDKit JS |
|---------|---------|--------|----------|
| **Primary Function** | Interactive molecule editor | Cheminformatics toolkit | Cheminformatics + visualization |
| **Web Interface** | Full GUI editor | API/library (no GUI) | JS library (embeddable) |
| **Deployment** | Docker / static files | Docker / Python package | NPM / CDN script tag |
| **Structure Input** | Draw, paste SMILES/InChI, import MOL/SDF | SMILES, InChI, MOL, SDF, CML | SMILES, InChI, MOL, SDF |
| **Search Capabilities** | Substructure, similarity, exact match | Substructure, tautomer, similarity | Substructure, similarity (via Python) |
| **Stereochemistry** | Full support (enhanced stereo) | Full support | Full support (CIP assignment) |
| **Reaction Support** | Yes (reactants → products) | Yes (reaction fingerprints) | Limited (focused on molecules) |
| **File Export** | SVG, PNG, MOL, SDF, SMILES, InChI, CDX | MOL, SDF, SMILES, InChI, CML | SVG, PNG (via JS canvas) |
| **GitHub Stars** | 810+ | 397+ | 233+ |
| **Language** | TypeScript/React | C++ with Python/Java/.NET wrappers | JavaScript (Emscripten from C++) |

## Ketcher: The Full-Featured Web Editor

[Ketcher](https://github.com/epam/ketcher), developed by EPAM Life Sciences, is the most complete open-source web-based chemical structure editor available. It provides a desktop-quality drawing experience entirely in the browser, with support for complex features like enhanced stereochemistry, query features, and polymer notation.

### Key Features

- **Professional drawing tools**: Bond drawing, atom placement, ring templates, chain tools, and reaction arrows
- **Multiple input modes**: Draw freely or paste SMILES, InChI, MOL/SDF formats
- **Enhanced stereochemistry**: Support for AND/OR stereochemistry groups and relative stereochemistry
- **Template library**: Built-in functional groups, ring systems, and amino acids
- **Reaction editing**: Draw full chemical reactions with reactants, reagents, and products
- **Server mode**: Deploy as a standalone web application with Docker
- **REST API integration**: Connect to Indigo services for structure validation, format conversion, and property calculation
- **CDX import/export**: Compatibility with ChemDraw files for academic-industry workflows

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ketcher:
    image: ghcr.io/epam/ketcher:latest
    container_name: ketcher
    ports:
      - "4000:80"
    restart: unless-stopped

  indigo-service:
    image: ghcr.io/epam/indigo-service:latest
    container_name: indigo-service
    ports:
      - "8002:8002"
    environment:
      - INDIGO_UWSGI_RUN_DIRECTORY=/tmp
      - PYTHONPATH=/srv/indigo-python
    restart: unless-stopped
```

Ketcher's editor interface can also be embedded into your own web application via an iframe or as a React component, making it ideal for electronic lab notebooks (ELNs), compound registration systems, and chemical inventory platforms.

## Indigo: The Cheminformatics Engine

[Indigo](https://github.com/epam/Indigo) is the computational powerhouse that underpins Ketcher. It's a universal cheminformatics toolkit written in C++ with bindings for Python, Java, and .NET. While Ketcher provides the drawing interface, Indigo handles everything happening behind the scenes — structure canonicalization, substructure matching, tautomer enumeration, and format conversion.

### Key Features

- **Canonical SMILES**: Deterministic structure representation for database deduplication
- **Substructure search**: Find molecular fragments within larger structures
- **Similarity search**: Tanimoto-based molecular similarity with multiple fingerprint types
- **Tautomer handling**: Automatic tautomer enumeration and canonical tautomer generation
- **Format conversion**: Convert between SMILES, InChI, MOL, SDF, RDF, CML, and CDX
- **Reaction processing**: Reaction fingerprint generation and reaction mapping
- **Exact structure search**: Find identical structures considering stereochemistry
- **Layout generation**: Automatic 2D coordinate generation for structure diagrams

### Docker Compose Deployment (Standalone)

```yaml
version: "3.8"
services:
  indigo:
    image: ghcr.io/epam/indigo-service:latest
    container_name: indigo-service
    ports:
      - "8002:8002"
    restart: unless-stopped
```

### Python API Example

```python
from indigo import Indigo

indigo = Indigo()

# Load a molecule from SMILES
molecule = indigo.loadMolecule("CC(=O)Oc1ccccc1C(=O)O")

# Canonicalize SMILES
canonical = molecule.canonicalSmiles()
print(f"Canonical SMILES: {canonical}")

# Calculate molecular weight
print(f"Molecular Weight: {molecule.molecularWeight()}")

# Generate InChI key
print(f"InChI Key: {molecule.inchiKey()}")

# Check for substructure
carboxyl = indigo.loadSmarts("C(=O)O")
matcher = indigo.substructureMatcher(molecule)
match_count = matcher.countMatches(carboxyl)
print(f"Carboxyl groups found: {match_count}")
```

## RDKit JS: The Industry Standard, in Your Browser

[RDKit JS](https://github.com/rdkit/rdkit-js) brings the battle-tested RDKit cheminformatics library — used by major pharmaceutical companies worldwide — directly into the browser. Compiled from C++ to WebAssembly via Emscripten, it provides near-native performance for structure manipulation, similarity searching, and visualization entirely client-side.

### Key Features

- **MinimalDrawer**: SVG-based 2D structure rendering with customizable styling
- **Substructure highlighting**: Highlight matching atoms and bonds in search results
- **Descriptors**: Calculate molecular weight, LogP, H-bond donors/acceptors, topological polar surface area
- **Fingerprints**: Morgan (circular), MACCS keys, Atom Pair, and Torsion fingerprints
- **Similarity search**: Tanimoto and Dice similarity calculations
- **Force field minimization**: MMFF94-based 3D structure optimization in the browser
- **Zero server dependency**: All computation happens client-side — no backend required

### Integration via NPM

```bash
npm install @rdkit/rdkit
```

```javascript
import initRDKitModule from "@rdkit/rdkit";

const RDKit = await initRDKitModule();

// Parse a molecule from SMILES
const mol = RDKit.get_mol("CC(=O)Oc1ccccc1C(=O)O");

// Generate SVG for display
const svg = mol.get_svg(400, 300);
document.getElementById("molecule-view").innerHTML = svg;

// Calculate descriptors
console.log("Molecular Weight:", mol.get_molwt());
console.log("LogP:", mol.get_descriptor("MolLogP"));

// Generate fingerprint for similarity search
const fingerprint = mol.get_morgan_fp();

// Clean up
mol.delete();
```

### HTML Integration (CDN)

```html
<script src="https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js"></script>
<script>
  window.initRDKitModule().then(function(RDKit) {
    const mol = RDKit.get_mol("c1ccccc1");
    const svg = mol.get_svg(300, 200);
    document.getElementById("mol-view").innerHTML = svg;
    mol.delete();
  });
</script>
<div id="mol-view"></div>
```

## Integration Scenarios

These three tools work best together, not as competitors:

**Ketcher as the frontend + Indigo as the backend**: Embed Ketcher's editor in your ELN or compound registration system, with Indigo processing structures server-side for validation, similarity searching, and database lookups.

**RDKit JS for lightweight embedding**: When you need molecule visualization in search results, dashboards, or data tables without a full editor, RDKit JS provides SVG rendering with minimal footprint.

**Hybrid architecture**: Use RDKit JS for client-side similarity screening (avoiding server round-trips), Ketcher for structure input, and Indigo for authoritative canonicalization and database indexing.

## Why Self-Host Your Chemical Structure Tools?

Pharmaceutical and chemical research involves proprietary compound structures that represent years of R&D investment. Uploading those structures to cloud-based editors — even "free" academic ones — means trusting a third party with your intellectual property.

Self-hosting chemical structure tools ensures your molecular data stays within your organization's infrastructure. This is particularly important for contract research organizations (CROs) working under client NDAs, biotech startups protecting patent-pending compounds, and academic labs collaborating with industry partners under material transfer agreements.

For labs already running [self-hosted cheminformatics platforms with RDKit, OpenBabel, and CDK](../2026-06-09-self-hosted-cheminformatics-rdkit-openbabel-cdk-guide/), Ketcher and Indigo provide the interactive frontend and processing backend those toolkit installations need. And for [computational chemistry workflows](../2026-06-10-self-hosted-computational-chemistry-engines-pyscf-psi4-nwchem/), structure editors are the starting point — every simulation begins with a molecular structure drawn by a chemist.

Compared to desktop alternatives like ChemDraw (proprietary, expensive) or Marvin (freemium), these open-source web tools provide comparable functionality with zero licensing costs and the flexibility to integrate into custom research platforms. Our [guide to molecular visualization tools](../2026-06-09-self-hosted-molecular-visualization-molstar-3dmoljs-nglview-ngl/) covers complementary 3D structure viewers that pair well with these 2D editors.

## Choosing the Right Tool

**Choose Ketcher if:**
- You need a complete, ready-to-use chemical structure editor
- Desktop-quality drawing experience matters
- You want CDX import/export for ChemDraw compatibility
- Your users include synthetic chemists who draw reactions

**Choose Indigo if:**
- You're building a custom cheminformatics backend
- You need server-side structure processing at scale
- Database indexing and substructure search are priorities
- You need Python/Java/.NET API access

**Choose RDKit JS if:**
- You need lightweight molecule rendering in existing web apps
- Client-side fingerprinting and similarity screening are important
- You want zero backend dependencies for structure visualization
- Your team already uses RDKit in Python and wants web parity

## FAQ

### Can Ketcher work without Indigo as a backend?

Yes, Ketcher functions as a standalone editor without Indigo. Basic drawing, structure editing, and SMILES/MOL export work independently. However, advanced features — aromatization, stereochemistry perception, canonicalization, format conversion beyond basic formats — require an Indigo service connection.

### How does RDKit JS performance compare to Python RDKit?

RDKit JS uses WebAssembly compiled from the same C++ codebase, so computation speed is comparable to native RDKit for most operations. However, very large molecules (10,000+ atoms) may be 2-3x slower in browser compared to native. The browser also has memory constraints — molecules with 50,000+ atoms may exceed available memory.

### Are these tools suitable for regulated environments (GxP, 21 CFR Part 11)?

Ketcher and Indigo are used in pharmaceutical R&D environments and can be deployed in validated systems. For GxP compliance, you'll need to implement audit trails, electronic signatures, and access controls at the application level — these tools provide the chemical editing functionality, not the regulatory framework. RDKit JS is more commonly used in early-stage research.

### Can I customize the toolbar and templates in Ketcher?

Yes, Ketcher supports extensive customization. You can add custom functional group templates, modify the toolbar layout, configure default settings, and even change the styling through CSS and React component props. The editor is designed to be embedded and customized for specific use cases.

### What's the difference between Indigo standalone and Indigo as a service?

Indigo can be used as a Python/Java library (installed via pip or maven), as a Docker-based REST service, or embedded in C++ applications. The REST service mode (indigo-service Docker image) is the most common deployment method — it provides HTTP endpoints for structure operations, making it accessible from any programming language.

### Do these tools support biological molecules (proteins, DNA, RNA)?

Ketcher supports HELM notation for biologics and can render peptides and oligonucleotides. Indigo has limited support for large biomolecules — it handles peptides up to ~100 residues but isn't designed for full protein structures. For macromolecular visualization, pair these tools with [Mol* or NGL Viewer](../2026-06-09-self-hosted-molecular-visualization-molstar-3dmoljs-nglview-ngl/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Web-Based Chemical Structure Editors: Ketcher vs Indigo vs RDKit JS",
  "description": "Compare Ketcher, Indigo, and RDKit JS for self-hosted web-based chemical structure editing. Covers Docker deployment, cheminformatics APIs, and integration with ELN platforms.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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
