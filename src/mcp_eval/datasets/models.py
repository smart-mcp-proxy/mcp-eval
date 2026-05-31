"""Pydantic v2 models for the Spec 065 D1 datasets.

Two on-disk artifacts (data-model §1 / §2):

- **Corpus** (`corpus_v1.json`): the frozen tool universe the eval scores
  against (CN-002). Shape: ``{version, generated_from, tools[]}``.
- **GoldenSet** (`retrieval_golden_v1.json`): the labeled retrieval set. Its
  on-disk shape is governed by the contract
  ``specs/065-evaluation-foundation/contracts/retrieval-dataset.schema.json``
  (``{corpus_version, queries[]}``) — see ``to_contract_dict`` /
  ``from_contract_dict`` for the exact mapping.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

TOOL_ID_RE = re.compile(r"^[^:]+:[^:]+$")


class CorpusTool(BaseModel):
    """A single tool in the frozen corpus (data-model §1)."""

    model_config = ConfigDict(populate_by_name=True)

    tool_id: str = Field(description="<server>:<tool>")
    server: str
    tool: str
    description: str = ""
    # On disk this field is named ``schema`` (data-model §1); we alias it to
    # avoid shadowing pydantic's BaseModel.schema attribute.
    json_schema: dict[str, Any] | None = Field(default=None, alias="schema")

    @field_validator("tool_id")
    @classmethod
    def _check_tool_id(cls, v: str) -> str:
        if not TOOL_ID_RE.match(v):
            raise ValueError(f"tool_id must be '<server>:<tool>', got {v!r}")
        return v

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class Corpus(BaseModel):
    """The frozen tool corpus (immutable once committed — FR-012)."""

    version: str
    generated_from: dict[str, Any] = Field(default_factory=dict)
    tools: list[CorpusTool]

    @field_validator("tools")
    @classmethod
    def _unique_tool_ids(cls, tools: list[CorpusTool]) -> list[CorpusTool]:
        seen: set[str] = set()
        for t in tools:
            if t.tool_id in seen:
                raise ValueError(f"duplicate tool_id in corpus: {t.tool_id}")
            seen.add(t.tool_id)
        return tools

    @property
    def tool_ids(self) -> set[str]:
        return {t.tool_id for t in self.tools}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_from": self.generated_from,
            "tools": [t.to_dict() for t in self.tools],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Corpus":
        return cls.model_validate(data)


class Label(BaseModel):
    """A graded relevance label for a (query, tool) pair (data-model §2)."""

    tool_id: str
    relevance: int = Field(description="2=primary, 1=acceptable, 0=irrelevant")

    @field_validator("tool_id")
    @classmethod
    def _check_tool_id(cls, v: str) -> str:
        if not TOOL_ID_RE.match(v):
            raise ValueError(f"label tool_id must be '<server>:<tool>', got {v!r}")
        return v

    @field_validator("relevance")
    @classmethod
    def _check_relevance(cls, v: int) -> int:
        if v not in (0, 1, 2):
            raise ValueError(f"relevance must be one of 0,1,2, got {v}")
        return v


class Query(BaseModel):
    """A paraphrased user intent with graded labels (R-C: never names the tool)."""

    id: str
    query: str
    labels: list[Label] = Field(min_length=1)
    notes: str | None = None


class GoldenSet(BaseModel):
    """The D1 retrieval golden set — contract: retrieval-dataset.schema.json."""

    corpus_version: str
    queries: list[Query] = Field(min_length=1)

    def to_contract_dict(self) -> dict[str, Any]:
        """Serialize to the exact on-disk contract shape."""
        out: dict[str, Any] = {"corpus_version": self.corpus_version, "queries": []}
        for q in self.queries:
            entry: dict[str, Any] = {
                "id": q.id,
                "query": q.query,
                "labels": [
                    {"tool_id": lbl.tool_id, "relevance": lbl.relevance} for lbl in q.labels
                ],
            }
            if q.notes is not None:
                entry["notes"] = q.notes
            out["queries"].append(entry)
        return out

    @classmethod
    def from_contract_dict(cls, data: dict[str, Any]) -> "GoldenSet":
        return cls.model_validate(data)
