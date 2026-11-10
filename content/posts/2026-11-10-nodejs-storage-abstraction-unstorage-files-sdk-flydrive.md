---
title: "Node.js Storage Abstraction in 2026: unstorage vs files-sdk vs Flydrive"
date: "2026-11-10"
tags: ["nodejs", "storage", "s3", "typescript", "developer-tools"]
description: "unstorage, files-sdk and Flydrive compared: driver catalogs, mount semantics, file handles, S3/R2 support and which one is safe to put in production in 2026."
cover: "/img/screenshots/files-sdk-logo.jpg"
draft: false
---

# Node.js Storage Abstraction in 2026: unstorage vs files-sdk vs Flydrive

You start with `fs.writeFile`, add S3 for uploads, then someone asks for R2 in staging and Azure Blob at one enterprise customer, and suddenly every route handler has a provider switch statement. The fix is a storage abstraction — one API, swappable backends. The three libraries that come up are not the same shape, and one of them has not shipped a commit since 2021.

Here is what each one actually does, with the real import paths and the parts that bite in production.

## TL;DR: The 60-Second Verdict

- **Key/value semantics, many backends, prefix routing between them:** **unstorage**. 2,661 stars, MIT, actively pushed (2026-11-10), and its driver catalog covers filesystem, Redis, S3/R2, Cloudflare KV bindings, MongoDB, SQLite via db0, and more — with Unix-style mounting so `cache:` can be Redis while `files:` stays on disk.
- **File/object semantics with a real typed API** (`upload`, `download`, `head`, `url`, signed uploads, `list`/`search`): **files-sdk**. 1,605 stars, MIT, and the only one of the three designed around Web-standard bodies (`Blob`, `File`, `ReadableStream`) instead of Node buffers.
- **You found `@slynova/flydrive` in an older tutorial:** do not adopt it. 406 stars, last push **2021-11-01**, three drivers, and a successor (`adonisjs/drive`, 72 stars) that is itself a thin wrapper. It is legacy maintenance, not a choice.

The short version: **unstorage for keys, files-sdk for files, Flydrive for nothing new.**

## The Three at a Glance

GitHub data pulled 2026-11-10.

| | **unstorage** | **files-sdk** | **Flydrive** |
|---|---|---|---|
| Repo | unjs/unstorage | haydenbleasel/files-sdk | Slynova-Org/flydrive |
| Stars | **2,661** | **1,605** | **406** |
| Last push | 2026-11-10 | 2026-11-01 | **2021-11-01** |
| License | MIT | MIT | MIT |
| Package | `unstorage` | `files-sdk` | `@slynova/flydrive` |
| Core model | async key/value + driver mounts | file/object operations via adapters | disk abstraction (`StorageManager#disk()`) |
| Drivers/adapters | **30+** (fs, redis, s3, r2, azure, mongo, db0, vercel, netlify, deno-kv, lru-cache…) | S3 + compatible, R2, GCS, Azure, Vercel Blob, local fs, Dropbox | **3** (local, s3, gcs) via separate packages |
| Multi-backend in one process | **yes, prefix mounts** | one adapter per `Files` instance | multiple disks in config |
| Value serialization | automatic JSON | Web-standard bodies | buffers/streams |
| Watching | yes (fs driver) | no | no |
| Built-in HTTP server | **yes** | no | no |
| Runtime support | Node, browser, Workers, Deno | Node 22+, Bun, Deno, Workers | Node (legacy) |

## Decision Matrix: Pick by Situation

| Your situation | Pick | Reason |
|---|---|---|
| Session cache in Redis, uploads on disk, metadata in SQLite — one API | unstorage | prefix mounts route each namespace to its own driver |
| Upload/download endpoints with presigned URLs | files-sdk | `url()`, `signedUploadUrl()`, `head()`, `list()` are first-class |
| Working in Nuxt/Nitro/unjs ecosystem | unstorage | it is the unjs storage layer Nitro already uses |
| Spec-compliant bodies (`Blob`, `ReadableStream`) because you also run on Workers | files-sdk | Web-standard I/O is the core design, not an adapter |
| You want provider-native features without rewriting | files-sdk | `files.raw` exposes the native client |
| Migrating a 2019 AdonisJS 4 project | Flydrive (temporarily), then plan an exit | it is what the old code already imports |
| New project | Flydrive | **never** — five years without a commit |

## unstorage — Key/Value With Unix-Style Mounts

unstorage's pitch is that a driver is a swappable backend behind one async KV API. The default is memory, which makes tests fast and honest:

```ts
import { createStorage } from "unstorage";
import redisDriver from "unstorage/drivers/redis";

const storage = createStorage({
  driver: redisDriver({ base: "my-app" }),
});
```

The feature that actually changes architecture is mounting. Mounts route a key prefix to another driver, and the most specific match wins:

```ts
import { createStorage } from "unstorage";
import fsDriver from "unstorage/drivers/fs";
import redisDriver from "unstorage/drivers/redis";

const storage = createStorage();

storage.mount("files", fsDriver({ base: "./data" }));
storage.mount("cache", redisDriver({ base: "my-app" }));
```

Now `storage.getItem("cache:session:42")` hits Redis while `storage.getItem("files:logo.png")` reads the disk. No provider switch, no second client, no dependency injection gymnastics. For a self-hosted app this is the cleanest way to keep hot data in Redis and blobs on a volume without inventing your own abstraction.

The catalog is genuinely wide: `fs`, `fs-lite`, `localstorage`, `indexeddb`, `deno-kv`, `lru-cache`, `null`, `overlay` for local/runtime; `db0` (SQLite/PostgreSQL/libSQL), `mongodb`, `planetscale`, `redis`, `upstash` for databases; and `s3`, `cloudflare-r2-binding`, `cloudflare-kv-binding`, `azure-storage-blob`, `netlify-blobs`, `vercel-blob`, `uploadthing` for cloud object storage. Values are JSON-serialized automatically, there is a watcher for the fs driver, and snapshots/hydration let you preload state.

It also ships an HTTP storage server, which means you can expose a namespace over HTTP and consume it from another process with the same API — useful when a background worker needs the same view of storage as the web tier.

**Where it breaks:** it is a KV abstraction, not a file manager. There is no presigned upload URL, no `head()` with content-type metadata semantics you would expect from an object store client, and no native escape hatch. Listing works, but you are listing keys, not enumerating objects with rich metadata. If your product is "upload a file, get a URL, set a content type," you will fight the abstraction.

## files-sdk — Object Storage Without the Provider Switch

files-sdk is the opposite trade-off: a small, honest file API with one adapter per backend and no KV pretence.

```ts
import { Files } from "files-sdk";
import { s3 } from "files-sdk/s3";

const files = new Files({
  adapter: s3({ bucket: "uploads" }),
});

await files.upload("avatars/abc.png", file, { contentType: "image/png" });
const got = await files.download("avatars/abc.png");
const exists = await files.exists("avatars/abc.png");
```

Swapping providers is an import change — `files-sdk/r2`, `files-sdk/gcs`, `files-sdk/azure` — and nothing else moves. Each provider's native SDK is an optional peer dependency, so you install only the client you actually use:

```bash
# S3 and anything S3-compatible: R2, MinIO, Spaces, B2, Wasabi
npm install files-sdk @aws-sdk/client-s3 @aws-sdk/s3-presigned-post @aws-sdk/s3-request-presigner

# Google Cloud Storage
npm install files-sdk @google-cloud/storage

# Azure Blob (add @azure/identity for Entra credentials)
npm install files-sdk @azure/storage-blob
```

That peer-dependency design is the difference between a 200 KB client bundle and a 40 MB one. It also means a missing adapter fails loudly with `ERR_MODULE_NOT_FOUND` naming the exact package, instead of a confusing runtime type error.

The API surface is the right one for file workloads: `upload`, `download`, `head`, `exists`, `delete`, `copy`, `move`, `list`/`listAll`, `search`, `url`, `signedUploadUrl`, `abortUpload`. Bodies are `Blob`, `File`, `ReadableStream`, `Uint8Array`, `ArrayBuffer` or `string` — no provider-specific types leaking into your handlers. `exists` returns `false` only on a genuine `NotFound`; auth, permission and transport errors still throw, which is the correct behavior and rarer than it should be.

For repeated access to the same key, file handles avoid re-passing the key everywhere:

```ts
const avatar = files.file("avatars/abc.png");

await avatar.upload(file, { contentType: "image/png" });

if (await avatar.exists()) {
  const meta = await avatar.head();
  const url = await avatar.url({ expiresIn: 300 });
}
```

When the provider is chosen at runtime — CLI tools, multi-tenant deployments — the loader avoids a hand-rolled adapter registry:

```ts
import { loadFiles } from "files-sdk/loader";

const { files, provider } = await loadFiles({
  bucket: "uploads",
  retries: 3,
  timeout: 10_000,
});
```

Set `FILES_SDK_PROVIDER` (for example `r2`) or pass `provider` directly; only the selected adapter is imported.

**Where it breaks:** it is one adapter per `Files` instance. If you need three backends simultaneously, you construct three `Files` objects and route yourself. And while `files.raw` exposes the native client, code that leans on it is no longer portable — use it deliberately, not as a default.

If you are running these against your own object store, our [MinIO vs SeaWeedFS vs Garage comparison](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/) covers the server side, and [LocalStack vs S3Ninja vs S3Mock](../2026-04-23-localstack-vs-s3ninja-vs-s3mock-self-hosted-s3-testing-tools-2026/) is the practical way to test adapters in CI. If you deploy to a Workers-compatible platform, the [self-hosted Workers comparison](../2026-11-10-self-hosted-workers-platforms-open-compute-workerd-winterjs/) explains which object bindings exist there.

## Flydrive — Why the Popular Answer Is the Wrong Answer

Flydrive is a framework-agnostic wrapper with a `StorageManager` facade and disk-based access:

```js
const { StorageManager } = require('@slynova/flydrive');
const storage = new StorageManager(config);

storage.disk();                 // default disk
storage.disk('awsCloud');       // the disk named "awsCloud" (s3 driver)
```

There are three drivers — `local`, `s3` and `gcs` — and the cloud ones live in separate packages (`@slynova/flydrive-s3`, `@slynova/flydrive-gcs`) that you register manually:

```js
storage.registerDriver('gcs', GoogleCloudStorage);
```

It is a reasonable 2019 design. The problem is the clock: **last push 2021-11-01**, 406 stars, and the successor `adonisjs/drive` sits at 72 stars while depending on `node-flydrive`. The S3 driver predates the AWS SDK v3 rewrite, which means you inherit a deprecated client, an old credential chain, and no answer for R2 or presigned-URL workflows.

If you are already running it, the migration is mechanical: map `disk().put/get/delete/exists` onto either unstorage's driver API (if you treat files as keys) or files-sdk's `upload/download/delete/exists` (if you need real file semantics). Do the mapping behind your own interface so the next migration is a one-file change — that is the actual lesson from Flydrive's decay, not "pick a better library."

## Pitfalls That Cost Real Debugging Time

**1. Key naming is a schema, not a string.** `files/logo.png` and `files:logo.png` are different namespaces in unstorage mounts. Decide the delimiter, write it down, and never let ad-hoc keys reach a mounted driver.

**2. Automatic JSON serialization cuts both ways.** unstorage serializes values for you, which is convenient until you store a `Buffer` and get an object back. Use the raw/binary path for bytes.

**3. Peer dependencies are a deployment concern.** files-sdk adapters fail at import time if the provider SDK is missing. That is good locally and a footgun in a slim container image — install the peer explicitly in the production layer.

**4. `exists()` semantics differ by provider.** files-sdk normalizes this (only `NotFound` yields `false`), but hand-rolled checks against legacy clients often swallow auth errors and report "file missing" when the real problem is a bad key.

**5. Mount order matters.** unstorage resolves the most specific matching mount, so a broad `""` mount can shadow what you think is a specific one. Test the resolution with explicit keys.

**6. Testing against the real backend is not optional.** Mocks pass with wrong content types and wrong ACLs. files-sdk ships live test suites (`LIVE_TESTS=1 bun test s3.live`) precisely because mock-only coverage misses provider quirks.

**7. Abandoned abstractions are a security surface.** A storage client that has not been updated since 2021 will not have fixes for credential-handling or request-signing issues found since. Age is a risk metric, not a style preference.

## FAQ

### What is the difference between unstorage and files-sdk?

unstorage is a key/value abstraction: you store and retrieve values by key across 30+ drivers, with automatic JSON serialization and prefix mounting. files-sdk is a file/object abstraction: you upload, download, head, list and generate URLs against object stores and blob providers. If your data is "values by key," use unstorage. If your data is "files with content types and URLs," use files-sdk.

### Can unstorage use S3 or Cloudflare R2 as a backend?

Yes. `unstorage/drivers/s3` covers Amazon S3, Cloudflare R2 and other S3-compatible stores, and there are dedicated Cloudflare binding drivers (`cloudflare-r2-binding`, `cloudflare-kv-binding`). The limitation is semantic, not technical: you get key/value operations, not presigned upload URLs or object metadata workflows.

### Is Flydrive still maintained?

No. The repository's last push was 2021-11-01 and it has 406 stars. AdonisJS moved on to `adonisjs/drive` (72 stars), which itself wraps `node-flydrive`. Treat Flydrive as legacy code to migrate away from, not a library to adopt in a new project.

### How do I use different storage backends in the same Node.js app?

With unstorage, mount each prefix to its own driver — `storage.mount("files", fsDriver(...))` and `storage.mount("cache", redisDriver(...))` — and the most specific mount wins. With files-sdk, construct one `Files` instance per adapter and select by tenant or environment in your own routing layer.

### Do these libraries work on Cloudflare Workers or Deno?

unstorage is explicitly designed for browser, Node and Workers environments, with drivers for KV, R2 bindings and Deno KV. files-sdk requires Node 22+ but states support for Bun, Deno and Cloudflare Workers, using Web-standard bodies so no Node buffer types leak into your code. Flydrive is Node-only legacy code.

### What about presigned upload URLs?

files-sdk exposes `signedUploadUrl()` and `url({ expiresIn })` as part of its core API, which is the main reason to choose it over a key/value abstraction when browsers upload directly to object storage. unstorage does not model presigned URLs — you would call the provider SDK directly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Storage Abstraction in 2026: unstorage vs files-sdk vs Flydrive",
  "description": "unstorage, files-sdk and Flydrive compared: driver catalogs, mount semantics, file handles, S3/R2 support and which one is safe to put in production in 2026.",
  "datePublished": "2026-11-10",
  "dateModified": "2026-11-10",
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
