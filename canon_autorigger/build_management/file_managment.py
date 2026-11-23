

from pathlib import Path
import maya.cmds as cmds

from Workshop.io.maya import export_maya_file, import_maya_file
from Workshop.config import RIG_BUILD_DIRECTORY, CANNON_DIRECTORY, CANNON_PROP_DIRECTORY


def export_guides(rig:str, rig_type:str):
    model_file, guide_file, work_file = _resolve_path(rig=rig, rig_type=rig_type)


    top_level_nodes = cmds.ls(assemblies=True, type="transform")
    list_b = ["geo", "guides"]
    exclude = set(list_b)
    difference = [obj for obj in top_level_nodes  if obj not in exclude]


    export_maya_file(filepath=Path(model_file), binary=True, nodes=['geo'] )
    export_maya_file(filepath=Path(guide_file), binary=True, nodes=['guides'] )
    if difference:
        export_maya_file(filepath=Path(work_file), binary=True, nodes=difference)

def import_guides(rig: str, rig_type: str, work:bool = True):
    model_file, guide_file, work_file = _resolve_path(
        rig=rig,
        rig_type=rig_type,
    )

    import_maya_file(filepath=Path(model_file))
    import_maya_file(filepath=Path(guide_file))

    work_path = Path(f"{work_file}")

    if work_path.exists():
        result = cmds.confirmDialog(
            title="Import Work File",
            message=(
                f"A work file was found for '{rig}'.\n\n"
                "Would you like to import it?"
            ),
            button=["Import", "Skip"],
            defaultButton="Import",
            cancelButton="Skip",
            dismissString="Skip",
            icon="question",
        )

        if result == "Import":
            import_maya_file(filepath=work_path)



def _resolve_path(rig:str, rig_type:str):
    if rig_type == 'prop':
        sub_direct = CANNON_PROP_DIRECTORY
    elif rig_type == 'Characters':
        sub_direct = CANNON_DIRECTORY
    model_file = rf'{RIG_BUILD_DIRECTORY}/{sub_direct}/{rig}/{rig}_model.mb'
    guide_file = rf'{RIG_BUILD_DIRECTORY}/{sub_direct}/{rig}/{rig}_guides.mb'
    work_file = rf'{RIG_BUILD_DIRECTORY}/{sub_direct}/{rig}/{rig}_work.mb'

    return [model_file, guide_file, work_file]