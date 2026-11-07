"""Redis-backed semantic cache. Only validated, grounded responses are stored."""

from __future__ import annotations

import json
import hashlib
import math
import re
import uuid
from typing import Any, cast

from redis import Redis

from ..config import Settings
from ..schemas import Answer, Passage

_FOLLOW_UP = re.compile(
    r"\b(it|that|those|they|them|this|these|he|she|its|their)\b|^(and|also|what about)\b",
    re.IGNORECASE,
)


def is_follow_up(question: str) -> bool:
    return bool(_FOLLOW_UP.search(question.strip()))


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return -1.0
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    if not denominator:
        return -1.0
    return sum(a * b for a, b in zip(left, right)) / denominator


class SemanticCache:
    def __init__(self, client: Redis, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        policy = {"version": 3, "floor": settings.relevance_floor,
                  "top_k": settings.top_k, "provider": settings.llm_provider,
                  "model": settings.llm_model, "temperature": settings.temperature,
                  "contract": Answer.model_json_schema()}
        self.policy = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()[:16]

    def invalidate_obsolete_revisions(self, revision: str) -> int:
        """Delete cache entries for inactive index revisions as a repair after re-index."""
        namespace = f"rahbar:cache:{self.settings.embed_model}:"
        active_prefix = f"{namespace}{revision}:"
        removed = 0
        for key in self.client.scan_iter(match=namespace + "*"):
            name = key.decode("utf-8") if isinstance(key, bytes) else key
            if not name.startswith(active_prefix):
                removed += cast(int, self.client.delete(key))
        return removed

    def lookup(self, vector: list[float], revision: str) -> tuple[Answer, list[Passage]] | None:
        """Return the most similar stored response only above the configured threshold."""
        self.invalidate_obsolete_revisions(revision)
        best_similarity = -1.0
        best: dict[str, Any] | None = None
        prefix = f"rahbar:cache:{self.settings.embed_model}:{revision}:{self.policy}:"
        for key in self.client.scan_iter(match=prefix + "*"):
            raw = cast(str | bytes | None, self.client.get(key))
            if not raw:
                continue
            try:
                entry = json.loads(raw)
                similarity = _cosine(vector, entry["embedding"])
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
            if similarity >= self.settings.cache_threshold and similarity > best_similarity:
                best_similarity, best = similarity, entry
        if best is None:
            return None
        answer = Answer.model_validate(best["answer"])
        passages = [Passage.model_validate(item) for item in best["passages"]]
        return answer, passages

    def store(
        self, vector: list[float], revision: str, answer: Answer, passages: list[Passage]
    ) -> None:
        key = f"rahbar:cache:{self.settings.embed_model}:{revision}:{self.policy}:{uuid.uuid4().hex}"
        payload = {
            "embedding": vector,
            "answer": answer.model_dump(mode="json"),
            "passages": [item.model_dump(mode="json") for item in passages],
        }
        self.client.set(key, json.dumps(payload), ex=7 * 24 * 60 * 60)
