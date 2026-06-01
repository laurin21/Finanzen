import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
CONFIG = {
    "spreadsheet_id": "DEINE_SPREADSHEET_ID_HIER",  # aus der Google Sheets URL
    "worksheet_name": "Tabelle1",
    "col_date":        "Datum",
    "col_amount":      "Betrag",
    "col_category":    "Kategorie",
    "col_description": "Beschreibung",
    # Budget-Ziele pro Kategorie (€/Monat) — anpassen!
    "budgets": {
        "Lebensmittel": 300,
        "Miete":        800,
        "Transport":    100,
        "Freizeit":     150,
        "Gesundheit":   50,
        "Kleidung":     80,
        "Restaurants":  120,
        "Sonstiges":    100,
    }
}

# ─────────────────────────────────────────────
# PAGE CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Finanzanalyse", page_icon="📊", layout="wide")

st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

PLOT_CFG = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#9a9ab0", size=12),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(gridcolor="#2a2a35", linecolor="#2a2a35", tickfont=dict(color="#6b6b8a")),
    yaxis=dict(gridcolor="#2a2a35", linecolor="#2a2a35", tickfont=dict(color="#6b6b8a")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9a9ab0")),
)
C = {"income": "#5dd4a0", "expense": "#e05c6a", "savings": "#7b8aff"}

# ─────────────────────────────────────────────
# DATEN LADEN
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Lädt Daten via st.secrets (Streamlit Cloud) oder lokaler secrets.toml."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    spreadsheet_id = st.secrets.get("spreadsheet_id", CONFIG["spreadsheet_id"])
    worksheet_name = st.secrets.get("worksheet_name", CONFIG["worksheet_name"])

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    return pd.DataFrame(ws.get_all_records())


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    c = CONFIG
    df = df.copy()

    # Datum — Format 21.05.2026
    df[c["col_date"]] = pd.to_datetime(df[c["col_date"]], format="%d.%m.%Y", errors="coerce")
    df = df.dropna(subset=[c["col_date"]])

    # Betrag
    df[c["col_amount"]] = (
        df[c["col_amount"]].astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(r"[^\d.\-]", "", regex=True)
    )
    df[c["col_amount"]] = pd.to_numeric(df[c["col_amount"]], errors="coerce")
    df = df.dropna(subset=[c["col_amount"]])

    # Typ aus Vorzeichen
    df["_typ"]        = df[c["col_amount"]].apply(lambda x: "Einnahme" if x >= 0 else "Ausgabe")
    df["_betrag_abs"] = df[c["col_amount"]].abs()

    # Hilfsspalten
    df["_monat_dt"]  = df[c["col_date"]].dt.to_period("M").dt.to_timestamp()
    df["_monat_str"] = df[c["col_date"]].dt.strftime("%b %Y")
    df["_jahr"]      = df[c["col_date"]].dt.year

    return df.sort_values(c["col_date"]).reset_index(drop=True)


# ─────────────────────────────────────────────
# DATEN LADEN + FEHLERBEHANDLUNG
# ─────────────────────────────────────────────
try:
    raw = load_data()
    df_all = prepare(raw)
    data_ok = True
except Exception as e:
    data_ok = False
    load_error = str(e)

# ─────────────────────────────────────────────
# SIDEBAR — Filter
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Finanzanalyse")

    if not data_ok:
        st.error("Keine Verbindung zu Google Sheets.")
        st.markdown("Siehe README für Setup-Anleitung.")
    else:
        if st.button("🔄 Neu laden", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("**Filter**")

        years = sorted(df_all["_jahr"].unique(), reverse=True)
        sel_years = st.multiselect("Jahr", years, default=years)

        all_cats = sorted(df_all[CONFIG["col_category"]].dropna().unique())
        sel_cats = st.multiselect("Kategorien", all_cats, default=all_cats)

        # Beschreibungs-Suche
        desc_search = st.text_input(
            "🔍 Beschreibung filtern",
            placeholder="z.B. REWE, Zugticket …",
            help="Suche über alle Beschreibungen (Groß-/Kleinschreibung egal)"
        )

        st.markdown("---")
        st.markdown(
            "<div style='font-size:11px;color:#4a4a6a;font-family:DM Mono,monospace'>Daten gecacht · 5 min</div>",
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────
# SETUP-SEITE (wenn Secrets fehlen)
# ─────────────────────────────────────────────
if not data_ok:
    st.markdown("# Finanzanalyse")
    st.error(f"Google Sheets Verbindungsfehler: `{load_error}`")
    with st.expander("📋 Setup-Anleitung", expanded=True):
        st.markdown("""
### 1. Google Service Account erstellen
- [console.cloud.google.com](https://console.cloud.google.com) → Neues Projekt
- **Google Sheets API** aktivieren
- Anmeldedaten → Dienstkonto erstellen → JSON-Schlüssel herunterladen

### 2. Google Sheet freigeben
- Sheet öffnen → Teilen → `client_email` aus der JSON einfügen → Betrachter

### 3. Lokale Datei `.streamlit/secrets.toml` anlegen
```toml
spreadsheet_id = "DEINE_SPREADSHEET_ID"
worksheet_name = "Tabelle1"

[gcp_service_account]
type = "service_account"
project_id = "dein-projekt"
private_key_id = "abc123"
private_key = "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n"
client_email = "finance@projekt.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

### 4. Streamlit Community Cloud
- Auf [share.streamlit.io](https://share.streamlit.io) deployen
- App Settings → **Secrets** → Inhalt der `secrets.toml` einfügen

### 5. App starten (lokal)
```bash
pip install -r requirements.txt
streamlit run app.py
```
        """)
    st.stop()

# ─────────────────────────────────────────────
# DATEN FILTERN
# ─────────────────────────────────────────────
df = df_all.copy()
c = CONFIG

if sel_years:
    df = df[df["_jahr"].isin(sel_years)]
if sel_cats:
    df = df[df[c["col_category"]].isin(sel_cats)]
if desc_search.strip():
    df = df[df[c["col_description"]].str.contains(desc_search.strip(), case=False, na=False)]

df_inc = df[df["_typ"] == "Einnahme"]
df_exp = df[df["_typ"] == "Ausgabe"]

n_months       = max(df["_monat_dt"].nunique(), 1)
total_income   = df_inc["_betrag_abs"].sum()
total_expense  = df_exp["_betrag_abs"].sum()
total_savings  = total_income - total_expense
savings_rate   = (total_savings / total_income * 100) if total_income > 0 else 0

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# Finanzanalyse")
date_min = df[c["col_date"]].min().strftime("%d.%m.%Y") if len(df) else "–"
date_max = df[c["col_date"]].max().strftime("%d.%m.%Y") if len(df) else "–"
active_desc = f" · Filter: „{desc_search}“" if desc_search.strip() else ""
st.markdown(
    f"<div style='color:#6b6b8a;font-size:13px;font-family:DM Mono,monospace;margin-bottom:28px'>"
    f"{date_min} – {date_max} · {len(df):,} Transaktionen{active_desc}</div>",
    unsafe_allow_html=True
)

if len(df) == 0:
    st.warning("Keine Transaktionen für die gewählten Filter.")
    st.stop()

# ─────────────────────────────────────────────
# KPI-KARTEN
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Übersicht</div>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Einnahmen gesamt</div>
        <div class='metric-value positive'>+{total_income:,.0f} €</div>
        <div class='metric-delta'>⌀ {total_income/n_months:,.0f} €/Monat</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Ausgaben gesamt</div>
        <div class='metric-value negative'>−{total_expense:,.0f} €</div>
        <div class='metric-delta'>⌀ {total_expense/n_months:,.0f} €/Monat</div>
    </div>""", unsafe_allow_html=True)
with col3:
    cls  = "positive" if total_savings >= 0 else "negative"
    sign = "+" if total_savings >= 0 else "−"
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Erspartes gesamt</div>
        <div class='metric-value {cls}'>{sign}{abs(total_savings):,.0f} €</div>
        <div class='metric-delta'>Sparquote {savings_rate:.1f} %</div>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Zeitraum</div>
        <div class='metric-value neutral'>{n_months} Mo.</div>
        <div class='metric-delta'>{len(df):,} Transaktionen</div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# EINNAHMEN VS. AUSGABEN ÜBER ZEIT
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Einnahmen vs. Ausgaben</div>", unsafe_allow_html=True)

monthly = (
    df.groupby(["_monat_dt", "_typ"])["_betrag_abs"]
    .sum().reset_index()
)
mw = monthly.pivot_table(index="_monat_dt", columns="_typ", values="_betrag_abs", fill_value=0).reset_index()
for col in ["Einnahme", "Ausgabe"]:
    if col not in mw.columns:
        mw[col] = 0
mw["Ersparnis"] = mw["Einnahme"] - mw["Ausgabe"]

fig = go.Figure()
fig.add_trace(go.Bar(x=mw["_monat_dt"], y=mw["Einnahme"],  name="Einnahmen",
    marker_color=C["income"],  opacity=0.85))
fig.add_trace(go.Bar(x=mw["_monat_dt"], y=mw["Ausgabe"],   name="Ausgaben",
    marker_color=C["expense"], opacity=0.85))
fig.add_trace(go.Scatter(x=mw["_monat_dt"], y=mw["Ersparnis"], name="Ersparnis",
    mode="lines+markers", line=dict(color=C["savings"], width=2.5), marker=dict(size=5)))
fig.update_layout(**PLOT_CFG, barmode="group", height=330)
st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# AUSGABEN NACH KATEGORIE + SPARQUOTE
# ─────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.markdown("<div class='section-header'>Ausgaben nach Kategorie</div>", unsafe_allow_html=True)
    cat_df = (
        df_exp.groupby(c["col_category"])["_betrag_abs"]
        .sum().reset_index()
        .sort_values("_betrag_abs", ascending=True)
    )
    fig2 = go.Figure(go.Bar(
        x=cat_df["_betrag_abs"], y=cat_df[c["col_category"]], orientation="h",
        marker=dict(color=cat_df["_betrag_abs"],
                    colorscale=[[0,"#2a2a35"],[1,C["expense"]]], showscale=False),
        text=cat_df["_betrag_abs"].apply(lambda x: f"{x:,.0f} €"),
        textposition="outside", textfont=dict(color="#9a9ab0", size=11),
    ))
    fig2.update_layout(**PLOT_CFG, height=380,
        xaxis=dict(visible=False), yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    st.markdown("<div class='section-header'>Monatliche Sparquote</div>", unsafe_allow_html=True)
    mw["Sparquote"] = (mw["Ersparnis"] / mw["Einnahme"].replace(0, float("nan")) * 100).fillna(0)
    bar_colors = [C["savings"] if v >= 0 else C["expense"] for v in mw["Sparquote"]]
    fig3 = go.Figure(go.Bar(
        x=mw["_monat_dt"], y=mw["Sparquote"], marker_color=bar_colors, opacity=0.85,
        text=mw["Sparquote"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside", textfont=dict(color="#9a9ab0", size=10),
    ))
    fig3.add_hline(y=0, line_color="#4a4a6a", line_width=1)
    fig3.update_layout(**PLOT_CFG, height=380,
        yaxis=dict(ticksuffix="%", gridcolor="#2a2a35", linecolor="#2a2a35"))
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────
# SALDO-VERLAUF
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Saldo-Verlauf (kumuliert)</div>", unsafe_allow_html=True)

df_s = df.sort_values(c["col_date"]).copy()
df_s["_flow"]  = df_s[c["col_amount"]]          # Vorzeichen bereits korrekt
df_s["_saldo"] = df_s["_flow"].cumsum()

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=df_s[c["col_date"]], y=df_s["_saldo"],
    mode="lines", fill="tozeroy",
    fillcolor="rgba(123,138,255,0.08)",
    line=dict(color=C["savings"], width=2.5),
))
fig4.add_hline(y=0, line_color="#4a4a6a", line_width=1, line_dash="dot")
fig4.update_layout(**PLOT_CFG, height=260,
    yaxis=dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35"))
st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────
# BUDGET-VERGLEICH
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Budgetvergleich (Ø Monat vs. Ziel)</div>", unsafe_allow_html=True)

avg_by_cat = (df_exp.groupby(c["col_category"])["_betrag_abs"].sum() / n_months).to_dict()
budgets = CONFIG["budgets"]
budget_cats = [cat for cat in budgets if cat in avg_by_cat]

if budget_cats:
    bcols = st.columns(2)
    for i, cat in enumerate(budget_cats):
        actual = avg_by_cat.get(cat, 0)
        budget = budgets[cat]
        pct = min(actual / budget * 100 if budget > 0 else 0, 100)
        over = actual > budget
        bar_color = C["expense"] if over else C["income"]
        status = f"<span style='color:{bar_color}'>{'↑ über Budget' if over else '✓ ok'}</span>"
        with bcols[i % 2]:
            st.markdown(f"""<div class='budget-bar-container'>
                <div class='budget-bar-label'>
                    <span style='color:#c8c8e0;font-weight:500'>{cat}</span>
                    <span style='color:#6b6b8a;font-family:DM Mono,monospace;font-size:12px'>
                        {actual:,.0f} € / {budget:,.0f} € · {status}
                    </span>
                </div>
                <div class='budget-bar-bg'>
                    <div class='budget-bar-fill' style='width:{pct:.1f}%;background:{bar_color}'></div>
                </div>
            </div>""", unsafe_allow_html=True)
else:
    st.info("Budgets in `CONFIG['budgets']` in app.py eintragen, um diesen Bereich zu nutzen.")

# ─────────────────────────────────────────────
# TRANSAKTIONS-TABELLE
# ─────────────────────────────────────────────
with st.expander(f"📋 Alle Transaktionen ({len(df):,})", expanded=False):
    show_cols = [c["col_date"], c["col_description"], c["col_category"], c["col_amount"]]
    show_cols = [col for col in show_cols if col in df.columns]
    disp = df[show_cols].sort_values(c["col_date"], ascending=False).copy()
    disp[c["col_date"]] = disp[c["col_date"]].dt.strftime("%d.%m.%Y")

    st.dataframe(
        disp.reset_index(drop=True),
        use_container_width=True,
        height=420,
        column_config={
            c["col_amount"]: st.column_config.NumberColumn(format="%.2f €"),
            c["col_date"]:   st.column_config.TextColumn("Datum"),
        }
    )
