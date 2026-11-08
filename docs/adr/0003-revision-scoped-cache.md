# ADR 0003: revision-scoped Redis semantic cache

- **Status:** Accepted; threshold measured on eight fixed pairs
- **Date:** 2026-11-05

## Context

Repeated or semantically similar questions can avoid repeated generation, but stale answers after re-indexing and caching abstentions/follow-ups can mislead users. The assignment also requires cache invalidation and threshold tuning.

## Decision

Store only validated grounded answers together with their evidence passages and question embedding. Scope keys by embedding model, active collection revision and a grounding/generation policy fingerprint (relevance floor, top-k, provider/model, temperature, schema and cache-format version), use a seven-day TTL, and compare vectors by cosine similarity at a configurable threshold (currently 0.96). Bypass cache for abstentions, follow-up questions, and stub retrieval. Index publication changes the active revision immediately. Only the API connects to Redis and prunes obsolete revisions during lookup; the indexer does not flush Redis. Redis is dedicated to this service in the current deployment.

## Consequences

Revision scoping makes stale entries unreachable after active-index change even if deletion fails. Grounded response/evidence pairs preserve citations on a hit. A Redis key scan and in-process cosine comparisons are simple for a small corpus but do not scale to high volume; a vector index or bounded candidate index would be needed. An interrupted prune can leave unreachable entries consuming memory until TTL. Policy fingerprints prevent a cached answer accepted under a lower floor or another generator from bypassing the current policy. The measured eight-pair study in docs/evidence/cache-sweep.json found two false hits at 0.90 and one at 0.94. Retain 0.96: it had zero false hits, but missed all four paraphrases. This is a safety tradeoff on a small sample; it does not demonstrate broad semantic-cache effectiveness. See docs/PIPELINE.md for the complete threshold table.

## Alternatives considered

- Cache by exact question only: misses paraphrases but has simple semantics.
- Redis vector search: more scalable, but adds index configuration and module dependency.
- Flush-only invalidation: rejected because it is not atomic with publication and violates the API-only Redis boundary if performed by the indexer.
- Cache all responses: rejected because follow-ups and abstentions are especially context-sensitive.

