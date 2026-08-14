export type Gate = {
  bet: boolean;
  reasons: string[];
};

export type ShapItem = {
  feature: string;
  shap_value: number;
  value: number;
};

export type Market = {
  home_ml?: number;
  away_ml?: number;
  implied_home?: number;
  implied_away?: number;
  no_vig_home?: number;
  no_vig_away?: number;
  ev_home?: number;
  edge_home?: number;
  kelly?: number;
};

export type GameCard = {
  game_id: number;
  season?: number;
  game_date: string;
  home_team_id: number;
  away_team_id: number;
  home_abbr: string;
  away_abbr: string;
  mu: number;
  sigma: number;
  p_home_win_raw: number;
  p_home_win_cal: number;
  market: Market;
  gate: Gate;
  shap: ShapItem[];
  completed?: boolean;
  p_home_cover?: number;
  home_spread?: number;
  spread_ev?: number;
};

export type SlateResponse = {
  date: string;
  games: GameCard[];
  summary: {
    n_games: number;
    n_bet: number;
    avg_p_home: number;
  };
};

export type BacktestResponse = {
  oof_metrics: Record<string, number>;
  walk_forward_folds: Array<Record<string, number>>;
  selection_note?: string;
  param_source?: string;
  sigma?: number;
  calibration: Array<{
    bucket: number;
    p_mean: number;
    win_rate: number;
    n: number;
  }>;
};

export type DqResponse = {
  generated_at: string;
  all_hard_passed: boolean;
  checks: Array<{
    name: string;
    passed: boolean;
    n_fail: number;
    detail: string;
  }>;
  quarantine_counts: Record<string, number>;
  row_counts: Record<string, number>;
  markdown?: string;
};

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export function fetchDates(includeCompleted: boolean) {
  const q = includeCompleted ? "?include_completed=true" : "";
  return getJson<{ dates: string[]; include_completed: boolean }>(`/api/slate/dates${q}`);
}

export function fetchSlate(date: string, includeCompleted: boolean) {
  const params = new URLSearchParams({ date });
  if (includeCompleted) params.set("include_completed", "true");
  return getJson<SlateResponse>(`/api/slate?${params}`);
}

export function fetchGame(
  gameId: number,
  opts: { home_ml?: number; away_ml?: number; home_spread?: number } = {},
) {
  const params = new URLSearchParams();
  if (opts.home_ml != null && !Number.isNaN(opts.home_ml)) {
    params.set("home_ml", String(opts.home_ml));
  }
  if (opts.away_ml != null && !Number.isNaN(opts.away_ml)) {
    params.set("away_ml", String(opts.away_ml));
  }
  if (opts.home_spread != null && !Number.isNaN(opts.home_spread)) {
    params.set("home_spread", String(opts.home_spread));
  }
  const q = params.toString();
  return getJson<GameCard>(`/api/games/${gameId}${q ? `?${q}` : ""}`);
}

export function fetchBacktest() {
  return getJson<BacktestResponse>("/api/backtest");
}

export function fetchDq() {
  return getJson<DqResponse>("/api/dq");
}
