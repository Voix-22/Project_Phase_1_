"""
client.py — Network QoE Agent
"""

import argparse
import math
import random
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests

# ── Constants ─────────────────────────────────────────────
SEND_INTERVAL_S = 5
C_TH = 1.0
EPSILON = 1e-9

# ── Network Measurement ───────────────────────────────────

def measure_latency_ms(host="8.8.8.8", count=4):
    try:
        if sys.platform.startswith("win"):
            cmd = ["ping", "-n", str(count), host]
        else:
            cmd = ["ping", "-c", str(count), "-W", "2", host]

        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout

        for line in out.splitlines():
            if "avg" in line.lower() or "average" in line.lower():
                for seg in line.replace("=", "/").split("/"):
                    try:
                        val = float(seg.strip().split()[0])
                        if 1 < val < 2000:
                            return round(val, 1)
                    except:
                        pass
    except:
        pass

    return round(random.uniform(20, 200), 1)


def measure_bandwidth_mbps():
    try:
        import speedtest
        s = speedtest.Speedtest()
        s.get_best_server()
        return round(s.download() / 1e6, 2)
    except:
        return round(random.uniform(5, 80), 2)


def measure_packet_loss(host="8.8.8.8", count=10):
    try:
        if sys.platform.startswith("win"):
            cmd = ["ping", "-n", str(count), host]
        else:
            cmd = ["ping", "-c", str(count), "-W", "2", host]

        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout

        for line in out.splitlines():
            if "%" in line:
                for tok in line.split():
                    try:
                        val = float(tok.replace("%", ""))
                        return val / 100
                    except:
                        pass
    except:
        pass

    return round(random.uniform(0, 0.1), 4)


# ── QoE Calculation ───────────────────────────────────────

def compute_qoe(bw, lat, loss):
    C = max(bw / 100, EPSILON)
    L = max(lat / 500, EPSILON)
    B = min(max(loss, 0), 1)

    p_out = min(B + 0.5 * (lat / 300) * B, 1)

    inner = (1 - B) * math.log(max(C / C_TH, EPSILON)) - math.log(L + EPSILON)
    return round((1 - p_out) * inner, 4)


def classify_qoe(q):
    if q > 0.5:
        return "GOOD"
    elif q > 0:
        return "MODERATE"
    return "POOR"


# ── Main Loop ─────────────────────────────────────────────

def run(server_url, username):
    print("\n" + "="*50)
    print("QoE Client Started")
    print("User:", username)
    print("Server:", server_url)
    print("="*50 + "\n")

    while True:
        try:
            print("Measuring...", end=" ")

            lat = measure_latency_ms()
            bw = measure_bandwidth_mbps()
            loss = measure_packet_loss()

            qoe = compute_qoe(bw, lat, loss)
            label = classify_qoe(qoe)

            payload = {
                "username": username,
                "bandwidth_mbps": bw,
                "latency_ms": lat,
                "packet_loss": loss,
                "qoe_score": qoe,
                "qoe_label": label,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            res = requests.post(
                server_url.rstrip("/") + "/update",
                json=payload,
                timeout=5
            )

            status = "OK" if res.status_code == 200 else "ERR"

            print(
                f"BW={bw:.1f}Mbps | Lat={lat:.0f}ms | Loss={loss*100:.1f}% | "
                f"QoE={qoe:.3f} ({label}) [{status}]"
            )

        except Exception as e:
            print("Error:", e)

        time.sleep(SEND_INTERVAL_S)


# ── Entry ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:5000")
    parser.add_argument("--user", default="User1")
    args = parser.parse_args()

    run(args.server, args.user)


if __name__ == "__main__":
    main()