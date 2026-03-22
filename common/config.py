"""Configuration loader — reads YAML files and validates via Pydantic."""

from pathlib import Path

import yaml
from dotenv import load_dotenv

from common.schemas import AnswersConfig, AppConfig, BlacklistConfig

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_app_config: AppConfig | None = None
_answers_config: AnswersConfig | None = None
_blacklist_config: BlacklistConfig | None = None


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config(config_dir: Path | None = None) -> AppConfig:
    """Load and validate the main application config."""
    global _app_config
    if _app_config is not None:
        return _app_config
    load_dotenv()
    base = config_dir or _CONFIG_DIR
    data = _load_yaml(base / "config.yaml")
    _app_config = AppConfig(**data)
    return _app_config


def load_answers(config_dir: Path | None = None) -> AnswersConfig:
    """Load and validate the answers config."""
    global _answers_config
    if _answers_config is not None:
        return _answers_config
    base = config_dir or _CONFIG_DIR
    data = _load_yaml(base / "answers.yaml")
    _answers_config = AnswersConfig(**data)
    return _answers_config


def load_blacklist(config_dir: Path | None = None) -> BlacklistConfig:
    """Load the company blacklist."""
    global _blacklist_config
    if _blacklist_config is not None:
        return _blacklist_config
    base = config_dir or _CONFIG_DIR
    data = _load_yaml(base / "blacklist.yaml")
    _blacklist_config = BlacklistConfig(**data)
    return _blacklist_config


def reset():
    """Reset cached configs (useful for testing)."""
    global _app_config, _answers_config, _blacklist_config
    _app_config = None
    _answers_config = None
    _blacklist_config = None
