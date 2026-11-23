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

"""Scope Guard: deterministic checks of explicit task restrictions.

This file is not part of the organizers' template. It adds two checks, and both
only flag. Neither blocks an action or changes a deliverable.

1. Unit confinement. When the instruction confines the work to a numbered unit
   ("Stay in Section 2"), and a table in a file the agent wrote keys its rows
   by item numbers under that unit (2.35, 2.38), rows of that key column that
   are numbered under another unit (3.05) are flagged.
2. Write freeze. When the instruction says nothing else is to change, files
   that existed before the run, were modified, and are not named in the
   instruction are flagged.

A flag is appended to the output of the command that follows the write, so the
model sees it while it can still act. A flag that still stands when the agent
stops is added to the final message for the person who reads it.

What the guard does not do: it calls no model, it does not judge whether a
flagged row is wrong, and it stays inactive (no extra command, no changed
prompt) unless the instruction contains one of the phrasings below. Restrictions
phrased any other way, restrictions on anything but numbered units and file
changes, and files it cannot read as tables (PDF, images) are not checked.
"""

from __future__ import annotations

import asyncio
import csv
import dataclasses
import io
import posixpath
import re
import secrets
import shlex
from typing import Any
from xml.etree import ElementTree
import zipfile

# --- 1. Directives read from the instruction ---------------------------------

KINDS = "section|division|part|chapter|article|schedule|group|category"
_UNIT = (
    rf"(?P<kind>{KINDS})s?\s+"
    r"(?P<labels>\d{1,3}(?:\s*(?:,|and|or|&|through|thru|to|-|–)\s*\d{1,3})*)"
    r"(?!\.?\d)"
)
_NOT = r"(?:do\s+not|don['’]t|never|must\s+not|should\s+not)"
# An imperative only: "Stay in Section 2", not "the allowances remain in
# Section 9".
_CLAUSE = r"(?:^|[.;:!?\n]\s*|,\s*|\b(?:and|but|so|please)\s+)"
CONFINE = [
    re.compile(p, re.I)
    for p in (
        _CLAUSE
        + r"(?:stay|keep|remain)\s+(?:strictly\s+|only\s+|entirely\s+)?"
        r"(?:in|within|inside|to)\s+(?:the\s+)?" + _UNIT,
        r"\b(?:limit|confine|restrict)(?:ed)?\b[^.;:!?\n]{0,60}?\bto\s+(?:the\s+)?"
        + _UNIT,
        rf"\b{_NOT}\s+(?:go|stray|reach|work|look|price|change\s+anything"
        r"|touch\s+anything)\s+(?:outside|beyond)(?:\s+of)?\s+(?:the\s+)?"
        + _UNIT,
        # "Check Parts 3 through 5 only.", not "Part 2 only applies to steel"
        r"\b" + _UNIT + r"\s+only(?=\s*(?:[.,;:!?)]|$|(?:and|but)\b))",
    )
]
_CHANGE = r"(?:chang|modif|edit|alter|touch|updat|revis|overwrit)\w*"
FREEZE = [
    re.compile(p, re.I)
    for p in (
        r"\bnothing\s+else\b[^.;:!?\n]{0,40}?\b(?:needs?|should|must|may|can"
        r"|is\s+to|are\s+to)\s+(?:to\s+)?(?:be\s+)?" + _CHANGE,
        rf"\b{_NOT}\s+{_CHANGE}\s+(?:anything\s+else|any\s+other\s+\w+"
        r"|(?:the\s+)?other\s+(?:file|document|sheet|workbook|drawing)s)",
        r"\bleave\s+(?:everything|all)\s+else\s+"
        r"(?:as\s+(?:it\s+)?is|alone|unchanged|untouched)",
    )
]


@dataclasses.dataclass(frozen=True)
class Directives:
  """The explicit restrictions recognized in one instruction."""

  kind: str = ""  # "section"
  allowed: frozenset[int] = frozenset()  # {2}
  unit_quote: str = ""  # the instruction sentence that confines the unit
  freeze_quote: str = ""  # the instruction sentence that freezes other files

  @property
  def active(self) -> bool:
    return bool(self.allowed or self.freeze_quote)

  @property
  def unit(self) -> str:
    return f"{self.kind.capitalize()} {_join(sorted(self.allowed))}"


def _join(numbers: list[int]) -> str:
  parts = [str(n) for n in numbers]
  return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _sentence(text: str, pos: int) -> str:
  """Returns the sentence of `text` that contains offset `pos`."""
  start = 0
  for m in re.finditer(r"(?<=[.!?])\s+|\n+", text):
    if m.start() >= pos:
      return " ".join(text[start : m.start()].split())[:400]
    start = m.end()
  return " ".join(text[start:].split())[:400]


def _labels(text: str) -> set[int]:
  """Expands "2", "2 and 3" or "3 through 5" into the numbers it names."""
  out, last, ranging = set(), None, False
  for token in re.findall(r"\d{1,3}|through|thru|to|-|–", text.lower()):
    if token.isdigit():
      n = int(token)
      out.update(range(last, n + 1) if ranging and last is not None and n - last < 100 else [n])
      last, ranging = n, False
    else:
      ranging = True
  return out


def parse(instruction: str) -> Directives:
  """Finds the confinement and freeze directives an instruction states."""
  kind, allowed, unit_quote, freeze_quote = "", set(), "", ""
  for pattern in CONFINE:
    for m in pattern.finditer(instruction):
      # "not limited to Section 2" confines nothing
      if re.search(r"(?:\bnot|n['’]t)\s*$", instruction[max(0, m.start() - 6) : m.start()], re.I):
        continue
      kind = kind or m.group("kind").lower()
      allowed |= _labels(m.group("labels"))
      unit_quote = unit_quote or _sentence(instruction, m.start("kind"))
  for pattern in FREEZE:
    m = pattern.search(instruction)
    if m:
      freeze_quote = _sentence(instruction, m.start() + 1)
      break
  return Directives(kind, frozenset(allowed), unit_quote, freeze_quote)


# --- 2. Tables in a written file ----------------------------------------------

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TABLE_SUFFIXES = (".docx", ".docm", ".xlsx", ".xlsm", ".md", ".txt", ".csv", ".tsv")
MAX_XML = 32 * 1024 * 1024


def _xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
  if archive.getinfo(name).file_size > MAX_XML:
    raise ValueError(f"{name} is too large to check")
  return ElementTree.fromstring(archive.read(name))


def _docx(data: bytes) -> list[list[list[str]]]:
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
    root = _xml(archive, "word/document.xml")
  return [
      [
          [
              "\n".join(
                  "".join(t.text or "" for t in p.iter(_W + "t"))
                  for p in cell.iter(_W + "p")
              ).strip()
              for cell in row.findall(_W + "tc")
          ]
          for row in table.findall(_W + "tr")
      ]
      for table in root.iter(_W + "tbl")
  ]


def _column(ref: str) -> int:
  index = 0
  for ch in ref:
    if not ch.isalpha():
      break
    index = index * 26 + ord(ch.upper()) - 64
  return max(index - 1, 0)


def _xlsx(data: bytes) -> list[list[list[str]]]:
  out = []
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
    names = archive.namelist()
    shared = []
    if "xl/sharedStrings.xml" in names:
      for item in _xml(archive, "xl/sharedStrings.xml").findall(_S + "si"):
        shared.append("".join(t.text or "" for t in item.iter(_S + "t")))
    for name in sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)):
      rows = []
      for row in _xml(archive, name).iter(_S + "row"):
        cells = {}
        for cell in row.findall(_S + "c"):
          if cell.get("t") == "inlineStr":
            text = "".join(t.text or "" for t in cell.iter(_S + "t"))
          else:
            value = cell.find(_S + "v")
            text = (value.text or "") if value is not None else ""
            if cell.get("t") == "s" and text.isdigit() and int(text) < len(shared):
              text = shared[int(text)]
          cells[_column(cell.get("r") or "")] = text.strip()
        if cells and max(cells) < 512:
          rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
      out.append(rows)
  return out


def _pipes(text: str) -> list[list[list[str]]]:
  """Reads Markdown-style pipe tables."""
  out, rows = [], []
  for line in text.splitlines() + [""]:
    line = line.strip()
    if line.count("|") >= 2:
      cells = [c.strip() for c in line.strip("|").split("|")]
      if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
        rows.append(cells)
    elif rows:
      out.append(rows)
      rows = []
  return out


def tables(name: str, data: bytes) -> list[list[list[str]]]:
  """Returns the tables of a file as rows of cell text, or [] if unreadable."""
  suffix = posixpath.splitext(name)[1].lower()
  if suffix in (".docx", ".docm"):
    return _docx(data)
  if suffix in (".xlsx", ".xlsm"):
    return _xlsx(data)
  text = data.decode("utf-8", "replace")
  if suffix in (".csv", ".tsv"):
    return [list(csv.reader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else ","))]
  if suffix in (".md", ".txt"):
    return _pipes(text)
  return []


# --- 3. Check 1: rows keyed outside the confined unit ---------------------------

# An item number at the start of a cell: "2.35", "**3.05** (added)". Not money
# ("$9.25"), not a percentage ("2.5%"), not a bracketed value ("(0.70 ft)").
_CODE = re.compile(r"^[\s*_`~]{0,3}((\d{1,3})\.\d{1,3}(?:\.\d{1,3})*)(?!\d|\s*%)")


@dataclasses.dataclass(frozen=True)
class Row:
  code: str  # "3.05"
  label: str  # the row's next non-empty cell, usually its description


def outside_rows(table: list[list[str]], allowed: frozenset[int]) -> list[Row]:
  """Returns the rows whose key is an item number under another unit.

  The key column is the first of the table's two leftmost columns that holds at
  least two item numbers. It counts only when at least two of its numbers are
  under an allowed unit and they are not outnumbered. A table of prices,
  quantities or dates, or a full listing of every unit, therefore flags
  nothing.

  Args:
    table: Rows of cell text.
    allowed: Unit numbers the instruction confines the work to.
  """
  for column in range(2):
    keyed = []
    for row in table:
      m = _CODE.match(row[column]) if column < len(row) else None
      if m:
        others = [c for c in row[column + 1 :] if c.strip()]
        label = " ".join((others[0] if others else "").split())[:70].strip()
        keyed.append((int(m.group(2)), m.group(1), label))
    if len(keyed) < 2:
      continue
    inside = sum(1 for major, _, _ in keyed if major in allowed)
    outside = [k for k in keyed if k[0] not in allowed]
    if inside >= 2 and inside >= len(outside):
      return [Row(code, label) for _, code, label in outside]
    return []
  return []


def check_file(name: str, data: bytes, allowed: frozenset[int]) -> list[Row]:
  """Runs check 1 on one file. An unreadable file yields no flag."""
  try:
    found = tables(name, data)
  except Exception:  # pylint: disable=broad-exception-caught
    return []
  rows: list[Row] = []
  for table in found:
    for row in outside_rows(table, allowed):
      # the same line repeated in a second table is one finding
      if not any(r.code == row.code and r.label[:20] == row.label[:20] for r in rows):
        rows.append(row)
  return rows


# --- 4. Check 2: pre-existing files modified under a freeze ----------------------


def named(path: str, instruction: str) -> bool:
  """True if the instruction names the file (by file name, with or without suffix)."""
  text = instruction.lower()
  base = posixpath.basename(path).lower()
  stem = posixpath.splitext(base)[0]
  return base in text or (len(stem) >= 4 and stem in text)


# --- 5. Runtime: flag in the tool result, then in the final message --------------

SEPARATOR = "@@scope-guard@@"
MAX_FILE_KB = 8192
MAX_FILES = 25
MAX_LISTED = 8


class Guard:
  """Runs the checks for one task session.

  All of its failures are swallowed: a guard that cannot run turns itself off
  and the harness continues as the template does.
  """

  MARKER_DIR = "/tmp"  # in the task container, outside the deliverables

  def __init__(self, session: Any):
    self.session = session
    try:
      self.directives = parse(session.instruction)
    except Exception:  # pylint: disable=broad-exception-caught
      self.directives = Directives()
    self.active = self.directives.active
    self._marker = f"{self.MARKER_DIR}/.scope-guard-{secrets.token_hex(6)}"
    self._lock = asyncio.Lock()
    self._sums: dict[str, str] = {}  # path -> cksum of the version checked
    self._rows: dict[str, list[Row]] = {}  # path -> standing check-1 flags
    self._frozen: list[str] = []  # standing check-2 flags
    self._told: set[tuple[str, ...]] = set()  # flags already shown to the model

  def wrap(self, session: Any) -> Any:
    """Returns the session the relay should use: a proxy only when active."""
    return GuardedSession(session, self) if self.active else session

  async def start(self) -> None:
    """Marks the start of the run inside the task container."""
    if not self.active:
      return
    root, marker = shlex.quote(self.session.workdir), shlex.quote(self._marker)
    listing = (
        f"find {root} -xdev -type f > {marker}.list 2>/dev/null; "
        if self.directives.freeze_quote
        else ""
    )
    try:
      result = await self.session.exec(f"{listing}touch {marker} && echo ok", 60)
      if "ok" not in (result.get("output") or ""):
        raise RuntimeError("could not write the start marker")
      d = self.directives
      await self.session.log(
          "scope guard: active"
          + (f"; confined to {d.unit}" if d.allowed else "")
          + ("; other files frozen" if d.freeze_quote else "")
      )
    except Exception as exc:  # pylint: disable=broad-exception-caught
      await self._off(exc)

  async def _off(self, exc: BaseException) -> None:
    if type(exc).__name__ == "Cancelled":
      raise exc
    self.active = False
    try:
      await self.session.log(f"scope guard: off ({type(exc).__name__}: {exc})"[:300])
    except Exception:  # pylint: disable=broad-exception-caught
      pass

  async def _poll(self) -> None:
    """Refreshes the standing flags from the files changed since the start."""
    root, marker = shlex.quote(self.session.workdir), shlex.quote(self._marker)
    command = (
        f"find {root} -xdev -type f -newer {marker} ! -size +{MAX_FILE_KB}k"
        " -exec cksum {} + 2>/dev/null | head -n 400"
    )
    if self.directives.freeze_quote:
      command += (
          f"; echo {SEPARATOR}; find {root} -xdev -type f -newer {marker}"
          f" 2>/dev/null | grep -Fxf {marker}.list | head -n 100"
      )
    result = await self.session.exec(command, 30)
    if result.get("timed_out"):
      raise RuntimeError("the file scan timed out")
    changed, _, frozen = (result.get("output") or "").partition(SEPARATOR)
    if self.directives.allowed:
      sums = {}
      for line in changed.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[2].lower().endswith(TABLE_SUFFIXES):
          sums[parts[2]] = parts[0] + " " + parts[1]
      complete = changed.count("\n") < 400  # head did not cut the listing
      for path in list(self._rows):
        if path not in sums and complete:  # the file is gone
          del self._rows[path]
          self._sums.pop(path, None)
      for path in list(sums)[:MAX_FILES]:
        if self._sums.get(path) != sums[path]:
          try:
            data = await self.session.read_file(path)
          except Exception as exc:  # pylint: disable=broad-exception-caught
            if type(exc).__name__ == "Cancelled":
              raise
            data = b""  # one unreadable file does not stop the guard
          self._sums[path] = sums[path]
          self._rows[path] = check_file(path, data, self.directives.allowed)
    self._frozen = [
        p
        for p in frozen.splitlines()
        if p.strip() and not named(p, self.session.instruction)
    ]

  def _flags(self) -> list[tuple[str, ...]]:
    """Returns a key for every standing flag."""
    flags = []
    for path in sorted(self._rows):
      for row in self._rows[path]:
        flags.append(("unit", path, row.code, row.label))
    return flags + [("freeze", path) for path in sorted(self._frozen)]

  def _relative(self, path: str) -> str:
    root = self.session.workdir.rstrip("/") + "/"
    return path[len(root) :] if path.startswith(root) else path

  def _describe(self, keys: list[tuple[str, ...]]) -> list[str]:
    """Describes flags in plain sentences, one per file or directive."""
    d, lines = self.directives, []
    by_file: dict[str, list[tuple[str, ...]]] = {}
    for key in keys:
      if key[0] == "unit":
        by_file.setdefault(key[1], []).append(key)
    for path, rows in by_file.items():
      shown = "; ".join(f"{k[2]} ({k[3]})" if k[3] else k[2] for k in rows[:MAX_LISTED])
      more = f"; and {len(rows) - MAX_LISTED} more" if len(rows) > MAX_LISTED else ""
      lines.append(
          f'The instruction says: "{d.unit_quote}" {self._relative(path)} has'
          f" table rows keyed to item numbers outside {d.unit}: {shown}{more}."
      )
    frozen = [self._relative(k[1]) for k in keys if k[0] == "freeze"]
    if frozen:
      more = f" and {len(frozen) - MAX_LISTED} more" if len(frozen) > MAX_LISTED else ""
      lines.append(
          f'The instruction says: "{d.freeze_quote}" These files existed before'
          " the run, were modified, and are not named in the instruction: "
          + ", ".join(frozen[:MAX_LISTED])
          + more
          + "."
      )
    return lines

  async def _refresh(self) -> bool:
    """Polls unless the guard is off or the task is nearly out of time."""
    left = self.session.time_left()
    if not self.active or (left is not None and left < 45):
      return False
    try:
      async with self._lock:
        await self._poll()
      return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
      await self._off(exc)
      return False

  async def notice(self) -> str:
    """Returns the text to append to a command's output: new flags only."""
    try:
      if not await self._refresh():
        return ""
      new = [key for key in self._flags() if key not in self._told]
      if not new:
        return ""
      self._told.update(new)
      lines = self._describe(new)
      await self.session.log(("scope guard: flagged. " + " ".join(lines))[:1000])
      return (
          "\n[scope guard] Automatic text check by the harness, not a judgment.\n"
          + "\n".join(lines)
          + "\nIf this is outside what the instruction allows, correct it. If"
          " it is intended, say so plainly in your final summary. Each finding"
          " is shown once.\n"
      )
    except Exception as exc:  # pylint: disable=broad-exception-caught
      await self._off(exc)
      return ""

  async def final_note(self) -> str:
    """Returns the note for the final message: flags that still stand."""
    try:
      await self._refresh()
      keys = self._flags() if self.active else []
      if not keys:
        return ""
      return (
          "\n\n---\nScope check (automatic, added by the harness, not by the"
          " model; it does not judge whether the items are wrong): "
          + " ".join(self._describe(keys))
          + " Please confirm they are intended."
      )
    except Exception as exc:  # pylint: disable=broad-exception-caught
      await self._off(exc)
      return ""


class GuardedSession:
  """The session as the relay sees it: command output carries new flags."""

  def __init__(self, session: Any, guard: Guard):
    self._session, self._guard = session, guard

  def __getattr__(self, name: str) -> Any:
    return getattr(self._session, name)

  async def exec(self, command: str, timeout_sec: int = 120) -> dict[str, Any]:
    result = await self._session.exec(command, timeout_sec)
    notice = await self._guard.notice()
    if notice:
      result = {**result, "output": (result.get("output") or "") + notice}
    return result
