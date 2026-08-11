from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
DATA = ROOT / "data"
RAW = DATA / "raw"
CURATED = DATA / "curated"
FEATURES = DATA / "features"
ARTIFACTS = ROOT / "artifacts"
PREDICTIONS = ROOT / "predictions"
REPORTS_DQ = ROOT / "reports" / "dq"


def ensure_dirs() -> None:
    for path in (RAW, CURATED, FEATURES, ARTIFACTS, PREDICTIONS, REPORTS_DQ):
        path.mkdir(parents=True, exist_ok=True)
