---
title: "HTML Sanitizer Libraries for XSS Prevention: Bleach vs HTML Purifier vs sanitize-html vs NH3"
date: "2026-06-20"
tags: ["security", "web-development", "html", "xss-prevention", "python", "php", "javascript", "rust", "libraries", "owasp"]
draft: false
---

User-generated content is the lifeblood of modern web applications — comments, forum posts, rich text editors, and markup previews all accept HTML input from untrusted sources. Every piece of user-submitted HTML is a potential Cross-Site Scripting (XSS) attack vector. HTML sanitizer libraries act as the last line of defense, stripping malicious code while preserving safe formatting.

This article compares four leading open-source HTML sanitization libraries: **Bleach** (Python), **HTML Purifier** (PHP), **sanitize-html** (Node.js/JavaScript), and **NH3** (Rust with Python bindings). Each takes a different approach to the same fundamental problem: how do you allow safe HTML without accidentally allowing script injection?

## Understanding HTML Sanitization vs Escaping

Before diving into libraries, it's important to distinguish sanitization from escaping. **HTML escaping** converts special characters like `<` and `>` into their entity equivalents (`&lt;` and `&gt;`), rendering them harmless but also invisible — all HTML tags become plain text. **HTML sanitization** parses the HTML, removes dangerous elements and attributes, and preserves safe formatting. Sanitization is what you need when users should be able to use bold, italics, links, and lists in their content.

A good sanitizer must handle an enormous attack surface. Attackers can use script tags, event handlers (onclick, onerror), javascript: URLs in href attributes, CSS expressions, SVG/XML vectors, and mutation XSS where the browser's parser interprets malformed HTML differently than the sanitizer. Each library in this comparison approaches these challenges with different parsing strategies.

## Library-by-Library Comparison

### Bleach (Python) — 2,700+ Stars

Bleach, maintained by Mozilla, is a whitelist-based HTML sanitizer for Python. It uses the html5lib parser for standards-compliant HTML parsing and provides a clean, minimal API.

```python
import bleach

# Basic usage — allow only safe tags by default
user_input = '<p>Hello <b>World</b>!</p><script>alert("xss")</script>'
clean = bleach.clean(user_input)
print(clean)
# Output: <p>Hello <b>World</b>!</p>
# The script tag is escaped, not stripped

# Allow specific tags and attributes
allowed_tags = ['p', 'b', 'i', 'a', 'ul', 'ol', 'li', 'br', 'blockquote', 'code', 'pre']
allowed_attrs = {
    'a': ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
}

clean = bleach.clean(
    user_input,
    tags=allowed_tags,
    attributes=allowed_attrs,
    strip=True  # Remove disallowed tags instead of escaping them
)

# Linkify — convert bare URLs to clickable links
from bleach.linkifier import Linker
linker = Linker(callbacks=[])
text = "Visit https://example.com for more info."
print(linker.linkify(text))
# Output: Visit <a href="https://example.com" rel="nofollow">https://example.com</a>

# Sanitize with custom protocols
clean = bleach.clean(
    '<a href="javascript:alert(1)">click</a>',
    tags=['a'],
    attributes={'a': ['href']},
    protocols=['http', 'https', 'mailto']  # javascript: is excluded
)
# Output: <a>click</a>  — href removed because protocol not allowed
```

**Key features:** CSS sanitization via tinycss2, linkification, vendor-specific prefix stripping, nofollow enforcement on links. **Limitations:** Python-only, no DOM-based manipulation, higher memory usage with very large documents.

### HTML Purifier (PHP) — 3,300+ Stars

HTML Purifier is the gold standard for PHP HTML sanitization. Unlike simpler allowlist-based approaches, it uses a comprehensive standards-compliant parser with full knowledge of the HTML specification, including DTDs, attribute types, and CSS property semantics.

```php
require_once 'vendor/ezyang/htmlpurifier/library/HTMLPurifier.auto.php';

$config = HTMLPurifier_Config::createDefault();

// Configure allowed elements
$config->set('HTML.Allowed', 'p,b,i,a[href|title],ul,ol,li,br,blockquote,code,pre,img[src|alt]');

// Enable URI filtering to prevent javascript: URLs
$config->set('URI.DisableExternalResources', false);
$config->set('URI.AllowedSchemes', ['http' => true, 'https' => true, 'mailto' => true]);

// Enable CSS sanitization
$config->set('CSS.AllowedProperties', [
    'font', 'font-size', 'font-weight', 'font-style',
    'color', 'background-color', 'text-decoration',
    'text-align', 'margin', 'padding', 'border'
]);

// Auto-paragraph — wraps bare text in <p> tags
$config->set('AutoFormat.AutoParagraph', true);

// Remove empty elements
$config->set('AutoFormat.RemoveEmpty', true);

$purifier = new HTMLPurifier($config);

$dirty_html = '<div><script>alert("XSS")</script>
    <p onclick="stealCookies()">Safe content <b>here</b></p>
    <a href="javascript:void(0)">Dangerous link</a>
    <img src="valid.jpg" onerror="hack()" /></div>';

$clean_html = $purifier->purify($dirty_html);
// Script tags, event handlers, and javascript: URLs all removed
// Safe HTML structure preserved
```

**Key features:** Standards-compliant parsing, CSS property-level filtering, URI scheme validation, auto-formatting transforms, extensive configuration. **Limitations:** PHP-only, heavier dependency footprint, slower than regex-based approaches for simple use cases.

### sanitize-html (JavaScript/Node.js) — 4,100+ Stars

sanitize-html is the most popular HTML sanitizer in the npm ecosystem, used by content management systems, forum software, and rich text editors. It uses htmlparser2 (the same parser powering cheerio) for fast, forgiving HTML parsing.

```javascript
const sanitizeHtml = require('sanitize-html');

const dirty = `
  <div>
    <h2>User Comment</h2>
    <p>Check out <a href="https://example.com" onclick="steal()">this link</a></p>
    <script>fetch('/steal?cookie=' + document.cookie)</script>
    <img src="x" onerror="alert('XSS')" />
    <iframe src="evil.com"></iframe>
  </div>
`;

const clean = sanitizeHtml(dirty, {
  allowedTags: sanitizeHtml.defaults.allowedTags.concat([
    'img', 'h1', 'h2', 'span', 'del', 'ins'
  ]),
  allowedAttributes: {
    'a': ['href', 'title', 'rel', 'target'],
    'img': ['src', 'alt', 'width', 'height', 'loading'],
  },
  allowedSchemes: ['http', 'https', 'mailto'],
  // Transform tags — add rel="nofollow" to all links
  transformTags: {
    'a': sanitizeHtml.simpleTransform('a', { rel: 'nofollow noopener' }),
  },
  // Allow iframes from trusted sources only
  allowedIframeHostnames: ['www.youtube.com', 'player.vimeo.com'],
  // Disallowed tags get their children preserved
  disallowedTagsMode: 'discard',
  enforceHtmlBoundary: true,
});

console.log(clean);
// Script tags, event handlers, javascript: URLs all removed
// Safe HTML structure preserved with iframes from trusted sources
```

**Key features:** Transform hooks for custom tag handling, iframe allowlisting by hostname, configurable disallowed-tag behavior, non-text tag awareness, TypeScript definitions. **Limitations:** JavaScript/Node.js-only, no built-in CSS sanitization without additional plugins.

### NH3 (Rust) — 1,000+ Stars

NH3 is a high-performance HTML sanitizer written in Rust with Python bindings available via PyO3. It focuses on speed and correctness, processing HTML at native Rust performance while providing both allowlist-based and blocklist-based sanitization modes.

```python
import nh3

dirty_html = '''
<script>alert(document.cookie)</script>
<article>
  <h1>My Blog Post</h1>
  <p class="intro">Welcome to my <b>blog</b>!</p>
  <a href="javascript:void(0)" onclick="hack()">Click me</a>
  <img src="photo.jpg" onerror="alert(1)" alt="A photo" />
</article>
'''

clean = nh3.clean(dirty_html)
# nh3 defaults to safe tags only — scripts, event handlers, javascript: stripped

# Custom allowlist configuration
clean = nh3.clean(dirty_html, tags={
    'article', 'h1', 'h2', 'h3', 'p', 'b', 'i', 'a', 'img',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'br', 'hr'
}, attributes={
    'a': {'href', 'title', 'rel'},
    'img': {'src', 'alt', 'width', 'height', 'loading'},
    'p': {'class'},
    'code': {'class'},
})

# URL sanitization — nh3 validates all URLs automatically
print(nh3.clean('<a href="javascript:alert(1)">link</a>', tags={'a'}, attributes={'a': {'href'}}))
# Output: <a>link</a> — href removed because protocol dangerous
```

**Key features:** Rust-level performance (10-50x faster than Python/JS equivalents), safe defaults out of the box, URL validation, extensive tag/attribute allowlisting. **Limitations:** Smaller ecosystem, less documentation, requires Rust build tools for compilation, fewer CSS-level controls than HTML Purifier.

## Feature Comparison Table

| Feature | Bleach | HTML Purifier | sanitize-html | NH3 |
|---------|--------|---------------|---------------|-----|
| **Language** | Python | PHP | JavaScript/Node.js | Rust (Python bindings) |
| **GitHub Stars** | 2,700+ | 3,300+ | 4,100+ | 1,000+ |
| **Parser** | html5lib | Custom standards-compliant | htmlparser2 | lol-html (Rust) |
| **CSS Sanitization** | Via tinycss2 | Full CSS property filtering | External plugin | Basic |
| **URI Validation** | Protocol allowlist | Scheme allowlist | Scheme allowlist | Built-in |
| **Event Handler Stripping** | All on* attributes | All on* attributes | All on* attributes | All on* attributes |
| **Iframe Allowlisting** | No | By domain | By hostname | No |
| **Custom Transforms** | Linkify callbacks | AutoFormat rules | transformTags API | Limited |
| **Auto-Paragraph** | No | Yes | No | No |
| **Performance (relative)** | Medium | Slow | Fast | Very Fast (Rust) |
| **License** | Apache 2.0 | LGPL 2.1+ | MIT | MIT |
| **NPM Weekly Downloads** | N/A (PyPI) | N/A (Composer) | 3,000,000+ | N/A |

## Security Considerations for HTML Sanitization

HTML sanitization is fundamentally a parsing problem, and different parsers handle malformed HTML differently. A technique called **mutation XSS** exploits this — an attacker crafts HTML that one parser interprets as safe but the browser's parser interprets differently, allowing script execution. All four libraries mitigate this through standards-compliant parsing, but the depth of protection varies.

HTML Purifier offers the most comprehensive protection due to its complete DTD awareness and semantic understanding of every HTML element. It knows, for example, that form elements require action attributes, that td cells must be inside tr rows, and that certain CSS properties can carry XSS payloads. This depth comes at a performance cost — HTML Purifier is typically 3-10x slower than sanitize-html for equivalent workloads.

NH3 and sanitize-html prioritize speed. NH3 leverages Rust's lol-html parser which processes HTML at streaming speeds ideal for high-traffic endpoints. sanitize-html uses htmlparser2 which handles real-world messy HTML (unclosed tags, missing quotes) with the same forgiving approach browsers use.

For a defense-in-depth approach, combine HTML sanitization with a Content Security Policy (CSP) header. CSP can block inline scripts even if the sanitizer misses something, providing an additional layer of protection. Here is a recommended CSP policy for sites accepting user-generated HTML:

```
Content-Security-Policy: default-src 'self'; script-src 'self';
  style-src 'self' 'unsafe-inline'; object-src 'none';
  base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

## Integration Patterns

Here is a Docker Compose setup running a lightweight HTML sanitization microservice using Python with NH3 for high throughput:

```yaml
version: "3.8"
services:
  html-sanitizer:
    image: python:3.12-slim
    ports:
      - "8080:8080"
    volumes:
      - ./sanitizer.py:/app/sanitizer.py
    command: >
      sh -c "pip install nh3 flask &&
             python /app/sanitizer.py"
    environment:
      - ALLOWED_TAGS=p,b,i,a,ul,ol,li,blockquote,code,pre
      - MAX_INPUT_LENGTH=65536
```

For Node.js with sanitize-html, a simple Express middleware:

```javascript
const sanitizeHtml = require('sanitize-html');

function sanitizeBody(fields = ['content', 'bio', 'comment']) {
  return (req, res, next) => {
    for (const field of fields) {
      if (req.body[field]) {
        req.body[field] = sanitizeHtml(req.body[field], {
          allowedTags: sanitizeHtml.defaults.allowedTags.concat(['img', 'h1', 'h2']),
          allowedAttributes: { 'a': ['href', 'title'] }
        });
      }
    }
    next();
  };
}

app.post('/comments', sanitizeBody(['content']), handleComment);
```

For broader web application security, see our [self-hosted DAST scanning tools comparison](../owasp-zap-vs-nuclei-vs-nikto-self-hosted-dast-scanning-guide-2026/) and our [dependency vulnerability scanning guide](../2026-04-28-owasp-dependency-check-vs-trivy-vs-grype-self-hosted-dependency-scanning/). For threat modeling workflows, check our [Threat Dragon vs ThreatMap comparison](../2026-04-24-owasp-threat-dragon-vs-threatmap-vs-threatsea-self-hosted-threat-modeling-guide-2026/).

## FAQ

### What's the difference between HTML sanitization and output encoding?

Output encoding (also called escaping) converts `<` to `&lt;` so that all HTML appears as plain text. Sanitization parses the HTML and selectively removes dangerous parts while keeping safe formatting intact. Use sanitization when users should be able to format their content (bold, links, lists). Use encoding when displaying user data in HTML attributes or JavaScript contexts where no formatting is expected.

### Can these libraries handle Markdown input?

Not directly. The standard workflow for Markdown user input is: Markdown to rendered HTML, then HTML sanitization. First convert Markdown to HTML using a Markdown renderer, then run the output through the sanitizer. This ensures that even if the Markdown renderer produces dangerous HTML, the sanitizer strips it. Never skip the sanitization step — Markdown renderers vary in their security hardening, and some allow raw HTML passthrough.

### How do I handle SVG files in user uploads?

SVG files are particularly dangerous because they can contain script tags, event handlers, and javascript: URLs. Most HTML sanitizers don't handle standalone SVG files well. Use a dedicated SVG sanitizer or DOMPurify with SVG mode. Always serve user-uploaded SVGs from a separate origin (e.g., user-content.example.com) to isolate them from your main application's cookie scope.

### Why is NH3 faster than Bleach despite both being usable from Python?

NH3 is written in Rust and compiled to native code, while Bleach runs in the Python interpreter. NH3's parser (lol-html) is a streaming HTML rewriter that processes bytes in a single pass with minimal allocations. Bleach uses html5lib which builds a full DOM tree in Python objects. For high-traffic applications sanitizing thousands of HTML fragments per second, NH3's 10-50x performance advantage translates directly to lower infrastructure costs.

### Can I use sanitize-html in browser-side code?

Yes, sanitize-html works in browser environments when bundled with webpack, Rollup, or esbuild. However, for browser-only use cases, consider DOMPurify which is specifically optimized for the browser DOM and has a smaller bundle size (approximately 15KB gzipped vs 50KB for sanitize-html). Server-side sanitization is always recommended as the primary defense — client-side sanitization should be considered a convenience, not a security boundary.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HTML Sanitizer Libraries for XSS Prevention: Bleach vs HTML Purifier vs sanitize-html vs NH3",
  "description": "Compare open-source HTML sanitization libraries across Python, PHP, JavaScript, and Rust. Code examples, security considerations, and deployment patterns for XSS prevention in user-generated content.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
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
