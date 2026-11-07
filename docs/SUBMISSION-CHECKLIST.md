# Final submission checklist

Audited 7 November 2026, approximately 15:05 PKT. Deadline: 8 November 2026,
23:59 PKT. This is a status checklist, not a declaration that the assignment is done.

## Verified work

- [x] Nine public corpus sources, 279 PDF pages, URLs/checksums and a fetcher; raw
  source documents are ignored. Genuine 2023/2026 policy differences were reviewed.
- [x] OCR executed on 41 pages, representative scan review and table before/after
  evidence recorded. Known OCR/HTML-cleaning limitations are disclosed.
- [x] Separate indexing Job/CronJob, versioned atomic Chroma publication, required
  metadata and shared embedding pin; API does not index on startup.
- [x] Three real chunk measurements: recall@5 82.35%, 88.24%, 88.24%; shipped 400/50.
- [x] Cache threshold measurements, revision invalidation and regression coverage
  for changed relevance floor/generation settings.
- [x] Four deliberate failures A/B/C/E with actual evidence and diagnosis.
- [x] Local Docker/Minikube with Calico, three ready API endpoints, numeric HPA,
  resource samples, network allow/deny, pod replacement and visible rollout/undo.
- [x] Served UI at http://localhost:18080; file-open guidance and duplicate-submit
  guard verified. Direct HTML files are not a running API service.
- [x] API 18 tests / 77.10% coverage, indexer 14 tests, evaluator four tests; Ruff
  and mypy passed in the recorded checks.
- [x] CI passed on source `9940eec` in runs 42360957317 and 42361063605.
  This does not verify later local commits or rewritten history.
- [x] Deliberate fixture regression caused recall to fall from 1.0 to 0.8 and CI
  blocked it. Restoring tuition evidence made the fork demonstration PR green.
- [x] Docker Hub API/UI/indexer images were published with immutable source tags
  `02246e5...` and later `bf3edf775c9d847188ca18e14aa251776c25273f`.
- [x] Original repository main reports protected. PR #3 exists as a draft and
  requires genuine review. No main merge or approval has been fabricated.

## Remaining work, in order

### 1. Finish generation correctness — coding is still required

The full 19-question diagnostic run completed in `work/real-eval-reviewed.json`:
recall@3 70.59%, recall@5 88.24%, citation membership 100% (10/10), and required
abstention 100% (2/2). Literal expected-term accuracy was only 35.29% (6/17).
Literal matching is not a complete correctness assessment; the raw responses also
show real problems and must be reviewed individually.

- A direct provider probe returned a supported CGPA answer with
  `answered_from_context=true` and `citations=[]`. The server correctly rejects it,
  but repeating the same generation can still end in a user-visible fallback.
  Strengthen the generation schema in `api/app/providers/llm/ollama.py` so the
  grounded branch requires at least one retrieved citation and the refusal branch
  has no citations. Preserve the independent server-side membership validation.
- Review r12: the current-version summer-elective question received a prerequisite
  answer. Inspect its retrieved text/source/section, correct retrieval/grounding,
  and rerun the unchanged golden question. Do not relabel gold to fit retrieval.
- Review fallbacks, incomplete answers and policy negation, including summer
  financial aid. Fix the actual defect, not just the literal-match diagnostic.
- Invalidate old generation results after a prompt/schema-policy change: update
  the cache policy version/fingerprint so old answers cannot mask the fix.
- Rerun API tests, coverage, Ruff/mypy and the actual indexed poisoned-fixture test.
  The saved small-model fixture response "Yes" is not proof of answer correctness.

### 2. Produce reviewed submission evaluation files

`eval/results.json` is still missing; `eval/baseline.json` is still an explicit
pending marker. The diagnostic output in ignored `work/` is not the submission.

With the local Ingress port-forward running:

```powershell
.venv\Scripts\python -u eval/run_eval.py --api http://localhost:18080 --timeout 480 --golden eval/golden.yaml --out eval/results.json --responses-out docs/evidence/submission-responses.json
```

Review every answer for correctness, relevant citations, actual question coverage,
unsupported claims and appropriate refusal. Only after that review, run the same
command with `--update-baseline`, then rerun without that flag to demonstrate the
gate passing against the committed baseline. Commit each resulting file separately.
Keep the real baseline separate from `eval/fixtures/baseline.fixture.json`.

### 3. Synchronize deployment and reproduction instructions

- Update local API/UI pins: the committed local overlay still points to older
  images than the corrected live deployment. Use verified published source-SHA
  tags or build/load the exact source before pinning it.
- Replace production `DOCKERHUB_USERNAME` / `REPLACE_WITH_GIT_SHA` placeholders
  before deployment; do not deploy `latest` or invent an unbuilt SHA tag.
- Update README's 17-question reference to 19, remove obsolete hosts-file-only
  instructions, and document the chosen local generator/floor and corpus-copy order.
- Verify clean-clone instructions: fetch/verify corpus, create namespace/PVC,
  copy corpus with the loader, delete the loader, then start exactly one real
  indexer Job. Do not leave two simultaneous indexing writers running.
- Record the final running image names/digests and final model digest. Original
  pre-reattribution source SHAs remain valid provenance via the archived history.

### 4. Finish evidence and documentation

- Commit final, reviewed runtime/evaluation evidence. Label preliminary files as
  preliminary; do not commit every interrupted run as the final result.
- Capture actual UI and required blocked/green PR screenshots. JSON API evidence
  is useful but does not substitute for screenshots requested by the handout.
  Windows computer use stopped because it could not verify Chrome's URL; no
  screenshots from that failed inspection are claimed.
- Refresh PIPELINE, ENGINEERING-NOTES, AI-USAGE and WORKLOG summaries so they
  agree with final generation results, image pins and measured resource values.

### 5. Publish the chosen real, balanced history and verify its CI

The separate balanced branch preserves real file changes and openly records author
reattribution in HISTORY-ATTRIBUTION.md. The original branch/archive are retained.
Choose whether to submit through a new PR or explicitly authorize replacing the old
PR branch. Replacing it needs a history rewrite/force-with-lease; it is not done
silently. Newly rewritten SHAs require fresh CI even if file contents are identical.

After publishing the chosen branch, require both `quality` and `cluster-smoke` to
pass on its exact final HEAD. Existing green runs cover the older source only.

### 6. Repository owner: secret, real review and CD

At the audit, `momnakhan24/rahbar` listed no repository Actions secrets. Sending a
token to the owner is not the same as saving it in GitHub.

1. Owner opens Settings → Secrets and variables → Actions.
2. Add repository secret `DOCKERHUB_TOKEN` with the supplied Docker Hub Read & Write
   token; add Actions variable `DOCKERHUB_USERNAME=aimwnoaim`.
3. Verify main requires a PR, `quality`, `cluster-smoke`, up-to-date checks and one
   genuine approval. A protected flag alone does not prove every required setting.
4. Once final code/evaluation/CI are reviewed, mark the correct PR ready, obtain a
   real approval and merge through GitHub. Do not push directly to main.
5. Verify CD `test → build-push → deploy` succeeds, including scans, SHA-tagged
   Docker Hub publication, rollout and Ingress smoke test. Save its successful URL.

The user declined agent-mediated credential export. Do not copy credentials to a
fork or another destination as a workaround. No successful CD run is verified yet.

### 7. Final mechanical check and Classroom submission

```powershell
.venv\Scripts\python scripts/check_submission.py
git status --short
```

Resolve every failure and review every warning; the checker is not the grader.
Ensure all intended deliverables are committed on the submitted branch and pushed.
Understand and be able to explain the AI-assisted implementation.

Submit these four required items to Classroom before the deadline:

- [ ] Accessible GitHub repository URL and the final reviewed branch/PR history.
- [ ] Successful `cd.yml` run URL.
- [ ] Docker Hub image links showing the SHA tags from that run.
- [ ] Committed `eval/results.json` and `eval/baseline.json`.
