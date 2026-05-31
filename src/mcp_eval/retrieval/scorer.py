"""RetrievalScorer — drives search, joins on tool_id, emits Spec 065 D1 metrics.

The scorer scores retrieval over the **frozen corpus** (CN-002): a retrieved
tool that is not in the corpus cannot count as a hit. This is what makes INV-2
hold — removing a labeled tool from the corpus drives that query's Recall to 0,
proving the scorer is not trivially passing (SC-003 / data-model §6).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..datasets.models import Corpus, GoldenSet
from . import metrics as M
from .search_client import SearchBackend

DEFAULT_K_VALUES = (1, 3, 5, 10)


class RetrievalMetrics(BaseModel):
    recall_at: dict[int, float]
    mrr: float
    ndcg_at_10: float
    map: float


class PerQueryResult(BaseModel):
    id: str
    query: str
    recall_at: dict[int, float]
    mrr: float
    ndcg_at_10: float
    ap: float
    retrieved: list[str]
    relevant: list[str]


class GateResult(BaseModel):
    metric: str = "recall_at_5"
    passed: bool = True
    tolerance: float = 0.0
    value: float | None = None
    threshold: float | None = None


class RetrievalReport(BaseModel):
    corpus_version: str
    golden_version: str
    runs_averaged: int = 1
    metrics: RetrievalMetrics
    per_query: list[PerQueryResult] = Field(default_factory=list)
    baseline_delta: dict[str, float] = Field(default_factory=dict)
    gate: GateResult = Field(default_factory=GateResult)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class RetrievalScorer:
    def __init__(
        self,
        backend: SearchBackend,
        *,
        k_values: tuple[int, ...] = DEFAULT_K_VALUES,
    ):
        self._backend = backend
        self._k_values = tuple(sorted(set(k_values)))
        self._limit = max(self._k_values + (10,))

    def _score_query(self, corpus_ids: set[str], query: Any) -> PerQueryResult:
        relevance_map = {
            lbl.tool_id: lbl.relevance for lbl in query.labels if lbl.relevance >= 1
        }
        relevant_ids = set(relevance_map)

        raw = self._backend.search(query.query, self._limit)
        # Score only against the frozen corpus universe (CN-002) -> INV-2.
        ranked = [st.tool_id for st in raw if st.tool_id in corpus_ids]

        return PerQueryResult(
            id=query.id,
            query=query.query,
            recall_at={k: M.recall_at_k(ranked, relevant_ids, k) for k in self._k_values},
            mrr=M.mrr(ranked, relevant_ids),
            ndcg_at_10=M.ndcg_at_k(ranked, relevance_map, 10),
            ap=M.average_precision(ranked, relevant_ids),
            retrieved=ranked,
            relevant=sorted(relevant_ids),
        )

    def _aggregate(self, per_query: list[PerQueryResult]) -> RetrievalMetrics:
        n = len(per_query) or 1
        recall = {
            k: sum(pq.recall_at[k] for pq in per_query) / n for k in self._k_values
        }
        return RetrievalMetrics(
            recall_at=recall,
            mrr=sum(pq.mrr for pq in per_query) / n,
            ndcg_at_10=sum(pq.ndcg_at_10 for pq in per_query) / n,
            map=sum(pq.ap for pq in per_query) / n,
        )

    def score(
        self,
        corpus: Corpus,
        golden: GoldenSet,
        *,
        baseline: dict[str, Any] | None = None,
        tolerance: float = 0.05,
        runs: int = 1,
        golden_version: str = "retrieval_golden",
    ) -> RetrievalReport:
        corpus_ids = corpus.tool_ids

        run_metrics: list[RetrievalMetrics] = []
        last_per_query: list[PerQueryResult] = []
        for _ in range(max(1, runs)):
            per_query = [self._score_query(corpus_ids, q) for q in golden.queries]
            run_metrics.append(self._aggregate(per_query))
            last_per_query = per_query

        metrics = self._average_runs(run_metrics)
        report = RetrievalReport(
            corpus_version=corpus.version,
            golden_version=golden_version,
            runs_averaged=max(1, runs),
            metrics=metrics,
            per_query=last_per_query,
        )

        if baseline is not None:
            report.baseline_delta = self._baseline_delta(metrics, baseline)
            report.gate = self._gate(metrics, baseline, tolerance)
        return report

    def _average_runs(self, run_metrics: list[RetrievalMetrics]) -> RetrievalMetrics:
        n = len(run_metrics) or 1
        ks = run_metrics[0].recall_at.keys()
        return RetrievalMetrics(
            recall_at={k: sum(m.recall_at[k] for m in run_metrics) / n for k in ks},
            mrr=sum(m.mrr for m in run_metrics) / n,
            ndcg_at_10=sum(m.ndcg_at_10 for m in run_metrics) / n,
            map=sum(m.map for m in run_metrics) / n,
        )

    @staticmethod
    def _baseline_recall_at_5(baseline: dict[str, Any]) -> float | None:
        recall = baseline.get("recall_at")
        if isinstance(recall, dict):
            for key in (5, "5"):
                if key in recall:
                    return float(recall[key])
        return None

    def _baseline_delta(
        self, metrics: RetrievalMetrics, baseline: dict[str, Any]
    ) -> dict[str, float]:
        delta: dict[str, float] = {}
        base_r5 = self._baseline_recall_at_5(baseline)
        if base_r5 is not None and 5 in metrics.recall_at:
            delta["recall_at_5"] = metrics.recall_at[5] - base_r5
        for name, current in (
            ("mrr", metrics.mrr),
            ("ndcg_at_10", metrics.ndcg_at_10),
            ("map", metrics.map),
        ):
            if name in baseline:
                delta[name] = current - float(baseline[name])
        return delta

    def _gate(
        self, metrics: RetrievalMetrics, baseline: dict[str, Any], tolerance: float
    ) -> GateResult:
        base_r5 = self._baseline_recall_at_5(baseline)
        value = metrics.recall_at.get(5)
        if base_r5 is None or value is None:
            return GateResult(passed=True, tolerance=tolerance, value=value)
        threshold = base_r5 - tolerance
        return GateResult(
            metric="recall_at_5",
            passed=value >= threshold,
            tolerance=tolerance,
            value=value,
            threshold=threshold,
        )
