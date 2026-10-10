from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds
from maya.api import OpenMaya as om

from Workshop.control import create_control
from Workshop.guide.core import GuideInfo, read_guide
from Workshop.joint import create_joint
from Workshop.nurbs.curve import get_curve_shape
from Workshop.transform.utils import create_transform
from Workshop.transform.constraint import constraint

from Workshop.canon_autorigger.module_schema import (
    ModuleCurveGuide,
    ModuleRelationship,
    ModuleSetting,
)

from .module_initialize import module_prep, module_space

# Update this import if your Workshop spline solver has a different path.
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms


@dataclass
class MatrixSplineInfo:
    controls: list
    joints: list[str]
    pinned_transforms: list[str]
    spline: object


def get_curve_matrix_at_percent(
    curve: str,
    percent: float,
) -> om.MMatrix:
    """Sample a world-space matrix along a curve by arc length."""

    selection = om.MSelectionList()
    selection.add(get_curve_shape(curve))

    dag_path = selection.getDagPath(0)
    curve_fn = om.MFnNurbsCurve(dag_path)

    percent = max(0.0, min(1.0, percent))

    parameter = curve_fn.findParamFromLength(
        curve_fn.length() * percent
    )

    point = curve_fn.getPointAtParam(
        parameter,
        om.MSpace.kWorld,
    )

    y_axis = curve_fn.tangent(
        parameter,
        om.MSpace.kWorld,
    ).normal()

    world_up = om.MVector(0, 0, 1)

    if abs(y_axis * world_up) > 0.999:
        world_up = om.MVector(1, 0, 0)

    x_axis = world_up ^ y_axis
    x_axis.normalize()

    z_axis = y_axis ^ x_axis
    z_axis.normalize()

    return om.MMatrix([
        x_axis.x, x_axis.y, x_axis.z, 0,
        y_axis.x, y_axis.y, y_axis.z, 0,
        z_axis.x, z_axis.y, z_axis.z, 0,
        point.x, point.y, point.z, 1,
    ])


class MatrixSpline:

    MODULE_NAME = "matrix_spline"
    DISPLAY_NAME = "Matrix Spline"

    GUIDES = (
        ModuleCurveGuide(
            name="curve",
            spans=3,
            degree=3,
            length=10.0,
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="driver_count",
            setting_type="int",
            default=3,
        ),
        ModuleSetting(
            name="divisions",
            setting_type="int",
            default=7,
        ),
        ModuleSetting(
            name="degree",
            setting_type="int",
            default=2,
        ),
        ModuleSetting(
            name="control_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="control_shape",
            setting_type="control_shape",
            default="circle",
        ),
        ModuleSetting(
            name="control_color",
            setting_type="string",
            default="MISC",
        ),
        ModuleSetting(
            name="constraint_type",
            setting_type="string",
            default="parent",
        ),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="control_space",
            relationship_type="control_space",
            default="auto",
        ),
    )

    def __init__(
        self,
        part: str = "spline",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list[GuideInfo] | None = None,
        joint_parent: str = "skel",
        control_space: list[str] | None = None,
        driver_count: int = 3,
        divisions: int = 7,
        degree: int = 2,
        control_shape: str = "circle",
        control_color: str = "MISC",
        constraint_type: str = "parent",
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.control_size = control_size
        self.guides = guides or []
        self.joint_parent = joint_parent
        self.control_space = control_space or []

        self.driver_count = driver_count
        self.divisions = divisions
        self.degree = degree
        self.control_shape = control_shape
        self.control_color = control_color
        self.constraint_type = constraint_type

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:
        if not guides:
            return {
                "controls": [],
                "joints": [],
                "output_control": None,
                "output_joint": None,
            }

        driver_count = max(
            2,
            int(settings.get("driver_count", 3)),
        )

        divisions = max(
            2,
            int(settings.get("divisions", 7)),
        )

        controls = [
            f"{part}_{i:02d}_{side}_ctrl"
            for i in range(driver_count)
        ]

        joints = [
            f"def_{part}_{i:02d}_{side}_jnt"
            for i in range(divisions)
        ]

        return {
            "controls": controls,
            "joints": joints,
            "output_control": controls[0],
            "output_joint": joints[0],
        }

    def build(self) -> MatrixSplineInfo:
        if not self.guides:
            raise ValueError("MatrixSpline requires a curve guide.")

        if self.driver_count < 2 or self.divisions < 2:
            raise ValueError(
                "MatrixSpline requires at least 2 drivers and 2 joints."
            )

        if self.constraint_type not in ("parent", "matrix"):
            raise ValueError(
                "constraint_type must be 'parent' or 'matrix'."
            )

        guide = self.guides[0]

        if isinstance(guide, str):
            guide = read_guide(guide)

        curve = guide.name
        get_curve_shape(curve)

        prep = module_prep(
            part=self.part,
            parent=self.parent,
            side=self.side,
            fkik=False,
            gut=True,
        )

        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        # -----------------------------------------
        # DRIVER CONTROLS
        # -----------------------------------------

        self.controls = []

        for index in range(self.driver_count):
            percent = index / (self.driver_count - 1)

            matrix = get_curve_matrix_at_percent(
                curve,
                percent,
            )

            name = f"{self.part}_{index:02d}_{self.side}"

            control = create_control(
                name=name,
                parent=self.control_grp,
                transform=matrix,
                size=self.control_size,
                control_shape=self.control_shape,
                direction="y",
                color_type=self.control_color,
            )

            self.controls.append(control)

        # Apply module spaces to the root control.
        module_space(
            control=self.controls[0],
            space_list=self.control_space,
        )

        # -----------------------------------------
        # PINNED TRANSFORMS + BIND JOINTS
        # -----------------------------------------

        self.pinned_transforms = []
        self.joints = []

        current_joint_parent = self.joint_parent

        for index in range(self.divisions):
            percent = index / (self.divisions - 1)

            matrix = get_curve_matrix_at_percent(
                curve,
                percent,
            )

            name = f"{self.part}_{index:02d}_{self.side}"

            pinned = create_transform(
                name=f"{name}_spline",
                parent=self.guts,
                transform=matrix,
            )

            joint = create_joint(
                name=f"def_{name}",
                parent=current_joint_parent,
                transform=matrix,
                connect=False,
            )

            self.pinned_transforms.append(pinned)
            self.joints.append(joint)

            current_joint_parent = joint

        # -----------------------------------------
        # MATRIX SPLINE SOLVER
        # -----------------------------------------

        self.spline = matrix_spline_from_transforms(
            name=f"{self.part}_{self.side}",
            pinned_transforms=self.pinned_transforms,
            cv_transforms=[
                control.ctrl
                for control in self.controls
            ],
            parent=self.guts,
            degree=min(
                self.degree,
                self.driver_count - 1,
            ),
        )

        # -----------------------------------------
        # DRIVE JOINTS
        # -----------------------------------------

        for pinned, joint in zip(
            self.pinned_transforms,
            self.joints,
        ):
            if self.constraint_type == "parent":
                cmds.parentConstraint(
                    pinned,
                    joint,
                    maintainOffset=False,
                )
            else:
                constraint(
                    drivers=[pinned],
                    driven=joint,
                    constraint_type="parent",
                    parent=self.guts,
                )

        return MatrixSplineInfo(
            controls=self.controls,
            joints=self.joints,
            pinned_transforms=self.pinned_transforms,
            spline=self.spline,
        )