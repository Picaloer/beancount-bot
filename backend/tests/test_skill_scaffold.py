"""Verify the skills directory structure meets Phase 1 success criteria."""
from pathlib import Path
import importlib.util

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
SKILL_NAME = "cross-channel-dedup"


def test_skills_directory_exists():
    assert SKILLS_DIR.is_dir(), f"backend/skills/ not found at {SKILLS_DIR}"


def test_skill_subdirectory_exists():
    assert (SKILLS_DIR / SKILL_NAME).is_dir()


def test_skill_md_exists():
    assert (SKILLS_DIR / SKILL_NAME / "SKILL.md").is_file()


def test_skill_md_has_yaml_frontmatter():
    text = (SKILLS_DIR / SKILL_NAME / "SKILL.md").read_text()
    lines = text.splitlines()
    assert lines[0].strip() == "---", "SKILL.md must start with YAML front matter delimiter"
    closing = lines[1:].index("---") if "---" in lines[1:] else -1
    assert closing >= 0, "SKILL.md YAML front matter must have a closing ---"


def test_skill_md_has_required_sections():
    text = (SKILLS_DIR / SKILL_NAME / "SKILL.md").read_text()
    for section in ["## Purpose", "## System Prompt", "## Input", "## Output", "## Usage Example"]:
        assert section in text, f"SKILL.md missing section: {section}"


def test_input_schema_exists():
    assert (SKILLS_DIR / SKILL_NAME / "input_schema.py").is_file()


def test_output_schema_exists():
    assert (SKILLS_DIR / SKILL_NAME / "output_schema.py").is_file()


def test_input_schema_importable():
    spec = importlib.util.spec_from_file_location(
        "input_schema",
        SKILLS_DIR / SKILL_NAME / "input_schema.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CrossChannelDedupInput")


def test_output_schema_importable():
    spec = importlib.util.spec_from_file_location(
        "output_schema",
        SKILLS_DIR / SKILL_NAME / "output_schema.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CrossChannelDedupOutput")


def test_schema_files_no_app_imports():
    for schema_file in ["input_schema.py", "output_schema.py"]:
        text = (SKILLS_DIR / SKILL_NAME / schema_file).read_text()
        assert "from app." not in text, f"{schema_file} must not import from app.*"
        assert "import app." not in text, f"{schema_file} must not import from app.*"
