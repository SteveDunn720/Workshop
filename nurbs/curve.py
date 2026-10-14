"""Workshop.nurbs.curve — curve utilities and consistent direction."""
import maya.api.OpenMaya as om
import maya.cmds as cmds


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
