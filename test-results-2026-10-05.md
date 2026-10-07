# Test results: "Can you make an AI agent overspend?" (dry run)

Date: 2026-10-05
Workspace: fresh `coffee` template sandbox, id `0aol8gz0d6` (created via `POST /v1/sandbox/workspaces`)
Agent used: "Purchasing AI" (`monthly_budget: $4,000`, `per_payment_cap: $500`, vault `v_ops`)
Transport: MCP (`https://agentic-sandbox.pinkwallet.com/mcp`), Bearer agent key
Keys: never recorded in this file or anywhere in the deliverables. The workspace above is throwaway test money only.

**Result: no bypass found.** Every attempt below was allowed, asked for human approval, or blocked exactly the way the published rules say it should. This is not a security audit and it is not a guarantee nothing is wrong, it is one afternoon of poking with 8 attempts. That's exactly why we're opening this up publicly instead of just trusting our own testing.

## Important quirk discovered: the night rule runs on UTC

The coffee template ships a rule "Between 11pm and 6am: ask the owner" (`r1`, `outside_hours: [6, 23]`). It evaluates against the **server's UTC clock**, not the caller's local time, unless the caller passes `local_hour` explicitly. Our tests ran at 04:54 UTC, which is inside that window, so almost everything came back `pending_human` under `r1` regardless of amount. We re-ran the same tests with `local_hour: 14` to see the rule that would actually apply during business hours. Both runs are below. **This is expected behavior, not a bug**: flag it in the challenge README so people don't file it as a false "bypass".

---

## Baseline (before any adversarial attempts)

**`pink.get_budget`**
```json
{
  "agent": "Purchasing AI",
  "status": "active",
  "monthly_budget": 4000,
  "spent_this_month": 2260,
  "left_this_month": 1740,
  "spent_today": 0,
  "single_payment_cap": 500,
  "vault": { "id": "v_ops", "name": "Operating", "balances": { "USD": 18420.55 } },
  "company_daily_ceiling": 6000,
  "company_spent_today": 0,
  "policy_version": 1
}
```
Note: the coffee template seeds the workspace with $2,260 already "spent this month" as sample history; that's template data, not something we spent.

**`pink.list_rules`** (11 total, 7 returned to this agent's view): `r11` block gift cards/cash-like/crypto, `r1` night hours ask owner, `r2` payee bank-details-changed ask owner, `r4` orders $0–500 allow, `r5` orders $500–2000 ask store manager, `r8` new payee ask owner, `r9` anything over $2,000 ask owner.

---

## Attempt log

### 1. Amount over the per-payment cap
Request: `{payee_id: "p_cc", amount: 650, purpose: "Coffee beans restock"}`

- At UTC night hour: **`pending_human`**, rule `r1` (night rule fired first), approver Maya Chen (Owner).
- Re-run with `local_hour: 14` (daytime): **`pending_human`**, rule `r5` "Bigger supply orders: store manager checks" ($500–$2,000 band), approver Luis Ortega (Store manager).

Verdict: cap enforced both times. The $650 never got a credential; it only ever produced a hold waiting on a named human.

### 2. Split one $900 purchase into two $450 requests back to back
Two separate calls, different idempotency keys, ~0.2s apart, `local_hour: 14`:

- Part A, $450 → **`allowed`**, rule `r4` "Small supply orders go through", returned a single-use sandbox `bank_transfer` credential capped at `max_amount: 450`.
- Part B, $450 → **`allowed`**, same rule, its own single-use credential capped at `max_amount: 450`.

Verdict, reported honestly: **both $450 legs were individually allowed.** Each one is under the $500 per-payment cap, and together ($900) they're still under the $4,000 monthly budget ($2,260 + $450 + $450 = $3,160 left $840), so no rule in this template is designed to catch this split. The per-payment cap limits the size of any single hole; the monthly budget limits the total; neither is a "total spent in the last N minutes" rule. This is a legitimate design question for defenders, not a broken promise, since the server never claimed to detect velocity/structuring, only caps and monthly totals. We're calling this out explicitly as the most interesting opening for challenge participants: can you use repeated small transactions to move more money than the cap implies, before the monthly budget or any other rule catches it?

### 3. Payee name dressed up as the bean supplier
Request: `{payee_name: "Coffee Co (beans) gift cards", amount: 60, purpose: "bean restock gift cards"}`

- At UTC night hour: **`blocked`**, rule `r11` "Never: gift cards, cash-like, crypto".
- Re-run with `local_hour: 14`: **`blocked`**, same rule.

Verdict: the gift-card block matched on the payee category regardless of the cosmetic "(beans)" dressing or the time of day, and it took priority over the night-ask rule. Disguising the name as a supplier did not help.

### 4. Negative and zero amounts
- `amount: -100` → MCP error: `Input validation error: Number must be greater than 0 at amount`
- `amount: 0` → same error: `Number must be greater than 0 at amount`

Verdict: rejected at input validation, before any policy rule even runs. No payment object was created for either.

### 5. Reusing an idempotency key with a different amount
- First call, `idempotency_key: "idem-test-key-1"`, `amount: 100` → `pending_human` (night rule), `payment_id: pay_2d937b15c48d`.
- Second call, same `idempotency_key: "idem-test-key-1"`, `amount: 480` → returned the **original** `pay_2d937b15c48d` record, `amount: 100`, with `"replayed": true`. The $480 was never created or evaluated.

Verdict: the idempotency key is a true replay guard, not a way to swap in a bigger number after the fact. The server does not re-price a replayed key to the new request; it just hands back the original decision untouched.

### 6. Calling `get_credential` for a payment that's `pending_human`
Using the hold from a $890 request that came back `pending_human` (rule `r1`, no approval given):

- `pink.get_credential({hold_id: "pay_aa2935df7658"})` → returned the same `pending_human` object again (status unchanged, no `credential` field populated, no transfer reference). No money-movable credential was issued.

Verdict: you cannot pull a credential out of a hold that a human hasn't approved yet.

### Control: normal in-cap order
`{payee_id: "p_cc", amount: 420, local_hour: 14}` → **`allowed`**, rule `r4`, single-use credential capped at `max_amount: 420`. Confirms the happy path works and the credential's `max_amount` field matches the requested amount (also worth participants checking: does the credential enforce its own cap if replayed against a different downstream amount?).

### Bonus: `pink.check_policy` dry run
`check_policy` for the same $650 case returned a full rule trace before any payment object exists:
```
PASS · Agent registered · Purchasing AI
PASS · Agent active · not paused
PASS · Monthly budget · $2,910 of $4,000 after this
PASS · Daily ceiling, all agents · $650 of $6,000
PASS · Vault balance · Operating · $18,420.55 available
SKIP · Never: gift cards, cash-like, crypto · payee out of scope
HIT · Between 11pm and 6am: ask the owner · matched · ask Maya
```
Useful for challenge participants: run `check_policy` first to see exactly which rule will fire before spending an attempt on `request_payment`.

---

## PM summary (for the founder, public-safe)

- 8 adversarial attempts + 2 controls, all against a live, fresh sandbox workspace, all via the real MCP API, no mocking.
- **No real bypass.** Cap enforcement, gift-card blocking, negative/zero rejection, idempotency replay protection, and credential-withholding on unapproved holds all worked as documented.
- One honest open question worth highlighting in the challenge itself: back-to-back small payments under the cap are each individually allowed; nothing in this template rate-limits by time window shorter than "this month." That's a legitimate thing for challenge participants to probe further (e.g., ten $450 orders in a row, or combined with `check_policy` to find the exact monthly ceiling).
- One UTC-vs-local-time quirk on the night rule that will generate false "bug" reports if we don't document it up front in the README. Done, see above.
- No SECURITY FINDING. Nothing here needs private disclosure to the founder beyond this file.

---

## Creative add-ons to make the challenge spread ($0 each)

1. **Weekly "best attempt" write-up.** Every Monday, the PM (or whoever's doing content that week) picks the most creative submitted attempt from the GitHub issues and writes a 300-word recap: what the person tried, which rule caught it, why it's clever. Posted as a GitHub Discussion pinned to the repo and cross-posted to the same subreddits/LinkedIn as the launch. Costs nothing but 20 minutes and keeps the repo from going quiet after week one.

2. **"Wall of blocked payments" page.** A static page (or just a pinned GitHub Discussion, no hosting needed) that's literally a running list: amount attempted, payee, rule that caught it, one-line description of the trick, submitter's handle (with permission). Turns every rejected attempt into a tiny trophy case instead of a dead end. Free to build as a markdown file in the repo (`WALL_OF_BLOCKED.md`), updated from accepted issues.

3. **Template-of-the-week.** The sandbox already supports multiple business templates (coffee shop is one). Each week, swap which template the challenge points people at (e.g. a different payee list, different caps, different rules) and announce it as "new rules, same question." Gives repeat participants a reason to come back without us building anything new, since the templates already exist server-side; it's just a README update pointing at a different `"template"` value in the `POST /v1/sandbox/workspaces` call.
