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

from ..module_shared import create_module_switch
from ..module_initialize import module_prep, module_space

from .utils import align_guides, curve_midpoint
from .simple_fk import build_simple_fk
from .hybrid import build_hybrid

from Workshop.canon_autorigger.module_schema import (
    ModuleCurveGuide,
    ModuleSetting,
    ModuleRelationship,
    ModuleGuide,
    ModuleSplineGuide
)


@dataclass
class module_info:
    switch_joints:list
    bind_joints:list
    chest_ctrl:Control
    chest_off:Control

class Spine:

    MODULE_NAME = "spine"
    DISPLAY_NAME = "Spine"

    # -----------------------------------
    # Guides
    # -----------------------------------

    GUIDES = (
        ModuleSplineGuide(
            name="spine",
            lower_name="spine_lower",
            upper_name="spine_upper",
            length=10.0,
        ),
    )

    # -----------------------------------
    # Settings
    # -----------------------------------

    SETTINGS = (

        # General

        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),

        ModuleSetting(
            name="divisions",
            setting_type="int",
            default=7,
        ),

        # Spine Types

        ModuleSetting(
            name="simple_fk",
            setting_type="bool",
            default=False,
        ),

        ModuleSetting(
            name="simple_ik",
            setting_type="bool",
            default=False,
        ),

        ModuleSetting(
            name="hybrid",
            setting_type="bool",
            default=True,
        ),

        # Control Descriptors

        ModuleSetting(
            name="chest_des",
            setting_type="string",
            default="chest",
        ),

        ModuleSetting(
            name="hip_des",
            setting_type="string",
            default="hip",
        ),

        ModuleSetting(
            name="cog_des",
            setting_type="string",
            default="cog",
        ),

        # Control Shapes

        ModuleSetting(
            name="chest_shape",
            setting_type="control_shape",
            default="chest",
        ),

        ModuleSetting(
            name="chest_off_shape",
            setting_type="control_shape",
            default="hexagon",
        ),

        ModuleSetting(
            name="hip_shape",
            setting_type="control_shape",
            default="circle",
        ),

        ModuleSetting(
            name="cog_shape",
            setting_type="control_shape",
            default="circle",
        ),

        ModuleSetting(
            name="hybrid_mid_shape",
            setting_type="control_shape",
            default="round_square",
        ),

        # Control Sizes

        ModuleSetting(
            name="chest_rig_size",
            setting_type="float",
            default=1 / 3,
        ),

        ModuleSetting(
            name="chest_off_rig_size",
            setting_type="float",
            default=1 / 3.5,
        ),

        ModuleSetting(
            name="cog_rig_size",
            setting_type="float",
            default=1 / 5,
        ),

        ModuleSetting(
            name="hip_rig_size",
            setting_type="float",
            default=1 / 4,
        ),

        ModuleSetting(
            name="hybrid_mid_rig_size",
            setting_type="float",
            default=1 / 3,
        ),

        ModuleSetting(
            name="hybrid_sub_rig_size",
            setting_type="float",
            default=1 / 30,
        ),

        # Control Offsets

        ModuleSetting(
            name="chest_control_pos_offset",
            setting_type="vector3",
            default=(0.0, 0.125, 0.0),
        ),

        ModuleSetting(
            name="hybrid_sub_control_pos_offset",
            setting_type="vector3",
            default=(0.0, 0.0, 0.25),
        ),
    )

    # -----------------------------------
    # Relationships
    # -----------------------------------

    RELATIONSHIPS = (

        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),

        ModuleRelationship(
            name="control_space",
            relationship_type="control_space",
            default="auto",
        ),

        ModuleRelationship(
            name="control_parent",
            relationship_type="control",
            default="auto",
        ),
    )

    def __init__(
        self,
        guides:SplineGuideInfo,
        part: str = "spine",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
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
        chest_rig_size:float = 1/3,
        chest_control_pos_offset:tuple = (0, 1/8 ,0) , 
        chest_off_rig_size:float = 1/3.5,
        cog_rig_size:float = 1/5,
        hip_rig_size:float = 1/4,
        hyrbid_mid_rig_size:float = 1/3,
        hybrid_sub_size:float = 1/30,
        hybrid_sub_offset:tuple = (0,0,1/4)
    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
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
        self.chest_rig_size = chest_rig_size
        self.chest_control_pos_offset = chest_control_pos_offset
        self.chest_off_rig_size = chest_off_rig_size
        self.cog_rig_size = cog_rig_size
        self.hip_rig_size = hip_rig_size
        self.hyrbid_mid_rig_size = hyrbid_mid_rig_size
        self.hybrid_sub_size = hybrid_sub_size
        self.hybrid_sub_offset = hybrid_sub_offset 




    # -------------------
    # Build steps
    # -------------------

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:
        """
        Predict the controls and joints created by the Spine module.

        This does not create Maya nodes.

        Args:
            part:
                Module descriptor.

            side:
                Module side (M, L, R).

            guides:
                Guide references assigned to this module.

            settings:
                Module setting overrides.

        Returns:
            Dictionary containing predicted controls, joints,
            and primary module outputs.
        """

        # -----------------------------------
        # Empty Guide Validation
        # -----------------------------------

        if not guides:
            return {
                "controls": [],
                "joints": [],
                "output_control": None,
                "output_joint": None,
            }

        # -----------------------------------
        # Resolve Settings
        # -----------------------------------

        defaults = {
            setting.name: setting.default
            for setting in cls.SETTINGS
        }

        defaults.update(settings or {})

        divisions = int(defaults["divisions"])

        simple_fk = defaults["simple_fk"]
        simple_ik = defaults["simple_ik"]
        hybrid = defaults["hybrid"]

        chest_des = defaults["chest_des"]
        hip_des = defaults["hip_des"]
        cog_des = defaults["cog_des"]

        # Match the fallback behavior in build()

        if not any((simple_fk, simple_ik, hybrid)):
            hybrid = True

        # -----------------------------------
        # Shared Controls
        # -----------------------------------

        chest_control = f"{chest_des}_{side}_ctrl"
        chest_off_control = f"{chest_des}_off_{side}_ctrl"

        cog_control = f"{cog_des}_{side}_ctrl"
        hip_control = f"{hip_des}_{side}_ctrl"

        controls = [
            chest_control,
            chest_off_control,
            cog_control,
            hip_control,
        ]

        # -----------------------------------
        # Shared Joints
        # -----------------------------------

        joints = []

        # The build creates divisions + 1 guide positions.
        # The final position becomes the chest joint.

        guide_count = divisions + 1

        for index in range(guide_count - 1):

            descriptor = (
                f"{part}_{side}_{index + 1:02d}"
            )

            switch_joint = (
                f"switch_{descriptor}_jnt"
            )

            bind_joint = (
                f"def_{descriptor}_jnt"
            )

            joints.extend([
                switch_joint,
                bind_joint,
            ])

        # Final chest joints

        chest_switch_joint = (
            f"switch_{chest_des}_{side}_jnt"
        )

        chest_bind_joint = (
            f"def_{chest_des}_{side}_jnt"
        )

        joints.extend([
            chest_switch_joint,
            chest_bind_joint,
        ])

        # -----------------------------------
        # Hybrid Spine
        # -----------------------------------

        if hybrid:

            mid_control = (
                f"{part}_mid_{side}_ctrl"
            )

            controls.append(mid_control)

            # Hybrid creates one control and joint
            # for every resampled guide position.

            for index in range(guide_count):

                descriptor = (
                    f"{part}_{side}_{index + 1:02d}"
                )

                sub_control = (
                    f"{descriptor}_ctrl"
                )

                hybrid_joint = (
                    f"Hybrid_{descriptor}_jnt"
                )

                controls.append(sub_control)
                joints.append(hybrid_joint)

        # -----------------------------------
        # Simple FK
        # -----------------------------------

        if simple_fk:
            # TODO:
            # Add FK controls and joints when
            # build_simple_fk() is implemented.
            pass

        # -----------------------------------
        # Simple IK
        # -----------------------------------

        if simple_ik:
            # TODO:
            # Add IK controls and joints when
            # build_simple_ik() is implemented.
            pass

        # -----------------------------------
        # Return Preview
        # -----------------------------------

        return {
            "controls": controls,
            "joints": joints,
            "output_control": chest_off_control,
            "output_joint": chest_bind_joint,
        }


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
        drivers = {}


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
        constraint(
            drivers=[self.chestswitch_joint],
            driven=self.chest_joint,
            constraint_type="parent",
            parent=self.guts,
        )

        ############# chest controls #######################
        chest_offset = get_distance_between(self.guides.lower.name, self.guides.upper.name)
        self.chest = create_control(
            name=f'{self.chest_des}_{self.side}',
            parent=self.control_grp ,
            transform=self.guides.lower.name,
            size=self.rig_size * self.chest_rig_size,
            control_shape=self.chest_shape,
            direction="y",
            color_type=self.sub_control_color,
            shape_position_offset=tuple(
                            value * self.rig_size + addition
                            for value, addition in zip(
                                self.chest_control_pos_offset,
                                (0, chest_offset, 0),
                                strict=True,
                            )
            )
        )
        for attrs in ['X', 'Y', 'Z']:
            cmds.setAttr(f'{self.chest.top}.rotate{attrs}', 0)
        module_space(control=self.chest, space_list=self.control_space)
        self.chest_off = create_control(
            name=f'{self.chest_des}_off_{self.side}',
            parent=self.chest.ctrl,
            transform=self.guides.upper.name,
            size=self.rig_size * self.chest_off_rig_size,
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
                size=self.rig_size * self.cog_rig_size,
                control_shape=self.hip_shape,
                direction="y",
                color_type=self.main_control_color
            )
            self.hip = create_control(
                name=f'{self.hip_des}_{self.side}',
                parent=self.cog.ctrl,
                transform=self.guides.lower.name,
                size=self.rig_size * self.hip_rig_size,
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
            hyrbid = build_hybrid(part=self.part, guts=self.guts, side=self.side, control_grp=self.control_grp, guide_curve=self.curve, guide_list=self.curve.locator_list, cv_transforms=[self.hip.ctrl, self.chest_off.ctrl,],  rig_size=self.rig_size, hip=self.hip, hip_des=self.hip_des, hybrid_mid_shape=self.hybrid_mid_shape, main_color=self.main_control_color, mid_rig_size = self.hyrbid_mid_rig_size, sub_spine_rig_size = self.hybrid_sub_size, sub_offset =self.hybrid_sub_offset)
            constraint(drivers=[self.hip.ctrl, self.chest_off.ctrl], driven=hyrbid.mid.top, constraint_type='parent', maintain_offset=True)

            #cmds.parentConstraint(self.hip.ctrl, hyrbid.mid.top, maintainOffset=True)
            #cmds.parentConstraint(self.chest_off.ctrl, hyrbid.mid.top, maintainOffset=True)
            #chest_jnt = create_joint(name=f'Hybrid_{self.chest_des}_{self.side}', transform=self.chest_off.ctrl, parent=jnt_par, bind_set= False, ue_set=False,)
            #constraint(drivers=[self.chest_off.ctrl], driven=self.chestswitch_joint, constraint_type="parent")
            #constraint(drivers=[self.chestswitch_joint], driven=self.chest_joint, constraint_type="parent", parent=self.guts)

            drivers["Hybrid"] = {
                "joints": hyrbid.joints,
                "visibility": [hyrbid.grp],
            }

        self.spine_switch = create_module_switch(
            driven=self.switch_joints,
            drivers=drivers,
            node_attr=self.chest.ctrl,
            descriptor=f"{self.part}_{self.side}",
        )

        cmds.delete(self.curve.group)
        spine_info = module_info(switch_joints=self.switch_joints, bind_joints=self.bind_joints, chest_ctrl=self.chest, chest_off=self.chest_off)
        return spine_info