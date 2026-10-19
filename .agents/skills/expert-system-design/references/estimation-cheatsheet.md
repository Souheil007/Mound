# Back-of-the-Envelope Estimation Cheatsheet

Back-of-the-envelope estimation enables quick sanity-checking of system capacity, hardware sizing, and architectural viability before writing code.

---

## 1. Latency Numbers Every Engineer Should Know

| Operation | Latency | Relative Scale (Human Equivalent) |
| :--- | :--- | :--- |
| **L1 Cache Reference** | 0.5 ns | 1 heartbeat (1 sec) |
| **Branch Mispredict** | 5 ns | 10 seconds |
| **L2 Cache Reference** | 7 ns | 14 seconds |
| **Mutex Lock / Unlock** | 25 ns | 50 seconds |
| **Main Memory Reference (RAM)** | 100 ns | ~3 minutes |
| **Compress 1KB with Snappy** | 2,000 ns (2 µs) | 1 hour |
| **Send 2KB over 1 Gbps Network** | 20,000 ns (20 µs) | 10 hours |
| **Read 1MB Sequentially from Memory** | 250,000 ns (250 µs) | ~3 days |
| **SSD Random Read** | 150,000 ns (150 µs) | ~2 days |
| **Round Trip inside Same Datacenter** | 500,000 ns (500 µs) | ~6 days |
| **Read 1MB Sequentially from SSD** | 1,000,000 ns (1 ms) | ~12 days |
| **HDD Random Seek** | 10,000,000 ns (10 ms) | ~4 months |
| **Read 1MB Sequentially from HDD** | 20,000,000 ns (20 ms) | ~8 months |
| **Send Packet US to Europe (RTT)** | 150,000,000 ns (150 ms) | ~5 years |

### Core Architectural Rules of Thumb:
1. **Memory is ~1,000x faster than SSD and ~100,000x faster than HDD.**
2. **Avoid disk seeks at all costs.** Use sequential disk writes (append-only logs, WAL, SSTables) instead of random writes.
3. **Network transfers are expensive.** Always compress payloads (Gzip, Brotli, Zstandard, Snappy) before sending over WAN.
4. **Data center cross-region latency (~150ms)** dominates end-user perceived latency; use GeoDNS + CDNs + edge points of presence (PoP).

---

## 2. Power-of-Two Storage Scale

| Power of 2 | Exact Value | Standard Unit | Short Notation |
| :--- | :--- | :--- | :--- |
| **$2^{10}$** | 1,024 | 1 Kilobyte (KB) | 1 Thousand |
| **$2^{20}$** | 1,048,576 | 1 Megabyte (MB) | 1 Million |
| **$2^{30}$** | 1,073,741,824 | 1 Gigabyte (GB) | 1 Billion |
| **$2^{40}$** | 1,099,511,627,776 | 1 Terabyte (TB) | 1 Trillion |
| **$2^{50}$** | 1,125,899,906,842,624 | 1 Petabyte (PB) | 1 Quadrillion |

---

## 3. High Availability (SLA) "Nines"

Availability is measured as uptime percentage over a calendar year:

| Availability Level | Annual Downtime | Monthly Downtime | Daily Downtime | Typical SLA Scope |
| :--- | :--- | :--- | :--- | :--- |
| **99% (Two Nines)** | 3.65 days | 7.31 hours | 14.4 minutes | Internal prototypes, dev environments |
| **99.9% (Three Nines)** | 8.77 hours | 43.8 minutes | 1.44 minutes | Standard SaaS apps, non-critical web apps |
| **99.99% (Four Nines)** | 52.6 minutes | 4.38 minutes | 8.64 seconds | Critical consumer services, cloud APIs |
| **99.999% (Five Nines)** | 5.26 minutes | 26.3 seconds | 864 milliseconds | Core payment gateways, telecom, banking |

---

## 4. Capacity & Load Formulas

### Time Conversions:
- 1 day = 24 hours = 1,440 minutes = **86,400 seconds** $\approx \mathbf{10^5\text{ seconds}}$ (for rapid estimation).

### Queries Per Second (QPS):
$$\text{Average QPS} = \frac{\text{DAU} \times \text{Requests per User per Day}}{86,400}$$
$$\text{Peak QPS} = \text{Average QPS} \times 2 \quad (\text{or } 3\text{--}5 \text{ for spiky burst workloads})$$

### Read/Write Split:
- **Read-Heavy systems** (Twitter, YouTube, News Feed, Mound Blueprints): $\text{Read-to-Write ratio} = 10:1 \text{ or } 100:1$.
- **Write-Heavy systems** (Metrics logging, IoT sensors, Ad click tracking): $\text{Read-to-Write ratio} = 1:1 \text{ or } 1:10$.

### Storage Sizing:
$$\text{Daily Storage} = \text{Daily Writes} \times \text{Average Record Size}$$
$$\text{Storage for } 5 \text{ Years} = \text{Daily Storage} \times 365 \times 5 \times 1.2 \quad (\text{with } 20\% \text{ index/metadata overhead})$$

### Cache Sizing (80/20 Pareto Rule):
- In most internet services, **20% of items generate 80% of read traffic**.
- Rule: Cache the top 20% of daily read volume in RAM:
$$\text{Cache RAM Sizing} = \text{Daily Read Data Volume} \times 0.20$$

### Server Hardware Estimation:
- Modern web server (e.g., Go/FastAPI/Node with 8 vCPUs): handles **500 to 2,000 QPS** depending on query complexity.
- Modern relational DB (PostgreSQL): handles **5,000 to 10,000 read QPS**, **1,000 to 3,000 write QPS** on a single node before sharding/replicas.
- Modern in-memory cache (Redis): handles **50,000 to 100,000 QPS** per core.
