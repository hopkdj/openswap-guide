---
title: "Saxon-HE vs libxslt vs lxml vs Xalan in 2026: Which XSLT Processor Should You Actually Use?"
date: "2026-10-11"
tags: ["xml", "developer-tools", "libraries", "data-engineering", "document-processing"]
draft: false
cover: "/img/screenshots/saxon-logo.jpg"
---

XSLT gets declared dead roughly once a decade, and roughly once a decade it turns out to be load-bearing under something unglamorous: bank payment mapping, government document standards, publishing pipelines, and any system that has to turn one XML dialect into another without a bespoke parser per counterparty. If you have ever had to produce ISO 20022 messages, transform JATS or DocBook, or generate print-ready output from structured content, you have been one stylesheet away from this decision.

The problem is that XSLT is not one language in practice. **XSLT 1.0 and XSLT 3.0 are effectively different languages**, and the four processors that matter in 2026 split hard along that line. Choosing the wrong one means discovering, three weeks in, that `xsl:for-each-group` simply does not exist in your processor.

## The 30-Second Verdict

- **You need XSLT 2.0 or 3.0 features — grouping, higher-order functions, maps, arrays, streaming:** use **Saxon-HE**. It is the only maintained open-source XSLT 3.0 processor, and there is no serious competitor.
- **You are in a C/C++ stack, or your Python project already depends on lxml:** use **libxslt** (directly or through lxml). Fast, mature, but **XSLT 1.0 only**.
- **You want XSLT inside a Python application with good error reporting:** use **lxml**. It is a binding over libxslt, so the same 1.0 ceiling applies.
- **You are maintaining a legacy Java integration that already uses Xalan:** keep it, but stop starting new work on it — the project is in maintenance and the repositories are mirrors.

One sentence: *Saxon-HE if you write modern stylesheets, libxslt or lxml if XSLT 1.0 is enough, Xalan only for legacy Java.*

## Quick Comparison: Four XSLT Processors in 2026

Repository statistics were pulled live from GitHub at publish time. Note that libxslt, Xalan-J, and Saxon-HE repositories are the project's public mirrors, so star counts understate real-world usage.

| Processor | Language / binding | XSLT version | Repo stars | Last activity | License |
|---|---|---|---|---|---|
| **Saxon-HE** | Java, .NET, C (SaxonC) | **3.0** (+ XPath 3.1) | 178 | Jul 2026 | MPL-2.0 |
| **libxslt** | C library (`xsltproc` CLI) | 1.0 | 73 | Oct 2026 | MIT |
| **lxml** | Python binding to libxml2/libxslt | 1.0 | 3,065 | Oct 2026 | BSD-3 |
| **Xalan-J** | Java | 1.0 | 26 | May 2026 | Apache-2.0 |

Two facts dominate everything else in this table. **Saxon-HE is the only processor here implementing XSLT 3.0.** And **lxml inherits libxslt's 1.0 ceiling** — the most popular Python XML library cannot run a modern stylesheet, no matter how convenient its API is. That mismatch is the single most common source of "but it worked in my other tool" bug reports.

## Decision Matrix: Pick by What Your Stylesheet Needs

| Your situation | Pick | Why |
|---|---|---|
| Stylesheet uses `xsl:for-each-group`, `xsl:function`, maps or arrays | **Saxon-HE** | XPath 3.1 / XSLT 3.0 is exclusive to Saxon in the open-source space |
| You must transform large documents without loading them fully | **Saxon-HE** | Streaming is a 3.0 feature; nothing else here streams |
| Python app, simple 1.0 templates, minimal dependencies | **lxml** | One wheel, fast C core, excellent error objects |
| C/C++ build, no JVM allowed on the target host | **libxslt** | Small, embeddable, no runtime to ship |
| Shell script batch conversion | **xsltproc** | Zero-config CLI from the libxslt package |
| Legacy Java app already on Xalan | **Xalan-J (keep, don't extend)** | Migration cost is real; new features are not coming |
| Needs XSLT 3.0 without a JVM | **SaxonC** | Saxon's C/C++/Python bindings |

## Saxon-HE — The Only Modern XSLT Processor

If your stylesheet needs anything from XSLT 2.0 or 3.0, this is not a comparison — Saxon-HE is the only open-source option. Grouping, user-defined functions, sequences, maps and arrays, `xsl:analyze-string`, higher-order functions, and streaming all live here. The commercial editions (Saxon-EE) add schema-awareness and the full streaming implementation, but a large majority of real integration work fits inside HE.

Installing it depends on your runtime:

```bash
# Java: Maven coordinates (Saxon-HE 12.x line)
#   <dependency>
#     <groupId>net.sf.saxon</groupId>
#     <artifactId>Saxon-HE</artifactId>
#     <version>12.5</version>
#   </dependency>

# .NET
dotnet add package Saxon-HE

# .NET CLI package installed, run a transformation directly
java -jar Saxon-HE-12.5.jar -s:input.xml -xsl:transform.xsl -o:output.html
```

A stylesheet that simply cannot run anywhere else — grouping with `xsl:for-each-group` and a user-defined function:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xsl:function name="local:vat" as="xs:decimal">
    <xsl:param name="net" as="xs:decimal"/>
    <xsl:sequence select="round($net * 0.19 * 100) div 100"/>
  </xsl:function>

  <xsl:template match="/orders">
    <table>
      <xsl:for-each-group select="order" group-by="@customer">
        <tr>
          <th><xsl:value-of select="current-grouping-key()"/></th>
          <td><xsl:value-of select="sum(current-group()/@total)"/></td>
          <td><xsl:value-of select="local:vat(sum(current-group()/@total))"/></td>
        </tr>
      </xsl:for-each-group>
    </table>
  </xsl:template>
</xsl:stylesheet>
```

Operationally, two Saxon details matter at scale. First, **external function calls and the `document()` network fetch are gated**; allow them deliberately (`ALLOW_EXTERNAL_FUNCTIONS` via the API) rather than discovering that a stylesheet can reach the network by default in a hardened deployment. Second, **style a compile-once pattern**: instantiate the `XsltCompiler`/`Processor` once and reuse the compiled `XsltExecutable`, because compiling a large stylesheet dominates the cost of small transformations.

## libxslt and xsltproc — Small, Fast, and Permanently 1.0

libxslt is the C workhorse behind an enormous amount of plumbing. Its companion CLI, `xsltproc`, is the fastest way to run a 1.0 stylesheet from a shell, and the same package back-ends lxml, PHP's ext-xsl, and several CMS pipelines.

```bash
# Debian / Ubuntu: library, headers and xsltproc
sudo apt install libxslt1-dev xsltproc

# Straightforward file-to-file transform
xsltproc --output report.html report.xsl data.xml

# Passing parameters from the shell — the quoting rules matter
xsltproc --stringparam reportDate 2026-10-11 --output report.html report.xsl data.xml
```

The hard limitation, restated because it causes most of the pain: **libxslt implements XSLT 1.0.** No grouping, no sequences, no user-defined functions. What you get instead is EXSLT extensions — widely supported, but a different API surface, and `node-set()` casting gymnastics for anything involving result-tree fragments.

Security deserves a deliberate sentence. libxslt has accumulated memory-safety fixes over the years, including a batch of CVEs patched in 2025, and it is a parser of untrusted input by definition. Pin a patched version, and follow the project's guidance on disabling network access for the transformation context; the same discipline that applies to any XML parser applies to stylesheets, which can fetch remote resources unless told not to.

## lxml — The Python Path (With the Same Ceiling)

lxml is the de facto Python interface for XML, and its XSLT support is a thin, high-quality binding over libxslt. If your templates are 1.0, this is the pleasant way to run them: fast C core, real error objects, no subprocess per document.

```bash
python3 -m pip install lxml
```

```python
from lxml import etree

# Parse with defensively hardened settings — no network, no external entities
parser = etree.XMLParser(resolve_entities=False, no_network=True)

xslt_root = etree.parse("report.xsl", parser)
transform = etree.XSLT(xslt_root)

source = etree.parse("data.xml", parser)
result = transform(source, report_date="2026-10-11")

# Check the error log even when output looks plausible
if transform.error_log:
    for entry in transform.error_log:
        print(entry.level_name, entry.line, entry.message)

print(str(result)[:400])
```

Two practical notes. Passing parameters through `transform(...)` as keyword arguments is the clean way, but every parameter arrives as a string unless you use `XSLT.strparam` or `etree.XPath`-style typed wrappers — a frequent source of "why is my numeric comparison failing" bugs. And because lxml cannot do 3.0, teams that outgrow it face a real migration: rewriting the stylesheet *and* changing the runtime, since Saxon requires a JVM (or the SaxonC bindings).

## Xalan-J — Legacy Java, Maintained But Not Growing

Xalan-J is the XSLT 1.0 processor that shipped inside countless Java stacks via the JAXP `TransformerFactory` default. Its GitHub repository is a mirror, activity is minimal, and no XSLT 2.0 or 3.0 support ever materialised. That does not make it broken — it makes it frozen.

```bash
# Command-line invocation with the classic Xalan packaging
java -cp xalan.jar org.apache.xalan.xslt.Process \
     -IN data.xml -XSL report.xsl -OUT report.html
```

The pragmatic guidance is simple. **Do not start a new project on Xalan.** If you are already on JAXP defaults, check which implementation you are actually loading — `TransformerFactory.newInstance()` may be Xalan or the JDK's internal XSLTC depending on classpath order, and the two differ on extension functions. When you do migrate, Saxon-HE is a drop-in-ish replacement for 1.0 stylesheets *and* unlocks 2.0/3.0, which is why it is the standard target for Java teams leaving Xalan.

## Why Run Your Own Transformation Pipeline?

XSLT pipelines are one of the last places where organisations still pay per-document SaaS pricing for something that is genuinely a few hundred kilobytes of library. Document generation, invoice mapping, publishing output, and standards conversion are all deterministic transformations with no network dependency — the ideal workload to run on your own hardware.

Self-hosting the transformation layer also removes the quiet supply-chain risk of handing structured business documents (payroll, invoices, patient records, payment messages) to a third-party rendering service. A container with Saxon-HE or libxslt, a read-only stylesheet directory, and no outbound network is a small, auditable component. For the wider picture, our [markdown parser libraries comparison](../2026-06-20-markdown-parser-libraries-pulldown-cmark-goldmark-comrak-commonmarkjs/) covers the other half of most publishing pipelines, the [expression languages comparison](../2026-09-27-expression-languages-cel-go-expr-lang-jsonata-starlark-comparison/) is the modern alternative when your transformation needs are simple mapping rather than full tree restructuring, and if your XSLT output is transactional email, the [self-hosted email template rendering guide](../2026-05-14-self-hosted-email-template-rendering-mjml-server-api-handlebars-guide/) is the natural next step.

The architecture that ages well: **compile the stylesheet once, keep it in version control next to its unit tests, and run the transformation in a container with no network access.** Golden-file tests — input XML plus expected output XML — catch the 1.0-versus-3.0 class of failures before they reach production, which is a far cheaper place to find them.

## Common Pitfalls and Migration Notes

**1. The 1.0 ceiling is not negotiable.** libxslt, lxml, and Xalan will not run `xsl:for-each-group`, `xsl:function`, or any 2.0/3.0 construct. If the stylesheet is modern, the processor is Saxon — plan for a JVM or the SaxonC bindings.

**2. `TransformerFactory` implementation is classpath-dependent on the JVM.** Two machines running "the same" Java code can use different XSLT engines. Log `factory.getClass().getName()` once and be certain.

**3. Parameters arrive as strings.** XSLT has no implicit numeric coercion from an external parameter. Convert explicitly (`number($limit)`) or the comparison will compare lexical values.

**4. Result-tree fragments break 1.0 code.** The `node-set()` EXSLT extension is required to treat a generated fragment as a node set, and it is a common hidden portability trap between processors.

**5. Stylesheets can reach the network.** `document()` fetches remote documents. In a hardened deployment, disable network access in the parser configuration and gate external functions explicitly rather than assuming the default is safe.

**6. Compile cost dominates small transformations.** Reusing a compiled stylesheet can be an order-of-magnitude win when you process thousands of small documents. Never recompile per document.

**7. Memory grows with document size, not stylesheet complexity.** Non-streaming processors build the whole input tree. For very large inputs, streaming (a Saxon feature) is not an optimisation — it is the only way the transformation completes at all.

**8. Pin libxslt.** It parses untrusted input and has a history of memory-safety fixes, including a substantial batch in 2025. Distribution packages lag; know which version you ship.

## FAQ

**Can lxml run XSLT 2.0 or 3.0 stylesheets?**
No. lxml is a binding over libxslt, which implements XSLT 1.0 (plus a subset of EXSLT). Anything using `xsl:for-each-group`, `xsl:function`, sequences, or maps requires Saxon-HE, and if you are in Python that means the SaxonC bindings or a subprocess invoking the JVM.

**Is XSLT still worth learning in 2026?**
Yes, in a specific domain: structured document transformation where the input and output are both XML-ish and the mapping is declarative. Standards-driven work (payments, publishing, government document formats) still expects it. For general-purpose data mapping, modern expression languages are usually the better fit.

**What is the fastest XSLT processor?**
For XSLT 1.0 templates, libxslt and lxml are very fast and have a small memory footprint. For 2.0/3.0 work, Saxon-HE is the only option and its performance is dominated by stylesheet compilation and by whether you use keys (`xsl:key`) instead of repeated XPath scans. Benchmark your own stylesheet — the differences are workload-specific.

**How do I convert an XSLT 1.0 stylesheet to work with Saxon?**
In most cases it runs as-is: Saxon-HE is a superset and accepts `version="1.0"` stylesheets. The problems appear where the 1.0 code relied on EXSLT extensions, `node-set()` casting, or vendor-specific behaviour. Port those pieces to native 2.0/3.0 constructs and add golden-file tests around the output.

**Can I avoid running a JVM for XSLT 3.0?**
SaxonC provides C, C++, and Python bindings to the same engine, so you can get XSLT 3.0 support without managing a JVM in your application process. It is still the Saxon codebase, just packaged as a native library with bindings.

**Should I use XSLT at all for JSON-to-JSON mapping?**
Generally no. XSLT 3.0 can do it, but tools purpose-built for the job will be clearer and more maintainable. Reserve XSLT for the case it was designed for: tree-shaped document transformation with a declarative mapping that other people need to read.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Saxon-HE vs libxslt vs lxml vs Xalan in 2026: Which XSLT Processor Should You Actually Use?",
  "description": "A 2026 comparison of the four XSLT processors that matter: Saxon-HE (XSLT 3.0), libxslt and xsltproc (1.0), lxml for Python, and legacy Xalan-J. Includes install commands, stylesheet examples, security notes and migration guidance.",
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
