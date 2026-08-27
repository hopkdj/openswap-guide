---
title: "Multer vs Busboy vs Formidable in 2026: Node.js File Upload Parsing, Decoded"
cover: "/img/screenshots/formidable-cover.jpg"
date: "2026-08-28"
tags: ["nodejs", "file-upload", "multipart", "library-comparison", "javascript"]
draft: false
---

Here is a fact most Express developers do not know: the `multer` middleware you use for every file upload is not a parser at all — it is a convenience wrapper around **busboy**, a lower-level streaming parser. And the library that started this entire ecosystem, **formidable**, warns in its own README that its most-used versions have been deprecated for years and are *"vulnerable to attacks if you are not implementing it properly."* Three libraries, one `multipart/form-data` problem, and very different trade-offs between convenience, control, and security. This guide compares them with live repository data and real code from the official docs.

## TL;DR / Quick Verdict

If you use **Express**, just keep using **Multer** — it is the safest, most ergonomic choice, and it delegates parsing to busboy under the hood anyway. If you need **raw control** over streaming, memory, or non-Express servers (fastify, plain `http`), use **busboy** directly. If you are still on formidable v1 or v2 — and a shocking number of projects are — **upgrade to v3+ today**; the old versions are deprecated and carry real security warnings. Do not build new projects on formidable; it is legacy with a maintenance team, not a growth library.

## Quick Comparison Table

| Criteria | Multer | Busboy | Formidable |
|---|---|---|---|
| GitHub stars | 12,085 | 2,998 | 7,178 |
| Last push | 2026-08-25 (active) | 2024-05-31 (stable) | 2026-08-06 (active) |
| License | MIT | MIT | MIT |
| Role | Express middleware | Low-level parser | Standalone parser + helpers |
| Built on | busboy | — | — |
| Streaming | Yes (via busboy) | Yes (core design) | Yes |
| Memory mode | `memoryStorage` built-in | Manual accumulation | `multiples` + options |
| Express integration | First-class | Manual | Manual |
| Non-Express servers | Awkward | Ideal | Good |
| File size limits | Built-in (`limits`) | Manual enforcement | Built-in (`maxFileSize`) |
| v1/v2 legacy risk | N/A | N/A | **Deprecated + security warnings** |

## Decision Matrix

| Use Case | Recommended | Why |
|---|---|---|
| Express API with file uploads | Multer | `upload.single('avatar')` and friends; storage engines included |
| Streaming uploads to S3/object storage | Busboy | Emit file data as a stream and pipe it — zero disk buffering |
| Microservice on fastify/Hono/plain http | Busboy | Framework-agnostic parser with a minimal event API |
| Legacy project on formidable v1/v2 | Formidable v3+ (upgrade now) | v3 is the maintained line; the old ones are flagged in the README |
| Multi-file uploads with fields in one request | Multer or Formidable | Both handle `upload.array()` / `form.parse()` cleanly |
| Tiny footprint, no framework at all | Busboy | Only dependency you add is the parser itself |

## Multer — The Express Default

Multer is the middleware that made file uploads boring, in the good sense. At **12,085 stars** with the last commit on **2026-08-25**, it is actively maintained by the Express organization. It is written on top of busboy — the README says so explicitly — and adds the ergonomics Express developers expect: a `file` or `files` object on the request, a `body` object for text fields, and pluggable storage engines.

The basic flow is two lines:

```html
<form action="/profile" method="post" enctype="multipart/form-data">
  <input type="file" name="avatar" />
</form>
```

```javascript
const express = require('express')
const multer  = require('multer')
const upload = multer({ dest: 'uploads/' })

const app = express()

app.post('/profile', upload.single('avatar'), function (req, res, next) {
  // req.file is the `avatar` file
  // req.body will hold the text fields, if there were any
})

app.post('/photos/upload', upload.array('photos', 12), function (req, res, next) {
  // req.files holds up to 12 files
})
```

When you need control over where files land and what they are named, `diskStorage` is the documented pattern:

```javascript
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, '/tmp/my-uploads')
  },
  filename: function (req, file, cb) {
    crypto.randomBytes(16, function (err, raw) {
      if (err) return cb(err)
      cb(null, file.fieldname + '-' + raw.toString('hex'))
    })
  }
})

const upload = multer({ storage: storage })
```

You can also set `limits` (file size, field count, parts) to protect against denial-of-service, and `fileFilter` to reject files by type before they are stored. The trade-off: Multer is Express-shaped. Using it outside Express means reimplementing the middleware hand-off, which is where busboy wins.

## Busboy — The Parser Under the Hood

Busboy, by Brian White (mscdex), is the streaming parser that Multer delegates to. It has **2,998 stars**, and its last push was **2024-05-31** — quiet because it is *done*, not because it is abandoned; the API surface is small and stable. Busboy never buffers a whole file: it emits `file` events with a readable stream you consume as data arrives.

Its official example works on a bare `http` server:

```javascript
const http = require('http');
const busboy = require('busboy');

http.createServer((req, res) => {
  if (req.method === 'POST') {
    const bb = busboy({ headers: req.headers });
    bb.on('file', (name, file, info) => {
      const { filename, encoding, mimeType } = info;
      file.on('data', (data) => {
        console.log(`File [${name}] got ${data.length} bytes`);
      }).on('close', () => {
        console.log(`File [${name}] done`);
      });
    });
    bb.on('field', (name, val, info) => {
      console.log(`Field [${name}]: value: %j`, val);
    });
    bb.on('close', () => {
      console.log('Done parsing form!');
      res.writeHead(303, { Connection: 'close', Location: '/' });
      res.end();
    });
    req.pipe(bb);
  }
}).listen(8080);
```

That `req.pipe(bb)` line is the whole story: you get the multipart stream as it arrives, and you can pipe each file straight to disk, S3, or any writable stream. The README also carries an important operational note: since Node 18, the HTTP server's `requestTimeout` is enabled by default, which can interrupt long uploads — bump it if you serve large files. Busboy gives you total control and zero magic, at the cost of writing your own file-storage logic.

## Formidable — The Pioneer That Fell Asleep

Formidable is the original Node.js form parser, created by Felix Geisendörfer in 2010 and now maintained by the formidable community. At **7,178 stars** with a push on **2026-08-06**, it is not abandoned — but its own README delivers the bluntest warning in this comparison: as of April 2025, v1 and v2 *"are still the most used, while they are deprecated for years — they are also vulnerable to attacks if you are not implementing it properly. Please upgrade!"*

The maintained v3 API is clean and promise-based:

```javascript
const form = formidable({});
let fields;
let files;
try {
  [fields, files] = await form.parse(req);
} catch (err) {
  res.writeHead(err.httpCode || 400, { "Content-Type": "text/plain" });
  res.end(String(err));
  return;
}
res.writeHead(200, { "Content-Type": "application/json" });
res.end(JSON.stringify({ fields, files }, null, 2));
```

![Formidable benchmark chart](/img/screenshots/formidable-benchmark.jpg "Official formidable benchmark from the project README")

The team also points to `formidable-mini`, a minimal web-standards-based variant (FormData API + File API) designed for streaming uploads directly to S3. Formidable's historical benchmark chart above shows why it dominated for years — but the ecosystem moved on. In 2026, the honest recommendation is: use it only to modernize existing v1/v2 deployments.

## Pitfalls and Migration Notes

- **The formidable v1/v2 trap is real.** The README explicitly calls old versions vulnerable. If `npm audit` or a dependency tree shows `formidable@^1 || ^2`, treat it as a security task, not a chore. The v3 API is a rewrite; budget time for migration, and check `formidable-mini` if you only need streaming to object storage.
- **Do not write uploads to disk by default.** `multer({ dest: 'uploads/' })` is convenient and wrong for production: you now manage orphaned temp files, permissions, and cleanup. Use `memoryStorage` (small files) or `diskStorage` with a deliberate filename policy (random bytes, never user input — see the `crypto.randomBytes` pattern above).
- **User-supplied filenames are attack vectors.** `file.originalname` can contain path traversal sequences. Never build a filesystem path from it directly; always generate your own storage name and keep the original only in metadata.
- **Size limits are a DoS control, not a nicety.** Multer `limits.fileSize`, formidable `maxFileSize`, and busboy `limits` all exist. Set them; a single 10 GB multipart body can exhaust memory on any of the three without limits.
- **Express 5 and middleware ordering.** File-parsing middleware must run before your JSON body parser's error handling swallows multipart errors. Verify `app.use(upload.single(...))` is mounted on the route, not globally, unless you want every route paying the parse cost.
- **Node 18+ `requestTimeout` breaks slow uploads.** Both busboy's README and real-world tickets report long uploads being cut off by the default 300s request timeout. Raise it explicitly for upload endpoints.
- **`upload.array` field-count mismatches fail loudly.** If the client sends more files than the limit, Multer errors the request — catch that error with an error-handling middleware, or users get a bare 500.
- **Test with real multipart bodies.** `curl -F "avatar=@photo.jpg"` is the minimum. Also test chunked/streamed uploads and non-ASCII filenames; the three libraries handle them differently.

For the client side of the same problem, see our [JavaScript upload library comparison (Uppy, Dropzone, tus)](../2026-08-14-javascript-file-upload-libraries-uppy-dropzone-tusd-guide/), the [resumable upload server guide (tusd, tus-node-server, tusdotnet)](../2026-05-02-self-hosted-resumable-file-upload-servers-tusd-tus-node-server-tusdotnet-guide/) if your users upload large files over flaky connections, and [self-hosted upload servers (Zipline, ShareX, Flowinity)](../2026-04-25-zipline-vs-sharex-upload-server-vs-flowinity-self-hosted-file-upload-screenshot-server-guide-2026/) when you want a full product instead of a library.

## FAQ

### Is Multer built on top of Busboy?

Yes. Multer's README states it is written on top of busboy for maximum efficiency. Multer is the ergonomic middleware layer; busboy is the streaming parser.

### Is Formidable still maintained?

Yes — the formidable community pushed commits as recently as **2026-08-06** and maintains the v3 line plus `formidable-mini`. However, the most-installed versions (v1/v2) are deprecated and flagged as vulnerable in the README. Upgrade any legacy usage.

### Which Node.js upload library is fastest?

At the parsing level they are all streaming and comparable; busboy is the raw engine with the least overhead, and Multer inherits that speed. The real performance difference comes from storage: writing to disk is fast but fragile, memory storage caps out at your heap, and streaming to object storage is slowest per byte but infinitely scalable.

### Can Busboy handle file size limits?

Busboy accepts a `limits` option (file size, files, fields, parts), but it is a low-level library — you must wire the enforcement and the error response yourself. Multer and formidable ship limit handling integrated with their APIs.

### Should I use Multer or Busboy for a Fastify app?

Busboy. Multer is designed around Express's middleware model; with Fastify you would fight the framework. Busboy plugs into any `req` stream and is the common recommendation for non-Express servers.

### What is the safest way to store uploaded files?

Never trust `file.originalname` — generate a random storage name (the `crypto.randomBytes(16, ...)` pattern from Multer's docs is the canonical approach), store the original name only as metadata, and set explicit size limits. For large files, stream to object storage instead of the local disk.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Multer vs Busboy vs Formidable in 2026: Node.js File Upload Parsing, Decoded",
  "description": "Compare Multer, Busboy, and Formidable for Node.js multipart file upload parsing: streaming, Express integration, security warnings, and the formidable v1/v2 upgrade question.",
  "datePublished": "2026-08-28",
  "dateModified": "2026-08-28",
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
