# Screenshots to capture on your cluster

Use Bash from the repository root. Follow [Kubernetes setup](../k8s/README.md), then run `k=(kubectl --context ragops-dev -n ragops)` in the screenshot terminal. Set paths and trace IDs from actual runs.

| ID | Capture | Command |
| --- | --- | --- |
| A1 | Verification decisions and quarantine reasons | `cat eval/results/verification_report_<run>.md` and `python -m json.tool eval/results/verification_report_<run>.json` |
| A2 | Fresh and unchanged counts | `cat eval/results/incremental_<run>.json` for each run |
| A-delete | Deleted-document count and orphan scan | `cat eval/results/incremental_<deletion_run>.json` |
| A-restore | Old version restored and retrievable | `python -m ragops --data /data restore equipment-loan 2026-01` from an ingest Job, then query the live Service |
| B-module | Cosine and deterministic embedding metrics | `python -c 'import json,sys; print(json.load(open(sys.argv[1]))["module"][0])' "$baseline"` |
| B-component | Retrieval metrics and noise deltas | `cat "${baseline%.json}.md"` |
| B-e2e | Faithfulness, correctness, abstention and stage latency | `cat "${baseline%.json}.md"` |
| B-repeat | Seeded run differences | `cat "${baseline%.json}.md"` |
| C-compare | Baseline and candidate | `cat "${baseline%.json}.md" "${candidate%.json}.md"` |
| C-gate | Pass and deliberate failure | `python -m ragops gate --baseline "$baseline" --candidate "$candidate" --config config/gate.yaml` and repeat with the bad candidate |
| D-trace | Trace details and prompt hash | `"${k[@]}" exec deploy/api -- python -m ragops trace "$trace_id"` |
| D-metrics | Similarity histogram, stage p95 and cache rate | `curl -fsS http://127.0.0.1:8000/metrics` |
| D-rail | Retrieval injection dropped | `"${k[@]}" logs deploy/api --tail=20` after the yellow-locker question |
| E-coverage | Coverage before and after, with exit codes | `python -m ragops coverage --live eval/live_queries.jsonl --golden "$golden" --threshold "$threshold"; echo "$?"` for each set |
| E-drift | Before/after Batch B metrics and updated fact | `cat "${baseline%.json}.md" "${after%.json}.md"` |
| F-inventory | Pods, services, PVCs, Jobs, CronJob and ConfigMaps | `"${k[@]}" get all,pvc,configmap` |
| F-persistence | Chroma restarts and retrieves the same fact | `"${k[@]}" delete pod chroma-0`, `"${k[@]}" rollout status statefulset/chroma`, then repeat the query |
| F-eval | Eval Job logs and terminal status | `"${k[@]}" logs job/eval; "${k[@]}" get job eval` |
| F-config | Gate ConfigMap before and after the edit | `"${k[@]}" get cm gate-config -o yaml`; recreate the Job and capture its result |
| F-rollout | Controlled release and rollback | `"${k[@]}" rollout history deploy/api; "${k[@]}" rollout status deploy/api; "${k[@]}" rollout undo deploy/api` |
| F-rollback-trace | Collection and embedding version after undo | Repeat the query, then use `"${k[@]}" logs deploy/api --tail=10` |
| F-stdout | Trace visible in deployment log | `"${k[@]}" logs deploy/api --tail=10` |
| F-read-only | API pod rejects a write command | `"${k[@]}" exec deploy/api -- python -m ragops sync` |
| F-resources | Live resource measurements | `"${k[@]}" top pods` during ingestion and evaluation |
| F-unseen | Verification and increment from a new inbox batch | `bash scripts/demo.sh` |
