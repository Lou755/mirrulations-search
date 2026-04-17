# Search runtime: performance suggestions

Combined checklist for hybrid Postgres + OpenSearch search (tuning, architecture, and observability).

## Sequential vs parallel OpenSearch (and Postgres)

You can run the document, comment, and extracted-text OpenSearch queries **one after another**, **at the same time** (multiple HTTP requests from the app), or **batched** (e.g. `_msearch` so one request carries several searches). You can also overlap **Postgres** with **OpenSearch** (e.g. title SQL while OpenSearch runs). These choices change **wall-clock latency**, **load shape** on OpenSearch, and **complexity**—not always in the same direction.

### Sequential (one query, then the next)

- **Why use it:** Simplest code path; lowest **peak** concurrency against the cluster; easy to reason about errors and timeouts; avoids exhausting client connection pools or hitting per-node thread limits when the cluster is small or already busy.
- **Runtime effect:** Total time is roughly the **sum** of the three latencies (plus fixed overhead three times). It **does not improve** wall-clock versus parallel when the three queries are independent and the cluster has spare capacity—often **worse** for user-perceived latency.
- **When it is acceptable:** Heavy aggregations that already saturate CPU/IO on the data nodes (parallel might queue anyway); strict rate limits; debugging where you want isolated traces per index.

### Parallel (multiple concurrent requests from the app)

- **Why use it:** The three searches do not depend on each other’s results. While one waits on disk/network inside OpenSearch, the others can run. Wall-clock tends toward **roughly the slowest** query plus overhead, not the sum—**better** end-to-end latency when the bottleneck is waiting, not a single shared resource.
- **Runtime effect:** **Improves** perceived latency when OpenSearch has headroom (extra threads, CPU, queue depth). **May not improve** (or can **hurt**) if the cluster is near saturation: concurrent heavy aggs **contend** for the same nodes, increase GC pressure, and widen tail latency (p95/p99).
- **Operational caveat:** More simultaneous connections from each app worker; ensure client and server limits are sized for `workers × parallel fan-out`.

### Batched (`_msearch` or similar)

- **Why use it:** Cuts **HTTP round-trips** (TLS, framing, client/server per-request overhead). The cluster still executes multiple searches, but coordination is on the server side in one shot—often **better** than three separate sequential calls and sometimes comparable to three parallel calls with less connection churn.
- **Runtime effect:** **Improves** runtime mainly when **network/connection overhead** matters; less dramatic if queries are huge and CPU-bound on the data nodes (total work is unchanged). Watch **request size** and timeout behavior for one large batch vs three smaller failures.

### “Both” (e.g. Postgres parallel with OpenSearch, while OpenSearch queries are sequential internally)

- **Why use it:** Dimensions are independent: overlapping **Postgres title search** with the **whole OpenSearch phase** hides SQL latency behind OpenSearch (or vice versa) when neither needs the other’s output first.
- **Runtime effect:** **Improves** wall-clock versus doing SQL then OpenSearch strictly in series. It **does not** remove the need to parallelize or batch **within** the OpenSearch phase if those three calls are still sequential— you get one overlap, not two.

### Summary

| Approach | Usually helps wall-clock when… | Often neutral or worse when… |
|----------|-------------------------------|------------------------------|
| Sequential | Cluster is saturated; you need minimal concurrency | Cluster has spare capacity and queries are I/O-bound |
| Parallel | Independent queries, cluster has headroom | Single-node or saturated cluster; connection limits tight |
| `_msearch` / batch | Round-trip and connection overhead is significant | Bodies are huge; one slow sub-search blocks the whole batch response |
| PG ∥ OS phase | SQL and OpenSearch are independent | (Rare) one path always dominates so overlap saves little |

Measure with **per-phase timings** (item 17): if the sum of three OpenSearch durations dominates, parallel or batch is a lever; if one query dominates and the others are tiny, gains are smaller.

---

1. Run the three OpenSearch searches in parallel or as one `_msearch` batch so network wait overlaps.
2. Narrow candidates in OpenSearch first when facets (agency, docket type, dates, CFR if indexed) are accurate vs Postgres.
3. Keep OpenSearch `terms`/bucket sizes intentional—not “as large as possible.”
4. Make unique-comment matching cheaper when hot: tune `terms`, allow approximate counts, or precompute at index time.
5. Tune OpenSearch cluster/index settings (shards, `refresh_interval`, capacity/JVM) when latency is dominated by the cluster.
6. Fewer Postgres round trips: one filtered query that returns the full joined row shape instead of ID pass then full fetch.
7. Index filter/join columns (`docket_id`, dates, agency, etc.) and prefer index-friendly predicates (avoid leading-`%` `ILIKE`; use exact keys or `pg_trgm` where needed).
8. Use materialized views or summary tables for per-docket totals maintained on ingest.
9. Use a read replica for search-heavy traffic to isolate load from writes.
10. Tune merge and ranking (boosts, title vs full-text, stable scoring) to fetch less long tail.
11. True pagination / bounded work: cursors, `search_after`, or fetch-enough-for-page instead of unbounded merge-enrich.
12. Optional long term: one primary search system (Postgres FTS or denormalized OpenSearch only).
13. Treat totals as first-class cost: overlap Postgres doc totals with OpenSearch comment totals; chunk IDs; totals for page/top slice only; or cache/store totals.
14. Short-lived cache on query + filters + sort with TTL and staleness rules.
15. Skip or lighten work for empty/placeholder queries; optional “fast mode” with documented tradeoffs.
16. Reuse one OpenSearch client per process (non-AOSS) if connection setup shows in profiles.
17. Log structured timings per phase to optimize the real p95 bottleneck.
