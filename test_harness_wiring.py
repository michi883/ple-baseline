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

"""Runs the real `harness.solve` and relay with a stand-in for the Pi binary.

    python3 -m unittest test_harness_wiring -v      # needs `websockets`

The stand-in sends one command through the relay, as Pi's bash tool does, and
reports the output it got back as its final message. No model, network or
Docker. It checks the wiring only, not how a model reacts to a flag.
"""

import os
import pathlib
import stat
import sys
import tempfile
import unittest
from unittest import mock

import test_scope_guard

try:
  import harness  # imports taskbridge, which needs `websockets`
except ImportError:
  harness = None

FAKE_PI = '''#!{python}
import json, os, sys, urllib.request
if "--list-models" in sys.argv:
    sys.exit(0)
sys.stdin.read()
request = urllib.request.Request(
    os.environ["TASK_RELAY_URL"] + "/exec",
    data=json.dumps({{"command": os.environ["FAKE_PI_COMMAND"]}}).encode(),
    headers={{"Content-Type": "application/json"}},
)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({{}}))
output = json.loads(opener.open(request).read())["output"]
message = {{"role": "assistant", "content": [{{"type": "text", "text": "TOOL OUTPUT: " + output}}], "usage": {{}}}}
print(json.dumps({{"type": "message_end", "message": message}}), flush=True)
'''


class Session(test_scope_guard.LocalSession):
  """LocalSession plus what `harness.solve` and the relay ask of a session."""

  mcp_servers = []
  final_message = ""

  async def usage(self, *args, **kwargs):
    pass


@unittest.skipIf(harness is None, "needs the websockets package")
class WiringTest(unittest.IsolatedAsyncioTestCase):

  def setUp(self):
    self._tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(self._tmp.name).resolve()
    self.work, self.stage, home = root / "work", root / "stage", root / "home"
    for d in (self.work / "out", self.stage, home):
      d.mkdir(parents=True)
    pi = root / "pi"
    pi.write_text(FAKE_PI.format(python=sys.executable))
    pi.chmod(pi.stat().st_mode | stat.S_IXUSR)
    table = [test_scope_guard.HEADER] + test_scope_guard.INSIDE + [test_scope_guard.OUTSIDE]
    (self.stage / "bad.docx").write_bytes(test_scope_guard.docx(table))
    env = {
        "HOME": str(home),
        "MODEL_NAME": "stand-in",
        "MODEL_BASE_URL": "http://127.0.0.1:9/v1",
        "MODEL_API_KEY": "none",
        "FAKE_PI_COMMAND": f"cp {self.stage}/bad.docx out/memo.docx && echo saved",
    }
    for patch in (
        mock.patch.dict(os.environ, env),
        mock.patch.object(harness, "PI", str(pi)),
        mock.patch.object(harness.scope_guard.Guard, "MARKER_DIR", str(root)),
    ):
      patch.start()
      self.addCleanup(patch.stop)
    for name in ("ANTHROPIC_BASE_URL", "GOOGLE_GEMINI_BASE_URL"):
      os.environ.pop(name, None)

  def tearDown(self):
    self._tmp.cleanup()

  async def test_flag_reaches_the_agent_and_the_final_message(self):
    session = Session(self.work, test_scope_guard.CONFINED)
    final = await harness.solve(session)
    seen, _, note = final.partition("\n\n---\n")
    self.assertTrue(seen.startswith("TOOL OUTPUT: saved\n\n[scope guard]"), seen)
    self.assertIn("outside Section 4: 5.02", seen)  # what the agent's tool call returned
    self.assertTrue(note.startswith("Scope check (automatic"), note)
    self.assertIn("out/memo.docx has table rows keyed to item numbers outside Section 4: 5.02", note)

  async def test_unrestricted_task_runs_exactly_as_the_template(self):
    session = Session(self.work, "Write the memo and save it as out/memo.docx.")
    final = await harness.solve(session)
    self.assertEqual(final, "TOOL OUTPUT: saved")  # the agent's message, untouched
    self.assertEqual(session.commands, [os.environ["FAKE_PI_COMMAND"]])  # no guard command ran
    self.assertFalse([line for line in session.logs if "scope guard" in line])


if __name__ == "__main__":
  unittest.main()
