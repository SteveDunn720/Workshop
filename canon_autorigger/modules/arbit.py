from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:Control
    joint:str

class Arbit:
    def __init__(
        self,
        part: str = "arbit",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space

    # -------------------
    # Build steps
    # -------------------

    def arbit_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.arbit_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape="Character_base",
            direction="y",
            color_type='arbit'
        )

        module_space(control=self.arbit_ctrl, space_list=self.control_space)

        #joints

        self.arbit_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.arbit_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.arbit_ctrl.ctrl], driven=self.arbit_joint, constraint_type='parent', parent=self.guts)

        arbit_info = module_info(control =self.arbit_ctrl, joint=self.arbit_joint)
        return arbit_info