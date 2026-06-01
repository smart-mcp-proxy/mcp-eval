"""`mcp-eval security` CLI command: score scan-eval verdicts (Spec 065 D2).

Consumes one or more scan-verdict JSON files emitted by ``cmd/scan-eval`` (B1),
computes per-detector P/R/F1/FPR, applies the FPR-ceiling + recall-floor gate,
and writes a JSON + HTML report. Multiple ``--verdicts`` files are treated as
N runs and averaged (R-B) — use this for non-deterministic detectors.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from . import report as report_mod
from .scorer import SecurityScorer, load_verdict


def _load_corpus_ids(corpus_path: Path | None) -> set[str] | None:
    if corpus_path is None:
        return None
    data = json.loads(corpus_path.read_text())
    entries = data.get("entries", [])
    return {e["id"] for e in entries if "id" in e}


@click.command("security")
@click.option(
    "--verdicts",
    "verdict_paths",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    multiple=True,
    help="scan-verdict JSON file(s) from cmd/scan-eval. Repeat for N runs (averaged).",
)
@click.option(
    "--corpus",
    "corpus_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="security_corpus_v1.json — asserts id-coverage (catches silent drops).",
)
@click.option("--fpr-ceiling", default=0.10, show_default=True, type=float)
@click.option("--recall-floor", default=0.80, show_default=True, type=float)
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=Path("reports/security"),
    show_default=True,
)
def security_cmd(
    verdict_paths: tuple[Path, ...],
    corpus_path: Path | None,
    fpr_ceiling: float,
    recall_floor: float,
    out_dir: Path,
) -> None:
    """Score security detectors (precision/recall/F1/FPR + gate) from verdicts."""
    corpus_ids = _load_corpus_ids(corpus_path)
    docs = [load_verdict(json.loads(p.read_text())) for p in verdict_paths]

    scorer = SecurityScorer(fpr_ceiling=fpr_ceiling, recall_floor=recall_floor)
    report = scorer.score(docs, corpus_ids=corpus_ids)

    json_path = report_mod.write_json(report, out_dir / "report.json")
    html_path = report_mod.write_html(report, out_dir / "report.html")

    for s in report.per_detector:
        click.echo(
            f"{s.detector}: P={s.precision:.3f} R={s.recall:.3f} "
            f"F1={s.f1:.3f} FPR={s.fpr:.3f} "
            f"[{'PASS' if s.gate.passed else 'FAIL'}]"
        )
    click.echo(
        f"Overall gate (fpr<={fpr_ceiling} AND recall>={recall_floor}): "
        f"{'PASS' if report.gate.passed else 'FAIL'}"
    )
    click.echo(f"Reports: {json_path} , {html_path}")

    if not report.gate.passed:
        raise SystemExit(1)
