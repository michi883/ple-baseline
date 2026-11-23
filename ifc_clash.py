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

"""Clash check of IFC files, for Scope Guard (not part of the organizers' template).

    python3 ifc_clash.py model.ifc [more.ifc ...]

Scope Guard sends this file to the task container's own `python3` and reads the
one line it prints: TAG followed by JSON. It only reads the files.

Every pair of physical elements (IfcElement, except openings and other
IfcFeatureElement and IfcVirtualElement) is tested with IfcOpenShell's clash
tree, using the ifcclash defaults: a protrusion of more than 2 mm
(`clash_intersection_many`, tolerance 0.002 m) or a collision of the solids
(`clash_collision_many`, touching not allowed). Where both solids are
axis-aligned boxes, an overlap of more than 2 mm on all three axes counts too:
the clash tree misses boxes that share faces, such as two straight segments of
one run that overlap end to end. Two segments of one run that overlap at a
joint count like a pipe through a column. One kind of pair is not
counted: a distribution element (pipe, duct, cable tray, busway, terminal) with
a floor or ceiling covering (IfcCovering FLOORING or CEILING), because services
are routed through those finishes, as through a raised access floor. Those pairs
are only counted under "excused".

Without IfcOpenShell (or with no `python3`) nothing is checked, and the output
says so; Scope Guard logs that and raises no flag.
"""

import json
import sys

TAG = "@@ifc-clash@@"
MAX_PAIRS = 200  # pairs listed per file; the count is always complete
TOLERANCE_M = 0.002


def _label(entity) -> str:
  name = entity.Name or getattr(entity, "Tag", None) or entity.GlobalId
  return f"{entity.is_a()} '{str(name)[:60]}'"


def _excused(a, b) -> bool:
  """A service passing through a floor or ceiling finish."""
  for finish, other in ((a, b), (b, a)):
    if (
        finish.is_a("IfcCovering")
        and finish.PredefinedType in ("FLOORING", "CEILING")
        and other.is_a("IfcDistributionElement")
    ):
      return True
  return False


def _box(verts) -> tuple | None:
  """Returns (min, max) if a mesh is an axis-aligned box (all vertices on its corners)."""
  points = [tuple(verts[i : i + 3]) for i in range(0, len(verts) - 2, 3)]
  if len(set(points)) != 8:
    return None
  low = [min(p[k] for p in points) for k in range(3)]
  high = [max(p[k] for p in points) for k in range(3)]
  for p in points:
    for k in range(3):
      if min(abs(p[k] - low[k]), abs(p[k] - high[k])) > 1e-6:
        return None
  return low, high


def _box_overlaps(boxes: dict) -> list:
  """Pairs of axis-aligned boxes overlapping by more than the tolerance on every axis."""
  found, order = [], sorted(boxes, key=lambda i: boxes[i][0][0])
  for n, i in enumerate(order):
    (ilo, ihi) = boxes[i]
    for j in order[n + 1 :]:
      (jlo, jhi) = boxes[j]
      if jlo[0] >= ihi[0] - TOLERANCE_M:
        break
      depth = min(min(ihi[k], jhi[k]) - max(ilo[k], jlo[k]) for k in range(3))
      if depth > TOLERANCE_M:
        centre = [(max(ilo[k], jlo[k]) + min(ihi[k], jhi[k])) / 2 for k in range(3)]
        found.append((i, j, depth, centre))
  return found


def check(path: str) -> dict:
  """Returns the clashing pairs of one file, sorted, with depth and location in mm."""
  import ifcopenshell  # pylint: disable=import-outside-toplevel
  import ifcopenshell.geom  # pylint: disable=import-outside-toplevel

  model = ifcopenshell.open(path)
  elements = [
      e
      for e in model.by_type("IfcElement")
      if not e.is_a("IfcFeatureElement") and not e.is_a("IfcVirtualElement")
  ]
  pairs, excused = {}, set()

  def add(a, b, depth, where):
    key = tuple(sorted((a.id(), b.id())))
    if a.id() == b.id() or key in pairs or key in excused:
      return
    if _excused(a, b):
      excused.add(key)
      return
    first, second = sorted((_label(a), _label(b)))
    depth = None if depth is None else round(depth * 1000)
    pairs[key] = [first, second, depth, [round(c * 1000) for c in where]]  # mm, world

  if elements:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    tree, boxes = ifcopenshell.geom.tree(), {}
    shapes = ifcopenshell.geom.iterator(settings, model, 1, include=elements)
    if shapes.initialize():
      while True:
        shape = shapes.get()
        tree.add_element(shape)
        box = _box(shape.geometry.verts)
        if box:
          boxes[shape.id] = box
        if not shapes.next():
          break
      for found in (
          tree.clash_intersection_many(elements, elements, tolerance=TOLERANCE_M, check_all=False),
          tree.clash_collision_many(elements, elements, allow_touching=False),
      ):
        for clash in found:
          depth = clash.distance if clash.clash_type in (0, 1) else None
          add(model.by_id(clash.a.id()), model.by_id(clash.b.id()), depth, list(clash.p1))
      for i, j, depth, centre in _box_overlaps(boxes):
        add(model.by_id(i), model.by_id(j), depth, centre)
  listed = sorted(pairs.values(), key=lambda p: (p[0], p[1], p[3]))
  return {
      "elements": len(elements),
      "pairs": len(pairs),
      "excused": len(excused),
      "listed": listed[:MAX_PAIRS],
  }


def main(paths: list[str]) -> dict:
  try:
    import ifcopenshell  # pylint: disable=import-outside-toplevel
    import ifcopenshell.geom  # pylint: disable=import-outside-toplevel,unused-import
  except Exception as exc:  # pylint: disable=broad-exception-caught
    return {"unavailable": f"{type(exc).__name__}: {exc}"[:300]}
  files = {}
  for path in paths:
    try:
      files[path] = check(path)
    except Exception as exc:  # pylint: disable=broad-exception-caught
      files[path] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
  return {"version": ifcopenshell.version, "files": files}


if __name__ == "__main__":
  print(TAG + json.dumps(main(sys.argv[1:])), flush=True)
