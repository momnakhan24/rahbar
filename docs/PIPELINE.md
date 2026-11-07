# Indexing and retrieval pipeline

The indexer is a one-shot Kubernetes Job, separate from API startup. Its stages are `extract → clean → chunk → embed → publish`; implementations live in `indexer/pipeline/`. The default run reads `corpus/raw/`, embeds with the configured Ollama model, writes a versioned Chroma collection, then switches the registry's active collection. The API checks the expected embedding model before serving ready traffic.

## Extraction and cleaning

PDF pages are extracted with pdfplumber. When normalized text has fewer than 25 characters, the page is rasterized with Poppler and OCR'd with Tesseract. PDF tables are serialized as pipe-delimited rows; HTML tables use the same row representation. Markdown front matter is skipped. Unsupported file extensions fail explicitly.

Cleaning normalizes whitespace and drops repeated page-edge lines when they recur across pages. It retains section labels, page boundaries, numbers, punctuation, table row boundaries and clause identifiers because they support exact-term answers and citation locations. OCR text is tagged in the page model. The executed extraction inventory is in `evidence/extraction.json`: 41 OCR pages across four PDFs, including all eight entrepreneurship-policy pages. Visual review of representative pages found detached clause numbers with default OCR; `--psm 6` kept the reviewed number/text pairs together. It also found off-page hidden PDF text, now removed by cropping to page bounds. Minor OCR artifacts and complex merged PDF cells remain; the audit is representative rather than exhaustive.

Actual fee-table before/after (`evidence/table-before-after.json`): naive flattened
HTML produces `Program Fee BBA / BS Rs. 12,000 MBA / MS Rs. 12,000`; the table parser
produces separate rows `Program | Fee`, `BBA / BS | Rs. 12,000`, and
`MBA / MS | Rs. 12,000`. Row/cell delimiters preserve which amount belongs to which
program. Script/navigation text remains elsewhere in the extracted HTML, a known
cleaning limitation. Numeric clauses are deliberately retained, including short
threshold-bearing lines that an aggressive short-line cleanup would destroy.

## Chunking

`indexer/pipeline/chunk.py` uses whitespace-delimited words as a practical token approximation (not a model tokenizer). It detects numbered/Markdown headings, groups paragraphs, prefers sentence boundaries, caps long sentences with sliding windows, and carries overlap across adjacent chunks. Every chunk records source, section, page, document version and superseded status. The configuration is currently 400 words with 50 words of overlap; these are the shipped parameters selected from the measured comparison below.

| Approx. size (words) | Overlap | Recall@3 | Recall@5 | Chunks | Stored/source word ratio |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | 30 | 70.59% | 82.35% | 1,332 | 1.0492 |
| **400** | **50** | **70.59%** | **88.24%** | **1,247** | **1.0320** |
| 600 | 75 | 70.59% | 88.24% | 1,206 | 1.0109 |

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

The real corpus is published on local Minikube and representative OCR review is complete. Live generation evaluation is in progress; the completed retrieval-only results above do not stand in for it. The fixture set can exercise the API and gate shape offline, but it is not a substitute for a measured real-corpus baseline. Never label a placeholder or fixture result as the production baseline.
