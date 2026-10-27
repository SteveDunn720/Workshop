from dataclasses import dataclass

from Workshop.transform.utils import create_transform
from Workshop.joint import create_joint
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms
from .utils import curve_midpoint
from Workshop.control.core import Control, create_control

@dataclass
class hybrid_info:
    mid:Control
    sub:list
    joints:list
    grp:str



def build_hybrid(part:str, guts:str, side:str, control_grp:str, guide_curve, guide_list:list, cv_transforms:list,  rig_size:float, hip, hip_des, hybrid_mid_shape:str, main_color:str, mid_control_size:float=1/3, sub_spine_control_size = 1/30, sub_offset =(0,0,1/4)):
    hybrid_grp = create_transform(name=f'{part}_{side}_hybrid_grp', parent=control_grp)

    mid_guide = curve_midpoint(curve=guide_curve.curve)

    mid_hip = create_transform(name=f'{hip_des}_mid_{side}_grp', parent=hybrid_grp, transform=hip.ctrl)
    mid = create_control(
        name=f'{part}_mid_{side}',
        parent=mid_hip,
        transform=mid_guide.name,
        size=rig_size * mid_control_size,
        control_shape=hybrid_mid_shape,
        direction="y",
        color_type=main_color
    )

    cv_transforms.insert(1, mid.ctrl)

    spine_off_ctrls = []
    spine_driven = []
    jnts = []

    jnt_par = guts
    for i, g in enumerate(guide_list): 
        ctrl = create_control(
                name=g.descriptor,
                parent=hybrid_grp,
                transform=g.name,
                size=rig_size * sub_spine_control_size,
                control_shape="circle",
                direction="z",
                color_type=main_color,
                shape_position_offset= tuple(value * rig_size for value in sub_offset)
            )
        jnt = create_joint(name=f'Hybrid_{g.descriptor}', transform=ctrl.ctrl, parent=jnt_par, bind_set= False, ue_set=False,)
        spine_off_ctrls.append(ctrl)
        spine_driven.append(ctrl.top)
        jnt_par=jnt
        jnts.append(jnt)


    matrix_spline_from_transforms(
        name=f"{part}_{side}_ms",
        pinned_transforms=spine_driven,
        cv_transforms=cv_transforms,
        parent=guts,
        degree=2,
    )

    return hybrid_info(mid=mid, sub=spine_off_ctrls, joints=jnts, grp=hybrid_grp)
