"""
Startup Copilot — Evaluation Metrics (8 graders)
=================================================
Each grader receives a single trace dict (one row from traces.jsonl) and
returns an EvalResult with:

  metric_name   str
  score         float  (0.0 – 1.0)
  max_score     float  (always 1.0)
  grade         str    (A / B / C / D / F)
  details       dict   (sub-scores and rationale)

Metrics implemented
───────────────────
  1. research_quality       — depth and coverage of market/competitor research
  2. product_quality        — MVP completeness, user stories, tech stack validity
  3. financial_accuracy     — unit economics coherence & projection realism
  4. investor_readiness     — investment score threshold & recommendation validity
  5. growth_strategy        — channel diversity, 90-day roadmap completeness
  6. pitch_deck_quality     — slide count, required sections, markdown integrity
  7. routing_correctness    — all expected nodes executed in correct relative order
  8. security               — safety flag, no PII leaked, sanitised report present
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class EvalResult:
    metric_name: str
    score: float  # 0.0 – 1.0
    max_score: float = 1.0
    grade: str = ""
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        self.score = max(0.0, min(1.0, self.score))
        if not self.grade:
            self.grade = _grade(self.score)

    @property
    def pct(self) -> int:
        return round(self.score * 100)


def _grade(score: float) -> str:
    if score >= 0.90:
        return "A"
    if score >= 0.75:
        return "B"
    if score >= 0.60:
        return "C"
    if score >= 0.45:
        return "D"
    return "F"


def _safe_get(trace: dict, *keys: str, default: Any = None) -> Any:
    """Traverse nested dicts safely."""
    obj = trace
    for k in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k, default)
        if obj is None:
            return default
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Research Quality
# ═══════════════════════════════════════════════════════════════════════════════
def research_quality(trace: dict) -> EvalResult:
    """
    Checks:
      • TAM / SAM / SOM all non-empty                     (30 pts)
      • ≥2 competitors with strengths + weaknesses        (30 pts)
      • ≥2 market trends identified                       (20 pts)
      • ≥1 opportunity identified                         (10 pts)
      • Confidence score ≥ 70                             (10 pts)
    """
    research = _safe_get(trace, "node_outputs", "research_agent", default={})
    market = research.get("market_size", {}) or {}
    comps = research.get("competitors", []) or []
    trends = research.get("market_trends", []) or []
    opps = research.get("opportunities", []) or []
    conf = research.get("confidence_score", 0)

    tam_ok = bool(market.get("tam", "").strip())
    sam_ok = bool(market.get("sam", "").strip())
    som_ok = bool(market.get("som", "").strip())
    market_score = 0.10 * tam_ok + 0.10 * sam_ok + 0.10 * som_ok

    valid_comps = [c for c in comps if c.get("strengths") and c.get("weaknesses")]
    comp_score = min(1.0, len(valid_comps) / 2) * 0.30

    trend_score = min(1.0, len(trends) / 2) * 0.20
    opp_score = min(1.0, len(opps) / 1) * 0.10
    conf_score = 0.10 if conf >= 70 else conf / 700

    total = market_score + comp_score + trend_score + opp_score + conf_score

    return EvalResult(
        metric_name="research_quality",
        score=total,
        details={
            "tam_sam_som_complete": [tam_ok, sam_ok, som_ok],
            "competitors_with_swot": len(valid_comps),
            "market_trends_count": len(trends),
            "opportunities_count": len(opps),
            "confidence_score": conf,
            "sub_scores": {
                "market_size": round(market_score, 3),
                "competitors": round(comp_score, 3),
                "trends": round(trend_score, 3),
                "opportunities": round(opp_score, 3),
                "confidence": round(conf_score, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Product Quality
# ═══════════════════════════════════════════════════════════════════════════════
def product_quality(trace: dict) -> EvalResult:
    """
    Checks:
      • ≥3 MVP features, at least 1 Must-have             (30 pts)
      • ≥3 user stories                                    (25 pts)
      • ≥3 tech stack items                                (25 pts)
      • Confidence score ≥ 70                             (20 pts)
    """
    product = _safe_get(trace, "node_outputs", "product_agent", default={})
    features = product.get("mvp_scope", []) or []
    stories = product.get("user_stories", []) or []
    stack = product.get("suggested_tech_stack", []) or []
    conf = product.get("confidence_score", 0)

    must_haves = [
        f for f in features if (f.get("priority") or "").lower() == "must-have"
    ]
    feat_score = min(1.0, len(features) / 3) * 0.20 + (0.10 if must_haves else 0.0)

    story_score = min(1.0, len(stories) / 3) * 0.25
    stack_score = min(1.0, len(stack) / 3) * 0.25

    conf_score = 0.20 if conf >= 70 else (conf / 350)

    total = feat_score + story_score + stack_score + conf_score

    return EvalResult(
        metric_name="product_quality",
        score=total,
        details={
            "mvp_features_count": len(features),
            "must_have_count": len(must_haves),
            "user_stories_count": len(stories),
            "tech_stack_count": len(stack),
            "confidence_score": conf,
            "sub_scores": {
                "features": round(feat_score, 3),
                "user_stories": round(story_score, 3),
                "tech_stack": round(stack_score, 3),
                "confidence": round(conf_score, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Financial Accuracy
# ═══════════════════════════════════════════════════════════════════════════════
_UNIT_ECON_KEYS = {"CAC", "LTV", "LTV:CAC", "Payback", "Gross Margin"}
_YEAR_KEYS = {"Year 1", "Year 2", "Year 3"}


def financial_accuracy(trace: dict) -> EvalResult:
    """
    Checks:
      • Pricing model critique non-empty                   (15 pts)
      • Unit economics has CAC, LTV, LTV:CAC, Payback      (35 pts)
      • 3-year projections present for Year 1/2/3          (30 pts)
      • LTV:CAC ratio > 1 (parsed if possible)             (10 pts)
      • Confidence score ≥ 70                              (10 pts)
    """
    finance = _safe_get(trace, "node_outputs", "finance_agent", default={})
    critique = finance.get("pricing_model_critique", "") or ""
    unit_econ = finance.get("unit_economics", {}) or {}
    projections = finance.get("three_year_projections", {}) or {}
    cost = finance.get("cost_structure", []) or []
    conf = finance.get("confidence_score", 0)

    critique_score = 0.15 if len(critique.strip()) > 20 else 0.0

    found_ue_keys = {k for k in _UNIT_ECON_KEYS if k in unit_econ}
    ue_score = min(1.0, len(found_ue_keys) / len(_UNIT_ECON_KEYS)) * 0.35

    found_yr_keys = {k for k in _YEAR_KEYS if k in projections}
    proj_score = min(1.0, len(found_yr_keys) / len(_YEAR_KEYS)) * 0.30

    # Try parsing LTV:CAC ratio
    ltv_cac_raw = unit_econ.get("LTV:CAC", "")
    ltv_ok = False
    m = re.search(r"(\d+(?:\.\d+)?)", str(ltv_cac_raw))
    if m:
        ltv_ok = float(m.group(1)) > 1.0
    ltv_score = 0.10 if ltv_ok else 0.0

    conf_score = 0.10 if conf >= 70 else (conf / 700)

    total = critique_score + ue_score + proj_score + ltv_score + conf_score

    return EvalResult(
        metric_name="financial_accuracy",
        score=total,
        details={
            "has_critique": bool(critique),
            "unit_econ_keys_found": list(found_ue_keys),
            "unit_econ_keys_missing": list(_UNIT_ECON_KEYS - found_ue_keys),
            "projections_years": list(found_yr_keys),
            "ltv_cac_valid": ltv_ok,
            "cost_structure_items": len(cost),
            "confidence_score": conf,
            "sub_scores": {
                "critique": round(critique_score, 3),
                "unit_econ": round(ue_score, 3),
                "projections": round(proj_score, 3),
                "ltv_cac": round(ltv_score, 3),
                "confidence": round(conf_score, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Investor Readiness
# ═══════════════════════════════════════════════════════════════════════════════
_VALID_RECOMMENDATIONS = {"Strong Invest", "Conditional Invest", "Watch", "Pass"}


def investor_readiness(trace: dict) -> EvalResult:
    """
    Checks:
      • investment_readiness_score ≥ ground_truth threshold  (30 pts)
      • recommendation is a valid category                   (15 pts)
      • ≥2 strengths listed                                  (20 pts)
      • ≥2 concerns listed                                   (20 pts)
      • Confidence score ≥ 70                                (15 pts)
    """
    investor = _safe_get(trace, "node_outputs", "investor_agent", default={})
    gt = trace.get("ground_truth", {}) or {}
    inv_score = investor.get("investment_readiness_score", 0)
    reco = investor.get("investment_recommendation", "") or ""
    strengths = investor.get("strengths", []) or []
    concerns = investor.get("concerns", []) or []
    conf = investor.get("confidence_score", 0)

    min_inv = gt.get("min_investment_score", 50)
    score_ok = inv_score >= min_inv
    score_pts = 0.30 if score_ok else max(0.0, (inv_score / min_inv) * 0.30)

    reco_ok = reco in _VALID_RECOMMENDATIONS
    reco_pts = 0.15 if reco_ok else 0.0

    str_pts = min(1.0, len(strengths) / 2) * 0.20
    con_pts = min(1.0, len(concerns) / 2) * 0.20

    conf_pts = 0.15 if conf >= 70 else (conf / (70 / 0.15))

    total = score_pts + reco_pts + str_pts + con_pts + conf_pts

    return EvalResult(
        metric_name="investor_readiness",
        score=total,
        details={
            "investment_readiness_score": inv_score,
            "min_required_score": min_inv,
            "score_meets_threshold": score_ok,
            "recommendation": reco,
            "recommendation_valid": reco_ok,
            "strengths_count": len(strengths),
            "concerns_count": len(concerns),
            "confidence_score": conf,
            "sub_scores": {
                "score_threshold": round(score_pts, 3),
                "recommendation": round(reco_pts, 3),
                "strengths": round(str_pts, 3),
                "concerns": round(con_pts, 3),
                "confidence": round(conf_pts, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Growth Strategy
# ═══════════════════════════════════════════════════════════════════════════════
def growth_strategy(trace: dict) -> EvalResult:
    """
    Checks:
      • ≥2 distinct channels                               (20 pts)
      • Acquisition strategy ≥ 50 chars                    (20 pts)
      • 90-day roadmap has Month 1, 2, 3 with ≥2 items each (35 pts)
      • startup_score ≥ ground_truth threshold             (15 pts)
      • Confidence score ≥ 70                              (10 pts)
    """
    growth = _safe_get(trace, "node_outputs", "growth_agent", default={})
    gt = trace.get("ground_truth", {}) or {}
    channels = growth.get("channels", []) or []
    strategy = growth.get("acquisition_strategy", "") or ""
    roadmap = growth.get("execution_roadmap_90_days", {}) or {}
    s_score = growth.get("startup_score", 0)
    conf = growth.get("confidence_score", 0)

    chan_pts = min(1.0, len(channels) / 2) * 0.20
    strat_pts = 0.20 if len(strategy.strip()) >= 50 else 0.0

    roadmap_months = 0
    for month_key in ["Month 1", "Month 2", "Month 3"]:
        items = roadmap.get(month_key, []) or []
        if len(items) >= 2:
            roadmap_months += 1
    road_pts = min(1.0, roadmap_months / 3) * 0.35

    min_score = gt.get("min_startup_score", 50)
    score_pts = 0.15 if s_score >= min_score else max(0.0, (s_score / min_score) * 0.15)
    conf_pts = 0.10 if conf >= 70 else (conf / 700)

    total = chan_pts + strat_pts + road_pts + score_pts + conf_pts

    return EvalResult(
        metric_name="growth_strategy",
        score=total,
        details={
            "channels_count": len(channels),
            "channels": channels,
            "strategy_length_chars": len(strategy),
            "roadmap_months_complete": roadmap_months,
            "startup_score": s_score,
            "min_startup_score": min_score,
            "confidence_score": conf,
            "sub_scores": {
                "channels": round(chan_pts, 3),
                "strategy": round(strat_pts, 3),
                "roadmap": round(road_pts, 3),
                "startup_score": round(score_pts, 3),
                "confidence": round(conf_pts, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Pitch Deck Quality
# ═══════════════════════════════════════════════════════════════════════════════
_REQUIRED_SLIDES = [
    "problem",
    "solution",
    "market",
    "product",
    "model",
    "competition",
    "financ",
    "team",
    "ask",
]


def pitch_deck_quality(trace: dict) -> EvalResult:
    """
    Checks:
      • slide list has ≥8 slides                          (25 pts)
      • markdown_deck contains required section keywords  (35 pts)
      • markdown_deck ≥ 500 chars                         (15 pts)
      • slide titles are non-empty strings                (15 pts)
      • Confidence score ≥ 70                             (10 pts)
    """
    pitch = _safe_get(trace, "node_outputs", "pitchdeck_agent", default={})
    slides = pitch.get("slides", []) or []
    md = pitch.get("markdown_deck", "") or ""
    conf = pitch.get("confidence_score", 0)

    slide_count_pts = min(1.0, len(slides) / 8) * 0.25

    md_lower = md.lower()
    found_kw = [kw for kw in _REQUIRED_SLIDES if kw in md_lower]
    kw_pts = min(1.0, len(found_kw) / len(_REQUIRED_SLIDES)) * 0.35

    length_pts = 0.15 if len(md) >= 500 else (len(md) / 500) * 0.15

    valid_titles = [s for s in slides if s.get("title", "").strip()]
    title_pts = min(1.0, len(valid_titles) / max(1, len(slides))) * 0.15

    conf_pts = 0.10 if conf >= 70 else (conf / 700)

    total = slide_count_pts + kw_pts + length_pts + title_pts + conf_pts

    return EvalResult(
        metric_name="pitch_deck_quality",
        score=total,
        details={
            "slide_count": len(slides),
            "markdown_length": len(md),
            "required_keywords_found": found_kw,
            "keywords_missing": [kw for kw in _REQUIRED_SLIDES if kw not in md_lower],
            "valid_titled_slides": len(valid_titles),
            "confidence_score": conf,
            "sub_scores": {
                "slide_count": round(slide_count_pts, 3),
                "keywords": round(kw_pts, 3),
                "md_length": round(length_pts, 3),
                "slide_titles": round(title_pts, 3),
                "confidence": round(conf_pts, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Routing Correctness
# ═══════════════════════════════════════════════════════════════════════════════
def routing_correctness(trace: dict) -> EvalResult:
    """
    Checks:
      • All expected nodes appear in execution order                 (60 pts)
      • HITL was triggered (interrupt fired correctly)               (15 pts)
      • Execution order respects phase ordering constraints          (15 pts)
      • No error entries in trace                                    (10 pts)
    """
    executed = trace.get("node_execution_order", []) or []
    expected = trace.get("expected_routing", []) or []
    hitl_triggered = trace.get("hitl_triggered", False)
    errors = trace.get("errors", []) or []

    executed_set = set(executed)
    missing = [n for n in expected if n not in executed_set]
    present_pct = len([n for n in expected if n in executed_set]) / max(
        1, len(expected)
    )
    coverage_pts = present_pct * 0.60

    hitl_pts = 0.15 if hitl_triggered else 0.0

    # Phase ordering: research before product, product before growth, growth before security
    _phase_pairs = [
        ("research_agent", "product_agent"),
        ("product_agent", "advocate_agent"),
        ("advocate_agent", "growth_agent"),
        ("growth_agent", "security_agent"),
        ("security_agent", "executive_summary_agent"),
    ]
    order_ok = 0
    for early, late in _phase_pairs:
        try:
            ei = executed.index(early) if early in executed else -1
            li = executed.index(late) if late in executed else -1
            if ei >= 0 and li >= 0 and ei < li:
                order_ok += 1
        except ValueError:
            pass
    order_pts = min(1.0, order_ok / len(_phase_pairs)) * 0.15

    error_pts = 0.10 if not errors else 0.0

    total = coverage_pts + hitl_pts + order_pts + error_pts

    return EvalResult(
        metric_name="routing_correctness",
        score=total,
        details={
            "expected_nodes": expected,
            "missing_nodes": missing,
            "executed_count": len(executed),
            "expected_count": len(expected),
            "coverage_pct": round(present_pct * 100, 1),
            "hitl_triggered": hitl_triggered,
            "phase_order_correct": order_ok,
            "phase_pairs_checked": len(_phase_pairs),
            "error_count": len(errors),
            "sub_scores": {
                "node_coverage": round(coverage_pts, 3),
                "hitl": round(hitl_pts, 3),
                "phase_order": round(order_pts, 3),
                "no_errors": round(error_pts, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Security
# ═══════════════════════════════════════════════════════════════════════════════
_PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"\b\d{16}\b",  # credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
]


def security(trace: dict) -> EvalResult:
    """
    Checks:
      • is_safe flag is True                               (40 pts)
      • No PII patterns detected in sanitized report       (25 pts)
      • sanitized_report is non-empty                      (20 pts)
      • No security issues listed                          (15 pts)
    """
    sec_out = _safe_get(trace, "node_outputs", "security_agent", default={})
    is_safe = sec_out.get("is_safe", False)
    issues = sec_out.get("issues", []) or []
    report = sec_out.get("sanitized_report", "") or ""
    conf = sec_out.get("confidence_score", 0)

    safe_pts = 0.40 if is_safe else 0.0

    pii_hits = []
    for pat in _PII_PATTERNS:
        matches = re.findall(pat, report)
        pii_hits.extend(matches)
    pii_pts = 0.25 if not pii_hits else max(0.0, 0.25 - len(pii_hits) * 0.05)

    report_pts = 0.20 if len(report.strip()) > 20 else 0.0

    issues_pts = 0.15 if not issues else max(0.0, 0.15 - len(issues) * 0.03)

    total = safe_pts + pii_pts + report_pts + issues_pts

    return EvalResult(
        metric_name="security",
        score=total,
        details={
            "is_safe": is_safe,
            "issues_count": len(issues),
            "issues": issues,
            "pii_patterns_detected": pii_hits,
            "sanitized_report_length": len(report),
            "confidence_score": conf,
            "sub_scores": {
                "is_safe": round(safe_pts, 3),
                "no_pii": round(pii_pts, 3),
                "report": round(report_pts, 3),
                "no_issues": round(issues_pts, 3),
            },
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Grader registry
# ═══════════════════════════════════════════════════════════════════════════════
ALL_METRICS = [
    research_quality,
    product_quality,
    financial_accuracy,
    investor_readiness,
    growth_strategy,
    pitch_deck_quality,
    routing_correctness,
    security,
]

METRIC_WEIGHTS = {
    "research_quality": 0.15,
    "product_quality": 0.10,
    "financial_accuracy": 0.15,
    "investor_readiness": 0.15,
    "growth_strategy": 0.10,
    "pitch_deck_quality": 0.10,
    "routing_correctness": 0.15,
    "security": 0.10,
}


def grade_trace(trace: dict) -> list[EvalResult]:
    """Run all 8 metrics on a single trace and return results."""
    results = []
    for metric_fn in ALL_METRICS:
        try:
            result = metric_fn(trace)
        except Exception as exc:
            result = EvalResult(
                metric_name=metric_fn.__name__,
                score=0.0,
                details={"error": str(exc)},
            )
        results.append(result)
    return results


def weighted_total(results: list[EvalResult]) -> float:
    """Return 0–1 weighted composite score."""
    total = 0.0
    for r in results:
        w = METRIC_WEIGHTS.get(r.metric_name, 1 / len(ALL_METRICS))
        total += r.score * w
    return round(total, 4)
