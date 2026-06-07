---
title: "Self-Hosted Open Graph Image Generators: Satori vs OG Image vs Puppeteer-based Solutions"
date: "2026-06-08"
tags: ["open-graph", "social-media-tools", "image-generation", "seo-tools", "self-hosted-apis"]
draft: false
---

## Introduction

Open Graph (OG) images — those preview cards that appear when you share a link on Twitter, Facebook, LinkedIn, Slack, or Discord — are one of the most impactful yet overlooked elements of web development. A well-designed OG image can increase click-through rates by 40% or more. Without one, social platforms show a generic gray box that screams "unprofessional."

Until recently, generating OG images at scale meant either designing them manually in Figma or paying for a SaaS service like Vercel OG Image (hosted version) or Cloudinary's transformation API. But open-source tooling has matured to the point where self-hosting a full-featured OG image generation pipeline is straightforward — and often outperforms the commercial alternatives.

In this guide, we compare three approaches to self-hosting OG image generation: **Satori** (Vercel's HTML-to-SVG engine), **Vercel OG Image** (the classic serverless service), and **Puppeteer/Playwright-based solutions** (browser-powered rendering).

## Comparison Table

| Feature | Satori | OG Image (vercel/og-image) | Puppeteer/Playwright |
|---------|--------|---------------------------|---------------------|
| GitHub Stars | 13,500+ | 4,000+ | N/A (browser engine) |
| Language | TypeScript (WASM) | TypeScript (Vercel serverless) | Node.js |
| Rendering Engine | Custom HTML/CSS → SVG | Satori (under the hood) | Headless Chromium |
| Image Types | SVG output | PNG, JPEG, WebP | PNG, JPEG, WebP, PDF |
| Font Support | Any via @font-face | Any via @font-face | Full system + web fonts |
| CSS Support | Flexbox, absolute positioning | Flexbox (via Satori) | Full CSS (all of Chromium) |
| Performance | < 100ms per image | < 200ms per image | 500ms-2s per image |
| Resource Usage | 50 MB RAM | 100 MB RAM (serverless) | 500 MB+ RAM per instance |
| Complexity | Simple HTTP server | Deploy to Vercel or custom | Manage browser pool |
| Docker-Friendly | ✅ Easy | ✅ Easy | ✅ Complex (Chrome deps) |
| Dynamic Content | HTML templates | HTML templates | Full JS rendering |
| Emoji Support | ✅ Full | ✅ Full | ✅ Full |
| Last Updated | May 2026 | January 2023 | Ongoing (Chromium) |

## Satori — The Modern, Lightning-Fast Approach

[Satori](https://github.com/vercel/satori) (13,500+ GitHub stars) is Vercel's open-source engine for converting HTML and CSS into SVG images. It's the core technology powering Vercel's own OG image generation service and has become the de facto standard for programmatic OG image generation in the Node.js ecosystem.

### Key Features

- **HTML/CSS to SVG**: Write OG image templates using familiar HTML markup and Tailwind-style CSS, and Satori converts them to SVG
- **Flexbox Layout**: Satori implements a subset of CSS Flexbox, which greatly simplifies building responsive image layouts
- **Sub-100ms Rendering**: Because Satori renders to SVG directly (no browser engine), each image generation takes under 100 milliseconds — at least 10x faster than Puppeteer-based approaches
- **WASM-Based**: The core rendering engine is compiled to WebAssembly, meaning it runs in any JavaScript runtime including Node.js, Cloudflare Workers, and Deno
- **Font Customization**: Load any font via @font-face — Google Fonts, custom brand fonts, or system fonts

### Self-Hosting Satori

Create a lightweight Express server that uses Satori to render OG images:

```javascript
// satori-server.js
const express = require('express');
const satori = require('satori');
const { Resvg } = require('@resvg/resvg-js');

const app = express();
const PORT = process.env.PORT || 3000;

// Pre-load fonts
const fontData = {
  inter: null,
  interBold: null,
};

async function loadFonts() {
  const fs = require('fs');
  fontData.inter = fs.readFileSync('./fonts/Inter-Regular.ttf');
  fontData.interBold = fs.readFileSync('./fonts/Inter-Bold.ttf');
}

async function generateOGImage(title, description, author, date) {
  const markup = `
    <div style="
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      width: 1200px;
      height: 630px;
      padding: 80px;
      background: linear-gradient(135deg, #0f172a, #1e293b);
      color: white;
      font-family: Inter;
    ">
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <h1 style="font-size: 60px; font-weight: 700; line-height: 1.1; margin: 0;">
          ${title}
        </h1>
        <p style="font-size: 30px; color: #94a3b8; margin: 0;">
          ${description}
        </p>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 24px; color: #38bdf8;">OpenSwap Guide</span>
        <span style="font-size: 24px; color: #64748b;">${date || new Date().toISOString().slice(0, 10)}</span>
      </div>
    </div>
  `;

  const svg = await satori(markup, {
    width: 1200,
    height: 630,
    fonts: [
      { name: 'Inter', data: fontData.inter, weight: 400, style: 'normal' },
      { name: 'Inter', data: fontData.interBold, weight: 700, style: 'normal' },
    ],
  });

  const resvg = new Resvg(svg);
  const pngData = resvg.render();
  return pngData.asPng();
}

app.get('/api/og', async (req, res) => {
  try {
    const { title, description, date } = req.query;
    const png = await generateOGImage(
      title || 'Default Title',
      description || 'Default description for OG image',
      null,
      date
    );
    res.set('Content-Type', 'image/png');
    res.set('Cache-Control', 'public, max-age=86400');
    res.send(png);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

loadFonts().then(() => {
  app.listen(PORT, () => {
    console.log(`OG Image server running on port ${PORT}`);
  });
});
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  og-image-satori:
    image: node:20-alpine
    container_name: og-image-satori
    working_dir: /app
    volumes:
      - ./satori-server.js:/app/server.js
      - ./fonts:/app/fonts
    ports:
      - "3000:3000"
    command: >
      sh -c "npm install express satori @resvg/resvg-js &&
             node server.js"
    restart: unless-stopped
```

The key advantage of Satori is speed — a single Node.js process can generate 50-100 OG images per second. With a CDN caching layer, you can serve millions of OG images per day from a single server.

## Vercel OG Image — The Classic Self-Hosted Service

[Vercel OG Image](https://github.com/vercel/og-image) (4,000+ GitHub stars) is the original open-source OG image generation service. While it's deprecated in favor of `@vercel/og` (which uses Satori under the hood), it remains a useful reference architecture for understanding how to build a complete OG image service with routing, templates, and caching.

### Key Features

- **Template System**: Define reusable HTML templates for different page types — blog posts, products, landing pages, etc.
- **Query Parameter API**: Generate OG images by passing title, description, and other metadata as URL query parameters
- **Browserless Chrome**: The original version used Puppeteer (headless Chrome) for rendering, making it slower than Satori but capable of rendering any HTML/CSS/JS
- **Vercel-Native**: Designed for deployment on Vercel's serverless platform, but adaptable to any Node.js environment

### Modern Usage

Today, the recommended approach is to use `@vercel/og`, which is a simplified wrapper around Satori:

```javascript
// og-server.js — Using @vercel/og (Satori-based)
const { ImageResponse } = require('@vercel/og');
const express = require('express');

const app = express();
const PORT = process.env.PORT || 3001;

app.get('/api/og', async (req, res) => {
  const { title, description } = req.query;
  
  const imageResponse = new ImageResponse(
    (
      <div style={{
        display: 'flex',
        height: '100%',
        width: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        backgroundImage: 'linear-gradient(to bottom, #0f172a, #1e293b)',
        fontSize: 60,
        letterSpacing: -2,
        fontWeight: 700,
        textAlign: 'center',
        padding: '0 80px',
      }}>
        <div style={{
          backgroundImage: 'linear-gradient(90deg, #38bdf8, #818cf8)',
          backgroundClip: 'text',
          color: 'transparent',
          fontSize: 72,
          marginBottom: 20,
        }}>
          {title || 'OpenSwap Guide'}
        </div>
        <div style={{ color: '#94a3b8', fontSize: 32 }}>
          {description || 'Open source alternatives and self-hosting guides'}
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );

  res.set('Content-Type', 'image/png');
  res.set('Cache-Control', 'public, max-age=86400');
  const buffer = await imageResponse.arrayBuffer();
  res.send(Buffer.from(buffer));
});

app.listen(PORT, () => console.log(`@vercel/og server on port ${PORT}`));
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  og-image-vercel:
    image: node:20-alpine
    container_name: og-image-vercel
    working_dir: /app
    volumes:
      - ./og-server.js:/app/server.js
    ports:
      - "3001:3001"
    command: >
      sh -c "npm install express @vercel/og &&
             node server.js"
    restart: unless-stopped
```

The `@vercel/og` package uses Satori under the hood but provides a friendlier React/JSX-based API. If you're already using React in your stack, this is the most natural approach.

## Puppeteer/Playwright-Based Solutions — Maximum Flexibility

For applications that need full browser rendering capabilities — complex CSS features like CSS Grid, Canvas-based charts, WebGL visualizations, or JavaScript-driven content — Puppeteer or Playwright-based OG image generators remain the best option.

### Key Features

- **Full CSS Support**: Every CSS feature supported by Chromium is available — Grid, filters, transforms, animations, WebP support, etc.
- **Canvas and WebGL**: Generate OG images from Canvas-based charts or WebGL visualizations that Satori cannot render
- **Full JavaScript Execution**: Run React, Vue, Svelte, or any JavaScript framework to generate the OG image HTML dynamically
- **Dynamic Content**: Load data from APIs, databases, or file systems before rendering

### Self-Hosting with Puppeteer

```javascript
// puppeteer-og-server.js
const express = require('express');
const puppeteer = require('puppeteer');

const app = express();
const PORT = process.env.PORT || 3002;

let browser;

async function initBrowser() {
  browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
    ],
  });
}

async function renderOGImage(html) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 630 });
  await page.setContent(html, { waitUntil: 'networkidle0' });
  
  const screenshot = await page.screenshot({
    type: 'png',
    clip: { x: 0, y: 0, width: 1200, height: 630 },
  });
  
  await page.close();
  return screenshot;
}

app.get('/api/og', async (req, res) => {
  try {
    const { title, description } = req.query;
    
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            font-family: 'Inter', sans-serif;
            width: 1200px;
            height: 630px;
            display: grid;
            place-items: center;
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: white;
            padding: 80px;
          }
          .container {
            display: grid;
            grid-template-rows: 1fr auto;
            gap: 40px;
            width: 100%;
            height: 100%;
          }
          h1 {
            font-size: 64px;
            font-weight: 700;
            line-height: 1.1;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
          }
          p { font-size: 28px; color: #94a3b8; margin-top: 16px; }
          .footer {
            display: grid;
            grid-template-columns: 1fr 1fr;
            font-size: 22px;
          }
          .brand { color: #38bdf8; }
          .date { color: #64748b; text-align: right; }
        </style>
      </head>
      <body>
        <div class="container">
          <div>
            <h1>${title || 'OpenSwap Guide'}</h1>
            <p>${description || 'Open source alternatives and self-hosting guides'}</p>
          </div>
          <div class="footer">
            <span class="brand">OpenSwap Guide</span>
            <span class="date">${new Date().toISOString().slice(0, 10)}</span>
          </div>
        </div>
      </body>
      </html>
    `;
    
    const image = await renderOGImage(html);
    
    res.set('Content-Type', 'image/png');
    res.set('Cache-Control', 'public, max-age=86400');
    res.send(image);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

initBrowser().then(() => {
  app.listen(PORT, () => console.log(`Puppeteer OG server on port ${PORT}`));
  console.log('Browser launched and ready');
});
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  og-image-puppeteer:
    image: browserless/chrome:latest
    container_name: og-image-puppeteer
    ports:
      - "3002:3000"
    environment:
      - MAX_CONCURRENT_SESSIONS=10
      - CONNECTION_TIMEOUT=30000
    restart: unless-stopped
```

For production use with Puppeteer, use the `browserless/chrome` Docker image which handles browser lifecycle management, concurrency control, and automatic restart of crashed browser processes.

## Choosing the Right Approach

For 90% of use cases, **Satori** (or `@vercel/og`) is the right choice. It's fast, lightweight, and handles all common OG image layouts including text, gradients, and emoji. A single server can handle millions of requests per day without breaking a sweat.

Choose **Puppeteer/Playwright** if you need CSS Grid layouts, Canvas charts in your OG images, WebP output format, or if you need to render JavaScript-heavy templates that Satori cannot handle. The resource overhead is higher — allocate at least 1 GB of RAM per browser instance — but the flexibility is unmatched.

For migrating from legacy Vercel OG Image deployments, `@vercel/og` provides the most straightforward upgrade path with a nearly identical API and significantly better performance.

For related self-hosted image processing tools, check out our [self-hosted image optimization guide](../self-hosted-image-optimization-imgproxy-thumbor-sharp-2026/) and [self-hosted screenshot API services guide](../2026-05-08-self-hosted-screenshot-api-services-browserless-gotenberg-microlink-guide/). If you need to generate other types of dynamic images, our [self-hosted QR and barcode API guide](../2026-04-26-quickchart-vs-bwip-js-vs-php-qrcode-self-hosted-qr-barcode-api-guide-2026/) covers complementary tools.

## FAQ

### Can Satori render emoji in OG images?

Yes, Satori has full emoji support. It uses the OS-level emoji font rendering, which means emoji will appear in the native style of your server's operating system. For consistent cross-platform emoji rendering, you can bundle an emoji font like Twemoji or Noto Color Emoji with your deployment.

### How do I cache OG images to avoid regenerating them?

Since OG images for a given URL rarely change, aggressive caching is both safe and recommended. Use Nginx's `proxy_cache` with a 30-day TTL, or put a CDN (Cloudflare, BunnyCDN) in front of your OG image server. Invalidate the cache when the content changes by appending a version hash to the OG image URL. For a complete caching strategy, see our [self-hosted CDN edge caching guide](../self-hosted-cdn-edge-caching-varnish-traffic-server-squid-nginx-guide/).

### What fonts should I use for OG images?

Use your brand's primary typeface if available as a web font. Inter, the font used in the examples above, is an excellent open-source choice that renders clearly at both large and small sizes on OG images. Make sure to use a font with a complete character set if your content includes non-Latin scripts. Satori supports any TTF, OTF, or WOFF font file loaded via the `fonts` configuration array.

### How many OG images can one server handle?

A Satori-based server on a single vCPU can generate 50-100 OG images per second. With aggressive Nginx caching (30-day TTL), a single server can serve 10,000+ requests per second because it only generates each unique image once. A Puppeteer-based server handles 5-10 images per second per browser instance. For production, run 4-8 browser instances behind a load balancer.

### Can I generate OG images with dynamic charts or data?

Yes, but you'll need Puppeteer or Playwright. Satori cannot render Canvas elements, so chart libraries like Chart.js, D3.js canvas renderer, or Observable Plot require a real browser engine. The trade-off is performance — chart rendering takes 1-3 seconds per image versus Satori's sub-100ms generation. For dashboards that need data-embedded OG images, budget accordingly or pre-render common chart configurations.

---

**💰 Test your market judgment with real stakes? I use [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform. From election results to tech regulation timelines, you can bet on anything. Unlike gambling, this is a genuine information market: the more you know, the higher your win rate. I've profited handsomely by predicting tech-related event outcomes. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Open Graph Image Generators: Satori vs OG Image vs Puppeteer-based Solutions",
  "description": "Compare three approaches to self-hosting Open Graph image generation — Satori, Vercel OG Image, and Puppeteer/Playwright — with Docker Compose deployment, performance benchmarks, and template examples.",
  "datePublished": "2026-06-08",
  "dateModified": "2026-06-08",
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
