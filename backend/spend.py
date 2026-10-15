"""Tracks estimated spend per calendar month and enforces the monthly budget.

Why? Experiments can repeat calls many times. A hard monthly limit means a
mistake (or an enthusiastic afternoon) can never run up a real bill. The
numbers are estimates from config.yaml prices, kept in data/spend.json.
"""
import json
import threading
from datetime import datetime
from typing import Dict

from backend.config import PROJECT_ROOT, load_config

SPEND_FILE = PROJECT_ROOT / "data" / "spend.json"

# FastAPI can handle requests in parallel threads; the lock stops two of them
# from writing the file at the same moment and losing an update.
_lock = threading.Lock()


class BudgetExceededError(RuntimeError):
    """Raised before an API call when this month's budget is used up."""


def _month() -> str:
    return datetime.now().strftime("%Y-%m")


def _read() -> Dict[str, float]:
    try:
        return json.loads(SPEND_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def month_total() -> float:
    return _read().get(_month(), 0.0)


def budget() -> float:
    return float(load_config().get("monthly_budget_usd", 1.0))


def check_budget() -> None:
    """Call BEFORE contacting Anthropic. Raises if the budget is used up."""
    spent, limit = month_total(), budget()
    if spent >= limit:
        raise BudgetExceededError(
            f"Monthly budget reached: ${spent:.4f} spent of ${limit:.2f}. "
            f"Raise monthly_budget_usd in config.yaml to continue."
        )


def record(cost_usd: float) -> None:
    """Call AFTER a successful API call to add its estimated cost."""
    with _lock:
        data = _read()
        data[_month()] = round(data.get(_month(), 0.0) + cost_usd, 8)
        SPEND_FILE.parent.mkdir(exist_ok=True)
        SPEND_FILE.write_text(json.dumps(data, indent=2))
