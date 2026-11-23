# PLE entry: Pi on Claude Opus 5.5 with Clash Flag

An entry for the Physical-Engineering's Last Exam harness competition. It is the organizers' [submission template](https://github.com/physical-engineerings-last-exam/submission-template) (the [Pi](https://github.com/badlogic/pi-mono) coding agent calling `google-cloud/claude-opus-5-5`) plus one addition of ours: a small validation layer (`scope_guard.py`). It runs deterministic checks of the restrictions an instruction states, and shows the agent what fails them while it can still act.

**Clash Flag, the main contribution.** When a task asks for an IFC model and forbids clashes, Clash Flag runs IfcOpenShell's standard clash tree on every IFC file the agent builds. It appends the clashing pairs to that command's output.
- **The autonomous run in `artifacts/`.** On `data-hall-mep-routing`, the agent's first build (turn 73) had **23 clashing pairs**. The warning appeared in that build's own output, and the agent investigated and repaired its own build script. The model was clash-free by turn 81, about 7 minutes later.
- **Grade:** the task's verifier scored the final deliverable **0.904**: valid, 0 clashes, connectivity passed. The organizers' saved run of this task scored 0 on the clash gate.
- **Caveat:** one run, with no matched run without the flag, so the score gain caused by the flag is not measured.

**Scope Guard's instruction checks, supplementary.** Two checks of explicit scope restrictions (a numbered unit, a write freeze). No score gain has been measured for them.

All the checks call no model, only flag, and are inactive unless the instruction states the restriction they check. See [Evidence](#evidence-what-each-result-is) for what each result is.

## What is whose

- **The organizers' template (Google LLC, Apache-2.0):** every file except the ones below. The first commit of this repository, `d988c45`, is the template unchanged, with the organizers' own saved dev-set artifacts.
- **Ours (Apache-2.0):** `scope_guard.py`, `ifc_clash.py`, `test_scope_guard.py`, `test_clash_flag.py`, `test_harness_wiring.py`, this README, and the changes to `harness.py` (2026-11-22). Those changes create the guard, hand the relay the guard's session proxy, and append the guard's note to the final message.
- **Used, not vendored:** Clash Flag runs [IfcOpenShell](https://ifcopenshell.org)'s standard clash tree (`ifcopenshell.geom`, LGPL-3.0) with the task container's own `python3` and its installed IfcOpenShell. No IfcOpenShell code is in this repository, and the harness installs nothing new.
- **The organizers' saved dev-set run** (the artifacts in `d988c45`, mean 0.491) is theirs. It was made with Harbor's own Pi agent inside the task container, without MCP tools, not with this template's harness.
- **Not in this repository:** the third-party starter harness whose failure motivated Scope Guard, and our analysis of it. Both are in [ple-veriflow-failure-analysis](https://github.com/michi883/ple-veriflow-failure-analysis).

## Dev-set artifacts in this commit

`artifacts/` holds **2 of 29 dev tasks**, each from one run of this harness (tree `a0a44f50…`, made at commit `bd733d9`; later commits changed only this README), exported by `eval/run.py`. The other 27 dev tasks were not run and count 0, so the **dev score is (0.904 + 0.348) / 29 = 0.043**.

| Task | Score | Agent time | Model calls | Prompt tokens (cached) | Output tokens | Cost at list price |
|---|---|---|---|---|---|---|
| `data-hall-mep-routing` (run `r1b`) | **0.904** (valid, 0 clashes, connectivity passed) | 66 min | 101 | 24.6M (95%) | 408k | $18.92 |
| `engineers-estimate-check` (run `r1a`) | **0.348** (16 of 46 rubric points) | 30 min | 46 | 8.9M (93%) | 195k | $8.65, judge included |

- **Model:** `claude-opus-5-5`, the model `submission.yaml` declares, served for the runs from a personal Anthropic API key through a local LiteLLM proxy (1.90.0).
- **Judges:** the MEP task's own programmatic verifier; for `engineers-estimate-check`, the kit's rubric judge, `claude-opus-5-5`.
- **Clash Flag:** fired once in the MEP run, and the agent acted on it (above). It cannot fire on `engineers-estimate-check`, which has no IFC deliverable.
- **Scope Guard:** active on `engineers-estimate-check` ("confined to Section 2") and raised no flag.
  - That score varies from run to run: an earlier run of this harness before Clash Flag (`81c4e77`), with identical behaviour on this task, scored 1.0. The organizers' saved run scored 0.543.
  - The 1.0 is not this entry's score.
- Each `trajectory.json` is the kit's optional, ungraded record of the run, kept as exported.

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
| `artifacts/` | Dev-set artifacts: two tasks (see above) |
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

| Result | What produced it | Clash Flag's part |
|---|---|---|
| The two MEP dev tasks (`data-hall-mep-routing`, `-offset`) scored 0 in the organizers' saved run. All 41 clashing pairs (23 + 18) were joints between segments of the same service | The organizers' saved run; the public grader | Diagnosis only |
| On the saved models, the check finds the same 23 and 18 clashing pairs as the public grader. It also matches on 4 models we repaired (3, 2, 0, 0), and raises nothing on the saved `data-center-site-model` IFC | Offline check, no model | The check agrees with the grader |
| A generic trim of the segment ends of the saved models, applied by us, scores 0.920 and 0.934 | **Offline repair by us**, no agent | None: it shows the clash gate was the only obstacle |
| Claude Opus 5.5 rewrote the organizers' saved build scripts itself, given the instruction, the script, the flag text and our request to remove the clashes and keep connectivity. Public grader: **0.920** (two turns, the second after the re-check) and **0.934** (one turn) | **Direct repair replay** through the Anthropic API, outside this harness; single samples, $0.70 | The flag text was the agent's input |
| In the real harness and task container, the flag arrived in the tool result of the build that made the clashes. Re-checks reported 23 → 6 → 0, the deliverable was never modified, and non-IFC tasks were unaffected. `kit check` passes | **Integration test with a scripted stand-in for the model**, no model calls | Delivery works as designed |
| **`data-hall-mep-routing`: the agent built a model with 23 clashing pairs, got the flag, and repaired its own script. Clean 8 turns later; verifier 0.904** | **Autonomous run of this harness** (the artifact above); one run, no run without the flag | The flag was the agent's first clash feedback; it then wrote its own test |
| Scope Guard, replayed on the template's 29 committed dev outputs: it recognizes a restriction in 2 instructions and flags 1 (two rows keyed 3.05 in a check confined to Section 2). In our two `engineers-estimate-check` runs it raised no flag | Offline replay; autonomous runs | — |

**Not measured:**
- the score this harness would get on the MEP task without the flag;
- a live run on `data-hall-mep-routing-offset`;
- any effect of Scope Guard's checks on a score;
- any model other than Claude Opus 5.5.

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
