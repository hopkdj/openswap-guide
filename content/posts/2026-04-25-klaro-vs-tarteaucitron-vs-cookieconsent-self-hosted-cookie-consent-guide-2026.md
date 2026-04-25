---
title: "Klaro! vs Tarteaucitron vs CookieConsent: Self-Hosted Cookie Consent Managers 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "privacy", "gdpr", "cookie-consent"]
draft: false
description: "Compare the top 3 open-source cookie consent managers for GDPR compliance. Self-host Klaro!, Tarteaucitron.js, or orestbida/CookieConsent with Docker on your own infrastructure."
---

Every website that serves visitors in the European Union must comply with the ePrivacy Directive (commonly called the "EU Cookie Law") and the GDPR. If you self-host your websites — whether it's a Hugo blog, a Next.js app, or a WordPress instance — you are responsible for ensuring cookie consent compliance. Commercial solutions like Cookiebot or OneTrust require external CDN calls and third-party scripts that undermine the privacy goals of self-hosting.

This guide compares three open-source, self-hosted cookie consent managers: **Tarteaucitron.js**, **Klaro!**, and **CookieConsent** (by orestbida). Each can be served entirely from your own server, requires no external dependencies, and gives you full control over consent data.

| Feature | Tarteaucitron.js | Klaro! | CookieConsent |
|---|---|---|---|
| GitHub Stars | 1,041 | 1,445 | 5,443 |
| License | MIT | BSD-3-Clause | MIT |
| Last Updated | April 2026 | March 2025 | May 2025 |
| Language | JavaScript | JavaScript | JavaScript |
| GDPR Compliant | Yes | Yes | Yes |
| CCPA Support | No | Yes | Yes |
| Consent Logging | Manual | Via API | Via Callbacks |
| IAB TCF Support | Partial | Yes (v2.2) | No |
| Framework Support | Vanilla JS | Vanilla, React, Vue | Vanilla, React, Vue |
| File Size | ~25 KB (gzipped) | ~35 KB (gzipped) | ~8 KB (gzipped) |
| Docker Deployment | Yes (nginx serving) | Yes (nginx serving) | Yes (nginx serving) |

## Why Self-Host Your Cookie Consent Manager

Most websites load cookie consent banners from commercial CDNs — adding third-party JavaScript that tracks users by default. For privacy-conscious operators, this defeats the entire purpose of compliance. Self-hosting your consent manager means:

- **No third-party CDN calls** — all JavaScript is served from your own domain
- **Full data sovereignty** — consent logs stay on your infrastructure
- **Zero external dependencies** — no risk of the vendor going offline or changing terms
- **Custom branding** — match your site's design without premium plan restrictions
- **Complete auditability** — you control every line of code running on your pages

For self-hosters running web servers like [Nginx, Caddy, or Traefik](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/), deploying a cookie consent manager is straightforward — simply serve the static JS/CSS files alongside your website assets.

## Tarteaucitron.js: The EU-Favorite Solution

**Tarteaucitron.js** ([GitHub](https://github.com/AmauriC/tarteaucitron.js)) is the most widely used open-source cookie consent manager in the European Union. Originally developed in France, it has become the de facto standard for GDPR compliance among French government websites and thousands of European organizations.

### Key Features

- **Automatic service blocking** — prevents cookies from loading until consent is given
- **Built-in service integrations** — pre-configured templates for Google Analytics, Facebook Pixel, YouTube, Google Ads, and 30+ other services
- **Multi-language support** — 20+ languages built in, with easy translation overrides
- **Accessibility compliant** — WCAG 2.1 AA compatible, keyboard navigable
- **Per-category consent** — users can accept analytics while rejecting advertising cookies

### Installation

The simplest deployment is to clone the repository and serve the files via your existing web server:

```bash
# Clone and serve via a lightweight web server
git clone https://github.com/AmauriC/tarteaucitron.js.git
cd tarteaucitron.js
# Serve on port 8080
python3 -m http.server 8080
```

### Docker Deployment

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./tarteaucitron.js:/usr/share/nginx/html/consent:ro
      - ./nginx-consent.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
```

With the Nginx configuration:

```nginx
server {
    listen 80;
    server_name consent.example.com;

    root /usr/share/nginx/html/consent;
    index tarteaucitron.js;

    # Enable caching for static assets
    location ~* \.(js|css)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_types application/javascript text/css;
}
```

### Integration Example

```html
<script src="/consent/tarteaucitron.js"></script>
<script>
tarteaucitron.init({
    "privacyUrl": "/privacy",
    "hashtag": "#tarteaucitron",
    "cookieName": "tarteaucitron",
    "orientation": "middle",
    "showAlertSmall": false,
    "cookieslist": true,
    "highDenialButton": true,
    "useExternalCss": false,
    "DenyAllCta": true,
    "AcceptAllCta": true,
    "readmoreLink": "/cookie-policy",
    "mandatory": true,
    "mandatoryCta": true
});

// Add Google Analytics as a service
(tarteaucitron.job = tarteaucitron.job || []).push('gtag');
</script>
```

## Klaro!: The Modern Consent Manager

**Klaro!** ([GitHub](https://github.com/KIProtect/klaro)) is developed by KIProtect, a German privacy technology company. It is designed as a modern, configurable consent manager that supports not just cookies but any kind of tracking technology. Klaro is fully compliant with GDPR, ePrivacy, and CCPA requirements.

### Key Features

- **IAB TCF v2.2 support** — integrates with the Interactive Advertising Bureau's Transparency and Consent Framework
- **Granular consent categories** — define custom categories with descriptions and purposes
- **CCPA opt-out mode** — supports "Do Not Sell My Personal Information" workflows
- **React/Vue integration** — official components for modern JavaScript frameworks
- **Configurable via JSON** — all settings in a single configuration file, no code changes needed
- **Multi-site management** — one configuration can manage consent across multiple domains

### Docker Deployment

Klaro can be served through a Docker-based Nginx container:

```yaml
version: "3.8"

services:
  klaro:
    image: nginx:alpine
    ports:
      - "8081:80"
    volumes:
      - ./klaro/dist:/usr/share/nginx/html/klaro:ro
      - ./klaro-config.js:/usr/share/nginx/html/klaro-config.js:ro
      - ./klaro-nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
```

The Klaro configuration file (`klaro-config.js`):

```javascript
window.klaroConfig = {
    version: 1,
    name: 'klaro',
    elementID: 'klaro',
    storageMethod: 'cookie',
    cookieName: 'klaro-consent',
    cookieExpiresAfterDays: 365,
    htmlTexts: true,
    default: false,
    mustConsent: true,
    acceptAll: true,
    hideDeclineAll: false,
    translations: {
        en: {
            consentModal: {
                description: 'We use cookies to ensure basic functionality and improve our service.'
            },
            googleAnalytics: {
                description: 'Anonymous usage statistics to improve the site.',
            },
        },
    },
    services: [
        {
            name: 'googleAnalytics',
            title: 'Google Analytics',
            purposes: ['analytics'],
            required: false,
            optOut: false,
        },
    ],
};
```

### Integration on Your Website

```html
<!-- Load Klaro config first -->
<script defer src="https://consent.example.com/klaro-config.js"></script>
<!-- Load Klaro library -->
<script defer src="https://consent.example.com/klaro/klaro.js"></script>

<!-- The banner will auto-render based on klaroConfig -->
```

## CookieConsent: The Lightweight Champion

**CookieConsent** by orestbida ([GitHub](https://github.com/orestbida/cookieconsent)) is the most starred open-source cookie consent project with over 5,400 stars. It is a lightweight, cross-browser plugin written in vanilla JavaScript with zero dependencies. Despite its small footprint (~8 KB gzipped), it offers robust features for GDPR and CCPA compliance.

### Key Features

- **Smallest file size** — only 8 KB gzipped, the lightest of the three options
- **Highest community adoption** — 5,443 GitHub stars, widely used in the open-source community
- **Framework-agnostic** — works with any frontend framework; official React and Vue wrappers available
- **Custom consent callbacks** — hook into accept/deny events for custom consent logging
- **Full styling control** — CSS custom properties for easy theme customization
- **Automatic language detection** — detects browser language and translates accordingly

### Docker Deployment

```yaml
version: "3.8"

services:
  cookieconsent:
    image: nginx:alpine
    ports:
      - "8082:80"
    volumes:
      - ./cookieconsent/dist:/usr/share/nginx/html/cc:ro
      - ./cc-nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
```

Nginx configuration for CookieConsent:

```nginx
server {
    listen 80;
    server_name cc.example.com;

    root /usr/share/nginx/html/cc;

    location / {
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    gzip on;
    gzip_types application/javascript text/css;
}
```

### Integration Example

```html
<link rel="stylesheet" href="/cc/css/cookieconsent.min.css">
<script src="/cc/js/cookieconsent.min.js"></script>

<script>
window.CookieConsent.run({
    categories: {
        necessary: {
            enabled: true,
            readOnly: true,
        },
        analytics: {
            enabled: false,
            readOnly: false,
        },
        marketing: {
            enabled: false,
            readOnly: false,
        },
    },
    language: {
        default: 'en',
        translations: {
            en: {
                consentModal: {
                    title: 'We use cookies',
                    description: 'This website uses essential cookies and optional analytics cookies.',
                    acceptAllBtn: 'Accept all',
                    acceptNecessaryBtn: 'Reject all',
                    showPreferencesBtn: 'Manage preferences',
                },
                preferencesModal: {
                    title: 'Cookie preferences',
                    acceptAllBtn: 'Accept all',
                    acceptNecessaryBtn: 'Reject all',
                    savePreferencesBtn: 'Save preferences',
                },
            },
        },
    },
    onConsent: function(cookie) {
        // Custom consent logging - send to your backend
        console.log('Consent received:', cookie);
    },
});
</script>
```

## Detailed Feature Comparison

### GDPR Compliance Depth

| Requirement | Tarteaucitron.js | Klaro! | CookieConsent |
|---|---|---|---|
| Prior blocking of non-essential scripts | Yes | Yes | Yes (with callbacks) |
| Granular per-category consent | Yes | Yes | Yes |
| Consent withdrawal (easy as giving) | Yes | Yes | Yes |
| Consent proof/logging | Manual setup | Via consent API | Via callback hooks |
| IAB TCF v2.2 integration | Partial | Yes | No |
| Multi-language out of the box | 20+ languages | Configurable | Browser auto-detect |
| Accessibility (WCAG 2.1 AA) | Yes | Yes | Yes |

### Technical Footprint

| Metric | Tarteaucitron.js | Klaro! | CookieConsent |
|---|---|---|---|
| Minified size | ~70 KB | ~120 KB | ~20 KB |
| Gzipped size | ~25 KB | ~35 KB | ~8 KB |
| Dependencies | None | None | None |
| Framework bindings | None | React, Vue | React, Vue |
| CDN alternative | Self-host | Self-host | Self-host |
| Active development | Very active | Moderate | Moderate |

### Which One Should You Choose?

**Choose Tarteaucitron.js if:**
- You serve EU visitors and want the most battle-tested GDPR solution
- You need pre-built integrations for 30+ common third-party services
- You want a French/EU-developed solution with strong legal pedigree
- Active development and frequent updates matter to you

**Choose Klaro! if:**
- You need IAB TCF v2.2 compliance for advertising consent
- You want CCPA "Do Not Sell" support alongside GDPR
- You prefer JSON-based configuration over JavaScript code
- You use React or Vue and want official component bindings

**Choose CookieConsent if:**
- Minimal JavaScript footprint is your top priority (8 KB gzipped)
- You want the most popular open-source option (5,400+ stars)
- You need maximum flexibility for custom consent workflows
- You want easy CSS theming via custom properties

For most self-hosted websites, **Tarteaucitron.js** is the safest choice for EU compliance, while **CookieConsent** is the best option when page load performance matters most. If you run a more complex setup requiring IAB TCF integration or CCPA compliance, **Klaro!** is the right pick.

For related reading, check out our [privacy analytics comparison](../matomo-vs-plausible-vs-umami-web-analytics-guide/) to understand how cookie consent ties into your overall [privacy stack](../privacy-stack-guide/).

## FAQ

### Is self-hosting a cookie consent manager legally compliant with GDPR?

Yes. The GDPR does not require you to use a specific vendor or cloud service for cookie consent. What matters is that your consent mechanism meets the legal requirements: prior blocking of non-essential cookies, granular per-category choices, easy withdrawal of consent, and a record of consent. All three tools compared here meet these requirements when properly configured.

### Do I need cookie consent if I only use essential cookies?

If your website only uses strictly necessary cookies (e.g., session cookies for login, shopping cart cookies), you generally do not need a consent banner under the ePrivacy Directive. However, you should still include a cookie policy page explaining what cookies you use and why. If you add any analytics, advertising, or social media cookies, consent becomes mandatory.

### Can I customize the appearance of the consent banner?

All three tools support full visual customization. Tarteaucitron.js allows CSS overrides through custom stylesheets. Klaro! supports custom CSS via configuration. CookieConsent offers the most flexible theming system using CSS custom properties (variables), making it easy to match any website design without writing custom CSS.

### How do I log and store user consent for audit purposes?

Cookie consent logging is a GDPR requirement. Tarteaucitron.js stores consent in a cookie that you can parse server-side. Klaro! provides a consent API that you can hook into for backend logging. CookieConsent fires `onConsent` and `onFirstConsent` callbacks where you can send consent data to your server. For production deployments, consider storing consent hashes with timestamps in your database to maintain an audit trail.

### Does self-hosting these tools affect my website's performance?

Self-hosting eliminates external CDN requests, which can actually improve performance. Tarteaucitron.js adds ~25 KB (gzipped) to your page, Klaro! adds ~35 KB, and CookieConsent adds just ~8 KB. When served from your own server with proper caching headers (30-day cache for static JS/CSS files), the browser downloads these files once and reuses them on subsequent visits. The impact on page load is minimal, especially with CookieConsent.

### Can these tools block scripts before consent is given?

Yes, all three tools support prior blocking. Tarteaucitron.js automatically wraps third-party scripts and prevents them from executing until consent is granted. Klaro! uses a service-based approach where you define which services load under which consent categories. CookieConsent requires you to use its callback system to conditionally load scripts after consent — slightly more manual but offers maximum control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Klaro! vs Tarteaucitron vs CookieConsent: Self-Hosted Cookie Consent Managers 2026",
  "description": "Compare the top 3 open-source cookie consent managers for GDPR compliance. Self-host Klaro!, Tarteaucitron.js, or orestbida/CookieConsent with Docker on your own infrastructure.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
