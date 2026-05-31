"""Pure ranking-metric functions (R-09).

All functions take an already-ranked list of ``tool_id`` strings (best first)
plus the relevance information for a single query, and return a float. No I/O,
no side effects — every value is hand-checkable in the unit tests.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    """|relevant ∩ top-k| / |relevant|. 0 when there are no relevant items."""
    if not relevant_ids:
        return 0.0
    top_k = set(ranked_ids[:k])
    return len(top_k & relevant_ids) / len(relevant_ids)


def mrr(ranked_ids: Sequence[str], relevant_ids: set[str]) -> float:
    """Reciprocal rank of the first relevant hit (0 if none retrieved)."""
    for rank, tool_id in enumerate(ranked_ids, start=1):
        if tool_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def _dcg(gains: Sequence[float]) -> float:
    # position i (1-based): gain / log2(i + 1)  -> position 1 divides by log2(2)=1
    return sum(g / math.log2(i + 1) for i, g in enumerate(gains, start=1))


def ndcg_at_k(ranked_ids: Sequence[str], relevance_map: Mapping[str, int], k: int) -> float:
    """nDCG@k with linear graded gain = relevance grade (R-05)."""
    gains = [float(relevance_map.get(tid, 0)) for tid in ranked_ids[:k]]
    ideal = sorted((float(v) for v in relevance_map.values()), reverse=True)[:k]
    idcg = _dcg(ideal)
    if idcg == 0.0:
        return 0.0
    return _dcg(gains) / idcg


def average_precision(ranked_ids: Sequence[str], relevant_ids: set[str]) -> float:
    """Average precision over the relevant items (component of MAP)."""
    if not relevant_ids:
        return 0.0
    hits = 0
    running = 0.0
    for rank, tool_id in enumerate(ranked_ids, start=1):
        if tool_id in relevant_ids:
            hits += 1
            running += hits / rank
    return running / len(relevant_ids)
