"""Dataset validation: jsonschema (contract) + INV-1 (no dangling labels)."""

from __future__ import annotations

import pytest

from mcp_eval.datasets.models import Corpus, GoldenSet, Label, Query
from mcp_eval.datasets.validate import (
    DatasetValidationError,
    validate_golden_schema,
    validate_golden_set,
)


def test_schema_accepts_valid_golden(golden: GoldenSet):
    # Should not raise.
    validate_golden_schema(golden.to_contract_dict())


def test_schema_rejects_bad_relevance():
    bad = {
        "corpus_version": "c",
        "queries": [
            {"id": "q1", "query": "x", "labels": [{"tool_id": "a:b", "relevance": 3}]}
        ],
    }
    with pytest.raises(DatasetValidationError):
        validate_golden_schema(bad)


def test_schema_rejects_bad_tool_id_pattern():
    bad = {
        "corpus_version": "c",
        "queries": [
            {"id": "q1", "query": "x", "labels": [{"tool_id": "no-colon", "relevance": 1}]}
        ],
    }
    with pytest.raises(DatasetValidationError):
        validate_golden_schema(bad)


def test_inv1_dangling_label_fails(corpus: Corpus):
    """INV-1: every golden-set tool_id must exist in the corpus."""
    dangling = GoldenSet(
        corpus_version=corpus.version,
        queries=[
            Query(id="q1", query="do a thing", labels=[Label(tool_id="ghost:tool", relevance=2)])
        ],
    )
    with pytest.raises(DatasetValidationError) as exc:
        validate_golden_set(dangling, corpus)
    assert "ghost:tool" in str(exc.value)


def test_validate_golden_set_passes_for_consistent_pair(corpus: Corpus, golden: GoldenSet):
    # Both schema and INV-1 hold -> no raise.
    validate_golden_set(golden, corpus)
