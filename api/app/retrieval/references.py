"""Rank explicitly linked policy clauses without changing corpus or golden labels."""
from __future__ import annotations

from collections import Counter
import math
import re

from ..schemas import Passage

_STOP = set("a an the of for to in on at is are was were be what which how when where "
            "why can could would should do does did has have had under about from and "
            "or with as by it its that this these those i my me we our you your their "
            "they them student students rules rule current listed page say may".split())


def _terms(text: str) -> list[str]:
    return [word[:-1] if len(word) > 4 and word.endswith("s") else word
            for word in re.findall(r"[a-z0-9]+(?:[.+][a-z0-9]*)?", text.lower())
            if word not in _STOP]


def referenced_section(passage: Passage) -> str | None:
    # A retrieved parent heading is itself a link to its numbered children.
    heading = re.match(r"^(\d+)\.\s", passage.section)
    if heading:
        return heading[1]
    explicit = re.search(r"\b(?:rule|clause|section)\s+(?:no\.?\s*)?(\d+(?:\.\d+)*)",
                         passage.text, re.IGNORECASE)
    return explicit[1] if explicit else None


def rank_children(question: str, passages: list[Passage]) -> list[Passage]:
    """BM25 within a linked section adds specificity to its children's own cosine."""
    tokens = [_terms(p.text) for p in passages]
    if not tokens:
        return []
    frequency = Counter(term for words in tokens for term in set(words))
    average = sum(map(len, tokens)) / len(tokens) or 1.0
    query_words = _terms(question)
    query = set(query_words)
    query_pairs = {(word, neighbor) for i, word in enumerate(query_words)
                   for neighbor in query_words[i + 1:i + 4]}
    scores = {}
    for passage, words in zip(passages, tokens):
        counts = Counter(words)
        lexical = 0.0
        for term in query:
            count = counts[term]
            inverse = math.log(1 + (len(tokens) - frequency[term] + .5) / (frequency[term] + .5))
            lexical += inverse * count * 2.5 / (count + 1.5 * (.25 + .75 * len(words) / average))
        # Permit an intervening modifier in the question ("new elective courses")
        # to match a direct policy phrase ("new courses"). Preserve word order.
        phrase_matches = len(query_pairs & set(zip(words, words[1:])))
        scores[passage.chunk_id] = (passage.score + .4 * lexical / (lexical + 3)
                                   + .15 * min(2, phrase_matches))
    return sorted(passages, key=lambda p: scores[p.chunk_id], reverse=True)
