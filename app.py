"""
Aging World — Apple-inspired dark dashboard
Design: glassmorphism + SF Pro + semantic colors
"""

import os

from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_widget
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from data import (
    AGE_GROUPS, METRICS, METRIC_GROUPS,
    METRIC_DESCRIPTIONS, CACHE_PYRAMID, get_data, get_pyramid_data,
)

# ── Apple color system (HIG) ──────────────────────────────────────────────────
BLUE   = "#0A84FF"
TEAL   = "#30D158"
ORANGE = "#FF9F0A"
RED    = "#FF453A"
PURPLE = "#BF5AF2"
INDIGO = "#5E5CE6"
PINK   = "#FF375F"

BG0  = "#000000"
BG1  = "#1C1C1E"
BG2  = "#2C2C2E"
BG3  = "#3A3A3C"
SEP  = "#38383A"
TEXT = "#FFFFFF"
T2   = "rgba(235,235,245,0.8)"
T3   = "rgba(235,235,245,0.6)"
T4   = "rgba(235,235,245,0.38)"

PALETTE = [BLUE, ORANGE, TEAL, PURPLE, RED, INDIGO, PINK]

# ── Plotly layout helpers ─────────────────────────────────────────────────────
SF = "-apple-system,'SF Pro Text','Helvetica Neue',sans-serif"
SF_D = "-apple-system,'SF Pro Display','Helvetica Neue',sans-serif"

def _xy(**kw):
    d = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=SF, color=T3, size=11),
        title_font=dict(family=SF_D, color=TEXT, size=14),
        margin=dict(l=48, r=16, t=44, b=40),
        xaxis=dict(showgrid=True, gridcolor=SEP, zeroline=False,
                   color=T3, tickfont_size=10),
        yaxis=dict(showgrid=True, gridcolor=SEP, zeroline=False,
                   color=T3, tickfont_size=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_color=T2),
        hoverlabel=dict(bgcolor=BG2, font_color=TEXT, bordercolor=SEP,
                        font_family=SF, font_size=12),
    )
    d.update(kw)
    return d

def _geo(**kw):
    d = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=SF, color=T3, size=11),
        title_font=dict(family=SF_D, color=TEXT, size=14),
        margin=dict(l=0, r=0, t=32, b=0),
        hoverlabel=dict(bgcolor=BG2, font_color=TEXT, bordercolor=SEP,
                        font_family=SF),
    )
    d.update(kw)
    return d

# ── Map click JS ──────────────────────────────────────────────────────────────
_MAP_CLICK_JS = """
(function(){
  function attach(){
    document.querySelectorAll('.js-plotly-plot').forEach(function(el){
      if(el._ah) return; el._ah=true;
      el.on('plotly_click',function(d){
        if(!d||!d.points||!d.points.length) return;
        var p=d.points[0];
        if(p.location===undefined) return;
        var c=(p.customdata&&p.customdata[0])||p.hovertext;
        if(c&&window.Shiny) Shiny.setInputValue('map_clicked_country',c,{priority:'event'});
      });
    });
  }
  new MutationObserver(attach).observe(document.body,{childList:true,subtree:true});
  attach();
})();
"""

# ── CSS (plain string, no f-string to avoid brace escaping) ──────────────────
_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.bslib-page-fill{
  background:#000 !important;
  color:#fff !important;
  font-family:-apple-system,'SF Pro Text','Helvetica Neue',Arial,sans-serif !important;
  -webkit-font-smoothing:antialiased;
}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#3A3A3C;border-radius:10px}
::-webkit-scrollbar-thumb:hover{background:#636366}

/* Cards — glassmorphism */
.card{
  background:rgba(28,28,30,0.75) !important;
  backdrop-filter:blur(40px) saturate(180%) !important;
  -webkit-backdrop-filter:blur(40px) saturate(180%) !important;
  border:1px solid rgba(255,255,255,0.10) !important;
  border-radius:16px !important;
  box-shadow:0 2px 4px rgba(0,0,0,0.4),0 8px 24px rgba(0,0,0,0.3),
             inset 0 1px 0 rgba(255,255,255,0.08) !important;
  transition:box-shadow .25s ease;
}
.card:hover{
  box-shadow:0 4px 8px rgba(0,0,0,0.5),0 16px 40px rgba(0,0,0,0.4),
             inset 0 1px 0 rgba(255,255,255,0.10) !important;
}
.card-header{
  background:rgba(44,44,46,0.6) !important;
  border-bottom:1px solid rgba(255,255,255,0.07) !important;
  color:rgba(235,235,245,0.6) !important;
  font-size:0.67rem !important;
  font-weight:600 !important;
  letter-spacing:0.07em !important;
  text-transform:uppercase !important;
  padding:0.5rem 1rem !important;
}
.card-body{padding:0.75rem !important;overflow:hidden}

/* Nav tabs — segmented control style */
.nav-tabs{
  border-bottom:none !important;
  background:rgba(44,44,46,0.6) !important;
  border-radius:10px !important;
  padding:3px !important;
  gap:2px !important;
  margin:0 0.5rem 0.5rem !important;
  display:inline-flex !important;
  width:auto !important;
}
.nav-tabs .nav-link{
  color:rgba(235,235,245,0.6) !important;
  font-size:0.72rem !important;
  font-weight:500 !important;
  border:none !important;
  border-radius:8px !important;
  padding:0.35rem 0.9rem !important;
  transition:all .2s cubic-bezier(.34,1.56,.64,1);
  white-space:nowrap;
}
.nav-tabs .nav-link:hover{color:#fff !important;background:rgba(255,255,255,0.08) !important}
.nav-tabs .nav-link.active{
  background:rgba(255,255,255,0.15) !important;
  color:#fff !important;
  font-weight:600 !important;
  box-shadow:0 1px 4px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.1) !important;
}

/* Inputs */
label,.form-label{
  color:rgba(235,235,245,0.6) !important;
  font-size:0.63rem !important;
  font-weight:600 !important;
  letter-spacing:0.06em !important;
  text-transform:uppercase !important;
  margin-bottom:0.2rem !important;
}
.form-select{
  background-color:#2C2C2E !important;
  border:1px solid rgba(255,255,255,0.12) !important;
  color:#fff !important;
  border-radius:10px !important;
  font-size:0.82rem !important;
  padding:0.42rem 0.75rem !important;
  transition:border-color .2s,box-shadow .2s;
}
.form-select:focus{border-color:#0A84FF !important;box-shadow:0 0 0 3px rgba(10,132,255,.25) !important}
.selectize-input{
  background:#2C2C2E !important;
  border:1px solid rgba(255,255,255,0.12) !important;
  color:#fff !important;
  border-radius:10px !important;
  font-size:0.82rem !important;
  box-shadow:none !important;
  padding:0.38rem 0.75rem !important;
  min-height:36px !important;
}
.selectize-input.focus{border-color:#0A84FF !important;box-shadow:0 0 0 3px rgba(10,132,255,.25) !important}
.selectize-input .item{
  background:rgba(10,132,255,0.2) !important;
  color:#0A84FF !important;
  border-radius:6px !important;
  padding:2px 8px !important;
  font-size:0.73rem !important;
  border:none !important;
}
.selectize-dropdown{
  background:rgba(44,44,46,0.97) !important;
  backdrop-filter:blur(40px) !important;
  border:1px solid rgba(255,255,255,0.12) !important;
  border-radius:12px !important;
  box-shadow:0 8px 32px rgba(0,0,0,0.6) !important;
  overflow:hidden !important;
  padding:4px !important;
}
.selectize-dropdown .option{
  color:#fff !important;
  font-size:0.82rem !important;
  padding:0.4rem 0.75rem !important;
  border-radius:8px !important;
}
.selectize-dropdown .option:hover,.selectize-dropdown .option.active{
  background:rgba(10,132,255,0.25) !important;
}
.selectize-dropdown .optgroup-header{
  color:#0A84FF !important;
  font-size:0.6rem !important;
  font-weight:700 !important;
  letter-spacing:0.1em !important;
  text-transform:uppercase !important;
  padding:0.5rem 0.75rem 0.1rem !important;
}

/* Slider */
.irs--shiny .irs-bar{background:#0A84FF !important;border:none !important;height:4px !important;border-radius:2px !important}
.irs--shiny .irs-line{background:#3A3A3C !important;border:none !important;height:4px !important;border-radius:2px !important}
.irs--shiny .irs-handle>i:first-child{
  background:#fff !important;border:none !important;
  width:20px !important;height:20px !important;border-radius:50% !important;
  box-shadow:0 2px 8px rgba(0,0,0,.5) !important;top:-8px !important;
}
.irs--shiny .irs-from,.irs--shiny .irs-to,.irs--shiny .irs-single{
  background:#2C2C2E !important;color:#fff !important;
  font-size:0.67rem !important;font-weight:600 !important;
  border-radius:6px !important;padding:2px 6px !important;
  box-shadow:0 2px 6px rgba(0,0,0,.4) !important;
}
.irs--shiny .irs-min,.irs--shiny .irs-max{
  color:rgba(235,235,245,0.38) !important;font-size:0.6rem !important;background:transparent !important;
}

/* Masthead */
.masthead{display:flex;align-items:center;gap:.9rem;padding:0 1rem;height:100%}
.masthead-icon{
  width:36px;height:36px;border-radius:10px;
  background:linear-gradient(145deg,#0A84FF,#5E5CE6);
  display:flex;align-items:center;justify-content:center;
  font-size:1.1rem;flex-shrink:0;
  box-shadow:0 2px 8px rgba(10,132,255,0.4);
}
.masthead-text{display:flex;flex-direction:column;gap:1px}
.masthead-title{
  font-family:-apple-system,'SF Pro Display',sans-serif;
  font-size:1.1rem;font-weight:700;color:#fff;
  letter-spacing:-.02em;line-height:1;
}
.masthead-sub{font-size:.6rem;font-weight:400;color:rgba(235,235,245,0.38);letter-spacing:.02em}

/* Quick stats */
.qstrip{display:flex;align-items:center;padding:0 .5rem;height:100%;overflow:hidden}
.qstrip-context{
  font-size:.65rem;font-weight:500;color:rgba(235,235,245,0.6);
  white-space:nowrap;padding-right:1rem;margin-right:.5rem;
  border-right:1px solid #38383A;
}
.qstrip-item{
  display:flex;flex-direction:column;gap:1px;flex:1;
  padding:0 .75rem;border-right:1px solid rgba(255,255,255,0.06);
}
.qstrip-item:last-child{border-right:none}
.qstrip-label{font-size:.56rem;font-weight:600;color:rgba(235,235,245,0.38);text-transform:uppercase;letter-spacing:.07em}
.qstrip-value{
  font-family:-apple-system,'SF Pro Display',sans-serif;
  font-size:1.25rem;font-weight:700;line-height:1;letter-spacing:-.02em;
}

/* Section labels */
.sec-label{
  display:block;font-size:.62rem;font-weight:600;
  color:rgba(235,235,245,0.6);text-transform:uppercase;
  letter-spacing:.07em;margin:.85rem 0 .28rem;
}
.sec-label:first-child{margin-top:0}

/* Story boxes */
.story-box{
  background:rgba(10,132,255,0.14);
  border:1px solid rgba(10,132,255,0.32);
  border-radius:10px;padding:.6rem .8rem;margin-top:.35rem;
  font-size:.72rem;color:rgba(235,235,245,0.85);line-height:1.55;
  flex-shrink:0;
}
.story-box b{color:#fff;font-weight:600}
.story-box em{color:#0A84FF;font-style:normal;font-weight:500}

/* KPI cards */
.kpi-wrap{
  display:flex;flex-direction:column;justify-content:center;
  padding:.8rem 1rem;height:100%;gap:.12rem;
  position:relative;overflow:hidden;
}
.kpi-label{font-size:.6rem;font-weight:600;color:rgba(235,235,245,0.6);text-transform:uppercase;letter-spacing:.07em}
.kpi-value{
  font-family:-apple-system,'SF Pro Display',sans-serif;
  font-size:1.95rem;font-weight:700;line-height:1;letter-spacing:-.03em;
}
.kpi-desc{font-size:.62rem;color:rgba(235,235,245,0.38);line-height:1.4;margin-top:.1rem}
.kpi-dot{
  display:inline-block;width:6px;height:6px;border-radius:50%;
  margin-right:5px;vertical-align:middle;position:relative;top:-1px;
}

/* Fade-up entrance */
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.card{animation:fadeUp .4s ease both}

/* Full screen button */
.bslib-full-screen-enter svg{color:rgba(235,235,245,0.6) !important}
"""

# ── Narratives ────────────────────────────────────────────────────────────────
TREND_NARRATIVE = {
    "Population Aged 65+ (%)":
        "<b>The share of people aged 65+ has doubled globally since 1960, reaching 10% by 2022.</b> "
        "The acceleration after 2000 reflects baby-boom cohorts entering old age. "
        "Japan leads at over 28%, while many African nations remain below 3%.",
    "Fertility Rate (births/woman)":
        "<b>Global fertility dropped from ~5 births/woman in 1960 to 2.3 in 2022</b> — approaching the 2.1 replacement threshold. "
        "Select individual countries to explore how development and education accelerate this convergence.",
    "Life Expectancy (years)":
        "<b>Global life expectancy rose nearly 25 years between 1960 and 2022</b> — one of humanity's greatest public-health achievements. "
        "The visible dip around 2020 reflects COVID-19 reversing decades of progress.",
    "Old-Age Dependency Ratio (%)":
        "<b>The old-age dependency ratio measures fiscal pressure on working populations.</b> "
        "In Japan and Southern Europe it exceeds 50% — one pensioner per two workers — straining pension systems.",
    "Child Mortality (per 1,000)":
        "<b>Under-5 mortality has fallen over 75% since 1960.</b> "
        "This is the primary driver of fertility decline: as child survival improves, families need fewer births.",
    "Urban Population (%)":
        "<b>The world crossed the 50% urban threshold around 2007 — a historic first.</b> "
        "Urbanisation strongly correlates with demographic transition: city-dwellers have fewer children and longer lives.",
    "GDP per Capita (USD)":
        "<b>GDP per capita is the strongest single predictor of demographic outcomes.</b> "
        "Richer countries uniformly show lower fertility, higher life expectancy, and older populations.",
    "Health Expenditure (% of GDP)":
        "<b>Health spending ranges from under 2% to over 16% of GDP.</b> "
        "Higher spending correlates with longer life expectancy, with diminishing returns above ~8%.",
    "Secondary School Enrollment (%)":
        "<b>Female secondary education is the most powerful lever for reducing fertility.</b> "
        "Countries crossing 80% female enrollment have almost universally fallen below replacement-level fertility. "
        "<em>Note: this is the World Bank's gross enrollment ratio (SE.SEC.ENRR) — total enrollment divided by the official secondary-age population. "
        "Values can legitimately exceed 100% when over-age or under-age students are also enrolled.</em>",
    "Net Migration (thousands)":
        "<b>Migration is the wildcard in demographic projections.</b> "
        "Ageing countries in Europe receive large inflows offsetting population decline.",
}

MAP_NARRATIVE = (
    "<b>Geography is destiny in demography.</b> The map reveals a stark North–South divide: "
    "high-income countries concentrate the deepest ageing, while younger populations dominate Sub-Saharan Africa. "
    "<em>Click any country</em> to update all panels instantly."
)
PYRAMID_NARRATIVE = (
    "<b>The population pyramid is a demographic fingerprint.</b> "
    "A wide base signals a young, growing population; top-heavy shapes signal ageing and low fertility. "
    "Compare Japan or Germany with Nigeria's broad base. Slide through years to watch the transformation. "
    "<em>The \"World average\" view is a simple country mean — small countries influence the shape as much as large ones, "
    "so for population-weighted reality pick a specific country.</em>"
)
SCATTER_NARRATIVE = (
    "<b>Fertility and life expectancy are two sides of the same demographic coin.</b> "
    "Bubble size encodes GDP per capita. The dashed line marks the 2.1 replacement threshold — "
    "every dot above it represents a still-growing population."
)
COMPARE_NARRATIVE = (
    "<b>Comparing countries reveals the uneven pace of demographic change.</b> "
    "High-income countries completed the transition decades earlier — yet many are converging. "
    "Outliers (conflict states, oil economies) break the expected pattern."
)

# ── UI helpers ────────────────────────────────────────────────────────────────
def story(html):
    return ui.tags.div(ui.HTML(html), class_="story-box")

def sec(text):
    return ui.tags.span(text, class_="sec-label")

# ── App UI ────────────────────────────────────────────────────────────────────
app_ui = ui.page_fillable(
    ui.tags.style(_CSS),
    ui.tags.script(_MAP_CLICK_JS),

    # Row 0: Masthead + quick stats
    ui.layout_columns(
        ui.card(
            ui.card_body(
                ui.tags.div(
                    ui.tags.div(
                        ui.HTML(
                            '<svg width="22" height="22" viewBox="0 0 24 24" '
                            'fill="none" stroke="#ffffff" stroke-width="1.6" '
                            'stroke-linecap="round" stroke-linejoin="round" '
                            'aria-label="Globe" role="img">'
                            '<circle cx="12" cy="12" r="9.5"/>'
                            '<ellipse cx="12" cy="12" rx="3.5" ry="9.5"/>'
                            '<path d="M2.5 12h19"/>'
                            '<path d="M4 7c2 1 5 2 8 2s6-1 8-2"/>'
                            '<path d="M4 17c2-1 5-2 8-2s6 1 8 2"/>'
                            '</svg>'
                        ),
                        class_="masthead-icon",
                    ),
                    ui.tags.div(
                        ui.tags.div("Aging World", class_="masthead-title"),
                        ui.tags.div(
                            "Global Demographic Observatory · World Bank · 1960–2022",
                            class_="masthead-sub",
                        ),
                        class_="masthead-text",
                    ),
                    class_="masthead",
                ),
                style="padding:0;height:100%;",
            ),
        ),
        ui.card(
            ui.card_body(
                ui.output_ui("quickstats"),
                style="padding:0;height:100%;",
            ),
        ),
        col_widths=[3, 9],
        style="height:62px;flex-shrink:0;",
    ),

    # Row 1: Sidebar + chart tabs
    ui.layout_columns(
        ui.card(
            ui.card_header("Controls"),
            ui.card_body(
                sec("Indicator"),
                ui.input_select(
                    "metric", label=None,
                    choices={
                        grp: {k: k for k in keys}
                        for grp, keys in METRIC_GROUPS.items()
                    },
                    selected="Population Aged 65+ (%)",
                ),
                sec("Year"),
                ui.input_slider("year", label=None,
                                min=1960, max=2022, value=2022, step=1, sep=""),
                sec("Country"),
                ui.input_selectize("country", label=None, choices=[], selected=None,
                                   options={"placeholder": "World average…"}),
                ui.tags.hr(style="border:none;border-top:1px solid #38383A;margin:.8rem 0;"),
                sec("Compare (up to 5)"),
                ui.input_selectize(
                    "countries_multi", label=None, choices=[],
                    selected=None, multiple=True,
                    options={"maxItems": 5, "placeholder": "Add countries…"},
                ),
                style="overflow-y:auto;height:100%;",
            ),
        ),
        ui.navset_card_tab(
            ui.nav_panel("📈  Trend",
                output_widget("trend_chart"),
                ui.output_ui("trend_story"),
            ),
            ui.nav_panel("🔺  Pyramid",
                output_widget("pyramid_chart"),
                ui.output_ui("pyramid_story"),
            ),
            ui.nav_panel("↔  Compare",
                output_widget("compare_chart"),
                ui.output_ui("compare_story"),
            ),
            full_screen=True,
        ),
        col_widths=[3, 9],
        style="flex:2;min-height:400px;",
    ),

    # Row 2: Map + scatter
    ui.layout_columns(
        ui.card(
            ui.card_header("🗺  World Map — click a country"),
            ui.card_body(
                output_widget("choropleth_map", height="320px"),
                ui.output_ui("map_story"),
                style="display:flex;flex-direction:column;gap:.4rem;",
            ),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("⬤  Fertility · Life Expectancy · GDP"),
            ui.card_body(
                output_widget("scatter_chart", height="300px"),
                ui.output_ui("scatter_story"),
                style="display:flex;flex-direction:column;gap:.4rem;",
            ),
            full_screen=True,
        ),
        col_widths=[5, 7],
        style="flex:1.6;min-height:460px;",
    ),

    # Row 3: KPI strip
    ui.layout_columns(
        ui.card(ui.card_body(ui.output_ui("kpi_aged"),       style="padding:0;")),
        ui.card(ui.card_body(ui.output_ui("kpi_fertility"),  style="padding:0;")),
        ui.card(ui.card_body(ui.output_ui("kpi_life"),       style="padding:0;")),
        ui.card(ui.card_body(ui.output_ui("kpi_dependency"), style="padding:0;")),
        col_widths=[3, 3, 3, 3],
        style="height:100px;flex-shrink:0;",
    ),

    padding="0.6rem",
    gap="0.6rem",
)


# ── Server ────────────────────────────────────────────────────────────────────
def server(input: Inputs, output: Outputs, session: Session):

    # Poll every 15 s so pyramid_chart re-renders once the background
    # download writes cache/pyramid.csv.
    @reactive.poll(lambda: os.path.exists(CACHE_PYRAMID), interval_secs=15)
    def _pyramid_cached():
        return os.path.exists(CACHE_PYRAMID)

    @reactive.calc
    def df():
        return get_data()

    @reactive.effect
    def _populate():
        data = df()
        countries = sorted(data["country"].dropna().unique().tolist())
        ui.update_selectize("country",
                            choices=["(World average)"] + countries,
                            selected="(World average)", session=session)
        ui.update_selectize("countries_multi", choices=countries,
                            selected=["Germany", "Japan", "Nigeria",
                                      "India", "United States"],
                            session=session)

    @reactive.effect
    def _map_click():
        c = input.map_clicked_country()
        if c:
            ui.update_selectize("country", selected=c, session=session)

    @reactive.calc
    def map_df():
        data = df()
        return data[(data["metric"] == input.metric()) &
                    (data["year"] == input.year())].dropna(subset=["value"])

    @reactive.calc
    def trend_df():
        data = df()
        sub = data[data["metric"] == input.metric()]
        c = input.country()
        if not c or c == "(World average)":
            return sub.groupby("year", as_index=False)["value"].mean().assign(country="World average")
        return sub[sub["country"] == c][["year", "value", "country"]].dropna()

    @reactive.calc
    def compare_df():
        data = df()
        sel = list(input.countries_multi() or [])
        if not sel:
            return pd.DataFrame(columns=["year", "value", "country"])
        return data[(data["metric"] == input.metric()) &
                    (data["country"].isin(sel))][["year", "value", "country"]].dropna()

    @reactive.calc
    def scatter_df():
        data = df()
        year = input.year()
        def pull(metric, col):
            return (data[(data["metric"] == metric) & (data["year"] == year)]
                    [["country", "value"]].rename(columns={"value": col}))
        fert = (data[(data["metric"] == "Fertility Rate (births/woman)") & (data["year"] == year)]
                [["country", "country_code", "value"]].rename(columns={"value": "fertility"}))
        life = pull("Life Expectancy (years)", "life_exp")
        gdp  = pull("GDP per Capita (USD)", "gdp")
        aged = pull("Population Aged 65+ (%)", "aged_pct")
        return (fert.merge(life, on="country")
                    .merge(gdp, on="country", how="left")
                    .merge(aged, on="country")
                    .dropna(subset=["fertility", "life_exp", "aged_pct"]))

    @reactive.calc
    def kpi_values():
        data = df()
        year = input.year()
        c = input.country()
        result = {}
        for label in ["Population Aged 65+ (%)", "Fertility Rate (births/woman)",
                      "Life Expectancy (years)", "Old-Age Dependency Ratio (%)"]:
            sub = data[(data["metric"] == label) & (data["year"] == year)]
            if not c or c == "(World average)":
                val = sub["value"].mean()
            else:
                row = sub[sub["country"] == c]["value"]
                val = row.iloc[0] if not row.empty else float("nan")
            result[label] = round(val, 2) if pd.notna(val) else None
        return result

    @render.ui
    def quickstats():
        c = input.country() or "(World average)"
        lbl = c if c != "(World average)" else "World average"
        vals = kpi_values()
        items = [
            ("Pop. 65+",   vals.get("Population Aged 65+ (%)"),       "%",    BLUE),
            ("Fertility",  vals.get("Fertility Rate (births/woman)"),  "",     TEAL),
            ("Life Exp.",  vals.get("Life Expectancy (years)"),        " yr",  ORANGE),
            ("Dependency", vals.get("Old-Age Dependency Ratio (%)"),   "%",    PURPLE),
        ]
        children = [ui.tags.span(f"{lbl}  ·  {input.year()}", class_="qstrip-context")]
        for label, val, unit, color in items:
            display = f"{val}{unit}" if val is not None else "–"
            children.append(ui.tags.div(
                ui.tags.div(label, class_="qstrip-label"),
                ui.tags.div(display, class_="qstrip-value", style=f"color:{color};"),
                class_="qstrip-item",
            ))
        return ui.tags.div(*children, class_="qstrip")

    @render_widget
    def choropleth_map():
        mdf = map_df()
        metric = input.metric()
        fig = px.choropleth(
            mdf, locations="country_code", color="value",
            hover_name="country", custom_data=["country"],
            color_continuous_scale=[[0,"#1C1C1E"],[0.2,"#0A3060"],
                                    [0.5,"#0A84FF"],[0.75,"#FF9F0A"],[1,"#FF453A"]],
            labels={"value": metric},
            title=f"{metric}  ·  {input.year()}",
        )
        fig.update_layout(
            **_geo(),
            coloraxis_colorbar=dict(title="", thickness=8, len=0.5,
                                    tickfont=dict(color=T3, size=9),
                                    outlinecolor="rgba(0,0,0,0)",
                                    bgcolor="rgba(0,0,0,0)"),
            geo=dict(showframe=False, projection_type="natural earth",
                     showcoastlines=True, coastlinecolor=BG3,
                     showland=True, landcolor="#1C1C1E",
                     showocean=True, oceancolor="#000000",
                     showcountries=True, countrycolor=SEP,
                     bgcolor="rgba(0,0,0,0)"),
        )
        return fig

    @render_widget
    def trend_chart():
        tdf = trend_df()
        c = input.country() or "World average"
        metric = input.metric()
        yr = input.year()
        fig = px.area(tdf, x="year", y="value",
                      title=f"{metric}  ·  {c}",
                      labels={"value": metric, "year": "Year"})
        fig.update_traces(line_color=BLUE, line_width=2.5,
                          fillcolor="rgba(10,132,255,0.12)")
        fig.update_layout(**_xy())
        if metric == "Fertility Rate (births/woman)":
            fig.add_hline(y=2.1, line_dash="dot", line_color=ORANGE, opacity=0.7,
                          annotation_text="Replacement (2.1)",
                          annotation_position="top right",
                          annotation_font=dict(size=10, color=ORANGE))
        elif metric == "Secondary School Enrollment (%)":
            fig.add_hline(y=100, line_dash="dot", line_color=TEAL, opacity=0.7,
                          annotation_text="100% (gross ratio threshold)",
                          annotation_position="top right",
                          annotation_font=dict(size=10, color=TEAL))
        yr_row = tdf[tdf["year"] == yr]
        if not yr_row.empty:
            val = yr_row["value"].iloc[0]
            fig.add_vline(x=yr, line_color=BLUE, line_width=1, line_dash="dot", opacity=0.6)
            fig.add_annotation(x=yr, y=val, text=f"  {val:.1f}",
                               showarrow=False, font_color=BLUE, font_size=12,
                               xanchor="left", yanchor="bottom")
        return fig

    @render_widget
    def compare_chart():
        cdf = compare_df()
        metric = input.metric()
        if cdf.empty:
            fig = go.Figure()
            fig.add_annotation(text="← Add countries in the sidebar",
                               showarrow=False, font_color=T3, font_size=13,
                               xref="paper", yref="paper", x=0.5, y=0.5)
            fig.update_layout(**_xy())
            return fig
        fig = px.line(cdf, x="year", y="value", color="country",
                      title=f"{metric}  ·  Country Comparison",
                      labels={"value": metric, "year": "Year", "country": ""},
                      color_discrete_sequence=PALETTE)
        fig.update_traces(line_width=2.5)
        fig.update_layout(**_xy())
        return fig

    @render_widget
    def scatter_chart():
        sdf = scatter_df()
        year = input.year()
        if sdf.empty:
            fig = go.Figure()
            fig.add_annotation(text="Loading…", showarrow=False, font_color=T3,
                               xref="paper", yref="paper", x=0.5, y=0.5)
            fig.update_layout(**_xy())
            return fig
        sdf = sdf.copy()
        # shinywidgets serializes Plotly customdata with stdlib json, so make
        # missing GDP values explicit strings instead of NaN.
        sdf["gdp_hover"] = sdf["gdp"].map(
            lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A"
        )
        sdf["bubble"] = np.where(sdf["gdp"].isna(),
                                 sdf["aged_pct"] * 5,
                                 np.log1p(sdf["gdp"].fillna(0)))
        sdf = sdf.drop(columns=["gdp"])
        fig = px.scatter(
            sdf, x="life_exp", y="fertility",
            size="bubble", size_max=32,
            hover_name="country",
            hover_data={
                "bubble": False,
                "aged_pct": ":.1f",
                "gdp_hover": True,
            },
            color="aged_pct",
            color_continuous_scale=[[0, TEAL],[0.4, ORANGE],[1, RED]],
            labels={"life_exp": "Life Expectancy (years)",
                    "fertility": "Fertility Rate (births/woman)",
                    "aged_pct": "Pop. 65+ (%)",
                    "gdp_hover": "GDP per capita (USD)"},
            title=f"Fertility vs. Life Expectancy  ·  {year}",
        )
        fig.add_hline(y=2.1, line_dash="dot", line_color=T3, opacity=0.5,
                      annotation_text="Replacement (2.1)",
                      annotation_position="top right",
                      annotation_font=dict(size=9, color=T3))
        c = input.country()
        if c and c != "(World average)":
            row = sdf[sdf["country"] == c]
            if not row.empty:
                fig.add_trace(go.Scatter(
                    x=row["life_exp"], y=row["fertility"],
                    mode="markers+text",
                    marker=dict(color=BLUE, size=14, line=dict(color=TEXT, width=2)),
                    text=row["country"], textposition="top center",
                    textfont=dict(color=BLUE, size=10), showlegend=False,
                ))
        fig.update_layout(**_xy(
            coloraxis_colorbar=dict(title="65+ %", thickness=8, len=0.4,
                                   tickfont=dict(color=T3, size=9),
                                   outlinecolor="rgba(0,0,0,0)",
                                   bgcolor="rgba(0,0,0,0)"),
        ))
        return fig

    @render_widget
    def pyramid_chart():
        _pyramid_cached()          # reactive dependency — re-renders when file appears
        year = input.year()
        country = input.country() or "(World average)"
        pdata = get_pyramid_data()
        def empty(msg):
            fig = go.Figure()
            fig.add_annotation(text=msg, showarrow=False, font_color=T3,
                               xref="paper", yref="paper", x=0.5, y=0.5)
            fig.update_layout(**_xy())
            return fig
        if pdata.empty:
            return empty("First-run download in progress (~3–5 min). This view will refresh automatically.")
        if country == "(World average)":
            sub = pdata[pdata["year"] == year].groupby(
                ["age_group", "gender"], as_index=False)["value"].mean()
        else:
            sub = pdata[(pdata["country"] == country) & (pdata["year"] == year)][
                ["age_group", "gender", "value"]].copy()
        if sub.empty:
            return empty("No data for this selection")
        pivoted = sub.pivot_table(index="age_group", columns="gender",
                                  values="value", aggfunc="sum").reset_index()
        for col in ("male", "female"):
            if col not in pivoted.columns:
                pivoted[col] = 0.0
        age_order = [lbl for lbl, _ in AGE_GROUPS]
        pivoted["age_group"] = pd.Categorical(pivoted["age_group"],
                                              categories=age_order, ordered=True)
        pivoted = pivoted.sort_values("age_group")
        total = pivoted[["male", "female"]].sum().sum()
        if not total or pd.isna(total):
            return empty("No data for this selection")
        pivoted["mp"] = -(pivoted["male"] / total * 100)
        pivoted["fp"] =   pivoted["female"] / total * 100
        pivoted["male_m"]   = pivoted["male"]   / 1_000_000
        pivoted["female_m"] = pivoted["female"] / 1_000_000
        mv = max(pivoted["fp"].max(), abs(pivoted["mp"].min()))
        tv = [-mv, -mv/2, 0, mv/2, mv]
        tt = [f"{abs(v):.1f}%" for v in tv]
        fig = go.Figure([
            go.Bar(
                y=pivoted["age_group"], x=pivoted["mp"], name="Male",
                orientation="h", marker_color=INDIGO, marker_opacity=0.9,
                customdata=np.stack([pivoted["male_m"], pivoted["mp"].abs()], axis=-1),
                hovertemplate=(
                    "<b>Male · %{y}</b><br>"
                    "Share: %{customdata[1]:.2f}%<br>"
                    "Population: %{customdata[0]:.2f} M"
                    "<extra></extra>"
                ),
            ),
            go.Bar(
                y=pivoted["age_group"], x=pivoted["fp"], name="Female",
                orientation="h", marker_color=PINK, marker_opacity=0.9,
                customdata=np.stack([pivoted["female_m"], pivoted["fp"]], axis=-1),
                hovertemplate=(
                    "<b>Female · %{y}</b><br>"
                    "Share: %{customdata[1]:.2f}%<br>"
                    "Population: %{customdata[0]:.2f} M"
                    "<extra></extra>"
                ),
            ),
        ])
        fig.update_layout(
            **_xy(
                barmode="overlay", bargap=0.1,
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
                            font_color=T2),
                title=f"Population Pyramid  ·  {country}  ({year})",
                xaxis=dict(title="% of population", tickvals=tv, ticktext=tt,
                           range=[-mv*1.12, mv*1.12], showgrid=True, gridcolor=SEP,
                           zeroline=True, zerolinecolor=BG3, color=T3,
                           tickfont_size=10),
                yaxis=dict(showgrid=False, color=T3, tickfont_size=10),
            ),
        )
        return fig

    @render.ui
    def trend_story():   return story(TREND_NARRATIVE.get(input.metric(), ""))
    @render.ui
    def pyramid_story(): return story(PYRAMID_NARRATIVE)
    @render.ui
    def compare_story(): return story(COMPARE_NARRATIVE)
    @render.ui
    def map_story():     return story(MAP_NARRATIVE)
    @render.ui
    def scatter_story(): return story(SCATTER_NARRATIVE)

    def _kpi(label, fmt, color, dot_color):
        val = kpi_values().get(label)
        display = fmt.format(val) if val is not None else "–"
        desc = METRIC_DESCRIPTIONS.get(label, "").split(".")[0] + "."
        return ui.HTML(
            f'<div class="kpi-wrap">'
            f'<div class="kpi-label">'
            f'<span class="kpi-dot" style="background:{dot_color}"></span>{label}'
            f'</div>'
            f'<div class="kpi-value" style="color:{color}">{display}</div>'
            f'<div class="kpi-desc">{desc}</div>'
            f'</div>'
        )

    @render.ui
    def kpi_aged():
        return _kpi("Population Aged 65+ (%)",      "{:.1f}%",   BLUE,   BLUE)
    @render.ui
    def kpi_fertility():
        return _kpi("Fertility Rate (births/woman)", "{:.2f}",    TEAL,   TEAL)
    @render.ui
    def kpi_life():
        return _kpi("Life Expectancy (years)",       "{:.1f} yr", ORANGE, ORANGE)
    @render.ui
    def kpi_dependency():
        return _kpi("Old-Age Dependency Ratio (%)",  "{:.1f}%",   PURPLE, PURPLE)


app = App(app_ui, server)
