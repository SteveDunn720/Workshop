from attr import dataclass
import maya.cmds as cmds

from Workshop.canon_autorigger.build_management.config_scene import configure_canon_scene
from Workshop.canon_autorigger.build_management.load_guides import load_guides
from Workshop.canon_autorigger import modules
from Workshop.tag.core import get_tags
from Workshop.canon_autorigger.canon_rig_config import generate_foot_guides

@dataclass
class rig_config:
    cor_joints:bool = True





def build(rig_name:str, config:rig_config):

    #build_prep

    cmds.file(new=True, force=True)
    imported_nodes = load_guides(rig_type='canon', rig=rig_name)
    canon = configure_canon_scene(rig_name=rig_name)



    #root controls


    root = modules.Root(control_size=canon.scene_size, joint_parent=canon.joints, parent=canon.rig)
    root_info = root.root_build()



    #middle modules

    hip = modules.Hip(control_size=canon.scene_size, parent=canon.rig, joint_parent=root_info.joint, control_space=[root_info.offset_control.ctrl], guides=['cog_M_guide'])
    hipinfo = hip.hip_build()



    ##side modules

    for side in ["L", "R"]:

        leg = modules.Limb(part='leg', control_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, side=side, guides= [f'upperleg_{side}_guide', f'knee_{side}_guide', f'foot_{side}_guide'],ik_end_control = False, fk_control_space=[hipinfo.hip_control.ctrl], ik_root_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl,], ik_pv_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ik_end_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ikfk_blend=0, ik_length=True)
        leg_info = leg.limb_build()

        footguide = generate_foot_guides(side=side, parent=None)
        foot = modules.Foot(part='feet', control_size=canon.scene_size, parent=canon.rig, side=side, joint_parent=leg_info.bind_joints[-1] ,  guides= [f'foot_{side}_guide', f'toe_ball_{side}_guide'], fk_control_space=[leg_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=leg_info.end_ik_hook, feet_guides=footguide, fkik_switch_attr=leg_info.fk_ik_switch, leg_info=leg_info)
        foot_info = foot.foot_build()
        


    #face modules






    # check for and apply tags
    
    rig_nodes = cmds.listRelatives(canon.top, allDescendents=True, fullPath=False, shapes=False, type="transform")

    for node in rig_nodes:
        get_tags(node)

    #cmds.delete('guides')





    