"""`mcp-eval datasets` CLI sub-group: snapshot, gen-queries, validate (Spec 065 D1)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from .gen_queries import AnthropicQueryGenerator, generate_queries
from .models import Corpus, GoldenSet
from .snapshot import ToolsClient, snapshot_corpus
from .validate import DatasetValidationError, validate_golden_set

_DEFAULT_BASE_URL = os.environ.get("MCPPROXY_BASE_URL", "http://127.0.0.1:8080")
_DEFAULT_API_KEY = os.environ.get("MCPPROXY_API_KEY", "")


@click.group()
def datasets() -> None:
    """Build and validate the Spec 065 evaluation datasets."""


@datasets.command("snapshot")
@click.option("--out", type=click.Path(path_type=Path), required=True, help="Output corpus JSON path.")
@click.option("--base-url", default=_DEFAULT_BASE_URL, show_default=True)
@click.option("--api-key", default=_DEFAULT_API_KEY, help="mcpproxy API key (env MCPPROXY_API_KEY).")
@click.option("--version", "version_", default="corpus_v1", show_default=True)
@click.option("--note", default="", help="Provenance note recorded in generated_from.")
def snapshot_cmd(out: Path, base_url: str, api_key: str, version_: str, note: str) -> None:
    """Freeze the tool corpus from a running mcpproxy (GET /api/v1/tools)."""
    with ToolsClient(base_url, api_key) as client:
        corpus = snapshot_corpus(client, version=version_, note=note)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus.to_dict(), indent=2, sort_keys=True))
    click.echo(f"Wrote {len(corpus.tools)} tools -> {out}")


@datasets.command("gen-queries")
@click.option("--corpus", "corpus_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--per-tool", default=3, show_default=True, type=int)
@click.option("--model", default="claude-sonnet-4-6", show_default=True)
def gen_queries_cmd(corpus_path: Path, out: Path, per_tool: int, model: str) -> None:
    """Generate paraphrased intents per tool (R-C: never names the tool)."""
    corpus = Corpus.from_dict(json.loads(corpus_path.read_text()))
    generator = AnthropicQueryGenerator(model=model)
    golden = generate_queries(corpus, generator, per_tool=per_tool)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(golden.to_contract_dict(), indent=2, sort_keys=True))
    click.echo(f"Wrote {len(golden.queries)} queries -> {out}")
    click.echo("Next: add human-verified hard negatives, then `datasets validate`.")


@datasets.command("validate")
@click.option("--corpus", "corpus_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--golden", "golden_path", type=click.Path(exists=True, path_type=Path), required=True)
def validate_cmd(corpus_path: Path, golden_path: Path) -> None:
    """Validate a golden set against the contract schema + INV-1."""
    corpus = Corpus.from_dict(json.loads(corpus_path.read_text()))
    golden = GoldenSet.from_contract_dict(json.loads(golden_path.read_text()))
    try:
        validate_golden_set(golden, corpus)
    except DatasetValidationError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"OK: {len(golden.queries)} queries valid against {corpus.version}")
