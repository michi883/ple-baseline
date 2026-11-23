"""Coordinated MEP model of DATA HALL 1 (dc_model hall_seed000_d000, project MDC-2026-014).

Builds the coordination background exactly as drawn on A-101 / A-301 / A-601 /
A-602 / M-101 / E-101 / F-101 and routes the three services (CT-1 telecom
cable tray, BW-1 power busway, CHW-1 chilled water) as straight, axis-aligned
segments.  Writes one IFC4 file (millimetre project units) to sys.argv[1]
(default: output/model.ifc next to this script).

Everything read off the drawing sheets is baked in below as literals; the
script never opens the PNGs, uses no network and is fully deterministic
(GlobalIds are name-based UUID5, header time stamp is fixed).

Routing concept (see ROUTING section):
  * A-602 detail 4 gives an 845 mm under-floor pathway zone and only 515 mm
    overhead.  Tray (127) + 300 clear (E-101 note 6) + busway (147) = 574 mm
    cannot be stacked overhead, but stacks in the plenum together with the
    insulated CHW main (168.3 jacket) in the 300 mm gap.  A-301 note 3 /
    A-602 "OVERHEAD OR PLENUM" permit plenum routing for all three services.
  * Each service is one tree on its own tier: entry stub at the west wall
    (x=0, y=9900 per M-101/E-101), a trunk under the west end of the rows
    (x=1800), and one header per hot aisle (busway/CHW y=4500, 9900, 15300 =
    1500 mm from both rows served; tray y=5000, 9900, 14800, <= 2000 mm;
    limit 2500).  Headers run x 1800..17000/17200, i.e. > 80 % of every row
    by row extent, by cabinet width and by cabinet count.  CHW adds short
    branches to the four perimeter CRAHs (<= 1835 mm in plan from each).
  * Every junction is a shared segment end point; every direction change
    starts a new segment.  Joints are mitred: each segment is extruded from
    junction centre to junction centre and clipped by 45-degree half-spaces,
    so adjacent solids of a run share a face and never overlap.
  * Nothing is placed in the clear-height band, under a sprinkler, above a
    PDU or near a column; tray/busway vertical clearance is 546 mm.
"""
import json
import math
import os
import re
import sys
import uuid

import ifcopenshell
import ifcopenshell.guid

OUT_PATH = (sys.argv[1] if len(sys.argv) > 1 else
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.ifc"))

# =============================================================================
# 1. DATUMS AND SIZES (A-301, A-602 general construction data / schedules)
# =============================================================================
HALL_X = 27000.0              # A-101 overall 27000
HALL_Y = 21000.0              # A-101 overall 21000
FFL = 0.0                     # top of access-floor panel
SLAB_TOP = -900.0             # top of structural slab
PANEL_T = 35.0                # access floor panel thickness
SOFFIT = 3600.0               # ceiling slab soffit = column height
CLEAR_MIN = 2600.0            # ANSI/TIA-942 minimum clear height
STANDOFF = 460.0              # clear below every deflector
DEFLECTOR_CEIL = SOFFIT - 25.4  # A-301: 25.4 below soffit (A-602: +3575)
ROOF_UNDERSIDE = 2000.0       # A-602 containment schedule
ROOF_T = 55.5
ROOF_W = 1400.0
DOOR_T = 60.0
DOOR_H = 2055.5
DEFLECTOR_AISLE = 1890.0      # A-301 detail 3 "IN-AISLE HEAD +1890"
UF_PANEL_CLEAR = 20.0         # ANSI/TIA-942-B 8.6.2: 20 under panel
TILE = 600.0                  # access floor grid, origin SW internal corner
CROSS_AISLE_E = 11400.0       # common east edge of the cross aisle (A-101 n.5)
CROSS_AISLE_CLEAR = 1200.0    # "1200 CLEAR"

CAB_H = 2000.0
CAB_D = 1200.0
BAY_W = {"C1": 600.0, "N1": 800.0, "CU": 600.0, "SP": 600.0, "-600": 600.0, "-800": 800.0}
CAB_DESC = {"C1": "SERVER CABINET, 600 WIDE", "N1": "DISTRIBUTOR CABINET, 800 WIDE"}

FACING_ROT = {"NORTH": 0.0, "SOUTH": 180.0, "EAST": -90.0, "WEST": 90.0}  # front = local +Y

# A-601 cabinet schedule (bay sequences transcribed, '·' -> space, '—' -> '-')
ROWS = [
    # row, centreline y (A-101), front faces, first tile, last tile, qty, bay sequence W->E
    ("A", 3000.0, "SOUTH", "D05", "AF05", 22, "4C1 CU 3C1 N1 3C1 CU CA 6C1 SP CU 5C1"),
    ("B", 6000.0, "NORTH", "D10", "AG10", 23, "4C1 CU 5C1 2N1 CU CA 7C1 SP CU 5C1"),
    ("C", 8400.0, "SOUTH", "D14", "AF14", 18, "3C1 CU 6C1 2-600 CU CA N1 4C1 CU SP C1 2-600 3C1"),
    ("D", 11400.0, "NORTH", "D19", "AG19", 23, "4C1 CU 3C1 2N1 2C1 CU CA 7C1 SP CU 5C1"),
    ("E", 13800.0, "SOUTH", "D23", "AF23", 22, "4C1 CU 5C1 N1 C1 CU CA 6C1 SP CU 5C1"),
    ("F", 16800.0, "NORTH", "D28", "AG28", 20, "4C1 CU 5C1 2-600 CU CA 2N1 5C1 SP -600 CU 4C1"),
]

# A-601 CRAH schedule: perimeter units, tiles B01 P01 AC01 AQ01, 1200 x 900, face north
PERIMETER_CRAH = [("CRAH-01", "B01"), ("CRAH-02", "P01"), ("CRAH-03", "AC01"), ("CRAH-04", "AQ01")]
PCRAH_W, PCRAH_D, PCRAH_H = 1200.0, 900.0, 2000.0
ICRAH_W, ICRAH_D, ICRAH_H = 600.0, 1200.0, 2000.0

# A-601 PDU schedule; A-101 note 8 (front flush with the row front face);
# E-101 measured: west face 1800 east of the row's east end (A-101 dim 4238).
PDUS = [("PDU-01", "A", "AJ05", "SOUTH"), ("PDU-02", "B", "AK10", "NORTH"),
        ("PDU-03", "C", "AJ14", "SOUTH"), ("PDU-04", "D", "AK19", "NORTH"),
        ("PDU-05", "E", "AJ23", "SOUTH"), ("PDU-06", "F", "AK28", "NORTH")]
PDU_W, PDU_D, PDU_H = 762.0, 813.0, 1959.0
PDU_GAP_FROM_ROW_END = 1800.0
PDU_WORKING = 900.0
PDU_DEDICATED = 1800.0

# Structural grid (A-101): A/B/C at 8400 spacing from the west wall, 1/2 at 8400.
GRID_X = {"A": 8400.0, "B": 16800.0, "C": 25200.0}
GRID_Y = {"1": 8400.0, "2": 16800.0}
COL_SIZE = 600.0

# Cold-aisle containment (A-602): roof panels are split by the cross aisle.
CONTAINMENT = [("CAC-BC", "ROWS B / C", 6600.0, 7800.0), ("CAC-DE", "ROWS D / E", 12000.0, 13200.0)]
ROOF_PANELS_X = [(1800.0, CROSS_AISLE_E - CROSS_AISLE_CLEAR), (CROSS_AISLE_E, 19800.0)]

# F-101: 9 x 7 ceiling grid 1500 + 3000 typ; heads at the column corners at
# B/2 and C/2 drawn relocated 60 mm clear of structure; 4 in-aisle heads per
# roof panel, 500 from each end, equal spacing, deflector 110 below roof.
CEIL_X = [1500.0 + 3000.0 * i for i in range(9)]
CEIL_Y = [1500.0 + 3000.0 * j for j in range(7)]
HEAD_RELOCATIONS = {(16500.0, 16500.0): (16440.0, 16500.0),   # column B/2
                    (25500.0, 16500.0): (25500.0, 16440.0)}   # column C/2
HEAD_R = 25.0
AISLE_HEADS_PER_PANEL = 4
AISLE_HEAD_END = 500.0

# Pathway section schedule (A-602) / E-101 / M-101
TRAY_W, TRAY_H = 683.0, 127.0
BUS_W, BUS_H = 128.0, 147.0
PIPE_OD = 114.3
PIPE_INS = 25.4
PIPE_JACKET_OD = 168.3

ENTRY = (0.0, 9900.0)       # M-101 / E-101 entry symbol, 9900 from south wall


# =============================================================================
# 2. DERIVED LAYOUT
# =============================================================================
def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def tile_of(address):
    m = re.fullmatch(r"([A-Z]+)(\d+)", address)
    return col_index(m.group(1)), int(m.group(2))


def tile_address(x, y):
    c = int(math.floor(x / TILE + 1e-9))
    r = int(math.floor(y / TILE + 1e-9)) + 1
    s = ""
    c1 = c + 1
    while c1 > 0:
        c1, rem = divmod(c1 - 1, 26)
        s = chr(65 + rem) + s
    return "%s%02d" % (s, r)


def layout_rows():
    racks, crahs, rows = [], [], {}
    for row, yc, face, first, last, qty, seq in ROWS:
        c0, r0 = tile_of(first)
        c1, r1 = tile_of(last)
        x = c0 * TILE
        y0, y1 = yc - CAB_D / 2.0, yc + CAB_D / 2.0
        assert int(y0 // TILE) + 1 == r0 == r1
        bays = []
        for tok in seq.split():
            m = re.fullmatch(r"(\d*)(C1|N1|CU|SP|CA|-600|-800)", tok)
            for _ in range(int(m.group(1) or 1)):
                term = m.group(2)
                if term == "CA":
                    assert CROSS_AISLE_E - x >= CROSS_AISLE_CLEAR
                    x = CROSS_AISLE_E
                    continue
                bays.append((term, x, x + BAY_W[term]))
                x += BAY_W[term]
        cabs = [b for b in bays if b[0] in ("C1", "N1")]
        cus = [b for b in bays if b[0] == "CU"]
        assert len(cabs) == qty and int(cabs[-1][1] // TILE) == c1
        for i, (term, xa, xb) in enumerate(cabs):
            racks.append(dict(tag="RACK-%s%02d" % (row, i + 1), row=row, index=i + 1, type=term,
                              x0=xa, x1=xb, y0=y0, y1=y1, face=face))
        for i, (term, xa, xb) in enumerate(cus):
            crahs.append(dict(tag="CRAH-%s%02d" % (row, i + 1), row=row, placement="IN ROW",
                              x0=xa, x1=xb, y0=y0, y1=y1, face=face, kw=50.0, airflow=9000.0,
                              service="CHILLED WATER, DN50", w=ICRAH_W, d=ICRAH_D, h=ICRAH_H))
        rows[row] = dict(y=yc, face=face, x0=c0 * TILE, x1=x, y0=y0, y1=y1, bays=bays,
                         front_y=(y0 if face == "SOUTH" else y1))
    return racks, crahs, rows


RACKS, INROW_CRAHS, ROWINFO = layout_rows()

PCRAHS = []
for tag, addr in PERIMETER_CRAH:
    c, r = tile_of(addr)
    PCRAHS.append(dict(tag=tag, row="-", placement="PERIMETER", x0=c * TILE, x1=c * TILE + PCRAH_W,
                       y0=(r - 1) * TILE, y1=(r - 1) * TILE + PCRAH_D, face="NORTH", kw=100.0,
                       airflow=20000.0, service="CHILLED WATER, DN100", w=PCRAH_W, d=PCRAH_D, h=PCRAH_H))

PDU_LIST = []
for tag, row, addr, face in PDUS:
    ri = ROWINFO[row]
    x0 = ri["x1"] + PDU_GAP_FROM_ROW_END
    y0 = ri["front_y"] if face == "SOUTH" else ri["front_y"] - PDU_D
    assert tile_address(x0, y0) == addr, (tag, tile_address(x0, y0), addr)
    PDU_LIST.append(dict(tag=tag, row=row, x0=x0, x1=x0 + PDU_W, y0=y0, y1=y0 + PDU_D, face=face, tile=addr))

COLUMNS = []
for gy in ("1", "2"):
    for gx in ("A", "B", "C"):
        COLUMNS.append(dict(tag="COL-%s%s" % (gx, gy), gx=gx, gy=gy, x=GRID_X[gx], y=GRID_Y[gy]))

ROOFS, DOORS = [], []
for tag, contains, ay0, ay1 in CONTAINMENT:
    ry0, ry1 = ay0 - (ROOF_W - (ay1 - ay0)) / 2.0, ay1 + (ROOF_W - (ay1 - ay0)) / 2.0
    for k, (px0, px1) in enumerate(ROOF_PANELS_X):
        ROOFS.append(dict(tag="%s-ROOF-%d" % (tag, k + 1), cac=tag, contains=contains, panel=k + 1,
                          x0=px0, x1=px1, y0=ry0, y1=ry1))
    dn = 0
    for px0, px1 in ROOF_PANELS_X:       # doors stand outside each roof end
        for dx0 in (px0 - DOOR_T, px1):
            dn += 1
            DOORS.append(dict(tag="%s-DOOR-%d" % (tag, dn), cac=tag, contains=contains,
                              x0=dx0, x1=dx0 + DOOR_T, y0=ry0, y1=ry1))

HEADS = []
n = 0
for y in CEIL_Y:
    for x in CEIL_X:
        n += 1
        rx, ry = HEAD_RELOCATIONS.get((x, y), (x, y))
        HEADS.append(dict(tag="SPK-C%02d" % n, kind="CEILING PENDENT", x=rx, y=ry, zd=DEFLECTOR_CEIL,
                          ztop=SOFFIT, relocated=(rx, ry) != (x, y), grid=(x, y)))
n = 0
for r in ROOFS:
    L = r["x1"] - r["x0"]
    s = (L - 2 * AISLE_HEAD_END) / (AISLE_HEADS_PER_PANEL - 1)
    for i in range(AISLE_HEADS_PER_PANEL):
        n += 1
        HEADS.append(dict(tag="SPK-IA%02d" % n, kind="IN-AISLE (%s)" % r["cac"], x=r["x0"] + AISLE_HEAD_END + i * s,
                          y=(r["y0"] + r["y1"]) / 2.0, zd=DEFLECTOR_AISLE, ztop=ROOF_UNDERSIDE,
                          relocated=False, grid=None))
assert len(HEADS) == 63 + 16


# =============================================================================
# 3. ROUTING (under-floor plenum, one tier per service)
# =============================================================================
# Tier centreline elevations (relative to FFL):
#   CT-1 tray  : top -60  (25 below panel underside -35; >= 20 required) -> z -187..-60
#   CHW-1 pipe : centre -460; jacket 168.3 / insulated 165.1 -> about -545..-375
#   BW-1 busway: bottom -880 (20 above slab -900)                          -> z -880..-733
# Tray/busway vertical clear = 546 mm (>= 300 on the z axis).
Z_TRAY = -60.0 - TRAY_H / 2.0
Z_CHW = -460.0
Z_BUS = -880.0 + BUS_H / 2.0

# Plan geometry.  Hot-aisle headers at 1500 from both rows they serve:
Y_AB, Y_CD, Y_EF = 4500.0, 9900.0, 15300.0
# The tray is the top tier (centre 124 mm below FFL), so its outer headers may sit
# 2000 from the outer row (A at 3000, F at 16800) and 1000 from the inner one;
# this shortens its trunk while staying well inside the 2500 limit.
Y_AB_TRAY, Y_EF_TRAY = 5000.0, 14800.0
X_TRUNK = 1800.0                 # under the west end of every row
X_END_AB = 17200.0               # >= 80 % of rows A/B by extent, bays and cabinet width
X_END_CD = 17200.0
X_END_EF = 17000.0
# CHW branches to the perimeter CRAHs (no row header passes them):
Y_CRAH01 = 2180.0                # trunk extension, CRAH-01 centre (1200, 450)
X_CRAH02, Y_CRAH02 = 9600.0, 2280.0
X_CRAH03, Y_CRAH03 = 17200.0, 1740.0
X_CRAH04 = 24500.0               # run end, CRAH-04 centre (25800, 450)


def comb(y_ab, y_ef, extra=()):
    e = ENTRY
    segs = [
        ("ENTRY STUB", (e[0], e[1]), (X_TRUNK, Y_CD), "C,D"),
        ("ROW HEADER C/D", (X_TRUNK, Y_CD), (X_END_CD, Y_CD), "C,D"),
        ("TRUNK SOUTH", (X_TRUNK, Y_CD), (X_TRUNK, y_ab), ""),
        ("TRUNK NORTH", (X_TRUNK, Y_CD), (X_TRUNK, y_ef), ""),
    ]
    return segs + list(extra)


SERVICES = [
    dict(key="CT-1", service="TELECOM", system="CT-1 TELECOM", sys_enum="DATA",
         ifc="IfcCableCarrierSegment", ptype="CABLETRAYSEGMENT", otype="CableTray",
         desc="CABLE TRAY, LADDER 683 x 127 (610 NOMINAL)", z=Z_TRAY, shape=("rect", TRAY_W, TRAY_H),
         segs=comb(Y_AB_TRAY, Y_EF_TRAY,
                   [("ROW HEADER A/B", (X_TRUNK, Y_AB_TRAY), (X_END_AB, Y_AB_TRAY), "A,B"),
                    ("ROW HEADER E/F", (X_TRUNK, Y_EF_TRAY), (X_END_EF, Y_EF_TRAY), "E,F")])),
    dict(key="BW-1", service="POWER", system="BW-1 POWER", sys_enum="ELECTRICAL",
         ifc="IfcCableSegment", ptype="BUSBARSEGMENT", otype="Busway",
         desc="BUSWAY 128 W x 147 H", z=Z_BUS, shape=("rect", BUS_W, BUS_H),
         segs=comb(Y_AB, Y_EF,
                   [("ROW HEADER A/B", (X_TRUNK, Y_AB), (X_END_AB, Y_AB), "A,B"),
                    ("ROW HEADER E/F", (X_TRUNK, Y_EF), (X_END_EF, Y_EF), "E,F")])),
    dict(key="CHW-1", service="CHILLED WATER", system="CHW-1 CHILLED WATER", sys_enum="CHILLEDWATER",
         ifc="IfcPipeSegment", ptype="RIGIDSEGMENT", otype="ChilledWaterPipe",
         desc="STEEL PIPE DN100, OD 114.3, INSULATED 25.4 (JACKET OD 168.3)", z=Z_CHW,
         shape=("circle", PIPE_OD / 2.0),
         segs=comb(Y_AB, Y_EF,
                   [("CRAH BRANCH CRAH-01", (X_TRUNK, Y_AB), (X_TRUNK, Y_CRAH01), ""),
                    ("ROW HEADER A/B", (X_TRUNK, Y_AB), (X_CRAH02, Y_AB), "A,B"),
                    ("ROW HEADER A/B", (X_CRAH02, Y_AB), (X_CRAH03, Y_AB), "A,B"),
                    ("CRAH BRANCH CRAH-02", (X_CRAH02, Y_AB), (X_CRAH02, Y_CRAH02), ""),
                    ("CRAH BRANCH CRAH-03", (X_CRAH03, Y_AB), (X_CRAH03, Y_CRAH03), ""),
                    ("CRAH BRANCH CRAH-04", (X_CRAH03, Y_CRAH03), (X_CRAH04, Y_CRAH03), ""),
                    ("ROW HEADER E/F", (X_TRUNK, Y_EF), (X_END_EF, Y_EF), "E,F")])),
]


# =============================================================================
# 4. IFC WRITER
# =============================================================================
NS = uuid.UUID("6d1f3c1e-6a0c-4f0e-9b39-0d5c1a2e2026")


class Model:
    def __init__(self):
        f = self.f = ifcopenshell.file(schema="IFC4")
        f.header.file_name.name = "model.ifc"
        f.header.file_name.time_stamp = "2026-07-27T09:00:00"
        f.header.file_name.author = ("JRK",)
        f.header.file_name.organization = ("MERIDIAN DIGITAL INFRASTRUCTURE",)
        f.header.file_name.originating_system = "dc_model solution.py (ifcopenshell)"
        f.header.file_name.authorization = "A. OKONKWO, PE"
        f.header.file_description.description = ("ViewDefinition [DesignTransferView_V1.0]",)
        self._pts, self._dirs = {}, {}
        self.contained = []

    def guid(self, key):
        return ifcopenshell.guid.compress(uuid.uuid5(NS, key).hex)

    def pt(self, c):
        c = tuple(float(round(v, 4)) + 0.0 for v in c)
        if c not in self._pts:
            self._pts[c] = self.f.create_entity("IfcCartesianPoint", Coordinates=c)
        return self._pts[c]

    def d(self, c):
        c = tuple(float(v) + 0.0 for v in c)
        if c not in self._dirs:
            self._dirs[c] = self.f.create_entity("IfcDirection", DirectionRatios=c)
        return self._dirs[c]

    def ax3(self, loc, z=(0.0, 0.0, 1.0), x=(1.0, 0.0, 0.0)):
        return self.f.create_entity("IfcAxis2Placement3D", Location=self.pt(loc), Axis=self.d(z), RefDirection=self.d(x))

    def ax2(self):
        return self.f.create_entity("IfcAxis2Placement2D", Location=self.pt((0.0, 0.0)), RefDirection=self.d((1.0, 0.0)))

    def local(self, rel, loc, z=(0.0, 0.0, 1.0), x=(1.0, 0.0, 0.0)):
        return self.f.create_entity("IfcLocalPlacement", PlacementRelTo=rel, RelativePlacement=self.ax3(loc, z, x))

    # --- geometry -----------------------------------------------------------
    def rect(self, xdim, ydim, name=None):
        return self.f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", ProfileName=name,
                                    Position=self.ax2(), XDim=float(xdim), YDim=float(ydim))

    def circle(self, r, name=None):
        return self.f.create_entity("IfcCircleProfileDef", ProfileType="AREA", ProfileName=name,
                                    Position=self.ax2(), Radius=float(r))

    def extrusion(self, profile, depth, z0=0.0):
        return self.f.create_entity("IfcExtrudedAreaSolid", SweptArea=profile, Position=self.ax3((0.0, 0.0, z0)),
                                    ExtrudedDirection=self.d((0.0, 0.0, 1.0)), Depth=float(depth))

    def shape(self, items_body, axis_pts=None, rep_type="SweptSolid"):
        reps = [self.f.create_entity("IfcShapeRepresentation", ContextOfItems=self.body_ctx,
                                     RepresentationIdentifier="Body", RepresentationType=rep_type,
                                     Items=items_body)]
        if axis_pts:
            pl = self.f.create_entity("IfcPolyline", Points=[self.pt(p) for p in axis_pts])
            reps.insert(0, self.f.create_entity("IfcShapeRepresentation", ContextOfItems=self.axis_ctx,
                                                RepresentationIdentifier="Axis", RepresentationType="Curve3D",
                                                Items=[pl]))
        return self.f.create_entity("IfcProductDefinitionShape", Representations=reps)

    # --- properties ---------------------------------------------------------
    def value(self, v):
        if isinstance(v, tuple):
            return self.f.create_entity(v[0], v[1])
        if isinstance(v, bool):
            return self.f.create_entity("IfcBoolean", v)
        if isinstance(v, int):
            return self.f.create_entity("IfcInteger", v)
        if isinstance(v, float):
            return self.f.create_entity("IfcReal", v)
        s = str(v)
        return self.f.create_entity("IfcText" if len(s) > 255 else "IfcLabel", s)

    def pset(self, el, name, props):
        vals = [self.f.create_entity("IfcPropertySingleValue", Name=k, NominalValue=self.value(v))
                for k, v in props.items() if v is not None]
        ps = self.f.create_entity("IfcPropertySet", GlobalId=self.guid("pset/%s/%s" % (el.GlobalId, name)),
                                  Name=name, HasProperties=vals)
        self.f.create_entity("IfcRelDefinesByProperties", GlobalId=self.guid("rdp/%s/%s" % (el.GlobalId, name)),
                             RelatedObjects=[el], RelatingPropertyDefinition=ps)
        return ps

    def element(self, cls, key, name, placement, shape, **attrs):
        el = self.f.create_entity(cls, GlobalId=self.guid("el/" + key), Name=name, ObjectPlacement=placement,
                                  Representation=shape, **attrs)
        self.contained.append(el)
        return el


def L(v):
    return ("IfcLengthMeasure", float(v))


def unit2(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return (round(dx / n, 12) + 0.0, round(dy / n, 12) + 0.0)


def build():
    m = Model()
    f = m.f

    # --- project, units, contexts --------------------------------------------
    units = f.create_entity("IfcUnitAssignment", Units=[
        f.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE"),
        f.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE"),
        f.create_entity("IfcSIUnit", UnitType="VOLUMEUNIT", Name="CUBIC_METRE"),
        f.create_entity("IfcSIUnit", UnitType="PLANEANGLEUNIT", Name="RADIAN"),
        f.create_entity("IfcSIUnit", UnitType="MASSUNIT", Prefix="KILO", Name="GRAM"),
        f.create_entity("IfcSIUnit", UnitType="POWERUNIT", Name="WATT"),
    ])
    ctx = f.create_entity("IfcGeometricRepresentationContext", ContextIdentifier=None, ContextType="Model",
                          CoordinateSpaceDimension=3, Precision=1.0e-5,
                          WorldCoordinateSystem=m.ax3((0.0, 0.0, 0.0)), TrueNorth=m.d((0.0, 1.0)))
    m.body_ctx = f.create_entity("IfcGeometricRepresentationSubContext", ContextIdentifier="Body",
                                 ContextType="Model", ParentContext=ctx, TargetView="MODEL_VIEW")
    m.axis_ctx = f.create_entity("IfcGeometricRepresentationSubContext", ContextIdentifier="Axis",
                                 ContextType="Model", ParentContext=ctx, TargetView="GRAPH_VIEW")
    project = f.create_entity("IfcProject", GlobalId=m.guid("project"), Name="MDC-2026-014",
                              Description="MERIDIAN DATA CENTER PHASE 1 - DATA HALL 1 - COORDINATED MEP MODEL",
                              LongName="MERIDIAN DATA CENTER - DATA HALL 1", Phase="ISSUED FOR CONSTRUCTION",
                              RepresentationContexts=[ctx], UnitsInContext=units)

    site_pl = m.local(None, (0.0, 0.0, 0.0))
    bldg_pl = m.local(site_pl, (0.0, 0.0, 0.0))
    storey_pl = m.local(bldg_pl, (0.0, 0.0, 0.0))
    site = f.create_entity("IfcSite", GlobalId=m.guid("site"), Name="MERIDIAN DATA CENTER",
                           ObjectPlacement=site_pl, CompositionType="ELEMENT")
    building = f.create_entity("IfcBuilding", GlobalId=m.guid("building"), Name="PHASE 1",
                               ObjectPlacement=bldg_pl, CompositionType="ELEMENT")
    storey = f.create_entity("IfcBuildingStorey", GlobalId=m.guid("storey"), Name="DATA HALL 1",
                             Description="Datum: finished floor (top of access-floor panel) = 0",
                             ObjectPlacement=storey_pl, CompositionType="ELEMENT", Elevation=0.0)
    space = f.create_entity("IfcSpace", GlobalId=m.guid("space"), Name="DATA HALL 1", LongName="DATA HALL 1",
                            ObjectPlacement=m.local(storey_pl, (0.0, 0.0, 0.0)), CompositionType="ELEMENT",
                            PredefinedType="SPACE")
    for key, parent, kids in (("agg/project", project, [site]), ("agg/site", site, [building]),
                              ("agg/building", building, [storey]), ("agg/storey", storey, [space])):
        f.create_entity("IfcRelAggregates", GlobalId=m.guid(key), RelatingObject=parent, RelatedObjects=kids)
    m.pset(space, "Pset_DCM_Hall", {"Length": L(HALL_X), "Width": L(HALL_Y), "FinishedFloorElevation": L(FFL),
                                    "SoffitElevation": L(SOFFIT), "StructuralSlabTop": L(SLAB_TOP),
                                    "MinimumClearHeight": L(CLEAR_MIN), "SprinklerStandoff": L(STANDOFF),
                                    "OverheadPathwayZone": "%.0f..%.0f" % (CLEAR_MIN, DEFLECTOR_CEIL - STANDOFF),
                                    "UnderFloorPathwayZone": "%.0f..%.0f" % (SLAB_TOP, -PANEL_T - UF_PANEL_CLEAR),
                                    "TileGrid": L(TILE), "GridOrigin": "SOUTH-WEST INTERNAL CORNER",
                                    "ServiceEntry": "x=%.0f y=%.0f (west wall)" % ENTRY})

    def oriented(x0, x1, y0, y1, z0, face):
        """Placement at the footprint centre, rotated about it so local +Y = front."""
        a = math.radians(FACING_ROT[face])
        xd = (round(math.cos(a), 12) + 0.0, round(math.sin(a), 12) + 0.0, 0.0)
        return m.local(storey_pl, ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z0), (0.0, 0.0, 1.0), xd)

    def box(w, d, h, z0=0.0):
        return m.shape([m.extrusion(m.rect(w, d), h, z0)])

    # --- access floor ----------------------------------------------------------
    floor = m.element("IfcSlab", "accessfloor", "ACCESS FLOOR", m.local(storey_pl, (HALL_X / 2, HALL_Y / 2, -PANEL_T)),
                      box(HALL_X, HALL_Y, PANEL_T), PredefinedType="FLOOR", ObjectType="AccessFloor",
                      Description="35 mm access-floor panel, top at FFL 0, following the room outline")
    m.pset(floor, "Pset_DCM_AccessFloor", {"PanelThickness": L(PANEL_T), "TopElevation": L(FFL),
                                            "BottomElevation": L(-PANEL_T), "TileSize": L(TILE),
                                            "PlenumDepthBelowPanel": L(-PANEL_T - SLAB_TOP),
                                            "StructuralSlabTop": L(SLAB_TOP), "Length": L(HALL_X), "Width": L(HALL_Y)})

    # --- structural columns -------------------------------------------------------
    for c in COLUMNS:
        el = m.element("IfcColumn", c["tag"], c["tag"], m.local(storey_pl, (c["x"], c["y"], FFL)),
                       box(COL_SIZE, COL_SIZE, SOFFIT - FFL), PredefinedType="COLUMN", ObjectType="Column",
                       Description="Structural column grid %s/%s, FFL to soffit" % (c["gx"], c["gy"]))
        m.pset(el, "Pset_DCM_Column", {"Tag": c["tag"], "GridX": c["gx"], "GridY": c["gy"],
                                       "Width": L(COL_SIZE), "Depth": L(COL_SIZE),
                                       "BaseElevation": L(FFL), "TopElevation": L(SOFFIT),
                                       "CentreX": L(c["x"]), "CentreY": L(c["y"])})

    # --- racks -------------------------------------------------------------------
    for r in RACKS:
        w = r["x1"] - r["x0"]
        el = m.element("IfcFurniture", r["tag"], r["tag"], oriented(r["x0"], r["x1"], r["y0"], r["y1"], FFL, r["face"]),
                       box(w, CAB_D, CAB_H), PredefinedType="USERDEFINED", ObjectType="Rack",
                       Description=CAB_DESC[r["type"]])
        m.pset(el, "Pset_DCM_Rack", {
            "Tag": r["tag"], "Row": r["row"], "PositionInRow": r["index"], "CabinetType": r["type"],
            "Width": L(w), "Depth": L(CAB_D), "Height": L(CAB_H), "RackUnits": 42,
            "FrontFaces": r["face"], "Facing": r["face"], "FacingRotationDeg": FACING_ROT[r["face"]],
            "Tile": tile_address(r["x0"], r["y0"]), "RowCentrelineY": L(ROWINFO[r["row"]]["y"]),
            "FootprintMinX": L(r["x0"]), "FootprintMaxX": L(r["x1"]),
            "FootprintMinY": L(r["y0"]), "FootprintMaxY": L(r["y1"]),
            "DesignLoadKW": 8.0, "LoadKg": 1363.0})

    # --- CRAH units -----------------------------------------------------------------
    for c in PCRAHS + INROW_CRAHS:
        el = m.element("IfcUnitaryEquipment", c["tag"], c["tag"],
                       oriented(c["x0"], c["x1"], c["y0"], c["y1"], FFL, c["face"]),
                       box(c["w"], c["d"], c["h"]), PredefinedType="AIRHANDLER", ObjectType="CRAH",
                       Description="CRAH, %s, %s" % (c["placement"], c["service"]))
        m.pset(el, "Pset_DCM_CRAH", {
            "Tag": c["tag"], "Placement": c["placement"], "Row": c["row"],
            "Width": L(c["w"]), "Depth": L(c["d"]), "Height": L(c["h"]),
            "CapacityKW": c["kw"], "AirflowM3h": c["airflow"], "FrontFaces": c["face"], "Facing": c["face"],
            "FacingRotationDeg": FACING_ROT[c["face"]], "Service": c["service"],
            "Tile": tile_address(c["x0"], c["y0"]),
            "FootprintMinX": L(c["x0"]), "FootprintMaxX": L(c["x1"]),
            "FootprintMinY": L(c["y0"]), "FootprintMaxY": L(c["y1"])})

    # --- PDUs -------------------------------------------------------------------------
    for p in PDU_LIST:
        el = m.element("IfcElectricDistributionBoard", p["tag"], p["tag"],
                       oriented(p["x0"], p["x1"], p["y0"], p["y1"], FFL, p["face"]),
                       box(PDU_W, PDU_D, PDU_H), PredefinedType="DISTRIBUTIONBOARD", ObjectType="PDU",
                       Description="POWER DISTRIBUTION UNIT 225 kVA, SERVES ROW %s" % p["row"])
        m.pset(el, "Pset_DCM_PDU", {
            "Tag": p["tag"], "ServesRow": p["row"], "Tile": p["tile"], "Width": L(PDU_W), "Depth": L(PDU_D),
            "Height": L(PDU_H), "RatingKVA": 225.0, "FrontFaces": p["face"], "Facing": p["face"],
            "FacingRotationDeg": FACING_ROT[p["face"]], "WorkingSpaceFront": L(PDU_WORKING),
            "DedicatedSpaceAbove": L(PDU_DEDICATED), "DedicatedSpaceTop": L(PDU_H + PDU_DEDICATED),
            "FootprintMinX": L(p["x0"]), "FootprintMaxX": L(p["x1"]),
            "FootprintMinY": L(p["y0"]), "FootprintMaxY": L(p["y1"])})

    # --- containment (roof panels + end doors) ------------------------------------------
    for r in ROOFS:
        el = m.element("IfcBuildingElementProxy", r["tag"], r["tag"],
                       m.local(storey_pl, ((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2, ROOF_UNDERSIDE)),
                       box(r["x1"] - r["x0"], r["y1"] - r["y0"], ROOF_T), PredefinedType="USERDEFINED",
                       ObjectType="ContainmentRoof", Description="Cold-aisle containment roof panel, %s" % r["contains"])
        m.pset(el, "Pset_DCM_Containment", {
            "Tag": r["cac"], "Contains": r["contains"], "Part": "ROOF PANEL", "PanelIndex": r["panel"],
            "RoofWidth": L(ROOF_W), "RoofThickness": L(ROOF_T), "RoofUnderside": L(ROOF_UNDERSIDE),
            "RoofTop": L(ROOF_UNDERSIDE + ROOF_T), "Length": L(r["x1"] - r["x0"]),
            "StartX": L(r["x0"]), "EndX": L(r["x1"]), "HeadsBeneath": AISLE_HEADS_PER_PANEL})
    for dr in DOORS:
        el = m.element("IfcBuildingElementProxy", dr["tag"], dr["tag"],
                       m.local(storey_pl, ((dr["x0"] + dr["x1"]) / 2, (dr["y0"] + dr["y1"]) / 2, FFL)),
                       box(DOOR_T, dr["y1"] - dr["y0"], DOOR_H), PredefinedType="USERDEFINED",
                       ObjectType="ContainmentDoor",
                       Description="Cold-aisle containment end door (kit), %s" % dr["contains"])
        m.pset(el, "Pset_DCM_Containment", {
            "Tag": dr["cac"], "Contains": dr["contains"], "Part": "END DOOR", "DoorThickness": L(DOOR_T),
            "DoorHeight": L(DOOR_H), "DoorWidth": L(dr["y1"] - dr["y0"]), "X": L((dr["x0"] + dr["x1"]) / 2)})

    # --- sprinkler heads ---------------------------------------------------------------
    for h in HEADS:
        el = m.element("IfcFireSuppressionTerminal", h["tag"], h["tag"], m.local(storey_pl, (h["x"], h["y"], h["zd"])),
                       m.shape([m.extrusion(m.circle(HEAD_R), h["ztop"] - h["zd"])]),
                       PredefinedType="SPRINKLER", ObjectType="SprinklerHead",
                       Description="Pendent sprinkler head, %s, deflector +%.1f" % (h["kind"], h["zd"]))
        props = {"Tag": h["tag"], "HeadType": h["kind"], "DeflectorElevation": L(h["zd"]),
                 "MountingElevation": L(h["ztop"]), "KeepClearBelow": L(STANDOFF),
                 "KeepClearBottom": L(h["zd"] - STANDOFF), "Relocated": bool(h["relocated"])}
        if h["grid"]:
            props["GridX"], props["GridY"] = L(h["grid"][0]), L(h["grid"][1])
        m.pset(el, "Pset_DCM_Sprinkler", props)

    # --- services ------------------------------------------------------------------------
    # Joints: each segment is extruded exactly from junction centre to junction centre
    # (so centrelines and end points coincide) and, at every junction, clipped by a
    # vertical 45-degree half-space against each perpendicular arm meeting there.
    # Neighbouring segments of a run therefore share a mitre face and never overlap.
    building_systems = []
    route_records = []
    for s in SERVICES:
        arms = {}
        for i, (_, a, b, _) in enumerate(s["segs"]):
            dv = unit2(a, b)
            arms.setdefault(a, []).append((i, dv))
            arms.setdefault(b, []).append((i, (-dv[0] + 0.0, -dv[1] + 0.0)))
        system = f.create_entity("IfcDistributionSystem", GlobalId=m.guid("sys/" + s["key"]), Name=s["system"],
                                 Description=s["desc"], ObjectType=s["service"], PredefinedType=s["sys_enum"])
        building_systems.append(system)
        z = s["z"]
        if s["shape"][0] == "rect":
            prof = m.rect(s["shape"][1], s["shape"][2], name=s["key"])
            half_h, half_w = s["shape"][2] / 2.0, s["shape"][1] / 2.0
        else:
            prof = m.circle(s["shape"][1], name=s["key"])
            half_h = half_w = s["shape"][1]
        members = []
        for i, (role, a, b, rows) in enumerate(s["segs"]):
            p0, p1 = (a[0], a[1], z), (b[0], b[1], z)
            vec = tuple(q - p for p, q in zip(p0, p1))
            length = math.sqrt(sum(v * v for v in vec))
            dirn = tuple(round(v / length, 12) + 0.0 for v in vec)
            assert sorted(abs(v) for v in dirn) == [0.0, 0.0, 1.0], "segments must be axis aligned"
            xdir = (-dirn[1] + 0.0, dirn[0] + 0.0, 0.0)          # keeps local +Y up (section height)
            ydir = (0.0, 0.0, 1.0)
            name = "%s-S%02d" % (s["key"], i + 1)
            solid = f.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, Position=m.ax3((0.0, 0.0, 0.0)),
                                    ExtrudedDirection=m.d((0.0, 0.0, 1.0)), Depth=length)
            nclip = 0
            for jp, away in ((a, (dirn[0], dirn[1])), (b, (-dirn[0] + 0.0, -dirn[1] + 0.0))):
                for j, e in arms[jp]:
                    if j == i or abs(e[0] * away[0] + e[1] * away[1]) > 1e-9:
                        continue
                    # remove {(p - J).(e - away) > 0}: the wedge that belongs to arm j
                    nw = ((e[0] - away[0]) / math.sqrt(2.0), (e[1] - away[1]) / math.sqrt(2.0), 0.0)
                    rel = (jp[0] - p0[0], jp[1] - p0[1], 0.0)
                    loc = tuple(sum(r * c for r, c in zip(rel, axis)) for axis in (xdir, ydir, dirn))
                    nl = tuple(round(sum(r * c for r, c in zip(nw, axis)), 12) + 0.0 for axis in (xdir, ydir, dirn))
                    plane = f.create_entity("IfcPlane", Position=f.create_entity(
                        "IfcAxis2Placement3D", Location=m.pt(loc), Axis=m.d(nl), RefDirection=m.d((0.0, 1.0, 0.0))))
                    solid = f.create_entity("IfcBooleanClippingResult", Operator="DIFFERENCE", FirstOperand=solid,
                                            SecondOperand=f.create_entity("IfcHalfSpaceSolid", BaseSurface=plane,
                                                                          AgreementFlag=False))
                    nclip += 1
            el = m.element(s["ifc"], name, name, m.local(storey_pl, p0, dirn, xdir),
                           m.shape([solid], axis_pts=[(0.0, 0.0, 0.0), (0.0, 0.0, length)],
                                   rep_type="Clipping" if nclip else "SweptSolid"),
                           PredefinedType=s["ptype"], ObjectType=s["otype"],
                           Description="%s %s - %s" % (s["key"], s["service"], role))
            members.append(el)
            axis = "XYZ"[[abs(v) for v in dirn].index(1.0)]
            sign = "+" if sum(dirn) > 0 else "-"
            props = {
                "Service": s["service"], "ServiceTag": s["key"], "System": s["system"], "SegmentIndex": i + 1,
                "SegmentRole": role, "ServesRows": rows or "-",
                "Zone": "UNDER-FLOOR PLENUM", "Tier": {"CT-1": "UF-T1 (top)", "CHW-1": "UF-T2 (middle)",
                                                     "BW-1": "UF-T3 (bottom)"}[s["key"]],
                "StartX": L(p0[0]), "StartY": L(p0[1]), "StartZ": L(p0[2]),
                "EndX": L(p1[0]), "EndY": L(p1[1]), "EndZ": L(p1[2]),
                "Length": L(length), "Direction": sign + axis,
                "Elevation": L(z), "CentrelineElevation": L(z),
                "ElevationReference": "FFL 0 (top of access-floor panel)",
                "HeightBand": "BELOW FINISHED FLOOR" if z + half_h <= FFL else (
                    "CLEAR-HEIGHT BAND" if z - half_h < CLEAR_MIN else "OVERHEAD PLENUM"),
                "TopElevation": L(z + half_h), "BottomElevation": L(z - half_h),
            }
            if s["shape"][0] == "rect":
                props.update({"SectionWidth": L(s["shape"][1]), "SectionHeight": L(s["shape"][2])})
            else:
                props.update({"OuterDiameter": L(PIPE_OD), "NominalDiameter": "DN100",
                              "InsulationThickness": L(PIPE_INS), "InsulatedOuterDiameter": L(PIPE_OD + 2 * PIPE_INS),
                              "JacketOuterDiameter": L(PIPE_JACKET_OD),
                              "InsulatedTopElevation": L(z + PIPE_JACKET_OD / 2),
                              "InsulatedBottomElevation": L(z - PIPE_JACKET_OD / 2)})
            m.pset(el, "Pset_DCM_Route", props)
            m.pset(el, "Pset_DCM_Service", {"Service": s["service"], "ServiceTag": s["key"], "System": s["system"],
                                            "EntryX": L(ENTRY[0]), "EntryY": L(ENTRY[1])})
            route_records.append((s["key"], name, p0, p1, length))
        f.create_entity("IfcRelAssignsToGroup", GlobalId=m.guid("grp/" + s["key"]), RelatedObjects=members,
                        RelatingGroup=system)
    f.create_entity("IfcRelServicesBuildings", GlobalId=m.guid("svc/buildings"), RelatingSystem=building_systems[0],
                    RelatedBuildings=[building])
    for k, sysm in enumerate(building_systems[1:]):
        f.create_entity("IfcRelServicesBuildings", GlobalId=m.guid("svc/buildings/%d" % k), RelatingSystem=sysm,
                        RelatedBuildings=[building])

    f.create_entity("IfcRelContainedInSpatialStructure", GlobalId=m.guid("contained/storey"),
                    RelatingStructure=storey, RelatedElements=m.contained)
    return m, route_records


# =============================================================================
# 5. DRAWING-NOTE RECONCILIATION LOG (optional side file)
# =============================================================================
def reconciliation(route_records):
    tot = {}
    for key, _, _, _, length in route_records:
        tot[key] = tot.get(key, 0.0) + length
    notes = [
        ("A-301 sec.1 / A-602 data", "Finished floor +/-0 = top of access-floor panel", 0.0, "Storey elevation 0; all z relative to FFL"),
        ("A-602 data", "Top of structural slab -900", -900.0, "Under-floor zone bottom; busway bottom kept at -880"),
        ("A-602 data / A-301 n.6", "Access floor panel 35 thk, 600 tile, follows room outline", 35.0, "IfcSlab 27000 x 21000, z -35..0"),
        ("A-602 data / A-301 n.4", "Ceiling slab soffit +3600 = column height", 3600.0, "Columns 600 sq. modelled FFL 0 to +3600"),
        ("A-602 data / A-301", "Minimum clear height 2600, nothing below", 2600.0, "No service between FFL and +2600 (all in plenum)"),
        ("A-602 data / F-101 n.5", "Sprinkler standoff 460 clear below every deflector", 460.0, "No service above +3114.6 (none overhead)"),
        ("A-301 / A-602 det.4", "Deflector 25.4 below soffit (+3575)", 3574.6, "Ceiling head deflector at +3574.6"),
        ("A-301 det.3 / F-101 n.8", "In-aisle head deflector +1890, 110 below roof", 1890.0, "16 in-aisle heads hang 1890..2000 under the roofs"),
        ("A-301 n.3 / A-602 det.2", "Under-floor tray top >= 20 below panel underside", 20.0, "Tray top at -60 (25 below -35)"),
        ("A-602 det.4", "Under-floor pathway zone 845 (-900..-55)", 845.0, "Tray -187..-60, CHW centre -460, busway -880..-733"),
        ("A-602 det.4", "Overhead pathway zone 515 (+2600..+3115)", 515.0, "Too shallow for tray+300+busway (574); not used"),
        ("A-602 CAC", "Roof width 1400 = aisle 1200 + 100 overhang each side", 1400.0, "Roofs y 6500..7900 and 11900..13300"),
        ("A-602 CAC", "Roof thickness 55.5, underside +2000", 55.5, "Roof panels z 2000..2055.5, split at the cross aisle"),
        ("A-602 CAC", "End door 60 x 2055.5, 4 per aisle", 60.0, "Doors outside each roof end: x 1740, 10200, 11340, 19800"),
        ("A-602 pathway", "CT-1 cable tray 683 x 127", 683.0, "Tray section 683 W x 127 H"),
        ("A-602 pathway / E-101 n.4", "BW-1 busway 128 x 147, support at 1500 max", 128.0, "Busway section 128 W x 147 H (supports not modelled)"),
        ("A-602 pathway / M-101 n.4", "CHW-1 DN100 OD 114.3, insulation 25 min, jacket OD 168.3", 114.3, "Pipe OD 114.3; clearances checked with 168.3/219.1 envelopes"),
        ("E-101 n.6", "300 clear between tray and busway on at least one axis", 300.0, "Vertical clear 546 (tray bottom -187, busway top -733)"),
        ("E-101 n.7 / M-101 n.5", "1800 dedicated space above each PDU, no piping", 1800.0, "CHW never inside a PDU footprint (it runs below FFL)"),
        ("E-101 n.8", "900 working space at every PDU front", 900.0, "Kept clear (services below the floor)"),
        ("A-601 PDU", "PDU 762 x 813 x 1959, 225 kVA", 762.0, "PDU boxes, front flush with row front (A-101 n.8)"),
        ("A-101 dim 4238 / E-101", "PDU west face 1800 east of its row's east end", 1800.0, "PDU-01..06 at x 21000/21600/21200/21600/21000/22000"),
        ("A-601 CRAH", "Perimeter CRAH 1200 x 900 x 2000 at B01 P01 AC01 AQ01, face N", 1200.0, "x 600, 9000, 16800, 25200; y 0..900"),
        ("A-601 CRAH", "In-row CRAH 600 x 1200 x 2000, one full bay (CU)", 600.0, "18 units at the CU bays of the bay sequences"),
        ("A-601 cabinet", "Cabinet depth 1200, height 2000, 42U; C1 600 / N1 800 wide", 1200.0, "128 racks from the bay sequences"),
        ("A-101 n.5", "Cross aisle: common east edge, 1200 clear, caps runs at 16 m", 11400.0, "CA term jumps to x = 11400"),
        ("A-101 left dims", "Row centrelines 3000/6000/8400/11400/13800/16800", 3000.0, "Rows A..F footprint = centreline +/- 600"),
        ("A-101 struct. grid", "Column grid 8400 x 8400 (A/B/C, 1/2)", 8400.0, "Columns at x 8400/16800/25200, y 8400/16800"),
        ("F-101", "Ceiling heads 1500 from walls, 3000 typ., 63 heads", 3000.0, "9 x 7 grid; B/2 and C/2 heads relocated 60 clear of column"),
        ("F-101 n.6", "20.9 m2 per head, 4600 max spacing", 4600.0, "Grid spacing 3000 <= 4600 (as drawn)"),
        ("F-101 n.8 / A-602 n.4", "Heads beneath containment roof (> 1200 wide)", 1200.0, "4 heads per roof panel, 500 from ends, equal spacing"),
        ("M-101 / E-101", "Service entries at west wall, 9900 from south wall", 9900.0, "All three services start at (0, 9900)"),
        ("Task / connectivity", "Rows served within 2500 across the row", 2500.0, "Headers on hot-aisle centres y 4500/9900/15300 (1500 from each row); tray A/B and E/F headers at y 5000/14800 (<= 2000)"),
        ("Task / connectivity", "Rows served along >= 80 % of length", 0.8, "Headers run x 1800..17200 (A/B, C/D) and ..17000 (E/F)"),
        ("Task / connectivity", "CHW within 2500 of every CRAH", 2500.0, "Branches end <= 1835 in plan (<= 2350 in 3D) from each perimeter CRAH centre"),
    ]
    return {
        "model": "dc_model hall_seed000_d000 - DATA HALL 1",
        "units": "mm, elevations relative to FFL",
        "notes": [dict(sheet=a, note=b, value=c, applied=d) for a, b, c, d in notes],
        "route_lengths_mm": {k: round(v, 1) for k, v in tot.items()},
        "route_total_mm": round(sum(tot.values()), 1),
    }


def main():
    m, recs = build()
    out_dir = os.path.dirname(os.path.abspath(OUT_PATH))
    os.makedirs(out_dir, exist_ok=True)
    try:
        with open(os.path.join(out_dir, "reconciliation.json"), "w") as fh:
            json.dump(reconciliation(recs), fh, indent=2)
    except OSError:
        pass
    m.f.write(OUT_PATH)


if __name__ == "__main__":
    main()
