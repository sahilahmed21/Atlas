"""Smoke test for the offline demo: the headline claims it prints are actually true."""


def test_demo_records_replays_identically_and_catches_the_regression(tmp_path):
    from demo import main

    out = main(tmp_path)

    assert out["trials"] == out["tasks"] * out["k"]
    assert out["report"]["pass_hat_k"]["mean"] < out["report"]["pass_at_1"]["mean"]
    assert out["replay_identical"] is True and out["model_calls_during_replay"] == 0
    assert out["gate_failed"] is True and out["gate_ci95"][1] < 0
    assert out["diverges_at_step"] == 1
