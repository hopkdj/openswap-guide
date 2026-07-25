---
title: "JavaScript GraphQL Client Libraries Compared: Apollo Client vs urql vs graphql-request"
date: "2026-07-26"
tags: ["javascript", "graphql", "typescript", "api-client", "react", "js-libraries"]
draft: false
---

## Introduction

Choosing the right GraphQL client shapes your entire data-fetching architecture. In the JavaScript ecosystem, three libraries represent different philosophies: **Apollo Client** (19,806 stars) is the feature-complete, industry-standard solution, **urql** (8,965 stars) offers a lightweight, extensible alternative with a functional approach, and **graphql-request** (6,113 stars) provides a minimal client for simple queries and mutations. Each targets a different segment of the complexity spectrum.

This comparison examines caching strategies, bundle size, React integration, TypeScript support, error handling, and the trade-offs between comprehensive features and minimal overhead. Whether you're building a large-scale React application with complex state management or a simple Node.js script that needs to query a GraphQL endpoint, this guide helps you choose wisely.

## Feature Comparison

| Feature | Apollo Client | urql | graphql-request |
|---------|--------------|------|-----------------|
| Stars | 19,806 | 8,965 | 6,113 |
| Bundle Size | ~35 KB gzipped | ~8 KB gzipped | ~5 KB gzipped |
| Normalized Cache | Yes (built-in) | Optional (via @urql/exchange-graphcache) | No |
| React Support | First-class | First-class | Manual |
| Framework Agnostic | Core only | Core only | Yes (fully agnostic) |
| Subscriptions | Built-in (WebSocket, SSE) | Via exchanges | No |
| TypeScript | Full support | Full support | Full support |
| DevTools | Apollo DevTools extension | urql DevTools extension | N/A |
| File Uploads | Yes (apollo-upload-client) | No built-in | No built-in |
| Pagination | fetchMore, relay-style | Via exchanges | Manual |
| Learning Curve | Moderate-High | Low-Moderate | Very Low |

## Library Deep Dives

### Apollo Client (`apollographql/apollo-client`)

Apollo Client is the most comprehensive GraphQL client for JavaScript, with a built-in normalized cache, advanced mutation management, optimistic updates, and a rich developer tooling ecosystem. It's backed by Apollo Graph and used by companies like Airbnb, The New York Times, and Shopify.

```javascript
import { ApolloClient, InMemoryCache, gql, useQuery } from '@apollo/client';

// Client setup
const client = new ApolloClient({
  uri: 'https://api.example.com/graphql',
  cache: new InMemoryCache({
    typePolicies: {
      User: {
        keyFields: ['id'],
        fields: {
          fullName: {
            read(_, { readField }) {
              return `${readField('firstName')} ${readField('lastName')}`;
            }
          }
        }
      }
    }
  })
});

// React component with useQuery
const GET_USER = gql`
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      firstName
      lastName
      email
      posts {
        id
        title
      }
    }
  }
`;

function UserProfile({ userId }) {
  const { loading, error, data } = useQuery(GET_USER, {
    variables: { id: userId },
    fetchPolicy: 'cache-first',
    pollInterval: 30000,
  });

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>{data.user.firstName} {data.user.lastName}</h1>
      <p>{data.user.email}</p>
    </div>
  );
}
```

**Strengths:** The normalized cache (`InMemoryCache`) is the gold standard — it automatically deduplicates entities, merges query results, and updates all dependent UI components when cached data changes. The `fetchPolicy` system gives fine-grained control over cache behavior (cache-first, network-only, cache-and-network, no-cache, standby). Apollo DevTools provides a browser extension for inspecting queries, mutations, and cache state in real-time. The `useMutation` hook supports optimistic updates for instant UI feedback.

**Weaknesses:** Large bundle size (~35 KB gzipped) can impact initial load times for performance-sensitive apps. The normalized cache adds complexity — cache eviction, field policies, and type policies require careful configuration. Breaking changes between Apollo Client 2.x and 3.x frustrated many developers. For simple use cases, Apollo's feature set is overkill.

### urql (`urql-graphql/urql`)

urql (Universal React Query Library) takes a functional, exchange-based approach to GraphQL clients. The core is minimal (~8 KB gzipped), with features added through composable "exchanges" — middleware-like functions that form a pipeline for each GraphQL operation.

```javascript
import { createClient, Provider, useQuery, cacheExchange, fetchExchange } from 'urql';

// Client setup with exchanges
const client = createClient({
  url: 'https://api.example.com/graphql',
  exchanges: [
    cacheExchange,
    fetchExchange,
  ],
});

// React component
const GET_USER = `
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      firstName
      lastName
      email
    }
  }
`;

function UserProfile({ userId }) {
  const [result] = useQuery({
    query: GET_USER,
    variables: { id: userId },
  });

  const { data, fetching, error } = result;

  if (fetching) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>{data.user.firstName} {data.user.lastName}</h1>
      <p>{data.user.email}</p>
    </div>
  );
}
```

**Strengths:** Minimal bundle size and simple API make it ideal for performance-sensitive applications. The exchange architecture is elegant — add features like normalized caching (`@urql/exchange-graphcache`), retry logic (`@urql/exchange-retry`), authentication (`@urql/exchange-auth`), or multipart uploads through additional exchanges. Excellent TypeScript support with typed documents via `@graphql-codegen`. The `useQuery` hook's tuple return pattern (`[result, executeQuery]`) is consistent and predictable.

**Weaknesses:** The basic `cacheExchange` only provides document caching (not normalized) — you need `@urql/exchange-graphcache` for sophisticated cache operations, which adds complexity. Smaller ecosystem and community than Apollo. Fewer tutorials and learning resources. The exchange API, while powerful, has a learning curve for debugging when exchanges interfere with each other.

### graphql-request (`jasonkuhrt/graphql-request`)

graphql-request is a minimal GraphQL client focused on simplicity. It provides a small set of functions for sending queries and mutations, with no caching, no React integration, and no normalization — just clean request/response handling.

```javascript
import { GraphQLClient, gql } from 'graphql-request';

// Client setup
const client = new GraphQLClient('https://api.example.com/graphql', {
  headers: {
    authorization: 'Bearer YOUR_TOKEN',
  },
});

const GET_USER = gql`
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      firstName
      lastName
      email
    }
  }
`;

async function getUser(userId) {
  try {
    const data = await client.request(GET_USER, { id: userId });
    console.log(`${data.user.firstName} ${data.user.lastName}`);
    return data;
  } catch (error) {
    console.error('GraphQL error:', error.response?.errors || error.message);
  }
}
```

**Strengths:** Extemely lightweight (~5 KB gzipped) with zero dependencies. API is dead simple — `request()`, `batchRequests()`, and `rawRequest()`. Works everywhere: Node.js, Deno, Cloudflare Workers, and browsers (via a single fetch call). Perfect for server-side GraphQL queries, build scripts, CI/CD pipelines, and simple web apps that don't need a full client. First-class TypeScript support with typed documents.

**Weaknesses:** No caching whatsoever — every `request()` call hits the network. No React integration — you must handle loading states, errors, and data manually. No subscription support. No built-in retry, deduplication, or batching logic (though `batchRequests()` provides basic batching). For complex frontend applications, the missing features quickly become burdensome.

## Bundle Size and Performance

At bundle sizes of 35 KB (Apollo), 8 KB (urql), and 5 KB (graphql-request), the performance impact varies significantly. For a content-heavy blog or marketing site, the 30 KB difference is negligible. For a mobile-first progressive web app targeting 50 KB total JavaScript budget, urql or graphql-request are essential choices.

In runtime performance: Apollo's normalized cache delivers the best performance for complex UIs with overlapping data — a single mutation can update dozens of components through cache normalization. urql's document cache works well for simpler data graphs where queries don't share entities. graphql-request has no cache overhead but pays the network cost on every query.

## Choosing the Right Library

| Use Case | Recommended Library |
|----------|-------------------|
| Large React app with complex data | Apollo Client |
| Performance-sensitive React app | urql |
| Server-side scripts, Node.js jobs | graphql-request |
| GraphQL API testing | graphql-request |
| Micro-frontend with simple data | urql |
| Full-featured with DevTools | Apollo Client |

For building GraphQL APIs, see our [GraphQL server libraries comparison](../2026-06-20-graphql-server-libraries-apollo-yoga-mercurius-strawberry-hotchocolate/). For Go-based GraphQL services, check our [Go GraphQL libraries guide](../2026-06-22-go-graphql-libraries-gqlgen-graphqlgo-graphgophers-guide/). For documenting your GraphQL API, our [API documentation tools comparison](../2026-06-14-api-documentation-redoc-scalar-stoplight-elements/) has you covered.

The JavaScript GraphQL client ecosystem offers a clear spectrum: Apollo Client for comprehensive data management, urql for a lightweight but extensible alternative, and graphql-request for minimal, no-frills queries. Match the library to your application's data complexity — you can always start simple and migrate up as your needs grow.

## FAQ

### Can I use multiple GraphQL clients in the same application?

Technically yes, but it's not recommended for production. Having two GraphQL client instances means two separate caches, two network layers, and potential data inconsistencies. If you need different client behaviors, urql's exchange architecture lets you customize per-operation behavior within a single client.

### How does Apollo Client's cache compare to urql's normalized cache?

Apollo's `InMemoryCache` is more mature with better default behavior — automatic entity normalization, garbage collection, and field-level policies. urql's `@urql/exchange-graphcache` provides similar normalized caching but requires more explicit configuration (you must define keys, resolvers, and updates). For most applications, the difference in practice is small, but Apollo edges ahead for complex data graphs with deeply nested, interconnected entities.

### Is graphql-request suitable for React applications?

graphql-request can work with React, but you'll need to write all the plumbing yourself — loading states, error boundaries, cache invalidation, and data refresh. For anything beyond a single query on a page, use Apollo Client or urql which provide React hooks (`useQuery`, `useMutation`) with built-in loading and error handling.

### What's the best way to handle authentication with these clients?

Apollo Client supports auth through Apollo Link middleware (`setContext`). urql uses the `@urql/exchange-auth` exchange. graphql-request passes headers in the constructor or per-request. All three support JWT Bearer tokens — the pattern is to intercept requests and attach the token, then handle 401 responses by refreshing the token or redirecting to login.

### Do these clients support GraphQL subscriptions over WebSockets?

Apollo Client supports subscriptions natively via WebSocket or SSE links (`GraphQLWsLink`, `SSELink`). urql handles subscriptions through the `subscriptionExchange`. graphql-request does not support subscriptions — it's designed for one-shot queries and mutations only.

### How do I migrate from Apollo Client to urql?

Start by mapping Apollo's hooks to urql equivalents: `useQuery` → `useQuery`, `useMutation` → `useMutation`. Replace `InMemoryCache` with urql's `cacheExchange` (document cache) or `@urql/exchange-graphcache` (normalized cache). Move Apollo Link logic to urql exchanges. The API surface is smaller, so most migrations are straightforward for typical query/mutation patterns. Cache-specific features (eviction, writeFragment) require the most rework.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript GraphQL Client Libraries Compared: Apollo Client vs urql vs graphql-request",
  "description": "Comprehensive comparison of JavaScript GraphQL client libraries: Apollo Client (19,806 stars), urql (8,965 stars), and graphql-request (6,113 stars). Covers caching strategies, bundle sizes, and React integration.",
  "datePublished": "2026-07-26",
  "dateModified": "2026-07-26",
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
