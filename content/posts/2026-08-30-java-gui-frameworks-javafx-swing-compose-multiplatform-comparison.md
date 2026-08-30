---
title: "JavaFX vs Swing vs Compose Multiplatform in 2026: Which Java GUI Framework Should You Use?"
date: "2026-08-30"
tags: ["java", "gui", "desktop-apps", "javafx", "swing", "compose-multiplatform", "kotlin"]
draft: false
cover: "/img/screenshots/compose-cover.jpg"
---

Java desktop development is not dead — it just got more confusing. In 2026 you have three credible paths to a native desktop app: Swing, the 1997-era toolkit that still ships inside every JDK; JavaFX, the modern retained-mode framework that Oracle handed to the OpenJFX community; and Compose Multiplatform, JetBrains' declarative UI that compiles the same Kotlin code to Windows, macOS, Linux, Android, and iOS. Pick wrong and you either fight a 25-year-old API or sign up for a learning curve that dwarfs your actual project. This guide compares all three with real code, current GitHub stats, and licensing facts so you can decide in ten minutes instead of three weekends.

## TL;DR / Quick Verdict

**If you maintain a legacy enterprise app or need zero dependencies, stay on Swing** — it still works and nothing about it will surprise you. **If you want modern controls, CSS styling, and a steady release cadence on the JVM only, choose JavaFX.** **If you're starting a NEW project and care about sharing UI code with Android or iOS, pick Compose Multiplatform** — it is the only one of the three with a first-party mobile story. Swing wins on ubiquity (23,287★ in the JDK repo), JavaFX wins on polish, Compose wins on the future.

## Quick Comparison Table (August 2026, live GitHub data)

| Dimension | Swing (openjdk/jdk) | JavaFX (openjdk/jfx) | Compose Multiplatform (JetBrains) |
|---|---|---|---|
| GitHub stars | 23,287★ | 3,282★ | 19,329★ |
| Last commit | 2026-08-30 | 2026-08-27 | 2026-08-29 |
| License | GPL-2.0 + Classpath Exception | GPL-2.0 + Classpath Exception | Apache-2.0 |
| First released | 1997 | 2008 (JavaFX 1.0), 2014 (2.0) | 2021 (desktop stable) |
| UI paradigm | Retained, MVC-ish | Retained, FXML + CSS | Declarative, reactive |
| Language | Java | Java (FXML/Kotlin possible) | Kotlin (Java interop possible) |
| Mobile targets | None | iOS/Android via Gluon (commercial) | Android, iOS, Web (beta), Desktop |
| Hardware acceleration | No (2D only) | Yes (Prism/Marlin) | Yes (Skia) |
| Styling | LookAndFeel, no CSS | CSS stylesheets | No CSS; theming via composables |
| Learning curve | Low | Medium | Medium-high |
| Best for | Legacy maintenance | JVM-only desktop polish | Cross-platform greenfield |

## Scenario Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Maintain an existing Swing app | Swing | Migration costs exceed any benefit; Swing is still maintained inside the JDK |
| New JVM-only business tool with modern UI | JavaFX | CSS theming, rich controls, TableView, and a healthy community ecosystem |
| App that must also run on Android/iOS | Compose Multiplatform | Single Kotlin codebase targets desktop + mobile + web (beta) |
| Team only knows Java, refuses Kotlin | JavaFX | Compose is Kotlin-first; Java interop exists but fights the grain |
| Ultra-tight dependency constraints | Swing | Ships in the JDK — zero extra jars, zero module-path pain |
| Prototype-to-production fast iteration | Compose Multiplatform | Hot reload, previews, and no FXML/controller boilerplate |

## Swing — The Undead Workhorse

Swing remains the most-installed GUI toolkit on the planet because it is physically inside every JDK. The `openjdk/jdk` repository — where Swing lives — sits at **23,287★ with commits as recent as 2026-08-30**. Oracle and the OpenJDK community still fix Swing bugs, and the API surface from 1997 has barely changed, which is precisely why legacy systems never migrate off it.

A minimal Swing app is five lines:

```java
import javax.swing.*;

public class HelloSwing {
    public static void main(String[] args) {
        JFrame frame = new JFrame("Hello Swing");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.add(new JLabel("Hello, world!", SwingConstants.CENTER));
        frame.setSize(400, 120);
        frame.setVisible(true);
    }
}
```

Swing's retained mode means you manipulate widgets directly: `button.setText(...)`, `model.addTableModelListener(...)`. There is no scene graph abstraction, no CSS, no binding framework in the core. You get `JTable`, `JTree`, `JTabbedPane`, and the rest of the palette, plus pluggable LookAndFeel themes. What you do not get is hardware acceleration — Swing renders through the 2D pipeline, which is fine for CRUD screens and miserable for canvas-heavy tools.

**Where Swing hurts in 2026:** HiDPI is handled but inconsistent across LookAndFeels; the default Metal look is visually dated; and building a modern layout means fighting `GroupLayout` or importing a third-party layout. For a brand-new project with no legacy constraints, choosing Swing is choosing familiarity over capability.

## JavaFX — The JVM-Native Modern Option

JavaFX is the successor Oracle built, then donated to the OpenJFX community in 2015. The `openjdk/jfx` repo shows **3,282★, active as of 2026-08-27**, and the toolkit ships as a separate module set — you add it to your module path or via Maven. JavaFX gives you a proper scene graph, CSS styling, and a retained-mode programming model that feels like a matured Swing rather than a rewrite-everything experiment.

The canonical hello world:

```java
import javafx.application.Application;
import javafx.scene.Scene;
import javafx.scene.control.Label;
import javafx.stage.Stage;

public class HelloJavaFX extends Application {
    @Override
    public void start(Stage stage) {
        Label label = new Label("Hello, JavaFX!");
        Scene scene = new Scene(label, 400, 120);
        stage.setTitle("Hello JavaFX");
        stage.setScene(scene);
        stage.show();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
```

What makes JavaFX worth considering in 2026:

- **CSS theming.** `scene.getStylesheets().add("app.css")` and you can restyle the entire app without touching code. This is the single biggest quality-of-life win over Swing.
- **Rich data controls.** `TableView` with `PropertyValueFactory`, `ListView` with cell factories, and observable collections (`FXCollections.observableArrayList`) give you data binding that Swing never had in the core.
- **Hardware acceleration.** The Prism renderer uses Direct3D/Metal/OpenGL under the hood, with the Marlin rasterizer as the CPU fallback. Canvas-heavy apps run far smoother than Swing.
- **FXML separation.** You can define UI in `.fxml` files with a controller class, which teams with designers appreciate.

The catch: JavaFX is JVM-only. Gluon offers commercial iOS/Android ports, but the open-source story for mobile is weak, and the module system (JavaFX modules must be on the module path with `--add-modules`) trips up beginners. It is also worth noting the OpenJFX project is community-driven — Oracle's corporate commitment ended years ago, so release cadence and funding depend on the ecosystem.

## Compose Multiplatform — The Declarative Future

Compose Multiplatform, at **19,329★ in JetBrains/compose-multiplatform (Apache-2.0, last commit 2026-08-29)**, is the fastest-rising option on this list. It is JetBrains' desktop/Web/iOS port of Google's Jetpack Compose: same declarative API, same compiler, Skia-based rendering, and hardware acceleration on all targets. You write UI in Kotlin as composable functions, and state changes automatically recompose only the affected parts of the tree.

The desktop hello world:

```kotlin
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application

fun main() = application {
    Window(onCloseRequest = ::exitApplication, title = "Hello Compose") {
        MaterialTheme {
            Text("Hello, Compose Multiplatform!", modifier = Modifier.padding(16.dp))
        }
    }
}
```

The killer feature is the matrix: the same `@Composable` code runs on **Windows, macOS, Linux, Android, iOS, and (in beta) the browser via Kotlin/Wasm**. The official repo README shows the same app UI rendered across all six targets — that is the pitch in one image. For teams already on Kotlin, there is no second language and no second UI paradigm to learn.

**Trade-offs to know before you commit:**

- **Kotlin-first.** Java interop works — you can call Compose from Java — but idiomatic Compose is Kotlin. A Java-only team faces a real language ramp.
- **Younger ecosystem.** JavaFX and Swing have two decades of Stack Overflow answers, third-party controls, and corporate case studies. Compose's component libraries are growing but thinner.
- **Web is beta.** The Kotlin/Wasm target works for demos and internal tools, but production web apps are still a promise, not a guarantee.
- **JDK requirements.** Desktop targets need a recent JDK, and tooling (Gradle plugin, Compose compiler) moves fast — expect frequent plugin upgrades.

## Migration and Coexistence Pitfalls

- **Never port a working Swing app to JavaFX for aesthetics.** Ports cost 3–10x the original build time and introduce layout regressions. Wrap the legacy UI in a new shell instead, or keep it until a feature rewrite is already on the table.
- **JavaFX module-path traps.** Missing `--add-modules javafx.controls` or running on the classpath instead of module path produces baffling `NoClassDefFoundError`s. Standardize on a Maven/Gradle plugin (javafx-maven-plugin, org.openjfx.javafxplugin) rather than hand-rolling module flags.
- **FXML + controller wiring is stringly-typed.** Refactoring a controller method name breaks FXML loading at runtime, not compile time. If your team churns, prefer programmatic scene construction or Kotlin DSL builders.
- **Compose version coupling.** Compose Multiplatform's compiler plugin must match the Kotlin version within a narrow window. Pin both in Gradle and upgrade them together — upgrading Kotlin alone routinely breaks builds.
- **Threading discipline.** Swing and JavaFX are single-threaded UI toolkits: all widget mutation must happen on the EDT / JavaFX Application Thread. Compose desktop is more forgiving but still expects state mutations on the UI thread; background work belongs in coroutines with `withContext(Dispatchers.Main)`.
- **HiDPI test early.** Rendering pipelines differ (Swing 2D vs Prism vs Skia). What looks crisp on a 100% scale Linux box can blur on a 200% Windows laptop. Add a HiDPI test pass before shipping.
- **Licensing reality check.** Swing and JavaFX are GPL-2.0 with the Classpath Exception — fine for proprietary apps as long as you don't statically link the JDK classes into your binary. Compose is Apache-2.0, the least restrictive of the three. If your legal team is skittish, that difference matters.

## How They Compare for Common App Types

**Internal business tools (CRUD, dashboards):** JavaFX's TableView + CSS wins for JVM-only shops; Compose wins if you need the same tool on phones. Swing remains perfectly serviceable for intranet apps where nobody sees the chrome.

**Designer-heavy or media apps:** JavaFX's scene graph and CSS make it the best JVM fit. Compose's declarative model is great once your team internalizes recomposition, but the learning curve is real.

**Cross-platform consumer apps:** Compose Multiplatform is the only serious answer here. No other JVM toolkit ships first-party Android and iOS support, and the official README's six-target demo is not marketing fluff — the same `@Composable` code genuinely compiles to all of them.

**Embedded / kiosk / single-purpose:** Swing's zero-dependency footprint still wins when you cannot control the JDK version on the target machine.

Java desktop projects rarely exist in isolation. If you are building a desktop app that talks to a backend, check out our [guide to Java code generation with JavaPoet and KotlinPoet](../2026-07-31-java-code-generation-javapoet-kotlinpoet-autovalue/) for the DTO and client boilerplate angle, and our [Kotlin HTTP client comparison covering Ktor, Fuel, and http4k](../2026-08-01-kotlin-http-clients-ktor-fuel-http4k-comparison/) for the API layer. When it comes to verifying UI logic, our [Java testing libraries roundup with AssertJ, Hamcrest, and Truth](../2026-07-24-java-testing-libraries-assertj-hamcrest-truth/) shows how to write assertions that survive UI refactors.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaFX vs Swing vs Compose Multiplatform in 2026: Which Java GUI Framework Should You Use?",
  "description": "In-depth 2026 comparison of JavaFX, Swing, and Compose Multiplatform for Java desktop development: real code, GitHub stats, licensing (GPL+CE vs Apache-2.0), migration pitfalls, and scenario-based recommendations.",
  "datePublished": "2026-08-30",
  "dateModified": "2026-08-30",
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

**Is Swing still maintained in 2026?** Yes. Swing is part of `openjdk/jdk` (23,287★, commits through 2026-08-30) and receives bug fixes with each JDK release, but no new features are planned. It is maintenance mode, not abandonment.

**Is JavaFX free for commercial use?** Yes. JavaFX is licensed GPL-2.0 with the Classpath Exception, the same license as the JDK itself, so proprietary applications can use it freely as long as they do not distribute modified JDK/JavaFX classes.

**Can I use Compose Multiplatform with Java instead of Kotlin?** Technically yes, but the entire API is designed for Kotlin. Java callers need to consume Kotlin functions with default arguments and deal with `Modifier` chains awkwardly. Realistically, Compose means Kotlin.

**Does Compose Multiplatform support web browsers?** Web support is in beta via Kotlin/Wasm as of Compose Multiplatform 1.9. It works for demos and internal tools; treat it as not-yet-production for public-facing web apps.

**Which framework has the best performance?** For typical business UIs all three are fast enough. For canvas/rendering-heavy workloads, JavaFX (Prism/Marlin) and Compose (Skia) are hardware-accelerated; Swing is not. The visible difference appears with large tables, charts, or custom-drawn components.

**How do JavaFX and Swing handle threading?** Both are single-threaded. Swing uses the Event Dispatch Thread (EDT); JavaFX uses the JavaFX Application Thread. Any mutation of live UI state off those threads throws or corrupts state, so long-running tasks must run in background workers (`SwingWorker`, `Task<V>`, coroutines) and marshal results back.

**Which framework is better for large data tables?** JavaFX `TableView` with virtualized rows and cell factories handles tens of thousands of rows smoothly and is the strongest of the three for data-heavy UIs. Swing's `JTable` is capable but verbose. Compose's LazyColumn-based tables are still maturing for spreadsheet-grade workloads.

**Can JavaFX and Compose be mixed in one application?** Not directly in the same window. You can embed a JavaFX `Scene` inside a Swing `JFrame` (interop is supported both ways), and you can run Compose windows alongside them as separate top-level windows, but there is no supported way to nest Compose composables inside a JavaFX scene graph today.

**What is the safest choice for a new JVM-only project in 2026?** JavaFX. It is actively maintained, licensed for commercial use, hardware-accelerated, and has the richest ecosystem of the JVM-only options. Choose Compose instead only when mobile targets are on your roadmap.


---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
