---
name: competitor-analysis
description: >
  Deep-dive competitor intelligence framework that maps the competitive landscape,
  profiles individual competitors, identifies strategic gaps, and produces a
  differentiation strategy. Trigger when the user wants in-depth competitor
  profiles, a competitive matrix, or differentiation analysis beyond basic market research.
---

# Competitor Analysis Skill

Strategic competitor intelligence framework. Goes deeper than market research to
profile individual competitors, map strategic positioning, and identify exploitable gaps.

## When to Trigger
- Research or Advocate agent needs detailed competitor profiles
- User asks for a competitive landscape or competitive matrix
- User wants to understand competitive positioning or differentiation strategy
- User asks "who are my main competitors?" or "how do I differentiate?"

## Analysis Framework

### Step 1 – Competitor Discovery
Identify all relevant competitors in three tiers:
- **Tier 1 (Direct)**: Same product, same customer, same price point
- **Tier 2 (Indirect)**: Different product solving the same problem
- **Tier 3 (Substitute)**: Alternative behavior that solves the same need (e.g., spreadsheets vs. SaaS)

For each competitor, gather:
- Company name, founding year, HQ location
- Funding stage and total capital raised
- Estimated revenue or ARR
- Employee count
- Customer count or market share estimate
- Key investors

### Step 2 – Competitor Profiling (per company)
For each competitor (minimum 5 total across all tiers):

**Product Assessment:**
- Core features (list top 5)
- Pricing model and price points
- Primary target customer segment
- Technical architecture (cloud, on-prem, API-first, etc.)

**Strengths Analysis (top 3):**
- Network effects, brand recognition, data moats
- Distribution advantages
- Technical superiority
- Regulatory approvals or certifications

**Weaknesses & Blind Spots (top 3):**
- User experience gaps
- Market segments they ignore
- Feature gaps or technical debt
- Customer service reputation
- Pricing flexibility issues

### Step 3 – Competitive Matrix
Build a feature-by-feature comparison matrix:

| Feature / Dimension | Our Startup | Competitor A | Competitor B | Competitor C |
|---------------------|-------------|--------------|--------------|--------------|
| Feature 1           | ✅           | ✅            | ❌            | ✅            |
| Feature 2           | ✅           | ❌            | ✅            | ❌            |
| Pricing             | $X/mo       | $Y/mo        | $Z/mo        | Enterprise   |
| Target Segment      | SMB         | Enterprise   | Consumer     | Mid-market   |

### Step 4 – Strategic Gap Analysis
Identify specific "white spaces" — areas where no competitor serves the market well:
- Underserved customer segments
- Missing product features with high demand
- Geographic markets with no dominant player
- Price points with no quality option
- Integration or interoperability gaps

### Step 5 – Differentiation Strategy
Produce a 3-pillar differentiation strategy:

1. **Product Differentiation**: What unique features create competitive separation?
2. **Market Differentiation**: Which customer segment or geography is underserved?
3. **Business Model Differentiation**: Does a different pricing or delivery model win?

For each pillar, assess:
- Defensibility (how hard is it for competitors to copy?)
- Timeline to replicate (months)
- Customer switching cost created

### Step 6 – Competitive Moat Assessment
Rate the startup's moat on a 1–5 scale for each type:
| Moat Type | Score (1–5) | Evidence |
|-----------|-------------|----------|
| Network Effects | X | explanation |
| Switching Costs | X | explanation |
| Cost Advantage | X | explanation |
| Intangible Assets (IP, brand) | X | explanation |
| Efficient Scale | X | explanation |

## Output Format
```json
{
  "competitor_profiles": [
    {
      "name": "Competitor A",
      "tier": "direct",
      "funding": "$50M Series B",
      "strengths": ["strength 1", "strength 2", "strength 3"],
      "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
      "market_share_estimate": "~15%"
    }
  ],
  "competitive_matrix_summary": "We lead on X, Y, Z; trail on A, B",
  "white_spaces": ["gap 1", "gap 2", "gap 3"],
  "differentiation_strategy": {
    "product": "...",
    "market": "...",
    "business_model": "..."
  },
  "moat_score": 3.4,
  "confidence_score": 76
}
```

## Confidence Score Guidelines
- **> 85**: Competitor data fully available (public filings, Crunchbase, press)
- **65–85**: Most competitor data available, some estimated
- **< 65**: Limited data; emerging market with few known players
