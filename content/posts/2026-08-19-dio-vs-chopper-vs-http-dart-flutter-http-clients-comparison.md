---
title: "dio vs Chopper vs http in 2026: Which Dart HTTP Client Should Your Flutter App Use?"
date: "2026-08-19"
tags: ["flutter", "dart", "http", "networking", "mobile"]
draft: false
cover: "/img/screenshots/dio-cover.jpg"
---

Every Flutter app eventually hits the same wall: the default `http` package works, then you need a token refresh interceptor, upload progress, request cancellation, or typed API clients — and suddenly you are choosing between **dio (12,839 stars)**, **Chopper (748 stars)**, and the official **http (1,108 stars)** package. The decision shapes your networking layer for the life of the app, and the wrong pick means rewriting every repository class later. Here is the 2026 state of the Dart HTTP client landscape, with live repository data and code you can lift directly.

## TL;DR — Quick Verdict

- **Pick dio** for almost any real app: interceptors, cancellation, FormData uploads, timeout control, and a plugin ecosystem (logging, cookie manager, retry) — all in one package with a huge community.
- **Pick the official `http` package** for tiny apps, quick scripts, or when you want zero dependencies and the thinnest possible abstraction — it is maintained by the Dart team.
- **Pick Chopper** if you come from a Retrofit/OkHttp background, love code generation, and want compile-time-checked, typed API clients with a clean service-class pattern.

dio is the safe default; the other two are deliberate architecture choices, not compromises.

## Feature Comparison Table

| Dimension | dio | Chopper | http (dart-lang) |
|---|---|---|---|
| GitHub stars (2026-08-19) | **12,839** | 748 | 1,108 |
| Last push | 2026-08-17 | 2026-08-03 | 2026-08-11 |
| Latest version | v5.11.0 | v8.7.0 | v1.6.0 |
| Maintainer | cfug community | lejard-h | Dart/Flutter team |
| Interceptors | **First-class** | Via interceptor chain | None built-in |
| Request cancellation | `CancelToken` | Built-in | Via `http.Client.close()` |
| Upload progress | **Yes (FormData)** | Via Request/Response | Manual streams |
| Code generation | No | **Yes (source_gen)** | No |
| Typed API clients | Manual | **Generated from annotations** | Manual |
| Web (browser) support | Yes | Yes | Yes |
| License | MIT | MIT | BSD-3-Clause |

## Use Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Standard REST app with auth/token refresh | **dio** | Interceptors make refresh-and-retry a 20-line pattern |
| File upload with progress bar | **dio** | `FormData` + `onSendProgress` callback out of the box |
| Large typed API surface (50+ endpoints) | **Chopper** | Generated clients catch URL/param typos at compile time |
| Microservice/service with 2-3 calls | **http package** | No abstraction tax; official, stable, zero surprises |
| Team migrating from Android Retrofit | **Chopper** | Same mental model: annotations + generated service |
| Server-side Dart scripts (non-Flutter) | **http package** | Lightweight, works in `dart run` without Flutter engine |

## dio — The Batteries-Included Networking Layer

dio describes itself as "a powerful HTTP networking package for Dart/Flutter, supporting Global configuration, Interceptors, FormData, Request cancellation, File uploading/downloading, Timeout, Custom adapters, Transformers, etc." (verified from the official README). It is the closest thing Dart has to OkHttp-plus-Retrofit in a single dependency.

The super-simple start (verbatim from the README):

```dart
import 'package:dio/dio.dart';

final dio = Dio();

void getHttp() async {
  final response = await dio.get('https://dart.dev');
  print(response);
}
```

Real apps configure a shared instance with base options and a logging interceptor:

```dart
final dio = Dio(BaseOptions(
  baseUrl: 'https://api.example.com',
  connectTimeout: const Duration(seconds: 10),
  receiveTimeout: const Duration(seconds: 10),
  headers: {'Accept': 'application/json'},
));

dio.interceptors.add(LogInterceptor(responseBody: true));
```

The token-refresh pattern that sells dio to most teams:

```dart
dio.interceptors.add(InterceptorsWrapper(
  onError: (error, handler) async {
    if (error.response?.statusCode == 401) {
      await refreshToken();
      final retry = await dio.request(
        error.requestOptions.path,
        options: Options(method: error.requestOptions.method),
      );
      return handler.resolve(retry);
    }
    handler.next(error);
  },
));
```

Uploads with progress, a common pain point in Flutter apps:

```dart
final formData = FormData.fromMap({
  'file': await MultipartFile.fromFile('/tmp/report.pdf'),
});

final response = await dio.post(
  '/upload',
  data: formData,
  onSendProgress: (sent, total) {
    print('${sent / total * 100}% uploaded');
  },
);
```

dio v5 (current) introduced breaking changes worth knowing: `DioError` became `DioException`, timeout options switched from `int` milliseconds to `Duration` objects, and `validateStatus` defaults were tightened. If you are migrating from dio 4.x, the official migration guide is short but mandatory — the API renames will break compilation in predictable places.

## The Official http Package — Minimalism by Design

`http` is the Dart team's official HTTP client, living in the `dart-lang/http` repository (the package source is under `pkgs/http` in the monorepo). Its philosophy is the opposite of dio's: **no global state, no interceptors, no magic** — just functions and a small `Client` abstraction that you can replace for testing.

Basic GET:

```dart
import 'package:http/http.dart' as http;

Future<void> fetchData() async {
  final response = await http.get(Uri.parse('https://dart.dev'));
  print(response.statusCode);
  print(response.body);
}
```

POST with JSON body and headers:

```dart
final response = await http.post(
  Uri.parse('https://api.example.com/orders'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({'sku': 'A-100', 'qty': 2}),
);
```

For tests, `MockClient` from `package:http/testing.dart` lets you stub responses without a server — the same pattern the Flutter team uses internally. Because `http` has no interceptors, middleware (auth headers, retries) is implemented by wrapping the `Client` — a small `AuthenticatedClient implements http.Client` class is the idiomatic approach, and it keeps your dependency graph minimal.

The trade-off becomes visible at scale: no cancellation tokens (you close the client), no upload progress callback, and no automatic content negotiation. Every feature you need beyond the basics is hand-rolled — which is exactly the point, but exactly why large apps graduate to dio.

## Chopper — Retrofit-Style Code Generation for Dart

Chopper is "an http client generator for Dart and Flutter using source_gen and inspired by Retrofit" (official README), and it is a **Flutter Favorite** package. You declare your API as an annotated abstract class, run `build_runner`, and get a concrete client with compile-time-validated paths and params.

Service definition:

```dart
// user_service.dart
import 'package:chopper/chopper.dart';

part 'user_service.chopper.dart';

@ChopperApi(baseUrl: '/users')
abstract class UserService extends ChopperService {
  @Get(path: '/{id}')
  Future<Response> getUser(@Path('id') int id);

  @Post()
  Future<Response> createUser(@Body() Map<String, dynamic> body);

  static UserService create([ChopperClient? client]) => _$UserService(client);
}
```

Client wiring with a JSON converter:

```dart
final client = ChopperClient(
  baseUrl: Uri.parse('https://api.example.com'),
  services: [UserService.create()],
  converter: const JsonConverter(),
);

final service = UserService.create(client);
final response = await service.getUser(42);
```

![Chopper generated HTTP client](/img/screenshots/chopper-inline.jpg "Chopper — Retrofit-style code generation for Dart")

Code generation adds a build step:

```bash
dart run build_runner build
```

Chopper shines when your API surface is large and stable: endpoint paths, query parameters, and body shapes are checked when you regenerate, so refactors break at compile time instead of runtime. Interceptors exist (`interceptors:` list on the client), but the ecosystem of ready-made interceptors is far thinner than dio's, and the codegen tooling (build_runner) slows incremental builds. For a small API, the annotation ceremony outweighs the benefit.

## Pitfalls and Migration Gotchas

- **dio 4 → 5 is a source-breaking upgrade.** `DioError` → `DioException`, timeout values become `Duration`, `responseType` defaults changed. Run the official migration guide, and grep your codebase for `DioError` before upgrading.
- **Chopper version skew is real.** The `chopper` package and the `chopper_annotation` package must stay in lockstep; mixing versions produces cryptic codegen errors ("Error: Couldn't find source file ... chopper.dart"). Pin both to the same version and regenerate with `dart run build_runner build --delete-conflicting-outputs`.
- **http package + large uploads = memory pressure.** `http.post` buffers the whole body. For streaming uploads or downloads, use `http.StreamedRequest`/`Client.send`, or switch to dio's `onSendProgress` for visibility.
- **Don't ignore `Client` lifecycle.** `package:http` clients hold sockets; long-lived apps should create one top-level `Client` and reuse it, or call `close()` in teardown — a leaked client per screen is a classic source of socket exhaustion.
- **Mocking strategy changes everything.** dio apps test with `dio.httpClientAdapter = ...` or `MockAdapter`; http apps use `MockClient`; Chopper apps mock at the service level. Decide your testing approach before the codebase grows — see our guide on [Dart and Flutter testing libraries](../2026-08-01-dart-flutter-testing-libraries-mocktail-bloc-test-comparison/) for the mocktail ecosystem.
- **Certificate pinning and proxies.** dio supports custom `HttpClientAdapter`s and `badCertificateCallback`; http requires wrapping `IOClient` with a custom `HttpClient`. If your enterprise app needs pinning, budget extra time with either — there is no one-liner in any of the three.
- **Platform differences.** On web, dio and http both compile to `XMLHttpRequest`/`fetch` under the hood; `MultipartFile` from file paths does **not** work on the browser (no dart:io). Use bytes-based uploads for web targets — a trap that appears in production, not in local tests.

## How the Packages Compare in a Real Codebase

A typical authenticated CRUD app with dio lands around 60-80 lines of networking infrastructure (base options + refresh interceptor + error mapping), versus 150-200 lines with plain http (wrapped client + manual retry), versus the same as dio plus a codegen file per service with Chopper. The `http` route only pays off when the "infrastructure" you need genuinely fits in a wrapper class. For everything else, dio's interceptors are the single highest-leverage feature in the Dart HTTP ecosystem, and the pattern transfers to any language — compare the same trade-offs in the [Swift HTTP client landscape](../2026-07-27-swift-http-client-libraries-alamofire-urlsession-moya-asynchttpclient/) or the [React data-fetching ecosystem](../2026-08-11-tanstack-query-vs-swr-vs-rtk-query-react-data-fetching-comparison/) to see how universal the interceptor-vs-clean-client debate is.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "dio vs Chopper vs http in 2026: Which Dart HTTP Client Should Your Flutter App Use?",
  "description": "Compare the three dominant Dart/Flutter HTTP clients: dio (interceptors, cancellation, uploads), Chopper (Retrofit-style code generation), and the official http package. Live GitHub stats, real code examples, migration pitfalls, and a use-case decision matrix.",
  "datePublished": "2026-08-19",
  "dateModified": "2026-08-19",
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

### What is the most popular HTTP client for Flutter?

dio is the clear leader with 12,839 GitHub stars (as of 2026-08-19), followed by the official http package (1,108 stars) and Chopper (748 stars). dio is also the most-used choice in production Flutter apps, with the largest community, plugin ecosystem, and documentation.

### When should I use the plain http package instead of dio?

Use `http` when your needs are minimal: a few endpoints, no auth middleware, no upload progress tracking, and a preference for zero dependencies maintained directly by the Dart team. It is also the right choice for server-side Dart scripts and for teams that prefer explicit wrapping over framework conventions.

### Does Chopper work with code generation tools other than build_runner?

Chopper uses `source_gen`, which is the build_runner ecosystem. There is no supported alternative build system; if your project avoids code generation entirely, Chopper is not a fit — dio or http are the alternatives.

### Is dio compatible with Flutter web?

Yes. dio supports web platforms through its browser adapter. Note that file-based `MultipartFile` uploads do not work on the web because there is no `dart:io`; use byte-based uploads instead.

### How do I handle token refresh with the http package?

You implement it manually: wrap the `http.Client` in a class that intercepts 401 responses, refreshes the token, and retries the original request. dio provides this pattern natively via interceptors, which is why most apps with authentication end up choosing dio.

### Are these packages free to use commercially?

All three are permissively licensed — dio and Chopper are MIT, and the http package is BSD-3-Clause — so commercial use is unrestricted.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
