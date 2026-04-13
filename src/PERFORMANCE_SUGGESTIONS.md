# Search runtime: performance suggestions

Combined checklist for hybrid Postgres + OpenSearch search (tuning, architecture, and observability).

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
