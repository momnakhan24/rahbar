"""Explicit policy links must retain child provenance and current-version filters."""
from app.config import Settings
from app.retrieval.chroma import ChromaRetriever
from app.retrieval.references import rank_children, referenced_section, requested_source
from app.schemas import Passage


def passage(identifier, section, text, score=.5, page=7):
    return Passage(chunk_id=identifier, source="project-policy.pdf", section=section,
                   text=text, score=score, page=page)


def test_specific_phrase_survives_an_intervening_question_modifier():
    candidates = [
        passage("general", "7.1", "Graduating students may register for summer courses.", .7),
        passage("rule", "7.2", "No new courses are allowed. Only repeat courses may be taken.", .6),
        passage("count", "7.3", "Ten students must register in a summer course.", .7),
    ]
    ranked = rank_children("Are new elective courses allowed?", candidates)
    assert ranked[0].chunk_id == "rule"


def test_expansion_uses_child_citation_and_keeps_source_version_filter():
    anchor = passage("anchor", "4.8", "For restrictions see rule no 7: summer enrollment.", .85, 2)
    child = passage("child", "7.2", "No new courses are allowed.", .6, 9)

    class Collection:
        def get(self, where, include):
            assert {"source": "project-policy.pdf"} in where["$and"]
            assert {"superseded": False} in where["$and"]
            return {"metadatas": [{"section": child.section}]}

        def query(self, **kwargs):
            if kwargs["where"] == {"superseded": False}:
                item = anchor
            else:
                assert {"superseded": False} in kwargs["where"]["$and"]
                assert {"section": {"$in": [child.section]}} in kwargs["where"]["$and"]
                item = child
            return {"ids": [[item.chunk_id]], "documents": [[item.text]],
                    "metadatas": [[{"source": item.source, "section": item.section,
                                    "page": item.page}]], "distances": [[1 - item.score]]}

    retriever = ChromaRetriever.__new__(ChromaRetriever)
    retriever.settings = Settings()
    retriever.active_collection = lambda: Collection()
    result = retriever.retrieve("Can I take new courses?", 5, [1., 0.])
    expanded = next(p for p in result if p.chunk_id == "child")
    assert (expanded.section, expanded.page) == ("7.2", 9)
    assert expanded.score == anchor.score
    assert expanded.match_kind == "section_reference"
    assert referenced_section(anchor) == "7"


def test_named_page_resolves_only_a_unique_corpus_source():
    sources = {"fee-structure-page.html", "grading-page.html", "policy.pdf"}
    assert requested_source("What fee is on the fee page?", sources) == "fee-structure-page.html"
    assert requested_source("What grade is on the grading page?", sources) == "grading-page.html"
    assert requested_source("What is on the hostel page?", sources) is None
    assert requested_source("What is on the fee page?", sources | {"old-fee-page.html"}) is None


def test_named_source_filter_retains_actual_dense_score_and_version_boundary():
    class Collection:
        def get(self, where, include):
            assert where == {"superseded": False}
            return {"metadatas": [{"source": "grading-page.html"}]}

        def query(self, **kwargs):
            assert kwargs["where"] == {"$and": [{"source": "grading-page.html"},
                                               {"superseded": False}]}
            return {"ids": [["grade"]], "documents": [["A+ | Excellent | 4.00"]],
                    "metadatas": [[{"source": "grading-page.html", "section": "Grades"}]],
                    "distances": [[.4]]}

    retriever = ChromaRetriever.__new__(ChromaRetriever)
    retriever.settings = Settings()
    retriever.active_collection = lambda: Collection()
    result = retriever.retrieve("What does A+ mean on the grading page?", 5, [1., 0.])
    assert result[0].match_kind == "source_reference"
    assert result[0].score == 1.
    assert result[0].dense_score == .6
