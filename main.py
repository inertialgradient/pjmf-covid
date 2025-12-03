from __future__ import annotations

from datetime import datetime
from typing import Tuple, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_URL = "https://data.cdc.gov/api/views/cf5u-bm9w/rows.csv"
LOCAL_DATA_PATH = "data.csv"
COLUMN_RENAME_MAP = {"monthlyrate": "hospitalization_rate"}

STATE_ABBR: Dict[str, str] = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

DEFAULT_STATES = ["COVID-NET", "New York", "California"]


# ---------------------------------------------------------------------
# Data fetching + preprocessing
# ---------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_remote_data() -> pd.DataFrame | None:
    """Try fetching remote CDC data (TTL = 1 hour)."""
    try:
        return pd.read_csv(DATA_URL)
    except Exception:
        return None


@st.cache_data
def load_local_data() -> pd.DataFrame:
    return pd.read_csv(LOCAL_DATA_PATH)


@st.cache_data
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, parse dates, standardize fields."""
    cleaned = df.copy()
    cleaned.columns = [c.strip().lower().replace(" ", "_") for c in cleaned.columns]
    cleaned = cleaned.rename(columns=COLUMN_RENAME_MAP)

    # Clean _yearmonth -> YYYYMM string
    cleaned["_yearmonth"] = (
        cleaned["_yearmonth"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )

    cleaned["date"] = pd.to_datetime(
        cleaned["_yearmonth"] + "01", format="%Y%m%d", errors="coerce"
    )
    cleaned = cleaned.dropna(subset=["date"])

    # Ensure hospitalization_rate is numeric
    if "hospitalization_rate" in cleaned.columns:
        cleaned["hospitalization_rate"] = pd.to_numeric(
            cleaned["hospitalization_rate"], errors="coerce"
        )
        cleaned = cleaned.dropna(subset=["hospitalization_rate"])

    return cleaned


def get_data() -> Tuple[pd.DataFrame, str]:
    """
    Return preprocessed data and a human-readable "last updated" string.
    Prefer remote; fall back to local.
    """
    remote = fetch_remote_data()
    if remote is not None:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        return preprocess(remote), ts

    local = load_local_data()
    ts = "Local file (remote fetch failed)"
    return preprocess(local), ts


# ---------------------------------------------------------------------
# Canonical slice (All/All/All, Crude) - used as first choice
# ---------------------------------------------------------------------
def canonical_slice(df: pd.DataFrame) -> pd.DataFrame:
    """
    Canonical CDC reporting line:
      Age = All, Sex = All, Race = All, Type contains 'Crude'.
    """
    if not {"sex_label", "race_label", "agecategory_legend", "type"}.issubset(df.columns):
        return df.iloc[0:0]

    canonical = df[
        (df["sex_label"] == "All")
        & (df["race_label"] == "All")
        & (df["agecategory_legend"] == "All")
        & (df["type"].str.contains("Crude", na=False))
    ]
    return canonical


# ---------------------------------------------------------------------
# Sidebar and filters
# ---------------------------------------------------------------------
def render_sidebar(
    df: pd.DataFrame, last_updated: str
) -> Tuple[Tuple[datetime, datetime], Dict[str, List[str]]]:
    st.sidebar.header("Data Controls")

    # Last updated indicator
    st.sidebar.caption(f"Last updated at: **{last_updated}**")

    # Date range
    min_date = df["date"].min().to_pydatetime()
    max_date = df["date"].max().to_pydatetime()
    date_range = st.sidebar.slider(
        "Date range:",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM",
    )

    # Dynamically derive options after date filtering
    df_for_options = df[(df["date"] >= date_range[0]) & (df["date"] <= date_range[1])]

    filter_config = {
        "state": "Filter by state:",
        "agecategory_legend": "Filter by age group:",
        "sex_label": "Filter by sex:",
        "race_label": "Filter by race:",
    }

    # Manage persistent filter selections
    if "filters" not in st.session_state:
        st.session_state["filters"] = {k: [] for k in filter_config}

    # Clear all button – reset widget keys and stored selections
    if st.sidebar.button("Clear all filters"):
        for col in filter_config:
            widget_key = f"filter-{col}"
            st.session_state[widget_key] = []
            st.session_state["filters"][col] = []
        st.rerun()

    selections: Dict[str, List[str]] = {}
    for col, label in filter_config.items():
        options = sorted(df_for_options[col].dropna().unique())
        widget_key = f"filter-{col}"
        selections[col] = st.sidebar.multiselect(
            label,
            options,
            default=st.session_state["filters"].get(col, []),
            key=widget_key,
        )
        st.session_state["filters"][col] = selections[col]

    return date_range, selections


def apply_filters(
    df: pd.DataFrame,
    date_range: Tuple[datetime, datetime],
    selections: Dict[str, List[str]],
) -> pd.DataFrame:
    filtered = df[(df["date"] >= date_range[0]) & (df["date"] <= date_range[1])]
    for col, vals in selections.items():
        if vals:
            filtered = filtered[filtered[col].isin(vals)]
    return filtered


# ---------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------
def restrict_initial_states(df: pd.DataFrame, selections: Dict[str, List[str]]) -> pd.DataFrame:
    """When no state is selected, limit the chart to a small default set."""
    if selections.get("state"):
        return df

    if df.empty:
        return df

    available_defaults = [s for s in DEFAULT_STATES if s in df["state"].unique()]
    if not available_defaults:
        available_defaults = sorted(df["state"].unique())[:3]

    return df[df["state"].isin(available_defaults)]


def aggregate_for_time_series(base_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate to one value per state/date using mean.
    Works for both canonical and fallback data.
    """
    if base_df.empty:
        return base_df
    return (
        base_df.groupby(["state", "date"], as_index=False)["hospitalization_rate"]
        .mean()
        .sort_values("date")
    )


def render_time_series(df: pd.DataFrame) -> None:
    st.subheader("Trend Over Time")

    if df.empty:
        st.info("No data available for the selected filters.")
        return

    fig = px.line(
        df,
        x="date",
        y="hospitalization_rate",
        color="state",
        labels={"hospitalization_rate": "Rate per 100,000"},
    )
    st.plotly_chart(fig, use_container_width=True)


def aggregate_for_map(base_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate to one value per state for the latest date using mean.
    """
    if base_df.empty:
        return base_df

    latest_date = base_df["date"].max()
    latest = base_df[base_df["date"] == latest_date].copy()
    if latest.empty:
        return latest

    latest_grouped = (
        latest.groupby("state", as_index=False)["hospitalization_rate"].mean()
    )
    return latest_grouped


def render_choropleth(base_df: pd.DataFrame) -> None:
    st.subheader("Latest Hospitalization Rate by State")

    latest_grouped = aggregate_for_map(base_df)
    if latest_grouped.empty:
        st.info("No data available for the latest date.")
        return

    # Map state names to 2-letter codes, drop non-state rows (e.g., 'COVID-NET')
    latest_grouped["state_code"] = latest_grouped["state"].map(STATE_ABBR)
    latest_grouped = latest_grouped.dropna(subset=["state_code"])
    if latest_grouped.empty:
        st.info("No state-level data available for the map.")
        return

    fig = px.choropleth(
        latest_grouped,
        locations="state_code",
        locationmode="USA-states",
        color="hospitalization_rate",
        scope="usa",
        color_continuous_scale="Reds",
        labels={"hospitalization_rate": "Rate per 100,000"},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_data_table(df: pd.DataFrame) -> None:
    st.subheader("Raw Data")
    if df.empty:
        st.info("No rows match the selected filters.")
        return

    st.dataframe(
        df.sort_values("date", ascending=False),
        use_container_width=True,
    )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="US COVID-19 Hospitalization Dashboard", layout="wide")

    st.title("US COVID-19 Hospitalization Dashboard")
    st.markdown(
        "Monthly hospitalization rates from CDC COVID-NET Surveillance. "
        "Rates represent laboratory-confirmed COVID-19 hospitalizations "
        "per 100,000 residents in participating surveillance areas."
    )

    df_raw, last_updated = get_data()

    # Sidebar + filters work on the full preprocessed dataset
    date_range, selections = render_sidebar(df_raw, last_updated)
    filtered_full = apply_filters(df_raw, date_range, selections)

    if filtered_full.empty:
        st.warning("No data available for the selected filters and date range.")
        return

    # Semantics:
    # 1. Try canonical slice AFTER filters.
    # 2. If canonical exists, use it.
    # 3. Otherwise, fall back to the filtered data, still respecting user filters.
    canonical = canonical_slice(filtered_full)
    if not canonical.empty:
        base_for_charts = canonical
    else:
        base_for_charts = filtered_full

    # Better initial defaults for time series when no state selected
    base_for_ts = restrict_initial_states(base_for_charts, selections)
    ts_data = aggregate_for_time_series(base_for_ts)

    render_time_series(ts_data)
    render_choropleth(base_for_charts)
    render_data_table(filtered_full)


if __name__ == "__main__":
    main()
