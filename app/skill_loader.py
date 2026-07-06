"""
Skill loader utility for Startup Copilot AI.

Discovers and loads all SKILL.md files from the app/skills/ directory,
building ADK Skill objects that can be passed to SkillToolset.

Each skill directory must contain a SKILL.md with YAML frontmatter::

    ---
    name: skill-name
    description: One-liner used by the LLM to decide when to trigger.
    ---

    # Skill Body
    ...instructions...
"""

from __future__ import annotations

import logging
import pathlib

try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from google.adk.tools.skill_toolset import SkillToolset, models

logger = logging.getLogger(__name__)

SKILLS_DIR = pathlib.Path(__file__).parent / "skills"


def _parse_skill_md(skill_md_path: pathlib.Path) -> models.Skill | None:
    """Parse a SKILL.md file and return a Skill model, or ``None`` on failure."""
    try:
        text = skill_md_path.read_text(encoding="utf-8")

        if not text.startswith("---"):
            logger.warning(
                "skill_loader: %s has no YAML frontmatter — skipping.", skill_md_path
            )
            return None

        try:
            end_fm = text.index("---", 3)
        except ValueError:
            logger.warning(
                "skill_loader: %s has unclosed frontmatter (missing closing '---') — skipping.",
                skill_md_path,
            )
            return None

        fm_text = text[3:end_fm].strip()
        body = text[end_fm + 3 :].strip()

        if _YAML_AVAILABLE:
            fm_data: dict = yaml.safe_load(fm_text) or {}
        else:
            # Minimal key: value fallback parser (no yaml dependency)
            fm_data = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm_data[k.strip()] = v.strip().strip('"').strip("'")

        name = fm_data.get("name", "")
        description = fm_data.get("description", "")
        if isinstance(description, str):
            description = description.strip()
        else:
            description = str(description)

        if not name:
            logger.warning(
                "skill_loader: %s frontmatter missing 'name' — skipping.", skill_md_path
            )
            return None

        frontmatter = models.Frontmatter(name=name, description=description)
        return models.Skill(frontmatter=frontmatter, instructions=body)

    except Exception as exc:
        logger.error("skill_loader: error loading %s: %s", skill_md_path, exc)
        return None


def load_all_skills() -> list[models.Skill]:
    """Walk SKILLS_DIR and load every SKILL.md found.

    Returns a list of valid :class:`models.Skill` objects sorted by name.
    """
    skills: list[models.Skill] = []

    if not SKILLS_DIR.exists():
        logger.warning("skill_loader: Skills directory not found: %s", SKILLS_DIR)
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            logger.warning(
                "skill_loader: No SKILL.md in %s — skipping.", skill_dir.name
            )
            continue

        skill = _parse_skill_md(skill_md)
        if skill:
            skills.append(skill)
            logger.info(
                "skill_loader: Loaded skill '%s' from %s/", skill.name, skill_dir.name
            )
            # Also emit to stdout so the skill loading is visible in non-logging contexts
            print(f"[skill_loader] Loaded skill: '{skill.name}' from {skill_dir.name}/")

    return skills


def build_skill_toolset(**kwargs) -> SkillToolset:
    """Build and return a SkillToolset pre-loaded with all project skills.

    Extra keyword arguments are forwarded to :class:`SkillToolset` (e.g. ``tool_filter``).
    """
    skills = load_all_skills()
    if not skills:
        logger.warning("skill_loader: No skills loaded — SkillToolset will be empty.")
    return SkillToolset(skills=skills, **kwargs)
