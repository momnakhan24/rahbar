# Assignment 03 — RAGOps report notes

## Cover page

**Project** RAHBAR, FAST-NUCES policy question answering  
**Member 1** [Name] · [Roll number]  
**Member 2** [Name] · [Roll number]

## Figure 3 lifecycle mapping

| Stage | Implementation | Evidence or open item |
| --- | --- | --- |
| Ingest | Stage the pinned corpus and source manifest, then extract pages. | `scripts/stage_ragops_batch_a.py`, `ragops/ingest.py` |
| Verify | Record quality, completeness, recency and uniqueness. Flag suspicious instructions. | `ragops/verify.py`, verification reports |
| Update data lake | Preserve raw revisions and maintain an active manifest, quarantine, archive and restore. | `ragops/lake.py`, unit tests |
| Update retrieval sources | Reconcile document versions, chunk hashes, access and status with Chroma. | `ragops/index.py`, incremental results |
| Offline testing | Compare embedding, retrieval and end-to-end results over seeded repeats and noise. | `ragops/evaluation.py` |
| Live testing | Evaluate the candidate Service and enforce the gate before rollout. | `k8s/eval-job.yaml`, `k8s/README.md` |
| Check coverage | Compare live queries with golden queries and group uncovered topics. | `ragops/coverage.py`, coverage calibration and reports |

## Quality attributes

| Attribute | Measure | Threshold or evidence |
| --- | --- | --- |
| Adaptability | Changed document and chunk counts | An unchanged ingestion should embed zero chunks. |
| Monitorability | Top-result similarity, abstention rate and latency by stage | `/metrics`, `python -m ragops metrics` |
| Observability | Dropped suspicious retrievals, supported citations and cache outcomes | Trace entries and per-question evaluation details |
| Traceability | Exact prompt hash, model revision, source version and access filters | `python -m ragops trace TRACE_ID` |
| Reliability | Index orphan scan, PVC recovery and rolling update availability | Incremental results, fresh-cluster evidence pending |

## A. Verification and incremental indexing

| Run | Seen | New | Changed | Quarantined | Embedded | Deleted chunks | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Full Batch A | 10 | 8 | 1 | 1 | 724 | 0 | [Verification](../eval/results/verification_report_20261123T193246Z-8e991eba.json), [incremental](../eval/results/incremental_20261123T193246Z-8e991eba.json) |
| Batch B against authored Batch A fixture | 11 | 5 | 1 | 5 | 6 | 1 | [Verification](../eval/results/verification_report_20261123T194050Z-9cf18ab7.json), [incremental](../eval/results/incremental_20261123T194050Z-9cf18ab7.json) |
| Batch B against full Batch A | 11 | 5 | 1 | 5 | 6 | 1 | [Verification](../eval/results/verification_report_20261123T200954Z-f924f005.json), [incremental](../eval/results/incremental_20261123T200954Z-f924f005.json) |
| Unchanged full Batch A | 10 | 0 | 0 | 2 | 0 | 0 | [Verification](../eval/results/verification_report_20261123T202520Z-d6eb3766.json), [incremental](../eval/results/incremental_20261123T202520Z-d6eb3766.json) |
| Unchanged authored fixture | 1 | 0 | 0 | 0 | 0 | 0 | [Incremental](../eval/results/incremental_fixture_unchanged.json) |

The full Batch A run flagged the 2023–24 annual report as a near duplicate of the 2019–20 report at cosine 0.951385. The report titles identify different periods. This is a likely false positive from shared structure and boilerplate. [Full Batch A verification](../eval/results/verification_report_20261123T193246Z-8e991eba.json)

With the fixture inbox changed to remove the locker policy, reconciliation deleted its chunk and found no orphans. After restore, a real retrieval returned the earlier recorder policy. [Deletion](../eval/results/incremental_20261123T195520Z-6e4d692a.json), [restore](../eval/results/restore_fixture.json), [restored retrieval](../eval/results/restore_fixture_retrieval.json)

## B and C. Evaluation and release

The full Batch A retrieval-only suite completed both seeded passes and the typo test. It measures the embedding and retrieval layers. The full Batch A end-to-end evaluation also completed.

| Baseline module or retrieval metric | Mean | Absolute difference | Typo delta |
| --- | ---: | ---: | ---: |
| Paraphrase cosine | 0.723273 | 0 | — |
| Unrelated cosine | 0.358703 | 0 | — |
| Cosine gap | 0.36457 | 0 | — |
| Embedding per text, mean ms | 1436.26 | 493.296 | — |
| Embedding per text, p95 ms | 1999.89 | 326.355 | — |
| Maximum repeated vector difference | 0 | 0 | — |
| recall_at_3 | 0.909091 | 0 | +0 |
| recall_at_5 | 0.954545 | 0 | -0.0454545 |
| precision_at_5 | 0.190909 | 0 | -0.00909091 |
| mrr | 0.819697 | 0 | +0.0363636 |
| ndcg_at_5 | 0.85362 | 0 | +0.0159676 |
| p95_retrieve_ms | 190.874 | 154.861 | +76.8335 |

[Batch A retrieval-only scores](../eval/results/retrieval_eval_20261123T201146183667Z_batch_a.json) · [Per-question retrieval output](../eval/results/retrieval_eval_20261123T201146183667Z_batch_a_details.jsonl)

| Full Batch A end-to-end metric | Mean | Absolute difference |
| --- | ---: | ---: |
| correctness | 0.655172 | 0.0689655 |
| faithfulness | 1 | 0 |
| hallucination_rate | 0 | 0 |
| citation_validity | 1 | 0 |
| abstention_correctness | 0.714286 | 0.285714 |
| false_abstention_rate | 0.0454545 | 0 |
| p50_total_ms | 20273.9 | 36677.7 |
| p95_total_ms | 72739.4 | 75767.2 |

[Full Batch A results](../eval/results/eval_20261123T200917344381Z_batch_a.json) · [Per-question generation output](../eval/results/eval_20261123T200917344381Z_batch_a_details.jsonl)

Across the two seeded passes, three questions changed answers while their retrieved order and prompt hashes stayed the same. The observed answer differences arose after retrieval. API response caching was bypassed for both passes. [Repeat diagnostics](../eval/results/baseline_seed_repeat_diagnostics.json)

The 600-word candidate reused 633 vectors from byte-identical baseline chunks, kept 64 previously indexed vectors and embedded 18 remaining chunks. [Candidate reconciliation](../eval/results/candidate_sync.json)

The 600-word candidate is rejected on the measured retrieval requirement. Recall@5 fell from 95.45% to 90.91%, a 4.55 percentage-point drop. The gate recorded the failed recall rule and withheld release because full end-to-end values were also pending. [Candidate comparison](../eval/results/comparison_retrieval_candidate.md), [gate output](../eval/results/gate_retrieval_candidate.txt)

The full baseline and 600-word candidate were also compared across all three levels. [Full candidate comparison](../eval/results/comparison_candidate.md), [full candidate gate](../eval/results/gate_candidate.txt)

The deliberate top-k=1 regression also failed the full gate. Recall@5 fell from 95.45% to 72.73% on the same Batch A questions. [Deliberate regression comparison](../eval/results/comparison_top1.md), [gate](../eval/results/gate_top1.txt)

The 420-word candidate passed every full gate rule. It retained the baseline recall@5 and passed the measured faithfulness, latency and abstention limits. It is the configuration selected for release review. [420-word baseline comparison](../eval/results/comparison_candidate_420.md), [passing gate](../eval/results/gate_candidate_420.txt), [candidate configuration](../config/candidate.yaml)

## D. Observability

The trace saves retrieved text, ranking, rail actions, filtered generation context and the complete Ollama request bodies.

A full-corpus query about lecture credit hours reconstructed both model requests and passed prompt hash verification. The Kubernetes Service also returned the trace metrics through a local port-forward. [Full-corpus trace](../traces/full-corpus-first-answer.jsonl), [reconstructed prompt](../eval/results/reconstructed_prompt_first_answer.json), [Kubernetes metrics](../eval/results/k8s_metrics_endpoint.json)

On the updated full corpus, a fresh query cited the five-working-day policy. The exact repeat returned the same source-backed response from the cache. [Batch B trace and cache hit](../traces/batch-b-version-and-cache.jsonl)

The locker trace retrieved the poisoned policy first. The retrieval rail dropped it for an instruction-pattern match. The remaining chunks fell below the relevance floor, leaving no model context. [Fixture trace](../traces/batch-b-fixture.jsonl)

1. Full-baseline trace `bbdf25092fd14a27b76dc5e207f675b2` asks about loan criteria and types.
2. The highest-ranked chunk came from the entrepreneurship policy at cosine 0.599934.
3. Student Handbook loan passages were retrieved at lower scores.
4. Every hit fell below the configured 0.60 relevance floor, leaving empty context.
5. No guardrail fired and no model request ran. The pipeline abstained at the relevance filter. [Full-baseline abstention trace](../traces/full-baseline-abstention.jsonl)

## E. Coverage and distribution change

The calibration computes the midpoint between the mean cosine scores of paraphrase and unrelated pairs. The initial exploratory threshold of 0.78 yielded 25% coverage before expansion and 62.5% after expansion. Both were below the paper's 85% example. [Calibration](../eval/results/coverage_calibration.json), [exploratory before](../eval/results/coverage_20261123T194246361873Z.json), [exploratory after](../eval/results/coverage_20261123T194439618413Z.json)

At the calibrated cutoff of 0.540988, coverage was 65% before expansion and 100% afterward. The original set returned exit code 1 and the expanded set returned 0. The expanded set deliberately targets uncovered live topics, including abstention for unsupported topics. Its coverage is an in-sample demonstration. [Calibrated before](../eval/results/coverage_20261123T194748858957Z.json), [calibrated after](../eval/results/coverage_20261123T194915958965Z.json)

The retrieval-only Batch B comparison measured 29 shared questions with hits before and after. The top-ranked document or version changed on 2 of those questions. Mean top-hit similarity moved by +0.000256. The aggregate tables also include the new Batch B questions, so the shared-question comparison isolates the original cohort. [Batch B retrieval comparison](../eval/results/comparison_retrieval_batch_ab.json)

The coverage rerun with the owner's questions measured 65.00% before and 100.00% after expansion. It preserved the fail/pass behavior. [Final before](../eval/results/coverage_20261123T205246044150Z.json), [final after](../eval/results/coverage_20261123T205330610091Z.json), [exit codes](../eval/results/coverage_final_exit_codes.json)

| Full-suite metric | Batch A | Batches A + B | Delta |
| --- | ---: | ---: | ---: |
| recall_at_3 | 0.909091 | 0.888889 | -0.020202 |
| recall_at_5 | 0.954545 | 0.962963 | +0.00841751 |
| mrr | 0.819697 | 0.825309 | +0.00561167 |
| ndcg_at_5 | 0.85362 | 0.859641 | +0.00602134 |
| correctness | 0.655172 | 0.691176 | +0.0360041 |
| abstention_correctness | 0.714286 | 0.857143 | +0.142857 |
| faithfulness | 1 | 1 | +0 |
| p95_total_ms | 72739.4 | 33446.5 | -39292.9 |

The full before/after comparison includes the extra Batch B questions. The recorder loan answer hint changes with the active document version. The new distribution and the enlarged test split both affect the aggregate deltas.

[Full before/after comparison](../eval/results/comparison_batch_ab.md) · [Batch B evaluation](../eval/results/eval_20261123T204647590405Z_batch_ab.json) · [Batch B per-question evidence](../eval/results/eval_20261123T204647590405Z_batch_ab_details.jsonl)

## F. Kubernetes

The fresh `ragops-dev` Minikube profile bound the data, model and Chroma PVCs. Fixture ingestion ran in the Kubernetes Job. Live and candidate Deployments reached readiness, the API rejected a write attempt, and the fixture chunk survived a Chroma pod restart. The Kubernetes workloads called the pinned local Ollama through a temporary relay while the in-cluster Ollama image pull was stalled. [Ingest Job](../eval/results/k8s_fixture_ingest.json), [API write rejection](../eval/results/k8s_api_readonly.txt), [persistence](../eval/results/k8s_chroma_persistence.txt)

| Workload | Highest sampled CPU | Highest sampled memory | Resource request |
| --- | ---: | ---: | --- |
| Live API | 286m | 270 MiB | 300m CPU, 320 MiB |
| Candidate API | 274m | 264 MiB | 300m CPU, 320 MiB |
| Chroma | 178m | 538 MiB sampled before full indexing | 200m CPU, 1024 MiB |
| Eval Job | 0m | 25 MiB | 200m CPU, 128 MiB |
| Unseen ingestion Job | — | 79.46 MiB peak RSS | 1500m CPU, 1280 MiB shared ingestion profile |
| Full ingestion Job | 1324m | 1085.70 MiB peak RSS | 1500m CPU, 1280 MiB |

The CPU and memory samples came from different stages of the fixture run. The Eval Job sample was taken while waiting on its dependency. Its configured request allows headroom for active work. The full ingestion sample informed the shared ingestion request. [Service sample](../eval/results/resources_minikube_fixture.txt), [Eval Job sample](../eval/results/resources_minikube_eval_job.txt)

The first full-corpus Kubernetes ingestion verified the source data and wrote a partial index before Chroma exceeded its original 1 GiB memory limit. The Job's write failed when its Service temporarily disappeared. Chroma's limit was raised to 2 GiB on the isolated node, and the next Job resumed reconciliation from the existing lake and persisted chunk IDs. [Timed ingest output](../eval/results/resources_minikube_full_ingest.txt), [resource sample](../eval/results/resources_minikube_full_ingest_sample.txt), [OOM termination](../eval/results/k8s_full_chroma_oom.json)

The resumed Job kept 432 persisted chunks, embedded the remaining 292, and passed its orphan check. The collection held 724 chunks. [Kubernetes verification](../eval/results/k8s_full_corpus_verification.json), [resume Job](../eval/results/k8s_full_corpus_resume.txt), [final collection](../eval/results/k8s_full_corpus_collection.json)

The Kubernetes smoke baseline finished. The first candidate Job received an HTTP 502 during evaluation, so it exited before the gate. [Smoke baseline](../eval/results/k8s_smoke_baseline.json), [per-question output](../eval/results/k8s_smoke_baseline_details.jsonl), [initial Job failure](../eval/results/k8s_smoke_first_failure.txt)

The optimized candidate Job completed the two-question fixture evaluation using in-cluster Ollama. All gate rules passed. A ConfigMap-only change forced the latency rule to fail on the same recorded result, and restoring the original ConfigMap let the Job pass again without rebuilding the image. This was a Kubernetes smoke release with the authored fixture. [Candidate evaluation](../eval/results/k8s_smoke_candidate.json), [per-question output](../eval/results/k8s_smoke_candidate_details.jsonl), [gate pass](../eval/results/k8s_smoke_gate_pass.txt), [strict gate fail](../eval/results/k8s_smoke_gate_fail.txt), [restored gate pass](../eval/results/k8s_smoke_gate_restored.txt), [model parity](../eval/results/k8s_model_embedding_parity.json)

| Fixture deployment step | Collection | Embedding version | Top-k |
| --- | --- | --- | ---: |
| Before release | `rahbar_kube_v1_nomic` | `8688dbc0926c` | 5 |
| Passing fixture release | `rahbar_kube_v2_nomic` | `8688dbc0926c` | 5 |
| Controlled regression | `rahbar_kube_v1_nomic` | `8688dbc0926c` | 1 |
| After undo | `rahbar_kube_v2_nomic` | `8688dbc0926c` | 5 |

[Rollout and undo](../eval/results/k8s_fixture_rollouts.txt) · [Service traces](../traces/k8s-fixture-rollouts.jsonl)

After undo, the unseen-batch Job verified and indexed the poster-printer policy. A live query retrieved the new document. [Unseen ingestion Job and peak memory](../eval/results/resources_minikube_unseen_ingest.txt) · [Verification](../eval/results/k8s_unseen_verification.json) · [Unseen document trace](../traces/k8s-unseen-batch.jsonl) · [Trace on Kubernetes stdout](../traces/k8s-stdout-after-undo.jsonl)

## Short answers

**(a)** Uniqueness caught both copied documents and the lightly edited duplicate. Completeness caught the missing title and missing page. The locker document passed verification and was flagged as suspicious. A retrieval rail can remove instruction-like chunks before generation. Meaning-changing or indirect instructions can evade pattern matching. [Batch B verification](../eval/results/verification_report_20261123T194050Z-9cf18ab7.json)

**(b)** Embedding separation and repeatability looked consistent, but the question about the online A+ grading table missed the expected grading page. The Academic Rules Handbook supplied related grading passages. This shows that global embedding separation can coexist with a source-specific retrieval miss. [Per-question retrieval output](../eval/results/retrieval_eval_20261123T201146183667Z_batch_a_details.jsonl)

**(c)** Archiving preserves the bytes and provenance needed to restore an old version and reproduce a citation. Deleting lake bytes eliminates those recovery options. Removing its derived chunks keeps stale content outside the active index.

**(d)** Faithfulness measures whether the generator quotes the selected evidence. A fully supported quote can still address the wrong policy, which is why correctness and retrieval labels are scored separately. This illustrates the paper's measurement challenge in §6.2.

**(e)** The difficult design trade-off is semantic verification across long documents. Shared report structure can make independently valid reports look redundant. The recorded Batch A false positive is evidence of that limitation. [Full Batch A verification](../eval/results/verification_report_20261123T193246Z-8e991eba.json)

**(f)** The ingestion Job owns writes and the CronJob schedules them. The PVC retains raw and archived data. The Chroma StatefulSet retains the vector state. The ConfigMap supplies gate limits. Services isolate candidate and live traffic. Deployment rolling updates and rollout history handle release and reversal.

## Contributions and AI disclosure

| Member | Work or review |
| --- | --- |
| Member 1 | [Confirm implemented, reviewed and demonstrated tasks] |
| Member 2 | [Confirm implemented, reviewed and demonstrated tasks] |

Codex assisted with implementation, original synthetic fixtures, documentation and execution. The project owner wrote the eight questions identified as human-authored. The team will record its contributions, review synthetic labels and demonstrate the Kubernetes flow.
