# Copyright 2026 michi883
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deterministic tests for check 3 of scope_guard.py (IFC clashes). No model, network or Docker.

    python3 -m unittest test_clash_flag -v

Most tests replace the task container's `python3` with a stand-in that returns
canned clash results, so they need no IfcOpenShell. The geometry tests run the
real `ifc_clash.py` and are skipped unless IFC_PYTHON names a Python with
`ifcopenshell==0.8.4.post1` (the version the MEP task images pin). With
CLASH_FIXTURES set to a folder of saved models (see `GraderMatchTest`), they
also compare against the counts the public grader reported for those models.

Every instruction and the synthetic model are invented. No competition task
content is used.
"""

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import scope_guard
import test_scope_guard

IFC_PYTHON = os.environ.get("IFC_PYTHON", "")
FIXTURES = pathlib.Path(os.environ.get("CLASH_FIXTURES", "/nonexistent"))
HERE = pathlib.Path(__file__).resolve().parent

ROUTING = """# Route the chilled-water main through the plant room, clash-free

## Constraints
- **No hard clashes**: a solid that overlaps another by more than 2 mm
  anywhere (a pipe through a beam) fails the review. Beams are full depth.
- Deliver an IFC4 model built with ifcopenshell, saved as out/model.ifc.
"""

# The stand-in for the task container's python3. Probe: prints a version, or
# fails like a container without IfcOpenShell. Check: every "IFC file" holds
# the canned result ifc_clash.py would print for it.
FAKE_PYTHON = '''#!{python}
import json, sys
args = sys.argv[1:]
if "-c" in args:
    print("ifcopenshell 0.8.4.post1" if {available} else "ModuleNotFoundError: No module named 'ifcopenshell'")
    sys.exit(0 if {available} else 1)
sys.stdin.read()
paths = [a for a in args if a not in ("-I", "-")]
print("@@ifc-clash@@" + json.dumps({{"version": "stand-in", "files": {{p: json.load(open(p)) for p in paths}}}}))
'''


def result(*pairs, excused=0):
  """A canned ifc_clash.py result for one file."""
  listed = [[a, b, depth, [1000 * i, 0, 0]] for i, (a, b, depth) in enumerate(pairs)]
  return json.dumps({"elements": 50, "pairs": len(listed), "excused": excused, "listed": listed})


JOINT = ("IfcPipeSegment 'CHW-01'", "IfcPipeSegment 'CHW-02'", 57)
BEAM = ("IfcBeam 'B-3'", "IfcPipeSegment 'CHW-04'", None)


class DirectiveTest(unittest.TestCase):

  def test_clash_restriction_in_an_ifc_task_is_recognized(self):
    d = scope_guard.parse(ROUTING)
    self.assertTrue(d.active)
    self.assertEqual(
        d.clash_quote,
        "No hard clashes: a solid that overlaps another by more than 2 mm anywhere"
        " (a pipe through a beam) fails the review.",
    )

  def test_other_explicit_phrasings(self):
    for text in [
        "Build the IFC model clash-free.",
        "Write model.ifc; the ducts must not clash with the steel.",
        "The IFC4 model must be free of clashes.",
        "Save the IFC file with zero collisions.",
    ]:
      self.assertTrue(scope_guard.parse(text).clash_quote, text)

  def test_no_clash_check_without_both_an_ifc_model_and_a_restriction(self):
    for text in [
        "Build the IFC model of the hall and save it as out/model.ifc.",  # no restriction
        "Route the ducts with no clashes and report the lengths.",  # no IFC deliverable
        "The IFC drawings show no clashes with the existing ducts.",  # issued for construction
        "No clash detection is required for the IFC model.",
    ]:
      self.assertFalse(scope_guard.parse(text).clash_quote, text)


class Base(unittest.IsolatedAsyncioTestCase):
  """A workdir, a scratch dir and a guard whose python3 is the stand-in (or a real one)."""

  def setUp(self):
    self._tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(self._tmp.name).resolve()
    self.root = root
    self.work, self.stage, self.marks, self.scratch = (
        root / "work", root / "stage", root / "marks", root / "scratch")
    for d in (self.work / "out", self.stage, self.marks, self.scratch):
      d.mkdir(parents=True)

  def tearDown(self):
    self._tmp.cleanup()

  def fake_python(self, available=True):
    path = self.root / ("python-ok" if available else "python-missing")
    path.write_text(FAKE_PYTHON.format(python=sys.executable, available=available))
    path.chmod(0o755)
    return str(path)

  async def start(self, instruction, python=None, **kwargs):
    session = test_scope_guard.LocalSession(self.work, instruction, **kwargs)
    for name, value in (
        ("MARKER_DIR", str(self.marks)),
        ("SCRATCH_DIRS", (str(self.scratch),)),
        ("PYTHON", python or self.fake_python()),
    ):
      self.addCleanup(setattr, scope_guard.Guard, name, getattr(scope_guard.Guard, name))
      setattr(scope_guard.Guard, name, value)
    guard = scope_guard.Guard(session)
    await guard.start()
    time.sleep(0.05)  # files written next are newer than the marker
    return session, guard, guard.wrap(session)

  def stage_model(self, name, content):
    (self.stage / name).write_text(content)
    return self.stage / name


class RuntimeTest(Base):

  async def test_flag_arrives_with_the_command_that_built_the_model(self):
    _, guard, relay = await self.start(ROUTING)
    model = self.stage_model("bad.ifc", result(JOINT, BEAM))
    out = (await relay.exec(f"cp {model} {self.scratch}/trial.ifc && echo built"))["output"]
    self.assertTrue(out.startswith("built\n\n[scope guard] Automatic geometry check"), out)
    self.assertIn('The instruction says: "No hard clashes: a solid that overlaps', out)
    self.assertIn(f"{self.scratch}/trial.ifc: 2 pairs of elements whose solids overlap", out)
    self.assertIn("Pairs of the same class, such as two segments of one run", out)
    self.assertIn("IfcPipeSegment 'CHW-01' x IfcPipeSegment 'CHW-02' (57 mm deep at 0, 0, 0 mm)", out)
    self.assertIn("IfcBeam 'B-3' x IfcPipeSegment 'CHW-04' (collision at 1000, 0, 0 mm)", out)
    self.assertEqual((await relay.exec("echo next"))["output"], "next\n")  # shown once
    self.assertEqual(await guard.final_note(), "")  # a trial file in scratch is not a deliverable

  async def test_rebuilds_report_progress_and_the_deliverable_reaches_the_final_note(self):
    _, guard, relay = await self.start(ROUTING)
    bad = self.stage_model("bad.ifc", result(JOINT, BEAM))
    half = self.stage_model("half.ifc", result(JOINT))
    good = self.stage_model("good.ifc", result(excused=3))
    await relay.exec(f"cp {bad} out/model.ifc")
    out = (await relay.exec(f"cp {half} out/model.ifc"))["output"]
    self.assertIn("out/model.ifc: 1 pair of elements whose solids overlap (was 2), all listed before.", out)
    note = await guard.final_note()
    self.assertIn("finds elements whose solids overlap in: out/model.ifc (1 pair).", note)
    out = (await relay.exec(f"cp {good} out/model.ifc && echo fixed"))["output"]
    self.assertIn("out/model.ifc: no clashing pairs now (was 1).", out)
    self.assertNotIn("correct the model", out)  # an all-clear gives no advice
    self.assertEqual(await guard.final_note(), "")

  async def test_only_the_file_just_built_is_reported(self):
    _, _, relay = await self.start(ROUTING)
    many = [(f"IfcPipeSegment 'P-{i:02d}'", f"IfcPipeSegment 'P-{i + 1:02d}'", 10) for i in range(15)]
    model = self.stage_model("many.ifc", result(*many))
    first = (await relay.exec(f"cp {model} {self.scratch}/trial.ifc"))["output"]
    self.assertIn("; and 3 more not listed yet.", first)
    second = (await relay.exec(f"cp {model} out/model.ifc"))["output"]
    self.assertNotIn("trial.ifc", second)  # unchanged: not reported again
    self.assertIn("out/model.ifc: 15 pairs of elements whose solids overlap", second)
    self.assertIn("Pairs not listed before: IfcPipeSegment 'P-12' x IfcPipeSegment 'P-13'", second)

  async def test_clean_model_and_unchanged_model_add_nothing(self):
    session, _, relay = await self.start(ROUTING)
    good = self.stage_model("good.ifc", result())
    self.assertEqual((await relay.exec(f"cp {good} out/model.ifc && echo ok"))["output"], "ok\n")
    checks = sum("ifc_clash" in c or "SCOPE_GUARD_IFC" in c for c in session.commands)
    await relay.exec("echo again")
    self.assertEqual(sum("SCOPE_GUARD_IFC" in c for c in session.commands), checks)  # not re-checked

  async def test_without_ifcopenshell_the_check_is_off_and_says_so(self):
    session, guard, relay = await self.start(ROUTING, python=self.fake_python(available=False))
    self.assertFalse(guard.active)
    self.assertIs(relay, session)  # the relay gets the template's own session
    self.assertTrue(any("IFC clash check OFF" in line and "No module named" in line for line in session.logs))

  async def test_inactive_without_an_ifc_clash_restriction(self):
    session, guard, relay = await self.start("Build the IFC model of the hall as out/model.ifc.")
    self.assertFalse(guard.active)
    self.assertIs(relay, session)
    self.assertEqual(session.commands, [])

  async def test_unreadable_output_is_logged_and_not_flagged(self):
    session, guard, relay = await self.start(ROUTING)
    broken = self.stage_model("broken.ifc", "this is not JSON")
    out = (await relay.exec(f"cp {broken} out/model.ifc && echo saved"))["output"]
    self.assertEqual(out, "saved\n")
    self.assertTrue(guard.active)
    self.assertTrue(any("IFC clash check gave no result" in line for line in session.logs))

  async def test_text_checks_still_work_beside_the_clash_check(self):
    instruction = ROUTING + "Stay in Section 4.\n"
    _, _, relay = await self.start(instruction)
    table = [test_scope_guard.HEADER] + test_scope_guard.INSIDE + [test_scope_guard.OUTSIDE]
    (self.stage / "memo.docx").write_bytes(test_scope_guard.docx(table))
    model = self.stage_model("bad.ifc", result(BEAM))
    out = (await relay.exec(f"cp {self.stage}/memo.docx out/memo.docx; cp {model} out/model.ifc"))["output"]
    self.assertIn("[scope guard] Automatic check by the harness", out)
    self.assertIn("outside Section 4: 5.02", out)
    self.assertIn("out/model.ifc: 1 pair of elements", out)


# --- Real IfcOpenShell -----------------------------------------------------------

BOXES = [
    # (class, name, predefined type, x, y, z, dx, dy, dz): centre of the base, size (mm)
    ("IFCCOLUMN", "C-1", ".COLUMN.", 0, 0, 0, 400, 400, 3000),
    ("IFCPIPESEGMENT", "P-THROUGH-COLUMN", ".RIGIDSEGMENT.", 0, 0, 2000, 2000, 100, 100),  # clash
    ("IFCPIPESEGMENT", "P-A", ".RIGIDSEGMENT.", 5000, 0, 2000, 1000, 100, 100),
    ("IFCPIPESEGMENT", "P-B", ".RIGIDSEGMENT.", 5950, 0, 2000, 1000, 100, 100),  # 50 mm joint overlap
    ("IFCPIPESEGMENT", "P-C", ".RIGIDSEGMENT.", 10000, 0, 2000, 1000, 100, 100),
    ("IFCPIPESEGMENT", "P-D", ".RIGIDSEGMENT.", 11005, 0, 2000, 1000, 100, 100),  # 5 mm gap
    ("IFCPIPESEGMENT", "P-E", ".RIGIDSEGMENT.", 15000, 0, 2000, 1000, 100, 100),
    ("IFCPIPESEGMENT", "P-F", ".RIGIDSEGMENT.", 16000, 0, 2000, 1000, 100, 100),  # exact abut
    ("IFCCOVERING", "FLOOR", ".FLOORING.", 20000, 0, -50, 2000, 2000, 50),
    ("IFCPIPESEGMENT", "P-THROUGH-FLOOR", ".RIGIDSEGMENT.", 20000, 0, -200, 100, 100, 400),  # excused
    ("IFCCOVERING", "ROOF", ".ROOFING.", 25000, 0, 2000, 2000, 2000, 50),
    ("IFCPIPESEGMENT", "P-THROUGH-ROOF", ".RIGIDSEGMENT.", 25000, 0, 1800, 100, 100, 400),  # clash
]
EXPECTED = {
    ("IfcColumn 'C-1'", "IfcPipeSegment 'P-THROUGH-COLUMN'"),
    ("IfcPipeSegment 'P-A'", "IfcPipeSegment 'P-B'"),
    ("IfcCovering 'ROOF'", "IfcPipeSegment 'P-THROUGH-ROOF'"),
}


def synthetic_ifc() -> str:
  """An invented IFC4 file of boxes (mm units), written as plain STEP text."""
  lines = [
      "#1=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);",
      "#2=IFCUNITASSIGNMENT((#1));",
      "#3=IFCCARTESIANPOINT((0.,0.,0.));",
      "#4=IFCAXIS2PLACEMENT3D(#3,$,$);",
      "#5=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#4,$);",
      "#6=IFCPROJECT('0000000000000000000000',$,'Synthetic',$,$,$,$,(#5),#2);",
      "#7=IFCGEOMETRICREPRESENTATIONSUBCONTEXT('Body','Model',*,*,*,*,#5,$,.MODEL_VIEW.,$);",
      "#8=IFCDIRECTION((0.,0.,1.));",
  ]
  n = 10
  for i, (cls, name, kind, x, y, z, dx, dy, dz) in enumerate(BOXES):
    guid = f"{i + 1:022d}"
    lines += [
        f"#{n}=IFCCARTESIANPOINT(({x:.1f},{y:.1f},{z:.1f}));",
        f"#{n + 1}=IFCAXIS2PLACEMENT3D(#{n},$,$);",
        f"#{n + 2}=IFCLOCALPLACEMENT($,#{n + 1});",
        f"#{n + 3}=IFCRECTANGLEPROFILEDEF(.AREA.,$,$,{dx:.1f},{dy:.1f});",
        f"#{n + 4}=IFCEXTRUDEDAREASOLID(#{n + 3},$,#8,{dz:.1f});",
        f"#{n + 5}=IFCSHAPEREPRESENTATION(#7,'Body','SweptSolid',(#{n + 4}));",
        f"#{n + 6}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{n + 5}));",
        f"#{n + 7}={cls}('{guid}',$,'{name}',$,$,#{n + 2},#{n + 6},$,{kind});",
    ]
    n += 10
  return (
      "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION((''),'2;1');\n"
      "FILE_NAME('synthetic.ifc','',(''),(''),'','','');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n"
      + "\n".join(lines)
      + "\nENDSEC;\nEND-ISO-10303-21;\n"
  )


def run_checker(*paths):
  out = subprocess.run(
      [IFC_PYTHON, "-I", str(HERE / "ifc_clash.py"), *map(str, paths)],
      capture_output=True, text=True, timeout=300, check=True,
  ).stdout
  line = next(l for l in out.splitlines() if l.startswith(scope_guard.CLASH_TAG))
  return json.loads(line[len(scope_guard.CLASH_TAG) :])


@unittest.skipUnless(IFC_PYTHON, "set IFC_PYTHON to a Python with ifcopenshell")
class GeometryTest(Base):

  def test_synthetic_model(self):
    path = self.stage / "synthetic.ifc"
    path.write_text(synthetic_ifc())
    found = run_checker(path)["files"][str(path)]
    self.assertEqual({(p[0], p[1]) for p in found["listed"]}, EXPECTED)
    self.assertEqual((found["pairs"], found["excused"], found["elements"]), (3, 1, len(BOXES)))
    self.assertEqual(run_checker(path), run_checker(path))  # deterministic

  async def test_end_to_end_with_the_real_checker(self):
    _, guard, relay = await self.start(ROUTING, python=IFC_PYTHON)
    self.stage_model("synthetic.ifc", synthetic_ifc())
    out = (await relay.exec(f"cp {self.stage}/synthetic.ifc out/model.ifc && echo built"))["output"]
    self.assertIn("out/model.ifc: 3 pairs of elements whose solids overlap", out)
    self.assertIn("IfcColumn 'C-1' x IfcPipeSegment 'P-THROUGH-COLUMN'", out)
    self.assertNotIn("P-THROUGH-FLOOR", out)
    self.assertIn("out/model.ifc (3 pairs)", await guard.final_note())
    written = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())
    self.assertEqual(  # the check writes nothing; only the marker files sit outside workdir
        [p for p in written if not p.startswith(("marks/", "stage/", "python-"))], ["work/out/model.ifc"])


# Saved models: <CLASH_FIXTURES>/<task>/<model>.ifc, with the clash count the
# public grader reported for each (offline, 2026-11-23).
GRADER_COUNTS = {
    ("mep-routing", "saved"): 23,
    ("mep-routing", "trim_abut"): 3,
    ("mep-routing", "trim_5mm"): 0,
    ("mep-routing-offset", "saved"): 18,
    ("mep-routing-offset", "trim_abut"): 2,
    ("mep-routing-offset", "trim_5mm"): 0,
}


@unittest.skipUnless(IFC_PYTHON and FIXTURES.is_dir(), "set IFC_PYTHON and CLASH_FIXTURES")
class GraderMatchTest(unittest.TestCase):

  def test_counts_match_the_grader(self):
    paths = {k: FIXTURES / k[0] / f"{k[1]}.ifc" for k in GRADER_COUNTS}
    found = run_checker(*paths.values())["files"]
    got = {k: found[str(p)]["pairs"] for k, p in paths.items()}
    self.assertEqual(got, GRADER_COUNTS)

  def test_held_out_site_model_raises_nothing(self):
    found = run_checker(FIXTURES / "site-model" / "saved.ifc")["files"]
    self.assertEqual([v["pairs"] for v in found.values()], [0])


if __name__ == "__main__":
  unittest.main()
