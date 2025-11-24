# US COVID-19 Hospitalization Dashboard

Monthly hospitalization rates from [CDC COVID-NET Surveillance][cdc].

[cdc]: https://catalog.data.gov/dataset/monthly-rates-of-laboratory-confirmed-covid-19-hospitalizations-from-the-covid-net-surveil

## Deployed

https://jmromer-pjmf.streamlit.app

[3fd1f85d-fdc3-4185-af21-3f1b518f59b5.webm](https://github.com/user-attachments/assets/22d79b36-1b0a-4fb5-800d-b4197c5a489b)


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
