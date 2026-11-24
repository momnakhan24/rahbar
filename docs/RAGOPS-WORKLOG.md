# Assignment 03 worklog

## Phase 0 — Checkout and discovery

| Decision or change | Reason and verification |
| --- | --- |
| Reused the existing checkout and pointed `origin` at `aimwnoaim/rahbar`. Created `codex/dev-ragops` at `1e60889`. | The target advertised only `main` at that commit. The existing local `dev` tracked the previous remote. Branch isolation allows Assignment 03 CI to run before any merge. |
| Mapped Parts A–G in [DISCOVERY.md](DISCOVERY.md). | The existing FastAPI, Chroma, Ollama and Redis paths already cover core retrieval and generation. Their current behaviors give the new lifecycle a real baseline. |
| Chose logical document IDs supplied by metadata. | Filenames can change between policy versions. A stable ID links verification, the archive, indexing and traces. |
| Reserved a separate Minikube profile for the clean-cluster demo. | A running `rahbar` profile already hosts earlier work. Docker and Kubernetes tools were confirmed available. |
| Keep evaluation outputs, per-question evidence and traces in version control. | Every report metric must be auditable against a real Assignment 03 run. Workflow checks and historical results remain distinguishable from the new evidence. |
| Use the two requested Git author identities for coherent phases. | The commit attribution is repository metadata. The contribution table will separately record who performed or reviewed the work. |

Discovery commit: `ca354c4`. The running Ollama container has Qwen 2.5 3B and nomic-embed-text. The host Python launcher lists 3.13, so Python 3.11 is still needed for the assignment image. All downloaded corpus originals are present under `corpus/raw/`.

## Phase 1 — Verification and raw-data history

| Decision or change | Reason and verification |
| --- | --- |
| Added separate quality, completeness, recency and uniqueness results. | An operator can see why a revision was quarantined. Exact duplicates use a normalized SHA-256 fingerprint, and a pluggable real embedder supports semantic comparison against active documents. |
| Flagged instruction-like text as informational. | The assignment requires the poisoned document to reach retrieval so the retrieval rail can demonstrate its action. |
| Wrote revision bytes before atomically replacing the manifest. | A crash between these steps leaves raw files available to retry. The manifest records which revision is active and preserves previous bytes for restore. Physical current-directory materialization and index synchronization are still pending. |
| Added verification, duplicate, injection and archive/restore tests. | `python -m pytest tests -q` passed four unit tests. `python -m ruff check ragops tests` passed. The tests use fixed test vectors to isolate the lifecycle and do not produce evaluation evidence. |
| Staged the pinned Assignment 02 originals and added a fictional loan policy to Batch A. | The original corpus exercises extraction. The authored policy gives Batch B a controlled fact change. |
| Added a Chroma reconciliation pass after lake admission. | Exact metadata and ID comparisons detect stale or orphaned chunks. Unchanged chunk hashes avoid embedding work. A fixture rerun embedded zero chunks. |
| Corrected Chroma revision publication after a real run. | The thin client rejects distance metadata in updates. Distance belongs in the creation configuration. |

## Phases 2–6 — Query evidence and offline release checks

| Decision or change | Reason and verification |
| --- | --- |
| Reused the grounded Ollama provider for the RAGOps endpoint. | The trace records both inference calls after the seed is populated. One hash covers both requests. |
| Dropped instruction-like chunks before generation. | Verification flags suspicious text without quarantining it. The trace identifies the dropped chunk and pattern. |
| Used an exact, revision-scoped query cache and bypassed it during evaluation. | Cache hits reuse the original request hashes. Both runs exercise the retrieval and generation stages. |
| Used a quote-overlap faithfulness proxy. | The existing generator produces a source-paired excerpt, so the evaluator can compare it against the actual context. |
| Labeled generated golden questions as pending manual review. | The team can complete human authoring and review using the checklist. The expanded set includes off-topic abstentions. |
| Set the candidate chunk-size limit as the only planned pipeline change. | Both collections can run on one corpus split with the same generator and seed. |
| Added eight questions supplied by the project owner. | Kept the author's wording and separately checked the evidence labels. The fee and credit-limit questions lack enough detail for a specific answer. Team review of generated rows is still open. |
| Calibrated coverage against the midpoint of the paraphrase and unrelated score means. | The exploratory cutoff rejected both sets. At the calibrated cutoff, the original golden set failed the 85% coverage rule and the expanded set passed it. The expanded set deliberately samples topics from the live set, so its score is demonstration coverage rather than an independent estimate. |

## Phase 7 — Branch and Kubernetes checks

| Decision or change | Reason and verification |
| --- | --- |
| Pushed `codex/dev-ragops` and ran CI on that branch. | The quality job passed on the first pushed commit. The cluster smoke job started after quality. |
| Created a separate Minikube profile and applied namespace, storage and dependency manifests. | The profile started clean and bound the claims. Cached models and images can be reused locally to reduce registry traffic. |
| Use a shared RWO data PVC on a single node for the assignment demo. | The read-only API uses it for trace append, while ingestion and evaluation Jobs use it for their outputs. Initial resource limits require measurement under load. |
| Added a writer lock and verification preview. | A scheduled Job and manually launched Job can share one PVC without racing to publish state. Preview mode evaluates the proposed revision in memory before any lake or index changes. |
| Reduced vector-write batches and batched the short evaluation pairs. | A long candidate embedding call timed out on the shared CPU model server. Smaller index batches can resume from existing chunks, and grouped pair calls reduce model request overhead. |
| Run the typo experiment without invoking generation. | The experiment measures retrieval. Skipping model decoding avoids measuring unrelated inference time and leaves ordinary trace metrics separate. |
| Deleted and restored data in an isolated fixture lake. | A real Chroma reconciliation reported zero remaining locker chunks and passed its orphan check. Restore reinserted the earlier recorder-policy revision. |
| Used the preloaded Chroma image directly and routed the cluster to the existing pinned Ollama service. | Fresh-cluster registry pulls stalled. Chroma started after requiring the cached image. The cluster verified both model tags through a temporary internal relay while its dedicated Ollama image was still pulling. |
| Ran the fixture ingestion Job on the fresh cluster. | The Job completed with one admitted document and one indexed chunk. The API became ready. The Python 3.11 workload wrote its data through the bound PVC. |
| Restarted Chroma after admitting the fixture and checked the API's write restriction. | The same chunk metadata appeared before and after the pod restart. The API's write command returned exit code 2. |
| Rounded API and Chroma resource requests above their sampled fixture usage. | The raw `kubectl top` sample is in `eval/results/resources_minikube_fixture.txt`. Job sizing still needs a running Job sample. |
| Reuse exact chunk vectors between collections only when the embedding model and version match. | The initial candidate partially populated before an embedding timeout. The candidate can reuse vectors from byte-identical baseline chunks and resume with smaller batches for the remaining chunks. |
| Changed the RAGOps generator to one model call for excerpt selection. | The earlier full-corpus trace captured two Ollama calls and high CPU latency. The second call reproduced an excerpt and citation already chosen by the first. Python now constructs that exact citation and answer directly. The Assignment 02 API still uses its original path. |
| Source-checked the first eight synthetic rows. | [Source checks](../eval/source_checks.json) identifies the physical pages and answer hints. The check is attributable to Codex. |
| Verified the full-corpus Batch B fact change and a real cache hit. | The first query cited five working days. The repeat returned the same citation from the cache. |
| Retained a failed Kubernetes evaluation attempt. | The first fixture candidate run returned HTTP 502 during the second seeded pass, before it reached the gate. The smoke baseline finished and remains available with per-question evidence. |
| Resampled resources during the smoke evaluation. | API and Chroma memory usage was higher under the query workload, so their requests now reflect the larger measurements. |
| Verified parity before moving the fixture to in-cluster Ollama. | The mounted model manifests matched the host manifests. The two Ollama services reported different tag IDs, but the parity query returned identical vectors. The cluster retry uses collections recorded under the in-cluster ID. |
| Rejected the 600-word candidate's measured recall. | Its Batch A recall@5 fell by more than the allowed two points. Retrieval-only results leave the other release criteria unmeasured. |
| Extended probe timeouts on the dedicated cluster after an unhealthy restart. | Under concurrent work, the default one-second Chroma probes failed. The follow-on indexing Job reported no reachable Chroma service, so it did not publish a collection. |
| Restored Chroma with a separately labeled local image built from the same public version. | Relaunching the original cached reference kept returning `ErrImageNeverPull`. The locally built image became ready, then both previously indexed fixture collections were visible on the existing PVC. |
| Completed the optimized Kubernetes smoke gate with in-cluster Ollama. | The candidate passed, failed the stricter latency rule after a ConfigMap-only edit, then passed again after restoring the measured threshold. Both rechecks consumed the same measured result using the same image. |
| Recorded a fixture rollout, a controlled bad configuration, undo, and unseen ingestion. | The Service traces show the collection and top-k at each step, with the original embedding version preserved after undo. The unseen policy was verified, indexed, retrieved, and measured for peak RSS. |
| Completed the full baseline and initial candidate. | The full gate confirmed the 600-word candidate's recall regression. In the seeded baseline repeats, ranking and prompt hashes stayed fixed for the questions whose model answers changed. |
| Selected the 420-word candidate after its full gate passed. | Kept the overlap, embedding model, generator and top-k fixed. The separate 600-word and deliberate top-k regressions remain documented. Updated the candidate Deployment and the eval Job defaults together. |
| Made the demo Job follow the live collection and chunk size. | The CronJob template can still point to the original baseline during a rollout drill. The unseen batch now uses the same settings as the running API. |
| Raised the Chroma limit after a full-corpus OOM and resumed its index. | Kubernetes reported `OOMKilled` when the limit was 1 GiB. The verified lake and persisted prefix let synchronization continue after raising the limit to 2 GiB. Added bounded retries for transient transport errors on idempotent index writes. |
| Completed the full-corpus restore of the Kubernetes index. | The resuming Job kept the chunks already recorded on the PVC, embedded only missing chunks and passed the orphan check. The scoped fixture release remains available separately. |
| Repeated coverage on the final golden files and completed the full Batch B suite. | The final dataset hashes accompany the measured coverage values and exit codes. The full before-and-after evaluation retains per-question outputs and uses the updated answer hint for the changed loan policy. |
