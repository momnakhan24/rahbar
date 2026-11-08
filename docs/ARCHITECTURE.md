# Architecture

## Process boundaries

The query and indexing paths are intentionally separate. Three API replicas accept
questions and read the Chroma collection. The indexer Job is the only writer. The weekly
CronJob uses the same image and arguments as that Job. This prevents replicas from racing
to rebuild one collection at startup and keeps model loading out of API availability.

Chroma is a one-replica StatefulSet with a volume claim template. Its identity and data
volume survive pod recreation. Redis is a one-replica Deployment backed by a PVC for cache
state. Neither service is exposed outside the namespace; both use ClusterIP Services.
Ingress routes `/api` to the API and `/` to nginx serving the static UI.

## Stub-first deployment

The development ConfigMap starts with `RETRIEVER=stub`, `LLM_PROVIDER=stub`, and
`EMBED_MODEL=dummy-768`. The initial indexer Job runs `--dummy` and creates three passages
whose collection metadata says `embed_model=dummy-768`. This proves the cluster plumbing
without requiring an external model. The real pipeline will use the same ConfigMap pin in
both API and indexer and replace the dummy index before enabling Chroma retrieval.

## Rollouts and graceful termination

The API Deployment uses three replicas, `maxUnavailable: 0`, `maxSurge: 1`, a 35 second
termination grace period, and a short preStop drain. Readiness removes a terminating pod
from Service endpoints before its process exits. The UI can scale independently.

## Security boundaries

Each workload has a dedicated ServiceAccount with token mounting disabled. Containers run
non-root, with a read-only root filesystem, no added capabilities, and resource requests
and limits. NetworkPolicy starts with default deny; the UI cannot reach Chroma. API and
indexer can reach Chroma, API can reach Redis, and all pods can reach cluster DNS. The
default host Ollama egress rule uses `192.168.49.1/32`, the common Minikube Docker-driver
host gateway; replace it with the address reported by `minikube ssh` for the actual
cluster before relying on the policy.

## Outstanding design and evidence

The current stack is an initial stub-mode scaffold, not a completed production deployment.
Corpus delivery to the Job, atomic re-index behavior, semantic-cache invalidation, live
resource measurements, and the production provider path still need implementation and
verification. Decisions will be recorded in `docs/adr/` and summarized in `docs/WORKLOG.md`.
