---
title: "Java Units of Measurement in 2026: JSR-385 (Indriya) vs Unit-API vs JScience"
date: "2026-09-18"
tags: ["java", "units-of-measurement", "jvm-libraries", "developer-tools", "open-source"]
cover: "/img/screenshots/jsr385-uom-logo.jpg"
draft: false
---

A satellite lands in the wrong orbit because one team wrote pound-force and another read newtons. A billing system charges a customer 1,000x too much because a duration was stored in milliseconds and compared against seconds. A chemical dosing API returns 10 mg instead of 10 µg. These are not exotic failures — they are the default outcome of passing bare `double` values between layers and hoping that everyone agrees on the unit.

Java solved this problem twice. **JSR-275** introduced type-safe quantities in 2005, **JSR-385** (the Units of Measurement API) replaced it with a modern, actively maintained standard — and as of September 2026 there are exactly three moving parts you need to know about: **Indriya 2.2.3** (the reference implementation), the **Unit-API 2.2** interfaces, and the legacy **JScience 4.3.1**. This guide compares all three with live version data, real Maven coordinates, and code you can paste into a project today.

## TL;DR — Quick Verdict

**Use Indriya 2.2.3 behind the JSR-385 API.** It is the only candidate with an active release cadence (last commit **August 25, 2026**), JPMS module descriptors, UCUM parsing, and reference-implementation status that makes it the safe long-term default. **If you are publishing a library** that must not impose an implementation on downstream users, depend on `javax.measure:unit-api:2.2` alone and let the consumer choose Indriya. **Do not start new work on JScience 4.3.1** — its last release predates Java 9, its GitHub mirror has been frozen since **September 2017**, and it forces the obsolete JSR-275 `javax.measure.unit` package onto your classpath, which actively conflicts with the modern API.

If you are tired of unit-mismatch bugs in production, the migration cost is typically an afternoon for a single service and pays back within the first incident you prevent.

## Side-by-Side Comparison: JSR-385 Implementations in 2026

| Dimension | Indriya 2.2.3 | Unit-API 2.2 | JScience 4.3.1 |
|---|---|---|---|
| Role | Reference implementation | API + interfaces only | Legacy all-in-one library |
| Maven coordinates | `tech.units:indriya:2.2.3` | `javax.measure:unit-api:2.2` | `org.jscience:jscience:4.3.1` |
| GitHub repository | unitsofmeasurement/indriya | unitsofmeasurement/unit-api | javolution/jscience (mirror) |
| Stars | 140 | 195 | 97 |
| Last commit | 2026-08-25 | 2026-07-06 | 2017-09-10 |
| Latest release | 2.2.3 | 2.2 | 4.3.1 (2011) |
| Relevant standard | JSR-385 2.x | JSR-385 2.x | JSR-275 lineage |
| API package | `javax.measure.*` | `javax.measure.*` | `javax.measure.*` (incompatible) |
| JPMS `module-info` | Yes | Yes | No |
| UCUM parsing / formatting | Yes (`UCUMFormat`) | N/A (API only) | Partial |
| Custom unit support | `alternate`, `shift`, `multiply` | Interfaces declared | Custom `Unit` subclasses |
| License | Other (see repo LICENSE) | Other (see repo LICENSE) | Other (see repo LICENSE) |
| Maintenance status | **Active** | **Active** | **End of life** |

The star counts are deliberately included to make a point: unit libraries are infrastructure, not fashion. Low star counts here reflect how much teams take dimensional safety for granted — the dependency is downloaded millions of times through enterprise builds rather than starred by hobbyists.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Choose | Why |
|---|---|---|
| New service, you control the whole build | Indriya 2.2.3 + unit-api 2.2 | Reference implementation under active maintenance |
| Writing a public library or SDK | `javax.measure:unit-api` only | Consumers pick the implementation; no transitive lock-in |
| Parsing units from config files, FHIR payloads, or user input | Indriya with `UCUMFormat` | Only candidate with a real UCUM parser |
| Legacy project already on JScience | Stay, but isolate the classpath | Rewriting is cheap, but only if you can pin dependencies |
| Scientific computing with decimal precision | Indriya plus a decimal-backed quantity | Dimensional checks still apply, rounding does not |
| Embedded or Android with an old toolchain | Unit-API interfaces + Indriya if the baseline allows | JScience's Javolution dependency is the bigger problem |

## Indriya 2.2.3 — The Reference Implementation

Indriya is the implementation that the JSR-385 expert group points at when someone asks "what does correct look like?" It ships the full API, quantity types, arithmetic with dimensional reduction, formatting, and UCUM support.

Add it to a Maven build:

```xml
<dependency>
  <groupId>tech.units</groupId>
  <artifactId>indriya</artifactId>
  <version>2.2.3</version>
</dependency>
<dependency>
  <groupId>javax.measure</groupId>
  <artifactId>unit-api</artifactId>
  <version>2.2</version>
</dependency>
```

The core workflow is quantity arithmetic with automatic unit normalisation:

```java
import javax.measure.Quantity;
import javax.measure.quantity.Length;
import javax.measure.quantity.Speed;
import tech.units.indriya.quantity.Quantities;
import tech.units.indriya.unit.Units;

Quantity<Length> track = Quantities.getQuantity(400, Units.METRE);
Quantity<Length> lap   = Quantities.getQuantity(2.5, Units.KILOMETRE);

System.out.println(track.add(lap));       // 2900 m
System.out.println(lap.to(Units.METRE));  // 2500 m

Quantity<Speed> pace = track
    .divide(Quantities.getQuantity(50, Units.SECOND))
    .asType(Speed.class);

System.out.println(pace.to(Units.KILOMETRE_PER_HOUR)); // 28.8 km/h
```

Two things are worth noticing. First, `track.add(lap)` returns **2900 m** — Indriya normalises to the unit of the left operand instead of silently mixing scales. Second, `divide` produces a dimensionally reduced quantity that you explicitly cast to `Speed`; the runtime verifies that metres per second really is a speed and throws if it is not.

The part that saves the most production time is **parsing**. Configuration files, CSV imports, and API payloads rarely contain SI symbols written in Java-friendly form — they contain UCUM strings authored by humans:

```java
import javax.measure.Unit;
import tech.units.indriya.format.UCUMFormat;

Unit<?> flowRate = UCUMFormat.getCaseSensitiveInstance().parse("mL/min");
Unit<?> pressure = UCUMFormat.getCaseSensitiveInstance().parse("kg.m/s2");

System.out.println(flowRate); // mL/min
System.out.println(pressure); // kg·m/s²
```

Custom units — the barrels, pallets, and BTUs that every logistics or energy codebase invents — are declared in one line and immediately participate in arithmetic and dimensional checking:

```java
import javax.measure.Unit;
import javax.measure.quantity.Volume;
import tech.units.indriya.unit.Units;

Unit<Volume> BARREL = Units.LITRE.multiply(159).alternate("bbl");

Quantity<Volume> shipment = Quantities.getQuantity(3, BARREL);
System.out.println(shipment.to(Units.LITRE)); // 477 L
```

![JSR-385 Units of Measurement API project logo](/img/screenshots/jsr385-uom-logo.jpg "JSR-385 Units of Measurement API — the standard implemented by Indriya")

## Unit-API 2.2 — When You Only Need the Interfaces

`javax.measure:unit-api:2.2` contains the specification types: `Quantity`, `Unit`, `UnitFormat`, `Units`, `Dimension`, and the editable `SystemOfUnits` interface. It contains no arithmetic engine. That is not a deficiency — it is the point.

If you maintain a library that models measurements (a pricing engine that takes a volume, a scheduling library that takes a duration, an SDK for hardware that reports temperatures), depending on the API alone means your users install exactly one implementation and your artifact never drags Javolution, a duplicate `javax.measure`, or an outdated transitive graph into their build.

```xml
<dependency>
  <groupId>javax.measure</groupId>
  <artifactId>unit-api</artifactId>
  <version>2.2</version>
  <scope>compile</scope>
</dependency>
```

```java
import javax.measure.Quantity;
import javax.measure.quantity.Temperature;

public final class Reading {

    private final Quantity<Temperature> value;

    public Reading(Quantity<Temperature> value) {
        this.value = value;
    }

    public Quantity<Temperature> inKelvin() {
        return value.to(javax.measure.unit.Units.KELVIN);
    }
}
```

The trade-off is honest: the API module gives you type declarations and conversion contracts, but you cannot construct quantities without an implementation on the runtime classpath. In tests, add Indriya as a test-scoped dependency and you get a complete, standards-compliant environment without leaking it to consumers.

Both `unit-api` and `indriya` publish JPMS module descriptors, so on Java 11+ the split is clean:

```java
module com.example.telemetry {
    requires tech.units.indriya;
    exports com.example.telemetry.reading;
}
```

## JScience 4.3.1 — The Legacy Option and Its Real Costs

JScience is the library that inspired the standard. It introduced `Amount`, a quantity type with arbitrary precision support, and a rich set of physics modules. Its `Amount` API is genuinely pleasant:

```java
import org.jscience.physics.amount.Amount;
import javax.measure.unit.SI;
import javax.measure.quantity.Length;

Amount<Length> distance = Amount.valueOf(400, SI.METRE);
Amount<Length> lap = Amount.valueOf(2.5, SI.KILOMETRE);

System.out.println(distance.plus(lap));   // 2900 m
System.out.println(distance.to(SI.METRE));
```

The problem is everything around it. The last Maven release, **4.3.1**, dates from 2011. The GitHub mirror `javolution/jscience` has not received a commit since **September 10, 2017** and carries 97 stars. It depends on Javolution, a Java 5-era utility library, and it targets the **JSR-275** package layout: `javax.measure.unit.SI`, `javax.measure.unit.Unit`, and `javax.measure.quantity.Measurable`.

That last detail is the one that breaks builds. JSR-385 deliberately kept the `javax.measure` namespace while changing the contents — `Measurable` was replaced by `Quantity`, `SI` by `Units`, and the conversion API was rewritten. Put JScience and unit-api on the same classpath and you get one of the least pleasant debugging experiences in the ecosystem: classes that resolve, compile, and then fail at runtime with `NoSuchMethodError` or `ClassCastException` because two different libraries claim the same package.

If you must keep JScience alive for a legacy service, isolate it: keep it out of any module that also uses JSR-385, pin the dependency with an explicit version, and add an ArchUnit or enforcer rule that fails the build if both appear in the same dependency set.

## Real-World Patterns: JSON, Decimals and Boundaries

**Serialising quantities to JSON.** There is no universally adopted Jackson module, so the reliable pattern is a small custom serializer that writes both the numeric value and the unit symbol — never a naked number:

```java
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import javax.measure.Quantity;
import tech.units.indriya.format.SimpleUnitFormat;

public final class QuantityModule extends SimpleModule {

    public QuantityModule() {
        addSerializer(Quantity.class, new JsonSerializer<Quantity<?>>() {
            @Override
            public void serialize(Quantity<?> value, JsonGenerator gen,
                                  SerializerProvider provider) throws java.io.IOException {
                gen.writeStartObject();
                gen.writeNumberField("value", value.getValue().doubleValue());
                gen.writeStringField("unit",
                        SimpleUnitFormat.getInstance().format(value.getUnit()));
                gen.writeEndObject();
            }
        });
    }
}
```

Consumers then read `{"value":2.5,"unit":"km"}` and reparse it with the same formatter, which keeps the contract stable across services written in different languages.

**Decimal precision.** If your domain is money-adjacent — tariffs per kilowatt-hour, freight per cubic metre — convert late. Keep quantities in the unit they arrived in, do all arithmetic in scaled decimals, and call `to()` exactly once at the boundary. Mixing `double` conversion chains with currency rounding is how teams produce invoices that are off by a cent per line item and auditable to nobody.

**Boundary discipline.** Validate units at the edge of the system. A single `UCUMFormat.parse()` call in a request DTO converts an entire class of user input errors into a clean 400 response instead of a corrupted record.

## Pitfalls, Migration Notes and Performance Traps

- **Duplicate `javax.measure` on the classpath** — the single most common failure. Run `mvn dependency:tree -Dincludes=javax.measure:*` before migrating; if JScience or any JSR-275 artifact appears, exclude it.
- **`Quantity` is immutable, so arithmetic allocates** — in tight loops (millions of conversions per second) that matters. Cache converted quantities, or hoist the conversion out of the loop.
- **Equality is not identity** — `Quantities.getQuantity(1, Units.METRE).equals(Quantities.getQuantity(100, Units.CENTIMETRE))` behaviour depends on the implementation's `equals` contract. Compare normalised values explicitly instead of relying on object equality.
- **Unit symbols are not user-facing strings** — format with `UnitFormat` and translate labels in your presentation layer; do not build UI strings from `unit.toString()`.
- **Don't skip dimensional types to save keystrokes** — using bare `Unit<?>` everywhere throws away the compiler's ability to tell a mass from a length.

## Extending the Ecosystem and Related Reading

Indriya is the engine; the wider UnitsofMeasurement project supplies the vocabulary. **UOM-Lib** provides common abstractions such as quantity types and unit systems, while **UOM-Systems** ships pre-built systems of units (SI, imperial, common, and more) so you do not hand-declare barrel or BTU constants per project.

If your work spans languages, the conceptual model transfers directly. Our comparison of [C++ units of measurement libraries](../2026-06-28-cpp-units-of-measurement-libraries-mp-units-nholthaus-boost-units/) covers the same dimensional-safety trade-offs with compile-time enforcement, and the [.NET units of measure libraries guide](../2026-09-17-dotnet-units-of-measure-libraries-unitsnet-quantitytypes-unitgenerator/) shows how UnitsNet structures the same problem for a managed runtime. Teams that adopt dimensional types often do it together with a monetary standard — our [Java money libraries comparison](../2026-09-17-java-money-libraries-moneta-joda-money-jsr354-comparison/) covers JSR-354, Moneta, and Joda-Money, which is the same pattern applied to ISO 4217 currencies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Java Units of Measurement in 2026: JSR-385 (Indriya) vs Unit-API vs JScience",
  "description": "Compare JSR-385 Java units of measurement libraries in 2026: Indriya 2.2.3, the Unit-API 2.2 interfaces, and legacy JScience 4.3.1, with real Maven coordinates and code.",
  "datePublished": "2026-09-18",
  "dateModified": "2026-09-18",
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

**Which Java units of measurement library should I use in 2026?**
Use **Indriya 2.2.3** with `javax.measure:unit-api:2.2`. It is the JSR-385 reference implementation, still receiving commits as of August 2026, and it is the only option with UCUM parsing, JPMS support, and an active release history.

**Is JScience still maintained?**
No. The last Maven release, 4.3.1, dates to 2011, and the GitHub mirror has been dormant since 2017. It also targets the older JSR-275 `javax.measure.unit` layout, which conflicts with modern JSR-385 artifacts on the same classpath.

**Do I need both Indriya and unit-api in my build?**
Indriya depends on the API module, so most applications only declare `tech.units:indriya`. Declaring `javax.measure:unit-api` explicitly is useful when you are writing a library that should let consumers choose the implementation.

**How do I convert a unit string like "mg/dL" that comes from a configuration file?**
Parse it with `UCUMFormat.getCaseSensitiveInstance().parse("mg/dL")`. Indriya returns a `Unit<?>` you can then use with `Quantities.getQuantity(value, unit)` — no manual lookup tables required.

**Does JSR-385 work with Java 17 and later?**
Yes. Both `unit-api` 2.2 and Indriya 2.2.3 ship module descriptors and run on modern JDKs. JScience is the outlier: its Javolution dependency and Java 5-era bytecode make it awkward on recent toolchains, and it has no JPMS support.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
