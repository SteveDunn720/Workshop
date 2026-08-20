from attr import dataclass
import maya.cmds as cmds

from Workshop.canon_autorigger.build_management.config_scene import configure_canon_scene
from Workshop.canon_autorigger.build_management.load_guides import load_guides
from Workshop.canon_autorigger import modules
from Workshop.tag.core import get_tags
from Workshop.canon_autorigger.canon_rig_config import generate_foot_guides, read_guides

@dataclass
class rig_config:
    cor_joints:bool = True



def build(rig_name:str, config:rig_config):

    #build_prep

    cmds.file(new=True, force=True)
    imported_nodes = load_guides(rig_type='canon', rig=rig_name)
    canon = configure_canon_scene(rig_name=rig_name)
    cmds.refresh()

    cmds.select(canon.geo, replace=True)
    cmds.viewFit()
    cmds.select(clear=True)

    guides = read_guides()



    #root controls


    root = modules.Root(control_size=canon.scene_size, joint_parent=canon.joints, parent=canon.rig, guides=[guides.root])
    root_info = root.root_build()



    #middle modules

    hip = modules.Hip(control_size=canon.scene_size, parent=canon.rig, joint_parent=root_info.joint, control_space=[root_info.offset_control.ctrl], guides=[guides.hip])
    hipinfo = hip.hip_build()

    spine = modules.Spine(control_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, guides=guides.spine, root_hook=[hipinfo.cog_control, hipinfo.hip_control], control_space=[hipinfo.cog_control.ctrl])
    spineinfo = spine.spine_build()

    neck = modules.Neck(control_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.neck, control_space=[spineinfo.chest_off.ctrl])
    neckinfo = neck.neck_build()
     



    ##side modules

    for side in ["L", "R"]:
    
        leg = modules.Limb(part='leg', control_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, side=side, guides=guides.leg[side],ik_end_control = False, fk_control_space=[hipinfo.hip_control.ctrl], ik_root_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl,], ik_pv_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ik_end_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ikfk_blend=0, ik_length=True)
        leg_info = leg.limb_build()

        footguide = generate_foot_guides(side=side, parent=None)
        foot = modules.Foot(part='feet', control_size=canon.scene_size, parent=canon.rig, side=side, joint_parent=leg_info.bind_joints[-1] ,  guides= guides.foot[side], fk_control_space=[leg_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=leg_info.end_ik_hook, feet_guides=footguide, fkik_switch_attr=leg_info.fk_ik_switch, leg_info=leg_info)
        foot_info = foot.foot_build()


        clav = modules.Clav(part='clav', side=side, control_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.clav[side], control_space=[spineinfo.chest_off.ctrl, spineinfo.switch_joints[-1]])
        clav_info = clav.clav_build()

        arm = modules.Limb(part='arm', control_size=canon.scene_size, parent=canon.rig, joint_parent=clav_info.joint, side=side, guides=guides.arm[side],ik_end_control = False, fk_control_space=[clav_info.control.ctrl], ik_root_control_space=[clav_info.control.ctrl, hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1],], ik_pv_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_end_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ikfk_blend=1, ik_length=True)
        arm_info = arm.limb_build()

        hand = modules.Hand(part='hand', control_size=canon.scene_size, joint_parent=arm_info.bind_joints[-1],  parent=canon.rig, side=side, guides=guides.arm[side][-1], fk_control_space=[arm_info.fk_controls[-1].ctrl], ik_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_hook=arm_info.end_ik_hook, fkik_switch_attr=arm_info.fk_ik_switch)
        hand_info = hand.hand_build()

        
        metacarpal = modules.Metacarpal(part='metacarpal', joint_parent=hand_info.joint , control_size=canon.scene_size, parent=canon.rig, side=side, guides=guides.metacarpal[side], control_space=[hand_info.switch],)
        metacarpal_info = metacarpal.metacarpal_build()

        for i, fingers in enumerate(['index', 'middle', 'ring', 'pinky', 'thumb']):
            if fingers == 'thumb':
                parent = hand_info.switch
                jnt_par = hand_info.joint
            else:
                parent = metacarpal_info.control[i].ctrl
                jnt_par = metacarpal_info.joint[i]

            finger = modules.Chain(part=fingers, control_size=canon.scene_size, joint_parent=jnt_par, parent=canon.rig, side=side, guides=guides.fingers[f'{fingers}_{side}'], control_space=parent)
            finger.chain_build()



        


    #face modules






    # check for and apply tags
    
    rig_nodes = cmds.listRelatives(canon.top, allDescendents=True, fullPath=False, shapes=False, type="transform")

    for node in rig_nodes:
        get_tags(node)

    #cmds.delete('guides')
    cmds.delete('foot_guides_temp')
    cmds.hide('guides')





    