
from dataclasses import dataclass

from Workshop.control.core import create_control
from Workshop.joint import create_joint


@dataclass
class SimpleFkInfo:
    joints:list
    controls:list

def build_simple_fk(fk_joint_parent:str, fk_control_grp:str, guide_list:list, rig_size:float, control_color:str, rig_size:float = .25, control_shape:str="circle"):
    jnt_par = fk_joint_parent
    ctrl_par = fk_control_grp

    joints = []
    controls = []
    for i,jnt in enumerate(guide_list):
        ctrl = create_control(
            name=f'FK_{jnt.descriptor}',
            parent=ctrl_par,
            transform=jnt.name,
            size=rig_size * rig_size,
            control_shape=control_shape,
            direction="y",
            color_type=control_color
        )

        fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par, bind_set= False, ue_set=False,)

        joints.append(fk_jnt)
        controls.append(ctrl)
        jnt_par = fk_jnt
        ctrl_par = ctrl.ctrl

    return SimpleFkInfo(joints=joints, controls=controls)