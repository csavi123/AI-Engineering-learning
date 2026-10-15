"""Small JSON files on disk for things worth keeping between sessions.

- data/runs/<key>.json   the last live run of each experiment, so viewing it
                         again later is free (no new API call)
- data/progress.json     your quiz answers, for scores and "Quiz me" review

Why plain JSON files? They're easy to open and read yourself, and this is a
single-person app, so a database would be overkill.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RUNS_DIR = DATA_DIR / "runs"
PROGRESS_FILE = DATA_DIR / "progress.json"


def _safe(key: str) -> str:
    # Keys become file names, so keep only safe characters.
    return re.sub(r"[^A-Za-z0-9_.-]", "_", key)


# --- Saved experiment runs ------------------------------------------------
def save_run(key: str, data: Any) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": datetime.now().isoformat(timespec="seconds"), "data": data}
    (RUNS_DIR / f"{_safe(key)}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def load_run(key: str) -> Optional[Dict[str, Any]]:
    """Return {"saved_at": ..., "data": ...} or None if never run."""
    try:
        return json.loads((RUNS_DIR / f"{_safe(key)}.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# --- Quiz progress -----------------------------------------------------------
def load_progress() -> Dict[str, Dict[str, Any]]:
    try:
        return json.loads(PROGRESS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def record_answer(question_id: str, correct: bool) -> None:
    """Count right/wrong answers per question, e.g. 'ch01/l01/q2'."""
    progress = load_progress()
    entry = progress.setdefault(question_id, {"right": 0, "wrong": 0})
    entry["right" if correct else "wrong"] += 1
    entry["last_correct"] = correct
    entry["last_at"] = datetime.now().isoformat(timespec="seconds")
    DATA_DIR.mkdir(exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
