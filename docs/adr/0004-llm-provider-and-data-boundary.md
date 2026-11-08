# ADR 0004: provider boundary and document privacy

- **Status:** Accepted
- **Date:** 2026-11-05

## Context

The API needs a local provider for development and an optional hosted provider, while retrieved university documents must remain the source of truth. Provider changes should not alter the validated answer contract. Sending questions and retrieved passages to a hosted service also changes the data boundary.

## Decision

Use a small `LLMProvider` interface with stub, local Ollama and hosted OpenAI-compatible implementations. All providers return the same Pydantic answer schema; JSON/schema constraints are requested where supported, and citations are validated against retrieved passages before returning. Default development and Kubernetes base configuration use the stub provider. Hosted generation is an explicit configuration choice and requires an externally provisioned `LLM_API_KEY` secret. The model receives the question and retrieved corpus excerpts only; no student account records or other personal data are part of this corpus.

## Consequences

The retrieval and API layers remain provider-agnostic and testable offline. Provider output is still untrusted: schema-valid text can be unsupported, so citation membership and relevance checks remain mandatory. Hosted mode sends question text and selected public-document excerpts to the configured vendor; operators must confirm vendor retention and institutional policy before enabling it with non-public data. Credentials are never placed in source, images or committed manifests. Stub answers are for plumbing tests and must not be used as quality evidence.

## Alternatives considered

- One provider embedded directly in the route: rejected because it complicates testing and provider changes.
- Hosted-only generation: rejected because it prevents local/offline development and increases data exposure.
- Fully local-only generation: offers stronger data locality but can impose local hardware/model requirements; Ollama remains available for deployment where provisioned.
