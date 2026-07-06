---
name: pitch-generator
description: >
  Generates a professional 10-slide startup pitch deck in structured Markdown.
  Synthesizes all prior agent analyses (market research, financials, product,
  growth strategy) into investor-ready slide content.
  Trigger when the user asks to create or generate a pitch deck, investor presentation,
  or startup slide deck.
---

# Pitch Deck Generator Skill

Investor-grade 10-slide pitch deck framework. Synthesizes all prior analyses
into a compelling, structured narrative optimized for seed to Series A fundraising.

## When to Trigger
- PitchDeck agent generates the final presentation
- User asks for a pitch deck, investor deck, or slide presentation
- User wants to prepare for a VC meeting or demo day
- Final workflow phase consolidating all prior outputs

## Narrative Arc
A great pitch deck tells a story: Problem → Solution → Why Now → Why Us → Ask.
Every slide must be crisp, data-backed, and visually descriptive.

## Slide-by-Slide Template

### Slide 1 – Title
- **Startup Name** (large, prominent)
- **One-line tagline** (< 10 words, benefit-focused)
- **Founding team** names and roles
- **Contact email** and website
- **Funding stage** and date

### Slide 2 – Problem
- The core pain point (1 sentence, visceral)
- Who experiences this problem (target persona)
- How severe is the pain? (quantify with data if possible)
- Current alternatives and why they fail
- The cost of inaction (economic or emotional)

### Slide 3 – Solution
- What the product does (1 clear sentence)
- Primary value proposition (what changes for the customer)
- Key differentiators (top 3 bullet points)
- Product screenshot or demo description (markdown image placeholder)
- "Secret sauce" — the non-obvious insight

### Slide 4 – Market Size
- **TAM**: $X billion — total global opportunity
- **SAM**: $X billion — addressable with current product
- **SOM**: $X million — Year 1–3 target
- Source methodology (top-down or bottoms-up)
- Growth rate (CAGR) of the market

### Slide 5 – Product & MVP
- MVP feature list (bullet points)
- User journey / primary workflow (step by step)
- Technology stack highlights
- Development timeline (past milestones + next 6 months)
- Key metrics the MVP will validate

### Slide 6 – Business Model
- Primary revenue stream (SaaS / marketplace / transaction / hardware)
- Pricing tiers with price points
- Gross margin target
- Revenue per customer estimate (ACV or MRR)
- Secondary revenue streams

### Slide 7 – Competition
- 3×3 competitive matrix (us vs top 3 competitors × top 3 features)
- Our unique position statement
- Why competitors cannot easily replicate our approach
- Partnership vs. competition dynamics

### Slide 8 – Go-to-Market
- Primary acquisition channel (PLG / outbound / content / partnerships)
- Ideal Customer Profile (ICP) definition
- First 100 customers strategy
- Growth levers (virality, network effects, content flywheel)
- Key distribution partners

### Slide 9 – Financials (3-Year Projections)
| Year | Revenue | Customers | MRR/ARR | Burn | Runway |
|------|---------|-----------|---------|------|--------|
| Y1   | $X      | X         | $X      | $X   | X mo   |
| Y2   | $X      | X         | $X      | $X   | X mo   |
| Y3   | $X      | X         | $X      | $X   | X mo   |

Include: Unit economics summary (LTV, CAC, payback period)

### Slide 10 – The Ask
- **Funding amount**: $X (seed / pre-seed / Series A)
- **Use of funds** (% breakdown: engineering, sales, marketing, ops)
- **Key milestones** this funding achieves (3–5 bullet points)
- **Timeline to next raise or profitability**
- Call to action: "We are raising $X to [milestone]. Join us."

## Output Format
Return the pitch deck as a structured Markdown string in the `markdown_deck` field:
```json
{
  "markdown_deck": "# Startup Name\\n\\n## Slide 1: Title\\n...",
  "slide_count": 10,
  "pitch_narrative_summary": "one paragraph summary of the pitch story",
  "confidence_score": 82
}
```

## Quality Checklist
Before finalizing, verify:
- [ ] Every slide has at least one data point or metric
- [ ] Market size slides cite research agent's TAM/SAM/SOM
- [ ] Financials reference finance agent's 3-year projections
- [ ] Competition slide references research agent's competitor list
- [ ] The Ask aligns with investor agent's funding recommendation
