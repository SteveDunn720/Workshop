from dataclasses import dataclass

from Workshop.guide.core import GuideInfo, read_guide, SplineGuideInfo

import maya.cmds as cmds

from Workshop.canon_autorigger.build_management.config_scene import configure_canon_scene
from Workshop.canon_autorigger.build_management.load_guides import load_guides
from Workshop.canon_autorigger.build_management.skin_geo import apply_skins, skin_meshes
from Workshop.canon_autorigger import modules
from Workshop.tag.core import get_tags
from Workshop.canon_autorigger.modules.foot.roll_guides import generate_foot_guides


@dataclass
class cannon_guide_config:
    root:GuideInfo
    spine:SplineGuideInfo
    hip:GuideInfo
    chest:GuideInfo
    neck:SplineGuideInfo
    head:GuideInfo
    leg:dict[str, list[GuideInfo]]
    arm:dict[str, list[GuideInfo]]
    clav:dict[str, list[GuideInfo]]
    fingers:dict[str, list[GuideInfo]]
    foot:dict[str, list[GuideInfo]]
    metacarpal:dict[str, list[GuideInfo]]
    metatarsals:dict[str, list[GuideInfo]]
    toes:dict[str, list[GuideInfo]]

    #hip_correctives:dict[str,list[GuideInfo]] | None
    #knee_correctives:dict[str,list[GuideInfo]] | None
    #ankle_correctives:dict[str,list[GuideInfo]] | None
    #elbow_correctives:dict[str,list[GuideInfo]] | None
    #wrist_correctives:dict[str,list[GuideInfo]] | None
    #chest_correctives:dict | None

    #full_joint_correctives:bool

    face:list[GuideInfo]
    jaw:list[GuideInfo]
    mouth:dict[str,GuideInfo]

    teeth:list[GuideInfo]
    tongue:GuideInfo

    brow:list[GuideInfo]
    cheek:dict[str, list[GuideInfo]]

    eye:dict[str,dict[str,GuideInfo]]

    primary_geo:str



def read_guides(rig_name:str='Canon')->cannon_guide_config:
    #read root
    root = read_guide('root_M_guide')
    # Spine
    chest = read_guide('chest_root_M_guide')
    cog = read_guide('cog_M_guide')
    chest_curve = read_guide('chest_M_guide')
    chest_tan = read_guide('chest_tan_M_guide')
    hip_curve = read_guide('hip_M_guide')
    hip_tan = read_guide('hip_tan_M_guide')
    spine_curve = read_guide('spine_curve_M_guide')
    spine = SplineGuideInfo(curve=spine_curve, lower=hip_curve, lower_tan=hip_tan, upper=chest_curve, upper_tan=chest_tan)
    # neck
    neck_upper = read_guide('upper_neck_M_guide')
    neck_upper_tan = read_guide('upper_neck_tan_M_guide')
    neck_lower = read_guide('lower_neck_M_guide')
    neck_lower_tan = read_guide('lower_neck_tan_M_guide')
    neck_curve = read_guide('neck_M_guide')
    neck = SplineGuideInfo(curve=neck_curve, lower=neck_lower, lower_tan=neck_lower_tan, upper=neck_upper, upper_tan=neck_upper_tan)
    # head
    head = read_guide('head_root_M_guide')
    # mirrored body guides
    fingers = {}
    leg = {}
    foot = {}
    arm = {}
    clav = {}
    metacarpal = {}
    pec_cor = {}
    trap_cor = {}
    necktrap_cor = {}

    mouth = {}
    nose = {}
    cheek = {}
    ear = {}
    eye = {}
    
    hip_correctives = {}
    knee_correctives = {}
    ankle_correctives = {}
    elbow_correctives = {}
    wrist_correctives = {}
    chest_correctives = {}
    toes = {}
    metatarsals = {}
    

    for side in ['L', "R"]: #'R'
        leg[side] = [read_guide(f'upperleg_{side}_guide'), read_guide(f'knee_{side}_guide'), read_guide(f'huck_{side}_guide'), read_guide(f'foot_{side}_guide')]
        arm[side] = [read_guide(f'shoulder_{side}_guide'), read_guide(f'elbow_{side}_guide'), read_guide(f'hand_{side}_guide')]
        foot[side] = [read_guide(f'foot_{side}_guide'), read_guide(f'toe_ball_{side}_guide'), read_guide(f'toe_ee_{side}_guide')]
        foot[f'{side}_piv'] = [read_guide(f'heel_{side}_guide'), read_guide(f'toetip_ground_{side}_guide') ]
        clav[side] = read_guide(f'clav_{side}_guide')
        metacarpal[side] = [read_guide(f'finger_index_{side}_00_guide'), read_guide(f'finger_middle_{side}_00_guide'),]
        metatarsals[side] = [read_guide(f'toe_index_{side}_00_guide'), read_guide(f'toe_middle_{side}_00_guide'),]

        #fingers = finger_Index_L_01_guide
        for fing in ['thumb', 'index', 'middle', ]:
            joint_list = []
            for i in [ '01', '02', '03', '04']:
                guide = read_guide(f'finger_{fing}_{side}_{i}_guide')
                joint_list.append(guide)
            fingers[f'{fing}_{side}'] = joint_list

        for fing in ['thumb', 'index', 'middle',]:
            joint_list = []
            for i in [ '01', '02', '03', '04']:
                guide = read_guide(f'toe_{fing}_{side}_{i}_guide')
                joint_list.append(guide)
            toes[f'{fing}_{side}'] = joint_list

        #pec_cor[side] = [read_guide(f'pec_insert_{side}_guide'), read_guide(f'pec_01_{side}_guide'), read_guide(f'pec_02_{side}_guide')]
        #trap_cor[side] = [read_guide(f'trap_insert_{side}_guide'), read_guide(f'trap_01_{side}_guide'), read_guide(f'trap_02_{side}_guide')]
        #necktrap_cor[side] = [read_guide(f'necktrap_insert_{side}_guide'), read_guide(f'necktrap_01_{side}_guide')]

        mouth[f'{side}_mouth'] = read_guide(f'lip_{side}_guide')
        mouth[f'{side}_path'] = read_guide(f'mouth_path_{side}_guide')
        #cheek[f'{side}'] = [read_guide(f'cheek_puff_{side}_guide'), read_guide(f'cheek_bone_{side}_guide')]
        eye[side] = {
                    "center": read_guide(f"eye_center_{side}_guide"),
                    "aim": read_guide(f"look_{side}_guide"),
                    "upblink": read_guide(f"eyelid_upblink_{side}_guide"),
                    "upper": read_guide(f"eyelid_upper_{side}_guide"),
                    "blink": read_guide(f"eyelid_blink_{side}_guide"),
                    "lower": read_guide(f"eyelid_lower_{side}_guide"),
                    "lowblink": read_guide(f"eyelid_lowblink_{side}_guide"),
                    "socket_upper": read_guide(f"socket_upper_{side}_guide"),
                    "socket_lower": read_guide(f"socket_lower_{side}_guide"),
                    "eye_diam": read_guide(f"eyeball_{side}_guide"),
                    "iris_diam": read_guide(f"iris_{side}_guide"),
                    "pupil_diam": read_guide(f"pupil_{side}_guide"),
                }
        eye[f'{side}_lower'] = {
                    "center": read_guide(f"eye_center_{side}_lower_guide"),
                    "aim": read_guide(f"look_{side}_lower_guide"),
                    "upblink": read_guide(f"eyelid_upblink_{side}_lower_guide"),
                    "upper": read_guide(f"eyelid_upper_{side}_lower_guide"),
                    "blink": read_guide(f"eyelid_blink_{side}_lower_guide"),
                    "lower": read_guide(f"eyelid_lower_{side}_lower_guide"),
                    "lowblink": read_guide(f"eyelid_lowblink_{side}_lower_guide"),
                    "socket_upper": read_guide(f"socket_upper_{side}_lower_guide"),
                    "socket_lower": read_guide(f"socket_lower_{side}_lower_guide"),
                    "eye_diam": read_guide(f"eyeball_{side}_lower_guide"),
                    "iris_diam": read_guide(f"iris_{side}_lower_guide"),
                    "pupil_diam": read_guide(f"pupil_{side}_lower_guide"),
                }
        
        
        """hip_correctives[side] = [read_guide(f'psoasup_{side}_guide'), read_guide(f'psoasdown_{side}_guide'), read_guide(f'glutelow_{side}_guide'), read_guide(f'glutemid_{side}_guide'), read_guide(f'gluteup_{side}_guide'), read_guide(f'trochanter_{side}_guide')]
        knee_correctives[side] = [read_guide(f'kneecap_{side}_guide'), read_guide(f'hamstring_{side}_guide'), read_guide(f'calf_{side}_guide'),]
        ankle_correctives[side] = [read_guide(f'tibialis_{side}_guide'), read_guide(f'achilles_{side}_guide'), read_guide(f'medialmalleolus_{side}_guide'), read_guide(f'lateralmalleolus_{side}_guide'),]
        elbow_correctives[side] = [read_guide(f'elbowin_{side}_guide'), read_guide(f'lowerbicep_{side}_guide'), read_guide(f'lowertricep_{side}_guide'), read_guide(f'pronator_{side}_guide')]
        wrist_correctives[side] = [read_guide(f'wristin_{side}_guide'), read_guide(f'wristout_{side}_guide'), read_guide(f'wristup_{side}_guide'), read_guide(f'wristdown_{side}_guide'), ]
        chest_correctives[side] = [pec_cor[side], trap_cor[side], necktrap_cor[side]]
        chest_correctives[f'{side}_bicep'] = read_guide(f'bicep_{side}_guide')"""
    #face_guides

    face = [read_guide('upper_head_M_guide'), read_guide('lower_head_M_guide'), read_guide('mid_head_M_guide'), read_guide('top_head_M_guide'), read_guide('jaw_M_guide')]
    jaw = [read_guide('jaw_M_guide'), read_guide('jaw_ee_M_guide'), read_guide('larynx_M_guide')]

    #teeth = [read_guide('teeth_upper_L_guide'),read_guide('teeth_upper_R_guide'), read_guide('teeth_lower_L_guide'), read_guide('teeth_lower_R_guide') ]
    tongue = read_guide('tongue_M_guide')

    brow = [read_guide('brow_L_guide'), ]#read_guide('brow_R_guide')]

    #geo temp logic, need to decide later how this will work
    primary_mesh = 'polySurface1'
    #tag geo

    all_guides = cannon_guide_config(
        root=root, 
        hip=cog, 
        chest=chest, 
        spine=spine, 
        neck=neck, 
        head=head, 
        leg=leg, 
        arm=arm, 
        fingers=fingers, 
        foot=foot, 
        clav=clav, 
        metacarpal=metacarpal, 
        metatarsals=metatarsals,
        toes=toes,

        #hip_correctives = hip_correctives,
        #knee_correctives = knee_correctives,
        #ankle_correctives = ankle_correctives,
        #elbow_correctives = elbow_correctives,
        #wrist_correctives = wrist_correctives,
        #chest_correctives = chest_correctives,

        #full_joint_correctives=True,

        face=face,
        jaw=jaw,
        mouth=mouth,
        teeth=None,#teeth,
        tongue=tongue,
        brow=brow,
        cheek=None,#cheek,
        eye=eye,

        primary_geo=primary_mesh,
    )
    return all_guides
    



@dataclass
class rig_config:
    cor_joints:bool = True
    face:bool = True



def build(rig_name:str, config:rig_config):

    #build_prep

    cmds.file(new=True, force=True)
    imported_nodes = load_guides(rig_type='Characters', rig=rig_name)
    canon = configure_canon_scene(rig_name=rig_name)
    cmds.refresh()

    cmds.select(canon.geo, replace=True)
    cmds.viewFit()
    cmds.select(clear=True)

    guides = read_guides(rig_name=rig_name)

    print(canon.scene_size)



    #root controls

    root = modules.Root(rig_size=canon.scene_size, joint_parent=canon.joints, parent=canon.rig, guides=[guides.root])
    root_info = root.build()
    #middle modules

    hip = modules.Hip(rig_size=canon.scene_size, parent=canon.rig, joint_parent=root_info.joint, control_space=[root_info.offset_control.ctrl], guides=[guides.hip])
    hipinfo = hip.build()

    spine = modules.Spine(rig_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, guides=guides.spine, root_hook=[hipinfo.cog_control, hipinfo.hip_control], control_space=[hipinfo.cog_control.ctrl])
    spineinfo = spine.build()

    neck = modules.Neck(rig_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.neck, control_space=[spineinfo.chest_off.ctrl], divisions=11)
    neckinfo = neck.build()

    head = modules.Head(rig_size=canon.scene_size, parent=canon.rig, joint_parent=neckinfo.joint[-1], guides=guides.head, control_space=[neckinfo.control[-1].ctrl])
    headinfo = head.build()
     



    ##side modules

    for side in ["L", "R"]:
    
        leg = modules.Quadruped_Leg(part='leg', rig_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, side=side, guides=guides.leg[side],ik_end_control = False, fk_control_space=[hipinfo.hip_control.ctrl], ik_root_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl,], ik_pv_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ik_end_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ikfk_blend=0, ik_length=True, fk_shape_twist=90)
        leg_info = leg.build()

        footguide = generate_foot_guides(side=side, parent=None)
        foot = modules.Foot(part='feet', rig_size=canon.scene_size, parent=canon.rig, side=side, joint_parent=leg_info.bind_joints[-1] ,  guides= guides.foot[side], fk_control_space=[leg_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=leg_info.end_ik_hook, feet_guides=footguide, fkik_switch_attr=leg_info.fk_ik_switch, leg_info=leg_info, piv_guides=guides.foot[f'{side}_piv'])
        foot_info = foot.build()


        clav = modules.Clav(part='clav', side=side, rig_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.clav[side], control_space=[spineinfo.chest_off.ctrl, spineinfo.switch_joints[-1]])
        clav_info = clav.build()

        arm = modules.Biped_Limb(part='arm', rig_size=canon.scene_size, parent=canon.rig, joint_parent=clav_info.joint, side=side, guides=guides.arm[side],ik_end_control = False, fk_control_space=[clav_info.control.ctrl], ik_root_control_space=[clav_info.control.ctrl, hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1],], ik_pv_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_end_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ikfk_blend=1, ik_length=True)
        arm_info = arm.build()

        hand = modules.Hand(part='hand', rig_size=canon.scene_size, joint_parent=arm_info.bind_joints[-1],  parent=canon.rig, side=side, guides=guides.arm[side][-1], fk_control_space=[arm_info.fk_controls[-1].ctrl], ik_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_hook=arm_info.end_ik_hook, fk_hook=arm_info.fk_hook , fkik_switch_attr=arm_info.fk_ik_switch, arm_info=arm_info)
        hand_info = hand.build()

        metacarpal = modules.Metacarpal(part='metacarpal', joint_parent=hand_info.joint , rig_size=canon.scene_size, parent=canon.rig, side=side, guides=guides.metacarpal[side], control_space=[hand_info.switch],)
        metacarpal_info = metacarpal.build()

        for i, fingers in enumerate(['index', 'middle', 'thumb']):
            if fingers == 'thumb':
                parent = hand_info.switch
                jnt_par = hand_info.joint
            else:
                parent = metacarpal_info.control[i].ctrl
                jnt_par = metacarpal_info.joint[i]

            finger = modules.Chain(part=f'finger{fingers}', rig_size=canon.scene_size, joint_parent=jnt_par, parent=canon.rig, side=side, guides=guides.fingers[f'{fingers}_{side}'], control_space=[parent])
            finger.build()

        for i, fingers in enumerate(['index', 'middle', 'thumb']):
            if fingers == 'thumb':
                parent = foot_info.swtich_joints[0]
                jnt_par = foot_info.bind_joints[0]
            else:
                parent = foot_info.swtich_joints[1]
                jnt_par = foot_info.bind_joints[1]
   

            finger = modules.Chain(part=f'toe{fingers}', rig_size=canon.scene_size, joint_parent=jnt_par, parent=canon.rig, side=side, guides=guides.toes[f'{fingers}_{side}'], control_space=[parent])
            finger.build()



        """if guides.full_joint_correctives:

            hip_cor = modules.Hip_Cor(rig_size=canon.scene_size, joint_parent=hipinfo.hip_joint, parent=canon.correctives, side=side, guides=guides.hip_correctives[side], driver=leg_info.bind_joints[0])
            hip_cor_info = hip_cor.build()

            knee_cor = modules.Knee_Cor(rig_size=canon.scene_size, joint_parent=leg_info.upper_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.knee_correctives[side], driver=leg_info.bind_joints[1])
            knee_cor_info = knee_cor.build()

            ankle_cor = modules.Ankle_Cor(rig_size=canon.scene_size, joint_parent=leg_info.lower_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.ankle_correctives[side], driver=foot_info.bind_joints[0])
            ankle_cor_info = ankle_cor.build()

            elbow_cor = modules.Elbow_Cor(rig_size=canon.scene_size, joint_parent=arm_info.upper_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.elbow_correctives[side], driver=arm_info.bind_joints[1])
            elbow_cor_info = elbow_cor.build()

            wrist_cor = modules.Wrist_Cor(rig_size=canon.scene_size, joint_parent=arm_info.lower_sub_joints[-1], parent=canon.correctives, side=side, guides=guides.wrist_correctives[side], driver=hand_info.joint)
            wrist_cor_info = wrist_cor.build()

            chest_cor = modules.Chest_Cor(rig_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.correctives, side=side, guides=guides.chest_correctives[side], driver=arm_info.upper_sub_joints[0], parent_space=spineinfo.chest_off.ctrl, clav_driver=clav_info.joint, blend=guides.chest_correctives[f'{side}_bicep'], blend_parent=clav_info.joint, blend_driver=arm_info.bind_joints[0],)
            chest_cor_info = chest_cor.build()


            pec = modules.Ik_correctives(part="pec", rig_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.rig, side=side, guides=guides.pec_correctives[side], end_ik_space=[arm_info.switch_joints[0]], root_ik_space=[spineinfo.chest_off.ctrl], divisions=1) #type:ignore
            pec.build()
            trap = modules.Ik_correctives(part="trap", rig_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.rig, side=side, guides=guides.trap_correctives[side], end_ik_space=[arm_info.switch_joints[0]], root_ik_space=[spineinfo.chest_off.ctrl], divisions=1) #type:ignore
            trap.build()
            necktrap = modules.Ik_correctives(part="necktrap", rig_size=canon.scene_size, joint_parent=spineinfo.bind_joints[-1], parent=canon.rig, side=side, guides=guides.necktrap_correctives[side], end_ik_space=[arm_info.switch_joints[0]], root_ik_space=[spineinfo.chest_off.ctrl], divisions=1) #type:ignore
            necktrap.build()"""

    #face modules
    if config.face:
        face = modules.Face(rig_size=canon.scene_size, parent=canon.rig, joint_parent=headinfo.joint, guides=guides.face, control_space=[headinfo.control.ctrl])
        faceinfo = face.build()

        jaw = modules.Jaw(rig_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=guides.jaw, control_space=[faceinfo.lower_control], larynx_follow_space=headinfo.control.ctrl, mid_face=faceinfo.submid_control)
        jawinfo = jaw.build()

        #mouth = modules.Mouth(rig_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=guides.mouth, jaw=jawinfo.jaw,  control_space=[faceinfo.lower_control], muppet=faceinfo.muppet_control, )
        #mouthinfo = mouth.build()

        #arch = modules.Arch(part='maxillary', rig_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.teeth[0], guides.teeth[1]], control_space=[faceinfo.muppet_control], driver=faceinfo.muppet_control, divisions = 2)
        #maxillaryinfo = arch.build()
        #arch = modules.Arch(part='mandibular', rig_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.teeth[2], guides.teeth[3]], control_space=[jawinfo.jaw], driver=jawinfo.jaw, divisions = 2)
        #mandibularinfo = arch.build()
        tongue = modules.Tongue(rig_size=canon.scene_size, parent=canon.rig, joint_parent=faceinfo.lower_joint, guides=[guides.tongue], control_space=[jawinfo.jaw])
        tongueinfo = tongue.build()

        for side in ["L", "R"]:
            brow = modules.Brow(rig_size=canon.scene_size, side=side, parent=canon.rig, joint_parent=faceinfo.top_joint, guides=[guides.brow[0]], control_space=[faceinfo.top_control], )
            browinfo = brow.build()

            #cheek = modules.Cheek(rig_size=canon.scene_size, side=side, parent=canon.rig, joint_parent=faceinfo.mid_joint, guides=guides.cheek[side], puff_space=[faceinfo.lower_control], cheekbone_space=[faceinfo.upper_control], driver=jawinfo.jaw, head_space=headinfo.control)
            #cheekinfo = cheek.build()

            look = modules.Look(side=side ,rig_size=canon.scene_size, parent=canon.rig, parent_jnt=faceinfo.mid_joint, guides=[guides.eye[f'{side}']["aim"], guides.eye[f'{side}_lower']["aim"]], control_parent=canon.rig, parent_spaces=[headinfo.control.ctrl])
            look.build()

            eye = modules.Eye(rig_size=canon.scene_size, part="eye", side=side, parent=canon.rig, joint_parent=faceinfo.upper_joint, guides=guides.eye[side], muppet=faceinfo.muppet_control, jaw=jawinfo.jaw, control_parent=canon.rig, control_space=[faceinfo.upper_control.ctrl], look_parent=look.main_ctrl.ctrl)
            eye.build()

            #eye = modules.Eye(rig_size=canon.scene_size, part="eye_lower", side=side, parent=canon.rig, joint_parent=faceinfo.upper_joint, guides=guides.eye[f'{side}_lowerx'], muppet=faceinfo.muppet_control, jaw=jawinfo.jaw, control_parent=canon.rig, control_space=[faceinfo.upper_control.ctrl], look_parent=look.main_ctrl.ctrl)
            #eye.build()



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





    









