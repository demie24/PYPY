import numpy as np
import pytest

from core.ai_runtime.model_service import IEEE39ModelRuntime, _ensure_finite


def test_model_runtime_branch_ids_match_ieee39_contract():
    assert IEEE39ModelRuntime._branch_id(0) == "L_line_0"
    assert IEEE39ModelRuntime._branch_id(34) == "L_line_34"
    assert IEEE39ModelRuntime._branch_id(35) == "L_trafo_0"
    assert IEEE39ModelRuntime._branch_id(45) == "L_trafo_10"


def test_model_runtime_rejects_non_finite_nested_output():
    with pytest.raises(ValueError, match="non-finite model output"):
        _ensure_finite({"risk": [0.1, np.nan]})


def test_all_trained_runtime_checkpoints_load_with_ieee39_shapes(monkeypatch):
    monkeypatch.setattr(
        "core.ai_runtime.model_service.CHECKPOINTS",
        {
            "lstm": __import__("pathlib").Path("core/lstm/trained_lstm_model.pt"),
            "gnn": __import__("pathlib").Path("core/gnn/trained_gnn_model.pt"),
            "stgnn": __import__("pathlib").Path("core/gnn/trained_stgnn_model.pt"),
            "pinn": __import__("pathlib").Path("core/pinn/trained_pinn_model.pt"),
        },
    )
    for component in ("lstm", "gnn", "stgnn", "pinn"):
        runtime = IEEE39ModelRuntime(component)
        assert runtime.readiness.model_loaded is True
        if component in {"gnn", "stgnn"}:
            assert len(runtime.edge_index) == 46
