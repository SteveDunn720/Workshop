from turtle import position

from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    upper_control:Control
    upper_joint:str
    lower_control:Control
    lower_joint:str

class Face:
    def __init__(
        self,
        part: str = "face",
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
        self.main_control_color = 'Middle'
        self.sub_control_color = 'SubMiddle'

    # -------------------
    # Build steps
    # -------------------

    def face_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.upper_face_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size/30,
            control_shape="round_square",
            direction="y",
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(self.control_size/4,0,0), 
            color_type=self.sub_control_color
        )

        module_space(control=self.upper_face_ctrl, space_list=self.control_space)

        self.lower_face_ctrl = create_control(
            name=self.guides[1].descriptor,
            parent=self.control_grp,
            transform=self.guides[1].name,
            size=self.control_size/30,
            control_shape="round_square",
            direction="y",
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(self.control_size/4,0,0), 
            color_type=self.sub_control_color
        )
        
        module_space(control=self.lower_face_ctrl, space_list=self.control_space)

        #joints

        self.upper_face_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.upper_face_ctrl.ctrl, connect=True, parent=self.joint_parent)
        self.lower_face_joint = create_joint(name=f'def_{self.guides[1].descriptor}', transform=self.lower_face_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.lower_face_ctrl.ctrl], driven=self.lower_face_joint, constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.upper_face_ctrl.ctrl], driven=self.upper_face_joint, constraint_type='parent', parent=self.guts)

        face_info = module_info(upper_control =self.upper_face_ctrl, upper_joint=self.upper_face_joint, lower_control =self.lower_face_ctrl, lower_joint=self.lower_face_joint)
        return face_info