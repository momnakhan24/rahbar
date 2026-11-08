# Runtime and evidence capture runbook

Use this after a Kubernetes cluster and GitHub repository settings are available. Save only real command output and screenshots under `docs/evidence/`; label timestamps, commit SHA, cluster version and image tags. Never place tokens, private keys, kubeconfigs or student information in evidence. No evidence below has been collected yet in this local-only workspace.

## Cluster setup and smoke checks

From the repository root in WSL/Bash:

```bash
make cluster
make images TAG=dev
kubectl apply -k k8s/overlays/dev
kubectl rollout status statefulset/chroma -n rahbar --timeout=5m
kubectl rollout status deployment/redis -n rahbar --timeout=3m
kubectl wait --for=condition=complete job/indexer -n rahbar --timeout=5m
kubectl rollout status deployment/api -n rahbar --timeout=5m
kubectl rollout status deployment/ui -n rahbar --timeout=3m
kubectl get pods,services,endpoints -n rahbar -o wide
kubectl get hpa -n rahbar
kubectl top pods -n rahbar --containers
```

Capture sanitized outputs as `docs/evidence/endpoints.txt`, `docs/evidence/hpa.txt`, and `docs/evidence/resources.txt`. Record the node and pod requests/limits beside the `kubectl top` sample; one snapshot is not a load test. Capture the dashboard/browser view as `docs/evidence/ui.png` if the assignment requests a screenshot.

## Readiness, rollout and policy evidence

- Query `/healthz` and `/readyz` while dependencies are healthy; record status codes and response bodies.
- In an isolated test namespace/branch, temporarily mismatch the API `EMBED_MODEL`, roll out, record `/readyz` 503 plus the model-conflict log, then restore and verify recovery.
- Apply an image update tagged with a test SHA. Record rollout status and pod availability; run `kubectl rollout undo deployment/api -n rahbar` and record recovery. Do not use mutable `latest` tags.
- From an authorized test pod, verify the allowed API→Chroma/Redis and indexer→Chroma/Redis/Ollama connections, plus a denied path. Capture NetworkPolicy and probe output.

## Deliberate failure experiments

Follow [`FAILURE-ANALYSIS.md`](FAILURE-ANALYSIS.md) one case at a time. Use a disposable fixture/index and restore the original manifests before moving to another stage. For each case, record the exact fault, timestamp, request/job ID, diagnostic command, observed symptom, remedy and recovery check. Do not insert real secrets in prompt-injection tests or use production documents for destructive experiments.

## GitHub branch protection and CI/CD

In GitHub repository settings, protect `main` and require `CI / quality` and `CI / cluster-smoke` before merge. Require a pull request and at least one approval if the account supports it. To prove the gate, open a disposable test PR with a failing check, capture the blocked merge state in `docs/evidence/blocked-merge.png`, then fix the check and close or merge the test PR according to team policy. Do not claim a blocked merge from a settings screenshot alone.

Configure the protected `production` environment, reviewers, image repository variables and `KUBECONFIG_B64` secret as listed in the README. Verify CD only with a published immutable SHA-tagged image and a non-production/test cluster first. Store the successful workflow summary and rollout output as `docs/evidence/deploy.txt`; redact cluster endpoints and credentials where needed.

## Final evidence review

Before submission, ensure every evidence file is dated and attributable to the commit/image it describes. Distinguish unit tests, rendered manifests, CI results and live cluster observations. Update `docs/WORKLOG.md` with actual outcomes and remaining failures; never replace `eval/baseline.json`'s pending marker until a reviewed real-corpus evaluation has produced measured values.
