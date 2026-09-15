import maya.api.OpenMaya as om2
import maya.cmds as cmds

from Workshop.poly.meshes import get_mesh_shape


def set_face_colors(
    mesh: str,
    faces: list[int],
    colors: list[tuple[float, float, float]],
) -> None:
    """Set colors on polygon faces."""

    if len(faces) != len(colors):
        raise ValueError(
            "Faces and colors must have the same length."
        )

    selection = om2.MSelectionList()
    selection.add(mesh)

    dag = selection.getDagPath(0)
    fn_mesh = om2.MFnMesh(dag)

    maya_colors = [
        om2.MColor(color)
        for color in colors
    ]

    fn_mesh.setFaceColors(
        maya_colors,
        faces,
    )


def set_faces_color(
    mesh: str,
    faces: list[int],
    color: tuple[float, float, float],
) -> None:
    """Set the same color on multiple faces."""

    set_face_colors(
        mesh=mesh,
        faces=faces,
        colors=[
            color
            for _ in faces
        ],
    )


def set_color_display(
    mesh: str,
    enabled: bool,
) -> None:
    """Toggle vertex color display on a mesh."""

    shapes = cmds.listRelatives(
        mesh,
        shapes=True,
        noIntermediate=True,
    ) or []

    if not shapes:
        raise RuntimeError(
            f"No shape found for '{mesh}'."
        )

    shape = shapes[0]

    cmds.setAttr(
        f"{shape}.displayColors",
        enabled,
    )

    if enabled:
        cmds.setAttr(
            f"{shape}.displayColorChannel",
            "Diffuse",
            type="string",
        )

def set_color_display(
    mesh: str,
    enabled: bool,
) -> None:
    """Toggle vertex color display on a mesh."""

    shape = get_mesh_shape(
        mesh=mesh,
    )

    cmds.setAttr(
        f"{shape}.displayColors",
        enabled,
    )

    if enabled:
        cmds.setAttr(
            f"{shape}.displayColorChannel",
            "Diffuse",
            type="string",
        )