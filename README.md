# 📡 Real-Time Meeting Network QoE Monitor

Monitor network quality and detect suspicious behaviour during virtual meetings.
Supports a Chrome extension for **real** Google Meet video-state detection.

---

## File Structure

```
qoe_monitor/
├── server.py           ← Flask central API
├── client.py           ← Python network agent (per user)
├── dashboard.py        ← Streamlit host dashboard
├── requirements.txt
└── extension/
    ├── manifest.json   ← Chrome extension manifest (v3)
    └── content.js      ← Injected script for Google Meet
```

---

## Architecture

```
[Python Client A]──┐
[Python Client B]──┼──► Flask Server :5000 ◄── Streamlit Dashboard :8501
[Python Client C]──┘         ▲
[Chrome Extension] ──────────┘
                        (via ngrok public URL)
```

---

## Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2 — Start the Flask server

```bash
python server.py
```

Server listens on `http://0.0.0.0:5000`.

| Method | Path            | Purpose                         |
|--------|-----------------|---------------------------------|
| POST   | /update         | Receive full metrics (client)   |
| POST   | /update_video   | Receive video state (extension) |
| GET    | /view           | Return all users' data          |
| GET    | /health         | Server health check             |

---

## Step 3 — Expose server with ngrok (for remote clients)

```bash
# Install: https://ngrok.com/download
ngrok http 5000
```

Copy the `Forwarding` URL, e.g.:
```
https://abc123.ngrok-free.app
```

Share this URL with remote participants.

---

## Step 4 — Run the Streamlit dashboard

```bash
# Local server
streamlit run dashboard.py -- --server http://localhost:5000

# ngrok URL
streamlit run dashboard.py -- --server https://abc123.ngrok-free.app
```

Opens at **http://localhost:8501**

---

## Step 5 — Run Python client(s)

Each participant runs this on their own machine:

```bash
# Local test
python client.py --server http://localhost:5000 --user Alice

# Remote via ngrok
python client.py --server https://abc123.ngrok-free.app --user Bob
```

The client reports every **5 seconds** with:
- Bandwidth, latency, packet loss (real or simulated)
- QoE score + label (GOOD / MODERATE / POOR)
- Suspicion score + reason

> **Tip:** `speedtest-cli` is slow (~15s). If absent, the client auto-simulates
> realistic values instantly. For a real speed test, `pip install speedtest-cli`.

---

## Step 6 — Load the Chrome Extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder

The extension is now installed.

---

## Step 7 — Test with Google Meet

1. Open a Google Meet call: **https://meet.google.com/**
2. The extension injects a small **📡 QoE Monitor** panel (bottom-right of the tab)
3. In the panel:
   - Set your **username** (must match the name you use in the Python client)
   - Set the **Server URL** (use ngrok URL for remote)
   - Click **Save & Start**
4. Toggle your camera ON/OFF — the dashboard will update within 3 seconds

---

## QoE Formula

```
QoE = (1 - P_outage) × [ (1 - B) × ln(C / C_th) − ln(L) ]

  C        = bandwidth_mbps / 100     (normalised; max = 100 Mbps)
  L        = latency_ms     / 500     (normalised; worst = 500 ms)
  B        = packet_loss ∈ [0, 1]
  C_th     = 1.0                      (reference threshold)
  P_outage = min(B + 0.5 × lat_factor × B, 1)

Classification:
  QoE > 0.5  → GOOD
  QoE > 0    → MODERATE
  else       → POOR
```

---

## Suspicion Logic

| QoE Label | Video | Score  | Reason |
|-----------|-------|--------|--------|
| GOOD      | OFF   | 0.6–1.0 | Strong connectivity but video disabled — suspected hoarding |
| GOOD      | ON    | 0.05   | Normal |
| MODERATE  | OFF   | 0.40   | Mildly suspicious |
| MODERATE  | ON    | 0.15   | Acceptable |
| POOR      | any   | 0.05   | Expected; poor network |

---

## Simulating Multiple Users

Open 3 terminals and run:

```bash
# Terminal 1
python client.py --user Alice --server http://localhost:5000

# Terminal 2
python client.py --user Bob   --server http://localhost:5000

# Terminal 3
python client.py --user Carol --server http://localhost:5000
```

Load the extension in Chrome for a 4th "user" whose camera state is tracked live.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `speedtest-cli` hangs | It can take 30s; client falls back to simulation automatically |
| Extension can't reach server | Check ngrok URL is set in the panel; ensure server is running |
| Camera state not detected | Google Meet may have updated its DOM — open browser console and check `[QoE]` logs |
| Dashboard shows nothing | Wait for at least one client to send data; check server logs |
