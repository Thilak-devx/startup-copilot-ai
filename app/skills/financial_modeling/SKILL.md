---
name: financial-modeling
description: >
  Builds a comprehensive 3-year financial model for a startup including revenue
  projections, cost structure, burn rate, runway, and break-even analysis.
  Trigger when the user needs financial projections, a financial model, burn rate
  calculation, runway estimation, or break-even analysis.
---

# Financial Modeling Skill

Three-year financial modeling framework for early-stage startups.
Produces revenue projections, cost structure, unit economics, and investor-grade
financial tables used in the pitch deck and investor reports.

## When to Trigger
- Finance agent needs to produce 3-year projections
- User asks for financial projections, burn rate, or runway
- User wants to model different growth scenarios
- Pitch deck Slide 9 (Financials) needs population
- Investor agent needs financial data to assess unit economics

## Modeling Framework

### Step 1 – Revenue Model Selection
Choose the appropriate revenue model archetype:

| Model | Applicable When | Key Driver |
|-------|-----------------|------------|
| **SaaS / Subscription** | Monthly/annual recurring revenue | MRR growth rate, churn |
| **Marketplace** | Two-sided platform with transaction fees | GMV, take rate |
| **E-commerce / Product** | Physical or digital product sales | Units sold, ASP |
| **Usage-Based** | API calls, storage, compute | Usage growth, ARPU |
| **Enterprise License** | Annual contracts with large orgs | ACV, sales cycle |
| **Freemium → Premium** | Free tier with paid conversion | Free users, conversion rate |

### Step 2 – Revenue Projections (3 Years)
Project revenue bottom-up for each year:

**Year 1 (Foundation):**
- Starting customers: X (from initial sales/pilots)
- Monthly new customer growth rate: X%
- Average Revenue Per User (ARPU): $X/month
- Churn rate: X%/month
- Monthly Recurring Revenue (MRR) at year end: $X
- Annual Recurring Revenue (ARR) Y1: $X

**Year 2 (Growth):**
- Customer growth rate (accelerating): X%
- Expansion revenue from upsells: $X
- Churn improvement: X% (as product matures)
- ARR Y2: $X (target: 3× Y1)

**Year 3 (Scale):**
- Market penetration: X% of SAM
- Enterprise tier introduction: $X ACV
- ARR Y3: $X (target: 3× Y2)

### Step 3 – Cost Structure

**COGS (Cost of Goods Sold):**
- Infrastructure / hosting (cloud costs)
- Payment processing fees (2–3% of revenue)
- Customer success (per-customer support cost)
- Third-party API / data costs

**Operating Expenses:**
| Category | Y1 ($) | Y2 ($) | Y3 ($) |
|----------|--------|--------|--------|
| Engineering & Product | | | |
| Sales & Marketing | | | |
| General & Administrative | | | |
| Customer Success | | | |
| **Total OpEx** | | | |

**Gross Margin Targets:**
- SaaS: 70–85%
- Marketplace: 40–60%
- Hardware + Software: 30–50%

### Step 4 – Burn Rate & Runway

```
Monthly Burn = Monthly OpEx + COGS - Revenue
Net Burn = Gross Revenue - Total Expenses (negative = burning cash)
Runway (months) = Cash on Hand / Monthly Net Burn
```

For each year, compute:
- **Peak monthly burn** (typically months 6–12 of Y1)
- **Burn multiple** = Net Burn / Net New ARR (< 1.5 is good; < 1 is excellent)
- **Runway at funding raise**: X months post-raise

### Step 5 – Break-Even Analysis

```
Break-Even Revenue = Total Fixed Costs / Gross Margin %
Break-Even Customers = Break-Even Revenue / ARPU
Break-Even Month = Month when cumulative revenue > cumulative costs
```

### Step 6 – Unit Economics Summary

| Metric | Value | Benchmark |
|--------|-------|-----------|
| CAC | $X | Industry avg: $X |
| LTV | $X | Target: 3× CAC |
| LTV:CAC Ratio | X:1 | ≥ 3:1 (good), ≥ 5:1 (great) |
| Payback Period | X months | < 12 mo (ideal) |
| Gross Margin | X% | ≥ 70% for SaaS |
| Net Revenue Retention | X% | > 110% (great), > 100% (good) |

### Step 7 – Scenario Analysis
Model three scenarios:

| Scenario | Assumption | ARR Y3 | Runway |
|----------|------------|--------|--------|
| **Conservative** | 50% of plan, higher churn | $X | X months |
| **Base Case** | Plan as modeled | $X | X months |
| **Optimistic** | 150% of plan, lower churn | $X | X months |

## Output Format
```json
{
  "revenue_model": "SaaS/Subscription",
  "projections": {
    "year1": {"arr": "$500K", "mrr_end": "$42K", "customers": 150},
    "year2": {"arr": "$1.8M", "mrr_end": "$150K", "customers": 520},
    "year3": {"arr": "$5.2M", "mrr_end": "$433K", "customers": 1500}
  },
  "unit_economics": {
    "cac": "$800",
    "ltv": "$4200",
    "ltv_cac_ratio": "5.25:1",
    "payback_period_months": 10,
    "gross_margin": "78%"
  },
  "burn_rate": {
    "peak_monthly_burn": "$85K",
    "runway_months_post_seed": 18,
    "break_even_month": "Month 28"
  },
  "scenarios": {
    "conservative_arr_y3": "$2.1M",
    "base_arr_y3": "$5.2M",
    "optimistic_arr_y3": "$9.8M"
  },
  "confidence_score": 72
}
```

## Confidence Score Guidelines
- **> 85**: Similar companies' financial data available for benchmarking
- **65–85**: Industry averages used; reasonable assumptions
- **< 65**: Novel business model; heavy estimation required; wide variance in scenarios
