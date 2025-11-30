from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_URL = "https://data.cdc.gov/api/views/cf5u-bm9w/rows.csv"
LOCAL_DATA_PATH = "data.csv"
COLUMN_RENAME_MAP = {"monthlyrate": "hospitalization_rate"}


def initialize_session_state() -> None:
    """Ensure required session state keys exist."""
    st.session_state.setdefault("data_refreshed", False)


@st.cache_data
def load_data(refreshed: bool = False) -> pd.DataFrame:
    """Load and clean COVID hospitalization data."""
    source = DATA_URL if refreshed else LOCAL_DATA_PATH
    raw_df = pd.read_csv(source)
    return prepare_data(raw_df)


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, derive date fields, and standardize rates."""
    cleaned = df.copy()
    cleaned.columns = [c.strip().lower().replace(" ", "_") for c in cleaned.columns]
    cleaned = cleaned.rename(columns=COLUMN_RENAME_MAP)
    cleaned["_yearmonth"] = (
        pd.to_numeric(cleaned["_yearmonth"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .str.zfill(6)
    )
    cleaned["date"] = pd.to_datetime(
        cleaned["_yearmonth"] + "01", format="%Y%m%d", errors="coerce"
    )
    cleaned = cleaned.dropna(subset=["date"])
    return cleaned


def render_sidebar(df: pd.DataFrame) -> tuple[tuple[datetime, datetime], dict[str, list[str]]]:
    """Render sidebar controls and return the selected filters."""
    st.sidebar.header("Data Controls")

    refresh_disabled = st.session_state["data_refreshed"]
    if st.sidebar.button("Fetch updated data", disabled=refresh_disabled):
        st.session_state["data_refreshed"] = True
        st.cache_data.clear()
        st.rerun()

    min_date = df["date"].min().to_pydatetime()
    max_date = df["date"].max().to_pydatetime()
    date_range = st.sidebar.slider(
        "Date range:",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM",
    )

    filter_config = {
        "state": "Filter by state:",
        "agecategory_legend": "Filter by age group:",
        "sex_label": "Filter by sex:",
        "race_label": "Filter by race:",
    }

    selections: dict[str, list[str]] = {}
    for column, label in filter_config.items():
        selections[column] = st.sidebar.multiselect(label, sorted(df[column].unique()))

    return date_range, selections


def apply_filters(
    df: pd.DataFrame, date_range: tuple[datetime, datetime], selections: dict[str, list[str]]
) -> pd.DataFrame:
    """Apply date and categorical filters to the dataset."""
    filtered = df.loc[(df["date"] >= date_range[0]) & (df["date"] <= date_range[1])]
    for column, values in selections.items():
        if values:
            filtered = filtered[filtered[column].isin(values)]
    return filtered


def render_time_series(df: pd.DataFrame) -> None:
    """Plot hospitalization rates over time."""
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    summary = (
        df.groupby(["state", "date"], as_index=False)["hospitalization_rate"]
        .mean()
        .sort_values("date")
    )
    fig = px.line(
        summary,
        x="date",
        y="hospitalization_rate",
        color="state",
        labels={"hospitalization_rate": "Rate per 100,000"},
    )
    st.subheader("Trend Over Time")
    st.plotly_chart(fig, use_container_width=True, key="national-trend")


def render_data_table(df: pd.DataFrame) -> None:
    """Display the filtered dataset."""
    st.subheader("Raw Data")
    st.dataframe(
        df.sort_values("date", ascending=False),
        use_container_width=True,
        key="raw-data-table",
    )


def main() -> None:
    st.set_page_config(page_title="US COVID-19 Hospitalization Dashboard", layout="wide")
    initialize_session_state()

    st.title("US COVID-19 Hospitalization Dashboard")
    st.markdown(
        "Monthly hospitalization rates from CDC COVID-NET Surveillance. "
        "Rates represent laboratory-confirmed COVID-19 hospitalizations per 100,000 residents "
        "in participating surveillance areas."
    )

    df = load_data(st.session_state["data_refreshed"])
    date_range, selections = render_sidebar(df)
    filtered_df = apply_filters(df, date_range, selections)

    render_time_series(filtered_df)
    render_data_table(filtered_df)


if __name__ == "__main__":
    main()
