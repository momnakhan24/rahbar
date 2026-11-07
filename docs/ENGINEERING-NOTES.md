# Engineering notes

These answers refer to implementation lines and actual local Docker/Minikube evidence.
Source line numbers refer to this revision and can move in later commits.

## 1. Three readers, one writer

Moving indexing into three API startups would run three OCR/embedding/publication jobs
concurrently and repeat that work on every restart. Readers could observe incompatible
or partially built generations. `k8s/base/indexer-job.yaml:2` makes indexing a Job,
with retry budget at line 7; `indexer/pipeline/run.py:66` owns the five stages.
`indexer/pipeline/store.py:76` switches the registry only after all chunks are stored.
API startup creates serving clients, never invokes that pipeline. The actual Job
published 1,247 chunks in 1,736.7 seconds (`evidence/indexer-completed.txt`), a cost
that must not be multiplied by each API restart.

## 2. Swapping readiness and liveness during 90 seconds of slow Chroma

`api/app/routes/health.py:21` returns process liveness without dependencies; line 27
checks collection/count/model and Redis for readiness. Probes are at
`k8s/base/api.yaml:43`, 49 and 56. Swapping them would leave broken readers in the
Service while dependency slowness triggers repeated restarts of all three healthy
processes. The 20-second liveness period and three-failure budget can restart them
within that 90-second outage. Correct readiness withdraws traffic without restarting
processes; `maxUnavailable: 0` at line 12 protects existing ready replicas on rollout.

## 3. What CPU HPA measures

`k8s/base/hpa.yaml:11`–19 sets 3–8 replicas and 70% CPU/request utilization. With each
API requesting 100m CPU (`k8s/base/api.yaml:69`), 70m average use reaches its target.
Actual HPA output showed 41%/70%, three replicas (`evidence/hpa.txt`). It measures
Python/client/JSON/retrieval work, not the external Ollama CPU doing generation. API
pods can wait on an overloaded model while barely using CPU, so this HPA can miss
long queues. Scale serving capacity using pending requests, in-flight generation and
latency/saturation, exposing metrics to Prometheus plus an external/custom-metrics
adapter and a bounded work queue. More API replicas alone do not add Ollama capacity.

## 4. Measured resources and margins

The corrected index Job was sampled 131 times at approximately ten-second intervals:
maximum observed CPU 1,843m and memory 654Mi (`evidence/indexer-resources-corrected.txt`).
This is a sampled maximum, not a guaranteed lifetime peak. Job/CronJob now request one
CPU/768Mi and limit two CPUs/2Gi (`k8s/base/indexer-job.yaml:31`–35). The memory limit
is 1,394Mi above the sample, about 3.13 times observed use. The request covers the
sample; OCR CPU can burst close to two cores, then falls near idle while external
embeddings compute. Crossing memory limit gives OOMKilled/exit 137, not CPU throttling.

Other container budgets are tied to `evidence/kubectl-top.txt` and subsequent work-log
samples: API startup reached 549m/66Mi; one CPU request of 100m supports mostly I/O-bound
steady work, with a 750m limit for startup bursts and 768Mi memory ceiling. New pods
were around 68–126Mi after transport reuse; the 256Mi memory request covers those
observations. The old probe implementation grew toward 511Mi, so it was corrected.
Chroma reached 894Mi and was actually OOMKilled under 1Gi: its new 768Mi request/2Gi
limit is supported by observed near-1Gi use and leaves write/query headroom, though the
request remains below that peak. Redis observed 62–87m/4–8Mi versus request 50m/96Mi,
limit 300m/256Mi; its CPU request is below sustained samples and should be revisited
for larger traffic. UI observed 1m/3–4Mi versus 25m/32Mi request, 200m/96Mi limit;
these small absolute reservations leave startup/burst margin but are not utilization
optima. These are assignment-scale budgets, not proof of production capacity.

The initial 4Gi Docker node reached 3.96Gi and Kubernetes API TLS handshakes stalled.
Increasing its budget to 6Gi/six CPUs recovered control-plane access. Ollama runs
outside that node, so its memory/CPU is an additional host cost, not included in
`kubectl top` for API/indexer.

## 5. Recall by question type

The first completed exact-cosine chunk experiment (250/30) measured overall recall@5
82.35%: ordinary 100%, exact 83.33%, version 0%, injection 100%. The source filter
excluded old material but could not guarantee that the right current clause ranked
highly. Version wording can favor general handbook context rather than the particular
summer clause. Dense similarity also blurs literal identifiers/years. Hybrid lexical
retrieval (BM25 plus dense ranking), exact clause lookup and reranking are appropriate
next techniques. These first-run figures are retrieval-only; the remaining chunk sweep
and live API evaluation must be reported separately before selecting shipped parameters.

## 6. Model pin changed on API alone

`api/app/routes/health.py:61` logs indexed/configured conflicts and readiness returns
503. The actual fault produced a new 0/1 pod, liveness 200 and readiness 503 naming
`nomic-embed-text` versus `deliberately-wrong-model`, with collection count 1,247.
Three old replicas stayed ready; restore/rollback succeeded. See
`evidence/failure-c-model-mismatch.txt`. Without this guard, equal-dimensional vectors
from different models could pass dimension checks yet silently return meaningless
neighbors; a different dimension could instead raise an error. The shared ConfigMap
and stored model/dimension metadata enforce the contract.

## 7. The failure that consumed more than an hour

Bootstrapping the real local pipeline involved interrupted binary/package downloads,
then apparent Kubernetes connectivity/readiness trouble. Retrying connectivity alone
did not resolve resource pressure. The decisive observations were `docker stats
--no-stream rahbar` showing 3.96Gi/4Gi, API TLS handshake timeouts, then
`kubectl --context rahbar get pod chroma-0 -n rahbar -o jsonpath=...` reporting
`reason: OOMKilled`, `exitCode: 137`. Increasing only the rahbar node budget to 6Gi
restored API responsiveness; raising Chroma to 2Gi stopped its immediate OOM loop.
Official bootstrap binaries were SHA-256 verified after Docker downloads succeeded
where host transfers stalled. The lesson is to inspect node/container resources and
last termination state before interpreting every timeout as an application bug.
A later host suspension interrupted measurements; resumable vector batches now avoid
throwing away all completed experiment work. WORKLOG preserves the uncertainty and
failed attempts rather than retroactively claiming every first diagnosis was correct.
