from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    cog_control:Control
    hip_control:Control

class Hip:
    def __init__(
        self,
        part: str = "hip",
        side: str = "m",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['pelvis'],
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

    def hip_build(self) ->module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.COG_ctrl = create_control(
            name='COG',
            parent=self.control_grp,
            transform=self.joints[0],
            size=self.control_size * .6,
            control_shape="circle",
            direction="x",
        )

        self.hip_ctrl = create_control(
            name='hip',
            parent=self.COG_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .4,
            control_shape="circle",
            direction="x",
        )

        cmds.parentConstraint(self.hip_ctrl.ctrl, self.joints[0], maintainOffset=True)

        module_space(space_list=self.control_space, control=self.COG_ctrl)


        hip_info = module_info(cog_control=self.COG_ctrl, hip_control=self.hip_ctrl)
        return hip_info