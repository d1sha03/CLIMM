from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MARKET_DIR = PROJECT_ROOT / "data" / "raw" / "market"

SYMBOL = "GUARSEED10"


def main():
    files = sorted(MARKET_DIR.glob("*.csv"))

    if not files:
        raise SystemExit(
            "No CSV files found. Put an extracted NCDEX CSV in data/raw/market."
        )

    # Inspect one file first. A multi-file importer comes after schema validation.
    path = files[0]

    print(f"Inspecting: {path.name}")

    market = pd.read_csv(
        path,
        dtype="string",
        encoding="utf-8-sig",
    )

    market.columns = market.columns.str.strip()

    print(f"\nTotal rows: {len(market)}")

    print("\nColumns:")
    print(market.columns.tolist())

    required = {
        "TradDt",
        "FinInstrmTp",
        "TckrSymb",
        "XpryDt",
        "ClsPric",
    }

    missing = required - set(market.columns)

    if missing:
        raise SystemExit(
            "\nThis file does not match the expected UDiFF headers. "
            f"Missing: {sorted(missing)}. "
            "Share the printed column names before changing the file."
        )

    print("\nInstrument types:")
    print(market["FinInstrmTp"].value_counts(dropna=False).to_string())

    symbol_match = (
        market["TckrSymb"]
        .str.strip()
        .str.upper()
        .eq(SYMBOL)
        .fillna(False)
    )

    futures_match = (
        market["FinInstrmTp"]
        .str.strip()
        .str.upper()
        .eq("COF")
        .fillna(False)
    )

    selected = market.loc[symbol_match & futures_match].copy()

    print(f"\n{SYMBOL} futures rows: {len(selected)}")

    if selected.empty:
        print("\nAvailable futures symbols:")
        print(
            market.loc[futures_match, "TckrSymb"]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .to_string(index=False)
        )
        return

    display_columns = [
        "TradDt",
        "TckrSymb",
        "XpryDt",
        "OpnPric",
        "HghPric",
        "LwPric",
        "ClsPric",
        "SttlmPric",
        "OpnIntrst",
        "TtlTrdgVol",
        "TtlTradgVol",
    ]

    available_columns = [
        column for column in display_columns
        if column in selected.columns
    ]

    print("\nSelected contract observations:")
    print(selected[available_columns].head(10).to_string(index=False))

    duplicate_keys = selected.duplicated(
        subset=["TradDt", "TckrSymb", "XpryDt"],
        keep=False,
    ).sum()

    print(f"\nRows with duplicate date/symbol/expiry keys: {duplicate_keys}")
    print("\nInspection complete. The original file has not been changed.")


if __name__ == "__main__":
    main()