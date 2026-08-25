---
title: "Java Barcode Libraries in 2026: ZXing vs OkapiBarcode vs Barcode4j — Which One Should You Use?"
cover: "/img/screenshots/okapi-cover.jpg"
date: "2026-08-26"
tags: ["java", "barcode", "qr-code", "library-comparison", "java-libraries"]
draft: false
---

The most widely used Java barcode library on the planet is in **maintenance mode** — its README now literally says the project has "no active development or roadmap" and its Android scanner app "does not work with Android 14 and will not be updated." If your logistics, POS, or inventory system depends on ZXing, that sentence should make you pause. Barcode generation looks like a solved problem until the library you built your warehouse label pipeline on stops evolving. This guide compares **ZXing**, **OkapiBarcode**, and **Barcode4j** with live repository data and real code, so you know what is actually safe to build on in 2026.

## TL;DR / Quick Verdict

- **Scanning + QR generation in one dependency** → **ZXing** (34,077 stars). Still the de facto standard for *reading* barcodes and generating QR codes, and the only one of the three with real scanning capability — but it is in maintenance mode, so treat it as a frozen, stable dependency, not a platform.
- **Pure generation with the widest symbology coverage** → **OkapiBarcode** (396 stars). 60+ barcode types including postal, GS1, and Swiss QR formats, with Java2D, SVG, and PostScript renderers. Actively maintained and cleanly licensed (Apache-2.0).
- **Classic 1D barcode library, revived** → **Barcode4j** (33 stars on the maintained fork). The old SourceForge workhorse is now maintained as a fork on GitHub with 2.4.0 releases, a drop-in migration path from the legacy `net.sf.barcode4j` artifacts, and XML/FOP integration.
- **Recommendation:** keep ZXing for decoding; generate new 1D barcodes with OkapiBarcode (or Barcode4j if you need FOP/XML workflows). Do not start a new project that *depends on ZXing's evolution* — there won't be any.

## Quick Comparison Table

| Criterion | ZXing | OkapiBarcode | Barcode4j (fork) |
|---|---|---|---|
| GitHub stars | 34,077 | 396 | 33 |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Last push | 2026-08-24 | 2026-06-05 | 2026-08-13 |
| Primary role | Decoding + QR/Data Matrix generation | 1D/2D barcode generation | 1D barcode generation |
| Scanning/decoding | ✅ (core strength) | ❌ | ❌ |
| 1D symbologies (Code 128, EAN, UPC...) | Limited (via 2D-focused core) | 60+ (extensive) | 20+ (Code 128, EAN, UPC, ITF...) |
| 2D symbologies (QR, Data Matrix, Aztec) | ✅ QR/Data Matrix/Aztec | ✅ QR, Data Matrix, Aztec, more | ⚠️ QR via 2.4.0+ (Aztec added) |
| Output formats | Image (via javase module) | PNG/JPEG (Java2D), SVG, PostScript | PNG/JPEG/SVG/PDF (FOP), EPS |
| Maven coordinates | com.google.zxing:core / javase | uk.org.okapibarcode:okapibarcode | com.singingbush:barcode4j |
| Android support | ✅ (core is Android-friendly) | ❌ (pure JavaSE) | ❌ |
| Maintenance status | **Maintenance mode (frozen)** | Active (2026-06) | Active fork (2026-08) |

## Use Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Scanning barcodes/QR from camera or images | **ZXing** | The only real decoding engine of the three; 34k stars of battle-testing |
| Generating Code 128 / EAN / UPC for labels | **OkapiBarcode** | Widest 1D coverage, clean API, active maintenance |
| Printing labels to PDF via FOP/Apache XML graphics | **Barcode4j** | Built-in FOP extension; XML-defined barcode config |
| Swiss QR / postal / GS1 specialized barcodes | **OkapiBarcode** | Swiss QR, Royal Mail, USPS OneCode, GS1 Composite all built in |
| New Android app needing QR generation | **ZXing core (generation only)** | Decoding is frozen on Android 14+; generation via core still works |
| Enterprise label service behind a REST API | **OkapiBarcode** | SVG output + pure Java = trivially served, no native deps |

## ZXing — The Standard You Can No Longer Rely On

ZXing ("Zebra Crossing") is a multi-format 1D/2D barcode image processing library originally from Google, and with **34,077 stars** it is by far the most popular Java barcode project. Its real strength is **decoding**: the `core` module can read QR codes, Data Matrix, Aztec, PDF 417, and a range of 1D formats from images or camera frames, and it is the engine behind countless scanner apps and server-side decoding pipelines.

But the README's status is unambiguous: *"The project is in maintenance mode... Only bug fixes and minor enhancements will be considered. The Barcode Scanner app can no longer be published... It does not work with Android 14 and will not be updated. There is otherwise no active development or roadmap for this project."* That last push on 2026-08-24 notwithstanding, the project is frozen by design — great if you want stability, dangerous if you are building a new Android scanning product or expecting fixes for modern camera/OS quirks.

For **QR generation**, ZXing's `core` + `javase` modules remain the fastest path, and the API is stable:

```java
// ZXing core + javase — QR code generation
import com.google.zxing.BarcodeFormat;
import com.google.zxing.EncodeHintType;
import com.google.zxing.WriterException;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel;
import com.google.zxing.client.j2se.MatrixToImageWriter;

import java.nio.file.Paths;
import java.util.EnumMap;
import java.util.Map;

Map<EncodeHintType, Object> hints = new EnumMap<>(EncodeHintType.class);
hints.put(EncodeHintType.ERROR_CORRECTION, ErrorCorrectionLevel.M);
hints.put(EncodeHintType.CHARACTER_SET, "UTF-8");

QRCodeWriter writer = new QRCodeWriter();
BitMatrix matrix = writer.encode("https://example.com/track/12345",
        BarcodeFormat.QR_CODE, 300, 300, hints);

MatrixToImageWriter.writeToPath(matrix, "PNG", Paths.get("qrcode.png"));
```

Maven:

```xml
<dependency>
  <groupId>com.google.zxing</groupId>
  <artifactId>core</artifactId>
  <version>3.5.3</version>
</dependency>
<dependency>
  <groupId>com.google.zxing</groupId>
  <artifactId>javase</artifactId>
  <version>3.5.3</version>
</dependency>
```

The generation side (`QRCodeWriter`, `BitMatrix`, `MatrixToImageWriter`) is stable, well-tested, and unlikely to break — this is the part of ZXing you can still build on with confidence. The decoding side is the part to treat carefully: on Android specifically, the scanner app is dead on Android 14+, and while the `core` decoding APIs still work, don't expect fixes for new camera formats or hardware.

## OkapiBarcode — The Generation Specialist

OkapiBarcode is an open-source barcode *encoding* library focused on one job: turning strings into crisp barcode images across **60+ symbologies**. The GitHub repo (396 stars, Apache-2.0, last push 2026-06-05) lists an impressive taxonomy — Code 128/39/93, EAN/UPC, ITF-14, GS1 DataBar and Composite, Data Matrix, QR Code, Aztec, Swiss QR, postal formats (USPS OneCode, Royal Mail 4 State, POSTNET), and more.

The API follows a simple four-step pattern: instantiate the symbology class, customize settings, set content, and render. From the official README:

```java
// From the OkapiBarcode README
import uk.org.okapibarcode.backend.Code128;
import uk.org.okapibarcode.backend.HumanReadableLocation;
import uk.org.okapibarcode.output.Java2DRenderer;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;

Code128 barcode = new Code128();
barcode.setFontName("Monospaced");
barcode.setFontSize(16);
barcode.setModuleWidth(2);
barcode.setBarHeight(50);
barcode.setHumanReadableLocation(HumanReadableLocation.BOTTOM);
barcode.setContent("123456789");

int width = barcode.getWidth();
int height = barcode.getHeight();

BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_BYTE_GRAY);
Graphics2D g2d = image.createGraphics();
Java2DRenderer renderer = new Java2DRenderer(g2d, 1, Color.WHITE, Color.BLACK);
renderer.render(barcode);

ImageIO.write(image, "png", new File("code128.png"));
```

Maven:

```xml
<dependency>
  <groupId>uk.org.okapibarcode</groupId>
  <artifactId>okapibarcode</artifactId>
  <version>1.5.2</version>
</dependency>
```

What makes OkapiBarcode stand out is the **SVG and PostScript renderers** — you can generate vector labels that scale cleanly for print, which matters enormously in logistics (thermal printers and high-DPI label stock). The human-readable text placement, quiet-zone handling, and module-width control are all explicit, which gives you the control a label-printing pipeline needs. The trade-off: **no decoding** — this library generates only. Pair it with ZXing for scanning and you have a complete, actively-maintained stack.

## Barcode4j — The Classic, Resurrected

Barcode4j has been generating 1D barcodes for Java since the early 2000s, and its `net.sf.barcode4j` artifacts are still the answer on a thousand Stack Overflow threads. The original project on SourceForge went quiet, but a community fork — `SingingBush/barcode4j` (33 stars, Apache-2.0, last push 2026-08-13) — migrated the full SVN history to GitHub in 2020 and continues releasing: the current 2.4.0 adds **Aztec support**, removes the retired Avalon-Framework dependency, and adds GraalVM native-image compatibility.

Its distinguishing feature is the **FOP extension** (`barcode4j-fop-ext`): you can embed barcodes in Apache FOP/XML-FO documents, which makes it the natural choice when barcodes must appear inside PDFs generated with the classic FOP pipeline. It also supports XML-defined barcode configuration via XSD.

A minimal Code 128 generation:

```java
// Barcode4j 2.4.0 (fork coordinates)
import org.krysalis.barcode4j.impl.code128.Code128Bean;
import org.krysalis.barcode4j.output.bitmap.BitmapCanvasProvider;

import java.awt.image.BufferedImage;
import java.io.FileOutputStream;

Code128Bean barcode = new Code128Bean();
barcode.setHeight(15f);
barcode.setModuleWidth(0.3);
barcode.setQuietZone(10);

try (FileOutputStream out = new FileOutputStream("barcode.png")) {
    BitmapCanvasProvider canvas = new BitmapCanvasProvider(
            out, "image/png", 300, BufferedImage.TYPE_BYTE_BINARY, false, 0);
    barcode.generateBarcode(canvas, "123456789");
    canvas.finish();
}
```

Maven (note the fork coordinates — the legacy `net.sf.barcode4j:barcode4j:2.1` artifact is the old fat-jar):

```xml
<dependency>
  <groupId>com.singingbush</groupId>
  <artifactId>barcode4j</artifactId>
  <version>2.4.0</version>
</dependency>
```

The fork keeps the original `org.krysalis.barcode4j` package names, so migrating from the old SourceForge releases is mostly a dependency-coordinate swap. It is a solid choice if you already use FOP, or if your team's muscle memory lives in Barcode4j's `Bean` classes. Compared to OkapiBarcode its symbology list is shorter (no postal formats beyond a few, no Swiss QR), so check your exact formats before committing.

## Pitfalls and Migration Guide

1. **ZXing is frozen — plan your Android strategy.** The official scanner app is gone from the store and broken on Android 14+. If you ship an Android scanning app, either keep ZXing core as a pinned dependency (it still decodes fine on supported devices) and prepare a fallback, or evaluate the ML Kit barcode scanning SDK. Do not wait for a ZXing fix; the maintainers have explicitly said there will not be one.
2. **ZXing's 1D generation is not its strong suit.** `BarcodeFormat.EAN_13` and `CODE_128` exist, but ZXing's `core` is 2D-focused and its 1D output lacks the fine control (module width, bar height, human-readable placement) that label printers need. For 1D labels, generate with OkapiBarcode or Barcode4j and reserve ZXing for QR/Data Matrix/Aztec and decoding.
3. **Legacy `net.sf.barcode4j` is unmaintained.** Many tutorials still reference the old coordinates. If you see `net.sf.barcode4j:barcode4j:2.1` in a pom, migrate to `com.singingbush:barcode4j:2.4.0` — same packages, modern builds, no Avalon dependency. Verify your exact symbology exists in the fork before migrating (Aztec and QR were added in 2.4.0).
4. **DPI matters more than pixels.** A barcode generated at 72 DPI and printed on a 300 DPI thermal label will scan poorly or not at all. OkapiBarcode's `Java2DRenderer` and Barcode4j's `BitmapCanvasProvider` both let you control resolution/scale explicitly — set it from your printer's actual DPI, not a magic number.
5. **Quiet zones are non-negotiable.** Truncating the quiet zone (the blank margin around the barcode) to save space is the single most common cause of "won't scan" production incidents. OkapiBarcode and Barcode4j both expose quiet-zone settings; ZXing's `encode()` width/height effectively define the zone via the matrix dimensions — leave headroom.
6. **Human-readable text must match the encoded data.** If you let a library auto-format EAN/UPC check digits but then print a different value below the bars, scanners reading the bars will disagree with operators reading the text. Generate the text from the same source of truth as the barcode content.
7. **Mix generation and decoding deliberately.** The complete 2026 stack is often a combination: OkapiBarcode (or Barcode4j) for generating labels + ZXing core for decoding inbound scans. Trying to force one library to do both jobs usually means compromising on one side.
8. **Test with real scanners, not just your eyes.** A barcode that renders fine on screen can fail on a warehouse gun scanner due to contrast, module width, or aspect ratio. Print a test sheet at the target DPI and verify with a physical scanner before rolling out label changes — the same discipline applies to our [POS system comparison](../2026-06-05-self-hosted-pos-systems-ospos-odoo-erpnext-guide/) where barcode fidelity is a hard requirement.

## Building a Barcode Pipeline That Lasts

The pattern that holds up in production: **ZXing core pinned at a known-good version** for decoding and QR generation, **OkapiBarcode** for 1D label generation with SVG output where print quality matters, and **Barcode4j** only when FOP/XML-FO PDF integration is already in your stack. All three are Apache-2.0, so mixing them carries zero licensing friction.

If you are generating barcodes as a *service* rather than inside an application, also look at the server-side QR/barcode API tools we compared in our [QuickChart vs BWIP-JS vs php-qrcode guide](../2026-04-26-quickchart-vs-bwip-js-vs-php-qrcode-self-hosted-qr-barcode-api-guide-2026/), and if your labels end up inside PDFs, our [Java PDF library comparison](../2026-08-26-java-pdf-libraries-pdfbox-openpdf-itext-comparison/) covers the document side of that pipeline.

## FAQ

### Is ZXing still maintained in 2026?

ZXing is in maintenance mode. The README states there is "no active development or roadmap," only bug fixes and minor enhancements. The repository still receives occasional pushes, but new features are not coming, and the Android Barcode Scanner app does not work with Android 14 and will not be updated.

### Which Java barcode library should I use to generate Code 128?

For pure Code 128 generation, OkapiBarcode is the best-maintained option with fine control over module width, bar height, and human-readable text. Barcode4j (the maintained `com.singingbush` fork, 2.4.0) is a solid alternative, especially if you need FOP/XML-FO integration. ZXing can generate Code 128 but its 1D support is secondary to its 2D and decoding focus.

### Can OkapiBarcode read or scan barcodes?

No. OkapiBarcode is generation-only (encoding). For decoding, use ZXing's `core` module. Many projects pair the two: OkapiBarcode (or Barcode4j) to generate labels, ZXing to read them back.

### Does Barcode4j support QR codes?

Yes, in the maintained fork. QR Code and Aztec support were added in Barcode4j 2.4.0. The legacy `net.sf.barcode4j:barcode4j:2.1` artifact does not have QR support — migrate to `com.singingbush:barcode4j:2.4.0` for it.

### What are the Maven coordinates for ZXing?

Two artifacts: `com.google.zxing:core` (the decoding and encoding engine, Android-friendly) and `com.google.zxing:javase` (the JavaSE-specific `MatrixToImageWriter` and other J2SE helpers). Current stable line is 3.5.x.

### How do I generate a barcode for a thermal label printer?

Use a library that exposes DPI/scale control — OkapiBarcode's `Java2DRenderer` or Barcode4j's `BitmapCanvasProvider` both do. Generate at your printer's native DPI (typically 203 or 300 DPI), keep the quiet zone intact, and test with a physical scanner before mass printing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Java Barcode Libraries in 2026: ZXing vs OkapiBarcode vs Barcode4j — Which One Should You Use?",
  "description": "Compare ZXing, OkapiBarcode, and Barcode4j for Java barcode generation and scanning with live GitHub stats, code examples, maintenance-status analysis, and label-printing pitfalls.",
  "datePublished": "2026-08-26",
  "dateModified": "2026-08-26",
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
