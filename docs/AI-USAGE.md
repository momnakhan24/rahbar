# AI usage

# AI assistance disclosure

Codex was used to read the assignment and starter kit, create the work tracker, and draft
the initial Dockerfiles, stub-mode Kubernetes resources, architecture notes, ADR, and
README structure. The user will review the implementation and must understand and be able
to explain it. Resource values and Minikube host networking are provisional assumptions;
they will be replaced or confirmed using cluster measurements and observed behavior. No
AI-generated evaluation results, corpus evidence, screenshots, or runtime claims are being
presented as observed facts.

| Tool | What it wrote or shaped | What we changed afterwards, and why |
| --- | --- | --- |

## Local execution and review, November 2026

Codex also implemented the real indexing/retrieval/generation/cache paths, evaluation
gates, Dockerfiles, Kubernetes manifests, CI/CD workflows and experiment scripts. It
operated Docker Desktop and the isolated Minikube profile `rahbar`, downloaded public
corpus files and model weights, ran tests and collected runtime output. AI assistance
extends to these documents and their engineering explanations; this is not a claim
that two humans independently authored the code or performed the recorded experiments.

Observed output changed the implementation: numbered PDF clauses were preserved after
fixture retrieval exposed discarded evidence; visible-page cropping removed hidden
adjacent-page text; single-block OCR kept reviewed clause numbers attached; model
abstentions were normalized after contradictory output; revision-based invalidation
removed the indexer's forbidden Redis access. Actual resource failures led to raising
the node and Chroma memory budgets. Golden version questions were corrected from source
comparison before corpus retrieval measurements because the originally chosen policies
had not changed. Cache threshold 0.96 was retained after measured unsafe near-neighbor
hits at lower thresholds, with the lost paraphrase hits explicitly disclosed.

Measured evidence is produced by commands/scripts, not invented by the language model.
Representative visual checks are labelled as such. Unexecuted external repository
settings, approvals, CD publication and screenshot requirements remain distinguishable
from local tests. The submitting team must review, understand and explain the final
implementation and measurements; Codex cannot attest to that human review.

## Final grounding and deployment corrections

Codex implemented and tested the final evidence-excerpt generation strategy after
live answers exposed correct facts paired with irrelevant citations and incorrect
source selection. It added unique named-page filtering, explicit raw dense scores,
a bounded numeric model evidence selector, constrained final Answer generation,
independent quote/citation pairing checks and cache policy invalidation. Qwen 2.5
3B was selected after smaller-model and alternative-schema probes failed review.
No question labels were changed to fit final retrieval or generation.

Codex also cleaned HTML navigation, added atomic selected-source refresh with PDF
vector reuse, reran the three chunk measurements with input fingerprints, hardened
the corpus loader, corrected clean-clone order, and made CD depend on the complete
reusable fixture CI gate. It records observed results, limitations and failed probes
in WORKLOG and evidence. The owner must still configure Actions credentials, provide
actual review/approval, capture required screenshots and submit the work. The agent
did not export Docker credentials or fabricate a successful hosted CD run.
