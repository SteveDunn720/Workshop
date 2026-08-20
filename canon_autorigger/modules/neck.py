from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo, SplineGuideInfo
from Workshop.guide.curve import GuideCurve
from Workshop.transform.utils import get_distance_between
from Workshop.maya_api.node import MultiplyDivideNode
from Workshop.skin.split.tag import tag_for_weight_split

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:list[Control]
    joint:list[str]

class Neck:
    def __init__(
        self,
        guides:SplineGuideInfo,
        part: str = "neck",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joint_parent:str = 'skel',
        control_space:list = [],
        simple_fk:bool=False,
        count:int=4

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides = guides
        self.joint_parent = joint_parent
        self.simple_fk = simple_fk
        self.count = count + 1
        if self.side == "M":
            self.main_control_color = 'Middle'
            self.sub_control_color = 'SubMiddle'
        elif self.side == "L":
            self.main_control_color = 'Left'
            self.sub_control_color = 'SubLeft'
        else:
            self.main_control_color = 'Right'
            self.sub_control_color = 'SubRight'
        self.control_space = control_space


    def align_guides(self, guide_01:GuideInfo, guide_02:GuideInfo, flip_y:bool=False):
            if guide_01.pos[2] > guide_02.pos[2]:
                mod = -1
            else:
                mod = 1
            ymod = -1 if flip_y else 1
    
            aim = cmds.aimConstraint(
                    guide_02.name,
                    guide_01.name,
                    aimVector=(0, 1 * ymod, 0),      # Primary / aim axis = +X
                    upVector=(0, 0, -1 * mod),       # Up axis = +Y
                    worldUpType="vector",
                    worldUpVector=(0, 1, 0),
                    maintainOffset=False
                )
    
            cmds.delete(aim)

    # -------------------
    # Build steps
    # -------------------

    def neck_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.controls = []
        self.bind_joints = []
        self.switch_joints = []

        defjnt_par=self.joint_parent
        control_par = self.control_grp

        guide_names = []

        offset = get_distance_between(self.guides.lower.name, self.guides.upper.name)

        self.roll_ctrl = create_control(
            name=f'autohead_{self.side}',
            parent=self.control_grp,
            transform=self.guides.lower.name,
            size=self.control_size/5,
            control_shape="round_square",
            direction="y",
            color_type=self.sub_control_color,
            shape_position_offset=(0, offset * 1.5, 0),
            shape_rotation_offset=(90,0,0)
        )

        for attrs in ['X', 'Y', 'Z']:
            cmds.setAttr(f'{self.roll_ctrl.top}.rotate{attrs}', 0)
        module_space(control=self.roll_ctrl, space_list=[self.control_space])
        self.rot_mult = MultiplyDivideNode(name='neck_rot_mult')
        self.trans_mult = MultiplyDivideNode(name='neck_trans_mult')
        self.rot_mult.input2.set((self.count/10,self.count/10,self.count/10))
        self.trans_mult.input2.set((self.count/10,self.count/10,self.count/10))
        self.rot_mult.input1.connect_from(f'{self.roll_ctrl.ctrl}.rotate')
        self.trans_mult.input1.connect_from(f'{self.roll_ctrl.ctrl}.translate')


        for i in range(self.count):
            guide_names.append(f'{self.part}_{self.side}_{i + 1:02d}')


        self.curve = GuideCurve(
                    curve= self.guides.curve.name, 
                    resample_amount=self.count,
                    output_names=guide_names,
                    ignore_handles=True,
                    align_normals=False,
                    primary_axis='+y'
        )

        jnt_par = self.guts

        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                self.align_guides(guide_01=guide, guide_02=self.curve.locator_list[i-1], flip_y=True)
                break
            else:
                self.align_guides(guide_01=guide, guide_02=self.curve.locator_list[i+1])

            jnt = create_joint(name=f'switch_{guide.descriptor}', transform=guide.name, parent=jnt_par, connect=False)
            self.switch_joints.append(jnt)
            jnt_par = jnt

            #controls
            ctrl = create_control(
                name=guide.descriptor,
                parent=control_par,
                transform=guide.name,
                size=self.control_size/8,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color,
                sdk_offset=True
            )
            self.controls.append(ctrl)
            control_par=ctrl.ctrl


            self.rot_mult.output.connect_to(f'{ctrl.sdk}.rotate')
            self.trans_mult.output.connect_to(f'{ctrl.sdk}.translate')

            defjnt = create_joint(name=f'def_{guide.descriptor}', transform=guide.name, parent=defjnt_par, connect=False)
            self.bind_joints.append(defjnt)
            defjnt_par = defjnt

            constraint(drivers=[ctrl.ctrl], driven=jnt, constraint_type='parent', parent=self.guts)
            constraint(drivers=[jnt], driven=defjnt, constraint_type='parent', parent=self.guts)

        module_space(control=self.controls[0], space_list=self.control_space)
        tag_for_weight_split(
            influence=self.bind_joints[0],  # <-- your SOURCE joint (must already exist)
            split_influences=self.bind_joints,  # <-- the ones you just created
        )

        #joints
        cmds.delete(self.curve.group)


        neck_info = module_info(control =self.controls, joint=self.bind_joints,)
        return neck_info