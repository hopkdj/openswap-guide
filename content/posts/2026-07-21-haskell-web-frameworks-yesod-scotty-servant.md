---
title: "Haskell Web Frameworks: Yesod vs Scotty vs Servant — Type-Safe Web Development Compared"
date: "2026-07-21"
tags: ["haskell", "web-frameworks", "yesod", "scotty", "servant", "functional-programming", "type-safety"]
draft: false
---

Haskell brings unparalleled type safety to web development. Three frameworks dominate the ecosystem, each representing a different point on the type-safety-vs-simplicity spectrum: **Yesod** (a full-stack, compile-time-safe framework), **Scotty** (a Sinatra-inspired micro-framework), and **Servant** (a type-level API definition library). Choosing between them means choosing how much the compiler should enforce at build time versus how quickly you can ship a prototype.

## Comparison Table

| Feature | Yesod | Scotty | Servant |
|---------|-------|--------|---------|
| **GitHub Stars** | ~2,600 | ~1,700 | ~1,800 |
| **Type Safety** | Compile-time routes, templates, DB | Runtime routing only | Compile-time API types, client/server |
| **Routing** | Type-safe DSL via Template Haskell | Simple `get`/`post`/`put`/`delete` | Type-level combinators |
| **Templates** | Shakespeare (compile-time checked) | Blaze Html or any | No built-in templating (use Lucid, Blaze) |
| **Database** | Persistent (type-safe ORM) | Manual (any library) | Manual (any library) |
| **Client Generation** | No | No | Automatic (Haskell, JS, TypeScript, Python, Ruby) |
| **OpenAPI/Swagger** | No | No | Automatic from types |
| **Middleware** | Yesod Middleware | WAI Middleware | WAI Middleware |
| **Async Support** | Yes (Warp server, async) | Yes (Warp) | Yes (Warp, async handlers) |
| **Learning Curve** | High (Template Haskell, Persistent) | Low (simple DSL) | Medium-High (type-level programming) |

## Getting Started: A Simple Todo API

### Scotty — The Micro-Framework

Scotty is the easiest to start with. Like Ruby's Sinatra, it maps HTTP methods directly to handler functions:

```haskell
{-# LANGUAGE OverloadedStrings #-}
import Web.Scotty
import Data.Aeson (object, (.=), ToJSON)
import GHC.Generics

data Todo = Todo
  { todoId :: Int
  , title :: String
  , completed :: Bool
  } deriving (Generic)

instance ToJSON Todo

todos :: [Todo]
todos = [Todo 1 "Learn Haskell" False, Todo 2 "Build API" True]

main :: IO ()
main = scotty 3000 $ do
  get "/todos" $ do
    json todos

  get "/todos/:id" $ do
    tid <- param "id"
    case filter (\t -> todoId t == tid) todos of
      [t] -> json t
      _   -> status status404 >> json (object ["error" .= ("Not found" :: String)])

  post "/todos" $ do
    title <- param "title"
    let newTodo = Todo (length todos + 1) title False
    status status201 >> json newTodo
```

### Servant — Type-Level API Design

Servant defines your entire API as a type. The compiler then verifies your handlers match the specification:

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE TypeOperators #-}
import Servant
import Network.Wai.Handler.Warp (run)
import Data.Aeson (ToJSON)
import GHC.Generics

data Todo = Todo
  { todoId :: Int
  , title :: String
  , completed :: Bool
  } deriving (Generic)

instance ToJSON Todo

-- The API type — this IS your contract
type TodoAPI = "todos" :> Get '[JSON] [Todo]
          :<|> "todos" :> Capture "id" Int :> Get '[JSON] Todo
          :<|> "todos" :> ReqBody '[JSON] Todo :> Post '[JSON] Todo

-- Handler implementation must match the type exactly
todoHandlers :: Server TodoAPI
todoHandlers = getTodos :<|> getTodoById :<|> createTodo

getTodos :: Handler [Todo]
getTodos = return [Todo 1 "Learn Servant" False]

getTodoById :: Int -> Handler Todo
getTodoById tid = case lookupTodo tid of
  Just t  -> return t
  Nothing -> throwError err404

createTodo :: Todo -> Handler Todo
createTodo todo = return todo

main :: IO ()
main = run 3000 $ serve (Proxy :: Proxy TodoAPI) todoHandlers
```

The magic of Servant: the same `TodoAPI` type can automatically generate client libraries and Swagger documentation:

```haskell
-- Automatic client generation
getTodosClient :: ClientM [Todo]
getTodosClient :<|> getTodoByIdClient :<|> createTodoClient =
    client (Proxy :: Proxy TodoAPI)

-- Automatic Swagger docs
todoSwagger :: Swagger
todoSwagger = toSwagger (Proxy :: Proxy TodoAPI)
```

### Yesod — Full-Stack, Compile-Time Safe

Yesod ensures correctness at compile time. Routes, templates, and database queries are all checked before your app runs. Here is a minimal Yesod application with type-safe routing:

```haskell
{-# LANGUAGE QuasiQuotes, TemplateHaskell, TypeFamilies #-}
import Yesod

data App = App
mkYesod "App" [parseRoutes|
/             HomeR     GET
/todos        TodoListR GET POST
/todos/#Int   TodoDetailR GET
|]

instance Yesod App

getTodoListR :: Handler Html
getTodoListR = do
    todos <- runDB $ selectList [] [LimitTo 10]
    defaultLayout [whamlet|
<h1>Todo List
<ul>
    $forall Entity tid todo <- todos
        <li>#{todoTitle todo}
|]

main :: IO ()
main = warp 3000 App
```

## Type Safety in Practice

The key philosophical difference between these frameworks is when errors are caught:

- **Scotty**: Errors surface at runtime — typos in route patterns or missing query parameters are only caught when you hit that endpoint. This makes prototyping fast but requires thorough integration testing.
- **Servant**: API mismatches are caught at compile time — add a field to your response type and the compiler tells you every handler that needs updating before you can even build the binary. This eliminates entire classes of bugs.
- **Yesod**: Everything is compile-time — routes, templates, and database schemas are all verified. A typo in a template variable name or a missing database column produces a compiler error, not a 500 error at 3 AM.

## Deployment Architecture and Self-Hosting

Haskell's Warp server — the underlying HTTP engine for all three frameworks — is one of the fastest web servers available. A typical production deployment uses Nginx as a reverse proxy in front of Warp, with systemd for process supervision:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

For production Haskell deployments, compile with full optimizations:

```bash
# Build with maximum optimization
cabal build --enable-optimization=2

# Run with systemd supervision
systemd-run --unit=haskell-api ./dist/build/api/api
```

Haskell's green-thread runtime means a single Warp process can handle thousands of concurrent connections efficiently. For high-availability deployments, run multiple Warp processes behind Nginx with round-robin load balancing.

## Performance Characteristics

All three frameworks sit atop the same Warp HTTP server, so raw throughput is similar. Where they differ is startup time and memory usage:

| Metric | Yesod | Scotty | Servant |
|--------|-------|--------|---------|
| **Binary Size** | 15-25MB | 5-8MB | 5-10MB |
| **Compile Time** | 2-5 min (TH heavy) | 30s-1min | 1-2 min |
| **Requests/sec** | ~50K (Warp) | ~50K (Warp) | ~50K (Warp) |
| **Memory Baseline** | 25-40MB | 8-15MB | 10-20MB |

For broader web framework comparisons across languages, see our [Rust web frameworks guide](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) and our [Java web frameworks comparison](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/).

## FAQ

### Is Haskell suitable for production web applications?

Absolutely. Companies like Standard Chartered, Facebook (Haxl, Sigma), and Hasura use Haskell in production. Warp, the underlying HTTP server, handles millions of concurrent connections. The primary trade-off is developer availability — finding Haskell developers is harder than finding Node.js or Python developers, but the type safety guarantees mean fewer production incidents and less debugging time.

### Which framework should I use for a REST API?

Servant is the best choice for REST APIs. Its type-level API specifications serve as living documentation, auto-generate client libraries in multiple languages, and catch endpoint mismatches at compile time. For a quick prototype, Scotty's simplicity can't be beat — you can have an API running in under 50 lines of code. Yesod is ideal for full-stack applications with server-rendered HTML and database integration.

### What is Template Haskell and why does Yesod use it?

Template Haskell (TH) is Haskell's compile-time metaprogramming system. Yesod uses TH to parse route files, validate templates, and generate database schemas at compile time rather than runtime. This means path typos, missing template variables, and schema mismatches become compiler errors instead of runtime surprises. The cost is longer compilation times and a steeper learning curve, but the safety payoff is significant for large applications.

### How does Servant automatically generate client libraries?

Servant's API types are regular Haskell types at the type level. The `client` function interprets the API type at compile time and generates functions for each endpoint. Because the API specification is just a type, it can produce not just Haskell clients but also JavaScript, TypeScript, and Python clients by interpreting the same type structure through different code generation backends. This eliminates the common problem of client-server contract drift.

### Do I need to know category theory to use Haskell web frameworks?

No! While Haskell's academic reputation can be intimidating, building web applications with these frameworks requires only basic Haskell knowledge — algebraic data types, functions, and IO. Servant's type-level programming looks complex at first but becomes intuitive with practice. Scotty, in particular, reads like a simple DSL and is accessible to newcomers. Start with Scotty, graduate to Servant for APIs, and explore Yesod when you need full-stack features.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Haskell Web Frameworks: Yesod vs Scotty vs Servant — Type-Safe Web Development Compared",
  "description": "A comprehensive comparison of Haskell web frameworks Yesod, Scotty, and Servant covering type safety, REST API design, automatic client generation, and self-hosting deployment with Nginx and Warp.",
  "datePublished": "2026-07-21",
  "dateModified": "2026-07-21",
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
