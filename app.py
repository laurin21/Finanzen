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
    raw     = load_data()
    df_all  = prepare(raw)
    data_ok = True
except Exception as e:
    data_ok    = False
    load_error = str(e)

today = pd.Timestamp.today().normalize()
c     = CONFIG

# ─────────────────────────────────────────────
# SIDEBAR — minimal
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
        st.markdown(
            "<div style='font-size:11px;color:#4a4a6a;font-family:DM Mono,monospace'>"
            "Daten gecacht · 5 min</div>",
            unsafe_allow_html=True,
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
# HEADER
# ─────────────────────────────────────────────
st.markdown("# Finanzanalyse")

# ─────────────────────────────────────────────
# FILTER-EXPANDER
# ─────────────────────────────────────────────
all_cats = sorted(df_all[c["col_category"]].dropna().unique())
min_date = df_all[c["col_date"]].min().date()
max_date = df_all[c["col_date"]].max().date()

for cat in all_cats:
    if f"budget_{cat}" not in st.session_state:
        st.session_state[f"budget_{cat}"] = float(CONFIG["budgets"].get(cat, 0))

with st.expander("🔍 Filter", expanded=False):
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        st.markdown("**Zeitraum**")
        date_range = st.date_input(
            "Zeitraum",
            value=(min_date, today.date()),
            min_value=min_date,
            max_value=max_date,
            format="DD.MM.YYYY",
            label_visibility="collapsed",
        )
    with fc2:
        sel_cats = st.multiselect("Kategorien", all_cats, default=all_cats)
    with fc3:
        desc_search = st.text_input(
            "🔍 Beschreibung filtern",
            placeholder="z.B. REWE, Zugticket …",
            help="Suche über alle Beschreibungen (Groß-/Kleinschreibung egal)",
        )

# ─────────────────────────────────────────────
# DATEN FILTERN
# ─────────────────────────────────────────────
df_all_today = df_all[df_all[c["col_date"]] <= today]

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_dt = pd.Timestamp(date_range[0])
    end_dt   = pd.Timestamp(date_range[1])
else:
    start_dt = pd.Timestamp(min_date)
    end_dt   = today

df = df_all[(df_all[c["col_date"]] >= start_dt) & (df_all[c["col_date"]] <= end_dt)].copy()
if sel_cats:
    df = df[df[c["col_category"]].isin(sel_cats)]
if desc_search.strip():
    df = df[df[c["col_description"]].str.contains(desc_search.strip(), case=False, na=False)]

df_inc = df[df["_typ"] == "Einnahme"]
df_exp = df[df["_typ"] == "Ausgabe"]

n_months      = max(df["_monat_dt"].nunique(), 1)
total_income  = df_inc["_betrag_abs"].sum()
total_expense = df_exp["_betrag_abs"].sum()
total_savings = total_income - total_expense
savings_rate  = (total_savings / total_income * 100) if total_income > 0 else 0
current_wealth = STARTING_WEALTH + df_all_today[c["col_amount"]].sum()

active_desc = f' · Suche: "{desc_search.strip()}"' if desc_search.strip() else ""
st.markdown(
    f"<div style='color:#6b6b8a;font-size:13px;font-family:DM Mono,monospace;margin-bottom:20px'>"
    f"{start_dt.strftime('%d.%m.%Y')} – {end_dt.strftime('%d.%m.%Y')}"
    f" · {len(df):,} Transaktionen{active_desc}</div>",
    unsafe_allow_html=True,
)

if len(df) == 0:
    st.warning("Keine Transaktionen für die gewählten Filter.")
    st.stop()

# ─────────────────────────────────────────────
# VORBERECHNUNGEN
# ─────────────────────────────────────────────
def build_mw(df_src: pd.DataFrame) -> pd.DataFrame:
    monthly = df_src.groupby(["_monat_dt", "_typ"])["_betrag_abs"].sum().reset_index()
    mw = monthly.pivot_table(
        index="_monat_dt", columns="_typ", values="_betrag_abs", fill_value=0
    ).reset_index()
    for col_name in ["Einnahme", "Ausgabe"]:
        if col_name not in mw.columns:
            mw[col_name] = 0
    mw["Ersparnis"] = mw["Einnahme"] - mw["Ausgabe"]
    mw["Sparquote"] = (
        mw["Ersparnis"] / mw["Einnahme"].replace(0, float("nan")) * 100
    ).fillna(0)
    return mw


mw_filtered = build_mw(df)
mw_all_t    = build_mw(df_all_today)

df_inc_total   = df_all_today[df_all_today["_typ"] == "Einnahme"]
df_exp_total   = df_all_today[df_all_today["_typ"] == "Ausgabe"]
n_months_total = max(df_all_today["_monat_dt"].nunique(), 1)
inc_total      = df_inc_total["_betrag_abs"].sum()
exp_total      = df_exp_total["_betrag_abs"].sum()
sav_total      = inc_total - exp_total
rate_total     = (sav_total / inc_total * 100) if inc_total > 0 else 0


def group_by_period(df_src: pd.DataFrame, granularity: str) -> pd.DataFrame:
    if granularity == "Wöchentlich":
        df2 = df_src.copy()
        df2["_period"] = (
            df2[c["col_date"]]
            - pd.to_timedelta(df2[c["col_date"]].dt.dayofweek, unit="D")
        )
    elif granularity == "Jährlich":
        df2 = df_src.copy()
        df2["_period"] = df2[c["col_date"]].dt.to_period("Y").dt.to_timestamp()
    else:
        df2 = df_src.copy()
        df2["_period"] = df2["_monat_dt"]
    grp = df2.groupby(["_period", "_typ"])["_betrag_abs"].sum().reset_index()
    gp  = grp.pivot_table(
        index="_period", columns="_typ", values="_betrag_abs", fill_value=0
    ).reset_index()
    for col_name in ["Einnahme", "Ausgabe"]:
        if col_name not in gp.columns:
            gp[col_name] = 0
    gp["Ersparnis"] = gp["Einnahme"] - gp["Ausgabe"]
    return gp


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["\U0001f4ca Analyse", "\U0001f4c8 Sparquoten"])

with tab1:

    # ── Gesamt-Toggle (steuert alle Objekte in diesem Tab) ──
    hdr_c, tog_c = st.columns([4, 1])
    with hdr_c:
        st.markdown("<div class='section-header'>Übersicht</div>", unsafe_allow_html=True)
    with tog_c:
        show_total = st.toggle(
            "Gesamt", value=False,
            help="Alle Aufzeichnungen von Start bis heute — ignoriert Filter",
        )

    df_d     = df_all_today if show_total else df
    df_inc_d = df_d[df_d["_typ"] == "Einnahme"]
    df_exp_d = df_d[df_d["_typ"] == "Ausgabe"]
    n_mo_d   = max(df_d["_monat_dt"].nunique(), 1)
    mw_d     = mw_all_t if show_total else mw_filtered

    if show_total:
        kpi_inc, kpi_exp, kpi_sav = inc_total, exp_total, sav_total
        kpi_rate, kpi_n           = rate_total, n_months_total
        kpi_ctx = f"Start – {today.strftime('%d.%m.%Y')}"
    else:
        kpi_inc, kpi_exp, kpi_sav = total_income, total_expense, total_savings
        kpi_rate, kpi_n           = savings_rate, n_months
        kpi_ctx = f"{start_dt.strftime('%d.%m.%Y')} – {end_dt.strftime('%d.%m.%Y')}"

    # ── KPI-Karten ──
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Einnahmen</div>
            <div class='metric-value positive'>+{kpi_inc:,.0f} €</div>
            <div class='metric-delta'>ø {kpi_inc/kpi_n:,.0f} €/Monat</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Ausgaben</div>
            <div class='metric-value negative'>−{kpi_exp:,.0f} €</div>
            <div class='metric-delta'>ø {kpi_exp/kpi_n:,.0f} €/Monat</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        cls  = "positive" if kpi_sav >= 0 else "negative"
        sign = "+" if kpi_sav >= 0 else "−"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Erspartes</div>
            <div class='metric-value {cls}'>{sign}{abs(kpi_sav):,.0f} €</div>
            <div class='metric-delta'>Sparquote {kpi_rate:.1f} %</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Zeitraum</div>
            <div class='metric-value neutral'>{kpi_n} Mo.</div>
            <div class='metric-delta'>{kpi_ctx}</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        wcls = "positive" if current_wealth >= STARTING_WEALTH else "negative"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Aktuelles Vermögen</div>
            <div class='metric-value {wcls}'>{current_wealth:,.0f} €</div>
            <div class='metric-delta'>Start: {STARTING_WEALTH:,.2f} €</div>
        </div>""", unsafe_allow_html=True)

    # ── Einnahmen vs. Ausgaben ──
    ev_hdr_c, ev_gran_c = st.columns([3, 1])
    with ev_hdr_c:
        st.markdown(
            "<div class='section-header'>Einnahmen vs. Ausgaben</div>",
            unsafe_allow_html=True,
        )
    with ev_gran_c:
        granularity = st.radio(
            "Granularität",
            ["Wöchentlich", "Monatlich", "Jährlich"],
            index=1,
            horizontal=True,
            label_visibility="collapsed",
            key="gran_ev",
        )

    gp = group_by_period(df_d, granularity)
    fig_ev = go.Figure()
    fig_ev.add_trace(go.Bar(
        x=gp["_period"], y=gp["Einnahme"], name="Einnahmen",
        marker_color=C["income"], opacity=0.85,
    ))
    fig_ev.add_trace(go.Bar(
        x=gp["_period"], y=gp["Ausgabe"], name="Ausgaben",
        marker_color=C["expense"], opacity=0.85,
    ))
    fig_ev.add_trace(go.Scatter(
        x=gp["_period"], y=gp["Ersparnis"], name="Ersparnis",
        mode="lines+markers",
        line=dict(color=C["savings"], width=2.5),
        marker=dict(size=5),
    ))
    fig_ev.update_layout(**PLOT_CFG, barmode="group", height=330)
    st.plotly_chart(fig_ev, use_container_width=True)

    # ── Ausgaben nach Kategorie ──
    st.markdown(
        "<div class='section-header'>Ausgaben nach Kategorie</div>",
        unsafe_allow_html=True,
    )
    cat_df = (
        df_exp_d.groupby(c["col_category"])["_betrag_abs"]
        .sum()
        .reset_index()
        .sort_values("_betrag_abs", ascending=True)
    )
    if len(cat_df):
        fig2 = go.Figure(go.Bar(
            x=cat_df["_betrag_abs"], y=cat_df[c["col_category"]],
            orientation="h",
            marker=dict(
                color=cat_df["_betrag_abs"],
                colorscale=[[0, "#2a2a35"], [1, C["expense"]]],
                showscale=False,
            ),
            text=cat_df["_betrag_abs"].apply(lambda x: f"{x:,.0f} €"),
            textposition="outside",
            textfont=dict(color="#9a9ab0", size=11),
        ))
        fig2.update_layout(**{**PLOT_CFG, "height": max(200, len(cat_df) * 36),
            "xaxis": dict(visible=False),
            "yaxis": dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)")})
        st.plotly_chart(fig2, use_container_width=True)

    # ── Vermögensverlauf ──
    st.markdown(
        "<div class='section-header'>Vermögensverlauf</div>",
        unsafe_allow_html=True,
    )
    if show_total:
        df_s = df_all_today.sort_values(c["col_date"]).copy()
        df_s["_vermoegen"] = STARTING_WEALTH + df_s[c["col_amount"]].cumsum()
    else:
        prior_sum = df_all[df_all[c["col_date"]] < start_dt][c["col_amount"]].sum()
        df_s = df.sort_values(c["col_date"]).copy()
        df_s["_vermoegen"] = (STARTING_WEALTH + prior_sum) + df_s[c["col_amount"]].cumsum()

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

# ── Tab 2: Sparquoten ──────────────────────────────────────────────────
with tab2:
    avg_sq  = mw_filtered["Sparquote"].mean()
    sq_cls  = "positive" if avg_sq >= 0 else "negative"
    sq_sign = "+" if avg_sq >= 0 else ""
    last_sq = mw_filtered["Sparquote"].iloc[-1] if len(mw_filtered) else 0
    lsq_cls = "positive" if last_sq >= 0 else "negative"
    lsq_lbl = mw_filtered["_monat_dt"].iloc[-1].strftime("%b %Y") if len(mw_filtered) else ""
    pos_mo  = int((mw_filtered["Sparquote"] > 0).sum())

    st.markdown(
        "<div class='section-header'>Sparquoten-Übersicht</div>",
        unsafe_allow_html=True,
    )
    sq1, sq2, sq3 = st.columns(3)
    with sq1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>ø Sparquote im Zeitraum</div>
            <div class='metric-value {sq_cls}'>{sq_sign}{avg_sq:.1f} %</div>
            <div class='metric-delta'>
                Min {mw_filtered["Sparquote"].min():.1f} % · Max {mw_filtered["Sparquote"].max():.1f} %
            </div>
        </div>""", unsafe_allow_html=True)
    with sq2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Letzter Monat ({lsq_lbl})</div>
            <div class='metric-value {lsq_cls}'>{last_sq:+.1f} %</div>
            <div class='metric-delta'>Sparquote</div>
        </div>""", unsafe_allow_html=True)
    with sq3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Monate mit posit. Sparquote</div>
            <div class='metric-value neutral'>{pos_mo} / {len(mw_filtered)}</div>
            <div class='metric-delta'>im gewählten Zeitraum</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(
        "<div class='section-header'>Sparquoten-Verlauf</div>",
        unsafe_allow_html=True,
    )
    dot_colors = [C["savings"] if v >= 0 else C["expense"] for v in mw_filtered["Sparquote"]]
    fig3 = go.Figure(go.Scatter(
        x=mw_filtered["_monat_dt"], y=mw_filtered["Sparquote"],
        mode="lines+markers",
        line=dict(color=C["savings"], width=2),
        marker=dict(size=6, color=dot_colors),
        fill="tozeroy",
        fillcolor="rgba(123,138,255,0.06)",
        hovertemplate="%{x|%b %Y}: %{y:.1f} %<extra></extra>",
    ))
    fig3.add_hline(y=0, line_color="#4a4a6a", line_width=1)
    fig3.update_layout(**{**PLOT_CFG, "height": 300,
        "yaxis": dict(ticksuffix="%", gridcolor="#2a2a35", linecolor="#2a2a35")})
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown(
        "<div class='section-header'>Monatliches Erspartes</div>",
        unsafe_allow_html=True,
    )
    bar_colors = [C["savings"] if v >= 0 else C["expense"] for v in mw_filtered["Ersparnis"]]
    fig5 = go.Figure(go.Bar(
        x=mw_filtered["_monat_dt"], y=mw_filtered["Ersparnis"],
        marker_color=bar_colors, opacity=0.85,
        text=mw_filtered["Ersparnis"].apply(lambda x: f"{x:+,.0f} €"),
        textposition="outside",
        textfont=dict(color="#9a9ab0", size=10),
    ))
    fig5.add_hline(y=0, line_color="#4a4a6a", line_width=1)
    fig5.update_layout(**{**PLOT_CFG, "height": 280,
        "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
    st.plotly_chart(fig5, use_container_width=True)

# ─────────────────────────────────────────────
# BUDGET-EXPANDER (zwischen Tabs und Tabelle)
# ─────────────────────────────────────────────
avg_by_cat       = (df_exp.groupby(c["col_category"])["_betrag_abs"].sum() / n_months).to_dict()
cats_with_budget = [cat for cat in sorted(avg_by_cat) if st.session_state.get(f"budget_{cat}", 0) > 0]

with st.expander("💰 Budgetvergleich (ø Monat vs. Ziel)", expanded=False):
    b_bars, b_edit = st.columns([3, 1])
    with b_bars:
        if cats_with_budget:
            bcols = st.columns(2)
            for i, cat in enumerate(cats_with_budget):
                actual      = avg_by_cat[cat]
                budget      = st.session_state[f"budget_{cat}"]
                pct         = min(actual / budget * 100, 100)
                over        = actual > budget
                bar_color   = C["expense"] if over else C["income"]
                status_text = "↑ über Budget" if over else "✓ ok"
                status      = f"<span style='color:{bar_color}'>{status_text}</span>"
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
            st.info("Rechts Budgets eintragen, um den Vergleich zu sehen.")
    with b_edit:
        st.markdown(
            "<div style='font-size:11px;font-weight:500;letter-spacing:0.1em;"
            "text-transform:uppercase;color:#6b6b8a;font-family:DM Mono,monospace;"
            "margin-bottom:8px'>Budgets (€/Monat)</div>",
            unsafe_allow_html=True,
        )
        for cat in sorted(all_cats):
            st.number_input(
                cat, min_value=0.0, step=10.0, format="%.0f",
                key=f"budget_{cat}",
            )

# ─────────────────────────────────────────────
# TRANSAKTIONS-TABELLE (außerhalb der Tabs)
# ─────────────────────────────────────────────
with st.expander(f"\U0001f4cb Alle Transaktionen ({len(df):,})", expanded=False):
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
        },
    )
