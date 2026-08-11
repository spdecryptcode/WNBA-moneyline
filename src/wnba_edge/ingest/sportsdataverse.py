"""Download SportsDataverse ESPN WNBA parquet releases into data/raw."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from tqdm import tqdm

from wnba_edge.config import model_config
from wnba_edge.paths import RAW, ensure_dirs

BASE = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"

DATASETS = {
    "schedules": ("espn_wnba_schedules", "wnba_schedule_{season}.parquet"),
    "team_box": ("espn_wnba_team_boxscores", "team_box_{season}.parquet"),
    "player_box": ("espn_wnba_player_boxscores", "player_box_{season}.parquet"),
}


def _url(release: str, filename: str) -> str:
    return f"{BASE}/{release}/{filename}"


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_season_file(
    dataset: str,
    season: int,
    *,
    force: bool = False,
    session: requests.Session | None = None,
) -> Path | None:
    release, pattern = DATASETS[dataset]
    filename = pattern.format(season=season)
    dest_dir = RAW / dataset
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")

    if dest.exists() and not force:
        return dest

    sess = session or requests.Session()
    url = _url(release, filename)
    resp = sess.get(url, timeout=120)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    meta = {
        "dataset": dataset,
        "season": season,
        "url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "sha256": _checksum(dest),
        "bytes": dest.stat().st_size,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return dest


def ingest_seasons(
    seasons: Iterable[int] | None = None,
    datasets: Iterable[str] | None = None,
    *,
    force: bool = False,
) -> dict[str, list[Path]]:
    ensure_dirs()
    cfg = model_config()
    if seasons is None:
        seasons = sorted(
            set(cfg["seasons_model"]) | set(cfg.get("seasons_elo_warmstart", []))
        )
    if datasets is None:
        datasets = list(DATASETS)

    results: dict[str, list[Path]] = {d: [] for d in datasets}
    with requests.Session() as session:
        for dataset in datasets:
            for season in tqdm(list(seasons), desc=f"ingest:{dataset}"):
                path = download_season_file(
                    dataset, int(season), force=force, session=session
                )
                if path is not None:
                    results[dataset].append(path)
    return results


def load_raw_concat(dataset: str, seasons: Iterable[int] | None = None) -> pd.DataFrame:
    cfg = model_config()
    if seasons is None:
        seasons = cfg["seasons_model"]
    frames: list[pd.DataFrame] = []
    release, pattern = DATASETS[dataset]
    _ = release
    for season in seasons:
        path = RAW / dataset / pattern.format(season=season)
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        df["source_season"] = season
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
