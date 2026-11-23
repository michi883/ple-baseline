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

"""Deterministic tests for scope_guard.py. No model, network or Docker.

    python3 -m unittest test_scope_guard -v

Every fixture is invented. No competition task content is used.
"""

import asyncio
import io
import pathlib
import tempfile
import time
import unittest
import zipfile

import scope_guard

CONFINED = (
    "Check the paving estimate against the drawings. Stay in Section 4, but add"
    " anything the drawings show that the estimate misses. Save the memo as"
    " out/memo.docx."
)
HEADER = ["Item", "Description", "Qty", "Unit price", "Amount"]
INSIDE = [
    ["4.10", "Aggregate base, 6 in", "22.02 CY", "$9.25", "$203.69"],
    ["4.12", "Asphalt, 3 in", "310.5 SY", "$14.00", "$4,347.00"],
    ["4.31", "Curb, type B", "120 LF", "$21.50", "$2,580.00"],
]
OUTSIDE = ["5.02", "Guard rail, priced from another section", "40 LF", "$38.00", "$1,520.00"]


def docx(*tables):
  """Builds a minimal .docx holding the given tables."""
  def cell(text):
    return f"<w:tc><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc>"
  body = "".join(
      "<w:tbl>" + "".join("<w:tr>" + "".join(cell(c) for c in row) + "</w:tr>" for row in rows) + "</w:tbl>"
      for rows in tables
  )
  xml = (
      '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
      f'wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
  )
  out = io.BytesIO()
  with zipfile.ZipFile(out, "w") as archive:
    archive.writestr("word/document.xml", xml)
  return out.getvalue()


def xlsx(rows):
  """Builds a minimal .xlsx with one sheet of inline strings."""
  def cell(r, c, text):
    return f'<c r="{chr(65 + c)}{r + 1}" t="inlineStr"><is><t>{text}</t></is></c>'
  data = "".join(
      f'<row r="{r + 1}">' + "".join(cell(r, c, t) for c, t in enumerate(row)) + "</row>"
      for r, row in enumerate(rows)
  )
  xml = (
      '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
      f'spreadsheetml/2006/main"><sheetData>{data}</sheetData></worksheet>'
  )
  out = io.BytesIO()
  with zipfile.ZipFile(out, "w") as archive:
    archive.writestr("xl/worksheets/sheet1.xml", xml)
  return out.getvalue()


def codes(rows):
  return [row.code for row in rows]


class DirectiveTest(unittest.TestCase):

  def test_explicit_confinement_is_recognized(self):
    d = scope_guard.parse(CONFINED)
    self.assertEqual((d.kind, d.allowed), ("section", frozenset({4})))
    self.assertEqual(
        d.unit_quote,
        "Stay in Section 4, but add anything the drawings show that the estimate misses.",
    )

  def test_other_explicit_phrasings(self):
    for text, allowed in [
        ("The review is limited to Sections 2 and 3.", {2, 3}),
        ("Do not go outside Division 26.", {26}),
        ("Check Parts 3 through 5 only.", {3, 4, 5}),
        ("Please keep to Schedule 7.", {7}),
    ]:
      self.assertEqual(scope_guard.parse(text).allowed, frozenset(allowed), text)

  def test_statements_that_are_not_restrictions_are_ignored(self):
    for text in [
        "Section 2 has been checked against the plans.",
        "The allowances remain in Section 9.",
        "The scope is not limited to Section 2.",
        "Stay in touch with the architect.",
        "See Section 2.03 only for the unit price.",
        "Part 2 only applies to the steel frame.",
        "Use engineering judgment on the pipe sizes.",
    ]:
      self.assertFalse(scope_guard.parse(text).active, text)

  def test_freeze_is_recognized_only_as_an_instruction(self):
    for text in [
        "Write the memo from what is on the server; nothing else on it needs changing.",
        "Do not modify any other file.",
        "Leave everything else untouched.",
    ]:
      self.assertTrue(scope_guard.parse(text).freeze_quote, text)
    for text in [
        "Nothing else has changed since the last revision.",
        "Do not change the units.",
    ]:
      self.assertFalse(scope_guard.parse(text).active, text)


class UnitCheckTest(unittest.TestCase):
  allowed = frozenset({4})

  def check(self, name, data):
    return codes(scope_guard.check_file(name, data, self.allowed))

  def test_prohibited_row_is_caught(self):
    rows = scope_guard.check_file("memo.docx", docx([HEADER] + INSIDE + [OUTSIDE]), self.allowed)
    self.assertEqual(codes(rows), ["5.02"])
    self.assertEqual(rows[0].label, "Guard rail, priced from another section")

  def test_legitimate_table_is_allowed(self):
    # quantities ("22.02 CY"), prices ("$9.25") and amounts are not item numbers
    self.assertEqual(self.check("memo.docx", docx([HEADER] + INSIDE)), [])

  def test_same_result_in_every_table_format(self):
    rows = [HEADER] + INSIDE + [OUTSIDE]
    pipe = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    pipe = pipe.replace("\n", "\n|---|---|---|---|---|\n", 1)
    comma = "\n".join(",".join(f'"{c}"' for c in r) for r in rows)
    self.assertEqual(self.check("book.xlsx", xlsx(rows)), ["5.02"])
    self.assertEqual(self.check("memo.md", pipe.encode()), ["5.02"])
    self.assertEqual(self.check("lines.csv", comma.encode()), ["5.02"])

  def test_key_column_may_follow_a_row_number(self):
    rows = [["No."] + HEADER] + [[str(i)] + r for i, r in enumerate(INSIDE + [OUTSIDE], 1)]
    self.assertEqual(self.check("memo.docx", docx(rows)), ["5.02"])

  def test_ambiguous_cases_are_not_flagged(self):
    rollup = [
        ["Roll-up", "Amount"],
        ["Section 3 (unchanged)", "$504,191.75"],
        ["Section 4 (corrected)", "$7,130.69"],
        ["Sections 5 through 8 (unchanged)", "$3,075,440.00"],
    ]
    cited = [
        ["Item", "What the drawings show", "Closest schedule item"],
        ["4.40 Gate", "Swing gate, chain link", "10.06 gate is tubular steel"],
        ["4.42 Riprap", "Grouted, 12 in", "5.02 is loose stone"],
    ]
    everything = [HEADER] + [[f"{s}.{i:02d}", "line", "1", "$1", "$1"] for s in range(1, 9) for i in (1, 2)]
    one_key = [HEADER, INSIDE[0], OUTSIDE]
    prose = b"We considered pricing the rail like item 5.02 but did not.\n"
    for name, data in [
        ("rollup.docx", docx(rollup)),  # other units named, none keyed
        ("cited.docx", docx(cited)),  # another unit's item cited outside the key column
        ("all.docx", docx(everything)),  # a full listing: the unit is a minority
        ("one.docx", docx(one_key)),  # too little to call it a key column
        ("notes.md", prose),  # prose, no table
        ("drawing.pdf", b"%PDF-1.7 4.10 5.02"),  # a format the guard cannot read
        ("broken.docx", b"not a zip file"),
    ]:
      self.assertEqual(self.check(name, data), [], name)


class LocalSession:
  """A task session backed by a local directory and the real shell."""

  def __init__(self, workdir, instruction, left=None, fail_on=None):
    self.workdir, self.instruction = str(workdir), instruction
    self.left, self.fail_on, self.fail_read = left, fail_on, None
    self.commands, self.logs = [], []

  def time_left(self):
    return self.left

  async def log(self, text):
    self.logs.append(text)

  async def exec(self, command, timeout_sec=120):
    self.commands.append(command)
    if self.fail_on and self.fail_on in command:
      raise RuntimeError("the container refused the command")
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=self.workdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return {"exit_code": proc.returncode, "output": out.decode(), "truncated": False, "timed_out": False}

  async def read_file(self, path):
    if self.fail_read and self.fail_read in path:
      raise RuntimeError("the container refused the read")
    return pathlib.Path(path).read_bytes()


class RuntimeTest(unittest.IsolatedAsyncioTestCase):

  def setUp(self):
    self._tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(self._tmp.name).resolve()
    self.work, self.stage, self.marks = root / "work", root / "stage", root / "marks"
    for d in (self.work / "out", self.stage, self.marks):
      d.mkdir(parents=True)

  def tearDown(self):
    self._tmp.cleanup()

  async def start(self, instruction, **kwargs):
    session = LocalSession(self.work, instruction, **kwargs)
    scope_guard.Guard.MARKER_DIR = str(self.marks)  # keep the marker out of /tmp
    self.addCleanup(setattr, scope_guard.Guard, "MARKER_DIR", "/tmp")
    guard = scope_guard.Guard(session)
    await guard.start()
    time.sleep(0.05)  # files written next are newer than the marker
    return session, guard, guard.wrap(session)

  async def test_inactive_without_an_explicit_restriction(self):
    session, guard, relay_session = await self.start("Size the pump and save pump.md.")
    self.assertFalse(guard.active)
    self.assertIs(relay_session, session)  # the relay gets the template's own session
    self.assertEqual(session.commands, [])  # and the guard ran nothing
    self.assertEqual(await guard.final_note(), "")

  async def test_flag_arrives_with_the_command_that_wrote_the_file(self):
    session, guard, relay_session = await self.start(CONFINED)
    (self.stage / "bad.docx").write_bytes(docx([HEADER] + INSIDE + [OUTSIDE]))
    result = await relay_session.exec(f"cp {self.stage}/bad.docx out/memo.docx && echo saved")
    self.assertTrue(result["output"].startswith("saved\n"))
    self.assertIn("[scope guard]", result["output"])
    self.assertIn('"Stay in Section 4, but add anything', result["output"])
    self.assertIn("out/memo.docx has table rows keyed to item numbers outside Section 4: 5.02", result["output"])
    again = await relay_session.exec("echo next")
    self.assertEqual(again["output"], "next\n")  # shown once
    self.assertIn("outside Section 4: 5.02", await guard.final_note())  # still standing

  async def test_a_corrected_file_clears_the_flag(self):
    _, guard, relay_session = await self.start(CONFINED)
    (self.stage / "bad.docx").write_bytes(docx([HEADER] + INSIDE + [OUTSIDE]))
    (self.stage / "good.docx").write_bytes(docx([HEADER] + INSIDE))
    await relay_session.exec(f"cp {self.stage}/bad.docx out/memo.docx")
    result = await relay_session.exec(f"cp {self.stage}/good.docx out/memo.docx && echo fixed")
    self.assertEqual(result["output"], "fixed\n")
    self.assertEqual(await guard.final_note(), "")

  async def test_legitimate_file_is_never_flagged(self):
    _, guard, relay_session = await self.start(CONFINED)
    (self.stage / "good.docx").write_bytes(docx([HEADER] + INSIDE))
    result = await relay_session.exec(f"cp {self.stage}/good.docx out/memo.docx && echo saved")
    self.assertEqual(result["output"], "saved\n")
    self.assertEqual(await guard.final_note(), "")

  async def test_freeze_flags_only_unnamed_preexisting_files(self):
    (self.work / "Tracker.csv").write_text("a,b\n")
    (self.work / "Calc sheet.csv").write_text("a,b\n")
    instruction = (
        "Update the Tracker and write out/reply.md from what is on the server;"
        " nothing else on it needs changing."
    )
    _, guard, relay_session = await self.start(instruction)
    result = await relay_session.exec(
        "echo x >> Tracker.csv; echo x >> 'Calc sheet.csv'; echo hi > out/reply.md; echo done"
    )
    # the named Tracker and the new reply.md are not listed
    self.assertIn("not named in the instruction: Calc sheet.csv.\n", result["output"])
    self.assertIn("Calc sheet.csv", await guard.final_note())

  async def test_guard_that_cannot_start_turns_itself_off(self):
    session, guard, relay_session = await self.start(CONFINED, fail_on="touch")
    self.assertFalse(guard.active)
    self.assertIs(relay_session, session)
    self.assertIn("scope guard: off", session.logs[-1])

  async def test_guard_that_breaks_mid_run_leaves_output_untouched(self):
    session, guard, relay_session = await self.start(CONFINED)
    session.fail_on = "cksum"
    result = await relay_session.exec("echo still works")
    self.assertEqual(result["output"], "still works\n")
    self.assertFalse(guard.active)
    self.assertEqual(await guard.final_note(), "")

  async def test_one_unreadable_file_does_not_stop_the_guard(self):
    session, guard, relay_session = await self.start(CONFINED)
    bad = docx([HEADER] + INSIDE + [OUTSIDE])
    (self.stage / "locked.docx").write_bytes(bad)
    (self.stage / "bad.docx").write_bytes(bad)
    session.fail_read = "locked"
    result = await relay_session.exec(
        f"cp {self.stage}/locked.docx out/locked.docx; cp {self.stage}/bad.docx out/memo.docx"
    )
    self.assertTrue(guard.active)
    self.assertIn("out/memo.docx has table rows", result["output"])
    self.assertNotIn("locked.docx", result["output"])

  async def test_no_scan_when_the_task_is_nearly_out_of_time(self):
    session, _, relay_session = await self.start(CONFINED, left=10)
    before = len(session.commands)
    await relay_session.exec("echo late")
    self.assertEqual(len(session.commands), before + 1)  # only the command itself


if __name__ == "__main__":
  unittest.main()
