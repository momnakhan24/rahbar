# Explaining Assignment 03

## A. Verification and data management

A source manifest lists the stable document ID, original filename, version, declared page count and access class. Verification checks all four categories and records why a document passed or failed. Quality checks examine extracted text and readability. Completeness checks metadata and truncation evidence. Recency compares versions of the same logical ID. Uniqueness compares normalized hashes and embedding cosine similarity against different active documents. An injection warning is informational so the retrieval rail can demonstrate how it handles the content during a query.

The lake keeps immutable source revision bytes and an authoritative manifest. A projection under `lake/current/` contains active bytes. The changelog records admission, deletion and restore. Chroma is a derived index. Synchronization compares chunk metadata and hashes, upserts the affected rows, and deletes rows absent from the active manifest. The final reconciliation verifies the entire collection.

## B. Offline evaluation

The embedding module compares paraphrase and unrelated cosine distributions, measures the time to embed text and repeats an embedding to check determinism. Retrieval evaluates ranked document relevance and introduces a simple query typo for its noise experiment. End-to-end grading checks expected facts, abstention and whether the returned quotation appears in the cited context. Two uncached passes use a fixed generation seed. Timing can still fluctuate with machine load.

## C. Release gate

The two collections differ in the maximum chunk size. The gate compares recall, faithfulness, latency and abstention against the measured baseline. The candidate is eligible only if every rule passes. The Kubernetes evaluation Job propagates the gate exit code.

## D. Tracing and monitoring

The trace records all retrieved chunks, deterministic reranking, discarded chunks, and the exact request sent to Ollama. The model chooses a numbered excerpt. Python formats that excerpt and its real citation into the answer. The reconstruction command checks the request hash. Cache hits retain the original context and prompt. The metrics view summarizes trace observations over a time window.

## E. Coverage and drift

Coverage computes each live question's best cosine match in the offline set. Uncovered queries are grouped by similarity to representative questions. The expanded evaluation set adds grounded questions for campus topics and abstention questions for unsupported topics. Before/after evaluation also changes the expected recorder loan duration once its new source revision is active.

## F. Kubernetes

Chroma owns its volume through a StatefulSet. One ingestion process writes the lake and derived vector state. Live and candidate APIs read separate collections. The evaluation Job targets a Service and reads mounted gate thresholds. The rolling update allows one temporary extra replica so the old one can serve until the new one is ready.
