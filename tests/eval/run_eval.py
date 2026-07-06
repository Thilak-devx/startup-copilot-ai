"""
Startup Copilot — Master Evaluation Runner
==========================================
Pipeline:
  1. Generate traces for all 10 startup ideas  (calls generate_traces.py logic)
  2. Grade each trace against 8 metrics         (calls eval_metrics.py)
  3. Write grade results JSON                   (tests/eval/results/grade_results.json)
  4. Generate the final evaluation report       (tests/eval/results/eval_report.md)

Usage:
    uv run python tests/eval/run_eval.py

Options:
    --skip-traces   skip trace generation (use existing traces.jsonl)
    --traces-only   only generate traces; skip grading and report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")
os.environ.setdefault("GOOGLE_API_KEY", "mock-eval-key")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ["PYTHONUTF8"] = "1"

import io as _io

if (
    hasattr(sys.stdout, "buffer")
    and getattr(sys.stdout, "encoding", "").lower() != "utf-8"
):
    sys.stdout = _io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
if (
    hasattr(sys.stderr, "buffer")
    and getattr(sys.stderr, "encoding", "").lower() != "utf-8"
):
    sys.stderr = _io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

EVAL_DIR = Path(__file__).parent
TRACES_FILE = EVAL_DIR / "traces" / "traces.jsonl"
RESULTS_DIR = EVAL_DIR / "results"
GRADES_FILE = RESULTS_DIR / "grade_results.json"
REPORT_FILE = RESULTS_DIR / "eval_report.md"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _log(msg: str, col: str = RESET) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{col}[{ts}] {msg}{RESET}", flush=True)


def _section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 66}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 66}{RESET}\n", flush=True)


def _bar(score: float, width: int = 30) -> str:
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def _grade_col(grade: str) -> str:
    return {
        "A": GREEN,
        "B": CYAN,
        "C": YELLOW,
        "D": YELLOW,
        "F": RED,
    }.get(grade, RESET)


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Generate traces
# ═══════════════════════════════════════════════════════════════════════════════
def step_generate_traces() -> int:
    _section("STEP 1 — GENERATING EXECUTION TRACES")
    from tests.eval.generate_traces import main as gen_main

    return gen_main()


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Load traces
# ═══════════════════════════════════════════════════════════════════════════════
def load_traces() -> list[dict]:
    if not TRACES_FILE.exists():
        _log(f"Trace file not found: {TRACES_FILE}", RED)
        sys.exit(1)
    traces = []
    for line in TRACES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            traces.append(json.loads(line))
    _log(f"Loaded {len(traces)} traces from {TRACES_FILE}", GREEN)
    return traces


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Grade
# ═══════════════════════════════════════════════════════════════════════════════
def step_grade(traces: list[dict]) -> list[dict]:
    _section("STEP 2 — GRADING TRACES")
    from tests.eval.eval_metrics import grade_trace, weighted_total

    all_grade_results: list[dict] = []

    for trace in traces:
        name = trace.get("startup_name", trace.get("eval_case_id", "?"))
        results = grade_trace(trace)
        wtotal = weighted_total(results)

        grade_summary = {
            "eval_case_id": trace.get("eval_case_id"),
            "startup_name": name,
            "domain": trace.get("domain", ""),
            "graded_at": datetime.now(UTC).isoformat(),
            "weighted_score": wtotal,
            "weighted_pct": round(wtotal * 100, 1),
            "overall_grade": _grade_from_score(wtotal),
            "metrics": [],
            "final_metrics": trace.get("final_metrics", {}),
            "errors": trace.get("errors", []),
        }

        _log(f"\n  ── {name} ──", BOLD)
        for r in results:
            grade_summary["metrics"].append(
                {
                    "metric": r.metric_name,
                    "score": r.score,
                    "pct": r.pct,
                    "grade": r.grade,
                    "details": r.details,
                }
            )
            col = _grade_col(r.grade)
            _log(
                f"    {r.metric_name:<25} {_bar(r.score, 20)}  {r.pct:3d}%  [{r.grade}]",
                col,
            )
        col_total = _grade_col(grade_summary["overall_grade"])
        _log(
            f"  {'WEIGHTED TOTAL':<27} {_bar(wtotal, 20)}  {grade_summary['weighted_pct']:4.1f}%  [{grade_summary['overall_grade']}]",
            col_total,
        )
        all_grade_results.append(grade_summary)

    return all_grade_results


def _grade_from_score(score: float) -> str:
    if score >= 0.90:
        return "A"
    if score >= 0.75:
        return "B"
    if score >= 0.60:
        return "C"
    if score >= 0.45:
        return "D"
    return "F"


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Save grade results JSON
# ═══════════════════════════════════════════════════════════════════════════════
def step_save_grades(all_grades: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with GRADES_FILE.open("w", encoding="utf-8") as f:
        json.dump({"grade_results": all_grades}, f, indent=2, ensure_ascii=False)
    _log(f"Saved grade results → {GRADES_FILE}", GREEN)


# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Build the evaluation report
# ═══════════════════════════════════════════════════════════════════════════════
METRIC_DESCRIPTIONS = {
    "research_quality": "Market/competitor research depth and coverage",
    "product_quality": "MVP completeness, user stories, tech stack validity",
    "financial_accuracy": "Unit economics coherence and projection realism",
    "investor_readiness": "Investment score threshold, recommendation validity",
    "growth_strategy": "Channel diversity and 90-day roadmap completeness",
    "pitch_deck_quality": "Slide count, required sections, markdown integrity",
    "routing_correctness": "All expected nodes executed in correct phase order",
    "security": "Safety flag, no PII leaked, sanitised report present",
}

METRIC_WEIGHTS_DISPLAY = {
    "research_quality": 15,
    "product_quality": 10,
    "financial_accuracy": 15,
    "investor_readiness": 15,
    "growth_strategy": 10,
    "pitch_deck_quality": 10,
    "routing_correctness": 15,
    "security": 10,
}


def step_generate_report(all_grades: list[dict], traces: list[dict]) -> None:
    _section("STEP 3 — GENERATING EVALUATION REPORT")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # ── Aggregate stats ────────────────────────────────────────────────────
    total_cases = len(all_grades)
    weighted_scores = [g["weighted_pct"] for g in all_grades]
    avg_score = round(sum(weighted_scores) / max(1, total_cases), 1)
    max_score = max(weighted_scores)
    min_score = min(weighted_scores)

    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for g in all_grades:
        grade_dist[g["overall_grade"]] += 1

    # Per-metric averages
    metric_avgs: dict[str, list[float]] = {}
    for g in all_grades:
        for m in g["metrics"]:
            metric_avgs.setdefault(m["metric"], []).append(m["score"])
    metric_avg_scores = {
        k: round(sum(v) / len(v) * 100, 1) for k, v in metric_avgs.items()
    }

    best_metric = max(metric_avg_scores, key=metric_avg_scores.get)
    worst_metric = min(metric_avg_scores, key=metric_avg_scores.get)

    # Routing stats
    routing_scores = [
        next(
            (m["pct"] for m in g["metrics"] if m["metric"] == "routing_correctness"), 0
        )
        for g in all_grades
    ]
    hitl_count = sum(1 for t in traces if t.get("hitl_triggered"))

    # ── Build Markdown ─────────────────────────────────────────────────────
    lines: list[str] = []

    def ln(s: str = "") -> None:
        lines.append(s)

    ln("# Startup Copilot AI — Evaluation Report")
    ln()
    ln(f"> **Generated:** {now}  ")
    ln(f"> **Eval Cases:** {total_cases}  ")
    ln(
        f"> **Metrics:** {len(METRIC_DESCRIPTIONS)} custom graders (deterministic, no LLM judge required)"
    )
    ln()
    ln("---")
    ln()

    # ── Executive Dashboard ────────────────────────────────────────────────
    ln("## 📊 Executive Dashboard")
    ln()
    ln("| Metric | Value |")
    ln("|---|---|")
    ln(f"| 🏆 Average Weighted Score | **{avg_score}%** |")
    ln(f"| 🔝 Best Case Score | {max_score}% |")
    ln(f"| 🔻 Lowest Case Score | {min_score}% |")
    ln(f"| 🔀 HITL Triggered | {hitl_count}/{total_cases} cases |")
    ln(
        f"| ✅ Routing Avg | {round(sum(routing_scores) / max(1, len(routing_scores)), 1)}% |"
    )
    ln()

    # Grade distribution
    ln("### Grade Distribution")
    ln()
    ln("| Grade | Count | Bar |")
    ln("|---|---|---|")
    for grd in ["A", "B", "C", "D", "F"]:
        count = grade_dist[grd]
        bar = "■" * count + "□" * (total_cases - count)
        ln(f"| **{grd}** | {count} | `{bar}` |")
    ln()

    # ── Metric Summary ─────────────────────────────────────────────────────
    ln("## 📐 Metric Summary (Averaged Across All Cases)")
    ln()
    ln("| # | Metric | Weight | Avg Score | Grade | Description |")
    ln("|---|---|---|---|---|---|")
    for i, (metric, desc) in enumerate(METRIC_DESCRIPTIONS.items(), 1):
        avg_pct = metric_avg_scores.get(metric, 0)
        weight = METRIC_WEIGHTS_DISPLAY.get(metric, 0)
        grade = _grade_from_score(avg_pct / 100)
        marker = (
            " 🏆" if metric == best_metric else (" ⚠️" if metric == worst_metric else "")
        )
        ln(
            f"| {i} | **{metric}**{marker} | {weight}% | {avg_pct}% | {grade} | {desc} |"
        )
    ln()

    # ── Per-Case Results ───────────────────────────────────────────────────
    ln("## 🚀 Per-Case Results")
    ln()

    for g in sorted(all_grades, key=lambda x: x["weighted_pct"], reverse=True):
        name = g["startup_name"]
        domain = g["domain"]
        wpct = g["weighted_pct"]
        grade = g["overall_grade"]
        fm = g.get("final_metrics", {}) or {}
        errors = g.get("errors", []) or []

        ln(f"### {name} ({domain})")
        ln()
        ln(
            f"**Overall Score:** {wpct}% &nbsp;|&nbsp; **Grade:** {grade} &nbsp;|&nbsp; **Startup Score:** {fm.get('startup_score', 'N/A')} &nbsp;|&nbsp; **Investment Score:** {fm.get('investment_score', 'N/A')}/100 &nbsp;|&nbsp; **Recommendation:** {fm.get('recommendation', 'N/A')}"
        )
        ln()

        # Metric table for this case
        ln("| Metric | Score | Grade | Top Issue |")
        ln("|---|---|---|---|")
        for m in g["metrics"]:
            issue = _get_top_issue(m)
            ln(f"| {m['metric']} | {m['pct']}% | {m['grade']} | {issue} |")
        ln()

        if errors:
            ln(f"> ⚠️ **Errors:** {'; '.join(errors)}")
            ln()

    # ── Metric Deep Dives ──────────────────────────────────────────────────
    ln("---")
    ln()
    ln("## 🔬 Metric Deep Dives")
    ln()

    for metric_name in METRIC_DESCRIPTIONS:
        all_results_for_metric = []
        for g in all_grades:
            for m in g["metrics"]:
                if m["metric"] == metric_name:
                    all_results_for_metric.append((g["startup_name"], m))

        avg_pct = metric_avg_scores.get(metric_name, 0)
        grade = _grade_from_score(avg_pct / 100)
        weight = METRIC_WEIGHTS_DISPLAY.get(metric_name, 0)
        desc = METRIC_DESCRIPTIONS[metric_name]

        ln(f"### {metric_name}")
        ln()
        ln(
            f"**Weight:** {weight}%  |  **Avg Score:** {avg_pct}%  |  **Grade:** {grade}"
        )
        ln(f"_{desc}_")
        ln()

        # Best and worst cases for this metric
        sorted_cases = sorted(
            all_results_for_metric, key=lambda x: x[1]["pct"], reverse=True
        )
        if sorted_cases:
            best_case = sorted_cases[0]
            worst_case = sorted_cases[-1]
            ln(f"- 🏆 Best:  **{best_case[0]}** — {best_case[1]['pct']}%")
            ln(f"- ⚠️  Worst: **{worst_case[0]}** — {worst_case[1]['pct']}%")
        ln()

        # Sub-score averages (from details.sub_scores)
        sub_avgs: dict[str, list[float]] = {}
        for _, m in all_results_for_metric:
            sub = m.get("details", {}).get("sub_scores", {})
            for k, v in sub.items():
                sub_avgs.setdefault(k, []).append(float(v))

        if sub_avgs:
            ln("| Sub-Criterion | Avg Score |")
            ln("|---|---|")
            for sub_key, vals in sub_avgs.items():
                sub_avg = round(sum(vals) / len(vals) * 100, 1)
                bar = "█" * round(sub_avg / 10) + "░" * (10 - round(sub_avg / 10))
                ln(f"| {sub_key} | `{bar}` {sub_avg}% |")
            ln()

    # ── Routing Analysis ───────────────────────────────────────────────────
    ln("---")
    ln()
    ln("## 🔀 Routing & Workflow Analysis")
    ln()
    ln("| Startup | Nodes Expected | Nodes Executed | Coverage | HITL | Order OK |")
    ln("|---|---|---|---|---|---|")
    for g in all_grades:
        case_id = g["eval_case_id"]
        trace = next((t for t in traces if t.get("eval_case_id") == case_id), {})
        expected_n = len(trace.get("expected_routing", [])) if trace else 0
        executed_n = len(trace.get("node_execution_order", [])) if trace else 0
        hitl_ok = "✅" if trace.get("hitl_triggered") else "❌"

        route_m = next(
            (m for m in g["metrics"] if m["metric"] == "routing_correctness"), {}
        )
        coverage = route_m.get("details", {}).get("coverage_pct", 0) if route_m else 0
        order_ok = (
            route_m.get("details", {}).get("phase_order_correct", 0) if route_m else 0
        )
        order_t = (
            route_m.get("details", {}).get("phase_pairs_checked", 5) if route_m else 5
        )
        ln(
            f"| {g['startup_name']} | {expected_n} | {executed_n} | {coverage}% | {hitl_ok} | {order_ok}/{order_t} |"
        )
    ln()

    # ── Security Summary ───────────────────────────────────────────────────
    ln("---")
    ln()
    ln("## 🔒 Security Summary")
    ln()
    ln("| Startup | Safe? | Issues | PII Detected | Score |")
    ln("|---|---|---|---|---|")
    for g in all_grades:
        case_id = g["eval_case_id"]
        trace = next((t for t in traces if t.get("eval_case_id") == case_id), {})
        sec_out = (trace.get("node_outputs") or {}).get("security_agent", {}) or {}
        is_safe = sec_out.get("is_safe", True)
        issues = len(sec_out.get("issues", []) or [])

        sec_m = next((m for m in g["metrics"] if m["metric"] == "security"), {})
        pii = (
            len(sec_m.get("details", {}).get("pii_patterns_detected", []) or [])
            if sec_m
            else 0
        )
        score = sec_m.get("pct", 0) if sec_m else 0

        ln(
            f"| {g['startup_name']} | {'✅ Yes' if is_safe else '❌ No'} | {issues} | {pii} | {score}% |"
        )
    ln()

    # ── Financial Benchmarks ───────────────────────────────────────────────
    ln("---")
    ln()
    ln("## 💰 Financial Benchmarks")
    ln()
    ln(
        "| Startup | Startup Score | Investment Score | Recommendation | Finance Grade |"
    )
    ln("|---|---|---|---|---|")
    for g in all_grades:
        fm = g.get("final_metrics", {}) or {}
        fin_m = next(
            (m for m in g["metrics"] if m["metric"] == "financial_accuracy"), {}
        )
        fin_g = fin_m.get("grade", "?") if fin_m else "?"
        ln(
            f"| {g['startup_name']} | {fm.get('startup_score', 'N/A')} | {fm.get('investment_score', 'N/A')}/100 | {fm.get('recommendation', '?')} | {fin_g} |"
        )
    ln()

    # ── Recommendations ────────────────────────────────────────────────────
    ln("---")
    ln()
    ln("## 📋 Improvement Recommendations")
    ln()

    worst_metric_score = metric_avg_scores.get(worst_metric, 0)
    best_metric_score = metric_avg_scores.get(best_metric, 0)

    ln(f"### ✅ Strength: `{best_metric}` — {best_metric_score}% average")
    ln(
        f"> {METRIC_DESCRIPTIONS.get(best_metric, '')} is performing well across all test cases."
    )
    ln()
    ln(f"### ⚠️ Priority Improvement: `{worst_metric}` — {worst_metric_score}% average")
    ln(f"> {METRIC_DESCRIPTIONS.get(worst_metric, '')} has the lowest average score.")
    ln()

    # Specific per-metric improvement tips
    improvement_tips = {
        "research_quality": "Ensure TAM/SAM/SOM are always populated and that ≥2 competitors include explicit strengths and weaknesses.",
        "product_quality": "Increase Must-have feature count to ≥3 and add ≥3 user stories per run.",
        "financial_accuracy": "Validate that all five unit economics keys (CAC, LTV, LTV:CAC, Payback, Gross Margin) are always present.",
        "investor_readiness": "Ensure investment_readiness_score meets per-case ground truth thresholds and recommendation is a valid enum value.",
        "growth_strategy": "Include ≥3 distinct channels and ensure all three months in the 90-day roadmap have ≥2 action items each.",
        "pitch_deck_quality": "Validate 10-slide minimum and confirm all required section keywords are present in markdown output.",
        "routing_correctness": "Verify all 12 expected nodes appear in execution order and that HITL interrupt fires on every run.",
        "security": "Run PII-pattern scan before emitting sanitized_report; ensure is_safe=True and issues=[] for all safe startups.",
    }

    ln("### All Metric Improvement Actions")
    ln()
    for metric_name, tip in improvement_tips.items():
        avg_pct = metric_avg_scores.get(metric_name, 0)
        priority = (
            "🔴 High" if avg_pct < 60 else ("🟡 Medium" if avg_pct < 80 else "🟢 Good")
        )
        ln(f"- **{metric_name}** ({avg_pct}%) — {priority}: {tip}")
    ln()

    # ── Appendix: Raw Scores Table ─────────────────────────────────────────
    ln("---")
    ln()
    ln("## 📎 Appendix: Raw Score Matrix")
    ln()

    metric_names = list(METRIC_DESCRIPTIONS.keys())
    header = "| Startup |"
    for mn in metric_names:
        short = mn.replace("_", " ").title()[:14]
        header += f" {short} |"
    header += " **Total** |"
    ln(header)

    divider = "|---|" + "---|" * len(metric_names) + "---|"
    ln(divider)

    for g in sorted(all_grades, key=lambda x: x["weighted_pct"], reverse=True):
        row = f"| **{g['startup_name']}** |"
        for mn in metric_names:
            m = next((m for m in g["metrics"] if m["metric"] == mn), {})
            row += f" {m.get('pct', 0)}% |"
        row += f" **{g['weighted_pct']}%** |"
        ln(row)
    ln()

    # ── Footer ─────────────────────────────────────────────────────────────
    ln("---")
    ln()
    ln("*Report generated by Startup Copilot Evaluation Suite.*  ")
    ln(
        f"*{total_cases} cases × {len(METRIC_DESCRIPTIONS)} metrics = {total_cases * len(METRIC_DESCRIPTIONS)} total grade points.*  "
    )
    ln(
        f"*Weights: {', '.join(f'{k}={v}%' for k, v in METRIC_WEIGHTS_DISPLAY.items())}*"
    )

    # ── Write ──────────────────────────────────────────────────────────────
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    _log(f"Evaluation report → {REPORT_FILE}", GREEN)


def _get_top_issue(m: dict) -> str:
    """Extract the most salient quality issue from metric details."""
    details = m.get("details", {}) or {}
    metric = m.get("metric", "")

    if metric == "research_quality":
        missing = []
        ts = details.get("tam_sam_som_complete", [True, True, True])
        if not all(ts):
            missing.append("incomplete TAM/SAM/SOM")
        if details.get("competitors_with_swot", 0) < 2:
            missing.append("<2 competitors with SWOT")
        return "; ".join(missing) or "—"

    if metric == "product_quality":
        if details.get("must_have_count", 0) == 0:
            return "no Must-have features"
        if details.get("user_stories_count", 0) < 3:
            return f"only {details.get('user_stories_count', 0)} user stories"
        return "—"

    if metric == "financial_accuracy":
        missing = details.get("unit_econ_keys_missing", [])
        return f"missing: {missing}" if missing else "—"

    if metric == "investor_readiness":
        if not details.get("score_meets_threshold"):
            return f"score {details.get('investment_readiness_score', 0)} < threshold {details.get('min_required_score', 0)}"
        if not details.get("recommendation_valid"):
            return f"invalid recommendation: '{details.get('recommendation', '')}'"
        return "—"

    if metric == "growth_strategy":
        months = details.get("roadmap_months_complete", 0)
        if months < 3:
            return f"roadmap only {months}/3 months complete"
        if details.get("channels_count", 0) < 2:
            return "fewer than 2 channels"
        return "—"

    if metric == "pitch_deck_quality":
        missing_kw = details.get("keywords_missing", [])
        if missing_kw:
            return f"missing sections: {missing_kw[:3]}"
        if details.get("slide_count", 0) < 8:
            return "fewer than 8 slides"
        return "—"

    if metric == "routing_correctness":
        missing_nodes = details.get("missing_nodes", [])
        if missing_nodes:
            return f"missing nodes: {missing_nodes[:2]}"
        if not details.get("hitl_triggered"):
            return "HITL not triggered"
        return "—"

    if metric == "security":
        if not details.get("is_safe"):
            return "is_safe=False"
        pii = details.get("pii_patterns_detected", [])
        if pii:
            return f"PII detected: {len(pii)} patterns"
        return "—"

    return "—"


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    parser = argparse.ArgumentParser(description="Startup Copilot Evaluation Runner")
    parser.add_argument(
        "--skip-traces",
        action="store_true",
        help="Skip trace generation (use existing traces.jsonl)",
    )
    parser.add_argument(
        "--traces-only",
        action="store_true",
        help="Only generate traces; skip grading and report",
    )
    args = parser.parse_args()

    start = datetime.now()

    # ── Step 1 ─────────────────────────────────────────────────────────────
    if not args.skip_traces:
        rc = step_generate_traces()
        if rc != 0:
            _log("Trace generation had errors — continuing with partial traces", YELLOW)
    else:
        _log("Skipping trace generation (--skip-traces)", YELLOW)

    if args.traces_only:
        _log("--traces-only: exiting after trace generation.", CYAN)
        return 0

    # ── Step 2: Load ────────────────────────────────────────────────────────
    _section("STEP 1.5 — LOADING TRACES")
    traces = load_traces()

    # ── Step 3: Grade ───────────────────────────────────────────────────────
    all_grades = step_grade(traces)

    # ── Step 4: Save grades ─────────────────────────────────────────────────
    step_save_grades(all_grades)

    # ── Step 5: Report ──────────────────────────────────────────────────────
    step_generate_report(all_grades, traces)

    # ── Final summary ───────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    _section("EVALUATION COMPLETE")

    avg_pct = round(
        sum(g["weighted_pct"] for g in all_grades) / max(1, len(all_grades)), 1
    )
    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for g in all_grades:
        grade_dist[g["overall_grade"]] += 1

    _log(f"Cases evaluated    : {len(all_grades)}", BOLD)
    _log(f"Average score      : {avg_pct}%", GREEN if avg_pct >= 75 else YELLOW)
    _log(
        "Grade distribution : " + "  ".join(f"{g}={c}" for g, c in grade_dist.items()),
        BOLD,
    )
    _log(f"Elapsed            : {elapsed:.1f}s", DIM)
    _log(f"Grade results      : {GRADES_FILE}", CYAN)
    _log(f"Evaluation report  : {REPORT_FILE}", CYAN)

    has_failures = grade_dist.get("F", 0) > 0 or avg_pct < 50
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
