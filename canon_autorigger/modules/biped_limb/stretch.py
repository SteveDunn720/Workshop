
import maya.cmds as cmds

from Workshop.maya_api.node import (
    DistanceBetweenNode,
    MultiplyDivideNode,
)


def build_stretchy_ik(
    name: str,
    root_reference: str,
    ik_control: str,
    upper_joint: str,
    lower_joint: str,
    end_joint: str,
    stretch_attr: str = "stretch",
    drive_length_joint: bool = False,
    len_joint: str = "",
    down_axis: str = "Y",
    soft_range: float = 0.05,
):
    """
    Stretchy IK with an animator-controlled maximum-length limit.

    stretch = 0.0 : no extension
    stretch = 0.2 : maximum 1.2x original length
    stretch = 1.0 : unrestricted stretch

    The limit is a hard cap (no soft ramp), avoiding knee re-bending.
    soft_range is retained for API compatibility but no longer used.
    """

    if not cmds.attributeQuery(
        stretch_attr, node=ik_control, exists=True
    ):
        cmds.addAttr(
            ik_control,
            longName=stretch_attr,
            attributeType="double",
            minValue=0.0,
            maxValue=1.0,
            defaultValue=0.1,
            keyable=True,
        )

    stretch_plug = f"{ik_control}.{stretch_attr}"

    upper_length = cmds.getAttr(
        f"{lower_joint}.translate{down_axis}"
    )
    lower_length = cmds.getAttr(
        f"{end_joint}.translate{down_axis}"
    )

    original_length = abs(upper_length) + abs(lower_length)

    if original_length <= 0:
        raise ValueError("Original IK length must be positive.")

    # -------------------------------------------------
    # Helpers for native Maya utility nodes
    # -------------------------------------------------

    def md(suffix, operation, input1, input2):
        node = cmds.createNode(
            "multiplyDivide",
            name=f"{name}_{suffix}",
        )
        cmds.setAttr(f"{node}.operation", operation)

        for attr, value in [
            ("input1X", input1),
            ("input2X", input2),
        ]:
            plug = f"{node}.{attr}"
            if isinstance(value, str):
                cmds.connectAttr(value, plug, force=True)
            else:
                cmds.setAttr(plug, value)

        return f"{node}.outputX"

    def subtract(suffix, a, b):
        node = cmds.createNode(
            "plusMinusAverage",
            name=f"{name}_{suffix}",
        )
        cmds.setAttr(f"{node}.operation", 2)

        for i, value in enumerate((a, b)):
            plug = f"{node}.input1D[{i}]"
            if isinstance(value, str):
                cmds.connectAttr(value, plug, force=True)
            else:
                cmds.setAttr(plug, value)

        return f"{node}.output1D"

    def condition(suffix, first, second, true, false):
        node = cmds.createNode(
            "condition",
            name=f"{name}_{suffix}",
        )
        cmds.setAttr(f"{node}.operation", 2)  # greater than

        values = {
            "firstTerm": first,
            "secondTerm": second,
            "colorIfTrueR": true,
            "colorIfFalseR": false,
        }

        for attr, value in values.items():
            plug = f"{node}.{attr}"
            if isinstance(value, str):
                cmds.connectAttr(value, plug, force=True)
            else:
                cmds.setAttr(plug, value)

        return f"{node}.outColorR"

    # -------------------------------------------------
    # Distance and raw stretch ratio
    # -------------------------------------------------

    distance = DistanceBetweenNode.create(
        name=f"{name}_stretch_distance"
    )

    distance.input_matrix1.connect_from(
        f"{root_reference}.worldMatrix[0]"
    )
    distance.input_matrix2.connect_from(
        f"{ik_control}.worldMatrix[0]"
    )

    ratio = MultiplyDivideNode.create(
        name=f"{name}_stretch_ratio"
    )
    ratio.operation.set(2)
    ratio.input1.x.connect_from(distance.distance)
    ratio.input2.x.set(original_length)

    raw_ratio = f"{ratio}.outputX"

    # Do not allow the limb to compress.
    extension_ratio = condition(
        "non_compress",
        raw_ratio, 1.0,
        raw_ratio, 1.0,
    )

    # -------------------------------------------------
    # Maximum ratio from the stretch slider
    #
    # cap = 1 + 0.8 * stretch / (1 - stretch)
    #
    # At stretch=1, the separate full-stretch
    # condition below bypasses the cap.
    # -------------------------------------------------

    remaining = subtract(
        "stretch_remaining",
        1.0,
        stretch_plug,
    )

    safe_remaining = condition(
        "safe_remaining",
        remaining,
        0.0001,
        remaining,
        0.0001,
    )

    scaled_stretch = md(
        "stretch_scaled",
        1,
        stretch_plug,
        0.8,
    )

    extension_limit = md(
        "extension_limit",
        2,
        scaled_stretch,
        safe_remaining,
    )

    cap_node = cmds.createNode(
        "plusMinusAverage",
        name=f"{name}_stretch_cap",
    )
    cmds.setAttr(f"{cap_node}.input1D[0]", 1.0)
    cmds.connectAttr(
        extension_limit,
        f"{cap_node}.input1D[1]",
    )
    cap = f"{cap_node}.output1D"

    # -------------------------------------------------
    # Maximum stretch, without the soft-stretch overshoot.
    # -------------------------------------------------
    # The previous remap made the segments longer than the ankle reach
    # near the cap, causing a knee re-bend / pop.  Use the actual
    # extension ratio all the way to the cap instead.
    limited_ratio = condition(
        "stretch_cutoff",
        extension_ratio,
        cap,
        cap,
        extension_ratio,
    )

    # At stretch=1, bypass the limiter entirely.
    final_ratio = condition(
        "full_stretch",
        stretch_plug,
        0.999999,
        extension_ratio,
        limited_ratio,
    )

    # -------------------------------------------------
    # Drive the joint lengths
    # -------------------------------------------------

    lengths = MultiplyDivideNode.create(
        name=f"{name}_stretch_lengths"
    )

    lengths.input1.x.set(upper_length)
    lengths.input1.y.set(lower_length)

    lengths.input2.x.connect_from(final_ratio)
    lengths.input2.y.connect_from(final_ratio)

    lengths.output.x.connect_to(
        f"{lower_joint}.translate{down_axis}"
    )
    lengths.output.y.connect_to(
        f"{end_joint}.translate{down_axis}"
    )

    # -------------------------------------------------
    # Optional length joint
    # -------------------------------------------------

    if drive_length_joint:
        if not len_joint:
            raise ValueError(
                "len_joint required when "
                "drive_length_joint=True"
            )

        # Preserve the original sign convention.
        sign = 1 if upper_length >= 0 else -1

        signed_distance = md(
            "signed_distance",
            1,
            f"{distance}.distance",
            sign,
        )

        # The length joint must respect the new cap.
        # Add the two stretched segment lengths.
        length_sum = cmds.createNode(
            "plusMinusAverage",
            name=f"{name}_limb_length_sum",
        )

        cmds.connectAttr(
            f"{lengths}.outputX",
            f"{length_sum}.input1D[0]",
        )
        cmds.connectAttr(
            f"{lengths}.outputY",
            f"{length_sum}.input1D[1]",
        )

        length_output = condition(
            "length_joint_selection",
            raw_ratio,
            1.0,
            f"{length_sum}.output1D",
            signed_distance,
        )

        cmds.connectAttr(
            length_output,
            f"{len_joint}.translate{down_axis}",
            force=True,
        )

    return final_ratio
