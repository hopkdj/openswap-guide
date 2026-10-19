---
title: "AWS Emulators in 2026: LocalStack vs Floci vs Moto for Offline Development"
date: "2026-10-18"
tags: ["aws", "localstack", "testing", "docker", "self-hosted", "comparison"]
draft: false
---

# AWS Emulators in 2026: LocalStack vs Floci vs Moto for Offline Development

The fastest way to slow down a development team is to make every integration test depend on a real cloud account. A test suite that touches S3, SQS, and DynamoDB can burn minutes per run on network latency alone — before you count the cost of the resources it creates and forgets to delete.

Three tools solve this locally, with **100,000+ GitHub stars between them**: LocalStack, the long-standing incumbent; Floci, a newcomer that markets itself as the no-token alternative; and Moto, the Python mocking library that doubles as a standalone server. I have run all three in CI and on developer laptops. They are not interchangeable.

## TL;DR — Quick Verdict

**Pick LocalStack when you need the widest service coverage and you are already standardised on `localhost:4566`.** It is the most complete emulator, it is what most tutorials and Terraform examples assume, and the community edition covers the core services most teams actually use.

**Pick Floci when you want zero friction: no account, no auth token, no feature gates.** It runs the same way, answers on the same port, and removes the single most common complaint about LocalStack — the paid tier gating.

**Pick Moto if your tests are written in Python and you want mocks, not a server.** Its decorators patch boto3 in-process, which is far faster than any HTTP round trip, and its server mode is a bonus for other languages.

**Rule of thumb: unit tests → Moto. Integration tests and Terraform plans → LocalStack or Floci. Never treat any of them as a substitute for a staging account.**

## Head-to-Head Comparison

| Dimension | LocalStack | Floci | Moto |
|---|---|---|---|
| GitHub stars | **65,142** | **26,907** | **8,711** |
| Last push | 2026-03-23 | 2026-10-18 | 2026-10-14 |
| Form factor | Docker service | Docker service | Python library + server |
| Default endpoint | `localhost:4566` | `localhost:4566` | `localhost:5000` |
| Auth token required | For advanced/paid services | **No** | No |
| Service breadth | Very wide | Wide, AWS-shaped | Wide, uneven per service |
| Language support | Any (HTTP) | Any (HTTP) | Python native, others via HTTP |
| Persistence | Optional, configured | Configurable | In-memory by default |
| Speed for unit tests | HTTP overhead | HTTP overhead | **In-process, fastest** |
| Terraform / CDK support | Strong | Documented | Limited |
| Best for | Integration suites | Token-free local stacks | Python unit tests |

The star counts tell a story about momentum, not quality: LocalStack has a decade of mindshare, while Floci's growth in a single year is unusual and reflects genuine frustration with gated features.

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Terraform `plan` and `apply` tests in CI | LocalStack | Provider compatibility is best documented |
| Python unit tests for Lambda handlers | Moto | Decorators avoid HTTP entirely |
| Team refuses to create another account | Floci | No token, no signup |
| Testing S3 presigned URLs and multipart uploads | LocalStack | Most complete S3 behaviour |
| Cross-language integration tests (Go, Node, Java) | LocalStack or Floci | Both are plain HTTP endpoints |
| Simulating IAM policy enforcement | None of them — use a real account | Emulators are permissive by design |
| Offline demo on a laptop with no network | Floci or Moto | Both run fully offline after image pull |

## LocalStack — The Incumbent

LocalStack runs a single container that answers AWS API calls for dozens of services. The documented invocation for the community edition:

```bash
docker run --rm -it \
  -p 127.0.0.1:4566:4566 \
  -p 127.0.0.1:4510-4559:4510-4559 \
  localstack/localstack
```

Point any SDK or CLI at it by overriding the endpoint:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
aws s3 mb s3://demo-bucket
aws sqs create-queue --queue-name jobs
```

**What it does well:** breadth and compatibility. S3, SQS, SNS, DynamoDB, Lambda, Kinesis, Step Functions, IAM, and CloudFormation all answer requests, and the behaviour is close enough that Terraform providers and the AWS CLI work without patching. The port range 4510–4559 exists because several services expect their own listener; mapping it saves you from mysterious connection resets.

**Where it hurts:** the open-core split. Some services and advanced behaviours require an auth token and a paid plan, so a green local test can still hide a feature your account does not have. It is also the heaviest of the three — startup takes several seconds and idle memory is measured in hundreds of megabytes, which matters if your CI runner is small.

## Floci — The Token-Free Drop-In

Floci's pitch is blunt: "No account. No auth token. No feature gates." It provides AWS-shaped services on `localhost:4566` and expects any region and any non-empty credentials unless you explicitly enable stricter checks.

The compose file from its README:

```yaml
services:
  floci:
    image: floci/floci:latest
    ports:
      - "4566:4566"
```

Then export the standard variables and keep your existing workflows:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=local
export AWS_SECRET_ACCESS_KEY=local
export AWS_DEFAULT_REGION=eu-west-1
```

Because it speaks the same endpoint and the same env-var conventions, migrating a test suite from LocalStack is usually a one-line image change.

**What it does well:** zero ceremony. There is no login, no token to rotate, and no "this service requires a paid plan" surprise halfway through a test run. The project also documents partition and region handling, which is the sort of detail that breaks naive emulators when a test hardcodes `us-east-1` but your config says otherwise.

**Where it hurts:** it is young. Deep behavioural parity — S3 multipart edge cases, DynamoDB conditional expressions, Lambda runtime quirks — is where mature emulators earn their keep, and a newer project will have more gaps. Treat it as excellent for the common path and verify anything exotic against a real account before you trust it.

## Moto — Mocking Without the Network

Moto takes a different approach: it patches the SDK in-process. For Python tests, that means no server, no ports, and no HTTP overhead.

```python
import boto3
from moto import mock_aws

@mock_aws
def test_upload_handler():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="uploads")
    s3.put_object(Bucket="uploads", Key="a.txt", Body=b"hello")
    assert s3.get_object(Bucket="uploads", Key="a.txt")["Body"].read() == b"hello"
```

For other languages, or when you need a shared endpoint, run the server:

```bash
docker run --rm -p 5000:5000 --name moto motoserver/moto:latest
```

Then set `AWS_ENDPOINT_URL=http://localhost:5000` in the test environment.

**What it does well:** speed and precision. In-process mocking removes network flakiness entirely and lets you assert on exact call parameters. If a test needs to prove that a function passes the right `ContentType`, that is trivial here and awkward with a server. The standalone image means PHP, Go, and Java suites can use the same mocks.

**Where it hurts:** each service is implemented independently, so coverage is uneven — some services are near-complete, others are stubs that accept a call and return a plausible-looking response. It is also Python-first by design; the server mode works, but the ergonomics and documentation assume you are writing Python.

## Pitfalls That Will Cost You a Debugging Session

**1. Path-style S3 addressing.** Many SDKs default to virtual-hosted-style requests (`bucket.localhost:4566`), which will not resolve. Set `s3ForcePathStyle: true` in the SDK config or `AWS_S3_FORCE_PATH_STYLE=true` where supported. This single issue accounts for most "emulator does not work" reports.

**2. IAM is permissive, so your tests lie.** Emulators generally accept any credentials and ignore most policies. A test that proves "this role cannot read that bucket" will pass locally and fail in production, or worse, pass for the wrong reason. Test authorisation against a real account with a disposable stack.

**3. Persistence is off by default.** Restart the container and your data is gone. If a test suite depends on state surviving a restart, mount a volume and enable the persistence feature explicitly — for Moto, that means configuring `MOTO_PERSISTENCE` style options rather than assuming it.

**4. Region mismatches cause silent 301s.** Emulators are more forgiving about regions than AWS, but some SDKs still build URLs from the region. Pin `AWS_DEFAULT_REGION` in the test environment and in CI, not in a developer's shell profile.

**5. Do not reuse real credentials.** Even though the emulator ignores them, exporting your production keys into a shell that points at `localhost` is how accidental cross-environment calls happen. Use obvious dummy values like `test`/`test` so a misconfiguration fails loudly.

**6. Version drift between emulator and API.** AWS adds fields constantly. An emulator pinned two years ago will silently drop new parameters instead of erroring, so your code appears to work while the field never reaches the service. Refresh the image on a schedule, and run one real-account smoke test per release.

**7. Startup order in compose.** A test container that starts before the emulator is ready will fail with a connection refused that looks like a code bug. Add a health check on `/_localstack/health` or a TCP probe, and gate dependent services on it.

## FAQ

### Is LocalStack free?

The community edition is free and covers the core services most teams need for local development. Advanced services and some behaviours require an auth token tied to a paid plan. If your tests hit a gated feature, they will behave differently than in a fully licensed setup — so check the feature matrix before standardising.

### Can I use these emulators for production?

No. They are development and test tools. They do not provide durability, real isolation, or AWS's security model, and several of them accept any credentials by design. Running one as a production dependency is a data-loss incident waiting for a date.

### Which one works best with Terraform?

LocalStack has the longest track record with Terraform and the most documentation for provider configuration, including examples for overriding endpoints and skipping credential validation. Floci documents the same pattern and generally works, but expect to debug more provider edge cases.

### Does Moto support every AWS service?

No. Coverage is per-service and uneven: the popular services are well implemented, while newer or niche services may only stub the API surface. Check the project's implementation coverage page for your specific service before you design a test suite around it.

### How do I run these in CI without a Docker daemon?

You need a container runtime — all three ship as images (Moto also runs as a Python package, which is the exception). On restricted CI runners, Moto's in-process mode is the only option that avoids Docker entirely, which is a strong argument for Python test suites.

### Can I test Lambda functions locally with these?

Yes, with caveats. LocalStack emulates Lambda execution and can mount your handler code; Moto can mock the invocation API without executing anything. If you need real runtime behaviour, run the function in a container yourself and point its AWS calls at the emulator.

## Related Reading

If your interest is specifically S3-compatible test doubles rather than full cloud emulation, our [LocalStack vs S3ninja vs S3mock comparison](../2026-04-23-localstack-vs-s3ninja-vs-s3mock-self-hosted-s3-testing-tools-2026/) goes deeper on object-storage fakes. For auditing what is actually deployed once you move back to a real account, the [cloud infrastructure querying guide](../2026-04-27-cloudquery-vs-steampipe-vs-cartography-cloud-infrastructure-querying-guide-2026/) covers CloudQuery, Steampipe, and Cartography. And if you are containerising the surrounding developer tooling, the [Docker control panel comparison](../2026-10-07-self-hosted-docker-control-panels-dokploy-komodo-arcane/) is worth a look.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "AWS Emulators in 2026: LocalStack vs Floci vs Moto for Offline Development",
  "description": "A comparison of three local AWS emulators for offline development and CI: LocalStack, Floci, and Moto, with real Docker commands, service coverage trade-offs, and the pitfalls that break test suites.",
  "datePublished": "2026-10-18",
  "dateModified": "2026-10-18",
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
