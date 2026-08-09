from __future__ import annotations

from bma.experiments.mercabarna_flor_v0_5_0 import ActivityModel, ParticipationModel, brier, log_loss


def test_activity_model_is_future_only() -> None:
    from datetime import date

    model = ActivityModel()
    target = date(2026, 7, 21)
    before = model.predict(target)
    model.update(target, True)
    after = model.predict(target)
    assert before == 0.5
    assert after > before


def test_hierarchical_participation_shrinks_and_updates() -> None:
    metadata = {
        "48|A": {"product": "A", "origin_code": "48", "family": "F"},
        "48|B": {"product": "B", "origin_code": "48", "family": "F"},
    }
    model = ParticipationModel(metadata)
    prior = model.predict("48|A")
    model.update({"48|A"})
    assert model.predict("48|A") > prior
    assert model.predict("48|B") < prior


def test_probabilistic_losses_are_finite() -> None:
    assert brier(1, 0.8) == 0.04 - 1e-16 or abs(brier(1, 0.8) - 0.04) < 1e-12
    assert log_loss(1, 1.0) < 1e-6
