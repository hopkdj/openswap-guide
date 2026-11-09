---
title: "ByteStash vs rustypaste vs Wastebin in 2026: Which Self-Hosted Pastebin Belongs in Your Stack?"
date: "2026-11-09"
tags: ["self-hosted", "pastebin", "rust", "docker", "developer-tools"]
draft: false
cover: "/img/screenshots/bytestash-snippets.jpg"
---

Every team has the same three secrets: a `curl` command that only works on one machine, a 400-line SQL query nobody wants to commit, and a config snippet that has been pasted into Slack eleven times. Public pastebins solve this until someone pastes a production connection string into one and it sits there, indexed, forever.

Self-hosting a paste service fixes that — but "pastebin" covers three genuinely different products. **ByteStash** is a snippet library with accounts and search. **rustypaste** is a tiny upload endpoint designed for scripts and CI. **Wastebin** is a human-facing pastebin with syntax highlighting and expiry. Choosing the wrong one means either fighting a UI you do not need or discovering that your "pastebin" has no authentication at all.

## TL;DR — the 30-second verdict

**Choose ByteStash** if humans will use it: it has accounts, tags, search, folders, and an optional PostgreSQL backend. **Choose rustypaste** if machines will use it: it is a single Rust binary with token auth, one-shot files, URL shortening, and a filesystem backend that needs no database. **Choose Wastebin** if you want the classic pastebin experience — paste text, get a link, it expires — with syntax highlighting for 170+ languages and zero configuration.

All three are open source, all three ship official container images, and all three will run in under 100 MB of RAM. The differences are in who is pasting.

## Side-by-side comparison

| Dimension | ByteStash | rustypaste | Wastebin |
|---|---|---|---|
| GitHub stars | **2,572** | 1,214 | 886 |
| Language | TypeScript (Node) | Rust | Rust |
| License | GPL-3.0 | MIT | MIT |
| Latest activity | Nov 2026 | Nov 2026 | Oct 2026 |
| Storage | SQLite or PostgreSQL | Filesystem | SQLite |
| User accounts | Yes (local + OIDC) | Token auth only | Optional paste passwords |
| Web UI | Full snippet manager | Minimal HTML form | Full pastebin UI |
| Syntax highlighting | Yes | No (raw + highlight.js on landing) | Yes, 170+ languages |
| Markdown rendering | Basic | No | Yes, GitHub-flavored |
| Paste expiry | No | Yes | Yes |
| One-shot links | No | Yes | Yes (delete after reading) |
| URL shortening | No | Yes | No |
| File uploads | Yes (as snippets) | Yes | No |
| API | REST + remote endpoint | REST | JSON API |
| Docker image | `ghcr.io/jordan-dalby/bytestash` | `orhunp/rustypaste` | `quxfoo/wastebin` |
| Default port | 5000 | 8000 | 8088 |

## Decision matrix: who is going to paste?

| Your situation | Recommended tool | Why |
|---|---|---|
| Five developers sharing reusable code | **ByteStash** | Tags, search, folders, per-user accounts |
| CI pipeline uploading build logs | **rustypaste** | Token auth, one-shot files, no UI needed |
| Sending a config snippet to a colleague | **Wastebin** | Paste, share link, auto-expire |
| You want SSO via Keycloak or Authentik | **ByteStash** | Native OIDC support |
| You refuse to run Node.js | **rustypaste** or **Wastebin** | Both are single Rust binaries |
| You need markdown rendering with tables | **Wastebin** | GFM tables, task lists, admonitions |
| You need short links for long URLs | **rustypaste** | Built-in URL shortening |
| You want the smallest possible attack surface | **rustypaste** | Filesystem storage, ~10 MB binary |

## ByteStash — the snippet library

ByteStash is the only one of the three that assumes multiple people. It stores snippets with a title, description, language, and tags, then gives you search and filtering across all of them. The UI is a three-pane layout — folders on the left, snippet list in the middle, code on the right — which is exactly what you want when you are hunting for "that nginx rewrite rule from last year".

The compose file is short, and the environment variables are the interesting part:

```yaml
services:
  bytestash:
    image: "ghcr.io/jordan-dalby/bytestash:latest"
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      BASE_PATH: ""
      ALLOWED_HOSTS: "localhost,paste.example.com"
      TOKEN_EXPIRY: 24h
      ALLOW_NEW_ACCOUNTS: "false"
      ALLOW_PASSWORD_CHANGES: "true"
      JWT_SECRET: "change-me-to-a-64-char-random-string"
    volumes:
      - ./data:/data/snippets
```

Four of those matter operationally. **`ALLOW_NEW_ACCOUNTS: "false"`** is the single most important setting on a public instance — without it, anyone who finds the URL can create an account. **`JWT_SECRET`** must be set explicitly, otherwise the container generates one and writes it into `/data/snippets`; that is fine for a test, bad for a backup-restore workflow. **`ALLOWED_HOSTS`** prevents host-header confusion when you terminate TLS at a reverse proxy. And **`BASE_PATH`** lets you serve the app from `example.com/paste` if you cannot get a dedicated subdomain.

ByteStash switches to PostgreSQL by setting a single variable — useful once you have more than a few thousand snippets or multiple replicas:

```yaml
    environment:
      DATABASE_URL: "postgres://bytestash:secret@postgres:5432/bytestash"
```

Keep the `/data/snippets` volume mounted either way: it holds the SQLite file used for migration and the generated JWT secret. The migration command is explicit, which is refreshing:

```bash
docker compose exec bytestash node src/scripts/migrateToPostgres.js
```

ByteStash also supports OIDC, so you can put it behind Authentik, Keycloak, or Pocket ID and skip local passwords entirely. The redirect URL is `https://paste.example.com/api/auth/oidc/callback`, and `PUBLIC_URL` must be set or the redirect will point at the wrong host.

![ByteStash snippet library with folders and code preview](/img/screenshots/bytestash-snippets.jpg "ByteStash snippet management interface")

## rustypaste — the upload endpoint

rustypaste does not want to be a destination. It wants to be a verb in your shell history. You `POST` a file, it returns a URL; you `GET` the URL, you get the file. The backend is the filesystem — no database, no migrations, no backup drama beyond copying a directory.

The compose file is four lines of substance:

```yaml
services:
  server:
    image: orhunp/rustypaste:${IMAGE_TAG:-latest}
    container_name: rustypaste
    restart: always
    environment:
      - RUST_LOG=info
    env_file:
      - ./.env
    ports:
      - "8000:8000"
    volumes:
      - ./upload/:/app/upload
      - ./config.toml:/app/config.toml
```

The behaviour lives in `config.toml`:

```toml
[server]
address = "0.0.0.0:8000"
max_content_length = "10MB"
upload_path = "./upload"
timeout = 30
expose_version = false

[paste]
random_url = { type = "petname" }
default_expiry = "1d"
delete_expired_files = { enabled = true, interval = "1h" }

[auth]
# tokens that are allowed to upload
token = ["s3cr3t-t0ken"]

[landing_page]
text = "internal paste service"
```

`random_url.type = "petname"` gives you URLs like `/capital-mosquito.txt` instead of a hash — easier to read aloud, easier to guess, so pair it with expiry. `delete_expired_files` is not enabled by default; without it, expired pastes stay on disk forever even though the links stop working. And the `[auth]` token list is what turns an open upload endpoint into a private one.

The real reason to pick rustypaste is the operational polish around the edges: one-shot files (deleted after the first download), one-shot URLs, password-protected files, URL shortening, pasting a file from a remote URL, and a `DELETE` endpoint that stays disabled unless you explicitly list `delete_tokens`. That last detail matters — an upload service with an unauthenticated delete endpoint is a denial-of-service waiting to happen.

A typical CI step looks like this:

```bash
curl -s -F "file=@build/report.html" \
  -H "Authorization: Bearer $PASTE_TOKEN" \
  https://paste.example.com/
```

No client library, no SDK. `curl` is the client.

## Wastebin — the classic pastebin, done properly

Wastebin is what most people mean when they say pastebin: a text box, a link, an expiry selector. What makes it worth running instead of a public service is the attention to detail — zstd compression on stored pastes, syntax highlighting for more than 170 languages via `syntect`, GitHub-flavoured Markdown rendering with tables and task lists, and a QR code so you can open a paste on your phone.

The minimal compose file:

```yaml
services:
  wastebin:
    image: quxfoo/wastebin:latest
    restart: always
    environment:
      - WASTEBIN_DATABASE_PATH=/data/state.db
      - WASTEBIN_TITLE=Internal Paste
      - WASTEBIN_SIGNING_KEY=at-least-64-bytes-of-random-text-goes-here-please-change
      - WASTEBIN_MAX_BODY_SIZE=2097152
      - WASTEBIN_PASTE_EXPIRATIONS=10m,1h,1d=d,1w,1M
      - WASTEBIN_THEME=catppuccin
    ports:
      - "8088:8088"
    volumes:
      - ./data:/data
```

Three of these are easy to get wrong. **`WASTEBIN_DATABASE_PATH` defaults to `:memory:`** — if you forget to set it and mount a volume, every restart wipes every paste. **`WASTEBIN_SIGNING_KEY`** must be at least 64 bytes; if you leave it unset, a random key is generated at startup, cookies are invalidated on every restart, and paste creators lose the ability to delete their own pastes. **`WASTEBIN_PASTE_EXPIRATIONS`** controls both the offered options and the default — the `=d` suffix marks which one is preselected.

The container runs as UID 10001, so the host directory must be writable by that user:

```bash
mkdir -p data && sudo chown -R 10001:10001 data
```

Wastebin also supports Unix sockets (`WASTEBIN_UNIX_SOCKET_PATH`), which is the cleanest way to run it behind nginx on the same host without exposing a TCP port at all.

![Wastebin paste view with syntax highlighting and expiry controls](/img/screenshots/wastebin-paste.jpg "Wastebin rendered paste with syntax highlighting")

## Pitfalls that bite in production

**An unauthenticated pastebin is a spam magnet.** The moment a public endpoint is indexed, you get SEO spam pastes. rustypaste needs `[auth].token`; Wastebin needs a reverse-proxy auth layer or network restrictions; ByteStash needs `ALLOW_NEW_ACCOUNTS=false` plus OIDC or closed registration. There is no fourth option.

**Body-size limits are your first line of defence.** Wastebin defaults to 1 MB, rustypaste to whatever `max_content_length` says. Raise them deliberately, not because a 200 MB upload failed once.

**Backups are trivial and therefore skipped.** rustypaste is `rsync ./upload`; Wastebin and ByteStash are SQLite files that must be copied with `.backup` or the container stopped first. Copying a live SQLite file with `cp` is how people discover database corruption.

**Reverse proxies break base paths.** If you serve from a subpath rather than a subdomain, set ByteStash's `BASE_PATH` and make sure your proxy strips the prefix consistently. Wastebin and rustypaste assume they own the root path.

**Expiry is not encryption.** Every one of these tools stores plaintext by default. If the content is sensitive, put it behind authenticated access, not behind a "expires in 10 minutes" setting.

## Which one fits your existing stack?

If you already run a code snippet habit — a folder of `.md` notes, a wiki, a Slack channel called `#snippets` — ByteStash is the natural upgrade because it gives that habit structure. If you are automating, rustypaste is the only one of the three designed to be called by a script rather than a human. If you just want to stop using public pastebins for internal configs, Wastebin is the least work.

For a broader look at the category, our [Opengist vs Pastefy vs PrivateBin comparison](../2026-04-30-opengist-vs-pastefy-vs-privatebin-self-hosted-code-sharing-guide/) covers git-backed and encrypted paste services, and the [code snippet manager roundup](../best-self-hosted-code-snippet-managers-privatebin-snippet-box-microbin-guide-2026/) covers tools that index snippets rather than host pastes. If your use case is closer to secret sharing than code sharing, see the [Password Pusher vs PrivateBin vs Bitwarden Send guide](../2026-05-03-passwordpusher-vs-privatebin-vs-bitwarden-send-self-hosted-password-sharing-guide/).

## FAQ

**Is ByteStash a pastebin or a snippet manager?**
Both, with the emphasis on snippet manager. It stores code with metadata — title, language, tags, folder — and gives you search across everything. If you need a throwaway link with a 10-minute expiry, Wastebin or rustypaste is a better fit.

**Can rustypaste run without a database?**
Yes, that is the design. Pastes are files under `upload_path`, metadata lives in the filename and file mtime, and expiry is enforced by a background task. Backups are a directory copy, which makes it the easiest of the three to operate.

**Does Wastebin support markdown?**
Yes. Markdown pastes render as HTML with GitHub-flavoured tables, task lists, and admonitions, and fenced code blocks get the same syntax highlighting as regular pastes. Raw HTML inside markdown is filtered.

**Which one should I expose to the public internet?**
None of them without authentication. If you must, Wastebin behind a reverse proxy with rate limiting and a strict body-size cap is the smallest attack surface, because it has no accounts, no upload API for arbitrary files, and no admin panel.

**Can I migrate between them?**
There is no shared format, but the data is simple: ByteStash exports snippets, Wastebin stores rows in SQLite, rustypaste stores files on disk. In practice, migration means re-pasting the twenty snippets you actually use — which is a good excuse to delete the other four hundred.

**Do these tools support team collaboration?**
Only ByteStash does, via local accounts or OIDC. rustypaste has token-based upload auth but no concept of users, and Wastebin's optional password protection is per-paste rather than per-user.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ByteStash vs rustypaste vs Wastebin in 2026: Which Self-Hosted Pastebin Belongs in Your Stack?",
  "description": "Hands-on comparison of three self-hosted paste services — ByteStash, rustypaste and Wastebin — with production Docker Compose configs, authentication guidance and operational pitfalls.",
  "datePublished": "2026-11-09",
  "dateModified": "2026-11-09",
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
