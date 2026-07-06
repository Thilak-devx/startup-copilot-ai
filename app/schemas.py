# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Startup Copilot — shared Pydantic schemas.

Every agent output carries a `confidence_score` (0–100, default 75) so the
Orchestrator and Executive Summary agent can weight individual findings.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Input schema
# ─────────────────────────────────────────────────────────────────────────────
class StartupIdea(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="The name of the startup")
    description: str = Field(
        ..., description="High-level description of the startup idea and product"
    )
    industry: str = Field(
        ..., description="The industry or sector (e.g., FinTech, SaaS, HealthTech)"
    )
    target_customer: str = Field(..., description="The target audience or user segment")
    estimated_pricing: str = Field(
        ..., description="Proposed pricing structure or revenue model"
    )
    funding_stage: str = Field(
        "Seed", description="Current funding stage (e.g., Pre-seed, Seed, Series A)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sub-models
# ─────────────────────────────────────────────────────────────────────────────
class Competitor(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    strengths: list[str]
    weaknesses: list[str]


class MarketSize(BaseModel):
    model_config = ConfigDict(frozen=True)

    tam: str = Field(..., description="Total Addressable Market size and justification")
    sam: str = Field(
        ..., description="Serviceable Addressable Market size and justification"
    )
    som: str = Field(
        ..., description="Serviceable Obtainable Market size and justification"
    )


class RiskItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str = Field(
        ..., description="Regulatory, Legal, Operational, or Market risk"
    )
    description: str
    severity: str = Field("Medium", description="Low, Medium, High")
    mitigation_strategy: str


class MVPFeature(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    priority: str = Field(
        "Must-have", description="Must-have, Should-have, Nice-to-have"
    )


class PitchDeckSlide(BaseModel):
    model_config = ConfigDict(frozen=True)

    slide_number: int
    title: str
    content: list[str]


class SimulationMonth(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: int
    active_users: int
    monthly_recurring_revenue: float
    burn_rate: float
    cash_balance: float
    milestones: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Research & Risk
# ─────────────────────────────────────────────────────────────────────────────
class ResearchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    market_size: MarketSize
    competitors: list[Competitor]
    market_trends: list[str]
    opportunities: list[str]
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in findings (0–100)",
        ge=0,
        le=100,
    )


class RiskOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    initial_risks: list[RiskItem]
    is_showstopper: bool = Field(
        False, description="Flag: startup violates baseline safety/legal rules"
    )
    reasoning: str | None = None
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in risk assessment (0–100)",
        ge=0,
        le=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Product & Finance
# ─────────────────────────────────────────────────────────────────────────────
class ProductOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    mvp_scope: list[MVPFeature]
    user_stories: list[str]
    suggested_tech_stack: list[str]
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in product plan (0–100)",
        ge=0,
        le=100,
    )


class FinanceOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    pricing_model_critique: str
    unit_economics: dict[str, str] = Field(
        ..., description="CAC, LTV, payback period estimate details"
    )
    cost_structure: list[str]
    three_year_projections: dict[str, str] = Field(
        ..., description="Year 1, 2, 3 projected revenue estimates"
    )
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in financial model (0–100)",
        ge=0,
        le=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Advocate & Investor
# ─────────────────────────────────────────────────────────────────────────────
class AdvocateOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    brutal_truth: str = Field(
        ..., description="Direct and unbiased critique on why this business might fail"
    )
    critical_assumptions: list[str]
    stress_test_results: dict[str, str] = Field(
        ..., description="Scenarios tested and their failure points"
    )
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in risk critique (0–100)",
        ge=0,
        le=100,
    )


class InvestorOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    investment_readiness_score: int = Field(
        ..., description="Score out of 100", ge=0, le=100
    )
    strengths: list[str]
    concerns: list[str]
    investment_recommendation: str
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in investment verdict (0–100)",
        ge=0,
        le=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HITL
# ─────────────────────────────────────────────────────────────────────────────
class HITLReviewInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str = Field(
        "approved",
        description="Must be 'approved', 'major_revision', or 'minor_revision'",
    )
    comments: str = Field(..., description="Founder feedback and requests for revision")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Growth, Simulator, PitchDeck
# ─────────────────────────────────────────────────────────────────────────────
class GrowthOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    channels: list[str] = Field(..., description="Top 3 marketing or GTM channels")
    acquisition_strategy: str
    startup_score: int = Field(
        ..., description="Weighted performance score out of 100", ge=0, le=100
    )
    execution_roadmap_90_days: dict[str, list[str]] = Field(
        ..., description="Key items for Month 1, Month 2, Month 3"
    )
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in growth strategy (0–100)",
        ge=0,
        le=100,
    )


class SimulatorOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    simulation_log: list[SimulationMonth]
    success_scenario: str
    failure_scenario: str
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in simulation accuracy (0–100)",
        ge=0,
        le=100,
    )


class PitchDeckOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    markdown_deck: str = Field(
        ..., description="Full 10-slide markdown presentation text"
    )
    slides: list[PitchDeckSlide]
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in pitch deck quality (0–100)",
        ge=0,
        le=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────────────────────────────────────
class SecurityCheckpointOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_safe: bool = Field(True, description="Safety and policy check flag")
    issues: list[str]
    sanitized_report: str
    confidence_score: int = Field(
        75,
        description="Agent self-assessed confidence in security assessment (0–100)",
        ge=0,
        le=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator telemetry
# ─────────────────────────────────────────────────────────────────────────────
class OrchestratorLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: str
    nodes_completed: list[str]
    avg_confidence: float = Field(
        ..., description="Mean confidence score of nodes in this phase"
    )
    retry_count: int = Field(
        0, description="Number of times this phase has been retried"
    )
    decision: str = Field(..., description="Human-readable routing decision taken")
    timestamp: str


# ─────────────────────────────────────────────────────────────────────────────
# Executive Summary
# ─────────────────────────────────────────────────────────────────────────────
class ExecutiveSummaryOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    executive_summary: str = Field(
        ..., description="2–4 sentence synthesis of the entire analysis"
    )
    top_strengths: list[str] = Field(
        ..., description="3–5 strongest signals identified across all agents"
    )
    top_risks: list[str] = Field(
        ..., description="3–5 most critical risks identified across all agents"
    )
    recommendation: str = Field(
        ...,
        description="Final verdict: 'Strong Invest', 'Conditional Invest', 'Watch', or 'Pass'",
    )
    overall_confidence_score: int = Field(
        ...,
        description="Weighted aggregate confidence across all agent outputs (0–100)",
        ge=0,
        le=100,
    )
    startup_health: str = Field(
        ...,
        description="Detailed assessment of the startup's overall health and viability",
    )
    biggest_strengths: list[str] = Field(
        ..., description="3–5 biggest strengths identified across all agents"
    )
    biggest_risks: list[str] = Field(
        ..., description="3–5 biggest risks identified across all agents"
    )
    recommended_next_action: str = Field(
        ...,
        description="Recommended next action (e.g. Invest, Pass, Watch, or specific milestone gate)",
    )
    overall_confidence: int = Field(
        ...,
        description="Overall confidence score (0–100)",
        ge=0,
        le=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────────
class SQLiteRunLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    startup_name: str
    startup_score: int
    investment_readiness_score: int
    overall_confidence_score: int = 0
    executive_summary: str = ""
    recommendation: str = ""
    status: str
    startup_health: str = ""
    recommended_next_action: str = ""
    overall_confidence: int = 0
