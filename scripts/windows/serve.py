"""
Runs Royal Shetkari on this PC with waitress (a production web server
that works on Windows) and opens the login page in the browser once the
server is answering. Called by start.bat. Close the window to stop.
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
URL = f"http://127.0.0.1:{PORT}/login/"


def port_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def open_browser_when_ready():
    for _ in range(120):
        if port_busy():
            webbrowser.open(URL)
            return
        time.sleep(0.5)


def lan_addresses():
    try:
        return sorted({info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                       if not info[4][0].startswith("127.")})
    except OSError:
        return []


def main():
    if port_busy():
        print(f"Royal Shetkari (or another program) is already running on port {PORT}.")
        print(f"Opening {URL}")
        webbrowser.open(URL)
        return
    from waitress import serve
    from core.wsgi import application

    print("=" * 64)
    print(" Royal Shetkari is running.")
    print(f" On this PC:  {URL}")
    if HOST == "0.0.0.0":
        for ip in lan_addresses():
            print(f" On tablets/phones on the same Wi-Fi:  http://{ip}:{PORT}/login/")
    print(" Keep this window open while the restaurant is working.")
    print(" To stop: close this window (or press Ctrl+C).")
    print("=" * 64, flush=True)
    if os.getenv("POS_NO_BROWSER") != "1":
        threading.Thread(target=open_browser_when_ready, daemon=True).start()
    serve(application, host=HOST, port=PORT, threads=8, ident="RoyalShetkariPOS")


if __name__ == "__main__":
    main()
