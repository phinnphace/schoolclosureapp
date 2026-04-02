# 📱 MMSD School Closure & Delay Monitor

MMSD (Madison Metropolitan School District) has a well-documented pattern of being one of the last districts in Dane County to announce closures and delays — often well after families with non-flexible schedules have already had to make childcare decisions.

This script won't fix that policy. But it will text you (or email you) the moment the MMSD website changes or closure/delay language appears, so you're not refreshing a browser tab at 5 AM.

---

## How it works

The script polls the MMSD homepage every 5 minutes and does two things:

1. **Page change detection** — hashes the full page content on each check. If anything changes, you get an alert immediately.
2. **Keyword detection** — scans for words like "closed," "delay," "late start," "cancelled," etc. Sends a one-time alert the first time these appear.

Alerts go to your phone via your carrier's SMS email gateway (arrives as a text), and optionally to an email inbox too.

---

## Setup

### 1. Prerequisites

- Python 3.9+
- A Gmail account (for sending alerts via SMTP)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your environment

```bash
cp .env.example .env
```

Edit `.env`:

```
FROM_EMAIL=you@gmail.com
FROM_APP_PASSWORD=your_app_password_here
TO_SMS=6085551234@vtext.com
TO_EMAIL=                          # optional second alert destination
```

**Setting up a Gmail App Password:**  
You need an App Password, not your regular Gmail password.  
Google Account → Security → 2-Step Verification → App Passwords → Create one for "Mail"

**Finding your carrier's SMS gateway:**

| Carrier | Gateway |
|---|---|
| Verizon | `number@vtext.com` |
| AT&T | `number@txt.att.net` |
| T-Mobile | `number@tmomail.net` |
| US Cellular | `number@email.uscc.net` |

Use your full 10-digit number with no dashes: `6085551234@vtext.com`

### 4. Run

```bash
python school_closure_monitor.py
```

You'll see confirmation output every cycle. Leave the terminal open, or see below for always-on options.

---

## Running it always-on

### macOS — launchd (runs on login, auto-restarts)

Create `~/Library/LaunchAgents/com.mmsdmonitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mmsdmonitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/.venv/bin/python</string>
        <string>/path/to/school_closure_monitor.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/mmsd-monitor</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/mmsd-monitor/monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/mmsd-monitor/monitor.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.mmsdmonitor.plist
```

### Linux — systemd

Create `/etc/systemd/system/mmsd-monitor.service`:

```ini
[Unit]
Description=MMSD School Closure Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/mmsd-monitor
ExecStart=/path/to/.venv/bin/python /path/to/school_closure_monitor.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mmsd-monitor
sudo systemctl start mmsd-monitor
sudo systemctl status mmsd-monitor
```

### tmux (quick and easy, any platform)

```bash
tmux new-session -d -s mmsd 'python school_closure_monitor.py'
# Reattach anytime to check logs:
tmux attach -t mmsd
```

---

## State persistence

The script saves a `mmsd_watch_state.json` file that records:
- The hash of the last page it saw (so it doesn't re-alert on restarts)
- Whether a keyword alert has already been sent this cycle

If you want to reset alerts (e.g. start of a new school year, or after a closure has resolved), delete this file:

```bash
rm mmsd_watch_state.json
```

---

## Adapting for other districts

This script works with any school district's website — just change `WATCH_URL` in `.env`:

```
WATCH_URL=https://your-district-website.org
```

---

## License

MIT — use it, modify it, share it.
