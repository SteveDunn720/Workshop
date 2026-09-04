from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import RemapValueNode

from .module_initialize import module_prep, module_space

import maya.cmds as cmds
import math


@dataclass
class module_info:
    control:Control
    joint:str

class Jaw:
    def __init__(
        self,
        part: str = "jaw",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        control_color:str = 'MISC',
        control_shape:str = 'circle'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.main_control_color = 'Middle'
        self.sub_control_color = 'SubMiddle'

    # -------------------
    # Build steps
    # -------------------

    def get_yz_angle(self, object_a: str, object_b: str) -> float:
        pos_a = cmds.xform(
            object_a,
            query=True,
            worldSpace=True,
            translation=True,
        )

        pos_b = cmds.xform(
            object_b,
            query=True,
            worldSpace=True,
            translation=True,
        )

        delta_y = pos_b[1] - pos_a[1]
        delta_z = pos_b[2] - pos_a[2]

        angle = math.degrees(
            math.atan2(delta_z, delta_y)
        )

        return angle

    def jaw_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        rot = self.get_yz_angle(self.guides[0].name, self.guides[1].name,)

        #controls
        self.jaw_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size/6,
            control_shape="jaw",
            direction="y",
            sdk_offset=True, 
            color_type=self.sub_control_color,
            shape_rotation_offset=(rot - 90,0,0),
            dimensions=(1,1.3,1.3),
            shape_position_offset=(0,-self.control_size/60,0)
        )

        module_space(control=self.jaw_ctrl, space_list=self.control_space)

        #joints

        self.jaw_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.jaw_ctrl.ctrl, connect=True, parent=self.joint_parent)
        self.jaw_ee_joint = create_joint(name=f'def_{self.guides[1].descriptor}', transform=self.guides[1].name, connect=False, parent=self.jaw_joint)

        self.larynx_ctrl = create_control(
            name=self.guides[2].descriptor,
            parent=self.control_grp,
            transform=self.guides[2].name,
            size=self.control_size/40,
            control_shape="circle",
            direction="y",
            sdk_offset=True, 
            shape_rotation_offset=(90,0,0),
            color_type=self.main_control_color
        )

        larynx_remap = RemapValueNode(name='larynx_remap')
        larynx_remap.input_value.connect_from(f'{self.jaw_ctrl.ctrl}.rotateX')
        larynx_remap.input_max.set(90)

        cmds.addAttr(self.jaw_ctrl.ctrl, longName="larynx_mult", defaultValue=-self.control_size/6, keyable=True)
        cmds.addAttr(self.larynx_ctrl.ctrl, longName="larynx_mult", proxy=f'{self.jaw_ctrl.ctrl}.larynx_mult')

        larynx_remap.output_max.connect_from(f'{self.jaw_ctrl.ctrl}.larynx_mult')
        larynx_remap.output.connect_to(f'{self.larynx_ctrl.sdk}.translateY')

        jaw_remap = RemapValueNode(name='jaw_remap')
        jaw_remap.input_value.connect_from(f'{self.jaw_ctrl.ctrl}.rotateX')
        jaw_remap.input_max.set(90)

        cmds.addAttr(self.jaw_ctrl.ctrl, longName="jaw_mult", defaultValue=self.control_size/10, keyable=True)

        jaw_remap.output_max.connect_from(f'{self.jaw_ctrl.ctrl}.jaw_mult')
        jaw_remap.output.connect_to(f'{self.jaw_ctrl.sdk}.translateZ')


        module_space(control=self.larynx_ctrl, space_list=self.control_space)
        #constraint(drivers=[self.control_space[0], ], driven=self.larynx_ctrl.top, constraint_type='parent', parent=self.guts)

        #joints

        self.larynx_joint = create_joint(name=f'def_{self.guides[2].descriptor}', transform=self.larynx_ctrl.ctrl, connect=True, parent=self.jaw_joint)

        #constraint(drivers=[self.larynx_ctrl.ctrl, self.jaw_ctrl.ctrl], driven=self.larynx_joint, constraint_type='parent', parent=self.guts)

        jaw_info = module_info(control =self.jaw_ctrl, joint=self.jaw_joint)
        return jaw_info