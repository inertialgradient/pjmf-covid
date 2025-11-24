# US COVID-19 Hospitalization Dashboard

Monthly hospitalization rates from [CDC COVID-NET Surveillance][cdc].

[cdc]: https://catalog.data.gov/dataset/monthly-rates-of-laboratory-confirmed-covid-19-hospitalizations-from-the-covid-net-surveil

## Deployed

https://jmromer-pjmf.streamlit.app

## Local

```
pip install uv
uv venv
uv run streamlit run main.py
```

## Features

- Time-series visualization, with per-state breakdown
- Tabular presentation of raw data
- Filtering by state, age, sex, race, and date
- Data refresh button (prototype limitation: data is only refreshed per-session)
