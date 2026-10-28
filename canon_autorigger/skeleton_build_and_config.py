from attr import dataclass
import maya.cmds as cmds

from Workshop.guide.core import  GuideInfo, read_guide, SplineGuideInfo
from Workshop.tag.core import sets_tag


from Workshop.canon_autorigger.build_management.config_scene import configure_canon_scene
from Workshop.canon_autorigger.build_management.load_guides import load_guides
from Workshop.canon_autorigger.build_management.skin_geo import apply_skins, skin_meshes
from Workshop.canon_autorigger import modules
from Workshop.tag.core import get_tags
from Workshop.canon_autorigger.canon_rig_config import generate_foot_guides


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
    toes:dict[str, list[GuideInfo]]


    jaw:list[GuideInfo]

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

    toes = {}

    for side in ['L', 'R']:
        leg[side] = [read_guide(f'upperleg_{side}_guide'), read_guide(f'knee_{side}_guide'), read_guide(f'foot_{side}_guide')]
        arm[side] = [read_guide(f'shoulder_{side}_guide'), read_guide(f'elbow_{side}_guide'), read_guide(f'hand_{side}_guide')]
        foot[side] = [read_guide(f'foot_{side}_guide'), read_guide(f'toe_ball_{side}_guide'), read_guide(f'toe_ee_{side}_guide')]
        clav[side] = read_guide(f'clav_{side}_guide')
        metacarpal[side] = [read_guide(f'finger_index_{side}_00_guide'), read_guide(f'finger_middle_{side}_00_guide'), read_guide(f'finger_ring_{side}_00_guide'), read_guide(f'finger_pinky_{side}_00_guide'),]

        #fingers = finger_Index_L_01_guide
        for fing in ['thumb', 'index', 'middle', 'ring', 'pinky' ]:
            joint_list = []
            for i in [ '01', '02', '03', '04']:
                guide = read_guide(f'finger_{fing}_{side}_{i}_guide')
                joint_list.append(guide)
            fingers[f'{fing}_{side}'] = joint_list

        for fing in ['thumb', 'index', 'middle', 'ring', 'pinky' ]:
                    joint_list = []
                    for i in ['00', '01', '02', '03',]:
                        guide = read_guide(f'toe_{fing}_{side}_{i}_guide')
                        joint_list.append(guide)
                    toes[f'{fing}_{side}'] = joint_list

    #face_guides
    jaw = [read_guide('jaw_M_guide'), read_guide('jaw_ee_M_guide'), read_guide('larynx_M_guide')]
    #geo temp logic, need to decide later how this will work
    primary_mesh = f'H_Ribcage_02'
    #tag geo
    sets_tag('geo', ['bind_joints_set'])

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
        jaw=jaw,
        toes=toes,
   
        primary_geo=primary_mesh,
    )
    return all_guides





def build(rig_name:str):

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


    root = modules.Root(rig_size=canon.scene_size, joint_parent=canon.joints, parent=canon.rig, guides=[guides.root])
    root_info = root.build()
    



    #middle modules

    hip = modules.Hip(rig_size=canon.scene_size, parent=canon.rig, joint_parent=root_info.joint, control_space=[root_info.offset_control.ctrl], guides=[guides.hip])
    hipinfo = hip.build()

    spine = modules.Spine(rig_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, guides=guides.spine, root_hook=[hipinfo.cog_control, hipinfo.hip_control], control_space=[hipinfo.cog_control.ctrl], divisions=17, chest_control_pos_offset=(0,0,0))
    spineinfo = spine.build()

    neck = modules.Neck(rig_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.neck, control_space=[spineinfo.chest_off.ctrl], divisions=7)
    neckinfo = neck.build()

    head = modules.Head(rig_size=canon.scene_size, parent=canon.rig, joint_parent=neckinfo.joint[-1], guides=guides.head, control_space=[neckinfo.control[-1].ctrl])
    headinfo = head.build()
     



    ##side modules

    for side in ["L", "R"]:
    
        leg = modules.Biped_Limb(part='leg', rig_size=canon.scene_size, parent=canon.rig, joint_parent=hipinfo.hip_joint, side=side, guides=guides.leg[side],ik_end_control = False, fk_control_space=[hipinfo.hip_control.ctrl], ik_root_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl,], ik_pv_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ik_end_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl], ikfk_blend=0, ik_length=True, fk_shape_twist=90, twist_joints=False, ik_bone=True)
        leg_info = leg.build()

        footguide = generate_foot_guides(side=side, parent=None)
        foot = modules.Foot(part='feet', rig_size=canon.scene_size, parent=canon.rig, side=side, joint_parent=leg_info.bind_joints[-1] ,  guides= guides.foot[side], fk_control_space=[leg_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=leg_info.end_ik_hook, feet_guides=footguide, fkik_switch_attr=leg_info.fk_ik_switch, leg_info=leg_info)
        foot_info = foot.build()


        clav = modules.Clav(part='clav', side=side, rig_size=canon.scene_size, parent=canon.rig, joint_parent=spineinfo.bind_joints[-1], guides=guides.clav[side], control_space=[spineinfo.chest_off.ctrl, spineinfo.switch_joints[-1]])
        clav_info = clav.build()

        arm = modules.Biped_Limb(part='arm', rig_size=canon.scene_size, parent=canon.rig, joint_parent=clav_info.joint, side=side, guides=guides.arm[side],ik_end_control = False, fk_control_space=[clav_info.control.ctrl], ik_root_control_space=[clav_info.control.ctrl, hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1],], ik_pv_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_end_control_space=[ hipinfo.hip_control.ctrl, root_info.root_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ikfk_blend=1, ik_length=True, twist_joints=False, ik_bone=True)
        arm_info = arm.build()

        hand = modules.Hand(part='hand', rig_size=canon.scene_size, joint_parent=arm_info.bind_joints[-1],  parent=canon.rig, side=side, guides=guides.arm[side][-1], fk_control_space=[arm_info.fk_controls[-1].ctrl], ik_control_space=[root_info.root_control.ctrl, hipinfo.hip_control.ctrl, spineinfo.switch_joints[-1], clav_info.control.ctrl,], ik_hook=arm_info.end_ik_hook, fk_hook=arm_info.fk_hook , fkik_switch_attr=arm_info.fk_ik_switch, arm_info=arm_info)
        hand_info = hand.build()

        
        metacarpal = modules.Metacarpal(part='metacarpal', joint_parent=hand_info.joint , rig_size=canon.scene_size, parent=canon.rig, side=side, guides=guides.metacarpal[side], control_space=[hand_info.switch],)
        metacarpal_info = metacarpal.build()

        for i, fingers in enumerate(['index', 'middle', 'ring', 'pinky', 'thumb']):
            if fingers == 'thumb':
                parent = hand_info.switch
                jnt_par = hand_info.joint
            else:
                parent = metacarpal_info.control[i].ctrl
                jnt_par = metacarpal_info.joint[i]

            finger = modules.Chain(part=fingers, rig_size=canon.scene_size, joint_parent=jnt_par, parent=canon.rig, side=side, guides=guides.fingers[f'{fingers}_{side}'], control_space=[parent])
            finger.build()

        for i, toes in enumerate(['index', 'middle', 'ring', 'pinky', 'thumb']):
                    
                    parent = foot_info.swtich_joints[1]
                    jnt_par = foot_info.bind_joints[1]
        
                    toe = modules.Chain(part=f'toe_{toes}', rig_size=canon.scene_size, joint_parent=jnt_par, parent=canon.rig, side=side, guides=guides.toes[f'{toes}_{side}'], control_space=[parent])
                    toe.build()



    jaw = modules.Jaw(rig_size=canon.scene_size, parent=canon.rig, joint_parent=headinfo.joint, guides=guides.jaw, control_space=[headinfo.control], larynx_follow_space=headinfo.control.ctrl, mid_face=None )
    jawinfo = jaw.build()


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





    