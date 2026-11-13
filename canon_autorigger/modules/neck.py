from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.maya_api.attribute_utils import set_attribute
from Workshop.canon_autorigger.build_management.dev import create_dev_attribute
from Workshop.canon_autorigger.module_schema import (
    ModuleRelationship, ModuleSetting, ModuleSplineGuide,
)
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo, SplineGuideInfo
from Workshop.guide.curve import GuideCurve
from Workshop.transform.utils import get_distance_between
from Workshop.maya_api.node import MultiplyDivideNode
from Workshop.skin.split.tag import tag_for_weight_split

from .module_shared import module_prep, module_space


@dataclass
class module_info:
    control:list[Control]
    joint:list[str]

class Neck:
    MODULE_NAME = "neck"
    DISPLAY_NAME = "Neck"
    GUIDES = (ModuleSplineGuide(name="neck"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="simple_fk", setting_type="bool", default=False),
        ModuleSetting(name="divisions", setting_type="int", default=4),
        ModuleSetting(name="roll_control_name", setting_type="string", default="autohead"),
        ModuleSetting(name="roll_control_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="main_control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="roll_control_size_scale", setting_type="float", default=0.2),
        ModuleSetting(name="main_control_size_scale", setting_type="float", default=0.125),
        ModuleSetting(name="roll_shape_offset_scale", setting_type="float", default=1.5),
        ModuleSetting(name="roll_shape_rotation", setting_type="vector3", default=(90, 0, 0)),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="follow_divisor", setting_type="float", default=10.0),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        guides:SplineGuideInfo,
        part: str = "neck",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        joint_parent:str = 'skel',
        control_space:list | None = None,
        simple_fk:bool=False,
        divisions:int=4,
        roll_control_name: str = "autohead",
        roll_control_shape: str = "round_square",
        main_control_shape: str = "circle",
        roll_control_size_scale: float = 0.2,
        main_control_size_scale: float = 0.125,
        roll_shape_offset_scale: float = 1.5,
        roll_shape_rotation: tuple[float, float, float] = (90, 0, 0),
        control_direction: str = "y",
        follow_divisor: float = 10.0,

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides = guides
        self.joint_parent = joint_parent
        self.simple_fk = simple_fk
        if divisions < 1:
            raise ValueError("Neck divisions must be at least 1")
        if follow_divisor == 0:
            raise ValueError("follow_divisor must be non-zero")
        self.divisions = divisions + 1
        self.roll_control_name = roll_control_name
        self.roll_control_shape = roll_control_shape
        self.main_control_shape = main_control_shape
        self.roll_control_size_scale = roll_control_size_scale
        self.main_control_size_scale = main_control_size_scale
        self.roll_shape_offset_scale = roll_shape_offset_scale
        self.roll_shape_rotation = roll_shape_rotation
        self.control_direction = control_direction
        self.follow_divisor = follow_divisor
        if self.side == "M":
            self.main_control_color = 'Middle'
            self.sub_control_color = 'SubMiddle'
        elif self.side == "L":
            self.main_control_color = 'Left'
            self.sub_control_color = 'SubLeft'
        else:
            self.main_control_color = 'Right'
            self.sub_control_color = 'SubRight'
        self.control_space = control_space if control_space is not None else []


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

    def build(self)->module_info:

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
            name=f'{self.roll_control_name}_{self.side}',
            parent=self.control_grp,
            transform=self.guides.lower.name,
            size=self.rig_size * self.roll_control_size_scale,
            control_shape=self.roll_control_shape,
            direction=self.control_direction,
            color_type=self.sub_control_color,
            shape_position_offset=(0, offset * self.roll_shape_offset_scale, 0),
            shape_rotation_offset=self.roll_shape_rotation
        )

        mult = (self.divisions / 2) / self.follow_divisor

        for attrs in ['X', 'Y', 'Z']:
            set_attribute(f'{self.roll_ctrl.top}.rotate{attrs}', 0)
        module_space(control=self.roll_ctrl, space_list=[self.control_space])
        self.rot_mult = MultiplyDivideNode(name='neck_rot_mult')
        self.trans_mult = MultiplyDivideNode(name='neck_trans_mult')
        # The original computed multiplier becomes an editable rig-time parameter.
        rot_follow = create_dev_attribute(
            attribute_name=f"{self.part}_{self.side}_rotation_follow",
            control=self.roll_ctrl.ctrl,
            rig_part=self.part,
            default=mult,
            attr_type="double",
        )
        trans_follow = create_dev_attribute(
            attribute_name=f"{self.part}_{self.side}_translation_follow",
            control=self.roll_ctrl.ctrl,
            rig_part=self.part,
            default=mult,
            attr_type="double",
        )
        for axis in "xyz":
            # Both follow attributes drive all three multiplier components.
            getattr(self.rot_mult.input2, axis).connect_from(rot_follow)
            getattr(self.trans_mult.input2, axis).connect_from(trans_follow)
        self.rot_mult.input1.connect_from(f'{self.roll_ctrl.ctrl}.rotate')
        self.trans_mult.input1.connect_from(f'{self.roll_ctrl.ctrl}.translate')


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

        jnt_par = self.guts

        for i, guide in enumerate(self.curve.locator_list):
            if guide == self.curve.locator_list[-1]:
                self.align_guides(guide_01=guide, guide_02=self.curve.locator_list[i-1], flip_y=True)
                break
            else:
                self.align_guides(guide_01=guide, guide_02=self.curve.locator_list[i+1])

            jnt = create_joint(name=f'switch_{guide.descriptor}', transform=guide.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.switch_joints.append(jnt)
            jnt_par = jnt

            #controls
            ctrl = create_control(
                name=guide.descriptor,
                parent=control_par,
                transform=guide.name,
                size=self.rig_size * self.main_control_size_scale,
                control_shape=self.main_control_shape,
                direction=self.control_direction,
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