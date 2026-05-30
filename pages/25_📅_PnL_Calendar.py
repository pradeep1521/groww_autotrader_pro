"""
P&L Calendar – Monthly Heatmap & Performance Analytics
========================================================
Daily P&L calendar heatmap · Daily bar chart · Win rate by weekday/month
Best/worst days · Running stats · Streak analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date
import calendar

st.set_page_config(page_title="P&L Calendar", page_icon="📅", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background:#0d0d1a; }
[data-testid="stSidebar"] { background:linear-gradient(160deg,#0d0d1a,#1a1a2e); }
[data-testid="stSidebar"] * { color:#c0caf5 !important; }
.block-container { padding-top:1.2rem !important; }
.rule-header {
  font-size:1rem; font-weight:700; color:#ffd200;
  border-left:3px solid #ffd200; padding-left:8px; margin:.8rem 0 .5rem;
}
[data-testid="stMetric"] { background:#12122a; border:1px solid #ffffff10; border-radius:10px; padding:.8rem; }
[data-testid="stMetricValue"] { color:#ffd200 !important; font-size:1.4rem !important; font-weight:700 !important; }
.stat-card {
  background:#12122a; border:1px solid #ffffff10; border-radius:12px;
  padding:1rem 1.2rem; text-align:center;
}
.stat-value { font-size:1.5rem; font-weight:800; }
.stat-label { font-size:.75rem; color:#8892a4; margin-top:.2rem; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _pnl_from_positions() -> pd.DataFrame:
    """Aggregate daily P&L from paper_positions session state."""
    positions = st.session_state.get("paper_positions", [])
    closed    = [p for p in positions
                 if p.get("status","OPEN") == "CLOSED" and p.get("realized_pnl") is not None]
    if not closed:
        return pd.DataFrame(columns=["date","pnl"])
    rows = []
    for p in closed:
        ts = p.get("timestamp", p.get("exit_time",""))
        try:
            d = pd.to_datetime(ts).date()
        except:
            d = date.today()
        rows.append({"date": d, "pnl": float(p.get("realized_pnl", 0))})
    df = pd.DataFrame(rows)
    return df.groupby("date")["pnl"].sum().reset_index()

def _demo_pnl(months_back: int = 3) -> pd.DataFrame:
    """Generate synthetic daily P&L for demo purposes."""
    rng   = np.random.default_rng(42)
    end   = date.today()
    start = end - timedelta(days=months_back * 30)
    rows  = []
    d     = start
    while d <= end:
        # Skip weekends
        if d.weekday() < 5:
            pnl = rng.normal(500, 2500)
            rows.append({"date": d, "pnl": round(pnl, 2)})
        d += timedelta(days=1)
    return pd.DataFrame(rows)

def _build_calendar_fig(df_pnl: pd.DataFrame, month: int, year: int) -> go.Figure:
    """Build a calendar heatmap for a given month."""
    # Get day grid
    cal = calendar.monthcalendar(year, month)
    z, customdata, hover = [], [], []

    for week in cal:
        row_z, row_cd, row_hv = [], [], []
        for wd in week:
            if wd == 0:
                row_z.append(None)
                row_cd.append("")
                row_hv.append("")
            else:
                d = date(year, month, wd)
                row = df_pnl[df_pnl["date"] == d]
                pnl = float(row["pnl"].iloc[0]) if not row.empty else None
                row_z.append(pnl)
                row_cd.append(f"{d.strftime('%b %d')}<br>{'₹{:+,.0f}'.format(pnl) if pnl is not None else 'No trade'}")
                row_hv.append(f"₹{pnl:+,.0f}" if pnl is not None else "")
        z.append(row_z)
        row_cd_str = row_cd
        hover.append(row_hv)

    days_abbr = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    fig = go.Figure(go.Heatmap(
        z=z,
        text=[[f"<b>{d if d else ''}</b><br>{h}" for d,h in zip(week, wh)]
              for week,wh in zip([[w for w in wk] for wk in cal], hover)],
        texttemplate="%{text}",
        colorscale=[
            [0.0, "#7f0000"],
            [0.3, "#ff5252"],
            [0.48, "#ff525255"],
            [0.5, "#1a1a2e"],
            [0.52, "#00c85355"],
            [0.7, "#00c853"],
            [1.0, "#007a2f"],
        ],
        zmid=0,
        xgap=4, ygap=4,
        showscale=True,
        colorbar=dict(
            title="P&L (₹)", tickfont=dict(color="#c0caf5"),
            titlefont=dict(color="#c0caf5"), bgcolor="#12122a", bordercolor="#ffffff10"),
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(
        title=f"{calendar.month_name[month]} {year} – Daily P&L",
        xaxis=dict(tickmode="array", tickvals=list(range(7)), ticktext=days_abbr,
                   side="top", gridcolor="#ffffff10", tickfont=dict(color="#c0caf5")),
        yaxis=dict(visible=False),
        plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=320,
        margin=dict(t=60, b=20, l=20, r=20))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#ffd200;margin:0;font-weight:800;'>📅 P&L Calendar</h2>"
    "<div style='color:#8892a4;font-size:.85rem;'>Daily · Weekly · Monthly performance analytics</div>",
    unsafe_allow_html=True)
st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
real_df = _pnl_from_positions()
use_demo = real_df.empty

hc1, hc2 = st.columns([5, 2])
with hc1:
    data_src = st.radio("Data source", ["Paper Trades", "Demo Data"],
                        horizontal=True, key="pnl_src",
                        index=0 if not use_demo else 1)
with hc2:
    months_back = st.select_slider("History", [1, 2, 3, 6, 12], value=3, key="pnl_hist")

if data_src == "Demo Data" or use_demo:
    df_pnl = _demo_pnl(months_back)
    if use_demo and data_src == "Paper Trades":
        st.info("No closed paper trades yet — showing demo data.", icon="ℹ️")
else:
    end   = date.today()
    start = end - timedelta(days=months_back * 30)
    df_pnl = real_df[real_df["date"] >= start].copy()

if df_pnl.empty:
    st.warning("No P&L data to display.", icon="⚠️")
    st.stop()

df_pnl["date"] = pd.to_datetime(df_pnl["date"]).dt.date

# ── Aggregate stats ───────────────────────────────────────────────────────────
total_pnl  = df_pnl["pnl"].sum()
win_days   = (df_pnl["pnl"] > 0).sum()
loss_days  = (df_pnl["pnl"] < 0).sum()
total_days = len(df_pnl)
win_rate   = win_days / total_days * 100 if total_days > 0 else 0
best_day   = df_pnl.loc[df_pnl["pnl"].idxmax()]
worst_day  = df_pnl.loc[df_pnl["pnl"].idxmin()]
avg_win    = df_pnl[df_pnl["pnl"] > 0]["pnl"].mean() if win_days else 0
avg_loss   = df_pnl[df_pnl["pnl"] < 0]["pnl"].mean() if loss_days else 0
expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

# Streak
streak_val, streak_type, max_win_streak, max_loss_streak = 0, "—", 0, 0
cur_w, cur_l = 0, 0
for pnl in df_pnl["pnl"]:
    if pnl > 0:
        cur_w += 1; cur_l = 0
        max_win_streak = max(max_win_streak, cur_w)
    else:
        cur_l += 1; cur_w = 0
        max_loss_streak = max(max_loss_streak, cur_l)
cur_streak = cur_w if cur_w > 0 else -cur_l
streak_label = f"{'🟢' if cur_streak>=0 else '🔴'} {abs(cur_streak)}-{'win' if cur_streak>=0 else 'loss'} streak"

# ── Summary Metrics ───────────────────────────────────────────────────────────
st.markdown("### 📊 Performance Summary")
mc = st.columns(8)
vals = [
    (f"₹{total_pnl:+,.0f}", "Total P&L", "#00c853" if total_pnl>=0 else "#ff5252"),
    (f"{win_rate:.1f}%",     "Win Rate",  "#ffd200"),
    (f"{win_days}/{total_days}", "Win Days", "#00c853"),
    (f"₹{avg_win:,.0f}",    "Avg Win",   "#00c853"),
    (f"₹{avg_loss:,.0f}",   "Avg Loss",  "#ff5252"),
    (f"₹{expectancy:,.0f}", "Expectancy","#a78bfa"),
    (f"{max_win_streak}",   "Max Win Streak","#00c853"),
    (f"{max_loss_streak}",  "Max Loss Streak","#ff5252"),
]
for col, (val, label, color) in zip(mc, vals):
    with col:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value" style="color:{color};">{val}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True)

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_cal, tab_bar, tab_wkday, tab_monthly, tab_dist = st.tabs([
    "📅 Calendar", "📊 Daily Bar", "📆 By Weekday", "📆 By Month", "📈 Distribution"
])

# ═══════════════════════════════════════════════════════════════
# Calendar heatmap
# ═══════════════════════════════════════════════════════════════
with tab_cal:
    today        = date.today()
    available_months = sorted({(d.year, d.month) for d in df_pnl["date"]}, reverse=True)
    month_labels = [f"{calendar.month_name[m]} {y}" for y,m in available_months]

    cal_col1, cal_col2 = st.columns([3,1])
    with cal_col2:
        sel_month_str = st.selectbox("Select month", month_labels, key="pnl_month")
    sel_idx   = month_labels.index(sel_month_str)
    sel_year, sel_month = available_months[sel_idx]

    fig_cal = _build_calendar_fig(df_pnl, sel_month, sel_year)
    st.plotly_chart(fig_cal, use_container_width=True)

    # Mini stats for selected month
    month_df = df_pnl[
        (pd.to_datetime(df_pnl["date"]).dt.month == sel_month) &
        (pd.to_datetime(df_pnl["date"]).dt.year  == sel_year)]
    if not month_df.empty:
        mc1,mc2,mc3,mc4 = st.columns(4)
        with mc1: st.metric("Month P&L",  f"₹{month_df['pnl'].sum():+,.0f}")
        with mc2: st.metric("Win Rate",   f"{(month_df['pnl']>0).sum()}/{len(month_df)} days")
        with mc3: st.metric("Best Day",   f"₹{month_df['pnl'].max():+,.0f} · {month_df.loc[month_df['pnl'].idxmax(),'date']}")
        with mc4: st.metric("Worst Day",  f"₹{month_df['pnl'].min():+,.0f} · {month_df.loc[month_df['pnl'].idxmin(),'date']}")

# ═══════════════════════════════════════════════════════════════
# Daily bar chart
# ═══════════════════════════════════════════════════════════════
with tab_bar:
    df_sorted = df_pnl.sort_values("date")
    df_sorted["cumulative"] = df_sorted["pnl"].cumsum()
    df_sorted["date_str"]   = df_sorted["date"].apply(lambda d: d.strftime("%b %d"))

    fig_bar = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             row_heights=[0.6, 0.4], vertical_spacing=0.05)

    bar_colors = ["#00c853" if v >= 0 else "#ff5252" for v in df_sorted["pnl"]]
    fig_bar.add_trace(go.Bar(x=df_sorted["date_str"], y=df_sorted["pnl"],
                              marker_color=bar_colors, name="Daily P&L"), row=1, col=1)
    fig_bar.add_hline(y=0, line_color="#ffffff30", line_width=1, row=1, col=1)

    fig_bar.add_trace(go.Scatter(x=df_sorted["date_str"], y=df_sorted["cumulative"],
                                  mode="lines", fill="tozeroy",
                                  line=dict(color="#ffd200", width=2),
                                  fillcolor="#ffd20015", name="Cumulative"), row=2, col=1)

    fig_bar.update_layout(
        plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=500,
        showlegend=True, legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis2=dict(gridcolor="#ffffff10"),
        yaxis=dict(title="Daily P&L (₹)", gridcolor="#ffffff10"),
        yaxis2=dict(title="Cumulative (₹)", gridcolor="#ffffff10"),
        margin=dict(t=30, b=40, l=70, r=30))
    st.plotly_chart(fig_bar, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# By Weekday
# ═══════════════════════════════════════════════════════════════
with tab_wkday:
    df_wk = df_pnl.copy()
    df_wk["weekday"] = pd.to_datetime(df_wk["date"]).dt.day_name()
    wk_order = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
    wk_agg   = (df_wk.groupby("weekday")["pnl"]
                .agg(["sum","mean","count",
                      lambda s: (s>0).sum(),
                      lambda s: (s<=0).sum()])
                .reindex(wk_order).reset_index())
    wk_agg.columns = ["Weekday","Total","Avg","Trades","Wins","Losses"]
    wk_agg["Win %"] = wk_agg["Wins"] / wk_agg["Trades"] * 100

    wk_col1, wk_col2 = st.columns(2)
    with wk_col1:
        fig_wk = go.Figure(go.Bar(
            x=wk_agg["Weekday"], y=wk_agg["Total"],
            marker_color=["#00c853" if v>=0 else "#ff5252" for v in wk_agg["Total"]],
            text=[f"₹{v:+,.0f}" for v in wk_agg["Total"]], textposition="outside"))
        fig_wk.update_layout(title="Total P&L by Weekday",
                              plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
                              font_color="#c0caf5", height=350,
                              yaxis=dict(gridcolor="#ffffff10"),
                              margin=dict(t=40,b=40,l=70,r=20))
        st.plotly_chart(fig_wk, use_container_width=True)
    with wk_col2:
        fig_wr = go.Figure(go.Bar(
            x=wk_agg["Weekday"], y=wk_agg["Win %"],
            marker_color=["#00c853" if v>=50 else "#ff5252" for v in wk_agg["Win %"]],
            text=[f"{v:.0f}%" for v in wk_agg["Win %"]], textposition="outside"))
        fig_wr.add_hline(y=50, line_color="#ffd200", line_dash="dash")
        fig_wr.update_layout(title="Win Rate % by Weekday",
                              plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
                              font_color="#c0caf5", height=350, yaxis_range=[0, 100],
                              yaxis=dict(title="Win %", gridcolor="#ffffff10"),
                              margin=dict(t=40,b=40,l=70,r=20))
        st.plotly_chart(fig_wr, use_container_width=True)

    st.dataframe(wk_agg.style.format({
        "Total": "₹{:+,.0f}", "Avg": "₹{:+,.0f}",
        "Win %": "{:.1f}%", "Trades": "{:.0f}", "Wins": "{:.0f}", "Losses": "{:.0f}"
    }), hide_index=True, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# By Month
# ═══════════════════════════════════════════════════════════════
with tab_monthly:
    df_mo = df_pnl.copy()
    df_mo["month"] = pd.to_datetime(df_mo["date"]).dt.to_period("M").astype(str)
    mo_agg = (df_mo.groupby("month")["pnl"]
              .agg(["sum","count", lambda s: (s>0).sum()])
              .reset_index())
    mo_agg.columns = ["Month","Total","Trades","Wins"]
    mo_agg["Win %"] = mo_agg["Wins"] / mo_agg["Trades"] * 100

    fig_mo = go.Figure(go.Bar(
        x=mo_agg["Month"], y=mo_agg["Total"],
        marker_color=["#00c853" if v>=0 else "#ff5252" for v in mo_agg["Total"]],
        text=[f"₹{v:+,.0f}" for v in mo_agg["Total"]], textposition="outside"))
    fig_mo.update_layout(title="Monthly P&L",
                          plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
                          font_color="#c0caf5", height=380,
                          yaxis=dict(title="P&L (₹)", gridcolor="#ffffff10"),
                          margin=dict(t=40,b=40,l=70,r=20))
    st.plotly_chart(fig_mo, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# Distribution
# ═══════════════════════════════════════════════════════════════
with tab_dist:
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=df_pnl["pnl"], nbinsx=30,
        marker=dict(
            color=[("#00c853" if v>=0 else "#ff5252") for v in df_pnl["pnl"]],
            line=dict(width=0)),
        name="P&L Distribution"))
    fig_dist.add_vline(x=0,    line_color="#ffffff50", line_dash="dash")
    fig_dist.add_vline(x=float(df_pnl["pnl"].mean()), line_color="#ffd200",
                       line_dash="dot", annotation_text=f"Avg ₹{df_pnl['pnl'].mean():,.0f}",
                       annotation_font_color="#ffd200")
    fig_dist.update_layout(
        title="P&L Distribution",
        plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=380,
        xaxis=dict(title="P&L (₹)", gridcolor="#ffffff10"),
        yaxis=dict(title="Frequency", gridcolor="#ffffff10"),
        bargap=0.1, margin=dict(t=40,b=40,l=70,r=20))
    st.plotly_chart(fig_dist, use_container_width=True)

    d1,d2,d3 = st.columns(3)
    with d1: st.metric("Mean",   f"₹{df_pnl['pnl'].mean():+,.0f}")
    with d2: st.metric("Std Dev",f"₹{df_pnl['pnl'].std():,.0f}")
    with d3: st.metric("Sharpe (daily)", f"{df_pnl['pnl'].mean()/df_pnl['pnl'].std():.2f}" if df_pnl['pnl'].std()>0 else "—")
