import maya.cmds as cmds

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance

    Signal = QtCore.Signal
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance



PRIMARY_UV_SET = 'UV_set_01'

def get_uv_sets(mesh:str)-> list[str]:
    """
    Used for getting all uv sets on a mesh 
    Args:
        mesh: mesh
    Returns:
        list of set names
    """

    uv_sets = cmds.polyUVSet(
        mesh,
        query=True,
        allUVSets=True,
    )

    return uv_sets #type:ignore

def get_current_uv_set(mesh:str)->str | None:
    """
    Used for getting current uv sets on a mesh 
    Args:
        mesh: mesh
    """
    uv_set = cmds.polyUVSet(
        mesh,
        query=True,
        currentUVSet=True,
    )[0] #type:ignore

    return uv_set 

def validate_uv_set(
    mesh: str,
    uv_set: str,
    create: bool = False,
) -> str:
    """
    Validate that a UV set exists on a mesh.

    Args:
        mesh: Mesh to check.
        uv_set: UV set name.
        create: If True, create the UV set if it does not exist.

    Returns:
        The validated UV set name.

    Raises:
        RuntimeError: If the UV set does not exist and create is False.
    """

    uv_sets = get_uv_sets(mesh=mesh)

    if uv_set in uv_sets:
        return uv_set

    if create:
        create_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        return uv_set

    raise RuntimeError(
        f"UV set '{uv_set}' does not exist on '{mesh}'."
    )

def create_uv_set(
    mesh: str,
    uv_set: str,
    initialize: bool = True,
) -> None:
    """
    Create a new UV set on a mesh.

    Args:
        mesh: Mesh to create the UV set on.
        uv_set: Name of the new UV set.
        initialize: If True, initialize the UV set with a camera projection.

    Raises:
        RuntimeError: If a UV set with the given name already exists.
    """

    if uv_set in get_uv_sets(mesh=mesh):
        raise RuntimeError(
            f"UV set '{uv_set}' already exists on '{mesh}'."
        )

    current_uv_set = get_current_uv_set(mesh=mesh)

    cmds.polyUVSet(
        mesh,
        create=True,
        uvSet=uv_set,
    )

    if not initialize:
        return

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        camera_project(mesh=mesh, uv_set=uv_set)

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )

def set_current_uv_set(mesh:str, uv_set:str):
    """
    Used for setting current uv sets on a mesh 
    Args:
        mesh: mesh
        set: set
    """
    cmds.polyUVSet(
        mesh,
        currentUVSet=True,
        uvSet=uv_set,
    )

def rename_uv_set(mesh:str, uv_set:str, new_name:str):
    """
    Used for renaming uv sets on a mesh 
    Args:
        mesh: mesh
        uv_set: suv_et
    """
    if uv_set == new_name:
        return
    else:
        uv_sets = get_uv_sets(mesh=mesh)
        if new_name in uv_sets:
            cmds.polyUVSet(
                mesh,
                rename=True,
                uvSet=new_name,
                newUVSet=f'{new_name}_temp',
            )
        cmds.polyUVSet(
            mesh,
            rename=True,
            uvSet=uv_set,
            newUVSet=new_name,
        )

def delete_uv_set(mesh:str, uv_set:str):
    """
    Used for deleting uv sets on a mesh 
    Args:
        mesh: mesh
        uv_set: uv_set
    """
    cmds.polyUVSet(
        mesh,
        delete=True,
        uvSet=uv_set,
    )

def clean_uv_sets(mesh:str, primary_set:str=PRIMARY_UV_SET, ignore_sets: list[str]  = []):
    """
    Used for cleaning up UV sets.

    Args:
        mesh: Mesh to clean.
        primary_set: Name the surviving UV set should use.
        ignore_sets: UV sets that should be left untouched.
    """

    uv_sets = [
        uv_set
        for uv_set in get_uv_sets(mesh=mesh)
        if uv_set not in ignore_sets #type:ignore
    ]

    if len(uv_sets) == 1:
        rename_uv_set(mesh=mesh, uv_set=uv_sets[0], new_name=primary_set)
    elif len(uv_sets) == 0:
        create_uv_set(mesh=mesh, uv_set=primary_set)
    else:
        chosen_set = choose_uv_set(uv_sets)

        if chosen_set is None:
            return

        print(f"Keeping UV set: {chosen_set}")

        rename_uv_set(mesh=mesh, uv_set=chosen_set, new_name=primary_set)
        make_uv_set_first(mesh=mesh, uv_set=primary_set)

        updatedsets = [
            uv_set
            for uv_set in get_uv_sets(mesh=mesh)
            if uv_set not in ignore_sets #type:ignore
        ]

        for uv_set in updatedsets:
            if uv_set == primary_set:
                pass
            else:
                delete_uv_set(mesh=mesh, uv_set=uv_set)

def choose_uv_set(uv_sets: list[str]) -> str | None:
    """
    Ask the user which UV set should be kept.

    Returns:
        Selected UV set, or None if cancelled.
    """

    item, accepted = QtWidgets.QInputDialog.getItem(
        None,
        "Choose UV Set",
        "UV set to keep:",
        uv_sets,
        0,
        False,
    )

    if not accepted:
        return None

    return item

def make_uv_set_first(mesh: str, uv_set: str) -> None:
    uv_sets = cmds.polyUVSet(
        mesh,
        query=True,
        allUVSets=True,
    ) or []

    if uv_set not in uv_sets:
        raise RuntimeError(f"UV set not found: {set}")

    first_set = uv_sets[0]

    if uv_set == first_set:
        return

    cmds.polyUVSet(
        mesh,
        reorder=True,
        uvSet=uv_set,
        newUVSet=first_set,
    )

def camera_project(
    mesh: str,
    uv_set: str,
) -> None:
    """
    Create UVs for every face on a mesh using a camera projection.

    Args:
        mesh: Mesh to project.
        uv_set: Existing UV set to project into.
    """

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    current_uv_set = get_current_uv_set(mesh=mesh)

    face_count = cmds.polyEvaluate(
        mesh,
        face=True,
    )

    if not face_count:
        raise RuntimeError(
            f"Mesh '{mesh}' has no polygon faces."
        )

    faces = f"{mesh}.f[0:{face_count - 1}]"

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        cmds.polyProjection(
            faces,
            type="planar",
            mapDirection="camera",
            constructionHistory=False,
        )

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )