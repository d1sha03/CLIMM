from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SYMBOL = "GUARSEED10"
CLIMATE_LAG_DAYS = 1  # trade date T may only see climate observed through T-1


def load_market():
    path = PROCESSED_DIR / f"{SYMBOL}_futures_clean.csv"
    if not path.exists():
        raise SystemExit("Run prepare_market.py first.")
    m = pd.read_csv(path, parse_dates=["TradDt", "XpryDt"])
    m = m.sort_values(["TradDt", "XpryDt"]).reset_index(drop=True)

    # Previous settlement of the SAME contract (not of whatever was 'front' yesterday)
    m["prev_settle_same_contract"] = m.groupby("XpryDt")["SttlmPric"].shift(1)
    m["prev_oi_same_contract"] = m.groupby("XpryDt")["OpnIntrst"].shift(1)
    return m


def select_front_contract(m):
    traded = m[(m["OpnIntrst"] > 0) | (m["TtlTradgVol"] > 0)].copy()
    if traded.empty:
        raise SystemExit("No traded contracts found.")

    traded = traded.sort_values(
        ["TradDt", "OpnIntrst", "XpryDt"], ascending=[True, False, True]
    )
    front = traded.drop_duplicates(subset="TradDt", keep="first").copy()
    front = front.sort_values("TradDt").reset_index(drop=True)

    front["prev_selected_expiry"] = front["XpryDt"].shift(1)
    front["roll_day"] = (
        front["prev_selected_expiry"].notna()
        & (front["XpryDt"] != front["prev_selected_expiry"])
    )
    front["days_to_expiry"] = (front["XpryDt"] - front["TradDt"]).dt.days
    return front


def add_financial_features(f):
    f["ret_1d"] = np.log(f["SttlmPric"] / f["prev_settle_same_contract"])
    f["vol_5d"] = f["ret_1d"].rolling(5, min_periods=3).std()
    f["vol_20d"] = f["ret_1d"].rolling(20, min_periods=10).std()
    f["log_volume"] = np.log1p(f["TtlTradgVol"])
    f["oi_change_pct"] = (
        f["OpnIntrst"] / f["prev_oi_same_contract"] - 1
    ).replace([np.inf, -np.inf], np.nan)
    f["ret_5d_momentum"] = f["ret_1d"].rolling(5, min_periods=3).sum()

    # Targets: what we try to predict for the NEXT trading day
    f["target_ret_1d_fwd"] = f["ret_1d"].shift(-1)
    f["target_absret_1d_fwd"] = f["target_ret_1d_fwd"].abs()
    return f


def load_climate():
    path = PROCESSED_DIR / "climate_features.csv"
    if not path.exists():
        raise SystemExit("Run src/climate/features.py first.")
    c = pd.read_csv(path, parse_dates=["observation_date_utc"])
    c = c.sort_values("observation_date_utc")

    # An observation for UTC day D is treated as usable from D + lag onward
    c["climate_available_from"] = c["observation_date_utc"] + pd.Timedelta(
        days=CLIMATE_LAG_DAYS
    )
    c = c.add_prefix("clim_").rename(
        columns={
            "clim_observation_date_utc": "climate_obs_date",
            "clim_climate_available_from": "climate_available_from",
        }
    )
    return c


def main():
    market = load_market()
    front = select_front_contract(market)
    front = add_financial_features(front)
    climate = load_climate()

    # For each trade date, take the most recent climate row already available
    aligned = pd.merge_asof(
        front.sort_values("TradDt"),
        climate.sort_values("climate_available_from"),
        left_on="TradDt",
        right_on="climate_available_from",
        direction="backward",
    )
    aligned["climate_signal_age_days"] = (
        aligned["TradDt"] - aligned["climate_obs_date"]
    ).dt.days

    # Hard guard against leakage
    leak = aligned["climate_obs_date"] >= aligned["TradDt"]
    if leak.any():
        raise SystemExit("LEAKAGE: climate observation date >= trade date.")

    out = PROCESSED_DIR / "climm_dataset.csv"
    aligned.to_csv(out, index=False)

    print(f"Aligned dataset saved: {out}")
    print(f"Trade days:           {len(aligned)}")
    print(f"Roll days:            {int(aligned['roll_day'].sum())}")
    print(f"Rows with 1d return:  {aligned['ret_1d'].notna().sum()}")
    print(f"Rows with target:     {aligned['target_ret_1d_fwd'].notna().sum()}")
    print(f"Rows missing climate: {aligned['climate_obs_date'].isna().sum()}")

    show = [
        "TradDt", "XpryDt", "SttlmPric", "OpnIntrst", "roll_day",
        "ret_1d", "climate_obs_date", "climate_signal_age_days",
        "clim_precip_14d_sum", "clim_tmax_7d_avg",
    ]
    print("\nHead:")
    print(aligned[show].head(10).to_string(index=False))

    if len(aligned) < 60:
        print(
            "\nNOTE: fewer than 60 trade days. The pipeline is validated, "
            "but empirical testing needs a much longer NCDEX history."
        )


if __name__ == "__main__":
    main()