"""Validate the D1 golden set against the contract schema + cross-entity INV-1.

Two layers:

1. **Schema** — jsonschema validation against
   ``retrieval-dataset.schema.json`` (vendored copy mirrors the source of truth
   at ``specs/065-evaluation-foundation/contracts/`` in mcpproxy-go).
2. **INV-1** — every ``labels[].tool_id`` exists in the referenced corpus
   (data-model §6, no dangling labels).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

from .models import Corpus, GoldenSet

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "retrieval-dataset.schema.json"


class DatasetValidationError(ValueError):
    """Raised when a dataset fails schema or cross-entity validation."""


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_golden_schema(doc: dict[str, Any]) -> None:
    """Validate a golden-set document against the contract JSON schema."""
    try:
        jsonschema.validate(instance=doc, schema=_schema())
    except jsonschema.ValidationError as exc:  # noqa: PERF203 - single try
        raise DatasetValidationError(f"schema violation: {exc.message}") from exc


def validate_golden_set(golden: GoldenSet, corpus: Corpus) -> None:
    """Full validation: contract schema + INV-1 (no dangling labels)."""
    validate_golden_schema(golden.to_contract_dict())

    corpus_ids = corpus.tool_ids
    dangling = sorted(
        {
            lbl.tool_id
            for q in golden.queries
            for lbl in q.labels
            if lbl.tool_id not in corpus_ids
        }
    )
    if dangling:
        raise DatasetValidationError(
            "INV-1 violation: golden-set labels reference tool_ids absent from "
            f"corpus {corpus.version!r}: {', '.join(dangling)}"
        )

    if golden.corpus_version != corpus.version:
        raise DatasetValidationError(
            f"corpus_version mismatch: golden references {golden.corpus_version!r} "
            f"but corpus is {corpus.version!r}"
        )
