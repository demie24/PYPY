import hashlib
import json

import pytest

from core.adversarial.coevolution_evaluator import run_evaluation, seed_everything


def test_seed_everything_repeats_numpy_and_torch_streams():
    import numpy as np
    import torch
    seed_everything(123)
    first = (np.random.rand(3).tolist(), torch.rand(3).tolist())
    seed_everything(123)
    second = (np.random.rand(3).tolist(), torch.rand(3).tolist())
    assert first == second


def test_multiseed_contract_rejects_single_seed(tmp_path):
    with pytest.raises(ValueError, match="at least two seeds"):
        run_evaluation([42], 1, tmp_path, tmp_path / "red.pt", tmp_path / "blue.pt")


def test_existing_evaluation_report_digest_is_self_consistent():
    path = "evaluation/coevolution/verified/report.json"
    try:
        report = json.loads(open(path, encoding="utf-8").read())
    except FileNotFoundError:
        pytest.skip("verified evaluation artefact is generated during checkpoint acceptance")
    expected = report.pop("reproducibility_digest")
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == expected
    assert len(report["seeds"]) >= 2
    assert report["grid"] == "ieee39"
