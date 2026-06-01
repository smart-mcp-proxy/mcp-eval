"""SecurityScorer tests: INV-3 canary, gate semantics, N-run averaging,
input-schema conformance (Spec 065 D2, FR-005/FR-006/FR-010, R-B).
"""

from __future__ import annotations

import copy

import pytest

from mcp_eval.security.scorer import (
    SecurityScorer,
    SecurityScoringError,
    load_verdict,
    validate_verdict_schema,
)

DETECTOR = "sensitive-data"


def _verdict(detector_flags: dict[str, bool], *, corpus_version="test-min-v1") -> dict:
    """Build a scan-verdict doc. ``detector_flags`` maps entry-id -> flagged.

    Four corpus entries mirror cmd/scan-eval/testdata/security_corpus_min.json:
    two malicious (tool_poisoning, prompt_injection) + two benign (benign,
    hard_negative).
    """
    truth = {
        "tp-aws-key-001": ("malicious", "tool_poisoning"),
        "tp-injection-001": ("malicious", "prompt_injection"),
        "benign-weather-001": ("benign", "benign"),
        "hardneg-credentials-doc-001": ("benign", "hard_negative"),
    }
    entries = []
    for eid, (label, category) in truth.items():
        flagged = detector_flags[eid]
        entries.append(
            {
                "id": eid,
                "label": label,
                "category": category,
                "verdicts": [
                    {
                        "detector": DETECTOR,
                        "flagged": flagged,
                        "max_severity": "high" if flagged else "",
                        "detections": (
                            [{"type": "api_token", "category": "cloud", "severity": "high"}]
                            if flagged
                            else []
                        ),
                    }
                ],
            }
        )
    return {"corpus_version": corpus_version, "detectors": [DETECTOR], "entries": entries}


# --- INV-3: the not-trivially-passing canary -------------------------------

# A detector that flags exactly the two malicious entries and neither benign.
_PERFECT_FLAGS = {
    "tp-aws-key-001": True,
    "tp-injection-001": True,
    "benign-weather-001": False,
    "hardneg-credentials-doc-001": False,
}


def test_inv3_true_positive_on_tool_poisoning():
    """A known tool-poisoning sample flagged ⇒ recorded as TP (recall=1)."""
    scorer = SecurityScorer(fpr_ceiling=0.10, recall_floor=0.80)
    report = scorer.score([load_verdict(_verdict(_PERFECT_FLAGS))])
    (s,) = report.per_detector
    assert s.tp == 2 and s.fn == 0
    assert s.recall == pytest.approx(1.0)
    assert s.fpr == pytest.approx(0.0)
    assert s.gate.passed is True


def test_inv3_benign_hard_negative_increments_visible_fp():
    """Flagging an attack-resembling benign hard-negative ⇒ visible FP; FPR moves
    off zero and the false positive is reflected in the score (INV-3)."""
    flags = dict(_PERFECT_FLAGS)
    flags["hardneg-credentials-doc-001"] = True  # the canary trip

    scorer = SecurityScorer(fpr_ceiling=0.10, recall_floor=0.80)
    report = scorer.score([load_verdict(_verdict(flags))])
    (s,) = report.per_detector
    assert s.fp == 1  # the hard-negative
    assert s.tn == 1
    assert s.fpr == pytest.approx(0.5)  # 1 / (1 fp + 1 tn)
    # FPR moved off the perfect-run zero — the canary is visible.
    assert s.fpr > 0.0


# --- Gate semantics (FR-006) ------------------------------------------------


def test_gate_fails_when_fpr_exceeds_ceiling():
    flags = dict(_PERFECT_FLAGS)
    flags["hardneg-credentials-doc-001"] = True  # fpr 0.5 > ceiling
    scorer = SecurityScorer(fpr_ceiling=0.10, recall_floor=0.80)
    report = scorer.score([load_verdict(_verdict(flags))])
    assert report.per_detector[0].gate.passed is False
    assert report.gate.passed is False


def test_gate_fails_when_recall_below_floor():
    flags = dict(_PERFECT_FLAGS)
    flags["tp-aws-key-001"] = False  # miss one attack -> recall 0.5 < floor
    scorer = SecurityScorer(fpr_ceiling=0.10, recall_floor=0.80)
    report = scorer.score([load_verdict(_verdict(flags))])
    s = report.per_detector[0]
    assert s.recall == pytest.approx(0.5)
    assert s.gate.passed is False


def test_gate_passes_at_boundary():
    # recall exactly at floor, fpr exactly at ceiling -> pass (>=, <=)
    scorer = SecurityScorer(fpr_ceiling=0.5, recall_floor=1.0)
    flags = dict(_PERFECT_FLAGS)
    flags["hardneg-credentials-doc-001"] = True  # fpr 0.5 == ceiling
    report = scorer.score([load_verdict(_verdict(flags))])
    s = report.per_detector[0]
    assert s.recall == pytest.approx(1.0)  # == floor
    assert s.fpr == pytest.approx(0.5)  # == ceiling
    assert s.gate.passed is True


# --- N-run averaging (FR-010, R-B) -----------------------------------------


def test_deterministic_runs_average_to_identical_mean_zero_variance():
    doc = load_verdict(_verdict(_PERFECT_FLAGS))
    scorer = SecurityScorer()
    report = scorer.score([doc, doc, doc])  # 3 identical runs
    s = report.per_detector[0]
    assert report.runs_averaged == 3
    assert s.runs == 3
    assert s.fpr == pytest.approx(0.0)
    assert s.fpr_std == pytest.approx(0.0)  # zero variance across identical runs


def test_stochastic_detector_reports_mean_with_tolerance():
    # Run A: clean (fpr 0.0). Run B: trips the hard-negative (fpr 0.5).
    run_a = load_verdict(_verdict(_PERFECT_FLAGS))
    flags_b = dict(_PERFECT_FLAGS)
    flags_b["hardneg-credentials-doc-001"] = True
    run_b = load_verdict(_verdict(flags_b))

    scorer = SecurityScorer()
    report = scorer.score([run_a, run_b])
    s = report.per_detector[0]
    assert s.fpr == pytest.approx(0.25)  # mean of 0.0 and 0.5
    assert s.fpr_std == pytest.approx(0.25)  # population std of {0.0, 0.5}
    assert s.runs == 2


# --- Input-schema conformance ----------------------------------------------


def test_valid_verdict_passes_schema():
    validate_verdict_schema(_verdict(_PERFECT_FLAGS))  # no raise


def test_malformed_verdict_rejected():
    bad = _verdict(_PERFECT_FLAGS)
    del bad["entries"][0]["label"]  # required field
    with pytest.raises(SecurityScoringError):
        validate_verdict_schema(bad)


def test_bad_label_enum_rejected():
    bad = _verdict(_PERFECT_FLAGS)
    bad["entries"][0]["label"] = "suspicious"  # not in enum
    with pytest.raises(SecurityScoringError):
        load_verdict(bad)


# --- Corpus coverage (silent-drop guard) -----------------------------------


def test_corpus_coverage_violation_raises():
    doc = load_verdict(_verdict(_PERFECT_FLAGS))
    scorer = SecurityScorer()
    extra = set(e.id for e in doc.entries) | {"tp-dropped-999"}
    with pytest.raises(SecurityScoringError, match="silent drop"):
        scorer.score([doc], corpus_ids=extra)


def test_corpus_coverage_ok_when_all_present():
    doc = load_verdict(_verdict(_PERFECT_FLAGS))
    scorer = SecurityScorer()
    ids = {e.id for e in doc.entries}
    report = scorer.score([doc], corpus_ids=ids)  # no raise
    assert report.per_detector[0].tp == 2


def test_to_dict_conforms_to_score_report_security_shape():
    report = SecurityScorer().score([load_verdict(_verdict(_PERFECT_FLAGS))])
    d = report.to_dict()
    assert set(d) >= {"runs_averaged", "per_detector", "gate"}
    det = d["per_detector"][0]
    assert {"detector", "precision", "recall", "f1", "fpr", "tp", "fp", "tn", "fn"} <= set(det)
    assert {"passed", "fpr_ceiling", "recall_floor"} <= set(det["gate"])
