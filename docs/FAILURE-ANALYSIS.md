# Controlled failure analysis

Experiments use the downloaded public corpus and local Docker/Minikube profile
`rahbar`. Each fault is isolated; raw evidence names the actual method. Retrieval-only
experiments do not establish LLM answer correctness.

## A · extraction without OCR (completed)

Disabled OCR for the real eight-page image-only entrepreneurship policy. Extracted text
was zero characters and chunk count zero; empty index publication was refused. Corrected
Tesseract extraction yields 1,814 words. Evidence: `evidence/failure-a-no-ocr.json`.

Without knowing the injected fault, compare document/page inventory to emitted chunk
counts, inspect text-layer length and page fonts, then rasterize a page. Zero extraction
before embedding identifies stage A. Remedy: OCR sparse pages, preserve boundaries and
review representative scans. Default OCR detached clause numbers on reviewed policy
page 2; single-block `--psm 6` improved that association. This was a Docker pipeline
probe, not a claim of a failed Kubernetes Job.

## B · fixed 100-word chunks with no overlap (running)

`scripts/measure_fixed_chunks.py` replaces structure-aware windows with fixed 100-word
windows and no overlap, using the same verified extraction, model and golden labels.
Whitespace words are the pipeline's documented token approximation. Metadata comes
from the section at the beginning of each window; it is not deliberately deleted.
The experiment writes `evidence/failure-b-fixed-chunks.json`; no metric is claimed until
it finishes. Compare recall@3/@5 and individual misses with the normal chunk sweep.

Without knowing the fault, inspect the retrieved IDs/sections and text at chunk ends,
then compare exact/definition recall. A policy split across adjacent windows suggests
stage B even when extraction contains the full text. Remedy: restore section/paragraph/
sentence-aware chunks and measured overlap; reindex and invalidate revision cache.

## C · API-only model mismatch (completed)

Changed ConfigMap EMBED_MODEL to `deliberately-wrong-model`, restarted only API and
left the published nomic index intact. The surge pod stayed 0/1. `/healthz` returned
200; `/readyz` returned 503 with indexed `nomic-embed-text`, configured wrong model,
and count 1,247. JSON logs named the conflict. Three original replicas stayed ready.
Restored the ConfigMap and rolled back; rollout succeeded. Evidence:
`evidence/failure-c-model-mismatch.txt`. An initial direct probe raced process startup;
the preserved repeat waited for listening and captured the actual guard.

Without knowing the fault, inspect status, readiness response and the conflict log
before changing retrieval or prompts. The 503/model pair identifies stage C/configuration,
not model hallucination. Remedy: restore the shared pin, or complete a new matching
index before admitting new-model readers. Liveness must remain dependency-independent.

## E · obsolete source filter removed (completed)

Read-only queries against the same active collection compared no metadata filter with
`superseded=false`. For each of three summer-policy questions, the unfiltered top five
contained three superseded passages; the restored query excluded obsolete sources.
Raw text, versions, scores and IDs: `evidence/failure-e-source-filter.json`.

The real policy difference is optional 8–9-week summer and elective exceptions in 2023
versus current 8-week, repeat-only provisions in clauses 6.1–6.2. These differences were
verified from source before retrieval tuning. This experiment demonstrates obsolete
context exposure; it does not claim that an LLM generated a particular wrong sentence.

Without knowing the fault, inspect retrieved source/version/superseded metadata and
compare current-version recall. High similarity to an old rule is a source-selection
failure, not proof that the generator invented it. Remedy: restore metadata filtering
and permit historical material only for an explicit historical question. A prompt alone
cannot remove obsolete candidates from the retrieved evidence.

## Operational incidents distinguished from deliberate faults

The initial 4Gi node ran out of headroom, producing Kubernetes TLS timeouts; increasing
its Docker budget to 6Gi/six CPUs recovered the API. Chroma was OOMKilled with exit 137
under its 1Gi limit; its request/limit became 768Mi/2Gi. Repeated readiness-client
construction accompanied API memory growth; connection reuse reduced observed pod
memory after rollout while retaining live metadata checks. Bulk embedding contention
and a host suspension interrupted evaluation; these are recorded in WORKLOG and are
not disguised as completed generation scores.
