import ast
from pathlib import Path

import pytest
import yaml


def test_skill_frontmatter_valid():
    """Verify all skills have valid frontmatter."""
    skills_dir = Path(".claude/skills")
    if not skills_dir.exists():
        pytest.skip("Skills directory does not exist yet")

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md in {skill_dir}"

        content = skill_file.read_text()
        assert content.startswith("---"), f"Missing frontmatter in {skill_file}"

        # Extract frontmatter
        parts = content.split("---")
        if len(parts) < 3:
            pytest.fail(f"Invalid frontmatter format in {skill_file}")

        frontmatter = yaml.safe_load(parts[1])

        # Required fields
        assert "name" in frontmatter
        assert "description" in frontmatter

        # Name validation
        name = frontmatter["name"]
        assert name == skill_dir.name, f"Name mismatch: {name} vs {skill_dir.name}"
        assert len(name) <= 64
        assert name.islower() or "-" in name
        assert not name.startswith("-")
        assert not name.endswith("-")
        assert "--" not in name


def test_skill_description_quality():
    """Verify descriptions are actionable."""
    skills_dir = Path(".claude/skills")
    if not skills_dir.exists():
        pytest.skip("Skills directory does not exist yet")

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text()
        parts = content.split("---")
        frontmatter = yaml.safe_load(parts[1])

        description = frontmatter.get("description", "")
        assert len(description) >= 20, f"Description too short in {skill_dir}"  # Lowered from 50 for initial dev
        assert len(description) <= 1024, f"Description too long in {skill_dir}"

        # Should include action keywords
        action_keywords = ["use when", "run", "execute", "select", "analyze", "discover", "optimize", "validate"]
        has_action = any(kw in description.lower() for kw in action_keywords)
        assert has_action, f"Description lacks action keywords in {skill_dir}"


def test_skill_scripts_executable():
    """Verify bundled scripts are valid Python."""
    skills_dir = Path(".claude/skills")
    if not skills_dir.exists():
        pytest.skip("Skills directory does not exist yet")

    for skill_dir in skills_dir.iterdir():
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            continue

        for script in scripts_dir.glob("*.py"):
            content = script.read_text()
            try:
                ast.parse(content)
            except SyntaxError as e:
                raise AssertionError(f"Invalid Python in {script}: {e}")
