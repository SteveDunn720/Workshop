from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.transform.utils import create_transform
from Workshop.joint import create_joint
from Workshop.spline.matrix_spline.build import (
    matrix_spline_from_transforms,
)
from Workshop.nurbs.curve import get_curve_point_matrix
from attribute_utils import set_attribute
from Workshop.control.core import Control, create_control
from Workshop.guide.curve import GuideCurve

from .utils import curve_midpoint

from .stabilization import (
    build_stabilized_drivers,
    publish_spine_measurements,
    limit_spine_length,
    create_stretch_attributes,
    create_limited_control,
    connect_limited_control,
)

@dataclass
class hybrid_info:
    mid: Control
    sub: list
    joints: list
    grp: str
    drivers: list
    chest_driver: str
    min_stretch: str
    max_stretch: str
    soft_range: str

def build_hybrid(
    part: str,
    guts: str,
    side: str,
    control_grp: str,
    guide_curve: GuideCurve,
    guide_list: list,
    cv_transforms: list,
    rig_size: float,
    hip,
    hip_des,
    hybrid_mid_shape: str,
    main_color: str,
    cog: str,
    chest: str,
    mid_control_size: float = 1 / 3,
    sub_spine_control_size: float = 1 / 30,
    sub_offset: tuple = (0, 0, 1 / 4),
    soft_influence: float = 0.2,
    longitudinal_influence: float = 0.05,
    compression_min: float = 0.25,
    compression_max: float = 0.75,
    max_offset_ratio: float = 0.3,
    min_stretch: float = 0.5,
    max_stretch: float = 1.5,
    soft_range: float = 0.05,
):

    hybrid_grp = create_transform(
        name=f"{part}_{side}_hybrid_grp",
        parent=control_grp,
    )
    stretch_attrs = create_stretch_attributes(
        hybrid_grp=hybrid_grp,
        min_stretch=min_stretch,
        max_stretch=max_stretch,
        soft_range=soft_range,
    )

    # -----------------------------------
    # Mid control
    # -----------------------------------

    mid_guide = curve_midpoint(
        curve=guide_curve.curve
    )

    mid_hip = create_transform(
        name=f"{hip_des}_mid_{side}_grp",
        parent=hybrid_grp,
        transform=hip.ctrl,
    )

    mid = create_control(
        name=f"{part}_mid_{side}",
        parent=mid_hip,
        transform=mid_guide.name,
        size=rig_size * mid_control_size,
        control_shape=hybrid_mid_shape,
        direction="y",
        color_type=main_color,
    )
    mid_input = create_limited_control(
        control=mid,
        follow_driver=chest,
        parent=hybrid_grp,
    )

    # -----------------------------------
    # Lower and upper raw drivers
    # -----------------------------------

    lower_matrix = get_curve_point_matrix(
        curve=guide_curve.curve,
        parameter=0.15,
        tangent_orient=True,
    )

    upper_matrix = get_curve_point_matrix(
        curve=guide_curve.curve,
        parameter=0.85,
        tangent_orient=True,
    )

    lower_driver = create_transform(
        name=f"{part}_{side}_lower_driver",
        parent=cv_transforms[0],
        transform=lower_matrix,
    )

    upper_driver = create_transform(
        name=f"{part}_{side}_upper_driver",
        parent=cv_transforms[-1],
        transform=upper_matrix,
    )

    for driver in (
        lower_driver,
        upper_driver,
    ):
        for axis in "XYZ":

            set_attribute(
                attr=f"{driver}.rotate{axis}",
                value=0,
            )

    # -----------------------------------
    # Raw spline drivers
    # -----------------------------------

    raw_drivers = [
        cv_transforms[0],
        lower_driver,
        mid_input.raw_driver,
        upper_driver,
        cv_transforms[-1],
    ]

    # -----------------------------------
    # Stabilized spline drivers
    # -----------------------------------

    stable_drivers = build_stabilized_drivers(
        name=f"{part}_{side}_hybrid",
        drivers=raw_drivers,
        cog=cog,
        soft_influence=soft_influence,
        longitudinal_influence=longitudinal_influence,
        compression_min=compression_min,
        compression_max=compression_max,
        max_offset_ratio=max_offset_ratio,
    )
    limited_drivers = limit_spine_length(
        name=f"{part}_{side}_hybrid",
        drivers=stable_drivers,
        cog=cog,
        hybrid_grp=hybrid_grp,
        min_stretch=stretch_attrs["min_stretch"],
        max_stretch=stretch_attrs["max_stretch"],
        soft_range=stretch_attrs["soft_range"],
    )

    connect_limited_control(
        control=mid_input,
        limited_driver=limited_drivers[2],
        name=f"{part}_{side}_mid",
    )

    # -----------------------------------
    # Sub spine controls and joints
    # -----------------------------------

    spine_off_ctrls = []
    spine_driven = []
    jnts = []

    jnt_par = guts

    for guide in guide_list:

        ctrl = create_control(
            name=guide.descriptor,
            parent=hybrid_grp,
            transform=guide.name,
            size=rig_size * sub_spine_control_size,
            control_shape="circle",
            direction="z",
            color_type=main_color,
            shape_position_offset=tuple(
                value * rig_size
                for value in sub_offset
            ),
        )

        jnt = create_joint(
            name=f"Hybrid_{guide.descriptor}",
            transform=ctrl.ctrl,
            parent=jnt_par,
            bind_set=False,
            ue_set=False,
        )

        spine_off_ctrls.append(ctrl)
        spine_driven.append(ctrl.top)

        jnt_par = jnt
        jnts.append(jnt)

    # -----------------------------------
    # Matrix spline
    # -----------------------------------

    matrix_spline_from_transforms(
        name=f"{part}_{side}_ms",
        pinned_transforms=spine_driven,
        cv_transforms=limited_drivers,
        parent=guts,
        degree=2,
    )

    # -----------------------------------
    # Squash and stretch measurements
    # -----------------------------------

    publish_spine_measurements(
        name=f"{part}_{side}_hybrid",
        hybrid_grp=hybrid_grp,
        drivers=limited_drivers,
        spline_pins=spine_driven,
        cog=cog,
    )

    return hybrid_info(
        mid=mid,
        sub=spine_off_ctrls,
        joints=jnts,
        grp=hybrid_grp,
        drivers=limited_drivers,
        chest_driver=limited_drivers[-1],
        min_stretch=stretch_attrs["min_stretch"],
        max_stretch=stretch_attrs["max_stretch"],
        soft_range=stretch_attrs["soft_range"],
    )