---
title: "Java Code Generation Libraries: JavaPoet vs KotlinPoet vs AutoValue for Annotation Processing"
date: "2026-07-31"
tags: ["java", "code-generation", "annotation-processing", "javapoet", "kotlinpoet", "autovalue", "jvm", "developer-tools", "kotlin", "compile-time"]
draft: false
---

## Introduction

Code generation is one of Java's superpowers. Annotation processors run at compile time, generating boilerplate code that developers would otherwise write by hand — builders, serializers, factory methods, and more. The JVM ecosystem offers several libraries that make writing annotation processors both productive and maintainable.

Three libraries dominate this space: **JavaPoet** (10,851 ⭐) from Square, **KotlinPoet** (4,147 ⭐) also from Square, and **AutoValue** (10,560 ⭐) from Google. While all three generate source code, they serve different roles — JavaPoet and KotlinPoet are general-purpose code generation APIs, while AutoValue is a specific annotation processor that uses code generation to eliminate value-type boilerplate.

This article compares these libraries, showing when to use a programmatic code writer, when to use Kotlin's syntax-aware generator, and when an opinionated annotation processor solves your problem out of the box.

## Library Overview

| Feature | JavaPoet | KotlinPoet | AutoValue |
|---------|----------|------------|-----------|
| Stars | 10,851 | 4,147 | 10,560 |
| Maintainer | Square | Square | Google |
| Target Language | Java | Kotlin | Java |
| Approach | Programmatic API | Kotlin DSL | Annotation Processor |
| Learning Curve | Moderate | Moderate (Kotlin knowledge) | Low (just add annotations) |
| Customization | Full control over output | Full control over Kotlin output | Extension-based |
| IDE Integration | Generated sources visible | Generated sources visible | Seamless (incremental) |
| Build System | `javac` / `kapt` / `ksp` | `kapt` / `ksp` | `javac` / `kapt` |

## JavaPoet: Programmatic Java Code Generation

JavaPoet provides a fluent API for generating `.java` source files. Instead of string concatenation (which inevitably produces broken code), JavaPoet models Java language constructs as objects:

```java
import com.squareup.javapoet.*;

public class BuilderGenerator {
    public static JavaFile generateBuilder(ClassName targetClass) {
        TypeSpec builder = TypeSpec.classBuilder(targetClass.simpleName() + "Builder")
            .addModifiers(Modifier.PUBLIC, Modifier.STATIC)
            .addField(FieldSpec.builder(targetClass, "instance", Modifier.PRIVATE)
                .initializer("new $T()", targetClass)
                .build())
            .addMethod(MethodSpec.methodBuilder("setName")
                .addModifiers(Modifier.PUBLIC)
                .returns(ClassName.get("", targetClass.simpleName() + "Builder"))
                .addParameter(String.class, "name")
                .addStatement("instance.name = name")
                .addStatement("return this")
                .build())
            .addMethod(MethodSpec.methodBuilder("build")
                .addModifiers(Modifier.PUBLIC)
                .returns(targetClass)
                .addStatement("return instance")
                .build())
            .build();

        return JavaFile.builder(targetClass.packageName(), builder).build();
    }
}
```

JavaPoet excels at generating complex code patterns. A real-world annotation processor using JavaPoet can generate entire classes from annotated interfaces:

```java
@AutoService(Processor.class)
public class RestClientProcessor extends AbstractProcessor {
    @Override
    public boolean process(Set<? extends TypeElement> annotations,
                           RoundEnvironment roundEnv) {
        for (Element element : roundEnv.getElementsAnnotatedWith(RestClient.class)) {
            TypeSpec client = TypeSpec.classBuilder(element.getSimpleName() + "Impl")
                .addModifiers(Modifier.PUBLIC)
                .addSuperinterface(ClassName.get((TypeElement) element))
                .addMethod(generateGetMethod())
                .addMethod(generatePostMethod())
                .build();

            JavaFile.builder(getPackage(element), client)
                .build()
                .writeTo(processingEnv.getFiler());
        }
        return true;
    }
}
```

**Key strengths:** Type-safe code generation prevents syntax errors; handles imports automatically; generates well-formatted output; battle-tested in Dagger, Retrofit, and thousands of other libraries.

## KotlinPoet: Kotlin-Aware Code Generation

KotlinPoet is the Kotlin counterpart, generating `.kt` files with full awareness of Kotlin language features — nullability, data classes, extension functions, and coroutines:

```kotlin
import com.squareup.kotlinpoet.*

fun generateDataClass(name: String, fields: List<Pair<String, TypeName>>): FileSpec {
    val className = ClassName("com.example", name)
    return FileSpec.builder(className)
        .addType(
            TypeSpec.classBuilder(className)
                .addModifiers(KModifier.DATA)
                .primaryConstructor(
                    FunSpec.constructorBuilder()
                        .addParameters(fields.map { (name, type) ->
                            ParameterSpec.builder(name, type).build()
                        })
                        .build()
                )
                .addProperties(fields.map { (name, type) ->
                    PropertySpec.builder(name, type)
                        .initializer(name)
                        .build()
                })
                .build()
        )
        .build()
}
```

KotlinPoet handles Kotlin-specific constructs that JavaPoet cannot express:

```kotlin
// Nullable types
ParameterSpec.builder("email", String::class.asTypeName().copy(nullable = true))

// Extension functions
FunSpec.builder("toUser")
    .receiver(ClassName("com.example.dto", "UserDto"))
    .returns(ClassName("com.example.model", "User"))
    .addStatement("return User(name = this.name, email = this.email)")

// Default parameter values
ParameterSpec.builder("page", Int::class)
    .defaultValue("%L", 1)
    .build()
```

For projects using Kotlin Symbol Processing (KSP), KotlinPoet integrates directly:

```kotlin
class MySymbolProcessor(private val codeGenerator: CodeGenerator) : SymbolProcessor {
    override fun process(resolver: Resolver): List<KSAnnotated> {
        val symbols = resolver.getSymbolsWithAnnotation("com.example.Generate")
        symbols.forEach { symbol ->
            val fileSpec = generateClass(symbol)
            fileSpec.writeTo(codeGenerator)
        }
        return emptyList()
    }
}
```

## AutoValue: Opinionated Value Type Generation

AutoValue takes a different approach. Instead of a programmatic API, you define an abstract class or interface, and AutoValue generates the implementation:

```java
import com.google.auto.value.AutoValue;

@AutoValue
public abstract class User {
    public abstract String name();
    public abstract String email();
    public abstract int age();

    public static User create(String name, String email, int age) {
        return new AutoValue_User(name, email, age);
    }
}
```

AutoValue generates `equals()`, `hashCode()`, `toString()`, and a builder automatically. With extensions, it handles even more:

```java
@AutoValue
public abstract class ApiResponse<T> {
    public abstract int statusCode();
    public abstract T body();
    public abstract Optional<String> errorMessage();

    @AutoValue.Builder
    public abstract static class Builder<T> {
        public abstract Builder<T> setStatusCode(int code);
        public abstract Builder<T> setBody(T body);
        public abstract Builder<T> setErrorMessage(String msg);
        public abstract ApiResponse<T> build();
    }

    public static <T> Builder<T> builder() {
        return new AutoValue_ApiResponse.Builder<>();
    }
}

// Gson integration
@AutoValue
@GsonTypeAdapter
public abstract class Config {
    public abstract String apiEndpoint();
    public abstract int timeoutSeconds();
}
```

**Key strengths:** Zero boilerplate for value types; IDE support with generated sources in build output; incremental annotation processing for fast builds; ecosystem extensions for Gson, Moshi, Room, and more.

## When to Use Each Library

| Use Case | Recommended Library |
|----------|-------------------|
| Generating builders, factories, or mappers | JavaPoet / KotlinPoet |
| Replacing hand-written value classes | AutoValue |
| Multi-module code generation | JavaPoet with `kapt` or `ksp` |
| Kotlin-first project with KSP | KotlinPoet |
| Simple data classes (Java) | AutoValue |
| Complex code patterns (Dagger, Room-like) | JavaPoet |
| Extension function generation | KotlinPoet |

## Why Self-Host Your Code Generation Pipeline?

Annotation processing and code generation reduce entire categories of bugs — no more mismatched `equals()` implementations or forgotten builder fields. When you invest in compile-time code generation:

- **Catch errors at compile time, not runtime** — generated code is verified by the compiler before your tests even run. For more JVM quality tools, see our [Java testing libraries guide](../2026-07-24-java-testing-libraries-assertj-hamcrest-truth/).

- **Eliminate boilerplate systematically** — one annotation processor can replace thousands of lines of repetitive code across your codebase. Our [JUnit 5 vs TestNG comparison](../2026-07-29-java-testing-frameworks-junit5-testng-spock-guide/) shows how generated test scaffolding saves time.

- **Enforce architectural patterns** — code generation ensures every class follows the same conventions. See our [object mapping libraries comparison](../2026-06-20-object-mapping-libraries-automapper-mapstruct-marshmallow-ent/) for another pattern where generated code outperforms reflection.

## Deployment Architecture for Code Generation

Annotation processors integrate directly into your build pipeline. For Gradle:

```kotlin
// build.gradle.kts
dependencies {
    annotationProcessor("com.google.auto.value:auto-value:1.11.0")
    annotationProcessor("com.squareup:javapoet:1.13.0")
    // For Kotlin projects with KSP:
    ksp("com.squareup:kotlinpoet-ksp:1.18.0")
}
```

For Maven:

```xml
<dependency>
    <groupId>com.google.auto.value</groupId>
    <artifactId>auto-value-annotations</artifactId>
    <version>1.11.0</version>
    <scope>provided</scope>
</dependency>
```

Generated sources appear in `build/generated/sources/annotationProcessor/` and are automatically included in compilation. No runtime dependencies — the generated code is plain Java or Kotlin.

## Migration and Coexistence Strategies

Adopting code generation in an existing codebase requires a gradual approach. Here are patterns for introducing JavaPoet, KotlinPoet, and AutoValue without disrupting development:

**Incremental AutoValue Adoption**: Start by converting hand-written value classes one at a time. AutoValue generates a separate implementation class, so existing code continues to compile during migration. Use IDE refactoring to extract the abstract class from existing concrete implementations:

```java
// Before: Hand-written value class
public final class Address {
    private final String street;
    private final String city;
    public Address(String street, String city) { ... }
    public String street() { return street; }
    public String city() { return city; }
    @Override public boolean equals(Object o) { ... }
    @Override public int hashCode() { ... }
}

// After: AutoValue with same API
@AutoValue
public abstract class Address {
    public abstract String street();
    public abstract String city();
    public static Address create(String street, String city) {
        return new AutoValue_Address(street, city);
    }
}
```

**Custom Annotation Processor Testing**: When writing custom processors with JavaPoet, test them by compiling test sources and verifying the generated output. Google's `compile-testing` library makes this straightforward:

```java
@Test
public void testBuilderGeneration() {
    JavaFileObject source = JavaFileObjects.forSourceString(
        "test.MyClass", 
        "@GenerateBuilder public class MyClass { private String name; }"
    );
    
    Compilation compilation = javac()
        .withProcessors(new BuilderProcessor())
        .compile(source);
    
    assertThat(compilation).succeeded();
    assertThat(compilation)
        .generatedSourceFile("test.MyClassBuilder")
        .contentsAsUtf8String()
        .contains("public MyClass build()");
}
```

**KotlinPoet with Multiplatform**: For Kotlin Multiplatform projects, KotlinPoet can generate common code that works across JVM, JS, and Native targets. Use `expect`/`actual` declarations with generated implementations to share code generation logic while accommodating platform differences.

**Build Integration Considerations**: When a project uses both Java and Kotlin annotation processors, processor ordering matters. Configure your build to run JavaPoet-based processors first (they generate Java sources), then KotlinPoet processors, and finally AutoValue. For Gradle with KSP, use the `ksp` configuration block with explicit processor class names to control execution order.



## FAQ

### Does AutoValue work with Kotlin?

AutoValue targets Java, but Kotlin's `data class` provides equivalent functionality natively. For mixed Java/Kotlin projects, use AutoValue for Java classes and `data class` for Kotlin. If you need shared value types, consider defining them in Kotlin or using KotlinPoet to generate cross-language compatible code.

### How does JavaPoet compare to string templates?

JavaPoet prevents common string-concatenation bugs — missing imports, broken indentation, duplicate method names. It also handles reserved keywords and generates valid Java syntax guaranteed. For simple cases, string templates work, but for annotation processors that generate hundreds of classes, JavaPoet's type safety pays for itself.

### Can I use both JavaPoet and AutoValue in the same project?

Yes — they serve different purposes. AutoValue generates implementations for annotated value types, while JavaPoet is used inside custom annotation processors. Many projects use AutoValue for their data models and JavaPoet for generating API clients, serializers, or test fixtures.

### What's the performance impact of annotation processing?

Annotation processing runs at compile time with zero runtime overhead. However, complex processors can slow down builds. Use incremental annotation processing (supported by both JavaPoet and AutoValue) and consider KSP over kapt for Kotlin projects — KSP is up to 2x faster.

### Is JavaPoet still relevant with Java records?

Java records (Java 16+) handle simple data carriers, but JavaPoet remains essential for generating complex code — builders, protocol buffers, API clients, and database mappers. Records replace some AutoValue use cases, but annotation processors generating non-trivial code patterns still need JavaPoet or KotlinPoet.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Java Code Generation Libraries: JavaPoet vs KotlinPoet vs AutoValue for Annotation Processing",
  "description": "Compare JavaPoet, KotlinPoet, and AutoValue for compile-time code generation. Learn when to use programmatic APIs versus annotation-driven value type generation in JVM projects.",
  "datePublished": "2026-07-31",
  "dateModified": "2026-07-31",
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
