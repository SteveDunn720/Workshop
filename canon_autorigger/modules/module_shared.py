from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.transform.constraint import constraint
from Workshop.maya_api.node import BlendMatrixNode, MultMatrixNode, MultiplyDivideNode, RemapValueNode, ReverseNode
from Workshop.tag.core import lock_tag
from Workshop.control.core import Control
from Workshop.transform.utils import create_transform
from Workshop.transform.utils import create_space_switch
from Workshop.tag.core import obj_vis_tag


@dataclass
class DriverOffset:
    pos: str
    offset: str

@dataclass
class module:
    main_grp:str
    control_grp:str
    guts:str
    fk_grp:str
    ik_grp:str
    bendy_grp:str
    

def module_prep(part: str, side: str, parent: str, fkik:bool=False, gut:bool=True, bendy:bool=True)->module:
    cmds.refresh()
    main_grp = create_transform(name=f"{part}_{side}", parent=parent)
    control_grp = create_transform(name=f"{part}_CTRLS_{side}", parent=main_grp)
    if gut:
        guts = create_transform(name=f"{part}_GUTS_{side}", parent=main_grp)
        obj_vis_tag(guts, 'ALWAYS')
    else:
        guts = ''
    if fkik:
        ik_control_grp = create_transform(name=f"{part}_IK_controls_{side}", parent=control_grp)
        fk_control_grp = create_transform(name=f"{part}_Fk_controls_{side}", parent=control_grp)
    else:
        ik_control_grp = ''
        fk_control_grp = ''
    if bendy:
        bendy_control_grp = create_transform(name=f"{part}_bendy_controls_{side}", parent=control_grp)
    else:
        bendy_control_grp = ''

    prep = module(main_grp=main_grp, control_grp=control_grp, guts=guts, fk_grp=fk_control_grp, ik_grp=ik_control_grp, bendy_grp=bendy_control_grp)
    
    return prep

def module_space(space_list:list, control:Control):
    if len(space_list) == 0:
        pass
    elif len(space_list) == 1:
        cmds.parentConstraint(space_list[0], control.top, maintainOffset=True)
    else:
        create_space_switch(target_transform=control.top, parents=space_list, target_control=control.ctrl)


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


def create_module_switch(
    driven: list[str],
    drivers: dict[str, dict[str, list[str]]],
    node_attr: str,
    descriptor: str,
    controls: list[str] | None = None,
    connect_switch_attr: str | None = None,
    maintain_offset: bool = True,
) -> str | None:
    """
    Connect multiple driver systems to a shared driven chain.

    Supports:
        1 driver  -> Direct parent constraints.
        2 drivers -> Float blend switch (0-1).
        3+ drivers -> Enum switch with condition nodes.

    Args:
        driven:
            Transforms receiving constraints.

        drivers:
            Dictionary of driver systems.

            {
                "FK": {
                    "joints": [...],
                    "visibility": [...]
                },
                "IK": {
                    "joints": [...],
                    "visibility": [...]
                }
            }

        node_attr:
            Node receiving the switch attribute.

        descriptor:
            Naming prefix for generated nodes.

        controls:
            Optional controls receiving proxy switch attributes.

        connect_switch_attr:
            Optional existing switch attribute.

        maintain_offset:
            Maintain offsets when creating constraints.

    Returns:
        Switch attribute path, or None for a single driver.
    """

    if not drivers:
        raise ValueError("At least one driver system is required.")

    if not driven:
        raise ValueError("At least one driven transform is required.")

    mode_names = list(drivers)
    mode_count = len(mode_names)

    # -----------------------------------------
    # Validate driver chains
    # -----------------------------------------

    for mode_name, data in drivers.items():

        joints = data.get("joints", [])

        if len(joints) != len(driven):
            raise ValueError(
                f"{mode_name} has {len(joints)} drivers, "
                f"but {len(driven)} driven transforms were provided."
            )

    # -----------------------------------------
    # Single driver: direct constraints
    # -----------------------------------------

    if mode_count == 1:

        mode_name = mode_names[0]
        driver_joints = drivers[mode_name]["joints"]

        for driver, target in zip(
            driver_joints,
            driven,
            strict=True,
        ):
            constraint(
                drivers=[driver],
                driven=target,
                constraint_type="parent",
                maintain_offset=maintain_offset,
            )

        return None

    # -----------------------------------------
    # Create or reuse switch attribute
    # -----------------------------------------

    if connect_switch_attr:

        switch_attr = connect_switch_attr

    else:

        if mode_count == 2:

            cmds.addAttr(
                node_attr,
                longName="module_switch",
                attributeType="double",
                defaultValue=0,
                minValue=0,
                maxValue=1,
                keyable=True,
            )

        else:

            cmds.addAttr(
                node_attr,
                longName="module_switch",
                attributeType="enum",
                enumName=":".join(mode_names),
                defaultValue=0,
                keyable=True,
            )

        switch_attr = f"{node_attr}.module_switch"

    # -----------------------------------------
    # Two drivers: float blend
    # -----------------------------------------

    if mode_count == 2:

        reverse = ReverseNode(
            name=f"{descriptor}_switch_rev"
        )

        reverse.input.x.connect_from(switch_attr)

        weights = [
            reverse.output.x,
            switch_attr,
        ]

        for index, mode_name in enumerate(mode_names):

            visibility_groups = drivers[mode_name].get(
                "visibility", []
            )

            for group in visibility_groups:

                cmds.connectAttr(
                    weights[index],
                    f"{group}.visibility",
                    force=True,
                )

        # Create constraints for each driven transform

        for joint_index, target in enumerate(driven):

            driver_joints = [
                drivers[mode_name]["joints"][joint_index]
                for mode_name in mode_names
            ]

            parent_con = constraint(
                drivers=driver_joints,
                driven=target,
                constraint_type="parent",
                maintain_offset=maintain_offset,
            )

            for weight_index, weight_attr in enumerate(weights):

                cmds.connectAttr(
                    weight_attr,
                    parent_con.connections[weight_index],
                    force=True,
                )

    # -----------------------------------------
    # Three or more drivers: enum switching
    # -----------------------------------------

    else:

        mode_outputs = []

        for index, mode_name in enumerate(mode_names):

            condition = cmds.createNode(
                "condition",
                name=f"{descriptor}_{mode_name}_switch_CND",
            )

            cmds.setAttr(
                f"{condition}.operation",
                0,  # Equal
            )

            cmds.setAttr(
                f"{condition}.secondTerm",
                index,
            )

            cmds.setAttr(
                f"{condition}.colorIfTrueR",
                1,
            )

            cmds.setAttr(
                f"{condition}.colorIfFalseR",
                0,
            )

            cmds.connectAttr(
                switch_attr,
                f"{condition}.firstTerm",
            )

            output = f"{condition}.outColorR"

            mode_outputs.append(output)

            # Visibility

            visibility_groups = drivers[mode_name].get(
                "visibility", []
            )

            for group in visibility_groups:

                cmds.connectAttr(
                    output,
                    f"{group}.visibility",
                    force=True,
                )

        # Create constraints

        for joint_index, target in enumerate(driven):

            driver_joints = [
                drivers[mode_name]["joints"][joint_index]
                for mode_name in mode_names
            ]

            parent_con = constraint(
                drivers=driver_joints,
                driven=target,
                constraint_type="parent",
                maintain_offset=maintain_offset,
            )

            for index, output in enumerate(mode_outputs):

                cmds.connectAttr(
                    output,
                    parent_con.connections[index],
                    force=True,
                )

    # -----------------------------------------
    # Proxy attributes
    # -----------------------------------------

    if controls:

        for control in controls:

            cmds.addAttr(
                control,
                longName="module_switch",
                proxy=switch_attr,
            )

    return switch_attr



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


def create_mid_blend_driver_offset(
    control: Control,
    driver_a: Control,
    driver_b: Control,
    parent_space: str,
    blend: float = 0.5,
) -> DriverOffset:
    """
    Drive a control from the change in the blended position between two drivers.

    At rest:
        midpoint_rest = blend(driver_a, driver_b)

    At runtime:
        midpoint_current = blend(driver_a, driver_b)

        delta = midpoint_current * inverse(midpoint_rest)

    Only that delta is applied to the affected control, so the control
    does not snap to the midpoint when the rig is built.

    Args:
        control:
            Control being affected.

        driver_a:
            First control contributing to the midpoint.

        driver_b:
            Second control contributing to the midpoint.

        parent_space:
            Space in which the two drivers should be evaluated.

        blend:
            Blend between driver_a and driver_b.
            0.0 = driver_a
            0.5 = midpoint
            1.0 = driver_b
    """

    driven_name = control.name
    driver_a_name = driver_a.name
    driver_b_name = driver_b.name

    # ---------------------------------------------------------
    # Current SDK parent
    # ---------------------------------------------------------

    current_parent = cmds.listRelatives(
        control.sdk,
        parent=True,
    )[0]

    # ---------------------------------------------------------
    # Create hierarchy AT THE CONTROL
    #
    # Unlike your other function, we don't want to create this
    # hierarchy at either driver or at the midpoint.
    # ---------------------------------------------------------

    blend_pos = create_transform(
        name=f"{driven_name}_{driver_a_name}_{driver_b_name}_blend_pos",
        parent=current_parent,
        transform=control.sdk,
    )

    blend_offset = create_transform(
        name=f"{driven_name}_{driver_a_name}_{driver_b_name}_blend_offset",
        parent=blend_pos,
        transform=control.sdk,
    )

    cmds.parent(
        control.sdk,
        blend_offset,
    )

    lock_tag(object=blend_pos)
    lock_tag(object=blend_offset)

    # ---------------------------------------------------------
    # Driver A relative to parent space
    # ---------------------------------------------------------

    driver_a_relative = MultMatrixNode(
        name=f"{driven_name}_{driver_a_name}_relative_matrix"
    )

    driver_a_relative.matrix_in[0].connect_from(
        f"{driver_a.ctrl}.worldMatrix[0]"
    )

    driver_a_relative.matrix_in[1].connect_from(
        f"{parent_space}.worldInverseMatrix[0]"
    )

    # ---------------------------------------------------------
    # Driver B relative to parent space
    # ---------------------------------------------------------

    driver_b_relative = MultMatrixNode(
        name=f"{driven_name}_{driver_b_name}_relative_matrix"
    )

    driver_b_relative.matrix_in[0].connect_from(
        f"{driver_b.ctrl}.worldMatrix[0]"
    )

    driver_b_relative.matrix_in[1].connect_from(
        f"{parent_space}.worldInverseMatrix[0]"
    )

    # ---------------------------------------------------------
    # Calculate current blended transform
    #
    # inputMatrix = A
    # targetMatrix = B
    #
    # 0.0 -> A
    # 0.5 -> midpoint
    # 1.0 -> B
    # ---------------------------------------------------------

    midpoint_matrix = BlendMatrixNode(
        name=f"{driven_name}_{driver_a_name}_{driver_b_name}_midpoint_matrix"
    )

    midpoint_matrix.input_matrix.connect_from(
        driver_a_relative.matrix_sum
    )

    midpoint_matrix.target[0].target_matrix.connect_from(
        driver_b_relative.matrix_sum
    )

    midpoint_matrix.target[0].weight.set(blend)

    # ---------------------------------------------------------
    # Store midpoint REST matrix
    # ---------------------------------------------------------

    rest_matrix = cmds.getAttr(
        str(midpoint_matrix.output_matrix)
    )

    rest_inverse = cmds.createNode(
        "inverseMatrix",
        name=f"{driven_name}_{driver_a_name}_{driver_b_name}_midpoint_rest_inverse",
    )

    cmds.setAttr(
        f"{rest_inverse}.inputMatrix",
        *rest_matrix,
        type="matrix",
    )

    # ---------------------------------------------------------
    # Current midpoint * inverse(rest midpoint)
    #
    # At rest:
    #
    # midpoint * inverse(midpoint) = identity
    #
    # Therefore blend_offset receives no movement.
    # ---------------------------------------------------------

    delta_matrix = MultMatrixNode(
        name=f"{driven_name}_{driver_a_name}_{driver_b_name}_midpoint_delta"
    )

    delta_matrix.matrix_in[0].connect_from(
        midpoint_matrix.output_matrix
    )

    delta_matrix.matrix_in[1].connect_from(
        f"{rest_inverse}.outputMatrix"
    )

    # ---------------------------------------------------------
    # Apply midpoint DELTA to affected control
    # ---------------------------------------------------------

    delta_matrix.matrix_sum.connect_to(
        f"{blend_offset}.offsetParentMatrix"
    )

    return DriverOffset(
        pos=blend_pos,
        offset=blend_offset,
    )