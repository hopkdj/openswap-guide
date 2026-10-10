---
title: "ExifTool vs Exiv2 vs metadata-extractor in 2026: Which Metadata Library Should You Actually Use?"
date: "2026-10-11"
tags: ["metadata", "image-processing", "developer-tools", "privacy", "libraries"]
draft: false
cover: "/img/screenshots/exiftool-overview.jpg"
---

Every photo you publish is a dossier. A single JPEG straight out of a phone camera can carry the exact GPS coordinates of your home, the serial number of the device that took it, a timestamp to the second, and sometimes the name of the software that edited it last. Photojournalists have been doxxed this way. So have activists, landlords, and anyone who posted a "for sale" listing shot in their own living room. **Metadata is not an edge case — it is the default.**

The practical question is not *whether* to handle EXIF, IPTC, and XMP metadata, but which library to build that handling on. There are four serious contenders in 2026: **ExifTool** (Perl), **Exiv2** (C++), **metadata-extractor** (Java), and the lightweight scripting pair **Piexif** (Python) and **exifr** (JavaScript). They are wildly different tools that get compared as if they were interchangeable. They are not.

## The 30-Second Verdict

- **You need to read *and* write metadata across 200+ file formats from a shell or script:** use **ExifTool**. Nothing else comes close on format coverage.
- **You are shipping a compiled application that embeds metadata handling:** link against **Exiv2**. It gives you a real API, predictable memory behaviour, and no interpreter dependency.
- **You run a JVM service that ingests uploads and needs metadata for indexing:** use **metadata-extractor**. It is read-only, which is often exactly what a server wants.
- **You need a five-line privacy strip inside an existing Python or Node app:** use **Piexif** or **exifr** — and accept their narrower format support.

If you only remember one sentence: *ExifTool is the widest, Exiv2 is the embeddable one, metadata-extractor is the safe JVM reader, and the scripting libraries are convenience wrappers you should treat as such.*

## Quick Comparison: The Five Contenders in 2026

All repository statistics below were pulled live from GitHub at publish time.

| Project | Language | Stars | Last commit | Read / Write | Format coverage | License |
|---|---|---|---|---|---|---|
| **ExifTool** | Perl | 5,142 | May 2026 | read + write | 200+ file types (images, video, audio, PDF) | GPL-1.0+ / Artistic |
| **Exiv2** | C++ | 1,166 | Oct 2026 | read + write | JPEG, TIFF, PNG, WebP, CR2/NEF/ARW and other RAW | GPL-2.0 |
| **metadata-extractor** | Java | 2,834 | Jul 2026 | read-only | JPEG, TIFF, PNG, WebP, HEIF, MP4, MOV, MP3, AVI | Apache-2.0 |
| **Piexif** | Python | 391 | Nov 2023 | read + write | JPEG, WebP | MIT |
| **exifr** | JavaScript / TypeScript | 1,250 | Mar 2024 | read-only | JPEG, HEIC, PNG, TIFF, AVIF | MIT |

Two numbers deserve a warning label. **Piexif and exifr have not had a commit since 2023 and 2024 respectively.** That does not make them unusable — they parse a frozen, well-specified binary format — but it does mean HEIC support will not magically appear, and a parser bug in a stale dependency is your problem. Treat them as convenience layers, not infrastructure.

## Decision Matrix: Pick by Use Case

| Your situation | Pick | Why |
|---|---|---|
| Media library cleanup, batch renames, EXIF stripping in CI | **ExifTool** | One binary handles every format you will ever meet; scriptable JSON/CSV output |
| Native desktop app or embedded device | **Exiv2** | Compiles into your binary; no Perl runtime on the target |
| Photo-sharing backend on the JVM | **metadata-extractor** | Fast, pure Java, Apache-2.0, safe to run on untrusted uploads |
| Django/Flask upload endpoint | **Piexif** | Two functions inline; no subprocess per image |
| Node upload pipeline on serverless | **exifr** | Zero-dependency ESM, works on partial buffers from S3 streams |
| Forensic/archival metadata audit | **ExifTool** | Prints unknown tags, maker notes, and vendor-specific blocks nobody else parses |

## ExifTool — The Undisputed Heavyweight

ExifTool, written and maintained for over two decades by Phil Harvey, reads and writes metadata in **more than 200 file formats**, including nasty vendor-specific maker notes that no other tool bothers with. It is a single Perl program, which is both its strength (portable, no compile step) and its weakness (startup cost in hot loops).

Install it from your distribution, never from a random binary:

```bash
# Debian / Ubuntu — the package ships the full tag database
sudo apt install libimage-exiftool-perl

# macOS
brew install exiftool

# Verify
exiftool -ver
```

Reading a photo's location and device data, in machine-readable form:

```bash
exiftool -json -GPSLatitude -GPSLongitude -Make -Model -DateTimeOriginal photo.jpg
```

Stripping *everything* — EXIF, IPTC, XMP, ICC, and the thumbnail — before publishing:

```bash
# -overwrite_original prevents the automatic photo.jpg_original backup file
exiftool -all= -overwrite_original photo.jpg
```

Renaming an entire shoot from the capture timestamp, with a counter for burst frames:

```bash
exiftool '-FileName<DateTimeOriginal' -d %Y-%m-%d_%H-%M-%S%%-c.%%e -r ./shoot-dir
```

When you process thousands of files, Perl's interpreter startup dominates. ExifTool ships an explicit remedy: **stay-open mode**, where one process reads commands from an argument file instead of being respawned per image.

```bash
exiftool -stay_open True -@ /tmp/exiftool-args
# each line in the file is an argument; -execute between commands
```

The `-all=` operator is the one to remember for privacy work. It removes metadata across families at once, which matters because GPS coordinates can live in three different places (Exif, IPTC, and XMP) and stripping only one of them leaves you exposed.

## Exiv2 — The C++ Library You Embed

Exiv2 is what you reach for when metadata handling is a *feature of your product*, not a shell step. It is a C++ library with a small command-line frontend attached, and it is the only serious option here for native applications that cannot ship a Perl interpreter.

![Exiv2 component architecture](/img/screenshots/exiv2-architecture.jpg "Exiv2 architecture: image I/O, metadata parsers, and the conversion layer")

Installing development headers:

```bash
sudo apt install exiv2 libexiv2-dev
# or from source, which is what most integrators do for a pinned version
```

The CLI is terse but effective — `-pa` prints *all* metadata, `-d` deletes:

```bash
# Print every tag Exiv2 knows about
exiv2 -pa photo.jpg

# Delete all metadata (Exif + IPTC + XMP + comments)
exiv2 -d a photo.jpg

# Write a single tag instead of nuking the file
exiv2 -M"set Exif.Image.ImageDescription Exported by our pipeline" photo.jpg
```

Inside a C++ application the API is a clean factory pattern. Since Exiv2 0.28 the factory returns a `UniquePtr`, which finally made the library behave like modern C++:

```cpp
#include <exiv2/exiv2.hpp>
#include <iostream>

int main() {
    auto image = Exiv2::ImageFactory::open("photo.jpg");
    image->readMetadata();

    Exiv2::ExifData& exif = image->exifData();
    auto lat = exif.findKey(Exiv2::ExifKey("Exif.GPSInfo.GPSLatitude"));
    if (lat != exif.end()) {
        std::cout << "GPS: " << lat->print(&exif) << std::endl;
    }

    // Strip everything, then write back
    exif.clear();
    image->writeMetadata();
    return 0;
}
```

The honest trade-off: Exiv2 supports a narrower format set than ExifTool (it does not chase every obscure audio container) and its RAW support is the real reason people adopt it — CR2, NEF, ARW, and friends are first-class, not afterthoughts.

## metadata-extractor — The JVM Standard

For JVM backends, `metadata-extractor` by Drew Noakes is the safe default. It is **read-only by design**, pure Java, Apache-2.0 licensed, and it will happily walk directories of JPEG, TIFF, WebP, HEIF, MP4, MOV, MP3, and AVI metadata without shelling out to anything. Read-only is not a limitation for a server that must extract indexing attributes from an upload; it is a security posture.

```gradle
// build.gradle.kts
dependencies {
    implementation("com.drewnoakes:metadata-extractor:2.19.0")
}
```

```java
import com.drew.imaging.ImageMetadataReader;
import com.drew.metadata.Metadata;
import com.drew.metadata.Directory;
import java.io.File;

Metadata metadata = ImageMetadataReader.readMetadata(new File("photo.jpg"));

for (Directory directory : metadata.getDirectories()) {
    directory.getTags().forEach(tag ->
        System.out.println(directory.getName() + " / " + tag.getTagName() + " = " + tag.getDescription())
    );
}
```

Two practical details matter in production. First, `ImageMetadataReader` **fully decodes metadata but never pixel data**, so it is cheap relative to image decoding — you can run it synchronously on upload without a worker pool. Second, because it cannot write, your privacy strip must happen elsewhere: many teams extract with metadata-extractor and sanitize with a separate re-encode step (or with ExifTool in a sidecar job).

## Piexif and exifr — The Lightweight Scripting Paths

Piexif is the Python answer for the 95% case: JPEG and WebP, load the dictionary, mutate it, save it.

```python
import piexif

exif_dict = piexif.load("photo.jpg")
gps = exif_dict.get("GPS", {})
print("Has GPS:", bool(gps))

# Remove all metadata and write a clean file
piexif.remove("photo.jpg")          # returns a sanitized JPEG stream/file
```

exifr is the JavaScript equivalent, and it is genuinely well engineered for streaming backends — it can parse from a partial buffer, so you do not need the whole upload on disk before reading metadata.

```javascript
import exifr from 'exifr';

const file = await fetch(uploadUrl).then(r => r.arrayBuffer());
const { latitude, longitude } = await exifr.gps(file);
const make = await exifr.parse(file, ['Make', 'Model', 'DateTimeOriginal']);
```

Both libraries fail in the same place: **format edges**. HEIC from modern phones, iPhone Live Photos, and stacked RAW+JPEG pairs are where they hand you nothing. If your input is "whatever users upload", you are choosing between ExifTool's breadth and writing your own fallback chain.

## Metadata Hygiene as a Privacy Control (And Why Self-Hosting Helps)

Metadata handling is one of those chores that quietly becomes a compliance requirement. Under GDPR-style regimes, a photo of an identifiable person that carries precise location data is personal data, and "we stripped it with a library we never audited" is not a defence. If your media pipeline runs on someone else's infrastructure, you are also trusting that provider's logging, thumbnailing, and transcoding steps not to reintroduce coordinates or hand the original to a third party.

Running the sanitization step yourself is genuinely cheaper than it sounds. All five libraries here are self-hostable by definition — they are libraries, not services — and the pipeline around them is a few dozen lines. Pair a sanitizer with a self-hosted image processing layer and you control the whole chain from upload to CDN. Our guide to [image optimization libraries](../2026-06-20-image-optimization-libraries-libvips-sharp-imagemagick-pillow/) covers the re-encoding half of that pipeline, and if your sanitizer needs to know what a file actually *is* before touching it, the [mime type detection libraries comparison](../2026-06-21-mime-type-detection-libraries-libmagic-apache-tika-file-type/) is the companion piece — trusting a user-supplied `Content-Type` header is how you end up passing a malicious payload to a parser.

The rule to internalise: **sanitize on ingest, verify on egress.** Run the strip when the file arrives (so the original never persists), then assert on publish that no GPS tags survive. A five-line assertion in CI catches the day someone adds a new upload path that skips the sanitizer.

## Common Pitfalls and Migration Notes

**1. ExifTool keeps backups by default.** Every write produces `photo.jpg_original`. In a batch job that silently doubles your storage and leaves the *unstripped* copy behind — which is precisely the file a leak would expose. Always pass `-overwrite_original` when sanitizing.

**2. Exiv2's `-d a` is not reversible.** There is no undo and no backup. Test on a copy, and prefer targeted group deletes (`-d e`, `-d i`, `-d x`) if you want to keep colour profiles or IPTC captions.

**3. metadata-extractor cannot strip anything.** Teams migrate to it expecting a full replacement for ExifTool and discover at review time that their "sanitizer" only ever read data. Plan for an explicit second step.

**4. GPS lives in multiple families.** Exif GPS tags, IPTC location fields, and XMP `exif:GPSLatitude` are independent. Removing only the Exif block feels safe and is not.

**5. Orientation tags are load-bearing.** `Exif.Image.Orientation` tells viewers how to rotate the image. Strip it *and* re-encode pixels, or your "sanitized" photo appears rotated in every viewer that respected the original tag. ExifTool's `-Orientation` handling and any re-encode step need to agree.

**6. Perl startup cost in hot loops.** Budget ~50–100 ms per ExifTool invocation. At 10,000 images that is a quarter of an hour of pure interpreter startup — use `-stay_open` or batch with an argument file.

**7. Stale scripting libraries.** Pin Piexif and exifr, and add a fallback to ExifTool for HEIC and RAW. A silent `undefined` from a JS parser on an iPhone photo is worse than a crash, because it looks like "no GPS data" and gets shipped.

## FAQ

**Which metadata library should I use by default?**
Start with ExifTool if you can shell out, and Exiv2 if you are writing a native application. ExifTool wins on format coverage and write support; Exiv2 wins on embeddability and RAW handling. For JVM services that only need to *read* metadata, metadata-extractor is the cleanest choice.

**Can I use these libraries to remove GPS data from photos automatically?**
Yes. `exiftool -all= -overwrite_original photo.jpg` removes Exif, IPTC, XMP, ICC profile, and the embedded thumbnail in one pass. In Python, `piexif.remove("photo.jpg")` does the same for JPEG and WebP files. Always verify afterwards with a read pass, because a single surviving tag can carry a location.

**Is metadata-extractor a drop-in replacement for ExifTool?**
No. It is read-only. It extracts metadata from images, video, and audio on the JVM, which is ideal for indexing and validation, but it cannot write or strip tags. Use it for extraction and pair it with ExifTool or Exiv2 for sanitization.

**Why does my sanitized photo show up rotated after stripping metadata?**
Because you removed the orientation tag without rotating the pixels. Stripping metadata is a two-part operation: either bake the rotation in during re-encode, or preserve `Exif.Image.Orientation`. Most "my image is sideways" bugs trace back to this.

**Do I need Docker to run any of these?**
No. All five are libraries or single binaries that install via the distribution package manager, Homebrew, pip, npm, Maven, or a compiler. Containerising them is useful for reproducible CI sanitization jobs, but nothing here requires a service to run.

**How large is the risk of stale dependencies like Piexif or exifr?**
Moderate and specific: parsing logic for a frozen format is stable, so lack of commits is not itself dangerous. The real exposure is format support — HEIC, AVIF, and vendor RAW files will not be added — plus any unpatched parser vulnerability. Keep them behind a fallback.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ExifTool vs Exiv2 vs metadata-extractor in 2026: Which Metadata Library Should You Actually Use?",
  "description": "Hands-on comparison of the five main image metadata libraries in 2026: ExifTool, Exiv2, metadata-extractor, Piexif and exifr. Covers EXIF/IPTC/XMP read and write support, format coverage, code examples, GPS stripping and privacy pitfalls.",
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
