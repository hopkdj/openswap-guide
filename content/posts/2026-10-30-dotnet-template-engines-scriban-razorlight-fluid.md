---
title: "Scriban vs RazorLight vs Fluid in 2026: The .NET Template Engine That Won't Bite You"
date: "2026-10-30"
tags: ["dotnet", "csharp", "templating", "email", "reporting", "developer-tools"]
draft: false
cover: "/img/screenshots/scriban-logo.png"
---

Sooner or later every .NET service needs to turn data into text: an invoice PDF header, a password-reset email, a nightly report, a webhook payload with a human-readable body. The first version is always string concatenation, then a `StringBuilder`, then a bug where a customer's name contains an ampersand and the email renders broken HTML. That is when you reach for a template engine — and discover that the three obvious choices disagree about the thing that matters most: **who is allowed to write the template.**

**Scriban** (3,986 stars) is a Lua-inspired engine with a fast parser and a rich function library. **Fluid** (1,790) implements Shopify's Liquid semantics faithfully. **RazorLight** (1,666) lets you render `.cshtml` files outside ASP.NET Core — a genuinely useful trick with a serious catch: *Razor templates are C# code*. If a template can come from a user, an admin panel, or a database row, RazorLight is remote code execution with extra steps.

There is also a maintenance signal worth knowing before you commit: **RazorLight's last push to GitHub was July 2024** — over two years stale as of this writing — while Scriban (October 2026) and Fluid (October 2026) are both actively developed.

## TL;DR — The 30-Second Verdict

**Use Scriban when you control the templates and want the most capable engine.** Best-in-class loops, filters, and built-in functions, fast parsing, and a clean object-model binding. It does *not* HTML-escape by default, so you must be deliberate about output encoding.

**Use Fluid when templates might be user-editable.** Liquid's semantics are deliberately restricted — no arbitrary method calls, no object graph traversal beyond what you expose — which makes it the only one of the three that is defensible as a multi-tenant feature.

**Use RazorLight only for developer-authored views** where you want Razor syntax (`@Model.Name`, `@foreach`) outside of MVC. Accept that template changes require a deploy, and never feed it user input.

## Side-by-Side Comparison

| Dimension | Scriban | Fluid | RazorLight |
|---|---|---|---|
| GitHub stars | 3,986 | 1,790 | 1,666 |
| License | BSD-2-Clause | MIT | MIT |
| Last push | 2026-10-24 | 2026-10-30 | 2024-07-06 (stale) |
| Syntax family | Liquid-like + Lua extensions | Shopify Liquid | Razor (C#) |
| Compilation model | Parse to AST, render | Parse to AST, render | Compile C# at runtime |
| HTML escaping | Opt-in (`html.escape`) | Opt-in (`escape` filter) | Automatic for `@expr` |
| Safe for user templates | No (functions may reach host objects) | **Yes, with a restricted model** | **Never** |
| Ahead-of-time / trimming safe | Yes | Yes | No (runtime compilation) |
| Layouts & partials | `include`, `extends` | `render`, sections | Layouts, partials, tag helpers |
| Best at | Reports, config generation, codegen | Multi-tenant emails, user themes | Developer-owned views |

## Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Transactional emails authored by your team | **Scriban** | Fast, no runtime compilation, rich filters |
| Customers can upload/edit their own email templates | **Fluid** | Liquid's restricted semantics; no code execution path |
| Migrating `.cshtml` views out of an MVC monolith | **RazorLight** | Reuses Razor syntax and existing views |
| Generating code or config files in a CLI tool | **Scriban** | Loop/function library beats string building |
| Publishing as AOT/trimmed single-file binary | **Scriban or Fluid** | RazorLight needs the C# compiler at runtime |
| Templates change weekly without a redeploy | **Fluid** (or Scriban with a cache) | Templates are data; keep them out of the build |

## Scriban — The Capable Generalist

Scriban parses a template into an AST and renders it against any object. The canonical usage is two lines:

```csharp
using Scriban;

var template = Template.Parse("Hello {{ name }}! You have {{ orders | array.size }} pending orders.");
var result = template.Render(new { name = "Ada", orders = new[] { 1041, 1042, 1043 } });
// Hello Ada! You have 3 pending orders.
```

For real invoices you want loops and formatting, which is where Scriban pulls ahead of the other two:

```csharp
var source = """
{{ for line in invoice.Lines }}
  {{ line.Sku }}  {{ line.Quantity }} x {{ line.UnitPrice | math.format "0.00" }} = {{ line.Total | math.format "0.00" }}
{{ end }}
Total: {{ invoice.Total | math.format "0.00" }} {{ invoice.Currency }}
""";

var parsed = Template.Parse(source);
var context = new TemplateContext { LoopLimit = 10_000 };
var body = parsed.Render(new { invoice = invoiceModel });
```

Two production notes. First, `Template.Parse` is the expensive part — parse once at startup, cache the `Template` instance, and render per request. Second, **Scriban emits raw text**: if `invoice.CustomerName` contains a raw `<`, it goes straight into your HTML. Escape explicitly with `{{ customer_name | html.escape }}`, or render to plain text instead of HTML.

Scriban also supports `include` and `extends`, so a shared `_layout.scriban` with per-report bodies works exactly as you would hope.

## Fluid — Liquid, and the Safety That Comes With It

Fluid implements Liquid: a deliberately limited language designed so that untrusted authors cannot reach your runtime. There are no method calls, no reflection, and no way to ask for `System.IO.File` — the template can only touch values you put into the context.

```csharp
using Fluid;

var parser = new FluidParser();
if (parser.TryParse("Hello {{ customer.name }}, your order {{ order.id }} ships {{ order.date | date: '%B %d' }}.", out var template, out var error))
{
    var context = new TemplateContext();
    context.SetValue("customer", new { name = "Ada" });
    context.SetValue("order", new { id = 1042, date = DateTime.UtcNow });

    var html = await template.RenderAsync(context);
}
else
{
    throw new InvalidOperationException($"Template parse error: {error}");
}
```

Custom filters are how you extend it without widening the attack surface:

```csharp
context.Filters.AddFilter("money", (input, arguments, ctx) =>
{
    var amount = input.ToNumberValue();
    var currency = arguments.At(0).ToStringValue();
    return new StringValue($"{amount:0.00} {currency}");
});
```

Fluid's `TryParse` pattern is important: templates often come from a database, so a malformed template must fail at save time, not at send time. Validate on write, cache the parsed `IFluidTemplate`, and store the version alongside the row.

The trade-off is expressiveness. Liquid has no `while`, no arbitrary functions, and awkward string handling. If an author needs "join these three fields and title-case the result", you will be writing a custom filter — which is precisely the point: every capability is one you granted on purpose.

## RazorLight — Razor Outside MVC

RazorLight compiles `.cshtml` files with the Razor engine and caches the resulting delegates in memory. It is the fastest way to reuse existing Razor views in a worker service or console app.

```csharp
using RazorLight;

var engine = new RazorLightEngineBuilder()
    .UseFileSystemProject(Path.Combine(AppContext.BaseDirectory, "Templates"))
    .UseMemoryCachingProvider()
    .Build();

var html = await engine.CompileRenderAsync("Invoice.cshtml", invoiceModel);
```

The view itself is plain Razor:

```cshtml
@model InvoiceModel
<h1>Invoice @Model.Number</h1>
<ul>
@foreach (var line in Model.Lines)
{
    <li>@line.Sku — @line.Quantity × @line.UnitPrice.ToString("0.00")</li>
}
</ul>
<p>Total: @Model.Total.ToString("0.00") @Model.Currency</p>
```

Note what `@Model.Total` implies: a Razor template is compiled C#. Once a `.cshtml` file is under someone else's control, that someone can call arbitrary code reachable from the model. There is no sandbox flag that makes this safe. Treat template files with the same trust level as your source code — because functionally, they are source code.

The second constraint is architectural. RazorLight needs the C# compiler available at runtime, which means it does not survive `PublishAot`, aggressive trimming, or a minimal chiseled runtime image. If your deployment target is a 60 MB trimmed container, RazorLight is not an option.

## Deploying a Renderer Service

A dedicated renderer is the cleanest way to isolate template execution. This Dockerfile publishes a trimmed ASP.NET Core renderer with templates copied as content:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish src/Renderer/Renderer.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app/publish .
COPY templates ./templates
ENV TEMPLATE_ROOT=/app/templates
ENTRYPOINT ["dotnet", "Renderer.dll"]
```

```yaml
services:
  renderer:
    build: .
    environment:
      TEMPLATE_ROOT: /app/templates
      TemplateCache__MaxEntries: "2000"
    ports:
      - "8080:8080"
    read_only: true
    tmpfs:
      - /tmp
```

The `read_only: true` line is not decoration. A template renderer that cannot write to disk cannot be turned into a persistence foothold by a template that manages to call into the host — a cheap, effective blast-radius control that costs nothing.

## Pitfalls That Actually Cause Incidents

**Caching parsed templates is mandatory.** Parsing on every request is 5-50× slower than rendering, and under load it turns a CPU-bound service into a queue. Cache the `Template` (Scriban) or `IFluidTemplate` (Fluid) keyed by template name plus a content hash so edits invalidate automatically.

**RazorLight's cache is a memory leak if templates are dynamic.** Each distinct template string compiles to a new in-memory assembly that is never unloaded. Generate templates from user data and you will OOM in production, usually within days.

**No engine HTML-escapes by default except Razor.** Scriban and Fluid both emit raw strings. One unescaped `&` is cosmetic; one unescaped `<` from a customer name is a broken email; one unescaped `<` followed by markup in a web view is an injection.

**Culture-dependent number formatting causes support tickets.** `{{ total }}` renders `1,234.50` in one locale and `1.234,50` in another depending on the context culture. Pin `CultureInfo.InvariantCulture` for machine-consumed output and set the culture explicitly for human-facing currency.

**Parse errors must fail at authoring time.** Validate templates when they are saved (`TryParse`), store a `compiled_version` column, and refuse to publish templates that fail. Discovering a Liquid syntax error while sending a password reset is unrecoverable.

**Loops need a budget.** Scriban's `LoopLimit` and Fluid's iteration limits exist for a reason: an accidental cross-join over 10,000 rows in a nested template will pin a CPU core and blow the response timeout.

**Email HTML is not browser HTML.** Gmail strips `<style>` blocks and Outlook ignores flexbox. Whatever engine you pick, run the output through an inliner (or use table-based layouts), and test in the clients your customers actually use.

## FAQ

### Which .NET template engine is fastest?

Scriban and Fluid are both AST-based and render in microseconds per small template, far faster than a runtime-compiled Razor view. RazorLight has a high first-render cost (it compiles C#) and is competitive only when its cache hits. For high-volume email, Scriban is the usual choice; benchmark with your own templates, because filter-heavy Liquid can lose to Scriban's built-in functions.

### Can I let users write templates with Scriban?

Not safely without substantial work. Scriban exposes host objects and functions to the template, and the surface is broad enough that a determined author can reach things you did not intend. If multi-tenant template authoring is a requirement, use Fluid or a restricted Scriban configuration with an allow-listed function set and no access to host types.

### Is RazorLight abandoned?

Its repository has not been pushed to since July 2024, while Scriban and Fluid both shipped commits in October 2026. "Abandoned" is a strong word for a stable library, but the practical risk is real: no fixes for new .NET runtime versions, and no response if a Razor compilation issue appears after an SDK upgrade. Prefer it for internal tooling, not for new long-lived services.

### How do these engines handle layouts and partials?

Scriban uses `include 'partial'` and `extends 'layout'`. Fluid uses `{% render 'partial' %}` and `{% layout 'layout' %}`. RazorLight supports Razor layouts and partials, but partial resolution outside MVC requires configuring the file project root correctly — a common source of "view not found" errors.

### Do I need a template engine for JSON output?

No. Use `System.Text.Json` with source generation. Template engines are for text where whitespace and formatting are part of the specification: emails, reports, invoices, config files, and code. Using Liquid to build JSON is how you end up with trailing-comma bugs that no schema validator catches.

### Can these run inside a trimmed or native AOT container?

Scriban and Fluid can. RazorLight cannot, because it depends on runtime Roslyn compilation. If your deployment strategy is chiseled containers or single-file AOT binaries, that constraint alone decides the choice.

For adjacent reading, see our [Mjml email template rendering guide](../2026-05-14-self-hosted-email-template-rendering-mjml-server-api-handlebars-guide/), the [Java template engine comparison](../2026-07-25-java-template-engines-thymeleaf-freemarker-jte-rocker/), and the [Go template engine roundup](../2026-08-20-go-template-engines-pongo2-fasttemplate-quicktemplate-comparison/) — the same trade-offs between expressiveness and safety appear in every language.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Scriban vs RazorLight vs Fluid in 2026: The .NET Template Engine That Won't Bite You",
  "description": "Scriban, Fluid and RazorLight compared for .NET in 2026: real rendering code, caching strategy, HTML escaping defaults, sandboxing for user-authored templates, AOT and trimming constraints, and the pitfalls that break production email rendering.",
  "datePublished": "2026-10-30",
  "dateModified": "2026-10-30",
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
