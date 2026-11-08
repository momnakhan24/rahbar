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
that must not be multiplied by each API restart. A subsequent sole-writer HTML refresh retained 1,232 PDF vectors and atomically published 1,239 total chunks in 22 seconds; this was not another full OCR run.

## 2. Swapping readiness and liveness during 90 seconds of slow Chroma

`api/app/routes/health.py:21` returns process liveness without dependencies; line 27
checks collection/count/model and Redis for readiness. Probes are at
`k8s/base/api.yaml:45`, 51 and 58. Swapping them would leave broken readers in the
Service while dependency slowness triggers repeated restarts of all three healthy
processes. The 10-second liveness period and three-failure budget can restart them
within that 90-second outage. Correct readiness withdraws traffic without restarting
processes; `maxUnavailable: 0` at line 12 protects existing ready replicas on rollout.

## 3. What CPU HPA measures

`k8s/base/hpa.yaml:11`–19 sets 3–8 replicas and 70% CPU/request utilization. With each
API requesting 100m CPU (`k8s/base/api.yaml:71`), 70m average use reaches its target.
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
Chroma reached 894Mi and was actually OOMKilled under 1Gi: its new 1Gi request/2Gi
limit is supported by observed near-1Gi use and leaves write/query headroom; the
request covers that observed peak. Redis observed 62–87m/4–8Mi versus request 100m/96Mi,
limit 300m/256Mi; its CPU request covers these samples and needs remeasurement under
larger traffic. UI observed 1m/3–4Mi versus 25m/32Mi request, 200m/96Mi limit;
these small absolute reservations leave startup/burst margin but are not utilization
optima. These are assignment-scale budgets, not proof of production capacity.

The initial 4Gi Docker node reached 3.96Gi and Kubernetes API TLS handshakes stalled.
Increasing its budget to 6Gi/six CPUs recovered control-plane access. Ollama runs
outside that node, so its memory/CPU is an additional host cost, not included in
`kubectl top` for API/indexer.

## 5. Recall by question type

The cleaned-corpus dense-only 400/50 experiment measured recall@5 88.24%:
ordinary 100%, exact 83.33%, version 50%, injection 100%
(`evidence/chunk-sweep.json`). Version questions were worst: excluding obsolete
material cannot make the right current clause rank first. Semantic similarity blurs
literal identifiers and can favor a general summer heading over its restriction.
The final query path therefore follows explicit numbered references, ranks linked
children using BM25/ordered phrases, focuses requested clauses and resolves unique
named pages. It retains both match relevance and original dense cosine rather than
presenting an exact-source match as a cosine of one. The complete live API metrics
are in eval/results.json; generation relevance/correctness is reviewed separately
in evidence/generation-review.md. Dense-only tuning scores and final query-path
scores measure different retrieval methods and must not be conflated.

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



## Final serving behavior and limitations

The provider first selects a bounded verbatim excerpt, then generates the shared
Answer contract constrained to that exact quote and original citation. The server
checks that pair independently. This avoids the observed small-model combination
of a correct fact and an unrelated citation. Qwen 2.5 3B remains CPU-bound and the
two model calls can make cold/long answers take minutes; this is measured assignment
behavior, not production latency. Exact repeats use the revision/policy-scoped cache.
The 0.70 floor conservatively refuses an injected but answerable attendance query;
the generation review labels that false abstention explicitly.

A real configuration rollout interrupted an in-flight long request because the
35-second termination grace was shorter than generation. API grace and Ingress
read/send timeouts now allow 900 seconds, covering two bounded model calls per
attempt and one retry plus embedding overhead. The existing five-second preStop
allows endpoint withdrawal; maxUnavailable remains zero. Request draining is verified
separately from merely counting three ready replicas. Long grace does not make a
forced kill or node loss preserve an in-memory request; clients still need retries
for those failures, and old ready replicas alone do not prove in-flight safety.

Final live API recall@3/5 is 100% across the 17 labelled retrieval questions, with
100% in every reported type. This follows explicit-reference/source improvements;
it does not retroactively change the dense-only 88.24% tuning measurement. Grounded
citation membership is 16/16 and required abstention 2/2. One answerable injection
question safely refuses; semantic correctness is therefore not claimed as 100%.
The measured mixed run's median request was 39.03s and maximum 216.31s; these CPU
latencies explain why short drain budgets and repeated cold evaluation are expensive.

The final drain probe returned HTTP 200 after 72.34 seconds while its serving pod
was gracefully deleted, with X-Cache MISS and three replacement pods ready afterward
(`evidence/request-drain.json`). This exceeds the old 35-second budget and directly
checks in-flight completion. It does not claim survival of forced kill/node loss or
full semantic coverage of the probe's compound question.
