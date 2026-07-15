from logging import warning

from attr import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform

@dataclass
class scene_config:
    top:str
    body_geo:str
    face_geo:str
    joints:str
    body_rig:str
    face_rig:str
    scene_size:float
    guides:str
    

def configure_metahuman_scene()->scene_config:
    nodes = ['rig', 'body_grp', 'head_grp', 'joints_grp', 'headRig_grp']

    missing = [node for node in nodes if not cmds.objExists(node)]

    if missing:
        print(f"Missing: {missing}")

    rig_container = create_transform(name='body_rig', parent='rig',)
    size = get_model_size(model='body_lod0_mesh')
    if not cmds.objExists('guides'):
        guides = create_transform(name='guides')

    config = scene_config(top='rig', body_geo='body_grp', face_geo='head_grp', joints = 'joints_gro', body_rig=rig_container, face_rig='headRig_grp', scene_size=size, guides='guides')
    return config


def get_model_size(model:str='body_lod0_mesh')->float:
    bbox = cmds.exactWorldBoundingBox(model)

    size_x = bbox[3] - bbox[0]
    size_z = bbox[5] - bbox[2]

    average = (size_x + size_z) / 3

    return average

        
