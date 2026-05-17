# Aging World — A Global Demographic Observatory

Interactive Shiny-for-Python dashboard on global demographic ageing, built on
World Bank Open Data (1960–2022).

**Live app:** <https://pcturnes.shinyapps.io/aging_world_global_demographic_observatory/>

Final assignment (F1) for *Networks Analysis & Data Visualization*, UC3M.
Authors: Pablo Cano · Miguel Ramos · Miguel Rodríguez.

## What it shows

Five interactive Plotly visualizations sharing the same controls:

- **Choropleth world map** — any indicator on a Natural-Earth projection; click a country to filter every other panel.
- **Population pyramid** — back-to-back age–sex bars (17 five-year bands × 2 sexes), share-of-population scale, hover shows absolute counts.
- **Trend (area chart)** — historical 1960–2022 line with metric-aware reference lines (2.1 replacement fertility, 100 % gross-enrollment threshold).
- **Country comparison** — multi-line chart for up to 5 user-selected countries.
- **Fertility × Life-Expectancy scatter** — 4-dimensional bubble plot (life expectancy, fertility, GDP via size, % 65+ via colour) with the 2.1 replacement line.

Each chart is accompanied by a one-paragraph narrative story-box rendered inline.

## Run locally

```bash
# 1. Create a Python 3.12 virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the Shiny server
shiny run app.py --port 8080
```

Then open <http://localhost:8080> in any browser.

The first run downloads ~460k rows from the World Bank API (~3–5 min) and
caches them under `cache/`. Subsequent runs load instantly from the cache.
The age–sex pyramid is fetched in a background thread, so the UI is never
blocked while the cache populates.

## Project structure

```
.
├── app.py              # Shiny UI + reactive server (charts, controls)
├── data.py             # World Bank API client + CSV cache layer
├── requirements.txt    # Pinned runtime dependencies
├── .python-version     # 3.12 (for pyenv)
├── cache/              # Generated CSV cache (gitignored)
└── report/             # LaTeX project report (F1 deliverable)
    ├── report.tex
    ├── report.pdf
    └── figs/           # Screenshots used in the report
```

## Tech stack

- **Framework:** [Shiny for Python](https://shiny.posit.co/py/) (Posit)
- **Charts:** [Plotly](https://plotly.com/python/) via `shinywidgets`
- **Data:** [`world_bank_data`](https://pypi.org/project/world-bank-data/), pandas
- **Deployment:** shinyapps.io (via `rsconnect-python`, install separately)

## Deploying to shinyapps.io

```bash
pip install rsconnect-python
rsconnect add --name <nickname> --account <account> --token <token> --secret <secret>
rsconnect deploy shiny . --title "Aging World"
```

Token and secret are issued at <https://www.shinyapps.io/admin/#/tokens>.
