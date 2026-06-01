import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import CONFIG, STARTING_WEALTH, PLOT_CFG, C, CSS, load_data, prepare

st.set_page_config(page_title="Sparanalyse", page_icon="💰", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATEN LADEN (vollständig, kein Datumsfilter)
# ─────────────────────────────────────────────
try:
    raw    = load_data()
    df_all = prepare(raw)
    data_ok = True
except Exception as e:
    data_ok    = False
    load_error = str(e)

with st.sidebar:
    st.markdown("## 💰 Sparanalyse")
    if not data_ok:
        st.error("Keine Verbindung zu Google Sheets.")
    else:
        if st.button("🔄 Neu laden", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.markdown(
            "<div style='font-size:11px;color:#4a4a6a;font-family:DM Mono,monospace'>"
            "Unabhängig vom Hauptfilter<br>Alle Daten · Daten gecacht · 5 min</div>",
            unsafe_allow_html=True
        )

if not data_ok:
    st.error(f"Google Sheets Verbindungsfehler: `{load_error}`")
    st.stop()

c     = CONFIG
today = pd.Timestamp.today().normalize()


# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def period_stats(start, end):
    mask = (df_all[c["col_date"]] >= start) & (df_all[c["col_date"]] <= end)
    sub  = df_all[mask]
    inc  = sub[sub["_typ"] == "Einnahme"]["_betrag_abs"].sum()
    exp  = sub[sub["_typ"] == "Ausgabe"]["_betrag_abs"].sum()
    sav  = inc - exp
    rate = (sav / inc * 100) if inc > 0 else 0
    return inc, exp, sav, rate, len(sub)


def last_occurrence(ref, day):
    """Letzter vergangener (oder heutiger) Tag mit gegebenem Monatstag."""
    candidate = ref.replace(day=day)
    if candidate > ref:
        candidate = (ref - pd.DateOffset(months=1)).replace(day=day)
    return candidate


def render_period_cards(ref_date):
    periods = [
        ("Letzter Monat",  1),
        ("3 Monate",       3),
        ("6 Monate",       6),
        ("12 Monate",     12),
    ]
    for label, months in periods:
        start = ref_date - pd.DateOffset(months=months)
        inc, exp, sav, rate, n = period_stats(start, ref_date)
        cls  = "positive" if sav >= 0 else "negative"
        sign = "+" if sav >= 0 else "−"
        st.markdown(f"""<div class='metric-card' style='margin-bottom:8px'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <div>
                    <div class='metric-label'>{label} &nbsp;·&nbsp; {start.strftime("%d.%m.%Y")} – {ref_date.strftime("%d.%m.%Y")}</div>
                    <div class='metric-value {cls}'>{sign}{abs(sav):,.0f} €</div>
                    <div class='metric-delta'>Sparquote {rate:.1f} % &nbsp;·&nbsp; {n} Buchungen</div>
                </div>
                <div style='text-align:right;padding-left:16px'>
                    <div style='color:#5dd4a0;font-family:DM Mono,monospace;font-size:13px'>+{inc:,.0f} €</div>
                    <div style='color:#e05c6a;font-family:DM Mono,monospace;font-size:13px'>−{exp:,.0f} €</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# Sparanalyse")
st.markdown(
    f"<div style='color:#6b6b8a;font-size:13px;font-family:DM Mono,monospace;margin-bottom:28px'>"
    f"Unabhängig vom Hauptfilter · Stand: {today.strftime('%d.%m.%Y')}</div>",
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────
# VERMÖGENS-ÜBERSICHT
# ─────────────────────────────────────────────
df_to_today    = df_all[df_all[c["col_date"]] <= today]
wealth_now     = STARTING_WEALTH + df_to_today[c["col_amount"]].sum()
delta          = wealth_now - STARTING_WEALTH
delta_cls      = "positive" if delta >= 0 else "negative"
delta_sign     = "+" if delta >= 0 else "−"
first_date     = df_all[c["col_date"]].min() if len(df_all) else today
total_days     = max((today - first_date).days, 1)
daily_rate     = delta / total_days

col_w1, col_w2, col_w3 = st.columns(3)
with col_w1:
    wcls = "positive" if wealth_now >= STARTING_WEALTH else "negative"
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Aktuelles Vermögen</div>
        <div class='metric-value {wcls}'>{wealth_now:,.0f} €</div>
        <div class='metric-delta'>Startkapital: {STARTING_WEALTH:,.2f} €</div>
    </div>""", unsafe_allow_html=True)
with col_w2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Zuwachs seit Start</div>
        <div class='metric-value {delta_cls}'>{delta_sign}{abs(delta):,.0f} €</div>
        <div class='metric-delta'>Über {total_days} Tage seit {first_date.strftime("%d.%m.%Y")}</div>
    </div>""", unsafe_allow_html=True)
with col_w3:
    dr_cls = "positive" if daily_rate >= 0 else "negative"
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Ø Tägl. Zuwachs</div>
        <div class='metric-value {dr_cls}'>{daily_rate:+,.2f} €/Tag</div>
        <div class='metric-delta'>⌀ {daily_rate * 30:+,.0f} €/Monat</div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# STICHTAG-ANALYSE: 19. und 1.
# ─────────────────────────────────────────────
ref_19 = last_occurrence(today, 19)
ref_1  = last_occurrence(today, 1)

col_left, col_right = st.columns(2)

with col_left:
    st.markdown(
        f"<div class='section-header'>Stichtag 19. · Referenz: {ref_19.strftime('%d.%m.%Y')}</div>",
        unsafe_allow_html=True
    )
    render_period_cards(ref_19)

with col_right:
    st.markdown(
        f"<div class='section-header'>Stichtag 1. · Referenz: {ref_1.strftime('%d.%m.%Y')}</div>",
        unsafe_allow_html=True
    )
    render_period_cards(ref_1)

# ─────────────────────────────────────────────
# MONATLICHER SPARTREND (Stichtag 19.)
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Monatliches Erspartes – Stichtag 19.</div>", unsafe_allow_html=True)

monthly_rows = []
for i in range(12):
    end   = ref_19 - pd.DateOffset(months=i)
    start = ref_19 - pd.DateOffset(months=i + 1)
    _, _, sav, rate, _ = period_stats(start, end)
    monthly_rows.append({"Periode": end.strftime("%b %Y"), "Periode_dt": end,
                          "Erspartes": sav, "Sparquote": rate})
monthly_rows.reverse()
mdf = pd.DataFrame(monthly_rows)

bar_colors = [C["savings"] if v >= 0 else C["expense"] for v in mdf["Erspartes"]]
fig_trend = go.Figure(go.Bar(
    x=mdf["Periode_dt"], y=mdf["Erspartes"],
    marker_color=bar_colors, opacity=0.85,
    text=mdf["Erspartes"].apply(lambda x: f"{x:+,.0f} €"),
    textposition="outside", textfont=dict(color="#9a9ab0", size=10),
))
fig_trend.add_hline(y=0, line_color="#4a4a6a", line_width=1)
fig_trend.update_layout(**{**PLOT_CFG, "height": 280,
    "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
st.plotly_chart(fig_trend, use_container_width=True)

# ─────────────────────────────────────────────
# VERMÖGENSVERLAUF (gesamt, ohne Datumsfilter)
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>Vermögensverlauf (gesamt)</div>", unsafe_allow_html=True)

df_s = df_all.sort_values(c["col_date"]).copy()
df_s["_vermoegen"] = STARTING_WEALTH + df_s[c["col_amount"]].cumsum()

fig_wealth = go.Figure()
fig_wealth.add_trace(go.Scatter(
    x=df_s[c["col_date"]], y=df_s["_vermoegen"],
    mode="lines", fill="tozeroy",
    fillcolor="rgba(123,138,255,0.08)",
    line=dict(color=C["savings"], width=2.5),
    hovertemplate="%{x|%d.%m.%Y}: %{y:,.0f} €<extra></extra>",
))
for day, color in [(19, "#5dd4a0"), (1, "#7b8aff")]:
    ref = last_occurrence(today, day)
    fig_wealth.add_vline(
        x=ref.timestamp() * 1000, line_color=color,
        line_width=1, line_dash="dot",
        annotation_text=f"{day}.",
        annotation_font_color=color,
        annotation_position="top right",
    )
fig_wealth.add_hline(y=0, line_color="#4a4a6a", line_width=1, line_dash="dot")
fig_wealth.update_layout(**{**PLOT_CFG, "height": 300,
    "yaxis": dict(ticksuffix=" €", gridcolor="#2a2a35", linecolor="#2a2a35")})
st.plotly_chart(fig_wealth, use_container_width=True)
