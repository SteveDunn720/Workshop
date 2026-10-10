import maya.api.OpenMaya as om
import maya.cmds as cmds


def are_curves_mirrored(
    curve_a: str,
    curve_b: str,
    axis: str = "x",
    tolerance: float = 1e-4,
    allow_reversed: bool = True,
) -> bool:
    """
    Check whether two NURBS curves are mirrored across an axis.

    Compares CV positions in world space.

    Args:
        curve_a: First curve transform or shape.
        curve_b: Second curve transform or shape.
        axis: Mirror axis ('x', 'y', or 'z').
        tolerance: Maximum allowed positional difference.
        allow_reversed: Allow the second curve's CV order to be reversed.

    Returns:
        True if the curves are mirrored, otherwise False.
    """

    axis = axis.lower()

    if axis not in {"x", "y", "z"}:
        raise ValueError(f"Invalid mirror axis: {axis}")

    def get_curve_fn(curve: str) -> om.MFnNurbsCurve:
        selection = om.MSelectionList()
        selection.add(curve)

        dag_path = selection.getDagPath(0)

        if dag_path.node().hasFn(om.MFn.kTransform):
            dag_path.extendToShape()

        return om.MFnNurbsCurve(dag_path)

    fn_a = get_curve_fn(curve_a)
    fn_b = get_curve_fn(curve_b)

    # Curves must have matching structures.
    if fn_a.numCVs != fn_b.numCVs:
        return False

    if fn_a.degree != fn_b.degree:
        return False

    if fn_a.form != fn_b.form:
        return False

    points_a = fn_a.cvPositions(om.MSpace.kWorld)
    points_b = fn_b.cvPositions(om.MSpace.kWorld)

    axis_index = {"x": 0, "y": 1, "z": 2}[axis]

    def matches(points_b_ordered):
        for point_a, point_b in zip(points_a, points_b_ordered):

            mirrored = om.MPoint(point_a)

            mirrored[axis_index] *= -1

            if mirrored.distanceTo(point_b) > tolerance:
                return False

        return True

    # Check normal CV order.
    if matches(points_b):
        return True

    # Check reversed CV order.
    if allow_reversed and matches(reversed(points_b)):
        return True

    return False



def get_curve_shape(curve: str) -> str:
    """Return the non-intermediate NURBS curve shape."""

    if not cmds.objExists(curve):
        raise ValueError(f"Curve does not exist: {curve}")

    if cmds.nodeType(curve) == "nurbsCurve":
        return curve

    shapes = cmds.listRelatives(
        curve,
        shapes=True,
        noIntermediate=True,
        fullPath=True,
    ) or []

    for shape in shapes:
        if cmds.nodeType(shape) == "nurbsCurve":
            return shape

    raise ValueError(
        f"Object does not contain a NURBS curve: {curve}"
    )


def resample_curve(
    curve: str,
    spans: int = 3,
    degree: int = 3,
) -> str:
    """Rebuild a NURBS curve with the specified spans and degree."""

    get_curve_shape(curve)

    if spans < 1:
        raise ValueError("Spans must be at least 1.")

    if degree not in (1, 2, 3):
        raise ValueError("Degree must be 1, 2, or 3.")

    cmds.rebuildCurve(
        curve,
        ch=False,
        rpo=True,
        rt=0,
        end=1,
        kr=0,
        kcp=False,
        kep=True,
        kt=False,
        s=max(spans, degree),
        d=degree,
    )

    return curve


def reverse_curve(curve: str) -> str:
    """Reverse the parameter direction of a NURBS curve."""

    get_curve_shape(curve)

    cmds.reverseCurve(
        curve,
        ch=False,
        rpo=True,
    )

    return curve