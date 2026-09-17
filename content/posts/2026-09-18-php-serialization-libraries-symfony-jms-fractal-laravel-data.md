---
title: "PHP Serialization in 2026: Symfony Serializer vs JMS Serializer vs Fractal vs Laravel Data"
date: "2026-09-18"
tags: ["php", "serialization", "api", "developer-tools", "open-source"]
cover: "/img/screenshots/jms-serializer-logo.jpg"
draft: false
---

Nothing exposes an API's design debt faster than its response bodies. A user endpoint returns the password hash because nobody configured exclusion groups. A mobile client receives 1.2 MB of nested ORM entities because the serializer walked every lazy-loaded relation. A partner integration breaks because a field changed from `"published_at"` to `"publishedAt"` after a refactor. Serialization is where your domain model meets the outside world, and in PHP it is almost always an afterthought until the first incident.

Four libraries dominate PHP serialization in 2026, and they are not interchangeable: **Symfony Serializer 8.1.7**, **JMS Serializer 3.32.9**, **League Fractal 0.21**, and **Spatie Laravel Data 4.23.0**. Each is the right answer to a different question, and picking the wrong one means fighting your own tooling for a year.

## TL;DR — Quick Verdict

**Choose Symfony Serializer** if you are on Symfony or want a framework-agnostic component with attribute-driven groups, normalizers you can compose, and the strongest metadata caching story. **Choose JMS Serializer** if you need response versioning as a first-class feature (`@Since`/`@Until`) across many API consumers, or you maintain a legacy bundle that already depends on it. **Choose Fraktal-style transform pipelines (League Fractal)** when your output shape is a product decision — transformers give you explicit, testable control over every field and native sparse-fieldset includes. **Choose Spatie Laravel Data** if you are on Laravel and want DTOs that validate, cast, and serialise without writing a transformer class per resource.

The mistake to avoid: adopting three of them in one codebase. Pick one serialization strategy, keep it at the edge of the application, and never let ORM entities escape a controller.

## Side-by-Side Comparison: PHP Serialization Libraries in 2026

| Dimension | Symfony Serializer | JMS Serializer | League Fractal | Spatie Laravel Data |
|---|---|---|---|---|
| Version | 8.1.7 | 3.32.9 | 0.21 | 4.23.0 |
| Install | `composer require symfony/serializer` | `composer require jms/serializer` | `composer require league/fractal` | `composer require spatie/laravel-data` |
| Framework coupling | None (used by Symfony) | None | None | Laravel |
| GitHub repository | symfony/serializer | schmittjoh/serializer | thephpleague/fractal | spatie/laravel-data |
| Stars | 2,535 | 2,342 | 3,544 | 1,793 |
| Last commit | 2026-09-16 | 2026-09-04 | 2025-12-16 | 2026-09-01 |
| License | MIT | MIT | MIT | MIT |
| Configuration style | PHP attributes (`#[Groups]`) | Attributes / annotations | PHP transformer classes | PHP attributes + constructor |
| Response versioning | Manual (groups per version) | **Built in** (`Since`/`Until`) | Manual (transformer per version) | Manual (data classes per version) |
| Sparse fieldsets / includes | Partial (via groups) | Partial | **Native** (`availableIncludes`) | Partial (`#[Lazy]`, partials) |
| Validation integration | Symfony Validator | Symfony Validator | None | **Built in** |
| Metadata caching | Tag-aware PSR-6 cache | File cache | Compiled transformers | Laravel cache |
| Best fit | Symfony apps, JSON API edges | Multi-version partner APIs | Public APIs with negotiated shapes | Laravel apps wanting DTOs |

One observation from the live data: Symfony Serializer had commits within two days of writing this, and Spatie Laravel Data within three weeks, while Fractal's last commit was in December 2025. Fractal is stable rather than abandoned — 3,544 stars and a frozen, well-understood API — but if you are choosing for a greenfield project in 2026, factor that cadence difference into the decision.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Choose | Why |
|---|---|---|
| Symfony application, REST endpoints | Symfony Serializer | Attribute groups, autowiring, metadata cache built in |
| Partner API with v1/v2 consumers | JMS Serializer | `@Since`/`@Until` plus `setVersion()` handles it declaratively |
| Public API with client-selected fields | League Fractal | `?include=author,comments` maps directly to includes |
| Laravel app with form-to-DTO flows | Spatie Laravel Data | Validation, casts, and serialisation in one class |
| Legacy codebase on Doctrine annotations | JMS Serializer | Mature, widely documented, minimal migration |
| You need full control of every response field | League Fractal | Transformers are explicit and trivially unit-testable |
| Plain-PHP microservice, no framework | Symfony Serializer | Standalone component, no container required |

## Symfony Serializer 8.1.7 — The Composable Default

Symfony Serializer separates two concerns that other libraries blur: **normalizers** convert objects to arrays and back, **encoders** convert arrays to formats such as JSON, XML, CSV, and YAML. You compose them, which means the same object graph can become JSON for a mobile client and CSV for a finance export without a second library.

```bash
composer require symfony/serializer symfony/property-access symfony/property-info
```

```php
use Symfony\Component\Serializer\Attribute\Groups;
use Symfony\Component\Serializer\Attribute\SerializedName;

final class Article
{
    #[Groups(['list', 'detail'])]
    public int $id;

    #[Groups(['list', 'detail'])]
    public string $title;

    #[Groups(['detail'])]
    #[SerializedName('published_at')]
    public \DateTimeImmutable $publishedAt;

    #[Groups(['detail'])]
    public Author $author;

    #[Groups(['detail'])]
    public string $internalNotes;
}
```

Serialising with groups is a single call, and the same object produces two different payloads without touching the model:

```php
use Symfony\Component\Serializer\Encoder\JsonEncoder;
use Symfony\Component\Serializer\Normalizer\ObjectNormalizer;
use Symfony\Component\Serializer\Serializer;

$serializer = new Serializer([new ObjectNormalizer()], [new JsonEncoder()]);

$list = $serializer->serialize($articles, 'json', ['groups' => ['list']]);
$detail = $serializer->serialize($article, 'json', [
    'groups' => ['detail'],
    'json_encode_options' => JSON_UNESCAPED_UNICODE,
]);
```

The `Groups` attribute is the security boundary most teams learn about the hard way: any property without a group is invisible when groups are active, which is exactly what you want for `internalNotes` above. Deserialisation respects the same metadata, so `$serializer->deserialize($json, Article::class, 'json')` validates the shape while building the object.

![Symfony Serializer — the composable serialization component](/img/screenshots/symfony-serializer-logo.jpg "Symfony Serializer: normalizers and encoders you compose yourself")

## JMS Serializer 3.32.9 — Versioning as a First-Class Concern

JMS Serializer predates attributes by a decade and is still the strongest choice when a single API must serve multiple contract versions simultaneously. Its `Since` and `Until` annotations let you express "this field appeared in 1.2 and disappeared in 2.0" directly on the property, and the serialization context selects the version at runtime.

```bash
composer require jms/serializer
```

```php
use JMS\Serializer\Annotation as Serializer;

#[Serializer\ExclusionPolicy('all')]
final class Article
{
    #[Serializer\Expose]
    #[Serializer\Groups(['list', 'detail'])]
    private int $id;

    #[Serializer\Expose]
    #[Serializer\Groups(['detail'])]
    #[Serializer\SerializedName('published_at')]
    #[Serializer\Type("DateTimeImmutable<'Y-m-d H:i:s'>")]
    private \DateTimeImmutable $publishedAt;

    #[Serializer\Expose]
    #[Serializer\Groups(['detail'])]
    #[Serializer\Since('2.0')]
    private ?string $readingTime = null;

    #[Serializer\Expose]
    #[Serializer\Groups(['detail'])]
    #[Serializer\Until('2.0')]
    private ?string $legacyExcerpt = null;
}
```

```php
use JMS\Serializer\SerializationContext;
use JMS\Serializer\SerializerBuilder;

$serializer = SerializerBuilder::create()
    ->setCacheDir(__DIR__ . '/var/cache/jms')
    ->setDebug(false)
    ->build();

$context = SerializationContext::create()->setGroups(['detail'])->setVersion('1.9');
$json = $serializer->serialize($article, 'json', $context);
```

`ExclusionPolicy('all')` inverts the default so that nothing is serialised unless explicitly exposed — a small annotation that prevents an entire category of data-leak bugs. JMS also supports `PostDeserialize` and `PreSerialize` visitors, which are the right place to hide fields conditionally (for example, omitting an author's email unless the requester owns the record).

## League Fractal 0.21 — Transformers and Sparse Fieldsets

Fractal takes a different stance: your API's shape is a product surface, so it deserves its own class. A transformer is pure PHP — a `transform()` method returning an array — which makes every response field explicit, greppable, and unit-testable without booting a framework.

```bash
composer require league/fractal
```

```php
use League\Fractal\Resource\Item;
use League\Fractal\TransformerAbstract;

final class ArticleTransformer extends TransformerAbstract
{
    protected array $availableIncludes = ['author', 'comments'];
    protected array $defaultIncludes = ['author'];

    public function transform(Article $article): array
    {
        return [
            'id' => $article->id,
            'title' => $article->title,
            'published_at' => $article->publishedAt->format(DATE_ATOM),
            'reading_time' => $article->readingTimeSeconds(),
        ];
    }

    public function includeAuthor(Article $article): Item
    {
        return $this->item($article->author, new AuthorTransformer());
    }
}
```

```php
use League\Fractal\Manager;
use League\Fractal\Resource\Collection;
use League\Fractal\Serializer\JsonApiSerializer;

$manager = new Manager();
$manager->setSerializer(new JsonApiSerializer('https://www.pistack.xyz/api'));

$resource = new Collection($articles, new ArticleTransformer(), 'articles');
$manager->parseIncludes($_GET['include'] ?? []);

$payload = $manager->createData($resource)->toArray();
```

`parseIncludes()` is where Fractal earns its keep: `?include=author,comments` becomes real eager-loading hints in a repository, so the client's requested shape drives exactly one query instead of a cascade of lazy loads. Deriving computed fields like `reading_time` inside the transformer also keeps presentation logic out of the entity, which is the difference between a model you can refactor and one you cannot.

## Spatie Laravel Data 4.23.0 — DTOs That Do Everything

If you work in Laravel, Spatie's Laravel Data collapses three separate concerns — validation, casting, and serialisation — into a single data class. You construct it from a request or a model, and it knows how to render itself.

```bash
composer require spatie/laravel-data
```

```php
use Spatie\LaravelData\Attributes\MapInputName;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Data;

final class ArticleData extends Data
{
    public function __construct(
        public int $id,
        #[Max(180)]
        public string $title,
        #[MapInputName('published_at')]
        public string $publishedAt,
        public AuthorData $author,
    ) {}

    public static function rules(): array
    {
        return ['title' => ['required', 'string', 'max:180']];
    }
}
```

```php
$data = ArticleData::from($article);
$data->toJson();                       // respects MapInputName mappings
$collection = ArticleData::collection($articles);

$filtered = ArticleData::from($request)->except('id');   // partial output
```

Attribute mapping means your API's snake_case contract and your DTO's camelCase properties coexist without a transformer. Because the data class is also a validation target, the same rules serve both inbound requests and documentation generators, which removes the drift that makes hand-written API docs wrong within a month.

## Real-World Patterns and Pitfalls

**Never `unserialize()` untrusted input.** PHP's native `serialize()`/`unserialize()` pair can instantiate arbitrary classes and is a well-known object-injection vector. All four libraries above serialise to JSON (or XML) for a reason: the wire format carries data, not class identities.

**Exclude by default, expose explicitly.** Whether you use `#[Groups]`, `ExclusionPolicy('all')`, or a transformer, the fail-safe direction is "nothing leaves unless declared." The alternative — blacklist patterns that hide `password` and `internalNotes` — fails the moment someone adds a `secretToken` field on a Friday afternoon.

**Handlers for circular references.** Bidirectional ORM relations will recurse forever. Symfony Serializer accepts a `circular_reference_handler` callback, JMS has a `CircularReferenceHandler` service, and Fractal simply cannot recurse because transformers are explicit. Choose the mechanism before your first nested relation ships.

**Serialize DTOs, not Doctrine proxies.** Normalising an entity directly drags in proxy classes, triggers lazy loads you did not intend, and couples your JSON contract to your database schema. Build a DTO in the controller or a dedicated assembler, then serialise that.

**Cache your metadata in production.** Reading attributes on every request is real CPU. Symfony Serializer's `CacheClassMetadataFactory`, JMS's `setCacheDir()`, and Laravel's config cache all remove that cost — but only if you configure them and, crucially, clear them on deploy.

**Pin your date format.** `DateTimeImmutable` serialised without an explicit format produces different strings across configurations. Pick ISO 8601 with an offset (or `DATE_ATOM`), document it, and assert it in a test.

**Watch memory on large collections.** Serialising 50,000 records into a single JSON array will exhaust `memory_limit` long before it finishes. Stream the response, paginate, or use a generator with a JSON streaming encoder.

## Related Reading for PHP Teams

Serialisation rarely stands alone. If your API accepts user input, pair it with the [PHP validation libraries comparison](../2026-07-21-php-validation-libraries-respect-symfony-rakit/) so inbound payloads are rejected before they reach your DTOs. When your service calls other services, the [PHP HTTP client comparison](../2026-07-13-php-http-clients-guzzle-saloon-httpful/) covers the client side of the same contract, including how response deserialisation is wired. And if your serialization configuration lives in a container — as it does in every Symfony or Laravel application — the [PHP dependency injection containers guide](../2026-07-14-php-dependency-injection-containers-phpdi-pimple-league-auryn/) explains how those services are assembled and cached.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP Serialization in 2026: Symfony Serializer vs JMS Serializer vs Fractal vs Laravel Data",
  "description": "Compare PHP serialization libraries in 2026: Symfony Serializer 8.1.7, JMS Serializer 3.32.9, League Fractal 0.21 and Spatie Laravel Data 4.23.0 with code, versioning and pitfalls.",
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

**Which PHP serialization library should I use in 2026?**
Use **Symfony Serializer** for Symfony applications and framework-agnostic components, **JMS Serializer** when you need built-in response versioning for multiple API consumers, **League Fractal** when explicit transformers and includes are the priority, and **Spatie Laravel Data** inside Laravel applications that want DTOs with validation included.

**Does JMS Serializer still make sense when Symfony Serializer exists?**
Yes, in two cases: APIs that must serve several contract versions at once, where `@Since` and `@Until` with `setVersion()` are cleaner than duplicating attribute groups, and legacy codebases already built on JMS annotations. For a fresh Symfony project, Symfony Serializer is the better default.

**How do I stop sensitive fields from leaking into API responses?**
Use exclusion-by-default. Set `ExclusionPolicy('all')` in JMS, rely on `#[Groups]` in Symfony (ungrouped properties are omitted when groups are active), or return explicit arrays from a Fractal transformer. Blacklists that list fields to hide will eventually miss one.

**Is League Fractal abandoned?**
No. Version 0.21 is the current release and the API has been stable for years; the repository last received a commit in December 2025 and carries 3,544 stars. Treat it as a mature, frozen library rather than an abandoned one, and note that its transformer approach means less churn than annotation-based alternatives.

**Can I use two serialization libraries in the same project?**
You can, and many mature applications do when they migrate gradually, but each additional library adds metadata caches, attribute dialects, and onboarding cost. If you must run two temporarily, isolate them behind a single assembler interface so the rest of the codebase never knows which one produced the payload.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
