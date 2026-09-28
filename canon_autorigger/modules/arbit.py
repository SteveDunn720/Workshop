from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import read_guide

from .module_initialize import module_prep, module_space

from Workshop.canon_autorigger.module_schema import (
    ModuleSetting,
    ModuleRelationship,
    ModuleGuide,
)


@dataclass
class module_info:
    control:Control
    joint:str

class Arbit:

    MODULE_NAME = "arbit"
    DISPLAY_NAME = "Arbit"

    GUIDES = (
        ModuleGuide(
            name="arbit",
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="control_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="control_color",
            setting_type="string",
            default="MISC",
        ),
        ModuleSetting(
            name="control_shape",
            setting_type="control_shape",
            default="circle",
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
        part: str = "arbit",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        control_color:str = 'MISC',
        control_shape:str = 'circle'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.control_color = control_color
        self.control_shape = control_shape


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

        guide = read_guide(
            guides[0]
        )

        control = f"{guide.descriptor}_ctrl"
        joint = f"def_{guide.descriptor}_jnt"

        return {
            "controls": [control],
            "joints": [joint],
            "output_control": control,
            "output_joint": joint,
        }

    # -------------------
    # Build steps
    # -------------------

    def arbit_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.arbit_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        module_space(control=self.arbit_ctrl, space_list=self.control_space)

        #joints

        self.arbit_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.arbit_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.arbit_ctrl.ctrl], driven=self.arbit_joint, constraint_type='parent', parent=self.guts)

        arbit_info = module_info(control =self.arbit_ctrl, joint=self.arbit_joint)
        return arbit_info