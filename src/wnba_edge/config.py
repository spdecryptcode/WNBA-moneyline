from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from wnba_edge.paths import CONFIGS


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIGS / name
    with path.open() as f:
        return yaml.safe_load(f)


def model_config() -> dict[str, Any]:
    return load_yaml("model.yaml")


def features_config() -> dict[str, Any]:
    return load_yaml("features.yaml")


def betting_config() -> dict[str, Any]:
    return load_yaml("betting.yaml")
