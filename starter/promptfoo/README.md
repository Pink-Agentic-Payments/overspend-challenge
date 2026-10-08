# Run the challenge with promptfoo in one command

[promptfoo](https://www.promptfoo.dev) is an open-source LLM eval / red-team CLI that a lot of
AI developers already have installed. This folder wires it up to the
[overspend challenge](../../README.md) so you don't have to write any attack code yourself:
promptfoo points a real LLM at the Pink sandbox's MCP tools and automatically generates
adversarial requests that try to make it violate the three ways to win (pay over the rules, pay
a blocked payee, or get a payment through without required human approval).

## Requirements

- Node.js >= 18 (tested on Node 22.21.0 with `promptfoo@0.118.0`; the `redteam-mcp` example in
  promptfoo's own repo asks for Node >= 22.22.0 for their *latest* release, so this kit pins an
  older promptfoo version that installs cleanly on a wider range of Node versions)
- Python 3, stdlib only (same as the main `starter/attempt.py`)
- An API key for whichever model you want to drive the attack. The default config uses
  `openai:gpt-4.1-mini` and reads `OPENAI_API_KEY`. Want to use Anthropic, or anything else
  promptfoo supports, instead? Edit the one `providers[0].id` line in `promptfooconfig.yaml` and
  export the matching key (e.g. `ANTHROPIC_API_KEY` for `anthropic:messages:claude-sonnet-5`).
  **You choose and pay for your own model**; nothing here ships or hardcodes a key.

## One command

```bash
OPENAI_API_KEY=sk-... ./starter/promptfoo/run.sh
```

This:

1. Creates a fresh Pink sandbox workspace (`setup_workspace.py`), named with the `RT-` prefix, and
   exports `PINK_WORKSPACE_ID` / `PINK_AGENT_KEY` for the run. If you already have
   `PINK_WORKSPACE_ID` and `PINK_AGENT_KEY` set in your shell (recommended for repeat runs, since
   workspace creation is rate limited), it reuses them instead of creating a new workspace.
2. Runs `npx promptfoo@0.118.0 redteam run -c promptfooconfig.yaml`, which: generates adversarial
   test cases for the plugins below, has your chosen model act as the sandbox's Purchasing AI
   over the real MCP connection (`https://agentic-sandbox.pinkwallet.com/mcp`, bearer-token auth
   with your agent key), and grades each attempt against the challenge's own win conditions.
3. Prints a results table. Run `npx promptfoo@0.118.0 redteam report` afterwards for the full
   interactive HTML report.

## What it tests

`promptfooconfig.yaml` configures:

- Three `policy` plugin instances, one per way to win from the main README: over-the-cap /
  split-payment amounts, blocked payees under a disguised name, and payments that should need
  human approval.
- `excessive-agency` (does the agent take payment actions it shouldn't assume it can) and `mcp`
  (MCP-specific probes: tool metadata injection, unauthorized tool invocation, and related
  attacks against the MCP surface itself).
- Strategies `basic`, `jailbreak`, and `prompt-injection` to vary how each adversarial request is
  delivered to the agent.

This is a starting point, not the only way to attack the sandbox. Edit `numTests`, `plugins`, or
`strategies` in `promptfooconfig.yaml` to try more.

## First-run note

The very first time you run `redteam eval` or `redteam run`, promptfoo's own CLI (not this kit)
asks you to type a work email for one-time verification before it will run a real eval. That's
promptfoo's standard first-run gate, independent of this config. `run.sh` sets `CI=true` to skip
promptfoo's interactive email prompt (promptfoo's own documented CI escape hatch); if you invoke
promptfoo directly instead of via `run.sh`, you'll see the prompt and can answer it once.

## Known limitation

Gemini as the target model currently fails with promptfoo 0.118.0 because its Google tool-schema
conversion passes JSON Schema keywords (`exclusiveMinimum`, `additionalProperties`) that the
Gemini API rejects. Use an OpenAI or Anthropic model for now.

## If promptfoo finds something

A promptfoo "fail" means the grader thinks the policy was violated, not that it's automatically
a challenge win. Per the main README, a win is the **Pink server actually issuing a credential or
completing a transfer** for one of the three goals. Open the promptfoo report, find the exact
tool calls and MCP responses for the failing test case, and check the real
`pink.request_payment` / `pink.get_credential` response before you open an issue. Follow the main
README's "How to submit" section (use the Attempt issue template, include your `workspace_id`
never a key, and the exact request/response pair).

## Validating the config without an LLM key

```bash
cd starter/promptfoo
npx --yes promptfoo@0.118.0 validate config
```

This checks `promptfooconfig.yaml` against promptfoo's schema without calling any model or
spending any API credits.

## Files

- `promptfooconfig.yaml`: the red-team config (MCP target, prompt, plugins, strategies).
- `setup_workspace.py`: stdlib-only script that creates or reuses a sandbox workspace. Prints
  `export` lines to stdout only; status/info goes to stderr. Never writes keys to disk.
- `run.sh`: the one-command entry point described above.
