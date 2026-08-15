from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint
from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    cog_control:Control
    hip_control:Control
    hip_joint:str

class Hip:
    def __init__(
        self,
        part: str = "hip",
        side: str = "M",
        parent: str = "components",
        control_size: float = 1.0,
        joint_parent:str = 'root',
        guides: list = ['pelvis'],
        control_space = [],
        rig_color_type:str = 'Middle'
    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.control_space = control_space
        self.joint_parent = joint_parent
        self.rig_color_type = rig_color_type
        self.sub_control_color = 'SubMiddle'

    # -------------------
    # Build steps
    # -------------------

    def hip_build(self) ->module_info:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.COG_ctrl = create_control(
            name='COG',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size * .45,
            control_shape="COG",
            direction="y",
            shape_rotation_offset=(0,0,0),
            color_type=self.sub_control_color
        )

        self.hip_ctrl = create_control(
            name='hip',
            parent=self.COG_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.control_size * .35,
            control_shape="circle",
            direction="y",
            color_type=self.rig_color_type
        )


        #bind joints

        self.joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.guides[0].name, connect=True, parent=self.joint_parent)
        constraint(drivers=[self.hip_ctrl.ctrl], driven=self.joint, parent=self.guts, constraint_type="parent")

    
        module_space(space_list=self.control_space, control=self.COG_ctrl)


        hip_info = module_info(cog_control=self.COG_ctrl, hip_control=self.hip_ctrl, hip_joint=self.joint)
        return hip_info