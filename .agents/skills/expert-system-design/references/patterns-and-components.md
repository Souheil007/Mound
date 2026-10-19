# Architectural Patterns & Core Components Reference

Comprehensive architectural patterns synthesized from *System Design Interview (Vol 1 & 2)*.

---

## 1. Caching Strategies & Topologies

### Cache Access Patterns:
1. **Cache-Aside (Lazy Loading)**:
   - Application queries cache first. On miss, queries DB, populates cache, and returns.
   - *Best for*: Read-heavy workloads with unpredictable access patterns.
   - *Trade-off*: Initial cache miss latency; cache can become stale if writes bypass it.
2. **Read-Through**:
   - Cache library/service sits between app and DB. App always queries cache; cache fetches from DB on miss transparently.
3. **Write-Through**:
   - App writes to cache; cache writes synchronously to DB before returning.
   - *Best for*: Strict read-your-own-writes consistency.
   - *Trade-off*: Higher write latency.
4. **Write-Behind (Write-Back)**:
   - App writes to cache immediately; cache asynchronously flushes batch writes to DB in background.
   - *Best for*: High-throughput write systems (e.g., counters, analytics).
   - *Trade-off*: Risk of data loss if cache server crashes before flushing to DB.

### Cache Failure Modes & Mitigations:
- **Cache Avalanche**: Many keys expire at the same instant or cache crashes, flooding DB with traffic.
  - *Fix*: Add random jitter to TTLs (`TTL = base_ttl + rand(0, 300)`), deploy multi-AZ cache clusters.
- **Cache Penetration**: Queries for non-existent keys bypass cache repeatedly and hammer DB.
  - *Fix*: Cache null values with short TTL, or use a **Bloom Filter** at the ingress gate.
- **Cache Stampede / Thundering Herd**: A popular key expires, and thousands of concurrent requests query the DB simultaneously.
  - *Fix*: Mutex / distributed lock on cache miss, or proactive asynchronous background refresh before expiration.

---

## 2. Distributed Rate Limiting

Rate limiting protects APIs from denial-of-service, abusive scraping, and runaway loops.

### Algorithms Comparison:

| Algorithm | Mechanism | Pros | Cons | Best Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Token Bucket** | Tokens added at fixed rate up to capacity; request consumes 1 token. | Handles bursts smoothly; memory efficient. | Tuning bucket size and refill rate. | General-purpose API gateways (Amazon, Stripe). |
| **Leaking Bucket** | FIFO queue processed at constant outflow rate; drops if full. | Smooth, predictable traffic flow; no bursts. | Bursty legitimate requests may be queued/delayed. | E-commerce checkout, payment processing. |
| **Fixed Window** | Counter increments per time slot (e.g., 1 min). | Extremely simple to implement. | Burst at boundary edges can allow $2\times$ the limit. | Low-stakes internal rate limits. |
| **Sliding Window Log** | Stores exact request timestamps in sorted set; purges old entries. | 100% mathematically precise limit. | High memory footprint storing every timestamp. | Low-volume, mission-critical operations. |
| **Sliding Window Counter** | Blends previous window count with current window percentage. | Memory efficient; prevents edge burst spikes. | Minor approximation margin (<0.05%). | High-throughput distributed platforms. |

### Distributed Implementation:
- In distributed microservices, use **Redis with Lua scripts** to ensure atomic check-and-decrement in a single round-trip, preventing multi-instance race conditions.

---

## 3. Consistent Hashing

Standard modular hashing (`hash(key) % N`) causes massive cache invalidation whenever server count $N$ changes.

### Mechanics:
1. Map both server identifiers and data keys onto a circular 160-bit hash ring ($0$ to $2^{160}-1$).
2. Key lookup: Walk clockwise from the key's hash position until reaching the first server node.
3. Adding/removing a server only reassigns keys in the immediate predecessor segment ($\sim 1/N$ fraction of keys).

### Virtual Nodes (Heterogeneity & Balance):
- Single physical servers are mapped to $k$ virtual nodes (e.g., 100–300 virtual nodes per physical machine).
- Eliminates uneven partition sizes and Hotspot/Celebrity skew.
- Permits weighting: more powerful physical servers receive proportionally more virtual nodes.

---

## 4. Distributed Unique ID Generators

Relational `auto_increment` primary keys fail in distributed systems due to cross-datacenter synchronization latency.

### Twitter Snowflake (64-bit Numerical ID):
- **1 bit**: Reserved / Sign bit (always `0`).
- **41 bits**: Timestamp in milliseconds since custom epoch (gives 69 years of sortable IDs).
- **5 bits**: Datacenter ID ($2^5 = 32$ datacenters).
- **5 bits**: Machine ID ($2^5 = 32$ machines per datacenter).
- **12 bits**: Sequence number per millisecond ($2^{12} = 4,096$ IDs per machine/ms).
- *Throughput*: $\sim 4.09$ million unique, time-sortable 64-bit IDs per second per datacenter cluster without database coordination.
- *Requirement*: Use NTP (Network Time Protocol) to prevent clock drift.

---

## 5. Distributed Messaging: Kafka vs. RabbitMQ

| Dimension | Distributed Log (Apache Kafka, Redpanda) | Traditional Broker (RabbitMQ, SQS) |
| :--- | :--- | :--- |
| **Data Model** | Append-only partitioned commit log on disk. | Queues with transient messages popped on read. |
| **Consumption Model** | **Pull-based**: Consumer tracks its own offset. | **Push-based**: Broker pushes message to consumer. |
| **Replayability** | High (retention for days/weeks/infinite; replay anytime). | Low (message deleted immediately upon ACK). |
| **Message Ordering** | Strictly guaranteed **within a single partition**. | Guaranteed per queue, but disrupted by retries/concurrency. |
| **Throughput** | Ultra-high (>1,000,000 msg/sec via zero-copy OS sendfile). | Moderate (10,000 to 50,000 msg/sec). |
| **Best Used For** | Event sourcing, metrics pipelines, stream analytics, spec feeds. | Task worker orchestration, asynchronous background jobs. |

---

## 6. Concurrency, Locking & Idempotency

### Concurrency Strategies:
1. **Pessimistic Locking** (`SELECT ... FOR UPDATE`):
   - Locks record until transaction commits.
   - *Best for*: High-contention, low-latency transactions (e.g., financial balance decrement).
   - *Downside*: Risk of deadlocks; degrades throughput under load.
2. **Optimistic Locking** (`version` column):
   - `UPDATE table SET val = :val, version = version + 1 WHERE id = :id AND version = :old_version`.
   - *Best for*: Low-to-moderate contention workloads.
   - *Downside*: Fails under extreme concurrent write storms, requiring retry loops.
3. **Distributed Locks (Redis Redlock / ZooKeeper)**:
   - Acquired with TTL; must use fencing tokens to prevent zombie lock execution during GC pauses.

### Idempotency Keys:
- Client generates unique `idempotency_key` (UUIDv4) and passes in request headers.
- Server uses an atomic check-and-insert in Redis/PostgreSQL:
  - If key exists with status `SUCCESS`: Return cached response immediately without re-executing.
  - If key exists with status `IN_PROGRESS`: Return 409 Conflict or wait.
  - If key does not exist: Insert key and execute transaction.
