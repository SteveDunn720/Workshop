from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.transform.utils import rotation_blend
from Workshop.maya_api.node import BlendColorsNode

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:list[Control]
    joint:list[str]

class Metacarpal:
    def __init__(
        self,
        part: str = "metacarpal",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        roll:bool = True

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.roll = roll
        self.main_control_color = 'Left' if self.side == 'L' else 'Right'
        self.sub_control_color = 'SubLeft' if self.side == 'L' else 'SubRight'

    # -------------------
    # Build steps
    # -------------------

    def metacarpal_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.metacarpal_ctrls = []
        self.metacarpal_joints = []

        if self.roll:

            self.roll_ctrl = create_control(
                            name=f'{self.part}_expresion_{self.side}',
                            parent=self.control_grp,
                            transform=self.guides[0].name,
                            size=self.control_size/32,
                            control_shape="cube",
                            direction="y",
                            color_type=self.sub_control_color,
                            shape_position_offset=(-(self.control_size/16), 0, 0)
                        )

            weights = [i / (len(self.guides) - 1) for i in range(len(self.guides))]
            weights.reverse()
            module_space(control=self.roll_ctrl, space_list=self.control_space)

        for i, guide in enumerate(self.guides):

            #controls
            ctrl = create_control(
                name=guide.descriptor,
                parent=self.control_grp,
                transform=guide.name,
                size=self.control_size/32,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color,
                sdk_offset=True
            )
            self.metacarpal_ctrls.append(ctrl)

            if i != 0:
                rotation_blend(name=f'{ctrl.ctrl}_meta', tfrom01=self.roll_ctrl.ctrl, tform02=ctrl.sdk, weight=weights[i], attr=True )

                translate_blend = BlendColorsNode(name=f'{ctrl.ctrl}_meta_BC')
                translate_blend.color2.connect_from(f'{self.roll_ctrl.ctrl}.translate')
                translate_blend.blender.set(weights[i])
                translate_blend.output.connect_to(f'{ctrl.sdk}.translate')



            
            #joints
            joint = create_joint(name=f'def_{guide.descriptor}', transform=ctrl.ctrl, connect=True, parent=self.joint_parent)
            self.metacarpal_joints.append(joint)
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type='parent', parent=self.guts)

            module_space(control=ctrl, space_list=self.control_space)

        metacarpal_info = module_info(control=self.metacarpal_ctrls, joint=self.metacarpal_joints)
        return metacarpal_info