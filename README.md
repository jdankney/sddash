# SDDASH

A tiny **systemd service dashboard** — a lightweight web UI that shows the live status of whitelisted services and lets you start, stop, and restart them.

Designed to run on a **private network** (e.g. your Tailscale tailnet) for safe, remote server management.

---

## Features

- **Live status monitoring** — running / inactive indicators with auto-refresh every 4 seconds
- **Full `systemctl status` output** — expandable panels showing the last 25 lines of each service's status log
- **Start / Stop / Restart controls** — one-click service management with immediate feedback
- **Security-first design**
  - Only services listed in the `SERVICES` whitelist are visible or controllable (no command injection surface)
  - Actions use `sudo -n systemctl ...` — grant only those exact commands via a sudoers rule, never blanket sudo
  - HTTP Basic Authentication with credentials read from environment variables (or explicitly disabled on a trusted network)
  - Meant to stay on a private network — do **not** expose to the public internet
- **Dark terminal aesthetic** — minimalist, mono-spaced UI with glowing status LEDs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + Flask |
| Frontend | Vanilla HTML / CSS / JS |
| Service communication | `systemctl` (via `subprocess`, no shell) |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure sudoers

Grant the Flask process permission to manage services **without a password**, and **only** for the exact commands listed. No sudoers file is shipped with the repo — create it yourself with `sudo visudo -f /etc/sudoers.d/sddash`:

```sudoers
# /etc/sudoers.d/sddash
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl start <unit>, \
                            /usr/bin/systemctl stop <unit>, \
                            /usr/bin/systemctl restart <unit>
```

Replace `www-data` with whatever user runs the app, and add one rule per unit you want to control. The app runs `sudo -n systemctl <action> <unit>` with the unit name **without** the `.service` suffix, so the sudoers entries must use the same names. Confirm the `systemctl` path on your system with `command -v systemctl`.

### 3. Edit the service list

Open `app.py` and customize the `SERVICES` dictionary — each key is a systemd unit name (without `.service`), and each value is a friendly label:

```python
SERVICES = {
    "nginx":  "Nginx",
    "docker": "Docker Containers",
    "ssh":    "OpenSSH",
}
```

### 4. Set authentication

Credentials are read from the environment, not stored in `app.py`:

```bash
export SDDASH_USER=admin          # optional; defaults to "admin"
export SDDASH_PASS='a-long-random-password'
```

The app refuses to start without `SDDASH_PASS` unless you explicitly opt out on a trusted network:

```bash
export SDDASH_NO_AUTH=1           # only on localhost / a trusted private network
```

### 5. Run

```bash
export SDDASH_PASS='a-long-random-password'
python app.py
```

The dashboard will be available at `http://127.0.0.1:8099` by default.

> **Tip:** To listen on a Tailscale/tailnet address, set the host explicitly:
> ```bash
> export SDDASH_HOST=100.x.y.z
> export SDDASH_PORT=8099
> ```

---

## Project Structure

```
app.py              # Flask backend — API routes, service helpers, config
requirements.txt    # Python dependencies
templates/
  index.html        # Frontend — UI, styling, and client-side logic
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard page |
| `GET` | `/api/services` | JSON list of all services with `name`, `label`, `active`, `enabled` |
| `GET` | `/api/status/<service>` | Full `systemctl status` text for a single service |
| `POST` | `/api/action/<service>/<action>` | Perform `start`, `stop`, or `restart` on a service. Requires the `X-Requested-With: sddash` header. |

All endpoints, including the dashboard page, require authentication unless `SDDASH_NO_AUTH=1` is set.

---

## Security Notes

- ⚠️ **Never port-forward this app to the public internet.**
- ⚠️ Only grant the minimum sudo permissions needed — the suggested sudoers model is per-command, not global.
- ⚠️ `systemctl` is never called with untrusted input; service names come exclusively from the `SERVICES` whitelist.
- ⚠️ The Flask development server is not intended for production use. Put it behind a production WSGI server (e.g. waitress or gunicorn) if you expose it beyond localhost.
- ⚠️ This repo starts with no credentials in source. If you previously published a password in Git history, rotate it and scrub the history before pushing.

---

## License

No license file is currently included. Add one (for example, MIT) if you intend others to reuse this project.
