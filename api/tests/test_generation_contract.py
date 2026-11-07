"""Regression coverage for contradictions found during local model validation."""
from types import SimpleNamespace

from app.config import Settings
from app.providers.llm.ollama import OllamaProvider, _answer_schema
from app.schemas import Answer, Citation, Passage
from app.services.answer import _select_evidence, _validate_citations


def test_model_declared_abstention_cannot_display_an_uncited_fact() -> None:
    result = _validate_citations(Answer(
        reasoning="model inconsistency", answer="80%", citations=[],
        answered_from_context=False, confidence="high",
    ), [])
    assert "do not establish" in result.answer
    assert result.confidence == "low"
    assert result.citations == []


def test_ollama_separates_system_instructions_from_untrusted_evidence(monkeypatch) -> None:
    evidence = Passage(chunk_id="p1", text="Attendance is 80%.", source="rules.md",
                       section="1. Attendance", page=1, score=0.9)
    expected = Answer(reasoning="supported", answer="80%", answered_from_context=True,
                      confidence="high", citations=[Citation(
                          source=evidence.source, section=evidence.section, page=1)])
    captured = {}

    def post(url, **kwargs):
        captured.update(kwargs["json"])
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"message": {"content": expected.model_dump_json()}})

    monkeypatch.setattr("app.providers.llm.ollama.httpx.post", post)
    result = OllamaProvider(Settings()).generate("What attendance is required?", [evidence])
    assert result == expected
    assert captured["messages"][0]["role"] == "system"
    assert "Attendance is 80%." not in captured["messages"][0]["content"]
    assert captured["messages"][1]["role"] == "user"
    assert '"citation"' in captured["messages"][1]["content"]
    assert captured["format"]["$defs"]["Citation"]["enum"] == [
        {"source": evidence.source, "section": evidence.section, "page": evidence.page}
    ]
    assert 0 < captured["options"]["num_predict"] <= 512


def test_decoder_requires_citations_only_for_grounded_branch() -> None:
    passage = Passage(chunk_id="x", text="The library closes at seven.",
                      source="library.txt", section="Hours", page=2, score=.9)
    schema = _answer_schema([passage])
    grounded, refusal = schema["oneOf"]
    assert grounded["properties"]["answered_from_context"]["const"] is True
    assert grounded["properties"]["citations"]["minItems"] == 1
    assert refusal["properties"]["answered_from_context"]["const"] is False
    assert refusal["properties"]["citations"]["maxItems"] == 0
    assert refusal["properties"]["confidence"]["const"] == "low"
    assert next(iter(grounded["properties"])) == "answered_from_context"


def test_explicit_clause_focus_does_not_bypass_relevance_floor() -> None:
    requested = Passage(chunk_id="clause", text="All classes must be attended.",
                        source="policy.pdf", section="4.12 Attendance", page=3, score=.75)
    other = requested.model_copy(update={"chunk_id": "other", "section": "4.120 Unrelated", "score": .9})
    assert _select_evidence("What does clause 4.12 say?", [other, requested], .7) == [requested]
    assert _select_evidence("What does clause 4.12 say?", [requested], .8) == []


def test_weak_passage_with_same_number_does_not_distract_generation() -> None:
    policy = Passage(chunk_id="rule", text="Minimum CGPA is 2.00.", source="rules.pdf",
                     section="Warning", page=1, score=.91)
    grades = policy.model_copy(update={"chunk_id": "table", "source": "grades.html", "score": .74})
    assert _select_evidence("What CGPA avoids a warning?", [policy, grades], .7) == [policy]


def test_bare_boolean_is_replaced_by_attributed_policy_text():
    passage = Passage(chunk_id="p", source="policy.txt", section="Repeats", page=1,
                      text="3.1 Only the most recent grade counts.", score=.9)
    answer = Answer(reasoning="supported", answer="Yes", answered_from_context=True,
                    confidence="high", citations=[Citation(source=passage.source,
                                                          section=passage.section, page=1)])
    result = _validate_citations(answer, [passage])
    assert result.answer == 'The cited policy states: "Only the most recent grade counts."'
    assert result.citations == answer.citations
