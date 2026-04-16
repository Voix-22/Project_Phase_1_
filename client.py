import subprocess
import time
import random
import speedtest
import requests
from sklearn.tree import DecisionTreeClassifier

# =========================
# CHANGE THIS
# =========================
SERVER_IP = "http://YOUR_IP:5000/update"
NAME = "Student_A"   # change per user
VIDEO_STATE = "OFF"  # change during demo

# =========================
# MODEL
# =========================

X = [
    [80, 5, 0.1],
    [60, 10, 0.2],
    [40, 20, 0.5],
    [20, 50, 2],
    [5, 100, 6]
]

y = ["GOOD", "GOOD", "MODERATE", "POOR", "POOR"]

model = DecisionTreeClassifier()
model.fit(X, y)

# =========================
# NETWORK
# =========================

def get_latency():
    try:
        output = subprocess.getoutput("ping -n 1 google.com")
        for line in output.split("\n"):
            if "time=" in line:
                return float(line.split("time=")[1].split("ms")[0])
    except:
        return random.randint(10, 50)
    return random.randint(10, 50)

def get_packet_loss():
    return round(random.uniform(0.1, 2.0), 2)

def get_bandwidth():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        return round(st.download() / 1e6, 2)
    except:
        return random.randint(10, 80)

# =========================
# RL TABLE
# =========================

q_table = {}

def get_state(qoe, video):
    return (qoe, video)

def get_suspicion(qoe, video):
    state = get_state(qoe, video)
    if state not in q_table:
        q_table[state] = 0.5
    return q_table[state]

def update_q(state, reward):
    lr = 0.1
    q_table[state] += lr * (reward - q_table[state])

# =========================
# MAIN LOOP
# =========================

while True:

    data = {
        "bandwidth": get_bandwidth(),
        "latency": get_latency(),
        "packet_loss": get_packet_loss()
    }

    qoe = model.predict([[data["bandwidth"], data["latency"], data["packet_loss"]]])[0]
    suspicion = get_suspicion(qoe, VIDEO_STATE)

    # RL update
    state = get_state(qoe, VIDEO_STATE)
    reward = 1 if (qoe == "GOOD" and VIDEO_STATE == "OFF") else 0
    update_q(state, reward)

    # Explanation
    if qoe == "GOOD" and VIDEO_STATE == "OFF":
        reason = "Stable network but video OFF"
    elif qoe == "POOR":
        reason = "Network issue"
    else:
        reason = "Normal"

    payload = {
        "name": NAME,
        "network": data,
        "qoe": qoe,
        "video": VIDEO_STATE,
        "suspicion": round(suspicion, 2),
        "reason": reason
    }

    try:
        requests.post(SERVER_IP, json=payload)
    except:
        print("⚠️ Could not send data")

    print(f"Sent data: {payload}")

    time.sleep(5)