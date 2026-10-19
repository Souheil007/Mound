# The 4-Step System Design Framework

Based on *System Design Interview – An Insider's Guide* by Alex Xu.

System design is not about finding the single "perfect" answer; it is about navigating ambiguous requirements, exploring trade-offs, and justifying architectural choices collaboratively.

---

## Step 1: Understand the Problem and Establish Design Scope (3–10 min)

Never jump into architecture or component selection immediately. Premature design leads to solving the wrong problem.

### 1. Functional Requirements (What the system does)
- What are the core user flows and API actions? (e.g., "User creates post", "User reads feed", "System sends notification").
- What are the explicit non-goals (features out of scope for v1)?

### 2. Non-Functional Requirements (How well the system behaves)
- **Latency**: P95 / P99 latency SLA (e.g., < 50ms read, < 200ms write).
- **Throughput & Scale**: Daily Active Users (DAU), read/write requests per second (QPS).
- **Availability vs Consistency (CAP Theorem)**:
  - Is high availability (AP) prioritized (e.g., news feed, social chat)?
  - Is strong consistency (CP) required (e.g., financial ledger, inventory, reservations)?
- **Durability & Retention**: Can data ever be lost? What is the retention policy (e.g., 30 days, 5 years, infinite)?
- **Security & Compliance**: PII, GDPR, PCI-DSS, end-to-end encryption.

---

## Step 2: Propose High-Level Design and Get Buy-In (10–15 min)

Formulate the end-to-end architecture blueprint before diving into specifics.

### 1. Core Architecture Blueprint
- **Client Tier**: Web browser, mobile app, CLI, external agents/services.
- **Edge / Ingress**: DNS (GeoDNS), CDN (Cloudflare/CloudFront), API Gateway / Reverse Proxy (NGINX, Envoy, Traefik).
- **Application Tier**: Stateless microservices or modular monolith (FastAPI, Go, Node.js).
- **Caching Layer**: Redis, Memcached, CDN edge caches.
- **Storage Tier**: Relational DB (PostgreSQL, MySQL), NoSQL (DynamoDB, Cassandra), Object Storage (S3).
- **Asynchronous Tier**: Message queues (RabbitMQ, Kafka, SQS), task workers (Celery, temporal, background workers).

### 2. Core API Interface Definition
Draft the REST / gRPC contract for the primary use cases:
```http
POST /v1/resources
GET /v1/resources/{id}
```
Include key headers: `Authorization`, `X-Request-Id`, `Idempotency-Key`.

### 3. High-Level Data Schema
Outline the core entities and primary keys (e.g., `user_id`, `item_id`, `created_at`, `status`).

---

## Step 3: Design Deep Dive (10–25 min)

Zero in on the 2–3 hardest technical challenges and bottlenecks specific to the problem domain.

### Focus Areas by System Type:
- **High-Write Data Ingestion** (Ad click, metrics, IoT):
  - In-memory buffering, write-ahead logs (WAL), LSM-trees, stream aggregations (Flink), batching writes.
- **High-Read Fanout** (News feed, Twitter, notification):
  - Fanout-on-write (push) vs Fanout-on-read (pull) vs hybrid approach (celebrity handling).
- **Financial / Transactional** (Payments, reservations, wallets):
  - Distributed locks, double-entry ledger, idempotency keys, two-phase commit (2PC) or Saga orchestrator, reconciliation jobs.
- **Real-Time Interactive** (Chat, collaborative docs, gaming):
  - WebSockets vs SSE vs Long-Polling, heartbeat / presence servers, differential synchronization (OT / CRDT).
- **Search & Discovery** (Autocomplete, proximity, search engine):
  - Trie data structures, Geospatial indexing (GeoHash, QuadTree, Google S2), Inverted index / Vector search (pgvector, Elasticsearch).

---

## Step 4: Wrap-Up, Failure Modes & Scaling (3–5 min)

Recap the architecture, identify potential bottlenecks, and plan for 10x growth.

### 1. Failure Scenarios & Mitigations
- What happens if the primary database crashes? (Automated failover to read replica, promotion).
- What happens if the cache goes down? (Cache avalanche prevention, circuit breakers, stale-while-revalidate).
- How do we handle network partitions between data centers? (Quorum consensus, eventual synchronization).

### 2. Monitoring & Observability
- **Metrics**: Prometheus / OpenTelemetry (P99 latency, 4xx/5xx rates, CPU/RAM utilization, queue lag).
- **Logging**: Structured JSON logs aggregated via ELK or Grafana Loki.
- **Distributed Tracing**: Jaeger / Tempo for cross-service request tracking.

### 3. Scaling to 10x
- Horizontal database sharding via consistent hashing.
- Read/write segregation and read replicas.
- Multi-region deployment with GeoDNS.
