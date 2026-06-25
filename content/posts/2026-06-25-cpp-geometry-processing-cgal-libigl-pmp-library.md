---
title: "Self-Hosted C++ Geometry Processing: CGAL vs libigl vs PMP Library"
date: "2026-06-25"
tags: ["c++", "computational-geometry", "mesh-processing", "3d-graphics", "libraries", "scientific-computing"]
draft: false
---

## Introduction

Computational geometry and mesh processing power applications ranging from computer-aided design (CAD) and building information modeling (BIM) to 3D printing, robotics simulation, and scientific visualization. Behind these applications sit geometry processing libraries that implement decades of research in mesh simplification, Boolean operations, surface reconstruction, and geodesic distance computation.

For C++ developers building self-hosted geometry processing services, the choice of library determines not only what operations are available but also licensing constraints, build complexity, and integration with existing 3D asset pipelines. This article compares three leading C++ geometry processing libraries — CGAL, libigl, and the PMP (Polygon Mesh Processing) Library — across features, performance, and practical applicability.

## Comparison: CGAL vs libigl vs PMP Library

| Feature | CGAL | libigl | PMP Library |
|---------|------|--------|-------------|
| GitHub Stars | 5,954 | 5,037 | 1,489 |
| License | GPLv3+ / Commercial | MPL-2.0 | MIT |
| C++ Standard | C++17 | C++17 | C++17 |
| Dependency Model | Header-only core + compiled components | Header-only | Header-only |
| Mesh Data Structure | Halfedge, Polyhedron, Surface_mesh | Eigen-based matrices | Dynamic property-based |
| Boolean Operations | Yes (Nef polyhedra, corefinement) | Via CGAL or Cork | No |
| Mesh Simplification | Yes (Edge collapse, Lindstrom-Turk) | Yes (qslim, decimate) | Yes (quadric error metric) |
| Surface Reconstruction | Yes (Poisson, Advancing Front) | No (use CGAL) | No |
| Remeshing | Yes (isotropic, anisotropic) | Yes (local operators) | Yes (uniform/adaptive) |
| Geodesic Distances | Yes (exact, heat method) | Yes (heat method) | Yes (heat method) |
| Parameterization | Yes (multiple methods) | Yes (Tutte, LSCM, ARAP) | No |
| Geometry Processing | Yes (full pipeline) | Yes (core operations) | Yes (mesh-focused) |
| Python Bindings | Yes (cgal-swig-bindings) | Yes (libigl-python) | Yes (pmpython) |
| Last Updated | Jun 2026 | May 2026 | May 2026 |

### CGAL (Computational Geometry Algorithms Library)

[CGAL](https://github.com/CGAL/cgal) is the most comprehensive computational geometry library available in any language, with 5,954 GitHub stars and a 25+ year development history. Originating from a European research consortium in 1996, CGAL provides exact arithmetic kernels, Nef polyhedra for Boolean operations, and exhaustive algorithm coverage spanning 2D/3D geometry, mesh generation, and spatial searching.

```cpp
// CGAL — Boolean difference operation with exact arithmetic
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Polyhedron_3.h>
#include <CGAL/Nef_polyhedron_3.h>

using Kernel = CGAL::Exact_predicates_inexact_constructions_kernel;
using Polyhedron = CGAL::Polyhedron_3<Kernel>;
using Nef_polyhedron = CGAL::Nef_polyhedron_3<Kernel>;

Polyhedron mesh_a, mesh_b;
// Load STL/OBJ files...
load_mesh("part_a.stl", mesh_a);
load_mesh("part_b.stl", mesh_b);

Nef_polyhedron nef_a(mesh_a), nef_b(mesh_b);
Nef_polyhedron result = nef_a - nef_b;  // Exact Boolean difference
Polyhedron output;
result.convert_to_polyhedron(output);
```

CGAL's exact arithmetic kernel eliminates floating-point robustness issues that plague Boolean operations in other libraries — a critical feature for CAD and manufacturing workflows where topological correctness is non-negotiable. The main trade-off is licensing: CGAL's core is dual-licensed under GPLv3+ and a commercial license, which may restrict integration into proprietary self-hosted services unless you purchase a commercial license.

### libigl

[libigl](https://github.com/libigl/libigl) by Alec Jacobson, Daniele Panozzo, and collaborators provides a modern, minimalist geometry processing library with 5,037 stars. It represents meshes using Eigen matrices (V for vertices as N×3 matrix, F for faces as M×3 matrix), making the API immediately familiar to anyone who has worked with MATLAB or NumPy.

```cpp
// libigl — mesh smoothing with Laplacian
#include <igl/cotmatrix.h>
#include <igl/massmatrix.h>
#include <igl/readOBJ.h>

Eigen::MatrixXd V;  // Vertices
Eigen::MatrixXi F;  // Faces
igl::readOBJ("scan.obj", V, F);

Eigen::SparseMatrix<double> L;
igl::cotmatrix(V, F, L);
Eigen::SparseMatrix<double> M;
igl::massmatrix(V, F, igl::MASSMATRIX_TYPE_BARYCENTRIC, M);

// Solve (M - lambda*L) * V_smooth = M * V
Eigen::SimplicialLDLT<Eigen::SparseMatrix<double>> solver(M - 0.001 * L);
Eigen::MatrixXd V_smooth = solver.solve(M * V);
```

libigl's matrix-based representation is remarkably concise — most operations are one-liner function calls. The library is licensed under MPL-2.0, making it fully compatible with commercial self-hosted services without licensing fees. However, libigl intentionally omits advanced operations like Boolean mesh operations and surface reconstruction, deferring those to external libraries.

### PMP Library (Polygon Mesh Processing)

[PMP Library](https://github.com/pmp-library/pmp-library) by Daniel Sieger and Mario Botsch provides a focused, self-contained mesh processing library with 1,489 stars. Unlike CGAL's exhaustive scope or libigl's dependency on external libraries for advanced operations, PMP targets the sweet spot of mesh processing: smoothing, decimation, remeshing, hole filling, and subdivision.

```cpp
// PMP Library — mesh subdivision and smoothing
#include <pmp/SurfaceMesh.h>
#include <pmp/algorithms/SurfaceSubdivision.h>
#include <pmp/algorithms/SurfaceSmoothing.h>
#include <pmp/io/io.h>

pmp::SurfaceMesh mesh;
pmp::read_off(mesh, "bunny.off");

// Catmull-Clark subdivision
pmp::SurfaceSubdivision subdiv(mesh);
subdiv.catmull_clark();
subdiv.catmull_clark();  // Two subdivision steps

// Explicit Laplacian smoothing
pmp::SurfaceSmoothing smoother(mesh);
smoother.explicit_smoothing(10, 0.5);  // 10 iterations, lambda=0.5

pmp::write_off(mesh, "bunny_smooth.off");
```

PMP's SurfaceMesh data structure uses a property-based system where you attach arbitrary attributes (normals, colors, texture coordinates) to mesh elements without modifying vertex structures. This flexibility is essential for geometry processing pipelines where intermediate data flows between operations. The MIT license makes PMP ideal for unrestricted commercial use.

## Integration with 3D Asset Pipelines

Self-hosted geometry processing services typically consume and produce standard 3D file formats. All three libraries support common formats:

```cpp
// Format support across libraries
// CGAL:   OFF, STL, OBJ, PLY, VTK (via dedicated I/O packages)
// libigl: OBJ, OFF, STL, PLY, WRL, MESH, XML
// PMP:    OFF, OBJ, STL, PLY
```

For server-side geometry services, consider wrapping the processing logic in a REST API using a C++ HTTP library like cpp-httplib or Beast. The service accepts mesh files via multipart upload, processes them using one of these libraries, and returns the processed file:

```bash
# Docker Compose for a geometry processing REST service
version: "3.8"
services:
  mesh-processor:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./uploads:/tmp/uploads
      - ./outputs:/tmp/outputs
    environment:
      - MAX_FILE_SIZE=500M
      - CGAL_DIR=/usr/lib/cmake/CGAL
```

## Why Self-Host Your Geometry Processing

Outsourcing 3D mesh processing to cloud services introduces latency, file size limits, and data privacy concerns — especially for proprietary CAD models and architectural BIM data. A self-hosted geometry processing service keeps your 3D assets on-premises and scales to handle files that exceed cloud provider upload limits.

For BIM and architectural workflows, self-hosted geometry services integrate directly with IFC models and point cloud data. See our [guide to self-hosted BIM servers](../2026-06-09-self-hosted-bim-servers-bimserver-ifcopenshell-xeokit-guide/) for the full stack from model storage to web-based 3D visualization. If your pipeline includes 3D printing, check our [self-hosted 3D printer server guide](../2026-04-20-octoprint-vs-mainsail-vs-fluidd-self-hosted-3d-printer-server-guide-2026/) for the print management layer. For physics simulation that builds on geometry processing, our [scientific simulation guide](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) covers the next step in the engineering pipeline.

## FAQ

### Which library handles Boolean operations robustly?

Only CGAL provides production-quality Boolean operations via its exact arithmetic kernel and Nef polyhedra. The corefinement-based Boolean operations (introduced in CGAL 4.12) handle most practical cases efficiently. libigl can wrap CGAL's Boolean operations, and PMP does not implement Boolean operations at all. For CAD and manufacturing applications requiring mesh Booleans, CGAL is the only viable choice among these three.

### Why does CGAL use GPL licensing?

CGAL's core is developed through publicly funded research and the project chose GPL to ensure improvements remain open. Commercial licenses are available for proprietary integration. libigl (MPL-2.0) and PMP (MIT) are fully permissive for commercial use. If your self-hosted service is internal (not distributed), GPL code can be used without restriction — the distribution trigger is what matters.

### Can I use these libraries in a GPU-accelerated pipeline?

None of these libraries natively leverage GPU compute (CUDA/OpenCL) for mesh processing. For GPU-accelerated geometry, consider integrating with libraries like OpenMesh (GPU-based remeshing), or wrapping individual expensive operations in custom CUDA kernels. libigl's matrix representation maps naturally to GPU computation since Eigen matrices can be transferred to CUDA device memory via Thrust.

### How do these compare for teaching and research?

libigl is the dominant choice in geometry processing research due to its MATLAB-like matrix API and minimal boilerplate. Most SIGGRAPH geometry processing courses since 2014 use libigl for code examples. CGAL is preferred in computational geometry research communities where exact arithmetic matters. PMP is commonly used in mesh processing courses due to its clean, self-contained codebase.

### What about mesh repair and validation?

CGAL provides the most comprehensive mesh repair toolkit via its Polygon Mesh Processing package, including self-intersection removal, orientation fixing, and manifold conversion. PMP provides basic repair (duplicate vertex removal, degenerate face detection). libigl delegates repair to CGAL or external tools. For self-hosted services ingesting user-uploaded meshes of varying quality, CGAL's repair pipeline significantly reduces downstream errors.

### Which library is easiest to build and deploy?

PMP is the easiest: pure CMake with zero mandatory external dependencies beyond a C++17 compiler (fetch everything via FetchContent). libigl similarly uses CMake with optional dependencies. CGAL requires the most setup: Boost, GMP, MPFR, and (optionally) Qt for demos. For Docker-based self-hosted services, PMP and libigl can be one-line apt installs; CGAL requires adding the CGAL PPA or building from source.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Geometry Processing: CGAL vs libigl vs PMP Library",
  "description": "Compare three C++ geometry processing libraries for self-hosted 3D mesh processing services: CGAL (comprehensive, exact arithmetic, GPL), libigl (matrix-based, MPL-2.0, research standard), and PMP Library (focused mesh processing, MIT, easy integration).",
  "datePublished": "2026-06-25",
  "dateModified": "2026-06-25",
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
