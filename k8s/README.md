# RAGOps on local Kubernetes

Run these commands in Bash from the repository root. The separate profile keeps the Assignment 02 cluster available.

```bash
minikube start -p ragops-dev --driver=docker --container-runtime=containerd --cpus=6 --memory=6144 --keep-context
minikube addons enable metrics-server -p ragops-dev
docker build --build-arg GIT_COMMIT="$(git rev-parse HEAD)" -t rahbar-ragops:dev .
docker pull chromadb/chroma:1.0.12
minikube image load -p ragops-dev rahbar-ragops:dev
minikube image load -p ragops-dev chromadb/chroma:1.0.12
k=(kubectl --context ragops-dev -n ragops)
"${k[@]}" apply -f k8s/namespace.yaml
"${k[@]}" apply -f k8s/config.yaml -f k8s/pvc.yaml -f k8s/chroma.yaml -f k8s/ollama.yaml -f k8s/inbox-loader.yaml
"${k[@]}" rollout status statefulset/chroma --timeout=10m
"${k[@]}" rollout status deploy/ollama --timeout=10m
"${k[@]}" rollout status deploy/inbox-loader --timeout=5m
"${k[@]}" exec deploy/ollama -- ollama pull nomic-embed-text
"${k[@]}" exec deploy/ollama -- ollama pull qwen2.5:3b
"${k[@]}" exec deploy/ollama -- ollama list
```

Compare the embedding model ID with `EMBEDDING_VERSION` in `ragops-config` before recording evidence. Use the existing corpus download workflow, then stage Batch A. Only the ingest job and its CronJob variants invoke lake and vector writes. API pods use a read-only code path, with an explicit flag rejecting CLI writes.

If a node cannot pull Ollama, set `OLLAMA_URL` in `ragops-config` to a reachable, already-running local Ollama service with the same models. Restart live and candidate workloads if they already use the old environment. New Jobs read the updated configuration when their pods start.

If kubelet continues to report `ErrImageNeverPull` for the public Chroma image after reloading it, the demo cluster recovered with a separately built local image based on the same Chroma version. [Kubernetes pre-pulled image behavior](https://kubernetes.io/docs/concepts/containers/images/#pre-pulled-images)

```bash
printf '%s\n' 'FROM chromadb/chroma:1.0.12' 'LABEL org.opencontainers.image.title="RAHBAR Chroma local demo"' |
  docker build -t rahbar-chroma-demo:1.0.12 -
minikube image load -p ragops-dev rahbar-chroma-demo:1.0.12
"${k[@]}" set image statefulset/chroma chroma=rahbar-chroma-demo:1.0.12
"${k[@]}" delete pod chroma-0
"${k[@]}" wait --for=condition=ready pod/chroma-0 --timeout=180s
```

```bash
python scripts/stage_ragops_batch_a.py --out work/ragops/k8s-batch-a
loader=$("${k[@]}" get pod -l app.kubernetes.io/name=inbox-loader -o jsonpath='{.items[0].metadata.name}')
"${k[@]}" exec "$loader" -- mkdir -p /data/inbox
"${k[@]}" cp work/ragops/k8s-batch-a/. "$loader:/data/inbox"
"${k[@]}" apply -f k8s/ingest-job.yaml -f k8s/ingest-cronjob.yaml
"${k[@]}" wait --for=condition=complete job/ingest --timeout=40m
"${k[@]}" logs job/ingest
"${k[@]}" exec deploy/inbox-loader -- ls /data/results
"${k[@]}" apply -f k8s/api.yaml -f k8s/candidate.yaml
"${k[@]}" rollout status deploy/api --timeout=5m
"${k[@]}" create job candidate-index --from=cronjob/ingest --dry-run=client -o json |
  python -c 'import json,sys; j=json.load(sys.stdin); c=j["spec"]["template"]["spec"]["containers"][0]; c["command"]=["python","-m","ragops","--data","/data","sync"]; c["args"]=[]; next(v for v in c["env"] if v["name"]=="CHROMA_COLLECTION")["value"]="rahbar_v3_nomic"; c["env"].append({"name":"CHUNK_SIZE","value":"420"}); print(json.dumps(j))' |
  "${k[@]}" apply -f -
"${k[@]}" wait --for=condition=complete job/candidate-index --timeout=25m
"${k[@]}" rollout status deploy/candidate --timeout=5m
```

## Gate, rollout and rollback

Measure the baseline against the running API. Save the resulting path as `baseline.json` on the same PVC. The image records the commit SHA supplied at build time.

```bash
commit=$(git rev-parse HEAD)
"${k[@]}" exec deploy/api -- sh -c 'GIT_COMMIT="$1" python -m ragops eval --target-url http://api:8000 --collection rahbar_v1_nomic --out /data/results --label baseline' sh "$commit"
"${k[@]}" exec deploy/inbox-loader -- sh -c 'cp "$(ls -t /data/results/eval_*_baseline.json | head -1)" /data/results/baseline.json'
"${k[@]}" apply -f k8s/eval-job.yaml
"${k[@]}" logs -f job/eval
"${k[@]}" get job eval
```

Change a gate limit with `"${k[@]}" edit configmap gate-config`. Delete the eval Job and rerun the preceding creation command. Collect both gate outcomes before changing the live Deployment. The measured release decision belongs in the report.

To isolate a threshold change, run the same Job with `EVALUATED_CANDIDATE_PATH` set to the measured candidate JSON under `/data/results`. With that variable unset, the Job evaluates the candidate before applying the gate.

```bash
"${k[@]}" annotate deploy/api kubernetes.io/change-cause='candidate passed offline gate' --overwrite
"${k[@]}" set env deploy/api CHROMA_COLLECTION=rahbar_v3_nomic CHUNK_SIZE=420
"${k[@]}" rollout status deploy/api
"${k[@]}" rollout history deploy/api
"${k[@]}" annotate deploy/api kubernetes.io/change-cause='controlled top-k regression demo' --overwrite
"${k[@]}" set env deploy/api CHROMA_COLLECTION=rahbar_v1_nomic CHUNK_SIZE=400 TOP_K=1
"${k[@]}" rollout status deploy/api
"${k[@]}" rollout undo deploy/api
"${k[@]}" rollout status deploy/api
"${k[@]}" logs deploy/api --tail=10
"${k[@]}" port-forward svc/api 8000:8000
```

From another terminal, submit a query and inspect the trace and metrics. Run `bash scripts/demo.sh` after the candidate gate succeeds to replay evaluation, trace reconstruction and unseen-batch admission. The script stops if evaluation fails.

After a permanent approved release, align the scheduled writer with the live collection using `"${k[@]}" set env cronjob/ingest CHROMA_COLLECTION=rahbar_v3_nomic CHUNK_SIZE=420`.

```bash
curl -fsS http://127.0.0.1:8000/metrics
curl -fsS -X POST http://127.0.0.1:8000/query -H 'Content-Type: application/json' \
  -d '{"question":"How long may I borrow a recorder?"}'
"${k[@]}" exec deploy/api -- python -m ragops trace TRACE_ID
"${k[@]}" exec deploy/api -- python -m ragops metrics --since 24h
"${k[@]}" delete pod chroma-0
"${k[@]}" rollout status statefulset/chroma --timeout=10m
"${k[@]}" top pods
```

Check retrieval again after the restart. Record actual API, Chroma and Job resource usage in `eval/results/resources_*.txt`. The tracked requests include headroom above the measured fixture workload. Measure a sustained workload with the full corpus before generalizing the sizing.
