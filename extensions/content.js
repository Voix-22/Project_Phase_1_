/**
 * content.js — Google Meet QoE Extension
 * =========================================
 * Detects the camera (video) button state in Google Meet by inspecting the
 * DOM, then POSTs the result to the central QoE server every 3 seconds.
 *
 * HOW IT WORKS
 * ─────────────
 * Google Meet renders the camera toggle as a <button> with:
 *   • data-tooltip containing "camera" / "Turn on camera" / "Turn off camera"
 *   • aria-label  containing similar text
 *   • aria-pressed="true"  when camera is ON
 *   • aria-pressed="false" when camera is OFF
 *
 * We probe multiple selector strategies so the extension stays robust across
 * minor DOM updates.
 *
 * CONFIGURATION
 * ─────────────
 * Edit SERVER_URL and USERNAME before loading the extension, OR use the
 * small floating UI panel that appears in Meet.
 */

// ── Configuration (edit these or use the floating panel) ────────────────────
let SERVER_URL = "http://localhost:5000";   // change to ngrok URL for remote
let USERNAME   = "MeetUser";               // set your name here
const POLL_MS  = 3000;                     // poll every 3 seconds

// ── Video-button detection ───────────────────────────────────────────────────

/**
 * Find the camera toggle button using several selectors to handle Meet UI
 * variations.
 * Returns the button element or null.
 */
function findCameraButton() {
  const strategies = [
    // aria-label based (most reliable)
    () => document.querySelector('[aria-label*="camera" i]'),
    () => document.querySelector('[aria-label*="Camera" i]'),
    // data-tooltip based
    () => document.querySelector('[data-tooltip*="camera" i]'),
    () => document.querySelector('[data-tooltip*="Camera" i]'),
    // jsname used internally by Meet (may change)
    () => document.querySelector('[jsname="BOHaEe"]'),
    // generic: any button whose accessible text includes "camera"
    () => {
      const buttons = document.querySelectorAll("button");
      for (const btn of buttons) {
        const label = (btn.getAttribute("aria-label") || "").toLowerCase();
        const title = (btn.getAttribute("title") || "").toLowerCase();
        if (label.includes("camera") || title.includes("camera")) {
          return btn;
        }
      }
      return null;
    },
  ];

  for (const fn of strategies) {
    try {
      const el = fn();
      if (el) return el;
    } catch (_) {}
  }
  return null;
}

/**
 * Determine whether the camera is currently ON.
 * Returns true (camera on) / false (camera off) / null (unknown).
 */
function isCameraOn() {
  const btn = findCameraButton();
  if (!btn) return null;

  // aria-pressed="true"  → camera is active (ON)
  // aria-pressed="false" → camera is muted (OFF)
  const pressed = btn.getAttribute("aria-pressed");
  if (pressed === "true")  return true;
  if (pressed === "false") return false;

  // Fallback: inspect aria-label text
  const label = (btn.getAttribute("aria-label") || "").toLowerCase();
  if (label.includes("turn on"))  return false;  // button says "turn ON" → currently off
  if (label.includes("turn off")) return true;   // button says "turn OFF" → currently on
  if (label.includes("unmute"))   return false;
  if (label.includes("mute"))     return true;

  // Fallback: inspect data-tooltip
  const tip = (btn.getAttribute("data-tooltip") || "").toLowerCase();
  if (tip.includes("turn on"))  return false;
  if (tip.includes("turn off")) return true;

  return null;   // could not determine
}

// ── Server communication ─────────────────────────────────────────────────────

async function postVideoState(videoOn) {
  try {
    const res = await fetch(`${SERVER_URL}/update_video`, {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({
        username: USERNAME,
        video_on: videoOn,
      }),
    });
    if (!res.ok) {
      console.warn(`[QoE] Server responded ${res.status}`);
    }
  } catch (err) {
    console.warn("[QoE] Could not reach server:", err.message);
  }
}

// ── Polling loop ─────────────────────────────────────────────────────────────

let lastState = null;   // avoid redundant POSTs when state unchanged
let pollTimer = null;

function poll() {
  const state = isCameraOn();

  if (state !== null && state !== lastState) {
    console.log(`[QoE] Camera changed → ${state ? "ON" : "OFF"}`);
    postVideoState(state);
    lastState = state;
  } else if (state === null) {
    // Meet not in call yet, or DOM not ready
    console.debug("[QoE] Camera button not found yet.");
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(poll, POLL_MS);
  poll(); // immediate first check
}

// ── Floating config panel ────────────────────────────────────────────────────

function createPanel() {
  const panel = document.createElement("div");
  panel.id = "qoe-panel";
  panel.style.cssText = `
    position: fixed;
    bottom: 80px;
    right: 16px;
    z-index: 99999;
    background: #0d1220;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 12px 16px;
    font-family: 'IBM Plex Mono', monospace, sans-serif;
    font-size: 12px;
    color: #94a3b8;
    width: 240px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.6);
    user-select: none;
  `;

  panel.innerHTML = `
    <div style="font-weight:700;color:#38bdf8;margin-bottom:8px;">📡 QoE Monitor</div>
    <label style="display:block;margin-bottom:4px;">Username
      <input id="qoe-user" value="${USERNAME}"
        style="display:block;width:100%;box-sizing:border-box;
               background:#080c14;border:1px solid #1e3a5f;
               color:#e2e8f0;border-radius:4px;padding:3px 6px;margin-top:2px;">
    </label>
    <label style="display:block;margin-bottom:6px;">Server URL
      <input id="qoe-server" value="${SERVER_URL}"
        style="display:block;width:100%;box-sizing:border-box;
               background:#080c14;border:1px solid #1e3a5f;
               color:#e2e8f0;border-radius:4px;padding:3px 6px;margin-top:2px;">
    </label>
    <button id="qoe-save"
      style="background:#0ea5e9;color:#fff;border:none;border-radius:4px;
             padding:4px 12px;cursor:pointer;font-size:11px;">Save & Start</button>
    <span id="qoe-status" style="margin-left:8px;color:#64748b;"></span>
  `;

  document.body.appendChild(panel);

  document.getElementById("qoe-save").addEventListener("click", () => {
    USERNAME   = document.getElementById("qoe-user").value.trim()   || USERNAME;
    SERVER_URL = document.getElementById("qoe-server").value.trim() || SERVER_URL;
    document.getElementById("qoe-status").textContent = "✓ Saved";
    setTimeout(() => {
      document.getElementById("qoe-status").textContent = "";
    }, 2000);
    startPolling();
  });
}

// ── Init ─────────────────────────────────────────────────────────────────────

(function init() {
  console.log("[QoE Extension] Loaded on", location.href);
  // Wait for Meet to render its toolbar
  const observer = new MutationObserver(() => {
    if (document.querySelector('button[aria-label]')) {
      observer.disconnect();
      createPanel();
      startPolling();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Fallback if DOM already ready
  if (document.querySelector('button[aria-label]')) {
    observer.disconnect();
    createPanel();
    startPolling();
  }
})();
