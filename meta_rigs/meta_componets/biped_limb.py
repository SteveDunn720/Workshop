

from attr import dataclass
import maya.cmds as cmds
from Workshop.meta_rigs.meta_componets.ik import create_IK_rotate_plane
from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import ReverseNode
from .module_initialize import module_prep, module_space





@dataclass
class limb_moudle:
    fk_root:str
    ik_root:str



class Limb:
    def __init__(
        self,
        part: str = "leg",
        side: str = "L",
        parent: str = "body_rig",
        control_size: float = 1.0,
        joints: list = ['thigh_l', 'calf_l', 'foot_l'],
        fk_control_space:list = [],
        ik_control_space:list = [],
        ik_end_control:bool = False

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.ik_end_control = ik_end_control
        self.fk_control_space = fk_control_space
        self.ik_control_space = ik_control_space


    def fkik_switch(self, controls:list|None):
        cmds.addAttr(self.main_grp, longName='FK_IK_Switch', attributeType='double', defaultValue=1, maxValue=1, minValue=0, keyable=True)
        self.FK_IK_Switch = f'{self.main_grp}.FK_IK_Switch'
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

    def limb_build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        self.controls = []


        self.switch_joints = []
        jnt_par = self.guts
        #switch_joints
        for i,jnt in enumerate(self.joints):
            switch_jnt = create_joint(name=f'switch_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt

        #fk_build

        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.joints):
            ctrl = create_control(
                name=f'FK_{jnt}',
                parent=ctrl_par,
                transform=jnt,
                size=self.control_size/4,
                control_shape="circle",
                direction="x",
            )

            fk_jnt = create_joint(name=f'FK_{jnt}', transform=ctrl.ctrl, parent=jnt_par)

            self.fk_joints.append(fk_jnt)
            self.fk_controls.append(ctrl)
            self.controls.append(ctrl.ctrl)
            jnt_par = fk_jnt
            ctrl_par = ctrl.ctrl
            
            

        self.ik_joints = []
        module_space(space_list=self.fk_control_space, control=self.fk_controls[0])
        jnt_par = self.guts
        #IK_build 
        for i,jnt in enumerate(self.joints):
            ik_jnt = create_joint(name=f'IK_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.ik_joints.append(ik_jnt)
            jnt_par = ik_jnt

        self.ik_handle = create_IK_rotate_plane(name=f'{self.part}_{self.side}', start_joint=self.ik_joints[0], mid_joint=self.ik_joints[1], end_joint=self.ik_joints[2], auto_pv=True, pole_vector_guide='')
        cmds.parent(self.ik_handle.handle, self.ik_handle.pole_vector, self.guts)
        self.ik_root_ctrl = create_control(
                name=f'IK_{self.joints[0]}',
                parent=self.ik_control_grp,
                transform=self.ik_handle.start_joint,
                size=self.control_size/8,
                control_shape="cube",
                direction="x",
            )
        module_space(space_list=self.ik_control_space, control=self.ik_root_ctrl)
        self.controls.append(self.ik_root_ctrl.ctrl)
        cmds.parentConstraint(self.ik_root_ctrl.ctrl, self.ik_handle.start_joint, maintainOffset=True)
        self.ik_pv_ctrl = create_control(
                name=f'{self.part}_IK_PV_{self.side}',
                parent=self.ik_control_grp,
                transform=self.ik_handle.pole_vector,
                size=self.control_size/40,
                control_shape="diamond",
                direction="x",
            )
        module_space(space_list=self.ik_control_space, control=self.ik_pv_ctrl)
        self.controls.append(self.ik_pv_ctrl.ctrl)
        cmds.parentConstraint(self.ik_pv_ctrl.ctrl, self.ik_handle.pole_vector, maintainOffset=True)

        if self.ik_end_control:
            self.ik_end_ctrl = create_control(
                name=f'IK_{self.joints[2]}',
                parent=self.ik_control_grp,
                transform=self.joints[2],
                size=self.control_size/8,
                control_shape="cube",
                direction="x",
            )
            cmds.parentConstraint(self.ik_end_ctrl.ctrl, self.ik_handle.handle, maintainOffset=True)
            cmds.orientConstraint(self.ik_end_ctrl.ctrl, self.ik_joints[2], maintainOffset=True)
            module_space(space_list=self.ik_control_space, control=self.ik_end_ctrl)
            self.controls.append(self.ik_end_ctrl.ctrl)
        else:
            self.ik_hook = self.ik_handle.handle


        self.fkik_switch(controls=self.controls)


        



