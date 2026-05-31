"""Render a RetrievalReport to JSON + a self-contained HTML file (NOT committed).

Reports are run artifacts only (CN-003 / repo rule: never commit reports).
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .scorer import RetrievalReport


def write_json(report: RetrievalReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return path


def _metrics_rows(report: RetrievalReport) -> str:
    m = report.metrics
    rows = []
    for k in sorted(m.recall_at):
        delta = report.baseline_delta.get(f"recall_at_{k}")
        rows.append(_row(f"Recall@{k}", m.recall_at[k], delta))
    rows.append(_row("MRR", m.mrr, report.baseline_delta.get("mrr")))
    rows.append(_row("nDCG@10", m.ndcg_at_10, report.baseline_delta.get("ndcg_at_10")))
    rows.append(_row("MAP", m.map, report.baseline_delta.get("map")))
    return "\n".join(rows)


def _row(name: str, value: float, delta: float | None) -> str:
    d = "" if delta is None else f"{delta:+.4f}"
    return (
        f"<tr><td>{html.escape(name)}</td><td>{value:.4f}</td><td>{d}</td></tr>"
    )


def _per_query_rows(report: RetrievalReport) -> str:
    rows = []
    for pq in report.per_query:
        rows.append(
            "<tr>"
            f"<td>{html.escape(pq.id)}</td>"
            f"<td>{html.escape(pq.query)}</td>"
            f"<td>{pq.recall_at.get(5, 0):.3f}</td>"
            f"<td>{pq.mrr:.3f}</td>"
            f"<td>{pq.ndcg_at_10:.3f}</td>"
            f"<td>{html.escape(', '.join(pq.relevant))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def write_html(report: RetrievalReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    gate = report.gate
    gate_class = "pass" if gate.passed else "fail"
    gate_label = "PASS" if gate.passed else "FAIL"
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>D1 Retrieval Report</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem;color:#1a1a1a}}
 h1{{font-size:1.4rem}} table{{border-collapse:collapse;margin:1rem 0}}
 td,th{{border:1px solid #ddd;padding:.4rem .8rem;text-align:left}}
 th{{background:#f5f5f7}} .pass{{color:#137333;font-weight:600}} .fail{{color:#c5221f;font-weight:600}}
 .meta{{color:#666;font-size:.9rem}}
</style></head><body>
<h1>D1 Tool-Retrieval Report</h1>
<p class="meta">corpus={html.escape(report.corpus_version)} ·
 golden={html.escape(report.golden_version)} ·
 queries={len(report.per_query)} · runs_averaged={report.runs_averaged}</p>
<p>Gate ({html.escape(gate.metric)}): <span class="{gate_class}">{gate_label}</span>
 value={gate.value if gate.value is None else f'{gate.value:.4f}'}
 threshold={gate.threshold if gate.threshold is None else f'{gate.threshold:.4f}'}
 tolerance={gate.tolerance}</p>
<h2>Aggregate metrics</h2>
<table><tr><th>Metric</th><th>Value</th><th>Δ baseline</th></tr>
{_metrics_rows(report)}
</table>
<h2>Per-query</h2>
<table><tr><th>id</th><th>query</th><th>R@5</th><th>MRR</th><th>nDCG@10</th><th>relevant</th></tr>
{_per_query_rows(report)}
</table>
</body></html>"""
    path.write_text(doc)
    return path
