---
title: "HDF5 vs NetCDF4 vs Zarr vs TileDB in 2026: Which Array Storage Engine Should You Actually Use?"
date: "2026-10-11"
tags: ["data-engineering", "scientific-computing", "storage", "hdf5", "libraries"]
draft: false
cover: "/img/screenshots/hdfview-gui.jpg"
---

The first time you try to read a slice out of a 40 GB climate file, you learn the lesson that every data engineer eventually learns the hard way: **the format you picked in hour one decides how painful year two is.** A monolithic `.nc` file is a joy on one workstation and a liability in a stack of containers reading from object storage. A pile of chunked arrays is the opposite. Neither is wrong — but they are not interchangeable, and migrating later means rewriting every reader you own.

Four formats dominate scientific and analytical array storage in 2026: **HDF5**, **NetCDF4**, **Zarr**, and **TileDB**. They look similar in a feature matrix and behave completely differently the moment concurrency, object storage, or partial reads enter the picture.

## The 30-Second Verdict

- **You need one portable container file for hierarchical, mixed-type data:** use **HDF5**. It has 30 years of tooling behind it and everything else speaks it.
- **Your data is gridded, labelled with coordinates, and lives in the climate/geoscience ecosystem:** use **NetCDF4**. You get `ncdump`, `xarray`, CF conventions, and an ecosystem that assumes this format.
- **You read slices from object storage with many parallel workers:** use **Zarr**. Chunk-per-object layout is the only one of the four designed for HTTP range reads.
- **You need sparse arrays, fast multi-dimensional range queries, or predicate pushdown on array coordinates:** use **TileDB**.

One sentence to remember: *HDF5 is the universal container, NetCDF4 is the geoscience contract, Zarr is the cloud-native layout, TileDB is the query engine.*

## Quick Comparison: Four Array Storage Engines in 2026

Repository statistics below were pulled live from GitHub at publish time.

| Project | Language | Stars | Last release activity | Model | Best backend | License |
|---|---|---|---|---|---|---|
| **HDF5** | C | 994 | Oct 2026 | Hierarchical groups + datasets | Local filesystem, parallel FS | BSD-style |
| **h5py** (HDF5 for Python) | Python | 2,256 | Oct 2026 | Pythonic wrapper over HDF5 | Local filesystem | BSD-3 |
| **netcdf-c** | C | 607 | Oct 2026 | Classic + netCDF-4 (HDF5-based) | Local filesystem, OPeNDAP | BSD-3 |
| **zarr-python** | Python | 2,068 | Oct 2026 | Chunked N-d arrays + JSON metadata | S3 / GCS / local / HTTP | MIT |
| **TileDB** | C++ | 2,086 | Sep 2026 | Dense + sparse array "universal storage" | S3, GCS, Azure, local | MIT |

The most important structural fact in that table: **netCDF4 is HDF5 underneath.** A netCDF-4 file is a valid HDF5 file with a specific convention layered on top. That is why geoscience tooling can read both, and why choosing between them is really a question about *ecosystem contracts*, not binary layout.

The second: **Zarr and TileDB are chunk-per-object designs.** HDF5 and netCDF4 store chunks *inside* a single file, which means opening the container is a prerequisite to reading any byte of it. Zarr and TileDB invert that. A thousand workers can each fetch one chunk without coordinating through one file handle — that property is the whole reason cloud analytics moved in this direction.

## Decision Matrix: Pick by Workload

| Your workload | Pick | Why |
|---|---|---|
| Lab instrument output, one file per experiment | **HDF5** | Self-describing, hierarchical, readable by MATLAB, Julia, R, Python, C++, Java |
| Climate/weather model output with CF conventions | **NetCDF4** | `xarray` + `ncdump` + IRI/LDEO tooling assume it; OPeNDAP servers serve it natively |
| Petabyte-scale arrays on S3, read by 1,000 pods | **Zarr** | HTTP range reads per chunk, no file locking, no central metadata bottleneck |
| Sparse event arrays with coordinate-range queries | **TileDB** | Sparse arrays + filters; range queries instead of full-chunk materialisation |
| Genomics / single-cell matrices | **Zarr or HDF5** | Both are established (AnnData is HDF5-backed; many pipelines now write Zarr) |
| You must keep existing `.nc` files but want cloud reads | **Kerchunk + Zarr** | Build a virtual Zarr view over immutable netCDF without rewriting a byte |

## HDF5 — The Universal Container

HDF5 is the lingua franca of scientific file formats. Its model is a filesystem in a file: groups act as directories, datasets as arrays with attached attributes, and the whole tree is self-describing. If your problem is "I have heterogeneous data and I need one portable container that outlives my framework of choice", this is still the answer.

```bash
# Debian / Ubuntu: library, headers and the CLI tools
sudo apt install libhdf5-dev hdf5-tools

# Python bindings (the interface most people actually use)
python3 -m pip install h5py

# Inspect structure without writing code
h5ls -r experiment.h5
h5dump -H -d /measurements/field experiment.h5
```

Writing a chunked, compressed dataset with h5py — note the chunk shape, which is the single most consequential parameter in the file:

```python
import h5py
import numpy as np

with h5py.File("experiment.h5", "w") as f:
    # Chunk shape should match how you later *read*, not how you write
    ds = f.create_dataset(
        "measurements/field",
        shape=(2048, 2048, 256),
        chunks=(128, 128, 32),
        compression="gzip",
        compression_opts=4,
        dtype="float32",
    )
    ds.attrs["units"] = "K"
    ds[:, :, 0] = np.zeros((2048, 2048), dtype="float32")

    f.create_group("metadata").attrs["instrument"] = "synchrotron-beamline-7"
```

Two properties define real-world HDF5 behaviour. First, **file locking**: HDF5 takes an advisory lock, which breaks on many NFS and container-overlay setups. The official escape hatch is an environment variable, and you will need it eventually:

```bash
export HDF5_USE_FILE_LOCKING=FALSE
```

Second, **single-writer semantics**: classic HDF5 writing from multiple processes risks corruption. Parallel writes require the parallel-HDF5 build (MPI) or an external merge step. Teams that skip this detail discover it when their cluster job produces an unreadable file.

![HDFView — the reference GUI for inspecting HDF5 files](/img/screenshots/hdfview-file-window.jpg "HDFView file window showing the HDF5 group hierarchy")

HDFView, maintained in the same organisation, remains the reference GUI and is genuinely useful for debugging an unfamiliar file structure without writing a line of code.

## NetCDF4 — The Geoscience Contract

The netCDF ecosystem's value is not the binary layout; it is the **conventions**. CF (Climate and Forecast) metadata tells any compliant reader what the dimensions mean, what the units are, and how coordinates map onto physical space. That is why three decades of climate tooling can interoperate at all.

```bash
sudo apt install libnetcdf-dev netcdf-bin

# Human-readable header, no data read
ncdump -h model_output.nc

# Copy/convert: classic netCDF -> netCDF-4 (HDF5-backed), with compression
nccopy -k netCDF-4 -d 4 model_output.nc model_output_compressed.nc

# Python: the xarray path, which is what most analysts use
python3 -m pip install xarray netCDF4 dask
```

```python
import xarray as xr

ds = xr.open_dataset("model_output.nc", chunks={"time": 24})
subset = ds["temperature"].sel(time="2026-06-01", method="nearest")
regional = ds["temperature"].sel(lat=slice(35, 45), lon=slice(-10, 5))
print(subset.mean().values)
```

The classic format deserves an explicit warning, because it still exists in the wild and still bites: **the original netCDF classic format stores offsets in 32 bits and therefore caps out around 2 GiB**, with a 64-bit-offset variant (CDF-5) existing precisely to work around it. If a legacy pipeline encodes CDF-1, no amount of disk will let it grow past the limit. `nccopy -k netCDF-4` is the standard migration.

## Zarr — Cloud-Native by Construction

Zarr stores each chunk as an independent object and describes the array in small JSON metadata files. There is no central file to open, no lock to take, and no monolithic header that every reader must fetch before reading a byte. On S3, that means a worker fetching a 2 MB chunk issues one GET for the chunk plus a cached metadata read — nothing else.

```bash
python3 -m pip install "zarr>=3"
```

```python
import numpy as np
import zarr

# Local store, or "s3://bucket/path" with fsspec for object storage
root = zarr.open_group("data.zarr", mode="w")
arr = root.create_array(
    "temperature",
    shape=(10_000, 1000, 1000),
    chunks=(100, 100, 100),
    dtype="float32",
    compressors=[zarr.codecs.BloscCodec(cname="zstd", clevel=5)],
)

# Write one region; readers only fetch the chunks they touch
arr[0:100, 0:100, 0:100] = np.random.rand(100, 100, 100).astype("float32")
print(root["temperature"].chunks)
```

The concurrency model is the selling point: independent chunk writes mean 500 workers can write disjoint regions without coordination. It is also the failure mode. Zarr gives you **no transactions** — a partially written dataset is a real, discoverable state, and on eventually-consistent storage you may read stale metadata. Production deployments adopt a write-new-then-swap pattern, or write through a single coordinator, rather than pretending the store is a filesystem.

The migration trick worth knowing: **Kerchunk** builds a virtual Zarr view over existing, immutable netCDF/HDF5 files by indexing their byte ranges. You get cloud-friendly parallel reads without regenerating a petabyte of archive data.

## TileDB — Array Storage With a Query Engine

TileDB is the odd one out: an embedded C++ storage engine that treats arrays as the primary abstraction and adds what the file formats lack — a filter pipeline, sparse arrays with coordinate-based indexing, and backends that include S3, GCS, and Azure as first-class citizens rather than mounted-filesystem workarounds.

```bash
python3 -m pip install tiledb
```

```python
import numpy as np
import tiledb

uri = "s3://analytics-bucket/temperature"

dom = tiledb.Domain(
    tiledb.Dim(name="x", domain=(0, 999), tile=100, dtype="int32"),
    tiledb.Dim(name="y", domain=(0, 999), tile=100, dtype="int32"),
)
schema = tiledb.ArraySchema(
    domain=dom,
    sparse=False,
    attrs=[tiledb.Attr(name="value", dtype="float32")],
)

tiledb.Array.create(uri, schema, overwrite=True)

with tiledb.open(uri, "w") as A:
    A[0:100, 0:100] = np.random.rand(100, 100).astype("float32")

with tiledb.open(uri, "r") as A:
    print(A[10:20, 10:20]["value"])
```

Where TileDB earns its place is the query shape it enables: sparse arrays with coordinate ranges, attribute filters applied during the read, and consolidation as an explicit operation instead of a background mystery. The trade-off is ecosystem gravity — fewer libraries read TileDB natively than read HDF5, so you are choosing a storage engine, not just a file format.

## Why Self-Host Your Array Storage At All?

The honest answer in 2026 is that the *format* is rarely the expensive part — the *service layer around it* is. Managed scientific data platforms bill per query and per egress gigabyte, and array workloads are exactly the workload where egress fees compound: a single training or analysis pass over a 20 TB dataset can move more bytes than the storage costs.

Self-hosting the read path changes the economics in a way that is easy to underestimate. HDF5 and netCDF4 files on your own server cost one fixed disk and serve unlimited internal readers; Zarr and TileDB on self-hosted S3-compatible object storage (MinIO, Ceph, Garage) give you the cloud-native access pattern without per-request pricing. If your data is served over HTTP, the classic options still work and still matter: our comparison of [self-hosted scientific data servers](../2026-06-10-self-hosted-scientific-data-servers-thredds-erddap-hyrax-guide/) covers THREDDS, ERDDAP, and Hyrax for exactly the case where consumers want URLs, not Python. And when the array is genuinely tabular, the [columnar data formats comparison](../2026-06-21-self-hosted-columnar-data-formats-parquet-arrow-orc/) is the right companion — Parquet beats all four formats here for row-oriented analytics.

A practical architecture that avoids the worst of both worlds: **write immutable archives as HDF5/netCDF4** (portable, fully self-describing, no service dependency), then **publish a derived Zarr or TileDB view** for the read-heavy analytics tier. Storage is cheap; re-deriving a published view is a job, not a rewrite.

## Common Pitfalls and Migration Notes

**1. HDF5 file locking breaks under NFS and containers.** Symptom: `unable to lock file` or a hang on open. Setting `HDF5_USE_FILE_LOCKING=FALSE` resolves it, at the cost of losing protection against concurrent writers. Do not disable locking on a shared writable file.

**2. netCDF classic silently caps at ~2 GiB.** If a legacy pipeline writes CDF-1, appending will fail or truncate depending on the tool. Convert with `nccopy -k netCDF-4` before growth, not after.

**3. Chunk shape dominates performance in every one of these formats.** Reading a time series out of a file chunked for spatial locality means reading gigabytes to produce kilobytes. Match chunking to the dominant access pattern, and re-chunk as a batch job when the pattern changes.

**4. Zarr is not transactional.** A killed writer leaves a dataset that *looks* readable and is not. Validate chunk manifests, or write to a new prefix and swap atomically.

**5. Dictionary-encoded and compressed chunks defeat memory-mapping.** Compression is a CPU/IO trade you must measure; on fast NVMe with CPU-bound pipelines, `gzip` level 9 is often a net loss versus `zstd` level 3.

**6. `xarray` hides the cost of `chunks={"time": 24}`.** Dask makes a 40 GB read look lazy and free until the first `.values`. Always check the task graph before scaling workers.

**7. Never mix writers.** HDF5 with a non-parallel build plus two writing processes equals corruption. Zarr with two writers on the same chunk equals last-writer-wins silently. Choose one writer per region, explicitly.

## FAQ

**Is NetCDF4 the same as HDF5?**
Structurally yes, contractually no. A netCDF-4 file is a valid HDF5 file, and netCDF-4 uses HDF5 as its storage layer. The difference is the convention: netCDF adds a defined dimension/coordinate model (CF) that geoscience tooling relies on. You can read a netCDF-4 file with any HDF5 library, but you will not get the semantic guarantees unless you use a netCDF-aware reader.

**Should I use Zarr or HDF5 for machine learning training data?**
Use Zarr (or TileDB) when many workers read random slices in parallel from object storage — that is the access pattern Zarr was designed for and HDF5 was not. Use HDF5 when you need one portable, self-describing file that non-Python tools can also open, or when the dataset comfortably fits on a shared filesystem.

**Why is my HDF5 file failing to open on a network share?**
Almost always file locking. HDF5 takes an advisory lock by default, and many NFS or container overlay filesystems do not support it correctly. Set `HDF5_USE_FILE_LOCKING=FALSE` in the environment, or move the file to a filesystem that implements POSIX locks properly.

**Can I keep my existing netCDF archives and still get cloud-friendly reads?**
Yes — that is exactly what Kerchunk solves. It generates an index of byte ranges over the existing files, which Zarr-aware readers then consume as a virtual dataset. No re-encoding, no data duplication, and the original archive stays immutable.

**Is TileDB worth it over plain Parquet for analytical data?**
Only if you are working with dense or sparse *arrays* that are queried by coordinate ranges. For tabular analytics with column predicates, Parquet plus an engine like DuckDB will be simpler, cheaper, and better supported. TileDB's advantage appears when your data is genuinely N-dimensional and sparse.

**How do I choose chunk sizes without benchmarking?**
Start from the read pattern: aim for chunks large enough to amortise object-store requests (1–10 MB compressed is a common target) and small enough that a typical query touches a small number of them. Then measure — every workload here is chunk-sensitive, and no default is right for all of them.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HDF5 vs NetCDF4 vs Zarr vs TileDB in 2026: Which Array Storage Engine Should You Actually Use?",
  "description": "A practical 2026 comparison of HDF5, NetCDF4, Zarr and TileDB for scientific and analytical array storage, with install commands, h5py/xarray/zarr/TileDB code examples, chunking advice and self-hosting considerations.",
  "datePublished": "2026-10-11",
  "dateModified": "2026-10-11",
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
