from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import ModuleRelationship, ModuleSetting
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.joint import create_joint

from .module_shared import (
    create_blend_driver_offset,
    create_driver_offset,
    module_prep,
    module_space,
)


@dataclass
class module_info:
    control: Control
    joint: str


class Cheek:
    MODULE_NAME = "cheek"
    DISPLAY_NAME = "Cheek"

    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="puff_shape", setting_type="control_shape", default="sphere"),
        ModuleSetting(name="cheekbone_shape", setting_type="control_shape", default="triangle"),
        ModuleSetting(name="puff_size", setting_type="float", default=0.01),
        ModuleSetting(name="cheekbone_size", setting_type="float", default=0.01),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="cheekbone_rotation", setting_type="vector3", default=(90.0, 0.0, 0.0)),
        ModuleSetting(name="puff_follow", setting_type="float", default=0.5),
        ModuleSetting(name="cheekbone_rotation_mult", setting_type="float", default=0.1),
        ModuleSetting(name="cheekbone_translation_mult", setting_type="float", default=0.0),
        ModuleSetting(name="cheekbone_x_range", setting_type="vector2", default=(-90.0, 0.0)),
        ModuleSetting(name="cheekbone_y_range", setting_type="vector2", default=(0.0, 0.0)),
        ModuleSetting(name="cheekbone_z_range", setting_type="vector2", default=(-5.0, 5.0)),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="puff_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="cheekbone_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="head_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="driver", relationship_type="control", default="auto"),
    )

    def __init__(
        self,
        puff_space,
        cheekbone_space,
        driver,
        head_space,
        part: str = "cheek",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        cheekbone_shape: str = "triangle",
        puff_shape: str = "sphere",
        puff_size: float = 0.01,
        cheekbone_size: float = 0.01,
        control_direction: str = "y",
        cheekbone_rotation: tuple[float, float, float] = (90.0, 0.0, 0.0),
        puff_follow: float = 0.5,
        cheekbone_rotation_mult: float = 0.1,
        cheekbone_translation_mult: float = 0.0,
        cheekbone_x_range: tuple[float, float] = (-90.0, 0.0),
        cheekbone_y_range: tuple[float, float] = (0.0, 0.0),
        cheekbone_z_range: tuple[float, float] = (-5.0, 5.0),
        control_color: str | None = None,
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.puff_shape = puff_shape
        self.cheekbone_shape = cheekbone_shape
        self.puff_size = puff_size
        self.cheekbone_size = cheekbone_size
        self.control_direction = control_direction
        self.cheekbone_rotation = cheekbone_rotation
        self.puff_follow = puff_follow
        self.cheekbone_rotation_mult = cheekbone_rotation_mult
        self.cheekbone_translation_mult = cheekbone_translation_mult
        self.cheekbone_x_range = cheekbone_x_range
        self.cheekbone_y_range = cheekbone_y_range
        self.cheekbone_z_range = cheekbone_z_range
        self.main_color = control_color or ("Left" if side == "L" else "Right")
        self.puff_space = puff_space
        self.cheekbone_space = cheekbone_space
        self.driver = driver
        self.head_space = head_space

    def build(self) -> module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.puff_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.rig_size * self.puff_size,
            control_shape=self.puff_shape,
            direction=self.control_direction,
            color_type=self.main_color,
            sdk_offset=True,
        )
        module_space(control=self.puff_ctrl, space_list=self.puff_space)
        create_blend_driver_offset(
            default_mult=self.puff_follow,
            control=self.puff_ctrl,
            driver=self.driver,
            parent_space=self.puff_space[0].ctrl,
        )
        self.puff_joint = create_joint(
            name=f"def_{self.guides[0].descriptor}",
            transform=self.puff_ctrl.ctrl,
            connect=True,
            parent=self.joint_parent,
        )

        self.cheekbone_ctrl = create_control(
            name=self.guides[1].descriptor,
            parent=self.control_grp,
            transform=self.guides[1].name,
            size=self.rig_size * self.cheekbone_size,
            control_shape=self.cheekbone_shape,
            direction=self.control_direction,
            color_type=self.main_color,
            sdk_offset=True,
            shape_rotation_offset=self.cheekbone_rotation,
        )
        module_space(control=self.cheekbone_ctrl, space_list=self.cheekbone_space)
        self.cheekbone_joint = create_joint(
            name=f"def_{self.guides[1].descriptor}",
            transform=self.cheekbone_ctrl.ctrl,
            connect=True,
            parent=self.joint_parent,
        )
        create_driver_offset(
            control=self.cheekbone_ctrl,
            driver=self.driver,
            x_range=self.cheekbone_x_range,
            rot_mult=self.cheekbone_rotation_mult,
            trans_mult=self.cheekbone_translation_mult,
            y_range=self.cheekbone_y_range,
            z_range=self.cheekbone_z_range,
        )

        return module_info(control=self.cheekbone_ctrl, joint=self.puff_joint)
