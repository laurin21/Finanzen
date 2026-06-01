import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import (CONFIG, STARTING_WEALTH, PLOT_CFG, C, CSS,
                    load_data, prepare, append_transaction,
                    update_transaction, delete_transaction)

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

today               = pd.Timestamp.today().normalize()
c                   = CONFIG
current_month_start = today.to_period("M").to_timestamp()

# Vorberechnungen für Sidebar & Widgets
if data_ok:
    all_cats        = sorted(df_all[c["col_category"]].dropna().unique())
    all_cats_by_freq = list(df_all[c["col_category"]].dropna().value_counts().index)
    min_date        = df_all[c["col_date"]].min().date()
    max_date        = df_all[c["col_date"]].max().date()
    for cat in all_cats:
        if f"budget_{cat}" not in st.session_state:
            st.session_state[f"budget_{cat}"] = float(CONFIG["budgets"].get(cat, 0))
else:
    all_cats = all_cats_by_freq = []
    min_date = max_date = today.date()

# ─────────────────────────────────────────────
# SIDEBAR — Kategorien & Beschreibung
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
        sel_cats = st.multiselect("Kategorien", all_cats, default=all_cats)
        desc_search = st.text_input(
            "🔍 Beschreibung filtern",
            placeholder="z.B. REWE, Zugticket …",
            help="Suche über alle Beschreibungen (Groß-/Kleinschreibung egal)",
        )
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
```

### 4. Streamlit Community Cloud
- Auf [share.streamlit.io](https://share.streamlit.io) deployen
- App Settings → **Secrets** → Inhalt der `secrets.toml` einfügen
        """)
    st.stop()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# Finanzanalyse")

# ─────────────────────────────────────────────
# ZEITRAUM (inline)
# ─────────────────────────────────────────────
st.markdown(
    "<div style='font-size:11px;font-weight:500;letter-spacing:0.12em;text-transform:uppercase;"
    "color:#6b6b8a;font-family:DM Mono,monospace;margin-bottom:6px'>Analysezeitraum</div>",
    unsafe_allow_html=True,
)
_PRESETS = [
    "Ganzer Zeitraum",
    "Aktuelles Jahr",
    "Letztes Jahr",
    "Letzte 12 Monate",
    "Letzte 6 Monate",
    "Letzte 3 Monate",
    "Benutzerdefiniert",
]
zeitraum_preset = st.selectbox(
    "Zeitraum", _PRESETS, index=0, label_visibility="collapsed",
)
date_range = None
if zeitraum_preset == "Benutzerdefiniert":
    date_range = st.date_input(
        "Benutzerdefinierter Zeitraum",
        value=(min_date, today.date()),
        min_value=min_date,
        max_value=max_date,
        format="DD.MM.YYYY",
        label_visibility="collapsed",
    )

st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATEN FILTERN
# ─────────────────────────────────────────────
df_all_today = df_all[df_all[c["col_date"]] <= today]

if zeitraum_preset == "Ganzer Zeitraum":
    start_dt, end_dt = pd.Timestamp(min_date), today
elif zeitraum_preset == "Aktuelles Jahr":
    start_dt, end_dt = pd.Timestamp(today.year, 1, 1), today
elif zeitraum_preset == "Letztes Jahr":
    start_dt = pd.Timestamp(today.year - 1, 1, 1)
    end_dt   = pd.Timestamp(today.year - 1, 12, 31)
elif zeitraum_preset == "Letzte 12 Monate":
    start_dt, end_dt = today - pd.DateOffset(months=12), today
elif zeitraum_preset == "Letzte 6 Monate":
    start_dt, end_dt = today - pd.DateOffset(months=6), today
elif zeitraum_preset == "Letzte 3 Monate":
    start_dt, end_dt = today - pd.DateOffset(months=3), today
else:  # Benutzerdefiniert
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_dt = pd.Timestamp(date_range[0])
        end_dt   = pd.Timestamp(date_range[1])
    else:
        start_dt, end_dt = pd.Timestamp(min_date), today

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


def group_by_period(df_src: pd.DataFrame, granularity: str) -> pd.DataFrame:
    df2 = df_src.copy()
    if granularity == "Wöchentlich":
        df2["_period"] = (
            df2[c["col_date"]]
            - pd.to_timedelta(df2[c["col_date"]].dt.dayofweek, unit="D")
        )
    elif granularity == "Jährlich":
        df2["_period"] = df2[c["col_date"]].dt.to_period("Y").dt.to_timestamp()
    else:
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


mw_filtered  = build_mw(df)
mw_comp_filt = mw_filtered[mw_filtered["_monat_dt"] < current_month_start].copy()


def _style_map(styler, func, subset):
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    return styler.applymap(func, subset=subset)  # pandas < 2.1


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab_a, tab_m, tab_k, tab_s = st.tabs([
    "\U0001f4ca Analyse",
    "\U0001f4c5 Monatsübersicht",
    "\U0001f5c2️ Kategorien",
    "\U0001f4c8 Sparquoten",
])

# ══════════════════════════════════════════════
with tab_a:

    st.markdown("<div class='section-header'>Übersicht</div>", unsafe_allow_html=True)

    kpi_ctx = f"{start_dt.strftime('%d.%m.%Y')} – {end_dt.strftime('%d.%m.%Y')}"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        wcls = "positive" if current_wealth >= STARTING_WEALTH else "negative"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Aktuelles Vermögen</div>
            <div class='metric-value {wcls}'>{current_wealth:,.0f} €</div>
            <div class='metric-delta'>Start: {STARTING_WEALTH:,.2f} €</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        cls  = "positive" if total_savings >= 0 else "negative"
        sign = "+" if total_savings >= 0 else "−"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Gewinn</div>
            <div class='metric-value {cls}'>{sign}{abs(total_savings):,.0f} €</div>
            <div class='metric-delta'>ø {total_savings/n_months:,.0f} €/Monat</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Zeitraum</div>
            <div class='metric-value neutral'>{n_months} Mo.</div>
            <div class='metric-delta'>{kpi_ctx}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Einnahmen</div>
            <div class='metric-value positive'>+{total_income:,.0f} €</div>
            <div class='metric-delta'>ø {total_income/n_months:,.0f} €/Monat</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Ausgaben</div>
            <div class='metric-value negative'>−{total_expense:,.0f} €</div>
            <div class='metric-delta'>ø {total_expense/n_months:,.0f} €/Monat</div>
        </div>""", unsafe_allow_html=True)

    # Einnahmen vs. Ausgaben
    st.markdown(
        "<div class='section-header'>Einnahmen vs. Ausgaben</div>",
        unsafe_allow_html=True,
    )
    granularity = st.radio(
        "Granularität", ["Wöchentlich", "Monatlich", "Jährlich"],
        index=1, horizontal=True, label_visibility="collapsed", key="gran_ev",
    )

    gp = group_by_period(df, granularity)

    ev_chart_tab, ev_table_tab = st.tabs(["📊 Diagramm", "📋 Tabelle"])

    with ev_chart_tab:
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
            line=dict(color=C["savings"], width=2.5), marker=dict(size=5),
        ))
        fig_ev.update_layout(**PLOT_CFG, barmode="group", height=330)
        st.plotly_chart(fig_ev, use_container_width=True, config={"locale": "de", "displaylogo": False})

    with ev_table_tab:
        def _fmt_period(dt, gran):
            if gran == "Wöchentlich":
                return f"{dt.strftime('%d.%m.')} – {(dt + pd.Timedelta(days=6)).strftime('%d.%m.%Y')}"
            if gran == "Jährlich":
                return str(dt.year)
            return dt.strftime("%b %Y")

        gp_disp = gp.copy()
        gp_disp["Zeitraum"] = gp_disp["_period"].apply(lambda d: _fmt_period(d, granularity))
        gp_disp = gp_disp[["Zeitraum", "Einnahme", "Ausgabe", "Ersparnis"]].copy()
        gp_disp.columns = ["Zeitraum", "Einnahmen", "Ausgaben", "Gewinn"]
        gp_disp = gp_disp.iloc[::-1].reset_index(drop=True)

        def _col_ev(v):
            if isinstance(v, (int, float)):
                return "color: #e05c6a" if v < 0 else "color: #e8e6e1"
            return ""

        styled_ev = _style_map(
            gp_disp.style.format(
                {"Einnahmen": "{:,.0f} €", "Ausgaben": "{:,.0f} €", "Gewinn": "{:+,.0f} €"},
                na_rep="–",
            ),
            _col_ev, ["Einnahmen", "Ausgaben", "Gewinn"],
        )
        st.dataframe(styled_ev, use_container_width=True,
                     height=min(500, 36 + len(gp_disp) * 35),
                     hide_index=True)

    # Vermögensverlauf
    st.markdown(
        "<div class='section-header'>Vermögensverlauf</div>",
        unsafe_allow_html=True,
    )
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
    st.plotly_chart(fig4, use_container_width=True, config={"locale": "de", "displaylogo": False})

    # ── Highlights ────────────────────────────
    st.markdown(
        "<div class='section-header'>Highlights</div>",
        unsafe_allow_html=True,
    )

    # Größte Einzelausgabe
    if len(df_exp):
        idx_mx      = df_exp["_betrag_abs"].idxmax()
        max_exp_val = df_exp.loc[idx_mx, "_betrag_abs"]
        max_exp_kat = df_exp.loc[idx_mx, c["col_category"]]
        max_exp_dt  = df_exp.loc[idx_mx, c["col_date"]].strftime("%d.%m.%Y")
    else:
        max_exp_val, max_exp_kat, max_exp_dt = 0.0, "–", "–"

    # Häufigste Ausgabe-Kategorie
    if len(df_exp):
        top_kat     = df_exp[c["col_category"]].value_counts().index[0]
        top_kat_cnt = int(df_exp[c["col_category"]].value_counts().iloc[0])
    else:
        top_kat, top_kat_cnt = "–", 0

    # Ausgaben laufender Monat vs. Ø Vormonate
    curr_mo_exp  = df_exp[df_exp["_monat_dt"] == current_month_start]["_betrag_abs"].sum()
    prev_mo_exps = (df_exp[df_exp["_monat_dt"] < current_month_start]
                    .groupby("_monat_dt")["_betrag_abs"].sum())
    avg_prev_exp = prev_mo_exps.mean() if len(prev_mo_exps) else curr_mo_exp
    trend_delta  = curr_mo_exp - avg_prev_exp

    # Ø Sparquote abgeschlossene Monate
    avg_sq_hl = mw_comp_filt["Sparquote"].mean() if len(mw_comp_filt) else 0

    h1, h2, h3, h4 = st.columns(4)
    with h1:
        st.metric(
            "Größte Einzelausgabe",
            f"{max_exp_val:,.0f} €",
            delta=f"{max_exp_kat}  ·  {max_exp_dt}",
            delta_color="off",
            help="Höchster Einzelbetrag einer Ausgabetransaktion im gewählten Zeitraum.",
        )
    with h2:
        st.metric(
            "Häufigste Kategorie",
            top_kat,
            delta=f"{top_kat_cnt} Buchungen",
            delta_color="off",
            help="Ausgabe-Kategorie mit den meisten Einzelbuchungen im gewählten Zeitraum.",
        )
    with h3:
        st.metric(
            "Ø Sparquote (abgeschl. Monate)",
            f"{avg_sq_hl:+.1f} %",
            help=(
                "Durchschnittliche Sparquote über alle abgeschlossenen Monate im Zeitraum. "
                "Formel: (Einnahmen − Ausgaben) / Einnahmen × 100. "
                "Der laufende Monat wird ausgeschlossen, da er noch nicht vollständig ist."
            ),
        )
    with h4:
        st.metric(
            "Ausgaben akt. Monat",
            f"{curr_mo_exp:,.0f} €",
            delta=f"{trend_delta:+,.0f} € ggü. Ø Vormonat",
            delta_color="inverse",
            help=(
                "Ausgaben im laufenden Monat. "
                "Der Delta-Wert zeigt die Abweichung vom Durchschnitt der Vormonate im Zeitraum — "
                "grün bedeutet weniger als üblich ausgegeben, rot mehr."
            ),
        )

# ══════════════════════════════════════════════
with tab_s:
    with st.expander("ℹ️ Was ist die Sparquote?"):
        st.markdown(
            "Die **Sparquote** gibt an, welcher Anteil der Einnahmen gespart wurde — "
            "also nicht für Ausgaben verwendet wurde.\n\n"
            "**Formel:** (Einnahmen − Ausgaben) / Einnahmen × 100\n\n"
            "Eine Sparquote von **20 %** bedeutet: von 100 € Einnahmen wurden 20 € gespart "
            "und 80 € ausgegeben.\n\n"
            "**Hinweis:** Hier werden ausschließlich **abgeschlossene Monate** ausgewertet. "
            "Der laufende Monat wird weggelassen, da unvollständige Daten die Quote verzerren würden."
        )

    # Nur abgelaufene Monate
    mw2 = mw_comp_filt

    avg_sq = mw2["Sparquote"].mean() if len(mw2) else 0
    sq_cls = "positive" if avg_sq >= 0 else "negative"
    sq_sign = "+" if avg_sq >= 0 else ""

    # Letzter abgelaufener Monat (nicht der laufende)
    last_sq  = mw2["Sparquote"].iloc[-1] if len(mw2) else 0
    lsq_cls  = "positive" if last_sq >= 0 else "negative"
    lsq_lbl  = mw2["_monat_dt"].iloc[-1].strftime("%b %Y") if len(mw2) else "–"

    pos_mo   = int((mw2["Sparquote"] > 0).sum())
    total_mo = len(mw2)
    pos_pct  = pos_mo / total_mo * 100 if total_mo > 0 else 0

    st.markdown(
        "<div class='section-header'>Sparquoten-Übersicht (nur abgelaufene Monate)</div>",
        unsafe_allow_html=True,
    )
    sq1, sq2, sq3 = st.columns(3)
    with sq1:
        sq_min = mw2["Sparquote"].min() if len(mw2) else 0
        sq_max = mw2["Sparquote"].max() if len(mw2) else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>ø Sparquote im Zeitraum</div>
            <div class='metric-value {sq_cls}'>{sq_sign}{avg_sq:.1f} %</div>
            <div class='metric-delta'>Min {sq_min:.1f} % · Max {sq_max:.1f} %</div>
        </div>""", unsafe_allow_html=True)
    with sq2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Letzter abgelauf. Monat ({lsq_lbl})</div>
            <div class='metric-value {lsq_cls}'>{last_sq:+.1f} %</div>
            <div class='metric-delta'>Sparquote</div>
        </div>""", unsafe_allow_html=True)
    with sq3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Monate mit posit. Sparquote</div>
            <div class='metric-value neutral'>{pos_mo} / {total_mo}</div>
            <div class='metric-delta'>gewählter Zeitraum · {pos_pct:.0f} %</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(
        "<div class='section-header'>Sparquoten-Verlauf</div>",
        unsafe_allow_html=True,
    )
    dot_colors = [C["savings"] if v >= 0 else C["expense"] for v in mw2["Sparquote"]]
    fig3 = go.Figure(go.Scatter(
        x=mw2["_monat_dt"], y=mw2["Sparquote"],
        mode="lines+markers",
        line=dict(color=C["savings"], width=2),
        marker=dict(size=6, color=dot_colors),
        fill="tozeroy", fillcolor="rgba(123,138,255,0.06)",
        hovertemplate="%{x|%b %Y}: %{y:.1f} %<extra></extra>",
    ))
    fig3.add_hline(y=0, line_color="#4a4a6a", line_width=1)
    fig3.update_layout(**{**PLOT_CFG, "height": 300,
        "yaxis": dict(ticksuffix="%", gridcolor="#2a2a35", linecolor="#2a2a35")})
    st.plotly_chart(fig3, use_container_width=True, config={"locale": "de", "displaylogo": False})

    st.markdown(
        "<div class='section-header'>Monatlicher Gewinn</div>",
        unsafe_allow_html=True,
    )
    bar_colors = [C["savings"] if v >= 0 else C["expense"] for v in mw2["Ersparnis"]]
    fig5 = go.Figure(go.Bar(
        x=mw2["_monat_dt"], y=mw2["Ersparnis"],
        marker_color=bar_colors, opacity=0.85,
        text=mw2["Ersparnis"].apply(lambda x: f"{x:+,.0f} €"),
        textposition="outside", textfont=dict(color="#9a9ab0", size=10),
    ))
    fig5.add_hline(y=0, line_color="#4a4a6a", line_width=1)
    fig5.update_layout(**{**PLOT_CFG, "height": 280,
        "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
    st.plotly_chart(fig5, use_container_width=True, config={"locale": "de", "displaylogo": False})

# ══════════════════════════════════════════════
with tab_m:
    st.markdown(
        "<div class='section-header'>Alle Monate seit Aufzeichnungsbeginn</div>",
        unsafe_allow_html=True,
    )

    inc_mo = (
        df_all_today[df_all_today["_typ"] == "Einnahme"]
        .groupby("_monat_dt")["_betrag_abs"].sum()
    )
    exp_mo = (
        df_all_today[df_all_today["_typ"] == "Ausgabe"]
        .groupby("_monat_dt")["_betrag_abs"].sum()
    )
    all_months_idx = pd.date_range(
        start=df_all_today["_monat_dt"].min(),
        end=today.to_period("M").to_timestamp(),
        freq="MS",
    )
    tbl = pd.DataFrame(index=all_months_idx)
    tbl["Einnahmen"] = inc_mo.reindex(tbl.index, fill_value=0)
    tbl["Ausgaben"]  = exp_mo.reindex(tbl.index, fill_value=0)
    tbl["Sparmenge"] = tbl["Einnahmen"] - tbl["Ausgaben"]
    tbl["Vermögen"]  = STARTING_WEALTH + tbl["Sparmenge"].cumsum()
    tbl["ø Gesamt"]    = tbl["Sparmenge"].expanding().mean()
    tbl["ø 3 Monate"]  = tbl["Sparmenge"].rolling(window=3,  min_periods=1).mean()
    tbl["ø 6 Monate"]  = tbl["Sparmenge"].rolling(window=6,  min_periods=1).mean()
    tbl["ø 12 Monate"] = tbl["Sparmenge"].rolling(window=12, min_periods=3).mean()

    tbl.index = tbl.index.strftime("%b %Y")
    tbl = tbl.reset_index().rename(columns={"index": "Monat"})
    tbl = tbl.iloc[::-1].reset_index(drop=True)

    euro_cols = ["Einnahmen", "Ausgaben", "Sparmenge", "Vermögen",
                 "ø Gesamt", "ø 3 Monate", "ø 6 Monate", "ø 12 Monate"]

    def _col_monthly(v):
        try:
            if pd.isna(v):
                return "color: #4a4a6a"
        except (TypeError, ValueError):
            pass
        if isinstance(v, (int, float)):
            return "color: #e05c6a" if v < 0 else "color: #e8e6e1"
        return ""

    styled_tbl = _style_map(
        tbl.style.format("{:,.0f} €", subset=euro_cols, na_rep="–"),
        _col_monthly, euro_cols,
    )
    st.dataframe(styled_tbl, use_container_width=True,
                 height=min(600, 36 + len(tbl) * 35),
                 hide_index=True)

# ══════════════════════════════════════════════
with tab_k:

    _GRAN_OPTS = ["Wöchentlich", "Monatlich", "Jährlich"]
    _PLOT_CFG_KAT = {"locale": "de", "displaylogo": False}

    def _cat_table(df_src, total_months):
        stats = (
            df_src.groupby(c["col_category"])["_betrag_abs"]
            .agg(Gesamt="sum", Buchungen="count")
            .reset_index()
            .rename(columns={c["col_category"]: "Kategorie"})
        )
        grand = stats["Gesamt"].sum()
        stats["% Gesamt"]    = stats["Gesamt"] / grand * 100 if grand else 0
        stats["ø / Monat"]   = stats["Gesamt"] / total_months
        stats["€ / Buchung"] = stats["Gesamt"] / stats["Buchungen"].replace(0, float("nan"))
        stats = stats.sort_values("Gesamt", ascending=False).reset_index(drop=True)

        def _white(v):
            return "color: #e8e6e1" if isinstance(v, (int, float)) else ""

        num_cols = ["Gesamt", "% Gesamt", "ø / Monat", "Buchungen", "€ / Buchung"]
        return _style_map(
            stats.style.format(
                {"Gesamt": "{:,.0f} €", "% Gesamt": "{:.1f} %",
                 "ø / Monat": "{:,.0f} €", "Buchungen": "{:,.0f}",
                 "€ / Buchung": "{:,.0f} €"},
                na_rep="–",
            ),
            _white, num_cols,
        ), stats

    def _stacked_chart(df_src, granularity):
        df2 = df_src.copy()
        if granularity == "Wöchentlich":
            df2["_period"] = (
                df2[c["col_date"]]
                - pd.to_timedelta(df2[c["col_date"]].dt.dayofweek, unit="D")
            )
        elif granularity == "Jährlich":
            df2["_period"] = df2[c["col_date"]].dt.to_period("Y").dt.to_timestamp()
        else:
            df2["_period"] = df2["_monat_dt"]

        period_df = (
            df2.groupby(["_period", c["col_category"]])["_betrag_abs"]
            .sum().reset_index()
        )
        order = (
            df_src.groupby(c["col_category"])["_betrag_abs"].sum()
            .sort_values(ascending=True).index.tolist()
        )
        fig = go.Figure()
        for cat in order:
            sub = period_df[period_df[c["col_category"]] == cat]
            fig.add_trace(go.Bar(
                x=sub["_period"], y=sub["_betrag_abs"], name=cat,
                hovertemplate=f"{cat}: %{{y:,.0f}} €<extra></extra>",
            ))
        fig.update_layout(**{**PLOT_CFG, "height": 320, "barmode": "stack",
            "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
        return fig, period_df

    def _trend_chart(df_src, period_df, n_top=5):
        top = (
            df_src.groupby(c["col_category"])["_betrag_abs"].sum()
            .sort_values(ascending=False).head(n_top).index.tolist()
        )
        fig = go.Figure()
        for cat in top:
            sub = period_df[period_df[c["col_category"]] == cat]
            fig.add_trace(go.Scatter(
                x=sub["_period"], y=sub["_betrag_abs"], name=cat,
                mode="lines+markers", marker=dict(size=5),
                hovertemplate=f"{cat}: %{{y:,.0f}} €<extra></extra>",
            ))
        fig.update_layout(**{**PLOT_CFG, "height": 280,
            "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
        return fig

    # ── Sub-Tabs ──────────────────────────────
    kat_exp, kat_inc = st.tabs(["📉 Ausgaben", "📈 Einnahmen"])

    with kat_exp:
        exp_styled, exp_stats = _cat_table(df_exp, n_months)
        st.dataframe(exp_styled, use_container_width=True,
                     height=min(400, 36 + len(exp_stats) * 35),
                     hide_index=True)

        gran_exp = st.radio(
            "Granularität Ausgaben", _GRAN_OPTS, index=1,
            horizontal=True, label_visibility="collapsed", key="gran_kat_exp",
        )
        fig_exp_stack, exp_period = _stacked_chart(df_exp, gran_exp)
        st.plotly_chart(fig_exp_stack, use_container_width=True, config=_PLOT_CFG_KAT)
        st.plotly_chart(_trend_chart(df_exp, exp_period), use_container_width=True, config=_PLOT_CFG_KAT)

    with kat_inc:
        inc_styled, inc_stats = _cat_table(df_inc, n_months)
        st.dataframe(inc_styled, use_container_width=True,
                     height=min(300, 36 + len(inc_stats) * 35),
                     hide_index=True)

        gran_inc = st.radio(
            "Granularität Einnahmen", _GRAN_OPTS, index=1,
            horizontal=True, label_visibility="collapsed", key="gran_kat_inc",
        )
        fig_inc_stack, inc_period = _stacked_chart(df_inc, gran_inc)
        st.plotly_chart(fig_inc_stack, use_container_width=True, config=_PLOT_CFG_KAT)
        if len(inc_stats) > 1:
            st.plotly_chart(_trend_chart(df_inc, inc_period), use_container_width=True, config=_PLOT_CFG_KAT)

# ─────────────────────────────────────────────
# BUDGET-EXPANDER
# ─────────────────────────────────────────────
avg_by_cat       = (df_exp.groupby(c["col_category"])["_betrag_abs"].sum() / n_months).to_dict()
cats_with_budget = [cat for cat in sorted(avg_by_cat)
                    if st.session_state.get(f"budget_{cat}", 0) > 0]

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
st.markdown("---")

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
            st.number_input(cat, min_value=0.0, step=10.0, format="%.0f",
                            key=f"budget_{cat}")

# ─────────────────────────────────────────────
# TRANSAKTIONS-TABELLE
# ─────────────────────────────────────────────
with st.expander(f"\U0001f4cb Alle Transaktionen ({len(df):,})", expanded=False):
    show_cols = [c["col_date"], c["col_description"], c["col_category"], c["col_amount"]]
    show_cols = [col for col in show_cols if col in df.columns]
    disp      = df[show_cols].sort_values(c["col_date"], ascending=False).copy()
    disp[c["col_date"]] = disp[c["col_date"]].dt.strftime("%d.%m.%Y")
    disp = disp.reset_index(drop=True)

    def _col_amount(v):
        try:
            if pd.isna(v):
                return ""
        except (TypeError, ValueError):
            pass
        if isinstance(v, (int, float)):
            return "color: #5dd4a0" if v > 0 else "color: #e8e6e1"
        return ""

    styled_disp = _style_map(
        disp.style.format("{:,.2f} €", subset=[c["col_amount"]]),
        _col_amount, [c["col_amount"]],
    )
    st.dataframe(styled_disp, use_container_width=True, height=420)

# ─────────────────────────────────────────────
# DATENPUNKTE VERWALTEN
# ─────────────────────────────────────────────
_mgmt_expanded = st.session_state.pop("_mgmt_open", False)
with st.expander("✏️ Datenpunkte verwalten", expanded=_mgmt_expanded):
    mgmt_new, mgmt_edit = st.tabs(["➕ Neue Transaktion", "✏️ Bearbeiten / Löschen"])

    # ── Tab: Neue Transaktion ──────────────────
    with mgmt_new:
        if "new_tx_msg" in st.session_state:
            lvl, txt = st.session_state.pop("new_tx_msg")
            (st.success if lvl == "ok" else st.error)(txt)

        with st.form("new_tx", clear_on_submit=True):
            fi1, fi2, fi3, fi4 = st.columns([1, 1, 1, 2])
            with fi1:
                inp_date = st.date_input("Datum", value=today.date(), format="DD.MM.YYYY")
            with fi2:
                inp_betrag = st.number_input(
                    "Betrag (€)", value=0.0, step=0.01, format="%.2f",
                    help="Positiv = Einnahme · Negativ = Ausgabe",
                )
            with fi3:
                inp_kat_sel = st.selectbox(
                    "Kategorie",
                    all_cats_by_freq + ["✏️ Neue Kategorie…"],
                )
            with fi4:
                inp_desc = st.text_input("Beschreibung", placeholder="z.B. REWE, Gehalt, Miete …")

            if inp_kat_sel == "✏️ Neue Kategorie…":
                inp_kat_neu = st.text_input("Neue Kategorie eingeben")
            else:
                inp_kat_neu = ""

            submitted = st.form_submit_button("💾 Speichern", use_container_width=True)
            if submitted:
                kat = inp_kat_neu.strip() if inp_kat_sel == "✏️ Neue Kategorie…" else inp_kat_sel
                if not kat:
                    st.session_state["new_tx_msg"] = ("err", "Bitte eine Kategorie angeben.")
                else:
                    try:
                        append_transaction(
                            inp_date.strftime("%d.%m.%Y"), inp_betrag, kat, inp_desc.strip()
                        )
                        st.cache_data.clear()
                        msg = f"✓  {inp_date.strftime('%d.%m.%Y')}  ·  {inp_betrag:+.2f} €  ·  {kat}"
                        if inp_desc.strip():
                            msg += f"  ·  {inp_desc.strip()}"
                        st.session_state["new_tx_msg"] = ("ok", msg)
                    except Exception as ex:
                        st.session_state["new_tx_msg"] = ("err", f"Fehler beim Speichern: {ex}")
                st.session_state["_mgmt_open"] = True
                st.rerun()

    # ── Tab: Bearbeiten / Löschen ──────────────
    with mgmt_edit:
        if "edit_tx_msg" in st.session_state:
            lvl, txt = st.session_state.pop("edit_tx_msg")
            (st.success if lvl == "ok" else st.error)(txt)

        ed1, ed2, ed3 = st.columns([1, 1, 1])
        with ed1:
            ed_start = st.date_input(
                "Von", value=(today - pd.Timedelta(days=30)).date(),
                min_value=min_date, max_value=max_date,
                format="DD.MM.YYYY", key="ed_start",
            )
        with ed2:
            ed_end = st.date_input(
                "Bis", value=today.date(),
                min_value=min_date, max_value=max_date,
                format="DD.MM.YYYY", key="ed_end",
            )
        with ed3:
            ed_kat = st.selectbox("Kategorie", ["Alle"] + all_cats, key="ed_kat")

        df_edit = df_all_today[
            (df_all_today[c["col_date"]] >= pd.Timestamp(ed_start)) &
            (df_all_today[c["col_date"]] <= pd.Timestamp(ed_end))
        ].copy()
        if ed_kat != "Alle":
            df_edit = df_edit[df_edit[c["col_category"]] == ed_kat]
        df_edit = df_edit.sort_values(c["col_date"], ascending=False)

        if len(df_edit) == 0:
            st.info("Keine Transaktionen im gewählten Bereich.")
        else:
            option_labels = [
                f"{row[c['col_date']].strftime('%d.%m.%Y')}  ·  "
                f"{row[c['col_amount']]:+.2f} €  ·  "
                f"{row[c['col_category']]}  ·  {str(row[c['col_description']])[:40]}"
                for _, row in df_edit.iterrows()
            ]
            sheet_rows = list(df_edit["_sheet_row"])
            sel_label  = st.selectbox("Transaktion auswählen", option_labels, key="ed_sel")
            sel_idx    = option_labels.index(sel_label)
            sel_sr     = sheet_rows[sel_idx]
            sel_row    = df_edit.iloc[sel_idx]

            with st.form("edit_tx"):
                ec1, ec2, ec3, ec4 = st.columns([1, 1, 1, 2])
                with ec1:
                    edit_date = st.date_input(
                        "Datum", value=sel_row[c["col_date"]].date(), format="DD.MM.YYYY",
                    )
                with ec2:
                    edit_betrag = st.number_input(
                        "Betrag (€)", value=float(sel_row[c["col_amount"]]),
                        step=0.01, format="%.2f",
                    )
                with ec3:
                    cur_kat  = sel_row[c["col_category"]]
                    kat_opts = all_cats_by_freq + ([] if cur_kat in all_cats_by_freq else [cur_kat])
                    edit_kat = st.selectbox(
                        "Kategorie", kat_opts,
                        index=kat_opts.index(cur_kat) if cur_kat in kat_opts else 0,
                    )
                with ec4:
                    edit_desc = st.text_input(
                        "Beschreibung", value=str(sel_row[c["col_description"]]),
                    )

                confirm_del = st.checkbox("⚠️ Löschen bestätigen")
                btn_s, btn_d = st.columns(2)
                with btn_s:
                    save_ok = st.form_submit_button("💾 Änderungen speichern",
                                                    use_container_width=True)
                with btn_d:
                    del_ok = st.form_submit_button("🗑️ Löschen",
                                                   use_container_width=True, type="secondary")

                if save_ok:
                    try:
                        update_transaction(
                            sel_sr, edit_date.strftime("%d.%m.%Y"),
                            edit_betrag, edit_kat, edit_desc.strip(),
                        )
                        st.cache_data.clear()
                        st.session_state["edit_tx_msg"] = ("ok", "✓ Transaktion aktualisiert.")
                    except Exception as ex:
                        st.session_state["edit_tx_msg"] = ("err", f"Fehler: {ex}")
                    st.session_state["_mgmt_open"] = True
                    st.rerun()

                if del_ok:
                    if not confirm_del:
                        st.session_state["edit_tx_msg"] = ("err", "Bitte Löschen per Checkbox bestätigen.")
                    else:
                        try:
                            delete_transaction(sel_sr)
                            st.cache_data.clear()
                            st.session_state["edit_tx_msg"] = ("ok", "✓ Transaktion gelöscht.")
                        except Exception as ex:
                            st.session_state["edit_tx_msg"] = ("err", f"Fehler: {ex}")
                    st.session_state["_mgmt_open"] = True
                    st.rerun()
