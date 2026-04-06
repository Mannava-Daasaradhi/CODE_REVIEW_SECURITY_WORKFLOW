"""
config.py — Loads and validates config.yaml using pydantic.
This is the single entry point for all configuration in the project.
No module should read config.yaml directly — import from here.
"""
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field
from loguru import logger


CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "config.yaml"


class ProjectConfig(BaseModel):
    name: str
    version: str = "0.1.0"
    description: str = ""
    domain: str = ""


class PathsConfig(BaseModel):
    data_raw: str = "data/raw"
    data_processed: str = "data/processed"
    checkpoints: str = "checkpoints"
    logs: str = "logs"


class ReproducibilityConfig(BaseModel):
    seed: int = 42
    deterministic: bool = True


class AppConfig(BaseModel):
    project: ProjectConfig
    paths: PathsConfig = Field(default_factory=PathsConfig)
    reproducibility: ReproducibilityConfig = Field(default_factory=ReproducibilityConfig)


def load_config(path: Optional[Path] = None) -> AppConfig:
    """Load and validate config.yaml. Raises on invalid config."""
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    config = AppConfig(**raw)
    logger.info(f"Config loaded: {config.project.name} v{config.project.version}")
    return config


# Module-level singleton — import this in other modules
config: AppConfig = load_config()
