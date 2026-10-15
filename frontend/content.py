"""Loads the course content (YAML files in content/).

Read fresh on every page load, so edits to a YAML file show up as soon as you
refresh the browser. The files are small, so this is fast.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def syllabus() -> List[Dict[str, Any]]:
    with open(CONTENT_DIR / "syllabus.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["chapters"]


def chapter(chapter_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The chapter's content, or None if it hasn't been built yet."""
    if not chapter_entry.get("content"):
        return None
    with open(CONTENT_DIR / chapter_entry["content"], encoding="utf-8") as f:
        return yaml.safe_load(f)


def question_ids(chap: Dict[str, Any]) -> List[str]:
    """Every quiz question id in a chapter, e.g. 'ch01/l01/q1'."""
    return [
        f"{chap['id']}/{lesson['id']}/q{i}"
        for lesson in chap["lessons"]
        for i, _ in enumerate(lesson.get("quiz", []), start=1)
    ]
