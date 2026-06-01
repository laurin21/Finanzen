import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

STARTING_WEALTH = 5813.06

CONFIG = {
    "spreadsheet_id": "DEINE_SPREADSHEET_ID_HIER",
    "worksheet_name": "Tabelle1",
    "col_date":        "Datum",
    "col_amount":      "Betrag",
    "col_category":    "Kategorie",
    "col_description": "Beschreibung",
    "budgets": {
        "Lebensmittel": 300,
        "Miete":        800,
        "Transport":    100,
        "Freizeit":     150,
        "Gesundheit":   50,
        "Kleidung":     80,
        "Restaurants":  120,
        "Sonstiges":    100,
    },
}

PLOT_CFG = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#9a9ab0", size=12),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(gridcolor="#2a2a35", linecolor="#2a2a35", tickfont=dict(color="#6b6b8a")),
    yaxis=dict(gridcolor="#2a2a35", linecolor="#2a2a35", tickfont=dict(color="#6b6b8a")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9a9ab0")),
)

C = {"income": "#5dd4a0", "expense": "#e05c6a", "savings": "#7b8aff"}

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
* { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0f0f13; color: #e8e6e1; }
[data-testid="stSidebar"] { background: #16161d !important; border-right: 1px solid #2a2a35; }
.metric-card { background: #1a1a24; border: 1px solid #2a2a35; border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; }
.metric-label { font-size: 11px; font-weight: 500; letter-spacing: 0.12em; text-transform: uppercase; color: #6b6b8a; margin-bottom: 6px; font-family: 'DM Mono', monospace; }
.metric-value { font-size: 26px; font-weight: 300; color: #e8e6e1; font-family: 'DM Mono', monospace; }
.metric-value.positive { color: #5dd4a0; }
.metric-value.negative { color: #e05c6a; }
.metric-value.neutral  { color: #7b8aff; }
.metric-delta { font-size: 12px; color: #6b6b8a; margin-top: 4px; font-family: 'DM Mono', monospace; }
.section-header { font-size: 11px; font-weight: 500; letter-spacing: 0.15em; text-transform: uppercase; color: #4a4a6a; font-family: 'DM Mono', monospace; margin: 28px 0 14px; padding-bottom: 8px; border-bottom: 1px solid #2a2a35; }
.budget-bar-container { background: #1a1a24; border: 1px solid #2a2a35; border-radius: 10px; padding: 14px 18px; margin-bottom: 8px; }
.budget-bar-label { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
.budget-bar-bg { background: #2a2a35; border-radius: 4px; height: 6px; overflow: hidden; }
.budget-bar-fill { height: 100%; border-radius: 4px; }
div[data-testid="stDataFrame"] { border: 1px solid #2a2a35; border-radius: 10px; }
</style>"""


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    creds_dict = dict(st.secrets["gcp_service_account"])
    spreadsheet_id = st.secrets.get("spreadsheet_id", CONFIG["spreadsheet_id"])
    worksheet_name = st.secrets.get("worksheet_name", CONFIG["worksheet_name"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    rows = ws.get_all_values()
    if not rows:
        return pd.DataFrame()
    headers = rows[0]
    df = pd.DataFrame(rows[1:], columns=headers)
    return df.loc[:, df.columns.str.strip() != ""]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    c = CONFIG
    df = df.copy()
    df[c["col_date"]] = pd.to_datetime(df[c["col_date"]], format="%d.%m.%Y", errors="coerce")
    df = df.dropna(subset=[c["col_date"]])
    df[c["col_amount"]] = (
        df[c["col_amount"]].astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(r"[^\d.\-]", "", regex=True)
    )
    df[c["col_amount"]] = pd.to_numeric(df[c["col_amount"]], errors="coerce")
    df = df.dropna(subset=[c["col_amount"]])
    df["_typ"]        = df[c["col_amount"]].apply(lambda x: "Einnahme" if x >= 0 else "Ausgabe")
    df["_betrag_abs"] = df[c["col_amount"]].abs()
    df["_monat_dt"]   = df[c["col_date"]].dt.to_period("M").dt.to_timestamp()
    df["_monat_str"]  = df[c["col_date"]].dt.strftime("%b %Y")
    df["_jahr"]       = df[c["col_date"]].dt.year
    return df.sort_values(c["col_date"]).reset_index(drop=True)


def append_transaction(datum: str, betrag: float, kategorie: str, beschreibung: str) -> None:
    """Hängt eine neue Transaktion ans Google Sheet an."""
    creds_dict     = dict(st.secrets["gcp_service_account"])
    spreadsheet_id = st.secrets.get("spreadsheet_id", CONFIG["spreadsheet_id"])
    worksheet_name = st.secrets.get("worksheet_name", CONFIG["worksheet_name"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc     = gspread.authorize(creds)
    ws     = gc.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    headers = ws.row_values(1)
    row_map = {
        CONFIG["col_date"]:        datum,
        CONFIG["col_amount"]:      str(betrag).replace(".", ","),
        CONFIG["col_category"]:    kategorie,
        CONFIG["col_description"]: beschreibung,
    }
    ws.append_row(
        [row_map.get(h.strip(), "") for h in headers],
        value_input_option="RAW",
    )
