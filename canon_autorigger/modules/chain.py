from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:list[Control]
    joint:list[str]

class Chain:
    def __init__(
        self,
        part: str = "chain",
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

    def chain_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.chain_ctrls = []
        self.chain_joints = []

        if self.roll:

            self.roll_ctrl = create_control(
                            name=f'{self.part}_curl_{self.side}',
                            parent=self.control_grp,
                            transform=self.guides[0].name,
                            size=self.control_size/64,
                            control_shape="sphere",
                            direction="y",
                            color_type=self.sub_control_color,
                            shape_position_offset=(-(self.control_size/16), 0, 0)
                        )
            module_space(control=self.roll_ctrl, space_list=[self.control_space])

        jnt_par = self.joint_parent
        ctrl_par = self.control_grp

        for i, guide in enumerate(self.guides):

            #controls
            ctrl = create_control(
                name=guide.descriptor,
                parent=ctrl_par,
                transform=guide.name,
                size=self.control_size/32,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color,
                sdk_offset=self.roll
            )
            self.chain_ctrls.append(ctrl)
            if self.roll:
                cmds.connectAttr(f'{self.roll_ctrl.ctrl}.rotateZ', f'{ctrl.sdk}.rotateZ')
                if i == 0:
                    cmds.connectAttr(f'{self.roll_ctrl.ctrl}.rotateX', f'{ctrl.sdk}.rotateX')
                    cmds.connectAttr(f'{self.roll_ctrl.ctrl}.rotateY', f'{ctrl.sdk}.rotateY')
            #joints
            joint = create_joint(name=f'def_{guide.descriptor}', transform=ctrl.ctrl, connect=True, parent=jnt_par)
            self.chain_joints.append(joint)
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type='parent', parent=self.guts)
            jnt_par = joint
            ctrl_par = ctrl.ctrl

        module_space(control=self.chain_ctrls[0], space_list=[self.control_space])

        chain_info = module_info(control=self.chain_ctrls, joint=self.chain_joints)
        return chain_info
    