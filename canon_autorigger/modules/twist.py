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
    invert:bool=False,
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

    mod =  1 #-1 if invert == True else

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
            dont_mirror=True
        )

        cmds.setAttr(
            f"{twist_joint}.translate{primary_axis}",
            bone_length * position * mod,
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
    cst_parent: str,
    twist_joints: list[str],
    primary_axis: str = "Y",
):
    """
    Drive a deformation twist segment from a switch-joint segment.

    Rotation:
        Each twist joint receives a percentage of the end driver's
        local primary-axis rotation.

    Translation:
        Each twist joint receives the same percentage of the end driver's
        change from its rest translation.

        All XYZ translation axes are tracked.

        On the primary axis, compression is clamped so that a twist joint
        cannot move closer to the segment root than its original/rest
        position.

        This clamp is sign-aware, so it works with both positive and
        negative primary-axis limb lengths.
    """

    if not twist_joints:
        return

    primary_axis = _validate_axis(primary_axis)

    # ---------------------------------------------------------
    # Start / end deformation joints
    # ---------------------------------------------------------

    constraint(
        drivers=[start_driver],
        driven=start_joint,
        maintain_offset=True,
        parent=cst_parent,
    )

    constraint(
        drivers=[end_driver],
        driven=end_joint,
        maintain_offset=True,
        parent=cst_parent,
    )

    # ---------------------------------------------------------
    # Twist source
    # ---------------------------------------------------------

    twist_source = f"{end_driver}.rotate{primary_axis}"

    # ---------------------------------------------------------
    # Capture end-driver rest translation
    # ---------------------------------------------------------

    end_rest_translate = {
        axis: cmds.getAttr(f"{end_driver}.translate{axis}")
        for axis in "XYZ"
    }

    count = len(twist_joints)

    for i, twist_joint in enumerate(twist_joints):

        # Example:
        #
        # start     twist01     twist02      end
        #  0%         33%         66%        100%
        #
        weight = (i + 1) / (count + 1)

        # =====================================================
        # ROTATION
        # =====================================================

        twist_mult = cmds.createNode(
            "multDoubleLinear",
            name=f"{twist_joint}_twist_mult",
        )

        cmds.connectAttr(
            twist_source,
            f"{twist_mult}.input1",
            force=True,
        )

        cmds.setAttr(
            f"{twist_mult}.input2",
            weight,
        )

        cmds.connectAttr(
            f"{twist_mult}.output",
            f"{twist_joint}.rotate{primary_axis}",
            force=True,
        )

        # =====================================================
        # TRANSLATION
        # =====================================================

        for axis in "XYZ":

            end_attr = f"{end_driver}.translate{axis}"
            twist_attr = f"{twist_joint}.translate{axis}"

            rest_end = end_rest_translate[axis]
            rest_twist = cmds.getAttr(twist_attr)

            # -------------------------------------------------
            # End translation delta
            #
            # currentEnd - restEnd
            # -------------------------------------------------

            delta = cmds.createNode(
                "plusMinusAverage",
                name=f"{twist_joint}_translate{axis}_delta",
            )

            cmds.setAttr(
                f"{delta}.operation",
                2,  # subtract
            )

            cmds.connectAttr(
                end_attr,
                f"{delta}.input1D[0]",
                force=True,
            )

            cmds.setAttr(
                f"{delta}.input1D[1]",
                rest_end,
            )

            # -------------------------------------------------
            # Weighted translation delta
            #
            # delta * twist percentage
            # -------------------------------------------------

            translate_mult = cmds.createNode(
                "multDoubleLinear",
                name=f"{twist_joint}_translate{axis}_mult",
            )

            cmds.connectAttr(
                f"{delta}.output1D",
                f"{translate_mult}.input1",
                force=True,
            )

            cmds.setAttr(
                f"{translate_mult}.input2",
                weight,
            )

            # -------------------------------------------------
            # Add rest position back
            #
            # restTwist + weightedDelta
            # -------------------------------------------------

            result = cmds.createNode(
                "addDoubleLinear",
                name=f"{twist_joint}_translate{axis}_add",
            )

            cmds.setAttr(
                f"{result}.input1",
                rest_twist,
            )

            cmds.connectAttr(
                f"{translate_mult}.output",
                f"{result}.input2",
                force=True,
            )

            # =================================================
            # PRIMARY AXIS COMPRESSION CLAMP
            # =================================================

            if axis == primary_axis:

                # ---------------------------------------------
                # Positive limb
                #
                # rest = +5
                #
                # Allowed:
                #     5, 6, 7, 8...
                #
                # Blocked:
                #     4, 3, 2...
                # ---------------------------------------------

                if rest_twist >= 0.0:

                    clamp = cmds.createNode(
                        "clamp",
                        name=f"{twist_joint}_translate{axis}_clamp",
                    )

                    cmds.setAttr(
                        f"{clamp}.minR",
                        weight,
                    )

                    cmds.setAttr(
                        f"{clamp}.maxR",
                        1000000.0,
                    )

                    cmds.connectAttr(
                        f"{result}.output",
                        f"{clamp}.inputR",
                        force=True,
                    )

                    cmds.connectAttr(
                        f"{clamp}.outputR",
                        twist_attr,
                        force=True,
                    )

                # ---------------------------------------------
                # Negative limb
                #
                # rest = -5
                #
                # Allowed:
                #     -5, -6, -7, -8...
                #
                # Blocked:
                #     -4, -3, -2...
                #
                # Therefore the rest position is our MAX,
                # rather than our MIN.
                # ---------------------------------------------

                else:

                    clamp = cmds.createNode(
                        "clamp",
                        name=f"{twist_joint}_translate{axis}_clamp",
                    )

                    cmds.setAttr(
                        f"{clamp}.minR",
                        -1000000.0,
                    )

                    cmds.setAttr(
                        f"{clamp}.maxR",
                        weight,
                    )

                    cmds.connectAttr(
                        f"{result}.output",
                        f"{clamp}.inputR",
                        force=True,
                    )

                    cmds.connectAttr(
                        f"{clamp}.outputR",
                        twist_attr,
                        force=True,
                    )

            # =================================================
            # SECONDARY AXES
            # =================================================

            else:

                cmds.connectAttr(
                    f"{result}.output",
                    twist_attr,
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
    invert:bool=False
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
        invert=invert,
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
        maintainOffset=True,
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
        maintainOffset=True,
        aimVector=aim_vector,
        upVector=(1, 0, 0),
        worldUpType="objectrotation",
        worldUpObject=start_driver,
        worldUpVector=(1, 0, 0),
    )

    return swing