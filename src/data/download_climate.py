import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


# Locate the project root independently of the terminal's current folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "climate"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Initial pipeline-test settings.
SITE_NAME = "rajasthan_demo"
LATITUDE = 28.0
LONGITUDE = 73.3

START_DATE = "20250101"
END_DATE = "20251231"

VARIABLES = {
    "T2M": "temperature_mean_c",
    "T2M_MAX": "temperature_max_c",
    "T2M_MIN": "temperature_min_c",
    "PRECTOTCORR": "precipitation_mm_day",
}


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    request_params = {
        "parameters": ",".join(VARIABLES),
        "community": "AG",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON",
        "time-standard": "UTC",
    }

    print("Downloading NASA POWER climate data...")
    print(f"Location: {LATITUDE}, {LONGITUDE}")
    print(f"Period: {START_DATE} to {END_DATE}")

    response = requests.get(
        API_URL,
        params=request_params,
        timeout=(15, 120),
    )
    response.raise_for_status()

    payload = response.json()
    retrieved_at = datetime.now(timezone.utc)

    # Preserve the original response without overwriting previous downloads.
    timestamp = retrieved_at.strftime("%Y%m%dT%H%M%S%fZ")
    file_stem = f"{SITE_NAME}_{START_DATE}_{END_DATE}"

    raw_path = RAW_DIR / f"{file_stem}_{timestamp}.json"
    raw_path.write_bytes(response.content)

    parameter_data = payload.get("properties", {}).get("parameter", {})

    missing_variables = set(VARIABLES) - set(parameter_data)
    if missing_variables:
        raise ValueError(
            f"API response is missing variables: {sorted(missing_variables)}"
        )

    climate = pd.DataFrame(
        {
            variable: parameter_data[variable]
            for variable in VARIABLES
        }
    )

    if climate.empty:
        raise ValueError("The API returned no climate observations.")

    climate.index = pd.to_datetime(
        climate.index,
        format="%Y%m%d",
        errors="raise",
    )

    climate = climate.sort_index()
    climate = climate.apply(pd.to_numeric, errors="raise")

    # Convert the response's missing-value marker into genuine missing values.
    fill_value = float(payload.get("header", {}).get("fill_value", -999.0))
    climate = climate.mask(climate.eq(fill_value))

    expected_dates = pd.date_range(
        start=pd.to_datetime(START_DATE, format="%Y%m%d"),
        end=pd.to_datetime(END_DATE, format="%Y%m%d"),
        freq="D",
    )

    if climate.index.has_duplicates:
        raise ValueError("Duplicate climate dates were returned.")

    if not climate.index.isin(expected_dates).all():
        raise ValueError("The API returned dates outside the requested period.")

    # Keep missing dates visible rather than silently dropping them.
    climate = climate.reindex(expected_dates)

    if climate.isna().all().all():
        raise ValueError("All downloaded climate values are missing.")

    if (climate["PRECTOTCORR"] < 0).any():
        raise ValueError("Negative precipitation found after missing-value handling.")

    if (climate["T2M_MAX"] < climate["T2M_MIN"]).any():
        raise ValueError("Maximum temperature is below minimum temperature.")

    climate = climate.rename(columns=VARIABLES)
    climate.index.name = "observation_date_utc"

    csv_path = PROCESSED_DIR / f"{file_stem}_daily.csv"
    climate.to_csv(csv_path, date_format="%Y-%m-%d")

    metadata = {
        "source": "NASA POWER Daily Point API",
        "request_parameters": request_params,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "response_geometry": payload.get("geometry"),
        "parameter_metadata": payload.get("parameters", {}),
        "raw_file": str(raw_path.relative_to(PROJECT_ROOT)),
        "processed_file": str(csv_path.relative_to(PROJECT_ROOT)),
        "rows": len(climate),
        "missing_values": {
            column: int(count)
            for column, count in climate.isna().sum().items()
        },
        "historical_information_availability_verified": False,
        "research_note": (
            "Exploratory historical download. Retrieval time is not the "
            "historical publication or availability time."
        ),
    }

    metadata_path = PROCESSED_DIR / f"{file_stem}_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\nDownload and basic validation completed.")
    print(f"Rows in daily table: {len(climate)}")

    print("\nFirst five rows:")
    print(climate.head().to_string())

    print("\nMissing values:")
    print(climate.isna().sum().to_string())

    print(f"\nRaw response: {raw_path}")
    print(f"Processed CSV: {csv_path}")
    print(f"Metadata: {metadata_path}")

    if climate.isna().any().any():
        print("\nWARNING: Missing values require review. Do not replace them with zero.")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError, KeyError) as error:
        raise SystemExit(f"CLIMM climate pipeline failed: {error}")