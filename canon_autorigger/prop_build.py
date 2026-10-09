from dataclasses import dataclass
import maya.cmds as cmds

from Workshop.tag.core import get_tags

from .build_management.skin_geo import skin_meshes
from .build_management.load_guides import load_guides

from .prop_auto_resolve import (
    auto_build_prop,
    PropBuildResults,
)
from .build_management.config_scene import configure_canon_scene


@dataclass
class PropRigConfig:
    control_size: float = 1.0
    build_modules: bool = True
    skin: bool = False
    cleanup: bool = False


def build(
    rig_name: str,
    config: PropRigConfig | None = None,
) -> PropBuildResults | None:

    if config is None:
        config = PropRigConfig()

    # --------------------------------------------------
    # SCENE CONFIGURATION
    # --------------------------------------------------

    cmds.file(new=True, force=True)
    imported_nodes = load_guides(rig_type='prop', rig=rig_name)

    scene = configure_canon_scene(
        rig_name=rig_name,
        correctives=False,
    )

    cmds.refresh()

    # --------------------------------------------------
    # AUTO MODULE BUILD
    # --------------------------------------------------

    results = None

    if config.build_modules:

        results = auto_build_prop(
            root="root_M_guide",
            parent=scene.rig,
            control_size=scene.scene_size,
        )


    rig_nodes = cmds.listRelatives(scene.top, allDescendents=True, fullPath=False, shapes=False, type="transform")
    
    for node in rig_nodes:
        get_tags(node)

    #cmds.delete('guides')
    cmds.hide('guides')


    # skin geo start
    skin_meshes()








    return results