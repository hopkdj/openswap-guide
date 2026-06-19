---
title: "Unit Test Mocking Libraries: Mockito vs Sinon.js vs GoMock vs TestDouble.js"
date: "2026-06-20"
tags: ["testing", "unit-testing", "developer-tools", "java", "javascript", "golang", "mock", "tdd", "libraries"]
draft: false
---

Unit testing is the foundation of software quality, but real-world code has dependencies — databases, HTTP clients, file systems, external APIs. Mocking libraries let you replace these dependencies with controlled test doubles, isolating the unit under test and making tests deterministic, fast, and reliable.

This article compares four leading open-source mocking libraries: **Mockito** (Java/JVM), **Sinon.js** (JavaScript), **GoMock** (Go), and **TestDouble.js** (JavaScript). Each takes a different philosophical approach to test doubles, shaped by the idioms of their host language.

## Test Double Taxonomy: Mocks, Stubs, Spies, and Fakes

Before comparing libraries, it's essential to understand the types of test doubles. Gerard Meszaros's xUnit Test Patterns defines four main categories:

- **Stubs** provide canned answers to calls during the test. They don't have expectations — they simply return predetermined values. Use stubs when you need a dependency to provide data without caring how many times it's called.

- **Mocks** are pre-programmed with expectations about which calls they should receive. If an expected call doesn't happen (or an unexpected call does), the mock fails the test. Use mocks when you need to verify interaction patterns — "was this method called exactly once with these arguments?"

- **Spies** wrap real objects and record all interactions without changing behavior. After the test, you inspect the spy to verify what happened. Use spies when you have a real implementation but need to verify how it was used.

- **Fakes** are working implementations with shortcuts (e.g., an in-memory database instead of PostgreSQL). They're not the focus of this article but are a valuable testing pattern for integration tests.

Different libraries emphasize different test double types. Mockito focuses on mocks with strong verification. Sinon.js provides equal support for spies, stubs, and mocks. GoMock generates type-safe mocks from interfaces. TestDouble.js emphasizes test readability over magic.

## Library-by-Library Deep Dive

### Mockito (Java/JVM) — 15,400+ Stars

Mockito is the most widely used mocking framework in the Java ecosystem. Its philosophy is simple: create mock objects with minimal ceremony, define behavior when needed, and verify interactions after the fact. It integrates seamlessly with JUnit, TestNG, and Spring Boot testing.

```java
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

// The system under test
class OrderService {
    private final PaymentGateway paymentGateway;
    private final InventoryService inventoryService;
    private final EmailNotifier emailNotifier;

    public OrderService(PaymentGateway pg, InventoryService inv, EmailNotifier email) {
        this.paymentGateway = pg;
        this.inventoryService = inv;
        this.emailNotifier = email;
    }

    public OrderResult placeOrder(Order order) {
        if (!inventoryService.checkStock(order.getItemId(), order.getQuantity())) {
            return OrderResult.INSUFFICIENT_STOCK;
        }
        PaymentResult payment = paymentGateway.charge(
            order.getCustomerId(), order.getTotalAmount()
        );
        if (payment.isSuccess()) {
            inventoryService.reserve(order.getItemId(), order.getQuantity());
            emailNotifier.sendConfirmation(order.getCustomerEmail(), order.getOrderId());
            return OrderResult.SUCCESS;
        }
        return OrderResult.PAYMENT_FAILED;
    }
}

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock PaymentGateway paymentGateway;
    @Mock InventoryService inventoryService;
    @Mock EmailNotifier emailNotifier;

    @Test
    void shouldCompleteOrderWhenPaymentSucceeds() {
        // Arrange
        Order order = new Order("CUST-1", "ITEM-42", 2, 199.98, "user@example.com");
        when(inventoryService.checkStock("ITEM-42", 2)).thenReturn(true);
        when(paymentGateway.charge("CUST-1", 199.98))
            .thenReturn(PaymentResult.success("TXN-123"));

        // Act
        OrderService service = new OrderService(paymentGateway, inventoryService, emailNotifier);
        OrderResult result = service.placeOrder(order);

        // Assert
        assertEquals(OrderResult.SUCCESS, result);
        verify(inventoryService).reserve("ITEM-42", 2);
        verify(emailNotifier).sendConfirmation("user@example.com", order.getOrderId());
    }

    @Test
    void shouldFailWhenStockInsufficient() {
        Order order = new Order("CUST-1", "ITEM-42", 99, 9.99, "user@example.com");
        when(inventoryService.checkStock("ITEM-42", 99)).thenReturn(false);

        OrderService service = new OrderService(paymentGateway, inventoryService, emailNotifier);
        OrderResult result = service.placeOrder(order);

        assertEquals(OrderResult.INSUFFICIENT_STOCK, result);
        // Payment should never be attempted if stock check fails
        verify(paymentGateway, never()).charge(anyString(), anyDouble());
    }
}
```

**Key features:** Annotation-driven mock creation, argument matchers (any(), eq(), argThat()), partial mocking with spy(), verifyNoMoreInteractions() for strict verification, InOrder for sequence verification, BDDMockito for BDD-style tests.

### Sinon.js (JavaScript) — 9,700+ Stars

Sinon.js is the Swiss Army knife of JavaScript testing. It provides standalone spies, stubs, and mocks that work with any test framework (Mocha, Jest, Jasmine, Ava). Unlike Mockito's annotation-based approach, Sinon uses explicit method calls to create and control test doubles.

```javascript
const sinon = require('sinon');
const { expect } = require('chai');

// System under test
class UserRegistrationService {
  constructor(userRepository, emailService, auditLogger) {
    this.userRepository = userRepository;
    this.emailService = emailService;
    this.auditLogger = auditLogger;
  }

  async register(userData) {
    if (!userData.email || !userData.email.includes('@')) {
      throw new Error('Invalid email');
    }

    const existing = await this.userRepository.findByEmail(userData.email);
    if (existing) {
      throw new Error('Email already registered');
    }

    const user = await this.userRepository.create({
      ...userData,
      createdAt: new Date(),
      status: 'pending_verification',
    });

    await this.emailService.sendWelcomeEmail(user.email, user.verificationToken);
    this.auditLogger.log('user_registered', { userId: user.id, email: user.email });

    return user;
  }
}

describe('UserRegistrationService', () => {
  let service, userRepo, emailService, auditLogger;

  beforeEach(() => {
    userRepo = {
      findByEmail: sinon.stub(),
      create: sinon.stub(),
    };
    emailService = {
      sendWelcomeEmail: sinon.stub().resolves(),
    };
    auditLogger = {
      log: sinon.spy(),
    };
    service = new UserRegistrationService(userRepo, emailService, auditLogger);
  });

  afterEach(() => {
    sinon.restore();
  });

  it('should register a new user successfully', async () => {
    const userData = { email: 'new@example.com', name: 'Alice' };
    userRepo.findByEmail.withArgs('new@example.com').resolves(null);
    userRepo.create.resolves({
      id: 'user-123', email: 'new@example.com', verificationToken: 'tok-abc',
    });

    const result = await service.register(userData);

    expect(result.id).to.equal('user-123');
    sinon.assert.calledOnceWithExactly(userRepo.findByEmail, 'new@example.com');
    sinon.assert.calledWith(emailService.sendWelcomeEmail, 'new@example.com', 'tok-abc');
    sinon.assert.calledWith(auditLogger.log, 'user_registered',
      sinon.match({ userId: 'user-123' }));
  });

  it('should reject duplicate emails', async () => {
    userRepo.findByEmail.resolves({ id: 'existing', email: 'dup@example.com' });

    try {
      await service.register({ email: 'dup@example.com', name: 'Bob' });
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err.message).to.equal('Email already registered');
    }

    sinon.assert.notCalled(userRepo.create);
    sinon.assert.notCalled(emailService.sendWelcomeEmail);
  });
});
```

**Key features:** Standalone (no framework dependency), spies that wrap real objects, stubs with programmable behavior, fake timers (useFakeTimers()), fake XHR/server (createFakeServer()), sandbox for automatic cleanup.

### GoMock (Go) — 3,300+ Stars

GoMock takes a fundamentally different approach from Mockito and Sinon. Instead of runtime magic, it uses code generation. You define an interface, run mockgen, and it produces a type-safe mock implementation. This compile-time safety aligns perfectly with Go's philosophy.

```go
// interfaces.go — define the interface to mock
package orders

import "context"

type PaymentProcessor interface {
    Charge(ctx context.Context, customerID string, amount float64) (*PaymentResult, error)
    Refund(ctx context.Context, transactionID string, amount float64) (*RefundResult, error)
}

// Generate mock: mockgen -source=interfaces.go -destination=mocks/mock_payment.go

// order_service_test.go
func TestProcessOrder_Success(t *testing.T) {
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()

    mockPayments := mocks.NewMockPaymentProcessor(ctrl)
    mockDB := mocks.NewMockOrderRepository(ctrl)

    ctx := context.Background()
    order := &Order{
        CustomerID: "cust-1",
        Amount:     99.99,
        Items:      []string{"item-1"},
    }

    mockPayments.EXPECT().
        Charge(ctx, "cust-1", 99.99).
        Return(&PaymentResult{TransactionID: "txn-abc"}, nil).
        Times(1)

    mockDB.EXPECT().
        Save(ctx, gomock.Any()).
        DoAndReturn(func(_ context.Context, o *Order) error {
            if o.TransactionID != "txn-abc" {
                t.Errorf("expected TransactionID txn-abc, got %s", o.TransactionID)
            }
            return nil
        })

    service := &OrderService{payments: mockPayments, db: mockDB}
    err := service.ProcessOrder(ctx, order)

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
}

func TestProcessOrder_PaymentFailure(t *testing.T) {
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()

    mockPayments := mocks.NewMockPaymentProcessor(ctrl)
    mockDB := mocks.NewMockOrderRepository(ctrl)

    ctx := context.Background()
    order := &Order{CustomerID: "cust-1", Amount: 50.00}

    mockPayments.EXPECT().
        Charge(ctx, "cust-1", 50.00).
        Return(nil, errors.New("insufficient funds"))

    mockDB.EXPECT().Save(ctx, gomock.Any()).Times(0)

    service := &OrderService{payments: mockPayments, db: mockDB}
    err := service.ProcessOrder(ctx, order)

    if err == nil {
        t.Fatal("expected error, got nil")
    }
}
```

**Key features:** Compile-time type safety, gomock.Any() matchers, DoAndReturn() for custom behavior, strict verification via ctrl.Finish(), InOrder() for sequence verification.

### TestDouble.js (JavaScript) — 1,400+ Stars

TestDouble.js takes a readability-first approach. Instead of the mock(), stub(), spy() terminology that confuses newcomers, it uses a single unified concept: test doubles that replace real dependencies. Its API is designed to read like natural English.

```javascript
const td = require('testdouble');

// System under test
class NewsletterService {
  constructor(subscriberDB, mailer, templateEngine) {
    this.subscriberDB = subscriberDB;
    this.mailer = mailer;
    this.templateEngine = templateEngine;
  }

  async sendNewsletter(campaignId, authorId) {
    const subscribers = await this.subscriberDB.getActiveSubscribers();
    if (subscribers.length === 0) {
      return { sent: 0, status: 'no_subscribers' };
    }

    const template = await this.templateEngine.render('newsletter', {
      campaignId, authorId,
    });

    let sent = 0;
    for (const sub of subscribers) {
      try {
        await this.mailer.send({
          to: sub.email,
          subject: template.subject,
          body: template.body,
        });
        sent++;
      } catch (err) {
        console.error(`Failed to send to ${sub.email}:`, err.message);
      }
    }

    return { sent, status: sent === subscribers.length ? 'complete' : 'partial' };
  }
}

describe('NewsletterService', function() {
  let service, subscriberDB, mailer, templateEngine;

  beforeEach(function() {
    subscriberDB = td.object(['getActiveSubscribers']);
    mailer = td.object(['send']);
    templateEngine = td.object(['render']);
    service = new NewsletterService(subscriberDB, mailer, templateEngine);
  });

  afterEach(function() {
    td.reset();
  });

  it('sends newsletter to all active subscribers', async function() {
    const subscribers = [
      { email: 'alice@example.com' },
      { email: 'bob@example.com' },
    ];

    td.when(subscriberDB.getActiveSubscribers()).thenResolve(subscribers);
    td.when(templateEngine.render('newsletter', td.matchers.anything()))
      .thenResolve({ subject: 'Monthly Update', body: '<h1>News</h1>' });
    td.when(mailer.send(td.matchers.anything())).thenResolve();

    const result = await service.sendNewsletter('camp-1', 'author-1');

    expect(result.sent).to.equal(2);
    expect(result.status).to.equal('complete');

    td.verify(mailer.send({ to: 'alice@example.com', subject: 'Monthly Update', body: '<h1>News</h1>' }));
    td.verify(mailer.send({ to: 'bob@example.com', subject: 'Monthly Update', body: '<h1>News</h1>' }));
  });

  it('handles partial send failures gracefully', async function() {
    const subscribers = [
      { email: 'good@example.com' },
      { email: 'bad@example.com' },
    ];

    td.when(subscriberDB.getActiveSubscribers()).thenResolve(subscribers);
    td.when(templateEngine.render(td.matchers.anything(), td.matchers.anything()))
      .thenResolve({ subject: 'Test', body: 'body' });

    td.when(mailer.send(td.matchers.contains({ to: 'good@example.com' })))
      .thenResolve();
    td.when(mailer.send(td.matchers.contains({ to: 'bad@example.com' })))
      .thenReject(new Error('SMTP error'));

    const result = await service.sendNewsletter('camp-1', 'author-1');

    expect(result.sent).to.equal(1);
    expect(result.status).to.equal('partial');
  });
});
```

**Key features:** Unified td.object(), td.function(), td.constructor() API, natural language assertions via td.verify(), argument matchers (td.matchers.contains(), td.matchers.isA()), td.replace() for module-level mocking, Jest/Mocha integration.

## Feature Comparison Table

| Feature | Mockito | Sinon.js | GoMock | TestDouble.js |
|---------|---------|----------|--------|---------------|
| **Language** | Java/Kotlin/Scala | JavaScript/TypeScript | Go | JavaScript/TypeScript |
| **GitHub Stars** | 15,400+ | 9,700+ | 3,300+ | 1,400+ |
| **Mock Creation** | Annotations + mock() | sinon.stub() / sinon.mock() | Code generation (mockgen) | td.object() / td.func() |
| **Spies** | spy() wraps real object | sinon.spy() | Not first-class | Unified API |
| **Stubs** | when().thenReturn() | stub().returns() | EXPECT().Return() | td.when().thenReturn() |
| **Type Safety** | Java type system | Dynamic (TS types available) | Compile-time + generated | Dynamic (TS types) |
| **Argument Matchers** | any(), eq(), argThat() | sinon.match() | gomock.Any(), gomock.Eq() | td.matchers |
| **Verification** | verify() + verifyNoMoreInteractions() | sinon.assert.calledWith() | Auto-verify via ctrl.Finish() | td.verify() |
| **Framework Integration** | JUnit, TestNG, Spring | Any (Mocha, Jest, Ava) | testing (stdlib) | Any (Mocha, Jest, Ava) |
| **Learning Curve** | Moderate | Moderate | Steep (code gen) | Low (unified API) |
| **License** | MIT | BSD-3 | Apache 2.0 | MIT |

## Choosing the Right Mocking Library

The choice depends primarily on your language ecosystem and testing philosophy. Mockito is the undisputed standard for JVM languages — it's mature, well-documented, and has the largest community. Its annotation-based approach with @ExtendWith(MockitoExtension.class) minimizes boilerplate.

Sinon.js excels when you need maximum flexibility. Its standalone nature means it works with any test runner, and its useFakeTimers() feature is invaluable for testing timeout-based logic, debouncing, and scheduled tasks. It's particularly strong for legacy code testing where you need to spy on existing objects without refactoring.

GoMock is the right choice for Go projects where interface-based design is already the norm. The code generation step adds friction during initial setup, but the compile-time safety catches mock/interface mismatches before tests even run. GoMock's strict verification (ctrl.Finish()) means unmet expectations fail the test — a feature that catches undertested code paths.

TestDouble.js shines when team readability is the priority. Its unified API eliminates the "mock vs stub vs spy" terminology debate, and td.verify() reads like English. Teams new to mocking often find TestDouble.js more approachable than Sinon.js, though Sinon's larger ecosystem (fake timers, fake XHR) gives it an edge for complex testing scenarios.

For API-level mocking (HTTP endpoints and service boundaries), see our [self-hosted API mocking tools guide](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/). For end-to-end browser testing, check our [self-hosted E2E testing tools comparison](../self-hosted-e2e-testing-tools-playwright-cypress-selenium-guide-2026/). For property-based testing approaches that complement mocking, see our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/).

## FAQ

### When should I use a mock vs a stub?

Use a stub when you need to provide controlled data to the system under test and don't care about the interaction details. Use a mock when the interaction itself matters — you need to verify that a specific method was called with specific arguments. Martin Fowler's classic article "Mocks Aren't Stubs" articulates this as the difference between state verification (stubs) and behavior verification (mocks).

### Does GoMock work with Go's generics?

Yes, as of Go 1.18+ with gomock v1.7+. Mockgen can generate mocks for generic interfaces. The generated mock uses type parameters and works with gomock.Any() matchers. You may need to use the -typed flag with mockgen for certain generic scenarios. The Go testing ecosystem around generics is still maturing, so expect occasional rough edges.

### How do I mock HTTP requests without a real server?

Mockito can mock HTTP clients (e.g., Spring's RestTemplate or OkHttp). Sinon.js provides useFakeXMLHttpRequest() to intercept XHR calls. GoMock works best when you abstract HTTP behind an interface. TestDouble.js pairs with td.replace() for module-level HTTP client mocking. For full HTTP API mocking at the network level rather than code level, use WireMock or MockServer.

### Can I mock static methods and final classes?

Mockito supports mocking static methods and final classes via mockito-inline (since Mockito 3.4+). Use try-with-resources for static method mocking: MockedStatic<ClassName> mocked = mockStatic(ClassName.class). Sinon.js can mock any exported function via module interception. GoMock cannot mock unexported or package-level functions — refactor them behind an interface if testing is needed. TestDouble.js uses td.replace() for any module-level function.

### Why does verifyNoMoreInteractions() sometimes cause test brittleness?

verifyNoMoreInteractions() is strict — it fails if ANY interaction on the mock wasn't explicitly verified. This can make tests brittle when you add new functionality that calls additional methods on the mock. Most testing experts recommend using verifyNoMoreInteractions() sparingly, primarily in tests that verify negative behavior (e.g., "payment should never be called when stock is zero"). Overusing it couples tests too tightly to implementation details.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Unit Test Mocking Libraries: Mockito vs Sinon.js vs GoMock vs TestDouble.js",
  "description": "Compare four leading open-source mocking libraries across Java, JavaScript, and Go. Code examples, test double taxonomy, and guidelines for choosing between mocks, stubs, and spies.",
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
