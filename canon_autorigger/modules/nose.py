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

class Nose:
    def __init__(
        self,
        part: str = "nose",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: dict = {},
        joint_parent:str = 'skel',
        control_space:list = [],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: dict = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.main_M_color = 'Middle'
        self.sub_M_color = 'SubMiddle'
    
        self.main_L_color = 'Left'
        self.sub_L_color = 'SubLeft'
    
        self.main_R_color = 'Right'
        self.sub_R_color = 'SubRight'

    # -------------------
    # Build steps
    # -------------------

    def nose_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.nose_ctrl = create_control(
            name=self.guides['Root'].descriptor,
            parent=self.control_grp,
            transform=self.guides['Root'].name,
            size=self.control_size/40,
            control_shape='round_square',
            direction="y",
            color_type=self.main_M_color
        )

        module_space(control=self.nose_ctrl, space_list=self.control_space)

        #joints

        self.nose_joint = create_joint(name=self.guides['Root'].descriptor, transform=self.nose_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.nose_ctrl.ctrl], driven=self.nose_joint, constraint_type='parent', parent=self.guts)

        nose_info = module_info(control =self.nose_ctrl, joint=self.nose_joint)

        #controls
        self.bridge_ctrl = create_control(
            name=self.guides['Bridge'].descriptor,
            parent=self.control_grp,
            transform=self.guides['Bridge'].name,
            size=self.control_size/50,
            control_shape='round_square',
            direction="y",
            color_type=self.main_M_color
        )

        module_space(control=self.bridge_ctrl, space_list=self.control_space)

        #joints

        self.bridge_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.bridge_ctrl.ctrl, connect=True, parent=self.nose_joint)

        constraint(drivers=[self.bridge_ctrl.ctrl], driven=self.bridge_joint, constraint_type='parent', parent=self.guts)

        nose_info = module_info(control =self.bridge_ctrl, joint=self.bridge_joint)



        for guide in [self.guides[f'L_Outer'], self.guides[f'R_Outer'], self.guides[f'L_UpperCorner'], self.guides[f'R_UpperCorner'], self.guides['Tip']]: #'Nostril_Inner' self.guides[f'L_Nostril'], self.guides[f'R_Nostril'],

            if guide.descriptor.startswith("L_"):
                color = self.main_L_color
            elif guide.descriptor.startswith("R_"):
                color = self.main_R_color
            else:
                color = self.main_M_color

            if guide in [self.guides[f'L_Outer'], self.guides[f'R_Outer']]:
                shape = 'bean'
            else:
                shape = 'circle'
            ctrl = create_control(
                name=guide.descriptor,
                parent=self.nose_ctrl.ctrl,
                transform=guide.name,
                size=self.control_size/70 if guide == self.guides['Tip'] else self.control_size/150,
                control_shape=shape,
                direction="y",
                color_type=color,
                shape_rotation_offset=(0,90,0),
                dimensions=(1,5,1),
            )

            joint = create_joint(name=guide.descriptor, transform=ctrl.ctrl, connect=True, parent=self.nose_joint)
            
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type='parent', parent=self.guts)
            

        return nose_info