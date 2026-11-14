from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_MARKET_DIR = PROJECT_ROOT / "data" / "raw" / "market"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SYMBOL = "GUARSEED10"
REQUIRED_COLUMNS = {
    "TradDt",
    "FinInstrmTp",
    "TckrSymb",
    "XpryDt",
    "OpnPric",
    "HghPric",
    "LwPric",
    "ClsPric",
    "SttlmPric",
    "OpnIntrst",
    "TtlTradgVol",
}


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(RAW_MARKET_DIR.glob("*.csv"))
    if not files:
        raise SystemExit("No raw market data files found in data/raw/market.")

    print(f"Found {len(files)} raw market file(s). Processing...")

    df_list = []
    skipped = []

    for path in files:
        print(f"\nReading: {path.name}")

        try:
            df = pd.read_csv(path, dtype="string", encoding="utf-8-sig")
        except Exception as error:
            skipped.append((path.name, f"read failed: {error}"))
            continue

        df.columns = df.columns.str.strip()

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            skipped.append((path.name, f"missing columns: {sorted(missing)}"))
            print(f"  SKIPPED — missing columns: {sorted(missing)}")
            print(f"  Available columns: {df.columns.tolist()}")
            continue

        mask = (
            df["TckrSymb"].str.strip().str.upper().eq(SYMBOL)
            & df["FinInstrmTp"].str.strip().str.upper().eq("COF")
        )

        selected = df.loc[mask].copy()
        print(f"  Matched {SYMBOL} futures rows: {len(selected)}")

        if not selected.empty:
            df_list.append(selected)

    if not df_list:
        message = [f"No usable {SYMBOL} futures rows found."]
        if skipped:
            message.append("Skipped files:")
            for name, reason in skipped:
                message.append(f"  - {name}: {reason}")
        raise SystemExit("\n".join(message))

    market = pd.concat(df_list, ignore_index=True)

    keep_columns = [
        "TradDt",
        "XpryDt",
        "OpnPric",
        "HghPric",
        "LwPric",
        "ClsPric",
        "SttlmPric",
        "OpnIntrst",
        "TtlTradgVol",
    ]
    market = market[keep_columns].copy()

    market["TradDt"] = pd.to_datetime(market["TradDt"], format="%Y-%m-%d", errors="coerce")
    market["XpryDt"] = pd.to_datetime(market["XpryDt"], format="%Y-%m-%d", errors="coerce")

    numeric_cols = [
        "OpnPric",
        "HghPric",
        "LwPric",
        "ClsPric",
        "SttlmPric",
        "OpnIntrst",
        "TtlTradgVol",
    ]
    for col in numeric_cols:
        market[col] = pd.to_numeric(market[col], errors="coerce")

    # Untraded contracts often show 0 open/high/low. Treat those as missing.
    for col in ["OpnPric", "HghPric", "LwPric"]:
        market.loc[market[col] == 0.0, col] = pd.NA

    # Drop rows with invalid dates or missing settlement/close
    market = market.dropna(subset=["TradDt", "XpryDt", "ClsPric", "SttlmPric"])

    # Remove exact duplicate contract-day rows if the same file was processed twice
    market = market.drop_duplicates(subset=["TradDt", "XpryDt"], keep="last")

    market = market.sort_values(by=["TradDt", "XpryDt"]).reset_index(drop=True)

    out_path = PROCESSED_DIR / f"{SYMBOL}_futures_clean.csv"
    market.to_csv(out_path, index=False)

    print("\nMarket Data Processing Complete.")
    print(f"Total valid observations: {len(market)}")
    print(f"Unique trade dates: {market['TradDt'].nunique()}")
    print(f"Unique expiries: {market['XpryDt'].nunique()}")
    print(f"Saved to: {out_path}")

    if skipped:
        print("\nSkipped files:")
        for name, reason in skipped:
            print(f"  - {name}: {reason}")

    print("\nSample output:")
    print(market.head(10).to_string(index=False))


if __name__ == "__main__":
    main()