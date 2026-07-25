from turtle import distance

from attr import dataclass
import maya.cmds as cmds
from Workshop.meta_rigs.meta_componets.ik import create_IK_rotate_plane, create_IK_single_chain
from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import ConditionNode, MultiplyDivideNode, ReverseNode, DistanceBetweenNode, BlendTwoAttrNode, SumNode
from Workshop.transform.utils import create_transform, get_distance_between
from .module_initialize import module_prep, module_space
from Workshop.control.core import Control




@dataclass
class moudle_info:
    fk_root:Control
    ik_root:Control
    fk_ik_switch:str
    end_ik_hook:list
    ik_controls:list
    fk_controls:list
    ik_len:list
    ik_stretch_attr:str


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
        ik_end_control:bool = False,
        ikfk_blend:float = 1,
        ik_length:bool = False,

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.ik_end_control = ik_end_control
        self.fk_control_space = fk_control_space
        self.ik_control_space = ik_control_space
        self.main_control_color = 'Left' if self.side == 'l' else 'Right'
        self.ikfk_blend = ikfk_blend
        self.ik_length = ik_length


    def build_stretchy_ik(self,
            name: str,
            root_reference: str,
            ik_control: str,
            upper_joint: str,
            lower_joint: str,
            end_joint: str,
            stretch_attr: str = "stretch",
            drive_length_joint:bool = False,
            len_joint:str = ''
        ):
            """Build a basic non-compressing stretchy IK setup.

            Assumes the limb joints extend along local translate X.
            """

            if not cmds.attributeQuery(stretch_attr, node=ik_control, exists=True):
                cmds.addAttr(
                    ik_control,
                    longName=stretch_attr,
                    attributeType="double",
                    minValue=0.0,
                    maxValue=1.0,
                    defaultValue=.2,
                    keyable=True,
                )

            upper_length = cmds.getAttr(f"{lower_joint}.translateX")
            lower_length = cmds.getAttr(f"{end_joint}.translateX")

            original_length = abs(upper_length) + abs(lower_length)

            ik_distance = DistanceBetweenNode(name=f"{name}_stretch_distance")

            ik_distance.input_matrix1.connect_from(f"{root_reference}.worldMatrix[0]")
            ik_distance.input_matrix2.connect_from(f"{ik_control}.worldMatrix[0]")

            ratio = MultiplyDivideNode(name = f"{name}_stretch_ratio")
            ratio.operation.set(2)
            ratio.input2.x.set(original_length)
            ratio.input1.x.connect_from(ik_distance.distance)

            clamp = ConditionNode(name=f"{name}_stretch_condition")
            clamp.operation.set(2)
            clamp.second_term.set(1)
            clamp.color_if_false.r.set(1)
            clamp.first_term.connect_from(ratio.output.x)
            clamp.color_if_true.r.connect_from(ratio.output.x)
            
            blend = BlendTwoAttrNode(name=f"{name}_stretch_blend")
            blend.input[0].set(1)
            blend.input[1].connect_from(clamp.out_color.r)
            blend.blend.connect_from(f"{ik_control}.{stretch_attr}")

            length = MultiplyDivideNode(name=f"{name}_stretch_lengths")
            length.input1.x.set(upper_length)
            length.input1.y.set(lower_length)
            length.input2.x.connect_from(blend.output)
            length.input2.y.connect_from(blend.output)
            length.output.x.connect_to(f"{lower_joint}.translateX",)
            length.output.y.connect_to(f"{end_joint}.translateX",)

            if drive_length_joint:
                len_mult = MultiplyDivideNode(name=f"{name}_ik_len")
                if upper_length >= 0:
                    mod = 1
                elif upper_length < 0:
                    mod = -1
                len_mult.input1.x.connect_from(ik_distance.distance)
                len_mult.input2.x.set(mod)

                len_sum = SumNode(name = f"{name}_limb_len")
                len_sum.input[0].connect_from(length.output.x)
                len_sum.input[1].connect_from(length.output.y)

                len_clamp = ConditionNode(name=f"{name}_stretch_condition_len")
                len_clamp.first_term.connect_from(ratio.output.x)
                len_clamp.second_term.set(1)
                len_clamp.color_if_true.r.connect_from(len_sum.output)
                len_clamp.color_if_false.r.connect_from(len_mult.output.x)
                len_clamp.operation.set(2)
                #len_clamp.color_if_true.g.connect_from(len_mult.output.x)

                len_clamp.out_color.r.connect_to(f'{len_joint}.translateX')





    def fkik_switch(self, controls:list|None):
        cmds.addAttr(self.main_grp, longName='FK_IK_Switch', attributeType='double', defaultValue=1, maxValue=1, minValue=0, keyable=True)
        self.FK_IK_Switch = f'{self.main_grp}.FK_IK_Switch'
        rev = ReverseNode(name=f"{self.part}_FKIK_rev")
        rev.input.x.connect_from(self.FK_IK_Switch)
        rev.output.x.connect_to(f'{self.ik_control_grp}.visibility')
        cmds.connectAttr(self.FK_IK_Switch, f'{self.fk_control_grp}.visibility')
        for i,jnt in enumerate(self.joints):
            if not self.ik_end_control and i == len(self.joints) - 1:
                continue
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
            if not self.ik_end_control and i == len(self.joints) - 1:
                continue
            switch_jnt = create_joint(name=f'switch_{jnt}', transform=jnt, parent=jnt_par, connect=False)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt

        #fk_build

        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.joints):
            if not self.ik_end_control and i == len(self.joints) - 1:
                continue
            ctrl = create_control(
                name=f'FK_{jnt}',
                parent=ctrl_par,
                transform=jnt,
                size=self.control_size/4,
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
            jnt_name = jnt
            if not self.ik_end_control and i == len(self.joints) - 1:
                jnt_name = f'{jnt}_hook'
            ik_jnt = create_joint(name=f'IK_{jnt_name}', transform=jnt, parent=jnt_par, connect=False)
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
                color_type=self.main_control_color
            )
        module_space(space_list=self.ik_control_space, control=self.ik_root_ctrl)
        self.controls.append(self.ik_root_ctrl.ctrl)
        self.ik_controls.append(self.ik_root_ctrl.ctrl)
        cmds.parentConstraint(self.ik_root_ctrl.ctrl, self.ik_handle.start_joint, maintainOffset=True)
        self.ik_pv_ctrl = create_control(
                name=f'{self.part}_IK_PV_{self.side}',
                parent=self.ik_control_grp,
                transform=self.ik_handle.pole_vector,
                size=self.control_size/10,
                control_shape="sims",
                direction="y",
                color_type=self.main_control_color,
                shape_rotation_offset=(90,-90,0)
            )
        module_space(space_list=self.ik_control_space, control=self.ik_pv_ctrl)
        self.controls.append(self.ik_pv_ctrl.ctrl)
        self.ik_controls.append(self.ik_pv_ctrl.ctrl)
        cmds.parentConstraint(self.ik_pv_ctrl.ctrl, self.ik_handle.pole_vector, maintainOffset=True)

        if self.ik_end_control:
            self.ik_end_ctrl = create_control(
                name=f'IK_{self.joints[2]}',
                parent=self.ik_control_grp,
                transform=self.joints[2],
                size=self.control_size/8,
                control_shape="cube",
                direction="x",
                color_type=self.main_control_color
            )
            cmds.parentConstraint(self.ik_end_ctrl.ctrl, self.ik_handle.handle, maintainOffset=True)
            cmds.orientConstraint(self.ik_end_ctrl.ctrl, self.ik_joints[2], maintainOffset=True)
            module_space(space_list=self.ik_control_space, control=self.ik_end_ctrl)
            self.controls.append(self.ik_end_ctrl.ctrl)
            self.ik_controls.append(self.ik_pv_ctrl.ctrl)
            self.ik_hook = None
        else:
            self.ik_end_ctrl = create_control(
                name=f'IK_{self.joints[2]}',
                parent=self.ik_control_grp,
                transform=self.joints[2],
                size=self.control_size/8,
                control_shape="cube",
                direction="x",
                color_type=self.main_control_color
            )
            cmds.parentConstraint(self.ik_end_ctrl.ctrl, self.ik_handle.handle, maintainOffset=True)
            cmds.orientConstraint(self.ik_end_ctrl.ctrl, self.ik_joints[2], maintainOffset=True)
            self.controls.append(self.ik_end_ctrl.ctrl)
            self.ik_controls.append(self.ik_pv_ctrl.ctrl)
            cmds.hide(self.ik_end_ctrl.ctrl)
            #self.ik_hook = None
            self.ik_hook = self.ik_end_ctrl.ctrl
            #self.ik_controls.append('')


        self.fkik_switch(controls=self.controls)
        cmds.setAttr(self.FK_IK_Switch, self.ikfk_blend)


        if self.ik_length:
            self.ik_len_joints = []
            jnt_par = self.guts
            for i,jnt in enumerate(self.joints):
                if i == 1:
                    pass
                else:
                    jnt_name = jnt
                    ik_jnt = create_joint(name=f'IK_len_{jnt_name}', transform=jnt, parent=jnt_par, connect=False)
                    self.ik_len_joints.append(ik_jnt)
                    jnt_par = ik_jnt
            self.ik_len_chain = create_IK_single_chain(name=f'{self.part}_len_{self.side}', start_joint=self.ik_len_joints[0], end_joint=self.ik_len_joints[1],)
            cmds.parent(self.ik_len_chain.handle, self.guts)
            cmds.pointConstraint(self.ik_joints[0], self.ik_len_joints[0])
            ik_len = [self.ik_len_chain, self.ik_len_joints[0], self.ik_len_joints[1]]
        else:
            ik_len = []

        #stretch
        
        if not self.ik_end_control:
            end_pos = create_transform(name=f'{self.joints[2]}_len_pos', transform=self.joints[2], parent=self.guts)
        else:
            end_pos = self.ik_end_ctrl.ctrl

        self.build_stretchy_ik(
            name=f'{self.joints[0]}',
            root_reference=self.ik_root_ctrl.ctrl,
            ik_control=end_pos,
            upper_joint=self.ik_joints[0],
            lower_joint=self.ik_joints[1],
            end_joint=self.ik_joints[2],
            stretch_attr= "stretch",
            drive_length_joint=self.ik_length,
            len_joint=ik_len[2] if self.ik_length else '')



        self.info = moudle_info(
                fk_root = self.fk_controls[0],
                ik_root = self.ik_controls[0],
                fk_ik_switch = self.FK_IK_Switch,
                end_ik_hook = [self.ik_hook, self.ik_joints[-1], end_pos],
                ik_controls = self.ik_controls,
                fk_controls = self.fk_controls,
                ik_len=ik_len,
                ik_stretch_attr = f'{end_pos}.stretch'
                )
        
        return self.info



        



