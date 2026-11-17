from dataclasses import dataclass

from Workshop.transform.utils import create_transform
from Workshop.joint import create_joint
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms
from Workshop.nurbs.curve import get_curve_point_matrix
from Workshop.maya_api.attribute_utils import set_attribute
from .utils import curve_midpoint
from Workshop.control.core import Control, create_control
from Workshop.guide.curve import GuideCurve

@dataclass
class hybrid_info:
    mid:Control
    sub:list
    joints:list
    grp:str



def build_hybrid(part:str, guts:str, side:str, control_grp:str, guide_curve:GuideCurve, guide_list:list, cv_transforms:list,  rig_size:float, hip, hip_des, hybrid_mid_shape:str, main_color:str, mid_control_size:float=1/3, sub_spine_control_size = 1/30, sub_offset =(0,0,1/4)):
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

    lower_matrix = get_curve_point_matrix(
        curve= guide_curve.curve,
        parameter=.15,
        tangent_orient=True,
    )

    upper_matrix = get_curve_point_matrix(
            curve= guide_curve.curve,
            parameter=.85,
            tangent_orient=True,
        )

    lower_driver = create_transform(name=f'{part}_lower_driver', parent=cv_transforms[0], transform=lower_matrix)
    upper_driver = create_transform(name=f'{part}_upper_driver', parent=cv_transforms[-1], transform=upper_matrix)
    for attrs in ['rotateX', 'rotateY', 'rotateZ']:
        set_attribute(attr=f'{lower_driver}.{attrs}', value=0)
        set_attribute(attr=f'{upper_driver}.{attrs}', value=0)

    cv_transforms.insert(1, lower_driver)
    cv_transforms.insert(2, mid.ctrl)
    cv_transforms.insert(3, upper_driver)

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
