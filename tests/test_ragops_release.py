import json
from pathlib import Path

from ragops.release import gate
from ragops.tracing import prompt_hash, reconstruct


def test_gate_accepts_baseline_and_rejects_recall_drop(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    config = Path("config/gate.yaml")
    result = {
        "environment": {"seed": 0, "split": "a", "llm_name": "test"},
        "mean": {
            "recall_at_5": 0.8,
            "faithfulness": 0.95,
            "p95_total_ms": 1000,
            "abstention_correctness": 0.9,
        },
    }
    baseline.write_text(json.dumps(result))
    candidate.write_text(json.dumps(result))
    assert gate(baseline, candidate, config)
    assert "RELEASE" in capsys.readouterr().out
    result["mean"]["recall_at_5"] = 0.77
    candidate.write_text(json.dumps(result))
    assert not gate(baseline, candidate, config)
    assert "REJECT" in capsys.readouterr().out


def test_trace_reconstructs_prompt(tmp_path):
    path = tmp_path / "traces.jsonl"
    requests = [{"messages": [{"role": "user", "content": "Evidence and policy question"}]}]
    path.write_text(json.dumps({
        "trace_id": "test", "model_requests": requests, "prompt_hash": prompt_hash(requests),
        "context": [{"chunk_id": "library"}],
    }) + "\n")
    assert reconstruct(path, "test")["model_requests"] == requests
