"""
dashboard.py — Real-Time Network QoE Dashboard (Streamlit)
===========================================================
Run:
  streamlit run dashboard.py -- --server http://localhost:5000
  streamlit run dashboard.py -- --server https://xxxx.ngrok-free.app
"""

import argparse
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QoE Network Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS / theme ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #080c14;
    color: #c8d6e5;
}
.mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; }

/* KPI card */
.kpi-wrap { display:flex; gap:16px; margin-bottom:20px; }
.kpi {
    flex:1; background:#0d1220; border:1px solid #1e2d45;
    border-radius:10px; padding:18px 22px;
}
.kpi-val  { font-size:2rem; font-weight:800; font-family:'IBM Plex Mono',monospace; color:#38bdf8; }
.kpi-lbl  { font-size:0.72rem; color:#64748b; text-transform:uppercase; letter-spacing:.1em; }

/* User row cards */
.ucard {
    background:#0d1220; border:1px solid #1e2d45;
    border-radius:8px; padding:12px 18px; margin:6px 0;
    display:flex; align-items:center; gap:18px; flex-wrap:wrap;
}
.ucard.alert { border-color:#ef4444; background:#130a0a; }
.uname  { font-weight:700; font-size:1rem; min-width:100px; }
.badge  { padding:2px 11px; border-radius:20px; font-size:0.7rem; font-weight:700; font-family:'IBM Plex Mono',monospace; }
.good   { background:#052e16; color:#4ade80; border:1px solid #4ade80; }
.mod    { background:#2d1b00; color:#fbbf24; border:1px solid #fbbf24; }
.poor   { background:#2d0e0e; color:#f87171; border:1px solid #f87171; }
.metric { font-family:'IBM Plex Mono',monospace; font-size:0.78rem; color:#94a3b8; }
.sus-hi { color:#ef4444; font-weight:700; }
.sus-md { color:#fbbf24; font-weight:700; }
.sus-lo { color:#4ade80; font-weight:700; }
.reason-txt { font-size:0.72rem; color:#475569; margin-top:4px; }
.section-title {
    font-size:0.7rem; text-transform:uppercase; letter-spacing:.15em;
    color:#475569; margin:24px 0 10px;
}
</style>
""", unsafe_allow_html=True)


# ── CLI argument parsing (passed after `--`) ──────────────────────────────────
def get_server_url() -> str:
    try:
        idx = sys.argv.index("--")
        p = argparse.ArgumentParser()
        p.add_argument("--server", default="http://localhost:5000")
        return p.parse_known_args(sys.argv[idx + 1:])[0].server.rstrip("/")
    except ValueError:
        return "http://localhost:5000"


SERVER = get_server_url()


# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=4)
def fetch(url: str) -> dict:
    try:
        r = requests.get(f"{url}/view", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def build_df(raw: dict) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    rows = []
    for user, d in raw.items():
        rows.append({
            "User"          : user,
            "QoE Score"     : d.get("qoe_score",        0.0),
            "QoE Label"     : d.get("qoe_label",        "—"),
            "Bandwidth(Mbps)": d.get("bandwidth_mbps",   0.0),
            "Latency(ms)"   : d.get("latency_ms",        0.0),
            "Pkt Loss(%)"   : round(d.get("packet_loss", 0.0) * 100, 2),
            "Video"         : d.get("video_on",          True),
            "Suspicion"     : d.get("suspicion_score",   0.0),
            "Reason"        : d.get("reason",            ""),
            "Last Updated"  : d.get("server_received_at", ""),
            "Source"        : d.get("source",            "client"),
        })
    return pd.DataFrame(rows).sort_values("Suspicion", ascending=False).reset_index(drop=True)


def qoe_badge(label: str) -> str:
    cls = {"GOOD": "good", "MODERATE": "mod", "POOR": "poor"}.get(label, "")
    return f'<span class="badge {cls}">{label}</span>'


def sus_class(v: float) -> str:
    if v >= 0.6: return "sus-hi"
    if v >= 0.3: return "sus-md"
    return "sus-lo"


def time_ago(iso: str) -> str:
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        s = int((datetime.now(timezone.utc) - t).total_seconds())
        return f"{s}s ago"
    except Exception:
        return "—"


# ── Plotly theme ──────────────────────────────────────────────────────────────
THEME = dict(
    template    = "plotly_dark",
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font_color    = "#94a3b8",
    margin        = dict(l=0, r=0, t=30, b=0),
)
QOE_COLORS = {"GOOD": "#4ade80", "MODERATE": "#fbbf24", "POOR": "#f87171"}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 QoE Monitor")
    st.markdown(f"**Server**  \n`{SERVER}`")
    st.markdown("---")
    refresh = st.slider("Refresh interval (s)", 2, 30, 5)
    st.markdown("---")
    st.markdown("### QoE Classes")
    st.markdown('<span class="badge good">GOOD</span> &nbsp; score > 0.5',     unsafe_allow_html=True)
    st.markdown('<span class="badge mod">MODERATE</span> &nbsp; 0 < score ≤ 0.5', unsafe_allow_html=True)
    st.markdown('<span class="badge poor">POOR</span> &nbsp; score ≤ 0',       unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Suspicion")
    st.markdown("🔴 ≥ 0.6 High")
    st.markdown("🟡 ≥ 0.3 Medium")
    st.markdown("🟢 < 0.3 Low")
    st.markdown("---")
    st.markdown("### Formula")
    st.latex(r"QoE = (1-P_{out})\left[(1-B)\ln\frac{C}{C_{th}} - \ln L\right]")


# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown("# 🖥️ Meeting Network QoE Monitor")
st.caption(f"Polling `{SERVER}/view` every {refresh}s · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

slot = st.empty()

# ── Main Loop ─────────────────────────────────────────────────────────────────
while True:
    raw = fetch(SERVER)
    df  = build_df(raw)

    with slot.container():
        if df.empty:
            st.warning("⚠️  No clients connected yet. Start a client or load the extension.")
        else:
            # ── KPI row ──────────────────────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👥 Connected Users",   len(df))
            c2.metric("🚨 High Suspicion",    int((df["Suspicion"] >= 0.5).sum()))
            c3.metric("📊 Avg QoE",           f"{df['QoE Score'].mean():.3f}")
            c4.metric("⏱️ Avg Latency",        f"{df['Latency(ms)'].mean():.0f} ms")

            st.markdown('<p class="section-title">User Status</p>', unsafe_allow_html=True)

            # ── Per-user cards ────────────────────────────────────────────
            for _, row in df.iterrows():
                sus   = row["Suspicion"]
                card  = "ucard alert" if sus >= 0.5 else "ucard"
                vid   = "🟢 ON" if row["Video"] else "🔴 OFF"
                sc    = sus_class(sus)
                badge = qoe_badge(row["QoE Label"])
                ago   = time_ago(row["Last Updated"])

                st.markdown(f"""
                <div class="{card}">
                  <span class="uname">{row['User']}</span>
                  {badge}
                  <span class="metric">BW&nbsp;<b>{row['Bandwidth(Mbps)']:.1f}</b>&nbsp;Mbps</span>
                  <span class="metric">Lat&nbsp;<b>{row['Latency(ms)']:.0f}</b>&nbsp;ms</span>
                  <span class="metric">Loss&nbsp;<b>{row['Pkt Loss(%)']:.1f}%</b></span>
                  <span class="metric">QoE&nbsp;<b>{row['QoE Score']:.3f}</b></span>
                  <span class="metric">Video&nbsp;{vid}</span>
                  <span class="{sc}">Sus&nbsp;{sus:.2f}</span>
                  <span class="metric" style="color:#475569">{ago}</span>
                  <div class="reason-txt">↳ {row['Reason']}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── Charts ───────────────────────────────────────────────────
            st.markdown('<p class="section-title">Charts</p>', unsafe_allow_html=True)
            ch1, ch2 = st.columns(2)

            with ch1:
                fig = px.bar(
                    df, x="User", y="Latency(ms)",
                    color="QoE Label",
                    color_discrete_map=QOE_COLORS,
                    title="Latency per User",
                    text_auto=".0f",
                )
                fig.update_layout(**THEME)
                st.plotly_chart(fig, use_container_width=True, key="chart_latency")

            with ch2:
                fig = px.bar(
                    df, x="User", y="Bandwidth(Mbps)",
                    color="QoE Label",
                    color_discrete_map=QOE_COLORS,
                    title="Bandwidth per User",
                    text_auto=".1f",
                )
                fig.update_layout(**THEME)
                st.plotly_chart(fig, use_container_width=True, key="chart_bandwidth")

            # Suspicion gauge
            fig_sus = go.Figure()
            for _, row in df.iterrows():
                s   = row["Suspicion"]
                col = "#ef4444" if s >= 0.6 else ("#fbbf24" if s >= 0.3 else "#4ade80")
                fig_sus.add_trace(go.Bar(
                    x=[row["User"]], y=[s],
                    name=row["User"],
                    marker_color=col,
                    text=[f"{s:.2f}"],
                    textposition="outside",
                ))
            fig_sus.add_hline(y=0.5, line_dash="dash", line_color="#ef4444",
                               annotation_text="High-suspicion threshold")
            fig_sus.update_layout(
                title="Suspicion Scores",
                yaxis_range=[0, 1.15],
                showlegend=False,
                **THEME,
            )
            st.plotly_chart(fig_sus, use_container_width=True, key="chart_suspicion")

            # ── Alert banner ──────────────────────────────────────────────
            top = df.iloc[0]
            if top["Suspicion"] >= 0.5:
                st.error(
                    f"🚨 **Most Suspicious:** {top['User']} "
                    f"(suspicion {top['Suspicion']:.2f}) — {top['Reason']}"
                )

    fetch.clear()       # force fresh fetch next iteration
    time.sleep(refresh)