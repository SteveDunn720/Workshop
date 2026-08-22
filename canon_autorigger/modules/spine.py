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

from .module_initialize import module_prep, module_space


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
        count:int = 7,
        root_hook: list | None = None,
        control_space:list = []
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


    # -------------------
    # Build steps
    # -------------------

    def curve_midpoint(self, curve: str) -> GuideInfo :
        pos = cmds.pointOnCurve(
            curve,
            parameter=0.5,
            position=True,
            turnOnPercentage=True,
        )

        mid_guide = create_guide_from_position(guide_name='mid_point', parent='guides', pos=tuple(pos))

        return mid_guide

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


    def spine_build(self):

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

        guide_names = []

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

        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                self.align_guides(guide_01=guide, guide_02=self.curve.locator_list[i-1], flip_y=True)
            else:
                self.align_guides(guide_01=guide, guide_02=self.curve.locator_list[i+1])

        jnt_par = self.guts

        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                break
            jnt = create_joint(name=f'switch_{guide.descriptor}', transform=guide.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.switch_joints.append(jnt)
            jnt_par = jnt

        self.chestswitch_joint = create_joint(name='switch_chest', transform=self.curve.locator_list[-1].name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
        self.switch_joints.append(self.chestswitch_joint)


        #fk/hybrid

        self.fk_joints = []
        self.fk_controls = []

        if self.simple_fk:
            jnt_par = self.guts
            ctrl_par = self.fk_control_grp
            for i,jnt in enumerate(self.curve.locator_list):
                ctrl = create_control(
                    name=f'FK_{jnt.descriptor}',
                    parent=ctrl_par,
                    transform=jnt.name,
                    size=self.control_size/4,
                    control_shape="circle",
                    direction="y",
                    color_type=self.main_control_color
                )

                fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par, bind_set= False, ue_set=False,)

                self.fk_joints.append(fk_jnt)
                self.fk_controls.append(ctrl)
                self.controls.append(ctrl.ctrl)
                jnt_par = fk_jnt
                ctrl_par = ctrl.ctrl

        else:

            self.hybrid_grp = create_transform(name=f'{self.part}_{self.side}_hyrbid_grp', parent=self.control_grp)

            if self.root_hook:
                self.hip = self.root_hook[1]
                self.cog = self.root_hook[0]
            else:
                self.hip = create_control(
                    name='hip',
                    parent=self.hybrid_grp,
                    transform=self.guides.lower.name,
                    size=self.control_size/4,
                    control_shape="circle",
                    direction="y",
                    color_type=self.main_control_color
                )
                self.cog = create_control(
                    name='cog',
                    parent=self.hybrid_grp,
                    transform=self.guides.lower.name,
                    size=self.control_size/5,
                    control_shape="circle",
                    direction="y",
                    color_type=self.main_control_color
                )

            self.mid_guide = self.curve_midpoint(curve=self.guides.curve.name)

            chest_offset = get_distance_between(self.guides.lower.name, self.guides.upper.name)

            self.mid_hip = create_transform(name='hip_mid_grp', parent=self.hybrid_grp, transform=self.hip.ctrl)
            self.mid = create_control(
                name='spine_mid',
                parent=self.mid_hip,
                transform=self.mid_guide.name,
                size=self.control_size/3,
                control_shape="round_square",
                direction="y",
                color_type=self.main_control_color
            )

            self.chest = create_control(
                name='chest',
                parent=self.hybrid_grp ,
                transform=self.guides.lower.name,
                size=self.control_size/3,
                control_shape="chest",
                direction="y",
                color_type=self.sub_control_color,
                shape_position_offset=(0,chest_offset + (self.control_size / 8),0)
            )


            for attrs in ['X', 'Y', 'Z']:
                cmds.setAttr(f'{self.chest.top}.rotate{attrs}', 0)

            module_space(control=self.chest, space_list=self.control_space)

            self.chest_off = create_control(
                name='chest_off',
                parent=self.chest.ctrl,
                transform=self.guides.upper.name,
                size=self.control_size/3.5,
                control_shape="hexagon",
                direction="y",
                color_type=self.main_control_color
            )

            self.spine_off_ctrls = []
            spine_driven = []


            for i, g in enumerate(self.curve.locator_list): 
                ctrl = create_control(
                        name=g.descriptor,
                        parent=self.hybrid_grp,
                        transform=g.name,
                        size=self.control_size/30,
                        control_shape="circle",
                        direction="z",
                        color_type=self.main_control_color,
                        shape_position_offset=(0,0,(self.control_size/4))
                    )
                self.spine_off_ctrls.append(ctrl)
                spine_driven.append(ctrl.top)
                matrix_constraint(constrain_transform=self.switch_joints[i], source_transform=ctrl.ctrl)

            

            cmds.parentConstraint(self.hip.ctrl, self.mid_hip, maintainOffset=True)
            cmds.parentConstraint(self.chest_off.ctrl, self.mid_hip, maintainOffset=True)


            matrix_spline_from_transforms(
                name=f"{self.side}_spine_ms",
                pinned_transforms=spine_driven,
                cv_transforms=[self.hip.ctrl, self.mid.ctrl, self.chest_off.ctrl],
                parent=self.guts,
                degree=2,
            )


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

            self.chest_joint = create_joint(name='def_chest', transform=self.curve.locator_list[-1].name, parent=jnt_par, connect=False)
            self.bind_joints.append(self.chest_joint)

            constraint(drivers=[self.chest_off.ctrl], driven=self.chestswitch_joint, constraint_type="parent")
            constraint(drivers=[self.chestswitch_joint], driven=self.chest_joint, constraint_type="parent")

        

        cmds.delete(self.curve.group)
        spine_info = module_info(switch_joints=self.switch_joints, bind_joints=self.bind_joints, chest_ctrl=self.chest, chest_off=self.chest_off)
        return spine_info