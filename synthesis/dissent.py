# novel-to-this-project — Phase 5 deterministic dissent computation (LLM-07 / Pattern #7 — project-original).
"""synthesis.dissent — Python-computed dissent rule per LLM-07 + Pattern #7.

The dissent rule is structural: "≥1 persona disagrees by ≥30 confidence
points on the OPPOSITE direction from the signed-weighted-vote majority".
This is a deterministic computation over 6 AgentSignals; Python is the
right tool. Pre-computed dissent_summary is passed to the synthesizer
prompt; the synthesizer renders it verbatim into TickerDecision.dissent.

Three reasons to compute in Python (not the LLM) per 05-RESEARCH.md
Pattern #7:
  1. Determinism — testable, reproducible, debuggable. A Python
     computation over 6 AgentSignals has a knowable contract surface;
     the LLM doing the same job would have ad-hoc tie-breaking.
  2. No hallucination risk — Pydantic constrained-decoding only
     validates that DissentSection.dissenting_persona is `str | None`,
     NOT that the string is one of the 6 valid persona IDs. A typo'd
     "warrenbufett" would pass schema validation but break Phase 6
     frontend rendering. Python guarantees a valid persona_id from
     the actual AgentSignal slate.
  3. Tie-break specificity — the user-locked rule (highest confidence
     wins; alphabetical analyst_id breaks ties) is precise; LLM
     tie-breaking is non-deterministic.

Per 05-RESEARCH.md Anti-Pattern at line 1189: dissent uses MAJORITY
DIRECTION (signed-weighted vote, factoring confidence) NOT MAJORITY
VERDICT (mode). Reason: a 4-bullish (conf 60 each) + 2-strong_bullish
(conf 90 each) slate has direction_score=+(4*60)+(2*90)=+420 — the
magnitude of conviction matters, not just the count.

Public surface (consumed by synthesis/synthesizer.py at Wave 4):
    VERDICT_TO_DIRECTION  — 5-key map (strong_bullish/bullish→+1; neutral→0;
                             bearish/strong_bearish→-1)
    DISSENT_THRESHOLD     — 30 (LLM-07 boundary inclusive; ≥30 triggers)
    compute_dissent(...)  — returns (Optional[persona_id], summary_str)
"""
from __future__ import annotations

from typing import Optional

from analysts.signals import AgentSignal, Verdict

# ---------------------------------------------------------------------------
# Module constants — single source of truth for the dissent computation.
# ---------------------------------------------------------------------------

VERDICT_TO_DIRECTION: dict[Verdict, int] = {
    "strong_bearish": -1,
    "bearish": -1,
    "neutral": 0,
    "bullish": 1,
    "strong_bullish": 1,
}

# LLM-07 boundary inclusive — confidence == 30 on the opposite direction
# triggers the dissent surface. Tested explicitly by both the inclusive-at-30
# and exclusive-at-29 cases in test_dissent.py.
DISSENT_THRESHOLD: int = 30

# Defensive cap on the summary string — matches DissentSection.dissent_summary
# max_length=500 (synthesis/decision.py). Keeps Pydantic validation from
# rejecting a synthesizer call when the dissenter has unusually verbose
# evidence strings.
_SUMMARY_MAX_LEN: int = 500


def compute_dissent(
    persona_signals: list[AgentSignal],
) -> tuple[Optional[str], str]:
    """Return (dissenting_persona_id, dissent_summary).

    Returns (None, "") in any of these degenerate cases:
      * <2 valid persona signals (data_unavailable filters; confidence>0
        also filters — a confidence-0 signal can't define a "majority").
      * direction_score == 0 (zero-sum across the valid signals; no clear
        majority direction).
      * No opposite-direction personas at confidence ≥ DISSENT_THRESHOLD.

    When ≥1 dissenter qualifies:
      * Tie-break primary: highest confidence wins.
      * Tie-break secondary: alphabetical analyst_id (deterministic;
        tested by burry vs munger at conf=70).

    Summary format: "<analyst_id> dissents (<verdict>, conf=<N>): <evidence>"
    where <evidence> is the joined-by-"; " concatenation of the dissenter's
    top-3 evidence strings; truncated to 500 chars defensively.

    Parameters
    ----------
    persona_signals
        List of AgentSignal objects from the 6-persona slate. Order does
        NOT matter for the computation (signed-weighted-vote is order-
        invariant); the returned dissenter is whichever qualifies after
        tie-break.

    Returns
    -------
    tuple[Optional[str], str]
        (dissenting_persona_id, dissent_summary). persona_id is exactly one
        of the 6 PersonaId Literal values OR None; summary is "" when
        persona_id is None and ≤500 chars when persona_id is non-None.
    """
    # Filter to "valid" persona signals — those that contribute to the
    # majority direction calculation. data_unavailable=True signals are
    # filtered (they carry verdict='neutral' + confidence=0 by schema
    # invariant); confidence=0 also filters because direction * 0 = 0
    # contributes nothing to the signed-weighted vote.
    valid = [
        s for s in persona_signals
        if not s.data_unavailable and s.confidence > 0
    ]
    if len(valid) < 2:
        # Can't define "majority direction" from fewer than 2 valid signals.
        # An all-data_unavailable slate AND a single-valid + 5-data_unavailable
        # slate both land here.
        return None, ""

    # Signed-weighted vote: sum(direction * confidence) — magnitude matters.
    direction_score = sum(
        VERDICT_TO_DIRECTION[s.verdict] * s.confidence for s in valid
    )
    if direction_score == 0:
        # Zero-sum: 3 bullish-conf-50 + 3 bearish-conf-50 → no clear majority.
        # Returning (None, '') matches the "split signals" intuition — there's
        # no single direction to dissent FROM.
        return None, ""

    majority_dir = 1 if direction_score > 0 else -1

    # Dissenters are valid signals whose direction is OPPOSITE the majority
    # AND whose confidence meets the LLM-07 threshold. Neutral verdicts
    # (direction=0) are NOT opposite to either +1 or -1 → they never dissent.
    dissenters = [
        s for s in valid
        if VERDICT_TO_DIRECTION[s.verdict] == -majority_dir
        and s.confidence >= DISSENT_THRESHOLD
    ]
    if not dissenters:
        return None, ""

    # Tie-break: max() with composite key.
    #   * Primary: confidence (higher wins via natural max).
    #   * Secondary: _neg_alpha(analyst_id) — tuple of negated codepoints
    #     so a "smaller" string sorts LATER under max — i.e., the
    #     ALPHABETICALLY-FIRST analyst_id wins ties.
    dissenter = max(
        dissenters,
        key=lambda s: (s.confidence, _neg_alpha(s.analyst_id)),
    )

    # Build the locked summary format.
    evidence_str = (
        "; ".join(dissenter.evidence[:3])
        if dissenter.evidence
        else ""
    )
    summary = (
        f"{dissenter.analyst_id} dissents "
        f"({dissenter.verdict}, conf={dissenter.confidence}): "
        f"{evidence_str}"
    )

    # Defensive truncation — DissentSection.dissent_summary max_length=500.
    return dissenter.analyst_id, summary[:_SUMMARY_MAX_LEN]


def _neg_alpha(analyst_id: str) -> tuple[int, ...]:
    """Tuple-of-negated-codepoints sort key — smaller string sorts LATER.

    This makes `max(...)` with this key as a secondary tie-breaker pick the
    ALPHABETICALLY-FIRST analyst_id. Equivalent to `sorted(..., key=alpha)[0]`
    but composes cleanly with a `max` over a multi-key tuple
    `(confidence, _neg_alpha(analyst_id))` — confidence-then-alphabetical
    in a single max() call.

    Example: "burry" < "munger" alphabetically. Negating per-character
    codepoints flips the ordering so under max(), `_neg_alpha("burry")` >
    `_neg_alpha("munger")` (because each negated codepoint of "burry" is
    "less negative" than the corresponding codepoint of "munger" at the
    first differing position — wait, the opposite; let's verify):

      ord('b') = 98; ord('m') = 109
      _neg_alpha("burry")[0] = -98
      _neg_alpha("munger")[0] = -109
      -98 > -109 → "burry" wins under max()  ✓

    So under max(), the alphabetically-first id wins, which is the locked
    tie-break behavior.
    """
    return tuple(-ord(c) for c in analyst_id)
