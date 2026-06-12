"""Ingredient price-forecasting core (the ML Model).

This module forecasts next-period ingredient prices so that NSGA-II can
optimise rations against *predicted* prices rather than the last observed
price. Forecasting domestically-traded inputs (maize, cassava, salt, palm oil,
dried fish) is what makes the formulation "dynamic under market volatility":
the genetic algorithm reacts to where prices are heading.

Design choices
-----------------------------------------------
* **Target = monthly log-return** `r_t = ln(price_t / price_{t-1})`, not the
  raw price. Differencing removes the strong upward trend/level differences
  between ingredients and yields a roughly stationary target, which tree models
  handle far better than raw, trending levels (trees cannot extrapolate beyond
  the training range). Prices are reconstructed from forecast returns.
* **Pooled supervised learning.** All ingredient series are stacked into one
  training matrix with an ingredient indicator, so the gradient-boosting model
  learns shared price dynamics from ~5x more rows than any single 26-29 month
  series would provide. This is essential given the short history.
* **Volatility-aware features.** Recent return mean and rolling return standard
  deviation are features, so forecasts track the prevailing volatility regime
  (the "consistent with market volatility" requirement). Backtest residuals
  give an empirical prediction interval.
* **Honest benchmarking.** The ML model (gradient boosting) is evaluated by
  expanding-window walk-forward backtest against a random-walk (naive) and a
  seasonal-naive baseline, reporting MAE / RMSE / MAPE — mirroring the
  NSGA-II-vs-LP benchmark. On short, noisy series the random walk is a strong
  competitor; reporting this transparently is part of the contribution.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

MODEL_VERSION = "gbr-returns-v1"
MIN_HISTORY_POINTS = 12  # need ~1 year before a series is forecastable
_LAGS = (1, 2, 3)
_EPS = 1e-9


# Data preparation
def to_monthly_series(observations: list[tuple]) -> pd.Series:
    """Turn [(date, price), ...] into a gap-filled monthly price Series.

    Multiple observations in the same month are averaged; missing interior
    months are linearly interpolated so returns are well defined.
    """
    if not observations:
        return pd.Series(dtype=float)
    monthly = _avg_by_month(observations)  # {month-start Timestamp: price}
    s = pd.Series(monthly).sort_index()
    if len(s) < 2:
        return s
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    return s.reindex(full_idx).interpolate(method="linear")


def _avg_by_month(observations: list[tuple]) -> dict:
    buckets: dict[pd.Timestamp, list[float]] = {}
    for d, p in observations:
        key = pd.Timestamp(d).to_period("M").to_timestamp()  # month-start
        buckets.setdefault(key, []).append(float(p))
    return {k: float(np.mean(v)) for k, v in buckets.items()}


def _supervised_frame(series: pd.Series, ingredient_id: int) -> pd.DataFrame:
    """Build the per-series supervised table targeting the monthly log-return."""
    df = pd.DataFrame({"price": series})
    df["ret"] = np.log(df["price"] / df["price"].shift(1))
    for lag in _LAGS:
        df[f"ret_lag{lag}"] = df["ret"].shift(lag)
    df["ret_roll_mean3"] = df["ret"].shift(1).rolling(3).mean()
    df["ret_roll_std3"] = df["ret"].shift(1).rolling(3).std()
    month = df.index.month
    df["month_sin"] = np.sin(2 * np.pi * month / 12)
    df["month_cos"] = np.cos(2 * np.pi * month / 12)
    df["ingredient_id"] = ingredient_id
    df["prev_price"] = df["price"].shift(1)
    return df


FEATURE_COLS = [
    "ret_lag1", "ret_lag2", "ret_lag3",
    "ret_roll_mean3", "ret_roll_std3",
    "month_sin", "month_cos",
    "ingredient_id",
]


def build_training_matrix(panel: dict[int, pd.Series]) -> pd.DataFrame:
    frames = []
    for ing_id, series in panel.items():
        if len(series) < MIN_HISTORY_POINTS:
            continue
        frames.append(_supervised_frame(series, ing_id))
    if not frames:
        return pd.DataFrame()
    full = pd.concat(frames, ignore_index=False).dropna(subset=FEATURE_COLS + ["ret"])
    return full


# Model
def _new_model() -> GradientBoostingRegressor:
    # Shallow + regularised: short, noisy series overfit easily.
    return GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=2,
        subsample=0.8,
        random_state=42,
    )


def train_model(panel: dict[int, pd.Series]) -> GradientBoostingRegressor | None:
    train = build_training_matrix(panel)
    if train.empty or len(train) < 20:
        return None
    model = _new_model()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(train[FEATURE_COLS], train["ret"])
    return model


def _one_step_features(series: pd.Series, ingredient_id: int) -> pd.DataFrame | None:
    frame = _supervised_frame(series, ingredient_id)
    # Build the feature row for the *next* month using the most recent values.
    ret = np.log(series / series.shift(1))
    if ret.dropna().shape[0] < max(_LAGS) + 1:
        return None
    last = series.index[-1]
    nxt = last + pd.offsets.MonthBegin(1)
    row = {
        "ret_lag1": ret.iloc[-1],
        "ret_lag2": ret.iloc[-2],
        "ret_lag3": ret.iloc[-3],
        "ret_roll_mean3": ret.iloc[-3:].mean(),
        "ret_roll_std3": ret.iloc[-3:].std(),
        "month_sin": np.sin(2 * np.pi * nxt.month / 12),
        "month_cos": np.cos(2 * np.pi * nxt.month / 12),
        "ingredient_id": ingredient_id,
    }
    return pd.DataFrame([row], index=[nxt])


def forecast_series(
    model: GradientBoostingRegressor,
    series: pd.Series,
    ingredient_id: int,
    horizon: int = 1,
) -> list[tuple[pd.Timestamp, float]]:
    """Recursively forecast `horizon` monthly prices ahead."""
    work = series.copy()
    out: list[tuple[pd.Timestamp, float]] = []
    for _ in range(horizon):
        feats = _one_step_features(work, ingredient_id)
        if feats is None:
            break
        r_hat = float(model.predict(feats[FEATURE_COLS])[0])
        # Dampen extreme predicted returns to the historically observed range.
        hist_ret = np.log(work / work.shift(1)).dropna()
        if len(hist_ret) > 1:
            lo, hi = hist_ret.quantile(0.05), hist_ret.quantile(0.95)
            r_hat = float(np.clip(r_hat, lo, hi))
        next_idx = feats.index[0]
        next_price = float(work.iloc[-1] * np.exp(r_hat))
        out.append((next_idx, next_price))
        work = pd.concat([work, pd.Series({next_idx: next_price})])
    return out


# Baselines (for benchmarking)
def naive_forecast(series: pd.Series, horizon: int = 1) -> float:
    return float(series.iloc[-1])  # random walk: best guess = last value


def seasonal_naive_forecast(series: pd.Series) -> float | None:
    if len(series) < 13:
        return None
    return float(series.iloc[-12])


# Walk-forward backtest
@dataclass
class BacktestMetrics:
    method: str
    n: int = 0
    mae: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0
    _abs: list[float] = field(default_factory=list)
    _sq: list[float] = field(default_factory=list)
    _pct: list[float] = field(default_factory=list)

    def add(self, actual: float, pred: float) -> None:
        err = actual - pred
        self._abs.append(abs(err))
        self._sq.append(err * err)
        self._pct.append(abs(err) / (abs(actual) + _EPS))

    def finalise(self) -> "BacktestMetrics":
        self.n = len(self._abs)
        if self.n:
            self.mae = float(np.mean(self._abs))
            self.rmse = float(np.sqrt(np.mean(self._sq)))
            self.mape = float(100 * np.mean(self._pct))
        return self


def walk_forward_backtest(
    panel: dict[int, pd.Series],
    test_months: int = 6,
) -> dict[str, dict]:
    """Expanding-window backtest comparing ML vs naive vs seasonal-naive.

    For each of the last `test_months` origins, the pooled model is retrained on
    all data up to that origin and used to forecast one month ahead for every
    series; the same origins are scored for the baselines. Returns per-method
    aggregate metrics plus per-ingredient ML metrics.
    """
    ml = BacktestMetrics("gradient_boosting")
    naive = BacktestMetrics("naive_random_walk")
    seasonal = BacktestMetrics("seasonal_naive")
    per_ingredient: dict[int, BacktestMetrics] = {}

    # Common timeline (use the longest series to define origins).
    longest = max(panel.values(), key=len)
    timeline = longest.index
    if len(timeline) <= MIN_HISTORY_POINTS + 1:
        return {"error": "insufficient history for backtest"}

    start = max(MIN_HISTORY_POINTS, len(timeline) - test_months)
    for t in range(start, len(timeline)):
        origin_date = timeline[t - 1]
        target_date = timeline[t]

        # Train pooled model on everything up to and including origin_date.
        train_panel = {
            i: s[s.index <= origin_date] for i, s in panel.items()
        }
        model = train_model(train_panel)

        for ing_id, series in panel.items():
            if target_date not in series.index:
                continue
            hist = series[series.index <= origin_date]
            if len(hist) < MIN_HISTORY_POINTS:
                continue
            actual = float(series.loc[target_date])

            # ML
            if model is not None:
                fc = forecast_series(model, hist, ing_id, horizon=1)
                if fc:
                    ml.add(actual, fc[0][1])
                    per_ingredient.setdefault(
                        ing_id, BacktestMetrics(f"ingredient_{ing_id}")
                    ).add(actual, fc[0][1])
            # Naive
            naive.add(actual, naive_forecast(hist))
            # Seasonal naive
            sn = seasonal_naive_forecast(hist)
            if sn is not None:
                seasonal.add(actual, sn)

    result = {
        m.method: vars(m.finalise())
        for m in (ml, naive, seasonal)
    }
    for k in result:
        for drop in ("_abs", "_sq", "_pct"):
            result[k].pop(drop, None)
    result["per_ingredient_ml"] = {
        ing: {kk: vv for kk, vv in vars(bm.finalise()).items()
              if not kk.startswith("_")}
        for ing, bm in per_ingredient.items()
    }
    return result
