# ADUSA In-Store Expert Connect
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
