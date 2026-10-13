"""Grounded foot-roll guide placement, before the leg flip group's final scaleX."""
from __future__ import annotations

from math import hypot
from maya import cmds
from Workshop.guide.core import create_guide_from_position
from Workshop.transform.utils import clean_parent


def _pos(node):
    return tuple(cmds.xform(node, q=True, ws=True, t=True))


def _distance_xz(a, b):
    return hypot(a[0] - b[0], a[2] - b[2])


def _create(name, world_position, parent, local_translation=None):
    if cmds.objExists(name):
        raise RuntimeError(f'Foot-roll guide already exists: {name}')
    info = create_guide_from_position(
        pos=world_position, guide_name=name.removesuffix('_guide')
    )
    node = info.name
    # World-aligned orientation before parenting. clean_parent preserves it.
    cmds.setAttr(f'{node}.jointOrient', 0, 0, 0, type='double3')
    cmds.xform(node, ws=True, rotation=(0, 0, 0))
    clean_parent(transform=node, parent=parent, joint_orient=True)
    if local_translation is not None:
        # Offsets are defined in the foot-roll parent's local XYZ frame.
        cmds.setAttr(f'{node}.jointOrient', 0, 0, 0, type='double3')
        cmds.setAttr(f'{node}.rotate', 0, 0, 0, type='double3')
        cmds.setAttr(f'{node}.translate', *local_translation, type='double3')
    return node


def build_foot_roll_guides(
    side: str,
    *,
    heel_position,
    toeball_position,
    bankout_position,
    bankin_position,
) -> dict[str, str]:
    """Build under an existing foot guide in the unflipped staging space.

    For an asymmetric target side, the caller must supply reflected X positions.
    For a symmetric target side, pass the source side's region positions unchanged.
    The enclosing leg flip group handles the final geometric mirror.
    """
    foot = f'foot_{side}_guide'
    toe_ee = f'toe_ee_{side}_guide'
    if not cmds.objExists(foot) or not cmds.objExists(toe_ee):
        raise RuntimeError(f'Foot-roll needs {foot} and {toe_ee} already built')

    foot_pos = _pos(foot)
    root_pos = (foot_pos[0], 0.0, foot_pos[2])
    root = _create(f'footroll_root_{side}_guide', root_pos, foot)
    cmds.setAttr(f'{root}.radius', 5.0)
    cmds.setAttr(f'{root}.drawStyle', 3)

    heel = _create(
        f'heel_{side}_guide', root_pos, root,
        (0, 0, -_distance_xz(root_pos, heel_position)),
    )
    ball = _create(
        f'toeball_ground_{side}_guide', root_pos, root,
        (0, 0, _distance_xz(root_pos, toeball_position)),
    )
    tip = _create(
        f'toetip_ground_{side}_guide', _pos(ball), ball,
        (0, 0, _distance_xz(toeball_position, _pos(toe_ee))),
    )
    bank_distance = (
        _distance_xz(toeball_position, bankout_position)
        + _distance_xz(toeball_position, bankin_position)
    ) / 2.0
    bankout = _create(
        f'bankout_{side}_guide', _pos(ball), ball, (bank_distance, 0, 0),
    )
    bankin = _create(
        f'bankin_{side}_guide', _pos(ball), ball, (-bank_distance, 0, 0),
    )
    return dict(root=root, heel=heel, ball=ball, tip=tip,
                bankout=bankout, bankin=bankin)
