# System Design Trade-Offs Catalog ("Why Choose X Over Y")

Architectural excellence lies in choosing the right set of trade-offs for a given set of constraints. This catalog provides structured decision trees and comparison matrices.

---

## 1. Storage: Relational (SQL) vs. Non-Relational (NoSQL)

| Dimension | Relational (PostgreSQL, MySQL) | Document (MongoDB) | Key-Value (Redis, DynamoDB) | Wide-Column (Cassandra, ScyllaDB) |
| :--- | :--- | :--- | :--- | :--- |
| **Schema** | Strict, typed, normalized tables. | Flexible JSON/BSON documents. | Opaque key-to-value blobs. | Column-families, partitioned. |
| **Transactions** | Full ACID, multi-table transactions. | Multi-document ACID (slower). | Single-key atomic operations. | Single-partition transactions. |
| **Querying** | Rich SQL, complex `JOIN`s, aggregations. | Document queries, nested index. | Primary key lookup only. | CQL, query by partition + cluster key. |
| **Scaling** | Vertical scale, Read replicas, manual sharding. | Horizontal sharding built-in. | Automatic partitioning. | Masterless peer-to-peer linear scaling. |
| **Best Used When** | Structured business entities, relational links, financial records, strict consistency required. | Rapid prototyping, hierarchical/variable schema (e.g., CMS, user profile). | Low-latency caching, session state, rate limiters, leaderboards. | High-write throughput (>100k writes/s), time-series, append-only logs. |

### Decision Rule:
- **Default to PostgreSQL** for almost all modern web and SaaS architectures unless write volume exceeds 10,000 writes/sec or data volume exceeds several Terabytes per month. PostgreSQL with extensions (e.g., `pgvector`, JSONB, PostGIS) satisfies relational, document, vector, and geospatial workloads in a single operational footprint.

---

## 2. API Communication: REST vs. gRPC vs. GraphQL vs. SSE vs. WebSockets

| Protocol | Transport | Latency / Overhead | Data Format | Streaming Support | Best Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REST** | HTTP/1.1 or HTTP/2 | Moderate (JSON serialization + HTTP headers) | JSON / Form | No (Request-Response) | Public developer APIs, CRUD interfaces, standard web clients. |
| **gRPC** | HTTP/2 (Multiplexed) | Ultra-low (binary Protocol Buffers) | Protobuf | Unidirectional & Bidirectional | Internal inter-microservice communication, high-throughput RPCs. |
| **GraphQL** | HTTP/POST | Moderate (query parsing overhead) | JSON | Subscriptions (via WS) | Complex frontend apps requiring selective field fetching from multiple resources. |
| **Server-Sent Events (SSE)** | HTTP/1.1 or HTTP/2 | Low (persistent unidirectional HTTP stream) | Text / Event-stream | Unidirectional (Server $\to$ Client) | LLM token streaming, notification feeds, Model Context Protocol (MCP) bridges. |
| **WebSockets** | TCP (Upgraded from HTTP) | Minimal framing (2 bytes overhead per message) | Binary / Text | Full Bidirectional | Multiplayer gaming, real-time collaborative editing, instant messaging. |

### Decision Rule:
- For LLM outputs and agent tooling: **Prefer SSE over WebSockets** because SSE runs over standard HTTP, works seamlessly through enterprise firewalls/proxies without custom port forwarding, and natively supports automatic HTTP reconnection.

---

## 3. Feed & Ingestion Fanout: Push vs. Pull vs. Hybrid

### Scenario: Social feeds, activity streams, or notification fanout.

| Strategy | Mechanism | Pros | Cons | When to Choose |
| :--- | :--- | :--- | :--- | :--- |
| **Fanout-on-Write (Push)** | When a user posts, immediately insert post ID into every follower's feed cache. | Read feed is instantaneous ($O(1)$ cache read). | Writing to 10M followers (celebrity) causes write amplification and severe delay. | Systems where users follow small to moderate numbers of people (<5,000 followers). |
| **Fanout-on-Read (Pull)** | When user opens feed, pull recent posts from all followed users and merge sort in real-time. | Fast write ($O(1)$ write); no write amplification. | Reading feed is slow ($O(N)$ merge on read); heavy DB query per feed load. | Systems with infrequent read traffic or uniform high-follower accounts. |
| **Hybrid Fanout** | Push to regular users; Pull from "celebrity" accounts (>20k followers) at read time and merge in memory. | Combines $O(1)$ reads for 99% of users with zero write bottlenecks for high-profile accounts. | Slightly higher code complexity in the feed aggregator service. | **Industry Standard** (Twitter / X, Instagram, LinkedIn). |

---

## 4. Distributed Transactions: Two-Phase Commit (2PC) vs. Saga Pattern

| Pattern | Mechanism | Consistency Guarantee | Availability & Latency | Best Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Two-Phase Commit (2PC)** | Coordinator sends `Prepare` to all nodes, then sends `Commit` if all agree. | Strong ACID consistency. | Low availability; nodes lock resources during prepare phase. If coordinator fails, locks stay open. | Monolithic database clusters, banking core engines. |
| **Saga Pattern (Choreography / Orchestration)** | Series of local transactions. If a step fails, executing compensating transactions in reverse. | Eventual consistency (compensating rollbacks). | High availability; non-blocking; services remain decoupled. | Distributed microservices, e-commerce checkout, multi-stage workflows. |

---

## 5. Search & Retrieval: BM25 vs. Dense Vector vs. Hybrid RRF

| Approach | Technology | Strengths | Weaknesses |
| :--- | :--- | :--- | :--- |
| **BM25 / Keyword Search** | PostgreSQL `tsvector`, Elasticsearch | Precise keyword matches, acronyms, exact IDs, error codes. | Fails on synonyms, conceptual queries, or paraphrasing. |
| **Dense Vector Embeddings** | `pgvector`, Qdrant, Pinecone | Captures semantic meaning, synonyms, conceptual similarity. | Struggles with exact model numbers, technical names, and rare jargon. |
| **Hybrid Reciprocal Rank Fusion (RRF)** | BM25 + Vector combined via $RRF(d) = \sum \frac{1}{k + r_i(d)}$ | Best of both worlds: high semantic recall + exact keyword precision. | Requires running two queries and fusing rank scores. |

### Decision Rule:
- Use **Hybrid RRF** whenever users or agents query technical domain specifications, bug reports, or legal/medical documentation.
