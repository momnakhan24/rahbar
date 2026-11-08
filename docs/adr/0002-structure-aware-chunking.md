# ADR 0002: structure-aware chunking

- **Status:** Accepted; parameter choice provisional pending measured evaluation
- **Date:** 2026-11-05

## Context

The source set contains numbered policy clauses, page-level citations, tables and long-form reports. Fixed character slicing can separate a rule from its clause heading or create citations that are hard to verify. Model tokenizers also differ, so a tokenizer-based limit would add a model-specific dependency.

## Decision

Chunk by document structure first: preserve page boundaries and numbered/Markdown headings, group paragraphs and sentences, and use overlapping word windows only for oversized passages. Use 400 whitespace-delimited words with 50 words overlap as the current default. Preserve source, section, page, version and superseded metadata on every chunk. Treat whitespace word count as an approximation, not a true model-token limit.

## Consequences

Clause labels and citation locations remain available to retrieval and evaluation, and extraction/chunking can be tested without an embedding service. Overlap duplicates content and can increase storage; the actual amplification has not yet been measured. The 400/50 setting is not claimed optimal. Compare 250/30, 400/50 and 600/75 on the same reviewed golden set and select using recall@5, citation quality and storage cost.

## Alternatives considered

- Fixed character windows: simpler, but can cut clause boundaries and has no consistent token meaning.
- Model tokenizer chunks: more accurate limits, but couples ingestion to a particular tokenizer and is not required for this prototype.
- No overlap: less storage, but risks losing context around chunk boundaries.
