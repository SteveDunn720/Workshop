from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform.utils import create_transform, get_position
from .module_initialize import module_prep, module_space
from Workshop.meta_rigs.meta_componets.ik import create_IK_rotate_plane
from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import AddDLNode, RemapValueNode, ReverseNode, SumNode
from .module_initialize import module_prep, module_space
from Workshop.meta_rigs.metahuman_rig_prep import foot_guides


@dataclass
class module_info:
    cog_control:Control
    hip_control:Control

class Foot:
    def __init__(
        self,
        guides:foot_guides,
        part: str = "roll",
        side: str = "l",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['foot_l', 'ball_l'],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.main_control_color = 'Left' if self.side == 'l' else 'Right' 
        self.guides = guides

    # -------------------
    # Build steps
    # -------------------

    def roll_build(self):
        self.smart_roll = create_control(
                name=f'roll_{self.side}',
                parent=self.control_parent,
                transform=self.joints[0],
                size=self.control_size/4,
                control_shape="sphere",
                direction="x",
                color_type=self.main_control_color
            )
        
        for attr in ['roll_twist', 'roll_sway', 'roll_angle']:
            cmds.addAttr(self.smart_roll.ctrl, longName=attr, attributeType='double', keyable=True)

        roll_group = create_transform(name=f'roll_{self.side}_grp', transform=self.guides.true_ball.name,)

        parent = None
        back_tforms = []
        for guide in [self.guides.true_toe, self.guides.true_ball, self.guides.true_heel, self.guides.true_foot]:
            tform = create_transform(name=f"{guide.name}_back", transform=guide.name, parent=parent)
            parent=tform
            back_tforms.append(tform)

        #toe_tip_roll

        toe_tip_remap = RemapValueNode(name=f'toe_roll_{self.side}_remap')
        toe_tip_adl = AddDLNode(name=f'toe_roll_{self.side}_adl')
        toe_tip_adl.input_1.set(90)
        toe_tip_adl.input_2.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        toe_tip_remap.input_max.connect_from(toe_tip_adl.output)
        toe_tip_remap.input_min.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        toe_tip_remap.output_min.set(0)
        toe_tip_remap.output_min.set(90)
        toe_tip_remap.output.connect_to(f'{back_tforms[0]}.rotateX')

        #ball_roll

        ball_adl = AddDLNode(name=f'ball_roll_{self.side}_adl')
        ball_remap1 = RemapValueNode(name=f'ball_roll1_{self.side}_remap')
        ball_remap2 = RemapValueNode(name=f'ball_roll2_{self.side}_remap')

        ball_remap1.input_value.connect_from(f'{self.smart_roll.ctrl}.rotateX')
        ball_remap1.input_max.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        ball_remap1.output_max.connect_from(f'{self.smart_roll.ctrl}.roll_angle')

        ball_remap2.input_min.connect_from(f'{self.smart_roll.ctrl}.roll_angle')



        








        




        

        