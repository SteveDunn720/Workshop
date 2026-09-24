import maya.cmds as cmds
from Workshop.tag.core import sets_tag
from Workshop.skin.core import skin_geometry, transfer_skin_weights
from Workshop.skin.ng import apply_ng_skin_weights, init_layers_from_transforms
from .load_guides import RIG_BUILD_DIRECTORY, CANNON_DIRECTORY
from pathlib import Path


SKINNABLE_TYPES = {
    "mesh",
    "nurbsSurface",
    "nurbsCurve",
}

def remove_non_joint_influences(geometry: str):
    """Remove any non-joint influences from skinClusters on geometry."""

    history = cmds.listHistory(geometry) or []
    skin_clusters = cmds.ls(history, type="skinCluster") or []

    for skin_cluster in skin_clusters:
        influences = cmds.skinCluster(
            skin_cluster,
            query=True,
            influence=True,
        ) or []

        non_joint_influences = [
            influence
            for influence in influences
            if cmds.nodeType(influence) != "joint"
        ]

        for influence in non_joint_influences:
            print(
                f"Removing non-joint influence "
                f"'{influence}' from '{skin_cluster}'"
            )

            cmds.skinCluster(
                skin_cluster,
                edit=True,
                removeInfluence=influence,
            )

def is_skinnable(obj: str) -> bool:
    shapes = cmds.listRelatives(
        obj,
        shapes=True,
        noIntermediate=True,
        fullPath=True
    ) or []

    return any(
        cmds.nodeType(shape) in SKINNABLE_TYPES
        for shape in shapes
    )


def skin_meshes(geo_root:str='geo', skin_method:int=0, joint_set:str='bind_joints_set', force_single_cluster:bool =True):
    '''
    args:
    geo_root:group in maya that holds geo
    skin_method:0-Classic Linear, 1-Dual Qaut, 2-Weight Blended
    joint_set:selectionset name
    force_single: skins mesh if already skinned
    '''

    joints = cmds.sets(joint_set, query=True) or []
    joints = cmds.ls(joints, type="joint") #type:ignore

    children = cmds.listRelatives(geo_root, children=True, type="transform", allDescendents=True) or []


    for geo in children:
        if force_single_cluster:
            history = cmds.listHistory(geo) or []
            if cmds.ls(history, type="skinCluster"): #type:ignore
                continue
        skin = is_skinnable(obj=geo)
        if skin:
            skin_geometry(bind_joints=joints, geometry=geo, skin_method=skin_method,)
        else:
            pass
            #print(f'{geo} not skinnable')


def geo_tags(geo_root:str='geo'):
    children = cmds.listRelatives(geo_root, children=True, type="transform") or []
    for geo in children:
        sets_tag(geo, ['unreal_set'])


def apply_skins(character:str, geo_root:str='geo', primary_mesh='Cannon_UBM',):
    #init_layers_from_transforms([primary_mesh])
    #print('past')
    #apply body / primary mesh first
    apply_ng_skin_weights(
        weights_file= (
            Path(RIG_BUILD_DIRECTORY)
            / CANNON_DIRECTORY
            / character
            / "skin_data"
            / f"{primary_mesh}.json"
        ), 
        geometry=primary_mesh
    )


    children = cmds.listRelatives(geo_root, children=True, type="transform", allDescendents=True) or []
    for geo in children:
        try:
            try:
                skin = is_skinnable(obj=geo)
                if geo == primary_mesh or not skin:
                    pass
                else:
                    apply_ng_skin_weights(
                        weights_file= (
                            Path(RIG_BUILD_DIRECTORY)
                            / CANNON_DIRECTORY
                            / character
                            / "skin_data"
                            / f"{geo}.json"
                        ), 
                        geometry=geo
                    )
            except Exception:
                transfer_skin_weights(
                    source=primary_mesh, target=geo, 
                )
        except Exception:
            print(f'{Exception} skinning failed')



