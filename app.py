import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import CONFIG, STARTING_WEALTH, PLOT_CFG, C, CSS, load_data, prepare

st.set_page_config(page_title="Finanzanalyse", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATEN LADEN
# ─────────────────────────────────────────────
try:
    raw    = load_data()
    df_all = prepare(raw)
    data_ok = True
except Exception as e:
    data_ok    = False
    load_error = str(e)

today = pd.Timestamp.today().normalize()
c     = CONFIG

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

        min_date = df_all[c["col_date"]].min().date()
        max_date = df_all[c["col_date"]].max().date()

        st.markdown("**Zeitraum**")
        date_range = st.date_input(
            "Zeitraum",
            value=(min_date, today.date()),
            min_value=min_date,
            max_value=max_date,
            format="DD.MM.YYYY",
            label_visibility="collapsed",
        )

        all_cats = sorted(df_all[c["col_category"]].dropna().unique())
        sel_cats = st.multiselect("Kategorien", all_cats, default=all_cats)

        desc_search = st.text_input(
            "🔍 Beschreibung filtern",
            placeholder="z.B. REWE, Zugticket …",
            help="Suche über alle Beschreibungen (Groß-/Kleinschreibung egal)"
        )

        st.markdown("---")
        st.markdown("**Budgets** (€/Monat)")

        for cat in all_cats:
            if f"budget_{cat}" not in st.session_state:
                st.session_state[f"budget_{cat}"] = float(CONFIG["budgets"].get(cat, 0))

        with st.expander("✏️ Anpassen"):
            for cat in sorted(all_cats):
                st.number_input(cat, min_value=0.0, step=10.0, format="%.0f",
                                key=f"budget_{cat}")

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
df_all_today = df_all[df_all[c["col_date"]] <= today]

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_dt = pd.Timestamp(date_range[0])
    end_dt   = pd.Timestamp(date_range[1])
else:
    start_dt = pd.Timestamp(df_all[c["col_date"]].min())
    end_dt   = today

df = df_all[(df_all[c["col_date"]] >= start_dt) & (df_all[c["col_date"]] <= end_dt)].copy()

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
current_wealth = STARTING_WEALTH + df_all_today[c["col_amount"]].sum()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# Finanzanalyse")
date_min    = df[c["col_date"]].min().strftime("%d.%m.%Y") if len(df) else "–"
date_max    = df[c["col_date"]].max().strftime("%d.%m.%Y") if len(df) else "–"
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
# KPI-KARTEN (inkl. Vermögen)
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Übersicht</div>", unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)

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
with col5:
    wcls = "positive" if current_wealth >= STARTING_WEALTH else "negative"
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Aktuelles Vermögen</div>
        <div class='metric-value {wcls}'>{current_wealth:,.0f} €</div>
        <div class='metric-delta'>Start: {STARTING_WEALTH:,.2f} €</div>
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
fig.add_trace(go.Bar(x=mw["_monat_dt"], y=mw["Einnahme"], name="Einnahmen",
    marker_color=C["income"], opacity=0.85))
fig.add_trace(go.Bar(x=mw["_monat_dt"], y=mw["Ausgabe"], name="Ausgaben",
    marker_color=C["expense"], opacity=0.85))
fig.add_trace(go.Scatter(x=mw["_monat_dt"], y=mw["Ersparnis"], name="Ersparnis",
    mode="lines+markers", line=dict(color=C["savings"], width=2.5), marker=dict(size=5)))
fig.update_layout(**PLOT_CFG, barmode="group", height=330)
st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# AUSGABEN NACH KATEGORIE + SPARQUOTE (kompakt)
# ─────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

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
                    colorscale=[[0, "#2a2a35"], [1, C["expense"]]], showscale=False),
        text=cat_df["_betrag_abs"].apply(lambda x: f"{x:,.0f} €"),
        textposition="outside", textfont=dict(color="#9a9ab0", size=11),
    ))
    fig2.update_layout(**{**PLOT_CFG, "height": 320,
        "xaxis": dict(visible=False),
        "yaxis": dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)")})
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    st.markdown("<div class='section-header'>Monatliche Sparquote</div>", unsafe_allow_html=True)
    mw["Sparquote"] = (mw["Ersparnis"] / mw["Einnahme"].replace(0, float("nan")) * 100).fillna(0)
    avg_sq  = mw["Sparquote"].mean()
    sq_cls  = "positive" if avg_sq >= 0 else "negative"
    sq_sign = "+" if avg_sq >= 0 else ""
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Ø Sparquote im Zeitraum</div>
        <div class='metric-value {sq_cls}'>{sq_sign}{avg_sq:.1f} %</div>
        <div class='metric-delta'>
            Min {mw["Sparquote"].min():.1f} % &nbsp;·&nbsp; Max {mw["Sparquote"].max():.1f} %
        </div>
    </div>""", unsafe_allow_html=True)
    dot_colors = [C["savings"] if v >= 0 else C["expense"] for v in mw["Sparquote"]]
    fig3 = go.Figure(go.Scatter(
        x=mw["_monat_dt"], y=mw["Sparquote"],
        mode="lines+markers",
        line=dict(color=C["savings"], width=2),
        marker=dict(size=5, color=dot_colors),
        fill="tozeroy",
        fillcolor="rgba(123,138,255,0.06)",
    ))
    fig3.add_hline(y=0, line_color="#4a4a6a", line_width=1)
    fig3.update_layout(**{**PLOT_CFG,
        "height": 180,
        "margin": dict(l=0, r=0, t=8, b=0),
        "yaxis": dict(ticksuffix="%", gridcolor="#2a2a35", linecolor="#2a2a35")})
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────
# VERMÖGENSVERLAUF
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Vermögensverlauf</div>", unsafe_allow_html=True)

df_s = df.sort_values(c["col_date"]).copy()
df_s["_flow"]      = df_s[c["col_amount"]]
df_s["_vermoegen"] = STARTING_WEALTH + df_s["_flow"].cumsum()

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=df_s[c["col_date"]], y=df_s["_vermoegen"],
    mode="lines", fill="tozeroy",
    fillcolor="rgba(123,138,255,0.08)",
    line=dict(color=C["savings"], width=2.5),
    hovertemplate="%{x|%d.%m.%Y}: %{y:,.0f} €<extra></extra>",
))
fig4.add_hline(y=0, line_color="#4a4a6a", line_width=1, line_dash="dot")
fig4.update_layout(**{**PLOT_CFG, "height": 280,
    "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────
# BUDGET-VERGLEICH
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Budgetvergleich (Ø Monat vs. Ziel)</div>", unsafe_allow_html=True)

avg_by_cat  = (df_exp.groupby(c["col_category"])["_betrag_abs"].sum() / n_months).to_dict()
cats_with_budget = [cat for cat in sorted(avg_by_cat)
                    if st.session_state.get(f"budget_{cat}", 0) > 0]

if cats_with_budget:
    bcols = st.columns(2)
    for i, cat in enumerate(cats_with_budget):
        actual    = avg_by_cat[cat]
        budget    = st.session_state[f"budget_{cat}"]
        pct       = min(actual / budget * 100, 100)
        over      = actual > budget
        bar_color = C["expense"] if over else C["income"]
        status    = f"<span style='color:{bar_color}'>{'↑ über Budget' if over else '✓ ok'}</span>"
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
    st.info("Budgets in der Seitenleiste unter **Budgets → ✏️ Anpassen** eintragen, um diesen Bereich zu nutzen.")

# ─────────────────────────────────────────────
# TRANSAKTIONS-TABELLE
# ─────────────────────────────────────────────
with st.expander(f"📋 Alle Transaktionen ({len(df):,})", expanded=False):
    show_cols = [c["col_date"], c["col_description"], c["col_category"], c["col_amount"]]
    show_cols = [col for col in show_cols if col in df.columns]
    disp      = df[show_cols].sort_values(c["col_date"], ascending=False).copy()
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
