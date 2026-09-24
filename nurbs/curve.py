import maya.api.OpenMaya as om


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