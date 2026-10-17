"""Orient Maya corrective joints using the nearest mesh surface normal.

Primary axis aligns with the surface normal. Secondary axis aligns with the
projection of a configurable world-space reference vector onto the tangent
plane. Defaults: +Y normal, +X projected world +Z.
"""
from __future__ import annotations

from maya import cmds
from maya.api import OpenMaya as om


def _axis(axis: str) -> tuple[int, float]:
    axis = axis.upper().strip()
    if axis not in ('+X', '-X', '+Y', '-Y', '+Z', '-Z'):
        raise ValueError(f'Invalid axis {axis!r}; expected +X/-X/+Y/-Y/+Z/-Z')
    return 'XYZ'.index(axis[-1]), (-1.0 if axis[0] == '-' else 1.0)


def _closest_normal(mesh: str, position: tuple[float, float, float]) -> om.MVector:
    shapes = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True) or []
    shape = next((s for s in shapes if cmds.nodeType(s) == 'mesh'), None)
    if shape is None and cmds.nodeType(mesh) == 'mesh':
        shape = mesh
    if not shape:
        raise ValueError(f'Not a polygon mesh: {mesh}')
    node = cmds.createNode('closestPointOnMesh', name='correctiveSurfaceNormal_tmp#')
    try:
        cmds.connectAttr(f'{shape}.worldMesh[0]', f'{node}.inMesh', force=True)
        cmds.connectAttr(f'{shape}.worldMatrix[0]', f'{node}.inputMatrix', force=True)
        cmds.setAttr(f'{node}.inPosition', *position, type='double3')
        normal = cmds.getAttr(f'{node}.normal')[0]
        result = om.MVector(*normal)
        if result.length() < 1e-8:
            raise ValueError(f'No surface normal found for {mesh} at {position}')
        return result.normal()
    finally:
        cmds.delete(node)


def orient_surface_corrective(
    guide: str,
    mesh: str,
    *,
    primary_axis: str = '+Y',
    secondary_axis: str = '+X',
    secondary_reference: tuple[float, float, float] = (0.0, 0.0, 1.0),
    normal_direction: str = 'outward',
) -> None:
    """Orient a guide to its mesh normal, preserving its world position.

    `secondary_reference` is a world-space vector (not a second surface normal).
    For opposite directions use normal_direction='inward'.
    """
    primary_index, primary_sign = _axis(primary_axis)
    secondary_index, secondary_sign = _axis(secondary_axis)
    if primary_index == secondary_index:
        raise ValueError('Primary and secondary axes must use different letters')
    if normal_direction not in ('outward', 'inward'):
        raise ValueError('normal_direction must be outward or inward')

    pos = tuple(cmds.xform(guide, query=True, worldSpace=True, translation=True))
    normal = _closest_normal(mesh, pos)
    if normal_direction == 'inward':
        normal *= -1.0
    reference = om.MVector(*secondary_reference)
    tangent = reference - normal * (reference * normal)
    if tangent.length() < 1e-8:
        # Choose a stable fallback when the reference is parallel to the normal.
        candidates = (om.MVector(1, 0, 0), om.MVector(0, 1, 0), om.MVector(0, 0, 1))
        reference = min(candidates, key=lambda v: abs(v * normal))
        tangent = reference - normal * (reference * normal)
    tangent.normalize()

    axes: list[om.MVector | None] = [None, None, None]
    axes[primary_index] = normal * primary_sign
    axes[secondary_index] = tangent * secondary_sign
    missing = ({0, 1, 2} - {primary_index, secondary_index}).pop()
    # A right-handed basis always satisfies X cross Y = Z.
    if missing == 0:
        axes[0] = axes[1] ^ axes[2]
    elif missing == 1:
        axes[1] = axes[2] ^ axes[0]
    else:
        axes[2] = axes[0] ^ axes[1]
    x, y, z = axes
    matrix = (
        x.x, x.y, x.z, 0.0,
        y.x, y.y, y.z, 0.0,
        z.x, z.y, z.z, 0.0,
        pos[0], pos[1], pos[2], 1.0,
    )
    cmds.xform(guide, worldSpace=True, matrix=matrix)
    if cmds.nodeType(guide) == 'joint':
        cmds.makeIdentity(guide, apply=True, rotate=True)
