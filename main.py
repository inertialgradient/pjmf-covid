import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk

# Data state
# ----------
if "data_refreshed" not in st.session_state:
    st.session_state["data_refreshed"] = False

# Page config
# -----------
st.set_page_config(page_title="US COVID-19 Hospitalization Dashboard", layout="wide")

st.title("US COVID-19 Hospitalization Dashboard")
st.markdown(
    "Monthly hospitalization rates from CDC COVID-NET Surveillance. "
    "Rates represent laboratory-confirmed COVID-19 hospitalizations per 100,000 residents "
    "in participating surveillance areas."
)


# Data loading
# ------------
DATA_URL = "https://data.cdc.gov/api/views/cf5u-bm9w/rows.csv"

@st.cache_data
def load_data(refreshed: bool = False):
    url = DATA_URL if refreshed else "./data.csv"
    df = pd.read_csv(url)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["_yearmonth"] = (
        df["_yearmonth"]
        .astype(float)  # handles "202202.0"
        .astype(int)  # yields 202202
        .astype(str)  # "202202"
        .str.zfill(6)  # ensure "YYYYMM"
    )
    df["date"] = pd.to_datetime(df["_yearmonth"] + "01", format="%Y%m%d")
    df = df.rename(columns={"monthlyrate": "hospitalization_rate"})
    return df

df = load_data(st.session_state["data_refreshed"])

# Sidebar
# -------
st.sidebar.write("### Data Controls")

# Disable refresh button after the first press
refresh_disabled = st.session_state["data_refreshed"]
if st.sidebar.button("Fetch updated data", disabled=refresh_disabled):
    st.session_state["data_refreshed"] = True
    st.cache_data.clear()
    st.rerun()

# Data filters
states_filter = st.sidebar.multiselect("Filter by state:", sorted(df["state"].unique()))
age_filter = st.sidebar.multiselect("Filter by age group:", sorted(df["agecategory_legend"].unique()))
sex_filter = st.sidebar.multiselect("Filter by sex:", sorted(df["sex_label"].unique()))
race_filter = st.sidebar.multiselect("Filter by race:", sorted(df["race_label"].unique()))

# Date range slider
min_date = df["date"].min().to_pydatetime()
max_date = df["date"].max().to_pydatetime()
date_range = st.sidebar.slider(
    "Date range:",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM",
)


# Filtering Pipeline
# ------------------
df_filtered = df.copy()

df_filtered = df_filtered[
    (df_filtered["date"] >= date_range[0]) & (df_filtered["date"] <= date_range[1])
]

if states_filter:
    df_filtered = df_filtered[df_filtered["state"].isin(states_filter)]
if age_filter:
    df_filtered = df_filtered[df_filtered["agecategory_legend"].isin(age_filter)]
if sex_filter:
    df_filtered = df_filtered[df_filtered["sex_label"].isin(sex_filter)]
if race_filter:
    df_filtered = df_filtered[df_filtered["race_label"].isin(race_filter)]


# Time-Series Plot 
# ----------------
df_summary = (
    df_filtered.groupby(["state", "date"])
    .agg({"hospitalization_rate": "mean"})
    .reset_index()
    .sort_values("date")
)

st.subheader("Trend Over Time")
fig_nat = px.line(
    df_summary,
    x="date",
    y="hospitalization_rate",
    color="state",
    labels={"hospitalization_rate": "Rate per 100,000"},
)
st.plotly_chart(fig_nat, width="stretch", key="national-trend")


# Raw Data Table
# ---------------
st.subheader("Raw Data")
df_table = df_filtered.sort_values("date", ascending=False)
st.dataframe(df_table, width="stretch", key="raw-data-table")
