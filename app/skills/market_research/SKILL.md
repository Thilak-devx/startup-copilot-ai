---
name: market-research
description: >
  Performs deep market analysis for a startup idea: TAM/SAM/SOM sizing,
  competitor mapping, trend identification, and opportunity discovery.
  Trigger this skill when asked to analyze market size, identify competitors,
  or map trends for any startup idea.
---

# Market Research Skill

Deep-dive market analysis framework for new startup ideas.

## When to Trigger
- User asks about market size, TAM/SAM/SOM
- User wants competitor analysis or landscape mapping
- User asks about market trends or opportunities
- Research agent needs structured market data

## Instructions

### Step 1 – Market Sizing
Estimate the following with clear monetary values and justifications:
- **TAM (Total Addressable Market)**: Total global demand if 100% of the market used this product.
- **SAM (Serviceable Addressable Market)**: Subset of TAM matching the startup's product scope and geography.
- **SOM (Serviceable Obtainable Market)**: Realistically capturable portion of SAM within 2–3 years.

Use industry benchmarks, analyst reports (Gartner, IDC, Statista), and bottoms-up estimation when top-down data is unavailable.

### Step 2 – Competitor Mapping
For each competitor (minimum 3 direct + 2 indirect):
- Company name and funding stage
- Core value proposition
- Key strengths (top 3)
- Key weaknesses / blind spots (top 3)
- Estimated market share or customer count
- How the startup differentiates from this competitor

### Step 3 – Trend Analysis
Identify minimum 5 market trends:
- Technology trends enabling or disrupting the market
- Regulatory trends (compliance requirements, policy changes)
- Consumer behavior shifts
- Investment / VC activity signals
- Macro-economic factors

### Step 4 – Opportunity Discovery
List minimum 5 specific opportunities:
- Underserved customer segments
- Geographic expansion angles
- Partnership leverage points
- Product differentiation white spaces
- Pricing model innovations

### Step 5 – Confidence Scoring
Assign `confidence_score` (0–100):
| Score | Meaning |
|-------|---------|
| 90–100 | Established market, abundant validated data |
| 70–89 | Reasonable data, limited estimation required |
| 50–69 | Emerging market, significant estimation required |
| < 50 | Highly speculative, data scarce |

## Output Format
Return structured JSON matching the `ResearchOutput` schema:
```json
{
  "tam": "string with $ value and explanation",
  "sam": "string with $ value and explanation",
  "som": "string with $ value and explanation",
  "competitors": [{"name": "", "strengths": [], "weaknesses": []}],
  "trends": ["trend 1", "trend 2", ...],
  "opportunities": ["opportunity 1", ...],
  "confidence_score": 85
}
```

## References
- [Gartner Market Research](https://www.gartner.com)
- [Statista Industry Data](https://www.statista.com)
- [CB Insights Startup Intelligence](https://www.cbinsights.com)
