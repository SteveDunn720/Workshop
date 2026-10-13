"""Best-fit planar placement for Maya guide chains.

Call before orienting and parenting guide joints. Uses a symmetric 3x3
Jacobi eigensolver so it does not require numpy inside Maya.
"""
from __future__ import annotations

import math
from maya import cmds


def _smallest_eigenvector(matrix: list[list[float]]) -> tuple[float, float, float]:
    a = [row[:] for row in matrix]
    v = [[float(i == j) for j in range(3)] for i in range(3)]
    for _ in range(40):
        p, q = max(((0, 1), (0, 2), (1, 2)), key=lambda pair: abs(a[pair[0]][pair[1]]))
        if abs(a[p][q]) < 1e-12:
            break
        angle = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(angle), math.sin(angle)
        # Rotation of basis columns p/q.
        for i in range(3):
            vip, viq = v[i][p], v[i][q]
            v[i][p] = c * vip - s * viq
            v[i][q] = s * vip + c * viq
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = c*c*app - 2*s*c*apq + s*s*aqq
        a[q][q] = s*s*app + 2*s*c*apq + c*c*aqq
        a[p][q] = a[q][p] = 0.0
        for i in range(3):
            if i in (p, q):
                continue
            aip, aiq = a[i][p], a[i][q]
            a[i][p] = a[p][i] = c*aip - s*aiq
            a[i][q] = a[q][i] = s*aip + c*aiq
    k = min(range(3), key=lambda i: a[i][i])
    n = [v[i][k] for i in range(3)]
    length = math.sqrt(sum(x*x for x in n))
    if length < 1e-10:
        raise ValueError('Could not calculate a stable plane normal')
    return tuple(x / length for x in n)


def force_planar_guides(
    guides: list[str],
    *,
    keep_endpoints: bool = False,
    normal_hint: tuple[float, float, float] | None = None,
) -> tuple[float, float, float]:
    """Project world-space guide positions onto their least-squares plane.

    The best-fit plane passes through the centroid. For exactly three
    noncollinear guides, all three already lie on the plane.
    """
    if len(guides) < 3:
        raise ValueError('Planar solving requires at least three guides')
    pts = [cmds.xform(g, q=True, ws=True, t=True) for g in guides]
    center = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    offsets = [[p[i] - center[i] for i in range(3)] for p in pts]
    cov = [[sum(d[i] * d[j] for d in offsets) for j in range(3)] for i in range(3)]
    normal = _smallest_eigenvector(cov)
    if normal_hint and sum(normal[i]*normal_hint[i] for i in range(3)) < 0:
        normal = tuple(-x for x in normal)
    # Degenerate straight chains have no unique plane.
    # Require a second non-parallel direction before moving any points.
    max_cross = 0.0
    for i in range(len(offsets)):
        for j in range(i + 1, len(offsets)):
            u, v = offsets[i], offsets[j]
            cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            max_cross = max(max_cross, sum(x*x for x in cross))
    if max_cross < 1e-12:
        raise ValueError('Guide chain is nearly collinear; no unique best-fit plane')
    for index, (guide, point) in enumerate(zip(guides, pts)):
        if keep_endpoints and index in (0, len(guides)-1):
            continue
        d = sum((point[i]-center[i])*normal[i] for i in range(3))
        projected = [point[i] - d*normal[i] for i in range(3)]
        cmds.xform(guide, ws=True, t=projected)
    return normal
