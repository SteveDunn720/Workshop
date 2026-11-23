from dataclasses import dataclass
import maya.cmds as cmds

from Workshop.config import RIG_BUILD_DIRECTORY, CANNON_DIRECTORY, CANNON_PROP_DIRECTORY
from .file_managment import import_guides


@dataclass
class import_info:
    all:list
    top:list



def load_guides(rig:str, rig_type:str = 'canon'):
    import_node_list = []
    import_guides(rig_type=rig_type, rig=rig, work=False)

    
    clean_scene()
    return import_node_list


def clean_scene():
    pass

       

def import_from_path(path_):

    print(path_)

    new_nodes = cmds.file(
        path_,
        i=True,
        namespace=":",
        mergeNamespacesOnClash=True,
        returnNewNodes=True,
        preserveReferences=True,
        ignoreVersion=True,
        prompt=False,
    )

    top_level = [
        node
        for node in new_nodes
        if cmds.objectType(node, isType="transform")
        and not cmds.listRelatives(node, parent=True)
    ]

    return import_info(all=new_nodes, top=top_level)