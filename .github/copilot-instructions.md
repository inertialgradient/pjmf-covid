<!-- .github/copilot-instructions.md for pjmf-covid -->
# Copilot instructions — pjmf-covid

This file gives AI coding agents the precise, actionable knowledge they need to be productive in this repository.

Summary
- Purpose: single-file Streamlit dashboard that visualizes CDC COVID-NET monthly hospitalization rates (`main.py`).
- Runtime: Python 3.12 (see `pyproject.toml` / `mise.toml`).
- Data: default uses local `data.csv`; a remote CDC CSV is available at runtime via `DATA_URL` in `main.py`.

Key files
- `main.py`: the entire app. Contains data-loading, processing, Streamlit UI (sidebar filters, plots, table). Primary place to modify behavior.
- `data.csv`: local snapshot used by default by `load_data()`.
- `pyproject.toml`: dependencies and supported Python version. Use it as the authoritative dependency list.
- `README.md`: contains deploy and local run instructions — follow those commands when unsure.

Architecture & data flow (short)
- On start, `main.py` calls `load_data(refreshed: bool)`.
  - If `st.session_state["data_refreshed"]` is False, `load_data` reads `./data.csv`.
  - If refreshed, it reads `DATA_URL` (CDC rows CSV).
  - The loader normalizes column names to lowercase/underscored and coerces `_yearmonth` → `date`.
  - `monthlyrate` is renamed to `hospitalization_rate` and used for plotting/aggregation.
- Downstream: filters (state, age, sex, race, date range) are applied on the normalized frame, then grouped for time-series plotting.

Project-specific conventions and patterns
- Column canonicalization: `df.columns = [c.strip().lower().replace(" ", "_") ...]`. Always expect lower_snake_case names in subsequent code.
- Date handling: `_yearmonth` is numeric-like (e.g. `202202.0`) and is transformed into a `date` column using `pd.to_datetime(_yearmonth + '01', format='%Y%m%d')`.
- Caching: `@st.cache_data` is used on `load_data()` and `st.cache_data.clear()` is called after fetching updated data. If modifying cached functions, consider clearing cache or bumping keys.
- UI flow: toggling `st.session_state['data_refreshed']` + `st.rerun()` is the pattern used to fetch remote data once per session.

Developer workflows (how to run & debug locally)
Use the commands from `README.md` for local runs (these are the documented steps that were used by the author):

```bash
pip install uv
uv venv
uv run streamlit run main.py
```

Notes:
- The project lists Python >=3.12 in `pyproject.toml` and `mise.toml`. Use a 3.12.x interpreter for local work.
- If you prefer a standard virtualenv workflow: `python -m venv .venv && . .venv/bin/activate && pip install -r <deps>` (there is no `requirements.txt`; reference `pyproject.toml`).

Integration points & external dependencies
- Remote data: `DATA_URL` in `main.py` points to a CDC data portal CSV. Changes in that CSV (column names/types) will require corresponding loader updates.
- Deployment: app is deployed at `https://jmromer-pjmf.streamlit.app` (see `README.md`). Deployment updates typically involve modifying `main.py` and redeploying to Streamlit cloud.

When editing the code, focus on these hotspots
- `load_data()` in `main.py`: any change to data schema or new fields should update the canonicalization logic and downstream code that expects `hospitalization_rate`, `date`, and identity of categorical columns (`state`, `agecategory_legend`, `sex_label`, `race_label`).
- Sidebar filters and `df_filtered` pipeline: keep filters applied by `.isin(...)` and the date-range logic intact if reusing the UI.
- Plot generation: `df_summary` is grouped by `state` and `date` and then passed to `plotly.express.line`. If changing aggregation, update labels and keys used by `st.plotly_chart`.

Examples (copyable) — common edits
- Add a new derived column after load:
```py
df['rate_per_million'] = df['hospitalization_rate'] * 10_000
```
- Force using remote data during development:
```py
df = load_data(refreshed=True)
```

What not to assume
- There are no tests or CI configured; do not assume test suites exist.
- The app is single-file. Global refactors should preserve Streamlit state usage and caching semantics.

If something is unclear or you need more rules
- Tell me which area (data loader, caching, deploy) you'd like more examples for and I will expand this file.

-- End of instructions
