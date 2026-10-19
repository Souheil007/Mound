# System Design Interactive Interview Guide

When running a system design analysis on a new codebase or project, use this questionnaire to clarify scope and constraints with the user (via `ask_question` or direct interactive prompts).

---

## 1. Scale & Traffic Assumptions
1. **Target User Base**:
   - What is the expected initial and 1-year scale? (e.g., internal team of 50 vs. 100k DAU vs. 10M DAU)
2. **Read vs. Write Profile**:
   - Is the workload read-heavy (e.g., social feed, content browsing), write-heavy (e.g., metrics, telemetry, logging), or balanced (e.g., financial trading)?
   - What is the estimated request rate (QPS)?

---

## 2. Latency & SLA Expectations
1. **Response Time Budget**:
   - What is the acceptable P95 / P99 latency SLA for core endpoints? (< 50ms, < 200ms, or asynchronous background)?
2. **High Availability Target**:
   - What is the required uptime target? (99.9% = ~8.8h downtime/year vs. 99.99% = ~52min downtime/year)
3. **Data Freshness / Consistency**:
   - Do clients require immediate strong consistency (read-your-own-writes across all nodes), or is eventual consistency (e.g., within a few hundred milliseconds) acceptable?

---

## 3. Storage & Data Lifecycle
1. **Data Volumetrics**:
   - What is the average payload size per transaction or record?
   - How long must historical records be retained? (30-day rolling window, 1 year, 7 years for compliance, or indefinitely)?
2. **Query Access Patterns**:
   - What are the primary query keys? (Lookup by ID, time-range queries, full-text search, geospatial distance, or vector similarity)?

---

## 4. Operational & Deployment Constraints
1. **Infrastructure & Hosting**:
   - Where will this run? (Single VPS / Docker Compose, Kubernetes cluster, Serverless / Edge, or Managed Cloud like AWS/GCP/Azure)?
2. **Existing Stack Preferences**:
   - Are there mandatory technologies already chosen by the team (e.g., Python FastAPI, Next.js, PostgreSQL, Redis)?
   - Are there budget limits or external API dependencies to account for?
