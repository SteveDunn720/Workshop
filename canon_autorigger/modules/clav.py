from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint

from .module_initialize import module_prep


@dataclass
class module_info:
    control:Control
    joint:str

class Clav:
    def __init__(
        self,
        part: str = "clav",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.main_control_color = 'Left' if self.side == 'L' else 'Right'

    # -------------------
    # Build steps
    # -------------------

    def clav_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.clav_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape="arch",
            direction="y",
            color_type=self.main_control_color
        )

        #joints

        self.clav_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.clav_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.clav_ctrl.ctrl], driven=self.clav_joint, constraint_type='parent', parent=self.guts)

        clav_info = module_info(control =self.clav_ctrl, joint=self.clav_joint)
        return clav_info