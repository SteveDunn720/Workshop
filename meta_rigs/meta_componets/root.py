from attr import dataclass
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform import create_transform
from .module_initialize import module_prep


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

    def root_build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.root_ctrl = create_control(
            name=self.part,
            parent=self.control_grp,
            transform=self.joints[0],
            size=self.control_size,
            control_shape="circle",
            direction="z",
        )

        self.local_ctrl = create_control(
            name='local',
            parent=self.root_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .8,
            control_shape="circle",
            direction="z",
        )

        self.offset_ctrl = create_control(
            name='offset',
            parent=self.local_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .6,
            control_shape="circle",
            direction="z",
        )

        cmds.parentConstraint(self.offset_ctrl.ctrl, self.joints[0], mo=True)