"""Loads settings from config.yaml and the API key from .env.

Why a separate module? Every backend file needs the same settings, and loading
them in one place means there is exactly one source of truth.
"""
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# load_dotenv copies the values from .env into os.environ, which is where the
# Anthropic SDK looks for ANTHROPIC_API_KEY. Nothing here prints the key.
load_dotenv(PROJECT_ROOT / ".env")


def load_config() -> Dict[str, Any]:
    """Read config.yaml fresh each time.

    Re-reading (instead of caching) means a price edit takes effect without
    restarting anything. The file is tiny, so this costs nothing noticeable.
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def model_info(model: str) -> Dict[str, Any]:
    """Return the config block for one model, or fail with a helpful message."""
    models = load_config().get("models", {})
    if model not in models:
        raise KeyError(
            f"Model '{model}' is not listed in config.yaml under 'models'. "
            f"Add it there with its prices before using it."
        )
    return models[model]


def api_key_present() -> bool:
    """True if a key is configured. We never return the key itself."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return key.startswith("sk-ant-") and len(key) > 20
