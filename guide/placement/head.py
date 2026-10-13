"""Procedural head guide placement for Workshop."""
from maya import cmds


def head_guide_positions(root_position, end_position, start=0.10, stop=0.50,
                         forward_fraction=0.10):
    """Return four evenly spaced positions, with world +Z as forward."""
    height = abs(end_position[1] - root_position[1])
    if height < 1e-6:
        raise ValueError('Head root and head end must have different Y positions')
    names = ('lower_head_M_guide', 'mid_head_M_guide',
             'upper_head_M_guide', 'top_head_M_guide')
    result = {}
    for i, name in enumerate(names):
        t = start + (stop - start) * i / (len(names) - 1)
        result[name] = tuple(
            root_position[axis] + (end_position[axis] - root_position[axis]) * t
            + (height * forward_fraction if axis == 2 else 0.0)
            for axis in range(3)
        )
    return result


def style_head_guides(guides, radius=2.5):
    for guide in guides:
        if cmds.objExists(guide) and cmds.nodeType(guide) == 'joint':
            cmds.setAttr(f'{guide}.radius', radius)
            cmds.setAttr(f'{guide}.drawStyle', 3)
