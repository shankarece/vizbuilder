"""
install_skill.py
----------------
Installs the vizbuilder Claude Code skill so Windsurf/Claude Code can
understand natural-language prompts like "add a bar chart showing Sales
by Region to my PBRS report".

Usage:
    python install_skill.py

This copies skill/SKILL.md to ~/.claude/skills/vizbuilder/SKILL.md
and adds vizbuilder to CLAUDE.md if not already present.
"""

import os
import shutil
import sys

SKILL_NAME = "vizbuilder"
SKILL_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", SKILL_NAME)
CLAUDE_MD = os.path.join(os.path.expanduser("~"), ".claude", "CLAUDE.md")
SRC_SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill", "SKILL.md")

CLAUDE_MD_ENTRY = """
**PBRS Report Visuals (no connection needed):**
- **vizbuilder** -- add visuals to PBRS .pbix files (bar, line, card, combo, etc.)
"""


def main():
    os.makedirs(SKILL_DIR, exist_ok=True)
    dest = os.path.join(SKILL_DIR, "SKILL.md")
    shutil.copy2(SRC_SKILL, dest)
    print(f"  Installed skill: {dest}")

    if os.path.exists(CLAUDE_MD):
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            content = f.read()
        if "vizbuilder" not in content:
            with open(CLAUDE_MD, "a", encoding="utf-8") as f:
                f.write(CLAUDE_MD_ENTRY)
            print(f"  Updated: {CLAUDE_MD}")
        else:
            print(f"  Already in: {CLAUDE_MD}")
    else:
        with open(CLAUDE_MD, "w", encoding="utf-8") as f:
            f.write(CLAUDE_MD_ENTRY.strip() + "\n")
        print(f"  Created: {CLAUDE_MD}")

    print(f"\n  Done! Restart Windsurf/Claude Code to activate the skill.")
    print(f"  Then say: \"add a bar chart showing Sales by Region to my PBRS report\"")


if __name__ == "__main__":
    main()
