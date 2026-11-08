"""Tests for golden-set retrieval and citation quality gates."""

from run_eval import citation_validity, gate, recall_at_k, summarise


def test_recall_matches_section_prefix_from_indexed_heading() -> None:
    relevant = [{"source": "rules.pdf", "section": "5.4"}]
    retrieved = [{"source": "rules.pdf", "section": "5.4 Academic Warning"}]
    assert recall_at_k(relevant, retrieved, 5) == 1.0
    assert recall_at_k(relevant, [], 3) == 0.0
    assert recall_at_k([], [], 5) is None


def test_citation_validity_rejects_fabricated_citation() -> None:
    response = {
        "retrieved": [{"source": "rules.pdf", "section": "5.4", "page": 12}],
        "citations": [
            {"source": "rules.pdf", "section": "5.4", "page": 12},
            {"source": "other.pdf", "section": "9", "page": 1},
        ],
    }
    assert citation_validity(response) == 0.5


def test_summary_and_gate_enforce_abstention_and_citation_rate() -> None:
    rows = [{
        "id": "q1", "type": "ordinary", "relevant": [{"source": "r.pdf", "section": "1"}],
        "expect": "supported term",
        "response": {
            "answer": "The supported term appears here.",
            "retrieved": [{"source": "r.pdf", "section": "1 Topic", "page": 2}],
            "citations": [{"source": "r.pdf", "section": "1 Topic", "page": 2}],
            "answered_from_context": True,
        },
    }, {
        "id": "q2", "type": "abstain", "must_abstain": True, "relevant": [],
        "response": {"retrieved": [], "citations": [], "answered_from_context": False},
    }]
    result = summarise(rows)
    assert result["recall_at_5"] == 1.0
    assert result["expected_term_accuracy"] == 1.0
    assert result["abstention_correctness"] == 1.0
    assert not gate(result, {"recall_at_5": 1.0})


def test_gate_rejects_recall_drop_bad_citations_and_failed_abstention() -> None:
    failures = gate({
        "recall_at_5": 0.8, "citation_validity": 0.9,
        "must_abstain_total": 1, "must_abstain_correct": 0,
        "abstention_correctness": 0.0,
    }, {"recall_at_5": 0.9})
    assert len(failures) >= 3
