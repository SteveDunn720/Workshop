from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    cog_control:Control
    hip_control:Control

class Foot:
    def __init__(
        self,
        part: str = "foot",
        side: str = "l",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['foot_l', 'ball_l'],
        control_space:list = [],
        ik_hook:str='',

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.control_space = control_space 
        self.ik_hook = ik_hook

    # -------------------
    # Build steps
    # -------------------

    def hip_build(self) ->module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.COG_ctrl = create_control(
            name=f'{self.part}_IK_{self.side}',
            parent=self.control_grp,
            transform=self.joints[0],
            size=self.control_size * .3,
            control_shape="ciricle",
            direction="x",
        )