from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    fk_spine_controls_list:list[Control,Control,Control,Control,Control]
    #chest_control:Control

class Spine:
    def __init__(
        self,
        part: str = "spine",
        side: str = "m",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'],
        fk_control_space = [],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.fk_control_space = fk_control_space 

    def spine_build(self) ->module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #fk_controls

        self.fk_controls = []
        self.controls = []
        control_parent = self.control_grp
        for jnt in self.joints:
            control = create_control(
                name=jnt,
                parent=control_parent,
                transform=jnt,
                size=self.control_size * .3,
                control_shape="circle",
                direction="x",
            )
            self.fk_controls.append(control)
            self.controls.append(control)
            control_parent=control.ctrl

            cmds.parentConstraint(control.ctrl, jnt, maintainOffset=True)

        module_space(space_list=self.fk_control_space, control=self.controls[0])


        spine_info = module_info(fk_spine_controls_list=self.controls)
        return spine_info