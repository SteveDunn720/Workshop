from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import (
    ModuleGuide,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint

from .module_shared import module_prep, module_space


@dataclass
class module_info:
    cog_control: Control
    hip_control: Control
    hip_joint: str


class Hip:
    MODULE_NAME = "hip"
    DISPLAY_NAME = "Hip"

    GUIDES = (ModuleGuide(name="pelvis"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="cog_control_shape", setting_type="control_shape", default="COG"),
        ModuleSetting(name="cog_control_size", setting_type="float", default=0.4),
        ModuleSetting(name="cog_control_name", setting_type="string", default="COG"),
        ModuleSetting(name="cog_control_direction", setting_type="string", default="y"),
        ModuleSetting(name="cog_control_rotation", setting_type="vector3", default=(0.0, 0.0, 0.0)),
        ModuleSetting(name="hip_control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="hip_control_size", setting_type="float", default=0.35),
        ModuleSetting(name="hip_control_name", setting_type="string", default="hip"),
        ModuleSetting(name="hip_control_direction", setting_type="string", default="y"),
        ModuleSetting(name="cog_control_color", setting_type="string", default="SubMiddle"),
        ModuleSetting(name="rig_color_type", setting_type="string", default="Middle"),
        ModuleSetting(name="joint_name", setting_type="string", default=""),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        part: str = "hip",
        side: str = "M",
        parent: str = "components",
        rig_size: float = 1.0,
        joint_parent: str = "root",
        guides: list | None = None,
        control_space: list | None = None,
        rig_color_type: str = "Middle",
        cog_control_shape: str = "COG",
        cog_control_size: float = 0.4,
        cog_control_name: str = "COG",
        cog_control_direction: str = "y",
        cog_control_rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        cog_control_color: str = "SubMiddle",
        hip_control_shape: str = "circle",
        hip_control_size: float = 0.35,
        hip_control_name: str = "hip",
        hip_control_direction: str = "y",
        joint_name: str | None = None,
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.rig_size = rig_size
        self.joint_parent = joint_parent
        self.guides = guides if guides is not None else ["pelvis"]
        self.control_space = control_space if control_space is not None else []
        self.rig_color_type = rig_color_type
        self.cog_control_shape = cog_control_shape
        self.cog_control_size = cog_control_size
        self.cog_control_name = cog_control_name
        self.cog_control_direction = cog_control_direction
        self.cog_control_rotation = cog_control_rotation
        self.sub_control_color = cog_control_color
        self.hip_control_shape = hip_control_shape
        self.hip_control_size = hip_control_size
        self.hip_control_name = hip_control_name
        self.hip_control_direction = hip_control_direction
        self.joint_name = joint_name

    @classmethod
    def preview(cls, part: str, side: str, guides: list[str], settings: dict) -> dict:
        if not guides:
            return {"controls": [], "joints": [], "output_control": None, "output_joint": None}
        cog = f"{settings.get('cog_control_name', 'COG')}_ctrl"
        hip = f"{settings.get('hip_control_name', 'hip')}_ctrl"
        joint = f"def_{guides[0]}_jnt"
        return {
            "controls": [cog, hip], "joints": [joint],
            "output_control": hip, "output_joint": joint,
        }

    def build(self) -> module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.COG_ctrl = create_control(
            name=self.cog_control_name,
            parent=self.control_grp,
            transform=self.guides[0].name, #type:ignore
            size=self.rig_size * self.cog_control_size,
            control_shape=self.cog_control_shape,
            direction=self.cog_control_direction,  #type:ignore
            shape_rotation_offset=self.cog_control_rotation,
            color_type=self.sub_control_color,
        )
        self.hip_ctrl = create_control(
            name=self.hip_control_name,
            parent=self.COG_ctrl.ctrl,
            transform=self.guides[0].name, #type:ignore
            size=self.rig_size * self.hip_control_size,
            control_shape=self.hip_control_shape,
            direction=self.hip_control_direction, #type:ignore
            color_type=self.rig_color_type,
        )

        self.joint = create_joint(
            name=self.joint_name or f"def_{self.guides[0].descriptor}", #type:ignore
            transform=self.guides[0].name, #type:ignore
            connect=True,
            parent=self.joint_parent,
        )
        constraint(
            drivers=[self.hip_ctrl.ctrl],
            driven=self.joint,
            parent=self.guts,
            constraint_type="parent",
        )
        module_space(space_list=self.control_space, control=self.COG_ctrl)
        return module_info(
            cog_control=self.COG_ctrl,
            hip_control=self.hip_ctrl,
            hip_joint=self.joint,
        )
