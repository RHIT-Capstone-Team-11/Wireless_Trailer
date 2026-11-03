#!/usr/bin/env python3
"""
OTM (on-trailer module) housing, v6 - CadQuery build script.

Rebuilt 2026-10-19 from the v6 STEP files after the original script was lost.
Running it reproduces v6 exactly: every solid and all 29 assembly parts were checked
against the original v6 STEP files (zero boolean difference volume, identical volumes,
areas, face counts, names and colors). Verified with CadQuery 2.8.0 / OCP 7.9.3.

Outputs (written to the output folder, default ./out):
    housing_v6_body.step
    housing_v6_lid_wiring_bay.step          (lid in its own frame: z=0 is the lid underside)
    housing_v6_lid_electronics_bay.step     (same)
    housing_v6_assembly_with_parts.step     (body + both lids seated + stand-in parts)
    housing_v6_preview.png, housing_v6_plan_section.png,
    housing_v6_side_section.png, housing_v6_corner_zoom.png

Usage:
    pip install cadquery matplotlib numpy
    python otm_housing_v6.py [output_folder] [--no-png]

Units are mm. Origin: centre of the footprint, z = 0 on the underside of the body.
+y is the wiring bay (client side), -y is the electronics bay (service side).

Design summary
    * Two-bay body: a Z-shaped 3 mm partition splits the cavity into a wiring bay
      (client-openable) and an electronics bay (service only).
    * 8 mm deck on top with one opening per bay and M3 heat-set insert holes.
    * Outer wall flares out at 45 deg into a wide rim (the "flange gusset"); the flare is
      cut back under the rim where the PG21 trunk glands need nut clearance.
    * Each lid: 5 mm plate, perimeter skirt over the rim, face-seal O-ring groove in the
      underside, and a plug that drops into the opening with a radial O-ring groove
      (double seal), plus counterbored M3 screw holes.
"""

import math
import os
import sys

import cadquery as cq

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

# Every outer outline is an offset of this core rectangle (half-sizes), with its
# corner arcs centred on the core corners (+-CORE_HX, +-CORE_HY).
CORE_HX, CORE_HY = 67.0, 68.5

WALL_OFF = 6.0                 # lower outer wall offset  -> 146 x 149, R6 corners
FLARE_Z0 = 33.1                # 45-degree flare starts here
DECK_Z0 = 46.5                 # flare ends / deck underside / rim bottom
TOP_Z = 54.5                   # top of deck (lid seating face)
RIM_OFF = WALL_OFF + (DECK_Z0 - FLARE_Z0)   # 19.4 -> rim 172.8 x 175.8

FLOOR_Z = 4.5                  # cavity floor (4.5 mm base)
CAV_HX, CAV_HY = 70.0, 71.5    # cavity walls (3 mm wall)
CAV_R = 2.0                    # cavity corner radius (plan view)

# Partition (divider) centreline: y = SPLIT_Y_LO for x < SPLIT_X, the jog at x = SPLIT_X,
# then y = SPLIT_Y_HI for x > SPLIT_X.  Wiring bay is "above" the line.
SPLIT_X, SPLIT_Y_LO, SPLIT_Y_HI = -11.5, 0.0, 30.0
DIV_T = 3.0                    # partition thickness

OPEN_LAND = 14.0               # deck land each side of the partition centreline
OPEN_R = 8.0                   # deck opening corner radius

# Gland clearance: flare removed under the rim on both sides for y in [31, 73]
GLAND_CLEAR_Y = (31.0, 73.0)

# Lids
LID_GAP = 0.5                  # each lid stops 0.5 mm short of the split centreline (1 mm gap)
LID_T = 5.0                    # plate thickness
LID_OUT_OFF = 22.4             # plate / skirt outer offset (rim + 3.0)
SKIRT_IN_OFF = 19.9            # skirt inner offset (0.5 clearance to the rim)
SKIRT_DEPTH = 10.0
PLUG_CLEAR = 0.3               # plug is the deck opening inset by 0.3
PLUG_DEPTH = 7.0
RADIAL_GROOVE_BOTTOM = 2.0     # radial O-ring groove bottom: opening inset by 2.0
RADIAL_GROOVE_Z = (-5.2, -1.8)
FACE_GROOVE_W = 3.4            # face-seal O-ring groove in lid underside
FACE_GROOVE_D = 2.0
FACE_GROOVE_SPLIT_INSET = 4.2  # groove centreline distance from split centreline
FACE_GROOVE_OUT_OFF = 7.7      # groove centreline offset from core rect on the outer sides
FACE_GROOVE_R_CONVEX = 8.0     # centreline corner radii
FACE_GROOVE_R_REFLEX = 4.5

# M3 screws: heat-set insert holes in the deck, counterbored clearance holes in the lids
INSERT_R, INSERT_DEPTH = 2.0, 5.0
SCREW_CLEAR_R = 1.7
SCREW_CBORE_R, SCREW_CBORE_Z = 3.3, 2.8      # counterbore from lid top down to z = 2.8

SCREWS_WIRING = [
    (-81.4, 12.0), (-40.0, 9.4), (-20.9, 26.0), (-81.4, 45.4), (-19.5, 38.0),
    (13.2, 39.4), (47.3, 39.4), (81.4, 42.0),
    (-77.2, 78.7), (-38.6, 82.9), (0.0, 82.9), (38.6, 82.9), (77.2, 78.7),
]
SCREWS_ELECTRONICS = [
    (-81.4, -12.0), (-40.0, -9.4), (-4.0, -7.5), (-81.4, -45.4), (16.0, 20.6),
    (50.0, 20.6), (81.4, 18.0), (81.4, -14.3), (81.4, -46.5),
    (-77.2, -78.7), (-38.6, -82.9), (0.0, -82.9), (38.6, -82.9), (77.2, -78.7),
]

# Glands (holes in the side walls; centres given as (y, z))
PG21_HOLE_R, PG21_YZ = 14.5, (52.0, 25.0)    # trunk, both sides
PG9_HOLE_R, PG9_YZ = 7.75, (16.5, 18.0)      # lamp pigtail, left side

# Electronics-bay features
PCB_STANDOFFS = [(x, y) for y in (-62.5, -10.5) for x in (-55.0, 0.0, 55.0)]
STANDOFF_R, STANDOFF_TOP, STANDOFF_HOLE_R, STANDOFF_HOLE_DEPTH = 3.5, 10.5, 2.0, 5.0
CELL_Y, CELL_Z, CRADLE_R = 7.0, 13.7, 9.2    # 18650 cradle axis along x
CRADLE_RIBS_X = [(11.0, 17.0), (43.0, 49.0)]
CRADLE_RIB_Y = (-4.5, 18.5)
ANTENNA_SHELF = dict(x=(-70.0, -56.0), y=(-68.5, -34.5), z=(38.0, 41.0))

# Partition pass-throughs (boss on the electronics side, hole through the partition)
PASS_LOW = dict(x=-36.0, z=24.0, boss_r=8.0, hole_r=5.0, boss_y=(-9.5, -1.5))    # y=0 run
PASS_HIGH = dict(x=14.0, z=24.0, boss_r=9.0, hole_r=6.0, boss_y=(20.5, 28.5))    # y=30 run

# Wiring-bay WAGO cradles: block on the floor with one pocket per lever nut
WAGO_OUT_BLOCK = dict(x=(-58.0, -14.0), y=(4.0, 28.0), z_top=12.5)
WAGO_OUT_POCKETS = dict(xc=[-50.0, -36.0, -22.0], yc=16.0, w=13.6, l=18.9, depth=5.0)
WAGO_IN_BLOCK = dict(x=(-46.0, 46.0), y=(33.0, 59.0), z_top=12.5)
WAGO_IN_POCKETS = dict(xc=[-33.75, -11.25, 11.25, 33.75], yc=46.0, w=19.4, l=19.2, depth=5.0)

# Base magnets (pockets open to the underside)
MAGNETS_XY = [(-50.0, 40.0), (50.0, 40.0), (-50.0, -45.0), (50.0, -45.0)]
MAGNET_POCKET_R, MAGNET_POCKET_DEPTH = 8.14, 2.87


# ---------------------------------------------------------------------------
# 2D helpers (all polygons are axis-aligned, counter-clockwise)
# ---------------------------------------------------------------------------

def _turn(pts, i):
    """Return (din, dout, left_turn) at vertex i."""
    n = len(pts)
    ax, ay = pts[i - 1]
    px, py = pts[i]
    bx, by = pts[(i + 1) % n]
    li = math.hypot(px - ax, py - ay)
    lo = math.hypot(bx - px, by - py)
    din = ((px - ax) / li, (py - ay) / li)
    dout = ((bx - px) / lo, (by - py) / lo)
    cross = din[0] * dout[1] - din[1] * dout[0]
    return din, dout, cross > 0


def rounded_poly(pts, radii, z=0.0):
    """Closed wire through axis-aligned polygon `pts` with a tangent fillet of radius
    radii[i] (or one radius for all) at every vertex, convex or reflex."""
    n = len(pts)
    if isinstance(radii, (int, float)):
        radii = [float(radii)] * n
    corners = []
    for i in range(n):
        din, dout, left = _turn(pts, i)
        r = radii[i]
        px, py = pts[i]
        p1 = (px - din[0] * r, py - din[1] * r)
        p2 = (px + dout[0] * r, py + dout[1] * r)
        c = (p1[0] + dout[0] * r, p1[1] + dout[1] * r)
        dx, dy = px - c[0], py - c[1]
        d = math.hypot(dx, dy) or 1.0
        mid = (c[0] + dx / d * r, c[1] + dy / d * r)
        corners.append((p1, mid, p2, r))
    wp = cq.Workplane("XY", origin=(0, 0, z)).moveTo(*corners[0][2])
    for i in range(1, n + 1):
        p1, mid, p2, r = corners[i % n]
        wp = wp.lineTo(*p1)
        if r > 0:
            wp = wp.threePointArc(mid, p2)
    return wp.close()


def offset_poly(pts, radii, d):
    """Offset an axis-aligned rounded polygon by d (positive = outward).
    Convex fillets grow by d, reflex fillets shrink by d (exactly what an arc offset does)."""
    n = len(pts)
    if isinstance(radii, (int, float)):
        radii = [float(radii)] * n
    new_pts, new_r = [], []
    for i in range(n):
        din, dout, left = _turn(pts, i)
        # outward normal of a CCW edge with direction (ex, ey) is (ey, -ex)
        n1 = (din[1], -din[0])
        n2 = (dout[1], -dout[0])
        px, py = pts[i]
        new_pts.append((px + d * (n1[0] + n2[0]), py + d * (n1[1] + n2[1])))
        new_r.append(radii[i] + d if left else radii[i] - d)
    return new_pts, new_r


def prism(pts, radii, z0, z1):
    return rounded_poly(pts, radii, z0).extrude(z1 - z0)


def core_rect(off):
    """Rounded rectangle = core rectangle offset by `off` (corner radius = off)."""
    hx, hy = CORE_HX + off, CORE_HY + off
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)], off


def split_region(side, inset, xlim, ylim):
    """Polygon of one side of the partition centreline, inset from it by `inset`,
    bounded by +-xlim / +-ylim on the outer sides.  side = 'wiring' or 'electronics'."""
    if side == "electronics":
        return [(-xlim, -ylim), (xlim, -ylim), (xlim, SPLIT_Y_HI - inset),
                (SPLIT_X + inset, SPLIT_Y_HI - inset), (SPLIT_X + inset, SPLIT_Y_LO - inset),
                (-xlim, SPLIT_Y_LO - inset)]
    return [(-xlim, SPLIT_Y_LO + inset), (SPLIT_X - inset, SPLIT_Y_LO + inset),
            (SPLIT_X - inset, SPLIT_Y_HI + inset), (xlim, SPLIT_Y_HI + inset),
            (xlim, ylim), (-xlim, ylim)]


def opening(side):
    return split_region(side, OPEN_LAND, CAV_HX, CAV_HY)


def box(x, y, z):
    return cq.Workplane("XY").box(x[1] - x[0], y[1] - y[0], z[1] - z[0], centered=False) \
        .translate((x[0], y[0], z[0]))


def cyl(r, p0, direction, length):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, length, cq.Vector(*p0), cq.Vector(*direction)))


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

def build_body():
    pts, r = core_rect(WALL_OFF)
    body = prism(pts, r, 0.0, FLARE_Z0)
    flare = rounded_poly(pts, r, FLARE_Z0).extrude(DECK_Z0 - FLARE_Z0, taper=-45)
    rpts, rr = core_rect(RIM_OFF)
    rim = prism(rpts, rr, DECK_Z0, TOP_Z)
    body = body.union(flare).union(rim)

    # Remove the flare under the rim where the PG21 gland nuts sit
    xw = CORE_HX + WALL_OFF
    for sx in (-1, 1):
        x = (xw, xw + 25.0) if sx > 0 else (-xw - 25.0, -xw)
        body = body.cut(box(x, GLAND_CLEAR_Y, (-1.0, DECK_Z0)))

    # Two bays (below the deck) and the deck openings
    for side in ("electronics", "wiring"):
        bay = split_region(side, DIV_T / 2, CAV_HX, CAV_HY)
        body = body.cut(prism(bay, CAV_R, FLOOR_Z, DECK_Z0))
        body = body.cut(prism(opening(side), OPEN_R, DECK_Z0 - 0.01, TOP_Z + 1.0))

    # ---- additions inside the bays ----
    for (x, y) in PCB_STANDOFFS:
        body = body.union(cyl(STANDOFF_R, (x, y, FLOOR_Z - 0.5), (0, 0, 1), STANDOFF_TOP - FLOOR_Z + 0.5))
    for (x0, x1) in CRADLE_RIBS_X:
        body = body.union(box((x0, x1), CRADLE_RIB_Y, (FLOOR_Z, CELL_Z)))
    s = ANTENNA_SHELF
    body = body.union(box((s["x"][0] - 1.5, s["x"][1]), s["y"], s["z"]))
    for p, ydir in ((PASS_LOW, +1), (PASS_HIGH, +1)):
        y0, y1 = p["boss_y"]
        body = body.union(cyl(p["boss_r"], (p["x"], y0, p["z"]), (0, 1, 0), (y1 - y0) + 1.5))
    for blk in (WAGO_OUT_BLOCK, WAGO_IN_BLOCK):
        body = body.union(box(blk["x"], blk["y"], (FLOOR_Z, blk["z_top"])))

    # ---- cuts ----
    for (x, y) in PCB_STANDOFFS:
        body = body.cut(cyl(STANDOFF_HOLE_R, (x, y, STANDOFF_TOP - STANDOFF_HOLE_DEPTH), (0, 0, 1), STANDOFF_HOLE_DEPTH + 1))
    for (x0, x1) in CRADLE_RIBS_X:
        body = body.cut(cyl(CRADLE_R, (x0 - 1.0, CELL_Y, CELL_Z), (1, 0, 0), (x1 - x0) + 2.0))
    for p in (PASS_LOW, PASS_HIGH):
        y0 = p["boss_y"][0]
        body = body.cut(cyl(p["hole_r"], (p["x"], y0 - 1.0, p["z"]), (0, 1, 0), (p["boss_y"][1] - y0) + DIV_T + 2.0))
    for blk, pk in ((WAGO_OUT_BLOCK, WAGO_OUT_POCKETS), (WAGO_IN_BLOCK, WAGO_IN_POCKETS)):
        for xc in pk["xc"]:
            body = body.cut(box((xc - pk["w"] / 2, xc + pk["w"] / 2),
                                (pk["yc"] - pk["l"] / 2, pk["yc"] + pk["l"] / 2),
                                (blk["z_top"] - pk["depth"], blk["z_top"] + 1.0)))
    # gland holes through the side walls
    xw_in = CAV_HX
    for sx in (-1, 1):
        y, z = PG21_YZ
        x0 = sx * (xw + 2.0)
        body = body.cut(cyl(PG21_HOLE_R, (x0, y, z), (-sx, 0, 0), (xw - xw_in) + 4.0))
    y, z = PG9_YZ
    body = body.cut(cyl(PG9_HOLE_R, (-(xw + 2.0), y, z), (1, 0, 0), (xw - xw_in) + 4.0))
    for (x, y) in MAGNETS_XY:
        body = body.cut(cyl(MAGNET_POCKET_R, (x, y, -1.0), (0, 0, 1), MAGNET_POCKET_DEPTH + 1.0))
    for (x, y) in SCREWS_WIRING + SCREWS_ELECTRONICS:
        body = body.cut(cyl(INSERT_R, (x, y, TOP_Z - INSERT_DEPTH), (0, 0, 1), INSERT_DEPTH + 1.0))
    return body


# ---------------------------------------------------------------------------
# Lids (built in their own frame: z = 0 is the plate underside that seats on the deck)
# ---------------------------------------------------------------------------

def face_groove_centreline(side):
    pts = split_region(side, FACE_GROOVE_SPLIT_INSET,
                       CORE_HX + FACE_GROOVE_OUT_OFF, CORE_HY + FACE_GROOVE_OUT_OFF)
    radii = []
    for i in range(len(pts)):
        _, _, left = _turn(pts, i)
        radii.append(FACE_GROOVE_R_CONVEX if left else FACE_GROOVE_R_REFLEX)
    return pts, radii


def build_lid(side):
    big = 150.0
    region = prism(split_region(side, LID_GAP, big, big), 0.0, -SKIRT_DEPTH - 1, LID_T + 1)

    opts, orr = core_rect(LID_OUT_OFF)
    ipts, irr = core_rect(SKIRT_IN_OFF)
    plate = prism(opts, orr, 0.0, LID_T).intersect(region)
    skirt = prism(opts, orr, -SKIRT_DEPTH, 0.0).cut(prism(ipts, irr, -SKIRT_DEPTH - 1, 1.0)).intersect(region)
    lid = plate.union(skirt)

    # plug that drops into the deck opening
    op = opening(side)
    ppts, prr = offset_poly(op, OPEN_R, -PLUG_CLEAR)
    lid = lid.union(prism(ppts, prr, -PLUG_DEPTH, 0.0))
    # radial O-ring groove around the plug
    gpts, grr = offset_poly(op, OPEN_R, -RADIAL_GROOVE_BOTTOM)
    wpts, wrr = offset_poly(op, OPEN_R, +1.0)
    z0, z1 = RADIAL_GROOVE_Z
    ring = prism(wpts, wrr, z0, z1).cut(prism(gpts, grr, z0 - 1, z1 + 1))
    lid = lid.cut(ring)

    # face-seal O-ring groove in the underside
    cpts, crr = face_groove_centreline(side)
    o_pts, o_r = offset_poly(cpts, crr, +FACE_GROOVE_W / 2)
    i_pts, i_r = offset_poly(cpts, crr, -FACE_GROOVE_W / 2)
    groove = prism(o_pts, o_r, -0.01, FACE_GROOVE_D).cut(prism(i_pts, i_r, -0.02, FACE_GROOVE_D + 0.02))
    lid = lid.cut(groove)

    # counterbored M3 clearance holes
    for (x, y) in (SCREWS_WIRING if side == "wiring" else SCREWS_ELECTRONICS):
        lid = lid.cut(cyl(SCREW_CBORE_R, (x, y, SCREW_CBORE_Z), (0, 0, 1), LID_T))
        lid = lid.cut(cyl(SCREW_CLEAR_R, (x, y, -0.5), (0, 0, 1), SCREW_CBORE_Z + 0.5))
    return lid


# ---------------------------------------------------------------------------
# Stand-in parts for the assembly (all placed in body coordinates)
# ---------------------------------------------------------------------------

def hex_x(circum_d, x0, x1, y, z):
    """Hex prism along x, flats facing +-y, vertices at +-z."""
    R = circum_d / 2
    pts = [(y + R * math.cos(math.radians(90 + 60 * k)), z + R * math.sin(math.radians(90 + 60 * k)))
           for k in range(6)]
    return cq.Workplane("YZ", origin=(x0, 0, 0)).polyline(pts).close().extrude(x1 - x0)


def gland(side, kind):
    """PG gland stand-in on the left (side=-1) or right (side=+1) wall, outward along x."""
    xw, xi = CORE_HX + WALL_OFF, CAV_HX        # 73, 70
    if kind == "PG21":
        y, z = PG21_YZ
        hex_d, thread_r, nut_out, nut_in, cap_r, cap_l, cable_r, cable_l = 38.1, 14.15, 8.0, 5.0, 15.0, 22.0, 7.2, 40.0
    else:
        y, z = PG9_YZ
        hex_d, thread_r, nut_out, nut_in, cap_r, cap_l, cable_r, cable_l = 21.94, 7.6, 6.0, 4.0, 8.5, 14.0, 0.0, 0.0
    # build on the left wall (negative x), mirror for the right
    g = hex_x(hex_d, -xw - nut_out, -xw, y, z)
    g = g.union(cyl(thread_r, (-xw, y, z), (1, 0, 0), xw - xi))
    g = g.union(hex_x(hex_d, -xi, -xi + nut_in, y, z))
    g = g.union(cyl(cap_r, (-xw - nut_out - cap_l, y, z), (1, 0, 0), cap_l))
    if cable_l:
        g = g.union(cyl(cable_r, (-xw - nut_out - cap_l - cable_l, y, z), (1, 0, 0), cable_l))
    if side > 0:
        g = g.mirror("YZ")
    return g


def wire_y(x, z, y0, y1, r=1.5):
    return cyl(r, (x, y0, z), (0, 1, 0), y1 - y0)


def build_parts():
    P = []   # (name, shape, sRGB colour)
    P.append(("PG21_trunk_left", gland(-1, "PG21"), (0.85, 0.4, 0.2)))
    P.append(("PG21_trunk_right", gland(+1, "PG21"), (0.85, 0.4, 0.2)))
    P.append(("PG9_lamp_left", gland(-1, "PG9"), (0.6, 0.6, 0.6)))
    P.append(("power_pcb_120x60", box((-60.0, 60.0), (-66.5, -6.5), (10.5, 12.1)), (0.1, 0.5, 0.5)))
    P.append(("pcb_parts_envelope", box((-56.0, 32.0), (-62.5, -20.5), (12.1, 22.1)), (0.2, 0.6, 0.6)))
    esp = box((36.0, 54.0), (-63.5, -44.3), (12.1, 15.3)).union(box((37.0, 40.0), (-45.3, -41.8), (14.3, 16.3)))
    P.append(("esp32_s3_wroom_1u_with_ufl", esp, (0.7, 0.7, 0.7)))
    P.append(("cell_18650_style_2200mAh", cyl(9.0, (-2.0, CELL_Y, CELL_Z), (1, 0, 0), 69.0), (0.2, 0.4, 0.8)))
    P.append(("antenna_standin", box((-67.0, -57.0), (-65.5, -35.5), (41.0, 43.0)), (0.9, 0.2, 0.6)))
    red, orange = (0.85, 0.3, 0.2), (0.9, 0.55, 0.2)
    P.append(("input_wire_12V_A", wire_y(12.2, 22.2, 14.5, 37.5), red))
    P.append(("input_wire_12V_B", wire_y(15.8, 22.2, 14.5, 37.5), red))
    P.append(("input_wire_GND_A", wire_y(12.2, 25.8, 14.5, 37.5), red))
    P.append(("input_wire_GND_B", wire_y(15.8, 25.8, 14.5, 37.5), red))
    P.append(("output_wire_tail", wire_y(-38.2, 22.6, -15.5, 7.5), orange))
    P.append(("output_wire_stop_turn", wire_y(-33.8, 22.6, -15.5, 7.5), orange))
    P.append(("output_wire_ground", wire_y(-36.0, 26.2, -15.5, 7.5), orange))
    for i, xc in enumerate(WAGO_IN_POCKETS["xc"]):
        P.append((f"WAGO_221_413_input_lever_{i}",
                  box((xc - 9.4, xc + 9.4), (36.7, 55.3), (7.5, 15.9)), (0.95, 0.7, 0.3)))
    for nm, xc in zip(("tail", "stop_turn", "ground"), WAGO_OUT_POCKETS["xc"]):
        P.append((f"WAGO_221_412_output_lever_{nm}",
                  box((xc - 6.5, xc + 6.5), (6.85, 25.15), (7.5, 15.65)), (0.95, 0.5, 0.1)))
    for i, (x, y) in enumerate(MAGNETS_XY):
        P.append((f"magnet_{i}", cyl(7.94, (x, y, -0.3), (0, 0, 1), 3.17), (0.8, 0.2, 0.2)))
    return P


def build_assembly(body, lid_w, lid_e, parts):
    a = cq.Assembly(name="OTM_housing_v6")
    a.add(body, name="body", color=cq.Color(0.2, 0.2, 0.25))
    a.add(lid_w.translate((0, 0, TOP_Z)), name="lid_wiring_bay_client", color=cq.Color(0.45, 0.5, 0.6))
    a.add(lid_e.translate((0, 0, TOP_Z)), name="lid_electronics_bay_service", color=cq.Color(0.3, 0.33, 0.4))
    for nm, shp, c in parts:
        a.add(shp, name=nm, color=cq.Color(*c))
    return a


# ---------------------------------------------------------------------------
# Images (matplotlib)
# ---------------------------------------------------------------------------

GRAY, ORANGE, TEAL = "#4a4a58", "#d2592a", "#1f8a84"


def _section_lines(shape, origin, normal):
    """Edges of `shape` cut by a plane, as lists of 3D points."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    sec = BRepAlgoAPI_Section(shape.wrapped, gp_Pln(gp_Pnt(*origin), gp_Dir(*normal)))
    sec.Build()
    out = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        n = max(2, int(e.Length() / 0.5))
        out.append([e.positionAt(i / n) for i in range(n + 1)])
    return out


def _plot_section(ax, shape, z_or_x, color, plan=True):
    if plan:
        for pl in _section_lines(shape, (0, 0, z_or_x), (0, 0, 1)):
            ax.plot([p.x for p in pl], [p.y for p in pl], color=color, lw=1.1)
    else:
        for pl in _section_lines(shape, (z_or_x, 0, 0), (1, 0, 0)):
            ax.plot([p.y for p in pl], [p.z for p in pl], color=color, lw=1.1)


def _mesh(shape, tol=0.3):
    verts, tris = shape.tessellate(tol, 0.3)
    return [[(verts[i].x, verts[i].y, verts[i].z) for i in t] for t in tris]


def _draw3d(ax, items, elev, azim, title):
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    # one collection for everything so matplotlib depth-sorts every triangle together
    all_polys, all_cols = [], []
    for shp, rgb in items:
        polys = _mesh(shp.val() if hasattr(shp, "val") else shp)
        for p in polys:
            a, b, c = (np.array(v) for v in p)
            n = np.cross(b - a, c - a); ln = np.linalg.norm(n)
            k = 0.45 + 0.55 * abs(float(np.dot(n / ln, light))) if ln > 0 else 0.6
            all_cols.append(tuple(min(1.0, ch * k) for ch in rgb))
        all_polys += polys
    pc = Poly3DCollection(all_polys, facecolors=all_cols, edgecolors=(0, 0, 0, 0.08), linewidths=0.2)
    ax.add_collection3d(pc)
    lim = 100
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim + 30, lim + 30)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title)


def make_images(out, body, lid_w, lid_e, parts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lw = lid_w.translate((0, 0, TOP_Z))
    le = lid_e.translate((0, 0, TOP_Z))
    body_rgb, lw_rgb, le_rgb = (0.55, 0.57, 0.65), (0.6, 0.64, 0.75), (0.5, 0.53, 0.62)
    part_items = [(shp, c) for _, shp, c in parts]

    fig = plt.figure(figsize=(19, 7))
    _draw3d(fig.add_subplot(131, projection="3d"), [(body, body_rgb)] + part_items, 90, -90,
            "Plan view, both lids off")
    _draw3d(fig.add_subplot(132, projection="3d"), [(body, body_rgb), (le, le_rgb)] + part_items, 35, -60,
            "Wiring lid off, electronics lid on")
    _draw3d(fig.add_subplot(133, projection="3d"), [(body, body_rgb), (lw, lw_rgb), (le, le_rgb)] + part_items,
            30, -60, "Closed")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "housing_v6_preview.png"), dpi=100)
    plt.close(fig)

    b, w, e = body.val(), lw.val(), le.val()
    z_body, z_lid = TOP_Z - 0.5, TOP_Z + 1.0

    fig, ax = plt.subplots(figsize=(9.6, 9.6))
    _plot_section(ax, b, z_body, GRAY); _plot_section(ax, w, z_lid, ORANGE); _plot_section(ax, e, z_lid, TEAL)
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Plan section: body just below the top face (gray), lids at the O-ring groove depth "
                 "(orange = wiring lid, teal = electronics lid)", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(out, "housing_v6_plan_section.png"), dpi=100); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    _plot_section(ax, b, 0.0, GRAY, plan=False); _plot_section(ax, w, 0.0, ORANGE, plan=False)
    _plot_section(ax, e, 0.0, TEAL, plan=False)
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Section through x = 0: flange gusset, face-seal grooves, radial lips, skirts, partition cap")
    fig.tight_layout(); fig.savefig(os.path.join(out, "housing_v6_side_section.png"), dpi=100); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(11.3, 5.8))
    for ax, (xl, yl), t in zip(axs, (((-45, 5), (-20, 50)), ((30, 95), (20, 95))),
                               ("Zoom: both reflex corners at the partition",
                                "Zoom: wiring-lid corner and the right-hand partition end")):
        _plot_section(ax, b, z_body, GRAY); _plot_section(ax, w, z_lid, ORANGE); _plot_section(ax, e, z_lid, TEAL)
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_title(t)
    fig.tight_layout(); fig.savefig(os.path.join(out, "housing_v6_corner_zoom.png"), dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------

def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    out = args[0] if args else "out"
    os.makedirs(out, exist_ok=True)

    body = build_body()
    lid_w = build_lid("wiring")
    lid_e = build_lid("electronics")
    parts = build_parts()

    cq.exporters.export(body, os.path.join(out, "housing_v6_body.step"))
    cq.exporters.export(lid_w, os.path.join(out, "housing_v6_lid_wiring_bay.step"))
    cq.exporters.export(lid_e, os.path.join(out, "housing_v6_lid_electronics_bay.step"))
    build_assembly(body, lid_w, lid_e, parts).export(os.path.join(out, "housing_v6_assembly_with_parts.step"))

    for nm, s in (("body", body), ("lid_wiring_bay", lid_w), ("lid_electronics_bay", lid_e)):
        v = s.val()
        bb = v.BoundingBox()
        print(f"{nm:22s} volume {v.Volume():12.3f} mm^3   bbox "
              f"{bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}   faces {len(v.Faces())}")

    if "--no-png" not in argv:
        make_images(out, body, lid_w, lid_e, parts)
    print("written to", os.path.abspath(out))


if __name__ == "__main__":
    main(sys.argv[1:])
