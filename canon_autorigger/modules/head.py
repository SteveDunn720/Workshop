from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:Control
    joint:str

class Head:
    def __init__(
        self,
        guides:GuideInfo,
        part: str = "head",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joint_parent:str = 'skel',
        control_space:list = [],
        control_shape:str = 'head'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides= guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        if self.side == "M":
            self.main_control_color = 'Middle'
            self.sub_control_color = 'SubMiddle'
        elif self.side == "L":
            self.main_control_color = 'Left'
            self.sub_control_color = 'SubLeft'
        else:
            self.main_control_color = 'Right'
            self.sub_control_color = 'SubRight'
        self.control_shape = control_shape

    # -------------------
    # Build steps
    # -------------------

    def head_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.head_ctrl = create_control(
            name=f'skull_{self.side}',
            parent=self.control_grp,
            transform=self.guides.name,
            size=self.control_size/4,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.main_control_color,
            shape_position_offset=(0,self.control_size/4,0),
        )

        module_space(control=self.head_ctrl, space_list=self.control_space)

        #joints

        self.head_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.head_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.head_ctrl.ctrl], driven=self.head_joint, constraint_type='parent', parent=self.guts)

        head_info = module_info(control =self.head_ctrl, joint=self.head_joint)
        return head_info