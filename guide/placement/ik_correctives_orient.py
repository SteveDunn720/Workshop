"""Orient IK corrective guides toward their insert guides in Maya.

Each insert becomes the parent of its associated corrective guides after
orientation. All world-space positions are preserved.
"""
from __future__ import annotations

from maya import cmds


def orient_ik_correctives(
    insert: str,
    guides: list[str],
    *,
    aim_axis: tuple[float, float, float] = (0.0, 1.0, 0.0),
    up_axis: tuple[float, float, float] = (1.0, 0.0, 0.0),
    forward: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> None:
    """Aim each guide's local +Y at insert, local +X toward world +Z.

    Temporarily parents insert below the guide for joint orientation, then
    restores the original hierarchy and reparents guides below insert.
    """
    from Workshop.transform.utils import clean_parent

    if not cmds.objExists(insert):
        raise RuntimeError(f"Missing corrective insert: {insert}")

    original_parent = (cmds.listRelatives(insert, parent=True, fullPath=True) or [None])[0]
    insert_world = cmds.xform(insert, query=True, worldSpace=True, matrix=True)

    for guide in guides:
        if not cmds.objExists(guide):
            raise RuntimeError(f"Missing corrective guide: {guide}")
        guide_pos = cmds.xform(guide, query=True, worldSpace=True, translation=True)
        insert_pos = cmds.xform(insert, query=True, worldSpace=True, translation=True)
        if sum((a - b) ** 2 for a, b in zip(guide_pos, insert_pos)) < 1e-10:
            raise ValueError(f"{guide} and {insert} share a position; cannot aim")

        # Remove the guide from any existing insert hierarchy before aiming.
        if cmds.listRelatives(guide, parent=True):
            cmds.parent(guide, world=True, absolute=True)
        clean_parent(transform=insert, parent=guide, joint_orient=True)
        try:
            constraint = cmds.aimConstraint(
                insert, guide,
                aimVector=aim_axis,
                upVector=up_axis,
                worldUpType='vector',
                worldUpVector=forward,
                maintainOffset=False,
            )[0]
            cmds.delete(constraint)
            # Store solved orientation in jointOrient instead of rotate.
            if cmds.nodeType(guide) == 'joint':
                cmds.makeIdentity(guide, apply=True, rotate=True)
        finally:
            if original_parent and cmds.objExists(original_parent):
                clean_parent(transform=insert, parent=original_parent, joint_orient=True)
            else:
                cmds.parent(insert, world=True, absolute=True)
            cmds.xform(insert, worldSpace=True, matrix=insert_world)

    # Final hierarchy: insert owns the corrective guides.
    for guide in guides:
        clean_parent(transform=guide, parent=insert, joint_orient=True)
