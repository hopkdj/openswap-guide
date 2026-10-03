---
title: "Flat-File CMS Comparison 2026: Statamic vs Kirby vs PluXML vs FlatPress"
date: "2026-10-03"
tags: ["cms", "self-hosted", "flat-file", "php", "web-hosting"]
draft: false
cover: "/img/screenshots/kirby-panel.jpg"
description: "Four flat-file CMS platforms compared for 2026: Statamic, Kirby, PluXML and FlatPress. Real install commands, licence costs, PHP limits and Docker deployment."
---

Your database-backed CMS is quietly becoming a liability: an extra service to patch, an extra backup to verify, an extra way for a small blog to go offline at 2 a.m. Flat-file CMS platforms throw the database away entirely — content lives in plain files on disk, and a page render is nothing more than a filesystem read. For the right project that is not a downgrade, it is a simplification. The catch is that "flat-file" spans a huge range of products: a commercial Laravel application at one end and a 200-star GPL blog engine at the other.

This guide compares the four flat-file CMS platforms that are genuinely maintained in 2026 — **Statamic, Kirby, PluXML and FlatPress** — with real repository data, real install commands and the licensing traps that decide most of these choices before performance ever enters the room.

## TL;DR — Quick Verdict

**Pick Statamic** if you want a Laravel-powered editorial platform with a Git-based content workflow and you are comfortable paying for a Pro licence on commercial projects. **Pick Kirby** if you are a developer or designer building a bespoke site and want a flexible PHP API with no framework lock-in — just budget one licence per production site. **Pick PluXML** if you want a classic multi-user blog with roles, plugins and zero licence cost on a small host. **Pick FlatPress** if you want the simplest possible no-database blog that runs on shared PHP hosting and needs a folder copy as its entire backup strategy. If you need zero licence fees, the two GPL options are your only candidates.

## At-a-Glance Comparison

| | Statamic | Kirby | PluXML | FlatPress |
|---|---|---|---|---|
| **Stack** | PHP + Laravel | Plain PHP, no framework | Plain PHP | Plain PHP |
| **Data store** | Flat files (YAML/Markdown) + Git | Flat files in `content/` | Flat XML files | Flat PHP-serialised files |
| **Database required** | No | No | No | No |
| **Licence** | Commercial (free tier, Pro paid) | Commercial (free to test, paid per site) | **GPL-3.0** | **GPL-2.0** |
| **GitHub stars** | 4,904★ | 1,535★ | 234★ | 215★ |
| **Latest release** | v6.35.0 | 5.6.0 | v5.8.23 | 1.5.1 |
| **Last commit** | 2026-10-02 | 2026-10-02 | 2026-09-19 | 2026-09-08 |
| **PHP support window** | 8.1+ (Laravel requirement) | 8.0+ | 5.6.34 → **8.1.2 max** | 7.2 → 8.5 |
| **Best for** | Editorial and marketing sites | Custom client builds | Classic small blogs | Hobby blogs, tiny hosts |

The star counts are pulled live from GitHub at publish time and are the single clearest signal of how alive each project is. Note that the two most-starred projects are also the two commercial ones — that is not a coincidence. Paid CMS work funds paid maintainers.

## Decision Matrix: Which One for Which Job

| Use case | Pick | Why |
|---|---|---|
| Content team editing through Git pull requests | **Statamic** | Content stored as Markdown/YAML in the repo, with Laravel tooling around it |
| Designer-built portfolio or agency site | **Kirby** | Flexible PHP API, template-per-page, no framework to fight |
| Multi-author blog with user roles on a €5 VPS | **PluXML** | Built-in users, grants, comments, plugins — and GPL licensing |
| One-person blog on shared hosting | **FlatPress** | No database, no Composer, no build step; unzip and run the installer |
| Zero licence budget, must be open source | **PluXML or FlatPress** | Both GPL; Statamic and Kirby require payment for production use |
| Headless/API-first delivery | **Statamic** | Laravel routing plus a REST layer makes it the only one of the four aimed at it |

## Statamic — Laravel-Powered, Flat-First

Statamic is the heavyweight here: 4,904 stars, releases cut within days of writing (v6.35.0, repo pushed 2026-10-02), and a templating language called Antlers layered on top of Laravel. "Flat-first" means content is written to files rather than a relational database, which makes the whole site diffable in Git and trivially deployable.

The install path is Composer-based, and there is an official CLI that scaffolds a preconfigured Laravel application so you never hand-assemble the skeleton:

```bash
# Recommended: the Statamic CLI tool
composer global require statamic/cli
statamic new my-site

# Alternative: create the project straight from the application repository
composer create-project statamic/statamic my-site
cd my-site

# Serve locally
php please serve
```

A critical structural detail that trips up newcomers: `statamic/cms` is the **core Composer package**, not a standalone application. If you clone that repository expecting a runnable site you will end up wiring Laravel by hand. Use the CLI or the application repository instead.

**Licensing is the real decision point.** Statamic is not OSI open source. It has a free tier that covers local development and solo projects, but production and client work require a Pro licence. For a single site the cost is easy to justify; for a portfolio of twenty micro-sites it changes the arithmetic completely.

## Kirby — The Flat-File CMS That Stays Out of Your Way

Kirby (1,535★, 5.6.0, pushed 2026-10-02) is the opposite philosophy: no framework, no database, no assumptions. You get a `content/` directory of text files, a PHP API for querying them, and templates you write yourself. The editing experience is a genuinely polished panel — a screenshot from the official project page shows exactly what your editors get:

![Kirby CMS panel interface](/img/screenshots/kirby-panel.jpg "Kirby CMS content editing panel")

Deployment is either a download or Composer:

```bash
# Option A — the Plainkit, a bare Kirby installation
curl -L -o plainkit.zip https://github.com/getkirby/plainkit/archive/main.zip
unzip plainkit.zip && mv plainkit-main my-kirby-site

# Option B — Composer
composer create-project getkirby/plainkit my-kirby-site

# Serve locally using PHP's built-in server and Kirby's router
php -S localhost:8000 kirby/router.php
```

Kirby stores each page as a directory containing a text file plus its media, which is why "backup" means "copy a folder" and why moving hosts never involves an SQL dump. The trade-off is licensing: the repository README states plainly that Kirby is **not free software**. You may develop and test locally for as long as you like, but each production site needs a licence. Compared with Statamic the licence model is simpler (per site rather than per tier), and the codebase is small enough to read end-to-end in an afternoon.

## PluXML — Small, Classic, GPL

PluXML (234★, v5.8.23, GPL-3.0) is a French-origin flat CMS that predates the current flat-file fashion by well over a decade. It behaves like a traditional blogging platform: articles, pages, categories, tags, comments, a media manager, multi-user support with permission levels, themes and plugins — all stored in flat XML files.

Installation is the classic upload-and-run pattern:

```bash
# Grab the v5.8.23 release archive from the GitHub releases page
git clone https://github.com/pluxml/pluxml.git pluxml
mv pluxml /var/www/html/pluxml

# Make the data directories writable by the web server user
chown -R www-data:www-data /var/www/html/pluxml/data
chmod -R 775 /var/www/html/pluxml/data

# Then open the admin UI and run the installer
# https://your-host/pluxml/core/admin/
```

**The PHP ceiling is the trap.** PluXML's own prerequisites state support for PHP **5.6.34 through 8.1.2** — with 7.2.5+ required for its mail library. If your host is already on PHP 8.2 or 8.3, PluXML will not run cleanly. That single constraint rules it out on many modern shared hosts and is the most common support question around the project. Its strengths are the licence (GPL-3.0, no fees ever), the eleven bundled translations and a genuinely lightweight footprint — it will run happily on hardware that would make a Laravel application weep.

## FlatPress — Blogging With No Database at All

FlatPress (215★, 1.5.1, GPL-2.0) is the minimal end of the spectrum: a blogging engine that stores everything in files, requires no database, and is documented in one sentence — download, unzip, upload, run the installer. It supports PHP 7.2 through 8.5, which is the widest compatibility window of the four and makes it the safest bet on locked-down shared hosting.

```bash
# 1. Download the latest FlatPress package from flatpress.org/download
# 2. Unzip it into your web root
unzip flatpress.zip -d /var/www/html/blog

# 3. Ensure the content directory is writable by the web server
chmod -R 755 /var/www/html/blog/fp-content

# 4. Open the site in a browser and complete the built-in installer
```

Themes are powered by Smarty and the plugin system is unusually capable for a project this small, with a widget layer for sidebars. FlatPress also runs its own PHPStan and CodeQL checks on every change, which is more quality tooling than most projects three times its size. If you have ever wanted a blog whose entire state is one directory you can `rsync` to a new host in seconds, this is it.

![FlatPress default theme front end](/img/screenshots/fp-preview.jpg "FlatPress default Leggero theme preview")

## Deployment: Running a Flat-File CMS in Docker

Because none of these need a database, the container story is refreshingly boring. A single PHP image plus a bind mount is a complete deployment. Here is a minimal Compose file for FlatPress:

```yaml
services:
  flatpress:
    image: php:8.3-apache
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./flatpress:/var/www/html
    environment:
      - TZ=UTC
```

Point your reverse proxy at port 8080 and you are done. Two adjustments matter in practice:

1. **Match the PHP version to the CMS.** FlatPress 1.5.1 accepts PHP 7.2–8.5, so `php:8.3-apache` is safe. PluXML caps out at 8.1.2, so use `php:8.1-apache` for it. Running PluXML on an 8.3 image produces runtime warnings you cannot simply ignore.
2. **Statamic and Kirby need more than a web server.** Both are installed with Composer, so either build a multi-stage image that runs `composer install` during the build, or install locally and ship the resulting directory into the container.

For a wider look at how these fit alongside static output, see our [self-hosted static site generator comparison](../self-hosted-static-site-generators-hugo-jekyll-astro-eleventy-guide/).

## Common Pitfalls and Migration Traps

**Do not migrate from a database CMS expecting an export button.** There is no SQL dump to import. WordPress-to-flat-file migrations need a converter script, and every flat-file CMS stores content in its own structure (Kirby's text files, PluXML's XML, FlatPress's serialised PHP). Budget real time for this, not an afternoon.

**Flat files have no transactions.** Two processes writing the same entry can corrupt it. This is fine for a single web server with normal editorial traffic, and a bad idea on a shared network filesystem where several nodes write the same directory. Keep writes local, back up with snapshots.

**Search degrades as the corpus grows.** Scanning every file per query is fast at 500 entries and painful at 50,000. If you expect a large archive, plan on generating an index or pushing search to an external service.

**Backups are simple, media is not.** Copying a folder is a great backup story — until that folder holds ten years of images. Separate your media from your content structure if you expect either to grow disproportionately.

**Version ceilings change silently.** PluXML's 8.1.2 ceiling and FlatPress's 8.5 ceiling are stated in their documentation today, but hosting panels upgrade PHP without asking. Pin the PHP version in your container and test upgrades deliberately.

If you already run a flat-file note system and like the model, our [flat-file Markdown notes comparison](../2026-05-23-self-hosted-flat-file-markdown-notes-flatnotes-dendron-hedgedoc/) covers the same trade-off for knowledge bases, and the [Grav vs Pico vs Bludit breakdown](../2026-04-23-grav-vs-pico-vs-bludit-flat-file-cms-guide-2026/) covers three more flat-file CMS options that fill the gap between these four.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Flat-File CMS Comparison 2026: Statamic vs Kirby vs PluXML vs FlatPress",
  "description": "Four flat-file CMS platforms compared for 2026: Statamic, Kirby, PluXML and FlatPress. Real install commands, licence costs, PHP limits and Docker deployment.",
  "datePublished": "2026-10-03",
  "dateModified": "2026-10-03",
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

**Do any of these flat-file CMS platforms need a database?**
No. All four — Statamic, Kirby, PluXML and FlatPress — store content in files on disk rather than in MySQL, PostgreSQL or SQLite. That removes an entire service from your stack: no database to patch, no SQL dump in your backup routine, and no connection pool to tune. The trade-off is that you lose database transactions when several writers touch the same content directory.

**Is Statamic free to use?**
Statamic has a free tier that covers local development and solo projects, but it is not OSI open source. Production and client work require a Pro licence. If your budget for software licences is exactly zero, choose one of the two GPL options instead: PluXML (GPL-3.0) or FlatPress (GPL-2.0).

**Which flat-file CMS is best for a small VPS or shared host?**
FlatPress is the safest choice because of its PHP compatibility window (7.2 through 8.5) and its no-Composer install. PluXML is equally light but caps out at PHP 8.1.2, so check your host's PHP version first — this single constraint disqualifies it on many current shared plans.

**Can I run a flat-file CMS in Docker?**
Yes, and it is simpler than a database-backed CMS. A single `php:8.3-apache` container with a bind mount for the site directory is a complete deployment. The only rule is to match the PHP version to the CMS: use `php:8.1-apache` for PluXML, and build a Composer stage for Statamic or Kirby.

**How many entries can a flat-file CMS handle before performance suffers?**
For a blog, effectively unbounded — thousands of entries are fine because each request only reads the files it needs. The pressure point is full-text search, which typically scans every file. Past roughly ten thousand entries you should generate an index or delegate search to an external service rather than scan the directory per query.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
