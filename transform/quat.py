from dataclasses import dataclass

import math
import maya.cmds as cmds
from maya.api.OpenMaya import MMatrix, MTransformationMatrix


from Workshop.maya_api.attribute import QuatAttribute, Vector3Attribute
from Workshop.maya_api.node import (
    QuatInvertNode,
    QuatNormalizeNode,
    QuatProdNode,
    QuatSlerpNode,
    QuatToEulerNode,
    DecomposeMatrixNode,
    MultMatrixNode,
)
from Workshop.name import get_short_name
from Workshop.transform.matrix import localize_and_decompose_matrix, matrix_constraint
from Workshop.transform.structs import Axis
from Workshop.transform.utils import create_transform, match_transform




@dataclass
class RelativeRotation:
    """Live rest-relative motion expressed in a reference space."""

    rotation: QuatAttribute
    translation: Vector3Attribute


def drive_rotation_with_quat(transform: str, quat_attribute: QuatAttribute) -> None:
    """
    Drive the rotation of a transform using a QuatAttribute via a QuatToEuler node.
    """
    euler_angles = QuatToEulerNode(f"{get_short_name(transform)}_euler")
    euler_angles.input_rotate_order.connect_from(f"{transform}.rotateOrder")
    quat_attribute.connect_to(euler_angles.input_quat)
    euler_angles.output_rotate.connect_to(f"{transform}.rotate")


def _connect_twist_quat(source: QuatAttribute, destination: QuatAttribute, axis: Axis) -> None:
    """
    Connect the W and the specified axis component from one quaternion to another.
    (Forming a twist Decomposition) https://www.chadvernon.com/blog/swing-twist/
    """
    source.w.connect_to(destination.w)
    if axis == "x":
        source.x.connect_to(destination.x)
    elif axis == "y":
        source.y.connect_to(destination.y)
    elif axis == "z":
        source.z.connect_to(destination.z)


def twist_extract_euler(transform: str, reference_space: str, axis: Axis) -> QuatToEulerNode:
    """
    Extract the twist of a transform relative to a specified axis and
    output it as Euler angles.
    Args:
        transform: Name of the transform whose twist should be extracted.
        reference_space: Transform used as the reference space for the twist.
        axis: Axis around which the twist should be isolated ("x", "y", or "z").

    Returns:
        QuatToEulerNode: Node producing the extracted twist as Euler rotation.
    """
    name = f"{get_short_name(transform)}_twist"
    decompose = localize_and_decompose_matrix(transform, reference_space)
    euler_output = QuatToEulerNode(f"{name}_euler")
    _connect_twist_quat(decompose.output_quat, euler_output.input_quat, axis)
    return euler_output


def twist_extract_quat(transform: str, reference_space: str, axis: Axis) -> QuatAttribute:
    """
    Extract the twist of a transform relative to a specified axis and
    output it as a normalized quaternion.
    Args:
        transform: Name of the transform whose twist should be extracted.
        reference_space: Transform used as the reference space for the twist.
        axis: Axis around which the twist should be isolated ("x", "y", or "z").

    Returns:
        QuatAttribute: The attribute with the resulting twist calculation.
    """
    name = f"{get_short_name(transform)}_twist"
    decompose = localize_and_decompose_matrix(transform, reference_space)
    output = QuatNormalizeNode(name)
    _connect_twist_quat(decompose.output_quat, output.input_quat, axis)
    return output.output_quat


def swing_extract_quat(transform: str, reference_space: str, axis: Axis) -> QuatAttribute:
    """
    Extract the swing of a transform relative to a specified axis and
    output it as a normalized quaternion.
    Args:
        transform: Name of the transform whose swing should be extracted.
        reference_space: Transform used as the reference space for the swing.
        axis: Axis around which the twist should be isolated ("x", "y", or "z").

    Returns:
        QuatAttribute: The attribute with the resulting swing calculation.
    """
    name = f"{get_short_name(transform)}_swing"
    decompose = localize_and_decompose_matrix(transform, reference_space)
    inverse = QuatInvertNode(f"{get_short_name(transform)}_twist_inverse")
    _connect_twist_quat(decompose.output_quat, inverse.input_quat, axis)
    swing = QuatProdNode(name)
    inverse.output_quat.connect_to(swing.input1_quat)
    decompose.output_quat.connect_to(swing.input2_quat)
    return swing.output_quat


def create_swing_only_transform(
    transform: str,
    reference_space: str,
    axis: Axis,
    name: str | None = None,
    parent: str | None = None,
    constrain_translate: bool = True,
) -> str:
    """
    Extracts the swing of a transform relative to a specific space and specified axis and
    creates a transform that follows only the position and swing.
    Args:
        transform: Name of the transform whose swing should be extracted.
        reference_space: Transform used as the reference space for the swing.
        axis: Axis around which the twist should be isolated ("x", "y", or "z").
        name (optional): The name for the newly created swing transform
        parent (optional): Parent for the newly created swing transform. If None, will be set to the reference space.
        constrain_translate: If True the swing transform will follow the translation of the source transform along with its swing.

    Returns:
        str: The name of the created swing transform.
    """
    used_name = name if name is not None else f"{get_short_name(transform)}_swing"
    used_parent = parent if parent is not None else reference_space

    neutral_group = create_transform(name=f"{name}_npo", parent=used_parent)
    swing_transform = create_transform(name=used_name, parent=neutral_group)
    match_transform(neutral_group, transform)
    if parent is not None:
        matrix_constraint(reference_space, neutral_group)
    swing_quat = swing_extract_quat(transform, neutral_group, axis)
    if constrain_translate:
        matrix_constraint(
            transform,
            swing_transform,
            translate=True,
            rotate=False,
            scale=False,
            shear=False,
        )
    drive_rotation_with_quat(swing_transform, swing_quat)
    return swing_transform


def relative_rotation(
    driver: str,
    reference: str,
    name: str,
) -> RelativeRotation:
    """
    Calculate the driver's motion relative to a reference transform.

    The current pose is captured as rest when this function is called.

    Rotation:
        Current relative orientation * inverse(rest orientation)

    Translation:
        Current relative position - rest relative position

    Uses Maya's row-vector matrix convention.
    """

    relative = MultMatrixNode(f"{name}_relative_mm")

    relative.matrix_in[0].connect_from(
        f"{driver}.worldMatrix[0]"
    )
    relative.matrix_in[1].connect_from(
        f"{reference}.worldInverseMatrix[0]"
    )

    # Capture rest pose before building the live delta network.
    rest_values = cmds.getAttr(
        f"{relative.name}.matrixSum"
    )

    rest_matrix = MMatrix(rest_values)
    rest_transform = MTransformationMatrix(rest_matrix)

    rest_translation = rest_transform.translation(
        4  # MSpace.kWorld
    )

    rest_rotation = rest_transform.rotation(
        asQuaternion=True
    )

    # Extract live translation in reference space.
    relative_decompose = DecomposeMatrixNode(
        f"{name}_relative_dm"
    )
    relative_decompose.input_matrix.connect_from(
        relative.matrix_sum
    )

    # Rotation-only matrix. Strip translation, scale and shear
    # before extracting the rotational delta.
    pick_rotation = cmds.createNode(
        "pickMatrix",
        name=f"{name}_rotation_pick",
    )

    cmds.connectAttr(
        f"{relative.name}.matrixSum",
        f"{pick_rotation}.inputMatrix",
    )

    cmds.setAttr(f"{pick_rotation}.useTranslate", False)
    cmds.setAttr(f"{pick_rotation}.useScale", False)
    cmds.setAttr(f"{pick_rotation}.useShear", False)

    rotation_delta = MultMatrixNode(
        f"{name}_rotation_delta_mm"
    )

    rotation_delta.matrix_in[0].connect_from(
        f"{pick_rotation}.outputMatrix"
    )

    rotation_delta.matrix_in[1].set(
        rest_rotation.inverse().asMatrix()
    )

    rotation_decompose = DecomposeMatrixNode(
        f"{name}_rotation_delta_dm"
    )

    rotation_decompose.input_matrix.connect_from(
        rotation_delta.matrix_sum
    )

    # Subtract the rest-relative translation.
    translation_delta = cmds.createNode(
        "plusMinusAverage",
        name=f"{name}_translation_delta",
    )

    cmds.setAttr(
        f"{translation_delta}.operation",
        2,  # Subtract
    )

    cmds.connectAttr(
        f"{relative_decompose.name}.outputTranslate",
        f"{translation_delta}.input3D[0]",
    )

    cmds.setAttr(
        f"{translation_delta}.input3D[1]",
        rest_translation.x,
        rest_translation.y,
        rest_translation.z,
        type="double3",
    )

    return RelativeRotation(
        rotation=rotation_decompose.output_quat,
        translation=Vector3Attribute(
            f"{translation_delta}.output3D"
        ),
    )


def weighted_rotation_quat(
    rotation: QuatAttribute,
    name: str,
    weight: float = 0.5,
) -> QuatAttribute:
    """
    Interpolate from identity to the supplied quaternion.

    The input should represent a rest-relative rotation.
    """

    slerp = QuatSlerpNode(f"{name}_slerp")

    slerp.input1_quat.x.set(0.0)
    slerp.input1_quat.y.set(0.0)
    slerp.input1_quat.z.set(0.0)
    slerp.input1_quat.w.set(1.0)

    slerp.input2_quat.connect_from(rotation)
    slerp.input_t.set(weight)

    return slerp.output_quat


def signed_relative_twist(
    rotation,
    axis: str,
    name: str,
) -> str:
    """
    Return a signed twist angle in degrees from a rest-relative quaternion.

    rotation:
        QuatAttribute representing the rest-relative rotation.

    axis:
        Local X, Y, or Z.

    Returns:
        Attribute path containing the signed angle in degrees.
    """

    axis = axis.upper()

    if axis not in ("X", "Y", "Z"):
        raise ValueError(f"Invalid twist axis: {axis}")

    # Extract the selected quaternion component.
    component = {
        "X": "X",
        "Y": "Y",
        "Z": "Z",
    }[axis]

    # atan2(q_axis, q_w) * 2, converted to degrees.
    #
    # Maya's floatMath node supports atan2 in versions that
    # provide that operation, but compatibility varies.
    #
    # This implementation uses an expression for the signed angle.

    expression_node = cmds.createNode(
        "expression",
        name=f"{name}_signed_twist_expr",
    )

    output_node = cmds.createNode(
        "network",
        name=f"{name}_signed_twist_output",
    )

    cmds.addAttr(
        output_node,
        longName="angle",
        attributeType="double",
    )

    q_axis = f"{rotation.attr_path}{component}"
    q_w = f"{rotation.attr_path}W"

    cmds.expression(
        expression_node,
        edit=True,
        string=(
            f"{output_node}.angle = "
            f"2 * atan2({q_axis}, {q_w}) * 57.29577951308232;"
        ),
        alwaysEvaluate=False,
        unitConversion="all",
    )

    return f"{output_node}.angle"