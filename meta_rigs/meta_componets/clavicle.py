from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    clav_control:Control

class Clavicle:
    def __init__(
        self,
        part: str = "clav",
        side: str = "m",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['clavicle_l'],
        control_space = [],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.control_space = control_space 

    # -------------------
    # Build steps
    # -------------------

    def clavicle_build(self) ->module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.clav_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.joints[0],
            size=self.control_size * .3,
            control_shape="circle",
            direction="x",
        )


        cmds.parentConstraint(self.clav_ctrl.ctrl, self.joints[0], maintainOffset=True)

        module_space(space_list=self.control_space, control=self.clav_ctrl)


        hip_info = module_info(clav_control=self.clav_ctrl,)
        return hip_info