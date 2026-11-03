#!/usr/bin/env python3
"""
ICM (in-cab module) housing, v1 - CadQuery build script.

Rough first version around a stand-in PCB (no layout yet), same approach as the OTM housing.

  * Body + snap-fit lid. In-cab, so no O-rings, no bolts, no glands.
  * J2 (Molex Micro-Fit 3.0, 43045-0600 right-angle, 2 x 3) sits on the -x board edge; the truck
    plug (43025-0600) goes in from outside through a window in the -x wall and latches onto it.
  * Antenna outside the housing: RP-SMA bulkhead (U.FL pigtail) through the +x wall, D-hole so it
    can't spin.
  * Pairing switch (TE FSMRA6J right-angle tact) on the +y board edge behind a 3 mm poke hole
    (pen tip / paperclip), so it can't be bumped by accident.
  * Piezo (Murata PKLCS1212E4001, 12 x 12 x 3) under a 3 x 3 grid of sound holes in the lid.
  * 7 status LEDs in a row under 2 mm windows in the lid (visible if you look, nothing more).
  * USB-C (vertical), boot and reset buttons: reached by popping the lid.
  * Snap fit: 4 cantilever hooks on the lid (2 per long side) catch in through-windows in the
    long walls. Release: push each hook in through its window with a small screwdriver.
  * Flat bottom, no mounting features yet (command strips / Velcro).

Board stand-in: 64 x 46 x 1.6, four M3 holes into heat-set inserts (same inserts as the OTM).

Outputs (default ./out_v1):
    icm_housing_v1_body.step / .stl
    icm_housing_v1_lid.step / .stl
    icm_housing_v1_assembly_with_parts.step
    icm_housing_v1_preview.png, icm_housing_v1_sections.png

Usage:
    pip install cadquery matplotlib numpy
    python icm_housing_v1.py [output_folder] [--no-png]

Print: PETG or ASA (not PLA: dash temperatures). Body floor-down, lid plate-down (hooks up).
Clearances are the OTM's (0.3 mm sliding fits).

Units mm. Origin: centre of the footprint, z = 0 on the underside of the body.
"""

import math
import os
import sys

import cadquery as cq

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

# Body
INT_HX, INT_HY, INT_R = 33.0, 24.0, 2.5        # cavity 66 x 48
WALL_T = 2.5
FLOOR_T = 2.5
OUT_HX, OUT_HY, OUT_R = INT_HX + WALL_T, INT_HY + WALL_T, INT_R + WALL_T   # 71 x 53, R5
TOP_CHAMFER = 0.8                               # lead-in on the inside top edge for the hooks

# PCB stand-in
STANDOFF_H, STANDOFF_D = 4.0, 7.0
INSERT_D, INSERT_DEPTH = 4.0, 5.0               # M3 heat-set inserts (same as the OTM)
PCB = dict(x=(-32.7, 31.3), y=(-23.0, 23.0), t=1.6)   # 64 x 46; -x edge 0.3 off the wall (J2)
PCB_R = 1.5                                     # board corner radius (clears the cavity corners)
PCB_HOLES = [(-29.2, -19.5), (27.8, -19.5), (27.8, 19.5), (-29.2, 19.5)]
PCB_Z0 = FLOOR_T + STANDOFF_H                   # 6.5
PCB_TOP = PCB_Z0 + PCB["t"]                     # 8.1

# Height: 16 mm over the board keeps the lid lip above the J2 window and the RP-SMA nut
TOP_Z = PCB_TOP + 16.0                          # 24.1 body height

# Lid
LID_T = 2.0
LIP_CLEAR, LIP_T, LIP_DEPTH = 0.3, 1.6, 3.0     # locating lip inside the walls

# Snap hooks (lid) and their windows (body long walls)
HOOK_X = (-18.0, 18.0)                          # on both long sides
ARM_W, ARM_T, ARM_L = 8.0, 1.4, 10.0            # cantilever arm
ARM_SLOT = 0.8                                  # gap cut in the lip each side of the arm
HOOK_D, HOOK_H = 1.1, 2.0                       # hook protrusion past the arm face, ramp height
WIN_W, WIN_H, WIN_PLAY = 8.8, 2.8, 0.15         # body window; catch sits 0.15 under its top edge

# J2: Molex Micro-Fit 3.0 right-angle header 43045-0600 on the -x board edge, mating plug 43025-0600
J2_Y = 0.0
PLUG_W, PLUG_H = 9.85, 11.56                    # 43025-0600 outline incl. latch (RS listing)
J2_WIN = dict(y=(J2_Y - 5.3, J2_Y + 5.3), z=(PCB_TOP + 0.45, PCB_TOP + 12.75))   # plug + ~0.35/side

# RP-SMA bulkhead (1/4"-36 thread) through the +x wall, D-hole
SMA_Y, SMA_Z = 10.0, PCB_TOP + 7.0              # 15.1
SMA_HOLE_R, SMA_FLAT = 3.25, 2.9                # 6.5 mm hole, flat 2.9 from centre (5.8 across)

# Pairing switch poke hole (+y wall)
PAIR_X, PAIR_Z, PAIR_HOLE_D = 0.0, PCB_TOP + 1.8, 3.0

# Lid holes
BUZZER_XY = (-10.0, 11.0)
SOUND_HOLE_D, SOUND_PITCH = 1.5, 2.5            # 3 x 3 grid
LED_Y = -12.0
LED_X = [-12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0]
LED_HOLE_D = 2.0


# ---------------------------------------------------------------------------
# Helpers (same as the OTM script)
# ---------------------------------------------------------------------------

def _turn(pts, i):
    n = len(pts)
    ax, ay = pts[i - 1]; px, py = pts[i]; bx, by = pts[(i + 1) % n]
    li = math.hypot(px - ax, py - ay); lo = math.hypot(bx - px, by - py)
    din = ((px - ax) / li, (py - ay) / li); dout = ((bx - px) / lo, (by - py) / lo)
    return din, dout, (din[0] * dout[1] - din[1] * dout[0]) > 0


def rounded_poly(pts, radii, z=0.0):
    n = len(pts)
    if isinstance(radii, (int, float)):
        radii = [float(radii)] * n
    corners = []
    for i in range(n):
        din, dout, _ = _turn(pts, i)
        r = radii[i]; px, py = pts[i]
        p1 = (px - din[0] * r, py - din[1] * r); p2 = (px + dout[0] * r, py + dout[1] * r)
        c = (p1[0] + dout[0] * r, p1[1] + dout[1] * r)
        dx, dy = px - c[0], py - c[1]; d = math.hypot(dx, dy) or 1.0
        corners.append((p1, (c[0] + dx / d * r, c[1] + dy / d * r), p2, r))
    wp = cq.Workplane("XY", origin=(0, 0, z)).moveTo(*corners[0][2])
    for i in range(1, n + 1):
        p1, mid, p2, r = corners[i % n]
        wp = wp.lineTo(*p1)
        if r > 0:
            wp = wp.threePointArc(mid, p2)
    return wp.close()


def rrect(hx, hy, r):
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)], r


def prism(pr, z0, z1):
    pts, r = pr
    return rounded_poly(pts, r, z0).extrude(z1 - z0)


def offset_rr(pr, d):
    pts, r = pr
    hx, hy = pts[2]
    return rrect(hx + d, hy + d, max(r + d, 0.0))


def ring(outer, inner, z0, z1):
    return prism(outer, z0, z1).cut(prism(inner, z0 - 1, z1 + 1))


def box(x, y, z):
    return cq.Workplane("XY").box(x[1] - x[0], y[1] - y[0], z[1] - z[0], centered=False) \
        .translate((x[0], y[0], z[0]))


def cyl(r, p0, direction, length):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, length, cq.Vector(*p0), cq.Vector(*direction)))


def loft_rr(lower, z0, upper, z1):
    w0 = rounded_poly(*lower, z0).val()
    w1 = rounded_poly(*upper, z1).val()
    return cq.Workplane(obj=cq.Solid.makeLoft([w0, w1], True))


def d_hole_x(y, z, r, flat, x0, x1):
    """Round hole along x with one flat (at the bottom), from x0 to x1."""
    c = cyl(r, (x0, y, z), (1, 0, 0), x1 - x0)
    return c.cut(box((x0 - 1, x1 + 1), (y - r - 1, y + r + 1), (z - r - 1, z - flat)))


INTERIOR = rrect(INT_HX, INT_HY, INT_R)
OUTSIDE = rrect(OUT_HX, OUT_HY, OUT_R)


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

def build_body():
    body = prism(OUTSIDE, 0.0, TOP_Z).cut(prism(INTERIOR, FLOOR_T, TOP_Z + 1))
    # lead-in chamfer on the inside top edge (hooks ride over it)
    body = body.cut(loft_rr(INTERIOR, TOP_Z - TOP_CHAMFER, offset_rr(INTERIOR, TOP_CHAMFER), TOP_Z + 0.01))

    # PCB standoffs with M3 heat-set insert holes
    for (x, y) in PCB_HOLES:
        body = body.union(cyl(STANDOFF_D / 2, (x, y, FLOOR_T - 0.01), (0, 0, 1), STANDOFF_H + 0.01))
        body = body.cut(cyl(INSERT_D / 2, (x, y, PCB_Z0 - INSERT_DEPTH), (0, 0, 1), INSERT_DEPTH + 0.5))

    # J2 window (-x wall): the 43025-0600 plug passes through and latches on the header inside
    body = body.cut(box((-OUT_HX - 1, -INT_HX + 0.1), J2_WIN["y"], J2_WIN["z"]))

    # RP-SMA bulkhead D-hole (+x wall)
    body = body.cut(d_hole_x(SMA_Y, SMA_Z, SMA_HOLE_R, SMA_FLAT, INT_HX - 0.1, OUT_HX + 1))

    # pairing switch poke hole (+y wall)
    body = body.cut(cyl(PAIR_HOLE_D / 2, (PAIR_X, INT_HY - 0.1, PAIR_Z), (0, 1, 0), WALL_T + 1.2))

    # snap windows in both long walls; the hook catch sits WIN_PLAY under the window's top edge
    catch_z = TOP_Z - ARM_L + HOOK_H
    for x in HOOK_X:
        for sy in (-1, 1):
            y0, y1 = (INT_HY - 0.1, OUT_HY + 1) if sy > 0 else (-OUT_HY - 1, -INT_HY + 0.1)
            body = body.cut(box((x - WIN_W / 2, x + WIN_W / 2), (y0, y1),
                                (catch_z + WIN_PLAY - WIN_H, catch_z + WIN_PLAY)))
    return body


# ---------------------------------------------------------------------------
# Lid (own frame: z = 0 is the underside that sits on the wall top)
# ---------------------------------------------------------------------------

def hook_profile(x, sy):
    """Arm + hook on the long side sy (+1 / -1), lid frame."""
    y_out = sy * (INT_HY - LIP_CLEAR)                     # arm outer face
    y_in = y_out - sy * ARM_T
    arm = box((x - ARM_W / 2, x + ARM_W / 2), tuple(sorted((y_in, y_out))), (-ARM_L, 0.01))
    # hook: triangular prism, ramp at the bottom, flat catch on top
    pts = [(y_out, -ARM_L), (y_out + sy * HOOK_D, -ARM_L + HOOK_H), (y_out, -ARM_L + HOOK_H)]
    hook = (cq.Workplane("YZ", origin=(x - ARM_W / 2 + 0.5, 0, 0)).polyline(pts).close()
            .extrude(ARM_W - 1.0))
    return arm.union(hook)


def build_lid():
    lid = prism(OUTSIDE, 0.0, LID_T)
    lip_out = offset_rr(INTERIOR, -LIP_CLEAR)
    lip = ring(lip_out, offset_rr(lip_out, -LIP_T), -LIP_DEPTH, 0.01)
    # free the arms: slot the lip around each hook
    for x in HOOK_X:
        for sy in (-1, 1):
            y = (INT_HY - 4.0, INT_HY + 1.0) if sy > 0 else (-INT_HY - 1.0, -INT_HY + 4.0)
            lip = lip.cut(box((x - ARM_W / 2 - ARM_SLOT, x + ARM_W / 2 + ARM_SLOT), y, (-LIP_DEPTH - 1, 0.0)))
    lid = lid.union(lip)
    for x in HOOK_X:
        for sy in (-1, 1):
            lid = lid.union(hook_profile(x, sy))

    # sound holes over the piezo (3 x 3)
    bx, by = BUZZER_XY
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            lid = lid.cut(cyl(SOUND_HOLE_D / 2, (bx + i * SOUND_PITCH, by + j * SOUND_PITCH, -1), (0, 0, 1), LID_T + 2))
    # LED windows
    for x in LED_X:
        lid = lid.cut(cyl(LED_HOLE_D / 2, (x, LED_Y, -1), (0, 0, 1), LID_T + 2))
    return lid


# ---------------------------------------------------------------------------
# Stand-in parts (body coordinates)
# ---------------------------------------------------------------------------

def build_parts():
    P = []
    z1 = PCB_TOP
    (x0, x1), (y0, y1) = PCB["x"], PCB["y"]
    pcb = rounded_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], PCB_R, PCB_Z0).extrude(PCB["t"])
    for (x, y) in PCB_HOLES:
        pcb = pcb.cut(cyl(1.6, (x, y, PCB_Z0 - 1), (0, 0, 1), 4))
    P.append(("icm_pcb_64x46_standin", pcb, (0.1, 0.5, 0.5)))

    # J2 header 43045-0600 (right angle), front face on the board edge
    hx0 = PCB["x"][0]
    hdr = box((hx0, hx0 + 12.4), (J2_Y - 5.8, J2_Y + 5.8), (z1, z1 + 9.6))
    hdr = hdr.cut(box((hx0 - 0.1, hx0 + 7.0), (J2_Y - 5.0, J2_Y + 5.0), (z1 + 0.7, z1 + 8.9)))
    P.append(("J2_microfit_43045-0600_header", hdr, (0.92, 0.92, 0.88)))
    # mating plug 43025-0600 (reference), inserted 7 mm
    plug = box((hx0 - 14.0 + 7.0, hx0 + 7.0), (J2_Y - PLUG_W / 2, J2_Y + PLUG_W / 2), (z1 + 0.8, z1 + 8.8))
    plug = plug.union(box((hx0 - 6.0, hx0 - 0.1), (J2_Y - 2.0, J2_Y + 2.0), (z1 + 8.8, z1 + 0.8 + PLUG_H)))
    P.append(("J2_mating_plug_43025-0600_ref", plug, (0.85, 0.85, 0.8)))

    # ESP32-S3-WROOM-1U (18 x 19.2 x 3.2) + U.FL
    P.append(("esp32_s3_wroom_1u", box((3.0, 22.2), (-2.0, 16.0), (z1, z1 + 3.2)), (0.7, 0.7, 0.7)))
    ufl_xy = (20.5, 12.5)
    P.append(("ufl_plug", box((ufl_xy[0] - 1.5, ufl_xy[0] + 1.5), (ufl_xy[1] - 1.5, ufl_xy[1] + 1.5), (z1 + 3.2, z1 + 5.2)), (0.8, 0.75, 0.5)))
    # U.FL pigtail (1.13 mm coax) to the bulkhead
    ux, uy = ufl_xy
    pig = cyl(0.6, (ux, uy, z1 + 5.2), (0, 0, 1), SMA_Z - (z1 + 5.2))
    pig = pig.union(cyl(0.6, (ux, uy, SMA_Z), (0, -1, 0), uy - SMA_Y))
    pig = pig.union(cyl(0.6, (ux, SMA_Y, SMA_Z), (1, 0, 0), 25.0 - ux))
    P.append(("ufl_pigtail", pig, (0.15, 0.15, 0.15)))
    # RP-SMA bulkhead: inside body, thread through the wall, outside nut + jack
    sma = cyl(4.0, (25.0, SMA_Y, SMA_Z), (1, 0, 0), INT_HX - 25.0)
    thread = cyl(3.17, (INT_HX, SMA_Y, SMA_Z), (1, 0, 0), OUT_HX + 6.5 - INT_HX)
    thread = thread.cut(box((INT_HX - 1, OUT_HX + 8), (SMA_Y - 5, SMA_Y + 5), (SMA_Z - 5, SMA_Z - SMA_FLAT + 0.05)))
    sma = sma.union(thread)
    sma = sma.union(cyl(4.6, (OUT_HX, SMA_Y, SMA_Z), (1, 0, 0), 2.0))
    sma = sma.union(cyl(3.0, (OUT_HX + 6.5, SMA_Y, SMA_Z), (1, 0, 0), 6.0))
    P.append(("rp_sma_bulkhead", sma, (0.85, 0.7, 0.3)))

    # piezo PKLCS1212E4001 (12 x 12 x 3)
    bx, by = BUZZER_XY
    P.append(("piezo_PKLCS1212E4001", box((bx - 6, bx + 6), (by - 6, by + 6), (z1, z1 + 3.0)), (0.15, 0.15, 0.15)))
    # USB-C vertical UJ20-C-V-G-SMT (8.94 x 4.3 x 6.4)
    P.append(("usb_c_vertical", box((-6.0, 2.94), (-22.5, -18.2), (z1, z1 + 6.4)), (0.75, 0.75, 0.78)))
    # status LEDs
    for i, x in enumerate(LED_X):
        P.append((f"led_{i}", box((x - 0.8, x + 0.8), (LED_Y - 0.4, LED_Y + 0.4), (z1, z1 + 0.6)), (0.2, 0.8, 0.2)))
    # pairing switch FSMRA6J (right angle), actuator facing +y
    P.append(("pairing_switch_FSMRA6J", box((PAIR_X - 3.5, PAIR_X + 3.5), (16.3, 23.0), (z1, z1 + 3.5)), (0.3, 0.3, 0.3)))
    P.append(("pairing_switch_actuator", box((PAIR_X - 1.2, PAIR_X + 1.2), (23.0, 23.7), (PAIR_Z - 0.9, PAIR_Z + 0.9)), (0.9, 0.3, 0.2)))
    # boot / reset buttons
    P.append(("sw_boot", box((-20.0, -16.5), (-21.5, -17.0), (z1, z1 + 2.0)), (0.3, 0.3, 0.3)))
    P.append(("sw_reset", box((-14.5, -11.0), (-21.5, -17.0), (z1, z1 + 2.0)), (0.3, 0.3, 0.3)))
    # keep-in zones for the rest (buck converter, input protection / dividers)
    P.append(("buck_zone_4mm", box((15.0, 24.5), (-21.0, -5.0), (z1, z1 + 4.0)), (0.2, 0.6, 0.6)))
    P.append(("input_zone_3mm", box((-19.5, -8.0), (-9.0, 3.0), (z1, z1 + 3.0)), (0.2, 0.6, 0.6)))
    # M3 screws (pan head)
    for i, (x, y) in enumerate(PCB_HOLES):
        P.append((f"M3x6_screw_{i}", cyl(1.5, (x, y, PCB_Z0 - 4.4), (0, 0, 1), 6.0)
                  .union(cyl(2.75, (x, y, z1), (0, 0, 1), 2.4)), (0.25, 0.25, 0.28)))
    return P


def build_assembly(body, lid, parts):
    a = cq.Assembly(name="ICM_housing_v1")
    a.add(body, name="body", color=cq.Color(0.2, 0.2, 0.25))
    a.add(lid.translate((0, 0, TOP_Z)), name="lid", color=cq.Color(0.3, 0.33, 0.4))
    for nm, shp, c in parts:
        a.add(shp, name=nm, color=cq.Color(*c))
    return a


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

GRAY, ORANGE, BLUE = "#4a4a58", "#d2592a", "#3a5fb0"


def _section_lines(shape, origin, normal):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    sec = BRepAlgoAPI_Section(shape.wrapped, gp_Pln(gp_Pnt(*origin), gp_Dir(*normal)))
    sec.Build()
    out = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        n = max(2, int(e.Length() / 0.3))
        out.append([e.positionAt(i / n) for i in range(n + 1)])
    return out


def _plot(ax, shape, plane, value, color, lw=1.1):
    if plane == "z":
        for pl in _section_lines(shape, (0, 0, value), (0, 0, 1)):
            ax.plot([p.x for p in pl], [p.y for p in pl], color=color, lw=lw)
    elif plane == "x":
        for pl in _section_lines(shape, (value, 0, 0), (1, 0, 0)):
            ax.plot([p.y for p in pl], [p.z for p in pl], color=color, lw=lw)
    else:
        for pl in _section_lines(shape, (0, value, 0), (0, 1, 0)):
            ax.plot([p.x for p in pl], [p.z for p in pl], color=color, lw=lw)


def _mesh(shape, tol=0.15):
    verts, tris = shape.tessellate(tol, 0.2)
    return [[(verts[i].x, verts[i].y, verts[i].z) for i in t] for t in tris]


def _draw3d(ax, items, elev, azim, title, zlim=(-5, 40), lim=48):
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    polys_all, cols_all = [], []
    for shp, rgb in items:
        polys = _mesh(shp.val() if hasattr(shp, "val") else shp)
        for p in polys:
            a, b, c = (np.array(v) for v in p)
            n = np.cross(b - a, c - a); ln = np.linalg.norm(n)
            k = 0.45 + 0.55 * abs(float(np.dot(n / ln, light))) if ln > 0 else 0.6
            cols_all.append(tuple(min(1.0, ch * k) for ch in rgb))
        polys_all += polys
    ax.add_collection3d(Poly3DCollection(polys_all, facecolors=cols_all, edgecolors=(0, 0, 0, 0.08), linewidths=0.2))
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(*zlim)
    ax.set_box_aspect((1, 1, (zlim[1] - zlim[0]) / (2 * lim)), zoom=1.25)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title)


def make_images(out, body, lid, parts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lid_a = lid.translate((0, 0, TOP_Z))
    body_rgb, lid_rgb = (0.55, 0.57, 0.65), (0.5, 0.53, 0.62)
    items = [(s, c) for _, s, c in parts]

    def keep(its, kx=(-300, 300), ky=(-300, 300), kz=(-100, 300)):
        k = box(kx, ky, kz).val()
        res = []
        for shp, rgb in its:
            s = (shp.val() if hasattr(shp, "val") else shp).intersect(k)
            if s.Volume() > 1e-3:
                res.append((s, rgb))
        return res

    everything = [(body, body_rgb), (lid_a, lid_rgb)] + items
    outside = [(s, c) for n, s, c in parts if n.startswith(("J2_mating_plug", "rp_sma"))]
    fig = plt.figure(figsize=(24, 15))
    _draw3d(fig.add_subplot(231, projection="3d"), [(body, body_rgb), (lid_a, lid_rgb)] + outside,
            28, -125, "Closed, J2 side: truck plug latched through the -x wall (71 x 53 x 26.1)")
    _draw3d(fig.add_subplot(232, projection="3d"), [(body, body_rgb), (lid_a, lid_rgb)] + outside,
            28, 55, "Closed, antenna side: RP-SMA bulkhead (+x), pairing poke hole (+y)")
    _draw3d(fig.add_subplot(233, projection="3d"), [(body, body_rgb)] + items,
            90, -90, "Lid off, from above: stand-in board 64 x 46")
    _draw3d(fig.add_subplot(234, projection="3d"), keep(everything, ky=(-300, J2_Y)),
            10, 90, "Cutaway at y = 0: J2 header + plug through the wall window")
    _draw3d(fig.add_subplot(235, projection="3d"), keep(everything, kx=(-300, HOOK_X[1])),
            12, 0, "Cutaway at x = 18: snap hooks caught in the wall windows")
    _draw3d(fig.add_subplot(236, projection="3d"), [(lid, lid_rgb)],
            -55, -60, "Lid from below: locating lip, 4 snap hooks, sound + LED holes", zlim=(-15, 10))
    fig.tight_layout()
    fig.savefig(os.path.join(out, "icm_housing_v1_preview.png"), dpi=100)
    plt.close(fig)

    b, l = body.val(), lid_a.val()
    others = [(s.val() if hasattr(s, "val") else s) for _, s, _ in parts]
    fig, axs = plt.subplots(3, 1, figsize=(13, 15))
    for ax, plane, val, title in (
            (axs[0], "y", J2_Y + 0.01, "Long section y = 0: J2 plug through the -x wall window"),
            (axs[1], "x", HOOK_X[1], "Cross section x = 18: lid hooks in the long-wall windows, lip inside the walls"),
            (axs[2], "y", SMA_Y, "Long section y = 10: RP-SMA bulkhead through the +x wall, U.FL pigtail")):
        _plot(ax, b, plane, val, GRAY); _plot(ax, l, plane, val, ORANGE)
        for o in others:
            _plot(ax, o, plane, val, BLUE, lw=0.7)
        ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_title(title)
    fig.tight_layout(); fig.savefig(os.path.join(out, "icm_housing_v1_sections.png"), dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------

def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    out = args[0] if args else "out_v1"
    os.makedirs(out, exist_ok=True)

    body = build_body()
    lid = build_lid()
    parts = build_parts()

    for nm, s in (("body", body), ("lid", lid)):
        cq.exporters.export(s, os.path.join(out, f"icm_housing_v1_{nm}.step"))
        cq.exporters.export(s, os.path.join(out, f"icm_housing_v1_{nm}.stl"), tolerance=0.03, angularTolerance=0.1)
        v = s.val(); bb = v.BoundingBox()
        print(f"{nm:6s} valid={v.isValid()} solids={len(s.solids().vals())} volume {v.Volume():9.1f} mm^3  "
              f"bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}")
    build_assembly(body, lid, parts).export(os.path.join(out, "icm_housing_v1_assembly_with_parts.step"))

    if "--no-png" not in argv:
        make_images(out, body, lid, parts)
    print("written to", os.path.abspath(out))


if __name__ == "__main__":
    main(sys.argv[1:])
