---
title: "UnitsNet vs QuantityTypes vs UnitGenerator: Picking a .NET Units of Measure Library in 2026"
date: "2026-09-17"
tags: ["dotnet", "csharp", "units-of-measure", "libraries", "type-safety"]
draft: false
cover: "/img/screenshots/unitsnet-logo.jpg"
description: "UnitsNet, QuantityTypes and UnitGenerator compared for .NET in 2026: real NuGet installs, real code, and the unit-conversion bugs each one prevents — or fails to prevent."
---

There is a specific class of production bug that no unit test catches, because the test asserts the wrong thing with total confidence. A spacecraft's ground software loses a probe because pound-force and newton were conflated. A billing pipeline issues refunds in cents where the ledger expected dollars. An engineering dashboard reports a beam's deflection in millimetres and a reviewer signs off because the number looks plausible. Every one of those bugs is a *type* bug: the program had a `double` where it needed a `Length`, and `double` never objects.

.NET's answer has traditionally been "name your variables carefully". In 2026 there are three mature, actively maintained libraries that make the compiler do the work instead: **UnitsNet**, **QuantityTypes** and **UnitGenerator**. They solve the problem at three genuinely different layers, and choosing the wrong layer is how teams end up with a 400-file refactor they did not need.

## TL;DR — Quick Verdict

Take **UnitsNet** (2,969 stars, last pushed August 2026) for almost everything. It is the only one of the three with per-unit properties, culture-aware parsing and formatting, dynamic runtime lookup, and serialization support — the boring completeness that production code actually needs. Take **QuantityTypes** (93 stars) if you want a tiny, dependency-free, value-type library that aligns with ISO 80000 and you are happy to live with a smaller unit catalogue. Take **UnitGenerator** (400 stars) when your problem is not physics at all but domain primitives — `UserId`, `OrderId`, `Celsius` as a generated readonly struct — and you want a Roslyn source generator to produce the boilerplate.

If you only ever convert kilometres to miles in one helper method, use `const double` and move on; none of these libraries earn their dependency weight for a single conversion.

| Dimension | UnitsNet | QuantityTypes | UnitGenerator |
| --- | --- | --- | --- |
| GitHub stars | 2,969 | 93 | 400 |
| Last commit | Aug 2026 | Aug 2026 | Jul 2026 |
| Install | `dotnet add package UnitsNet` | NuGet `QuantityTypes` | `Install-Package UnitGenerator` |
| Approach | generated quantities + units, `struct` value types | hand-written strongly typed quantities | Roslyn source generator from your own `[UnitOf]` declarations |
| Quantity catalogue | ~100+ quantities, thousands of units | engineering-focused set (length, mass, time, temperature, velocity, …) | whatever you declare |
| Unit-aware arithmetic | yes — `Length l3 = l1 + l2`, `Speed * TimeSpan = Length` | yes — `Length / Time = Velocity` | yes, opt-in via `UnitGenerateOptions.ArithmeticOperator` |
| Culture-aware parse/format | yes (`en-US`, `ru-RU` abbreviations, custom formats) | yes (configurable default units) | no — you write the formatting |
| Runtime lookup of quantities/units | yes (`Quantity`, `QuantityInfo`, `UnitConverter`, `UnitParser`) | no | no |
| Best fit | product code where correctness and i18n matter | minimal footprint on engineering apps | domain primitives and ID types, not physics |

## Decision Matrix: Pick in Ten Seconds

| Your situation | Use this | Why |
| --- | --- | --- |
| Telemetry, CAD, GIS or billing code handling many physical quantities | UnitsNet | largest unit catalogue plus culture-aware I/O |
| You need a `Length` type and nothing else, with zero runtime dependencies | QuantityTypes | tiny surface, value types, ISO 80000 alignment documented |
| Your bug is `OrderId` passed where `UserId` was expected | UnitGenerator | generates strongly typed value objects from annotations |
| User input arrives as `"1 pt"` and you must convert it | UnitsNet | `Length.Parse` throws a descriptive ambiguity error instead of guessing |
| You need JSON round-tripping of quantities | UnitsNet | serialization hooks documented for JSON and XML |

![Installing the UnitsNet package from the official project documentation](/img/screenshots/unitsnet-install.jpg "Adding UnitsNet via NuGet, from the project's own docs")

## UnitsNet — The Completeness Play

UnitsNet generates its quantities from JSON unit definitions, which is why it can ship dozens of unit types per quantity without hand-writing them. Construction and conversion read like domain language:

```csharp
// Construct
Length meter = Length.FromMeters(1);
Length twoMeters = new Length(2, LengthUnit.Meter);

// Convert
double cm = meter.Centimeters;         // 100
double yards = meter.Yards;            // 1.09361
double feet = meter.Feet;              // 3.28084
double inches = meter.Inches;          // 39.3701

// Pass quantity types instead of values to avoid conversion mistakes and communicate intent
string PrintPersonWeight(Mass weight)
{
    // Compile error! Newtons belong to Force, not Mass. A common source of confusion.
    double weightNewtons = weight.Newtons;

    // Convert to the unit of choice - when you need it
    return $"You weigh {weight.Kilograms:F1} kg.";
}
```

The commented line is the whole point of the library: `Mass.Newtons` does not compile, so the class of bug where a weight is silently treated as a force never reaches code review. Operator overloads extend this across quantity algebra, including time-based composition:

```csharp
// Arithmetic
Length l1 = 2 * Length.FromMeters(1);
Length l2 = Length.FromMeters(1) / 2;
Length l3 = l1 + l2;

// Construct between units
Length distance = Speed.FromKilometersPerHour(80) * TimeSpan.FromMinutes(30);
Acceleration a1 = Speed.FromKilometersPerHour(80) / TimeSpan.FromSeconds(2);
Acceleration a2 = Force.FromNewtons(100) / Mass.FromKilograms(20);
RotationalSpeed r = Angle.FromDegrees(90) / TimeSpan.FromSeconds(2);
```

Culture handling is where UnitsNet pulls away from hobby libraries. Abbreviations default to `Thread.CurrentCulture` with a US English fallback, and both `ToString()` and `Parse()` respect it:

```csharp
var usEnglish = new CultureInfo("en-US");
var russian = new CultureInfo("ru-RU");
var oneKg = Mass.FromKilograms(1);

CultureInfo.CurrentCulture = russian;
string kgRu = oneKg.ToString(); // "1 кг"

string mgUs = oneKg.ToUnit(MassUnit.Milligram).ToString(usEnglish, "unit: {1}, value: {0:F2}"); // "unit: mg, value: 1.00"
Mass kg = Mass.Parse("1.0 kg", usEnglish);

// Parse unit from string, a unit can have multiple abbreviations
RotationalSpeedUnit rpm1 = RotationalSpeed.ParseUnit("rpm");   // RevolutionPerMinute
RotationalSpeedUnit rpm2 = RotationalSpeed.ParseUnit("r/min"); // RevolutionPerMinute
```

For dynamic scenarios — a unit-converter UI, or an import pipeline where the unit is only known at runtime — `Quantity`, `QuantityInfo`, `UnitConverter` and `UnitParser` let you enumerate quantities and units, look them up by name, and convert from strings:

```csharp
string[] names = Quantity.Names;     // ["Length", "Mass", ...]
QuantityInfo lengthInfo = Quantity.ByName["Length"];
UnitInfo[] lengthUnits = lengthInfo.UnitInfos;
```

Two operational notes. On versioning, the `master` branch targets v6 and is still pre-release while new units are backported to `maintenance/v5`, so pin your PackageReference deliberately rather than floating. On trimming, `UnitsNet.Modular` is the experimental package that generates only the quantities your application uses — relevant if you ship a mobile or client-side assembly where a full unit catalogue is dead weight.

## QuantityTypes — Small, Typed, Predictable

QuantityTypes takes the hand-written route: a curated set of physical quantities implemented as value types, with multiplication and division producing the right derived type. The README example is compact enough to memorise:

```csharp
using QuantityTypes;

Length s = 100 * Length.Metre;
Time t = 9.58 * Time.Second;
Velocity v = s / t;
Console.WriteLine(v);
Console.WriteLine(v.ToString("0.00[km/h]"));
Console.WriteLine("Speed: {0:0.00[!km/h] kmph}", v);
Mass m = Mass.Parse("92 kg");
double massInPounds = m / Mass.Pound;
Temperature temp = 100 * Temperature.DegreeCelsius;
double tempInFahrenheit = temp.ConvertTo(Temperature.DegreeFahrenheit);
```

The format string `"0.00[km/h]"` is the interesting design choice: the unit is part of the format specifier, so a value can be displayed in one unit regardless of the unit it was stored in, and `[!km/h]` renders the abbreviation literally. Its documented feature list is deliberately boring — strongly typed arithmetic, value types, parsing, formatting, operators, conversion, extensible quantities, configurable default units — and it ships a standards alignment review describing how the library maps to ISO 80000, NIST SP 811 and the SI Brochure.

Where it loses is breadth. With 93 stars and a hand-maintained catalogue, you should check that your specific quantity exists before committing — and if you work in a domain with unusual units, you may find yourself defining them rather than using them. Its real advantage is footprint: no runtime reflection, no generated code, no culture machinery to reason about.

## UnitGenerator — Not a Physics Library

UnitGenerator solves an adjacent problem and it is important not to confuse the two. It is a C# source generator that turns an annotated partial struct into a strongly typed value object with equality, `TypeConverter` support and, optionally, arithmetic:

```csharp
using UnitGenerator;

[UnitOf(typeof(int))]
public readonly partial struct UserId; { }

// or, on C# 11 / .NET 7 and later:
[UnitOf<int>] public readonly partial struct UserId;
```

The generator then emits the constructor, `AsPrimitive()`, explicit conversions, `Equals`, `GetHashCode`, `ToString`, equality operators and a nested `TypeConverter`. Arithmetic is opt-in per type through flags, which is how you get `Hp` semantics — comparable and arithmetic-capable, but never assignable to another type:

```csharp
[UnitOf<int>(UnitGenerateOptions.ArithmeticOperator | UnitGenerateOptions.ValueArithmeticOperator | UnitGenerateOptions.Comparable | UnitGenerateOptions.MinMaxMethod)]
public readonly partial struct Hp;
```

Use this when your "units" are business units — `UserId`, `OrderId`, `Hp`, `Celsius`, `BasisPoints` — and the compiler error you want is "cannot convert `UserId` to `OrderId`". Do not use it as a replacement for UnitsNet: it will not convert kilometres to nautical miles for you, and there is no unit catalogue, no culture-aware formatting and no parsing of measurement strings. It is also used in Unity projects, which is a genuine differentiator if your .NET code lives in a game engine.

## The Pitfalls That Bite in Real Code

**Ambiguous abbreviations are a feature, not a bug — handle them.** `Length.Parse("1 pt")` throws `AmbiguousUnitParseException` with the message `Cannot parse "pt" since it could be either of these: DtpPoint, PrinterPoint`. That is correct behaviour: the library refuses to guess. In an import pipeline you must catch it and apply your own preferred-unit policy, because there is no built-in mechanism that knows your domain defaults.

**Unit-specific properties are conversion points, not storage.** `meter.Centimeters` returns a `double`. Every time you call one you leave the type-safe world and re-enter raw doubles. Convert late, convert once, and keep the quantity type in your data model.

**`QuantityTypes` is not a drop-in for a unit catalogue.** With 93 stars and a hand-curated quantity list, verify your unit exists before designing around it. If it does not, you are choosing between contributing it upstream and defining your own.

**A source generator is a build-time dependency.** UnitGenerator-generated code is invisible in your source tree until you inspect the generated output. Enable `EmitCompilerGeneratedFiles` in the consuming project so the emitted structs are reviewable and diffable — otherwise a generator upgrade can silently change operator semantics and nothing in your diff shows it.

**Rounding and scale are a separate problem from units.** Converting to the right unit solves dimensional analysis, not decimal precision. Currency and fixed-point work needs its own treatment; our [fixed-point arithmetic library comparison](../2026-06-19-fixed-point-arithmetic-libraries-libfixmath-fpm-cnl-shopspring-guide/) covers the scale questions, and the [money and decimal libraries round-up](../2026-09-16-money-decimal-libraries-dinerojs-go-money-py-moneyed-rust-decimal/) covers the same ground in other languages. If you are persisting quantities, the serialization decisions matter too — see our [C# serialization comparison](../2026-07-05-csharp-serialization-libraries-newtonsoft-json-messagepack-protobuf-memorypack/) — and if your quantities are stored through an ORM, the [EF Core versus Dapper versus NHibernate guide](../2026-07-06-csharp-orm-libraries-entity-framework-core-dapper-nhibernate/) explains how value converters interact with query translation.

**C++ teams face the same split.** If your stack is polyglot, the trade-offs in [C++ units of measurement libraries](../2026-06-28-cpp-units-of-measurement-libraries-mp-units-nholthaus-boost-units/) map almost one-to-one onto this article: a big generated catalogue versus a compile-time dimensional-analysis library versus generating your own strong types.

## FAQ

**Which .NET units of measure library should I pick in 2026?**
UnitsNet for production code that handles real physical quantities — it has the widest unit catalogue, culture-aware parsing and formatting, runtime lookup, and serialization support. QuantityTypes when you want a small dependency-free library and only need common engineering quantities. UnitGenerator when the "unit" is a domain primitive rather than a physical quantity.

**Can I use UnitsNet and UnitGenerator together?**
Yes, and it is a sensible split. Use UnitsNet for physical quantities (`Length`, `Mass`, `Speed`) and UnitGenerator for identifier types and business-domain wrappers (`UserId`, `OrderId`, `BasisPoints`). They operate at different layers and do not conflict.

**How do I handle `AmbiguousUnitParseException` when parsing user input?**
Catch it explicitly and map the abbreviation to a preferred unit in your own code. `Length.Parse("1 pt")` cannot decide between `DtpPoint` and `PrinterPoint`, and that ambiguity is domain-dependent — the cleanest fix is a small lookup of the abbreviations you accept plus a documented default.

**Is UnitsNet safe to use in a trimmed or AOT-compiled application?**
Check the current guidance for your target: the library relies on generated types and reflection-based parsing helpers, and the project ships `UnitsNet.Modular` specifically to generate only the quantities an application needs. If size or trimming matters, start with the modular package and measure.

**Does QuantityTypes have enough units for mechanical engineering work?**
It covers the common engineering quantities well and its documented alignment with ISO 80000 and NIST SP 811 is a real advantage. The catalogue is hand-maintained, so confirm your specific unit and precision requirements before you start; if something is missing you extend the library rather than configure it.

**Do these libraries help with decimal money math?**
No. Units of measure give you dimensional correctness; they do not give you currency precision rules, banker's rounding or ledger semantics. Use a dedicated money or decimal library for financial amounts and reserve unit libraries for physical quantities.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "UnitsNet vs QuantityTypes vs UnitGenerator: Picking a .NET Units of Measure Library in 2026",
  "description": "UnitsNet, QuantityTypes and UnitGenerator compared for .NET in 2026, with real NuGet installs, real code and the conversion bugs each library prevents.",
  "datePublished": "2026-09-17",
  "dateModified": "2026-09-17",
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
