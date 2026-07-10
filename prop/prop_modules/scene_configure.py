

from attr import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform

@dataclass
class scene_config:
    top:str
    geo:str
    skel:str
    rig:str
    scene_size:float
    

def configure_prop_scene()->scene_config:
    nodes = ['geo']

    missing = [node for node in nodes if not cmds.objExists(node)]

    if missing:
        print(f"Missing: {missing}")

    top = create_transform(name='root', parent=None,)

    skel = create_transform(name='skel', parent=top,)
    rig = create_transform(name='rig', parent=top,)
    cmds.parent('geo', top)

    size = get_model_size(model='geo')

    config = scene_config(top='rig', geo='geo', skel = skel, rig=rig, scene_size=size)
    return config


def get_model_size(model:str='body_lod0_mesh')->float:
    bbox = cmds.exactWorldBoundingBox(model)

    size_x = bbox[3] - bbox[0]
    size_z = bbox[5] - bbox[2]

    average = (size_x + size_z) / 3

    return average

        
