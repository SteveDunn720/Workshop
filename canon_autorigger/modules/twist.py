from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.control import create_control
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

    control: object | None = None


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
    Return the two non-primary axes.
    """

    axes = ["X", "Y", "Z"]
    axes.remove(primary_axis)

    return axes[0], axes[1]


def _get_twist_weight(
    index: int,
    count: int,
) -> float:
    """
    Return the normalized position of a twist joint along the segment.

    Example with two twist joints:

        start     twist01     twist02      end
         0.0       0.333       0.666       1.0
    """

    return (index + 1) / (count + 1)


def _get_control_weight(
    twist_weight: float,
) -> float:
    """
    Return the influence of the midpoint control.

    The influence peaks at the middle of the segment and falls to
    zero at either endpoint.

        position:
            0.0     0.25     0.5     0.75     1.0

        influence:
            0.0      0.5     1.0      0.5     0.0
    """

    return 1.0 - abs((twist_weight - 0.5) * 2.0)


def _get_control_transform(control) -> str | None:
    """
    Resolve either a Workshop Control object or a Maya transform name
    into the actual control transform.
    """

    if control is None:
        return None

    if isinstance(control, str):
        return control

    if hasattr(control, "ctrl"):
        return control.ctrl

    return None


# ----------------------------------------------------------------------
# Joint Creation
# ----------------------------------------------------------------------

def create_twist_joints(
    start_joint: str,
    end_joint: str,
    twist_count: int = 2,
    primary_axis: str = "Y",
    invert: bool = False,
) -> list[str]:
    """
    Create twist joints between two existing deformation joints.

    Twist joints are parented beneath the start deformation joint and
    distributed evenly along the segment.

    The end joint itself represents 100% of the segment, so generated
    twist joints do not occupy the endpoint.
    """

    if twist_count < 1:
        raise ValueError(
            "twist_count must be at least 1."
        )

    primary_axis = _validate_axis(primary_axis)

    bone_length = cmds.getAttr(
        f"{end_joint}.translate{primary_axis}"
    )

    # Keeping this matching your existing setup.
    mod = 1

    descriptor = start_joint.removesuffix("_jnt")

    twist_joints = []

    for i in range(twist_count):

        position = _get_twist_weight(
            index=i,
            count=twist_count,
        )

        twist_joint = create_joint(
            name=f"{descriptor}_twist_{i + 1:02d}",
            transform=start_joint,
            parent=start_joint,
            connect=False,
            bind_set=True,
            ue_set=True,
            dont_mirror=True,
        )

        cmds.setAttr(
            f"{twist_joint}.translate{primary_axis}",
            bone_length * position * mod,
        )

        twist_joints.append(
            twist_joint
        )

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
# Optional Mid Control
# ----------------------------------------------------------------------

def create_twist_control(
    start_joint: str,
    end_joint: str,
    primary_axis: str,
    control_parent: str | None = None,
    control_size: float = 1.0,
    control_shape:str = 'round_square'
):
    """
    Create a control at the midpoint of the twist segment.

    The control's top transform follows a 50/50 matrix blend between
    the start and end joints.

    This gives us:
        - midpoint translation
        - blended orientation
        - clean zeroed animator control underneath
    """

    primary_axis = _validate_axis(primary_axis)

    descriptor = start_joint.removesuffix("_jnt")

    # ---------------------------------------------------------
    # Temporary midpoint transform
    #
    # Only used to initially create/place the control.
    # ---------------------------------------------------------

    midpoint = cmds.createNode(
        "transform",
        name=f"{descriptor}_twist_mid_tmp",
    )

    cmds.matchTransform(
        midpoint,
        start_joint,
        position=True,
        rotation=True,
    )

    tmp_constraint = cmds.parentConstraint(
        start_joint,
        end_joint,
        midpoint,
        maintainOffset=False,
    )[0]

    cmds.delete(tmp_constraint)

    # ---------------------------------------------------------
    # Create control
    # ---------------------------------------------------------

    control = create_control(
        name=f"{descriptor}_twist",
        transform=midpoint,
        parent=control_parent,
        size=control_size,
        control_shape=control_shape,
        direction=primary_axis.lower(),
    )

    cmds.delete(midpoint)

    # ---------------------------------------------------------
    # 50/50 blended world matrix
    # ---------------------------------------------------------

    blend = cmds.createNode(
        "blendMatrix",
        name=f"{descriptor}_twist_mid_blendMatrix",
    )

    # Start is the base.
    cmds.connectAttr(
        f"{start_joint}.worldMatrix[0]",
        f"{blend}.inputMatrix",
        force=True,
    )

    # End is the target.
    cmds.connectAttr(
        f"{end_joint}.worldMatrix[0]",
        f"{blend}.target[0].targetMatrix",
        force=True,
    )

    cmds.setAttr(
        f"{blend}.target[0].weight",
        0.5,
    )

    cmds.setAttr(
        f"{blend}.target[0].translateWeight",
        1.0,
    )

    cmds.setAttr(
        f"{blend}.target[0].rotateWeight",
        1.0,
    )

    cmds.setAttr(
        f"{blend}.target[0].scaleWeight",
        0.0,
    )

    cmds.setAttr(
        f"{blend}.target[0].shearWeight",
        0.0,
    )

    # ---------------------------------------------------------
    # Convert world result into control.top's parent space
    # ---------------------------------------------------------

    local_mult = cmds.createNode(
        "multMatrix",
        name=f"{descriptor}_twist_mid_local_multMatrix",
    )

    cmds.connectAttr(
        f"{blend}.outputMatrix",
        f"{local_mult}.matrixIn[0]",
        force=True,
    )

    cmds.connectAttr(
        f"{control.top}.parentInverseMatrix[0]",
        f"{local_mult}.matrixIn[1]",
        force=True,
    )

    # ---------------------------------------------------------
    # Decompose into local translate / rotate
    # ---------------------------------------------------------

    decompose = cmds.createNode(
        "decomposeMatrix",
        name=f"{descriptor}_twist_mid_decomposeMatrix",
    )

    cmds.connectAttr(
        f"{local_mult}.matrixSum",
        f"{decompose}.inputMatrix",
        force=True,
    )

    # Make decomposition respect the control top's rotation order.
    cmds.connectAttr(
        f"{control.top}.rotateOrder",
        f"{decompose}.inputRotateOrder",
        force=True,
    )

    cmds.connectAttr(
        f"{decompose}.outputTranslate",
        f"{control.top}.translate",
        force=True,
    )

    cmds.connectAttr(
        f"{decompose}.outputRotate",
        f"{control.top}.rotate",
        force=True,
    )

    # ---------------------------------------------------------
    # Lock non-twist rotation axes
    # ---------------------------------------------------------

    for axis in "XYZ":

        attr = f"{control.ctrl}.scale{axis}"
        
        cmds.setAttr(
            attr,
            lock=True,
            keyable=False,
            channelBox=False,
        )

        if axis == primary_axis:
            continue

        attr = f"{control.ctrl}.rotate{axis}"

        cmds.setAttr(
            attr,
            lock=True,
            keyable=False,
            channelBox=False,
        )
        

    return control




# ----------------------------------------------------------------------
# Rotation Driving
# ----------------------------------------------------------------------

def _drive_twist_rotation(
    end_driver: str,
    twist_joint: str,
    primary_axis: str,
    weight: float,
    control=None,
):
    """
    Drive one twist joint's primary-axis rotation.

    Automatic:
        end driver twist * twist percentage

    Optional control:
        control twist * midpoint falloff

    Final:
        automatic + control
    """

    twist_source = (
        f"{end_driver}.rotate{primary_axis}"
    )

    # ---------------------------------------------------------
    # Automatic twist
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # No control
    # ---------------------------------------------------------

    control_transform = _get_control_transform(
        control
    )

    if not control_transform:

        cmds.connectAttr(
            f"{twist_mult}.output",
            f"{twist_joint}.rotate{primary_axis}",
            force=True,
        )

        return

    # ---------------------------------------------------------
    # Mid-control twist
    # ---------------------------------------------------------

    control_weight = _get_control_weight(
        weight
    )

    control_mult = cmds.createNode(
        "multDoubleLinear",
        name=f"{twist_joint}_control_twist_mult",
    )

    cmds.connectAttr(
        f"{control_transform}.rotate{primary_axis}",
        f"{control_mult}.input1",
        force=True,
    )

    cmds.setAttr(
        f"{control_mult}.input2",
        control_weight,
    )

    # ---------------------------------------------------------
    # Add automatic + control
    # ---------------------------------------------------------

    twist_add = cmds.createNode(
        "addDoubleLinear",
        name=f"{twist_joint}_twist_add",
    )

    cmds.connectAttr(
        f"{twist_mult}.output",
        f"{twist_add}.input1",
        force=True,
    )

    cmds.connectAttr(
        f"{control_mult}.output",
        f"{twist_add}.input2",
        force=True,
    )

    cmds.connectAttr(
        f"{twist_add}.output",
        f"{twist_joint}.rotate{primary_axis}",
        force=True,
    )


# ----------------------------------------------------------------------
# Translation Driving
# ----------------------------------------------------------------------

def _create_translation_result(
    end_driver: str,
    twist_joint: str,
    axis: str,
    weight: float,
    rest_end: float,
    rest_twist: float,
    control=None,
) -> str:
    """
    Create the translation calculation for one axis.

    Automatic translation:

        restTwist
            +
        ((currentEnd - restEnd) * twistWeight)

    Optional control:

        +
        (controlTranslate * midpointFalloff)

    Returns the output plug containing the final unclamped value.
    """

    end_attr = (
        f"{end_driver}.translate{axis}"
    )

    # ---------------------------------------------------------
    # End-driver delta
    #
    # current - rest
    # ---------------------------------------------------------

    delta = cmds.createNode(
        "plusMinusAverage",
        name=f"{twist_joint}_translate{axis}_delta",
    )

    cmds.setAttr(
        f"{delta}.operation",
        2,
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

    # ---------------------------------------------------------
    # Percentage of delta
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Add original twist position
    # ---------------------------------------------------------

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

    automatic_output = (
        f"{result}.output"
    )

    # ---------------------------------------------------------
    # Optional midpoint control
    # ---------------------------------------------------------

    control_transform = _get_control_transform(
        control
    )

    if not control_transform:
        return automatic_output

    control_weight = _get_control_weight(
        weight
    )

    control_mult = cmds.createNode(
        "multDoubleLinear",
        name=f"{twist_joint}_control_translate{axis}_mult",
    )

    cmds.connectAttr(
        f"{control_transform}.translate{axis}",
        f"{control_mult}.input1",
        force=True,
    )

    cmds.setAttr(
        f"{control_mult}.input2",
        control_weight,
    )

    control_add = cmds.createNode(
        "addDoubleLinear",
        name=f"{twist_joint}_control_translate{axis}_add",
    )

    cmds.connectAttr(
        automatic_output,
        f"{control_add}.input1",
        force=True,
    )

    cmds.connectAttr(
        f"{control_mult}.output",
        f"{control_add}.input2",
        force=True,
    )

    return f"{control_add}.output"


def _connect_primary_translation_clamp(
    source: str,
    end_driver: str,
    twist_joint: str,
    primary_axis: str,
    weight: float,
    negative: bool,
):
    """
    Clamp the primary-axis translation.

    Positive segment:

        minimum = twist percentage
        maximum = current limb length - remaining percentage

    Negative segment:

        minimum = current limb length + remaining percentage
        maximum = -twist percentage

    This prevents a midpoint control from:

        1. collapsing a twist joint through the segment root
        2. pushing a twist joint through the current segment end
    """

    twist_attr = (
        f"{twist_joint}.translate{primary_axis}"
    )

    end_attr = (
        f"{end_driver}.translate{primary_axis}"
    )

    remaining_weight = (
        1.0 - weight
    )

    clamp = cmds.createNode(
        "clamp",
        name=f"{twist_joint}_translate{primary_axis}_clamp",
    )

    # ---------------------------------------------------------
    # Positive primary-axis segment
    # ---------------------------------------------------------

    if not negative:

        # Dynamic upper boundary:
        #
        # current limb length - remaining percentage

        upper_limit = cmds.createNode(
            "addDoubleLinear",
            name=f"{twist_joint}_translate{primary_axis}_max",
        )

        cmds.connectAttr(
            end_attr,
            f"{upper_limit}.input1",
            force=True,
        )

        cmds.setAttr(
            f"{upper_limit}.input2",
            -remaining_weight,
        )

        # Literal percentage minimum.
        cmds.setAttr(
            f"{clamp}.minR",
            weight,
        )

        cmds.connectAttr(
            f"{upper_limit}.output",
            f"{clamp}.maxR",
            force=True,
        )

    # ---------------------------------------------------------
    # Negative primary-axis segment
    # ---------------------------------------------------------

    else:

        # Dynamic lower boundary:
        #
        # current limb length + remaining percentage

        lower_limit = cmds.createNode(
            "addDoubleLinear",
            name=f"{twist_joint}_translate{primary_axis}_min",
        )

        cmds.connectAttr(
            end_attr,
            f"{lower_limit}.input1",
            force=True,
        )

        cmds.setAttr(
            f"{lower_limit}.input2",
            remaining_weight,
        )

        cmds.connectAttr(
            f"{lower_limit}.output",
            f"{clamp}.minR",
            force=True,
        )

        # Literal percentage maximum toward zero.
        cmds.setAttr(
            f"{clamp}.maxR",
            -weight,
        )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    cmds.connectAttr(
        source,
        f"{clamp}.inputR",
        force=True,
    )

    cmds.connectAttr(
        f"{clamp}.outputR",
        twist_attr,
        force=True,
    )


def _drive_twist_translation(
    end_driver: str,
    twist_joint: str,
    primary_axis: str,
    weight: float,
    end_rest_translate: dict[str, float],
    control=None,
):
    """
    Drive XYZ translation for a single twist joint.

    All three axes receive proportional translation.

    The primary axis additionally receives dynamic compression and
    extension limits.
    """

    # ---------------------------------------------------------
    # Capture twist rest position BEFORE connecting anything.
    # ---------------------------------------------------------

    twist_rest_translate = {
        axis: cmds.getAttr(
            f"{twist_joint}.translate{axis}"
        )
        for axis in "XYZ"
    }

    primary_rest = twist_rest_translate[
        primary_axis
    ]

    negative = primary_rest < 0.0

    # ---------------------------------------------------------
    # XYZ
    # ---------------------------------------------------------

    for axis in "XYZ":

        source = _create_translation_result(
            end_driver=end_driver,
            twist_joint=twist_joint,
            axis=axis,
            weight=weight,
            rest_end=end_rest_translate[axis],
            rest_twist=twist_rest_translate[axis],
            control=control,
        )

        twist_attr = (
            f"{twist_joint}.translate{axis}"
        )

        # -----------------------------------------------------
        # Primary axis gets dynamic min/max limits.
        # -----------------------------------------------------

        if axis == primary_axis:

            _connect_primary_translation_clamp(
                source=source,
                end_driver=end_driver,
                twist_joint=twist_joint,
                primary_axis=primary_axis,
                weight=weight,
                negative=negative,
            )

        # -----------------------------------------------------
        # Other axes remain unrestricted.
        # -----------------------------------------------------

        else:

            cmds.connectAttr(
                source,
                twist_attr,
                force=True,
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
    control=None,
):
    """
    Drive a deformation twist segment from a switch-joint segment.

    Automatic behavior:
        - start/end bind joints follow their switch joints
        - twist is distributed by normalized segment position
        - translation/stretch is distributed by normalized position
        - primary-axis compression is clamped

    Optional midpoint control:
        - adds twist rotation
        - adds XYZ translation
        - influence peaks at the center of the segment
        - influence fades toward the start/end
        - primary translation remains constrained inside the segment
    """

    if not twist_joints:
        return

    primary_axis = _validate_axis(
        primary_axis
    )

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
    # Capture driver rest translation
    # ---------------------------------------------------------

    end_rest_translate = {
        axis: cmds.getAttr(
            f"{end_driver}.translate{axis}"
        )
        for axis in "XYZ"
    }

    # ---------------------------------------------------------
    # Twist joints
    # ---------------------------------------------------------

    count = len(
        twist_joints
    )

    for i, twist_joint in enumerate(
        twist_joints
    ):

        weight = _get_twist_weight(
            index=i,
            count=count,
        )

        # -----------------------------------------------------
        # Rotation
        # -----------------------------------------------------

        _drive_twist_rotation(
            end_driver=end_driver,
            twist_joint=twist_joint,
            primary_axis=primary_axis,
            weight=weight,
            control=control,
        )

        # -----------------------------------------------------
        # Translation
        # -----------------------------------------------------

        _drive_twist_translation(
            end_driver=end_driver,
            twist_joint=twist_joint,
            primary_axis=primary_axis,
            weight=weight,
            end_rest_translate=end_rest_translate,
            control=control,
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def create_twist(
    start_driver: str,
    end_driver: str,
    start_joint: str,
    end_joint: str,
    cst_parent: str,
    twist_count: int = 2,
    primary_axis: str = "Y",
    invert: bool = False,

    # Optional midpoint control
    mid_control: bool = False,
    control_parent: str | None = None,
    control_size: float = 1.0,
    control_shape:str = "round_square"

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

        cst_parent:
            Parent for generated constraint nodes.

        twist_count:
            Number of intermediate twist joints.

        primary_axis:
            Local bone/twist axis.

        invert:
            Existing inversion option.

        mid_control:
            If True, create an additive midpoint twist control.

        control_parent:
            Parent for the optional midpoint control.

        control_size:
            Size of the optional midpoint control.

    Returns:
        TwistData
    """

    primary_axis = _validate_axis(
        primary_axis
    )

    # ---------------------------------------------------------
    # Twist joints
    # ---------------------------------------------------------

    twist_joints = create_twist_joints(
        start_joint=start_joint,
        end_joint=end_joint,
        twist_count=twist_count,
        primary_axis=primary_axis,
        invert=invert,
    )

    # ---------------------------------------------------------
    # Weight split
    # ---------------------------------------------------------

    setup_twist_tag(
        start_joint=start_joint,
        twist_joints=twist_joints,
    )

    # ---------------------------------------------------------
    # Optional midpoint control
    # ---------------------------------------------------------

    control = None

    if mid_control:

        control = create_twist_control(
            start_joint=start_joint,
            end_joint=end_joint,
            primary_axis=primary_axis,
            control_parent=control_parent,
            control_size=control_size,
            control_shape =control_shape,
        )

    # ---------------------------------------------------------
    # Drive
    # ---------------------------------------------------------

    drive_twist_joints(
        start_driver=start_driver,
        end_driver=end_driver,
        start_joint=start_joint,
        end_joint=end_joint,
        twist_joints=twist_joints,
        primary_axis=primary_axis,
        cst_parent=cst_parent,
        control=control,
    )

    # ---------------------------------------------------------
    # Info
    # ---------------------------------------------------------

    return TwistData(
        start_driver=start_driver,
        end_driver=end_driver,
        start_joint=start_joint,
        end_joint=end_joint,
        twist_joints=twist_joints,
        control=control,
    )


# ----------------------------------------------------------------------
# Swing Driver
# ----------------------------------------------------------------------

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

    primary_axis = _validate_axis(
        primary_axis
    )

    descriptor = start_driver.removesuffix(
        "_jnt"
    )

    swing = cmds.createNode(
        "transform",
        name=f"{descriptor}_swing",
        parent=parent,
    )

    # ---------------------------------------------------------
    # Match initial transform
    # ---------------------------------------------------------

    cmds.matchTransform(
        swing,
        start_driver,
        position=True,
        rotation=True,
    )

    # ---------------------------------------------------------
    # Follow segment start
    # ---------------------------------------------------------

    cmds.pointConstraint(
        start_driver,
        swing,
        maintainOffset=True,
    )

    # ---------------------------------------------------------
    # Aim down segment
    # ---------------------------------------------------------

    aim_vectors = {
        "X": (1, 0, 0),
        "Y": (0, 1, 0),
        "Z": (0, 0, 1),
    }

    aim_vector = aim_vectors[
        primary_axis
    ]

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