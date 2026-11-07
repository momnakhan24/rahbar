# Final submission checklist

Audited 7 November 2026. Deadline: **8 November 2026, 23:59 PKT**.
The implementation and reviewed real evaluation are complete locally. Repository
settings, real review/merge, hosted CD and required screenshots still need human
completion. Exact instructions are in [OWNER-STEPS](OWNER-STEPS.md).

## Completed implementation and observed evidence

- [x] Corpus: nine public documents, 279 PDF pages, verified SHA manifest/fetcher;
  raw university files ignored. CORPUS documents all seven properties, the genuine
  2023/2026 pair, scanned text, meaningful tables, long definitions, absent hostel
  topic and exact terms. OCR ran on 41 pages with representative visual review.
- [x] Indexing: extract/OCR → clean → structured overlapping chunks → pinned
  embeddings → versioned atomic Chroma publication. Only Job/CronJob write; API
  startup never indexes. Required metadata and readiness model guard are present.
- [x] Chunk measurements: three real configurations on unchanged gold; cleaned
  400/50 ships 1,239 chunks, dense-only recall@5 88.24%. Word amplification and
  rejected alternatives are recorded. No fixture numbers substitute for real data.
- [x] Cache: actual threshold sweep, selected 0.96 with zero measured false hits;
  follow-up/refusal bypass, revision invalidation and generation policy versioning.
- [x] Generation: Qwen 2.5 3B locally, temperature zero, bounded excerpt selection,
  shared Answer decoder/Pydantic validation, exact quote/citation pairing, one retry
  then safe fallback. Actual indexed poison test resists the planted instruction.
- [x] Kubernetes: namespace, three API replicas, UI, Chroma StatefulSet/PVC, Redis
  PVC, four ClusterIP Services, Ingress, Job/weekly CronJob, ConfigMap, deny/allow
  Calico policies, three probes, 3–8 HPA, resources and hardened container contexts.
  Runtime evidence includes three endpoints, numeric HPA, resources, allow/deny,
  replacement, visible rollout/undo and completed real index Jobs.
- [x] Deployment: all three published SHA images pinned, actual registry manifests
  recorded, real local runtime synchronized. Hardened corpus loader permissions and
  generated clean-clone overlay validated. Corpus copy precedes the first index Job.
- [x] Evaluation: all 19 unchanged questions executed, every answer reviewed.
  Recall@3/5 100%; citation membership 16/16; required abstention 2/2.
  Results and reviewed baseline are real measurements. Literal terms 16/17; the
  answerable injection false abstention is disclosed, not counted as perfect accuracy.
- [x] Regression gates: live fixture CI checks recall drop, citation validity and
  required refusals. Committed-real-result integrity check recalculates recorded
  response metrics. Reviewed baseline is separate from the fixture baseline.
- [x] Four deliberate failures A/B/C/E recorded with symptoms, diagnosis, remedy,
  logs/metrics. Controlled tuition-evidence removal made fixture recall 1.0→0.8 and
  blocked the gate; restoration passed. Historical screenshots are not fabricated.
- [x] CI/CD code: least privilege, reusable full CI prerequisite, needs on publishing
  and deployment, scanned SHA images, explicit registry preflight, serialized CD,
  bounded jobs, Ingress/admission waits, JSON smoke assertions and artifacts.
- [x] Local checks: API 31 tests / 83.71% coverage; indexer 16 tests; evaluator four
  tests; Ruff/mypy pass; strict production render validates all 28 objects;
  actionlint/shellcheck pass. Checker: 166 passes, zero failures, one reviewed warning
  for the empty Secret template in history.
- [x] Engineering notes answer all seven questions with implementation references
  and actual measurements. AI-USAGE and HISTORY-ATTRIBUTION disclose assistance
  and author metadata. All new commits/pushes use aimwnoaim on dev, one file/change
  per commit. Main was not directly pushed.

## Final branch checks

The current exact-head quality and cluster-smoke checks are at
[PR #5](https://github.com/momnakhan24/rahbar/pull/5/checks). The final handoff and PR
summary identify the verified successful run after pushing all intended files.
Earlier source passed runs 42385009754 and 42385002481; those earlier links do not
verify later evidence/documentation commits. Require both final checks before merge,
and confirm a clean working tree with every intended commit pushed.

## Remaining owner / submission actions

- [ ] Add DOCKERHUB_TOKEN and DOCKERHUB_USERNAME=aimwnoaim to the original repo.
  Docker CLI login and sending a token to someone do not create an Actions secret.
- [ ] Owner verifies main requires PR, up-to-date quality/cluster-smoke and one
  genuine approval. Obtain that review; merge the final PR through GitHub.
- [ ] Capture actual UI/citation/refusal, branch-protection and failed/green merge
  screenshots. Recorded text/JSON evidence does not replace requested screenshots.
- [ ] Verify the complete hosted CD run succeeds (test → build-push → deploy),
  including any production-environment approval. Local registry pushes and local
  acceptance tests are not a successful hosted CD run.
- [ ] Submit repository URL, successful CD URL, that run's SHA image links, and
  committed eval/results.json plus eval/baseline.json to Classroom before deadline.

No credential was exported from Docker Desktop to GitHub. The connected account
has push access but no administration permission. These external steps cannot be
replaced by a code change, fabricated approval, screenshot or claimed CD success.
