# TODO

Found during a security review. Roughly in order of urgency.

## Broken / security

- [ ] **Rotate the Basic-auth password.** A literal password was committed
      in `app.py` in the initial commit (`97f0b9b`), so it remains in the
      repository history. The current file reads credentials from the
      environment; rotate the old password anywhere it was reused.
- [x] **Read credentials from the environment** (`SDDASH_USER` /
      `SDDASH_PASS`, or a hash) instead of source. Refuse to start with no
      password unless explicitly told to (`SDDASH_NO_AUTH=1`).
- [ ] **Scrub the password from history** once rotated (`git filter-repo
      --replace-text`, then force-push). Rotation is the real fix; this is
      just hygiene.
- [x] **Fix the syntax error:** missing comma after `"syncthing": "Syncige"`
      in `SERVICES`. This prevented the app from starting.
- [x] **CSRF on `POST /api/action/...`.** Browsers attach cached Basic-auth
      credentials to cross-site requests, so any page you visit could submit a
      form that stops a service. Require a custom header (e.g.
      `X-Requested-With: sddash`, which a cross-site form can't set) or check
      `Origin`, and send it from `doAction()`.
- [x] **Constant-time password compare:** use `hmac.compare_digest` instead
      of `!=`.

## Hardening

- [x] Default `HOST` to `127.0.0.1` (or the tailnet IP) rather than `0.0.0.0`.
- [ ] Don't run Flask's dev server in production: use waitress or gunicorn.
- [ ] Ship an example systemd unit and sudoers file (the README currently
      shows a snippet, but no files are included).
- [ ] Sudoers rules must match the exact argv: the app runs
      `systemctl start <unit>` (no `.service` suffix). The README documents
      this; consider using the full `/usr/bin/systemctl` path in the app too.
- [ ] Frontend builds rows with `innerHTML` from `name`, `label` and the
      `systemctl is-enabled` output. Low risk since it's all server-side, but
      `textContent` costs nothing.

## Polish

- [x] Typo: `"Syncige"` → `"Syncthing"`.
- [ ] Move `SERVICES` out of `app.py` into a config file (YAML/TOML/env), so
      updating the code doesn't clobber your list.
- [ ] `/api/services` spawns two `systemctl` processes per service every 4 s
      per open tab. One `systemctl show -p ActiveState,UnitFileState unit1 unit2 …`
      call can return everything.
- [x] Add `requirements.txt` (or `pyproject.toml`).
- [x] README: "All endpoints (except the page itself) require authentication"
      — the page requires it too.
- [x] README License says "Private / internal use only". Pick a real license
      if it's going to stay on a shared forge.
- [ ] Self-host the IBM Plex Mono font so the page works with no internet.
