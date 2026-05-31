"""SC-006 / FR-011: the golden set is consumable unchanged as future GEPA fitness.

A future GEPA (D5) loop loads `retrieval_golden_v1.json` through the same
`GoldenSet` model and uses it as a fitness function with no transformation. This
test asserts round-trip stability: parse -> serialize -> parse yields an
identical contract document, and the parsed model exposes exactly what a fitness
function needs (queries + graded labels).
"""

from __future__ import annotations

import json

from mcp_eval.datasets.models import GoldenSet


def test_golden_set_roundtrips_unchanged(golden: GoldenSet):
    doc = golden.to_contract_dict()
    serialized = json.dumps(doc, sort_keys=True)

    # A downstream consumer (GEPA) reloads from the on-disk contract shape.
    reloaded = GoldenSet.from_contract_dict(json.loads(serialized))
    assert json.dumps(reloaded.to_contract_dict(), sort_keys=True) == serialized


def test_golden_set_exposes_fitness_inputs(golden: GoldenSet):
    # GEPA fitness needs, per query, the intent text and graded relevant labels.
    for q in golden.queries:
        assert q.query
        relevant = {lbl.tool_id: lbl.relevance for lbl in q.labels if lbl.relevance >= 1}
        assert relevant, "every fitness query needs at least one relevant tool"
