# PLE entry: Pi on Claude Opus 5.5 with Clash Flag

An entry for the Physical-Engineering's Last Exam harness competition. It is the organizers' [submission template](https://github.com/physical-engineerings-last-exam/submission-template) (the [Pi](https://github.com/badlogic/pi-mono) coding agent calling `google-cloud/claude-opus-5-5`) plus one addition of ours: a small validation layer (`scope_guard.py`) that runs deterministic checks of the restrictions an instruction states, and shows the agent what fails them while it can still act.

- **Clash Flag, the main contribution.** When a task asks for an IFC model and forbids clashes, it reports the pairs of elements whose solids overlap. It targets a failure that zeroed two dev tasks. Repairs prompted by the flag score 0.920 and 0.934 on those tasks with the public grader, but in replays: see [Evidence](#evidence-what-each-result-is) for what each result is.
- **Scope Guard's instruction checks, supplementary.** Two checks of explicit scope restrictions (a numbered unit, a write freeze). No score gain has been measured for them.

Both call no model, only flag, and are inactive unless the instruction states the restriction they check.

## What is whose

- **The organizers' template (Google LLC, Apache-2.0):** every file except the ones below. The first commit of this repository, `d988c45`, is the template unchanged, with the organizers' own dev-set artifacts.
- **Ours (Apache-2.0):** `scope_guard.py`, `ifc_clash.py`, `test_scope_guard.py`, `test_clash_flag.py`, `test_harness_wiring.py`, this README, and the changes to `harness.py` (2026-11-22). Those changes create the guard, hand the relay the guard's session proxy, and append the guard's note to the final message.
- **Used, not vendored:** Clash Flag runs [IfcOpenShell](https://ifcopenshell.org)'s standard clash tree (`ifcopenshell.geom`, LGPL-3.0) with the task container's own `python3` and its installed IfcOpenShell. No IfcOpenShell code is in this repository, and the harness installs nothing new.
- **Not in this repository:** the third-party starter harness whose failure motivated Scope Guard, and our analysis of it. Both are in [ple-veriflow-failure-analysis](https://github.com/michi883/ple-veriflow-failure-analysis).

## Dev-set artifacts in this commit

**Pending re-export.** The artifact below was made by the previous version of this harness (`81c4e77`, before Clash Flag). Clash Flag is inactive on that task, which has no IFC deliverable. Even so, the rules require artifacts exported by the submitted harness, so it has to be re-run before this commit is submitted.

`artifacts/` holds **one task of 29**: `engineers-estimate-check`, from a single run of the previous harness (run `my-harness-20261122-203043`, exported by `eval/run.py`). The other 28 dev tasks were not run and count 0, so the dev score is 1.0 / 29 = 0.034. The organizers' artifacts for the other tasks were removed because this harness did not produce them.

- Local score on that task: 1.0 (46 of 46 rubric points). Judge: `claude-opus-5-5`.
- Model: `claude-opus-5-5`, the model `submission.yaml` declares, served for the run from a personal Anthropic API key through a local LiteLLM proxy.
- Usage: 9.42M input tokens (93% cached), 176k output tokens, 26 min 45 s of agent time, about $8.50 at list price.
- **Scope Guard was active in that run and raised no flag**: the agent never wrote a row outside the section the instruction confines it to. The score is therefore not evidence that the guard works.
  - The same model scored 0.543 on this task in the organizers' saved dev-set run (the artifacts in this repository's first commit).
  - That run used Harbor's own Pi agent inside the task container, without MCP tools, not this template's harness.

## Files

| File | Purpose |
|---|---|
| `submission.yaml` | The model, and the install and start commands |
| `serve.py` | The WebSocket endpoint: hands each task to `harness.solve` |
| `harness.py` | Runs Pi on each task. Edit `NOTE` (prompt), `THINKING`, or `UNKNOWN_MODEL` (limits for a model Pi doesn't know) |
| `task-tools.ts` | Points Pi's `read`, `write`, `edit` and `bash` tools at the task container |
| `taskbridge.py` | The competition protocol |
| `scope_guard.py` | The validation layer: Clash Flag and Scope Guard's instruction checks (see below) |
| `ifc_clash.py` | Clash Flag's checker, sent to the task container's `python3` |
| `test_clash_flag.py`, `test_scope_guard.py`, `test_harness_wiring.py` | Their tests |
| `package.json`, `package-lock.json` | Pi 1.1.0 and every package it uses, pinned. To upgrade, edit `package.json`, run `npm install --package-lock-only`, commit both |
| `artifacts/` | Dev-set artifacts: one task (see above) |
| `AGENTS.md` | The full rules, for a coding agent working on your entry |

## The validation layer (ours, not part of the template)

Everything in this repository is the organizers' template except `scope_guard.py`, `ifc_clash.py`, the three test files and the lines in `harness.py` that call the guard.

| Check | Runs when the instruction says | Flags |
|---|---|---|
| **Clash Flag** | an IFC model is asked for and clashes are forbidden, e.g. "the model must be clash-free" | Pairs of elements whose solids overlap in an IFC file written in the working directory or `/tmp`, by IfcOpenShell's clash tree: more than 2 mm, or a collision. It gives counts by class and the pairs, and after a rebuild, the new count ("was N") |
| Unit confinement (Scope Guard) | the work is confined to a numbered unit, e.g. "Stay in Section 2" | Table rows, in a file the agent wrote, keyed to item numbers under another unit (3.05), when the same column keys at least as many rows under the allowed unit |
| Write freeze (Scope Guard) | nothing else is to change | Files that existed before the run, were modified, and are not named in the instruction |

**Where it sits.** `harness.py` hands the relay a thin proxy of the task session. After each command the agent runs, the proxy checks what changed since the start, with one or more extra commands in the task container, and appends any new flag to that command's output. The model therefore sees the flag in the same tool result as the command that caused it, while it can still act. A flag that still stands when the agent stops is added to the final message for the person who reads it.

**Clash Flag in detail.**
- At the start, the guard checks that the task container's `python3` can import `ifcopenshell.geom`. If it cannot, the check turns off and says so in the log.
- After each command it checksums the IFC files changed since the start, and runs `ifc_clash.py` (sent on standard input, `python3 -I -`) on new versions only.
- Limits: at most 3 files per command, 50 MB each, 120 s per check.
- A model is checked once per version. A clean or unchanged model adds nothing. A file written with `write` or `edit` alone is checked on the next command.

**Scope Guard in detail.** The proxy reads the changed `.docx`, `.xlsx`, `.md`, `.txt`, `.csv` and `.tsv` files for the unit check, and compares the start-of-run file list for the freeze.
- It does not check:
  - restrictions phrased differently;
  - restrictions on anything other than numbered units and file changes;
  - files it cannot read as tables (PDF, images).
- **How it differs from the rule gate we tested and rejected.** That gate asked the model to quote a rule and its evidence for every decision, checked the quotes in code, and replaced the decision when they failed. Held out, it fixed 1 decision, broke 2 and doubled the cost. The guard reads the file the agent wrote, not the model's account of its reasoning; it adds no model call; and it cannot change an answer.

**What it does not do.** Nothing is blocked and no deliverable is edited: whether a flagged item is wrong is left to the model and the reader. Without one of the recognized phrasings the layer is inactive: no extra command, no change to the prompt, and the relay receives the template's own session object. If one of its own commands fails, it turns itself off.

## Evidence: what each result is

None of the results below is an autonomous run of this harness with the model on an MEP task. That run has not been done.

| Result | What produced it | Clash Flag's part |
|---|---|---|
| The two MEP dev tasks (`data-hall-mep-routing`, `-offset`) scored 0 in the organizers' saved run. Every clash was a joint between segments of the same service | The organizers' run; the public grader | Diagnosis only |
| On the saved models, the check finds the same 23 and 18 clashing pairs as the public grader. It also matches on 4 models we repaired (3, 2, 0, 0), and raises nothing on the saved `data-center-site-model` IFC | Offline check, no model | The check agrees with the grader |
| A generic trim of the segment ends of the saved models, applied by us, scores 0.920 and 0.934 | **Offline repair by us**, no agent | None: it shows the clash gate was the only obstacle |
| Claude Opus 5.5 rewrote the saved build script itself, from the instruction, the script and the flag text, plus our request to remove the clashes and keep connectivity. Public grader: **0.920** (two turns, the second after the re-check) and **0.934** (one turn) | **Agent-repair replay** through the Anthropic API, outside this harness; single samples, $0.70 | The flag text was the agent's input |
| In the real harness and task container, the flag arrived in the tool result of the build that made the clashes. Re-checks reported the new counts (23, then 6, then 0), the deliverable was never modified, and non-IFC tasks were unaffected. `kit check` passes | **Integration test with a scripted stand-in for the model**, no model calls | Delivery works as designed |
| Scope Guard, replayed on the template's 29 committed dev outputs: it recognizes a restriction in 2 instructions and flags 1 (two rows keyed 3.05 in a check confined to Section 2) | Offline replay, no model | — |

**Not tested yet:**
- whether the model, in a live run of this harness, acts on the flag mid-run, and the dev score that results;
- any effect of Scope Guard's checks on a score.

## Tests

```bash
python3 -m unittest test_scope_guard -v      # 18 tests; no model, network or Docker
python3 -m unittest test_clash_flag -v       # 15 tests; the checker tests need IFC_PYTHON (ifcopenshell 0.8.4.post1) and CLASH_FIXTURES, else they skip
python3 -m unittest test_harness_wiring -v   # 4 tests; real harness.solve and relay, stand-in agent; needs websockets
```

Scope Guard's unit check is covered by these cases:
- a prohibited row is caught;
- a legitimate table passes;
- seven ambiguous cases are not flagged: other units only named, another unit's item cited outside the key column, a full listing, too few keys, prose, an unreadable format, a broken file.

The table rule is weak on its own. In the other tasks' outputs, 5 of 15 tables with a numbered key column mix unit numbers legitimately (clause references, quantities). That is why it runs only under an explicit confinement.
