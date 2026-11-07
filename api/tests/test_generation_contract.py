"""Regression coverage for contradictions found during local model validation."""
from types import SimpleNamespace

from app.config import Settings
from app.providers.llm.ollama import OllamaProvider
from app.schemas import Answer, Citation, Passage
from app.services.answer import _validate_citations


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
