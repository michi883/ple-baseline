# PLE entry: Pi on Claude Opus 5.5 with Scope Guard

An entry for the Physical-Engineering's Last Exam harness competition. It is the organizers' [submission template](https://github.com/physical-engineerings-last-exam/submission-template) (the [Pi](https://github.com/badlogic/pi-mono) coding agent calling `google-cloud/claude-opus-5-5`) plus one addition of ours, Scope Guard.

## What is whose

- **The organizers' template (Google LLC, Apache-2.0):** every file except the ones below. The first commit of this repository, `d988c45`, is the template unchanged, with the organizers' own dev-set artifacts.
- **Ours (Apache-2.0):** `scope_guard.py`, `test_scope_guard.py`, `test_harness_wiring.py`, this README, and the changes to `harness.py` (2026-11-22: it creates the guard, hands the relay the guard's session proxy, and appends the guard's note to the final message).
- **Not in this repository:** the third-party starter harness whose failure motivated the guard, and our analysis of it. Both are in [ple-veriflow-failure-analysis](https://github.com/michi883/ple-veriflow-failure-analysis).

## Dev-set artifacts in this commit

`artifacts/` holds **one task of 29**: `engineers-estimate-check`, from a single run of this harness (run `my-harness-20261122-203043`, exported by `eval/run.py`). The other 28 dev tasks were not run and count 0, so the dev score is 1.0 / 29 = 0.034. The organizers' artifacts for the other tasks were removed because this harness did not produce them.

- Local score on that task: 1.0 (46 of 46 rubric points). Judge: `claude-opus-5-5`.
- Model: `claude-opus-5-5`, the model `submission.yaml` declares, served for the run from a personal Anthropic API key through a local LiteLLM proxy.
- Usage: 9.42M input tokens (93% cached), 176k output tokens, 26 min 45 s of agent time, about $8.50 at list price.
- **Scope Guard was active in that run and raised no flag**: the agent never wrote a row outside the section the instruction confines it to. The score is therefore not evidence that the guard works. The same model scored 0.543 on this task in the organizers' run of the unmodified template.

## Files

| File | Purpose |
|---|---|
| `submission.yaml` | The model, and the install and start commands |
| `serve.py` | The WebSocket endpoint: hands each task to `harness.solve` |
| `harness.py` | Runs Pi on each task. Edit `NOTE` (prompt), `THINKING`, or `UNKNOWN_MODEL` (limits for a model Pi doesn't know) |
| `task-tools.ts` | Points Pi's `read`, `write`, `edit` and `bash` tools at the task container |
| `taskbridge.py` | The competition protocol |
| `scope_guard.py`, `test_scope_guard.py`, `test_harness_wiring.py` | Scope Guard and its tests (see below) |
| `package.json`, `package-lock.json` | Pi 1.1.0 and every package it uses, pinned. To upgrade, edit `package.json`, run `npm install --package-lock-only`, commit both |
| `artifacts/` | Dev-set artifacts: one task (see above) |
| `AGENTS.md` | The full rules, for a coding agent working on your entry |

## Scope Guard (our addition, not part of the template)

Everything in this repository is the organizers' template except `scope_guard.py`, the two test files and the lines in `harness.py` that call the guard. The failure analysis that motivated it is in [ple-veriflow-failure-analysis](https://github.com/michi883/ple-veriflow-failure-analysis).

The guard makes two deterministic checks of restrictions an instruction states explicitly. It calls no model and it only flags.

| Check | Runs when the instruction says | Flags |
|---|---|---|
| Unit confinement | the work is confined to a numbered unit, e.g. "Stay in Section 2" | table rows, in a file the agent wrote, keyed to item numbers under another unit (3.05), when the same column keys at least as many rows under the allowed unit |
| Write freeze | nothing else is to change | files that existed before the run, were modified, and are not named in the instruction |

**Where it sits.** `harness.py` hands the relay a thin proxy of the task session. After each command the agent runs, the proxy lists the files changed since the start (one extra command in the task container), reads the changed `.docx`, `.xlsx`, `.md`, `.txt`, `.csv` and `.tsv` files, and appends any new flag to that command's output. The model therefore sees the flag in the same tool result as the write, while it can still act. A flag that still stands when the agent stops is added to the final message for the person who reads it.

**What it does not do.** Nothing is blocked and no deliverable is edited: whether a flagged row is wrong is left to the model and the reader. Without one of the recognized phrasings the guard is inactive: no extra command, no change to the prompt, and the relay receives the template's own session object. It does not check restrictions phrased differently, restrictions on anything other than numbered units and file changes, or files it cannot read as tables (PDF, images). If one of its own commands fails, it turns itself off.

**How it differs from the rule gate we tested and rejected.** That gate asked the model to quote a rule and its evidence for every decision, checked the quotes in code, and replaced the decision when they failed. Held out, it fixed 1 decision, broke 2 and doubled the cost. The guard reads the file the agent wrote, not the model's account of its reasoning; it adds no model call; and it cannot change an answer.

**What is tested, and what is not.**

```bash
python3 -m unittest test_scope_guard -v      # 18 tests; no model, network or Docker
python3 -m unittest test_harness_wiring -v   # 2 tests; real harness.solve and relay, stand-in agent; needs websockets
```

- A prohibited row is caught, a legitimate table passes, and seven ambiguous cases are not flagged (other units only named, another unit's item cited outside the key column, a full listing, too few keys, prose, an unreadable format, a broken file).
- Replayed offline on the template's 29 committed dev outputs, the guard recognizes a restriction in 2 instructions and raises flags in 1: two rows keyed 3.05 in a check confined to Section 2.
- The table rule is weak on its own: in the other tasks' outputs, 5 of 15 tables with a numbered key column mix unit numbers legitimately (clause references, quantities). That is why it runs only under an explicit confinement.
- **Not tested:** the guard has not run with a model or on the dev set. Whether a flag changes what the model does, or any score, is unknown.
