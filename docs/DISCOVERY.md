# Assignment 03 discovery

Work starts from `1e60889` on `codex/dev-ragops` in `aimwnoaim/rahbar`.

RAHBAR already has a FastAPI query service, a Kubernetes indexer Job, Chroma server storage, Ollama embeddings and generation, and Redis caching scoped to the published index revision. The extraction pipeline reads PDF, HTML, Markdown, and text, retaining page and section provenance. The production query path includes citations, abstention, and instruction-pattern filtering within grounded generation. The tracked corpus inventory is in [MANIFEST.md](../corpus/MANIFEST.md).

| Part | Existing capability | Assignment 03 work |
| --- | --- | --- |
| A | Extraction, page-aware chunking and versioned publication | Verify source metadata and text before chunking. Record quarantine and archive history, then synchronize active documents incrementally by ID. |
| B | Recall, abstention and citation fixture runner | Add embedding, retrieval and end-to-end evaluation with seeded repeats, noise and auditable per-question results. |
| C | Assignment 02 regression thresholds | Isolate candidate collections and compare measured outputs under the configurable release gate. |
| D | Request logs, Prometheus metrics and Redis cache | Trace exact generation inputs, document versions, retrieval filtering and rail actions. |
| E | Existing golden questions and corpus inventory | Measure live-query coverage and Batch B drift. Keep the before/after question splits explicit. |
| F | Chroma StatefulSet, Jobs, CronJob, probes and rolling updates | Add the Assignment 03 namespace, evaluation Job, candidate service and persistent raw-data lifecycle. Verify the complete workflow on a clean cluster. |
| G | Architecture notes and previous evidence | Write the explanation, report and screenshot checklist against Assignment 03 evidence. |

Use Chroma server mode and the existing Ollama generator. Pin the embedding model and its digest per collection. Use a chunk-size change as the single candidate variable, with the baseline keeping the existing page-aware chunking. Verification needs an explicit stable logical document ID because the same policy can have multiple source filenames. A truncated PDF can be checked against both the declared page count and its EOF marker. Apply textual truncation heuristics to the authored fixture format so policy tables ending in numbers do not trigger false positives.

The host has Docker Desktop, kubectl and Minikube. Docker reports 12 logical CPUs. The existing `rahbar` profile and an Ollama container are present. The local virtual environment runs Python 3.13, and the Kubernetes image ran Python 3.11. Ollama reported CPU inference and the required nomic and Qwen model tags. The existing cluster serves Assignment 02, so the clean-cluster demo uses its own profile.

Keep the real runs and unedited query traces under `eval/results/` and `traces/`. The golden question checklist must distinguish human authorship from manual review of synthetic questions.
