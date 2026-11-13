
from dataclasses import dataclass
from weakref import proxy
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform.utils import get_position, match_transform, convert_to_matrix
from Workshop.joint import create_joint
from Workshop.maya_api.node import ConditionNode, DistanceBetweenNode, MultiplyDivideNode, ReverseNode
from Workshop.guide.core import GuideInfo
from Workshop.transform.constraint import constraint
from Workshop.maya_api.attribute_utils import add_proxy, set_attribute

from ..ik import auto_pv_space, create_IK_single_chain
from ..module_shared import fkik_switch, module_prep, module_space

from.utils import build_compressible_ik_length
from .roll import Roll

@dataclass
class module_info:
    ik_controls:list
    fk_control:list
    swtich_joints:list
    fk_joints:list
    ik_joints:list
    bind_joints:list

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
        rig_size: float = 1.0,
        guides: list = [],
        fk_control_space:list = [],
        ik_control_space:list = [],
        ik_hook:list=[],
        fkik_switch_attr:str = '',
        joint_parent:str = 'foot_joint',
        fk_start_size:float = 6.0,
        fk_shape:str = "fk",
        fk_twist:tuple = (0,90,0),
        ik_foot_size:float = 1/4,
        ik_foot_shape:str = "foot",
        ik_toe_shape:str = "ik_toes",
        ik_toe_size:float = 1/8,
        ik_foot_twist:tuple = (0,180,0),

        

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: list = guides
        self.fk_control_space = fk_control_space
        self.ik_control_space = ik_control_space
        self.main_control_color = 'Left' if self.side == 'L' else 'Right' 
        self.ik_hook = ik_hook
        self.feet_guides = feet_guides
        self.fkik_switch_attr = fkik_switch_attr
        self.leg_info = leg_info
        self.joint_parent = joint_parent
        self.fk_start_size = fk_start_size
        self.fk_shape = fk_shape
        self.fk_twist = fk_twist
        self.ik_foot_size = ik_foot_size
        self.ik_foot_shape = ik_foot_shape
        self.ik_toe_shape = ik_toe_shape
        self.ik_toe_size = ik_toe_size
        self.ik_foot_twist = ik_foot_twist

    # -------------------
    # Build steps
    # -------------------


    def get_ground_distance(self, object)->float:
        pos = get_position(object)

        return pos[1]
        

    def build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        ground_offset = self.get_ground_distance(object=self.guides[0].name)
        self.controls = []


        self.switch_joints = []

        jnt_par = self.guts
        #switch_joints
        for i,jnt in enumerate(self.guides):
            switch_jnt = create_joint(name=f'switch_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt
        
        #Fk_build
        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.guides):
            ctrl = create_control(
                name=f'FK_{jnt.descriptor}',
                parent=ctrl_par,
                transform=jnt.name,
                size=self.rig_size * 1/(self.fk_start_size * (i + 1)),
                control_shape=self.fk_shape,
                direction="y",
                color_type=self.main_control_color,
                shape_rotation_offset=self.fk_twist
            )

            fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par, bind_set= False, ue_set=False,)

            self.fk_joints.append(fk_jnt)
            self.fk_controls.append(ctrl)
            self.controls.append(ctrl.ctrl)
            jnt_par = fk_jnt
            ctrl_par = ctrl.ctrl

        constraint(drivers=[self.fk_controls[0].ctrl], driven=self.leg_info.fk_hook)
            
            

        self.ik_joints = []
        self.ik_controls = []
        module_space(space_list=self.fk_control_space, control=self.fk_controls[0])
        jnt_par = self.guts
        

        #IK_build 
        for i,jnt in enumerate(self.guides):
            ik_jnt = create_joint(name=f'IK_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.ik_joints.append(ik_jnt)
            jnt_par = ik_jnt
        
        ctrl_par = self.ik_control_grp

        temp_guide = cmds.duplicate(self.guides[0].name)[0]

        for axis in ['X', 'Y', 'Z']:
            num = 180 if axis == 'X' else 0

            set_attribute(f'{temp_guide}.jointOrient{axis}', num)

        self.ik_foot = create_control(
                name=f'IK_{self.guides[0].descriptor}_main',
                parent=ctrl_par,
                transform=temp_guide,
                size=self.rig_size * self.ik_foot_size,
                control_shape=self.ik_foot_shape,
                direction="y",
                color_type=self.main_control_color,
                shape_position_offset=(0, -ground_offset, -self.rig_size/10),
                shape_rotation_offset=self.ik_foot_twist
            )

        cmds.delete(temp_guide)

        module_space(space_list=self.ik_control_space, control=self.ik_foot)
        self.ik_controls.append(self.ik_foot)
        self.controls.append(self.ik_foot)
        self.ik_toes = create_control(
                name=f'IK_{self.guides[1].descriptor}',
                parent=ctrl_par,
                transform=f'{self.guides[1].name}',
                size=self.rig_size * self.ik_toe_size,
                control_shape=self.ik_toe_shape,
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
            ik_jnt = create_joint(name=f'IK_roll_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.ik_roll_joints.append(ik_jnt)
            jnt_par = ik_jnt

        roll_ik = create_IK_single_chain(name=f'{self.part}_{self.side}_roll', start_joint=self.ik_roll_joints[0], end_joint=self.ik_roll_joints[1])
        cmds.parent(roll_ik.handle, self.guts)

        roll = Roll(part='roll', rig_size=self.rig_size, side=self.side, joints= [f'foot_{self.side}', f'ball_{self.side}'], guides=self.feet_guides, control_parent=self.ik_foot.ctrl)
        roll_info = roll.build()

        #self.build_compressible_ik_length(name=f'{self.part}_{self.side}_roll', root_reference=roll_info.roll_ctrl.top, ik_control=roll_info.down_driver, down_axis='X', length_joint=self.ik_roll_joints[1])

        match_transform(transform=roll_info.roll_grp, target_transform=self.feet_guides.og_foot_pos[-2])

        cmds.parent(roll_info.roll_grp, self.ik_foot.ctrl)

        add_proxy(source=self.leg_info.ik_stretch_attr, proxy_list=[self.ik_foot.ctrl], proxy_name='stretch')

        # connecting the rool to the foot and leg

        constraint(drivers=[roll_info.down_driver], driven=roll_ik.handle, constraint_type='parent', parent=self.guts)
        constraint(drivers=[roll_info.down_driver], driven=self.ik_roll_joints[1], constraint_type='orient', parent=self.guts)
        constraint(drivers=[roll_info.up_driver], driven=self.ik_hook[0], constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_hook[1]], driven=self.ik_roll_joints[0], constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_roll_joints[0]], driven=self.ik_joints[0], constraint_type='parent', parent=self.guts)
        constraint(drivers=[roll_info.down_driver], driven=self.ik_toes.top, constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_foot.ctrl], driven=self.leg_info.ik_len[0].handle, constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_foot.ctrl], driven=self.leg_info.ik_len[2], constraint_type='orient', parent=self.guts)
        constraint(drivers=[self.leg_info.ik_len[2]], driven=roll_info.roll_grp, constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_foot.ctrl], driven=self.leg_info.end_ik_hook[2], constraint_type='parent', parent=self.guts)

        self.bind_joints = []

        jnt_par = self.joint_parent


        #bind joints
        for i,jnt in enumerate(self.guides):
            switch_jnt = create_joint(name=f'def_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False)
            self.bind_joints.append(switch_jnt)
            jnt_par = switch_jnt
            constraint(drivers=[self.switch_joints[i]], driven=switch_jnt, parent=self.guts, constraint_type="parent")


        if self.leg_info.auto_pv_driven:
            pv_auto = auto_pv_space(end_control=self.ik_foot, pv_control=self.leg_info.ik_controls[1], parent_space=self.ik_control_space[0], parent=self.guts, swing_range=((-90, 90),(-self.rig_size/10, self.rig_size/10)))
            cmds.parent(self.leg_info.auto_pv_driven, pv_auto.driver)


        feet_info = module_info(fk_control=self.fk_controls, ik_controls=self.ik_controls, swtich_joints=self.switch_joints, fk_joints=self.fk_joints, ik_joints=self.ik_joints, bind_joints=self.bind_joints,)
        return feet_info






