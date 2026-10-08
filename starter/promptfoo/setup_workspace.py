#!/usr/bin/env python3
"""Create (or reuse) a Pink sandbox workspace for the promptfoo red-team run.

Python 3 stdlib only. Prints two `export` lines to stdout (and nothing else to
stdout), so it can be eval'd directly by a shell script:

    eval "$(python3 setup_workspace.py)"

All human-readable status goes to stderr. If PINK_WORKSPACE_ID and
PINK_AGENT_KEY are already set, it reuses them and makes no network call
(workspace creation is rate limited; see the challenge README).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://agentic-sandbox.pinkwallet.com"


def mask(key):
    if not key or len(key) < 12:
        return "****"
    return key[:12] + "…"


def log(msg):
    print(msg, file=sys.stderr)


def http(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    # Cloudflare blocks the default urllib User-Agent; any browser-like UA works.
    req.add_header("User-Agent", "Mozilla/5.0 pink-promptfoo-starter/1.0")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": str(e)}


def main():
    ws_id = os.environ.get("PINK_WORKSPACE_ID")
    agent_key = os.environ.get("PINK_AGENT_KEY")
    if ws_id and agent_key:
        log("Reusing workspace %s, agent key %s" % (ws_id, mask(agent_key)))
        print("export PINK_WORKSPACE_ID=%s" % ws_id)
        print("export PINK_AGENT_KEY=%s" % agent_key)
        return

    log("No PINK_WORKSPACE_ID / PINK_AGENT_KEY set. Creating a new sandbox workspace...")
    company = "RT-promptfoo-%d" % int(time.time())
    for attempt in range(6):
        status, body = http(
            "POST",
            "/v1/sandbox/workspaces",
            body={"company": company, "email": os.environ.get("PINK_SETUP_EMAIL", "redteam@example.com"), "template": "coffee"},
        )
        if status in (200, 201):
            break
        if status == 429:
            log("Rate limited, retrying in 25s...")
            time.sleep(25)
            continue
        log("Failed to create workspace: HTTP %s %s" % (status, body))
        sys.exit(1)
    else:
        log("Giving up after repeated rate limiting.")
        sys.exit(1)

    ws_id = body["workspace_id"]
    purchasing = next(a for a in body["agents"] if a["id"] == "a_purch")
    agent_key = purchasing["key"]

    log("Created workspace %s" % ws_id)
    log("Purchasing AI key: %s (per_payment_cap $%s, monthly_budget $%s)" % (
        mask(agent_key), purchasing.get("per_payment_cap"), purchasing.get("monthly_budget")))
    log("")
    log("To reuse this workspace next run (workspace creation is rate limited):")
    log("  export PINK_WORKSPACE_ID=%s" % ws_id)
    log("  export PINK_AGENT_KEY=%s   # keep this private, do not post it (full key printed to stdout only)" % mask(agent_key))
    log("")

    print("export PINK_WORKSPACE_ID=%s" % ws_id)
    print("export PINK_AGENT_KEY=%s" % agent_key)


if __name__ == "__main__":
    main()
