from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.tag.core import lock_tag
from Workshop.prop.prop_modules.module_initialize import module_prep
from Workshop.joint import create_joint


@dataclass
class module_info:
    root_control:Control
    local_control:Control
    offset_control:Control
    root_joint:str

class Root:
    def __init__(
        self,
        part: str = "root",
        side: str = "m",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joint_parent:str = 'skel'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joint_parent = joint_parent

    # -------------------
    # Build steps
    # -------------------

    def root_build(self)->module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.joints = []


        self.root_ctrl = create_control(
            name=self.part,
            parent=self.control_grp,
            transform=None,
            size=self.control_size,
            control_shape="circle",
            direction="y",
            color_type='Root'
        )
        jnt = create_joint(name='root', transform=self.root_ctrl.ctrl, parent=self.joint_parent)
        self.joints.append(jnt)

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


        self.vis_control = create_control(
            name='visibility_options',
            parent=self.local_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .05,
            control_shape="circle",
            direction="y",
            shape_position_offset=(self.control_size * .9, self.control_size * .1, 0 )
        )

        self.color_control = create_control(
            name='color_options',
            parent=self.local_ctrl.ctrl,
            transform=self.joints[0],
            size=self.control_size * .05,
            control_shape="circle",
            direction="y",
            shape_position_offset=(self.control_size * .9, self.control_size * -.1, 0)
        )
        lock_tag(self.color_control.ctrl, hide_tag=True)
        lock_tag(self.vis_control.ctrl, hide_tag=True)

        root_info = module_info(root_control =self.root_ctrl, local_control=self.local_ctrl, offset_control=self.offset_ctrl, root_joint=jnt)
        return root_info