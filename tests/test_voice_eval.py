"""The statistics of the voice evaluation (experiments/voice_eval) give textbook values."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "voice_eval"))
sys.path.insert(0, str(ROOT / "experiments" / "voice_eval" / "listening"))

from analyze import icc_2_1
from stats import auc, cohen_d, edit_distance, proportion_ci, quantile, ranks, spearman


def test_ranks_share_ties():
    assert ranks([10, 20, 20, 30]) == [1, 2.5, 2.5, 4]


def test_spearman_monotone_and_reversed():
    assert spearman([1, 2, 3, 4], [10, 20, 25, 100]) == pytest.approx(1)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1)


def test_auc_and_cohen_d():
    assert auc([3, 4, 5], [0, 1, 2]) == 1
    assert auc([1, 2], [1, 2]) == 0.5
    assert cohen_d([2, 4, 6], [1, 3, 5]) == pytest.approx(0.5)


def test_wilson_interval_contains_the_proportion():
    lo, hi = proportion_ci(50, 100)
    assert lo < 0.5 < hi and hi - lo == pytest.approx(0.19, abs=0.01)


def test_quantile_and_edit_distance():
    assert quantile([1, 2, 3, 4, 5], 0.5) == 3
    assert edit_distance(["il", "a", "poussé"], ["il", "la", "poussait"]) == 2


def test_icc_perfect_and_null_agreement():
    assert icc_2_1([[1, 1], [2, 2], [3, 3], [4, 4]]) == pytest.approx(1)
    assert icc_2_1([[1, 4], [4, 1], [2, 3], [3, 2]]) < 0
