from attr import dataclass
import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import read_guide

from .module_shared import module_prep, module_space

from ..module_schema import (
    ModuleSetting,
    ModuleRelationship,
    ModuleGuide,
)


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

    MODULE_NAME = "face"
    DISPLAY_NAME = "Face"

    GUIDES = (
        ModuleGuide(
            name="upper_face",
        ),
        ModuleGuide(
            name="lower_face",
        ),
        ModuleGuide(
            name="mid_face",
        ),
        ModuleGuide(
            name="top_face",
        ),
        ModuleGuide(
            name="muppet",
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),

        # Face controls
        ModuleSetting(
            name="face_ctrl_shape",
            setting_type="control_shape",
            default="round_square",
        ),
        ModuleSetting(
            name="face_control_rot",
            setting_type="tuple",
            default=(90, 0, 0),
        ),
        ModuleSetting(
            name="face_control_offset",
            setting_type="tuple",
            default=(1/4, 0, 0),
        ),
        ModuleSetting(
            name="face_control_size",
            setting_type="float",
            default=1/30,
        ),

        # Top face control
        ModuleSetting(
            name="top_dimentions",
            setting_type="tuple",
            default=(8, 0.1, 1),
        ),
        ModuleSetting(
            name="top_offset",
            setting_type="tuple",
            default=(0, 1/10, 1/6),
        ),
        ModuleSetting(
            name="top_size",
            setting_type="float",
            default=1/70,
        ),

        # Muppet control
        ModuleSetting(
            name="muppet_shape",
            setting_type="control_shape",
            default="triangle",
        ),
        ModuleSetting(
            name="muppet_size",
            setting_type="float",
            default=1/30,
        ),
        ModuleSetting(
            name="muppet_offset",
            setting_type="tuple",
            default=(0, 1/2.5, 0),
        ),

        # Naming
        ModuleSetting(
            name="muppet_des",
            setting_type="string",
            default="muppet",
        ),
        ModuleSetting(
            name="skull_des",
            setting_type="string",
            default="skull",
        ),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="control_space",
            relationship_type="control_space",
            default="auto",
        ),
    )


    def __init__(
        self,
        part: str = "face",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        face_ctrl_shape:str = 'round_square',
        face_control_rot:tuple = (90,0,0) ,
        face_control_offset:tuple = (1/4,0,0) ,
        face_control_size:float = 1/30,
        top_dimentions:tuple = (8,.1,1),
        top_offset:tuple = (0, 1/10, 1/6),
        top_size:float = 1/70,
        muppet_shape:str = "triangle",
        muppet_size:float= 1/30,
        muppet_offset:tuple = (0, 1/2.5, 0),
        muppet_des:str = 'muppet',
        skull_des:str = 'skull'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.main_control_color = 'Middle'
        self.sub_control_color = 'SubMiddle'
        self.face_ctrl_shape = face_ctrl_shape
        self.face_control_rot = face_control_rot
        self.face_control_offset = face_control_offset
        self.face_control_size = face_control_size
        self.top_dimentions = top_dimentions
        self.top_offset = top_offset
        self.top_size = top_size
        self.muppet_shape =muppet_shape
        self.muppet_size = muppet_size
        self.muppet_offset = muppet_offset
        self.muppet_des = muppet_des
        self.skull_des = skull_des

    # -------------------
    # Build steps
    # -------------------

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:

        if len(guides) < 5:
            return {
                "controls": [],
                "joints": [],
                "output_control": None,
                "output_joint": None,
            }

        upper_guide = read_guide(guides[0])
        lower_guide = read_guide(guides[1])
        mid_guide = read_guide(guides[2])
        top_guide = read_guide(guides[3])

        muppet_des = settings.get("muppet_des", "muppet")
        skull_des = settings.get("skull_des", "skull")

        # Controls
        muppet_control = f"{muppet_des}_M_ctrl"
        submid_control = f"sub_{mid_guide.descriptor}_ctrl"

        upper_control = f"{upper_guide.descriptor}_ctrl"
        lower_control = f"{lower_guide.descriptor}_ctrl"
        top_control = f"{top_guide.descriptor}_ctrl"

        # Joints
        skull_joint = f"def_{skull_des}_M_jnt"
        mid_joint = f"def_{mid_guide.descriptor}_jnt"

        upper_joint = f"def_{upper_guide.descriptor}_jnt"
        lower_joint = f"def_{lower_guide.descriptor}_jnt"
        top_joint = f"def_{top_guide.descriptor}_jnt"

        return {
            "controls": [
                muppet_control,
                submid_control,
                upper_control,
                lower_control,
                top_control,
            ],
            "joints": [
                skull_joint,
                mid_joint,
                upper_joint,
                lower_joint,
                top_joint,
            ],
            "output_control": muppet_control,
            "output_joint": skull_joint,
        }

    def build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts


        self.mid_face_ctrl = create_control(
            name=f'{self.muppet_des}_M',
            parent=self.control_grp,
            transform=self.guides[-1].name,
            size=self.rig_size * self.muppet_size,
            control_shape=self.muppet_shape,
            direction="y",
            shape_rotation_offset=self.face_control_rot,
            shape_position_offset=tuple(value * self.rig_size for value in self.muppet_offset), 
            color_type=self.sub_control_color
        )
        
        module_space(control=self.mid_face_ctrl, space_list=self.control_space)

        self.mid_sub_ctrl = create_control(
            name=f'sub_{self.guides[2].descriptor}',
            parent=self.mid_face_ctrl.ctrl,
            transform=self.guides[2].name,
            size=self.rig_size * self.muppet_size * 1/2,
            control_shape=self.muppet_shape,
            direction="y",
            shape_rotation_offset=self.face_control_rot,
            shape_position_offset=tuple(value * self.rig_size for value in self.muppet_offset), 
            color_type=self.sub_control_color,
            sdk_offset=True
        )

        cmds.hide(self.mid_sub_ctrl.ctrl)



        #joints

        self.mid_face_joint = create_joint(name=f'def_{self.guides[2].descriptor}', transform=self.guides[2].name, connect=False, parent=self.joint_parent)

        constraint(drivers=[self.mid_sub_ctrl.ctrl], driven=self.mid_face_joint, constraint_type='parent', parent=self.guts)

        self.skull_face_joint = create_joint(name=f'def_{self.skull_des}_M', transform=self.mid_face_ctrl.ctrl, connect=False, parent=self.joint_parent)
        
        constraint(drivers=[self.mid_face_ctrl.ctrl], driven=self.skull_face_joint, constraint_type='parent', parent=self.guts)

        #controls
        self.upper_face_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.mid_face_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.rig_size * self.face_control_size,
            control_shape=self.face_ctrl_shape,
            direction="y",
            shape_rotation_offset=self.face_control_rot,
            shape_position_offset=tuple(value * self.rig_size for value in self.face_control_offset), 
            color_type=self.sub_control_color
        )

        #module_space(control=self.upper_face_ctrl, space_list=self.control_space)

        self.lower_face_ctrl = create_control(
            name=self.guides[1].descriptor,
            parent=self.control_grp,
            transform=self.guides[1].name,
            size=self.rig_size * self.face_control_size,
            control_shape=self.face_ctrl_shape,
            direction="y",
            shape_rotation_offset=self.face_control_rot,
            shape_position_offset=tuple(value * self.rig_size for value in self.face_control_offset), 
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
            size=self.rig_size * self.top_size,
            control_shape=self.face_ctrl_shape,
            direction="y",
            shape_rotation_offset=self.face_control_rot,
            shape_position_offset=tuple(value * self.rig_size for value in self.top_offset), 
            color_type=self.sub_control_color,
            dimensions=self.top_dimentions
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