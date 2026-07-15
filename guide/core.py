from attr import dataclass
import maya.cmds as cmds
from maya.api.OpenMaya import MMatrix

from Workshop.joint import create_joint
from Workshop.transform.matrix import set_local_matrix
from Workshop.transform.utils import match_location

@dataclass 
class guide_info:
    name:str
    pos:tuple
    rot:tuple
    guide_type:str
    extra_channels:list


def create_guide_from_position(pos, guide_name, parent)->guide_info:
    guide = create_joint(name=guide_name, connect=False, parent=parent, suffix=False)

    if isinstance(pos, str):
        if not cmds.objExists(pos):
            print(f'{pos} does not exist')
            return None
        match_location(transform=guide, target_transform=pos)
    elif isinstance(pos, tuple):
        cmds.xform(guide, query=False, worldSpace=True, translation=pos)
    elif isinstance(pos, MMatrix):
        set_local_matrix(transform=guide, matrix=pos, use_joint_orient=False, )
    else:
        print(f'{pos} is incompatible')
        return None
    return_pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
    return_rot = cmds.xform(guide, query=True, rotation=True, worldSpace=True)
    
    info = guide_info(name=guide_name, pos=return_pos, rot=return_rot, guide_type='joint', extra_channels=[] ) #type:ignore
    return info

