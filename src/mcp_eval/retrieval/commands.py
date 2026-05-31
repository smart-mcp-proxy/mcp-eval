"""`mcp-eval retrieval` CLI command: score the D1 golden set (Spec 065)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from ..datasets.models import Corpus, GoldenSet
from . import report as report_mod
from .scorer import RetrievalScorer
from .search_client import SearchClient

_DEFAULT_BASE_URL = os.environ.get("MCPPROXY_BASE_URL", "http://127.0.0.1:8080")
_DEFAULT_API_KEY = os.environ.get("MCPPROXY_API_KEY", "")


@click.command("retrieval")
@click.option("--corpus", "corpus_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--golden", "golden_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--baseline", "baseline_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--tolerance", default=0.05, show_default=True, type=float)
@click.option("--runs", default=1, show_default=True, type=int)
@click.option("--out-dir", type=click.Path(path_type=Path), default=Path("reports/retrieval"), show_default=True)
@click.option("--base-url", default=_DEFAULT_BASE_URL, show_default=True)
@click.option("--api-key", default=_DEFAULT_API_KEY, help="mcpproxy API key (env MCPPROXY_API_KEY).")
def retrieval_cmd(
    corpus_path: Path,
    golden_path: Path,
    baseline_path: Path | None,
    tolerance: float,
    runs: int,
    out_dir: Path,
    base_url: str,
    api_key: str,
) -> None:
    """Score retrieval (Recall@k/MRR/nDCG@10/MAP) against a running mcpproxy."""
    corpus = Corpus.from_dict(json.loads(corpus_path.read_text()))
    golden = GoldenSet.from_contract_dict(json.loads(golden_path.read_text()))
    baseline = json.loads(baseline_path.read_text()) if baseline_path else None

    with SearchClient(base_url, api_key) as client:
        scorer = RetrievalScorer(client)
        report = scorer.score(
            corpus, golden, baseline=baseline, tolerance=tolerance, runs=runs,
            golden_version=golden_path.stem,
        )

    json_path = report_mod.write_json(report, out_dir / "report.json")
    html_path = report_mod.write_html(report, out_dir / "report.html")

    m = report.metrics
    click.echo("Recall@1/3/5/10: " + " ".join(f"{m.recall_at[k]:.3f}" for k in sorted(m.recall_at)))
    click.echo(f"MRR={m.mrr:.3f}  nDCG@10={m.ndcg_at_10:.3f}  MAP={m.map:.3f}")
    if baseline is not None:
        click.echo(f"Gate ({report.gate.metric}): {'PASS' if report.gate.passed else 'FAIL'} "
                   f"(value={report.gate.value:.3f} threshold={report.gate.threshold:.3f})")
    click.echo(f"Reports: {json_path} , {html_path}")

    if baseline is not None and not report.gate.passed:
        raise SystemExit(1)
