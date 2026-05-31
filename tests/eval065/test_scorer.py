"""RetrievalScorer behaviour, including INV-2 (data-model §6 / SC-003)."""

from __future__ import annotations

import pytest

from mcp_eval.datasets.models import Corpus, GoldenSet
from mcp_eval.retrieval.scorer import RetrievalScorer
from mcp_eval.retrieval.search_client import ScoredTool


class FakeSearchBackend:
    """Deterministic search backend keyed by query text -> ranked tool_ids."""

    def __init__(self, table: dict[str, list[str]]):
        self._table = table

    def search(self, query: str, limit: int) -> list[ScoredTool]:
        ids = self._table.get(query, [])[:limit]
        # descending synthetic score so order is preserved on the consumer side
        return [ScoredTool(tool_id=tid, score=float(len(ids) - i)) for i, tid in enumerate(ids)]


def _perfect_backend() -> FakeSearchBackend:
    return FakeSearchBackend(
        {
            "file a bug report against a code repository": [
                "github:create_issue",
                "gitlab:create_issue",
                "docker:run_container",
            ],
            "spin up an isolated runtime from a prebuilt image": [
                "docker:run_container",
                "github:create_issue",
            ],
        }
    )


def test_scorer_perfect_retrieval(corpus: Corpus, golden: GoldenSet):
    scorer = RetrievalScorer(_perfect_backend())
    report = scorer.score(corpus, golden)
    # both queries put a relevant tool at rank 1 -> MRR 1.0, Recall@5 1.0
    assert report.metrics.recall_at[5] == pytest.approx(1.0)
    assert report.metrics.mrr == pytest.approx(1.0)
    assert report.metrics.ndcg_at_10 == pytest.approx(1.0)


def test_inv2_removing_labeled_tool_drives_recall_to_zero(corpus: Corpus, golden: GoldenSet):
    """INV-2: a labeled tool removed from the corpus -> that query's Recall = 0.

    The scorer only scores against the frozen corpus universe (CN-002), so a
    retrieved tool absent from the corpus cannot count as a hit. Proves the
    scorer is not trivially passing (SC-003).
    """
    # Take query q0002 in isolation (single relevant: docker:run_container).
    single = GoldenSet(corpus_version=corpus.version, queries=[golden.queries[1]])

    full = RetrievalScorer(_perfect_backend()).score(corpus, single)
    assert full.metrics.recall_at[5] == pytest.approx(1.0)

    # Remove the only labeled tool from the corpus.
    degraded = Corpus(
        version=corpus.version,
        generated_from=corpus.generated_from,
        tools=[t for t in corpus.tools if t.tool_id != "docker:run_container"],
    )
    degraded_report = RetrievalScorer(_perfect_backend()).score(degraded, single)
    assert degraded_report.metrics.recall_at[5] == 0.0
    assert degraded_report.metrics.mrr == 0.0


def test_baseline_delta_reported(corpus: Corpus, golden: GoldenSet):
    scorer = RetrievalScorer(_perfect_backend())
    baseline = {"recall_at": {"5": 0.8}, "mrr": 0.5, "ndcg_at_10": 0.9, "map": 0.5}
    report = scorer.score(corpus, golden, baseline=baseline, tolerance=0.05)
    # delta = current - baseline ; recall@5 1.0 - 0.8 = +0.2
    assert report.baseline_delta["recall_at_5"] == pytest.approx(0.2)
    assert report.gate.passed is True  # 1.0 >= 0.8 - 0.05
