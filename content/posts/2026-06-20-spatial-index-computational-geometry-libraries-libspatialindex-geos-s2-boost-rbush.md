---
title: "Self-Hosted Spatial Index and Computational Geometry Libraries: libspatialindex vs GEOS vs S2 Geometry vs Boost.Geometry vs rbush"
date: "2026-06-20"
tags: ["spatial-index", "gis", "computational-geometry", "cpp", "javascript", "geospatial", "r-tree", "geometry"]
draft: false
---

## Introduction

Spatial data is everywhere — from GPS coordinates in mobile apps to geometric shapes in CAD software and polygons in GIS systems. Efficiently querying "what is near this point?" or "do these polygons intersect?" requires specialized data structures and algorithms that standard databases cannot provide out of the box. Spatial index libraries bridge this gap, offering R-trees, quadtrees, and computational geometry primitives optimized for 2D and 3D spatial queries.

This article compares five leading open-source spatial libraries: **libspatialindex** (C++ R-tree), **GEOS** (geometry engine), **S2 Geometry** (spherical indexing), **Boost.Geometry** (C++ template library), and **rbush** (JavaScript R-tree). We evaluate them on indexing algorithms, geometry operations, performance characteristics, and real-world integration.

## Spatial Indexing Fundamentals: R-trees, Quadtrees, and Hilbert Curves

Spatial indexes solve the fundamental problem: given millions of spatial objects (points, lines, polygons), how do you quickly find those within a query region? Traditional B-tree indexes do not work because spatial data lacks a natural total ordering.

The **R-tree** (Rectangle tree) is the most widely used spatial index. It organizes objects into nested bounding rectangles, with each node storing the minimum bounding rectangle of its children. Variants include R*-tree (better insertion strategy), R+-tree (disjoint nodes), and Hilbert R-tree (Hilbert curve ordering for better locality).

**Quadtrees** recursively subdivide space into four quadrants, creating a tree where each node either contains a small number of objects or subdivides further. They are simpler than R-trees but less balanced for non-uniform data distributions.

**Hilbert curves** and other space-filling curves map multi-dimensional coordinates to one-dimensional values while preserving spatial locality. Google's S2 library uses the Hilbert curve to partition the sphere into cells at 30 levels of resolution.

## Feature Comparison Table

| Feature | libspatialindex | GEOS | S2 Geometry | Boost.Geometry | rbush |
|---------|----------------|------|-------------|----------------|-------|
| **Stars** | 790 | 1,475 | 2,681 | 511 | 2,751 |
| **Language** | C++ | C++ | C++ | C++ | JavaScript |
| **Index Types** | R*-tree, MVR-tree, TPR-tree | STRtree, Quadtree | Hilbert curve cells | R-tree | R-tree (bulk-loaded) |
| **Geometry Ops** | Basic | Full (OGC-compliant) | Partial (spherical) | Full (OGC-inspired) | None (index only) |
| **Bulk Loading** | Yes | Yes (STRtree) | N/A | Yes | Yes (default) |
| **Coordinate System** | Cartesian 2D/3D | Cartesian 2D/3D | Spherical (S2 cells) | Cartesian n-D | Cartesian 2D |
| **API Style** | C API | C/C++ API | C++ API | C++ templates | JS API |
| **Standards** | None | OGC Simple Features | None | OGC-inspired | None |
| **Last Updated** | 2026-04 | 2026-06 | 2026-06 | 2026-06 | 2026-06 |
| **License** | MIT | LGPL-2.1 | Apache 2.0 | Boost | MIT |

## libspatialindex: The C++ R-tree Specialist

libspatialindex provides one of the most comprehensive R-tree implementations available. Beyond the standard R-tree, it implements the R*-tree (optimized node splitting), MVR-tree (multi-version R-tree for temporal data), and TPR-tree (time-parameterized R-tree for moving objects).

**Installation:**

```bash
# Debian/Ubuntu
sudo apt install libspatialindex-dev

# macOS
brew install spatialindex

# From source
git clone https://github.com/libspatialindex/libspatialindex.git
cd libspatialindex && mkdir build && cd build
cmake .. && make && sudo make install
```

**Example: R-tree insertion and query:**

```cpp
#include <spatialindex/SpatialIndex.h>
#include <iostream>

using namespace SpatialIndex;

int main() {
    // Create an in-memory R*-tree
    id_type indexIdentifier;
    IStorageManager* storage = StorageManager::createNewMemoryStorageManager();
    ISpatialIndex* tree = RTree::createNewRTree(
        *storage, 0.7, 100, 100, 2,
        RTree::RV_RSTAR, indexIdentifier
    );

    // Insert a point
    double coords[] = {10.0, 20.0};
    Point p(coords, 2);
    tree->insertData(0, nullptr, p, 1);

    // Query: find all objects within a region
    double regionLow[] = {5.0, 15.0};
    double regionHigh[] = {15.0, 25.0};
    Region queryRegion(regionLow, regionHigh, 2);

    class MyVisitor : public IVisitor {
    public:
        void visitNode(const INode&) override {}
        void visitData(const IData& d) override {
            std::cout << "Found object: " << d.getIdentifier() << std::endl;
        }
        void visitData(std::vector<const IData*>& v) override {}
    };

    MyVisitor visitor;
    tree->intersectsWithQuery(queryRegion, visitor);
}
```

libspatialindex is the foundation for many GIS tools and is included as a dependency in Python's `rtree` package and R's `sf` package.

## GEOS: The Complete Geometry Engine

GEOS (Geometry Engine, Open Source) is a C++ port of the Java Topology Suite (JTS). It implements the Open Geospatial Consortium (OGC) Simple Features specification, providing a complete set of geometry operations: union, intersection, difference, buffer, convex hull, and spatial predicates (contains, intersects, touches, overlaps).

**Installation:**

```bash
sudo apt install libgeos-dev
```

**Example: polygon intersection and area calculation:**

```cpp
#include <geos/geom/GeometryFactory.h>
#include <geos/geom/Polygon.h>
#include <geos/geom/CoordinateSequence.h>
#include <geos/operation/overlay/OverlayOp.h>
#include <iostream>

using namespace geos::geom;

int main() {
    auto factory = GeometryFactory::getDefaultInstance();

    // Create two intersecting polygons
    auto poly1 = factory->createPolygon(
        factory->getCoordinateSequenceFactory()->create(
            {{0, 0}, {10, 0}, {10, 10}, {0, 10}, {0, 0}}
        )
    );
    auto poly2 = factory->createPolygon(
        factory->getCoordinateSequenceFactory()->create(
            {{5, 5}, {15, 5}, {15, 15}, {5, 15}, {5, 5}}
        )
    );

    // Compute intersection
    auto intersection = poly1->intersection(poly2.get());
    std::cout << "Intersection area: " << intersection->getArea() << std::endl;
    std::cout << "Is valid? " << intersection->isValid() << std::endl;
}
```

GEOS is the computational geometry backbone of PostGIS, QGIS, Shapely (Python), and GDAL. If you need spatial operations in any open-source GIS pipeline, GEOS is almost certainly involved.

## S2 Geometry: Spherical Indexing at Google Scale

Google's S2 Geometry library takes a fundamentally different approach — it models the Earth as a sphere and partitions it using the Hilbert space-filling curve. Each S2 cell is a quadrilateral on the sphere identified by a 64-bit integer, with 30 resolution levels from ~85 million km² down to ~0.5 cm².

**Installation:**

```bash
git clone https://github.com/google/s2geometry.git
cd s2geometry && mkdir build && cd build
cmake .. -DBUILD_SHARED_LIBS=ON
make && sudo make install
```

**Example: finding nearby points using S2 cells:**

```cpp
#include "s2/s2latlng.h"
#include "s2/s2cell.h"
#include "s2/s2cell_id.h"
#include <iostream>

int main() {
    // Define two points
    S2LatLng nyc = S2LatLng::FromDegrees(40.7128, -74.0060);
    S2LatLng boston = S2LatLng::FromDegrees(42.3601, -71.0589);

    // Convert to S2 cells at level 10 (~1km accuracy)
    S2CellId nyc_cell = S2CellId(nyc).parent(10);
    S2CellId boston_cell = S2CellId(boston).parent(10);

    // Check distance in cell levels
    int level_diff = S2CellId::CommonAncestorLevel(nyc_cell, boston_cell);
    std::cout << "Common ancestor level: " << level_diff << std::endl;

    // Generate nearby cells for coverage queries
    S2CellId neighbors[4];
    nyc_cell.GetEdgeNeighbors(neighbors);
    std::cout << "Neighbor cell count: 4 (cardinal directions)" << std::endl;
}
```

S2 is used by Google Maps, MongoDB's geospatial queries, and Foursquare's venue search. Its Hilbert curve-based approach provides excellent cache locality and natural hierarchical querying.

## Boost.Geometry: Template-Based Generic Geometry

Boost.Geometry takes the C++ template metaprogramming approach — geometry algorithms are written once and work with any point or polygon type that satisfies the library's concept requirements.

**Installation:**

```bash
sudo apt install libboost-geometry-dev
```

**Example: distance and area with Boost.Geometry:**

```cpp
#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>
#include <boost/geometry/geometries/polygon.hpp>
#include <iostream>

namespace bg = boost::geometry;
using point = bg::model::d2::point_xy<double>;
using polygon = bg::model::polygon<point>;

int main() {
    point p1(0.0, 0.0);
    point p2(3.0, 4.0);
    std::cout << "Distance: " << bg::distance(p1, p2) << std::endl;

    polygon poly;
    bg::read_wkt("POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))", poly);
    std::cout << "Area: " << bg::area(poly) << std::endl;
    std::cout << "Point in polygon: " << bg::within(p2, poly) << std::endl;
}
```

Boost.Geometry's template-based design allows it to work seamlessly with existing codebases' point types. It supports cartesian, geographic, and spherical coordinate systems with automatic coordinate transformation.

## rbush: High-Performance R-tree for JavaScript

rbush brings R-tree spatial indexing to JavaScript with a focus on performance and simplicity. It uses the bulk-loading algorithm (OMT — Overlap Minimizing Top-down) to build balanced trees from static datasets, achieving excellent query performance for read-heavy workloads.

**Installation:**

```bash
npm install rbush
```

**Example: spatial queries in Node.js:**

```javascript
const RBush = require('rbush');

const tree = new RBush();

// Insert items with bounding boxes
tree.insert({ minX: 10, minY: 10, maxX: 20, maxY: 20, id: 'A' });
tree.insert({ minX: 15, minY: 15, maxX: 25, maxY: 25, id: 'B' });
tree.insert({ minX: 30, minY: 30, maxX: 40, maxY: 40, id: 'C' });

// Query: find all items overlapping a region
const results = tree.search({ minX: 0, minY: 0, maxX: 22, maxY: 22 });
console.log('Found:', results.map(r => r.id)); // ['A', 'B']
```

rbush is widely used in web mapping applications (Leaflet plugins, Mapbox GL JS), data visualization, and any JavaScript application that needs fast spatial queries in the browser or Node.js.

## Why Choose Each Spatial Library?

- **Choose libspatialindex** when you need a pure C/C++ R-tree implementation with multiple variants (R*, MVR, TPR) and a clean C API for language bindings. It is the engine behind Python's `rtree` and numerous GIS pipelines.

- **Choose GEOS** when you need full OGC-compliant geometry operations — union, intersection, buffer, validity checking — for GIS applications. It is the computational core of PostGIS and QGIS.

- **Choose S2 Geometry** when your data is global (latitude/longitude) and you need hierarchical spatial indexing that handles the sphere correctly without projection distortions. Ideal for location-based services and global-scale geofencing.

- **Choose Boost.Geometry** when you are in a C++ codebase and want template-based generic geometry that works with your existing types. Its compile-time polymorphism avoids virtual function overhead.

- **Choose rbush** when you need fast client-side spatial queries in JavaScript. Its bulk-loading algorithm and simple API make it perfect for interactive maps and data visualizations.

For related geospatial tooling, see our guides on [GeoIP databases](../2026-04-23-self-hosted-geoip-databases-maxmind-ip2location-dbip-guide-2026/) and [self-hosted routing engines](../2026-04-25-graphhopper-vs-osrm-vs-valhalla-self-hosted-routing-engines-guide-2026/). For binary data handling techniques that complement spatial data processing, check our [binary serialization frameworks guide](../2026-06-19-binary-serialization-frameworks-bincode-borsh-postcard-rkyv/).

## Why Self-Host Spatial Index Libraries?

Spatial indexing may seem like an implementation detail, but the choice of library has far-reaching consequences. Government agencies processing property boundaries, logistics companies optimizing delivery routes, and environmental scientists analyzing satellite imagery all depend on spatial libraries. Using open-source libraries means your spatial algorithms are auditable, reproducible, and not locked into a proprietary vendor's update cycle.

GEOS (LGPL-2.1), libspatialindex (MIT), and rbush (MIT) are all actively maintained with communities that span academia, government, and industry. S2 Geometry (Apache 2.0) has Google's backing and is proven at planetary scale. Boost.Geometry benefits from the rigorous Boost review process and works with any C++17 compiler.

## FAQ

### What is the difference between a spatial index and a geometry engine?

A spatial index (like libspatialindex or rbush) organizes objects for fast spatial queries — "find all restaurants within 5 km." A geometry engine (like GEOS or Boost.Geometry) performs computational geometry operations — "compute the intersection of these two polygons" or "buffer this line by 10 meters." Many applications need both: the spatial index to quickly narrow down candidates, then the geometry engine to perform precise operations.

### Why use S2 cells instead of latitude/longitude directly?

S2 cells solve several problems: (1) they provide a uniform hierarchical partitioning of the sphere without projection distortion, (2) the 64-bit cell ID naturally encodes zoom level and position, making range queries efficient, and (3) Hilbert curve ordering maximizes cache locality — geographically close cells have similar IDs. Direct latitude/longitude comparisons suffer from wraparound at the antimeridian and distortion near the poles.

### Is Boost.Geometry header-only?

Yes, Boost.Geometry is mostly header-only, meaning you include the headers and compile. Some advanced features (like the S2 strategy or certain I/O formats) require linking against compiled Boost libraries, but the core geometry algorithms and spatial indexes work as headers only.

### Can rbush handle millions of points?

Yes, rbush is designed for bulk loading large datasets. Its OMT (Overlap Minimizing Top-down) algorithm builds a near-optimal R-tree in O(n log n) time. For datasets with hundreds of millions of points, consider server-side spatial indexes (GEOS + STRtree, or S2) instead.

### Which library should I use with PostGIS?

PostGIS uses GEOS internally for geometry operations. If you are extending PostGIS with custom functions or building a C/C++ application that feeds data into PostGIS, GEOS is the natural choice. For client-side visualization, combine rbush (fast filtering) with GEOS or Boost.Geometry (precise operations).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Spatial Index and Computational Geometry Libraries: libspatialindex vs GEOS vs S2 Geometry vs Boost.Geometry vs rbush",
  "description": "Comprehensive comparison of five open-source spatial libraries: libspatialindex (R-tree), GEOS (geometry engine), S2 Geometry (spherical), Boost.Geometry (C++ templates), and rbush (JavaScript). Covers spatial indexing, geometry operations, and real-world GIS integration.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
