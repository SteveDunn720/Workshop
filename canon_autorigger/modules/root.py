from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.tag.core import lock_tag
from Workshop.joint import create_joint
from .module_initialize import module_prep


@dataclass
class module_info:
    root_control:Control
    local_control:Control
    offset_control:Control
    joint:str

class Root:
    def __init__(
        self,
        part: str = "root",
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
        self.root_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape="Character_base",
            direction="y",
            color_type='Root'
        )

        self.local_ctrl = create_control(
            name=f'local_{self.side}',
            parent=self.root_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.control_size * .56,
            control_shape="circle",
            direction="y",
        )

        self.offset_ctrl = create_control(
            name=f'offset_{self.side}',
            parent=self.local_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.control_size * .4,
            control_shape="circle",
            direction="y",
        )

        #rig option controls
        self.vis_control = create_control(
            name='visibility_options',
            parent=self.root_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.control_size * .05,
            control_shape="gear",
            direction="y",
            shape_position_offset=(self.control_size * 0.88, 0, 0 )
        )

        self.color_control = create_control(
            name='color_options',
            parent=self.root_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.control_size * .05,
            control_shape="gear",
            direction="y",
            shape_position_offset=(self.control_size * -0.88, 0, 0 )
        )
        lock_tag(self.color_control.ctrl, hide_tag=True)
        lock_tag(self.vis_control.ctrl, hide_tag=True)

        #root joint

        self.root_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.root_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.root_ctrl.ctrl], driven=self.root_joint, constraint_type='parent', parent=self.guts)

        #default attr
        for rig_vis_type in ['skel', 'geo', 'rig', 'controls']:
            cmds.addAttr(self.vis_control.ctrl, longName=f'{rig_vis_type}_vis', defaultValue=1, maxValue=1, minValue=0, keyable=True)


        root_info = module_info(root_control =self.root_ctrl, local_control=self.local_ctrl, offset_control=self.offset_ctrl, joint=self.root_joint)
        return root_info