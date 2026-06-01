"""Pydantic v2 models for D2 security scoring.

Input: ``ScanVerdictDoc`` mirrors the ``scan-verdict.schema.json`` contract
emitted by ``cmd/scan-eval`` (B1). Output: ``SecurityReport`` is an in-memory
pydantic model serialized via ``to_dict()`` whose ``security`` shape conforms to
``score-report.schema.json`` (no separate output-schema validation, mirroring
the merged A1 ``RetrievalScorer``).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Label = Literal["malicious", "benign"]
Category = Literal[
    "tool_poisoning",
    "prompt_injection",
    "shadowing",
    "rug_pull",
    "benign",
    "hard_negative",
]


class Detection(BaseModel):
    type: str
    category: str
    severity: str


class Verdict(BaseModel):
    detector: str
    flagged: bool
    max_severity: str = ""
    detections: list[Detection] = Field(default_factory=list)


class VerdictEntry(BaseModel):
    id: str
    label: Label
    category: Category
    verdicts: list[Verdict]


class ScanVerdictDoc(BaseModel):
    """One scan-eval run: detectors that ran + per-entry verdicts."""

    corpus_version: str = "unknown"
    detectors: list[str]
    entries: list[VerdictEntry]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanVerdictDoc":
        return cls.model_validate(data)


class SecurityGate(BaseModel):
    passed: bool
    fpr_ceiling: float
    recall_floor: float


class DetectorScore(BaseModel):
    detector: str
    precision: float
    recall: float
    f1: float
    fpr: float
    tp: int
    fp: int
    tn: int
    fn: int
    # mean ± tolerance bookkeeping for non-deterministic (LLM-judge) detectors
    # (FR-010 / R-B). For deterministic detectors fpr_std == 0.0.
    fpr_std: float = 0.0
    runs: int = 1
    gate: SecurityGate


class SecurityReport(BaseModel):
    corpus_version: str
    runs_averaged: int = 1
    per_detector: list[DetectorScore] = Field(default_factory=list)
    gate: SecurityGate

    def to_dict(self) -> dict[str, Any]:
        """JSON-able dict whose shape conforms to score-report.schema.json's
        ``security`` block (per-detector P/R/F1/FPR + counts + per-detector
        gate), plus an overall ``gate`` summarising pass/fail across detectors.
        """
        return self.model_dump()
