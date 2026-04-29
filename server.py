"""
server.py — Central Flask API for Network QoE Monitoring
"""

import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Storage ─────────────────────────────────────────────
user_data: dict[str, dict] = {}
lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Suspicion Logic ─────────────────────────────────────
def compute_suspicion(qoe_label, video_on, qoe_score):
    if qoe_label == "GOOD" and not video_on:
        return 0.8, "Good network but video OFF → suspicious"
    elif qoe_label == "GOOD" and video_on:
        return 0.05, "Normal behaviour"
    elif qoe_label == "MODERATE" and not video_on:
        return 0.4, "Moderate network + video OFF"
    elif qoe_label == "MODERATE":
        return 0.15, "Moderate normal"
    else:
        return 0.05, "Poor network expected"


# ── Routes ─────────────────────────────────────────────

@app.route("/update", methods=["POST"])
def update():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON"}), 400

    username = payload.get("username", "").strip()
    if not username:
        return jsonify({"error": "username required"}), 400

    payload["server_received_at"] = _now()

    with lock:
        existing = user_data.get(username, {})

        # Preserve video state if not sent
        video_on = existing.get("video_on", True)

        payload["video_on"] = video_on

        # 🔥 Recompute suspicion HERE
        sus, reason = compute_suspicion(
            payload.get("qoe_label", "POOR"),
            video_on,
            payload.get("qoe_score", 0)
        )

        payload["suspicion_score"] = sus
        payload["reason"] = reason

        user_data[username] = payload

    return jsonify({"status": "ok"}), 200


@app.route("/update_video", methods=["POST"])
def update_video():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON"}), 400

    username = payload.get("username", "").strip()
    if not username:
        return jsonify({"error": "username required"}), 400

    video_on = bool(payload.get("video_on", True))

    with lock:
        if username not in user_data:
            user_data[username] = {
                "username": username,
                "video_on": video_on,
                "qoe_label": "POOR",
                "qoe_score": 0,
                "server_received_at": _now(),
            }

        else:
            user_data[username]["video_on"] = video_on

        # 🔥 Recompute suspicion AFTER video change
        qoe_label = user_data[username].get("qoe_label", "POOR")
        qoe_score = user_data[username].get("qoe_score", 0)

        sus, reason = compute_suspicion(qoe_label, video_on, qoe_score)

        user_data[username]["suspicion_score"] = sus
        user_data[username]["reason"] = reason
        user_data[username]["video_updated_at"] = _now()

    return jsonify({"status": "ok"}), 200


@app.route("/view", methods=["GET"])
def view():
    with lock:
        return jsonify(dict(user_data)), 200


@app.route("/health", methods=["GET"])
def health():
    with lock:
        return jsonify({
            "status": "running",
            "users": len(user_data),
            "time": _now()
        })


# ── Run ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Server running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)