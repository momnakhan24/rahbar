"""The real retriever. Yours to build (sections 3.2 and 4.4).

Connection details are already here; the query is not.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import Settings
from ..embedding import embed_query
from ..schemas import Passage
from .references import rank_children, referenced_section


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        import chromadb  # the thin client, from chromadb-client in requirements.txt
        from chromadb.config import Settings as ChromaSettings

        self.settings = settings
        self.client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                                          settings=ChromaSettings(anonymized_telemetry=False))

    def retrieve(
        self, question: str, k: int, query_embedding: list[float] | None = None
    ) -> list[Passage]:
        collection = self.active_collection()
        vector = query_embedding or embed_query(question, self.settings)
        where = None if _asks_for_older_version(question) else {"superseded": False}
        result = collection.query(
            query_embeddings=[vector],
            n_results=max(1, k),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        texts = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        passages = []
        for chunk_id, text, metadata, distance in zip(ids, texts, metadatas, distances):
            if not metadata or text is None or distance is None:
                continue
            passages.append(Passage(
                chunk_id=str(chunk_id),
                text=str(text),
                source=str(metadata.get("source", "unknown")),
                section=str(metadata.get("section", "unknown")),
                page=int(metadata["page"]) if metadata.get("page") is not None else None,
                score=max(-1.0, min(1.0, 1.0 - float(distance))),
            ))
        return self._expand_reference(question, vector, passages, k, where)

    def _expand_reference(self, question: str, vector: list[float], passages: list[Passage],
                          k: int, where: dict[str, bool] | None) -> list[Passage]:
        if k < 2:
            return passages
        collection = self.active_collection()
        for anchor in passages[:3]:
            number = referenced_section(anchor)
            if not number:
                continue
            filters: list[dict[str, Any]] = [{"source": anchor.source}]
            if where:
                filters.append(where)
            source_filter = {"$and": filters} if len(filters) > 1 else filters[0]
            entries = collection.get(where=source_filter, include=["metadatas"])
            matching = [m for m in entries["metadatas"]
                        if m and re.match(rf"^{re.escape(number)}\.\d+(?:\s|\.|$)", m["section"])]
            sections = sorted({m["section"] for m in matching})
            if not sections:
                continue
            linked_filter = {"$and": [*filters, {"section": {"$in": sections}}]}
            linked = collection.query(query_embeddings=[vector], n_results=len(matching),
                                      where=linked_filter,
                                      include=["documents", "metadatas", "distances"])
            children = [Passage(chunk_id=i, text=t, source=m["source"], section=m["section"],
                                page=m.get("page"), score=1 - distance)
                        for i, t, m, distance in zip(linked["ids"][0], linked["documents"][0],
                                                    linked["metadatas"][0], linked["distances"][0])]
            chosen = rank_children(question, children)[:min(3, k - 1)]
            # A cross-reference carries the anchor's contextual relevance. Citation
            # metadata still names the actual child clause, never its parent.
            expanded = [p.model_copy(update={"score": max(p.score, anchor.score),
                                             "match_kind": "section_reference"}) for p in chosen]
            output: list[Passage] = []
            for p in [*passages[:k - len(expanded)], *expanded, *passages]:
                if all(prior.chunk_id != p.chunk_id for prior in output):
                    output.append(p)
                if len(output) == k:
                    return output
            return output
        return passages

    def active_collection(self):  # type annotation omitted for Chroma's dynamic client type
        """Resolve the published generation, falling back to the starter dummy collection."""
        registry_name = f"{self.settings.collection[:40]}-registry"
        try:
            registry = self.client.get_collection(registry_name)
            active = (registry.metadata or {}).get("active_collection")
            if active:
                return self.client.get_collection(str(active))
        except Exception:
            pass
        return self.client.get_collection(self.settings.collection)

    def cache_revision(self) -> str:
        collection = self.active_collection()
        return str((collection.metadata or {}).get("index_revision", collection.name))


def _asks_for_older_version(question: str) -> bool:
    """Allow superseded chunks only when the question explicitly asks historically."""
    import re

    return bool(re.search(
        r"\b(older|old|previous|prior|superseded|historical|before\s+20\d{2}|20\d{2}\s+version)\b",
        question,
        re.IGNORECASE,
    ))
