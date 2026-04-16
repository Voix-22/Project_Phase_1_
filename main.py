import subprocess
import time
import random
import speedtest
from sklearn.tree import DecisionTreeClassifier

# =========================
# STEP 1: Train QoE Model
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
# NETWORK FUNCTIONS
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
# RL Q-TABLE
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
# AGENTS
# =========================

class NetworkAgent:
    def __init__(self):
        self.bandwidth = get_bandwidth()
        self.last_check = time.time()

    def run(self):
        if time.time() - self.last_check > 30:
            self.bandwidth = get_bandwidth()
            self.last_check = time.time()

        return {
            "bandwidth": self.bandwidth,
            "latency": get_latency(),
            "packet_loss": get_packet_loss()
        }

class QoEAgent:
    def run(self, data):
        return model.predict([[data["bandwidth"], data["latency"], data["packet_loss"]]])[0]

class BehaviorAgentRL:
    def run(self, qoe, video):
        return get_suspicion(qoe, video)

class TroubleshooterAgent:
    def run(self, qoe):
        if qoe == "POOR":
            return "⚠️ Poor network: Reduce quality / switch network"
        elif qoe == "MODERATE":
            return "⚠️ Moderate: Close background apps"
        return "✅ Network stable"

# =========================
# EXPLAINABILITY
# =========================

def explain(qoe, video):
    if qoe == "GOOD" and video == "OFF":
        return "Stable network but video OFF → Suspicious"
    elif qoe == "POOR":
        return "Network issue detected"
    return "Normal behavior"

# =========================
# SIMULATED USERS (HOST VIEW)
# =========================

users = [
    {"name": "Student A", "video": "OFF"},
    {"name": "Student B", "video": "ON"},
    {"name": "Student C", "video": "OFF"}
]

# =========================
# MAIN SYSTEM
# =========================

def main():
    network_agent = NetworkAgent()
    qoe_agent = QoEAgent()
    behavior_agent = BehaviorAgentRL()
    troubleshoot = TroubleshooterAgent()

    print("🚀 Host Monitoring Dashboard Started...\n")

    while True:
        print("\n================ HOST VIEW ================\n")

        for user in users:

            data = network_agent.run()
            qoe = qoe_agent.run(data)
            suspicion = behavior_agent.run(qoe, user["video"])
            reason = explain(qoe, user["video"])
            suggestion = troubleshoot.run(qoe)

            # Simulated reward (for RL learning)
            state = get_state(qoe, user["video"])
            reward = 1 if (qoe == "GOOD" and user["video"] == "OFF") else 0
            update_q(state, reward)

            print(f"👤 {user['name']}")
            print(f"📊 Network: {data}")
            print(f"🧠 QoE: {qoe}")
            print(f"🎥 Video: {user['video']}")
            print(f"🚨 Suspicion: {round(suspicion, 2)}")
            print(f"🧾 Reason: {reason}")
            print(f"💡 Suggestion: {suggestion}")
            print("----------------------------------")

        time.sleep(5)

# =========================

if __name__ == "__main__":
    main()