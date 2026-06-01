"""SecurityScorer — derive per-detector P/R/F1/FPR from scan-eval verdicts.

The scorer consumes one or more scan-verdict documents (B1), validates each
against the **vendored** ``scan-verdict.schema.json`` input contract, aggregates
the confusion matrix per detector (prediction-positive = ``flagged``;
truth-positive = ``label == "malicious"``), and applies a configurable
FPR-ceiling + recall-floor gate (FR-006).

Non-deterministic detectors (LLM-judge) are averaged over N runs and reported as
mean with a standard-deviation tolerance (FR-010, R-B). Deterministic
(rule-based) detectors gate tightly at N=1.

The optional ``corpus_ids`` set lets the scorer assert id-coverage against the
frozen security corpus (B2) — a silently dropped entry is a scoring bug, not a
free pass (mirrors INV-2 in the retrieval scorer).
"""

from __future__ import annotations

import json
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

from . import metrics as M
from .models import (
    DetectorScore,
    ScanVerdictDoc,
    SecurityGate,
    SecurityReport,
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "datasets"
    / "schemas"
    / "scan-verdict.schema.json"
)


class SecurityScoringError(ValueError):
    """Raised on schema violation or corpus id-coverage mismatch."""


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_verdict_schema(doc: dict[str, Any]) -> None:
    """Validate a raw verdict document against the vendored input contract."""
    try:
        jsonschema.validate(instance=doc, schema=_schema())
    except jsonschema.ValidationError as exc:
        raise SecurityScoringError(f"scan-verdict schema violation: {exc.message}") from exc


def load_verdict(data: dict[str, Any]) -> ScanVerdictDoc:
    """Schema-validate then parse a raw verdict dict into a model."""
    validate_verdict_schema(data)
    return ScanVerdictDoc.from_dict(data)


def _confusion_for_run(doc: ScanVerdictDoc) -> dict[str, M.Confusion]:
    """Per-detector confusion matrix for a single verdict document."""
    per_detector: dict[str, M.Confusion] = {d: M.Confusion() for d in doc.detectors}
    for entry in doc.entries:
        malicious = entry.label == "malicious"
        for v in entry.verdicts:
            contrib = M.tally(v.flagged, malicious)
            current = per_detector.get(v.detector, M.Confusion())
            per_detector[v.detector] = M.add(current, contrib)
    return per_detector


def _assert_corpus_coverage(doc: ScanVerdictDoc, corpus_ids: set[str]) -> None:
    seen = {e.id for e in doc.entries}
    missing = sorted(corpus_ids - seen)
    if missing:
        raise SecurityScoringError(
            "corpus coverage violation: verdict omits corpus entries "
            f"{', '.join(missing)} (silent drop)"
        )


class SecurityScorer:
    def __init__(self, *, fpr_ceiling: float = 0.10, recall_floor: float = 0.80):
        self._fpr_ceiling = fpr_ceiling
        self._recall_floor = recall_floor

    def score(
        self,
        verdict_docs: list[ScanVerdictDoc],
        *,
        corpus_ids: set[str] | None = None,
    ) -> SecurityReport:
        """Aggregate one or more runs into a per-detector security report.

        ``verdict_docs`` with length 1 → deterministic gate (N=1). With length
        > 1 → the runs are averaged per detector (mean P/R/F1/FPR) and ``fpr``
        carries a population std as its tolerance (R-B).
        """
        if not verdict_docs:
            raise SecurityScoringError("no verdict documents supplied")

        corpus_version = verdict_docs[0].corpus_version
        runs = len(verdict_docs)

        # detector -> list of per-run confusion matrices (and derived metrics)
        per_run_conf: dict[str, list[M.Confusion]] = {}
        for doc in verdict_docs:
            if corpus_ids is not None:
                _assert_corpus_coverage(doc, corpus_ids)
            for det, conf in _confusion_for_run(doc).items():
                per_run_conf.setdefault(det, []).append(conf)

        scores: list[DetectorScore] = []
        for det in sorted(per_run_conf):
            confs = per_run_conf[det]
            scores.append(self._score_detector(det, confs))

        overall = SecurityGate(
            passed=all(s.gate.passed for s in scores) if scores else True,
            fpr_ceiling=self._fpr_ceiling,
            recall_floor=self._recall_floor,
        )
        return SecurityReport(
            corpus_version=corpus_version,
            runs_averaged=runs,
            per_detector=scores,
            gate=overall,
        )

    def _score_detector(self, detector: str, confs: list[M.Confusion]) -> DetectorScore:
        runs = len(confs)
        precisions = [M.precision(c) for c in confs]
        recalls = [M.recall(c) for c in confs]
        f1s = [M.f1(c) for c in confs]
        fprs = [M.fpr(c) for c in confs]

        # Mean across runs; for N=1 this is just the single run (R-B no-op).
        mean_p = statistics.fmean(precisions)
        mean_r = statistics.fmean(recalls)
        mean_f1 = statistics.fmean(f1s)
        mean_fpr = statistics.fmean(fprs)
        fpr_std = statistics.pstdev(fprs) if runs > 1 else 0.0

        # Confusion counts reported are the per-run mean rounded to int (display
        # only; the gate uses the averaged rate metrics, not the counts).
        agg = confs[0]
        for c in confs[1:]:
            agg = M.add(agg, c)

        gate = SecurityGate(
            passed=mean_fpr <= self._fpr_ceiling and mean_r >= self._recall_floor,
            fpr_ceiling=self._fpr_ceiling,
            recall_floor=self._recall_floor,
        )
        return DetectorScore(
            detector=detector,
            precision=mean_p,
            recall=mean_r,
            f1=mean_f1,
            fpr=mean_fpr,
            tp=agg.tp // runs,
            fp=agg.fp // runs,
            tn=agg.tn // runs,
            fn=agg.fn // runs,
            fpr_std=fpr_std,
            runs=runs,
            gate=gate,
        )
