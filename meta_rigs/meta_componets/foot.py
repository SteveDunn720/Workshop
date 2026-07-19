from attr import dataclass
from Workshop.control.core import Control
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform.utils import get_position, match_transform
from .module_initialize import module_prep, module_space
from Workshop.joint import create_joint
from Workshop.maya_api.node import ReverseNode
from Workshop.meta_rigs.metahuman_rig_prep import foot_guides
from Workshop.meta_rigs.meta_componets.roll import Roll

@dataclass
class module_info:
    cog_control:Control
    hip_control:Control

class Foot:
    def __init__(
        self,
        feet_guides:foot_guides,
        part: str = "foot",
        side: str = "l",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joints: list = ['foot_l', 'ball_l'],
        fk_control_space:list = [],
        ik_control_space:list = [],
        ik_hook:str='',
        fkik_switch_attr:str = '',

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.fk_control_space = fk_control_space
        self.ik_control_space = ik_control_space
        self.main_control_color = 'Left' if self.side == 'l' else 'Right' 
        self.ik_hook = ik_hook
        self.feet_guides = feet_guides
        self.fkik_switch_attr = fkik_switch_attr
        self.mod = 1 if side == 'l' else -1

    # -------------------
    # Build steps
    # -------------------


    def get_ground_distance(self, object)->float:
        pos = get_position(object)

        return pos[1]
        


    def fkik_switch(self, controls:list|None, attr=''):
        #cmds.addAttr(self.main_grp, longName='FK_IK_Switch', attributeType='double', defaultValue=1, maxValue=1, minValue=0, keyable=True)
        self.FK_IK_Switch = attr #f'{self.main_grp}.FK_IK_Switch'
        rev = ReverseNode(name=f"{self.part}_FKIK_rev")
        rev.input.x.connect_from(self.FK_IK_Switch)
        rev.output.x.connect_to(f'{self.ik_control_grp}.visibility')
        cmds.connectAttr(self.FK_IK_Switch, f'{self.fk_control_grp}.visibility')
        for i,jnt in enumerate(self.joints):
            parent_con:str = cmds.parentConstraint(self.fk_joints[i], self.ik_joints[i], self.switch_joints[i], maintainOffset=True)[0] #type:ignore
            #scale_con:str = cmds.scaleConstraint(self.fk_joints[i], self.ik_joints[i], self.switch_joints[i], maintainOffset=True)[0] #type:ignore
            parent_weights = cmds.parentConstraint(parent_con, query=True, weightAliasList=True)
            #scale_weights = cmds.parentConstraint(scale_con, query=True, weightAliasList=True)
            
            cmds.connectAttr(self.FK_IK_Switch, f'{parent_con}.{parent_weights[0]}')
            #cmds.connectAttr(self.FK_IK_Switch, f'{scale_con}.{scale_weights[0]}')
            cmds.connectAttr(rev.output.x, f'{parent_con}.{parent_weights[1]}')
            #cmds.connectAttr(rev.output.x, f'{scale_con}.{scale_weights[1]}')

            cmds.parentConstraint(self.switch_joints[i], jnt, maintainOffset=True)
            #cmds.scaleConstraint(self.switch_joints[i], jnt, maintainOffset=True)
        if controls:
            for control in controls:
                cmds.addAttr(control, longName='FKIK_Switch', proxy=self.FK_IK_Switch)

    def foot_build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        ground_offset = self.get_ground_distance(object=self.joints[0])
        self.controls = []


        self.switch_joints = []

        jnt_par = self.guts
        #switch_joints
        for i,jnt in enumerate(self.joints):
            switch_jnt = create_joint(name=f'switch_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt
        
        #Fk_build
        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.joints):
            ctrl = create_control(
                name=f'FK_{jnt}',
                parent=ctrl_par,
                transform=jnt,
                size=self.control_size/(4 * (i + 1)),
                control_shape="circle",
                direction="x",
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
        for i,jnt in enumerate(self.joints):
            ik_jnt = create_joint(name=f'IK_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.ik_joints.append(ik_jnt)
            jnt_par = ik_jnt
        
        ctrl_par = self.ik_control_grp

        self.ik_foot = create_control(
                name=f'IK_{self.joints[0]}_main',
                parent=ctrl_par,
                transform=f'{self.joints[0]}',
                size=self.control_size/4,
                control_shape="circle",
                direction="x",
                color_type=self.main_control_color,
                shape_position_offset=(-ground_offset * self.mod, 0, 0)
            )
        
        self.ik_controls.append(self.ik_foot)

        

        self.controls.append(self.ik_foot)
        self.ik_toes = create_control(
                name=f'IK_{self.joints[1]}',
                parent=ctrl_par,
                transform=f'{self.joints[1]}',
                size=self.control_size/8,
                control_shape="circle",
                direction="x",
                color_type=self.main_control_color,
            )
        cmds.parentConstraint(self.ik_toes.ctrl, self.ik_joints[1])
        self.ik_controls.append(self.ik_toes)
        self.controls.append(self.ik_toes)

        self.fkik_switch(controls=self.controls, attr=self.fkik_switch_attr)

        roll = Roll(part='roll', control_size=self.control_size, side=self.side, joints= [f'foot_{self.side}', f'ball_{self.side}'], guides=self.feet_guides, control_parent=self.ik_foot.ctrl)
        roll_info = roll.roll_build()

        match_transform(transform=roll_info.roll_grp, target_transform=self.feet_guides.og_foot_pos[-2].name)
        cmds.setAttr(f'{roll_info.roll_grp}.rotateY', self.feet_guides.aim_angle)
        cmds.parent(roll_info.roll_grp, self.ik_foot.ctrl)
        cmds.parentConstraint(roll_info.down_driver, self.ik_toes.top, maintainOffset=True)
        cmds.parentConstraint(roll_info.up_driver, self.ik_hook[0], maintainOffset=True)
        cmds.parentConstraint(self.ik_hook[1], self.ik_joints[0])
        cmds.orientConstraint(roll_info.up_driver, self.ik_hook[1], maintainOffset=True)





