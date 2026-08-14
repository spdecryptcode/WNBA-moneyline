from __future__ import annotations

import argparse
import json


def ingest_main(argv: list[str] | None = None) -> None:
    from wnba_edge.ingest.sportsdataverse import ingest_seasons

    p = argparse.ArgumentParser(description="Ingest SportsDataverse WNBA data")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)
    results = ingest_seasons(force=args.force)
    for ds, paths in results.items():
        print(f"{ds}: {len(paths)} season files")


def clean_main(argv: list[str] | None = None) -> None:
    from wnba_edge.cleaning.pipeline import run_cleaning

    report = run_cleaning()
    print(json.dumps(report.to_dict(), indent=2))
    if not report.all_hard_passed:
        raise SystemExit("DQ hard checks failed — see reports/dq/latest.md")


def features_main(argv: list[str] | None = None) -> None:
    from wnba_edge.features.build import build_features

    feat = build_features()
    print(f"Wrote {len(feat)} pregame feature rows")


def train_main(argv: list[str] | None = None) -> None:
    from wnba_edge.models.train import run_training_pipeline

    p = argparse.ArgumentParser(description="Train margin model")
    p.add_argument("--trials", type=int, default=None, help="Hyperparam trials (default from config)")
    args = p.parse_args(argv)
    meta = run_training_pipeline(n_trials=args.trials)
    print(json.dumps({k: meta[k] for k in meta if k != "hyperparam_search"}, indent=2))
    if "hyperparam_search" in meta:
        print("best_params:", json.dumps(meta["hyperparam_search"], indent=2))


def predict_main(argv: list[str] | None = None) -> None:
    from wnba_edge.models.predict import predict_games

    p = argparse.ArgumentParser(description="Predict games")
    p.add_argument("--date", type=str, default=None)
    args = p.parse_args(argv)
    cards = predict_games(as_of_date=args.date)
    print(json.dumps(cards[:5], indent=2, default=str))
    print(f"... total cards: {len(cards)}")


def odds_snapshot_main(argv: list[str] | None = None) -> None:
    from wnba_edge.odds.snapshot import fetch_odds_snapshot

    df = fetch_odds_snapshot()
    print(f"Snapshot rows: {len(df)}")


def api_main(argv: list[str] | None = None) -> None:
    import uvicorn

    p = argparse.ArgumentParser(description="Serve WNBA Edge HTTP API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    args = p.parse_args(argv)
    uvicorn.run(
        "wnba_edge.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
