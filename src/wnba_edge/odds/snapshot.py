"""The Odds API free-tier snapshot collector (quota-safe)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from wnba_edge.config import betting_config
from wnba_edge.paths import RAW, ensure_dirs

load_dotenv()


def fetch_odds_snapshot(*, api_key: str | None = None) -> pd.DataFrame:
    ensure_dirs()
    cfg = betting_config()["odds_api"]
    key = api_key or os.getenv("ODDS_API_KEY")
    if not key:
        raise RuntimeError(
            "ODDS_API_KEY not set. Add it to .env (see .env.example). "
            "Model training does not require this key."
        )

    url = f"https://api.the-odds-api.com/v4/sports/{cfg['sport']}/odds"
    params = {
        "apiKey": key,
        "regions": cfg["regions"],
        "markets": cfg["markets"],
        "oddsFormat": cfg["odds_format"],
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    snap_ts = datetime.now(timezone.utc).isoformat()

    rows = []
    for event in payload:
        event_id = event.get("id")
        commence = event.get("commence_time")
        home = event.get("home_team")
        away = event.get("away_team")
        for book in event.get("bookmakers", []):
            book_key = book.get("key")
            for market in book.get("markets", []):
                mkey = market.get("key")
                for outcome in market.get("outcomes", []):
                    rows.append(
                        {
                            "snapshot_ts": snap_ts,
                            "event_id": event_id,
                            "commence_time": commence,
                            "home_team": home,
                            "away_team": away,
                            "book": book_key,
                            "market": mkey,
                            "name": outcome.get("name"),
                            "price": outcome.get("price"),
                            "point": outcome.get("point"),
                        }
                    )

    df = pd.DataFrame(rows)
    out_dir = RAW / "odds_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"odds_{stamp}.parquet"
    if not df.empty:
        df.to_parquet(path, index=False)
    meta = {
        "snapshot_ts": snap_ts,
        "n_rows": len(df),
        "remaining_requests": resp.headers.get("x-requests-remaining"),
        "used_requests": resp.headers.get("x-requests-used"),
        "path": str(path) if not df.empty else None,
    }
    (out_dir / "latest_meta.json").write_text(json.dumps(meta, indent=2))
    return df
