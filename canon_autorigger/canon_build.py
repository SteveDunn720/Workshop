from attr import dataclass
import maya.cmds as cmds

from Workshop.canon_autorigger.build_management.config_scene import configure_canon_scene
from Workshop.canon_autorigger.build_management.load_guides import load_guides
from Workshop.canon_autorigger.build_management.skin_geo import apply_skins, skin_meshes
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

    guides = read_guides(rig_name=rig_name)

    print(canon.scene_size)



    #root controls


    root = modules.Root(control_size=canon.scene_size, joint_parent=canon.joints, parent=canon.rig, guides=[guides.root])
    root_info = root.build()
    



    #middle modules

    hip = modules.Hip(control_size=canon.scene_size, parent=canon.rig, joint_parent=root_info.joint, control_space=[root_info.offset_control.ctrl], guides=[guides.hip])
    hipinfo = hip.build()

    spine = modules.Spine(control_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, guides=guides.spine, root_hook=[hipinfo.cog_control, hipinfo.hip_control], control_space=[hipinfo.cog_control.ctrl])
    spineinfo = spine.build()

    neck = modules.Neck(control_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.neck, control_space=[spineinfo.chest_off.ctrl])
    neckinfo = neck.build()

    head = modules.Head(control_size=canon.scene_size, parent=canon.rig, joint_parent=neckinfo.joint[-1], guides=guides.head, control_space=[neckinfo.control[-1].ctrl])
    headinfo = head.build()
     



    ##side modules

    for side in ["L", "R"]:
    
        leg = modules.Biped_Limb(part='leg', control_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, side=side, guides=guides.leg[side],ik_end_control = False, fk_control_space=[hipinfo.hip_control.ctrl], ik_root_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl,], ik_pv_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ik_end_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ikfk_blend=0, ik_length=True, fk_shape_twist=90)
        leg_info = leg.build()

        footguide = generate_foot_guides(side=side, parent=None)
        foot = modules.Foot(part='feet', control_size=canon.scene_size, parent=canon.rig, side=side, joint_parent=leg_info.bind_joints[-1] ,  guides= guides.foot[side], fk_control_space=[leg_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=leg_info.end_ik_hook, feet_guides=footguide, fkik_switch_attr=leg_info.fk_ik_switch, leg_info=leg_info)
        foot_info = foot.build()


        clav = modules.Clav(part='clav', side=side, control_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.clav[side], control_space=[spineinfo.chest_off.ctrl, spineinfo.switch_joints[-1]])
        clav_info = clav.build()

        arm = modules.Biped_Limb(part='arm', control_size=canon.scene_size, parent=canon.rig, joint_parent=clav_info.joint, side=side, guides=guides.arm[side],ik_end_control = False, fk_control_space=[clav_info.control.ctrl], ik_root_control_space=[clav_info.control.ctrl, hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1],], ik_pv_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_end_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ikfk_blend=1, ik_length=True)
        arm_info = arm.build()

        hand = modules.Hand(part='hand', control_size=canon.scene_size, joint_parent=arm_info.bind_joints[-1],  parent=canon.rig, side=side, guides=guides.arm[side][-1], fk_control_space=[arm_info.fk_controls[-1].ctrl], ik_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_hook=arm_info.end_ik_hook, fk_hook=arm_info.fk_hook , fkik_switch_attr=arm_info.fk_ik_switch)
        hand_info = hand.build()

        
        metacarpal = modules.Metacarpal(part='metacarpal', joint_parent=hand_info.joint , control_size=canon.scene_size, parent=canon.rig, side=side, guides=guides.metacarpal[side], control_space=[hand_info.switch],)
        metacarpal_info = metacarpal.build()

        for i, fingers in enumerate(['index', 'middle', 'ring', 'pinky', 'thumb']):
            if fingers == 'thumb':
                parent = hand_info.switch
                jnt_par = hand_info.joint
            else:
                parent = metacarpal_info.control[i].ctrl
                jnt_par = metacarpal_info.joint[i]

            finger = modules.Chain(part=fingers, control_size=canon.scene_size, joint_parent=jnt_par, parent=canon.rig, side=side, guides=guides.fingers[f'{fingers}_{side}'], control_space=parent)
            finger.build()



        if guides.full_joint_correctives:

            hip_cor = modules.Hip_Cor(control_size=canon.scene_size, joint_parent=hipinfo.hip_joint, parent=canon.correctives, side=side, guides=guides.hip_correctives[side], driver=leg_info.bind_joints[0])
            hip_cor_info = hip_cor.build()

            knee_cor = modules.Knee_Cor(control_size=canon.scene_size, joint_parent=leg_info.upper_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.knee_correctives[side], driver=leg_info.bind_joints[1])
            knee_cor_info = knee_cor.build()

            ankle_cor = modules.Ankle_Cor(control_size=canon.scene_size, joint_parent=leg_info.lower_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.ankle_correctives[side], driver=foot_info.bind_joints[0])
            ankle_cor_info = ankle_cor.build()

            elbow_cor = modules.Elbow_Cor(control_size=canon.scene_size, joint_parent=arm_info.upper_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.elbow_correctives[side], driver=arm_info.bind_joints[1])
            elbow_cor_info = elbow_cor.build()

            wrist_cor = modules.Wrist_Cor(control_size=canon.scene_size, joint_parent=arm_info.lower_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.wrist_correctives[side], driver=hand_info.joint)
            wrist_cor_info = wrist_cor.build()

            chest_cor = modules.Chest_Cor(control_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.correctives, side=side, guides=guides.chest_correctives[side], driver=arm_info.switch_joints[0], parent_space=spineinfo.chest_off.ctrl)
            chest_cor_info = chest_cor.build()


            """pec = modules.Ik_correctives(part="pec", control_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.rig, side=side, guides=guides.pec_correctives[side], end_ik_space=[arm_info.switch_joints[0]], root_ik_space=[spineinfo.chest_off.ctrl], divisions=1) #type:ignore
            pec.build()
            trap = modules.Ik_correctives(part="trap", control_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.rig, side=side, guides=guides.trap_correctives[side], end_ik_space=[arm_info.switch_joints[0]], root_ik_space=[spineinfo.chest_off.ctrl], divisions=1) #type:ignore
            trap.build()
            necktrap = modules.Ik_correctives(part="necktrap", control_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.rig, side=side, guides=guides.necktrap_correctives[side], end_ik_space=[arm_info.switch_joints[0]], root_ik_space=[spineinfo.chest_off.ctrl], divisions=1) #type:ignore
            necktrap.build()"""

    #face modules

    face = modules.Face(control_size=canon.scene_size, parent=canon.rig, joint_parent=headinfo.joint, guides=guides.face, control_space=[headinfo.control.ctrl])
    faceinfo = face.build()

    jaw = modules.Jaw(control_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=guides.jaw, control_space=[faceinfo.lower_control], larynx_follow_space=headinfo.control.ctrl, mid_face=faceinfo.submid_control)
    jawinfo = jaw.build()

    mouth = modules.Mouth(control_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=guides.mouth, jaw=jawinfo.jaw,  control_space=[faceinfo.lower_control], muppet=faceinfo.muppet_control, )
    mouthinfo = mouth.build()

    arch = modules.Arch(part='maxillary', control_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.teeth[0], guides.teeth[1]], control_space=[faceinfo.muppet_control], driver=faceinfo.muppet_control, divisions = 2)
    maxillaryinfo = arch.build()
    arch = modules.Arch(part='mandibular', control_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.teeth[2], guides.teeth[3]], control_space=[jawinfo.jaw], driver=jawinfo.jaw, divisions = 2)
    mandibularinfo = arch.build()
    tongue = modules.Tongue(control_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.tongue], control_space=[jawinfo.jaw])
    tongueinfo = tongue.build()

    nose = modules.Nose(control_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.mid_joint, guides=guides.nose,  control_space=[faceinfo.muppet_control], mouth=mouthinfo.master, jaw=jawinfo.jaw, head=headinfo.control, bridge_space=[faceinfo.upper_control])
    noseinfo = nose.build()

    for side in ["L", "R"]:
        nl_fold = modules.NL_Fold(control_size=canon.scene_size, side=side, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.nl[0]], control_space=[faceinfo.lower_control], upper_driver=noseinfo.control, lower_driver=mouthinfo.macro[f'upper_corner_{side}'], corner=mouthinfo.corner_controls[side] )
        nl_foldinfo = nl_fold.build()

        brow = modules.Brow(control_size=canon.scene_size, side=side, parent=canon.rig, joint_parent=faceinfo.top_joint, guides=[guides.brow[0]], control_space=[faceinfo.top_control], )
        browinfo = brow.build()

        cheek = modules.Cheek(control_size=canon.scene_size, side=side, parent=canon.rig, joint_parent=faceinfo.mid_joint, guides=guides.cheek[side], puff_space=[faceinfo.lower_control], cheekbone_space=[faceinfo.upper_control], driver=jawinfo.jaw, head_space=headinfo.control)
        cheekinfo = cheek.build()

        ear = modules.Ear(control_size=canon.scene_size, side=side, parent=canon.rig, joint_parent=faceinfo.mid_joint, guides=guides.ear, main_space=[faceinfo.muppet_control], driver=jawinfo.jaw, head_space=headinfo.control)
        earinfo = ear.build()
            
    
      






    # check for and apply tags
    
    rig_nodes = cmds.listRelatives(canon.top, allDescendents=True, fullPath=False, shapes=False, type="transform")

    for node in rig_nodes:
        get_tags(node)

    #cmds.delete('guides')
    cmds.delete('foot_guides_temp')
    cmds.hide('guides')


    # skin geo start
    skin_meshes()
    apply_skins(character=rig_name, primary_mesh=guides.primary_geo)





    