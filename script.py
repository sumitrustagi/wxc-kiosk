
import zipfile, os

# ── All file contents ────────────────────────────────────────────────────────

README = """# ADUSA In-Store Expert Connect
## Powered by Webex Calling + Customer Assist

### Files in this package
| File | Purpose |
|------|---------|
| `kiosk.html` | Full kiosk UI — open in any browser |
| `server.py` | Zero-dependency Python web server (stdlib only) |
| `QUICKSTART.md` | Step-by-step launch & configuration guide |

---

## 60-Second Launch

```bash
# 1. Start the server
python3 server.py

# 2. Open in browser
open http://localhost:8080          # macOS
google-chrome http://localhost:8080 # Linux
# For kiosk/touchscreen mode:
google-chrome --kiosk --noerrdialogs --incognito http://localhost:8080
```

## Configure Webex Live Calling
1. Go to https://developer.webex.com — sign in
2. Copy your Bearer token (top-right of the page, valid 12h)
3. In the kiosk Config modal: paste token + enter queue DIDs
4. Click **Apply & Launch**

## Architecture
```
[Kiosk Browser] → Webex Web Calling SDK (@webex/calling CDN)
                    │  serviceData: { indicator: 'calling' }
                    │  credentials: { access_token: BEARER_TOKEN }
                    ▼
              Webex Calling Cloud
                    │
                    ▼
          Customer Assist Call Queue
                    │
                    ▼
        Remote Expert on Webex App
```

## Webex SDK Scopes (auto-included in personal token if you have Webex Calling)
- spark:webrtc_calling
- spark:calls_read / spark:calls_write
- spark:xsi

## Production Checklist
- [ ] Serve over HTTPS (required for mic on non-localhost)
- [ ] Use a dedicated Webex Calling service account (not personal token)
- [ ] Create one Call Queue per department in Control Hub
- [ ] Set 45s inactivity timeout (already built-in)
- [ ] Enable Chrome kiosk mode on touchscreen hardware
"""

QUICKSTART = """# ADUSA Expert Connect — Full Quickstart Guide

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
google-chrome --kiosk --noerrdialogs --disable-infobars \\
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
openssl req -x509 -newkey rsa:4096 -keyout key.pem \\
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
"""

SERVER_PY = '''#!/usr/bin/env python3
"""
ADUSA Expert Connect — Kiosk Server
Zero dependencies — Python 3 stdlib only

Usage:
    python3 server.py            # serves on port 8080
    PORT=9090 python3 server.py  # custom port
"""
import http.server, os, sys

PORT      = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class KioskHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIRECTORY, **kw)

    def end_headers(self):
        # Required for Webex SDK SharedArrayBuffer + mic access
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Opener-Policy",   "same-origin")
        super().end_headers()

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.path = '/kiosk.html'
        super().do_GET()

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()}  {fmt % args}")

if __name__ == '__main__':
    with http.server.HTTPServer(('', PORT), KioskHandler) as httpd:
        print(f"\\n{'═'*51}")
        print(f"  ADUSA Expert Connect Kiosk Server")
        print(f"  http://localhost:{PORT}")
        print(f"  Network: http://{_get_lan_ip()}:{PORT}")
        print(f"  Press Ctrl+C to stop")
        print(f"{'═'*51}\\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nServer stopped.")
            sys.exit(0)

def _get_lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"
'''

KIOSK_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>ADUSA In-Store Expert Connect</title>
  <script src="https://unpkg.com/@webex/calling/dist/webex-calling.min.js"></script>
  <style>
    :root{
      --red:#D22630;--dark:#1A1A2E;--accent:#0F3460;
      --green:#00B388;--yellow:#F5A623;
      --light:#F0F4F8;--muted:#94A3B8;
      --card:rgba(255,255,255,0.07);--border:rgba(255,255,255,0.12);
      --shadow:0 20px 60px rgba(0,0,0,0.5);
    }
    *{margin:0;padding:0;box-sizing:border-box;}
    body{font-family:\'Segoe UI\',system-ui,sans-serif;background:var(--dark);
      color:var(--light);height:100vh;width:100vw;overflow:hidden;
      display:flex;flex-direction:column;}
    .screen{display:none;flex-direction:column;height:100vh;width:100vw;}
    .screen.active{display:flex;}

    /* ── ATTRACT ── */
    #s-attract{background:linear-gradient(145deg,#0F1B35,#1A2A4A 50%,#0F1B35);
      align-items:center;justify-content:center;position:relative;overflow:hidden;}
    #s-attract::before{content:\'\';position:absolute;inset:0;
      background:radial-gradient(ellipse 80% 60% at 50% 50%,rgba(210,38,48,.12),transparent 70%);}
    .a-logo{display:flex;flex-direction:column;align-items:center;gap:16px;z-index:1;}
    .a-icon{width:120px;height:120px;background:linear-gradient(135deg,var(--red),#FF6B6B);
      border-radius:28px;display:flex;align-items:center;justify-content:center;
      font-size:56px;box-shadow:0 0 60px rgba(210,38,48,.5);}
    .a-title{font-size:52px;font-weight:800;
      background:linear-gradient(135deg,#fff 30%,#FFAAAA);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .a-sub{font-size:20px;color:var(--muted);}
    .a-tag{font-size:26px;color:var(--green);letter-spacing:2px;
      text-transform:uppercase;margin-top:20px;z-index:1;}
    .tap-btn{margin-top:56px;z-index:1;
      background:linear-gradient(135deg,var(--red),#FF4757);
      border:none;border-radius:60px;padding:28px 72px;
      font-size:26px;font-weight:700;color:#fff;cursor:pointer;
      box-shadow:0 8px 40px rgba(210,38,48,.55);
      animation:pulse 2.5s infinite;}
    @keyframes pulse{0%,100%{box-shadow:0 8px 40px rgba(210,38,48,.55)}
      50%{box-shadow:0 8px 60px rgba(210,38,48,.85)}}
    .stores{position:absolute;bottom:28px;left:50%;transform:translateX(-50%);
      display:flex;gap:20px;z-index:1;}
    .pill{background:rgba(255,255,255,.08);border:1px solid var(--border);
      border-radius:30px;padding:8px 20px;font-size:13px;color:var(--muted);}
    .token-badge{position:absolute;top:20px;right:20px;z-index:10;
      padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;
      display:flex;align-items:center;gap:8px;}
    .tb-ok  {background:rgba(0,179,136,.15);border:1px solid rgba(0,179,136,.35);color:var(--green);}
    .tb-warn{background:rgba(245,166,35,.15);border:1px solid rgba(245,166,35,.35);color:var(--yellow);}

    /* ── HEADER ── */
    .hdr{display:flex;align-items:center;justify-content:space-between;
      padding:18px 40px;background:rgba(10,15,30,.95);
      border-bottom:1px solid var(--border);backdrop-filter:blur(12px);flex-shrink:0;}
    .hdr-logo{display:flex;align-items:center;gap:14px;}
    .hdr-icon{width:44px;height:44px;background:linear-gradient(135deg,var(--red),#FF6B6B);
      border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;}
    .hdr-brand{font-size:20px;font-weight:700;}
    .hdr-brand span{color:var(--red);}
    .hdr-r{display:flex;align-items:center;gap:14px;}
    .dot{width:10px;height:10px;border-radius:50%;background:var(--green);
      box-shadow:0 0 8px var(--green);animation:blink 2s infinite;}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
    .dot-txt{font-size:14px;color:var(--green);font-weight:500;}
    .clock{font-size:15px;color:var(--muted);}
    .btn-sm{background:rgba(255,255,255,.08);border:1px solid var(--border);
      border-radius:10px;padding:8px 18px;color:var(--light);font-size:14px;cursor:pointer;}
    .btn-sm:hover{background:rgba(255,255,255,.15);}
    .btn-cfg{border-color:rgba(0,179,136,.4);color:var(--green);}

    /* ── SELECT ── */
    #s-select{background:linear-gradient(160deg,#0D1628,#1A2540);}
    .sel-body{flex:1;overflow-y:auto;padding:32px 40px;}
    .sel-greet{text-align:center;margin-bottom:30px;}
    .sel-greet h2{font-size:34px;font-weight:700;}
    .sel-greet p{font-size:17px;color:var(--muted);margin-top:8px;}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;
      max-width:1100px;margin:0 auto;}
    .card{background:var(--card);border:1px solid var(--border);border-radius:22px;
      padding:32px 24px;display:flex;flex-direction:column;align-items:center;gap:14px;
      cursor:pointer;transition:all .2s;position:relative;overflow:hidden;}
    .card::before{content:\'\';position:absolute;inset:0;
      background:linear-gradient(135deg,var(--dc,#444),transparent 80%);
      opacity:0;transition:opacity .3s;border-radius:22px;}
    .card:hover{transform:translateY(-4px);box-shadow:var(--shadow);border-color:var(--dc,#888);}
    .card:hover::before{opacity:.12;}
    .card-icon{width:76px;height:76px;border-radius:20px;font-size:36px;
      display:flex;align-items:center;justify-content:center;
      background:linear-gradient(135deg,var(--dc,#555),color-mix(in srgb,var(--dc,#555) 60%,#000));
      box-shadow:0 8px 24px rgba(0,0,0,.35);}
    .card-name{font-size:19px;font-weight:700;text-align:center;}
    .card-desc{font-size:13px;color:var(--muted);text-align:center;line-height:1.5;}
    .badge-ok{background:rgba(0,179,136,.15);border:1px solid rgba(0,179,136,.3);
      border-radius:20px;padding:5px 14px;font-size:13px;color:var(--green);font-weight:600;}
    .badge-busy{background:rgba(245,166,35,.15);border:1px solid rgba(245,166,35,.3);
      border-radius:20px;padding:5px 14px;font-size:13px;color:var(--yellow);font-weight:600;}
    .sbar{background:rgba(5,10,20,.95);border-top:1px solid var(--border);
      padding:10px 40px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
    .sb{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);}
    .sb span{color:var(--light);font-weight:500;}

    /* ── PRE-CALL ── */
    #s-pre{background:linear-gradient(160deg,#0D1628,#1A2540);
      align-items:center;justify-content:center;}
    .pre-card{background:rgba(255,255,255,.06);border:1px solid var(--border);
      border-radius:28px;padding:48px 56px;max-width:640px;width:90%;
      display:flex;flex-direction:column;align-items:center;gap:22px;box-shadow:var(--shadow);}
    .pre-icon{width:100px;height:100px;border-radius:24px;
      display:flex;align-items:center;justify-content:center;font-size:50px;}
    .pre-title{font-size:30px;font-weight:700;text-align:center;}
    .pre-sub{font-size:16px;color:var(--muted);text-align:center;line-height:1.6;}
    .pre-info{background:rgba(0,179,136,.1);border:1px solid rgba(0,179,136,.25);
      border-radius:14px;padding:16px 24px;width:100%;
      display:flex;align-items:center;gap:14px;font-size:14px;color:var(--green);line-height:1.5;}
    .btn-call{width:100%;padding:22px;
      background:linear-gradient(135deg,var(--green),#009966);
      border:none;border-radius:16px;font-size:22px;font-weight:700;color:#fff;cursor:pointer;
      display:flex;align-items:center;justify-content:center;gap:12px;
      box-shadow:0 8px 30px rgba(0,179,136,.4);transition:all .2s;}
    .btn-call:hover{transform:translateY(-2px);}
    .btn-back{background:none;border:1px solid var(--border);border-radius:12px;
      padding:14px 32px;color:var(--muted);font-size:16px;cursor:pointer;}
    .btn-back:hover{border-color:#fff;color:#fff;}

    /* ── CALL ── */
    #s-call{background:linear-gradient(160deg,#060D1A,#0D1628);}
    .call-body{flex:1;display:flex;align-items:center;justify-content:center;padding:28px;}
    .call-layout{display:grid;grid-template-columns:1fr 320px;gap:22px;
      max-width:1200px;width:100%;}
    .vid{background:rgba(255,255,255,.04);border:1px solid var(--border);
      border-radius:24px;aspect-ratio:16/9;display:flex;flex-direction:column;
      align-items:center;justify-content:center;gap:18px;position:relative;overflow:hidden;}
    .vid-av{width:110px;height:110px;border-radius:50%;font-size:52px;
      background:linear-gradient(135deg,var(--accent),var(--red));
      display:flex;align-items:center;justify-content:center;
      border:4px solid rgba(0,179,136,.4);box-shadow:0 0 40px rgba(0,179,136,.3);}
    .vid-status{font-size:22px;font-weight:600;color:var(--green);}
    .vid-sub{font-size:15px;color:var(--muted);}
    .vid-timer{position:absolute;top:16px;right:20px;background:rgba(0,0,0,.6);
      border-radius:20px;padding:6px 16px;font-size:18px;font-weight:700;}
    .vid-qual{position:absolute;top:16px;left:20px;display:flex;align-items:center;gap:8px;
      background:rgba(0,0,0,.6);border-radius:20px;padding:6px 14px;
      font-size:13px;color:var(--green);}
    .vid-self{position:absolute;bottom:16px;right:16px;width:130px;aspect-ratio:16/9;
      background:rgba(30,40,60,.9);border-radius:12px;border:2px solid var(--border);
      display:flex;align-items:center;justify-content:center;font-size:26px;}
    .dots span{display:inline-block;width:8px;height:8px;
      background:var(--green);border-radius:50%;margin:0 3px;
      animation:bounce 1.4s infinite;}
    .dots span:nth-child(2){animation-delay:.2s}
    .dots span:nth-child(3){animation-delay:.4s}
    @keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
    .ctrl{display:flex;gap:12px;justify-content:center;margin-top:14px;}
    .cb{width:62px;height:62px;border-radius:50%;border:2px solid var(--border);
      background:rgba(255,255,255,.07);display:flex;align-items:center;
      justify-content:center;font-size:22px;cursor:pointer;transition:all .2s;}
    .cb:hover{background:rgba(255,255,255,.15);transform:scale(1.1);}
    .cb.muted{border-color:var(--red);background:rgba(210,38,48,.2);}
    .cb.end{width:76px;height:76px;font-size:28px;
      background:linear-gradient(135deg,var(--red),#FF4757);border:none;
      box-shadow:0 8px 24px rgba(210,38,48,.5);}
    .cb.end:hover{box-shadow:0 12px 36px rgba(210,38,48,.7);transform:scale(1.1);}
    .sidebar{display:flex;flex-direction:column;gap:14px;}
    .scard{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:22px;}
    .slabel{font-size:12px;color:var(--muted);text-transform:uppercase;
      letter-spacing:1px;margin-bottom:12px;}
    .srow{display:flex;align-items:center;gap:12px;}
    .sav{width:50px;height:50px;border-radius:14px;font-size:22px;flex-shrink:0;
      background:linear-gradient(135deg,var(--accent),var(--red));
      display:flex;align-items:center;justify-content:center;}
    .sname{font-size:17px;font-weight:700;}
    .srole{font-size:13px;color:var(--muted);}
    .sverif{display:inline-flex;align-items:center;gap:6px;margin-top:10px;
      background:rgba(0,179,136,.15);border:1px solid rgba(0,179,136,.3);
      border-radius:20px;padding:5px 12px;font-size:12px;color:var(--green);font-weight:600;}
    .tscript{height:150px;overflow-y:auto;font-size:14px;line-height:1.7;}
    .ta{color:var(--green);font-weight:600;}
    .ts{color:#87CEEB;font-weight:600;}
    .meta{background:var(--card);border:1px solid var(--border);border-radius:14px;
      padding:14px;font-size:13px;color:var(--muted);line-height:1.7;}

    /* ── POST-CALL ── */
    #s-post{background:linear-gradient(160deg,#0D1628,#1A2540);
      align-items:center;justify-content:center;}
    .post-card{background:var(--card);border:1px solid var(--border);
      border-radius:28px;padding:52px 60px;max-width:620px;width:90%;
      display:flex;flex-direction:column;align-items:center;gap:22px;box-shadow:var(--shadow);}
    .post-icon{font-size:72px;}
    .post-title{font-size:32px;font-weight:800;text-align:center;}
    .post-sub{font-size:17px;color:var(--muted);text-align:center;line-height:1.6;}
    .stars{display:flex;gap:14px;margin:8px 0;}
    .star{width:66px;height:66px;border-radius:16px;font-size:30px;
      border:2px solid var(--border);background:var(--card);cursor:pointer;transition:all .2s;}
    .star:hover,.star.sel{border-color:var(--yellow);
      background:rgba(245,166,35,.15);transform:scale(1.15);}
    .btn-home2{width:100%;padding:20px;background:linear-gradient(135deg,var(--red),#FF4757);
      border:none;border-radius:16px;font-size:20px;font-weight:700;
      color:#fff;cursor:pointer;box-shadow:0 8px 30px rgba(210,38,48,.4);}
    .post-foot{font-size:13px;color:var(--muted);text-align:center;}

    /* ── OVERLAY ── */
    #overlay{display:none;position:fixed;inset:0;z-index:999;
      background:rgba(5,10,20,.92);backdrop-filter:blur(8px);
      align-items:center;justify-content:center;flex-direction:column;gap:20px;}
    #overlay.on{display:flex;}
    .spin{width:60px;height:60px;border-radius:50%;
      border:4px solid rgba(0,179,136,.2);border-top-color:var(--green);
      animation:spin .8s linear infinite;}
    @keyframes spin{to{transform:rotate(360deg)}}
    .spin-txt{font-size:18px;color:var(--green);}

    /* ── CONFIG MODAL ── */
    #cfg-modal{display:none;position:fixed;inset:0;z-index:1000;
      background:rgba(5,10,20,.96);backdrop-filter:blur(12px);
      align-items:center;justify-content:center;}
    #cfg-modal.on{display:flex;}
    .cfg-card{background:#1A2540;border:1px solid var(--border);border-radius:24px;
      padding:44px 52px;max-width:680px;width:90%;
      display:flex;flex-direction:column;gap:20px;box-shadow:var(--shadow);}
    .cfg-card h2{font-size:26px;font-weight:700;}
    .cfg-card p{font-size:15px;color:var(--muted);line-height:1.6;}
    .hint{background:rgba(0,179,136,.08);border:1px solid rgba(0,179,136,.25);
      border-radius:12px;padding:14px 18px;font-size:13px;
      color:var(--green);line-height:1.7;}
    .hint code{background:rgba(0,0,0,.3);padding:2px 6px;border-radius:4px;font-family:monospace;}
    .lbl{font-size:13px;color:var(--muted);display:block;margin-bottom:6px;}
    .tok-inp{width:100%;background:rgba(255,255,255,.06);border:1px solid var(--border);
      border-radius:12px;padding:16px 18px;color:var(--light);font-size:14px;
      font-family:monospace;resize:vertical;min-height:80px;}
    .tok-inp:focus{outline:none;border-color:var(--green);}
    .q-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
    .q-inp{background:rgba(255,255,255,.06);border:1px solid var(--border);
      border-radius:10px;padding:12px 14px;color:var(--light);
      font-size:14px;font-family:monospace;}
    .q-inp:focus{outline:none;border-color:var(--green);}
    .btn-apply{background:linear-gradient(135deg,var(--green),#009966);
      border:none;border-radius:12px;padding:14px;color:#fff;
      font-size:16px;font-weight:700;cursor:pointer;width:100%;}
    .btn-skip{background:none;border:1px solid var(--border);border-radius:12px;
      padding:12px;color:var(--muted);font-size:15px;cursor:pointer;width:100%;}
    ::-webkit-scrollbar{width:6px;}
    ::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:3px;}
  </style>
</head>
<body>

<!-- ══ CONFIG MODAL ════════════════════════════════════════════════ -->
<div id="cfg-modal" class="on">
  <div class="cfg-card">
    <h2>⚙️ Webex Configuration</h2>
    <p>Paste your <strong>Personal Bearer Token</strong> from
      <code>developer.webex.com</code> and your
      <strong>Call Queue extensions</strong> from Control Hub to enable live calls.
      Or skip to run in demo simulation mode.</p>
    <div class="hint">
      🔑 Get token: <strong>developer.webex.com</strong> → sign in → copy Bearer token
      (top-right). Valid <strong>12 hours</strong>.<br>
      📞 Queue extension = the DID/extension of your Webex Customer Assist
      Call Queue in Control Hub.<br>
      💡 Requires: Webex Calling license + <code>spark:webrtc_calling</code> scope
      (included automatically in personal tokens).
    </div>
    <div>
      <label class="lbl">Webex Personal Access Token (Bearer)</label>
      <textarea id="inp-tok" class="tok-inp"
        placeholder="Paste Bearer token here…"></textarea>
    </div>
    <div>
      <label class="lbl">Call Queue Destinations — per department (E.164 or extension)</label>
      <div class="q-grid">
        <input class="q-inp" id="q-nutrition"   placeholder="🥦 Nutrition queue DID/ext"/>
        <input class="q-inp" id="q-pharmacy"    placeholder="💊 Pharmacy queue DID/ext"/>
        <input class="q-inp" id="q-electronics" placeholder="📱 Electronics queue DID/ext"/>
        <input class="q-inp" id="q-wine"        placeholder="🍷 Wine & Spirits DID/ext"/>
        <input class="q-inp" id="q-floral"      placeholder="💐 Floral DID/ext"/>
        <input class="q-inp" id="q-manager"     placeholder="🏪 Store Manager DID/ext"/>
      </div>
    </div>
    <button class="btn-apply" onclick="applyConfig()">✅ Apply & Launch Kiosk</button>
    <button class="btn-skip"  onclick="skipConfig()">▶ Demo Mode (no real calls)</button>
  </div>
</div>

<!-- ══ SCREEN 1 — ATTRACT ══════════════════════════════════════════ -->
<div id="s-attract" class="screen active">
  <div id="tbadge" class="token-badge tb-warn">⚠ Demo Mode</div>
  <div class="a-logo">
    <div class="a-icon">🛒</div>
    <div>
      <div class="a-title">Expert Connect</div>
      <div class="a-sub">Powered by Webex Calling · Customer Assist</div>
    </div>
    <div class="a-tag">🎙 Talk to a Specialist Instantly</div>
    <button class="tap-btn" onclick="goTo(\'s-select\')">👆 Tap to Get Started</button>
  </div>
  <div class="stores">
    <div class="pill">🏪 Stop &amp; Shop</div>
    <div class="pill">🛒 Giant Food</div>
    <div class="pill">🌿 Hannaford</div>
    <div class="pill">🦁 Food Lion</div>
    <div class="pill">🌻 Giant Martin\'s</div>
  </div>
</div>

<!-- ══ SCREEN 2 — SELECT ═══════════════════════════════════════════ -->
<div id="s-select" class="screen">
  <div class="hdr">
    <div class="hdr-logo">
      <div class="hdr-icon">🛒</div>
      <div class="hdr-brand">ADUSA <span>Expert Connect</span></div>
    </div>
    <div class="hdr-r">
      <div class="dot"></div>
      <div class="dot-txt">Specialists Online</div>
      <div class="clock" id="clock"></div>
      <button class="btn-sm" onclick="goTo(\'s-attract\')">🏠 Home</button>
      <button class="btn-sm btn-cfg"
        onclick="document.getElementById(\'cfg-modal\').classList.add(\'on\')">⚙ Config</button>
    </div>
  </div>
  <div class="sel-body">
    <div class="sel-greet">
      <h2>👋 How Can We Help You Today?</h2>
      <p>Select a department to connect with a live expert — no wait, no app needed.</p>
    </div>
    <div class="grid">
      <div class="card" style="--dc:#00B388"
        onclick="pick(\'Nutrition Advisor\',\'🥦\',\'nutrition\',\'00B388\',\'Dietary guidance, meal planning &amp; allergen advice.\')">
        <div class="card-icon">🥦</div>
        <div class="card-name">Nutrition Advisor</div>
        <div class="card-desc">Dietary guidance, meal planning, health labels &amp; allergen advice</div>
        <div class="badge-ok">⚡ Available Now</div>
      </div>
      <div class="card" style="--dc:#4A90E2"
        onclick="pick(\'Pharmacy Consultant\',\'💊\',\'pharmacy\',\'4A90E2\',\'Licensed pharmacist for medication &amp; wellness questions.\')">
        <div class="card-icon">💊</div>
        <div class="card-name">Pharmacy Consultant</div>
        <div class="card-desc">Medication questions, OTC recommendations &amp; drug interactions</div>
        <div class="badge-ok">⚡ Available Now</div>
      </div>
      <div class="card" style="--dc:#F5A623"
        onclick="pick(\'Electronics Expert\',\'📱\',\'electronics\',\'F5A623\',\'Devices, smart home, specs &amp; setup advice.\')">
        <div class="card-icon">📱</div>
        <div class="card-name">Electronics Expert</div>
        <div class="card-desc">Devices, smart home, specs comparison &amp; setup advice</div>
        <div class="badge-busy">~2 min wait</div>
      </div>
      <div class="card" style="--dc:#9B59B6"
        onclick="pick(\'Wine &amp; Spirits Sommelier\',\'🍷\',\'wine\',\'9B59B6\',\'Pairing recommendations &amp; occasion picks.\')">
        <div class="card-icon">🍷</div>
        <div class="card-name">Wine &amp; Spirits</div>
        <div class="card-desc">Pairing recommendations, regional varietals &amp; occasion picks</div>
        <div class="badge-ok">⚡ Available Now</div>
      </div>
      <div class="card" style="--dc:#FF6B9D"
        onclick="pick(\'Floral Designer\',\'💐\',\'floral\',\'FF6B9D\',\'Arrangements, events &amp; gift planning.\')">
        <div class="card-icon">💐</div>
        <div class="card-name">Floral Designer</div>
        <div class="card-desc">Arrangements, seasonal flowers, wedding &amp; event planning</div>
        <div class="badge-ok">⚡ Available Now</div>
      </div>
      <div class="card" style="--dc:#D22630"
        onclick="pick(\'Store Manager\',\'🏪\',\'manager\',\'D22630\',\'Feedback, loyalty programs &amp; store policies.\')">
        <div class="card-icon">🏪</div>
        <div class="card-name">Store Manager</div>
        <div class="card-desc">Store feedback, complaints, loyalty programs &amp; policies</div>
        <div class="badge-ok">⚡ Available Now</div>
      </div>
    </div>
  </div>
  <div class="sbar">
    <div class="sb">📍 Store #4721 — Machelen, BE</div>
    <div class="sb">🔒 Encrypted via <span>Webex Calling</span></div>
    <div class="sb">🕒 <span id="sbar-t"></span></div>
    <div class="sb" id="sb-mode">🟡 <span>Demo Mode</span></div>
  </div>
</div>

<!-- ══ SCREEN 3 — PRE-CALL ═════════════════════════════════════════ -->
<div id="s-pre" class="screen">
  <div class="hdr">
    <div class="hdr-logo">
      <div class="hdr-icon">🛒</div>
      <div class="hdr-brand">ADUSA <span>Expert Connect</span></div>
    </div>
    <div class="hdr-r">
      <div class="dot"></div>
      <div class="dot-txt">Ready to Connect</div>
      <button class="btn-sm" onclick="goTo(\'s-select\')">← Back</button>
    </div>
  </div>
  <div style="flex:1;display:flex;align-items:center;justify-content:center;padding:32px">
    <div class="pre-card">
      <div class="pre-icon" id="pre-icon">🥦</div>
      <div class="pre-title" id="pre-title">Connect to Expert</div>
      <div class="pre-sub"   id="pre-sub">Expert description</div>
      <div class="pre-info">
        <span style="font-size:24px">🔒</span>
        <span>Call is <strong>encrypted end-to-end</strong> via Webex Calling (SRTP + TLS).
        No app install — connect instantly from this kiosk.</span>
      </div>
      <audio id="audio" autoplay></audio>
      <button class="btn-call" onclick="startCall()">📞 Connect to Expert Now</button>
      <button class="btn-back" onclick="goTo(\'s-select\')">Cancel — Go Back</button>
    </div>
  </div>
</div>

<!-- ══ SCREEN 4 — CALL ═════════════════════════════════════════════ -->
<div id="s-call" class="screen">
  <div class="hdr">
    <div class="hdr-logo">
      <div class="hdr-icon">🛒</div>
      <div class="hdr-brand">ADUSA <span>Expert Connect</span></div>
    </div>
    <div class="hdr-r">
      <div class="dot" style="background:#FF6B6B;box-shadow:0 0 8px #FF6B6B"></div>
      <div class="dot-txt" style="color:#FF6B6B" id="call-status">🔴 Connecting…</div>
    </div>
  </div>
  <div class="call-body">
    <div class="call-layout">
      <div style="display:flex;flex-direction:column;gap:14px">
        <div class="vid">
          <div class="vid-qual">📶 HD Audio</div>
          <div class="vid-timer" id="timer">0:00</div>
          <div class="vid-av" id="call-av">🥦</div>
          <div class="vid-status" id="call-con">Connecting to Expert…</div>
          <div class="dots" id="dots"><span></span><span></span><span></span></div>
          <div class="vid-sub" id="call-qlabel">Queue</div>
          <div class="vid-self">🧑</div>
        </div>
        <div class="ctrl">
          <div class="cb" id="btn-mute" onclick="toggleMute()">🎤</div>
          <div class="cb">🔊</div>
          <div class="cb end" onclick="endCall()">📵</div>
          <div class="cb">💬</div>
          <div class="cb">ℹ️</div>
        </div>
      </div>
      <div class="sidebar">
        <div class="scard">
          <div class="slabel">Connected Specialist</div>
          <div class="srow">
            <div class="sav" id="s-av">🥦</div>
            <div>
              <div class="sname" id="s-name">Advisor</div>
              <div class="srole">ADUSA Expert Network</div>
            </div>
          </div>
          <div class="sverif">✅ Webex Verified</div>
        </div>
        <div class="scard">
          <div class="slabel">💬 Live Transcript (AI)</div>
          <div class="tscript" id="tscript">
            <em style="color:var(--muted)">Waiting for connection…</em>
          </div>
        </div>
        <div class="meta">
          📋 <strong style="color:#fff">Queue:</strong> <span id="s-queue">—</span><br>
          🔐 <strong style="color:#fff">Encryption:</strong> SRTP + TLS<br>
          📡 <strong style="color:#fff">Codec:</strong> Opus 48kHz<br>
          🏪 <strong style="color:#fff">Store:</strong> #4721 Machelen
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══ SCREEN 5 — POST-CALL ════════════════════════════════════════ -->
<div id="s-post" class="screen">
  <div class="post-card">
    <div class="post-icon">✅</div>
    <div class="post-title">Call Ended — Thank You!</div>
    <div class="post-sub">Your call with the
      <strong id="post-dept">Expert</strong> has ended.<br>
      How was your experience?</div>
    <div style="text-align:center">
      <p style="color:var(--muted);margin-bottom:12px;font-size:15px">Rate your experience:</p>
      <div class="stars">
        <button class="star" onclick="rate(this)">😞</button>
        <button class="star" onclick="rate(this)">😐</button>
        <button class="star" onclick="rate(this)">🙂</button>
        <button class="star" onclick="rate(this)">😊</button>
        <button class="star" onclick="rate(this)">🤩</button>
      </div>
    </div>
    <button class="btn-home2" onclick="goTo(\'s-attract\')">🏠 Return to Home Screen</button>
    <div class="post-foot">Call log saved · Webex Customer Assist · ADUSA Expert Network</div>
  </div>
</div>

<!-- ══ SPINNER OVERLAY ═════════════════════════════════════════════ -->
<div id="overlay">
  <div class="spin"></div>
  <div class="spin-txt" id="overlay-txt">Initializing…</div>
</div>

<script>
// ── STATE ────────────────────────────────────────────────────────
const S={
  token:null,demo:true,
  dept:null,icon:null,key:null,
  calling:null,activeCall:null,
  t0:null,tiv:null,muted:false,
  q:{nutrition:\'\',pharmacy:\'\',electronics:\'\',wine:\'\',floral:\'\',manager:\'\'}
};

// ── CONFIG ───────────────────────────────────────────────────────
function applyConfig(){
  const tok=document.getElementById(\'inp-tok\').value.trim();
  if(tok.length>20){
    S.token=tok; S.demo=false;
    [\'nutrition\',\'pharmacy\',\'electronics\',\'wine\',\'floral\',\'manager\'].forEach(k=>{
      S.q[k]=document.getElementById(\'q-\'+k).value.trim();
    });
    setBadge(\'ok\',\'🟢 Live — Webex Calling\');
    document.getElementById(\'sb-mode\').innerHTML=\'🟢 <span>Live Webex Calling</span>\';
  }
  document.getElementById(\'cfg-modal\').classList.remove(\'on\');
}
function skipConfig(){
  document.getElementById(\'cfg-modal\').classList.remove(\'on\');
}
function setBadge(cls,txt){
  const b=document.getElementById(\'tbadge\');
  b.className=\'token-badge tb-\'+cls; b.textContent=txt;
}

// ── NAVIGATION ───────────────────────────────────────────────────
function goTo(id){
  document.querySelectorAll(\'.screen\').forEach(s=>s.classList.remove(\'active\'));
  document.getElementById(id).classList.add(\'active\');
}
function pick(name,icon,key,col,desc){
  S.dept=name; S.icon=icon; S.key=key;
  const pi=document.getElementById(\'pre-icon\');
  pi.textContent=icon;
  pi.style.background=`linear-gradient(135deg,#${col},color-mix(in srgb,#${col} 60%,#000))`;
  document.getElementById(\'pre-title\').textContent=`Connect to ${name}`;
  document.getElementById(\'pre-sub\').textContent=desc;
  document.getElementById(\'post-dept\').textContent=name;
  goTo(\'s-pre\');
}

// ── CALL FLOW ─────────────────────────────────────────────────────
async function startCall(){
  [\'call-av\',\'s-av\'].forEach(id=>document.getElementById(id).textContent=S.icon);
  document.getElementById(\'s-name\').textContent=S.dept;
  document.getElementById(\'call-qlabel\').textContent=S.dept+\' Queue\';
  document.getElementById(\'s-queue\').textContent=
    S.q[S.key]||(\'CQ-\'+S.dept.replace(/\\s+/g,\'\').toUpperCase().slice(0,10));
  goTo(\'s-call\');
  showOv(\'Initializing Webex Calling SDK…\');
  (!S.demo && S.token) ? await liveCall() :
    setTimeout(()=>{hideOv();simConnect();},2200);
}

// ── REAL WEBEX CALLING (Bearer token, no Service App) ────────────
async function liveCall(){
  try{
    S.calling=await Calling.init({
      webexConfig:{
        credentials:{access_token:S.token}, // ← Bearer token, pasted at runtime
        config:{logger:{level:\'error\'}}
      },
      callingConfig:{
        clientConfig:{calling:true},
        callingClientConfig:{
          // \'calling\' indicator = full Webex Calling user mode
          // No Service App, no JWE token, no AWS backend needed
          serviceData:{indicator:\'calling\'}
        },
        logger:{level:\'error\'}
      }
    });
    S.calling.on(\'ready\',()=>S.calling.register().then(async()=>{
      const mic=await Calling.createMicrophoneStream({audio:true});
      const line=Object.values(S.calling.callingClient.getLines())[0];
      line.on(\'registered\',()=>{
        updOv(\'Dialing queue…\');
        const dest=S.q[S.key];
        if(!dest){hideOv();simConnect();return;}
        const call=line.makeCall({destination:dest});
        call.on(\'progress\',  ()=>updOv(\'Ringing…\'));
        call.on(\'connected\', ()=>{hideOv();onConnected(call);});
        call.on(\'remote_audio\',(stream)=>{document.getElementById(\'audio\').srcObject=stream;});
        call.on(\'disconnected\',()=>endCall());
        call.on(\'call_error\', ()=>{hideOv();simConnect();});
        call.dial(mic);
      });
      updOv(\'Registering…\');
      line.register();
    }));
  }catch(e){console.error(e);hideOv();simConnect();}
}

function onConnected(call){
  S.activeCall=call;
  document.getElementById(\'call-con\').textContent=\'✅ Connected!\';
  document.getElementById(\'dots\').style.display=\'none\';
  document.getElementById(\'call-status\').textContent=\'🔴 Call Active\';
  S.t0=Date.now(); S.tiv=setInterval(tick,1000);
}

// ── DEMO SIMULATION ───────────────────────────────────────────────
function simConnect(){
  document.getElementById(\'call-con\').textContent=\'✅ Connected (Demo)\';
  document.getElementById(\'dots\').style.display=\'none\';
  document.getElementById(\'call-status\').textContent=\'🔴 Demo Call Active\';
  S.t0=Date.now(); S.tiv=setInterval(tick,1000);
  const tb=document.getElementById(\'tscript\'); tb.innerHTML=\'\';
  [{d:1200,c:\'ta\',t:\'Agent: Hello! This is Sarah, your Nutrition Advisor.\'},
   {d:4800,c:\'ts\',t:\'Shopper: Hi! Need high-protein options in the dairy aisle.\'},
   {d:8500,c:\'ta\',t:\'Agent: Chobani Greek Yogurt — 17g protein per serving.\'},
   {d:13000,c:\'ts\',t:\'Shopper: Any lactose-free options?\'},
   {d:16500,c:\'ta\',t:\'Agent: Green Valley Creamery — aisle 4, top shelf!\'}
  ].forEach(l=>setTimeout(()=>{
    const p=document.createElement(\'p\');
    p.className=l.c; p.textContent=l.t;
    tb.appendChild(p); tb.scrollTop=tb.scrollHeight;
  },l.d));
}

function tick(){
  const e=Math.floor((Date.now()-S.t0)/1000);
  document.getElementById(\'timer\').textContent=
    `${Math.floor(e/60)}:${(e%60).toString().padStart(2,\'0\')}`;
}

function endCall(){
  clearInterval(S.tiv);
  if(S.activeCall)try{S.activeCall.end();}catch(e){}
  if(S.calling)   try{S.calling.deregister();}catch(e){}
  S.activeCall=null; S.calling=null;
  goTo(\'s-post\');
}

function toggleMute(){
  S.muted=!S.muted;
  const b=document.getElementById(\'btn-mute\');
  b.textContent=S.muted?\'🔇\':\'🎤\';
  b.classList.toggle(\'muted\',S.muted);
  if(S.activeCall)try{S.muted?S.activeCall.mute():S.activeCall.unmute();}catch(e){}
}

// ── OVERLAY ───────────────────────────────────────────────────────
function showOv(m){document.getElementById(\'overlay-txt\').textContent=m;
  document.getElementById(\'overlay\').classList.add(\'on\');}
function updOv(m){document.getElementById(\'overlay-txt\').textContent=m;}
function hideOv(){document.getElementById(\'overlay\').classList.remove(\'on\');}

// ── RATING ────────────────────────────────────────────────────────
function rate(b){
  document.querySelectorAll(\'.star\').forEach(x=>x.classList.remove(\'sel\'));
  b.classList.add(\'sel\');
}

// ── CLOCK ─────────────────────────────────────────────────────────
function updClock(){
  const t=new Date().toLocaleTimeString(\'en-US\',{hour:\'2-digit\',minute:\'2-digit\'});
  [\'clock\',\'sbar-t\'].forEach(id=>{const el=document.getElementById(id);if(el)el.textContent=t;});
}
setInterval(updClock,1000); updClock();

// ── IDLE TIMEOUT (45s) ────────────────────────────────────────────
let idle;
function resetIdle(){
  clearTimeout(idle);
  idle=setTimeout(()=>{
    const a=document.querySelector(\'.screen.active\');
    if(a&&![\'s-attract\',\'s-call\'].includes(a.id))goTo(\'s-attract\');
  },45000);
}
[\'touchstart\',\'click\',\'keydown\'].forEach(e=>document.addEventListener(e,resetIdle));
resetIdle();
</script>
</body>
</html>'''

# ── Write all files + ZIP ────────────────────────────────────────────────────
files = {
    'kiosk.html':    KIOSK_HTML,
    'server.py':     SERVER_PY,
    'README.md':     README,
    'QUICKSTART.md': QUICKSTART,
}

for fname, content in files.items():
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

with zipfile.ZipFile('ADUSA_Expert_Connect.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for fname in files:
        z.write(fname)

sizes = {f: os.path.getsize(f) for f in list(files.keys()) + ['ADUSA_Expert_Connect.zip']}
for f, s in sizes.items():
    print(f"  {f:<35} {s:>8,} bytes")
