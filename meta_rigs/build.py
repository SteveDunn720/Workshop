
from Workshop.meta_rigs import meta_componets
import maya.cmds as cmds
from Workshop.tag.core import get_tags
from Workshop.meta_rigs.metahuman_rig_prep import generate_foot_guides

def build(meta_type:str='metahuman'):

    #verify and assign meta rig type, current plans for mixamo and metahuman, may add more later

    if meta_type == 'metahuman':
        rig_root = meta_componets.configure_metahuman_scene()
    else:
        print(f'meta_type:{meta_type} is incompatible with this build, only metahuman is curently compatable')


    #prep    
    
    body_rig_root:str = rig_root.body_rig #type:ignore
    rig_size:float = rig_root.scene_size #type:ignore


    #middle rig parts

    root = meta_componets.Root(control_size=rig_size, parent=body_rig_root)
    root_info = root.root_build()
    hip = meta_componets.Hip(control_size=rig_size, parent=body_rig_root, control_space=[root_info.offset_control.ctrl])
    hipinfo = hip.hip_build()
    spine = meta_componets.Spine(control_size=rig_size, parent=body_rig_root, fk_control_space=[hipinfo.cog_control.ctrl])
    spineinfo = spine.spine_build()

    #side parts

    for side in ['l', 'r']:
        clav = meta_componets.Clavicle(part='clav', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'clavicle_{side}'], control_space=[spineinfo.fk_spine_controls_list[-1].ctrl], )
        clavinfo = clav.clavicle_build()

        arm = meta_componets.Limb(part='arm', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'upperarm_{side}', f'lowerarm_{side}', f'hand_{side}'],ik_end_control = False, fk_control_space=[clavinfo.clav_control.ctrl], ik_control_space=[clavinfo.clav_control.ctrl, root_info.offset_control.ctrl, ])
        arm_info = arm.limb_build()

        leg = meta_componets.Limb(part='leg', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'thigh_{side}', f'calf_{side}', f'foot_{side}'],ik_end_control = False, fk_control_space=[hipinfo.hip_control.ctrl], ik_control_space=[hipinfo.hip_control.ctrl, root_info.offset_control.ctrl, ], ikfk_blend=0)
        leg_info = leg.limb_build()

        footguide = generate_foot_guides(parent=rig_root.guides, side=side)
        foot = meta_componets.Foot(part='feet', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'foot_{side}', f'ball_{side}'], fk_control_space=[leg_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=leg_info.end_ik_hook, feet_guides=footguide, fkik_switch_attr=leg_info.fk_ik_switch)
        foot_info = foot.foot_build()


        #hand

        hand = meta_componets.Hand(part='palm', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'hand_{side}',], fk_control_space=[arm_info.fk_controls[-1].ctrl], ik_control_space=[root_info.offset_control.ctrl, hipinfo.hip_control.ctrl, ], ik_hook=arm_info.end_ik_hook, fkik_switch_attr=arm_info.fk_ik_switch)
        hand_info = hand.hand_build()


        #metacarples

        metacarpal = meta_componets.Metacarpal(part='metacarpal', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'index_metacarpal_{side}', f'middle_metacarpal_{side}', f'ring_metacarpal_{side}', f'pinky_metacarpal_{side}'], fk_control_space=[hand_info.switch],)
        metacarpal_info = metacarpal.metacarpal_build()



        for i, finger in enumerate(['index', 'middle', 'ring', 'pinky', 'thumb']):
            if finger == 'thumb':
                parent = hand_info.switch
            else:
                parent = metacarpal_info.fk_controls[i].ctrl

            finger = meta_componets.Chain(part=finger, control_size=rig_size, parent=body_rig_root, side=side, joints= [f'{finger}_01_{side}', f'{finger}_02_{side}', f'{finger}_03_{side}',], fk_control_space=parent, )
            finger.chain_build()









    # check for and apply tags

    rig_nodes = cmds.listRelatives(body_rig_root, allDescendents=True, fullPath=False, shapes=False, type="transform")

    for node in rig_nodes:
        get_tags(node)

    cmds.delete('guides')

    
