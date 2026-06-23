
from Workshop.meta_rigs import meta_componets

def build(meta_type:str='metahuman'):

    #verify and assign meta rig type, current plans for mixamo and metahuman, may add more later

    if meta_type == 'metahuman':
        rig_root = meta_componets.configure_metahuman_scene()
    else:
        print(f'meta_type:{meta_type} is incompatible with this build, only metahuman is curently compatable')
    
    body_rig_root:str = rig_root.body_rig #type:ignore
    rig_size:float = rig_root.scene_size #type:ignore

    root = meta_componets.Root(control_size=rig_size, parent=body_rig_root)
    root_info = root.root_build()
    hip = meta_componets.Hip(control_size=rig_size, parent=body_rig_root, control_space=[root_info.offset_control.ctrl])
    hipinfo = hip.hip_build()
    spine = meta_componets.Spine(control_size=rig_size, parent=body_rig_root, fk_control_space=[hipinfo.cog_control.ctrl])
    spineinfo = spine.spine_build()

    for side in ['l', 'r']:
        clav = meta_componets.Clavicle(part='clav', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'clavicle_{side}'], control_space=[spineinfo.fk_spine_controls_list[-1].ctrl], )
        clavinfo = clav.clavicle_build()
        leg = meta_componets.Limb(part='leg', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'thigh_{side}', f'calf_{side}', f'foot_{side}'],ik_end_control = True, fk_control_space=[hipinfo.hip_control.ctrl], ik_control_space=[hipinfo.hip_control.ctrl, root_info.offset_control.ctrl, ])
        leg.limb_build()
        arm = meta_componets.Limb(part='arm', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'upperarm_{side}', f'lowerarm_{side}', f'hand_{side}'],ik_end_control = True, fk_control_space=[clavinfo.clav_control.ctrl], ik_control_space=[clavinfo.clav_control.ctrl, root_info.offset_control.ctrl, ])
        arm.limb_build()
