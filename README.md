# PLE entry: Pi on Claude Opus 5.5 with Clash Flag

An entry for the Physical-Engineering's Last Exam harness competition. It is the organizers' [submission template](https://github.com/physical-engineerings-last-exam/submission-template) (the [Pi](https://github.com/badlogic/pi-mono) coding agent calling `google-cloud/claude-opus-5-5`) plus one addition of ours: a small validation layer (`scope_guard.py`). It runs deterministic checks of restrictions an instruction states, and shows the agent what fails them while it can still act.

**Dev score: 0.560** (29 tasks, one run each; 28 delivered, one counts 0). Details and limits are below.

## Clash Flag, the main contribution

**What it is.** When a task asks for an IFC building model and forbids clashes, Clash Flag runs IfcOpenShell's standard clash tree on every IFC file the agent builds, and appends the clashing pairs to the output of the command that built it. A rebuild is re-checked and reported as "N pairs (was M)". It calls no model, never blocks and never edits a file. On tasks without that requirement it is inactive.

**Why it matters.** In the organizers' saved dev-set run, both MEP routing tasks scored 0 on the hard-clash gate. The agent had seen the overlaps: its final messages note that segments of the same service overlap at their joints, and that a check counting those would fail the model. It delivered anyway, on the assumption that they would not count. They count. Clash Flag replaces that assumption with a measurement, taken the way the task states the rule, at the moment the agent builds.

**What happened in the two runs of this harness** (one autonomous run per task, no prompt from us; both are in `artifacts/`):

| | `data-hall-mep-routing` | `data-hall-mep-routing-offset` |
|---|---|---|
| Agent's first build | 23 clashing pairs | 18 clashing pairs |
| After the flag | 0 at the next rebuild (8 model calls, 7 min) | 6, then 4, then 0 (29 model calls, 20 min) |
| What the agent did in between | read IfcOpenShell's clash code, wrote its own clash test, edited its build script | the same, plus 32 two- and three-element test models to find what counts as a clash |
| Task verifier | **0.904**: valid, 0 clashes, connectivity passed | **0.960**: valid, 0 clashes, connectivity passed |
| Organizers' saved run | 0 (23 clashes) | 0 (18 clashes) |
| Cost of the run; of the repair | $18.92; $1.82 | $20.28; $5.30 |

Each agent's `final_message.md` describes the change in its own words.

**What this does not show.** We did not run the agent with the flag switched off, so we cannot show that it would not have found and fixed the clashes by itself. One run per task. The comparison run is the organizers', made with a different agent setup.

**Scope Guard's instruction checks, supplementary.** Two checks of explicit scope restrictions (a numbered unit, a write freeze). They raised no flag in any of the 29 runs, and no score gain is attributed to them.

## Result on the 29 dev tasks

| | Mean of 29 | The two MEP tasks | The other 27 |
|---|---|---|---|
| This entry (one run per task) | **0.560** | 0.904, 0.960 | 0.532 |
| Organizers' saved run (`d988c45`) | 0.491 | 0, 0 | 0.528 |

- **The difference is the MEP pair.** Of the +0.068 difference in the mean, +0.064 comes from the two MEP tasks.
- **No demonstrated difference on the other 27.** Mean paired difference +0.004 (bootstrap 95% interval −0.12 to +0.13); 12 tasks higher, 13 lower, 2 equal. On those tasks Clash Flag was inactive and Scope Guard raised no flag.
- **Not a controlled comparison.** The organizers' run is not a run of this template's harness: it used Harbor's own Pi agent inside the task container, without MCP tools, on another date and API route. Both sides are single runs, and single-task scores move a lot between runs (our two `engineers-estimate-check` runs of behaviour-identical harnesses scored 1.0 and 0.348). Two of the organizers' zeros and one of ours are delivery failures, not engineering results; without those three tasks and the MEP pair, the remaining 24 average 0.532 (ours) and 0.552 (organizers').

| Task | Grading | This entry | Organizers' saved run | Cost | Route |
|---|---|---|---|---|---|
| `data-hall-mep-routing-offset` | checks | 0.960 | 0.000 | $20.28 | V |
| `data-hall-mep-routing` | checks | 0.904 | 0.000 | $18.92 | A |
| `solar-witness-test-package` | rubric | 0.806 | 0.000 | $6.82 | V |
| `foundation-strategy` | checks-judge | 0.795 | 0.000 | $14.29 | V |
| `data-hall-device-takeoff` | checks | 0.965 | 0.383 | $20.48 | V |
| `fire-solve-convergence` | rubric | 0.783 | 0.636 | $10.11 | V |
| `fill-compaction-acceptance` | rubric | 0.759 | 0.676 | $6.86 | V |
| `pre-application-capacity-response` | rubric | 0.282 | 0.231 | $6.26 | V |
| `roof-deck-design` | checks | 0.314 | 0.286 | $35.78 | V |
| `emergency-spillway-check` | rubric | 0.649 | 0.622 | $10.35 | V |
| `wind-diaphragm-shear` | checks | 0.335 | 0.316 | $12.65 | V |
| `footing-settlement-verification` | rubric | 0.548 | 0.532 | $10.18 | V |
| `seismic-diaphragm-shear` | checks | 0.329 | 0.316 | $13.23 | V |
| `mv-conveyance-study` | checks | 0.358 | 0.353 | $17.23 | V |
| `data-center-site-model` | checks | 1.000 | 1.000 | $5.00 | V |
| `solar-supplemental-review` | rubric | 0.208 | 0.208 | $6.76 | V |
| `frame-extension-method` | checks | 0.806 | 0.806 | $11.57 | V |
| `eor-review-corrections` | checks-judge | 0.301 | 0.302 | $14.29 | V |
| `fire-test-validation-memo` | rubric | 0.798 | 0.808 | $8.05 | V |
| `lv-cable-sizing` | checks-judge | 0.878 | 0.907 | $14.42 | V |
| `division-26-specifications` | checks | 0.274 | 0.349 | $16.11 | V |
| `landscape-sheet-revision` | rubric | 0.727 | 0.857 | $9.49 | V |
| `cooling-water-flush-plan` | checks | 0.328 | 0.461 | $17.75 | V |
| `shoring-design-verification` | rubric | 0.369 | 0.516 | $12.63 | V |
| `permission-to-operate-memo` | rubric | 0.727 | 0.909 | $8.41 | V |
| `engineers-estimate-check` | rubric | 0.348 | 0.543 | $8.65 | A |
| `les-mesh-resolution` | rubric | 0.293 | 0.537 | $5.18 | V |
| `heat-rejection-life-cycle-cost` | checks | 0.386 | 0.692 | $16.17 | V |
| `backfeed-energization-reply` | rubric | 0.000 | 1.000 | $2.72 | V |

Scores are each task's own grader in our local kit run. Costs are list price from each call's reported token usage. Route: A = Anthropic API, V = Vertex AI (global endpoint). The 29 kept runs cost $360.64 in all (mean $12.44 per task): 2,478 model calls, 636M prompt tokens (96.5% read from cache), 6.4M output tokens, 22.4 hours of agent time.

## Dev-set artifacts in this commit

`artifacts/` holds **28 of the 29 dev tasks**, each exported by the kit (`eval/run.py`, or `kit artifacts --from` for runs made on another machine) from one run of this harness. Every graded file (`files/` and `final_message.md`) is as exported and matches the hashes in the kit's `manifest.json`, which is unchanged.

- **Model:** `claude-opus-5-5`, the model `submission.yaml` declares, with the harness's own settings. Two tasks were served from a personal Anthropic API key and 27 from Vertex AI, both through a LiteLLM proxy (1.90.0) at the kit's `MODEL_PROXY_URL`.
- **Judges:** the tasks' own programmatic graders; for `rubric` and `checks-judge` tasks, the kit's judge, `claude-opus-5-5`, through the same proxy. The organizers re-grade the artifacts with the official judge, so the scores above are local values.
- **Runs:** one per task (`--trials 1 --attempts 1`), kept as first obtained, with the exceptions listed here.
  - **`backfeed-energization-reply` has no artifact and counts 0.** In both of its runs (the first and one rerun) the model API ended the agent's first long generation with "Output blocked by content filtering policy" before any deliverable was written. Pi does not retry that error, so the harness returned with nothing. We did not create a deliverable by hand. The cause of the block is not established.
  - **`roof-deck-design` (0.314)** was stopped by our own $40 per-task spending cap while the agent was still optimizing; the deliverable it had already written was graded and exported unchanged.
  - **`solar-supplemental-review`** is a second attempt: the first ended on a full disk before any model call.
- **Harness version of two artifacts.** `kit artifacts` warns that `data-hall-mep-routing` and `engineers-estimate-check` were "made by an earlier version of the harness than the one submitted".
  - They were exported at commit `bd733d9` (harness tree `a0a44f50…`); the other 26 at `217269f` (tree `4ec0504c…`).
  - The two commits differ in one harness file, this README: `git diff --stat bd733d9 217269f -- . ':(exclude)artifacts'`. The harness code is byte-identical, and this commit again changes only the README and `artifacts/`.
  - The kit's harness digest includes the README, and the manifest keeps a file list only for the latest run, so the review cannot tell that the earlier tree differs in documentation alone.
  - The kit's rules list this case under "Warned about, then graded as it is" (`docs/artifacts.md`). Clearing the warning would need a re-run of both tasks or an edit of `manifest.json`; we did neither.
- **A key-like string in three tasks' app state.** `kit check` warns of "what looks like an API key" in `wiki_dump.sql` under `permission-to-operate-memo`, `pre-application-capacity-response` and `solar-witness-test-package`. It is the certificate that the task's own wiki server generated inside the task container, exported because `/app/tools/.apps_data/` is one of those tasks' declared deliverables. It is not a credential of ours, and the files are kept as exported.
- **Activity of the validation layer in these runs:** Clash Flag was active on the two MEP tasks and fired on both. Scope Guard recognized a restriction on two other tasks (`engineers-estimate-check`, `fire-test-validation-memo`) and raised no flag. On the remaining 25 tasks the layer was inactive and the relay received the template's own session object.
- **No `trajectory.json`.** The kit's optional, ungraded run records are left out of this commit, because they repeat task instructions and task files from the gated dev set. The manifest does not record them, and nothing the graders read was touched.

## What is whose

- **The organizers' template (Google LLC, Apache-2.0):** every file except the ones below. The first commit of this repository, `d988c45`, is the template unchanged, with the organizers' own saved dev-set artifacts.
- **Ours (Apache-2.0):** `scope_guard.py`, `ifc_clash.py`, `test_scope_guard.py`, `test_clash_flag.py`, `test_harness_wiring.py`, this README, and the changes to `harness.py` (2026-11-22). Those changes create the guard, hand the relay the guard's session proxy, and append the guard's note to the final message.
- **Used, not vendored:** Clash Flag runs [IfcOpenShell](https://ifcopenshell.org)'s standard clash tree (`ifcopenshell.geom`, LGPL-3.0) with the task container's own `python3` and its installed IfcOpenShell. No IfcOpenShell code is in this repository, and the harness installs nothing new.
- **The organizers' saved dev-set run** (the artifacts in `d988c45`, mean 0.491) is theirs. It was made with Harbor's own Pi agent inside the task container, without MCP tools, not with this template's harness.
- **Not in this repository:** the third-party starter harness whose failure motivated Scope Guard, and our analysis of it. Both are in [ple-veriflow-failure-analysis](https://github.com/michi883/ple-veriflow-failure-analysis).

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
| `artifacts/` | Dev-set artifacts: 28 tasks (see above) |
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
- The checker uses the clash tree (overlap of more than 2 mm, or a collision), adds an exact box test for collinear overlaps the tree misses, and excuses floor and ceiling coverings. Pairs of the same class count: two segments of one run that overlap at a joint are a clash.
- Limits: at most 3 files per command, 50 MB each, 120 s per check.
- A model is checked once per version. A clean or unchanged model adds nothing. A file written with `write` or `edit` alone is checked on the next command.
- Cost: no model call; one file scan per command (about 0.2 s) and 1.3–1.4 s per new IFC version (277 elements, under emulation).
- How it was validated: on six saved MEP models (the organizers' two and four we repaired offline) it reports the same clashing pairs as the public grader (23, 18, 3, 2, 0, 0). The geometry rule and its thresholds were checked against that grader during development. The harness never reads a grader or the dev set at run time.

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
| The two MEP dev tasks scored 0 in the organizers' saved run. All 41 clashing pairs (23 + 18) were joints between segments of the same service | The organizers' saved run; the public grader | Diagnosis only |
| On the saved models, the check finds the same 23 and 18 clashing pairs as the public grader. It also matches on 4 models we repaired (3, 2, 0, 0), and raises nothing on the saved `data-center-site-model` IFC | Offline check, no model | The check agrees with the grader |
| A generic trim of the segment ends of the saved models, applied by us, scores 0.920 and 0.934 | **Offline repair by us**, no agent | None: it shows the clash gate was the only obstacle |
| Claude Opus 5.5 rewrote the organizers' saved build scripts itself, given the instruction, the script, the flag text and our request to remove the clashes and keep connectivity. Public grader: 0.920 (two turns, the second after the re-check) and 0.934 (one turn) | **Direct repair replay** through the Anthropic API, outside this harness; single samples, $0.70 | The flag text was the agent's input |
| In the real harness and task container, the flag arrived in the tool result of the build that made the clashes. Re-checks reported 23 → 6 → 0, the deliverable was never modified, and non-IFC tasks were unaffected | **Integration test with a scripted stand-in for the model**, no model calls | Delivery works as designed |
| **`data-hall-mep-routing`: the agent's first build had 23 clashing pairs; it got the flag and repaired its own script. Clean 8 model calls later; verifier 0.904** | **Autonomous run of this harness** (in `artifacts/`); one run, no run without the flag | The flag was the agent's first clash feedback; it then wrote its own test |
| **`data-hall-mep-routing-offset`: first build 18 pairs; after the flag 6, 4, then 0; verifier 0.960** | **Autonomous run of this harness** (in `artifacts/`); one run, no run without the flag | As above; every rebuild was re-checked |
| 29 dev tasks: mean 0.560; organizers' saved run 0.491 | One run per task of this harness; a different agent setup on the organizers' side | Active on 2 of the 29 tasks, which carry nearly all of the difference |
| Scope Guard, replayed on the template's 29 committed dev outputs: it recognizes a restriction in 2 instructions and flags 1 (two rows keyed 3.05 in a check confined to Section 2). In our runs it raised no flag | Offline replay; autonomous runs | — |

**Not measured:**
- the score this harness would get on the MEP tasks with the flag switched off (no ablation);
- run-to-run variance (one run per task);
- any effect of Scope Guard's checks on a score;
- any model other than Claude Opus 5.5;
- IFC tasks other than the two MEP dev tasks.

## Checks and reproduction

Run from the root of the competition kit ([google-research/ple](https://github.com/google-research/ple)), with this repository checked out beside it:

```bash
uv run python -m kit artifacts ../ple-baseline         # the artifact review: 28 usable, 1 missing, the warning described above
uv run python -m kit check ../ple-baseline             # builds and smoke-tests the harness, repeats the review: every stage passes, "ready to submit"
uv run python eval/run.py --artifacts ../ple-baseline  # re-grades the committed artifacts in fresh task containers
uv run python eval/run.py ../ple-baseline --tasks data-hall-mep-routing --trials 1 --attempts 1   # one live run
```

A live run needs a `claude-opus-5-5` endpoint at the kit's `MODEL_PROXY_URL`. Scores of single runs vary; the clash counts the agent starts from, and whether it repairs them, are what to compare with the table above.

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
