import streamlit as st
import requests
import pandas as pd
import time

# =========================
# CONFIG
# =========================
SERVER_URL = "http://IP:5000/view"

st.set_page_config(page_title="Host Dashboard", layout="wide")

st.title("📊 AI Network Monitoring Dashboard")

# =========================
# AUTO REFRESH
# =========================
placeholder = st.empty()

while True:
    try:
        res = requests.get(SERVER_URL)
        data = res.json()
    except:
        st.error("⚠️ Cannot connect to server")
        time.sleep(5)
        continue

    if not data:
        st.warning("No data yet...")
        time.sleep(5)
        continue

    # =========================
    # CONVERT TO TABLE
    # =========================
    rows = []
    for user, info in data.items():
        rows.append({
            "Name": user,
            "QoE": info["qoe"],
            "Video": info["video"],
            "Suspicion": info["suspicion"],
            "Bandwidth": info["network"]["bandwidth"],
            "Latency": info["network"]["latency"],
            "Packet Loss": info["network"]["packet_loss"],
            "Reason": info["reason"]
        })

    df = pd.DataFrame(rows)

    # =========================
    # SORT BY SUSPICION
    # =========================
    df = df.sort_values(by="Suspicion", ascending=False)

    # =========================
    # DISPLAY
    # =========================
    with placeholder.container():

        st.subheader("🚨 Most Suspicious Users")
        st.dataframe(df, use_container_width=True)

        # =========================
        # HIGHLIGHT TOP USER
        # =========================
        top = df.iloc[0]

        st.metric(
            label=f"🔥 Highest Suspicion: {top['Name']}",
            value=top["Suspicion"],
            delta=top["Reason"]
        )

        # =========================
        # GRAPHS
        # =========================
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📶 Bandwidth")
            st.bar_chart(df.set_index("Name")["Bandwidth"])

        with col2:
            st.subheader("📡 Latency")
            st.bar_chart(df.set_index("Name")["Latency"])

    time.sleep(5)