from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def main():
    climate_files = sorted(PROCESSED_DIR.glob("*_daily.csv"))
    if not climate_files:
        raise SystemExit("No processed climate data found. Run download_climate.py first.")

    # Prefer the Rajasthan demo file if several exist
    preferred = [p for p in climate_files if "rajasthan_demo" in p.name]
    climate_path = preferred[0] if preferred else climate_files[0]

    print(f"Loading base climate data: {climate_path.name}")

    df = pd.read_csv(climate_path, parse_dates=["observation_date_utc"])
    df = df.sort_values("observation_date_utc").set_index("observation_date_utc")

    # ---------------------------------------------------------
    # FEATURE ENGINEERING
    # Rolling windows use only current and past observations.
    # Do NOT use bfill: that would leak future values.
    # ---------------------------------------------------------

    # Temperature features
    df["tmax_7d_avg"] = df["temperature_max_c"].rolling(window=7, min_periods=1).mean()
    df["tmax_14d_avg"] = df["temperature_max_c"].rolling(window=14, min_periods=1).mean()
    df["tmean_7d_avg"] = df["temperature_mean_c"].rolling(window=7, min_periods=1).mean()

    # Heat stress: days above 35C in the last 7 days
    heat_days = (df["temperature_max_c"] > 35.0).astype(int)
    df["heat_stress_7d_count"] = heat_days.rolling(window=7, min_periods=1).sum()

    # Precipitation features
    df["precip_7d_sum"] = df["precipitation_mm_day"].rolling(window=7, min_periods=1).sum()
    df["precip_14d_sum"] = df["precipitation_mm_day"].rolling(window=14, min_periods=1).sum()
    df["precip_30d_sum"] = df["precipitation_mm_day"].rolling(window=30, min_periods=1).sum()

    # Dry days in last 14 days (< 1 mm)
    dry_days = (df["precipitation_mm_day"] < 1.0).astype(int)
    df["dry_days_in_last_14d"] = dry_days.rolling(window=14, min_periods=1).sum()

    # Simple daily temperature range
    df["temp_range_c"] = df["temperature_max_c"] - df["temperature_min_c"]

    out_path = PROCESSED_DIR / "climate_features.csv"
    df.to_csv(out_path)

    print("\nClimate Feature Engineering Complete.")
    print(f"Rows: {len(df)}")
    print(f"Saved to: {out_path}")

    print("\nMissing values after feature creation:")
    print(df.isna().sum().to_string())

    columns_to_show = [
        "temperature_max_c",
        "tmax_7d_avg",
        "precip_14d_sum",
        "dry_days_in_last_14d",
        "heat_stress_7d_count",
    ]
    print("\nLatest 5 days of features:")
    print(df[columns_to_show].tail(5).to_string())


if __name__ == "__main__":
    main()