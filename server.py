# Replace the broken server.py inline
cat > server.py << 'EOF'
#!/usr/bin/env python3
import http.server, os, sys

PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

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

class KioskHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIRECTORY, **kw)
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        super().end_headers()
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.path = '/kiosk.html'
        super().do_GET()
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

if __name__ == '__main__':
    with http.server.HTTPServer(('', PORT), KioskHandler) as httpd:
        print(f"\n{'═'*51}")
        print(f"  ADUSA Expert Connect Kiosk Server")
        print(f"  http://localhost:{PORT}")
        print(f"  Network: http://{_get_lan_ip()}:{PORT}")
        print(f"  Press Ctrl+C to stop")
        print(f"{'═'*51}\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            sys.exit(0)
EOF
