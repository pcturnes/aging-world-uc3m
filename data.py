"""
data.py — World Bank data fetcher with local CSV cache.

First run: downloads from the API (~3-5 min) and saves to cache/
Next runs:  loads from CSV instantly (~1-2 sec)

To force a fresh download, delete the cache/ folder.
"""

import threading
import os
import pandas as pd
import world_bank_data as wb

# ── Cache folder ──────────────────────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_MAIN    = os.path.join(CACHE_DIR, "main.csv")
CACHE_PYRAMID = os.path.join(CACHE_DIR, "pyramid.csv")

# ── Metrics ───────────────────────────────────────────────────────────────────
METRICS = {
    "Population Aged 65+ (%)":        "SP.POP.65UP.TO.ZS",
    "Fertility Rate (births/woman)":   "SP.DYN.TFRT.IN",
    "Life Expectancy (years)":         "SP.DYN.LE00.IN",
    "Old-Age Dependency Ratio (%)":    "SP.POP.DPND.OL",
    "Child Mortality (per 1,000)":     "SH.DYN.MORT",
    "Urban Population (%)":            "SP.URB.TOTL.IN.ZS",
    "GDP per Capita (USD)":            "NY.GDP.PCAP.CD",
    "Health Expenditure (% of GDP)":   "SH.XPD.CHEX.GD.ZS",
    "Secondary School Enrollment (%)": "SE.SEC.ENRR",
    "Net Migration (thousands)":       "SM.POP.NETM",
}

METRIC_GROUPS = {
    "🧓 Ageing": [
        "Population Aged 65+ (%)",
        "Old-Age Dependency Ratio (%)",
        "Life Expectancy (years)",
    ],
    "👶 Fertility & Youth": [
        "Fertility Rate (births/woman)",
        "Child Mortality (per 1,000)",
        "Secondary School Enrollment (%)",
    ],
    "🌍 Society & Economy": [
        "Urban Population (%)",
        "GDP per Capita (USD)",
        "Health Expenditure (% of GDP)",
        "Net Migration (thousands)",
    ],
}

METRIC_DESCRIPTIONS = {
    "Population Aged 65+ (%)":
        "Share of the total population aged 65 or older. "
        "Rising values signal an ageing society and greater demand for healthcare.",
    "Fertility Rate (births/woman)":
        "Average number of children born per woman over her lifetime. "
        "A rate below 2.1 means the population shrinks without immigration.",
    "Life Expectancy (years)":
        "Average number of years a newborn is expected to live "
        "under current mortality conditions.",
    "Old-Age Dependency Ratio (%)":
        "Number of people aged 65+ per 100 working-age people (15–64). "
        "High values strain pension and social-security systems.",
    "Child Mortality (per 1,000)":
        "Under-5 mortality rate per 1,000 live births. "
        "A key indicator of overall public health and development.",
    "Urban Population (%)":
        "Share of population living in urban areas. "
        "Urbanisation correlates strongly with demographic transition.",
    "GDP per Capita (USD)":
        "Gross Domestic Product divided by total population. "
        "A proxy for living standards and economic development.",
    "Health Expenditure (% of GDP)":
        "Current health expenditure as a percentage of GDP. "
        "Reflects government and private investment in healthcare.",
    "Secondary School Enrollment (%)":
        "Gross enrollment ratio in secondary education. "
        "Higher enrollment is strongly linked to lower fertility rates.",
    "Net Migration (thousands)":
        "Net number of migrants (thousands) over a 5-year period. "
        "Positive = more arrivals than departures.",
}

AGE_GROUPS = [
    ("0–4",   "0004"), ("5–9",   "0509"), ("10–14", "1014"),
    ("15–19", "1519"), ("20–24", "2024"), ("25–29", "2529"),
    ("30–34", "3034"), ("35–39", "3539"), ("40–44", "4044"),
    ("45–49", "4549"), ("50–54", "5054"), ("55–59", "5559"),
    ("60–64", "6064"), ("65–69", "6569"), ("70–74", "7074"),
    ("75–79", "7579"), ("80+",   "80UP"),
]

# ── Internal state ────────────────────────────────────────────────────────────
_name2code:         dict | None = None
_cache_main:        pd.DataFrame | None = None
_cache_pyr:         pd.DataFrame | None = None
_pyramid_bg_started = False


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _get_name2code() -> dict:
    global _name2code
    if _name2code is None:
        countries  = wb.get_countries()
        non_agg    = countries[countries["region"] != "Aggregates"]
        _name2code = {row["name"]: idx for idx, row in non_agg.iterrows()}
    return _name2code


# ── Main dataset ──────────────────────────────────────────────────────────────
def get_data() -> pd.DataFrame:
    """
    Returns the full metrics dataframe.
    - If cache/main.csv exists → loads it instantly.
    - Otherwise → fetches from World Bank API and saves to cache.
    """
    global _cache_main
    if _cache_main is not None:
        return _cache_main

    # Load from CSV cache if available
    if os.path.exists(CACHE_MAIN):
        print("[data] Loading main data from cache...")
        _cache_main = pd.read_csv(CACHE_MAIN, dtype={"year": int})
        print(f"[data] Loaded {len(_cache_main):,} rows from cache.")
        return _cache_main

    # Download from API
    print("[data] Downloading main data from World Bank API (first run, please wait)...")
    _ensure_cache_dir()
    name2code = _get_name2code()
    frames = []

    for label, indicator in METRICS.items():
        print(f"[data]   Fetching: {label}...")
        try:
            series = wb.get_series(indicator, date="1960:2022", simplify_index=True)
            df = series.reset_index()
            df.columns = ["country", "year", "value"]
            df["metric"]       = label
            df["country_code"] = df["country"].map(name2code)
            frames.append(df)
        except Exception as e:
            print(f"[data]   WARNING: failed to fetch {label}: {e}")

    raw = pd.concat(frames, ignore_index=True)
    raw = raw.dropna(subset=["country_code"])
    raw["year"] = raw["year"].astype(int)

    raw.to_csv(CACHE_MAIN, index=False)
    print(f"[data] Saved {len(raw):,} rows to {CACHE_MAIN}")

    _cache_main = raw
    return _cache_main


# ── Pyramid dataset ───────────────────────────────────────────────────────────
_EMPTY_PYR = pd.DataFrame(
    columns=["country", "year", "value", "age_group", "gender", "country_code"]
)

def get_pyramid_data() -> pd.DataFrame:
    """
    Returns age-sex population data.
    - If cache/pyramid.csv exists → loads it instantly.
    - Otherwise → starts a background download and returns empty immediately
      so the event loop is never blocked.  The caller should poll and retry.
    """
    global _cache_pyr, _pyramid_bg_started
    if _cache_pyr is not None:
        return _cache_pyr

    if os.path.exists(CACHE_PYRAMID):
        print("[data] Loading pyramid data from cache...")
        _cache_pyr = pd.read_csv(CACHE_PYRAMID, dtype={"year": int})
        print(f"[data] Loaded {len(_cache_pyr):,} pyramid rows from cache.")
        return _cache_pyr

    # Not cached — start background download once, return empty immediately.
    if not _pyramid_bg_started:
        _pyramid_bg_started = True
        print("[data] Pyramid cache missing — downloading in background (~3-5 min)…")
        threading.Thread(target=_fetch_pyramid_bg, daemon=True).start()

    return _EMPTY_PYR


def _fetch_pyramid_bg() -> None:
    """Download pyramid data in a daemon thread (non-blocking for the caller)."""
    global _cache_pyr
    _ensure_cache_dir()
    name2code   = _get_name2code()
    frames      = []
    frames_lock = threading.Lock()

    def fetch(label: str, code: str, gender: str) -> None:
        ind = f"SP.POP.{code}.{'MA' if gender == 'male' else 'FE'}"
        try:
            raw = wb.get_series(ind, date="1960:2022",
                                simplify_index=True).reset_index()
            raw.columns = ["country", "year", "value"]
            raw["age_group"]    = label
            raw["gender"]       = gender
            raw["country_code"] = raw["country"].map(name2code)
            raw = raw.dropna(subset=["country_code"])
            raw["year"] = raw["year"].astype(int)
            with frames_lock:
                frames.append(raw)
        except Exception:
            pass

    threads = [
        threading.Thread(target=fetch, args=(lbl, code, g))
        for lbl, code in AGE_GROUPS
        for g in ("male", "female")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if frames:
        result = pd.concat(frames, ignore_index=True)
        result.to_csv(CACHE_PYRAMID, index=False)
        _cache_pyr = result
        print(f"[data] Pyramid download complete: {len(result):,} rows saved.")
    else:
        print("[data] Pyramid download failed — no data retrieved.")