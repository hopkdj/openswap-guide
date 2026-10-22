---
title: "ecCodes vs cfgrib vs MetPy in 2026: The Right Way to Decode GRIB2 Weather Data in Python"
date: "2026-10-23"
tags: ["python", "weather-data", "grib", "meteorology", "data-engineering", "eccodes"]
draft: false
cover: "/img/screenshots/metpy-logo.jpg"
description: "How to decode GRIB2 forecast data without fighting your toolchain: ecCodes vs cfgrib vs MetPy in 2026, with verified install steps, CLI recipes, xarray pipelines and the pitfalls that cost days."
---

A single ERA5 pressure-level file is 400 MB. A GFS 0.25° forecast cycle is several gigabytes spread over dozens of files. And when you open the first one, Python hands you back a wall of undocumented integer codes, a longitude axis running from 0 to 360, and a `KeyError` for a parameter you were sure existed.

GRIB2 is the format every national weather service actually uses, and the Python ecosystem around it is three layers deep. **ecCodes** is the C engine that encodes and decodes the format. **cfgrib** is the xarray engine that turns GRIB into labelled N-dimensional arrays. **MetPy** is the meteorology layer that converts those arrays into dewpoints, CAPE, and skew-T plots. Confusing them is the most common cause of wasted days in weather-data work, because each one answers a different question.

## TL;DR — the 30-second verdict

- **You need to read, filter, or convert GRIB files**: install **ecCodes** (274★, Apache-2.0, pushed 2026-10-22) and use its CLI tools (`grib_ls`, `grib_copy`, `grib_get`) for inspection and subsetting. This is the reference implementation from ECMWF — everything else wraps it.
- **You need arrays for analysis or plotting**: use **cfgrib** (465★, Apache-2.0, pushed 2026-07-08) as an xarray engine. One line turns a GRIB file into a `Dataset` with coordinates, lazily loaded and dask-compatible.
- **You need meteorological calculations**: use **MetPy** (1,451★, BSD-3-Clause, pushed 2026-10-19). Unit-aware thermodynamics, indices and plotting — but it does **not** decode GRIB by itself.
- **The practical answer**: ecCodes + cfgrib are a pair, not alternatives. Add MetPy only when you need physics. Anyone who tells you to "just use MetPy to read GRIB" has not tried it.

## Comparison table (GitHub data, 2026-10-23)

| Dimension | ecCodes | cfgrib | MetPy |
|---|---|---|---|
| GitHub stars | 274 | 465 | 1,451 |
| Last commit | 2026-10-22 | 2026-07-08 | 2026-10-19 |
| License | Apache-2.0 | Apache-2.0 | BSD-3-Clause |
| Maintainer | ECMWF | ECMWF (community) | NSF Unidata |
| Language | C, with Fortran 90 and Python interfaces | Python | Python |
| Role | GRIB/BUFR encode + decode engine | xarray backend (`engine="cfgrib"`) | Meteorology calculations + plots |
| Install | CMake build from source, or conda-forge | `pip install cfgrib` (needs ecCodes present) | `pip install metpy` |
| Input formats | GRIB 1/2, BUFR | GRIB 1/2 via ecCodes | Arrays from xarray/netCDF, not GRIB |
| Output | Raw keys/values, CLI text, re-encoded GRIB | `xarray.Dataset` | Quantities, indices, figures |
| Handles huge files | Yes (streaming CLI tools) | Yes (lazy + dask chunking) | Only what fits the arrays you pass |
| Learning curve | Steep (GRIB key names) | Low | Medium (units discipline) |
| Best for | Pipelines, subsetting, format conversion | Analysis-ready arrays | Forecast soundings, indices, verification |

## Decision matrix: what are you actually trying to do?

| Task | Tool | Why |
|---|---|---|
| "What is inside this .grib2 file?" | ecCodes `grib_ls` | Prints every message with parameter, level and timestamp |
| "Extract only total precipitation" | ecCodes `grib_copy -w` | Server-side filter, no full decode into memory |
| "Open a forecast file in xarray" | cfgrib | `xr.open_dataset(..., engine="cfgrib")` |
| "Load 40 GB of GRIB with dask" | cfgrib | Lazy loading plus chunking; build an index once |
| "Compute dewpoint from temperature and RH" | MetPy | `dewpoint_from_relative_humidity` with unit checking |
| "Calculate CAPE or lifted condensation level" | MetPy | `lcl`, `precipitable_water`, `bulk_shear` |
| "Plot a skew-T log-P diagram" | MetPy | `metpy.plots.SkewT` |
| "Convert GRIB to NetCDF or Zarr" | ecCodes + cfgrib | Decode, then `to_zarr()` for columnar/array storage |
| "Read a GRIB file on a machine with no build tools" | conda-forge `eccodes` | Prebuilt binaries, then `pip install cfgrib` |

![MetPy official project logo](/img/screenshots/metpy-logo.jpg "MetPy — tools for reading, visualising and calculating with weather data")

## ecCodes — install it first, because everything depends on it

ecCodes is ECMWF's library for GRIB and BUFR. It is a C library with Fortran and Python interfaces, and it is the only implementation in this list that both **encodes** and **decodes**. The build is CMake-based, straight from the official README:

```bash
tar -xzf eccodes-x.y.z-Source.tar.gz
mkdir build && cd build
cmake ../eccodes-x.y.z-Source -DCMAKE_INSTALL_PREFIX=/opt/eccodes
make
ctest
make install
```

The Python bindings live in a separate PyPI package and need to find that install:

```bash
pip3 install eccodes
export ECCODES_DIR=/opt/eccodes
```

On Ubuntu and in containers, `apt-get install libeccodes-tools libeccodes-dev` or `conda install -c conda-forge eccodes` is faster than compiling, and it is what most production images do. The CLI tools are the reason to care even if you never write C:

```bash
# What is in this file? One line per GRIB message
grib_ls -p shortName,level,dataDate,dataTime,step forecast.grib2

# Keep only total precipitation, discard the other 200 fields
grib_copy -w shortName=tp forecast.grib2 precip.grib2

# Dump every key of the first message (the GRIB dictionary)
grib_dump -O forecast.grib2 | head -60
```

That third command is the single most useful debugging tool in this entire ecosystem. GRIB is not self-describing in the way NetCDF is: parameter names come from tables, and the "name" you see is a lookup, not a string stored in the file. `grib_dump` shows you the actual keys so you can stop guessing what `cfgrib` renamed to `t2m`.

Low-level access from Python, when you want streaming control rather than an array:

```python
import eccodes

with open("forecast.grib2", "rb") as f:
    while True:
        gid = eccodes.codes_grib_new_from_file(f)
        if gid is None:
            break
        try:
            print(eccodes.codes_get(gid, "shortName"),
                  eccodes.codes_get(gid, "level"),
                  eccodes.codes_get(gid, "dataDate"))
        finally:
            eccodes.codes_release(gid)
```

This loop never materialises a full field. On a 6 GB file it is the difference between 40 MB of RSS and an out-of-memory kill.

## cfgrib — GRIB as an xarray Dataset

cfgrib is a thin, well-designed adapter: it uses ecCodes to decode messages, then maps them onto the NetCDF Common Data Model following CF conventions. The result is a normal `xarray.Dataset`, which means every downstream tool — dask, matplotlib, zarr, parquet exporters — just works.

```python
import xarray as xr

ds = xr.open_dataset("era5-levels-members.grib", engine="cfgrib")
print(ds)
```

Real output shape from the project's README:

```
Dimensions:        (number: 10, time: 4, isobaricInhPa: 2, latitude: 61, longitude: 120)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) float64 850.0 500.0
  * latitude       (latitude) float64 90.0 87.0 ... -90.0
  * longitude      (longitude) float64 0.0 3.0 ... 357.0
```

Three capabilities make cfgrib worth the extra dependency:

1. **Heterogeneous files.** `cfgrib.open_datasets(path)` returns a *list* of datasets, one per distinct GRIB structure. Forecast files routinely mix surface fields, pressure-level fields and ensemble members; the single-dataset call raises or silently drops fields, while `open_datasets` keeps everything.
2. **Custom key access.** `backend_kwargs={"read_keys": ["experimentVersionNumber"]}` exposes GRIB keys that are not part of the standard mapping, attached to the variable's `.attrs`:

```python
ds = xr.open_dataset("era5-levels-members.grib", engine="cfgrib",
                     backend_kwargs={"read_keys": ["experimentVersionNumber"]})
print(ds.t.attrs["GRIB_experimentVersionNumber"])   # '0001'
```

3. **Index files.** cfgrib writes a `.idx` sidecar on first open so the next open skips a full-file scan. For a directory of 500 forecast files this is the difference between minutes and milliseconds — but the index goes stale if the file is rewritten. Disable it with `backend_kwargs={"indexpath": ""}` when files are generated in place.

The hard requirement people trip over: **cfgrib is pure Python and does not ship ecCodes.** `pip install cfgrib` succeeds, then the first `open_dataset` fails with `ecCodes library not found`. Install the binary library first (`conda install -c conda-forge eccodes` is the shortest path), or point `ECCODES_DIR` at an existing build.

## MetPy — where weather data becomes meteorology

MetPy does not read GRIB and never claimed to. It is a unit-aware calculation and plotting library: you feed it arrays from xarray, and it gives you thermodynamics, indices and soundings. It requires Python 3.11 or newer, follows semantic versioning (any `1.x` release stays backward compatible), and builds on NumPy, SciPy, Matplotlib, pandas and Pint.

```python
import metpy.calc as mpcalc
from metpy.units import units

temperature = 25 * units.degC
relative_humidity = 60 * units.percent

td = mpcalc.dewpoint_from_relative_humidity(temperature, relative_humidity)
print(td.to("degC"))
```

The units are not decoration. Passing bare floats raises, and that is the feature: a pressure array in Pa silently interpreted as hPa produces a physically plausible but wrong sounding, which is far worse than an exception.

The functions that justify the dependency are the ones you should never hand-roll:

```python
import metpy.calc as mpcalc
from metpy.units import units
import numpy as np

pressure = np.array([1000, 925, 850, 700, 500]) * units.hPa
temperature = np.array([20, 15, 8, -2, -20]) * units.degC
dewpoint = np.array([12, 8, 2, -8, -30]) * units.degC
u = np.array([5, 8, 12, 20, 30]) * units("m/s")
v = np.array([2, 3, 5, 8, 12]) * units("m/s")

lcl_pressure, lcl_temperature = mpcalc.lcl(pressure[0], temperature[0], dewpoint[0])
print(f"LCL: {lcl_pressure:.0f}, {lcl_temperature:.1f}")

pw = mpcalc.precipitable_water(pressure, dewpoint)
shear = mpcalc.bulk_shear(pressure, u, v, height=None)
```

Verified signatures from the source tree: `lcl(pressure, temperature, dewpoint)`, `dewpoint_from_relative_humidity(temperature, relative_humidity)`, `precipitable_water(pressure, dewpoint, *, bottom=None, top=None)`, `bulk_shear(pressure, u, v, height, bottom, depth)`. Notice that `bulk_shear` wants a height coordinate you usually have to derive first — that is the pattern with MetPy: it makes the physics correct and leaves the data plumbing to you.

## The pipeline that actually works

Combining all three is not redundant; each layer does one job:

```bash
# 1. Inspect and subset with ecCodes (no Python process, no memory)
grib_copy -w shortName=t,dewpoint,gh forecast.grib2 subset.grib2
```

```python
# 2. Load analysis-ready arrays with cfgrib
import xarray as xr
ds = xr.open_dataset("subset.grib2", engine="cfgrib")

# 3. Compute meteorology with MetPy
import metpy.calc as mpcalc
from metpy.units import units

t = ds["t"].metpy.quantify()          # attaches pint units from GRIB attributes
td = ds["dewpoint"].metpy.quantify()
rh = mpcalc.relative_humidity_from_dewpoint(t, td)
print(float(rh.isel(isobaricInhPa=0).mean()))

# 4. Persist for analytics, not for decoding
ds.to_zarr("forecast.zarr", mode="w", consolidated=True)
```

Step 4 matters more than it looks. Decoding GRIB repeatedly is a tax on every analysis run; converting once to Zarr or Parquet and querying that store is what turns a nightly script into a data platform. Our [columnar format comparison](../2026-06-21-self-hosted-columnar-data-formats-parquet-arrow-orc/) covers the Parquet/Arrow side of that decision, and if you are serving time-indexed observations at query time, the [time-series database comparison](../2026-05-18-m3db-vs-questdb-vs-timescaledb-self-hosted-time-series-databases/) is the relevant next read. For gridded geospatial storage with spatial indexes, see the [spatiotemporal database roundup](../2026-06-13-self-hosted-spatiotemporal-databases-mobilitydb-geomesa-h2gis/).

## Pitfalls that cost days, not hours

1. **`pip install cfgrib` without ecCodes.** The Python package is a wrapper. Install the binary library first, then set `ECCODES_DIR` if it is not on the default path.
2. **Using `open_dataset` on a mixed file.** Ensemble members, surface fields and pressure levels in one file will collide. Use `cfgrib.open_datasets()` and merge deliberately.
3. **Assuming parameter names.** GRIB stores table indices, not names. `t2m`, `2t`, `t` and `air_temperature` may all be the same physical thing in different files. Always confirm with `grib_ls -p shortName,name`.
4. **Longitude conventions.** GRIB usually runs 0→360 while your basemap expects -180→180. A global plot shifted by half a map is this bug, every time.
5. **Calling `.values` on a lazy dataset.** cfgrib returns lazy arrays backed by ecCodes. Materialising a 40 GB field is an OOM kill, not a slow operation. Chunk first, then reduce.
6. **Stale `.idx` sidecars.** Rewriting a GRIB file in place leaves an index describing the old contents. Delete the `.idx`, or pass `indexpath=""`.
7. **Mismatched definition tables.** Local GRIB variants (national centres, experimental products) may need extra definition files via `ECCODES_DEFINITION_PATH`. A parameter decoding as `unknown` is usually this.
8. **Ignoring units in MetPy.** Wrapping arrays with `units` on entry, and calling `.to()` on output, prevents the class of bug where the number looks fine and is wrong by a factor of 100.
9. **Treating GRIB as an archive format.** It is a transport format. Convert to Zarr/Parquet for storage, and keep the raw GRIB only for reproducibility of the original forecast.

## FAQ

**Do I need MetPy to read GRIB files?**
No. MetPy does not decode GRIB at all. Use ecCodes directly or cfgrib as an xarray engine, then pass the resulting arrays to MetPy for calculations.

**Is cfgrib a replacement for ecCodes?**
No — it is a client of ecCodes. cfgrib calls into the ecCodes library for every message it reads, which is why the binary library must be installed before `engine="cfgrib"` works.

**Can I decode GRIB without installing a C library?**
Not in practice. Every mature Python option wraps ecCodes. The pragmatic path is a prebuilt package (`conda install -c conda-forge eccodes` or the distribution's `libeccodes-tools`), not reimplementation.

**What is the fastest way to inspect a large GRIB file?**
`grib_ls -p shortName,level,dataDate,step file.grib2` prints one line per message without decoding data. `grib_dump -O` shows every key when you need the full picture. Both stream the file and use negligible memory.

**How do I handle files larger than RAM?**
Load with cfgrib and chunk: `xr.open_dataset(path, engine="cfgrib", chunks={"time": 24})`. Keep arrays lazy through dask, reduce before plotting, and write results to Zarr rather than re-decoding GRIB each run.

**Does MetPy work with Python 3.10?**
No. MetPy currently supports Python 3.11 and newer. It follows semantic versioning, so a `1.x` release will not break correct code across minor upgrades.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ecCodes vs cfgrib vs MetPy in 2026: The Right Way to Decode GRIB2 Weather Data in Python",
  "description": "Verified 2026 guide to GRIB2 decoding in Python: ecCodes CLI and API, cfgrib xarray pipelines, MetPy meteorology calculations, install steps and the pitfalls that break weather-data workflows.",
  "datePublished": "2026-10-23",
  "dateModified": "2026-10-23",
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
