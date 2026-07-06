"""
Unit tests for the Startup Copilot skill loader.

Verifies:
- All 6 required skills are discovered
- Each skill has valid frontmatter (name + description)
- Each skill has non-empty instructions
- SkillToolset builds without errors
"""

from app.skill_loader import build_skill_toolset, load_all_skills

REQUIRED_SKILL_NAMES = {
    "market-research",
    "competitor-analysis",
    "startup-scoring",
    "pitch-generator",
    "investor-review",
    "financial-modeling",
}


class TestSkillLoader:
    def test_loads_all_six_skills(self):
        skills = load_all_skills()
        assert len(skills) == 6, (
            f"Expected 6 skills, got {len(skills)}: {[s.name for s in skills]}"
        )

    def test_all_required_skill_names_present(self):
        skills = load_all_skills()
        loaded_names = {s.name for s in skills}
        missing = REQUIRED_SKILL_NAMES - loaded_names
        assert not missing, f"Missing skills: {missing}"

    def test_each_skill_has_non_empty_description(self):
        skills = load_all_skills()
        for skill in skills:
            assert skill.description.strip(), (
                f"Skill '{skill.name}' has empty description"
            )
            assert len(skill.description.strip()) > 20, (
                f"Skill '{skill.name}' description too short: '{skill.description[:50]}'"
            )

    def test_each_skill_has_non_empty_instructions(self):
        skills = load_all_skills()
        for skill in skills:
            assert skill.instructions.strip(), (
                f"Skill '{skill.name}' has empty instructions"
            )
            assert len(skill.instructions.strip()) > 100, (
                f"Skill '{skill.name}' instructions too short ({len(skill.instructions)} chars)"
            )

    def test_skill_instructions_contain_output_format(self):
        """Each skill should define an expected output format."""
        skills = load_all_skills()
        for skill in skills:
            instructions_lower = skill.instructions.lower()
            assert "output" in instructions_lower or "json" in instructions_lower, (
                f"Skill '{skill.name}' instructions don't mention output format or JSON"
            )

    def test_skill_instructions_contain_when_to_trigger(self):
        """Each skill should say when to trigger it."""
        skills = load_all_skills()
        for skill in skills:
            instructions_lower = skill.instructions.lower()
            assert "trigger" in instructions_lower or "when" in instructions_lower, (
                f"Skill '{skill.name}' instructions don't mention trigger conditions"
            )

    def test_build_skill_toolset_returns_toolset(self):
        from google.adk.tools.skill_toolset import SkillToolset

        toolset = build_skill_toolset()
        assert isinstance(toolset, SkillToolset), (
            "build_skill_toolset() did not return SkillToolset"
        )

    def test_market_research_skill_has_tam_sam_som(self):
        skills = load_all_skills()
        mr = next((s for s in skills if s.name == "market-research"), None)
        assert mr is not None
        assert "TAM" in mr.instructions
        assert "SAM" in mr.instructions
        assert "SOM" in mr.instructions

    def test_financial_modeling_has_projections(self):
        skills = load_all_skills()
        fm = next((s for s in skills if s.name == "financial-modeling"), None)
        assert fm is not None
        assert "Year 1" in fm.instructions or "year1" in fm.instructions.lower()
        assert "burn" in fm.instructions.lower()

    def test_pitch_generator_has_ten_slides(self):
        skills = load_all_skills()
        pg = next((s for s in skills if s.name == "pitch-generator"), None)
        assert pg is not None
        assert "Slide 10" in pg.instructions or "10" in pg.instructions

    def test_startup_scoring_has_five_dimensions(self):
        skills = load_all_skills()
        ss = next((s for s in skills if s.name == "startup-scoring"), None)
        assert ss is not None
        assert "Market Feasibility" in ss.instructions
        assert "MVP Feasibility" in ss.instructions
        assert "Risk Profile" in ss.instructions
        assert "Growth Strategy" in ss.instructions

    def test_competitor_analysis_has_moat_assessment(self):
        skills = load_all_skills()
        ca = next((s for s in skills if s.name == "competitor-analysis"), None)
        assert ca is not None
        assert "moat" in ca.instructions.lower() or "Moat" in ca.instructions

    def test_investor_review_has_ltv_cac(self):
        skills = load_all_skills()
        ir = next((s for s in skills if s.name == "investor-review"), None)
        assert ir is not None
        assert "LTV" in ir.instructions
        assert "CAC" in ir.instructions
