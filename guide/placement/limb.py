from __future__ import annotations

import maya.cmds as cmds
from maya.api import OpenMaya as om

from Workshop.transform.matrix import set_world_matrix


_AXIS_VECTORS = {
    "x": om.MVector(1, 0, 0),
    "y": om.MVector(0, 1, 0),
    "z": om.MVector(0, 0, 1),
    "-x": om.MVector(-1, 0, 0),
    "-y": om.MVector(0, -1, 0),
    "-z": om.MVector(0, 0, -1),
}


def _get_guide_position(guide: str) -> om.MVector:
    position = cmds.xform(
        guide,
        query=True,
        worldSpace=True,
        translation=True,
    )
    return om.MVector(*position)


def _get_limb_normal(
    positions: list[om.MVector],
    flip: bool = False,
) -> om.MVector:
    """Calculate the plane normal of a guide chain."""

    start = positions[0]
    middle = positions[len(positions) // 2]
    end = positions[-1]

    upper = middle - start
    lower = end - middle

    normal = upper ^ lower

    if normal.length() < 1e-8:
        raise RuntimeError(
            "Cannot calculate limb plane: guides are collinear."
        )

    normal.normalize()

    if flip:
        normal *= -1

    return normal


def _build_aim_matrix(
    position: om.MVector,
    direction: om.MVector,
    up_vector: om.MVector,
    aim_axis: str = "y",
    up_axis: str = "z",
) -> om.MMatrix:
    """
    Build an orthonormal world matrix using configurable
    local aim and up axes.
    """

    if aim_axis not in _AXIS_VECTORS:
        raise ValueError(f"Invalid aim axis: {aim_axis}")

    if up_axis not in _AXIS_VECTORS:
        raise ValueError(f"Invalid up axis: {up_axis}")

    local_aim = _AXIS_VECTORS[aim_axis]
    local_up = _AXIS_VECTORS[up_axis]

    if abs(local_aim * local_up) > 0.999:
        raise ValueError(
            "Aim and up axes must be different axes."
        )

    aim = om.MVector(direction)
    aim.normalize()

    # Remove any component of the up vector along aim.
    up = up_vector - aim * (up_vector * aim)

    if up.length() < 1e-8:
        raise RuntimeError(
            "Up vector is parallel to aim direction."
        )

    up.normalize()

    side = aim ^ up
    side.normalize()

    # Re-orthogonalize.
    up = side ^ aim
    up.normalize()

    # Map local axes to world axes.
    axis_map = {}

    for local, world in (
        (local_aim, aim),
        (local_up, up),
    ):
        for index, value in enumerate((local.x, local.y, local.z)):
            if abs(value) > 0.5:
                axis_map[index] = world * value
                break

    missing = ({0, 1, 2} - set(axis_map)).pop()

    # Complete the right-handed coordinate frame.
    if missing == 0:
        axis_map[0] = axis_map[1] ^ axis_map[2]
    elif missing == 1:
        axis_map[1] = axis_map[2] ^ axis_map[0]
    else:
        axis_map[2] = axis_map[0] ^ axis_map[1]

    x = axis_map[0]
    y = axis_map[1]
    z = axis_map[2]

    return om.MMatrix([
        x.x, x.y, x.z, 0,
        y.x, y.y, y.z, 0,
        z.x, z.y, z.z, 0,
        position.x, position.y, position.z, 1,
    ])


def orient_limb_guides(
    guides: list[str],
    aim_axis: str = "y",
    up_axis: str = "z",
    flip_normal: bool = False,
    orient_end: bool = True,
) -> None:
    """
    Orient a chain of guides using its anatomical plane.

    Args:
        guides: Ordered guide names, root to tip.
        aim_axis: Local axis pointing toward the next guide.
        up_axis: Local axis aligned to the limb plane normal.
        flip_normal: Reverse the calculated plane normal.
        orient_end: Copy the final segment orientation
            onto the last guide.
    """

    if len(guides) == 2:
        orient_two_guides(
            guides=guides,
            aim_axis=aim_axis,
            up_axis=up_axis,
        )
        return

    if len(guides) < 2:
        raise ValueError(
            "Limb orientation requires at least two guides."
        )

    for guide in guides:
        if not cmds.objExists(guide):
            raise RuntimeError(
                f"Guide does not exist: {guide}"
            )

    positions = [
        _get_guide_position(guide)
        for guide in guides
    ]

    normal = _get_limb_normal(
        positions=positions,
        flip=flip_normal,
    )

    matrices = []

    for index in range(len(guides) - 1):

        direction = positions[index + 1] - positions[index]

        if direction.length() < 1e-8:
            raise RuntimeError(
                f"Coincident guides: "
                f"{guides[index]}, {guides[index + 1]}"
            )

        matrix = _build_aim_matrix(
            position=positions[index],
            direction=direction,
            up_vector=normal,
            aim_axis=aim_axis,
            up_axis=up_axis,
        )

        matrices.append(matrix)

    # Calculate all matrices before changing any guides.
    for guide, matrix in zip(guides[:-1], matrices):
        set_world_matrix(
            transform=guide,
            matrix=matrix,
            use_joint_orient=True,
        )

    if orient_end:
        end_matrix = om.MMatrix(matrices[-1])

        end_position = positions[-1]

        for index, value in enumerate(
            (end_position.x, end_position.y, end_position.z)
        ):
            end_matrix.setElement(3, index, value)

        set_world_matrix(
            transform=guides[-1],
            matrix=end_matrix,
            use_joint_orient=True,
        )


import maya.cmds as cmds


def orient_two_guides(
    guides: list[str],
    aim_axis: str = "y",
    up_axis: str = "x",
    world_up: tuple[float, float, float] = (0, 0, 1),
):
    """
    Orient the first guide toward the second guide.

    The second guide is left unchanged, allowing it to be
    oriented separately by another chain.
    """

    start, end = guides

    constraint = cmds.aimConstraint(
        end,
        start,
        aimVector=_axis_vector(aim_axis),
        upVector=_axis_vector(up_axis),
        worldUpType="vector",
        worldUpVector=world_up,
        maintainOffset=False,
    )[0]

    cmds.delete(constraint)


def _axis_vector(axis: str):
    vectors = {
        "x": (1, 0, 0),
        "y": (0, 1, 0),
        "z": (0, 0, 1),
        "-x": (-1, 0, 0),
        "-y": (0, -1, 0),
        "-z": (0, 0, -1),
    }
    return vectors[axis.lower()]