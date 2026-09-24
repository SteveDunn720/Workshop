from attr import dataclass
import maya.cmds as cmds

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
    top_control:Control
    top_joint:str
    muppet_control:Control
    skull_joint:str
    mid_joint:str
    submid_control:Control

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


        self.mid_face_ctrl = create_control(
            name='muppet_M',
            parent=self.control_grp,
            transform=self.guides[-1].name,
            size=self.control_size/30,
            control_shape="triangle",
            direction="y",
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(0,self.control_size/2.5,0), 
            color_type=self.sub_control_color
        )
        
        module_space(control=self.mid_face_ctrl, space_list=self.control_space)

        self.mid_sub_ctrl = create_control(
            name=f'def_{self.guides[2].descriptor}',
            parent=self.mid_face_ctrl.ctrl,
            transform=self.guides[2].name,
            size=self.control_size/40,
            control_shape="triangle",
            direction="y",
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(0,self.control_size/2,0), 
            color_type=self.sub_control_color,
            sdk_offset=True
        )

        cmds.hide(self.mid_sub_ctrl.ctrl)



        #joints

        self.mid_face_joint = create_joint(name=f'def_{self.guides[2].descriptor}', transform=self.guides[2].name, connect=False, parent=self.joint_parent)

        constraint(drivers=[self.mid_sub_ctrl.ctrl], driven=self.mid_face_joint, constraint_type='parent', parent=self.guts)

        self.skull_face_joint = create_joint(name='def_skull_M', transform=self.mid_face_ctrl.ctrl, connect=False, parent=self.joint_parent)
        
        constraint(drivers=[self.mid_face_ctrl.ctrl], driven=self.skull_face_joint, constraint_type='parent', parent=self.guts)

        #controls
        self.upper_face_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.mid_face_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.control_size/30,
            control_shape="round_square",
            direction="y",
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(self.control_size/4,0,0), 
            color_type=self.sub_control_color
        )

        #module_space(control=self.upper_face_ctrl, space_list=self.control_space)

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

        self.upper_face_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.upper_face_ctrl.ctrl, connect=False, parent=self.joint_parent)
        self.lower_face_joint = create_joint(name=f'def_{self.guides[1].descriptor}', transform=self.lower_face_ctrl.ctrl, connect=False, parent=self.joint_parent)

        constraint(drivers=[self.lower_face_ctrl.ctrl], driven=self.lower_face_joint, constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.upper_face_ctrl.ctrl], driven=self.upper_face_joint, constraint_type='parent', parent=self.guts)

        self.top_face_ctrl = create_control(
            name=self.guides[3].descriptor,
            parent=self.upper_face_ctrl.ctrl,
            transform=self.guides[3].name,
            size=self.control_size/70,
            control_shape="round_square",
            direction="y",
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(0,self.control_size/10, self.control_size/6), 
            color_type=self.sub_control_color,
            dimensions=(8,.1,1)
        )
        
        #module_space(control=self.top_face_ctrl, space_list=self.control_space)

        #joints

        self.top_face_joint = create_joint(name=f'def_{self.guides[3].descriptor}', transform=self.top_face_ctrl.ctrl, connect=False, parent=self.joint_parent)

        constraint(drivers=[self.top_face_ctrl.ctrl], driven=self.top_face_joint, constraint_type='parent', parent=self.guts)

        face_info = module_info(
            upper_control =self.upper_face_ctrl, 
            upper_joint=self.upper_face_joint, 
            lower_control =self.lower_face_ctrl, 
            lower_joint=self.lower_face_joint,
            top_control=self.top_face_ctrl,
            top_joint=self.top_face_joint,
            muppet_control=self.mid_face_ctrl , 
            skull_joint=self.skull_face_joint , 
            mid_joint=self.mid_face_joint ,
            submid_control = self.mid_sub_ctrl
        )
        return face_info