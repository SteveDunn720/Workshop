
from attr import dataclass
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform.utils import get_position, match_transform, convert_to_matrix
from Workshop.joint import create_joint
from Workshop.maya_api.node import ConditionNode, DistanceBetweenNode, MultiplyDivideNode, ReverseNode
from Workshop.guide.core import GuideInfo
from Workshop.transform.constraint import constraint

from .roll import Roll
from .ik import create_IK_single_chain
from .module_initialize import module_prep, module_space
from .module_shared import fkik_switch

@dataclass
class module_info:
    ik_controls:list
    fk_control:list
    swtich_joints:list
    fk_joints:list
    ik_joints:list

@dataclass
class foot_guides:
    true_heel:GuideInfo
    true_foot:GuideInfo
    true_groundfoot:GuideInfo
    true_toe:GuideInfo
    true_inbank:GuideInfo
    true_outbank:GuideInfo
    true_ball:GuideInfo
    og_foot_pos:list[GuideInfo]
    aim_angle:float
    neg:str
    pos:str

class Foot:
    def __init__(
        self,
        leg_info,
        feet_guides:foot_guides,
        part: str = "foot",
        side: str = "L",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = ['foot_l', 'ball_l'],
        fk_control_space:list = [],
        ik_control_space:list = [],
        ik_hook:list=[],
        fkik_switch_attr:str = '',
        joint_parent:str = 'foot_joint',

        

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.fk_control_space = fk_control_space
        self.ik_control_space = ik_control_space
        self.main_control_color = 'Left' if self.side == 'L' else 'Right' 
        self.ik_hook = ik_hook
        self.feet_guides = feet_guides
        self.fkik_switch_attr = fkik_switch_attr
        self.leg_info = leg_info
        self.joint_parent = joint_parent
    # -------------------
    # Build steps
    # -------------------


    def get_ground_distance(self, object)->float:
        pos = get_position(object)

        return pos[1]

    def build_compressible_ik_length(
            self,
            name: str,
            root_reference: str,
            ik_control: str,
            length_joint: str,
            down_axis: str = "Y",
        ) -> None:
            """Build a single-joint IK length that compresses but does not stretch.

            The length_joint's translate channel is shortened when the IK control
            moves closer than the original joint length. Moving farther away will
            not extend the joint beyond its original length.

            Args:
                name: Base name used for created nodes.
                root_reference: Transform marking the beginning of the chain.
                ik_control: Transform marking the desired end of the chain.
                length_joint: Joint whose translate channel controls the chain length.
                down_axis: Local joint axis used for its length.
            """
            translate_attr = f"{length_joint}.translate{down_axis}"
            original_length = cmds.getAttr(translate_attr)
            absolute_original_length = abs(original_length)

            # Preserve whether the joint extends down the positive or negative axis.
            direction = 1.0 if original_length >= 0.0 else -1.0

            distance = DistanceBetweenNode(name=f"{name}_compress_distance")
            distance.input_matrix1.connect_from(
                f"{root_reference}.worldMatrix[0]"
            )
            distance.input_matrix2.connect_from(
                f"{ik_control}.worldMatrix[0]"
            )

            # Convert the always-positive world-space distance into the joint's
            # original positive or negative translate direction.
            signed_distance = MultiplyDivideNode(
                name=f"{name}_compress_signed_distance"
            )
            signed_distance.input1.x.connect_from(distance.distance)
            signed_distance.input2.x.set(direction)

            compress_condition = ConditionNode(
                name=f"{name}_compress_condition"
            )

            # condition operation 4 means "Less Than":
            # distance < original length
            compress_condition.operation.set(4)
            compress_condition.first_term.connect_from(distance.distance)
            compress_condition.second_term.set(absolute_original_length)

            # Shorter than the original: use the measured distance.
            compress_condition.color_if_true.r.connect_from(
                signed_distance.output.x
            )

            # Longer than the original: remain at the original length.
            compress_condition.color_if_false.r.set(original_length)

            compress_condition.out_color.r.connect_to(translate_attr)
        

    def foot_build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        ground_offset = self.get_ground_distance(object=self.guides[0])
        self.controls = []


        self.switch_joints = []

        jnt_par = self.guts
        #switch_joints
        for i,jnt in enumerate(self.guides):
            switch_jnt = create_joint(name=f'switch_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt
        
        #Fk_build
        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.guides):
            ctrl = create_control(
                name=f'FK_{jnt}',
                parent=ctrl_par,
                transform=jnt,
                size=self.control_size/(4 * (i + 1)),
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color
            )

            fk_jnt = create_joint(name=f'FK_{jnt}', transform=ctrl.ctrl, parent=jnt_par)

            self.fk_joints.append(fk_jnt)
            self.fk_controls.append(ctrl)
            self.controls.append(ctrl.ctrl)
            jnt_par = fk_jnt
            ctrl_par = ctrl.ctrl
            
            

        self.ik_joints = []
        self.ik_controls = []
        module_space(space_list=self.fk_control_space, control=self.fk_controls[0])
        jnt_par = self.guts

        #IK_build 
        for i,jnt in enumerate(self.guides):
            ik_jnt = create_joint(name=f'IK_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.ik_joints.append(ik_jnt)
            jnt_par = ik_jnt
        
        ctrl_par = self.ik_control_grp

        temp_guide = cmds.duplicate(self.guides[0])[0]

        for axis in ['X', 'Y', 'Z']:
            num = 180 if axis == 'X' else 0

            cmds.setAttr(f'{temp_guide}.jointOrient{axis}', num)

        self.ik_foot = create_control(
                name=f'IK_{self.guides[0]}_main',
                parent=ctrl_par,
                transform=temp_guide,
                size=self.control_size/4,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color,
                shape_position_offset=(0, -ground_offset, 0)
            )

        cmds.delete(temp_guide)

    
        
        self.ik_controls.append(self.ik_foot)
        self.controls.append(self.ik_foot)
        self.ik_toes = create_control(
                name=f'IK_{self.guides[1]}',
                parent=ctrl_par,
                transform=f'{self.guides[1]}',
                size=self.control_size/8,
                control_shape="circle",
                direction="y",
                color_type=self.main_control_color,
            )
        constraint(drivers=[self.ik_toes.ctrl], driven=self.ik_joints[1], constraint_type='parent', parent=self.guts)
        self.ik_controls.append(self.ik_toes)
        self.controls.append(self.ik_toes)


        self.FK_IK_Switch = fkik_switch(controls=self.controls, node_attr=self.main_grp, descriptor=self.part, fk_grp=self.fk_control_grp, ik_grp=self.ik_control_grp, fk_joints=self.fk_joints, ik_joints=self.ik_joints, switch_joints=self.switch_joints, connect_switch_attr=self.fkik_switch_attr )

        jnt_par = self.guts
        self.ik_roll_joints = []
        
        #IK_roll_build 
        for i,jnt in enumerate(self.guides):
            ik_jnt = create_joint(name=f'IK_roll_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.ik_roll_joints.append(ik_jnt)
            jnt_par = ik_jnt

        roll_ik = create_IK_single_chain(name=f'{self.part}_{self.side}_roll', start_joint=self.ik_roll_joints[0], end_joint=self.ik_roll_joints[1])
        cmds.parent(roll_ik.handle, self.guts)

        roll = Roll(part='roll', control_size=self.control_size, side=self.side, joints= [f'foot_{self.side}', f'ball_{self.side}'], guides=self.feet_guides, control_parent=self.ik_foot.ctrl)
        roll_info = roll.roll_build()

        #self.build_compressible_ik_length(name=f'{self.part}_{self.side}_roll', root_reference=roll_info.roll_ctrl.top, ik_control=roll_info.down_driver, down_axis='X', length_joint=self.ik_roll_joints[1])

        match_transform(transform=roll_info.roll_grp, target_transform=self.feet_guides.og_foot_pos[-2])

        cmds.parent(roll_info.roll_grp, self.ik_foot.ctrl)

        constraint(drivers=[roll_info.down_driver], driven=roll_ik.handle, constraint_type='parent', parent=self.guts)
        cmds.orientConstraint(roll_info.down_driver, self.ik_roll_joints[1], maintainOffset=True)   #FIX
        constraint(drivers=[roll_info.up_driver], driven=self.ik_hook[0], constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_hook[1]], driven=self.ik_roll_joints[0], constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_roll_joints[0]], driven=self.ik_joints[0], constraint_type='parent', parent=self.guts)
        constraint(drivers=[roll_info.down_driver], driven=self.ik_toes.top, constraint_type='parent', parent=self.guts)
        cmds.addAttr(self.ik_foot.ctrl, longName='stretch', proxy = self.leg_info.ik_stretch_attr)
        constraint(drivers=[self.ik_foot.ctrl], driven=self.leg_info.ik_len[0].handle, constraint_type='parent', parent=self.guts)
        cmds.orientConstraint(self.ik_foot.ctrl, self.leg_info.ik_len[2], maintainOffset=True)  #FIX
        constraint(drivers=[self.leg_info.ik_len[2]], driven=roll_info.roll_grp, constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_foot.ctrl], driven=self.leg_info.end_ik_hook[2], constraint_type='parent', parent=self.guts)

        self.bind_joints = []

        jnt_par = self.joint_parent

        #bind joints
        for i,jnt in enumerate(self.guides):
            switch_jnt = create_joint(name=f'def_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.bind_joints.append(switch_jnt)
            jnt_par = switch_jnt
            constraint(drivers=[self.switch_joints[i]], driven=switch_jnt, parent=self.guts, constraint_type="parent")


        feet_info = module_info(fk_control=self.fk_controls, ik_controls=self.ik_controls, swtich_joints=self.switch_joints, fk_joints=self.fk_joints, ik_joints=self.ik_joints)
        return feet_info






