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

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:Control
    joint:str

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
        self.count = count
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
        self.switch_joints = []

        guide_names = []

        for i in range(self.count):
            guide_names.append(f'{self.part}_{self.side}_{i + 1:02d}')

        self.curve = GuideCurve(
                    curve= self.guides.curve.name, 
                    resample_amount=self.count,
                    output_names=guide_names,
                    ignore_handles=True,
                    align_normals=True,
        )

        jnt_par = self.guts

        for i, guide in enumerate(self.curve.locator_list):
            jnt = create_joint(name=f'Switch_{guide.descriptor}', transform=guide.name, parent=jnt_par)
            self.switch_joints.append(jnt)
            jnt_par = jnt


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

                fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par)

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
                size=self.control_size/2,
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

            

            """blend_rotate = BlendColorsNode(name='spine_translate_blend')

            blend_rotate.color1.connect_from(f'{self.cog.ctrl}.rotate')
            blend_rotate.color2.connect_from(f'{self.chest.ctrl}.rotate')
            blend_rotate.output.connect_to(f"{self.mid_hip}.rotate")

            blend_rotate.output.r.connect_to(f"{self.mid.ctrl}.rotateX")
            blend_rotate.output.b.connect_to(f"{self.mid.ctrl}.rotateZ")"""

            cmds.parentConstraint(self.hip.ctrl, self.mid_hip, maintainOffset=True)
            cmds.parentConstraint(self.chest_off.ctrl, self.mid_hip, maintainOffset=True)



            










        """jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.guides):
            if not self.ik_end_control and i == len(self.guides) - 1:
                continue
            ctrl = create_control(
                name=f'FK_{jnt.descriptor}',
                parent=ctrl_par,
                transform=jnt.name,
                size=self.control_size/4,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color
            )

            fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par)

            self.fk_joints.append(fk_jnt)
            self.fk_controls.append(ctrl)
            self.controls.append(ctrl.ctrl)
            jnt_par = fk_jnt
            ctrl_par = ctrl.ctrl"""
















        
        #self.spine_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.spine_ctrl.ctrl, connect=True, parent=self.joint_parent)

        #constraint(drivers=[self.spine_ctrl.ctrl], driven=self.spine_joint, constraint_type='parent', parent=self.guts)

        #spine_info = module_info(control =self.spine_ctrl, joint=self.spine_joint)
        #return spine_info