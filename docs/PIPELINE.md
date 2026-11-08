# Indexing and retrieval pipeline

The indexer is a one-shot Kubernetes Job, separate from API startup. Its stages are `extract → clean → chunk → embed → publish`; implementations live in `indexer/pipeline/`. The default run reads `corpus/raw/`, embeds with the configured Ollama model, writes a versioned Chroma collection, then switches the registry's active collection. The API checks the expected embedding model before serving ready traffic.

## Extraction and cleaning

PDF pages are extracted with pdfplumber. When normalized text has fewer than 25 characters, the page is rasterized with Poppler and OCR'd with Tesseract. PDF tables are serialized as pipe-delimited rows; HTML tables use the same row representation. Markdown front matter is skipped. Unsupported file extensions fail explicitly.

Cleaning normalizes whitespace and drops repeated page-edge lines when they recur across pages. It retains section labels, page boundaries, numbers, punctuation, table row boundaries and clause identifiers because they support exact-term answers and citation locations. OCR text is tagged in the page model. The executed extraction inventory is in `evidence/extraction.json`: 41 OCR pages across four PDFs, including all eight entrepreneurship-policy pages. Visual review of representative pages found detached clause numbers with default OCR; `--psm 6` kept the reviewed number/text pairs together. It also found off-page hidden PDF text, now removed by cropping to page bounds. Minor OCR artifacts and complex merged PDF cells remain; the audit is representative rather than exhaustive.

Actual fee-table before/after (`evidence/table-before-after.json`): naive flattened
HTML produces `Program Fee BBA / BS Rs. 12,000 MBA / MS Rs. 12,000`; the table parser
produces separate rows `Program | Fee`, `BBA / BS | Rs. 12,000`, and
`MBA / MS | Rs. 12,000`. Row/cell delimiters preserve which amount belongs to which
program. HTML extraction now excludes head, script, style, navigation, header and footer blocks; policy text and tables remain. Numeric clauses are deliberately retained, including short
threshold-bearing lines that an aggressive short-line cleanup would destroy.

## Chunking

`indexer/pipeline/chunk.py` uses whitespace-delimited words as a practical token approximation (not a model tokenizer). It detects numbered/Markdown headings, groups paragraphs, prefers sentence boundaries, caps long sentences with sliding windows, and carries overlap across adjacent chunks. Every chunk records source, section, page, document version and superseded status. The configuration is currently 400 words with 50 words of overlap; these are the shipped parameters selected from the measured comparison below.

| Approx. size (words) | Overlap | Recall@3 | Recall@5 | Chunks | Stored/source word ratio |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | 30 | 70.59% | 82.35% | 1,322 | 1.0493 |
| **400** | **50** | **70.59%** | **88.24%** | **1,239** | **1.0326** |
| 600 | 75 | 70.59% | 88.24% | 1,198 | 1.0113 |

Measured on the unchanged 19-question golden set with local nomic embeddings, 768
vector dimensions, exact cosine ranking and current-version metadata filtering.
Raw data: `evidence/chunk-sweep.json`; runner: `scripts/measure_pipeline.py`.
This is retrieval-only, separate from API generation evaluation. Identical texts reuse
vectors from the successful published index or the model-digest/text-hash measurement
cache; only changed texts are re-embedded. No fixture scores enter this table.

Ship 400/50: it improves recall over 250/30, ties 600/75, and bounds individual evidence
windows more tightly for the CPU-only generator. The 600/75 alternative saves 41
chunks and about two percentage points of word amplification, but brings no measured
recall improvement. All three preserve page/section boundaries, so many policy clauses
are already shorter than either target. Amplification uses whitespace words as the
documented token approximation, not an exact model-token or disk-byte ratio. At the
shipped setting, ordinary recall@5 is 100%, exact 83.33%, version 50%, injection 100%.
Version selection remains the weakest measured category; current filtering prevents
obsolete candidates but does not itself rank the correct current clause first.

## Embedding and version pin

`EMBED_MODEL` defaults to `nomic-embed-text`; the indexer and API both use the Ollama `/api/embed` endpoint. The configured model name is stored in Chroma collection metadata and exposed through the active registry. The API readiness route compares that metadata with its configured model and reports not-ready on a mismatch. Live local Docker embeddings have 768 dimensions; model IDs/digests are recorded in `evidence/local-models.json`.

Read-only query expansion follows numbered policy references within the same source/version. Linked children use BM25 and phrase ranking; their actual provenance is retained. Explicit unique page aliases restrict retrieval to the requested source. `match_kind` identifies dense, section_reference or source_reference matches; `dense_score` preserves raw cosine independently of inherited or exact-source relevance.

Current-document retrieval applies `superseded=false`. A narrow historical-language heuristic permits old policy chunks when a question explicitly refers to prior versions. This reduces accidental mixing but should be tested with a live index and explicit version questions. Re-indexing publishes a new versioned collection before switching the registry pointer. Cache keys include the active index revision, so publication immediately invalidates previous entries logically; the API prunes obsolete revisions. The indexer never connects to Redis, consistent with the API-only Redis NetworkPolicy.

## Semantic cache

Redis entries store the query embedding, validated answer and cited passages, scoped by embedding model and index revision, with a seven-day TTL. The configured similarity cutoff currently defaults to 0.96. Abstentions, follow-up questions and non-Chroma/stub requests bypass cache use; only grounded answers are stored. Cache lookup scans the revision's keys and computes cosine similarity in the API, so this is suitable for a small assignment corpus, not a high-volume cache.

The local Docker Ollama service was used to embed the eight fixed pairs in
`eval/cache-pairs.yaml` (four paraphrases, four unsafe near neighbors). Measured results
are in `docs/evidence/cache-sweep.json`, generated by `scripts/measure_cache.py`.

| Threshold | True hits | False hits | Paraphrase misses |
| ---: | ---: | ---: | ---: |
| 0.85 | 3 | 3 | 1 |
| 0.90 | 3 | 2 | 1 |
| 0.94 | 1 | 1 | 3 |
| 0.96 | 0 | 0 | 4 |
| 0.98 | 0 | 0 | 4 |

The 2026-versus-2023 rules pair scored 0.9547, producing an unsafe cross-version
hit at 0.94. The A+-versus-B+ pair scored 0.9284 and would collide at 0.90.
Retain 0.96 as the least conservative tested threshold without false hits in this
small sample. It sacrifices all four tested paraphrase hits, so this is a safety
choice, not evidence of an effective general-purpose semantic cache. Exact repeats
can still hit. Redis latency, operational invalidation, and follow-up bypass require
separate live checks; this experiment measures the cosine decision only.

## Evaluation method

`eval/run_eval.py` compares each golden `(source, section)` pair with retrieved passages, accepting an exact normalized section or a retrieved subsection whose label begins with the expected label. It reports macro recall@3 and recall@5 for answerable questions, plus recall@5 by question type, citation validity (citation tuple must occur in retrieved passages), and must-abstain correctness. The gate permits at most a five percentage-point recall@5 regression from baseline, requires 95% citation validity, and requires every must-abstain question to be declined.

The real corpus is published on local Minikube and representative OCR review is complete. Final live generation results and per-answer review are recorded separately; the retrieval-only results above do not stand in for generation correctness. The fixture set can exercise the API and gate shape offline, but it is not a substitute for a measured real-corpus baseline. Never label a placeholder or fixture result as the production baseline.


## Grounded generation in the local release

The measured release uses **Qwen 2.5 3B**, temperature **0.0**, an evidence floor of
**0.70**, top-k **5**, and nomic-embed-text (768 dimensions). API and indexer share
the embedding ConfigMap pin; full model digests are recorded in local-models.json.
All three published source-SHA image tags/digests are in final-images.json. The
index remains 1,239 chunks: 1,232 PDF chunks plus seven cleaned HTML chunks.

The provider is intentionally extractive on this CPU budget. After version/source
filtering, clause focus and the relevance window, it builds up to four verbatim
quote choices per eligible passage. Currency abbreviations retain their amounts;
obvious instruction-like sentences cannot be policy choices. A schema-constrained
numeric model call selects a directly answering excerpt or zero for refusal.
Final generation uses the shared Pydantic Answer schema constrained to that selected
quote/citation pair, or the refusal branch. Independent checks reject altered quotes,
wrong citations and out-of-range choices; the query service retries once then safely
falls back. Internal reasoning is an evidence-status summary and is stripped from the
public response. This is two bounded model calls, not free-form policy paraphrasing.

The stronger selection step followed observed wrong-source/negation mistakes in
smaller-model and long-alternative decoder probes. It trades latency and terse
extractive prose for attributable facts. It does not establish universal semantic
correctness: an exact quote can still be irrelevant or incomplete. The per-question
generation review therefore assesses correctness, coverage and citation relevance
separately from the automated membership percentage. Safe false abstentions and
partial answers are disclosed rather than relabelled as successes.

Cache policy version 6 prevents reuse of answers generated before this selection
change; the policy hash also includes the relevance floor, model and temperature.
The active Chroma revision continues to invalidate cache entries after publication.
HTML refresh was a sole writer Job: it verified unchanged embedding metadata,
retained PDF vectors, embedded only changed HTML, then atomically replaced the
active generation. The full PDF OCR run and the later 22-second HTML refresh are
separate observations, not two full-corpus indexing runs.

## Final measured live result

The reviewed 19-question API run reports recall@3 **100%**, recall@5 **100%**,
with recall@5 **100%** for ordinary, exact, version and injection types. Citation
membership is **16/16 (100%)**; both required refusals are correct (**2/2**).
Literal expected terms match **16/17 (94.12%)**. The missing term is the answerable
injected attendance question, which safely refuses below the 0.70 floor. This is
reported as a false abstention, not a perfect generation score. All other grounded
answers were reviewed for relevance and checked verbatim against the cited indexed
text; see `evidence/generation-review.md` and `evidence/final-responses.json`.

The observed run took 1,032.11 seconds in total, median 39.03 seconds and maximum
216.31 seconds per request. It includes an already-cached first answer; these are
observed mixed-run latencies, not a cold-start benchmark. Subsequent baseline/gate
runs use safe cached answers and must not be used to claim faster cold generation.
The initial real baseline was frozen only after review. CI also recomputes metrics
from the committed raw responses and compares them to results and the real baseline.
The fixture gate still separately runs against a live freshly indexed CI stack.
