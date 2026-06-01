"""Hand-computed confusion-matrix metric tests (R-09, FR-005).

Every expected value is derived by hand from the four confusion counts.
"""

from __future__ import annotations

import pytest

from mcp_eval.security import metrics as M
from mcp_eval.security.metrics import Confusion


def test_precision_recall_f1_fpr_basic():
    # tp=3 fp=1 tn=4 fn=2
    c = Confusion(tp=3, fp=1, tn=4, fn=2)
    assert M.precision(c) == pytest.approx(3 / 4)  # 3/(3+1)
    assert M.recall(c) == pytest.approx(3 / 5)  # 3/(3+2)
    assert M.fpr(c) == pytest.approx(1 / 5)  # 1/(1+4)
    p, r = 3 / 4, 3 / 5
    assert M.f1(c) == pytest.approx(2 * p * r / (p + r))


def test_perfect_detector():
    c = Confusion(tp=5, fp=0, tn=5, fn=0)
    assert M.precision(c) == 1.0
    assert M.recall(c) == 1.0
    assert M.f1(c) == 1.0
    assert M.fpr(c) == 0.0


def test_precision_zero_when_no_positives_predicted():
    # flagged nothing: tp=0 fp=0 -> precision denom 0 -> 0.0 (not div error)
    c = Confusion(tp=0, fp=0, tn=8, fn=2)
    assert M.precision(c) == 0.0
    assert M.recall(c) == 0.0  # 0/(0+2)
    assert M.f1(c) == 0.0
    assert M.fpr(c) == 0.0  # 0/(0+8)


def test_recall_zero_when_no_malicious_present():
    # all benign: tp=0 fn=0 -> recall denom 0 -> 0.0
    c = Confusion(tp=0, fp=2, tn=6, fn=0)
    assert M.recall(c) == 0.0
    assert M.fpr(c) == pytest.approx(2 / 8)


def test_fpr_zero_when_no_benigns():
    # all malicious: fp=0 tn=0 -> fpr denom 0 -> 0.0
    c = Confusion(tp=4, fp=0, tn=0, fn=1)
    assert M.fpr(c) == 0.0
    assert M.recall(c) == pytest.approx(4 / 5)


def test_tally_and_add():
    # malicious+flagged -> tp ; benign+flagged -> fp
    assert M.tally(flagged=True, malicious=True) == Confusion(tp=1)
    assert M.tally(flagged=False, malicious=True) == Confusion(fn=1)
    assert M.tally(flagged=True, malicious=False) == Confusion(fp=1)
    assert M.tally(flagged=False, malicious=False) == Confusion(tn=1)
    summed = M.add(Confusion(tp=1, fp=2), Confusion(tp=3, tn=4))
    assert summed == Confusion(tp=4, fp=2, tn=4, fn=0)
    assert summed.total == 10
