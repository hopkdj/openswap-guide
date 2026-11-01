---
title: "PHP Image Processing in 2026: Intervention Image vs Glide vs Imagine"
date: "2026-11-01"
tags: ["php", "image-processing", "performance", "web-development", "self-hosted"]
draft: false
---

Resize a 12-megapixel JPEG on every page view and your PHP-FPM worker spends **200–400 ms and roughly 40 MB of RAM per request** doing it. Ten concurrent visitors and you have allocated half a gigabyte to produce ten identical thumbnails. That is the moment you start caring about which PHP image library you picked — and by then it is usually welded into 40 controllers.

PHP has three mature options, and they are not interchangeable. **Intervention Image** is a full manipulation toolkit with a clean modern API. **Glide** is an on-demand HTTP image server built on top of Intervention. **Imagine** is the older, PIL-inspired object-oriented abstraction designed for driver portability. Picking the wrong layer is the expensive mistake; picking the wrong driver inside the right layer is the second most expensive.

## The 30-Second Verdict

**For an application that generates derivatives at upload time, use Intervention Image v4.** Its 2026 API is the most ergonomic of the three, it supports GD, Imagick, and libvips behind one interface, and the pipeline (`decodePath` → manipulate → `encodeUsingFormat`) maps directly onto queue jobs.

**For a site that serves user-uploaded images at arbitrary sizes, use Glide.** You point it at a source folder and a cache folder, it answers `?w=600&fit=crop&fm=webp` requests, caches the result, and sets far-future cache headers. No controller code, no cron job.

**Use Imagine only if you are maintaining an existing Imagine codebase.** It is not dead — 4,471 stars, releases through 2026 — but its API predates the modern PHP ecosystem, it has no first-party HTTP server, and every new project in 2026 has a better option.

The sharpest framing: **Glide is what you deploy as a service. Intervention is what you call from a job. Imagine is what you inherit.**

## Comparison Table

| Dimension | Intervention Image | Glide | Imagine |
|---|---|---|---|
| Latest version | 4.4.1 | 4.2.0 | 1.5.4 |
| GitHub stars | 14,379 | 2,629 | 4,471 |
| Last repo activity | 2026-10-30 | 2026-10-10 | 2026-06-04 |
| License | MIT | MIT | MIT |
| Primary role | Manipulation library | HTTP image server | OO abstraction layer |
| API style | Fluent, pipeline-based | URL query parameters | PIL-inspired OO |
| Drivers | GD / Imagick / libvips | GD / Imagick (via Intervention) | GD / Imagick / Gmagick |
| Built-in HTTP serving | No | Yes | No |
| Built-in derivative cache | No | Yes (filesystem or Flysystem) | No |
| PHP requirement | 8.3+ | 8.1+ | 7.1+ |
| Best fit | Upload pipelines, thumbnails | Media sites, CDN origin | Legacy maintenance |

The dependency relationship matters: **Glide 4 depends on Intervention Image 4** for decode, manipulate, and encode. You are not choosing between them — Glide is the HTTP wrapper, Intervention is the engine. Installing more than 14,000 stars' worth of battle testing comes free with the 2,600-star package.

## Decision Matrix

| Your situation | Choose | Why |
|---|---|---|
| WordPress-style media site, many sizes | Glide | URL-driven, cached, zero controller code |
| Upload → 4 derivatives in a queue job | Intervention Image | Explicit pipeline, easy to test |
| Need libvips for 50 MP images | Intervention Image | Only one of the three with a first-party vips driver |
| S3/R2 storage backend | Glide | Flysystem adapters are built in |
| Existing Imagine-based codebase | Imagine | Rewriting buys nothing unless you hit a limit |
| Image watermarking at request time | Glide | `watermarks` config + `mark`/`markpos` params |
| Drawing text and shapes for invoices | Imagine or Intervention | Both have full drawing APIs |
| Budget VPS, 1 GB RAM | Intervention + GD | Imagick's per-image memory footprint is larger |

## Intervention Image v4 — The Modern Toolkit

Install:

```bash
composer require intervention/image
```

Version 4 changed the instantiation API. Every pre-2025 tutorial you find will show `new ImageManager(new Driver())` from v3 and `Image::make()` from v2 — both are gone. The current form is a static factory:

```php
use Intervention\Image\ImageManager;
use Intervention\Image\Drivers\Gd\Driver as GdDriver;
use Intervention\Image\Format;
use Intervention\Image\Alignment;

$manager = ImageManager::usingDriver(GdDriver::class);

$image = $manager->decodePath('uploads/hero.jpg');

$image->scale(width: 1200);                     // proportional, keeps ratio
$image->insert('assets/watermark.png', alignment: Alignment::BOTTOM_RIGHT);

$encoded = $image->encodeUsingFormat(Format::JPEG, quality: 82);
$encoded->save('public/img/hero-1200.jpg');
```

Four things worth internalising:

1. **`decodePath()` reads, `encodeUsingFormat()` writes.** You cannot `save()` an unencoded image directly in v4 — encoding is an explicit step, which is good: it forces you to decide format and quality rather than silently inheriting the source's.
2. **`scale()` preserves aspect ratio; `resize()` does not.** Using `resize(width: 600, height: 600)` on a 3:2 photo produces a distorted image. Use `scale()` for one dimension, or `cover()`/`contain()` when you need exact dimensions.
3. **Driver choice is a real performance decision.** Swap `GdDriver` for `ImagickDriver` or the libvips driver without changing a single call site:

```php
use Intervention\Image\Drivers\Imagick\Driver as ImagickDriver;

$manager = ImageManager::usingDriver(ImagickDriver::class);
```

GD is bundled with most PHP builds and uses moderate memory but poor resampling quality on large downscales. Imagick produces visibly better Lanczos output and handles CMYK/ICC profiles, at roughly **2–3× the memory** for the same source image. libvips is the outlier: it streams and tiles, so a 50 MP source stays near-constant in memory. For a server that processes 100k images a day, libvips is not a luxury.

4. **Animated formats need explicit care.** `decodePath('animation.gif')` gives you a multi-frame image in v4; encoding back to GIF preserves frames, but converting an animated GIF to JPEG silently keeps only the first frame. If your pipeline accepts GIF/WebP uploads, branch on `$image->isAnimated()` before choosing an output format.

The library also ships a real `docker-compose.yml` in its repo — though be warned, it is a **test harness**, not a deployment recipe: four services (`tests`, `coverage`, `analysis`, `standards`) that all run PHPUnit, PHPStan, or PHPCS against the mounted source. Useful if you contribute upstream; useless for production.

## Glide — Serving Images Over HTTP

Install and configure:

```bash
composer require league/glide
```

```php
use League\Glide\ServerFactory;

$server = ServerFactory::create([
    'source'        => '/var/www/media/source',
    'cache'         => '/var/www/media/cache',
    'driver'        => 'gd',              // or 'imagick'
    'defaults'      => ['q' => 82, 'fm' => 'webp'],
    'presets'       => [
        'thumb' => ['w' => 200, 'h' => 200, 'fit' => 'crop'],
        'hero'  => ['w' => 1600, 'q' => 85, 'fm' => 'jpg'],
    ],
    'watermarks'    => '/var/www/media/watermarks',
    'cache_with_file_extensions' => true,
]);

// In your front controller:
$server->outputImage(
    $_GET['path'],
    ['w' => 600, 'fit' => 'crop', 'fm' => 'webp']
);
```

The request `GET /img/photo.jpg?w=600&fit=crop&fm=webp` becomes a cached file. Parameters Glide understands out of the box: `w`, `h`, `fit` (`contain`, `max`, `fill`, `stretch`, `crop`), `crop`, `fm` (`jpg`, `png`, `gif`, `webp`, `avif`), `q`, `dpr`, `bg`, `blur`, `bri`, `con`, `gam`, `sharp`, `flip`, `or` (orientation), `mark` and `markpos` for watermarks.

Two integration details that consume an afternoon if you miss them:

**Front controller versus direct file serving.** If nginx serves `/media/` directly, Glide never runs. You need a rewrite so image paths hit PHP:

```nginx
location /img/ {
    try_files $uri /index.php?$query_string;
}
```

**Cache invalidation.** Glide caches by path plus parameter hash under `cache/`. Change a preset and old derivatives keep serving — you must purge the cache directory (or version the URL: `/img/v2/photo.jpg`). There is no built-in purge endpoint, which is a deliberate design choice and a frequent surprise after a design refresh.

**Security note that is not optional:** `$_GET['path']` must be validated. Glide's `Server` normalises the path, but a naive front controller that concatenates user input into a filesystem path is one `../` away from serving arbitrary files. Use `$server->getSourcePath()` only through the server object, and never pass unvalidated absolute paths.

For a fully containerised image service, this is the pattern that works in practice:

```yaml
services:
  img:
    image: php:8.4-fpm-alpine
    working_dir: /app
    volumes:
      - ./app:/app
      - ./media:/var/www/media
    environment:
      - PHP_MEMORY_LIMIT=512M
    command: >
      sh -c "docker-php-ext-install gd exif &&
             php-fpm"
```

Then put nginx in front with the `try_files` rewrite above. Image processing is CPU-bound, so cap PHP-FPM workers to your core count — six workers on a four-core box simply adds context switching.

## Imagine — The Portable Abstraction

Imagine's pitch is driver portability: the same code runs on GD, Imagick, or Gmagick. That mattered enormously in 2011 and barely matters now, but the API is clean and the library is still released:

```bash
composer require imagine/imagine
```

```php
use Imagine\Gd\Imagine;
use Imagine\Image\Box;
use Imagine\Image\Point;
use Imagine\Image\ImageInterface;

$imagine = new Imagine();

$image = $imagine->open('uploads/hero.jpg');

$image->resize(new Box(1200, 800))
      ->crop(new Point(0, 0), new Box(1200, 630))
      ->save('public/img/hero-crop.jpg', ['jpeg_quality' => 82]);

// Thumbnail preserving aspect ratio
$image->thumbnail(new Box(400, 400), ImageInterface::THUMBNAIL_INSET)
      ->save('public/img/hero-thumb.jpg');
```

The pieces you will actually use: `Box` for dimensions, `Point` for coordinates, `ImageInterface::THUMBNAIL_INSET` (fit inside) versus `THUMBNAIL_OUTBOUND` (fill and crop), and the drawing API for text overlays.

```php
$font = $imagine->font('assets/Inter-Bold.ttf', 32, $imagine->palette()->color('#ffffff'));
$image->draw()->text('2026', $font, new Point(40, 40));
```

Where Imagine genuinely still wins: `RelativeResize` filters (scale by percentage or by one dimension without computing the other), and a drawing API that is slightly more intuitive than Intervention's for multi-element compositions. Where it loses: no official HTTP server, no cache layer, no libvips driver, and a PHP 7.1 floor that means the codebase carries compatibility shims you will never use.

## Real Pitfalls That Cost Real Money

**1. `memory_limit` is the top cause of silent image failures.** GD holds decoded pixels in memory: a 4000×3000 image is 4000 × 3000 × 4 bytes ≈ 48 MB decoded, regardless of the 3 MB JPEG on disk. Resize ten in a loop without `imagedestroy`/unsetting and a 128 MB limit dies at image three with "Allowed memory size exhausted" in a log nobody reads. Set `memory_limit = 512M` for the image worker, not the whole FPM pool.

**2. EXIF orientation.** A phone photo shot in portrait often stores landscape pixels plus an orientation flag. You resize it, and the thumbnail is sideways. Intervention v4 and Imagick honour orientation when the `exif` extension is loaded; GD-based paths need an explicit `->orient()` or `autoOrient()`. Load `exif`, call orientation, then resize — in that order.

**3. Resizing before cropping wastes CPU.** Always crop to the target aspect ratio first when the final output is a thumbnail. Decoding a 12 MP image to produce a 200×200 avatar is unavoidable, but running three separate resize passes is not: do one `cover()` with the final dimensions.

**4. Serving originals through PHP.** The most common Glide misconfiguration is routing every image through PHP "for consistency." Static originals should be served by nginx directly; only derivative URLs belong to Glide. Otherwise you pay PHP-FPM startup for bytes that needed no processing.

**5. WebP/AVIF encoding availability.** `fm=webp` returns a 500 if your GD build lacks WebP support. Check with `gd_info()` before deploying, and prefer building the container image from `php:8.4-fpm` with `docker-php-ext-install gd` rather than trusting a distro package's compile flags.

**6. Filename collisions in cache.** Two source images named `photo.jpg` in different folders with `group_cache_in_folders` disabled collide. Leave it enabled (the default) or use `cache_path_callable` to hash the full source path.

## Migration Notes

**v3 → v4 of Intervention Image** is the migration you are most likely to face. The breaking changes: `new ImageManager($driver)` becomes `ImageManager::usingDriver($driverClass)`, `read()`/`make()` becomes `decodePath()`/`decodeBinary()`, `encode()`/`save()` split into `encodeUsingFormat()` plus `save()`, and `->fit()`, `->widen()` are replaced by `scale`/`cover`/`contain`. Do it with tests, not by find-and-replace — the subtle ones are dimension semantics, where `resize(w,h)` with only one argument changed behaviour between majors.

**Glide 3 → 4** moved to Intervention 4 and Flysystem 3. The `driver` config now accepts `'gd'`/`'imagick'` strings, and custom manipulators must implement the new interfaces. Cache keys change, so plan a cache purge as part of the deploy.

**From Imagine to Intervention** is worth it only if you need libvips or a maintained HTTP layer. The APIs are close enough that a 500-line image service converts in an afternoon.

If you are also tuning the request path around your image service, our [PHP HTTP clients comparison](../2026-07-13-php-http-clients-guzzle-saloon-httpful/) covers the outbound side (fetching remote images), the [PHP ORM comparison](../2026-07-06-php-orm-libraries-laravel-eloquent-doctrine-propel/) covers storing image metadata, and the [PHP session management guide](../2026-07-05-php-session-management-native-symfony-laravel/) covers the upload flow that feeds all of this. Readers working in a Node.js stack should see our [sharp vs image-rs vs Jimp comparison](../2026-06-20-self-hosted-image-processing-libraries-sharp-image-rs-jimp/) — the same architecture questions, different runtime.

## FAQ

**Which is fastest: GD, Imagick, or libvips?**
libvips is fastest and lowest-memory on large images because it streams tiles instead of decoding everything into RAM. Imagick produces better quality and handles colour profiles properly. GD is the most available and usually fast enough for thumbnails under 2 MP. Benchmark with your own source images — the ranking flips depending on image size and operation.

**Can I use Glide without Intervention Image?**
Not in Glide 4. `ServerFactory` imports `Intervention\Image\ImageManager` directly and uses it for decoding, manipulation, and encoding. Glide is a routing, caching, and parameter-parsing layer over Intervention.

**Does Intervention Image v4 still support PHP 7?**
No. v4 requires PHP 8.3 or newer. If you are stuck on PHP 7.4, you need v2 or v3, which are in maintenance rather than active development.

**How do I generate WebP or AVIF derivatives?**
In Intervention, `encodeUsingFormat(Format::WEBP, quality: 80)`. In Glide, add `fm=webp` or `fm=avif` to the URL. Both require the underlying extension to be compiled with support — verify with `gd_info()` or `Imagick::queryFormats('AVIF')` before shipping.

**Is a dedicated image service worth it for a small site?**
Usually not. Under roughly 10,000 images and a few hundred daily requests, an upload-time job that writes three sizes to disk beats operating Glide plus nginx plus a cache purge process. Add Glide when you need arbitrary sizes, responsive `srcset` with many breakpoints, or multiple storage backends.

**What about image optimisation after resizing?**
Resizing is not compression. Run derivatives through `pngquant`/`jpegoptim` or encode to AVIF at quality 50–60 for a further 30–60% size reduction. Do it in the same job, not at request time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP Image Processing in 2026: Intervention Image vs Glide vs Imagine",
  "description": "Intervention Image v4, Glide, and Imagine compared for PHP image processing: real code, driver benchmarks, deployment configs, and memory pitfalls.",
  "datePublished": "2026-11-01",
  "dateModified": "2026-11-01",
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
