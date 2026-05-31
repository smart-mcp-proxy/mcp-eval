"""Hand-computed metric tests (R-09). Each expected value is derived by hand."""

from __future__ import annotations

import math

import pytest

from mcp_eval.retrieval import metrics


def test_recall_at_k_basic():
    ranked = ["a", "b", "c", "d"]
    relevant = {"b", "d"}
    # top-1 = {a}: 0 of 2; top-3 = {a,b,c}: 1 of 2; top-5: 2 of 2
    assert metrics.recall_at_k(ranked, relevant, 1) == 0.0
    assert metrics.recall_at_k(ranked, relevant, 3) == pytest.approx(0.5)
    assert metrics.recall_at_k(ranked, relevant, 5) == pytest.approx(1.0)


def test_recall_at_k_no_relevant_is_zero():
    assert metrics.recall_at_k(["a", "b"], set(), 5) == 0.0


def test_mrr_first_hit_rank():
    # first relevant at rank 2 -> 1/2
    assert metrics.mrr(["a", "b", "c"], {"b"}) == pytest.approx(0.5)
    # first relevant at rank 1 -> 1.0
    assert metrics.mrr(["b", "a"], {"b"}) == pytest.approx(1.0)
    # no relevant in list -> 0
    assert metrics.mrr(["a", "c"], {"z"}) == 0.0


def test_ndcg_at_k_graded():
    # ranked relevances: [2, 0, 1] ; ideal = [2, 1, 0]
    relevance_map = {"a": 2, "b": 0, "c": 1}
    ranked = ["a", "b", "c"]
    # DCG = 2/log2(2) + 0/log2(3) + 1/log2(4) = 2 + 0 + 0.5 = 2.5
    # IDCG = 2/log2(2) + 1/log2(3) + 0/log2(4) = 2 + 0.6309 = 2.6309
    dcg = 2 / math.log2(2) + 0 / math.log2(3) + 1 / math.log2(4)
    idcg = 2 / math.log2(2) + 1 / math.log2(3) + 0 / math.log2(4)
    assert metrics.ndcg_at_k(ranked, relevance_map, 10) == pytest.approx(dcg / idcg)


def test_ndcg_zero_when_no_relevant():
    assert metrics.ndcg_at_k(["a"], {"a": 0}, 10) == 0.0


def test_average_precision():
    # relevant = {a, c}; ranked = [a, b, c, d]
    # hit at rank1 -> 1/1; miss; hit at rank3 -> 2/3 ; AP = (1 + 0.6667)/2
    ranked = ["a", "b", "c", "d"]
    relevant = {"a", "c"}
    assert metrics.average_precision(ranked, relevant) == pytest.approx((1.0 + 2 / 3) / 2)


def test_average_precision_no_relevant_is_zero():
    assert metrics.average_precision(["a"], set()) == 0.0
