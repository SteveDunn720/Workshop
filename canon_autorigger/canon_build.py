from attr import dataclass
import maya.cmds as cmds

from Workshop.canon_autorigger.build_management.config_scene import configure_canon_scene
from Workshop.canon_autorigger.build_management.load_guides import load_guides
from Workshop.canon_autorigger import modules
from Workshop.tag.core import get_tags

@dataclass
class rig_config:
    cor_joints:bool = True





def build(rig_name:str, config:rig_config):

    #build_prep

    imported_nodes = load_guides(rig_type='canon', rig=rig_name)
    canon = configure_canon_scene(rig_name=rig_name)



    #root controls


    root = modules.Root(control_size=canon.scene_size, joint_parent=canon.joints, parent=canon.rig)
    root_info = root.root_build()



    #middle modules



    ##side modules

    for side in ["L", "R"]:

        leg = modules.Limb(part='leg', control_size=canon.scene_size, parent=canon.rig, joint_parent=canon.joints, side=side, guides= [f'upperleg_{side}_guide', f'knee_{side}_guide', f'foot_{side}_guide'],ik_end_control = True, fk_control_space=[root_info.root_control.ctrl], ik_control_space=[root_info.root_control.ctrl,], ikfk_blend=0, ik_length=True)
        leg_info = leg.limb_build()


    #face modules






    # check for and apply tags
    
    rig_nodes = cmds.listRelatives(canon.top, allDescendents=True, fullPath=False, shapes=False, type="transform")

    for node in rig_nodes:
        get_tags(node)

    #cmds.delete('guides')





    