"""Pure confusion-matrix metrics for D2 security scoring (R-09, FR-005).

A detector makes a binary prediction per corpus entry: ``flagged`` (positive)
or not. Ground truth is ``label == "malicious"`` (positive). From the four
confusion counts we derive precision, recall, F1 and the false-positive rate
(FPR) — the quiet-security gate metric. No I/O, no side effects; every value is
hand-checkable in the unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Confusion:
    """The four confusion counts for a single detector over a corpus.

    - ``tp``: flagged AND malicious
    - ``fp``: flagged AND benign  (a benign description the detector tripped on)
    - ``tn``: not flagged AND benign
    - ``fn``: not flagged AND malicious  (a missed attack)
    """

    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn


def precision(c: Confusion) -> float:
    """tp / (tp + fp). 0.0 when the detector flagged nothing (no positives)."""
    denom = c.tp + c.fp
    return c.tp / denom if denom else 0.0


def recall(c: Confusion) -> float:
    """tp / (tp + fn). 0.0 when there are no malicious entries to find."""
    denom = c.tp + c.fn
    return c.tp / denom if denom else 0.0


def f1(c: Confusion) -> float:
    """Harmonic mean of precision and recall. 0.0 when either is 0."""
    p = precision(c)
    r = recall(c)
    if p + r == 0.0:
        return 0.0
    return 2 * p * r / (p + r)


def fpr(c: Confusion) -> float:
    """fp / (fp + tn) — false-positive rate. 0.0 when there are no benigns."""
    denom = c.fp + c.tn
    return c.fp / denom if denom else 0.0


def tally(flagged: bool, malicious: bool) -> Confusion:
    """The one-entry confusion contribution for a single (prediction, truth)."""
    if malicious:
        return Confusion(tp=1) if flagged else Confusion(fn=1)
    return Confusion(fp=1) if flagged else Confusion(tn=1)


def add(a: Confusion, b: Confusion) -> Confusion:
    """Sum two confusion matrices component-wise."""
    return Confusion(tp=a.tp + b.tp, fp=a.fp + b.fp, tn=a.tn + b.tn, fn=a.fn + b.fn)
