#!/usr/bin/env python3
"""MDC-2026-014 Meridian Data Center, Data Hall 1 -- coordinated MEP model.

Rebuilds the hall from the seven-sheet drawing set (A-101, A-301, A-601, A-602,
M-101, E-101, F-101) and routes the three services (CT-1 telecom ladder tray,
BW-1 busway, CHW-1 chilled-water main) clash-free.  Every value used below was
read off the drawings and is baked in as a literal; the PNG sheets are never
opened.  Output: one IFC4 file (millimetre units) written to sys.argv[1]
(default output/model.ifc) plus reconciliation.json next to it.

Coordination decisions (see reconciliation.json for the full log):
* A-602 vertical budget: deflector +3024.6 (A-301: 25.4 below the +3050 soffit)
  minus the 460 standoff is +2564.6, i.e. BELOW the 2600 minimum clear height.
  There is no overhead pathway zone in this hall, so all three services run in
  the access-floor plenum (A-301 note 3), tops >= 20 mm under the panel.
* Under the floor a 300 mm vertical tray/busway separation cannot be had
  (545 mm zone), so tray and busway are separated horizontally everywhere
  (>= 305 mm) and their networks never cross in plan: the busway is a west
  comb (wall leg + trunk at the row ends), the tray a serpentine (west descent,
  C/D header east, east trunk, A/B header back west).  CHW runs on its own,
  higher tier and crosses the electrical tier with > 160 mm vertical clearance.
* One header per pair of rows (A/B and C/D) serves both rows within 2500 mm;
  CHW taps reach the perimeter CRAH gallery (every CRAH centroid <= 2400 mm).
* Shared entry (0, 12470): busway along the west wall from the south, tray on
  an E-W stub just north of it (both ~326 mm from the point), CHW through it.
* Joints: every segment is extruded node to node; segments of one run touch
  but never interpenetrate (tray/busway joint quadrants notched out by CSG,
  CHW elbows and tees mitred with half-space clips).
* Structure/tile conflict: bays hit by the 150 mm-offset columns are omitted
  (A-601 "-600" terms); the row is not re-spaced.
"""
import hashlib
import json
import math
import os
import sys

import ifcopenshell
import ifcopenshell.guid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "model.ifc")

# =============================================================================
# 1. DRAWING DATA (literals read off the sheets)
# =============================================================================
TILE = 600.0                                   # A-101 note 3 / A-602
ROOM_OUTLINE = [(0.0, 0.0), (27000.0, 0.0), (27000.0, 15600.0), (18600.0, 15600.0),
                (18600.0, 24000.0), (0.0, 24000.0)]   # A-101: 27000 x 24000, NE notch 8400 x 8400 (no slab)

# Vertical datums (A-301 / A-602) -- all mm above finished floor
Z_FF = 0.0
Z_SLAB_TOP = -600.0
PANEL_THK = 35.0
Z_PANEL_UNDERSIDE = Z_FF - PANEL_THK
UNDERPANEL_CLEAR = 20.0                         # A-301 note 3 (ANSI/TIA-942-B 8.6.2)
Z_SOFFIT = 3050.0
DEFLECTOR_BELOW_SOFFIT = 25.4
Z_DEFLECTOR = Z_SOFFIT - DEFLECTOR_BELOW_SOFFIT  # +3024.6
SPRINKLER_STANDOFF = 460.0
MIN_CLEAR_HEIGHT = 2600.0
CABINET_HEIGHT = 2000.0
COLUMN_SIZE = 600.0
COLUMN_HEIGHT = 3050.0                          # FF to soffit (A-301 note 4)

# Structural grid (A-101): columns A,B,C at x = 7050/14250/21450, rows 1,2,3 at y = 7050/14250/21450
GRID_X = {"A": 7050.0, "B": 14250.0, "C": 21450.0}
GRID_Y = {"1": 7050.0, "2": 14250.0, "3": 21450.0}
COLUMNS = ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3"]   # C3 falls in the no-slab notch

# Cabinet type schedule (A-601): width, depth, description
CAB_TYPES = {
    "C1": (600.0, 1200.0, "SERVER CABINET, 600 WIDE"),
    "C2": (600.0, 1070.0, "SERVER CABINET, 600 WIDE, SHALLOW"),
    "N1": (800.0, 1200.0, "DISTRIBUTOR CABINET, 800 WIDE"),
    "N2": (800.0, 1070.0, "DISTRIBUTOR CABINET, 800 WIDE, SHALLOW"),
}
# Cabinet schedule (A-601) + row centrelines (A-101 dimension chain 3000/2935/2465/2935/12665)
ROWS = [
    # row, centreline y, depth, front faces, first tile, last tile, qty, bay sequence west->east
    ("A", 3000.0, 1200.0, "SOUTH", "D05", "AJ05", 26,
     "4C1 · CU · 4C1 · N1 · 4C1 · CU · CA · 7C1 · SP · CU · 6C1"),
    ("B", 5935.0, 1070.0, "NORTH", "D10", "AI10", 21,
     "4C2 · CU · 3C2 · 2—600 · 2C2 · 2N2 · CU · CA · 2C2 · 2—600 · 3C2 · CU · SP · 5C2 · 2—600"),
    ("C", 8400.0, 1200.0, "SOUTH", "D14", "AH14", 20,
     "4C1 · CU · 3C1 · 2—600 · 2C1 · CU · 2C1 · CA · N1 · 2—600 · 4C1 · SP · CU · 4C1 · 2—600"),
    ("D", 11335.0, 1070.0, "NORTH", "D19", "AK19", 27,
     "5C2 · CU · 3C2 · 2N2 · 3C2 · CU · CA · 8C2 · SP · CU · 6C2"),
]
RACK_RU, RACK_KW, RACK_KG = 42, 8.0, 1363.0
INROW_CU_WIDTH = 600.0                          # CRAH schedule 600 x 1070 / 600 x 1200
SPARE_WIDTH = 600.0

# Perimeter CRAH gallery (A-601 CRAH schedule): tiles B01, P01, AC01, AQ01, 1200 x 900, faces NORTH
PERIMETER_CRAH_TILES = ["B01", "P01", "AC01", "AQ01"]
PERIM_W, PERIM_D = 1200.0, 900.0
CRAH_HEIGHT = 2000.0

# PDU schedule (A-601) + E-101 plan position; front flush with the served row's front (A-101 note 8)
PDU_W, PDU_D, PDU_H = 762.0, 813.0, 1959.0
PDUS = [
    # tag, row, tile, SW corner x, SW corner y, front faces
    ("PDU-01", "A", "AN05", 23400.0, 2400.0, "SOUTH"),
    ("PDU-02", "B", "AM10", 22800.0, 5657.0, "NORTH"),
    ("PDU-03", "C", "AL14", 22400.0, 7800.0, "SOUTH"),
    ("PDU-04", "D", "AO19", 24000.0, 11057.0, "NORTH"),
]
PDU_WORKING_SPACE = 900.0                        # E-101 note 8
PDU_DEDICATED_SPACE = 1800.0                     # E-101 note 7 / NFPA 70 110.26(E)

# Cold-aisle containment CAC-BC (A-602): 4 roof panels 1530 wide x 55.5, underside +2000, 4 doors 60 x 2055.5
CAC_ROOF_WIDTH, CAC_ROOF_THK, CAC_ROOF_UNDERSIDE = 1530.0, 55.5, 2000.0
CAC_DOOR_THK, CAC_DOOR_H = 60.0, 2055.5
# roof panels: stop at the column faces (A1, B1 stand in the aisle) and at the cross-aisle break
CAC_ROOF_PANELS = [(1800.0, 6750.0), (7350.0, 11400.0), (12600.0, 13950.0), (14550.0, 21000.0)]
# end doors placed just outside the roof ends (west end, both sides of the break, east end)
CAC_DOORS = [(1740.0, 1800.0), (11400.0, 11460.0), (12540.0, 12600.0), (21000.0, 21060.0)]

# Sprinklers (F-101): 94 ceiling heads, 1250 / 2500 grid, wall-snapped last lines, relocated off columns
CEILING_HEADS = (
    [(1250.0 + 2500.0 * i, y) for y in (1250.0, 3750.0, 6250.0, 8750.0, 11250.0) for i in range(11)]
    + [(x, 13750.0) for x in (1250.0, 3750.0, 6250.0, 8750.0, 11250.0, 13750.0, 16250.0, 21250.0)]
    + [(x, 14350.0) for x in (18750.0, 23750.0, 26250.0)]
    + [(x, y) for y in (16250.0, 18750.0, 21250.0, 23750.0)
       for x in (1250.0, 3750.0, 6250.0, 8750.0, 11250.0, 13750.0, 17350.0)]
)
RELOCATED_HEADS = {(21250.0, 13750.0): "relocated one tile south off column C2",
                   (17350.0, 16250.0): "last line snapped 1250 off notch wall",
                   (17350.0, 18750.0): "last line snapped 1250 off notch wall",
                   (17350.0, 21250.0): "last line snapped 1250 off notch wall",
                   (17350.0, 23750.0): "last line snapped 1250 off notch wall",
                   (18750.0, 14350.0): "last line snapped 1250 off notch wall",
                   (23750.0, 14350.0): "last line snapped 1250 off notch wall",
                   (26250.0, 14350.0): "last line snapped 1250 off notch wall"}
# 10 in-aisle heads under the CAC-BC roof, deflector +1890 (110 below the roof underside, 3/A-301)
Z_INAISLE_DEFLECTOR = 1890.0
INAISLE_HEADS_X = [2300.0, 4275.0, 6250.0, 7850.0, 10900.0, 13275.0, 15050.0, 16866.7, 18683.3, 20500.0]
HEAD_RADIUS = 20.0

# Pathway sections (A-602 / E-101 / M-101)
TRAY_W, TRAY_H = 683.0, 127.0                  # CT-1 cable tray, ladder (610 nominal)
BUS_W, BUS_H = 128.0, 147.0                    # BW-1 busway
CHW_OD = 114.3                                 # CHW-1 DN100 steel, bare OD
CHW_INSUL = 25.4                               # 25 mm min insulation (counts in clashes)
CHW_JACKET_OD = 168.3                          # M-101 note 4: next ASTM C585 jacket size
TRAY_BUS_SEP = 300.0                           # E-101 note 6 / ANSI/TIA-942 7.3.1
BUS_SUPPORT_MAX = 1500.0                       # E-101 note 4
BUS_SUPPORT_SPACING = 1400.0

# Service entries (M-101 / E-101): west wall, 12470 north of the south wall, all three services
ENTRY = (0.0, 12470.0)

# =============================================================================
# 2. LAYOUT
# =============================================================================


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def tile_origin(addr):
    i = 0
    while addr[i].isalpha():
        i += 1
    return col_index(addr[:i]) * TILE, (int(addr[i:]) - 1) * TILE


def tile_address(x, y):
    c = int(math.floor(x / TILE + 1e-9))
    r = int(math.floor(y / TILE + 1e-9)) + 1
    s = ""
    c += 1
    while c > 0:
        c, rem = divmod(c - 1, 26)
        s = chr(65 + rem) + s
    return "%s%02d" % (s, r)


def parse_sequence(seq):
    terms = []
    for tok in seq.split("·"):
        tok = tok.strip()
        i = 0
        while i < len(tok) and tok[i].isdigit():
            i += 1
        terms += [tok[i:]] * (int(tok[:i]) if i else 1)
    return terms


def cross_aisle_east_edge():
    """A-101 note 5: the cross aisle's east edge is common to every row.  Derive it
    from each row's last tile (the bays after CA accumulate to the last cabinet)."""
    edges = []
    for row, ycl, depth, facing, ft, lt, qty, seq in ROWS:
        terms = parse_sequence(seq)
        k = terms.index("CA")
        after = terms[k + 1:]
        # offset from the CA east edge to the SW corner of the last cabinet
        last_cab = max(i for i, t in enumerate(after) if t in CAB_TYPES)
        off = 0.0
        for t in after[:last_cab]:
            off += CAB_TYPES[t][0] if t in CAB_TYPES else (float(t[1:]) if t.startswith("—") else 600.0)
        lx = tile_origin(lt)[0]
        edges.append((lx - off, lx + TILE - off))
    lo = max(e[0] for e in edges)
    hi = min(e[1] for e in edges)
    assert lo < hi, edges
    x = math.ceil(lo / TILE - 1e-9) * TILE        # on the tile grid
    assert lo <= x < hi
    return x


X_CA_EAST = cross_aisle_east_edge()             # 12600


def build_rows():
    racks, crahs, rows = [], [], {}
    for row, ycl, depth, facing, ft, lt, qty, seq in ROWS:
        x = tile_origin(ft)[0]
        x_start = x
        n_rack = n_cu = 0
        bays = []
        for term in parse_sequence(seq):
            if term == "CA":
                bays.append(("CA", x, X_CA_EAST))
                x = X_CA_EAST
                continue
            if term in CAB_TYPES:
                w = CAB_TYPES[term][0]
                n_rack += 1
                racks.append(dict(tag="RACK-%s%02d" % (row, n_rack), row=row, ctype=term, x0=x, x1=x + w,
                                  y0=ycl - depth / 2.0, y1=ycl + depth / 2.0, facing=facing, bay=len(bays) + 1))
            elif term == "CU":
                w = INROW_CU_WIDTH
                n_cu += 1
                crahs.append(dict(tag="CRAH-%s%02d" % (row, n_cu), row=row, kind="IN ROW %s" % row,
                                  x0=x, x1=x + w, y0=ycl - depth / 2.0, y1=ycl + depth / 2.0, facing=facing,
                                  kw=50.0, airflow=9000.0, branch="DN50"))
            elif term == "SP":
                w = SPARE_WIDTH                    # spare position, not in contract -> not modelled
            elif term.startswith("—"):
                w = float(term[1:])                 # bay omitted for structure, row not re-spaced
            else:
                raise ValueError(term)
            bays.append((term, x, x + w))
            x += w
        mine = [r for r in racks if r["row"] == row]
        assert len(mine) == qty, (row, len(mine), qty)
        assert tile_address(mine[0]["x0"], mine[0]["y0"]) == ft, (row, ft)
        assert tile_address(mine[-1]["x0"], mine[-1]["y0"]) == lt, (row, lt)
        rows[row] = dict(row=row, y=ycl, depth=depth, facing=facing, x0=x_start, x1=x,
                         cab_x1=mine[-1]["x1"], bays=bays)
    return racks, crahs, rows


RACKS, INROW_CRAHS, ROWD = build_rows()
PERIM_CRAHS = []
for _i, _t in enumerate(PERIMETER_CRAH_TILES):
    _x, _y = tile_origin(_t)
    PERIM_CRAHS.append(dict(tag="CRAH-%02d" % (_i + 1), row=None, kind="PERIMETER", x0=_x, x1=_x + PERIM_W,
                            y0=_y, y1=_y + PERIM_D, facing="NORTH", kw=100.0, airflow=20000.0, branch="DN100"))
CRAHS = PERIM_CRAHS + INROW_CRAHS

for _tag, _row, _tile, _x, _y, _f in PDUS:
    assert tile_address(_x, _y) == _tile, (_tag, tile_address(_x, _y), _tile)
    _r = ROWD[_row]
    _front = _r["y"] - _r["depth"] / 2 if _f == "SOUTH" else _r["y"] + _r["depth"] / 2
    assert abs((_y if _f == "SOUTH" else _y + PDU_D) - _front) < 1e-6, _tag

assert len(RACKS) == 94 and len(CRAHS) == 16 and len(CEILING_HEADS) == 94 and len(INAISLE_HEADS_X) == 10

AISLE_BC = (ROWD["B"]["y"] + ROWD["B"]["depth"] / 2, ROWD["C"]["y"] - ROWD["C"]["depth"] / 2)   # 6470..7800
AISLE_BC_MID = 0.5 * (AISLE_BC[0] + AISLE_BC[1])                                                 # 7135

# =============================================================================
# 3. ROUTES  (all in the access-floor plenum; constant tier per service)
# =============================================================================
Z_SERVICE_BOTTOM = Z_SLAB_TOP + 20.0           # electrical tier sits 20 mm off the slab
Z_TRAY = Z_SERVICE_BOTTOM + TRAY_H / 2.0      # -516.5  (top -453)
Z_BUS = Z_SERVICE_BOTTOM + BUS_H / 2.0        # -506.5  (top -433)
Z_CHW = -160.0                                 # jacket top -75.85 (>= 20 clear of the -35 panel underside)
SEP = TRAY_BUS_SEP + 5.0                       # 305 mm, 5 mm margin on the 300 rule

# coverage / reach targets
ROW_REACH = 2500.0
CRAH_REACH_TARGET = 2400.0                      # 100 mm margin on the 2500 rule, 3D to the unit centroid
CRAH_PLAN_REACH = math.sqrt(CRAH_REACH_TARGET ** 2 - (CRAH_HEIGHT / 2.0 - Z_CHW) ** 2)

# --- horizontal tracks
HALF_TB = TRAY_W / 2.0 + BUS_W / 2.0 + SEP     # tray/busway centre-to-centre spacing (710.5)
# Shared entry (0, 12470): the busway arrives along the west wall from the south and the tray along an
# E-W stub just north of it; the 305 mm gap between them is split so both centrelines are equidistant
# from the entry point (~326 mm each).
X_BUS_WALL = BUS_W / 2.0                        # busway hugging the west wall (x 0..128)
_GAP_Y = TRAY_W / 2.0 + SEP                     # busway end -> tray centreline
_U = round((_GAP_Y ** 2 - X_BUS_WALL ** 2) / (2.0 * _GAP_Y), 2)
Y_BUS_ENTRY = ENTRY[1] - _U                     # 12149.92
Y_TRAY_STUB = Y_BUS_ENTRY + _GAP_Y              # 12796.42
X_TRAY_DESC = 2400.0                            # tray west descent (C02/D02 fully covered)
X_BUS_TRUNK = X_TRAY_DESC - HALF_TB             # busway west trunk (1689.5)
Y_BUS_CD = 9400.0                               # C/D zone: busway south, tray north
Y_TRAY_CD = Y_BUS_CD + HALF_TB                  # 10110.5
Y_TRAY_AB = 4000.0                              # A/B zone: tray south, busway north
Y_BUS_AB = Y_TRAY_AB + HALF_TB                  # 4710.5
X_BUS_END = 19200.0                             # busway headers end (>=85 % of every row)
X_TRAY_EAST = X_BUS_END + SEP + TRAY_W / 2.0    # tray east trunk (19846.5)
X_TRAY_AB_END = 2400.0
X_CHW_TRUNK = X_BUS_TRUNK - BUS_W / 2.0 - CHW_JACKET_OD / 2.0 - 11.35   # 1530, clear of the busway in plan
Y_CHW_CD = 9800.0
Y_CHW_AB = 3900.0                               # within reach of A and B in-row CRAHs, short perimeter taps
X_CHW_CD_END = 19200.0


def _crah_centre(tag):
    c = [c for c in CRAHS if c["tag"] == tag][0]
    return 0.5 * (c["x0"] + c["x1"]), 0.5 * (c["y0"] + c["y1"])


_c1 = _crah_centre("CRAH-01")
_c2 = _crah_centre("CRAH-02")
_c3 = _crah_centre("CRAH-03")
_c4 = _crah_centre("CRAH-04")
Y_CHW_C1 = _c1[1] + math.sqrt(CRAH_PLAN_REACH ** 2 - (X_CHW_TRUNK - _c1[0]) ** 2)
Y_CHW_TAP = _c2[1] + CRAH_PLAN_REACH
X_CHW_C4 = _c4[0] - 1400.0
Y_CHW_C4 = _c4[1] + math.sqrt(CRAH_PLAN_REACH ** 2 - 1400.0 ** 2)


def r1(v):
    return round(v, 2)


# polylines (each list is a chain of points; branches start on an existing node)
SERVICES = {
    "CT-1": dict(kind="TRAY", name="TELECOM", z=Z_TRAY, w=TRAY_W, h=TRAY_H, polylines=[
        [(0.0, Y_TRAY_STUB), (X_TRAY_DESC, Y_TRAY_STUB), (X_TRAY_DESC, Y_TRAY_CD), (X_TRAY_EAST, Y_TRAY_CD),
         (X_TRAY_EAST, Y_TRAY_AB), (X_TRAY_AB_END, Y_TRAY_AB)],
    ]),
    "BW-1": dict(kind="BUSWAY", name="POWER", z=Z_BUS, w=BUS_W, h=BUS_H, polylines=[
        [(X_BUS_WALL, Y_BUS_ENTRY), (X_BUS_WALL, Y_BUS_CD), (X_BUS_TRUNK, Y_BUS_CD), (X_BUS_END, Y_BUS_CD)],
        [(X_BUS_TRUNK, Y_BUS_CD), (X_BUS_TRUNK, Y_BUS_AB), (X_BUS_END, Y_BUS_AB)],
    ]),
    "CHW-1": dict(kind="CHW", name="CHILLED WATER", z=Z_CHW, w=CHW_OD, h=CHW_OD, polylines=[
        [(0.0, ENTRY[1]), (X_CHW_TRUNK, ENTRY[1]), (X_CHW_TRUNK, Y_CHW_CD), (X_CHW_TRUNK, Y_CHW_AB),
         (X_CHW_TRUNK, Y_CHW_C1)],
        [(X_CHW_TRUNK, Y_CHW_CD), (X_CHW_CD_END, Y_CHW_CD)],
        [(X_CHW_TRUNK, Y_CHW_AB), (_c2[0], Y_CHW_AB), (_c3[0], Y_CHW_AB), (X_CHW_C4, Y_CHW_AB),
         (X_CHW_C4, Y_CHW_C4)],
        [(_c2[0], Y_CHW_AB), (_c2[0], Y_CHW_TAP)],
        [(_c3[0], Y_CHW_AB), (_c3[0], Y_CHW_TAP)],
    ]),
}
TAP_TARGETS = {  # segment end point -> CRAH it terminates at (CHW taps / drops)
    (r1(X_CHW_TRUNK), r1(Y_CHW_C1)): "CRAH-01",
    (r1(_c2[0]), r1(Y_CHW_TAP)): "CRAH-02",
    (r1(_c3[0]), r1(Y_CHW_TAP)): "CRAH-03",
    (r1(X_CHW_C4), r1(Y_CHW_C4)): "CRAH-04",
}


def build_segments():
    """Explode polylines into straight segments, split at every junction node."""
    out = {}
    for tag, svc in SERVICES.items():
        pts = [[(r1(x), r1(y)) for x, y in pl] for pl in svc["polylines"]]
        nodes = set(p for pl in pts for p in pl)
        raw = []
        for pl in pts:
            for a, b in zip(pl[:-1], pl[1:]):
                raw.append((a, b))
        segs = []
        for a, b in raw:
            # split at nodes lying strictly inside the segment
            inner = []
            for n in nodes:
                if n in (a, b):
                    continue
                if a[0] == b[0] == n[0] and min(a[1], b[1]) < n[1] < max(a[1], b[1]):
                    inner.append(n)
                elif a[1] == b[1] == n[1] and min(a[0], b[0]) < n[0] < max(a[0], b[0]):
                    inner.append(n)
            inner.sort(key=lambda n: abs(n[0] - a[0]) + abs(n[1] - a[1]))
            chain = [a] + inner + [b]
            for p, q in zip(chain[:-1], chain[1:]):
                assert p[0] == q[0] or p[1] == q[1], "segments must be axis-aligned"
                segs.append((p, q))
        out[tag] = segs
    return out


SEGMENTS = build_segments()


def seg_len(a, b):
    return abs(b[0] - a[0]) + abs(b[1] - a[1])


def seg_box(tag, a, b, envelope=False):
    svc = SERVICES[tag]
    if svc["kind"] == "CHW":
        w = h = (CHW_JACKET_OD if envelope else CHW_OD)
    else:
        w, h = svc["w"], svc["h"]
    z = svc["z"]
    if a[1] == b[1]:
        return (min(a[0], b[0]), max(a[0], b[0]), a[1] - w / 2, a[1] + w / 2, z - h / 2, z + h / 2)
    return (a[0] - w / 2, a[0] + w / 2, min(a[1], b[1]), max(a[1], b[1]), z - h / 2, z + h / 2)


def axis_gap(a0, a1, b0, b1):
    return max(0.0, a0 - b1, b0 - a1)


def box_sep(p, q):
    """separation on the best axis (the E-101 'on at least one axis' measure)"""
    return max(axis_gap(p[0], p[1], q[0], q[1]), axis_gap(p[2], p[3], q[2], q[3]), axis_gap(p[4], p[5], q[4], q[5]))


def pt_seg_dist(p, a, b, z=None):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    d2 = (p[0] - qx) ** 2 + (p[1] - qy) ** 2
    if z is not None and len(p) > 2:
        d2 += (p[2] - z) ** 2
    return math.sqrt(d2)


def row_coverage(tag, row, x_hi=None):
    r = ROWD[row]
    lo, hi = r["x0"], (x_hi if x_hi is not None else r["x1"])
    iv = []
    for a, b in SEGMENTS[tag]:
        if a[1] == b[1] and abs(a[1] - r["y"]) <= ROW_REACH:
            x0, x1 = max(min(a[0], b[0]), lo), min(max(a[0], b[0]), hi)
            if x1 > x0:
                iv.append((x0, x1))
    iv.sort()
    tot, cur = 0.0, None
    for x0, x1 in iv:
        if cur is None or x0 > cur[1]:
            if cur:
                tot += cur[1] - cur[0]
            cur = [x0, x1]
        else:
            cur[1] = max(cur[1], x1)
    if cur:
        tot += cur[1] - cur[0]
    return tot / (hi - lo)


# --- self-checks of the routing (cheap, deterministic) ---------------------------------
def _verify_routes():
    tb = min(box_sep(seg_box("CT-1", *s), seg_box("BW-1", *t)) for s in SEGMENTS["CT-1"] for t in SEGMENTS["BW-1"])
    assert tb >= TRAY_BUS_SEP, tb
    for tag in SERVICES:
        for row in ROWD:
            assert row_coverage(tag, row) >= 0.85, (tag, row, row_coverage(tag, row))
    for c in CRAHS:
        p = (0.5 * (c["x0"] + c["x1"]), 0.5 * (c["y0"] + c["y1"]), CRAH_HEIGHT / 2.0)
        d = min(pt_seg_dist(p, a, b, Z_CHW) for a, b in SEGMENTS["CHW-1"])
        assert d <= CRAH_REACH_TARGET + 0.5, (c["tag"], d)
    for tag in SERVICES:
        top = SERVICES[tag]["z"] + (CHW_JACKET_OD if SERVICES[tag]["kind"] == "CHW" else SERVICES[tag]["h"]) / 2
        assert top <= Z_PANEL_UNDERSIDE - UNDERPANEL_CLEAR + 1e-9, (tag, top)
    return tb


MIN_TRAY_BUS_SEP = _verify_routes()

# =============================================================================
# 4. IFC AUTHORING
# =============================================================================
f = ifcopenshell.file(schema="IFC4")
f.header.file_name.name = os.path.basename(OUT_PATH)
f.header.file_name.time_stamp = "2026-07-27T00:00:00"
f.header.file_name.author = ("JRK",)
f.header.file_name.organization = ("Meridian Digital Infrastructure",)
f.header.file_name.originating_system = "solution.py (ifcopenshell %s)" % ifcopenshell.version
f.header.file_name.authorization = "A. OKONKWO, PE"

_GUIDS = set()


def gid(key):
    h = hashlib.md5(("MDC-2026-014/" + key).encode("utf-8")).hexdigest()
    g = ifcopenshell.guid.compress(h)
    assert g not in _GUIDS, key
    _GUIDS.add(g)
    return g


_DIRS, _P2 = {}, {}


def d3(x, y, z):
    k = (float(x), float(y), float(z))
    if k not in _DIRS:
        _DIRS[k] = f.createIfcDirection(k)
    return _DIRS[k]


def p3(x, y, z):
    return f.createIfcCartesianPoint((float(x), float(y), float(z)))


ORIGIN = p3(0, 0, 0)
ORIGIN2 = f.createIfcCartesianPoint((0.0, 0.0))
PLACE2 = f.createIfcAxis2Placement2D(ORIGIN2, None)
IDENT3 = f.createIfcAxis2Placement3D(ORIGIN, d3(0, 0, 1), d3(1, 0, 0))

units = f.createIfcUnitAssignment([
    f.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE"),
    f.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE"),
    f.create_entity("IfcSIUnit", UnitType="VOLUMEUNIT", Name="CUBIC_METRE"),
    f.create_entity("IfcSIUnit", UnitType="PLANEANGLEUNIT", Name="RADIAN"),
])
model_ctx = f.create_entity("IfcGeometricRepresentationContext", ContextType="Model", CoordinateSpaceDimension=3,
                            Precision=0.01, WorldCoordinateSystem=IDENT3, TrueNorth=f.createIfcDirection((0.0, 1.0)))
body_ctx = f.create_entity("IfcGeometricRepresentationSubContext", ContextIdentifier="Body", ContextType="Model",
                           ParentContext=model_ctx, TargetView="MODEL_VIEW")

project = f.create_entity("IfcProject", GlobalId=gid("project"), Name="MDC-2026-014",
                          LongName="MERIDIAN DATA CENTER PHASE 1 - DATA HALL 1",
                          Description="Coordinated MEP model (IFC4, mm)", Phase="ISSUED FOR CONSTRUCTION",
                          RepresentationContexts=[model_ctx], UnitsInContext=units)
site_pl = f.createIfcLocalPlacement(None, IDENT3)
bldg_pl = f.createIfcLocalPlacement(site_pl, IDENT3)
storey_pl = f.createIfcLocalPlacement(bldg_pl, IDENT3)
site = f.create_entity("IfcSite", GlobalId=gid("site"), Name="MERIDIAN DATA CENTER", ObjectPlacement=site_pl,
                       CompositionType="ELEMENT")
building = f.create_entity("IfcBuilding", GlobalId=gid("building"), Name="PHASE 1", ObjectPlacement=bldg_pl,
                           CompositionType="ELEMENT")
storey = f.create_entity("IfcBuildingStorey", GlobalId=gid("storey"), Name="DATA HALL 1",
                         LongName="DATA HALL 1 (FINISHED FLOOR = TOP OF ACCESS FLOOR PANEL)",
                         ObjectPlacement=storey_pl, CompositionType="ELEMENT", Elevation=0.0)
f.create_entity("IfcRelAggregates", GlobalId=gid("agg/project"), RelatingObject=project, RelatedObjects=[site])
f.create_entity("IfcRelAggregates", GlobalId=gid("agg/site"), RelatingObject=site, RelatedObjects=[building])
f.create_entity("IfcRelAggregates", GlobalId=gid("agg/building"), RelatingObject=building, RelatedObjects=[storey])

CONTAINED = []


def placement(x, y, z, axis=(0, 0, 1), ref=(1, 0, 0), rel=None):
    return f.createIfcLocalPlacement(rel if rel is not None else storey_pl,
                                     f.createIfcAxis2Placement3D(p3(x, y, z), d3(*axis), d3(*ref)))


def shape(solid):
    rep = f.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [solid])
    return f.createIfcProductDefinitionShape(None, None, [rep])


_PROFILES = {}


def rect_profile(w, d):
    k = ("R", round(w, 4), round(d, 4))
    if k not in _PROFILES:
        _PROFILES[k] = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=PLACE2,
                                       XDim=float(w), YDim=float(d))
    return _PROFILES[k]


def circle_profile(r):
    k = ("C", round(r, 4))
    if k not in _PROFILES:
        _PROFILES[k] = f.create_entity("IfcCircleProfileDef", ProfileType="AREA", Position=PLACE2, Radius=float(r))
    return _PROFILES[k]


def extrude(profile, depth):
    return f.createIfcExtrudedAreaSolid(profile, IDENT3, d3(0, 0, 1), float(depth))


def ival(v):
    if isinstance(v, bool):
        return f.create_entity("IfcBoolean", v)
    if isinstance(v, int):
        return f.create_entity("IfcInteger", v)
    if isinstance(v, float):
        return f.create_entity("IfcReal", v)
    return f.create_entity("IfcLabel", str(v))


def lval(v):
    return f.create_entity("IfcLengthMeasure", float(v))


def add_pset(obj, name, props, key):
    """props: dict name -> value; floats whose name ends with 'Mm' or is a length are IfcLengthMeasure."""
    ps = []
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, float):
            v = round(v, 3)
        if isinstance(v, float) and (k.endswith("Mm") or k.endswith("Elevation") or k in (
                "Width", "Depth", "Height", "Length", "Radius", "OuterDiameter", "Thickness")):
            nv = lval(v)
        else:
            nv = ival(v)
        ps.append(f.create_entity("IfcPropertySingleValue", Name=k, NominalValue=nv))
    pset = f.create_entity("IfcPropertySet", GlobalId=gid("pset/%s/%s" % (name, key)), Name=name, HasProperties=ps)
    f.create_entity("IfcRelDefinesByProperties", GlobalId=gid("rdp/%s/%s" % (name, key)),
                    RelatedObjects=[obj], RelatingPropertyDefinition=pset)
    return pset


def element(cls, key, name, plc, solid, predefined=None, objtype=None, tag=None, description=None, contain=True):
    kw = dict(GlobalId=gid("el/" + key), Name=name, ObjectPlacement=plc,
              Representation=shape(solid) if solid is not None else None)
    if objtype is not None:
        kw["ObjectType"] = objtype
    if description is not None:
        kw["Description"] = description
    if tag is not None:
        kw["Tag"] = tag
    if predefined is not None:
        kw["PredefinedType"] = predefined
    e = f.create_entity(cls, **kw)
    if contain:
        CONTAINED.append(e)
    return e


FACING_REF = {"NORTH": (1, 0, 0), "SOUTH": (-1, 0, 0), "EAST": (0, -1, 0), "WEST": (0, 1, 0)}
FACING_DEG = {"NORTH": 0.0, "WEST": 90.0, "SOUTH": 180.0, "EAST": 270.0}
FRONT_VEC = {"NORTH": (0.0, 1.0), "SOUTH": (0.0, -1.0), "EAST": (1.0, 0.0), "WEST": (-1.0, 0.0)}


def facing_box(cls, key, name, x0, x1, y0, y1, z0, h, facing, **kw):
    """Box whose placement origin is the footprint centre; the facing is a rotation about that
    centre (local +Y = front).  Width is measured along the row, depth across it."""
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    w, d = (x1 - x0), (y1 - y0)
    if facing in ("EAST", "WEST"):
        w, d = d, w
    return element(cls, key, name, placement(cx, cy, z0, ref=FACING_REF[facing]), extrude(rect_profile(w, d), h), **kw)


ELEMENTS = {}

# ---- access floor (35 mm panel following the room outline, cut round the columns) ----
outer = f.createIfcPolyline([f.createIfcCartesianPoint((float(x), float(y))) for x, y in ROOM_OUTLINE + ROOM_OUTLINE[:1]])
holes = []
for c in COLUMNS:
    cx, cy, h2 = GRID_X[c[0]], GRID_Y[c[1]], COLUMN_SIZE / 2
    ring = [(cx - h2, cy - h2), (cx + h2, cy - h2), (cx + h2, cy + h2), (cx - h2, cy + h2), (cx - h2, cy - h2)]
    holes.append(f.createIfcPolyline([f.createIfcCartesianPoint((float(x), float(y))) for x, y in ring]))
floor_prof = f.create_entity("IfcArbitraryProfileDefWithVoids", ProfileType="AREA", ProfileName="ROOM OUTLINE",
                             OuterCurve=outer, InnerCurves=holes)
floor = element("IfcCovering", "accessfloor", "ACCESS FLOOR", placement(0, 0, Z_FF - PANEL_THK),
                extrude(floor_prof, PANEL_THK), predefined="FLOORING", objtype="AccessFloor", tag="AF-1",
                description="Raised access floor, 35 mm panel, top at FF +/-0; pedestals and plenum not modelled")
add_pset(floor, "Pset_DCM_AccessFloor", {"Tag": "AF-1", "PanelThicknessMm": PANEL_THK, "TopElevation": Z_FF,
                                         "TileSizeMm": TILE, "GridOrigin": "SOUTH-WEST INTERNAL CORNER",
                                         "SlabTopElevation": Z_SLAB_TOP, "PlenumDepthMm": Z_PANEL_UNDERSIDE - Z_SLAB_TOP,
                                         "UnderPanelClearanceMm": UNDERPANEL_CLEAR}, "AF-1")
ELEMENTS["floor"] = [floor]

# ---- structural columns ----
ELEMENTS["columns"] = []
for c in COLUMNS:
    cx, cy = GRID_X[c[0]], GRID_Y[c[1]]
    h2 = COLUMN_SIZE / 2
    col = facing_box("IfcColumn", "col/" + c, "COL-%s" % c, cx - h2, cx + h2, cy - h2, cy + h2, Z_FF, COLUMN_HEIGHT,
                     "NORTH", predefined="COLUMN", objtype="Column", tag=c,
                     description="Structural column, grid %s/%s, FF to soffit" % (c[0], c[1]))
    add_pset(col, "Pset_DCM_Column", {"Tag": "COL-%s" % c, "GridRef": "%s/%s" % (c[0], c[1]), "Width": COLUMN_SIZE,
                                      "Depth": COLUMN_SIZE, "Height": COLUMN_HEIGHT, "BaseElevation": Z_FF,
                                      "TopElevation": Z_SOFFIT, "CentreXMm": cx, "CentreYMm": cy,
                                      "GridOffsetFromTileGridMm": 150.0}, c)
    ELEMENTS["columns"].append(col)

# ---- racks ----
ELEMENTS["racks"] = []
for r in RACKS:
    w, d, desc = CAB_TYPES[r["ctype"]]
    e = facing_box("IfcFurniture", "rack/" + r["tag"], r["tag"], r["x0"], r["x1"], r["y0"], r["y1"], Z_FF,
                   CABINET_HEIGHT, r["facing"], predefined="USERDEFINED", objtype="Rack", tag=r["tag"],
                   description=desc)
    add_pset(e, "Pset_DCM_Rack", {
        "Tag": r["tag"], "Row": r["row"], "CabinetType": r["ctype"], "Description": desc, "Width": w, "Depth": d,
        "Height": CABINET_HEIGHT, "RackUnits": RACK_RU, "FrontFaces": r["facing"],
        "FacingRotationDeg": FACING_DEG[r["facing"]], "FrontVectorX": FRONT_VEC[r["facing"]][0],
        "FrontVectorY": FRONT_VEC[r["facing"]][1], "FrontIsLocalAxis": "+Y", "TileAddress": tile_address(r["x0"], r["y0"]),
        "BayIndex": r["bay"], "KWPerCabinet": RACK_KW, "LoadKg": RACK_KG,
        "Distributor": r["ctype"].startswith("N"), "RowCentrelineYMm": ROWD[r["row"]]["y"],
        "FootprintMinXMm": r["x0"], "FootprintMaxXMm": r["x1"], "FootprintMinYMm": r["y0"], "FootprintMaxYMm": r["y1"]},
        r["tag"])
    ELEMENTS["racks"].append(e)

# ---- CRAH units ----
ELEMENTS["crahs"] = []
for c in CRAHS:
    e = facing_box("IfcUnitaryEquipment", "crah/" + c["tag"], c["tag"], c["x0"], c["x1"], c["y0"], c["y1"], Z_FF,
                   CRAH_HEIGHT, c["facing"], predefined="AIRHANDLER", objtype="CRAH", tag=c["tag"],
                   description="Computer-room air handler, chilled water (%s)" % c["kind"])
    add_pset(e, "Pset_DCM_CRAH", {
        "Tag": c["tag"], "Placement": c["kind"], "Row": c["row"], "Width": c["x1"] - c["x0"],
        "Depth": c["y1"] - c["y0"], "Height": CRAH_HEIGHT, "CapacityKW": c["kw"], "AirflowM3h": c["airflow"],
        "Service": "CHILLED WATER, %s" % c["branch"], "FrontFaces": c["facing"],
        "FacingRotationDeg": FACING_DEG[c["facing"]], "FrontVectorX": FRONT_VEC[c["facing"]][0],
        "FrontVectorY": FRONT_VEC[c["facing"]][1], "FrontIsLocalAxis": "+Y", "TileAddress": tile_address(c["x0"], c["y0"]),
        "ChilledWaterConsumer": True}, c["tag"])
    ELEMENTS["crahs"].append(e)

# ---- PDUs ----
ELEMENTS["pdus"] = []
PDU_REC = []
for tag, row, tile, x0, y0, facing in PDUS:
    e = facing_box("IfcElectricDistributionBoard", "pdu/" + tag, tag, x0, x0 + PDU_W, y0, y0 + PDU_D, Z_FF, PDU_H,
                   facing, predefined="USERDEFINED", objtype="PDU", tag=tag,
                   description="Power distribution unit, 225 kVA, serves row %s" % row)
    PDU_REC.append((e, tag, row, tile, x0, y0, facing))
    ELEMENTS["pdus"].append(e)

# ---- cold-aisle containment CAC-BC ----
ELEMENTS["containment"] = []
for i, (xa, xb) in enumerate(CAC_ROOF_PANELS, 1):
    e = facing_box("IfcBuildingElementProxy", "cac/roof%d" % i, "CAC-BC ROOF PANEL %d" % i, xa, xb,
                   AISLE_BC_MID - CAC_ROOF_WIDTH / 2, AISLE_BC_MID + CAC_ROOF_WIDTH / 2, CAC_ROOF_UNDERSIDE,
                   CAC_ROOF_THK, "NORTH", predefined="USERDEFINED", objtype="Containment", tag="CAC-BC-R%d" % i,
                   description="Cold-aisle containment roof panel (fixed obstruction > 1200 wide; heads beneath)")
    add_pset(e, "Pset_DCM_Containment", {"Tag": "CAC-BC", "Contains": "ROWS B / C", "Part": "ROOF", "PanelIndex": i,
                                         "RoofWidthMm": CAC_ROOF_WIDTH, "RoofThicknessMm": CAC_ROOF_THK,
                                         "RoofUndersideElevation": CAC_ROOF_UNDERSIDE, "LengthMm": xb - xa,
                                         "RoofPanelsInKit": 4, "EndDoorsInKit": 4}, "roof%d" % i)
    ELEMENTS["containment"].append(e)
for i, (xa, xb) in enumerate(CAC_DOORS, 1):
    # end doors of the containment kit: real doors (IfcDoor), standing on the floor at the aisle ends
    e = facing_box("IfcDoor", "cac/door%d" % i, "CAC-BC END DOOR %d" % i, xa, xb,
                   AISLE_BC[0], AISLE_BC[1], Z_FF, CAC_DOOR_H, "NORTH", predefined="DOOR",
                   objtype="EndDoor", tag="CAC-BC-D%d" % i,
                   description="Cold-aisle containment end door (CAC-BC), 60 x 2055.5")
    e.OverallHeight = CAC_DOOR_H
    e.OverallWidth = AISLE_BC[1] - AISLE_BC[0]
    e.OperationType = "DOUBLE_DOOR_SLIDING"
    add_pset(e, "Pset_DCM_Containment", {"Tag": "CAC-BC", "Contains": "ROWS B / C", "Part": "DOOR", "PanelIndex": i,
                                         "DoorThicknessMm": CAC_DOOR_THK, "DoorHeightMm": CAC_DOOR_H,
                                         "DoorWidthMm": AISLE_BC[1] - AISLE_BC[0]}, "door%d" % i)
    ELEMENTS["containment"].append(e)

# =============================================================================
# 5. SERVICES (segments, ports, systems, supports)
# =============================================================================
SYS_ENUM = {"TRAY": "DATA", "BUSWAY": "ELECTRICAL", "CHW": "CHILLEDWATER"}
PORT_ENUM = {"TRAY": "CABLECARRIER", "BUSWAY": "CABLE", "CHW": "PIPE"}
SEG_OBJTYPE = {"TRAY": "CableTray", "BUSWAY": "Busway", "CHW": "ChilledWaterPipe"}
SEG_CLASS = {"TRAY": ("IfcCableCarrierSegment", "CABLETRAYSEGMENT"),
             "BUSWAY": ("IfcCableSegment", "BUSBARSEGMENT"),
             "CHW": ("IfcPipeSegment", "RIGIDSEGMENT")}


def _unit(s):
    (ax, ay), (bx, by) = s
    L = seg_len(*s)
    return ((bx - ax) / L, (by - ay) / L)


def joint_plan(segs, kind, half_w):
    """Segments of one run must touch at their joints but never interpenetrate (a joint overlap is a
    clash).  Every segment is extruded exactly node to node along its nominal centreline.
    Rectangular sections (tray, busway): the overlapping joint quadrant is notched out of the incoming
    segment at an L-corner and out of both trunk segments at a T-junction.
    Circular section (CHW): mitred joints -- at an elbow both legs are clipped by the 45 deg bisector
    plane through the node; at a tee the two trunk pieces and the branch are clipped by the two 45 deg
    planes through the node (a mitred tee), so the pieces meet on shared planar faces.
    Returns per segment: dict(s_off, e_off, notches[(end, side, length)], clips[(end, normal_xy)])."""
    def side_of(seg_dir, other_dir):
        nx, ny = -seg_dir[1], seg_dir[0]
        return "left" if nx * other_dir[0] + ny * other_dir[1] > 0 else "right"

    r2 = 1.0 / math.sqrt(2.0)
    plan = [dict(s_off=0.0, e_off=0.0, notches=[], clips=[]) for _ in segs]
    inc = {}
    for i, (a, b) in enumerate(segs):
        inc.setdefault(a, []).append((i, "start"))
        inc.setdefault(b, []).append((i, "end"))
    for node, lst in inc.items():
        if len(lst) < 2:
            continue
        ins = [i for i, e in lst if e == "end"]
        outs = [i for i, e in lst if e == "start"]
        assert len(ins) == 1, (node, lst)
        i_in = ins[0]
        d_in = _unit(segs[i_in])
        straight = [o for o in outs if _unit(segs[o]) == d_in]
        turns = [o for o in outs if abs(_unit(segs[o])[0] * d_in[0] + _unit(segs[o])[1] * d_in[1]) < 1e-9]
        assert len(straight) + len(turns) == len(outs) and len(turns) <= 1 and len(straight) <= 1, (node, lst)
        if not turns:
            continue                                   # in-line joint: end faces simply abut
        o_t = turns[0]
        d_t = _unit(segs[o_t])
        if kind == "CHW":
            if straight:                               # mitred tee
                nw = ((d_in[0] + d_t[0]) * r2, (d_in[1] + d_t[1]) * r2)
                ne = ((-d_in[0] + d_t[0]) * r2, (-d_in[1] + d_t[1]) * r2)
                plan[i_in]["clips"].append(("end", nw))
                plan[straight[0]]["clips"].append(("start", ne))
                plan[o_t]["clips"] += [("start", (-nw[0], -nw[1])), ("start", (-ne[0], -ne[1]))]
            else:                                      # mitred elbow (outer wedge left open)
                m = ((d_in[0] + d_t[0]) * r2, (d_in[1] + d_t[1]) * r2)
                plan[i_in]["clips"].append(("end", m))
                plan[o_t]["clips"].append(("start", (-m[0], -m[1])))
        else:
            plan[i_in]["notches"].append(("end", side_of(d_in, d_t), half_w))
            if straight:                               # tee: both trunk segments yield on the branch side
                o = straight[0]
                plan[o]["notches"].append(("start", side_of(_unit(segs[o]), d_t), half_w))
    return plan


def notch_box(w, h, L, end, side, length):
    """Removal solid for one joint notch, in the segment's local frame (X = left, Y = up, Z = along).
    Inner faces are exact (centre plane, notch plane); outer faces overshoot by 1 mm."""
    half = w / 2.0 + 1.0
    hh = h + 2.0
    cx = half / 2.0 if side == "left" else -half / 2.0
    prof = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
                           Position=f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((cx, 0.0)), None),
                           XDim=half, YDim=hh)
    z0, z1 = (L - length, L + 1.0) if end == "end" else (-1.0, length)
    pos = f.createIfcAxis2Placement3D(p3(0, 0, z0), d3(0, 0, 1), d3(1, 0, 0))
    return f.createIfcExtrudedAreaSolid(prof, pos, d3(0, 0, 1), float(z1 - z0))


def clip_halfspace(d, node_z, n_world):
    """Half-space (segment local frame) through the node whose material -- the side the plane normal
    points to -- is removed by the clipping."""
    lx = (-d[1], d[0])
    nx = n_world[0] * lx[0] + n_world[1] * lx[1]
    nz = n_world[0] * d[0] + n_world[1] * d[1]
    plane = f.createIfcPlane(f.createIfcAxis2Placement3D(p3(0, 0, node_z), f.createIfcDirection((nx, 0.0, nz)),
                                                         f.createIfcDirection((0.0, 1.0, 0.0))))
    return f.createIfcHalfSpaceSolid(plane, False)


SEG_ELEMS = {}
SEG_INFO = []
JOINTS = {}
for tag, svc in SERVICES.items():
    kind = svc["kind"]
    cls, ptype = SEG_CLASS[kind]
    SEG_ELEMS[tag] = []
    half_w = CHW_OD / 2.0 if kind == "CHW" else svc["w"] / 2.0
    JOINTS[tag] = joint_plan(SEGMENTS[tag], kind, half_w)
    for i, (a, b) in enumerate(SEGMENTS[tag], 1):
        jp = JOINTS[tag][i - 1]
        L = seg_len(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        s0, e0 = jp["s_off"], jp["e_off"]
        Lx = L - s0 + e0                               # extruded length
        jp["L"], jp["Lx"] = L, Lx
        plc = placement(a[0] + dx * s0, a[1] + dy * s0, svc["z"], axis=(dx, dy, 0.0), ref=(-dy, dx, 0.0))
        prof = circle_profile(CHW_OD / 2) if kind == "CHW" else rect_profile(svc["w"], svc["h"])
        solid = extrude(prof, Lx)
        rep_type = "SweptSolid"
        for end, side, length in jp["notches"]:
            solid = f.createIfcBooleanResult("DIFFERENCE", solid, notch_box(svc["w"], svc["h"], Lx, end, side, length))
            rep_type = "CSG"
        for end, nrm in jp["clips"]:
            solid = f.createIfcBooleanClippingResult("DIFFERENCE", solid,
                                                     clip_halfspace((dx, dy), (L - s0) if end == "end" else -s0, nrm))
            rep_type = "Clipping"
        end_target = TAP_TARGETS.get(b) if kind == "CHW" else None
        name = "%s-%02d" % (tag, i)
        e = f.create_entity(cls, GlobalId=gid("el/seg/%s/%d" % (tag, i)), Name=name, ObjectPlacement=plc,
                            Representation=f.createIfcProductDefinitionShape(None, None, [
                                f.createIfcShapeRepresentation(body_ctx, "Body", rep_type, [solid])]),
                            ObjectType=SEG_OBJTYPE[kind] + ((" Tap to %s" % end_target) if end_target else ""),
                            Tag=name,
                            Description="%s %s segment %d (under-floor plenum)" % (tag, svc["name"], i),
                            PredefinedType=ptype)
        CONTAINED.append(e)
        SEG_ELEMS[tag].append(e)
        SEG_INFO.append((tag, i, a, b, e))

# --- connectivity: ports + IfcRelConnectsPorts at every node ---
for tag, svc in SERVICES.items():
    kind = svc["kind"]
    segs = SEGMENTS[tag]
    elems = SEG_ELEMS[tag]
    node_inc = {}
    for i, (a, b) in enumerate(segs):
        node_inc.setdefault(a, []).append((i, 0))
        node_inc.setdefault(b, []).append((i, 1))
    ports_of = {i: [] for i in range(len(segs))}
    pcount = [0]

    entry_node = svc["polylines"][0][0]
    entry_node = (r1(entry_node[0]), r1(entry_node[1]))

    def mkport(i, end, flow, objtype=None):
        # ports sit on the logical node (nominal centreline end), whatever the joint trimming
        pcount[0] += 1
        jp = JOINTS[tag][i]
        zloc = (jp["L"] - jp["s_off"]) if end else -jp["s_off"]
        p = f.create_entity("IfcDistributionPort", GlobalId=gid("port/%s/%d/%d" % (tag, i, pcount[0])),
                            Name="%s-%02d/%s%d" % (tag, i + 1, "E" if end else "S", pcount[0]),
                            ObjectType=objtype, ObjectPlacement=placement(0, 0, zloc,
                                                                          rel=elems[i].ObjectPlacement),
                            FlowDirection=flow, PredefinedType=PORT_ENUM[kind], SystemType=SYS_ENUM[kind])
        ports_of[i].append(p)
        return p

    for node, inc in sorted(node_inc.items()):
        if len(inc) == 1:
            i, end = inc[0]
            if node == entry_node and end == 0:
                mkport(i, end, "SINK", "ServiceEntry")
            else:
                tgt = TAP_TARGETS.get(node) if kind == "CHW" else None
                mkport(i, end, "SOURCE", "Termination" + (" at %s" % tgt if tgt else ""))
            continue
        hub = [x for x in inc if x[1] == 1][0]          # the segment arriving from the entry side
        for other in inc:
            if other == hub:
                continue
            hp = mkport(hub[0], 1, "SOURCE")
            op = mkport(other[0], other[1], "SINK")
            f.create_entity("IfcRelConnectsPorts", GlobalId=gid("conn/%s/%s/%d" % (tag, node, other[0])),
                            RelatingPort=hp, RelatedPort=op)
    for i, ps in ports_of.items():
        f.create_entity("IfcRelNests", GlobalId=gid("nest/%s/%d" % (tag, i)), RelatingObject=elems[i],
                        RelatedObjects=ps)

# --- busway supports (E-101: 1500 max) ---
SUPPORTS = []
_seen = set()
for a, b in SEGMENTS["BW-1"]:
    L = seg_len(a, b)
    n = int(math.ceil(L / BUS_SUPPORT_SPACING - 1e-9))
    for k in range(n + 1):
        t = min(max(k * L / n, 20.0), L - 20.0)
        x = a[0] + (b[0] - a[0]) * t / L
        y = a[1] + (b[1] - a[1]) * t / L
        key = (round(x, 1), round(y, 1))
        if any(abs(key[0] - s[0]) + abs(key[1] - s[1]) < 100.0 for s in _seen):
            continue
        _seen.add(key)
        SUPPORTS.append((x, y, a[1] == b[1]))
ELEMENTS["supports"] = []
for i, (x, y, along_x) in enumerate(SUPPORTS, 1):
    zt = Z_BUS - BUS_H / 2                       # seated on the busway underside (face contact, no overlap)
    hx, hy = (20.0, BUS_W / 2) if along_x else (BUS_W / 2, 20.0)
    e = facing_box("IfcBuildingElementProxy", "sup/%d" % i, "SUP-%02d" % i, x - hx, x + hx, y - hy, y + hy,
                   Z_SLAB_TOP, zt - Z_SLAB_TOP, "NORTH", predefined="USERDEFINED", objtype="Support",
                   tag="SUP-%02d" % i, description="Slab-mounted floor stand (support), max 1400 centres")
    add_pset(e, "Pset_DCM_Support", {"Tag": "SUP-%02d" % i, "SupportedRun": "BW-1", "SupportType": "FLOOR STAND",
                                     "MaxSpacingMm": BUS_SUPPORT_MAX, "DesignSpacingMm": BUS_SUPPORT_SPACING,
                                     "CentreXMm": x, "CentreYMm": y, "TopElevation": zt}, "sup%d" % i)
    ELEMENTS["supports"].append(e)


def max_unsupported_span():
    best = 0.0
    for a, b in SEGMENTS["BW-1"]:
        on = []
        for x, y, _ in SUPPORTS:
            if pt_seg_dist((x, y), a, b) < 1.0:
                on.append(abs(x - a[0]) + abs(y - a[1]))
        on = sorted(on)
        L = seg_len(a, b)
        chain = [0.0] + on + [L]
        best = max(best, max(q - p for p, q in zip(chain[:-1], chain[1:])))
    return best


MAX_BUS_SPAN = max_unsupported_span()

# ---- sprinklers ----
ELEMENTS["sprinklers"] = []
HEADS = []
for i, (x, y) in enumerate(CEILING_HEADS, 1):
    HEADS.append(dict(tag="SPK-C%03d" % i, x=x, y=y, z=Z_DEFLECTOR, h=Z_SOFFIT - Z_DEFLECTOR, kind="CEILING",
                      note=RELOCATED_HEADS.get((x, y), "on grid")))
for i, x in enumerate(INAISLE_HEADS_X, 1):
    HEADS.append(dict(tag="SPK-A%02d" % i, x=x, y=AISLE_BC_MID, z=Z_INAISLE_DEFLECTOR,
                      h=CAC_ROOF_UNDERSIDE - Z_INAISLE_DEFLECTOR, kind="IN-AISLE (UNDER CAC-BC ROOF)",
                      note="hangs from the containment roof soffit"))
HEAD_ELEMS = []
for hd in HEADS:
    e = element("IfcFireSuppressionTerminal", "spk/" + hd["tag"], hd["tag"], placement(hd["x"], hd["y"], hd["z"]),
                extrude(circle_profile(HEAD_RADIUS), hd["h"]), predefined="SPRINKLER", objtype="Sprinkler",
                tag=hd["tag"], description="Pendent sprinkler head, %s; placement origin = deflector" % hd["kind"])
    HEAD_ELEMS.append(e)
    ELEMENTS["sprinklers"].append(e)

# =============================================================================
# 6. DIAGNOSTICS (clearances, length split, tiers) -> Psets
# =============================================================================


def svc_top(tag, envelope=True):
    s = SERVICES[tag]
    if s["kind"] == "CHW":
        return s["z"] + (CHW_JACKET_OD if envelope else CHW_OD) / 2
    return s["z"] + s["h"] / 2


def svc_bottom(tag, envelope=True):
    s = SERVICES[tag]
    if s["kind"] == "CHW":
        return s["z"] - (CHW_JACKET_OD if envelope else CHW_OD) / 2
    return s["z"] - s["h"] / 2


for hd, e in zip(HEADS, HEAD_ELEMS):
    props = {"Tag": hd["tag"], "HeadType": hd["kind"], "DeflectorElevation": hd["z"],
             "KeepClearBelowMm": SPRINKLER_STANDOFF, "KeepClearZoneBottomElevation": hd["z"] - SPRINKLER_STANDOFF,
             "Relocation": hd["note"], "CentreXMm": hd["x"], "CentreYMm": hd["y"]}
    nearest = 1e18
    for tag in SERVICES:
        under = [seg for seg in SEGMENTS[tag]
                 if (lambda bx: bx[0] <= hd["x"] <= bx[1] and bx[2] <= hd["y"] <= bx[3])(seg_box(tag, *seg, envelope=True))]
        key = {"TRAY": "Tray", "BUSWAY": "Busway", "CHW": "CHW"}[SERVICES[tag]["kind"]]
        props["%sPassesUnder" % key] = bool(under)
        if under:
            props["%sVerticalClearanceMm" % key] = hd["z"] - svc_top(tag)
        d = min(pt_seg_dist((hd["x"], hd["y"]), a, b) for a, b in SEGMENTS[tag])
        props["%sNearestPlanDistanceMm" % key] = d
        props["%sVerticalOffsetBelowDeflectorMm" % key] = hd["z"] - svc_top(tag)
        nearest = min(nearest, hd["z"] - svc_top(tag))
    props["MinServiceClearanceBelowDeflectorMm"] = nearest
    props["StandoffZoneClear"] = nearest >= SPRINKLER_STANDOFF
    add_pset(e, "Pset_DCM_Sprinkler", props, hd["tag"])

PDU_DIAG = {}
for e, tag, row, tile, x0, y0, facing in PDU_REC:
    cx, cy = x0 + PDU_W / 2, y0 + PDU_D / 2
    best = min((pt_seg_dist((cx, cy), a, b), a, b) for a, b in SEGMENTS["CHW-1"])
    plan_gap = min(max(axis_gap(bx[0], bx[1], x0, x0 + PDU_W), axis_gap(bx[2], bx[3], y0, y0 + PDU_D))
                   for bx in (seg_box("CHW-1", a, b, envelope=True) for a, b in SEGMENTS["CHW-1"]))
    vclr = PDU_H - svc_top("CHW-1")
    in_space = plan_gap == 0.0 and svc_top("CHW-1") > PDU_H and svc_bottom("CHW-1") < PDU_H + PDU_DEDICATED_SPACE
    PDU_DIAG[tag] = dict(vertical=vclr, plan_gap=plan_gap, in_dedicated_space=in_space)
    add_pset(e, "Pset_DCM_PDU", {
        "Tag": tag, "ServesRow": row, "Width": PDU_W, "Depth": PDU_D, "Height": PDU_H, "RatingKVA": 225.0,
        "FrontFaces": facing, "FacingRotationDeg": FACING_DEG[facing], "FrontVectorX": FRONT_VEC[facing][0],
        "FrontVectorY": FRONT_VEC[facing][1], "FrontIsLocalAxis": "+Y", "TileAddress": tile,
        "WorkingSpaceMm": PDU_WORKING_SPACE, "DedicatedSpaceAboveMm": PDU_DEDICATED_SPACE,
        "DedicatedSpaceTopElevation": PDU_H + PDU_DEDICATED_SPACE,
        "CHWVerticalClearanceMm": vclr, "CHWPlanGapToFootprintMm": plan_gap,
        "CHWNearestCentrelineDistanceMm": best[0], "CHWInDedicatedSpace": in_space}, tag)

LENGTHS = {}
for tag, svc in SERVICES.items():
    tot = sum(seg_len(a, b) for a, b in SEGMENTS[tag])
    under = sum(seg_len(a, b) for a, b in SEGMENTS[tag] if svc_top(tag) <= Z_FF)
    over = sum(seg_len(a, b) for a, b in SEGMENTS[tag] if svc_bottom(tag) >= MIN_CLEAR_HEIGHT)
    LENGTHS[tag] = dict(total=float(tot), underfloor=float(under), overhead=float(over),
                        occupied_band=float(tot - under - over))

for tag, i, a, b, e in SEG_INFO:
    svc = SERVICES[tag]
    bx = seg_box(tag, a, b, envelope=True)
    props = {"Service": svc["name"], "ServiceTag": tag, "ServiceKind": svc["kind"], "SegmentIndex": i,
             "Length": seg_len(a, b), "StartXMm": a[0], "StartYMm": a[1], "EndXMm": b[0], "EndYMm": b[1],
             "CentrelineElevation": svc["z"], "TopElevation": svc_top(tag), "BottomElevation": svc_bottom(tag),
             "ElevationZone": "UNDERFLOOR PLENUM", "Tier": {"TRAY": 1, "BUSWAY": 1, "CHW": 2}[svc["kind"]],
             "BelowFinishedFloor": True, "InClearHeightBand": False, "AboveClearHeight": False}
    jp = JOINTS[tag][i - 1]
    trims = ["notch %s-%s %.1f" % (en, sd, ln) for en, sd, ln in jp["notches"]] + \
            ["mitre %s (%.3f,%.3f)" % (en, nv[0], nv[1]) for en, nv in jp["clips"]]
    props["JointTrim"] = "; ".join(trims) if trims else "none"
    if svc["kind"] == "CHW":
        props.update({"OuterDiameter": CHW_OD, "InsulationThicknessMm": CHW_INSUL, "JacketOuterDiameterMm": CHW_JACKET_OD,
                      "NominalSize": "DN100", "ClashEnvelopeDiameterMm": CHW_JACKET_OD})
        if b in TAP_TARGETS:
            props["TerminatesAt"] = TAP_TARGETS[b]
    else:
        props.update({"Width": svc["w"], "Height": svc["h"]})
    if svc["kind"] in ("TRAY", "BUSWAY"):
        other = "BW-1" if tag == "CT-1" else "CT-1"
        props["MinSeparationToOtherElectricalTierMm"] = min(box_sep(bx, seg_box(other, *s)) for s in SEGMENTS[other])
    if svc["kind"] == "BUSWAY":
        props["SupportMaxSpacingMm"] = BUS_SUPPORT_MAX
        props["SupportSpacingMm"] = BUS_SUPPORT_SPACING
    add_pset(e, "Pset_DCM_Service", props, "%s/%d" % (tag, i))

# distribution systems
SYSTEMS = {}
for tag, svc in SERVICES.items():
    s = f.create_entity("IfcDistributionSystem", GlobalId=gid("sys/" + tag), Name=tag,
                        Description="%s - %s" % (svc["name"], {"TRAY": "cable tray, ladder 683x127",
                                                               "BUSWAY": "busway 128x147",
                                                               "CHW": "steel pipe DN100, OD 114.3, 25.4 insulation"}[svc["kind"]]),
                        ObjectType=svc["kind"], LongName=svc["name"], PredefinedType=SYS_ENUM[svc["kind"]])
    SYSTEMS[tag] = s
    f.create_entity("IfcRelAssignsToGroup", GlobalId=gid("grp/" + tag), RelatedObjects=SEG_ELEMS[tag], RelatingGroup=s)
    f.create_entity("IfcRelServicesBuildings", GlobalId=gid("srv/" + tag), RelatingSystem=s, RelatedBuildings=[building])
    entry_d = min(pt_seg_dist(ENTRY, a, b) for a, b in SEGMENTS[tag])
    cov = {r: row_coverage(tag, r) for r in ROWD}
    props = {"ServiceTag": tag, "Service": svc["name"], "ServiceKind": svc["kind"],
             "TotalLengthMm": LENGTHS[tag]["total"], "UnderfloorLengthMm": LENGTHS[tag]["underfloor"],
             "OverheadLengthMm": LENGTHS[tag]["overhead"], "OccupiedBandLengthMm": LENGTHS[tag]["occupied_band"],
             "SegmentCount": len(SEGMENTS[tag]), "EntryXMm": ENTRY[0], "EntryYMm": ENTRY[1],
             "EntryPlanDistanceMm": entry_d, "TierCentrelineElevation": svc["z"],
             "TopElevation": svc_top(tag), "BottomElevation": svc_bottom(tag)}
    for r, v in cov.items():
        props["Row%sCoverage" % r] = round(v, 4)
    if svc["kind"] in ("TRAY", "BUSWAY"):
        props["MinTrayBuswaySeparationMm"] = MIN_TRAY_BUS_SEP
    if svc["kind"] == "BUSWAY":
        props["SupportCount"] = len(SUPPORTS)
        props["MaxUnsupportedSpanMm"] = MAX_BUS_SPAN
    if svc["kind"] == "CHW":
        props["WorstCRAHDistanceMm"] = max(
            min(pt_seg_dist((0.5 * (c["x0"] + c["x1"]), 0.5 * (c["y0"] + c["y1"]), CRAH_HEIGHT / 2), a, b, Z_CHW)
                for a, b in SEGMENTS[tag]) for c in CRAHS)
    add_pset(s, "Pset_DCM_ServiceSummary", props, tag)

spk_sys = f.create_entity("IfcDistributionSystem", GlobalId=gid("sys/FP"), Name="FP-1",
                          Description="Wet-pipe sprinkler heads (F-101)", ObjectType="SPRINKLER",
                          LongName="FIRE PROTECTION", PredefinedType="FIREPROTECTION")
f.create_entity("IfcRelAssignsToGroup", GlobalId=gid("grp/FP"), RelatedObjects=HEAD_ELEMS, RelatingGroup=spk_sys)

# ---- spatial containment ----
f.create_entity("IfcRelContainedInSpatialStructure", GlobalId=gid("contain/storey"), Name="DATA HALL 1 CONTENTS",
                RelatedElements=CONTAINED, RelatingStructure=storey)
add_pset(storey, "Pset_DCM_Hall", {"Hall": "DATA HALL 1", "Project": "MDC-2026-014", "RoomWidthMm": 27000.0,
                                    "RoomDepthMm": 24000.0, "NoSlabNotch": "x 18600..27000, y 15600..24000",
                                    "FinishedFloorElevation": Z_FF, "SoffitElevation": Z_SOFFIT,
                                    "MinimumClearHeightMm": MIN_CLEAR_HEIGHT, "SprinklerDeflectorElevation": Z_DEFLECTOR,
                                    "SprinklerStandoffMm": SPRINKLER_STANDOFF,
                                    "OverheadPathwayZoneMm": max(0.0, (Z_DEFLECTOR - SPRINKLER_STANDOFF) - MIN_CLEAR_HEIGHT),
                                    "RoutingZone": "UNDERFLOOR PLENUM"}, "hall")

# =============================================================================
# 7. RECONCILIATION LOG
# =============================================================================
RECON = {
    "project": "MDC-2026-014 Meridian Data Center - Data Hall 1",
    "model": os.path.basename(OUT_PATH),
    "units": "millimetres (IFC4 project length unit = mm)",
    "routing_summary": {
        tag: {"total_length_mm": round(v["total"], 1), "underfloor_length_mm": round(v["underfloor"], 1),
              "overhead_length_mm": round(v["overhead"], 1), "clear_height_band_length_mm": round(v["occupied_band"], 1),
              "tier_centreline_elevation_mm": SERVICES[tag]["z"],
              "entry_plan_distance_mm": round(min(pt_seg_dist(ENTRY, a, b) for a, b in SEGMENTS[tag]), 1),
              "row_coverage": {r: round(row_coverage(tag, r), 3) for r in ROWD}}
        for tag, v in LENGTHS.items()},
    "grand_total_length_mm": round(sum(v["total"] for v in LENGTHS.values()), 1),
    "min_tray_busway_separation_mm": round(MIN_TRAY_BUS_SEP, 1),
    "busway_supports": {"count": len(SUPPORTS), "max_unsupported_span_mm": round(MAX_BUS_SPAN, 1)},
    "pdu_chw_clearance": {k: {"vertical_mm": round(v["vertical"], 1), "plan_gap_mm": round(v["plan_gap"], 1),
                              "in_dedicated_space": v["in_dedicated_space"]} for k, v in PDU_DIAG.items()},
    "coordination_decisions": [
        "All three services run in the access-floor plenum: the A-301/A-602 vertical budget leaves no overhead zone (standoff bottom +2564.6 < 2600 clear height).",
        "Tray and busway share one entry point and cannot be 300 mm apart vertically under a 545 mm plenum, so they are kept >= 305 mm apart horizontally everywhere and never cross in plan (busway west comb, tray serpentine).",
        "CHW is on its own upper tier (centre -160) and crosses the electrical tier with > 160 mm vertical clearance (25.4 insulation / 168.3 jacket included).",
        "Joints: segments are extruded node to node; tray/busway joint quadrants are notched out (CSG difference) and CHW elbows/tees are mitred with half-space clips, so segments of one run touch on shared faces but never interpenetrate.",
        "Facing: racks, CRAHs and PDUs are placed at their footprint centre and rotated about it; local +Y is the front (NORTH = 0 deg, SOUTH = 180 deg).",
        "CHW pipe body is the bare DN100 OD 114.3; insulation thickness and jacket OD are carried in Pset_DCM_Service and used as the clash envelope in coordination.",
        "Diagnostics: per-head service clearances (Pset_DCM_Sprinkler), PDU-to-CHW clearance (Pset_DCM_PDU), tray/busway separation and length split (Pset_DCM_Service / Pset_DCM_ServiceSummary), busway supports (IfcBuildingElementProxy ObjectType 'Support'), CHW taps (ObjectType '... Tap to CRAH-nn') and Termination ports."
    ],
    "notes": [
        {"sheet": "A-101", "note": "Room 27000 x 24000, NE notch 8400 x 8400 'no slab'", "applied": "Access floor outline = L-shaped room outline; nothing modelled or routed in the notch"},
        {"sheet": "A-101", "note": "Access-floor tile grid 600, origin SW internal corner, tile address = tile of the SW corner", "applied": "All rows, PDUs and perimeter CRAHs set out from their tile addresses; addresses re-derived and asserted in the script"},
        {"sheet": "A-101", "note": "Structural grid 7050 / 7200 / 7200 both ways (150 off the tile grid), columns 600 x 600", "applied": "8 columns A1,B1,C1,A2,B2,C2,A3,B3 (C3 lies in the no-slab notch); modelled FF to soffit (3050)"},
        {"sheet": "A-101", "note": "Row centrelines 3000 / 2935 / 2465 / 2935 (12665 to north wall)", "applied": "Row CL y = 3000, 5935, 8400, 11335; footprint = CL +/- depth/2 (A-601 note 2)"},
        {"sheet": "A-101", "note": "Pitch class C: cold 1200 clear, hot 1800 clear", "applied": "Hot aisles A/B and C/D are 1800; contained cold aisle B/C is 1330 as dimensioned (>= 1200)"},
        {"sheet": "A-101", "note": "Cross aisle 1200 clear, east edge common to every row, 16 m max continuous run", "applied": "East edge derived = 12600 from the last-tile addresses; west edges step with the bays (11000/11200/10800/11200); longest run 9600 < 16000"},
        {"sheet": "A-101", "note": "Bays taken by structure or in-row CRAH omitted, row not re-spaced", "applied": "'2-600' terms leave 1200 gaps at the column lines (x 6600-7800, 13800-15000 / 13400-14600, 21000-22200 / 20600-21800); no cabinet straddles a column"},
        {"sheet": "A-101", "note": "Perimeter CRAH face 900 from south wall; CRAH centres 8400 / 7800 / 8400", "applied": "CRAH-01..04 1200 x 900 on tiles B01, P01, AC01, AQ01"},
        {"sheet": "A-101", "note": "Each PDU front flush with the front face of its row", "applied": "Asserted in script for PDU-01..04"},
        {"sheet": "A-301", "note": "Ceiling slab soffit +3050; deflector plane 25.4 below soffit; 460 keep clear below", "applied": "Ceiling heads modelled with deflector at +3024.6; keep-clear zone bottom +2564.6; no service above the floor"},
        {"sheet": "A-301", "note": "Minimum clear height 2600 (ANSI/TIA-942), nothing below", "applied": "Enforced as headroom rule: no service segment between FF and +2600 (0 mm in the clear-height band)"},
        {"sheet": "A-301", "note": "Overhead space = between clear height and standoff zone", "applied": "2564.6 < 2600 -> zero-height overhead zone (A-602 red note); all three services routed in the access-floor plenum"},
        {"sheet": "A-301", "note": "Access floor 600 (slab -600), 35 panel, 565 plenum, under-floor tray top 20 below panel underside", "applied": "Access floor = 35 mm IfcCovering -35..0; every service top <= -55 (CHW jacket top -75.85, busway top -433, tray top -453)"},
        {"sheet": "A-301", "note": "Columns FF to soffit, hard obstructions at every elevation", "applied": "Columns modelled 0..3050 and kept clear in plan at all elevations (min plan clearance > 900); floor panel cut round them"},
        {"sheet": "A-301", "note": "Containment roof 55.5, cabinet 2000, in-aisle head +1890 (110 below roof), roof width 1530", "applied": "Roof panels +2000..+2055.5, in-aisle heads deflector +1890 hung from roof soffit"},
        {"sheet": "A-601", "note": "Cabinet schedule rows A-D, bay sequences, qty 26/21/20/27 = 94, depth 1200/1070, 42U, 2000 high, 8 kW, 1363 kg", "applied": "94 racks generated by accumulating the bay sequences from the first tile; quantities and last tiles asserted"},
        {"sheet": "A-601", "note": "Cabinet types C1 600x1200, C2 600x1070, N1 800x1200, N2 800x1070", "applied": "Rack widths/depths per type; distributor cabinets flagged in Pset_DCM_Rack"},
        {"sheet": "A-601", "note": "CRAH schedule: perimeter 1200x900 100 kW DN100; in-row 600x1070 (B,D) / 600x1200 (A,C) 50 kW DN50; 2000 high", "applied": "16 IfcUnitaryEquipment (4 perimeter + 12 in-row), in-row units take a full bay and face with their row"},
        {"sheet": "A-601", "note": "PDU schedule 762 x 813 x 1959, 225 kVA, 900 working space", "applied": "4 PDUs on tiles AN05, AM10, AL14, AO19 (E-101 plan positions)"},
        {"sheet": "A-601", "note": "Typical cabinet elevation 2000 overall, 1867 = 42U, 1U = 44.45", "applied": "Rack height 2000 (overall); RU recorded as 42"},
        {"sheet": "A-601", "note": "Row D overall 20400", "applied": "Row D x 1800..22200 = 20400 (check passes)"},
        {"sheet": "A-602", "note": "CAC-BC: 4 roof panels, 1530 wide, 55.5 thick, underside 2000, 4 end doors 60 x 2055.5", "applied": "Roof split at columns A1/B1 and at the cross-aisle break (1800-6750, 7350-11400, 12600-13950, 14550-21000), roof y 6370-7900; end doors (IfcDoor) just outside the roof ends at x 1740, 11400, 12540, 21000"},
        {"sheet": "A-602", "note": "CT-1 cable tray ladder 683 x 127, 300 from power", "applied": "Tray 683 x 127; min tray/busway separation 305 mm on at least one axis everywhere"},
        {"sheet": "A-602", "note": "BW-1 busway 128 x 147, support at 1500 max", "applied": "Busway 128 x 147; slab-mounted stands at <= 1400 centres (max unsupported span %.0f mm)" % MAX_BUS_SPAN},
        {"sheet": "A-602", "note": "CHW-1 steel DN100 OD 114.3, insulate 25 min", "applied": "Pipe body OD 114.3; 25.4 insulation (168.3 jacket) used as the clash envelope; >160 mm clear of every other solid"},
        {"sheet": "A-602", "note": "Vertical budget: deflector +3025, 425 standoff above clear height, 545 under-floor pathway zone", "applied": "Under-floor zone -600..-55 used: electrical tier -580..-433, CHW tier -244..-76 (jacket)"},
        {"sheet": "M-101", "note": "CHW supply + return entry 2 x DN100 at west wall, 12470 from south wall", "applied": "CHW-1 network starts at (0, 12470)"},
        {"sheet": "M-101", "note": "Pipe every CRAH (perimeter and in-row); run a header along every row", "applied": "Headers at y=3900 (rows A/B) and y=9800 (rows C/D); taps to CRAH-01..04; every CRAH centroid within %.0f mm (3D) of the CHW" % max(min(pt_seg_dist((0.5 * (c['x0'] + c['x1']), 0.5 * (c['y0'] + c['y1']), CRAH_HEIGHT / 2), a, b, Z_CHW) for a, b in SEGMENTS['CHW-1']) for c in CRAHS)},
        {"sheet": "M-101", "note": "Jacket OD over insulation 168.3 must be coordinated for clash", "applied": "168.3 envelope (+25.4 extra margin) checked against every solid"},
        {"sheet": "M-101", "note": "914 service clearance in front of in-row CRAH", "applied": "Floor-level zone; nothing routed above the floor so it stays clear"},
        {"sheet": "M-101", "note": "Chilled-water consumers: rows 3 x 150 kW DN50, perimeter 4 x 400 kW DN100", "applied": "Recorded in CRAH Psets; single DN100 main modelled (branches DN50 not modelled)"},
        {"sheet": "E-101", "note": "Busway feed + telecom riser entry at west wall, 12470 from south wall", "applied": "Busway arrives along the west wall, tray on an E-W stub just north of it; both centrelines %.0f mm from the entry point so the 300 mm separation (305 used) holds right up to the wall; CHW starts on the entry point" % min(pt_seg_dist(ENTRY, a, b) for a, b in SEGMENTS["BW-1"])},
        {"sheet": "E-101", "note": "1800 dedicated electrical space above each PDU (NFPA 70 110.26(E)), no piping", "applied": "CHW never enters it (CHW under the floor, min plan gap to a PDU footprint %.0f mm)" % min(v["plan_gap"] for v in PDU_DIAG.values())},
        {"sheet": "E-101", "note": "900 working space at every PDU front", "applied": "Floor-level zone kept clear (no equipment or services above the floor there)"},
        {"sheet": "E-101", "note": "PDU 225 kVA each, one per row (one-line)", "applied": "Pset_DCM_PDU.RatingKVA / ServesRow"},
        {"sheet": "F-101", "note": "94 ceiling heads + 10 in-aisle heads; grid 1250 / 2500 typ", "applied": "104 IfcFireSuppressionTerminal; grid lines snapped 1250 off the notch walls and one head relocated off column C2 as drawn"},
        {"sheet": "F-101", "note": "460 clear below every deflector (nothing routed inside)", "applied": "All services under the floor: >= %.0f mm below every deflector" % min(hd["z"] - svc_top(t) for hd in HEADS for t in SERVICES)},
        {"sheet": "F-101", "note": "20.9 m2 per head / 4600 max spacing / 2300 max from wall / 1500 column keep-out", "applied": "Architect's head layout reproduced as drawn (not re-designed)"},
        {"sheet": "F-101", "note": "Heads required beneath obstructions wider than 1200 (containment roof)", "applied": "10 in-aisle heads under the 1530 roof; every service run is <= 683 wide and below the floor"},
        {"sheet": "F-101", "note": "Coverage-check table values 1100 / 600 / 0.7 m2", "applied": "Informational (as printed), not used for geometry"},
        {"sheet": "brief", "note": "Prefer the FF..2600 clear-height band for services", "applied": "Not applied: it contradicts the 2600 minimum clear height (A-301/A-602 'nothing below'); 0 mm of any service lies in that band"},
    ],
}

# =============================================================================
# 8. WRITE
# =============================================================================
_out_dir = os.path.dirname(os.path.abspath(OUT_PATH))
if not os.path.isdir(_out_dir):
    os.makedirs(_out_dir, exist_ok=True)
f.write(OUT_PATH)
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(OUT_PATH)), "reconciliation.json"), "w") as fh:
        json.dump(RECON, fh, indent=2)
except OSError:
    pass
