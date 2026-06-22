from attr import dataclass
import maya.cmds as cmds

from Workshop.control import create_control
from .module_initialize import module_prep


@dataclass
class Root_guides:
    root:str

class Hip:
    def __init__(
        self,
        part: str = "hip",
        side: str = "m",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['pelvis'],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joints: list = joints

    # -------------------
    # Build steps
    # -------------------

    def hip_build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.COG_ctrl = create_control(
            name=self.part,
            parent=self.control_grp,
            transform=self.joints[0],
            size=self.control_size * .8,
            control_shape="circle",
            direction="z",
        )

        self.hip_ctrl = create_control(
            name='local',
            parent=self.COG_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .6,
            control_shape="circle",
            direction="z",
        )

        cmds.parentConstraint(self.hip_ctrl.ctrl, self.joints[0], maintainOffset=True)