"""Workshop.nurbs.curve — curve utilities and consistent direction."""
from typing import Literal

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya.api.OpenMaya import (
    MFnNurbsCurve,
    MMatrix,
    MPoint,
    MSelectionList,
    MSpace,
    MVector,
)


Axis = Literal["x", "y", "z"]
ParameterMode = Literal["normalized", "parameter"]
CurveSpace = Literal["world", "object"]



def are_curves_mirrored(curve_a: str, curve_b: str, axis: str = 'x', tolerance: float = 1e-4, allow_reversed: bool = True) -> bool:
    axis = axis.lower()
    if axis not in {'x', 'y', 'z'}:
        raise ValueError(f'Invalid mirror axis: {axis}')

    def curve_fn(curve):
        selection = om.MSelectionList()
        selection.add(get_curve_shape(curve))
        return om.MFnNurbsCurve(selection.getDagPath(0))

    a, b = curve_fn(curve_a), curve_fn(curve_b)
    if (a.numCVs, a.degree, a.form) != (b.numCVs, b.degree, b.form):
        return False
    points_a = a.cvPositions(om.MSpace.kWorld)
    points_b = b.cvPositions(om.MSpace.kWorld)
    axis_index = {'x': 0, 'y': 1, 'z': 2}[axis]

    def matches(points):
        for p_a, p_b in zip(points_a, points):
            mirrored = om.MPoint(p_a)
            mirrored[axis_index] *= -1
            if mirrored.distanceTo(p_b) > tolerance:
                return False
        return True

    return matches(points_b) or (allow_reversed and matches(reversed(points_b)))


def get_curve_shape(curve: str) -> str:
    if not cmds.objExists(curve):
        raise ValueError(f'Curve does not exist: {curve}')
    if cmds.nodeType(curve) == 'nurbsCurve':
        return curve
    shapes = cmds.listRelatives(curve, shapes=True, noIntermediate=True, fullPath=True) or []
    for shape in shapes:
        if cmds.nodeType(shape) == 'nurbsCurve':
            return shape
    raise ValueError(f'Object does not contain a NURBS curve: {curve}')


def resample_curve(curve: str, spans: int = 3, degree: int = 3) -> str:
    get_curve_shape(curve)
    if spans < 1:
        raise ValueError('Spans must be at least 1.')
    if degree not in (1, 2, 3):
        raise ValueError('Degree must be 1, 2, or 3.')
    cmds.rebuildCurve(curve, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=False, kep=True, kt=False, s=max(spans, degree), d=degree)
    return curve


def reverse_curve(curve: str) -> str:
    get_curve_shape(curve)
    cmds.reverseCurve(curve, ch=False, rpo=True)
    return curve


def orient_curve(curve: str, direction: str = 'outward', axis: str = 'X', reverse: bool = False, center: float = 0.0) -> str:
    """Orient an OPEN curve by its world-space endpoints.

    outward/inward use distance from the origin's symmetry plane on axis.
    positive/negative use signed axis travel; preserve leaves the order alone.
    reverse=True flips the final result, including preserve.
    """
    axis = axis.upper()
    direction = direction.lower()
    if axis not in {'X', 'Y', 'Z'}:
        raise ValueError(f'Invalid axis: {axis}')
    if direction not in {'outward', 'inward', 'positive', 'negative', 'preserve'}:
        raise ValueError(f'Invalid direction: {direction}')
    shape = get_curve_shape(curve)
    if cmds.getAttr(f'{shape}.form') != 0:
        if direction != 'preserve' or reverse:
            raise ValueError('Direction orientation requires an open curve; use preserve for closed curves.')
        return curve
    cvs = cmds.ls(f'{curve}.cv[*]', flatten=True) or []
    if len(cvs) < 2:
        return curve
    i = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    start = cmds.pointPosition(cvs[0], world=True)[i] - center
    end = cmds.pointPosition(cvs[-1], world=True)[i] - center
    should_reverse = False
    if direction == 'outward':
        should_reverse = abs(start) > abs(end) + 1e-6
    elif direction == 'inward':
        should_reverse = abs(start) + 1e-6 < abs(end)
    elif direction == 'positive':
        should_reverse = start > end + 1e-6
    elif direction == 'negative':
        should_reverse = start + 1e-6 < end
    if should_reverse != reverse:
        reverse_curve(curve)
    return curve


def create_curve_through_positions(
    name: str,
    positions: list[tuple[float, float, float]],
    degree: int = 3,
) -> str:
    """Create an open NURBS curve interpolating the given world-space positions.

    Maya's editPoint flag places the curve THROUGH the points, rather than
    treating them as control vertices. Degree is clamped to the point count.
    """
    if len(positions) < 2:
        raise ValueError("At least two positions are required")
    if degree < 1:
        raise ValueError("Degree must be at least 1")
    actual_degree = min(degree, len(positions) - 1)
    return cmds.curve(
        name=name,
        degree=actual_degree,
        editPoint=[tuple(point) for point in positions],
    )

def get_nurbs_curve_radius(curve: str) -> float:
    """
    Returns the radius of a NURBS circle.

    Args:
        obj (str): Transform of the NURBS circle

    Returns:
        float: radius
    """

    bbox: list[int | float] = cmds.exactWorldBoundingBox(curve)

    x: int | float = bbox[3] - bbox[0]
    y: int | float = bbox[4] - bbox[1]
    z: int | float = bbox[5] - bbox[2]

    return max(x, y, z) * 0.5



def smooth_curve_weights(
        curve: str,
        iterations: int = 5,
        strength: float = 0.5,
        preserve_ends: bool = True,
    ) -> None:
        """Smooth skin weights along a NURBS curve."""

        strength = max(0.0, min(1.0, strength))

        history = cmds.listHistory(curve) or []
        skins = cmds.ls(history, type="skinCluster")  # type:ignore

        if not skins:
            raise ValueError(f"No skinCluster found on {curve}")

        skin = skins[0]

        influences = cmds.skinCluster(
            skin,
            query=True,
            influence=True,
        )

        cvs = cmds.ls(
            f"{curve}.cv[*]",
            flatten=True,
        )

        if not cvs:
            raise ValueError(f"No CVs found on {curve}")

        for _ in range(iterations):
            weights = [
                [
                    cmds.skinPercent(
                        skin,
                        cv,
                        query=True,
                        transform=joint,
                    )
                    for joint in influences  # type:ignore
                ]
                for cv in cvs
            ]

            for i, cv in enumerate(cvs):
                if preserve_ends and i in (0, len(cvs) - 1):
                    continue

                neighbors = [weights[j] for j in (i - 1, i + 1) if 0 <= j < len(cvs)]

                if not neighbors:
                    continue

                new_weights = []

                for j, weight in enumerate(weights[i]):
                    average = sum(neighbor[j] for neighbor in neighbors) / len(neighbors)  # type:ignore

                    smoothed = weight * (1.0 - strength) + average * strength  # type:ignore

                    new_weights.append(smoothed)

                cmds.skinPercent(
                    skin,
                    cv,
                    transformValue=list(zip(influences, new_weights, strict=True)),  # type:ignore
                    normalize=True,
                )

def get_curve_point_matrix(
    curve: str,
    parameter: float,
    tangent_orient: bool = True,
    up_vector: tuple[float, float, float] = (0, 1, 0),
    aim_axis: Axis = "x",
    mirror: bool = False,
    mirror_axis: Axis = "x",
    parameter_mode: ParameterMode = "normalized",
    space: CurveSpace = "world",
) -> MMatrix:
    """
    Get a matrix at a point along a NURBS curve.

    Args:
        curve: Curve transform or shape.
        parameter: Position along the curve.
        tangent_orient: Align orientation to the curve tangent.
        up_vector: Reference up direction in the requested space.
        aim_axis: Local axis aligned with the tangent.
        mirror: Construct a mirrored orientation.
        mirror_axis: Axis used for reflection.
        parameter_mode:
            'normalized': Arc-length fraction (0-1).
            'parameter': Native NURBS curve parameter.
        space:
            'world': Return a world-space matrix.
            'object': Return a curve-local matrix.

    Returns:
        MMatrix containing translation and orientation.
    """

    # --------------------------------------------------
    # Resolve curve
    # --------------------------------------------------

    if cmds.nodeType(curve) == "nurbsCurve":
        shape = curve
    else:
        shapes = cmds.listRelatives(
            curve,
            shapes=True,
            noIntermediate=True,
            type="nurbsCurve",
            fullPath=True,
        ) or []

        if not shapes:
            raise ValueError(f"No NURBS curve found: {curve}")

        shape = shapes[0]

    selection = MSelectionList()
    selection.add(shape)

    dag_path = selection.getDagPath(0)
    fn_curve = MFnNurbsCurve(dag_path)

    # --------------------------------------------------
    # Resolve sampling space and parameter
    # --------------------------------------------------

    sample_space = (
        MSpace.kWorld
        if space == "world"
        else MSpace.kObject
    )

    if parameter_mode == "normalized":
        parameter = max(0.0, min(1.0, parameter))

        curve_param = fn_curve.findParamFromLength(
            fn_curve.length() * parameter
        )

    elif parameter_mode == "parameter":
        curve_param = parameter

    else:
        raise ValueError(
            f"Unsupported parameter mode: {parameter_mode}"
        )

    position = fn_curve.getPointAtParam(
        curve_param,
        sample_space,
    )

    # --------------------------------------------------
    # Reflection helper
    # --------------------------------------------------

    if mirror_axis not in ("x", "y", "z"):
        raise ValueError(f"Invalid mirror axis: {mirror_axis}")

    axis_index = {"x": 0, "y": 1, "z": 2}[mirror_axis]

    def reflect(vector: MVector) -> MVector:
        values = [vector.x, vector.y, vector.z]
        values[axis_index] *= -1.0
        return MVector(*values)

    if mirror:
        mirrored_position = reflect(
            MVector(position.x, position.y, position.z)
        )
        position = MPoint(
            mirrored_position.x,
            mirrored_position.y,
            mirrored_position.z,
        )

    # --------------------------------------------------
    # Construct orientation
    # --------------------------------------------------

    if tangent_orient:
        tangent = fn_curve.tangent(
            curve_param,
            sample_space,
        ).normal()

        if mirror:
            tangent = reflect(tangent)

        aim = tangent.normal()
        up = MVector(*up_vector).normal()

        if aim.length() < 1e-8:
            raise ValueError("Curve tangent has zero length")

        if up.length() < 1e-8:
            raise ValueError("Up vector cannot be zero")

        # Avoid parallel vectors.
        if abs(aim * up) > 0.999:
            candidates = (
                MVector(1, 0, 0),
                MVector(0, 1, 0),
                MVector(0, 0, 1),
            )

            up = min(
                candidates,
                key=lambda axis: abs(aim * axis),
            )

        side = (aim ^ up).normal()
        up = (side ^ aim).normal()

        if aim_axis == "x":
            x_axis = aim
            y_axis = up
            z_axis = side

        elif aim_axis == "y":
            x_axis = -side
            y_axis = aim
            z_axis = up

        elif aim_axis == "z":
            x_axis = up
            y_axis = -side
            z_axis = aim

        else:
            raise ValueError(f"Invalid aim axis: {aim_axis}")

    else:
        x_axis = MVector(1, 0, 0)
        y_axis = MVector(0, 1, 0)
        z_axis = MVector(0, 0, 1)

    # --------------------------------------------------
    # Build matrix
    # --------------------------------------------------

    matrix = MMatrix([
        x_axis.x, x_axis.y, x_axis.z, 0.0,
        y_axis.x, y_axis.y, y_axis.z, 0.0,
        z_axis.x, z_axis.y, z_axis.z, 0.0,
        position.x, position.y, position.z, 1.0,
    ])

    # --------------------------------------------------
    # Apply reflection
    # --------------------------------------------------

    if mirror:
        scale = [1.0, 1.0, 1.0]
        scale[axis_index] = -1.0

        reflection = MMatrix([
            scale[0], 0.0, 0.0, 0.0,
            0.0, scale[1], 0.0, 0.0,
            0.0, 0.0, scale[2], 0.0,
            0.0, 0.0, 0.0, 1.0,
        ])

        matrix = matrix * reflection

    return matrix
