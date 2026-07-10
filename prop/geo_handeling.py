import maya.cmds as cmds
from Workshop.tag.core import sets_tag


def prop_skinning(geo_root:str='geo'):


    joints = cmds.sets("bind_joints_set", query=True) or []
    joints = cmds.ls(joints, type="joint") #type:ignore

    children = cmds.listRelatives(geo_root, children=True, type="transform") or []


    for geo in children:
        history = cmds.listHistory(geo) or []
        if cmds.ls(history, type="skinCluster"): #type:ignore
            continue

        cmds.skinCluster(
            joints,                      #type:ignore
            geo,
            toSelectedBones=True,
            bindMethod=0,
            skinMethod=0,
            normalizeWeights=1,
        )


def geo_tags(geo_root:str='geo'):
    children = cmds.listRelatives(geo_root, children=True, type="transform") or []
    for geo in children:
        sets_tag(geo, ['unreal_set'])