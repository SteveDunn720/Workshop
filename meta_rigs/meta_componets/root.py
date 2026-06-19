from attr import dataclass
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform import create_transform


@dataclass
class Root_guides:
    root:str

class Root:
    def __init__(
        self,
        part: str = "root",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['root'],

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

    def component_prep(self):
        self.main_grp = create_transform(name=f"{self.part}_{self.side}", parent=self.parent)
        self.control_grp = create_transform(name=f"{self.part}_CTRLS_{self.side}", parent=self.main_grp)
        self.guts = create_transform(name=f"{self.part}_GUTS_{self.side}", parent=self.main_grp)

    def root_build(self):
        self.component_prep()

        self.root_ctrl = create_control(
            name=self.part,
            parent=self.control_grp,
            transform=self.joints[0],
            size=self.control_size,
            control_shape="circle",
            direction="y",
        )

        self.local_ctrl = create_control(
            name='local',
            parent=self.root_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .8,
            control_shape="circle",
            direction="y",
        )

        self.offset_ctrl = create_control(
            name='offset',
            parent=self.local_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .6,
            control_shape="circle",
            direction="y",
        )

        cmds.parentConstraint(self.offset_ctrl.ctrl, self.joints[0], mo=True)