# ADUSA Expert Connect — Full Quickstart Guide

## Requirements
- Python 3.6+ (check: `python3 --version`)
- Any modern browser (Chrome recommended for kiosk mode)
- Webex Calling license on your Webex account
- Call Queues created in Control Hub (one per department)

---

## Step 1 — Start the Server

```bash
python3 server.py
# Output:
# ═══════════════════════════════════════════════════
#   ADUSA Expert Connect Kiosk
#   http://localhost:8080
#   Press Ctrl+C to stop
# ═══════════════════════════════════════════════════
```

Custom port:
```bash
PORT=9090 python3 server.py
```

Expose on local network (for tablet/kiosk device on same WiFi):
```bash
python3 server.py
# Then open http://<YOUR-MACHINE-IP>:8080 on the kiosk device
```

---

## Step 2 — Get Your Webex Bearer Token

1. Open https://developer.webex.com in a separate browser tab
2. Sign in with your Webex account (must have Webex Calling license)
3. Top-right corner → your avatar → copy the **Bearer token**
4. Token is valid for **12 hours** (sufficient for demos/testing)

For longer-lived tokens, create a Bot at developer.webex.com/my-apps
(Bot tokens do not expire unless regenerated)

---

## Step 3 — Configure the Kiosk

When the kiosk loads, a Config modal appears:

1. Paste Bearer token into the token field
2. Enter Call Queue extensions (from Control Hub → Calling → Queues)
   - Format: E.164 (+3222XXXXXX) or internal extension (e.g. 5001)
3. Click **Apply & Launch**

To re-open Config at any time: Home screen → Select screen → ⚙ Config button

---

## Step 4 — Run in Full Kiosk Mode (Touchscreen)

```bash
# Linux/Chrome OS
google-chrome --kiosk --noerrdialogs --disable-infobars \
  --incognito http://localhost:8080

# macOS
open -a "Google Chrome" --args --kiosk http://localhost:8080

# Raspberry Pi (Chromium)
chromium-browser --kiosk --noerrdialogs http://localhost:8080
```

---

## Production: HTTPS (Required for Microphone on LAN IP)

localhost is treated as secure — mic works fine for demos.
For a real LAN/IP deployment:

### Option A — Caddy (easiest, single binary)
```bash
# Install: https://caddyserver.com/docs/install
caddy file-server --listen :443 --root /path/to/kiosk/folder
```

### Option B — Python + self-signed cert
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem \
  -out cert.pem -days 365 -nodes -subj '/CN=localhost'
python3 -c "
import ssl, http.server
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain('cert.pem','key.pem')
httpd = http.server.HTTPServer(('',443), http.server.SimpleHTTPRequestHandler)
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
httpd.serve_forever()
"
```

---

## Webex Control Hub — Call Queue Setup

For each department:
1. Control Hub → Calling → Customer Assist → Call Queues → Add
2. Name: e.g. "Nutrition Advisors"
3. Routing: Longest Idle (recommended) or Circular
4. Add specialist agents to the queue
5. Note the queue's main number/extension → paste into kiosk Config

---

## Demo Screens

| Screen | Trigger |
|--------|---------|
| Attract / Idle | Default, returns after 45s inactivity |
| Department Select | Tap "Get Started" |
| Pre-Call Confirm | Tap any department card |
| Active Call | Tap "Connect to Expert Now" |
| Post-Call Rating | Tap 📵 End Call button |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Mic not working | Serve over HTTPS (see above) or use localhost |
| Call fails silently | Check Bearer token is not expired (12h limit) |
| SDK loads but call errors | Confirm account has Webex Calling license |
| Queue unreachable | Verify DID format — use E.164 (+country code) |
| Blank screen | Check browser console — likely CDN load issue |
