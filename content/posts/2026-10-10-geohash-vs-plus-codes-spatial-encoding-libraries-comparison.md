---
title: "Geohash vs Plus Codes in 2026: Spatial Encoding Libraries Compared (Rust, Go, Python, Java, JS)"
date: "2026-10-10"
tags: ["geospatial", "encoding", "libraries", "location", "developer-tools"]
cover: "/img/screenshots/geohash-plus-codes-grid.jpg"
draft: false
---

Roughly four billion people live at addresses that either do not exist or cannot be found by a delivery driver. Meanwhile, the software industry solved the opposite problem years ago: turn a latitude and longitude into a short string that sorts spatially, indexes in a database, and can be shared over SMS. Two encoding families do this — **geohash** and **Plus Codes (Open Location Code)** — and they are frequently confused with each other even though they make opposite trade-offs.

Geohash interleaves latitude and longitude bits into a recursive grid, so any prefix of the string is a valid, larger cell. Plus Codes are a deliberately human-readable addressing format defined by an open specification, with a short form that can be completed from a nearby reference location. Picking wrong costs you boundary bugs, precision surprises, or a format your users cannot read aloud.

## TL;DR / Quick Verdict

- **Database prefix search, proximity bucketing, spatial indexing?** → **geohash**. The prefix property is the whole point: one indexed column, one `LIKE 'abc%'` query, and neighbouring cells are one lookup away.
- **Human-facing addresses where street addresses do not exist (delivery, aid, field surveys)?** → **Plus Codes / Open Location Code**. Short, pronounceable, offline-derivable, and specified in one readable document.
- **Rust?** → `georust/geohash` (the `geohash` crate). **Go?** → `mmcloughlin/geohash`. **Python?** → `pygeohash` for geohash, `openlocationcode` for Plus Codes. **Java?** → `kungfoo/geohash-java` or the official OLC Java implementation.

**The trap:** geohash prefix *looks* like true proximity but is not. Two points 20 metres apart can have completely different prefixes if they straddle a cell boundary, and z-order interleaving creates discontinuities where neighbouring prefixes are physically far apart. Always query the eight surrounding cells, never just the one.

## Comparison Table

| Feature | Geohash | Plus Codes (Open Location Code) |
|---|---|---|
| Alphabet | Base32, minus `a`, `i`, `l`, `o` | Base20 (`23456789CFGHJMPQRVWX`) |
| Typical length | 1–12 characters | 2–11 characters (plus `+` separator) |
| Full code example | `u4pruydqqvj` | `8FW4V75V+8Q` |
| Short form | Not applicable | `V75V+8Q` with a reference locality |
| Hierarchical prefix | Yes — truncation = coarser cell | Yes for the first 10 characters |
| Encodes | Point (with cell size) | Point, or an area at 11+ digits |
| Human-readable / speakable | Poorly (no separators) | Yes, by design, with `+` |
| Offline derivation | Yes | Yes |
| Open specification | De facto (wiki + implementations) | Formal spec in the OLC repository |
| `google/open-location-code` | n/a | **4,362 stars**, last push 2026-03-30 |
| Rust | `georust/geohash` — 121 stars, 2026-08-19 | via JVM/other bindings |
| Go | `mmcloughlin/geohash` — **579 stars**, 2024-02-09 | port available |
| Python | `wdm0006/pygeohash` — 179 stars, 2026-10-07 | `openlocationcode` package |
| Java | `kungfoo/geohash-java` — 1,011 stars, 2022-07-03 | official Java implementation |

Star counts and last-push dates were retrieved live from the GitHub API. Note that **the OLC reference repository dwarfs every geohash library (4,362 stars)** because it is a multi-language reference implementation of a specification, not a single-language library.

## Scenario Decision Matrix

| Your situation | Pick | Reason |
|---|---|---|
| Store locations in one Postgres column, index them | **Geohash** | B-tree friendly, fixed-length prefix queries |
| Find "points within 1 km" without PostGIS | **Geohash** + 8 neighbours | Prefix scan plus neighbour expansion approximates a radius |
| Show a human a location to read over the phone | **Plus Codes** | Designed for dictation; includes a `+` separator |
| Rural delivery or disaster response with no street addresses | **Plus Codes** | Officially supported offline addressing format |
| Cluster 10 million events into ~150 m cells | **Geohash** | Truncate to the precision you need and group by prefix |
| River navigation or region naming (coarse areas) | **Plus Codes** (11 digits) | Reports an area, not a single point |
| Cross-language interoperability with JVM services | **Plus Codes + geohash-java** | Both have mature Java implementations |
| Maximal privacy (deliberately vague location) | Either, truncated | Shorter code = larger cell = less precision shared |

## Geohash Libraries

### Rust: `georust/geohash`

121 stars, actively maintained (last push 2026-08-19), part of the broader GeoRust ecosystem alongside `georust/geo` (1,943 stars).

```toml
[dependencies]
geohash = "0.13"
```

```rust
use geohash::{encode, decode, neighbors, Coord};

fn main() -> Result<(), geohash::GeohashError> {
    // Coordinate { x: longitude, y: latitude }
    let c = Coord { x: 112.5584, y: 37.8324 };

    let hash = encode(c, 9)?;          // "ww8p1r4t8"
    let (decoded, _len) = decode(&hash)?;
    println!("{hash} -> ({:.5}, {:.5})", decoded.y, decoded.x);

    // The eight adjacent cells — mandatory for any proximity query.
    for n in neighbors(&hash)? { println!("neighbour: {n}"); }
    Ok(())
}
```

Two details cause most of the confusion in the wild. First, **`Coord` is `{ x: longitude, y: latitude }`**, the opposite order from the `(lat, lng)` convention most APIs use. Second, `neighbors()` exists precisely because a strict prefix query misses points that are physically close but separated by a cell boundary. If you build a "nearby" feature without it, your bug report will be "some restaurants are missing".

### Go: `mmcloughlin/geohash`

579 stars — the most-starred single-language geohash library — with a stable API that has not needed a push since 2024-02-09.

```go
import "github.com/mmcloughlin/geohash"

hash := geohash.Encode(37.8324, 112.5584)          // default precision
hash = geohash.EncodeWithPrecision(37.8324, 112.5584, 9)

lat, lng := geohash.Decode(hash)
box := geohash.BoundingBox(hash)                    // cell extent
neighbours := geohash.Neighbors(hash)               // all 8 (plus self)
```

`BoundingBox` is the function people forget they need: when you decode a geohash you get the cell's centre, and using that centre as "the location" introduces up to half a cell of error. Storing the centre is fine for clustering, misleading for anything that presents a map pin.

### Python: `pygeohash`

179 stars, last push 2026-10-07 — the most recently updated geohash library in this comparison.

```python
import pygeohash as pgh

pgh.encode(37.8324, 112.5584, precision=9)      # 'ww8p1r4t8'
pgh.decode('ww8p1r4t8')                          # (37.8324..., 112.5584...)
pgh.get_adjacent('ww8p1r4t8')                    # dict of 8 neighbours incl. diagonals
```

The library also exposes `get_adjacent` returning all diagonal neighbours, which is what you actually want for a radius query — cardinal-only neighbour sets leave corner gaps that produce visible holes in coverage maps.

### Java: `kungfoo/geohash-java`

1,011 stars despite a last push of 2022-07-03. It is the mature JVM option and its API remains the one most Java tutorials assume:

```java
import ch.hsr.geohash.GeoHash;

GeoHash gh = GeoHash.withCharacterPrecision(37.8324, 112.5584, 12);
String hash = gh.toBase32();

GeoHash[] neighbours = gh.getAdjacent();   // 8 neighbours
gh.getBoundingBox().getCenter();
```

The staleness matters only if you need fixes: with 1,011 stars and a frozen API, treat it as stable infrastructure rather than an actively evolving dependency.

## Plus Codes (Open Location Code)

Plus Codes take a different philosophical position: a location code should be **something a human can say out loud and write on a form**. The specification lives in `google/open-location-code` (4,362 stars), which hosts reference implementations in Java, JavaScript, Python, C, C++, Go, Rust, and more.

```bash
pip install openlocationcode
```

```python
import openlocationcode as olc

code = olc.encode(37.8324, 112.5584, 10)   # '8FW4V75V+8Q'
area = olc.decode(code)
print(area.latitudeCenter, area.longitudeCenter)

# Short form — requires a reference location to be recoverable.
short = olc.shorten(code, 37.83, 112.55)             # 'V75V+8Q'
full  = olc.recoverNearest(short, 37.83, 112.55)     # '8FW4V75V+8Q'
```

The `+` separator is not decoration: it marks the position where the code switches from area resolution to point resolution, and it gives a human a natural place to pause when reading a code aloud. That single design choice is why Plus Codes work on radio and in field notebooks while a raw geohash does not.

![Open Location Code area grid showing how codes tile a city](/img/screenshots/plus-codes-area-grid.jpg "Open Location Code area grid from the official OLC documentation")

Note the short-form rule: **a short Plus Code is meaningless without its reference location.** Store the recovery point alongside a short code, or store the full code. Attempting to recover a short code against the wrong city produces a confidently wrong location — a failure mode with real operational consequences.

## Precision Reference

| Geohash length | Approx. cell size | Plus Code digits | Approx. cell size |
|---|---|---|---|
| 1 | 5,000 km × 5,000 km | 2 | ~1,000 km |
| 4 | 39 km × 19.5 km | 4 | ~25 km |
| 5 | 4.9 km × 4.9 km | 6 | ~1.2 km |
| 6 | 1.2 km × 0.61 km | 8 | ~275 m |
| 7 | 153 m × 153 m | 10 | ~14 m |
| 8 | 38 m × 19 m | 11 | ~3 m (area code) |
| 9 | 4.8 m × 4.8 m | — | — |
| 12 | 3.7 cm × 1.9 cm | — | — |

Choose the shortest encoding that satisfies your use case. Every extra character is a character you must store, index, transmit, and explain — and, from a privacy standpoint, a character that narrows a person's location. **Precision you do not need is a liability, not a feature.**

## Pitfalls That Break Proximity Features

**The prefix illusion.** Geohash prefixes are hierarchical but not locally continuous. Two cells can share a long prefix and be physically far apart because of z-order interleaving. Never treat "same prefix" as a precise distance; treat it as a bucket.

**Cell boundaries split nearby points.** A café 5 metres from a table can fall into a different cell from the table. The fix is always the same: expand the query to the eight adjacent cells, and if you are near a corner, consider the two-step ring.

**Latitude/longitude ordering is inconsistent.** Rust libraries commonly use `(x, y)` = `(lon, lat)`; most other APIs take `(lat, lon)`. Passing them in the wrong order puts your points in the ocean and produces no error at all.

**Decoding returns a centre, not your point.** Round-tripping a coordinate through an encode/decode cycle quantises it to the cell centre. Keep the original coordinates for display and use the hash only for indexing and grouping.

**Plus Code short forms need a reference.** Without one, recovery is guesswork. Persist the full code, or persist the reference locality explicitly.

**Poles and the anti-meridian are special.** Wrapping behaviour near ±180° longitude and ±90° latitude differs between implementations. Test them explicitly if your data is global.

**A bounding-box radius is not a real radius.** Geohash neighbour expansion produces a rectangular approximation. For strict distance semantics, filter the candidates with an actual great-circle distance after the prefix lookup — this is the pattern used by dedicated geofencing engines, and it is where a spatial database starts to earn its place.

## Choosing Between Encoding and a Spatial Database

If your query pattern is "give me rows whose bucket matches", encoding is enough and costs nothing at runtime. The moment you need true radius queries, polygon containment, or index-backed ORDER BY distance, you have outgrown prefix matching. That boundary is exactly where our [spatial index and computational geometry library comparison](../2026-06-20-spatial-index-computational-geometry-libraries-libspatialindex-geos-s2-boost-rbush/) and the [Python geospatial stack overview](../2026-07-01-python-geospatial-libraries-geopandas-shapely-fiona-rasterio-folium/) pick up.

For teams that want both — encoded buckets *and* real geospatial queries — a self-hosted spatial engine is the standard answer; see our [geospatial database guide covering Tile38, PostGIS and Redis](../2026-05-20-self-hosted-geospatial-database-tile38-postgis-redis-guide/). If your real problem is triggering actions when a device enters an area, the [geofencing and spatial query engine comparison](../2026-06-15-self-hosted-geofencing-spatial-query-engines-tile38-postgis-redis/) covers the event-driven side.

## FAQ

**Is geohash the same thing as a Plus Code?**
No. Both encode a latitude and longitude into a short string, but geohash is a spatially sortable grid built for indexing, while Plus Codes are an addressing format designed for humans to read, dictate, and write down. Geohash prefixes support database range scans; Plus Codes support "what is your address?" in places that have none.

**Why is my geohash proximity query missing nearby results?**
Because points close to a cell boundary land in a different cell. Query the eight neighbouring cells as well as the centre cell, then filter candidates by real distance. Cardinal-only neighbours still leave gaps at the diagonals.

**How many characters of a geohash should I store?**
Match the precision to your use case: 6 characters is roughly a neighbourhood (about 1.2 km), 7 is a block, 9 is a few metres. Storing 12 characters when you only cluster at block level wastes space and indexing time.

**Can Plus Codes work completely offline?**
Yes. Encoding and decoding are pure arithmetic over the specification's alphabet grid with no network calls and no lookup tables beyond the character set. That is a core reason they are used in field work and disaster response.

**What does the `+` in a Plus Code mean?**
It separates the coarse area portion of the code from the refined portion, and it marks the point where a code transitions from describing an area to describing a point. It is also the natural place to pause when reading a code aloud.

**Should I use geohash or a spatial database like PostGIS?**
Use geohash when you need cheap, index-friendly bucketing and can tolerate approximate proximity. Use a spatial database when you need exact radius queries, polygon containment, or distance-ordered results. Many systems use both — geohash for fast candidate selection, the database for the authoritative answer.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Geohash vs Plus Codes in 2026: Spatial Encoding Libraries Compared (Rust, Go, Python, Java, JS)",
  "description": "A 2026 comparison of geohash and Open Location Code (Plus Codes) libraries across Rust, Go, Python and Java, with precision tables, code samples and proximity pitfalls.",
  "datePublished": "2026-10-10",
  "dateModified": "2026-10-10",
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
