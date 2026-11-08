# ADR 0001: Keep indexing in a one-shot Job

- **Status:** Accepted
- **Date:** 2026-11-05

## Context

The API has multiple replicas sharing one Chroma collection. If each API process indexes
on startup, simultaneous rollout or restart causes competing writers, duplicate work, and
query pods that become available at different times. Indexing can also require much more
memory than query serving.

## Decision

Only the `indexer` Job and its weekly CronJob write the collection. The API Deployment is
read-only with respect to Chroma. Chroma is a single-replica StatefulSet with a persistent
volume claim template. The initial job runs the starter `--dummy` mode to validate the
cluster before enabling the real pipeline.

## Consequences

- API replicas can scale independently without running extraction, embedding, or writes.
- The collection survives Chroma pod replacement.
- Re-indexing has an explicit lifecycle and can invalidate cache entries in one place.
- The real store builds a uniquely named collection and publishes it through a small
  registry collection only after all chunks have been written. API reads resolve that
  active generation, so a failed build leaves the previously published collection in
  service.
- Only the API connects to Redis, and the NetworkPolicy blocks the indexer from reaching it, so the indexer never flushes the cache. Cache keys include the index revision, so when a new index is published, old cache entries can no longer be found. The API removes them when it looks up the cache (see ADR 0003).
- Old physical index generations are retained for rollback/debugging. A later maintenance
  task should prune them only after the new generation has been observed healthy.
