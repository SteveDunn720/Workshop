from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from turtle import shape
from typing import Iterator

from maya import cmds
from maya.api.OpenMaya import MMatrix

from Workshop.control.serialize import ControlShape, create_curve
from Workshop.maya_api.enum import RotateOrder
from Workshop.name import MIDDLE_SIDE_NAME, get_side
from Workshop.transform import create_transform
from Workshop.transform.matrix import get_world_matrix
from Workshop.transform.structs import Direction
from Workshop.transform.utils import bake_shape, match_location, partial_path_name

CONTROL_SUFFIX = "_ctrl"
TOP_SUFFIX = "_offset"
SDK_SUFFIX = "_sdk"

_control_collection: ContextVar[list[Control] | None] = ContextVar(
    "control_collection", default=None
)


@contextmanager
def collect_controls() -> Iterator[list[Control]]:
    """
    Collect controls created inside this block.

    Any controls created within the `with` statement are added to a list,
    which is returned when the block finishes. Nested blocks are supported,
    and inner results are included in the outer list.

    Returns:
        list[Control]: Controls created in the block.
    """
    # Create a bucket to collect the controls created in the with block
    # then put it into the ContextVar so that _register_control will add to this bucket
    bucket: list[Control] = []
    parent_bucket = _control_collection.get()
    token = _control_collection.set(bucket)
    try:
        yield bucket
    finally:
        # Restore the previous state
        _control_collection.reset(token)
        # If there was a parent, bubble up the results
        if parent_bucket is not None:
            parent_bucket.extend(bucket)


def _register_control(ctrl: "Control") -> None:
    bucket = _control_collection.get()
    if bucket is not None:
        bucket.append(ctrl)


@dataclass
class Control:
    ctrl: str
    sdk: str | None
    top: str
    name: str

    def __str__(self) -> str:
        return self.ctrl


def _create_control_curve(
    name: str,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    direction: Direction = "y",
    size: float = 1,
    dimensions: tuple[float, float, float] = (1, 1, 1),
    position_offset: tuple[float, float, float] = (0, 0, 0)
) -> str:
    curve_transform = create_curve(name, control_shape)
    bake: bool = False
    match direction:
        case "y":
            pass
        case "-y":
            cmds.rotate(180, 0, 0, curve_transform)
            bake = True
        case "x":
            cmds.rotate(0, 0, -90, curve_transform)
            bake = True
        case "-x":
            cmds.rotate(0, 0, 90, curve_transform)
            bake = True
        case "z":
            cmds.rotate(90, 0, 0, curve_transform)
            bake = True
        case "-z":
            cmds.rotate(-90, 0, 0, curve_transform)
            bake = True
        case _:
            raise RuntimeError(
                f"{direction} is not a valid direction. It should be x,y,z or -x,-y,-z."
            )
    if position_offset != (0,0,0):
        cmds.move(
            position_offset[0],
            position_offset[1],
            position_offset[2], 
            curve_transform)
        bake=True

    if (size != 1) or (dimensions != (1, 1, 1)):
        scaled_dimensions = (size * dimension for dimension in dimensions)
        cmds.scale(*scaled_dimensions, curve_transform, relative=False)  # type: ignore
        bake = True

    if bake:
        bake_shape(transform=curve_transform)
    return curve_transform


def create_control(
    name: str,
    parent: str | Control | None,
    transform: str | MMatrix | None = None,
    sdk_offset:bool = False,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    direction: Direction = "y",
    shape_position_offset: tuple[float, float, float] =(0,0,0),
    size: float = 1,
    dimensions: tuple[float, float, float] = (1, 1, 1),
    rotation_order: RotateOrder = RotateOrder.XYZ,
    limit_min_scale: bool = True,
) -> Control:
    transform_matrix: MMatrix | None
    if transform is not None:
        if isinstance(transform, str):
            transform_matrix = get_world_matrix(transform)
        elif isinstance(transform, MMatrix):
            transform_matrix = transform
        else:
            raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    else:
        transform_matrix = None
    parent_transform = parent.transform if isinstance(parent, Control) else parent

    top_transform = create_transform(
        name=f"{name}{TOP_SUFFIX}", parent=parent_transform, transform=transform_matrix
    )
 

    if sdk_offset:
        sdk_transform = create_transform(
        name=f"{name}{SDK_SUFFIX}", parent=top_transform, transform=transform_matrix
    )
        control_parent = sdk_transform
    else:
        sdk_transform = None
        control_parent = top_transform
    
    control_name = f"{name}{CONTROL_SUFFIX}"
    # We call a function to create an mGear compatible control here, since mGear is rather specific about what it needs.
    # Feel free to replace this if you ditch mGear.
    control_transform = build_control(
        control_name,
        control_parent,
        control_shape,
        direction,
        size,
        dimensions,
        rotation_order,
        shape_position_offset,
    )
    

    if limit_min_scale:  # Comfort feature: make it so it's not possible to have negative scale
        min_scale: float = 0.01
        cmds.transformLimits(
            control_transform,
            enableScaleX=(True, False),
            scaleX=(min_scale, 1),
            enableScaleY=(True, False),
            scaleY=(min_scale, 1),
            enableScaleZ=(True, False),
            scaleZ=(min_scale, 1),
        )

    control = Control(ctrl=control_transform, top=top_transform, sdk=sdk_transform, name=name)
    _register_control(control)
    return control

def build_control(
    name,
    parent,
    control_shape,
    direction,
    size,
    dimensions,
    rotation_order,
    position_offset
):


    # shape build (your system)
    shape_parent = _create_control_curve(
        name,
        control_shape,
        direction,
        size,
        dimensions,
        position_offset
    )

    cmds.setAttr(shape_parent + ".rotateOrder", int(rotation_order))
    
    cmds.parent(shape_parent, parent)

    for attr in ['rotateX', 'rotateY', 'rotateZ', 'translateX', 'translateY', 'translateZ']:
        cmds.setAttr(f'{shape_parent}.{attr}', 0)

    return shape_parent


