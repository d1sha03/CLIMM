# CLIMM — Climate-Informed Market Making

**An early-stage research project exploring whether climate information can help manage risk in Indian agricultural commodity markets.**

> **Project status:** Initial data pipelines are working. The project is not yet a trading system, and no performance or predictive claims have been established.

## Overview

Agricultural production is affected by conditions such as rainfall, temperature and drought. These conditions may influence expectations about crop supply and commodity prices.

A **market maker** continuously offers to buy and sell a financial instrument. One risk it faces is **adverse selection**: a trader may trade against the market maker because they have better information about a future change in value.

CLIMM investigates whether climate information can add useful information to the financial data a market maker already uses.

### Main research question

> **Does climate information from Indian agricultural regions help market makers make better decisions than financial information alone, and under what conditions?**

The project will test this question rather than assume climate information improves performance.

## Initial India-focused scope

- **Market:** NCDEX agricultural commodity futures
- **Provisional commodity:** Guar seed (`GUARSEED10`)
- **Provisional region:** Rajasthan
- **Initial climate variables:** Temperature and precipitation
- **Initial frequency:** Daily data
- **Potential future strategies:** Avellaneda–Stoikov and Counterfactual Regret Minimization (CFR)

Guar seed and Rajasthan are **initial research choices, not final conclusions**. The commodity, region and climate indicators may change after data availability and agricultural relevance are reviewed.

## Current progress

| Component | Current status |
|---|---|
| Project folders and Python environment | Set up |
| NASA POWER climate download | Working for one Rajasthan demonstration point |
| Climate data | 365 daily observations for 2025; no missing values in the test download |
| Climate feature generation | Working |
| NCDEX UDiFF market-file inspection | Working |
| Guar seed futures cleaning | Working |
| Market history | One trading date currently processed; insufficient for predictive analysis |
| Market–climate alignment | Not yet validated |
| Predictive modelling | Not yet started |
| Market simulator, AS and CFR strategies | Planned |
| Streamlit dashboard | Planned |

The current market sample contains **one trading date** with several contract expiries. This is useful for testing the data pipeline, but not for model training or drawing conclusions.

## Implemented data pipeline

### Climate data

`src/data/download_climate.py` downloads daily climate data for a demonstration location and saves:

- The original API response under `data/raw/climate/`
- A processed daily CSV under `data/processed/`
- Metadata describing the request and download

`src/climate/features.py` creates exploratory rolling features, including:

- 7-day and 14-day average maximum temperature
- 7-day average mean temperature
- Number of days above a provisional 35°C threshold in the previous 7 days
- 7-, 14- and 30-day precipitation totals
- Number of dry days in the previous 14 days
- Daily temperature range

The temperature threshold and rolling-window definitions are **initial exploratory choices**. They require review against the crop calendar and agricultural evidence.

### NCDEX market data

Place downloaded NCDEX CSV files in:

```text
data/raw/market/
```

`src/data/inspect_market.py` inspects a market CSV and checks for the expected UDiFF fields.

`src/data/prepare_market.py` filters for `GUARSEED10` commodity-futures rows, parses dates and numeric fields, and saves the cleaned data to:

```text
data/processed/GUARSEED10_futures_clean.csv
```

The cleaner currently skips files whose column layout does not match the expected UDiFF format. For example, the legacy-format `FO_100125_FINAL.csv` is skipped rather than incorrectly treated as a UDiFF file.

Untraded contracts may contain zero values for open, high and low prices. The cleaning pipeline records those fields as missing values rather than treating them as genuine zero-price trades.

## Repository structure

```text
CLIMM/
├── data/
│   ├── raw/
│   │   ├── market/
│   │   └── climate/
│   └── processed/
├── notebooks/
├── src/
│   ├── data/
│   │   ├── download_climate.py
│   │   ├── inspect_market.py
│   │   └── prepare_market.py
│   ├── climate/
│   │   └── features.py
│   ├── market/       # Planned simulation code
│   ├── strategies/   # Planned market-making strategies
│   └── experiments/  # Planned evaluation scripts
├── results/
├── reports/
├── tests/
└── dashboard/        # Planned Streamlit app
```

## Setup

The commands below are for Windows PowerShell.

```powershell
git clone https://github.com/d1sha03/CLIMM.git
cd CLIMM

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install numpy pandas scipy statsmodels yfinance requests matplotlib plotly scikit-learn jupyter arch
```

If the repository is already on your computer, open PowerShell in the project directory instead of cloning it again.

## Run the current pipeline

### 1. Download climate data

```powershell
python src\data\download_climate.py
```

### 2. Generate climate features

```powershell
python src\climate\features.py
```

### 3. Add an NCDEX UDiFF CSV

Download an appropriate NCDEX UDiFF bhavcopy CSV and place it in:

```text
data/raw/market/
```

Keep the original file unchanged.

### 4. Inspect the market file

```powershell
python src\data\inspect_market.py
```

### 5. Prepare the market data

```powershell
python src\data\prepare_market.py
```

## Research approach

The planned evaluation compares a financial-only baseline against a model that also uses climate features.

Potential market outcomes include:

- Future returns
- Future realised volatility
- Large price movements
- Market-making performance in a controlled simulation

The project plans to use chronological evaluation rather than randomly shuffling time-series observations. Market and climate data must be aligned using information that was actually available at each decision time.

## Important limitations

- **Insufficient market history:** The currently processed NCDEX data covers only one trading date. More history is required before empirical modelling.
- **Provisional region:** The current climate download uses one demonstration point. It is not yet a production-weighted representation of Rajasthan’s guar-growing areas.
- **Climate availability timing:** An observation date does not automatically mean the information was available to a trader on that date. Publication and processing delays must be considered before aligning climate signals with trades.
- **Exploratory features:** Current rolling features are not yet validated as crop-stress indicators.
- **Adverse selection:** Daily price data alone cannot establish whether particular real-world trades were adversely selected. Quote and transaction-level data, or a clearly labelled simulation, will be needed.
- **Simulation assumptions:** Future simulation results will depend on the model assumptions and must not be presented as proof of real-world trading performance.

## Planned next steps

1. Obtain a longer NCDEX history for the selected commodity.
2. Confirm the contract selection and expiry-handling methodology.
3. Choose and justify relevant crop-growing districts.
4. Review climate variables against the crop calendar.
5. Align market and climate data without look-ahead bias.
6. Compare financial-only and climate-enhanced predictive baselines.
7. Build a transparent market simulator and a classical market-making baseline.
8. Add CFR only after defining the game and its information structure.
9. Develop a Streamlit dashboard after the research pipeline is established.

## Research and financial-use disclaimer

CLIMM is an academic research prototype. It is not a live trading system, investment recommendation or guarantee of market performance. Simulated results must be clearly distinguished from evidence based on real-world trading.
