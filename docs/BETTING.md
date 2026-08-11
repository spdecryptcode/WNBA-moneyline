# Odds & Betting Layer

## Conversions

- **American → implied probability**  
  - Positive `+150` → `100 / (150+100)`  
  - Negative `-150` → `150 / (150+100)`
- **American → decimal** used for EV: stake return multiple
- **No-vig (multiplicative)** for a two-way market:  
  `p_fair = p_implied / (p_home_imp + p_away_imp)`

## Expected value

```text
EV = model_p * decimal_odds - 1
```

Positive EV means the model thinks the price is profitable *if* probabilities are well calibrated.

## Edge

```text
edge = model_p - no_vig_market_p
```

Configured minimums live in `configs/betting.yaml` (`min_edge_ml`, `min_edge_spread`).

## Gates (v1)

A recommendation is **Bet** only if:

1. Calibrated model probability is available  
2. Market price is present  
3. Edge ≥ configured minimum  
4. Sigma ≤ `max_sigma`  
5. (Optional later) availability confidence not too low  

Stake sizing uses **fractional Kelly** (`kelly_fraction`), never full Kelly.

## What we do not do

- Use closing odds as a model feature  
- Claim historical ROI without our own snapshot history  
- Buy paid odds archives (project constraint)

## Free odds source

[The Odds API](https://the-odds-api.com/) free tier:

```bash
export ODDS_API_KEY=...   # or set in .env
wnba-odds-snapshot
```

Sport key: `basketball_wnba`. Markets: `h2h`, `spreads`.
