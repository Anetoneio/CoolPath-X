from __future__ import annotations

from main import _simulate_summary


def test_summary_a_clearly_lower():
    s = _simulate_summary({"total_exposure": 50}, {"total_exposure": 100})
    assert "Option A" in s and "50%" in s


def test_summary_b_clearly_lower():
    s = _simulate_summary({"total_exposure": 100}, {"total_exposure": 40})
    assert "Option B" in s and "60%" in s


def test_summary_nearly_equal():
    s = _simulate_summary({"total_exposure": 100}, {"total_exposure": 95})
    assert "only" in s


def test_summary_identical():
    s = _simulate_summary({"total_exposure": 80}, {"total_exposure": 80})
    assert "same" in s
