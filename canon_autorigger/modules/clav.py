from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo

from .module_shared import module_prep, module_space

from Workshop.canon_autorigger.module_schema import (
    ModuleSetting,
    ModuleRelationship,
    ModuleGuide,
)


@dataclass
class module_info:
    control:Control
    joint:str

class Clav:

    MODULE_NAME = "clav"
    DISPLAY_NAME = "Clavicle"

    GUIDES = (
        ModuleGuide(
            name="clav",
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="control_shape",
            setting_type="control_shape",
            default="arch",
        ),
        ModuleSetting(
            name="control_size",
            setting_type="float",
            default=0.25,
        ),
        ModuleSetting(
            name="control_rot",
            setting_type="vector3",
            default=(0.0, 90.0, 0.0),
        ),
        ModuleSetting(
            name="control_offset",
            setting_type="vector3",
            default=(0.0, 0.1, 0.0),
        ),
    )

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
    )
    def __init__(
        self,
        guides: GuideInfo,
        part: str = "clav",
        side: str = "L",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        joint_parent:str = 'skel',
        control_space:list = [],
        control_shape:str = "arch",
        control_size:float = 1/4,
        control_rot:tuple = (0,90,0),
        control_offset:tuple = (0,1/10,0),

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides = guides
        self.joint_parent = joint_parent
        self.main_control_color = 'Left' if self.side == 'L' else 'Right'
        self.control_space = control_space
        self.control_shape = control_shape
        self.control_size = control_size
        self.control_rot = control_rot
        self.control_offset = control_offset

    # -------------------
    # Preview
    # -------------------

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:

        if not guides:
            return {
                "controls": [],
                "joints": [],
                "output_control": None,
                "output_joint": None,
            }

        control = f"{part}_{side}_ctrl"
        joint = f"def_{part}_{side}_jnt"

        return {
            "controls": [control],
            "joints": [joint],
            "output_control": control,
            "output_joint": joint,
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
        self.clav_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides.name,
            size=self.rig_size * self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.main_control_color,
            shape_rotation_offset=self.control_rot,
            shape_position_offset=tuple(value * self.rig_size for value in self.control_offset)
        )

        #joints

        module_space(control=self.clav_ctrl, space_list=self.control_space)

        self.clav_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.clav_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.clav_ctrl.ctrl], driven=self.clav_joint, constraint_type='parent', parent=self.guts)

        clav_info = module_info(control =self.clav_ctrl, joint=self.clav_joint)
        return clav_info