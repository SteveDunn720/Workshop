from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.canon_autorigger.module_schema import ModuleGuide, ModuleRelationship, ModuleSetting
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.guide.core import GuideInfo
from Workshop.joint import create_joint
from Workshop.maya_api.attribute_utils import add_proxy
from Workshop.transform.constraint import constraint

from .ik import auto_pv_space
from .module_shared import fkik_switch, module_prep, module_space


@dataclass
class module_info:
    fk_control: Control
    ik_control: Control
    switch: str
    joint: str


class Hand:
    MODULE_NAME = "hand"
    DISPLAY_NAME = "Hand"
    GUIDES = (ModuleGuide(name="hand"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="fk_control_shape", setting_type="control_shape", default="fk"),
        ModuleSetting(name="ik_control_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="ik_offset_shape", setting_type="control_shape", default="triangle"),
        ModuleSetting(name="prop_shape", setting_type="control_shape", default="cube"),
        ModuleSetting(name="fk_control_size", setting_type="float", default=1 / 6),
        ModuleSetting(name="ik_control_size", setting_type="float", default=1 / 4),
        ModuleSetting(name="ik_offset_size", setting_type="float", default=1 / 16),
        ModuleSetting(name="prop_control_size", setting_type="float", default=1 / 32),
        ModuleSetting(name="ik_offset_position", setting_type="vector3", default=(0.0, 0.0, -0.4)),
        ModuleSetting(name="prop_position", setting_type="vector3", default=(0.1, 0.0, 0.0)),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="fk_control_name", setting_type="string", default=""),
        ModuleSetting(name="ik_control_name", setting_type="string", default=""),
        ModuleSetting(name="ik_offset_name", setting_type="string", default=""),
        ModuleSetting(name="prop_control_name", setting_type="string", default=""),
        ModuleSetting(name="main_control_color", setting_type="string", default=""),
        ModuleSetting(name="sub_control_color", setting_type="string", default=""),
        ModuleSetting(name="auto_pv_angle_range", setting_type="vector2", default=(-90.0, 90.0)),
        ModuleSetting(name="auto_pv_distance", setting_type="float", default=0.1),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="fk_control_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="ik_control_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="fk_hook", relationship_type="transform", default="auto"),
        ModuleRelationship(name="ik_hook", relationship_type="transform", default="auto"),
    )

    def __init__(
        self,
        arm_info,
        guides: GuideInfo,
        joint_parent: str,
        part: str = "hand",
        side: str = "L",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        fk_control_space: list | None = None,
        ik_control_space: list | None = None,
        ik_hook: list | None = None,
        fkik_switch_attr: str = "",
        fk_hook: str = "",
        ik_control_shape: str = "round_square",
        ik_offset_shape: str = "triangle",
        fk_control_shape: str = "fk",
        prop_shape: str = "cube",
        fk_control_size: float = 1 / 6,
        ik_control_size: float = 1 / 4,
        ik_offset_size: float = 1 / 16,
        prop_control_size: float = 1 / 32,
        ik_offset_position: tuple[float, float, float] = (0.0, 0.0, -0.4),
        prop_position: tuple[float, float, float] = (0.1, 0.0, 0.0),
        control_direction: str = "y",
        fk_control_name: str | None = None,
        ik_control_name: str | None = None,
        ik_offset_name: str | None = None,
        prop_control_name: str | None = None,
        main_control_color: str | None = None,
        sub_control_color: str | None = None,
        auto_pv_angle_range: tuple[float, float] = (-90.0, 90.0),
        auto_pv_distance: float = 0.1,
    ):
        self.arm_info = arm_info
        self.guides = guides
        self.joint_parent = joint_parent
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.fk_control_space = fk_control_space if fk_control_space is not None else []
        self.ik_control_space = ik_control_space if ik_control_space is not None else []
        self.ik_hook = ik_hook if ik_hook is not None else []
        self.fkik_switch_attr = fkik_switch_attr
        self.fk_hook = fk_hook
        self.ik_control_shape = ik_control_shape
        self.ik_offset_shape = ik_offset_shape
        self.fk_control_shape = fk_control_shape
        self.prop_shape = prop_shape
        self.fk_control_size = fk_control_size
        self.ik_control_size = ik_control_size
        self.ik_offset_size = ik_offset_size
        self.prop_control_size = prop_control_size
        self.ik_offset_position = ik_offset_position
        self.prop_position = prop_position
        self.control_direction = control_direction
        self.fk_control_name = fk_control_name or f"FK_{part}_{side}"
        self.ik_control_name = ik_control_name or f"IK_{part}_{side}"
        self.ik_offset_name = ik_offset_name or f"IK_{part}_off_{side}"
        self.prop_control_name = prop_control_name or f"prop_{side}"
        self.main_control_color = main_control_color or ("Left" if side == "L" else "Right")
        self.sub_control_color = sub_control_color or ("SubLeft" if side == "L" else "SubRight")
        self.auto_pv_angle_range = auto_pv_angle_range
        self.auto_pv_distance = auto_pv_distance

    @classmethod
    def preview(cls, part: str, side: str, guides: list[str], settings: dict) -> dict:
        if not guides:
            return {"controls": [], "joints": [], "output_control": None, "output_joint": None}
        fk = settings.get("fk_control_name") or f"FK_{part}_{side}"
        ik = settings.get("ik_control_name") or f"IK_{part}_{side}"
        ik_off = settings.get("ik_offset_name") or f"IK_{part}_off_{side}"
        prop = settings.get("prop_control_name") or f"prop_{side}"
        joints = [f"def_{part}_{side}_jnt"]
        controls = [f"{name}_ctrl" for name in (fk, ik, ik_off, prop)]
        return {"controls": controls, "joints": joints, "output_control": controls[2], "output_joint": joints[0]}

    def build(self) -> module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        self.controls = []
        self.switch_joints = []
        switch_jnt = create_joint(
            name=f"switch_{self.part}_{self.side}", transform=self.guides.name,
            parent=self.guts, connect=False, bind_set=False, ue_set=False,
        )
        self.switch_joints.append(switch_jnt)

        self.fk_controls = []
        self.fk_joints = []
        fk_ctrl = create_control(
            name=self.fk_control_name, parent=self.fk_control_grp,
            transform=self.guides.name, size=self.rig_size * self.fk_control_size,
            control_shape=self.fk_control_shape, direction=self.control_direction,
            color_type=self.main_control_color,
        )
        fk_jnt = create_joint(
            name=f"FK_{self.part}_{self.side}", transform=fk_ctrl.ctrl,
            parent=self.guts, bind_set=False, ue_set=False,
        )
        constraint(drivers=[fk_ctrl.ctrl], driven=self.fk_hook)
        self.fk_controls.append(fk_ctrl)
        self.fk_joints.append(fk_jnt)
        self.controls.append(fk_ctrl.ctrl)
        module_space(space_list=self.fk_control_space, control=fk_ctrl)

        self.ik_joints = []
        self.ik_controls = []
        ik_jnt = create_joint(
            name=f"IK_{self.part}_{self.side}", transform=self.guides.name,
            parent=self.guts, connect=False, bind_set=False, ue_set=False,
        )
        self.ik_joints.append(ik_jnt)
        self.ik_hand_piv = create_control(
            name=self.ik_control_name, parent=self.ik_control_grp,
            transform=self.guides.name, size=self.rig_size * self.ik_control_size,
            control_shape=self.ik_control_shape, direction=self.control_direction,
            color_type=self.sub_control_color,
        )
        self.ik_controls.append(self.ik_hand_piv)
        self.controls.append(self.ik_hand_piv)
        self.ik_hand = create_control(
            name=self.ik_offset_name, parent=self.ik_hand_piv.ctrl,
            transform=self.guides.name, size=self.rig_size * self.ik_offset_size,
            control_shape=self.ik_offset_shape, direction=self.control_direction,
            color_type=self.main_control_color,
            shape_position_offset=tuple(value * self.rig_size for value in self.ik_offset_position),
            shape_rotation_offset=(0, 0, 0),
        )
        self.ik_controls.append(self.ik_hand)
        self.controls.append(self.ik_hand)
        module_space(space_list=self.ik_control_space, control=self.ik_hand_piv)

        self.FK_IK_Switch = fkik_switch(
            controls=self.controls, node_attr=self.main_grp, descriptor=self.part,
            fk_grp=self.fk_control_grp, ik_grp=self.ik_control_grp,
            fk_joints=self.fk_joints, ik_joints=self.ik_joints,
            switch_joints=self.switch_joints, connect_switch_attr=self.fkik_switch_attr,
        )

        self.prop = create_control(
            name=self.prop_control_name, parent=self.control_grp,
            transform=self.guides.name, size=self.rig_size * self.prop_control_size,
            control_shape=self.prop_shape, direction=self.control_direction,
            color_type=self.main_control_color,
            shape_position_offset=tuple(value * self.rig_size for value in self.prop_position),
        )
        constraint(drivers=[self.switch_joints[0]], driven=self.prop.top, constraint_type="parent", parent=self.guts)
        self.controls.append(self.prop)

        constraint(drivers=[self.ik_hand.ctrl], driven=self.ik_hook[0], constraint_type="parent", parent=self.guts)
        constraint(drivers=[self.ik_hook[1]], driven=self.ik_joints[0], constraint_type="parent", parent=self.guts)
        constraint(drivers=[self.ik_hand.ctrl], driven=self.ik_hook[2], constraint_type="parent", parent=self.guts)
        add_proxy(source=f"{self.ik_hook[2]}.stretch", proxy_list=[self.ik_hand.ctrl], proxy_name="stretch")

        self.bind_jnt = create_joint(
            name=f"def_{self.part}_{self.side}", transform=self.guides.name,
            parent=self.joint_parent, connect=False,
        )
        constraint(driven=self.bind_jnt, drivers=self.switch_joints[0], constraint_type="parent", parent=self.guts)

        if self.arm_info.auto_pv_driven:
            pv_distance = self.rig_size * self.auto_pv_distance
            pv_auto = auto_pv_space(
                end_control=self.ik_hand, pv_control=self.arm_info.ik_controls[1],
                parent_space=self.ik_control_space[0], parent=self.guts,
                swing_range=(self.auto_pv_angle_range, (-pv_distance, pv_distance)),
            )
            cmds.parent(self.arm_info.auto_pv_driven, pv_auto.driver)

        return module_info(
            fk_control=self.fk_controls[0], ik_control=self.ik_controls[1],
            switch=self.switch_joints[0], joint=self.bind_jnt,
        )
