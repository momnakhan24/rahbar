"""Grounded query path: cache, retrieve, check relevance, generate, validate, return."""

from __future__ import annotations

import logging
import math
import re
import time

from redis import Redis

from ..config import Settings
from ..embedding import embed_query
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.base import Retriever
from ..routes.metrics import (
    ABSTENTIONS,
    FALLBACKS,
    GENERATION_LATENCY,
    RETRIEVAL_LATENCY,
    TOKENS_IN,
    TOKENS_OUT,
    observe_cache,
)
from ..schemas import Answer, AskResponse, Passage, RetrievedRef
from .cache import SemanticCache, is_follow_up

log = logging.getLogger("rahbar.answer")


def _fallback() -> Answer:
    return Answer(
        reasoning="Safe fallback after provider output failed validation or generation.",
        answer="I could not produce a validated answer from the available documents. Please try again.",
        citations=[],
        answered_from_context=False,
        confidence="low",
    )


def never_cache(answer: Answer, follow_up: bool) -> bool:
    """Abstentions and context-dependent follow-ups must not enter semantic cache."""
    return follow_up or not answer.answered_from_context


def _validate_citations(answer: Answer, passages: list[Passage]) -> Answer:
    if not answer.answered_from_context:
        return answer.model_copy(update={
            "answer": "The available documents do not establish an answer to this question.",
            "citations": [], "confidence": "low",
        })
    valid = {(p.source, p.section, p.page) for p in passages}
    if not answer.citations:
        raise ValueError("grounded answer has no citations")
    invalid = [c for c in answer.citations if (c.source, c.section, c.page) not in valid]
    if invalid:
        raise ValueError("one or more citations do not match retrieved passages")
    if answer.answer.strip().rstrip(".! ").lower() in {"yes", "no"}:
        citation = answer.citations[0]
        cited = next(p for p in passages if (p.source, p.section, p.page)
                     == (citation.source, citation.section, citation.page))
        text = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", cited.text).strip()
        if len(text) > 650:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            text = sentences[0]
        if 5 < len(text) <= 650:
            # Show the actual policy rather than an ambiguous, potentially misleading
            # bare yes/no. This is an attributed excerpt, not invented explanation.
            return answer.model_copy(update={"answer": f'The cited policy states: "{text}"'})
    return answer


def _retrieval_refs(passages: list[Passage]) -> list[RetrievedRef]:
    return [RetrievedRef(
        chunk_id=p.chunk_id, source=p.source, section=p.section, page=p.page, score=p.score,
        match_kind=p.match_kind,
    ) for p in passages]


def _response(
    answer: Answer, passages: list[Passage], request_id: str, provider: str
) -> AskResponse:
    return AskResponse(
        request_id=request_id,
        answer=answer.answer,
        citations=answer.citations,
        answered_from_context=answer.answered_from_context,
        confidence=answer.confidence,
        retrieved=_retrieval_refs(passages),
        provider=provider,
    )


def _select_evidence(question: str, passages: list[Passage], floor: float) -> list[Passage]:
    eligible = [p for p in passages if p.score >= floor]
    if not eligible:
        return []
    if re.search(r"\b(?:clause|section|rule)s?\b", question, re.IGNORECASE):
        numbers = re.findall(r"\b\d+(?:\.\d+)+\b", question)
        exact = [p for p in eligible if any(
            p.section == number or p.section.startswith(number + " ")
            or p.section.startswith(number + ".") for number in numbers)]
        if exact:
            return exact[:3]
    # Keep similarly numbered facts in weakly related passages from distracting
    # the generator (for example a grade-point table versus an academic warning).
    cutoff = max(floor, max(p.score for p in eligible) - .10)
    return [p for p in eligible if p.score >= cutoff][:3]


def answer_question(
    question: str,
    retriever: Retriever,
    provider: LLMProvider,
    settings: Settings,
    redis: Redis | None = None,
) -> tuple[AskResponse, bool]:
    follow_up = is_follow_up(question)
    cache = SemanticCache(redis, settings) if redis is not None and retriever.name == "chroma" else None
    query_embedding: list[float] | None = None
    cache_hit = False
    cache_revision = ""
    answer: Answer | None = None
    passages: list[Passage] = []

    # Semantic comparison requires a question vector. It is done before vector search, so a
    # hit skips Chroma retrieval and generation while preserving the cached evidence refs.
    if cache is not None and not follow_up:
        try:
            query_embedding = embed_query(question, settings)
            revision_method = getattr(retriever, "cache_revision", None)
            cache_revision = revision_method() if revision_method else settings.collection
            cached = cache.lookup(query_embedding, cache_revision)
            observe_cache(cached is not None)
            if cached is not None:
                answer, passages = cached
                cache_hit = True
        except Exception:
            log.warning("semantic cache lookup failed", exc_info=True)

    if not cache_hit:
        started = time.perf_counter()
        if query_embedding is None and retriever.name == "chroma":
            query_embedding = embed_query(question, settings)
        passages = retriever.retrieve(question, k=settings.top_k, query_embedding=query_embedding)
        RETRIEVAL_LATENCY.observe(time.perf_counter() - started)

        evidence = _select_evidence(question, passages, settings.relevance_floor)
        if not evidence:
            answer = Answer(
                reasoning="No retrieved passage cleared the configured relevance floor.",
                answer="The available documents do not contain enough relevant information to answer that.",
                citations=[],
                answered_from_context=False,
                confidence="low",
            )
        else:
            # A malformed response or citation is retried once. The user receives a safe
            # abstention after the second failure rather than a 500 or unsupported claim.
            for retry in range(2):
                started = time.perf_counter()
                try:
                    candidate = provider.generate(question, evidence)
                    answer = _validate_citations(candidate, evidence)
                    break
                except Exception as exc:
                    log.warning("generation validation failed", extra={
                        "attempt": retry + 1, "error": type(exc).__name__,
                    })
                    answer = None
                finally:
                    GENERATION_LATENCY.observe(time.perf_counter() - started)
            if answer is None:
                answer = _fallback()
                FALLBACKS.inc()

    assert answer is not None
    if not answer.answered_from_context:
        ABSTENTIONS.inc()

    # Prometheus token counters use a visible, deterministic ~4 characters/token estimate.
    TOKENS_IN.inc(math.ceil((len(question) + sum(len(p.text) for p in passages)) / 4))
    TOKENS_OUT.inc(math.ceil(len(answer.answer) / 4))

    if cache is not None and not cache_hit and not never_cache(answer, follow_up):
        try:
            if query_embedding is not None:
                cache.store(query_embedding, cache_revision, answer, passages)
        except Exception:
            log.warning("semantic cache store failed", exc_info=True)

    log.info(
        "answered",
        extra={
            "retriever": retriever.name,
            "provider": provider.name,
            "top_k": settings.top_k,
            "chunk_ids": [p.chunk_id for p in passages],
            "scores": [round(p.score, 4) for p in passages],
            "answered_from_context": answer.answered_from_context,
            "cache_hit": cache_hit,
        },
    )
    response = _response(answer, passages, request_id_var.get(), provider.name)
    return response, cache_hit
