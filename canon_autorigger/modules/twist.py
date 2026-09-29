from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.joint import create_joint
from Workshop.skin.split.tag import tag_for_weight_split
from Workshop.transform.constraint import constraint


@dataclass
class TwistData:
    start_driver: str
    end_driver: str
    start_joint: str
    end_joint: str
    twist_joints: list[str]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _validate_axis(primary_axis: str) -> str:
    """
    Validate and normalize a primary axis.
    """

    primary_axis = primary_axis.upper()

    if primary_axis not in {"X", "Y", "Z"}:
        raise ValueError(
            f"Invalid primary_axis: {primary_axis}. "
            "Expected X, Y, or Z."
        )

    return primary_axis


def _get_other_axes(primary_axis: str) -> tuple[str, str]:
    """
    Return the two non-primary rotation axes.
    """

    axes = ["X", "Y", "Z"]
    axes.remove(primary_axis)

    return axes[0], axes[1]


# ----------------------------------------------------------------------
# Joint Creation
# ----------------------------------------------------------------------

def create_twist_joints(
    start_joint: str,
    end_joint: str,
    twist_count: int = 2,
    primary_axis: str = "Y",
) -> list[str]:
    """
    Create twist joints between two existing deformation joints.

    Twist joints are parented beneath the start deformation joint and
    distributed evenly along the segment.

    The end joint itself represents 100% of the segment, so generated
    twist joints do not occupy the endpoint.
    """

    if twist_count < 1:
        raise ValueError("twist_count must be at least 1.")

    primary_axis = _validate_axis(primary_axis)

    bone_length = cmds.getAttr(
        f"{end_joint}.translate{primary_axis}"
    )

    descriptor = start_joint.removesuffix("_jnt")

    twist_joints = []

    for i in range(twist_count):

        # Example with two twist joints:
        #
        # start     twist01     twist02     end
        #   0%        33%         66%       100%
        #
        position = (i + 1) / (twist_count + 1)

        twist_joint = create_joint(
            name=f"{descriptor}_twist_{i + 1:02d}",
            transform=start_joint,
            parent=start_joint,
            connect=False,
            bind_set=True,
            ue_set=True,
        )

        cmds.setAttr(
            f"{twist_joint}.translate{primary_axis}",
            bone_length * position,
        )

        twist_joints.append(twist_joint)

    return twist_joints


# ----------------------------------------------------------------------
# Weight Split
# ----------------------------------------------------------------------

def setup_twist_tag(
    start_joint: str,
    twist_joints: list[str],
):
    """
    Set up weight splitting for a twist segment.
    """

    if not twist_joints:
        return

    if len(twist_joints) == 1:
        split_influences = [
            start_joint,
            twist_joints[0],
            twist_joints[0],
        ]

    else:
        split_influences = [
            start_joint,
            *twist_joints,
        ]

    tag_for_weight_split(
        influence=start_joint,
        split_influences=split_influences,
    )


# ----------------------------------------------------------------------
# Driving
# ----------------------------------------------------------------------

def drive_twist_joints(
    start_driver: str,
    end_driver: str,
    start_joint: str,
    end_joint: str,
    cst_parent:str,
    twist_joints: list[str],
    primary_axis: str = "Y",
):
    """
    Drive a deformation twist segment from a switch-joint segment.

    The switch joints are the authoritative input.

    The start bind joint follows the start driver normally.

    The generated twist joints inherit the start bind joint's transform,
    then progressively receive the relative axial rotation between the
    start and end switch joints.

    The end bind joint continues to be driven by the end switch joint.

    This intentionally handles TWIST ONLY. Bendy/swing interpolation can
    be layered on top later.
    """

    if not twist_joints:
        return

    primary_axis = _validate_axis(primary_axis)

    # ---------------------------------------------------------
    # Start / end deformation joints
    # ---------------------------------------------------------
    #
    # These should follow their corresponding switch joints.
    #
    # If your limb already creates these constraints, REMOVE these
    # two constraints from here OR from the limb. Do not build both.
    # ---------------------------------------------------------

    """start_constraint = cmds.parentConstraint(
        start_driver,
        start_joint,
        maintainOffset=False,
        name=f"{start_joint}_switch_parentConstraint",
    )[0]"""

    constraint(drivers=[start_driver], driven=start_joint, maintain_offset=False, parent=cst_parent)
    constraint(drivers=[end_driver], driven=end_joint, maintain_offset=False, parent=cst_parent)

    """end_constraint = cmds.parentConstraint(
        end_driver,
        end_joint,
        maintainOffset=False,
        name=f"{end_joint}_switch_parentConstraint",
    )[0]"""

    # ---------------------------------------------------------
    # Relative rotation
    # ---------------------------------------------------------
    #
    # end_driver is a child of start_driver in the switch chain.
    #
    # Therefore:
    #
    #     end_driver.rotate<axis>
    #
    # already represents the end's local rotation relative to
    # the start driver.
    #
    # We only use the primary axis here so knee/elbow bending
    # doesn't contaminate twist.
    # ---------------------------------------------------------

    twist_source = f"{end_driver}.rotate{primary_axis}"

    count = len(twist_joints)

    for i, twist_joint in enumerate(twist_joints):

        # -----------------------------------------------------
        # Rotation percentage
        # -----------------------------------------------------
        #
        # start     twist01     twist02     end
        #   0%        33%         66%       100%
        #
        weight = (i + 1) / (count + 1)

        mult = cmds.createNode(
            "multDoubleLinear",
            name=f"{twist_joint}_twist_mult",
        )

        cmds.connectAttr(
            twist_source,
            f"{mult}.input1",
            force=True,
        )

        cmds.setAttr(
            f"{mult}.input2",
            weight,
        )

        cmds.connectAttr(
            f"{mult}.output",
            f"{twist_joint}.rotate{primary_axis}",
            force=True,
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def create_twist(
    start_driver: str,
    end_driver: str,
    start_joint: str,
    end_joint: str,
    cst_parent:str,
    twist_count: int = 2,
    primary_axis: str = "Y",
) -> TwistData:
    """
    Create a twist deformation segment.

    Args:
        start_driver:
            Start switch/driver joint.

        end_driver:
            End switch/driver joint.

        start_joint:
            Existing start deformation/bind joint.

        end_joint:
            Existing end deformation/bind joint.

        twist_count:
            Number of intermediate twist joints.

        primary_axis:
            Local bone/twist axis.

    Returns:
        TwistData
    """

    primary_axis = _validate_axis(primary_axis)

    twist_joints = create_twist_joints(
        start_joint=start_joint,
        end_joint=end_joint,
        twist_count=twist_count,
        primary_axis=primary_axis,
    )

    setup_twist_tag(
        start_joint=start_joint,
        twist_joints=twist_joints,
    )

    drive_twist_joints(
        start_driver=start_driver,
        end_driver=end_driver,
        start_joint=start_joint,
        end_joint=end_joint,
        twist_joints=twist_joints,
        primary_axis=primary_axis,
        cst_parent=cst_parent
    )

    return TwistData(
        start_driver=start_driver,
        end_driver=end_driver,
        start_joint=start_joint,
        end_joint=end_joint,
        twist_joints=twist_joints,
    )

def create_swing_driver(
    start_driver: str,
    end_driver: str,
    parent: str,
    primary_axis: str = "Y",
) -> str:
    """
    Create a twist-free swing driver for a joint segment.

    The swing driver:
        - follows start_driver's position
        - aims its primary axis toward end_driver
        - does not inherit axial twist from start_driver
    """

    primary_axis = primary_axis.upper()

    if primary_axis not in {"X", "Y", "Z"}:
        raise ValueError(
            f"Invalid primary_axis: {primary_axis}. "
            "Expected X, Y, or Z."
        )

    descriptor = start_driver.removesuffix("_jnt")

    swing = cmds.createNode(
        "transform",
        name=f"{descriptor}_swing",
        parent=parent,
    )

    # Match the initial position/orientation.
    cmds.matchTransform(
        swing,
        start_driver,
        position=True,
        rotation=True,
    )

    # Follow the start of the segment.
    cmds.pointConstraint(
        start_driver,
        swing,
        maintainOffset=False,
    )

    # Aim primary axis down the segment.
    aim_vectors = {
        "X": (1, 0, 0),
        "Y": (0, 1, 0),
        "Z": (0, 0, 1),
    }

    aim_vector = aim_vectors[primary_axis]

    cmds.aimConstraint(
        end_driver,
        swing,
        maintainOffset=False,
        aimVector=aim_vector,
        upVector=(1, 0, 0),
        worldUpType="objectrotation",
        worldUpObject=start_driver,
        worldUpVector=(1, 0, 0),
    )

    return swing