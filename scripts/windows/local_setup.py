"""
Prepares this PC to run Royal Shetkari. Called by setup.bat and start.bat;
safe to run any number of times.

  --first-run   also load the Royal Shetkari menu and sample data
  (always)      create .env with fresh secret keys if missing, back up the
                database, apply database updates, collect static files

Never overwrites an existing secret key: FIELD_ENCRYPTION_KEY protects
stored payment-gateway secrets and must stay the same once data exists.
"""
import argparse
import os
import secrets
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env"
DB = ROOT / "db.sqlite3"
BACKUPS = ROOT / "backups"
LOGINS = ROOT / "DEMO_LOGINS.txt"
KEEP_BACKUPS = 20


def say(msg):
    print(f"  {msg}", flush=True)


def read_env():
    values = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


def ensure_env():
    from cryptography.fernet import Fernet

    values = read_env()
    wanted = {
        "SECRET_KEY": lambda: secrets.token_urlsafe(50),
        "FIELD_ENCRYPTION_KEY": lambda: Fernet.generate_key().decode(),
        "LOCAL_INSTALL": lambda: "True",
        "DEBUG": lambda: "False",
        "ALLOWED_HOSTS": lambda: "*",
        "BASE_URL": lambda: "http://127.0.0.1:8000",
        "DB_CONN_MAX_AGE": lambda: "0",
        "EMAIL_BACKEND": lambda: "django.core.mail.backends.console.EmailBackend",
        "HOST": lambda: "127.0.0.1",
        "PORT": lambda: "8000",
    }
    added = [k for k in wanted if k not in values]
    if not ENV.exists():
        header = ("# Royal Shetkari - settings for this PC (created by setup.bat).\n"
                  "# Keep this file private. Do NOT change SECRET_KEY or FIELD_ENCRYPTION_KEY once data exists.\n"
                  "# HOST=0.0.0.0 lets tablets/phones on the restaurant Wi-Fi open the POS (see WINDOWS_SETUP.md).\n")
        ENV.write_text(header, encoding="utf-8")
    if added:
        with open(ENV, "a", encoding="utf-8") as fh:
            for k in added:
                fh.write(f"{k}={wanted[k]()}\n")
        say(f".env: added {', '.join(added)}")
    else:
        say(".env: already configured")
    values = read_env()
    if values.get("LOCAL_INSTALL") != "True":
        say("NOTE: LOCAL_INSTALL is not True in .env; the app will run in hosted-server mode.")


def backup_db(reason):
    if not DB.exists():
        return
    BACKUPS.mkdir(exist_ok=True)
    target = BACKUPS / f"db_{datetime.now():%Y%m%d_%H%M%S}_{reason}.sqlite3"
    # sqlite3's online backup: a consistent copy even if the file is busy.
    import sqlite3
    src = sqlite3.connect(str(DB))
    dst = sqlite3.connect(str(target))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    say(f"Database backed up to backups\\{target.name}")
    old = sorted(BACKUPS.glob("db_*_start.sqlite3"))
    for f in old[:-KEEP_BACKUPS]:
        f.unlink()


def manage(*args, check=True):
    cmd = [sys.executable, str(ROOT / "manage.py"), *args]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if check and result.returncode != 0:
        print(f"\nFAILED: manage.py {' '.join(args)}", flush=True)
        sys.exit(result.returncode)
    return result.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first-run", action="store_true")
    args = ap.parse_args()
    os.chdir(ROOT)

    print("[1/4] Settings", flush=True)
    ensure_env()
    print("[2/4] Database backup", flush=True)
    backup_db("setup" if args.first_run else "start")
    print("[3/4] Database updates", flush=True)
    manage("migrate", "--noinput", "-v", "0")
    say("Database is up to date")
    print("[4/4] Screens and styles", flush=True)
    manage("collectstatic", "--noinput", "-v", "0")
    say("Static files ready")

    if args.first_run:
        print("[+] Royal Shetkari menu and sample data", flush=True)
        manage("seed_royal_shetkari")
        if not LOGINS.exists():
            # A copied database: give the sample logins fresh passwords on this PC.
            manage("seed_royal_shetkari", "--no-history", "--reset-demo-passwords")
        manage("check_royal_shetkari", check=False)
        if LOGINS.exists():
            print("\nSample staff logins are in DEMO_LOGINS.txt (keep it private).", flush=True)


if __name__ == "__main__":
    main()
