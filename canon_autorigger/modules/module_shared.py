from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.transform.constraint import constraint
from Workshop.maya_api.node import BlendMatrixNode, MultMatrixNode, MultiplyDivideNode, RemapValueNode, ReverseNode
from Workshop.tag.core import lock_tag
from Workshop.control.core import Control
from Workshop.transform.utils import create_transform

@dataclass
class DriverOffset:
    pos: str
    offset: str


def fkik_switch(controls:list|None, node_attr:str, descriptor:str, fk_grp:str, ik_grp:str, fk_joints:list, ik_joints:list, switch_joints:list, connect_switch_attr:str | None = None,):
    if connect_switch_attr:
        FK_IK_Switch=connect_switch_attr
    else:
        cmds.addAttr(node_attr, longName='FK_IK_Switch', attributeType='double', defaultValue=1, maxValue=1, minValue=0, keyable=True)
        FK_IK_Switch = f'{node_attr}.FK_IK_Switch'
    rev = ReverseNode(name=f"{descriptor}_FKIK_rev")
    rev.input.x.connect_from(FK_IK_Switch)
    rev.output.x.connect_to(f'{ik_grp}.visibility')
    cmds.connectAttr(FK_IK_Switch, f'{fk_grp}.visibility')
    for i,jnt in enumerate(switch_joints):
        parent_con = constraint(drivers=[fk_joints[i], ik_joints[i]], driven=jnt, constraint_type='parent', maintain_offset=True)

        parent_con.connections[0]
       
        cmds.connectAttr(FK_IK_Switch, f'{parent_con.connections[0]}')   #type:ignore
        cmds.connectAttr(rev.output.x, f'{parent_con.connections[1]}')   #type:ignore
    if controls:
        for control in controls:
            cmds.addAttr(control, longName='FKIK_Switch', proxy=FK_IK_Switch)

    return FK_IK_Switch


def create_driver_offset(
    control: Control,
    driver: Control | str,
    x_range: tuple = (-90, 90),
    y_range: tuple = (-90, 90),
    z_range: tuple = (-90, 90),
    trans_mult: float | tuple = 1.0,
    rot_mult: float | tuple = 1.0,
) -> DriverOffset:

    # ---------------------------------------------------------
    # Resolve driver
    # ---------------------------------------------------------

    if isinstance(driver, Control):
        driver_transform = driver.ctrl
    else:
        driver_transform = driver

    # ---------------------------------------------------------
    # Normalize multipliers
    # ---------------------------------------------------------

    if isinstance(trans_mult, (int, float)):
        trans_mult = (
            trans_mult,
            trans_mult,
            trans_mult,
        )

    if isinstance(rot_mult, (int, float)):
        rot_mult = (
            rot_mult,
            rot_mult,
            rot_mult,
        )

    # ---------------------------------------------------------
    # Naming
    # ---------------------------------------------------------

    driven_name = control.name
    driver_name = driver_transform

    # ---------------------------------------------------------
    # Find current SDK parent
    # ---------------------------------------------------------

    current_parent = cmds.listRelatives(
        control.sdk,
        parent=True,
    )[0]

    # ---------------------------------------------------------
    # Create driver hierarchy
    #
    # IMPORTANT:
    # These are positioned at the DRIVER, just like the
    # original connect_jaw setup.
    # ---------------------------------------------------------

    driver_pos = create_transform(
        name=f"{driven_name}_{driver_name}_pos",
        parent=current_parent,
        transform=driver_transform,
    )

    driver_offset = create_transform(
        name=f"{driven_name}_{driver_name}_offset",
        parent=driver_pos,
        transform=driver_transform,
    )

    cmds.parent(
        control.sdk,
        driver_offset,
    )

    lock_tag(object=driver_pos)
    lock_tag(object=driver_offset)

    # ---------------------------------------------------------
    # Rotation
    # ---------------------------------------------------------

    rotation_data = (
        ("X", x_range, rot_mult[0]),
        ("Y", y_range, rot_mult[1]),
        ("Z", z_range, rot_mult[2]),
    )

    for axis, value_range, multiplier in rotation_data:

        remap = RemapValueNode(
            name=f"{driven_name}_{driver_name}_remap{axis}"
        )

        remap.input_min.set(value_range[0])
        remap.input_max.set(value_range[1])

        remap.output_min.set(
            value_range[0] * multiplier
        )

        remap.output_max.set(
            value_range[1] * multiplier
        )

        remap.input_value.connect_from(
            f"{driver_transform}.rotate{axis}"
        )

        remap.output.connect_to(
            f"{driver_offset}.rotate{axis}"
        )

    # ---------------------------------------------------------
    # Translation
    # ---------------------------------------------------------

    translate_mult = MultiplyDivideNode(
        name=f"{driven_name}_{driver_name}_translate_mult"
    )

    translate_mult.input1.connect_from(
        f"{driver_transform}.translate"
    )

    translate_mult.input2.set(
        trans_mult
    )

    translate_mult.output.connect_to(
        f"{driver_offset}.translate"
    )

    return DriverOffset(
        pos=driver_pos,
        offset=driver_offset,
    )

def create_blend_driver_offset(
    control: Control,
    driver: Control,
    parent_space: str,
    default_mult: float = 0.5,
) -> DriverOffset:

    driven_transform = control.ctrl
    driver_transform = driver.ctrl

    driven_name = control.name
    driver_name = driver.name

    # ---------------------------------------------------------
    # Find current SDK parent
    # ---------------------------------------------------------

    current_parent = cmds.listRelatives(
        control.sdk,
        parent=True,
    )[0]

    # ---------------------------------------------------------
    # Create driver hierarchy
    #
    # Position this hierarchy at the driver.
    # ---------------------------------------------------------

    driver_pos = create_transform(
        name=f"{driven_name}_{driver_name}_pos",
        parent=current_parent,
        transform=driver_transform,
    )

    driver_offset = create_transform(
        name=f"{driven_name}_{driver_name}_offset",
        parent=driver_pos,
        transform=driver_transform,
    )

    cmds.parent(
        control.sdk,
        driver_offset,
    )

    lock_tag(object=driver_pos)
    lock_tag(object=driver_offset)

    # ---------------------------------------------------------
    # Follow attribute
    # ---------------------------------------------------------

    driven_attr = f"follow_{driver_name}"
    driver_attr = f"{driven_name}_follow"

    cmds.addAttr(
        driven_transform,
        longName=driven_attr,
        attributeType="double",
        minValue=0,
        maxValue=1,
        defaultValue=default_mult,
        keyable=True,
    )

    cmds.addAttr(
        driver_transform,
        longName=driver_attr,
        proxy=f"{driven_transform}.{driven_attr}",
    )

    # ---------------------------------------------------------
    # Driver relative to parent space
    #
    # driver.worldMatrix
    # *
    # parent_space.worldInverseMatrix
    # ---------------------------------------------------------

    relative_matrix = MultMatrixNode(
        name=f"{driven_name}_{driver_name}_relative_matrix"
    )

    relative_matrix.matrix_in[0].connect_from(
        f"{driver_transform}.worldMatrix[0]"
    )

    relative_matrix.matrix_in[1].connect_from(
        f"{parent_space}.worldInverseMatrix[0]"
    )

    # ---------------------------------------------------------
    # Store rest relative matrix
    # ---------------------------------------------------------

    rest_matrix = cmds.getAttr(
        f"{relative_matrix}.matrixSum"
    )

    # ---------------------------------------------------------
    # Current relative * inverse rest
    # ---------------------------------------------------------

    rest_inverse = cmds.createNode(
        "inverseMatrix",
        name=f"{driven_name}_{driver_name}_rest_inverse"
    )

    cmds.setAttr(
        f"{rest_inverse}.inputMatrix",
        *rest_matrix,
        type="matrix",
    )

    delta_matrix = MultMatrixNode(
        name=f"{driven_name}_{driver_name}_delta_matrix"
    )

    delta_matrix.matrix_in[0].connect_from(
        relative_matrix.matrix_sum
    )

    delta_matrix.matrix_in[1].connect_from(
        f"{rest_inverse}.outputMatrix"
    )

    # ---------------------------------------------------------
    # Blend identity -> relative driver delta
    # ---------------------------------------------------------

    blend_matrix = BlendMatrixNode(
        name=f"{driven_name}_{driver_name}_blend_matrix"
    )

    blend_matrix.target[0].target_matrix.connect_from(
        delta_matrix.matrix_sum
    )

    blend_matrix.target[0].weight.connect_from(
        f"{driven_transform}.{driven_attr}"
    )
    # ---------------------------------------------------------
    # Drive offset
    # ---------------------------------------------------------

    blend_matrix.output_matrix.connect_to(
        f"{driver_offset}.offsetParentMatrix"
    )

    return DriverOffset(
        pos=driver_pos,
        offset=driver_offset,
    )