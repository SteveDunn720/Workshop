from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform.utils import create_transform, get_position
from .module_initialize import module_prep, module_space
from Workshop.meta_rigs.meta_componets.ik import create_IK_rotate_plane
from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import AddDLNode, ConditionNode, MultiplyDivideNode, RemapValueNode, ReverseNode, SumNode
from .module_initialize import module_prep, module_space
from Workshop.meta_rigs.metahuman_rig_prep import foot_guides


@dataclass
class module_info:
    up_driver:str
    down_driver:str
    roll_ctrl:Control
    twist_ctrl:Control
    roll_grp:str

class Roll:
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
        roll_group = create_transform(name=f'roll_{self.side}_grp', transform=self.guides.true_ball.name,)
        self.smart_roll = create_control(
                name=f'foot_roll_{self.side}',
                parent=roll_group,
                transform=self.guides.true_foot.name,
                size=self.control_size/8,
                control_shape="sphere",
                direction="x",
                color_type=self.main_control_color,
                ignore_rotations=True,
            )
        
        for attr in ['roll_twist', 'roll_sway', 'roll_angle', 'bank_width', 'DEV_bank_sensitivity']:
            cmds.addAttr(self.smart_roll.ctrl, longName=attr, attributeType='double', keyable=True)
        
        cmds.setAttr(f'{self.smart_roll.ctrl}.roll_angle', 70)
        cmds.setAttr(f'{self.smart_roll.ctrl}.DEV_bank_sensitivity', 1)

    
        roll_center = create_transform(name=f'roll_{self.side}_center', transform=self.guides.true_ball.name,)

        parent = roll_center
        back_tforms = []
        for guide in [self.guides.true_toe, self.guides.true_ball, self.guides.true_heel, self.guides.true_foot]:
            tform = create_transform(name=f"{guide.name}_back", transform=guide.name, parent=parent)
            parent=tform
            back_tforms.append(tform)

        #senstivity_mult

        sensitivty = MultiplyDivideNode(name=f'roll_{self.side}_md')
        sensitivty.input1.z.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        sensitivty.input2.z.set(-1)
        sensitivty.input1.x.connect_from(f'{self.smart_roll.ctrl}.rotateZ')
        sensitivty.input2.x.connect_from(f'{self.smart_roll.ctrl}.DEV_bank_sensitivity')

        #toe_tip_roll

        toe_tip_remap = RemapValueNode(name=f'toe_roll_{self.side}_remap')
        toe_tip_adl = AddDLNode(name=f'toe_roll_{self.side}_adl')
        toe_tip_adl.input_1.set(90)
        toe_tip_adl.input_2.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        toe_tip_remap.input_max.connect_from(toe_tip_adl.output)
        toe_tip_remap.input_min.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        toe_tip_remap.output_min.set(0)
        toe_tip_remap.output_max.set(90)
        toe_tip_remap.output.connect_to(f'{back_tforms[0]}.rotateX')
        toe_tip_remap.input_value.connect_from(f'{self.smart_roll.ctrl}.rotateX')

        #ball_roll

        ball_adl = AddDLNode(name=f'ball_roll_{self.side}_adl')
        ball_remap1 = RemapValueNode(name=f'ball_roll1_{self.side}_remap')
        ball_remap2 = RemapValueNode(name=f'ball_roll2_{self.side}_remap')

        ball_remap1.input_value.connect_from(f'{self.smart_roll.ctrl}.rotateX')
        ball_remap1.input_max.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        ball_remap1.output_max.connect_from(f'{self.smart_roll.ctrl}.roll_angle')

        ball_remap2.input_min.connect_from(f'{self.smart_roll.ctrl}.roll_angle')
        ball_remap2.input_max.connect_from(toe_tip_adl.output)
        ball_remap2.output_max.connect_from(sensitivty.output.z)
        ball_remap2.input_value.connect_from(f'{self.smart_roll.ctrl}.rotateX')


        ball_adl.input_1.connect_from(ball_remap1.output)
        ball_adl.input_2.connect_from(ball_remap2.output)
        ball_adl.output.connect_to(f'{back_tforms[1]}.rotateX')

        #heel_roll

        heel_remap = RemapValueNode(name=f'heel_roll_{self.side}_remap')
        heel_remap.input_max.set(-90)
        heel_remap.output_max.set(-90)
        heel_remap.input_value.connect_from(f'{self.smart_roll.ctrl}.rotateX')
        heel_remap.output.connect_to(f'{back_tforms[2]}.rotateX')


        front_tforms = []
        parent = roll_center
        for guide in [self.guides.true_heel, self.guides.true_toe, self.guides.true_ball,]:
            tform = create_transform(name=f"{guide.name}_front", transform=guide.name, parent=parent)
            parent=tform
            front_tforms.append(tform)

        for axis in ['X', 'Y', 'Z']:
            cmds.connectAttr(f'{back_tforms[2]}.rotate{axis}', f'{front_tforms[0]}.rotate{axis}')
            cmds.connectAttr(f'{back_tforms[0]}.rotate{axis}', f'{front_tforms[1]}.rotate{axis}')

        
        self.smart_twist = create_control(
                name=f'foot_twist_{self.side}',
                parent=roll_group,
                transform=self.guides.true_ball.name,
                size=self.control_size/8,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color,
                ignore_rotations=True,
            )


        #bank_and roll_pivot
        twist_main = create_transform(name=f"{self.guides.true_ball.name}_twist", transform=self.guides.true_ball.name, parent=roll_group)
        #twist_offset = create_transform(name=f"{self.guides.true_ball.name}_twist_offset", transform=self.guides.true_ball.name, parent=twist_main)

        bank_main = create_transform(name=f"{self.guides.true_ball.name}_bank_main", transform=self.guides.true_ball.name, parent=roll_group)
        bank_twist_offset = create_transform(name=f"{self.guides.true_ball.name}_bank_twist_offset", transform=self.guides.true_ball.name, parent=bank_main)

        #cmds.parentConstraint(twist_main, bank_main)

        inbank_main = create_transform(name=f"{self.guides.true_inbank.name}_main", transform=self.guides.true_inbank.name, parent=twist_main)
        inbank_offset = create_transform(name=f"{self.guides.true_inbank.name}_offset", transform=self.guides.true_ball.name, parent=inbank_main)
        outbank_main = create_transform(name=f"{self.guides.true_outbank.name}_main", transform=self.guides.true_outbank.name, parent=twist_main)
        outbank_offset = create_transform(name=f"{self.guides.true_outbank.name}_offset", transform=self.guides.true_ball.name, parent=outbank_main)

        constraint = cmds.parentConstraint(outbank_offset,inbank_offset, bank_main)
        weight_attrs = cmds.parentConstraint(
                        constraint[0], #type:ignore
                        query=True,
                        weightAliasList=True
                    )

        twist_inverse = MultiplyDivideNode(name = f'twist_inverse_{self.side}_md')
        twist_inverse.input1.connect_from(f'{twist_main}.translate')
        twist_inverse.input2.set((-1,-1,-1))
        twist_inverse.output.connect_to(f'{bank_twist_offset}.translate')

        bank_width = (abs(cmds.getAttr(f'{inbank_main}.translateX')) + abs(cmds.getAttr(f'{outbank_main}.translateX')))/2
        bank_width_mult = MultiplyDivideNode(name = f'bank_width_{self.side}_md')
        cmds.setAttr(f'{self.smart_roll.ctrl}.bank_width', bank_width)
        bank_width_mult.input1.x.connect_from(f'{self.smart_roll.ctrl}.bank_width')
        bank_width_mult.input1.y.connect_from(f'{self.smart_roll.ctrl}.bank_width')
        bank_width_mult.input2.x.set(-1)

        bank_neg = RemapValueNode(name=f'bank_neg_{self.side}_remap')
        bank_neg.input_value.connect_from(sensitivty.output.x)
        bank_neg.input_max.set(-90)
        bank_neg.output_max.set(-90)

        bank_pos = RemapValueNode(name=f'bank_pos_{self.side}_remap')
        bank_pos.input_value.connect_from(sensitivty.output.x)
        bank_pos.input_max.set(90)
        bank_pos.output_max.set(90)
        bank_condition = ConditionNode(name=f'bank_{self.side}_condition')
        bank_condition.operation.set(3)
        bank_condition.first_term.connect_from(sensitivty.output.x)
        bank_condition.color_if_true.set((1,0,0))
        bank_condition.color_if_false.set((0,1,0))

        if self.guides.neg == 'inner':
            cmds.connectAttr(f'{bank_width_mult.output.x}', f'{inbank_main}.translateX')
            cmds.connectAttr(f'{bank_width_mult.output.y}', f'{inbank_offset}.translateX')
            cmds.connectAttr(f'{bank_width_mult.output.y}', f'{outbank_main}.translateX')
            cmds.connectAttr(f'{bank_width_mult.output.x}', f'{outbank_offset}.translateX')
            bank_pos.output.connect_to(f'{inbank_main}.rotateZ')
            bank_neg.output.connect_to(f'{outbank_main}.rotateZ')
            bank_condition.out_color.g.connect_to(f'{constraint[0]}.{weight_attrs[0]}')
            bank_condition.out_color.r.connect_to(f'{constraint[0]}.{weight_attrs[1]}')

        else:
            cmds.connectAttr(f'{bank_width_mult.output.y}', f'{inbank_main}.translateX')
            cmds.connectAttr(f'{bank_width_mult.output.x}', f'{inbank_offset}.translateX')
            cmds.connectAttr(f'{bank_width_mult.output.x}', f'{outbank_main}.translateX')
            cmds.connectAttr(f'{bank_width_mult.output.y}', f'{outbank_offset}.translateX')
            bank_neg.output.connect_to(f'{inbank_main}.rotateZ')
            bank_pos.output.connect_to(f'{outbank_main}.rotateZ')
            bank_condition.out_color.r.connect_to(f'{constraint[0]}.{weight_attrs[0]}')
            bank_condition.out_color.g.connect_to(f'{constraint[0]}.{weight_attrs[1]}')

        cmds.parent(roll_center, bank_twist_offset)

        cmds.connectAttr(f"{self.smart_twist}.translate", f"{twist_main}.translate")
        cmds.connectAttr(f"{self.smart_twist}.rotate", f"{twist_main}.rotate")

        info = module_info(up_driver=back_tforms[-1], down_driver=front_tforms[-1], roll_grp=roll_group, roll_ctrl=self.smart_roll, twist_ctrl=self.smart_twist)
        return info

        
        






        



        








        




        

        