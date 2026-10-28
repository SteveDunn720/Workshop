"""Generate a surface-conforming ribbon mesh from a winding curve.

Workshop.modeling_tools.wrap_generator
Maya Python API 2.0. Input mesh should be the same mesh used for the path.
"""
from __future__ import annotations

import maya.api.OpenMaya as om
import maya.cmds as cmds

from Workshop.poly.meshes import get_mesh_shape, get_selected_mesh
from Workshop.nurbs.curve import get_curve_shape
from Workshop.modeling_tools.surface_helix import generate_surface_helix


def _dag(node: str) -> om.MDagPath:
    selection = om.MSelectionList()
    selection.add(node)
    return selection.getDagPath(0)


def _safe_normal(vector: om.MVector, fallback: om.MVector) -> om.MVector:
    return vector.normal() if vector.length() > 1e-9 else fallback.normal()


def create_wrap_mesh(
    mesh: str,
    curve: str,
    width: float = 1.0,
    length_segments: int = 240,
    width_segments: int = 6,
    surface_offset: float = 0.025,
    name: str = 'surface_wrap_geo',
) -> str:
    """Make an open quad ribbon oriented to the target mesh normals.

    Each ribbon vertex is projected onto the nearest surface location.
    Very wide ribbons or tight folds may still overlap or jump to other
    nearby surfaces; this is a static mesh, not a cloth simulation.
    """
    if width <= 0 or length_segments < 2 or width_segments < 1:
        raise ValueError('width > 0, length_segments >= 2, width_segments >= 1 required')

    mesh_fn = om.MFnMesh(_dag(get_mesh_shape(mesh)))
    curve_fn = om.MFnNurbsCurve(_dag(get_curve_shape(curve)))
    start, end = curve_fn.knotDomain
    vertices = []
    previous_width = None

    for i in range(length_segments + 1):
        parameter = start + (end - start) * i / length_segments
        center = curve_fn.getPointAtParam(parameter, om.MSpace.kWorld)
        tangent = _safe_normal(
            curve_fn.tangent(parameter, om.MSpace.kWorld),
            om.MVector(0, 1, 0),
        )
        hit, normal, _ = mesh_fn.getClosestPointAndNormal(center, om.MSpace.kWorld)
        normal = _safe_normal(normal, om.MVector(0, 0, 1))
        # Width lies in the mesh tangent plane, perpendicular to the path.
        width_axis = _safe_normal(normal ^ tangent, om.MVector(1, 0, 0))
        if previous_width is not None and width_axis * previous_width < 0:
            width_axis *= -1
        previous_width = width_axis

        for j in range(width_segments + 1):
            across = (j / width_segments - 0.5) * width
            guess = om.MPoint(hit + width_axis * across)
            projected, projected_normal, _ = mesh_fn.getClosestPointAndNormal(
                guess, om.MSpace.kWorld
            )
            projected_normal = _safe_normal(projected_normal, normal)
            position = projected + projected_normal * surface_offset
            vertices.append(om.MPoint(position))

    stride = width_segments + 1
    polygon_counts = []
    polygon_connects = []
    for i in range(length_segments):
        for j in range(width_segments):
            a = i * stride + j
            b = a + 1
            c = b + stride
            d = a + stride
            polygon_counts.append(4)
            polygon_connects.extend((a, b, c, d))

    transform = cmds.createNode('transform', name=name)
    try:
        parent_obj = _dag(transform).node()
        created = om.MFnMesh().create(
            vertices, polygon_counts, polygon_connects, parent=parent_obj
        )
        shape_name = om.MFnDagNode(created).fullPathName()
        cmds.rename(shape_name, f'{transform}Shape')
        cmds.polySoftEdge(transform, angle=180, constructionHistory=False)
    except Exception:
        cmds.delete(transform)
        raise
    return transform


def generate_surface_wrap(
    mesh: str | None = None,
    curve: str | None = None,
    mode: str = 'wandering',
    turns: float = 5.0,
    randomness: float = 0.3,
    backtrack: float = 0.2,
    seed: int | None = None,
    start_angle: float = 0.0,
    width: float = 1.0,
    length_segments: int = 240,
    width_segments: int = 6,
    surface_offset: float = 0.025,
    name: str = 'surface_wrap_geo',
    keep_curve: bool = True,
) -> tuple[str, str | None]:
    """Generate a helix if necessary, then create a fitted ribbon mesh.

    Returns (mesh_transform, curve_transform_or_None).
    """
    mesh = mesh or get_selected_mesh()
    if not mesh:
        raise ValueError('Provide a polygon mesh or select one.')
    generated_curve = curve is None
    if generated_curve:
        curve = generate_surface_helix(
            mesh=mesh,
            mode=mode,
            turns=turns,
            samples=max(length_segments + 1, 150),
            randomness=randomness,
            backtrack=backtrack,
            surface_offset=surface_offset,
            seed=seed,
            start_angle=start_angle,
        )
    try:
        wrap = create_wrap_mesh(
            mesh=mesh,
            curve=curve,
            width=width,
            length_segments=length_segments,
            width_segments=width_segments,
            surface_offset=surface_offset,
            name=name,
        )
    except Exception:
        if generated_curve and cmds.objExists(curve):
            cmds.delete(curve)
        raise
    if generated_curve and not keep_curve:
        cmds.delete(curve)
        curve = None
    return wrap, curve
