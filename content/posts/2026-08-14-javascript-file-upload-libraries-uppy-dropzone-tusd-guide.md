---
title: "File Uploads in 2026: Uppy vs Dropzone vs tusd — Which Should You Actually Use?"
date: "2026-08-14"
tags: ["javascript", "file-upload", "frontend", "web-development", "developer-tools"]
draft: false
cover: "/img/screenshots/uppy-dashboard.jpg"
---

Your user just spent **four minutes uploading a 2 GB video, and at 87% the connection dropped**. The progress bar resets to zero, the browser shows `NETWORK_ERROR`, and you get a support ticket the same afternoon. This is the real cost of a naive `<input type="file">` approach: every flaky mobile connection, every corporate proxy timeout, and every 4 GB camera export turns into lost data and lost trust.

The fix is not a bigger server. It is picking the right upload stack — and in 2026 that means deciding between three very different layers: a **framework-agnostic drop-in UI** (Dropzone), a **full upload pipeline with resumable transport** (Uppy), and a **standards-based resumable upload server** (tusd). This guide compares all three with real code, real star counts, and honest trade-offs, so you can stop guessing and ship uploads that survive anything.

## TL;DR — Quick Verdict

**If you need a resumable, protocol-correct upload backend, run tusd.** **If you want a polished drag-and-drop upload UI with the least code, use Uppy** (it speaks the tus protocol natively, so the two are a natural pair). **Dropzone is the minimalist's choice**: a single 40 KB script that turns any element into a drop zone, perfect for small files and simple forms, but it has no built-in resumability, no retry logic, and its repo has not seen meaningful commits since 2024.

| Dimension | Uppy | Dropzone | tusd |
|---|---|---|---|
| **Role** | Client upload pipeline (UI + plugins) | Client drop-zone widget | Server implementing the tus protocol |
| **GitHub stars** | **30,920** | 18,382 | 3,846 |
| **Last push** | 2026-08-13 | 2024-07-15 | 2026-08-01 |
| **License** | MIT | MIT | MIT |
| **Bundle size** | ~50 KB core (plugins extra) | ~40 KB | ~20 MB binary |
| **Resumable uploads** | ✅ via tus or S3 multipart | ❌ (single-shot XHR) | ✅ native tus protocol |
| **Retry / pause / resume UI** | ✅ built-in | ❌ | ✅ server-side (any client) |
| **Remote sources** (Google Drive, Dropbox, URLs) | ✅ via Companion | ❌ | ❌ |
| **Image editing / webcam capture** | ✅ plugins | ❌ | ❌ |
| **Framework bindings** | React, Vue, Svelte, Angular + vanilla | jQuery-friendly, vanilla | any language (HTTP API) |
| **Best for** | Product-grade upload UX | Quick drop zones | Upload backend at any scale |

| Use Case | Pick | Why |
|---|---|---|
| Large files (100 MB–100 GB) over flaky networks | **Uppy + tusd** | Pause/resume + chunked tus protocol end-to-end |
| Simple contact-form attachments (< 25 MB) | **Dropzone** | 5 lines of code, zero server changes |
| You already use S3 and need uploads to go straight there | **tusd with S3 storage** or Uppy's S3 Multipart plugin | Multipart uploads with server-side orchestration |
| Uploads from Google Drive / Dropbox / remote URLs | **Uppy + Companion** | Only option with first-class remote-source support |
| You need uploads that work in every framework, including vanilla JS | **Dropzone** | No framework assumptions, tiny footprint |
| Maximum reliability for enterprise media pipelines | **tusd + any tus client** | Protocol is language-agnostic; clients exist for 10+ languages |

## Uppy — The Full Upload Pipeline

Uppy (MIT, **30,920 stars**, actively maintained with pushes in August 2026) is not a widget — it is a modular upload pipeline: drag-and-drop dashboard, webcam capture, image editor, remote sources via Companion, and a transport layer that speaks **both the tus protocol and S3 multipart**. That last part is the killer feature: your uploads can pause, resume, and retry without you writing a single byte of retry logic.

Install the pieces you need:

```bash
npm install @uppy/core @uppy/dashboard @uppy/tus
```

Wire them together with the exact pattern from the official README:

```js
import Uppy from '@uppy/core'
import Dashboard from '@uppy/dashboard'
import RemoteSources from '@uppy/remote-sources'
import Webcam from '@uppy/webcam'
import ImageEditor from '@uppy/image-editor'
import Tus from '@uppy/tus'

const uppy = new Uppy()
  .use(Dashboard, { trigger: '#select-files' })
  .use(RemoteSources, { companionUrl: 'https://companion.uppy.io' })
  .use(Webcam)
  .use(ImageEditor)
  .use(Tus, { endpoint: 'https://tusd.tusdemo.net/files/' })
  .on('complete', (result) => {
    console.log('Upload result:', result)
  })
```

The dashboard gives you drag-and-drop, file previews, progress bars, pause/resume buttons, and error recovery out of the box. `@uppy/tus` splits the file into chunks, and if the network dies, the next request asks the server "where did we get to?" and continues from that byte — no re-uploading.

**Where Uppy costs you**: the plugin architecture means you should code-split it, and Companion (for Google Drive / Dropbox / remote URLs) is an extra Node.js service you must host and secure. For a plain "upload my file" form, it is more machinery than you need.

## Dropzone — The Minimalist Drop Zone

Dropzone (MIT, **18,382 stars**) is the library that started the drag-and-drop upload trend. One script, one line of init, and every element with a `.dropzone` class becomes an upload target with previews and progress bars:

```bash
npm install --save dropzone
```

```js
import Dropzone from 'dropzone'

// Any element with class="dropzone" is now an upload target
new Dropzone('div#my-dropzone', {
  url: '/upload',
  maxFilesize: 25,          // MB
  acceptedFiles: 'image/*',
  parallelUploads: 2,
  dictDefaultMessage: 'Drop files here or click to upload'
})
```

Dropzone handles styling, thumbnail previews, file-type validation, and queueing gracefully, and it is genuinely framework-agnostic — you can use it from React, Vue, or a plain server-rendered page. For small files on reasonably reliable connections, it is often the right answer: **zero backend changes, five lines of frontend code**.

**Where Dropzone hurts**: uploads are single-shot XMLHttpRequests. No chunking, no pause/resume, no automatic retry — if the connection dies at 90%, the user starts over. The project's last meaningful release activity was mid-2024 (pushedAt 2024-07-15), so while it is stable and battle-tested, you are betting on a mature but slow-moving codebase. Its own author describes it as "easy to use drag'n'drop" — which is exactly its lane, and exactly its ceiling.

## tusd — The Resumable Upload Server

tusd (MIT, **3,846 stars**) is the reference server implementation of the **tus resumable upload protocol** — an open, language-agnostic standard that lets any client pause, resume, and retry uploads over plain HTTP `PATCH` requests. Because the protocol is the contract, your client library and server never need to agree on chunk sizes or retry semantics; they just follow the spec.

The official Docker image is the fastest way to stand one up:

```bash
docker pull tusproject/tusd:latest
docker run tusproject/tusd:latest -s3-bucket=my-bucket
```

For production, the official example `docker-compose.yml` pairs tusd with MinIO for S3-backed storage with Swarm secrets:

```yaml
version: "3.9"
services:
    tusd:
      image: tusproject/tusd:v1.9
      command: -verbose -s3-bucket mybucket -s3-endpoint http://minio:9000
      volumes:
        - tusd:/data
      environment:
        - AWS_REGION=us-east-1
        - AWS_ACCESS_KEY_ID_FILE=/run/secrets/minio-username
        - AWS_SECRET_ACCESS_KEY_FILE=/run/secrets/minio-password
      secrets:
        - minio-username
        - minio-password
      networks:
        - tusd

volumes:
  tusd:

secrets:
  minio-username:
    external: true
  minio-password:
    external: true

networks:
  tusd:
```

tusd's real strengths show up in production: it persists upload state (a crashed server resumes the upload where it left off), supports **local disk, S3-compatible storage, and Google Cloud Storage** backends, and exposes hooks for authentication and post-upload processing. Since the protocol is open, you can pair it with the official JavaScript client, a Go client, Python, Java, Rust, or the tus clients built into Uppy — all of them resume against the same server.

**Where tusd costs you**: it is a server, not a UI. You still need a frontend (Uppy's Tus plugin, or a bare tus-js-client) and you must handle CORS, authentication hooks, and storage lifecycle yourself. For a 5 MB contact-form attachment it is overkill — for anything that hurts when lost, it is the only honest choice.

## Why Resumability Is a Protocol Problem, Not a Library Problem

Here is the trap most teams fall into: they build "retry" by wrapping an upload in a `for` loop and hoping. That breaks the moment a partial upload reaches the server — the server has no idea what bytes it already has, so the client must start over or the server ends up with a corrupt file. The tus protocol fixes this structurally: a `HEAD` request returns the number of bytes stored, and the client resumes with `PATCH` at that exact offset. Chunked, idempotent, resumable — with zero ambiguous state. This is why **resumability is a server protocol decision, not a frontend flourish**: tusd gives it to every client that speaks the protocol, today and in ten years.

## Common Pitfalls and Migration Notes

- **Don't put a 100 GB video through a normal reverse proxy.** nginx and Caddy buffer requests by default; a 2 GB upload can fill memory buffers and get killed mid-flight. Set `client_max_body_size` explicitly and either stream (`proxy_request_buffering off` in nginx) or send chunked tus requests that keep each PATCH small.
- **CORS is the #1 silent failure.** When your frontend and upload endpoint are on different origins, configure `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods: POST, HEAD, PATCH, OPTIONS`, and `Access-Control-Allow-Headers: tus-resumable, upload-length, upload-metadata, upload-offset, content-type`. Uppy surfaces cryptic CORS errors; test the preflight with `curl -X OPTIONS` before blaming the client.
- **Chunk size is a tuning dial, not a constant.** Uppy's tus plugin defaults are sensible, but on high-latency mobile links, smaller chunks (5–10 MB) resume faster; on reliable gigabit links, larger chunks reduce overhead. Measure, don't assume.
- **Migrating from plain XHR to tus changes your backend contract.** Your existing `/upload` endpoint that returns a URL becomes a tus endpoint that returns upload metadata — plan the transition, keep the old endpoint during the cutover, and use `upload-metadata` headers to carry your original fields.
- **Storage backends are not interchangeable.** tusd's local-disk mode is perfect for a single node; S3 mode changes cost and consistency characteristics (multipart parts are stored server-side). If you run behind a load balancer with local disk, pin uploads to one node or switch to S3 storage — otherwise resumability breaks across restarts.
- **Remote sources (Drive/Dropbox) are a security surface.** Companion proxies third-party credentials; restrict its origin, rate-limit it, and keep it on an internal network if possible.
- **For related storage and sharing decisions**, see our [S3 object storage comparison (MinIO vs SeaweedFS vs Garage)](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/), the [secure file sharing guide (Gokapi vs Lufi vs FileShelter)](../2026-05-05-gokapi-vs-lufi-vs-fileshelter-secure-self-hosted-file-sharing/), and the [file sharing protocols comparison (Samba vs NFS vs WebDAV)](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "File Uploads in 2026: Uppy vs Dropzone vs tusd — Which Should You Actually Use?",
  "description": "Deep comparison of JavaScript file upload libraries: Uppy, Dropzone, and the tusd resumable upload server. Real code, live GitHub stats, decision matrix, and migration pitfalls.",
  "datePublished": "2026-08-14",
  "dateModified": "2026-08-14",
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

**Is Dropzone still maintained in 2026?**
Dropzone is stable and widely used (18,382 stars), but its last significant activity was mid-2024. It works fine for small files and simple forms, but treat it as feature-complete rather than actively evolving — don't expect resumability or remote-source support to arrive.

**Do I need both Uppy and tusd?**
No, but they are designed to work together. Uppy's `@uppy/tus` plugin talks to any tus server including tusd. You can also use Uppy with a plain XHR endpoint, or use tusd with the bare `tus-js-client` — but the full reliability story (pause, resume, retry) requires a tus server on the backend.

**Which upload stack handles files larger than 5 GB?**
tusd with the tus protocol, or Uppy's S3 Multipart plugin. Both avoid loading the whole file into memory and support byte-range resumption. Plain Dropzone or XHR uploads will struggle with multi-gigabyte files on any real-world network.

**How does tusd store files — do I need S3?**
No. tusd supports local disk storage out of the box, plus S3-compatible and Google Cloud Storage backends. Local disk is fine for a single server; S3 is recommended for horizontal scaling and restart safety.

**What about uploads from Google Drive or Dropbox?**
Only Uppy with Companion supports remote sources like Google Drive, Dropbox, Box, and plain remote URLs. Dropzone and bare tusd do not — the user must download the file locally first.

**Is there a way to add resumability without changing my backend?**
Yes, if your backend supports ranged PUT or multipart: use Uppy's `@uppy/aws-s3-multipart` plugin, which performs multipart uploads directly to S3 from the browser. Otherwise, adding tusd (a single Go binary or container) is the least invasive way to get a real resumable protocol.

**Which license restrictions apply?**
All three are MIT licensed, including tusd. You can use them in commercial products, self-hosted or SaaS, without paying licensing fees or disclosing source.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
