#!/usr/bin/env python3
"""
sddash - a tiny systemd service dashboard.

Shows live status (running/inactive), full `systemctl status` output in a
collapsible panel, and start/stop/restart buttons for a *whitelisted* set of
services.

SECURITY MODEL
--------------
* systemctl is never handed any service name that isn't a key in SERVICES,
  so there is no command-injection surface from the web side.
* Reading status (is-active / status) needs no privilege.
* start/stop/restart use `sudo -n systemctl ...`. Grant ONLY those exact
  commands via a per-command sudoers rule -- never blanket sudo. No sudoers
  file is shipped; see README.md for an example.
* This is meant to live behind a private network (your Tailscale tailnet).
  Do NOT port-forward it to the public internet.
"""
import hmac
import os
import subprocess
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response

# ---- Configuration -------------------------------------------------------
# The ONLY services this dashboard can see or touch. Edit to taste.
# Key = systemd unit name (without .service), value = friendly label.
SERVICES = {
    "netbird":    "Netbird VPN",
    "projecttree":"Projecttree",
    "docker":     "Docker Containers",
    "radicale":   "CalDAV Server",
    "smbd":       "Samba (SMB file sharing)",
    "dnsmasq":    "Local mDNS",
    "syncthing":  "Syncthing",
    "kiwix-serve": "Kiwix (Wikipedia)",
    "immich":     "Immich Photo Service",
    "jellyfin":   "Jellyfin media server",
}

ALLOWED_ACTIONS = {"start", "stop", "restart"}

# HTTP Basic auth. Credentials come from the environment, never from source.
# Set SDDASH_NO_AUTH=1 only on a trusted network to disable auth explicitly.
AUTH_USER = os.environ.get("SDDASH_USER", "admin")
AUTH_PASS = os.environ.get("SDDASH_PASS") or None
AUTH_DISABLED = os.environ.get("SDDASH_NO_AUTH") == "1"

if not AUTH_PASS and not AUTH_DISABLED:
    raise SystemExit(
        "SDDASH_PASS is not set. Set SDDASH_PASS (and optionally SDDASH_USER), "
        "or set SDDASH_NO_AUTH=1 to run without authentication."
    )

# Bind to localhost by default. For remote access, set SDDASH_HOST to your
# private/tailnet IP (for example, 100.x.y.z).
HOST = os.environ.get("SDDASH_HOST", "127.0.0.1")
PORT = int(os.environ.get("SDDASH_PORT", "8099"))
# -------------------------------------------------------------------------

app = Flask(__name__)


def run(cmd):
    """Run a command (list form, NO shell) -> (returncode, combined output)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "command timed out"
    except Exception as e:  # pragma: no cover
        return 1, str(e)


def is_active(service):
    rc, _ = run(["systemctl", "is-active", "--quiet", service])
    return rc == 0


def enabled_state(service):
    rc, out = run(["systemctl", "is-enabled", service])
    return out.strip() or ("enabled" if rc == 0 else "unknown")


def requires_auth(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if AUTH_DISABLED:
            return f(*a, **kw)
        auth = request.authorization
        if not auth:
            return Response("Authentication required", 401,
                            {"WWW-Authenticate": 'Basic realm="sddash"'})
        user_ok = hmac.compare_digest(auth.username or "", AUTH_USER)
        pass_ok = hmac.compare_digest(auth.password or "", AUTH_PASS or "")
        if not (user_ok and pass_ok):
            return Response("Authentication required", 401,
                            {"WWW-Authenticate": 'Basic realm="sddash"'})
        return f(*a, **kw)
    return wrapper


@app.route("/")
@requires_auth
def index():
    return render_template("index.html")


@app.route("/api/services")
@requires_auth
def api_services():
    return jsonify([
        {"name": name, "label": label,
         "active": is_active(name), "enabled": enabled_state(name)}
        for name, label in SERVICES.items()
    ])


@app.route("/api/status/<service>")
@requires_auth
def api_status(service):
    if service not in SERVICES:
        return jsonify({"error": "unknown service"}), 404
    _, text = run(["systemctl", "status", service, "--no-pager", "-n", "25"])
    return jsonify({"active": is_active(service), "text": text})


@app.route("/api/action/<service>/<action>", methods=["POST"])
@requires_auth
def api_action(service, action):
    # Require a custom header so a cross-site HTML form cannot trigger actions
    # using cached Basic-auth credentials.
    if request.headers.get("X-Requested-With") != "sddash":
        return jsonify({"error": "missing X-Requested-With header"}), 403
    if service not in SERVICES:
        return jsonify({"error": "unknown service"}), 404
    if action not in ALLOWED_ACTIONS:
        return jsonify({"error": "bad action"}), 400
    rc, text = run(["sudo", "-n", "systemctl", action, service])
    return jsonify({"ok": rc == 0, "active": is_active(service), "text": text})


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)

