

from turtle import position
from attr import dataclass
import maya.cmds as cmds
from Workshop.meta_rigs.meta_componets.ik import create_IK_rotate_plane
from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import ReverseNode
from .module_initialize import module_prep, module_space
from Workshop.control.core import Control




@dataclass
class moudle_info:
    fk_root:Control
    fk_controls:list


class Metacarpal:
    def __init__(
        self,
        part: str = "leg",
        side: str = "L",
        parent: str = "body_rig",
        control_size: float = 1.0,
        joints: list = ['thigh_l', 'calf_l', 'foot_l'],
        fk_control_space:list = [],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_size: float = control_size
        self.joints: list = joints
        self.fk_control_space = fk_control_space
        self.main_control_color = 'Left' if self.side == 'l' else 'Right'
        self.sub_control_color = 'SubLeft' if self.side == 'l' else 'SubRight'

    def metacarpal_build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        self.controls = []



        #fk_build

        self.fk_controls = []

        ctrl_par = self.fk_control_grp

        self.roll_ctrl = create_control(
                name=f'{self.part}_expresion_{self.side}',
                parent=ctrl_par,
                transform=self.joints[0],
                size=self.control_size/32,
                control_shape="sphere",
                direction="x",
                color_type=self.sub_control_color,
                shape_position_offset=(0, -4, 0)
            )
        
        self.controls.append(self.roll_ctrl.ctrl)


        for i,jnt in enumerate(self.joints):
            ctrl = create_control(
                name=f'FK_{jnt}',
                parent=ctrl_par,
                transform=jnt,
                size=self.control_size/32,
                control_shape="circle",
                direction="x",
                color_type=self.main_control_color,
                sdk_offset=True
            )
            for attr in ['translate', 'rotate']:
                for axis in ['X', 'Z', 'Y']:
                    cmds.connectAttr(f'{self.roll_ctrl.ctrl}.{attr}{axis}', f'{ctrl.sdk}.{attr}{axis}')


            self.fk_controls.append(ctrl)
            self.controls.append(ctrl.ctrl)
            ctrl_par = ctrl.ctrl
            cmds.parentConstraint(ctrl.ctrl, jnt, maintainOffset=True)
            
            

    
        module_space(space_list=self.fk_control_space, control=self.fk_controls[0])
        module_space(space_list=self.fk_control_space, control=self.roll_ctrl)
        self.info = moudle_info(
                fk_root = self.fk_controls[0],
                fk_controls = self.fk_controls,
                )
        
        return self.info



        



