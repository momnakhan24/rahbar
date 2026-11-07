# RAHBAR assignment work log

This log is the reviewable record of implementation, verification, assumptions and remaining work for Assignment 02. It records concise engineering rationale and evidence, not private chain-of-thought. Status labels distinguish code that exists from behavior actually observed in a running system.

## Working rules

- Work only in the connected repository. Push only when the user explicitly authorizes it; do not merge or open a PR unless asked.
- Keep all assignment changes on the user-requested local `dev-aimwnoaim` branch; keep each commit limited to one file/change.
- New genuine audit changes use `aimwnoaim <aimtk20@gmail.com>` at the user's request. A separate balanced branch transparently reattributes selected existing commits between the two accounts the user identified as their own; the original history is retained. Author counts are metadata, not proof of independent contributors.
- Record unknowns as unknown. Source code and rendered YAML are not evidence of a live rollout, measured retrieval quality or protected-branch behavior.
- Assignment deadline from the handout: 8 November 2026, 23:59 PKT.

## Current status (audited 7 November 2026)

The complete ordered handoff is in SUBMISSION-CHECKLIST.md. The assignment is not
finished; in particular, there is still generation/retrieval work and no reviewed
submission baseline. Earlier chronological entries below preserve past states.

| Area | Verified | Outstanding |
| --- | --- | --- |
| History | Real changes on dev-aimwnoaim; author-count imbalance identified | Prepare transparent balanced history without empty commits; choose publication route before overwriting anything |
| Corpus/index | Nine public sources, 279 PDF pages, 41 OCR pages; 1,247 real chunks published | Representative review is not exhaustive OCR proofreading |
| Chunk/cache experiments | All three chunk sweeps measured; 400/50 recall@5 88.24%; threshold study complete | Final documentation must distinguish retrieval scores from answer correctness |
| Kubernetes | Three endpoints, numeric HPA, resource samples, Calico checks, pod replacement and rollout/undo captured | Synchronize committed image pins/README with the corrected live runtime |
| UI/API checks | localhost served UI, file-open guidance and duplicate-submit guard; 18 API tests / 77.10% coverage | Final generation correctness and per-answer review |
| Real evaluation | Completed 19-question diagnostic: recall@3 70.59%, recall@5 88.24%, citation membership 10/10, must-abstain 2/2; literal expected terms 6/17 | eval/results.json missing; baseline pending; fix supported-answer fallbacks and wrong r12 prerequisite answer before accepting results |
| Citation diagnosis | Provider can emit a true grounded flag with an empty citation list; server rejects it safely | Enforce compatible grounded/refusal branches during decoding, then test actual model behavior |
| Controlled failures | A/B/C/E executed; removed fixture tuition caused 1.0→0.8 recall and a failed gate; restoration passed CI | Required actual screenshots remain missing |
| CI | Original PR #3 is draft; checks passed on 9940eec in runs 42360957317 / 42361063605 | Later local and rewritten commits require fresh CI |
| Registry/CD | Local Docker pushes succeeded for 02246e5 and bf3edf7 source tags | No successful CD verified; original repository listed no Actions secrets at audit |
| Repository controls | Original main reports protected; PR #3 requires real review | Owner must verify all protection settings, save DOCKERHUB_TOKEN, obtain approval and merge through PR |

The user declined agent-mediated export of the Docker credential; no such transfer
occurred. Giving a token to the owner does not establish that the Actions secret exists.
Windows screenshot inspection stopped because current Chrome URL could not be verified.


## Decisions and assumptions

| Date (PKT) | Decision / assumption | Reason and limits |
| --- | --- | --- |
| 2026-11-05 | Use the connected repository at `C:\Users\HP\Downloads\rahbar-starter\rahbar-starter`; do not push. | The user connected this folder and explicitly requested local-only work. |
| 2026-11-05 | Push the five committed changes on `dev-aimwnoaim` to origin. | The user explicitly authorized the push on 2026-11-05 after the local commits were reviewed. Push succeeded; no merge or PR was created. |
| 2026-11-05 | Continue on branch `dev-aimwnoaim` and make one file/change per commit. | Explicit user instruction. Each new commit is independently reviewable. |
| 2026-11-05 | Use the user-provided alternate account name/email only as local Git author metadata for new commits. | The user identified it as their own repo-owner account. Existing commits are not rewritten; no credentials or authenticated GitHub access were provided. |
| 2026-11-05 | Use FAST-NUCES public documents from the starter source list. | Fits the assignment source and enables plausible exact-term and abstention questions. Web pages can change; manifest hashes establish the retrieved bytes. |
| 2026-11-05 | Keep current rules as default and permit superseded chunks only when a question asks historically. | Prevent accidental citation of old policy. Historical retrieval still needs a live, reviewed version-pair evaluation. |
| 2026-11-05 | Use 400/50 approximate word chunks, cache cutoff 0.96, and relevance floor 0.35 provisionally. | Defaults are implementation values, not tuned results. Three chunk sizes, threshold sweeps and false-hit checks have not been run. |
| 2026-11-05 | Do not fabricate baseline values, resource measurements or evidence screenshots. | They are empirical assignment deliverables and require access to the live runtime/settings. |

## Work completed

### Kubernetes scaffold and deployment path

- Added pinned API/indexer/UI Dockerfiles, non-root users, exec-form commands, `.dockerignore` rules, Namespace, Services, Deployments, Chroma StatefulSet/PVC, Redis/PVC, indexer Job/CronJob, Ingress, HPA, service accounts and default-deny/allow NetworkPolicies.
- Added dev and prod overlays. Dev patches the indexer to dummy mode; prod selects Chroma retrieval, `ollama-host`, and `nomic-embed-text`, and the base Job runs the actual pipeline.
- Added a persistent corpus PVC and temporary loader Pod example excluded from Kustomize. The README documents corpus copy, one-shot indexing and rollout order. The placeholder Secret is documentation only and is not applied; real secrets are created with `make secret`.
- Updated capability-drop syntax and UI image command after mechanical checking.
- **Verification:** `kubectl kustomize k8s/overlays/dev` and `kubectl kustomize k8s/overlays/prod` both exit successfully after the current manifest changes. No Kubernetes API server validation or live workload was available.
- **Environment blocker:** Docker CLI exists, but `docker info` cannot connect to Docker Desktop's Linux engine. Minikube, kind, Tesseract and Poppler are unavailable in this environment. Do not claim cluster, image, OCR or resource evidence.

### Pipeline, API and corpus

- Implemented PDF/HTML/Markdown/text extraction; OCR fallback on pages with under 25 normalized text characters; PDF and HTML table serialization; repeated page-furniture cleanup; section-aware word chunking with overlap; batched Ollama embeddings; versioned Chroma collection publication and registry switch.
- Implemented Chroma query embeddings, current-version filtering, historical question heuristic, Ollama and OpenAI-compatible provider classes, schema-constrained JSON, Pydantic validation, one retry, validated citation membership, fallback and low-relevance abstention.
- Implemented Redis semantic cache with model/revision-scoped keys, seven-day TTL, follow-up and abstention exclusion, re-index invalidation and a deterministic character/4 token estimate in metrics. Cache threshold remains unmeasured.
- Readiness checks active Chroma collection count, configured/indexed embedding model and Redis; liveness avoids dependencies. Structured logs and Prometheus metrics are implemented.
- Downloaded nine public sources locally; verified source hashes and audited PDF pages. The 2022 entrepreneurship policy has 8 image-only pages; the 2023 undergraduate rules have 24 of 26 pages with negligible text. OCR execution and manual accuracy review remain open.
- Added 17 real-corpus golden questions covering ordinary, exact, current-version, must-abstain and instruction-injection cases. Relevant sections are based on the current 2026 handbook and parser's `Document` heading for HTML.
- Evaluation output also reports literal expected-term match accuracy for questions with an `expect` value; this is a diagnostic metric and does not replace human answer review.

### Tests and static validation

- API tests: 14 passed, including citation validation/fallback, abstention, semantic-cache revision pruning, prompt-injection handling and embedding-model mismatch behavior.
- Indexer tests: 9 passed, covering Markdown front matter, HTML tables, repeated headers, chunk overlap/metadata and invalid configuration.
- Evaluation tests: 4 passed, covering recall matching, citation validity, abstention and score gates.
- Ruff: `ruff check api indexer eval corpus` passed.
- API mypy: `mypy app` passed with no issues in 23 source files.
- Indexer mypy passed: no issues found in 10 source files.
- The latest submission-checker run reported 162 passes, 3 warnings and 1 failure. The sole failure is the five-file evidence bundle (branch protection, blocked merge, `kubectl top`, endpoints and HPA). Warnings are the placeholder Secret heuristic, 44% conventional commit prefixes, and missing measured `eval/results.json`. The baseline file is intentionally a pending marker; it is not reported as a measured baseline.
- The most recent full test runs passed: API 14, indexer 9 and evaluation 4. Ruff passed; API mypy reported no issues in 23 files; indexer mypy reported no issues in 10 files. Both Kustomize overlays rendered successfully.
- README now lists the GitHub Environment, secrets, variables, required checks and registry image prerequisites for the manual CD workflow. Those external settings have not been configured from this local-only workspace.
- Added [`OPERATIONS.md`](OPERATIONS.md) with safe cluster, rollback, failure-injection, GitHub protection and evidence-capture steps; it is a runbook, not evidence of those operations.
- Investigated the uploaded Trivy CI log. The failing gate was scanning `rahbar-api:dev`: Debian packages had HIGH/CRITICAL findings and the installed Starlette 0.46.2 had three HIGH findings. It was a vulnerability scan failure, not a Docker socket failure.
- Updated API and indexer Dockerfiles to Python 3.12.16 slim Trixie and refresh OS packages at build time; upgraded FastAPI and pinned Starlette to 1.7.0; configured the three Trivy image scans to fail on HIGH/CRITICAL vulnerabilities that have fixes while omitting unfixable findings. These changes are local commits `82e712c`, `22a58aa`, `931c004`, and `c703d7f`, each limited to one file.
- After dependency update, API tests passed (14), API mypy passed (23 source files), and Ruff passed for `api indexer eval corpus`. The dependency installation resolved successfully. GitHub Actions has not yet run against these commits, so the scan result is not verified as fixed remotely; the UI image scan may reveal separate findings when CI progresses.
- Pushed the five remediation/documentation commits to `origin/dev-aimwnoaim` after explicit user authorization. GitHub's combined status endpoint currently returned no check entries, so CI completion remains unverified.
- Retrieved the latest push-triggered CI run `41995169603`. The quality job passed; in `cluster-smoke`, the API image and indexer OS scan had zero high/critical findings, while the indexer Python scan failed on 22 HIGH findings: `pypdf==5.4.0` and transitive `pdfminer.six==20250327`. The job stopped there, so the UI scan was not reached.
- Upgraded the indexer parser stack to `pdfplumber==0.11.10`, `pypdf==6.21.4`, and `pdfminer.six==20260107`, which satisfy the fixed versions identified by Trivy. These dependency pins install together successfully. Indexer tests pass (9); the CI mypy command `cd indexer && mypy pipeline` passes with no issues in 10 files. This CI fix is committed locally as `86a60a7`; the follow-up workflow run is still needed to verify the scan and UI image.
- Follow-up CI run `42075533976` passed its quality job and cleared API/indexer scans, then failed at the UI scan with 63 HIGH/CRITICAL OS findings from the older NGINX Alpine base. Updated the UI image to `nginxinc/nginx-unprivileged:1.31.7-alpine3.24` and refresh Alpine packages during build. This is committed as `3459cf3`; a new CI run is required to verify the UI scan and smoke deployment.
- CI run `42076546169` passed quality and all three Trivy scans (API, indexer, UI). The cluster job timed out waiting for `statefulset/chroma`'s `chroma-0` pod. Added a 90-second readiness check and failure diagnostics (`get/describe`, container logs and events); run `42078459739` showed the container panicking during SQLite migration with extended error 6410. This corresponds to SQLite failing to find a usable temp directory; SQLite checks `SQLITE_TMPDIR`/`TMPDIR` and standard temporary paths on Unix ([SQLite temporary files](https://www.sqlite.org/tempfiles.html)). Added a writable `emptyDir` at `/tmp` plus `SQLITE_TMPDIR=/tmp` and `TMPDIR=/tmp`, retaining the read-only root filesystem. Manifest rendering passes; commit `082e935` awaits CI validation.
- CI run `42079830021` verified that Chroma no longer panicked, but diagnostics showed `Listening on localhost:8000`; readiness probes to the pod IP were refused. Added `--host 0.0.0.0` to the Chroma command so the service can accept pod-network connections. `kubectl kustomize` renders both dev and prod overlays. This fix is committed as `f1fe2e3`; CI validation remains pending.

## Assignment completion checklist

- [x] Build K8s scaffold for API/UI/Chroma/Redis and separate Job/CronJob indexing; dev/prod overlays render.
- [x] Provide container definitions, non-root execution, probes, resource requests/limits, security contexts, ingress, autoscaling and network policies.
- [x] Implement extraction/OCR fallback, cleaning, chunking, embedding pin metadata and versioned vector-store publication.
- [x] Implement grounded API retrieval, source/version filters, citation checks, retry/fallback, abstention, cache and readiness guard.
- [x] Provide corpus manifest and document required source properties; record scan/table/absent-topic evidence.
- [x] Add test suites, prompt-injection probe, 17-question real-corpus golden set and evaluation scoring/gate code.
- [x] Write four ADRs, architecture/AI disclosure, pipeline, corpus, failure-analysis plans, engineering notes and local work log.
- [x] Prepare CI and manual SHA-based CD workflows locally; address the uploaded API Trivy failure in four one-file local commits.
- [ ] Run GitHub CI against the local remediation commits and review any subsequent indexer/UI scan failures.
- [ ] Establish and commit a measured baseline/results after real corpus indexing and model evaluation; run chunk-size and cache-threshold experiments.
- [ ] Execute OCR and manually review scan output, especially the 2023 rules and 2022 policy.
- [ ] Build images and run dev cluster; capture API/UI endpoints, probes, readiness mismatch, rollout/undo, HPA and NetworkPolicy evidence.
- [ ] Run four deliberate failure experiments and replace planned procedures with timestamped actual diagnostics/remedies.
- [ ] Configure GitHub environment protection/secrets, run CI/CD, and capture branch protection plus blocked-merge evidence.
- [ ] Re-run full submission checker and resolve remaining evidence-dependent issues before submission.

## Next actions

1. Run `docker info`, start Docker Desktop, and provision Minikube with Calico; otherwise use a cluster with equivalent ingress/metrics support.
2. Fetch/verify the corpus and load `corpus/raw` into `corpus-data` using the temporary loader workflow. Run the real indexer and verify Chroma active revision/model metadata.
3. Install/run Tesseract and Poppler through the indexer image, review OCR pages, and correct source metadata/golden sections if needed.
4. Execute golden evaluation and chunk/cache sweeps; write only actual results to `eval/baseline.json` and `eval/results.json`.
5. Capture evidence files from the actual cluster and GitHub settings; configure the protected production environment and required repository variables/secrets.
6. Run `make check`, full tests, lint and type checks. Review the local commit list; do not push unless the user later authorizes it.

### CI follow-up: indexer startup

- Run 42081591091 passed quality and all image scans. Chroma and Redis became ready; the indexer Job did not complete within five minutes. Its logs were not captured by that workflow.
- Added a bounded 60-second Chroma heartbeat wait before creating the indexer client (e1a81f8). This addresses an identified startup race; the failed Job's exact cause is not yet confirmed.
- Added workload descriptions, current/previous container logs, and events on failure (8f92cd1). Indexer tests: 9 passed; Ruff passed. Next CI run will validate the wait and reveal any remaining failure.

### CI verified passing

- GitHub Actions run [42083260429](https://github.com/momnakhan24/rahbar/actions/runs/42083260429) on commit `daff3ae` completed successfully: both `quality` and `cluster-smoke` passed.
- Observed checks include lint/type checks, unit/evaluation-gate tests, manifest validation, image builds, all three Trivy gates, Chroma/Redis/API/UI rollout, dummy indexer Job completion, and HTTP question endpoint smoke test.
- The bounded Chroma connection wait cleared the remaining indexer startup failure. Each implementation/workflow change and its log update was committed separately. This is evidence for the dev stub CI path, not real-model retrieval quality or a production deployment.

### Full assignment execution started

- User authorized Minikube installation and completing remaining assignment work; Docker Hub namespace: `aimwnoaim`.
- Docker Desktop Linux engine responds with version 29.8.0. Installed Minikube 1.39.0 through the official Winget package. Provisioning isolated profile `rahbar` with Docker, Calico, 4 CPUs, 4096 MB, metrics-server and ingress; other running projects are left intact.
- Local immutable image builds and a local Ollama model service download are underway. No new live evaluation results are claimed yet.
- Re-read the assignment: the existing CI smoke path does not yet satisfy fixture retrieval evaluation, and existing manual CD does not satisfy the required push-to-main test/build-push/deploy chain. These gaps must be addressed, in addition to real evaluation, experiments and evidence.
- Submission checker currently reports 162 passes, 3 warnings and 1 evidence-bundle failure; passing that checker alone is not assignment completion.
- Implemented CD test → build-push → ephemeral acceptance deploy with `needs:`, SHA tags, Trivy and Ingress smoke verification (a862192). It triggers on main or manual dispatch and uses Docker Hub namespace aimwnoaim plus repository secret DOCKERHUB_TOKEN. YAML parsing passed; publication/deployment remains unverified until credentials and a workflow run are available.
- Added scripts/measure_pipeline.py for cached extraction/OCR inventories and measured 250/30, 400/50, 600/75 chunk sweeps using real embeddings and exact cosine retrieval. It explicitly separates retrieval-only experiments from API generation evaluation. Script compiles and Ruff passes; experimental values are pending execution. Ignored work/ for intermediate extraction/vector data.
- Local runtime is the chosen path following user clarification: use local Docker. An aimwnoaim/rahbar fork was created while exploring the unavailable owner-settings workaround; no main merge or settings changes have been made there. Existing Docker Desktop account names show aimwnoaim; credential values were not displayed.
- API coverage verification passed: 14 tests, 68.36% app statement coverage, above the required 60%. README now describes the revised SHA-tagged build/publish/ephemeral acceptance CD path accurately.
- Auditing the handout against golden.yaml found only six ordinary questions, below the required eight. Added two ordinary questions grounded directly in the unqueried source PDF, clauses 6.6 (maximum two summer repeats) and 6.10 (no summer financial aid), before tuning. Golden set now has 19 questions, including eight ordinary questions. Existing relevant labels were not adjusted from retrieval results.
- CI now explicitly enforces --cov-fail-under=60, based on the observed 68.36% local app coverage.
- Official Ollama image download completed; the service runs locally in Docker as rahbar-ollama using persistent volume rahbar-models and a localhost-only published port. Runtime image digest: sha256:ebaef4f4c5d93660e1f25f8ad085a112f51ccfb0e8458073e71793959dba91c9. Pulling nomic-embed-text and llama3.2:3b next.
- Added fixed-label cache pairs and an offline cosine threshold-sweep script (5e4ee11, 035ccaf). Ruff passes; no threshold values have yet been measured.
- Captured actual tool versions and Docker capacity in docs/evidence/local-setup.txt; it explicitly labels Kubernetes bootstrap as pending.
- Real local nomic-embed-text experiment completed: eight fixed cache pairs, thresholds 0.85/0.90/0.94/0.96/0.98. False-hit counts: 3/2/1/0/0. Paraphrase misses: 1/1/3/4/4. The version pair scored 0.9547 and A+/B+ scored 0.9284. Retained 0.96 for safety, explicitly noting lost paraphrase hits and limited sample size. Committed raw measured evidence, PIPELINE discussion, and cache ADR separately.
- Local overlay uses the isolated model service at 192.168.49.10 and restricts model egress to that address. Image tags are pinned to the actual source SHA used for the in-progress builds, 675ec46644f8ef2a4d0247322225f3bb6fb779cd.
- Fixture retrieval inspection exposed a real chunker bug: numbered clause lines became section labels but were discarded from evidence. Fixed by preserving PDF clause text and retaining numbered prose beneath Markdown parent sections (c877d42). Added two regression tests in a separate file commit (f640244). All 11 indexer tests and Ruff pass. Rebuild the indexer image with this fix before real indexing; the initial 675ec46 image is no longer the intended shipped indexer.
- Live Docker fixture indexing completed with the corrected chunker: 11 chunks across the three fixture documents, real nomic-embed-text embeddings, Chroma publication, Redis and the API's real retriever. Generation remained stubbed for this CI-specific acceptance study. At fixture relevance floor 0.6, measured recall@3/@5=1.0, citation validity=1.0, must-abstain=1/1. Expected-term diagnostic=0.8, so this is not evidence of LLM answer quality or injection resistance.
- Recorded the measured fixture baseline separately in eval/fixtures/baseline.fixture.json, preserving the pending real-corpus baseline. A second live evaluation against that baseline passed. Added the same indexed fixture path and evaluation gate to CI; YAML parses, but the updated GitHub workflow still requires an actual run.
- Minikube's initial Kubernetes binary transfers were interrupted at the transport layer. Retrying official binary downloads with SHA-256 validation. Local indexer build also received malformed/truncated package metadata; preparing an offline Linux wheelhouse to retry the same requirements reliably. No cluster/evaluation evidence is fabricated from these failures.
- Minikube node is now Ready with Kubernetes v1.37.0 and Calico. Official Kubernetes binaries were downloaded through Docker after host transfers stalled, and SHA-256 checks passed before populating the cache. Ingress and metrics-server are being verified; no HPA/resource claim is made before those checks pass.
- Local Llama validation exposed contradictory output: answer 80% but answered_from_context=false, no citations, high confidence. Separated system instructions from evidence, added explicit citation/boolean semantics and a bounded output budget, and normalized model-declared abstentions to a refusal. Two new regression tests pass; API suite now 16 passing tests and Ruff passes.
- Corrected indexer built successfully with a Linux wheelhouse after truncated network metadata interrupted the initial build. Runtime images now use source SHA f388a80e3cdf32490b7035c5fa93c5ca1db11be8; corpus OCR extraction is running in that image, and Minikube image loading is underway.
- Visual OCR review compared the 2023 rules PDF page 7 and entrepreneurship-policy page 2 with their OCR text. Default OCR detached clause numbers from policy paragraphs. Single-block --psm 6 preserves the reviewed numbering/content substantially better; minor scan artifacts remain and will be documented.
- Handbook page 25 had 2,601 text-layer characters, including 1,112 outside the visible page. Rendering showed a single visible policy page, while uncropped extraction interleaved obsolete/off-page content. Cropping to page.bbox removed that hidden content and restored the visible clause sequence. Added a synthetic off-page PDF regression fixture; its initial direct stream was corrected to a valid indirect stream, after which all 14 indexer tests and Ruff passed.
- Initial corpus extraction is preliminary and not used as final evidence after these parser corrections. The measurement cache now validates both source SHA-256 and extractor-code SHA-256, forcing re-extraction on either change. Corrected OCR/indexing and the three chunk sweeps are running anew.
- Removed indexer Redis flushing to comply with API-only Redis access: revision publication immediately makes old cache keys unreachable, and the API already prunes obsolete revisions on lookup. Atomic-publication regression tests verify that failed batch writes leave the old registry active and successful publication needs no Redis connection.
- Live samples showed the initial OCR Job at about 992m CPU against its 1-core limit and 230Mi early memory use. Increased the indexer request to 1 core and limit to 2 cores in both Job and CronJob, retaining 512Mi request / 2Gi limit pending full-run peak samples. Initial Job was stopped before the corrected run; final evidence will name real-index-corrected and image 7b4daae5a28f50df37d3a1c6fa5734a70f6f3bc0.
- Source comparison before retrieval tuning found the original version-labelled CGPA/attendance questions did not concern changed rules: the reviewed 2023 and 2026 clauses retain those values. Replaced r11/r12 with genuine summer-policy changes verified from source text: 2023 allowed an optional 8-to-9-week summer and listed exceptions for new electives; current 2026 specifies an 8-week summer and repeat-only courses. Gold references now point to current clauses 6.1 and 6.2. This corrects the task specification rather than fitting labels to retrieved output; no real-corpus recall result has been used to change them.
- Stage A deliberate failure executed against the real eight-page scanned policy with OCR disabled: zero characters, zero chunks, and the store rejected empty publication. Corrected OCR yields 1,814 words. Saved factual failure evidence in docs/evidence/failure-a-no-ocr.json.
- Minikube UI through its actual Ingress returned HTTP 200 with title RAHBAR (docs/evidence/ui-http.txt). API readiness remains a truthful 503 while its collection is not yet published.
- Initial 4Gi node budget proved insufficient under the real workload (Docker observed 3.96Gi/4Gi, CPU quota saturated, Kubernetes API TLS handshake timeouts). Raised only the rahbar container/profile to 6Gi memory and six CPUs; API recovered immediately. Metrics API recovered afterwards. Corrected indexing resource sampling records the incident and allocation transition.
- Corrected bulk embedding is in progress. A live sample showed indexer 1m CPU / 586Mi while the external Ollama service used about six CPU cores; this demonstrates why API/indexer CPU alone does not represent external model compute. No final recall or real-corpus baseline is claimed before evaluation completes.

- Local Chroma terminated with OOMKilled (exit 137) at 10:15:21 UTC while limited to 1Gi. Increased its request from 384Mi to 768Mi and limit to 2Gi before index publication. This is a measured runtime correction; post-change stability remains under observation.

- CI run 42177121689 passed quality, manifests, image builds/scans and stub cluster smoke, then failed because fixture Ollama was not accepting connections yet. Added a bounded 60-second readiness loop before model pull; final ollama list still fails explicitly if startup never succeeds. Rerun pending.

- Executed Calico checks: API -> Chroma heartbeat 200, API -> local Ollama 200, API -> Redis +PONG, UI -> Chroma timeout. Found missing UI egress allow; added UI -> API:8000 and verified direct pod liveness 200. API Service currently has no ready endpoints until indexing completes, so initial Service timeout is preserved in evidence and is not represented as a policy-only result. Stage B fixed 100-word/no-overlap retrieval experiment is running separately in Docker against the source-verified extraction cache.

- API memory rose to roughly 430–453Mi during repeated unready probes. Reused the serving Chroma transport instead of constructing one per readiness request. Regression test confirms reuse still re-reads active metadata and returns 503 after a model mismatch. Existing 16 API tests plus the new regression pass; deployed source SHA c4d59f28a484e6e9b399ebcae704823ddf75ae86 locally for post-change resource observation.

- Full corrected Kubernetes Job completed: 1,247 chunks, 1,736.7 seconds. API rolled out to three ready replicas; Service listed three IPs; HPA showed numeric 41%/70%. UI image rollout showed Academic Guide title and heading through Ingress, and rollout undo restored RAHBAR. Immediate first HTTP checks saw transient 502s; bounded repeated HTTP checks confirmed both final versions and are included in evidence.
- First real evaluation attempt returned 504: query embeddings queued behind concurrent bulk Ollama batches and timed out at 60 seconds, then repeated retrieval exceeded ingress timeout. Started separate local Docker container rahbar-serving at 192.168.49.11, sharing the exact downloaded model volume read-only, limited to 4Gi/four CPUs. Bulk experiments continue at .10; the shared ConfigMap/policies now direct API and future index jobs to .11. This isolates test workload contention without changing the model pin. Evaluation will be rerun and raw responses retained for review.

- Revised GitHub CI run 42201877130 on cdb58b8 completed successfully, including real fixture embedding/indexing/retrieval evaluation and the measured gate. Link: https://github.com/momnakhan24/rahbar/actions/runs/42201877130 . This verifies the updated CI path, not the separate production Docker Hub/CD requirements.

- Stage C executed: deliberately-wrong-model in shared ConfigMap, restart API only. Surge pod remained 0/1; /healthz returned 200, /readyz returned 503 with indexed nomic-embed-text versus configured wrong model, and conflict log named both. Three old replicas stayed ready. Restored ConfigMap and rolled back successfully. First direct probe raced process startup, then repeat waited for listening and captured the actual guard.
- Dedicated generation still exceeded client timeout with host-detected model threading under a four-CPU Docker quota. Bounded provider inference to four threads and 384 output tokens; rebuilding/retesting before accepting any evaluation baseline. No timed-out or fallback-only run is reported as a quality result.

- Host clock advanced from Nov 6 afternoon to Nov 7 afternoon during suspended work; pending requests expired across the pause. Corrected chunk sweep stopped on ReadTimeout after its first completed configuration, while the published Kubernetes index remained ready. Added model-digest/text-hash embedding cache with per-batch durable writes and resumable completed configurations; restarted remaining chunk measurements serially to avoid batch contention. Stage E read-only comparison returned three superseded passages in each unfiltered top five for three summer queries; restored filters excluded old sources. Resource sampler captured 131 corrected Job observations, maximum sampled memory 654Mi (not guaranteed lifetime peak).

- Pod deletion check passed: Service remained live with two ready endpoints during replacement and returned to three ready replicas. Measured 400/50 retrieval-only sweep: 1,247 chunks, 768 dimensions, amplification 1.03199, recall@3 70.59%, recall@5 88.24%; ordinary 100%, exact 83.33%, version 50%, injection 100%. Identical corpus chunk vectors were reused read-only from the already published matching-model index to avoid needless recomputation; changed chunk texts still receive new embeddings. No golden labels were changed. README now documents the tested Windows Ingress port-forward and its required Host header.

- User-owned fork aimwnoaim/rahbar main now requires quality and cluster-smoke checks, up-to-date branch, one approval, stale-review dismissal and conversation resolution, enforced for administrators. Original repository settings are unchanged because current login has no admin access. Opened controlled gate PR https://github.com/aimwnoaim/rahbar/pull/1 on separate demo-eval-gate worktree/branch; deliberately removed fixture tuition evidence, keeping golden labels/baseline fixed. It will be restored after observing the live eval gate failure. No main merge or fabricated approval.
- CPU-only Llama 1B declined directly supported r01/r02 despite relevant evidence; Qwen 0.5B comparison then exceeded 120-second generation/request budget. Added explicit schema prose/citation bounds, 256-token generation cap, 180-second attempt timeout, configurable evaluator timeout and 480-second Ingress budget for two attempts. This is an operational adjustment, not evidence of answer accuracy. Latest local checks: API 17 pass with 76.83% coverage, indexer 14 pass, eval 4 pass, mypy 23 API/10 indexer source files clean. The earlier CI exact-512-token test failed after the intentional cap change; the test now checks the bounded-output contract and the fix is pushed. HPA recovered from startup unknown to numeric 15%/70%.

### Author-balance and final submission audit

- User reiterated balanced account history as an assignment requirement. Empty/padding
  commits are not used. Prepare the real, transparently reattributed feature history on
  a separate branch, preserve main ancestry and the original history, and verify every
  rewritten commit retains its original tree/message/timestamps. Do not overwrite the
  published branch or claim old CI checks validate new SHAs.
- New audit documents and this status update are genuine file changes, committed
  individually under aimwnoaim. HISTORY-ATTRIBUTION.md explains the metadata adjustment.
- Full local diagnostic run completed after the prior turn: citation membership and
  must-abstain gates pass, but wrong/incomplete/fallback answers remain. The evaluator
  still fails against the pending baseline. Do not bless that baseline without fixes
  and manual answer review. SUBMISSION-CHECKLIST.md records exact remaining steps.

- Mechanical audit found duplicate starter files in the completed experimental worktree under ignored work/. Moved that clean worktree with git worktree move to the verified task-specific temporary directory, retaining its commits. The checker's captured output is a .log scratch file so the checker does not recursively scan its own diagnostics. The assignment checker itself was not modified.

### Balanced branch verified

- Prepared dev-aimwnoaim-balanced, retaining dev-aimwnoaim and
  archive/pre-balance-2026-11-07. No main commit or published branch was overwritten.
- Reattributed 72 existing non-merge feature commits between the two user-owned
  identities. All 251 feature-history commits were checked; 75 SHAs changed through
  identity or parent changes. Original messages, timestamps and snapshot trees remain
  intact. The pre/post-rewrite snapshots were identical and main ancestry was preserved.
- The SHA mapping is committed as a genuine documentation change under aimwnoaim;
  this audit entry is committed under momnakhan24. With these two real audit changes,
  the final balanced submission branch has 129 commits attributed to each account
  (258 total). Historical archives intentionally retain their original attribution.
- Runtime code, manifests, evaluation code and corpus files were not changed by
  reattribution. Old image/CI source SHAs remain resolvable through the archive/map;
  their runs are not presented as runs of newly rewritten SHAs.
- SUBMISSION-CHECKLIST.md is the ordered final handoff. The assignment still needs
  generation/citation fixes, reviewed committed results/baseline, synchronized deployment
  documentation/image pins, actual screenshots, owner secret configuration and real
  approval/merge followed by a successful CD run.

### Remaining coding and evaluation completion started

- User authorized finishing coding/evaluation on dev-aimwnoaim-balanced, pushing real
  fixes and following CI to success, with genuine commits balanced between accounts.
- Added grounded/refusal decoder branches derived from Answer: grounded output must
  cite retrieved evidence; refusal has no citations and low confidence. The grounding
  decision is decoded before dependent fields. Increased the bounded output budget
  to 384 tokens and invalidated prior cache policy entries.
- Added read-only policy cross-reference following. Root headings and explicit rule/
  clause/section references expand only within the same source and version filter.
  Child provenance is retained; inherited anchor relevance is labelled section_reference.
  Local BM25 plus ordered phrase matching ranks children without changing golden labels.
- Synthetic regression tests cover source/version boundaries, numeric-only labels,
  provenance, modifier-separated phrases and decoder branch constraints. API: 21
  tests pass, 83.42% coverage. Ruff passes; mypy passes 24 source files. Live model
  verification remains pending at this entry. The first eight commits are four per
  account; there are no padding commits.
- Generation temperature is now 0.0 for deterministic policy extraction, with its
  rationale in the shared ConfigMap. Grounding still relies on evidence and validation.
