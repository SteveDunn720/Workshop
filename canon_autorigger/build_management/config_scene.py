from attr import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform
from Workshop.tag.core import lock_tag, obj_vis_tag

@dataclass
class scene_config:
    top:str
    geo:str
    joints:str
    rig:str
    scene_size:float
    guides:str
    hide:str
    

def configure_canon_scene(rig_name:str)->scene_config:
    nodes = ['guides', 'geo', f'{rig_name}_UBM']

    missing = [node for node in nodes if not cmds.objExists(node)]

    if missing:
        print(f"Missing: {missing}")

    root = create_transform(name='root')
    skel_container = create_transform(name='skel', parent=root)
    rig_container = create_transform(name='rig', parent=root)
    hide_container = create_transform(name='hide', parent=root)
    size = get_model_size(model='geo')

    cmds.parent('geo', root)

    for tform in [root, skel_container, rig_container, hide_container, 'geo']:
        lock_tag(object=tform, hide_tag=False)

    obj_vis_tag(skel_container, visibility='visibility_options_ctrl.skel_vis')
    obj_vis_tag(rig_container, visibility='visibility_options_ctrl.controls_vis')
    obj_vis_tag('geo', visibility='visibility_options_ctrl.geo_vis')


    config = scene_config(top=root, geo='geo', joints = skel_container, rig=rig_container, scene_size=size, guides='guides', hide=hide_container)
    return config


def get_model_size(model:str='body_lod0_mesh')->float:
    bbox = cmds.exactWorldBoundingBox(model)

    size_x = bbox[3] - bbox[0]
    size_z = bbox[5] - bbox[2]

    average = (size_x + size_z) / 3

    return average

        
