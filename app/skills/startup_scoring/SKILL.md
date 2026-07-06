---
name: startup-scoring
description: >
  Computes a weighted Startup Score (0–100) across five dimensions: market
  feasibility, MVP feasibility, unit economics, risk profile, and growth strategy.
  Trigger when generating the final startup score, evaluating overall startup quality,
  or comparing startups across a standard rubric.
---

# Startup Scoring Skill

Weighted scoring rubric for quantifying the overall quality of a startup idea.

## When to Trigger
- Advocate or Investor agent needs to produce a final startup score
- User asks "how good is this startup idea?"
- User wants a structured evaluation across multiple dimensions
- Comparative startup assessment is needed

## Scoring Dimensions

The Startup Score is computed as a weighted sum across five dimensions, each scored 0–100.

### 1. Market Feasibility (Weight: 20%)
| Score | Criteria |
|-------|----------|
| 85–100 | > $10B TAM, clear growth trend, few entrenched players |
| 70–84 | $1B–$10B TAM, moderate growth, some competitors |
| 50–69 | $100M–$1B TAM, stable market, crowded landscape |
| < 50 | < $100M TAM, shrinking market, or monopoly dominance |

**Sub-factors:** TAM size, SAM reachability, SOM realism, trend tailwinds, competitive gap

### 2. MVP Feasibility (Weight: 20%)
| Score | Criteria |
|-------|----------|
| 85–100 | MVP buildable in < 3 months, proven tech stack, clear user stories |
| 70–84 | MVP buildable in 3–6 months, some technical risk |
| 50–69 | MVP needs 6–12 months, significant R&D required |
| < 50 | MVP unclear, requires novel research, or prohibitively complex |

**Sub-factors:** Technical complexity, build time estimate, team capability, stack appropriateness

### 3. Unit Economics & Revenue Model (Weight: 20%)
| Score | Criteria |
|-------|----------|
| 85–100 | LTV:CAC ≥ 5:1, payback < 12 mo, gross margin > 70% |
| 70–84 | LTV:CAC 3–5:1, payback 12–18 mo, gross margin 50–70% |
| 50–69 | LTV:CAC 1.5–3:1, payback 18–24 mo, gross margin 30–50% |
| < 50 | LTV:CAC < 1.5:1, negative margin, or unclear monetization |

**Sub-factors:** Revenue model clarity, pricing strategy, margin profile, payback period

### 4. Risk Profile (Weight: 20%)
| Score | Criteria |
|-------|----------|
| 85–100 | Low regulatory risk, strong IP moat, no single point of failure |
| 70–84 | Moderate regulatory hurdles, some IP protection, manageable risks |
| 50–69 | Significant regulatory uncertainty, limited IP, external dependencies |
| < 50 | High regulatory friction, no IP, critical external dependencies |

**Sub-factors:** Regulatory exposure, IP strategy, key person risk, technical risk, market timing risk

### 5. Growth Strategy (Weight: 20%)
| Score | Criteria |
|-------|----------|
| 85–100 | Clear PLG or outbound engine, defined ICP, proven GTM channels |
| 70–84 | Reasonable GTM plan, 2+ customer acquisition channels |
| 50–69 | GTM plan is vague, single-channel dependency |
| < 50 | No clear GTM strategy or acquisition plan |

**Sub-factors:** Customer acquisition clarity, growth levers, network effects, channel diversity

## Calculation Formula
```
startup_score = (
    market_feasibility_score   * 0.20 +
    mvp_feasibility_score      * 0.20 +
    unit_economics_score       * 0.20 +
    risk_profile_score         * 0.20 +
    growth_strategy_score      * 0.20
)
```

## Output Format
```json
{
  "startup_score": 72,
  "market_feasibility_score": 80,
  "mvp_feasibility_score": 75,
  "unit_economics_score": 65,
  "risk_profile_score": 70,
  "growth_strategy_score": 70,
  "score_rationale": {
    "market_feasibility": "explanation...",
    "mvp_feasibility": "explanation...",
    "unit_economics": "explanation...",
    "risk_profile": "explanation...",
    "growth_strategy": "explanation..."
  },
  "confidence_score": 78
}
```

## Confidence Score
Assign a `confidence_score` (0–100) reflecting how much supporting data existed for the scoring:
- **> 80**: All five dimensions had clear data
- **60–80**: Most dimensions had data; 1–2 required estimation
- **< 60**: Multiple dimensions required heavy estimation
