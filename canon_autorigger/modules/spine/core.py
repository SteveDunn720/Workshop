from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.curve import GuideCurve
from Workshop.guide.core import GuideInfo, SplineGuideInfo, create_guide_from_position
from Workshop.transform.utils import create_transform, get_distance_between
from Workshop.maya_api.node import BlendColorsNode
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms
from Workshop.transform.matrix import matrix_constraint
from Workshop.skin.split.tag import tag_for_weight_split


from ..module_initialize import module_prep, module_space

from .utils import align_guides, curve_midpoint
from .simple_fk import build_simple_fk


@dataclass
class module_info:
    switch_joints:list
    bind_joints:list
    chest_ctrl:Control
    chest_off:Control

class Spine:
    def __init__(
        self,
        guides:SplineGuideInfo,
        part: str = "spine",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joint_parent:str = 'skel',
        simple_fk:bool = False,
        simple_ik:bool = False,
        hybrid:bool = True,
        divisions:int = 7,
        root_hook: list | None = None,
        control_space:list = [],
        hybrid_mid_shape:str = 'round_square',
        chest_des:str = 'chest',
        hip_shape:str = 'circle',
        hip_des:str = 'hip',
        cog_des:str = 'cog',
        chest_shape:str = 'chest',
        chest_off_shape:str = "hexagon",
    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides = guides
        self.joint_parent = joint_parent
        self.simple_fk = simple_fk
        self.simple_ik = simple_ik
        self.hybrid = hybrid
        self.divisions = divisions + 1
        self.root_hook = root_hook
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
        self.hybrid_mid_shape = hybrid_mid_shape
        self.chest_des = chest_des
        self.hip_des = hip_des
        self.cog_des = cog_des
        self.hip_shape = hip_shape
        self.chest_shape = chest_shape
        self.chest_off_shape = chest_off_shape


    # -------------------
    # Build steps
    # -------------------


    def build(self):

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        self.controls = []
        self.bind_joints = []
        split_joints = []
        self.switch_joints = []


        ##### Validate Spine Types ########
        if not self.hybrid and not self.simple_fk and not self.simple_ik:
            print('need at least one valid spine control type: reverting to hybrid spine')
            self.hybrid = True
             
 
        ##### Guide interpret from spine guide curve #######
        guide_names = []
        for i in range(self.divisions):
            guide_names.append(f'{self.part}_{self.side}_{i + 1:02d}')
        self.curve = GuideCurve(
                    curve= self.guides.curve.name, 
                    resample_amount=self.divisions,
                    output_names=guide_names,
                    ignore_handles=True,
                    align_normals=False,
                    primary_axis='+y'
        )
        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                align_guides(guide_01=guide, guide_02=self.curve.locator_list[i-1], flip_y=True)
            else:
                align_guides(guide_01=guide, guide_02=self.curve.locator_list[i+1])

        ########## Switch Joints #################
        jnt_par = self.guts
        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                break
            jnt = create_joint(name=f'switch_{guide.descriptor}', transform=guide.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.switch_joints.append(jnt)
            jnt_par = jnt

        ############ Chest Switch joints ###############
        self.chestswitch_joint = create_joint(name=f'switch_{self.chest_des}_{self.side}', transform=self.curve.locator_list[-1].name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
        self.switch_joints.append(self.chestswitch_joint)



        ############ def joints ################# 

        jnt_par = self.joint_parent
        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                            break
            jnt = create_joint(name=f'def_{guide.descriptor}', transform=guide.name, parent=jnt_par, connect=False)
            self.bind_joints.append(jnt)
            split_joints.append(jnt)
            jnt_par = jnt
            constraint(drivers=[self.switch_joints[i]], driven=jnt, constraint_type='parent', parent=self.guts)

        tag_for_weight_split(
            influence=self.bind_joints[0],  # <-- your SOURCE joint (must already exist)
            split_influences=split_joints,  # <-- the ones you just created
        )

        self.chest_joint = create_joint(name=f'def_{self.chest_des}_{self.side}', transform=self.curve.locator_list[-1].name, parent=jnt_par, connect=False)
        self.bind_joints.append(self.chest_joint)


        ############# chest controls #######################
        chest_offset = get_distance_between(self.guides.lower.name, self.guides.upper.name)
        self.chest = create_control(
            name=f'{self.chest_des}_{self.side}',
            parent=self.hybrid_grp ,
            transform=self.guides.lower.name,
            size=self.control_size/3,
            control_shape=self.chest_shape,
            direction="y",
            color_type=self.sub_control_color,
            shape_position_offset=(0,chest_offset + (self.control_size / 8),0)  
        )
        for attrs in ['X', 'Y', 'Z']:
            cmds.setAttr(f'{self.chest.top}.rotate{attrs}', 0)
        module_space(control=self.chest, space_list=self.control_space)
        self.chest_off = create_control(
            name=f'{self.chest_des}_off_{self.side}',
            parent=self.chest.ctrl,
            transform=self.guides.upper.name,
            size=self.control_size/3.5,
            control_shape=self.chest_off_shape,
            direction="y",
            color_type=self.main_control_color
        )
        ############ hip validation ############

        if self.root_hook:
            self.cog = self.root_hook[0]
            self.hip = self.root_hook[1]
        else:
            self.cog = create_control(
                name=f'{self.cog_des}_{self.side}',
                parent=self.control_grp,
                transform=self.guides.lower.name,
                size=self.control_size/5,
                control_shape=self.hip_shape,
                direction="y",
                color_type=self.main_control_color
            )
            self.hip = create_control(
                name=f'{self.hip_des}_{self.side}',
                parent=self.cog.ctrl,
                transform=self.guides.lower.name,
                size=self.control_size/4,
                control_shape=self.hip_shape,
                direction="y",
                color_type=self.main_control_color
            )

            
        

        ############# spine types ##########################

        if self.simple_fk:
            self.fk_joints = []
            self.fk_controls = []
            pass
            #build_simple_fk
            

        if self.hybrid:

            pass

        cmds.parentConstraint(self.hip.ctrl, self.mid_hip, maintainOffset=True)
        cmds.parentConstraint(self.chest_off.ctrl, self.mid_hip, maintainOffset=True)

        constraint(drivers=[self.chest_off.ctrl], driven=self.chestswitch_joint, constraint_type="parent")
        constraint(drivers=[self.chestswitch_joint], driven=self.chest_joint, constraint_type="parent", parent=self.guts)

        cmds.delete(self.curve.group)
        spine_info = module_info(switch_joints=self.switch_joints, bind_joints=self.bind_joints, chest_ctrl=self.chest, chest_off=self.chest_off)
        return spine_info