from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import ModuleGuideArray, ModuleRelationship, ModuleSetting
from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.joint import create_joint
from Workshop.maya_api.node import BlendColorsNode
from Workshop.transform.constraint import constraint
from Workshop.transform.utils import rotation_blend

from .module_shared import module_prep, module_space


@dataclass
class module_info:
    control: list[Control]
    joint: list[str]


class Metacarpal:
    MODULE_NAME = "metacarpal"
    DISPLAY_NAME = "Metacarpal"
    GUIDES = (ModuleGuideArray(name="metacarpal", default_count=4),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="roll", setting_type="bool", default=True),
        ModuleSetting(name="control_size", setting_type="float", default=1 / 32),
        ModuleSetting(name="control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="roll_control_size", setting_type="float", default=1 / 32),
        ModuleSetting(name="roll_control_shape", setting_type="control_shape", default="four_star"),
        ModuleSetting(name="roll_control_offset", setting_type="vector3", default=(-1 / 16, 0.0, 0.0)),
        ModuleSetting(name="roll_control_name", setting_type="string", default="expresion"),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="main_control_color", setting_type="string", default=""),
        ModuleSetting(name="sub_control_color", setting_type="string", default=""),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        part: str = "metacarpal",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        control_space: list | None = None,
        roll: bool = True,
        control_size: float = 1 / 32,
        control_shape: str = "circle",
        roll_control_size: float = 1 / 32,
        roll_control_shape: str = "four_star",
        roll_control_offset: tuple[float, float, float] = (-1 / 16, 0.0, 0.0),
        roll_control_name: str = "expresion",
        control_direction: str = "y",
        main_control_color: str | None = None,
        sub_control_color: str | None = None,
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.control_space = control_space if control_space is not None else []
        self.roll = roll
        self.control_size = control_size
        self.control_shape = control_shape
        self.roll_control_size = roll_control_size
        self.roll_control_shape = roll_control_shape
        self.roll_control_offset = roll_control_offset
        self.roll_control_name = roll_control_name
        self.control_direction = control_direction
        self.main_control_color = main_control_color or ("Left" if side == "L" else "Right")
        self.sub_control_color = sub_control_color or ("SubLeft" if side == "L" else "SubRight")

    @classmethod
    def preview(cls, part: str, side: str, guides: list[str], settings: dict) -> dict:
        controls = [f"{guide}_ctrl" for guide in guides]
        if settings.get("roll", True) and guides:
            controls.insert(0, f"{part}_{settings.get('roll_control_name', 'expresion')}_{side}_ctrl")
        joints = [f"def_{guide}_jnt" for guide in guides]
        return {
            "controls": controls,
            "joints": joints,
            "output_control": controls[-1] if controls else None,
            "output_joint": joints[-1] if joints else None,
        }

    def build(self) -> module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.metacarpal_ctrls = []
        self.metacarpal_joints = []

        weights: list[float] = []
        if self.roll:
            self.roll_ctrl = create_control(
                name=f"{self.part}_{self.roll_control_name}_{self.side}",
                parent=self.control_grp,
                transform=self.guides[0].name,
                size=self.rig_size * self.roll_control_size,
                control_shape=self.roll_control_shape,
                direction=self.control_direction,
                color_type=self.sub_control_color,
                shape_position_offset=tuple(value * self.rig_size for value in self.roll_control_offset),
            )
            weights = [i / (len(self.guides) - 1) for i in range(len(self.guides))] if len(self.guides) > 1 else [1.0]
            weights.reverse()
            module_space(control=self.roll_ctrl, space_list=self.control_space)

        for i, guide in enumerate(self.guides):
            ctrl = create_control(
                name=guide.descriptor,
                parent=self.control_grp,
                transform=guide.name,
                size=self.rig_size * self.control_size,
                control_shape=self.control_shape,
                direction=self.control_direction,
                color_type=self.main_control_color,
                sdk_offset=True,
            )
            self.metacarpal_ctrls.append(ctrl)

            if self.roll and i != 0:
                rotation_blend(
                    name=f"{ctrl.ctrl}_meta",
                    tfrom01=self.roll_ctrl.ctrl,
                    tform02=ctrl.sdk,
                    weight=weights[i],
                    attr=True,
                )
                translate_blend = BlendColorsNode(name=f"{ctrl.ctrl}_meta_BC")
                translate_blend.color2.connect_from(f"{self.roll_ctrl.ctrl}.translate")
                translate_blend.blender.set(weights[i])
                translate_blend.output.connect_to(f"{ctrl.sdk}.translate")

            joint = create_joint(
                name=f"def_{guide.descriptor}",
                transform=ctrl.ctrl,
                connect=True,
                parent=self.joint_parent,
            )
            self.metacarpal_joints.append(joint)
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type="parent", parent=self.guts)
            module_space(control=ctrl, space_list=self.control_space)

        return module_info(control=self.metacarpal_ctrls, joint=self.metacarpal_joints)
