"""Render a SecurityReport to JSON + a self-contained HTML file (NOT committed).

Reports are run artifacts only (CN-003 / repo rule: never commit reports). The
JSON shape conforms to the ``security`` block of ``score-report.schema.json``.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .models import SecurityReport


def write_json(report: SecurityReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"security": report.to_dict()}, indent=2, sort_keys=True))
    return path


def _detector_rows(report: SecurityReport) -> str:
    rows = []
    for s in report.per_detector:
        gate_class = "pass" if s.gate.passed else "fail"
        gate_label = "PASS" if s.gate.passed else "FAIL"
        tol = f" ±{s.fpr_std:.3f}" if s.runs > 1 else ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(s.detector)}</td>"
            f"<td>{s.precision:.3f}</td>"
            f"<td>{s.recall:.3f}</td>"
            f"<td>{s.f1:.3f}</td>"
            f"<td>{s.fpr:.3f}{tol}</td>"
            f"<td>{s.tp}/{s.fp}/{s.tn}/{s.fn}</td>"
            f'<td class="{gate_class}">{gate_label}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def write_html(report: SecurityReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    gate = report.gate
    gate_class = "pass" if gate.passed else "fail"
    gate_label = "PASS" if gate.passed else "FAIL"
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>D2 Security Report</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem;color:#1a1a1a}}
 h1{{font-size:1.4rem}} table{{border-collapse:collapse;margin:1rem 0}}
 td,th{{border:1px solid #ddd;padding:.4rem .8rem;text-align:left}}
 th{{background:#f5f5f7}} .pass{{color:#137333;font-weight:600}} .fail{{color:#c5221f;font-weight:600}}
 .meta{{color:#666;font-size:.9rem}}
</style></head><body>
<h1>D2 Security-Detector Report</h1>
<p class="meta">corpus={html.escape(report.corpus_version)} ·
 detectors={len(report.per_detector)} · runs_averaged={report.runs_averaged}</p>
<p>Overall gate (fpr ≤ {gate.fpr_ceiling} AND recall ≥ {gate.recall_floor}):
 <span class="{gate_class}">{gate_label}</span></p>
<h2>Per-detector metrics</h2>
<table><tr><th>detector</th><th>precision</th><th>recall</th><th>F1</th>
 <th>FPR</th><th>TP/FP/TN/FN</th><th>gate</th></tr>
{_detector_rows(report)}
</table>
</body></html>"""
    path.write_text(doc)
    return path
