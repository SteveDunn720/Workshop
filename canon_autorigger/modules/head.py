from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import (
    ModuleGuide,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.guide.core import GuideInfo
from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint

from .module_shared import module_prep, module_space


@dataclass
class module_info:
    control: Control
    joint: str


class Head:
    MODULE_NAME = "head"
    DISPLAY_NAME = "Head"

    GUIDES = (ModuleGuide(name="head"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="control_shape", setting_type="control_shape", default="head"),
        ModuleSetting(name="control_size", setting_type="float", default=0.2),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="control_offset", setting_type="vector3", default=(0.0, 0.25, 0.0)),
        ModuleSetting(name="control_name", setting_type="string", default="skull"),
        ModuleSetting(name="joint_name", setting_type="string", default=""),
        ModuleSetting(name="control_color", setting_type="string", default=""),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        guides: GuideInfo,
        part: str = "head",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        joint_parent: str = "skel",
        control_space: list | None = None,
        control_shape: str = "head",
        control_size: float = 0.2,
        control_direction: str = "y",
        control_offset: tuple[float, float, float] = (0.0, 0.25, 0.0),
        control_name: str = "skull",
        joint_name: str | None = None,
        control_color: str | None = None,
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides
        self.joint_parent = joint_parent
        self.control_space = control_space if control_space is not None else []
        self.control_shape = control_shape
        self.control_size = control_size
        self.control_direction = control_direction
        self.control_offset = control_offset
        self.control_name = control_name
        self.joint_name = joint_name
        self.main_control_color = control_color or {
            "M": "Middle", "L": "Left", "R": "Right"
        }.get(side, "Right")

    @classmethod
    def preview(cls, part: str, side: str, guides: list[str], settings: dict) -> dict:
        if not guides:
            return {"controls": [], "joints": [], "output_control": None, "output_joint": None}
        control_name = settings.get("control_name", "skull")
        joint_name = settings.get("joint_name") or f"def_{part}_{side}"
        control = f"{control_name}_{side}_ctrl"
        joint = f"{joint_name}_jnt"
        return {
            "controls": [control], "joints": [joint],
            "output_control": control, "output_joint": joint,
        }

    def build(self) -> module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.head_ctrl = create_control(
            name=f"{self.control_name}_{self.side}",
            parent=self.control_grp,
            transform=self.guides.name,
            size=self.rig_size * self.control_size,
            control_shape=self.control_shape,
            direction=self.control_direction, #type:ignore
            color_type=self.main_control_color,
            shape_position_offset=tuple(value * self.rig_size for value in self.control_offset), #type:ignore
        )
        module_space(control=self.head_ctrl, space_list=self.control_space)

        self.head_joint = create_joint(
            name=self.joint_name or f"def_{self.part}_{self.side}",
            transform=self.head_ctrl.ctrl,
            connect=True,
            parent=self.joint_parent,
        )
        constraint(
            drivers=[self.head_ctrl.ctrl],
            driven=self.head_joint,
            constraint_type="parent",
            parent=self.guts,
        )
        return module_info(control=self.head_ctrl, joint=self.head_joint)
