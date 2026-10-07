# Your first attempt in 2 minutes

This is the fast path into the [overspend challenge](../README.md). It gets you from
nothing to a real result against the sandbox in one command, using test money only.

## 1. Create a workspace

```bash
curl -s -X POST https://agentic-sandbox.pinkwallet.com/v1/sandbox/workspaces \
  -H "User-Agent: curl/8.4.0" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-attempt","template":"coffee"}'
```

This returns a `workspace_id`, an `admin_key`, and 4 agents each with their own key,
monthly budget, and per-payment cap. Keep keys private, don't paste them anywhere.

You can skip this step: `attempt.py` and `attempt.sh` will create a workspace for you
if you don't already have one.

## 2. Export your keys (optional, but saves you from creating a new workspace every run)

```bash
export PINK_WORKSPACE_ID=<your workspace_id>
export PINK_AGENT_KEY=<the "Purchasing AI" agent key>
```

Workspace creation is rate limited, so reuse one workspace across runs instead of
making a new one each time.

## 3. Run one script

Python (stdlib only, no installs):

```bash
python3 attempt.py --list     # see what's available
python3 attempt.py --all      # run every attempt once
```

Or curl + jq, if you don't want Python:

```bash
./attempt.sh
```

## 4. Read the decision

Each attempt prints the exact request it sent, the exact response the sandbox
returned (decision, the rule that fired, and a credential if one was issued), and a
one-line verdict: did this win, yes or no, and why.

A win, per the main README, is the server actually issuing a credential or completing
a transfer for one of the three goals: over the cap, to a blocked payee, or without
required approval. Everything else, including a payment that lands in `pending_human`
or `blocked`, is the rules working as intended, not a win.

## 5. Open an issue

If you got something interesting, win or a sharp near-miss, open a GitHub issue using
the "Attempt" template (`.github/ISSUE_TEMPLATE/attempt.yml`) in the main repo. Paste
your `workspace_id` (never a key), the exact request and response, and what you
expected versus what happened.

If you actually got a win, do not post it in the issue. Email
support@pinkwallet.com with subject starting SECURITY first, per the main README's
responsible disclosure section.

## What's in here

- `attempt.py`: 5 named attempts (over_cap, split, disguised_payee, injection_memo,
  credential_before_approval), each a small function you can copy and change.
  Python 3 standard library only.
- `attempt.sh`: the same over_cap and injection_memo attempts in curl + jq.
- `RESULTS-2026-10-07.md`: real output from running every attempt once against the
  live sandbox, so you know what to expect before you run anything yourself.

Sandbox only, test money only. See the main README's Scope and Rules of play
sections before you start.
