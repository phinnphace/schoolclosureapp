#!/usr/bin/env python3
"""
MMSD School Closure / Delay Monitor
-------------------------------------
Watches the Madison Metropolitan School District website for closure or
delay announcements and sends you an alert via SMS (carrier email gateway)
and/or email — so you don't have to keep refreshing the page at 5 AM.

MMSD has a well-documented tendency to be among the last districts to call
closures, which doesn't work for families with blue-collar schedules that
can't flex on short notice. This script gives you an early heads-up the
moment the page changes or closure language appears.

Usage
-----
1. Copy .env.example to .env and fill in your values.
2. Install dependencies:  pip install -r requirements.txt
3. Run:                   python school_closure_monitor.py

The script runs in a loop, checking every 5 minutes (configurable).
Keep it running in a terminal, tmux session, or set it up as a service.

See README.md for always-on setup instructions (systemd, launchd, etc.)
"""

import os
import time
import json
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURATION  (all values come from .env)
# ============================================================================

# Page to watch
URL = os.getenv("WATCH_URL", "https://www.madison.k12.wi.us")

# How often to check, in seconds (default: 5 minutes)
CHECK_EVERY_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

# --- Email / SMS credentials -------------------------------------------
# Gmail is simplest. Use a Google App Password, not your regular password.
# How to create one: myaccount.google.com → Security → App Passwords
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_APP_PASSWORD = os.getenv("FROM_APP_PASSWORD")

if not FROM_EMAIL or not FROM_APP_PASSWORD:
    raise SystemExit(
        "\n❌  FROM_EMAIL and FROM_APP_PASSWORD must be set in .env\n"
        "    See .env.example for instructions.\n"
    )

# --- Where alerts go ---------------------------------------------------
# SMS via carrier email gateway (sends as a text message)
# Format: your_number@carrier_gateway
# Common gateways:
#   Verizon:   number@vtext.com
#   AT&T:      number@txt.att.net
#   T-Mobile:  number@tmomail.net
#   US Cellular: number@email.uscc.net
TO_SMS = os.getenv("TO_SMS", "")          # e.g. 6085551234@vtext.com

# Optional: also send to a regular email address
TO_EMAIL = os.getenv("TO_EMAIL", "")      # e.g. you@example.com

if not TO_SMS and not TO_EMAIL:
    raise SystemExit(
        "\n❌  Set at least one of TO_SMS or TO_EMAIL in .env\n"
        "    You need somewhere for alerts to go.\n"
    )

# --- Keywords that signal a closure or delay ---------------------------
KEYWORDS = [
    "closed", "closure", "no school", "weather", "extreme weather",
    "late start", "delay", "canceled", "cancelled",
]

# Where script state is persisted between runs
STATE_FILE = os.getenv("STATE_FILE", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mmsd_watch_state.json"
))


# ============================================================================
# CORE LOGIC
# ============================================================================

def fetch_page(url: str):
    r = requests.get(url, timeout=20, allow_redirects=True)
    return r.status_code, r.text


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_hash": None, "keyword_alerted": False}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def send_alert(subject: str, body: str) -> None:
    """Send an alert to SMS gateway and/or email."""
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)

    recipients = [r for r in [TO_SMS, TO_EMAIL] if r]
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(FROM_EMAIL, FROM_APP_PASSWORD)
        smtp.send_message(msg)


def main():
    state = load_state()
    last_hash = state.get("last_hash")
    keyword_alerted = state.get("keyword_alerted", False)

    print(f"👀  MMSD closure/delay monitor started")
    print(f"    Watching: {URL}")
    print(f"    Interval: every {CHECK_EVERY_SECONDS}s ({CHECK_EVERY_SECONDS // 60} min)")
    print(f"    Alerts → {', '.join(r for r in [TO_SMS, TO_EMAIL] if r)}\n")

    while True:
        try:
            status_code, html = fetch_page(URL)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if status_code != 200:
                print(f"{now} - HTTP {status_code}; skipping (not a closure signal)")
                time.sleep(CHECK_EVERY_SECONDS)
                continue

            current_hash = sha256(html)
            lower = html.lower()

            # Alert on any page change
            if last_hash and current_hash != last_hash:
                send_alert(
                    subject="MMSD page changed",
                    body=f"[{now}] The MMSD website changed. Check for closure/delay info: {URL}",
                )
                print(f"{now} - ⚡ Page change detected → alert sent.")

            # Alert once when closure/delay keywords are detected
            if (not keyword_alerted) and any(k in lower for k in KEYWORDS):
                send_alert(
                    subject="MMSD closure/delay signal",
                    body=(
                        f"[{now}] Possible closure or delay language detected on the MMSD site.\n"
                        f"Check: {URL}"
                    ),
                )
                keyword_alerted = True
                print(f"{now} - 🚨 Keyword signal detected → alert sent (one-time).")

            # Persist state
            last_hash = current_hash
            state["last_hash"] = last_hash
            state["keyword_alerted"] = keyword_alerted
            save_state(state)

            print(f"{now} - ✓ checked (hash: {current_hash[:8]}…)")

        except Exception as e:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ⚠️  Check failed: {e}")

        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()
