#type:ignore
import maya.cmds as cmds


def create_control_helper_plane(
    image_path: str,
    name: str = "top_reference",
    width: float = 10.0,
    depth: float = 100.0,
) -> tuple[str, str]:
    """Create an image plane attached to the orthographic top camera."""

    transform, shape = cmds.imagePlane(
        fileName=image_path,
        name=name,
    )
    cmds.setAttr(f"{transform}.rotateX", 90)

    # Move it to the origin
    cmds.setAttr(f"{transform}.translateX", 0)
    cmds.setAttr(f"{transform}.translateY", 0)
    cmds.setAttr(f"{transform}.translateZ", 0)

    """cmds.setAttr(f"{image_plane_shape}.width", width)
    cmds.setAttr(f"{image_plane_shape}.depth", depth)"""

    return transform, shape
