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


class Root:
    def __init__(
        self,
        part: str = "root",
        side: str = "m",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = ['root_M_guide'],
        joint_parent:str = 'skel',
        shape:str = 'circle',
        rig_color_type = 'MISC',

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.shape = shape
        self.rig_color_type = rig_color_type

    # -------------------
    # Build steps
    # -------------------

    def root_build(self)->module_info:

        #modeule prop work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0],
            size=self.control_size,
            control_shape=self.shape,
            direction="y",
            color_type=self.rig_color_type
        )

        #joint

        self.joint = create_joint(name=f'{self.part}_{self.side}', transform=self.ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.ctrl.ctrl], driven=self.joint, onstraint_type='parent', parent=self.guts)

        info = module_info(control=self.ctrl, joint=self.joint)
        return info