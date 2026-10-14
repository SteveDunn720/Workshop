"""Extract ordered shared topology between two Workshop polygroups.

Put this module in Workshop/poly/polygroup_boundary.py.
"""
from __future__ import annotations

from collections import defaultdict

from maya import cmds
from maya.api import OpenMaya as om

from Workshop.poly.polygroups import PolyGroup, get_polygroup, read_polygroup_layer_from_scene
from Workshop.poly.face import get_face_indices
from Workshop.poly.meshes import get_mesh_shape
from Workshop.poly.convert import to_border_edges
from Workshop.nurbs.curve import orient_curve


def _mesh_fn(mesh: str) -> om.MFnMesh:
    selection = om.MSelectionList()
    selection.add(get_mesh_shape(mesh))
    return om.MFnMesh(selection.getDagPath(0))


def get_shared_polygroup_edges(polygroup_a: PolyGroup, polygroup_b: PolyGroup) -> list[str]:
    """Return mesh edges separating faces in A from faces in B."""
    if polygroup_a.mesh != polygroup_b.mesh:
        # Different spellings of the same DAG node are allowed.
        a = cmds.ls(polygroup_a.mesh, long=True) or []
        b = cmds.ls(polygroup_b.mesh, long=True) or []
        if not a or not b or a[0] != b[0]:
            raise ValueError('Polygroups must belong to the same mesh')
    a_faces = set(get_face_indices(polygroup_a.get_faces()))
    b_faces = set(get_face_indices(polygroup_b.get_faces()))
    if not a_faces or not b_faces:
        raise ValueError('One or both polygroups contain no faces')
    if a_faces & b_faces:
        raise ValueError('Polygroups overlap; expected two distinct face regions')

    # Faces are mesh components; no UV-set-dependent conversion here.
    border_a = set(to_border_edges(polygroup_a.get_faces()))
    border_b = set(to_border_edges(polygroup_b.get_faces()))
    shared_names = border_a & border_b
    shared = sorted(int(edge.rsplit('[', 1)[1][:-1]) for edge in shared_names)
    if not shared:
        raise ValueError(f'No shared boundary between {polygroup_a.name!r} and {polygroup_b.name!r}')
    return [f'{polygroup_a.mesh}.e[{edge}]' for edge in shared]


def get_ordered_boundary_vertices(polygroup_a: PolyGroup, polygroup_b: PolyGroup) -> tuple[list[int], bool]:
    """Return ordered vertex IDs and whether the shared boundary is closed.

    Raises for branching or disconnected boundaries rather than creating an
    unpredictable curve. A closed boundary repeats its first vertex at the end.
    """
    fn = _mesh_fn(polygroup_a.mesh)
    edge_names = get_shared_polygroup_edges(polygroup_a, polygroup_b)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge_name in edge_names:
        edge_id = int(edge_name.rsplit('[', 1)[1][:-1])
        v0, v1 = fn.getEdgeVertices(edge_id)
        adjacency[v0].add(v1)
        adjacency[v1].add(v0)
    if any(len(neighbors) > 2 for neighbors in adjacency.values()):
        raise ValueError('Shared boundary branches; select simpler polygroup regions')
    ends = sorted(v for v, neighbors in adjacency.items() if len(neighbors) == 1)
    if len(ends) not in (0, 2):
        raise ValueError('Shared boundary is not a single open chain or closed loop')
    closed = not ends
    start = ends[0] if ends else min(adjacency)
    ordered = [start]
    previous = None
    current = start
    while True:
        candidates = sorted(adjacency[current] - ({previous} if previous is not None else set()))
        if not candidates:
            break
        nxt = candidates[0]
        if nxt == start:
            ordered.append(start)
            break
        if nxt in ordered:
            raise ValueError('Unexpected cycle in boundary')
        ordered.append(nxt)
        previous, current = current, nxt
    if len(set(ordered)) != len(adjacency):
        raise ValueError('Shared boundary has multiple disconnected chains')
    return ordered, closed


def get_shared_polygroup_positions(polygroup_a: PolyGroup, polygroup_b: PolyGroup, reverse: bool = False) -> tuple[list[tuple[float, float, float]], bool]:
    """Ordered world-space vertex positions along the shared boundary."""
    fn = _mesh_fn(polygroup_a.mesh)
    vertices, closed = get_ordered_boundary_vertices(polygroup_a, polygroup_b)
    if reverse:
        vertices.reverse()
    positions = [tuple(fn.getPoint(index, om.MSpace.kWorld))[:3] for index in vertices]
    return positions, closed


def create_polygroup_boundary_curve(
    mesh: str,
    uv_set: str,
    region_a: str,
    region_b: str,
    name: str,
    degree: int = 3,
    spans: int | None = None,
    reverse: bool = False,
    parent: str | None = None,
    direction: str = "outward",
    direction_axis: str = "X",
) -> str:
    """Build a NURBS curve through the boundary between two named regions.

    The initial curve interpolates topology vertices; `spans` optionally
    rebuilds it to a more compact editable curve.
    """
    layer = read_polygroup_layer_from_scene(mesh=mesh, uv_set=uv_set)
    a = get_polygroup(layer=layer, name=region_a)
    b = get_polygroup(layer=layer, name=region_b)
    positions, closed = get_shared_polygroup_positions(a, b, reverse=False)
    unique_count = len(positions) - int(closed)
    if unique_count < 2:
        raise ValueError('Boundary requires at least two distinct vertices')
    if degree < 1 or degree > 3:
        raise ValueError('degree must be between 1 and 3')
    if closed and unique_count < 3:
        raise ValueError('Closed boundary requires at least three vertices')
    actual_degree = min(degree, unique_count - 1)
    if closed:
        curve = cmds.curve(point=positions[:-1], degree=actual_degree, periodic=False, name=name)
        cmds.closeCurve(curve, constructionHistory=False, replaceOriginal=True, preserveShape=0)
    else:
        curve = cmds.curve(point=positions, degree=actual_degree, name=name)
    if spans is not None:
        if spans < 1:
            raise ValueError('spans must be positive')
        cmds.rebuildCurve(
            curve, constructionHistory=False, replaceOriginal=True,
            rebuildType=0, endKnots=1, keepRange=0,
            keepControlPoints=False, keepEndPoints=not closed,
            spans=spans, degree=actual_degree,
        )
    if closed:
        if direction != "preserve":
            raise ValueError("Closed boundaries require direction='preserve'.")
        if reverse:
            from Workshop.nurbs.curve import reverse_curve
            reverse_curve(curve)
    else:
        # Auto-orient first; reverse=True flips the resulting direction.
        orient_curve(curve, direction=direction, axis=direction_axis, reverse=reverse)
    if parent:
        curve = cmds.parent(curve, parent)[0]
    return curve
