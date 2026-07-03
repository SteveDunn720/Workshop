import maya.cmds as cmds



def get_position_from_vertex(vert:str, world_space:bool=True):
    pos = cmds.pointPosition(vert, world=world_space)
    return pos