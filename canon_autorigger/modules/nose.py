from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import ModuleRelationship, ModuleSetting
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint

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


class Nose:
    MODULE_NAME = "nose"
    DISPLAY_NAME = "Nose"

    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="root_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="bridge_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="outer_shape", setting_type="control_shape", default="bean"),
        ModuleSetting(name="detail_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="root_size", setting_type="float", default=0.025),
        ModuleSetting(name="bridge_size", setting_type="float", default=0.02),
        ModuleSetting(name="tip_size", setting_type="float", default=1 / 70),
        ModuleSetting(name="detail_size", setting_type="float", default=1 / 150),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="root_rotation", setting_type="vector3", default=(90.0, 0.0, 0.0)),
        ModuleSetting(name="detail_rotation", setting_type="vector3", default=(0.0, 90.0, 0.0)),
        ModuleSetting(name="detail_dimensions", setting_type="vector3", default=(1.0, 5.0, 1.0)),
        ModuleSetting(name="mouth_follow", setting_type="float", default=0.05),
        ModuleSetting(name="jaw_rotation_mult", setting_type="float", default=0.8),
        ModuleSetting(name="jaw_translation_mult", setting_type="float", default=0.25),
        ModuleSetting(name="jaw_x_range", setting_type="vector2", default=(-90.0, 0.0)),
        ModuleSetting(name="jaw_y_range", setting_type="vector2", default=(0.0, 0.0)),
        ModuleSetting(name="jaw_z_range", setting_type="vector2", default=(-5.0, 5.0)),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="bridge_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="mouth", relationship_type="control", default="auto"),
        ModuleRelationship(name="jaw", relationship_type="control", default="auto"),
        ModuleRelationship(name="head", relationship_type="control", default="auto"),
    )

    def __init__(
        self,
        mouth,
        jaw,
        head,
        part: str = "nose",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: dict | None = None,
        joint_parent: str = "skel",
        control_space: list | None = None,
        bridge_space: list | None = None,
        root_shape: str = "round_square",
        bridge_shape: str = "round_square",
        outer_shape: str = "bean",
        detail_shape: str = "circle",
        root_size: float = 1 / 40,
        bridge_size: float = 1 / 50,
        tip_size: float = 1 / 70,
        detail_size: float = 1 / 150,
        control_direction: str = "y",
        root_rotation: tuple[float, float, float] = (90.0, 0.0, 0.0),
        detail_rotation: tuple[float, float, float] = (0.0, 90.0, 0.0),
        detail_dimensions: tuple[float, float, float] = (1.0, 5.0, 1.0),
        mouth_follow: float = 0.05,
        jaw_rotation_mult: float = 0.2,
        jaw_translation_mult: float = 0.25,
        jaw_x_range: tuple[float, float] = (-90.0, 0.0),
        jaw_y_range: tuple[float, float] = (0.0, 0.0),
        jaw_z_range: tuple[float, float] = (-5.0, 5.0),
        middle_color: str = "Middle",
        left_color: str = "Left",
        right_color: str = "Right",
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else {}
        self.joint_parent = joint_parent
        self.control_space = control_space if control_space is not None else []
        self.bridge_space = bridge_space if bridge_space is not None else []
        self.mouth = mouth
        self.jaw = jaw
        self.head = head
        self.root_shape = root_shape
        self.bridge_shape = bridge_shape
        self.outer_shape = outer_shape
        self.detail_shape = detail_shape
        self.root_size = root_size
        self.bridge_size = bridge_size
        self.tip_size = tip_size
        self.detail_size = detail_size
        self.control_direction = control_direction
        self.root_rotation = root_rotation
        self.detail_rotation = detail_rotation
        self.detail_dimensions = detail_dimensions
        self.mouth_follow = mouth_follow
        self.jaw_rotation_mult = jaw_rotation_mult
        self.jaw_translation_mult = jaw_translation_mult
        self.jaw_x_range = jaw_x_range
        self.jaw_y_range = jaw_y_range
        self.jaw_z_range = jaw_z_range
        self.main_M_color = middle_color
        self.main_L_color = left_color
        self.main_R_color = right_color

    def build(self) -> module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.nose_ctrl = create_control(
            name=self.guides["Root"].descriptor,
            parent=self.control_grp,
            transform=self.guides["Root"].name,
            size=self.rig_size * self.root_size,
            control_shape=self.root_shape,
            direction=self.control_direction,
            sdk_offset=True,
            color_type=self.main_M_color,
            shape_rotation_offset=self.root_rotation,
        )
        module_space(control=self.nose_ctrl, space_list=self.control_space)
        create_blend_driver_offset(
            default_mult=self.mouth_follow,
            control=self.nose_ctrl,
            driver=self.mouth,
            parent_space=self.head.ctrl,
        )
        create_driver_offset(
            control=self.nose_ctrl,
            driver=self.jaw,
            x_range=self.jaw_x_range,
            rot_mult=self.jaw_rotation_mult,
            trans_mult=self.jaw_translation_mult,
            y_range=self.jaw_y_range,
            z_range=self.jaw_z_range,
        )
        self.nose_joint = create_joint(
            name=self.guides["Root"].descriptor,
            transform=self.nose_ctrl.ctrl,
            connect=True,
            parent=self.joint_parent,
        )
        constraint(drivers=[self.nose_ctrl.ctrl], driven=self.nose_joint, constraint_type="parent", parent=self.guts)

        self.bridge_ctrl = create_control(
            name=self.guides["Bridge"].descriptor,
            parent=self.control_grp,
            transform=self.guides["Bridge"].name,
            size=self.rig_size * self.bridge_size,
            control_shape=self.bridge_shape,
            direction=self.control_direction,
            color_type=self.main_M_color,
        )
        module_space(control=self.bridge_ctrl, space_list=self.bridge_space)
        self.bridge_joint = create_joint(
            name=f"def_{self.part}_{self.side}",
            transform=self.bridge_ctrl.ctrl,
            connect=True,
            parent=self.nose_joint,
        )
        constraint(drivers=[self.bridge_ctrl.ctrl], driven=self.bridge_joint, constraint_type="parent", parent=self.guts)

        detail_keys = ("L_Outer", "R_Outer", "L_UpperCorner", "R_UpperCorner", "Tip")
        for key in detail_keys:
            guide = self.guides[key]
            if key in ("L_Outer", "L_UpperCorner"):
                color = self.main_L_color
            elif key in ("R_Outer", "R_UpperCorner"):
                color = self.main_R_color
            else:
                color = self.main_M_color

            shape = self.outer_shape if key in ("L_Outer", "R_Outer") else self.detail_shape
            size = self.tip_size if key == "Tip" else self.detail_size
            ctrl = create_control(
                name=guide.descriptor,
                parent=self.nose_ctrl.ctrl,
                transform=guide.name,
                size=self.rig_size * size,
                control_shape=shape,
                direction=self.control_direction,
                color_type=color,
                shape_rotation_offset=self.detail_rotation,
                dimensions=self.detail_dimensions,
            )
            joint = create_joint(
                name=guide.descriptor,
                transform=ctrl.ctrl,
                connect=True,
                parent=self.nose_joint,
            )
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type="parent", parent=self.guts)

        return module_info(control=self.nose_ctrl, joint=self.nose_joint)
