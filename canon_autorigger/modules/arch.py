from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.canon_autorigger.module_schema import ModuleCurveGuide, ModuleRelationship, ModuleSetting
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.guide.core import create_guide_from_position, create_midpoint_guide, mirror_guide
from Workshop.joint import create_joint
from Workshop.skin.split.tag import tag_for_weight_split
from Workshop.transform.constraint import constraint

from .module_shared import module_prep, module_space


@dataclass
class module_info:
    control: Control
    joint: str


class Arch:
    MODULE_NAME = "arch"
    DISPLAY_NAME = "Arch"
    GUIDES = (ModuleCurveGuide(name="arch"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="divisions", setting_type="int", default=2),
        ModuleSetting(name="main_control_size", setting_type="float", default=1 / 140),
        ModuleSetting(name="sub_control_size", setting_type="float", default=1 / 80),
        ModuleSetting(name="main_control_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="sub_control_shape", setting_type="control_shape", default="sphere"),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="main_control_rotation", setting_type="vector3", default=(90.0, 0.0, 0.0)),
        ModuleSetting(name="main_control_offset", setting_type="vector3", default=(1 / 6, 0.0, 0.0)),
        ModuleSetting(name="main_control_color", setting_type="string", default="Middle"),
        ModuleSetting(name="sub_middle_color", setting_type="string", default="SubMiddle"),
        ModuleSetting(name="sub_left_color", setting_type="string", default="SubLeft"),
        ModuleSetting(name="sub_right_color", setting_type="string", default="SubRight"),
        ModuleSetting(name="guide_parent", setting_type="string", default="guides"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        driver,
        divisions: int = 2,
        part: str = "arch",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        control_space: list | None = None,
        main_control_size: float = 1 / 140,
        sub_control_size: float = 1 / 80,
        main_control_shape: str = "round_square",
        sub_control_shape: str = "sphere",
        control_direction: str = "y",
        main_control_rotation: tuple[float, float, float] = (90.0, 0.0, 0.0),
        main_control_offset: tuple[float, float, float] = (1 / 6, 0.0, 0.0),
        main_control_color: str = "Middle",
        sub_middle_color: str = "SubMiddle",
        sub_left_color: str = "SubLeft",
        sub_right_color: str = "SubRight",
        guide_parent: str = "guides",
    ):
        self.driver = driver
        self.divisions = divisions
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.control_space = control_space if control_space is not None else []
        self.main_control_size = main_control_size
        self.sub_control_size = sub_control_size
        self.main_control_shape = main_control_shape
        self.sub_control_shape = sub_control_shape
        self.control_direction = control_direction
        self.main_control_rotation = main_control_rotation
        self.main_control_offset = main_control_offset
        self.main_M_color = main_control_color
        self.sub_M_color = sub_middle_color
        self.sub_L_color = sub_left_color
        self.sub_R_color = sub_right_color
        self.guide_parent = guide_parent

    def build(self) -> module_info:
        if self.divisions < 1:
            raise ValueError("Arch divisions must be at least 1")

        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        guides = []
        joints = []
        center_pos = cmds.pointOnCurve(
            self.guides[0].name, parameter=0, position=True, turnOnPercentage=True
        )
        guides.append(create_guide_from_position(
            guide_name=f"{self.part}_00_M", pos=center_pos, parent=self.guide_parent
        ))

        percent = 1 / self.divisions
        for i in range(self.divisions):
            pos = cmds.pointOnCurve(
                self.guides[0].name,
                parameter=percent * (i + 1),
                position=True,
                turnOnPercentage=True,
            )
            guide = create_guide_from_position(
                guide_name=f"{self.part}_0{i + 1}_L", pos=pos, parent=self.guide_parent
            )
            guides.append(guide)
            guides.append(mirror_guide(guide=guide))

        main_guide = create_midpoint_guide(
            guide_a=guides[-1], guide_b=guides[-2],
            position_only=True, name=f"{self.part}_main_M", parent=self.guide_parent,
        )
        self.main_ctrl = create_control(
            name=main_guide.descriptor,
            parent=self.control_grp,
            transform=main_guide.name,
            size=self.rig_size * self.main_control_size,
            control_shape=self.main_control_shape,
            direction=self.control_direction,
            color_type=self.main_M_color,
            shape_rotation_offset=self.main_control_rotation,
            shape_position_offset=tuple(value * self.rig_size for value in self.main_control_offset),
        )
        module_space(control=self.main_ctrl, space_list=self.control_space)
        self.main_joint = create_joint(
            name=f"def_{main_guide.descriptor}",
            transform=self.main_ctrl.ctrl,
            connect=True,
            parent=self.joint_parent,
        )

        for guide in guides:
            guide_side = next((s for s in ("L", "R", "M") if f"_{s}" in guide.name), None)
            color = {"L": self.sub_L_color, "R": self.sub_R_color}.get(guide_side, self.sub_M_color)
            ctrl = create_control(
                name=guide.descriptor,
                parent=self.main_ctrl.ctrl,
                transform=guide.name,
                size=self.rig_size * self.sub_control_size,
                control_shape=self.sub_control_shape,
                direction=self.control_direction,
                color_type=color,
            )
            joint = create_joint(
                name=f"def_{guide.descriptor}",
                transform=ctrl.ctrl,
                connect=True,
                parent=self.main_joint,
            )
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type="parent", parent=self.guts)
            joints.append(joint)

        sorted_joints = sorted(
            joints,
            key=lambda transform: cmds.xform(transform, query=True, worldSpace=True, translation=True)[0],
        )
        tag_for_weight_split(influence=joints[0], split_influences=sorted_joints)
        return module_info(control=self.main_ctrl, joint=self.main_joint)
