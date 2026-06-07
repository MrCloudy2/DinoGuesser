import os, sys, subprocess, http.server, threading, webbrowser, socket

# Generate picker if outdated or missing
picker = "../picker.html"
if not os.path.exists(picker):
    print("Generating picker.html ...")
    subprocess.run([sys.executable, "3b_generate_picker.py"], check=True)

# Serve from project root (one level up), so data/images/* are reachable
os.chdir("..")

PORT = 8001

# --- Helper to automatically find your actual local IP address ---
def get_local_ip():
    try:
        # Does not actually connect to the internet, just probes local routing
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silence request logs

# Update print statements to show the network-accessible URL
print(f"Local access:   http://localhost:{PORT}/picker.html")
print(f"Network access: http://{LOCAL_IP}:{PORT}/picker.html")
print("Press Ctrl-C to stop.\n")

def open_browser():
    import time; time.sleep(0.5)
    # The host machine can still just open localhost
    webbrowser.open(f"http://localhost:{PORT}/picker.html")

threading.Thread(target=open_browser, daemon=True).start()

# Changing "" to "0.0.0.0" opens it up to the local network
with http.server.HTTPServer(("0.0.0.0", PORT), Handler) as srv:
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
