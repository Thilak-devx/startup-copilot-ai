---
name: investor-review
description: >
  Evaluates a startup's investment readiness by analyzing unit economics,
  pricing model, funding stage alignment, and key investor concerns.
  Trigger when asked to score investment readiness, evaluate funding potential,
  or assess unit economics (LTV, CAC, payback period).
---

# Investor Review Skill

Investment readiness evaluation framework used by the Investor Agent.

## When to Trigger
- Investor agent evaluates funding readiness
- User asks about unit economics, LTV:CAC ratio, or payback period
- User wants to understand what VCs would think of the startup
- User asks for an investment score or funding recommendation

## Instructions

### Step 1 – Unit Economics Analysis
Calculate and evaluate:
- **CAC (Customer Acquisition Cost)**: Estimated cost to acquire one paying customer
- **LTV (Lifetime Value)**: Expected total revenue from one customer over their lifetime
- **LTV:CAC Ratio**: Must be ≥ 3:1 for investor interest; ≥ 5:1 is excellent
- **Payback Period**: Months to recover CAC; < 12 months is ideal, < 18 months acceptable
- **Gross Margin**: Target ≥ 60% for SaaS, ≥ 40% for marketplace, ≥ 20% for hardware

### Step 2 – Investment Readiness Score
Score each dimension 0–100, then compute weighted average:

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Market Size & TAM | 20% | > $1B TAM for VC, > $100M for angels |
| Unit Economics | 25% | LTV:CAC ≥ 3, payback < 18 mo |
| Competitive Moat | 20% | Network effects, IP, switching costs |
| Team Strength | 15% | Domain expertise, prior exits |
| Revenue Traction | 20% | ARR growth rate, retention, NPS |

**Score Thresholds:**
- **80–100**: Highly investment ready — strong market, clear unit economics, differentiated
- **50–79**: Partially ready — needs refinement in pricing, MVP scope, or differentiation
- **0–49**: Not ready — high risks, saturated market, or weak revenue model

### Step 3 – Investor Concern Analysis
For each concern, provide:
- The concern statement
- Evidence from the startup data
- Mitigation recommendation
- Severity (High / Medium / Low)

### Step 4 – Funding Recommendation
- Recommended funding stage (Pre-seed / Seed / Series A)
- Suggested raise amount with justification
- Key milestones to achieve before raising
- Top 3 investor types or firm categories to target

### Step 5 – Confidence Score
Assign `confidence_score` (0–100) reflecting how well the available financial data supports the assessment.

## Output Format
Return structured JSON matching the `InvestorOutput` schema:
```json
{
  "investment_readiness_score": 75,
  "ltv_cac_ratio": "4.2:1",
  "payback_period_months": 14,
  "core_strengths": ["strength 1", "strength 2"],
  "investor_concerns": ["concern 1", "concern 2"],
  "funding_recommendation": "Seed round of $1.5M",
  "confidence_score": 80
}
```

## References
- [a16z Startup Benchmarks](https://a16z.com/benchmarks)
- [Bessemer Venture Metrics](https://www.bvp.com/atlas)
- [First Round Capital Resources](https://firstround.com)
