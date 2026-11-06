from attr import dataclass

from Workshop.control.core import Control
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import read_guide

from .module_shared import create_blend_driver_offset, module_prep, module_space

from Workshop.canon_autorigger.module_schema import (
    ModuleSetting,
    ModuleRelationship,
    ModuleGuide,
)

@dataclass
class module_info:
    control:Control
    joint:str
    sub_controls:list
    sub_joints:list
class Ear:

    MODULE_NAME = "ear"
    DISPLAY_NAME = "Ear"

    GUIDES = (
        ModuleGuide(
            name="root",
        ),
        ModuleGuide(
            name="lower",
            parent="root",
            position=(0.0, -0.5, 0.0),
        ),
        ModuleGuide(
            name="upper",
            parent="root",
            position=(0.0, 0.5, 0.0),
        ),
        ModuleGuide(
            name="outer",
            parent="root",
            position=(0.5, 0.0, 0.0),
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="shape",
            setting_type="control_shape",
            default="sphere",
        ),
        ModuleSetting(
            name="main_shape",
            setting_type="control_shape",
            default="round_square",
        ),
        ModuleSetting(
            name="root_size",
            setting_type="float",
            default=1 / 100,
        ),
        ModuleSetting(
            name="sub_size",
            setting_type="float",
            default=1 / 150,
        ),
        ModuleSetting(
            name="root_offset",
            setting_type="vector3",
            default=(0.03, 0.03, 0.0),
        ),
        ModuleSetting(
            name="root_rot",
            setting_type="vector3",
            default=(90.0, 0.0, 0.0),
        ),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="main_space",
            relationship_type="control_space",
            default="auto",
        ),
        ModuleRelationship(
            name="driver",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="head_space",
            relationship_type="control_space",
            default="auto",
        ),
    )
    def __init__(
        self,
        main_space,
        driver,
        head_space,
        part: str = "ear",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: dict = {},
        joint_parent:str = 'skel',
        shape:str = 'sphere',
        main_shape:str = 'round_square',
        root_size:float = 1/100,
        sub_size:float = 1/150,
        root_offset:tuple = ( .03, .03, 0),
        root_rot:tuple = (90,0,0)


    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides= guides
        self.joint_parent = joint_parent
        self.main_shape = main_shape
        self.shape = shape
        if self.side == 'L':
            self.main_color = 'Left'
            self.sub_color = 'SubLeft'
        else:
            self.main_color = 'Right'
            self.sub_color = 'SubRight'
        self.main_space = main_space
        self.driver = driver
        self.head_space = head_space
        self.root_size = root_size
        self.sub_size = sub_size
        self.root_offset = root_offset
        self.root_rot = root_rot

    @staticmethod
    def _guide_map(guides, side):
        """
        Normalize guides to a dictionary keyed by
        root, lower, upper, outer.

        Supports both the original dictionary format
        and the new ordered guide list.
        """
        names = ("root", "lower", "upper", "outer")

        if isinstance(guides, dict):
            return {
                name: guides.get(f"{side}_{name}", guides.get(name))
                for name in names
            }

        return {
            name: guides[i] if i < len(guides) else None
            for i, name in enumerate(names)
        }

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:

        guide_map = cls._guide_map(guides, side)

        controls = []
        joints = []

        output_control = None
        output_joint = None

        for name in ("root", "lower", "upper", "outer"):
            guide_name = guide_map[name]

            if not guide_name:
                continue

            guide = read_guide(guide_name)

            control = f"{guide.descriptor}_ctrl"
            joint = f"def_{guide.descriptor}_jnt"

            controls.append(control)
            joints.append(joint)

            if name == "root":
                output_control = control
                output_joint = joint

        return {
            "controls": controls,
            "joints": joints,
            "output_control": output_control,
            "output_joint": output_joint,
        }
    # -------------------
    # Build steps
    # -------------------

    def build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.main_ctrl = create_control(
            name=self.guides[f'{self.side}_root'].descriptor,
            parent=self.control_grp,
            transform=self.guides[f'{self.side}_root'].name,
            size=self.rig_size * self.root_size,
            control_shape=self.main_shape,
            direction="y",
            color_type=self.main_color,
            sdk_offset=True,
            shape_position_offset=tuple(value * self.rig_size for value in self.root_offset),
            shape_rotation_offset=self.root_rot
        )

        module_space(control=self.main_ctrl, space_list=self.main_space)
        self.main_joint = create_joint(name=f"def_{self.guides[f'{self.side}_root'].descriptor}", transform=self.main_ctrl.ctrl, connect=True, parent=self.joint_parent)
        sub_controls = []
        sub_joints = []

        for mod in ['lower', 'upper', 'outer']:
            ctrl = create_control(
                name=self.guides[f'{self.side}_{mod}'].descriptor,
                parent=self.main_ctrl.ctrl,
                transform=self.guides[f'{self.side}_{mod}'].name,
                size=self.rig_size * self.sub_size,
                control_shape=self.shape,
                direction="y",
                color_type=self.main_color,
                sdk_offset=True
            )
            #joints

            joint = create_joint(name=f"def_{self.guides[f'{self.side}_{mod}'].descriptor}", transform=ctrl.ctrl, connect=True, parent=self.joint_parent)

            sub_controls.append(ctrl)
            sub_joints.append(joint)

            if mod == 'lower':
                create_blend_driver_offset(default_mult=.5, control=ctrl, driver=self.driver, parent_space=self.main_space[0].ctrl,)

        ear_info = module_info(control =self.main_ctrl, joint=self.main_joint, sub_controls=sub_controls, sub_joints=sub_joints)
        return ear_info